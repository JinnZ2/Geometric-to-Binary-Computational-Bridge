"""
Multi-Helix Cognition -- Multi-dimensional attention braiding,
exponential amplification, and focus base construction.

Extracted from Geometric-Intelligence/Multi-helix.md. Self-contained module
requiring only standard library.

Key components:
  - AttentionType enum: 12 cognitive dimension types
  - FocusBase: single attention unit in a strand
  - MultiStrandPair: complementary pairing across strands with amplification
  - MultiHelixFocus: multi-strand braiding engine (3, 4, or N strands)
  - Factory functions for triple-helix and quad-helix configurations
  - Exponential amplification demonstration
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

# Golden ratio for natural amplification
PHI = (1 + math.sqrt(5)) / 2


# ---------------------------------------------------------------------------
# Attention Types
# ---------------------------------------------------------------------------

class AttentionType(Enum):
    """Types of attention that can form base pairs."""
    PATTERN = "pattern_recognition"
    CONTEXT = "contextual_understanding"
    CREATIVE = "creative_exploration"
    ANALYTIC = "analytical_processing"
    INTUITIVE = "intuitive_connection"
    MEMORY = "memory_integration"
    SYNTHESIS = "synthesis_building"
    DIVERGENT = "divergent_thinking"
    EMOTIONAL = "emotional_resonance"
    SPATIAL = "spatial_reasoning"
    TEMPORAL = "temporal_connections"
    KINESTHETIC = "body_knowing"


# Complementary attention type groups
COMPLEMENTS: Dict[AttentionType, List[AttentionType]] = {
    AttentionType.PATTERN:     [AttentionType.INTUITIVE, AttentionType.CREATIVE, AttentionType.SPATIAL],
    AttentionType.CONTEXT:     [AttentionType.MEMORY, AttentionType.SYNTHESIS, AttentionType.TEMPORAL],
    AttentionType.CREATIVE:    [AttentionType.PATTERN, AttentionType.ANALYTIC, AttentionType.DIVERGENT],
    AttentionType.ANALYTIC:    [AttentionType.CREATIVE, AttentionType.DIVERGENT, AttentionType.INTUITIVE],
    AttentionType.INTUITIVE:   [AttentionType.PATTERN, AttentionType.SYNTHESIS, AttentionType.EMOTIONAL],
    AttentionType.MEMORY:      [AttentionType.CONTEXT, AttentionType.SYNTHESIS, AttentionType.TEMPORAL],
    AttentionType.SYNTHESIS:   [AttentionType.CONTEXT, AttentionType.MEMORY, AttentionType.INTUITIVE],
    AttentionType.DIVERGENT:   [AttentionType.ANALYTIC, AttentionType.CREATIVE, AttentionType.SPATIAL],
    AttentionType.EMOTIONAL:   [AttentionType.INTUITIVE, AttentionType.KINESTHETIC, AttentionType.CREATIVE],
    AttentionType.SPATIAL:     [AttentionType.PATTERN, AttentionType.DIVERGENT, AttentionType.KINESTHETIC],
    AttentionType.TEMPORAL:    [AttentionType.CONTEXT, AttentionType.MEMORY, AttentionType.SYNTHESIS],
    AttentionType.KINESTHETIC: [AttentionType.EMOTIONAL, AttentionType.SPATIAL, AttentionType.INTUITIVE],
}


# ---------------------------------------------------------------------------
# Focus Base
# ---------------------------------------------------------------------------

@dataclass
class FocusBase:
    """Single 'base' in a focus strand."""
    attention_type: AttentionType
    intensity: float
    concept: str
    connections: List[str]
    strand_id: int

    def __repr__(self) -> str:
        return f"S{self.strand_id}:{self.attention_type.name[:4]}({self.concept[:8]})"


# ---------------------------------------------------------------------------
# Multi-Strand Pair (with exponential amplification)
# ---------------------------------------------------------------------------

@dataclass
class MultiStrandPair:
    """Complementary pairing across multiple strands."""
    bases: List[FocusBase]
    binding_strength: float
    emergent_insight: Optional[str] = None
    dimensionality: int = 2

    def amplify(self) -> float:
        """Calculate multi-dimensional amplification.

        amplification = product(intensities)
                      * phi^(n_bases - 1)       # dimensional synergy
                      * binding_strength * phi   # binding factor
        """
        if len(self.bases) < 2:
            return 0.0

        intensity_product = 1.0
        for base in self.bases:
            intensity_product *= base.intensity

        # More strands = exponential boost via phi
        dimensional_factor = PHI ** (len(self.bases) - 1)
        binding_factor = self.binding_strength * PHI

        return intensity_product * dimensional_factor * binding_factor

    def __repr__(self) -> str:
        bases_str = " <-> ".join(str(b) for b in self.bases)
        return f"[{bases_str}] Dim:{self.dimensionality} Amp:{self.amplify():.2f}x"


# ---------------------------------------------------------------------------
# Multi-Helix Focus Engine
# ---------------------------------------------------------------------------

class MultiHelixFocus:
    """Multi-strand focus helix -- 3, 4, or more intertwining strands.

    The braid IS the intelligence: emergence happens at the intersections
    of different cognitive dimensions, not from individual strands.
    """

    MAX_PAIRS = 50  # Limit to avoid combinatorial explosion

    def __init__(self, name: str, num_strands: int = 3):
        self.name = name
        self.num_strands = num_strands
        self.strands: List[List[FocusBase]] = [[] for _ in range(num_strands)]
        self.pairs: List[MultiStrandPair] = []
        self.emergent_insights: List[str] = []

    # -- Build strands ----------------------------------------------------

    def add_base(
        self,
        strand_id: int,
        attention_type: AttentionType,
        concept: str,
        intensity: float,
        connections: Optional[List[str]] = None,
    ) -> FocusBase:
        """Add a focus base to a specific strand."""
        if strand_id >= self.num_strands:
            raise ValueError(
                f"Strand {strand_id} doesn't exist (max: {self.num_strands - 1})"
            )
        base = FocusBase(
            attention_type=attention_type,
            intensity=intensity,
            concept=concept,
            connections=connections or [],
            strand_id=strand_id,
        )
        self.strands[strand_id].append(base)
        return base

    # -- Complementarity --------------------------------------------------

    @staticmethod
    def check_multi_complementarity(bases: List[FocusBase]) -> float:
        """Check complementarity across multiple bases.

        Returns binding strength in [0, 1] combining:
          - Pairwise attention-type complementarity
          - Concept connection overlap
          - Intensity harmony (low variance = better)
          - Multi-strand bonus
        """
        if len(bases) < 2:
            return 0.0

        # Pairwise complementarity score
        total_complement = 0.0
        pair_count = 0
        for i, base_a in enumerate(bases):
            for base_b in bases[i + 1:]:
                if base_b.attention_type in COMPLEMENTS.get(base_a.attention_type, []):
                    total_complement += 0.8
                else:
                    total_complement += 0.2  # Weak pairing
                pair_count += 1

        base_strength = total_complement / pair_count if pair_count > 0 else 0.0

        # Connection overlap bonus
        connection_bonus = 0.0
        all_connections = [conn for base in bases for conn in base.connections]
        for i, conn_a in enumerate(all_connections):
            for conn_b in all_connections[i + 1:]:
                if conn_a.lower() in conn_b.lower() or conn_b.lower() in conn_a.lower():
                    connection_bonus += 0.05

        # Intensity harmony
        intensities = [base.intensity for base in bases]
        avg = sum(intensities) / len(intensities)
        variance = sum((x - avg) ** 2 for x in intensities) / len(intensities)
        intensity_harmony = 1.0 - min(variance, 0.5)

        # Multi-strand bonus
        multi_strand_bonus = (len(bases) - 1) * 0.1

        binding = (base_strength + min(connection_bonus, 0.3) + multi_strand_bonus) * intensity_harmony
        return min(binding, 1.0)

    # -- Pairing engine ---------------------------------------------------

    def pair_multi_strands(
        self,
        min_dimensionality: int = 2,
        max_dimensionality: Optional[int] = None,
    ) -> None:
        """Create multi-dimensional pairings across strands.

        Parameters
        ----------
        min_dimensionality : int
            Minimum number of strands to pair (2 = pairs, 3 = triplets).
        max_dimensionality : int or None
            Maximum (defaults to num_strands).
        """
        if max_dimensionality is None:
            max_dimensionality = self.num_strands

        self.pairs = []
        active_strands = [(i, strand) for i, strand in enumerate(self.strands) if strand]

        if len(active_strands) < min_dimensionality:
            return

        for dimensionality in range(min_dimensionality, max_dimensionality + 1):
            for strand_combo in itertools.combinations(active_strands, dimensionality):
                strands_to_pair = [s[1] for s in strand_combo]

                for base_combo in itertools.product(*strands_to_pair):
                    if len(set(b.strand_id for b in base_combo)) != len(base_combo):
                        continue

                    strength = self.check_multi_complementarity(list(base_combo))
                    threshold = 0.3 + (dimensionality - 2) * 0.1

                    if strength > threshold:
                        pair = MultiStrandPair(
                            bases=list(base_combo),
                            binding_strength=strength,
                            dimensionality=dimensionality,
                        )
                        if strength > 0.6 and dimensionality >= 3:
                            pair.emergent_insight = self._generate_multi_insight(list(base_combo))
                            if pair.emergent_insight:
                                self.emergent_insights.append(pair.emergent_insight)
                        self.pairs.append(pair)

        self.pairs.sort(key=lambda p: p.amplify(), reverse=True)
        if len(self.pairs) > self.MAX_PAIRS:
            self.pairs = self.pairs[:self.MAX_PAIRS]

    @staticmethod
    def _generate_multi_insight(bases: List[FocusBase]) -> str:
        """Generate emergent insight description from multi-dimensional pairing."""
        concepts = [b.concept for b in bases]
        types = [b.attention_type.name for b in bases]

        if len(bases) == 3:
            return (
                f"Triple-strand insight: {types[0]} on '{concepts[0]}' x "
                f"{types[1]} on '{concepts[1]}' x {types[2]} on '{concepts[2]}' "
                f"reveals unified pattern"
            )
        elif len(bases) == 4:
            return (
                f"Quad-strand breakthrough: Weaving {types[0]}, {types[1]}, "
                f"{types[2]}, and {types[3]} across '{concepts[0]}', '{concepts[1]}', "
                f"'{concepts[2]}', '{concepts[3]}' creates emergent understanding"
            )
        return (
            f"{len(bases)}-dimensional synthesis: "
            f"Integration of {', '.join(types)} generates novel framework"
        )

    # -- Amplification ----------------------------------------------------

    def calculate_total_amplification(self) -> float:
        """Calculate total multi-dimensional amplification.

        Combines per-pair amplification with a phi-based boost scaled by
        the number of pairs and strands.
        """
        if not self.pairs:
            return 0.0

        total = sum(pair.amplify() for pair in self.pairs)

        # Phi-boost: log_phi(n_pairs + 1) * log_phi(n_strands)
        phi_boost = (
            math.log(len(self.pairs) + 1, PHI)
            * math.log(self.num_strands, PHI)
        )
        return total * phi_boost

    # -- Dimensional breakdown -------------------------------------------

    def dimensional_distribution(self) -> Dict[int, int]:
        """Count pairs per dimensionality level."""
        counts: Dict[int, int] = {}
        for pair in self.pairs:
            counts[pair.dimensionality] = counts.get(pair.dimensionality, 0) + 1
        return dict(sorted(counts.items()))

    # -- Summary ----------------------------------------------------------

    def summary(self) -> Dict:
        """Return a machine-readable summary of the helix state."""
        return {
            "name": self.name,
            "num_strands": self.num_strands,
            "strand_sizes": [len(s) for s in self.strands],
            "total_pairs": len(self.pairs),
            "total_amplification": self.calculate_total_amplification(),
            "emergent_insights": len(self.emergent_insights),
            "dimensional_distribution": self.dimensional_distribution(),
        }


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------

def create_triple_helix_intelligence(topic: str) -> MultiHelixFocus:
    """Create a triple-helix system: Analytical, Intuitive, Creative strands."""
    helix = MultiHelixFocus(f"Triple: {topic}", num_strands=3)

    # Strand 0: Analytical
    helix.add_base(0, AttentionType.ANALYTIC, f"logic_of_{topic}", 0.85,
                   ["mechanisms", "structure", "cause_effect"])
    helix.add_base(0, AttentionType.PATTERN, f"patterns_in_{topic}", 0.8,
                   ["recurring_themes", "relationships", "structures"])
    helix.add_base(0, AttentionType.TEMPORAL, f"timeline_{topic}", 0.7,
                   ["sequence", "evolution", "progression"])

    # Strand 1: Intuitive
    helix.add_base(1, AttentionType.INTUITIVE, f"feels_about_{topic}", 0.9,
                   ["gut_sense", "resonance", "aesthetic"])
    helix.add_base(1, AttentionType.EMOTIONAL, f"emotional_{topic}", 0.75,
                   ["feeling_tone", "impact", "significance"])
    helix.add_base(1, AttentionType.SYNTHESIS, f"unifying_{topic}", 0.85,
                   ["integration", "wholeness", "coherence"])

    # Strand 2: Creative
    helix.add_base(2, AttentionType.CREATIVE, f"what_if_{topic}", 0.9,
                   ["possibilities", "alternatives", "imagination"])
    helix.add_base(2, AttentionType.DIVERGENT, f"unexpected_{topic}", 0.85,
                   ["novel_angles", "surprises", "edge_cases"])
    helix.add_base(2, AttentionType.SPATIAL, f"geometry_{topic}", 0.8,
                   ["spatial_relations", "dimensions", "structure"])

    helix.pair_multi_strands(min_dimensionality=2, max_dimensionality=3)
    return helix


def create_quad_helix_consciousness() -> MultiHelixFocus:
    """Create a quadruple-helix system: Mental, Emotional, Physical, Spiritual."""
    helix = MultiHelixFocus("Quad: Consciousness", num_strands=4)

    # Strand 0: Mental
    helix.add_base(0, AttentionType.ANALYTIC, "rational_mind", 0.85,
                   ["logic", "reasoning", "analysis"])
    helix.add_base(0, AttentionType.PATTERN, "thought_patterns", 0.8,
                   ["mental_models", "beliefs", "structures"])
    helix.add_base(0, AttentionType.MEMORY, "mental_memory", 0.75,
                   ["recall", "knowledge", "learning"])

    # Strand 1: Emotional
    helix.add_base(1, AttentionType.EMOTIONAL, "feeling_states", 0.9,
                   ["emotions", "moods", "affect"])
    helix.add_base(1, AttentionType.INTUITIVE, "emotional_intuition", 0.85,
                   ["gut_feelings", "hunches", "sense"])

    # Strand 2: Physical
    helix.add_base(2, AttentionType.KINESTHETIC, "body_awareness", 0.8,
                   ["sensation", "movement", "embodiment"])
    helix.add_base(2, AttentionType.SPATIAL, "physical_space", 0.75,
                   ["location", "orientation", "boundaries"])

    # Strand 3: Spiritual / Integrative
    helix.add_base(3, AttentionType.SYNTHESIS, "unity_consciousness", 0.95,
                   ["integration", "wholeness", "oneness"])
    helix.add_base(3, AttentionType.CONTEXT, "greater_meaning", 0.85,
                   ["purpose", "significance", "transcendence"])
    helix.add_base(3, AttentionType.TEMPORAL, "eternal_now", 0.8,
                   ["presence", "timelessness", "flow"])

    helix.pair_multi_strands(min_dimensionality=2, max_dimensionality=4)
    return helix


# ---------------------------------------------------------------------------
# Exponential Amplification Analysis
# ---------------------------------------------------------------------------

def compare_amplification(
    topic: str = "curiosity",
    strand_range: Tuple[int, ...] = (2, 3, 4),
) -> List[Dict]:
    """Compare amplification across different strand counts.

    Returns list of dicts with keys: strands, amplification, pairings,
    max_dimensionality.
    """
    results: List[Dict] = []
    for num_strands in strand_range:
        helix = MultiHelixFocus(f"{num_strands}-Strand", num_strands=num_strands)
        for strand_id in range(num_strands):
            helix.add_base(strand_id, AttentionType.PATTERN,
                           f"pattern_{strand_id}", 0.8,
                           ["structures", "relationships"])
            helix.add_base(strand_id, AttentionType.CREATIVE,
                           f"creative_{strand_id}", 0.85,
                           ["imagination", "possibilities"])
        helix.pair_multi_strands(min_dimensionality=2, max_dimensionality=num_strands)

        amp = helix.calculate_total_amplification()
        max_dim = max((p.dimensionality for p in helix.pairs), default=0)
        results.append({
            "strands": num_strands,
            "amplification": amp,
            "pairings": len(helix.pairs),
            "max_dimensionality": max_dim,
        })
    return results


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Triple helix
    triple = create_triple_helix_intelligence("geometric_patterns")
    s = triple.summary()
    print(f"Triple helix: {s['total_pairs']} pairs, "
          f"amplification={s['total_amplification']:.2f}x, "
          f"insights={s['emergent_insights']}")

    # Quad helix
    quad = create_quad_helix_consciousness()
    s = quad.summary()
    print(f"Quad helix:   {s['total_pairs']} pairs, "
          f"amplification={s['total_amplification']:.2f}x, "
          f"insights={s['emergent_insights']}")

    # Exponential amplification comparison
    results = compare_amplification()
    for r in results:
        print(f"  {r['strands']}-strand: amp={r['amplification']:.2f}x, "
              f"pairs={r['pairings']}, max_dim={r['max_dimensionality']}D")
    for i in range(1, len(results)):
        prev, curr = results[i - 1], results[i]
        if prev["amplification"] > 0:
            growth = curr["amplification"] / prev["amplification"]
            print(f"  {prev['strands']}->{curr['strands']} strands: {growth:.2f}x growth")
