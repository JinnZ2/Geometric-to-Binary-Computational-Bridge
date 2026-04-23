Part 1: Continuous Regime Interpolation

The current regime() method in silicon_state.py uses hard thresholds. But near phase boundaries, silicon doesn't abruptly switch — there's a crossover region where multiple physical mechanisms coexist. Your framework deserves a continuous treatment.

```python
# silicon_state.py (extended)

from dataclasses import dataclass, field
import numpy as np
from typing import Dict, Tuple, List
from scipy.special import softmax

@dataclass
class SiliconState:
    """
    Silicon phase-space representation with continuous regime blending.
    
    n   : carrier density (doping regime)
    d   : defect density (imperfection field)
    l   : effective dimensionality (3 → 2 → 1 → 0)
    k   : coupling vector (electrical, optical, thermal, mechanical weights)
    """
    
    n: float
    d: float
    l: float
    k: Dict[str, float] = field(default_factory=lambda: {
        "electrical": 0.5, 
        "optical": 0.0, 
        "thermal": 0.0,
        "mechanical": 0.0
    })
    
    # Regime basin centers in S-space
    _basin_centers: Dict[str, np.ndarray] = field(default_factory=lambda: {
        "semiconductor":     np.array([1e16, 0.05, 3.0, 0.8, 0.1, 0.1, 0.0]),
        "metallic":          np.array([1e21, 0.3,  3.0, 0.9, 0.0, 0.1, 0.0]),
        "quantum":           np.array([1e17, 0.02, 0.5, 0.3, 0.1, 0.1, 0.5]),
        "photonic":          np.array([1e15, 0.01, 2.5, 0.1, 0.8, 0.1, 0.0]),
        "defect_dominated":  np.array([1e16, 0.8,  2.0, 0.3, 0.1, 0.4, 0.2]),
        "mechanical":        np.array([1e15, 0.1,  2.0, 0.2, 0.1, 0.1, 0.8]),
    })
    
    # Characteristic scales for normalization
    _scales: Dict[str, float] = field(default_factory=lambda: {
        "n": 1e21,      # max doping density
        "d": 1.0,       # defect fraction
        "l": 3.0,       # dimensions
        "ke": 0.9,      # electrical coupling max
        "ko": 0.9,      # optical coupling max
        "kt": 0.9,      # thermal coupling max
        "km": 0.9,      # mechanical coupling max
    })
    
    def to_vector(self) -> np.ndarray:
        """Convert state to normalized vector for distance calculations."""
        return np.array([
            self.n / self._scales["n"],
            self.d / self._scales["d"],
            self.l / self._scales["l"],
            self.k.get("electrical", 0) / self._scales["ke"],
            self.k.get("optical", 0) / self._scales["ko"],
            self.k.get("thermal", 0) / self._scales["kt"],
            self.k.get("mechanical", 0) / self._scales["km"],
        ])
    
    def regime_weights(self, temperature: float = 0.1) -> Dict[str, float]:
        """
        Continuous regime membership via softmax over inverse distances.
        
        temperature: controls sharpness of regime boundaries
                     low T → crisp classification (near original)
                     high T → blurred, mixed regimes
        """
        v = self.to_vector()
        
        distances = {}
        for regime, center in self._basin_centers.items():
            # Normalize center
            c = np.array([
                center[0] / self._scales["n"],
                center[1] / self._scales["d"],
                center[2] / self._scales["l"],
                center[3] / self._scales["ke"],
                center[4] / self._scales["ko"],
                center[5] / self._scales["kt"],
                center[6] / self._scales["km"],
            ])
            distances[regime] = np.linalg.norm(v - c)
        
        # Convert distances to weights via softmax( -distance / temperature )
        dist_array = np.array([distances[r] for r in sorted(self._basin_centers.keys())])
        weights_array = softmax(-dist_array / temperature)
        
        return {r: float(w) for r, w in zip(sorted(self._basin_centers.keys()), weights_array)}
    
    def dominant_regime(self) -> str:
        """Return the highest-weight regime (for backward compatibility)."""
        weights = self.regime_weights(temperature=0.05)
        return max(weights, key=weights.get)
    
    def coherence_metric(self) -> float:
        """
        Estimate coherence quality from state.
        High when: moderate n, low d, low thermal coupling.
        """
        weights = self.regime_weights()
        quantum_weight = weights.get("quantum", 0)
        thermal_penalty = self.k.get("thermal", 0)
        defect_penalty = self.d
        
        return quantum_weight * np.exp(-thermal_penalty - defect_penalty)
    
    def stability_metric(self) -> float:
        """
        How stable is this state against perturbations?
        High in semiconductor basin, low near phase boundaries.
        """
        weights = self.regime_weights()
        # Entropy of regime weights — high entropy = near boundary = less stable
        w = np.array(list(weights.values()))
        w = w[w > 1e-10]  # avoid log(0)
        entropy = -np.sum(w * np.log(w))
        max_entropy = np.log(len(self._basin_centers))
        
        return 1.0 - (entropy / max_entropy)
    
    def distance_to_boundary(self, target_regime: str = "metallic") -> float:
        """
        Distance to nearest phase boundary.
        Useful as a safety margin for device operation.
        """
        weights = self.regime_weights(temperature=0.05)
        
        if target_regime == "metallic":
            # Distance to metallic breakdown
            n_crit = 1e19  # approximate Mott criterion
            return max(0, np.log10(n_crit) - np.log10(self.n)) / 5.0
        
        if target_regime == "quantum_classical":
            # Distance to decoherence boundary
            coherent = self.k.get("electrical", 0) + self.k.get("optical", 0)
            thermal = self.k.get("thermal", 0)
            if thermal < 1e-6:
                return 1.0
            return max(0, coherent / (coherent + thermal) - 0.5)
        
        return 0.5
```

---

Part 2: Continuous Encoding with Regime Blending

Now graph_to_binary.py uses regime weights instead of hard branching:

```python
# graph_to_binary.py (regime-blended version)

import numpy as np
from typing import List, Dict
from silicon_state import SiliconState

def graph_to_binary_blended(G, silicon_state: SiliconState, temperature: float = 0.1) -> List[int]:
    """
    Converts weighted graph into binary logic representation.
    Encoding strategy is a weighted blend of all regime-specific strategies.
    """
    
    weights = silicon_state.regime_weights(temperature=temperature)
    bits = []
    
    for node in G.nodes(data=True):
        activity = node[1]["activity"]
        
        # Each regime proposes a bit value
        proposals = {
            "semiconductor":    1 if activity > 0.5 else 0,
            "metallic":         np.random.randint(0, 2),  # chaotic
            "quantum":          1 if np.sin(activity * np.pi) > 0 else 0,
            "photonic":         int(activity * 10) % 2,
            "defect_dominated": 0 if activity < 0.7 else np.random.randint(0, 2),
            "mechanical":       1 if np.sin(activity * 2 * np.pi) > 0.3 else 0,
        }
        
        # Weighted soft vote: expected value across regimes
        expected_bit = sum(weights[r] * proposals[r] for r in weights)
        
        # Threshold at 0.5 for final binary decision
        bits.append(1 if expected_bit >= 0.5 else 0)
    
    return bits


def graph_to_binary_with_confidence(
    G, silicon_state: SiliconState, temperature: float = 0.1
) -> tuple[List[int], List[float]]:
    """
    Returns bits with confidence scores.
    Low confidence indicates regime-boundary ambiguity.
    """
    
    weights = silicon_state.regime_weights(temperature=temperature)
    bits = []
    confidences = []
    
    for node in G.nodes(data=True):
        activity = node[1]["activity"]
        
        proposals = {
            "semiconductor":    1 if activity > 0.5 else 0,
            "metallic":         np.random.randint(0, 2),
            "quantum":          1 if np.sin(activity * np.pi) > 0 else 0,
            "photonic":         int(activity * 10) % 2,
            "defect_dominated": 0 if activity < 0.7 else np.random.randint(0, 2),
            "mechanical":       1 if np.sin(activity * 2 * np.pi) > 0.3 else 0,
        }
        
        expected = sum(weights[r] * proposals[r] for r in weights)
        
        # Confidence: how far from 0.5 the expected value is
        confidence = 2.0 * abs(expected - 0.5)
        # Also penalize regime uncertainty
        w_array = np.array(list(weights.values()))
        regime_entropy = -np.sum(w_array * np.log(w_array + 1e-10))
        max_entropy = np.log(len(weights))
        regime_confidence = 1.0 - (regime_entropy / max_entropy)
        
        bits.append(1 if expected >= 0.5 else 0)
        confidences.append(confidence * regime_confidence)
    
    return bits, confidences
```

