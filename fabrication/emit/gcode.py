"""
gcode.py  (fabrication/emit/)

Direct G-code for FDM 3D-printing of stacked-axisymmetric IRs --
Helmholtz resonators, tube stacks, channel arrays. Skips the
slicer when the geometry is regular enough that a slicer would
be overkill.

WARNING -- this is generic Marlin-flavored G-code:
  - default 0.2 mm layer, 0.4 mm nozzle, PLA temps
  - homing + leveling assumed already done
  - center of bed at (x_home, y_home)
  - no firmware-specific gcodes
For anything beyond stacked axisymmetric shapes, use the SCAD
emitter and run it through a real slicer.

License: CC0. Stdlib only.
"""
import math

from ._common import emit_claim, register_parasitic, slugify


# ----- parasitic-reinjection hook (TIER 3 FIX_3_A) -----
# When gcode lays down a tube, the airspace inside it introduces
# acoustic inertance (ρL/A) and compliance (V/(ρc²)) that the IR
# didn't have until the print existed. The reinject pass folds
# these additions back. Caller passes an `emitted` dict like
# {"gcode": {"tubes": [{"length": ..., "cross_section_area": ...,
#                       "id": "..."}, ...]}}.

RHO_AIR = 1.225
C_AIR   = 343.0


@register_parasitic("acoustic", "gcode")
def gcode_acoustic_parasitic(emitted_geometry):
    """For each printed tube, emit one I-element (inertance) and one
    C-element (compliance) tagged with provenance so the ledger can
    trace the additions back to the gcode artifact."""
    additions = []
    for tube in (emitted_geometry or {}).get("tubes", []):
        L = tube["length"]
        A = tube["cross_section_area"]
        V = L * A
        ident = tube.get("id", "anon")
        additions.append({
            "kind":       "store_flow",
            "domain":     "acoustic",
            "param":      RHO_AIR * L / A,
            "provenance": f"reinjected from gcode tube id={ident}",
        })
        additions.append({
            "kind":       "store_effort",
            "domain":     "acoustic",
            "param":      V / (RHO_AIR * C_AIR ** 2),
            "provenance": f"reinjected from gcode tube id={ident}",
        })
    return additions


def _header(name, layer_h, nozzle_temp, bed_temp, x_home, y_home):
    return (
        f"; auto-generated G-code  ({name})\n"
        f"; layer={layer_h}mm  nozzle={nozzle_temp}C  bed={bed_temp}C\n"
        f"M104 S{nozzle_temp}\nM140 S{bed_temp}\n"
        f"M109 S{nozzle_temp}\nM190 S{bed_temp}\n"
        "G21        ; mm\nG90        ; absolute\n"
        "M82        ; absolute extrusion\n"
        "G28        ; home all\n"
        f"G1 X{x_home} Y{y_home} Z0.3 F1500\n"
        "G92 E0\n"
    )


def _trailer():
    return ("G92 E0\nG1 E-2 F1800\nG28 X0 Y0\n"
            "M104 S0\nM140 S0\nM84\n")


def _circle_path(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n + 1)]


def _extrude_to(x, y, e, feed=900):
    return f"G1 X{x:.3f} Y{y:.3f} E{e:.4f} F{feed}\n"


def emit_gcode_axisymmetric(ir, geo_hash, name="part",
                            layer_h=0.2, nozzle_temp=205, bed_temp=60,
                            x_home=110, y_home=110,
                            wall_thickness=1.2, extrude_per_mm=0.04):
    """Treat IR as a stack of cylinders / spheres. Each element
    with geometry containing (length + area/radius) becomes a
    cylinder; an element with only `volume` becomes a sphere of
    equivalent volume rendered as a stack of horizontal rings."""
    out = _header(name, layer_h, nozzle_temp, bed_temp, x_home, y_home)
    z = 0.0
    e = 0.0
    for i, el in enumerate(ir.elements):
        g = el.geometry or {}
        length = g.get("length")
        if length is None:
            if "volume" in g:
                r0 = (3 * g["volume"] / (4 * math.pi)) ** (1 / 3)
                length = 2 * r0
                radius_fn = (lambda h, r=r0:
                             max(0.01, (r * r - (h - r) ** 2) ** 0.5))
            else:
                out += f"; element {i} ({el.kind}) -- skipped (no geometry)\n"
                continue
        else:
            r_const = ((g["area"] / math.pi) ** 0.5 if "area" in g
                       else g.get("radius", 5e-3))
            radius_fn = (lambda h, r=r_const: r)
        n_layers = max(1, int(round(length * 1000 / layer_h)))
        out += f"; element {i} ({el.kind}) z0={z*1000:.2f}mm\n"
        for layer in range(n_layers):
            z_mm = (z + layer * layer_h / 1000) * 1000
            radius_mm = radius_fn(layer * layer_h / 1000) * 1000
            out += f"G1 Z{z_mm:.3f} F600\n"
            path = _circle_path(x_home, y_home, radius_mm)
            for x, y in path:
                e += extrude_per_mm
                out += _extrude_to(x, y, e)
        z += length
    out += _trailer()
    return out


def write_gcode(ir, geo_hash, name="part", out_dir=".", **kw):
    path = f"{out_dir}/{slugify(name)}_{geo_hash}.gcode"
    with open(path, "w") as fp:
        fp.write(emit_gcode_axisymmetric(ir, geo_hash, name, **kw))
    emit_claim("gcode", ir, path, geo_hash,
               params={"name": name,
                       "layer_h_mm": kw.get("layer_h", 0.2)})
    return path
