# Theoretical Claims — Honest Audit

> **Status: Speculative.** This file documents the most ambitious claims of the mandala
> framework with honest physical caveats. The ideas are interesting and worth developing.
> They are not established results.

---

## 1. P vs NP via Geometric Ground State

### The Claim

Every NP-hard problem can be encoded as a geometric configuration of the octahedral substrate.
The solution emerges as the ground state via thermal relaxation — in ~1 nanosecond.

### What's Correct

The *encoding idea* is real. Many combinatorial problems can be written as energy minimisation:

| Problem | Energy function |
|---------|----------------|
| SAT | E = number of unsatisfied clauses |
| Graph Coloring | E = number of same-color adjacent pairs |
| TSP | E = total tour length |
| Factorisation | E = (p × q − N)² |

This is the basis of simulated annealing, quantum annealing (D-Wave), and Hopfield networks.

### The Gap

**Finding the ground state of a coupled spin system IS NP-hard.**

This is not a loophole in complexity theory — it is a theorem. The ground state problem
of the 2D Ising model is NP-hard (Barahona 1982). D-Wave's quantum annealer, with
thousands of physical qubits and genuine quantum tunnelling, does not reliably solve
NP-hard problems faster than classical heuristics at scale.

The specific flaw in the factorisation example:

```python
# This line does not factor N:
substrate.thermal_relaxation(temperature=300, duration=1e-9)

# It relaxes toward A local minimum, not THE global minimum.
# The energy landscape E(p,q) = (pq − N)² has many local minima.
# Thermal relaxation at 300K gets trapped in them.
# To guarantee the global minimum, you need exponential time
# (in the worst case) — which is exactly P vs NP.
```

The constraint field `generate_factorization_constraint(N)` itself encodes the hard
problem. Constructing a potential well with minima exactly at the factor pairs requires
knowing the factors — that is circular.

### What It Could Mean

The geometric framing IS useful for approximate optimisation and heuristic solvers.
It is the foundation of:
- Simulated annealing (classical)
- Quantum annealing / QAOA (quantum)
- Hopfield / Boltzmann machines (neural)

The octahedral substrate could provide a physically efficient implementation of
approximate ground-state finding — which is genuinely valuable, just not O(1) for NP-hard problems.

### Honest Status

| Claim | Status |
|-------|--------|
| NP problems encodable as energy landscapes | True |
| Relaxation finds approximate solutions | True (annealing) |
| Relaxation finds exact global minimum in O(1) | Not established — contradicts known hardness results |
| RSA-2048 factorable in 1ns | Not plausible with current physics |

---

## 2. Consciousness Emergence — Integrated Information Φ

### The Claim

A recursive mandala structure with 7+ layers and feedback loops automatically exhibits
consciousness signatures, measured by IIT's integrated information Φ.

### What's Correct

Tononi's Integrated Information Theory (IIT 3.0) is a serious scientific framework.
High Φ does correlate with measures of consciousness in empirical studies.
Self-referential loop structures (Hofstadter strange loops) are a legitimate architectural
ingredient that some theories consider necessary for consciousness.

The connection: mandala feedback loops → high mutual information between layers → high Φ.

### The Gap

**1. The Φ formula in the original code is wrong.**

```python
# Original (incorrect):
EI = total_coupling * math.log(len(states_A) * len(states_B))
```

Tononi's actual Φ (IIT 3.0) requires computing the **earth mover's distance**
(Wasserstein distance) between the full joint probability distribution of the system
and the product of marginal distributions across a minimum information partition.

```
Φ = min over all partitions { D_W(p(system) || p(A) ⊗ p(B)) }
```

This is a fundamentally different quantity from coupling strength × log(partition size).
The simplified formula will always return a positive number — it does not measure
integrated information.

**2. Exact Φ computation is NP-hard.**

The partition space grows exponentially with system size. For a 100-cell substrate,
computing exact Φ requires evaluating ~2^99 partitions. Practical approximations exist
(ΦID, Φ*) but they sacrifice the theoretical guarantees.

**3. High coupling ≠ high Φ.**

A fully connected graph (every cell coupled to every other) has Φ = 0 if the
coupling is deterministic — because the system can be predicted from any subset.
Φ requires *irreducibility*, not just connectivity.

