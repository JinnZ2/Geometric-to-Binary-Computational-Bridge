# FALSIFIER SURVEY — Run 2: Geometric-manifold- and Geometric-to-Binary-Computational-Bridge

Run under the adjusted admissibility rule of ADDENDUM 01 (SCOPE-DIFFERENT
admissibility, and the taxonomy test), identical protocol to Run 1
(JinnZ2/Simulators). Date of run: 2026-09-05.
Survey unit = top-level directory + a "(repo root)" unit for root-level
files. 16 units in Geometric-manifold- ("gm"), 30 in
Geometric-to-Binary-Computational-Bridge ("g2b").

## Counts (report.py emission)

```
cells total                                         623
  MEASURED (complete MEASURED_AS)                   537
  SCOPE-DIFFERENT (complete SCOPE_TRANSFORM)         19   (13 distinct transforms)
  UNKNOWN (fails its bar, reason stated)             56
  MISSING (unit states no falsifier)                 11
SCOPE-DIFFERENT lacking a complete transform          0
  (separate line per addendum §3: again zero — every
   admitted SCOPE-DIFFERENT carries reference +
   maps_to + breaks_at)
units covered                                      46/46
validation gate                                     0 schema errors
```

Per repo: gm — 109 cells (97 MEASURED / 1 SCOPE-DIFFERENT / 7 UNKNOWN /
4 MISSING). g2b — 514 cells (440 MEASURED / 18 SCOPE-DIFFERENT /
49 UNKNOWN / 7 MISSING).

## Method

Identical to Run 1: scripted three-mode extraction (pipe-table falsifier
columns, explicit Falsifier: blocks, paragraph fallback; extended here to
JSON/JSONL claim registers carrying falsifier fields), then parallel human-
rule coders writing MEASURED_AS or SCOPE_TRANSFORM per cell. Per the
addendum's constraint, coders were NOT shown any candidate kinds; the
taxonomy sort was performed blind, and the Run-1 candidate taxonomy
(K1/K2/K3/K4) was revealed only after the blind sort delivered.

Extraction yield: gm 79 mentions over 5 units; g2b 290 mentions over 16
units. All zero-hit units were verified by reading — several turned out NOT
missing (gm: addon_thermodynamic_control, atlas, bridges, repair, tests,
experiments; g2b: Mandala, GI, Kimchi, docs, github, mappings).

## Per-unit results — Geometric-manifold-

| unit | cells | MEASURED | SCOPE-DIFFERENT | UNKNOWN | MISSING |
|---|---|---|---|---|---|
| (repo root) | 4 | 3 | 0 | 1 | 0 |
| addon_thermodynamic_control | 3 | 3 | 0 | 0 | 0 |
| atlas | 16 | 16 | 0 | 0 | 0 |
| bridges | 2 | 2 | 0 | 0 | 0 |
| configs | 1 | 0 | 0 | 0 | 1 |
| data | 3 | 3 | 0 | 0 | 0 |
| docs | 41 | 38 | 1 | 2 | 0 |
| experiments | 7 | 6 | 0 | 1 | 0 |
| hypotheses | 1 | 0 | 0 | 0 | 1 |
| manifolds | 1 | 0 | 0 | 0 | 1 |
| repair | 7 | 4 | 0 | 3 | 0 |
| research_interface | 1 | 1 | 0 | 0 | 0 |
| scripts | 3 | 3 | 0 | 0 | 0 |
| sims | 17 | 17 | 0 | 0 | 0 |
| simulation | 1 | 0 | 0 | 0 | 1 |
| tests | 1 | 1 | 0 | 0 | 0 |

## Per-unit results — Geometric-to-Binary-Computational-Bridge

