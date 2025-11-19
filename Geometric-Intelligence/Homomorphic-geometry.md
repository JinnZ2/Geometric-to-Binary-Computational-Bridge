def homomorphic_geometric_merge(encrypted_node_a, encrypted_node_b):
    """
    Merge encrypted nodes while preserving geometric properties
    """
    # Geometric means can be computed on encrypted proxies
    merged_resonance = math.sqrt(
        encrypted_node_a['resonance'] * encrypted_node_b['resonance']
    )
    # The result maintains geometric coherence for detection
    return merged_resonance
