"""
thermal.py  (fabrication/backends/)

Thermal: flow = heat-flow q̇ (W), effort = temperature difference ΔT (K).

  kind         formula                              physical meaning
  dissipate    R = ℓ/(k·A)                          conduction resistance
  dissipate    R = 1/(h·A)                          convection resistance
  dissipate    R ≈ 1/(4·ε·σ·T_avg³·A)               linearized radiation
  store_eff    C = ρ·c_p·V                          thermal capacitance
  composite    τ = R·C                              first-order time const

No real resonance: thermal diffusion is overdamped. Verification
focuses on time-constant fitting and steady-state ΔT.

License: CC0. Stdlib only.
"""
import math


STEFAN_BOLTZMANN = 5.670374419e-8     # W/(m²·K⁴)


def conduction_resistance(length_m, area_m2, k_thermal):
    """R = ℓ / (k·A)  in K/W."""
    return length_m / (k_thermal * area_m2)


def storage_capacity(volume_m3, density, specific_heat):
    """C = ρ·c_p·V  in J/K."""
    return density * specific_heat * volume_m3


def convection_resistance(h_W_per_m2K, area_m2):
    """R = 1/(h·A).  Natural air h ≈ 5–25 W/m²K;  forced ≈ 25–250."""
    return 1.0 / (h_W_per_m2K * area_m2)


def radiation_resistance_linearized(emissivity, area_m2, T_avg_K):
    """R_rad ≈ 1/(4·ε·σ·T³·A) -- valid for small ΔT around T_avg."""
    return 1.0 / (4.0 * emissivity * STEFAN_BOLTZMANN
                  * (T_avg_K ** 3) * area_m2)


def time_constant(R, C):
    return R * C


# Reference table -- CC0 published values, override per build.
MATERIAL_THERMAL = {
    "copper":     {"k": 401.0,  "rho": 8960,  "cp":  385, "epsilon": 0.04},
    "aluminum":   {"k": 237.0,  "rho": 2700,  "cp":  897, "epsilon": 0.09},
    "steel":      {"k":  50.0,  "rho": 7850,  "cp":  466, "epsilon": 0.50},
    "abs_3dp":    {"k":   0.17, "rho": 1040,  "cp": 1300, "epsilon": 0.90},
    "pla_3dp":    {"k":   0.13, "rho": 1240,  "cp": 1800, "epsilon": 0.90},
    "wood_pine":  {"k":   0.12, "rho":  500,  "cp": 1700, "epsilon": 0.85},
    "water":      {"k":   0.60, "rho": 1000,  "cp": 4186, "epsilon": 0.95},
    "air":        {"k":   0.026,"rho":   1.225,"cp":1005, "epsilon": 0.0},
}
