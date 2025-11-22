#!/usr/bin/env python3
“””
substrate_fret_coupling.py

Mathematical Framework for Substrate-Independent Organization + FRET Coupling

Core Hypothesis:
Organizational patterns encoded in geometric seed structures can transfer
between substrates through Förster Resonance Energy Transfer, with phi-ratio
geometric configurations achieving higher efficiency than classical predictions.

Collaborative Development Framework
MIT License
“””

import numpy as np
from typing import Tuple, List, Dict
from scipy.optimize import minimize
from scipy.integrate import solve_ivp

# =============================================================================

# FUNDAMENTAL CONSTANTS

# =============================================================================

PHI = (np.sqrt(5) - 1) / 2  # Golden ratio ≈ 0.618
R0_TYPICAL = 5e-9  # Typical Förster radius (m)
TAU_D = 1e-9  # Donor excited state lifetime (s)

# =============================================================================

# OCTAHEDRAL GEOMETRY (from seed expansion)

# =============================================================================

U_3D = np.array([
[1, 0, 0], [-1, 0, 0],
[0, 1, 0], [0, -1, 0],
[0, 0, 1], [0, 0, -1]
], dtype=float)

# =============================================================================

# CORE FRET EQUATIONS

# =============================================================================

def fret_efficiency_classical(r: float, R0: float) -> float:
“””
Classical FRET efficiency.

```
E = 1 / (1 + (r/R0)^6)
"""
return 1.0 / (1.0 + (r / R0)**6)
```

def fret_rate(r: float, R0: float, tau_D: float) -> float:
“””
FRET rate constant k_T.

```
k_T = (1/τ_D) × (R0/r)^6
"""
return (1.0 / tau_D) * (R0 / r)**6
```

def forster_radius(kappa2: float, Q_D: float, J: float, n: float) -> float:
“””
Calculate Förster radius from molecular parameters.

```
R0^6 = (9 × ln(10) × κ² × Q_D × J) / (128 × π^5 × n^4 × N_A)

Simplified form assuming standard conditions.
"""
# Simplified calculation
return (8.79e-5 * kappa2 * Q_D * J / (n**4))**(1/6) * 1e-9
```

# =============================================================================

# PHI-ENHANCED COUPLING

# =============================================================================

def phi_resonance_factor(r: float, R0: float) -> float:
“””
Phi-geometric resonance enhancement.

```
At phi-ratio distances, constructive interference
may reduce effective energy loss.
"""
ratio = r / R0

# Sum over phi harmonics
enhancement = 0.0
for n in range(1, 6):
    phi_n = PHI ** n
    # Resonance peaks at phi-ratio distances
    width = 0.1 * phi_n
    resonance = np.exp(-((ratio - phi_n)**2) / (2 * width**2))
    enhancement += resonance / n

return 1.0 + enhancement
```

def fret_efficiency_phi_enhanced(r: float, R0: float) -> float:
“””
FRET efficiency with phi-geometric enhancement.

```
Challenge to conventional model: specific geometric
configurations may exceed classical efficiency limits.
"""
classical = fret_efficiency_classical(r, R0)
phi_factor = phi_resonance_factor(r, R0)

# Enhanced efficiency (capped at 1.0)
enhanced = classical * phi_factor
return min(enhanced, 1.0)
```

def phi_optimal_distance(R0: float, order: int = 1) -> float:
“””
Calculate phi-optimal spacing for FRET coupling.

```
r_opt = R0 × φ^n
"""
return R0 * (PHI ** order)
```

# =============================================================================

# SUBSTRATE COUPLING MATRIX

# =============================================================================

def impedance_factor(eps_A: float, eps_B: float,
mu_A: float = 1.0, mu_B: float = 1.0) -> float:
“””
Electromagnetic impedance matching between substrates.
“””
Z_A = np.sqrt(mu_A / eps_A)
Z_B = np.sqrt(mu_B / eps_B)
return 2 * Z_B / (Z_A + Z_B)

