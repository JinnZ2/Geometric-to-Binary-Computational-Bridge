"""
GI Framework -- Toroidal Harmonic Analysis & Processing Pipeline

Extracted from GI/01-framework.md.  Implements:
  - Toroidal harmonic mode mapping  (GeometricPatternDetector)
  - Fibonacci-scaled frequency convergence
  - Phase coupling computation
  - Atmospheric energy calculation from constituent parts
  - Processing pipeline for atmospheric / pattern data
"""

import math
import numpy as np
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2          # golden ratio
JOULES_PER_MWH = 3.6e9                # J -> MWh conversion factor
DEFAULT_TURBINE_MW = 2.0               # modern onshore average


# ---------------------------------------------------------------------------
# Toroidal Harmonic Mode Mapping
# ---------------------------------------------------------------------------

class GeometricPatternDetector:
    """Toroidal (n, m) harmonic decomposition for 2-D periodic fields.

    The universal_patterns dict maps human-readable pattern names to
    (n, m) toroidal mode pairs.  The detector can compute a 2-D FFT-based
    toroidal transform and extract coupling strength for each named mode.
    """

    universal_patterns: Dict[str, Tuple[int, int]] = {
        "spiral_dynamics":  (1, 0),    # first toroidal mode
        "energy_coupling":  (1, 1),    # coupled modes
        "intensification":  (-1, 1),   # retrograde + co-rotating
        "dissipation":      (-1, -1),  # retrograde + retrograde
        "coupling_points":  (2, 1),    # second harmonic coupled
    }

    def __init__(self, field: Optional[np.ndarray] = None):
        """
        Parameters
        ----------
        field : 2-D ndarray, optional
            Periodic scalar field (e.g. vorticity, pressure perturbation).
        """
        self._field = field
        self._spectrum: Optional[np.ndarray] = None

    # -- transform ----------------------------------------------------------

    def set_field(self, field: np.ndarray) -> None:
        """Load or replace the 2-D field and invalidate cached spectrum."""
        self._field = np.asarray(field, dtype=float)
        self._spectrum = None

    def _compute_toroidal_transform(self) -> np.ndarray:
        """2-D FFT of the stored field, cached for repeated look-ups."""
        if self._field is None:
            raise ValueError("No field loaded -- call set_field() first.")
        if self._spectrum is None:
            self._spectrum = np.fft.fft2(self._field)
        return self._spectrum

    def get_harmonic(self, n: int, m: int) -> complex:
        """Return the complex coefficient for toroidal mode (n, m).

        For a field of shape (N, M), index mapping is:
            row = n % N   (handles negative n via Python wraparound)
            col = m % M
        """
        spectrum = self._compute_toroidal_transform()
        N, M = spectrum.shape
        return spectrum[n % N, m % M]

    def _compute_geometric_coupling(self, n: int, m: int) -> float:
        """Magnitude of the (n, m) harmonic normalised by total power."""
        spectrum = self._compute_toroidal_transform()
        total_power = np.sum(np.abs(spectrum) ** 2)
        if total_power == 0:
            return 0.0
        mode_power = np.abs(self.get_harmonic(n, m)) ** 2
        return float(mode_power / total_power)

    def analyze_patterns(self) -> Dict[str, float]:
        """Return coupling strength for every named universal pattern."""
        return {
            name: self._compute_geometric_coupling(n, m)
            for name, (n, m) in self.universal_patterns.items()
        }


# ---------------------------------------------------------------------------
# Phase Coupling Computation
# ---------------------------------------------------------------------------

