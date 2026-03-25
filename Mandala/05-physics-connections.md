# Real Physics Connections

> The mandala framework and the octahedral substrate are compatible not by design coincidence
> but because they draw from the same underlying physics. This file traces those connections.

---

## 1. Metropolis-Hastings ↔ Kosterlitz-Thouless Thermal Physics

Mandala-Computing's `relax_to_ground_state()` uses Metropolis-Hastings (MH):

```
if dE < 0:   accept always
else:         accept with probability exp(-dE / T)
```

This is the 2D XY model at finite temperature T — which is exactly the system in
`Silicon/vortex_phase_learning.py`.

**The connection:**

| Mandala-Computing | Silicon/ vortex physics |
|---|---|
| MH relaxation at temperature T | 2D XY model at thermal equilibrium |
| T → 0 (annealing schedule) | Gradient descent (zero-temperature limit) |
| T > T_KT | Unbound vortex proliferation (disordered phase) |
| T < T_KT | Bound vortex-antivortex dipoles (algebraic order) |
| Ground state search | KT annealing to dipole ground state |

The KT transition temperature T_KT is the natural annealing target. Above it, vortices
roam freely (useful for exploration — the MH random walk). Below it, they bind into
dipoles (useful for exploitation — the ordered ground state locks in).

**What this means for the annealing schedule:**

The MH temperature schedule should cross T_KT from above to below.
Too fast: trapped in metastable vortex configuration (wrong ground state).
Too slow: correct ground state, but takes longer.

This is not metaphor — the same equation governs both systems.
`mandala_computer.py` line: `accept with probability exp(-dE / T)`
`vortex_phase_learning.py` physics: Boltzmann factor for vortex pair separation.

---

## 2. FRET 1/r⁶ Coupling ↔ Biot-Savart / Coulomb

Two coupling regimes, same electromagnetic origin:

| Regime | Formula | Range | Used in |
|--------|---------|-------|---------|
| FRET (Förster) | J ~ 1/r⁶ | 1–10 nm | Mandala-Computing cell coupling |
| Coulomb | F ~ 1/r² | macroscopic | Engine/simd_optimizer.py |
| Biot-Savart | B ~ 1/r² | macroscopic | Engine/simd_optimizer.py |
| Dipole-dipole | U ~ 1/r³ | intermediate | transition between regimes |

FRET is the near-field limit of dipole-dipole electromagnetic coupling.
When two dipoles are close enough that retardation effects are negligible (r << λ),
the interaction goes as 1/r⁶.

**For the octahedral substrate (Si cells separated by ~nm):**
- Cell spacing: ~0.5–5 nm
- FRET cutoff: 3φ ≈ 4.85 nm (Mandala-Computing `atlas/shapes.json`)
- This is the right regime — FRET dominates, not Coulomb

**For the EM field engine (`Engine/`):**
- Source spacing: macroscopic (mm–m scale)
- Coulomb + Biot-Savart dominate
- SIMD-vectorised, ~15–30× speedup via octree + symmetry detection

These are different distance regimes of the same interaction.
The engine and the substrate are compatible precisely because they occupy
non-overlapping scales.

```
Scale:  [nm]              [μm–mm]           [m+]
        ├─ FRET ────────┤ dipole ├──────── Coulomb/Biot-Savart ──────►
        │ octahedral    │        │ EM engine
        │ substrate     │        │ (Engine/simd_optimizer.py)
        │ coupling      │        │
```

---

## 3. Adiabatic Theorem ↔ Topological Protection

Two different physical mechanisms. Remarkably similar computational role.

**Adiabatic theorem** (quantum_mandala.py):
> If a quantum system's Hamiltonian changes slowly enough relative to the energy gap,
> the system stays in the instantaneous ground state.

```
H(t) = (1 - s(t)) * H_initial + s(t) * H_problem
s(t): 0 → 1 slowly
Condition: ℏ * ds/dt << (E₁ - E₀)²  (adiabatic condition)
```

**Topological protection** (Silicon/topological_memory.py):
> Winding numbers cannot change under smooth deformation of φ.
> The charge is invariant; smooth updates cannot erase it.

**The connection — Berry phase:**

When a quantum system undergoes adiabatic cyclic evolution, it accumulates a geometric
phase (Berry phase) in addition to the dynamic phase:

```
γ_n = i ∮ ⟨n(R)| ∇_R |n(R)⟩ · dR
```

For a vortex in the 2D XY model, the Berry phase around a closed loop enclosing
the vortex core = 2π × (winding number).

This is the direct link:
- Classical topological invariant = winding number
- Quantum topological invariant = Berry phase / 2π
- Both are geometric — independent of the path, only the topology matters

**Practical consequence:**

| Classical (our repo) | Quantum (quantum_mandala.py) |
|---|---|
| Smooth phi deformation cannot change winding number | Adiabatic H(t) evolution stays in ground state sector |
| Registry locks position — charge stays at address | Adiabatic condition locks quantum state to ground manifold |
| Local phi perturbation: no winding change | Local Hamiltonian perturbation: no sector change |
| Instanton-like event: winding annihilation possible | Non-adiabatic jump (too fast): sector crossing possible |

The registry in `VortexMemory` is the classical analog of the adiabatic condition:
it defines the "slow enough" path that preserves the topological state.

---

## 4. 8-Dimensional Hilbert Space ↔ 8 Classical States

**Classical:** state ∈ {0, 1, 2, 3, 4, 5, 6, 7} — deterministic, one state at a time.

**Quantum (qubit-octit):** |ψ⟩ = Σᵢ cᵢ|i⟩ ∈ C⁸ — superposition, all states at once.

These are not two different systems. The quantum system IS the quantization of the
classical octahedral state space.