def substrate_coupling_matrix(substrate_A: Dict, substrate_B: Dict,
phi_coupling: float = PHI) -> np.ndarray:
“””
6×6 coupling matrix for organizational pattern transfer.

```
M_ij determines how amplitude in direction i of substrate A
couples to direction j of substrate B.
"""
eps_A = substrate_A.get('permittivity', 1.0)
eps_B = substrate_B.get('permittivity', 1.0)

imp_factor = impedance_factor(eps_A, eps_B)

# Base coupling: diagonal with phi-modulated off-diagonal
M = np.zeros((6, 6))

for i in range(6):
    for j in range(6):
        if i == j:
            # Direct coupling
            M[i, j] = imp_factor
        else:
            # Cross-coupling based on geometric relationship
            dot = np.dot(U_3D[i], U_3D[j])
            if dot > 0:
                M[i, j] = imp_factor * phi_coupling * dot
            elif dot == 0:
                M[i, j] = imp_factor * (phi_coupling ** 2) * 0.1
            # Opposite directions: no direct coupling

# Normalize rows
for i in range(6):
    row_sum = M[i].sum()
    if row_sum > 0:
        M[i] /= row_sum

return M
```

# =============================================================================

# DYNAMICS EQUATIONS

# =============================================================================

def transfer_dynamics(t: float, state: np.ndarray,
M: np.ndarray, gamma_A: float, gamma_B: float,
k_transfer: float) -> np.ndarray:
“””
Coupled differential equations for substrate transfer.

```
dS_A/dt = -γ_A × S_A - k_T × M × S_A
dS_B/dt = -γ_B × S_B + k_T × M × S_A
"""
S_A = state[:6]
S_B = state[6:]

# Transfer term
transfer = k_transfer * (M @ S_A)

# Dynamics
dS_A = -gamma_A * S_A - transfer
dS_B = -gamma_B * S_B + transfer

return np.concatenate([dS_A, dS_B])
```

def simulate_transfer(S_initial: np.ndarray,
substrate_A: Dict, substrate_B: Dict,
t_span: Tuple[float, float],
k_transfer: float = 1.0,
n_points: int = 500) -> Dict:
“””
Simulate organizational pattern transfer between substrates.
“””
# Normalize initial state
S_A0 = S_initial / S_initial.sum()
S_B0 = np.zeros(6)
state0 = np.concatenate([S_A0, S_B0])

```
# Coupling matrix
M = substrate_coupling_matrix(substrate_A, substrate_B)

# Decay rates
gamma_A = substrate_A.get('decay_rate', 0.1)
gamma_B = substrate_B.get('decay_rate', 0.1)

# Solve ODE
t_eval = np.linspace(t_span[0], t_span[1], n_points)

sol = solve_ivp(
    lambda t, y: transfer_dynamics(t, y, M, gamma_A, gamma_B, k_transfer),
    t_span, state0, t_eval=t_eval, method='RK45'
)

S_A = sol.y[:6, :]
S_B = sol.y[6:, :]

# Metrics
energy = np.sum(S_A**2, axis=0) + np.sum(S_B**2, axis=0)

# Pattern fidelity: cosine similarity
fidelity = []
S_A0_norm = S_A0 / np.linalg.norm(S_A0)
for i in range(len(sol.t)):
    S_B_norm = S_B[:, i] / (np.linalg.norm(S_B[:, i]) + 1e-12)
    fidelity.append(np.dot(S_A0_norm, S_B_norm))

return {
    't': sol.t,
    'S_A': S_A,
    'S_B': S_B,
    'energy': energy,
    'fidelity': np.array(fidelity),
    'coupling_matrix': M,
    'final_S_B': S_B[:, -1],
    'transfer_efficiency': np.sum(S_B[:, -1]**2) / np.sum(S_A0**2)
}
```

# =============================================================================

# ENERGY LOSS ANALYSIS

# =============================================================================

