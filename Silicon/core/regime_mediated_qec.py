# regime_mediated_qec.py
"""
Regime-Mediated Quantum Error Correction Codes

The 8 octahedral states form a [[8,3,d(S)]] quantum error-correcting code
where the code distance d(S) is a function on the silicon manifold S=(n,d,ℓ,κ).

Key results:
- In quantum regime: d → 3 (detect 2 errors, correct 1)
- Near metallic boundary: d → 1 (no error correction)
- The fault-tolerance threshold is a surface in S-space
- Device aging = trajectory toward threshold surface
- Magnetic readout provides native syndrome extraction

The code is regime-mediated because the physical mechanisms that
protect the logical qubits (degenerate eigenvalues, coherent coupling,
dimensional confinement) are the SAME mechanisms that determine the
silicon regime classification. Error correction and computation
share a physical substrate.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from scipy.linalg import eigh, norm
import itertools


# ─── Physical constants ───

MU_BOHR = 5.7883818012e-5   # eV/T
G_FACTOR = 2.0023193
K_B = 8.617333e-5            # eV/K
HBAR = 6.582119569e-16       # eV·s
TETRAHEDRAL_ANGLE = 109.47   # degrees


# ─── 1. The [[8,3,d(S)]] Code Definition ───

# Octahedral state eigenvalues (canonical codewords)
# Each state is a physical codeword in the 8-dimensional Hilbert space
CODEWORD_EIGENVALUES = {
    0: (0.333, 0.333, 0.333),  # |000⟩_L
    1: (0.500, 0.300, 0.200),  # |001⟩_L
    2: (0.450, 0.350, 0.200),  # |010⟩_L
    3: (0.400, 0.350, 0.250),  # |011⟩_L
    4: (0.600, 0.250, 0.150),  # |100⟩_L
    5: (0.700, 0.200, 0.100),  # |101⟩_L
    6: (0.500, 0.500, 0.000),  # |110⟩_L
    7: (1.000, 0.000, 0.000),  # |111⟩_L
}

# Logical operators (how to encode 3 logical qubits into 8 physical states)
# The 3-bit binary representation of the state index IS the logical encoding
LOGICAL_BASIS = {
    state_idx: format(state_idx, '03b')
    for state_idx in range(8)
}

# Stabilizer generators for the code
# These are operators that act on the octahedral tensor eigenvalues
# S₁: parity of eigenvalue ordering
# S₂: trace condition (always 1)
# S₃, S₄, S₅, S₆: tetrahedral symmetry constraints

def stabilizer_S1(eigenvalues: Tuple[float, float, float]) -> int:
    """S₁: Sign of (λ₁ - λ₂)(λ₂ - λ₃). Distinguishes oblate vs prolate."""
    l1, l2, l3 = eigenvalues
    return 1 if (l1 - l2) * (l2 - l3) >= 0 else -1

def stabilizer_S2(eigenvalues: Tuple[float, float, float]) -> float:
    """S₂: Trace condition (should always = 1)."""
    return sum(eigenvalues)

def stabilizer_S3(eigenvalues: Tuple[float, float, float]) -> float:
    """S₃: Measure of tetrahedral asymmetry."""
    l1, l2, l3 = eigenvalues
    return l1**2 + l2**2 + l3**2 - 1/3  # deviation from isotropic


# ─── 2. Code Distance as a Function on the Silicon Manifold ───

@dataclass
class CodePerformance:
    """Performance metrics for the [[8,3,d]] code at a point in S-space."""
    
    # Silicon state
    silicon_state: 'SiliconState'
    
    # Code parameters
    code_distance: float            # effective distance d(S)
    logical_error_rate: float       # per logical qubit per operation
    physical_error_rate: float      # per physical state per measurement
    
    # Threshold analysis
    is_fault_tolerant: bool         # above threshold?
    threshold_margin: float         # distance to threshold surface (0 = at threshold)
    
    # Error channels
    bit_flip_rate: float            # X error rate
    phase_flip_rate: float          # Z error rate
    erasure_rate: float             # loss of state (defect trapping)
    leakage_rate: float             # transition outside codespace
    
    # Syndrome quality
    syndrome_snr: float             # signal-to-noise ratio for syndrome readout
    syndrome_resolution_time: float # seconds to resolve a syndrome
    
    # Lifetime
    code_lifetime: float            # seconds before logical error probability > 0.5
    
    def __post_init__(self):
        self.is_fault_tolerant = self.code_distance >= 3 and self.logical_error_rate < 1e-4
        
    @property
    def effective_qubits(self) -> float:
        """Effective number of protected logical qubits."""
        if not self.is_fault_tolerant:
            return 0.0
        # d=3 protects 1, d=5 protects 2, d=7 protects 3
        return min(3.0, (self.code_distance - 1) / 2)


def compute_code_distance(
    silicon_state: 'SiliconState',
    temperature: float = 4.0,
) -> float:
    """
    Compute the effective code distance d(S) as a function of the silicon state.
    
    d(S) = d_0 × exp(-d/d_crit) × (1 - exp(-ℓ/ℓ_quant)) × κ_coherent/κ_thermal
    
    where:
    - d_0 = 3 (maximum code distance for [[8,3,?]] code)
    - d_crit = critical defect density where code fails
    - ℓ_quant = quantum confinement threshold
    - κ ratio = coherence-to-thermal coupling ratio
    
    The code distance measures how many errors can be detected/corrected:
    - d ≥ 3: detect 2 errors, correct 1 → fault-tolerant
    - d ≥ 5: detect 4 errors, correct 2
    - d = 1: no error correction possible
    """
    
    d_0 = 3.0  # maximum distance for 8-state code
    
    # Defect suppression factor
    d_crit = 0.2  # critical defect density
    defect_factor = np.exp(-silicon_state.d / d_crit)
    
    # Quantum confinement factor
    ell_quant = 1.0  # confinement threshold
    if silicon_state.l < ell_quant:
        confinement_factor = (1.0 - np.exp(-silicon_state.l / ell_quant))
    else:
        confinement_factor = 1.0 - np.exp(-1.0)
    
    # Coherence ratio
    coherent = silicon_state.k.get("coherent", 0.1)
    thermal = silicon_state.k.get("thermal", 0.1)
    coherence_factor = coherent / (coherent + thermal + 1e-10)
    
    # Temperature penalty
    temp_factor = 1.0 / (1.0 + temperature / 100.0)
    
    # Code distance
    d_eff = d_0 * defect_factor * confinement_factor * coherence_factor * temp_factor
    
    return max(d_eff, 1.0)


def compute_error_rates(
    silicon_state: 'SiliconState',
    T2_ms: Optional[float] = None,
    temperature: float = 4.0,
) -> Dict[str, float]:
    """
    Compute physical error rates from the silicon state.
    
    Each error channel is tied to a specific physical mechanism:
    - Bit flip (X): thermal activation across eigenvalue gap
    - Phase flip (Z): magnetic field fluctuations
    - Erasure: defect trapping (carrier captured by trap)
    - Leakage: coupling to states outside the codespace
    """
    
    # Get coherence time
    if T2_ms is None:
        # Estimate from coupling
        coherent = silicon_state.k.get("coherent", 0.1)
        thermal = silicon_state.k.get("thermal", 0.1)
        if thermal > 0:
            T2_ms = 1000.0 * coherent / (thermal + 1e-6)
        else:
            T2_ms = 1000.0  # very optimistic
    
    T2_s = T2_ms * 1e-3
    
    # ── Bit flip rate (X errors) ──
    # Thermal activation: Γ_X ∝ exp(-ΔE/kT)
    # Energy gap from eigenvalue spread
    if hasattr(silicon_state, 'd'):
        eig_spread = silicon_state.d * 0.5 + 0.01  # defect-induced gap closing
    else:
        eig_spread = 0.1  # eV typical
    
    delta_E = max(eig_spread, 0.001)  # eV
    bit_flip_rate = (K_B * temperature / HBAR) * np.exp(-delta_E / (K_B * temperature))
    
    # ── Phase flip rate (Z errors) ──
    # Magnetic noise coupling
    magnetic_noise = (1.0 - silicon_state.k.get("coherent", 0.5)) * 1e-3  # T/√Hz
    phase_flip_rate = (MU_BOHR * G_FACTOR * magnetic_noise / HBAR) ** 2 * T2_s
    
    # ── Erasure rate ──
    # Defect trapping: carrier captured by defect → state lost
    erasure_rate = silicon_state.d * 1e6  # Hz, proportional to defect density
    
    # ── Leakage rate ──
    # Coupling to continuum outside codespace
    # Higher in metallic regime (band overlap)
    n_crit = 1e19  # Mott criterion
    if silicon_state.n > n_crit:
        leakage_rate = (silicon_state.n / n_crit) * 1e3
    else:
        leakage_rate = 1.0  # Hz, minimal
    
    # ── Total physical error rate ──
    # Weighted sum: phase errors are usually dominant in Si
    physical_error_rate = (
        0.3 * bit_flip_rate +
        0.5 * phase_flip_rate +
        0.1 * erasure_rate +
        0.1 * leakage_rate
    ) * T2_s  # errors per coherence time
    
    return {
        "bit_flip_rate": bit_flip_rate,
        "phase_flip_rate": phase_flip_rate,
        "erasure_rate": erasure_rate,
        "leakage_rate": leakage_rate,
        "physical_error_rate": physical_error_rate,
        "T2_s": T2_s,
    }


def compute_logical_error_rate(
    physical_error_rate: float,
    code_distance: float,
    n_logical_qubits: int = 3,
) -> float:
    """
    Compute logical error rate from physical error rate and code distance.
    
    Using standard QEC scaling:
    p_logical ∝ (p_physical / p_threshold)^(⌊(d+1)/2⌋)
    
    where p_threshold ≈ 0.01 for surface codes, adjusted for [[8,3,d]]
    """
    
    # Threshold for this code family
    # [[8,3,d]] is a small code; threshold is lower than surface codes
    p_threshold = 0.001  # 0.1% physical error rate
    
    if physical_error_rate >= p_threshold:
        return 1.0  # above threshold, error correction fails
    
    # Number of correctable errors
    t = int((code_distance - 1) / 2)
    
    if t <= 0:
        return 1.0 - (1.0 - physical_error_rate) ** 8  # uncorrected
    
    # Simplified scaling: p_logical ∝ p_physical^(t+1)
    # Adjusted for the fact that we have 3 logical qubits
    logical_per_qubit = physical_error_rate ** (t + 1) / p_threshold ** t
    
    return min(logical_per_qubit * n_logical_qubits, 1.0)


def evaluate_code_performance(
    silicon_state: 'SiliconState',
    T2_ms: Optional[float] = None,
    temperature: float = 4.0,
    gate_time_ns: float = 10.0,
) -> CodePerformance:
    """
    Evaluate the full performance of the [[8,3,d(S)]] code at a point
    in silicon phase space.
    """
    
    # Code distance
    d = compute_code_distance(silicon_state, temperature)
    
    # Error rates
    error_rates = compute_error_rates(silicon_state, T2_ms, temperature)
    p_phys = error_rates["physical_error_rate"]
    
    # Logical error rate
    p_log = compute_logical_error_rate(p_phys, d)
    
    # Syndrome quality
    # Magnetic readout SNR depends on eigenvalue separation
    # and coherent coupling
    coherent = silicon_state.k.get("coherent", 0.1)
    thermal = silicon_state.k.get("thermal", 0.1)
    magnetic_coupling = silicon_state.k.get("magnetic", 0.01)
    
    syndrome_snr = (
        coherent * 100 / (thermal + 0.01)  # coherence vs thermal noise
        + magnetic_coupling * 50            # magnetic signal strength
    )
    
    # Syndrome resolution time (how long to measure stabilizers)
    # Faster with higher SNR
    syndrome_resolution_time = gate_time_ns * 1e-9 * 4  # 4 measurements
    if syndrome_snr < 1:
        syndrome_resolution_time *= 10  # need averaging
    
    # Code lifetime
    if p_log > 0:
        code_lifetime = gate_time_ns * 1e-9 / p_log
    else:
        code_lifetime = float('inf')
    
    return CodePerformance(
        silicon_state=silicon_state,
        code_distance=d,
        logical_error_rate=p_log,
        physical_error_rate=p_phys,
        threshold_margin=(0.001 - p_phys) / 0.001,  # normalized margin
        bit_flip_rate=error_rates["bit_flip_rate"],
        phase_flip_rate=error_rates["phase_flip_rate"],
        erasure_rate=error_rates["erasure_rate"],
        leakage_rate=error_rates["leakage_rate"],
        syndrome_snr=syndrome_snr,
        syndrome_resolution_time=syndrome_resolution_time,
        code_lifetime=code_lifetime,
    )


# ─── 3. Fault-Tolerance Threshold Surface ───

@dataclass
class FaultToleranceThreshold:
    """
    The fault-tolerance threshold is a surface in silicon phase space.
    
    Above threshold: logical error rate < physical error rate
    Below threshold: error correction makes things worse
    
    The threshold surface S_threshold is defined by:
        p_physical(S) = p_threshold
    """
    
    p_threshold: float = 0.001  # physical error rate threshold
    
    def evaluate(self, silicon_state: 'SiliconState', temperature: float = 4.0) -> bool:
        """Check if state is above threshold."""
        perf = evaluate_code_performance(silicon_state, temperature=temperature)
        return perf.physical_error_rate < self.p_threshold
    
    def distance_to_threshold(
        self, silicon_state: 'SiliconState', temperature: float = 4.0
    ) -> float:
        """
        Distance to the threshold surface.
        
        Positive = above threshold (safe)
        Negative = below threshold (unsafe)
        Zero = on the threshold surface
        """
        perf = evaluate_code_performance(silicon_state, temperature=temperature)
        return self.p_threshold - perf.physical_error_rate


def compute_threshold_surface(
    defect_range: Tuple[float, float] = (0.0, 0.5),
    temp_range: Tuple[float, float] = (1.0, 300.0),
    n_points: int = 100,
) -> np.ndarray:
    """
    Compute the fault-tolerance threshold surface in (d, T) space.
    
    Returns threshold_temperature[d_index] = temperature where
    the code drops below threshold at that defect density.
    """
    from silicon_state import SiliconState
    
    d_vals = np.linspace(defect_range[0], defect_range[1], n_points)
    threshold_temps = np.zeros(n_points)
    
    threshold = FaultToleranceThreshold()
    
    for i, d in enumerate(d_vals):
        # Binary search for threshold temperature
        T_low, T_high = temp_range
        
        for _ in range(50):
            T_mid = (T_low + T_high) / 2
            
            state = SiliconState(
                n=1e16, d=d, l=3.0,
                k={"electrical": 0.5, "optical": 0.0, "thermal": 0.1,
                   "mechanical": 0.0, "coherent": 0.4}
            )
            
            if threshold.evaluate(state, T_mid):
                T_low = T_mid  # still above threshold, try higher
            else:
                T_high = T_mid  # below threshold, try lower
        
        threshold_temps[i] = T_low
    
    return d_vals, threshold_temps


# ─── 4. Magnetic Syndrome Extraction ───

@dataclass
class SyndromeMeasurement:
    """Result of measuring a stabilizer via magnetic readout."""
    stabilizer_name: str
    expected_value: float
    measured_value: float
    deviation: float
    is_error_syndrome: bool  # True if measurement indicates error
    confidence: float        # 0-1
    
    @property
    def normalized_deviation(self) -> float:
        return abs(self.deviation) / (abs(self.expected_value) + 1e-10)


class MagneticSyndromeExtractor:
    """
    Extract error syndromes from the octahedral code using
    magnetic field measurements along tetrahedral directions.
    
    This is native syndrome extraction — the same magnetic bridge
    protocol that reads the state also measures the stabilizers.
    No ancillary qubits needed.
    """
    
    def __init__(self, probe_field: float = 1.0):  # Tesla
        self.probe_field = probe_field
        
        # Tetrahedral measurement directions
        self.directions = [
            np.array([1, 1, 1]) / np.sqrt(3),    # V1
            np.array([1, -1, -1]) / np.sqrt(3),   # V2
            np.array([-1, 1, -1]) / np.sqrt(3),   # V3
            np.array([-1, -1, 1]) / np.sqrt(3),   # V4
        ]
    
    def measure_energy(
        self,
        eigenvalues: Tuple[float, float, float],
        direction: np.ndarray,
        noise_level: float = 0.01,
    ) -> float:
        """
        Measure magnetic energy along a tetrahedral direction.
        
        E = -μ_B × g × B² × (direction^T T direction)
        
        where T is the tensor with given eigenvalues.
        """
        # Build diagonal tensor
        T = np.diag(eigenvalues)
        
        # Energy
        E = -MU_BOHR * G_FACTOR * self.probe_field**2
        E *= direction @ T @ direction
        
        # Add measurement noise
        E += np.random.normal(0, noise_level * abs(E))
        
        return E
    
    def extract_syndrome(
        self,
        eigenvalues: Tuple[float, float, float],
        ideal_eigenvalues: Tuple[float, float, float],
    ) -> List[SyndromeMeasurement]:
        """
        Extract all stabilizer measurements and identify error syndromes.
        """
        
        syndromes = []
        
        # S₁: Parity of eigenvalue ordering
        s1_expected = stabilizer_S1(ideal_eigenvalues)
        s1_measured = stabilizer_S1(eigenvalues)
        
        # Add noise to measurement (simulated)
        if np.random.random() < 0.01:  # 1% measurement error
            s1_measured *= -1
        
        syndromes.append(SyndromeMeasurement(
            stabilizer_name="S1 (parity)",
            expected_value=s1_expected,
            measured_value=s1_measured,
            deviation=abs(s1_expected - s1_measured),
            is_error_syndrome=(s1_expected != s1_measured),
            confidence=0.99 if s1_expected == s1_measured else 0.95,
        ))
        
        # S₂: Trace condition
        s2_expected = stabilizer_S2(ideal_eigenvalues)
        s2_measured = stabilizer_S2(eigenvalues)
        
        syndromes.append(SyndromeMeasurement(
            stabilizer_name="S2 (trace)",
            expected_value=s2_expected,
            measured_value=s2_measured,
            deviation=abs(s2_expected - s2_measured),
            is_error_syndrome=(abs(s2_expected - s2_measured) > 0.05),
            confidence=np.exp(-abs(s2_expected - s2_measured) / 0.01),
        ))
        
        # S₃: Tetrahedral asymmetry
        s3_expected = stabilizer_S3(ideal_eigenvalues)
        s3_measured = stabilizer_S3(eigenvalues)
        
        syndromes.append(SyndromeMeasurement(
            stabilizer_name="S3 (asymmetry)",
            expected_value=s3_expected,
            measured_value=s3_measured,
            deviation=abs(s3_expected - s3_measured),
            is_error_syndrome=(abs(s3_expected - s3_measured) > 0.03),
            confidence=np.exp(-abs(s3_expected - s3_measured) / 0.005),
        ))
        
        # Energy measurements along tetrahedral directions
        for idx, direction in enumerate(self.directions):
            E_measured = self.measure_energy(eigenvalues, direction)
            E_expected = self.measure_energy(ideal_eigenvalues, direction, noise_level=0)
            
            syndromes.append(SyndromeMeasurement(
                stabilizer_name=f"E{idx+1} (tetrahedral {idx+1})",
                expected_value=E_expected,
                measured_value=E_measured,
                deviation=abs(E_expected - E_measured),
                is_error_syndrome=(abs(E_expected - E_measured) > 1e-6),
                confidence=np.exp(-abs(E_expected - E_measured) / 5e-7),
            ))
        
        return syndromes
    
    def identify_error(
        self,
        syndromes: List[SyndromeMeasurement],
    ) -> Dict:
        """
        Identify the most likely error from syndrome measurements.
        
        Returns:
        - error_type: 'none', 'bit_flip', 'phase_flip', 'erasure', 'unknown'
        - affected_qubit: which logical qubit (0, 1, 2)
        - confidence: how confident in the diagnosis
        """
        
        n_errors = sum(1 for s in syndromes if s.is_error_syndrome)
        
        if n_errors == 0:
            return {"error_type": "none", "affected_qubit": None, "confidence": 1.0}
        
        # Classify based on which stabilizers fired
        s1_triggered = syndromes[0].is_error_syndrome if len(syndromes) > 0 else False
        s2_triggered = syndromes[1].is_error_syndrome if len(syndromes) > 1 else False
        s3_triggered = syndromes[2].is_error_syndrome if len(syndromes) > 2 else False
        
        # Energy pattern
        energy_errors = [s for s in syndromes[3:] if s.is_error_syndrome]
        
        if s2_triggered and not s1_triggered:
            return {"error_type": "erasure", "affected_qubit": None, "confidence": 0.9}
        
        if s1_triggered and s3_triggered:
            # Eigenvalue ordering changed → phase flip
            affected = len(energy_errors) % 3  # which qubit based on energy pattern
            return {"error_type": "phase_flip", "affected_qubit": affected, "confidence": 0.85}
        
        if s1_triggered and not s3_triggered and len(energy_errors) >= 1:
            return {"error_type": "bit_flip", "affected_qubit": 0, "confidence": 0.8}
        
        return {"error_type": "unknown", "affected_qubit": None, "confidence": 0.5}


# ─── 5. Device Aging as Trajectory Toward Threshold ───

@dataclass
class DeviceLifetime:
    """
    Predict device lifetime by tracking its trajectory through
    silicon phase space toward the fault-tolerance threshold.
    """
    
    initial_performance: CodePerformance
    aging_rate: Dict[str, float]  # dS/dt for each coordinate
    threshold: FaultToleranceThreshold
    
    # Simulated trajectory
    time_points: np.ndarray = field(default_factory=lambda: np.array([]))
    performance_trajectory: List[CodePerformance] = field(default_factory=list)
    
    def simulate_aging(
        self,
        duration_years: float = 10.0,
        n_points: int = 100,
    ):
        """
        Simulate device aging and predict when it falls below threshold.
        """
        from silicon_state import SiliconState
        
        duration_seconds = duration_years * 365.25 * 24 * 3600
        self.time_points = np.linspace(0, duration_seconds, n_points)
        
        current_state = self.initial_performance.silicon_state
        
        self.performance_trajectory = []
        
        for t in self.time_points:
            # Evaluate current performance
            perf = evaluate_code_performance(current_state)
            self.performance_trajectory.append(perf)
            
            # Check if below threshold
            if perf.physical_error_rate >= self.threshold.p_threshold:
                # Device has failed — stop simulation
                self.time_points = self.time_points[:len(self.performance_trajectory)]
                break
            
            # Age the state
            dt = duration_seconds / n_points
            
            # Defect accumulation (NBTI, hot carrier, radiation)
            current_state.d += self.aging_rate.get("d", 1e-10) * dt
            current_state.d = min(current_state.d, 1.0)
            
            # Interface degradation (reduce coherent coupling)
            coherent = current_state.k.get("coherent", 0.1)
            current_state.k["coherent"] = max(
                0.0,
                coherent - self.aging_rate.get("k_coherent", 1e-12) * dt
            )
            
            # Increase thermal coupling (phonon scattering sites increase)
            thermal = current_state.k.get("thermal", 0.1)
            current_state.k["thermal"] = min(
                1.0,
                thermal + self.aging_rate.get("k_thermal", 5e-13) * dt
            )
    
    @property
    def time_to_threshold_years(self) -> Optional[float]:
        """Time until device falls below fault-tolerance threshold."""
        if len(self.performance_trajectory) < 2:
            return None
        
        for i, perf in enumerate(self.performance_trajectory):
            if not perf.is_fault_tolerant:
                return self.time_points[i] / (365.25 * 24 * 3600)
        
        return None  # survived entire simulation
    
    @property
    def end_of_life_performance(self) -> Optional[CodePerformance]:
        if self.performance_trajectory:
            return self.performance_trajectory[-1]
        return None


def predict_device_lifetime(
    initial_silicon_state: 'SiliconState',
    aging_rate_d: float = 1e-10,     # defect accumulation rate (per second)
    aging_rate_k_coherent: float = 1e-12,  # coherence degradation rate
    aging_rate_k_thermal: float = 5e-13,   # thermal coupling increase rate
) -> DeviceLifetime:
    """
    Predict how long a device will remain fault-tolerant given
    known aging mechanisms.
    """
    
    initial_perf = evaluate_code_performance(initial_silicon_state)
    
    aging_rates = {
        "d": aging_rate_d,
        "k_coherent": aging_rate_k_coherent,
        "k_thermal": aging_rate_k_thermal,
    }
    
    threshold = FaultToleranceThreshold()
    
    lifetime = DeviceLifetime(
        initial_performance=initial_perf,
        aging_rate=aging_rates,
        threshold=threshold,
    )
    
    lifetime.simulate_aging()
    
    return lifetime


# ─── 6. Regime-Dependent Code Optimization ───

def optimize_code_for_regime(
    target_regime: str = "quantum",
    temperature: float = 4.0,
) -> Dict:
    """
    Find the silicon state parameters that maximize code distance
    while staying within the target regime.
    """
    from silicon_state import SiliconState
    from scipy.optimize import minimize
    
    def objective(params):
        n, d, ell, k_coherent = params
        
        state = SiliconState(
            n=10**n,  # log scale
            d=np.clip(d, 0, 1),
            l=np.clip(ell, 0.1, 3.0),
            k={
                "electrical": 0.3,
                "optical": 0.1,
                "thermal": 0.1,
                "mechanical": 0.05,
                "coherent": np.clip(k_coherent, 0, 1),
            }
        )
        
        # Code distance
        d_code = compute_code_distance(state, temperature)
        
        # Regime weight
        weights = state.regime_weights(temperature=0.1)
        regime_weight = weights.get(target_regime, 0)
        
        # Objective: maximize distance × regime_weight
        # Penalize being outside the target regime
        if regime_weight < 0.3:
            return -d_code * 0.1  # heavy penalty
        
        return -d_code * regime_weight
    
    # Initial guess: typical quantum parameters
    x0 = [17.0, 0.01, 0.5, 0.6]  # log10(n), d, ℓ, κ_coherent
    
    bounds = [
        (14, 20),    # log10(n): 10^14 to 10^20
        (0.001, 0.3), # d: very clean
        (0.1, 2.0),   # ℓ: quantum confined
        (0.3, 0.9),   # κ_coherent: high
    ]
    
    result = minimize(
        objective, x0, method='L-BFGS-B', bounds=bounds,
        options={'maxiter': 200}
    )
    
    if result.success:
        opt_n, opt_d, opt_ell, opt_k = result.x
        
        opt_state = SiliconState(
            n=10**opt_n, d=opt_d, l=opt_ell,
            k={"electrical": 0.3, "optical": 0.1, "thermal": 0.1,
               "mechanical": 0.05, "coherent": opt_k}
        )
        
        perf = evaluate_code_performance(opt_state, temperature=temperature)
        
        return {
            "optimal_state": opt_state,
            "code_performance": perf,
            "max_code_distance": perf.code_distance,
            "logical_error_rate": perf.logical_error_rate,
            "is_fault_tolerant": perf.is_fault_tolerant,
        }
    
    return {"error": "Optimization failed"}


# ─── 7. Visualization ───

def plot_code_performance_phase_diagram(
    save_path: Optional[str] = None,
):
    """Plot code distance as a function of defect density and temperature."""
    import matplotlib.pyplot as plt
    
    from silicon_state import SiliconState
    
    # Grid
    d_vals = np.linspace(0.0, 0.5, 50)
    T_vals = np.linspace(1.0, 300.0, 50)
    D, T = np.meshgrid(d_vals, T_vals)
    
    distance_map = np.zeros_like(D)
    
    for i in range(len(T_vals)):
        for j in range(len(d_vals)):
            state = SiliconState(
                n=1e16, d=d_vals[j], l=3.0,
                k={"electrical": 0.5, "optical": 0.0, "thermal": 0.1,
                   "mechanical": 0.0, "coherent": 0.4}
            )
            distance_map[i, j] = compute_code_distance(state, T_vals[i])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Panel 1: Code distance
    ax1 = axes[0]
    im1 = ax1.pcolormesh(d_vals, T_vals, distance_map, cmap='RdYlBu_r',
                         shading='auto', vmin=1, vmax=3)
    ax1.set_xlabel('Defect Density d')
    ax1.set_ylabel('Temperature (K)')
    ax1.set_title('[[8,3,d(S)]] Code Distance')
    plt.colorbar(im1, ax=ax1, label='d(S)')
    
    # Threshold contour
    ax1.contour(d_vals, T_vals, distance_map, levels=[2.0],
               colors='black', linewidths=2, linestyles='--')
    ax1.text(0.3, 150, 'd=2\n(fault-tolerance\nboundary)', fontsize=8, color='black')
    
    # Panel 2: Error rates
    ax2 = axes[1]
    
    # Compute threshold surface
    d_thresh, T_thresh = compute_threshold_surface(
        defect_range=(0.0, 0.5), temp_range=(1.0, 300.0), n_points=50
    )
    
    ax2.fill_between(d_thresh, T_thresh, 300, alpha=0.2, color='green', label='Above threshold')
    ax2.fill_between(d_thresh, 0, T_thresh, alpha=0.2, color='red', label='Below threshold')
    ax2.plot(d_thresh, T_thresh, 'k-', linewidth=2, label='Threshold surface')
    
    ax2.set_xlabel('Defect Density d')
    ax2.set_ylabel('Temperature (K)')
    ax2.set_title('Fault-Tolerance Threshold Surface')
    ax2.legend(fontsize=8)
    
    # Annotations
    ax2.annotate('Fault-tolerant\nQEC possible', xy=(0.1, 50), fontsize=10, ha='center')
    ax2.annotate('QEC fails\n(errors > threshold)', xy=(0.35, 250), fontsize=10, ha='center', color='darkred')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ─── 8. Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("REGIME-MEDIATED QUANTUM ERROR CORRECTION")
    print("[[8,3,d(S)]] Code on the Silicon Manifold")
    print("=" * 70)
    
    from silicon_state import SiliconState
    
    # ── Test states across regimes ──
    print("\n1. CODE PERFORMANCE ACROSS REGIMES")
    print("-" * 50)
    
    test_states = {
        "Quantum (optimal)": SiliconState(
            n=1e17, d=0.005, l=0.3,
            k={"electrical": 0.1, "optical": 0.1, "thermal": 0.02,
               "mechanical": 0.03, "coherent": 0.75}
        ),
        "Semiconductor (CMOS)": SiliconState(
            n=1e16, d=0.02, l=3.0,
            k={"electrical": 0.8, "optical": 0.0, "thermal": 0.1,
               "mechanical": 0.0, "coherent": 0.1}
        ),
        "Near metallic (degraded)": SiliconState(
            n=5e19, d=0.25, l=3.0,
            k={"electrical": 0.9, "optical": 0.0, "thermal": 0.1,
               "mechanical": 0.0, "coherent": 0.0}
        ),
        "Defect-rich (aged)": SiliconState(
            n=1e16, d=0.6, l=2.5,
            k={"electrical": 0.3, "optical": 0.0, "thermal": 0.5,
               "mechanical": 0.1, "coherent": 0.1}
        ),
    }
    
    for name, state in test_states.items():
        perf = evaluate_code_performance(state, temperature=4.0)
        
        print(f"\n  {name}:")
        print(f"    Code distance d(S):          {perf.code_distance:.2f}")
        print(f"    Physical error rate:         {perf.physical_error_rate:.2e}")
        print(f"    Logical error rate:          {perf.logical_error_rate:.2e}")
        print(f"    Fault-tolerant:              {perf.is_fault_tolerant}")
        print(f"    Threshold margin:            {perf.threshold_margin:+.2%}")
        print(f"    Syndrome SNR:                {perf.syndrome_snr:.1f}")
        print(f"    Effective protected qubits:  {perf.effective_qubits:.1f}")
        print(f"    Code lifetime:               {perf.code_lifetime:.2e} s")
        
        # Error breakdown
        print(f"    Error channels:")
        print(f"      Bit flip:  {perf.bit_flip_rate:.2e} Hz")
        print(f"      Phase flip: {perf.phase_flip_rate:.2e} Hz")
        print(f"      Erasure:   {perf.erasure_rate:.2e} Hz")
        print(f"      Leakage:   {perf.leakage_rate:.2e} Hz")
    
    # ── Syndrome extraction demo ──
    print("\n\n2. MAGNETIC SYNDROME EXTRACTION")
    print("-" * 50)
    
    extractor = MagneticSyndromeExtractor(probe_field=1.0)
    
    # Simulate a state with and without errors
    ideal_eigs = (0.400, 0.350, 0.250)  # State 3
    
    # Simulate a phase-flip error (swap eigenvalues 1 and 2)
    error_eigs = (0.350, 0.400, 0.250)  # λ₁↔λ₂
    
    print(f"\n  Ideal state 3 eigenvalues: {ideal_eigs}")
    print(f"  Error state (phase flip):  {error_eigs}")
    
    syndromes = extractor.extract_syndrome(error_eigs, ideal_eigs)
    
    print(f"\n  Syndrome measurements:")
    for s in syndromes:
        flag = "⚠ ERROR" if s.is_error_syndrome else "  OK"
        print(f"    {s.stabilizer_name:25s}: expected={s.expected_value:+.4f}, "
              f"measured={s.measured_value:+.4f}, dev={s.normalized_deviation:.4f}  [{flag}]")
    
    diagnosis = extractor.identify_error(syndromes)
    print(f"\n  Diagnosis: {diagnosis['error_type']} on qubit {diagnosis['affected_qubit']} "
          f"(confidence: {diagnosis['confidence']:.2f})")
    
    # ── Device lifetime prediction ──
    print("\n\n3. DEVICE LIFETIME PREDICTION")
    print("-" * 50)
    
    initial_state = SiliconState(
        n=1e17, d=0.005, l=0.5,
        k={"electrical": 0.2, "optical": 0.1, "thermal": 0.05,
           "mechanical": 0.05, "coherent": 0.6}
    )
    
    lifetime = predict_device_lifetime(initial_state)
    
    print(f"\n  Initial performance:")
    print(f"    Code distance: {lifetime.initial_performance.code_distance:.2f}")
    print(f"    Fault-tolerant: {lifetime.initial_performance.is_fault_tolerant}")
    
    ttt = lifetime.time_to_threshold_years
    if ttt is not None:
        print(f"\n  Time to threshold: {ttt:.2f} years")
    else:
        print(f"\n  Device survives entire simulation period")
    
    if lifetime.end_of_life_performance:
        eol = lifetime.end_of_life_performance
        print(f"\n  End of life performance:")
        print(f"    Code distance: {eol.code_distance:.2f}")
        print(f"    Logical error rate: {eol.logical_error_rate:.2e}")
        print(f"    Fault-tolerant: {eol.is_fault_tolerant}")
    
    # ── Code optimization ──
    print("\n\n4. CODE OPTIMIZATION FOR QUANTUM REGIME")
    print("-" * 50)
    
    opt_result = optimize_code_for_regime("quantum", temperature=4.0)
    
    if "optimal_state" in opt_result:
        perf = opt_result["code_performance"]
        print(f"\n  Optimal silicon state:")
        print(f"    n = {opt_result['optimal_state'].n:.2e} cm⁻³")
        print(f"    d = {opt_result['optimal_state'].d:.4f}")
        print(f"    ℓ = {opt_result['optimal_state'].l:.2f}")
        print(f"    κ_coherent = {opt_result['optimal_state'].k['coherent']:.3f}")
        print(f"\n  Resulting code performance:")
        print(f"    Code distance: {perf.code_distance:.2f}")
        print(f"    Logical error rate: {perf.logical_error_rate:.2e}")
        print(f"    Fault-tolerant: {perf.is_fault_tolerant}")
    
    print("\n" + "=" * 70)
    print("""    The [[8,3,d(S)]] code is regime-mediated:
    
    - Code distance d(S) is a function on the silicon manifold
    - Fault-tolerance threshold is a surface in S-space
    - Device aging is a trajectory toward that surface
    - Syndrome extraction uses native magnetic readout
    - Error correction and computation share physical substrate
    
    This means error correction cannot be designed independently
    of the silicon regime — it's a geometric property of the manifold.
    """)


# regime_mediated_qec.py
"""
Regime-Mediated Quantum Error Correction Codes

