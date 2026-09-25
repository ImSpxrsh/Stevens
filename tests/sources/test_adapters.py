import shutil
from datetime import date
from pathlib import Path

from gauge.core.models import Address, NormalizedRecord, Provenance, SourceType
from gauge.db.connection import open_database
from gauge.db.repo import load_records
from gauge.sources.adapters import FormDDataSetAdapter, SbirAwardsAdapter
from gauge.sources.base import FetchContext, RawPayload, RecordRejected, SourceAdapter
from gauge.sources.http import FetchError, Http
from tests.sources.test_sources import write_quarter, write_sbir


class FakeHttp(Http):
    """Serves pages and files from a dict instead of the network."""

    def __init__(self, pages=None, files=None):
        super().__init__(user_agent="Gauge test test@example.com")
        self.pages, self.files, self.downloads = pages or {}, files or {}, []

    def get(self, url):
        if url not in self.pages:
            raise FetchError(f"no page {url}")
        return self.pages[url].encode()

    def download(self, url, dest, *, only_if_newer=True):
        self.downloads.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.files[url], dest)
        return True


def test_form_d_adapter_downloads_missing_quarters_and_imports_nj(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    write_quarter(src / "q1.zip")
    write_quarter(src / "q2.zip", filing_date="30-JUN-2022")
    page = (
        '<a href="/files/structureddata/data/form-d-data-sets/2022q1_d.zip">'
        '<a href="/files/structureddata/data/form-d-data-sets/2022q2_d.zip">'
        '<a href="/files/structureddata/data/form-d-data-sets/2018q4_d.zip">'
    )
    base = "https://www.sec.gov/files/structureddata/data/form-d-data-sets/"
    http = FakeHttp(
        {"https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets": page},
        {base + "2022q1_d.zip": src / "q1.zip", base + "2022q2_d.zip": src / "q2.zip"},
    )
    conn = open_database(tmp_path / "g.sqlite3")
    ctx = FetchContext(raw_dir=tmp_path / "raw", http=http, today=date(2026, 9, 1))
    summary = FormDDataSetAdapter().run(conn, ctx)
    assert (
        summary.payloads == 2 and summary.added == 1 and summary.filtered == 2
    )  # PA issuer in each quarter; TEST filings never parse
    # Both fixture quarters carry the same accession: stored once.
    assert summary.skipped == 1 and not summary.failed
    assert all("2018q4" not in u for u in http.downloads)

    again = FormDDataSetAdapter().run(conn, ctx)
    assert again.added == 0 and again.skipped == 2
    assert http.downloads.count(base + "2022q1_d.zip") == 1  # published quarters are not refetched
    runs = conn.execute("SELECT status, records_added FROM importer_runs ORDER BY id").fetchall()
    assert [tuple(r) for r in runs] == [("ok", 1), ("ok", 0)]
    assert conn.execute("SELECT count(*) FROM raw_source_records").fetchone()[0] == 2


def test_sbir_adapter(tmp_path):
    write_sbir(tmp_path / "awards.csv")
    http = FakeHttp(
        files={"https://data.www.sbir.gov/awarddatapublic/award_data.csv": tmp_path / "awards.csv"}
    )
    conn = open_database(tmp_path / "g.sqlite3")
    summary = SbirAwardsAdapter().run(
        conn, FetchContext(tmp_path / "raw", http, today=date(2026, 9, 1))
    )
    assert summary.added == 2 and summary.filtered == 1
    assert {r.name for r in load_records(conn)} == {"Pinewood Therapeutics LLC", "Year Only Co"}


class BadAdapter(SourceAdapter):
    name = "bad"
    source_type = SourceType.SEC_FORM_D
    allowed_domains = ("sec.gov",)

    def __init__(self, rows):
        self.rows = rows

    def fetch(self, ctx):
        p = ctx.raw_dir / "x.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
        return [RawPayload("x", "https://www.sec.gov/x", p)]

    def parse(self, payload):
        yield from self.rows

    def normalize(self, row, payload, ctx):
        if row == "malformed":
            raise RecordRejected("row is malformed")
        url, when = row
        from gauge.core.models import FormDFacts

        return NormalizedRecord(
            Provenance(SourceType.SEC_FORM_D, f"id-{url}-{when}", url, when),
            "Acme",
            Address(state="NJ"),
            form_d=FormDFacts(),
        )


def test_bad_records_are_rejected_reported_and_never_persisted(tmp_path):
    conn = open_database(tmp_path / "g.sqlite3")
    rows = [
        ("https://www.sec.gov/ok", date(2026, 1, 1)),
        ("https://evil.example.com/x", date(2026, 1, 1)),
        ("https://www.sec.gov/future", date(2027, 1, 1)),
        "malformed",
    ]
    ctx = FetchContext(tmp_path / "raw", FakeHttp(), today=date(2026, 9, 1))
    summary = BadAdapter(rows).run(conn, ctx)
    assert summary.added == 1 and summary.rejected == 3
    joined = " ".join(summary.errors)
    assert "not an expected source" in joined and "future" in joined and "malformed" in joined
    assert [r.provenance.source_url for r in load_records(conn)] == ["https://www.sec.gov/ok"]


def test_fetch_failure_fails_the_run_visibly(tmp_path):
    conn = open_database(tmp_path / "g.sqlite3")
    summary = FormDDataSetAdapter().run(conn, FetchContext(tmp_path / "raw", FakeHttp()))
    assert summary.failed and "FAILED" in summary.line()
    status, error = conn.execute("SELECT status, error FROM importer_runs").fetchone()
    assert status == "failed" and "no page" in error


def test_sec_requires_a_user_agent():
    try:
        Http(user_agent=None)._agent_for("www.sec.gov")
    except FetchError as e:
        assert "SEC_USER_AGENT" in str(e)
    else:
        raise AssertionError("expected FetchError")
    assert "Mozilla" in Http()._agent_for("www.njeda.gov")


def test_raw_payload_hash(tmp_path):
    p = Path(tmp_path / "a.txt")
    p.write_text("abc")
    assert RawPayload("a", "https://x.test", p).sha256().startswith("ba7816bf")
