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
    ConsciousnessBridgeEncoder,
    EmotionBridgeEncoder,
    OctahedralTorsor,
    Connection,
    HolonomyResult,
    compute_monodromy,
    classify_holonomy_around_regimes,
    compute_holonomy_group,
)

from .domain_bridge_catalog import DomainBridgeRecord, DOMAIN_BRIDGES
from .geometric_fiber_encoder import GeometricFiberEncoder, encode_fiber_bundle_topology
from .hardware_modules import (
    HardwareModuleEntry,
    HARDWARE_MODULES,
    list_hardware_modules,
    choose_hardware_modules,
)

# Re-export everything from the silicon-native modules at the package
# root so callers can do ``from Silicon.core.bridges import X``. Star
# imports are the canonical Python pattern for package re-exports; the
# noqa silences ruff's F403 (which is a style warning for non-package
# code, not a bug indicator here).
from .fret_coulomb_analysis import *       # noqa: F403
from .gies_encoder import *                 # noqa: F403
from .hardware_bridge import *              # noqa: F403
from .magnetic_bridge_protocol import *     # noqa: F403
from .pipeline import *                     # noqa: F403
from .silicon_gies_bridge import *          # noqa: F403

__all__ = [
    "BridgeEntry",
    "BRIDGE_ENCODERS",
    "BRIDGE_CATALOG",
    "DomainBridgeRecord",
    "DOMAIN_BRIDGES",
    "HardwareModuleEntry",
    "HARDWARE_MODULES",
    "list_hardware_modules",
    "choose_hardware_modules",
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
    "GeometricFiberEncoder",
    "ConsciousnessBridgeEncoder",
    "EmotionBridgeEncoder",
    "encode_fiber_bundle_topology",
    "OctahedralTorsor",
    "Connection",
    "HolonomyResult",
    "compute_monodromy",
    "classify_holonomy_around_regimes",
    "compute_holonomy_group",
]
