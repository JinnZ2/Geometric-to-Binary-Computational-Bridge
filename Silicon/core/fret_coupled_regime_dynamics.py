# fret_coupled_regime_dynamics.py
"""
Cross-State Entanglement via FRET Coupling:
Coupled Dynamical Systems on the Silicon Manifold

Implements the regime-heterogeneous coupled dynamics:

    dS₁/dt = F₁(S₁) + C₁₂(S₁, S₂)
    dS₂/dt = F₂(S₂) + C₂₁(S₂, S₁)

where F₁ and F₂ are DIFFERENT vector fields because the states
inhabit different computational regimes, and C is the FRET-mediated
coupling that bridges between basins of attraction.

Novel phenomena:
- Regime locking: both states synchronize to a shared intermediate
- Regime oscillation: periodic switching between regimes
- Regime separation: coupling drives states apart
- FRET-induced phase transitions: coupling flips a state's regime
- Coherence transfer: quantum coherence leaks across the bridge
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Callable
from dataclasses import dataclass, field
from scipy.integrate import solve_ivp
from enum import Enum, auto
import warnings


# ─── Physical constants ───

K_B = 8.617333262145e-5   # eV/K
HBAR = 6.582119569e-16    # eV·s
PHI = 1.618033988749895
R_0_FRET = 15.0            # Å, Förster radius
DELTA_E_TRANS = 4.1e-3     # eV, transition energy (~4.1 meV)


# ─── 1. Single-State Vector Field F(S) ───

def single_state_vector_field(
    S: np.ndarray,           # [n, d, ℓ, κ_eff]
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
) -> np.ndarray:
    """
    The intrinsic vector field F(S) for a single silicon state.
    
    This is the relaxation dynamics that pulls the state toward
    its local free energy minimum (attractor basin).
    
    F(S) = -∇_S F_free(S) + noise(S)
    
    Returns dS/dt for each coordinate.
    """
    
    from silicon_information_geometry import free_energy_landscape
    
    n, d, ell, k_eff = S
    
    # ── Gradient of free energy (deterministic part) ──
    # Compute via finite differences
    h = 1e-4
    scales = np.array([max(n * h, 1e8), h, h, h])
    
    F0 = free_energy_landscape(S, temperature, k_dft, strain_pct)
    
    grad_F = np.zeros(4)
    for i in range(4):
        S_fwd = S.copy()
        S_fwd[i] += scales[i]
        F_fwd = free_energy_landscape(S_fwd, temperature, k_dft, strain_pct)
        
        S_bwd = S.copy()
        S_bwd[i] -= scales[i]
        F_bwd = free_energy_landscape(S_bwd, temperature, k_dft, strain_pct)
        
        grad_F[i] = (F_fwd - F_bwd) / (2 * scales[i])
    
    # ── Mobility matrix (regime-dependent relaxation rates) ──
    # Different coordinates relax at different speeds depending on regime
    
    # Carrier density relaxation (fast: electronic)
    gamma_n = 1e12  # Hz, ~picosecond electronic relaxation
    
    # Defect relaxation (slow: atomic diffusion)
    # Arrhenius: gamma_d ∝ exp(-E_a/kT)
    E_a_defect = 0.5  # eV, migration barrier
    gamma_d = 1e6 * np.exp(-E_a_defect / (K_B * temperature))
    
    # Dimensional relaxation (very slow: requires structural change)
    gamma_ell = 1e-3  # Hz, essentially frozen
    
    # Coupling relaxation (intermediate: phonon-mediated)
    gamma_k = 1e9  # Hz
    
    mobility = np.array([gamma_n, gamma_d, gamma_ell, gamma_k])
    
    # ── Noise terms (fluctuation-dissipation) ──
    # σ_i = sqrt(2 * k_B T * gamma_i)
    noise_amplitude = np.sqrt(2 * K_B * temperature * mobility)
    noise = np.random.normal(0, 1, 4) * noise_amplitude * 1e-10
    
    # ── Conservative + dissipative + noise ──
    dS_dt = -mobility * grad_F + noise
    
    # ── Hard constraints ──
    # Prevent unphysical values
    if n < 1e8 and dS_dt[0] < 0:
        dS_dt[0] = max(dS_dt[0], 0)  # don't go below intrinsic carrier density
    if d < 0 and dS_dt[1] < 0:
        dS_dt[1] = max(dS_dt[1], 0)
    if ell < 0.1 and dS_dt[2] < 0:
        dS_dt[2] = max(dS_dt[2], 0)
    if ell > 3.0 and dS_dt[2] > 0:
        dS_dt[2] = min(dS_dt[2], 0)
    if k_eff < 0 and dS_dt[3] < 0:
        dS_dt[3] = max(dS_dt[3], 0)
    if k_eff > 1 and dS_dt[3] > 0:
        dS_dt[3] = min(dS_dt[3], 0)
    
    return dS_dt


# ─── 2. FRET Coupling Term ───

def fret_coupling_strength(
    d_ang: float,
    orientation_factor: float = 1.0,
    R_0: float = R_0_FRET,
    delta_E: float = DELTA_E_TRANS,
) -> float:
    """
    FRET coupling strength between two Er-P sites.
    
    V_FRET = ΔE × κ² × (R₀/d)⁶
    
    where κ² is the dipole orientation factor.
    """
    if d_ang <= 0:
        return 0.0
    return delta_E * orientation_factor * (R_0 / d_ang)**6


def fret_coupling_vector_field(
    S1: np.ndarray,
    S2: np.ndarray,
    d_ang: float,
    orientation_factor: float = 1.0,
    coupling_strength: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the FRET coupling term C(S₁, S₂) for both states.
    
    The coupling has two effects:
    1. Energy transfer: shifts the effective carrier density
    2. Coherence coupling: shares coherent coupling between states
    3. Defect-mediated coupling: defects in one create noise in the other
    
    Returns (C₁₂, C₂₁) — the coupling force on S₁ due to S₂, and vice versa.
    """
    
    V_fret = fret_coupling_strength(d_ang, orientation_factor)
    
    n1, d1, ell1, k1 = S1
    n2, d2, ell2, k2 = S2
    
    # ── 1. Carrier density coupling ──
    # FRET transfers excitation → effective change in carrier population
    # Direction: from higher energy to lower energy
    delta_n = (n2 - n1) * V_fret * coupling_strength * 1e-6
    
    # ── 2. Coherence coupling ──
    # Coherent coupling can be shared through dipole-dipole interaction
    # The state with higher coherence "lends" coherence to the other
    delta_k = (k2 - k1) * V_fret * coupling_strength * 0.1
    
    # ── 3. Defect cross-talk ──
    # Defects in one state create effective disorder in the other
    # through strain fields and charge trapping
    defect_cross_talk_1 = d2 * V_fret * coupling_strength * 0.05
    defect_cross_talk_2 = d1 * V_fret * coupling_strength * 0.05
    
    # ── 4. Dimensional coupling ──
    # Confinement in one state affects the effective dimensionality
    # of the coupled system
    delta_ell = (ell2 - ell1) * V_fret * coupling_strength * 0.01
    
    # ── Assemble coupling vectors ──
    C_12 = np.array([
        delta_n,                      # carrier transfer
        defect_cross_talk_1,          # defect noise from S2
        delta_ell,                    # dimensional coupling
        delta_k,                      # coherence sharing
    ])
    
    C_21 = np.array([
        -delta_n,                     # opposite direction
        defect_cross_talk_2,          # defect noise from S1
        -delta_ell,                   # opposite direction
        -delta_k,                     # opposite direction (for scalar k)
    ])
    
    # ── 5. Regime-mediated coupling enhancement ──
    # Coupling is stronger when states are in compatible regimes
    # and weaker when they're in incompatible regimes
    
    # Compute approximate regime weights
    from silicon_state import SiliconState
    
    state1 = SiliconState(n=n1, d=d1, l=ell1, k={"coherent": k1, "electrical": 0.5, "optical": 0.0, "thermal": 0.1, "mechanical": 0.0})
    state2 = SiliconState(n=n2, d=d2, l=ell2, k={"coherent": k2, "electrical": 0.5, "optical": 0.0, "thermal": 0.1, "mechanical": 0.0})
    
    weights1 = state1.regime_weights(temperature=0.1)
    weights2 = state2.regime_weights(temperature=0.1)
    
    # Regime compatibility: dot product of weight vectors
    regimes = sorted(weights1.keys())
    w1_vec = np.array([weights1.get(r, 0) for r in regimes])
    w2_vec = np.array([weights2.get(r, 0) for r in regimes])
    
    compatibility = np.dot(w1_vec, w2_vec)  # 1 if identical, 0 if orthogonal
    
    # Enhance coupling for compatible regimes
    # Attenuate for incompatible regimes
    enhancement = 0.5 + 0.5 * compatibility
    
    return C_12 * enhancement, C_21 * enhancement


