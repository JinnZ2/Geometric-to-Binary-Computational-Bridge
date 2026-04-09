# STATUS: infrastructure -- NSET, plasmon relay, BIC-enhanced long-range FRET
"""
extended_range.py – Extend FRET beyond the classical 10‑nm limit.
Implements:
- NSET (nanoparticle surface energy transfer, r⁻⁴ dependence)
- Plasmon relay (coupled mode theory, enhanced effective R0)
- BIC-enhanced FRET (exponential decay over long range)
- Composite system stacking multiple mechanisms
"""

import numpy as np
from scipy.constants import c, hbar, epsilon_0
from fret_core import k_FRET, E_FRET

# ----------------------------------------------------------------------
# Material dielectric functions (simplified Drude-Lorentz)
# ----------------------------------------------------------------------
def drude_lorentz_epsilon(omega, omega_p, gamma, epsilon_inf=1.0):
    """Drude model dielectric function."""
    return epsilon_inf - omega_p**2 / (omega**2 + 1j * gamma * omega)

def gold_epsilon(omega):
    """Gold dielectric function (simplified parameters)."""
    # omega in rad/s
    omega_p = 1.37e16   # plasma frequency rad/s
    gamma = 1.08e14     # damping rad/s
    return drude_lorentz_epsilon(omega, omega_p, gamma, epsilon_inf=9.5)

def silver_epsilon(omega):
    """Silver dielectric function."""
    omega_p = 1.37e16
    gamma = 2.73e13
    return drude_lorentz_epsilon(omega, omega_p, gamma, epsilon_inf=4.0)

# ----------------------------------------------------------------------
# 1. NSET: Nanosurface Energy Transfer
# ----------------------------------------------------------------------
class NSETDonor:
    """
    Donor coupled to a metal nanoparticle via NSET.
    Characteristic distance d0 calculated from Persson-Lang model.
    """
    def __init__(self, tau_D, Phi_D, kappa2, lambda_D, metal='Au', epsilon_d=1.33**2):
        """
        Parameters
        ----------
        tau_D : float
            Donor lifetime (ns).
        Phi_D : float
            Donor quantum yield.
        kappa2 : float
            Orientation factor.
        lambda_D : float
            Donor emission wavelength (nm).
        metal : str
            'Au' or 'Ag'.
        epsilon_d : float
            Dielectric constant of surrounding medium.
        """
        self.tau_D = tau_D
        self.Phi_D = Phi_D
        self.kappa2 = kappa2
        self.lambda_D = lambda_D
        self.omega_D = 2 * np.pi * c / (lambda_D * 1e-9)
        self.epsilon_d = epsilon_d

        # Get metal epsilon at donor frequency
        if metal == 'Au':
            self.eps_m = gold_epsilon(self.omega_D)
        elif metal == 'Ag':
            self.eps_m = silver_epsilon(self.omega_D)
        else:
            raise ValueError("Metal must be 'Au' or 'Ag'")

        # Compute d0 (in nm)
        self.d0 = self._compute_d0()

    def _compute_d0(self):
        """Persson-Lang d0 calculation (returns nm)."""
        # Prefactor: (3 hbar c^3 Phi_D kappa^2 / (4 pi omega_D^3))^(1/4)
        # Convert to SI, then result in meters, finally nm
        hbar_c3 = hbar * c**3
        omega3 = self.omega_D**3
        prefactor = (3 * hbar_c3 * self.Phi_D * self.kappa2 / (4 * np.pi * omega3))**(0.25)

        # Metal response term: Im[eps_m] / |eps_m + 2 eps_d|^2
        metal_term = np.imag(self.eps_m) / np.abs(self.eps_m + 2 * self.epsilon_d)**2
        d0_m = prefactor * metal_term**(0.25)
        return d0_m * 1e9  # convert m to nm

    def k_NSET(self, r):
        """NSET rate (ns⁻¹) at distance r (nm)."""
        return (1.0 / self.tau_D) * (self.d0 / r)**4

    def E_NSET(self, r, k_rad=0.1, k_nr=0.05):
        """NSET efficiency at distance r."""
        knset = self.k_NSET(r)
        return knset / (knset + k_rad + k_nr)

