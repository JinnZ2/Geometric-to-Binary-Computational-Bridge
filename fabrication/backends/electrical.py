"""
electrical.py  (fabrication/backends/)

Electrical-domain bond-graph parameters with two interpretations:

  (a) idealized lumped values directly specified (R, L, C) --
      for breadboard verification where you read off component
      labels.

  (b) geometric -> parameter -- for fabricated coils, PCB
      inductors, capacitor stacks. All first-principles, no fits.

License: CC0. Stdlib only.
"""
import math


EPSILON_0 = 8.854e-12              # F/m
MU_0      = 4 * math.pi * 1e-7     # H/m


# ----- inductors --------------------------------------------------

def solenoid_inductance(turns, length_m, area_m2, mu_r=1.0):
    """L = μ₀ μ_r N² A / ℓ -- long-solenoid approximation."""
    return MU_0 * mu_r * turns**2 * area_m2 / length_m


def air_core_loop_inductance(radius_m, wire_radius_m):
    """Single circular loop, thin wire."""
    return MU_0 * radius_m * (math.log(8*radius_m/wire_radius_m) - 2)


# ----- capacitors -------------------------------------------------

def parallel_plate_capacitance(area_m2, gap_m, er=1.0):
    return EPSILON_0 * er * area_m2 / gap_m


def cylindrical_capacitance(inner_r, outer_r, length_m, er=1.0):
    return (2*math.pi*EPSILON_0*er*length_m
            / math.log(outer_r/inner_r))


# ----- resistors --------------------------------------------------

def wire_resistance(length_m, area_m2, rho):
    """R = ρ·ℓ/A -- rho in Ω·m."""
    return rho * length_m / area_m2


RHO_TABLE = {
    "copper":   1.68e-8,
    "aluminum": 2.65e-8,
    "nichrome": 1.10e-6,
    "graphite": 7.84e-6,
    "carbon":   3.5e-5,
    "iron":     9.7e-8,
}
