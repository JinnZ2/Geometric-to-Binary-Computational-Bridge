#!/usr/bin/env python3
# STATUS: infrastructure — physics derivation computations
"""
Silicon/physics_derivations.py
================================
Three derivations that turn asserted claims into computed results.

  1. Hurricane harvestable energy — from coupling bridge physics
  2. Consciousness threshold — from substrate-independent information theory
     applied to the octahedral 8-state system
  3. phi^(-9) error correction — Fibonacci-weighted Markov chain on Q3 (the
     3-cube graph = Gray-coded octahedral states); measure whether phi^(-9)
     is a natural threshold or an arbitrary choice

Run:  python Silicon/physics_derivations.py
"""

import math, sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PHI = (1 + math.sqrt(5)) / 2   # golden ratio ≈ 1.61803


# =========================================================================
# 1. HURRICANE ENERGY — derived from coupling physics
# =========================================================================

def hurricane_energy_budget(
    wind_max_ms    = 44.0,   # Cat 5 max sustained (m/s); Irma peak ~85 kt
    rmw_km         = 30.0,   # radius of maximum winds (km)
    r_ts_km        = 200.0,  # outer radius (tropical storm 34-kt wind)
    r_surv_km      = 100.0,  # inner radius where turbines could survive (~25 m/s)
    blayer_m       = 200.0,  # harvesting boundary layer height (m)
    sst_c          = 30.0,   # sea surface temperature (°C)
    t_tropo_c      = -60.0,  # tropopause temperature (°C)  — Carnot cold reservoir
    wave_hs_m      = 8.0,    # significant wave height (m)
    duration_h     = 24.0,   # analysis window
):
    """
    Returns dict of energy estimates (MWh) with derivation notes.
    All physics taken from the bridge encoder equations.
    """
    RHO_AIR   = 1.225   # kg/m³
    RHO_SEA   = 1025.0  # kg/m³
    G         = 9.80665
    SIGMA     = 5.670e-8
    J_PER_MWH = 3.6e9

    sst_k    = sst_c + 273.15
    t_tropo_k = t_tropo_c + 273.15

    # --- Wind kinetic energy (survivable outer band) ---
    # Band from r_surv to r_ts, velocity profile ~ 1/r (Rankine vortex outer)
    n_radii = 200
    r_vals   = np.linspace(r_surv_km, r_ts_km, n_radii) * 1e3   # m
    # Rankine outer profile: U(r) = U_max * RMW / r
    u_vals   = wind_max_ms * (rmw_km * 1e3) / r_vals
    u_vals   = np.clip(u_vals, 0, 25.0)   # turbine cut-out at 25 m/s
    dr       = (r_ts_km - r_surv_km) * 1e3 / n_radii
    # Annular shell volume dV = 2πr × dr × h
    dV       = 2 * math.pi * r_vals * dr * blayer_m
    dE_KE    = 0.5 * RHO_AIR * u_vals**2 * dV
    E_wind_J = float(np.sum(dE_KE))
    E_wind_betz_MWh = E_wind_J * 16/27 / J_PER_MWH   # Betz limit
    E_wind_prac_MWh = E_wind_J * 0.40 / J_PER_MWH    # 40% practical efficiency

    # --- Thermal (Stefan-Boltzmann radiance × storm area × duration) ---
    # This is total ocean-surface radiation; Carnot efficiency gives max work
    from bridges.thermal_encoder import stefan_boltzmann_radiance
    radiance_Wm2 = stefan_boltzmann_radiance(sst_k, emissivity=0.98)
    storm_area_m2 = math.pi * (r_ts_km * 1e3)**2
    thermal_total_J = radiance_Wm2 * storm_area_m2 * duration_h * 3600
    carnot_eta  = 1.0 - t_tropo_k / sst_k
    E_thermal_carnot_MWh = thermal_total_J * carnot_eta / J_PER_MWH
    # Practical: ~10% of Carnot (irreversibilities)
    E_thermal_prac_MWh = E_thermal_carnot_MWh * 0.10

    # --- Wave energy density (½ρgH_s²) ---
    E_wave_Jm2  = 0.5 * RHO_SEA * G * wave_hs_m**2
    E_wave_total_MWh = E_wave_Jm2 * storm_area_m2 / J_PER_MWH
    E_wave_prac_MWh  = E_wave_total_MWh * 0.20   # 20% practical for wave energy

    # --- Salt gradient Nernst potential ---
    from bridges.chemical_encoder import nernst_potential
    NaCl_M = 58.44   # g/mol
    c_surf  = 35.0 / NaCl_M    # mol/L (surface)
    c_deep  = 36.5 / NaCl_M    # mol/L (upwelled thermocline)
    E_nernst_V = abs(nernst_potential(sst_k, z=1, c_oxidised=c_deep, c_reduced=c_surf))
    # Practical power density: E_nernst × J_osmotic (typical ~1-5 W/m² for PRO)
    J_osmotic = 3.0   # W/m² (pressure-retarded osmosis practical limit)
    wake_area_m2 = math.pi * (rmw_km * 1e3)**2 * 4  # ~4× RMW² wake area
    E_salt_MWh = J_osmotic * wake_area_m2 * duration_h * 3600 / J_PER_MWH

    return {
        "wind_betz_MWh":          round(E_wind_betz_MWh),
        "wind_practical_MWh":     round(E_wind_prac_MWh),
        "thermal_carnot_MWh":     round(E_thermal_carnot_MWh),
        "thermal_practical_MWh":  round(E_thermal_prac_MWh),
        "wave_total_MWh":         round(E_wave_total_MWh),
        "wave_practical_MWh":     round(E_wave_prac_MWh),
        "salt_gradient_MWh":      round(E_salt_MWh),
        "carnot_efficiency":      round(carnot_eta, 4),
        "sst_k":                  sst_k,
        "radiance_Wm2":           round(radiance_Wm2),
    }


