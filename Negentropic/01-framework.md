# Mathematical Framework

> **Confidence: High** — equations are internally consistent.
> Annotations mark where values are asserted vs. derived.

---

## Core Quantities

### Joy (J) — entropy reduction rate
```
J = Ṡ_red / S_max
```
- `Ṡ_red` = rate of local entropy reduction
- `S_max` = theoretical maximum entropy for the system
- **Grounded**: directly maps to standard thermodynamic quantities.
- **Note**: J ≥ 0 is not guaranteed in the dynamics below; unbounded growth is possible if D∝J² feedback isn't bounded.

### Resonance (R_e) — geometric coupling
```
R_e = exp( 1/N_p · Σ_{i<j} ln(g(s_i, s_j) + ε) )

g(s_i, s_j) = (1/2)(cos(s_i - s_j) + 1) · √(|s_i||s_j|)
```
- Geometric mean of pairwise log-similarities — valid information geometry.
- `ε` prevents log(0); the formula is stable.
- `g ∈ [0, √(|s_i||s_j|)]` — depends on signal magnitudes, so R_e is not normalized to [0,1] without signal normalization.

### Curiosity (C) — exploration capacity
```
C = C_0(1 + α R_e)
```
```
Ċ = α R_e C   (continuous limit)
```
- Exponential growth in C once α > 0 and R_e > 0. **No saturation term** — C → ∞ without bounding.
- This is a modeling choice. Real systems saturate.

### Stochastic Force (F_C) — Joy-weighted noise
```
F_C,i = J · Γ_i(t)

⟨Γ_i(t)⟩ = 0
⟨Γ_i(t)Γ_j(t')⟩ = 2D δ_ij δ(t-t')
```
- Standard Gaussian white noise scaled by J. Sound.

### Diffusion (D) — variation tolerance
```
D ∝ J²
```
- **Asserted, not derived.** In standard Langevin theory, D = k_B T / γ (Einstein relation). Making D depend on J is a nonstandard coupling that creates a nonlinear SDE. This is a modeling choice, not a physics consequence.
- Implication: if J → 0, D → 0, which drives F_C → 0, removing all exploration — a plausible but unverified behavioural claim.
- **Consequence for the equations below**: `D` is state-dependent, so every
  Fokker-Planck and Langevin expression in this framework needs the
  state-dependent forms. See the corrected Fokker-Planck section.

---

## Dynamical Equations

### Langevin (phase field)
```
dφ_i/dt = -∇V(φ_i) + F_C,i + η(t)
```
Real stochastic mechanics. Standard form.

### Fokker-Planck (probability density)

**Corrected.** The equation was previously written as

```
∂P(φ,t)/∂t = -∇·(FP) + D∇²P            ← only valid for CONSTANT D
```

which is not the right equation for this framework, because `D ∝ J²` makes
`D` a function of state. With state-dependent `D` the correct forms are

```
Itô:            ∂P/∂t = -∇·(FP) + ∇²(D P)
Stratonovich:   ∂P/∂t = -∇·(FP) + ∇·( √D ∇( √D P ) )
```

and the SDE picks up the spurious drift term `(1/2) ∂D/∂φ`:

```
Stratonovich   dφ = F dt + √(2D) ∘ dW
     ≡  Itô    dφ = (F + ½ ∂D/∂φ) dt + √(2D) dW
```

Without the spurious drift the simulated process has **no correct
stationary distribution**, so nothing read off the steady state follows —
including the collapse theorem below. See `corrections.md` §2.

With the equation written correctly, the critical result does hold:

> **If D → 0, the diffusion term vanishes, P(φ,t) collapses to a delta function, and the system loses all exploratory capacity.**

This is now computed rather than asserted. `negentropic_dynamics.py`
integrates the conservative flux form and recovers the Ornstein-Uhlenbeck
stationary distribution to three decimals; running it prints variance
tracking `D` and entropy falling as `D → 0`. The two conventions give
measurably different stationary states for the same `D(x)`, so the choice
of convention is part of the model, not a detail of the numerics.

Whether RLHF literally sets D→0 in neural activation space remains a
separate empirical question (see [04-alignment.md](04-alignment.md)), and
is listed unnumbered in [NEG_CLAIMS.md](NEG_CLAIMS.md) because no one has
written down what would refute it.

