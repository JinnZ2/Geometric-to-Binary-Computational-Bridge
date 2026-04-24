"""
encode_state — unified dispatcher for binary / ternary / dual / paradigm encoding
=================================================================================

The single entry point for the branch-point architecture described in
``alternative_computing_bridge.md`` and ``alternative_computing_integration_schedule.md``.

Modes
-----
Seven alternative paradigms (plus the original binary path and a dual
combination) are dispatchable here. Paradigm selection is orthogonal to
domain selection:

  binary                                  → run the registered binary encoder
  ternary / alternative / stochastic /    → per-domain ternary+quantum+stochastic
    quantum                                 diagnostic (ElectricAlternativeDiagnostic, etc.)
  neuromorphic                            → spike-based interpretation of every
                                             list-valued channel in geometry
  memristive                              → hysteretic trace of conductivity/
                                             voltage/current histories
  reservoir                               → single-domain reservoir network
                                             (for multi-domain reservoirs, use
                                             bridges.reservoir_bridge.reservoir_wrap_geometries
                                             directly)
  dual / both / merge                     → return {"binary": ..., "alternative": ...}

Domains without a registered interpreter for the selected paradigm
raise ``NotImplementedError``. Binary always works for every registered
encoder.

Examples
--------
>>> encode_state({"charge": [1e-6]}, domain="electric", mode="binary")
'1111'
>>> diag = encode_state({"charge": [1e-6]}, domain="electric", mode="ternary")
>>> type(diag).__name__
'ElectricAlternativeDiagnostic'
>>> encoding = encode_state(
...     {"current_A": [0.5, -0.5, 0.0, 0.3]},
...     domain="electric", mode="neuromorphic",
... )
>>> type(encoding).__name__
'NeuromorphicEncoding'
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from bridges.adapters import AlternativeAdapter, BinaryAdapter
from bridges.adapters.ternary_adapter import (
    ALL_PARADIGMS,
    CROSS_DOMAIN_PARADIGMS,
    PER_DOMAIN_PARADIGMS,
)


# Mode alias → (bucket, paradigm).  "bucket" picks the top-level
# control-flow branch below; "paradigm" selects which alternative
# interpreter runs when the bucket is "alternative".
_MODE_ALIASES: Dict[str, tuple] = {
    # binary
    "binary": ("binary", None),
    "bin":    ("binary", None),
    "b":      ("binary", None),

    # per-domain alternative family
    "ternary":     ("alternative", "ternary"),
    "alternative": ("alternative", "ternary"),
    "alt":         ("alternative", "ternary"),
    "stochastic":  ("alternative", "stochastic"),
    "quantum":     ("alternative", "quantum"),

    # cross-domain paradigms
    "neuromorphic": ("alternative", "neuromorphic"),
    "spike":        ("alternative", "neuromorphic"),
    "memristive":   ("alternative", "memristive"),
    "memristor":    ("alternative", "memristive"),
    "reservoir":    ("alternative", "reservoir"),
    "echo":         ("alternative", "reservoir"),

    # dual
    "dual":  ("dual", "ternary"),
    "both":  ("dual", "ternary"),
    "merge": ("dual", "ternary"),
}


def _resolve_mode(mode: str) -> tuple:
    key = mode.lower().strip()
    if key not in _MODE_ALIASES:
        raise ValueError(
            f"Unknown encoding mode {mode!r}. "
            f"Known: {sorted(set(_MODE_ALIASES))}"
        )
    return _MODE_ALIASES[key]


def binary_encode(geometry: Dict[str, Any], domain: str = "electric") -> str:
    """Shortcut: run the registered binary encoder for ``domain``."""
    return BinaryAdapter(domain).encode(geometry)


def alternative_encode(
    geometry: Dict[str, Any],
    domain: str = "electric",
    paradigm: str = "ternary",
    frequency_hz: Optional[float] = None,
    **extra: Any,
) -> Any:
    """
    Shortcut: run a named alternative paradigm for ``domain``.

    ``paradigm`` must be one of :data:`~bridges.adapters.ternary_adapter.ALL_PARADIGMS`.
    Per-domain paradigms use ``frequency_hz``; cross-domain paradigms
    ignore it.
    """
    return AlternativeAdapter(domain, paradigm=paradigm).encode(
        geometry, frequency_hz=frequency_hz, **extra
    )


def encode_state(
    geometry: Dict[str, Any],
    domain: str = "electric",
    mode: str = "binary",
    frequency_hz: Optional[float] = None,
    **extra: Any,
) -> Any:
    """
    Dispatch ``geometry`` to the requested interpreter(s).

    Parameters
    ----------
    geometry
        Input geometry dict (domain-specific schema for binary and
        per-domain paradigms; paradigm-specific for neuromorphic /
        memristive / reservoir).
    domain
        Domain key — see :func:`bridges.adapters.binary_adapter.known_domains`.
    mode
        ``"binary"``            → return bitstring.
        ``"ternary"`` / ``"alternative"`` / ``"stochastic"`` / ``"quantum"``
                                → return the domain diagnostic object
                                  (all three share the same diagnostic type;
                                  the dataclass exposes each view separately).
        ``"neuromorphic"`` / ``"spike"``
                                → :class:`~bridges.neuromorphic_bridge.NeuromorphicEncoding`.
        ``"memristive"`` / ``"memristor"``
                                → :class:`~bridges.memristive_bridge.MemristiveTrace`.
        ``"reservoir"`` / ``"echo"``
                                → :class:`~bridges.reservoir_bridge.ReservoirNetwork`.
        ``"dual"`` / ``"both"`` / ``"merge"``
                                → ``{"binary": ..., "alternative": <ternary diagnostic>}``.
    frequency_hz
        Optional excitation frequency. Used by per-domain paradigms
        (ternary / quantum / stochastic) for skin-effect and zero-crossing
        analysis; ignored by binary and cross-domain paradigms.
    **extra
        Forwarded verbatim to the alternative interpreter.

    Returns
    -------
    str | object | dict
        Shape depends on ``mode``.

    Raises
    ------
    ValueError
        If ``mode`` is not recognised.
    NotImplementedError
        If the selected per-domain paradigm has no registered
        interpreter for ``domain``.
    """
    bucket, paradigm = _resolve_mode(mode)

    if bucket == "binary":
        return binary_encode(geometry, domain=domain)

    if bucket == "alternative":
        return alternative_encode(
            geometry, domain=domain, paradigm=paradigm,
            frequency_hz=frequency_hz, **extra,
        )

    # dual: run both paths; fail soft on alternative so callers still
    # get the binary representation when the alt path is not wired up.
    binary = binary_encode(geometry, domain=domain)
    alt_adapter = AlternativeAdapter(domain, paradigm=paradigm)
    alternative: Any
    if alt_adapter.is_available:
        alternative = alt_adapter.encode(
            geometry, frequency_hz=frequency_hz, **extra
        )
    else:
        alternative = None
    return {"binary": binary, "alternative": alternative}


# ---------------------------------------------------------------------------
# Legacy-shaped aliases from the spec
# ---------------------------------------------------------------------------

def encode_binary(geometry: Dict[str, Any], domain: str = "electric") -> str:
    """Alias preserved for the spec's ``encode_binary()`` entry point."""
    return binary_encode(geometry, domain=domain)


def encode_alternative(
    geometry: Dict[str, Any],
    domain: str = "electric",
    frequency_hz: Optional[float] = None,
    paradigm: str = "ternary",
) -> Any:
    """Alias preserved for the spec's ``encode_alternative()`` entry point."""
    return alternative_encode(
        geometry, domain=domain, paradigm=paradigm,
        frequency_hz=frequency_hz,
    )


__all__ = [
    "encode_state",
    "binary_encode",
    "alternative_encode",
    "encode_binary",
    "encode_alternative",
    "ALL_PARADIGMS",
    "PER_DOMAIN_PARADIGMS",
    "CROSS_DOMAIN_PARADIGMS",
]
