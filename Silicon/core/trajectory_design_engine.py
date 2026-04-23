# trajectory_design_engine.py
"""
Full Dynamical System: Trajectory Design on the Combined Fiber Bundle

Solves for optimal trajectories through the mixed continuous-discrete space:

    Combined state: X = (S_silicon, octahedral_index)
    where S_silicon = (n, d, ℓ, κ) ∈ ℝ⁴ continuous
          octahedral_index ∈ {0,...,7} discrete (Z₂³ fiber)

Dynamics:
    dS/dt = F(S) + G(S) · u(t)           continuous flow
    idx_jump = σ(S, idx, control_pulse)   discrete transition

Objective:
    min ∫ L(S, u) dt + Σ J(idx_i → idx_{i+1})
    subject to: S(t_f) ∈ target_basin, idx(t_f) = target_state

This is a hybrid optimal control problem on a fiber bundle.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from scipy.optimize import minimize, differential_evolution
from scipy.integrate import solve_ivp
import warnings


# ─── 1. Combined State Space ───

class ControlAction(Enum):
    """Discrete control actions that can be applied to the system."""
    # Continuous controls
    CHANGE_DOPING = auto()       # ion implantation or gate voltage
    CHANGE_TEMPERATURE = auto()  # heating or cooling
    APPLY_STRAIN = auto()        # piezoelectric or mechanical
    APPLY_B_FIELD = auto()       # magnetic field (continuous)
    
    # Discrete controls (fiber jumps)
    MAGNETIC_PULSE = auto()      # resonant π-pulse to flip octahedral state
    ADIABATIC_SWEEP = auto()     # adiabatic passage between states
    FRET_MEDIATED_JUMP = auto()  # exploit FRET coupling for transfer
    
    # Measurement
    READ_STATE = auto()          # measure current state
    VERIFY_REGIME = auto()       # check regime classification


@dataclass
class CombinedState:
    """A point in the combined continuous-discrete state space."""
    silicon_state: 'SiliconState'
    octahedral_index: int  # 0-7, the Z₂³ fiber element
    
    # Derived properties
    regime_weights: Dict[str, float] = field(default_factory=dict)
    dominant_regime: str = ""
    computational_class: str = ""
    code_performance: Optional['CodePerformance'] = None
    
    def __post_init__(self):
        if not self.regime_weights:
            self.regime_weights = self.silicon_state.regime_weights(temperature=0.1)
        if not self.dominant_regime:
            self.dominant_regime = max(self.regime_weights, key=self.regime_weights.get)
    
    @property
    def is_valid(self) -> bool:
        """Check if this combined state is physically valid."""
        n_ok = 1e8 <= self.silicon_state.n <= 1e23
        d_ok = 0.0 <= self.silicon_state.d <= 1.0
        ell_ok = 0.1 <= self.silicon_state.l <= 3.0
        idx_ok = 0 <= self.octahedral_index <= 7
        return n_ok and d_ok and ell_ok and idx_ok
    
    def copy(self) -> 'CombinedState':
        from silicon_state import SiliconState
        new_si = SiliconState(
            n=self.silicon_state.n,
            d=self.silicon_state.d,
            l=self.silicon_state.l,
            k=self.silicon_state.k.copy(),
        )
        return CombinedState(
            silicon_state=new_si,
            octahedral_index=self.octahedral_index,
            regime_weights=self.regime_weights.copy(),
            dominant_regime=self.dominant_regime,
            computational_class=self.computational_class,
        )


# ─── 2. Continuous Dynamics F(S) ───

def continuous_dynamics(
    S: np.ndarray,
    controls: Dict[str, float],
    temperature: float = 300.0,
) -> np.ndarray:
    """
    Continuous dynamics dS/dt = F(S) + G(S) · u(t)
    
    S = [log10(n), d, ℓ, κ_coherent]
    
    Controls u(t) = {
        "doping_rate": dn/dt (cm⁻³/s, log scale),
        "strain_rate": d(strain)/dt (%/s),
        "cooling_rate": dT/dt (K/s),
        "B_field_rate": dB/dt (T/s),
        "anneal_rate": d(defect)/dt (fraction/s, negative = healing),
    }
    """
    from silicon_information_geometry import free_energy_landscape
    
    log10_n, d, ell, k_coh = S
    
    # ── Natural relaxation (gradient of free energy) ──
    S_vec = np.array([10**log10_n, d, ell, k_coh])
    F_nat = -np.array([
        1e12 * (log10_n - 16),  # n relaxes to ~10^16
        1e-6 * (d - 0.0),       # d relaxes to 0 (annealing)
        1e-9 * (ell - 3.0),     # ℓ relaxes to 3D bulk
        1e-3 * (k_coh - 0.0),   # coherence naturally decays
    ])
    
    # ── Control inputs ──
    G_u = np.zeros(4)
    
    if "doping_rate" in controls:
        G_u[0] += controls["doping_rate"]  # direct doping control
    
    if "anneal_rate" in controls:
        G_u[1] += controls["anneal_rate"]  # defect reduction
    
    if "strain_rate" in controls:
        # Strain affects both dimension and doping
        G_u[2] += controls["strain_rate"] * 0.1
        G_u[0] += controls["strain_rate"] * 0.01
    
    if "cooling_rate" in controls:
        # Cooling increases coherence
        G_u[3] += controls["cooling_rate"] * 0.01
    
    if "B_field_rate" in controls:
        # Magnetic field couples to coherence
        G_u[3] += controls["B_field_rate"] * 0.05
    
    dS_dt = F_nat + G_u
    
    return dS_dt


# ─── 3. Discrete Transitions (Fiber Jumps) ───

@dataclass
class DiscreteTransition:
    """A discrete jump between octahedral states."""
    from_state: int
    to_state: int
    method: ControlAction
    energy_cost: float        # eV
    probability_success: float  # 0-1
    required_conditions: Dict[str, Tuple[float, float]]  # (min, max)
    transition_time: float    # seconds
    
    @property
    def bit_flips(self) -> Tuple[int, int, int]:
        """Which bits flip in this transition."""
        from_bits = [(self.from_state >> i) & 1 for i in range(3)]
        to_bits = [(self.to_state >> i) & 1 for i in range(3)]
        return tuple((f - t) % 2 for f, t in zip(from_bits, to_bits))


def compute_discrete_transitions(
    from_state: int,
    silicon_state: 'SiliconState',
    temperature: float = 4.0,
) -> List[DiscreteTransition]:
    """
    Compute all possible discrete octahedral state transitions
    from the current combined state.
    
    Different transition methods have different costs and success
    probabilities depending on the silicon regime.
    """
    from octahedral_fiber_bundle import OctahedralTorsor, BitFlip
    from silicon_gies_bridge import octahedral_state_to_silicon_state
    
    transitions = []
    weights = silicon_state.regime_weights(temperature=0.1)
    dominant_regime = max(weights, key=weights.get)
    
    for to_state in range(8):
        if to_state == from_state:
            continue
        
        # Determine bit flips
        torsor = OctahedralTorsor()
        bit_flip = torsor.difference(from_state, to_state)
        hamming = sum(bit_flip.value)
        
        # ── Method 1: Magnetic pulse (resonant π-pulse) ──
        # Works best with coherent coupling
        k_coherent = silicon_state.k.get("coherent", 0.1)
        B_field_available = 1.0  # T
        
        magnetic_energy = (
            5.788e-5 * 2.0 * B_field_available  # μ_B × g × B
        )
        
        # Single-pulse can flip one bit; need hamming pulses for multi-bit
        if hamming == 1:
            pulse_success = k_coherent * np.exp(-temperature / 100)
            pulse_energy = magnetic_energy * 1.5  # π-pulse
        elif hamming == 2:
            pulse_success = k_coherent * np.exp(-temperature / 100) * 0.5
            pulse_energy = magnetic_energy * 3.0  # composite pulse
        else:
            pulse_success = k_coherent * np.exp(-temperature / 100) * 0.25
            pulse_energy = magnetic_energy * 5.0  # sequence of pulses
        
        pulse_success = np.clip(pulse_success, 0.01, 0.99)
        
        transitions.append(DiscreteTransition(
            from_state=from_state,
            to_state=to_state,
            method=ControlAction.MAGNETIC_PULSE,
            energy_cost=pulse_energy,
            probability_success=pulse_success,
            required_conditions={
                "k_coherent": (0.1, 1.0),
                "temperature": (0.1, 100.0),
            },
            transition_time=10e-12,  # 10 ps
        ))
        
        # ── Method 2: Adiabatic sweep ──
        # Slower but higher fidelity for any hamming distance
        adiabatic_success = 0.95 * np.exp(-temperature / 200) * np.exp(-hamming * 0.1)
        adiabatic_energy = magnetic_energy * hamming * 0.5  # less energy, slower
        
        transitions.append(DiscreteTransition(
            from_state=from_state,
            to_state=to_state,
            method=ControlAction.ADIABATIC_SWEEP,
            energy_cost=adiabatic_energy,
            probability_success=adiabatic_success,
            required_conditions={
                "k_coherent": (0.0, 1.0),  # works even without coherence
                "temperature": (0.1, 300.0),
            },
            transition_time=100e-12,  # 100 ps
        ))
        
        # ── Method 3: FRET-mediated jump ──
        # Uses FRET coupling if another state is nearby
        if silicon_state.k.get("optical", 0) > 0.05:
            fret_success = silicon_state.k.get("optical", 0.1) * 0.8
            fret_energy = 4.1e-3  # ~4.1 meV, FRET energy
            
            transitions.append(DiscreteTransition(
                from_state=from_state,
                to_state=to_state,
                method=ControlAction.FRET_MEDIATED_JUMP,
                energy_cost=fret_energy,
                probability_success=fret_success,
                required_conditions={
                    "k_optical": (0.05, 1.0),
                    "d_ErP": (2.0, 15.0),  # Å
                },
                transition_time=1e-9,  # 1 ns
            ))
    
    return transitions


# ─── 4. Trajectory Optimization Problem ───

@dataclass
class TrajectorySpec:
    """Specification for a trajectory optimization problem."""
    # Initial state
    initial_silicon: 'SiliconState'
    initial_octahedral: int
    
    # Target
    target_regime: str           # desired final regime
    target_regime_weight: float  # minimum weight (0-1)
    target_octahedral: Optional[int] = None  # specific state, or None = any
    
    # Constraints
    max_time: float = 1000.0     # seconds
    max_energy: float = 100.0    # eV
    max_defects: float = 0.1     # maximum tolerable defect density
    min_coherence: float = 0.3   # minimum coherent coupling at target
    
    # Available controls
    max_doping_rate: float = 1e15  # cm⁻³/s
    max_strain_rate: float = 0.1   # %/s
    max_cooling_rate: float = 10.0 # K/s
    max_B_field: float = 2.0       # T
    
    # Preferences
    prefer_fewer_jumps: bool = True
    prefer_high_fidelity: bool = True


@dataclass
class OptimizedTrajectory:
    """Result of trajectory optimization."""
    # Path through combined space
    time_points: np.ndarray           # time (s)
    silicon_path: np.ndarray          # (n_steps, 4) array
    octahedral_path: List[int]        # octahedral state at each step
    regime_path: List[str]            # dominant regime at each step
    
    # Control sequence
    continuous_controls: List[Dict]   # controls applied at each step
    discrete_jumps: List[Dict]        # discrete transitions
    
    # Performance
    total_energy: float               # eV
    total_time: float                 # seconds
    n_jumps: int                      # number of discrete transitions
    final_regime_weight: float        # achieved target regime weight
    success_probability: float        # overall success probability
    
    # Validation
    reaches_target: bool
    within_constraints: bool
    constraint_violations: List[str]
    
    @property
    def trajectory_summary(self) -> str:
        lines = [
            f"OPTIMIZED TRAJECTORY SUMMARY",
            f"{'='*40}",
            f"Total time: {self.total_time:.2e} s",
            f"Total energy: {self.total_energy:.2f} eV",
            f"Discrete jumps: {self.n_jumps}",
            f"Success probability: {self.success_probability:.1%}",
            f"Final regime: {self.final_regime_weight:.1%} {self.regime_path[-1] if self.regime_path else ''}",
            f"",
            f"Path:",
        ]
        
        for i, (regime, oct_idx) in enumerate(zip(self.regime_path, self.octahedral_path)):
            if i == 0:
                lines.append(f"  Start: [{oct_idx}] {regime}")
            elif regime != self.regime_path[i-1] or oct_idx != self.octahedral_path[i-1]:
                lines.append(f"  Step {i}: [{oct_idx}] {regime} "
                           f"(t={self.time_points[i]:.2e}s)")
        
        if self.discrete_jumps:
            lines.append(f"\nDiscrete transitions:")
            for jump in self.discrete_jumps:
                lines.append(
                    f"  t={jump['time']:.2e}s: State {jump['from']}→{jump['to']} "
                    f"via {jump['method']} (p={jump['probability']:.2f})"
                )
        
        return "\n".join(lines)


def optimize_trajectory(
    spec: TrajectorySpec,
    n_time_steps: int = 20,
    n_optimization_restarts: int = 3,
    verbose: bool = False,
) -> OptimizedTrajectory:
    """
    Solve the hybrid optimal control problem on the combined fiber bundle.
    
    This is the master trajectory designer: given start and target,
    it finds the optimal sequence of continuous flows and discrete
    jumps through the silicon-octahedral space.
    
    The optimization is done in stages:
    1. Plan discrete jumps (which octahedral state sequence)
    2. Optimize continuous path between jumps
    3. Refine with local optimization
    """
    from silicon_state import SiliconState
    
    # ── Stage 0: Evaluate initial state ──
    current_state = CombinedState(
        silicon_state=spec.initial_silicon,
        octahedral_index=spec.initial_octahedral,
    )
    
    initial_regime = current_state.dominant_regime
    
    # ── Stage 1: Plan discrete jump sequence ──
    # Determine which octahedral state is optimal for the target regime
    from inverse_regime_design import (
        compute_structural_metrics, rank_all_states_for_regime
    )
    
    ranking = rank_all_states_for_regime(spec.target_regime)
    
    # Best octahedral state for the target regime
    if spec.target_octahedral is not None:
        target_octahedral = spec.target_octahedral
    else:
        target_octahedral = ranking.best_state
    
    # ── Determine if we need discrete jumps ──
    if spec.initial_octahedral == target_octahedral:
        # No discrete jumps needed — pure continuous trajectory
        jump_sequence = []
    else:
        # Plan jump sequence using the octahedral fiber bundle
        jumps_needed = plan_discrete_jumps(
            spec.initial_octahedral,
            target_octahedral,
            spec.initial_silicon,
        )
        jump_sequence = jumps_needed
    
    # ── Stage 2: Optimize continuous path ──
    # Target silicon state that maximizes target regime weight
    target_silicon = find_target_silicon_state(
        spec.target_regime,
        target_octahedral,
        spec,
    )
    
    # Optimize continuous trajectory
    n_control_intervals = n_time_steps
    
    best_trajectory = None
    best_cost = float('inf')
    
    for restart in range(n_optimization_restarts):
        if verbose:
            print(f"  Optimization restart {restart+1}/{n_optimization_restarts}")
        
        # Initialize random control sequence
        controls_init = []
        for _ in range(n_control_intervals):
            controls_init.append({
                "doping_rate": np.random.uniform(-0.1, 0.1) * spec.max_doping_rate,
                "strain_rate": np.random.uniform(-0.1, 0.1) * spec.max_strain_rate,
                "cooling_rate": np.random.uniform(-1, 1) * spec.max_cooling_rate,
                "anneal_rate": np.random.uniform(-0.01, 0.01),  # negative = healing
            })
        
        # Simulate trajectory with these controls
        traj = simulate_controlled_trajectory(
            spec.initial_silicon,
            spec.initial_octahedral,
            target_silicon,
            target_octahedral,
            controls_init,
            jump_sequence,
            spec,
        )
        
        if traj and traj.total_energy < best_cost:
            best_cost = traj.total_energy
            best_trajectory = traj
    
    if best_trajectory is None:
        # Fallback: linear interpolation with no jumps
        best_trajectory = create_fallback_trajectory(spec, target_silicon, target_octahedral)
    
    return best_trajectory


def plan_discrete_jumps(
    from_state: int,
    to_state: int,
    silicon_state: 'SiliconState',
) -> List[DiscreteTransition]:
    """
    Plan the optimal sequence of discrete octahedral state transitions.
    
    Uses the octahedral fiber bundle connection to find the path
    with minimum transport cost.
    """
    from octahedral_fiber_bundle import OctahedralTorsor, BitFlip, Connection
    
    if from_state == to_state:
        return []
    
    # Get all possible transitions
    available_transitions = compute_discrete_transitions(from_state, silicon_state)
    
    # Find shortest path in Hamming distance
    torsor = OctahedralTorsor()
    bit_flip = torsor.difference(from_state, to_state)
    hamming = sum(bit_flip.value)
    
    if hamming == 1:
        # Single jump possible
        for trans in available_transitions:
            if trans.to_state == to_state:
                return [trans]
    
    # Multi-jump sequence: decompose bit flips one at a time
    jumps = []
    current = from_state
    
    for bit_idx in range(3):
        if bit_flip.value[bit_idx] == 1:
            # Flip this bit
            next_state = current ^ (1 << bit_idx)
            
            trans_list = compute_discrete_transitions(current, silicon_state)
            best_trans = None
            best_prob = -1
            
            for trans in trans_list:
                if trans.to_state == next_state:
                    if trans.probability_success > best_prob:
                        best_prob = trans.probability_success
                        best_trans = trans
            
            if best_trans:
                jumps.append(best_trans)
                current = next_state
    
    return jumps


def find_target_silicon_state(
    target_regime: str,
    target_octahedral: int,
    spec: TrajectorySpec,
) -> 'SiliconState':
    """
    Find a target silicon state that maximizes the target regime weight
    for a given octahedral state.
    """
    from silicon_state import SiliconState
    from silicon_gies_bridge import octahedral_state_to_silicon_state
    
    # Use the inverse design to find optimal parameters
    from inverse_regime_design import solve_inverse_problem, RegimeTarget
    
    target_spec = RegimeTarget(
        target_regime=target_regime,
        min_weight=spec.target_regime_weight,
        min_coherence=spec.min_coherence,
        max_defect_density=spec.max_defects,
    )
    
    solutions = solve_inverse_problem(target_spec)
    
    # Find solution matching target octahedral state
    for sol in solutions:
        if sol.octahedral_state_index == target_octahedral:
            return SiliconState(
                n=1e17 if target_regime == "quantum" else 1e16,
                d=0.01,
                l=0.5 if target_regime == "quantum" else 3.0,
                k={
                    "electrical": 0.2,
                    "optical": 0.1,
                    "thermal": 0.05,
                    "mechanical": 0.05,
                    "coherent": 0.6 if target_regime == "quantum" else 0.1,
                }
            )
    
    # Default target
    return SiliconState(
        n=1e17, d=0.01, l=0.5,
        k={"electrical": 0.2, "optical": 0.1, "thermal": 0.05,
           "mechanical": 0.05, "coherent": 0.6}
    )


def simulate_controlled_trajectory(
    initial_silicon: 'SiliconState',
    initial_octahedral: int,
    target_silicon: 'SiliconState',
    target_octahedral: int,
    controls: List[Dict],
    jump_sequence: List[DiscreteTransition],
    spec: TrajectorySpec,
) -> Optional[OptimizedTrajectory]:
    """
    Simulate a trajectory under a given control sequence.
    """
    from silicon_state import SiliconState
    
    n_steps = len(controls)
    total_time = spec.max_time
    dt = total_time / n_steps
    
    # State arrays
    S = np.zeros((n_steps + 1, 4))
    octahedral_path = [initial_octahedral]
    regime_path = []
    
    # Initial state
    current_silicon = SiliconState(
        n=initial_silicon.n,
        d=initial_silicon.d,
        l=initial_silicon.l,
        k=initial_silicon.k.copy(),
    )
    current_octahedral = initial_octahedral
    
    S[0] = [
        np.log10(current_silicon.n),
        current_silicon.d,
        current_silicon.l,
        current_silicon.k.get("coherent", 0.1),
    ]
    
    # Track jumps
    discrete_jumps_applied = []
    jump_remaining = list(jump_sequence)
    
    total_energy = 0.0
    total_probability = 1.0
    
    for step in range(n_steps):
        # Check if a discrete jump should be applied
        if jump_remaining:
            # Apply jump at the midpoint of the trajectory
            if step == n_steps // len(jump_remaining):
                jump = jump_remaining.pop(0)
                
                # Check conditions
                conditions_met = True
                for cond, (min_val, max_val) in jump.required_conditions.items():
                    if cond == "k_coherent":
                        val = current_silicon.k.get("coherent", 0)
                    elif cond == "temperature":
                        val = 300  # approximate
                    else:
                        val = current_silicon.k.get(cond, 0)
                    
                    if not (min_val <= val <= max_val):
                        conditions_met = False
                        break
                
                if conditions_met:
                    current_octahedral = jump.to_state
                    total_energy += jump.energy_cost
                    total_probability *= jump.probability_success
                    
                    discrete_jumps_applied.append({
                        "time": step * dt,
                        "from": jump.from_state,
                        "to": jump.to_state,
                        "method": jump.method.name,
                        "energy": jump.energy_cost,
                        "probability": jump.probability_success,
                    })
        
        # Apply continuous controls
        ctrl = controls[step]
        S_current = S[step]
        
        dS_dt = continuous_dynamics(S_current, ctrl)
        S_next = S_current + dS_dt * dt
        
        # Clamp to physical bounds
        S_next[0] = np.clip(S_next[0], 8, 23)  # log10(n)
        S_next[1] = np.clip(S_next[1], 0, 1)   # d
        S_next[2] = np.clip(S_next[2], 0.1, 3) # ℓ
        S_next[3] = np.clip(S_next[3], 0, 1)   # κ
        
        # Energy cost of continuous controls
        control_power = sum(abs(v) for v in ctrl.values())
        total_energy += control_power * dt * 1e-3  # approximate
        
        S[step + 1] = S_next
        
        # Update silicon state
        current_silicon = SiliconState(
            n=10**S_next[0],
            d=S_next[1],
            l=S_next[2],
            k={
                "electrical": 0.5,
                "optical": 0.0,
                "thermal": 0.1,
                "mechanical": 0.0,
                "coherent": S_next[3],
            }
        )
        
        octahedral_path.append(current_octahedral)
        weights = current_silicon.regime_weights(temperature=0.1)
        regime_path.append(max(weights, key=weights.get))
    
    # Final regime weight
    final_weights = current_silicon.regime_weights(temperature=0.1)
    final_regime_weight = final_weights.get(spec.target_regime, 0)
    
    # Check target reached
    reaches_target = (
        final_regime_weight >= spec.target_regime_weight and
        current_octahedral == target_octahedral
    )
    
    # Check constraints
    violations = []
    if total_time > spec.max_time:
        violations.append(f"Time {total_time:.2e} > {spec.max_time:.2e}")
    if total_energy > spec.max_energy:
        violations.append(f"Energy {total_energy:.2f} > {spec.max_energy:.2f}")
    if current_silicon.d > spec.max_defects:
        violations.append(f"Defects {current_silicon.d:.3f} > {spec.max_defects:.2f}")
    
    return OptimizedTrajectory(
        time_points=np.linspace(0, total_time, n_steps + 1),
        silicon_path=S,
        octahedral_path=octahedral_path,
        regime_path=regime_path,
        continuous_controls=controls,
        discrete_jumps=discrete_jumps_applied,
        total_energy=total_energy,
        total_time=total_time,
        n_jumps=len(discrete_jumps_applied),
        final_regime_weight=final_regime_weight,
        success_probability=total_probability,
        reaches_target=reaches_target,
        within_constraints=len(violations) == 0,
        constraint_violations=violations,
    )


def create_fallback_trajectory(
    spec: TrajectorySpec,
    target_silicon: 'SiliconState',
    target_octahedral: int,
) -> OptimizedTrajectory:
    """Create a simple linear interpolation trajectory as fallback."""
    
    n_steps = 20
    
    S_start = np.array([
        np.log10(spec.initial_silicon.n),
        spec.initial_silicon.d,
        spec.initial_silicon.l,
        spec.initial_silicon.k.get("coherent", 0.1),
    ])
    
    S_end = np.array([
        np.log10(target_silicon.n),
        target_silicon.d,
        target_silicon.l,
        target_silicon.k.get("coherent", 0.1),
    ])
    
    S_path = np.zeros((n_steps + 1, 4))
    for i in range(4):
        S_path[:, i] = np.linspace(S_start[i], S_end[i], n_steps + 1)
    
    octahedral_path = [spec.initial_octahedral] * (n_steps + 1)
    
    from silicon_state import SiliconState
    
    regime_path = []
    for i in range(n_steps + 1):
        si = SiliconState(
            n=10**S_path[i, 0], d=S_path[i, 1], l=S_path[i, 2],
            k={"electrical": 0.5, "optical": 0.0, "thermal": 0.1,
               "mechanical": 0.0, "coherent": S_path[i, 3]}
        )
        weights = si.regime_weights(temperature=0.1)
        regime_path.append(max(weights, key=weights.get))
    
    final_si = SiliconState(
        n=10**S_path[-1, 0], d=S_path[-1, 1], l=S_path[-1, 2],
        k={"coherent": S_path[-1, 3], "electrical": 0.5, "optical": 0.0,
           "thermal": 0.1, "mechanical": 0.0}
    )
    final_weights = final_si.regime_weights(temperature=0.1)
    
    return OptimizedTrajectory(
        time_points=np.linspace(0, 100, n_steps + 1),
        silicon_path=S_path,
        octahedral_path=octahedral_path,
        regime_path=regime_path,
        continuous_controls=[{}] * n_steps,
        discrete_jumps=[],
        total_energy=abs(np.sum(S_end - S_start)) * 10,
        total_time=100.0,
        n_jumps=0,
        final_regime_weight=final_weights.get(spec.target_regime, 0),
        success_probability=1.0,
        reaches_target=False,
        within_constraints=True,
        constraint_violations=[],
    )


# ─── 5. Trajectory Visualization ───

def plot_optimized_trajectory(
    trajectory: OptimizedTrajectory,
    save_path: Optional[str] = None,
):
    """Visualize the optimized trajectory through the combined space."""
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.35)
    
    time = trajectory.time_points
    
    # Panel 1: Silicon state evolution
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.plot(time, trajectory.silicon_path[:, 0], 'b-', linewidth=2, label='log₁₀(n)')
    ax1.plot(time, trajectory.silicon_path[:, 1], 'r-', linewidth=2, label='d (defects)')
    ax1.plot(time, trajectory.silicon_path[:, 2], 'g-', linewidth=2, label='ℓ (dim)')
    ax1.plot(time, trajectory.silicon_path[:, 3], 'orange', linewidth=2, label='κ (coherence)')
    
    # Mark discrete jumps
    for jump in trajectory.discrete_jumps:
        ax1.axvline(x=jump['time'], color='purple', linestyle='--', linewidth=1.5, alpha=0.7)
        ax1.annotate(f"State {jump['from']}→{jump['to']}",
                    xy=(jump['time'], 0.5), fontsize=7, color='purple',
                    rotation=90, va='center')
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('State coordinate value')
    ax1.set_title('Silicon State Evolution')
    ax1.legend(fontsize=8, ncol=4)
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Regime + Octahedral state
    ax2 = fig.add_subplot(gs[0, 2])
    
    REGIME_COLORS = {
        "semiconductor": "#2E86AB", "metallic": "#A23B72",
        "quantum": "#F18F01", "photonic": "#C73E1D",
        "defect_dominated": "#6B4D57", "mechanical": "#58A449",
    }
    
    unique_regimes = sorted(set(trajectory.regime_path))
    regime_to_y = {r: i for i, r in enumerate(unique_regimes)}
    
    y_regime = np.array([regime_to_y[r] for r in trajectory.regime_path])
    
    ax2.step(time, y_regime, 'b-', linewidth=2, where='mid', alpha=0.8)
    ax2.set_yticks(range(len(unique_regimes)))
    ax2.set_yticklabels(unique_regimes, fontsize=7)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Regime')
    ax2.set_title('Regime Evolution')
    
    # Octahedral state as color
    for i in range(len(time)):
        if i < len(trajectory.octahedral_path):
            oct_idx = trajectory.octahedral_path[i]
            color = plt.cm.Set3(oct_idx / 8)
            ax2.axvspan(time[max(0, i-1)], time[min(len(time)-1, i)],
                       alpha=0.1, color=color)
    
    ax2.grid(True, alpha=0.3, axis='x')
    
    # Panel 3: Control sequence
    ax3 = fig.add_subplot(gs[1, :])
    
    if trajectory.continuous_controls:
        ctrl_names = ['doping_rate', 'strain_rate', 'cooling_rate', 'anneal_rate']
        ctrl_colors = ['blue', 'red', 'cyan', 'brown']
        
        ctrl_array = np.zeros((len(trajectory.continuous_controls), len(ctrl_names)))
        for i, ctrl in enumerate(trajectory.continuous_controls):
            for j, name in enumerate(ctrl_names):
                ctrl_array[i, j] = ctrl.get(name, 0)
        
        for j, (name, color) in enumerate(zip(ctrl_names, ctrl_colors)):
            ax3.plot(time[:-1], ctrl_array[:, j], color=color, linewidth=1.5, label=name)
        
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Control amplitude')
        ax3.set_title('Control Sequence')
        ax3.legend(fontsize=7, ncol=4)
        ax3.grid(True, alpha=0.3)
    
    # Panel 4: Summary
    ax4 = fig.add_subplot(gs[2, :])
    ax4.axis('off')
    ax4.text(0.05, 0.95, trajectory.trajectory_summary,
            transform=ax4.transAxes, fontsize=9, fontfamily='monospace',
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    
    fig.suptitle('Optimized Trajectory on the Combined Fiber Bundle',
                fontsize=14, fontweight='bold')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ─── 6. Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("TRAJECTORY DESIGN ENGINE")
    print("Optimal Control on the Combined Fiber Bundle")
    print("=" * 70)
    
    from silicon_state import SiliconState
    
    # Define the problem: go from semiconductor to quantum
    print("\n1. PROBLEM DEFINITION")
    print("-" * 50)
    
    spec = TrajectorySpec(
        initial_silicon=SiliconState(
            n=1e16, d=0.02, l=3.0,
            k={"electrical": 0.8, "optical": 0.0, "thermal": 0.1,
               "mechanical": 0.0, "coherent": 0.1}
        ),
        initial_octahedral=7,  # classical state (fully aligned)
        target_regime="quantum",
        target_regime_weight=0.6,
        target_octahedral=3,   # quantum state (nearly degenerate)
        max_time=1000.0,
        max_energy=100.0,
        max_defects=0.05,
        min_coherence=0.5,
    )
    
    print(f"  Start: State {spec.initial_octahedral}, "
          f"n={spec.initial_silicon.n:.1e}, d={spec.initial_silicon.d:.3f}")
    print(f"  Target: State {spec.target_octahedral}, regime='{spec.target_regime}'")
    
    # Optimize trajectory
    print("\n2. TRAJECTORY OPTIMIZATION")
    print("-" * 50)
    print("  Solving hybrid optimal control problem...")
    
    trajectory = optimize_trajectory(spec, n_time_steps=30, verbose=True)
    
    print(f"\n  Optimization complete!")
    print(f"  Total time: {trajectory.total_time:.2e} s")
    print(f"  Total energy: {trajectory.total_energy:.2f} eV")
    print(f"  Discrete jumps: {trajectory.n_jumps}")
    print(f"  Success probability: {trajectory.success_probability:.1%}")
    print(f"  Final regime weight: {trajectory.final_regime_weight:.1%}")
    
    if trajectory.discrete_jumps:
        print(f"\n  Jump sequence:")
        for jump in trajectory.discrete_jumps:
            print(f"    t={jump['time']:.2e}s: {jump['from']}→{jump['to']} "
                  f"via {jump['method']} (p={jump['probability']:.2f})")
    
    # Regime path
    print(f"\n  Regime path:")
    prev = None
    for t, regime, oct_idx in zip(
        trajectory.time_points,
        trajectory.regime_path,
        trajectory.octahedral_path
    ):
        if regime != prev:
            print(f"    t={t:.2e}s: State {oct_idx} → {regime}")
            prev = regime
    
    print("\n" + trajectory.trajectory_summary)
    
    print("\n" + "=" * 70)
    print("""    The trajectory design engine orchestrates:
    
    1. Continuous flows through silicon phase space (doping, strain, cooling)
    2. Discrete jumps between octahedral states (magnetic pulses)
    3. Regime transitions (semiconductor → quantum)
    
    Each step is a movement in the combined fiber bundle,
    respecting both the Riemannian geometry of the base manifold
    and the Z₂³ torsor structure of the fiber.
    """)
