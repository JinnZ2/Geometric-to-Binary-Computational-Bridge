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

Level 1 alone leaves 24.8% of signal energy; it captures 77.0% of
signal energy directly (|c_1|²/|z|², held-out). The residual exceeds
the naive 1 − 0.770 = 23.0% because the cross term 2⟨c_1, r⟩ is
negative-deficient — c_1 correlates with the residual it leaves
behind. That gap is exactly the non-orthogonality of claim 2. The
"level one stands alone" property — the codec's version of a
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
| per-level captured energy frac | [0.770, 0.099, 0.043, 0.026] | [0.770, 0.101, 0.044, 0.027] |
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

## 6. Errata — caught by the experiment-bridge audit, 2026-11-17

The bridge repo's `evidence/reproduce_kimi.py` harness archived this
document as-received, replayed the instrument twice (stable fields
bit-identical, verdicts recalculated — all matching), and ran an
independent census. All seven of its checks pass, re-verified from
this side with identical census values. It also caught defects.
Errors remain data; original values are quoted, not erased.

1. **Wrong denominator (this document, now fixed inline).** The §4
   table's held-out "per-level captured energy frac" column originally
   read [0.378, 0.050, 0.022, 0.013] — held-out energies divided by
   the *train* signal energy. Correct same-split values: [0.770,
   0.101, 0.044, 0.027]. Claim 1's prose carried the same error
   ("captures 37.8% directly" -> 77.0%). The claims themselves are
   unaffected: every value/measured/verdict in §3 recomputes exactly.
2. **Calibration trajectory mismatch (instrument, documented not
   repaired).** `set_thresholds` calibrates on the *ungated*
   trajectory (every residual fully subtracted), while `encode` is
   gated (a VOID stage passes its residual downstream unchanged).
   Result: unconditional calibration VOID rates are [0.0095, 0.0095,
   0.0095, 0.0095] but the actual encoded train rates are [0.0095,
   0.011, 0.012, 0.013], drifting from the 0.010 target as VOIDs
   accumulate. The bridge v1's `calibrate_thresholds(gated=True)` is
   the correct fix; this specimen keeps the defect.
3. **Adversarial edge census (instrument, 22 probes).** Failure modes
   now demonstrated constructively, all outside the declared main
   configuration: a codebook with 17 real codes collides with the
   global VOID sentinel 16 (the exact failure mode claim 3 names —
   claim 3's structural 0.0 holds only for the declared 16-code
   configuration); NaN threshold fails *open* (accepts arbitrary
   distance); NaN input snaps to code 0; a missing tau silently skips
   a level; extra input dimensions are zip-swallowed; decode accepts
   negative indices. `verdict(NaN)` correctly returns `fail`.
4. **Richer path census (enrichment, claim 4 unchanged).** The
   independent census resolves the 1.5% redundant fraction into
   multiplicities [2, 2, 2, 2, 2, 2, 2, 2, 2, 7]: nine paths are
   shared by two samples, one path is shared by seven. 2.5% of
   held-out samples live in non-singleton paths. Claim 4's defined
   quantity (1 − distinct/n) stands; these are the finer-grained
   numbers behind it.

## 7. Reproduce

```sh
python3 toy_rvq_void.py 0     # writes toy_rvq_void_seed0.json
```

Stdlib only (`json`, `math`, `random`, `sys`, `time`). CPython 3.10+.
Runs on a phone. Different seed -> same record structure, fresh
numbers; the claims are the contract, the seed-0 record is one
witness.

## 8. Addendum — repairs built on the audit findings, 2026-11-18

Two successor instruments. The specimen above stays unrepaired; each
successor ships its own claims so the repairs are measured, not
asserted. Both are stdlib-only and reuse the specimen's source,
constants and seed schedule, so records are directly comparable.

### 8.1 `toy_rvq_void_v2.py` — hygiene repair (record: `toy_rvq_void_v2_seed0.json`)

Fixes against the 22-probe adversarial census, each now covered by a
ported probe (23 probes, all landing in declared categories):

| Fix | Measured result |
|---|---|
| VOID is the null index, not sentinel 16 | 17-real-code book now round-trips (probe `seventeenth_real_code_roundtrips`); specimen misdecoded it to zero |
| Full input validation (finite, dims, taus present) | NaN threshold/input, missing/extra tau, ragged/short books all reject instead of failing open |
| decode validates range and the DIMS contract | negative index and short-book probes reject; decode may not redefine output dimension |
| measure() is null-safe | empty/zero-energy/zero-level inputs return records of nulls (nulls are outputs) |
| **Gated calibration** | train VOID rates **[0.0095, 0.0095, 0.0095, 0.0095]** against target 0.010; the ungated control in the same record reproduces the specimen's drift [0.0095, 0.011, 0.012, 0.013] exactly |

Claim outcomes: C1 pass (0.245521 -> 0.248381, unchanged), C3 pass,
C4 pass (0.028 -> 0.015, unchanged), C5 calibration pass (worst
held-out rate 0.008), C6 probe suite pass (0 mismatches).
**C2 energy identity still fails at 1.5036** — as declared in the
claim text: hygiene is not physics. The clean-data numerics of the
specimen are unchanged by validation, which is exactly the regression
signal wanted.

### 8.2 `toy_rvq_orthogonal.py` — physics repair attempt (record: `toy_rvq_orthogonal_seed0.json`)

The remaining VOID item from §5 was the power reading, "pending any
orthogonalizing redesign". This instrument implements it: after the
usual argmin/VOID walk selects codes, solve least squares over the
accepted-code span and **transmit the gains β** alongside the indices.
Decode is z_hat = Σ β_k c_k, so r ⊥ span by construction.

| Claim | Measured | Verdict |
|---|---|---|
| O1 projection energy identity | worst rel defect **2.6e-15** | **pass** |
| O2 unit-gain control, same stream | worst rel defect **1.5036325501281391** | fail (expected — exactly the specimen's number) |
| O3 dominance ratio proj/unit | **0.7511** (0.0571 vs 0.0760 residual frac) | pass (one-sided) |
| O4 gain channel cost | **3.971 gains/sample** held-out (train 3.962); zero singular-Gram fallbacks | pass |
| O5 VOID integrity | 0.0 structural | pass |

The pairing is the result: same data, same codes, same indices — only
the decode changes, and the identity defect moves from 1.50 to 1e-15.
**The power-conjugate reading of the contextual substrate is no longer
VOID; it is priced.** The price is a continuous gain channel — about
K real scalars per sample that are not symbols and cannot be coded as
symbols. In the bridge's own vocabulary: the gain channel is the
transformer modulus of this substrate, and projection decode is a
soft-ratio (calibrated) coupler, not an exact-ratio one. Side effect:
projection also cuts final residual energy by 24.9% against unit-gain
decode of the same stream (0.0571 vs 0.0760).

Still VOID, recorded not guessed: entropy-coded bit cost of the gain
channel (unmeasured); behavior on learned neural codebooks and real
data (unmeasured); singular-Gram fallback rate on large codebooks
(zero here, unmeasured elsewhere); any claim that β generalizes
across sources (refuted by construction until measured).