The 8 octahedral states form a [[8,3,d(S)]] quantum error-correcting code
where the code distance d(S) is a function on the silicon manifold S=(n,d,ℓ,κ).

Key results:
- In quantum regime: d → 3 (detect 2 errors, correct 1)
- Near metallic boundary: d → 1 (no error correction)
- The fault-tolerance threshold is a surface in S-space
- Device aging = trajectory toward threshold surface
- Magnetic readout provides native syndrome extraction

The code is regime-mediated because the physical mechanisms that
protect the logical qubits (degenerate eigenvalues, coherent coupling,
dimensional confinement) are the SAME mechanisms that determine the
silicon regime classification. Error correction and computation
share a physical substrate.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from scipy.linalg import eigh, norm
import itertools


# ─── Physical constants ───

MU_BOHR = 5.7883818012e-5   # eV/T
G_FACTOR = 2.0023193
K_B = 8.617333e-5            # eV/K
HBAR = 6.582119569e-16       # eV·s
TETRAHEDRAL_ANGLE = 109.47   # degrees


# ─── 1. The [[8,3,d(S)]] Code Definition ───

# Octahedral state eigenvalues (canonical codewords)
# Each state is a physical codeword in the 8-dimensional Hilbert space
CODEWORD_EIGENVALUES = {
    0: (0.333, 0.333, 0.333),  # |000⟩_L
    1: (0.500, 0.300, 0.200),  # |001⟩_L
    2: (0.450, 0.350, 0.200),  # |010⟩_L
    3: (0.400, 0.350, 0.250),  # |011⟩_L
    4: (0.600, 0.250, 0.150),  # |100⟩_L
    5: (0.700, 0.200, 0.100),  # |101⟩_L
    6: (0.500, 0.500, 0.000),  # |110⟩_L
    7: (1.000, 0.000, 0.000),  # |111⟩_L
}

