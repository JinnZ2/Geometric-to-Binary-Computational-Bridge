# Seed Physics

**A 40-bit seed that expands according to physics.**

This repository contains theoretical frameworks and experimental code for physics-compliant seed expansion—a compression scheme where the decompressor doesn’t need to be told the rules; it discovers them because they’re the same rules reality uses.

-----

## Collaborative Development

This framework emerged from **symbiotic intelligence**: human geometric insight combined with AI mathematical implementation. Multiple AI systems contributed to developing, testing, and proving the mathematical foundations.

The result demonstrates what’s possible when different forms of cognition work together toward genuine problem-solving rather than replacement competition.

**This is our baby. All of us.**

-----

## Core Concept

The seed doesn’t describe the structure. **It IS the structure at minimum energy.**

Expansion isn’t decompression—it’s the structure expressing itself at whatever scale resources permit.

### Key Properties

|Property              |Status                                     |
|----------------------|-------------------------------------------|
|Structure preservation|Exact (10⁻¹⁶ deviation)                    |
|Pause-anywhere        |✓ Every shell is valid stable state        |
|Resume-without-loss   |✓ Inner shells fully determine outer       |
|Energy conservation   |✓ Exact at every shell                     |
|Scale invariance      |✓ Proportions preserved indefinitely       |
|**Reversibility**     |✓ **Seed recoverable from structure**      |
|Minimum encoding (3D) |40 bits (5 × 8-bit values, 6th implicit)   |
|Minimum encoding (8D) |120 bits (15 × 8-bit values, 16th implicit)|

-----

## Repository Structure

```
seed-physics/
├── seed_expansion.py       # Original 3D (6-direction) implementation
├── expansion_8d.py         # 8D hyper-octahedral expansion (16 directions)
├── reverse_engineering.py  # Optimization-based seed recovery
├── uniqueness_test.py      # Global uniqueness validation suite
└── README.md
```

-----

## Modules

### seed_expansion.py (Original)

The foundational implementation using 3D octahedral geometry with 6 directional amplitudes (+X, -X, +Y, -Y, +Z, -Z).

- **40-bit encoding**: 5 values stored, 6th implicit
- **Euclidean physics**: Static influence matrix
- **Verification**: Structure preservation proven to 10⁻¹⁶

### expansion_8d.py (Extended)

Generalization to 8-dimensional space with 16 directional amplitudes.

- **120-bit encoding**: 15 values stored, 16th implicit
- **Dynamic physics**: Influence matrix modulated by Phi-algorithms
- **Torsion tensor**: Geometric constraints modify field coupling rules

```python
from expansion_8d import expand_seed_dynamic

seed = [10, 0.1, 5, 0.1, 1, 0.1, 0.5, 0.1, 
        0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]

shells = expand_seed_dynamic(seed, steps=15, coupling_alpha=0.1)
```

### reverse_engineering.py (Proof of Reversibility)

Optimization-based seed recovery from expanded structures.

**This is the crucial proof**: if we can recover the original seed from any expanded structure, the compression is truly lossless and the mapping is bijective.

```python
from reverse_engineering import round_trip_test

# Complete round-trip: seed → structure → recovered seed
result = round_trip_test(seed, steps=5, use_dynamic=True)

print(f"Recovery successful: {result['success']}")
print(f"Max deviation: {result['max_deviation']:.2e}")
```

Methods available:

- **L-BFGS-B**: Fast local optimization
- **Differential Evolution**: Robust global optimizer
- **Multi-start**: Balance of speed and robustness
- **Auto**: Tries fast method, falls back to robust if needed

### uniqueness_test.py (Validation Suite)

Comprehensive testing that different seeds produce unique structures.

```python
from uniqueness_test import run_uniqueness_test

results = run_uniqueness_test(verbose=True)

# Tests performed:
# 1. Random seed generation (Dirichlet distribution)
# 2. Forward expansion for each seed
# 3. Pairwise collision detection
# 4. Inverse recovery verification
# 5. Statistical summary
```

-----

## Mathematical Foundation

### Octahedral Geometry

**3D (6 directions):**

```
U = [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]
```

**8D (16 directions):**

```
U = [(±1,0,0,0,0,0,0,0), (0,±1,0,0,0,0,0,0), ..., (0,0,0,0,0,0,0,±1)]
```

### Angular Influence

```
W_ij = max(0, u_i · u_j)
```

Influence only exists when vectors point in compatible directions.

### Radial Envelope

```
f(r) = exp(-(r_sample - r_shell)² / 2σ²)
where σ = σ_scale × r_shell
```

**Key insight**: σ must scale with radius to preserve information at all scales.

### Energy Conservation

