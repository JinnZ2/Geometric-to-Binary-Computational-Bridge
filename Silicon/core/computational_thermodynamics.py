# computational_thermodynamics.py
"""
Energetics of computational phase stability.

Connects the silicon manifold, energy framework, and crystalline storage
encoding to determine the metabolic cost of computation in each regime.

Key insight: computational phase boundaries are also energetic phase
boundaries. The cost of maintaining coherence diverges as you approach
the quantum-classical transition, just as the computational susceptibility
diverges.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

if TYPE_CHECKING:  # pandas is optional — imported lazily in the one function that uses it
    import pandas as pd


# ─── Physical constants ───

K_B = 8.617333262145e-5  # eV/K
HBAR = 6.582119569e-16   # eV·s
ROOM_TEMP = 300.0         # K


# ─── 1. Free Energy of a Silicon State ───

def free_energy(
    silicon_state: 'SiliconState',
    temperature: float = ROOM_TEMP,
    k_dft: Optional[float] = None,  # eV/Å², from hardware bridge
) -> float:
    """
    Helmholtz free energy F = E_internal - T·S of a silicon state.
    
    E_internal: from band structure + defect formation + strain
    S: configurational entropy of defects + carrier entropy
    
    Lower F = more thermodynamically stable.
    """
    
    # Internal energy contributions
    # Band gap energy (scales with carrier density)
    E_gap = 1.12  # eV, silicon bandgap at 300K
    E_electronic = E_gap * np.log10(silicon_state.n / 1e10 + 1) / 10
    
    # Defect formation energy
    E_defect_formation = 3.0  # eV per defect (typical Si vacancy)
    E_defects = E_defect_formation * silicon_state.d
    
    # Confinement energy (from dimensional reduction)
    E_confinement = 0.1 * (3.0 - silicon_state.l) ** 2  # eV
    
    # Strain energy (if k_dft provided)
    if k_dft is not None:
        # Harmonic approximation: E = ½ k x², where x ≈ 0.1 Å typical
        E_strain = 0.5 * k_dft * (0.1) ** 2
    else:
        E_strain = 0.0
    
    E_internal = E_electronic + E_defects + E_confinement + E_strain
    
    # Entropy contributions
    # Configurational entropy of defects: S = k_B ln(W)
    # W = N!/(n_d!(N-n_d)!) where n_d = d * N_sites
    N_sites = 5e22  # atoms/cm³ in Si
    n_defects = silicon_state.d * N_sites
    if n_defects > 0 and n_defects < N_sites:
        # Stirling approximation
        S_config = K_B * (
            N_sites * np.log(N_sites) 
            - n_defects * np.log(n_defects) 
            - (N_sites - n_defects) * np.log(N_sites - n_defects)
        )
    else:
        S_config = 0.0
    
    # Carrier entropy (ideal gas approximation)
    n_carriers = silicon_state.n
    if n_carriers > 0:
        # S_carrier ≈ k_B * n * ln(T^(3/2)/n)
        S_carriers = K_B * n_carriers * np.log(
            (temperature ** 1.5) / (n_carriers + 1)
        )
    else:
        S_carriers = 0.0
    
    S_total = S_config + S_carriers
    
    return E_internal - temperature * S_total


# ─── 2. Maintenance Energy (cost of staying in regime) ───

def maintenance_energy(
    silicon_state: 'SiliconState',
    temperature: float = ROOM_TEMP,
    T2_ms: Optional[float] = None,  # coherence time from hardware bridge
) -> float:
    """
    Energy required to maintain the silicon state against thermal drift
    and decoherence. This is the metabolic cost of computation.
    
    Higher near phase boundaries (susceptibility divergence).
    Higher in quantum regime (coherence maintenance).
    Lower in semiconductor regime (stable attractor).
    """
    
    # Thermal drift cost (from crystalline storage framework)
    # dphi = alpha * dT * L * (1 - beta * I_grating)
    alpha = 2.6e-6  # Si thermal expansion coefficient (1/K)
    L = 100.0       # characteristic length scale (nm)
    delta_T = abs(temperature - ROOM_TEMP)
    
    # Grating stabilization factor (from crystalline storage)
    beta = 0.5
    I_grating = silicon_state.k.get("optical", 0)  # optical coupling as grating
    
    thermal_drift = alpha * delta_T * L * (1 - beta * I_grating)
    
    # Coherence maintenance cost
    if T2_ms is not None and T2_ms > 0:
        # Energy per coherence time: E_coh ∝ ℏ / T₂
        coherence_cost = HBAR / (T2_ms * 1e-3)  # eV per coherence period
    else:
        # Estimate from coupling vector
        thermal_coupling = silicon_state.k.get("thermal", 0.1)
        coherent_coupling = silicon_state.k.get("coherent", 0.1)
        if thermal_coupling > 0:
            coherence_cost = K_B * temperature * thermal_coupling / (coherent_coupling + 1e-10)
        else:
            coherence_cost = 0.0
    
    # Defect management cost
    defect_cost = silicon_state.d * 0.5  # eV per defect fraction
    
    # Regime-specific overhead
    weights = silicon_state.regime_weights(temperature=0.1)
    quantum_weight = weights.get("quantum", 0)
    
    # Quantum error correction overhead
    # Surface code: ~1000 physical qubits per logical qubit
    qec_overhead = quantum_weight * 1000 * coherence_cost
    
    return thermal_drift + coherence_cost + defect_cost + qec_overhead


# ─── 3. Restoration Rate ───

def restoration_rate(
    silicon_state: 'SiliconState',
    e_current: float,
    e_max: float,
    temperature: float = ROOM_TEMP,
) -> float:
    """
    Rate at which the silicon state can restore to equilibrium.
    
    From energy framework: E_r = (E_max - E_t) * exp(-t / tau_r)
    
    The recovery time constant tau_r depends on the regime:
    - Semiconductor: fast (~ns, electronic)
    - Quantum: slow (~ms, phonon-limited)
    - Defect-dominated: very slow (~s, trap-mediated)
    """
    
    weights = silicon_state.regime_weights()
    
    # Recovery time constants by regime (seconds)
    tau_by_regime = {
        "semiconductor": 1e-9,      # electronic: nanoseconds
        "metallic": 1e-12,          # metallic: picoseconds
        "quantum": 1e-3,            # phonon-limited: milliseconds
        "photonic": 1e-9,           # optical: nanoseconds
        "defect_dominated": 1.0,    # trap-mediated: seconds
        "mechanical": 1e-6,         # mechanical: microseconds
    }
    
    # Weighted average recovery time
    tau_eff = sum(
        weights.get(r, 0) * tau_by_regime.get(r, 1e-6)
        for r in tau_by_regime
    )
    
    # Restoration rate (eV/s)
    return (e_max - e_current) / tau_eff


# ─── 4. Computational Stability Phase Diagram ───

@dataclass
class StabilityMetrics:
    """Stability metrics for a point in silicon phase space."""
    free_energy: float           # eV — thermodynamic stability
    maintenance_cost: float      # eV/s — cost to maintain state
    restoration_rate: float      # eV/s — recovery speed
    stability_ratio: float       # maintenance / restoration (want < 1)
    sustainable: bool            # can this state be maintained?
    max_computation_time: float  # seconds before thermal degradation


def compute_stability(
    silicon_state: 'SiliconState',
    temperature: float = ROOM_TEMP,
    k_dft: Optional[float] = None,
    T2_ms: Optional[float] = None,
) -> StabilityMetrics:
    """
    Compute stability metrics for a silicon state.
    
    A state is computationally viable only if:
    1. Free energy is negative (thermodynamically stable)
    2. Maintenance cost < restoration rate (can be sustained)
    3. Max computation time > required circuit depth
    """
    
    F = free_energy(silicon_state, temperature, k_dft)
    E_maint = maintenance_energy(silicon_state, temperature, T2_ms)
    E_max = abs(F) + 1.0  # maximum energy before degradation
    
    # Get restoration rate
    r_restore = restoration_rate(silicon_state, F, E_max, temperature)
    
    # Stability ratio: maintenance / restoration
    # Ratio > 1 means the state degrades faster than it can recover
    stability_ratio = E_maint / (r_restore + 1e-30)
    
    # Sustainable if ratio < 1 AND free energy is negative
    sustainable = (stability_ratio < 1.0) and (F < 0)
    
    # Maximum computation time before thermal degradation
    if E_maint > 0:
        # Time until energy budget exhausted
        energy_budget = E_max - abs(F)
        max_time = energy_budget / E_maint
    else:
        max_time = float('inf')
    
    return StabilityMetrics(
        free_energy=F,
        maintenance_cost=E_maint,
        restoration_rate=r_restore,
        stability_ratio=stability_ratio,
        sustainable=sustainable,
        max_computation_time=max_time,
    )


# ─── 5. Energetic Phase Boundary Detection ───

def detect_energetic_phase_boundary(
    silicon_state: 'SiliconState',
    perturbation: float = 0.01,
    temperature: float = ROOM_TEMP,
) -> float:
    """
    Detect energetic phase boundaries by measuring the energetic
    susceptibility: ∂(stability_ratio)/∂(perturbation).
    
    Diverges at boundaries where small changes in doping/defects/temperature
    cause the system to become unsustainable.
    """
    
    # Compute stability at current point
    metrics_center = compute_stability(silicon_state, temperature)
    
    # Compute stability at perturbed points along each axis
    from silicon_state import SiliconState
    
    # Perturb carrier density
    n_perturbed = SiliconState(
        n=silicon_state.n * (1 + perturbation),
        d=silicon_state.d,
        l=silicon_state.l,
        k=silicon_state.k.copy(),
    )
    metrics_n = compute_stability(n_perturbed, temperature)
    
    # Perturb defect density
    d_perturbed = SiliconState(
        n=silicon_state.n,
        d=min(1.0, silicon_state.d + perturbation),
        l=silicon_state.l,
        k=silicon_state.k.copy(),
    )
    metrics_d = compute_stability(d_perturbed, temperature)
    
    # Energetic susceptibility: max change in stability ratio
    delta_n = abs(metrics_n.stability_ratio - metrics_center.stability_ratio)
    delta_d = abs(metrics_d.stability_ratio - metrics_center.stability_ratio)
    
    return max(delta_n, delta_d) / perturbation


# ─── 6. Cross-Regime Energy Comparison ───

def compare_regime_energetics(
    states: Dict[str, 'SiliconState'],
    temperature: float = ROOM_TEMP,
) -> 'pd.DataFrame':
    """
    Compare the energetic costs of computation across different silicon regimes.
    
    Uses the energy framework's cross-domain comparison to show how
    different computational paradigms have different energy profiles.
    """
    import pandas as pd
    
    results = []
    for name, state in states.items():
        metrics = compute_stability(state, temperature)
        phase = classify_computational_phase(state)  # from earlier module
        
        results.append({
            "Name": name,
            "Computational Class": phase.comp_class.name,
            "Free Energy (eV)": f"{metrics.free_energy:.3f}",
            "Maintenance Cost (eV/s)": f"{metrics.maintenance_cost:.2e}",
            "Restoration Rate (eV/s)": f"{metrics.restoration_rate:.2e}",
            "Stability Ratio": f"{metrics.stability_ratio:.3f}",
            "Sustainable": metrics.sustainable,
            "Max Computation (s)": f"{metrics.max_computation_time:.2e}",
            "Coherence Volume": f"{phase.coherence_volume:.2f}",
            "Near Boundary": phase.is_near_transition(),
        })
    
    return pd.DataFrame(results)


# ─── 7. Optimal Operating Point Finder ───

def find_optimal_operating_point(
    target_regime: str = "quantum",
    n_range: Tuple[float, float] = (1e14, 1e20),
    d_range: Tuple[float, float] = (0.0, 0.5),
    n_steps: int = 50,
    temperature: float = 4.0,
) -> Dict:
    """
    Find the optimal (n, d) point for a target computational regime,
    maximizing sustainability while maintaining the target regime.
    """
    from silicon_state import SiliconState
    
    n_vals = np.logspace(np.log10(n_range[0]), np.log10(n_range[1]), n_steps)
    d_vals = np.linspace(d_range[0], d_range[1], n_steps)
    
    best_point = None
    best_score = -float('inf')
    
    for n in n_vals:
        for d in d_vals:
            state = SiliconState(
                n=n, d=d, l=3.0,
                k={"electrical": 0.5, "optical": 0.0, "thermal": 0.1,
                   "mechanical": 0.0, "coherent": 0.4}
            )
            metrics = compute_stability(state, temperature)
            phase = classify_computational_phase(state)
            
            # Score: high sustainability + target regime weight
            if metrics.sustainable:
                regime_weight = phase.comp_class.name == f"QUANTUM_{target_regime.upper()}" if target_regime == "bqp" else True
                score = (
                    1.0 / (metrics.stability_ratio + 1e-10)  # low ratio = stable
                    + metrics.max_computation_time * 0.1       # long computation time
                    + phase.coherence_volume * 10              # high coherence
                )
                
                if score > best_score:
                    best_score = score
                    best_point = {
                        "n": n,
                        "d": d,
                        "stability_ratio": metrics.stability_ratio,
                        "max_computation_time": metrics.max_computation_time,
                        "coherence_volume": phase.coherence_volume,
                        "comp_class": phase.comp_class.name,
                        "free_energy": metrics.free_energy,
                    }
    
    return best_point


# ─── Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("COMPUTATIONAL THERMODYNAMICS")
    print("Energetics of Phase Stability in Silicon Manifolds")
    print("=" * 70)
    
    from silicon_state import SiliconState
    from computational_phase_transition import classify_computational_phase
    
    # Test states across regimes
    test_states = {
        "CMOS (room temp)": SiliconState(
            n=1e16, d=0.02, l=3.0,
            k={"electrical": 0.8, "optical": 0.0, "thermal": 0.1, 
               "mechanical": 0.0, "coherent": 0.1}
        ),
        "Quantum (cryogenic)": SiliconState(
            n=1e17, d=0.01, l=0.5,
            k={"electrical": 0.2, "optical": 0.1, "thermal": 0.05,
               "mechanical": 0.05, "coherent": 0.6}
        ),
        "Defect-rich": SiliconState(
            n=1e16, d=0.75, l=2.5,
            k={"electrical": 0.3, "optical": 0.0, "thermal": 0.4,
               "mechanical": 0.2, "coherent": 0.1}
        ),
        "Near phase boundary": SiliconState(
            n=5e17, d=0.15, l=1.5,
            k={"electrical": 0.3, "optical": 0.1, "thermal": 0.3,
               "mechanical": 0.1, "coherent": 0.2}
        ),
    }
    
    # Compute stability for each
    for name, state in test_states.items():
        metrics = compute_stability(state, ROOM_TEMP)
        phase = classify_computational_phase(state)
        
        print(f"\n{name}:")
        print(f"  Class:           {phase.comp_class.name}")
        print(f"  Free Energy:     {metrics.free_energy:.3f} eV")
        print(f"  Maintenance:     {metrics.maintenance_cost:.2e} eV/s")
        print(f"  Restoration:     {metrics.restoration_rate:.2e} eV/s")
        print(f"  Stability ratio: {metrics.stability_ratio:.3f}")
        print(f"  Sustainable:     {metrics.sustainable}")
        print(f"  Max comp time:   {metrics.max_computation_time:.2e} s")
        print(f"  Coherence vol:   {phase.coherence_volume:.2f}")
        
        # Energetic susceptibility
        chi = detect_energetic_phase_boundary(state)
        print(f"  Energetic χ:     {chi:.2f}")
    
    # Compare across regimes
    print("\n\nRegime Comparison Table:")
    df = compare_regime_energetics(test_states, ROOM_TEMP)
    print(df.to_string(index=False))
    
    # Find optimal quantum operating point
    print("\n\nSearching for optimal quantum operating point...")
    optimal = find_optimal_operating_point("bqp", temperature=4.0)
    if optimal:
        print(f"  Optimal (n, d): ({optimal['n']:.2e}, {optimal['d']:.3f})")
        print(f"  Stability ratio: {optimal['stability_ratio']:.3f}")
        print(f"  Max comp time:   {optimal['max_computation_time']:.2e} s")
        print(f"  Coherence vol:   {optimal['coherence_volume']:.2f}")
    
    print("\n" + "=" * 70)
