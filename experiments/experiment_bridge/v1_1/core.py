"""Checked numerical RVQ; no code index carries an assumed semantic assignment.

Ordered iterables, including one-shot iterators, are copied with explicit limits.
Arithmetic remains binary64, not exact real/decimal arithmetic. Lossy integer
conversion, nonzero components whose squares round to zero, and additive state
outside the declared tolerance raise ValueError. Other Real inputs may round.
These item limits do not bound execution time of user-defined Python methods.
Hashes identify canonical ordered codebooks, not authenticity or semantic truth.
"""

from collections.abc import Mapping, Set
from dataclasses import dataclass
import hashlib
from itertools import islice
import json
import math
from numbers import Integral, Real

VERSION = "experiment-bridge/v1.1"
MAX_ITERABLE_ITEMS = 4096
MAX_DIMENSION = 4096
MAX_CODES = 4096
MAX_LEVELS = 64
MAX_SAMPLES = 4096
TRACE_REL_TOL = 1e-12
TRACE_ABS_TOL = 1e-12


def _number(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("expected a real number, not bool")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("number cannot be represented as finite binary64") from exc
    if not math.isfinite(result):
        raise ValueError("nonfinite number or arithmetic overflow")
    if isinstance(value, Integral) and int(result) != value:
        raise ValueError("integer cannot be represented exactly as binary64")
    return result


def _items(value, limit=MAX_ITERABLE_ITEMS, name="iterable"):
    if isinstance(value, (str, bytes, bytearray, Mapping, Set)):
        raise ValueError("expected a nonempty ordered iterable")
    try:
        result = tuple(islice(iter(value), limit + 1))
    except (TypeError, ValueError, OverflowError, RuntimeError) as exc:
        raise ValueError(f"cannot read ordered {name}: {exc}") from exc
    if len(result) > limit:
        raise ValueError(f"{name} exceeds limit ({limit} items)")
    if not result:
        raise ValueError("empty input")
    return result


def _vector(value, dimension=None):
    result = tuple(_number(x) for x in _items(value, MAX_DIMENSION, "vector"))
    if dimension is not None and len(result) != dimension:
        raise ValueError("vector dimension mismatch")
    return result


def _matrix(value, dimension=None, limit=MAX_CODES, name="codebook"):
    rows = _items(value, limit, name)
    first = _vector(rows[0], dimension)
    return (first,) + tuple(_vector(row, len(first)) for row in rows[1:])


def _combine(a, b, sign=1):
    return tuple(_number(x + sign * y) for x, y in zip(a, b))


def _squared(vector):
    def square(x):
        result = _number(x * x)
        if x != 0 and result == 0:
            raise ValueError("squared error underflow: nonzero component squared to zero")
        return result

    try:
        return _number(math.fsum(square(x) for x in vector))
    except OverflowError as exc:
        raise ValueError("squared error overflow") from exc


def _identity_close(target, reconstruction, residual):
    return all(abs(t - (c + r)) <= TRACE_REL_TOL * max(1, abs(t), abs(c), abs(r))
               for t, c, r in zip(target, reconstruction, residual))


def _nearest(residual, codebook):
    distances = [_squared(_combine(residual, code, -1)) for code in codebook]
    index = min(range(len(distances)), key=distances.__getitem__)
    return index, distances[index]


def _hash(codebook):
    data = json.dumps(codebook, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class Level:
    """Immutable defensive copy, checked even when constructed directly."""

    codebook: tuple[tuple[float, ...], ...]
    threshold_squared: float
    label: str = ""

    def __post_init__(self):
        object.__setattr__(self, "codebook", _matrix(self.codebook))
        threshold = _number(self.threshold_squared)
        if threshold < 0 or not isinstance(self.label, str):
            raise ValueError("threshold must be nonnegative and label must be a string")
        object.__setattr__(self, "threshold_squared", threshold)

    @property
    def codebook_sha256(self):
        return _hash(self.codebook)


def make_level(codebook, threshold_squared, label="") -> Level:
    return Level(codebook, threshold_squared, label)


def _levels(levels, dimension):
    result = []
    for level in _items(levels, MAX_LEVELS, "levels"):
        if not isinstance(level, Level):
            raise ValueError("levels must contain Level objects")
        checked = make_level(level.codebook, level.threshold_squared, level.label)
        if len(checked.codebook[0]) != dimension:
            raise ValueError("level dimension mismatch")
        result.append(checked)
    return tuple(result)


def walk(target, levels) -> dict:
    """Add accepted nearest codes; reject with zero and unchanged residual.

    Squared error can increase after acceptance. error_reduction is the signed
    error_squared_before minus error_squared_after, not a monotonicity claim.
    Catastrophic cancellation outside the validator's additive tolerance fails
    closed rather than returning a trace that fails its own arithmetic audit.
    """
    target = _vector(target)
    levels = _levels(levels, len(target))
    residual, reconstruction = target, (0.0,) * len(target)
    _squared(residual)
    steps = []
    for number, level in enumerate(levels, 1):
        nearest, distance = _nearest(residual, level.codebook)
        accepted = distance <= level.threshold_squared
        contribution = level.codebook[nearest] if accepted else (0.0,) * len(target)
        after = _combine(reconstruction, contribution)
        remaining = _combine(residual, contribution, -1)
        before_error, after_error = _squared(residual), _squared(remaining)
        if not _identity_close(target, after, remaining):
            raise ValueError("additive identity outside binary64 trace tolerance")
        steps.append({
            "level": number, "codebook_sha256": level.codebook_sha256,
            "nearest_index": nearest, "code_index": nearest if accepted else None,
            "distance_squared": distance, "threshold_squared": level.threshold_squared,
            "numerical_status": "ACCEPTED" if accepted else "REJECTED",
            "contribution": list(contribution),
            "reconstruction_before": list(reconstruction), "reconstruction_after": list(after),
            "residual_before": list(residual), "residual_after": list(remaining),
            "error_squared_before": before_error, "error_squared_after": after_error,
            "error_reduction": before_error - after_error,
        })
        reconstruction, residual = after, remaining
    return {"version": VERSION, "target": list(target), "dimension": len(target),
            "steps": steps, "reconstruction": list(reconstruction), "residual": list(residual)}


def validate_trace(trace, levels=None) -> list[str]:
    """Return diagnostics, including for malformed traces, without calling walk.

    Recompute arithmetic and gates rather than trusting recorded errors/status.
    With levels, also verify actual nearest code, contribution, threshold, hash
    and count. Without them, codebook identity/nearest choice cannot be certified.
    Arithmetic comparisons allow binary64 roundoff (1e-12 relative/absolute).
    Small mutations within that tolerance can pass; this is not exact integrity
    verification. Structured traces and ordinary iterator errors yield diagnostics,
    not a sandbox for arbitrary Python objects or their methods.
    """
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    def close(a, b):
        return math.isclose(a, b, rel_tol=TRACE_REL_TOL, abs_tol=TRACE_ABS_TOL)

    def equal(a, b):
        return all(close(x, y) for x, y in zip(a, b))

    def index(value):
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    try:
        if not isinstance(trace, dict):
            raise ValueError("expected a trace dictionary")
        target = _vector(trace["target"])
        dimension = len(target)
        check(index(trace["dimension"]) and trace["dimension"] == dimension, "dimension mismatch")
        check(trace["version"] == VERSION, "version mismatch")
        if not isinstance(trace["steps"], (list, tuple)):
            raise ValueError("steps must be a list or tuple")
        steps = _items(trace["steps"], MAX_LEVELS, "steps")
        actual_levels = _levels(levels, dimension) if levels is not None else None
        if actual_levels is not None:
            check(len(steps) == len(actual_levels), "level count mismatch")
        _squared(target)
        reconstruction, residual = (0.0,) * dimension, target
        for number, step in enumerate(steps, 1):
            prefix = f"step {number}: "
            try:
                if not isinstance(step, dict):
                    raise ValueError("expected a step dictionary")
                check(index(step["level"]) and step["level"] == number, prefix + "level mismatch")
                digest = step["codebook_sha256"]
                check(isinstance(digest, str) and len(digest) == 64
                      and all(c in "0123456789abcdef" for c in digest), prefix + "invalid hash")
                vectors = {key: _vector(step[key], dimension) for key in (
                    "contribution", "reconstruction_before", "reconstruction_after",
                    "residual_before", "residual_after")}
                contribution = vectors["contribution"]
                rb, ra = vectors["residual_before"], vectors["residual_after"]
                cb, ca = vectors["reconstruction_before"], vectors["reconstruction_after"]
                distance, threshold = _number(step["distance_squared"]), _number(step["threshold_squared"])
                check(distance >= 0 and threshold >= 0, prefix + "negative distance/threshold")
                check(index(step["nearest_index"]), prefix + "invalid nearest index")
                accepted = step["numerical_status"] == "ACCEPTED"
                check(step["numerical_status"] in ("ACCEPTED", "REJECTED"), prefix + "invalid status")
                check(accepted == (distance <= threshold), prefix + "threshold routing mismatch")
                if accepted:
                    check(index(step["code_index"]) and step["code_index"] == step["nearest_index"],
                          prefix + "accepted code index mismatch")
                    check(close(distance, _squared(_combine(rb, contribution, -1))),
                          prefix + "accepted distance mismatch")
                else:
                    check(step["code_index"] is None and all(x == 0 for x in contribution),
                          prefix + "rejection must use null index and zero contribution")
                expected_after = _combine(reconstruction, contribution)
                expected_residual = _combine(residual, contribution, -1)
                check(equal(cb, reconstruction) and equal(rb, residual), prefix + "stale before state")
                check(equal(ca, expected_after) and equal(ra, expected_residual), prefix + "transition mismatch")
                for summed, remaining in ((cb, rb), (ca, ra)):
                    check(_identity_close(target, summed, remaining), prefix + "additive identity mismatch")
                before_error, after_error = _squared(rb), _squared(ra)
                check(close(_number(step["error_squared_before"]), before_error)
                      and close(_number(step["error_squared_after"]), after_error), prefix + "squared error mismatch")
                check(close(_number(step["error_reduction"]), before_error - after_error),
                      prefix + "error reduction mismatch")
                if actual_levels is not None and number <= len(actual_levels):
                    level = actual_levels[number - 1]
                    nearest, actual_distance = _nearest(residual, level.codebook)
                    check(digest == level.codebook_sha256, prefix + "codebook hash mismatch")
                    check(threshold == level.threshold_squared, prefix + "actual threshold mismatch")
                    check(step["nearest_index"] == nearest and distance == actual_distance,
                          prefix + "actual nearest/distance mismatch")
                    actual_accepted = actual_distance <= level.threshold_squared
                    check(accepted == actual_accepted, prefix + "actual routing mismatch")
                    expected_code = level.codebook[nearest] if actual_accepted else (0.0,) * dimension
                    check(contribution == expected_code, prefix + "actual contribution mismatch")
                reconstruction, residual = expected_after, expected_residual
            except (KeyError, TypeError, ValueError, OverflowError, AttributeError, RuntimeError) as exc:
                errors.append(prefix + f"malformed step: {exc}")
        check(equal(_vector(trace["reconstruction"], dimension), reconstruction), "final reconstruction mismatch")
        check(equal(_vector(trace["residual"], dimension), residual), "final residual mismatch")
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError, RuntimeError) as exc:
        errors.append(f"malformed trace or levels: {exc}")
    return errors


def calibrate_thresholds(samples, codebooks, rejection_fraction, gated=True) -> tuple[float, ...]:
    """Illustrative calibration, not a universal semantic or rejection guarantee.

    At each stage sort nearest squared distances ascending. Select the k-th
    value, k=max(1, ceil((1-rejection_fraction)*n)), using one-based order.
    Zero rejection selects the maximum. Inclusive acceptance and ties mean the
    realized rejection fraction is discrete and may be below the requested one.
    Gated trajectories keep rejected samples unchanged; ungated trajectories
    always subtract the nearest code before calibrating the following stage.
    """
    fraction = _number(rejection_fraction)
    if not 0 <= fraction < 1 or not isinstance(gated, bool):
        raise ValueError("rejection_fraction must be in [0, 1); gated must be bool")
    residuals = _matrix(samples, limit=MAX_SAMPLES, name="samples")
    books = tuple(_matrix(book, len(residuals[0]))
                  for book in _items(codebooks, MAX_LEVELS, "codebooks"))
    for residual in residuals:
        _squared(residual)
    thresholds = []
    for book in books:
        choices = [_nearest(residual, book) for residual in residuals]
        ordered = sorted(distance for _, distance in choices)
        k = len(ordered) if fraction == 0 else max(1, math.ceil((1 - fraction) * len(ordered)))
        threshold = ordered[min(k, len(ordered)) - 1]
        thresholds.append(threshold)
        residuals = tuple(_combine(residual, book[index], -1)
                          if not gated or distance <= threshold else residual
                          for residual, (index, distance) in zip(residuals, choices))
        for residual in residuals:
            _squared(residual)
    return tuple(thresholds)
