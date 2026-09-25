from datetime import date

from gauge.core.models import SbirPhase
from gauge.core.serialize import dump_records, load_records, record_from_dict, record_to_dict
from tests.factories import form_d, sbir


def test_records_round_trip_through_json(tmp_path):
    records = [
        form_d(date_of_first_sale=date(2022, 5, 5), total_offering_amount=None),
        sbir(phase=SbirPhase.PHASE_II, place_of_performance_state="NJ"),
    ]
    path = tmp_path / "records.json"
    dump_records(records, path)
    assert load_records(path) == records


def test_unknown_fields_are_rejected():
    d = record_to_dict(form_d())
    d["form_d"]["surprise"] = 1
    try:
        record_from_dict(d)
    except ValueError as e:
        assert "surprise" in str(e)
    else:
        raise AssertionError("expected ValueError")
