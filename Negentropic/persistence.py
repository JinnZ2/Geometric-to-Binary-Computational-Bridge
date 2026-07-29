"""
NEG-8 -- the persistence criterion, and the relaxation assumption it rests on.

    A structure persists iff it exports entropy at least as fast as it
    produces it.

        Phi  =  -S_exchange_dot  -  sigma          [W/K]
        persist  <=>  Phi >= 0

There is no threshold to tune and no normalisation to choose.  ``Phi`` is
the rate of internal entropy decrease: from ``dS/dt = S_exchange_dot +
sigma`` with ``sigma >= 0`` by the second law, the structure holds when
``dS/dt <= 0``, which is exactly ``Phi >= 0``.  Both terms are in W/K and
they subtract, which is more than can be said for ``M = R*A*D - L`` (see
``corrections.md``: ``D`` is a variance and ``L`` is a power, so ``M >= 10``
was never a statement about anything).

FALSIFIER: a system with ``Phi < 0`` sustained over ``tau`` that does not
lose structure.  :func:`sustained_deficit` finds those windows in a trace
so the claim can be checked rather than asserted.

Relaxation is not assumed monotone
----------------------------------
Anomalous relaxation is real.  The Mpemba effect and its inverse have been
observed in colloidal systems (Kumar & Bechhoefer 2020), and strong system-
bath coupling admits shortcuts where a system further from equilibrium
reaches it first.  Any decay term written as a single monotone exponential
is making an assumption that measurement can and does violate.

So this module ships :func:`relaxation_report` rather than a decay
constant.  Code that fits a relaxation time should call it first and say
out loud that the trajectory is monotone, instead of discovering later
that it fitted an exponential to a crossing.

Stdlib only.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

KB = 1.380649e-23  # Boltzmann constant, J/K

__all__ = [
    "KB",
    "persistence_margin",
    "persists",
    "sigma_to_watts_per_kelvin",
    "required_export_rate",
    "sustained_deficit",
    "relaxation_report",
]


def persistence_margin(s_exchange_rate: float, sigma: float) -> float:
    """``Phi = -S_exchange_dot - sigma``, in W/K.

    Parameters
    ----------
    s_exchange_rate : float
        Entropy exchange rate with the environment, W/K.  Negative when the
        structure is exporting entropy -- that is the sign convention that
        makes ``Phi`` positive for a system that is holding together.
    sigma : float
        Internal entropy production rate, W/K.  Must be non-negative; a
        negative value is a second-law violation and is rejected rather
        than quietly clamped.
    """
    if sigma < 0.0:
        raise ValueError("sigma must be non-negative (second law)")
    return -s_exchange_rate - sigma


def persists(s_exchange_rate: float, sigma: float) -> bool:
    """Whether the structure holds at this instant: ``Phi >= 0``."""
    return persistence_margin(s_exchange_rate, sigma) >= 0.0


def sigma_to_watts_per_kelvin(sigma_nats_per_second: float) -> float:
    """Convert an entropy production rate from nats/s to W/K.

    ``DissipativeCore.step`` reports ``sigma`` in nats per unit time, which
    is the natural output of a dimensionless phase model.  Multiplying by
    ``k_B`` is what turns it into a physical rate that can be compared with
    an exchange term.  Without this step the two sides of ``Phi`` are not
    in the same units and the comparison is meaningless.
    """
    if sigma_nats_per_second < 0.0:
        raise ValueError("entropy production rate must be non-negative")
    return KB * sigma_nats_per_second


def required_export_rate(sigma: float) -> float:
    """Minimum entropy export rate, W/K, for the structure to hold.

    Returns the magnitude: the structure needs ``S_exchange_dot <= -sigma``.
    """
    if sigma < 0.0:
        raise ValueError("sigma must be non-negative")
    return sigma


def sustained_deficit(margins: Sequence[float], dt: float,
                      tau: float) -> List[Tuple[int, int, float]]:
    """Find windows where ``Phi < 0`` is sustained for at least ``tau``.

    Parameters
    ----------
    margins : sequence of float
        ``Phi`` sampled at uniform intervals, W/K.
    dt : float
        Sample spacing, s.
    tau : float
        Minimum duration, s, that a deficit must persist to count.

    Returns
    -------
    list of (start_index, end_index, duration)
        Half-open index ranges, with duration in seconds.  A non-empty
        result on a system that did *not* lose structure over that window
        falsifies NEG-8.  An empty result is not confirmation -- it only
        means this trace has nothing to say.
    """
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    if tau < 0.0:
        raise ValueError("tau must be non-negative")

    windows: List[Tuple[int, int, float]] = []
    start: Optional[int] = None
    for i, phi in enumerate(margins):
        if phi < 0.0:
            if start is None:
                start = i
        elif start is not None:
            duration = (i - start) * dt
            if duration >= tau:
                windows.append((start, i, duration))
            start = None
    if start is not None:
        duration = (len(margins) - start) * dt
        if duration >= tau:
            windows.append((start, len(margins), duration))
    return windows


def relaxation_report(series: Sequence[float],
                      tolerance: float = 0.0) -> Dict[str, object]:
    """Check whether a decaying series is actually monotone.

    Parameters
    ----------
    series : sequence of float
        The quantity claimed to be relaxing, in time order.
    tolerance : float
        Increases smaller than this are treated as noise rather than
        reversals.  Set it from the measurement noise floor, not from what
        makes the answer come out monotone.

    Returns
    -------
    dict
        ``monotone`` (bool), ``reversals`` (list of indices where the series
        increased by more than ``tolerance``), ``largest_reversal`` (float),
        and ``fit_exponential_ok`` -- ``False`` when reversals are present,
        meaning a single-exponential relaxation time should not be reported
        for this trajectory.

    A non-monotone relaxation is not a broken measurement.  Mpemba-type
    crossings and strong-coupling shortcuts are physical, and the right
    response is to report the crossing, not to smooth it away.
    """
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")

    vals = [float(v) for v in series]
    reversals: List[int] = []
    largest = 0.0
    for i in range(1, len(vals)):
        rise = vals[i] - vals[i - 1]
        if rise > tolerance:
            reversals.append(i)
            largest = max(largest, rise)

    return {
        "monotone": not reversals,
        "reversals": reversals,
        "largest_reversal": largest,
        "fit_exponential_ok": not reversals,
        "n": len(vals),
    }


if __name__ == "__main__":
    print("NEG-8: persistence margin")
    for s_ex, sig in ((-3.0e-3, 1.0e-3), (-1.0e-3, 1.0e-3), (-0.5e-3, 1.0e-3)):
        phi = persistence_margin(s_ex, sig)
        print(f"  S_exchange_dot={s_ex:+.1e} W/K  sigma={sig:.1e} W/K"
              f"  ->  Phi={phi:+.1e} W/K  persists={persists(s_ex, sig)}")

    margins = [1.0, 0.5, -0.2, -0.3, -0.1, 0.4, -0.9]
    print(f"\n  sustained deficits (dt=1s, tau=2s): "
          f"{sustained_deficit(margins, dt=1.0, tau=2.0)}")

    print("\nRelaxation monotonicity guard")
    clean = [1.0, 0.6, 0.36, 0.22, 0.13]
    mpemba = [1.0, 0.6, 0.7, 0.2, 0.05]
    for name, series in (("plain exponential", clean), ("crossing", mpemba)):
        rep = relaxation_report(series, tolerance=1e-6)
        print(f"  {name:18s} monotone={rep['monotone']}  "
              f"fit_exponential_ok={rep['fit_exponential_ok']}  "
              f"reversals={rep['reversals']}")

    from_core = sigma_to_watts_per_kelvin(252.62)
    print(f"\n  DissipativeCore sigma 252.62 nats/s = {from_core:.3e} W/K")