# ----------------------------------------------------------------------
# 2. Plasmon Relay (Coupled Mode Theory)
# ----------------------------------------------------------------------
class PlasmonRelay:
    """
    Donor → Plasmonic Antenna → Acceptor energy relay.
    Effective R0 enhanced by Purcell factor and plasmon lifetime.
    """
    def __init__(self, tau_D, R0_nominal, F_P, tau_P, r_DP):
        """
        Parameters
        ----------
        tau_D : float
            Donor lifetime (ns).
        R0_nominal : float
            Förster radius for direct donor-acceptor (nm).
        F_P : float
            Purcell factor for donor-plasmon coupling.
        tau_P : float
            Plasmon lifetime (ns). Typically very short (~0.01 ns).
        r_DP : float
            Fixed distance from donor to plasmonic structure (nm).
        """
        self.tau_D = tau_D
        self.R0 = R0_nominal
        self.F_P = F_P
        self.tau_P = tau_P
        self.r_DP = r_DP

        # Effective R0 for plasmon-acceptor step
        # R_eff = R0 * (F_P * tau_P / tau_D)^(1/6)
        self.R_eff = R0_nominal * (F_P * tau_P / tau_D)**(1/6)

    def k_plasmon_relay(self, r_PA, k_rad_D=0.1, k_nr_D=0.05):
        """
        Effective transfer rate from donor to acceptor via plasmon.
        r_PA: distance from plasmon to acceptor (nm).
        Returns rate in ns⁻¹.
        """
        # Donor to plasmon rate (Purcell enhanced)
        k_DP = self.F_P * k_rad_D  # assume only radiative couples to plasmon
        # Plasmon to acceptor rate (FRET-like with enhanced R0)
        k_PA = (1.0 / self.tau_P) * (self.R_eff / r_PA)**6
        # Plasmon loss rate
        k_P_loss = 1.0 / self.tau_P

        # Effective transfer rate: k_DP * k_PA / (k_PA + k_P_loss)
        return k_DP * k_PA / (k_PA + k_P_loss)

    def E_plasmon_relay(self, r_PA, k_rad_D=0.1, k_nr_D=0.05):
        """Overall efficiency from donor to acceptor."""
        k_transfer = self.k_plasmon_relay(r_PA, k_rad_D, k_nr_D)
        k_total_loss = k_rad_D + k_nr_D + k_transfer
        return k_transfer / k_total_loss

# ----------------------------------------------------------------------
# 3. BIC-Enhanced FRET
# ----------------------------------------------------------------------
class BICEnhancer:
    """
    Bound state in the continuum mediated energy transfer.
    Exponential distance dependence with long decay length.
    """
    def __init__(self, tau_D, g_coupling, L_BIC, lambda_BIC, lambda_D, Q=1e4):
        """
        Parameters
        ----------
        tau_D : float
            Donor lifetime (ns).
        g_coupling : float
            Dimensionless coupling strength (0 to 1).
        L_BIC : float
            BIC propagation length (nm). Can be >10000 nm.
        lambda_BIC : float
            BIC resonance wavelength (nm).
        lambda_D : float
            Donor emission wavelength (nm).
        Q : float
            Quality factor of the BIC.
        """
        self.tau_D = tau_D
        self.g = g_coupling
        self.L_BIC = L_BIC
        self.lambda_BIC = lambda_BIC
        self.lambda_D = lambda_D
        self.Q = Q
        # Detuning (nm)
        self.delta = lambda_D - lambda_BIC
        # Linewidth (nm) approx lambda_BIC / Q
        self.Gamma = lambda_BIC / Q

    def k_BIC(self, r):
        """
        BIC-mediated transfer rate at distance r (nm).
        Uses Lorentzian detuning and exponential spatial decay.
        """
        # Lorentzian lineshape
        lorentz = self.Gamma**2 / (self.Gamma**2 + self.delta**2)
        # Exponential decay
        spatial = np.exp(-r / self.L_BIC)
        return (1.0 / self.tau_D) * self.g * lorentz * spatial

    def E_BIC(self, r, k_rad=0.1, k_nr=0.05):
        """Efficiency for BIC-mediated transfer."""
        kBIC = self.k_BIC(r)
        return kBIC / (kBIC + k_rad + k_nr)

