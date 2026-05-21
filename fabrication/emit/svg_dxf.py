"""
svg_dxf.py  (fabrication/emit/)

SVG + DXF mask emitter. Complements the existing svg_mask.py by
adding DXF (R12, minimal LINE entities) for older CAM workflows
and a hatch-fill option for solid-region patterns.

Takes a `channels` list (each: dict with x0, y0, x1, y1,
radius_mm). Not a substrate-IR emitter -- it's a 2D shape
emitter typically called from a fluidic/acoustic layout step.

License: CC0. Stdlib only.
"""
from ._common import emit_claim, slugify


def _dxf_header():
    return ("0\nSECTION\n2\nHEADER\n"
            "9\n$ACADVER\n1\nAC1009\n"
            "0\nENDSEC\n"
            "0\nSECTION\n2\nENTITIES\n")


def _dxf_trailer():
    return "0\nENDSEC\n0\nEOF\n"


def _dxf_line(x1, y1, x2, y2, layer="0"):
    return (f"0\nLINE\n8\n{layer}\n"
            f"10\n{x1}\n20\n{y1}\n30\n0\n"
            f"11\n{x2}\n21\n{y2}\n31\n0\n")


def emit_dxf_channels(channels, layer="cut"):
    s = _dxf_header()
    for ch in channels:
        s += _dxf_line(ch["x0"], ch["y0"], ch["x1"], ch["y1"], layer)
    s += _dxf_trailer()
    return s


def emit_svg_channels_with_hatch(channels, width_mm=50,
                                 height_mm=30,
                                 hatch_spacing_mm=1.0):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">'
    ]
    for ch in channels:
        d = f"M {ch['x0']} {ch['y0']} L {ch['x1']} {ch['y1']}"
        sw = 2 * ch["radius_mm"]
        parts.append(f'<path d="{d}" stroke="black" '
                     f'stroke-width="{sw}" stroke-linecap="round" '
                     f'fill="none"/>')
    n = int(width_mm / hatch_spacing_mm)
    for i in range(n + 1):
        x = i * hatch_spacing_mm
        parts.append(f'<line x1="{x}" y1="0" x2="{x}" '
                     f'y2="{height_mm}" stroke="lightgray" '
                     f'stroke-width="0.05"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_svg_dxf(channels, geo_hash, name="mask", out_dir=".",
                  width_mm=50, height_mm=30):
    path_svg = f"{out_dir}/{slugify(name)}_{geo_hash}.svg"
    path_dxf = f"{out_dir}/{slugify(name)}_{geo_hash}.dxf"
    with open(path_svg, "w") as fp:
        fp.write(emit_svg_channels_with_hatch(channels,
                                              width_mm, height_mm))
    with open(path_dxf, "w") as fp:
        fp.write(emit_dxf_channels(channels))

    class _Stub:
        domain = "fluidic_or_acoustic_2d"
        elements = channels

    emit_claim("svg", _Stub(), path_svg, geo_hash,
               params={"name": name,
                       "n_channels": len(channels)})
    emit_claim("dxf", _Stub(), path_dxf, geo_hash,
               params={"name": name,
                       "n_channels": len(channels)})
    return path_svg, path_dxf