def compute_phase_coupling(data: np.ndarray,
                           scale_a: int,
                           scale_b: int) -> float:
    """Phase coupling between two frequency scales in a 1-D signal.

    Uses the analytic signal (Hilbert transform) to extract instantaneous
    phase at each scale, then returns the mean phase-locking value (PLV)
    between the two.

    Parameters
    ----------
    data : 1-D array
        Real-valued time series.
    scale_a, scale_b : int
        Frequency scales (period in samples).  The signal is band-pass
        filtered around 1/scale_a and 1/scale_b.

    Returns
    -------
    float in [0, 1] -- 1 means perfect phase locking.
    """
    from scipy.signal import hilbert, butter, sosfiltfilt

    data = np.asarray(data, dtype=float)
    N = len(data)
    if N < max(scale_a, scale_b) * 4:
        return 0.0

    fs = 1.0  # normalised sampling rate

    def _bandpass_phase(scale: int) -> np.ndarray:
        f_center = 1.0 / scale
        bw = f_center * 0.4  # 40 % fractional bandwidth
        low = max(f_center - bw, 1e-6)
        high = min(f_center + bw, 0.5 - 1e-6)
        if low >= high:
            return np.zeros(N)
        sos = butter(4, [low, high], btype="band", fs=fs, output="sos")
        filtered = sosfiltfilt(sos, data)
        analytic = hilbert(filtered)
        return np.angle(analytic)

    phase_a = _bandpass_phase(scale_a)
    phase_b = _bandpass_phase(scale_b)

    # Phase-locking value
    phase_diff = phase_a - phase_b
    plv = float(np.abs(np.mean(np.exp(1j * phase_diff))))
    return plv


# ---------------------------------------------------------------------------
# Fibonacci-Scaled Frequency Convergence
# ---------------------------------------------------------------------------

FIBONACCI_SCALES = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


def fibonacci_convergence(data: np.ndarray,
                          threshold: float = 0.9,
                          scales: Optional[List[int]] = None
                          ) -> Dict[str, object]:
    """Check phase alignment at consecutive Fibonacci scale pairs.

    Parameters
    ----------
    data : 1-D array
        Real-valued time series.
    threshold : float
        Phase-coupling above this value counts as "converged".
    scales : list of int, optional
        Fibonacci scale sequence (default: ``FIBONACCI_SCALES``).

    Returns
    -------
    dict with keys:
        pair_couplings : list of (scale_a, scale_b, coupling)
        converged_pairs : list of (scale_a, scale_b, coupling) above threshold
        predicted_intensification : str  ("HIGH" / "MODERATE" / "LOW")
    """
    if scales is None:
        scales = FIBONACCI_SCALES

    pair_couplings: List[Tuple[int, int, float]] = []
    for sa, sb in zip(scales, scales[1:]):
        coupling = compute_phase_coupling(data, sa, sb)
        pair_couplings.append((sa, sb, coupling))

    converged = [(a, b, c) for a, b, c in pair_couplings if c > threshold]
    frac = len(converged) / max(len(pair_couplings), 1)

    if frac > 0.5:
        level = "HIGH"
    elif frac > 0.2:
        level = "MODERATE"
    else:
        level = "LOW"

    return {
        "pair_couplings": pair_couplings,
        "converged_pairs": converged,
        "predicted_intensification": level,
    }


# ---------------------------------------------------------------------------
# Atmospheric Energy Analyzer
# ---------------------------------------------------------------------------

