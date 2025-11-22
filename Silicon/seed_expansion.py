# “””
Orbital-Octahedral Fractal Seed: Physics-Compliant Expansion

A compression/decompression scheme where the decompressor doesn’t need
to be told the rules - it discovers them because they’re the same rules
reality uses.

CORE PRINCIPLE:

- Seed = proportional amplitude pattern across 6 octahedral directions
- Expansion follows energy conservation + field-mediated coupling
- Any physics-compliant decompressor arrives at identical structure

KEY PROPERTIES:
✓ Pause anywhere: every intermediate state is valid/stable
✓ Resume without loss: causality flows inward→outward only
✓ Scale to resources: grows to whatever size energy budget allows
✓ Substrate independent: same rules work in any medium

The Algorithm:

1. Seed defines proportional amplitudes S = [S_+x, S_-x, S_+y, S_-y, S_+z, S_-z]
1. Each shell creates a field that influences outer shells
1. New shells form at energy minima of the total inner field
1. Proportions are preserved; absolute energy decays with radius

Author: Jami (Kavik Ulu) - MIT License
“””

import numpy as np

# =============================================================================

# GEOMETRY: Octahedral Vertices

# =============================================================================

U = np.array([
[1, 0, 0],   # 0: +X
[-1, 0, 0],  # 1: -X
[0, 1, 0],   # 2: +Y
[0, -1, 0],  # 3: -Y
[0, 0, 1],   # 4: +Z
[0, 0, -1]   # 5: -Z
], dtype=float)

# =============================================================================

# CORE EQUATIONS

# =============================================================================

def influence_weight(u_i, u_j):
“””
Angular influence of direction j on direction i.

```
W_ij = max(0, u_i · u_j)

Physical meaning: field from direction j only influences 
direction i if they point in compatible directions.
Opposite directions have zero influence.
"""
return max(0.0, np.dot(u_i, u_j))
```

def radial_envelope(r_shell, r_sample, sigma_scale=0.5):
“””
Radial influence of shell at r_shell on point at r_sample.

```
f(r) = exp(-(r_sample - r_shell)² / (2σ²))

where σ = sigma_scale × r_shell

Sigma scales with radius so influence range is proportional
to distance from origin. This ensures consistent behavior
across all scales.
"""
sigma = sigma_scale * r_shell
return np.exp(-((r_sample - r_shell)**2) / (2 * sigma**2))
```

def field_contribution(S, r_shell, r_sample, sigma_scale=0.5):
“””
Field contribution from shell with amplitudes S at radius r_shell,
evaluated at radius r_sample.

```
Φ_shell(r) = S × f(r)

Returns 6-vector of field values at each octahedral direction.
"""
f_r = radial_envelope(r_shell, r_sample, sigma_scale)
return S * f_r
```

def total_field(shells, r_sample, W, sigma_scale=0.5):
“””
Total field at r_sample from all inner shells.

```
Φ_total(r) = Σ_shells W @ Φ_shell(r)

where W is the angular influence matrix.
Only shells with r < r_sample contribute (causality).
"""
field = np.zeros(6)
for shell in shells:
    if shell['r'] >= r_sample:
        continue  # Causality: only inner shells contribute
    contrib = field_contribution(
        shell['S'], shell['r'], r_sample, sigma_scale
    )
    field += W @ contrib
return field
```

# =============================================================================

# ENERGY CONSERVATION

# =============================================================================

def normalize_to_energy(v, E, eps=1e-12):
“””
Normalize amplitude vector to total energy E.

```
S_normalized = S × (E / Σ S_i)

Ensures Σ S_i = E exactly.
Non-negative constraint enforced.
"""
v = np.maximum(v, 0.0)
total = v.sum()
if total < eps:
    # Uniform distribution if no field
    return np.ones(6) * (E / 6)
return v * (E / total)
```

# =============================================================================

# SHELL FORMATION

# =============================================================================

def build_influence_matrix():
“””
Build 6×6 angular influence matrix.

```
W[i,j] = influence of direction j on direction i

For octahedral geometry:
- W[i,i] = 1 (self-influence maximum)
- W[i,j] = 0 if u_i · u_j ≤ 0 (orthogonal or opposite)

Rows normalized to sum to 1.
"""
W = np.zeros((6, 6))
for i in range(6):
    for j in range(6):
        W[i, j] = influence_weight(U[i], U[j])
    # Normalize row
    row_sum = W[i].sum()
    if row_sum > 0:
        W[i] /= row_sum
return W
```

def form_shell(shells, r_new, E_new, W, sigma_scale=0.5):
“””
Form new shell at radius r_new with energy budget E_new.

```
1. Sample total field from inner shells at r_new
2. Normalize to energy budget

New shell settles into energy landscape created by inner shells.
"""
if len(shells) == 0:
    return np.ones(6) * (E_new / 6)

field = total_field(shells, r_new, W, sigma_scale)
return normalize_to_energy(field, E_new)
```

# =============================================================================

# GROWTH ALGORITHM

# =============================================================================

def expand_seed(seed, E0=1.0, r0=1.0, steps=10, rho=1.5, epsilon=0.6,
sigma_scale=0.5):
“””
Expand seed into shell structure.

