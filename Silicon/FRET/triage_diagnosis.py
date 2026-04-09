# STATUS: infrastructure -- fault injection and hierarchical diagnosis
"""
triage_diagnostics.py – Simulated fault injection and hierarchical diagnosis.
"""

import numpy as np
import matplotlib.pyplot as plt
from fret_core import E_FRET, R0

def simulate_measurements(r, R0, F=1.0, noise_level=0.02):
    """
    Generate synthetic observables: tau_DA, E, r_ss.
    r in nm, R0 in nm.
    """
    # True efficiency
    E_true = E_FRET(r, R0)
    # tau_DA: donor lifetime normalized to tau_D = 1
    kF = (R0 / r)**6
    kR = 0.1 * F  # base radiative rate 0.1, modified by F
    knr = 0.05
    tau_DA = 1.0 / (kF + kR + knr)
    # Steady-state anisotropy r_ss: simple model decreases with FRET
    r0 = 0.4  # fundamental anisotropy
    r_ss = r0 * (kR / (kF + kR + knr))
    
    # Add Gaussian noise
    tau_DA += np.random.normal(0, noise_level * tau_DA)
    E_meas = E_true + np.random.normal(0, noise_level)
    r_ss += np.random.normal(0, noise_level * r_ss)
    
    return tau_DA, np.clip(E_meas, 0, 1), r_ss

def triage_decision(tau_DA, E, r_ss, thresholds):
    """
    Decision tree per framework hierarchy.
    thresholds: dict with keys 'tau_high', 'rss_low', 'frad_high', etc.
    Returns diagnosis string.
    """
    # Level 1: Geometry check
    if tau_DA > thresholds['tau_high'] and r_ss < thresholds['rss_low']:
        return "Geometry failure (r drift or κ² drop)"
    # Level 2: Rate budget (we need f_rad, compute from tau_DA and E)
    k_total = 1.0 / tau_DA
    kF_est = k_total * E
    f_rad_est = (k_total - kF_est - 0.05) / k_total  # approximate knr=0.05
    if f_rad_est > thresholds['frad_high']:
        return "Radiative loss high (LDOS detune)"
    # Level 3: Servo (need servo error, not available here; use proxy)
    # For demo, assume if tau_DA within band but E low, it's spectral
    if E < thresholds['E_low']:
        return "Spectral overlap drift (J)"
    # Level 4: Triplet reservoir (low E despite all else)
    return "Possible triplet loss (check reservoir)"

# Demonstration with injected faults
if __name__ == "__main__":
    np.random.seed(42)
    R0_nom = 5.0  # nm
    r_nom = 3.0
    F_nom = 0.1
    thresholds = {'tau_high': 0.8, 'rss_low': 0.05, 'frad_high': 0.2, 'E_low': 0.7}
    
    print("Simulating normal condition:")
    tau, E, rss = simulate_measurements(r_nom, R0_nom, F_nom)
    diag = triage_decision(tau, E, rss, thresholds)
    print(f"tau_DA={tau:.2f}, E={E:.2f}, r_ss={rss:.3f} -> {diag}")
    
    print("\nFault 1: increased r to 4.5 nm")
    tau, E, rss = simulate_measurements(4.5, R0_nom, F_nom)
    diag = triage_decision(tau, E, rss, thresholds)
    print(f"tau_DA={tau:.2f}, E={E:.2f}, r_ss={rss:.3f} -> {diag}")
    
    print("\nFault 2: F increased to 0.8 (DBR detune)")
    tau, E, rss = simulate_measurements(r_nom, R0_nom, F=0.8)
    diag = triage_decision(tau, E, rss, thresholds)
    print(f"tau_DA={tau:.2f}, E={E:.2f}, r_ss={rss:.3f} -> {diag}")
