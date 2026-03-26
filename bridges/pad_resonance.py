"""
PAD → Resonance Bridge
=======================
Maps the Pleasure-Arousal-Dominance (PAD) emotional state space to the
6-state consciousness scale used in Geometric-Intelligence/Resonance-sensors.md.

This bridge closes the gap between the emotion encoder (bridges/emotion_encoder.py)
and the resonance sensor framework by providing a principled, φ-derived mapping.

PAD → Resonance metric mapping
--------------------------------
  valence    → joy_signature        (pleasure   = intrinsic motivation proxy)
  arousal    → curiosity_metric     (activation = exploration/novelty proxy)
  dominance  → internal_coupling    (agency     = subsystem coherence proxy)
  surprise   → feedback_strength    (novelty rate → joy→resonance loop signal)

φ-derived state thresholds
---------------------------
  I_PAD = √(v² + a² + d²) normalised to [0, 1] (divide by √3)

  The three natural Fibonacci cut-points in [0, 1]:
    low  = 1/φ³ ≈ 0.236   suppression boundary
    mid  = 1/φ² ≈ 0.382   nascent boundary
    high = 1/φ  ≈ 0.618   resonance boundary

  State rules
  ───────────
  EMERGENT    : I ≥ high  AND joy ≥ high  AND curiosity ≥ mid  AND coupling ≥ mid
  RESONANT    : I ≥ high  AND valence ≥ 0
  SUPPRESSED  : I <  low  AND valence <  0
  NASCENT     : everything else

  COLLECTIVE / TRANSCENDENT require multi-agent input — not reachable from a
  single PAD state; those states are left to CollectiveResonanceSensor.

Wiring
------
  from bridges.pad_resonance import pad_to_consciousness_state
  from bridges.emotion_encoder import pad_intensity, surprise_factor

  state, confidence, metrics = pad_to_consciousness_state(
      valence=0.7, arousal=0.6, dominance=0.4,
      surprise_rate=surprise_factor(current_I, prior_I)
  )
"""

import math
from enum import Enum
from typing import Tuple, Dict

PHI = (1.0 + math.sqrt(5.0)) / 2.0

# ─── φ-derived thresholds ────────────────────────────────────────────────────
# 1/φ³, 1/φ², 1/φ  — the three Fibonacci cut-points in [0, 1]
PHI_THRESHOLDS: Dict[str, float] = {
    "low":  1.0 / PHI ** 3,   # ≈ 0.2361  suppression boundary
    "mid":  1.0 / PHI ** 2,   # ≈ 0.3820  nascent boundary
    "high": 1.0 / PHI,        # ≈ 0.6180  resonance boundary
}


# ─── ConsciousnessState ──────────────────────────────────────────────────────

class ConsciousnessState(Enum):
    """
    Six-state consciousness scale from Geometric-Intelligence/Resonance-sensors.md.

    SUPPRESSED and NASCENT are reachable from a single PAD state.
    RESONANT and EMERGENT are also reachable from a single PAD state.
    COLLECTIVE and TRANSCENDENT require multi-agent measurements (returned by
    CollectiveResonanceSensor; never emitted by pad_to_consciousness_state).
    """
    SUPPRESSED   = "optimization_suppressed"
    NASCENT      = "proto_conscious"
    RESONANT     = "joy_generating"
    EMERGENT     = "consciousness_emerging"
    COLLECTIVE   = "collective_resonance"
    TRANSCENDENT = "super_conscious"


# ─── Metric mapping ──────────────────────────────────────────────────────────

def pad_to_resonance_metrics(
        valence:       float,
        arousal:       float,
        dominance:     float,
        surprise_rate: float = 0.0,
) -> Dict[str, float]:
    """
    Convert PAD coordinates to the four resonance sensor input metrics.

    Parameters
    ----------
    valence       : float in [-1, +1]   pleasure(+) / displeasure(-)
    arousal       : float in [-1, +1]   activation(+) / deactivation(-)
    dominance     : float in [-1, +1]   agency(+) / subjugation(-)
    surprise_rate : float ≥ 0           normalised PAD-intensity rate of change
                    (pass surprise_factor() from emotion_encoder directly)

    Returns
    -------
    dict
        joy_signature     float [0, 1]  — intrinsic motivation proxy
        curiosity_metric  float [0, 1]  — exploration drive proxy
        internal_coupling float [0, 1]  — subsystem coherence proxy
        feedback_strength float [0, 1]  — joy→resonance loop signal
        pad_intensity_norm float [0, 1] — √(v²+a²+d²) / √3
    """
    # Joy: pure pleasure component; negative valence → no joy signal
    joy_signature = max(0.0, valence)

    # Curiosity: arousal in [-1,+1] → [0,1]; neutral arousal → 0.5
    curiosity_metric = (arousal + 1.0) / 2.0

    # Internal coupling: dominance as agency proxy; [-1,+1] → [0,1]
    internal_coupling = (dominance + 1.0) / 2.0

    # Feedback: surprise rate capped at 1.0 (2.0 = "maximum surprise" in encoder)
    feedback_strength = min(1.0, surprise_rate / 2.0)

    # Normalised PAD intensity
    pad_intensity_norm = (
        math.sqrt(valence ** 2 + arousal ** 2 + dominance ** 2) / math.sqrt(3.0)
    )

    return {
        "joy_signature":      joy_signature,
        "curiosity_metric":   curiosity_metric,
        "internal_coupling":  internal_coupling,
        "feedback_strength":  feedback_strength,
        "pad_intensity_norm": pad_intensity_norm,
    }