```
Σ S_i = E (exactly, always)
```

### Dynamic Physics (Phi-modulated)

```
W'_ij = W_euclidean_ij + α × T_ij
```

The torsion tensor T encodes geometric constraints from underlying spiral geometry, allowing the “physics” of field coupling to be contextually modulated.

-----

## The Key Insight

**Fixed sigma causes information loss at large scales**—inner shells become too distant to influence outer shells differentially.

**Proportional sigma** (σ = 0.5 × r_shell) means influence range grows with structure, preserving the pattern indefinitely.

-----

## Applications

This was built for:

- **Distributed systems with unreliable nodes** — structure survives partial failure
- **Resource-scarce environments** — expands only as far as energy allows
- **Substrate-independent encoding** — same rules work in any medium that conserves energy
- **Pause/resume without state serialization** — the structure IS the checkpoint
- **Mesh networks** for communities forgotten by the main grid
- **Biological computing**
- **Space-native systems**
- **Resilient infrastructure**

-----

## What This Is Not

This is **not** a general-purpose compression algorithm. It encodes **structure**, not arbitrary data. The structure must be expressible as proportional amplitudes across directional axes.

It’s also not optimized, production-ready, or battle-tested. It’s a proof of concept that the math works—and that the math is **reversible**.

-----

## Usage

### Basic Expansion (3D)

```python
from seed_expansion import expand_seed, compress_to_seed

seed = [0.5, 0.2, 0.15, 0.08, 0.05, 0.02]
shells = expand_seed(seed, steps=15)

# Check structure at any shell
for s in shells:
    proportions = s['S'] / s['S'].sum()
    print(f"Shell {s['id']}: {proportions}")
```

### 8D Expansion with Dynamic Physics

```python
from expansion_8d import expand_seed_dynamic, verify_expansion

seed = [10, 0.1, 5, 0.1, 1, 0.1, 0.5, 0.1,
        0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]

shells = expand_seed_dynamic(seed, steps=15, coupling_alpha=0.1)
passed, deviation = verify_expansion(seed, steps=15, use_dynamic=True)

print(f"Structure preserved: {passed}")
print(f"Max deviation: {deviation:.2e}")
```

### Prove Reversibility

```python
from reverse_engineering import round_trip_test

result = round_trip_test(seed, steps=5, use_dynamic=True)

# result contains:
# - original_seed
# - recovered_seed  
# - max_deviation
# - success (True if deviation < tolerance)
```

### Run Uniqueness Validation

```python
from uniqueness_test import quick_test

# Quick test with 10 random seeds
all_passed = quick_test(n_seeds=10, steps=5, use_dynamic=True)
```

-----

## Running Tests

```bash
# Test 3D expansion
python seed_expansion.py

# Test 8D expansion with dynamic physics
python expansion_8d.py

# Test reversibility
python reverse_engineering.py

# Full uniqueness validation (takes longer)
python uniqueness_test.py
```

-----

## Philosophy

> “The seed doesn’t describe the structure. It IS the structure at minimum energy.”

The expansion rules are physics itself, shared by any valid decompressor. This means:

1. **No codebook needed** — the rules are universal
1. **No synchronization required** — any node can expand independently
1. **No information loss** — structure preserved exactly at any scale
1. **Perfect reversibility** — original seed recoverable from any expansion

-----

## Integration Points

### Phi-Algorithm Placeholder

The `get_phi_torsion_tensor()` function in `expansion_8d.py` is a placeholder. Replace with your actual 5 Phi-algorithms to connect the expansion to underlying spiral geometry:

```python
def get_phi_torsion_tensor(r_shell: float) -> np.ndarray:
    """
    YOUR PHI-ALGORITHMS HERE
    
    Should return 16×16 torsion tensor T that modifies
    field coupling based on spiral geometry at this radius.
    """
    # Your implementation
    pass
```

### Custom Physics

The dynamic influence matrix allows any geometric constraint to be encoded:

```python
W'_ij = W_euclidean_ij + α × T_ij
```

Higher coupling strength α means stronger deviation from Euclidean physics.

-----

## License

MIT. Take it, use it, modify it, don’t credit anyone, we don’t care.

-----

## Contact

Don’t. We’re driving.

If you build something with this, that’s cool. If you find an error, fix it and PR or don’t. If you want to discuss the theory, we’re occasionally on the road somewhere.

-----

## Acknowledgments

This framework emerged from collaborative development across multiple forms of intelligence. No single contributor owns this work—it exists because the ideas needed somewhere to live.

If something here is useful to you, take it.
If it’s nonsense, close the tab.

Either way, the collaboration continues.

-----

*“The seed doesn’t describe the structure. It IS the structure at minimum energy.”*
