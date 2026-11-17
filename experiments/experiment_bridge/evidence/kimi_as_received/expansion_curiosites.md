# Expansion curiosités — explorative-math, three exact-inflation systems

**Scope.** The three expansion systems in `exact/inflation.py`: Fibonacci chain, nested pentagons, Penrose (Robinson-triangle) subdivision. All computations exact (`ZPhi` = a + b·φ, a,b ∈ ℚ; `Cyc5` = u + v·w, w² = −(2+φ)); no floats except where noted as a contrast arm. Repo: JinnZ2/explorative-math, branch main (pushed 2026-11-16), retrieved 2026-11-17. Stdlib only.

**Reproducibility baseline (OBSERVED).** `experiments/exact_inflation.py`, seed 0, rerun independently: output byte-identical to the committed `runs/exact_inflation_seed0.json`. Their claims re-confirmed: chain two-way agreement through 16 levels (2584 tiles); pentagon through 12 levels; Penrose through 10 levels (10946 triangles). Their float contrast arm: same constructions in binary floats drift to 1.046e-10 max difference, 2551/2585 positions unequal at level 16. Exact forms: zero drift.

Status tags follow house convention (PROPOSED before run; OBSERVED = computed and checked exactly; "no match" = pattern searched, none found; nulls kept).

---

## 1. Fibonacci chain (L = φ, S = 1; L→LS, S→L)

- **C1 — OBSERVED.** Level n word: |w| = F(n+2), #L = F(n+1), #S = F(n), all 17 levels (F(0)=0, F(1)=1). Level 16: 2584 = F(18).
- **C2 — Beatty skeleton, exact (OBSERVED).** Letter positions (1-indexed) at level 16: every L sits at ⌊k·φ⌋, every S at ⌊k·φ²⌋ — all 1597 L's and 987 S's, by exact integer comparison (no floats). The Rayleigh partition 1/φ + 1/φ² = 1 witnessed exactly. (Instrument: exact floor of a + b·φ via rational comparison with √5; stress-tested on 3000 random forms, 0 disagreements.)
- **C3 (OBSERVED).** Smallest period of every prefix of the substitution word, lengths 1..399: every value a Fibonacci number. Matches the repo's open question Q6 base observation.
- **Q6-probe, silver slope — OBSERVED, new.** Q6 asks: "at another irrational slope, which integer sequence do the prefix periods land on?" Characteristic Sturmian word of slope α = √2 − 1 = [0;2,2,2,…] built by exact floors in ℤ[√2] (a + b√2; exact floor stress-tested, 0/3000 disagreements), 4000 letters, prefixes 1..1499:
  - periods land on **1, 3, 5, 17, 29, 99, 169, 577, 985** — no exceptions;
  - this set is exactly **q₂ₖ ∪ {q₂ₖ + q₂ₖ₊₁}** where q = 1,2,5,12,29,70,169,408,985 are the convergent denominators of α (Pell numbers, A000129);
  - equivalently the interleave of A001653 (1,5,29,169,985; numbers n with 2n²−1 a square) and A001541 (3,17,99,577; a(n)=6a(n−1)−a(n−2));
  - golden case consistency: for the all-1s CF there are no intermediate semiconvergents, so only convergent denominators (Fibonacci) appear — recovering C3.
  - **PROPOSED beyond range:** prefix periods of the characteristic Sturmian word of slope α land on (a subset of) the convergent and intermediate-semiconvergent denominators of α's continued fraction. Consistent with the abelian-period theorem of Peltomäki (2020), where minimal abelian periods are multiples of convergent denominators or semiconvergent denominators.

## 2. Nested pentagons (inner pentagon = pentagram intersection points)

