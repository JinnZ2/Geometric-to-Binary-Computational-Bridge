"""
lowering.py  (fabrication/)

Geometric primitive graph -> SubstrateIR. One pass per target domain.

The LOWER table is intentionally narrower than
substrate_ir.GEOMETRY_TO_PARAMETER: it only covers domains for which
we ship working backend code in backends/. Adding a new domain =
add one row here + one file in backends/.

License: CC0. Stdlib only (imports siblings).
"""
from substrate_ir import SubstrateIR, Element, BondPort
from backends import acoustic, fluidic, electrical as elec


DOMAIN_PORTS = {
    "acoustic":   BondPort("acoustic",   "Q",    "P"),
    "fluidic":    BondPort("fluidic",    "mdot", "P"),
    "electrical": BondPort("electrical", "I",    "V"),
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
}


def lower(geometric_graph, domain: str) -> SubstrateIR:
    """One pass: shape -> substrate IR. No domain-specific code path."""
    ir = SubstrateIR(domain=domain)
    port = DOMAIN_PORTS[domain]
    for node in geometric_graph.nodes:
        key = (domain, node.primitive)
        if key not in LOWER:
            raise ValueError(f"No lowering for {key}; add to LOWER table.")
        kind, fn = LOWER[key]
        param = fn(node.geometry)
        ir.elements.append(Element(kind, node.geometry, param, port, port))
    ir.topology = list(geometric_graph.edges)
    return ir
