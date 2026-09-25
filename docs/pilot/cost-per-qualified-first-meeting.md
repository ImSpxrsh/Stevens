# Pilot metric: cost per qualified first meeting

The 90-day pilot with the Garden State Innovation Fund is judged on one
number: what it costs to get a **qualified first meeting** through Gauge,
compared with the fund's current sourcing process over the same window.

> **Status: draft.** The definition below needs to be agreed with the fund
> before the pilot starts. Once the pilot runs, the report is computed from
> the logs in `templates/`.

## Definition (draft for the fund to confirm)

A **qualified first meeting** is a call or in-person meeting that meets all
of these:

1. It is with a founder or executive of the company.
2. The fund has not met the company in the 12 months before the pilot.
3. It happens inside the pilot window.
4. Afterward, a partner marks it **qualified**: the company fits the fund's
   mandate (New Jersey, stage, sector) **and** the partner wants a next step
   (second meeting, diligence request, or investment memo).

A meeting that happens but is not marked qualified counts in the funnel, not
in the numerator.

## What gets logged

| File | One row per | Columns |
|---|---|---|
| `pilot_events.csv` | funnel event | `date, company_id, channel, event, actor, notes` |
| `time_log.csv` | block of sourcing work | `date, channel, person, hours, activity` |
| `costs.json` | pilot | window, hourly rates, monthly fixed costs per channel |

- `channel` is `gauge` or `current`.
- `event` is one of `sourced`, `outreach_sent`, `meeting_booked`,
  `meeting_held`, `qualified`, `disqualified`.
- Log time for **both** channels. A channel with no time logged reports its
  labor cost as missing, not zero.

## How it is computed

- **Attribution:** a company belongs to whichever channel **sourced it
  first**. Later events count toward that channel. Companies both channels
  sourced are counted once and reported as overlap.
- **Cost** per channel is hours × hourly rate (per person, or the default)
  plus monthly fixed costs prorated over the window (e.g. Gauge hosting and
  LLM usage vs. the fund's data subscriptions).
- **Cost per qualified first meeting** = total cost ÷ qualified first
  meetings, per channel.

```bash
python -m gauge.pilot.report --events pilot_events.csv --time time_log.csv --costs costs.json
python -m gauge.pilot.report ... --format csv   # for a spreadsheet
```

## Caveats the report prints

- **Small samples:** fewer than 10 qualified meetings in a channel means the
  ratio is directional only.
- **Attribution:** first-touch attribution credits whichever channel logged
  `sourced` first; the fund's team may have heard of a company earlier
  without logging it.
- **Window edge:** meetings qualified after the window closes are not
  counted, which understates late-pilot sourcing.
- **Comparison:** the current-process numbers come from the same window,
  not the fund's historical averages. If the fund has a historical cost per
  meeting, show it alongside but do not mix the two.