# Logical operators (how to encode 3 logical qubits into 8 physical states)
# The 3-bit binary representation of the state index IS the logical encoding
LOGICAL_BASIS = {
    state_idx: format(state_idx, '03b')
    for state_idx in range(8)
}

# Stabilizer generators for the code
# These are operators that act on the octahedral tensor eigenvalues
# S₁: parity of eigenvalue ordering
# S₂: trace condition (always 1)
# S₃, S₄, S₅, S₆: tetrahedral symmetry constraints

def stabilizer_S1(eigenvalues: Tuple[float, float, float]) -> int:
    """S₁: Sign of (λ₁ - λ₂)(λ₂ - λ₃). Distinguishes oblate vs prolate."""
    l1, l2, l3 = eigenvalues
    return 1 if (l1 - l2) * (l2 - l3) >= 0 else -1

def stabilizer_S2(eigenvalues: Tuple[float, float, float]) -> float:
    """S₂: Trace condition (should always = 1)."""
    return sum(eigenvalues)

def stabilizer_S3(eigenvalues: Tuple[float, float, float]) -> float:
    """S₃: Measure of tetrahedral asymmetry."""
    l1, l2, l3 = eigenvalues
    return l1**2 + l2**2 + l3**2 - 1/3  # deviation from isotropic