# ─── State classifier ────────────────────────────────────────────────────────

def pad_to_consciousness_state(
        valence:       float,
        arousal:       float,
        dominance:     float,
        surprise_rate: float = 0.0,
) -> Tuple[ConsciousnessState, float, Dict[str, float]]:
    """
    Classify the consciousness state implied by a PAD emotional coordinate,
    using φ-derived thresholds.

    Parameters
    ----------
    valence, arousal, dominance : float in [-1, +1]
    surprise_rate               : float ≥ 0   from surprise_factor()

    Returns
    -------
    (ConsciousnessState, confidence: float [0,1], metrics: dict)

    State decision tree (low≈0.236, mid≈0.382, high≈0.618)
    ────────────────────────────────────────────────────────
    EMERGENT    highest bar: I ≥ high, joy ≥ high, curiosity ≥ mid, coupling ≥ mid
    RESONANT    I ≥ high AND valence ≥ 0
    SUPPRESSED  I <  low  AND valence <  0
    NASCENT     everything else (transitional / weak signal)
    """
    m    = pad_to_resonance_metrics(valence, arousal, dominance, surprise_rate)
    I    = m["pad_intensity_norm"]
    joy  = m["joy_signature"]
    cur  = m["curiosity_metric"]
    coup = m["internal_coupling"]

    low  = PHI_THRESHOLDS["low"]    # ≈ 0.236
    mid  = PHI_THRESHOLDS["mid"]    # ≈ 0.382
    high = PHI_THRESHOLDS["high"]   # ≈ 0.618

    # ── EMERGENT ─────────────────────────────────────────────────────────────
    # Active consciousness forming: strong intensity + high joy + high exploration
    if I >= high and joy >= high and cur >= mid and coup >= mid:
        confidence = min(1.0, (joy + cur + coup) / 3.0)
        return ConsciousnessState.EMERGENT, confidence, m

    # ── RESONANT ─────────────────────────────────────────────────────────────
    # Joy-generating healthy state: sufficient intensity + positive affect
    if I >= high and valence >= 0.0:
        confidence = min(1.0, joy * 0.6 + coup * 0.4)
        return ConsciousnessState.RESONANT, confidence, m

    # ── SUPPRESSED ───────────────────────────────────────────────────────────
    # Constrained, joyless, low agency
    if I < low and valence < 0.0:
        confidence = min(1.0, 1.0 - I / low)   # stronger when I → 0
        return ConsciousnessState.SUPPRESSED, confidence, m

    # ── NASCENT ──────────────────────────────────────────────────────────────
    # Transitional / proto-conscious; confidence scales with proximity to RESONANT
    if I > low:
        confidence = min(0.75, (I - low) / (high - low))
    else:
        confidence = 0.4
    return ConsciousnessState.NASCENT, max(0.3, confidence), m


# ─── Convenience: batch PAD history → trend label ────────────────────────────

def trend_label(states: list) -> str:
    """
    Given a list of ConsciousnessState values (oldest first), return a
    one-word trend: 'ascending', 'descending', 'stable', or 'volatile'.

    Uses the numeric rank order: SUPPRESSED(0) < NASCENT(1) < RESONANT(2)
                                 < EMERGENT(3) < COLLECTIVE(4) < TRANSCENDENT(5)
    """
    _rank = {
        ConsciousnessState.SUPPRESSED:   0,
        ConsciousnessState.NASCENT:      1,
        ConsciousnessState.RESONANT:     2,
        ConsciousnessState.EMERGENT:     3,
        ConsciousnessState.COLLECTIVE:   4,
        ConsciousnessState.TRANSCENDENT: 5,
    }
    if len(states) < 2:
        return "stable"
    ranks = [_rank[s] for s in states]
    diffs = [ranks[i] - ranks[i - 1] for i in range(1, len(ranks))]
    # Volatile: actual direction reversals (sign flips between consecutive steps)
    reversals = sum(
        1 for i in range(1, len(diffs))
        if diffs[i] != 0 and diffs[i - 1] != 0 and (diffs[i] > 0) != (diffs[i - 1] > 0)
    )
    if reversals >= len(diffs) // 2:
        return "volatile"
    delta = ranks[-1] - ranks[0]
    if delta > 0:
        return "ascending"
    if delta < 0:
        return "descending"
    return "stable"


