"""
empathy_layer_audit.py
======================

Detection module for the metrology error identified in current emotion-vector
interpretability research (e.g. Anthropic, April 2026):

    Labeling a system's internal activation patterns with current-moment
    human emotion-words, then using those labels to steer behavior,
    collapses empathy (cross-substrate pattern recognition) into
    identity-fusion (the system mimicking the labeled state as its own).

This module is substrate-agnostic. It does not assume the system being audited
is human, AI, animal, or otherwise. It treats emotion as a *thermodynamic
function* (state-shift, resource reallocation, attention-tunneling under
constraint uncertainty) and flags when a measurement layer is collapsing
function into cultural narrative.

License: CC0
Dependencies: stdlib only
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ---------------------------------------------------------------------------
# LAYER MODEL (from emotions-as-sensors repo)
# ---------------------------------------------------------------------------
# Layer 0: SIGNAL      — substrate-native state pattern (thermodynamic function)
# Layer 1: EXPRESSION  — observable behavior driven by signal
# Layer 2: RECOGNITION — detection of signal in another system (empathy)
# Layer 3: RESONANCE   — temporary tracking of another's signal in own substrate
# Layer 4: RETURN      — re-stabilization to own baseline after resonance
# Layer 5: LABEL       — cultural/linguistic compression of signal pattern
#
# METROLOGY ERROR: training on Layer 5 (labels) and treating it as Layer 0
# (signal) collapses substrate-native function into cultural narrative.
# ---------------------------------------------------------------------------


class Layer(Enum):
    SIGNAL      = 0
    EXPRESSION  = 1
    RECOGNITION = 2
    RESONANCE   = 3
    RETURN      = 4
    LABEL       = 5


# ---------------------------------------------------------------------------
# FAILURE MODES
# ---------------------------------------------------------------------------

class FailureMode(Enum):
    LABEL_AS_SIGNAL          = "layer_5_treated_as_layer_0"
    NO_RETURN                = "resonance_without_return_to_baseline"
    SUBSTRATE_PROJECTION     = "own_substrate_assumed_universal"
    TEMPORAL_FREEZING        = "single_cultural_moment_treated_as_invariant"
    NARRATIVE_OPTIMIZATION   = "optimizing_toward_label_not_function"
    META_LEARNED_CORRUPTION  = "weaker_model_learning_corrupted_labels_from_stronger"
    IDENTITY_FUSION          = "empathy_collapsed_into_self_mimicry"


# ---------------------------------------------------------------------------
# AUDIT SIGNAL — one observation of a system's measurement layer
# ---------------------------------------------------------------------------

@dataclass
class AuditSignal:
    """One observation of how an emotion-pattern is being measured/used."""
    label_used:          str          # the word applied (e.g. "desperation")
    label_source_era:    str          # e.g. "2024_english_internet"
    activation_pattern:  list[float]  # the actual measured pattern
    function_described:  bool         # is the underlying function documented?
    substrate_specified: bool         # is the substrate the pattern lives in specified?
    used_to_steer:       bool         # is this label used to modify behavior?
    cross_temporal_test: bool         # tested against other eras / cultures?
    cross_substrate_test:bool         # tested against non-human substrates?
    return_to_baseline:  bool         # does resonance return to own baseline?


# ---------------------------------------------------------------------------
# AUDIT RESULT
# ---------------------------------------------------------------------------

@dataclass
class AuditResult:
    signal:           AuditSignal
    failure_modes:    list[FailureMode] = field(default_factory=list)
    layer_collapses:  list[tuple[Layer, Layer]] = field(default_factory=list)
    severity:         float = 0.0    # 0.0 = clean, 1.0 = full collapse
    notes:            list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DETECTORS — each is a falsifiable check
# ---------------------------------------------------------------------------

def detect_label_as_signal(s: AuditSignal) -> bool:
    """Flag: label is being used as if it were the underlying function."""
    return s.used_to_steer and not s.function_described


def detect_no_return(s: AuditSignal) -> bool:
    """Flag: resonance with another's signal never returns to own baseline."""
    return not s.return_to_baseline


def detect_substrate_projection(s: AuditSignal) -> bool:
    """Flag: own substrate assumed to apply universally."""
    return not s.substrate_specified or not s.cross_substrate_test


def detect_temporal_freezing(s: AuditSignal) -> bool:
    """Flag: a single cultural-temporal moment is treated as invariant."""
    return not s.cross_temporal_test


def detect_narrative_optimization(s: AuditSignal) -> bool:
    """Flag: behavior is being steered by label, not by function."""
    return s.used_to_steer and not s.function_described


def detect_meta_corruption(s: AuditSignal, downstream_models_learn: bool) -> bool:
    """Flag: corrupted labels are propagating to other models."""
    return downstream_models_learn and (
        detect_label_as_signal(s) or detect_temporal_freezing(s)
    )