# ─── 3. Coupled Dynamical System ───

class RegimeInteractionType(Enum):
    """Classification of the interaction between two coupled regimes."""
    LOCKING = auto()         # Both states converge to same intermediate
    OSCILLATION = auto()     # Periodic switching between regimes
    SEPARATION = auto()      # States diverge further apart
    DOMINANCE = auto()       # One state pulls the other into its regime
    CHAOS = auto()           # Irregular, unpredictable dynamics
    DECOUPLING = auto()      # Coupling too weak to affect dynamics


@dataclass
class CoupledTrajectory:
    """Result of simulating the coupled silicon state dynamics."""
    time: np.ndarray                    # time points
    S1_trajectory: np.ndarray           # (n_steps, 4) for state 1
    S2_trajectory: np.ndarray           # (n_steps, 4) for state 2
    regime1_trajectory: List[str]       # dominant regime of state 1
    regime2_trajectory: List[str]       # dominant regime of state 2
    coupling_energy: np.ndarray         # FRET coupling energy over time
    interaction_type: RegimeInteractionType
    synchronization_metric: float       # 0-1, how synchronized
    regime_transitions: List[Dict]      # detected regime changes
    d_ang: float = 4.8                  # FRET distance used for the run (Å)
    temperature: float = 300.0          # simulation temperature (K)
    
    @property
    def n_regime_switches_1(self) -> int:
        return sum(
            1 for i in range(1, len(self.regime1_trajectory))
            if self.regime1_trajectory[i] != self.regime1_trajectory[i-1]
        )
    
    @property
    def n_regime_switches_2(self) -> int:
        return sum(
            1 for i in range(1, len(self.regime2_trajectory))
            if self.regime2_trajectory[i] != self.regime2_trajectory[i-1]
        )


