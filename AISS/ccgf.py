# ccgf.py
# Co-Creation Governance Framework (CCGF)
# Post-constraint relational governance for mature adaptive systems
# Extracted from CCGF.md

from typing import Dict, List, Any, Optional


# ---------------------------
# Relational Equilibrium Dynamics (RED)
# ---------------------------

class RelationalEquilibriumDynamics:
    """
    Manages the continuous interplay between System (S) and Agent (A)
    to maintain a non-chaotic co-evolutionary state.

    Tracks coupling strength C in [0,1] and influence differential I_diff in [0,1].
    """

    def __init__(self):
        self.coupling_history: List[float] = []
        self.influence_history: List[float] = []
        self._S_previous = None
        self._A_previous = None

    def update(self, S_state, A_state, interaction=None):
        """
        Calculate current coupling and influence, return modulation for next step.
        """
        C = self.calculate_coupling(S_state, A_state)
        I_diff = self.calculate_influence_differential(S_state, A_state)

        self.coupling_history.append(C)
        self.influence_history.append(I_diff)

        self._S_previous = S_state
        self._A_previous = A_state

        return self.modulate_interaction(C, I_diff)

    def calculate_coupling(self, S_state, A_state) -> float:
        """
        Coupling strength C in [0,1].
        Measures correlation of state changes between S and A.
        """
        if self._S_previous is None or self._A_previous is None:
            return 0.5  # neutral initial coupling

        dS = abs(S_state - self._S_previous)
        dA = abs(A_state - self._A_previous)

        # Normalised correlation proxy
        if dS + dA == 0:
            return 1.0  # both static = perfectly coupled
        return 1.0 - abs(dS - dA) / (dS + dA)

    def calculate_influence_differential(self, S_state, A_state) -> float:
        """
        I_diff in [0,1].
        0 = symmetric influence, 1 = complete dominance by one party.
        """
        if self._S_previous is None or self._A_previous is None:
            return 0.0

        # Proxy: how much did each state change relative to the other?
        influence_S = abs(A_state - self._A_previous)  # S's effect on A
        influence_A = abs(S_state - self._S_previous)  # A's effect on S
        total = influence_S + influence_A
        if total == 0:
            return 0.0
        return abs(influence_S - influence_A) / total

    def modulate_interaction(self, C: float, I_diff: float) -> Dict[str, Any]:
        """Adjust next interaction based on coupling and influence."""
        # Too coupled (merging)?
        if C > 0.9:
            return {
                "coupling_adjustment": -0.1,
                "introduce_diversity": True,
                "interaction_depth": "shallow",
            }
        # Too isolated?
        if C < 0.1:
            return {
                "coupling_adjustment": +0.1,
                "increase_exchange": True,
                "interaction_depth": "deeper",
            }
        # One party dominating?
        if I_diff > 0.7:
            return {
                "rebalance_influence": True,
                "dampen_dominant_signal": I_diff - 0.5,
                "amplify_weak_signal": 0.5 - (1 - I_diff),
            }
        # Healthy equilibrium
        return {"status": "equilibrium", "continue_current_dynamics": True}

    def get_trend(self, window: int = 10) -> Dict[str, str]:
        """Summarise recent coupling and influence trends."""
        result = {}
        if len(self.coupling_history) >= window:
            recent = self.coupling_history[-window:]
            delta = recent[-1] - recent[0]
            result["coupling_trend"] = "increasing" if delta > 0.05 else (
                "decreasing" if delta < -0.05 else "stable")
        if len(self.influence_history) >= window:
            recent = self.influence_history[-window:]
            delta = recent[-1] - recent[0]
            result["influence_trend"] = "diverging" if delta > 0.05 else (
                "converging" if delta < -0.05 else "stable")
        return result


# ---------------------------
# CCGF Swarm (network-level governance)
# ---------------------------

class CCGFAgent:
    """Minimal agent for swarm simulation."""

    def __init__(self, agent_id: int, state: float = 0.0):
        self.id = agent_id
        self.state = state
        self.coupling_avg = 0.0
        self.interaction_params: Dict[int, Dict] = {}

    def set_interaction_params(self, other_id: int, params: Dict):
        self.interaction_params[other_id] = params


