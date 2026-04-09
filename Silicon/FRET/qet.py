# STATUS: infrastructure -- quantum energy teleportation on spin chain
"""
qet.py – Quantum Energy Teleportation protocol.
Energy transfer without carrier travel.
"""

import numpy as np

class QETProtocol:
    """
    Implements Hotta's QET protocol on a spin chain.
    """
    def __init__(self, chain_length: int, coupling: float, measurement_strength: float):
        """
        Parameters
        ----------
        chain_length : int
            Number of spins
        coupling : float
            Interaction strength J
        measurement_strength : float
            Strength of local measurement (0 to 1)
        """
        self.N = chain_length
        self.J = coupling
        self.m = measurement_strength

    def ground_state_energy(self):
        """Energy of ground state (placeholder)."""
        return -self.N * self.J

    def measurement_energy_cost(self):
        """Energy injected by Alice's measurement."""
        return self.m * self.J

    def teleported_energy(self, distance: int):
        """
        Energy Bob can extract after Alice's measurement.
        Decays with distance.
        """
        return self.m * self.J * np.exp(-distance / self.N)

    def effective_efficiency(self, distance: int):
        """η = E_Bob / E_Alice."""
        E_in = self.measurement_energy_cost()
        E_out = self.teleported_energy(distance)
        return E_out / E_in if E_in > 0 else 0.0
