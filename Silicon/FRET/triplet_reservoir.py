# STATUS: infrastructure -- kinetic triplet state model with rISC
"""
triplet_reservoir.py – Kinetic model including triplet states and rISC.
Computes effective FRET efficiency boost.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

def triplet_kinetics(t, y, kF, kR, knrS, kISC, krISC, knrT, kP):
    """
    Rate equations for donor singlet and triplet populations.
    y = [S1, T1]
    """
    S1, T1 = y
    dS1 = - (kF + kR + knrS + kISC) * S1 + krISC * T1
    dT1 = kISC * S1 - (krISC + knrT + kP) * T1
    return [dS1, dT1]

def effective_fret_efficiency(kF, kR, knrS, kISC, krISC, knrT, kP, excitation_pulse=None):
    """
    Compute steady-state FRET efficiency including triplet reservoir.
    If excitation_pulse is a function of time, we can integrate; 
    for steady-state, we solve equilibrium.
    """
    # Steady-state: dS1/dt = dT1/dt = 0, plus normalization S1 + T1 = 1 (in excited manifold)
    # Actually, we can compute fraction of excitation that leads to FRET:
    # f_FRET = kF * S1_ss / (kF + kR + knrS) for standard case.
    # With triplets, the denominator changes.
    # Solve linear system:
    # (kF+kR+knrS+kISC) * S1 - krISC * T1 = 1 (excitation rate set to 1)
    # -kISC * S1 + (krISC+knrT+kP) * T1 = 0
    A = np.array([[kF + kR + knrS + kISC, -krISC],
                  [-kISC, krISC + knrT + kP]])
    b = np.array([1.0, 0.0])
    S1_ss, T1_ss = np.linalg.solve(A, b)
    # Total excitation flux = 1, FRET flux = kF * S1_ss
    return kF * S1_ss

def efficiency_boost(kF, kR, knrS, rho, return_ratio):
    """
    Convenience function using parameters ρ and b/(b+c).
    ρ = kISC / (kISC + knrS)  (fraction of non-radiative loss diverted to ISC)
    return_ratio = krISC / (krISC + knrT + kP)
    """
    # Derive rates from parameters
    # knrS given, then kISC = rho * knrS / (1 - rho)  (since rho = kISC/(kISC+knrS))
    if rho >= 1.0: rho = 0.99
    kISC = rho * knrS / (1 - rho)
    # For return ratio b = krISC, c = knrT+kP
    # We can set c = 1.0, then krISC = return_ratio * c / (1 - return_ratio) if return_ratio < 1
    c = 1.0
    krISC = return_ratio * c / (1 - return_ratio) if return_ratio < 0.99 else 99.0
    knrT_kP = c
    return effective_fret_efficiency(kF, kR, knrS, kISC, krISC, knrT_kP, 0.0)

# Demo
if __name__ == "__main__":
    # Base rates (ns^-1)
    kF = 1.0
    kR = 0.5
    knrS = 0.3
    
    rho_vals = np.linspace(0, 0.9, 20)
    return_ratio_vals = np.linspace(0.5, 0.95, 20)
    
    boost_map = np.zeros((len(rho_vals), len(return_ratio_vals)))
    for i, rho in enumerate(rho_vals):
        for j, rr in enumerate(return_ratio_vals):
            boost_map[i,j] = efficiency_boost(kF, kR, knrS, rho, rr)
    
    # Reference efficiency without triplet reservoir
    E_ref = kF / (kF + kR + knrS)
    
    plt.figure()
    plt.contourf(return_ratio_vals, rho_vals, boost_map / E_ref - 1, levels=20)
    plt.colorbar(label='Relative efficiency boost')
    plt.xlabel('Return ratio b/(b+c)')
    plt.ylabel('Diversion fraction ρ')
    plt.title('Triplet Reservoir Enhancement')
    plt.show()
