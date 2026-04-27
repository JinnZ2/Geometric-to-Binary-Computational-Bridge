"""
primitives_encoder — bundle SensorReadings into Primitives + serialise.

A :class:`Primitive` is the framework's atomic unit of *measurement*:
one moment, one location, one set of co-located observations, one
explicit confidence value. Primitives are written to ``.obs`` files
(one per line, tab-delimited) for transmission and archival.

A :class:`Primitive` is **not** a CLAIM_SCHEMA claim. Claims are
*differential laws* that hold under stated bounds; primitives are
the timestamped data that supports or falsifies them. Each primitive
may carry a ``claim_ref`` linking it to a CLAIM_SCHEMA id (see
:func:`primitives_to_claim_evidence` for the integration helper).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sensing.firmware.sensor_drivers.base import SensorReading
from sensing.processing.epi_classifier import (
    Epistemology,
    classify_confidence,
    epi_for_readings,
)


# ----------------------------------------------------------------------
# Primitive
# ----------------------------------------------------------------------

@dataclass
class Primitive:
    """
    Atomic measurement record.

    Attributes
    ----------
    concept_id
        Stable handle for the *thing* being observed
        (``"soil_regime_KV"``, ``"bear_activity"``).
    domain
        High-level taxonomy slot
        (``"measured_kinesthetic"`` for direct sensor data,
        ``"derived_thermodynamic"`` for processed regime indicators).
    form
        Compact JSON dump of the raw values, capped to the line-format
        budget at write time. The full :class:`SensorReading` list is
        retained on the Primitive in :attr:`readings` for richer
        downstream consumers.
    role
        Short role tag
        (``"direct_observation"`` / ``"anomaly_signal"`` / ``"calibration"``).
    couplings
        Other concept ids this measurement co-varies with — fed to
        the intersection layer when multiple Primitives are composed.
    bounds
        ``(spatial, temporal, scale)`` triple — same shape as the
        CLAIM_SCHEMA bounds field so a Primitive's bounds are
        directly comparable to a Claim's.
    epi / epi_confidence
        Epistemology label + numeric confidence in ``[0, 1]``.
    timestamp
        UTC ISO-8601, taken from the most-recent reading.
    claim_ref
        Optional CLAIM_SCHEMA id this Primitive bears on (e.g. a soil
        moisture reading bears on ``ohmic_dissip`` only loosely but on
        a future ``soil_regime`` claim directly).
    readings
        The full :class:`SensorReading` list. Not serialised to the
        ``.obs`` line — kept on the in-memory object for richer
        consumers.
    """

    concept_id: str
    domain: str
    form: str
    role: str
    couplings: List[str]
    bounds: Tuple[str, str, str]
    epi: Epistemology
    epi_confidence: float
    timestamp: str
    claim_ref: Optional[str] = None
    readings: List[SensorReading] = field(default_factory=list, repr=False)


# ----------------------------------------------------------------------
# Builder
# ----------------------------------------------------------------------

def build_primitive(
    *,
    concept_id: str,
    domain: str,
    role: str,
    couplings: Sequence[str],
    bounds: Tuple[str, str, str],
    readings: Sequence[SensorReading],
    base_confidence_grades: Sequence[float],
    claim_ref: Optional[str] = None,
    is_calibrated: bool = True,
    near_saturation: bool = False,
    has_baseline: bool = True,
    form_budget_chars: int = 240,
) -> Primitive:
    """
    Construct a :class:`Primitive` from one or more SensorReadings.

    ``base_confidence_grades`` is a parallel sequence to ``readings``;
    each entry is the corresponding driver's headline grade
    (``driver.confidence_grade``). The combined confidence is the
    minimum of the per-reading confidences after classification —
    a Primitive can only be as trustworthy as its weakest input.
    """
    if not readings:
        raise ValueError("at least one reading is required")
    if len(base_confidence_grades) != len(readings):
        raise ValueError(
            "base_confidence_grades must be the same length as readings"
        )

    confidences = [
        classify_confidence(
            grade, r,
            is_calibrated=is_calibrated,
            near_saturation=near_saturation,
            has_baseline=has_baseline,
        )
        for grade, r in zip(base_confidence_grades, readings)
    ]
    epi_conf = round(min(confidences), 3)

    payload = {
        r.sensor_id: r.values for r in readings
    }
    form_dump = json.dumps(payload, separators=(",", ":"))
    if len(form_dump) > form_budget_chars:
        form_dump = form_dump[: form_budget_chars - 3] + "..."

    return Primitive(
        concept_id=concept_id,
        domain=domain,
        form=form_dump,
        role=role,
        couplings=list(couplings),
        bounds=tuple(bounds),  # type: ignore[arg-type]
        epi=epi_for_readings(readings),
        epi_confidence=epi_conf,
        timestamp=readings[-1].timestamp_iso,
        claim_ref=claim_ref,
        readings=list(readings),
    )


# ----------------------------------------------------------------------
# Line-format codec
# ----------------------------------------------------------------------
# Tab-delimited, one Primitive per line. Fields:
#
#   concept_id \t domain \t form \t role \t couplings \t
#   bounds \t epi \t epi_confidence \t timestamp \t claim_ref
#
# Multi-valued ``couplings`` is comma-joined.
# ``bounds`` is comma-joined (3-tuple).
# ``form`` may include commas; tabs are forbidden in any field.
# ``claim_ref`` is the literal "-" when absent (so the column count is
# stable for awk-style parsing).

_OBS_FIELDS = (
    "concept_id", "domain", "form", "role",
    "couplings", "bounds", "epi", "epi_confidence",
    "timestamp", "claim_ref",
)


def primitive_to_obs_line(p: Primitive) -> str:
    """Serialise a Primitive to one ``.obs`` line."""
    fields = [
        p.concept_id,
        p.domain,
        p.form,
        p.role,
        ",".join(p.couplings),
        ",".join(p.bounds),
        p.epi.value if isinstance(p.epi, Epistemology) else str(p.epi),
        f"{float(p.epi_confidence):.3f}",
        p.timestamp,
        p.claim_ref if p.claim_ref else "-",
    ]
    for f in fields:
        if "\t" in f or "\n" in f:
            raise ValueError(
                f"primitive {p.concept_id!r} contains a tab or newline "
                f"in a field — would corrupt the .obs format"
            )
    return "\t".join(fields)


def obs_line_to_primitive(line: str) -> Primitive:
    """Inverse of :func:`primitive_to_obs_line`. Drops the ``readings``
    list (it's not stored on disk)."""
    parts = line.rstrip("\n").split("\t")
    if len(parts) != len(_OBS_FIELDS):
        raise ValueError(
            f"expected {len(_OBS_FIELDS)} tab-delimited fields, "
            f"got {len(parts)}: {line!r}"
        )
    d = dict(zip(_OBS_FIELDS, parts))
    bounds_parts = d["bounds"].split(",")
    if len(bounds_parts) != 3:
        raise ValueError(
            f"bounds must have exactly 3 comma-separated parts: "
            f"{d['bounds']!r}"
        )
    return Primitive(
        concept_id=d["concept_id"],
        domain=d["domain"],
        form=d["form"],
        role=d["role"],
        couplings=[s for s in d["couplings"].split(",") if s],
        bounds=tuple(bounds_parts),  # type: ignore[arg-type]
        epi=Epistemology(d["epi"]),
        epi_confidence=float(d["epi_confidence"]),
        timestamp=d["timestamp"],
        claim_ref=None if d["claim_ref"] == "-" else d["claim_ref"],
        readings=[],
    )


def append_obs(path: str, primitive: Primitive) -> None:
    """Append one Primitive to a ``.obs`` file (text mode)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(primitive_to_obs_line(primitive) + "\n")


def read_obs(path: str) -> List[Primitive]:
    """Read a whole ``.obs`` file back into Primitives."""
    out: List[Primitive] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            out.append(obs_line_to_primitive(line))
    return out


# ----------------------------------------------------------------------
# JSON codec (for debugging / pretty pipelines)
# ----------------------------------------------------------------------

def primitive_to_json(p: Primitive) -> str:
    out = asdict(p)
    out["epi"] = p.epi.value if isinstance(p.epi, Epistemology) else str(p.epi)
    # SensorReading objects are dataclasses too — ``asdict`` already
    # handled them. Drop them from the JSON shape to keep it small.
    out["readings"] = [
        {k: v for k, v in r.items() if k != "raw"}
        for r in out["readings"]
    ]
    return json.dumps(out, separators=(",", ":"), default=str)


# ----------------------------------------------------------------------
# CLAIM_SCHEMA bridge
# ----------------------------------------------------------------------

def primitives_to_claim_evidence(
    primitives: Iterable[Primitive],
    claim_id: str,
) -> Dict[str, Any]:
    """
    Filter ``primitives`` down to the ones that explicitly support
    ``claim_id`` (via ``primitive.claim_ref``) and return a small
    summary suitable for attaching to a CLAIM_SCHEMA claim.

    The returned shape is intentionally minimal: count + mean
    confidence + earliest/latest timestamp + the bounds-set the
    primitives agree on. Use it to feed a future ``meas`` field on a
    Claim, or to render a "this law is currently supported by N
    field measurements" badge.
    """
    matching = [p for p in primitives if p.claim_ref == claim_id]
    if not matching:
        return {
            "claim_ref":             claim_id,
            "supporting_primitives": 0,
        }
    confs = [p.epi_confidence for p in matching]
    timestamps = sorted(p.timestamp for p in matching)
    bounds_set = sorted({",".join(p.bounds) for p in matching})
    return {
        "claim_ref":             claim_id,
        "supporting_primitives": len(matching),
        "mean_confidence":       round(sum(confs) / len(confs), 3),
        "min_confidence":        min(confs),
        "earliest_timestamp":    timestamps[0],
        "latest_timestamp":      timestamps[-1],
        "distinct_bounds":       bounds_set,
    }


__all__ = [
    "Primitive",
    "build_primitive",
    "primitive_to_obs_line",
    "obs_line_to_primitive",
    "append_obs",
    "read_obs",
    "primitive_to_json",
    "primitives_to_claim_evidence",
]
