# silicon_gies_phase_diagram.py
"""
Silicon-GIES Phase Diagram: Where Geometry Selects Physics

Computes and analyzes the (strain, temperature) phase diagram for all
8 octahedral states simultaneously. Reveals:

1. Regime consensus regions: where all states agree → robust design zones
2. Regime ambiguity regions: where different states map to different regimes
   → geometry selects physics (the inversion zone)
3. Phase boundaries: where the dominant regime changes for each state
4. Coexistence topologies: the structure of ambiguity regions

The key discovery: at certain (strain, T) points, the choice of which
octahedral state you encode determines which physical regime you're in.
This means geometric encoding is not passive — it's an active control
parameter on equal footing with doping, strain, and temperature.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, field
from scipy.stats import entropy as shannon_entropy
from scipy.ndimage import label, find_objects, gaussian_filter
import warnings


# ─── 1. Phase Diagram Computation ───

@dataclass
class PhaseDiagram:
    """Complete (strain, T) phase diagram for all 8 octahedral states."""
    
    # Grid coordinates
    strain_range: Tuple[float, float]
    temp_range: Tuple[float, float]
    strains: np.ndarray          # shape (resolution,)
    temps: np.ndarray            # shape (resolution,)
    resolution: int
    
    # Raw data
    diagram: np.ndarray          # (8, res, res) — regime classification per state
    regime_names: List[str]      # index → regime name
    regime_to_int: Dict[str, int]
    int_to_regime: Dict[int, str]
    
    # Derived
    consensus_map: np.ndarray    # (res, res) — -1 if no consensus, else regime int
    disagreement_map: np.ndarray # (res, res) — entropy of regime distribution
    n_active_regimes: np.ndarray # (res, res) — how many distinct regimes present
    
    # Per-state regime maps
    state_maps: Dict[int, np.ndarray]  # state_idx → (res, res) regime int map
    
    # Analysis
    consensus_fraction: float    # fraction of phase space with full consensus
    ambiguity_regions: List[Dict]  # connected regions of disagreement
    phase_boundaries: Dict[int, List]  # per-state phase boundary contours
    
    def get_consensus_regime(self, i: int, j: int) -> Optional[str]:
        """Get the consensus regime at grid point (i,j), or None if no consensus."""
        if self.consensus_map[i, j] >= 0:
            return self.int_to_regime[self.consensus_map[i, j]]
        return None
    
    def get_regime_distribution(self, i: int, j: int) -> Dict[str, int]:
        """Get the distribution of regimes across states at point (i,j)."""
        regimes = self.diagram[:, i, j]
        dist = {}
        for r in regimes:
            name = self.int_to_regime.get(r, "unknown")
            dist[name] = dist.get(name, 0) + 1
        return dist
    
    def point_is_ambiguous(self, strain: float, temp: float) -> Tuple[bool, float]:
        """
        Check if a specific (strain, temperature) point is in an ambiguity region.
        Returns (is_ambiguous, disagreement_entropy).
        """
        i = np.argmin(np.abs(self.strains - strain))
        j = np.argmin(np.abs(self.temps - temp))
        ent = self.disagreement_map[j, i]
        return ent > 0.1, ent


def compute_silicon_gies_phase_diagram(
    strain_range: Tuple[float, float] = (-3.0, 3.0),
    temp_range: Tuple[float, float] = (1.0, 500.0),
    resolution: int = 80,
    B_field: Optional[np.ndarray] = None,
    d_ErP: float = 4.8,
    k_dft: Optional[float] = None,
    verbose: bool = True,
) -> PhaseDiagram:
    """
    Compute the complete (strain, temperature) phase diagram for all
    8 octahedral states.
    
    This is the central computation that reveals where geometry selects physics.
    
    Parameters
    ----------
    strain_range : (min, max) in percent
    temp_range : (min, max) in Kelvin
    resolution : grid resolution per axis
    B_field : magnetic field vector for states with magnetic coupling
    d_ErP : Er-P distance for FRET coupling
    k_dft : DFT confinement stiffness (if available)
    verbose : print progress
    
    Returns
    -------
    PhaseDiagram with full analysis
    """
    
    from silicon_state import SiliconState
    from silicon_gies_bridge import octahedral_state_to_silicon_state
    
    if B_field is None:
        B_field = np.array([0.0, 0.0, 0.1])  # small probe field
    
    # Grid
    strains = np.linspace(strain_range[0], strain_range[1], resolution)
    temps = np.linspace(temp_range[0], temp_range[1], resolution)
    
    # Storage
    diagram = np.zeros((8, resolution, resolution), dtype=int)
    regime_map = {}
    int_to_regime = {}
    
    # Coherence and stability maps per state (additional observables)
    coherence_maps = np.zeros((8, resolution, resolution))
    stability_maps = np.zeros((8, resolution, resolution))
    
    total_points = resolution * resolution * 8
    
    for i_strain, eps in enumerate(strains):
        if verbose and i_strain % 10 == 0:
            print(f"  Strain: {eps:+.2f}% ({i_strain+1}/{resolution})")
        
        for j_temp, T in enumerate(temps):
            for idx in range(8):
                try:
                    silicon_state, diagnostics = octahedral_state_to_silicon_state(
                        idx,
                        B_field=B_field,
                        temperature=T,
                        strain_pct=eps,
                        d_ErP=d_ErP,
                    )
                    
                    regime = silicon_state.dominant_regime()
                    
                    if regime not in regime_map:
                        regime_id = len(regime_map)
                        regime_map[regime] = regime_id
                        int_to_regime[regime_id] = regime
                    
                    diagram[idx, j_temp, i_strain] = regime_map[regime]
                    coherence_maps[idx, j_temp, i_strain] = silicon_state.coherence_metric()
                    stability_maps[idx, j_temp, i_strain] = silicon_state.stability_metric()
                    
                except Exception as e:
                    diagram[idx, j_temp, i_strain] = -1
    
    # ── Derived maps ──
    
    # Consensus map: regime at points where all 8 states agree, -1 otherwise
    consensus_map = np.full((resolution, resolution), -1, dtype=int)
    n_active_regimes = np.zeros((resolution, resolution), dtype=int)
    
    for i in range(resolution):
        for j in range(resolution):
            regimes_at_point = diagram[:, j, i]
            
            # Count unique regimes (excluding errors)
            valid = regimes_at_point[regimes_at_point >= 0]
            unique_regimes = np.unique(valid)
            n_active_regimes[j, i] = len(unique_regimes)
            
            # Consensus if exactly one regime
            if len(unique_regimes) == 1:
                consensus_map[j, i] = unique_regimes[0]
    
    # Disagreement map (entropy of regime distribution)
    disagreement_map = np.zeros((resolution, resolution))
    
    for i in range(resolution):
        for j in range(resolution):
            regimes_at_point = diagram[:, j, i]
            valid = regimes_at_point[regimes_at_point >= 0]
            
            if len(valid) > 0:
                # Count frequencies
                counts = np.bincount(valid, minlength=len(regime_map))
                # Filter zeros for entropy calculation
                nonzero = counts[counts > 0]
                if len(nonzero) > 1:
                    disagreement_map[j, i] = shannon_entropy(nonzero, base=2)
                else:
                    disagreement_map[j, i] = 0.0
    
    # ── Per-state maps ──
    state_maps = {}
    for idx in range(8):
        state_maps[idx] = diagram[idx]
    
    # ── Consensus fraction ──
    n_consensus = np.sum(consensus_map >= 0)
    consensus_fraction = n_consensus / (resolution * resolution)
    
    # ── Ambiguity regions (connected components of disagreement) ──
    ambiguity_regions = find_ambiguity_regions(disagreement_map, strains, temps)
    
    # ── Phase boundaries per state ──
    phase_boundaries = {}
    for idx in range(8):
        boundaries = find_phase_boundaries(diagram[idx], strains, temps)
        phase_boundaries[idx] = boundaries
    
    return PhaseDiagram(
        strain_range=strain_range,
        temp_range=temp_range,
        strains=strains,
        temps=temps,
        resolution=resolution,
        diagram=diagram,
        regime_names=list(regime_map.keys()),
        regime_to_int=regime_map,
        int_to_regime=int_to_regime,
        consensus_map=consensus_map,
        disagreement_map=disagreement_map,
        n_active_regimes=n_active_regimes,
        state_maps=state_maps,
        consensus_fraction=consensus_fraction,
        ambiguity_regions=ambiguity_regions,
        phase_boundaries=phase_boundaries,
    )


# ─── 2. Ambiguity Region Detection ───

def find_ambiguity_regions(
    disagreement_map: np.ndarray,
    strains: np.ndarray,
    temps: np.ndarray,
    threshold: float = 0.3,
    min_area: int = 4,
) -> List[Dict]:
    """
    Find connected regions of high disagreement (ambiguity zones).
    
    Returns list of regions with:
    - bounding box in (strain, T) coordinates
    - area (number of grid points)
    - peak disagreement
    - center of mass
    """
    
    # Binary mask of ambiguous regions
    mask = disagreement_map > threshold
    
    # Label connected components
    labeled, n_regions = label(mask)
    
    regions = []
    slices = find_objects(labeled)
    
    for region_id in range(1, n_regions + 1):
        region_mask = labeled == region_id
        n_points = np.sum(region_mask)
        
        if n_points < min_area:
            continue
        
        # Indices
        j_indices, i_indices = np.where(region_mask)
        
        # Bounding box
        i_min, i_max = i_indices.min(), i_indices.max()
        j_min, j_max = j_indices.min(), j_indices.max()
        
        strain_min = strains[i_min]
        strain_max = strains[i_max]
        temp_min = temps[j_min]
        temp_max = temps[j_max]
        
        # Peak disagreement within region
        peak_disagreement = np.max(disagreement_map[region_mask])
        
        # Center of mass (weighted by disagreement)
        weights = disagreement_map[region_mask]
        com_i = np.average(i_indices, weights=weights)
        com_j = np.average(j_indices, weights=weights)
        
        # Regime distribution at center of mass
        com_i_int = int(np.clip(com_i, 0, len(strains)-1))
        com_j_int = int(np.clip(com_j, 0, len(temps)-1))
        
        regions.append({
            "region_id": region_id,
            "n_points": n_points,
            "strain_range": (strain_min, strain_max),
            "temp_range": (temp_min, temp_max),
            "center_strain": strains[com_i_int],
            "center_temp": temps[com_j_int],
            "peak_disagreement": peak_disagreement,
            "i_indices": i_indices,
            "j_indices": j_indices,
        })
    
    return regions


def find_phase_boundaries(
    state_map: np.ndarray,
    strains: np.ndarray,
    temps: np.ndarray,
) -> List[Dict]:
    """
    Find phase boundaries for a single octahedral state.
    
    A phase boundary is where the regime classification changes
    between adjacent grid points.
    """
    
    boundaries = []
    resolution = state_map.shape[1]
    
    # Horizontal boundaries (along strain)
    for j in range(state_map.shape[0] - 1):
        for i in range(resolution):
            if state_map[j, i] != state_map[j+1, i] and state_map[j, i] >= 0 and state_map[j+1, i] >= 0:
                boundaries.append({
                    "strain": strains[i],
                    "temp": (temps[j] + temps[j+1]) / 2,
                    "direction": "temperature",
                })
    
    # Vertical boundaries (along temperature)
    for j in range(state_map.shape[0]):
        for i in range(resolution - 1):
            if state_map[j, i] != state_map[j, i+1] and state_map[j, i] >= 0 and state_map[j, i+1] >= 0:
                boundaries.append({
                    "strain": (strains[i] + strains[i+1]) / 2,
                    "temp": temps[j],
                    "direction": "strain",
                })
    
    return boundaries


# ─── 3. Discovery: Geometry-Selects-Physics Zones ───

@dataclass
class GeometrySelectsPhysicsZone:
    """
    A region where the choice of octahedral state determines the physical regime.
    
    In these zones, the usual causal hierarchy is inverted:
    normally, physics (doping, strain, temperature) determines computation.
    Here, the geometric encoding choice determines which physics is active.
    """
    strain_center: float
    temp_center: float
    n_regimes_present: int
    regimes_present: List[str]
    state_to_regime: Dict[int, str]  # which state maps to which regime
    disagreement_entropy: float
    
    # Which regime does each state favor?
    @property
    def regime_controlled_by_state(self) -> bool:
        """True if individual states map to different regimes."""
        return len(set(self.state_to_regime.values())) > 1
    
    @property
    def controllable_regimes(self) -> List[str]:
        """Regimes that can be accessed by choosing a different state."""
        return sorted(set(self.state_to_regime.values()))


def find_geometry_selects_physics_zones(
    phase_diagram: PhaseDiagram,
    min_disagreement: float = 0.5,
    min_regimes: int = 3,
) -> List[GeometrySelectsPhysicsZone]:
    """
    Identify regions where geometric encoding selects the physical regime.
    
    These are points where:
    1. Different octahedral states map to DIFFERENT dominant regimes
    2. Multiple distinct regimes are accessible
    3. The disagreement entropy is high
    """
    
    zones = []
    
    resolution = phase_diagram.resolution
    
    for i in range(resolution):
        for j in range(resolution):
            ent = phase_diagram.disagreement_map[j, i]
            
            if ent < min_disagreement:
                continue
            
            # Get regimes at this point
            regimes_at_point = phase_diagram.diagram[:, j, i]
            valid = regimes_at_point[regimes_at_point >= 0]
            
            unique_regimes = np.unique(valid)
            if len(unique_regimes) < min_regimes:
                continue
            
            # Map state → regime
            state_to_regime = {}
            for idx in range(8):
                r_int = phase_diagram.diagram[idx, j, i]
                if r_int >= 0:
                    state_to_regime[idx] = phase_diagram.int_to_regime[r_int]
            
            regimes_present = [phase_diagram.int_to_regime[r] for r in unique_regimes]
            
            zones.append(GeometrySelectsPhysicsZone(
                strain_center=phase_diagram.strains[i],
                temp_center=phase_diagram.temps[j],
                n_regimes_present=len(unique_regimes),
                regimes_present=regimes_present,
                state_to_regime=state_to_regime,
                disagreement_entropy=ent,
            ))
    
    return zones


# ─── 4. Regime Transition Network ───

def build_regime_transition_network(
    phase_diagram: PhaseDiagram,
) -> Dict:
    """
    Build a network of regime transitions as a function of strain and temperature.
    
    Nodes: regimes
    Edges: transitions between regimes for individual octahedral states
    Edge weights: frequency of transition
    
    This reveals which regimes are "adjacent" in the phase diagram
    and which transitions are most common.
    """
    
    transitions = {}  # (regime_A, regime_B) → count
    
    for idx in range(8):
        state_map = phase_diagram.state_maps[idx]
        
        # Scan for transitions along temperature axis
        for i in range(phase_diagram.resolution):
            for j in range(phase_diagram.resolution - 1):
                r1 = state_map[j, i]
                r2 = state_map[j+1, i]
                
                if r1 >= 0 and r2 >= 0 and r1 != r2:
                    name1 = phase_diagram.int_to_regime[r1]
                    name2 = phase_diagram.int_to_regime[r2]
                    
                    # Canonical ordering
                    key = tuple(sorted([name1, name2]))
                    transitions[key] = transitions.get(key, 0) + 1
        
        # Scan for transitions along strain axis
        for j in range(phase_diagram.resolution):
            for i in range(phase_diagram.resolution - 1):
                r1 = state_map[j, i]
                r2 = state_map[j, i+1]
                
                if r1 >= 0 and r2 >= 0 and r1 != r2:
                    name1 = phase_diagram.int_to_regime[r1]
                    name2 = phase_diagram.int_to_regime[r2]
                    key = tuple(sorted([name1, name2]))
                    transitions[key] = transitions.get(key, 0) + 1
    
    return {
        "transitions": transitions,
        "regimes": phase_diagram.regime_names,
        "total_transitions": sum(transitions.values()),
    }


# ─── 5. Stability Analysis ───

def compute_regime_stability_map(
    phase_diagram: PhaseDiagram,
) -> Dict[str, float]:
    """
    Compute how much of the phase diagram each regime occupies,
    both in consensus and total.
    """
    
    total_points = phase_diagram.resolution ** 2
    regime_areas = {}
    consensus_areas = {}
    
    for regime_name in phase_diagram.regime_names:
        regime_int = phase_diagram.regime_to_int[regime_name]
        
        # Total: fraction of (state, strain, temp) points in this regime
        total_count = np.sum(phase_diagram.diagram == regime_int)
        regime_areas[regime_name] = total_count / (8 * total_points)
        
        # Consensus: fraction of points where ALL states agree on this regime
        consensus_count = np.sum(phase_diagram.consensus_map == regime_int)
        consensus_areas[regime_name] = consensus_count / total_points
    
    return {
        "total_areas": regime_areas,
        "consensus_areas": consensus_areas,
        "total_consensus_fraction": phase_diagram.consensus_fraction,
    }


# ─── 6. Cross-State Correlation Analysis ───

def compute_state_correlation_matrix(
    phase_diagram: PhaseDiagram,
) -> np.ndarray:
    """
    Compute the correlation matrix between octahedral states:
    how similarly do pairs of states respond to (strain, T) changes?
    
    High correlation → states are "siblings" (similar regime membership)
    Low correlation → states are "orthogonal" (different regime preferences)
    """
    
    resolution = phase_diagram.resolution
    n_points = resolution * resolution
    
    # Flatten each state's regime map
    state_vectors = np.zeros((8, n_points))
    
    for idx in range(8):
        state_vectors[idx] = phase_diagram.state_maps[idx].flatten()
    
    # Correlation matrix
    corr_matrix = np.corrcoef(state_vectors)
    
    return corr_matrix


def find_orthogonal_states(
    phase_diagram: PhaseDiagram,
    threshold: float = -0.3,
) -> List[Tuple[int, int]]:
    """
    Find pairs of octahedral states that are anti-correlated
    in their regime response — when one is in regime A,
    the other tends to be in regime B.
    
    These are the state pairs that give maximum geometric control
    over the physical regime.
    """
    
    corr_matrix = compute_state_correlation_matrix(phase_diagram)
    
    orthogonal_pairs = []
    
    for i in range(8):
        for j in range(i+1, 8):
            if corr_matrix[i, j] < threshold:
                orthogonal_pairs.append((i, j, corr_matrix[i, j]))
    
    orthogonal_pairs.sort(key=lambda x: x[2])  # most anti-correlated first
    
    return orthogonal_pairs


# ─── 7. Visualization Suite ───

def plot_phase_diagram_overview(
    phase_diagram: PhaseDiagram,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (20, 14),
):
    """
    Comprehensive visualization of the Silicon-GIES phase diagram.
    
    Shows:
    1. Consensus map (where all states agree)
    2. Disagreement map (entropy of regime distribution)
    3. Number of active regimes at each point
    4. Individual state maps for key states
    5. Regime transition network
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    from matplotlib.gridspec import GridSpec
    
    # Color maps for regimes
    REGIME_COLORS = {
        "semiconductor": "#2E86AB",
        "metallic": "#A23B72",
        "quantum": "#F18F01",
        "photonic": "#C73E1D",
        "defect_dominated": "#6B4D57",
        "mechanical": "#58A449",
    }
    
    # Build colormap from available regimes
    available_regimes = phase_diagram.regime_names
    colors = [REGIME_COLORS.get(r, "#888888") for r in available_regimes]
    
    # Add grey for "no consensus"
    consensus_colors = ["#888888"] + colors  # index 0 = grey (no consensus)
    
    fig = plt.figure(figsize=figsize)
    gs = GridSpec(3, 4, figure=fig, hspace=0.4, wspace=0.4)
    
    strains = phase_diagram.strains
    temps = phase_diagram.temps
    S, T_grid = np.meshgrid(strains, temps)
    
    # ── Panel 1: Consensus Map ──
    ax1 = fig.add_subplot(gs[0, :2])
    
    # Shift consensus map: -1 → 0 (grey), 0+ → regime index + 1
    consensus_shifted = phase_diagram.consensus_map + 1
    consensus_cmap = ListedColormap(consensus_colors)
    
    im1 = ax1.pcolormesh(S, T_grid, consensus_shifted, cmap=consensus_cmap,
                         shading='auto', vmin=0, vmax=len(colors))
    ax1.set_xlabel('Strain (%)')
    ax1.set_ylabel('Temperature (K)')
    ax1.set_title(f'Consensus Map (all 8 states agree)\n'
                  f'Consensus fraction: {phase_diagram.consensus_fraction:.2%}')
    
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='#888888', label='No consensus')]
    for r in available_regimes:
        legend_elements.append(Patch(facecolor=REGIME_COLORS.get(r, '#888'), label=r))
    ax1.legend(handles=legend_elements, fontsize=6, loc='upper right', ncol=2)
    
    # ── Panel 2: Disagreement Map ──
    ax2 = fig.add_subplot(gs[0, 2:])
    
    im2 = ax2.pcolormesh(S, T_grid, phase_diagram.disagreement_map,
                         cmap='hot', shading='auto', vmin=0, vmax=3)
    ax2.set_xlabel('Strain (%)')
    ax2.set_ylabel('Temperature (K)')
    ax2.set_title('Regime Disagreement Entropy\n(high = geometry selects physics)')
    plt.colorbar(im2, ax=ax2, label='Entropy (bits)')
    
    # Overlay ambiguity region contours
    if phase_diagram.ambiguity_regions:
        for region in phase_diagram.ambiguity_regions[:5]:
            s_min, s_max = region["strain_range"]
            t_min, t_max = region["temp_range"]
            rect = plt.Rectangle(
                (s_min, t_min), s_max - s_min, t_max - t_min,
                fill=False, edgecolor='cyan', linewidth=1.5, linestyle='--'
            )
            ax2.add_patch(rect)
    
    # ── Panel 3: Number of Active Regimes ──
    ax3 = fig.add_subplot(gs[1, 0])
    
    im3 = ax3.pcolormesh(S, T_grid, phase_diagram.n_active_regimes,
                         cmap='RdYlBu_r', shading='auto', vmin=1, vmax=6)
    ax3.set_xlabel('Strain (%)')
    ax3.set_ylabel('Temperature (K)')
    ax3.set_title('Number of Active Regimes')
    plt.colorbar(im3, ax=ax3, label='N regimes')
    
    # ── Panels 4-7: Selected Individual State Maps ──
    # Show the most informative states: isotropic (0), quantum-favored (3),
    # classical (7), and a mid-state (5)
    showcase_states = [0, 3, 5, 7]
    panel_positions = [(1, 1), (1, 2), (1, 3), (2, 0)]
    
    regime_cmap = ListedColormap(colors)
    
    for state_idx, (g_row, g_col) in zip(showcase_states, panel_positions):
        ax = fig.add_subplot(gs[g_row, g_col])
        
        state_map = phase_diagram.state_maps[state_idx]
        
        # Set -1 to NaN for white display
        state_map_display = state_map.astype(float)
        state_map_display[state_map < 0] = np.nan
        
        im = ax.pcolormesh(S, T_grid, state_map_display, cmap=regime_cmap,
                          shading='auto', vmin=0, vmax=len(colors)-1)
        ax.set_xlabel('Strain (%)')
        ax.set_ylabel('Temperature (K)')
        
        # Get eigenvalues for context
        from inverse_regime_design import CANONICAL_EIGENVALUES, compute_structural_metrics
        eig = CANONICAL_EIGENVALUES[state_idx]
        metrics = compute_structural_metrics(state_idx)
        ax.set_title(f'State {state_idx}: λ=({eig[0]:.2f},{eig[1]:.2f},{eig[2]:.2f})\n'
                    f'Natural: {metrics.natural_regime}')
    
    # ── Panel 8: Regime Area Distribution ──
    ax8 = fig.add_subplot(gs[2, 1])
    
    stability = compute_regime_stability_map(phase_diagram)
    
    regime_names = list(stability["total_areas"].keys())
    total_vals = [stability["total_areas"][r] * 100 for r in regime_names]
    consensus_vals = [stability["consensus_areas"][r] * 100 for r in regime_names]
    
    x = np.arange(len(regime_names))
    width = 0.35
    
    bars1 = ax8.bar(x - width/2, total_vals, width, label='Total area',
                    color='#2E86AB', alpha=0.7, edgecolor='black')
    bars2 = ax8.bar(x + width/2, consensus_vals, width, label='Consensus area',
                    color='#F18F01', alpha=0.7, edgecolor='black')
    
    ax8.set_xticks(x)
    ax8.set_xticklabels(regime_names, rotation=45, ha='right', fontsize=8)
    ax8.set_ylabel('Area (% of phase diagram)')
    ax8.set_title('Regime Stability Areas')
    ax8.legend(fontsize=7)
    
    # ── Panel 9: State Correlation Matrix ──
    ax9 = fig.add_subplot(gs[2, 2])
    
    corr_matrix = compute_state_correlation_matrix(phase_diagram)
    
    im9 = ax9.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    ax9.set_xticks(range(8))
    ax9.set_yticks(range(8))
    ax9.set_xticklabels([f'{i}' for i in range(8)], fontsize=8)
    ax9.set_yticklabels([f'{i}' for i in range(8)], fontsize=8)
    ax9.set_xlabel('State index')
    ax9.set_ylabel('State index')
    ax9.set_title('State-State Correlation\n(regime response similarity)')
    plt.colorbar(im9, ax=ax9, label='Correlation')
    
    # Highlight anti-correlated pairs
    orthogonal = find_orthogonal_states(phase_diagram)
    for i, j, corr in orthogonal[:3]:
        ax9.annotate('✗', (j, i), ha='center', va='center', fontsize=14, color='red')
    
    # ── Panel 10: Summary Text ──
    ax10 = fig.add_subplot(gs[2, 3])
    ax10.axis('off')
    
    # Find geometry-selects-physics zones
    gsp_zones = find_geometry_selects_physics_zones(phase_diagram)
    
    summary = f"""
    PHASE DIAGRAM SUMMARY
    ═════════════════════
    
    Resolution: {phase_diagram.resolution}×{phase_diagram.resolution}
    Regimes found: {len(available_regimes)}
    Consensus fraction: {phase_diagram.consensus_fraction:.1%}
    
    Ambiguity regions: {len(phase_diagram.ambiguity_regions)}
    
    Geometry-selects-physics
    zones: {len(gsp_zones)}
    
    Most anti-correlated
    state pairs:
    """
    
    for i, j, corr in orthogonal[:4]:
        summary += f"  States {i}↔{j}: ρ={corr:.3f}\n"
    
    if gsp_zones:
        summary += f"\nTop GSP zone:\n"
        best_zone = max(gsp_zones, key=lambda z: z.disagreement_entropy)
        summary += f"  Strain={best_zone.strain_center:+.1f}%\n"
        summary += f"  Temp={best_zone.temp_center:.0f}K\n"
        summary += f"  Regimes: {best_zone.n_regimes_present}\n"
        summary += f"  Entropy: {best_zone.disagreement_entropy:.2f} bits\n"
    
    ax10.text(0.05, 0.95, summary, transform=ax10.transAxes,
             fontsize=8, fontfamily='monospace', verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    
    fig.suptitle('Silicon-GIES Phase Diagram: Geometry Selects Physics',
                fontsize=16, fontweight='bold', y=1.01)
    
    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    
    return fig


def plot_geometry_selects_physics_detail(
    phase_diagram: PhaseDiagram,
    zone_index: int = 0,
    save_path: Optional[str] = None,
):
    """
    Zoom in on a specific geometry-selects-physics zone to show
    exactly which octahedral states map to which regimes.
    """
    import matplotlib.pyplot as plt
    
    gsp_zones = find_geometry_selects_physics_zones(phase_diagram)
    
    if not gsp_zones:
        print("No geometry-selects-physics zones found.")
        return None
    
    zone = gsp_zones[min(zone_index, len(gsp_zones)-1)]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # ── Panel 1: State → Regime mapping ──
    REGIME_COLORS = {
        "semiconductor": "#2E86AB", "metallic": "#A23B72",
        "quantum": "#F18F01", "photonic": "#C73E1D",
        "defect_dominated": "#6B4D57", "mechanical": "#58A449",
    }
    
    states = sorted(zone.state_to_regime.keys())
    regimes = [zone.state_to_regime[s] for s in states]
    colors = [REGIME_COLORS.get(r, '#888') for r in regimes]
    
    bars = ax1.bar(states, [1]*8, color=colors, edgecolor='black', linewidth=1)
    
    # Add regime labels
    for s, r in zone.state_to_regime.items():
        ax1.text(s, 0.5, r, ha='center', va='center', rotation=90,
                fontsize=8, fontweight='bold', color='white')
    
    ax1.set_xticks(states)
    ax1.set_xlabel('Octahedral State Index')
    ax1.set_ylabel('Active')
    ax1.set_title(f'State → Regime Mapping at\n'
                  f'Strain={zone.strain_center:+.2f}%, T={zone.temp_center:.0f}K\n'
                  f'{zone.n_regimes_present} distinct regimes accessible')
    ax1.set_ylim(0, 1.5)
    
    # ── Panel 2: Cube visualization ──
    ax2 = fig.add_subplot(122, projection='3d')
    
    # Plot octahedral positions colored by regime
    from inverse_regime_design import OCTAHEDRAL_POSITIONS
    
    for state_idx, pos in OCTAHEDRAL_POSITIONS.items():
        regime = zone.state_to_regime.get(state_idx, "unknown")
        color = REGIME_COLORS.get(regime, '#888')
        
        ax2.scatter(*pos, c=color, s=200, edgecolors='black', linewidth=1.5, alpha=0.9)
        ax2.text(pos[0], pos[1], pos[2], f'{state_idx}', fontsize=8, ha='center')
    
    # Draw cube edges
    cube_edges = [
        (0,1), (0,2), (0,4), (1,3), (1,5), (2,3), (2,6),
        (3,7), (4,5), (4,6), (5,7), (6,7)
    ]
    
    for i, j in cube_edges:
        p1 = OCTAHEDRAL_POSITIONS[i]
        p2 = OCTAHEDRAL_POSITIONS[j]
        ax2.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                'k-', alpha=0.2, linewidth=0.5)
    
    ax2.set_xlabel('x')
    ax2.set_ylabel('y')
    ax2.set_zlabel('z')
    ax2.set_title('Octahedral Vertex Mapping\nColor = Physical Regime')
    
    # Legend
    unique_regimes = sorted(set(zone.state_to_regime.values()))
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=REGIME_COLORS.get(r, '#888'), label=r)
        for r in unique_regimes
    ]
    ax2.legend(handles=legend_elements, fontsize=7, loc='upper right')
    
    fig.suptitle('Geometry Selects Physics: Active Zone Detail',
                fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    
    return fig


# ─── 8. Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("SILICON-GIES PHASE DIAGRAM")
    print("Where Geometry Selects Physics")
    print("=" * 70)
    
    # Compute phase diagram (reduced resolution for quick demo)
    print("\nComputing phase diagram (this may take a moment)...")
    print("  Grid: 40×40 × 8 states = 12,800 evaluations")
    
    phase_diagram = compute_silicon_gies_phase_diagram(
        strain_range=(-2.0, 2.0),
        temp_range=(1.0, 400.0),
        resolution=40,
        B_field=np.array([0, 0, 0.5]),
        verbose=True,
    )
    
    print(f"\n✓ Phase diagram computed")
    print(f"  Regimes found: {phase_diagram.regime_names}")
    print(f"  Consensus fraction: {phase_diagram.consensus_fraction:.2%}")
    print(f"  Ambiguity regions: {len(phase_diagram.ambiguity_regions)}")
    
    # ── Analysis ──
    
    # Regime stability
    stability = compute_regime_stability_map(phase_diagram)
    print(f"\nRegime Stability Areas:")
    for regime in phase_diagram.regime_names:
        total = stability["total_areas"].get(regime, 0) * 100
        consensus = stability["consensus_areas"].get(regime, 0) * 100
        print(f"  {regime:20s}: total={total:5.1f}%, consensus={consensus:5.1f}%")
    
    # State correlations
    orthogonal = find_orthogonal_states(phase_diagram)
    print(f"\nMost Anti-Correlated State Pairs:")
    for i, j, corr in orthogonal[:4]:
        print(f"  States {i} ↔ {j}: ρ = {corr:.3f}")
    
    # Geometry-selects-physics zones
    gsp_zones = find_geometry_selects_physics_zones(phase_diagram)
    print(f"\nGeometry-Selects-Physics Zones: {len(gsp_zones)} found")
    
    if gsp_zones:
        # Show top zone
        best = max(gsp_zones, key=lambda z: z.disagreement_entropy)
        print(f"\n  Top Zone:")
        print(f"    Strain: {best.strain_center:+.2f}%")
        print(f"    Temperature: {best.temp_center:.0f} K")
        print(f"    Regimes present: {best.n_regimes_present}")
        print(f"    Disagreement entropy: {best.disagreement_entropy:.2f} bits")
        print(f"    Regimes: {best.regimes_present}")
        print(f"\n    State → Regime mapping:")
        for idx in sorted(best.state_to_regime.keys()):
            print(f"      State {idx}: {best.state_to_regime[idx]}")
    
    # Transition network
    network = build_regime_transition_network(phase_diagram)
    print(f"\nRegime Transition Network:")
    print(f"  Total transitions: {network['total_transitions']}")
    print(f"  Top transitions:")
    sorted_transitions = sorted(network["transitions"].items(), key=lambda x: -x[1])
    for (r1, r2), count in sorted_transitions[:5]:
        print(f"    {r1} ↔ {r2}: {count} ({count/network['total_transitions']*100:.1f}%)")
    
    print("\n" + "=" * 70)
    print("KEY DISCOVERY:")
    print("=" * 70)
    print(f"""
    At {len(gsp_zones)} points in the (strain, temperature) phase diagram,
    the choice of octahedral state determines which physical regime is active.
    
    This means geometric encoding is not passive — it is a control parameter
    on equal footing with doping, strain, and temperature.
    
    In these zones, you can change the computation type (classical → quantum,
    electronic → photonic) simply by choosing a different octahedral state,
    without changing any physical parameters.
    """)
