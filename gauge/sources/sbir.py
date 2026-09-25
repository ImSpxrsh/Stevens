"""SBIR.gov bulk award data -> NormalizedRecords.

Source: https://data.www.sbir.gov/awarddatapublic/award_data.csv (the
SBIR.gov award data download). The file also carries personal contact and
principal-investigator names, emails, and phone numbers; this reader never
reads those columns, so they cannot reach records, logs, or outputs.
"""

from __future__ import annotations

import csv
import hashlib
import sys
from collections.abc import Collection
from datetime import date, datetime
from pathlib import Path

from gauge.core.models import (
    Address,
    NormalizedRecord,
    Provenance,
    SbirFacts,
    SbirPhase,
    SourceType,
)

DATASET_URL = "https://data.www.sbir.gov/awarddatapublic/award_data.csv"

# The only columns read. Contact/PI fields are deliberately absent.
COLUMNS = (
    "Company",
    "Award Title",
    "Agency",
    "Phase",
    "Program",
    "Agency Tracking Number",
    "Contract",
    "Proposal Award Date",
    "Contract End Date",
    "Award Year",
    "Award Amount",
    "Number Employees",
    "City",
    "State",
    "Zip",
    "Abstract",
)

AGENCIES = {
    "Department of Health and Human Services": "HHS",
    "National Science Foundation": "NSF",
    "Department of Defense": "DOD",
    "Department of Energy": "DOE",
    "National Aeronautics and Space Administration": "NASA",
    "Department of Agriculture": "USDA",
    "Department of Homeland Security": "DHS",
    "Department of Commerce": "DOC",
    "Department of Transportation": "DOT",
    "Environmental Protection Agency": "EPA",
    "Department of Education": "ED",
}

_PHASES = {"Phase I": SbirPhase.PHASE_I, "Phase II": SbirPhase.PHASE_II}
ABSTRACT_LIMIT = 1500


def _date(v: str | None) -> date | None:
    try:
        return datetime.strptime((v or "").strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def _number(v: str | None) -> float | None:
    try:
        return float((v or "").replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def read_awards(path: str | Path, states: Collection[str] = ("NJ",)) -> list[NormalizedRecord]:
    wanted = {s.upper() for s in states}
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    seen: dict[str, NormalizedRecord] = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            if (row.get("State") or "").strip().upper() not in wanted:
                continue
            rec = _record({k: row.get(k) or "" for k in COLUMNS})
            if rec is not None:
                seen.setdefault(rec.provenance.source_id, rec)
    return sorted(seen.values(), key=lambda r: (r.source_date, r.key))


def _record(row: dict[str, str]) -> NormalizedRecord | None:
    phase = _PHASES.get(row["Phase"].strip())
    name = row["Company"].strip()
    awarded = _date(row["Proposal Award Date"])
    if awarded is None and row["Award Year"].strip().isdigit():
        awarded = date(int(row["Award Year"]), 1, 1)  # year-only awards: dated Jan 1
    if phase is None or not name or awarded is None:
        return None
    key = "|".join(
        (row["Agency"], row["Agency Tracking Number"], row["Contract"], row["Phase"], name.upper())
    )
    source_id = "sbir-" + hashlib.sha256(key.encode()).hexdigest()[:16]
    contract = row["Contract"].strip() or row["Agency Tracking Number"].strip()
    employees = _number(row["Number Employees"])
    abstract = row["Abstract"].strip()
    return NormalizedRecord(
        provenance=Provenance(
            SourceType.SBIR_STTR,
            source_id,
            f"{DATASET_URL}#contract={contract}",
            awarded,
        ),
        name=name,
        address=Address(
            city=row["City"].strip().title() or None,
            state=row["State"].strip().upper() or None,
            postal_code=row["Zip"].strip() or None,
        ),
        sbir=SbirFacts(
            phase=phase,
            program=row["Program"].strip() or "SBIR",
            agency=AGENCIES.get(row["Agency"].strip(), row["Agency"].strip() or None),
            award_amount=_number(row["Award Amount"]),
            award_start=awarded,
            award_end=_date(row["Contract End Date"]),
            topic_title=row["Award Title"].strip() or None,
            abstract=abstract[:ABSTRACT_LIMIT] or None,
            employee_count=int(employees) if employees is not None else None,
        ),
    )
