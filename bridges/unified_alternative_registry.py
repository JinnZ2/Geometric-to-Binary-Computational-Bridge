# bridges/unified_alternative_registry.py
"""
Unified Alternative Paradigm Registry
======================================
Maps each alternative computing paradigm to the encoder domains
where it recovers information that binary encoding compresses.

This is the "computational epistemology layer" over the hardware
encoders—each paradigm is a different way of knowing what the
physical system is actually doing.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Callable, Any

class AlternativeParadigm(Enum):
    TERNARY = "ternary"           # Three-valued logic
    QUANTUM = "quantum"           # Superposition & measurement
    STOCHASTIC = "stochastic"     # Probability streams
    NEUROMORPHIC = "neuromorphic" # Spike-based, event-driven
    RESERVOIR = "reservoir"       # Dynamical systems, echo state
    MEMRISTIVE = "memristive"     # Hysteresis, state-as-history
    APPROXIMATE = "approximate"   # Low-precision, confidence-bound

@dataclass
class ParadigmEncoderMapping:
    """Maps a paradigm to the encoder domains where it applies."""
    paradigm: AlternativeParadigm
    primary_encoders: List[str]     # Encoder names where this paradigm shines
    recovery_function: str          # Function name that wraps the encoder
    what_it_recovers: str           # What binary encoding erases
    axis: str                       # Which axis this addresses

# Complete mapping of all seven paradigms across all encoders
PARADIGM_REGISTRY: Dict[str, List[ParadigmEncoderMapping]] = {
    "ternary": [
        ParadigmEncoderMapping(
            AlternativeParadigm.TERNARY,
            ["SoundBridgeEncoder", "GravityBridgeEncoder", "ElectricBridgeEncoder"],
            "classify_phase_ternary / classify_gravity_ternary / classify_current_ternary",
            "Binary sign bits erase the physically distinct ZERO/EQUILIBRIUM state",
            "State Representation (binary → ternary)"
        ),
    ],
    "quantum": [
        ParadigmEncoderMapping(
            AlternativeParadigm.QUANTUM,
            ["SoundBridgeEncoder", "GravityBridgeEncoder", "ElectricBridgeEncoder"],
            "QuantumHarmonicSuperposition / QuantumOrbitalStability / QuantumSkinEffect",
            "Binary thresholding collapses continuous superpositions into false dichotomies",
            "State Representation (ternary → quantum amplitude)"
        ),
    ],
    "stochastic": [
        ParadigmEncoderMapping(
            AlternativeParadigm.STOCHASTIC,
            ["SoundBridgeEncoder", "ElectricBridgeEncoder", "CommunityBridgeEncoder"],
            "StochasticJitterPreservation / StochasticContactResistance / StochasticEnergyReserve",
            "Binary declares probability distributions as point estimates",
            "State Representation (probabilistic)"
        ),
    ],
    "neuromorphic": [
        ParadigmEncoderMapping(
            AlternativeParadigm.NEUROMORPHIC,
            ["SoundBridgeEncoder", "ElectricBridgeEncoder"],
            "NeuromorphicEncoding.from_samples",
            "Binary treats time-series as independent frames; spikes carry temporal structure",
            "Execution Model (parallel → event-driven)"
        ),
    ],
    "reservoir": [
        ParadigmEncoderMapping(
            AlternativeParadigm.RESERVOIR,
            ["All encoders simultaneously"],
            "ReservoirNetwork.build_from_geometry",
            "Binary processes domains independently; reservoir couples all dynamics",
            "Execution Model (event-driven → dynamical)"
        ),
    ],
    "memristive": [
        ParadigmEncoderMapping(
            AlternativeParadigm.MEMRISTIVE,
            ["ElectricBridgeEncoder"],  # scope: conductivity sub-domain
            "MemristiveTrace.from_measurements",
            "Binary reads instantaneous state; memristor state IS its history",
            "Memory Coupling (co-located → intrinsic)"
        ),
    ],
    "approximate": [
        ParadigmEncoderMapping(
            AlternativeParadigm.APPROXIMATE,
            ["CommunityBridgeEncoder", "ElectricBridgeEncoder"],
            "ApproximateInstitutionalRedundancy / ApproximateTAF.infer_q_factor",
            "Binary demands exact thresholds; approximate gives confidence intervals",
            "State Representation (ternary → probabilistic → continuous)"
        ),
    ],
}

def get_applicable_paradigms(encoder_name: str) -> List[ParadigmEncoderMapping]:
    """Get all alternative paradigms applicable to a given encoder."""
    applicable = []
    for paradigm_name, mappings in PARADIGM_REGISTRY.items():
        for mapping in mappings:
            if encoder_name in mapping.primary_encoders or "All encoders" in mapping.primary_encoders:
                applicable.append(mapping)
    return applicable

def print_paradigm_matrix():
    """Print the complete paradigm × encoder applicability matrix."""
    encoders = [
        "SoundBridgeEncoder",
        "GravityBridgeEncoder", 
        "ElectricBridgeEncoder",
        "CommunityBridgeEncoder",
    ]
    
    paradigms = [p.value for p in AlternativeParadigm]
    
    # Header
    print(f"{'Paradigm':<15}", end="")
    for enc in encoders:
        print(f"{enc:<25}", end="")
    print()
    print("-" * (15 + 25 * len(encoders)))
    
    for paradigm in paradigms:
        print(f"{paradigm:<15}", end="")
        for enc in encoders:
            applicable = get_applicable_paradigms(enc)
            matches = [m for m in applicable if m.paradigm.value == paradigm]
            marker = "✓" if matches else "·"
            print(f"{marker:<25}", end="")
        print()

if __name__ == "__main__":
    print("=" * 60)
    print("Alternative Paradigm × Encoder Matrix")
    print("=" * 60)
    print_paradigm_matrix()
    
    print("\n" + "=" * 60)
    print("Paradigm Recovery Summary")
    print("=" * 60)
    for paradigm_name, mappings in PARADIGM_REGISTRY.items():
        for m in mappings:
            print(f"\n{m.paradigm.value.upper()} → {', '.join(m.primary_encoders)}")
            print(f"  Function: {m.recovery_function}")
            print(f"  Recovers: {m.what_it_recovers}")
            print(f"  Axis: {m.axis}")
