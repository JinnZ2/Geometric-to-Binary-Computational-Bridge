"""
axion_fret.py – FRET-based axion dark matter sensor.
Axion-photon conversion in B-field modulates spectral overlap J.
"""

import numpy as np
from scipy.constants import c, e, hbar, pi
from fret_core import R0, E_FRET

class AxionSensor:
    """
    Models axion dark matter conversion to photons inside a cavity.
    """
    def __init__(self, B_field: float, cavity_Q: float, cavity_volume: float, axion_mass: float):
        """
        Parameters
        ----------
        B_field : float
            Magnetic field strength (Tesla)
        cavity_Q : float
            Quality factor of optical cavity
        cavity_volume : float
            Mode volume (m³)
        axion_mass : float
            Axion mass (eV)
        """
        self.B = B_field
        self.Q = cavity_Q
        self.V = cavity_volume
        self.m_a = axion_mass
        self.g_agg = 1e-11  # axion-photon coupling (GeV^-1), placeholder
        self.rho_DM = 0.45  # GeV/cm³, local dark matter density

    def conversion_power(self) -> float:
        """
        Power of axion-converted photons (Watts).
        From Sikivie formula: P ∝ (g B)^2 ρ V Q / m_a.
        """
        # Convert to SI
        rho_SI = self.rho_DM * 1e9 * 1.6e-19 / 1e-6  # J/m³
        m_a_eV = self.m_a
        m_a_kg = m_a_eV * 1.6e-19 / c**2
        g_agg_GeV = self.g_agg
        g_agg_SI = g_agg_GeV * 1e-9 / 1.6e-19  # T^-1? Simplified.
        # Placeholder scaling
        return (g_agg_SI * self.B)**2 * rho_SI * self.V * self.Q / m_a_kg

    def photon_rate(self) -> float:
        """Number of photons per second in cavity mode."""
        P = self.conversion_power()
        omega = self.m_a * 1.6e-19 / hbar  # axion frequency
        return P / (hbar * omega)

    def fret_modulation(self, R0_nominal: float, r: float, tau_D: float) -> float:
        """
        If axion photon frequency matches donor emission, it adds an excitation channel,
        effectively increasing the apparent donor excitation rate. This changes FRET efficiency.
        """
        # In a real experiment, axion photons would be at ω_a = m_a c^2 / ħ.
        # We model as an additional excitation rate k_ax.
        k_ax = self.photon_rate()  # photons/s, need to match units
        kf = (1/tau_D) * (R0_nominal/r)**6
        k_rad = 0.1
        k_nr = 0.05
        # Additional excitation increases donor population, but FRET efficiency unchanged.
        # For sensing, we look at fluorescence intensity modulation.
        return kf / (kf + k_rad + k_nr)  # no change in E, but intensity increases
