"""Alert generation, dedupe, and status tracking.

Alerts come from new public records linked to companies Gauge surfaces:

* ``new_likely_startup``: a likely startup's first public record
* ``raised_again``: a new (non-amendment) Form D from a company with an
  earlier Form D
* ``phase_ii_win``: an SBIR/STTR Phase II award

Identity decides delivery, via ``gauge.review.gate.alert_gate``: only an
exact SEC company ID match is ``ready`` to send automatically; a match a
person approved is also ``ready``; anything else is ``held`` for review, and
a rejected match produces no alert at all.

Dedupe: an alert's id is derived from its type, company, and source record,
so rerunning the pipeline over the same records never creates a second
alert, and a status someone set (sent, dismissed) is kept.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from gauge.classifier import StartupLabel
from gauge.core.models import CompanyProfile, NormalizedRecord, SbirPhase
from gauge.pipeline import PipelineOutput
from gauge.review.gate import AlertGate, alert_gate
from gauge.review.models import now
from gauge.review.store import ReviewStore


class AlertType(StrEnum):
    NEW_LIKELY_STARTUP = "new_likely_startup"
    RAISED_AGAIN = "raised_again"
    PHASE_II_WIN = "phase_ii_win"


class AlertStatus(StrEnum):
    READY = "ready"  # identity certain; may be sent
    HELD = "held"  # waiting for a person to confirm the company match
    SENT = "sent"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class Alert:
    alert_id: str
    type: AlertType
    company_id: str
    company_name: str
    record_key: str
    summary: str
    why: str  # why it fired and how identity was established
    source_url: str
    source_date: str
    status: AlertStatus
    created_at: str
    updated_at: str


def alert_id(type_: AlertType, company_id: str, record_key: str) -> str:
    digest = hashlib.sha256(f"{type_}|{company_id}|{record_key}".encode()).hexdigest()
    return f"al_{digest[:12]}"


def _money(x: float | None) -> str:
    return f"${x:,.0f}" if x else "an undisclosed amount"


def _classify_event(
    rec: NormalizedRecord, profile: CompanyProfile, label: StartupLabel
) -> tuple[AlertType, str] | None:
    earlier = [r for r in profile.records if r.source_date < rec.source_date and r.key != rec.key]
    name, when = profile.name, rec.source_date.isoformat()
    if rec.sbir and rec.sbir.phase in (SbirPhase.PHASE_II, SbirPhase.DIRECT_TO_PHASE_II):
        agency = rec.sbir.agency or "a federal agency"
        return AlertType.PHASE_II_WIN, (
            f"{name} won an {rec.sbir.program} Phase II award from {agency} "
            f"({_money(rec.sbir.award_amount)}) on {when}."
        )
    if rec.form_d and not rec.form_d.is_amendment and any(r.form_d for r in earlier):
        amount = rec.form_d.total_offering_amount or rec.form_d.total_amount_sold
        return AlertType.RAISED_AGAIN, (
            f"{name} filed a new SEC Form D on {when} for {_money(amount)}, after an earlier raise."
        )
    if not earlier and label is StartupLabel.LIKELY_STARTUP:
        what = "an SEC Form D" if rec.form_d else "a federal SBIR/STTR award"
        return AlertType.NEW_LIKELY_STARTUP, (
            f"{name} appeared in public records for the first time with {what} on {when}."
        )
    return None


def generate(out: PipelineOutput, store: ReviewStore, *, since: date) -> list[Alert]:
    """Alerts for records dated after ``since`` on companies discovery shows."""
    shown = {c.company_id for c in (*out.discovery.ranked, *out.discovery.uncertain)}
    records = {r.key: r for p in out.profiles.values() for r in p.records}
    stamp = now().isoformat()
    alerts: list[Alert] = []
    for elig in out.alerts:
        rec = records[elig.record_key]
        if rec.source_date <= since or elig.company_id not in shown:
            continue
        if elig.gate is AlertGate.BLOCKED:
            continue
        profile = out.profiles[elig.company_id]
        event = _classify_event(rec, profile, out.classifications[elig.company_id].label)
        if event is None:
            continue
        type_, summary = event
        gate, reason = alert_gate(
            elig.record_key, out.linking.links[elig.record_key].company_id, out.linking, store
        )
        status = (
            AlertStatus.READY
            if gate in (AlertGate.AUTOMATIC, AlertGate.HUMAN_REVIEWED)
            else AlertStatus.HELD
        )
        alerts.append(
            Alert(
                alert_id=alert_id(type_, elig.company_id, elig.record_key),
                type=type_,
                company_id=elig.company_id,
                company_name=profile.name,
                record_key=elig.record_key,
                summary=summary,
                why=f"{type_.value.replace('_', ' ')}; identity: {reason}",
                source_url=rec.provenance.source_url,
                source_date=rec.source_date.isoformat(),
                status=status,
                created_at=stamp,
                updated_at=stamp,
            )
        )
    return alerts


class AlertLog:
    """Persistent, deduplicated alert feed (one JSON file until #28's schema exists)."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._alerts: dict[str, Alert] = {}
        if self.path and self.path.exists():
            for d in json.loads(self.path.read_text())["alerts"]:
                d["type"], d["status"] = AlertType(d["type"]), AlertStatus(d["status"])
                self._alerts[d["alert_id"]] = Alert(**d)

    def alerts(self, status: AlertStatus | None = None) -> list[Alert]:
        found = [a for a in self._alerts.values() if status is None or a.status is status]
        return sorted(found, key=lambda a: (a.source_date, a.alert_id), reverse=True)

    def add(self, alerts: Iterable[Alert]) -> list[Alert]:
        """Add new alerts; returns only the ones not seen before.

        An existing alert keeps its status, except that a HELD alert becomes
        READY once its company match has been approved.
        """
        added = []
        for a in alerts:
            existing = self._alerts.get(a.alert_id)
            if existing is None:
                self._alerts[a.alert_id] = a
                added.append(a)
                # An approved merge moves the record to another company, which gives
                # its alert a new id; retire the alert that was held under the old one.
                for other in list(self._alerts.values()):
                    if (
                        other.alert_id != a.alert_id
                        and other.record_key == a.record_key
                        and other.status is AlertStatus.HELD
                    ):
                        self._alerts[other.alert_id] = replace(
                            other, status=AlertStatus.DISMISSED, updated_at=a.updated_at,
                            why=other.why + f" Superseded by {a.alert_id}.",
                        )  # fmt: skip
            elif existing.status is AlertStatus.HELD and a.status is AlertStatus.READY:
                self._alerts[a.alert_id] = replace(
                    existing, status=AlertStatus.READY, why=a.why, updated_at=a.updated_at
                )
        self._save()
        return added

    def set_status(self, alert_id: str, status: AlertStatus) -> Alert:
        a = self._alerts[alert_id]
        if status is AlertStatus.SENT and a.status is not AlertStatus.READY:
            raise ValueError(f"{alert_id} is {a.status.value}; only ready alerts can be sent")
        a = replace(a, status=status, updated_at=datetime.now().astimezone().isoformat())
        self._alerts[alert_id] = a
        self._save()
        return a

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"alerts": [asdict(a) for a in self.alerts()]}
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        os.replace(tmp, self.path)