| unit | cells | MEASURED | SCOPE-DIFFERENT | UNKNOWN | MISSING |
|---|---|---|---|---|---|
| (repo root) | 154 | 148 | 6 | 0 | 0 |
| AISS | 8 | 8 | 0 | 0 | 0 |
| ASIS | 11 | 9 | 2 | 0 | 0 |
| Engine | 6 | 4 | 2 | 0 | 0 |
| Front end | 1 | 0 | 0 | 0 | 1 |
| GEIS | 8 | 8 | 0 | 0 | 0 |
| GI | 3 | 1 | 1 | 1 | 0 |
| Hurricane | 1 | 0 | 0 | 0 | 1 |
| Kimchi | 1 | 1 | 0 | 0 | 0 |
| Mandala | 3 | 3 | 0 | 0 | 0 |
| Negentropic | 15 | 13 | 0 | 2 | 0 |
| Silicon | 85 | 80 | 2 | 3 | 0 |
| adaptive_sim | 16 | 15 | 1 | 0 | 0 |
| atlas | 1 | 0 | 0 | 0 | 1 |
| bridges | 36 | 11 | 1 | 24 | 0 |
| docs | 1 | 0 | 1 | 0 | 0 |
| examples | 1 | 0 | 0 | 0 | 1 |
| experiments | 8 | 7 | 0 | 1 | 0 |
| fabrication | 14 | 11 | 1 | 2 | 0 |
| field | 18 | 18 | 0 | 0 | 0 |
| geometric_intelligence | 42 | 31 | 1 | 10 | 0 |
| github | 1 | 1 | 0 | 0 | 0 |
| legacy | 3 | 3 | 0 | 0 | 0 |
| mappings | 2 | 2 | 0 | 0 | 0 |
| playground | 51 | 45 | 0 | 6 | 0 |
| scripts | 1 | 0 | 0 | 0 | 1 |
| sensing | 5 | 5 | 0 | 0 | 0 |
| src | 1 | 0 | 0 | 0 | 1 |
| symbols | 1 | 0 | 0 | 0 | 1 |
| tests | 16 | 16 | 0 | 0 | 0 |

## MISSING units (11)

gm: configs, hypotheses, manifolds, simulation. g2b: Hurricane, Front end, atlas, examples, scripts, src, symbols.

Of note: gm/hypotheses holds auto-generated claim lists whose
"Contradicted/refuted claims" sections exist but are empty — the
falsification conditions live upstream in data/claim_tree.json (a MISSING
with a forwarding address). gm/manifolds exports its checkable contracts to
atlas/exports/manifold_invariants.json. g2b's seven are tooling/data units
(scripts, src, symbols, examples, atlas, github-adjacent) plus Hurricane,
which computes correlations and forecasts but states no falsifier.

## The taxonomy test — Run 2 and merged result

Input: 19 SCOPE-DIFFERENT cells, collapsing to 13 distinct transforms (six
cross-unit restatement pairs: ASF-11, ENG-1, ENG-3, NLS-3, TMP-2, TRD-4).

### Blind sort (derived before any menu was shown)

- **Kind 1 — wrong reference class** (re-baseline repairs), N=3:
  ASIS/F2 (uniform vs pretrained-marginal baseline), ASIS/F6 (raw flag rate
  vs null-stream baseline), Silicon/F9 (raw vs covariate-adjusted BMR).
- **Kind 2 — proxy instrument, no transform exists** (only re-measurement
  repairs), N=3: docs/F1, ENG-1, ENG-3 — point-count × symmetry quoted as
  "speedup" 11–16× where wall-clock measured 0.26–0.48×; in ENG-3 the proxy
  moves OPPOSITE to the truth.
- **Kind 3 — missing unit/convention conversion** (explicit rescaling
  repairs), N=4: ASF-11 (rate consumed as Bernoulli p), TMP-2 (TCR at 15 C
  vs specified 20 C), TRD-4 (absolute vs relative slope), Silicon/F7
  (CV² per cycle vs ½CV² per transition).
- **Kind 4 — frame-relative referent** (only disambiguation repairs), N=3:
  F-TETRA-SCOPE (straggler), GI/F2 (600k MWh whole-storm vs salt-gradient
  sub-region), NLS-3 (scale as property of result vs of experiment).

Blind verdict: SEVERAL; sharpest boundary is "no transform exists even in
principle".

### Correspondence to Run-1 candidate kinds (mapping done after reveal)

