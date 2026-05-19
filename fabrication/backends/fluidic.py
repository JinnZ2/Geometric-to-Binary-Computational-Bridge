"""
fluidic.py  (fabrication/backends/)

Fluidic (laminar, incompressible) reuses acoustic algebra with
different conserved quantities. This is the bond-graph payoff:
same IR, different units.

License: CC0. Stdlib only.
"""
from math import pi
from dataclasses import dataclass


@dataclass(frozen=True)
class FluidParams:
    rho: float        # working fluid density
    mu:  float        # dynamic viscosity


WATER  = FluidParams(rho=1000.0, mu=1.00e-3)
GLY50  = FluidParams(rho=1130.0, mu=6.00e-3)   # 50% glycerin
AIR_F  = FluidParams(rho=1.225,  mu=1.81e-5)


def channel_resistance(length, radius, p: FluidParams):
    """Hagen-Poiseuille."""
    return 8 * p.mu * length / (pi * radius**4)


def channel_inertance(length, area, p: FluidParams):
    return p.rho * length / area


def reservoir_compliance(volume, bulk_modulus):
    """Soft-walled reservoir or air-trapped chamber."""
    return volume / bulk_modulus


# Reynolds gate -- claim is only valid in laminar regime.
def reynolds(rho, v_mean, diameter, mu):
    return rho * v_mean * diameter / mu


def laminar_ok(Re):
    return Re < 2300.0  # transition threshold; flag if violated