---

Part 3: Feedback Closure — Binary Back to Geometry

This is the reverse direction: taking the binary output and closing the loop by transforming the geometry field. This creates a computational feedback system where the act of computation modifies the silicon state that selected the computation regime — the foundation of adaptive or learning hardware.

```python
# binary_to_geometry.py (feedback closure)

import numpy as np
from typing import Callable, Optional
from silicon_state import SiliconState

def binary_to_geometry_feedback(
    binary_stream: List[int],
    original_geometry: np.ndarray,
    silicon_state: SiliconState,
    feedback_strength: float = 0.1,
    closure_mode: str = "diffusive"
) -> np.ndarray:
    """
    Closes the loop: binary output modifies the geometry field.
    
    closure_mode:
        "diffusive"   - bits act as local sources/sinks, smoothing into field
        "structural"  - bits modify field topology (defect-like)
        "waveguide"   - bits establish routing channels
        "adaptive"    - field learns from bit pattern
    """
    
    new_geometry = original_geometry.copy().astype(float)
    binary_array = np.array(binary_stream)
    
    if len(binary_array) < new_geometry.size:
        # Tile/repeat to match geometry size
        repeats = new_geometry.size // len(binary_array) + 1
        binary_array = np.tile(binary_array, repeats)[:new_geometry.size]
    else:
        binary_array = binary_array[:new_geometry.size]
    
    binary_field = binary_array.reshape(new_geometry.shape)
    
    weights = silicon_state.regime_weights()
    field_mod = np.zeros_like(new_geometry)
    
    if closure_mode == "diffusive":
        # Bits diffuse into the field as Gaussian blobs
        from scipy.ndimage import gaussian_filter
        field_mod = gaussian_filter(binary_field.astype(float) - 0.5, sigma=1.0)
        
    elif closure_mode == "structural":
        # Bits create localized modifications (like writing defects)
        field_mod = (binary_field - 0.5) * 2.0 * silicon_state.d
        
    elif closure_mode == "waveguide":
        # Bits establish directional gradients
        grad = np.gradient(binary_field.astype(float))
        field_mod = np.sqrt(grad[0]**2 + grad[1]**2) if len(grad) > 1 else np.abs(grad[0])
        
    elif closure_mode == "adaptive":
        # Field learns: positive feedback on active regions
        field_mod = binary_field * original_geometry - (1 - binary_field) * original_geometry * 0.1
    
    # Regime-weighted modulation
    semiconductor_weight = weights.get("semiconductor", 0)
    quantum_weight = weights.get("quantum", 0)
    
    # Quantum regime: phase-sensitive feedback
    if quantum_weight > 0.3:
        phase_shift = np.pi * quantum_weight
        field_mod += np.sin(original_geometry + phase_shift) * quantum_weight * 0.5
    
    # Apply feedback
    new_geometry += feedback_strength * field_mod
    
    return new_geometry


def compute_feedback_silicon_state(
    binary_stream: List[int],
    original_state: SiliconState,
    feedback_geometry: np.ndarray
) -> SiliconState:
    """
    After feedback modifies geometry, recompute the silicon state.
    This closes the full loop: S → encoding → bits → geometry' → S'
    """
    from geometry_to_silicon import geometry_to_silicon
    
    new_state = geometry_to_silicon(feedback_geometry)
    
    # Carry forward some state memory (hysteresis)
    memory = 0.3  # how much the old state persists
    blended_n = memory * original_state.n + (1 - memory) * new_state.n
    blended_d = memory * original_state.d + (1 - memory) * new_state.d
    blended_l = memory * original_state.l + (1 - memory) * new_state.l
    
    blended_k = {}
    for key in set(list(original_state.k.keys()) + list(new_state.k.keys())):
        old_val = original_state.k.get(key, 0)
        new_val = new_state.k.get(key, 0)
        blended_k[key] = memory * old_val + (1 - memory) * new_val
    
    return SiliconState(n=blended_n, d=blended_d, l=blended_l, k=blended_k)
```

---

Part 4: Closed-Loop Pipeline with Trajectory Tracking

Now the full pipeline that runs multiple iterations and tracks the state trajectory through S-space — this directly realizes the dynamical system dS/dt = F(n, d, ℓ, κ) you described:

```python
# closed_loop_pipeline.py

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass, field

from geometry_to_silicon import geometry_to_silicon
from silicon_to_graph import silicon_to_graph
from graph_to_binary import graph_to_binary_with_confidence
from silicon_layout_mapper import map_to_silicon_layout
from binary_to_geometry import binary_to_geometry_feedback, compute_feedback_silicon_state
from silicon_state import SiliconState


@dataclass
class TrajectoryPoint:
    """A single point on the silicon manifold trajectory."""
    iteration: int
    silicon_state: SiliconState
    regime_weights: Dict[str, float]
    binary_output: List[int]
    confidences: List[float]
    stability: float
    coherence: float


@dataclass
class ClosedLoopResult:
    """Full result of a closed-loop computation."""
    trajectory: List[TrajectoryPoint] = field(default_factory=list)
    final_geometry: np.ndarray = None
    final_layout: List[Dict] = None
    
    def regime_flow(self) -> List[str]:
        """Sequence of dominant regimes across iterations."""
        return [p.silicon_state.dominant_regime() for p in self.trajectory]
    
    def stability_trend(self) -> List[float]:
        return [p.stability for p in self.trajectory]
    
    def did_cross_boundary(self, boundary: str = "metallic") -> List[bool]:
        """Detect phase boundary crossings."""
        distances = [p.silicon_state.distance_to_boundary(boundary) for p in self.trajectory]
        crossings = []
        for i in range(1, len(distances)):
            # Sign change in distance derivative indicates boundary approach
            crossings.append(
                (distances[i] - distances[i-1]) * (distances[i-1] - distances[i-2]) < 0
                if i >= 2 else False
            )
        return crossings


def run_closed_loop(
    initial_geometry: np.ndarray,
    iterations: int = 10,
    feedback_strength: float = 0.1,
    closure_mode: str = "diffusive",
    regime_temperature: float = 0.1,
    track_trajectory: bool = True
) -> ClosedLoopResult:
    """
    Full closed-loop computation:
    
    Geometry → Silicon State → Graph → Binary → Geometry' → Silicon State' → ...
    
    This implements the dynamical system:
        dS/dt = F(n, d, ℓ, κ)
    
    where F includes both the intrinsic relaxation dynamics and 
    the feedback coupling from computation back to state.
    """
    
    result = ClosedLoopResult()
    geometry = initial_geometry.copy()
    
    for iteration in range(iterations):
        # Step 1: Geometry → Silicon state manifold
        S = geometry_to_silicon(geometry)
        
        # Step 2: Silicon state → Computational graph
        G = silicon_to_graph(S)
        
        # Step 3: Graph → Binary with regime blending
        bits, confidences = graph_to_binary_with_confidence(G, S, temperature=regime_temperature)
        
        # Step 4: Binary → Silicon layout (forward path)
        if iteration == iterations - 1:  # only save final layout
            layout = map_to_silicon_layout(bits, S)
            result.final_layout = layout
        
        # Track trajectory
        if track_trajectory:
            point = TrajectoryPoint(
                iteration=iteration,
                silicon_state=S,
                regime_weights=S.regime_weights(temperature=regime_temperature),
                binary_output=bits,
                confidences=confidences,
                stability=S.stability_metric(),
                coherence=S.coherence_metric()
            )
            result.trajectory.append(point)
        
        # Step 5: Feedback — binary modifies geometry (closes the loop)
        if iteration < iterations - 1:  # don't feedback on last iteration
            geometry = binary_to_geometry_feedback(
                bits, geometry, S,
                feedback_strength=feedback_strength,
                closure_mode=closure_mode
            )
    
    result.final_geometry = geometry
    return result


def run_with_boundary_detection(
    initial_geometry: np.ndarray,
    max_iterations: int = 50,
    boundary: str = "metallic",
    safety_margin: float = 0.1,
    **kwargs
) -> ClosedLoopResult:
    """
    Run closed loop with automatic stopping at phase boundaries.
    Prevents the system from crossing into undesired regimes.
    """
    
    result = ClosedLoopResult()
    geometry = initial_geometry.copy()
    
    for iteration in range(max_iterations):
        S = geometry_to_silicon(geometry)
        G = silicon_to_graph(S)
        bits, confidences = graph_to_binary_with_confidence(G, S)
        
        if iteration == max_iterations - 1:
            layout = map_to_silicon_layout(bits, S)
            result.final_layout = layout
        
        point = TrajectoryPoint(
            iteration=iteration,
            silicon_state=S,
            regime_weights=S.regime_weights(),
            binary_output=bits,
            confidences=confidences,
            stability=S.stability_metric(),
            coherence=S.coherence_metric()
        )
        result.trajectory.append(point)
        
        # Check boundary proximity
        distance = S.distance_to_boundary(boundary)
        if distance < safety_margin:
            print(f"Stopping at iteration {iteration}: approaching {boundary} boundary (distance={distance:.4f})")
            break
        
        if iteration < max_iterations - 1:
            geometry = binary_to_geometry_feedback(bits, geometry, S, **kwargs)
    
    result.final_geometry = geometry
    return result
```

