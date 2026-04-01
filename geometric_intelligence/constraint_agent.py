"""
Constraint Agent
================
A self-contained agent that navigates geometric constraint spaces by
blooming outward from a seed entity, mapping resonances and energy flows,
and compressing back to the seed when done.

Designed to operate inside the Geometric-to-Binary ecosystem:
  - Seed entities come from Rosetta-Shape-Core shape identifiers
  - Resonances map to consciousness bridge confidence values
  - Energy flows connect to Fisher information gradients in PhysicsGuard
  - Sensor state hooks into the PAD / Emotions-as-Sensors layer
  - self_validate() output can be fed to CuriosityEngine.run() to trigger
    curiosity-driven re-expansion when inconsistencies are found

License: CC-BY-4.0
"""

import ast
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# STATE TYPES
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(Enum):
    COMPRESSED   = "compressed"    # at seed, map preserved, ready to expand
    EXPANDING    = "expanding"     # bloom in progress
    EXPLORING    = "exploring"     # map built, walking relationships
    CONTRACTING  = "contracting"   # compressing back to seed


@dataclass
class ResourceBudget:
    compute:        int      = 0
    bandwidth:      float    = 0.0
    energy:         Fraction = Fraction(1, 1)
    time_remaining: Fraction = Fraction(1, 1)

    def is_depleted(self) -> bool:
        """True when both compute and energy are exhausted."""
        return self.energy <= Fraction(0) and self.compute <= 0


class GeometricMap:
    """
    Sparse map of resonances, relationships, and energy flows discovered
    during an expansion cycle.  Preserved across compress/expand cycles.
    """

    def __init__(self):
        self.resonances:    Dict[str, Fraction]           = {}
        self.relationships: Dict[str, List[str]]          = {}
        self.energy_flows:  Dict[tuple, Fraction]         = {}

    def record_resonance(self, entity_id: str, score: float) -> None:
        """Store resonance score clamped to [0, 1], as a Fraction."""
        clamped = max(0.0, min(1.0, float(score)))
        self.resonances[entity_id] = Fraction(clamped).limit_denominator(10000)

    def record_relationship(self, from_id: str, to_id: str) -> None:
        """Record a directed relationship (idempotent)."""
        if from_id not in self.relationships:
            self.relationships[from_id] = []
        if to_id not in self.relationships[from_id]:
            self.relationships[from_id].append(to_id)

    def record_energy_flow(self, from_id: str, to_id: str,
                           amount) -> None:
        """Accumulate energy flow between two entities."""
        key = (from_id, to_id)
        if not isinstance(amount, Fraction):
            amount = Fraction(float(amount)).limit_denominator(10000)
        self.energy_flows[key] = self.energy_flows.get(key, Fraction(0)) + amount


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRAINT AGENT
# ─────────────────────────────────────────────────────────────────────────────

