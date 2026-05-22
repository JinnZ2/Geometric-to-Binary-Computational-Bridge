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


# `Domain` is kept as Literal for the original substrates but
# multi-substrate hyphenated names ("electrical-magnetic", ...) are
# now used by transducer couplers; we relax the runtime type to `str`
# on the dataclass fields so those names parse without escape hatches.
Domain = Literal[
    "electrical", "mechanical", "acoustic",
    "fluidic", "optical", "magnetic", "thermal"
]


JunctionKind = Literal["0", "1"]      # 0=shared effort, 1=shared flow
Causality    = Literal["effort_in", "flow_in"]


@dataclass(frozen=True)
class BondPort:
    """One port = (flow var, effort var) in a chosen domain.

    Optional `junction_id` lets a port name the junction it connects
    to (set by the lowering pass or by an SCAP run). Optional
    `causality` is set by `passes.causality.assign_causality`.
    """
    domain: str
    flow_name: str
    effort_name: str
    junction_id: Optional[str] = None
    causality: Optional[Causality] = None


@dataclass(frozen=True)
class Element:
    """
    Substrate-agnostic primitive.
    `kind` is a str (was Literal); a registry of valid kinds is
    documented below but not enforced at construction time so future
    backends can extend it without editing this file.

    Known kinds:
      store_flow       inductor / mass / inertance / inductance
      store_effort     capacitor / spring / compliance / tank
      dissipate        resistor / damper / acoustic loss
      dissipate_dynamic state-dependent R(state)  (e.g. T^4 radiation,
                       μ(B) reluctance)
      transform        transformer / lever / horn / lens
      gyrate           cross-domain gyrator coupler
      transformer      cross-domain TF coupler (e.g. coil N:1)
      mesh_expand      geometry that lowers into N sub-elements
      source_flow      source of flow
      source_effort    source of effort

    `parameter` may be a scalar OR a dict (e.g. transformers carry
    modulus + leakage + winding resistance + core loss together).
    """
    kind: str
    geometry: dict
    parameter: object
    port_a: BondPort
    port_b: Optional[BondPort] = None
    is_transducer: bool = False     # NEW: cross-substrate flag


@dataclass(frozen=True)
class Junction:
    """Bond-graph junction node.

    0-junction: all bonds share effort
                (parallel circuits, force balance)
    1-junction: all bonds share flow
                (series circuits, velocity balance)
    """
    id: str
    kind: JunctionKind
    domain: str


@dataclass
class Bond:
    """Power bond between an Element port and a Junction.
    Causality is set by `passes.causality.assign_causality`."""
    element_idx: int
    port: Literal["a", "b"]
    junction_id: str
    causality: Optional[Causality] = None


@dataclass
class SubstrateIR:
    """The lowered graph -- same shape, different domain.

    `junctions` + `bonds` carry the bond-graph topology (added in
    TIER 1 of the structural-repair wedge). `topology` predates them
    and is preserved for backward compatibility; legacy code that
    only fills `topology` continues to work unchanged.
    """
    domain: str
    elements: list = field(default_factory=list)
    junctions: list = field(default_factory=list)
    bonds: list = field(default_factory=list)
    topology: list = field(default_factory=list)
    # element indices forming legacy edges

    def add_junction(self, jid, kind, domain):
        if any(j.id == jid for j in self.junctions):
            raise ValueError(f"duplicate junction id: {jid}")
        self.junctions.append(Junction(jid, kind, domain))

    def add_bond(self, element_idx, port, junction_id):
        if not any(j.id == junction_id for j in self.junctions):
            raise ValueError(f"unknown junction: {junction_id}")
        self.bonds.append(Bond(element_idx, port, junction_id))


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
