"""One command for teammates: `pytest tests/test_golden_path.py` or `python -m gauge.golden`."""

import json

from gauge.golden import EXPECTED, main, run_golden, snapshot


def test_golden_path_matches_reviewed_expected_output(capsys):
    assert main([]) == 0, capsys.readouterr().out


def test_fixtures_cover_success_exclusion_uncertainty_and_review():
    out, store = run_golden()
    snap = snapshot(out, store)
    companies = snap["companies"]

    merged = companies["cik:0009000003"]
    assert {r.split(":")[0] for r in merged["records"]} == {"sec_form_d", "sbir_sttr"}

    assert snap["discovery"]["excluded"] == ["cik:0009000004"]
    assert companies["cik:0009000004"]["classification"]["exclusion"] == "fund"
    assert snap["discovery"]["uncertain"] == ["rec:sbir_sttr:SBIR-FIXTURE-0006"]
    assert [i["status"] for i in snap["review_queue"]] == ["open"]

    results = {m["result"] for c in companies.values() for m in c["programs"].values()}
    assert results == {"strong_match", "potential_match_verify", "not_a_match"}

    gates = {a["gate"] for a in snap["alerts"]}
    assert gates == {"automatic", "hold_for_review"}
    assert not any(a["company_id"] == "cik:0009000004" for a in snap["alerts"])


def test_snapshot_can_be_written_for_the_demo_ui(tmp_path):
    target = tmp_path / "golden.json"
    assert main(["--output", str(target)]) == 0
    assert json.loads(target.read_text()) == json.loads(EXPECTED.read_text())
