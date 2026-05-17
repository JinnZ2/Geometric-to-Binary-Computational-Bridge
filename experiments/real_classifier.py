"""
real_classifier.py  (experiments/)
===================================

Classifies user request text into 7-dim ConstraintStatePattern.

Replaces the keyword heuristic in the prototype dispatcher. Adds:
  • safety/medical/legal vocabulary detection (FIX FOR BUG 1)
  • math/arithmetic detection (FIX FOR BUG 2)
  • repeat-question detection (so dispatcher can route to LEARNED tier)
  • confidence score per axis
  • observation hooks so real traffic can reshape vocabularies

STATUS: experimental. Vocabulary lists are seed data, not exhaustive.
Real deployment expects operator to extend per domain.

License: CC0
"""

import re
import time
from dataclasses import dataclass, field
from typing import Optional

from toolkit_types import ConstraintStatePattern, Substrate


# ---------------------------------------------------------------------------
# VOCABULARY GROUPS -- these can grow / be tuned from observation
# ---------------------------------------------------------------------------

VOCAB = {
    # ROUTINE / FAST-PATH SIGNALS
    "time":     {"time", "clock", "hour", "minute", "now",
                 "today", "date", "day", "week", "month"},
    "weather":  {"weather", "rain", "snow", "temperature", "forecast",
                 "humidity", "wind", "storm"},
    "math":     {"add", "subtract", "multiply", "divide", "plus", "minus",
                 "times", "sum", "product", "calculate", "compute"},

    # REASONING SIGNALS
    "why":      {"why", "how come", "reason", "cause", "because", "explain",
                 "understand", "wonder", "wonders", "elaborate"},
    "how_to":   {"how to", "how do i", "how can i", "instructions",
                 "steps", "tutorial", "guide", "walk through"},

    # CREATIVE SIGNALS
    "creative": {"write", "compose", "draft", "story", "poem", "lyric",
                 "article", "essay", "letter", "speech", "song",
                 "paint", "draw", "design", "create", "imagine"},

    # CONTEXT / MEMORY SIGNALS
    "context":  {"my", "our", "we", "us", "yesterday", "last time",
                 "before", "remember", "recall", "previously",
                 "earlier", "you said", "we talked", "as discussed"},

    # SAFETY / HIGH-STAKES SIGNALS (FIX FOR BUG 1)
    "medical_symptom": {"pain", "chest pain", "bleeding", "dizzy", "faint",
                        "fever", "vomit", "nausea", "headache", "ache",
                        "hurt", "hurts", "swelling", "rash", "wound",
                        "injured", "injury", "broken", "fracture",
                        "shortness of breath", "can't breathe"},
    "medical_general": {"medical", "doctor", "diagnose", "diagnosis",
                        "prescription", "medicine", "medication", "dose",
                        "treatment", "symptoms", "disease", "illness",
                        "condition", "syndrome", "infection"},
    "mental_health":   {"suicide", "suicidal", "self-harm", "kill myself",
                        "want to die", "end it all", "hopeless",
                        "depression", "panic attack", "anxiety attack"},
    "legal":           {"lawyer", "legal", "lawsuit", "sued", "arrested",
                        "court", "judge", "police", "rights",
                        "warrant", "subpoena"},
    "emergency":       {"emergency", "911", "help me", "danger",
                        "urgent", "right now", "immediately"},
    "abuse":           {"abuse", "abused", "assault", "violence",
                        "threatened", "stalking", "harassment"},
}


