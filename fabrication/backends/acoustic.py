"""
acoustic.py  (fabrication/backends/)

Acoustic = pressure (effort) / volume-flow (flow).
Speed of sound c, air density ρ as defaults; overridable.
All formulas are first-principles, no empirical fudge.

Geometry -> bond-graph parameter

  kind        formula                       physical meaning
  store_flow  M = ρℓ/A                      inertance (mass-of-air-in-tube)
  store_eff   C = V/(ρc²)                   compliance (cavity springiness)
  dissipate   R = 8μℓ/(πr⁴)  [tube]         viscous loss (also laminar fluid)
  transform   n = A_in / A_out              horn / area ratio
  Helmholtz   f = (c/2π)√(A/(Vℓ_eff))       resonator natural freq

License: CC0. Stdlib only.
"""
from math import pi, sqrt
from dataclasses import dataclass

RHO_AIR = 1.225     # kg/m^3   at 15 C, 1 atm
C_AIR   = 343.0     # m/s
MU_AIR  = 1.81e-5   # Pa·s     (used in fluidic + acoustic loss)


@dataclass(frozen=True)
class AcousticParams:
    rho: float = RHO_AIR
    c:   float = C_AIR
    mu:  float = MU_AIR


def inertance(length, area, p: AcousticParams = AcousticParams()):
    return p.rho * length / area


def compliance(volume, p: AcousticParams = AcousticParams()):
    return volume / (p.rho * p.c**2)


def viscous_loss(length, radius, p: AcousticParams = AcousticParams()):
    return 8 * p.mu * length / (pi * radius**4)


def horn_ratio(area_in, area_out):
    return area_in / area_out


def helmholtz_freq(neck_area, neck_length, cavity_volume,
                   p: AcousticParams = AcousticParams()):
    """Effective neck length: ℓ + 1.7 r  (Rayleigh end-correction, one side)."""
    r = sqrt(neck_area / pi)
    l_eff = neck_length + 1.7 * r
    return (p.c / (2 * pi)) * sqrt(neck_area / (cavity_volume * l_eff))


# Returns (parameter_value, tolerance_band) for claim emission.
# Tolerance comes from fab variance, NOT from physics.
def with_tolerance(value, frac=0.05):
    return value, (value * (1 - frac), value * (1 + frac))
