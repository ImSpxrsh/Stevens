"""JSON (de)serialization for normalized records.

Used for fixtures, local record dumps, and the review CLI. Dates are ISO
strings; enums are their values.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, fields
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from gauge.core.models import (
    Address,
    FormDFacts,
    NormalizedRecord,
    Provenance,
    SbirFacts,
    SbirPhase,
    SourceType,
)

_FORM_D_DATES = {"date_of_first_sale"}
_SBIR_DATES = {"award_start", "award_end"}


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple | list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items() if v is not None}
    return value


def record_to_dict(record: NormalizedRecord) -> dict[str, Any]:
    return {k: _plain(v) for k, v in asdict(record).items() if v is not None}


def record_from_dict(d: dict[str, Any]) -> NormalizedRecord:
    p = d["provenance"]
    form_d = None
    if d.get("form_d") is not None:
        fd = dict(d["form_d"])
        for k in _FORM_D_DATES & fd.keys():
            fd[k] = date.fromisoformat(fd[k])
        fd["securities_offered"] = tuple(fd.get("securities_offered", ()))
        form_d = FormDFacts(**_known(FormDFacts, fd))
    sbir = None
    if d.get("sbir") is not None:
        sb = dict(d["sbir"])
        for k in _SBIR_DATES & sb.keys():
            sb[k] = date.fromisoformat(sb[k])
        sb["phase"] = SbirPhase(sb["phase"])
        sbir = SbirFacts(**_known(SbirFacts, sb))
    return NormalizedRecord(
        provenance=Provenance(
            SourceType(p["source_type"]),
            p["source_id"],
            p["source_url"],
            date.fromisoformat(p["source_date"]),
        ),
        name=d["name"],
        address=Address(**d["address"]) if d.get("address") else None,
        cik=d.get("cik"),
        form_d=form_d,
        sbir=sbir,
    )


def _known(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    names = {f.name for f in fields(cls)}
    unknown = set(data) - names
    if unknown:
        raise ValueError(f"unknown {cls.__name__} fields: {sorted(unknown)}")
    return data


def load_records(path: str | Path) -> list[NormalizedRecord]:
    return [record_from_dict(d) for d in json.loads(Path(path).read_text())]


def dump_records(records: Iterable[NormalizedRecord], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps([record_to_dict(r) for r in records], indent=2, sort_keys=True) + "\n"
    )
