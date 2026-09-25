import json
from datetime import date

from gauge.ai.claude import JsonResult
from gauge.core.models import SourceType
from gauge.db.connection import open_database
from gauge.db.repo import load_records
from gauge.db.stores import SqliteReviewStore
from gauge.sources.base import FetchContext
from gauge.sources.watch import (
    EdgarDailyFormDAdapter,
    Post,
    extract_pending,
    fetch_posts,
    html_to_text,
    parse_daily_index,
    parse_form_d_xml,
    store_posts,
)
from tests.ai.fakes import FakeLLM
from tests.sources.test_adapters import FakeHttp

INDEX = """Form Type   Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------------------------------------
1-A              Something Else Inc.                                           2065495     20260923    edgar/data/2065495/0001683168-26-007327.txt
D                Halyard Sensors, Inc.                                         1234        20260923    edgar/data/1234/0000001234-26-000001.txt
D/A              Keystone Labs                                                 5678        20260923    edgar/data/5678/0000005678-26-000002.txt
"""


def form_d_xml(
    state="NJ", name="Halyard Sensors, Inc.", cik="0000001234", live="LIVE", amendment="false"
):
    return f"""<?xml version="1.0"?><edgarSubmission><schemaVersion>X0708</schemaVersion>
<submissionType>D</submissionType><testOrLive>{live}</testOrLive>
<primaryIssuer><cik>{cik}</cik><entityName>{name}</entityName>
<issuerAddress><street1>1 River St</street1><city>HOBOKEN</city><stateOrCountry>{state}</stateOrCountry><zipCode>07030</zipCode></issuerAddress>
<jurisdictionOfInc>DELAWARE</jurisdictionOfInc><entityType>Corporation</entityType>
<yearOfInc><withinFiveYears>true</withinFiveYears><value>2024</value></yearOfInc></primaryIssuer>
<offeringData><industryGroup><industryGroupType>Other Technology</industryGroupType></industryGroup>
<issuerSize><revenueRange>No Revenues</revenueRange></issuerSize>
<typeOfFiling><newOrAmendment><isAmendment>{amendment}</isAmendment></newOrAmendment><dateOfFirstSale><value>2026-09-01</value></dateOfFirstSale></typeOfFiling>
<typesOfSecuritiesOffered><isEquityType>true</isEquityType></typesOfSecuritiesOffered>
<offeringSalesAmounts><totalOfferingAmount>Indefinite</totalOfferingAmount><totalAmountSold>750000</totalAmountSold></offeringSalesAmounts>
</offeringData></edgarSubmission>""".encode()


def test_daily_index_keeps_only_form_d():
    entries = parse_daily_index(INDEX)
    assert [(e.form, e.cik, e.accession) for e in entries] == [
        ("D", "0000001234", "0000001234-26-000001"),
        ("D/A", "0000005678", "0000005678-26-000002"),
    ]
    assert entries[0].filed == date(2026, 9, 23)


def test_form_d_xml_fields():
    row = parse_form_d_xml(form_d_xml())
    assert row["name"] == "Halyard Sensors, Inc." and row["state"] == "NJ"
    assert row["within_five_years"] is True and row["securities"] == ["Equity"]
    assert row["total_offering_amount"] == "Indefinite" and row["total_amount_sold"] == "750000"


