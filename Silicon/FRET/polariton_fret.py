"""
polariton_fret.py – Exciton-polariton mediated energy transfer.
"""

import numpy as np

class PolaritonRelay:
    def __init__(self, Rabi_splitting, gamma_D, gamma_cav, v_group, tau_LP, eta_abs):
        """
        Parameters (all in meV or ps)
        Rabi_splitting : float
            Ω_R, strong coupling energy (meV)
        gamma_D, gamma_cav : float
            Donor and cavity decay rates (meV)
        v_group : float
            Polariton group velocity (μm/ps)
        tau_LP : float
            Polariton lifetime (ps)
        eta_abs : float
            Acceptor absorption efficiency (0-1)
        """
        self.Omega = Rabi_splitting
        self.gamma_D = gamma_D
        self.gamma_cav = gamma_cav
        self.v_g = v_group
        self.tau = tau_LP
        self.eta_abs = eta_abs

    def injection_efficiency(self):
        """Efficiency of donor exciting polariton."""
        return self.Omega**2 / (self.Omega**2 + self.gamma_D * self.gamma_cav)

    def propagation_efficiency(self, distance):
        """Exponential decay over distance (μm)."""
        return np.exp(-distance / (self.v_g * self.tau))

    def total_efficiency(self, distance):
        return (self.injection_efficiency() *
                self.propagation_efficiency(distance) *
                self.eta_abs)
