"""
Drill Loop — Causality Feedback Closure
=========================================
Closes the feedback circuit opened by the emotion bridge.

The EmotionBridgeEncoder emits a causality drill-target (the bridge with the
highest Fisher information) when PAD intensity exceeds drill_threshold.
This module receives that signal and completes the loop:

  1. Identify  — emotion bridge selects target via drill_target() / Fisher info
  2. Re-encode — target bridge re-runs at full resolution on fresh geometry data
  3. Validate  — PhysicsGuard checks the result against five physics invariants:
                   non-negativity, causality, conservation, decay (Seed-physics)
                   + phi-coherence (Geometric-seed TrojanEngine)
  4. Route     — action='accept'     → result valid, pass binary to consciousness
                 action='quarantine' → invariant violated, suppress propagation
                 action='no_target'  → drill target unknown or unregistered

This closes the loop opened at:
  bridges/cognitive/emotion_encoder.py line 320 — target_name = drill_target(bridge_grads)

Architecture position
---------------------
  Physical bridges  (full-resolution re-evaluation of drill target)
    └─ DrillLoop.execute()
         ├─ encoder_registry[drill_target].from_geometry(data).to_binary()
         └─ PhysicsGuard.validate_drill(bridge_gradients)
               ├─ action='accept'     → return binary to caller
               └─ action='quarantine' → suppress, log violation

Usage
-----
    from bridges.drill_loop import DrillLoop
    from bridges.thermal_encoder import ThermalBridgeEncoder
    from bridges.cognitive.consciousness_encoder import ConsciousnessBridgeEncoder

    loop = DrillLoop(
        encoder_registry={
            "thermal":       ThermalBridgeEncoder(),
            "consciousness": ConsciousnessBridgeEncoder(),
        }
    )

    result = loop.execute(
        drill_target="thermal",
        geometry_data={...},       # full-resolution thermal geometry
        bridge_gradients={         # gradients from all active bridges
            "thermal":       [...],
            "consciousness": [...],
            "emotion":       [...],
        },
    )

    if result["action"] == "accept":
        binary = result["binary"]   # pass to consciousness bridge
"""

from bridges.physics_guard import PhysicsGuard