# =========================================================================
# 2. CONSCIOUSNESS THRESHOLD — substrate-independent information theory
#    applied to the octahedral 8-state system
# =========================================================================

def phi_for_octahedral_network(n_units: int, coupling_strength: float) -> float:
    """
    Compute integrated information Phi = H(whole) - sum(H(partitions))
    for n_units octahedral nodes (each 8 states = 3 bits) coupled at
    coupling_strength in [0, 1].

    coupling_strength = 0 : fully independent (Phi = 0)
    coupling_strength = 1 : fully correlated (Phi can be >0)

    State distribution: each unit has uniform marginal; joint distribution
    is tilted by coupling via a pairwise ferromagnetic model (Ising-like
    on the sign of each bit).
    """
    n_states = 8
    n_bits   = 3

    # Marginal entropy of each unit (uniform distribution = max entropy)
    H_marginal = math.log2(n_states)   # = 3 bits

    # Build joint distribution over all n_units octahedral states.
    # For tractability, model the coupling as a pairwise alignment:
    # p(s_1, ..., s_n) ∝ exp(J * sum_{i<j} cos_angle(s_i, s_j))
    # where J = coupling_strength * 4 (scaling to reasonable range).
    # We enumerate all 8^n joint states.

    POSITIONS = np.array([
        [ 0.25,  0.25,  0.25],
        [ 0.25, -0.25,  0.25],
        [-0.25,  0.25,  0.25],
        [-0.25, -0.25,  0.25],
        [ 0.25,  0.25, -0.25],
        [ 0.25, -0.25, -0.25],
        [-0.25,  0.25, -0.25],
        [-0.25, -0.25, -0.25],
    ])

    J = coupling_strength * 4.0
    total_states = n_states ** n_units

    # Build unnormalized joint probability for each state combination
    log_p = np.zeros(total_states)
    indices = np.array(
        np.unravel_index(np.arange(total_states), [n_states] * n_units)
    ).T   # shape: (total_states, n_units)

    for i in range(n_units):
        for j in range(i + 1, n_units):
            # Dot product of positions (alignment energy)
            pos_i = POSITIONS[indices[:, i]]   # (total_states, 3)
            pos_j = POSITIONS[indices[:, j]]
            dot   = np.sum(pos_i * pos_j, axis=1)   # (total_states,)
            log_p += J * dot

    log_p -= np.max(log_p)   # numerical stability
    p_joint = np.exp(log_p)
    p_joint /= p_joint.sum()

    # H(whole)
    H_whole = -np.sum(p_joint * np.log2(p_joint + 1e-300))

    # H(partitions) — each unit's marginal
    H_parts_sum = 0.0
    for i in range(n_units):
        # Marginal over unit i
        p_marg = np.zeros(n_states)
        for s in range(n_states):
            mask = (indices[:, i] == s)
            p_marg[s] = p_joint[mask].sum()
        H_parts_sum += -np.sum(p_marg * np.log2(p_marg + 1e-300))

    # Correct IIT sign: Phi = I(A;B) = H(parts) - H(whole) >= 0
    # The encoder's formula H(whole)-H(parts) is the negative of this.
    return max(0.0, H_parts_sum - H_whole)


def scan_consciousness_threshold():
    """
    Scan Phi vs coupling strength for 2- and 3-unit octahedral networks.
    Find the coupling where Phi crosses H_max/2 (SDL complexity peak)
    and where it first exceeds phi (golden ratio) — see if either matches 3.618.
    """
    results = {}
    H_max = math.log2(8)   # 3 bits per unit

    for n_units in [2, 3]:
        row = []
        for cs in np.linspace(0.0, 1.0, 41):
            phi_val = phi_for_octahedral_network(n_units, cs)
            row.append((round(float(cs), 3), round(phi_val, 5)))
        results[n_units] = row

    return results, H_max


