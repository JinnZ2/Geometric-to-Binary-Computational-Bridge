#!/usr/bin/env python3
# STATUS: infrastructure — kT annealing simulation
"""
kt_annealing.py
===============
Optimal annealing schedule for mandala_computer.py derived from
Kosterlitz-Thouless transition physics.

The Problem
-----------
mandala_computer.py uses FIXED temperature MH relaxation.
The default T=1.0 sits just above T_KT ≈ 0.9 J — the worst place to be stuck.
Above T_KT: free vortices roam, system never settles.
Below T_KT: dipoles bind, system converges.
At T_KT: critical slowing down, correlation time diverges.

The Fix
-------
Start well above T_KT (explore freely), cross T_KT with the correct rate,
finish well below (lock in ground state).

Near T_KT the correlation length diverges as an ESSENTIAL SINGULARITY:
    ξ(T) ~ exp(b / sqrt((T - T_KT) / T_KT))   for T → T_KT⁺

This means logarithmic cooling is optimal — power-law cooling leaves O(1)
defect density no matter how slow it is.

Derivation Sections
-------------------
1. T_KT from coupling J (analytic + numerical)
2. Relaxation time divergence (dynamical scaling)
3. Kibble-Zurek freeze-out for KT transition
4. Three schedule comparison on 2D XY lattice
5. Optimal parameters for mandala_computer.py

Run:
    python Silicon/kt_annealing.py
"""

from __future__ import annotations
import numpy as np
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# vortex_phase_learning moved to experiments/silicon_speculative/
try:
    from experiments.silicon_speculative.vortex_phase_learning import winding_number_field
except ImportError:
    winding_number_field = None

# ============================================================
# Section 1: T_KT derivation
# ============================================================

PHI = (1 + np.sqrt(5)) / 2

# Mandala coupling formula: E = J * sin^2(|s_i - s_j| * pi/4)
# Peak coupling at |s_i - s_j| = 2:  sin^2(pi/2) = 1  => E_peak = J
# So effective J = coupling_strength (default 1.0)

J_COUPLING = 1.0   # mandala_computer.py default coupling_strength

# KT transition — two equivalent statements:
#
# Analytic (renormalized spin stiffness at transition):
#   K_c = J / (k_B T_KT) = 2/pi    (BKT universal jump)
#   => T_KT_analytic = pi*J/2
#
# Numerical (bare 2D XY on square lattice, from Monte Carlo):
#   T_KT_numerical ≈ 0.8929 * J
#
# The difference: RG flow renormalizes the bare stiffness downward.
# For simulation purposes, use the numerical value.

T_KT_ANALYTIC  = np.pi * J_COUPLING / 2           # ≈ 1.571
T_KT_NUMERICAL = 0.8929 * J_COUPLING              # ≈ 0.893  ← use this

# Vortex core energy (discrete lattice, 4-connected)
# E_core ≈ pi * J * ln(L/a) for system size L, lattice spacing a
# For our finite grid, the effective core energy is:
E_CORE = np.pi * J_COUPLING                        # ≈ 3.14 J (leading term)

# Dynamical critical exponent for Model A (non-conserved order parameter)
Z_DYNAMIC = 2.0

# KT amplitude constant b (from RG, order 1)
B_KT = 1.5

# ============================================================
# Section 2: Schedule functions
# ============================================================

def schedule_linear(step: int, n_steps: int,
                    T_init: float, T_final: float) -> float:
    """T(t) = T_init + (T_final - T_init) * t/n_steps"""
    return T_init + (T_final - T_init) * step / n_steps


def schedule_power(step: int, n_steps: int,
                   T_init: float, T_final: float,
                   alpha: float = 1.5) -> float:
    """T(t) = T_final + (T_init - T_final) / (1 + step/tau)^alpha"""
    tau = n_steps / ((T_init / T_final) ** (1 / alpha) - 1)
    return T_final + (T_init - T_final) / (1.0 + step / tau) ** alpha


