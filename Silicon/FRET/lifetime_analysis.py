"""
lifetime_analysis.py – Compute τ_acceptable from variance budget equation.
"""

import numpy as np
from scipy.optimize import root_scalar

def tau_acceptable(sensitivities, sigma0, gamma_eff, servo_gain=0.0, target_cv=0.015):
    """
    Compute time t at which CV(τ_DA) exceeds target_cv.

    Parameters
    ----------
    sensitivities : dict
        Partial derivatives ∂lnτ/∂x for x in {r, kappa2, J, F, ...}
    sigma0 : dict
        Initial standard deviations for each parameter.
    gamma_eff : dict
        Drift rates (units of parameter per unit time). For J, can be reduced by servo.
    servo_gain : float, optional
        Fractional reduction in effective drift for parameters under servo (e.g., J).
        Effective drift = gamma * (1 - servo_gain).
    target_cv : float, default 0.015 (1.5%)

    Returns
    -------
    float
        τ_acceptable (time units) or np.inf if never exceeded.
    """
    def variance_ratio(t):
        total = 0.0
        for param in sensitivities:
            s = sensitivities[param]
            sigma_init = sigma0.get(param, 0.0)
            gamma = gamma_eff.get(param, 0.0)
            # Apply servo reduction to drift (for spectral parameters)
            if param == 'J':
                gamma = gamma * (1 - servo_gain)
            total += s**2 * (sigma_init**2 + (gamma * t)**2)
        return total

    # Check if initial CV already exceeds target
    if variance_ratio(0) > target_cv**2:
        return 0.0

    # Find t where variance_ratio(t) = target_cv**2
    # Use root finding; assume monotonic increase
    try:
        sol = root_scalar(
            lambda t: variance_ratio(t) - target_cv**2,
            bracket=[0, 1e6],
            method='bisect'
        )
        return sol.root if sol.converged else np.inf
    except ValueError:
        return np.inf

# Example usage for documentation
if __name__ == "__main__":
    # Sensitivities from FRET equations
    # τ_DA ≈ 1 / (k_F + k_rad + k_nr)
    # For typical values near R0, ∂lnτ/∂r ≈ -6 * (r/R0)^6 / (1 + (r/R0)^6) * (1/r)
    # Here we use approximate numbers
    sens = {
        'r': -1.2,          # per nm
        'kappa2': -0.15,    # per unit
        'J': -0.15,         # per relative change
        'F': 0.05           # per unit
    }
    sigma0 = {
        'r': 0.05,          # nm
        'kappa2': 0.1,
        'J': 0.02,          # relative
        'F': 0.01
    }
    gamma = {
        'r': 0.0001,        # nm / hour (linker creep)
        'kappa2': 0.0005,   # / hour (orientation relaxation)
        'J': 0.001,         # relative / hour (aging)
        'F': 0.0002         # / hour (index drift)
    }

    # Without servo on J
    t_accept_no_servo = tau_acceptable(sens, sigma0, gamma, servo_gain=0.0)
    print(f"Without servo: τ_acceptable = {t_accept_no_servo:.1f} hours")

    # With servo reducing J drift by 80%
    t_accept_servo = tau_acceptable(sens, sigma0, gamma, servo_gain=0.8)
    print(f"With servo (80% reduction on J): τ_acceptable = {t_accept_servo:.1f} hours")
