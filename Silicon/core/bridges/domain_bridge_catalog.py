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
        name="magnetic",
        coupling_model="Couples to magnetic field structure and comparative field geometry.",
        top_level_module="bridges.magnetic_encoder.MagneticBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.MagneticBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="light",
        coupling_model="Couples to optical wavelength, intensity, and radiative field structure.",
        top_level_module="bridges.light_encoder.LightBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.LightBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="pressure",
        coupling_model="Couples to pressure-state geometry and compressive field response.",
        top_level_module="bridges.pressure_encoder.PressureBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.PressureBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="thermal",
        coupling_model="Couples to thermal gradients, dissipation, and heat-flow structure.",
        top_level_module="bridges.thermal_encoder.ThermalBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.ThermalBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="wave",
        coupling_model="Couples to generalized wave propagation, coherence, and interference structure.",
        top_level_module="bridges.wave_encoder.WaveBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.WaveBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="chemical",
        coupling_model="Couples to concentration, reactivity, and chemical-state transition structure.",
        top_level_module="bridges.chemical_encoder.ChemicalBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.ChemicalBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="community",
        coupling_model="Couples to thermodynamic population viability through reserves, redundancy, knowledge continuity, and institutional resilience.",
        top_level_module="bridges.community_encoder.CommunityBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.CommunityBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="resilience",
        coupling_model="Substrate-independent resilience geometry spanning viability, reserves, spillover, and mutual resilience across axes.",
        top_level_module="bridges.resilience_encoder.ResilienceBridgeEncoder",
        silicon_entry_point="Silicon.core.bridges.adapters.ResilienceBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="geometric_fiber",
        coupling_model="Detects whether a globally consistent physical-to-computational mapping exists by measuring fiber transport and holonomy.",
        top_level_module="Silicon.core.bridges.geometric_fiber_encoder.GeometricFiberEncoder",
        silicon_entry_point="Silicon.core.bridges.geometric_fiber_encoder.GeometricFiberEncoder",
    ),
    DomainBridgeRecord(
        name="consciousness",
        coupling_model="Encodes consciousness-state structure as a bridge-aware meta-layer over the physical and contextual bridge families.",
        top_level_module="bridges.cognitive.consciousness_encoder.ConsciousnessBridgeEncoder",
        silicon_entry_point="bridges.cognitive.consciousness_encoder.ConsciousnessBridgeEncoder",
    ),
    DomainBridgeRecord(
        name="emotion",
        coupling_model="Encodes emotional-state geometry and cross-bridge resonance as a bridge-aware meta-layer over the physical and contextual bridge families.",
        top_level_module="bridges.cognitive.emotion_encoder.EmotionBridgeEncoder",
        silicon_entry_point="bridges.cognitive.emotion_encoder.EmotionBridgeEncoder",
    ),
]


__all__ = ["DomainBridgeRecord", "DOMAIN_BRIDGES"]
