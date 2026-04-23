# bridges/gravity_alternative_compute.py
"""
Gravity Bridge — Ternary & Quantum Extensions
==============================================
Extends GravityBridgeEncoder with alternative representations
that recover structural information compressed by binary thresholding.

Gravity is the ideal domain for these paradigms because:

  Ternary   → Gravitational fields are inherently three-valued
              at every point: ATTRACT / NULL (Lagrange) / REPEL.
              The "null" point isn't just "zero gravity"—it's a
              specific geometry where forces balance (Lagrange points,
              Hill spheres, equipotential surfaces).

  Quantum   → Orbital stability in N-body systems is fundamentally
              quantum-like: before measurement (integration), an orbit
              exists in superposition over stable/unstable states.
              The stability metric collapses at observation time.

  Stochastic → Tidal acceleration is a probability distribution
               over the body's internal mass distribution, not a
               deterministic scalar. The "d" parameter in a_tidal
               is an expectation value over a deformable body.

These are NOT replacement encodings. They are diagnostic lenses
that expose what binary compression declares nonexistent.

Usage:
    from bridges.gravity_alternative_compute import (
        TernaryGravityField, QuantumOrbitalStability,
        StochasticTidalResponse, gravity_ternary_diagnostic,
        gravity_full_alternative_diagnostic
    )
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import IntEnum

from bridges.gravity_encoder import (
    G, C_LIGHT,
    gravitational_acceleration, escape_velocity, orbital_velocity,
    schwarzschild_radius, tidal_acceleration
)


# ======================================================================
# 1. TERNARY GRAVITY FIELD
# ======================================================================

class TernaryGravityState(IntEnum):
    """
    Three-valued gravitational field classification at a point.
    
    Binary encoding says "inward = 1 if y_component < 0 else 0".
    This is wrong in three ways:
    1. It ignores the vector nature of gravity
    2. It treats "zero" as a threshold boundary rather than a distinct state
    3. It can't represent balanced-force points (Lagrange points)
    
    Ternary captures what's actually happening:
    
      ATTRACT  (−1): Net gravitational force points toward source.
                     Object accelerates toward the dominant mass.
                     
      NULL       (0): Gravitational forces balance. Net acceleration
                     is zero—this is a Lagrange point, a Hill sphere
                     boundary, or an equipotential surface.
                     
      REPEL     (+1): Net gravitational force points away from source.
                     This occurs in:
                     - Rotating reference frames (centrifugal)
                     - Dark energy dominated regions (cosmic scale)
                     - Tidal separation zones
                     - Artificial constructs (the encoder's upward-pointing
                       Moon vector example)
    
    The NULL state is the most information-rich: it's where the
    interesting dynamics happen. Binary encoding erases it.
    """
    ATTRACT = -1
    NULL    =  0
    REPEL   = +1
    
    @property
    def symbol(self) -> str:
        return {self.ATTRACT: '↓', self.NULL: '0', self.REPEL: '↑'}[self]
    
    @property
    def physical_meaning(self) -> str:
        return {
            self.ATTRACT: "Net force toward source — acceleration inward",
            self.NULL:    "Forces balanced — Lagrange point or equipotential surface",
            self.REPEL:   "Net force away from source — tidal expansion or frame effect"
        }[self]
    
    @property
    def stability_implication(self) -> str:
        return {
            self.ATTRACT: "CONVERGENT — trajectory bends toward source",
            self.NULL:    "NEUTRAL — small perturbations determine fate (chaotic regime)",
            self.REPEL:   "DIVERGENT — trajectory expands away from source"
        }[self]


def classify_gravity_ternary(vector: List[float],
                             mass_positions: List[List[float]] = None,
                             null_threshold: float = 1e-6) -> TernaryGravityState:
    """
    Classify a gravity vector into ternary state.
    
    Simple case (single vector, no additional masses):
    - Magnitude near zero → NULL (within threshold)
    - Y-component negative → ATTRACT (standard inward convention)
    - Y-component positive → REPEL (outward, frame effect, or multi-body)
    
    Advanced case (multiple mass positions provided):
    Computes net gravitational vector from all masses, then classifies.
    This correctly identifies Lagrange points where multiple gravitational
    influences cancel to near-zero net acceleration.
    
    Args:
        vector: [x, y, z] or [x, y] acceleration vector (m/s²)
        mass_positions: Optional list of [x,y,z] source mass positions
        null_threshold: Magnitude below this is NULL (balanced forces)
    
    Returns:
        TernaryGravityState classification
    """
    if mass_positions:
        # Compute net vector from all masses
        # (Simplified: assumes point at origin feeling forces from all masses)
        net = [0.0, 0.0, 0.0]
        for pos in mass_positions:
            dx = -pos[0]  # Vector FROM origin to mass (attraction toward mass)
            dy = -pos[1] if len(pos) > 1 else 0.0
            dz = -pos[2] if len(pos) > 2 else 0.0
            r = math.sqrt(dx*dx + dy*dy + dz*dz)
            if r > 0:
                # Force proportional to 1/r² in direction of mass
                mag = 1.0 / (r * r)
                net[0] += mag * dx / r
                net[1] += mag * dy / r
                net[2] += mag * dz / r
        magnitude = math.sqrt(sum(x*x for x in net))
        y_component = net[1] if len(net) > 1 else net[0]
    else:
        magnitude = math.sqrt(sum(x*x for x in vector))
        y_component = vector[1] if len(vector) > 1 else vector[0]
    
    # Check NULL first (most important state)
    if magnitude < null_threshold:
        return TernaryGravityState.NULL
    
    # Classify direction
    if y_component < 0:
        return TernaryGravityState.ATTRACT
    else:
        return TernaryGravityState.REPEL


def find_lagrange_points_ternary(vectors: List[List[float]],
                                 null_threshold: float = 1e-6) -> Dict[str, Any]:
    """
    Analyze a vector field to identify potential Lagrange points.
    
    Lagrange points are locations where gravitational forces from
    multiple bodies balance—they appear as NULL states in the
    ternary classification.
    
    In the binary encoding, these would be classified as either
    "inward" or "outward" depending on the sign of the largest
    remaining component—completely erasing their special status.
    
    Returns:
        Dict with null point locations, count, and field geometry analysis
    """
    if not vectors:
        return {"null_count": 0, "null_fraction": 0.0}
    
    states = [classify_gravity_ternary(v, null_threshold=null_threshold) 
              for v in vectors]
    
    null_count = sum(1 for s in states if s == TernaryGravityState.NULL)
    attract_count = sum(1 for s in states if s == TernaryGravityState.ATTRACT)
    repel_count = sum(1 for s in states if s == TernaryGravityState.REPEL)
    
    # Field geometry analysis
    total = len(vectors)
    null_fraction = null_count / total if total > 0 else 0
    
    # Identify clusters of NULL states (potential Lagrange regions)
    null_indices = [i for i, s in enumerate(states) if s == TernaryGravityState.NULL]
    
    # Determine field character
    if null_fraction > 0.1:
        field_character = "MULTI_BODY_BALANCED"
        interpretation = (
            f"Significant NULL regions detected ({null_fraction:.1%}). "
            f"Field shows multi-body equilibrium structure—possible "
            f"Lagrange points or equipotential surfaces. Binary encoding "
            f"would misclassify these as merely 'weak' inward/outward points."
        )
    elif null_fraction > 0.01:
        field_character = "ISOLATED_NULLS"
        interpretation = (
            f"Isolated NULL points detected ({null_count} of {total}). "
            f"These may be numerical artifacts or genuine saddle points "
            f"in the gravitational potential."
        )
    else:
        field_character = "DOMINATED"
        dominant = "ATTRACT" if attract_count > repel_count else "REPEL"
        interpretation = (
            f"Field dominated by {dominant} states. No significant "
            f"force-balance regions detected. Single-body or strongly "
            f"asymmetric multi-body configuration."
        )
    
    return {
        "total_points": total,
        "null_count": null_count,
        "null_fraction": null_fraction,
        "null_indices": null_indices[:20],  # First 20
        "attract_count": attract_count,
        "repel_count": repel_count,
        "field_character": field_character,
        "interpretation": interpretation
    }


# ======================================================================
# 2. QUANTUM ORBITAL STABILITY
# ======================================================================

@dataclass
class QuantumOrbitalStability:
    """
    Orbital stability modeled as quantum superposition.
    
    The binary encoder says "stable = 1 if s >= 0.5 else 0".
    This is a measurement collapse—it forces a continuous stability
    metric into a binary outcome.
    
    But in N-body gravitational systems, stability is fundamentally
    quantum-like:
    
    1. SUPERPOSITION: Before long-term integration, an orbit exists
       in superposition over stable and unstable futures. The stability
       metric s ∈ [0,1] is the probability amplitude, not a classification.
       
    2. MEASUREMENT: Running an N-body simulation for time T collapses
       the superposition. But different integration times give different
       results—the "measurement basis" matters.
       
    3. CHAOS: The Lyapunov time (e-folding time for perturbations)
       sets a Heisenberg-like uncertainty: Δ(stability) · Δ(time) ≥ τ_Lyap
    
    The binary threshold at 0.5 is particularly violent: it declares
    s=0.49 "unstable" and s=0.51 "stable" even though they're physically
    indistinguishable within any reasonable measurement uncertainty.
    """
    
    stability_metrics: List[float]  # Raw stability values [0,1]
    orbital_energies: List[float] = field(default_factory=list)  # Specific orbital energy
    
    # Quantum analogues
    superposition_state: Dict[str, complex] = field(default_factory=dict)
    collapse_threshold: float = 0.5
    lyapunov_uncertainty: float = 0.0
    
    # Measurement statistics
    stable_count: int = 0
    unstable_count: int = 0
    uncertain_count: int = 0  # Within uncertainty band of threshold
    
    def __post_init__(self):
        self._compute_superposition()
    
    def _compute_superposition(self):
        """
        Compute quantum-like superposition over orbital stability.
        
        Each orbit exists in state:
          |orbit⟩ = α|stable⟩ + β|unstable⟩
        
        where |α|² = stability_metric (probability of stable outcome)
              |β|² = 1 - stability_metric (probability of unstable outcome)
        
        Orbits near the threshold (0.5) are in near-equal superposition—
        they are genuinely indeterminate. The binary encoding's hard
        cutoff at 0.5 destroys this information.
        """
        if not self.stability_metrics:
            return
        
        # Lyapunov uncertainty: energy spread indicates chaotic timescale
        if self.orbital_energies and len(self.orbital_energies) > 1:
            energy_spread = max(self.orbital_energies) - min(self.orbital_energies)
            mean_energy = sum(abs(e) for e in self.orbital_energies) / len(self.orbital_energies)
            if mean_energy > 0:
                self.lyapunov_uncertainty = energy_spread / mean_energy
            else:
                self.lyapunov_uncertainty = 0.1  # Default uncertainty
        else:
            self.lyapunov_uncertainty = 0.05  # Default for single orbit
        
        # Uncertainty band around threshold
        uncertainty_band = self.lyapunov_uncertainty
        
        for s in self.stability_metrics:
            # Distance from threshold in units of uncertainty
            distance_from_threshold = (s - self.collapse_threshold) / uncertainty_band if uncertainty_band > 0 else float('inf')
            
            if distance_from_threshold > 1.0:
                self.stable_count += 1
            elif distance_from_threshold < -1.0:
                self.unstable_count += 1
            else:
                self.uncertain_count += 1
        
        # Superposition state (aggregate)
        total = len(self.stability_metrics)
        if total > 0:
            p_stable = self.stable_count / total
            p_unstable = self.unstable_count / total
            p_uncertain = self.uncertain_count / total
            
            self.superposition_state = {
                "|stable⟩": complex(math.sqrt(p_stable), 0),
                "|unstable⟩": complex(math.sqrt(p_unstable), 0),
                "|uncertain⟩": complex(math.sqrt(p_uncertain), 0),
            }
    
    def measure_at_time(self, integration_time_ratio: float) -> Dict[str, Any]:
        """
        Simulate measurement collapse after integration time.
        
        Longer integration reveals more instabilities—the act of
        measurement (integration) changes the outcome. This is the
        gravitational analogue of the quantum measurement problem.
        
        Args:
            integration_time_ratio: Ratio of integration time to
                                    characteristic orbital period
        
        Returns:
            Dict with collapsed stability classification and metadata
        """
        if not self.stability_metrics:
            return {"collapsed_state": "NO_DATA"}
        
        # Longer integration reveals more chaos
        # Effective threshold shifts with integration time
        # (longer time → higher threshold for stability)
        effective_threshold = 0.5 + 0.3 * (1 - math.exp(-integration_time_ratio))
        effective_threshold = min(0.9, effective_threshold)
        
        mean_stability = sum(self.stability_metrics) / len(self.stability_metrics)
        
        if mean_stability > effective_threshold + self.lyapunov_uncertainty:
            state = "STABLE"
        elif mean_stability < effective_threshold - self.lyapunov_uncertainty:
            state = "UNSTABLE"
        else:
            state = "INDETERMINATE"
        
        return {
            "collapsed_state": state,
            "mean_stability": mean_stability,
            "effective_threshold": effective_threshold,
            "integration_time_ratio": integration_time_ratio,
            "lyapunov_uncertainty": self.lyapunov_uncertainty,
            "uncertain_orbit_fraction": self.uncertain_count / len(self.stability_metrics) if self.stability_metrics else 0
        }
    
    def diagnose(self) -> str:
        """Human-readable quantum orbital stability diagnosis."""
        if not self.stability_metrics:
            return "No orbital stability data."
        
        total = len(self.stability_metrics)
        binary_stable = sum(1 for s in self.stability_metrics if s >= 0.5)
        binary_unstable = total - binary_stable
        
        diagnosis = (
            f"{total} orbits analyzed. "
            f"Binary encoding: {binary_stable} stable, {binary_unstable} unstable "
            f"(threshold = {self.collapse_threshold}).\n"
        )
        
        if self.uncertain_count > 0.2 * total:
            diagnosis += (
                f"QUANTUM WARNING: {self.uncertain_count} orbits ({self.uncertain_count/total:.1%}) "
                f"are within the Lyapunov uncertainty band (±{self.lyapunov_uncertainty:.3f}) "
                f"of the stability threshold. Their classification as 'stable' or 'unstable' "
                f"is a measurement artifact—the binary encoding creates a false dichotomy. "
                f"These orbits are genuinely indeterminate: their long-term fate depends on "
                f"unmodeled perturbations, integration accuracy, and observation duration."
            )
        elif self.uncertain_count > 0:
            diagnosis += (
                f"{self.uncertain_count} orbits are near the stability boundary "
                f"(within ±{self.lyapunov_uncertainty:.3f} of threshold). "
                f"Classification uncertainty exists but is limited."
            )
        else:
            diagnosis += (
                f"All orbits are cleanly separable from the stability threshold. "
                f"Binary encoding is adequate for this population."
            )
        
        if self.lyapunov_uncertainty > 0.2:
            diagnosis += (
                f" High Lyapunov uncertainty ({self.lyapunov_uncertainty:.3f}) "
                f"indicates a strongly chaotic system—stability classifications "
                f"are inherently time-dependent."
            )
        
        return diagnosis


# ======================================================================
# 3. STOCHASTIC TIDAL RESPONSE
# ======================================================================

@dataclass
class StochasticTidalResponse:
    """
    Tidal acceleration as a probability distribution over deformable body.
    
    The tidal equation a_tidal = 2GM·d/r³ uses a single "d" parameter.
    But real bodies are not rigid—the tidal deformation "d" is:
    - A function of internal structure (crust, mantle, core coupling)
    - Frequency-dependent (resonance with orbital period)
    - Probabilistic (material failure, plastic deformation)
    
    The binary encoder treats "d" as deterministic. The stochastic
    representation treats it as a probability distribution, giving
    P(a_tidal > threshold) rather than a single value.
    
    This matters for:
    - Roche limit calculations (tidal disruption)
    - Orbital evolution (tidal locking timescales)
    - Internal heating (Io, Enceladus, exoplanets)
    """
    
    mass_source: float     # Mass of tide-raising body (kg)
    distance: float         # Orbital distance (m)
    body_diameter: float    # Characteristic size of affected body (m)
    
    # Stochastic parameters
    rigidity_mean: float = 0.5       # Mean rigidity (0=liquid, 1=perfectly rigid)
    rigidity_uncertainty: float = 0.2  # Uncertainty in rigidity
    internal_structure_modes: int = 3  # Number of resonant modes
    
    # Derived distributions
    tidal_accel_mean: float = 0.0
    tidal_accel_std: float = 0.0
    roche_limit_distance: float = 0.0
    disruption_probability: float = 0.0
    
    def __post_init__(self):
        self._compute_stochastic_tidal()
    
    def _compute_stochastic_tidal(self):
        """
        Compute tidal response as probability distribution.
        
        The effective "d" is the tidal deformation, which depends on
        the body's internal structure (rigidity, resonant modes).
        
        For a perfectly rigid body: d ≈ body_diameter (elastic deformation)
        For a liquid body: d >> body_diameter (large tidal bulge)
        For a resonant body: d is frequency-dependent and can be very large
        """
        # Effective deformation parameter with uncertainty
        # Liquid body: larger deformation (1/rigidity factor)
        effective_d_mean = self.body_diameter / (self.rigidity_mean + 0.01)
        effective_d_std = effective_d_mean * self.rigidity_uncertainty
        
        # Tidal acceleration distribution
        # a_tidal ∝ d (linear in deformation)
        base_tidal = tidal_acceleration(self.mass_source, self.distance, self.body_diameter)
        self.tidal_accel_mean = base_tidal * (effective_d_mean / self.body_diameter)
        self.tidal_accel_std = abs(base_tidal * effective_d_std / self.body_diameter)
        
        # Roche limit: distance where tidal force exceeds self-gravity
        # Approximate: r_Roche = R * (2 * ρ_M / ρ_m)^(1/3)
        # Simplified: r_Roche ∝ R / rigidity^(1/3)
        # Treat rigidity as probabilistic
        if self.rigidity_mean > 0:
            # Deterministic Roche limit using mean rigidity
            self.roche_limit_distance = self.body_diameter * (2.0 / self.rigidity_mean) ** (1/3)
        else:
            self.roche_limit_distance = float('inf')  # Liquid body, always disrupted
        
        # Disruption probability: P(distance < Roche limit)
        # Monte Carlo over rigidity distribution
        import random
        n_samples = 1000
        disruptions = 0
        for _ in range(n_samples):
            sampled_rigidity = max(0.001, random.gauss(self.rigidity_mean, self.rigidity_uncertainty))
            sampled_roche = self.body_diameter * (2.0 / sampled_rigidity) ** (1/3)
            if self.distance < sampled_roche:
                disruptions += 1
        
        self.disruption_probability = disruptions / n_samples
    
    def diagnose(self) -> str:
        """Human-readable stochastic tidal diagnosis."""
        diagnosis = (
            f"Tidal acceleration: {self.tidal_accel_mean:.4e} ± {self.tidal_accel_std:.4e} m/s². "
            f"Mean Roche limit: {self.roche_limit_distance:.1f} m. "
        )
        
        if self.disruption_probability > 0.5:
            diagnosis += (
                f"TIDAL DISRUPTION LIKELY: P(disruption) = {self.disruption_probability:.1%}. "
                f"Body is within the Roche limit for most probable rigidity states. "
                f"Binary encoding using deterministic 'd' gives a single tidal value "
                f"that cannot capture this catastrophic risk."
            )
        elif self.disruption_probability > 0.1:
            diagnosis += (
                f"TIDAL DISRUPTION POSSIBLE: P(disruption) = {self.disruption_probability:.1%}. "
                f"Uncertainty in internal structure creates a non-negligible disruption risk "
                f"that deterministic tidal calculation would miss."
            )
        elif self.disruption_probability > 0.01:
            diagnosis += (
                f"Tidal disruption unlikely: P(disruption) = {self.disruption_probability:.1%}. "
                f"Tail risk exists from rigidity uncertainty."
            )
        else:
            diagnosis += (
                f"Tidal disruption negligible: P(disruption) = {self.disruption_probability:.1%}. "
                f"Body well outside Roche limit for all probable rigidity states."
            )
        
        return diagnosis


# ======================================================================
# 4. COMPOSITE GRAVITY DIAGNOSTIC
# ======================================================================

@dataclass
class GravityAlternativeDiagnostic:
    """
    Complete alternative computing diagnostic for gravity field data.
    """
    
    ternary_field_analysis: Dict[str, Any] = field(default_factory=dict)
    quantum_orbital_stability: Optional[QuantumOrbitalStability] = None
    stochastic_tidal: Optional[StochasticTidalResponse] = None
    binary_encoding: Optional[str] = None
    
    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            "Gravity Alternative Diagnostic",
            f"{'='*60}",
            "",
            "TERNARY FIELD ANALYSIS:",
        ]
        
        if self.ternary_field_analysis:
            ta = self.ternary_field_analysis
            lines.append(f"  Total points: {ta.get('total_points', 0)}")
            lines.append(f"  NULL states: {ta.get('null_count', 0)} ({ta.get('null_fraction', 0):.1%})")
            lines.append(f"  ATTRACT states: {ta.get('attract_count', 0)}")
            lines.append(f"  REPEL states: {ta.get('repel_count', 0)}")
            lines.append(f"  Field character: {ta.get('field_character', 'UNKNOWN')}")
            lines.append(f"  {ta.get('interpretation', '')}")
        
        lines.append("")
        lines.append("QUANTUM ORBITAL STABILITY:")
        
        if self.quantum_orbital_stability:
            qos = self.quantum_orbital_stability
            lines.append(f"  Orbits: {len(qos.stability_metrics)}")
            lines.append(f"  Binary-stable: {qos.stable_count}")
            lines.append(f"  Binary-unstable: {qos.unstable_count}")
            lines.append(f"  UNCERTAIN (within Lyapunov band): {qos.uncertain_count}")
            lines.append(f"  Lyapunov uncertainty: {qos.lyapunov_uncertainty:.4f}")
            lines.append(f"  {qos.diagnose()}")
            
            # Show measurement collapse at different integration times
            for t_ratio in [0.1, 1.0, 10.0]:
                result = qos.measure_at_time(t_ratio)
                lines.append(f"    Integration {t_ratio:4.1f}x: {result['collapsed_state']}")
        
        lines.append("")
        lines.append("STOCHASTIC TIDAL RESPONSE:")
        
        if self.stochastic_tidal:
            st = self.stochastic_tidal
            lines.append(f"  Tidal accel: {st.tidal_accel_mean:.4e} ± {st.tidal_accel_std:.4e} m/s²")
            lines.append(f"  Roche limit: {st.roche_limit_distance:.1f} m")
            lines.append(f"  P(disruption): {st.disruption_probability:.1%}")
            lines.append(f"  {st.diagnose()}")
        
        if self.binary_encoding:
            lines.append(f"\nBINARY ENCODING (reference):")
            lines.append(f"  {len(self.binary_encoding)} bits")
        
        lines.append(f"\n{'='*60}")
        return '\n'.join(lines)


def gravity_ternary_diagnostic(vectors: List[List[float]],
                               mass_positions: List[List[float]] = None) -> Dict[str, Any]:
    """Quick ternary field diagnostic from vector data."""
    if mass_positions:
        states = [classify_gravity_ternary(v, mass_positions) for v in vectors]
    else:
        states = [classify_gravity_ternary(v) for v in vectors]
    
    null_count = sum(1 for s in states if s == TernaryGravityState.NULL)
    attract_count = sum(1 for s in states if s == TernaryGravityState.ATTRACT)
    repel_count = sum(1 for s in states if s == TernaryGravityState.REPEL)
    
    return find_lagrange_points_ternary(vectors)


def gravity_full_alternative_diagnostic(geometry: Dict[str, Any]) -> GravityAlternativeDiagnostic:
    """
    Generate complete alternative computing diagnostic for gravity data.
    """
    diag = GravityAlternativeDiagnostic()
    
    # Ternary field analysis
    vectors = geometry.get("vectors", [])
    if vectors:
        diag.ternary_field_analysis = find_lagrange_points_ternary(vectors)
    
    # Quantum orbital stability
    stability = geometry.get("orbital_stability", [])
    potential = geometry.get("potential_energy", [])
    if stability:
        diag.quantum_orbital_stability = QuantumOrbitalStability(
            stability_metrics=stability,
            orbital_energies=potential if potential else []
        )
    
    # Stochastic tidal response (if vector masses can be inferred)
    # Simplified: use a representative mass from potential energy
    if potential and vectors:
        # Crude mass estimate from potential at some distance
        mean_potential = sum(abs(e) for e in potential) / len(potential)
        if mean_potential > 0:
            # Assume potential measured at ~1e7 m distance (rough)
            estimated_mass = mean_potential * 1e7 / G
            diag.stochastic_tidal = StochasticTidalResponse(
                mass_source=estimated_mass,
                distance=1e7,  # Assumed measurement distance
                body_diameter=1e6  # Assumed body size
            )
    
    # Binary encoding reference
    try:
        from bridges.gravity_encoder import GravityBridgeEncoder
        encoder = GravityBridgeEncoder()
        encoder.from_geometry(geometry)
        diag.binary_encoding = encoder.to_binary()
    except ImportError:
        pass
    
    return diag


# ======================================================================
# Demo
# ======================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Gravity Alternative Computing — Ternary & Quantum Demo")
    print("=" * 60)
    
    # Demo using Earth-Moon-like system
    geometry = {
        "vectors": [
            [0.0, -9.81, 0.0],    # Earth surface: strong ATTRACT
            [0.0, -1.62, 0.0],    # Moon surface: weak ATTRACT
            [0.0,  0.00, 0.0],    # Lagrange-like: NULL (balanced)
            [0.0,  0.05, 0.0],    # Near-Lagrange: weak REPEL
        ],
        "curvature": [0.5, -0.05, 2.3],
        "orbital_stability": [0.9, 0.3, 0.55, 0.48, 0.51, 0.47, 0.53],
        "potential_energy": [-6.3e7, -5.0e7, -2.8e6, 1.2e6],
    }
    
    diag = gravity_full_alternative_diagnostic(geometry)
    print(diag.summary())
