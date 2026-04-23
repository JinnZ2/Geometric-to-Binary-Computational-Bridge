"""
Alternative adapter — wraps ternary / stochastic / quantum interpreters.

Each domain's alternative compute module exports a top-level
diagnostic function (e.g. ``electric_full_alternative_diagnostic``)
that maps a geometry dict to a domain-specific diagnostic object.
This adapter hides the naming and import details behind a uniform
``encode(geometry, frequency_hz=None)`` call.

Domains that do not yet have an alternative interpreter are left
registered with ``None`` so the dispatcher can emit a clear error
rather than failing on an unrelated ImportError.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


# domain → "<module>:<function>" or None when not yet implemented
_ALTERNATIVE_REGISTRY: Dict[str, Optional[str]] = {
    "electric":  "bridges.electric_alternative_compute:electric_full_alternative_diagnostic",
    "sound":     "bridges.sound_alternative_compute:sound_full_alternative_diagnostic",
    "gravity":   "bridges.gravity_alternative_compute:gravity_full_alternative_diagnostic",
    # Not yet implemented — will raise NotImplementedError from dispatcher.
    "magnetic":      None,
    "light":         None,
    "wave":          None,
    "thermal":       None,
    "pressure":      None,
    "chemical":      None,
    "consciousness": None,
    "emotion":       None,
}


def _resolve(spec: str) -> Callable[..., Any]:
    module_name, _, func_name = spec.partition(":")
    module = __import__(module_name, fromlist=[func_name])
    return getattr(module, func_name)


def _try_resolve(domain: str) -> Optional[Callable[..., Any]]:
    """
    Resolve a diagnostic function for ``domain``.

    Returns ``None`` if the domain has no registered alternative
    interpreter, or if the registered module fails to import (some
    ``*_alternative_compute`` modules expose variant factory names;
    those are handled by best-effort name probing below).
    """
    spec = _ALTERNATIVE_REGISTRY.get(domain)
    if spec is not None:
        try:
            return _resolve(spec)
        except (ImportError, AttributeError):
            pass

    # Best-effort probe: domain may expose a diagnostic under a
    # different name convention.
    module_name = f"bridges.{domain}_alternative_compute"
    candidates = [
        f"{domain}_full_alternative_diagnostic",
        f"{domain}_alternative_diagnostic",
        "full_alternative_diagnostic",
        "diagnose",
    ]
    try:
        module = __import__(module_name, fromlist=candidates)
    except ImportError:
        return None
    for name in candidates:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    return None


class AlternativeAdapter:
    """
    Wrap a domain's alternative interpreter as ``encode(geometry, **kw)``.

    Parameters
    ----------
    domain
        Registered domain name.
    diagnostic_fn
        Explicit override of the resolved function; mainly for tests.
    """

    def __init__(
        self,
        domain: str,
        diagnostic_fn: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.domain = domain
        self._fn = diagnostic_fn or _try_resolve(domain)

    @property
    def is_available(self) -> bool:
        """True when a concrete interpreter has been resolved."""
        return self._fn is not None

    def encode(
        self,
        geometry: Dict[str, Any],
        frequency_hz: Optional[float] = None,
        **extra: Any,
    ) -> Any:
        """
        Run the alternative interpreter and return its diagnostic object.

        Raises
        ------
        NotImplementedError
            If the domain has no registered alternative interpreter.
        """
        if self._fn is None:
            raise NotImplementedError(
                f"No alternative interpreter registered for domain "
                f"{self.domain!r}. Add an entry to "
                f"bridges.adapters.ternary_adapter._ALTERNATIVE_REGISTRY "
                f"once the module is implemented."
            )

        # Only pass frequency_hz when the underlying function accepts it.
        # Every alternative module currently follows the
        # ``<fn>(geometry, frequency_hz=None)`` convention; tolerate
        # simpler signatures for future additions.
        try:
            return self._fn(geometry, frequency_hz=frequency_hz, **extra)
        except TypeError:
            return self._fn(geometry, **extra)


__all__ = ["AlternativeAdapter"]