class DrillLoop:
    """
    Receives causality drill-targets from the emotion bridge, re-evaluates the
    target bridge at full resolution, validates via PhysicsGuard, and returns
    the result for downstream consumption by the consciousness bridge.

    Parameters
    ----------
    encoder_registry : dict
        bridge_name (str) → encoder instance.
        Each encoder must implement from_geometry() / to_binary() (i.e. inherit
        from BinaryBridgeEncoder in bridges/abstract_encoder.py).
    guard : PhysicsGuard, optional
        Physics validator.  A default PhysicsGuard() is created if omitted.
    """

    def __init__(self, encoder_registry: dict, guard: PhysicsGuard = None):
        self.encoder_registry = encoder_registry
        self.guard            = guard or PhysicsGuard()
        self.last_result      = None

    def execute(self, drill_target: str, geometry_data: dict,
                bridge_gradients: dict) -> dict:
        """
        Execute a drill-down re-evaluation of the target bridge.

        Parameters
        ----------
        drill_target     : str
            Bridge name emitted by EmotionBridgeEncoder (e.g. 'thermal').
            Must be a key in encoder_registry, or 'none'.
        geometry_data    : dict
            Full-resolution geometry for the target bridge — same format as
            the geometry dict passed to that bridge's from_geometry().
        bridge_gradients : dict
            bridge_name → list of log-likelihood gradients for all currently
            active bridges.  Passed directly to PhysicsGuard.validate_drill().
            Include 'consciousness' and 'emotion' layers when available for a
            complete three-layer stack check.

        Returns
        -------
        dict with keys:
          drill_target : str   — which bridge was re-evaluated
          binary       : str   — full-resolution binary encoding ('' if skipped)
          valid        : bool  — True if all physics constraints passed
          coherence    : float — phi-coherence score [0, 1]
          action       : str   — 'accept' | 'quarantine' | 'no_target'
          guard_detail : dict  — per-constraint breakdown from PhysicsGuard
        """
        # Guard: unknown or missing target
        if drill_target == "none" or drill_target not in self.encoder_registry:
            result = {
                "drill_target": drill_target,
                "binary":       "",
                "valid":        False,
                "coherence":    0.0,
                "action":       "no_target",
                "guard_detail": {},
            }
            self.last_result = result
            return result

        # Full-resolution re-evaluation
        encoder = self.encoder_registry[drill_target]
        encoder.from_geometry(geometry_data)
        binary = encoder.to_binary()

        # Physics guard validation
        validation = self.guard.validate_drill(bridge_gradients)

        result = {
            "drill_target": drill_target,
            "binary":       binary,
            "valid":        validation["passed"],
            "coherence":    validation["coherence"],
            "action":       validation["action"],
            "guard_detail": validation,
        }
        self.last_result = result
        return result


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Minimal self-contained demo using the emotion encoder to fire the drill
    # and the drill loop to close the circuit.

    from bridges.cognitive.emotion_encoder import EmotionBridgeEncoder, drill_target
    from bridges.physics_guard import PhysicsGuard

    print("=" * 60)
    print("Drill Loop — Causality Feedback Closure Demo")
    print("=" * 60)

    # Simulate emotion bridge firing on a strong thermal anomaly
    geometry = {
        "valence":   0.4,
        "arousal":   0.8,
        "dominance": 0.2,
        "prior_intensity": 0.1,
        "delta_t":   1.0,
        "trigger_signals": [
            {"bridge_name": "thermal", "intensity": 0.9},
        ],
        "bridge_gradients": {
            "thermal":       [-1.8,  2.1, -2.3,  1.9],   # sharpest — drill target
            "pressure":      [-0.3,  0.2, -0.25, 0.28],
            "consciousness": [-0.9,  1.1, -1.2,  1.0],
            "emotion":       [-0.4,  0.5, -0.55, 0.45],
        },
    }

    emotion_enc = EmotionBridgeEncoder(drill_threshold=0.5)
    emotion_enc.from_geometry(geometry)
    emotion_binary = emotion_enc.to_binary()
    target = drill_target(geometry["bridge_gradients"])

    print(f"\nEmotion binary ({len(emotion_binary)} bits): {emotion_binary}")
    print(f"Drill target identified: '{target}'")

    # DrillLoop with a stub encoder for demo (real usage: pass actual encoder)
    class _StubEncoder:
        """Stand-in encoder that echoes geometry as a fixed bit pattern."""
        def from_geometry(self, data):
            self._data = data
            return self
        def to_binary(self):
            return "101010" * 6   # 36-bit stub output

    loop = DrillLoop(
        encoder_registry={"thermal": _StubEncoder()},
        guard=PhysicsGuard(),
    )

    result = loop.execute(
        drill_target=target,
        geometry_data={"temperature_k": 310.0, "heat_flux": 0.85},
        bridge_gradients=geometry["bridge_gradients"],
    )

    print(f"\nDrill result:")
    print(f"  drill_target : {result['drill_target']}")
    print(f"  action       : {result['action']}")
    print(f"  valid        : {result['valid']}")
    print(f"  coherence    : {result['coherence']:.4f}")
    print(f"  binary       : {result['binary'][:24]}...  ({len(result['binary'])} bits)")
    print(f"\n  Guard detail:")
    for k, v in result["guard_detail"].get("stack_valid", {}).items():
        if isinstance(v, dict):
            print(f"    {k:14s} passed={v.get('passed')}")

    # Unknown target → no_target
    miss = loop.execute("chemical", {}, geometry["bridge_gradients"])
    print(f"\nUnregistered target 'chemical' → action='{miss['action']}'")
