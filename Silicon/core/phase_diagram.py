# phase_diagram.py

def compute_phase_diagram(
    strain_range: Tuple[float, float],
    temp_range: Tuple[float, float],
    resolution: int = 50,
) -> np.ndarray:
    """
    Compute the (strain, temperature) phase diagram for all 8 states.
    Returns a (8, resolution, resolution) array of regime classifications.
    Regions where states disagree = coexistence/ambiguity zones.
    """
    strains = np.linspace(*strain_range, resolution)
    temps = np.linspace(*temp_range, resolution)
    
    diagram = np.zeros((8, resolution, resolution), dtype=int)
    regime_map = {}  # string → int encoding
    
    for i, eps in enumerate(strains):
        for j, T in enumerate(temps):
            for idx in range(8):
                result = run_integrated_pipeline(
                    state_index=idx, strain_pct=eps, temperature=T
                )
                regime = result.silicon_state.dominant_regime()
                if regime not in regime_map:
                    regime_map[regime] = len(regime_map)
                diagram[idx, j, i] = regime_map[regime]
    
    # Disagreement metric: entropy of regime assignments across states
    from scipy.stats import entropy
    disagreement = np.zeros((resolution, resolution))
    for i in range(resolution):
        for j in range(resolution):
            counts = np.bincount(diagram[:, j, i], minlength=len(regime_map))
            disagreement[j, i] = entropy(counts + 1e-10)
    
    return diagram, disagreement, regime_map
