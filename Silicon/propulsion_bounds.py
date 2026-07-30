"""
FP-1..5: momentum bounds and discriminating power for the field-propulsion claim.

The claim under test: a helical array of phase-coupled oscillators, driven with
a traveling-wave phase gradient, produces "a net momentum flux (thrust)
through the surrounding medium ... without expelling reaction mass".

That sentence contains its own refutation, and this module makes it
arithmetic rather than argument. A momentum flux *through a medium* IS
expelled reaction momentum -- carried by the medium, or by the field. The
question is never "is there reaction mass" but "how much thrust per watt
does the carrier allow", and that has a hard answer.

THE BOUND (FP-1)
----------------
A wave of speed ``v`` carrying power ``P`` carries momentum flux ``P/v``.
So::

    F <= P / v          EM:       3.34e-9  N/W    (v = c)
                        air:      2.92e-3  N/W    (v = 343 m/s)
                        water:    6.75e-4  N/W    (v = 1481 m/s)

The consequence for the registered prediction ``F > 0.1 mN`` is decisive and
runs the opposite way from intuition:

* via EM, 0.1 mN needs **30 kW**. A tabletop array delivers ~1 W, so a
  positive result is six orders too large to be electromagnetic.
* via acoustics, 0.1 mN needs **34 mW**. Trivially achievable.

**A positive result at the registered threshold therefore identifies the
mechanism as acoustic, which is to say: a fan.** The measurement that was
meant to confirm an exotic effect confirms an ordinary one.

WHY 3*pi/2 IS NOT MYSTERIOUS (FP-2)
-----------------------------------
A closed array of ``N`` nodes supports traveling waves only at
``dphi = 2*pi*m/N``. For ``N = 8``, ``3*pi/2 = 2*pi*6/8`` -- it is exactly
the ``m = 6`` mode, and by aliasing ``m = 6`` is the same physical mode as
``m = -2``: a backward wave of two turns.

So ``dphi = 3*pi/2`` and ``dphi = -pi/2`` are **the same excitation**. Any
claim that the first is special and the second is not is refuted by
arithmetic, with no experiment. :func:`aliased_modes` lists the equivalences.

ALL FOUR REGISTERED PREDICTIONS ARE H0 PREDICTIONS (FP-3)
---------------------------------------------------------
This is the methodological finding, and it survives however much Bayesian
machinery is wrapped around the experiment:

===============================  =========================================
prediction                       also predicted by ordinary radiation?
===============================  =========================================
F > 0.1 mN at 3*pi/2             YES -- needs only 34 mW of acoustic power
sign reverses with dphi -> -dphi YES -- reversing the gradient reverses the
                                 wave direction, so streaming reverses
F scales as N^2                  YES -- N coherent sources give amplitude
                                 ~N, power ~N^2, and F = P/v, so F ~ N^2
                                 *exactly*
helix beats ring                 YES -- a ring has no axial phase gradient
                                 and therefore no axial streaming
===============================  =========================================

A pre-registered prediction that both hypotheses make is not a test. The
protocol as written cannot return "no", which is the one thing a protocol
has to be able to do.

WHAT WOULD DISCRIMINATE (FP-4)
------------------------------
One ratio, two instruments, no phase sweep::

    measure F (force balance) and P (total radiated acoustic power)
    simultaneously, then compare F to P/v.

    H0:  F <= P/v
    H1:  F  > P/v      thrust exceeding the momentum carried by the
                       radiation that produced it

:func:`exceeds_momentum_bound` is that test. It is the only measurement in
the plan that can come back negative, and it needs no pre-registered phase
angle at all.

Stdlib only.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

__all__ = [
    "C_LIGHT", "C_AIR", "C_WATER", "CARRIERS",
    "thrust_bound", "power_for_thrust", "exceeds_momentum_bound",
    "traveling_wave_gradients", "aliased_modes", "is_traveling_wave_mode",
    "coherent_power_scaling", "discriminates",
]

C_LIGHT = 2.99792458e8
C_AIR = 343.0
C_WATER = 1481.0

#: Wave speed by carrier, m/s.
CARRIERS: Dict[str, float] = {
    "em": C_LIGHT,
    "acoustic_air": C_AIR,
    "acoustic_water": C_WATER,
}


def thrust_bound(power_w: float, carrier: str = "acoustic_air") -> float:
    """Maximum thrust in newtons for ``power_w`` radiated into ``carrier``.

    ``F <= P / v``. This is momentum conservation, not an engineering
    estimate: a wave of speed ``v`` carrying power ``P`` carries momentum
    flux ``P/v``, and a radiator cannot recoil harder than the momentum it
    emits.
    """
    if power_w < 0.0:
        raise ValueError("power must be non-negative")
    if carrier not in CARRIERS:
        raise ValueError(f"unknown carrier {carrier!r}; choose from {sorted(CARRIERS)}")
    return power_w / CARRIERS[carrier]


def power_for_thrust(thrust_n: float, carrier: str = "acoustic_air") -> float:
    """Minimum radiated power, in watts, to reach ``thrust_n``.

    The inverse of :func:`thrust_bound`, and the number that settles whether
    a claimed thrust is plausible for a given carrier at a given power
    budget.
    """
    if thrust_n < 0.0:
        raise ValueError("thrust must be non-negative")
    if carrier not in CARRIERS:
        raise ValueError(f"unknown carrier {carrier!r}; choose from {sorted(CARRIERS)}")
    return thrust_n * CARRIERS[carrier]


def exceeds_momentum_bound(thrust_n: float, power_w: float,
                           carrier: str = "acoustic_air",
                           margin: float = 1.0) -> Dict[str, object]:
    """THE discriminating test (FP-4). Does measured thrust beat ``P/v``?

    Parameters
    ----------
    thrust_n : float
        Measured axial force, newtons, from a calibrated balance.
    power_w : float
        Total radiated power into the carrier, watts, measured over a closed
        surface -- not the electrical input power, which includes ohmic loss
        that produces no momentum.
    carrier : str
        Which wave carries the momentum.
    margin : float
        Required factor above the bound to claim an anomaly. 1.0 is the bare
        bound; use >1 to absorb calibration uncertainty.

    Returns
    -------
    dict
        ``bound_n``, ``ratio`` (measured / bound), ``anomalous`` (bool), and
        ``verdict``.

    A ``ratio`` at or below 1 is consistent with ordinary radiation however
    large the thrust is in absolute terms. That is the whole point: absolute
    thrust is not evidence, thrust *per watt radiated* is.
    """
    if margin <= 0.0:
        raise ValueError("margin must be positive")
    bound = thrust_bound(power_w, carrier)
    if bound == 0.0:
        return {"bound_n": 0.0, "ratio": float("inf") if thrust_n > 0 else 0.0,
                "anomalous": thrust_n > 0.0,
                "verdict": "no radiated power: any thrust is unexplained, "
                           "but check for mechanical or thermal coupling first"}
    ratio = thrust_n / bound
    anomalous = ratio > margin
    return {
        "bound_n": bound,
        "ratio": ratio,
        "anomalous": anomalous,
        "verdict": ("EXCEEDS the momentum bound -- this is the only result that "
                    "supports H1" if anomalous else
                    "within the momentum bound -- consistent with ordinary "
                    "radiation at any absolute thrust"),
    }


# ---------------------------------------------------------------------------
# Traveling-wave modes on a closed array of N nodes
# ---------------------------------------------------------------------------

def traveling_wave_gradients(n_nodes: int) -> List[Tuple[int, float]]:
    """Allowed ``(m, dphi)`` traveling-wave modes for ``n_nodes``.

    A closed array supports only ``dphi = 2*pi*m/N``. Returns one entry per
    distinct ``dphi`` in ``[0, 2*pi)``, with ``m`` reduced to the range
    ``(-N/2, N/2]`` so the direction of travel is readable from its sign.
    """
    if n_nodes < 2:
        raise ValueError("need at least 2 nodes")
    out = []
    for k in range(n_nodes):
        m = k if k <= n_nodes // 2 else k - n_nodes
        out.append((m, 2.0 * math.pi * k / n_nodes))
    return out


def is_traveling_wave_mode(dphi: float, n_nodes: int,
                           tol: float = 1e-9) -> bool:
    """Whether ``dphi`` is an allowed traveling-wave gradient for ``n_nodes``."""
    target = dphi % (2.0 * math.pi)
    return any(abs(target - d) < tol or abs(target - d - 2 * math.pi) < tol
               for _, d in traveling_wave_gradients(n_nodes))


def aliased_modes(dphi: float, n_nodes: int) -> Dict[str, object]:
    """Which other phase gradients are the SAME excitation as ``dphi``.

    Aliasing on a discrete array means many nominally different gradients
    drive one physical mode. Two gradients differing by ``2*pi`` per node are
    indistinguishable, and ``m`` and ``m - N`` are the same wave.

    Returns the reduced mode index, the equivalent gradient in
    ``(-pi, pi]``, and whether ``dphi`` is an allowed mode at all. Any claim
    that one member of an alias class is special is refuted by this function
    alone.
    """
    if n_nodes < 2:
        raise ValueError("need at least 2 nodes")
    reduced = dphi % (2.0 * math.pi)
    if not is_traveling_wave_mode(dphi, n_nodes):
        return {"allowed": False, "m": None, "equivalent_dphi": None,
                "note": f"{dphi:.6f} is not 2*pi*m/{n_nodes} for integer m: "
                        "not a traveling-wave mode on this array"}
    m_raw = round(reduced * n_nodes / (2.0 * math.pi))
    m = m_raw if m_raw <= n_nodes // 2 else m_raw - n_nodes
    signed = 2.0 * math.pi * m / n_nodes
    return {
        "allowed": True,
        "m": m,
        "m_as_given": m_raw,
        "equivalent_dphi": signed,
        "turns": m,
        "note": (f"dphi={reduced:.6f} is mode m={m_raw}, which aliases to "
                 f"m={m} (dphi={signed:+.6f}). These are the SAME excitation."),
    }


def coherent_power_scaling(n_nodes: int) -> float:
    """Radiated power of ``n_nodes`` coherent sources, relative to one.

    Amplitudes add for coherent sources, so amplitude ~ N and power ~ N².
    Combined with ``F = P/v`` this makes ``F ~ N²`` a **prediction of
    ordinary radiation**, which is why the N² test discriminates nothing.
    """
    if n_nodes < 1:
        raise ValueError("need at least 1 node")
    return float(n_nodes ** 2)


def discriminates(predicted_by_h0: bool, predicted_by_h1: bool) -> Dict[str, object]:
    """Whether a prediction can separate two hypotheses.

    Trivial by construction, and included because the field-propulsion
    protocol pre-registered four predictions without running this check on
    any of them, and all four came back ``False``.
    """
    ok = predicted_by_h0 != predicted_by_h1
    return {
        "discriminates": ok,
        "verdict": ("separates the hypotheses" if ok else
                    "BOTH hypotheses predict this -- it is not a test, however "
                    "precisely it is pre-registered"),
    }


if __name__ == "__main__":
    print("FP-1: the momentum bound, F <= P/v\n")
    print(f"  {'carrier':16s} {'thrust per watt':>16s} {'power for 0.1 mN':>20s}")
    for name in ("em", "acoustic_air", "acoustic_water"):
        per_w = thrust_bound(1.0, name)
        need = power_for_thrust(1e-4, name)
        print(f"  {name:16s} {per_w:12.4e} N/W {need:16.4e} W")
    print("\n  The registered prediction is F > 0.1 mN.")
    print(f"    via EM        : needs {power_for_thrust(1e-4, 'em') / 1e3:,.0f} kW")
    print(f"    via air       : needs {power_for_thrust(1e-4, 'acoustic_air') * 1e3:.1f} mW")
    print("  A positive result at that threshold is 6 orders too large to be")
    print("  electromagnetic and trivial for acoustics. It identifies a fan.\n")

    print("FP-2: is 3*pi/2 special?\n")
    for n in (6, 8, 12):
        info = aliased_modes(3 * math.pi / 2, n)
        print(f"  N={n:<3} {info['note']}")
    print("\n  For N=8, dphi=3*pi/2 and dphi=-pi/2 are the same excitation.")
    print("  A claim that one is special and the other is not needs no")
    print("  experiment to refute.\n")

    print("FP-3: discriminating power of the registered predictions\n")
    preds = [
        ("F > 0.1 mN at 3*pi/2", True, True),
        ("sign reverses when dphi -> -dphi", True, True),
        ("F scales as N^2", True, True),
        ("helix beats ring", True, True),
    ]
    for name, h0, h1 in preds:
        d = discriminates(h0, h1)
        print(f"  {name:34s} -> {d['verdict']}")
    print(f"\n  N^2 is not a coincidence: {coherent_power_scaling(8):.0f}x the power "
          f"for 8 coherent sources,")
    print("  and F = P/v, so ordinary radiation gives F ~ N^2 exactly.\n")

    print("FP-4: the one test that can return 'no'\n")
    for label, F, P in (("plausible fan", 1.0e-4, 0.05),
                        ("exactly at bound", 1.0e-4, power_for_thrust(1e-4)),
                        ("genuine anomaly", 1.0e-2, 0.05)):
        r = exceeds_momentum_bound(F, P)
        print(f"  {label:18s} F={F:.1e} N  P={P:.3f} W  "
              f"ratio={r['ratio']:6.3f}  anomalous={r['anomalous']}")
    print("\n  Absolute thrust is not evidence. Thrust per watt radiated is.")
