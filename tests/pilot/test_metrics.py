from datetime import date
from pathlib import Path

import pytest

from gauge.pilot.metrics import (
    Channel,
    CostInputs,
    EventType,
    PilotEvent,
    TimeEntry,
    compute,
    load_cost_inputs,
    load_events,
    load_time_log,
)
from gauge.pilot.report import main, to_csv, to_markdown

START, END = date(2026, 10, 1), date(2026, 12, 29)
INPUTS = CostInputs(
    START,
    END,
    default_hourly_rate=100.0,
    hourly_rates={"partner": 200.0},
    monthly_fixed={Channel.GAUGE: {"hosting": 365 / 12 * 1}, Channel.CURRENT: {}},
)
TEMPLATES = Path(__file__).parents[2] / "docs" / "pilot" / "templates"


def ev(day, company, channel, event):
    return PilotEvent(date(2026, 10, day), company, Channel(channel), EventType(event))


def funnel(company, channel, upto):
    steps = ["sourced", "outreach_sent", "meeting_booked", "meeting_held", "qualified"]
    return [ev(i + 1, company, channel, s) for i, s in enumerate(steps[: steps.index(upto) + 1])]


def test_cost_per_qualified_first_meeting_by_channel():
    events = [
        *funnel("a", "gauge", "qualified"),
        *funnel("b", "gauge", "qualified"),
        *funnel("c", "gauge", "meeting_held"),
        *funnel("d", "current", "qualified"),
    ]
    time_log = [
        TimeEntry(date(2026, 10, 3), Channel.GAUGE, "analyst", 10),
        TimeEntry(date(2026, 10, 3), Channel.GAUGE, "partner", 2),
        TimeEntry(date(2026, 10, 3), Channel.CURRENT, "analyst", 30),
    ]
    report = compute(events, time_log, INPUTS)
    g, c = report.channels[Channel.GAUGE], report.channels[Channel.CURRENT]
    assert g.funnel[EventType.MEETING_HELD] == 3 and g.qualified_meetings == 2
    assert g.labor_cost == 10 * 100 + 2 * 200
    assert g.fixed_cost == pytest.approx(INPUTS.days)  # $1/day of hosting
    assert g.cost_per_qualified_meeting == pytest.approx((1400 + INPUTS.days) / 2)
    assert c.cost_per_qualified_meeting == pytest.approx(3000)
    assert g.conversion(EventType.MEETING_HELD, EventType.QUALIFIED) == pytest.approx(2 / 3)


def test_first_touch_attribution_and_overlap():
    events = [
        ev(1, "x", "current", "sourced"),
        ev(2, "x", "gauge", "sourced"),
        ev(3, "x", "gauge", "meeting_held"),
        ev(4, "x", "gauge", "qualified"),
    ]
    report = compute(events, [], INPUTS)
    assert report.channels[Channel.CURRENT].qualified_meetings == 1
    assert report.channels[Channel.GAUGE].qualified_meetings == 0
    assert report.overlap_companies == ("x",)
    assert any("both channels" in c for c in report.caveats)


def test_no_qualified_meetings_gives_no_ratio_and_caveats_are_printed():
    report = compute(funnel("a", "gauge", "meeting_held"), [], INPUTS)
    g = report.channels[Channel.GAUGE]
    assert g.cost_per_qualified_meeting is None
    text = " ".join(report.caveats)
    assert "directional only" in text and "no time logged" in text


def test_events_outside_window_and_unsourced_companies_are_excluded():
    events = [
        PilotEvent(date(2026, 9, 30), "early", Channel.GAUGE, EventType.SOURCED),
        PilotEvent(date(2026, 10, 5), "early", Channel.GAUGE, EventType.QUALIFIED),
    ]
    report = compute(events, [], INPUTS)
    assert report.channels[Channel.GAUGE].qualified_meetings == 0
    assert any("no 'sourced' event" in c for c in report.caveats)


def test_templates_load_and_report_renders(capsys):
    events = load_events(TEMPLATES / "pilot_events.csv")
    time_log = load_time_log(TEMPLATES / "time_log.csv")
    inputs = load_cost_inputs(TEMPLATES / "costs.json")
    report = compute(events, time_log, inputs)
    md = to_markdown(report)
    assert "cost per qualified first meeting" in md and "## Caveats" in md
    assert to_csv(report).startswith("channel,sourced,")
    assert main([
        "--events", str(TEMPLATES / "pilot_events.csv"),
        "--time", str(TEMPLATES / "time_log.csv"),
        "--costs", str(TEMPLATES / "costs.json"),
        "--format", "csv",
    ]) == 0  # fmt: skip
    assert "gauge,1,1,1,1,1" in capsys.readouterr().out
