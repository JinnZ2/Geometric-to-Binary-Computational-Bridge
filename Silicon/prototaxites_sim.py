#!/usr/bin/env python3
"""
prototaxites_sim.py
===================
Numeric simulation of the Prototaxites Energy Mimetics framework.

Source: experiments/prototaxites.md

The Prototaxites organism (420-370 Mya) is interpreted here as a
sophisticated multi-source electromagnetic energy processor with three
tube types and a distributed adaptive nervous system.

Model
-----
Three tube types (from fossil evidence):
  Type 1 -- thin septate HF tubes    (10 MHz - 10 GHz  EM antennae)
  Type 2 -- wide smooth LF tubes     (DC  - 10 MHz  power transmission)
  Type 3 -- medullary spots          (capacitive/inductive storage nodes)

Five energy sources with time-varying availability:
  cosmic, electromagnetic, thermal, chemical, plasma

Key equations implemented
-------------------------
Adaptive efficiency (prototaxites.md, Feedback Control System):
    eta(E) = eta0 * [1 + tanh(beta * (E - E_threshold))]

Dynamic source weighting:
    w_i(t) = (E_i / E_th_i) / sum_j(E_j / E_th_j)

Storage dynamics (per storage node):
    dE_stored/dt = eta(E_in) * E_in - P_metabolic(E_stored)

Feast-or-famine metabolic rate:
    P_met(E) = P_min + (P_max - P_min) * (1 - exp(-E / E_scale))

Resonant quality factor (Type 1 tube):
    f_res = 1 / (2*pi*sqrt(L*C))
    Q     = omega0 * L / R

Adaptive conductivity (prototaxites.md, Adaptive Conductivity):
    sigma(T) = sigma0 * exp(-Ea / (kB * T))
    R(T) ∝ 1 / sigma(T)   =>   Q(T) = omega0 * L * sigma(T) / A_tube

Predictions to verify
---------------------
  1. Threshold awakening  -- eta shows > 2x increase across E_threshold
  2. Dynamic load balance -- weights redistribute as sources fade/spike
  3. Storage buffering    -- E_stored variance < E_in variance  (ratio > 2x)
  4. Adaptive Q           -- Q(T) rises with T (conductivity-driven)
"""

import numpy as np

# ---------------------------------------------------------------------------
# Physical parameters (normalized / dimensionless unless noted)
# ---------------------------------------------------------------------------

# --- Tube parameters ---
N_TYPE1  = 12       # HF signal tubes (antennae)
N_TYPE2  =  6       # LF power tubes
N_TYPE3  =  8       # medullary storage nodes

L1 = 1e-9           # Type-1 inductance (H)  -- HF: f ~ GHz
C1 = 1e-12          # Type-1 capacitance (F)
R1_BASE = 1.0       # Base resistance (normalized Ohms)

L2 = 1e-6           # Type-2 inductance (H)  -- LF: f ~ MHz
C2 = 1e-9           # Type-2 capacitance (F)
R2_BASE = 0.5

C3 = 1e-6           # Storage node capacitance
L3 = 1e-6           # Storage node inductance
E3_MAX  = 10.0      # Max storable energy per node (normalized)

# --- Efficiency function ---
ETA0        = 0.5   # half-value so full awakening reaches eta=1
BETA_EFF    = 8.0   # steepness of tanh transition
E_THRESHOLD = 0.5   # threshold energy triggering awakening

# --- Metabolic rate ---
P_MET_MIN   = 0.04
P_MET_MAX   = 0.30
E_MET_SCALE = 0.8

# --- Adaptive conductivity ---
SIGMA0 = 1.0        # base conductivity (normalized)
EA_KB  = 1200.0     # Ea / kB  (Kelvin), controls temperature sensitivity
A_TUBE = 0.01       # tube cross-section area (normalized)

# --- Source threshold energies for weight normalisation ---
E_SOURCE_THRESHOLDS = np.array([0.3, 0.5, 0.4, 0.6, 0.7])   # cosmic/EM/thermal/chem/plasma


