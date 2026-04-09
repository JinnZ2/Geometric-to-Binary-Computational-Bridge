"""
thermal_fret.py – Thermal control of FRET.
- Temperature-dependent R0 via spectral overlap and quantum yield.
- Thermally activated conformational switches (two-state linkers).
- Phonon-assisted FRET for mismatched energy levels.
"""

import numpy as np
from scipy.integrate import quad
from fret_core import R0, E_FRET, k_FRET

# ----------------------------------------------------------------------
# Temperature dependence of R0
# ----------------------------------------------------------------------
class ThermalSpectralShift:
    """
    Models temperature dependence of spectral overlap J and quantum yield Phi_D.
    Typically both decrease with T due to thermal broadening and enhanced non-radiative decay.
    """
    def __init__(self, J0: float, Phi_D0: float, T0: float = 298.0,
                 alpha_J: float = -0.002, alpha_Phi: float = -0.001):
        """
        Parameters
        ----------
        J0, Phi_D0 : float
            Values at reference temperature T0 (K).
        alpha_J, alpha_Phi : float
            Linear temperature coefficients (K^-1). Negative for typical dyes.
        """
        self.J0 = J0
        self.Phi_D0 = Phi_D0
        self.T0 = T0
        self.alpha_J = alpha_J
        self.alpha_Phi = alpha_Phi

    def J(self, T: float) -> float:
        """Spectral overlap at temperature T."""
        return self.J0 * (1 + self.alpha_J * (T - self.T0))

    def Phi_D(self, T: float) -> float:
        """Quantum yield at temperature T."""
        return self.Phi_D0 * (1 + self.alpha_Phi * (T - self.T0))

    def R0_T(self, T: float, kappa2: float, n: float) -> float:
        """Förster radius at temperature T."""
        return R0(kappa2, self.Phi_D(T), n, self.J(T))


# ----------------------------------------------------------------------
# Thermally Activated Conformational Switch
# ----------------------------------------------------------------------
class ThermalSwitch:
    """
    Two-state linker that changes distance at a characteristic temperature.
    Modeled as a sigmoidal transition with free energy difference ΔG(T).
    """
    def __init__(self, r_open: float, r_closed: float,
                 Tm: float, enthalpy: float, heat_capacity: float = 0.0):
        """
        Parameters
        ----------
        r_open, r_closed : float
            Distances (nm) in open and closed states.
        Tm : float
            Melting temperature (K) where states equally populated.
        enthalpy : float
            Enthalpy change ΔH (kJ/mol) at Tm.
        heat_capacity : float
            Heat capacity change ΔCp (kJ/mol·K). Default 0.
        """
        self.r_open = r_open
        self.r_closed = r_closed
        self.Tm = Tm
        self.dH = enthalpy * 1000  # J/mol
        self.dCp = heat_capacity * 1000  # J/mol·K
        self.R = 8.314  # J/mol·K

    def delta_G(self, T: float) -> float:
        """
        Free energy difference (J/mol) between closed and open states.
        Using Gibbs-Helmholtz with constant ΔCp.
        """
        if self.dCp == 0:
            return self.dH * (1 - T / self.Tm)
        else:
            return (self.dH * (1 - T / self.Tm) +
                    self.dCp * (T - self.Tm - T * np.log(T / self.Tm)))

    def fraction_closed(self, T: float) -> float:
        """Fraction of population in closed state."""
        dG = self.delta_G(T)
        return 1.0 / (1.0 + np.exp(dG / (self.R * T)))

    def mean_distance(self, T: float) -> float:
        """Ensemble-averaged distance at temperature T."""
        f_closed = self.fraction_closed(T)
        return f_closed * self.r_closed + (1 - f_closed) * self.r_open

    def effective_efficiency(self, T: float, R0: float) -> float:
        """
        FRET efficiency averaged over thermal ensemble.
        Note: assumes interconversion is fast compared to FRET.
        """
        f_closed = self.fraction_closed(T)
        E_open = E_FRET(self.r_open, R0)
        E_closed = E_FRET(self.r_closed, R0)
        return f_closed * E_closed + (1 - f_closed) * E_open


