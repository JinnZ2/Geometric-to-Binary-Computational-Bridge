# STATUS: infrastructure -- Casimir cavity force tuning of donor-acceptor distance
"""
vacuum_fret.py – Engineering the quantum vacuum via Casimir forces.
"""

import numpy as np
from scipy.constants import hbar, c, pi
from fret_core import E_FRET, k_FRET

class CasimirCavity:
    """
    Two parallel plates separated by distance d exert Casimir force.
    One plate is attached to a FRET scaffold, tuning r.
    """
    def __init__(self, plate_separation: float, area: float, r0: float, spring_constant: float):
        """
        Parameters
        ----------
        plate_separation : float
            d in nm
        area : float
            Plate area in nm²
        r0 : float
            Equilibrium donor-acceptor distance without Casimir force (nm)
        spring_constant : float
            Effective spring constant of linker (N/m)
        """
        self.d = plate_separation * 1e-9  # m
        self.A = area * 1e-18  # m²
        self.r0 = r0
        self.k = spring_constant

    def casimir_force(self) -> float:
        """Casimir force (N) for perfect conductors."""
        return -pi**2 * hbar * c / (240 * self.d**4) * self.A

    def effective_distance(self) -> float:
        """New equilibrium distance r (nm)."""
        delta_r_m = self.casimir_force() / self.k
        delta_r_nm = delta_r_m * 1e9
        return max(0.1, self.r0 + delta_r_nm)

    def efficiency(self, R0: float, tau_D: float, k_rad: float, k_nr: float) -> float:
        r_eff = self.effective_distance()
        kf = k_FRET(r_eff, R0, tau_D)
        return kf / (kf + k_rad + k_nr)


class VacuumFriction:
    """
    Rotational vacuum friction on a spinning nanoparticle, tunable via graphene.
    Could be used to orient dipoles (κ² control).
    """
    def __init__(self, rotation_freq: float, distance_to_graphene: float):
        self.omega = rotation_freq
        self.z = distance_to_graphene * 1e-9  # m

    def friction_torque(self) -> float:
        """Qualitative model: torque ∝ ω / z^4."""
        return 1e-30 * self.omega / self.z**4  # placeholder scaling

    def alignment_factor(self) -> float:
        """
        Friction slows rotation, allowing external B-field to align dipoles.
        Returns effective κ² enhancement factor (1 to 4).
        """
        # Placeholder: more friction = more alignment
        torque = self.friction_torque()
        alignment = 1.0 / (1.0 + np.exp(-torque / 1e-25))
        return 2/3 + (4 - 2/3) * alignment