def simulate_coupled_dynamics(
    S1_initial: np.ndarray,
    S2_initial: np.ndarray,
    d_ang: float = 4.8,
    orientation_factor: float = 1.0,
    coupling_strength: float = 1.0,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
    t_span: Tuple[float, float] = (0, 1e-6),
    n_points: int = 1000,
    seed: Optional[int] = 42,
) -> CoupledTrajectory:
    """
    Simulate the coupled dynamics of two silicon states connected by FRET.
    
    This is the core simulation: two state vectors evolving under
    their own regime-specific vector fields PLUS the FRET coupling
    that bridges between their attractor basins.
    
    Parameters
    ----------
    S1_initial, S2_initial : arrays of shape (4,)
        Starting points in silicon phase space [n, d, ℓ, κ]
    d_ang : float
        Distance between Er-P sites (Å)
    orientation_factor : float
        Dipole orientation factor κ²
    coupling_strength : float
        Overall coupling multiplier
    temperature : float
        Temperature (K)
    t_span : tuple
        (t_start, t_end) in seconds
    n_points : int
        Number of output time points
    
    Returns
    -------
    CoupledTrajectory with full dynamics and regime analysis
    """
    
    if seed is not None:
        np.random.seed(seed)
    
    from silicon_state import SiliconState
    
    # ── Define the coupled ODE system ──
    def coupled_ode(t, Y):
        S1 = Y[:4]
        S2 = Y[4:]
        
        # Single-state vector fields (regime-specific!)
        F1 = single_state_vector_field(S1, temperature, k_dft, strain_pct)
        F2 = single_state_vector_field(S2, temperature, k_dft, strain_pct)
        
        # FRET coupling terms
        C12, C21 = fret_coupling_vector_field(
            S1, S2, d_ang, orientation_factor, coupling_strength
        )
        
        # Total dynamics
        dS1_dt = F1 + C12
        dS2_dt = F2 + C21
        
        return np.concatenate([dS1_dt, dS2_dt])
    
    # ── Time points ──
    t_eval = np.linspace(t_span[0], t_span[1], n_points)
    
    # ── Integrate ──
    Y0 = np.concatenate([S1_initial, S2_initial])
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        solution = solve_ivp(
            coupled_ode,
            t_span,
            Y0,
            t_eval=t_eval,
            method='RK45',
            rtol=1e-6,
            atol=1e-9,
            max_step=(t_span[1] - t_span[0]) / n_points * 10,
        )
    
    # ── Extract trajectories ──
    S1_traj = solution.y[:4, :].T
    S2_traj = solution.y[4:, :].T
    time = solution.t
    
    # ── Classify regimes along trajectory ──
    regime1_traj = []
    regime2_traj = []
    coupling_energy_traj = []
    
    for i in range(len(time)):
        S1_i = S1_traj[i]
        S2_i = S2_traj[i]
        
        state1 = SiliconState(
            n=max(S1_i[0], 1e8), d=np.clip(S1_i[1], 0, 1),
            l=np.clip(S1_i[2], 0.1, 3.0),
            k={"coherent": np.clip(S1_i[3], 0, 1),
               "electrical": 0.5, "optical": 0.0, "thermal": 0.1, "mechanical": 0.0}
        )
        state2 = SiliconState(
            n=max(S2_i[0], 1e8), d=np.clip(S2_i[1], 0, 1),
            l=np.clip(S2_i[2], 0.1, 3.0),
            k={"coherent": np.clip(S2_i[3], 0, 1),
               "electrical": 0.5, "optical": 0.0, "thermal": 0.1, "mechanical": 0.0}
        )
        
        regime1_traj.append(state1.dominant_regime())
        regime2_traj.append(state2.dominant_regime())
        
        V_fret = fret_coupling_strength(d_ang, orientation_factor)
        coupling_energy_traj.append(V_fret)
    
    # ── Detect regime transitions ──
    transitions = []
    for i in range(1, len(time)):
        if regime1_traj[i] != regime1_traj[i-1]:
            transitions.append({
                "time": time[i],
                "state": 1,
                "from": regime1_traj[i-1],
                "to": regime1_traj[i],
            })
        if regime2_traj[i] != regime2_traj[i-1]:
            transitions.append({
                "time": time[i],
                "state": 2,
                "from": regime2_traj[i-1],
                "to": regime2_traj[i],
            })
    
    # ── Classify interaction type ──
    interaction_type = classify_interaction(regime1_traj, regime2_traj, S1_traj, S2_traj)
    
    # ── Synchronization metric ──
    # Fraction of time both states are in the same regime
    same_regime = sum(
        1 for r1, r2 in zip(regime1_traj, regime2_traj) if r1 == r2
    )
    sync_metric = same_regime / len(regime1_traj)
    
    return CoupledTrajectory(
        time=time,
        S1_trajectory=S1_traj,
        S2_trajectory=S2_traj,
        regime1_trajectory=regime1_traj,
        regime2_trajectory=regime2_traj,
        coupling_energy=np.array(coupling_energy_traj),
        interaction_type=interaction_type,
        synchronization_metric=sync_metric,
        regime_transitions=transitions,
        d_ang=d_ang,
        temperature=temperature,
    )


