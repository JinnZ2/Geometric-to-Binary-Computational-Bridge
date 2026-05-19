"""
couplers.py  (fabrication/)

GYRATOR / TRANSFORMER OVERLAY -- separate graph layer.

A coupler connects two BondPorts in DIFFERENT domains. Lives in its
own graph layered on top of per-domain SubstrateIRs, so lowering
passes stay clean.

  piezo:   electrical ↔ mechanical     (V·I  ↔  F·v)
  speaker: electrical ↔ acoustic       (V·I  ↔  P·Q)
  pump:    mechanical ↔ fluidic        (F·v  ↔  P·ṁ)
  horn:    acoustic   ↔ acoustic       (area transform)

These edges are where most cross-domain bugs live. Every coupler
gets its own test rig before it goes into a build.

License: CC0. Stdlib only.
"""
from dataclasses import dataclass
from typing import Literal

from substrate_ir import BondPort


@dataclass(frozen=True)
class Coupler:
    """
    Cross-domain edge.

    transformer: effort↔effort with ratio n
    gyrator:     effort↔flow   with constant r  (V = r·F, F = V/r)
    """
    name: str
    kind: Literal["transformer", "gyrator"]
    ratio_or_r: float
    port_in:  BondPort
    port_out: BondPort
    geometry: dict
    provenance: str = "fabrication/couplers.py"


# Catalog of common geometric -> coupler mappings.
# Each one is a SEPARATE specification from the per-domain IRs;
# the bridge composes them at runtime.
COUPLER_CATALOG = {
    "horn_acoustic": {
        "kind": "transformer",
        "ratio_fn": lambda g: g["area_in"] / g["area_out"],
        "ports": ("acoustic", "acoustic"),
    },
    "piezo_disc": {
        "kind": "gyrator",
        "ratio_fn": lambda g: g["d33"] * g["area"] / g["thickness"],
        "ports": ("electrical", "mechanical"),
    },
    "syringe_pump": {
        "kind": "transformer",
        "ratio_fn": lambda g: g["piston_area"],   # F -> P, v -> Q
        "ports": ("mechanical", "fluidic"),
    },
    "diaphragm_speaker": {
        "kind": "gyrator",
        "ratio_fn": lambda g: g["BL"],            # force/current = flux·length
        "ports": ("electrical", "acoustic"),
    },
}
