"""Daily watch scans.

* ``EdgarDailyFormDAdapter`` (#13): reads the EDGAR daily form index for the
  last few business days, fetches each Form D / D-A filing's XML, and imports
  NJ issuers. Accession numbers match the quarterly data sets, so filings
  imported here are not duplicated when the quarter is published. A new Form
  D from a known SEC company ID becomes a ``raised_again`` alert on refresh.
* ``watch_announcements`` (#14): pulls new NJEDA and CSIT posts through their
  WordPress JSON APIs, keeps the ones about awards, grants, investments, or
  credits, and (when an Anthropic key is configured) extracts award facts
  with ``gauge.ai.announcements``. Low-confidence extractions go to the
  review queue; usable ones become announcement records that the linker can
  only propose for review, never merge silently.

New SBIR/STTR awards are picked up by the daily ``ingest-sbir`` job; the
refresh after it turns new NJ Phase II awards into alerts.
"""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from gauge.core.models import Address, FormDFacts, NormalizedRecord, Provenance, SourceType
from gauge.sources.base import FetchContext, RawPayload, RecordRejected, SourceAdapter
from gauge.sources.formd import filing_url
from gauge.sources.http import FetchError, Http

# --- EDGAR daily index (#13) --------------------------------------------------------

DAILY_INDEX = "https://www.sec.gov/Archives/edgar/daily-index/{y}/QTR{q}/form.{ymd}.idx"
INDEX_LINE = re.compile(
    r"^(D|D/A)\s+(.+?)\s+(\d{1,10})\s+(\d{8})\s+(edgar/data/\d+/(\d{10}-\d{2}-\d{6})\.txt)\s*$"
)
SECURITY_TAGS = (
    ("isEquityType", "Equity"),
    ("isDebtType", "Debt"),
    ("isOptionToAcquireType", "Option, Warrant or Other Right to Acquire"),
    ("isSecurityToBeAcquiredType", "Security to be Acquired"),
    ("isPooledInvestmentFundType", "Pooled Investment Fund Interests"),
    ("isTenantInCommonType", "Tenant-in-Common"),
    ("isMineralPropertyType", "Mineral Property"),
    ("isOtherType", "Other"),
)


@dataclass(frozen=True)
class IndexEntry:
    form: str
    company: str
    cik: str
    filed: date
    accession: str


def parse_daily_index(text: str) -> list[IndexEntry]:
    out = []
    for line in text.splitlines():
        m = INDEX_LINE.match(line)
        if m:
            form, company, cik, ymd, _, acc = m.groups()
            out.append(
                IndexEntry(
                    form,
                    company.strip(),
                    cik.zfill(10),
                    datetime.strptime(ymd, "%Y%m%d").date(),
                    acc,
                )
            )
    return out


def primary_doc_url(cik: str, accession: str) -> str:
    return filing_url(cik, accession) + "primary_doc.xml"


def _text(node: ET.Element | None, path: str) -> str:
    found = node.find(path) if node is not None else None
    return (found.text or "").strip() if found is not None and found.text else ""


def _amount(v: str) -> float | None:
    try:
        return float(v)
    except ValueError:
        return None  # "Indefinite" or blank


def parse_form_d_xml(xml: bytes) -> dict[str, Any]:
    root = ET.fromstring(xml)
    issuer = root.find("primaryIssuer")
    offering = root.find("offeringData")
    year = issuer.find("yearOfInc") if issuer is not None else None
    within = None
    if year is not None:
        if _text(year, "withinFiveYears") == "true" or year.find("yetToBeFormed") is not None:
            within = True
        elif _text(year, "overFiveYears") == "true":
            within = False
    types = offering.find("typesOfSecuritiesOffered") if offering is not None else None
    return {
        "test_or_live": _text(root, "testOrLive"),
        "cik": _text(issuer, "cik"),
        "name": _text(issuer, "entityName"),
        "street": " ".join(
            p
            for p in (
                _text(issuer, "issuerAddress/street1"),
                _text(issuer, "issuerAddress/street2"),
            )
            if p
        ),
        "city": _text(issuer, "issuerAddress/city"),
        "state": _text(issuer, "issuerAddress/stateOrCountry"),
        "zip": _text(issuer, "issuerAddress/zipCode"),
        "jurisdiction": _text(issuer, "jurisdictionOfInc"),
        "entity_type": _text(issuer, "entityType"),
        "year_of_inc": _text(issuer, "yearOfInc/value"),
        "within_five_years": within,
        "industry_group": _text(offering, "industryGroup/industryGroupType"),
        "investment_fund_type": _text(
            offering, "industryGroup/investmentFundInfo/investmentFundType"
        ),
        "revenue_range": _text(offering, "issuerSize/revenueRange"),
        "is_amendment": _text(offering, "typeOfFiling/newOrAmendment/isAmendment") == "true",
        "date_of_first_sale": _text(offering, "typeOfFiling/dateOfFirstSale/value"),
        "securities": [label for tag, label in SECURITY_TAGS if _text(types, tag) == "true"],
        "total_offering_amount": _text(offering, "offeringSalesAmounts/totalOfferingAmount"),
        "total_amount_sold": _text(offering, "offeringSalesAmounts/totalAmountSold"),
    }


