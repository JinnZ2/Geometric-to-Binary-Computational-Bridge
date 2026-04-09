"""
geometry_lock.py – Modeling distance distribution and orientation factor under a potential.
"""

import numpy as np
from scipy.stats import boltzmann
import matplotlib.pyplot as plt
from fret_core import R0, E_FRET

def U_linker(r, r_eq, k_spring, r_hard_min=0.0):
    """
    Potential energy (in kT) for a linker with harmonic spring and hard-wall repulsion.
    """
    U = 0.5 * k_spring * (r - r_eq)**2
    if r < r_hard_min:
        U += 1e6 * (r_hard_min - r)**2  # steep penalty
    return U

def r_distribution(r_eq, k_spring, T=298.0, r_hard_min=0.0, r_range=(0, 10), num=1000):
    """
    Generate probability density of donor-acceptor distance using Boltzmann factor.
    Returns r_grid and pdf.
    """
    r_grid = np.linspace(r_range[0], r_range[1], num)
    U_vals = np.array([U_linker(ri, r_eq, k_spring, r_hard_min) for ri in r_grid])
    # Boltzmann factor (kT = 1 for energy in kT units)
    pdf = np.exp(-U_vals)
    pdf /= np.trapz(pdf, r_grid)
    return r_grid, pdf

def effective_kappa2(phi0, sigma_phi, T=298.0, U_barrier=5.0):
    """
    Simple model: orientation factor averaged over angular fluctuations.
    Assumes a harmonic angular trap with barrier U_barrier (in kT).
    sigma_phi is the rms angular deviation (radians).
    """
    # For dipoles constrained near parallel (θ small), κ² ≈ 4 cos²θ.
    # We average cos²θ over Gaussian θ distribution with width sigma_phi.
    # Effective kappa2 = 4 * <cos²θ>.
    # <cos²θ> = (1/2)(1 + exp(-2 sigma_phi²) cos(2φ0)) but for φ0=0:
    # <cos²θ> ≈ 1 - sigma_phi² (for small sigma)
    # More accurately: use numerical integration.
    from scipy.integrate import quad
    
    def integrand(theta):
        # Boltzmann weight exp(-U(theta)/kT) with U = (1/2) k_theta theta²
        k_theta = U_barrier / (0.1**2)  # set barrier to correspond to 0.1 rad confinement
        return np.exp(-0.5 * k_theta * theta**2) * (np.cos(theta)**2) * np.sin(theta)
    
    norm = quad(lambda t: np.exp(-0.5 * k_theta * t**2) * np.sin(t), 0, np.pi)[0]
    avg_cos2 = quad(integrand, 0, np.pi)[0] / norm
    return 4.0 * avg_cos2

# Demonstration
if __name__ == "__main__":
    r_eq = 3.0  # nm
    k_spring = 50.0  # kT / nm² (stiff)
    r_vals, pdf = r_distribution(r_eq, k_spring, r_hard_min=1.8)
    
    plt.figure()
    plt.plot(r_vals, pdf)
    plt.xlabel('r (nm)')
    plt.ylabel('P(r)')
    plt.title('Donor-Acceptor Distance Distribution')
    plt.show()
    
    # Compute CV(r)
    mean_r = np.trapz(r_vals * pdf, r_vals)
    var_r = np.trapz((r_vals - mean_r)**2 * pdf, r_vals)
    cv = np.sqrt(var_r) / mean_r
    print(f"Mean r = {mean_r:.3f} nm, CV = {cv*100:.1f}%")
    
    # Orientation lock
    kappa2_mean = effective_kappa2(phi0=0, sigma_phi=0.05)  # 0.05 rad ~ 3 deg
    print(f"Effective <κ²> = {kappa2_mean:.2f}")
