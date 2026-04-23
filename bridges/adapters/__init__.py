"""
bridges.adapters
================

Uniform wrappers that expose domain encoders (binary) and alternative
interpreters (ternary / stochastic / quantum) behind a single call
signature. Each adapter hides the concrete implementation details so
the dual-path pipeline can be written domain-agnostically.

Two flavours:

* ``BinaryAdapter``       — wraps a ``BinaryBridgeEncoder`` subclass.
* ``AlternativeAdapter``  — wraps a module-level
                            ``<domain>_full_alternative_diagnostic``
                            function.

Both implement ``encode(geometry, **kwargs)``; use
``bridges.encode_state.encode_state`` to dispatch by mode.
"""

from bridges.adapters.binary_adapter import BinaryAdapter
from bridges.adapters.ternary_adapter import AlternativeAdapter

__all__ = ["BinaryAdapter", "AlternativeAdapter"]
