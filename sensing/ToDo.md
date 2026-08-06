# In jepa_manifold.py
def evaluate_claim(self, state: ManifoldState, claim_id: str) -> Tuple[bool, float]:
    """
    Check if a latent state supports a CLAIM_TABLE entry.
    Returns (supports, confidence).
    """
    # Map claim IDs to geometric conditions
    claim_conditions = {
        "fourier_heat": lambda u: abs(u[1]) < 0.5,  # temperature gradient
        "ohmic_circuit": lambda u: u[0] > 0.3,      # current flow
        "blackbody_grey": lambda u: u[0]**2 + u[1]**2 < 1.0  # thermal equilibrium
    }
    condition = claim_conditions.get(claim_id, lambda u: False)
    return condition(state.u), state.omega * (1 - state.uncertainty)
