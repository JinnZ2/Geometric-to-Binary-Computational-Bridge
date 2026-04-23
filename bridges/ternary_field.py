"""
TernaryField — tensor-field propagation over ternary electrical states.

A 2D grid where each cell carries four channels:

  * channel 0 — charge class, one of ``{-1, 0, +1}``
  * channel 1 — current class, one of ``{-1, 0, +1}``
  * channel 2 — conductivity (continuous S/m)
  * channel 3 — probability mass in ``[0, 1]``

The propagation rule is a ternary-aware diffusion: each cell relaxes
toward the local neighbourhood average, the new charge is collapsed
back to a ternary class, and the current channel is classified from
the delta. A probability-mass update damps regions with large local
change, modelling the stochastic loss of certainty near fast
transients.

This module deliberately avoids NumPy on the hot path so it stays
self-contained; swap the inner loop for vectorised NumPy when the
grid grows beyond a few hundred cells on a side.
"""

from __future__ import annotations

from typing import List, Tuple

from bridges.electric_alternative_compute import classify_current_ternary


class TernaryField:
    """
    2D grid with four channels per cell.

    The grid is stored as nested Python lists to keep the module
    dependency-free; the shape is ``(nx, ny, 4)``.
    """

    NUM_CHANNELS = 4
    CH_CHARGE = 0
    CH_CURRENT = 1
    CH_CONDUCTIVITY = 2
    CH_PROBABILITY = 3

    def __init__(self, nx: int, ny: int) -> None:
        if nx < 3 or ny < 3:
            raise ValueError(
                "TernaryField requires nx and ny ≥ 3 so the "
                "interior update rule has at least one cell."
            )
        self.nx = nx
        self.ny = ny
        self.grid: List[List[List[float]]] = [
            [[0.0] * self.NUM_CHANNELS for _ in range(ny)]
            for _ in range(nx)
        ]

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def set_charge(self, x: int, y: int, value: float) -> None:
        self.grid[x][y][self.CH_CHARGE] = value

    def set_current(self, x: int, y: int, value: float) -> None:
        self.grid[x][y][self.CH_CURRENT] = value

    def set_conductivity(self, x: int, y: int, sigma: float) -> None:
        self.grid[x][y][self.CH_CONDUCTIVITY] = sigma

    def set_probability(self, x: int, y: int, p: float) -> None:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"probability must be in [0, 1], got {p}")
        self.grid[x][y][self.CH_PROBABILITY] = p

    def cell(self, x: int, y: int) -> Tuple[float, float, float, float]:
        c = self.grid[x][y]
        return c[0], c[1], c[2], c[3]

    # ------------------------------------------------------------------
    # Bulk setters — useful for tests and notebooks
    # ------------------------------------------------------------------

    def fill_conductivity(self, sigma: float) -> None:
        for i in range(self.nx):
            for j in range(self.ny):
                self.grid[i][j][self.CH_CONDUCTIVITY] = sigma


# ---------------------------------------------------------------------------
# Propagator
# ---------------------------------------------------------------------------

def _collapse_to_ternary(value: float, threshold: float = 0.5) -> int:
    """Snap a continuous charge estimate to ``{-1, 0, +1}``."""
    if value < -threshold:
        return -1
    if value > threshold:
        return 1
    return 0


def propagate(field: TernaryField, dt: float) -> TernaryField:
    """
    One timestep of ternary-aware diffusion.

    The rule per interior cell:

      * compute 4-neighbour average charge,
      * delta = conductivity * (neighbour_avg - charge),
      * new_charge = collapse_to_ternary(charge + dt * delta),
      * new_current = classify_current_ternary(delta),
      * new_probability = clamp(1 - |delta|, 0, 1).

    The boundary ring is left untouched; callers seed edges explicitly.
    """
    nx, ny = field.nx, field.ny

    # Allocate a fresh grid so the update is synchronous (no
    # read-modify-write contamination across cells).
    new_grid = [
        [list(field.grid[i][j]) for j in range(ny)]
        for i in range(nx)
    ]

    for i in range(1, nx - 1):
        for j in range(1, ny - 1):
            charge = field.grid[i][j][TernaryField.CH_CHARGE]
            conductivity = field.grid[i][j][TernaryField.CH_CONDUCTIVITY]

            neighbour_avg = (
                field.grid[i + 1][j][TernaryField.CH_CHARGE]
                + field.grid[i - 1][j][TernaryField.CH_CHARGE]
                + field.grid[i][j + 1][TernaryField.CH_CHARGE]
                + field.grid[i][j - 1][TernaryField.CH_CHARGE]
            ) / 4.0

            delta = conductivity * (neighbour_avg - charge)
            raw_charge = charge + dt * delta

            new_grid[i][j][TernaryField.CH_CHARGE] = _collapse_to_ternary(
                raw_charge
            )
            new_grid[i][j][TernaryField.CH_CURRENT] = float(
                classify_current_ternary(delta)
            )
            new_grid[i][j][TernaryField.CH_PROBABILITY] = max(
                0.0, min(1.0, 1.0 - abs(delta))
            )

    field.grid = new_grid
    return field


__all__ = ["TernaryField", "propagate"]
