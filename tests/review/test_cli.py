from gauge.core.models import Address
from gauge.core.serialize import dump_records
from gauge.review.cli import main
from gauge.review.store import JsonReviewStore
from tests.factories import form_d, sbir

NEWARK = Address(city="Newark", state="NJ", postal_code="07102")


def test_review_workflow_without_touching_the_database(tmp_path, capsys):
    records, store = tmp_path / "records.json", tmp_path / "review.json"
    dump_records(
        [form_d("Acme Robotics, Inc.", cik="0001"), sbir("Acme Robotics", address=NEWARK)], records
    )

    assert main(["--store", str(store), "link", str(records)]) == 0
    assert "1 open review items" in capsys.readouterr().out
    (item,) = JsonReviewStore(store).items()

    assert main(["--store", str(store), "reject", item.item_id, "--by", "Priya"]) == 0
    assert "rejected (by Priya)" in capsys.readouterr().out
    assert main(["--store", str(store), "show", item.item_id]) == 0
    assert "human:Priya reject_merge" in capsys.readouterr().out

    assert main(["--store", str(store), "search", str(records), "acme"]) == 0
    out = capsys.readouterr().out
    assert out.count("Acme Robotics") >= 2  # rejected: still two companies

    assert main(["--store", str(store), "show", "rv_missing"]) == 1
