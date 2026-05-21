# Geometric-to-Binary Computational Bridge — fabrication subsystem

Bond-graph based cross-substrate **design / verify / emit** framework.
One IR. One ledger. Six substrates. Six cross-substrate edges.
Six emit formats. Stdlib only. CC0. Mobile-runnable.

## What this does

Given a geometric specification (cavity, beam, channel, coil…),
the bridge:

1. **lowers** it into a substrate-tagged bond-graph IR
2. **predicts** measurable physics (resonance, time constants,
   impedance, etc.) and writes the predictions as falsifiable
   claims to a single ledger
3. **emits** the fab artifacts needed to build the thing
   (KiCad netlist, g-code, OpenSCAD, SVG/DXF, coil schedule,
   woven topology)
4. **verifies** the built artifact against the predicted claims
   using measurements from a phone or basic bench equipment

The same IR feeds all four steps. Verify and emit use the same
data. Cross-substrate couplers triangulate physics across
domains so a single physical object can be measured two or
three different ways with independent chains; disagreements are
localized to a specific physical cause.

## Substrates

| Substrate  | Lumped              | Distributed        | Verifier              |
|------------|---------------------|--------------------|-----------------------|
| Acoustic   | Helmholtz / chain   | pipe / box / cyl   | swept-sine + baseline |
| Fluidic    | R only / R+L+C      | —                  | steady CSV / transient|
| Electrical | RLC mesh            | (KLM available)    | CSV / shunt-WAV       |
| Mechanical | mass-spring-damper  | (planned: beam)    | vibration CSV         |
| Thermal    | R-C, q̇·R            | (planned: 1-D PDE) | heating / cooling CSV |
| Magnetic   | reluctance + N²/ℛ   | —                  | LCR + B-vs-I CSV      |

## Cross-substrate couplers

| Coupler     | Pair                  | Ratio                 | Falsifiability         |
|-------------|-----------------------|-----------------------|------------------------|
| Piezo       | electrical ↔ acoustic | k_eff² (weak / KLM)   | f₀ agreement           |
| Speaker     | E ↔ M ↔ acoustic      | Thiele-Small set      | triple agreement       |
| Heater      | electrical ↔ thermal  | **1.0 exact** (Joule) | ΔT_ss, τ, R_th         |
| Transformer | electrical ↔ magnetic | **N₂/N₁ exact**       | n_oc, n_sc, L_ratio    |
| Friction    | mechanical ↔ thermal  | **1.0 exact** (1st law)| P_mech ≡ q̇            |
| Solenoid    | magnetic ↔ mechanical | BL (soft, isolated)   | motor / gen / impedance|

## Emit formats

| Format         | Target                | Field-runnable          |
|----------------|-----------------------|-------------------------|
| OpenSCAD .scad | slicer → STL → 3DP    | laptop or any 3DP       |
| KiCad .net     | PCB house or bench    | PCB days / bench mins   |
| g-code         | direct FDM / CNC      | machine-dependent       |
| Coil schedule  | bobbin or hand-wind   | yes (hand mode)         |
| Loom pattern   | pegboard / hand-weave | YES — no machine        |
| SVG + DXF      | laser / vinyl / litho | minutes if cutter       |

## Quick start

```bash
# run everything once to confirm the bridge is healthy
python -m fabrication.smoke

# inspect what's in the ledger
python -m fabrication.ledger summary

# launch the menu-driven mini app
python -m fabrication.mini
```

## Layout

```
fabrication/
├── backends/                  # per-substrate parameter physics
│   ├── acoustic.py
│   ├── electrical.py
│   ├── fluidic.py
│   ├── magnetic.py
│   ├── mechanical.py
│   └── thermal.py
├── couplers_*.py              # cross-substrate physics
├── eigenmodes.py + pipe_modes.py
├── claim_back_*.py            # predicted physics → ledger
├── lowering.py                # geometry → IR
├── verify/
│   ├── verifier_*.py          # substrate + cross-substrate verifiers
│   ├── transfer.py            # FFT, transfer function, coherence
│   ├── baseline.py + correct.py
│   ├── peak.py + peak_multi.py
│   ├── transient_fit.py + regression.py
│   ├── csv_io.py
│   └── tests/                 # smoke tests
├── emit/
│   ├── scad.py
│   ├── kicad.py
│   ├── gcode.py
│   ├── coil_schedule.py
│   ├── loom.py
│   ├── svg_dxf.py
│   ├── _common.py
│   └── tests/
├── ledger.py                  # ledger inspector
├── smoke.py                   # all-smoke runner
├── mini.py                    # menu-driven entry
├── CLAIM_TABLE.fab.json              ← single ledger
├── CLAIM_TABLE.fab.measurements.json
├── CLAIM_TABLE.fab.baselines.json
└── coupler_overlay.json
```

## Licensing

CC0. Adopt, fork, port, modify, embed. No attribution required
but appreciated. No claim of correctness beyond what the
verifier reports against its own ledger — the framework is
self-falsifying, not self-validating.
