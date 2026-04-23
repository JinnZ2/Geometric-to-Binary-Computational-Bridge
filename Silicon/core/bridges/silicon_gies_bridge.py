# silicon_gies_bridge.py
"""
Bridge between GIES geometric encoding and silicon manifold pipeline.

Connects three layers:
  1. GIES OctahedralState → SiliconState (geometric → physical regime)
  2. Hardware bridge DFT/FRET → SiliconState validation
  3. SiliconState → GIES encoding strategy selection
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class SiliconState:
    """Compact silicon state model used by the bridge pipeline."""

    n: float
    d: float
    l: float
    k: Dict[str, float]
    _last_eigenvalues: Optional[np.ndarray] = None

    def regime_weights(self, temperature: float = 0.1) -> Dict[str, float]:
        log_n = np.log10(max(self.n, 1.0))
        optical = float(self.k.get("optical", 0.0))
        thermal = float(self.k.get("thermal", 0.0))
        coherent = float(self.k.get("coherent", 0.0))
        electrical = float(self.k.get("electrical", 0.0))
        mechanical = float(self.k.get("mechanical", 0.0))
        magnetic = float(self.k.get("magnetic", 0.0))

        semiconductor = (
            1.2 / (1.0 + np.exp(2.0 * abs(log_n - 16.5) - 4.0))
            * 1.0 / (1.0 + np.exp((self.d - 0.25) * 10.0))
            * (0.5 + 0.5 * electrical)
        )
        metallic = 1.0 / (1.0 + np.exp(-(log_n - 19.0) * 3.0)) * (0.5 + 0.5 * electrical)
        quantum = (
            1.0 / (1.0 + np.exp(-(coherent - 0.25) * 8.0))
            * 1.0 / (1.0 + np.exp((self.d - 0.18) * 14.0))
            * 1.0 / (1.0 + np.exp((self.l - 1.2) * 4.0))
            * 1.0 / (1.0 + np.exp((temperature - 0.18) * 12.0))
        )
        photonic = (0.2 + optical) * (0.7 + 0.3 * np.tanh(self.l - 1.2))
        defect_dominated = 1.0 / (1.0 + np.exp(-(self.d - 0.35) * 10.0)) * (0.6 + 0.4 * thermal)
        mechanical_regime = (0.2 + mechanical + 0.2 * magnetic) * (0.7 + 0.3 * np.tanh(self.l - 2.0))

        raw_weights = {
            "semiconductor": max(0.0, float(semiconductor)),
            "metallic": max(0.0, float(metallic)),
            "quantum": max(0.0, float(quantum)),
            "photonic": max(0.0, float(photonic)),
            "defect_dominated": max(0.0, float(defect_dominated)),
            "mechanical": max(0.0, float(mechanical_regime)),
        }
        total = sum(raw_weights.values())
        if total <= 0:
            return {name: 0.0 for name in raw_weights}
        return {name: value / total for name, value in raw_weights.items()}

    def dominant_regime(self, temperature: float = 0.1) -> str:
        weights = self.regime_weights(temperature=temperature)
        return max(weights, key=weights.get)

    def stability_metric(self) -> float:
        return float(np.exp(-self.d) * (1.0 + self.k.get("electrical", 0.0) + self.k.get("coherent", 0.0)) / (1.0 + self.k.get("thermal", 0.0)))

    def coherence_metric(self) -> float:
        return float((1.0 - min(self.d, 0.95)) * (0.5 + self.k.get("coherent", 0.0)) * (1.0 + 0.2 * self.k.get("optical", 0.0)))


def geometry_to_silicon_rigorous(
    field: np.ndarray,
    grid_spacing: float = 2.5e-10,
    temperature: float = 300.0,
) -> SiliconState:
    """Reduce a geometric field to a compact silicon manifold state."""
    field = np.asarray(field, dtype=float)
    centered = field - np.mean(field)
    spectral_scale = float(np.linalg.norm(centered))
    gradient_scale = float(np.mean(np.abs(np.gradient(field))))
    variance = float(np.var(field))

    carrier_density = 1e15 * (1.0 + 20.0 * spectral_scale + 5.0 * gradient_scale)
    defect_density = float(np.clip(0.05 + 0.8 * variance + 0.1 * gradient_scale, 0.0, 1.0))
    effective_dimension = float(np.clip(0.8 + 2.5 * spectral_scale + 0.5 * grid_spacing / 1e-10, 0.2, 6.0))

    couplings = {
        "electrical": float(np.clip(0.25 + 0.5 * spectral_scale, 0.0, 1.0)),
        "optical": float(np.clip(0.15 + 0.6 * variance, 0.0, 1.0)),
        "thermal": float(np.clip(temperature / 1200.0 + 0.2 * variance, 0.0, 1.0)),
        "mechanical": float(np.clip(0.2 + 0.5 * gradient_scale, 0.0, 1.0)),
        "coherent": float(np.clip(0.7 - defect_density * 0.6 - temperature / 900.0, 0.0, 1.0)),
    }

    total = sum(couplings.values())
    if total > 1.0:
        couplings = {key: value / total for key, value in couplings.items()}

    return SiliconState(
        n=float(carrier_density),
        d=defect_density,
        l=effective_dimension,
        k=couplings,
    )


# GIES types (inline for self-containment, reference your actual modules)
OCTAHEDRAL_POSITIONS = {
    0: (0.25, 0.25, 0.25),   1: (0.25, -0.25, 0.25),
    2: (-0.25, 0.25, 0.25),  3: (-0.25, -0.25, 0.25),
    4: (0.25, 0.25, -0.25),  5: (0.25, -0.25, -0.25),
    6: (-0.25, 0.25, -0.25), 7: (-0.25, -0.25, -0.25),
}

# ─── 1. OctahedralState → SiliconState mapper ───

def octahedral_state_to_silicon_state(
    state_index: int,
    B_field: Optional[np.ndarray] = None,
    temperature: float = 300.0,
    strain_pct: float = 0.0,
    d_ErP: float = 4.8,
) -> Tuple[SiliconState, Dict]:
    """
    Maps an octahedral geometric state to the silicon phase-space manifold.
    
    The octahedron's 8 vertices form a geometric field F(x) = {±¼, ±¼, ±¼}.
    This field's spectral and correlation properties determine the effective
    silicon state coordinates.
    
    Parameters
    ----------
    state_index : int
        Octahedral state index (0-7), mapping to 3-bit binary.
    B_field : (3,) array, optional
        External magnetic field (T). Enables magnetic coupling contribution.
    temperature : float
        Temperature (K).
    strain_pct : float
        Biaxial strain (%) from DFT framework.
    d_ErP : float
        Er-P separation distance (Å) for FRET coupling.
    
    Returns
    -------
    silicon_state : SiliconState
        The mapped silicon phase-space coordinates.
    diagnostics : dict
        Intermediate physical quantities for validation.
    """
    
    if not 0 <= state_index <= 7:
        raise ValueError(f"State index must be 0-7, got {state_index}")
    
    position = np.array(OCTAHEDRAL_POSITIONS[state_index])
    binary = format(state_index, '03b')
    
    # ── Construct geometric field from octahedral state ──
    # The octahedron's 8 vertices define a 2×2×2 field on a cubic lattice
    field = np.zeros((2, 2, 2))
    for idx, pos in OCTAHEDRAL_POSITIONS.items():
        i = 0 if pos[0] < 0 else 1
        j = 0 if pos[1] < 0 else 1
        k = 0 if pos[2] < 0 else 1
        # Field value = signed distance from origin along position vector
        field[i, j, k] = np.dot(pos, position)  # projection onto state vector
    
    # ── Compute tensor properties ──
    tensor = np.outer(position, position)
    eigenvalues, eigenvectors = np.linalg.eigh(tensor)
    
    # ── Map to SiliconState via rigorous reduction ──
    silicon_state = geometry_to_silicon_rigorous(
        field,
        grid_spacing=2.5e-10,  # ~half lattice constant of Si
        temperature=temperature,
    )
    silicon_state._last_eigenvalues = eigenvalues
    
    # ── Augment coupling vector with magnetic contribution ──
    if B_field is not None:
        B = np.asarray(B_field, dtype=float)
        # Physical magnetic energy: E_mag = -μ_B × g × λ_i × B_i²
        MU_BOHR = 5.7883818012e-5  # eV/T
        G_FACTOR = 2.0023193
        
        # Align B components with eigenvalue ordering
        B_sq = np.sort(B**2)[::-1]
        E_mag = -MU_BOHR * G_FACTOR * float(np.dot(eigenvalues, B_sq))
        
        # Magnetic coupling strength (normalized)
        k_magnetic = np.clip(np.abs(E_mag) / 1e-4, 0.0, 0.5)
        silicon_state.k["magnetic"] = float(k_magnetic)
        
        # Renormalize couplings
        total = sum(silicon_state.k.values())
        if total > 1.0:
            silicon_state.k = {k: v/total for k, v in silicon_state.k.items()}
    
    # ── Apply FRET contribution to defect density ──
    # FRET coupling modifies the effective disorder landscape
    if d_ErP > 0:
        R_0 = 15.0  # Förster radius (Å)
        delta_E = 4.135667696e-15 * 1e12  # ~4.1 meV
        U_fret = delta_E * (R_0 / d_ErP)**6
        # FRET energy fluctuation acts as effective disorder
        fret_disorder = np.clip(U_fret / 0.01, 0.0, 0.3)
        silicon_state.d = np.clip(silicon_state.d + fret_disorder, 0.0, 1.0)
    
    # ── Diagnostics ──
    diagnostics = {
        "state_index": state_index,
        "binary": binary,
        "position": position.tolist(),
        "eigenvalues": eigenvalues.tolist(),
        "tensor_trace": float(np.trace(tensor)),
        "tensor_det": float(np.linalg.det(tensor)),
        "field_mean": float(np.mean(field)),
        "field_std": float(np.std(field)),
        "E_mag_eV": float(E_mag) if B_field is not None else None,
        "U_fret_eV": float(U_fret) if d_ErP > 0 else None,
    }
    
    return silicon_state, diagnostics


def all_octahedral_states_to_silicon(
    B_field: Optional[np.ndarray] = None,
    temperature: float = 300.0,
    strain_pct: float = 0.0,
    d_ErP: float = 4.8,
) -> Dict[int, Tuple[SiliconState, Dict]]:
    """
    Map all 8 octahedral states to silicon phase space.
    
    Returns
    -------
    Dict mapping state_index → (SiliconState, diagnostics)
    """
    results = {}
    for idx in range(8):
        results[idx] = octahedral_state_to_silicon_state(
            idx, B_field, temperature, strain_pct, d_ErP
        )
    return results


# ─── 2. GIES encoding strategy selector ───

@dataclass
class GIESEncodingStrategy:
    """Encoding strategy selected by silicon regime."""
    regime: str
    encoding_mode: str       # 'threshold', 'phase', 'stochastic', 'frequency'
    operator: str            # '|' or '/'
    symbol_preference: str   # 'O', 'I', 'X', 'Δ'
    redundancy: int          # error-correction redundancy level
    confidence_threshold: float


def select_gies_strategy(silicon_state: SiliconState) -> GIESEncodingStrategy:
    """
    Select GIES encoding strategy based on silicon regime.
    
    Different silicon regimes favor different geometric encoding modes:
    - Semiconductor → threshold logic, '|' operator, 'O' symbol
    - Quantum → phase encoding, '|' operator, 'Δ' symbol
    - Defect-dominated → stochastic encoding, '/' operator, 'X' symbol
    - Photonic → frequency encoding, '/' operator, 'I' symbol
    """
    
    weights = silicon_state.regime_weights(temperature=0.1)
    dominant = max(weights, key=weights.get)
    
    strategies = {
        "semiconductor": GIESEncodingStrategy(
            regime="semiconductor",
            encoding_mode="threshold",
            operator="|",
            symbol_preference="O",
            redundancy=1,
            confidence_threshold=0.5,
        ),
        "metallic": GIESEncodingStrategy(
            regime="metallic",
            encoding_mode="stochastic",  # chaotic conduction → stochastic encoding
            operator="/",
            symbol_preference="X",
            redundancy=3,  # high redundancy to counter noise
            confidence_threshold=0.3,
        ),
        "quantum": GIESEncodingStrategy(
            regime="quantum",
            encoding_mode="phase",  # phase-sensitive encoding
            operator="|",
            symbol_preference="Δ",  # delta for quantum superposition
            redundancy=2,
            confidence_threshold=0.6,
        ),
        "photonic": GIESEncodingStrategy(
            regime="photonic",
            encoding_mode="frequency",  # wavelength-division encoding
            operator="/",
            symbol_preference="I",
            redundancy=1,
            confidence_threshold=0.7,
        ),
        "defect_dominated": GIESEncodingStrategy(
            regime="defect_dominated",
            encoding_mode="stochastic",
            operator="/",
            symbol_preference="X",
            redundancy=4,  # maximum redundancy for defect tolerance
            confidence_threshold=0.2,
        ),
        "mechanical": GIESEncodingStrategy(
            regime="mechanical",
            encoding_mode="threshold",
            operator="|",
            symbol_preference="O",
            redundancy=2,
            confidence_threshold=0.5,
        ),
    }
    
    # For mixed regimes, blend strategies
    if weights.get(dominant, 0) < 0.6:
        # Near phase boundary: use blended strategy with higher redundancy
        base = strategies.get(dominant, strategies["semiconductor"])
        return GIESEncodingStrategy(
            regime=f"blended({dominant})",
            encoding_mode=base.encoding_mode,
            operator=base.operator,
            symbol_preference=base.symbol_preference,
            redundancy=base.redundancy + 1,  # extra redundancy at boundaries
            confidence_threshold=base.confidence_threshold * 0.8,
        )
    
    return strategies.get(dominant, strategies["semiconductor"])


# ─── 3. Silicon state → GIES token encoder ───

def silicon_state_to_gies_token(
    silicon_state: SiliconState,
    state_index: int,
    strategy: Optional[GIESEncodingStrategy] = None,
) -> str:
    """
    Encode a silicon state + octahedral index into a GIES token
    with regime-appropriate operator and symbol.
    
    Example:
      silicon_state in quantum regime, state_index=5 (101)
      → "101|Δ" (phase-encoded quantum token)
    
      silicon_state in defect regime, state_index=5
      → "101/X" (stochastic defect-tolerant token)
    """
    
    if strategy is None:
        strategy = select_gies_strategy(silicon_state)
    
    binary = format(state_index, '03b')
    return f"{binary}{strategy.operator}{strategy.symbol_preference}"


def silicon_state_to_gies_stream(
    silicon_state: SiliconState,
    state_indices: List[int],
) -> List[str]:
    """
    Encode a sequence of octahedral states using regime-selected encoding.
    """
    strategy = select_gies_strategy(silicon_state)
    return [
        f"{format(idx, '03b')}{strategy.operator}{strategy.symbol_preference}"
        for idx in state_indices
    ]


# ─── 4. Hardware bridge validation ───

@dataclass
class HardwareValidation:
    """Validation results from hardware bridge physics."""
    k_well: float           # eV/Å² — confinement stiffness
    k_fret: float           # eV/Å² — FRET contribution
    k_total: float          # eV/Å² — combined stiffness
    sigma_T: float          # Å — thermal displacement
    T2_ms: float            # ms — coherence time
    E_mag: Optional[float]  # eV — magnetic energy (if B_field present)
    
    def validates_regime(self, silicon_state: SiliconState) -> Dict[str, bool]:
        """
        Check if hardware physics supports the silicon regime classification.
        """
        checks = {}
        
        # Quantum regime requires T₂ > 1 ms
        weights = silicon_state.regime_weights()
        if weights.get("quantum", 0) > 0.3:
            checks["T2_sufficient_for_quantum"] = self.T2_ms > 1.0
        
        # Semiconductor regime requires k_well > 1 eV/Å²
        if weights.get("semiconductor", 0) > 0.3:
            checks["kwell_sufficient_for_semiconductor"] = self.k_well > 1.0
        
        # Defect-dominated regime: high sigma_T means large thermal disorder
        if weights.get("defect_dominated", 0) > 0.3:
            checks["thermal_disorder_consistent"] = self.sigma_T > 0.05  # Å
        
        # Metallic regime: low k_well means soft potential
        if weights.get("metallic", 0) > 0.3:
            checks["soft_potential_for_metallic"] = self.k_total < 5.0
        
        checks["all_consistent"] = all(checks.values()) if checks else True
        return checks


def validate_silicon_state_with_hardware(
    silicon_state: SiliconState,
    k_dft: float,
    d_ErP: float,
    B_field: Optional[np.ndarray] = None,
    temperature: float = 300.0,
) -> HardwareValidation:
    """
    Validate a silicon state classification using hardware bridge physics.
    
    Uses the DFT + FRET + magnetic chain from hardware_bridge.py
    to compute physical quantities and check regime consistency.
    """
    
    # FRET contribution
    R_0 = 15.0
    delta_E = 4.135667696e-15 * 1e12
    k_fret = 42.0 * delta_E * R_0**6 / d_ErP**8
    k_total = k_dft + k_fret
    
    # Thermal displacement
    K_B = 8.617333e-5
    sigma_T = np.sqrt(K_B * temperature / k_total)
    
    # T₂ estimation (from hardware bridge model)
    K_WELL_REF = 8.5
    GAMMA_PH_0 = 4.99
    gamma_ph = GAMMA_PH_0 * (K_WELL_REF / k_total) * (temperature / 300.0)
    gamma_total = gamma_ph + 0.90 + 0.12
    T2_ms = 1000.0 / gamma_total
    
    # Magnetic energy
    E_mag = None
    if B_field is not None and hasattr(silicon_state, '_last_eigenvalues'):
        MU_BOHR = 5.7883818012e-5
        G_FACTOR = 2.0023193
        B = np.asarray(B_field)
        B_sq = np.sort(B**2)[::-1]
        eigenvalues = silicon_state._last_eigenvalues
        E_mag = -MU_BOHR * G_FACTOR * float(np.dot(eigenvalues, B_sq))
    
    return HardwareValidation(
        k_well=k_dft,
        k_fret=k_fret,
        k_total=k_total,
        sigma_T=sigma_T,
        T2_ms=T2_ms,
        E_mag=E_mag,
    )


# ─── 5. Full integrated pipeline ───

@dataclass
class IntegratedGIESResult:
    """Complete result from integrated GIES → Silicon → Hardware pipeline."""
    state_index: int
    binary: str
    gies_token: str
    silicon_state: SiliconState
    regime_weights: Dict[str, float]
    encoding_strategy: GIESEncodingStrategy
    hardware_validation: Optional[HardwareValidation]
    diagnostics: Dict
    consistency_checks: Dict[str, bool]


def run_integrated_pipeline(
    state_index: int,
    B_field: Optional[np.ndarray] = None,
    temperature: float = 300.0,
    strain_pct: float = 0.0,
    d_ErP: float = 4.8,
    k_dft: Optional[float] = None,
) -> IntegratedGIESResult:
    """
    Full integrated pipeline:
    
    Octahedral State → Silicon Manifold → GIES Encoding → Hardware Validation
    """
    
    # Step 1: Octahedral → Silicon state
    silicon_state, diagnostics = octahedral_state_to_silicon_state(
        state_index, B_field, temperature, strain_pct, d_ErP
    )
    
    # Step 2: Silicon regime → GIES encoding strategy
    strategy = select_gies_strategy(silicon_state)
    
    # Step 3: Generate GIES token
    gies_token = silicon_state_to_gies_token(silicon_state, state_index, strategy)
    
    # Step 4: Hardware validation (if k_dft provided)
    hardware_val = None
    consistency = {}
    if k_dft is not None:
        hardware_val = validate_silicon_state_with_hardware(
            silicon_state, k_dft, d_ErP, B_field, temperature
        )
        consistency = hardware_val.validates_regime(silicon_state)
    
    return IntegratedGIESResult(
        state_index=state_index,
        binary=diagnostics["binary"],
        gies_token=gies_token,
        silicon_state=silicon_state,
        regime_weights=silicon_state.regime_weights(temperature=0.1),
        encoding_strategy=strategy,
        hardware_validation=hardware_val,
        diagnostics=diagnostics,
        consistency_checks=consistency,
    )


# ─── 6. Octahedral ensemble → Silicon manifold coverage ───

def octahedral_ensemble_silicon_coverage(
    B_field: Optional[np.ndarray] = None,
    temperature: float = 300.0,
) -> Dict:
    """
    Analyze how the 8 octahedral states cover the silicon regime manifold.
    
    Identifies:
    - Which octahedral states map to which silicon regimes
    - Regime coverage gaps
    - Optimal states for each computational paradigm
    """
    
    all_states = all_octahedral_states_to_silicon(B_field=B_field, temperature=temperature)
    
    coverage = {
        "state_regime_map": {},
        "regime_states": {},
        "coverage_stats": {},
    }
    
    for idx, (silicon_state, diag) in all_states.items():
        dominant = silicon_state.dominant_regime()
        coverage["state_regime_map"][idx] = dominant
        
        if dominant not in coverage["regime_states"]:
            coverage["regime_states"][dominant] = []
        coverage["regime_states"][dominant].append({
            "index": idx,
            "binary": diag["binary"],
            "stability": silicon_state.stability_metric(),
            "coherence": silicon_state.coherence_metric(),
        })
    
    # Coverage statistics
    total_regimes = 6
    covered_regimes = len(coverage["regime_states"])
    coverage["coverage_stats"] = {
        "total_regimes": total_regimes,
        "covered_regimes": covered_regimes,
        "coverage_fraction": covered_regimes / total_regimes,
        "uncovered_regimes": [
            r for r in ["semiconductor", "metallic", "quantum", 
                        "photonic", "defect_dominated", "mechanical"]
            if r not in coverage["regime_states"]
        ],
    }
    
    return coverage


# ─── 7. Visualization of GIES-Silicon mapping ───

def plot_gies_silicon_mapping(
    results: Dict[int, IntegratedGIESResult],
    save_path: Optional[str] = None,
):
    """Visualize how octahedral states map onto the silicon regime manifold."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    import matplotlib.gridspec as gridspec
    
    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 4, figure=fig, hspace=0.4, wspace=0.4)
    
    REGIME_COLORS = {
        "semiconductor": "#2E86AB", "metallic": "#A23B72",
        "quantum": "#F18F01", "photonic": "#C73E1D",
        "defect_dominated": "#6B4D57", "mechanical": "#58A449",
    }
    
    for idx in range(8):
        if idx not in results:
            continue
        
        ax = fig.add_subplot(gs[idx // 4, idx % 4])
        result = results[idx]
        
        # Regime color background
        regime = result.silicon_state.dominant_regime()
        color = REGIME_COLORS.get(regime, "#888888")
        ax.set_facecolor(color + "15")  # very light tint
        
        # Title
        ax.set_title(f"State {idx} ({result.binary})\n→ {regime}",
                    fontweight='bold', fontsize=11, color=color)
        
        # GIES token
        ax.text(0.5, 0.85, result.gies_token, transform=ax.transAxes,
               ha='center', fontsize=18, fontfamily='monospace',
               bbox=dict(boxstyle='round', facecolor='white', edgecolor=color, alpha=0.9))
        
        # Coupling vector as horizontal bars
        couplings = result.silicon_state.k
        y_pos = 0.65
        for mode, strength in sorted(couplings.items(), key=lambda x: -x[1]):
            if strength > 0.01:
                ax.barh(y_pos, strength, height=0.06, color=color, alpha=0.7)
                ax.text(0.01, y_pos, mode, fontsize=7, va='center')
                y_pos -= 0.08
        
        # Regime weights
        weights = result.regime_weights
        y_pos = 0.35
        for r, w in sorted(weights.items(), key=lambda x: -x[1])[:3]:
            if w > 0.05:
                ax.text(0.5, y_pos, f"{r}: {w:.2f}", transform=ax.transAxes,
                       ha='center', fontsize=7, alpha=0.8)
                y_pos -= 0.07
        
        # Hardware validation
        if result.hardware_validation:
            hv = result.hardware_validation
            ax.text(0.5, 0.08, f"T₂={hv.T2_ms:.1f}ms | k={hv.k_total:.1f} eV/Å²",
                   transform=ax.transAxes, ha='center', fontsize=7,
                   color='green' if hv.T2_ms > 1 else 'orange')
        
        ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1)
        ax.axis('off')
    
    fig.suptitle('Octahedral States → Silicon Regime Manifold', 
                fontsize=16, fontweight='bold', y=1.02)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ─── 8. Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("GIES ↔ Silicon Manifold Integration Demo")
    print("=" * 70)
    
    B_field = np.array([0.0, 0.0, 1.0])  # 1T along z
    
    # Single state mapping
    print("\n--- Single State: Octahedral(5) → Silicon ---")
    result = run_integrated_pipeline(
        state_index=5,
        B_field=B_field,
        temperature=4.0,  # cryogenic
        d_ErP=4.8,
        k_dft=8.5,
    )
    
    print(f"  Binary:           {result.binary}")
    print(f"  GIES Token:       {result.gies_token}")
    print(f"  Dominant Regime:  {result.silicon_state.dominant_regime()}")
    print(f"  Encoding Mode:    {result.encoding_strategy.encoding_mode}")
    print(f"  Redundancy:       {result.encoding_strategy.redundancy}")
    print(f"  Stability:        {result.silicon_state.stability_metric():.3f}")
    print(f"  Coherence:        {result.silicon_state.coherence_metric():.3f}")
    
    if result.hardware_validation:
        print(f"  T₂:               {result.hardware_validation.T2_ms:.1f} ms")
        print(f"  k_total:          {result.hardware_validation.k_total:.2f} eV/Å²")
        print(f"  Consistent:       {result.consistency_checks.get('all_consistent', 'N/A')}")
    
    # All states
    print("\n--- All 8 Octahedral States ---")
    all_results = {}
    for idx in range(8):
        all_results[idx] = run_integrated_pipeline(
            state_index=idx, B_field=B_field, temperature=4.0, d_ErP=4.8, k_dft=8.5
        )
    
    print(f"\n{'Idx':>4} {'Binary':>5} {'Token':>8} {'Regime':>20} {'T₂(ms)':>8} {'Stability':>10} {'Coherence':>10}")
    print("-" * 75)
    for idx, res in all_results.items():
        t2 = f"{res.hardware_validation.T2_ms:.1f}" if res.hardware_validation else "N/A"
        print(f"{idx:>4} {res.binary:>5} {res.gies_token:>8} "
              f"{res.silicon_state.dominant_regime():>20} {t2:>8} "
              f"{res.silicon_state.stability_metric():.3f}     "
              f"{res.silicon_state.coherence_metric():.3f}")
    
    # Coverage analysis
    print("\n--- Regime Coverage ---")
    coverage = octahedral_ensemble_silicon_coverage(B_field=B_field, temperature=4.0)
    for regime, states in coverage["regime_states"].items():
        print(f"  {regime}: {len(states)} states → {[s['binary'] for s in states]}")
    print(f"  Coverage: {coverage['coverage_stats']['covered_regimes']}/"
          f"{coverage['coverage_stats']['total_regimes']} regimes")
    
    # Visualization
    try:
        plot_gies_silicon_mapping(all_results, save_path="gies_silicon_mapping.png")
        print("\n  → Saved visualization: gies_silicon_mapping.png")
    except Exception as e:
        print(f"\n  Visualization skipped: {e}")
