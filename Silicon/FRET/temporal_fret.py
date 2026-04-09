# STATUS: infrastructure -- photonic time crystals with periodic refractive index
"""
temporal_fret.py – Time as a control axis: Photonic Time Crystals (PTC).
Modulates radiative rate k_rad(t) or FRET rate k_FRET(t) periodically.
"""

import numpy as np
from scipy.integrate import quad
from fret_core import E_FRET, k_FRET

class PhotonicTimeCrystal:
    """
    Models a medium with time-periodic refractive index: n(t) = n0 + Δn sin(Ωt).
    This modulates the LDOS, hence k_rad and potentially R0.
    """
    def __init__(self, n0: float, delta_n: float, frequency: float, tau_D: float, R0: float):
        """
        Parameters
        ----------
        n0 : float
            Average refractive index
        delta_n : float
            Modulation amplitude
        frequency : float
            Modulation frequency (MHz)
        tau_D : float
            Donor lifetime (ns)
        R0 : float
            Förster radius at n=n0 (nm)
        """
        self.n0 = n0
        self.delta_n = delta_n
        self.f = frequency
        self.omega = 2 * np.pi * frequency
        self.tau_D = tau_D
        self.R0 = R0

    def n_t(self, t: float) -> float:
        """Instantaneous refractive index at time t (μs)."""
        return self.n0 + self.delta_n * np.sin(self.omega * t)

    def R0_t(self, t: float) -> float:
        """
        R0 scales as n^{-2/3} (from R0 ∝ n^{-2/3}).
        """
        n_ratio = self.n_t(t) / self.n0
        return self.R0 * (n_ratio)**(-2/3)

    def k_rad_t(self, k_rad0: float, t: float) -> float:
        """
        Radiative rate modulated by LDOS change.
        For a weak modulation, assume k_rad ∝ n (simplified).
        """
        return k_rad0 * (self.n_t(t) / self.n0)

    def average_efficiency(self, r: float, k_rad0: float, k_nr: float, n_cycles: int = 10) -> float:
        """
        Time-averaged FRET efficiency over PTC cycles.
        """
        period = 1.0 / self.f
        T = n_cycles * period

        def integrand(t):
            R0_t = self.R0_t(t)
            kf = k_FRET(r, R0_t, self.tau_D)
            kr_t = self.k_rad_t(k_rad0, t)
            k_total = kf + kr_t + k_nr
            return kf / k_total

        avg_E, _ = quad(integrand, 0, T, limit=100)
        return avg_E / T

    def enhancement_factor(self, r: float, k_rad0: float, k_nr: float) -> float:
        """Ratio of average to static efficiency."""
        E_static = E_FRET(r, self.R0)  # static uses k_rad0 implicitly? We'll compute properly
        kf_static = k_FRET(r, self.R0, self.tau_D)
        E_static_correct = kf_static / (kf_static + k_rad0 + k_nr)
        E_avg = self.average_efficiency(r, k_rad0, k_nr)
        return E_avg / E_static_correct
