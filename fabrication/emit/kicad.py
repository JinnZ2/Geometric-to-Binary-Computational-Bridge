"""
kicad.py  (fabrication/emit/)

KiCad legacy netlist (.net) emitter. Pure text; loads in
eeschema; Gerbers exported downstream go to any PCB house.

Mapping (matches emit_spice_electrical's topology by construction
so SPICE pre-fab simulation and PCB layout describe the same
circuit):

  store_flow  (L) -> Inductor_SMD:L_0805
  store_effort (C) -> Capacitor_SMD:C_0805   (shunt to GND)
  dissipate   (R) -> Resistor_SMD:R_0805

License: CC0. Stdlib only.
"""
from ._common import emit_claim, slugify


def _component_line(ref, value, footprint):
    return (f"  (comp (ref {ref})\n"
            f"    (value {value})\n"
            f"    (footprint {footprint}))\n")


def _net_block(net_name, code, pins):
    s = f"  (net (code {code}) (name \"{net_name}\")\n"
    for ref, pin in pins:
        s += f"    (node (ref {ref}) (pin {pin}))\n"
    s += "  )\n"
    return s


def emit_kicad(ir, geo_hash, name="circuit"):
    if ir.domain != "electrical":
        raise ValueError("KiCad emitter requires an electrical IR.")
    out  = "(export (version D)\n"
    out += f"  (design (source \"{name}\"))\n"
    out += "  (components\n"
    nets = {1: [], 0: []}      # net 0 = GND; net 1 = source side
    node = 1
    for i, el in enumerate(ir.elements):
        n_in, n_out = node, node + 1
        if el.kind == "store_flow":
            ref = f"L{i+1}"
            val = f"{el.parameter:.3e}H"
            fp  = "Inductor_SMD:L_0805"
            nets.setdefault(n_in,  []).append((ref, "1"))
            nets.setdefault(n_out, []).append((ref, "2"))
            node = n_out
        elif el.kind == "store_effort":
            ref = f"C{i+1}"
            val = f"{el.parameter:.3e}F"
            fp  = "Capacitor_SMD:C_0805"
            nets.setdefault(n_in, []).append((ref, "1"))
            nets[0].append((ref, "2"))
        elif el.kind == "dissipate":
            ref = f"R{i+1}"
            val = f"{el.parameter:.3e}ohm"
            fp  = "Resistor_SMD:R_0805"
            nets.setdefault(n_in,  []).append((ref, "1"))
            nets.setdefault(n_out, []).append((ref, "2"))
            node = n_out
        else:
            continue
        out += _component_line(ref, val, fp)
    # source connector
    out += _component_line("J1", "SRC",
                           "Connector_Generic:Conn_01x02")
    nets[1].append(("J1", "1"))
    nets[0].append(("J1", "2"))
    out += "  )\n  (nets\n"
    for code, pins in sorted(nets.items()):
        net_name = "GND" if code == 0 else f"N{code}"
        out += _net_block(net_name, code, pins)
    out += "  )\n)\n"
    return out


def write_kicad(ir, geo_hash, name="circuit", out_dir="."):
    path = f"{out_dir}/{slugify(name)}_{geo_hash}.net"
    with open(path, "w") as fp:
        fp.write(emit_kicad(ir, geo_hash, name))
    emit_claim("kicad", ir, path, geo_hash, params={"name": name})
    return path
