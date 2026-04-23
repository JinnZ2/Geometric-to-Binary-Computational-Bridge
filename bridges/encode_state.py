"""
encode_state — unified dispatcher for binary / ternary / dual encoding
======================================================================

This is the single entry point for the branch-point architecture
described in ``alternative_computing_bridge.md``:

                     ┌── binary encoder  (deterministic bitstring)
    geometry ────────┼── alternative interpreter (ternary + stochastic + quantum)
                     └── dual             (both; returns {"binary": ..., "alternative": ...})

The function avoids hard-wiring any domain — it takes a ``domain``
keyword and delegates to the matching adapter in
``bridges.adapters``. Domains without an alternative interpreter raise
a clear ``NotImplementedError`` rather than silently falling back to
the binary path (silent fallback was explicitly the failure mode the
alternative bridge was designed to eliminate).

Basic usage
-----------
>>> from bridges.encode_state import encode_state
>>> encode_state({"charge": [1e-6]}, domain="electric", mode="binary")
'1111'
>>> diag = encode_state({"charge": [1e-6]}, domain="electric", mode="ternary")
>>> type(diag).__name__
'ElectricAlternativeDiagnostic'
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from bridges.adapters import AlternativeAdapter, BinaryAdapter


# Accept several spellings for mode so callers can match the terminology
# in the original spec without tripping on aliases.
_MODE_ALIASES = {
    "binary": "binary",
    "bin":    "binary",
    "b":      "binary",

    "ternary":     "alternative",
    "alternative": "alternative",
    "alt":         "alternative",
    "stochastic":  "alternative",
    "quantum":     "alternative",

    "dual":  "dual",
    "both":  "dual",
    "merge": "dual",
}


def _normalise_mode(mode: str) -> str:
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
    frequency_hz: Optional[float] = None,
    **extra: Any,
) -> Any:
    """Shortcut: run the registered alternative interpreter for ``domain``."""
    return AlternativeAdapter(domain).encode(
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
        Input geometry dict (domain-specific schema).
    domain
        Domain key — one of ``electric``, ``magnetic``, ``light``,
        ``sound``, ``gravity``, ``wave``, ``thermal``, ``pressure``,
        ``chemical``, ``consciousness``, ``emotion``.
    mode
        ``"binary"``  → return bitstring.
        ``"ternary"`` / ``"alternative"`` / ``"stochastic"`` / ``"quantum"``
                      → return the domain diagnostic object.
        ``"dual"`` / ``"both"``
                      → return ``{"binary": ..., "alternative": ...}``.
    frequency_hz
        Optional excitation frequency for skin-effect / zero-crossing
        / Doppler analyses. Ignored by the binary path.
    **extra
        Additional keyword arguments forwarded to the alternative
        interpreter.

    Returns
    -------
    str | object | dict
        Shape depends on ``mode``.

    Raises
    ------
    ValueError
        If ``mode`` is not recognised.
    NotImplementedError
        If ``mode`` selects the alternative path but the domain has no
        registered alternative interpreter.
    """
    resolved = _normalise_mode(mode)

    if resolved == "binary":
        return binary_encode(geometry, domain=domain)

    if resolved == "alternative":
        return alternative_encode(
            geometry, domain=domain, frequency_hz=frequency_hz, **extra
        )

    # dual: run both paths; fail soft on alternative so callers still
    # get the binary representation when the alt path is not wired up.
    binary = binary_encode(geometry, domain=domain)
    alt_adapter = AlternativeAdapter(domain)
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
) -> Any:
    """Alias preserved for the spec's ``encode_alternative()`` entry point."""
    return alternative_encode(
        geometry, domain=domain, frequency_hz=frequency_hz
    )


__all__ = [
    "encode_state",
    "binary_encode",
    "alternative_encode",
    "encode_binary",
    "encode_alternative",
]