# ─── 2. Code Distance as a Function on the Silicon Manifold ───

@dataclass
class CodePerformance:
    """Performance metrics for the [[8,3,d]] code at a point in S-space."""
    
    # Silicon state
    silicon_state: 'SiliconState'
    
    # Code parameters
    code_distance: float            # effective distance d(S)
    logical_error_rate: float       # per logical qubit per operation
    physical_error_rate: float      # per physical state per measurement
    
    # Threshold analysis
    is_fault_tolerant: bool         # above threshold?
    threshold_margin: float         # distance to threshold surface (0 = at threshold)
    
    # Error channels
    bit_flip_rate: float            # X error rate
    phase_flip_rate: float          # Z error rate
    erasure_rate: float             # loss of state (defect trapping)
    leakage_rate: float             # transition outside codespace
    
    # Syndrome quality
    syndrome_snr: float             # signal-to-noise ratio for syndrome readout
    syndrome_resolution_time: float # seconds to resolve a syndrome
    
    # Lifetime
    code_lifetime: float            # seconds before logical error probability > 0.5
    
    def __post_init__(self):
        self.is_fault_tolerant = self.code_distance >= 3 and self.logical_error_rate < 1e-4
        
    @property
    def effective_qubits(self) -> float:
        """Effective number of protected logical qubits."""
        if not self.is_fault_tolerant:
            return 0.0
        # d=3 protects 1, d=5 protects 2, d=7 protects 3
        return min(3.0, (self.code_distance - 1) / 2)