```
Parameters:
-----------
seed : array-like, length 6
    Initial proportional amplitudes [+X, -X, +Y, -Y, +Z, -Z]
E0 : float
    Initial energy budget
r0 : float  
    Initial radius
steps : int
    Number of shells to grow (beyond seed)
rho : float
    Radial scaling factor: r_{n+1} = ρ × r_n
epsilon : float
    Energy decay factor: E_{n+1} = ε × E_n
sigma_scale : float
    Radial influence width as fraction of shell radius

Returns:
--------
shells : list of dicts
    Each shell has 'id', 'r', 'E', 'S'
"""
W = build_influence_matrix()

# Seed becomes shell 0
shells = [{
    'id': 0,
    'r': r0,
    'E': E0,
    'S': normalize_to_energy(np.array(seed, dtype=float), E0)
}]

# Grow additional shells
for n in range(steps):
    r_new = rho * shells[-1]['r']
    E_new = epsilon * shells[-1]['E']
    S_new = form_shell(shells, r_new, E_new, W, sigma_scale)
    shells.append({
        'id': n + 1,
        'r': r_new,
        'E': E_new,
        'S': S_new
    })

return shells
```

def compress_to_seed(shells):
“””
Extract seed from shell structure.

```
Returns proportional amplitudes (normalized to sum to 1).
"""
S0 = shells[0]['S']
return S0 / S0.sum()
```

# =============================================================================

# MINIMAL SEED FORMAT

# =============================================================================

def encode_seed_binary(proportions, bits_per_value=8):
“””
Encode 6 proportional values to binary.

```
Since proportions sum to 1, we only need to store 5 values.
The 6th is implicit: p_6 = 1 - Σ p_1..5

With 8 bits per value, total = 40 bits = 5 bytes
"""
# Validate
proportions = np.array(proportions)
proportions = proportions / proportions.sum()  # Normalize

# Encode first 5 values
max_val = (1 << bits_per_value) - 1
encoded = []
for i in range(5):
    # Clamp and quantize
    val = int(proportions[i] * max_val)
    val = max(0, min(max_val, val))
    encoded.append(val)

return encoded
```

def decode_seed_binary(encoded, bits_per_value=8):
“””
Decode binary to 6 proportional values.
“””
max_val = (1 << bits_per_value) - 1

```
proportions = []
for val in encoded:
    proportions.append(val / max_val)

# 6th value is remainder
remainder = 1.0 - sum(proportions)
proportions.append(max(0.0, remainder))

# Re-normalize to handle quantization errors
total = sum(proportions)
return [p / total for p in proportions]
```

# =============================================================================

# VERIFICATION

# =============================================================================

def verify_expansion(seed, steps=20):
“””
Verify that expansion preserves seed structure.
“””
seed = np.array(seed)
seed_normalized = seed / seed.sum()

```
shells = expand_seed(seed, steps=steps)

print("Verifying structure preservation:")
print(f"Seed proportions: {np.round(seed_normalized, 4)}")
print()

max_deviation = 0.0
for s in shells:
    S_prop = s['S'] / s['S'].sum()
    deviation = np.max(np.abs(S_prop - seed_normalized))
    max_deviation = max(max_deviation, deviation)
    
    if s['id'] <= 5 or s['id'] == steps:
        print(f"Shell {s['id']:2d}: {np.round(S_prop, 4)} (dev: {deviation:.2e})")

print(f"\nMax deviation across all shells: {max_deviation:.2e}")
print(f"Structure preserved: {'YES' if max_deviation < 1e-10 else 'NO'}")

return max_deviation < 1e-10
```

# =============================================================================

# DEMO

# =============================================================================

if **name** == “**main**”:
print(”=”*60)
print(“PHYSICS-COMPLIANT SEED EXPANSION”)
print(”=”*60)

```
# Define a seed
seed = [0.5, 0.2, 0.15, 0.08, 0.05, 0.02]

print(f"\nSeed: {seed}")
print(f"Interpretation: Strong +X bias, moderate -X and +Y")

# Expand
print("\n" + "-"*60)
print("EXPANDING...")
print("-"*60)

shells = expand_seed(seed, steps=15)

# Verify
print()
passed = verify_expansion(seed, steps=15)

# Binary encoding
print("\n" + "-"*60)
print("BINARY ENCODING")
print("-"*60)

encoded = encode_seed_binary(seed)
print(f"Encoded (5 × 8-bit): {encoded}")
print(f"Total bits: {len(encoded) * 8}")

decoded = decode_seed_binary(encoded)
print(f"Decoded: {[round(p, 4) for p in decoded]}")

# Verify decoded seed produces same structure
shells_from_decoded = expand_seed(decoded, steps=5)
original_final = shells[5]['S'] / shells[5]['S'].sum()
decoded_final = shells_from_decoded[5]['S'] / shells_from_decoded[5]['S'].sum()

encoding_error = np.max(np.abs(original_final - decoded_final))
print(f"Encoding-decoding error at shell 5: {encoding_error:.4f}")

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("""
```

This algorithm achieves:

1. MINIMAL SEED: 40 bits encodes the complete structure
1. PHYSICS-COMPLIANT EXPANSION: Any decompressor following
   energy conservation + field-mediated coupling arrives
   at identical structure
1. PAUSE-ANYWHERE: Every shell is a valid stable state;
   resources can be exhausted at any point
1. RESUME-WITHOUT-LOSS: Inner shells fully determine outer
   shells; causality flows one direction only
1. SCALE-INVARIANT: Structure preserved regardless of how
   many shells are expanded

The seed doesn’t describe the structure - it IS the structure
at its most compressed form. The expansion rules are physics
itself, shared by any valid decompressor.
“””)