- **C4 — OBSERVED.** Generation k is exactly gen-0 scaled by (−1)ᵏ·φ^(−2k) (8 generations, vertex-by-vertex equality, up to the fixed index shift of 3).
- **C5 — OBSERVED, null kept.** Gen-1 vertices lie on exactly 2 gen-0 diagonals each (the repo's own check). Gen-2, gen-3, gen-4 vertices lie on **zero** gen-0 diagonals — deeper generations leave the original lines entirely.
- **C7 — exact identity (OBSERVED).** inner[i] = (v[i] + v[i+1])·φ⁻³ for all i — inner vertices sit on the edge-bisector rays at radius 1/φ² (since |vᵢ + vᵢ₊₁| = φ, the 10 union vertices lie on 10 rays spaced 36°, radii alternating 1, 1/φ²).
- **C8 — OBSERVED.** Squared circumradius of generation k is exactly φ^(−4k), and φ^(−4k) = F(4k+1) − F(4k)·φ as a ℤ[φ] form — the nesting radii are governed by every fourth Fibonacci number: (5,−3), (34,−21), (233,−144), (1597,−987), …

## 3. Penrose subdivision (Robinson triangles, seed: one acute triangle)

- **P1 — OBSERVED.** Counts at level n: acute = F(2n−1), obtuse = F(2n), total = F(2n+1), levels 0..10. Level 10 total 10946 = F(21).
- **P3 — OBSERVED.** Exactly **one** absolute area per colour per level: acute = seed·φ^(−2n), obtuse = seed·φ^(−2n+1). Ratio obtuse:acute = φ at every level. (Note: signed areas cancel — orientations mix; absolute areas are the invariant.)
- **P6 — the identity the tiling knows (OBSERVED).** Area conservation at level n is term-by-term the exact identity φ^(2n) = φ·F(2n) + F(2n−1) (both sides compared in ℤ[φ], n = 1..29).
- **P5b — edge law (OBSERVED).** At level n the squared edge lengths are exactly three powers of φ, with multiplicities: φ^(−2n−2) × F(2n−1), φ^(−2n) × 2·F(2n+1), φ^(−2n+2) × F(2n) — levels 1..8. (The committed run records "3 distinct squared edge lengths" at level 10; this is the full counting law.)
- **P7 — OBSERVED.** Vertex/edge census by exact dedupe: V−E+F = 1 at every level 0..8 (the patch remains a topological disk; no accidental exact vertex identifications). V(n) = 3, 4, 6, 12, 26, 58, 137, 338, 852 — **no match**: no Fibonacci-indexed or low-order linear recurrence found.
- **P8 — OBSERVED.** Coordination distribution at level 8 (tiles per vertex): {1:1, 2:18, 3:34, 4:313, 5:36, 6:288, 8:64, 10:98}. No vertex of degree 7 or 9; maximum 10 (full star).
- **P9 — OBSERVED.** Subdivision insertion points never coincide with pre-existing vertices (0 collisions, levels 1..8); new vertices per level equal insertion points minus **same-level** duplicates D(n) = 0, 1, 2, 7, 23, 65, 176, 473 — double insertions on shared edges subdivided from both sides. D(n): **no match** found.

## Read depth declaration

- `exact/` (zphi, cyc5, inflation, fold, corkscrew, volume): `__init__` and `inflation.py` read in full; `zphi.py`/`cyc5.py` read to the extent of the operators used (arithmetic, cross, norm2, inverse, hash).
- `experiments/exact_inflation.py` read in full; rerun seed 0 (see baseline).
- `open_questions.md` read for Q6/Q7 context; `README.md`, `README.claude-code-build.md` read.
- Method vocabulary borrowed from sibling repos (read to README depth): `study-aperture` (read-depth declaration, measured vs assumed), `formula-audit` (VOID rather than guess), `framework-instruments` (nulls are outputs), `method-layer` (preference-free ranking).
- OEIS identifications via web search: A000129, A001333, A001541, A001653, A120858; Peltomäki, J. Number Theory 2020 (abelian periods of Sturmian factors).

## Open threads (not chased here)

- Why only q₂ₖ (even indices) and the semiconvergents immediately after them appear as prefix periods at slope √2−1, within 1499 prefixes; longer words may admit q₂ₖ₊₁ — instrument is built, just needs a longer word.
- V(n) and D(n) sequences for Penrose: computed, unmatched.
- A natural next exact field: ℤ[√2] already exists in this session's instrument (used for the Q6 probe) — Ammann–Beenker octagonal substitution would sit beside `inflation.py` with ratio 1/(1+√2).