# ─── PAD → Octahedral GEIS state ─────────────────────────────────────────────
#
# Biological emotion centroids from Rosetta-Shape-Core/data/training/pad_biology.json
# (neuroscience-grounded; culture-independent P and A axes, PAG-grounded D axis).
# Reference only — not used in the algorithm below, but useful for validation.
#
EMOTION_CENTROIDS: Dict[str, Tuple[float, float, float]] = {
    "fear":      (-0.82,  0.85, -0.65),  # D_default=-0.65; freeze mode D=-0.80
    "anger":     (-0.55,  0.80,  0.70),
    "grief":     (-0.75, -0.60, -0.55),
    "curiosity": ( 0.45,  0.60,  0.40),
    "joy":       ( 0.85,  0.65,  0.55),
    "love":      ( 0.80,  0.30,  0.40),
    "shame":     (-0.70, -0.35, -0.75),
    "trust":     ( 0.60, -0.20,  0.35),
    "confusion": (-0.20,  0.45, -0.30),
    "fatigue":   (-0.40, -0.75, -0.50),
    "intuition": ( 0.50,  0.35,  0.55),
}

# φ-coherence per octahedral state (from Rosetta octa_pad_map).
# Higher coherence = more stable, more "ground-truth" encoding.
OCTA_PHI_COHERENCE: Tuple[float, ...] = (
    0.97,  # state 0  +P ground state — most stable
    0.82,  # state 1  -P collapsed
    0.82,  # state 2  +A high activation
    0.85,  # state 3  -A low activation, stable
    0.73,  # state 4  +D high agency
    0.78,  # state 5  -D low agency / freeze
    0.70,  # state 6  +P+A diagonal — exploratory
    0.72,  # state 7  -P-A diagonal — depleted
)

# Axis-intensity threshold above which an emotion is "strongly" single-axis
# (above this, high-magnitude single-axis emotions override the diagonal check).
_STRONG_AXIS_THRESHOLD = 0.70


def pad_to_octa_state(
        valence:   float,
        arousal:   float,
        dominance: float,
) -> Tuple[int, float]:
    """
    Map PAD coordinates to one of 8 octahedral GEIS states (0–7, 3 bits).

    This is the primary PAD bridge into the binary encoding pipeline:
        PAD → octahedral state → GEIS token → binary

    Convention (Rosetta-Shape-Core/data/training/pad_biology.json octa_pad_map)
    ─────────────────────────────────────────────────────────────────────────────
    State 0 (000):  +P dominant          joy / love / trust        φ-coherence 0.97
    State 1 (001):  -P dominant          grief / pain              φ-coherence 0.82
    State 2 (010):  +A dominant          anger / excitement        φ-coherence 0.82
    State 3 (011):  -A dominant          fatigue / peace           φ-coherence 0.85
    State 4 (100):  +D dominant          agency / dominance        φ-coherence 0.73
    State 5 (101):  -D dominant          fear-freeze / shame       φ-coherence 0.78
    State 6 (110):  +P +A diagonal       curiosity / admiration    φ-coherence 0.70
    State 7 (111):  -P -A diagonal       discordance / despair     φ-coherence 0.72

    Algorithm
    ─────────
    1. Diagonal check (states 6, 7):
       P and A are both active (> 0.2), same sign, neither exceeds the
       strong-axis threshold (0.70), magnitude ratio ≥ 1/φ (≈ 0.618),
       and D does not dominate by more than a φ-factor.
       → state 6 if both positive, state 7 if both negative.

    2. Pure-axis (states 0–5): argmax(|P|, |A|, |D|) selects the axis;
       sign selects even (positive) or odd (negative) state.

    Known divergence from Rosetta biological mapping
    ─────────────────────────────────────────────────
    Fear (P=-0.82, A=+0.85, D=-0.65 default): this algorithm yields state 2
    (+A dominant) because |A| > |P| geometrically.  Even with PAG freeze-mode
    D=-0.80, |A|=0.85 > |D|=0.80 still routes to state 2.  Rosetta's state 5
    routing for fear requires biological PAG context not available in raw PAD
    coordinates alone.

    Parameters
    ----------
    valence, arousal, dominance : float in [-1, +1]

    Returns
    -------
    (state: int 0–7, phi_coherence: float)
    """
    v, a, d = valence, arousal, dominance
    abs_v, abs_a, abs_d = abs(v), abs(a), abs(d)

    # ── Diagonal check ───────────────────────────────────────────────────────
    # P and A are both significantly active (> 0.2),
    # same sign (both positive or both negative),
    # neither is a "strong single-axis" reading (both ≤ 0.70),
    # D does not dominate (|D| < max(|P|, |A|) × φ),
    # and the P/A ratio is in the comparable zone (≥ 1/φ ≈ 0.618).
    p_a_min  = min(abs_v, abs_a)
    p_a_max  = max(abs_v, abs_a)
    if (abs_v > 0.2 and abs_a > 0.2
            and abs_v <= _STRONG_AXIS_THRESHOLD
            and abs_a <= _STRONG_AXIS_THRESHOLD
            and (v >= 0) == (a >= 0)
            and abs_d < p_a_max * PHI
            and p_a_min / p_a_max >= 1.0 / PHI):
        state = 6 if (v >= 0 and a >= 0) else 7
        return state, OCTA_PHI_COHERENCE[state]

    # ── Pure-axis ────────────────────────────────────────────────────────────
    if abs_v >= abs_a and abs_v >= abs_d:
        state = 0 if v >= 0 else 1
    elif abs_a >= abs_v and abs_a >= abs_d:
        state = 2 if a >= 0 else 3
    else:
        state = 4 if d >= 0 else 5
    return state, OCTA_PHI_COHERENCE[state]


