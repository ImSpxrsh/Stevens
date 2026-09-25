"""A small, inspectable logistic-regression model.

Pure Python on purpose: a dozen 0/1 features do not need numpy, and keeping
the weights in a plain dict means a partner can read the whole model.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from gauge.classifier.features import FEATURE_NAMES


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


@dataclass(frozen=True)
class LogisticModel:
    weights: Mapping[str, float]
    bias: float
    version: str
    notes: str = ""
    feature_names: tuple[str, ...] = field(default=FEATURE_NAMES)

    def logit(self, x: Mapping[str, float]) -> float:
        return self.bias + sum(self.weights.get(n, 0.0) * x.get(n, 0.0) for n in self.feature_names)

    def predict_proba(self, x: Mapping[str, float]) -> float:
        return _sigmoid(self.logit(x))

    def contributions(self, x: Mapping[str, float]) -> dict[str, float]:
        return {n: self.weights.get(n, 0.0) * x.get(n, 0.0) for n in self.feature_names}


# Hand-set starting weights. They encode the sourcing team's priors and are
# meant to be replaced by `fit` once the #22 labeling sample exists.
PRIOR_MODEL = LogisticModel(
    weights={
        "incorporated_within_5y": 1.6,
        "incorporated_over_5y": -1.2,
        "no_revenue": 0.8,
        "revenue_over_1m": -0.8,
        "tech_industry": 0.9,
        "equity_offering": 0.5,
        "offering_under_10m": 0.4,
        "sbir_phase_i": 1.0,
        "sbir_phase_ii": 0.6,
        "small_team": 0.7,
        "large_team": -1.5,
        "first_record_recent": 0.6,
    },
    bias=-1.0,
    version="prior-2026-09",
    notes="Hand-set priors; refit on the #22 hand-labeled sample before quoting precision.",
)


def fit(
    rows: Sequence[Mapping[str, float]],
    labels: Sequence[int],
    *,
    version: str,
    l2: float = 0.1,
    learning_rate: float = 0.5,
    epochs: int = 2000,
    start: LogisticModel = PRIOR_MODEL,
) -> LogisticModel:
    """Fit by full-batch gradient descent with L2 shrinkage toward ``start``.

    Shrinking toward the priors (rather than toward zero) keeps a small
    labeled sample from flipping weights it has no data about.
    """
    if len(rows) != len(labels) or not rows:
        raise ValueError("fit needs the same nonzero number of rows and labels")
    if any(y not in (0, 1) for y in labels):
        raise ValueError("labels must be 0 or 1")

    names = start.feature_names
    w = {n: start.weights.get(n, 0.0) for n in names}
    b = start.bias
    n_rows = len(rows)
    for _ in range(epochs):
        grad_w = dict.fromkeys(names, 0.0)
        grad_b = 0.0
        for x, y in zip(rows, labels, strict=True):
            z = b + sum(w[n] * x.get(n, 0.0) for n in names)
            err = _sigmoid(z) - y
            grad_b += err
            for n in names:
                grad_w[n] += err * x.get(n, 0.0)
        for n in names:
            penalty = l2 * (w[n] - start.weights.get(n, 0.0))
            w[n] -= learning_rate * (grad_w[n] / n_rows + penalty)
        b -= learning_rate * grad_b / n_rows

    return LogisticModel(
        weights=w,
        bias=b,
        version=version,
        notes=f"Fit on {n_rows} labeled rows from {start.version}.",
        feature_names=names,
    )
