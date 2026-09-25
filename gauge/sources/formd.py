"""SEC Form D quarterly data sets -> NormalizedRecords.

Source: https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets
Each quarterly zip holds tab-separated FORMDSUBMISSION, ISSUERS, and
OFFERING tables keyed by accession number. Only the primary issuer is used,
only live filings are kept, and issuers are filtered by state.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Collection, Iterator
from datetime import date, datetime
from pathlib import Path

from gauge.core.models import (
    Address,
    FormDFacts,
    NormalizedRecord,
    Provenance,
    SourceType,
)

DATASET_PAGE = "https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets"

_SECURITY_FLAGS = (
    ("ISEQUITYTYPE", "Equity"),
    ("ISDEBTTYPE", "Debt"),
    ("ISOPTIONTOACQUIRETYPE", "Option, Warrant or Other Right to Acquire"),
    ("ISSECURITYTOBEACQUIREDTYPE", "Security to be Acquired"),
    ("ISPOOLEDINVESTMENTFUNDTYPE", "Pooled Investment Fund Interests"),
    ("ISTENANTINCOMMONTYPE", "Tenant-in-Common"),
    ("ISMINERALPROPERTYTYPE", "Mineral Property"),
    ("ISOTHERTYPE", "Other"),
)


def filing_url(cik: str, accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def _table(z: zipfile.ZipFile, name: str) -> Iterator[dict[str, str]]:
    member = next(n for n in z.namelist() if n.upper().endswith(f"/{name}.TSV"))
    with z.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
        yield from csv.DictReader(text, delimiter="\t", quoting=csv.QUOTE_NONE)


def _flag(v: str | None) -> bool:
    return (v or "").strip().lower() == "true"


def _amount(v: str | None) -> float | None:
    v = (v or "").strip()
    if not v or v.lower() == "indefinite":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _date(v: str | None, fmt: str) -> date | None:
    try:
        return datetime.strptime((v or "").strip(), fmt).date()
    except ValueError:
        return None


def read_quarter(path: str | Path, states: Collection[str] = ("NJ",)) -> list[NormalizedRecord]:
    wanted = {s.upper() for s in states}
    with zipfile.ZipFile(path) as z:
        filed: dict[str, date] = {}
        for row in _table(z, "FORMDSUBMISSION"):
            if row.get("TESTORLIVE", "LIVE").strip() != "LIVE":
                continue
            # Newer files use 31-MAR-2022; files through 2020 use 2019-06-28 17:30:19.
            raw = (row.get("FILING_DATE") or "").strip()
            d = _date(raw, "%d-%b-%Y") or _date(raw[:10], "%Y-%m-%d")
            if d:
                filed[row["ACCESSIONNUMBER"]] = d
        issuers: dict[str, dict[str, str]] = {}
        for row in _table(z, "ISSUERS"):
            if row.get("IS_PRIMARYISSUER_FLAG") != "YES":
                continue
            if (row.get("STATEORCOUNTRY") or "").strip().upper() not in wanted:
                continue
            issuers[row["ACCESSIONNUMBER"]] = row
        records = []
        for row in _table(z, "OFFERING"):
            acc = row["ACCESSIONNUMBER"]
            issuer = issuers.get(acc)
            if issuer is None or acc not in filed:
                continue
            records.append(_record(acc, filed[acc], issuer, row))
    return records


def _record(
    acc: str, filed: date, issuer: dict[str, str], offering: dict[str, str]
) -> NormalizedRecord:
    cik = issuer["CIK"].strip().zfill(10)
    year = (issuer.get("YEAROFINC_VALUE_ENTERED") or "").strip()
    span = (issuer.get("YEAROFINC_TIMESPAN_CHOICE") or "").strip()
    within = {"withinFiveYears": True, "yetToBeFormed": True, "overFiveYears": False}.get(span)
    street = " ".join(p for p in (issuer.get("STREET1"), issuer.get("STREET2")) if p and p.strip())
    return NormalizedRecord(
        provenance=Provenance(SourceType.SEC_FORM_D, acc, filing_url(cik, acc), filed),
        name=issuer["ENTITYNAME"].strip(),
        address=Address(
            street=street or None,
            city=(issuer.get("CITY") or "").strip().title() or None,
            state=(issuer.get("STATEORCOUNTRY") or "").strip().upper() or None,
            postal_code=(issuer.get("ZIPCODE") or "").strip() or None,
        ),
        cik=cik,
        form_d=FormDFacts(
            industry_group=(offering.get("INDUSTRYGROUPTYPE") or "").strip() or None,
            is_pooled_investment_fund=_flag(offering.get("ISPOOLEDINVESTMENTFUNDTYPE"))
            or bool((offering.get("INVESTMENTFUNDTYPE") or "").strip()),
            entity_type=(issuer.get("ENTITYTYPE") or "").strip() or None,
            jurisdiction_of_incorporation=(issuer.get("JURISDICTIONOFINC") or "").strip() or None,
            year_of_incorporation=int(year) if year.isdigit() else None,
            incorporated_within_five_years=within,
            revenue_range=(offering.get("REVENUERANGE") or "").strip() or None,
            total_offering_amount=_amount(offering.get("TOTALOFFERINGAMOUNT")),
            total_amount_sold=_amount(offering.get("TOTALAMOUNTSOLD")),
            date_of_first_sale=_date(offering.get("SALE_DATE"), "%Y-%m-%d"),
            is_amendment=_flag(offering.get("ISAMENDMENT")),
            securities_offered=tuple(
                label for col, label in _SECURITY_FLAGS if _flag(offering.get(col))
            ),
        ),
    )


def read_directory(
    directory: str | Path, states: Collection[str] = ("NJ",)
) -> list[NormalizedRecord]:
    """Every ``*_d.zip`` in ``directory``, deduplicated by accession number."""
    seen: dict[str, NormalizedRecord] = {}
    for path in sorted(Path(directory).glob("*_d.zip")):
        for rec in read_quarter(path, states):
            seen.setdefault(rec.provenance.source_id, rec)
    return sorted(seen.values(), key=lambda r: (r.source_date, r.key))
