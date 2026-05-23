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
    """R_rad ≈ 1/(4·ε·σ·T³·A) -- LINEAR APPROXIMATION around T_avg.

    Only valid within ±20 K of the linearization temperature; use
    `radiation_resistance_dynamic` for hot transients."""
    return 1.0 / (4.0 * emissivity * STEFAN_BOLTZMANN
                  * (T_avg_K ** 3) * area_m2)


def radiation_resistance_dynamic(emissivity, area_m2,
                                 T_surface_K, T_ambient_K=293.15):
    """True nonlinear radiation resistance.

      q_rad   = σ·ε·A·(T_s⁴ - T_a⁴)
      R(T_s)  = (T_s - T_a) / q_rad

    Falls back to the linearized form at the midpoint when T_s == T_a
    (avoiding a 0/0 limit) so the simulator can call this every step
    without special-casing equilibrium."""
    if abs(T_surface_K - T_ambient_K) < 1e-6:
        T_avg = 0.5 * (T_surface_K + T_ambient_K)
        return radiation_resistance_linearized(emissivity, area_m2, T_avg)
    q = (STEFAN_BOLTZMANN * emissivity * area_m2
         * (T_surface_K ** 4 - T_ambient_K ** 4))
    return (T_surface_K - T_ambient_K) / q


def build_1d_mesh(length_m, area_m2, material, n_nodes=5):
    """Build a 1-D thermal mesh: N nodes, N-1 R links, N C lumps.

    Returns a dict ready for the lowering pass to expand into N
    Elements + N-1 bonds + junctions. Captures spatial gradients
    that a single R-C lump misses (hot spots near a heater, slow
    soak across a thick wall).
    """
    from .materials import resolve_material
    p = resolve_material(material)
    k   = p["thermal_k"]
    cp  = p["specific_heat"]
    rho = p["density"]

    dx = length_m / n_nodes
    R_segment = dx / (k * area_m2)
    C_node    = rho * cp * area_m2 * dx

    return {
        "nodes": [{"id": f"th_node_{i}", "C": C_node}
                  for i in range(n_nodes)],
        "links": [{"from": f"th_node_{i}", "to": f"th_node_{i+1}",
                   "R":    R_segment}
                  for i in range(n_nodes - 1)],
        "n_nodes":   n_nodes,
        "dx_m":      dx,
        "R_per_seg": R_segment,
        "C_per_node": C_node,
    }


def time_constant(R, C):
    return R * C


# Thermal-domain view onto backends.materials.MATERIALS. Legacy
# callers expect the {"k", "rho", "cp", "epsilon"} key shape.
from .materials import MATERIALS as _M_ALL


def _thermal_view(name):
    p = _M_ALL[name]
    return {
        "k":        p["thermal_k"],
        "rho":      p["density"],
        "cp":       p["specific_heat"],
        "epsilon":  p.get("epsilon", 0.0),
    }


class _ThermalView:
    def __getitem__(self, key):
        return _thermal_view(key)

    def __contains__(self, key):
        return key in _M_ALL

    def get(self, key, default=None):
        return _thermal_view(key) if key in _M_ALL else default


MATERIAL_THERMAL = _ThermalView()
