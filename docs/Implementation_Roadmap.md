# Implementation Roadmap

**Revised 2026-08.** The previous version was written in relative months
("Month 1", "Months 2–6") with no anchor date, and every phase target was a
multiple of a speedup figure — 10×–100×, then 100×–1000×, then 1000×+. Its one
unchecked Month-1 item was *"Add basic benchmarks for EM field problems"*, and
it stayed unchecked. So the multipliers had nothing under them.

That item is now done: `Engine/engine_benchmark.py`. What it measured is in
§1, and it changed this document.

This roadmap is dated, and each item says what would settle it. Where a branch
has been refuted, it is marked dead with the claim id rather than quietly
dropped — a roadmap that only lists what is still alive is a roadmap you
cannot tell has been corrected.

```bash
python Engine/engine_benchmark.py     # §1, the measured numbers
python claims_index.py status         # what is registered, and what can fail
python playground/playground.py problems   # the 38 open problems
python graveyard.py                   # what was killed, and what it bought
```

---

## 1. What the performance claim actually was

`PerformanceTracker` reported `(32³ / n_points) × symmetry_reduction` as
`averageSpeedup`. That is a ratio of point counts times a factor for work the
solver does not skip. No clock entered it, though `total_time` was recorded in
the same call.

Timed against a uniform grid on the same sources, through the same optimizer:

| case | uniform pts | adaptive pts | point ratio | **measured** |
|---|---|---|---|---|
| dipole (asymmetric) | 32 768 | 2 150 | 15.2× | **0.48×** |
| quadrupole (2-fold) | 32 768 | 2 864 | 11.4× | **0.26×** |
| wire + charge | 32 768 | 2 024 | 16.2× | **0.31×** |

The adaptive path is **2× to 50× slower**, not 15–33× faster. ENG-1.

**The geometry is not the problem.** `SpatialGrid.createRegion` returns
exactly one sample point per leaf region, so the solver calls
`calculateFieldChunk` once per point — 2150 numpy calls on 1-element arrays.
Splitting the cost (dipole, resolution 32):

| | time |
|---|---|
| octree decomposition | 0.0645 s |
| uniform grid construction | 0.0104 s |
| field, one call per region — *as the solver does it* | 0.0597 s |
| field, same points in one call | **0.0023 s** |
| field, uniform grid in one call | 0.0562 s |

Batching is a **26× win on the field evaluation**, and at 15× fewer points the
octree is doing real work. But the decomposition costs more than the entire
uniform computation, so batching **alone** lands at 1.07× end to end. Both
halves have to come down. ENG-5.

Four smaller defects in the same metric are recorded as ENG-2, ENG-3, ENG-4
and ENG-6; ENG-3 is the one worth knowing about, because the reported figure
rose 1.50× for a symmetric configuration that took 1.89× *longer*.

---

## 2. Done, and verified

Each of these has tests that can fail.

- **GEIS encoder/decoder** — round-trips validated, 116 tests. The 8 states are
  the ⟨111⟩ bond directions, not octahedron vertices; the 3-bit result is
  unaffected, the derivation was corrected (2026-07).
- **11 domain bridge encoders** — 768 tests. Gray-coded, lossless round-trip.
- **Engine** — symmetry detection, adaptive octree, vectorised Coulomb and
  Biot–Savart, 58 tests. See §1 for what its performance numbers mean.
- **Frontend** — builds clean (`npm run build`). Not yet driven live in a
  browser against real interaction.
- **The audit apparatus** — `repo_guard.py` (4 stages), `claims_index.py`,
  `graveyard.py`, `explore.py`, `playground/`. 222 claim ids, 127 with a
  recorded statement, 166 with something executable pointed at them.
- **2600+ unittest cases** under `tests/`, all passing from the repo root with
  no `PYTHONPATH`.

---

## 3. Next — near-term, and each one is cheap

Ordered by cost-to-settle, not by ambition.

### 3.1 Make the adaptive path actually faster (ENG-5)

The measurement above is the specification. Two changes, both scoped:

- Batch the leaf points into one `calculateFieldChunk` call. Measured payoff
  26× on field evaluation; the fields are identical to 1e-12, which
  `tests/test_engine_metrics.py` pins.
- Bring the decomposition cost down — it is a Python recursion allocating a
  dict and two numpy arrays per leaf. Until it does, end-to-end stays at
  ~1.07×.

**Settled by:** `python Engine/engine_benchmark.py` reporting a measured
speedup above 1.0. Not by a point ratio.

### 3.2 The three cheap, decisive, unrun experiments

All three return a real result, and none needs a magnet, a cryostat, or a THz
source.

| id | experiment | cost |
|---|---|---|
| **FAB-3** | Are 8 implant states separable at >3σ in (R_s, carrier type, n)? | ~$3–6k |
| **BRG-6** | Piezoresistive dR/R at 0.1 % strain | a strain gauge and a four-point probe |
| **R2-3** | Bifilar CMRR at achievable matching tolerance | magneto-optic sampling at a stated frequency |

