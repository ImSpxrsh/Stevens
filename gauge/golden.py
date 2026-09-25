"""Golden path: run the whole pipeline on the fixture dataset and compare it
with the reviewed expected output.

    python -m gauge.golden             # check; exits 1 and prints a diff on mismatch
    python -m gauge.golden --update    # rewrite fixtures/golden/expected.json (review the diff!)
    python -m gauge.golden --output data/local/golden.json   # snapshot for the demo UI

The fixtures (fixtures/golden/records.json) are fictional companies covering a
Form D company, an SBIR/STTR company, a merged company, a hard exclusion, a
fuzzy match waiting for review, and an uncertain classification.
"""

from __future__ import annotations

import argparse
import difflib
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from gauge.core.serialize import load_records
from gauge.pipeline import PipelineOutput, run
from gauge.review.store import ReviewStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
RECORDS = FIXTURES / "records.json"
EXPECTED = FIXTURES / "expected.json"
AS_OF = date(2026, 9, 1)


def run_golden(records_path: Path = RECORDS) -> tuple[PipelineOutput, ReviewStore]:
    store = ReviewStore()  # fresh queue: the golden path starts with no decisions
    return run(load_records(records_path), AS_OF, store), store


def snapshot(out: PipelineOutput, store: ReviewStore) -> dict[str, Any]:
    """A stable, JSON-ready view of everything the golden path checks."""
    companies: dict[str, Any] = {}
    for cid, profile in sorted(out.profiles.items()):
        c = out.classifications[cid]
        card = out.evidence_cards[cid]
        companies[cid] = {
            "name": profile.name,
            "records": sorted(r.key for r in profile.records),
            "classification": {
                "label": c.label.value,
                "probability": None if c.probability is None else round(c.probability, 3),
                "exclusion": c.exclusion.reason.value if c.exclusion else None,
                "top_features": [f.name for f in c.top_features],
            },
            "programs": {
                pid: {
                    "result": m.result.value,
                    "rules_version": m.rules_version,
                    "verification_questions": list(m.verification_questions),
                }
                for pid, m in out.program_matches.get(cid, {}).items()
            },
            "evidence_card": {
                kind: [
                    f"{i.claim}: {i.value}" if i.value and kind == "fact" else i.claim
                    for i in card
                    if i.kind.value == kind
                ]
                for kind in ("fact", "inferred", "unknown")
            },
        }
    discoverable = {c.company_id for c in (*out.discovery.ranked, *out.discovery.uncertain)}
    return {
        "as_of": out.as_of.isoformat(),
        "companies": companies,
        "discovery": {
            "ranked": [c.company_id for c in out.discovery.ranked],
            "uncertain": [c.company_id for c in out.discovery.uncertain],
            "excluded": sorted(c.company_id for c in out.discovery.excluded),
            "not_startup": [c.company_id for c in out.discovery.not_startup],
        },
        "review_queue": [
            {
                "kind": i.kind.value,
                "subject": i.subject,
                "candidate": i.candidate_company_id,
                "status": i.status.value,
                "score": round(i.score, 3),
            }
            for i in store.items()
        ],
        # Excluded and not-a-startup companies never produce alerts.
        "alerts": [
            {"record": a.record_key, "company_id": a.company_id, "gate": a.gate.value}
            for a in out.alerts
            if a.company_id in discoverable
        ],
    }


def _dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gauge.golden")
    parser.add_argument("--update", action="store_true", help="rewrite expected.json")
    parser.add_argument("--output", help="also write the snapshot to this path")
    args = parser.parse_args(argv)

    actual = _dumps(snapshot(*run_golden()))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(actual)
    if args.update:
        EXPECTED.write_text(actual)
        print(f"wrote {EXPECTED}")
        return 0
    expected = EXPECTED.read_text()
    if actual == expected:
        print("golden path OK")
        return 0
    diff = difflib.unified_diff(
        expected.splitlines(), actual.splitlines(), "expected", "actual", lineterm=""
    )
    print("\n".join(diff))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
