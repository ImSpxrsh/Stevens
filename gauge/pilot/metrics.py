"""Cost per qualified first meeting for the Gauge pilot.

Two channels are compared over the same pilot window:

* ``gauge``: companies first surfaced by Gauge.
* ``current``: companies first surfaced by the fund's existing process.

A company belongs to the channel of its first ``sourced`` event (first-touch
attribution); later events for that company count toward that channel even
if the other channel also touched it. Companies both channels sourced are
reported as overlap.

Cost per channel = hours logged x hourly rate + fixed costs prorated over
the window. Cost per qualified first meeting = cost / qualified first
meetings in that channel.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path


class Channel(StrEnum):
    GAUGE = "gauge"
    CURRENT = "current"


class EventType(StrEnum):
    SOURCED = "sourced"
    OUTREACH_SENT = "outreach_sent"
    MEETING_BOOKED = "meeting_booked"
    MEETING_HELD = "meeting_held"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"


FUNNEL = (
    EventType.SOURCED,
    EventType.OUTREACH_SENT,
    EventType.MEETING_BOOKED,
    EventType.MEETING_HELD,
    EventType.QUALIFIED,
)
SMALL_SAMPLE = 10


@dataclass(frozen=True)
class PilotEvent:
    on: date
    company_id: str
    channel: Channel
    event: EventType
    actor: str = ""
    notes: str = ""


@dataclass(frozen=True)
class TimeEntry:
    on: date
    channel: Channel
    person: str
    hours: float
    activity: str = ""


@dataclass(frozen=True)
class CostInputs:
    start: date
    end: date
    default_hourly_rate: float
    hourly_rates: dict[str, float] = field(default_factory=dict)  # per person
    # Monthly fixed costs per channel, e.g. {GAUGE: {"hosting": 150}, CURRENT: {"data": 1200}}
    monthly_fixed: dict[Channel, dict[str, float]] = field(default_factory=dict)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def rate(self, person: str) -> float:
        return self.hourly_rates.get(person, self.default_hourly_rate)


@dataclass(frozen=True)
class ChannelMetrics:
    channel: Channel
    funnel: dict[EventType, int]  # distinct companies reaching each step
    hours: float
    labor_cost: float
    fixed_cost: float

    @property
    def total_cost(self) -> float:
        return self.labor_cost + self.fixed_cost

    @property
    def qualified_meetings(self) -> int:
        return self.funnel[EventType.QUALIFIED]

    @property
    def cost_per_qualified_meeting(self) -> float | None:
        q = self.qualified_meetings
        return self.total_cost / q if q else None

    def conversion(self, frm: EventType, to: EventType) -> float | None:
        base = self.funnel[frm]
        return self.funnel[to] / base if base else None


@dataclass(frozen=True)
class PilotReport:
    inputs: CostInputs
    channels: dict[Channel, ChannelMetrics]
    overlap_companies: tuple[str, ...]
    caveats: tuple[str, ...]


def compute(
    events: Iterable[PilotEvent], time_log: Iterable[TimeEntry], inputs: CostInputs
) -> PilotReport:
    in_window = [e for e in events if inputs.start <= e.on <= inputs.end]
    hours_in_window = [t for t in time_log if inputs.start <= t.on <= inputs.end]

    first_touch: dict[str, Channel] = {}
    sourced_by: dict[str, set[Channel]] = defaultdict(set)
    for e in sorted(in_window, key=lambda e: (e.on, e.channel.value)):
        if e.event is EventType.SOURCED:
            sourced_by[e.company_id].add(e.channel)
            first_touch.setdefault(e.company_id, e.channel)

    reached: dict[Channel, dict[EventType, set[str]]] = {
        c: {step: set() for step in FUNNEL} for c in Channel
    }
    unattributed: set[str] = set()
    for e in in_window:
        if e.event not in FUNNEL:
            continue
        channel = first_touch.get(e.company_id)
        if channel is None:
            unattributed.add(e.company_id)
            continue
        reached[channel][e.event].add(e.company_id)

    channels = {}
    for c in Channel:
        entries = [t for t in hours_in_window if t.channel is c]
        hours = sum(t.hours for t in entries)
        labor = sum(t.hours * inputs.rate(t.person) for t in entries)
        monthly = sum(inputs.monthly_fixed.get(c, {}).values())
        fixed = monthly * 12 / 365 * inputs.days
        channels[c] = ChannelMetrics(
            c, {step: len(ids) for step, ids in reached[c].items()}, hours, labor, fixed
        )

    overlap = tuple(sorted(cid for cid, chans in sourced_by.items() if len(chans) > 1))
    return PilotReport(inputs, channels, overlap, _caveats(channels, overlap, unattributed, inputs))


def _caveats(
    channels: dict[Channel, ChannelMetrics],
    overlap: tuple[str, ...],
    unattributed: set[str],
    inputs: CostInputs,
) -> tuple[str, ...]:
    notes = []
    for m in channels.values():
        if m.qualified_meetings < SMALL_SAMPLE:
            notes.append(
                f"{m.channel.value}: {m.qualified_meetings} qualified first meetings; with fewer "
                f"than {SMALL_SAMPLE}, treat cost per meeting as directional only."
            )
        if m.hours == 0:
            notes.append(f"{m.channel.value}: no time logged; labor cost is missing, not zero.")
    if overlap:
        notes.append(
            f"{len(overlap)} companies were sourced by both channels; each is counted once, "
            "under whichever channel sourced it first."
        )
    if unattributed:
        notes.append(
            f"{len(unattributed)} companies have events but no 'sourced' event in the window "
            "and are excluded."
        )
    notes.append(
        f"Window {inputs.start} to {inputs.end} ({inputs.days} days). Meetings qualified after "
        "the window ends are not counted, which understates the most recent sourcing."
    )
    return tuple(notes)


# --- CSV/JSON loading -------------------------------------------------------


def load_events(path: str | Path) -> list[PilotEvent]:
    with open(path, newline="") as f:
        return [
            PilotEvent(
                date.fromisoformat(row["date"]),
                row["company_id"].strip(),
                Channel(row["channel"].strip()),
                EventType(row["event"].strip()),
                row.get("actor", "").strip(),
                row.get("notes", "").strip(),
            )
            for row in csv.DictReader(f)
        ]


def load_time_log(path: str | Path) -> list[TimeEntry]:
    with open(path, newline="") as f:
        return [
            TimeEntry(
                date.fromisoformat(row["date"]),
                Channel(row["channel"].strip()),
                row["person"].strip(),
                float(row["hours"]),
                row.get("activity", "").strip(),
            )
            for row in csv.DictReader(f)
        ]


def load_cost_inputs(path: str | Path) -> CostInputs:
    d = json.loads(Path(path).read_text())
    return CostInputs(
        start=date.fromisoformat(d["start"]),
        end=date.fromisoformat(d["end"]),
        default_hourly_rate=float(d["default_hourly_rate"]),
        hourly_rates={k: float(v) for k, v in d.get("hourly_rates", {}).items()},
        monthly_fixed={
            Channel(c): {k: float(v) for k, v in items.items()}
            for c, items in d.get("monthly_fixed", {}).items()
        },
    )
