"""
claim_evidence — verify that a Primitive really bears on a Claim.

Up to this point the linkage between a Primitive's ``claim_ref`` and
the CLAIM_SCHEMA Claim it points at has been *descriptive*: nothing
checks that the Primitive's measurement vocabulary actually intersects
the Claim's ``meas`` set. This module closes that gap.

Three pieces:

* :class:`MeasurementVocabulary` — a tiny lookup that maps sensor IDs
  (``"DS18B20.surface"``, ``"MLX90614.canopy"``, …) to the canonical
  CLAIM_TABLE ``meas`` entries (``"thermocouple_array"``, ``"IR_camera"``).
  Default vocabulary covers every sensor driver shipped under
  ``sensing/firmware/``; extend per-deployment for custom hardware.

* :func:`verify_primitive_against_claim` — the structural check.
  Returns a :class:`VerificationResult` carrying ``ok`` and a list of
  human-readable reasons. Used by tests, by the sensing CLI, and by
  any downstream consumer that wants to filter out Primitives whose
  ``claim_ref`` they don't actually back.

* :func:`find_applicable_claims` — given a Primitive (without a
  ``claim_ref``), return the Claim ids whose ``meas`` set overlaps
  the Primitive's vocabulary. Useful when a sensor configuration was
  set up before the claim list was finalised.

Design rule: the verifier is *advisory*, not enforcing. It never
mutates the Primitive or the Claim. Callers decide what to do with a
mismatch — drop, downgrade confidence, requeue for human review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


# ----------------------------------------------------------------------
# Default vocabulary — every shipped sensor driver
# ----------------------------------------------------------------------
#
# Keys are the ``device_name`` class attribute on each SensorDriver
# (case-sensitive). Values are sets of canonical CLAIM_TABLE meas
# entries that a reading from that device legitimately supports.
#
# Add custom hardware by passing an extended vocabulary to
# :func:`verify_primitive_against_claim`; the defaults below are
# treated as an immutable starter set.

_DEFAULT_VOCABULARY: Dict[str, frozenset] = {
    # 1-wire digital temperature
    "DS18B20": frozenset({
        "thermocouple_array", "thermocouple", "IR_camera",
    }),
    # Capacitive soil-moisture probe
    "CapacitiveSoilMoisture": frozenset({
        "four_wire_AC", "eddy_probe",
    }),
    # IR thermometer
    "MLX90614": frozenset({
        "IR_camera", "thermocouple", "thermocouple_array", "bolometer",
    }),
    # Passive-infrared motion
    "PIRMotion": frozenset({
        "free_fall",  # PIR detects motion → kinematic event marker
    }),
    # USB microphone
    "Microphone": frozenset({
        "spectrogram", "FFT", "phase_locked_loop", "pitch_tracker",
    }),
}


@dataclass(frozen=True)
class MeasurementVocabulary:
    """
    Bidirectional mapping between sensor ``device_name`` and
    canonical CLAIM_TABLE ``meas`` entries.

    Use the :meth:`with_extension` helper to add custom hardware
    without mutating the default. The class is frozen so a
    misconfigured vocabulary does not silently propagate through
    a long-running pipeline.
    """

    mapping: Mapping[str, frozenset] = field(
        default_factory=lambda: dict(_DEFAULT_VOCABULARY)
    )

    def measurements_for(self, device_name: str) -> frozenset:
        """Return the canonical ``meas`` entries this device supports."""
        return self.mapping.get(device_name, frozenset())

    def supports(self, device_name: str, claim_meas: str) -> bool:
        return claim_meas in self.measurements_for(device_name)

    def known_devices(self) -> List[str]:
        return sorted(self.mapping)

    def with_extension(
        self,
        extra: Mapping[str, Iterable[str]],
    ) -> "MeasurementVocabulary":
        merged: Dict[str, frozenset] = dict(self.mapping)
        for dev, meas in extra.items():
            existing = merged.get(dev, frozenset())
            merged[dev] = existing | frozenset(meas)
        return MeasurementVocabulary(mapping=merged)


def default_vocabulary() -> MeasurementVocabulary:
    return MeasurementVocabulary()


# ----------------------------------------------------------------------
# Primitive shape (duck-typed)
# ----------------------------------------------------------------------
#
# We avoid importing :class:`sensing.processing.primitives_encoder.Primitive`
# here so this module stays usable from any context. Any object with
# the following attributes is acceptable:
#
#   * ``claim_ref``  — Optional[str]
#   * ``readings``   — iterable; each item has a ``sensor_id`` like
#                      ``"DS18B20.surface"``. Empty list means the
#                      Primitive came back from disk and we fall
#                      back to scanning ``form`` for sensor names.
#   * ``form``       — str (compact JSON of {sensor_id: {channel: value}})
#   * ``bounds``     — 3-tuple of strings


def _device_names_from_primitive(primitive: Any) -> List[str]:
    """
    Extract the set of ``device_name`` strings present in a Primitive.

    Looks at ``readings`` first (richer), then falls back to parsing
    ``form`` JSON (which survives disk round-trips).
    """
    devices: List[str] = []
    seen: set = set()

    for reading in getattr(primitive, "readings", []) or []:
        sid = getattr(reading, "sensor_id", "") or ""
        device = sid.split(".", 1)[0] if "." in sid else sid
        if device and device not in seen:
            devices.append(device)
            seen.add(device)

    if not devices:
        form = getattr(primitive, "form", "") or ""
        if form:
            import json
            try:
                blob = json.loads(form)
            except (json.JSONDecodeError, ValueError):
                blob = None
            if isinstance(blob, dict):
                for sid in blob:
                    device = sid.split(".", 1)[0] if "." in sid else sid
                    if device and device not in seen:
                        devices.append(device)
                        seen.add(device)

    return devices


# ----------------------------------------------------------------------
# Result type
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a single verifier call."""

    ok: bool
    reasons: tuple
    matched_meas: tuple = ()      # claim meas entries this prim supports
    matched_devices: tuple = ()   # device_names that produced a hit

    def __bool__(self) -> bool:   # so callers can `if verify(...): ...`
        return self.ok


