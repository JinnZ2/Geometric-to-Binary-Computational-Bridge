"""
mechanical.py  (fabrication/backends/)

Mechanical translational: effort = F (N), flow = v (m/s).

Geometry / material -> bond-graph parameter

  kind         formula                        physical meaning
  store_flow   m = ρ·V                        inertia (mass, momentum store)
  store_eff    1/k                            compliance (spring, displacement store)
  dissipate    b = F/v                        viscous damping (heat sink)

Springs:
  axial      k = E·A / ℓ                   (rod in tension/compression)
  cantilever k = 3 E I / ℓ³                (rectangular beam, end-loaded)
                 I = b·h³ / 12

The mechanical port is the dual of acoustic / fluidic. Resonance
of a (mass m, compliance c=1/k) pair:
    f₀ = (1/2π)·√(k/m)

License: CC0. Stdlib only.
"""
import math


# Density (kg/m³) and Young's modulus E (Pa) for common materials.
# CC0 reference values; override with datasheet for actual stock.
MATERIAL_TABLE = {
    "aluminum":  {"rho": 2700, "E": 69e9},
    "steel":     {"rho": 7850, "E": 200e9},
    "stainless": {"rho": 8000, "E": 193e9},
    "brass":     {"rho": 8500, "E": 100e9},
    "copper":    {"rho": 8960, "E": 117e9},
    "titanium":  {"rho": 4500, "E": 116e9},
    "wood_pine": {"rho":  500, "E": 9e9},
    "wood_oak":  {"rho":  750, "E": 11e9},
    "abs":       {"rho": 1050, "E": 2.3e9},
    "pla":       {"rho": 1240, "E": 3.5e9},
    "petg":      {"rho": 1270, "E": 2.1e9},
    "silicon":   {"rho": 2330, "E": 130e9},
    "polymer_paper": {"rho": 800, "E": 4e9},  # speaker cone composite
}


# ----- inertia ----------------------------------------------------

def rod_mass(length_m, area_m2, material):
    """Mass of a uniform rod / column. m = ρ·ℓ·A."""
    rho = MATERIAL_TABLE[material]["rho"]
    return rho * length_m * area_m2


def disc_mass(radius_m, thickness_m, material):
    """Mass of a flat disc. m = ρ·π·r²·t."""
    rho = MATERIAL_TABLE[material]["rho"]
    return rho * math.pi * radius_m**2 * thickness_m


# ----- compliance (= 1/k) -----------------------------------------

def axial_spring_constant(length_m, area_m2, material):
    """k = E·A / ℓ for a rod in axial loading."""
    E = MATERIAL_TABLE[material]["E"]
    return E * area_m2 / length_m


def cantilever_spring_constant(length_m, width_m, thickness_m, material):
    """k = 3·E·I / ℓ³ for an end-loaded rectangular cantilever.
       I = b·h³ / 12."""
    E = MATERIAL_TABLE[material]["E"]
    I = width_m * thickness_m**3 / 12.0
    return 3.0 * E * I / length_m**3


def compliance_from_stiffness(k_N_per_m):
    """c = 1/k -- bond-graph store_effort parameter."""
    return 1.0 / k_N_per_m


# ----- dissipation -----------------------------------------------

def viscous_damping_plate(area_m2, gap_m, mu=1.81e-5):
    """Squeeze-film viscous damping under a plate moving normal to
    a parallel surface. F = b·v, b ≈ μ·A / gap.
    First-pass model; real geometry (perforations, edges) shifts b."""
    return mu * area_m2 / gap_m


# ----- composite -------------------------------------------------

def resonance_freq_Hz(mass_kg, compliance_m_per_N):
    """f = 1/(2π·√(m·c)) = (1/2π)·√(k/m)."""
    return 1.0 / (2.0 * math.pi * math.sqrt(mass_kg * compliance_m_per_N))


def damping_ratio(damping_b, mass_kg, compliance_m_per_N):
    """ζ = b / (2·√(m/c)) = b / (2·√(m·k))."""
    k = 1.0 / compliance_m_per_N
    return damping_b / (2.0 * math.sqrt(mass_kg * k))


def with_tolerance(value, frac=0.05):
    return value, (value * (1 - frac), value * (1 + frac))