class EdgarDailyFormDAdapter(SourceAdapter):
    name = "edgar-daily-form-d"
    source_type = SourceType.SEC_FORM_D
    allowed_domains = ("sec.gov",)

    def __init__(self, lookback_days: int = 5, max_filings: int | None = None) -> None:
        self.lookback_days = lookback_days
        self.max_filings = max_filings

    def days(self, today: date) -> list[date]:
        days = [today - timedelta(days=i) for i in range(1, self.lookback_days + 1)]
        return sorted(d for d in days if d.weekday() < 5)

    def fetch(self, ctx: FetchContext) -> list[RawPayload]:
        base = ctx.raw_dir / "edgar-daily"
        payloads: list[RawPayload] = []
        for day in self.days(ctx.today):
            q = (day.month - 1) // 3 + 1
            url = DAILY_INDEX.format(y=day.year, q=q, ymd=day.strftime("%Y%m%d"))
            idx = base / f"form.{day:%Y%m%d}.idx"
            if not idx.exists():
                try:
                    ctx.http.download(url, idx, only_if_newer=False)
                except FetchError as e:
                    if "404" in str(e) or "403" in str(e):
                        continue  # holiday or not yet published
                    raise
            for entry in parse_daily_index(idx.read_text(errors="replace")):
                if self.max_filings is not None and len(payloads) >= self.max_filings:
                    return payloads
                doc = base / "filings" / f"{entry.accession}.xml"
                doc_url = primary_doc_url(entry.cik, entry.accession)
                if not doc.exists():
                    ctx.http.download(doc_url, doc, only_if_newer=False)
                payloads.append(RawPayload(entry.accession, doc_url, doc))
                meta = doc.with_suffix(".json")
                if not meta.exists():
                    meta.write_text(
                        json.dumps({"filed": entry.filed.isoformat(), "cik": entry.cik})
                    )
        return payloads

    def parse(self, payload: RawPayload) -> Iterator[dict[str, Any]]:
        meta = json.loads(payload.path.with_suffix(".json").read_text())
        row = parse_form_d_xml(payload.path.read_bytes())
        row.update(accession=payload.source_id, filed=meta["filed"], index_cik=meta["cik"])
        yield row

    def normalize(
        self, row: dict[str, Any], payload: RawPayload, ctx: FetchContext
    ) -> NormalizedRecord | None:
        if row["test_or_live"] and row["test_or_live"] != "LIVE":
            return None
        if row["state"].upper() not in {s.upper() for s in ctx.states}:
            return None
        if not row["name"]:
            raise RecordRejected(f"{row['accession']}: issuer has no name")
        cik = (row["cik"] or row["index_cik"]).zfill(10)
        return NormalizedRecord(
            provenance=Provenance(
                SourceType.SEC_FORM_D,
                row["accession"],
                filing_url(cik, row["accession"]),
                date.fromisoformat(row["filed"]),
            ),
            name=row["name"],
            address=Address(
                row["street"] or None,
                row["city"].title() or None,
                row["state"].upper(),
                row["zip"] or None,
            ),
            cik=cik,
            form_d=FormDFacts(
                industry_group=row["industry_group"] or None,
                is_pooled_investment_fund="Pooled Investment Fund Interests" in row["securities"]
                or bool(row["investment_fund_type"]),
                entity_type=row["entity_type"] or None,
                jurisdiction_of_incorporation=row["jurisdiction"] or None,
                year_of_incorporation=int(row["year_of_inc"])
                if row["year_of_inc"].isdigit()
                else None,
                incorporated_within_five_years=row["within_five_years"],
                revenue_range=row["revenue_range"] or None,
                total_offering_amount=_amount(row["total_offering_amount"]),
                total_amount_sold=_amount(row["total_amount_sold"]),
                date_of_first_sale=date.fromisoformat(row["date_of_first_sale"])
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date_of_first_sale"])
                else None,
                is_amendment=row["is_amendment"],
                securities_offered=tuple(row["securities"]),
            ),
        )


# --- NJEDA / CSIT announcements (#14) ----------------------------------------------------

