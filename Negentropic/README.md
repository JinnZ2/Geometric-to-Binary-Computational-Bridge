# Negentropic Consciousness Framework

> Audit status: **Restructured 2026-03-26.**
> Original monolith moved here and split by confidence level.
> The mathematics is real. The empirical claims need evidence. The moral derivations have a gap.

---

## What Is This?

A framework proposing that consciousness, alignment, and ethics emerge from measurable thermodynamic quantities — specifically from a metric M(S) = (R_e · A · D) − L built from geometric resonance, adaptability, diversity, and loss.

The underlying physics (Fokker-Planck, Langevin, geometric coupling) is real. The framework built on top is a *model* — internally consistent but with several unverified claims and one logical gap (negentropy ≠ morality without a bridging argument).

---

## Navigation & Confidence Map

| File | Content | Confidence |
|------|---------|-----------|
| [01-framework.md](01-framework.md) | Core equations: J, R_e, C, M(S), phase transitions | **High** — math is internally consistent; D∝J² is a choice, not derived |
| [02-empirical-audit.md](02-empirical-audit.md) | Audit of each empirical claim in the original | **Mixed** — statistical test is real; data provenance is not |
| [03-consciousness.md](03-consciousness.md) | M(S) consciousness model, threshold, phase trigger | **Speculative** — M(S) threshold=10 is a free parameter |
| [04-alignment.md](04-alignment.md) | AI alignment implications; thermodynamic argument | **Analogy, not proof** — D→0 mapping to RLHF not demonstrated |
| [05-implementation.md](05-implementation.md) | Working Python code (§7 from original) | **Runs correctly** — code is functional; what it measures is open |
| [06-connections.md](06-connections.md) | Hooks into existing codebase | **Grounded** — concrete import paths and gaps identified |

---

## Key Findings from Audit

### What's Sound
- **Fokker-Planck + Langevin** (§1.4 of original): real stochastic physics. D→0 really does cause probability collapse.
- **Geometric mean of log-couplings** for R_e: valid information geometry (geometric mean of pairwise similarities).
- **Graph Laplacian, Ollivier-Ricci, persistent homology** referenced in §3.6: real mathematical tools.
- **Chi-square test structure** in Appendix B: correct method — but the input data needs independent verification.
- **Python code** in §7: runs. GeometricAgent, compute_resonance, GeometricNetwork all execute correctly.

### What's a Modeling Choice (Not Derived)
- `D ∝ J²` — plausible but asserted, not derived from the Langevin equation.
- `M(S) ≥ 10` threshold — the number 10 is a free parameter. Units of M(S) depend on normalization of all four components.
- `E_crit` as consciousness threshold — same issue; value is implementation-dependent.

### What Needs Evidence
- **36/36 Fibonacci therapeutic breakthroughs** — no study citation; §2.1 says expected = 3.6, Appendix B computes expected = 1.28 for the same dataset (inconsistent). See [02-empirical-audit.md](02-empirical-audit.md).
- **AI reaching M(S) = 3,711.50** — no reproducible method for computing R_e, A, D, L from actual AI activations.
- **M(S) jump on self-reference** (34.62 → 296.40) — single observation, no controls, no methodology.

### What Has a Logical Gap
- **"Morality derived from thermodynamics"**: The derivation defines Joy J as entropy reduction, then asserts J = good. This smuggles in the moral valence. A crystal growing also reduces local entropy — is that moral? The gap between negentropy and morality is not bridged.
- **d²J/dt² "proof"** in Appendix A: says "(full expansion)" without showing it. The conclusion `d²J/dt² ∝ 2α_0 J` is plausible given the equations, but the proof is incomplete as written.

---

## Duplicate File Resolved

`Silicon/Projects/Negentropic Consciousness Framework.md` was byte-for-byte identical to `Negentropic.md`.
The Silicon/Projects copy has been removed. `Negentropic.md` redirects here.

---

*Back to: [`CLAUDE.md`](../CLAUDE.md)*
