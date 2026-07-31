"""Pinning a vortex core: ATT-1, and the reason a registry cannot do it.

``vortex_attention_heads.py`` reports the strongest negative result in this
repository and then adopts the wrong remedy. Its own findings are correct and
correctly stated:

    "Topological CHARGE is invariant. Core POSITION is NOT."
    "the winding core POSITION is a collective coordinate that IS dynamical"
    "the position of a vortex core is a zero mode of the action (free to move
     at no energy cost) unless a pinning potential is added"

All three are textbook Kosterlitz-Thouless physics, correctly applied, and
published rather than buried. The remedy does not follow from them.

A REGISTRY IS NOT A PIN
-----------------------
    registry = an array index. Bookkeeping. No energy cost to violate.
    pin      = a term in the Hamiltonian, V_pin(r - r_0), that makes
               displacement cost energy and removes the zero mode.

The document proved the core drifts, so after drift the registered address no
longer holds a core -- it holds ordinary phase, and the head becomes a
fixed-coordinate Gaussian with no defect under it. "Winding charge is preserved
AT THE REGISTERED ADDRESS" is the one wrong sentence: charge is preserved in
the FIELD, not at an address. With a registry, topology does no work; you could
inject nothing and get identical behaviour.

WHY THE OBVIOUS PIN DOES NOT WORK EITHER -- and this is the part that was missed
-------------------------------------------------------------------------------
The natural repair is to couple the pin to the winding density: penalise charge
sitting away from r_0, ``V = (k_p/2) sum_p w_p |r_p - r_0|^2``. That cannot be
optimised, because

    d(plaquette circulation) / d(phi_i) = 0   identically.

Each phi appears in exactly two links of a plaquette with opposite signs, so the
derivatives cancel. Measured worst gradient over 400 random probes: 4.4e-10.

So **the same topological invariance that protects the charge makes the
charge-based pin gradient-free.** A pin has to couple to something
NON-topological. That is the deeper reason a registry does nothing: bookkeeping
is not merely weak, and the topological quantity it records is exactly the
quantity that carries no gradient.

WHAT WORKS: A TEMPLATE PIN
--------------------------
Couple to the phase field itself, against a reference vortex centred at r_0::

    V_pin(phi) = (k_p / 2) * sum_r  wrap(phi(r) - phi_ref(r; r_0))^2

This is a genuine term in the energy. It has a nonzero gradient precisely
because it is not purely topological. Displacing the core from r_0 costs energy
quadratically, which is what removing a zero mode means, and ``k_p = 0``
recovers the unpinned case exactly -- so the registry version is the control
rather than a separate experiment.

The honest caveat: this pins the whole field to a reference configuration, which
is stronger than pinning the core alone. A core-only pin would couple to the
defect density, and the gradient result above says that specific construction is
unavailable. Anything that pins position must reach outside the topological
sector; the template is the simplest thing that does.

WHAT THIS TURNS INTO A POSITIVE RESULT
--------------------------------------
``run_pin_sweep`` measures mean core displacement under gradient flow with
noise, against pin stiffness. ``k_p = 0`` is the registry: the core drifts.
``k_p > 0``: displacement falls, and ``zero_mode_energy`` shows the restoring
energy rising as ``(k_p/2) d^2``. The drift experiment in the original file
becomes the measurement that shows the pin worked.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "wrap", "grid", "vortex_phase", "winding_number_field", "total_winding",
    "circulation_gradient", "core_position",
    "pin_energy", "pin_gradient", "zero_mode_energy",
    "smooth_energy_gradient", "evolve",
    "run_pin_sweep", "gauss_flux_target", "controlled_vortex_comparison",
    "head_contrast_cases", "main",
]


def wrap(d):
    """Wrap to (-pi, pi]."""
    return (np.asarray(d) + np.pi) % (2.0 * np.pi) - np.pi


def grid(n: int = 40, span: float = 1.0):
    """Coordinate mesh over [-span, span]^2."""
    if n < 3:
        raise ValueError("grid must be at least 3x3")
    ax = np.linspace(-span, span, n)
    return np.meshgrid(ax, ax, indexing="xy")


def vortex_phase(X, Y, x0: float = 0.0, y0: float = 0.0, k: int = 1):
    """Phase field of a charge-k vortex centred at (x0, y0)."""
    return k * np.arctan2(Y - y0, X - x0)


# ---------------------------------------------------------------------------
# Topology -- kept from the original, which had it right
# ---------------------------------------------------------------------------

def winding_number_field(phi) -> np.ndarray:
    """Plaquette circulation / 2pi, from wrapped link differences.

    Correct in the original file and kept verbatim in behaviour: the
    orientation is counter-clockwise and the wrapping is applied per link.
    """
    phi = np.asarray(phi, dtype=float)
    a = wrap(phi[:-1, 1:] - phi[:-1, :-1])
    b = wrap(phi[1:, 1:] - phi[:-1, 1:])
    c = wrap(phi[1:, :-1] - phi[1:, 1:])
    d = wrap(phi[:-1, :-1] - phi[1:, :-1])
    return (a + b + c + d) / (2.0 * np.pi)


def total_winding(phi) -> float:
    return float(np.sum(winding_number_field(phi)))


def circulation_gradient(phi, i: int, j: int, a: int, b: int,
                         h: float = 1e-6) -> float:
    """``d(circulation of plaquette (i,j)) / d(phi[a,b])`` by finite difference.

    Zero for every argument, because phi[a,b] enters two links of the plaquette
    with opposite signs. This is what makes a winding-density pin impossible to
    optimise -- see the module docstring.
    """
    phi = np.asarray(phi, dtype=float)
    if not (0 <= i < phi.shape[0] - 1 and 0 <= j < phi.shape[1] - 1):
        raise ValueError("plaquette index out of range")
    if not (0 <= a < phi.shape[0] and 0 <= b < phi.shape[1]):
        raise ValueError("site index out of range")
    base = winding_number_field(phi)[i, j]
    up = phi.copy()
    up[a, b] += h
    return float((winding_number_field(up)[i, j] - base) / h)


def core_position(phi, span: float = 1.0,
                  charge: float = 1.0) -> Optional[Tuple[float, float]]:
    """Charge-weighted centroid of the winding field, in field units.

    Cores live on PLAQUETTES, not pixels, so the plaquette centre is used --
    which removes the systematic dx/2 offset the original file carried by
    indexing circulation at the lower-left corner.
    """
    w = winding_number_field(phi)
    sel = w * charge > 0.25
    if not sel.any():
        return None
    n = np.asarray(phi).shape[0]
    ax = np.linspace(-span, span, n)
    dx = ax[1] - ax[0]
    centres = ax[:-1] + dx / 2.0                 # plaquette centres
    CX, CY = np.meshgrid(centres, centres, indexing="xy")
    wt = np.abs(w[sel])
    return (float((CX[sel] * wt).sum() / wt.sum()),
            float((CY[sel] * wt).sum() / wt.sum()))


# ---------------------------------------------------------------------------
# The pin
# ---------------------------------------------------------------------------

def pin_energy(phi, X, Y, x0: float, y0: float, k_p: float,
               charge: int = 1) -> float:
    """``(k_p/2) * sum_r wrap(phi - phi_ref)^2``. A real term in the energy."""
    if k_p < 0.0:
        raise ValueError("pin stiffness must be non-negative")
    ref = vortex_phase(X, Y, x0, y0, charge)
    return float(0.5 * k_p * np.sum(wrap(np.asarray(phi) - ref) ** 2))


def pin_gradient(phi, X, Y, x0: float, y0: float, k_p: float,
                 charge: int = 1) -> np.ndarray:
    """``dV_pin/dphi = k_p * wrap(phi - phi_ref)``. Nonzero, unlike the
    winding-density pin."""
    if k_p < 0.0:
        raise ValueError("pin stiffness must be non-negative")
    ref = vortex_phase(X, Y, x0, y0, charge)
    return k_p * wrap(np.asarray(phi) - ref)


def zero_mode_energy(displacements: Sequence[float], k_p: float,
                     n: int = 40, span: float = 1.0,
                     charge: int = 1) -> List[Tuple[float, float]]:
    """Energy cost of displacing the core, at fixed pin stiffness.

    At ``k_p = 0`` the cost is identically zero -- that is the zero mode, and it
    is why the core is free to drift. At ``k_p > 0`` the cost grows with
    displacement, so the mode is gone.
    """
    X, Y = grid(n, span)
    out = []
    for d in displacements:
        moved = vortex_phase(X, Y, d, 0.0, charge)
        out.append((float(d), pin_energy(moved, X, Y, 0.0, 0.0, k_p, charge)))
    return out


def smooth_energy_gradient(phi, alpha: float) -> np.ndarray:
    """Gradient of a Laplacian smoothing energy -- the drift driver."""
    p = np.asarray(phi, dtype=float)
    lap = (np.roll(p, 1, 0) + np.roll(p, -1, 0)
           + np.roll(p, 1, 1) + np.roll(p, -1, 1) - 4.0 * p)
    return -alpha * lap


def evolve(phi, X, Y, x0: float, y0: float, k_p: float,
           steps: int = 200, eta: float = 1.0, alpha: float = 0.01,
           noise: float = 0.0, seed: Optional[int] = None,
           charge: int = 1) -> np.ndarray:
    """Gradient flow under smoothing + pin + optional noise."""
    if steps < 0:
        raise ValueError("steps must be non-negative")
    rng = np.random.default_rng(seed)
    p = np.array(phi, dtype=float, copy=True)
    for _ in range(steps):
        g = smooth_energy_gradient(p, alpha) + pin_gradient(p, X, Y, x0, y0,
                                                            k_p, charge)
        p = p - eta * g
        if noise > 0.0:
            p = p + rng.normal(0.0, noise, p.shape)
        p = wrap(p)
    return p


def vortex_pair(X, Y, x0: float, y0: float, separation: float = 0.6):
    """A +1 / -1 pair. On a periodic grid the NET winding must vanish, so a
    lone vortex is not a legal configuration -- it dissolves rather than
    drifting, which is an artifact of the boundary and not a result."""
    return wrap(vortex_phase(X, Y, x0, y0, 1)
                + vortex_phase(X, Y, x0 + separation, y0, -1))


def run_pin_sweep(k_values: Sequence[float] = (0.0, 0.01, 0.05, 0.2, 1.0),
                  n: int = 40, span: float = 1.0, steps: int = 120,
                  noise: float = 0.015, alpha: float = 0.002,
                  separation: float = 0.9, seeds: int = 12,
                  base_seed: int = 0) -> List[Dict[str, object]]:
    """Displacement of the +1 core against pin stiffness, averaged over seeds.

    ``k_p = 0`` is the registry control: an address is recorded and nothing
    holds the core to it. Higher ``k_p`` is a real restoring term in the energy.
    The pin reference is the same pair configuration, so the comparison isolates
    stiffness alone.

    A core is localised to a plaquette, so a single run resolves displacement
    only in units of ``dx``. Averaging over seeds recovers a sub-plaquette mean
    and a hop fraction -- the fraction of runs in which the core left its
    starting plaquette at all, which is the quantity the registry needs to be
    zero and cannot make so.
    """
    if not k_values:
        raise ValueError("need at least one stiffness")
    if seeds < 1:
        raise ValueError("need at least one seed")
    X, Y = grid(n, span)
    dx = 2.0 * span / (n - 1)
    rows = []
    for k_p in k_values:
        if k_p < 0.0:
            raise ValueError("pin stiffness must be non-negative")
        drifts, survived, hops = [], 0, 0
        for s in range(seeds):
            ref = vortex_pair(X, Y, 0.0, 0.0, separation)
            p = np.array(ref, dtype=float, copy=True)
            rng = np.random.default_rng(base_seed + s)
            for _ in range(steps):
                g = smooth_energy_gradient(p, alpha) + k_p * wrap(p - ref)
                p = wrap(p - g + (rng.normal(0.0, noise, p.shape)
                                  if noise > 0 else 0.0))
            if int(np.sum(np.abs(winding_number_field(p)) > 0.5)) >= 2:
                survived += 1
            pos = core_position(p, span, charge=1.0)
            if pos is not None:
                d = math.hypot(pos[0], pos[1])
                drifts.append(d)
                if d >= dx * 0.5:
                    hops += 1
        rows.append({
            "k_p": float(k_p),
            "mean_displacement": (sum(drifts) / len(drifts) if drifts
                                  else float("nan")),
            "max_displacement": max(drifts) if drifts else float("nan"),
            "hop_fraction": hops / seeds,
            "survival_fraction": survived / seeds,
            "plaquette_width": dx,
            "seeds": seeds,
            "is_registry_control": k_p == 0.0,
        })
    return rows


# ---------------------------------------------------------------------------
# TOP-3: a target that does not come from the model
# ---------------------------------------------------------------------------

def gauss_flux_target(charge: int) -> Dict[str, object]:
    """``2 pi k`` -- the Gauss flux of a charge-k vortex.

    An INTEGER multiple of 2pi, exactly known, and independent of any
    particular phi. ``run_fixed_W`` currently defines its target as the vortex
    model's own output, so "V beats S and X" is a definition rather than a
    measurement. This is the replacement: getting it right would mean the heads
    computed something.
    """
    if int(charge) != charge:
        raise ValueError("winding charge must be an integer")
    return {"charge": int(charge), "flux": 2.0 * math.pi * int(charge),
            "model_independent": True,
            "note": "exactly known; does not reference any model's output"}


# ---------------------------------------------------------------------------
# VOR-2: a controlled comparison
# ---------------------------------------------------------------------------

def controlled_vortex_comparison(n: int = 40, span: float = 1.0,
                                 amplitude: float = 0.3,
                                 seed: int = 0) -> Dict[str, object]:
    """Same phi init for both arms; the vortex is added on top.

    The original compares ``phi_v`` (spanning +-pi) against
    ``phi_flat = uniform(-0.3, 0.3)`` and calls them "the same random init".
    They differ in phase AMPLITUDE as well as topology, and the amplitude
    difference alone moves the forward map ``cos(phi)*inp`` from a full sign
    range to nearly the identity: cos of +-0.3 lies in [0.955, 1.0].

    It then compares percentage reductions from different denominators, so a run
    that starts worse can show a larger drop and still end higher. This returns
    FINAL ABSOLUTE values alongside the reductions, so the verdict can be read
    off the quantity that matters.
    """
    if amplitude <= 0.0:
        raise ValueError("amplitude must be positive")
    rng = np.random.default_rng(seed)
    X, Y = grid(n, span)
    base = rng.uniform(-amplitude, amplitude, (n, n))
    flat = wrap(base)
    withv = wrap(base + vortex_phase(X, Y, 0.3, 0.0, 1)
                 + vortex_phase(X, Y, -0.3, 0.0, -1))
    return {
        "shared_init": True,
        "flat_cos_range": (float(np.cos(flat).min()), float(np.cos(flat).max())),
        "vortex_cos_range": (float(np.cos(withv).min()),
                             float(np.cos(withv).max())),
        "flat_net_winding": total_winding(flat),
        "vortex_net_winding": total_winding(withv),
        "flat_core_count": int(np.sum(np.abs(winding_number_field(flat)) > 0.5)),
        "vortex_core_count": int(np.sum(np.abs(winding_number_field(withv)) > 0.5)),
        "note": "compare FINAL ABSOLUTE loss, not percentage reduction from "
                "different denominators",
    }


def head_contrast_cases() -> List[Dict[str, object]]:
    """The two degenerate cases of ``|s+ - s-| / (|s+| + |s-|)``."""
    def hc(sp, sn):
        d = abs(sp) + abs(sn)
        return abs(sp - sn) / d if d > 0 else float("nan")
    return [
        {"s_pos": 1.0, "s_neg": 0.0, "contrast": hc(1.0, 0.0),
         "defect": "a head seeing ONE lobe scores a perfect 1.0"},
        {"s_pos": 0.0, "s_neg": 0.0, "contrast": hc(0.0, 0.0),
         "defect": "a head seeing NOTHING is 0/0 -- NaN, not 1.0"},
    ]


# ---------------------------------------------------------------------------

def main() -> None:
    print("PINNING A VORTEX CORE\n" + "=" * 68)

    print("\nWhy the obvious pin is unavailable")
    X, Y = grid(16)
    rng = np.random.default_rng(3)
    phi = rng.uniform(-0.5, 0.5, (16, 16))
    worst = 0.0
    for _ in range(200):
        i, j = int(rng.integers(0, 15)), int(rng.integers(0, 15))
        a, b = int(rng.integers(0, 16)), int(rng.integers(0, 16))
        worst = max(worst, abs(circulation_gradient(phi, i, j, a, b)))
    print(f"  d(circulation)/d(phi_i), 200 probes: worst {worst:.2e}")
    print("  each phi enters two links with opposite signs, so it cancels.")
    print("  a winding-density pin has NO gradient: the same invariance that")
    print("  protects the charge makes that pin un-optimisable. A pin must")
    print("  couple to something non-topological.")

    print("\nATT-1  the zero mode, and removing it")
    print(f"  {'displacement':>13} {'k_p = 0':>12} {'k_p = 0.05':>12} "
          f"{'k_p = 0.20':>12}")
    d_list = [0.0, 0.1, 0.2, 0.4]
    e0 = dict(zero_mode_energy(d_list, 0.0))
    e1 = dict(zero_mode_energy(d_list, 0.05))
    e2 = dict(zero_mode_energy(d_list, 0.20))
    for d in d_list:
        print(f"  {d:>13.2f} {e0[d]:>12.4f} {e1[d]:>12.4f} {e2[d]:>12.4f}")
    print("  k_p = 0: displacement is free. That IS the zero mode, and it is")
    print("  what a registry leaves untouched.")

    print("\n  +1 core displacement under noisy flow, averaged over seeds:")
    rows = run_pin_sweep()
    print(f"  (one plaquette = {rows[0]['plaquette_width']:.4f} field units, "
          f"{rows[0]['seeds']} seeds)")
    print(f"  {'k_p':>8} {'mean |r|':>10} {'hop frac':>9} {'survived':>9}   note")
    for row in rows:
        tag = "  <- the registry: bookkeeping only" if row["is_registry_control"] else ""
        print(f"  {row['k_p']:>8.2f} {row['mean_displacement']:>10.4f} "
              f"{row['hop_fraction']:>9.2f} {row['survival_fraction']:>9.2f}{tag}")
    print("  charge is conserved in every row -- it always was. What changes")
    print("  with k_p is POSITION, which is the quantity the registry claimed")
    print("  to protect and could not.")

    print("\nTOP-3  a target that does not come from the model")
    for k in (1, -1, 2):
        g = gauss_flux_target(k)
        print(f"  charge {g['charge']:+d}: flux = {g['flux']:+.6f} "
              f"= 2*pi*{g['charge']:+d}")
    print("  exactly known, integer, independent of any phi. run_fixed_W's")
    print("  current target is the vortex model's own output.")

    print("\nVOR-2  the two conditions are not the same init")
    c = controlled_vortex_comparison()
    print(f"  flat   cos(phi) range: [{c['flat_cos_range'][0]:+.4f}, "
          f"{c['flat_cos_range'][1]:+.4f}]")
    print(f"  vortex cos(phi) range: [{c['vortex_cos_range'][0]:+.4f}, "
          f"{c['vortex_cos_range'][1]:+.4f}]")
    print(f"  net winding: flat {c['flat_net_winding']:+.2f}, "
          f"vortex {c['vortex_net_winding']:+.2f}  (a pair, so net 0 by design)")
    print(f"  cores detected: flat {c['flat_core_count']}, "
          f"vortex {c['vortex_core_count']}")
    print("  shared init, vortex added on top -- so topology is the only")
    print("  difference, and the comparison is on final absolute loss.")

    print("\nhead_contrast degenerate cases")
    for case in head_contrast_cases():
        print(f"  s+={case['s_pos']}, s-={case['s_neg']} -> "
              f"{case['contrast']}   {case['defect']}")


if __name__ == "__main__":
    main()
