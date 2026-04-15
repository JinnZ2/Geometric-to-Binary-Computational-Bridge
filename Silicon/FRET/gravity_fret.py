# STATUS: infrastructure -- gravitational redshift and time dilation on FRET
"""
gravity_fret.py – Gravitational effects on FRET.
- Redshift spectral detuning
- Time dilation rate modulation
- Tidal strain on molecular scaffolds
"""

import numpy as np
from scipy.constants import G, c, h, k as kB
# NOTE: We deliberately do NOT import R0 from fret_core here. The
# GravitationalFRET class takes R0 as a constructor parameter (each
# instance carries its own Förster radius), so a module-level R0 would
# only shadow the parameter and confuse readers. k_FRET and E_FRET are
# still imported as module-level helpers.
from fret_core import k_FRET, E_FRET  # noqa: F401 — E_FRET used by demo block

# ----------------------------------------------------------------------
# 1. Gravitational Redshift: Spectral Overlap Tuning
# ----------------------------------------------------------------------
class GravitationalRedshift:
    """
    Models the shift in donor emission wavelength due to gravitational potential.
    """
    def __init__(self, lambda_D_emit, potential_difference):
        """
        Parameters
        ----------
        lambda_D_emit : float
            Donor emission wavelength at emission point (nm)
        potential_difference : float
            ΔΦ = Φ_obs - Φ_emit (m²/s²). Positive means observer is higher up.
        """
        self.lambda0 = lambda_D_emit
        self.dphi = potential_difference

    def shifted_wavelength(self):
        """Wavelength observed at acceptor (nm)."""
        # Δλ/λ ≈ ΔΦ / c²
        return self.lambda0 * (1 + self.dphi / c**2)

    def spectral_shift_nm(self):
        """Shift in nm."""
        return self.shifted_wavelength() - self.lambda0

    def J_factor(self, sensitivity=0.1):
        """
        Fractional change in spectral overlap J.
        Assumes linear sensitivity near peak.
        """
        delta_lambda = self.spectral_shift_nm()
        return 1.0 - sensitivity * delta_lambda / 10.0  # heuristic


# ----------------------------------------------------------------------
# 2. Time Dilation: Rate Modulation
# ----------------------------------------------------------------------
class GravitationalTimeDilation:
    """
    Clocks run slower in a gravitational well. All rates are multiplied by
    sqrt(1 + 2Φ/c²). For weak fields, factor ≈ 1 + Φ/c².
    """
    def __init__(self, potential):
        """
        Parameters
        ----------
        potential : float
            Gravitational potential Φ (m²/s²). Negative near mass.
        """
        self.Phi = potential
        # Time dilation factor relative to flat spacetime
        self.gamma = np.sqrt(1 + 2 * self.Phi / c**2)

    def rate_multiplier(self):
        """All rates (k_FRET, k_rad, k_nr) are multiplied by gamma."""
        return self.gamma

    def observed_lifetime(self, tau_D_proper):
        """Proper lifetime tau_D appears dilated to distant observer."""
        return tau_D_proper / self.gamma


# ----------------------------------------------------------------------
# 3. Tidal Forces: Strain on Molecular Scaffolds
# ----------------------------------------------------------------------
class TidalStrain:
    """
    Models stretching of linker due to gravitational gradient.
    """
    def __init__(self, mass, distance, linker_length, stiffness):
        """
        Parameters
        ----------
        mass : float
            Mass of the gravitating body (kg)
        distance : float
            Distance from center of mass to scaffold (m)
        linker_length : float
            Length of the FRET linker (nm)
        stiffness : float
            Effective spring constant of linker (N/m)
        """
        self.M = mass
        self.R = distance
        self.L0 = linker_length * 1e-9  # m
        self.k = stiffness

    def tidal_force_difference(self):
        """
        Force difference across the linker (N).
        dF ≈ (2 G M / R³) * L0 * m_linker
        For simplicity, we assume a point mass m_eff at each end.
        """
        # Use gradient of gravity: dg/dr = -2GM/R³
        g_gradient = 2 * G * self.M / self.R**3
        # Assume effective mass of dye+linker segment is ~10^-24 kg
        m_eff = 1e-24  # approximate molecular mass
        return m_eff * g_gradient * self.L0

    def strain(self):
        """Fractional length change ΔL / L0."""
        F = self.tidal_force_difference()
        delta_L = F / self.k
        return delta_L / self.L0

    def effective_distance(self, r0_nm):
        """Distance r modified by tidal strain."""
        strain = self.strain()
        return r0_nm * (1 + strain)


# ----------------------------------------------------------------------
# 4. Combined Gravitational FRET System
# ----------------------------------------------------------------------
class GravitationalFRET:
    """
    Combines redshift, time dilation, and tidal strain.
    """
    def __init__(self, tau_D, R0, redshift=None, dilation=None, tidal=None):
        self.tau_D = tau_D
        self.R0 = R0
        self.redshift = redshift
        self.dilation = dilation
        self.tidal = tidal

    def effective_parameters(self, r_nominal):
        """Return (tau_eff, R0_eff, r_eff) after applying all effects."""
        tau_eff = self.tau_D
        R0_eff = self.R0
        r_eff = r_nominal

        if self.dilation:
            gamma = self.dilation.rate_multiplier()
            tau_eff = self.tau_D / gamma  # rates scale with gamma, so lifetime scales 1/gamma

        if self.redshift:
            J_factor = self.redshift.J_factor()
            R0_eff = self.R0 * (J_factor)**(1/6)

        if self.tidal:
            r_eff = self.tidal.effective_distance(r_nominal)

        return tau_eff, R0_eff, r_eff

    def efficiency(self, r_nominal, k_rad=0.1, k_nr=0.05):
        tau_eff, R0_eff, r_eff = self.effective_parameters(r_nominal)
        kf = k_FRET(r_eff, R0_eff, tau_eff)
        if self.dilation:
            gamma = self.dilation.rate_multiplier()
            k_rad_eff = k_rad * gamma
            k_nr_eff = k_nr * gamma
        else:
            k_rad_eff = k_rad
            k_nr_eff = k_nr
        return kf / (kf + k_rad_eff + k_nr_eff)
