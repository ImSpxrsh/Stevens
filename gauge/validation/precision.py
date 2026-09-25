"""Proof number 2: how often the "likely startup" label is right.

1. ``sample`` draws a seeded random sample of companies from pipeline output
   and writes a *blind* labeling sheet (no model label or score on it) plus a
   manifest that keeps the predictions for scoring.
2. People label each row ``likely_startup``, ``not_startup``, or
   ``uncertain`` following docs/validation/labeling-guidelines.md.
3. ``score`` computes precision for the likely-startup class with a Wilson
   95% interval, lists false positives with the features that drove them,
   and ``training_rows`` turns the labels into data for ``classifier.fit``.

    python -m gauge.validation.precision sample RECORDS.json --as-of 2026-09-25 \\
        --out-dir data/local/precision [--n 100] [--seed 2026] [--population likely|all]
    python -m gauge.validation.precision score data/local/precision/manifest.json \\
        data/local/precision/labeling_sheet.csv [--out report.md]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from gauge.classifier import StartupLabel
from gauge.classifier.features import extract_features
from gauge.pipeline import PipelineOutput
from gauge.validation.stats import fmt_rate, wilson_interval

LABELS = tuple(label.value for label in StartupLabel)
SHEET_COLUMNS = (
    "sample_id",
    "company_name",
    "towns",
    "sec_company_ids",
    "public_records",
    "form_d_summary",
    "sbir_summary",
    "label",
    "labeler",
    "notes",
)


@dataclass(frozen=True)
class SampleRow:
    sample_id: str
    company_id: str
    predicted_label: str
    probability: float | None
    top_features: list[str]
    features: dict[str, float]


@dataclass(frozen=True)
class SampleManifest:
    as_of: str
    seed: int
    population: str
    population_size: int
    model_version: str
    rows: list[SampleRow] = field(default_factory=list)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> SampleManifest:
        d = json.loads(Path(path).read_text())
        d["rows"] = [SampleRow(**r) for r in d["rows"]]
        return cls(**d)


def draw_sample(
    out: PipelineOutput, *, n: int = 100, seed: int = 2026, population: str = "likely"
) -> SampleManifest:
    """Seeded random sample. ``likely`` samples the likely-startup predictions
    (what precision needs); ``all`` samples every classified company."""
    if population == "likely":
        pool = sorted(c.company_id for c in out.discovery.ranked)
    elif population == "all":
        pool = sorted(out.classifications)
    else:
        raise ValueError(f"unknown population {population!r}")
    chosen = random.Random(seed).sample(pool, min(n, len(pool)))
    rows = []
    for i, cid in enumerate(chosen, start=1):
        c = out.classifications[cid]
        rows.append(
            SampleRow(
                sample_id=f"S{i:03d}",
                company_id=cid,
                predicted_label=c.label.value,
                probability=c.probability,
                top_features=[f.name for f in c.top_features],
                features=extract_features(out.profiles[cid], out.as_of).values,
            )
        )
    model_versions = {c.model_version for c in out.classifications.values()}
    return SampleManifest(
        as_of=out.as_of.isoformat(),
        seed=seed,
        population=population,
        population_size=len(pool),
        model_version=",".join(sorted(model_versions)),
        rows=rows,
    )


def write_labeling_sheet(manifest: SampleManifest, out: PipelineOutput, path: str | Path) -> None:
    """Blind sheet: public facts and links only, never the model's label or score."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        for row in manifest.rows:
            p = out.profiles[row.company_id]
            records = sorted(p.records, key=lambda r: r.source_date)
            form_ds = [r for r in records if r.form_d]
            awards = [r for r in records if r.sbir]
            w.writerow(
                {
                    "sample_id": row.sample_id,
                    "company_name": p.name,
                    "towns": "; ".join(
                        sorted(
                            {
                                f"{r.address.city}, {r.address.state}"
                                for r in records
                                if r.address and r.address.city
                            }
                        )  # fmt: skip
                    ),
                    "sec_company_ids": "; ".join(sorted(p.ciks)),
                    "public_records": "\n".join(
                        f"{r.provenance.source_type.value} {r.source_date} "
                        f"{r.provenance.source_url}"
                        for r in records
                    ),
                    "form_d_summary": "\n".join(
                        f"{r.source_date}: {r.form_d.industry_group}; revenue "
                        f"{r.form_d.revenue_range}; incorporated {r.form_d.year_of_incorporation}"
                        for r in form_ds
                        if r.form_d
                    ),
                    "sbir_summary": "\n".join(
                        f"{r.source_date}: {r.sbir.agency} {r.sbir.program} {r.sbir.phase.value}; "
                        f"{r.sbir.topic_title}; employees {r.sbir.employee_count}"
                        for r in awards
                        if r.sbir
                    ),
                    "label": "",
                    "labeler": "",
                    "notes": "",
                }
            )


def read_labels(path: str | Path) -> dict[str, dict[str, str]]:
    with open(path, newline="") as f:
        rows = {r["sample_id"]: r for r in csv.DictReader(f)}
    for sid, r in rows.items():
        label = r.get("label", "").strip().lower()
        if label and label not in LABELS:
            raise ValueError(f"{sid}: label {label!r} is not one of {LABELS}")
        r["label"] = label
    return rows


@dataclass(frozen=True)
class FalsePositive:
    sample_id: str
    company_id: str
    top_features: list[str]
    notes: str