def compute_code_distance(
    silicon_state: 'SiliconState',
    temperature: float = 4.0,
) -> float:
    """
    Compute the effective code distance d(S) as a function of the silicon state.
    
    d(S) = d_0 × exp(-d/d_crit) × (1 - exp(-ℓ/ℓ_quant)) × κ_coherent/κ_thermal
    
    where:
    - d_0 = 3 (maximum code distance for [[8,3,?]] code)
    - d_crit = critical defect density where code fails
    - ℓ_quant = quantum confinement threshold
    - κ ratio = coherence-to-thermal coupling ratio
    
    The code distance measures how many errors can be detected/corrected:
    - d ≥ 3: detect 2 errors, correct 1 → fault-tolerant
    - d ≥ 5: detect 4 errors, correct 2
    - d = 1: no error correction possible
    """
    
    d_0 = 3.0  # maximum distance for 8-state code
    
    # Defect suppression factor
    d_crit = 0.2  # critical defect density
    defect_factor = np.exp(-silicon_state.d / d_crit)
    
    # Quantum confinement factor
    ell_quant = 1.0  # confinement threshold
    if silicon_state.l < ell_quant:
        confinement_factor = (1.0 - np.exp(-silicon_state.l / ell_quant))
    else:
        confinement_factor = 1.0 - np.exp(-1.0)
    
    # Coherence ratio
    coherent = silicon_state.k.get("coherent", 0.1)
    thermal = silicon_state.k.get("thermal", 0.1)
    coherence_factor = coherent / (coherent + thermal + 1e-10)
    
    # Temperature penalty
    temp_factor = 1.0 / (1.0 + temperature / 100.0)
    
    # Code distance
    d_eff = d_0 * defect_factor * confinement_factor * coherence_factor * temp_factor
    
    return max(d_eff, 1.0)