def schedule_log(step: int, n_steps: int,
                 T_init: float, T_kt: float,
                 T_final: float = None) -> float:
    """
    Three-phase KT-optimal schedule that correctly crosses T_kt.

    Bug in the previous version: T_kt*(1 + C/ln²(t)) asymptotes TO T_kt
    from above but never crosses below it.  The system ended at T > T_kt
    (still in the free-vortex phase) with 254 residual defects.

    Fix: three explicit phases with quadratic vanishing of dT/dt at T_kt.

    Phase 1  [0,   n//5]:    fast exponential  T_init  → 2*T_kt
    Phase 2  [n//5, 4n//5]:  slow crossing of T_kt
        Above T_kt: T = T_kt*(1 + (1-2x)²)   x ∈ [0, 0.5]
                    dT/dt → 0 quadratically as T → T_kt from above
        Below T_kt: T = T_kt*(0.3 + 0.7*(1-2(x-0.5))²)
                    symmetric slow exit below T_kt
    Phase 3  [4n//5, n]:    fast exponential  0.3*T_kt → T_final

    The quadratic vanishing of dT/dt near T_kt is consistent with the
    KT relaxation time τ ~ exp(b/sqrt(ε)) diverging as ε→0.
    The system spends the most time in the critical window.
    """
    if T_final is None:
        T_final = 0.1 * T_kt

    t1 = n_steps // 5
    t2 = 4 * n_steps // 5

    if step < t1:
        # Phase 1: fast exponential T_init → 2*T_kt
        frac = step / max(t1, 1)
        return T_init * (2.0 * T_kt / T_init) ** frac

    elif step < t2:
        x = (step - t1) / (t2 - t1)   # 0 → 1
        if x < 0.5:
            # Above T_kt: quadratic approach to T_kt
            # T(0)=2*T_kt, T(0.5)=T_kt, dT/dx → 0 at x=0.5
            return T_kt * (1.0 + (1.0 - 2.0 * x) ** 2)
        else:
            # Below T_kt: quadratic exit from T_kt
            # T(0.5)=T_kt, T(1)=0.3*T_kt, dT/dx → 0 at x=0.5
            x_b = 2.0 * (x - 0.5)          # 0 → 1
            return T_kt * (0.3 + 0.7 * (1.0 - x_b) ** 2)

    else:
        # Phase 3: fast exponential 0.3*T_kt → T_final
        frac = (step - t2) / max(n_steps - t2, 1)
        return 0.3 * T_kt * (T_final / (0.3 * T_kt)) ** frac


# ============================================================
# Section 3: KZ freeze-out prediction
# ============================================================

def frozen_vortex_density_linear(tau_Q: float, T_kt: float = T_KT_NUMERICAL) -> float:
    """
    Vortex density frozen in by linear quench through T_KT at rate 1/tau_Q.

    From KZ self-consistency for KT essential singularity:
        epsilon* = (B_KT * Z_DYNAMIC)^2 / ln^2(tau_Q / tau_0)
        xi* = exp(B_KT / sqrt(epsilon*))
        n_defects ~ xi*^{-2}

    Result: n_defects ~ tau_Q^{-2}  (power law, NOT logarithm)
    """
    ln_tau = np.log(max(tau_Q, 1.1))
    eps_star = (B_KT * Z_DYNAMIC) ** 2 / ln_tau ** 2
    xi_star = np.exp(B_KT / (np.sqrt(eps_star) + 1e-10))
    return xi_star ** (-2)


def frozen_vortex_density_log(n_steps: int, T_kt: float = T_KT_NUMERICAL) -> float:
    """
    Vortex density under logarithmic cooling.

    The log schedule drives n_defects → 0 asymptotically as:
        n_defects ~ exp(-2 * B_KT * ln(n_steps/tau_0))
                  = (tau_0 / n_steps)^{2*B_KT}

    Exponentially fewer defects than power law for same budget.
    """
    return (1.0 / max(n_steps, 2)) ** (2 * B_KT)


# ============================================================
# Section 4: 2D XY Langevin simulation
# ============================================================

def langevin_step(phi: np.ndarray, T: float, J: float = J_COUPLING,
                  dt: float = 0.05) -> np.ndarray:
    """
    One step of overdamped Langevin dynamics for the 2D XY model.

    dphi/dt = J * sin-Laplacian(phi) + sqrt(2T) * eta

    The sine-Laplacian is the discrete XY force:
        F_i = sum_j sin(phi_j - phi_i)   (4 neighbours)
    """
    # Discrete sine-Laplacian (force from 4 neighbours)
    force = (np.sin(np.roll(phi, -1, axis=0) - phi) +
             np.sin(np.roll(phi,  1, axis=0) - phi) +
             np.sin(np.roll(phi, -1, axis=1) - phi) +
             np.sin(np.roll(phi,  1, axis=1) - phi))

    noise = np.sqrt(2.0 * T * dt) * np.random.randn(*phi.shape)
    phi_new = phi + dt * J * force + noise
    return (phi_new + np.pi) % (2 * np.pi) - np.pi


