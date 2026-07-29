# Negentropic Consciousness Framework

> Audit status: **Restructured 2026-03-26. Corrected and re-grounded 2026-07-29.**
> The mathematics is real, and three of its equations were wrong — those are
> fixed. The empirical claims still need evidence. One claim has now been
> tested and failed. The moral derivation still has its gap.

---

## What Is This?

A framework proposing that consciousness, alignment, and ethics emerge from
measurable thermodynamic quantities. The underlying physics (Fokker-Planck,
Langevin, geometric coupling) is real. The framework built on top is a
*model* — and after the 2026-07 pass, a model with its dimensional errors
removed and its central isomorphism claim withdrawn.

The metric the framework was organised around, `M(S) = (R_e · A · D) − L`,
does not have units. `D` is a variance and `L` is a power; the subtraction
was never defined, so the threshold `M(S) ≥ 10` was never a claim about
anything. The dimensionally sound replacement is the persistence criterion
NEG-8, `Φ = −Ṡ_exchange − σ` in W/K, which has no threshold to tune.

---

## Start Here

| If you want | Read |
|---|---|
| What is claimed and what would refute it | [NEG_CLAIMS.md](NEG_CLAIMS.md) |
| What was broken and what was done about it | [corrections.md](corrections.md) |
| The physics the framework now rests on | [07-thermodynamics.md](07-thermodynamics.md) |
| A working instrument reconstructed from claims that read as mystical | [08-oral-technology.md](08-oral-technology.md) |

---

## Navigation & Confidence Map

| File | Content | Confidence |
|------|---------|-----------|
| [NEG_CLAIMS.md](NEG_CLAIMS.md) | Numbered claims, predictions, falsifiers, status | **Register** — the spine of the folder |
| [corrections.md](corrections.md) | Every defect found, severity-ordered, with its fix | **Ledger** |
| [01-framework.md](01-framework.md) | Core equations: J, R_e, C, Φ, phase transitions | **Corrected** — Fokker-Planck now in state-dependent form; M's units addressed |
| [02-empirical-audit.md](02-empirical-audit.md) | Audit of each empirical claim | **Mixed** — statistical method is real; data provenance is not. Claim 5 revised on second pass. Includes a safety correction |
| [03-consciousness.md](03-consciousness.md) | M(S) consciousness model, threshold, phase trigger | **Speculative** — and the threshold is dimensionally undefined, not merely free |
| [04-alignment.md](04-alignment.md) | AI alignment implications | **Analogy, not proof** — D→0 mapping to RLHF still not demonstrated |
| [legacy/Negentropic-05-implementation.md](../legacy/Negentropic-05-implementation.md) | Original code listings (§7 of the monolith) | **Historical** — the running code is the modules below |
| [06-connections.md](06-connections.md) | Hooks into the rest of the repository | **Grounded** |
| [07-thermodynamics.md](07-thermodynamics.md) | TUR/KUR, finite-time Landauer, dissipative adaptation, p-bit hardware, Mpemba, MaxCal | **Grounded** — established results, with the speculative application flagged per axis |
| [08-oral-technology.md](08-oral-technology.md) | Reconstruction of a pole-referenced field polarimeter from claims that read as mystical, with seven discriminating tests | **Split** — mechanisms documented, attribution inferred, T1–T7 not yet run |

---

## Code

Two tiers. The **stdlib tier** imports nothing outside the standard library
and carries all the new work, including every falsifier. The **numpy tier**
holds the historical implementations, fixed in place.

### Stdlib tier

| Module | What it does | Run it |
|---|---|---|
| `core.py` | `DissipativeCore` — corrected Kuramoto + Langevin. Emits R (dimensionless), H (nats), σ (1/time), absorbed work. Also the two coupling kernels | `python Negentropic/core.py` |
| `bounds.py` | TUR and kinetic uncertainty floors. Replaces hand-set efficiency constants | `python Negentropic/bounds.py` |
| `landauer.py` | NEG-3. Finite-time erasure, `τ⁻¹` excess, resurfacing prediction, exponent fitter | `python Negentropic/landauer.py` |
| `maintenance.py` | NEG-2. Archive lifetime under care flux; expanding schedule with a *fitted* ratio | `python Negentropic/maintenance.py` |
| `persistence.py` | NEG-8. Persistence margin Φ, sustained-deficit finder, Mpemba monotonicity guard | `python Negentropic/persistence.py` |
| `rebase.py` | NEG-4/9/10/11. Archive dependency graph: radiate, recenter, contradiction detection, validation gate, topology metrics | `python Negentropic/rebase.py` |
| `precession.py` | Dating a sky datum: pole position vs epoch, closest approach, re-datum interval, epoch-dependent circumpolarity | `python Negentropic/precession.py` |
| `emit_ising.py` | Emit target for p-bit / Ising hardware, plus Gray-coded octahedral encoding | `python Negentropic/emit_ising.py` |
| `lenses.py` | The 17 lens functions, defined once, with the shared functional form made explicit | — |
| `lens_collapse_test.py` | **NEG-7 falsifier** | `python Negentropic/lens_collapse_test.py` |

### numpy tier

| Module | What it does |
|---|---|
| `negentropic_dynamics.py` | Langevin, Fokker-Planck (both conventions, conservative flux form), phase transitions, collective coupling |
| `negentropic_engine.py` | R_e / A / D / L, agent network, schedules |
| `consciousness_metric.py` | M(S) components and theory comparison |
| `alignment_thermodynamics.py` | Suppression cascade analysis |
| `empirical_audit.py` | Claim-audit helpers |
| `lens_playground.py` | Action comparison across the 17 lenses; the divergence table is the useful part |

