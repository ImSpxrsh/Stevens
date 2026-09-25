from datetime import date

import pytest

from gauge.core.models import Address
from gauge.golden import RECORDS, run_golden
from gauge.pipeline import run
from gauge.review.store import ReviewStore
from gauge.validation.coverage import (
    MIN_REFERENCE_SIZE,
    Outcome,
    ReferenceCompany,
    audit,
    load_reference,
    main,
    to_markdown,
)
from tests.factories import form_d


def ref(name, town="", sector="software", source="test list"):
    return ReferenceCompany(name, town, sector, source)


@pytest.fixture(scope="module")
def golden():
    out, _ = run_golden()
    return out


def outcomes(report):
    return {r.reference.name: r.outcome for r in report.rows}


def test_outcomes_on_golden_fixtures(golden):
    report = audit(
        [
            ref("Halyard Sensors"),
            ref("Pinewood Therapeutics, Inc.", sector="life sciences"),
            ref("Old Mill Instruments", sector="hardware"),
            ref("Garden State Opportunity Fund II LP", sector="fintech"),
            ref("Lumen Grid Systems", sector="climate"),
            ref("Lumen Grid Systems", town="Trenton", sector="climate"),
            ref("Nonexistent Robotics", sector="hardware"),
            ref("Northbeam Analytic", sector="software"),  # typo: strict fuzzy match
        ],
        golden,
    )
    got = [r.outcome for r in report.rows]
    assert got == [
        Outcome.FOUND,
        Outcome.FOUND,
        Outcome.FOUND_UNCERTAIN,
        Outcome.EXCLUDED,
        Outcome.AMBIGUOUS,
        Outcome.FOUND,
        Outcome.NO_PUBLIC_SIGNAL,
        Outcome.FOUND,
    ]
    assert report.rows[5].company_id == "cik:0009000005"
    assert report.rows[7].match.startswith("fuzzy")
    assert report.found == 5
    assert report.by_sector()["climate"] == (1, 2)
    assert report.misses()[Outcome.NO_PUBLIC_SIGNAL] == 1


def test_out_of_state_and_classified_not_startup():
    records = [
        form_d(
            "Keystone Labs Inc", cik="0005000001", address=Address(city="Philadelphia", state="PA")
        ),
        form_d(
            "Old Line Tooling Co",
            cik="0005000002",
            incorporated_within_five_years=False,
            revenue_range="$5,000,001 - $25,000,000",
            industry_group="Manufacturing",
            filed=date(2019, 1, 1),
        ),
    ]
    out = run(records, date(2026, 9, 1), ReviewStore())
    report = audit([ref("Keystone Labs"), ref("Old Line Tooling")], out)
    assert outcomes(report) == {
        "Keystone Labs": Outcome.OUT_OF_STATE,
        "Old Line Tooling": Outcome.CLASSIFIED_NOT_STARTUP,
    }


def test_small_or_unsourced_lists_are_a_pilot_step(golden):
    small = audit([ref("Halyard Sensors")], golden)
    assert not small.is_proof_number
    assert "Pilot step, not a proof number" in to_markdown(small)
    big = audit([ref("Halyard Sensors")] * MIN_REFERENCE_SIZE, golden)
    assert big.is_proof_number
    unsourced = audit([ref("Halyard Sensors", source="")] * MIN_REFERENCE_SIZE, golden)
    assert not unsourced.is_proof_number


def test_report_explains_misses_by_category(golden):
    text = to_markdown(audit([ref("Nonexistent Robotics"), ref("Halyard Sensors")], golden))
    assert "## By sector" in text and "no_public_signal" in text and "source blind spot" in text


def test_cli_and_template(tmp_path, capsys):
    path = tmp_path / "ref.csv"
    path.write_text("name,town,sector,source\nHalyard Sensors,Hoboken,hardware,demo\n,,,\n")
    assert len(load_reference(path)) == 1
    csv_out = tmp_path / "out.csv"
    assert main([str(RECORDS), str(path), "--as-of", "2026-09-01", "--csv", str(csv_out)]) == 0
    assert "found" in csv_out.read_text()
    assert "Coverage audit" in capsys.readouterr().out
