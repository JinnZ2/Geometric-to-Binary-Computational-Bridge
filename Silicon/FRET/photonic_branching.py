# STATUS: infrastructure -- DBR reflectance and radiative rate modification
"""
photonic_branching.py – Transfer matrix calculation for 1D photonic crystal.
Determines radiative rate modification factor F.
"""

import numpy as np
import matplotlib.pyplot as plt

def transfer_matrix_layer(n, d, lam, theta=0):
    """
    Transfer matrix for a single layer at wavelength lam (vacuum).
    theta is incidence angle in radians.
    Returns 2x2 matrix.
    """
    # Snell's law for effective index
    n_eff = n * np.cos(theta)
    phi = 2 * np.pi * n_eff * d / lam
    M = np.array([[np.cos(phi), 1j * np.sin(phi) / n_eff],
                  [1j * n_eff * np.sin(phi), np.cos(phi)]], dtype=complex)
    return M

def dbr_reflectance(wavelengths, n_low, n_high, d_low, d_high, N_pairs, n_sub=1.5, n_sup=1.0, theta=0):
    """
    Compute reflectance spectrum of a DBR stack.
    Returns array of reflectance values.
    """
    R = np.zeros_like(wavelengths)
    for i, lam in enumerate(wavelengths):
        # Build total matrix starting from substrate
        M_total = np.eye(2, dtype=complex)
        for _ in range(N_pairs):
            M_total = transfer_matrix_layer(n_low, d_low, lam, theta) @ M_total
            M_total = transfer_matrix_layer(n_high, d_high, lam, theta) @ M_total
        # From superstrate to substrate
        r = (M_total[0,0] * n_sup - M_total[1,1] * n_sub + 1j*(n_sup*n_sub*M_total[0,1] - M_total[1,0])) / \
            (M_total[0,0] * n_sup + M_total[1,1] * n_sub + 1j*(n_sup*n_sub*M_total[0,1] + M_total[1,0]))
        R[i] = np.abs(r)**2
    return R

def LDOS_factor(R, position_in_cavity=0.5):
    """
    Simple model: F = 1 - η * R, where η depends on position.
    For a dipole at center of a defect layer, η ≈ 1.
    More accurate: use Purcell formula with cavity parameters.
    Here we approximate F = 1 - R (suppression inside stop-band).
    """
    # In stop-band, high R → low LDOS.
    return 1.0 - R

# Demonstration
if __name__ == "__main__":
    # Design a DBR for 500 nm
    n_low, n_high = 1.45, 2.0
    lambda_center = 500  # nm
    d_low = lambda_center / (4 * n_low)
    d_high = lambda_center / (4 * n_high)
    N_pairs = 10
    
    wl = np.linspace(400, 700, 500)
    R = dbr_reflectance(wl, n_low, n_high, d_low, d_high, N_pairs)
    F = LDOS_factor(R)
    
    plt.figure()
    plt.plot(wl, R, label='Reflectance')
    plt.plot(wl, F, label='F = k_rad / k_rad0')
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Value')
    plt.legend()
    plt.title('DBR Stop-band and Radiative Rate Modification')
    plt.grid(True)
    plt.show()
    
    # Check suppression at donor emission 480 nm
    idx_donor = np.argmin(np.abs(wl - 480))
    print(f"At λ=480 nm: R={R[idx_donor]:.3f}, F={F[idx_donor]:.3f}")