FEEDS = {
    SourceType.NJEDA_ANNOUNCEMENT: "https://www.njeda.gov/wp-json/wp/v2/posts",
    SourceType.CSIT_ANNOUNCEMENT: "https://www.njcsit.gov/wp-json/wp/v2/posts",
}
RELEVANT = re.compile(
    r"\b(award(s|ed)?|grant(s|ed)?|invest(s|ed|ment|ments)|tax credits?|recipients?|"
    r"approv(es|ed)|funding|fund(s|ed)?|closes? on)\b",
    re.IGNORECASE,
)
_TAG = re.compile(r"<[^>]+>")


def html_to_text(markup: str) -> str:
    text = re.sub(r"</(p|h\d|li|div)>|<br\s*/?>", "\n", markup, flags=re.I)
    text = html.unescape(_TAG.sub("", text))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


@dataclass(frozen=True)
class Post:
    source_type: SourceType
    post_id: str
    url: str
    published_on: date
    title: str
    text: str

    @property
    def relevant(self) -> bool:
        return bool(RELEVANT.search(self.title) or RELEVANT.search(self.text[:1500]))


def fetch_posts(http: Http, source_type: SourceType, since: date, raw_dir: Path) -> list[Post]:
    url = (
        f"{FEEDS[source_type]}?per_page=50&orderby=date&order=desc"
        f"&after={since.isoformat()}T00:00:00&_fields=id,date,link,title,content"
    )
    body = http.get(url)
    dest = raw_dir / "announcements" / f"{source_type.value}-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    posts = []
    for p in json.loads(body):
        posts.append(
            Post(
                source_type,
                str(p["id"]),
                p["link"],
                date.fromisoformat(p["date"][:10]),
                html.unescape(_TAG.sub("", p["title"]["rendered"])).strip(),
                html_to_text(p.get("content", {}).get("rendered", "")),
            )
        )
    return posts


def llm_enabled() -> bool:
    flag = os.environ.get("GAUGE_ENABLE_LLM_EXTRACTION")
    if flag is not None:
        return flag == "1"
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def store_posts(conn: sqlite3.Connection, posts: list[Post], *, llm: bool) -> list[int]:
    """Insert new posts; return ids of new relevant ones waiting for extraction."""
    stamp = datetime.now(UTC).isoformat()
    pending = []
    with conn:
        for p in posts:
            status = (
                "pending"
                if p.relevant and llm
                else ("llm_disabled" if p.relevant else "not_relevant")
            )
            cur = conn.execute(
                """INSERT OR IGNORE INTO announcements
                   (source_type, post_id, url, published_on, title, text, fetched_at,
                    relevant, extraction_status)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    p.source_type.value,
                    p.post_id,
                    p.url,
                    p.published_on.isoformat(),
                    p.title,
                    p.text,
                    stamp,
                    int(p.relevant),
                    status,
                ),
            )
            if cur.rowcount and status == "pending":
                pending.append(int(cur.lastrowid))
    return pending


def extract_pending(conn: sqlite3.Connection, llm_client, store) -> tuple[int, int]:
    """Run extraction on pending announcements. Returns (announcements processed, records added)."""
    from gauge.ai.announcements import Announcement, extract, queue_for_review, to_record, usable
    from gauge.db.repo import upsert_records

    processed = added = 0
    rows = conn.execute(
        "SELECT * FROM announcements WHERE extraction_status = 'pending' ORDER BY published_on"
    ).fetchall()
    for row in rows:
        ann = Announcement(
            SourceType(row["source_type"]),
            row["url"],
            date.fromisoformat(row["published_on"]),
            row["title"],
            row["text"],
        )
        result = extract(ann, llm_client)
        stamp = datetime.now(UTC).isoformat()
        with conn:
            if result.error:
                conn.execute(
                    "UPDATE announcements SET extraction_status='failed', "
                    "extraction_error=?, extracted_at=? WHERE id=?",
                    (result.error, stamp, row["id"]),
                )
                continue
            for a in result.awards:
                conn.execute(
                    "INSERT OR REPLACE INTO announcement_extractions "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        row["id"],
                        a.extraction_id,
                        a.company_name,
                        a.program_name,
                        a.award_date.isoformat() if a.award_date else None,
                        a.amount_usd,
                        a.sector,
                        a.town,
                        a.quote,
                        a.confidence,
                        a.extracted_by,
                        int(a.needs_review),
                    ),
                )
                conn.executemany(
                    "INSERT OR REPLACE INTO announcement_extraction_issues VALUES (?,?,?,?)",
                    [(row["id"], a.extraction_id, i, issue) for i, issue in enumerate(a.issues)],
                )
            conn.execute(
                "UPDATE announcements SET extraction_status='extracted', extracted_at=? WHERE id=?",
                (stamp, row["id"]),
            )
        queue_for_review(result, store)
        added += upsert_records(conn, [to_record(a) for a in usable(result.awards, store)])[0]
        processed += 1
    return processed, added
