# monodromy_test.py — detect fiber holonomy around phase boundaries

def compute_monodromy(
    start_state_index: int,
    loop_in_S_space: List[SiliconState],  # closed loop
) -> int:
    """
    Trace a closed loop in silicon phase space.
    Returns the final octahedral state index after parallel transport.
    If != start_state_index, the fiber has nontrivial holonomy.
    """
    current_index = start_state_index
    
    for S in loop_in_S_space:
        # Parallel transport: find octahedral state that minimizes
        # "distance" in the combined geometric+silicon space
        current_index = minimize_transport_cost(current_index, S)
    
    return current_index
