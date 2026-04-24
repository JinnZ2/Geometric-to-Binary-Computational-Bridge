"""
Alternative adapter — wraps every registered non-binary interpretation paradigm.

Seven paradigms are catalogued in
``bridges/unified_alternative_registry.py``. Each one recovers a
different slice of the information the binary encoder compresses
away. This module makes them dispatchable through a uniform
``adapter.encode(geometry)`` call so downstream code does not need
to special-case the paradigm.

Two families of paradigms
-------------------------
1. **Per-domain diagnostics.** ``ternary`` / ``quantum`` / ``stochastic``
   are all served by the same ``<domain>_full_alternative_diagnostic``
   function for a given domain. The resulting
   :class:`~bridges.electric_alternative_compute.ElectricAlternativeDiagnostic`
   (and its sound/gravity siblings) already bundles the ternary, quantum,
   and stochastic analyses — so the adapter picks the domain-specific
   function via ``domain`` and returns the unified diagnostic.

2. **Cross-domain paradigms.** ``neuromorphic``, ``memristive``,
   ``reservoir``, and ``approximate`` are *not* per-domain — they wrap
   any compatible geometry dict. The adapter routes these through the
   relevant top-level ``<paradigm>_wrap_*`` function and normalises the
   input shape so the standard geometry dict works unchanged.

Domains that do not yet have a diagnostic for family 1 raise
``NotImplementedError``; all domains are supported for family 2
(the input shape is paradigm-defined, not domain-defined).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Family 1: per-domain ternary/quantum/stochastic diagnostics
# ---------------------------------------------------------------------------

# domain → "<module>:<function>" or None when not yet implemented
_ALTERNATIVE_REGISTRY: Dict[str, Optional[str]] = {
    "electric":  "bridges.electric_alternative_compute:electric_full_alternative_diagnostic",
    "sound":     "bridges.sound_alternative_compute:sound_full_alternative_diagnostic",
    "gravity":   "bridges.gravity_alternative_compute:gravity_full_alternative_diagnostic",
    "community": "bridges.community_alternative_compute:community_alternative_diagnostic",
    # Not yet implemented — will raise NotImplementedError from dispatcher.
    "magnetic":       None,
    "light":          None,
    "wave":           None,
    "thermal":        None,
    "pressure":       None,
    "chemical":       None,
    "consciousness":  None,
    "emotion":        None,
    "biomachine":     None,
    "coop":           None,
    "cyclic":         None,
    "resilience":     None,
    "vortex":         None,
    "geometric_fiber": None,
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


# ---------------------------------------------------------------------------
# Family 2: cross-domain paradigms
# ---------------------------------------------------------------------------

def _run_neuromorphic(
    geometry: Dict[str, Any],
    threshold: Optional[float] = None,
    **_: Any,
) -> Any:
    """
    Route ``geometry`` through the spike-based interpreter.

    Only list-valued keys are passed to ``neuromorphic_wrap_encoder``
    so auxiliary metadata (scalars, strings) does not corrupt the
    per-channel spike trains.
    """
    from bridges.neuromorphic_bridge import neuromorphic_wrap_encoder

    list_channels: Dict[str, List[float]] = {
        k: list(v) for k, v in geometry.items()
        if isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v)
    }
    return neuromorphic_wrap_encoder(list_channels, threshold=threshold)


def _run_memristive(
    geometry: Dict[str, Any],
    **_: Any,
) -> Any:
    """
    Route conductivity measurements through the memristive interpreter.

    Pulls ``conductivity_S`` (the electric-bridge canonical key) plus
    optional ``voltage_V`` and ``current_A`` histories. Geometries
    without a conductivity list raise ``ValueError`` with a clear hint.
    """
    from bridges.memristive_bridge import memristive_wrap_conductivity

    conductivity = geometry.get("conductivity_S")
    if not conductivity:
        raise ValueError(
            "Memristive paradigm requires 'conductivity_S' (list of floats) "
            "in geometry. Got keys: " + str(sorted(geometry))
        )
    return memristive_wrap_conductivity(
        list(conductivity),
        voltage=list(geometry.get("voltage_V") or []) or None,
        current=list(geometry.get("current_A") or []) or None,
    )


def _run_reservoir(
    geometry: Dict[str, Any],
    domain: str = "electric",
    **_: Any,
) -> Any:
    """
    Route a single-domain geometry through the reservoir as a singleton.

    For multi-domain reservoirs (the intended use — gravity ↔ electric
    ↔ sound coupling), call ``bridges.reservoir_bridge.reservoir_wrap_geometries``
    directly with ``{domain: geometry, ...}``.
    """
    from bridges.reservoir_bridge import reservoir_wrap_geometries

    return reservoir_wrap_geometries({domain: geometry})


_PARADIGM_DISPATCH: Dict[str, Callable[..., Any]] = {
    "neuromorphic": _run_neuromorphic,
    "memristive":   _run_memristive,
    "reservoir":    _run_reservoir,
}


PER_DOMAIN_PARADIGMS = frozenset({"ternary", "quantum", "stochastic"})
CROSS_DOMAIN_PARADIGMS = frozenset(_PARADIGM_DISPATCH)
ALL_PARADIGMS = PER_DOMAIN_PARADIGMS | CROSS_DOMAIN_PARADIGMS


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class AlternativeAdapter:
    """
    Wrap a domain's alternative interpreter as ``encode(geometry, **kw)``.

    Parameters
    ----------
    domain
        Registered domain name (used by per-domain paradigms).
    paradigm
        One of ``"ternary"``, ``"quantum"``, ``"stochastic"``,
        ``"neuromorphic"``, ``"memristive"``, ``"reservoir"``.
        Defaults to ``"ternary"`` which preserves the previous
        behaviour of this class.
    diagnostic_fn
        Explicit override of the resolved function for per-domain
        paradigms; mainly for tests.
    """

    def __init__(
        self,
        domain: str,
        paradigm: str = "ternary",
        diagnostic_fn: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.domain = domain
        self.paradigm = paradigm

        if paradigm in CROSS_DOMAIN_PARADIGMS:
            self._fn = _PARADIGM_DISPATCH[paradigm]
            self._is_cross_domain = True
        elif paradigm in PER_DOMAIN_PARADIGMS:
            self._fn = diagnostic_fn or _try_resolve(domain)
            self._is_cross_domain = False
        else:
            raise ValueError(
                f"Unknown paradigm {paradigm!r}. "
                f"Known: {sorted(ALL_PARADIGMS)}"
            )

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
            If the paradigm is per-domain and the domain has no
            registered diagnostic function.
        """
        if self._fn is None:
            raise NotImplementedError(
                f"No {self.paradigm!r} interpreter registered for domain "
                f"{self.domain!r}. Add an entry to "
                f"bridges.adapters.ternary_adapter._ALTERNATIVE_REGISTRY "
                f"once the module is implemented."
            )

        if self._is_cross_domain:
            # Cross-domain paradigms ignore frequency_hz — it is
            # irrelevant to their semantics — but forward the domain
            # name so paradigm-specific helpers can use it.
            return self._fn(geometry, domain=self.domain, **extra)

        # Per-domain paradigms follow the ``fn(geometry, frequency_hz=None)``
        # convention. Tolerate simpler signatures for future additions.
        try:
            return self._fn(geometry, frequency_hz=frequency_hz, **extra)
        except TypeError:
            return self._fn(geometry, **extra)


__all__ = [
    "AlternativeAdapter",
    "PER_DOMAIN_PARADIGMS",
    "CROSS_DOMAIN_PARADIGMS",
    "ALL_PARADIGMS",
]
