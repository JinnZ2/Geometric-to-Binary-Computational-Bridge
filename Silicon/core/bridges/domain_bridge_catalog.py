"""Catalog of bridge families available to the silicon layer.

This file is intentionally documentation-oriented: it gives one stable place
where readers can see which bridge concept maps to which implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DomainBridgeRecord:
    name: str
    coupling_model: str
    top_level_module: str
    silicon_entry_point: str


DOMAIN_BRIDGES: List[DomainBridgeRecord] = [
    DomainBridgeRecord(
        name="sound",
        coupling_model="Couples to pressure-wave structure in a compressible medium through phase, frequency, amplitude, and resonance.",
        top_level_module="bridges.sound_encoder.SoundBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.SoundBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="electric",
        coupling_model="Couples to charge flow and electromagnetic state through conduction, impedance, skin depth, and threshold crossings.",
        top_level_module="bridges.electric_encoder.ElectricBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.ElectricBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="gravity",
        coupling_model="Couples to gravitational potential structure through curvature, bound states, tidal response, and balance conditions.",
        top_level_module="bridges.gravity_encoder.GravityBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.GravityBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="community",
        coupling_model="Couples to thermodynamic population viability through reserves, redundancy, knowledge continuity, and institutional resilience.",
        top_level_module="bridges.community_encoder.CommunityBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.CommunityBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="geometric_fiber",
        coupling_model="Detects whether a globally consistent physical-to-computational mapping exists by measuring fiber transport and holonomy.",
        top_level_module="Silicon.core.octahedral_fiber_bundle",
        silicon_entry_point="Silicon.core.bridges.adapters.trace_closed_loop",
    ),
]


__all__ = ["DomainBridgeRecord", "DOMAIN_BRIDGES"]
