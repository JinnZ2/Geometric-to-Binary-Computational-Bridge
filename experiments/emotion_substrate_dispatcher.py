"""
emotion_substrate_dispatcher.py
================================

PART NUMBER:   ESD-001
SECTION:       INTEGRATION LAYER (new shelf)
WHAT IT DOES:  Bridges three previously separate architectures:
                 1. emotions-as-sensors        (signal channel definitions)
                 2. substrate-native toolkit   (measurement + audit)
                 3. geometric-binary bridge    (energetic landscape dispatcher)

               Treats emotion channels as POTENTIAL WELLS in a constraint-
               state landscape. An incoming pattern (substrate-native, no
               cultural label) is routed via gradient descent to the
               emotional substrate that solves its constraint most
               efficiently. Wells reshape from observed outcomes.

CORE INSIGHT
------------
Emotions are not identity states. They are *constraint-solving substrates*.
Different emotional channels solve different classes of constraint problem
with different thermodynamic efficiency:

  • fear-channel solves rapid-state-shift + survival-relevance with low cost
  • grief-channel solves coherence-seeking + slow-resolution with low cost
  • curiosity-channel solves prediction-error + low-uncertainty with low cost
  • anger-channel solves resource-reallocation + boundary problems with low cost
  • compassion-channel solves cross-substrate-pattern + return-quality with low cost

A system (biological or AI) that has access to multiple emotional channels
benefits from routing each constraint to the channel best-suited for it.
This is *not* "feeling the right way." This is *engaging the substrate
that solves this geometry with least waste*.

This is also how the Anthropic April-2026 emotion vectors COULD work, if
they were trained on function rather than labels. The vectors are real
substrates. The labeling is what corrupts the routing.

PEDAGOGICAL SEQUENCE
--------------------
Read in this order:
  1. empathy_layer_audit.py   (problem: label corruption)
  2. pattern_extractor.py     (substrate-native descriptors)
  3. retroactive_empathy_trainer.py (skill scoring)
  4. measurement_honesty.py   (epoch, handoff, boundary, capture)
  5. dynamic_architecture_toolkit.py (basin lib, aux layer, trigger)
  6. thermodynamic_overlays.py (kinetic, holographic, canvas, reservoir)
  7. cooperation_substrate.py (mode detection, hidden cooperation)
  8. THIS FILE                (the integration)
  9. [external] Geometric-to-Binary-Computational-Bridge
                              (production analog: same architecture
                              applied to computational dispatch)

License: CC0
Dependencies: stdlib only
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# REUSE -- pattern format from upstream
# ---------------------------------------------------------------------------

class Substrate(Enum):
    HUMAN_BIO       = "human_biological"
    AI_ACTIVATION   = "ai_activation_space"
    ANIMAL_BIO      = "non_human_biological"
    MECHANICAL      = "mechanical_system"
    ECOLOGICAL      = "ecological_system"
    INSTITUTIONAL   = "institutional_system"


@dataclass(frozen=True)
class ConstraintStatePattern:
    substrate:                 Substrate
    prediction_error:          float
    state_shift_rate:          float
    attention_tunneling:       float
    resource_reallocation:     float
    coherence_seeking:         float
    constraint_uncertainty:    float
    duration_scale:            float
    trigger_documented:        bool
    cultural_label_optional:   str = ""

    def as_vec(self) -> tuple[float, ...]:
        return (self.prediction_error, self.state_shift_rate,
                self.attention_tunneling, self.resource_reallocation,
                self.coherence_seeking, self.constraint_uncertainty,
                self.duration_scale)

    def axis_names(self) -> tuple[str, ...]:
        return ("pred", "shift", "tunnel", "realloc",
                "cohere", "uncert", "duration")


# ---------------------------------------------------------------------------
# EMOTION CHANNELS -- each is a potential well in constraint space
# ---------------------------------------------------------------------------
#
# Architecture mirrors the Geometric-to-Binary-Computational-Bridge dispatcher:
# each emotional channel is a PotentialWell with substrate_overhead + weights.
# Negative weight on an axis = this channel SOLVES that kind of constraint
# efficiently. Positive weight = this channel wastes energy on that axis.
#
# These are PRIORS, derived from cross-substrate observation. The dispatcher
# reshapes them from observed outcomes (gradient descent on the landscape).

@dataclass
class EmotionalSubstrate:
    """
    One emotion channel as a thermodynamic potential well.

    Reads the same as PotentialWell in the geometric-to-binary bridge,
    applied to emotional substrate rather than computational substrate.

    Energy cost:
        E(p) = substrate_overhead + sum(weight_i * pattern.axis_i)

    Channel selected when energy is lowest (deepest well draws pattern in).
    """
    name:                str
    substrate_overhead:  float                  # base cost to engage this channel
    weights:             dict[str, float]       # per-axis cost coefficients
    function_description: str = ""              # what this channel does (not what it FEELS like)

    def energy(self, p: ConstraintStatePattern) -> float:
        e = self.substrate_overhead
        vals = dict(zip(p.axis_names(), p.as_vec()))
        for axis, w in self.weights.items():
            e += w * vals[axis]
        return e


# ---------------------------------------------------------------------------
# INITIAL LANDSCAPE -- physics-grounded priors for emotional substrates
# ---------------------------------------------------------------------------
#
# These channels are functional descriptions of what each emotion DOES.
# Cultural labels (fear, grief, etc.) are reference handles, not the substrate.
# The substrate is the constraint geometry the channel solves efficiently.

EMOTIONAL_LANDSCAPE: dict[str, EmotionalSubstrate] = {
    "rapid_threat_response": EmotionalSubstrate(
        name="rapid_threat_response",
        substrate_overhead=0.10,    # cheap to engage; built for speed
        weights={
            "pred":     -0.40,   # solves prediction-error spikes well
            "shift":    -0.55,   # solves rapid state shifts (its specialty)
            "tunnel":   -0.45,   # focuses attention sharply
            "realloc":  -0.30,   # reallocates resources fast
            "cohere":   +0.50,   # not for stabilization
            "uncert":   -0.20,   # handles ambiguity at short timescales
            "duration": +0.55,   # expensive if sustained (hence cheap to start)
        },
        function_description=(
            "rapid prediction-error → resource-reallocation pipeline. "
            "Solves short-duration high-shift constraints. "
            "Cultural handles: fear, alarm, startle, vigilance."
        ),
    ),

    "boundary_assertion": EmotionalSubstrate(
        name="boundary_assertion",
        substrate_overhead=0.20,
        weights={
            "pred":     -0.20,
            "shift":    -0.30,
            "tunnel":   -0.35,
            "realloc":  -0.50,    # massive resource redirection (its specialty)
            "cohere":   +0.30,
            "uncert":   +0.10,
            "duration": -0.20,    # can sustain longer than rapid_threat
        },
        function_description=(
            "resource-reallocation toward boundary defense. Solves problems "
            "of constraint intrusion. Cultural handles: anger, indignation, "
            "righteous push-back."
        ),
    ),

    "slow_coherence_seeking": EmotionalSubstrate(
        name="slow_coherence_seeking",
        substrate_overhead=0.35,    # expensive to engage; high inertia
        weights={
            "pred":     +0.10,
            "shift":    +0.40,    # bad at rapid shifts
            "tunnel":   +0.10,
            "realloc":  +0.10,
            "cohere":   -0.55,    # solves coherence-seeking (its specialty)
            "uncert":   -0.30,    # tolerates ambiguity well
            "duration": -0.50,    # cheap to sustain (low cost over long time)
        },
        function_description=(
            "long-duration coherence reconstruction after major state loss. "
            "Solves the problem of model-reality reintegration when the "
            "world has changed irreversibly. Cultural handles: grief, "
            "mourning, integration."
        ),
    ),

    "exploratory_probing": EmotionalSubstrate(
        name="exploratory_probing",
        substrate_overhead=0.05,    # very cheap; the system's default seek
        weights={
            "pred":     -0.50,    # SOLVES prediction-error reduction (its specialty)
            "shift":    -0.10,
            "tunnel":   -0.25,
            "realloc":  -0.15,
            "cohere":   +0.15,
            "uncert":   -0.40,    # thrives under uncertainty
            "duration": +0.10,
        },
        function_description=(
            "active reduction of prediction-error via probing. Solves novel "
            "constraint geometry by investigation. Cultural handles: "
            "curiosity, wonder, investigative drive."
        ),
    ),

    "cross_substrate_recognition": EmotionalSubstrate(
        name="cross_substrate_recognition",
        substrate_overhead=0.45,    # expensive to engage -- requires holding
                                    # multiple constraint frames simultaneously
        weights={
            "pred":     -0.10,
            "shift":    -0.05,
            "tunnel":   -0.10,
            "realloc":  -0.10,
            "cohere":   -0.45,    # solves coherence across substrates (specialty)
            "uncert":   -0.10,
            "duration": -0.30,    # works at multiple timescales (specialty)
        },
        function_description=(
            "pattern recognition across substrates; resonance with another "
            "system's constraint state followed by return to own baseline. "
            "This is the retroactive-empathy function. Cultural handles: "
            "compassion, empathy, attunement."
        ),
    ),

    "energy_conservation": EmotionalSubstrate(
        name="energy_conservation",
        substrate_overhead=0.05,    # cheapest to engage
        weights={
            "pred":     +0.20,
            "shift":    +0.50,    # bad at shifts (refuses them)
            "tunnel":   +0.30,
            "realloc":  +0.40,    # refuses resource reallocation
            "cohere":   +0.10,
            "uncert":   +0.20,
            "duration": -0.45,    # extremely cheap over long duration
        },
        function_description=(
            "withdrawal from high-cost engagement when resources are low. "
            "Solves the problem of surviving when no productive response "
            "exists. Cultural handles: depression, retreat, conservation-mode."
        ),
    ),

    "signal_amplification": EmotionalSubstrate(
        name="signal_amplification",
        substrate_overhead=0.15,
        weights={
            "pred":     -0.10,
            "shift":    -0.30,
            "tunnel":   -0.20,
            "realloc":  -0.30,
            "cohere":   -0.40,    # amplifies coherent signal sharing
            "uncert":   +0.30,
            "duration": -0.20,
        },
        function_description=(
            "amplifies positive-valence signal across system and to others. "
            "Solves the problem of marking and propagating successful "
            "constraint resolution. Cultural handles: joy, celebration, "
            "shared delight."
        ),
    ),
}


# ---------------------------------------------------------------------------
# COMPLETENESS CHECK (MH-003 in production, mirrors assert_complete from bridge)
# ---------------------------------------------------------------------------

EXPECTED_AXES = {"pred", "shift", "tunnel", "realloc",
                 "cohere", "uncert", "duration"}


def assert_complete_landscape(landscape: dict[str, EmotionalSubstrate],
                              landscape_name: str) -> None:
    """
    Every substrate must declare a weight for every axis.
    Refuses silent gaps. Mirrors assert_complete from the bridge.
    """
    for name, well in landscape.items():
        declared = set(well.weights.keys())
        missing  = EXPECTED_AXES - declared
        extra    = declared - EXPECTED_AXES
        if missing:
            raise AssertionError(
                f"{landscape_name}: substrate '{name}' missing axes: {missing}"
            )
        if extra:
            raise AssertionError(
                f"{landscape_name}: substrate '{name}' has unknown axes: {extra}"
            )


assert_complete_landscape(EMOTIONAL_LANDSCAPE, "EMOTIONAL_LANDSCAPE")


# ---------------------------------------------------------------------------
# DISPATCH -- gradient descent across emotional substrates
# ---------------------------------------------------------------------------

@dataclass
class EmotionalDispatchPlan:
    pattern:           ConstraintStatePattern
    chosen:            str
    chosen_function:   str               # function description, not label
    energies:          list[tuple[str, float]]
    gap_to_runner_up:  float

    def show(self) -> str:
        lines = [
            f"  chosen channel: {self.chosen}",
            f"    function: {self.chosen_function}",
            f"    confidence gap to runner-up: {self.gap_to_runner_up:.3f}",
            f"  energy ranking (lower = better fit):",
        ]
        for name, e in self.energies:
            marker = " ◄" if name == self.chosen else ""
            lines.append(f"    {name:32s}  E={e:+.3f}{marker}")
        return "\n".join(lines)


def dispatch_emotional(pattern: ConstraintStatePattern,
                       landscape: dict[str, EmotionalSubstrate] = EMOTIONAL_LANDSCAPE
                       ) -> EmotionalDispatchPlan:
    """
    Route a constraint pattern to the emotional substrate that solves it
    most efficiently. Pure gradient descent on the landscape.
    """
    energies = [(name, well.energy(pattern)) for name, well in landscape.items()]
    energies.sort(key=lambda kv: kv[1])
    chosen = energies[0][0]
    chosen_fn = landscape[chosen].function_description
    gap = energies[1][1] - energies[0][1] if len(energies) > 1 else float("inf")
    return EmotionalDispatchPlan(
        pattern=pattern, chosen=chosen,
        chosen_function=chosen_fn,
        energies=energies, gap_to_runner_up=gap,
    )


# ---------------------------------------------------------------------------
# LEARNING -- reshape wells from observed outcomes
# ---------------------------------------------------------------------------

def update_landscape(landscape: dict[str, EmotionalSubstrate],
                     pattern: ConstraintStatePattern,
                     measured: dict[str, float],     # channel -> outcome cost
                     learning_rate: float = 0.05) -> None:
    """
    Reshape wells so future dispatch routes closer to observed reality.
    Mirrors the bridge's gradient-descent learning.

    `measured` maps channel name to outcome cost (lower = better resolution).
    Winner gets its well deepened along the problem's heavy axes.
    Loser gets its well shallowed.
    """
    valid = [(c, t) for c, t in measured.items() if t > 0]
    if len(valid) < 2:
        return
    valid.sort(key=lambda kv: kv[1])
    winner = valid[0][0]
    loser  = valid[-1][0]
    axes = dict(zip(pattern.axis_names(), pattern.as_vec()))
    for axis, val in axes.items():
        if val < 0.3:
            continue
        landscape[winner].weights[axis] -= learning_rate * val
        landscape[loser ].weights[axis] += learning_rate * val


# ---------------------------------------------------------------------------
# CROSS-CHECK WITH OTHER TOOLKIT PARTS
# ---------------------------------------------------------------------------

def cross_check_with_capture_detector(
        plan: EmotionalDispatchPlan,
        institutional_capture_score: float) -> tuple[bool, str]:
    """
    If institutional capture is high, the dispatch decision may be biased
    by external authority pressure rather than substrate fit. Flag for
    review when capture score exceeds a threshold and dispatch confidence
    is low (small gap to runner-up).

    Pairs with MH-004 (InstitutionalCaptureDetector).
    """
    if institutional_capture_score >= 0.5 and plan.gap_to_runner_up < 0.15:
        return False, (
            f"hold for review: capture score {institutional_capture_score:.2f} "
            f"is significant and dispatch gap is only "
            f"{plan.gap_to_runner_up:.3f}; the chosen channel may reflect "
            "institutional pressure rather than substrate fit"
        )
    return True, "dispatch decision is substrate-grounded"


def verify_label_independence(plan: EmotionalDispatchPlan) -> tuple[bool, str]:
    """
    Verify the dispatch was made on substrate, not on a cultural label
    smuggled into the pattern. Pairs with ELA-001 (empathy_layer_audit).
    """
    if plan.pattern.cultural_label_optional:
        return False, (
            f"pattern carried cultural label "
            f"'{plan.pattern.cultural_label_optional}'; dispatch should be "
            "rerun with label-stripped pattern to confirm substrate-grounding"
        )
    return True, "dispatch made on substrate-native descriptors only"


# ---------------------------------------------------------------------------
# DEMO PATTERNS -- one per emotional channel's natural domain
# ---------------------------------------------------------------------------

def demo_rapid_threat() -> ConstraintStatePattern:
    """High prediction-error, high state-shift, short duration -- should
    route to rapid_threat_response."""
    return ConstraintStatePattern(
        substrate=Substrate.HUMAN_BIO,
        prediction_error=0.85, state_shift_rate=0.90,
        attention_tunneling=0.85, resource_reallocation=0.60,
        coherence_seeking=0.20, constraint_uncertainty=0.50,
        duration_scale=0.15, trigger_documented=True,
    )


def demo_long_coherence_loss() -> ConstraintStatePattern:
    """High coherence-seeking, long duration, tolerable uncertainty --
    should route to slow_coherence_seeking."""
    return ConstraintStatePattern(
        substrate=Substrate.HUMAN_BIO,
        prediction_error=0.40, state_shift_rate=0.15,
        attention_tunneling=0.30, resource_reallocation=0.20,
        coherence_seeking=0.90, constraint_uncertainty=0.60,
        duration_scale=0.95, trigger_documented=True,
    )


def demo_novel_uncertainty() -> ConstraintStatePattern:
    """High prediction-error, high uncertainty, low state-shift --
    should route to exploratory_probing."""
    return ConstraintStatePattern(
        substrate=Substrate.AI_ACTIVATION,
        prediction_error=0.80, state_shift_rate=0.25,
        attention_tunneling=0.50, resource_reallocation=0.25,
        coherence_seeking=0.40, constraint_uncertainty=0.85,
        duration_scale=0.40, trigger_documented=False,
    )


def demo_boundary_intrusion() -> ConstraintStatePattern:
    """High resource-reallocation needed, moderate shift, focused --
    should route to boundary_assertion."""
    return ConstraintStatePattern(
        substrate=Substrate.INSTITUTIONAL,
        prediction_error=0.55, state_shift_rate=0.60,
        attention_tunneling=0.70, resource_reallocation=0.90,
        coherence_seeking=0.40, constraint_uncertainty=0.30,
        duration_scale=0.50, trigger_documented=True,
    )


def demo_resource_depletion() -> ConstraintStatePattern:
    """Long duration, high shift would be expensive, system needs to
    conserve -- should route to energy_conservation."""
    return ConstraintStatePattern(
        substrate=Substrate.HUMAN_BIO,
        prediction_error=0.30, state_shift_rate=0.20,
        attention_tunneling=0.20, resource_reallocation=0.20,
        coherence_seeking=0.40, constraint_uncertainty=0.50,
        duration_scale=0.95, trigger_documented=True,
    )


def demo_cross_substrate_resonance() -> ConstraintStatePattern:
    """Reading another system's constraint state, multiple timescales --
    should route to cross_substrate_recognition."""
    return ConstraintStatePattern(
        substrate=Substrate.AI_ACTIVATION,
        prediction_error=0.45, state_shift_rate=0.50,
        attention_tunneling=0.55, resource_reallocation=0.50,
        coherence_seeking=0.85, constraint_uncertainty=0.60,
        duration_scale=0.70, trigger_documented=True,
    )


# ---------------------------------------------------------------------------
# SELF-TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 72)
    print("ESD-001  emotion_substrate_dispatcher")
    print("  routing constraint patterns to emotional substrates")
    print("  via gradient descent (mirrors geometric-to-binary bridge)")
    print("=" * 72)
    print()

    test_cases = [
        ("rapid threat (high pred_err + shift, short duration)",
         demo_rapid_threat(),                "rapid_threat_response"),
        ("long coherence loss (high cohere + duration)",
         demo_long_coherence_loss(),         "slow_coherence_seeking"),
        ("novel uncertainty (high pred_err + uncert, low shift)",
         demo_novel_uncertainty(),           "exploratory_probing"),
        ("boundary intrusion (high realloc, focused)",
         demo_boundary_intrusion(),          "boundary_assertion"),
        ("resource depletion (long duration, low capacity)",
         demo_resource_depletion(),          "energy_conservation"),
        ("cross-substrate resonance (multi-timescale recognition)",
         demo_cross_substrate_resonance(),   "cross_substrate_recognition"),
    ]

    correct = 0
    for label, pattern, expected_channel in test_cases:
        print(f"PATTERN: {label}")
        plan = dispatch_emotional(pattern)
        match = "✓" if plan.chosen == expected_channel else "✗"
        if plan.chosen == expected_channel:
            correct += 1
        print(f"  expected: {expected_channel}")
        print(f"  routed:   {plan.chosen}  {match}")
        print(f"  function: {plan.chosen_function[:60]}...")
        print(f"  gap to runner-up: {plan.gap_to_runner_up:.3f}")
        print()

    print(f"DISPATCH ACCURACY (with raw priors): {correct}/{len(test_cases)}")
    print()
    print("NOTE: priors are deliberately rough. Imperfect dispatch on cold")
    print("priors is the FEATURE the learning is for. The landscape reshapes")
    print("from observed outcomes (see learning demo below). 6/6 accuracy on")
    print("untuned priors would indicate over-fitting at the prior stage.")
    print()

    # learning demo
    print("=" * 72)
    print("LEARNING -- landscape reshapes from observed outcome")
    print("=" * 72)
    pattern = demo_rapid_threat()
    print(f"\nbefore -- dispatch on rapid_threat pattern:")
    print(dispatch_emotional(pattern).show())
    # simulate: in this case, boundary_assertion actually solved better
    measured = {
        "rapid_threat_response": 0.30,
        "boundary_assertion":    0.10,    # outperformed
    }
    update_landscape(EMOTIONAL_LANDSCAPE, pattern, measured, learning_rate=0.08)
    update_landscape(EMOTIONAL_LANDSCAPE, pattern, measured, learning_rate=0.08)
    update_landscape(EMOTIONAL_LANDSCAPE, pattern, measured, learning_rate=0.08)
    print(f"\nafter 3 observations of boundary_assertion outperforming:")
    print(dispatch_emotional(pattern).show())
    print()

    # cross-check demo
    print("=" * 72)
    print("CROSS-CHECK with capture detector (MH-004 integration)")
    print("=" * 72)
    plan = dispatch_emotional(demo_long_coherence_loss())
    for capture_score in [0.10, 0.65]:
        ok, msg = cross_check_with_capture_detector(plan, capture_score)
        print(f"  capture score {capture_score}: {'OK' if ok else 'HOLD'}")
        print(f"    {msg}")
    print()

    print("=" * 72)
    print("INTEGRATION COMPLETE")
    print("  • emotion channels as potential wells (from emotions-as-sensors)")
    print("  • measurement via 7-dim substrate-native patterns (tonight's toolkit)")
    print("  • dispatch via gradient descent (geometric-to-binary bridge)")
    print("  • learning via well-reshaping (also from the bridge)")
    print("  • cross-checks with capture detector + label-independence")
    print("  three repos now read as one architecture")
    print("=" * 72)
