# Architecture

This is the root-level architectural overview. The `fabrication/`
subsystem has its own narrower architecture page at
`fabrication/ARCHITECTURE.md`; this file frames the whole repo and
its position in the wider JinnZ2 ecosystem.

## Top-level structure

```
Geometric-to-Binary-Computational-Bridge/
├── GEIS/                       Geometric Information Encoding System
│                               (octahedral state model, 8-state encoder,
│                                lossless geometric <-> binary)
├── bridges/                    11 substrate encoders (magnetic, light,
│                                sound, gravity, electric, wave, thermal,
│                                pressure, chemical + cognitive)
├── Engine/                     EM-field solver, SIMD optimizer, spatial
│                               octree, symmetry detector, Gaussian-splat
│                               representations
├── fabrication/                bond-graph IR + cross-substrate verifiers
│                               + emit formats. The subsystem developed
│                               in greatest depth in this branch.
├── experiments/                polyglot dispatcher, agent comfort layer,
│                               cognition-style addon, request_tool
│                               (Phase 0 agent request channel)
├── Silicon/                    silicon hardware-pathway research
├── docs/                       architecture notes + Gaussian-splat
│                               design series
├── tests/                      bridge + engine test suites
├── CLAIM_TABLE.json            root-level rate-equation domain claims
├── AI_CONTEXT.md               cross-repo context for AI readers
├── AI_INDEX.json               machine-readable navigation
├── CLAUDE.md                   in-repo instructions
└── BRIDGE_GLOSSARY.md          internal <-> academic term mapping
```

## Position in the JinnZ2 ecosystem

This repo is one node in a network of related CC0 / public-domain
work. Sister repos that couple to this one:

| Repo                         | How it couples                        |
|------------------------------|---------------------------------------|
| differential-frame-core      | foundational DE contract across substrates |
| energy_english               | constraint-grounded grammar this repo uses for its voice layer |
| earth-systems-physics        | source of physics constraints used in some bridges |
| calibration-audit            | the methodology this repo's verifiers implement at substrate level |
| labor-thermodynamics         | thermodynamic-accountability framework |
| projection_error_modes       | error-mode catalog this repo's verifiers attempt to surface |
| Hormuz_cascade               | applied earth-systems case study |
| automation_scope_audit       | bounds-of-applicability reasoning used here for verifier scope |

All eight live under github.com/JinnZ2/ and share the same
falsifiable-claims-based methodology and CC0 intent. Cross-links
maintained via `.fieldlink.json` and `CROSSLINKS.md`.

## Energy flow through the fabrication subsystem

```
   SPEC (geometry)
        |
        v
   LOWERING                    <- lowering.py + per-substrate LOWER tables
        |
        v
   IR (substrate-tagged bond graph)
        |
   +----+----------------+
   v                     v
 PREDICT               EMIT
 (claim_back_*.py)     (emit/*.py)
   |                     |
   v                     v
 CLAIM_TABLE.fab.json  artifact (.scad / .net / .gcode / .csv)
   ^                     |
   |                     v
   |              PHYSICAL BUILD
   |                     |
   |                     v
   |              MEASUREMENT
   |              (sweep.wav / .csv / vibration / .)
   |                     |
   |                     v
   +---- VERIFY  (verify/verifier_*.py)
                         |
                         v
              CLAIM_TABLE.fab.measurements.json
                         |
                         v
                 verdict in {pass, drift, fail}
                 + diagnostic localizing the leak
```

## Falsifiability principle (single most important architectural commitment)

Every claim carries five required fields:

* `value`       predicted quantity
* `tol_frac`    tolerance band
* `measurement` protocol for producing a measured equivalent
* `failure`     list of specific physical causes for disagreement
* `provenance`  which module produced the claim

The verifier maps `(measured, predicted, tolerance) -> verdict` and
walks `failure` for localized diagnostics. Nothing in the framework
is "trusted." Every prediction has a measurement that can break it,
and every disagreement has a documented physical interpretation. A
disagreement is therefore not just a "doesn't match" — it routes to
a specific suspect physical mechanism the operator can investigate.

## Cross-substrate triangulation

```
      +------------+------------+
      v            v            v
   PATH A       PATH B       PATH C       (each = independent
   substrate_1   substrate_2  substrate_3  measurement chain)
      |            |            |
      v            v            v
    f_A, .       f_B, .       f_C, .
      |            |            |
      +------------+------------+
                   v
            coupler claim
            (ratio prediction)
                   v
            pairwise agreement
                   v
   which PAIR agrees? -> that's where the model is right
   which PAIR disagrees? -> that pair tells you where the leak is
```

## Coupler ratio taxonomy

```
EXACT-RATIO COUPLERS   (zero free parameters)
  heater         ratio = 1.0          (Joule's law)
  transformer    ratio = N2/N1        (Faraday's law)
  friction       ratio = 1.0          (1st law of thermodynamics)

SOFT-RATIO COUPLERS    (single calibratable parameter)
  solenoid       ratio = BL           (motor constant)

COMPOSITE COUPLERS     (multiple parameters, bundled physics)
  piezo          k_eff^2 (weak) or KLM-derived (strong)
  speaker        full Thiele-Small set
```

Exact-ratio couplers are the most rigorous tests of the framework:
any disagreement IS a real measurement leak, not coupler-model
uncertainty. Soft-ratio and composite couplers calibrate the
parameter against the measurement.

## Key constraint: stdlib only

No pip dependencies in the core path. The framework is intended to
run on a phone (Termux / Pyto), on a Raspberry Pi, on a vintage
laptop, on any vanilla CPython 3.10+. This is a deliberate
architectural choice -- it bounds the audience to "anyone with
Python" rather than "anyone who can resolve their dependency tree."
