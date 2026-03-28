"""
BioMachine Bridge Encoder
=========================
Encodes field-machine state (seals, gaskets, regenerative edge nodes) into binary
using physics-grounded equations for material stress, thermal limits, and
regeneration dynamics.

Designed for integration with the biomachine_ecology repository:
  - seal_stress_index() implements the composite stress metric from AutoTuneLoop
  - Material class maps to Gray-coded band for adjacent-material stability
  - Emotional glyph state (grief/presence/resilience) feeds the emotion encoder
  - bridge_primary() routes the dominant signal to the correct physical bridge
  - regen_trigger() matches SEAL_GENOME_TEMPLATE.json tolerances.seal_stress_threshold

Equations implemented
---------------------
  Seal stress index  :  σ = w_c·(Cset/C_max) + w_e·(1 − ε/ε_min) + w_v·V_class
                          + w_T·(ΔT/T_max) + w_s·S_exp + w_u·U_exp   (weighted sum)
  Material temp head :  ΔT_head = T_max − T_ambient                   (margin to limit)
  Compression set    :  Cset% ← measured; threshold from genome         (0–100%)
  Regen trigger      :  σ ≥ threshold (default 0.70 per genome template)
  Shore band         :  A-scale 0–100 → 4 linear bands                 (soft→rigid)

Bit layout (39 bits)
--------------------
Section A — Seal / field state  (12 bits):
  [machine_phase  2b Gray]  NOMINAL(00)→STRESSED(01)→REGENERATING(11)→FAILED(10)
  [stress_band    3b Gray]  seal_stress_index across 8 bands ([0, 0.1, 0.2, …, 0.7])
  [above_thresh   1b]       stress ≥ 0.70 (regen trigger active)
  [material_class 3b Gray]  HDPE(000)→PETG(001)→PP(011)→RUBBER(010)→
                              TPU(110)→NYLON(111)→COMPOSITE(101)→METAL(100)
  [uv_exposed     1b]       UV exposure flag
  [salt_exposed   1b]       salt/marine environment flag
  [submerged      1b]       submerged_intermittent or continuous

Section B — Environmental measurements  (12 bits):
  [vibration_class 2b Gray]  none(00)→low(01)→moderate(11)→high(10)
  [temp_delta_band 3b Gray]  temperature rise above ambient (°C) across 8 bands
  [comp_set_band   3b Gray]  compression_set % across 8 bands ([0, 5, 10, 15, 20, 25, 30, 40])
  [elongation_ok   1b]       elongation remaining > 50% of minimum
  [shore_band      2b Gray]  Shore A hardness: soft(00)→medium(01)→hard(11)→rigid(10)
  [age_hi          1b]       component age > 1000 cycles

Section C — Regeneration state  (9 bits):
  [regen_active    1b]       auto_regen_on_stress triggered
  [fallback_mat    2b Gray]  fallback material: NONE(00)→PETG(01)→PP(11)→HDPE(10)
  [stl_ready       1b]       regenerated STL output ready for print
  [emotion_glyph   3b Gray]  NEUTRAL(000)→PRESENCE(001)→GRIEF(011)→ADAPTATION(010)→
                               RESILIENCE(110)→FAILURE(111)→REGENERATING(101)→THRIVING(100)
  [harvest_active  1b]       energy harvester operational
  [queue_pending   1b]       offline telemetry queue has unsent packets

Section D — Bridge routing  (6 bits):
  [bridge_primary  3b Gray]  dominant bridge: PRESSURE(000)→THERMAL(001)→CHEMICAL(011)→
                               ELECTRIC(010)→MAGNETIC(110)→WAVE(111)→SOUND(101)→LIGHT(100)
  [regen_hi        1b]       regeneration efficiency above baseline (capacity > 1.5)
  [needs_drill     1b]       requires curiosity engine re-evaluation
  [anomaly         1b]       physics_anomaly flag (stress > 0.85 OR material near T_max)

License: CC-BY-4.0
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Ordered tables for Gray-coded fields
# ---------------------------------------------------------------------------

_MACHINE_PHASES = ["nominal", "stressed", "regenerating", "failed"]

_MATERIAL_CLASSES = [
    "hdpe", "petg", "pp", "rubber",
    "tpu", "nylon", "composite", "metal",
]

_VIBRATION_CLASSES = ["none", "low", "moderate", "high"]

_FALLBACK_MATERIALS = ["none", "petg", "pp", "hdpe"]

_EMOTION_GLYPHS = [
    "neutral", "presence", "grief", "adaptation",
    "resilience", "failure", "regenerating", "thriving",
]

_BRIDGE_PRIMARY = [
    "pressure", "thermal", "chemical", "electric",
    "magnetic", "wave", "sound", "light",
]

# ---------------------------------------------------------------------------
# Physical material limits (max continuous-use temperature, °C)
# ---------------------------------------------------------------------------
_MATERIAL_MAX_TEMP = {
    "hdpe": 80.0, "petg": 75.0, "pp": 100.0, "rubber": 120.0,
    "tpu": 90.0,  "nylon": 130.0, "composite": 110.0, "metal": 450.0,
}

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_STRESS_BANDS    = [0.0, 0.1, 0.2, 0.35, 0.5, 0.60, 0.70, 0.85]
_TEMP_DELTA_BANDS= [0.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 80.0]      # °C above ambient
_COMP_SET_BANDS  = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0]      # %
_SHORE_BANDS     = [0.0, 30.0, 55.0, 75.0]                               # Shore A, 4-band 2b

# Stress weighting factors (must sum to 1.0)
_W_COMP  = 0.30   # compression set contribution
_W_ELONG = 0.25   # elongation margin contribution
_W_VIB   = 0.15   # vibration class contribution
_W_TEMP  = 0.15   # temperature delta contribution
_W_SALT  = 0.08   # salt exposure
_W_UV    = 0.07   # UV exposure

# Vibration class → numeric severity for weighting
_VIB_SEVERITY = {"none": 0.0, "low": 0.33, "moderate": 0.67, "high": 1.0}


def _table_bits(value: str, table: list, n_bits: int = 3) -> str:
    v   = value.lower().strip()
    idx = table.index(v) if v in table else 0
    g   = idx ^ (idx >> 1)
    return format(g, f"0{n_bits}b")


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def seal_stress_index(compression_set_pct: float,
                      compression_set_max_pct: float,
                      elongation_remaining_pct: float,
                      elongation_min_pct: float,
                      vibration_class: str = "none",
                      temp_delta_c: float = 0.0,
                      temp_delta_max_c: float = 80.0,
                      salt_exposure: bool = False,
                      uv_exposure: bool = False) -> float:
    """
    Composite seal stress index: σ ∈ [0, 1].

    Weighted combination of six stress contributors:
      w_c · Cset/C_max  +  w_e · (1 − ε/ε_min)
      + w_v · V_class   +  w_T · ΔT/ΔT_max
      + w_s · S_exp     +  w_u · U_exp

    Returns 1.0 when every dimension is at its limit; 0.0 when pristine.
    Matches the SEAL_GENOME_TEMPLATE tolerances.seal_stress_threshold = 0.70.
    """
    c_term = min(compression_set_pct / max(compression_set_max_pct, 1.0), 1.0)
    e_term = max(0.0, 1.0 - elongation_remaining_pct / max(elongation_min_pct, 1.0))
    v_term = _VIB_SEVERITY.get(vibration_class.lower(), 0.0)
    t_term = min(abs(temp_delta_c) / max(temp_delta_max_c, 1.0), 1.0)
    s_term = 1.0 if salt_exposure else 0.0
    u_term = 1.0 if uv_exposure   else 0.0

    return (_W_COMP  * c_term +
            _W_ELONG * e_term +
            _W_VIB   * v_term +
            _W_TEMP  * t_term +
            _W_SALT  * s_term +
            _W_UV    * u_term)


def regen_trigger(stress_index: float, threshold: float = 0.70) -> bool:
    """
    Return True when seal stress exceeds regen threshold.

    Matches SEAL_GENOME_TEMPLATE tolerances.seal_stress_threshold = 0.70.
    """
    return stress_index >= threshold


def material_temp_headroom(material_type: str, ambient_temp_c: float) -> float:
    """
    Temperature headroom before material limit: ΔT_head = T_max − T_ambient (°C).

    Returns 0.0 when ambient already exceeds material limit.
    Known materials: hdpe, petg, pp, rubber, tpu, nylon, composite, metal.
    """
    t_max = _MATERIAL_MAX_TEMP.get(material_type.lower(), 80.0)
    return max(0.0, t_max - ambient_temp_c)


def shore_to_numeric(shore_str: str) -> float:
    """
    Parse Shore hardness string to numeric value.

    Accepts "60A", "80A", "95A", or bare numbers.  Returns 0.0 on failure.
    """
    s = shore_str.upper().replace("A", "").replace(" ", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def dominant_bridge(stress_index: float, temp_delta_c: float,
                    salt_exposure: bool, vibration_class: str) -> str:
    """
    Select the primary physical bridge based on dominant stress signal.

    Rules (in priority order):
      - stress ≥ 0.7 + high vibration  → pressure
      - temp_delta > 30°C              → thermal
      - salt + stress ≥ 0.5           → chemical
      - stress ≥ 0.5                  → pressure
      - temp_delta > 10°C             → thermal
      - any exposure                  → chemical
      - default                       → pressure
    """
    if stress_index >= 0.7 and vibration_class.lower() in ("moderate", "high"):
        return "pressure"
    if temp_delta_c > 30.0:
        return "thermal"
    if salt_exposure and stress_index >= 0.5:
        return "chemical"
    if stress_index >= 0.5:
        return "pressure"
    if temp_delta_c > 10.0:
        return "thermal"
    if salt_exposure:
        return "chemical"
    return "pressure"


def emotion_from_stress(stress_index: float, regen_active: bool,
                        previous_failure: bool = False) -> str:
    """
    Map machine state to emotional glyph label.

    Maps to the biomachine_ecology vault/emotions emotion-machine-map:
      thriving      : stress < 0.2
      presence      : 0.2 ≤ stress < 0.4
      adaptation    : 0.4 ≤ stress < 0.6
      resilience    : 0.6 ≤ stress < 0.7
      regenerating  : regen_active=True
      grief         : stress ≥ 0.7 (loss of integrity)
      failure       : previous_failure=True
      neutral       : default
    """
    if regen_active:
        return "regenerating"
    if previous_failure:
        return "failure"
    if stress_index >= 0.70:
        return "grief"
    if stress_index >= 0.60:
        return "resilience"
    if stress_index >= 0.40:
        return "adaptation"
    if stress_index >= 0.20:
        return "presence"
    return "thriving"


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class BiomachineBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes field-machine / seal state into a 39-bit binary bitstring.

    Input geometry dict keys
    ------------------------
    machine_phase         : str   — "nominal"/"stressed"/"regenerating"/"failed"
    stress_index          : float — seal_stress_index() output [0, 1]
    stress_threshold      : float — regen trigger threshold (default 0.70)
    material_type         : str   — "hdpe"/"petg"/"pp"/"rubber"/"tpu"/"nylon"/"composite"/"metal"
    uv_exposure           : bool
    salt_exposure         : bool
    submerged             : bool
    vibration_class       : str   — "none"/"low"/"moderate"/"high"
    temp_delta_c          : float — temperature rise above ambient (°C)
    compression_set_pct   : float — measured compression set (%)
    elongation_remaining  : float — remaining elongation (% of rated minimum)
    shore_hardness        : float — Shore A value (e.g. 60.0)
    age_cycles            : int   — operational cycle count
    regen_active          : bool  — auto-regen triggered
    fallback_material     : str   — "none"/"petg"/"pp"/"hdpe"
    stl_ready             : bool  — regenerated geometry ready for print
    emotion_glyph         : str   — see emotion_from_stress(); overrides auto if provided
    harvest_active        : bool  — energy harvester online
    queue_pending         : bool  — offline telemetry queue non-empty
    regen_capacity_ratio  : float — current capacity / initial capacity (> 1.0 = grown)
    """

    def __init__(self, stress_threshold: float = 0.70):
        super().__init__("biomachine")
        self.stress_threshold = stress_threshold

    def from_geometry(self, geometry_data: dict):
        """Load field-machine state from a geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert field-machine state into a 39-bit binary string.

        Raises
        ------
        ValueError
            If from_geometry() has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        d = self.input_geometry
        phase       = d.get("machine_phase",        "nominal")
        stress      = float(d.get("stress_index",          0.0))
        threshold   = float(d.get("stress_threshold",      self.stress_threshold))
        material    = d.get("material_type",         "hdpe")
        uv          = bool(d.get("uv_exposure",      False))
        salt        = bool(d.get("salt_exposure",    False))
        submerged   = bool(d.get("submerged",        False))
        vib         = d.get("vibration_class",       "none")
        temp_delta  = float(d.get("temp_delta_c",        0.0))
        comp_set    = float(d.get("compression_set_pct",  0.0))
        elong_rem   = float(d.get("elongation_remaining", 100.0))
        shore       = float(d.get("shore_hardness",       60.0))
        age         = int(d.get("age_cycles",             0))
        regen       = bool(d.get("regen_active",    False))
        fallback_m  = d.get("fallback_material",    "none")
        stl_ready   = bool(d.get("stl_ready",       False))
        emotion     = d.get("emotion_glyph",
                             emotion_from_stress(stress, regen))
        harvest     = bool(d.get("harvest_active",  False))
        queue       = bool(d.get("queue_pending",   False))
        cap_ratio   = float(d.get("regen_capacity_ratio", 1.0))

        bits = []

        # ------------------------------------------------------------------
        # Section A: Seal / field state  →  12 bits
        # ------------------------------------------------------------------
        bits.append(_table_bits(phase,    _MACHINE_PHASES,    n_bits=2))
        bits.append(_gray_bits(stress,    _STRESS_BANDS))
        bits.append("1" if stress >= threshold else "0")         # above_thresh
        bits.append(_table_bits(material, _MATERIAL_CLASSES,   n_bits=3))
        bits.append("1" if uv        else "0")
        bits.append("1" if salt      else "0")
        bits.append("1" if submerged else "0")

        # ------------------------------------------------------------------
        # Section B: Environmental measurements  →  12 bits
        # ------------------------------------------------------------------
        bits.append(_table_bits(vib,   _VIBRATION_CLASSES,  n_bits=2))
        bits.append(_gray_bits(temp_delta, _TEMP_DELTA_BANDS))
        bits.append(_gray_bits(comp_set,   _COMP_SET_BANDS))
        bits.append("1" if elong_rem > 50.0 else "0")            # elongation_ok
        bits.append(_gray_bits(shore,      _SHORE_BANDS, n_bits=2))
        bits.append("1" if age > 1000 else "0")                  # age_hi

        # ------------------------------------------------------------------
        # Section C: Regeneration state  →  9 bits
        # ------------------------------------------------------------------
        bits.append("1" if regen     else "0")
        bits.append(_table_bits(fallback_m, _FALLBACK_MATERIALS, n_bits=2))
        bits.append("1" if stl_ready else "0")
        bits.append(_table_bits(emotion, _EMOTION_GLYPHS, n_bits=3))
        bits.append("1" if harvest   else "0")
        bits.append("1" if queue     else "0")

        # ------------------------------------------------------------------
        # Section D: Bridge routing  →  6 bits
        # ------------------------------------------------------------------
        bp     = dominant_bridge(stress, temp_delta, salt, vib)
        anomaly = stress > 0.85 or material_temp_headroom(material, 25.0 + temp_delta) < 5.0

        bits.append(_table_bits(bp, _BRIDGE_PRIMARY, n_bits=3))
        bits.append("1" if cap_ratio > 1.5 else "0")            # regen_hi
        bits.append("1" if regen_trigger(stress, threshold) else "0")  # needs_drill
        bits.append("1" if anomaly else "0")

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("BioMachine Bridge Encoder — Seal / Field Machine Demo")
    print("=" * 60)

    # 1. Seal stress across conditions
    print("\n1. Seal stress index σ (threshold = 0.70)")
    scenarios = [
        ("Pristine",        5.0,  25.0, 250.0, 300.0, "none",     False, False),
        ("Moderate wear",  15.0,  20.0, 180.0, 300.0, "low",      False, True),
        ("High stress",    20.0,  45.0,  90.0, 300.0, "moderate", True,  True),
        ("Critical",       24.0,  60.0,  40.0, 300.0, "high",     True,  True),
    ]
    for label, cs, td, el, el_min, vib, salt, uv in scenarios:
        s = seal_stress_index(cs, 25.0, el, el_min, vib, td, 80.0, salt, uv)
        print(f"   {label:14s}  σ = {s:.3f}  regen={'YES' if regen_trigger(s) else 'no '}")

    # 2. Emotion mapping
    print("\n2. Emotional state from stress")
    for stress, regen, prev in [(0.1, False, False), (0.3, False, False),
                                 (0.55, False, False), (0.72, False, False),
                                 (0.72, True, False), (0.9, False, True)]:
        em = emotion_from_stress(stress, regen, prev)
        print(f"   stress={stress:.2f} regen={regen} prev_fail={prev} → {em}")

    # 3. Material headroom
    print("\n3. Material temperature headroom")
    for mat, ambient in [("hdpe", 25.0), ("hdpe", 75.0), ("pp", 90.0), ("nylon", 125.0)]:
        h = material_temp_headroom(mat, ambient)
        print(f"   {mat:10s} at {ambient:5.0f}°C → headroom = {h:.0f}°C")

    # 4. Full encoding
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "machine_phase":        "stressed",
        "stress_index":         0.73,
        "material_type":        "hdpe",
        "uv_exposure":          True,
        "salt_exposure":        True,
        "submerged":            False,
        "vibration_class":      "moderate",
        "temp_delta_c":         22.0,
        "compression_set_pct":  18.0,
        "elongation_remaining": 210.0,
        "shore_hardness":       60.0,
        "age_cycles":           850,
        "regen_active":         True,
        "fallback_material":    "petg",
        "stl_ready":            False,
        "harvest_active":       True,
        "queue_pending":        False,
        "regen_capacity_ratio": 1.1,
    }

    enc = BiomachineBridgeEncoder()
    enc.from_geometry(geometry)
    b = enc.to_binary()

    print(f"\nMachine phase   : {geometry['machine_phase']}")
    print(f"Stress index    : {geometry['stress_index']}")
    print(f"Emotion         : {emotion_from_stress(geometry['stress_index'], geometry['regen_active'])}")
    print(f"Bridge target   : {dominant_bridge(geometry['stress_index'], geometry['temp_delta_c'], geometry['salt_exposure'], geometry['vibration_class'])}")
    print(f"Binary output   : {b}")
    print(f"Total bits      : {len(b)}")
    print(f"Report          : {enc.report()}")
