"""Hardware module chooser for the silicon bridge layer.

This module provides a navigation-first entry point for users who do not want
one large wildcard import from ``Silicon.core.bridges``. Instead, they can ask
for only the hardware-related bridge modules they need.

Example
-------
    from Silicon.core.bridges.hardware_modules import choose_hardware_modules

    mods = choose_hardware_modules("hardware_bridge", "magnetic_bridge_protocol")
    hardware_bridge = mods["hardware_bridge"]
    magnetic_protocol = mods["magnetic_bridge_protocol"]

It also exposes a small catalog so readers can discover which hardware-facing
modules exist before importing them.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class HardwareModuleEntry:
    """Catalog entry describing one hardware-related silicon bridge module."""

    name: str
    module_path: str
    role: str


HARDWARE_MODULES: Dict[str, HardwareModuleEntry] = {
    "hardware_bridge": HardwareModuleEntry(
        name="hardware_bridge",
        module_path="Silicon.core.bridges.hardware_bridge",
        role="First-principles bridge from DFT, FRET, and magnetic quantities into silicon coherence and confinement physics.",
    ),
    "magnetic_bridge_protocol": HardwareModuleEntry(
        name="magnetic_bridge_protocol",
        module_path="Silicon.core.bridges.magnetic_bridge_protocol",
        role="Magnetic probing and tensor-reconstruction protocol for silicon-side bridge measurements.",
    ),
    "fret_coulomb_analysis": HardwareModuleEntry(
        name="fret_coulomb_analysis",
        module_path="Silicon.core.bridges.fret_coulomb_analysis",
        role="Förster and Coulomb coupling analysis used by the silicon hardware bridge layer.",
    ),
    "pipeline": HardwareModuleEntry(
        name="pipeline",
        module_path="Silicon.core.bridges.pipeline",
        role="End-to-end bridge orchestration pipeline connecting silicon-side components.",
    ),
    "silicon_gies_bridge": HardwareModuleEntry(
        name="silicon_gies_bridge",
        module_path="Silicon.core.bridges.silicon_gies_bridge",
        role="Silicon-specific GIES bridge utilities and state reduction helpers.",
    ),
    "gies_encoder": HardwareModuleEntry(
        name="gies_encoder",
        module_path="Silicon.core.bridges.gies_encoder",
        role="Encoder for silicon-side GIES representations and bridge-aligned export.",
    ),
}


def list_hardware_modules() -> List[HardwareModuleEntry]:
    """Return the hardware-module catalog in a stable, navigation-friendly order."""
    return [HARDWARE_MODULES[name] for name in sorted(HARDWARE_MODULES)]


def choose_hardware_modules(*names: str):
    """
    Import only the named hardware-facing silicon bridge modules.

    If no names are supplied, all cataloged hardware modules are imported.
    Returns a dict mapping the requested short names to the imported modules.
    """
    requested: Iterable[str] = names or tuple(sorted(HARDWARE_MODULES))
    loaded = {}
    for name in requested:
        if name not in HARDWARE_MODULES:
            available = ", ".join(sorted(HARDWARE_MODULES))
            raise KeyError(f"Unknown hardware module '{name}'. Available modules: {available}")
        entry = HARDWARE_MODULES[name]
        loaded[name] = import_module(entry.module_path)
    return loaded


__all__ = [
    "HardwareModuleEntry",
    "HARDWARE_MODULES",
    "list_hardware_modules",
    "choose_hardware_modules",
]
