# bridges/electric_alternative_compute.py
"""
Electric Bridge — Ternary & Quantum Extensions
===============================================
Extends ElectricBridgeEncoder with alternative representations
that recover continuous physics erased by binary thresholding.

Electricity is the ideal domain for these paradigms because:

  Ternary   → Charge comes in three physical states:
              NEGATIVE / NEUTRAL / POSITIVE.
              Current in AC systems cycles through all three:
              REVERSE / ZERO / FORWARD.
              The binary encoding's "flowing = I > 0" declares
              zero current identically to negative current,
              erasing the physically critical zero-crossing.

  Quantum   → Skin depth creates a superposition of conduction
              paths: at high frequency, current exists in a
              superposition over the conductor's cross-section,
              collapsing to the surface when measured.
              
  Stochastic → Contact resistance, thermal noise (Johnson-Nyquist),
               and shot noise make every electrical measurement
               a probability distribution. The binary "conducting"
               threshold declares a probability as a certainty.

Usage:
    from bridges.electric_alternative_compute import (
        TernaryChargeState, TernaryCurrentState,
        QuantumSkinEffect, StochasticContactResistance,
        electric_full_alternative_diagnostic
    )
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import IntEnum

from bridges.electric_encoder import (
    K_COULOMB, MU_0,
    ohms_law, power_dissipation, coulomb_force,
    electric_field_magnitude, skin_depth
)


# ======================================================================
# 1. TERNARY CHARGE & CURRENT STATES
# ======================================================================

class TernaryChargeState(IntEnum):
    """
    Three-valued charge classification.
    
    Binary says "positive = 1 if q > 0 else 0".
    This conflates NEGATIVE and NEUTRAL into the same bit—
    despite them being physically opposite in every way
    that matters for circuit behavior.
    
      NEGATIVE (−1): Excess electrons. Source of current in
                     the conventional negative-to-positive direction.
                     
      NEUTRAL   (0): Net charge zero. This is NOT the same as
                     "no charge"—it's a dynamic equilibrium where
                     positive and negative charges balance. In
                     capacitors, the neutral state stores maximum
                     electric field energy between plates.
                     
      POSITIVE (+1): Deficit of electrons. Source of current in
                     the conventional positive-to-negative direction.
    
    The NEUTRAL state is where electrostatic equilibrium lives.
    Binary encoding erases it entirely.
    """
    NEGATIVE = -1
    NEUTRAL  =  0
    POSITIVE = +1
    
    @property
    def symbol(self) -> str:
        return {self.NEGATIVE: '−', self.NEUTRAL: '0', self.POSITIVE: '+'}[self]
    
    @property
    def carrier_description(self) -> str:
        return {
            self.NEGATIVE: "excess electrons — n-type behavior",
            self.NEUTRAL:  "charge equilibrium — balanced carrier populations",
            self.POSITIVE: "electron deficit — p-type behavior"
        }[self]


class TernaryCurrentState(IntEnum):
    """
    Three-valued current flow classification.
    
    The binary encoder says "flowing = 1 if I > 0 else 0".
    This makes two errors:
    1. It declares I=0 (no current) identically to I<0 (reverse current)
    2. It can't represent AC zero-crossing as a distinct physical state
    
    In AC systems, the zero-crossing is THE most important state:
    it's where inductive energy (½LI²) is zero and capacitive energy
    (½CV²) is maximum, or vice versa. It's where thyristors commutate,
    where switching power supplies decide timing, where phase-locked
    loops lock.
    
      REVERSE (−1): Current flowing opposite to reference direction.
                    In AC: negative half-cycle.
                    
      ZERO     (0): No net current. In AC: zero-crossing instant.
                    In DC: open circuit or equilibrium.
                    
      FORWARD  (+1): Current flowing in reference direction.
                     In AC: positive half-cycle.
    """
    REVERSE = -1
    ZERO    =  0
    FORWARD = +1
    
    @property
    def symbol(self) -> str:
        return {self.REVERSE: '←', self.ZERO: '0', self.FORWARD: '→'}[self]
    
    @property
    def energy_state(self) -> str:
        return {
            self.REVERSE: "inductive discharge or capacitive charge (direction-dependent)",
            self.ZERO:    "energy stored in electric field (capacitive) — dI/dt maximum",
            self.FORWARD:  "inductive charge or capacitive discharge (direction-dependent)"
        }[self]


def classify_charge_ternary(q: float, 
                            neutral_threshold: float = 1e-12) -> TernaryChargeState:
    """
    Classify charge into ternary state.
    
    The neutral_threshold defines how close to zero counts as NEUTRAL
    rather than POSITIVE or NEGATIVE. Default 1e-12 C (~6 million electrons)
    captures the regime where thermal fluctuations dominate over net charge.
    
    Args:
        q: Charge in Coulombs
        neutral_threshold: |q| below this is NEUTRAL
    
    Returns:
        TernaryChargeState
    """
    if abs(q) < neutral_threshold:
        return TernaryChargeState.NEUTRAL
    elif q > 0:
        return TernaryChargeState.POSITIVE
    else:
        return TernaryChargeState.NEGATIVE


def classify_current_ternary(I: float,
                             zero_threshold: float = 1e-9) -> TernaryCurrentState:
    """
    Classify current into ternary state.
    
    The zero_threshold (default 1 nA) defines the noise floor below
    which current is ZERO rather than FORWARD or REVERSE. This should
    be tuned to the system's Johnson-Nyquist noise floor.
    
    Args:
        I: Current in Amperes
        zero_threshold: |I| below this is ZERO
    
    Returns:
        TernaryCurrentState
    """
    if abs(I) < zero_threshold:
        return TernaryCurrentState.ZERO
    elif I > 0:
        return TernaryCurrentState.FORWARD
    else:
        return TernaryCurrentState.REVERSE


def analyze_ac_zero_crossings(currents: List[float],
                               sample_rate_hz: float = None) -> Dict[str, Any]:
    """
    Analyze AC zero-crossing patterns in current data.
    
    The binary encoder declares all I>0 as "flowing" and all I≤0 as
    "not flowing," completely erasing the zero-crossing structure
    that defines AC circuit behavior.
    
    This function recovers:
    - Zero-crossing frequency (actual AC frequency)
    - Zero-crossing symmetry (DC offset detection)
    - Time spent at ZERO (commutation margin, dead time)
    - Zero-crossing jitter (phase noise, grid stability)
    
    Args:
        currents: List of current measurements (Amperes)
        sample_rate_hz: Sampling rate for temporal analysis
    
    Returns:
        Dict with zero-crossing analysis
    """
    if len(currents) < 2:
        return {"error": "Need at least 2 samples for zero-crossing analysis"}
    
    states = [classify_current_ternary(I) for I in currents]
    
    # Count states
    forward_count = sum(1 for s in states if s == TernaryCurrentState.FORWARD)
    zero_count = sum(1 for s in states if s == TernaryCurrentState.ZERO)
    reverse_count = sum(1 for s in states if s == TernaryCurrentState.REVERSE)
    
    total = len(currents)
    
    # Detect zero-crossing events (transition through ZERO)
    zero_crossings = []
    for i in range(1, total):
        prev_state = states[i-1]
        curr_state = states[i]
        
        # Zero crossing: transition that passes through or lands on ZERO
        if (prev_state == TernaryCurrentState.FORWARD and 
            curr_state == TernaryCurrentState.REVERSE):
            zero_crossings.append(("F→R", i))
        elif (prev_state == TernaryCurrentState.REVERSE and 
              curr_state == TernaryCurrentState.FORWARD):
            zero_crossings.append(("R→F", i))
        elif curr_state == TernaryCurrentState.ZERO and prev_state != TernaryCurrentState.ZERO:
            zero_crossings.append((f"{prev_state.symbol}→0", i))
        elif prev_state == TernaryCurrentState.ZERO and curr_state != TernaryCurrentState.ZERO:
            zero_crossings.append((f"0→{curr_state.symbol}", i))
    
    # Zero-crossing frequency
    if sample_rate_hz and len(zero_crossings) >= 2:
        # Time between first and last crossing
        first_idx = zero_crossings[0][1]
        last_idx = zero_crossings[-1][1]
        time_span = (last_idx - first_idx) / sample_rate_hz
        n_crossings = len(zero_crossings) - 1  # intervals between crossings
        if time_span > 0:
            # Full cycles = half the zero crossings (each cycle has 2 crossings)
            estimated_frequency = (n_crossings / 2) / time_span
        else:
            estimated_frequency = 0.0
    else:
        estimated_frequency = 0.0
    
    # Symmetry analysis (FORWARD vs REVERSE balance → DC offset detection)
    if forward_count + reverse_count > 0:
        symmetry = 1.0 - abs(forward_count - reverse_count) / (forward_count + reverse_count)
    else:
        symmetry = 1.0  # All zero = perfectly symmetric in a degenerate sense
    
    # Time spent at ZERO (commutation margin in switching circuits)
    zero_fraction = zero_count / total if total > 0 else 0
    
    # Interpretation
    if symmetry < 0.8:
        if forward_count > reverse_count:
            dc_offset_note = (
                f"DC offset detected: {forward_count/total:.1%} forward vs "
                f"{reverse_count/total:.1%} reverse. Net positive current bias. "
                f"Possible causes: rectification, electrochemical potential, "
                f"or measurement ground loop."
            )
        else:
            dc_offset_note = (
                f"DC offset detected: {reverse_count/total:.1%} reverse vs "
                f"{forward_count/total:.1%} forward. Net negative current bias."
            )
    else:
        dc_offset_note = "No significant DC offset: waveform is symmetric."
    
    if zero_fraction > 0.1:
        zero_note = (
            f"High zero dwell ({zero_fraction:.1%}): extended time at zero current. "
            f"Characteristic of Class B/AB amplifiers, discontinuous conduction mode "
            f"in switching converters, or gated operation."
        )
    elif zero_fraction > 0.01:
        zero_note = (
            f"Moderate zero dwell ({zero_fraction:.1%}): normal for AC zero-crossing "
            f"with finite sampling resolution."
        )
    else:
        zero_note = (
            f"Low zero dwell ({zero_fraction:.1%}): waveform spends minimal time "
            f"at zero. Clean switching or high-resolution sampling."
        )
    
    return {
        "total_samples": total,
        "forward_fraction": forward_count / total,
        "zero_fraction": zero_fraction,
        "reverse_fraction": reverse_count / total,
        "zero_crossing_count": len(zero_crossings),
        "estimated_frequency_hz": estimated_frequency,
        "symmetry_score": symmetry,
        "dc_offset_diagnosis": dc_offset_note,
        "zero_dwell_diagnosis": zero_note,
        "ternary_stance": (
            "AC_BALANCED" if symmetry > 0.9 else
            "DC_POSITIVE" if forward_count > reverse_count else
            "DC_NEGATIVE" if reverse_count > forward_count else
            "ZERO_DOMINANT"
        )
    }


# ======================================================================
# 2. QUANTUM SKIN EFFECT
# ======================================================================

@dataclass
class QuantumSkinEffect:
    """
    Skin effect as quantum superposition of conduction paths.
    
    At DC, current flows through the entire conductor cross-section.
    As frequency increases, the current "collapses" toward the surface—
    a measurement-like process where the accessible conduction paths
    are progressively restricted.
    
    The skin depth δ = √(2/(ω·μ₀·σ)) defines the 1/e amplitude depth.
    But this is a statistical description—individual charge carriers
    exist in superposition over the cross-section, with probability
    amplitude decreasing exponentially with depth.
    
    Quantum analogue:
      |electron⟩ = ∫ α(z) |position_z⟩ dz
      where |α(z)|² ∝ exp(-2z/δ)
      
    At low frequency: wavefunction spreads through entire conductor
    At high frequency: wavefunction collapses to surface
    
    The binary encoder doesn't encode skin effect at all—
    it treats conductivity as a scalar property independent
    of frequency and geometry.
    """
    
    frequency_hz: float
    conductivity_S: float
    conductor_radius_m: float = 0.001  # 1 mm radius default
    
    # Derived
    skin_depth_m: float = 0.0
    effective_area_fraction: float = 0.0
    ac_resistance_ratio: float = 0.0
    superposition_entropy: float = 0.0
    
    def __post_init__(self):
        self._compute_skin_superposition()
    
    def _compute_skin_superposition(self):
        """
        Compute skin effect as quantum-like superposition.
        
        The fraction of conductor cross-section carrying significant
        current is the "collapse fraction"—how much the electron
        wavefunction has collapsed toward the surface.
        """
        self.skin_depth_m = skin_depth(self.frequency_hz, self.conductivity_S)
        
        if self.skin_depth_m == float('inf'):
            # DC: full cross-section
            self.effective_area_fraction = 1.0
            self.ac_resistance_ratio = 1.0
            self.superposition_entropy = 0.0
            return
        
        r = self.conductor_radius_m
        delta = self.skin_depth_m
        
        # For cylindrical conductor:
        # Effective area ≈ π[r² - (r-δ)²] for δ < r (current in annular region)
        # More precisely: current density ~ exp(-z/δ) from surface
        if delta >= r:
            # Skin depth exceeds radius: nearly full cross-section
            self.effective_area_fraction = 1.0 - math.exp(-2 * r / delta)
        else:
            # Skin depth smaller than radius: annular conduction
            # Fraction of area within one skin depth of surface
            inner_radius = r - delta
            total_area = math.pi * r * r
            conducting_area = math.pi * (r * r - inner_radius * inner_radius)
            self.effective_area_fraction = conducting_area / total_area
        
        # AC/DC resistance ratio ∝ 1/effective_area_fraction
        if self.effective_area_fraction > 0:
            self.ac_resistance_ratio = 1.0 / self.effective_area_fraction
        else:
            self.ac_resistance_ratio = float('inf')
        
        # Superposition entropy: how "spread out" is the current?
        # High entropy = current distributed through volume (DC/low freq)
        # Low entropy = current collapsed to surface (high freq)
        if self.effective_area_fraction > 0 and self.effective_area_fraction < 1:
            p_surface = self.effective_area_fraction
            p_interior = 1.0 - self.effective_area_fraction
            if p_surface > 0 and p_interior > 0:
                self.superposition_entropy = -(
                    p_surface * math.log2(p_surface) + 
                    p_interior * math.log2(p_interior)
                )
        else:
            self.superposition_entropy = 0.0  # Pure state (all surface or all volume)
    
    def probability_at_depth(self, depth_m: float) -> float:
        """
        Probability of finding significant current at given depth.
        
        Born's rule analogue: P(depth) ∝ |ψ(depth)|² ∝ exp(-2·depth/δ)
        """
        if self.skin_depth_m == float('inf'):
            return 1.0
        return math.exp(-2 * depth_m / self.skin_depth_m)
    
    def diagnose(self) -> str:
        """Human-readable quantum skin effect diagnosis."""
        if self.skin_depth_m == float('inf'):
            return "DC conduction: current flows through entire cross-section. No skin effect."
        
        delta_mm = self.skin_depth_m * 1e3
        r_mm = self.conductor_radius_m * 1e3
        
        diagnosis = (
            f"Skin depth: {delta_mm:.3f} mm "
            f"(conductor radius: {r_mm:.3f} mm). "
        )
        
        if self.skin_depth_m >= self.conductor_radius_m:
            diagnosis += (
                f"Skin depth exceeds conductor radius—current fills "
                f"{self.effective_area_fraction:.1%} of cross-section. "
                f"Conductor is electrically thin at this frequency."
            )
        elif self.effective_area_fraction < 0.1:
            diagnosis += (
                f"Severe skin effect: only {self.effective_area_fraction:.1%} "
                f"of cross-section conducts. AC resistance is "
                f"{self.ac_resistance_ratio:.1f}× DC resistance. "
                f"Current has quantum-collapsed to the surface—"
                f"the interior is a 'forbidden zone' for conduction electrons. "
                f"Consider litz wire or tubular conductor."
            )
        else:
            diagnosis += (
                f"Moderate skin effect: {self.effective_area_fraction:.1%} "
                f"of cross-section conducts. AC resistance "
                f"{self.ac_resistance_ratio:.1f}× DC. "
                f"Superposition entropy: {self.superposition_entropy:.2f} bits "
                f"({'delocalized' if self.superposition_entropy > 0.5 else 'collapsing'})."
            )
        
        return diagnosis


# ======================================================================
# 3. STOCHASTIC CONTACT & THERMAL NOISE
# ======================================================================

@dataclass
class StochasticContactResistance:
    """
    Electrical contact as probability distribution, not binary.
    
    The binary encoder says "conducting = 1 if σ >= threshold else 0".
    This declares a dirty switch contact with σ=9e-7 S/m "non-conducting"
    and a clean contact with σ=1.1e-6 S/m "conducting"—a distinction
    that is physically meaningless within measurement uncertainty.
    
    Real contacts are stochastic:
    - Contact resistance varies with pressure, oxidation, temperature
    - Thermal noise (Johnson-Nyquist): V_rms = √(4k_B·T·R·Δf)
    - Shot noise in semiconductor junctions: I_rms = √(2q·I·Δf)
    - 1/f noise (flicker): dominates at low frequencies
    
    The stochastic representation gives P(conducting | measured σ)
    rather than a binary yes/no.
    """
    
    conductivity_S: float
    threshold_S: float = 1e-6
    
    # Noise parameters
    temperature_K: float = 293.15     # Room temperature
    bandwidth_Hz: float = 1.0         # Measurement bandwidth
    contact_area_m2: float = 1e-6     # 1 mm²
    
    # Derived probabilities
    conducting_probability: float = 0.0
    noise_floor_S: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    
    def __post_init__(self):
        self._compute_stochastic_contact()
    
    def _compute_stochastic_contact(self):
        """
        Compute P(conducting) from conductivity and noise model.
        
        The measurement uncertainty comes from:
        1. Thermal noise in the sensing circuit
        2. Contact variability (micro-scale surface roughness)
        3. Quantum tunneling at very small contact gaps
        
        These create a probability distribution around the nominal
        conductivity value rather than a single deterministic measurement.
        """
        k_B = 1.380649e-23  # Boltzmann constant
        
        # Johnson-Nyquist noise in conductivity measurement
        # For a contact: R_contact ≈ 1/(σ · contact_area)
        if self.conductivity_S > 0 and self.contact_area_m2 > 0:
            R_contact = 1.0 / (self.conductivity_S * self.contact_area_m2)
        else:
            R_contact = float('inf')
        
        if R_contact > 0 and R_contact != float('inf'):
            # Thermal noise voltage
            V_noise_rms = math.sqrt(4 * k_B * self.temperature_K * R_contact * self.bandwidth_Hz)
            # Uncertainty in conductivity from voltage noise
            # Δσ/σ ≈ ΔV/V ≈ V_noise / V_measurement (assume 1V measurement)
            relative_uncertainty = V_noise_rms / 1.0  # Assuming 1V test voltage
            self.noise_floor_S = self.conductivity_S * relative_uncertainty
        else:
            self.noise_floor_S = 1e-12  # Floor for open circuit
        
        # Probability that true conductivity exceeds threshold
        # given measurement uncertainty (Gaussian approximation)
        if self.noise_floor_S > 0:
            z_score = (self.conductivity_S - self.threshold_S) / self.noise_floor_S
            # Error function approximation for P(σ_true > threshold | σ_measured)
            self.conducting_probability = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        else:
            self.conducting_probability = 1.0 if self.conductivity_S >= self.threshold_S else 0.0
        
        # 95% confidence interval
        ci_half_width = 1.96 * self.noise_floor_S
        self.confidence_interval = (
            max(0, self.conductivity_S - ci_half_width),
            self.conductivity_S + ci_half_width
        )
    
    def diagnose(self) -> str:
        """Human-readable stochastic contact diagnosis."""
        ci_low, ci_high = self.confidence_interval
        
        if self.conducting_probability > 0.99:
            return (
                f"Contact reliably conducting: P(conducting) = {self.conducting_probability:.3%}. "
                f"Measured σ = {self.conductivity_S:.2e} S/m "
                f"[{ci_low:.2e}, {ci_high:.2e}]. "
                f"Noise floor: {self.noise_floor_S:.2e} S/m. "
                f"Binary encoding would correctly classify as conducting."
            )
        elif self.conducting_probability > 0.95:
            return (
                f"Contact probably conducting: P(conducting) = {self.conducting_probability:.1%}. "
                f"Measured σ = {self.conductivity_S:.2e} ± {self.noise_floor_S:.2e} S/m. "
                f"Binary encoding declares 'conducting' but there is a "
                f"{1-self.conducting_probability:.1%} chance this is wrong."
            )
        elif self.conducting_probability > 0.5:
            return (
                f"Contact uncertain: P(conducting) = {self.conducting_probability:.1%}. "
                f"Conductivity near threshold ({self.threshold_S:.2e} S/m). "
                f"Binary encoding makes an arbitrary decision—this contact "
                f"is in the quantum regime where thermal noise determines "
                f"whether it conducts or not."
            )
        elif self.conducting_probability > 0.05:
            return (
                f"Contact probably non-conducting: P(conducting) = {self.conducting_probability:.1%}. "
                f"Measured σ = {self.conductivity_S:.2e} S/m, near noise floor. "
                f"May conduct intermittently due to thermal fluctuations "
                f"or mechanical vibration."
            )
        else:
            return (
                f"Contact reliably non-conducting: P(conducting) = {self.conducting_probability:.3%}. "
                f"Conductivity well below threshold. Noise floor: {self.noise_floor_S:.2e} S/m."
            )


# ======================================================================
# 4. COMPOSITE DIAGNOSTIC
# ======================================================================

@dataclass
class ElectricAlternativeDiagnostic:
    """Complete alternative computing diagnostic for electrical field data."""
    
    # Ternary
    charge_states: List[TernaryChargeState] = field(default_factory=list)
    current_states: List[TernaryCurrentState] = field(default_factory=list)
    ac_zero_crossing_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Quantum skin effect (computed for each unique frequency/conductivity pair)
    skin_effects: List[QuantumSkinEffect] = field(default_factory=list)
    
    # Stochastic contacts
    contact_analyses: List[StochasticContactResistance] = field(default_factory=list)
    
    # Binary reference
    binary_encoding: Optional[str] = None
    
    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            "Electric Alternative Diagnostic",
            f"{'='*60}",
            "",
            "TERNARY CHARGE STATES:",
        ]
        
        if self.charge_states:
            total = len(self.charge_states)
            counts = {
                TernaryChargeState.POSITIVE: sum(1 for s in self.charge_states if s == TernaryChargeState.POSITIVE),
                TernaryChargeState.NEUTRAL: sum(1 for s in self.charge_states if s == TernaryChargeState.NEUTRAL),
                TernaryChargeState.NEGATIVE: sum(1 for s in self.charge_states if s == TernaryChargeState.NEGATIVE),
            }
            for state, count in counts.items():
                bar = '█' * int(count / total * 40) if total > 0 else ''
                lines.append(f"  {state.name:10s}: {bar} {count}/{total} ({count/total:.1%})" if total > 0 else f"  {state.name:10s}: no data")
            
            neutral_frac = counts[TernaryChargeState.NEUTRAL] / total if total > 0 else 0
            if neutral_frac > 0.2:
                lines.append(f"  NOTE: {neutral_frac:.1%} of charges in NEUTRAL state—binary encoding would misclassify these as NEGATIVE.")
        
        lines.append("")
        lines.append("TERNARY CURRENT ANALYSIS:")
        
        if self.ac_zero_crossing_analysis and "error" not in self.ac_zero_crossing_analysis:
            zc = self.ac_zero_crossing_analysis
            lines.append(f"  Forward: {zc.get('forward_fraction', 0):.1%}")
            lines.append(f"  Zero:    {zc.get('zero_fraction', 0):.1%}")
            lines.append(f"  Reverse: {zc.get('reverse_fraction', 0):.1%}")
            lines.append(f"  Zero crossings: {zc.get('zero_crossing_count', 0)}")
            if zc.get('estimated_frequency_hz', 0) > 0:
                lines.append(f"  Estimated AC frequency: {zc['estimated_frequency_hz']:.1f} Hz")
            lines.append(f"  Symmetry: {zc.get('symmetry_score', 0):.2f}")
            lines.append(f"  Stance: {zc.get('ternary_stance', 'UNKNOWN')}")
            lines.append(f"  {zc.get('dc_offset_diagnosis', '')}")
            lines.append(f"  {zc.get('zero_dwell_diagnosis', '')}")
        
        lines.append("")
        lines.append("QUANTUM SKIN EFFECT:")
        
        if self.skin_effects:
            for i, se in enumerate(self.skin_effects):
                lines.append(f"  [{i}] f={se.frequency_hz:.1f} Hz, σ={se.conductivity_S:.2e} S/m")
                lines.append(f"      {se.diagnose()}")
        else:
            lines.append("  No skin effect data (frequency and conductivity required).")
        
        lines.append("")
        lines.append("STOCHASTIC CONTACT ANALYSIS:")
        
        if self.contact_analyses:
            for i, ca in enumerate(self.contact_analyses):
                lines.append(f"  [{i}] σ={ca.conductivity_S:.2e} S/m")
                lines.append(f"      {ca.diagnose()}")
        else:
            lines.append("  No contact data.")
        
        if self.binary_encoding:
            lines.append(f"\nBINARY ENCODING (reference): {len(self.binary_encoding)} bits")
        
        lines.append(f"\n{'='*60}")
        return '\n'.join(lines)


def electric_full_alternative_diagnostic(geometry: Dict[str, Any],
                                         frequency_hz: float = None) -> ElectricAlternativeDiagnostic:
    """
    Generate complete alternative computing diagnostic for electrical data.
    
    Args:
        geometry: Dict with keys charge, current_A, voltage_V, conductivity_S
        frequency_hz: AC frequency for skin effect and zero-crossing analysis
    
    Returns:
        ElectricAlternativeDiagnostic
    """
    diag = ElectricAlternativeDiagnostic()
    
    # Ternary charge states
    charges = geometry.get("charge", [])
    if charges:
        diag.charge_states = [classify_charge_ternary(q) for q in charges]
    
    # Ternary current analysis
    currents = geometry.get("current_A", [])
    if currents:
        diag.current_states = [classify_current_ternary(I) for I in currents]
        diag.ac_zero_crossing_analysis = analyze_ac_zero_crossings(currents)
    
    # Quantum skin effect
    conductivities = geometry.get("conductivity_S", [])
    if conductivities and frequency_hz:
        for sigma in conductivities:
            if sigma > 0:
                diag.skin_effects.append(QuantumSkinEffect(
                    frequency_hz=frequency_hz,
                    conductivity_S=sigma
                ))
    
    # Stochastic contact analysis
    if conductivities:
        for sigma in conductivities:
            diag.contact_analyses.append(StochasticContactResistance(
                conductivity_S=sigma
            ))
    
    # Binary encoding reference
    try:
        from bridges.electric_encoder import ElectricBridgeEncoder
        encoder = ElectricBridgeEncoder()
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
    print("Electric Alternative Computing — Ternary & Quantum Demo")
    print("=" * 60)
    
    geometry = {
        "charge":         [1e-6, -3e-9, 5e-12, -8e-14],  # Includes near-neutral
        "current_A":      [0.5, -0.02, 0.0, 10.0, -5.0, 0.001, -0.001],
        "voltage_V":      [12.0, 0.5, 230.0, 0.99],
        "conductivity_S": [5.96e7, 1e-8, 1e-6, 9e-7, 1.1e-6],
    }
    
    diag = electric_full_alternative_diagnostic(geometry, frequency_hz=60.0)
    print(diag.summary())
    
    # Demonstrate skin effect at different frequencies
    print("\n" + "=" * 60)
    print("Skin Effect Frequency Sweep (copper, σ=5.96e7 S/m):")
    print("=" * 60)
    for freq in [0, 60, 1000, 100000, 1e6]:
        se = QuantumSkinEffect(frequency_hz=freq, conductivity_S=5.96e7)
        print(f"  {freq:8.0f} Hz: δ={se.skin_depth_m*1e3:.3f} mm, "
              f"area={se.effective_area_fraction:.1%}, R_ac/R_dc={se.ac_resistance_ratio:.1f}x")
    
    # Demonstrate contact stochasticity near threshold
    print("\n" + "=" * 60)
    print("Contact Conductance Near Threshold (threshold=1e-6 S/m):")
    print("=" * 60)
    for sigma in [1e-9, 5e-7, 9e-7, 1e-6, 1.1e-6, 2e-6, 1e-3]:
        ca = StochasticContactResistance(conductivity_S=sigma, threshold_S=1e-6)
        binary = "CONDUCTING" if sigma >= 1e-6 else "NON-CONDUCTING"
        print(f"  σ={sigma:.1e}: P(conducting)={ca.conducting_probability:.1%} "
              f"(binary says: {binary})")