def test_edgar_watch_imports_nj_filings_with_quarterly_accession_ids(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "idx").write_text(INDEX)
    (src / "nj.xml").write_bytes(form_d_xml())
    (src / "pa.xml").write_bytes(form_d_xml(state="PA", name="Keystone Labs", cik="0000005678"))
    idx_url = "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR3/form.20260923.idx"
    http = FakeHttp(files={
        idx_url: src / "idx",
        "https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/primary_doc.xml": src / "nj.xml",
        "https://www.sec.gov/Archives/edgar/data/5678/000000567826000002/primary_doc.xml": src / "pa.xml",
    })  # fmt: skip

    def download(url, dest, *, only_if_newer=True):
        if url not in http.files:
            from gauge.sources.http import FetchError

            raise FetchError(f"GET {url} failed: HTTP Error 404")
        return FakeHttp.download(http, url, dest)

    http.download = download
    conn = open_database(tmp_path / "g.sqlite3")
    ctx = FetchContext(tmp_path / "raw", http, today=date(2026, 9, 24))
    summary = EdgarDailyFormDAdapter(lookback_days=2).run(conn, ctx)
    assert (summary.payloads, summary.added, summary.filtered) == (2, 1, 1) and not summary.failed
    (rec,) = load_records(conn)
    assert rec.provenance.source_id == "0000001234-26-000001"  # same id the quarterly data set uses
    assert rec.source_date == date(2026, 9, 23) and rec.form_d.total_amount_sold == 750000
    assert rec.form_d.total_offering_amount is None and rec.address.city == "Hoboken"
    again = EdgarDailyFormDAdapter(lookback_days=2).run(conn, ctx)
    assert again.added == 0 and again.skipped == 1


def test_weekends_are_skipped():
    days = EdgarDailyFormDAdapter(lookback_days=7).days(date(2026, 9, 28))  # a Monday
    assert all(d.weekday() < 5 for d in days) and len(days) == 5


POSTS = [
    {"id": 1, "date": "2026-09-17T15:00:04", "link": "https://www.njcsit.gov/grants",
     "title": {"rendered": "CSIT Awards SBIR Grants to Three Companies"},
     "content": {"rendered": "<p>Halyard Sensors LLC received a $25,000 Direct Funding Grant.</p>"}},
    {"id": 2, "date": "2026-09-09T10:00:00", "link": "https://www.njcsit.gov/board",
     "title": {"rendered": "Notice of Board Meeting &#8211; 9/16"},
     "content": {"rendered": "<p>The board meets virtually.</p>"}},
]  # fmt: skip


def test_announcements_are_stored_and_relevant_ones_extracted(tmp_path):
    class JsonHttp(FakeHttp):
        def get(self, url):
            return json.dumps(POSTS).encode()

    conn = open_database(tmp_path / "g.sqlite3")
    posts = fetch_posts(
        JsonHttp(), SourceType.CSIT_ANNOUNCEMENT, date(2026, 9, 1), tmp_path / "raw"
    )
    assert [p.relevant for p in posts] == [True, False]
    assert posts[1].title == "Notice of Board Meeting – 9/16"
    pending = store_posts(conn, posts, llm=True)
    assert len(pending) == 1
    assert store_posts(conn, posts, llm=True) == []  # already stored

    quote = "Halyard Sensors LLC received a $25,000 Direct Funding Grant."
    llm = FakeLLM(JsonResult({"awards": [{
        "company_name": "Halyard Sensors LLC", "program_name": "Direct Funding Grant", "award_date": None,
        "amount_usd": 25000, "sector": None, "town": None, "quote": quote, "confidence": 0.95}]},
        "claude-opus-5"))  # fmt: skip
    store = SqliteReviewStore(conn)
    assert extract_pending(conn, llm, store) == (1, 1)
    (rec,) = load_records(conn)
    assert (
        rec.provenance.source_type is SourceType.CSIT_ANNOUNCEMENT
        and rec.name == "Halyard Sensors LLC"
    )
    status = conn.execute(
        "SELECT extraction_status FROM announcements WHERE post_id='1'"
    ).fetchone()[0]
    assert status == "extracted"
    assert conn.execute("SELECT count(*) FROM announcement_extractions").fetchone()[0] == 1


def test_without_an_llm_relevant_posts_wait(tmp_path):
    conn = open_database(tmp_path / "g.sqlite3")
    post = Post(
        SourceType.NJEDA_ANNOUNCEMENT,
        "9",
        "https://www.njeda.gov/x",
        date(2026, 9, 1),
        "Grant awarded",
        "x",
    )
    assert store_posts(conn, [post], llm=False) == []
    assert (
        conn.execute("SELECT extraction_status FROM announcements").fetchone()[0] == "llm_disabled"
    )


def test_html_to_text():
    assert html_to_text("<p>One &amp; two</p><p>Three<br>four</p>") == "One & two\nThree\nfour"