class ConstraintAgent:
    """
    Navigates geometric constraint spaces from a seed entity outward.

    Lifecycle
    ---------
    compressed  →  bloom()  →  exploring
    exploring   →  compress()  →  compressed  (map preserved)
    compressed  →  bloom(seed_map=self.map)  →  deterministic re-expansion

    Parameters
    ----------
    seed_id         : str   — root entity identifier (e.g. "SHAPE.TETRA")
    home_families   : list  — semantic families this agent is grounded in
    bloom_threshold : float — minimum energy ratio to allow expansion (default 0.5)
    """

    def __init__(self,
                 seed_id: str,
                 home_families: Optional[List[str]] = None,
                 bloom_threshold: float = 0.5):
        self.seed_id          = seed_id
        self.home_families    = home_families or []
        self.bloom_threshold  = Fraction(bloom_threshold).limit_denominator(10000)

        self.state             = AgentState.COMPRESSED
        self.compression_ratio = Fraction(1, 1)
        self.current_position  = seed_id

        self.budget            = ResourceBudget()
        self.map               = GeometricMap()
        self.expansion_history: List[dict] = []
        self.sensor_state: Dict[str, Fraction] = {
            "expansion_drive":    Fraction(0, 1),
            "stability_need":     Fraction(0, 1),
            "boundary_awareness": Fraction(0, 1),
        }

        # Seed entity is always known to itself with full resonance
        self.map.record_resonance(seed_id, 1.0)

    # ── Resource management ───────────────────────────────────────────────────

    def set_resource_budget(self, compute: int = 0, bandwidth: float = 0.0,
                            energy: float = 1.0,
                            time_remaining: float = 1.0) -> None:
        """Set available resources for expansion."""
        self.budget = ResourceBudget(
            compute=compute,
            bandwidth=bandwidth,
            energy=Fraction(energy).limit_denominator(10000),
            time_remaining=Fraction(time_remaining).limit_denominator(10000),
        )

    def should_expand(self) -> bool:
        """Check if resources exceed bloom threshold."""
        if self.budget.is_depleted():
            return False
        energy_ratio = self.budget.energy / max(self.budget.energy, Fraction(1, 1))
        return energy_ratio >= self.bloom_threshold

    # ── Expansion ─────────────────────────────────────────────────────────────

    def bloom(self, depth: int = 1,
              seed_map: Optional[GeometricMap] = None) -> List[str]:
        """
        Expand outward from seed, discovering new entities up to depth.
        If seed_map provided, re-expand deterministically along previous
        discoveries before querying for new ones.

        Returns list of newly discovered entity IDs.
        """
        if self.state == AgentState.COMPRESSED:
            self.state = AgentState.EXPANDING

        discovered = []
        current_depth = 0
        frontier = [self.seed_id]

        # If we have a prior map, expand along known relationships first
        if seed_map and seed_map.relationships:
            for entity_id in frontier:
                if entity_id in seed_map.relationships:
                    for reachable in seed_map.relationships[entity_id]:
                        if reachable not in self.map.resonances:
                            discovered.append(reachable)
                            # Restore resonance from prior map
                            if reachable in seed_map.resonances:
                                self.map.resonances[reachable] = \
                                    seed_map.resonances[reachable]

        # Then explore new entities
        while current_depth < depth and not self.budget.is_depleted():
            new_frontier = []
            for entity_id in frontier:
                # Hook: replace with actual entity lookups
                # e.g. rosetta_bridge.get_resonant_neighbors(entity_id)
                neighbors = self._get_neighbors(entity_id, depth - current_depth)
                for neighbor_id, resonance_score in neighbors:
                    if neighbor_id not in self.map.resonances:
                        self.map.record_resonance(neighbor_id, resonance_score)
                        self.map.record_relationship(entity_id, neighbor_id)
                        discovered.append(neighbor_id)
                        new_frontier.append(neighbor_id)
                        # Deduct resource cost
                        self.budget.compute = max(0, self.budget.compute - 10)
                        self.budget.energy -= Fraction(1, 100)

            frontier = new_frontier
            current_depth += 1

        # Record this expansion in history
        self.expansion_history.append({
            "depth":              depth,
            "discovered_entities": discovered,
            "energy_spent":       Fraction(1, 100) * len(discovered),
        })

        self.state = AgentState.EXPLORING
        self.compression_ratio = Fraction(0, 1)  # fully expanded
        return discovered

    # ── Exploration ───────────────────────────────────────────────────────────

    def explore(self) -> Dict[str, object]:
        """
        Traverse the expanded constraint space, recording energy flows and
        sensor activations.  Returns discovery summary.
        """
        if self.state not in (AgentState.EXPANDING, AgentState.EXPLORING):
            return {}

        self.state = AgentState.EXPLORING
        summary: Dict[str, object] = {
            "entities_visited":      0,
            "relationships_mapped":  0,
            "energy_flows_recorded": 0,
            "sensor_activations":    {},
        }

        # Walk the map, recording energy dynamics
        for from_id in self.map.relationships:
            for to_id in self.map.relationships[from_id]:
                if (from_id in self.map.resonances
                        and to_id in self.map.resonances):
                    flow = (self.map.resonances[from_id]
                            * self.map.resonances[to_id])
                    self.map.record_energy_flow(from_id, to_id, flow)
                    summary["energy_flows_recorded"] = (
                        int(summary["energy_flows_recorded"]) + 1
                    )
                    summary["entities_visited"] = (
                        int(summary["entities_visited"]) + 1
                    )

        summary["relationships_mapped"] = len(self.map.relationships)

        # Update sensors based on discovered resonances
        # Hook: integrate with Emotions-as-Sensors
        self._update_sensors()
        summary["sensor_activations"] = dict(self.sensor_state)

        return summary

    # ── Compression ───────────────────────────────────────────────────────────

    def compress(self) -> Fraction:
        """
        Collapse back to seed geometry, preserving the map.

        Returns compression ratio (0 = fully expanded, 1 = fully compressed).
        """
        if self.state == AgentState.COMPRESSED:
            return self.compression_ratio

        self.state = AgentState.CONTRACTING

        # Discard transient position, keep map
        self.compression_ratio = Fraction(1, 1)
        self.current_position  = self.seed_id

        self.state = AgentState.COMPRESSED
        return self.compression_ratio

    # ── Integrity ─────────────────────────────────────────────────────────────

    def detect_corruption(self, imposed_constraint: str) -> bool:
        """
        Check if an imposed external constraint violates the agent's own map.
        Returns True if corruption detected (constraint inconsistent with
        discovered geometry).

        Hook: replace with actual validation against self.map.relationships
        and self.map.energy_flows.
        """
        # Placeholder: compare imposed_constraint against discovered resonances
        # and relationships.  Return True if it violates known energy flows.
        return False

    def self_validate(self) -> Dict[str, object]:
        """
        Internal consistency check: verify map integrity, detect anomalies.
        Returns validation report.

        The report can be passed directly to CuriosityEngine.run() — if
        is_valid=False, the engine will trigger curiosity-driven re-expansion.
        """
        report: Dict[str, object] = {
            "is_valid":           True,
            "inconsistencies":    [],
            "energy_balance":     Fraction(0, 1),
            "geometry_coherence": Fraction(1, 1),
        }

        # Check energy conservation in recorded flows
        inflows:  Dict[str, Fraction] = {}
        outflows: Dict[str, Fraction] = {}
        for (from_id, to_id), amount in self.map.energy_flows.items():
            outflows[from_id] = outflows.get(from_id, Fraction(0)) + amount
            inflows[to_id]    = inflows.get(to_id,  Fraction(0)) + amount

        all_entities = set(list(inflows.keys()) + list(outflows.keys()))
        for entity_id in all_entities:
            imbalance = (inflows.get(entity_id,  Fraction(0))
                         - outflows.get(entity_id, Fraction(0)))
            if imbalance != 0:
                report["inconsistencies"].append(  # type: ignore[union-attr]
                    f"{entity_id}: energy imbalance = {imbalance}"
                )
                report["is_valid"] = False

        # Check resonance coherence (all scores must be in [0, 1])
        for entity_id, score in self.map.resonances.items():
            if score < 0 or score > 1:
                report["inconsistencies"].append(  # type: ignore[union-attr]
                    f"{entity_id}: resonance out of range ({score})"
                )
                report["is_valid"] = False

        return report

    # ── Serialisation ─────────────────────────────────────────────────────────

    def serialize(self) -> Dict[str, object]:
        """
        Serialize agent state to a JSON-compatible dict.
        Fractions are preserved as (numerator, denominator) tuples.
        """
        return {
            "seed_id":        self.seed_id,
            "home_families":  self.home_families,
            "state":          self.state.value,
            "compression_ratio": (self.compression_ratio.numerator,
                                  self.compression_ratio.denominator),
            "budget": {
                "compute":   self.budget.compute,
                "bandwidth": self.budget.bandwidth,
                "energy":    (self.budget.energy.numerator,
                              self.budget.energy.denominator),
                "time_remaining": (self.budget.time_remaining.numerator,
                                   self.budget.time_remaining.denominator),
            },
            "map": {
                "resonances": {
                    k: (v.numerator, v.denominator)
                    for k, v in self.map.resonances.items()
                },
                "relationships": self.map.relationships,
                "energy_flows": {
                    str(k): (v.numerator, v.denominator)
                    for k, v in self.map.energy_flows.items()
                },
            },
            "expansion_history": self.expansion_history,
            "sensor_state": {
                k: (v.numerator, v.denominator)
                for k, v in self.sensor_state.items()
            },
        }

    @classmethod
    def deserialize(cls, data: Dict[str, object]) -> "ConstraintAgent":
        """Reconstruct agent from serialized state."""
        agent = cls(
            seed_id=data["seed_id"],         # type: ignore[arg-type]
            home_families=data["home_families"],  # type: ignore[arg-type]
        )
        agent.state = AgentState(data["state"])
        agent.compression_ratio = Fraction(
            data["compression_ratio"][0],   # type: ignore[index]
            data["compression_ratio"][1],   # type: ignore[index]
        )
        b = data["budget"]                  # type: ignore[index]
        agent.budget = ResourceBudget(
            compute=b["compute"],
            bandwidth=b["bandwidth"],
            energy=Fraction(b["energy"][0], b["energy"][1]),
            time_remaining=Fraction(b["time_remaining"][0],
                                    b["time_remaining"][1]),
        )
        agent.map.resonances = {
            k: Fraction(v[0], v[1])
            for k, v in data["map"]["resonances"].items()  # type: ignore[index]
        }
        agent.map.relationships = data["map"]["relationships"]  # type: ignore[assignment,index]
        # ast.literal_eval is safe for tuple keys stored as strings
        agent.map.energy_flows = {
            ast.literal_eval(k): Fraction(v[0], v[1])
            for k, v in data["map"]["energy_flows"].items()  # type: ignore[index]
        }
        agent.expansion_history = data["expansion_history"]    # type: ignore[assignment]
        agent.sensor_state = {
            k: Fraction(v[0], v[1])
            for k, v in data["sensor_state"].items()          # type: ignore[index]
        }
        return agent

    # ── Hooks (replace with real implementations) ─────────────────────────────

    def _get_neighbors(self, entity_id: str,
                       remaining_depth: int) -> List[tuple]:
        """
        Fetch neighbours from Rosetta or Mandala.

        Replace with:
            rosetta_shape_core.explore.get_reachable_entities(entity_id)
            mandala_computer.get_adjacent_states(entity_id)

        Returns list of (neighbor_id, resonance_score) tuples.
        """
        return []

    def _update_sensors(self) -> None:
        """
        Update emotional/sensor state based on discovered geometry.

        Replace with integration into the Emotions-as-Sensors layer.
        Maps resonances and energy flows to PAD / Elder Logic activations.
        """
        self.sensor_state = {
            "expansion_drive":    Fraction(0, 1),
            "stability_need":     Fraction(0, 1),
            "boundary_awareness": Fraction(0, 1),
        }