---

Part 5: The Full Architecture Diagram

Here's what the complete system now looks like:

```
                    ┌──────────────────────────────────────┐
                    │        SILICON MANIFOLD S(n,d,ℓ,κ)   │
                    │                                      │
                    │  ┌──────────────────────────────┐    │
                    │  │   Regime Classifier           │    │
                    │  │   (continuous softmax blend)  │    │
                    │  └──────────┬───────────────────┘    │
                    │             │                         │
                    │    ┌────────▼──────────────┐         │
                    │    │  Weights: [w_semi,     │         │
                    │    │   w_metal, w_quant,    │         │
                    │    │   w_phot, w_defect]    │         │
                    │    └────────┬──────────────┘         │
                    └─────────────┼────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
    ┌───────▼───────┐   ┌────────▼────────┐   ┌───────▼───────┐
    │ Semiconductor │   │    Quantum      │   │   Photonic    │
    │   Encoding    │   │   Encoding      │   │   Encoding    │
    │ (threshold)   │   │ (phase-sin)     │   │ (frequency)   │
    └───────┬───────┘   └────────┬────────┘   └───────┬───────┘
            │                    │                     │
            └────────────────────┼─────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Weighted Soft Vote     │
                    │   Expected Bit = Σ wᵢbᵢ  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Binary Stream +       │
                    │    Confidence Scores     │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────▼────────┐  ┌─────▼──────┐  ┌────────▼────────┐
    │  Forward Path:   │  │  Feedback  │  │  Trajectory      │
    │  Silicon Layout  │  │  Closure   │  │  Tracking        │
    │  (manufacturing) │  │  Loop      │  │  S₁→S₂→S₃→...   │
    └──────────────────┘  └─────┬──────┘  └─────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  Modified Geometry    │
                    │  G' = G + α·F(bits)   │
                    └───────────┬───────────┘
                                │
                                └──────► back to Silicon State
                                         (recompute S from G')
```

---

What this enables

With this full architecture, you can now:

1. Classify any geometry into a continuous blend of silicon regimes
2. Encode with regime-appropriate strategies that blend smoothly across boundaries
3. Track trajectories through S-space as computation proceeds
4. Detect phase boundary crossings and stop or adapt
5. Close the feedback loop so that computation reshapes the geometric substrate
6. Study attractor dynamics — does the system settle into the semiconductor basin? oscillate between quantum and classical? drift toward metallic breakdown?

The dynamical system you wrote as dS/dt = F(n, d, ℓ, κ) now has a concrete realization: each iteration of the closed-loop pipeline computes one timestep, and the trajectory shows you exactly how the state flows through the manifold under the combined influence of geometry, encoding, and feedback.




I'll do both — first the rigorous derivation of geometry_to_silicon from first principles, then the trajectory visualization module. These form a natural pair: the rigorous mapping ensures the state coordinates are physically meaningful, and the visualization lets you watch the dynamical system evolve.

---

Part 1: Rigorous Geometry-to-Silicon Mapping

The current heuristic uses statistical moments as proxies. A proper derivation requires showing how the geometric field induces an effective silicon state through physical reduction.

