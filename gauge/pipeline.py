"""The core Gauge flow, end to end, on normalized records:

records -> linked company profiles (+ review queue) -> startup classification
-> discovery view -> program matches -> evidence card -> alert eligibility.

``evidence_card`` and the alert step here are the minimal versions the golden
path needs; the full evidence model (#8) and the alert feed (#15) build on
the same outputs.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import date

from gauge.classifier import Classification, DiscoveryView, StartupLabel, classify, discovery_view
from gauge.core.models import (
    CompanyProfile,
    EvidenceItem,
    EvidenceKind,
    NormalizedRecord,
    SbirPhase,
)
from gauge.programs.base import ProgramMatch
from gauge.programs.registry import evaluate_all
from gauge.review.dedupe import merge_approved_duplicates
from gauge.review.gate import AlertGate, alert_gate
from gauge.review.linking import LinkResult, link_records
from gauge.review.store import ReviewStore

_PHASE_LABELS = {
    SbirPhase.PHASE_I: "Phase I",
    SbirPhase.PHASE_II: "Phase II",
    SbirPhase.FAST_TRACK: "Fast Track",
    SbirPhase.DIRECT_TO_PHASE_II: "Direct to Phase II",
}

# Questions public records never answer; they seed every first call.
STANDARD_GAPS = (
    "Who are the founders and how large is the team today?",
    "What revenue or customer traction does the company have?",
)


@dataclass(frozen=True)
class AlertEligibility:
    record_key: str
    company_id: str
    gate: AlertGate
    reason: str


@dataclass(frozen=True)
class PipelineOutput:
    as_of: date
    linking: LinkResult
    profiles: dict[str, CompanyProfile]
    classifications: dict[str, Classification]
    discovery: DiscoveryView
    program_matches: dict[str, dict[str, ProgramMatch]]  # company id -> program id -> match
    evidence_cards: dict[str, list[EvidenceItem]]
    alerts: list[AlertEligibility]


def run(
    records: Iterable[NormalizedRecord],
    as_of: date,
    store: ReviewStore,
    *,
    public_ciks: Collection[str] = (),
) -> PipelineOutput:
    records = list(records)
    linking = link_records(records, store)
    profiles = merge_approved_duplicates(linking.profiles, store)
    classifications = {
        cid: classify(p, as_of, public_ciks=public_ciks) for cid, p in profiles.items()
    }
    discovery = discovery_view(classifications.values())
    # Program matching is for companies discovery shows or holds for review;
    # hard-excluded and not-a-startup companies are skipped.
    shown = {c.company_id for c in (*discovery.ranked, *discovery.uncertain)}
    matches = {cid: evaluate_all(profiles[cid], as_of) for cid in sorted(shown)}
    cards = {
        cid: evidence_card(profiles[cid], classifications[cid], matches.get(cid, {}))
        for cid in sorted(profiles)
    }
    alerts = []
    for r in sorted(records, key=lambda r: (r.source_date, r.key)):
        gate, reason = alert_gate(r.key, linking.links[r.key].company_id, linking, store)
        alerts.append(AlertEligibility(r.key, _company_of(r.key, linking, profiles), gate, reason))
    return PipelineOutput(
        as_of, linking, profiles, classifications, discovery, matches, cards, alerts
    )


def _company_of(record_key: str, linking: LinkResult, profiles: dict[str, CompanyProfile]) -> str:
    cid = linking.links[record_key].company_id
    if cid in profiles:
        return cid
    # The record's company was merged into another by an approved duplicate review.
    return next(
        p.company_id for p in profiles.values() if any(r.key == record_key for r in p.records)
    )


def evidence_card(
    profile: CompanyProfile, classification: Classification, matches: dict[str, ProgramMatch]
) -> list[EvidenceItem]:
    """Facts from records, then inferred labels, then unknowns as first-call questions."""
    facts: list[EvidenceItem] = []
    for r in sorted(profile.records, key=lambda r: r.source_date):
        if r.form_d:
            amount = r.form_d.total_offering_amount
            facts.append(
                EvidenceItem(
                    claim=f"Filed SEC Form D on {r.source_date.isoformat()}",
                    kind=EvidenceKind.FACT,
                    source=r.provenance,
                    value=f"${amount:,.0f} offering"
                    if amount is not None
                    else "indefinite offering",
                )
            )
        if r.sbir:
            phase = _PHASE_LABELS[r.sbir.phase]
            facts.append(
                EvidenceItem(
                    claim=f"Won an {r.sbir.program} {phase} award from "
                    f"{r.sbir.agency or 'a federal agency'} on {r.source_date.isoformat()}",
                    kind=EvidenceKind.FACT,
                    source=r.provenance,
                    value=f"${r.sbir.award_amount:,.0f}" if r.sbir.award_amount else None,
                )
            )
    latest = profile.latest_address()
    if latest and latest[0].city:
        facts.append(
            EvidenceItem(
                claim=f"Listed address in {latest[0].city}, {latest[0].state}",
                kind=EvidenceKind.FACT,
                source=latest[1],
            )
        )

    inferred = [_classification_item(classification)]
    unknowns: list[str] = []
    for match in matches.values():
        items = match.evidence_items()
        inferred.append(items[0])
        unknowns.extend(i.claim for i in items[1:])
    unknowns.extend(STANDARD_GAPS)
    gaps = [EvidenceItem(claim=q, kind=EvidenceKind.UNKNOWN) for q in dict.fromkeys(unknowns)]
    return facts + inferred + gaps


def _classification_item(c: Classification) -> EvidenceItem:
    labels = {
        StartupLabel.LIKELY_STARTUP: "Likely startup",
        StartupLabel.NOT_STARTUP: "Not a startup",
        StartupLabel.UNCERTAIN: "Uncertain whether this is a startup",
    }
    if c.exclusion is not None:
        why = c.exclusion.explanation
    else:
        why = "; ".join(f.description for f in c.top_features) or "no strong signals"
    return EvidenceItem(
        claim=labels[c.label],
        kind=EvidenceKind.INFERRED,
        value=c.label.value,
        confidence=c.confidence,
        limitations=f"Model {c.model_version}. Based on: {why}",
    )
