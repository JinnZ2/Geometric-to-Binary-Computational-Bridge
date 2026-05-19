"""
spice_electrical.py  (fabrication/emit/)

Direct SPICE emit for electrical IR. Mirrors emit_spice() in the
acoustic backend but uses real component letters (L, C, R) and
adds an AC analysis tuned to typical electronics ranges.

License: CC0. Stdlib only.
"""


def emit_spice_electrical(ir, source_amp=1.0,
                          fmin=10.0, fmax=1e6, points=200):
    """
    Chain topology: node 0 = ground, source at node 1, then elements
    in series along increasing nodes. Caps go to ground.
    """
    lines = [f"* auto-generated electrical IR (n_elements={len(ir.elements)})"]
    node = 1
    src_node = 1
    for i, el in enumerate(ir.elements):
        n_in, n_out = node, node + 1
        if el.kind == "store_flow":      # inductor in series
            lines.append(f"L{i} {n_in} {n_out} {el.parameter:.6e}")
        elif el.kind == "store_effort":  # capacitor shunt to ground
            lines.append(f"C{i} {n_in} 0 {el.parameter:.6e}")
            n_out = n_in
        elif el.kind == "dissipate":     # resistor in series
            lines.append(f"R{i} {n_in} {n_out} {el.parameter:.6e}")
        node = n_out
    lines.insert(1, f"V1 {src_node} 0 AC {source_amp}")
    lines.append(f".AC DEC {points} {fmin} {fmax}")
    lines.append(f".PRINT AC V({node}) I(V1)")
    lines.append(".END")
    return "\n".join(lines)
