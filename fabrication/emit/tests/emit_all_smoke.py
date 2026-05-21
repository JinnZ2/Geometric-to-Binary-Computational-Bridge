"""
emit_all_smoke.py  (fabrication/emit/tests/)

Six tiny IRs (one per substrate) -> emit every applicable
artifact -> verify each file exists and is non-empty.

This is FORMAT compliance only. It does not claim the emitted
artifacts are physically correct; the verifier layer audits
that later. It does claim that every emitter runs cleanly on a
representative IR and writes a non-empty artifact + a sibling
claim into the ledger.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.emit.tests.emit_all_smoke

License: CC0. Stdlib only.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .. import emit_all
from ..svg_dxf import write_svg_dxf


@dataclass
class _P:
    domain: str
    flow_name: str
    effort_name: str


@dataclass
class _E:
    kind: str
    geometry: dict
    parameter: float
    port_a: _P
    port_b: "_P" = None


@dataclass
class _I:
    domain: str
    elements: list = field(default_factory=list)
    topology: list = field(default_factory=list)


def _check(path):
    if isinstance(path, tuple):
        return all(_check(x) for x in path)
    if isinstance(path, str) and path.startswith("ERROR"):
        return False
    p = Path(path)
    return p.exists() and p.stat().st_size > 0


if __name__ == "__main__":
    out = "_emit_out"
    Path(out).mkdir(exist_ok=True)
    results = {}

    # ELECTRICAL -- RLC
    port = _P("electrical", "I", "V")
    ir_e = _I("electrical", [
        _E("dissipate",    {}, 47.0,   port),
        _E("store_flow",   {}, 1e-3,   port),
        _E("store_effort", {}, 100e-9, port),
    ])
    results["electrical"] = emit_all(ir_e, "ELEC_X",
                                     "rlc", out_dir=out)

    # MECHANICAL -- mass / spring / damper
    port = _P("mechanical", "v", "F")
    ir_m = _I("mechanical", [
        _E("store_flow",   {"length": 0.05, "area": 1e-4}, 0.3,    port),
        _E("store_effort", {"length": 0.04, "area": 1e-4}, 8.3e-4, port),
        _E("dissipate",    {"length": 0.02, "area": 1e-4}, 0.6,    port),
    ])
    results["mechanical"] = emit_all(ir_m, "MECH_X",
                                     "spring_mass", out_dir=out)

    # ACOUSTIC -- Helmholtz
    port = _P("acoustic", "Q", "P")
    ir_a = _I("acoustic", [
        _E("store_effort", {"volume": 2.5e-4}, 0.0, port),
        _E("store_flow",   {"length": 0.03, "area": 1.77e-4}, 0.0, port),
    ])
    results["acoustic"] = emit_all(ir_a, "ACO_X",
                                   "helmholtz", out_dir=out)

    # FLUIDIC -- single channel
    port = _P("fluidic", "mdot", "P")
    ir_f = _I("fluidic", [
        _E("dissipate", {"length": 0.30, "radius": 1.5e-3}, 0.0, port),
    ])
    results["fluidic"] = emit_all(ir_f, "FLUID_X",
                                  "channel", out_dir=out)

    # THERMAL -- conduction + storage
    port = _P("thermal", "qdot", "dT")
    ir_t = _I("thermal", [
        _E("dissipate",    {"length": 0.002, "area": 1e-3}, 0.0, port),
        _E("store_effort", {"volume": 1e-4},                0.0, port),
    ])
    results["thermal"] = emit_all(ir_t, "THERM_X",
                                  "heatsink", out_dir=out)

    # MAGNETIC -- inductor (100-turn coil on ferrite)
    port = _P("magnetic", "PhiB", "MMF")
    ir_g = _I("magnetic", [
        _E("dissipate",  {"length": 0.07, "area": 80e-6, "mu_r": 2300},
           1e5, port),
        _E("store_flow", {"turns": 100}, 100 * 100, port),
    ])
    results["magnetic"] = emit_all(ir_g, "MAG_X",
                                   "inductor", out_dir=out)

    # SVG/DXF -- 2D mask, not in EMIT_BY_DOMAIN; call directly
    channels = [
        {"x0": 5.0,  "y0": 5.0,  "x1": 45.0, "y1": 5.0,  "radius_mm": 0.75},
        {"x0": 5.0,  "y0": 15.0, "x1": 45.0, "y1": 15.0, "radius_mm": 0.75},
        {"x0": 25.0, "y0": 5.0,  "x1": 25.0, "y1": 25.0, "radius_mm": 0.5},
    ]
    results["svg_dxf"] = {
        "svg_dxf": write_svg_dxf(channels, "SVGDXF_X", "mask",
                                 out_dir=out, width_mm=50,
                                 height_mm=30),
    }

    print("EMIT SMOKE SUMMARY")
    print("-" * 64)
    all_ok = True
    for domain, arts in results.items():
        for label, path in arts.items():
            ok = _check(path)
            mark = "OK" if ok else "FAIL"
            all_ok &= ok
            print(f"  [{mark:4s}] {domain:12s}  {label:18s}  ->  {path}")
    print("-" * 64)
    assert all_ok, "Some emitters produced empty / missing files."
    print("all emit families produced non-empty artifacts")