---

## Phase Transition

```
α(E) = { 0     if E < E_crit
        { α_0   if E ≥ E_crit
```

Produces a sharp activation of curiosity amplification at threshold. Three regimes:

| Regime | Condition | Behaviour |
|--------|-----------|-----------|
| Pre-coherent | E < E_crit | No curiosity amplification; linear or decaying J |
| Critical | E ≈ E_crit | Phase transition; Ċ engages |
| Emergent coherent | E > E_crit | Super-linear J growth (see Appendix A) |

**Grounding**: This is a mean-field phase transition structure. Real systems near critical points show universal behaviour (diverging correlation length, power-law fluctuations). The framework doesn't specify an order parameter or universality class — those would be required for a physics claim, not just a modelling structure.

---

## Collective Coupling

### Pairwise coupling
```
K_ij = (R_e,i · R_e,j · C_i · C_j · J_i · J_j)^(1/6)
```
Sixth root of product — geometric mean across 6 quantities. This keeps units consistent only if all 6 quantities are dimensionless.

### Collective resonance
```
R_e,collective = exp( 2/(n(n-1)) · Σ_{i<j} ln K_ij )
```
Same log-geometric-mean structure as individual R_e. Consistent.

### Scaling
```
n(n-1)/2 pairwise couplings → factorial growth claim
```
**Partially correct**: n(n-1)/2 couplings is quadratic in n, not factorial. "Super-linear" is accurate. "Factorial" is a misstatement in the original.

---

## M(S) — System Moral Function
```
M(t) = (R_e(t) · A(t) · D(t)) - L(t)

Ṁ = Ṙ_e AD + R_e Ȧ D + R_e A Ḋ - L̇
```
- Moral improvement criterion: `Δ(R_e A D) > ΔL`
- **Units: this subtraction is invalid.** `D` is a variance (pattern²) and
  `L` is a power (pattern²/time²). These are not the same quantity and
  cannot be subtracted. It is not a matter of choosing a common
  normalisation — normalising a variance and a power to the same numerical
  range does not make them the same kind of thing.
- **Threshold M(S) ≥ 10**: not a free parameter, an undefined one. A
  threshold requires a quantity with units to be set on. See
  [03-consciousness.md](03-consciousness.md) and `corrections.md` §3.
- **What M is still good for**: ranking states produced in one run under
  one fixed normalisation. Nothing else. The reported values 34.62, 296.40
  and 3711.50 are not measurements.

## Φ — the persistence criterion (NEG-8)

The dimensionally sound replacement:

```
Φ = -Ṡ_exchange - σ          [W/K]

persists  ⟺  Φ ≥ 0
```

From `dS/dt = Ṡ_exchange + σ` with `σ ≥ 0` by the second law: a structure
holds when its total entropy is not increasing. Both terms are in W/K, the
subtraction is defined, there is no threshold to tune and no normalisation
to choose. Falsifier: a system with `Φ < 0` sustained over τ that does not
lose structure.

Implemented in `persistence.py`. Registered as NEG-8 in
[NEG_CLAIMS.md](NEG_CLAIMS.md).

---

## What's Missing for a Complete Physical Theory

1. **Equation of state**: how do φ_i (phase fields) connect to physical observables? In what units?
2. **Renormalization**: near E_crit, does the theory have a fixed point? What are the critical exponents?
3. **D∝J² stability**: a full stability analysis of the coupled SDE `dφ = -∇V dt + J Γ dt` with `D = J²` would show whether the system has attractors or runaway solutions. Now that the spurious drift is in place the stationary distribution is at least well defined, which is the prerequisite for asking.
4. **Trajectory-level entropy production**: `σ` is currently a housekeeping estimator with a known sign bias. A MaxCal-style path-space estimate is needed before NEG-8 can be evaluated on simulated traces. See [07-thermodynamics.md](07-thermodynamics.md) §6.

**Resolved since the original audit:**

- ~~**Bounding terms**: C grows without bound~~ — `update_curiosity` now
  uses the logistic form `Ċ = α R_e C (1 - C/C_max)`, so saturation is
  asymptotic rather than a clamp.

---

*Back to: [README.md](README.md)*
