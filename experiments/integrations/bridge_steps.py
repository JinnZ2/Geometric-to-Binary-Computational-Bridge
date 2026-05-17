"""
experiments/integrations/bridge_steps.py

OPT-IN: turns any bridges/*_encoder.py into a polyglot_playground.Step
factory. Bridges aren't solvers (no Problem -> answer); they're
transformations (geometry dict -> binary string). The right place to
plug them in is mid-pipeline, not as a top-level runner.

Usage:

    from polyglot_playground import Playground, Pipeline
    from integrations.bridge_steps import bridge_step, BRIDGE_DOMAINS

    pg = Playground()
    pg.register_language("python")

    pipe = Pipeline(
        name="magnetic_field_pipeline",
        steps=[
            ...,                                # produce a geometry dict
            bridge_step("magnetic",             # encode it
                        input_key="geometry",
                        output_key="binary"),
            ...,                                # downstream uses .binary
        ],
    )

Each bridge_step runs in-process (the bridges are pure Python), so
no subprocess overhead. The Step's shape defaults to {"bitwise"}
because the output is a binary string -- override if your pipeline
needs different routing semantics for the step.
"""
from __future__ import annotations

import os
import sys
from typing import Any

# Add repo root to sys.path so we can import bridges/* without ceremony.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Add experiments/ for polyglot_playground import.
_EXP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _EXP_ROOT not in sys.path:
    sys.path.insert(0, _EXP_ROOT)

from polyglot_playground import Step


# Map of domain -> (module path, class name). Mirrors solver_registry's
# bridge map but kept local so this file is standalone.
BRIDGE_DOMAINS: dict[str, tuple[str, str]] = {
    "magnetic":      ("bridges.magnetic_encoder",  "MagneticBridgeEncoder"),
    "light":         ("bridges.light_encoder",     "LightBridgeEncoder"),
    "sound":         ("bridges.sound_encoder",     "SoundBridgeEncoder"),
    "gravity":       ("bridges.gravity_encoder",   "GravityBridgeEncoder"),
    "electric":      ("bridges.electric_encoder",  "ElectricBridgeEncoder"),
    "wave":          ("bridges.wave_encoder",      "WaveBridgeEncoder"),
    "thermal":       ("bridges.thermal_encoder",   "ThermalBridgeEncoder"),
    "pressure":      ("bridges.pressure_encoder",  "PressureBridgeEncoder"),
    "chemical":      ("bridges.chemical_encoder",  "ChemicalBridgeEncoder"),
    "consciousness": ("bridges.cognitive.consciousness_encoder",
                      "ConsciousnessBridgeEncoder"),
    "emotion":       ("bridges.cognitive.emotion_encoder",
                      "EmotionBridgeEncoder"),
}


def _load_bridge(domain: str):
    """Import and instantiate the encoder class for `domain`."""
    if domain not in BRIDGE_DOMAINS:
        raise KeyError(
            f"unknown bridge domain '{domain}'. "
            f"Available: {sorted(BRIDGE_DOMAINS)}"
        )
    mod_path, cls_name = BRIDGE_DOMAINS[domain]
    import importlib
    mod = importlib.import_module(mod_path)
    return getattr(mod, cls_name)


def bridge_step(domain: str,
                input_key: str = "geometry",
                output_key: str = "binary",
                label: str | None = None,
                shape: set[str] | None = None) -> Step:
    """Build a Playground Step that encodes a geometry dict via the
    named bridge.

    Reads inputs[input_key] (expected to be a dict of bridge-specific
    geometry params), runs from_geometry() then to_binary(), and writes
    {"binary": str, "report": dict} into state[output_key].
    """
    encoder_cls = _load_bridge(domain)
    step_label  = label or f"encode_{domain}"
    step_shape  = shape or {"bitwise"}

    def encode(inputs, state):
        geometry = inputs.get(input_key)
        if not isinstance(geometry, dict):
            raise ValueError(
                f"bridge_step('{domain}'): expected dict at "
                f"state['{input_key}'], got {type(geometry).__name__}"
            )
        enc = encoder_cls()
        enc.from_geometry(geometry)
        return {
            "binary": enc.to_binary(),
            "report": enc.report(),
        }

    return Step(
        label=step_label,
        shape=step_shape,
        operation=encode,
        input_keys=[input_key],
        output_key=output_key,
    )


# ===================================================================
# SELF-TEST -- run a real bridge inside a pipeline
# ===================================================================

def _self_test() -> None:
    print("=" * 64)
    print("bridge_steps self-test")
    print("=" * 64)

    print(f"\navailable bridge domains: {sorted(BRIDGE_DOMAINS)}")

    from polyglot_playground import Playground, Pipeline, Step

    pg = Playground()
    pg.register_language("python")

    # Step 1: synthesize a minimal magnetic-field geometry
    # Step 2: run it through the magnetic bridge encoder
    # Step 3: report the bit length
    def make_geometry(inputs, state):
        # MagneticBridgeEncoder expects field_lines as a list of dicts
        # with direction/curvature/magnitude keys (see bridges/magnetic_encoder.py).
        return {
            "field_lines": [
                {"direction": "N", "curvature":  0.5, "magnitude": 1.2},
                {"direction": "S", "curvature": -0.3, "magnitude": 0.7},
            ],
            "current_elements": [],
            "resonance_map":    [],
        }

    def summarize(inputs, state):
        binary = state.get("encoded", {}).get("binary", "")
        report = state.get("encoded", {}).get("report", {})
        return (f"binary length: {len(binary)} bits; "
                f"report keys: {sorted(report) if isinstance(report, dict) else type(report).__name__}")

    pipe = Pipeline(
        name="magnetic_bridge_demo",
        description="geometry -> magnetic bridge -> binary report",
        steps=[
            Step("build_geom", {"symbolic"},
                 make_geometry, [], "geometry"),
            bridge_step("magnetic",
                        input_key="geometry",
                        output_key="encoded"),
            Step("summarize",  {"symbolic"},
                 summarize, ["encoded"], "report"),
        ],
    )

    run = pg.run(pipe)

    print(f"\npipeline success: {run.success}")
    for sr in run.step_results:
        print(f"  [{sr.lang_used:8s}] {sr.label:18s}  "
              f"{sr.duration_ms:6.2f}ms  ok={sr.success}")
        if sr.error:
            print(f"      error: {sr.error}")
    print(f"\nfinal report: {run.final_state.get('report')}")


if __name__ == "__main__":
    _self_test()