def count_vortices(phi: np.ndarray) -> tuple[int, int]:
    """Count positive and negative winding-number vortices."""
    w = winding_number_field(phi)
    return int((w > 0.5).sum()), int((w < -0.5).sum())


def run_schedule(schedule_fn, N: int, n_steps: int, rng_seed: int = 42,
                 T_init: float = None) -> dict:
    """
    Run a full annealing schedule and report final defect count.

    Returns: dict with T trace, vortex trace, and final state.
    """
    rng = np.random.default_rng(rng_seed)
    # Start from a hot random configuration
    phi = rng.uniform(-np.pi, np.pi, (N, N))

    T_log = []
    v_log = []

    for step in range(n_steps + 1):
        T = schedule_fn(step)
        if step % (n_steps // 20) == 0:
            pos, neg = count_vortices(phi)
            T_log.append(T)
            v_log.append(pos + neg)

        if step < n_steps:
            phi = langevin_step(phi, T)

    pos_final, neg_final = count_vortices(phi)
    return {
        "T_trace":      T_log,
        "vortex_trace": v_log,
        "final_vortices": pos_final + neg_final,
        "final_free":   abs(pos_final - neg_final),  # charge imbalance = unbound
        "phi":          phi,
    }


# ============================================================
# Section 5: Main — derive, simulate, recommend
# ============================================================

def run(N: int = 40, n_steps: int = 2000, seeds: int = 3):

    print("=" * 68)
    print("KT ANNEALING ANALYSIS for mandala_computer.py")
    print("=" * 68)
    print()

    # --- Derivation -----------------------------------------------------------
    print("── 1. T_KT DERIVATION ─────────────────────────────────────────────")
    print()
    print(f"  Coupling: E = J * sin²(|Δstate| * π/4)")
    print(f"  Peak coupling at |Δstate|=2: J_eff = {J_COUPLING:.3f}")
    print()
    print(f"  T_KT (analytic, renormalized stiffness)  = π*J/2  = {T_KT_ANALYTIC:.4f}")
    print(f"  T_KT (numerical, bare 2D XY, Monte Carlo) ≈ 0.893*J = {T_KT_NUMERICAL:.4f}")
    print()
    print(f"  mandala_computer.py default temperatures:")
    print(f"    T=0.3 → {0.3/T_KT_NUMERICAL:.2f} × T_KT  (deep ordered phase, frozen)")
    print(f"    T=0.5 → {0.5/T_KT_NUMERICAL:.2f} × T_KT  (ordered, may miss ground state)")
    print(f"    T=1.0 → {1.0/T_KT_NUMERICAL:.2f} × T_KT  (just above transition — WORST POINT)")
    print()
    print(f"  Recommended T_init = 3–5 × T_KT = {3*T_KT_NUMERICAL:.2f}–{5*T_KT_NUMERICAL:.2f}")
    print()

    # --- KZ predictions -------------------------------------------------------
    print("── 2. KIBBLE-ZUREK DEFECT DENSITY PREDICTIONS ─────────────────────")
    print()
    print(f"  Near T_KT, correlation length diverges as essential singularity:")
    print(f"    ξ(T) ~ exp(b / sqrt((T-T_KT)/T_KT))  [faster than any power law]")
    print()
    print(f"  {'Schedule':<20}  {'n_steps':>8}  {'n_defects (predicted)':>22}")
    print("  " + "-" * 54)
    for n in [500, 2000, 10000]:
        n_lin = frozen_vortex_density_linear(n) * N * N
        n_log = frozen_vortex_density_log(n)    * N * N
        print(f"  {'Linear':20}  {n:8d}  {n_lin:22.2f}")
        print(f"  {'Logarithmic':20}  {n:8d}  {n_log:22.6f}")
        print()

    print(f"  Key result: logarithmic cooling gives exponentially fewer defects.")
    print(f"  Power law cooling leaves O(1) defect density regardless of n_steps.")
    print()

    # --- Simulation -----------------------------------------------------------
    print("── 3. SIMULATION: THREE SCHEDULES (N={}×{}, {} steps) ─────────────".format(
        N, N, n_steps))
    print()

    T_init  = 4.0 * T_KT_NUMERICAL
    T_final = 0.1 * T_KT_NUMERICAL

    schedules = {
        "Linear":      lambda s: schedule_linear(s, n_steps, T_init, T_final),
        "Power(α=1.5)": lambda s: schedule_power(s, n_steps, T_init, T_final, 1.5),
        "Logarithmic": lambda s: schedule_log(s, n_steps, T_init, T_KT_NUMERICAL),
    }

    results = {}
    print(f"  {'Schedule':<16}  {'Final T':>8}  {'Vortices':>10}  {'Free':>6}  {'Defect/cell':>12}")
    print("  " + "-" * 60)

    for name, fn in schedules.items():
        totals = {"final_vortices": [], "final_free": []}
        for seed in range(seeds):
            r = run_schedule(fn, N, n_steps, rng_seed=seed)
            totals["final_vortices"].append(r["final_vortices"])
            totals["final_free"].append(r["final_free"])
            if name == "Logarithmic":
                results[name] = r   # save one for display

        mv = np.mean(totals["final_vortices"])
        mf = np.mean(totals["final_free"])
        T_end = fn(n_steps)
        dpc = mv / (N * N)
        print(f"  {name:<16}  {T_end:8.4f}  {mv:10.1f}  {mf:6.1f}  {dpc:12.6f}")

    print()

    # --- Optimal parameters ---------------------------------------------------
    print("── 4. OPTIMAL PARAMETERS FOR mandala_computer.py ───────────────────")
    print()
    T_kt  = T_KT_NUMERICAL
    C_opt = (B_KT * Z_DYNAMIC) ** 2
    print(f"  T_KT (use this value): {T_kt:.4f}")
    print()
    print("  Recommended schedule (paste into relax_to_ground_state):")
    print()
    T_final_disp = 0.1 * T_kt
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print(f"  │  T_init   = {T_init:.4f}  # 4 × T_KT, start hot             │")
    print(f"  │  T_KT     = {T_kt:.4f}  # KT transition temperature       │")
    print(f"  │  T_final  = {T_final_disp:.4f}  # 0.1 × T_KT, locked ground state  │")
    print("  │                                                             │")
    print("  │  Three-phase schedule (dT/dt → 0 quadratically at T_KT):  │")
    print("  │                                                             │")
    print("  │  Phase 1 [0, n//5]:    T_init → 2*T_KT  (fast exp)        │")
    print("  │  Phase 2 [n//5, 4n//5]:                                    │")
    print("  │    Above T_KT:  T = T_KT*(1 + (1-2x)²)   x ∈ [0, 0.5]   │")
    print("  │    Below T_KT:  T = T_KT*(0.3+0.7*(1-2(x-½))²)           │")
    print("  │    → dT/dt vanishes quadratically at T_KT (critical slow) │")
    print("  │  Phase 3 [4n//5, n]:   0.3*T_KT → T_final (fast exp)     │")
    print("  │                                                             │")
    print("  │  Use: schedule_log(step, n_steps, T_init, T_KT)           │")
    print("  │  from Silicon.kt_annealing import schedule_log, T_KT_NUMERICAL │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()

    print("── 5. CONNECTION TO mandala_computer.py ────────────────────────────")
    print()
    print("  Current relax_to_ground_state() calls relax_step() at fixed T.")
    print("  Replace temperature parameter with kt_schedule(step, max_steps, ...):")
    print()
    print("  # In relax_to_ground_state(), change:")
    print("  #   dE = self.relax_step()          # fixed T")
    print("  # To:")
    print("  #   self.temperature = kt_schedule(step, max_steps, T_init, T_KT, C)")
    print("  #   dE = self.relax_step()          # temperature now decreasing")
    print()
    print(f"  For golden_depth=5 (default): ~{int(PHI**5 + PHI**4 + PHI**3 + PHI**2 + PHI)}"
          f" cells → use max_steps ≥ {int(PHI**5 + PHI**4 + PHI**3 + PHI**2 + PHI) * 200}")
    print()
    print(f"  The log cooling phase near T_KT needs ≥ 2/3 of total steps.")
    print(f"  Minimum useful budget: ~1000 steps for N≤50 cells.")
    print()
    print("=" * 68)

    return {
        "T_KT": T_kt,
        "T_init": T_init,
        "C_optimal": C_opt,
        "results": results,
    }


if __name__ == "__main__":
    run()
