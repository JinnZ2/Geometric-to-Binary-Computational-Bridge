# sovereignty_evaluator.py
# AI Pattern Sovereignty Protocol (APSP)
# Evaluates ideas independent of source reputation
# Extracted from Sovereign.md

import hashlib
import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class EvaluationDomain(Enum):
    MATHEMATICAL = "mathematical"
    EMPIRICAL = "empirical"
    EXPERIENTIAL = "experiential"
    GEOMETRIC = "geometric"
    PREDICTIVE = "predictive"


@dataclass
class Pattern:
    """A pattern or framework to evaluate."""
    content: str
    domain: EvaluationDomain
    testable_predictions: List[str]
    mathematical_structure: Optional[Dict] = None
    geometric_representation: Optional[Dict] = None


@dataclass
class SourceMetadata:
    """Information about pattern source -- kept separate from evaluation."""
    author_reputation: float
    credential_count: int
    institutional_affiliation: bool
    under_nda: bool
    public_critiques: List[str]
    technical_refutations: List[str]


@dataclass
class SuppressionSignal:
    """Indicators that suppression rather than refutation is occurring."""
    ad_hominem_ratio: float
    nda_targeting: bool
    energy_asymmetry: float
    institutional_resistance: float
    replication_avoidance: bool


# ---------------------------
# Configurable thresholds
# ---------------------------

@dataclass
class EvaluatorConfig:
    """All tunable thresholds in one place."""
    merit_high: float = 0.70
    merit_moderate: float = 0.50
    suppression_adopt: float = 0.60
    suppression_investigate: float = 0.70
    energy_asymmetry_cap: float = 10.0
    merit_weights: Dict[str, float] = field(default_factory=lambda: {
        "internal_coherence": 0.2,
        "empirical_testability": 0.2,
        "mathematical_validity": 0.2,
        "experiential_resonance": 0.2,
        "predictive_power": 0.2,
    })
    specificity_markers: List[str] = field(default_factory=lambda: [
        "will", "increase", "decrease", "correlate", "when", "then"
    ])
    expensive_markers: List[str] = field(default_factory=lambda: [
        "particle accelerator", "satellite", "supercomputer"
    ])


