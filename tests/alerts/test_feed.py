from datetime import date

import pytest

from gauge.alerts import AlertLog, AlertStatus, AlertType, generate
from gauge.core.models import Address, SbirPhase
from gauge.pipeline import run
from gauge.review import Action, ReviewStore
from tests.factories import form_d, sbir

AS_OF = date(2026, 9, 1)
SINCE = date(2026, 1, 1)
NEWARK = Address(city="Newark", state="NJ", postal_code="07102")


def records():
    return [
        form_d(
            "Acme Robotics, Inc.", cik="0001", filed=date(2025, 3, 1), revenue_range="No Revenues"
        ),
        form_d(
            "Acme Robotics, Inc.", cik="0001", filed=date(2026, 5, 1), total_offering_amount=4e6
        ),
        form_d("Acme Robotics, Inc.", cik="0001", filed=date(2026, 6, 1), is_amendment=True),
        sbir("Acme Robotics", address=NEWARK, awarded=date(2026, 4, 1), phase=SbirPhase.PHASE_II),
        form_d(
            "Brand New Bio Inc",
            cik="0002",
            filed=date(2026, 7, 1),
            revenue_range="No Revenues",
            industry_group="Biotechnology",
        ),
        form_d(
            "Harbor Fund II, L.P.",
            cik="0003",
            filed=date(2026, 7, 1),
            industry_group="Pooled Investment Fund",
        ),
    ]


def by_type(alerts):
    return {a.type: a for a in alerts}


def test_event_types_summaries_and_sources():
    recs = records()
    alerts = generate(run(recs, AS_OF, ReviewStore()), ReviewStore(), since=SINCE)
    got = by_type(alerts)
    assert set(got) == {
        AlertType.RAISED_AGAIN,
        AlertType.NEW_LIKELY_STARTUP,
        AlertType.PHASE_II_WIN,
    }
    raised = got[AlertType.RAISED_AGAIN]
    assert raised.status is AlertStatus.READY and "Exact SEC company ID" in raised.why
    assert raised.source_url == recs[1].provenance.source_url
    assert "$4,000,000" in raised.summary
    assert got[AlertType.NEW_LIKELY_STARTUP].company_name == "Brand New Bio Inc"


def test_amendments_old_records_and_excluded_companies_do_not_alert():
    alerts = generate(run(records(), AS_OF, ReviewStore()), ReviewStore(), since=SINCE)
    keys = {a.record_key for a in alerts}
    recs = records()
    assert all("Harbor" not in a.company_name for a in alerts)
    assert len([a for a in alerts if a.type is AlertType.RAISED_AGAIN]) == 1
    assert recs[0].key not in keys


def test_fuzzy_matched_award_is_held_until_a_person_approves():
    recs, store, log = records(), ReviewStore(), AlertLog()
    log.add(generate(run(recs, AS_OF, store), store, since=SINCE))
    phase_ii = by_type(log.alerts())[AlertType.PHASE_II_WIN]
    assert phase_ii.status is AlertStatus.HELD
    with pytest.raises(ValueError):
        log.set_status(phase_ii.alert_id, AlertStatus.SENT)

    (item,) = store.items()
    store.decide(item.item_id, Action.APPROVE_MERGE, "Priya")
    log.add(generate(run(recs, AS_OF, store), store, since=SINCE))
    wins = [a for a in log.alerts() if a.type is AlertType.PHASE_II_WIN]
    ready = [a for a in wins if a.status is AlertStatus.READY]
    assert len(ready) == 1 and ready[0].company_id == "cik:0001"
    assert [a.status for a in wins if a is not ready[0]] == [AlertStatus.DISMISSED]


def test_rejected_match_never_alerts_for_the_candidate():
    recs, store = records(), ReviewStore()
    run(recs, AS_OF, store)
    (item,) = store.items()
    store.decide(item.item_id, Action.REJECT_MERGE, "Priya")
    alerts = generate(run(recs, AS_OF, store), store, since=SINCE)
    assert not any(a.record_key == recs[3].key and a.company_id == "cik:0001" for a in alerts)


def test_dedupe_across_reruns_keeps_status(tmp_path):
    path = tmp_path / "alerts.json"
    recs = records()
    first = AlertLog(path).add(
        generate(run(recs, AS_OF, ReviewStore()), ReviewStore(), since=SINCE)
    )
    assert first
    raised = next(a for a in first if a.type is AlertType.RAISED_AGAIN)
    AlertLog(path).set_status(raised.alert_id, AlertStatus.SENT)
    again = AlertLog(path).add(
        generate(run(recs, AS_OF, ReviewStore()), ReviewStore(), since=SINCE)
    )
    assert again == []
    log = AlertLog(path)
    assert len(log.alerts()) == len(first)
    assert next(a for a in log.alerts() if a.alert_id == raised.alert_id).status is AlertStatus.SENT