# ----------------------------------------------------------------------
# Core verifier
# ----------------------------------------------------------------------

def verify_primitive_against_claim(
    primitive: Any,
    claim: Mapping[str, Any],
    vocabulary: Optional[MeasurementVocabulary] = None,
    *,
    require_bounds_overlap: bool = False,
) -> VerificationResult:
    """
    Check whether ``primitive`` is admissible evidence for ``claim``.

    Conditions checked, in order:

    1. ``primitive.claim_ref`` matches ``claim['id']`` (or is None —
       in which case the function reports "no claim asserted" and
       returns ``ok=False`` so callers don't silently treat
       unattributed Primitives as supporting evidence).
    2. The Primitive's device set has at least one sensor whose
       vocabulary entry appears in ``claim['meas']``.
    3. (Optional) The Primitive's ``bounds`` agree on at least one
       of the three components with the claim's ``bounds``. Disabled
       by default because field bounds (``Superior_MN``,
       ``2026_April``, …) rarely match a claim's lab bounds verbatim.

    Returns a :class:`VerificationResult` even on failure so the
    caller can render the reasons.
    """
    vocab = vocabulary or default_vocabulary()
    reasons: List[str] = []

    claim_id = str(claim.get("id", "") or "")
    claim_meas = list(claim.get("meas", []) or [])

    # 1. claim_ref agreement
    prim_ref = getattr(primitive, "claim_ref", None)
    if prim_ref is None:
        reasons.append(
            "primitive has no claim_ref — cannot match against any claim"
        )
        return VerificationResult(ok=False, reasons=tuple(reasons))
    if prim_ref != claim_id:
        reasons.append(
            f"primitive.claim_ref={prim_ref!r} does not match "
            f"claim.id={claim_id!r}"
        )
        return VerificationResult(ok=False, reasons=tuple(reasons))

    # 2. measurement vocabulary overlap
    devices = _device_names_from_primitive(primitive)
    if not devices:
        reasons.append(
            "primitive has no detectable sensor devices "
            "(empty readings + unparseable form)"
        )
        return VerificationResult(ok=False, reasons=tuple(reasons))

    matched_meas: List[str] = []
    matched_devices: List[str] = []
    for device in devices:
        supports = vocab.measurements_for(device)
        for m in claim_meas:
            if m in supports:
                if m not in matched_meas:
                    matched_meas.append(m)
                if device not in matched_devices:
                    matched_devices.append(device)

    if not matched_meas:
        reasons.append(
            f"none of {devices!r} produces any of "
            f"claim.meas={claim_meas!r} under the supplied vocabulary"
        )
        return VerificationResult(
            ok=False, reasons=tuple(reasons),
            matched_devices=tuple(matched_devices),
        )

    # 3. optional bounds-overlap (disabled by default)
    if require_bounds_overlap:
        prim_bounds = tuple(getattr(primitive, "bounds", ()))
        claim_bounds_str = str(claim.get("bounds", "") or "")
        claim_bounds = tuple(
            s for s in claim_bounds_str.split(",") if s
        )
        overlap = set(prim_bounds) & set(claim_bounds)
        if not overlap:
            reasons.append(
                f"bounds disagree — primitive {prim_bounds!r} vs. "
                f"claim {claim_bounds!r}"
            )
            return VerificationResult(
                ok=False, reasons=tuple(reasons),
                matched_meas=tuple(matched_meas),
                matched_devices=tuple(matched_devices),
            )

    reasons.append(
        f"matched {len(matched_meas)} measurement(s) via "
        f"{len(matched_devices)} device(s)"
    )
    return VerificationResult(
        ok=True, reasons=tuple(reasons),
        matched_meas=tuple(matched_meas),
        matched_devices=tuple(matched_devices),
    )


