# Bridge Architecture — single page

## Energy flow

```
   SPEC (geometry)
        │
        ▼
   LOWERING                ← lowering.py + per-substrate LOWER tables
        │
        ▼
   IR (substrate-tagged bond graph)
        │
   ┌────┴────────────────┐
   ▼                     ▼
 PREDICT                EMIT
 (claim_back_*.py)      (emit/*.py)
   │                     │
   ▼                     ▼
 CLAIM_TABLE.fab.json   artifact (.scad / .net / .gcode / …)
   ▲                     │
   │                     ▼
   │              PHYSICAL BUILD
   │                     │
   │                     ▼
   │              MEASUREMENT
   │              (sweep.wav / .csv / vibration / …)
   │                     │
   │                     ▼
   └─── VERIFY  (verify/verifier_*.py)
                         │
                         ▼
              CLAIM_TABLE.fab.measurements.json
                         │
                         ▼
            verdict ∈ {pass, drift, fail}
            + diagnostic localizing the leak
```

## Cross-substrate triangulation

```
      ┌────────────┬────────────┐
      ▼            ▼            ▼
   PATH A       PATH B       PATH C       (each = independent
   substrate₁   substrate₂   substrate₃     measurement chain)
      │            │            │
      ▼            ▼            ▼
    f_A, …      f_B, …       f_C, …
      │            │            │
      └────────────┼────────────┘
                   ▼
            coupler claim
            (ratio prediction)
                   │
                   ▼
            pairwise agreement
                   │
                   ▼
   which PAIR agrees? → that's where the model is right
   which PAIR disagrees? → that pair tells you where the leak is
                   │
                   ▼
   overall verdict = worst of (sub-verdicts + cross verdict)
   + diagnostic mapping pattern → physical cause
```

## Ledger as single source of truth

Three claim families, one file:

```
CLAIM_TABLE.fab.json
├── PHYSICS claims     scope = fab::<domain>::<hash>[::elN|::modeN]
│                      what the IR predicts about a fabricated part
│
├── COUPLER claims     scope = fab::coupler::<kind>::<name>
│                      what cross-substrate verification predicts
│
└── EMIT claims        scope = fab::emit::<format>::<hash>
                       what fab artifact was emitted, where, with
                       what parameters
```

Sibling files:

```
CLAIM_TABLE.fab.measurements.json   verdict log
CLAIM_TABLE.fab.baselines.json      phone-rig characterizations
coupler_overlay.json                cross-substrate physics
                                    parameters per coupler
```

## Falsifiability principle

Every claim has:

- `value`       predicted quantity
- `tol_frac`    tolerance band
- `measurement` protocol for producing a measured equivalent
- `failure`     list of specific physical causes for disagreement
- `provenance`  which module produced the claim

The verifier maps `(measured, predicted, tolerance)` → verdict
and walks `failure` for diagnostics. Nothing in the framework
is "trusted" — every prediction has a measurement that can
break it, and every disagreement has a documented physical
interpretation.

## Coupler ratio taxonomy

```
EXACT-RATIO COUPLERS  (zero free parameters)
  heater         ratio = 1.0          (Joule's law)
  transformer    ratio = N₂/N₁        (Faraday's law)
  friction       ratio = 1.0          (1st law of thermo)

SOFT-RATIO COUPLERS  (single calibratable parameter)
  solenoid       ratio = BL           (motor constant)

COMPOSITE COUPLERS  (multiple parameters, bundled physics)
  piezo          k_eff² (weak) or KLM-derived (strong)
  speaker        Thiele-Small full set
```

Exact-ratio couplers are the most rigorous tests of the
framework: any disagreement is a real measurement leak, not
coupler-model uncertainty. Soft-ratio and composite couplers
calibrate the parameter against the measurement.
