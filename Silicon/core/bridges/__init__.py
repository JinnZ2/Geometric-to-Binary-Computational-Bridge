"""Silicon bridge package.

Use this package as the navigation entry point when you are working from the
silicon layer and need either silicon-native bridge physics or adapters into
one of the top-level domain bridge encoders.
"""

from .adapters import (
    BridgeEntry,
    BRIDGE_ENCODERS,
    BRIDGE_CATALOG,
    get_bridge_encoder,
    describe_bridge,
    SoundBridgeEncoder,
    ElectricBridgeEncoder,
    GravityBridgeEncoder,
    CommunityBridgeEncoder,
    PressureBridgeEncoder,
    LightBridgeEncoder,
    MagneticBridgeEncoder,
    ThermalBridgeEncoder,
    WaveBridgeEncoder,
    ChemicalBridgeEncoder,
    ResilienceBridgeEncoder,
    OctahedralTorsor,
    Connection,
    HolonomyResult,
    compute_monodromy,
    classify_holonomy_around_regimes,
    compute_holonomy_group,
)

from .domain_bridge_catalog import DomainBridgeRecord, DOMAIN_BRIDGES
from .fret_coulomb_analysis import *
from .gies_encoder import *
from .hardware_bridge import *
from .magnetic_bridge_protocol import *
from .pipeline import *
from .silicon_gies_bridge import *

__all__ = [
    "BridgeEntry",
    "BRIDGE_ENCODERS",
    "BRIDGE_CATALOG",
    "DomainBridgeRecord",
    "DOMAIN_BRIDGES",
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
