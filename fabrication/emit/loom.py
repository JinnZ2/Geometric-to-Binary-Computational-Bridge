"""
loom.py  (fabrication/emit/)

Field-runnable fallback: no machine required. ASCII grid where
each cell encodes a wire crossing or component slot. Preserves
the IR's topology so a human can lay it out by hand on a
pegboard / loom frame using magnet wire and bobbins.

Outputs:
  .txt   ASCII grid + legend
  .csv   (x, y, char) for any rendering pipeline

License: CC0. Stdlib only.
"""
from ._common import emit_claim, slugify


CH_EMPTY  = "."
CH_WIRE_H = "-"
CH_WIRE_V = "|"
CH_CROSS  = "+"
CH_R      = "R"
CH_L      = "L"
CH_C      = "C"
CH_NODE   = "o"


def _layout_chain(ir):
    """1-D chain layout: elements occupy cells along the
    horizontal rail; store_effort items shunt down to a parallel
    ground rail."""
    elements = ir.elements
    width  = max(8, 2 * len(elements) + 4)
    height = 5
    grid = [[CH_EMPTY for _ in range(width)] for _ in range(height)]
    mid = height // 2

    # horizontal main rail
    for x in range(1, width - 1):
        grid[mid][x] = CH_WIRE_H
    # ground rail
    for x in range(1, width - 1):
        grid[height - 1][x] = CH_WIRE_H

    legend = []
    for i, el in enumerate(elements):
        x = 2 + 2 * i
        sym = {"dissipate":    CH_R,
               "store_flow":   CH_L,
               "store_effort": CH_C}.get(el.kind, "?")
        if el.kind == "store_effort":
            # shunt to ground rail
            for y in range(mid + 1, height - 1):
                grid[y][x] = CH_WIRE_V
            grid[mid][x] = CH_CROSS
            grid[mid + 1][x] = sym
        else:
            grid[mid][x] = sym
        legend.append(f"  {sym}{i+1} = {el.kind}  "
                      f"param={el.parameter:.3e}")
    return grid, legend


def emit_loom_ascii(ir, name="topology"):
    grid, legend = _layout_chain(ir)
    body = "\n".join("".join(row) for row in grid)
    head = (f"WOVEN / LOOM TOPOLOGY -- {name}\n"
            f"domain : {ir.domain}\n"
            f"legend :\n" + "\n".join(legend) +
            "\n\nGRID:\n")
    return head + body + "\n"


def emit_loom_csv(ir, name="topology"):
    grid, _ = _layout_chain(ir)
    rows = []
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != CH_EMPTY:
                rows.append(f"{x},{y},{ch}")
    return "x,y,char\n" + "\n".join(rows) + "\n"


def write_loom(ir, geo_hash, name="topology", out_dir="."):
    path_txt = f"{out_dir}/{slugify(name)}_{geo_hash}_loom.txt"
    path_csv = f"{out_dir}/{slugify(name)}_{geo_hash}_loom.csv"
    with open(path_txt, "w") as fp:
        fp.write(emit_loom_ascii(ir, name))
    with open(path_csv, "w") as fp:
        fp.write(emit_loom_csv(ir, name))
    emit_claim("loom", ir, path_txt, geo_hash, params={"name": name})
    return path_txt, path_csv
