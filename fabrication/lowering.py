"""
lowering.py  (fabrication/)

Geometric primitive graph -> SubstrateIR. One pass per target domain.

The LOWER table is intentionally narrower than
substrate_ir.GEOMETRY_TO_PARAMETER: it only covers domains for which
we ship working backend code in backends/. Adding a new domain =
add one row here + one file in backends/.

License: CC0. Stdlib only (imports siblings).
"""
from .substrate_ir import SubstrateIR, Element, BondPort
from .backends import (acoustic, fluidic, electrical as elec,
                       mechanical as mech, thermal as therm,
                       magnetic as mag)
from .backends.materials import _expand_material


DOMAIN_PORTS = {
    "acoustic":   BondPort("acoustic",   "Q",    "P"),
    "fluidic":    BondPort("fluidic",    "mdot", "P"),
    "electrical": BondPort("electrical", "I",    "V"),
    "mechanical": BondPort("mechanical", "v",    "F"),
    "thermal":    BondPort("thermal",    "qdot", "dT"),
    "magnetic":   BondPort("magnetic",   "PhiB", "MMF"),
}


# Geometric primitive -> (kind, param-fn).
# The param-fn closes over the backend module so adding a domain
# means adding rows here without touching the rest of the file.
LOWER = {
    ("acoustic", "channel"):  ("dissipate",
        lambda g: acoustic.viscous_loss(g["length"], g["radius"])),
    ("acoustic", "tube"):     ("store_flow",
        lambda g: acoustic.inertance(g["length"], g["area"])),
    ("acoustic", "cavity"):   ("store_effort",
        lambda g: acoustic.compliance(g["volume"])),
    ("acoustic", "neck"):     ("store_flow",
        lambda g: acoustic.inertance(g["length"], g["area"])),

    ("fluidic",  "channel"):  ("dissipate",
        lambda g: fluidic.channel_resistance(g["length"], g["radius"], g["fluid"])),
    ("fluidic",  "tube"):     ("store_flow",
        lambda g: fluidic.channel_inertance(g["length"], g["area"], g["fluid"])),
    ("fluidic",  "reservoir"):("store_effort",
        lambda g: fluidic.reservoir_compliance(g["volume"], g["bulk_modulus"])),

    # ----- electrical: geometry primitives -----
    ("electrical", "loop"):     ("store_flow",
        lambda g: elec.air_core_loop_inductance(g["radius"],
                                                g["wire_radius"])),
    ("electrical", "solenoid"): ("store_flow",
        lambda g: elec.solenoid_inductance(g["turns"], g["length"],
                                           g["area"], g.get("mu_r", 1.0))),
    ("electrical", "gap"):      ("store_effort",
        lambda g: elec.parallel_plate_capacitance(g["area"], g["gap"],
                                                  g.get("er", 1.0))),
    ("electrical", "cyl_cap"):  ("store_effort",
        lambda g: elec.cylindrical_capacitance(g["inner_r"], g["outer_r"],
                                               g["length"],
                                               g.get("er", 1.0))),
    ("electrical", "wire"):     ("dissipate",
        lambda g: elec.wire_resistance(g["length"], g["area"], g["rho"])),

    # ----- electrical: explicit breadboard values -----
    ("electrical", "R_value"):  ("dissipate",     lambda g: g["R"]),
    ("electrical", "L_value"):  ("store_flow",    lambda g: g["L"]),
    ("electrical", "C_value"):  ("store_effort",  lambda g: g["C"]),

    # ----- mechanical: geometry primitives -----
    ("mechanical", "rod"):     ("store_flow",
        lambda g: mech.rod_mass(g["length"], g["area"], g["material"])),
    ("mechanical", "disc"):    ("store_flow",
        lambda g: mech.disc_mass(g["radius"], g["thickness"], g["material"])),
    ("mechanical", "axial_spring"): ("store_effort",
        lambda g: mech.compliance_from_stiffness(
            mech.axial_spring_constant(g["length"], g["area"], g["material"]))),
    ("mechanical", "cantilever"):   ("store_effort",
        lambda g: mech.compliance_from_stiffness(
            mech.cantilever_spring_constant(g["length"], g["width"],
                                            g["thickness"], g["material"]))),
    ("mechanical", "viscous_plate"):("dissipate",
        lambda g: mech.viscous_damping_plate(g["area"], g["gap"],
                                             g.get("mu", 1.81e-5))),

    # ----- mechanical: explicit lab values -----
    ("mechanical", "mass_value"):       ("store_flow",
        lambda g: g["m"]),
    ("mechanical", "compliance_value"): ("store_effort",
        lambda g: g["c"]),
    ("mechanical", "damping_value"):    ("dissipate",
        lambda g: g["b"]),

    # ----- thermal: geometry primitives -----
    ("thermal", "wall"):                ("dissipate",
        lambda g: therm.conduction_resistance(
            g["length"], g["area"], g["k"])),
    ("thermal", "block"):               ("store_effort",
        lambda g: therm.storage_capacity(
            g["volume"], g["density"], g["cp"])),
    ("thermal", "convective_surface"):  ("dissipate",
        lambda g: therm.convection_resistance(g["h"], g["area"])),
    ("thermal", "radiative_surface"):   ("dissipate",
        lambda g: therm.radiation_resistance_linearized(
            g["epsilon"], g["area"], g.get("T_avg_K", 300.0))),

    # ----- thermal: explicit lab values -----
    ("thermal", "R_value"):             ("dissipate",
        lambda g: g["R_th"]),
    ("thermal", "C_value"):             ("store_effort",
        lambda g: g["C_th"]),

    # ----- thermal: nonlinear radiation (TIER 2 FIX_2_A) -----
    # Parameter is a dict; the simulator calls the func at runtime
    # with the current surface temperature to get R(T_s).
    ("thermal", "radiative_surface"):   ("dissipate_dynamic",
        lambda g: {
            "func":       "radiation_resistance_dynamic",
            "epsilon":    g["epsilon"],
            "area":       g["area"],
            "T_ambient":  g.get("T_ambient", 293.15),
        }),

    # ----- thermal: 1-D mesh (TIER 2 FIX_2_C) -----
    # `mesh_expand` kind tells a richer lowering pass to inflate
    # this single node into N R-C elements; the existing lower()
    # records the spec dict as the parameter so a future
    # mesh_expand pass can act on it.
    ("thermal", "solid_wall"):          ("mesh_expand",
        lambda g: therm.build_1d_mesh(
            g["length"], g["area"], g["material"],
            g.get("n_nodes", 5))),

    # ----- magnetic: nonlinear reluctance (TIER 2 FIX_2_B) -----
    ("magnetic", "core_segment"):       ("dissipate_dynamic",
        lambda g: {
            "func":     "reluctance_nonlinear",
            "length":   g["length"],
            "area":     g["area"],
            "material": g["material"],
        }),

    # ----- magnetic: geometry primitives -----
    ("magnetic", "gap"):                ("dissipate",
        lambda g: mag.gap_reluctance(g["gap"], g["area"])),
    ("magnetic", "core_leg"):           ("dissipate",
        lambda g: mag.core_reluctance(g["length"], g["area"], g["mu_r"])),
    # A coil's contribution to the magnetic IR is N² (turns-squared);
    # the eventual inductance is N² / ℛ_total, computed at claim time.
    # See ("electrical-magnetic", "coil") for the proper transducer
    # entry that couples copper loss + leakage + core loss across
    # both domains; the magnetic-only entry above is preserved for
    # smokes and legacy callers.
    ("magnetic", "coil"):               ("store_flow",
        lambda g: g["turns"] ** 2),

    # ----- electrical <-> magnetic transducer (coil as TF) -----
    # Couples electrical and magnetic IRs through one N-modulus
    # transformer. Parameter is a DICT carrying:
    #   modulus_N            turns ratio (gyrator-like)
    #   winding_resistance   copper I²R loss [Ω]
    #   leakage_inductance   imperfect coupling [H]
    #   core_eddy_R          eddy-loss as parallel R [Ω]
    # Simulators that handle dict parameters get the full physics;
    # legacy paths that only inspect kind="transformer" can read
    # modulus_N from the dict.
    ("electrical-magnetic", "coil"):    ("transformer",
        lambda g: {
            "modulus_N":          g["turns"],
            "winding_resistance": _wire_resistance(g),
            "leakage_inductance": _leakage_estimate(g),
            "core_eddy_R":        g.get("core_eddy_R", 1e4),
        }),
}


