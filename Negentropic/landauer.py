"""
NEG-3 -- finite-time erasure, and the resurfacing prediction that follows.

Landauer's bound ``k_B T ln 2`` per erased bit is a quasi-static limit: it
is the cost of taking infinitely long.  Erasure in finite time ``tau``
costs strictly more, and the excess has a known scaling::

    W(tau)  =  k_B T ln 2  +  C / tau

The ``C/tau`` term is the finite-time (optimal-protocol) excess.  ``C`` is
protocol-dependent and set by the Wasserstein-2 distance between the
initial and final distributions divided by the mobility -- Aurell et al.
(2012) derived the optimal-transport form, Proesmans, Ehrich & Bechhoefer
(2020) measured it and confirmed the ``1/tau`` scaling experimentally.

This is what makes the negentropy budget in this framework *measurable*
rather than asserted.  Sub-``kT`` erasure regimes and feedback-engine work
extraction are laboratory quantities now, not thought experiments, so a
claim of the form "maintaining this structure costs X" has a number to be
checked against instead of a hand-set constant.

The prediction this repository actually cares about
---------------------------------------------------
Memory reconsolidation (see ``02-empirical-audit.md``, Claim 5) is an
erasure-and-rewrite operation on a physical substrate.  If the rate at
which an old trace resurfaces is proportional to the residual dissipation
of the rewrite, then::

    resurfacing(tau)  ~  1 / tau

and an abrupt purge -- small ``tau`` -- costs quadratically more *per unit
time* than a gradual one, because excess power goes as ``tau^-2``.

FALSIFIER: measure resurfacing rate against cue-swap duration.  If it is
flat in ``tau``, or scales with any exponent materially different from
-1, the dissipation account of reconsolidation is wrong.  Use
:func:`fit_excess_exponent` on the measured pairs; the decision rule is in
its docstring.

Stdlib only.
"""

from __future__ import annotations

import math
from typing import Dict, Sequence

KB = 1.380649e-23  # Boltzmann constant, J/K
LN2 = math.log(2.0)

__all__ = [
    "KB",
    "LN2",
    "landauer_floor",
    "erase_cost",
    "excess",
    "excess_power",
    "protocol_constant",
    "resurfacing_rate",
    "fit_excess_exponent",
]


def landauer_floor(temperature: float) -> float:
    """Quasi-static cost of erasing one bit, in joules: ``k_B T ln 2``."""
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    return KB * temperature * LN2


def erase_cost(temperature: float, tau: float, c: float) -> float:
    """Minimum work to erase one bit in finite time ``tau``, in joules.

    ``W(tau) = k_B T ln 2 + C / tau``.

    Parameters
    ----------
    temperature : float
        Bath temperature, K.
    tau : float
        Protocol duration, s.  Must be positive; the cost diverges as
        ``tau -> 0``, which is the whole point.
    c : float
        Protocol constant, J*s.  See :func:`protocol_constant`.
    """
    if tau <= 0.0:
        raise ValueError("tau must be positive")
    return landauer_floor(temperature) + c / tau


def excess(tau: float, c: float) -> float:
    """Dissipation above the Landauer bound, in joules: ``C / tau``.

    The exponent is -1.  Temperature does not appear here because it is
    already inside ``C`` (see :func:`protocol_constant`); folding it in
    twice is a common way to get the scaling wrong.
    """
    if tau <= 0.0:
        raise ValueError("tau must be positive")
    return c / tau


def excess_power(tau: float, c: float) -> float:
    """Excess dissipation per unit time, in watts: ``C / tau^2``.

    Excess *work* scales as ``tau^-1``; excess *power* as ``tau^-2``.  This
    is the sense in which an abrupt purge costs quadratically more for the
    speed it buys.
    """
    if tau <= 0.0:
        raise ValueError("tau must be positive")
    return c / (tau * tau)


