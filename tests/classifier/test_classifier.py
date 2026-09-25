from datetime import date

import pytest

from gauge.classifier import (
    PRIOR_MODEL,
    ExclusionReason,
    StartupLabel,
    classify,
    discovery_view,
    fit,
    hard_exclusion,
)
from gauge.classifier.features import FEATURE_NAMES, extract_features
from tests.factories import form_d, profile, sbir

AS_OF = date(2022, 12, 31)


def test_seed_stage_tech_company_is_likely_startup():
    p = profile(form_d(revenue_range="No Revenues", filed=date(2022, 5, 1)))
    result = classify(p, AS_OF)
    assert result.label is StartupLabel.LIKELY_STARTUP
    assert result.confidence == result.probability > 0.9
    assert result.top_features[0].name == "incorporated_within_5y"
    assert result.top_features[0].sources  # every reason cites a filing


def test_sbir_only_small_team_is_likely_startup():
    p = profile(sbir(awarded=date(2022, 3, 1), employee_count=4))
    assert classify(p, AS_OF).label is StartupLabel.LIKELY_STARTUP


def test_older_company_with_revenue_is_not_startup():
    p = profile(
        form_d(
            incorporated_within_five_years=False,
            revenue_range="$5,000,001 - $25,000,000",
            industry_group="Manufacturing",
            filed=date(2018, 1, 1),
        )
    )
    result = classify(p, AS_OF)
    assert result.label is StartupLabel.NOT_STARTUP
    assert result.exclusion is None
    assert result.confidence == pytest.approx(1 - result.probability)


def test_thin_evidence_is_uncertain_not_hidden():
    p = profile(sbir(awarded=date(2015, 3, 1), employee_count=None))
    result = classify(p, AS_OF)
    assert result.label is StartupLabel.UNCERTAIN
    view = discovery_view([result])
    assert view.uncertain == (result,)
    assert view.ranked == ()


def test_every_profile_gets_one_of_three_labels():
    profiles = [
        profile(form_d()),
        profile(sbir()),
        profile(form_d(industry_group="Pooled Investment Fund")),
        profile(form_d(incorporated_within_five_years=False, revenue_range="Over $100,000,000")),
    ]
    for p in profiles:
        assert classify(p, AS_OF).label in set(StartupLabel)


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (form_d(is_pooled_investment_fund=True), ExclusionReason.FUND),
        (form_d(industry_group="Investing"), ExclusionReason.FUND),
        (form_d("Garden State Seed Fund II, L.P."), ExclusionReason.FUND),
        (form_d("Beacon Capital Partners LP"), ExclusionReason.FUND),
        (form_d(industry_group="REITS and Finance"), ExclusionReason.REAL_ESTATE),
        (form_d(industry_group="Residential"), ExclusionReason.REAL_ESTATE),
        (form_d(revenue_range="Over $100,000,000"), ExclusionReason.ESTABLISHED),
        (form_d(year_of_incorporation=1990), ExclusionReason.ESTABLISHED),
        (sbir(employee_count=800), ExclusionReason.ESTABLISHED),
    ],
)
def test_hard_exclusions(record, reason):
    exclusion = hard_exclusion(profile(record), AS_OF)
    assert exclusion is not None
    assert exclusion.reason is reason
    assert exclusion.source == record.provenance


def test_public_company_exclusion_uses_supplied_cik_list():
    p = profile(form_d(cik="0000320193"))
    assert hard_exclusion(p, AS_OF) is None
    exclusion = hard_exclusion(p, AS_OF, public_ciks={"0000320193"})
    assert exclusion.reason is ExclusionReason.PUBLIC_COMPANY


@pytest.mark.parametrize("name", ["Fundly Robotics Inc.", "CrowdFund Health LLC", "Refund Labs"])
def test_fund_like_words_in_startup_names_do_not_exclude(name):
    assert hard_exclusion(profile(form_d(name)), AS_OF) is None


def test_excluded_records_never_reach_discovery():
    fund = classify(profile(form_d(industry_group="Pooled Investment Fund")), AS_OF)
    startup = classify(profile(form_d(revenue_range="No Revenues")), AS_OF)
    view = discovery_view([fund, startup])
    assert fund not in view.ranked
    assert view.excluded == (fund,)
    assert view.ranked == (startup,)
    assert fund.label is StartupLabel.NOT_STARTUP
    assert fund.probability is None


def test_features_ignore_records_after_as_of():
    p = profile(form_d(filed=date(2023, 6, 1), revenue_range="No Revenues"))
    fv = extract_features(p, AS_OF)
    assert set(fv.values) == set(FEATURE_NAMES)
    assert all(v == 0.0 for v in fv.values.values())


def test_discovery_ranks_by_probability():
    strong = classify(profile(form_d(revenue_range="No Revenues")), AS_OF)
    weaker = classify(profile(sbir(employee_count=4)), AS_OF)
    assert discovery_view([weaker, strong]).ranked == (strong, weaker)


def test_fit_moves_weights_toward_labels_and_keeps_version():
    rows = [{"tech_industry": 1.0}] * 20 + [{"tech_industry": 0.0}] * 20
    labels = [0] * 20 + [1] * 20
    refit = fit(rows, labels, version="test-refit", epochs=500)
    assert refit.version == "test-refit"
    assert refit.weights["tech_industry"] < PRIOR_MODEL.weights["tech_industry"]
    # Features with no signal in the sample stay at their prior.
    assert refit.weights["large_team"] == pytest.approx(PRIOR_MODEL.weights["large_team"])


def test_fit_rejects_bad_labels():
    with pytest.raises(ValueError):
        fit([{}], [2], version="x")