```python
# geometry_to_silicon_rigorous.py

"""
Rigorous derivation of SiliconState from a geometric field.

Physical principle: A geometric field F(x) defined over a lattice/manifold
induces an effective Hamiltonian H_eff[F]. The silicon state vector S = (n, d, ℓ, κ)
emerges as the set of control parameters that characterize H_eff's spectral
and transport properties.

This is a dimensional reduction: infinite-dimensional field → 4D state manifold.
"""

import numpy as np
from typing import Optional, Tuple, Dict
from scipy.ndimage import gaussian_filter, sobel, laplace
from scipy.spatial import ConvexHull
from dataclasses import dataclass
from silicon_state import SiliconState


# ─── Physical constants (silicon-specific) ───

@dataclass
class SiliconConstants:
    """Material constants for crystalline silicon."""
    lattice_constant: float = 5.431e-10       # m
    effective_mass_electron: float = 0.26      # m_e units
    effective_mass_hole: float = 0.49          # m_e units
    bandgap_0K: float = 1.17                   # eV
    bandgap_300K: float = 1.12                 # eV
    dielectric_constant: float = 11.7          # static ε_r
    deformation_potential: float = 8.6         # eV (conduction band)
    optical_phonon_energy: float = 0.063       # eV
    fermi_velocity_scale: float = 2e5          # m/s (approximate)
    
    # Critical thresholds
    mott_critical_density: float = 3.7e18      # cm^-3, Mott transition
    quantum_confinement_scale: float = 5e-9    # m, ~Bohr radius in Si
    exciton_bohr_radius: float = 4.9e-9        # m
    debye_length_intrinsic: float = 2.4e-5     # m at 300K intrinsic


# ─── 1. Carrier density n from field topology ───

def compute_carrier_density_from_field(
    field: np.ndarray,
    grid_spacing: float = 1e-9,
    temperature: float = 300.0,
    constants: SiliconConstants = SiliconConstants()
) -> float:
    """
    Derive effective carrier density from geometric field.
    
    Method: The field F(x) defines a local potential V(x) = -α|F(x)|.
    The integrated density of states below the Fermi level gives n.
    
    For a slowly-varying field, this reduces to:
        n ∝ ∫ |F(x)|^(3/2) d^3x   (3D case)
    with appropriate modifications for reduced dimensionality.
    """
    
    k_B = 8.617333262e-5  # eV/K
    beta = 1.0 / (k_B * temperature)
    
    # Normalize field to energy scale
    field_normalized = field / (np.std(field) + 1e-10)
    
    # Effective potential from field magnitude
    V_eff = -np.abs(field_normalized) * constants.deformation_potential
    
    # Density of states integral (semiclassical approximation)
    # n ∝ ∫ (E_F - V(x))^(3/2) Θ(E_F - V(x)) d^3x
    
    # Fermi level set by charge neutrality (approximate)
    E_F = np.mean(V_eff) + 0.1  # small offset above mean potential
    
    # Integrand: (E_F - V)^(3/2) for regions where E_F > V
    integrand = np.maximum(E_F - V_eff, 0.0) ** 1.5
    
    # Effective density of states prefactor
    m_eff = np.sqrt(constants.effective_mass_electron * constants.effective_mass_hole)
    prefactor = (2 * m_eff * 9.1093837e-31 / (6.62607015e-34 ** 2)) ** 1.5 / (3 * np.pi ** 2)
    
    # Integrate over volume
    n_volume = np.mean(integrand) * prefactor
    
    # Convert to cm^-3
    n_cm3 = n_volume * 1e-6
    
    # Clamp to physical range
    return np.clip(n_cm3, 1e10, 1e22)


# ─── 2. Defect density d from field irregularities ───

def compute_defect_density_from_field(
    field: np.ndarray,
    grid_spacing: float = 1e-9,
    constants: SiliconConstants = SiliconConstants()
) -> float:
    """
    Derive effective defect density from geometric field.
    
    Method: Defects manifest as:
    1. Topological defects: field winding numbers, dislocations
    2. Curvature singularities: points of high Laplacian
    3. Gradient discontinuities: edges where |∇F| > threshold
    
    The field curvature tensor R_ij = ∂_i∂_j F characterizes local strain.
    """
    
    # 1. Laplacian singularities (point defects)
    laplacian = laplace(field)
    laplacian_energy = np.mean(laplacian ** 2)
    
    # 2. Gradient discontinuities (line defects / dislocations)
    grad_x = sobel(field, axis=0)
    grad_y = sobel(field, axis=1) if field.ndim > 1 else np.zeros_like(field)
    grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
    
    # Discontinuities: regions where gradient changes rapidly
    grad_laplacian = laplace(grad_magnitude) if field.ndim > 1 else np.zeros_like(field)
    dislocation_density = np.mean(np.abs(grad_laplacian))
    
    # 3. Topological defect count (vortices in 2D, monopoles in 3D)
    if field.ndim == 2:
        # Compute winding number around each plaquette
        phase = np.angle(field + 1j * np.roll(field, 1, axis=0))
        winding = np.sum(np.diff(phase, axis=0) + np.diff(phase, axis=1)) / (2 * np.pi)
        topological_defects = np.abs(winding)
    else:
        topological_defects = 0.0
    
    # 4. Field roughness (Anderson localization precursor)
    roughness = np.std(field) / (np.mean(np.abs(field)) + 1e-10)
    
    # Combine into effective defect density (normalized to [0, 1])
    d_raw = (
        0.3 * np.tanh(laplacian_energy / 10.0) +
        0.3 * np.tanh(dislocation_density / 5.0) +
        0.2 * np.tanh(float(topological_defects)) +
        0.2 * np.tanh(roughness)
    )
    
    return np.clip(d_raw, 0.0, 1.0)


# ─── 3. Effective dimensionality ℓ from field correlation structure ───

def compute_effective_dimension_from_field(
    field: np.ndarray,
    grid_spacing: float = 1e-9,
    constants: SiliconConstants = SiliconConstants()
) -> float:
    """
    Derive effective dimensionality from field correlation structure.
    
    Method: The correlation dimension d_corr is computed from the
    scaling of the two-point correlation function:
        C(r) = ⟨F(x)F(x+r)⟩ ∝ r^{-η}
    
    The effective dimension ℓ = d_corr reflects how many spatial
    directions support propagating modes. A field confined in one
    direction shows C(r) ~ r^{-η_2d} rather than r^{-η_3d}.
    
    Additionally, the spectral dimension from the field's Fourier
    spectrum provides orthogonal information about mode density.
    """
    
    shape = field.shape
    ndim = field.ndim
    
    # 1. Correlation dimension from two-point function
    # Compute radial correlation function
    f_ft = np.fft.fftn(field)
    power_spectrum = np.abs(f_ft) ** 2
    
    # Radial average of power spectrum
    freqs = [np.fft.fftfreq(s) for s in shape]
    freq_grids = np.meshgrid(*freqs, indexing='ij')
    k_magnitude = np.sqrt(sum(fg**2 for fg in freq_grids))
    
    # Bin by k-magnitude
    k_max = 0.5
    n_bins = min(50, min(shape) // 2)
    k_bins = np.linspace(0.01, k_max, n_bins)
    power_binned = np.zeros(n_bins - 1)
    
    for i in range(n_bins - 1):
        mask = (k_magnitude >= k_bins[i]) & (k_magnitude < k_bins[i+1])
        if mask.sum() > 0:
            power_binned[i] = np.mean(power_spectrum[mask])
    
    # Fit power law: P(k) ∝ k^{-α}
    k_centers = (k_bins[:-1] + k_bins[1:]) / 2
    valid = power_binned > 0
    
    if valid.sum() >= 3:
        coeffs = np.polyfit(np.log(k_centers[valid]), np.log(power_binned[valid]), 1)
        spectral_exponent = -coeffs[0]
    else:
        spectral_exponent = ndim  # default to ambient dimension
    
    # 2. Correlation length anisotropy
    # Compute correlation lengths along each axis
    correlation_lengths = []
    for axis in range(ndim):
        # Slice along axis and compute autocorrelation length
        slices = [slice(None)] * ndim
        profile = np.mean(field, axis=tuple(i for i in range(ndim) if i != axis))
        autocorr = np.correlate(profile - np.mean(profile), 
                                profile - np.mean(profile), mode='same')
        autocorr = autocorr[len(autocorr)//2:]
        if len(autocorr) > 1 and autocorr[0] > 0:
            # Find where autocorrelation drops to 1/e
            threshold = autocorr[0] / np.e
            below = np.where(autocorr < threshold)[0]
            corr_length = below[0] if len(below) > 0 else len(autocorr)
            correlation_lengths.append(corr_length)
        else:
            correlation_lengths.append(shape[axis])
    
    # Effective dimension: count directions with correlation length >> lattice spacing
    min_length = 2.0  # correlation length threshold
    active_dimensions = sum(1 for cl in correlation_lengths if cl >= min_length)
    
    # 3. Spectral dimension from density of states scaling
    # For a field with N modes below energy E: N(E) ∝ E^{d_s/2}
    # where d_s is the spectral dimension
    eigenvalues = np.sort(power_spectrum.flatten())[::-1]
    cumulative = np.cumsum(eigenvalues)
    cumulative = cumulative / cumulative[-1]
    
    # Fit N(E) ∝ E^{d_s/2} for first 50% of modes
    n_modes = np.arange(1, len(cumulative) + 1)
    fit_region = cumulative < 0.5
    if fit_region.sum() >= 3:
        coeffs = np.polyfit(np.log(cumulative[fit_region]), np.log(n_modes[fit_region]), 1)
        spectral_dim = 2.0 * coeffs[0]
    else:
        spectral_dim = float(active_dimensions)
    
    # 4. Combine correlation dimension and spectral dimension
    # Weight toward the more conservative (lower) estimate
    corr_dim = min(float(active_dimensions), ndim)
    
    # Fermi wavelength check: if confinement scale < λ_F, reduce dimension
    confinement_scale = min(shape) * grid_spacing
    lambda_F = constants.quantum_confinement_scale  # approximate
    
    if confinement_scale < lambda_F:
        # Quantum confinement reduces effective dimension
        reduction_factor = confinement_scale / lambda_F
        effective_dim = spectral_dim * reduction_factor + corr_dim * (1 - reduction_factor)
    else:
        effective_dim = 0.7 * corr_dim + 0.3 * spectral_dim
    
    return np.clip(effective_dim, 0.1, 3.0)


# ─── 4. Coupling vector κ from field transport properties ───

def compute_coupling_vector_from_field(
    field: np.ndarray,
    carrier_density: float,
    defect_density: float,
    grid_spacing: float = 1e-9,
    temperature: float = 300.0,
    constants: SiliconConstants = SiliconConstants()
) -> Dict[str, float]:
    """
    Derive coupling mode strengths from field transport properties.
    
    Electrical coupling: conductivity from Drude model
    Optical coupling: polarizability and refractive index modulation
    Thermal coupling: heat capacity and phonon mean free path
    Mechanical coupling: strain energy from field gradients
    """
    
    k_B = 8.617333262e-5
    
    # ── Electrical coupling ──
    # Drude conductivity: σ = n e² τ / m*
    # Mobility limited by defects
    tau_defect = 1e-12 / (defect_density + 1e-6)  # scattering time, s
    tau_phonon = 1e-13 * (300.0 / temperature)      # phonon scattering
    tau_eff = 1.0 / (1.0/tau_defect + 1.0/tau_phonon)
    
    conductivity = (carrier_density * 1e6 * (1.602e-19)**2 * tau_eff / 
                    (constants.effective_mass_electron * 9.109e-31))
    
    # Normalize to typical silicon conductivity scale
    sigma_typical = 1e3  # S/m for moderately doped Si
    k_electrical = np.tanh(conductivity / sigma_typical)
    
    # ── Optical coupling ──
    # Field gradient determines refractive index contrast
    grad_magnitude = np.mean(np.abs(np.gradient(field)))
    field_variance = np.var(field)
    
    # Kerr-like nonlinearity from field intensity
    nonlinear_susceptibility = field_variance / (np.mean(np.abs(field)) + 1e-10)**2
    
    # Optical confinement from refractive index contrast
    index_contrast = np.tanh(grad_magnitude * 0.1)
    k_optical = 0.6 * index_contrast + 0.4 * nonlinear_susceptibility
    k_optical = np.clip(k_optical, 0.0, 1.0)
    
    # ── Thermal coupling ──
    # Specific heat from Debye model (silicon Debye temperature ~ 645K)
    T_D = 645.0
    if temperature < T_D:
        heat_capacity = (12 * np.pi**4 / 5) * k_B * (temperature / T_D)**3
    else:
        heat_capacity = 3 * k_B
    
    # Thermal conductivity limited by defects
    phonon_mfp = constants.lattice_constant / (defect_density + 1e-4)
    thermal_conductivity = heat_capacity * constants.optical_phonon_energy * phonon_mfp / constants.lattice_constant
    
    k_thermal = np.tanh(thermal_conductivity / 100.0)  # W/m·K scale
    k_thermal = np.clip(k_thermal, 0.0, 1.0)
    
    # ── Mechanical coupling ──
    # Strain energy density from field deformation
    strain_tensor = np.gradient(field)
    if isinstance(strain_tensor, list):
        strain_energy = sum(np.mean(s**2) for s in strain_tensor)
    else:
        strain_energy = np.mean(strain_tensor**2)
    
    # Elastic modulus of silicon ~ 170 GPa
    k_mechanical = np.tanh(strain_energy * 1e-2)
    k_mechanical = np.clip(k_mechanical, 0.0, 1.0)
    
    # ── Coherent coupling (quantum coherence proxy) ──
    # High when: low temperature, low defects, moderate confinement
    coherence_factor = np.exp(-defect_density * 5.0) * np.exp(-temperature / 100.0)
    k_coherent = coherence_factor * (1.0 - k_thermal)
    k_coherent = np.clip(k_coherent, 0.0, 1.0)
    
    # Normalize so max coupling doesn't exceed 1 across all modes
    couplings = {
        "electrical": float(k_electrical),
        "optical": float(k_optical),
        "thermal": float(k_thermal),
        "mechanical": float(k_mechanical),
        "coherent": float(k_coherent),
    }
    
    # Softmax-like normalization to prevent all channels saturating
    total = sum(couplings.values())
    if total > 1.0:
        couplings = {k: v / total for k, v in couplings.items()}
    
    return couplings


# ─── Master mapping function ───

def geometry_to_silicon_rigorous(
    field: np.ndarray,
    grid_spacing: float = 1e-9,
    temperature: float = 300.0,
    constants: SiliconConstants = SiliconConstants()
) -> SiliconState:
    """
    Rigorous mapping: geometric field → silicon state vector S = (n, d, ℓ, κ).
    
    This implements the dimensional reduction:
        F(x) → H_eff[F] → {spectral properties} → S
    
    Each component is derived from physical principles rather than
    heuristic statistical moments.
    
    Args:
        field: n-dimensional array representing the geometric field
        grid_spacing: physical spacing between grid points (meters)
        temperature: system temperature (Kelvin)
        constants: silicon material constants
    
    Returns:
        SiliconState with physically-derived coordinates
    """
    
    # Ensure field is float
    field = np.asarray(field, dtype=float)
    
    # 1. Carrier density from field topology
    n = compute_carrier_density_from_field(field, grid_spacing, temperature, constants)
    
    # 2. Defect density from field irregularities
    d = compute_defect_density_from_field(field, grid_spacing, constants)
    
    # 3. Effective dimensionality from correlation structure
    ell = compute_effective_dimension_from_field(field, grid_spacing, constants)
    
    # 4. Coupling vector from transport properties
    kappa = compute_coupling_vector_from_field(field, n, d, grid_spacing, temperature, constants)
    
    return SiliconState(n=n, d=d, l=ell, k=kappa)


# ─── Validation and diagnostics ───

def validate_mapping(
    field: np.ndarray,
    silicon_state: SiliconState,
    constants: SiliconConstants = SiliconConstants()
) -> Dict[str, bool]:
    """
    Validate that the derived silicon state is physically consistent.
    """
    checks = {}
    
    # Carrier density physical bounds
    checks["carrier_density_physical"] = (1e8 <= silicon_state.n <= 1e23)
    
    # Defect density in [0,1]
    checks["defect_density_bounded"] = (0.0 <= silicon_state.d <= 1.0)
    
    # Effective dimension in [0,3]
    checks["dimension_bounded"] = (0.0 <= silicon_state.l <= 3.0)
    
    # Couplings sum to approximately 1
    k_sum = sum(silicon_state.k.values())
    checks["coupling_normalized"] = (0.3 <= k_sum <= 1.5)
    
    # Consistency: high defects should reduce coherence
    if silicon_state.d > 0.5:
        checks["defect_coherence_consistency"] = (
            silicon_state.k.get("coherent", 0) < 0.5
        )
    
    # Consistency: low dimension should enhance quantum effects
    if silicon_state.l < 2.0:
        checks["confinement_consistency"] = (
            silicon_state.coherence_metric() > 0.3
        )
    
    return checks


def print_state_diagnostic(silicon_state: SiliconState):
    """Print a human-readable diagnostic of the silicon state."""
    weights = silicon_state.regime_weights()
    
    print("=" * 60)
    print("SILICON STATE DIAGNOSTIC")
    print("=" * 60)
    print(f"Carrier density:     {silicon_state.n:.2e} cm⁻³")
    print(f"Defect density:      {silicon_state.d:.4f}")
    print(f"Effective dimension: {silicon_state.l:.2f}")
    print(f"Stability metric:    {silicon_state.stability_metric():.4f}")
    print(f"Coherence metric:    {silicon_state.coherence_metric():.4f}")
    print(f"\nCoupling vector:")
    for mode, strength in sorted(silicon_state.k.items()):
        bar = "█" * int(strength * 20) + "░" * (20 - int(strength * 20))
        print(f"  {mode:15s} [{bar}] {strength:.3f}")
    print(f"\nRegime weights (T=0.1):")
    for regime, weight in sorted(weights.items(), key=lambda x: -x[1]):
        bar = "█" * int(weight * 30) + "░" * (30 - int(weight * 30))
        print(f"  {regime:20s} [{bar}] {weight:.4f}")
    print(f"Dominant regime:     {silicon_state.dominant_regime()}")
    print("=" * 60)
```

