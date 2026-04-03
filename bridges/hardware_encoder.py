"""
Hardware Bridge Encoder
=======================
Encodes electronic component health and failure-repurposing state into binary
using core electronics failure-analysis equations and Gray-coded magnitude bands.

Designed for integration with the Component-failure-repurposing-database:
  - FailureMode enum maps to Gray-coded phase bits (adjacent modes differ 1 bit)
  - ComponentHealth health_score feeds directly into consciousness encoder confidence
  - RepurposeChannel maps failed component to the surviving physical bridge modality
  - physics_anomaly / drill_target route degradation signals to CuriosityEngine

Equations implemented
---------------------
  Health score    :  H = max(0, 1 − |x − x₀| / |x_fail − x₀|)  (normalised degradation)
  Drift percent   :  D = |x − x₀| / |x₀| × 100                  (parameter drift %)
  Lifetime est.   :  L = H / max(Ḣ, ε)                           (hours remaining)
  Noise power     :  N = V_rms² / R                               (noise power density)
  Temp coeff sens :  S = ΔV / ΔT                                  (2–3 mV/°C for diodes)

Bit layout (39 bits)
--------------------
Section A — Component health  (9 bits):
  [failure_mode   3b Gray]  NONE(000)→DRIFT(001)→DEGRADED(011)→PARTIAL(010)→OPEN(110)→SHORT(111)
  [health_band    3b Gray]  health_score across 8 linear bands ([0, 0.125, ..., 0.875])
  [is_critical    1b]       health_score < 0.30 (near-failure zone)
  [confidence_hi  1b]       detection confidence > 0.70
  [has_synergy    1b]       known cross-component synergy partner present

Section B — Measurements  (12 bits):
  [voltage_band   3b Gray]  measured voltage (V) across 8 log bands
  [current_band   3b Gray]  measured current (A) across 8 log bands
  [temp_band      3b Gray]  junction/body temperature (°C) across 8 bands
  [noise_band     3b Gray]  normalised noise level [0, 1] across 8 bands

Section C — Repurpose routing  (12 bits):
  [repurpose_class 3b Gray]  NONE(000)→THERMAL(001)→CONDUCTOR(011)→SENSOR(010)→
                              ANTENNA(110)→NOISE_SRC(111)→MECHANICAL(101)→FILTER(100)
  [effectiveness  2b Gray]  repurpose effectiveness across 4 bands ([0, 2.5, 5.0, 7.5]/10)
  [bridge_target  3b Gray]  physical bridge this measurement feeds:
                              THERMAL(000)→ELECTRIC(001)→MAGNETIC(011)→LIGHT(010)→
                              SOUND(110)→WAVE(111)→PRESSURE(101)→CHEMICAL(100)
  [drift_pct_band 2b Gray]  drift % across 4 bands ([0, 1, 10, 50])
  [salvageable    1b]       component can be repurposed
  [fallback_ready 1b]       component viable as emergency fallback channel

Section D — System integration  (6 bits):
  [lifetime_band  3b Gray]  estimated lifetime (h) across 8 log bands ([0, 1, 10, 100, …])
  [drill_depth    2b Gray]  consciousness drill depth: PASS(00)→MONITOR(01)→ALERT(11)→QUARANTINE(10)
  [semiconductor  1b]       is semiconductor (diode/transistor/IC) = 1; passive = 0

License: CC-BY-4.0
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Failure mode ordering (Gray-coded adjacency)
# ---------------------------------------------------------------------------
# NONE→DRIFT→DEGRADED→PARTIAL_DEGRADATION→OPEN_CIRCUIT→SHORT_CIRCUIT
# Adjacent severity levels differ by exactly 1 bit.

_FAILURE_MODES = [
    "none", "drift", "degradation",
    "partial_degradation", "open_circuit", "short_circuit",
]

# Repurpose class ordering (Gray-coded)
_REPURPOSE_CLASSES = [
    "none", "thermal", "conductor", "sensor",
    "antenna", "noise_source", "mechanical", "filter",
]

# Bridge target ordering (Gray-coded)
_BRIDGE_TARGETS = [
    "thermal", "electric", "magnetic", "light",
    "sound", "wave", "pressure", "chemical",
]

# Drill depth ordering (2-bit Gray)
_DRILL_DEPTHS = ["pass", "monitor", "alert", "quarantine"]

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_HEALTH_BANDS    = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]
_VOLTAGE_BANDS   = [0.0, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 50.0]          # V
_CURRENT_BANDS   = [0.0, 1e-6, 1e-4, 1e-3, 0.01, 0.1, 1.0, 10.0]       # A
_TEMP_BANDS      = [-55.0, 25.0, 40.0, 60.0, 85.0, 100.0, 125.0, 175.0] # °C
_NOISE_BANDS     = [0.0, 0.01, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0]           # normalised
_EFFECT_BANDS    = [0.0, 2.5, 5.0, 7.5]                                   # /10, 4-band 2b
_DRIFT_BANDS     = [0.0, 1.0, 10.0, 50.0]                                 # %, 4-band 2b
_LIFETIME_BANDS  = [0.0, 1.0, 10.0, 100.0, 500.0, 1000.0, 5000.0, 1e9]  # hours


# ---------------------------------------------------------------------------
# Lookup tables derived from failure_mode_matrix.csv
# ---------------------------------------------------------------------------

# (component_type, failure_mode) → repurpose_class
_REPURPOSE_MAP = {
    ("diode",       "short_circuit"):        "conductor",
    ("diode",       "open_circuit"):         "antenna",
    ("diode",       "partial_degradation"):  "noise_source",
    ("diode",       "drift"):                "sensor",
    ("resistor",    "open_circuit"):         "mechanical",
    ("resistor",    "value_drift"):          "sensor",
    ("resistor",    "short_circuit"):        "conductor",
    ("capacitor",   "open_circuit"):         "mechanical",
    ("capacitor",   "value_drift"):          "sensor",
    ("capacitor",   "short_circuit"):        "filter",
    ("transistor",  "short_circuit"):        "conductor",
    ("transistor",  "open_circuit"):         "antenna",
    ("transistor",  "degradation"):          "noise_source",
    ("inductor",    "open_circuit"):         "antenna",
    ("inductor",    "degradation"):          "filter",
    ("default",     "short_circuit"):        "conductor",
    ("default",     "open_circuit"):         "mechanical",
    ("default",     "drift"):                "sensor",
    ("default",     "partial_degradation"):  "noise_source",
    ("default",     "degradation"):          "filter",
    ("default",     "none"):                 "none",
}

# repurpose_class → bridge_target  (which physical bridge this now feeds)
_BRIDGE_FROM_REPURPOSE = {
    "thermal":      "thermal",
    "conductor":    "electric",
    "sensor":       "thermal",     # most sensors → thermal channel
    "antenna":      "magnetic",    # RF/inductive loops → magnetic bridge
    "noise_source": "wave",        # entropy/noise → quantum wave bridge
    "mechanical":   "pressure",    # vibration/spacer → pressure bridge
    "filter":       "electric",    # LC/impedance → electric bridge
    "none":         "electric",
}

# failure_mode → effectiveness score /10 (from repurpose_effectiveness.csv)
_EFFECTIVENESS = {
    ("diode",   "short_circuit"):        9.0,
    ("diode",   "partial_degradation"):  8.0,
    ("diode",   "drift"):                7.0,
    ("resistor","open_circuit"):         8.5,
    ("resistor","value_drift"):          6.5,
    ("default", "short_circuit"):        7.0,
    ("default", "open_circuit"):         6.0,
    ("default", "drift"):                5.5,
    ("default", "partial_degradation"):  7.5,
    ("default", "degradation"):          5.0,
    ("default", "none"):                 0.0,
}

_SEMICONDUCTORS = {"diode", "transistor", "bjt", "mosfet", "ic", "led", "photodiode"}


def _failure_bits(failure_mode: str) -> str:
    fm = failure_mode.lower().replace(" ", "_")
    idx = _FAILURE_MODES.index(fm) if fm in _FAILURE_MODES else 0
    g   = idx ^ (idx >> 1)
    return format(g, "03b")


def _index_bits(value: str, table: list, n_bits: int = 3) -> str:
    v   = value.lower().replace(" ", "_")
    idx = table.index(v) if v in table else 0
    g   = idx ^ (idx >> 1)
    return format(g, f"0{n_bits}b")


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def component_health_score(baseline: float, current: float,
                            failure_threshold: float) -> float:
    """
    Normalised health score: H = max(0, 1 − |x − x₀| / |x_fail − x₀|).

    Maps the distance from current value to failure threshold as a [0, 1] score.
    H = 1.0 at baseline; H = 0.0 at or beyond failure_threshold.
    Returns 1.0 when baseline == failure_threshold (degenerate case).
    """
    span = abs(failure_threshold - baseline)
    if span < 1e-30:
        return 1.0
    return max(0.0, 1.0 - abs(current - baseline) / span)


def drift_percent(baseline: float, current: float) -> float:
    """
    Parameter drift percentage: D = |x − x₀| / |x₀| × 100.

    Returns 0.0 when baseline is zero (undefined drift).
    Implements the drift% formula from Core_engine.md health monitoring.
    """
    if abs(baseline) < 1e-30:
        return 0.0
    return abs(current - baseline) / abs(baseline) * 100.0


def lifetime_estimate_hours(health_score: float,
                             drift_rate_per_hour: float) -> float:
    """
    Estimated operational lifetime: L = H / max(Ḣ, ε).

    health_score   : current normalised health [0, 1]
    drift_rate_per_hour : health loss per hour (dimensionless/h)
    Returns hours until health_score → 0; returns 1e9 (infinite) when drift_rate ≤ 0.
    """
    if drift_rate_per_hour <= 0.0:
        return 1e9
    return health_score / max(drift_rate_per_hour, 1e-12)


def noise_power(v_rms: float, resistance_ohm: float) -> float:
    """
    Electrical noise power density: N = V_rms² / R  (W).

    Converts measured RMS noise voltage and source resistance to power.
    High noise power in a degraded junction indicates PARTIAL_DEGRADATION mode.
    """
    if resistance_ohm <= 0.0:
        return 0.0
    return (v_rms ** 2) / resistance_ohm


def temp_coefficient_sensitivity(delta_v: float, delta_t: float) -> float:
    """
    Temperature coefficient sensitivity: S = ΔV / ΔT  (V/°C).

    Typical values: silicon diode −2 to −3 mV/°C; failed diodes 2–5 mV/°C.
    Used to identify components repurposed as temperature sensors.
    """
    if abs(delta_t) < 1e-10:
        return 0.0
    return delta_v / delta_t


def repurpose_class(component_type: str, failure_mode: str) -> str:
    """
    Look up repurpose class from (component_type, failure_mode) pair.

    Returns one of: none, thermal, conductor, sensor, antenna,
                    noise_source, mechanical, filter.
    Falls back to 'default' key when component_type is unknown.
    """
    key = (component_type.lower(), failure_mode.lower().replace(" ", "_"))
    return _REPURPOSE_MAP.get(key,
           _REPURPOSE_MAP.get(("default", failure_mode.lower().replace(" ", "_")),
           "none"))


def bridge_target(repurpose: str) -> str:
    """
    Map repurpose class to the physical bridge modality it feeds.

    Returns one of: thermal, electric, magnetic, light, sound, wave, pressure, chemical.
    """
    return _BRIDGE_FROM_REPURPOSE.get(repurpose.lower(), "electric")


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class HardwareBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes electronic component health and repurpose state into a 39-bit bitstring.

    Input geometry dict keys
    ------------------------
    component_type  : str   — "diode"/"resistor"/"capacitor"/"transistor"/"inductor"/...
    failure_mode    : str   — "none"/"drift"/"degradation"/"partial_degradation"/
                              "open_circuit"/"short_circuit"
    health_score    : float — normalised health [0, 1]  (use component_health_score())
    confidence      : float — detection confidence [0, 1]
    has_synergy     : bool  — cross-component synergy partner exists
    voltage_v       : float — measured terminal voltage (V)
    current_a       : float — measured current (A)
    temperature_c   : float — component temperature (°C)
    noise_level     : float — normalised noise [0, 1]  (use noise_power() normalised)
    drift_pct       : float — parameter drift %        (use drift_percent())
    lifetime_hours  : float — estimated lifetime (h)   (use lifetime_estimate_hours())
    salvageable     : bool  — component viable for repurposing
    fallback_ready  : bool  — component usable as emergency fallback channel
    """

    def __init__(self):
        super().__init__("hardware")

    def from_geometry(self, geometry_data: dict):
        """Load component state data from a geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert component health state to a 39-bit binary string.

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
        comp_type   = d.get("component_type",  "default")
        fail_mode   = d.get("failure_mode",    "none")
        health      = float(d.get("health_score",   1.0))
        confidence  = float(d.get("confidence",     1.0))
        has_syn     = bool(d.get("has_synergy",     False))
        voltage     = float(d.get("voltage_v",      0.0))
        current     = float(d.get("current_a",      0.0))
        temperature = float(d.get("temperature_c",  25.0))
        noise       = float(d.get("noise_level",    0.0))
        drift       = float(d.get("drift_pct",      0.0))
        lifetime    = float(d.get("lifetime_hours", 1e9))
        salvageable = bool(d.get("salvageable",     False))
        fallback    = bool(d.get("fallback_ready",  False))

        bits = []

        # ------------------------------------------------------------------
        # Section A: Component health  →  9 bits
        # ------------------------------------------------------------------
        bits.append(_failure_bits(fail_mode))
        bits.append(_gray_bits(health, _HEALTH_BANDS))
        bits.append("1" if health < 0.30 else "0")                  # is_critical
        bits.append("1" if confidence > 0.70 else "0")              # confidence_hi
        bits.append("1" if has_syn else "0")                         # has_synergy

        # ------------------------------------------------------------------
        # Section B: Measurements  →  12 bits
        # ------------------------------------------------------------------
        bits.append(_gray_bits(abs(voltage),  _VOLTAGE_BANDS))
        bits.append(_gray_bits(abs(current),  _CURRENT_BANDS))
        bits.append(_gray_bits(temperature,   _TEMP_BANDS))
        bits.append(_gray_bits(noise,         _NOISE_BANDS))

        # ------------------------------------------------------------------
        # Section C: Repurpose routing  →  12 bits
        # ------------------------------------------------------------------
        rp    = repurpose_class(comp_type, fail_mode)
        bt    = bridge_target(rp)
        key   = (comp_type.lower(), fail_mode.lower().replace(" ", "_"))
        eff   = _EFFECTIVENESS.get(key,
                _EFFECTIVENESS.get(("default", fail_mode.lower().replace(" ", "_")), 0.0))

        bits.append(_index_bits(rp, _REPURPOSE_CLASSES))
        bits.append(_gray_bits(eff,  _EFFECT_BANDS, n_bits=2))
        bits.append(_index_bits(bt,  _BRIDGE_TARGETS))
        bits.append(_gray_bits(drift, _DRIFT_BANDS, n_bits=2))
        bits.append("1" if salvageable else "0")
        bits.append("1" if fallback    else "0")

        # ------------------------------------------------------------------
        # Section D: System integration  →  6 bits
        # ------------------------------------------------------------------
        # Drill depth: escalate based on health
        if health < 0.30:
            drill = "quarantine"
        elif health < 0.50:
            drill = "alert"
        elif health < 0.70:
            drill = "monitor"
        else:
            drill = "pass"

        bits.append(_gray_bits(lifetime, _LIFETIME_BANDS))
        bits.append(_index_bits(drill, _DRILL_DEPTHS, n_bits=2))
        bits.append("1" if comp_type.lower() in _SEMICONDUCTORS else "0")

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Hardware Bridge Encoder — Component Failure Demo")
    print("=" * 60)

    # 1. Health score across failure progression
    print("\n1. Health score  H = 1 − |x − x₀| / |x_fail − x₀|")
    cases = [
        ("Nominal resistor",  1000.0, 1000.0, 2000.0),
        ("10% drift",         1000.0, 1100.0, 2000.0),
        ("50% drift",         1000.0, 1500.0, 2000.0),
        ("At failure",        1000.0, 2000.0, 2000.0),
    ]
    for label, x0, x, xf in cases:
        h = component_health_score(x0, x, xf)
        d = drift_percent(x0, x)
        print(f"   {label:22s}  H = {h:.3f}  drift = {d:.1f}%")

    # 2. Repurpose routing
    print("\n2. Repurpose routing")
    examples = [
        ("diode",    "short_circuit"),
        ("diode",    "partial_degradation"),
        ("resistor", "open_circuit"),
        ("resistor", "value_drift"),
        ("inductor", "open_circuit"),
    ]
    for ct, fm in examples:
        rp = repurpose_class(ct, fm)
        bt = bridge_target(rp)
        print(f"   {ct:12s} + {fm:22s} → repurpose={rp:12s}  bridge={bt}")

    # 3. Lifetime estimates
    print("\n3. Lifetime estimates  L = H / drift_rate")
    for H, rate in [(0.9, 0.001), (0.5, 0.01), (0.3, 0.05), (0.1, 0.1)]:
        L = lifetime_estimate_hours(H, rate)
        print(f"   H={H:.1f}, rate={rate:.3f}/h → L ≈ {L:.0f} h")

    # 4. Full encoding
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    components = [
        {
            "component_type": "diode",
            "failure_mode":   "partial_degradation",
            "health_score":   0.45,
            "confidence":     0.85,
            "has_synergy":    True,
            "voltage_v":      0.35,
            "current_a":      0.002,
            "temperature_c":  65.0,
            "noise_level":    0.62,
            "drift_pct":      18.0,
            "lifetime_hours": 120.0,
            "salvageable":    True,
            "fallback_ready": True,
        },
        {
            "component_type": "resistor",
            "failure_mode":   "open_circuit",
            "health_score":   0.10,
            "confidence":     0.95,
            "has_synergy":    False,
            "voltage_v":      0.0,
            "current_a":      0.0,
            "temperature_c":  28.0,
            "noise_level":    0.05,
            "drift_pct":      100.0,
            "lifetime_hours": 0.0,
            "salvageable":    True,
            "fallback_ready": False,
        },
    ]

    for comp in components:
        enc = HardwareBridgeEncoder()
        enc.from_geometry(comp)
        b = enc.to_binary()
        rp = repurpose_class(comp["component_type"], comp["failure_mode"])
        print(f"\n  {comp['component_type']:12s} [{comp['failure_mode']}]")
        print(f"  repurpose → {rp:14s}  bridge → {bridge_target(rp)}")
        print(f"  binary    : {b}  ({len(b)} bits)")


### notes to do: have ("diode", "short_circuit") mapping to "conductor". In a high-energy task, a shorted diode often becomes a thermal event (a fuse) before it becomes a useful conductor. Have you considered adding a conditional check in Section D that triggers a QUARANTINE if the temp_band and current_band spike simultaneously, regardless of the health score?