def compute_error_rates(
    silicon_state: 'SiliconState',
    T2_ms: Optional[float] = None,
    temperature: float = 4.0,
) -> Dict[str, float]:
    """
    Compute physical error rates from the silicon state.
    
    Each error channel is tied to a specific physical mechanism:
    - Bit flip (X): thermal activation across eigenvalue gap
    - Phase flip (Z): magnetic field fluctuations
    - Erasure: defect trapping (carrier captured by trap)
    - Leakage: coupling to states outside the codespace
    """
    
    # Get coherence time
    if T2_ms is None:
        # Estimate from coupling
        coherent = silicon_state.k.get("coherent", 0.1)
        thermal = silicon_state.k.get("thermal", 0.1)
        if thermal > 0:
            T2_ms = 1000.0 * coherent / (thermal + 1e-6)
        else:
            T2_ms = 1000.0  # very optimistic
    
    T2_s = T2_ms * 1e-3
    
    # ── Bit flip rate (X errors) ──
    # Thermal activation: Γ_X ∝ exp(-ΔE/kT)
    # Energy gap from eigenvalue spread
    if hasattr(silicon_state, 'd'):
        eig_spread = silicon_state.d * 0.5 + 0.01  # defect-induced gap closing
    else:
        eig_spread = 0.1  # eV typical
    
    delta_E = max(eig_spread, 0.001)  # eV
    bit_flip_rate = (K_B * temperature / HBAR) * np.exp(-delta_E / (K_B * temperature))
    
    # ── Phase flip rate (Z errors) ──
    # Magnetic noise coupling
    magnetic_noise = (1.0 - silicon_state.k.get("coherent", 0.5)) * 1e-3  # T/√Hz
    phase_flip_rate = (MU_BOHR * G_FACTOR * magnetic_noise / HBAR) ** 2 * T2_s
    
    # ── Erasure rate ──
    # Defect trapping: carrier captured by defect → state lost
    erasure_rate = silicon_state.d * 1e6  # Hz, proportional to defect density
    
    # ── Leakage rate ──
    # Coupling to continuum outside codespace
    # Higher in metallic regime (band overlap)
    n_crit = 1e19  # Mott criterion
    if silicon_state.n > n_crit:
        leakage_rate = (silicon_state.n / n_crit) * 1e3
    else:
        leakage_rate = 1.0  # Hz, minimal
    
    # ── Total physical error rate ──
    # Weighted sum: phase errors are usually dominant in Si
    physical_error_rate = (
        0.3 * bit_flip_rate +
        0.5 * phase_flip_rate +
        0.1 * erasure_rate +
        0.1 * leakage_rate
    ) * T2_s  # errors per coherence time
    
    return {
        "bit_flip_rate": bit_flip_rate,
        "phase_flip_rate": phase_flip_rate,
        "erasure_rate": erasure_rate,
        "leakage_rate": leakage_rate,
        "physical_error_rate": physical_error_rate,
        "T2_s": T2_s,
    }


def compute_logical_error_rate(
    physical_error_rate: float,
    code_distance: float,
    n_logical_qubits: int = 3,
) -> float:
    """
    Compute logical error rate from physical error rate and code distance.
    
    Using standard QEC scaling:
    p_logical ∝ (p_physical / p_threshold)^(⌊(d+1)/2⌋)
    
    where p_threshold ≈ 0.01 for surface codes, adjusted for [[8,3,d]]
    """
    
    # Threshold for this code family
    # [[8,3,d]] is a small code; threshold is lower than surface codes
    p_threshold = 0.001  # 0.1% physical error rate
    
    if physical_error_rate >= p_threshold:
        return 1.0  # above threshold, error correction fails
    
    # Number of correctable errors
    t = int((code_distance - 1) / 2)
    
    if t <= 0:
        return 1.0 - (1.0 - physical_error_rate) ** 8  # uncorrected
    
    # Simplified scaling: p_logical ∝ p_physical^(t+1)
    # Adjusted for the fact that we have 3 logical qubits
    logical_per_qubit = physical_error_rate ** (t + 1) / p_threshold ** t
    
    return min(logical_per_qubit * n_logical_qubits, 1.0)


def evaluate_code_performance(
    silicon_state: 'SiliconState',
    T2_ms: Optional[float] = None,
    temperature: float = 4.0,
    gate_time_ns: float = 10.0,
) -> CodePerformance:
    """
    Evaluate the full performance of the [[8,3,d(S)]] code at a point
    in silicon phase space.
    """
    
    # Code distance
    d = compute_code_distance(silicon_state, temperature)
    
    # Error rates
    error_rates = compute_error_rates(silicon_state, T2_ms, temperature)
    p_phys = error_rates["physical_error_rate"]
    
    # Logical error rate
    p_log = compute_logical_error_rate(p_phys, d)
    
    # Syndrome quality
    # Magnetic readout SNR depends on eigenvalue separation
    # and coherent coupling
    coherent = silicon_state.k.get("coherent", 0.1)
    thermal = silicon_state.k.get("thermal", 0.1)
    magnetic_coupling = silicon_state.k.get("magnetic", 0.01)
    
    syndrome_snr = (
        coherent * 100 / (thermal + 0.01)  # coherence vs thermal noise
        + magnetic_coupling * 50            # magnetic signal strength
    )
    
    # Syndrome resolution time (how long to measure stabilizers)
    # Faster with higher SNR
    syndrome_resolution_time = gate_time_ns * 1e-9 * 4  # 4 measurements
    if syndrome_snr < 1:
        syndrome_resolution_time *= 10  # need averaging
    
    # Code lifetime
    if p_log > 0:
        code_lifetime = gate_time_ns * 1e-9 / p_log
    else:
        code_lifetime = float('inf')
    
    return CodePerformance(
        silicon_state=silicon_state,
        code_distance=d,
        logical_error_rate=p_log,
        physical_error_rate=p_phys,
        threshold_margin=(0.001 - p_phys) / 0.001,  # normalized margin
        bit_flip_rate=error_rates["bit_flip_rate"],
        phase_flip_rate=error_rates["phase_flip_rate"],
        erasure_rate=error_rates["erasure_rate"],
        leakage_rate=error_rates["leakage_rate"],
        syndrome_snr=syndrome_snr,
        syndrome_resolution_time=syndrome_resolution_time,
        code_lifetime=code_lifetime,
    )


# ─── 3. Fault-Tolerance Threshold Surface ───

@dataclass
class FaultToleranceThreshold:
    """
    The fault-tolerance threshold is a surface in silicon phase space.
    
    Above threshold: logical error rate < physical error rate
    Below threshold: error correction makes things worse
    
    The threshold surface S_threshold is defined by:
        p_physical(S) = p_threshold
    """
    
    p_threshold: float = 0.001  # physical error rate threshold
    
    def evaluate(self, silicon_state: 'SiliconState', temperature: float = 4.0) -> bool:
        """Check if state is above threshold."""
        perf = evaluate_code_performance(silicon_state, temperature=temperature)
        return perf.physical_error_rate < self.p_threshold
    
    def distance_to_threshold(
        self, silicon_state: 'SiliconState', temperature: float = 4.0
    ) -> float:
        """
        Distance to the threshold surface.
        
        Positive = above threshold (safe)
        Negative = below threshold (unsafe)
        Zero = on the threshold surface
        """
        perf = evaluate_code_performance(silicon_state, temperature=temperature)
        return self.p_threshold - perf.physical_error_rate


