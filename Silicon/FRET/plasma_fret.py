"""
plasma_fret.py – Plasma effects on FRET.
- Dielectric function ε(ω) modifying refractive index and LDOS
- Debye screening of dipole-dipole interaction
- Collisional decoherence (quantum yield suppression)
"""

import numpy as np
from scipy.constants import epsilon_0, e, m_e, c
from fret_core import R0, k_FRET, E_FRET

# ----------------------------------------------------------------------
# 1. Plasma Dielectric Function
# ----------------------------------------------------------------------
class PlasmaDielectric:
    """
    Cold plasma dielectric function ε(ω) = 1 - ω_p² / (ω² + i γ ω).
    """
    def __init__(self, electron_density, collision_freq=0.0):
        """
        Parameters
        ----------
        electron_density : float
            n_e in m^-3
        collision_freq : float
            γ in rad/s (damping)
        """
        self.n_e = electron_density
        self.gamma = collision_freq
        self.omega_p = np.sqrt(self.n_e * e**2 / (m_e * epsilon_0))

    def epsilon(self, omega):
        """Complex dielectric constant at angular frequency ω (rad/s)."""
        return 1 - self.omega_p**2 / (omega**2 + 1j * self.gamma * omega)

    def refractive_index(self, omega):
        """Complex refractive index n = √ε."""
        eps = self.epsilon(omega)
        return np.sqrt(eps)

    def LDOS_factor(self, omega):
        """
        Modification of radiative LDOS in plasma.
        Simplified: F = |n|³ for isotropic medium (approx).
        """
        n = self.refractive_index(omega)
        return np.abs(n)**3


# ----------------------------------------------------------------------
# 2. Debye Screening of Dipole Interaction
# ----------------------------------------------------------------------
class DebyeScreening:
    """
    In a plasma, the Coulomb interaction is screened: V(r) ∝ e^{-κ r} / r.
    For dipole-dipole interaction, the screening modifies the r⁻⁶ dependence.
    """
    def __init__(self, temperature, electron_density, ion_density=None):
        """
        Parameters
        ----------
        temperature : float
            T in Kelvin
        electron_density : float
            n_e in m^-3
        ion_density : float, optional
            If None, assume quasi-neutrality n_i ≈ n_e.
        """
        self.T = temperature
        self.n_e = electron_density
        self.n_i = ion_density if ion_density else electron_density
        self.kB = 1.38e-23
        self.eps0 = epsilon_0
        self.e = e
        # Debye length λ_D
        self.lambda_D = np.sqrt(self.eps0 * self.kB * self.T /
                                (self.n_e * self.e**2 + self.n_i * self.e**2))

    def screening_factor(self, r_nm):
        """
        Multiply k_FRET by exp(-κ r) with κ = 1/λ_D.
        r_nm : distance in nm.
        """
        r_m = r_nm * 1e-9
        kappa = 1.0 / self.lambda_D
        return np.exp(-kappa * r_m)

    def effective_R0(self, R0_nominal, r):
        """
        Since k_FRET ∝ (R0/r)⁶, multiplying by screening factor is equivalent
        to R0_eff = R0 * [exp(-κ r)]^{1/6}.
        """
        sf = self.screening_factor(r)
        return R0_nominal * sf**(1/6)


# ----------------------------------------------------------------------
# 3. Collisional Decoherence
# ----------------------------------------------------------------------
class CollisionalDecoherence:
    """
    Frequent collisions in plasma reduce quantum yield Φ_D.
    """
    def __init__(self, collision_rate, tau_D):
        """
        Parameters
        ----------
        collision_rate : float
            Γ_coll in s^-1
        tau_D : float
            Donor lifetime in ns
        """
        self.Gamma = collision_rate  # s^-1
        self.tau_D_ns = tau_D
        self.k_D = 1.0 / (tau_D * 1e-9)  # s^-1

    def effective_quantum_yield(self, Phi_D0):
        """
        Φ_eff = k_rad / (k_rad + k_nr + Γ_coll)
        Assuming k_rad = Φ_D0 * k_D, k_nr = (1-Φ_D0)*k_D.
        """
        k_rad = Phi_D0 * self.k_D
        k_nr = (1 - Phi_D0) * self.k_D
        return k_rad / (k_rad + k_nr + self.Gamma)


# ----------------------------------------------------------------------
# 4. Combined Plasma FRET System
# ----------------------------------------------------------------------
class PlasmaFRET:
    def __init__(self, tau_D, R0, lambda_D, plasma_diel=None, debye=None, decoherence=None, Phi_D0=0.6):
        self.tau_D = tau_D
        self.R0 = R0
        self.lambda_D = lambda_D  # nm
        self.omega = 2 * np.pi * c / (lambda_D * 1e-9)
        self.plasma = plasma_diel
        self.debye = debye
        self.decoherence = decoherence
        self.Phi_D0 = Phi_D0

    def effective_parameters(self, r):
        """Return (tau_eff, R0_eff, k_rad_eff, k_nr_eff)."""
        # Start with base
        tau_eff = self.tau_D
        R0_eff = self.R0
        Phi_eff = self.Phi_D0

        # Plasma dielectric modifies n, which affects R0 via n^{-4} factor
        if self.plasma:
            n_complex = self.plasma.refractive_index(self.omega)
            n_real = np.real(n_complex)
            # R0 ∝ n^{-2/3} (from earlier equation, check: actually n^{-4} inside R0^6, so R0 ∝ n^{-2/3})
            R0_eff *= (1.4 / n_real)**(2/3)  # assuming reference n=1.4

            # LDOS modifies radiative rate
            F = self.plasma.LDOS_factor(self.omega)
            k_rad_base = self.Phi_D0 / (self.tau_D * 1e-9)
            k_rad_eff = k_rad_base * F
        else:
            k_rad_base = self.Phi_D0 / (self.tau_D * 1e-9)
            k_rad_eff = k_rad_base

        # Debye screening
        if self.debye:
            R0_eff = self.debye.effective_R0(R0_eff, r)

        # Collisional decoherence
        if self.decoherence:
            Phi_eff = self.decoherence.effective_quantum_yield(self.Phi_D0)
            # Update radiative rate accordingly
            k_rad_eff = Phi_eff * (1.0 / (self.tau_D * 1e-9))

        # Non-radiative rate
        k_nr_eff = (1 - Phi_eff) * (1.0 / (self.tau_D * 1e-9))

        # Convert back to ns^-1 for consistency with fret_core
        k_rad_ns = k_rad_eff * 1e-9
        k_nr_ns = k_nr_eff * 1e-9

        return tau_eff, R0_eff, k_rad_ns, k_nr_ns

    def efficiency(self, r):
        tau_eff, R0_eff, k_rad_ns, k_nr_ns = self.effective_parameters(r)
        kf = k_FRET(r, R0_eff, tau_eff)
        return kf / (kf + k_rad_ns + k_nr_ns)
