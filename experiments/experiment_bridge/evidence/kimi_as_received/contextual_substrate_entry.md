# Contextual Substrate — Entry for the Geometric-to-Binary Computational Bridge

Status: **measured, not just described.** Every number below comes from
`toy_rvq_void.py` (stdlib-only, seed 0, train n=2000 / held-out n=1000,
8-D correlated Gaussian source, 4 residual levels, 16 codes + 1 VOID
escape per level). Full record: `toy_rvq_void_seed0.json`.
Instrument runtime: ~7 s on commodity hardware. License: CC0.

Provenance of the proposal: a conversation (external, with Grok)
suggesting a neural codec ("NCM") as a ninth, *contextual* substrate
for the bridge. This entry puts that proposal through the house
procedure: glossary row, coupler taxonomy rows, claim-table rows with
all five required fields (value / tol_frac / measurement / failure /
provenance), and a falsifiable verdict per claim.

---

## 1. Glossary row — "Domains and Their Conjugate Variables"

Proposed addition to `BRIDGE_GLOSSARY.md`, domain table:

| Substrate    | Flow (through)              | Effort (across)                | Resistance            |
|--------------|-----------------------------|--------------------------------|-----------------------|
| contextual   | residual stream r_k per level | codebook pull d_k = c_k − r_{k−1} | quantization (argmin snap) |

**Qualifier that must ship with the row:** these are *bookkeeping*
variables, **not** power-conjugate variables. In every physical
substrate already in the table, effort × flow = power and the
orthogonal split |z|² = |ẑ|² + |r|² is the bookkeeping identity behind
energy conservation. In this substrate that identity fails by up to
**150% relative defect** (claim 2 below, verdict `fail`). The hard
argmin snap correlates the chosen code with the remaining residual —
<ẑ, r> ≠ 0 — so no effort/flow pair read off this substrate obeys a
power law. The row is admitted as a *bookkeeping domain* (tracked
quantities: residual norm, index, VOID flag), with the power reading
recorded **VOID**, not guessed.

Companion row for "Frameworks and Methodology":

| In this repo         | Canonical / academic term                                      |
|----------------------|----------------------------------------------------------------|
| contextual substrate | rate-distortion-limited representation channel (vector quantization) |

## 2. Coupler taxonomy rows — "Cross-Substrate Couplers"

| In this repo          | Canonical term                                           |
|-----------------------|----------------------------------------------------------|
| VQ snap coupler       | hard argmin vector quantizer (Lloyd iteration)           |
| soft-snap coupler     | soft-assignment / entropy-constrained vector quantizer   |
| VOID escape coupler   | escape symbol in entropy coding (reserved index, decodes as zero) |

Notes:

- The VOID escape coupler is **not** a new mechanism — escape symbols
  are ~50-year-old entropy-coding practice. What is new here is reading
  it as a first-class coupler state with a measured rate
  (claim 3, and the per-level census below).
- The VQ snap coupler is a *composite* coupler by the repo's own
  taxonomy (its "ratio" is the whole codebook — many bundled
  parameters), not an exact-ratio coupler. Claims that treat it as
  exact-ratio are VOID until a zero-free-parameter reduction is shown.

## 3. Claim-table rows (claim_back `_pack` format)

All four claims were packed by the instrument and verdicted on the
held-out split. `value` is predicted from the train split;
`measured` is the held-out result; verdict bands: pass ≤ tol_frac,
drift ≤ 3·tol_frac, fail beyond.

### Claim 1 — level-one residual collapse: **pass**

```json
{
  "scope": "fab::contextual::rvq::level1_residual_energy_frac",
  "rate_var": "dE_residual/dlevel",
  "kind": "contextual",
  "value": 0.245521,
  "tol_frac": 0.25,
  "measurement": "encode held-out split; decode with ONLY the level-1 index; residual energy / signal energy",
  "failure": "- codebook overfit -> held-out worse than train (drift/fail)\n- source distribution shift -> level-1 codes no longer stand alone\n- VOID rate at level 1 >> target -> level 1 never stood alone",
  "provenance": "toy_rvq_void.py",
  "measured": 0.248381,
  "verdict": "pass"
}
```

Level 1 alone leaves 24.8% of signal energy (it captures 37.8% of
signal energy directly; the gap is the non-orthogonality of claim 2).
The "level one stands alone" property — the codec's version of a
readable first bond — transfers from train to held-out within
tolerance.

### Claim 2 — energy identity: **fail** (the designed falsifiable check)

```json
{
  "scope": "fab::contextual::rvq::energy_identity_defect",
  "rate_var": "d(|z|^2 - |z_hat|^2 - |r|^2)/dn",
  "kind": "contextual",
  "value": 0.0,
  "tol_frac": 1e-06,
  "measurement": "per sample: |z|^2 - (|z_hat|^2 + |r|^2) == 2<z_hat,r>; identity holds only if the split is orthogonal; report worst relative magnitude over held-out split",
  "failure": "- non-orthogonal codebook entries -> defect != 0: the\n  effort/flow energy reading of this substrate is VOID,\n  use bookkeeping reading only",
  "provenance": "toy_rvq_void.py",
  "measured": 1.5036325501281391,
  "verdict": "fail"
}
```

