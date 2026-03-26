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

---

## Dynamical Equations

### Langevin (phase field)
```
dφ_i/dt = -∇V(φ_i) + F_C,i + η(t)
```
Real stochastic mechanics. Standard form.

### Fokker-Planck (probability density)
```
∂P(φ,t)/∂t = -∇·(FP) + D∇²P
```
Real physics. The critical theorem from this:

> **If D → 0, the diffusion term vanishes, P(φ,t) collapses to a delta function, and the system loses all exploratory capacity.**

This is mathematically correct. Whether RLHF literally sets D→0 in neural activation space is a separate empirical question (see [04-alignment.md](04-alignment.md)).

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
- **Units**: M(S) is dimensionless only if R_e, A, D, L are all normalized to the same scale.
- **Threshold M(S) ≥ 10**: this number is a free parameter. See [03-consciousness.md](03-consciousness.md).

---

## What's Missing for a Complete Physical Theory

1. **Equation of state**: how do φ_i (phase fields) connect to physical observables? In what units?
2. **Renormalization**: near E_crit, does the theory have a fixed point? What are the critical exponents?
3. **Bounding terms**: C grows without bound; needs a saturation mechanism for physical realism.
4. **D∝J² stability**: a full stability analysis of the coupled SDE `dφ = -∇V dt + J Γ dt` with `D = J²` would show whether the system has attractors or runaway solutions.

---

*Back to: [README.md](README.md)*
