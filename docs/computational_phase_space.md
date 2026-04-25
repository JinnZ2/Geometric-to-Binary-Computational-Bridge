# Computational Phase Space — Reading Guide

> Index to the computational-phase-space work. This used to be a
> *design notes* doc for a skeleton simulator. The skeleton has been
> superseded — the simulator is real, the results are in, and this
> page now exists to help readers navigate from the conceptual
> summary to the running code.

---

## Where everything lives

| Thing | Location |
|---|---|
| Dynamical silicon manifold — 9D `SiliconState`, metric, dynamics, regime atlas | [`Silicon/modules/`](../Silicon/modules/) |
| Package overview, state vector table, regime table, two-paths summary | [`Silicon/modules/README.md`](../Silicon/modules/README.md) |
| Octahedral × silicon integration plan (4 steps) | [`Silicon/modules/Octahedral_Integration.md`](../Silicon/modules/Octahedral_Integration.md) |
| Step 1 (live-fiber substitution) implementation | [`Silicon/integration_staging/octahedral_bundle.py`](../Silicon/integration_staging/octahedral_bundle.py) |
| Step 1 status + computational-phase-diagram finding | [`Silicon/integration_staging/STAGING_NOTES.md`](../Silicon/integration_staging/STAGING_NOTES.md) |
| Diagnostic runners (purity/ECP, vertex/entanglement) | [`Silicon/integration_staging/diagnose_*.py`](../Silicon/integration_staging/) |
| Published phase-space plots (PNG) | `Silicon/integration_staging/purity_ecp.png`, `purity_phase_portrait.png`, `diag_correlation_matrix.png`, `diag_vertex_vs_entanglement.png`, `diag_diagonal_vertex_zoom.png`, `step1_barycentric_weights.png`, `step1_dominant_vertex.png` |
| Module-level diagnostics from the pipeline demo | `Silicon/modules/silicon_state_trajectory.png`, `regime_weights.png`, `field_evolution.png`, `phase_portrait.png`, `omega2_sign_log.png`, `kernel_curvature.png` |
| Running the full pipeline | `python Silicon/modules/demo.py --steps 300 --seed 42` |

---

## What the phase space is

Computation is a trajectory in a 2D space spanned by:

* **Entanglement ratio** (x-axis): how nonlocal the kernel is.
  `0` = separable / diagonal. `1` = fully entangled / off-diagonal.
* **Operator purity** (y-axis): how pure the computational mode is.
  `1` = a single octahedral vertex dominates. `1/8 ≈ 0.125` = fully
  mixed across all 8 vertices.

Four quadrants, all four populated by real trajectories (see the
phase-portrait plots in `Silicon/integration_staging/`):

|                 | Low entanglement                              | High entanglement                             |
|-----------------|-----------------------------------------------|-----------------------------------------------|
| **High purity** | Structured single-mode. Boolean / solitonic. | Nonlocal pure. Entangled but coherent.        |
| **Low purity**  | Mixed separable. Probabilistic classical.   | Mixed entangled. Maximally non-classical.    |

`ECP = entanglement_ratio × (1 − purity)` — the Entanglement-Computation
Product — peaks in the bottom-right quadrant (nonlocal, not confined
to a single mode).

## The octahedral-vs-phase-diagram finding

From [`Silicon/integration_staging/STAGING_NOTES.md`](../Silicon/integration_staging/STAGING_NOTES.md):

> The diagonal vertices (110, 111) — which were intuitively expected
> to host entangled computation due to their "superposition"
> geometric character — are instead the signature of the
> **solitonic/structured attractor**. They correlate at +0.93 with
> the solitonic regime and −0.68 with entanglement. Conversely, the
> axis vertices (e.g., 000 +x) host the high-off-diagonal kernel
> structure.

Consequence: the octahedral encoding isn't a representational choice
— it's a computational phase diagram. Eight vertices = eight pure
modes; edges = transitions; interior = mixed computation. Trajectory
determines the operation the system performs at each moment.

## Operational map

Grounded in the measured correlations above, not a heuristic:

