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
    "community": CommunityBridgeEncoder,
    "pressure": PressureBridgeEncoder,
    "light": LightBridgeEncoder,
    "magnetic": MagneticBridgeEncoder,
    "thermal": ThermalBridgeEncoder,
    "wave": WaveBridgeEncoder,
    "chemical": ChemicalBridgeEncoder,
    "resilience": ResilienceBridgeEncoder,
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
        implementation_path="Silicon.core.octahedral_fiber_bundle",
        role="Detects whether a globally consistent physical-to-computational mapping exists by probing fiber transport and holonomy.",
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
    "CommunityBridgeEncoder",
    "PressureBridgeEncoder",
    "LightBridgeEncoder",
    "MagneticBridgeEncoder",
    "ThermalBridgeEncoder",
    "WaveBridgeEncoder",
    "ChemicalBridgeEncoder",
    "ResilienceBridgeEncoder",
    "OctahedralTorsor",
    "Connection",
    "HolonomyResult",
    "compute_monodromy",
    "classify_holonomy_around_regimes",
    "compute_holonomy_group",
]