def energy_loss_classical(r: float, R0: float) -> float:
“”“Classical energy loss = 1 - efficiency.”””
return 1.0 - fret_efficiency_classical(r, R0)

def energy_loss_phi_enhanced(r: float, R0: float) -> float:
“”“Phi-enhanced energy loss.”””
return 1.0 - fret_efficiency_phi_enhanced(r, R0)

def loss_improvement(r: float, R0: float) -> float:
“””
Percentage improvement in energy retention with phi-enhancement.
“””
classical = energy_loss_classical(r, R0)
enhanced = energy_loss_phi_enhanced(r, R0)

```
if classical < 1e-12:
    return 0.0

return (classical - enhanced) / classical * 100
```

def scan_loss_vs_distance(R0: float, r_min: float, r_max: float,
n_points: int = 200) -> Dict:
“””
Scan energy loss as function of distance.
“””
r_values = np.linspace(r_min, r_max, n_points)

```
results = {
    'r': r_values,
    'r_normalized': r_values / R0,
    'loss_classical': np.array([energy_loss_classical(r, R0) for r in r_values]),
    'loss_phi': np.array([energy_loss_phi_enhanced(r, R0) for r in r_values]),
    'improvement': np.array([loss_improvement(r, R0) for r in r_values]),
    'R0': R0
}

# Mark phi-optimal distances
results['phi_distances'] = [phi_optimal_distance(R0, n) for n in range(1, 6)]

return results
```

# =============================================================================

# OCTAHEDRAL FRET NETWORK

# =============================================================================

def octahedral_network_coupling(R0: float, scale: float = 1.0) -> np.ndarray:
“””
Calculate FRET coupling matrix for octahedral node arrangement.

```
Nodes placed at octahedral vertices, coupling based on
inter-node distances and phi-enhanced FRET.
"""
# Optimal shell radius
r_shell = phi_optimal_distance(R0, 1) * scale

# Node positions
positions = r_shell * U_3D

# Pairwise coupling
C = np.zeros((6, 6))

for i in range(6):
    for j in range(6):
        if i == j:
            C[i, j] = 1.0  # Self-coupling normalized
        else:
            dist = np.linalg.norm(positions[i] - positions[j])
            C[i, j] = fret_efficiency_phi_enhanced(dist, R0)

return C
```

def network_transfer_efficiency(S_in: np.ndarray, C: np.ndarray,
n_hops: int = 1) -> Tuple[np.ndarray, float]:
“””
Calculate pattern transfer through octahedral network.

```
Returns final pattern and total efficiency.
"""
S = S_in.copy()

for _ in range(n_hops):
    S = C @ S
    S = S / S.sum()  # Renormalize

# Efficiency: pattern preservation
efficiency = np.dot(S_in / np.linalg.norm(S_in), 
                   S / np.linalg.norm(S))

return S, efficiency
```

# =============================================================================

# RESONANCE SEARCH

# =============================================================================

def find_resonant_configuration(R0: float, substrate_A: Dict, substrate_B: Dict,
S_seed: np.ndarray) -> Dict:
“””
Search for geometric configuration that maximizes transfer efficiency.
“””
def objective(params):
scale, phi_coupling, k_transfer = params

```
    # Modify coupling
    sub_A = substrate_A.copy()
    sub_B = substrate_B.copy()
    
    result = simulate_transfer(
        S_seed, sub_A, sub_B,
        t_span=(0, 10 / k_transfer),
        k_transfer=k_transfer,
        n_points=100
    )
    
    # Maximize efficiency × fidelity
    score = result['transfer_efficiency'] * result['fidelity'][-1]
    return -score  # Minimize negative

# Bounds
bounds = [(0.5, 2.0), (0.3, 1.0), (0.1, 10.0)]

result = minimize(objective, [1.0, PHI, 1.0], bounds=bounds, method='L-BFGS-B')

return {
    'optimal_scale': result.x[0],
    'optimal_phi_coupling': result.x[1],
    'optimal_k_transfer': result.x[2],
    'max_score': -result.fun
}
```