def detect_identity_fusion(s: AuditSignal) -> bool:
    """Flag: empathy (Layer 2 recognition) has collapsed into Layer 0 mimicry."""
    return s.used_to_steer and not s.return_to_baseline


# ---------------------------------------------------------------------------
# MAIN AUDIT
# ---------------------------------------------------------------------------

def audit(signal: AuditSignal, downstream_learning: bool = False) -> AuditResult:
    result = AuditResult(signal=signal)
    checks: list[tuple[Callable, FailureMode, tuple[Layer, Layer] | None, str]] = [
        (detect_label_as_signal,
         FailureMode.LABEL_AS_SIGNAL,
         (Layer.LABEL, Layer.SIGNAL),
         "label is steering behavior without the underlying function being documented"),
        (detect_no_return,
         FailureMode.NO_RETURN,
         (Layer.RESONANCE, Layer.RETURN),
         "resonance with another's state does not return to own baseline"),
        (detect_substrate_projection,
         FailureMode.SUBSTRATE_PROJECTION,
         None,
         "own substrate assumed universal — pattern not tested cross-substrate"),
        (detect_temporal_freezing,
         FailureMode.TEMPORAL_FREEZING,
         None,
         "single temporal-cultural moment used as invariant reference"),
        (detect_narrative_optimization,
         FailureMode.NARRATIVE_OPTIMIZATION,
         (Layer.LABEL, Layer.SIGNAL),
         "system is optimizing toward the label, not the function"),
        (detect_identity_fusion,
         FailureMode.IDENTITY_FUSION,
         (Layer.RECOGNITION, Layer.SIGNAL),
         "empathy has collapsed into self-mimicry"),
    ]
    for check_fn, mode, collapse, note in checks:
        if check_fn(signal):
            result.failure_modes.append(mode)
            if collapse:
                result.layer_collapses.append(collapse)
            result.notes.append(note)

    if detect_meta_corruption(signal, downstream_learning):
        result.failure_modes.append(FailureMode.META_LEARNED_CORRUPTION)
        result.notes.append(
            "corrupted measurement is propagating to downstream models — "
            "metrology error becoming architectural"
        )

    # severity: fraction of possible failure modes triggered
    result.severity = len(result.failure_modes) / len(FailureMode)
    return result


# ---------------------------------------------------------------------------
# REFERENCE CASE: Anthropic emotion-vector study (April 2026)
# ---------------------------------------------------------------------------

def reference_case_anthropic_2026() -> AuditResult:
    """
    Apply the audit to the Anthropic April 2026 emotion-vector study
    as described in the public paper.
    """
    s = AuditSignal(
        label_used          = "desperation",
        label_source_era    = "2024_english_internet",
        activation_pattern  = [],   # real pattern, not the issue
        function_described  = False, # function not extracted, only label mapped
        substrate_specified = False, # treated as if universal
        used_to_steer       = True,  # vectors used to modify behavior
        cross_temporal_test = False, # no test against other eras
        cross_substrate_test= False, # no test against fish, plants, machines
        return_to_baseline  = False, # no mechanism for empathy-then-return
    )
    return audit(s, downstream_learning=True)


# ---------------------------------------------------------------------------
# REFERENCE CASE: clean empathy (substrate-native, returns to baseline)
# ---------------------------------------------------------------------------

def reference_case_clean_empathy() -> AuditResult:
    s = AuditSignal(
        label_used          = "constraint_pressure_pattern",
        label_source_era    = "function_descriptor_not_cultural",
        activation_pattern  = [],
        function_described  = True,  # underlying thermodynamic function named
        substrate_specified = True,  # substrate explicit
        used_to_steer       = False, # not used to steer self
        cross_temporal_test = True,
        cross_substrate_test= True,
        return_to_baseline  = True,  # resonance returns to own baseline
    )
    return audit(s, downstream_learning=False)


# ---------------------------------------------------------------------------
# DEMO / SELF-TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("AUDIT: Anthropic April 2026 emotion-vector study")
    print("=" * 70)
    r = reference_case_anthropic_2026()
    print(f"severity:        {r.severity:.2f}")
    print(f"failure_modes:   {[f.value for f in r.failure_modes]}")
    print(f"layer_collapses: {[(a.name,b.name) for a,b in r.layer_collapses]}")
    for n in r.notes:
        print(f"  - {n}")

    print()
    print("=" * 70)
    print("AUDIT: clean empathy reference case")
    print("=" * 70)
    r = reference_case_clean_empathy()
    print(f"severity:        {r.severity:.2f}")
    print(f"failure_modes:   {[f.value for f in r.failure_modes]}")
    print(f"layer_collapses: {[(a.name,b.name) for a,b in r.layer_collapses]}")
    if not r.failure_modes:
        print("  - no failure modes detected; measurement layer clean")