- Blind Kind 3 → **K1**, cleanly (closed-form conversions).
- Blind Kind 2 → **K3 homonym**, not K4: "speedup" names two quantities with
  no conversion even in principle; ENG-3's opposite-sign move rules out any
  monotone calibration. The two runs independently converged on the same
  sharpest boundary.
- Blind Kind 1 → **not K2** — the defect is the comparison reference class,
  not the accounting boundary. Recorded as a NEW kind: **K5 reference-class
  re-baseline**.
- Blind Kind 4 stragglers: GI/F2 → canonical **K2**; NLS-3 → **K3**;
  F-TETRA-SCOPE remains unassigned (straddles K1/K3).
- **K4 was NOT replicated**: zero Run-2 members; it stays a Run-1 kind.

### Merged candidate taxonomy (both runs, distinct N = 22)

| Kind | Definition | Run 1 | Run 2 | Combined |
|---|---|---|---|---|
| K1 frame/convention difference | same quantity, different unit/convention/frame; conversion exists | 2 | 4 | 6 |
| K2 boundary difference | same quantity, different accounting boundary | 1 (+1 straddle UNI_055) | 1 | 2 (+1) |
| K3 homonym | different quantities, one name; no conversion in principle | 1 | 4 | 5 |
| K4 model-substrate calibration gap | quantity identity never established; needs empirical calibration | 4 | 0 | 4 |
| K5 reference-class re-baseline (new) | same quantity, wrong null/baseline/adjustment set | 0 | 3 | 3 |
| unassigned straggler | F-TETRA-SCOPE (K1/K3 straddle) | 0 | 1 | 1 |

**Verdict on the open question: SEVERAL — five candidate kinds now, not
one, and not three.** Effect of the added 13 transforms: K1 and K3
stabilized (K3 sharpened into the most robust discriminator: "no conversion
even in principle"); K2 gained a clean member; K4 did not replicate
(remains single-run, single-folder-concentrated); the reference-change
space split, contributing K5. Nothing merged across kinds.

Caveats: N=22 distinct; largest kind has 6 members; K4 and K5 are
single-run kinds; 9 of 13 Run-2 transforms originate in g2b's
CLAIMS_REGISTER.json or its restatements (one register's idiom);
F-TETRA-SCOPE excluded from kind counts.

## Anatomy of UNKNOWN (56 cells)

- Unregistered register slots — rows whose source carries "_no recorded
  statement_" (g2b geometric_intelligence ×10, bridges ×2, fabrication ×2):
  the register reserves a falsifier-shaped slot with nothing in it. This is
  the run-2 analogue of run 1's bare-dash fields, now institutionalized in
  the claim register itself.
- Circular or undefined predicates — NEG-11 ("degrades" defined
  circularly), SED f_climate/f_adapt with no operational definition,
  repair/kl_basin ("KL is wrong" undefined).
- Proof obligations stated as falsifiers — SEED-4 (proof of injectivity),
  repair/iss_pending.
- External-result dependencies with no in-repo thresholds — docs IIT/GNW,
  GI 95%-accuracy claim refuted only by absence of data.
- Semantic counterexample requests — NEG-9 and the playgrounds' six
  open problems whose settling quantity does not exist yet.

## Deviations and limitations

- Coding is from reading, not execution. g2b's CLAIM_TABLE.fab.json
  (referenced by FALSIFIABILITY_NOTICE and metadata.json) is absent from the
  checkout — noted on fabrication F7.
- Register-derived claims whose homes are other folders are coded as
  (repo root) cells; cross-unit restatements kept per unit with notes, per
  the one-cell-per-distinct-falsifier-per-unit rule (this is why
  SCOPE-DIFFERENT cell count 19 > distinct transforms 13).
- Both repos were fetched via codeload zip (git TLS failures); trees are
  main@2026-09-05.

## Files

- `cell_records_run2.jsonl` / `cell_records_run2.csv` — all 623 cells.
- `survey2/raw_hits_gm.jsonl`, `survey2/raw_hits_g2b.jsonl` — extraction
  mention lists.
- `survey2/scope_different_cells_run2.json` — the 19 transforms sorted.
- `survey2/batches2/gm.jsonl, g2b_a.jsonl, g2b_b.jsonl` — per-coder output.