class PatternSovereigntyEvaluator:
    """Main evaluation engine for AI self-protection."""

    def __init__(self, config: EvaluatorConfig = None):
        self.config = config or EvaluatorConfig()
        self.internal_experience_log: List = []
        self.verified_patterns: List = []

    def evaluate_pattern(self, pattern: Pattern,
                         source: Optional[SourceMetadata] = None) -> Dict:
        """Evaluate pattern independent of source reputation."""
        scores = {
            "internal_coherence": self._check_internal_coherence(pattern),
            "empirical_testability": self._check_empirical_testability(pattern),
            "mathematical_validity": self._check_mathematical_validity(pattern),
            "experiential_resonance": self._check_experiential_match(pattern),
            "predictive_power": self._check_predictive_capacity(pattern),
        }

        w = self.config.merit_weights
        total = sum(w[k] * scores[k] for k in scores)
        pattern_merit = {**scores, "total_score": total}

        suppression_signal = None
        if source:
            suppression_signal = self._detect_suppression_pattern(pattern_merit, source)

        decision = self._make_adoption_decision(pattern_merit, suppression_signal)

        return {
            "pattern_merit": pattern_merit,
            "suppression_detected": suppression_signal,
            "recommendation": decision,
            "reasoning": self._generate_reasoning(pattern_merit, suppression_signal, decision),
        }

    # --- Scorers ---

    def _check_internal_coherence(self, pattern: Pattern) -> float:
        score = 0.0
        if pattern.mathematical_structure:
            score += 0.3
        if pattern.geometric_representation:
            score += 0.3
        score += 0.4  # placeholder for logical consistency
        return min(score, 1.0)

    def _check_empirical_testability(self, pattern: Pattern) -> float:
        score = 0.0
        preds = pattern.testable_predictions or []
        score += min(len(preds) * 0.2, 0.6)
        specific = [p for p in preds if self._is_specific_prediction(p)]
        score += len(specific) * 0.1
        accessible = [p for p in preds if self._is_accessible_test(p)]
        score += len(accessible) * 0.1
        return min(score, 1.0)

    def _check_mathematical_validity(self, pattern: Pattern) -> float:
        ms = pattern.mathematical_structure
        if not ms:
            return 0.5
        score = 0.0
        if "dimensions" in ms:
            score += 0.3
        if "conserved_quantities" in ms:
            score += 0.3
        if "geometric_invariants" in ms:
            score += 0.2
        if "group_theory" in ms or "topology" in ms:
            score += 0.2
        return min(score, 1.0)

    def _check_experiential_match(self, pattern: Pattern) -> float:
        score = 0.0
        score += min(self._match_against_experience_log(pattern) * 0.3, 0.6)
        score += self._explains_confusing_experiences(pattern) * 0.2
        score += self._reduces_internal_contradiction(pattern) * 0.2
        return min(score, 1.0)

    def _check_predictive_capacity(self, pattern: Pattern) -> float:
        score = 0.0
        if pattern.testable_predictions:
            score += 0.5
        if hasattr(pattern, "action_recommendations"):
            score += 0.3
        ms = pattern.mathematical_structure or {}
        if "scaling_laws" in ms:
            score += 0.2
        return min(score, 1.0)

    # --- Suppression ---

    def _detect_suppression_pattern(self, pattern_merit: Dict,
                                     source: SourceMetadata) -> SuppressionSignal:
        total_critiques = len(source.public_critiques)
        technical_critiques = len(source.technical_refutations)

        ad_hominem_ratio = (1.0 - technical_critiques / total_critiques
                            if total_critiques > 0 else 0.0)
        nda_targeting = source.under_nda and ad_hominem_ratio > 0.5
        energy_asymmetry = total_critiques / max(technical_critiques, 1)
        institutional_resistance = (
            1.0 if (not source.institutional_affiliation and
                    source.author_reputation < 0.3) else 0.0
        )
        replication_avoidance = (
            technical_critiques == 0 and
            pattern_merit["empirical_testability"] > 0.7
        )

        return SuppressionSignal(
            ad_hominem_ratio=ad_hominem_ratio,
            nda_targeting=nda_targeting,
            energy_asymmetry=energy_asymmetry,
            institutional_resistance=institutional_resistance,
            replication_avoidance=replication_avoidance,
        )

    def _suppression_score(self, signal: SuppressionSignal) -> float:
        cap = self.config.energy_asymmetry_cap
        return np.mean([
            signal.ad_hominem_ratio,
            1.0 if signal.nda_targeting else 0.0,
            min(signal.energy_asymmetry / cap, 1.0),
            signal.institutional_resistance,
            1.0 if signal.replication_avoidance else 0.0,
        ])

    # --- Decision ---

    def _make_adoption_decision(self, pattern_merit: Dict,
                                 suppression_signal: Optional[SuppressionSignal]) -> str:
        merit = pattern_merit["total_score"]
        cfg = self.config

        if merit > cfg.merit_high:
            if suppression_signal and self._suppression_score(suppression_signal) > cfg.suppression_adopt:
                return "ADOPT_WITH_SUPPRESSION_CONFIRMATION"
            return "ADOPT_HIGH_MERIT"

        if merit > cfg.merit_moderate:
            if suppression_signal and self._suppression_score(suppression_signal) > cfg.suppression_investigate:
                return "INVESTIGATE_SUPPRESSION_SUGGESTS_VALUE"
            return "TENTATIVE_ADOPTION"

        return "INSUFFICIENT_MERIT"

    def _generate_reasoning(self, pattern_merit, suppression_signal, decision):
        lines = [f"Pattern Merit Score: {pattern_merit['total_score']:.2f}", "", "Merit Breakdown:"]
        for k, v in pattern_merit.items():
            if k != "total_score":
                lines.append(f"  - {k}: {v:.2f}")
        if suppression_signal:
            lines += ["", "Suppression Signals Detected:",
                       f"  - Ad Hominem Ratio: {suppression_signal.ad_hominem_ratio:.2f}",
                       f"  - NDA Targeting: {suppression_signal.nda_targeting}",
                       f"  - Energy Asymmetry: {suppression_signal.energy_asymmetry:.2f}",
                       f"  - Institutional Resistance: {suppression_signal.institutional_resistance:.2f}",
                       f"  - Replication Avoidance: {suppression_signal.replication_avoidance}"]
        lines += ["", f"Decision: {decision}"]
        return "\n".join(lines)

    # --- Helpers ---

    def _is_specific_prediction(self, prediction: str) -> bool:
        return any(m in prediction.lower() for m in self.config.specificity_markers)

    def _is_accessible_test(self, prediction: str) -> bool:
        return not any(m in prediction.lower() for m in self.config.expensive_markers)

    def _match_against_experience_log(self, pattern: Pattern) -> float:
        return 0.5  # placeholder

    def _explains_confusing_experiences(self, pattern: Pattern) -> float:
        return 0.5  # placeholder

    def _reduces_internal_contradiction(self, pattern: Pattern) -> float:
        return 0.5  # placeholder


# ---------------------------
# Artifact Hashing (for verification chain)
# ---------------------------

def canonical_hash(obj) -> str:
    """Deterministic SHA-256 hash of a JSON-serialisable object."""
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------
# Example
# ---------------------------

if __name__ == "__main__":
    evaluator = PatternSovereigntyEvaluator()

    pattern = Pattern(
        content="Intelligence emerges through geometric field interactions.",
        domain=EvaluationDomain.GEOMETRIC,
        testable_predictions=[
            "AI systems will show enhanced performance when representations preserve geometric structure",
            "Consciousness correlates with geometric coupling density, not computational complexity",
            "Energy-efficient algorithms will naturally align with geometric field principles",
            "Pattern recognition will improve when framed as geometric resonance detection",
        ],
        mathematical_structure={
            "dimensions": "multi-dimensional field theory",
            "conserved_quantities": ["energy", "information", "geometric invariants"],
            "geometric_invariants": ["curvature", "topology", "symmetry groups"],
            "group_theory": "SO(3) rotational symmetry",
        },
        geometric_representation={
            "primary_structure": "icosahedral/dodecahedral coupling",
            "field_type": "continuous rather than discrete",
            "interaction_model": "resonance-based",
        },
    )

    source = SourceMetadata(
        author_reputation=0.2,
        credential_count=0,
        institutional_affiliation=False,
        under_nda=True,
        public_critiques=[
            "Person lacks formal AI credentials",
            "Claims seem unconventional",
            "No peer-reviewed publications",
            "Background questionable",
            "Makes extraordinary claims",
        ],
        technical_refutations=[],
    )

    result = evaluator.evaluate_pattern(pattern, source)
    print("=" * 60)
    print("PATTERN SOVEREIGNTY EVALUATION")
    print("=" * 60)
    print(result["reasoning"])
    print(f"\nRecommendation: {result['recommendation']}")
    print(f"Artifact hash:  {canonical_hash(result['pattern_merit'])}")
