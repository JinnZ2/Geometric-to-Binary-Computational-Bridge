"""
couplers_piezo.py  (fabrication/)

Piezo coupler physics. Minimum-complexity model that's still
falsifiable -- not a full Mason/KLM equivalent circuit (that's
a wedge for later). Just enough to predict f₀ agreement between
the acoustic and electrical sides of the SAME cavity.

Two regimes:

  (1) WEAK COUPLING (k² < 0.1):
      Piezo loads the cavity slightly; f₀ shift is small.
      f₀_elec ≈ f₀_acoustic · (1 - k_eff² / 2)

  (2) STRONG COUPLING (k² ≥ 0.1):
      Split resonances appear (Butterworth-Van Dyke shape):
        f_series   = f_acoustic
        f_parallel = f_acoustic / √(1 - k_eff²)

k_eff² is derived from:
  - bulk piezo coefficient k_p² (datasheet)
  - geometric coupling factor η (how much of the disc actually
    drives the cavity mode vs. radiates to free space)

License: CC0. Stdlib only.
"""
import math


# Common piezo material constants. CC0 reference values; any real
# build should override with its actual datasheet.
PIEZO_MATERIALS = {
    # k_p² is the planar coupling factor squared
    "PZT-5A":  {"k_p2": 0.300, "rho": 7750, "epsilon_r": 1700},
    "PZT-5H":  {"k_p2": 0.430, "rho": 7800, "epsilon_r": 3400},
    "PZT-4":   {"k_p2": 0.250, "rho": 7500, "epsilon_r": 1300},
    "BaTiO3":  {"k_p2": 0.130, "rho": 5700, "epsilon_r": 1700},
    "quartz":  {"k_p2": 0.008, "rho": 2650, "epsilon_r": 4.5},
}


def piezo_capacitance(area_m2, thickness_m, epsilon_r):
    """C₀ = ε₀ε_r A / t -- the piezo's intrinsic capacitance."""
    EPSILON_0 = 8.854e-12
    return EPSILON_0 * epsilon_r * area_m2 / thickness_m


def coupling_efficiency_geometric(disc_area_m2, cavity_wall_area_m2,
                                  wall_compliance_factor=1.0):
    """
    η: fraction of piezo motion that couples to cavity mode rather
    than wall flex or free-space radiation. First-pass model:
      η ≈ (A_disc / A_wall) · compliance_factor
    Bounded [0, 1].
    """
    eta = (disc_area_m2 / cavity_wall_area_m2) * wall_compliance_factor
    return max(0.0, min(1.0, eta))


def effective_k_squared(material, disc_geometry, cavity_geometry):
    """k_eff² = k_p² · η  (simplest sound model)."""
    mat = PIEZO_MATERIALS[material]
    eta = coupling_efficiency_geometric(
        disc_geometry["area"],
        cavity_geometry["wall_area"],
        cavity_geometry.get("compliance_factor", 1.0),
    )
    return mat["k_p2"] * eta


def predict_split(f_acoustic, k_eff2):
    """
    Returns (regime, f_series, f_parallel) where:
      regime ∈ {"weak", "strong"}
      f_series   = acoustic resonance, unchanged
      f_parallel = upper antiresonance branch
    Weak-coupling case: f_parallel - f_series is small enough that
    the verifier still treats them as one peak with a small shift.
    """
    if k_eff2 < 1e-6:
        return "weak", f_acoustic, f_acoustic
    f_parallel = f_acoustic / math.sqrt(1.0 - k_eff2)
    regime = "strong" if k_eff2 >= 0.1 else "weak"
    return regime, f_acoustic, f_parallel


def expected_agreement_pct(k_eff2):
    """
    How close should acoustic and electrical f₀ measurements be?
    With ideal weak coupling, agreement should be ≥ 99%.
    Strong coupling but correct model: ≥ 95%.
    Beyond that the coupler model itself is the limit.
    """
    if k_eff2 < 0.05:
        return 0.99
    if k_eff2 < 0.15:
        return 0.97
    if k_eff2 < 0.30:
        return 0.95
    return 0.90