This is the load-bearing negative result of the entry. The claim
states the identity a power reading *requires*; the measurement
refutes it (worst held-out defect 1.50, i.e. the cross term is as
large as the signal energy itself for some samples). Consequence,
recorded rather than smoothed over: **the contextual substrate does
not support an effort/flow power bond-graph reading. Bookkeeping
reading only.** Any future document that draws power arrows on this
substrate must first falsify this claim's failure.

### Claim 3 — VOID escape integrity: **pass** (structural)

```json
{
  "scope": "fab::contextual::rvq::void_escape_integrity",
  "rate_var": "dN_silent_snap/dn",
  "kind": "contextual",
  "value": 0.0,
  "tol_frac": 0.0,
  "measurement": "count held-out residuals whose min distance exceeds tau_k that were nevertheless snapped to a code (must be zero)",
  "failure": "- threshold not applied at some level -> silent snap returns\n- VOID index collides with a real code index -> misdecode",
  "provenance": "toy_rvq_void.py",
  "measured": 0.0,
  "verdict": "pass",
  "note": "encode() routes every over-threshold residual to the reserved VOID index by construction; the measured value is a structural 0.0 and the claim is falsified by any code path that snaps past tau_k"
}
```

### Claim 4 — codepath collision rate: **pass**

```json
{
  "scope": "fab::contextual::rvq::codepath_collision_rate",
  "rate_var": "dN_shared_path/dn",
  "kind": "contextual",
  "value": 0.028,
  "tol_frac": 0.5,
  "measurement": "full index-tuple census over held-out split: 1 - distinct_paths/n; two samples collide iff their entire code path (VOID positions included) is identical",
  "failure": "- degenerate/discrete source -> collision rate >> train\n- per-level input census substituted for full-path census ->\n  degenerate 0.0 on continuous floats (false pass)",
  "provenance": "toy_rvq_void.py",
  "measured": 0.015,
  "verdict": "pass",
  "distinct_paths_train": 1944,
  "distinct_paths_held_out": 985
}
```

This claim exists because the naive per-level census is degenerate:
on continuous float inputs every level-1 input is distinct, so the
per-level "collision rate" is exactly 0.0 — a false-clean signal. The
full-path census is the meaningful one: 985 of 1000 held-out samples
have unique descriptions; 1.5% share a complete code path with
another sample. That measured 1.5% *is* the many-to-one property the
substrate is built on — the quantizer maps distinct contexts to
identical symbols, and now the rate at which it does so is a number
with a tolerance band, not an adjective.

## 4. Measured context (kept outputs, seed 0)

| Quantity | train | held-out |
|---|---|---|
| signal energy | 28565.31 | 14016.98 |
| level-1-only residual energy frac | 0.2455 | 0.2484 |
| final (4-level) residual energy frac | 0.0827 | 0.0766 |
| per-level captured energy frac | [0.770, 0.099, 0.043, 0.026] | [0.378, 0.050, 0.022, 0.013] |
| per-level VOID rate (target 0.010) | [0.0095, 0.011, 0.012, 0.013] | [0.007, 0.007, 0.009, 0.014] |
| codepath distinct / n | 1944 / 2000 | 985 / 1000 |
| codepath collision rate | 0.028 | 0.015 |
| energy-identity worst rel. defect | 4.009 | 1.504 |

tau per level (squared-distance thresholds set to 1% train VOID rate):
[9.991, 5.288, 3.444, 2.163].

## 5. What is still VOID (recorded, not guessed)

- **Real neural codecs.** This is a toy RVQ on a synthetic source.
  Transfer of any claim above to SoundStream-lineage codecs, learned
  codebooks, or audio/EEG data is VOID until re-measured there.
- **Bit-rate accounting.** Index entropy (including the VOID symbol's
  cost) is not measured; rate-distortion claims are VOID.
- **Power reading.** VOID by measurement (claim 2), pending any
  orthogonalizing redesign (e.g. explicit Gram-Schmidt stage), which
  would be a new instrument with its own claims.
- **Cross-substrate couplers *to* the contextual domain.** The three
  coupler rows in §2 are intra-substrate. A measured coupler from,
  say, acoustic into contextual (an encoder front-end) is future work.

## 6. Reproduce

```sh
python3 toy_rvq_void.py 0     # writes toy_rvq_void_seed0.json
```

Stdlib only (`json`, `math`, `random`, `sys`, `time`). CPython 3.10+.
Runs on a phone. Different seed -> same record structure, fresh
numbers; the claims are the contract, the seed-0 record is one
witness.