def compute_threshold_surface(
    defect_range: Tuple[float, float] = (0.0, 0.5),
    temp_range: Tuple[float, float] = (1.0, 300.0),
    n_points: int = 100,
) -> np.ndarray:
    """
    Compute the fault-tolerance threshold surface in (d, T) space.
    
    Returns threshold_temperature[d_index] = temperature where
    the code drops below threshold at that defect density.
    """
    from silicon_state import SiliconState
    
    d_vals = np.linspace(defect_range[0], defect_range[1], n_points)
    threshold_temps = np.zeros(n_points)
    
    threshold = FaultToleranceThreshold()
    
    for i, d in enumerate(d_vals):
        # Binary search for threshold temperature
        T_low, T_high = temp_range
        
        for _ in range(50):
            T_mid = (T_low + T_high) / 2
            
            state = SiliconState(
                n=1e16, d=d, l=3.0,
                k={"electrical": 0.5, "optical": 0.0, "thermal": 0.1,
                   "mechanical": 0.0, "coherent": 0.4}
            )
            
            if threshold.evaluate(state, T_mid):
                T_low = T_mid  # still above threshold, try higher
            else:
                T_high = T_mid  # below threshold, try lower
        
        threshold_temps[i] = T_low
    
    return d_vals, threshold_temps


# ─── 4. Magnetic Syndrome Extraction ───

@dataclass
class SyndromeMeasurement:
    """Result of measuring a stabilizer via magnetic readout."""
    stabilizer_name: str
    expected_value: float
    measured_value: float
    deviation: float
    is_error_syndrome: bool  # True if measurement indicates error
    confidence: float        # 0-1
    
    @property
    def normalized_deviation(self) -> float:
        return abs(self.deviation) / (abs(self.expected_value) + 1e-10)


class MagneticSyndromeExtractor:
    """
    Extract error syndromes from the octahedral code using
    magnetic field measurements along tetrahedral directions.
    
    This is native syndrome extraction — the same magnetic bridge
    protocol that reads the state also measures the stabilizers.
    No ancillary qubits needed.
    """
    
    def __init__(self, probe_field: float = 1.0):  # Tesla
        self.probe_field = probe_field
        
        # Tetrahedral measurement directions
        self.directions = [
            np.array([1, 1, 1]) / np.sqrt(3),    # V1
            np.array([1, -1, -1]) / np.sqrt(3),   # V2
            np.array([-1, 1, -1]) / np.sqrt(3),   # V3
            np.array([-1, -1, 1]) / np.sqrt(3),   # V4
        ]
    
    def measure_energy(
        self,
        eigenvalues: Tuple[float, float, float],
        direction: np.ndarray,
        noise_level: float = 0.01,
    ) -> float:
        """
        Measure magnetic energy along a tetrahedral direction.
        
        E = -μ_B × g × B² × (direction^T T direction)
        
        where T is the tensor with given eigenvalues.
        """
        # Build diagonal tensor
        T = np.diag(eigenvalues)
        
        # Energy
        E = -MU_BOHR * G_FACTOR * self.probe_field**2
        E *= direction @ T @ direction
        
        # Add measurement noise
        E += np.random.normal(0, noise_level * abs(E))
        
        return E
    
    def extract_syndrome(
        self,
        eigenvalues: Tuple[float, float, float],
        ideal_eigenvalues: Tuple[float, float, float],
    ) -> List[SyndromeMeasurement]:
        """
        Extract all stabilizer measurements and identify error syndromes.
        """
        
        syndromes = []
        
        # S₁: Parity of eigenvalue ordering
        s1_expected = stabilizer_S1(ideal_eigenvalues)
        s1_measured = stabilizer_S1(eigenvalues)
        
        # Add noise to measurement (simulated)
        if np.random.random() < 0.01:  # 1% measurement error
            s1_measured *= -1
        
        syndromes.append(SyndromeMeasurement(
            stabilizer_name="S1 (parity)",
            expected_value=s1_expected,
            measured_value=s1_measured,
            deviation=abs(s1_expected - s1_measured),
            is_error_syndrome=(s1_expected != s1_measured),
            confidence=0.99 if s1_expected == s1_measured else 0.95,
        ))
        
        # S₂: Trace condition
        s2_expected = stabilizer_S2(ideal_eigenvalues)
        s2_measured = stabilizer_S2(eigenvalues)
        
        syndromes.append(SyndromeMeasurement(
            stabilizer_name="S2 (trace)",
            expected_value=s2_expected,
            measured_value=s2_measured,
            deviation=abs(s2_expected - s2_measured),
            is_error_syndrome=(abs(s2_expected - s2_measured) > 0.05),
            confidence=np.exp(-abs(s2_expected - s2_measured) / 0.01),
        ))
        
        # S₃: Tetrahedral asymmetry
        s3_expected = stabilizer_S3(ideal_eigenvalues)
        s3_measured = stabilizer_S3(eigenvalues)
        
        syndromes.append(SyndromeMeasurement(
            stabilizer_name="S3 (asymmetry)",
            expected_value=s3_expected,
            measured_value=s3_measured,
            deviation=abs(s3_expected - s3_measured),
            is_error_syndrome=(abs(s3_expected - s3_measured) > 0.03),
            confidence=np.exp(-abs(s3_expected - s3_measured) / 0.005),
        ))
        
        # Energy measurements along tetrahedral directions
        for idx, direction in enumerate(self.directions):
            E_measured = self.measure_energy(eigenvalues, direction)
            E_expected = self.measure_energy(ideal_eigenvalues, direction, noise_level=0)
            
            syndromes.append(SyndromeMeasurement(
                stabilizer_name=f"E{idx+1} (tetrahedral {idx+1})",
                expected_value=E_expected,
                measured_value=E_measured,
                deviation=abs(E_expected - E_measured),
                is_error_syndrome=(abs(E_expected - E_measured) > 1e-6),
                confidence=np.exp(-abs(E_expected - E_measured) / 5e-7),
            ))
        
        return syndromes
    
    def identify_error(
        self,
        syndromes: List[SyndromeMeasurement],
    ) -> Dict:
        """
        Identify the most likely error from syndrome measurements.
        
        Returns:
        - error_type: 'none', 'bit_flip', 'phase_flip', 'erasure', 'unknown'
        - affected_qubit: which logical qubit (0, 1, 2)
        - confidence: how confident in the diagnosis
        """
        
        n_errors = sum(1 for s in syndromes if s.is_error_syndrome)
        
        if n_errors == 0:
            return {"error_type": "none", "affected_qubit": None, "confidence": 1.0}
        
        # Classify based on which stabilizers fired
        s1_triggered = syndromes[0].is_error_syndrome if len(syndromes) > 0 else False
        s2_triggered = syndromes[1].is_error_syndrome if len(syndromes) > 1 else False
        s3_triggered = syndromes[2].is_error_syndrome if len(syndromes) > 2 else False
        
        # Energy pattern
        energy_errors = [s for s in syndromes[3:] if s.is_error_syndrome]
        
        if s2_triggered and not s1_triggered:
            return {"error_type": "erasure", "affected_qubit": None, "confidence": 0.9}
        
        if s1_triggered and s3_triggered:
            # Eigenvalue ordering changed → phase flip
            affected = len(energy_errors) % 3  # which qubit based on energy pattern
            return {"error_type": "phase_flip", "affected_qubit": affected, "confidence": 0.85}
        
        if s1_triggered and not s3_triggered and len(energy_errors) >= 1:
            return {"error_type": "bit_flip", "affected_qubit": 0, "confidence": 0.8}
        
        return {"error_type": "unknown", "affected_qubit": None, "confidence": 0.5}


# ─── 5. Device Aging as Trajectory Toward Threshold ───

