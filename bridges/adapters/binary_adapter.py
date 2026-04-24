"""
Binary adapter — thin wrapper over existing BinaryBridgeEncoder subclasses.

The set of known domains is resolved dynamically from
``Silicon.core.bridges.adapters.BRIDGE_ENCODERS``, which is the
repo's canonical source of truth for registered encoders. That map
already covers all 18 domains the solver_registry and bridge_contract
manifest know about, so we inherit additions (biomachine, community,
coop, cyclic, resilience, vortex, geometric_fiber, ...) for free.

Exists so the dual-path pipeline can call ``adapter.encode(geometry)``
without caring which concrete encoder class implements the domain.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from bridges.abstract_encoder import BinaryBridgeEncoder


def _silicon_encoders() -> Dict[str, Type[BinaryBridgeEncoder]]:
    """
    Return the canonical domain → encoder-class map from the silicon layer.

    Isolated in a function so import-time failures in the silicon layer
    do not sink this module. Callers that hit an ImportError fall back
    to :data:`_FALLBACK_REGISTRY` below.
    """
    from Silicon.core.bridges.adapters import BRIDGE_ENCODERS

    return dict(BRIDGE_ENCODERS)


# Last-resort registry used when the silicon layer cannot be imported
# (e.g. minimal test environments). Kept intentionally small — the
# silicon layer is the authoritative list.
_FALLBACK_REGISTRY: Dict[str, str] = {
    "electric":      "bridges.electric_encoder:ElectricBridgeEncoder",
    "magnetic":      "bridges.magnetic_encoder:MagneticBridgeEncoder",
    "light":         "bridges.light_encoder:LightBridgeEncoder",
    "sound":         "bridges.sound_encoder:SoundBridgeEncoder",
    "gravity":       "bridges.gravity_encoder:GravityBridgeEncoder",
    "wave":          "bridges.wave_encoder:WaveBridgeEncoder",
    "thermal":       "bridges.thermal_encoder:ThermalBridgeEncoder",
    "pressure":      "bridges.pressure_encoder:PressureBridgeEncoder",
    "chemical":      "bridges.chemical_encoder:ChemicalBridgeEncoder",
    "consciousness": "bridges.cognitive.consciousness_encoder:ConsciousnessBridgeEncoder",
    "emotion":       "bridges.cognitive.emotion_encoder:EmotionBridgeEncoder",
}


def _resolve_fallback(spec: str) -> Type[BinaryBridgeEncoder]:
    module_name, _, class_name = spec.partition(":")
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def known_domains() -> List[str]:
    """Return every domain name the binary adapter can resolve."""
    try:
        return sorted(_silicon_encoders())
    except ImportError:
        return sorted(_FALLBACK_REGISTRY)


def _resolve_encoder(domain: str) -> Type[BinaryBridgeEncoder]:
    """Resolve ``domain`` to its encoder class via silicon, else fallback."""
    try:
        encoders = _silicon_encoders()
    except ImportError:
        encoders = None

    if encoders is not None and domain in encoders:
        return encoders[domain]

    if domain in _FALLBACK_REGISTRY:
        return _resolve_fallback(_FALLBACK_REGISTRY[domain])

    known = known_domains()
    raise KeyError(
        f"Unknown binary domain {domain!r}. Known: {known}"
    )


class BinaryAdapter:
    """
    Wrap a ``BinaryBridgeEncoder`` so it is callable via ``encode(geometry)``.

    Parameters
    ----------
    domain
        Registered domain name. Resolved against
        ``Silicon.core.bridges.adapters.BRIDGE_ENCODERS`` first, falling
        back to the minimal local registry if the silicon layer is
        unavailable.
    encoder_cls
        Override the class resolved from the registry. Useful for tests
        and for custom downstream bridges.
    encoder_kwargs
        Keyword arguments passed to the encoder constructor.
    """

    def __init__(
        self,
        domain: str,
        encoder_cls: Optional[Type[BinaryBridgeEncoder]] = None,
        encoder_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.domain = domain
        self._encoder_kwargs = encoder_kwargs or {}

        if encoder_cls is None:
            encoder_cls = _resolve_encoder(domain)

        self._encoder_cls = encoder_cls

    def encode(self, geometry: Dict[str, Any], **_: Any) -> str:
        """Return the binary bitstring for ``geometry``."""
        encoder = self._encoder_cls(**self._encoder_kwargs)
        encoder.from_geometry(geometry)
        return encoder.to_binary()

    def report(self, geometry: Dict[str, Any]) -> Dict[str, Any]:
        """Return the encoder's standard report dict after encoding."""
        encoder = self._encoder_cls(**self._encoder_kwargs)
        encoder.from_geometry(geometry)
        encoder.to_binary()
        return encoder.report()


# ---------------------------------------------------------------------------
# Back-compat alias — older callers import _ENCODER_REGISTRY directly.
# ---------------------------------------------------------------------------
# The integration_pipeline previously imported this name to enumerate
# domains. Exposing ``known_domains()`` via a dict-shaped facade keeps
# that import working without freezing the domain set.
class _EncoderRegistryFacade:
    """Dict-shaped view over the live encoder registry."""

    def __contains__(self, domain: str) -> bool:
        try:
            return domain in _silicon_encoders()
        except ImportError:
            return domain in _FALLBACK_REGISTRY

    def __iter__(self):
        return iter(known_domains())

    def __len__(self) -> int:
        return len(known_domains())

    def keys(self):
        return known_domains()


_ENCODER_REGISTRY = _EncoderRegistryFacade()


__all__ = [
    "BinaryAdapter",
    "known_domains",
    "_ENCODER_REGISTRY",
]