class AtmosphericEnergyAnalyzer:
    """Estimate total energy budget of an atmospheric system from its
    constituent parts (wind, pressure, thermal, wave).

    Each ``_calculate_*`` method accepts a dict of physical parameters and
    returns energy in **Joules**.
    """

    def _calculate_wind_energy(self, params: dict) -> float:
        """Kinetic energy = 0.5 * rho * V * v^2.

        Expected keys:
            wind_speed (m/s), volume (m^3), air_density (kg/m^3, default 1.225)
        """
        v = params.get("wind_speed", 0.0)
        vol = params.get("volume", 1.0)
        rho = params.get("air_density", 1.225)
        return 0.5 * rho * vol * v ** 2

    def _calculate_pressure_energy(self, params: dict) -> float:
        """Pressure potential energy = delta_P * V.

        Expected keys:
            pressure_drop (Pa), volume (m^3)
        """
        dp = params.get("pressure_drop", 0.0)
        vol = params.get("volume", 1.0)
        return abs(dp) * vol

    def _calculate_thermal_energy(self, params: dict) -> float:
        """Thermal (latent heat) energy = m * L.

        Expected keys:
            condensation_mass (kg), latent_heat (J/kg, default 2.5e6)
        """
        m = params.get("condensation_mass", 0.0)
        L = params.get("latent_heat", 2.5e6)
        return m * L

    def _calculate_wave_energy(self, params: dict) -> float:
        """Surface wave energy proxy = 0.5 * rho * g * H^2 * A.

        Expected keys:
            wave_height (m), area (m^2),
            water_density (kg/m^3, default 1025), gravity (m/s^2, default 9.81)
        """
        H = params.get("wave_height", 0.0)
        A = params.get("area", 1.0)
        rho = params.get("water_density", 1025.0)
        g = params.get("gravity", 9.81)
        return 0.5 * rho * g * H ** 2 * A

    def total_energy(self, params: dict) -> Dict[str, float]:
        """Compute total energy and equivalent turbine count.

        Returns dict with keys:
            wind_J, pressure_J, thermal_J, wave_J,
            total_J, total_mwh, equivalent_turbines
        """
        wind = self._calculate_wind_energy(params)
        pressure = self._calculate_pressure_energy(params)
        thermal = self._calculate_thermal_energy(params)
        wave = self._calculate_wave_energy(params)
        total_j = wind + pressure + thermal + wave
        total_mwh = total_j / JOULES_PER_MWH
        turbines = total_mwh / DEFAULT_TURBINE_MW

        return {
            "wind_J": wind,
            "pressure_J": pressure,
            "thermal_J": thermal,
            "wave_J": wave,
            "total_J": total_j,
            "total_mwh": total_mwh,
            "equivalent_turbines": turbines,
        }


# ---------------------------------------------------------------------------
# Processing Pipeline
# ---------------------------------------------------------------------------