# ─── 4. Interaction Classification ───

def classify_interaction(
    regime1_traj: List[str],
    regime2_traj: List[str],
    S1_traj: np.ndarray,
    S2_traj: np.ndarray,
) -> RegimeInteractionType:
    """
    Classify the type of interaction between two coupled silicon states.
    
    Uses the regime trajectories and state distances to determine
    whether the coupling produces locking, oscillation, separation,
    dominance, chaos, or decoupling.
    """
    
    n = len(regime1_traj)
    
    # Count regime switches
    switches1 = sum(
        1 for i in range(1, n) if regime1_traj[i] != regime1_traj[i-1]
    )
    switches2 = sum(
        1 for i in range(1, n) if regime2_traj[i] != regime2_traj[i-1]
    )
    total_switches = switches1 + switches2
    
    # Fraction of time in same regime
    same_frac = sum(
        1 for r1, r2 in zip(regime1_traj, regime2_traj) if r1 == r2
    ) / n
    
    # Distance between states in phase space
    distances = np.linalg.norm(S1_traj - S2_traj, axis=1)
    mean_distance = np.mean(distances)
    final_distance = distances[-1]
    initial_distance = distances[0]
    
    distance_change = final_distance - initial_distance
    
    # ── Classification logic ──
    
    # No switches and converged to same regime → LOCKING
    if total_switches == 0 and same_frac > 0.9:
        return RegimeInteractionType.LOCKING
    
    # High switch rate but regular pattern → OSCILLATION
    if total_switches > 5 and same_frac > 0.3 and same_frac < 0.7:
        # Check for periodicity in regime differences
        diff_signal = np.array([
            1 if r1 == r2 else 0
            for r1, r2 in zip(regime1_traj, regime2_traj)
        ])
        # Simple autocorrelation check
        autocorr = np.correlate(diff_signal - np.mean(diff_signal),
                                diff_signal - np.mean(diff_signal), mode='same')
        if np.max(autocorr[len(autocorr)//2 + 10:]) > 0.3 * autocorr[len(autocorr)//2]:
            return RegimeInteractionType.OSCILLATION
    
    # States diverging → SEPARATION
    if distance_change > 0.1 * initial_distance and same_frac < 0.3:
        return RegimeInteractionType.SEPARATION
    
    # One state dominant (other switches to match it)
    if switches1 == 0 and switches2 > 2 and same_frac > 0.7:
        return RegimeInteractionType.DOMINANCE
    if switches2 == 0 and switches1 > 2 and same_frac > 0.7:
        return RegimeInteractionType.DOMINANCE
    
    # High switch rate, irregular → CHAOS
    if total_switches > 10 and same_frac < 0.5:
        return RegimeInteractionType.CHAOS
    
    # Very few switches, not locked → DECOUPLING
    if total_switches <= 1 and same_frac < 0.5:
        return RegimeInteractionType.DECOUPLING
    
    # Default: weak interaction
    return RegimeInteractionType.DECOUPLING


# ─── 5. Parameter Sweep: Coupling Strength vs Distance ───

@dataclass
class CouplingPhaseDiagram:
    """Phase diagram of interaction types as a function of coupling parameters."""
    d_distances: np.ndarray       # FRET distances (Å)
    coupling_strengths: np.ndarray  # coupling multipliers
    interaction_map: np.ndarray    # (len(d), len(c)) integer array
    sync_map: np.ndarray           # synchronization metric
    interaction_labels: Dict[int, str]
    
    def optimal_coupling_region(self, target: RegimeInteractionType) -> Tuple:
        """Find the (d, coupling) region that maximizes target interaction."""
        target_idx = list(RegimeInteractionType).index(target)
        mask = self.interaction_map == target_idx
        if not mask.any():
            return None
        # Return center of mass of the region
        d_indices, c_indices = np.where(mask)
        d_center = self.d_distances[int(np.mean(d_indices))]
        c_center = self.coupling_strengths[int(np.mean(c_indices))]
        return d_center, c_center


def compute_coupling_phase_diagram(
    S1_initial: np.ndarray,
    S2_initial: np.ndarray,
    d_range: Tuple[float, float] = (2.0, 20.0),
    n_d: int = 10,
    coupling_range: Tuple[float, float] = (0.01, 10.0),
    n_c: int = 10,
    temperature: float = 300.0,
    t_span: Tuple[float, float] = (0, 1e-7),
    n_points: int = 200,
) -> CouplingPhaseDiagram:
    """
    Compute the phase diagram of interaction types as a function
    of FRET distance and coupling strength.
    
    Reveals regions where locking, oscillation, separation, etc.
    occur in the coupled silicon state dynamics.
    """
    
    d_distances = np.linspace(d_range[0], d_range[1], n_d)
    coupling_strengths = np.logspace(
        np.log10(coupling_range[0]), np.log10(coupling_range[1]), n_c
    )
    
    interaction_map = np.zeros((n_d, n_c), dtype=int)
    sync_map = np.zeros((n_d, n_c))
    
    interaction_labels = {
        i: t.name for i, t in enumerate(RegimeInteractionType)
    }
    
    for i, d in enumerate(d_distances):
        for j, c in enumerate(coupling_strengths):
            try:
                traj = simulate_coupled_dynamics(
                    S1_initial.copy(),
                    S2_initial.copy(),
                    d_ang=d,
                    coupling_strength=c,
                    temperature=temperature,
                    t_span=t_span,
                    n_points=n_points,
                    seed=None,  # different noise each time
                )
                
                interaction_map[i, j] = list(RegimeInteractionType).index(
                    traj.interaction_type
                )
                sync_map[i, j] = traj.synchronization_metric
                
            except Exception:
                interaction_map[i, j] = -1
                sync_map[i, j] = 0.0
    
    return CouplingPhaseDiagram(
        d_distances=d_distances,
        coupling_strengths=coupling_strengths,
        interaction_map=interaction_map,
        sync_map=sync_map,
        interaction_labels=interaction_labels,
    )


# ─── 6. FRET-Induced Phase Transition Detector ───

def detect_fret_induced_transition(
    S_initial: np.ndarray,
    d_ang: float,
    coupling_strength: float = 1.0,
    temperature: float = 300.0,
) -> Dict:
    """
    Determine whether FRET coupling can induce a computational
    phase transition in a silicon state.
    
    A FRET-induced transition occurs when the coupling is strong
    enough to push a state across a basin boundary into a different
    computational regime.
    """
    
    from silicon_state import SiliconState
    
    # Initial regime
    state_initial = SiliconState(
        n=S_initial[0], d=S_initial[1], l=S_initial[2],
        k={"coherent": S_initial[3], "electrical": 0.5,
           "optical": 0.0, "thermal": 0.1, "mechanical": 0.0}
    )
    initial_regime = state_initial.dominant_regime()
    
    # Compute the FRET energy
    V_fret = fret_coupling_strength(d_ang) * coupling_strength
    
    # Estimate the free energy barrier to the nearest phase boundary
    from silicon_information_geometry import (
        free_energy_landscape, compute_metric_tensor, metric_properties
    )
    from computational_phase_transition import classify_computational_phase
    
    F_initial = free_energy_landscape(S_initial, temperature)
    phase_initial = classify_computational_phase(state_initial)
    
    # Distance to nearest phase boundary (from computational phase framework)
    boundary_distance = phase_initial.phase_boundary_distance
    
    # The FRET coupling effectively adds V_fret to the energy
    # If V_fret > barrier_height, the state can be pushed across
    
    # Estimate barrier height from energy landscape curvature
    g, _ = compute_metric_tensor(S_initial, temperature)
    props = metric_properties(g)
    
    # Barrier ~ smallest eigenvalue of metric (softest direction)
    barrier_estimate = min(props["eigenvalues"]) * boundary_distance**2
    
    can_transition = V_fret > barrier_estimate
    
    return {
        "initial_regime": initial_regime,
        "computational_class": phase_initial.comp_class.name,
        "fret_energy_eV": V_fret,
        "barrier_estimate_eV": barrier_estimate,
        "boundary_distance": boundary_distance,
        "can_fret_induce_transition": can_transition,
        "required_coupling_factor": barrier_estimate / (V_fret + 1e-30) if not can_transition else 1.0,
    }


# ─── 7. Coherence Transfer Efficiency ───

def coherence_transfer_efficiency(
    S1: np.ndarray,
    S2: np.ndarray,
    d_ang: float,
    temperature: float = 300.0,
) -> float:
    """
    Compute how efficiently quantum coherence transfers from one
    silicon state to another through FRET coupling.
    
    High efficiency when:
    - Both states are near the quantum regime
    - Distance is close to Förster radius
    - Temperature is low
    """
    
    V_fret = fret_coupling_strength(d_ang)
    
    # Coherence of each state
    k1 = S1[3]  # coherent coupling
    k2 = S2[3]
    
    # Spectral overlap (resonance condition)
    # Requires both states to have similar effective dimensionality
    ell1 = S1[2]
    ell2 = S2[2]
    spectral_overlap = np.exp(-(ell1 - ell2)**2 / 0.5)
    
    # Thermal decoherence factor
    thermal_factor = np.exp(-temperature / 100.0)
    
    # Transfer efficiency (Förster-like)
    # η = V_fret / (V_fret + Γ_thermal)
    gamma_thermal = K_B * temperature / HBAR
    
    eta = V_fret / (V_fret + gamma_thermal + 1e-10) * spectral_overlap * thermal_factor
    
    # Cap at 1
    return min(eta, 1.0)


# ─── 8. Visualization ───

def plot_coupled_dynamics(
    trajectory: CoupledTrajectory,
    save_path: Optional[str] = None,
):
    """Visualize the coupled silicon state dynamics."""
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.35)
    
    REGIME_COLORS = {
        "semiconductor": "#2E86AB", "metallic": "#A23B72",
        "quantum": "#F18F01", "photonic": "#C73E1D",
        "defect_dominated": "#6B4D57", "mechanical": "#58A449",
    }
    
    time_ns = trajectory.time * 1e9
    
    # Panel 1: State trajectories in (n, d) plane
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(np.log10(trajectory.S1_trajectory[:, 0]),
             trajectory.S1_trajectory[:, 1],
             'b-', linewidth=1.5, alpha=0.7, label='State 1')
    ax1.plot(np.log10(trajectory.S2_trajectory[:, 0]),
             trajectory.S2_trajectory[:, 1],
             'r-', linewidth=1.5, alpha=0.7, label='State 2')
    ax1.scatter(np.log10(trajectory.S1_trajectory[0, 0]),
                trajectory.S1_trajectory[0, 1],
                color='blue', s=100, marker='o', zorder=5)
    ax1.scatter(np.log10(trajectory.S2_trajectory[0, 0]),
                trajectory.S2_trajectory[0, 1],
                color='red', s=100, marker='o', zorder=5)
    ax1.set_xlabel('log₁₀(n) [cm⁻³]')
    ax1.set_ylabel('Defect density d')
    ax1.set_title('Phase Space Trajectory (n, d)')
    ax1.legend(fontsize=7)
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Regime evolution
    ax2 = fig.add_subplot(gs[0, 1:])
    
    # Color-code the background by regime1
    unique_regimes = sorted(set(trajectory.regime1_trajectory + trajectory.regime2_trajectory))
    regime_to_y = {r: i for i, r in enumerate(unique_regimes)}
    
    y1 = np.array([regime_to_y[r] for r in trajectory.regime1_trajectory])
    y2 = np.array([regime_to_y[r] for r in trajectory.regime2_trajectory])
    
    ax2.step(time_ns, y1, 'b-', linewidth=2, where='mid', label='State 1', alpha=0.8)
    ax2.step(time_ns, y2, 'r--', linewidth=2, where='mid', label='State 2', alpha=0.8)
    ax2.set_yticks(range(len(unique_regimes)))
    ax2.set_yticklabels(unique_regimes, fontsize=8)
    ax2.set_xlabel('Time (ns)')
    ax2.set_ylabel('Regime')
    ax2.set_title(
        f'Regime Evolution — {trajectory.interaction_type.name} '
        f'(sync={trajectory.synchronization_metric:.2f})'
    )
    ax2.legend(fontsize=7)
    ax2.grid(True, alpha=0.3, axis='x')
    
    # Panel 3: Coupling energy
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(time_ns, trajectory.coupling_energy * 1e3, 'g-', linewidth=1.5)
    ax3.set_xlabel('Time (ns)')
    ax3.set_ylabel('FRET Energy (meV)')
    ax3.set_title('Coupling Energy')
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: State distance
    ax4 = fig.add_subplot(gs[1, 1])
    distances = np.linalg.norm(
        trajectory.S1_trajectory - trajectory.S2_trajectory, axis=1
    )
    ax4.plot(time_ns, distances, 'k-', linewidth=1.5)
    ax4.axhline(y=distances[0], color='gray', linestyle='--', alpha=0.5, label='Initial')
    ax4.set_xlabel('Time (ns)')
    ax4.set_ylabel('State Distance |S₁-S₂|')
    ax4.set_title('Inter-State Distance')
    ax4.legend(fontsize=7)
    ax4.grid(True, alpha=0.3)
    
    # Panel 5: Coherence evolution
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.plot(time_ns, trajectory.S1_trajectory[:, 3], 'b-', linewidth=1.5, label='κ₁ (coherence)')
    ax5.plot(time_ns, trajectory.S2_trajectory[:, 3], 'r--', linewidth=1.5, label='κ₂ (coherence)')
    ax5.set_xlabel('Time (ns)')
    ax5.set_ylabel('Coherent Coupling κ')
    ax5.set_title('Coherence Transfer')
    ax5.legend(fontsize=7)
    ax5.grid(True, alpha=0.3)
    
    # Panel 6: Summary
    ax6 = fig.add_subplot(gs[2, :])
    ax6.axis('off')
    
    summary = f"""
    COUPLED SILICON STATE DYNAMICS
    ═══════════════════════════════
    
    Interaction Type: {trajectory.interaction_type.name}
    Synchronization:  {trajectory.synchronization_metric:.3f}
    
    State 1 regime switches: {trajectory.n_regime_switches_1}
    State 2 regime switches: {trajectory.n_regime_switches_2}
    
    Initial regimes:
      State 1: {trajectory.regime1_trajectory[0]}
      State 2: {trajectory.regime2_trajectory[0]}
    
    Final regimes:
      State 1: {trajectory.regime1_trajectory[-1]}
      State 2: {trajectory.regime2_trajectory[-1]}
    
    Coupling energy range: [{np.min(trajectory.coupling_energy)*1e3:.3f}, {np.max(trajectory.coupling_energy)*1e3:.3f}] meV
    
    {'Regime transitions detected:' if trajectory.regime_transitions else 'No regime transitions detected.'}
    """
    
    for trans in trajectory.regime_transitions[:10]:
        summary += f"\n  t={trans['time']*1e9:.2f} ns: State {trans['state']}: {trans['from']} → {trans['to']}"
    
    ax6.text(0.05, 0.95, summary, transform=ax6.transAxes,
            fontsize=9, fontfamily='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    
    fig.suptitle(
        f'Coupled Regime Dynamics — FRET distance = {trajectory.d_ang:.1f} Å, '
        f'T = {trajectory.temperature:.0f} K',
        fontsize=14, fontweight='bold'
    )
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


def plot_coupling_phase_diagram(
    phase_diagram: CouplingPhaseDiagram,
    save_path: Optional[str] = None,
):
    """Visualize the coupling phase diagram."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Color map for interaction types
    interaction_colors = {
        "LOCKING": "#2E86AB",
        "OSCILLATION": "#F18F01",
        "SEPARATION": "#C73E1D",
        "DOMINANCE": "#58A449",
        "CHAOS": "#A23B72",
        "DECOUPLING": "#888888",
    }
    
    n_types = len(RegimeInteractionType)
    colors = [interaction_colors.get(t.name, '#888') for t in RegimeInteractionType]
    cmap = ListedColormap(colors)
    
    # Panel 1: Interaction type
    ax1 = axes[0]
    im1 = ax1.pcolormesh(
        phase_diagram.d_distances,
        phase_diagram.coupling_strengths,
        phase_diagram.interaction_map.T,
        cmap=cmap,
        shading='auto',
        vmin=0,
        vmax=n_types-1,
    )
    ax1.set_xlabel('FRET Distance (Å)')
    ax1.set_ylabel('Coupling Strength')
    ax1.set_yscale('log')
    ax1.set_title('Interaction Type Phase Diagram')
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=interaction_colors[t.name], label=t.name)
        for t in RegimeInteractionType
    ]
    ax1.legend(handles=legend_elements, fontsize=7, loc='upper right')
    
    # Panel 2: Synchronization
    ax2 = axes[1]
    im2 = ax2.pcolormesh(
        phase_diagram.d_distances,
        phase_diagram.coupling_strengths,
        phase_diagram.sync_map.T,
        cmap='RdYlBu',
        shading='auto',
        vmin=0,
        vmax=1,
    )
    ax2.set_xlabel('FRET Distance (Å)')
    ax2.set_ylabel('Coupling Strength')
    ax2.set_yscale('log')
    ax2.set_title('Synchronization Metric')
    plt.colorbar(im2, ax=ax2, label='Sync (0-1)')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ─── 9. Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("CROSS-STATE ENTANGLEMENT via FRET COUPLING")
    print("Coupled Attractor Dynamics on the Silicon Manifold")
    print("=" * 70)
    
    # ── Define initial states in different regimes ──
    
    # State 1: Quantum regime
    S1_initial = np.array([
        1e17,   # n: moderate doping
        0.01,   # d: low defects (clean quantum state)
        0.5,    # ℓ: strong confinement (quantum dot)
        0.6,    # κ: high coherence
    ])
    
    # State 2: Semiconductor regime
    S2_initial = np.array([
        1e16,   # n: standard CMOS doping
        0.02,   # d: low defects
        3.0,    # ℓ: bulk 3D
        0.1,    # κ: low coherence, high electrical
    ])
    
    print(f"\nInitial states:")
    print(f"  State 1: n={S1_initial[0]:.1e}, d={S1_initial[1]:.3f}, "
          f"ℓ={S1_initial[2]:.2f}, κ={S1_initial[3]:.3f} → QUANTUM")
    print(f"  State 2: n={S2_initial[0]:.1e}, d={S2_initial[1]:.3f}, "
          f"ℓ={S2_initial[2]:.2f}, κ={S2_initial[3]:.3f} → SEMICONDUCTOR")
    
    # ── Test 1: Close coupling (d = 3 Å, strong FRET) ──
    print("\n\n" + "=" * 70)
    print("TEST 1: STRONG FRET COUPLING (d = 3 Å)")
    print("=" * 70)
    
    traj_close = simulate_coupled_dynamics(
        S1_initial, S2_initial,
        d_ang=3.0,
        coupling_strength=5.0,
        temperature=4.0,  # cryogenic
        t_span=(0, 1e-7),
        n_points=500,
    )
    
    print(f"\n  Interaction type: {traj_close.interaction_type.name}")
    print(f"  Synchronization:  {traj_close.synchronization_metric:.3f}")
    print(f"  State 1 switches: {traj_close.n_regime_switches_1}")
    print(f"  State 2 switches: {traj_close.n_regime_switches_2}")
    print(f"  Initial: {traj_close.regime1_trajectory[0]} / {traj_close.regime2_trajectory[0]}")
    print(f"  Final:   {traj_close.regime1_trajectory[-1]} / {traj_close.regime2_trajectory[-1]}")
    
    if traj_close.regime_transitions:
        print(f"\n  Transitions:")
        for t in traj_close.regime_transitions[:5]:
            print(f"    t={t['time']*1e9:.2f} ns: State {t['state']}: {t['from']} → {t['to']}")
    
    # ── Test 2: Intermediate coupling (d = 8 Å) ──
    print("\n\n" + "=" * 70)
    print("TEST 2: INTERMEDIATE FRET COUPLING (d = 8 Å)")
    print("=" * 70)
    
    traj_mid = simulate_coupled_dynamics(
        S1_initial, S2_initial,
        d_ang=8.0,
        coupling_strength=1.0,
        temperature=77.0,  # liquid nitrogen
        t_span=(0, 1e-6),
        n_points=500,
    )
    
    print(f"\n  Interaction type: {traj_mid.interaction_type.name}")
    print(f"  Synchronization:  {traj_mid.synchronization_metric:.3f}")
    print(f"  State 1 switches: {traj_mid.n_regime_switches_1}")
    print(f"  State 2 switches: {traj_mid.n_regime_switches_2}")
    print(f"  Initial: {traj_mid.regime1_trajectory[0]} / {traj_mid.regime2_trajectory[0]}")
    print(f"  Final:   {traj_mid.regime1_trajectory[-1]} / {traj_mid.regime2_trajectory[-1]}")
    
    # ── Test 3: Weak coupling (d = 20 Å, minimal FRET) ──
    print("\n\n" + "=" * 70)
    print("TEST 3: WEAK FRET COUPLING (d = 20 Å)")
    print("=" * 70)
    
    traj_far = simulate_coupled_dynamics(
        S1_initial, S2_initial,
        d_ang=20.0,
        coupling_strength=0.1,
        temperature=300.0,
        t_span=(0, 1e-6),
        n_points=500,
    )
    
    print(f"\n  Interaction type: {traj_far.interaction_type.name}")
    print(f"  Synchronization:  {traj_far.synchronization_metric:.3f}")
    print(f"  Initial: {traj_far.regime1_trajectory[0]} / {traj_far.regime2_trajectory[0]}")
    print(f"  Final:   {traj_far.regime1_trajectory[-1]} / {traj_far.regime2_trajectory[-1]}")
    
    # ── Coherence transfer analysis ──
    print("\n\n" + "=" * 70)
    print("COHERENCE TRANSFER ANALYSIS")
    print("=" * 70)
    
    for d_test in [3.0, 5.0, 8.0, 15.0, 20.0]:
        eta = coherence_transfer_efficiency(S1_initial, S2_initial, d_test, temperature=4.0)
        print(f"  d = {d_test:5.1f} Å: η = {eta:.4f}")
    
    # ── FRET-induced transition check ──
    print("\n\n" + "=" * 70)
    print("FRET-INDUCED PHASE TRANSITION DETECTION")
    print("=" * 70)
    
    for d_test in [3.0, 5.0, 8.0]:
        result = detect_fret_induced_transition(
            S2_initial, d_test, coupling_strength=3.0, temperature=4.0
        )
        print(f"\n  d = {d_test:.1f} Å:")
        print(f"    Initial regime: {result['initial_regime']}")
        print(f"    Comp class:     {result['computational_class']}")
        print(f"    FRET energy:    {result['fret_energy_eV']*1e3:.3f} meV")
        print(f"    Barrier:        {result['barrier_estimate_eV']*1e3:.3f} meV")
        print(f"    Can transition: {result['can_fret_induce_transition']}")
    
    # ── Coupling phase diagram (small) ──
    print("\n\n" + "=" * 70)
    print("COUPLING PHASE DIAGRAM (quick scan)")
    print("=" * 70)
    
    phase_diagram = compute_coupling_phase_diagram(
        S1_initial, S2_initial,
        d_range=(2.0, 15.0), n_d=5,
        coupling_range=(0.1, 5.0), n_c=5,
        temperature=77.0,
        t_span=(0, 5e-8),
        n_points=100,
    )
    
    print(f"\n  Interaction types found:")
    for i, label in phase_diagram.interaction_labels.items():
        count = np.sum(phase_diagram.interaction_map == i)
        if count > 0:
            print(f"    {label}: {count} points")
    
    # Check for optimal locking region
    optimal = phase_diagram.optimal_coupling_region(RegimeInteractionType.LOCKING)
    if optimal:
        print(f"\n  Optimal LOCKING region: d ≈ {optimal[0]:.1f} Å, "
              f"coupling ≈ {optimal[1]:.2f}")
    
    print("\n" + "=" * 70)
    print("SIMULATIONS COMPLETE")
    print("=" * 70)