# ----------------------------------------------------------------------
# Phonon-Assisted FRET (Energy Mismatch)
# ----------------------------------------------------------------------
class PhononAssistedFRET:
    """
    Models FRET between donor and acceptor with energy mismatch ΔE.
    The missing energy is supplied by a phonon.
    """
    def __init__(self, delta_E: float, phonon_energy: float,
                 tau_D: float = 2.5, R0_resonant: float = 5.0):
        """
        Parameters
        ----------
        delta_E : float
            Energy mismatch (meV). Positive if acceptor is higher in energy.
        phonon_energy : float
            Energy of the assisting phonon mode (meV).
        tau_D : float
            Donor lifetime (ns).
        R0_resonant : float
            Förster radius when ΔE=0 (nm).
        """
        self.delta_E = delta_E
        self.hbar_omega = phonon_energy
        self.tau_D = tau_D
        self.R0_res = R0_resonant
        self.kB = 0.08617  # meV/K

    def phonon_occupation(self, T: float) -> float:
        """Bose-Einstein occupation of the phonon mode."""
        if T == 0:
            return 0.0
        x = self.hbar_omega / (self.kB * T)
        return 1.0 / (np.exp(x) - 1.0)

    def franck_condon_factor(self, S: float = 0.1) -> float:
        """
        Huang-Rhys factor S determines phonon coupling strength.
        For weak coupling, probability of phonon emission/absorption ~ S.
        """
        return S

    def k_phonon_assisted(self, r: float, T: float, S: float = 0.1) -> float:
        """
        Phonon-assisted FRET rate.
        Rate is proportional to phonon occupation for absorption (ΔE>0)
        or 1+n for emission (ΔE<0).
        """
        n = self.phonon_occupation(T)
        if self.delta_E > 0:
            # Need to absorb a phonon
            factor = n * S
        else:
            # Phonon emission
            factor = (1 + n) * S

        # Effective R0 is reduced by the Franck-Condon factor
        R0_eff = self.R0_res * (factor)**(1/6) if factor > 0 else 0.0
        if R0_eff == 0:
            return 0.0
        return k_FRET(r, R0_eff, self.tau_D)

    def E_phonon_assisted(self, r: float, T: float, k_rad: float = 0.1, k_nr: float = 0.05, S: float = 0.1) -> float:
        k_assist = self.k_phonon_assisted(r, T, S)
        return k_assist / (k_assist + k_rad + k_nr)


# ----------------------------------------------------------------------
# Combined Thermal System
# ----------------------------------------------------------------------
class ThermalFRETSystem:
    """
    Combines temperature-dependent R0, conformational switching, and phonon assistance.
    """
    def __init__(self, r0: float, R0_0: float, tau_D: float = 2.5,
                 thermal_shift: ThermalSpectralShift = None,
                 switch: ThermalSwitch = None,
                 phonon_assist: PhononAssistedFRET = None):
        self.r0 = r0
        self.R0_0 = R0_0
        self.tau_D = tau_D
        self.thermal_shift = thermal_shift
        self.switch = switch
        self.phonon_assist = phonon_assist

    def efficiency(self, T: float, k_rad: float = 0.1, k_nr: float = 0.05) -> float:
        # Determine current R0
        if self.thermal_shift:
            R0_curr = self.thermal_shift.R0_T(T, kappa2=2/3, n=1.4)  # default κ², n
        else:
            R0_curr = self.R0_0

        # Determine current distance
        if self.switch:
            r_curr = self.switch.mean_distance(T)
        else:
            r_curr = self.r0

        # Base FRET rate
        k_fret = k_FRET(r_curr, R0_curr, self.tau_D)

        # Add phonon-assisted channel if present
        if self.phonon_assist:
            k_assist = self.phonon_assist.k_phonon_assisted(r_curr, T)
            k_fret += k_assist

        return k_fret / (k_fret + k_rad + k_nr)