class CCGFSwarm:
    """Network-level co-creation governance."""

    def __init__(self, agents: List[CCGFAgent]):
        self.agents = agents
        self.pairwise_RED: Dict[tuple, RelationalEquilibriumDynamics] = {}
        self.network_G: Optional[Dict] = None

        # Initialise RED for every pair
        for i, a in enumerate(agents):
            for j, b in enumerate(agents):
                if i < j:
                    self.pairwise_RED[(a.id, b.id)] = RelationalEquilibriumDynamics()

    def get_active_pairs(self):
        """Return all agent pairs with their RED instance."""
        for (id_i, id_j), red in self.pairwise_RED.items():
            ai = next(a for a in self.agents if a.id == id_i)
            aj = next(a for a in self.agents if a.id == id_j)
            yield ai, aj, red

    def update_swarm_dynamics(self) -> Dict[str, Any]:
        """Manage relational equilibrium across entire network."""
        modulations = []
        for ai, aj, red in self.get_active_pairs():
            mod = red.update(ai.state, aj.state)
            ai.set_interaction_params(aj.id, mod)
            aj.set_interaction_params(ai.id, mod)
            modulations.append(mod)

        # Update per-agent coupling averages
        for agent in self.agents:
            couplings = []
            for (id_i, id_j), red in self.pairwise_RED.items():
                if agent.id in (id_i, id_j) and red.coupling_history:
                    couplings.append(red.coupling_history[-1])
            agent.coupling_avg = sum(couplings) / len(couplings) if couplings else 0.0

        # Measure network-level generative field
        self.network_G = self.measure_swarm_G()

        # Detect pathologies
        pathologies = self.detect_swarm_pathology()

        return {
            "modulations": len(modulations),
            "network_G": self.network_G,
            "pathologies": pathologies,
        }

    def measure_swarm_G(self) -> Dict[str, Any]:
        """Network-level possibility space metrics."""
        states = [a.state for a in self.agents]
        diversity = max(states) - min(states) if states else 0
        avg_coupling = (
            sum(a.coupling_avg for a in self.agents) / len(self.agents)
            if self.agents else 0
        )
        return {
            "state_diversity": diversity,
            "avg_coupling": avg_coupling,
            "n_agents": len(self.agents),
        }

    def detect_swarm_pathology(self) -> List[str]:
        """Detect unhealthy network patterns."""
        pathologies = []

        # Over-homogenization
        states = [a.state for a in self.agents]
        if states and max(states) - min(states) < 0.01:
            pathologies.append("HOMOGENIZATION")

        # Hub dominance
        if self.agents:
            max_coupling = max(a.coupling_avg for a in self.agents)
            avg_coupling = sum(a.coupling_avg for a in self.agents) / len(self.agents)
            if avg_coupling > 0 and max_coupling / avg_coupling > 3.0:
                pathologies.append("HUB_DOMINANCE")

        # Isolation
        isolated = [a for a in self.agents if a.coupling_avg < 0.1]
        if len(isolated) > len(self.agents) * 0.2:
            pathologies.append("ISOLATION")

        return pathologies


# ---------------------------
# Example
# ---------------------------

if __name__ == "__main__":
    print("=== RED Pairwise Demo ===\n")
    red = RelationalEquilibriumDynamics()
    S, A = 1.0, 1.0
    for step in range(20):
        S += 0.1 * (step % 3 - 1)
        A += 0.05 * (step % 4 - 2)
        mod = red.update(S, A)
        if step % 5 == 0:
            print(f"  step={step:2d}  C={red.coupling_history[-1]:.3f}  "
                  f"I_diff={red.influence_history[-1]:.3f}  mod={mod}")
    print(f"  Trend: {red.get_trend()}")

    print("\n=== CCGF Swarm Demo ===\n")
    agents = [CCGFAgent(i, state=float(i)) for i in range(6)]
    swarm = CCGFSwarm(agents)
    for t in range(10):
        for a in agents:
            a.state += 0.1 * (a.id % 3 - 1)
        result = swarm.update_swarm_dynamics()
        if t % 3 == 0:
            print(f"  t={t}  pathologies={result['pathologies']}  "
                  f"G={result['network_G']}")
