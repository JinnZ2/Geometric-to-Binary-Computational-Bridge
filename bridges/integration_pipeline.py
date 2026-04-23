"""
Integration pipeline — orchestrates dual-path encoding at the repo level.

This is the repo's canonical "one call that produces everything" entry
point. Internally it uses the ``bridges.encode_state`` dispatcher and
the ``BinaryBridgeEncoder`` / alternative interpreter adapters; the
separate orchestration layer exists so downstream code never has to
know whether a domain has an alternative interpreter registered.

Design notes
------------
* ``run_full_bridge`` is domain-parametric. It is what the spec asks
  for when it says "add ``alternative_encode()`` alongside ``encode()``
  at the main encoder entry."
* ``run_all_bridges`` iterates every domain that has a registered
  binary encoder and collects dual-path results. Domains whose
  alternative interpreter is missing still produce a binary
  representation plus an ``alternative=None`` marker.
* The return shape is a plain ``dict`` so it is trivially
  JSON-serialisable (after calling ``.summary()`` on diagnostic
  objects).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from bridges.adapters.binary_adapter import _ENCODER_REGISTRY as _BINARY_DOMAINS
from bridges.adapters.ternary_adapter import AlternativeAdapter
from bridges.encode_state import alternative_encode, binary_encode


def run_full_bridge(
    geometry: Dict[str, Any],
    domain: str = "electric",
    frequency_hz: Optional[float] = None,
    include_raw_encoder: bool = False,
) -> Dict[str, Any]:
    """
    Run the full geometric → binary + alternative pipeline for one domain.

    Parameters
    ----------
    geometry
        Domain-specific geometry dict.
    domain
        Domain key (defaults to ``"electric"`` to match the spec example).
    frequency_hz
        Optional excitation frequency forwarded to the alternative path.
    include_raw_encoder
        When true, also instantiate the binary encoder and include the
        full encoder report (checksum, metadata, bit depth) under
        ``raw_encoder_state``.

    Returns
    -------
    dict
        ``{
            "domain": ...,
            "binary_representation": "...",
            "alternative_representation": <diagnostic summary or None>,
            "alternative_available": bool,
            "raw_encoder_state": {...} or absent,
        }``
    """
    binary = binary_encode(geometry, domain=domain)

    alt_adapter = AlternativeAdapter(domain)
    if alt_adapter.is_available:
        diag = alternative_encode(
            geometry, domain=domain, frequency_hz=frequency_hz
        )
        alt_repr: Any = (
            diag.summary() if hasattr(diag, "summary") else diag
        )
    else:
        diag = None
        alt_repr = None

    result: Dict[str, Any] = {
        "domain": domain,
        "binary_representation": binary,
        "alternative_representation": alt_repr,
        "alternative_available": alt_adapter.is_available,
        "alternative_object": diag,
    }

    if include_raw_encoder:
        from bridges.adapters.binary_adapter import BinaryAdapter

        result["raw_encoder_state"] = BinaryAdapter(domain).report(geometry)

    return result


def run_all_bridges(
    geometry_by_domain: Dict[str, Dict[str, Any]],
    frequency_hz: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Run ``run_full_bridge`` for every domain in ``geometry_by_domain``.

    Parameters
    ----------
    geometry_by_domain
        Mapping from domain key to that domain's geometry dict. Only
        domains present as keys are run.
    frequency_hz
        Forwarded to each domain's alternative path.

    Returns
    -------
    dict
        ``{domain: run_full_bridge(...)}`` for every input domain.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for domain, geometry in geometry_by_domain.items():
        if domain not in _BINARY_DOMAINS:
            raise KeyError(
                f"No registered binary encoder for domain {domain!r}. "
                f"Known: {sorted(_BINARY_DOMAINS)}"
            )
        out[domain] = run_full_bridge(
            geometry, domain=domain, frequency_hz=frequency_hz
        )
    return out


def domains_with_alternative() -> Iterable[str]:
    """List domains that currently have a wired-up alternative interpreter."""
    return [
        domain
        for domain in _BINARY_DOMAINS
        if AlternativeAdapter(domain).is_available
    ]


def domains_missing_alternative() -> Iterable[str]:
    """List domains that still need an alternative interpreter."""
    return [
        domain
        for domain in _BINARY_DOMAINS
        if not AlternativeAdapter(domain).is_available
    ]


__all__ = [
    "run_full_bridge",
    "run_all_bridges",
    "domains_with_alternative",
    "domains_missing_alternative",
]
