"""
materials.py  (fabrication/backends/)

Unified material registry. Every numeric property a backend or a
substrate_ir GEOMETRY_TO_PARAMETER lambda might need lives here,
keyed by lowercase material name. Stdlib only. CC0.

Provenance is documented per entry. Values are NOMINAL engineering
references; override with datasheet values for a real build.

`resolve_material(name)` returns a COPY of the property dict (so
callers can mutate freely). `_expand_material(g)` (called in
lowering.py) folds the resolved properties INTO the geometry dict
without overwriting any explicit numeric overrides the caller set.

Domain-specific tables in mechanical.py / thermal.py / magnetic.py
remain for backward compatibility but now defer to MATERIALS here.

License: CC0. Stdlib only.
"""

MATERIALS = {
    "steel": {
        "youngs":         200e9,
        "density":        7850.0,
        "poisson":        0.30,
        "yield_strength": 250e6,
        "thermal_k":      50.0,
        "specific_heat":  490.0,
        "epsilon":        0.50,
        # provenance: AISI 1018 mild steel nominal
    },
    "stainless": {
        "youngs":         193e9,
        "density":        8000.0,
        "poisson":        0.30,
        "yield_strength": 215e6,
        "thermal_k":      16.0,
        "specific_heat":  500.0,
        "epsilon":        0.50,
        # provenance: 304 stainless nominal
    },
    "aluminum": {
        "youngs":         69e9,
        "density":        2700.0,
        "poisson":        0.33,
        "yield_strength": 95e6,
        "thermal_k":      237.0,
        "specific_heat":  897.0,
        "epsilon":        0.09,
        # provenance: 6061-T6 nominal
    },
    "copper": {
        "youngs":         117e9,
        "density":        8960.0,
        "poisson":        0.34,
        "yield_strength": 70e6,
        "thermal_k":      401.0,
        "specific_heat":  385.0,
        "epsilon":        0.04,
        # provenance: C11000 annealed
    },
    "brass": {
        "youngs":         100e9,
        "density":        8500.0,
        "poisson":        0.34,
        "yield_strength": 200e6,
        "thermal_k":      120.0,
        "specific_heat":  380.0,
        "epsilon":        0.05,
        # provenance: C26000 cartridge brass nominal
    },
    "iron": {
        "youngs":         211e9,
        "density":        7874.0,
        "poisson":        0.29,
        "yield_strength": 130e6,
        "thermal_k":      80.0,
        "specific_heat":  449.0,
        "epsilon":        0.30,
        # provenance: pure Fe nominal
    },
    "titanium": {
        "youngs":         116e9,
        "density":        4500.0,
        "poisson":        0.32,
        "yield_strength": 830e6,
        "thermal_k":      22.0,
        "specific_heat":  528.0,
        "epsilon":        0.30,
        # provenance: Ti-6Al-4V nominal
    },
    "silicon": {
        "youngs":         130e9,
        "density":        2330.0,
        "poisson":        0.28,
        "yield_strength": 7e9,
        "thermal_k":      149.0,
        "specific_heat":  705.0,
        "epsilon":        0.65,
        # provenance: monocrystalline Si nominal
    },
    "wood_pine": {
        "youngs":         9e9,
        "density":        500.0,
        "poisson":        0.30,
        "yield_strength": 40e6,
        "thermal_k":      0.12,
        "specific_heat":  1700.0,
        "epsilon":        0.85,
        # provenance: white pine, longitudinal nominal
    },
    "wood_oak": {
        "youngs":         11e9,
        "density":        750.0,
        "poisson":        0.30,
        "yield_strength": 50e6,
        "thermal_k":      0.17,
        "specific_heat":  2000.0,
        "epsilon":        0.85,
        # provenance: red oak, longitudinal nominal
    },
    "abs": {
        "youngs":         2.3e9,
        "density":        1050.0,
        "poisson":        0.35,
        "yield_strength": 40e6,
        "thermal_k":      0.17,
        "specific_heat":  1300.0,
        "epsilon":        0.90,
        # provenance: 3D-print grade ABS nominal
    },
    "pla": {
        "youngs":         3.5e9,
        "density":        1240.0,
        "poisson":        0.36,
        "yield_strength": 50e6,
        "thermal_k":      0.13,
        "specific_heat":  1800.0,
        "epsilon":        0.90,
        # provenance: 3D-print grade PLA nominal
    },
    "petg": {
        "youngs":         2.1e9,
        "density":        1270.0,
        "poisson":        0.40,
        "yield_strength": 50e6,
        "thermal_k":      0.20,
        "specific_heat":  1200.0,
        "epsilon":        0.90,
        # provenance: 3D-print grade PETG nominal
    },
    "polymer_paper": {
        "youngs":         4e9,
        "density":        800.0,
        "poisson":        0.30,
        "yield_strength": 30e6,
        "thermal_k":      0.10,
        "specific_heat":  1300.0,
        "epsilon":        0.90,
        # provenance: speaker cone composite nominal
    },
    "water": {
        "youngs":         2.2e9,    # bulk modulus
        "density":        1000.0,
        "poisson":        0.50,
        "thermal_k":      0.60,
        "specific_heat":  4186.0,
        "epsilon":        0.95,
        # provenance: pure water at 20°C nominal
    },
    "air": {
        "youngs":         0.142e6,  # bulk modulus, isentropic
        "density":        1.225,
        "thermal_k":      0.026,
        "specific_heat":  1005.0,
        "epsilon":        0.0,
        # provenance: dry air at 15°C, 1 atm nominal
    },
}


def resolve_material(name):
    """Resolve a material name to its property dict.
    Returns a COPY so callers can mutate without polluting the registry.
    Raises KeyError with the known-name list on miss."""
    key = str(name).lower().strip()
    if key not in MATERIALS:
        raise KeyError(
            f"unknown material '{name}'. "
            f"known: {sorted(MATERIALS.keys())}"
        )
    return dict(MATERIALS[key])


def _expand_material(g):
    """If `g` has a string `material` key, fold its resolved properties
    into a fresh dict. Explicit numeric overrides in `g` ALWAYS win.

    Idempotent: calling on an already-expanded dict is a no-op.

    Use this at the top of any lowering lambda that wants to consume
    geometry expressed either as material-string or as numeric props.
    """
    if not isinstance(g, dict):
        return g
    mat = g.get("material")
    if not isinstance(mat, str):
        return g
    props = resolve_material(mat)
    out = dict(props)
    out.update(g)
    return out