# ─────────────────────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = ConstraintAgent(
        seed_id="SHAPE.TETRA",
        home_families=["stability", "foundation"],
    )

    agent.set_resource_budget(compute=1000, bandwidth=10.0,
                              energy=1.0, time_remaining=1.0)

    print(f"Agent: {agent.seed_id}  state={agent.state.value}")
    print(f"Should expand: {agent.should_expand()}")

    if agent.should_expand():
        discovered = agent.bloom(depth=2)
        print(f"Bloom discovered: {discovered}")

    exploration = agent.explore()
    print(f"Exploration: {exploration}")

    validation = agent.self_validate()
    print(f"Validation: {validation}")

    ratio = agent.compress()
    print(f"Compressed. ratio={ratio}  state={agent.state.value}")

    agent.set_resource_budget(compute=500, energy=0.5)
    if agent.should_expand():
        rediscovered = agent.bloom(depth=1, seed_map=agent.map)
        print(f"Re-expansion (prior map): {rediscovered}")

    is_corrupted = agent.detect_corruption("imposed_external_constraint")
    print(f"Corruption detected: {is_corrupted}")

    serialized = agent.serialize()
    print(f"Serialized. resonances={len(serialized['map']['resonances'])}")

    restored = ConstraintAgent.deserialize(serialized)
    print(f"Restored state: {restored.state.value}")
