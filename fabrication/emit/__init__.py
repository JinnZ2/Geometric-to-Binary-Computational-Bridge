"""
fabrication/emit/

SubstrateIR -> physical fab artifact. Every emit_* returns BYTES
or TEXT that goes to a real machine (or a real hand).

Currently shipped:

  Format-spec emitters (one IR -> one artifact):
    stl.py             3D-print / CNC shells (mechanical, acoustic)
    svg_mask.py        laser-cut / photolitho mask (fluidic, optical)
    spice_acoustic.py  pre-fab simulation, acoustic-electric analogy
    spice_electrical.py SPICE netlist from an electrical IR
    scad.py            OpenSCAD parametric source (any 3D geometry)
    kicad.py           KiCad .net (electrical)
    gcode.py           Marlin G-code (stacked axisymmetric)
    coil_schedule.py   coil winding instructions + stepper table
    loom.py            ASCII grid topology (field-runnable fallback)
    svg_dxf.py         SVG + DXF masks for laser/CAM tools

The dispatcher below (`emit_all`) routes a single IR through
every applicable emitter for its domain, and each emitter
writes a sibling claim to CLAIM_TABLE.fab.json so the verifier
can later confirm: "the artifact I'm measuring is the artifact
this IR produced."

License: CC0. Stdlib only.
"""
from .scad           import write_scad
from .kicad          import write_kicad
from .gcode          import write_gcode
from .coil_schedule  import write_coil_schedule
from .loom           import write_loom
from .svg_dxf        import write_svg_dxf


EMIT_BY_DOMAIN = {
    "electrical": [
        ("kicad", write_kicad),
        ("loom",  write_loom),
    ],
    "mechanical": [
        ("scad",  write_scad),
        ("gcode", write_gcode),
        ("loom",  write_loom),
    ],
    "acoustic": [
        ("scad",  write_scad),
        ("gcode", write_gcode),
        ("loom",  write_loom),
    ],
    "fluidic": [
        ("scad",  write_scad),
        ("loom",  write_loom),
    ],
    "thermal": [
        ("scad",  write_scad),
        ("loom",  write_loom),
    ],
    "magnetic": [
        ("coil_schedule", write_coil_schedule),
        ("loom",          write_loom),
    ],
}


_COIL_OPT_KEYS = ("bobbin_length_m", "wire_dia_m",
                  "wire_gauge", "pack_factor")


def emit_all(ir, geo_hash, name="part", out_dir=".", **opts):
    """Run every emitter applicable to the IR's domain.

    Returns dict {format_label: path_or_(path_txt, path_csv)} or
    {format_label: "ERROR: <message>"} on per-emitter failure.
    Unknown domains fall back to the loom emitter only.
    """
    artifacts = {}
    targets = EMIT_BY_DOMAIN.get(ir.domain, [("loom", write_loom)])
    for label, fn in targets:
        try:
            if label == "coil_schedule":
                kw = {k: v for k, v in opts.items()
                      if k in _COIL_OPT_KEYS}
                artifacts[label] = fn(ir, geo_hash, name=name,
                                      out_dir=out_dir, **kw)
            else:
                artifacts[label] = fn(ir, geo_hash, name=name,
                                      out_dir=out_dir)
        except Exception as e:
            artifacts[label] = f"ERROR: {e}"
    return artifacts
