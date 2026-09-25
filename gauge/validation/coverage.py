"""Proof number 3 (stretch): what share of known NJ startups does Gauge find?

Each company on a reference list is matched to a Gauge profile by name
(exact normalized match first, then a strict fuzzy match, using town to break
ties) and given one outcome:

* ``found``: in the discovery list (likely startup)
* ``found_uncertain``: found but held in the uncertain list for review
* ``excluded``: found but removed by a hard exclusion rule
* ``classified_not_startup``: found but the model scored it not a startup
* ``out_of_state``: found but no linked record has an NJ address
* ``ambiguous``: several profiles match and the town does not settle it
* ``no_public_signal``: no Form D or SBIR/STTR record in Gauge's data (a
  source blind spot, not a classifier error)

    python -m gauge.validation.coverage RECORDS.json REFERENCE.csv --as-of 2026-09-25 \\
        [--out report.md] [--csv results.csv]
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

from gauge.classifier import StartupLabel
from gauge.core.names import name_similarity, normalize_company_name, normalize_town
from gauge.pipeline import PipelineOutput
from gauge.validation.stats import fmt_rate

FUZZY_MATCH_THRESHOLD = 0.92
# Below this many reference companies, present coverage as a pilot step, not a proof number.
MIN_REFERENCE_SIZE = 30


class Outcome(StrEnum):
    FOUND = "found"
    FOUND_UNCERTAIN = "found_uncertain"
    EXCLUDED = "excluded"
    CLASSIFIED_NOT_STARTUP = "classified_not_startup"
    OUT_OF_STATE = "out_of_state"
    AMBIGUOUS = "ambiguous"
    NO_PUBLIC_SIGNAL = "no_public_signal"


FOUND_OUTCOMES = (Outcome.FOUND, Outcome.FOUND_UNCERTAIN)

MISS_EXPLANATIONS = {
    Outcome.EXCLUDED: "Found, but a hard exclusion rule removed it; check the rule.",
    Outcome.CLASSIFIED_NOT_STARTUP: "Found, but scored not a startup; a classifier false negative.",
    Outcome.OUT_OF_STATE: "Found, but no linked record lists an NJ address.",
    Outcome.AMBIGUOUS: "Several companies share the name; the match could not be settled.",
    Outcome.NO_PUBLIC_SIGNAL: "No Form D or SBIR/STTR record: a source blind spot (e.g. "
    "raised on SAFEs without filing, bootstrapped, or grant-funded outside SBIR).",
}


@dataclass(frozen=True)
class ReferenceCompany:
    name: str
    town: str
    sector: str
    source: str


@dataclass(frozen=True)
class CoverageRow:
    reference: ReferenceCompany
    outcome: Outcome
    company_id: str | None
    match: str  # "exact", "fuzzy 0.95", or ""
    detail: str


@dataclass(frozen=True)
class CoverageReport:
    as_of: date
    rows: tuple[CoverageRow, ...]

    @property
    def found(self) -> int:
        return sum(r.outcome in FOUND_OUTCOMES for r in self.rows)

    def by_sector(self) -> dict[str, tuple[int, int]]:
        totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for r in self.rows:
            t = totals[r.reference.sector or "unspecified"]
            t[1] += 1
            t[0] += r.outcome in FOUND_OUTCOMES
        return {s: (f, n) for s, (f, n) in sorted(totals.items())}

    def misses(self) -> Counter[Outcome]:
        return Counter(r.outcome for r in self.rows if r.outcome not in FOUND_OUTCOMES)

    @property
    def is_proof_number(self) -> bool:
        return len(self.rows) >= MIN_REFERENCE_SIZE and all(r.reference.source for r in self.rows)


def load_reference(path: str | Path) -> list[ReferenceCompany]:
    with open(path, newline="") as f:
        return [
            ReferenceCompany(
                name=row["name"].strip(),
                town=row.get("town", "").strip(),
                sector=row.get("sector", "").strip(),
                source=row.get("source", "").strip(),
            )
            for row in csv.DictReader(f)
            if row.get("name", "").strip()
        ]


def audit(reference: Sequence[ReferenceCompany], out: PipelineOutput) -> CoverageReport:
    names: dict[str, list[str]] = defaultdict(list)  # normalized record name -> company ids
    for cid, p in out.profiles.items():
        for n in {normalize_company_name(r.name) for r in p.records} | {
            normalize_company_name(p.name)
        }:
            names[n].append(cid)
    return CoverageReport(out.as_of, tuple(_audit_one(ref, out, names) for ref in reference))


def _towns(out: PipelineOutput, cid: str) -> set[str]:
    return {
        normalize_town(r.address.city)
        for r in out.profiles[cid].records
        if r.address and r.address.city
    }


def _audit_one(
    ref: ReferenceCompany, out: PipelineOutput, names: dict[str, list[str]]
) -> CoverageRow:
    norm = normalize_company_name(ref.name)
    candidates = sorted(set(names.get(norm, [])))
    how = "exact"
    if not candidates:
        # "JOGO Health" vs "JogoHealth, Inc.": the same name once spaces are ignored.
        compact = norm.replace(" ", "")
        candidates = sorted(
            {c for n, cids in names.items() if n.replace(" ", "") == compact for c in cids}
        )
        how = "exact (ignoring spaces)"
    if not candidates:
        scored = [(name_similarity(ref.name, n), cid) for n, cids in names.items() for cid in cids]
        best = max((s for s, _ in scored), default=0.0)
        if best >= FUZZY_MATCH_THRESHOLD:
            candidates = sorted({cid for s, cid in scored if s == best})
            how = f"fuzzy {best:.2f}"
    if not candidates:
        detail = MISS_EXPLANATIONS[Outcome.NO_PUBLIC_SIGNAL]
        hints = _legal_name_hints(norm, out, names)
        if hints:
            detail += " Check by hand, possible legal names: " + "; ".join(hints)
        return CoverageRow(ref, Outcome.NO_PUBLIC_SIGNAL, None, "", detail)
    if len(candidates) > 1 and ref.town:
        in_town = [c for c in candidates if normalize_town(ref.town) in _towns(out, c)]
        candidates = in_town or candidates
    if len(candidates) > 1:
        return CoverageRow(
            ref, Outcome.AMBIGUOUS, None, how, f"Candidates: {', '.join(candidates)}"
        )

    cid = candidates[0]
    c = out.classifications[cid]
    if not out.profiles[cid].has_new_jersey_address():
        outcome, detail = Outcome.OUT_OF_STATE, MISS_EXPLANATIONS[Outcome.OUT_OF_STATE]
    elif c.exclusion is not None:
        outcome, detail = Outcome.EXCLUDED, f"{c.exclusion.reason.value}: {c.exclusion.explanation}"
    elif c.label is StartupLabel.LIKELY_STARTUP:
        outcome, detail = Outcome.FOUND, f"probability {c.probability:.2f}"
    elif c.label is StartupLabel.UNCERTAIN:
        outcome, detail = Outcome.FOUND_UNCERTAIN, f"probability {c.probability:.2f}"
    else:
        outcome, detail = Outcome.CLASSIFIED_NOT_STARTUP, f"probability {c.probability:.2f}"
    return CoverageRow(ref, outcome, cid, how, detail)


def _legal_name_hints(norm: str, out: PipelineOutput, names: dict[str, list[str]]) -> list[str]:
    """Record names that start with the reference name ("Balcony" -> "Balcony Technology
    Group, Inc."). Shown for a person to check, never counted: the same rule would also
    match unrelated funds ("Gather" -> "Gather Ventures Fund II LP")."""
    compact = norm.replace(" ", "")
    if len(compact) < 6:
        return []
    hits = {
        out.profiles[c].name
        for n, cids in names.items()
        if n.replace(" ", "").startswith(compact)
        for c in cids
    }
    return sorted(hits)[:3]


def to_markdown(report: CoverageReport) -> str:
    n = len(report.rows)
    likely = sum(r.outcome is Outcome.FOUND for r in report.rows)
    lines = ["# Coverage audit: known New Jersey startups", ""]
    if not report.is_proof_number:
        lines += [
            f"> **Pilot step, not a proof number.** The reference list has {n} companies"
            + (
                " and some rows have no source"
                if any(not r.reference.source for r in report.rows)
                else ""
            )
            + f"; a proof number needs at least {MIN_REFERENCE_SIZE} sourced companies.",
            "",
        ]
    sources = sorted({r.reference.source for r in report.rows if r.reference.source})
    lines += [
        f"- As of {report.as_of}; reference sources: {', '.join(sources) or 'none given'}",
        f"- **Found (discovery or uncertain list): {fmt_rate(report.found, n)}**",
        f"- Found in the likely-startup list alone: {fmt_rate(likely, n)}",
        "",
        "## By sector",
        "",
        "| sector | found | coverage |",
        "|---|---:|---:|",
    ]
    for sector, (found, total) in report.by_sector().items():
        lines.append(f"| {sector} | {found}/{total} | {fmt_rate(found, total)} |")
    lines += ["", "## Why companies were missed", ""]
    misses = report.misses()
    if not misses:
        lines.append("No misses.")
    for outcome, count in misses.most_common():
        lines.append(f"- **{outcome.value}** ({count}): {MISS_EXPLANATIONS[outcome]}")
        for r in report.rows:
            if r.outcome is outcome:
                lines.append(
                    f"  - {r.reference.name} ({r.reference.sector or 'no sector'}): {r.detail}"
                )
    lines += [
        "",
        "## Reading this",
        "",
        "- Coverage depends on the reference list. A list built from Form D or SBIR data "
        "would make coverage look better than it is; prefer lists from accelerators, "
        "partners, or press that are independent of Gauge's sources.",
        "- `no_public_signal` misses describe what Form D and SBIR/STTR cannot see. They are "
        "the case for adding sources, not a classifier defect.",
        "",
    ]
    return "\n".join(lines)


def write_csv(report: CoverageReport, path: str | Path) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "town", "sector", "source", "outcome", "company_id", "match", "detail"])
        for r in report.rows:
            ref = r.reference
            w.writerow(
                [ref.name, ref.town, ref.sector, ref.source, r.outcome.value, r.company_id or "",
                 r.match, r.detail]
            )  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    from gauge.core.serialize import load_records
    from gauge.pipeline import run
    from gauge.review.store import JsonReviewStore, ReviewStore

    parser = argparse.ArgumentParser(prog="gauge.validation.coverage")
    parser.add_argument("records")
    parser.add_argument("reference")
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--store", help="review queue JSON (applies merge decisions)")
    parser.add_argument("--out")
    parser.add_argument("--csv")
    args = parser.parse_args(argv)
    store = JsonReviewStore(args.store) if args.store else ReviewStore()
    out = run(load_records(args.records), args.as_of, store)
    report = audit(load_reference(args.reference), out)
    text = to_markdown(report)
    if args.out:
        Path(args.out).write_text(text)
    if args.csv:
        write_csv(report, args.csv)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