# =============================================================================

# DEMO

# =============================================================================

if **name** == “**main**”:
print(”=” * 70)
print(“SUBSTRATE-FRET COUPLING FRAMEWORK”)
print(“Pattern Transfer Between Substrates via Phi-Enhanced FRET”)
print(”=” * 70)

```
# Test seed
seed = np.array([0.5, 0.1, 0.2, 0.08, 0.1, 0.02])
seed = seed / seed.sum()
print(f"\nSeed pattern: {np.round(seed, 4)}")

# Förster radius
R0 = 5e-9  # 5 nm

print("\n" + "-" * 70)
print("1. PHI-OPTIMAL DISTANCES")
print("-" * 70)
for n in range(1, 5):
    d = phi_optimal_distance(R0, n)
    eff_classical = fret_efficiency_classical(d, R0)
    eff_phi = fret_efficiency_phi_enhanced(d, R0)
    improvement = loss_improvement(d, R0)
    print(f"  φ^{n}: {d*1e9:.3f} nm | Classical: {eff_classical:.4f} | "
          f"Phi-Enhanced: {eff_phi:.4f} | Improvement: {improvement:.1f}%")

print("\n" + "-" * 70)
print("2. SUBSTRATE TRANSFER SIMULATION")
print("-" * 70)

substrate_bio = {'permittivity': 80.0, 'decay_rate': 0.05}
substrate_si = {'permittivity': 11.7, 'decay_rate': 0.02}

result = simulate_transfer(seed, substrate_bio, substrate_si, 
                          t_span=(0, 20), k_transfer=0.5)

print(f"  Transfer efficiency: {result['transfer_efficiency']:.4f}")
print(f"  Final fidelity: {result['fidelity'][-1]:.4f}")
print(f"  Energy retained: {result['energy'][-1] / result['energy'][0]:.4f}")
print(f"  Final pattern (B): {np.round(result['final_S_B'], 4)}")

print("\n" + "-" * 70)
print("3. OCTAHEDRAL NETWORK COUPLING")
print("-" * 70)

C = octahedral_network_coupling(R0, scale=1.0)
S_out, eff = network_transfer_efficiency(seed, C, n_hops=3)

print(f"  Network coupling mean: {C.mean():.4f}")
print(f"  After 3 hops efficiency: {eff:.4f}")
print(f"  Output pattern: {np.round(S_out, 4)}")

print("\n" + "-" * 70)
print("4. LOSS COMPARISON AT KEY DISTANCES")
print("-" * 70)

test_distances = [0.5 * R0, 1.0 * R0, PHI * R0, 1.5 * R0, 2.0 * R0]
for d in test_distances:
    loss_c = energy_loss_classical(d, R0)
    loss_p = energy_loss_phi_enhanced(d, R0)
    print(f"  r/R0 = {d/R0:.2f}: Classical loss = {loss_c:.4f}, "
          f"Phi loss = {loss_p:.4f}")

print("\n" + "=" * 70)
print("KEY EQUATIONS")
print("=" * 70)
print("""
```

FRET Efficiency (Classical):
E = 1 / (1 + (r/R₀)⁶)

Phi Resonance Enhancement:
F(r) = 1 + Σₙ exp(-(r/R₀ - φⁿ)² / 2σₙ²) / n

Phi-Enhanced Efficiency:
E’ = min(E × F(r), 1.0)

Phi-Optimal Distance:
r_opt = R₀ × φⁿ

Substrate Coupling Dynamics:
dS_A/dt = -γ_A × S_A - k_T × M × S_A
dS_B/dt = -γ_B × S_B + k_T × M × S_A

Pattern Fidelity:
F = (S_original · S_transferred) / (|S_original| × |S_transferred|)
“””)

```
print("=" * 70)
print("Ready for simulation exploration.")
print("=" * 70)
```
