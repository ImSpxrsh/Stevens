import csv
import zipfile
from datetime import date

from gauge.core.models import SbirPhase
from gauge.core.serialize import load_records
from gauge.sources import build, formd, sbir

SUB = ["ACCESSIONNUMBER", "FILING_DATE", "SUBMISSIONTYPE", "TESTORLIVE"]
ISS = [
    "ACCESSIONNUMBER",
    "IS_PRIMARYISSUER_FLAG",
    "CIK",
    "ENTITYNAME",
    "STREET1",
    "STREET2",
    "CITY",
    "STATEORCOUNTRY",
    "ZIPCODE",
    "JURISDICTIONOFINC",
    "ENTITYTYPE",
    "YEAROFINC_TIMESPAN_CHOICE",
    "YEAROFINC_VALUE_ENTERED",
]
OFF = [
    "ACCESSIONNUMBER",
    "INDUSTRYGROUPTYPE",
    "INVESTMENTFUNDTYPE",
    "REVENUERANGE",
    "ISAMENDMENT",
    "SALE_DATE",
    "ISEQUITYTYPE",
    "ISDEBTTYPE",
    "ISPOOLEDINVESTMENTFUNDTYPE",
    "TOTALOFFERINGAMOUNT",
    "TOTALAMOUNTSOLD",
]


def tsv(rows, cols):
    return (
        "\n".join(["\t".join(cols)] + ["\t".join(r.get(c, "") for c in cols) for r in rows]) + "\n"
    )


def write_quarter(path, filing_date="31-MAR-2022"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "2022Q1_d/FORMDSUBMISSION.tsv",
            tsv(
                [
                    {
                        "ACCESSIONNUMBER": "0001-22-000001",
                        "FILING_DATE": filing_date,
                        "TESTORLIVE": "LIVE",
                    },
                    {
                        "ACCESSIONNUMBER": "0002-22-000001",
                        "FILING_DATE": filing_date,
                        "TESTORLIVE": "LIVE",
                    },
                    {
                        "ACCESSIONNUMBER": "0003-22-000001",
                        "FILING_DATE": filing_date,
                        "TESTORLIVE": "TEST",
                    },
                ],
                SUB,
            ),
        )
        z.writestr(
            "2022Q1_d/ISSUERS.tsv",
            tsv(
                [
                    {
                        "ACCESSIONNUMBER": "0001-22-000001",
                        "IS_PRIMARYISSUER_FLAG": "YES",
                        "CIK": "1234",
                        "ENTITYNAME": "Halyard Sensors, Inc.",
                        "STREET1": "1 River St",
                        "CITY": "HOBOKEN",
                        "STATEORCOUNTRY": "NJ",
                        "ZIPCODE": "07030",
                        "ENTITYTYPE": "Corporation",
                        "YEAROFINC_TIMESPAN_CHOICE": "withinFiveYears",
                        "YEAROFINC_VALUE_ENTERED": "2021",
                    },
                    {
                        "ACCESSIONNUMBER": "0002-22-000001",
                        "IS_PRIMARYISSUER_FLAG": "YES",
                        "CIK": "5678",
                        "ENTITYNAME": "Keystone Labs",
                        "STATEORCOUNTRY": "PA",
                    },
                    {
                        "ACCESSIONNUMBER": "0003-22-000001",
                        "IS_PRIMARYISSUER_FLAG": "YES",
                        "CIK": "9",
                        "ENTITYNAME": "Test Filing",
                        "STATEORCOUNTRY": "NJ",
                    },
                ],
                ISS,
            ),
        )
        z.writestr(
            "2022Q1_d/OFFERING.tsv",
            tsv(
                [
                    {
                        "ACCESSIONNUMBER": "0001-22-000001",
                        "INDUSTRYGROUPTYPE": "Other Technology",
                        "REVENUERANGE": "No Revenues",
                        "ISAMENDMENT": "false",
                        "SALE_DATE": "2022-02-01",
                        "ISEQUITYTYPE": "true",
                        "TOTALOFFERINGAMOUNT": "Indefinite",
                        "TOTALAMOUNTSOLD": "500000",
                    },
                    {"ACCESSIONNUMBER": "0002-22-000001", "INDUSTRYGROUPTYPE": "Other"},
                    {"ACCESSIONNUMBER": "0003-22-000001", "INDUSTRYGROUPTYPE": "Other"},
                ],
                OFF,
            ),
        )


