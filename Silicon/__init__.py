"""Silicon — hardware implementation pathway for the octahedral bridge.

This package is the root for silicon-specific physics, fabrication
planning, and hardware-to-bridge adapters. Empty on purpose: submodules
(``core``, ``FRET``, ``lattice``, ``Projects``) hold the implementation.

The ``__init__`` exists solely so ``import Silicon.core.bridges.adapters``
works from a fresh checkout. Do not put logic here — every silicon-side
helper lives under a named submodule so the import surface stays
navigable.
"""
