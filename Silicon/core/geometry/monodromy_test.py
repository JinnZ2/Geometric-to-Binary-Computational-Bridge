# monodromy_test.py — detect fiber holonomy around phase boundaries

from __future__ import annotations

from typing import List

import numpy as np

from Silicon.core.analysis.computational_phase_transition import SiliconState


def _state_distance(a: SiliconState, b: SiliconState) -> float:
    """Heuristic distance in silicon state space used for parallel transport."""
    coupling_keys = sorted(set(a.k) | set(b.k))
    coupling_distance = sum((a.k.get(key, 0.0) - b.k.get(key, 0.0)) ** 2 for key in coupling_keys)
    return float(
        ((np.log10(max(a.n, 1.0)) - np.log10(max(b.n, 1.0))) ** 2)
        + (a.d - b.d) ** 2
        + (a.l - b.l) ** 2
        + coupling_distance
    )


def minimize_transport_cost(current_index: int, target_state: SiliconState) -> int:
    """Choose the octahedral label that best matches the target state."""
    candidate_states = {
        candidate: SiliconState(
            n=max(target_state.n * (1.0 + 0.02 * (candidate - current_index)), 1.0),
            d=float(np.clip(target_state.d + 0.01 * abs(candidate - current_index), 0.0, 1.0)),
            l=max(target_state.l + 0.05 * ((candidate % 3) - 1), 0.1),
            k=dict(target_state.k),
        )
        for candidate in range(8)
    }
    return min(candidate_states, key=lambda candidate: _state_distance(candidate_states[candidate], target_state))


def compute_monodromy(
    start_state_index: int,
    loop_in_S_space: List[SiliconState],
) -> int:
    """
    Trace a closed loop in silicon phase space.
    Returns the final octahedral state index after parallel transport.
    If != start_state_index, the fiber has nontrivial holonomy.
    """
    current_index = start_state_index

    for state in loop_in_S_space:
        current_index = minimize_transport_cost(current_index, state)

    return current_index