def test_form_d_quarter_keeps_live_filings_from_requested_state(tmp_path):
    write_quarter(tmp_path / "2022q1_d.zip")
    (rec,) = formd.read_quarter(tmp_path / "2022q1_d.zip")
    assert rec.name == "Halyard Sensors, Inc." and rec.cik == "0000001234"
    assert rec.source_date == date(2022, 3, 31)
    assert (
        rec.provenance.source_url == "https://www.sec.gov/Archives/edgar/data/1234/000122000001/"
    )
    assert rec.address.city == "Hoboken" and rec.address.postal_code == "07030"
    fd = rec.form_d
    assert fd.total_offering_amount is None and fd.total_amount_sold == 500_000
    assert fd.incorporated_within_five_years is True and fd.year_of_incorporation == 2021
    assert fd.securities_offered == ("Equity",) and fd.date_of_first_sale == date(2022, 2, 1)


def test_form_d_older_date_format_and_directory_dedupe(tmp_path):
    write_quarter(tmp_path / "2019q2_d.zip", filing_date="2019-06-28 17:30:19")
    write_quarter(tmp_path / "2019q3_d.zip", filing_date="2019-06-28 17:30:19")
    (rec,) = formd.read_directory(tmp_path)
    assert rec.source_date == date(2019, 6, 28)


SBIR_COLS = list(sbir.COLUMNS) + [
    "Contact Name",
    "Contact Email",
    "PI Name",
    "PI Email",
    "PI Phone",
]


def write_sbir(path):
    rows = [
        {
            "Company": "Pinewood Therapeutics LLC",
            "Award Title": "RNA therapeutics",
            "Agency": "Department of Health and Human Services",
            "Phase": "Phase II",
            "Program": "SBIR",
            "Agency Tracking Number": "R44CA1",
            "Contract": "R44CA000001",
            "Proposal Award Date": "03/01/2023",
            "Contract End Date": "02/28/2025",
            "Award Year": "2023",
            "Award Amount": "1,500,000",
            "Number Employees": "8",
            "City": "PRINCETON",
            "State": "NJ",
            "Zip": "08540",
            "Abstract": "x" * 5000,
            "Contact Name": "Jane Private",
            "Contact Email": "jane@private.test",
            "PI Name": "Pat Private",
            "PI Email": "pat@private.test",
            "PI Phone": "(555) 010-0000",
        },
        {
            "Company": "Elsewhere Inc",
            "Phase": "Phase I",
            "State": "CA",
            "Proposal Award Date": "01/01/2023",
        },
        {
            "Company": "Year Only Co",
            "Phase": "Phase I",
            "State": "NJ",
            "Award Year": "2019",
            "Agency": "National Science Foundation",
        },
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SBIR_COLS)
        w.writeheader()
        w.writerows(rows)


def test_sbir_awards_are_normalized_and_contact_data_never_read(tmp_path):
    write_sbir(tmp_path / "awards.csv")
    recs = sbir.read_awards(tmp_path / "awards.csv")
    assert [r.name for r in recs] == ["Year Only Co", "Pinewood Therapeutics LLC"]
    year_only, rec = recs
    assert year_only.source_date == date(2019, 1, 1) and year_only.sbir.agency == "NSF"
    s = rec.sbir
    assert s.phase is SbirPhase.PHASE_II and s.agency == "HHS" and s.award_amount == 1_500_000
    assert s.award_end == date(2025, 2, 28) and s.employee_count == 8
    assert len(s.abstract) == sbir.ABSTRACT_LIMIT
    assert "private" not in repr(rec).lower()


def test_build_writes_a_records_file(tmp_path, capsys):
    (tmp_path / "formd").mkdir()
    write_quarter(tmp_path / "formd" / "2022q1_d.zip")
    write_sbir(tmp_path / "awards.csv")
    out = tmp_path / "records.json"
    assert (
        build.main(
            [
                "--formd-dir",
                str(tmp_path / "formd"),
                "--sbir-csv",
                str(tmp_path / "awards.csv"),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert len(load_records(out)) == 3
    assert "private" not in out.read_text().lower()