# ----------------------------------------------------------------------
# 4. Composite System: Stacking Mechanisms
# ----------------------------------------------------------------------
class ExtendedFRETSystem:
    """
    Combine FRET, NSET, plasmon relay, and BIC into a unified system.
    Total transfer rate is sum of independent parallel pathways.
    """
    def __init__(self, tau_D, R0, k_rad=0.1, k_nr=0.05):
        self.tau_D = tau_D
        self.R0 = R0
        self.k_rad = k_rad
        self.k_nr = k_nr
        self.components = {}  # dict of active mechanisms with their parameters

    def add_fret(self, r):
        """Add classical FRET component at distance r."""
        self.components['FRET'] = {'r': r, 'type': 'fret'}

    def add_nset(self, nset_donor, r):
        """Add NSET component."""
        self.components['NSET'] = {'donor': nset_donor, 'r': r, 'type': 'nset'}

    def add_plasmon(self, plasmon_relay, r_PA):
        """Add plasmon relay component."""
        self.components['plasmon'] = {'relay': plasmon_relay, 'r_PA': r_PA, 'type': 'plasmon'}

    def add_bic(self, bic_enhancer, r):
        """Add BIC component."""
        self.components['bic'] = {'bic': bic_enhancer, 'r': r, 'type': 'bic'}

    def total_rate(self):
        """Sum of all active transfer rates (ns⁻¹)."""
        k_tot = 0.0
        for name, comp in self.components.items():
            if comp['type'] == 'fret':
                k_tot += k_FRET(comp['r'], self.R0, self.tau_D)
            elif comp['type'] == 'nset':
                k_tot += comp['donor'].k_NSET(comp['r'])
            elif comp['type'] == 'plasmon':
                k_tot += comp['relay'].k_plasmon_relay(comp['r_PA'], self.k_rad, self.k_nr)
            elif comp['type'] == 'bic':
                k_tot += comp['bic'].k_BIC(comp['r'])
        return k_tot

    def total_efficiency(self):
        """Overall energy transfer efficiency."""
        k_tot = self.total_rate()
        return k_tot / (k_tot + self.k_rad + self.k_nr)

    def rate_breakdown(self):
        """Return dictionary of individual rates."""
        rates = {}
        for name, comp in self.components.items():
            if comp['type'] == 'fret':
                rates[name] = k_FRET(comp['r'], self.R0, self.tau_D)
            elif comp['type'] == 'nset':
                rates[name] = comp['donor'].k_NSET(comp['r'])
            elif comp['type'] == 'plasmon':
                rates[name] = comp['relay'].k_plasmon_relay(comp['r_PA'], self.k_rad, self.k_nr)
            elif comp['type'] == 'bic':
                rates[name] = comp['bic'].k_BIC(comp['r'])
        return rates

# ----------------------------------------------------------------------
# Unified rate function for parameter sweeps
# ----------------------------------------------------------------------
def unified_rate(r, tau_D, R0,
                 alpha=0.0, d0=0.0,
                 beta=0.0, R_eff=0.0, r_c=0.0,
                 gamma=0.0, L_BIC=0.0):
    """
    Unified transfer rate function with smooth interpolation.

    Parameters
    ----------
    r : array or float
        Distance (nm).
    tau_D : float
        Donor lifetime (ns).
    R0 : float
        Förster radius (nm).
    alpha : float
        NSET amplitude (0 disables).
    d0 : float
        NSET characteristic distance (nm).
    beta : float
        Plasmon enhancement factor.
    R_eff : float
        Effective R0 for plasmon-acceptor (nm).
    r_c : float
        Cutoff distance for plasmon saturation (nm).
    gamma : float
        BIC coupling strength.
    L_BIC : float
        BIC decay length (nm).

    Returns
    -------
    Total transfer rate (ns⁻¹).
    """
    k_fret = (1.0 / tau_D) * (R0 / r)**6
    k_nset = alpha * (1.0 / tau_D) * (d0 / r)**4 if d0 > 0 else 0.0
    # Plasmon term with saturation at large r (due to ohmic loss)
    k_plasmon = beta * (1.0 / tau_D) * (R_eff / r)**6 / (1 + (r / r_c)**6) if R_eff > 0 else 0.0
    k_bic = gamma * (1.0 / tau_D) * np.exp(-r / L_BIC) if L_BIC > 0 else 0.0

    return k_fret + k_nset + k_plasmon + k_bic

def unified_efficiency(r, tau_D, R0, k_rad=0.1, k_nr=0.05, **kwargs):
    """Efficiency corresponding to unified_rate."""
    k_tot = unified_rate(r, tau_D, R0, **kwargs)
    return k_tot / (k_tot + k_rad + k_nr)