def protocol_constant(w2_distance: float, diffusion: float,
                      temperature: float) -> float:
    """Optimal-transport protocol constant ``C``, in J*s.

    ``C = k_B T * W_2^2 / D``, with ``W_2`` the Wasserstein-2 distance
    between initial and final distributions (in the same length units as
    ``D``) and ``D`` the diffusion coefficient of the memory coordinate.

    Units check: ``[W_2^2 / D] = m^2 / (m^2/s) = s``, so ``C`` is an energy
    times a time and ``C/tau`` is an energy.
    """
    if diffusion <= 0.0:
        raise ValueError("diffusion must be positive")
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    return KB * temperature * (w2_distance ** 2) / diffusion


def resurfacing_rate(tau: float, k: float = 1.0) -> float:
    """Predicted resurfacing rate of an overwritten trace: ``k / tau``.

    Follows from assuming resurfacing is proportional to residual
    dissipation, which scales as ``tau^-1``.  ``k`` folds together the
    protocol constant and the unknown proportionality between residual
    dissipation and observable resurfacing; it is a fitted quantity, and
    the prediction under test is the *exponent*, not ``k``.
    """
    if tau <= 0.0:
        raise ValueError("tau must be positive")
    return k / tau


def fit_excess_exponent(taus: Sequence[float],
                        values: Sequence[float]) -> Dict[str, float]:
    """Least-squares fit of ``value ~ k * tau^p`` in log-log space.

    Returns ``exponent`` (``p``), ``prefactor`` (``k``), ``r_squared``, and
    ``n``.

    DECISION RULE for NEG-3:

    * ``|exponent + 1| < 0.2`` and ``r_squared > 0.9``
      -> consistent with the finite-time dissipation account.
    * ``|exponent| < 0.2``
      -> resurfacing is flat in ``tau``.  NEG-3 is dead; the dissipation
      account of reconsolidation predicts nothing, delete it.
    * anything else
      -> the scaling is real but is not ``tau^-1``.  Report the measured
      exponent; do not describe it as agreeing with Landauer.

    Requires at least three distinct positive ``tau`` values, otherwise the
    exponent is not identified.
    """
    if len(taus) != len(values):
        raise ValueError("taus and values must be the same length")
    pts = [(math.log(t), math.log(v))
           for t, v in zip(taus, values) if t > 0.0 and v > 0.0]
    if len(pts) < 3:
        raise ValueError("need at least 3 positive (tau, value) pairs")
    if len({t for t, _ in pts}) < 2:
        raise ValueError("need at least 2 distinct tau values")

    n = len(pts)
    mx = sum(t for t, _ in pts) / n
    my = sum(v for _, v in pts) / n
    sxy = sum((t - mx) * (v - my) for t, v in pts)
    sxx = sum((t - mx) ** 2 for t, _ in pts)
    syy = sum((v - my) ** 2 for _, v in pts)

    slope = sxy / sxx
    intercept = my - slope * mx
    r_squared = (sxy * sxy) / (sxx * syy) if syy > 0.0 else 1.0

    return {
        "exponent": slope,
        "prefactor": math.exp(intercept),
        "r_squared": r_squared,
        "n": float(n),
    }


if __name__ == "__main__":
    T = 300.0
    c = protocol_constant(w2_distance=1e-7, diffusion=1e-12, temperature=T)
    print(f"Landauer floor at {T} K: {landauer_floor(T):.4e} J")
    print(f"protocol constant C:     {c:.4e} J*s")
    for tau in (1e-3, 1e-2, 1e-1, 1.0):
        print(f"  tau={tau:<7g}  W={erase_cost(T, tau, c):.4e} J"
              f"  excess={excess(tau, c):.4e} J"
              f"  power={excess_power(tau, c):.4e} W")

    taus = [1e-3, 1e-2, 1e-1, 1.0]
    fit = fit_excess_exponent(taus, [excess(t, c) for t in taus])
    print(f"\nrecovered exponent: {fit['exponent']:.4f} "
          f"(r^2 = {fit['r_squared']:.4f}) -- expect -1")
