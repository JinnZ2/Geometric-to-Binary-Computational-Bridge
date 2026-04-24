# Alternative-Computing Integration Schedule

> Roadmap for extending the ternary / stochastic / quantum interpreter
> layer (`bridges/*_alternative_compute.py`) to every domain encoder
> in the repo. Supersedes nothing; complements the branch-point
> architecture described in `alternative_computing_bridge.md`.

---

## Status snapshot

Run these two helpers at any time for the up-to-date picture:

```python
from bridges.integration_pipeline import (
    domains_with_alternative,
    domains_missing_alternative,
)
list(domains_with_alternative())     # wired up today
list(domains_missing_alternative())  # scheduled below
```

At time of writing:

| Domain           | Binary encoder | Per-domain alt interpreter | Integration entry |
|------------------|----------------|-----------------------------|----------------------|
| electric         | ✅              | ✅                            | `electric_full_alternative_diagnostic` |
| sound            | ✅              | ✅                            | `sound_full_alternative_diagnostic`    |
| gravity          | ✅              | ✅                            | `gravity_full_alternative_diagnostic`  |
| community        | ✅              | ✅                            | `community_alternative_diagnostic`     |
| magnetic         | ✅              | ⬜ scheduled                  | (pending)            |
| light            | ✅              | ⬜ scheduled                  | (pending)            |
| wave             | ✅              | ⬜ scheduled                  | (pending)            |
| thermal          | ✅              | ⬜ scheduled                  | (pending)            |
| pressure         | ✅              | ⬜ scheduled                  | (pending)            |
| chemical         | ✅              | ⬜ scheduled                  | (pending)            |
| consciousness    | ✅              | ⬜ scheduled                  | (pending)            |
| emotion          | ✅              | ⬜ scheduled                  | (pending)            |
| biomachine       | ✅              | ⬜ scheduled                  | (pending)            |
| coop             | ✅              | ⬜ scheduled                  | (pending)            |
| cyclic           | ✅              | ⬜ scheduled                  | (pending)            |
| resilience       | ✅              | ⬜ scheduled                  | (pending)            |
| vortex           | ✅              | ⬜ scheduled                  | (pending)            |
| geometric_fiber  | ✅              | ⬜ scheduled                  | (pending)            |

Binary coverage is now driven by
`Silicon/core/bridges/adapters.BRIDGE_ENCODERS`, so the binary path
inherits new domains automatically. Registration for per-domain
alternative interpreters lives in
`bridges/adapters/ternary_adapter.py` (`_ALTERNATIVE_REGISTRY`). Flip
a domain from `None` to
`"bridges.<domain>_alternative_compute:<domain>_full_alternative_diagnostic"`
once the module exists — no dispatcher changes required.

## Paradigm coverage

Seven paradigms from `bridges/unified_alternative_registry.PARADIGM_REGISTRY`:

| Paradigm       | Family       | Dispatchable via `encode_state(mode=...)` | Implementation |
|----------------|--------------|--------------------------------------------|----------------|
| ternary        | per-domain   | ✅ `"ternary"` / `"alternative"` / `"alt"`  | per-domain diagnostic |
| quantum        | per-domain   | ✅ `"quantum"`                              | per-domain diagnostic |
| stochastic     | per-domain   | ✅ `"stochastic"`                           | per-domain diagnostic |
| neuromorphic   | cross-domain | ✅ `"neuromorphic"` / `"spike"`             | `neuromorphic_wrap_encoder` |
| memristive     | cross-domain | ✅ `"memristive"` / `"memristor"`           | `memristive_wrap_conductivity` |
| reservoir      | cross-domain | ✅ `"reservoir"` / `"echo"`                 | `reservoir_wrap_geometries` (single-domain) |
| approximate    | —            | ⬜ scheduled                                | `ApproximateInstitutionalRedundancy`, `ApproximateTAF` — no generic `*_wrap_*` entry yet |

*Per-domain paradigms* are served by the single
`<domain>_full_alternative_diagnostic` function, which already bundles
ternary + quantum + stochastic views. The dispatcher returns the whole
diagnostic object regardless of which of the three names was used;
callers pick the relevant slice via the dataclass attributes.

*Cross-domain paradigms* take any compatible geometry dict. For
multi-domain reservoirs (the intended use — gravity ↔ electric ↔
sound coupling), call `bridges.reservoir_bridge.reservoir_wrap_geometries`
directly with `{domain: geometry, ...}`; the single-domain dispatcher
shortcut is a convenience for unit-tests and simple pipelines.

---

## Integration template (per bridge)

Every new `<domain>_alternative_compute.py` module must provide:

1. **Ternary state class** — an `IntEnum` whose members capture the
   three-regime physics that the binary encoder collapses. The
   ZERO / EQUILIBRIUM / NEUTRAL member is the one binary encodings
   routinely erase; its presence is the point of the file.

