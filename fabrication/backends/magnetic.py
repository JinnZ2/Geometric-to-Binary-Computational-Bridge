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


# ----- nonlinear saturation model (TIER 2 FIX_2_B) -----

# tanh saturation parameters per material. provenance per entry.
SATURATION_MODELS = {
    "silicon_steel":  {"B_sat": 1.8, "mu_r_initial": 4000.0,
                       # M-19 grain-oriented nominal
                       },
    "ferrite_3C90":   {"B_sat": 0.4, "mu_r_initial": 2300.0,
                       # 3C90 typical
                       },
    "ferrite_77":     {"B_sat": 0.4, "mu_r_initial": 2000.0,
                       # 77 typical
                       },
    "iron_powder_26": {"B_sat": 1.4, "mu_r_initial": 75.0,
                       # iron-powder cores, nominal
                       },
    "mu_metal":       {"B_sat": 0.75, "mu_r_initial": 80000.0,
                       # mumetal nominal
                       },
    "air":            {"B_sat": float("inf"), "mu_r_initial": 1.0},
}


def mu_effective(material, H_A_per_m):
    """Effective permeability with tanh saturation.

      B(H)  = B_sat · tanh(μ_r_initial · μ₀ · H / B_sat)
      μ_eff = dB/dH = μ_r_initial·μ₀ · sech²(arg)
                    = μ_r_initial·μ₀ · (1 - tanh²(arg))

    Air / vacuum (B_sat = ∞) returns the static μ_r_initial·μ₀.
    """
    m = SATURATION_MODELS.get(material, SATURATION_MODELS["air"])
    mu_init = m["mu_r_initial"] * MU_0
    if m["B_sat"] == float("inf"):
        return mu_init
    arg = mu_init * H_A_per_m / m["B_sat"]
    return mu_init * (1.0 - math.tanh(arg) ** 2)


def reluctance_nonlinear(length_m, area_m2, material, H_A_per_m):
    """ℛ(H) = ℓ / (μ_eff(H) · A).

    For a simulator: at each step, compute H from the current MMF
    state, look up μ_eff, recompute ℛ -- this is the "dissipate_dynamic"
    element kind in the IR. When μ becomes B-dependent the storage
    accounting on the I-element must switch from energy to co-energy
    W' = ∫λ·di; flagged as `fab::magnetic::coenergy` claim."""
    return length_m / (mu_effective(material, H_A_per_m) * area_m2)
