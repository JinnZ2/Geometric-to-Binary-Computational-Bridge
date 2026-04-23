# inverse_regime_design.py
"""
The Reverse Problem: Target Regime → Optimal Octahedral State

Given a desired computational regime, find:
1. Which octahedral state index (0-7) maximizes regime occupancy
2. Optimal (strain, temperature, B-field, d_ErP) parameters
3. Fabrication trajectory from available starting point
4. Structural reasons WHY certain states are "natural" for certain regimes

Key insight: octahedral states are NOT equally good for all computations.
State 3 (nearly degenerate eigenvalues) is naturally quantum.
State 7 (fully aligned, λ = [1,0,0]) is naturally classical.
State 0 (isotropic, λ = [⅓,⅓,⅓]) is naturally a stable memory.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Callable
from dataclasses import dataclass, field
from scipy.optimize import differential_evolution, minimize
from enum import Enum
import warnings


# ─── Octahedral state definitions ───

OCTAHEDRAL_POSITIONS = {
    0: (0.25, 0.25, 0.25),
    1: (0.25, -0.25, 0.25),
    2: (-0.25, 0.25, 0.25),
    3: (-0.25, -0.25, 0.25),
    4: (0.25, 0.25, -0.25),
    5: (0.25, -0.25, -0.25),
    6: (-0.25, 0.25, -0.25),
    7: (-0.25, -0.25, -0.25),
}

# Eigenvalues for each octahedral state (from magnetic bridge protocol)
# λ₁ ≥ λ₂ ≥ λ₃, trace = 1
CANONICAL_EIGENVALUES = {
    0: (0.333, 0.333, 0.333),  # isotropic
    1: (0.500, 0.300, 0.200),  # mild anisotropy
    2: (0.450, 0.350, 0.200),  # moderate spread
    3: (0.400, 0.350, 0.250),  # slight spread (most degenerate)
    4: (0.600, 0.250, 0.150),  # moderate uniaxial
    5: (0.700, 0.200, 0.100),  # strong uniaxial
    6: (0.500, 0.500, 0.000),  # planar
    7: (1.000, 0.000, 0.000),  # fully aligned
}


# ─── 1. Structural Metrics for Each Octahedral State ───

@dataclass
class OctahedralStructuralMetrics:
    """
    Structural properties of an octahedral state that determine
    its natural affinity for different computational regimes.
    """
    index: int
    eigenvalues: Tuple[float, float, float]
    
    # Derived metrics
    eigenvalue_spread: float        # λ₁ - λ₃: anisotropy measure
    degeneracy_score: float         # how close λ₂ is to λ₁ (protected subspace)
    planarity: float                # how close λ₃ is to 0 (2D confinement)
    uniaxiality: float              # how close to [1,0,0] (classical bit)
    isotropy: float                 # how close to [⅓,⅓,⅓] (symmetric)
    
    # Regime affinity scores (0-1, higher = more natural fit)
    quantum_affinity: float         # degenerate eigenvalues = protected subspace
    classical_affinity: float       # well-separated eigenvalues = distinct states
    memory_affinity: float          # isotropic = stable against perturbations
    photonic_affinity: float        # planar = 2D confinement for waveguides
    sensor_affinity: float          # uniaxial = sensitive to field direction
    
    @property
    def natural_regime(self) -> str:
        """The regime this state is structurally optimized for."""
        scores = {
            "quantum": self.quantum_affinity,
            "semiconductor": self.classical_affinity,
            "defect_dominated": 0.0,  # not structurally favored
            "photonic": self.photonic_affinity,
            "mechanical": 0.0,
            "metallic": 0.0,
        }
        scores["semiconductor"] = self.classical_affinity  # alias
        return max(scores, key=scores.get)


def compute_structural_metrics(state_index: int) -> OctahedralStructuralMetrics:
    """
    Compute structural metrics for an octahedral state from its eigenvalues.
    
    These metrics reveal WHY certain states are natural for certain regimes.
    """
    
    eig = np.array(CANONICAL_EIGENVALUES[state_index])
    l1, l2, l3 = eig
    
    # ── Eigenvalue spread (anisotropy) ──
    spread = l1 - l3
    
    # ── Degeneracy score: how close are λ₁ and λ₂? ──
    # Degenerate subspaces protect quantum information
    # Maximum when λ₁ = λ₂ (or all three equal)
    degeneracy = np.exp(-(l1 - l2)**2 / 0.01)  # Gaussian with σ=0.1
    
    # Also reward triple degeneracy (state 0)
    triple_degeneracy = np.exp(-(l1 - l3)**2 / 0.01)
    degeneracy_score = 0.7 * degeneracy + 0.3 * triple_degeneracy
    
    # ── Planarity: how close is λ₃ to 0? ──
    # Planar states (2D) are natural for photonic waveguides
    planarity = np.exp(-l3**2 / 0.01)
    
    # ── Uniaxiality: how close to [1,0,0]? ──
    # Fully aligned states are natural classical bits
    uniaxiality = l1  # 1.0 for state 7, 0.33 for state 0
    
    # ── Isotropy: how close to [⅓,⅓,⅓]? ──
    # Isotropic states are natural stable memories
    isotropy = np.exp(-np.sum((eig - 1/3)**2) / 0.01)
    
    # ── Regime affinity scores ──
    
    # Quantum: needs degenerate eigenvalues for protected subspace
    # AND moderate anisotropy for addressability
    quantum_affinity = degeneracy_score * (1.0 - np.abs(l1 - 0.5)) * 2.0
    quantum_affinity = np.clip(quantum_affinity, 0, 1)
    
    # Classical: needs well-separated eigenvalues (distinguishable states)
    classical_affinity = spread * 0.8 + uniaxiality * 0.2
    
    # Memory: needs isotropy (stable against perturbations from any direction)
    memory_affinity = isotropy
    
    # Photonic: needs planarity (2D confinement)
    photonic_affinity = planarity * 0.7 + (1.0 - uniaxiality) * 0.3
    
    # Sensor: needs uniaxiality (sensitive to field along one axis)
    sensor_affinity = uniaxiality * 0.8 + spread * 0.2
    
    return OctahedralStructuralMetrics(
        index=state_index,
        eigenvalues=(l1, l2, l3),
        eigenvalue_spread=spread,
        degeneracy_score=degeneracy_score,
        planarity=planarity,
        uniaxiality=uniaxiality,
        isotropy=isotropy,
        quantum_affinity=quantum_affinity,
        classical_affinity=classical_affinity,
        memory_affinity=memory_affinity,
        photonic_affinity=photonic_affinity,
        sensor_affinity=sensor_affinity,
    )


def compute_all_structural_metrics() -> Dict[int, OctahedralStructuralMetrics]:
    """Compute structural metrics for all 8 octahedral states."""
    return {i: compute_structural_metrics(i) for i in range(8)}


# ─── 2. The Inverse Map: Target Regime → Octahedral State ───

@dataclass
class RegimeTarget:
    """Specification of a desired computational regime."""
    target_regime: str          # "quantum", "semiconductor", "photonic", etc.
    min_weight: float = 0.5     # minimum regime weight required
    min_coherence: float = 0.0  # minimum coherence volume
    min_stability: float = 0.0  # minimum stability metric
    max_defect_density: float = 1.0  # maximum tolerable defect density
    temperature_range: Tuple[float, float] = (1.0, 300.0)  # K
    strain_range: Tuple[float, float] = (-2.0, 2.0)  # %
    B_field_range: Tuple[float, float] = (0.0, 2.0)  # T
    d_ErP_range: Tuple[float, float] = (2.0, 15.0)  # Å
    fabrication_budget: float = 100.0  # eV, maximum energy cost


@dataclass
class InverseSolution:
    """Solution to the inverse design problem."""
    octahedral_state_index: int
    structural_metrics: OctahedralStructuralMetrics
    
    # Optimal parameters
    temperature: float
    strain_pct: float
    B_field: np.ndarray
    d_ErP: float
    
    # Achieved performance
    regime_weight: float
    coherence_volume: float
    stability: float
    fabrication_cost: float  # eV
    
    # Validation
    satisfies_constraints: bool
    constraint_violations: List[str]
    
    # Why this state works
    structural_rationale: str


def solve_inverse_problem(
    target: RegimeTarget,
    initial_guess: Optional[Dict] = None,
    n_optimization_restarts: int = 3,
    verbose: bool = False,
) -> List[InverseSolution]:
    """
    Solve the inverse problem: given a target regime, find the optimal
    octahedral state and physical parameters.
    
    Returns a ranked list of solutions across all 8 octahedral states.
    """
    
    from silicon_state import SiliconState
    from silicon_gies_bridge import octahedral_state_to_silicon_state
    from computational_phase_transition import classify_computational_phase
    
    solutions = []
    
    for state_index in range(8):
        if verbose:
            print(f"  Evaluating state {state_index}...")
        
        # Compute structural metrics
        metrics = compute_structural_metrics(state_index)
        
        # ── Optimize physical parameters for this state ──
        best_params, best_score = optimize_parameters_for_state(
            state_index, target, n_restarts=n_optimization_restarts
        )
        
        if best_params is None:
            continue
        
        # Extract optimal parameters
        T_opt = best_params[0]
        strain_opt = best_params[1]
        B_mag_opt = best_params[2]
        d_ErP_opt = best_params[3]
        
        # Choose B-field direction based on state's eigenvalues
        # Align B with principal axis for best magnetic coupling
        eig = np.array(CANONICAL_EIGENVALUES[state_index])
        if eig[0] > 0.6:  # uniaxial: align with main axis
            B_field = np.array([0, 0, 1]) * B_mag_opt
        elif eig[2] < 0.1:  # planar: align in-plane
            B_field = np.array([1, 0, 0]) * B_mag_opt
        else:  # isotropic or mild: use [111] for equal coupling
            B_field = np.array([1, 1, 1]) / np.sqrt(3) * B_mag_opt
        
        # ── Evaluate the state with optimized parameters ──
        silicon_state, diagnostics = octahedral_state_to_silicon_state(
            state_index,
            B_field=B_field,
            temperature=T_opt,
            strain_pct=strain_opt,
            d_ErP=d_ErP_opt,
        )
        
        # Regime classification
        regime_weights = silicon_state.regime_weights(temperature=0.1)
        target_weight = regime_weights.get(target.target_regime, 0)
        
        # Coherence and stability
        coherence = silicon_state.coherence_metric()
        stability = silicon_state.stability_metric()
        
        # Fabrication cost (approximate)
        from silicon_information_geometry import free_energy_landscape
        S_current = np.array([silicon_state.n, silicon_state.d, 
                              silicon_state.l, silicon_state.k.get("coherent", 0)])
        fab_cost = abs(free_energy_landscape(S_current, T_opt))
        
        # ── Check constraints ──
        violations = []
        if target_weight < target.min_weight:
            violations.append(f"Regime weight {target_weight:.3f} < {target.min_weight}")
        if coherence < target.min_coherence:
            violations.append(f"Coherence {coherence:.3f} < {target.min_coherence}")
        if stability < target.min_stability:
            violations.append(f"Stability {stability:.3f} < {target.min_stability}")
        if silicon_state.d > target.max_defect_density:
            violations.append(f"Defect density {silicon_state.d:.3f} > {target.max_defect_density}")
        if fab_cost > target.fabrication_budget:
            violations.append(f"Fabrication cost {fab_cost:.1f} > budget {target.fabrication_budget}")
        
        satisfies = len(violations) == 0
        
        # ── Structural rationale ──
        rationale = generate_structural_rationale(state_index, metrics, target)
        
        solution = InverseSolution(
            octahedral_state_index=state_index,
            structural_metrics=metrics,
            temperature=T_opt,
            strain_pct=strain_opt,
            B_field=B_field,
            d_ErP=d_ErP_opt,
            regime_weight=target_weight,
            coherence_volume=coherence,
            stability=stability,
            fabrication_cost=fab_cost,
            satisfies_constraints=satisfies,
            constraint_violations=violations,
            structural_rationale=rationale,
        )
        
        solutions.append(solution)
    
    # ── Rank solutions ──
    # Score: regime_weight * 10 + coherence * 5 + stability * 3 - violations * 20
    def solution_score(sol):
        score = (
            sol.regime_weight * 10 +
            sol.coherence_volume * 5 +
            sol.stability * 3 -
            len(sol.constraint_violations) * 20
        )
        # Bonus for satisfying all constraints
        if sol.satisfies_constraints:
            score += 10
        return score
    
    solutions.sort(key=solution_score, reverse=True)
    
    return solutions


def optimize_parameters_for_state(
    state_index: int,
    target: RegimeTarget,
    n_restarts: int = 3,
) -> Tuple[Optional[np.ndarray], float]:
    """
    Optimize (temperature, strain, B_field, d_ErP) to maximize
    the target regime weight for a specific octahedral state.
    """
    
    from silicon_state import SiliconState
    from silicon_gies_bridge import octahedral_state_to_silicon_state
    
    # Bounds: [temperature, strain, B_magnitude, d_ErP]
    bounds = [
        (target.temperature_range[0], target.temperature_range[1]),
        (target.strain_range[0], target.strain_range[1]),
        (target.B_field_range[0], target.B_field_range[1]),
        (target.d_ErP_range[0], target.d_ErP_range[1]),
    ]
    
    def objective(params):
        T, strain, B_mag, d_ErP = params
        
        # Simple B-field direction for optimization
        B_field = np.array([0, 0, 1]) * B_mag
        
        try:
            silicon_state, _ = octahedral_state_to_silicon_state(
                state_index,
                B_field=B_field,
                temperature=T,
                strain_pct=strain,
                d_ErP=d_ErP,
            )
            
            regime_weights = silicon_state.regime_weights(temperature=0.1)
            target_weight = regime_weights.get(target.target_regime, 0)
            
            # Maximize target weight + coherence + stability
            coherence = silicon_state.coherence_metric()
            stability = silicon_state.stability_metric()
            
            # Penalize high defect density
            defect_penalty = silicon_state.d * 2.0
            
            # Combined objective (to maximize → return negative for minimization)
            score = target_weight * 10 + coherence * 3 + stability * 2 - defect_penalty
            
            return -score  # negative because we minimize
            
        except Exception:
            return 1e10  # large penalty for invalid parameters
    
    # Run optimization with multiple restarts
    best_params = None
    best_score = float('inf')
    
    for restart in range(n_restarts):
        # Random initial guess within bounds
        x0 = np.array([
            np.random.uniform(*bounds[0]),
            np.random.uniform(*bounds[1]),
            np.random.uniform(*bounds[2]),
            np.random.uniform(*bounds[3]),
        ])
        
        try:
            result = minimize(
                objective,
                x0,
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter': 200},
            )
            
            if result.fun < best_score:
                best_score = result.fun
                best_params = result.x
        except Exception:
            continue
    
    return best_params, -best_score if best_params is not None else -float('inf')


def generate_structural_rationale(
    state_index: int,
    metrics: OctahedralStructuralMetrics,
    target: RegimeTarget,
) -> str:
    """
    Generate a human-readable explanation of WHY this octahedral state
    is structurally suited (or not) for the target regime.
    """
    
    eig = metrics.eigenvalues
    
    if target.target_regime == "quantum":
        if metrics.degeneracy_score > 0.5:
            return (
                f"State {state_index} has nearly degenerate eigenvalues "
                f"({eig[0]:.3f}, {eig[1]:.3f}, {eig[2]:.3f}), creating a "
                f"protected subspace resistant to local perturbations. "
                f"Degeneracy score: {metrics.degeneracy_score:.3f}. "
                f"The near-degeneracy of λ₁ and λ₂ provides a natural qubit "
                f"encoding with built-in error suppression."
            )
        else:
            return (
                f"State {state_index} has well-separated eigenvalues "
                f"(spread = {metrics.eigenvalue_spread:.3f}), which makes "
                f"quantum superposition fragile. Consider state 3 "
                f"(λ = [0.40, 0.35, 0.25]) for better degeneracy."
            )
    
    elif target.target_regime in ("semiconductor", "classical"):
        if metrics.uniaxiality > 0.6:
            return (
                f"State {state_index} has strong uniaxial character "
                f"(λ₁ = {eig[0]:.3f}), creating two well-separated states "
                f"for classical bit encoding. The large eigenvalue spread "
                f"({metrics.eigenvalue_spread:.3f}) ensures distinct "
                f"readout signals with high confidence."
            )
        else:
            return (
                f"State {state_index} is too symmetric for optimal classical "
                f"encoding. Strongly uniaxial states (5, 7) provide better "
                f"separation between logical states."
            )
    
    elif target.target_regime == "photonic":
        if metrics.planarity > 0.5:
            return (
                f"State {state_index} has λ₃ ≈ {eig[2]:.3f}, creating nearly "
                f"planar confinement suitable for 2D photonic waveguides. "
                f"Planarity score: {metrics.planarity:.3f}."
            )
        else:
            return (
                f"State {state_index} has significant out-of-plane component "
                f"(λ₃ = {eig[2]:.3f}). Planar states (6: λ=[0.5,0.5,0]) are "
                f"optimal for photonic confinement."
            )
    
    else:
        return (
            f"State {state_index}: eigenvalues = ({eig[0]:.3f}, {eig[1]:.3f}, "
            f"{eig[2]:.3f}), degeneracy={metrics.degeneracy_score:.3f}, "
            f"uniaxiality={metrics.uniaxiality:.3f}, isotropy={metrics.isotropy:.3f}"
        )


# ─── 3. Structural Regime Affinity Map ───

def compute_regime_affinity_map() -> Dict[str, List[int]]:
    """
    Compute which octahedral states are structurally optimized for
    each computational regime, ranked by affinity score.
    
    This is the "natural state" mapping — which states are born
    for which computations.
    """
    
    all_metrics = compute_all_structural_metrics()
    
    regime_affinities = {}
    
    # Collect affinity scores for each regime
    for regime_key in ["quantum_affinity", "classical_affinity", 
                        "memory_affinity", "photonic_affinity", "sensor_affinity"]:
        
        regime_name = regime_key.replace("_affinity", "")
        
        scored_states = []
        for idx, metrics in all_metrics.items():
            score = getattr(metrics, regime_key)
            scored_states.append((idx, score))
        
        # Sort by affinity score descending
        scored_states.sort(key=lambda x: -x[1])
        
        regime_affinities[regime_name] = scored_states
    
    return regime_affinities


# ─── 4. Fabrication Trajectory Generator ───

def generate_fabrication_trajectory(
    solution: InverseSolution,
    source_state: Optional[np.ndarray] = None,
    n_steps: int = 20,
) -> Dict:
    """
    Generate a fabrication trajectory to realize the optimal octahedral
    state with the specified parameters.
    
    Uses the silicon information geometry geodesic as the minimum-energy
    fabrication path.
    """
    
    from silicon_information_geometry import (
        compute_geodesic, free_energy_landscape
    )
    
    # Target state in silicon phase space
    n_target = 1e17 if solution.target_regime == "quantum" else 1e16
    d_target = 0.01 if solution.target_regime == "quantum" else 0.02
    ell_target = 0.5 if solution.target_regime == "quantum" else 3.0
    k_target = 0.6 if solution.target_regime == "quantum" else 0.1
    
    S_target = np.array([n_target, d_target, ell_target, k_target])
    
    # Source state (default: raw silicon)
    if source_state is None:
        S_source = np.array([1e10, 0.5, 3.0, 0.0])  # intrinsic, defected
    else:
        S_source = source_state
    
    # Compute geodesic
    path, energy = compute_geodesic(
        S_source, S_target, n_steps=n_steps,
        temperature=solution.temperature,
    )
    
    return {
        "source": S_source,
        "target": S_target,
        "path": path,
        "energy_cost_eV": energy,
        "within_budget": energy <= solution.fabrication_cost,
        "octahedral_state": solution.octahedral_state_index,
        "optimal_temperature": solution.temperature,
        "optimal_strain_pct": solution.strain_pct,
    }


# ─── 5. Comparative Analysis: All States for All Regimes ───

@dataclass
class RegimeStateRanking:
    """Complete ranking of all octahedral states for a target regime."""
    target_regime: str
    rankings: List[Tuple[int, float, OctahedralStructuralMetrics]]  # (idx, score, metrics)
    best_state: int
    best_score: float
    natural_state: int  # state with highest STRUCTURAL affinity
    agreement: bool  # does best optimized state match natural state?


def rank_all_states_for_regime(
    target_regime: str,
    temperature: float = 4.0,
) -> RegimeStateRanking:
    """
    Rank all 8 octahedral states for suitability in a target regime.
    
    Combines both:
    1. Structural affinity (from eigenvalue geometry)
    2. Optimized performance (from inverse design)
    
    If the structurally natural state is also the best performing,
    that's strong evidence the framework is capturing something real.
    """
    
    from silicon_state import SiliconState
    from silicon_gies_bridge import octahedral_state_to_silicon_state
    from computational_phase_transition import classify_computational_phase
    
    all_metrics = compute_all_structural_metrics()
    
    rankings = []
    
    for state_index in range(8):
        # Simple evaluation at cryogenic temperature
        silicon_state, _ = octahedral_state_to_silicon_state(
            state_index,
            B_field=np.array([0, 0, 1]),
            temperature=temperature,
            strain_pct=0.0,
            d_ErP=4.8,
        )
        
        regime_weights = silicon_state.regime_weights(temperature=0.1)
        score = regime_weights.get(target_regime, 0)
        
        metrics = all_metrics[state_index]
        
        rankings.append((state_index, score, metrics))
    
    # Sort by score
    rankings.sort(key=lambda x: -x[1])
    
    best_state = rankings[0][0]
    best_score = rankings[0][1]
    
    # Natural state from structural affinity
    affinity_key = {
        "quantum": "quantum_affinity",
        "semiconductor": "classical_affinity",
        "photonic": "photonic_affinity",
    }.get(target_regime, "memory_affinity")
    
    natural_scores = [
        (idx, getattr(metrics, affinity_key))
        for idx, metrics in all_metrics.items()
    ]
    natural_scores.sort(key=lambda x: -x[1])
    natural_state = natural_scores[0][0]
    
    agreement = (best_state == natural_state)
    
    return RegimeStateRanking(
        target_regime=target_regime,
        rankings=rankings,
        best_state=best_state,
        best_score=best_score,
        natural_state=natural_state,
        agreement=agreement,
    )


# ─── 6. Visualization ───

def plot_structural_affinity_matrix(
    save_path: Optional[str] = None,
):
    """Plot the structural affinity of each octahedral state for each regime."""
    import matplotlib.pyplot as plt
    
    all_metrics = compute_all_structural_metrics()
    
    regimes = ["quantum", "classical", "memory", "photonic", "sensor"]
    affinity_keys = [
        "quantum_affinity", "classical_affinity", "memory_affinity",
        "photonic_affinity", "sensor_affinity"
    ]
    
    matrix = np.zeros((8, len(regimes)))
    for i in range(8):
        metrics = all_metrics[i]
        for j, key in enumerate(affinity_keys):
            matrix[i, j] = getattr(metrics, key)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Panel 1: Heatmap
    im = ax1.imshow(matrix.T, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)
    ax1.set_xticks(range(8))
    ax1.set_xticklabels([f"State {i}" for i in range(8)])
    ax1.set_yticks(range(len(regimes)))
    ax1.set_yticklabels(regimes)
    ax1.set_xlabel('Octahedral State')
    ax1.set_title('Structural Affinity Matrix\n(darker = more natural fit)')
    
    # Add text annotations
    for i in range(8):
        for j in range(len(regimes)):
            val = matrix[i, j]
            color = 'white' if val > 0.5 else 'black'
            ax1.text(i, j, f'{val:.2f}', ha='center', va='center', 
                    fontsize=8, color=color, fontweight='bold')
    
    plt.colorbar(im, ax=ax1, label='Affinity Score')
    
    # Panel 2: Eigenvalue visualization
    ax2.set_xlim(-0.5, 7.5)
    ax2.set_ylim(0, 1.1)
    ax2.set_xlabel('Octahedral State')
    ax2.set_ylabel('Eigenvalue')
    ax2.set_title('Eigenvalue Spectrum by State')
    
    for i in range(8):
        l1, l2, l3 = CANONICAL_EIGENVALUES[i]
        ax2.plot([i-0.2, i, i+0.2], [l1, l2, l3], 'ko-', markersize=8, linewidth=2)
        ax2.plot(i-0.2, l1, 's', color='#2E86AB', markersize=10)
        ax2.plot(i, l2, 'D', color='#F18F01', markersize=8)
        ax2.plot(i+0.2, l3, 'v', color='#C73E1D', markersize=8)
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor='#2E86AB',
               markersize=10, label='λ₁ (largest)'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#F18F01',
               markersize=8, label='λ₂'),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#C73E1D',
               markersize=8, label='λ₃ (smallest)'),
    ]
    ax2.legend(handles=legend_elements, fontsize=8, loc='upper right')
    
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


def plot_regime_rankings(
    rankings: Dict[str, RegimeStateRanking],
    save_path: Optional[str] = None,
):
    """Plot state rankings for each target regime."""
    import matplotlib.pyplot as plt
    
    regimes = list(rankings.keys())
    n_regimes = len(regimes)
    
    fig, axes = plt.subplots(1, n_regimes, figsize=(5*n_regimes, 5))
    
    if n_regimes == 1:
        axes = [axes]
    
    for ax, regime in zip(axes, regimes):
        ranking = rankings[regime]
        
        states = [r[0] for r in ranking.rankings]
        scores = [r[1] for r in ranking.rankings]
        
        colors = []
        for s in states:
            if s == ranking.natural_state and s == ranking.best_state:
                colors.append('#2E86AB')  # blue: both natural and best
            elif s == ranking.best_state:
                colors.append('#F18F01')  # orange: best but not natural
            elif s == ranking.natural_state:
                colors.append('#58A449')  # green: natural but not best
            else:
                colors.append('#CCCCCC')
        
        bars = ax.barh(range(8), scores, color=colors, edgecolor='black', linewidth=0.5)
        ax.set_yticks(range(8))
        ax.set_yticklabels([f"State {s}" for s in states])
        ax.set_xlabel('Regime Weight')
        ax.set_xlim(0, 1)
        ax.set_title(f'{regime.capitalize()} Regime\n' +
                    (f'Natural = Best: {"✓" if ranking.agreement else "✗"}'))
        
        # Add structural affinity stars
        for i, (state, score, metrics) in enumerate(ranking.rankings):
            affinity_key = {
                "quantum": "quantum_affinity",
                "semiconductor": "classical_affinity",
                "photonic": "photonic_affinity",
            }.get(regime, "memory_affinity")
            
            structural_score = getattr(metrics, affinity_key)
            ax.text(score + 0.02, i, f'★{structural_score:.2f}', 
                   fontsize=7, va='center', alpha=0.7)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ─── 7. Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("THE REVERSE PROBLEM")
    print("Target Regime → Optimal Octahedral State Design")
    print("=" * 70)
    
    # ── Part 1: Structural metrics for all states ──
    print("\n1. STRUCTURAL METRICS FOR ALL OCTAHEDRAL STATES")
    print("-" * 50)
    
    all_metrics = compute_all_structural_metrics()
    
    print(f"\n{'Idx':>4} {'λ₁,λ₂,λ₃':>20} {'Spread':>8} {'Degen':>8} "
          f"{'Planar':>8} {'Uniax':>8} {'Iso':>8} {'Natural Regime':>20}")
    print("-" * 95)
    
    for idx in range(8):
        m = all_metrics[idx]
        eig_str = f"({m.eigenvalues[0]:.3f},{m.eigenvalues[1]:.3f},{m.eigenvalues[2]:.3f})"
        print(f"{idx:>4} {eig_str:>20} {m.eigenvalue_spread:>8.3f} "
              f"{m.degeneracy_score:>8.3f} {m.planarity:>8.3f} "
              f"{m.uniaxiality:>8.3f} {m.isotropy:>8.3f} {m.natural_regime:>20}")
    
    # ── Part 2: Natural regime mapping ──
    print("\n\n2. STRUCTURAL REGIME AFFINITY MAP")
    print("-" * 50)
    
    affinity_map = compute_regime_affinity_map()
    
    for regime, scored_states in affinity_map.items():
        print(f"\n{regime.upper()}")
        for idx, score in scored_states[:3]:
            print(f"  state {idx}: affinity={score:.3f}")

    print("\nDemo complete.")