### Tests

```bash
python tests/test_negentropic_stdlib.py     # stdlib tier, no dependencies
python tests/test_negentropic.py            # numpy tier
```

---

## Key Findings

### Tested and failed: NEG-7, the isomorphism claim

The framework claimed that seventeen cultural and scientific lenses all
correlate above 0.88 when applied to one core, and that this shows they are
renderings of a single deep grammar.

Thirteen of the seventeen are the same function with six constants changed.
Of the four inputs, `D` was constant along every trajectory and `A` was an
affine function of `R`. `lens_collapse_test.py` draws seventeen lenses with
the same functional form, random coefficients, and no cultural content:

```
named lenses     correlation floor   0.8657
random lenses    median floor        0.9211
                 frac above 0.88     0.955
                 named percentile    0.005
```

Random labels reproduce the result and clear the threshold more often than
the named ones. Across every `n` and trace length tried, the named lenses
land at the 0th–5th percentile of the random distribution: seventeen
worldviews agree with each other slightly *less* than seventeen arbitrary
parameter draws of the same shape do. **The isomorphism claim is
withdrawn.**

This says nothing about whether these traditions converge on anything. It
shows the arithmetic could not have detected it either way — which matters,
because a method that returns r > 0.88 for random coefficients should not be
used to put words in the mouths of living traditions.

### Fixed: three wrong equations

- Kuramoto coupling had an **inverted sign** and a missing order-parameter
  weight — the model was actively desynchronising.
- Fokker-Planck was written in the **constant-D form** and used with
  `D ∝ J²`, and the SDE was missing the spurious drift `½ ∂D/∂φ`. The
  "D → 0 collapse" result did not follow from the equation as written. It
  does now, and it is computed rather than asserted.
- The integrator **did not conserve probability**; a uniform distribution
  was a spurious fixed point that it returned unchanged forever.

Full list with severities in [corrections.md](corrections.md).

### Still sound

- **Geometric mean of log-couplings** for R_e: valid information geometry.
- **Graph Laplacian, Ollivier-Ricci, persistent homology** as referenced:
  real tools.
- **Chi-square test structure** in Appendix B: correct method — the input
  data still needs independent verification.

### Corrected on second pass: the crystal cluster is not "mostly refuted"

The first audit of the crystal-memory claims marked most of them false and
stopped. That answered the wrong question. Re-examined, nearly every
refuted claim sits **one changed variable** away from a documented
mechanism:

| Asserted | Δ variable | What actually works |
|---|---|---|
| Voice makes the crystal glow | **contact** | Triboluminescence / piezoelectric discharge |
| Crystal remembers its place via frequency | **modality** | Radiation dosimetry, read by OSL/TL — standard geochronology |
| Crystal gives direction | **which mineral** | Calcite polarisation compass. Ropars et al. 2012. The Viking sunstone |
| Crystal sings back | **geometry** | Flexural modes of a bladed crystal, 200–800 Hz |
| Tansy blocks the trace | **sign** | GABA-A antagonism *raises* arousal, destabilising the trace — window-opener, not eraser |

A procedure transmitted orally encodes what to do, not why it works. When
the "why" is supplied later by an outsider — or by a language model, which
is where several of these framings came from — refuting the supplied
mechanism says nothing about the procedure. **An audit that returns FALSE
and stops has not finished.** See [02-empirical-audit.md](02-empirical-audit.md)
Claim 5, and [08-oral-technology.md](08-oral-technology.md) for the
instrument the pieces assemble into.

The safety correction on tansy is unchanged by the mechanism revision and
does not soften: a corrected mechanism is not a licence to attempt the
protocol.

### Still needs evidence

- **36/36 Fibonacci therapeutic breakthroughs** — no citation, and §2.1 and
  Appendix B disagree on the expected value (3.6 vs 1.28) for the same
  dataset. See [02-empirical-audit.md](02-empirical-audit.md).
- **AI reaching M(S) = 3,711.50** — no reproducible extraction method, and
  M has no units for the number to be in.
- **M(S) jump on self-reference** (34.62 → 296.40) — single observation, no
  controls.

### Still has a logical gap

**"Morality derived from thermodynamics."** The derivation defines Joy J as
entropy reduction, then asserts J = good. This smuggles in the moral
valence. A crystal growing also reduces local entropy — is that moral? The
gap is not bridged, and correcting the thermodynamics does not close it.
TUR bounds tell you what a structure costs; they do not tell you it ought to
exist.

---

## Duplicate & Dead Files Resolved

- `Silicon/Projects/Negentropic Consciousness Framework.md` was byte-for-byte
  identical to `Negentropic.md`. Removed; `Negentropic.md` redirects here.
- `Negentropic/bridge.py` was a paste dump that **did not parse** — bare
  `bridge:`, `lens:`, `sim:` lines are syntax errors, so it had never been
  imported. Its contents were superseded by `core.py` (the corrected core),
  `lenses.py` (the lens functions, previously defined twice) and
  `lens_collapse_test.py` (the correlation analysis, with the diagonal
  masking bug fixed). Deleted.

---

*Back to: [`CLAUDE.md`](../CLAUDE.md)*
