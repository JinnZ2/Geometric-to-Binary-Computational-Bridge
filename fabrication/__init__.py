"""
fabrication/  -- shape -> any-substrate fab artifacts.

Extends the geometric-to-binary bridge with non-silicon emission
targets. Same shape, same symmetry decomposition; different
lowering pass, different physical artifact.

ENERGY FLOW

    gshape ──► symmetry decomp ──► primitive graph (G)
                                          │
                                          ▼
                              ┌──── lowering pass ────┐
                              │   (per substrate)     │
                              ▼                       ▼
                    binary/SIMD (current)    NON-SILICON TARGETS:
                                                ├─ analog RC/LC
                                                ├─ mechanical (cam/linkage)
                                                ├─ optical (diffractive)
                                                ├─ acoustic (cavity)
                                                ├─ fluidic (microchannel)
                                                ├─ magnetic (coil winding)
                                                └─ woven (loom/wire)

Bond-graph formalism (Paynter, 1959) lets ONE primitive lower into
any substrate by swapping the (flow, effort) pair. A resonator is a
resonator whether it's L-C, mass-spring, Helmholtz cavity, or
Fabry-Pérot.

Substrate-specific physics is confined to:
  substrate_ir.GEOMETRY_TO_PARAMETER     (wide catalog, all 7 domains)
  backends/<domain>.py                   (concrete fns for the
                                          domains that have working
                                          backend code -- currently
                                          acoustic, fluidic)
  emit/<format>.py                       (artifact emitters)

Every emission also writes a CLAIM_TABLE.fab.json entry via
claim_back.back_claim, so each substrate stays falsifiable.

Layout

    fabrication/
    ├── substrate_ir.py           bond-graph IR + wide reference table
    ├── lowering.py               primitive graph -> SubstrateIR
    ├── couplers.py               gyrator/transformer cross-domain layer
    ├── claim_back.py             ledger writer (CLAIM_TABLE.fab.json)
    ├── backends/
    │   ├── acoustic.py           pressure/volume-flow domain
    │   └── fluidic.py            laminar liquid/gas
    ├── emit/
    │   ├── stl.py                3D-print / CNC artifact
    │   ├── svg_mask.py           laser-cut / photolitho mask
    │   └── spice_acoustic.py     pre-fab simulation netlist
    └── tests/
        └── helmholtz_loop.py     falsifiable end-to-end demo

License: CC0
"""