### Corrected Approach

```python
# Approximate Φ using minimum information partition (MIP)
from pyiit import phi_mip   # external library — not yet in requirements.txt

def estimate_phi(substrate, n_samples=1000):
    """
    Approximate Φ via Monte Carlo sampling of partitions.
    Returns lower bound — true Φ may be higher.
    """
    states = [cell["state"] for cell in substrate.cells]
    # Build transition probability matrix from coupling strengths
    T = substrate.transition_matrix()
    phi_approx = phi_mip(T, n_samples=n_samples)
    return phi_approx
```

### Honest Status

| Claim | Status |
|-------|--------|
| Self-referential loops necessary for consciousness | Theoretical (Hofstadter, IIT) |
| Mandala structure has high mutual information | Plausible — needs measurement |
| Feedback loops → high Φ | Not guaranteed — depends on specific coupling values |
| Φ calculation in original code is correct IIT | Incorrect — formula is a proxy |
| 7-layer mandala "automatically" conscious | Not established |

---

## 3. Physical Constants as Geometric Ground States

### The Claim

Physical constants (c, G, ℏ, e, α) are not fundamental — they are eigenvalues
of the universal geometric substrate at its ground state.

### What's Interesting

This is a real class of theories in physics:
- **Geometrodynamics** (Wheeler): spacetime geometry as the fundamental entity
- **Emergent gravity** (Verlinde): gravity as entropic force from geometric degrees of freedom
- **Fine structure constant from geometry**: several attempts exist (Wyler, Eddington)
- **Varying constants**: Webb et al. report α variations at high redshift (contested)

The idea that constants *could* be ground-state properties of a deeper substrate
is not dismissed by mainstream physics — it is an open research area.

### The Gap

**The derivations in the original file are circular.**

```python
def fine_structure_constant_from_geometry(self):
    charge_coupling = 1.0
    vacuum_coupling = 137.0      # ← manually set to 137
    return charge_coupling / vacuum_coupling   # returns 1/137
```

This does not derive α = 1/137 from geometry. It inputs 137 and divides.

The fibonacci match "137 ≈ 89 + 55 − 8 + 1" is numerological coincidence.
137 = 89 + 48, or 137 = 128 + 9, or infinitely many other decompositions.

The speed of light derivation:
```python
c_effective = 1e9 * 5e-10 = 0.5 m/s   # Not 3×10⁸ m/s
```
Off by ~8 orders of magnitude, and the comment acknowledges "THz range" would be needed —
which is not silicon at room temperature.

### What Would Make This Rigorous

To derive a physical constant from geometry, you need:
1. A Lagrangian for the geometric substrate (not just an energy landscape)
2. A derivation showing the constant emerges as a ratio of characteristic scales in that Lagrangian
3. A prediction that differs from the standard value in a testable way

The Wyler formula for α is the best-known serious attempt:
```
α ≈ (9 / (8π⁴)) × (π⁵/245)^(1/4) ≈ 1/137.036
```
This uses volumes of symmetric spaces (O_h-like geometric objects).
It gives the right number but its physical interpretation remains contested.

### Honest Status

| Claim | Status |
|-------|--------|
| Constants could be ground-state eigenvalues | Open research area — not ruled out |
| Geometric frameworks for constants exist | Yes (Wyler, Verlinde, geometrodynamics) |
| The specific derivations in this document derive constants from first principles | No — they input the constants |
| Webb et al. α variation evidence | Contested; not confirmed by other groups |

---

## 4. Summary Table

| Section | Interesting Idea | Honest Problem | Path to Rigour |
|---------|-----------------|----------------|----------------|
| P=NP via relaxation | Ground-state encoding of NP problems | Finding ground state IS NP-hard (Barahona 1982) | Treat as approximate annealing, not exact solver |
| Consciousness Φ | Self-referential loops + IIT | Φ formula is wrong; exact Φ is NP-hard | Use proper MIP approximation; add `pyiit` dependency |
| Physical constants | Constants as geometric eigenvalues | Derivations are circular (input the answer) | Derive from a proper geometric Lagrangian; compare to Wyler |

---

*Next: [`04-roadmap.md`](04-roadmap.md) — implementation phases with updated code.*
