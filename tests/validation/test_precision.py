import csv

import pytest

from gauge.classifier import fit
from gauge.golden import run_golden
from gauge.validation.precision import (
    SHEET_COLUMNS,
    SampleManifest,
    draw_sample,
    main,
    read_labels,
    score,
    to_markdown,
    training_rows,
    write_labeling_sheet,
)
from gauge.validation.stats import fmt_rate, wilson_interval


@pytest.fixture(scope="module")
def golden():
    out, _ = run_golden()
    return out


def label_all(manifest, mapping):
    return {
        r.sample_id: {"label": mapping(r), "notes": f"note {r.sample_id}"} for r in manifest.rows
    }


def test_sample_is_seeded_and_limited_to_likely_predictions(golden):
    a = draw_sample(golden, n=3, seed=7)
    b = draw_sample(golden, n=3, seed=7)
    assert [r.company_id for r in a.rows] == [r.company_id for r in b.rows]
    assert {r.predicted_label for r in a.rows} == {"likely_startup"}
    assert a.population_size == len(golden.discovery.ranked)
    assert [r.sample_id for r in a.rows] == ["S001", "S002", "S003"]
    assert len(draw_sample(golden, n=100).rows) == len(golden.discovery.ranked)
    assert draw_sample(golden, population="all").population_size == len(golden.classifications)


def test_labeling_sheet_is_blind(golden, tmp_path):
    manifest = draw_sample(golden, n=100)
    path = tmp_path / "sheet.csv"
    write_labeling_sheet(manifest, golden, path)
    text = path.read_text()
    assert "likely_startup" not in text and "probability" not in text
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert tuple(rows[0]) == SHEET_COLUMNS
    assert all(r["label"] == "" for r in rows)
    assert all("https://" in r["public_records"] for r in rows)


def test_manifest_round_trips(golden, tmp_path):
    manifest = draw_sample(golden, n=2)
    manifest.save(tmp_path / "m.json")
    assert SampleManifest.load(tmp_path / "m.json") == manifest


def test_precision_counts_uncertain_separately_and_lists_false_positives(golden):
    manifest = draw_sample(golden, n=100)
    labels = label_all(manifest, lambda r: "likely_startup")
    ids = [r.sample_id for r in manifest.rows]
    labels[ids[0]]["label"] = "not_startup"
    labels[ids[1]]["label"] = "uncertain"
    report = score(manifest, labels)
    assert report.true_positives == len(ids) - 2
    assert report.false_positives == 1 and report.human_uncertain == 1
    assert report.precision == pytest.approx((len(ids) - 2) / (len(ids) - 1))
    (fp,) = report.false_positive_rows
    assert fp.sample_id == ids[0] and fp.notes == f"note {ids[0]}"
    md = to_markdown(report)
    assert "Precision for likely startup" in md and "incomplete" not in md


def test_unlabeled_rows_block_a_quotable_number(golden):
    manifest = draw_sample(golden, n=100)
    report = score(manifest, {})
    assert report.precision is None and len(report.unlabeled) == len(manifest.rows)
    assert "do not quote" in to_markdown(report)


def test_invalid_labels_are_rejected(tmp_path):
    path = tmp_path / "l.csv"
    path.write_text("sample_id,label\nS001,maybe\n")
    with pytest.raises(ValueError, match="maybe"):
        read_labels(path)


def test_labels_feed_back_into_the_classifier(golden):
    manifest = draw_sample(golden, n=100, population="all")
    labels = label_all(
        manifest, lambda r: "not_startup" if r.features["sbir_phase_i"] else "likely_startup"
    )
    rows, ys = training_rows(manifest, labels)
    assert len(rows) == len(ys) == len(manifest.rows)
    refit = fit(rows, ys, version="refit-from-labels", epochs=300)
    assert refit.version == "refit-from-labels"


def test_wilson_interval():
    assert wilson_interval(0, 0) is None
    lo, hi = wilson_interval(72, 100)
    assert 0.62 < lo < 0.64 and 0.79 < hi < 0.81
    assert fmt_rate(72, 100) == "72% (95% CI 63%-80%, n=100)"


def test_cli_sample_then_score(tmp_path, capsys):
    from gauge.golden import RECORDS

    out_dir = tmp_path / "precision"
    assert main(["sample", str(RECORDS), "--as-of", "2026-09-01", "--out-dir", str(out_dir)]) == 0
    sheet = out_dir / "labeling_sheet.csv"
    with open(sheet, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["label"], r["labeler"] = "likely_startup", "Sam"
    with open(sheet, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    capsys.readouterr()
    assert main(["score", str(out_dir / "manifest.json"), str(sheet)]) == 0
    assert f"{len(rows)} of {len(rows)} were startups" in capsys.readouterr().out
