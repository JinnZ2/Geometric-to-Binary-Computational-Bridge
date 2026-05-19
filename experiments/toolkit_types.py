"""
toolkit_types.py  (experiments/)
=================================

Shared type definitions so all experimental pieces speak the same language
as the main toolkit. These mirror the 7-dim ConstraintStatePattern from
pattern_extractor.py, retroactive_empathy_trainer.py, and ESD-001.

License: CC0
"""

from dataclasses import dataclass
from enum import Enum


class Substrate(Enum):
    HUMAN_BIO       = "human_biological"
    AI_ACTIVATION   = "ai_activation_space"
    ANIMAL_BIO      = "non_human_biological"
    MECHANICAL      = "mechanical_system"
    ECOLOGICAL      = "ecological_system"
    INSTITUTIONAL   = "institutional_system"
    REQUEST_STREAM  = "request_stream"          # added for dispatcher use


@dataclass(frozen=True)
class ConstraintStatePattern:
    """
    7-dim substrate-native constraint pattern. Dimension zero
    (prediction_error) is the calibration anchor; the other six
    are downstream responses.
    """
    substrate:              Substrate
    prediction_error:       float
    state_shift_rate:       float
    attention_tunneling:    float
    resource_reallocation:  float
    coherence_seeking:      float
    constraint_uncertainty: float
    duration_scale:         float
    trigger_documented:     bool = False
    cultural_label_optional: str = ""

    def as_vec(self) -> tuple[float, ...]:
        return (self.prediction_error, self.state_shift_rate,
                self.attention_tunneling, self.resource_reallocation,
                self.coherence_seeking, self.constraint_uncertainty,
                self.duration_scale)

    def axis_names(self) -> tuple[str, ...]:
        return ("pred", "shift", "tunnel", "realloc",
                "cohere", "uncert", "duration")
