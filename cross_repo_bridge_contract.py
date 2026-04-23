"""Cross-repository access helpers for the canonical bridge contract.

This module gives related repositories one small, stable import surface instead
of requiring them to inspect the registry, silicon adapter layer, and hardware
chooser independently.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List


_CONTRACT_PATH = Path(__file__).resolve().parent / "bridge_contract_manifest.json"


@lru_cache(maxsize=1)
def load_bridge_contract() -> Dict:
    """Load the canonical bridge contract manifest from disk."""
    return json.loads(_CONTRACT_PATH.read_text())


@lru_cache(maxsize=1)
def _bridge_index() -> Dict[str, Dict]:
    contract = load_bridge_contract()
    return {entry["name"]: entry for entry in contract["bridge_domains"]}


@lru_cache(maxsize=1)
def _hardware_index() -> Dict[str, Dict]:
    contract = load_bridge_contract()
    return {entry["name"]: entry for entry in contract["hardware_module_catalog"]}


def list_bridge_domains() -> List[str]:
    """Return bridge domains in canonical contract order."""
    return [entry["name"] for entry in load_bridge_contract()["bridge_domains"]]


def get_bridge_domain(name: str) -> Dict:
    """Return manifest metadata for one bridge domain."""
    key = name.strip().lower()
    if key not in _bridge_index():
        available = ", ".join(sorted(_bridge_index()))
        raise KeyError(f"Unknown bridge domain '{name}'. Available domains: {available}")
    return _bridge_index()[key]


def get_solver_name(name: str) -> str:
    """Return the canonical registry solver name for a bridge domain."""
    return get_bridge_domain(name)["solver_name"]


def get_top_level_encoder(name: str) -> str:
    """Return the canonical top-level encoder import path for a bridge domain."""
    return get_bridge_domain(name)["top_level_encoder"]


def get_silicon_entry_point(name: str) -> str:
    """Return the canonical silicon-side entry point for a bridge domain."""
    return get_bridge_domain(name)["silicon_entry_point"]


def list_hardware_modules() -> List[str]:
    """Return hardware-module names in canonical contract order."""
    return [entry["name"] for entry in load_bridge_contract()["hardware_module_catalog"]]


def get_hardware_module(name: str) -> Dict:
    """Return manifest metadata for one hardware-side module."""
    key = name.strip().lower()
    if key not in _hardware_index():
        available = ", ".join(sorted(_hardware_index()))
        raise KeyError(f"Unknown hardware module '{name}'. Available modules: {available}")
    return _hardware_index()[key]


__all__ = [
    "load_bridge_contract",
    "list_bridge_domains",
    "get_bridge_domain",
    "get_solver_name",
    "get_top_level_encoder",
    "get_silicon_entry_point",
    "list_hardware_modules",
    "get_hardware_module",
]
