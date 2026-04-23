"""
Binary adapter — thin wrapper over existing BinaryBridgeEncoder subclasses.

Exists so the dual-path pipeline can call ``adapter.encode(geometry)``
without caring which concrete encoder class implements the domain.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from bridges.abstract_encoder import BinaryBridgeEncoder


# Lazy registry of domain name → encoder class. Each entry is resolved
# on first use so that domains without an installed encoder do not
# trigger ImportError on module load.
_ENCODER_REGISTRY: Dict[str, str] = {
    "electric":   "bridges.electric_encoder:ElectricBridgeEncoder",
    "magnetic":   "bridges.magnetic_encoder:MagneticBridgeEncoder",
    "light":      "bridges.light_encoder:LightBridgeEncoder",
    "sound":      "bridges.sound_encoder:SoundBridgeEncoder",
    "gravity":    "bridges.gravity_encoder:GravityBridgeEncoder",
    "wave":       "bridges.wave_encoder:WaveBridgeEncoder",
    "thermal":    "bridges.thermal_encoder:ThermalBridgeEncoder",
    "pressure":   "bridges.pressure_encoder:PressureBridgeEncoder",
    "chemical":   "bridges.chemical_encoder:ChemicalBridgeEncoder",
    "consciousness": "bridges.cognitive.consciousness_encoder:ConsciousnessBridgeEncoder",
    "emotion":       "bridges.cognitive.emotion_encoder:EmotionBridgeEncoder",
}


def _resolve(spec: str) -> Type[BinaryBridgeEncoder]:
    module_name, _, class_name = spec.partition(":")
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


class BinaryAdapter:
    """
    Wrap a ``BinaryBridgeEncoder`` so it is callable via ``encode(geometry)``.

    Parameters
    ----------
    domain
        Registered domain name (see ``_ENCODER_REGISTRY``).
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
            if domain not in _ENCODER_REGISTRY:
                raise KeyError(
                    f"Unknown binary domain {domain!r}. "
                    f"Known: {sorted(_ENCODER_REGISTRY)}"
                )
            encoder_cls = _resolve(_ENCODER_REGISTRY[domain])

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


__all__ = ["BinaryAdapter"]