2. **Classifier function** — `classify_<quantity>_ternary(value,
   threshold=...)`. The threshold defaults must be tied to a real
   physical floor (noise floor, measurement uncertainty, thermal
   energy), not to an arbitrary constant.

3. **Quantum superposition class** — a `@dataclass` that captures
   whatever is frequency-coupled or wavelength-coupled in the
   domain's geometry. Must expose a `diagnose()` string and any
   derived spatial / energetic distributions.

4. **Stochastic class** — a `@dataclass` that returns
   `<quantity>_probability` rather than a boolean. Uses domain-native
   noise (Johnson-Nyquist for electric, Planck for thermal, Allan
   variance for time, etc.).

5. **Composite diagnostic dataclass** — holds the per-sample ternary
   states, the skin/superposition analyses, the stochastic analyses,
   and the reference binary encoding. Exposes `summary()`.

6. **Top-level entry point** —
   `<domain>_full_alternative_diagnostic(geometry, frequency_hz=None)`.
   Matching the naming lets the registry resolve it automatically.

7. **Integration hook** — wire into `_ALTERNATIVE_REGISTRY` and add a
   row in the status table above. No changes to any downstream code
   are required; the adapter registry handles routing.

Use `bridges/electric_alternative_compute.py` as the canonical
reference implementation (767 lines, covers all six sections).

---

## Per-bridge scheduling

Priority order reflects *how much information the binary encoder is
currently erasing* in each domain — domains where the ternary /
quantum layer recovers the most physics ship first.

### Phase 1 — erased-zero domains (highest priority)

These bridges all hide a physically meaningful "zero / neutral /
equilibrium" state behind a single bit.

#### magnetic

* **What's erased:** inflection between north / zero / south at
  domain walls; vortex cores; KT-phase transition neighbourhoods.
* **Ternary states:** `NORTH / NEUTRAL / SOUTH` or equivalently
  `CHIRAL_POS / ACHIRAL / CHIRAL_NEG` for spin textures.
* **Quantum layer:** superposition of Larmor precession phases.
* **Stochastic layer:** thermal magnonic occupation via the existing
  `Engine/magnonic_sublayer.py`.
* **Hook:** reuse `Engine/kt_annealer.py` for the phase-transition
  neighbourhood analysis.

#### wave

* **What's erased:** wavefunction node positions; phase discontinuities
  at π; tunnelling-vs-reflection ambiguity at barriers.
* **Ternary states:** `TRANSMITTED / EVANESCENT / REFLECTED`.
* **Quantum layer:** the wave encoder is already the richest
  candidate — every field it encodes already exists as a superposition.
* **Stochastic layer:** decoherence rate as probability of basis
  collapse per sample.

#### thermal

* **What's erased:** temperature signs relative to equilibrium;
  radiative-vs-conductive crossover; thermodynamic near-zero regimes.
* **Ternary states:** `ABOVE_EQUIL / AT_EQUIL / BELOW_EQUIL`.
* **Quantum layer:** Planck distribution as continuous superposition
  over mode occupation.
* **Stochastic layer:** Boltzmann shot-noise on small heat fluxes.

### Phase 2 — phase-conflating domains

Bridges whose binary encoder conflates two distinct phase regimes as
"on/off."

#### light

* **Ternary states:** `LINEAR / CIRCULAR / UNPOLARIZED`.
* **Quantum layer:** coherent-state superposition over photon number.
* **Stochastic layer:** Poisson photon-counting statistics.

#### pressure

* **Ternary states:** `COMPRESSIVE / HYDROSTATIC / TENSILE`.
* **Quantum layer:** phonon superposition.
* **Stochastic layer:** surface-roughness contact pressure distribution
  (maps closely onto the existing `StochasticContactResistance`
  pattern from electric).

#### chemical

* **Ternary states:** `OXIDIZED / EQUILIBRIUM / REDUCED`, or
  `ACID / NEUTRAL / BASE` depending on geometry schema.
* **Quantum layer:** electronic-state superposition at bonding
  orbitals.
* **Stochastic layer:** reaction-rate Poisson statistics and kinetic
  Monte Carlo bounds.

### Phase 3 — cognitive/affective bridges

These bridges already carry more uncertainty than their binary
counterparts. The alternative layer is primarily about *preserving*
that uncertainty instead of collapsing it to a confidence threshold.

#### consciousness

* **Ternary states:** `FOCUSED / DIFFUSE / DISSOCIATED`, mapped from
  Φ and attention-entropy.
* **Quantum layer:** integrated-information superposition across
  candidate partitions.
* **Stochastic layer:** Fisher-information uncertainty surface.

#### emotion

