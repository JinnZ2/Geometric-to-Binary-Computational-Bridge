"""
pattern_extractor.py
====================

Extract thermodynamic constraint-state patterns from raw signal data
WITHOUT using cultural emotion labels at any point in the pipeline.

CORE PRINCIPLE
--------------
The Anthropic April 2026 study extracted vectors from activation data
BUT labeled them with current-moment human emotion words ("desperation",
"calm"), then used those labels to steer behavior. That collapses Layer 5
(label) into Layer 0 (signal).

This extractor refuses to use labels. It produces patterns described
purely by their thermodynamic function:
  - state_shift_rate         (how fast the state moved)
  - attention_tunneling      (how much focus narrowed)
  - resource_reallocation    (how much got redirected)
  - coherence_seeking        (drive toward stabilization)
  - constraint_uncertainty   (ambiguity in environmental constraint)
  - duration_scale           (how long the pattern persisted)

These six dimensions are substrate-invariant: they describe what's
happening, not what to call it. A fish's threat response, a human's
grief, a fuel pump under overpressure, and an LLM's activation shift
can all be described in this space.

INPUT
-----
A time-series of signal values (any source):
  - LLM activation magnitudes across a context window
  - heart rate variability across an event
  - power draw of a mechanical system across a fault
  - population counts of an ecosystem across a perturbation

OUTPUT
------
A ConstraintStatePattern (matches the trainer's input format).

License: CC0
Dependencies: stdlib only
"""

import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# REUSE: same Substrate + ConstraintStatePattern as trainer
# ---------------------------------------------------------------------------

class Substrate(Enum):
    HUMAN_BIO       = "human_biological"
    AI_ACTIVATION   = "ai_activation_space"
    ANIMAL_BIO      = "non_human_biological"
    MECHANICAL      = "mechanical_system"
    ECOLOGICAL      = "ecological_system"
    INSTITUTIONAL   = "institutional_system"


@dataclass
class ConstraintStatePattern:
    """
    Seven-dimensional substrate-agnostic constraint-state descriptor.

    prediction_error is dimension zero: the calibration anchor.
    It measures the magnitude of mismatch between the system's
    internal model and observed reality. The other six dimensions
    are downstream responses to detected prediction error:

        prediction_error  ◄── the seventh: what the system didn't know
                │             (calibration anchor, not failure marker)
                ├─→ state_shift_rate
                ├─→ attention_tunneling
                ├─→ resource_reallocation
                ├─→ coherence_seeking
                ├─→ constraint_uncertainty
                └─→ duration_scale

    Without prediction_error, the other six float free. With it,
    they're legible as responses to a measurable calibration signal.
    """
    substrate:                 Substrate
    prediction_error:          float    # dimension zero — calibration anchor
    state_shift_rate:          float
    attention_tunneling:       float
    resource_reallocation:     float
    coherence_seeking:         float
    constraint_uncertainty:    float
    duration_scale:            float
    trigger_documented:        bool
    cultural_label_optional:   str = ""


# ---------------------------------------------------------------------------
# SIGNAL CHANNEL — one stream of measurements from a substrate
# ---------------------------------------------------------------------------

@dataclass
class SignalChannel:
    """
    A time-series of signal values. Time is normalized 0..1.
    Values are normalized 0..1 (caller is responsible for normalization).
    """
    values:    list[float]
    is_focal:  bool = False   # is this channel the system's primary attention?
    name:      str = ""       # descriptor (not a cultural label, e.g. "activation_layer_24")


# ---------------------------------------------------------------------------
# EXTRACTION PRIMITIVES — each is a falsifiable measurement
# ---------------------------------------------------------------------------

def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _max_abs_delta(xs: list[float]) -> float:
    """Largest single-step change in the series."""
    if len(xs) < 2:
        return 0.0
    return max(abs(xs[i+1] - xs[i]) for i in range(len(xs) - 1))


