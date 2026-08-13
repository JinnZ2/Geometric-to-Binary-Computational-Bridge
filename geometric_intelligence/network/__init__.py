"""
geometric_intelligence.network -- geometric network analysis with phi scaling.

    from geometric_intelligence.network import GeometricNetwork, IntegrityMonitor

WHY THIS IS A SUBPACKAGE AND NOT THE TOP LEVEL
    The drop's README and FIELD_GUIDE both say
    `from geometric_intelligence import GeometricNetwork`, and its
    `__init__.py` was written to sit at `geometric_intelligence/__init__.py`
    doing `from .core import ...`.

    That directory already holds twelve modules and is imported by four test
    suites (`test_framework_modules.py`, `test_multi_helix_swarm.py`,
    `test_bridges.py`), whose `geometric_intelligence/__init__.py` is empty on
    purpose. Replacing it with one that imports `.core` makes every one of
    those imports depend on this package loading, which is the same failure
    that took out `bridges/` when `glyph_state_encoder.py` stopped compiling.

    So the drop lands one level down and the import lines in the two documents
    are corrected to match. Nothing else about it is changed.

WHAT IS MISSING FROM THE DROP
    `core.py`     reconstructed here from what the supplied modules call.
                  `audit()` and `correct()` refuse rather than guess -- see
                  the provenance note at the top of core.py.
    `bridge.py`   `network_to_claims` / `append_geo_claims`, which the README
                  says write into `CLAIM_TABLE.fab.json`. Not written: open
                  problem GI-10 states why.
    `tests/test_geometric_intelligence.py`  the "20 unit tests" the README
                  cites. `tests/test_gi_network.py` in this repo is not a
                  substitute for it -- it tests the audit findings, not the
                  behaviour those 20 were written for.
    `examples/demo.py`

License: CC0. Stdlib only.
"""
from .core import (
    GeometricNetwork,
    GeoNode,
    GeoEdge,
    PHI,
    PHI_INV,
    PHI_INV_9,
    INTEGRITY_THRESHOLD,
)
from .resonance import MultiScaleResonance, ResonancePeak
from .integrity import IntegrityMonitor, IntegrityReport

__all__ = [
    "GeometricNetwork", "GeoNode", "GeoEdge",
    "PHI", "PHI_INV", "PHI_INV_9", "INTEGRITY_THRESHOLD",
    "MultiScaleResonance", "ResonancePeak",
    "IntegrityMonitor", "IntegrityReport",
]

__version__ = "0.1.0"
