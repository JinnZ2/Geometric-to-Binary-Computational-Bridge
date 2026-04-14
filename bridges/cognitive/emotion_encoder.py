"""
Emotion Bridge Encoder
=======================
Macro-scale compression overlay.  Reads signals across all physical bridges
and the consciousness bridge, classifies the current emotional state using
the PAD (Pleasure-Arousal-Dominance) model, and — critically — when a
significant emotional signal is detected, emits a **causality drill-target**
pointing back to the specific physical bridge that is the causal source.

Architecture position
---------------------
  Physical bridges (thermal, pressure, chemical, …)
    └→  Consciousness bridge  (internal state → confidence, entropy)
          └→  Emotion bridge   (macro compression → PAD state + drill target)
                └→  if emotion detected → drill into causal bridge

The emotion bridge does NOT process everything at full resolution.
It is a fast macro-evaluator: if the emotional signal is below threshold,
it returns a low-cost compressed summary.  When threshold is exceeded it
returns the drill-target so the full-resolution bridge can be re-evaluated.

Equations implemented
---------------------
  PAD intensity    :  I_PAD = √(v² + a² + d²)       (Euclidean distance from neutral)
  Valence-arousal coherence:
    C_VA = 1 − |ρ_expected(v,a) − ρ_actual|         (Russell circumplex consistency)
  Surprise factor  :  S = |ΔI_PAD| / Δt             (rate of change of emotional state)
  Cross-bridge resonance:
    R = 1 − JSD(bridge_signal ‖ consciousness)        (Jensen-Shannon similarity)
  Drill-target selection:
    bridge* = argmax_b [ I_F(b) ]                     (Fisher information per bridge)

Bit layout (39 bits for canonical 3 PAD dimensions + 2 triggers input)
------------------------------------------------------------------------
Per PAD dimension  (8 bits each — valence, arousal, dominance):
  [positive    1b]       value > 0 = 1
  [mag_band    3b Gray]  |value| across 8 linear bands [0, 1]
  [coherent    1b]       dimension is internally consistent = 1
  [coher_band  3b Gray]  coherence score across 8 linear bands [0, 1]

Per trigger signal  (4 bits each):
  [triggered   1b]       signal exceeds trigger threshold = 1
  [bridge_id   3b Gray]  which bridge triggered (0–7 Gray → none/physical/conscious)

Summary  (7 bits — appended when any section present):
  [drill_now   1b]       overall emotional intensity > drill_threshold = 1
  [priority    3b Gray]  drill urgency across 8 bands [0, 1]
  [causal_id   3b Gray]  causal bridge identifier (0=none, 1–8=bridge index)

Bridge index map (causal_id)
  0 = none         1 = magnetic   2 = light      3 = sound
  4 = gravity      5 = electric   6 = wave       7 = thermal
  8 = pressure     (chemical and consciousness map to higher, encoded mod 8)
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits
from bridges.cognitive.consciousness_encoder import mutual_information, fisher_information

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_MAG_BANDS    = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]   # [0, 1]
_COHER_BANDS  = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]   # [0, 1]
_PRIO_BANDS   = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]   # [0, 1]
_BRIDGE_IDS   = list(range(9))  # 0=none, 1-8 = physical bridges

# Russell circumplex: expected correlation sign between valence and arousal
# for coherent emotional states — positive valence / high arousal = joy (coherent)
# negative valence / high arousal = fear/anger (coherent)
# high valence / low arousal = calm/contentment (coherent)
_RUSSELL_COHERENT_PAIRS = [
    (1, 1),   # positive valence + high arousal  → joy / excitement
    (-1, 1),  # negative valence + high arousal  → fear / anger
    (1, -1),  # positive valence + low arousal   → calm / contentment
    (-1, -1), # negative valence + low arousal   → sadness / boredom
]


# ---------------------------------------------------------------------------
# Emotion equations (pure, importable)
# ---------------------------------------------------------------------------

def pad_intensity(valence: float, arousal: float, dominance: float) -> float:
    """
    I_PAD = √(v² + a² + d²)  — Euclidean distance from neutral in PAD space.

    All three dimensions in [−1, +1].  Maximum I_PAD = √3 ≈ 1.732.
    Returns 0 at the neutral point (v=a=d=0).
    """
    return math.sqrt(valence**2 + arousal**2 + dominance**2)


def valence_arousal_coherence(valence: float, arousal: float) -> float:
    """
    Consistency of (valence, arousal) with the Russell circumplex model.

    The circumplex predicts that any emotion lies in a smooth 2D ring.
    Coherence = 1 − deviation from the ring; the ring radius is normalised to 1.

    C_VA = 1 − |√(v² + a²) − 1|

    Returns 1.0 when the state sits exactly on the unit circle (a pure emotion),
    returns 0.0 when it is at the origin (flat/neutral) or outside radius 2.
    Clamped to [0, 1].
    """
    radius = math.sqrt(valence**2 + arousal**2)
    return max(0.0, 1.0 - abs(radius - 1.0))


def surprise_factor(current_intensity: float, prior_intensity: float,
                    delta_t: float = 1.0) -> float:
    """
    S = |ΔI_PAD| / Δt  — rate of change of emotional intensity.

    Large S means the emotional state shifted quickly → high surprise / novelty.
    delta_t is dimensionless (relative time units); defaults to 1 step.
    Returns 0 if delta_t = 0.
    """
    if delta_t <= 0.0:
        return 0.0
    return abs(current_intensity - prior_intensity) / delta_t


def cross_bridge_resonance(bridge_signal_probs: list,
                            consciousness_probs: list) -> float:
    """
    R = 1 − JSD(bridge ‖ consciousness)  — Jensen-Shannon similarity.

    Measures how well a physical bridge signal aligns with the current
    consciousness state distribution.  Unlike mutual information this only
    requires the two marginal distributions, not a joint.

    JSD(P‖Q) = (KL(P‖M) + KL(Q‖M)) / 2   where M = (P + Q) / 2
    R = 1 − JSD  →  R = 1 when identical, R ≈ 0 when maximally different.

    High resonance → physical bridge is coupled to internal state → likely causal source.
    """
    n = max(len(bridge_signal_probs), len(consciousness_probs))
    eps = 1e-9
    b = list(bridge_signal_probs) + [eps] * (n - len(bridge_signal_probs))
    c = list(consciousness_probs)  + [eps] * (n - len(consciousness_probs))
    sb = sum(b) or 1.0
    sc = sum(c) or 1.0
    b = [x / sb for x in b]
    c = [x / sc for x in c]
    m = [(b[i] + c[i]) / 2.0 for i in range(n)]
    # KL(P‖M)
    kl_pm = sum(b[i] * math.log2(b[i] / m[i]) for i in range(n) if b[i] > 0 and m[i] > 0)
    # KL(Q‖M)
    kl_qm = sum(c[i] * math.log2(c[i] / m[i]) for i in range(n) if c[i] > 0 and m[i] > 0)
    jsd = (kl_pm + kl_qm) / 2.0
    return max(0.0, 1.0 - jsd)


def drill_target(bridge_gradients: dict) -> str:
    """
    Select the bridge with the highest Fisher information — the sharpest signal.

    bridge_gradients : dict mapping bridge_name (str) → list of log-likelihood
                       gradients (floats) for that bridge's recent readings.

    Returns the name of the bridge with the highest I_F, or "none" if the
    dict is empty.  This is the recommended drill-down target.
    """
    if not bridge_gradients:
        return "none"
    scores = {name: fisher_information(grads)
              for name, grads in bridge_gradients.items() if grads}
    if not scores:
        return "none"
    return max(scores, key=scores.__getitem__)


# ---------------------------------------------------------------------------
# Bridge name → causal_id mapping
# ---------------------------------------------------------------------------
_BRIDGE_NAME_TO_ID = {
    "none":          0,
    "magnetic":      1,
    "light":         2,
    "sound":         3,
    "gravity":       4,
    "electric":      5,
    "wave":          6,
    "thermal":       7,
    "pressure":      8,
    "chemical":      1,   # wraps (chemical=9 mod 8 = 1, distinguished by context)
    "consciousness": 2,
}


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class EmotionBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes macro emotional state + causality drill-target into binary.

    Input geometry dict keys
    ------------------------
    valence           : float in [−1, +1]  — pleasant (+) / unpleasant (−)
    arousal           : float in [−1, +1]  — activated (+) / deactivated (−)
    dominance         : float in [−1, +1]  — in control (+) / controlled (−)
    prior_intensity   : float ≥ 0          — PAD intensity at previous timestep
    delta_t           : float > 0          — time units since prior_intensity
    trigger_signals   : list of dicts with keys:
                          bridge_name : str  — which bridge raised this trigger
                          intensity   : float in [0, 1]
    bridge_gradients  : dict bridge_name → list of log-likelihood gradients
                        (used to select the drill-down target)

    Threshold parameters (constructor)
    -----------------------------------
    drill_threshold   : float — PAD intensity above which drill_now=1 (default 0.5)
    trigger_threshold : float — signal intensity above which triggered=1 (default 0.3)
    """

    def __init__(self, drill_threshold: float = 0.5,
                 trigger_threshold: float = 0.3):
        super().__init__("emotion")
        self.drill_threshold   = drill_threshold
        self.trigger_threshold = trigger_threshold

    def from_geometry(self, geometry_data: dict):
        """Load emotional state geometry dict."""
        self.input_geometry = geometry_data
        return self

    # ------------------------------------------------------------------
    # SensorSuite integration
    # ------------------------------------------------------------------

    def to_suite(self, suite):
        """
        Map loaded PAD geometry into SensorSuite readings and run the
        compositor.

        Translates the three PAD dimensions plus derived scalars
        (PAD intensity, valence-arousal coherence, surprise factor) into
        per-sensor magnitude readings on the supplied SensorSuite, then
        returns the compositor's CompositeOutput.

        Only the 15 PAD-relevant sensors are written; all others retain
        whatever state the caller has previously set.  Sensors with a
        derived magnitude of 0 are reset to quiescent so stale readings
        do not bleed into the compositor pass.

        Parameters
        ----------
        suite : SensorSuite
            A live SensorSuite instance.  Its state is modified in-place.

        Returns
        -------
        CompositeOutput
            Result of suite.compose() after applying PAD-derived readings.

        Raises
        ------
        ValueError
            If from_geometry() has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_suite()."
            )

        data       = self.input_geometry
        v          = data.get("valence",          0.0)
        a          = data.get("arousal",          0.0)
        d          = data.get("dominance",        0.0)
        prior_I    = data.get("prior_intensity",  0.0)
        dt         = data.get("delta_t",          1.0)
        bridge_grads = data.get("bridge_gradients", {})

        # Derived scalars
        I      = pad_intensity(v, a, d)
        norm_I = I / math.sqrt(3.0)
        C_VA   = valence_arousal_coherence(v, a)
        S      = surprise_factor(I, prior_I, dt)
        norm_S = min(S / 2.0, 1.0)

        # Reset the 15 PAD-driven channels before re-mapping so previous
        # calls don't bleed forward.
        _PAD_CHANNELS = (
            "coherence", "discordance", "fear", "anger", "grief", "pain",
            "love", "trust", "pride", "shame", "dignity", "vigilance",
            "curiosity", "pressure", "confusion",
        )
        for sid in _PAD_CHANNELS:
            suite.reset(sid)

        def _m(value: float, floor: float = 0.0) -> float:
            """Clamp value to [0, 1]; return 0 if below floor."""
            clamped = max(0.0, min(1.0, value))
            return clamped if clamped > floor else 0.0

        # Coherence: calm positive affect (v > 0, low |a|)
        if v > 0:
            suite.update("coherence",
                         signal_vector=[v, -abs(a)],
                         magnitude=_m(v * (1.0 - abs(a))))

        # Discordance: circumplex incoherence when state is non-trivial
        if norm_I > 0.1:
            suite.update("discordance",
                         signal_vector=[1.0 - C_VA],
                         magnitude=_m(1.0 - C_VA, floor=0.2))

        # Fear: negative valence + high arousal
        if v < 0 and a > 0:
            suite.update("fear",
                         signal_vector=[abs(v), a],
                         magnitude=_m((abs(v) + a) / 2.0))

        # Anger: negative valence + high arousal + positive dominance
        if v < 0 and a > 0 and d > 0:
            suite.update("anger",
                         signal_vector=[abs(v), a, d],
                         magnitude=_m(abs(v) * a))

        # Grief: negative valence + low arousal
        if v < 0 and a < 0:
            suite.update("grief",
                         signal_vector=[abs(v), abs(a)],
                         magnitude=_m((abs(v) + abs(a)) / 2.0))

        # Pain: high negative affect regardless of arousal
        if v < 0 and norm_I > 0.3:
            suite.update("pain",
                         signal_vector=[abs(v)],
                         magnitude=_m(abs(v)))

        # Love: positive valence + low or negative arousal
        if v > 0 and a <= 0:
            suite.update("love",
                         signal_vector=[v, abs(d)],
                         magnitude=_m(v))

        # Trust: coherent positive valence (circumplex-consistent)
        if v > 0 and C_VA > 0.5:
            suite.update("trust",
                         signal_vector=[v, C_VA],
                         magnitude=_m(v * C_VA))

        # Pride: positive valence + high arousal + positive dominance
        if v > 0 and a > 0 and d > 0:
            suite.update("pride",
                         signal_vector=[v, a, d],
                         magnitude=_m((v + a + d) / 3.0))

        # Shame: negative valence + negative dominance
        if v < 0 and d < 0:
            suite.update("shame",
                         signal_vector=[abs(v), abs(d)],
                         magnitude=_m((abs(v) + abs(d)) / 2.0))

        # Dignity: positive dominance regardless of valence
        if d > 0:
            suite.update("dignity",
                         signal_vector=[d],
                         magnitude=_m(d))

        # Vigilance: high absolute arousal
        if abs(a) > 0.3:
            suite.update("vigilance",
                         signal_vector=[abs(a)],
                         magnitude=_m(abs(a)))

        # Curiosity: rapid surprise (state changed quickly)
        if norm_S > 0.15:
            suite.update("curiosity",
                         signal_vector=[norm_S],
                         magnitude=_m(norm_S))

        # Pressure: high overall PAD intensity
        if norm_I > 0.5:
            suite.update("pressure",
                         signal_vector=[norm_I],
                         magnitude=_m(norm_I))

        # Confusion: low circumplex coherence when state is active
        if C_VA < 0.4 and norm_I > 0.2:
            suite.update("confusion",
                         signal_vector=[1.0 - C_VA],
                         magnitude=_m(1.0 - C_VA))

        return suite.compose()

    # ------------------------------------------------------------------

    def to_binary(self) -> str:
        """
        Convert loaded emotional state into a binary bitstring.

        Returns
        -------
        str
            A string of ``"0"`` and ``"1"`` characters.

        Raises
        ------
        ValueError
            If ``from_geometry`` has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        data            = self.input_geometry
        valence         = data.get("valence",   0.0)
        arousal         = data.get("arousal",   0.0)
        dominance       = data.get("dominance", 0.0)
        prior_int       = data.get("prior_intensity", 0.0)
        delta_t         = data.get("delta_t", 1.0)
        trigger_signals = data.get("trigger_signals", [])
        bridge_grads    = data.get("bridge_gradients", {})
        bits            = []
        any_section     = False

        # ------------------------------------------------------------------
        # Precompute coherence scores for each PAD dimension
        # ------------------------------------------------------------------
        # Valence coherence: how well |valence| sits near 1.0 (strong pure emotion)
        val_coherence = max(0.0, 1.0 - abs(abs(valence) - 0.75))   # peaks at |v|=0.75
        # Arousal-valence circumplex coherence
        va_coherence  = valence_arousal_coherence(valence, arousal)
        # Dominance coherence: how stable/expected given arousal level
        dom_coherence = max(0.0, 1.0 - abs(abs(dominance) - abs(arousal)))

        # ------------------------------------------------------------------
        # Section 1: three PAD dimensions  →  8 bits each
        #   [positive 1b][mag_band 3b Gray][coherent 1b][coher_band 3b Gray]
        # ------------------------------------------------------------------
        for dim_val, dim_coher in [(valence, val_coherence),
                                    (arousal, va_coherence),
                                    (dominance, dom_coherence)]:
            any_section = True
            positive   = "1" if dim_val > 0.0 else "0"
            mag_band   = _gray_bits(abs(dim_val), _MAG_BANDS)
            coherent   = "1" if dim_coher > 0.5 else "0"
            coher_band = _gray_bits(dim_coher, _COHER_BANDS)

            bits.append(positive)
            bits.append(mag_band)
            bits.append(coherent)
            bits.append(coher_band)

        # ------------------------------------------------------------------
        # Section 2: trigger signals  →  4 bits each
        #   [triggered 1b][bridge_id 3b Gray]
        # ------------------------------------------------------------------
        for sig in trigger_signals:
            any_section = True
            intensity   = sig.get("intensity", 0.0)
            bridge_name = sig.get("bridge_name", "none")
            triggered   = "1" if intensity > self.trigger_threshold else "0"
            bid         = _BRIDGE_NAME_TO_ID.get(bridge_name, 0)
            bridge_id   = _gray_bits(bid, list(range(9)))
            bits.append(triggered)
            bits.append(bridge_id)

        # ------------------------------------------------------------------
        # Summary  (7 bits)
        # ------------------------------------------------------------------
        if any_section:
            # Overall PAD intensity
            intensity = pad_intensity(valence, arousal, dominance)
            # Normalise to [0, 1] (max √3 ≈ 1.732)
            norm_intensity = intensity / math.sqrt(3.0)
            drill_now  = "1" if norm_intensity > self.drill_threshold else "0"

            # Surprise factor (rate of intensity change)
            S = surprise_factor(intensity, prior_int, delta_t)
            # Normalise S to [0, 1] — cap at 2.0 as "maximum surprise"
            norm_S = min(S / 2.0, 1.0)

            # Drill-target bridge
            target_name = drill_target(bridge_grads)
            causal_id   = _BRIDGE_NAME_TO_ID.get(target_name, 0)

            bits.append(drill_now)
            bits.append(_gray_bits(norm_S, _PRIO_BANDS))
            bits.append(_gray_bits(causal_id, list(range(9))))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Emotion Bridge Encoder — Macro Compression Demo")
    print("=" * 60)

    # 1. PAD intensity across the emotional spectrum
    print("\n1. PAD intensity  I = √(v² + a² + d²)")
    emotions = [
        ("Neutral     (0,  0,  0)",    0.0,  0.0,  0.0),
        ("Joy         (0.9, 0.7, 0.6)",0.9,  0.7,  0.6),
        ("Fear        (-0.8, 0.9, -0.7)",-0.8, 0.9, -0.7),
        ("Sadness     (-0.7, -0.4, -0.5)",-0.7,-0.4,-0.5),
        ("Calm        (0.5, -0.5, 0.3)", 0.5,-0.5,  0.3),
        ("Curiosity   (0.4, 0.6, 0.2)",  0.4, 0.6,  0.2),
    ]
    for label, v, a, d in emotions:
        I = pad_intensity(v, a, d)
        print(f"   {label:42s}  I_PAD = {I:.4f}")

    # 2. Valence-arousal circumplex coherence
    print("\n2. Valence-arousal coherence  C = 1 − |√(v²+a²) − 1|")
    for label, v, a, _ in emotions:
        C = valence_arousal_coherence(v, a)
        print(f"   {label:42s}  C_VA = {C:.4f}")

    # 3. Surprise factor
    print("\n3. Surprise factor  S = |ΔI| / Δt")
    seq = [0.05, 0.1, 0.12, 0.8, 0.85, 0.3]   # sudden spike then recovery
    print(f"   Intensity sequence: {seq}")
    print(f"   Surprise at each step:")
    for i in range(1, len(seq)):
        S = surprise_factor(seq[i], seq[i-1])
        marker = " ← spike!" if S > 0.4 else ""
        print(f"     step {i}: S = {S:.3f}{marker}")

    # 4. Cross-bridge resonance
    print("\n4. Cross-bridge resonance  R = I(bridge ; consciousness)")
    # Bridge signal aligned with consciousness state → high resonance
    bridge_aligned   = [0.7, 0.2, 0.05, 0.05]
    consciousness_aligned = [0.65, 0.25, 0.05, 0.05]
    # Bridge signal orthogonal to consciousness state → low resonance
    bridge_ortho     = [0.05, 0.05, 0.2, 0.7]
    R_aligned = cross_bridge_resonance(bridge_aligned, consciousness_aligned)
    R_ortho   = cross_bridge_resonance(bridge_ortho,   consciousness_aligned)
    print(f"   Aligned signals    R = {R_aligned:.4f}  (expected > R_ortho)")
    print(f"   Orthogonal signals R = {R_ortho:.4f}")

    # 5. Drill-target selection via Fisher information
    print("\n5. Drill-target selection via Fisher information")
    bridge_grads = {
        "thermal":  [-0.05, 0.03, -0.02, 0.04],   # quiet
        "pressure": [-0.1,  0.08, -0.09, 0.11],    # moderate
        "chemical": [-1.8,  2.1,  -2.3,  1.9],     # sharp signal  ← expected target
    }
    target = drill_target(bridge_grads)
    print(f"   Fisher scores: {{{', '.join(f'{k}: {fisher_information(v):.3f}' for k,v in bridge_grads.items())}}}")
    print(f"   Drill target  → '{target}'  (highest Fisher information)")

    # Full encoding demo — curiosity state with thermal trigger
    print("\n" + "=" * 60)
    print("Encoding demo — curiosity state, thermal trigger fires")
    print("=" * 60)

    geometry = {
        "valence":   0.4,   # mildly pleasant
        "arousal":   0.6,   # moderately activated
        "dominance": 0.2,   # slight sense of exploration
        "prior_intensity": 0.1,   # was near-neutral before
        "delta_t":   1.0,
        "trigger_signals": [
            {"bridge_name": "thermal", "intensity": 0.75},   # thermal anomaly
            {"bridge_name": "chemical","intensity": 0.2},    # low chemical signal
        ],
        "bridge_gradients": {
            "thermal":     [-1.8, 2.1, -2.3, 1.9],
            "pressure":    [-0.1, 0.08, -0.09, 0.11],
            "chemical":    [-0.05, 0.03, -0.02, 0.04],
            "consciousness": [-0.3, 0.2, -0.25, 0.28],
        },
    }

    encoder = EmotionBridgeEncoder(drill_threshold=0.5, trigger_threshold=0.3)
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    I = pad_intensity(geometry["valence"], geometry["arousal"], geometry["dominance"])
    S = surprise_factor(I, geometry["prior_intensity"], geometry["delta_t"])
    target = drill_target(geometry["bridge_gradients"])

    print(f"\nEmotional state    : valence={geometry['valence']}, arousal={geometry['arousal']}, dominance={geometry['dominance']}")
    print(f"PAD intensity      : {I:.4f}  (normalised: {I/math.sqrt(3):.4f})")
    print(f"Surprise factor    : {S:.4f}  (state changed rapidly from {geometry['prior_intensity']:.2f})")
    print(f"Drill target       : '{target}'  (sharpest Fisher signal)")
    print(f"\nBinary output      : {binary}")
    print(f"Total bits         : {len(binary)}")
    print(f"Report             : {encoder.report()}")
    print()
    print("Drill logic:")
    drill_fired = I / math.sqrt(3.0) > 0.5
    print(f"  Intensity {I/math.sqrt(3):.3f} {'>' if drill_fired else '<='} threshold 0.5  →  drill_now = {'1 ← causality loop triggered' if drill_fired else '0'}")
    print(f"  Causal bridge: '{target}'  →  re-evaluate thermal bridge at full resolution")
