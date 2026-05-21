"""
scad.py  (fabrication/emit/)

OpenSCAD parametric emitter -- text-based, human-readable,
version-controllable. Tweakable in any text editor and exportable
to STL by any slicer.

Heuristic geometry mapping from the IR's element.geometry dict:

  cavity (volume)                   -> sphere
  channel / tube (length, area)     -> cylinder
  channel (length, radius)          -> cylinder
  cantilever (length, width,        -> rectangular box
              thickness)

Elements stack along the Z axis in IR order. For anything more
than that, edit the .scad by hand.

License: CC0. Stdlib only.
"""
import math

from ._common import emit_claim, slugify


def _scad_header(name, params):
    head = f"// auto-generated from IR  ({name})\n"
    head += "// edit parameters below, re-export STL\n\n"
    for k, v in params.items():
        head += f"{k} = {v};\n"
    head += "\n$fn = 64;\n\n"
    return head


def _scad_cavity(volume_m3, idx, z):
    return (f"// cavity {idx} (volume-derived radius)\n"
            f"radius_cavity_{idx} = "
            f"pow(3*{volume_m3}/(4*PI), 1/3);\n"
            f"translate([0,0,{z}]) "
            f"sphere(r=radius_cavity_{idx});\n")


def _scad_cylinder(name, idx, length, radius, z):
    return (f"// {name} {idx}\n"
            f"translate([0,0,{z}]) "
            f"cylinder(h={length}, r={radius}, center=false);\n")


def _scad_box(name, idx, L, W, H, z):
    return (f"// {name} {idx}\n"
            f"translate([0,0,{z}]) cube([{L},{W},{H}], center=false);\n")


def emit_scad(ir, geo_hash, name="part"):
    params = {"PI": math.pi}
    body = ""
    z = 0.0
    for i, el in enumerate(ir.elements):
        g = el.geometry or {}
        if "volume" in g and "length" not in g:
            body += _scad_cavity(g["volume"], i, z)
            r = (3 * g["volume"] / (4 * math.pi)) ** (1 / 3)
            z += 2 * r
        elif "length" in g and "area" in g:
            r = (g["area"] / math.pi) ** 0.5
            body += _scad_cylinder("tube", i, g["length"], r, z)
            z += g["length"]
        elif "length" in g and "radius" in g:
            body += _scad_cylinder("channel", i, g["length"],
                                   g["radius"], z)
            z += g["length"]
        elif ("length" in g and "width" in g
                and "thickness" in g):
            body += _scad_box("block", i, g["length"], g["width"],
                              g["thickness"], z)
            z += g["thickness"]
        else:
            body += f"// element {i} ({el.kind}) -- no geometry handler\n"
    return _scad_header(name, params) + body


def write_scad(ir, geo_hash, name="part", out_dir="."):
    path = f"{out_dir}/{slugify(name)}_{geo_hash}.scad"
    with open(path, "w") as fp:
        fp.write(emit_scad(ir, geo_hash, name))
    emit_claim("scad", ir, path, geo_hash,
               params={"name": name, "n_elements": len(ir.elements)})
    return path
