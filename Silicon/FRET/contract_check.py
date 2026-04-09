"""
contract_check.py – Simulate FRET cascade performance over time with drift.
Checks against the output contract specifications.
"""

import numpy as np
from scipy.integrate import solve_ivp
from fret_core import R0, k_FRET, E_FRET
from geometry_lock import effective_kappa2
from photonic_branching import LDOS_factor
from triplet_reservoir import effective_fret_efficiency

def simulate_system(t_span, dt_eval, params, drift_rates, servo_params=None):
    """
    Simulate the FRET system over time, including parameter drifts and servo correction.

    Returns
    -------
    dict with time series of observables: E_cas, f_rad, CV_tau, J_error, etc.
    """
    t_eval = np.arange(t_span[0], t_span[1], dt_eval)
    n_steps = len(t_eval)

    # Unpack initial parameters
    r0 = params['r']
    kappa2_0 = params['kappa2']
    J0 = params['J']
    F0 = params['F']
    tau_D = params['tau_D']
    n = params['n']
    Phi_D = params['Phi_D']
    rho = params.get('rho', 0.0)
    return_ratio = params.get('return_ratio', 0.0)

    # Drift rates (linear)
    gamma_r = drift_rates.get('r', 0.0)
    gamma_kappa2 = drift_rates.get('kappa2', 0.0)
    gamma_J = drift_rates.get('J', 0.0)
    gamma_F = drift_rates.get('F', 0.0)

    # Servo parameters (PI controller for J)
    if servo_params:
        Kp = servo_params.get('Kp', 0.0)
        Ki = servo_params.get('Ki', 0.0)
        J_target = J0
        integral = 0.0
        max_stark = servo_params.get('max_stark', 5.0)  # nm equivalent
    else:
        Kp = Ki = 0.0
        J_target = J0
        max_stark = 0.0

    # Initialize arrays
    R0_vals = np.zeros(n_steps)
    E_vals = np.zeros(n_steps)
    f_rad_vals = np.zeros(n_steps)
    tau_DA_vals = np.zeros(n_steps)
    J_vals = np.zeros(n_steps)
    stark_shift_vals = np.zeros(n_steps)

    # Current values
    r = r0
    kappa2 = kappa2_0
    J = J0
    F = F0
    stark = 0.0

    for i, t in enumerate(t_eval):
        # Apply drift (linear)
        r_drift = r0 + gamma_r * t
        kappa2_drift = kappa2_0 + gamma_kappa2 * t
        J_drift = J0 + gamma_J * t
        F_drift = F0 + gamma_F * t

        # Servo correction on J (Stark shift)
        if servo_params:
            error = J_target - J_drift
            integral += error * dt_eval
            stark = Kp * error + Ki * integral
            stark = np.clip(stark, -max_stark, max_stark)
            # Stark shift changes J linearly (approx)
            J_eff = J_drift * (1 + 0.05 * stark)  # 5% per nm shift, placeholder
        else:
            J_eff = J_drift
            stark = 0.0

        # Compute R0 with current parameters
        R0_current = R0(kappa2_drift, Phi_D, n, J_eff)

        # FRET rate and efficiency (single hop)
        kF = k_FRET(r_drift, R0_current, tau_D)
        kR = 0.2 * F_drift  # base radiative rate
        knr = 0.1
        k_total = kF + kR + knr

        # Two-hop cascade efficiency (simplified: E_cas = E1 * E2)
        E1 = E_FRET(r_drift, R0_current)
        E2 = E1  # assume symmetric second hop
        E_cas = E1 * E2

        # If triplet reservoir active
        if rho > 0:
            E1_eff = effective_fret_efficiency(kF, kR, knr, rho, return_ratio)
            E_cas = E1_eff * E1_eff
        else:
            E1_eff = E1

        # Radiative fraction
        f_rad = kR / k_total

        # tau_DA
        tau_DA = 1.0 / k_total

        # Store
        R0_vals[i] = R0_current
        E_vals[i] = E_cas
        f_rad_vals[i] = f_rad
        tau_DA_vals[i] = tau_DA
        J_vals[i] = J_eff
        stark_shift_vals[i] = stark

    # Compute CV of tau_DA over last 10% of simulation as stability metric
    window = max(1, n_steps // 10)
    tau_recent = tau_DA_vals[-window:]
    cv_tau = np.std(tau_recent) / np.mean(tau_recent)

    return {
        'time': t_eval,
        'E_cas': E_vals,
        'f_rad': f_rad_vals,
        'tau_DA': tau_DA_vals,
        'J': J_vals,
        'stark': stark_shift_vals,
        'CV_tau': cv_tau,
        'final_E_cas': E_vals[-1],
        'final_f_rad': f_rad_vals[-1]
    }

def check_contract(results, contract):
    """Evaluate whether contract metrics are satisfied."""
    checks = {
        'E_cas': results['final_E_cas'] >= contract['E_cas_min'],
        'f_rad': results['final_f_rad'] <= contract['f_rad_max'],
        'CV_tau': results['CV_tau'] <= contract['CV_tau_max']
    }
    all_pass = all(checks.values())
    return checks, all_pass
