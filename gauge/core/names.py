"""Company-name and town normalization shared by matching, search, and audits."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# Trailing legal-form words that do not distinguish one company from another.
_LEGAL_SUFFIXES = frozenset(
    {
        "inc",
        "incorporated",
        "llc",
        "corp",
        "corporation",
        "co",
        "company",
        "ltd",
        "limited",
        "lp",
        "llp",
        "pllc",
        "pc",
        "plc",
    }
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_company_name(name: str) -> str:
    """Lowercase, drop punctuation, and strip trailing legal suffixes.

    ``"Acme Robotics, Inc."`` and ``"ACME ROBOTICS INC"`` both become
    ``"acme robotics"``. Dotted forms such as ``"L.L.C."`` are collapsed first.
    """
    text = name.lower().replace("&", " and ")
    text = re.sub(r"\b(l)\.(l)\.(c)\.?", "llc", text)
    text = re.sub(r"\b(l)\.(p)\.?", "lp", text)
    tokens = [t for t in _NON_ALNUM.split(text) if t]
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    while len(tokens) > 1 and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def name_similarity(a: str, b: str) -> float:
    """Similarity in [0, 1] between two company names, ignoring word order."""
    left = " ".join(sorted(normalize_company_name(a).split()))
    right = " ".join(sorted(normalize_company_name(b).split()))
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def normalize_town(town: str | None) -> str:
    if not town:
        return ""
    text = " ".join(_NON_ALNUM.split(town.lower())).strip()
    return re.sub(r"\btwp\b", "township", text)
