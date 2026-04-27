"""
octahedral_canon — bijection between the GEIS and Engine octahedral
                    coordinate conventions.

Two subsystems in this repo number the eight octahedral vertices
differently:

* ``GEIS/octahedral_state.py::OctahedralState.POSITIONS`` —
  coordinate triples in :math:`\\{-0.25, +0.25\\}^3` with bit-value
  ``0`` meaning **positive** and the bit-to-axis layout::

      bit 0 (LSB) → y    bit 1 → x    bit 2 (MSB) → z

* ``Engine/gaussian_splats/octahedral.py::OctahedralStateEncoder.state_centers`` —
  cube-corner coordinates in :math:`\\{-1, +1\\}^3` with bit-value
  ``1`` meaning **positive** and the bit-to-axis layout::

      bit 0 (LSB) → x    bit 1 → y    bit 2 (MSB) → z

Each system is internally consistent. Neither imports the other, so
there is no live bug today — but **any code that translates a GEIS
index into an Engine index must apply both an axis permutation
(swap LSB and bit-1) and a per-bit inversion**, or it will silently
write field sources at the wrong coordinates.

This module is the single source of truth for that translation.

Use it whenever you need to:

* feed a GEIS-encoded vertex stream into Engine field-source code,
* read an Engine-side dominant_state back into GEIS-shaped
  bookkeeping, or
* assert that a downstream consumer's understanding of "vertex 3"
  matches the producer's.

The bijection is an involution: ``swap_geis_engine(swap_geis_engine(i))
== i`` for all i in 0..7. ``geis_to_engine`` and ``engine_to_geis``
are aliases pointing at the same function so callers can name the
direction they care about without juggling a separate inverse.
"""

from __future__ import annotations

from typing import Sequence, Tuple


# ----------------------------------------------------------------------
# Bit-level bijection
# ----------------------------------------------------------------------

NUM_VERTICES = 8


def swap_geis_engine(index: int) -> int:
    """
    Translate one octahedral vertex index between the two conventions.

    The transformation is an involution; applying it twice returns
    the original index.

    The implementation:

    1. Pull GEIS axis bits (y at bit 0, x at bit 1, z at bit 2).
    2. Invert each (GEIS uses 0 for positive; Engine uses 1).
    3. Repack into Engine layout (x at bit 0, y at bit 1, z at bit 2).

    Equivalent one-liner: ``(index ^ 0b111) ^ ((index ^ (index >> 1)) & 1) * 0b011``
    — but the explicit form below is the one the docstring describes.
    """
    if not 0 <= index < NUM_VERTICES:
        raise ValueError(
            f"octahedral index must be in [0, {NUM_VERTICES}); got {index}"
        )
    y_bit = index & 1
    x_bit = (index >> 1) & 1
    z_bit = (index >> 2) & 1

    # Sign inversion (GEIS bit_value 0 == Engine bit_value 1).
    x_swap = 1 - x_bit
    y_swap = 1 - y_bit
    z_swap = 1 - z_bit

    # Layout swap: Engine puts x at LSB, y at bit 1.
    return x_swap | (y_swap << 1) | (z_swap << 2)


# Direction-named aliases — same function, different reading.
geis_to_engine = swap_geis_engine
engine_to_geis = swap_geis_engine


# ----------------------------------------------------------------------
# Position-vector bijection
# ----------------------------------------------------------------------

def geis_position_to_engine_position(
    pos: Sequence[float],
) -> Tuple[float, float, float]:
    """
    Translate a GEIS position triple ``(±0.25, ±0.25, ±0.25)`` to its
    Engine counterpart in ``{-1, +1}^3``.

    The signs flip iff the GEIS components are non-positive — the
    GEIS magnitude (0.25) does *not* mean a different physical
    location, just a different basis scaling. Callers that want to
    preserve magnitude should apply the bijection on signs only and
    keep their own scalar.
    """
    if len(pos) != 3:
        raise ValueError(f"position must be a 3-tuple; got len={len(pos)}")
    return tuple(  # type: ignore[return-value]
        +1.0 if v > 0 else -1.0 for v in pos
    )


def engine_position_to_geis_position(
    pos: Sequence[float],
    magnitude: float = 0.25,
) -> Tuple[float, float, float]:
    """
    Reverse of :func:`geis_position_to_engine_position`.

    The Engine convention has unit-magnitude axes; GEIS uses 0.25.
    Pass ``magnitude`` to rescale (defaults to the GEIS canonical
    0.25 used in :data:`GEIS.octahedral_state.OctahedralState.POSITIONS`).
    """
    if len(pos) != 3:
        raise ValueError(f"position must be a 3-tuple; got len={len(pos)}")
    return tuple(  # type: ignore[return-value]
        magnitude if v > 0 else -magnitude for v in pos
    )


# ----------------------------------------------------------------------
# Verification helpers
# ----------------------------------------------------------------------

def is_bijection_intact() -> bool:
    """
    Return True iff ``swap_geis_engine`` is a proper involution
    on the eight indices. Used by the test suite to catch
    accidental refactors of the bit-level math.
    """
    seen = set()
    for i in range(NUM_VERTICES):
        e = swap_geis_engine(i)
        if not 0 <= e < NUM_VERTICES:
            return False
        seen.add(e)
        if swap_geis_engine(e) != i:
            return False
    return len(seen) == NUM_VERTICES


def reconciliation_table() -> Tuple[Tuple[int, int, Tuple[int, int, int]], ...]:
    """
    Produce the canonical ``(geis_index, engine_index, signs)`` table
    for inspection / documentation. ``signs`` is a 3-tuple of ``±1``
    matching the physical x / y / z signs both subsystems agree on.
    """
    out = []
    for g in range(NUM_VERTICES):
        e = geis_to_engine(g)
        x_sign = -1 if (g >> 1) & 1 else 1
        y_sign = -1 if (g & 1) else 1
        z_sign = -1 if (g >> 2) & 1 else 1
        out.append((g, e, (x_sign, y_sign, z_sign)))
    return tuple(out)


__all__ = [
    "NUM_VERTICES",
    "swap_geis_engine",
    "geis_to_engine",
    "engine_to_geis",
    "geis_position_to_engine_position",
    "engine_position_to_geis_position",
    "is_bijection_intact",
    "reconciliation_table",
]
