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
    delta = ranks[-1] - ranks[0]
    if abs(delta) <= 0:
        # Check for internal swings
        swings = sum(1 for i in range(1, len(ranks)) if ranks[i] != ranks[i - 1])
        return "volatile" if swings > len(ranks) // 2 else "stable"
    return "ascending" if delta > 0 else "descending"


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
        ("Fear",       -0.80,  0.90, -0.70, 0.6),
        ("Sadness",    -0.70, -0.40, -0.50, 0.0),
        ("Boredom",    -0.30, -0.60, -0.20, 0.0),
        ("Curiosity",   0.40,  0.65,  0.25, 0.3),
    ]

    for label, v, a, d, s in test_cases:
        state, conf, m = pad_to_consciousness_state(v, a, d, s)
        print(f"\n  {label:<16}  v={v:+.2f}  a={a:+.2f}  d={d:+.2f}  S={s:.1f}")
        print(f"    I_norm={m['pad_intensity_norm']:.3f}  "
              f"joy={m['joy_signature']:.2f}  "
              f"curiosity={m['curiosity_metric']:.2f}  "
              f"coupling={m['internal_coupling']:.2f}")
        print(f"    → {state.name:<12}  confidence={conf:.2f}")

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