# ---------------------------------------------------------------------------
# Core equations
# ---------------------------------------------------------------------------

def adaptive_efficiency(E_in: float | np.ndarray,
                        eta0: float = ETA0,
                        beta: float = BETA_EFF,
                        E_thr: float = E_THRESHOLD) -> float | np.ndarray:
    """eta(E) = eta0 * [1 + tanh(beta * (E - E_threshold))]"""
    return eta0 * (1.0 + np.tanh(beta * (E_in - E_thr)))


def source_weights(E_sources: np.ndarray,
                   E_thresholds: np.ndarray = E_SOURCE_THRESHOLDS) -> np.ndarray:
    """w_i = (E_i / E_th_i) / sum_j(E_j / E_th_j).  Returns (5,) array."""
    ratios = E_sources / (E_thresholds + 1e-12)
    total  = ratios.sum()
    return ratios / (total if total > 0 else 1.0)


def metabolic_rate(E_stored: float | np.ndarray,
                   P_min: float = P_MET_MIN,
                   P_max: float = P_MET_MAX,
                   E_scale: float = E_MET_SCALE) -> float | np.ndarray:
    """P(E) = P_min + (P_max - P_min) * (1 - exp(-E / E_scale))"""
    return P_min + (P_max - P_min) * (1.0 - np.exp(-E_stored / E_scale))


def quality_factor(omega0: float, L: float, R: float) -> float:
    """Q = omega0 * L / R"""
    return omega0 * L / R


def adaptive_conductivity(T: float | np.ndarray,
                           sigma0: float = SIGMA0,
                           Ea_kB: float = EA_KB) -> float | np.ndarray:
    """sigma(T) = sigma0 * exp(-Ea / (kB * T))"""
    return sigma0 * np.exp(-Ea_kB / T)


def resonant_frequency(L: float, C: float) -> float:
    """f = 1 / (2*pi*sqrt(L*C))"""
    return 1.0 / (2.0 * np.pi * np.sqrt(L * C))


# ---------------------------------------------------------------------------
# Energy source model  (time-varying, normalized to [0, 1])
# ---------------------------------------------------------------------------

