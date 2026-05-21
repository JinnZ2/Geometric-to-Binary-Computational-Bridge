"""
magnetic.py  (fabrication/backends/)

Magnetic circuit: flow = flux Φ_B (Wb), effort = MMF ℱ = N·I (A·turn).

  ℛ_gap   = g / (μ₀·A)                   (units: A·turns/Wb = 1/H)
  ℛ_core  = ℓ / (μ₀·μ_r·A)
  L       = N² / ℛ_total                 (inductance from turns + circuit)

Series reluctances add directly; parallel paths combine reciprocally
(same algebra as resistors).

Bridge to electrical IR: a wound coil with N turns is BOTH a
magnetic store_flow (with parameter N²) AND an electrical
store_flow (an inductor) -- N is the gyrator ratio that links the
two scopes. Cross-substrate L claim is the next coupler wedge.

License: CC0. Stdlib only.
"""
import math


MU_0 = 4 * math.pi * 1e-7      # H/m


def gap_reluctance(gap_m, area_m2):
    """Air gap: ℛ = g / (μ₀·A)."""
    return gap_m / (MU_0 * area_m2)


def core_reluctance(length_m, area_m2, mu_r):
    return length_m / (MU_0 * mu_r * area_m2)


def series_reluctance(*Rs):
    return sum(Rs)


def parallel_reluctance(*Rs):
    inv = sum(1.0 / R for R in Rs if R > 0)
    return 1.0 / inv if inv > 0 else float("inf")


def coil_inductance(turns, R_total):
    return (turns ** 2) / R_total


# Common core materials -- CC0 reference μ_r at low B, B_sat at room temp.
MAGNETIC_CORE = {
    "air":             {"mu_r":     1.0, "B_sat_T":  None},
    "ferrite_3C90":    {"mu_r":  2300.0, "B_sat_T":  0.50},
    "ferrite_77":      {"mu_r":  2000.0, "B_sat_T":  0.49},
    "iron_powder_26":  {"mu_r":    75.0, "B_sat_T":  1.4},
    "iron_powder_2":   {"mu_r":    10.0, "B_sat_T":  1.4},
    "silicon_steel":   {"mu_r":  4000.0, "B_sat_T":  2.0},
    "mu_metal":        {"mu_r": 80000.0, "B_sat_T":  0.75},
}