@dataclass(frozen=True)
class PrecisionReport:
    manifest: SampleManifest
    true_positives: int
    false_positives: int
    human_uncertain: int
    unlabeled: list[str]
    confusion: dict[str, dict[str, int]]  # predicted -> human -> count
    false_positive_rows: list[FalsePositive]

    @property
    def precision(self) -> float | None:
        judged = self.true_positives + self.false_positives
        return self.true_positives / judged if judged else None

    @property
    def interval(self) -> tuple[float, float] | None:
        return wilson_interval(self.true_positives, self.true_positives + self.false_positives)

    @property
    def false_positive_feature_counts(self) -> Counter[str]:
        return Counter(f for fp in self.false_positive_rows for f in fp.top_features)


def score(manifest: SampleManifest, labels: dict[str, dict[str, str]]) -> PrecisionReport:
    tp = fp = uncertain = 0
    unlabeled: list[str] = []
    confusion: dict[str, dict[str, int]] = {p: dict.fromkeys(LABELS, 0) for p in LABELS}
    fps: list[FalsePositive] = []
    for row in manifest.rows:
        human = labels.get(row.sample_id, {}).get("label", "")
        if not human:
            unlabeled.append(row.sample_id)
            continue
        confusion[row.predicted_label][human] += 1
        if row.predicted_label != StartupLabel.LIKELY_STARTUP.value:
            continue
        if human == StartupLabel.LIKELY_STARTUP.value:
            tp += 1
        elif human == StartupLabel.NOT_STARTUP.value:
            fp += 1
            notes = labels[row.sample_id].get("notes", "").strip()
            fps.append(FalsePositive(row.sample_id, row.company_id, row.top_features, notes))
        else:
            uncertain += 1
    return PrecisionReport(manifest, tp, fp, uncertain, unlabeled, confusion, fps)


def training_rows(
    manifest: SampleManifest, labels: dict[str, dict[str, str]]
) -> tuple[list[dict[str, float]], list[int]]:
    """Definitive human labels as (features, 0/1) rows for ``gauge.classifier.fit``."""
    rows, ys = [], []
    for row in manifest.rows:
        human = labels.get(row.sample_id, {}).get("label", "")
        if human == StartupLabel.LIKELY_STARTUP.value:
            rows.append(row.features)
            ys.append(1)
        elif human == StartupLabel.NOT_STARTUP.value:
            rows.append(row.features)
            ys.append(0)
    return rows, ys


def to_markdown(report: PrecisionReport) -> str:
    m = report.manifest
    judged = report.true_positives + report.false_positives
    lines = [
        "# Classifier precision check",
        "",
        f"- Sample: {len(m.rows)} of {m.population_size} companies "
        f"(population `{m.population}`, seed {m.seed}, as of {m.as_of}, model {m.model_version})",
        f"- **Precision for likely startup: {fmt_rate(report.true_positives, judged)}**",
        f"- Labeled uncertain by reviewers (excluded from precision): {report.human_uncertain}",
        f"- Unlabeled rows: {len(report.unlabeled)}",
        "",
    ]
    if report.unlabeled:
        lines += ["> Labeling is incomplete; do not quote this number yet.", ""]
    lines += [
        "Proof-slide wording: of the companies Gauge labeled *likely startup* in a random "
        f"sample, {report.true_positives} of {judged} were startups on manual review.",
        "",
        "## Confusion (rows: model, columns: reviewer)",
        "",
        "| model \\ reviewer | " + " | ".join(LABELS) + " |",
        "|---|" + "---:|" * len(LABELS),
    ]
    for pred, counts in report.confusion.items():
        lines.append(f"| {pred} | " + " | ".join(str(counts[h]) for h in LABELS) + " |")
    lines += ["", "## False positives", ""]
    if not report.false_positive_rows:
        lines.append("None.")
    for fp in report.false_positive_rows:
        lines.append(
            f"- {fp.sample_id} `{fp.company_id}`: top features {', '.join(fp.top_features)}"
            + (f"; notes: {fp.notes}" if fp.notes else "")
        )
    common = report.false_positive_feature_counts.most_common(5)
    if common:
        lines += ["", "Most common features among false positives: "
                  + ", ".join(f"{name} ({n})" for name, n in common)]  # fmt: skip
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    from gauge.core.serialize import load_records
    from gauge.pipeline import run
    from gauge.review.store import JsonReviewStore, ReviewStore

    parser = argparse.ArgumentParser(prog="gauge.validation.precision")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sample")
    s.add_argument("records")
    s.add_argument("--as-of", required=True, type=date.fromisoformat)
    s.add_argument("--out-dir", required=True)
    s.add_argument("--n", type=int, default=100)
    s.add_argument("--seed", type=int, default=2026)
    s.add_argument("--population", choices=["likely", "all"], default="likely")
    s.add_argument("--store", help="review queue JSON (applies merge decisions)")
    sc = sub.add_parser("score")
    sc.add_argument("manifest")
    sc.add_argument("labels")
    sc.add_argument("--out")
    args = parser.parse_args(argv)

    if args.command == "sample":
        store = JsonReviewStore(args.store) if args.store else ReviewStore()
        out = run(load_records(args.records), args.as_of, store)
        manifest = draw_sample(out, n=args.n, seed=args.seed, population=args.population)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest.save(out_dir / "manifest.json")
        write_labeling_sheet(manifest, out, out_dir / "labeling_sheet.csv")
        print(f"sampled {len(manifest.rows)} of {manifest.population_size} -> {out_dir}")
        return 0

    report = score(SampleManifest.load(args.manifest), read_labels(args.labels))
    text = to_markdown(report)
    if args.out:
        Path(args.out).write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
