"""
Stochastic-thermodynamic floors: TUR and KUR.

Every hand-set efficiency constant in this framework -- the ``0.2 *
kinetic`` friction weight, the ``lambda_param`` inefficiency scaling, the
``L = 0.1`` in ``GeometricNetwork.step`` -- was a free parameter chosen to
make a plot look right.  Stochastic thermodynamics supplies actual floors
for the same quantity, so the free parameters can be deleted rather than
retuned.

The thermodynamic uncertainty relation (Barato & Seifert 2015; Gingrich,
Horowitz, Perunov & England 2016) says that a steady-state current cannot
be made precise for free::

    Var(J) / <J>^2  >=  2 k_B / Sigma

where ``Sigma`` is the *total* entropy production over the same observation
window that ``J`` was accumulated in.  Rearranged, it is a hard lower bound
on dissipation per unit precision::

    Sigma  >=  2 k_B <J>^2 / Var(J)

The kinetic uncertainty relation (Di Terlizzi & Baiesi 2019) bounds the
same precision by dynamical activity instead of dissipation, and is the
tighter of the two in the far-from-equilibrium, low-dissipation corner::

    Var(J) / <J>^2  >=  1 / A

with ``A`` the mean number of transitions in the window.  A system that
claims high precision has to pay in one currency or the other; the
combined bound is whichever is larger.

Both relations are stated for time-homogeneous Markov dynamics in a
non-equilibrium steady state.  Outside that regime -- transients,
time-dependent driving, non-Markovian memory -- the standard TUR can be
violated, and the generalised forms carry extra terms.  ``tur_valid_regime``
is a reminder, not a proof; it does not inspect the dynamics.

Stdlib only.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

KB = 1.380649e-23  # Boltzmann constant, J/K

__all__ = [
    "KB",
    "precision",
    "tur_entropy_floor",
    "tur_precision_ceiling",
    "tur_dissipated_energy_floor",
    "kur_activity_floor",
    "combined_precision_ceiling",
    "tur_valid_regime",
]


def precision(mean_current: float, var_current: float) -> float:
    """Signal-to-noise ratio ``<J> / std(J)`` of an accumulated current.

    This is the quantity both uncertainty relations bound.  It is
    dimensionless whatever the units of ``J``, which is the reason the
    bounds can be stated without knowing what ``J`` counts.
    """
    if var_current <= 0.0:
        raise ValueError("var_current must be positive")
    return abs(mean_current) / math.sqrt(var_current)


def tur_entropy_floor(mean_current: float, var_current: float) -> float:
    """Minimum total entropy production, in J/K, for the observed precision.

    ``Sigma >= 2 k_B <J>^2 / Var(J)``.

    Returns the floor over the *same* window the current statistics were
    measured in.  Divide by the window length for a rate.
    """
    return 2.0 * KB * precision(mean_current, var_current) ** 2


def tur_precision_ceiling(sigma_total: float) -> float:
    """Maximum achievable precision given an entropy production budget.

    Inverse of :func:`tur_entropy_floor`: ``<J>/std(J) <= sqrt(Sigma / 2 k_B)``.

    Parameters
    ----------
    sigma_total : float
        Total entropy production over the window, J/K.
    """
    if sigma_total < 0.0:
        raise ValueError("sigma_total must be non-negative")
    return math.sqrt(sigma_total / (2.0 * KB))


def tur_dissipated_energy_floor(mean_current: float, var_current: float,
                                temperature: float) -> float:
    """Minimum dissipated energy, in joules, for the observed precision.

    ``W_diss >= T * Sigma_min``.  This is the number that replaces a
    hand-set efficiency constant: given a target precision and a bath
    temperature, the dissipation is not a tunable, it is bounded below.
    """
    if temperature <= 0.0:
        raise ValueError("temperature must be positive")
    return temperature * tur_entropy_floor(mean_current, var_current)


def kur_activity_floor(mean_current: float, var_current: float) -> float:
    """Minimum dynamical activity ``A`` for the observed precision.

    ``A >= <J>^2 / Var(J)``, dimensionless (a count of transitions).
    Where TUR charges for dissipation, KUR charges for how much the system
    has to move; a low-dissipation system that is nonetheless precise pays
    here instead.
    """
    return precision(mean_current, var_current) ** 2


def combined_precision_ceiling(sigma_total: float, activity: float) -> Dict[str, float]:
    """Tightest precision ceiling from TUR and KUR together.

    Returns both individual ceilings and which relation binds.  The system
    cannot beat the smaller of the two.
    """
    if activity < 0.0:
        raise ValueError("activity must be non-negative")
    tur = tur_precision_ceiling(sigma_total)
    kur = math.sqrt(activity)
    return {
        "tur_ceiling": tur,
        "kur_ceiling": kur,
        "ceiling": min(tur, kur),
        "binding": "TUR" if tur <= kur else "KUR",
    }


def tur_valid_regime(steady_state: bool, time_homogeneous: bool,
                     markovian: bool) -> Optional[str]:
    """Return why the standard TUR does not apply, or ``None`` if it does.

    The caller asserts the three conditions; this function does not verify
    them.  It exists so that code invoking the bound has to state which
    regime it believes it is in, rather than applying the bound silently to
    a transient or a driven system where it can be violated.
    """
    if not steady_state:
        return ("not a steady state: the standard TUR is a NESS result; "
                "transients require the finite-time / generalised form")
    if not time_homogeneous:
        return ("time-dependent driving: periodically driven systems obey a "
                "modified TUR with an extra term, and can violate the standard one")
    if not markovian:
        return ("non-Markovian dynamics: memory kernels break the derivation")
    return None


if __name__ == "__main__":
    mean_j, var_j, T = 100.0, 4.0, 300.0
    print(f"current: <J> = {mean_j}, Var(J) = {var_j}, T = {T} K")
    print(f"  precision            {precision(mean_j, var_j):.2f}")
    print(f"  TUR entropy floor    {tur_entropy_floor(mean_j, var_j):.4e} J/K")
    print(f"  TUR energy floor     {tur_dissipated_energy_floor(mean_j, var_j, T):.4e} J")
    print(f"  KUR activity floor   {kur_activity_floor(mean_j, var_j):.1f} transitions")
    combined = combined_precision_ceiling(sigma_total=1e-19, activity=1e4)
    print(f"  combined ceiling     {combined['ceiling']:.2f} (bound by {combined['binding']})")
    print(f"  regime check         {tur_valid_regime(True, False, True)}")
