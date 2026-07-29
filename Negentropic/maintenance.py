"""
NEG-2 -- an archive is a dissipative structure, not an object.

A stored record is not a thing that sits still and slowly wears out.  It is
a structure held against its own entropy production by a maintenance flux,
and it lasts exactly as long as that flux keeps up.  Steady state requires::

    W_care  =  T * sigma_decay

Below that the structure is running down; at or above it, it persists
indefinitely, at a cost that never goes to zero.  This is the same
criterion as NEG-8 (``persistence.py``) applied to one specific kind of
structure, with the maintenance term written explicitly.

PREDICTION: two archives built from identical materials but given unequal
care flux diverge in lifetime, with the ratio set by ``sigma - W/T`` rather
than by anything about the material.

FALSIFIER: equal lifetimes under unequal care flux.  That would mean
lifetime is a property of the substrate and the maintenance term is
decoration.

Scheduling
----------
The framework used to assert a Fibonacci session schedule.  There is no
derivation anywhere for why the spacing should be Fibonacci specifically,
and the empirical claim that was supposed to support it does not survive
audit (``02-empirical-audit.md``, Claim 1).  What survives is the weaker
and testable statement that revisit intervals should *expand* geometrically.
:func:`expanding_schedule` takes the ratio as a parameter and
:func:`fit_ratio` estimates it from data with an interval, so the golden
ratio becomes one hypothesis among others rather than a premise.  A fit
whose confidence interval excludes 1.618 is a result, not a failure.

Stdlib only.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

PHI = (1.0 + math.sqrt(5.0)) / 2.0  # 1.6180339887..., Fibonacci's asymptotic ratio

__all__ = [
    "PHI",
    "archive_lifetime",
    "steady_state_care",
    "lifetime_ratio",
    "expanding_schedule",
    "fit_ratio",
]


def archive_lifetime(ds_budget: float, sigma_decay: float,
                     w_care: float, temperature: float) -> Optional[float]:
    """Seconds until the structure stops being readable, or ``None``.

    Parameters
    ----------
    ds_budget : float
        Entropy the structure can absorb before it is no longer readable,
        J/K.  This is a property of the encoding's error tolerance, not of
        the medium alone.
    sigma_decay : float
        Intrinsic entropy production rate, W/K.
    w_care : float
        Maintenance work flux, W.
    temperature : float
        Ambient temperature, K.

    Returns
    -------
    float or None
        Lifetime in seconds, or ``None`` when ``W_care / T >= sigma_decay``
        -- the maintenance flux matches or exceeds the decay, and the
        structure persists indefinitely at that ongoing cost.
    """
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    if ds_budget < 0.0:
        raise ValueError("ds_budget must be non-negative")
    net = sigma_decay - w_care / temperature
    if net <= 0.0:
        return None
    return ds_budget / net


def steady_state_care(sigma_decay: float, temperature: float) -> float:
    """Maintenance flux, in watts, that exactly holds the structure steady.

    ``W_care = T * sigma_decay``.  Anything less has a finite lifetime;
    there is no free storage.
    """
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    return temperature * sigma_decay


def lifetime_ratio(ds_budget: float, sigma_decay: float,
                   w_care_a: float, w_care_b: float,
                   temperature: float) -> Optional[float]:
    """Predicted lifetime ratio of two identical archives under unequal care.

    Returns ``lifetime(a) / lifetime(b)``, or ``None`` if either archive is
    at or above steady state (infinite lifetime, ratio undefined).  This is
    the quantity the NEG-2 falsifier measures: the prediction is that it
    depends only on ``sigma - W/T``, so a measured ratio of 1 under unequal
    ``W_care`` falsifies the claim.
    """
    la = archive_lifetime(ds_budget, sigma_decay, w_care_a, temperature)
    lb = archive_lifetime(ds_budget, sigma_decay, w_care_b, temperature)
    if la is None or lb is None or lb == 0.0:
        return None
    return la / lb


def expanding_schedule(start: float, n: int,
                       ratio: float = PHI) -> Tuple[List[float], List[float]]:
    """Geometrically expanding revisit schedule.

    Parameters
    ----------
    start : float
        First interval, in whatever time unit the caller is working in.
    n : int
        Number of revisits, including the one at offset zero.
    ratio : float
        Interval growth factor.  ``PHI`` recovers Fibonacci spacing
        asymptotically, but it is a *fitted* parameter with a confidence
        interval (:func:`fit_ratio`), not an assertion.  ``ratio = 1``
        gives uniform spacing, which is the null hypothesis.

    Returns
    -------
    (offsets, intervals)
        ``offsets`` are cumulative, starting at 0.0 and of length ``n``.
        ``intervals`` has length ``n - 1``.
    """
    if n < 1:
        raise ValueError("n must be at least 1")
    if start <= 0.0:
        raise ValueError("start must be positive")
    if ratio <= 0.0:
        raise ValueError("ratio must be positive")

    intervals = [start * ratio ** k for k in range(max(0, n - 1))]
    offsets = [0.0]
    cumulative = 0.0
    for gap in intervals:
        cumulative += gap
        offsets.append(cumulative)
    return offsets, intervals


def fit_ratio(intervals: Sequence[float], z: float = 1.96) -> Dict[str, float]:
    """Estimate the expansion ratio from observed intervals, with an interval.

    Fits the geometric mean of successive interval ratios and returns a
    confidence interval from the spread of the log-ratios.

    Parameters
    ----------
    intervals : sequence of float
        Observed gaps between revisits, in order.  Needs at least three, so
        that there are at least two ratios and a spread to estimate.
    z : float
        Normal-approximation multiplier; 1.96 is nominally 95%.  With few
        ratios this understates the width -- a t multiplier would be
        correct, and the stdlib has no t quantile, so the caller can pass
        one in.  Do not report the default as exact for small samples.

    Returns
    -------
    dict
        ``ratio``, ``ci_low``, ``ci_high``, ``n_ratios``, and
        ``excludes_phi`` -- whether the golden ratio falls outside the
        interval, which is the comparison the old Fibonacci claim needs to
        survive.
    """
    vals = [float(v) for v in intervals]
    if len(vals) < 3:
        raise ValueError("need at least 3 intervals to estimate a ratio and its spread")
    if any(v <= 0.0 for v in vals):
        raise ValueError("intervals must be positive")

    logs = [math.log(vals[i + 1] / vals[i]) for i in range(len(vals) - 1)]
    m = len(logs)
    mean_log = sum(logs) / m
    if m > 1:
        var_log = sum((x - mean_log) ** 2 for x in logs) / (m - 1)
        se = math.sqrt(var_log / m)
    else:
        se = 0.0

    ratio = math.exp(mean_log)
    low = math.exp(mean_log - z * se)
    high = math.exp(mean_log + z * se)

    return {
        "ratio": ratio,
        "ci_low": low,
        "ci_high": high,
        "n_ratios": float(m),
        "excludes_phi": float(not (low <= PHI <= high)),
    }


if __name__ == "__main__":
    T = 293.0
    sigma = 1e-9  # W/K
    budget = 1e-3  # J/K

    print("NEG-2: archive lifetime under unequal care")
    for care in (0.0, 1e-7, steady_state_care(sigma, T)):
        life = archive_lifetime(budget, sigma, care, T)
        shown = "indefinite" if life is None else f"{life:.3e} s ({life / 3.156e7:.1f} yr)"
        print(f"  W_care = {care:.3e} W  ->  {shown}")
    print(f"  steady-state care flux: {steady_state_care(sigma, T):.3e} W")
    ratio = lifetime_ratio(budget, sigma, 0.0, 1e-7, T)
    print(f"  predicted lifetime ratio (no care vs 1e-7 W): {ratio:.3f}")

    print("\nExpanding schedule, ratio as a fitted parameter")
    offsets, intervals = expanding_schedule(start=1.0, n=8, ratio=PHI)
    print(f"  offsets:   {[round(o, 2) for o in offsets]}")
    fit = fit_ratio(intervals)
    print(f"  refit:     ratio = {fit['ratio']:.4f} "
          f"[{fit['ci_low']:.4f}, {fit['ci_high']:.4f}]")
    uniform = fit_ratio([3.0, 3.1, 2.9, 3.05, 3.0])
    print(f"  uniform data: ratio = {uniform['ratio']:.4f} "
          f"[{uniform['ci_low']:.4f}, {uniform['ci_high']:.4f}], "
          f"excludes phi = {bool(uniform['excludes_phi'])}")
