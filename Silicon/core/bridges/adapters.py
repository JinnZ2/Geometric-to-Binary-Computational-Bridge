"""Navigation-friendly bridge adapters for the silicon layer.

This module provides one import location for the bridge families that live
in the top-level ``bridges/`` package, plus the geometric fiber / holonomy
bridge that lives in the silicon layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Type

from bridges.sound_encoder import SoundBridgeEncoder
from bridges.electric_encoder import ElectricBridgeEncoder
from bridges.gravity_encoder import GravityBridgeEncoder
from bridges.community_encoder import CommunityBridgeEncoder
from bridges.pressure_encoder import PressureBridgeEncoder
from bridges.light_encoder import LightBridgeEncoder
from bridges.magnetic_encoder import MagneticBridgeEncoder
from bridges.thermal_encoder import ThermalBridgeEncoder
from bridges.wave_encoder import WaveBridgeEncoder
from bridges.chemical_encoder import ChemicalBridgeEncoder
from bridges.resilience_encoder import ResilienceBridgeEncoder
from bridges.cognitive.consciousness_encoder import ConsciousnessBridgeEncoder
from bridges.cognitive.emotion_encoder import EmotionBridgeEncoder
from Silicon.core.bridges.geometric_fiber_encoder import GeometricFiberEncoder

from Silicon.core.octahedral_fiber_bundle import (
    OctahedralTorsor,
    Connection,
    HolonomyResult,
    compute_monodromy,
    classify_holonomy_around_regimes,
    compute_holonomy_group,
)


@dataclass(frozen=True)
class BridgeEntry:
    """Describes one bridge family and where its implementation lives."""

    name: str
    implementation_path: str
    role: str


BRIDGE_ENCODERS: Dict[str, Type] = {
    "sound": SoundBridgeEncoder,
    "electric": ElectricBridgeEncoder,
    "gravity": GravityBridgeEncoder,
    "magnetic": MagneticBridgeEncoder,
    "light": LightBridgeEncoder,
    "pressure": PressureBridgeEncoder,
    "thermal": ThermalBridgeEncoder,
    "wave": WaveBridgeEncoder,
    "chemical": ChemicalBridgeEncoder,
    "community": CommunityBridgeEncoder,
    "resilience": ResilienceBridgeEncoder,
    "geometric_fiber": GeometricFiberEncoder,
    "consciousness": ConsciousnessBridgeEncoder,
    "emotion": EmotionBridgeEncoder,
}

BRIDGE_CATALOG: Dict[str, BridgeEntry] = {
    "sound": BridgeEntry(
        name="sound",
        implementation_path="bridges.sound_encoder.SoundBridgeEncoder",
        role="Couples to pressure-wave structure in a compressible medium through phase, frequency, amplitude, and resonance behavior.",
    ),
    "electric": BridgeEntry(
        name="electric",
        implementation_path="bridges.electric_encoder.ElectricBridgeEncoder",
        role="Couples to charge flow and field behavior through conduction, skin depth, impedance, and threshold crossings.",
    ),
    "gravity": BridgeEntry(
        name="gravity",
        implementation_path="bridges.gravity_encoder.GravityBridgeEncoder",
        role="Couples to gravitational potential structure through curvature, tidal response, bound-state behavior, and balance points.",
    ),
    "magnetic": BridgeEntry(
        name="magnetic",
        implementation_path="bridges.magnetic_encoder.MagneticBridgeEncoder",
        role="Couples to magnetic field structure and comparative field geometry.",
    ),
    "light": BridgeEntry(
        name="light",
        implementation_path="bridges.light_encoder.LightBridgeEncoder",
        role="Couples to optical wavelength, intensity, and radiative field structure.",
    ),
    "pressure": BridgeEntry(
        name="pressure",
        implementation_path="bridges.pressure_encoder.PressureBridgeEncoder",
        role="Couples to pressure-state geometry and compressive field response.",
    ),
    "thermal": BridgeEntry(
        name="thermal",
        implementation_path="bridges.thermal_encoder.ThermalBridgeEncoder",
        role="Couples to thermal gradients, dissipation, and heat-flow structure.",
    ),
    "wave": BridgeEntry(
        name="wave",
        implementation_path="bridges.wave_encoder.WaveBridgeEncoder",
        role="Couples to generalized wave propagation, coherence, and interference structure.",
    ),
    "chemical": BridgeEntry(
        name="chemical",
        implementation_path="bridges.chemical_encoder.ChemicalBridgeEncoder",
        role="Couples to concentration, reactivity, and chemical-state transition structure.",
    ),
    "community": BridgeEntry(
        name="community",
        implementation_path="bridges.community_encoder.CommunityBridgeEncoder",
        role="Concrete human-organism and settlement-scale instantiation of the substrate-independent resilience bridge, coupling to thermodynamic population viability through reserves, redundancy, and resilience-domain structure.",
    ),
    "resilience": BridgeEntry(
        name="resilience",
        implementation_path="bridges.resilience_encoder.ResilienceBridgeEncoder",
        role="Substrate-independent resilience encoder for viability, reserves, cascade coupling, and sustainability-oriented mutual resilience across the shared six-axis model.",
    ),
    "geometric_fiber": BridgeEntry(
        name="geometric_fiber",
        implementation_path="Silicon.core.bridges.geometric_fiber_encoder.GeometricFiberEncoder",
        role="Detects whether a globally consistent physical-to-computational mapping exists by probing fiber transport and holonomy.",
    ),
    "consciousness": BridgeEntry(
        name="consciousness",
        implementation_path="bridges.cognitive.consciousness_encoder.ConsciousnessBridgeEncoder",
        role="Meta-layer encoder for consciousness-state structure and bridge-coupled internal state estimation.",
    ),
    "emotion": BridgeEntry(
        name="emotion",
        implementation_path="bridges.cognitive.emotion_encoder.EmotionBridgeEncoder",
        role="Meta-layer encoder for affective state geometry and cross-bridge resonance / drill-down guidance.",
    ),
}


def get_bridge_encoder(name: str):
    """Return the encoder class for a named bridge family."""
    key = name.strip().lower()
    if key not in BRIDGE_ENCODERS:
        raise KeyError(f"Unknown bridge encoder '{name}'. Available: {', '.join(sorted(BRIDGE_ENCODERS))}")
    return BRIDGE_ENCODERS[key]



def describe_bridge(name: str) -> BridgeEntry:
    """Return a human-readable catalog entry for a bridge family."""
    key = name.strip().lower()
    if key not in BRIDGE_CATALOG:
        raise KeyError(f"Unknown bridge description '{name}'. Available: {', '.join(sorted(BRIDGE_CATALOG))}")
    return BRIDGE_CATALOG[key]


__all__ = [
    "BridgeEntry",
    "BRIDGE_ENCODERS",
    "BRIDGE_CATALOG",
    "get_bridge_encoder",
    "describe_bridge",
    "SoundBridgeEncoder",
    "ElectricBridgeEncoder",
    "GravityBridgeEncoder",
    "MagneticBridgeEncoder",
    "LightBridgeEncoder",
    "PressureBridgeEncoder",
    "ThermalBridgeEncoder",
    "WaveBridgeEncoder",
    "ChemicalBridgeEncoder",
    "CommunityBridgeEncoder",
    "ResilienceBridgeEncoder",
    "GeometricFiberEncoder",
    "ConsciousnessBridgeEncoder",
    "EmotionBridgeEncoder",
    "OctahedralTorsor",
    "Connection",
    "HolonomyResult",
    "compute_monodromy",
    "classify_holonomy_around_regimes",
    "compute_holonomy_group",
]
