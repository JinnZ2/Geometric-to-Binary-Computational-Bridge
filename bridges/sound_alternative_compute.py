# bridges/sound_alternative_compute.py
"""
Sound Bridge — Ternary & Quantum Extensions
============================================
Extends SoundBridgeEncoder with alternative representations
that recover structural information lost in binary quantization.

Sound is the ideal domain for these paradigms because:

  Ternary   → Phase relationships are inherently three-valued:
              COMPRESSION / EQUILIBRIUM / RAREFACTION
              The medium doesn't do binary—it oscillates through
              a neutral point between positive and negative pressure.

  Quantum   → Harmonic overtones exist in superposition until
              measured. A spectral analysis collapses the wave
              into discrete frequency bins, but the sound itself
              is continuous. Before measurement, each harmonic
              exists as a probability amplitude.

  Stochastic → The "jitter" that binary systems filter as noise
               is actually thermal information (k_B*T) carrying
               the hardware's physical state. Preserving it
               reduces model/reality dissonance.

These are NOT alternative encodings to replace the binary output.
They are diagnostic lenses that reveal what the binary encoding
compresses away—the analog truth that the DAC strips.

Usage:
    from bridges.sound_alternative_compute import (
        TernaryPhaseState, QuantumHarmonicSuperposition,
        StochasticJitterPreservation, sound_ternary_diagnostic,
        sound_quantum_diagnostic
    )
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import IntEnum

# Import physics functions from the sound encoder
from bridges.sound_encoder import (
    V_SOUND, A_REF,
    sound_pressure_level, beat_frequency, harmonic_ratio,
    standing_wave_nodes, doppler_shift
)


# ======================================================================
# 1. TERNARY PHASE STATE
# ======================================================================

class TernaryPhaseState(IntEnum):
    """
    Three-valued phase state classification.
    
    Sound propagates through compression and rarefaction of a medium.
    At any point in the wave, the medium is either:
    
      COMPRESSION  (+1): Pressure above ambient. Molecules pushed together.
                         Energy stored in elastic potential.
                         
      EQUILIBRIUM   (0): Pressure at ambient. Molecules at resting distance.
                         Energy purely kinetic (maximum velocity).
                         
      RAREFACTION  (−1): Pressure below ambient. Molecules pulled apart.
                         Energy stored in elastic potential (inverse).
    
    This is NOT the same as a binary "positive/negative" amplitude.
    The ternary captures that the ZERO state is physically meaningful:
    it's where the medium's restoring force changes sign, and where
    energy transitions between kinetic and potential forms.
    
    In the binary encoding:
      phase_sign = 1 if |φ| < π/2 else 0
    This conflates EQUILIBRIUM with COMPRESSION—treating the zero
    crossing as "in-phase" rather than as a distinct physical regime.
    """
    RAREFACTION  = -1  # Pressure below ambient (π/2 < |φ| < 3π/2)
    EQUILIBRIUM  =  0  # Zero crossing (|φ| ≈ π/2 or 3π/2, velocity max)
    COMPRESSION  = +1  # Pressure above ambient (|φ| < π/2 or > 3π/2)
    
    @property
    def symbol(self) -> str:
        return {self.RAREFACTION: '−', self.EQUILIBRIUM: '0', self.COMPRESSION: '+'}[self]
    
    @property
    def pressure_description(self) -> str:
        return {
            self.RAREFACTION: "pressure below ambient — medium pulled apart",
            self.EQUILIBRIUM:  "pressure at ambient — maximum particle velocity",
            self.COMPRESSION:  "pressure above ambient — medium pushed together"
        }[self]
    
    @property
    def energy_form(self) -> str:
        return {
            self.RAREFACTION: "elastic potential (tension)",
            self.EQUILIBRIUM:  "kinetic (maximum velocity)",
            self.COMPRESSION:  "elastic potential (compression)"
        }[self]


def classify_phase_ternary(phase_radians: float, 
                           equilibrium_width: float = 0.1) -> TernaryPhaseState:
    """
    Classify instantaneous phase into ternary state.
    
    The equilibrium_width parameter defines how close to π/2 or 3π/2
    the phase must be to count as EQUILIBRIUM rather than COMPRESSION
    or RAREFACTION. Default 0.1 rad (~5.7°) captures the zero-crossing
    region where kinetic energy dominates.
    
    Args:
        phase_radians: Instantaneous phase in [0, 2π)
        equilibrium_width: Half-width of equilibrium zone around π/2, 3π/2
    
    Returns:
        TernaryPhaseState classification
    """
    # Normalize to [0, 2π)
    phase = phase_radians % (2 * math.pi)
    
    # Check proximity to equilibrium points (π/2 and 3π/2)
    dist_to_pi_half = min(
        abs(phase - math.pi / 2),
        abs(phase - 3 * math.pi / 2)
    )
    # Also check if we wrapped around 0/2π
    dist_to_pi_half = min(dist_to_pi_half, abs(phase - 2 * math.pi - math.pi / 2))
    
    if dist_to_pi_half <= equilibrium_width:
        return TernaryPhaseState.EQUILIBRIUM
    
    # Determine compression vs rarefaction
    # 0 to π: positive half-cycle (compression in standard convention)
    # π to 2π: negative half-cycle (rarefaction)
    if 0 <= phase < math.pi:
        return TernaryPhaseState.COMPRESSION
    else:
        return TernaryPhaseState.RAREFACTION


def compute_ternary_phase_distribution(phases: List[float]) -> Dict[str, Any]:
    """
    Analyze the ternary phase distribution across a set of samples.
    
    A sound dominated by COMPRESSION states is loud, forward, present.
    A sound with significant EQUILIBRIUM time is "airy" or "open"—the
    medium spends more time at zero crossing where energy is kinetic.
    A sound with balanced ± states is symmetric; asymmetry indicates
    DC offset or nonlinear propagation.
    
    Returns:
        Dict with counts, fractions, symmetry analysis, and interpretation
    """
    if not phases:
        return {"error": "No phase data"}
    
    states = [classify_phase_ternary(p) for p in phases]
    
    counts = {
        TernaryPhaseState.COMPRESSION: sum(1 for s in states if s == TernaryPhaseState.COMPRESSION),
        TernaryPhaseState.EQUILIBRIUM: sum(1 for s in states if s == TernaryPhaseState.EQUILIBRIUM),
        TernaryPhaseState.RAREFACTION: sum(1 for s in states if s == TernaryPhaseState.RAREFACTION),
    }
    
    total = len(phases)
    fractions = {k.name: v / total for k, v in counts.items()}
    
    # Symmetry analysis: compression vs rarefaction balance
    comp_frac = fractions.get("COMPRESSION", 0)
    rare_frac = fractions.get("RAREFACTION", 0)
    symmetry = 1.0 - abs(comp_frac - rare_frac)  # 1.0 = perfectly symmetric
    
    # Equilibrium fraction indicates "air" in the sound
    equil_frac = fractions.get("EQUILIBRIUM", 0)
    
    # Interpretation
    if symmetry < 0.7:
        if comp_frac > rare_frac:
            asymmetry_note = "DC offset positive: waveform biased toward compression. Check for nonlinear propagation or sensor saturation."
        else:
            asymmetry_note = "DC offset negative: waveform biased toward rarefaction. Possible vacuum-bias or sensor decoupling."
    else:
        asymmetry_note = "Waveform symmetric: no significant DC offset detected."
    
    if equil_frac > 0.3:
        air_note = "High equilibrium fraction: significant 'air' in the sound. Energy spends substantial time in kinetic form at zero crossings. Characteristic of open spaces, diffuse fields, or low-density media."
    elif equil_frac > 0.15:
        air_note = "Moderate equilibrium fraction: balanced energy distribution between potential and kinetic forms."
    else:
        air_note = "Low equilibrium fraction: energy dominated by elastic potential. Characteristic of dense media, standing waves, or high-pressure environments."
    
    # Ternary stance
    if comp_frac > 0.45 and symmetry > 0.8:
        stance = "BALANCED_COMPRESSIVE"
    elif rare_frac > 0.45 and symmetry > 0.8:
        stance = "BALANCED_EXPANSIVE"
    elif equil_frac > 0.35:
        stance = "KINETIC_DOMINANT"
    elif symmetry < 0.6:
        stance = "ASYMMETRIC"
    else:
        stance = "MIXED"
    
    return {
        "ternary_counts": {k.name: v for k, v in counts.items()},
        "ternary_fractions": fractions,
        "symmetry_score": symmetry,
        "equilibrium_fraction": equil_frac,
        "asymmetry_diagnosis": asymmetry_note,
        "air_diagnosis": air_note,
        "ternary_stance": stance,
        "dominant_state": max(counts, key=counts.get).name
    }


# ======================================================================
# 2. QUANTUM HARMONIC SUPERPOSITION
# ======================================================================

@dataclass
class QuantumHarmonicSuperposition:
    """
    Harmonic overtones modeled as quantum superposition.
    
    Before spectral analysis (FFT), a complex tone does not "have"
    discrete harmonics. The waveform exists as a continuous superposition
    of all possible frequency components. The Fourier transform is a
    measurement that collapses this superposition into discrete bins.
    
    This matters because:
    - The bin spacing (frequency resolution) determines what can be "seen"
    - Harmonics between bins are invisible—structurally excluded
    - The measurement itself (window function, FFT size) shapes the result
    
    Key quantum analogues:
      |ψ(t)⟩ = Σ c_n |n·f₀⟩    (superposition over harmonics)
      Measurement = FFT with window function (collapses to bins)
      Heisenberg: Δt · Δf ≥ 1/(4π)  (time-frequency uncertainty)
    
    The binary encoder measures the fundamental frequency and
    discards the harmonic structure. The quantum representation
    preserves the full superposition—including the information
    that binary compression declares "noise."
    """
    
    frequencies: List[float]
    amplitudes: List[float]
    phases: List[float]
    
    # Analysis parameters
    fundamental_estimate: float = 0.0
    harmonic_amplitudes: Dict[int, complex] = field(default_factory=dict)
    superposition_entropy: float = 0.0
    collapsed_harmonics: List[int] = field(default_factory=list)
    excluded_energy_fraction: float = 0.0
    
    def __post_init__(self):
        if self.frequencies and self.amplitudes:
            self._compute_harmonic_superposition()
    
    def _compute_harmonic_superposition(self):
        """
        Compute harmonic superposition from frequency/amplitude data.
        
        Estimates the fundamental as the lowest significant frequency,
        then projects each frequency onto the harmonic series to
        determine which overtones are present and with what amplitude.
        """
        if not self.frequencies or len(self.frequencies) < 2:
            return
        
        # Estimate fundamental: lowest frequency with amplitude > 10% of max
        max_amp = max(self.amplitudes)
        significant = [
            (f, a) for f, a in zip(self.frequencies, self.amplitudes)
            if a >= 0.1 * max_amp
        ]
        
        if not significant:
            return
        
        # Fundamental is the lowest significant frequency
        self.fundamental_estimate = min(f for f, _ in significant)
        
        # Project onto harmonic series
        self.harmonic_amplitudes = {}
        for f, a, ph in zip(self.frequencies, self.amplitudes, self.phases):
            if self.fundamental_estimate > 0:
                harmonic_number = f / self.fundamental_estimate
                nearest_integer = round(harmonic_number)
                
                # Only assign if within 5% of an integer multiple
                if abs(harmonic_number - nearest_integer) < 0.05 * max(1, nearest_integer):
                    # Store as complex amplitude (magnitude + phase)
                    self.harmonic_amplitudes[nearest_integer] = complex(
                        a * math.cos(ph),
                        a * math.sin(ph)
                    )
        
        # Compute superposition entropy (von Neumann entropy over harmonic distribution)
        total_power = sum(abs(amp)**2 for amp in self.harmonic_amplitudes.values())
        if total_power > 0:
            probabilities = [abs(amp)**2 / total_power for amp in self.harmonic_amplitudes.values()]
            self.superposition_entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
        else:
            self.superposition_entropy = 0.0
        
        # Simulate measurement collapse: which harmonics survive binning?
        # A typical FFT with N points can only resolve harmonics up to N/2
        # Harmonics that fall between bins are structurally excluded
        self.collapsed_harmonics = sorted(self.harmonic_amplitudes.keys())
        
        # Excluded energy: harmonics that are present but not integer multiples
        total_energy = sum(a**2 for a in self.amplitudes)
        harmonic_energy = sum(abs(amp)**2 for amp in self.harmonic_amplitudes.values())
        self.excluded_energy_fraction = 1.0 - (harmonic_energy / total_energy) if total_energy > 0 else 0.0
    
    def measure_harmonic(self, n: int) -> Optional[complex]:
        """
        Collapse superposition to measure a specific harmonic.
        
        Returns the complex amplitude if the harmonic exists,
        None if it's not present in the superposition.
        """
        return self.harmonic_amplitudes.get(n)
    
    def measure_dominant(self) -> Tuple[int, complex]:
        """
        Collapse to the dominant harmonic (highest amplitude).
        
        Returns:
            (harmonic_number, complex_amplitude)
        """
        if not self.harmonic_amplitudes:
            return (0, complex(0, 0))
        
        dominant = max(self.harmonic_amplitudes, 
                      key=lambda k: abs(self.harmonic_amplitudes[k])**2)
        return (dominant, self.harmonic_amplitudes[dominant])
    
    def time_frequency_uncertainty(self, duration_seconds: float) -> Dict[str, float]:
        """
        Compute Heisenberg time-frequency uncertainty.
        
        Δt · Δf ≥ 1/(4π)
        
        For a sound of given duration, this gives the minimum
        frequency uncertainty—the fundamental limit on how
        precisely harmonics can be resolved.
        
        Args:
            duration_seconds: Duration of the sound sample
        
        Returns:
            Dict with frequency_resolution and uncertainty_product
        """
        delta_t = duration_seconds
        delta_f_min = 1.0 / (4 * math.pi * delta_t) if delta_t > 0 else float('inf')
        
        return {
            "time_resolution_s": delta_t,
            "frequency_resolution_hz": delta_f_min,
            "uncertainty_product": delta_t * delta_f_min,
            "heisenberg_limit": 1.0 / (4 * math.pi),
            "is_quantum_limited": abs(delta_t * delta_f_min - 1.0/(4*math.pi)) < 1e-10
        }
    
    def diagnose(self) -> str:
        """Human-readable quantum harmonic diagnosis."""
        if not self.harmonic_amplitudes:
            return "No harmonic structure detected—possibly a pure tone or noise."
        
        n_harmonics = len(self.harmonic_amplitudes)
        dominant_n, dominant_amp = self.measure_dominant()
        dominant_freq = dominant_n * self.fundamental_estimate if self.fundamental_estimate > 0 else 0
        
        diagnosis = (
            f"Fundamental: {self.fundamental_estimate:.1f} Hz. "
            f"{n_harmonics} harmonics detected in superposition. "
        )
        
        if self.superposition_entropy > 2.0:
            diagnosis += (
                f"High harmonic entropy ({self.superposition_entropy:.2f} bits): "
                f"energy distributed across many overtones. Rich timbre, "
                f"complex waveform—characteristic of natural sources or "
                f"resonant bodies with multiple modes."
            )
        elif self.superposition_entropy > 1.0:
            diagnosis += (
                f"Moderate harmonic entropy ({self.superposition_entropy:.2f} bits): "
                f"balanced harmonic distribution."
            )
        else:
            diagnosis += (
                f"Low harmonic entropy ({self.superposition_entropy:.2f} bits): "
                f"energy concentrated in few harmonics. Pure or near-pure tone, "
                f"or strongly filtered source."
            )
        
        if self.excluded_energy_fraction > 0.2:
            diagnosis += (
                f" WARNING: {self.excluded_energy_fraction:.1%} of total energy "
                f"is in non-integer harmonics—this energy would be structurally "
                f"excluded by bin-based spectral analysis. The binary encoding "
                f"discards this as 'noise' but it carries physical information "
                f"about inharmonicity, nonlinear propagation, or measurement artifacts."
            )
        
        return diagnosis


# ======================================================================
# 3. STOCHASTIC JITTER PRESERVATION
# ======================================================================

@dataclass
class StochasticJitterPreservation:
    """
    Thermal jitter as information carrier, not noise.
    
    Binary systems filter low-level stochastic variation as "noise"
    to be removed. But in physical systems, this jitter carries
    information about the hardware state:
    
    - Thermal energy (k_B*T) sets the noise floor
    - Component aging changes the noise spectrum
    - Mechanical coupling introduces correlated jitter
    - Environmental factors (temperature, humidity, pressure)
      shift the jitter characteristics
    
    The Sound Bridge Encoder's note about cellphone DACs is exactly
    this: the phone's energy-saving algorithms strip the very
    analog details that carry the most information about the
    physical system state.
    
    Preserving jitter = preserving model/reality coupling.
    """
    
    phase_radians: List[float]
    amplitude: List[float]
    frequency_hz: List[float]
    
    # Jitter statistics
    phase_jitter_rms: float = 0.0
    amplitude_jitter_rms: float = 0.0
    frequency_jitter_rms: float = 0.0
    
    # Thermal estimates
    estimated_temperature_k: float = 0.0
    jitter_entropy_bits: float = 0.0
    
    # Information preservation
    information_loss_from_filtering: float = 0.0
    
    def __post_init__(self):
        if len(self.phase_radians) >= 2:
            self._compute_jitter_statistics()
    
    def _compute_jitter_statistics(self):
        """
        Compute jitter statistics from sequence data.
        
        Jitter = sample-to-sample variation that binary systems
        would filter as "noise" but which carries physical information.
        """
        n = len(self.phase_radians)
        
        # Phase jitter: difference between consecutive phase readings
        # minus the expected phase advance (2π * f / sample_rate)
        if n >= 2:
            phase_diffs = []
            amp_diffs = []
            freq_diffs = []
            
            for i in range(1, n):
                # Phase difference
                diff = self.phase_radians[i] - self.phase_radians[i-1]
                # Normalize to [-π, π]
                while diff > math.pi:
                    diff -= 2 * math.pi
                while diff < -math.pi:
                    diff += 2 * math.pi
                phase_diffs.append(diff)
                
                # Amplitude difference
                amp_diffs.append(self.amplitude[i] - self.amplitude[i-1])
                
                # Frequency difference
                if self.frequency_hz and i < len(self.frequency_hz):
                    freq_diffs.append(
                        self.frequency_hz[i] - self.frequency_hz[i-1]
                    )
            
            # RMS jitter
            if phase_diffs:
                mean_phase_diff = sum(phase_diffs) / len(phase_diffs)
                self.phase_jitter_rms = math.sqrt(
                    sum((d - mean_phase_diff)**2 for d in phase_diffs) / len(phase_diffs)
                )
            
            if amp_diffs:
                mean_amp_diff = sum(amp_diffs) / len(amp_diffs)
                self.amplitude_jitter_rms = math.sqrt(
                    sum((d - mean_amp_diff)**2 for d in amp_diffs) / len(amp_diffs)
                )
            
            if freq_diffs:
                mean_freq_diff = sum(freq_diffs) / len(freq_diffs)
                self.frequency_jitter_rms = math.sqrt(
                    sum((d - mean_freq_diff)**2 for d in freq_diffs) / len(freq_diffs)
                )
        
        # Estimate temperature from jitter (k_B*T model)
        # Phase jitter ∝ sqrt(k_B * T / E_signal)
        # Simplified: T_estimate = (phase_jitter_rms * scaling_factor)²
        scaling = 1e6  # Arbitrary scaling for demonstration
        self.estimated_temperature_k = (self.phase_jitter_rms * scaling)**2 + 273
        
        # Jitter entropy: how much information is in the jitter?
        # Assuming Gaussian jitter: entropy = 0.5 * log2(2πe * σ²)
        if self.phase_jitter_rms > 0:
            self.jitter_entropy_bits = 0.5 * math.log2(
                2 * math.pi * math.e * self.phase_jitter_rms**2
            )
        
        # Information loss if jitter were filtered
        # (percentage of total entropy in the signal)
        if self.jitter_entropy_bits > 0:
            # Assume signal has ~8 bits of entropy per sample
            self.information_loss_from_filtering = min(
                1.0, self.jitter_entropy_bits / 8.0
            )
    
    def diagnose(self) -> str:
        """Human-readable jitter preservation diagnosis."""
        if self.phase_jitter_rms == 0:
            return "No jitter detected—signal may be synthetic or already filtered."
        
        diagnosis = (
            f"Phase jitter RMS: {self.phase_jitter_rms:.6f} rad. "
            f"Amplitude jitter RMS: {self.amplitude_jitter_rms:.6f}. "
        )
        
        if self.estimated_temperature_k > 300:
            diagnosis += (
                f"Estimated thermal state: {self.estimated_temperature_k:.0f} K "
                f"({self.estimated_temperature_k - 273:.0f}°C). "
            )
        
        if self.information_loss_from_filtering > 0.5:
            diagnosis += (
                f"CRITICAL: Filtering this jitter would discard "
                f"{self.information_loss_from_filtering:.1%} of total "
                f"signal information. The 'noise' IS the signal—it carries "
                f"the hardware's thermal state, component aging, and "
                f"environmental coupling. Binary systems that smooth this "
                f"jitter are actively destroying model/reality coherence."
            )
        elif self.information_loss_from_filtering > 0.2:
            diagnosis += (
                f"SIGNIFICANT: Filtering would discard "
                f"{self.information_loss_from_filtering:.1%} of information. "
                f"The jitter contains physically meaningful variation."
            )
        else:
            diagnosis += (
                f"Low jitter: signal is clean. "
                f"Information loss from filtering would be "
                f"{self.information_loss_from_filtering:.1%}—acceptable "
                f"for most applications, though still physically meaningful."
            )
        
        return diagnosis


# ======================================================================
# 4. COMPOSITE SOUND DIAGNOSTIC
# ======================================================================

@dataclass
class SoundAlternativeDiagnostic:
    """
    Complete alternative computing diagnostic for a sound sample.
    
    Aggregates ternary phase analysis, quantum harmonic superposition,
    and stochastic jitter preservation into a single report.
    """
    
    # Ternary phase analysis
    ternary_phase_distribution: Dict[str, Any] = field(default_factory=dict)
    
    # Quantum harmonic superposition
    quantum_harmonics: Optional[QuantumHarmonicSuperposition] = None
    
    # Stochastic jitter
    stochastic_jitter: Optional[StochasticJitterPreservation] = None
    
    # Binary encoding reference
    binary_encoding: Optional[str] = None
    
    def summary(self) -> str:
        """Multi-line diagnostic summary."""
        lines = [
            f"{'='*60}",
            "Sound Alternative Diagnostic",
            f"{'='*60}",
            "",
            "TERNARY PHASE ANALYSIS:",
        ]
        
        if self.ternary_phase_distribution:
            td = self.ternary_phase_distribution
            if "ternary_fractions" in td:
                for state, frac in td["ternary_fractions"].items():
                    bar = '█' * int(frac * 40)
                    lines.append(f"  {state:15s}: {bar} {frac:.1%}")
                
                lines.append(f"  Symmetry score: {td.get('symmetry_score', 0):.2f}")
                lines.append(f"  Stance: {td.get('ternary_stance', 'UNKNOWN')}")
                lines.append(f"  {td.get('asymmetry_diagnosis', '')}")
                lines.append(f"  {td.get('air_diagnosis', '')}")
            else:
                lines.append(f"  {td.get('error', 'No data')}")
        else:
            lines.append("  No phase data available")
        
        lines.append("")
        lines.append("QUANTUM HARMONIC SUPERPOSITION:")
        
        if self.quantum_harmonics:
            qh = self.quantum_harmonics
            lines.append(f"  Fundamental estimate: {qh.fundamental_estimate:.1f} Hz")
            lines.append(f"  Harmonics in superposition: {len(qh.harmonic_amplitudes)}")
            
            if qh.harmonic_amplitudes:
                for n in sorted(qh.harmonic_amplitudes.keys())[:10]:  # Top 10
                    amp = qh.harmonic_amplitudes[n]
                    power = abs(amp)**2
                    bar = '█' * int(power * 20 / max(abs(a)**2 for a in qh.harmonic_amplitudes.values()))
                    lines.append(f"    Harmonic {n:2d}: {bar} ({power:.4f})")
                
                if len(qh.harmonic_amplitudes) > 10:
                    lines.append(f"    ... and {len(qh.harmonic_amplitudes) - 10} more")
            
            lines.append(f"  Superposition entropy: {qh.superposition_entropy:.2f} bits")
            lines.append(f"  Excluded energy fraction: {qh.excluded_energy_fraction:.1%}")
            lines.append(f"  {qh.diagnose()}")
        else:
            lines.append("  No harmonic data available")
        
        lines.append("")
        lines.append("STOCHASTIC JITTER PRESERVATION:")
        
        if self.stochastic_jitter:
            sj = self.stochastic_jitter
            lines.append(f"  Phase jitter RMS: {sj.phase_jitter_rms:.6f} rad")
            lines.append(f"  Amplitude jitter RMS: {sj.amplitude_jitter_rms:.6f}")
            lines.append(f"  Frequency jitter RMS: {sj.frequency_jitter_rms:.4f} Hz")
            lines.append(f"  Estimated temperature: {sj.estimated_temperature_k:.0f} K ({sj.estimated_temperature_k - 273:.0f}°C)")
            lines.append(f"  Jitter entropy: {sj.jitter_entropy_bits:.2f} bits/sample")
            lines.append(f"  Information loss if filtered: {sj.information_loss_from_filtering:.1%}")
            lines.append(f"  {sj.diagnose()}")
        else:
            lines.append("  No jitter data available")
        
        if self.binary_encoding:
            lines.append(f"\nBINARY ENCODING (for reference):")
            lines.append(f"  {len(self.binary_encoding)} bits: {self.binary_encoding[:80]}...")
        
        lines.append(f"\n{'='*60}")
        return '\n'.join(lines)


def sound_ternary_diagnostic(phase_radians: List[float]) -> Dict[str, Any]:
    """
    Quick ternary phase diagnostic from phase data alone.
    
    Args:
        phase_radians: List of instantaneous phase values [0, 2π)
    
    Returns:
        Ternary phase distribution dict
    """
    return compute_ternary_phase_distribution(phase_radians)


def sound_quantum_diagnostic(frequencies: List[float],
                             amplitudes: List[float],
                             phases: List[float],
                             duration_seconds: float = 1.0) -> QuantumHarmonicSuperposition:
    """
    Quick quantum harmonic diagnostic from frequency/amplitude/phase data.
    
    Args:
        frequencies: List of frequency values in Hz
        amplitudes: List of amplitude values
        phases: List of phase values in radians
        duration_seconds: Duration of sound sample for uncertainty calculation
    
    Returns:
        QuantumHarmonicSuperposition with analysis
    """
    qh = QuantumHarmonicSuperposition(
        frequencies=frequencies,
        amplitudes=amplitudes,
        phases=phases
    )
    
    # Attach uncertainty analysis
    uncertainty = qh.time_frequency_uncertainty(duration_seconds)
    qh.frequency_resolution = uncertainty["frequency_resolution_hz"]
    
    return qh


def sound_full_alternative_diagnostic(geometry: Dict[str, Any]) -> SoundAlternativeDiagnostic:
    """
    Generate complete alternative computing diagnostic for a sound sample.
    
    Args:
        geometry: Dict with keys phase_radians, frequency_hz, amplitude, resonance_index
                  (same format accepted by SoundBridgeEncoder)
    
    Returns:
        SoundAlternativeDiagnostic with all analyses
    """
    phases = geometry.get("phase_radians", [])
    freqs = geometry.get("frequency_hz", [])
    amps = geometry.get("amplitude", [])
    
    diag = SoundAlternativeDiagnostic()
    
    # Ternary phase analysis
    if phases:
        diag.ternary_phase_distribution = compute_ternary_phase_distribution(phases)
    
    # Quantum harmonic superposition
    if freqs and amps and phases:
        diag.quantum_harmonics = QuantumHarmonicSuperposition(
            frequencies=freqs,
            amplitudes=amps,
            phases=phases
        )
    
    # Stochastic jitter preservation
    if phases and amps and len(phases) >= 2:
        diag.stochastic_jitter = StochasticJitterPreservation(
            phase_radians=phases,
            amplitude=amps,
            frequency_hz=freqs
        )
    
    # Binary encoding reference
    try:
        from bridges.sound_encoder import SoundBridgeEncoder
        encoder = SoundBridgeEncoder()
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
    print("Sound Alternative Computing — Ternary & Quantum Demo")
    print("=" * 60)
    
    # Demo geometry (same as Sound Bridge Encoder demo)
    geometry = {
        "phase_radians":  [0.3,  1.8,  3.5,  0.8,  2.1,  4.2,  1.5,  3.0],
        "frequency_hz":   [261.63, 440.0, 880.0, 261.63, 440.0, 880.0, 523.25, 659.25],
        "amplitude":      [0.8,  0.4,  0.6,  0.7,  0.35, 0.55, 0.5,  0.45],
        "resonance_index": [0.75, 0.3, 0.9, 0.6, 0.25, 0.85, 0.7, 0.4],
    }
    
    diag = sound_full_alternative_diagnostic(geometry)
    print(diag.summary())
    
    print("\n" + "=" * 60)
    print("Individual quick diagnostics:")
    print("=" * 60)
    
    # Quick ternary
    ternary = sound_ternary_diagnostic(geometry["phase_radians"])
    print(f"\nTernary stance: {ternary.get('ternary_stance', 'UNKNOWN')}")
    print(f"Dominant state: {ternary.get('dominant_state', 'UNKNOWN')}")
    
    # Quick quantum
    quantum = sound_quantum_diagnostic(
        geometry["frequency_hz"],
        geometry["amplitude"],
        geometry["phase_radians"]
    )
    print(f"\nQuantum harmonics detected: {len(quantum.harmonic_amplitudes)}")
    print(f"Fundamental: {quantum.fundamental_estimate:.1f} Hz")
    print(f"Superposition entropy: {quantum.superposition_entropy:.2f} bits")
    dominant_n, _ = quantum.measure_dominant()
    print(f"Dominant harmonic: {dominant_n}")
