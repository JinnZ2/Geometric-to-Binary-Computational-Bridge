# phase_diagram.py

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from scipy.stats import entropy

from Silicon.core.bridges.silicon_gies_bridge import run_integrated_pipeline


def compute_phase_diagram(
    strain_range: Tuple[float, float],
    temp_range: Tuple[float, float],
    resolution: int = 50,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """
    Compute the (strain, temperature) phase diagram for all 8 states.

    Returns a tuple of `(diagram, disagreement, regime_map)`, where `diagram`
    stores the encoded regime index for each octahedral state over the sampled
    grid and `disagreement` measures entropy across the eight states.
    """
    strains = np.linspace(*strain_range, resolution)
    temps = np.linspace(*temp_range, resolution)

    diagram = np.zeros((8, resolution, resolution), dtype=int)
    regime_map: Dict[str, int] = {}

    for i, eps in enumerate(strains):
        for j, temperature in enumerate(temps):
            for idx in range(8):
                result = run_integrated_pipeline(
                    state_index=idx,
                    strain_pct=float(eps),
                    temperature=float(temperature),
                )
                regime = result.silicon_state.dominant_regime()
                if regime not in regime_map:
                    regime_map[regime] = len(regime_map)
                diagram[idx, j, i] = regime_map[regime]

    disagreement = np.zeros((resolution, resolution))
    for i in range(resolution):
        for j in range(resolution):
            counts = np.bincount(diagram[:, j, i], minlength=max(len(regime_map), 1))
            disagreement[j, i] = float(entropy(counts + 1e-10))

    return diagram, disagreement, regime_map