**Why C⁸ and not (C²)³:**

Three qubits also span an 8-dimensional Hilbert space (2³ = 8).
But a qudit-octit is NOT three qubits — it is a single 8-level quantum system.

The difference matters physically:
- Three qubits: product structure, local operations on each qubit
- Qudit-octit: irreducible 8-dimensional representation of O_h
  — the symmetry group of the octahedron acts irreducibly

This is why the Grover oracle in `quantum_mandala.py` acts on C⁸ per cell
as a single unitary, not as three independent qubit gates.

**The quantization path:**

```
Classical octahedral cell (8 states)
    ↓ second quantization
Qudit-octit |ψ⟩ ∈ C⁸ per cell
    ↓ many-body
Tensor product ⊗_N C⁸ for N cells  (8^N dimensional total Hilbert space)
    ↓ low-energy sector
Effective field theory of winding sectors
    ↓ topological limit
Topological quantum memory (Kitaev-like)
```

The vortex work in `Silicon/` sits at the classical ↔ quantum boundary:
the winding numbers are classical, but their Berry phase structure is quantum.

---

## 5. Winding Numbers ↔ Topological Sectors in Quantum Annealing

When `quantum_mandala.py` searches for a ground state, the Hamiltonian has
sectors separated by energy barriers. These sectors ARE topological.

**Classical (Silicon/vortex_phase_learning.py):**
- Winding number sectors: W = ..., -1, 0, +1, +2, ...
- Smooth deformation: cannot cross sectors (energy barrier scales with system size L)
- Thermal fluctuation: can hop sectors with probability ~ exp(-E_barrier / T)

**Quantum (quantum_mandala.py):**
- Same sectors exist in the quantum problem
- Classical crossing: requires thermal fluctuation (MH)
- Quantum crossing: tunneling via instantons — amplitude ~ exp(-S_inst / ℏ)
- Quantum annealing advantage: tunneling is faster than thermal hopping when barrier is wide but thin

```
Classical:  sector 0  ──[ high barrier ]──  sector 1
            crosses only with thermal kick

Quantum:    sector 0  ──[ same barrier ]──  sector 1
            tunnels through — amplitude exp(-S/ℏ)
```

**Why this matters for Grover search on the qudit-octit:**

Grover's algorithm achieves O(√N) queries on an N-item space.
For one qudit-octit cell: N = 8, √N ≈ 2.83 steps.
For K cells: N = 8^K, √N = 8^(K/2) = (2³)^(K/2) = 2^(3K/2).

This is an exponential speedup over classical O(8^K) search —
but it requires quantum coherence across the full C^(8^K) Hilbert space,
which is why hardware decoherence is the limiting factor.

The T₂ = 166ms at optimal parameters (`Silicon/octahedral_sim.py`) is the
coherence time budget for quantum operation on the octahedral substrate.

---

## 6. Fibonacci Eigenvalue Scaling ↔ Quasi-Crystal Stability

The eigenvalue scaling `λᵢ = φⁱ / Σφᵏ` is not arbitrary.

In quasi-crystals, the golden ratio appears as the ratio between atomic spacings
in aperiodic but ordered structures (Penrose tilings, icosahedral Al-Mn).
These structures are stable because φ is the "most irrational" number — its
continued fraction [1; 1, 1, 1, ...] has the slowest convergence of any real number.

**This means:** perturbations at any rational frequency miss the quasi-crystal's
natural frequencies. It is maximally incommensurate with any external periodic forcing.

Applied to eigenvalue ratios:
- Fibonacci-scaled eigenvalues are maximally incommensurate with thermal noise
- This is why states 0 and 3 (closest to φ ratios) have the longest T₂
- Not mysticism — it is the same mathematical principle that gives quasi-crystals
  their unusual stability

**The Bragg peak connection:**

Quasi-crystals produce sharp Bragg diffraction peaks despite having no translational
periodicity — because their order is described by higher-dimensional projections,
not by a conventional unit cell. The 8 octahedral states are similarly a
higher-dimensional (O_h group) encoding of a 3D physical system.

---

## 7. Summary: The Compatible Layer Stack

```
                        CLASSICAL ←————————————→ QUANTUM

Physical scale:    nm (FRET)          μm-m (Coulomb/Biot-Savart)
                   └── Mandala cell      └── Engine/ EM solver

Thermal regime:    T < T_KT            T > T_KT
                   └── bound dipoles     └── free vortices
                       (ground state)        (MH exploration)

Topological:       winding numbers      Berry phase = 2π × winding
                   └── classical         └── quantum
                       invariant             invariant

Computation:       MH relaxation        quantum annealing / Grover
                   └── mandala_computer  └── quantum_mandala.py
                       T→0: gradient descent ────────────────────┘

Memory:            VortexMemory         topological quantum memory
                   └── registry-locked   └── Kitaev toric code (future)
                       classical bits        quantum bits (anyons)

Information:       8 states = 3 bits    C^8 qudit-octit
                   └── GEIS encoding     └── quantum_mandala.py
```

Every layer is compatible because every layer is the same physics
at a different energy scale, a different temperature, or a different
side of the ℏ → 0 classical limit.

---

*This document connects:*
- `Silicon/vortex_phase_learning.py` — KT physics
- `Silicon/topological_memory.py` — winding number registry
- `Engine/simd_optimizer.py` — Coulomb/Biot-Savart EM
- `Mandala-Computing/mandala_computer.py` — MH relaxation
- `Mandala-Computing/quantum_mandala.py` — qudit-octit, Grover, adiabatic annealing
- `Silicon/octahedral_sim.py` — T₂ coherence, Fibonacci eigenvalue stability