* **Ternary states:** PAD → `APPROACH / NEUTRAL / AVOID` per axis.
* **Quantum layer:** affective superposition until drill-target
  evaluation collapses to a single physical-bridge target.
* **Stochastic layer:** empirical PAD-state distribution over
  recent history (already present as the drill-loop input).

---

## Engine-layer collapse sites

Separate from the per-bridge work, several Engine/ modules currently
collapse distributions via `np.argmax` or hard thresholds. The shared
tool is `bridges/probability_collapse.DistributionCollapse`, which
preserves dominant / runner-up / entropy / ternary-regime while still
exposing a `dominant_index` that matches the old argmax integer. New
call sites should use `collapse_distribution(probs)` instead of
`int(np.argmax(probs))`.

| Site | Status | Method | Notes |
|------|--------|--------|-------|
| `Engine/gaussian_splats/octahedral.py` | ✅ done | `Gaussian8FieldSource.state_collapse()` | Non-breaking superset of `most_likely_state()` |
| `Engine/gaussian_splats/rhombic.py` | ✅ done | `Gaussian32FieldSource.state_collapse()` | Ditto, 32 vertices |
| `Engine/gaussian_splats/octahedral.py:170` | ⬜ scheduled | `OctahedralStateEncoder.decode_gaussian_to_state` | `(state_bits, confidence)` → add `(state_bits, collapse)` overload |
| `Engine/kt_annealer.py` | ⬜ scheduled | Expose `phase_regime` (above / at / below T_KT) as a `DistributionRegime` derived from coherence-at-T_KT |
| `Engine/geometric_transformer_engine.py:190` | ⬜ scheduled | `predict()` → add `predict_collapse()` that returns top-k + attention entropy |

## Engine → dispatcher handoff

| Site | Status | Method |
|------|--------|--------|
| `bridges/field_adapter.py` | ✅ done | `field_to_alternative(field_data, mode="dual")` projects solver output through `encode_state` |
| `bridges/sensor_suite.py` | ⬜ scheduled | `AlternativeSensorSuite` parallel-compositor over every domain's ternary interpreter |
| `bridges/vortex_bridge.py` | ⬜ scheduled | Replace `wp > threshold` with ternary winding classification |
| `bridges/wave_encoder.py:205` | ⬜ scheduled | Replace `probability_density > 0.5` with `DistributionRegime` over the Born-rule mass |
| `bridges/physics_guard.py` | ⬜ scheduled | Extend pass/fail to `satisfied / marginal / violated` |

---

## Cross-cutting work (after all bridges are wired)

1. **Field-level propagation.** `bridges/ternary_field.py` currently
   models electrical charge/current channels. Add sibling fields
   `ternary_magnetic_field.py`, `ternary_thermal_field.py`, etc., or
   generalise `TernaryField` so the channel semantics are carried by
   a domain plug-in.

2. **Event-driven cross-domain scheduling.** `bridges/event_scheduler.py`
   today only detects zero crossings in a scalar signal. Extend it to
   dispatch events when *any* bridge's ternary state transitions, so
   upstream orchestrators can treat state-flips as interrupts.

3. **Sensor-suite wiring.** `bridges/sensor_suite.py` composes all
   domains as a parallel-field vector. Add a parallel
   `alternative_sensor_suite` that runs every domain's alternative
   diagnostic alongside its binary encoding and emits a merged
   dual-path representation.

4. **Frontend surfaces.** `Front end/` currently visualises binary
   field magnitudes. Once three or more alternative interpreters are
   live, add a toggle that overlays ternary state colouring
   (red / grey / blue for the three regimes) on the same grid.

5. **C acceleration.** `experiments/c/` handles geometric NFS hot
   paths. The ternary classifiers themselves are cheap, but the
   tensor-field propagation and zero-crossing sweep become bottlenecks
   at production grid sizes. A C or SIMD port belongs on this list
   once the Python implementation has stabilised.

---

## Pull-request checklist

When submitting the alternative-compute module for a new domain:

- [ ] `bridges/<domain>_alternative_compute.py` created following the
      template above.
- [ ] Entry registered in `bridges/adapters/ternary_adapter.py`
      (`_ALTERNATIVE_REGISTRY`).
- [ ] Test file `tests/test_<domain>_alternative.py` covers the
      classifier thresholds, the stochastic probability derivation,
      the skin/superposition derivation, and one end-to-end
      `<domain>_full_alternative_diagnostic` call.
- [ ] `tests/test_alternative_integration.py`:
      `TestAdapters.test_alternative_adapter_availability_flags`
      extended so the new domain appears in the `True` branch.
- [ ] Status table in this file updated.
- [ ] `docs/gaussian_splats/` or domain-specific docs note the
      addition if the new module introduces a new geometric
      vocabulary.
