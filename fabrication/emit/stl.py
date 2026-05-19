"""
stl.py  (fabrication/emit/)

Minimal STL emitter for a Helmholtz-style cavity + neck.
No external CAD lib. Triangulates from cylinder primitives.
Output: ASCII STL string -> write to file -> 3D-print / mill.

License: CC0. Stdlib only.
"""
from math import pi, cos, sin


def _ring(cx, cy, z, r, n=48):
    return [(cx + r*cos(2*pi*i/n), cy + r*sin(2*pi*i/n), z) for i in range(n)]


def _tri(a, b, c):
    """ASCII STL facet. Normal left as 0 0 0; slicers re-normal."""
    return (
        "  facet normal 0 0 0\n"
        "    outer loop\n"
        f"      vertex {a[0]:.6f} {a[1]:.6f} {a[2]:.6f}\n"
        f"      vertex {b[0]:.6f} {b[1]:.6f} {b[2]:.6f}\n"
        f"      vertex {c[0]:.6f} {c[1]:.6f} {c[2]:.6f}\n"
        "    endloop\n"
        "  endfacet\n"
    )


def cylinder_shell(z0, z1, r, n=48):
    lo, hi = _ring(0, 0, z0, r, n), _ring(0, 0, z1, r, n)
    s = ""
    for i in range(n):
        j = (i + 1) % n
        s += _tri(lo[i], lo[j], hi[i])
        s += _tri(lo[j], hi[j], hi[i])
    return s


def emit_helmholtz_stl(cavity_r, cavity_h, neck_r, neck_h, name="resonator"):
    s = f"solid {name}\n"
    s += cylinder_shell(0.0,      cavity_h,            cavity_r)
    s += cylinder_shell(cavity_h, cavity_h + neck_h,   neck_r)
    s += f"endsolid {name}\n"
    return s
