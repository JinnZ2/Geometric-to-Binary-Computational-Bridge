"""
quantum_thermo.py – Maximum work extraction and thermal rectification.
"""

import numpy as np
from scipy.linalg import expm

class FRETQuantumBattery:
    """
    Models the excited donor as a quantum battery with energy E_D.
    Computes ergotropy (maximum extractable work).
    """
    def __init__(self, energy: float, temperature: float):
        """
        Parameters
        ----------
        energy : float
            Donor excited state energy (eV)
        temperature : float
            Bath temperature (K)
        """
        self.E = energy
        self.T = temperature
        self.kB = 8.617e-5  # eV/K

    def thermal_state(self):
        """Gibbs state of two-level system."""
        Z = 1 + np.exp(-self.E / (self.kB * self.T))
        p1 = np.exp(-self.E / (self.kB * self.T)) / Z
        return np.array([1-p1, p1])

    def ergotropy(self, initial_excited_prob: float = 1.0):
        """
        Max work extractable via unitary operations.
        For a two-level system initially in state with probability p_exc,
        ergotropy = (p_exc - p_thermal) * E  if p_exc > p_thermal else 0.
        """
        p_thermal = self.thermal_state()[1]
        p_exc = initial_excited_prob
        if p_exc > p_thermal:
            return (p_exc - p_thermal) * self.E
        return 0.0

    def max_fret_efficiency(self, E_FRET: float):
        """
        The thermodynamic upper bound on FRET efficiency.
        Energy not extractable as work is lost as heat.
        """
        W_max = self.ergotropy()
        return W_max / self.E


class ThermalDiode:
    """
    Quantum thermal rectification: heat flows preferentially in one direction.
    """
    def __init__(self, coupling_forward: float, coupling_backward: float):
        self.k_fwd = coupling_forward
        self.k_rev = coupling_backward

    def rectification_ratio(self) -> float:
        """R = |(k_fwd - k_rev) / (k_fwd + k_rev)|."""
        return abs(self.k_fwd - self.k_rev) / (self.k_fwd + self.k_rev)

    def heat_flow(self, T_hot: float, T_cold: float, direction: str = 'forward') -> float:
        """Heat current (arbitrary units)."""
        delta_T = T_hot - T_cold
        k = self.k_fwd if direction == 'forward' else self.k_rev
        return k * delta_T
