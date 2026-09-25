"""Render the pilot metric as Markdown or CSV.

    python -m gauge.pilot.report --events pilot_events.csv --time time_log.csv \\
        --costs costs.json [--format md|csv]
"""

from __future__ import annotations

import argparse
import csv
import io
from collections.abc import Sequence

from gauge.pilot.metrics import (
    FUNNEL,
    Channel,
    EventType,
    PilotReport,
    compute,
    load_cost_inputs,
    load_events,
    load_time_log,
)


def _money(x: float | None) -> str:
    return "n/a" if x is None else f"${x:,.0f}"


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def to_markdown(report: PilotReport) -> str:
    g, c = report.channels[Channel.GAUGE], report.channels[Channel.CURRENT]
    lines = [
        "# Cost per qualified first meeting",
        "",
        f"Pilot window: {report.inputs.start} to {report.inputs.end}",
        "",
        "| | Gauge | Current process |",
        "|---|---:|---:|",
    ]
    for step in FUNNEL:
        lines.append(f"| {step.value.replace('_', ' ')} | {g.funnel[step]} | {c.funnel[step]} |")
    lines += [
        f"| hours logged | {g.hours:,.1f} | {c.hours:,.1f} |",
        f"| labor cost | {_money(g.labor_cost)} | {_money(c.labor_cost)} |",
        f"| fixed cost (prorated) | {_money(g.fixed_cost)} | {_money(c.fixed_cost)} |",
        f"| total cost | {_money(g.total_cost)} | {_money(c.total_cost)} |",
        f"| **cost per qualified first meeting** | **{_money(g.cost_per_qualified_meeting)}** "
        f"| **{_money(c.cost_per_qualified_meeting)}** |",
        f"| meeting held → qualified | "
        f"{_pct(g.conversion(EventType.MEETING_HELD, EventType.QUALIFIED))} | "
        f"{_pct(c.conversion(EventType.MEETING_HELD, EventType.QUALIFIED))} |",
        "",
        "## Caveats",
        "",
        *[f"- {note}" for note in report.caveats],
        "",
    ]
    return "\n".join(lines)


def to_csv(report: PilotReport) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["channel", *[s.value for s in FUNNEL], "hours", "labor_cost", "fixed_cost", "total_cost",
         "cost_per_qualified_first_meeting"]
    )  # fmt: skip
    for m in report.channels.values():
        cpq = m.cost_per_qualified_meeting
        w.writerow(
            [m.channel.value, *[m.funnel[s] for s in FUNNEL], f"{m.hours:.2f}",
             f"{m.labor_cost:.2f}", f"{m.fixed_cost:.2f}", f"{m.total_cost:.2f}",
             "" if cpq is None else f"{cpq:.2f}"]
        )  # fmt: skip
    return buf.getvalue()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gauge.pilot.report")
    parser.add_argument("--events", required=True)
    parser.add_argument("--time", required=True)
    parser.add_argument("--costs", required=True)
    parser.add_argument("--format", choices=["md", "csv"], default="md")
    args = parser.parse_args(argv)
    report = compute(
        load_events(args.events), load_time_log(args.time), load_cost_inputs(args.costs)
    )
    print(to_markdown(report) if args.format == "md" else to_csv(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