# ----- helpers for the electrical-magnetic transducer entry -----

import math as _math


def _wire_resistance(g):
    """R = ρ · L_wire / A_wire.  Copper at 20°C: 1.68e-8 Ω·m.

    L_wire = turns × mean turn length (caller can override via
    `mean_turn_length`; otherwise 2π·coil_radius).
    A_wire = π·wire_radius² (caller can override).
    """
    rho_cu = g.get("wire_rho", 1.68e-8)
    mean_turn = g.get("mean_turn_length",
                      2 * _math.pi * g.get("coil_radius", 0.01))
    L_wire = g["turns"] * mean_turn
    A_wire = _math.pi * g.get("wire_radius", 0.0005) ** 2
    return rho_cu * L_wire / A_wire


def _leakage_estimate(g):
    """Coupling coefficient k typically 0.95–0.99 for tight cores.
    Leakage L_leak ≈ (1 - k²) · L_self where L_self = N² / ℛ."""
    k = g.get("coupling_coefficient", 0.97)
    L_self = (g["turns"] ** 2) / g.get("reluctance", 1e6)
    return (1 - k * k) * L_self


def lower(geometric_graph, domain: str) -> SubstrateIR:
    """One pass: shape -> substrate IR. No domain-specific code path.

    Material expansion happens BEFORE the LOWER lambda runs, so a
    geometry dict carrying `{"material": "steel", ...}` is functionally
    interchangeable with one carrying explicit `{"youngs": 200e9,
    "density": 7850, ...}` -- the lambda sees both. Explicit numeric
    overrides always win over the registry default.
    """
    ir = SubstrateIR(domain=domain)
    port = DOMAIN_PORTS[domain]
    for node in geometric_graph.nodes:
        key = (domain, node.primitive)
        if key not in LOWER:
            raise ValueError(f"No lowering for {key}; add to LOWER table.")
        kind, fn = LOWER[key]
        geom = _expand_material(node.geometry)
        param = fn(geom)
        ir.elements.append(Element(kind, geom, param, port, port))
    ir.topology = list(geometric_graph.edges)
    return ir