# ----------------------------------------------------------------------
# Reverse lookup
# ----------------------------------------------------------------------

def find_applicable_claims(
    primitive: Any,
    claims: Sequence[Mapping[str, Any]],
    vocabulary: Optional[MeasurementVocabulary] = None,
) -> List[str]:
    """
    Given a Primitive (with or without a ``claim_ref``), return the
    claim ids whose ``meas`` set overlaps the Primitive's vocabulary.

    Useful when a sensor was deployed before the claim list was
    finalised, or when a Primitive's ``claim_ref`` is ``None`` and
    you want to suggest candidates.
    """
    vocab = vocabulary or default_vocabulary()
    devices = _device_names_from_primitive(primitive)
    if not devices:
        return []

    supported_meas: set = set()
    for d in devices:
        supported_meas |= set(vocab.measurements_for(d))

    out: List[str] = []
    for claim in claims:
        claim_meas = set(claim.get("meas", []) or [])
        if claim_meas & supported_meas:
            out.append(str(claim.get("id", "")))
    return out


# ----------------------------------------------------------------------
# Bulk verification
# ----------------------------------------------------------------------

@dataclass
class BulkVerificationReport:
    """Aggregate verifier output across many Primitives + Claims."""

    total_primitives: int = 0
    verified:        int = 0
    rejected:        int = 0
    unattributed:    int = 0      # primitive.claim_ref is None
    missing_claim:   int = 0      # claim_ref names a non-existent claim
    failures: List[tuple] = field(default_factory=list)
    """Each tuple is ``(primitive_index, claim_ref, reasons)``."""

    def __str__(self) -> str:
        return (
            f"BulkVerificationReport("
            f"total={self.total_primitives}, "
            f"verified={self.verified}, "
            f"rejected={self.rejected}, "
            f"unattributed={self.unattributed}, "
            f"missing_claim={self.missing_claim})"
        )


def verify_primitives_bulk(
    primitives: Sequence[Any],
    claims: Sequence[Mapping[str, Any]],
    vocabulary: Optional[MeasurementVocabulary] = None,
    *,
    require_bounds_overlap: bool = False,
) -> BulkVerificationReport:
    """
    Cross-verify a stream of Primitives against a list of Claims.

    The function never raises — it accumulates failures in the
    returned :class:`BulkVerificationReport`. Useful as the entry
    point for a CI gate that asserts every shipped ``.obs`` file is
    backed by valid claim references.
    """
    vocab = vocabulary or default_vocabulary()
    claim_index = {str(c.get("id", "")): c for c in claims}

    report = BulkVerificationReport(total_primitives=len(primitives))
    for i, prim in enumerate(primitives):
        ref = getattr(prim, "claim_ref", None)
        if ref is None:
            report.unattributed += 1
            continue
        if ref not in claim_index:
            report.missing_claim += 1
            report.failures.append((i, ref, ("claim id not in table",)))
            continue
        result = verify_primitive_against_claim(
            prim, claim_index[ref], vocab,
            require_bounds_overlap=require_bounds_overlap,
        )
        if result.ok:
            report.verified += 1
        else:
            report.rejected += 1
            report.failures.append((i, ref, result.reasons))
    return report


__all__ = [
    "MeasurementVocabulary",
    "default_vocabulary",
    "VerificationResult",
    "BulkVerificationReport",
    "verify_primitive_against_claim",
    "find_applicable_claims",
    "verify_primitives_bulk",
]
