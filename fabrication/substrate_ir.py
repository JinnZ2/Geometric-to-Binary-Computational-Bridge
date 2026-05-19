"""
substrate_ir.py  (fabrication/)

Bond-graph IR. Every substrate is just a different MEDIUM for the
same flow. What changes: the conserved quantity and its dual.

  substrate    flow (through)    effort (across)    impedance
  ───────────  ────────────────  ─────────────────  ────────────
  electrical   current  I        voltage  V         Z = V/I
  mechanical   force    F        velocity v         Z = F/v
  acoustic     vol.flow Q        pressure P         Z = P/Q
  fluidic      mass.flow ṁ       pressure P         Z = P/ṁ
  optical      photon flux Φ     field amplitude E  Z = E/Φ
  magnetic     flux     Φ_B      MMF   ℱ            Z = ℱ/Φ_B
  thermal      heat.flow q̇       temp diff ΔT       Z = ΔT/q̇

GEOMETRY_TO_PARAMETER is the WIDE catalog -- entries for every domain
this repo cares about. The narrower lowering.LOWER table only covers
the domains that also have concrete backend code in backends/. Both
exist intentionally: the wide catalog is the architectural reference;
the narrow table is what the lowering pass actually executes.

License: CC0. Stdlib only.
"""
from dataclasses import dataclass, field
from typing import Literal, Callable, Optional


Domain = Literal[
    "electrical", "mechanical", "acoustic",
    "fluidic", "optical", "magnetic", "thermal"
]


@dataclass(frozen=True)
class BondPort:
    """One port = (flow var, effort var) in a chosen domain."""
    domain: Domain
    flow_name: str          # e.g. "I", "F", "Q", "Φ"
    effort_name: str        # e.g. "V", "v", "P", "E"


@dataclass(frozen=True)
class Element:
    """
    Substrate-agnostic primitive.
    Geometry sets the parameter; domain sets the units.
    """
    kind: Literal[
        "store_flow",     # inductor / mass / inertance / inductance
        "store_effort",   # capacitor / spring / compliance
        "dissipate",      # resistor / damper / acoustic loss
        "transform",      # transformer / lever / horn / lens
        "gyrate",         # gyrator -- cross-domain coupler
        "source_flow",
        "source_effort",
    ]
    geometry: dict        # e.g. {"length": 0.10, "area": 1e-4}
    parameter: float      # L, C, R, ratio -- computed FROM geometry
    port_a: BondPort
    port_b: Optional[BondPort] = None


@dataclass
class SubstrateIR:
    """The lowered graph -- same shape, different domain."""
    domain: Domain
    elements: list[Element] = field(default_factory=list)
    topology: list[tuple[int, int]] = field(default_factory=list)
    # element indices forming edges


# -------------------------------------------------------------
# Geometry -> parameter, per domain.
# This is the ONLY substrate-specific physics. Everything else
# is topology, which is invariant.
# -------------------------------------------------------------

GEOMETRY_TO_PARAMETER: dict[tuple[str, str], Callable] = {

    # ----- electrical -----
    ("electrical", "store_flow"):    # inductor: L = μ₀ N² A / ℓ
        lambda g: 4e-7 * 3.14159 * g["turns"]**2 * g["area"] / g["length"],
    ("electrical", "store_effort"):  # capacitor: C = ε₀ε_r A / d
        lambda g: 8.854e-12 * g.get("er", 1.0) * g["area"] / g["gap"],
    ("electrical", "dissipate"):     # resistor: R = ρ ℓ / A
        lambda g: g["rho"] * g["length"] / g["area"],

    # ----- mechanical -----
    ("mechanical", "store_flow"):    # mass: m = ρ V
        lambda g: g["density"] * g["volume"],
    ("mechanical", "store_effort"):  # spring: 1/k = ℓ / (E A)  (axial)
        lambda g: g["length"] / (g["youngs"] * g["area"]),
    ("mechanical", "dissipate"):     # damper coefficient from geometry
        lambda g: g["mu"] * g["area"] / g["gap"],

    # ----- acoustic -----
    ("acoustic", "store_flow"):      # inertance: M = ρ ℓ / A
        lambda g: 1.225 * g["length"] / g["area"],
    ("acoustic", "store_effort"):    # compliance: C = V / (ρ c²)
        lambda g: g["volume"] / (1.225 * 343.0**2),

    # ----- fluidic (laminar) -----
    ("fluidic", "dissipate"):        # Hagen-Poiseuille: R = 8μℓ/(πr⁴)
        lambda g: 8 * g["mu"] * g["length"] / (3.14159 * g["radius"]**4),
    ("fluidic", "store_flow"):       # fluid inertance: I = ρℓ/A
        lambda g: g["density"] * g["length"] / g["area"],

    # ----- optical -----
    ("optical", "store_effort"):     # Fabry-Pérot: τ = 2nℓ/c
        lambda g: 2 * g["n"] * g["length"] / 3e8,

    # ----- magnetic -----
    ("magnetic", "dissipate"):       # reluctance: ℛ = ℓ/(μA)
        lambda g: g["length"] / (g["mu"] * g["area"]),

    # ----- thermal -----
    ("thermal", "dissipate"):        # R_th = ℓ / (k A)
        lambda g: g["length"] / (g["k"] * g["area"]),
    ("thermal", "store_effort"):     # C_th = ρ c_p V
        lambda g: g["density"] * g["cp"] * g["volume"],
}
