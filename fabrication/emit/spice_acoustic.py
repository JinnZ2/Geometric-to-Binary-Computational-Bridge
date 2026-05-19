"""
spice_acoustic.py  (fabrication/emit/)

Pre-fab simulation. Uses the electrical-acoustic analogy so we
can run the design in ngspice BEFORE cutting anything.

  inertance M  ->  inductor  L = M
  compliance C ->  capacitor C = C
  viscous R    ->  resistor  R = R

Pressure ≡ voltage, volume-flow ≡ current.

License: CC0. Stdlib only.
"""


def emit_spice(ir, source_amp=1.0, fmin=20, fmax=20000, points=200):
    lines = [f"* auto-generated from SubstrateIR (domain={ir.domain})"]
    node = 1
    for i, el in enumerate(ir.elements):
        n_in, n_out = node, node + 1
        if el.kind == "store_flow":
            lines.append(f"L{i} {n_in} {n_out} {el.parameter:.6e}")
        elif el.kind == "store_effort":
            lines.append(f"C{i} {n_in} 0 {el.parameter:.6e}")  # shunt to ground
            n_out = n_in
        elif el.kind == "dissipate":
            lines.append(f"R{i} {n_in} {n_out} {el.parameter:.6e}")
        node = n_out
    lines.insert(1, f"V1 1 0 AC {source_amp}")
    lines.append(f".AC DEC {points} {fmin} {fmax}")
    lines.append(".END")
    return "\n".join(lines)
