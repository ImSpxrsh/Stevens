"""Label each canonical company: likely startup, not a startup, or uncertain."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from gauge.classifier.exclusions import Exclusion, hard_exclusion
from gauge.classifier.features import FEATURE_DESCRIPTIONS, extract_features
from gauge.classifier.model import PRIOR_MODEL, LogisticModel
from gauge.core.models import CompanyProfile, Provenance

LIKELY_THRESHOLD = 0.70
NOT_STARTUP_THRESHOLD = 0.30
TOP_FEATURES = 4


class StartupLabel(StrEnum):
    LIKELY_STARTUP = "likely_startup"
    NOT_STARTUP = "not_startup"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class FeatureContribution:
    name: str
    description: str
    contribution: float  # weight * value; positive pushes toward "startup"
    sources: tuple[Provenance, ...]


@dataclass(frozen=True)
class Classification:
    company_id: str
    label: StartupLabel
    probability: float | None  # model P(startup); None when a hard rule decided
    confidence: float | None  # probability of the returned label; None for hard rules
    top_features: tuple[FeatureContribution, ...]
    exclusion: Exclusion | None
    model_version: str
    as_of: date

    @property
    def excluded(self) -> bool:
        return self.exclusion is not None


def classify(
    profile: CompanyProfile,
    as_of: date,
    *,
    model: LogisticModel = PRIOR_MODEL,
    public_ciks: Collection[str] = (),
) -> Classification:
    exclusion = hard_exclusion(profile, as_of, public_ciks)
    if exclusion is not None:
        return Classification(
            company_id=profile.company_id,
            label=StartupLabel.NOT_STARTUP,
            probability=None,
            confidence=None,
            top_features=(),
            exclusion=exclusion,
            model_version=model.version,
            as_of=as_of,
        )

    fv = extract_features(profile, as_of)
    contributions = model.contributions(fv.values)
    top = tuple(
        FeatureContribution(name, FEATURE_DESCRIPTIONS[name], c, fv.sources[name])
        for name, c in sorted(contributions.items(), key=lambda kv: -abs(kv[1]))
        if c != 0.0
    )[:TOP_FEATURES]

    has_structured_evidence = bool(profile.as_of(as_of).form_d_records) or bool(
        profile.as_of(as_of).sbir_records
    )
    p = model.predict_proba(fv.values)
    if not has_structured_evidence:
        label = StartupLabel.UNCERTAIN
    elif p >= LIKELY_THRESHOLD:
        label = StartupLabel.LIKELY_STARTUP
    elif p <= NOT_STARTUP_THRESHOLD:
        label = StartupLabel.NOT_STARTUP
    else:
        label = StartupLabel.UNCERTAIN

    if label is StartupLabel.LIKELY_STARTUP:
        confidence = p
    elif label is StartupLabel.NOT_STARTUP:
        confidence = 1.0 - p
    else:
        confidence = max(p, 1.0 - p)

    return Classification(
        company_id=profile.company_id,
        label=label,
        probability=p,
        confidence=confidence,
        top_features=top,
        exclusion=None,
        model_version=model.version,
        as_of=as_of,
    )


@dataclass(frozen=True)
class DiscoveryView:
    """How classifications feed the discovery screens.

    ``ranked`` is what discovery shows. Hard-excluded companies never appear
    there. Uncertain companies are kept in their own list for review rather
    than dropped.
    """

    ranked: tuple[Classification, ...]
    uncertain: tuple[Classification, ...]
    excluded: tuple[Classification, ...]
    not_startup: tuple[Classification, ...]


def discovery_view(results: Iterable[Classification]) -> DiscoveryView:
    ranked, uncertain, excluded, not_startup = [], [], [], []
    for r in results:
        if r.excluded:
            excluded.append(r)
        elif r.label is StartupLabel.LIKELY_STARTUP:
            ranked.append(r)
        elif r.label is StartupLabel.UNCERTAIN:
            uncertain.append(r)
        else:
            not_startup.append(r)

    def by_probability(c: Classification) -> tuple[float, str]:
        return (-(c.probability or 0.0), c.company_id)

    return DiscoveryView(
        ranked=tuple(sorted(ranked, key=by_probability)),
        uncertain=tuple(sorted(uncertain, key=by_probability)),
        excluded=tuple(excluded),
        not_startup=tuple(sorted(not_startup, key=by_probability)),
    )