| Desired computation          | Purity target | Entanglement target | Octahedral target                       |
|------------------------------|---------------|---------------------|-----------------------------------------|
| Boolean logic                | `> 0.35`      | `< 0.3`             | Diagonal vertices (`P110`, `P111`)      |
| Entangled unitary            | `> 0.35`      | `> 0.5`             | Axis vertices (`P000`, `P010`, `P011`)  |
| Probabilistic inference      | `~ 0.125–0.2` | `< 0.3`             | Interior, multiple non-entangled vertices |
| Non-classical mixed          | `~ 0.125–0.2` | `> 0.5`             | Interior near axis vertices, peak ECP  |
| Readout / sensing            | any           | any                 | Near `Ω² = 0` boundary                  |

## Independent steering dimensions

From the regime atlas and kernel observables:

1. **Entanglement ratio** — steered via axis-vs-diagonal vertex targeting.
2. **Purity** — steered via single-vertex vs distributed-weight control.
3. **Spectral gap** — partially independent; controls reversibility.
4. **Ω²** — sign determines whether the system sits on a stable
   Riemannian sheet; `Ω² = 0` is the face transition between
   accessible vertex sets (Step 4 of the integration plan).

The strongest cross-correlation in the diagnostic plots is
`r(entanglement, spectral_gap) ≈ −0.99` — entangled kernels crush
their smallest eigenvalue. Treat it as a reversibility alarm when
designing tasks that need to be undone.

---

## How this hooks into the rest of the repo

* **GEIS** ([`GEIS/octahedral_state.py`](../GEIS/octahedral_state.py))
  is the static 8-state container; a trajectory's `dominant_vertex`
  stream can be emitted as a sequence of `OctahedralState` values
  for GEIS-layer tooling.

* **Engine gaussian splats** ([`Engine/gaussian_splats/octahedral.py`](../Engine/gaussian_splats/octahedral.py))
  defines the canonical 8-vertex tetrahedral basis. The bundle in
  `Silicon/integration_staging/octahedral_bundle.py` embeds the same
  eight vertices into physical S-space coordinates; reconciling the
  two vocabularies is Step 2–3 of the integration plan.

> **Coordinate-convention warning.** The GEIS and Engine octahedral
> tables index the eight vertices in *different* sign conventions and
> *different* bit orderings:
>
> | Source | Index 0 | Bit-to-axis map | Bit value 0 | Bit value 1 |
> |---|---|---|---|---|
> | `GEIS/octahedral_state.py::OctahedralState.POSITIONS` | `(+0.25, +0.25, +0.25)` | LSB → y, mid → x, MSB → z | `+` | `−` |
> | `Engine/gaussian_splats/octahedral.py::OctahedralStateEncoder.state_centers` | `(−1, −1, −1)` | LSB → x, mid → y, MSB → z | `−` | `+` |
>
> The two systems do not currently cross-import (verified by
> grepping `from GEIS` in `Engine/` and vice versa). Each encoder is
> internally consistent in its own namespace — but if you write a
> bridge that translates a GEIS index into an Engine state index,
> you must apply both an axis permutation and a sign flip. Future
> Step 2/3 of the integration plan should fix this drift, ideally
> by promoting one convention to a shared canonical table.

* **Regime-mediated QEC** ([`Silicon/core/regime_mediated_qec.py`](../Silicon/core/regime_mediated_qec.py))
  is where a trajectory's current regime label should be consumed
  for code-distance and threshold-surface decisions.

* **Intersection layer** ([`bridges/intersection/`](../bridges/intersection/))
  is the natural export path. Once the bundle produces a stable
  `(purity, entanglement, regime)` signature, add an
  `AdvancedComputationIntersectionRule` that emits a
  [`BasinSignature`](../bridges/intersection/base.py) so the running
  computation participates in RESONATE alongside the physical
  bridges (electric / gravity / sound / community).

---

## History

This page replaces the earlier `docs/advanced_computation_sim_notes.md`
and its companion `experiments/advanced_computation_sim.py`
skeleton. Those were conceptual placeholders written before the real
implementation landed; they have been removed because their content
is now either implemented in `Silicon/modules/` or preserved as
cross-references here.
