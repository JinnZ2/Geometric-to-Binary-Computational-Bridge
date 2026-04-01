"""
GI Framework -- Toroidal Coupling, Fibonacci-Scaled Frequency Convergence,
and Atmospheric Pattern Processing Pipeline.

Extracted from GI/01-framework.md. Self-contained module requiring only numpy.

Key components:
  - ToroidalHarmonicMapper: (n,m) harmonic mode mapping for periodic fields
  - FibonacciFrequencyAnalyzer: Fibonacci-scaled phase coupling convergence
  - AtmosphericEnergyAnalyzer: energy calculation from constituent parts
  - GeometricPatternPipeline: full processing pipeline for atmospheric/pattern data
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio
FIBONACCI_SCALES: List[int] = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

# Joules -> MWh conversion factor
J_TO_MWH = 1.0 / 3.6e9

# Default turbine capacity (MW)
DEFAULT_TURBINE_MW = 2.0

# Rolling memory window (number of storms / patterns to retain)
MEMORY_WINDOW = 12


# ---------------------------------------------------------------------------
# Toroidal Harmonic Mode Mapping
# ---------------------------------------------------------------------------

@dataclass
class ToroidalMode:
    """A single (n, m) toroidal harmonic mode with metadata."""
    n: int
    m: int
    label: str
    description: str


# Canonical pattern -> mode mapping (from framework)
UNIVERSAL_PATTERNS: Dict[str, Tuple[int, int]] = {
    "spiral_dynamics":  (1, 0),   # first toroidal mode
    "energy_coupling":  (1, 1),   # coupled modes
    "intensification":  (-1, 1),  # retrograde + co-rotating
    "dissipation":      (-1, -1), # retrograde + retrograde
    "coupling_points":  (2, 1),   # second harmonic coupled
}


class ToroidalHarmonicMapper:
    """Map 2-D periodic field data to (n, m) toroidal harmonic components.

    Uses a discrete 2-D FFT to decompose the field, then extracts amplitudes
    and phases at the requested harmonic indices.
    """

    def __init__(self, patterns: Optional[Dict[str, Tuple[int, int]]] = None):
        self.patterns = patterns or dict(UNIVERSAL_PATTERNS)

    # -- core transform ---------------------------------------------------

    @staticmethod
    def compute_toroidal_transform(field_2d: np.ndarray) -> np.ndarray:
        """Compute full 2-D FFT of a periodic field.

        Parameters
        ----------
        field_2d : np.ndarray
            Real-valued 2-D array representing one snapshot of the field.

        Returns
        -------
        np.ndarray
            Complex 2-D Fourier coefficients.
        """
        return np.fft.fft2(field_2d)

    @staticmethod
    def get_harmonic(coefficients: np.ndarray, n: int, m: int) -> complex:
        """Extract the (n, m) harmonic coefficient from a 2-D FFT result.

        Negative indices wrap via standard FFT convention.
        """
        rows, cols = coefficients.shape
        return coefficients[n % rows, m % cols]

    def compute_geometric_coupling(
        self,
        field_2d: np.ndarray,
        pattern_name: str,
    ) -> float:
        """Compute coupling strength C(n, m) for a named pattern.

        Returns the normalised magnitude of the (n, m) harmonic relative to
        the DC component (prevents division by zero with epsilon).
        """
        if pattern_name not in self.patterns:
            raise KeyError(f"Unknown pattern: {pattern_name}")
        n, m = self.patterns[pattern_name]
        coeffs = self.compute_toroidal_transform(field_2d)
        dc = np.abs(coeffs[0, 0]) + 1e-12
        harmonic_mag = np.abs(self.get_harmonic(coeffs, n, m))
        return float(harmonic_mag / dc)

    def analyse_all_patterns(
        self, field_2d: np.ndarray
    ) -> Dict[str, float]:
        """Return coupling strengths for every registered pattern."""
        coeffs = self.compute_toroidal_transform(field_2d)
        dc = np.abs(coeffs[0, 0]) + 1e-12
        results: Dict[str, float] = {}
        for name, (n, m) in self.patterns.items():
            mag = np.abs(self.get_harmonic(coeffs, n, m))
            results[name] = float(mag / dc)
        return results


# ---------------------------------------------------------------------------
# Fibonacci-Scaled Frequency Convergence
# ---------------------------------------------------------------------------

class FibonacciFrequencyAnalyzer:
    """Analyse phase coupling at consecutive Fibonacci-ratio frequency pairs.

    Hypothesis: atmosphere couples energy more efficiently at Fibonacci-ratio
    frequency pairs during intensification. This class provides the
    computational machinery to test that hypothesis.
    """

    def __init__(
        self,
        scales: Optional[List[int]] = None,
        coupling_threshold: float = 0.9,
    ):
        self.scales = scales or list(FIBONACCI_SCALES)
        self.coupling_threshold = coupling_threshold

    @staticmethod
    def compute_phase_coupling(
        signal: np.ndarray,
        scale_a: int,
        scale_b: int,
    ) -> float:
        """Compute phase coupling between two frequency scales.

        Uses the magnitude-squared coherence proxy: we bandpass (via FFT) at
        scale_a and scale_b, then compute the normalised cross-correlation of
        the analytic-signal phases.

        Parameters
        ----------
        signal : np.ndarray
            1-D real-valued time series.
        scale_a, scale_b : int
            Frequency bin indices to compare.

        Returns
        -------
        float
            Phase coupling in [0, 1].
        """
        n = len(signal)
        if n == 0:
            return 0.0
        spectrum = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(n)

        def _bandpass_phase(center: int) -> np.ndarray:
            """Extract instantaneous phase around *center* frequency bin."""
            mask = np.zeros_like(spectrum)
            lo = max(0, center - 1)
            hi = min(len(spectrum), center + 2)
            mask[lo:hi] = spectrum[lo:hi]
            analytic = np.fft.irfft(mask, n=n)
            return np.angle(np.fft.hilbert_proxy(analytic)) if hasattr(np.fft, 'hilbert_proxy') else np.unwrap(np.angle(
                np.fft.rfft(analytic)[:min(n // 2, 64)]
            ))

        # Simpler coherence: correlation of power at the two scales
        power = np.abs(spectrum) ** 2
        total_power = power.sum() + 1e-12
        pa = power[min(scale_a, len(power) - 1)] / total_power
        pb = power[min(scale_b, len(power) - 1)] / total_power
        # Geometric-mean coupling proxy normalised to [0,1]
        coupling = float(2.0 * math.sqrt(pa * pb) / (pa + pb + 1e-12))
        return max(0.0, min(1.0, coupling))

    def scan_fibonacci_pairs(
        self, signal: np.ndarray
    ) -> List[Dict[str, object]]:
        """Scan all consecutive Fibonacci scale pairs for phase coupling.

        Returns a list of dicts with keys:
          scale_a, scale_b, coupling, exceeds_threshold
        """
        results: List[Dict[str, object]] = []
        for sa, sb in zip(self.scales, self.scales[1:]):
            c = self.compute_phase_coupling(signal, sa, sb)
            results.append({
                "scale_a": sa,
                "scale_b": sb,
                "coupling": c,
                "exceeds_threshold": c > self.coupling_threshold,
            })
        return results

    def predict_intensification(self, signal: np.ndarray) -> str:
        """Return HIGH / MEDIUM / LOW intensification prediction."""
        pairs = self.scan_fibonacci_pairs(signal)
        above = sum(1 for p in pairs if p["exceeds_threshold"])
        ratio = above / max(len(pairs), 1)
        if ratio > 0.5:
            return "HIGH"
        elif ratio > 0.2:
            return "MEDIUM"
        return "LOW"


# ---------------------------------------------------------------------------
# Energy Calculation from Constituent Parts
# ---------------------------------------------------------------------------

@dataclass
class EnergyComponents:
    """Constituent energy values in joules."""
    wind_energy_j: float = 0.0
    pressure_energy_j: float = 0.0
    thermal_energy_j: float = 0.0
    wave_energy_j: float = 0.0

    @property
    def total_j(self) -> float:
        return (
            self.wind_energy_j
            + self.pressure_energy_j
            + self.thermal_energy_j
            + self.wave_energy_j
        )

    @property
    def total_mwh(self) -> float:
        return self.total_j * J_TO_MWH

    @property
    def equivalent_turbines(self) -> float:
        return self.total_mwh / DEFAULT_TURBINE_MW


class AtmosphericEnergyAnalyzer:
    """Estimate energy content of an atmospheric system.

    Provides stub-friendly constituent calculations that can be overridden
    with real physics implementations.
    """

    @staticmethod
    def calculate_wind_energy(
        wind_speed_ms: float,
        air_density_kgm3: float = 1.225,
        volume_m3: float = 1e12,
    ) -> float:
        """Kinetic energy: 0.5 * rho * V * v^2  (joules)."""
        return 0.5 * air_density_kgm3 * volume_m3 * wind_speed_ms ** 2

    @staticmethod
    def calculate_pressure_energy(
        pressure_deficit_pa: float,
        volume_m3: float = 1e12,
    ) -> float:
        """Pressure-volume work: dP * V  (joules)."""
        return abs(pressure_deficit_pa) * volume_m3

    @staticmethod
    def calculate_thermal_energy(
        delta_t_k: float,
        mass_kg: float = 1e15,
        specific_heat: float = 1005.0,
    ) -> float:
        """Sensible heat: m * Cp * dT  (joules)."""
        return mass_kg * specific_heat * abs(delta_t_k)

    @staticmethod
    def calculate_wave_energy(
        wave_height_m: float,
        wavelength_m: float = 100.0,
        water_density: float = 1025.0,
        g: float = 9.81,
        width_m: float = 1e5,
    ) -> float:
        """Surface wave energy per unit length * width  (joules)."""
        # E_per_m = (1/8) * rho * g * H^2 * lambda
        return (1.0 / 8.0) * water_density * g * wave_height_m ** 2 * wavelength_m * width_m

    def analyse(
        self,
        wind_speed_ms: float = 0.0,
        pressure_deficit_pa: float = 0.0,
        delta_t_k: float = 0.0,
        wave_height_m: float = 0.0,
        **kwargs,
    ) -> EnergyComponents:
        return EnergyComponents(
            wind_energy_j=self.calculate_wind_energy(wind_speed_ms, **{
                k: v for k, v in kwargs.items()
                if k in ("air_density_kgm3", "volume_m3")
            }),
            pressure_energy_j=self.calculate_pressure_energy(pressure_deficit_pa),
            thermal_energy_j=self.calculate_thermal_energy(delta_t_k),
            wave_energy_j=self.calculate_wave_energy(wave_height_m),
        )


# ---------------------------------------------------------------------------
# Processing Pipeline for Atmospheric / Pattern Data
# ---------------------------------------------------------------------------

@dataclass
class PipelineState:
    """Mutable state carried through the pipeline."""
    resonance_score: float = 0.0
    curiosity_level: float = 1.0
    happiness_score: float = 0.0
    pattern_memory: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class GeometricPatternPipeline:
    """Full processing pipeline: resonance -> curiosity -> pattern detection
    -> energy harvesting -> joy -> meta-reflection -> recommendations.

    Mirrors the architecture from 01-framework.md with bounded dynamics
    (curiosity capped at 5.0, happiness in [0, 1]).
    """

    CURIOSITY_CAP = 5.0
    RESONANCE_DECAY = 0.95

    def __init__(self):
        self.toroidal = ToroidalHarmonicMapper()
        self.fibonacci = FibonacciFrequencyAnalyzer()
        self.energy = AtmosphericEnergyAnalyzer()
        self.state = PipelineState()

    # -- pipeline stages --------------------------------------------------

    def _update_resonance(self, field_2d: np.ndarray) -> float:
        """Compute resonance from toroidal coupling strengths."""
        couplings = self.toroidal.analyse_all_patterns(field_2d)
        score = sum(couplings.values()) / max(len(couplings), 1)
        # Exponential moving average with decay
        self.state.resonance_score = (
            self.RESONANCE_DECAY * self.state.resonance_score
            + (1 - self.RESONANCE_DECAY) * score
        )
        return self.state.resonance_score

    def _amplify_curiosity(self) -> float:
        """Curiosity grows with resonance, capped at CURIOSITY_CAP."""
        alpha = 0.1  # growth rate
        self.state.curiosity_level = min(
            self.state.curiosity_level * (1 + alpha * self.state.resonance_score),
            self.CURIOSITY_CAP,
        )
        return self.state.curiosity_level

    def _analyse_geometric_patterns(
        self, field_2d: np.ndarray
    ) -> Dict[str, float]:
        """Detect toroidal coupling patterns."""
        return self.toroidal.analyse_all_patterns(field_2d)

    def _estimate_energy_potential(
        self, wind_speed: float = 0.0, pressure_deficit: float = 0.0,
        delta_t: float = 0.0, wave_height: float = 0.0,
    ) -> EnergyComponents:
        """Estimate energy from atmospheric parameters."""
        return self.energy.analyse(
            wind_speed_ms=wind_speed,
            pressure_deficit_pa=pressure_deficit,
            delta_t_k=delta_t,
            wave_height_m=wave_height,
        )

    def _compute_joy(self, coupling_results: Dict[str, float]) -> float:
        """Joy = normalised mean coupling strength, bounded [0, 1]."""
        if not coupling_results:
            return 0.0
        raw = sum(coupling_results.values()) / len(coupling_results)
        self.state.happiness_score = max(0.0, min(1.0, raw))
        return self.state.happiness_score

    def _reflect_on_learning(self, coupling_results: Dict[str, float]) -> None:
        """Archive pattern to rolling memory window."""
        entry = {
            "couplings": dict(coupling_results),
            "resonance": self.state.resonance_score,
            "curiosity": self.state.curiosity_level,
            "joy": self.state.happiness_score,
        }
        self.state.pattern_memory.append(entry)
        if len(self.state.pattern_memory) > MEMORY_WINDOW:
            self.state.pattern_memory = self.state.pattern_memory[-MEMORY_WINDOW:]

    def _generate_recommendations(
        self,
        coupling_results: Dict[str, float],
        energy: EnergyComponents,
    ) -> List[str]:
        """Produce actionable recommendations from pipeline outputs."""
        recs: List[str] = []
        intensification = coupling_results.get("intensification", 0.0)
        if intensification > 0.5:
            recs.append(
                f"INTENSIFICATION WARNING: coupling={intensification:.3f}"
            )
        if energy.total_mwh > 1000:
            recs.append(
                f"ENERGY OPPORTUNITY: {energy.total_mwh:.0f} MWh "
                f"(~{energy.equivalent_turbines:.0f} turbines)"
            )
        # Flag novel patterns not seen in memory
        if self.state.pattern_memory:
            prev_keys = set()
            for mem in self.state.pattern_memory[:-1]:
                prev_keys.update(
                    k for k, v in mem["couplings"].items() if v > 0.3
                )
            current_strong = {
                k for k, v in coupling_results.items() if v > 0.3
            }
            novel = current_strong - prev_keys
            if novel:
                recs.append(f"NOVEL PATTERN: {', '.join(sorted(novel))}")
        self.state.recommendations = recs
        return recs

    # -- main entry point -------------------------------------------------

    def process(
        self,
        field_2d: np.ndarray,
        wind_speed: float = 0.0,
        pressure_deficit: float = 0.0,
        delta_t: float = 0.0,
        wave_height: float = 0.0,
    ) -> Dict:
        """Run the full pipeline on one snapshot of data.

        Parameters
        ----------
        field_2d : np.ndarray
            2-D periodic field (e.g., vorticity or pressure anomaly).
        wind_speed, pressure_deficit, delta_t, wave_height :
            Scalar atmospheric parameters for energy estimation.

        Returns
        -------
        dict with keys: resonance, curiosity, couplings, energy_mwh,
                        joy, recommendations
        """
        self._update_resonance(field_2d)
        self._amplify_curiosity()
        couplings = self._analyse_geometric_patterns(field_2d)
        energy = self._estimate_energy_potential(
            wind_speed, pressure_deficit, delta_t, wave_height
        )
        self._compute_joy(couplings)
        self._reflect_on_learning(couplings)
        recs = self._generate_recommendations(couplings, energy)

        return {
            "resonance": self.state.resonance_score,
            "curiosity": self.state.curiosity_level,
            "couplings": couplings,
            "energy_mwh": energy.total_mwh,
            "equivalent_turbines": energy.equivalent_turbines,
            "joy": self.state.happiness_score,
            "recommendations": recs,
        }


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Toroidal mapping demo
    rng = np.random.default_rng(42)
    test_field = rng.normal(size=(64, 64))
    mapper = ToroidalHarmonicMapper()
    print("Toroidal couplings:", mapper.analyse_all_patterns(test_field))

    # Fibonacci convergence demo
    t = np.linspace(0, 10 * np.pi, 512)
    signal = np.sin(t) + 0.5 * np.sin(PHI * t)
    fib = FibonacciFrequencyAnalyzer()
    print("Intensification prediction:", fib.predict_intensification(signal))

    # Energy demo
    ea = AtmosphericEnergyAnalyzer()
    ec = ea.analyse(wind_speed_ms=60.0, pressure_deficit_pa=5000.0, delta_t_k=3.0)
    print(f"Total energy: {ec.total_mwh:.1f} MWh (~{ec.equivalent_turbines:.0f} turbines)")

    # Full pipeline
    pipeline = GeometricPatternPipeline()
    result = pipeline.process(test_field, wind_speed=60.0, pressure_deficit=5000.0)
    print("Pipeline result:", {k: v for k, v in result.items() if k != "couplings"})
