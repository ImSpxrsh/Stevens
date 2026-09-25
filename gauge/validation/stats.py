"""Small statistics helpers for validation reports."""

from __future__ import annotations

import math


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval for a proportion; None when there are no trials.

    Better behaved than the normal approximation at the small sample sizes and
    extreme proportions a 100-record check produces.
    """
    if trials <= 0:
        return None
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def fmt_rate(successes: int, trials: int) -> str:
    """'72% (95% CI 62%-80%, n=100)' or 'n/a (n=0)'."""
    ci = wilson_interval(successes, trials)
    if ci is None:
        return "n/a (n=0)"
    return f"{successes / trials:.0%} (95% CI {ci[0]:.0%}-{ci[1]:.0%}, n={trials})"