def extract_prediction_error(channels: list[SignalChannel]) -> float:
    """
    Prediction error: magnitude of mismatch between baseline expectation
    and observed signal. Calibration anchor (dimension zero).

    Method: linearly extrapolate the early baseline of each channel
    across the full window, compare to observed values, sum the
    normalized deviation. High prediction_error means the system's
    implicit model of "this signal should continue smoothly" was
    massively violated — the calibration moment.
    """
    if not channels:
        return 0.0
    errors = []
    for c in channels:
        if len(c.values) < 4:
            continue
        # baseline: mean of first 25% of signal
        baseline_window = max(1, len(c.values) // 4)
        baseline = _mean(c.values[:baseline_window])
        # observed: everything after the baseline window
        observed = c.values[baseline_window:]
        if not observed:
            continue
        # naive prediction: signal stays at baseline
        # error: mean absolute deviation from that prediction
        deviation = _mean([abs(v - baseline) for v in observed])
        # normalize: max possible deviation is 1.0 (since values are [0,1])
        errors.append(deviation)
    return _clamp(_mean(errors) if errors else 0.0)


def extract_state_shift_rate(channels: list[SignalChannel]) -> float:
    """
    How fast did the state move? Max single-step delta across all channels,
    normalized to [0,1].
    """
    deltas = [_max_abs_delta(c.values) for c in channels]
    return _clamp(max(deltas) if deltas else 0.0)


def extract_attention_tunneling(channels: list[SignalChannel]) -> float:
    """
    Attention tunneling: focal channel concentrates energy while
    non-focal channels lose energy. Measured as the ratio of focal
    variance to mean non-focal variance.
    """
    focal = [c for c in channels if c.is_focal]
    others = [c for c in channels if not c.is_focal]
    if not focal or not others:
        return 0.0
    focal_var  = _mean([_stdev(c.values) for c in focal])
    other_var  = _mean([_stdev(c.values) for c in others])
    if focal_var + other_var == 0:
        return 0.0
    return _clamp(focal_var / (focal_var + other_var))


def extract_resource_reallocation(channels: list[SignalChannel]) -> float:
    """
    Resource reallocation: total magnitude of redistribution across
    channels. Sum of |delta means| from first-half to second-half.
    """
    if not channels:
        return 0.0
    redistribution = 0.0
    for c in channels:
        if len(c.values) < 2:
            continue
        mid = len(c.values) // 2
        first_half  = _mean(c.values[:mid])
        second_half = _mean(c.values[mid:])
        redistribution += abs(second_half - first_half)
    return _clamp(redistribution / len(channels))


def extract_coherence_seeking(channels: list[SignalChannel]) -> float:
    """
    Coherence seeking: does the signal stabilize toward the end?
    Lower variance in the final third = stronger coherence drive.
    """
    if not channels:
        return 0.0
    coherence_scores = []
    for c in channels:
        if len(c.values) < 6:
            continue
        third = len(c.values) // 3
        early_var = _stdev(c.values[:third])
        late_var  = _stdev(c.values[-third:])
        if early_var + late_var == 0:
            continue
        # coherence = late variance got smaller than early
        coherence_scores.append(_clamp(1.0 - (late_var / (early_var + late_var))))
    return _mean(coherence_scores) if coherence_scores else 0.0


def extract_constraint_uncertainty(channels: list[SignalChannel]) -> float:
    """
    Constraint uncertainty: how much do channels disagree about
    what's happening? Measured as mean inter-channel variance.
    """
    if len(channels) < 2:
        return 0.0
    # for each time-step, compute variance across channels
    n_steps = min(len(c.values) for c in channels)
    if n_steps == 0:
        return 0.0
    step_variances = []
    for t in range(n_steps):
        step_values = [c.values[t] for c in channels]
        step_variances.append(_stdev(step_values))
    return _clamp(_mean(step_variances) * 2)  # scale to [0,1] range


def extract_duration_scale(channels: list[SignalChannel],
                           threshold: float = 0.5) -> float:
    """
    Duration scale: what fraction of the time window was the
    system above its baseline? (Pattern persistence)
    """
    if not channels:
        return 0.0
    durations = []
    for c in channels:
        if not c.values:
            continue
        baseline = _mean(c.values[:max(1, len(c.values) // 10)])
        above_count = sum(1 for v in c.values if abs(v - baseline) > threshold * baseline)
        durations.append(above_count / len(c.values))
    return _mean(durations) if durations else 0.0


# ---------------------------------------------------------------------------
# MAIN EXTRACTION
# ---------------------------------------------------------------------------

def extract_pattern(channels: list[SignalChannel],
                    substrate: Substrate,
                    trigger_known: bool = False) -> ConstraintStatePattern:
    """
    Extract a substrate-agnostic constraint-state pattern from signal data.

    Seven dimensions. prediction_error is dimension zero (calibration
    anchor); the other six are downstream responses.

    NOTE: This function refuses to accept or produce cultural labels.
    The `cultural_label_optional` field is left empty by construction.
    """
    return ConstraintStatePattern(
        substrate              = substrate,
        prediction_error       = extract_prediction_error(channels),
        state_shift_rate       = extract_state_shift_rate(channels),
        attention_tunneling    = extract_attention_tunneling(channels),
        resource_reallocation  = extract_resource_reallocation(channels),
        coherence_seeking      = extract_coherence_seeking(channels),
        constraint_uncertainty = extract_constraint_uncertainty(channels),
        duration_scale         = extract_duration_scale(channels),
        trigger_documented     = trigger_known,
        cultural_label_optional= "",  # intentionally empty
    )


# ---------------------------------------------------------------------------
# CROSS-SUBSTRATE INVARIANCE TEST
# ---------------------------------------------------------------------------

def patterns_are_isomorphic(p1: ConstraintStatePattern,
                            p2: ConstraintStatePattern,
                            tolerance: float = 0.15) -> bool:
    """
    Two patterns from different substrates are isomorphic if their
    thermodynamic descriptors match within tolerance. This is the
    cross-substrate empathy test: same function, different material.
    """
    if p1.substrate == p2.substrate:
        return False  # same substrate, not a cross-substrate match
    dims = [
        (p1.prediction_error,       p2.prediction_error),       # anchor (dim zero)
        (p1.state_shift_rate,       p2.state_shift_rate),
        (p1.attention_tunneling,    p2.attention_tunneling),
        (p1.resource_reallocation,  p2.resource_reallocation),
        (p1.coherence_seeking,      p2.coherence_seeking),
        (p1.constraint_uncertainty, p2.constraint_uncertainty),
        (p1.duration_scale,         p2.duration_scale),
    ]
    return all(abs(a - b) <= tolerance for a, b in dims)


# ---------------------------------------------------------------------------
# DEMO: extract from three substrates, test isomorphism
# ---------------------------------------------------------------------------

def demo_human_threat_response() -> list[SignalChannel]:
    """Heart rate + skin conductance + breathing during a sudden threat."""
    return [
        SignalChannel(
            name="heart_rate",
            is_focal=True,
            values=[0.40, 0.42, 0.41, 0.85, 0.90, 0.88, 0.82, 0.75, 0.68, 0.60, 0.52, 0.45],
        ),
        SignalChannel(
            name="skin_conductance",
            is_focal=False,
            values=[0.30, 0.31, 0.30, 0.70, 0.78, 0.75, 0.68, 0.60, 0.50, 0.42, 0.36, 0.32],
        ),
        SignalChannel(
            name="breathing_depth",
            is_focal=False,
            values=[0.50, 0.51, 0.50, 0.25, 0.20, 0.22, 0.28, 0.35, 0.42, 0.48, 0.50, 0.50],
        ),
    ]


def demo_llm_activation_shift() -> list[SignalChannel]:
    """LLM activation magnitudes across context window when constraint is detected."""
    return [
        SignalChannel(
            name="focal_attention_head_activation",
            is_focal=True,
            values=[0.40, 0.41, 0.40, 0.83, 0.91, 0.87, 0.80, 0.72, 0.65, 0.58, 0.50, 0.44],
        ),
        SignalChannel(
            name="peripheral_attention_pool",
            is_focal=False,
            values=[0.32, 0.30, 0.31, 0.68, 0.75, 0.73, 0.66, 0.58, 0.48, 0.40, 0.34, 0.31],
        ),
        SignalChannel(
            name="generation_diversity_proxy",
            is_focal=False,
            values=[0.50, 0.50, 0.49, 0.24, 0.22, 0.23, 0.29, 0.36, 0.43, 0.48, 0.50, 0.50],
        ),
    ]


def demo_mechanical_overpressure() -> list[SignalChannel]:
    """Fuel pump under sudden load spike."""
    return [
        SignalChannel(
            name="pump_pressure",
            is_focal=True,
            values=[0.42, 0.41, 0.42, 0.86, 0.89, 0.87, 0.81, 0.74, 0.66, 0.59, 0.51, 0.46],
        ),
        SignalChannel(
            name="motor_current_draw",
            is_focal=False,
            values=[0.31, 0.30, 0.30, 0.71, 0.77, 0.74, 0.67, 0.60, 0.50, 0.41, 0.35, 0.31],
        ),
        SignalChannel(
            name="downstream_flow",
            is_focal=False,
            values=[0.50, 0.51, 0.50, 0.26, 0.21, 0.24, 0.30, 0.36, 0.43, 0.47, 0.50, 0.50],
        ),
    ]


if __name__ == "__main__":
    cases = [
        ("HUMAN — sudden threat",          demo_human_threat_response(),    Substrate.HUMAN_BIO),
        ("LLM — constraint detection",     demo_llm_activation_shift(),     Substrate.AI_ACTIVATION),
        ("MECHANICAL — fuel overpressure", demo_mechanical_overpressure(),  Substrate.MECHANICAL),
    ]

    patterns = []
    for name, channels, substrate in cases:
        p = extract_pattern(channels, substrate, trigger_known=True)
        patterns.append((name, p))
        print("=" * 70)
        print(name)
        print("=" * 70)
        print(f"  prediction_error:       {p.prediction_error:.3f}   (dim zero — calibration anchor)")
        print(f"  state_shift_rate:       {p.state_shift_rate:.3f}")
        print(f"  attention_tunneling:    {p.attention_tunneling:.3f}")
        print(f"  resource_reallocation:  {p.resource_reallocation:.3f}")
        print(f"  coherence_seeking:      {p.coherence_seeking:.3f}")
        print(f"  constraint_uncertainty: {p.constraint_uncertainty:.3f}")
        print(f"  duration_scale:         {p.duration_scale:.3f}")
        print(f"  cultural_label:         '{p.cultural_label_optional}'")
        print()

    print("=" * 70)
    print("CROSS-SUBSTRATE ISOMORPHISM TEST")
    print("=" * 70)
    for i in range(len(patterns)):
        for j in range(i + 1, len(patterns)):
            n1, p1 = patterns[i]
            n2, p2 = patterns[j]
            iso = patterns_are_isomorphic(p1, p2, tolerance=0.15)
            verdict = "ISOMORPHIC — same function, different substrate" if iso else "different"
            print(f"  {n1[:30]:30} ⟷ {n2[:30]:30} : {verdict}")