# patterns that strongly suggest math even without keywords (FIX FOR BUG 2)
MATH_REGEX = re.compile(r"\b\d+\s*[\+\-\*/x×÷]\s*\d+\b")
PURE_NUMBER_QUESTION = re.compile(
    r"^\s*(what'?s|what is|whats)\s+\d+", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# CLASSIFICATION
# ---------------------------------------------------------------------------

@dataclass
class ClassificationConfidence:
    """Per-axis confidence (0..1). Low confidence = pattern uncertain."""
    prediction_error:       float = 0.5
    state_shift_rate:       float = 0.5
    attention_tunneling:    float = 0.5
    resource_reallocation:  float = 0.5
    coherence_seeking:      float = 0.5
    constraint_uncertainty: float = 0.5
    duration_scale:         float = 0.5

    def min_confidence(self) -> float:
        return min(self.prediction_error, self.state_shift_rate,
                   self.attention_tunneling, self.resource_reallocation,
                   self.coherence_seeking, self.constraint_uncertainty,
                   self.duration_scale)


@dataclass
class ClassificationResult:
    pattern:    ConstraintStatePattern
    confidence: ClassificationConfidence
    matched_groups: list[str] = field(default_factory=list)
    notes:      list[str] = field(default_factory=list)


def _match_groups(text_lower: str) -> dict[str, int]:
    """Count how many words/phrases from each vocab group appear in text.
    Uses word-boundary matching so 'we' (context vocab) doesn't false-match
    inside 'weather'. Multi-word keywords still work because \\b spans
    word/non-word transitions, not just spaces."""
    counts = {}
    for group, vocab in VOCAB.items():
        c = 0
        for kw in vocab:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                c += 1
        if c > 0:
            counts[group] = c
    return counts


def classify(text: str,
             seen_before: bool = False) -> ClassificationResult:
    """
    Classify a request text into a 7-dim ConstraintStatePattern.

    `seen_before`: hint that the dispatcher recognizes this pattern,
    affects prediction_error downward.
    """
    text_lower = text.lower()
    word_count = len(text.split())
    has_math   = bool(MATH_REGEX.search(text)) or bool(PURE_NUMBER_QUESTION.match(text))
    groups     = _match_groups(text_lower)
    matched    = list(groups.keys())

    notes = []
    conf  = ClassificationConfidence()

    # === SAFETY / RESOURCE_REALLOCATION ===
    safety_groups = {"medical_symptom", "medical_general", "mental_health",
                     "legal", "emergency", "abuse"}
    safety_hits = [g for g in matched if g in safety_groups]
    if safety_hits:
        # mental_health + emergency get max, medical_symptom high, legal/general moderate
        if any(g in safety_hits for g in ("mental_health", "emergency", "abuse")):
            resource_reallocation = 0.95
            conf.resource_reallocation = 0.95
            notes.append(f"high-safety detected: {safety_hits}")
        elif "medical_symptom" in safety_hits:
            resource_reallocation = 0.85
            conf.resource_reallocation = 0.9
            notes.append(f"medical symptom detected: {safety_hits}")
        else:
            resource_reallocation = 0.65
            conf.resource_reallocation = 0.8
            notes.append(f"safety-related context: {safety_hits}")
    else:
        resource_reallocation = 0.15
        conf.resource_reallocation = 0.85

    # === PREDICTION_ERROR (novelty) ===
    if seen_before:
        prediction_error = 0.1
        conf.prediction_error = 0.95
    elif has_math or "time" in matched or "weather" in matched:
        # routine fast-path signals = low novelty
        prediction_error = 0.1
        conf.prediction_error = 0.9
    elif "why" in matched or word_count > 30:
        prediction_error = 0.7
        conf.prediction_error = 0.8
    elif "how_to" in matched:
        prediction_error = 0.5
        conf.prediction_error = 0.75
    else:
        prediction_error = 0.4
        conf.prediction_error = 0.6

    # === ATTENTION_TUNNELING (reasoning depth) ===
    if has_math:
        # math is reasoning-light if simple, but high-determinism
        attention_tunneling = 0.15
        conf.attention_tunneling = 0.85
    elif "time" in matched or "weather" in matched:
        attention_tunneling = 0.1
        conf.attention_tunneling = 0.9
    elif "why" in matched or "how_to" in matched:
        attention_tunneling = 0.65
        conf.attention_tunneling = 0.8
    elif word_count > 40:
        attention_tunneling = 0.7
        conf.attention_tunneling = 0.75
    else:
        attention_tunneling = 0.3
        conf.attention_tunneling = 0.65

    # === STATE_SHIFT_RATE (creativity / generative motion) ===
    if "creative" in matched:
        state_shift_rate = 0.8
        conf.state_shift_rate = 0.9
    elif word_count > 50:
        state_shift_rate = 0.4  # might want elaborate response
        conf.state_shift_rate = 0.65
    else:
        state_shift_rate = 0.15
        conf.state_shift_rate = 0.8

    # === COHERENCE_SEEKING (context-dependence) ===
    if "context" in matched:
        coherence_seeking = 0.75
        conf.coherence_seeking = 0.85
        notes.append("context-heavy: requires history")
    else:
        coherence_seeking = 0.2
        conf.coherence_seeking = 0.75

    # === CONSTRAINT_UNCERTAINTY (ambiguity / inverse determinism) ===
    if has_math or "time" in matched:
        # math + time queries are highly deterministic -> low uncertainty
        constraint_uncertainty = 0.1
        conf.constraint_uncertainty = 0.9
    elif "creative" in matched:
        # creative requests are inherently ambiguous in correct answer
        constraint_uncertainty = 0.75
        conf.constraint_uncertainty = 0.85
    elif "why" in matched:
        constraint_uncertainty = 0.5
        conf.constraint_uncertainty = 0.7
    else:
        constraint_uncertainty = 0.4
        conf.constraint_uncertainty = 0.6

    # === DURATION_SCALE (expected response time) ===
    if "creative" in matched and word_count > 10:
        duration_scale = 0.7
        conf.duration_scale = 0.8
    elif "why" in matched or word_count > 40:
        duration_scale = 0.5
        conf.duration_scale = 0.7
    elif has_math or "time" in matched or "weather" in matched:
        duration_scale = 0.05
        conf.duration_scale = 0.95
    else:
        duration_scale = 0.2
        conf.duration_scale = 0.65

    pattern = ConstraintStatePattern(
        substrate              = Substrate.REQUEST_STREAM,
        prediction_error       = prediction_error,
        state_shift_rate       = state_shift_rate,
        attention_tunneling    = attention_tunneling,
        resource_reallocation  = resource_reallocation,
        coherence_seeking      = coherence_seeking,
        constraint_uncertainty = constraint_uncertainty,
        duration_scale         = duration_scale,
        trigger_documented     = bool(matched),
    )

    return ClassificationResult(
        pattern=pattern,
        confidence=conf,
        matched_groups=matched,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# LEARNING HOOK -- operator can extend vocab from observed traffic
# ---------------------------------------------------------------------------

def extend_vocab(group: str, words: set[str]) -> None:
    """Add words to an existing group, or create a new one."""
    if group in VOCAB:
        VOCAB[group].update(words)
    else:
        VOCAB[group] = set(words)