These gate the entire hardware path in §5. Doing them is worth more than any
amount of further specification.

### 3.3 Run the falsifiers that exist and have never been run

**NEG-2** and **NEG-3** have implemented falsifiers and no data. That is the
cheapest unclaimed result in the repository.

### 3.4 Close the five principles nothing catches

6 of 11 recurring failure shapes are mechanised. `python graveyard.py todo`
lists the screens with reach ≥ 2 that nothing runs automatically —
`enumerate-reachable-outputs` is at reach 7 across folders sharing no code, and
it looks mechanisable: sweep the input domain, list the outputs nothing
produces, make the author say which absences are intended.

---

## 4. Medium term

- **Hybrid symbolic + geometric compiler.** Unchanged in intent from the
  previous roadmap. Now gated on §3.1: a compiler that emits a slower path is
  not worth building yet.
- **GPU / WebGPU field acceleration.** Deferred deliberately. §1 shows the
  current bottleneck is call overhead and Python-side decomposition, neither of
  which a GPU fixes; porting first would move the overhead, not remove it.
- **Integration with symbolic AI agents.** The `adaptive_sim/` audit
  (ASF-1..16) is the cautionary case: an agent loop whose reasoning chain was
  prose it then grepped, which made the one knob its own diagnosis named
  unreachable. Structured diagnoses, and a provenance record that can be
  replayed, are preconditions rather than polish.
- **A response-claim runner (ASF-A).** Every claim in the archive is a
  threshold on one run. Nothing can currently test "X is correlated with
  parameter P", which is most of what a scaling result is.

**No multiplier is stated for this section.** The previous version promised
100×–1000×; §1 is what happened to the last such number.

---

## 5. The hardware path, corrected

The previous roadmap's Phase 3 ("Native Geometric Computing, 18–36 months,
geometric processors or FPGAs, 1000×+") sat on a physics layer that has since
been substantially refuted. What died, and what survived it:

**Dead:**

- **No magnetic state channel exists in silicon.** Si is diamagnetic at
  χ ≈ −4e-6 and 95.3 % of nuclei are spin-zero. A 5 µm cell carries 4e-19 A·m²,
  11 orders below a Hall sensor and 7 below a SQUID. Five documents proposed
  one. FAB-1, BRG-1.
- **Er³⁺ cannot hold coherence at 300 K.** The crystal-field gap is
  40–60 cm⁻¹ against kT = 208.5 cm⁻¹, so Orbach relaxation goes linear in T;
  T₂ ≤ 2T₁ caps it 8 orders below the headline 166 ms. ER-1.
- **The clamped Keating cluster has one minimum, not eight.** Keating is a sum
  of squares, so E ≥ 0 with a unique zero. 200 random starts find one, at any
  α, β > 0. KEA-1.
- **Two independent 8-state representations collapse under inversion.**
  `outer(v,v)` cannot see the sign of v, and the Keating energy is exactly even
  in the displacement. GIES-1, KEA-7.
- **The write pulse is ~700× too weak to move a spin.** R2-8.

**Survived, and load-bearing:**

- **8 states / 3 bits is unaffected** — the ⟨111⟩ set is real; only the
  octahedron-vertex derivation was wrong.
- **Strain replaces magnetism throughout.** Ξ_u = 9.16 eV gives 9.2 meV of
  valley splitting at 0.1 % strain — 40× the 2 T Zeeman figure — written
  piezo/optomechanically and read piezoresistively at dR/R ≈ 12 % (GF ≈ 121).
- **Index parity is site type, and it is free.** The 3-bit address space
  already carries a physically meaningful single-bit error-detecting code, with
  **J3** as the carrier invariant (trace and J2 are identical across all eight
  states).
- **The Keating parameters** α = 48.1 and β = 12.0 N/m are correct and reusable.
- **`Magnetic-bridge.md`'s FSM, protocol and hardware list** were kept intact;
  only the transduction layer was replaced.

**So the phase is not cancelled — its transduction layer changed, and the gate
is §3.2.** Until FAB-3, BRG-6 and R2-3 have been run, any date attached to
native geometric hardware is a guess. None is given here.

---

## 6. What is deliberately not in this roadmap

The previous version's long-term section promised "post-binary geometric
intelligence", "self-evolving codes", and gains that were "Unbounded —
qualitative leap". Those are not dropped because they are uninteresting. They
are dropped because as written **no observation could have contradicted them**,
which is the exact shape `repo_guard.py`'s null stage and `playground/`'s
`broken()` gate exist to catch, and it would be strange to run those gates on
incoming work while exempting our own plan.

The long-range intent still lives in `INTENT.md` and `Core-principle.md`, where
it is framed as intent rather than as a schedule.

`playground/OPEN_PROBLEMS.json` holds the 38 open problems in machine-readable
form, each with what would settle it. That file, not this one, is where the
work that has not been scoped yet belongs.

---

## Notes

Partial implementations are still worth shipping — that was true in the
previous version and survives. What changed is the standard for saying so: a
gain gets stated here once a clock has been on it.