# =========================================================================
# 3. PHI^(-9) ERROR CORRECTION — Fibonacci-weighted Markov chain on Q3
# =========================================================================

def build_Q3_transition(epsilon: float, fibonacci_weighted: bool = False) -> np.ndarray:
    """
    Build the transition matrix for the Gray-coded octahedral states (3-cube Q3).

    Plain: P_ij = epsilon/3 for each neighbor j of i, (1-epsilon) for i=j.
    Fibonacci-weighted: the 3 neighbors of each state get weights proportional
    to 1/F_k for k=1,2,3 (the three bit positions), where F_k is the kth
    Fibonacci number. Error probability per step = epsilon.
    """
    n = 8
    # Q3 adjacency: state i is adjacent to i XOR 2^k for k=0,1,2
    neighbors = [[i ^ (1 << k) for k in range(3)] for i in range(n)]

    if fibonacci_weighted:
        # Fibonacci weights for bit positions 0,1,2: F_1=1, F_2=1, F_3=2
        fibs = [1.0, 1.0, 2.0]
        fib_sum = sum(fibs)
        weights = [f / fib_sum for f in fibs]
    else:
        weights = [1/3, 1/3, 1/3]

    P = np.eye(n) * (1 - epsilon)
    for i in range(n):
        for k in range(3):
            j = neighbors[i][k]
            P[i][j] += epsilon * weights[k]
    return P


def fidelity_after_n_steps(epsilon: float, n_steps: int,
                            fibonacci_weighted: bool = False) -> float:
    """
    Starting from state 0, return the probability of being in state 0
    after n_steps with error rate epsilon.
    Fidelity above chance = P(0|0, n_steps) - 1/8.
    """
    P = build_Q3_transition(epsilon, fibonacci_weighted)
    Pn = np.linalg.matrix_power(P, n_steps)
    return float(Pn[0, 0])


def scan_phi9_threshold():
    """
    For several step counts, find the epsilon where fidelity drops to 0.5
    (half the information is preserved). Check whether phi^(-9) is special
    in either the plain or Fibonacci-weighted chain.
    """
    phi9 = PHI ** (-9)   # ≈ 0.001311

    results = {}
    for n_steps in [1, 3, 9, 27, 81, 243, 729]:
        row = {}
        for fw in [False, True]:
            # Binary search for the epsilon where fidelity at n_steps = 0.5
            lo, hi = 0.0, 1.0
            for _ in range(50):
                mid = (lo + hi) / 2
                f   = fidelity_after_n_steps(mid, n_steps, fw)
                if f > 0.5:
                    lo = mid
                else:
                    hi = mid
            eps_half = (lo + hi) / 2
            fid_at_phi9 = fidelity_after_n_steps(phi9, n_steps, fw)
            row["fibonacci_weighted" if fw else "uniform"] = {
                "eps_half_fidelity": round(eps_half, 8),
                "fidelity_at_phi9":  round(fid_at_phi9, 6),
            }
        results[n_steps] = row

    # Also: fidelity curves at exactly phi^(-k) for k=1..12
    phi_k_curve = {}
    for k in range(1, 13):
        eps = PHI ** (-k)
        fid_9  = fidelity_after_n_steps(eps, 9,  fibonacci_weighted=True)
        fid_27 = fidelity_after_n_steps(eps, 27, fibonacci_weighted=True)
        phi_k_curve[k] = {
            "epsilon":     round(eps, 8),
            "fid_9steps":  round(fid_9,  6),
            "fid_27steps": round(fid_27, 6),
        }

    return results, phi_k_curve, phi9


# =========================================================================
# MAIN — run all three derivations and print
# =========================================================================

