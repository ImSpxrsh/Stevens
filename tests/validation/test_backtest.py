from datetime import date

import pytest

from gauge.core.models import Address, SbirPhase
from gauge.core.serialize import dump_records
from gauge.validation.backtest import main, run_backtest, to_markdown
from tests.factories import form_d, sbir

CUTOFF = date(2022, 12, 31)
PA = Address(city="Philadelphia", state="PA", postal_code="19103")


def town(i):
    return Address(city=f"Town{i}", state="NJ", postal_code=f"07{i:03d}")


def dataset():
    """Startup-like companies (new, no revenue) raise again after the cutoff;
    older companies with revenue and big past raises do not."""
    records = []
    for i in range(6):  # young startups, first seen in 2022 (cold start), raise again in 2024
        cik = f"00010000{i:02d}"
        records.append(
            form_d(
                f"Seedling {i} Inc",
                cik=cik,
                address=town(i),
                filed=date(2022, 6, 1),
                revenue_range="No Revenues",
                total_offering_amount=1_500_000.0,
                total_amount_sold=1_000_000.0,
            )
        )
        records.append(
            form_d(
                f"Seedling {i} Inc",
                cik=cik,
                address=town(i),
                filed=date(2024, 3, 1),
                total_offering_amount=5_000_000.0,
            )
        )
    for i in range(6, 12):  # older companies with revenue and a big 2021 raise; no follow-on
        cik = f"00020000{i:02d}"
        records.append(
            form_d(
                f"Mature {i} Corp",
                cik=cik,
                address=town(i),
                filed=date(2021, 3, 1),
                incorporated_within_five_years=False,
                revenue_range="$5,000,001 - $25,000,000",
                industry_group="Manufacturing",
                total_offering_amount=9_000_000.0,
                total_amount_sold=9_000_000.0,
            )
        )
    # SBIR company that wins Phase II later (matched by exact name + postal code)
    records.append(
        sbir("Quantum Loom LLC", address=town(20), awarded=date(2022, 2, 1), employee_count=4)
    )
    records.append(
        sbir(
            "Quantum Loom LLC", address=town(20), awarded=date(2023, 9, 1), phase=SbirPhase.PHASE_II
        )
    )
    # Out-of-state and excluded companies are never candidates
    records.append(
        form_d("Keystone Labs Inc", cik="0003000001", address=PA, filed=date(2022, 5, 1))
    )
    records.append(
        form_d(
            "Beacon Fund II, L.P.",
            cik="0003000002",
            address=town(30),
            filed=date(2022, 5, 1),
            industry_group="Pooled Investment Fund",
        )
    )
    return records


def test_gauge_ranks_follow_on_companies_above_the_raise_size_baseline():
    report = run_backtest(dataset(), cutoff=CUTOFF, k=7)
    o = report.overall
    assert o.candidates == 13  # 6 + 6 + 1; PA and fund excluded
    assert o.positives == 7
    assert o.gauge.hits == 7
    raise_baseline = next(b for b in o.baselines if b.name == "largest_recent_raise")
    assert raise_baseline.hits < o.gauge.hits


def test_future_records_cannot_change_the_ranking():
    records = dataset()
    base = run_backtest(records, cutoff=CUTOFF, k=7)
    extra = [
        form_d(
            f"Mature {i} Corp",
            cik=f"00020000{i:02d}",
            address=town(i),
            filed=date(2024, 1, 1),
            revenue_range="No Revenues",
        )
        for i in range(6, 12)
    ]
    later = run_backtest(records + extra, cutoff=CUTOFF, k=7)
    assert later.overall.gauge.top == base.overall.gauge.top
    assert later.overall.positives == base.overall.positives + 6  # outcomes do change


def test_cold_start_group_is_reported_separately():
    report = run_backtest(dataset(), cutoff=CUTOFF, k=25)
    cold = report.cold_start
    assert cold.candidates == 7  # the six 2022 seedlings + the 2022 SBIR company
    assert cold.gauge.hits == 7


def test_amendments_and_small_raises_are_not_outcomes():
    records = [
        form_d("Solo Inc", cik="0004000001", address=town(40), filed=date(2022, 6, 1)),
        form_d(
            "Solo Inc",
            cik="0004000001",
            address=town(40),
            filed=date(2023, 6, 1),
            is_amendment=True,
            total_offering_amount=5_000_000.0,
        ),
        form_d(
            "Solo Inc",
            cik="0004000001",
            address=town(40),
            filed=date(2023, 7, 1),
            total_offering_amount=200_000.0,
            total_amount_sold=None,
        ),
    ]
    assert run_backtest(records, cutoff=CUTOFF).overall.positives == 0


def test_report_states_limits():
    text = to_markdown(run_backtest(dataset(), cutoff=CUTOFF, k=7))
    assert "What this does and does not show" in text
    assert "Does not:" in text and "Cold start" in text and "strongest baseline" in text


def test_bad_window_is_rejected():
    with pytest.raises(ValueError):
        run_backtest([], cutoff=CUTOFF, outcome_end=CUTOFF)


def test_cli(tmp_path, capsys):
    path = tmp_path / "records.json"
    dump_records(dataset(), path)
    assert main([str(path), "--k", "7", "--out", str(tmp_path / "r.md")]) == 0
    assert "Top-25 discovery backtest" in (tmp_path / "r.md").read_text()


def test_ties_at_rank_k_are_flagged():
    records = [
        form_d(
            f"Twin {i} Inc", cik=f"00050000{i:02d}", address=town(50 + i), filed=date(2022, 6, 1)
        )
        for i in range(5)
    ]
    report = run_backtest(records, cutoff=CUTOFF, k=2)
    assert report.overall.gauge_ties_at_k == 5
    assert "arbitrary" in to_markdown(report)