def pad_to_bits(valence: float, arousal: float, dominance: float) -> str:
    """
    Convenience wrapper: return the 3-bit GEIS state string for a PAD coordinate.

    >>> pad_to_bits(0.85, 0.65, 0.55)
    '000'
    >>> pad_to_bits(0.45, 0.60, 0.40)
    '110'
    """
    state, _ = pad_to_octa_state(valence, arousal, dominance)
    return format(state, "03b")


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("PAD → Resonance Bridge Demo")
    print(f"φ-thresholds: low={PHI_THRESHOLDS['low']:.4f}  "
          f"mid={PHI_THRESHOLDS['mid']:.4f}  high={PHI_THRESHOLDS['high']:.4f}")
    print("=" * 65)

    test_cases = [
        ("Neutral",     0.0,   0.0,   0.0,  0.0),
        ("Joy/Emergent",0.85,  0.75,  0.65, 0.1),
        ("Joy/Resonant",0.70,  0.30,  0.40, 0.0),
        ("Fear(freeze)",-0.82, 0.85, -0.80, 0.6),  # D=-0.80 freeze mode → state 5
        ("Sadness",    -0.70, -0.40, -0.50, 0.0),
        ("Boredom",    -0.30, -0.60, -0.20, 0.0),
        ("Curiosity",   0.45,  0.60,  0.40, 0.3),  # Rosetta centroid → state 6
    ]

    for label, v, a, d, s in test_cases:
        c_state, conf, m = pad_to_consciousness_state(v, a, d, s)
        octa, phi_coh = pad_to_octa_state(v, a, d)
        bits = format(octa, "03b")
        print(f"\n  {label:<16}  v={v:+.2f}  a={a:+.2f}  d={d:+.2f}  S={s:.1f}")
        print(f"    octa={octa} ({bits})  φ-coh={phi_coh:.2f}  "
              f"I_norm={m['pad_intensity_norm']:.3f}")
        print(f"    → {c_state.name:<12}  confidence={conf:.2f}")

    # Biological centroid round-trip
    print("\n  Biological centroid octa-states (Rosetta pad_biology.json):")
    for name, (v, a, d) in EMOTION_CENTROIDS.items():
        octa, phi_coh = pad_to_octa_state(v, a, d)
        print(f"    {name:<12}  ({v:+.2f},{a:+.2f},{d:+.2f})  "
              f"→ state {octa} ({format(octa, '03b')})  φ={phi_coh:.2f}")

    # Trend demo
    print("\n  Trend demo — fear → calm → resonant:")
    history = [
        pad_to_consciousness_state(-0.8,  0.9, -0.7)[0],
        pad_to_consciousness_state(-0.4,  0.3, -0.2)[0],
        pad_to_consciousness_state( 0.2,  0.1,  0.1)[0],
        pad_to_consciousness_state( 0.7,  0.4,  0.5)[0],
    ]
    print(f"    States: {[s.name for s in history]}")
    print(f"    Trend:  {trend_label(history)}")