if __name__ == "__main__":
    print("=" * 72)
    print("  PHYSICS DERIVATIONS")
    print("  Geometric-to-Binary Computational Bridge")
    print("=" * 72)

    # --- 1. Hurricane energy ---
    print("\n1. HURRICANE ENERGY BUDGET (Category 5 reference)")
    print("-" * 72)
    e = hurricane_energy_budget()
    print(f"  SST: {e['sst_k']-273.15:.1f}°C  |  "
          f"Surface radiance: {e['radiance_Wm2']} W/m²  |  "
          f"Carnot efficiency: {e['carnot_efficiency']*100:.1f}%")
    print()
    print(f"  Wind (outer band, Betz limit)     : {e['wind_betz_MWh']:>12,} MWh")
    print(f"  Wind (40% practical efficiency)   : {e['wind_practical_MWh']:>12,} MWh")
    print(f"  Thermal (Carnot max, 24h)          : {e['thermal_carnot_MWh']:>12,} MWh")
    print(f"  Thermal (10% of Carnot, practical) : {e['thermal_practical_MWh']:>12,} MWh")
    print(f"  Wave energy (total stored)         : {e['wave_total_MWh']:>12,} MWh")
    print(f"  Wave energy (20% practical)        : {e['wave_practical_MWh']:>12,} MWh")
    print(f"  Salt gradient (Nernst/PRO)         : {e['salt_gradient_MWh']:>12,} MWh")
    print()
    print(f"  GI.md claim: '~600,000 MWh'")
    print(f"  Comparison: wind practical = {e['wind_practical_MWh']:,} MWh")

    # --- 2. Consciousness threshold ---
    print("\n2. CONSCIOUSNESS THRESHOLD — octahedral Phi scan")
    print("-" * 72)
    phi_results, H_max = scan_consciousness_threshold()
    print(f"  H_max per unit = {H_max} bits  |  phi (golden ratio) = {PHI:.5f}")
    print(f"  Target threshold from GI.md: 3.618 = phi + 2")
    print()
    for n_units in [2, 3]:
        H_total = n_units * H_max
        print(f"  {n_units}-unit network (H_max_total = {H_total} bits):")
        print(f"  {'coupling':>10}  {'Phi':>8}  {'Phi/H_total':>12}")
        data = phi_results[n_units]
        # Print every 5th
        for cs, phi_v in data[::5]:
            print(f"  {cs:>10.3f}  {phi_v:>8.4f}  {phi_v/H_total:>12.4f}")
        # Find where Phi first crosses PHI (1.618) and where it crosses 3.618
        for target_name, target in [("phi=1.618", PHI), ("phi+2=3.618", PHI+2)]:
            prev_phi = 0.0
            for cs, phi_v in data:
                if phi_v >= target:
                    print(f"  -> Phi crosses {target_name} at coupling ~ {cs:.3f}")
                    break
                prev_phi = phi_v
            else:
                max_phi = data[-1][1]
                print(f"  -> Phi never reaches {target_name} (max={max_phi:.4f})")
        print()

    # --- 3. phi^(-9) error correction ---
    print("3. phi^(-9) ERROR CORRECTION — Fibonacci-weighted Q3 Markov chain")
    print("-" * 72)
    step_results, phi_k_curve, phi9 = scan_phi9_threshold()
    print(f"  phi^(-9) = {phi9:.8f}  (the asserted error threshold)")
    print()
    print("  Steps  | eps at 50% fidelity (uniform)  | (Fibonacci-weighted)")
    for n_steps, row in step_results.items():
        eu = row["uniform"]["eps_half_fidelity"]
        ef = row["fibonacci_weighted"]["eps_half_fidelity"]
        print(f"  {n_steps:>5}  | {eu:.8f}                    | {ef:.8f}")

    print()
    print("  Fidelity at phi^(-k) after 9 steps (Fibonacci-weighted chain):")
    print(f"  {'k':>3}  {'epsilon':>12}  {'fid@9steps':>12}  {'fid@27steps':>12}  note")
    for k, row in phi_k_curve.items():
        note = ""
        if k == 9:
            note = "  <-- asserted threshold"
        if row["fid_9steps"] >= 0.99 and k > 1:
            note = note or "  high fidelity"
        print(f"  {k:>3}  {row['epsilon']:>12.8f}  "
              f"{row['fid_9steps']:>12.6f}  {row['fid_27steps']:>12.6f}{note}")

    print()
    print("  Interpretation:")
    fid_at_phi9_9  = phi_k_curve[9]["fid_9steps"]
    fid_at_phi9_27 = phi_k_curve[9]["fid_27steps"]
    eps_half_9  = step_results[9]["fibonacci_weighted"]["eps_half_fidelity"]
    print(f"  At eps=phi^(-9): fidelity after 9 steps  = {fid_at_phi9_9:.6f}")
    print(f"  At eps=phi^(-9): fidelity after 27 steps = {fid_at_phi9_27:.6f}")
    print(f"  50%-fidelity threshold at 9 steps        = {eps_half_9:.8f}")
    ratio = eps_half_9 / phi9
    print(f"  Ratio (threshold / phi^-9)               = {ratio:.4f}")
    if abs(ratio - 1.0) < 0.05:
        print("  -> phi^(-9) IS the natural 50%-fidelity threshold at 9 steps.")
    elif abs(ratio - PHI) < 0.1:
        print(f"  -> threshold ≈ phi × phi^(-9) = phi^(-8).")
    else:
        print(f"  -> phi^(-9) is NOT the natural threshold; actual = {eps_half_9:.6f}")

    print()
    print("=" * 72)