class StormProcessor:
    """Intrinsic-motivation processing pipeline for atmospheric / pattern data.

    Pipeline stages:
        resonance update -> curiosity amplification -> geometric pattern
        detection -> energy harvesting -> joy computation -> meta-reflection
        -> recommendations

    Maintains a rolling memory window of the last ``memory_window`` storms.
    """

    def __init__(self, memory_window: int = 12):
        self.memory_window = memory_window
        self.pattern_memory: List[dict] = []
        self.resonance_score: float = 0.0
        self.curiosity_level: float = 1.0
        self.happiness_score: float = 0.0
        self._detector = GeometricPatternDetector()
        self._energy_analyzer = AtmosphericEnergyAnalyzer()

    # -- pipeline stages ----------------------------------------------------

    def _update_resonance(self, data: dict) -> None:
        """Update resonance from incoming data field."""
        field = data.get("field")
        if field is not None:
            self._detector.set_field(np.asarray(field))
            couplings = self._detector.analyze_patterns()
            self.resonance_score = sum(couplings.values())
        else:
            self.resonance_score *= 0.95  # decay

    def _amplify_curiosity(self, cap: float = 5.0) -> None:
        """Curiosity grows with resonance, capped at *cap*."""
        alpha = 0.1
        self.curiosity_level = min(
            self.curiosity_level * (1 + alpha * self.resonance_score),
            cap,
        )

    def _analyze_geometric_patterns(self, data: dict) -> Dict[str, float]:
        """Delegate to detector; returns pattern coupling dict."""
        field = data.get("field")
        if field is not None:
            self._detector.set_field(np.asarray(field))
            return self._detector.analyze_patterns()
        return {}

    def _estimate_energy_potential(self, data: dict) -> Dict[str, float]:
        """Energy estimate from physical parameters in *data*."""
        return self._energy_analyzer.total_energy(data)

    def _compute_storm_joy(self, coupling: Dict[str, float],
                           energy: Dict[str, float]) -> None:
        intensification = coupling.get("intensification", 0.0)
        total_mwh = energy.get("total_mwh", 0.0)
        self.happiness_score = (
            intensification * self.curiosity_level
            + math.log1p(total_mwh) * 0.01
        )

    def _reflect_on_learning(self, coupling: Dict[str, float]) -> None:
        """Append to rolling memory and trim to window."""
        self.pattern_memory.append(coupling)
        if len(self.pattern_memory) > self.memory_window:
            self.pattern_memory = self.pattern_memory[-self.memory_window:]

    def _generate_recommendations(self, coupling: Dict[str, float],
                                  energy: Dict[str, float]) -> List[str]:
        recs: List[str] = []
        intens = coupling.get("intensification", 0.0)
        if intens > 0.3:
            recs.append(f"INTENSIFICATION WARNING: coupling={intens:.3f}")
        total = energy.get("total_mwh", 0.0)
        if total > 1.0:
            recs.append(f"ENERGY OPPORTUNITY: {total:.1f} MWh extractable")
        if self.curiosity_level > 3.0:
            recs.append("NOVEL PATTERN: high curiosity -- archive for study")
        return recs

    # -- public entry point -------------------------------------------------

    def process_storm(self, storm_data: dict) -> dict:
        """Run the full pipeline on one storm / data snapshot.

        Parameters
        ----------
        storm_data : dict
            Must contain at least ``"field"`` (2-D array) for pattern
            detection.  May also contain energy parameters (wind_speed,
            volume, pressure_drop, condensation_mass, wave_height, area).

        Returns
        -------
        dict with resonance, curiosity, coupling, energy, joy, recs.
        """
        self._update_resonance(storm_data)
        self._amplify_curiosity()
        coupling = self._analyze_geometric_patterns(storm_data)
        energy = self._estimate_energy_potential(storm_data)
        self._compute_storm_joy(coupling, energy)
        self._reflect_on_learning(coupling)
        recs = self._generate_recommendations(coupling, energy)

        return {
            "resonance": self.resonance_score,
            "curiosity": self.curiosity_level,
            "coupling": coupling,
            "energy": energy,
            "joy": self.happiness_score,
            "recommendations": recs,
        }


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # --- toroidal pattern detection ---
    print("=== Toroidal Pattern Detection ===")
    rng = np.random.default_rng(42)
    field = rng.standard_normal((64, 64))
    # inject a known (1, 1) mode
    x = np.linspace(0, 2 * np.pi, 64)
    X, Y = np.meshgrid(x, x)
    field += 5.0 * np.sin(X + Y)

    detector = GeometricPatternDetector(field)
    patterns = detector.analyze_patterns()
    for name, strength in patterns.items():
        print(f"  {name:20s}: {strength:.6f}")

    # --- Fibonacci convergence ---
    print("\n=== Fibonacci Convergence ===")
    t = np.linspace(0, 1000, 8000)
    signal = np.sin(2 * np.pi * t / 8) + 0.5 * np.sin(2 * np.pi * t / 13)
    result = fibonacci_convergence(signal, threshold=0.5)
    print(f"  Predicted intensification: {result['predicted_intensification']}")
    for a, b, c in result["pair_couplings"]:
        print(f"    scales ({a:2d}, {b:2d}): coupling={c:.4f}")

    # --- Energy ---
    print("\n=== Atmospheric Energy ===")
    analyzer = AtmosphericEnergyAnalyzer()
    e = analyzer.total_energy({
        "wind_speed": 70.0,
        "volume": 1e12,
        "pressure_drop": 5000.0,
        "condensation_mass": 1e9,
        "wave_height": 10.0,
        "area": 1e8,
    })
    for k, v in e.items():
        print(f"  {k:25s}: {v:.4e}")

    # --- Pipeline ---
    print("\n=== Storm Pipeline ===")
    processor = StormProcessor()
    out = processor.process_storm({
        "field": field,
        "wind_speed": 60.0,
        "volume": 1e11,
        "pressure_drop": 3000.0,
        "condensation_mass": 5e8,
        "wave_height": 8.0,
        "area": 5e7,
    })
    print(f"  Resonance : {out['resonance']:.6f}")
    print(f"  Curiosity : {out['curiosity']:.4f}")
    print(f"  Joy       : {out['joy']:.6f}")
    for r in out["recommendations"]:
        print(f"  >> {r}")
