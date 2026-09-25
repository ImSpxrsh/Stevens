import pytest

from gauge.core.names import name_similarity, normalize_company_name, normalize_town


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Acme Robotics, Inc.", "acme robotics"),
        ("ACME ROBOTICS INC", "acme robotics"),
        ("Acme Robotics L.L.C.", "acme robotics"),
        ("The Garden & Gun Co.", "garden and gun"),
        ("Inc", "inc"),
    ],
)
def test_normalize_company_name(raw, expected):
    assert normalize_company_name(raw) == expected


def test_similarity_ignores_suffix_and_word_order():
    assert name_similarity("Acme Robotics, Inc.", "Robotics Acme LLC") == 1.0
    assert name_similarity("Acme Robotics", "Zenith Therapeutics") < 0.5


def test_normalize_town():
    assert normalize_town("Montclair Twp.") == "montclair township"
    assert normalize_town(None) == ""
