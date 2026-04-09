"""
magneto_fret.py – Magnetic field control of FRET.
- Zeeman spectral shift
- Langevin alignment of magnetic dipoles
"""

import numpy as np
from scipy.constants import mu_0, k as kB, hbar, eV
from fret_core import R0, k_FRET, E_FRET

class MagnetoFRET:
    def __init__(self, tau_D, R0_0, g_D=2.0, g_A=2.0, mu_m=0.0, T=298):
        """
        Parameters
        ----------
        tau_D : float
            Donor lifetime (ns)
        R0_0 : float
            Förster radius at B=0 (nm)
        g_D, g_A : float
            g-factors for Zeeman shift (donor & acceptor)
        mu_m : float
            Magnetic dipole moment (Bohr magnetons) for alignment
        T : float
            Temperature (K)
        """
        self.tau_D = tau_D
        self.R0_0 = R0_0
        self.g_D = g_D
        self.g_A = g_A
        self.mu_m = mu_m * 9.274e-24  # Bohr magneton to J/T
        self.T = T
        self.mu_B = 9.274e-24  # J/T

    def zeeman_shift(self, B):
        """Energy shift in eV for field B (Tesla)."""
        return self.g_D * self.mu_B * B / eV  # eV

    def spectral_shift_factor(self, B, sensitivity=0.1):
        """Fractional change in J per Tesla (simplified)."""
        dE = self.zeeman_shift(B)
        return 1.0 - sensitivity * dE / 0.1  # empirical

    def kappa2_aligned(self, B):
        """Orientation factor under magnetic alignment."""
        if self.mu_m == 0:
            return 2/3
        x = self.mu_m * B / (kB * self.T)
        if x < 1e-6:
            return 2/3
        L = 1.0 / np.tanh(x) - 1.0 / x  # Langevin
        # Max κ² = 4 for parallel dipoles, min = 0 for perpendicular
        # Aligned dipoles give κ² = 4 * L^2 (simplified)
        aligned = 4.0 * L**2
        return 2/3 + (aligned - 2/3) * L

    def R0_B(self, B):
        """Förster radius at field B."""
        k2 = self.kappa2_aligned(B)
        J_factor = self.spectral_shift_factor(B)
        return self.R0_0 * (k2 / (2/3) * J_factor)**(1/6)

    def efficiency(self, r, B, k_rad=0.1, k_nr=0.05):
        kf = k_FRET(r, self.R0_B(B), self.tau_D)
        return kf / (kf + k_rad + k_nr)