def energy_sources(t: float, T_sim: float, rng: np.random.Generator) -> np.ndarray:
    """
    Return instantaneous energies for the 5 source types at time t.

    Returns
    -------
    E : ndarray (5,)  -- [cosmic, electromagnetic, thermal, chemical, plasma]
    """
    t_frac = t / T_sim   # [0, 1]

    # Cosmic: low baseline + rare high-energy spikes
    cosmic = 0.15 + 0.03 * rng.standard_normal()
    if rng.random() < 0.03:           # 3% chance of cosmic ray burst
        cosmic += rng.uniform(0.4, 0.9)
    cosmic = float(np.clip(cosmic, 0, 1))

    # Electromagnetic: smooth day/night cycle
    em = 0.45 * (1.0 + np.sin(2.0 * np.pi * t_frac * 3.0)) / 2.0
    em += 0.03 * rng.standard_normal()
    em = float(np.clip(em, 0, 1))

    # Thermal: slow season-like variation
    thermal = 0.35 * (1.0 + np.cos(2.0 * np.pi * t_frac * 1.5)) / 2.0
    thermal += 0.02 * rng.standard_normal()
    thermal = float(np.clip(thermal, 0, 1))

    # Chemical: available for first 60% of simulation, then drops
    chemical = 0.55 if t_frac < 0.6 else 0.18
    chemical += 0.02 * rng.standard_normal()
    chemical = float(np.clip(chemical, 0, 1))

    # Plasma: rare large pulses (geomagnetic storms)
    if rng.random() < 0.02:           # 2% chance of plasma pulse
        plasma = rng.uniform(0.6, 1.0)
    else:
        plasma = 0.05 + 0.01 * max(0, rng.standard_normal())
    plasma = float(np.clip(plasma, 0, 1))

    return np.array([cosmic, em, thermal, chemical, plasma])


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def run(T_sim: float = 200.0, dt: float = 0.5,
        seed: int = 42, verbose: bool = True) -> dict:
    """
    Simulate the Prototaxites energy processor over T_sim time steps.

    Returns a dict with time-series arrays for all key observables.
    """
    rng   = np.random.default_rng(seed)
    steps = int(T_sim / dt)
    times = np.arange(steps) * dt

    # Storage node state  (N_TYPE3 independent nodes)
    E_stored = np.ones(N_TYPE3) * 0.3     # initial partial charge

    # Recording arrays
    rec_E_in     = np.zeros(steps)        # total energy intake
    rec_eta      = np.zeros(steps)        # efficiency applied
    rec_E_cond   = np.zeros(steps)        # conditioned (efficiency-scaled) energy
    rec_E_stored = np.zeros(steps)        # mean stored energy across nodes
    rec_weights  = np.zeros((steps, 5))  # source weights
    rec_sources  = np.zeros((steps, 5))  # raw source energies
    rec_T_local  = np.zeros(steps)        # local temperature proxy

    if verbose:
        print("=" * 64)
        print("Prototaxites Energy Mimetics -- Numeric Experiment")
        print("Source: experiments/prototaxites.md")
        print("=" * 64)
        print(f"\n  T_sim={T_sim}  dt={dt}  steps={steps}")
        print(f"  Tubes: {N_TYPE1} Type-1 (HF)  {N_TYPE2} Type-2 (LF)  "
              f"{N_TYPE3} Type-3 (storage)")
        f1 = resonant_frequency(L1, C1)
        f2 = resonant_frequency(L2, C2)
        print(f"  f_res1 = {f1/1e9:.2f} GHz  |  f_res2 = {f2/1e6:.2f} MHz")

    for step in range(steps):
        t = times[step]

        # 1. Read energy sources
        E_src = energy_sources(t, T_sim, rng)
        rec_sources[step] = E_src

        # 2. Dynamic source weighting
        w = source_weights(E_src)
        rec_weights[step] = w

        # 3. Total energy intake
        E_in = float((w * E_src).sum())
        rec_E_in[step] = E_in

        # 4. Adaptive efficiency (Type-1 + Type-2 combined response)
        eta = adaptive_efficiency(E_in)
        rec_eta[step] = eta

        # 5. Conditioned energy
        E_cond = eta * E_in
        rec_E_cond[step] = E_cond

        # 6. Distribute conditioned energy across storage nodes
        E_per_node = E_cond / N_TYPE3

        # 7. Update each storage node:  dE/dt = E_per_node - P_metabolic(E)
        P_met = metabolic_rate(E_stored)
        dE    = (E_per_node - P_met) * dt
        E_stored = np.clip(E_stored + dE, 0.0, E3_MAX)

        rec_E_stored[step] = float(E_stored.mean())

        # 8. Local temperature proxy: rises with stored + intake energy
        T_local = 250.0 + 100.0 * float(E_stored.mean()) / E3_MAX
        rec_T_local[step] = T_local

    # -----------------------------------------------------------------------
    # Analysis & verification
    # -----------------------------------------------------------------------

    # --- Prediction 1: Threshold awakening ---
    E_scan     = np.linspace(0.0, 1.2, 300)
    eta_scan   = adaptive_efficiency(E_scan)
    eta_lo     = float(eta_scan[E_scan <= E_THRESHOLD - 0.3].max()) if any(E_scan <= E_THRESHOLD - 0.3) else 0.0
    eta_hi     = float(eta_scan[E_scan >= E_THRESHOLD + 0.3].min())
    awakening  = eta_hi / (eta_lo + 1e-12)
    pred1_pass = awakening >= 2.0

    # --- Prediction 2: Dynamic load balancing ---
    # Measure weight shift when chemical source drops (after t_frac > 0.6)
    early_w = rec_weights[: steps // 2]         # chem available
    late_w  = rec_weights[steps // 2 :]         # chem dropped
    delta_w = float(np.abs(late_w.mean(0) - early_w.mean(0)).max())
    pred2_pass = delta_w >= 0.05

    # --- Prediction 3: Storage buffering ---
    var_in     = float(np.var(rec_E_in))
    var_stored = float(np.var(rec_E_stored))
    smoothing  = var_in / (var_stored + 1e-12)
    pred3_pass = smoothing >= 2.0

    # --- Prediction 4: Adaptive Q vs temperature ---
    T_range   = np.linspace(200.0, 400.0, 100)
    sigma_T   = adaptive_conductivity(T_range)
    R_T       = R1_BASE / (sigma_T * A_TUBE + 1e-12)
    omega0_1  = 2.0 * np.pi * resonant_frequency(L1, C1)
    Q_T       = quality_factor(omega0_1, L1, R_T)
    Q_ratio   = float(Q_T[-1] / (Q_T[0] + 1e-12))   # Q at 400K / Q at 200K
    pred4_pass = Q_ratio >= 2.0

    if verbose:
        # --- Summary statistics ---
        print(f"\n  Energy source statistics (mean over simulation):")
        src_names = ['cosmic', 'EM    ', 'thermal', 'chemical', 'plasma ']
        for i, name in enumerate(src_names):
            mu = rec_sources[:, i].mean()
            w_mu = rec_weights[:, i].mean()
            bar = '#' * int(round(w_mu * 40))
            print(f"    {name}  E_mean={mu:.3f}  w_mean={w_mu:.3f}  {bar}")

        print(f"\n  Storage dynamics:")
        print(f"    E_stored mean = {rec_E_stored.mean():.4f}  "
              f"std = {rec_E_stored.std():.4f}")
        print(f"    E_in     mean = {rec_E_in.mean():.4f}  "
              f"std = {rec_E_in.std():.4f}")
        print(f"    eta      mean = {rec_eta.mean():.4f}  "
              f"range = [{rec_eta.min():.3f}, {rec_eta.max():.3f}]")

        print(f"\n  Efficiency function  (threshold awakening):")
        print(f"    E_threshold = {E_THRESHOLD}  beta = {BETA_EFF}")
        print(f"    eta at E = {E_THRESHOLD-0.3:.1f} (below threshold):  {eta_lo:.4f}")
        print(f"    eta at E = {E_THRESHOLD+0.3:.1f} (above threshold):  {eta_hi:.4f}")
        print(f"    Awakening ratio:  {awakening:.2f}x")

        print(f"\n  Source weight redistribution (early vs late):")
        for i, name in enumerate(src_names):
            print(f"    {name}  early_w={early_w.mean(0)[i]:.3f}  "
                  f"late_w={late_w.mean(0)[i]:.3f}  "
                  f"delta={late_w.mean(0)[i]-early_w.mean(0)[i]:+.3f}")
        print(f"    Max weight shift: {delta_w:.4f}")

        print(f"\n  Buffering analysis:")
        print(f"    Var(E_in)      = {var_in:.5f}")
        print(f"    Var(E_stored)  = {var_stored:.5f}")
        print(f"    Smoothing ratio: {smoothing:.2f}x")

        print(f"\n  Adaptive Q factor  (Type-1 HF tube):")
        print(f"    Q at 200K = {Q_T[0]:.2f}   Q at 400K = {Q_T[-1]:.2f}")
        print(f"    Q ratio (400K / 200K): {Q_ratio:.2f}x")
        print(f"    Target Q > 100:  {'YES' if Q_T.max() > 100 else 'NO'}")

        print(f"\n{'='*64}")
        print("Verification against prototaxites.md predictions")
        print(f"{'='*64}")
        print(f"  Threshold awakening  (>= 2x at threshold):  "
              f"{'PASS' if pred1_pass else 'FAIL'}  ({awakening:.2f}x)")
        print(f"  Dynamic load balance (weight shift > 0.05): "
              f"{'PASS' if pred2_pass else 'FAIL'}  (delta={delta_w:.4f})")
        print(f"  Storage buffering    (smoothing >= 2x):     "
              f"{'PASS' if pred3_pass else 'FAIL'}  ({smoothing:.2f}x)")
        print(f"  Adaptive Q rise      (Q_400K/Q_200K >= 2x): "
              f"{'PASS' if pred4_pass else 'FAIL'}  ({Q_ratio:.2f}x)")
        all_pass = pred1_pass and pred2_pass and pred3_pass and pred4_pass
        print(f"\n  Overall: {'ALL PASS' if all_pass else 'PARTIAL'}")

    return {
        'times':      times,
        'E_in':       rec_E_in,
        'eta':        rec_eta,
        'E_cond':     rec_E_cond,
        'E_stored':   rec_E_stored,
        'weights':    rec_weights,
        'sources':    rec_sources,
        'T_local':    rec_T_local,
        'Q_T':        Q_T,
        'T_range':    T_range,
        'smoothing':  smoothing,
        'Q_ratio':    Q_ratio,
        'awakening':  awakening,
    }


# ---------------------------------------------------------------------------
# Multi-source sensitivity sweep
# ---------------------------------------------------------------------------

def source_sweep(verbose: bool = True) -> dict:
    """
    Vary individual source availability and record how the system adapts.

    Shows: when one source is removed, weights and stored energy compensate.
    Storage.md §10 / prototaxites.md 'Multi-source adaptation' principle.
    """
    if verbose:
        print("\n" + "=" * 64)
        print("Source sweep  (multi-source adaptation, prototaxites.md §Digestive)")
        print("=" * 64)
        print(f"\n  {'source off':>12}  {'E_stored_mean':>13}  "
              f"{'E_stored_std':>12}  {'max_w_shift':>11}")
        print(f"  {'----------':>12}  {'-------------':>13}  "
              f"{'------------':>12}  {'-----------':>11}")

    src_names = ['cosmic', 'EM', 'thermal', 'chemical', 'plasma']
    base  = run(verbose=False)
    sweep = {}

    for off_idx in range(5):
        # Re-run with one source pinned to zero by overriding threshold to inf
        rng_sw = np.random.default_rng(42)
        steps  = int(200.0 / 0.5)
        E_stored = np.ones(N_TYPE3) * 0.3
        E_stored_ts = np.zeros(steps)
        weights_ts  = np.zeros((steps, 5))

        for step in range(steps):
            t = step * 0.5
            E_src = energy_sources(t, 200.0, rng_sw)
            E_src[off_idx] = 0.0           # remove this source
            w = source_weights(E_src)
            weights_ts[step] = w
            E_in  = float((w * E_src).sum())
            eta   = adaptive_efficiency(E_in)
            E_per = eta * E_in / N_TYPE3
            P_met = metabolic_rate(E_stored)
            E_stored = np.clip(E_stored + (E_per - P_met) * 0.5, 0.0, E3_MAX)
            E_stored_ts[step] = float(E_stored.mean())

        mean_s = float(E_stored_ts.mean())
        std_s  = float(E_stored_ts.std())
        w_base = base['weights'].mean(0)
        w_off  = weights_ts.mean(0)
        max_shift = float(np.abs(w_off - w_base).max())

        if verbose:
            print(f"  {src_names[off_idx]:>12}  {mean_s:>13.4f}  "
                  f"{std_s:>12.4f}  {max_shift:>11.4f}")

        sweep[src_names[off_idx]] = {
            'E_stored_mean': mean_s,
            'E_stored_std':  std_s,
            'max_w_shift':   max_shift,
        }

    if verbose:
        # Verify: removing any single source triggers weight redistribution
        all_adapt = all(v['max_w_shift'] > 0.03 for v in sweep.values())
        print(f"\n  All sources trigger redistribution (>0.03): "
              f"{'PASS' if all_adapt else 'FAIL'}")

    return sweep


if __name__ == "__main__":
    # Primary experiment
    results = run(T_sim=200.0, dt=0.5, seed=42)

    # Multi-source sensitivity
    source_sweep()
