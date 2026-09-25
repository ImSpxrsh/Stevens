"""Proof number 1: does Gauge's top 25 beat the strongest simple baseline?

Method (all choices are parameters, recorded in the report):

1. **Freeze** the data at ``cutoff`` (default 2022-12-31): only records dated
   on or before it are linked, classified, or ranked. Linking uses a fresh
   review queue, so later human decisions cannot leak in.
2. **Candidates**: non-excluded companies with an NJ address and a record in
   the ``active_window`` before the cutoff.
3. **Rank** candidates with Gauge (classifier probability) and with simple
   baselines using the same frozen data: largest recent raise, most recent
   activity, and SBIR/STTR award count.
4. **Outcome**: a candidate is a hit if, after the cutoff and by
   ``outcome_end``, it files a new Form D of at least ``min_follow_on`` or
   wins an SBIR/STTR Phase II. Future records are tied to candidates only by
   exact SEC company ID or exact name + postal code (no fuzzy matching).
5. **Compare** precision@k for Gauge against every baseline, headline against
   the best-performing one, then repeat on the **cold-start** group:
   companies whose first public record falls in the year before the cutoff.

    python -m gauge.validation.backtest RECORDS.json [--cutoff 2022-12-31] \\
        [--outcome-end 2024-12-31] [--k 25] [--out report.md]
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from gauge.classifier import classify
from gauge.core.models import CompanyProfile, NormalizedRecord, SbirPhase
from gauge.core.names import normalize_company_name
from gauge.review.linking import link_records
from gauge.review.store import ReviewStore
from gauge.validation.stats import fmt_rate, wilson_interval

Scorer = Callable[[CompanyProfile, date], float]


def _largest_recent_raise(p: CompanyProfile, cutoff: date) -> float:
    since = cutoff - timedelta(days=2 * 365)
    amounts = [
        (r.form_d.total_amount_sold or r.form_d.total_offering_amount or 0.0)
        for r in p.form_d_records
        if r.form_d and r.source_date >= since
    ]
    return max(amounts, default=0.0)


def _most_recent_activity(p: CompanyProfile, cutoff: date) -> float:
    return float(max(r.source_date for r in p.records).toordinal()) if p.records else 0.0


def _sbir_award_count(p: CompanyProfile, cutoff: date) -> float:
    return float(len(p.sbir_records))


BASELINES: dict[str, tuple[str, Scorer]] = {
    "largest_recent_raise": (
        "Largest Form D raise in the 2 years before cutoff",
        _largest_recent_raise,
    ),
    "most_recent_activity": ("Most recent public record", _most_recent_activity),
    "sbir_award_count": ("Number of SBIR/STTR awards", _sbir_award_count),
}


@dataclass(frozen=True)
class RankingResult:
    name: str
    description: str
    top: tuple[str, ...]
    hits: int

    @property
    def k(self) -> int:
        return len(self.top)

    @property
    def precision(self) -> float | None:
        return self.hits / self.k if self.k else None


@dataclass(frozen=True)
class GroupResult:
    label: str
    candidates: int
    positives: int  # candidates with the outcome, at any rank
    gauge: RankingResult
    baselines: tuple[RankingResult, ...]
    # Candidates sharing Gauge's score at rank k; their order is arbitrary.
    gauge_ties_at_k: int = 0

    @property
    def best_baseline(self) -> RankingResult | None:
        return max(self.baselines, key=lambda b: (b.hits, b.name)) if self.baselines else None


@dataclass(frozen=True)
class BacktestReport:
    cutoff: date
    outcome_end: date
    k: int
    min_follow_on: float
    active_window_days: int
    overall: GroupResult
    cold_start: GroupResult


def run_backtest(
    records: Sequence[NormalizedRecord],
    *,
    cutoff: date = date(2022, 12, 31),
    outcome_end: date = date(2024, 12, 31),
    k: int = 25,
    min_follow_on: float = 1_000_000.0,
    active_window: timedelta = timedelta(days=2 * 365),
) -> BacktestReport:
    if outcome_end <= cutoff:
        raise ValueError("outcome_end must be after cutoff")
    frozen = [r for r in records if r.source_date <= cutoff]
    future = [r for r in records if cutoff < r.source_date <= outcome_end]

    linking = link_records(frozen, ReviewStore())
    candidates: dict[str, CompanyProfile] = {}
    for cid, p in linking.profiles.items():
        if not p.has_new_jersey_address():
            continue
        if not any(r.source_date >= cutoff - active_window for r in p.records):
            continue
        if classify(p, cutoff).excluded:
            continue
        candidates[cid] = p

    positives = _outcomes(candidates, future, min_follow_on)
    cold = {
        cid: p
        for cid, p in candidates.items()
        if min(r.source_date for r in p.records) > cutoff - timedelta(days=365)
    }
    return BacktestReport(
        cutoff=cutoff,
        outcome_end=outcome_end,
        k=k,
        min_follow_on=min_follow_on,
        active_window_days=active_window.days,
        overall=_evaluate("All candidates", candidates, positives, cutoff, k),
        cold_start=_evaluate(
            "Cold start (first public record in the prior year)", cold, positives, cutoff, k
        ),
    )


def _outcomes(
    candidates: dict[str, CompanyProfile], future: Sequence[NormalizedRecord], min_follow_on: float
) -> set[str]:
    by_cik = {cik: cid for cid, p in candidates.items() for cik in p.ciks}
    by_name_postal = {
        (normalize_company_name(r.name), (r.address.postal_code or "")[:5]): cid
        for cid, p in candidates.items()
        for r in p.records
        if r.address and r.address.postal_code
    }
    hits: set[str] = set()
    for r in future:
        is_raise = (
            r.form_d is not None
            and not r.form_d.is_amendment
            and (r.form_d.total_offering_amount or r.form_d.total_amount_sold or 0) >= min_follow_on
        )
        is_phase_ii = r.sbir is not None and r.sbir.phase in (
            SbirPhase.PHASE_II,
            SbirPhase.DIRECT_TO_PHASE_II,
        )
        if not (is_raise or is_phase_ii):
            continue
        cid = by_cik.get(r.cik) if r.cik else None
        if cid is None and r.address and r.address.postal_code:
            cid = by_name_postal.get((normalize_company_name(r.name), r.address.postal_code[:5]))
        if cid is not None:
            hits.add(cid)
    return hits


def _rank(
    profiles: dict[str, CompanyProfile], score: Scorer, cutoff: date, k: int
) -> tuple[str, ...]:
    ordered = sorted(profiles, key=lambda cid: (-score(profiles[cid], cutoff), cid))
    return tuple(ordered[:k])


def _gauge_score(p: CompanyProfile, cutoff: date) -> float:
    return classify(p, cutoff).probability or 0.0


def _evaluate(
    label: str, profiles: dict[str, CompanyProfile], positives: set[str], cutoff: date, k: int
) -> GroupResult:
    def result(name: str, description: str, scorer: Scorer) -> RankingResult:
        top = _rank(profiles, scorer, cutoff, k)
        return RankingResult(name, description, top, sum(cid in positives for cid in top))

    gauge = result("gauge", "Gauge likely-startup probability", _gauge_score)
    ties = 0
    if gauge.top and len(profiles) > k:
        kth = round(_gauge_score(profiles[gauge.top[-1]], cutoff), 6)
        ties = sum(round(_gauge_score(p, cutoff), 6) == kth for p in profiles.values())
    return GroupResult(
        label=label,
        candidates=len(profiles),
        positives=sum(cid in positives for cid in profiles),
        gauge=gauge,
        baselines=tuple(result(n, d, s) for n, (d, s) in BASELINES.items()),
        gauge_ties_at_k=ties if ties > 1 else 0,
    )


def _group_markdown(g: GroupResult) -> list[str]:
    lines = [f"## {g.label}", ""]
    if not g.candidates:
        return lines + ["No candidates in this group.", ""]
    lines += [
        f"{g.candidates} candidates; {g.positives} had the outcome "
        f"(base rate {fmt_rate(g.positives, g.candidates)}).",
        "",
        "| ranking | hits in top k | precision@k |",
        "|---|---:|---:|",
        f"| **Gauge** | {g.gauge.hits}/{g.gauge.k} | {fmt_rate(g.gauge.hits, g.gauge.k)} |",
    ]
    for b in g.baselines:
        lines.append(f"| {b.description} | {b.hits}/{b.k} | {fmt_rate(b.hits, b.k)} |")
    best = g.best_baseline
    if best is not None:
        lines += [
            "",
            f"Headline: Gauge {g.gauge.hits}/{g.gauge.k} vs. strongest baseline "
            f"({best.description}) {best.hits}/{best.k}.",
        ]
        g_ci, b_ci = wilson_interval(g.gauge.hits, g.gauge.k), wilson_interval(best.hits, best.k)
        if g_ci and b_ci and g_ci[0] <= b_ci[1] and b_ci[0] <= g_ci[1]:
            lines.append("The 95% intervals overlap, so this difference is not conclusive.")
    if g.gauge_ties_at_k:
        lines.append(
            f"Warning: {g.gauge_ties_at_k} candidates share Gauge's score at rank {g.gauge.k}, "
            "so which of them make the top k is arbitrary. The classifier scores how "
            "startup-like a company is; it saturates and is not a follow-on predictor."
        )
    return lines + [""]


def to_markdown(r: BacktestReport) -> str:
    return "\n".join(
        [
            "# Top-25 discovery backtest",
            "",
            f"- Frozen at **{r.cutoff}**; outcomes observed through **{r.outcome_end}**; "
            f"k = {r.k}.",
            f"- Candidates: non-excluded NJ companies with a public record in the "
            f"{r.active_window_days} days before the cutoff.",
            f"- Outcome: a new Form D of at least ${r.min_follow_on:,.0f} or an SBIR/STTR "
            "Phase II award after the cutoff, tied to the candidate by exact SEC company ID "
            "or exact name + postal code.",
            "",
            *_group_markdown(r.overall),
            *_group_markdown(r.cold_start),
            "## What this does and does not show",
            "",
            "- **Does:** whether Gauge's ranking, using only records available at the cutoff, "
            "puts more companies with later follow-on activity in its top k than simple "
            "rankings built from the same records. The headline uses the best baseline on this "
            "data, which favors the baseline.",
            "- **Does not:** measure investment returns or company quality. The outcome is a "
            "proxy that only counts activity visible in public filings; companies that raise "
            "without a Form D, or whose later records use another name or address, count as "
            "misses.",
            "- The classifier's prior weights were written in 2026, not fit on this data, but "
            "their authors knew how startups generally behave; treat the result as supportive, "
            "not a controlled experiment.",
            "- With k = 25 the intervals are wide; one or two hits can change the comparison.",
            "",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    from gauge.core.serialize import load_records

    parser = argparse.ArgumentParser(prog="gauge.validation.backtest")
    parser.add_argument("records")
    parser.add_argument("--cutoff", type=date.fromisoformat, default=date(2022, 12, 31))
    parser.add_argument("--outcome-end", type=date.fromisoformat, default=date(2024, 12, 31))
    parser.add_argument("--k", type=int, default=25)
    parser.add_argument("--min-follow-on", type=float, default=1_000_000.0)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    report = run_backtest(
        load_records(args.records),
        cutoff=args.cutoff,
        outcome_end=args.outcome_end,
        k=args.k,
        min_follow_on=args.min_follow_on,
    )
    text = to_markdown(report)
    if args.out:
        Path(args.out).write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