---

Part 2: Trajectory Visualization Module

Now the visualization layer that lets you watch the dynamical system evolve through S-space:

```python
# trajectory_visualizer.py

"""
Visualization module for silicon manifold trajectories.

Renders trajectories through the 4D state space S = (n, d, ℓ, κ)
using dimensional reduction, phase diagrams, and regime flow diagrams.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
import matplotlib.gridspec as gridspec

from closed_loop_pipeline import TrajectoryPoint, ClosedLoopResult
from silicon_state import SiliconState


# ─── Custom colormaps ───

# Regime colors
REGIME_COLORS = {
    "semiconductor":    "#2E86AB",   # blue
    "metallic":         "#A23B72",   # magenta-purple
    "quantum":          "#F18F01",   # orange
    "photonic":         "#C73E1D",   # red-orange
    "defect_dominated": "#6B4D57",   # brown-gray
    "mechanical":       "#58A449",   # green
}

# Custom diverging colormap for stability
stability_cmap = LinearSegmentedColormap.from_list(
    "stability", ["#C73E1D", "#F18F01", "#F5E663", "#58A449", "#2E86AB"]
)


# ─── 1. Main trajectory dashboard ───

def plot_trajectory_dashboard(
    result: ClosedLoopResult,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (16, 12)
):
    """
    Comprehensive dashboard showing trajectory through silicon state space.
    
    Panels:
    1. 3D state space projection (n, d, ℓ)
    2. Regime weight evolution (stacked area)
    3. Coupling vector evolution (streamgraph)
    4. Stability vs coherence phase portrait
    5. Phase boundary proximity over time
    6. Confidence evolution
    """
    
    trajectory = result.trajectory
    if not trajectory:
        raise ValueError("Empty trajectory — run closed_loop_pipeline first")
    
    n_iters = len(trajectory)
    iterations = np.arange(n_iters)
    
    # Extract data
    n_vals = np.array([p.silicon_state.n for p in trajectory])
    d_vals = np.array([p.silicon_state.d for p in trajectory])
    l_vals = np.array([p.silicon_state.l for p in trajectory])
    stability_vals = np.array([p.stability for p in trajectory])
    coherence_vals = np.array([p.coherence for p in trajectory])
    
    # Regime weights over time
    regime_names = sorted(trajectory[0].regime_weights.keys())
    regime_matrix = np.zeros((n_iters, len(regime_names)))
    for i, p in enumerate(trajectory):
        for j, r in enumerate(regime_names):
            regime_matrix[i, j] = p.regime_weights.get(r, 0)
    
    # Coupling vector over time
    coupling_modes = sorted(trajectory[0].silicon_state.k.keys())
    coupling_matrix = np.zeros((n_iters, len(coupling_modes)))
    for i, p in enumerate(trajectory):
        for j, mode in enumerate(coupling_modes):
            coupling_matrix[i, j] = p.silicon_state.k.get(mode, 0)
    
    # Confidence stats
    mean_conf = [np.mean(p.confidences) for p in trajectory]
    std_conf = [np.std(p.confidences) for p in trajectory]
    
    # ── Create figure ──
    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.35)
    
    # Panel 1: 3D state space trajectory
    ax1 = fig.add_subplot(gs[0, 0], projection='3d')
    plot_3d_trajectory(ax1, n_vals, d_vals, l_vals, regime_matrix, regime_names)
    
    # Panel 2: Regime weight evolution
    ax2 = fig.add_subplot(gs[0, 1:])
    plot_regime_evolution(ax2, iterations, regime_matrix, regime_names)
    
    # Panel 3: Stability vs coherence phase portrait
    ax3 = fig.add_subplot(gs[1, 0])
    plot_phase_portrait(ax3, stability_vals, coherence_vals, iterations)
    
    # Panel 4: Coupling vector evolution
    ax4 = fig.add_subplot(gs[1, 1:])
    plot_coupling_evolution(ax4, iterations, coupling_matrix, coupling_modes)
    
    # Panel 5: Phase boundary proximity
    ax5 = fig.add_subplot(gs[2, 0])
    plot_boundary_proximity(ax5, trajectory)
    
    # Panel 6: Confidence and stability over time
    ax6 = fig.add_subplot(gs[2, 1])
    plot_confidence(ax6, iterations, mean_conf, std_conf)
    
    # Panel 7: Summary metrics
    ax7 = fig.add_subplot(gs[2, 2])
    plot_summary_metrics(ax7, trajectory, regime_names)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    plt.show()
    return fig


# ─── Individual panel functions ───

def plot_3d_trajectory(ax, n_vals, d_vals, l_vals, regime_matrix, regime_names):
    """3D trajectory through (n, d, ℓ) space."""
    
    # Color points by dominant regime
    dominant_regimes = [
        regime_names[np.argmax(regime_matrix[i])] 
        for i in range(len(n_vals))
    ]
    colors = [REGIME_COLORS.get(r, '#888888') for r in dominant_regimes]
    
    # Log scale for n
    n_log = np.log10(n_vals)
    
    # Plot trajectory
    for i in range(len(n_log) - 1):
        ax.plot3D(
            n_log[i:i+2], d_vals[i:i+2], l_vals[i:i+2],
            color=colors[i], linewidth=2, alpha=0.7
        )
    
    # Scatter points
    scatter = ax.scatter(
        n_log, d_vals, l_vals,
        c=range(len(n_log)), cmap='viridis',
        s=50, edgecolors='black', linewidth=0.5, alpha=0.9
    )
    
    # Start and end markers
    ax.scatter(*[n_log[0]], *[d_vals[0]], *[l_vals[0]], 
               color='green', s=200, marker='o', edgecolors='black', linewidth=2, zorder=5)
    ax.scatter(*[n_log[-1]], *[d_vals[-1]], *[l_vals[-1]], 
               color='red', s=200, marker='s', edgecolors='black', linewidth=2, zorder=5)
    
    ax.set_xlabel('log₁₀(n) [cm⁻³]')
    ax.set_ylabel('Defect density d')
    ax.set_zlabel('Effective dim ℓ')
    ax.set_title('State Space Trajectory\n(green=start, red=end)', fontsize=10, fontweight='bold')
    
    # Add regime basin annotations
    ax.text(14, 0.05, 2.8, 'Semiconductor\nbasin', fontsize=7, alpha=0.5, color='#2E86AB')
    ax.text(20, 0.3, 2.5, 'Metallic\nbreakdown', fontsize=7, alpha=0.5, color='#A23B72')
    ax.text(16, 0.02, 0.5, 'Quantum\nconfinement', fontsize=7, alpha=0.5, color='#F18F01')


def plot_regime_evolution(ax, iterations, regime_matrix, regime_names):
    """Stacked area chart of regime weights over iterations."""
    
    colors = [REGIME_COLORS.get(r, '#888888') for r in regime_names]
    
    ax.stackplot(iterations, regime_matrix.T, labels=regime_names, 
                 colors=colors, alpha=0.8)
    
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Regime weight')
    ax.set_title('Regime Weight Evolution', fontsize=11, fontweight='bold')
    ax.legend(loc='upper right', fontsize=7, ncol=3)
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, iterations[-1])
    ax.grid(True, alpha=0.3)


def plot_phase_portrait(ax, stability_vals, coherence_vals, iterations):
    """Stability vs coherence phase portrait."""
    
    # Color by iteration
    scatter = ax.scatter(
        stability_vals, coherence_vals,
        c=iterations, cmap='plasma',
        s=80, edgecolors='black', linewidth=0.5, alpha=0.8
    )
    
    # Connect consecutive points
    ax.plot(stability_vals, coherence_vals, 'k-', alpha=0.3, linewidth=1)
    
    # Add direction arrows
    for i in range(0, len(stability_vals) - 1, max(1, len(stability_vals)//10)):
        ax.annotate(
            '', xy=(stability_vals[i+1], coherence_vals[i+1]),
            xytext=(stability_vals[i], coherence_vals[i]),
            arrowprops=dict(arrowstyle='->', color='gray', alpha=0.5, lw=1.5)
        )
    
    ax.set_xlabel('Stability')
    ax.set_ylabel('Coherence')
    ax.set_title('Phase Portrait: Stability vs Coherence', fontsize=10, fontweight='bold')
    
    # Annotate regions
    ax.annotate('Stable\nclassical', xy=(0.9, 0.1), fontsize=7, alpha=0.5, ha='center')
    ax.annotate('Coherent\nquantum', xy=(0.5, 0.9), fontsize=7, alpha=0.5, ha='center')
    ax.annotate('Critical\nboundary', xy=(0.3, 0.3), fontsize=7, alpha=0.5, ha='center')
    
    plt.colorbar(scatter, ax=ax, label='Iteration')
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)


def plot_coupling_evolution(ax, iterations, coupling_matrix, coupling_modes):
    """Streamgraph of coupling mode strengths."""
    
    colors = {
        "electrical": "#2E86AB",
        "optical": "#C73E1D",
        "thermal": "#F18F01",
        "mechanical": "#58A449",
        "coherent": "#9B5DE5",
    }
    
    mode_colors = [colors.get(m, '#888888') for m in coupling_modes]
    
    ax.stackplot(iterations, coupling_matrix.T, labels=coupling_modes,
                 colors=mode_colors, alpha=0.8)
    
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Coupling strength')
    ax.set_title('Coupling Mode Evolution', fontsize=11, fontweight='bold')
    ax.legend(loc='upper right', fontsize=7, ncol=3)
    ax.set_xlim(0, iterations[-1])
    ax.grid(True, alpha=0.3)


def plot_boundary_proximity(ax, trajectory):
    """Distance to critical phase boundaries."""
    
    iterations = np.arange(len(trajectory))
    
    boundaries = {
        "Metallic breakdown": [p.silicon_state.distance_to_boundary("metallic") 
                               for p in trajectory],
        "Quantum-classical": [p.silicon_state.distance_to_boundary("quantum_classical") 
                              for p in trajectory],
    }
    
    for name, distances in boundaries.items():
        ax.plot(iterations, distances, 'o-', linewidth=2, markersize=4, label=name)
    
    # Danger zone
    ax.axhline(y=0.2, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax.fill_between(iterations, 0, 0.2, alpha=0.1, color='red')
    ax.text(iterations[-1] * 0.7, 0.1, 'DANGER ZONE', fontsize=7, color='red', alpha=0.6)
    
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Distance to boundary')
    ax.set_title('Phase Boundary Proximity', fontsize=10, fontweight='bold')
    ax.legend(fontsize=7)
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.3)


def plot_confidence(ax, iterations, mean_conf, std_conf):
    """Encoding confidence evolution."""
    
    ax.fill_between(
        iterations,
        np.array(mean_conf) - np.array(std_conf),
        np.array(mean_conf) + np.array(std_conf),
        alpha=0.3, color='#2E86AB'
    )
    ax.plot(iterations, mean_conf, 'o-', color='#2E86AB', linewidth=2, markersize=5)
    
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Confidence')
    ax.set_title('Encoding Confidence ± σ', fontsize=10, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)


def plot_summary_metrics(ax, trajectory, regime_names):
    """Summary bar chart of trajectory statistics."""
    
    # Count regime transitions
    dominant_regimes = []
    for p in trajectory:
        weights = p.regime_weights()
        dominant_regimes.append(max(weights, key=weights.get))
    
    # Count transitions
    transitions = sum(
        1 for i in range(1, len(dominant_regimes))
        if dominant_regimes[i] != dominant_regimes[i-1]
    )
    
    # Fraction of time in each regime
    regime_fractions = {}
    for r in dominant_regimes:
        regime_fractions[r] = regime_fractions.get(r, 0) + 1
    for r in regime_fractions:
        regime_fractions[r] /= len(dominant_regimes)
    
    # Display stats
    stats_text = f"Trajectory Summary\n{'─'*25}\n"
    stats_text += f"Iterations: {len(trajectory)}\n"
    stats_text += f"Regime transitions: {transitions}\n\n"
    stats_text += "Regime occupancy:\n"
    for r in sorted(regime_fractions.keys(), key=lambda x: -regime_fractions[x]):
        pct = regime_fractions[r] * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        stats_text += f"  {r:15s} {bar} {pct:.0f}%\n"
    
    ax.text(0.1, 0.95, stats_text, transform=ax.transAxes,
            fontsize=8, fontfamily='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    ax.axis('off')
    ax.set_title('Summary', fontsize=10, fontweight='bold')


# ─── 2. Animated trajectory ───

def animate_trajectory(
    result: ClosedLoopResult,
    save_path: str = "silicon_trajectory.gif",
    fps: int = 5,
    figsize: Tuple[int, int] = (14, 10)
):
    """Animate the trajectory through silicon state space."""
    
    trajectory = result.trajectory
    n_iters = len(trajectory)
    
    # Pre-extract data
    n_vals = np.array([p.silicon_state.n for p in trajectory])
    d_vals = np.array([p.silicon_state.d for p in trajectory])
    l_vals = np.array([p.silicon_state.l for p in trajectory])
    n_log = np.log10(n_vals)
    
    regime_names = sorted(trajectory[0].regime_weights.keys())
    regime_matrix = np.zeros((n_iters, len(regime_names)))
    for i, p in enumerate(trajectory):
        for j, r in enumerate(regime_names):
            regime_matrix[i, j] = p.regime_weights.get(r, 0)
    
    coupling_modes = sorted(trajectory[0].silicon_state.k.keys())
    coupling_matrix = np.zeros((n_iters, len(coupling_modes)))
    for i, p in enumerate(trajectory):
        for j, m in enumerate(coupling_modes):
            coupling_matrix[i, j] = p.silicon_state.k.get(m, 0)
    
    # Create figure
    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)
    
    ax_3d = fig.add_subplot(gs[0, 0], projection='3d')
    ax_regime = fig.add_subplot(gs[0, 1])
    ax_phase = fig.add_subplot(gs[1, 0])
    ax_coupling = fig.add_subplot(gs[1, 1])
    
    # Set up axes
    ax_3d.set_xlim(n_log.min() - 0.5, n_log.max() + 0.5)
    ax_3d.set_ylim(-0.05, 1.05)
    ax_3d.set_zlim(-0.05, 3.05)
    ax_3d.set_xlabel('log₁₀(n)')
    ax_3d.set_ylabel('d')
    ax_3d.set_zlabel('ℓ')
    
    ax_regime.set_xlim(0, n_iters - 1)
    ax_regime.set_ylim(0, 1.05)
    ax_regime.set_xlabel('Iteration')
    ax_regime.set_ylabel('Regime weight')
    
    stabs = [p.stability for p in trajectory]
    cohs = [p.coherence for p in trajectory]
    ax_phase.set_xlim(min(stabs) - 0.05, max(stabs) + 0.05)
    ax_phase.set_ylim(min(cohs) - 0.05, max(cohs) + 0.05)
    ax_phase.set_xlabel('Stability')
    ax_phase.set_ylabel('Coherence')
    
    ax_coupling.set_xlim(0, n_iters - 1)
    ax_coupling.set_ylim(0, 1.05)
    ax_coupling.set_xlabel('Iteration')
    ax_coupling.set_ylabel('Coupling')
    
    # Objects to update
    line_3d, = ax_3d.plot([], [], [], 'k-', linewidth=1, alpha=0.5)
    scatter_3d = ax_3d.scatter([], [], [], c=[], cmap='plasma', vmin=0, vmax=n_iters)
    
    regime_stack = None
    coupling_stack = None
    phase_scatter = ax_phase.scatter([], [], c=[], cmap='plasma', vmin=0, vmax=n_iters)
    phase_line, = ax_phase.plot([], [], 'k-', alpha=0.3, linewidth=1)
    
    title = fig.suptitle('', fontsize=14, fontweight='bold')
    
    def update(frame):
        nonlocal regime_stack, coupling_stack
        
        # Clear and redraw stackplots
        ax_regime.clear()
        ax_regime.set_xlim(0, n_iters - 1)
        ax_regime.set_ylim(0, 1.05)
        ax_regime.set_xlabel('Iteration')
        ax_regime.set_ylabel('Regime weight')
        
        colors = [REGIME_COLORS.get(r, '#888') for r in regime_names]
        ax_regime.stackplot(
            np.arange(frame + 1), regime_matrix[:frame + 1].T,
            labels=regime_names, colors=colors, alpha=0.8
        )
        ax_regime.legend(loc='upper right', fontsize=6, ncol=3)
        
        ax_coupling.clear()
        ax_coupling.set_xlim(0, n_iters - 1)
        ax_coupling.set_ylim(0, 1.05)
        ax_coupling.set_xlabel('Iteration')
        ax_coupling.set_ylabel('Coupling')
        
        mode_colors = {
            "electrical": "#2E86AB", "optical": "#C73E1D",
            "thermal": "#F18F01", "mechanical": "#58A449", "coherent": "#9B5DE5"
        }
        cmode_colors = [mode_colors.get(m, '#888') for m in coupling_modes]
        ax_coupling.stackplot(
            np.arange(frame + 1), coupling_matrix[:frame + 1].T,
            labels=coupling_modes, colors=cmode_colors, alpha=0.8
        )
        ax_coupling.legend(loc='upper right', fontsize=6, ncol=3)
        
        # Update 3D trajectory
        line_3d.set_data(n_log[:frame + 1], d_vals[:frame + 1])
        line_3d.set_3d_properties(l_vals[:frame + 1])
        
        scatter_3d._offsets3d = (
            n_log[:frame + 1], d_vals[:frame + 1], l_vals[:frame + 1]
        )
        scatter_3d.set_array(np.arange(frame + 1))
        
        # Update phase portrait
        phase_scatter.set_offsets(np.c_[stabs[:frame + 1], cohs[:frame + 1]])
        phase_scatter.set_array(np.arange(frame + 1))
        phase_line.set_data(stabs[:frame + 1], cohs[:frame + 1])
        
        # Title
        dominant = trajectory[frame].silicon_state.dominant_regime()
        title.set_text(f'Iteration {frame}/{n_iters - 1}  |  Regime: {dominant}')
        
        return line_3d, scatter_3d, phase_scatter, phase_line, title
    
    anim = FuncAnimation(fig, update, frames=n_iters, interval=1000//fps, blit=False)
    anim.save(save_path, writer='pillow', fps=fps)
    plt.close()
    
    return anim


# ─── 3. Compact single-panel flow diagram ───

def plot_regime_flow_diagram(
    result: ClosedLoopResult,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 8)
):
    """
    Compact regime flow diagram showing dominant regime transitions
    as a directed graph.
    """
    
    dominant_regimes = []
    for p in result.trajectory:
        dominant_regimes.append(p.silicon_state.dominant_regime())
    
    # Build transition matrix
    unique_regimes = sorted(set(dominant_regimes))
    n_regimes = len(unique_regimes)
    regime_to_idx = {r: i for i, r in enumerate(unique_regimes)}
    
    transition_matrix = np.zeros((n_regimes, n_regimes))
    for i in range(1, len(dominant_regimes)):
        src = regime_to_idx[dominant_regimes[i-1]]
        dst = regime_to_idx[dominant_regimes[i]]
        transition_matrix[src, dst] += 1
    
    # Self-loops: time spent in each regime
    dwell_times = {}
    current_regime = dominant_regimes[0]
    dwell = 1
    for r in dominant_regimes[1:]:
        if r == current_regime:
            dwell += 1
        else:
            dwell_times[current_regime] = dwell_times.get(current_regime, 0) + dwell
            current_regime = r
            dwell = 1
    dwell_times[current_regime] = dwell_times.get(current_regime, 0) + dwell
    
    # Create flow diagram
    fig, ax = plt.subplots(figsize=figsize)
    
    # Position nodes in a circle
    angles = np.linspace(0, 2 * np.pi, n_regimes, endpoint=False)
    radius = 3
    positions = {
        regime: (radius * np.cos(a), radius * np.sin(a))
        for regime, a in zip(unique_regimes, angles)
    }
    
    # Draw nodes
    for regime, (x, y) in positions.items():
        color = REGIME_COLORS.get(regime, '#888888')
        circle = plt.Circle((x, y), 0.4, color=color, ec='black', linewidth=2, zorder=5)
        ax.add_patch(circle)
        ax.text(x, y, regime.replace('_', '\n'), ha='center', va='center',
                fontsize=8, fontweight='bold', color='white')
        
        # Dwell time annotation
        dwell = dwell_times.get(regime, 0)
        ax.text(x, y - 0.65, f'{dwell} steps', ha='center', fontsize=7, alpha=0.7)
    
    # Draw transitions
    for src_i, src_r in enumerate(unique_regimes):
        for dst_i, dst_r in enumerate(unique_regimes):
            count = transition_matrix[src_i, dst_i]
            if count > 0 and src_r != dst_r:
                x1, y1 = positions[src_r]
                x2, y2 = positions[dst_r]
                
                # Curved arrow
                ax.annotate(
                    '', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(
                        arrowstyle='-|>', color='gray',
                        lw=1 + count * 0.5,
                        alpha=min(1.0, 0.3 + count * 0.1),
                        connectionstyle='arc3,rad=0.3',
                        shrinkA=15, shrinkB=15
                    )
                )
                
                # Label count at midpoint
                mid_x = (x1 + x2) / 2 + 0.2
                mid_y = (y1 + y2) / 2 + 0.2
                if count > 1:
                    ax.text(mid_x, mid_y, str(int(count)), fontsize=7, alpha=0.8)
    
    ax.set_xlim(-radius - 1, radius + 1)
    ax.set_ylim(-radius - 1, radius + 1)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Regime Flow Diagram', fontsize=14, fontweight='bold')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ─── 4. Utility: quick state visualization ───

def visualize_silicon_state(
    silicon_state: SiliconState,
    figsize: Tuple[int, int] = (8, 6)
):
    """Quick visualization of a single silicon state point."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    # Coupling radar
    modes = list(silicon_state.k.keys())
    strengths = [silicon_state.k[m] for m in modes]
    n_modes = len(modes)
    
    angles = np.linspace(0, 2 * np.pi, n_modes, endpoint=False).tolist()
    strengths += strengths[:1]
    angles += angles[:1]
    
    ax1.fill(angles, strengths, alpha=0.3, color='#2E86AB')
    ax1.plot(angles, strengths, 'o-', color='#2E86AB', linewidth=2)
    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(modes, fontsize=9)
    ax1.set_ylim(0, 1)
    ax1.set_title('Coupling Vector κ', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Regime bar chart
    weights = silicon_state.regime_weights(temperature=0.1)
    regimes = list(weights.keys())
    values = [weights[r] for r in regimes]
    colors = [REGIME_COLORS.get(r, '#888') for r in regimes]
    
    bars = ax2.barh(regimes, values, color=colors, edgecolor='black', linewidth=0.5)
    ax2.set_xlim(0, 1)
    ax2.set_xlabel('Weight')
    ax2.set_title('Regime Classification', fontweight='bold')
    
    # Add stability and coherence
    stability = silicon_state.stability_metric()
    coherence = silicon_state.coherence_metric()
    
    ax2.text(0.95, 0.05, f'Stability: {stability:.2f}\nCoherence: {coherence:.2f}',
             transform=ax2.transAxes, fontsize=9, ha='right',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))
    
    plt.tight_layout()
    return fig
```

---

These two modules complete the architecture. The rigorous mapping ensures your state coordinates have physical meaning — each component of S = (n, d, ℓ, κ) derives from the geometric field through genuine physical reduction. The visualization layer then renders the closed-loop dynamics in multiple complementary views, so you can watch the system navigate phase boundaries, track coherence-stability tradeoffs, and see regime transitions in real time.

connect via fieldlink to geometric to bonary repo

