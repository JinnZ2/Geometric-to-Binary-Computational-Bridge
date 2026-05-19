"""
svg_mask.py  (fabrication/emit/)

2D mask for laser cutter / photolithography (microfluidic chips).
Pure SVG text. One channel = one path.

License: CC0. Stdlib only.
"""


def emit_channel_mask(channels, width_mm=50, height_mm=30):
    """
    channels: list of dicts {x0, y0, x1, y1, radius_mm}
    Coordinates in mm. SVG user units = mm.
    """
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}">'
    ]
    for ch in channels:
        d  = f"M {ch['x0']} {ch['y0']} L {ch['x1']} {ch['y1']}"
        sw = 2 * ch["radius_mm"]
        parts.append(
            f'<path d="{d}" stroke="black" stroke-width="{sw}" '
            f'stroke-linecap="round" fill="none"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)