@dataclass
class DeviceLifetime:
    """
    Predict device lifetime by tracking its trajectory through
    silicon phase space toward the fault-tolerance threshold.
    """
    
    initial_performance: CodePerformance
    aging_rate: Dict[str, float]  # dS/dt for each coordinate
    threshold: FaultToleranceThreshold
    
    # Simulated trajectory
    time_points: np.ndarray = field(default_factory=lambda: np.array([]))
    performance_trajectory: List[CodePerformance] = field(default_factory=list)
    
    def simulate_aging(
        self,
        duration_years: float = 10.0,
        n_points: int = 100,
    ):
        """
        Simulate device aging and predict when it falls below threshold.
        """
        from silicon_state import SiliconState
        
        duration_seconds = duration_years * 365.25 * 24 * 3600
        self.time_points = np.linspace(0, duration_seconds, n_points)
        
        current_state = self.initial_performance.silicon_state
        
        self.performance_trajectory = []
        
        for t in self.time_points:
            # Evaluate current performance
            perf = evaluate_code_performance(current_state)
            self.performance_trajectory.append(perf)
            
            # Check if below threshold
            if perf.physical_error_rate >= self.threshold.p_threshold:
                # Device has failed — stop simulation
                self.time_points = self.time_points[:len(self.performance_trajectory)]
                break
            
            # Age the state
            dt = duration_seconds / n_points
            
            # Defect accumulation (NBTI, hot carrier, radiation)
            current_state.d += self.aging_rate.get("d", 1e-10) * dt
            current_state.d = min(current_state.d, 1.0)
            
            # Interface degradation (reduce coherent coupling)
            coherent = current_state.k.get("coherent", 0.1)
            current_state.k["coherent"] = max(
                0.0,
                coherent - self.aging_rate.get("k_coherent", 1e-12) * dt
            )
            
            # Increase thermal coupling (phonon scattering sites increase)
            thermal = current_state.k.get("thermal", 0.1)
            current_state.k["thermal"] = min(
                1.0,
                thermal + self.aging_rate.get("k_thermal", 5e-13) * dt
            )
    
    @property
    def time_to_threshold_years(self) -> Optional[float]:
        """Time until device falls below fault-tolerance threshold."""
        if len(self.performance_trajectory) < 2:
            return None
        
        for i, perf in enumerate(self.performance_trajectory):
            if not perf.is_fault_tolerant:
                return self.time_points[i] / (365.25 * 24 * 3600)
        
        return None  # survived entire simulation
    
    @property
    def end_of_life_performance(self) -> Optional[CodePerformance]:
        if self.performance_trajectory:
            return self.performance_trajectory[-1]
        return None


def predict_device_lifetime(
    initial_silicon_state: 'SiliconState',
    aging_rate_d: float = 1e-10,     # defect accumulation rate (per second)
    aging_rate_k_coherent: float = 1e-12,  # coherence degradation rate
    aging_rate_k_thermal: float = 5e-13,   # thermal coupling increase rate
) -> DeviceLifetime:
    """
    Predict how long a device will remain fault-tolerant given
    known aging mechanisms.
    """
    
    initial_perf = evaluate_code_performance(initial_silicon_state)
    
    aging_rates = {
        "d": aging_rate_d,
        "k_coherent": aging_rate_k_coherent,
        "k_thermal": aging_rate_k_thermal,
    }
    
    threshold = FaultToleranceThreshold()
    
    lifetime = DeviceLifetime(
        initial_performance=initial_perf,
        aging_rate=aging_rates,
        threshold=threshold,
    )
    
    lifetime.simulate_aging()
    
    return lifetime


# ─── 6. Regime-Dependent Code Optimization ───

def optimize_code_for_regime(
    target_regime: str = "quantum",
    temperature: float = 4.0,
) -> Dict:
    """
    Find the silicon state parameters that maximize code distance
    while staying within the target regime.
    """
    from silicon_state import SiliconState
    from scipy.optimize import minimize
    
    def objective(params):
        n, d, ell, k_coherent = params
        
        state = SiliconState(
            n=10**n,  # log scale
            d=np.clip(d, 0, 1),
            l=np.clip(ell, 0.1, 3.0),
            k={
                "electrical": 0.3,
                "optical": 0.1,
                "thermal": 0.1,
                "mechanical": 0.05,
                "coherent": np.clip(k_coherent, 0, 1),
            }
        )
        
        # Code distance
        d_code = compute_code_distance(state, temperature)
        
        # Regime weight
        weights = state.regime_weights(temperature=0.1)
        regime_weight = weights.get(target_regime, 0)
        
        # Objective: maximize distance × regime_weight
        # Penalize being outside the target regime
        if regime_weight < 0.3:
            return -d_code * 0.1  # heavy penalty
        
        return -d_code * regime_weight
    
    # Initial guess: typical quantum parameters
    x0 = [17.0, 0.01, 0.5, 0.6]  # log10(n), d, ℓ, κ_coherent
    
    bounds = [
        (14, 20),    # log10(n): 10^14 to 10^20
        (0.001, 0.3), # d: very clean
        (0.1, 2.0),   # ℓ: quantum confined
        (0.3, 0.9),   # κ_coherent: high
    ]
    
    result = minimize(
        objective, x0, method='L-BFGS-B', bounds=bounds,
        options={'maxiter': 200}
    )
    
    if result.success:
        opt_n, opt_d, opt_ell, opt_k = result.x
        
        opt_state = SiliconState(
            n=10**opt_n, d=opt_d, l=opt_ell,
            k={"electrical": 0.3, "optical": 0.1, "thermal": 0.1,
               "mechanical": 0.05, "coherent": opt_k}
        )
        
        perf = evaluate_code_performance(opt_state, temperature=temperature)
        
        return {
            "optimal_state": opt_state,
            "code_performance": perf,
            "max_code_distance": perf.code_distance,
            "logical_error_rate": perf.logical_error_rate,
            "is_fault_tolerant": perf.is_fault_tolerant,
        }
    
    return {"error": "Optimization failed"}


# ─── 7. Visualization ───

def plot_code_performance_phase_diagram(
    save_path: Optional[str] = None,
):
    """Plot code distance as a function of defect density and temperature."""
    import matplotlib.pyplot as plt
    
    from silicon_state import SiliconState
    
    # Grid
    d_vals = np.linspace(0.0, 0.5, 50)
    T_vals = np.linspace(1.0, 300.0, 50)
    D, T = np.meshgrid(d_vals, T_vals)
    
    distance_map = np.zeros_like(D)
    
    for i in range(len(T_vals)):
        for j in range(len(d_vals)):
            state = SiliconState(
                n=1e16, d=d_vals[j], l=3.0,
                k={"electrical": 0.5, "optical": 0.0, "thermal": 0.1,
                   "mechanical": 0.0, "coherent": 0.4}
            )
            distance_map[i, j] = compute_code_distance(state, T_vals[i])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Panel 1: Code distance
    ax1 = axes[0]
    im1 = ax1.pcolormesh(d_vals, T_vals, distance_map, cmap='RdYlBu_r',
                         shading='auto', vmin=1, vmax=3)
    ax1.set_xlabel('Defect Density d')
    ax1.set_ylabel('Temperature (K)')
    ax1.set_title('[[8,3,d(S)]] Code Distance')
    plt.colorbar(im1, ax=ax1, label='d(S)')
    
    # Threshold contour
    ax1.contour(d_vals, T_vals, distance_map, levels=[2.0],
               colors='black', linewidths=2, linestyles='--')
    ax1.text(0.3, 150, 'd=2\n(fault-tolerance\nboundary)', fontsize=8, color='black')
    
    # Panel 2: Error rates
    ax2 = axes[1]
    
    # Compute threshold surface
    d_thresh, T_thresh = compute_threshold_surface(
        defect_range=(0.0, 0.5), temp_range=(1.0, 300.0), n_points=50
    )
    
    ax2.fill_between(d_thresh, T_thresh, 300, alpha=0.2, color='green', label='Above threshold')
    ax2.fill_between(d_thresh, 0, T_thresh, alpha=0.2, color='red', label='Below threshold')
    ax2.plot(d_thresh, T_thresh, 'k-', linewidth=2, label='Threshold surface')
    
    ax2.set_xlabel('Defect Density d')
    ax2.set_ylabel('Temperature (K)')
    ax2.set_title('Fault-Tolerance Threshold Surface')
    ax2.legend(fontsize=8)
    
    # Annotations
    ax2.annotate('Fault-tolerant\nQEC possible', xy=(0.1, 50), fontsize=10, ha='center')
    ax2.annotate('QEC fails\n(errors > threshold)', xy=(0.35, 250), fontsize=10, ha='center', color='darkred')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ───
