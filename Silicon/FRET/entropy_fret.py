# STATUS: infrastructure -- entropic linker and worm-like chain distributions
"""
entropy_fret.py – Entropy-driven distance distributions.
"""

import numpy as np
from scipy.integrate import simpson
from fret_core import E_FRET

class EntropicLinker:
    def __init__(self, L_contour, L_persistence, binding_sites=None, T=298):
        """
        Parameters
        ----------
        L_contour : float
            Contour length (nm)
        L_persistence : float
            Persistence length (nm)
        binding_sites : list of tuples (r_b, dG, sigma)
            Each binding site: position (nm), free energy (kT), width (nm)
        T : float
            Temperature (K)
        """
        self.Lc = L_contour
        self.Lp = L_persistence
        self.binding = binding_sites if binding_sites else []
        self.T = T
        self.kBT = 1.38e-23 * T / 1.6e-19  # J -> eV, but we work in kT units
        # Actually keep everything in kT for simplicity

    def free_energy(self, r):
        """F(r) in units of kT."""
        # Worm-like chain approximation for entropic spring
        # F_entropic ≈ (3/2) * (r^2) / (Lp * Lc) for small extensions
        F_ent = 1.5 * r**2 / (self.Lp * self.Lc)
        F_bind = 0.0
        for rb, dG, sig in self.binding:
            F_bind += dG * np.exp(-(r - rb)**2 / (2 * sig**2))
        return F_ent + F_bind

    def probability_density(self, r_vals):
        """Boltzmann distribution P(r)."""
        F = np.array([self.free_energy(r) for r in r_vals])
        P = np.exp(-F)
        return P / simpson(P, r_vals)

    def average_efficiency(self, r_vals, R0):
        P = self.probability_density(r_vals)
        E = np.array([E_FRET(r, R0) for r in r_vals])
        return simpson(P * E, r_vals)
