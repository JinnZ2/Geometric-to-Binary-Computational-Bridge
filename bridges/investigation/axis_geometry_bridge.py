"""Axis Geometry Bridge (Investigation Stage)
================================================

This module explores whether the six-axis community / resilience geometry can
be read not only through per-axis capacities and buffers, but also through the
**coherence of relationships between axes**.

Status
------
This module is **under investigation and review**. It is importable and useful
for exploratory analysis, but it is not yet part of the repository's canonical
bridge contract or main registry surface.

Architectural role
------------------
The implementation builds on top of ``bridges.community_encoder`` and therefore
should be read as an analysis layer over the existing community / resilience
geometry, not as an independent bridge family.

Interpretation caution
----------------------
The quantities below are heuristic diagnostics. In particular, the geometric
integrity and eigenvalue summaries are simplified proxies intended for review
and comparative exploration rather than settled physical observables.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Tuple

from bridges.community_encoder import profile_to_buffers, profile_to_capacities


class OctahedralAxis(IntEnum):
    """The six axes used by the community and resilience bridge geometry."""

    FOOD_POS_X = 0
    ENERGY_NEG_X = 1
    SOCIAL_POS_Y = 2
    INSTITUTIONAL_NEG_Y = 3
    KNOWLEDGE_POS_Z = 4
    INFRA_NEG_Z = 5

    @property
    def opposite(self) -> "OctahedralAxis":
        opposites = {
            self.FOOD_POS_X: self.ENERGY_NEG_X,
            self.ENERGY_NEG_X: self.FOOD_POS_X,
            self.SOCIAL_POS_Y: self.INSTITUTIONAL_NEG_Y,
            self.INSTITUTIONAL_NEG_Y: self.SOCIAL_POS_Y,
            self.KNOWLEDGE_POS_Z: self.INFRA_NEG_Z,
            self.INFRA_NEG_Z: self.KNOWLEDGE_POS_Z,
        }
        return opposites[self]

    @property
    def dimension(self) -> str:
        return {
            self.FOOD_POS_X: "X",
            self.ENERGY_NEG_X: "X",
            self.SOCIAL_POS_Y: "Y",
            self.INSTITUTIONAL_NEG_Y: "Y",
            self.KNOWLEDGE_POS_Z: "Z",
            self.INFRA_NEG_Z: "Z",
        }[self]


class AxisGeometryState(IntEnum):
    """Exploratory three-state classification of cross-axis coherence."""

    COHERENT = -1
    DECOUPLING = 0
    FRACTURED = 1

    @property
    def interpretation(self) -> str:
        return {
            self.COHERENT: "Axes appear mutually coherent, so cross-domain transport remains comparatively easy.",
            self.DECOUPLING: "Some axis relationships appear to be separating, suggesting rising path dependence.",
            self.FRACTURED: "Axis relationships appear strongly separated, suggesting poor cross-domain transport.",
        }[self]


@dataclass
class AxisGeometry:
    """Exploratory reading of cross-axis coherence derived from a community profile."""

    buffers: Dict[str, float] = field(default_factory=dict)
    capacities: Dict[str, float] = field(default_factory=dict)
    axis_values: Dict[OctahedralAxis, float] = field(default_factory=dict)
    coherence_matrix: Dict[Tuple[OctahedralAxis, OctahedralAxis], float] = field(default_factory=dict)
    transport_costs: Dict[Tuple[OctahedralAxis, OctahedralAxis], float] = field(default_factory=dict)
    decoupled_axes: List[Tuple[OctahedralAxis, OctahedralAxis]] = field(default_factory=list)
    geometric_integrity: float = 0.0
    eigenvalues: List[float] = field(default_factory=list)
    holonomy_risk: bool = False
    geometry_state: AxisGeometryState = AxisGeometryState.COHERENT
    decoupling_threshold: float = 0.30

    def from_profile(self, community_profile: dict | Any) -> "AxisGeometry":
        if not isinstance(community_profile, dict):
            community_profile = community_profile.__dict__

        self.buffers = profile_to_buffers(community_profile)
        self.capacities = profile_to_capacities(community_profile)
        self.axis_values = {
            OctahedralAxis.FOOD_POS_X: self.buffers.get("food", 0.0),
            OctahedralAxis.ENERGY_NEG_X: self.buffers.get("energy", 0.0),
            OctahedralAxis.SOCIAL_POS_Y: self.buffers.get("social", 0.0),
            OctahedralAxis.INSTITUTIONAL_NEG_Y: self.buffers.get("institutional", 0.0),
            OctahedralAxis.KNOWLEDGE_POS_Z: self.buffers.get("knowledge", 0.0),
            OctahedralAxis.INFRA_NEG_Z: self.buffers.get("infrastructure", 0.0),
        }
        self._compute_coherence_matrix()
        self._compute_transport_costs()
        self._compute_geometric_integrity()
        self._detect_holonomy()
        self._classify_geometry()
        return self

    def _compute_coherence_matrix(self) -> None:
        axes = list(OctahedralAxis)
        self.coherence_matrix = {}
        for i, axis_i in enumerate(axes):
            for j, axis_j in enumerate(axes):
                if i <= j:
                    val_i = self.axis_values.get(axis_i, 0.0)
                    val_j = self.axis_values.get(axis_j, 0.0)
                    coherence = max(0.0, 1.0 - abs(val_i - val_j))
                    self.coherence_matrix[(axis_i, axis_j)] = coherence
                    self.coherence_matrix[(axis_j, axis_i)] = coherence

    def _compute_transport_costs(self) -> None:
        self.transport_costs = {}
        for (axis_i, axis_j), coherence in self.coherence_matrix.items():
            if axis_i == axis_j:
                continue
            c = max(-1.0, min(1.0, coherence))
            self.transport_costs[(axis_i, axis_j)] = math.acos(c)

    def _compute_geometric_integrity(self) -> None:
        axes = list(OctahedralAxis)
        integrity = 1.0
        for dim in ["X", "Y", "Z"]:
            dim_axes = [axis for axis in axes if axis.dimension == dim]
            if len(dim_axes) != 2:
                continue
            a1, a2 = dim_axes
            c11 = self.coherence_matrix.get((a1, a1), 1.0)
            c12 = self.coherence_matrix.get((a1, a2), 0.0)
            c21 = self.coherence_matrix.get((a2, a1), 0.0)
            c22 = self.coherence_matrix.get((a2, a2), 1.0)
            det_dim = c11 * c22 - c12 * c21
            integrity *= max(0.0, det_dim)
        self.geometric_integrity = integrity

        n = len(axes)
        diagonal_values = [self.coherence_matrix.get((a, a), 1.0) for a in axes]
        off_diagonal_means: List[float] = []
        for i, axis_i in enumerate(axes):
            row_sum = sum(
                self.coherence_matrix.get((axis_i, axis_j), 0.0)
                for j, axis_j in enumerate(axes)
                if i != j
            )
            off_diagonal_means.append(row_sum / max(n - 1, 1))
        self.eigenvalues = [d + od for d, od in zip(diagonal_values, off_diagonal_means)]

    def _detect_holonomy(self) -> None:
        self.decoupled_axes = []
        for (axis_i, axis_j), coherence in self.coherence_matrix.items():
            if axis_i == axis_j or axis_i.value >= axis_j.value:
                continue
            if coherence < self.decoupling_threshold:
                self.decoupled_axes.append((axis_i, axis_j))
        self.holonomy_risk = bool(self.decoupled_axes)

    def _classify_geometry(self) -> None:
        n_axes = len(OctahedralAxis)
        n_pairs = n_axes * (n_axes - 1) // 2
        n_decoupled = len(self.decoupled_axes)
        opposing_coherences = [
            self.coherence_matrix.get((axis, axis.opposite), 1.0)
            for axis in OctahedralAxis
            if axis.value < axis.opposite.value
        ]
        min_opposing = min(opposing_coherences) if opposing_coherences else 1.0

        if n_decoupled == 0 and self.geometric_integrity > 0.5:
            self.geometry_state = AxisGeometryState.COHERENT
        elif min_opposing < 0.1 or n_decoupled >= n_pairs // 2:
            self.geometry_state = AxisGeometryState.FRACTURED
        else:
            self.geometry_state = AxisGeometryState.DECOUPLING

    def compute_innovation_capacity(self) -> Dict[str, Any]:
        base_capacity = self.geometric_integrity
        if self.transport_costs:
            avg_transport = sum(self.transport_costs.values()) / len(self.transport_costs)
            transport_factor = max(0.0, 1.0 - avg_transport / math.pi)
        else:
            transport_factor = 1.0
        holonomy_penalty = 0.5 if self.holonomy_risk else 0.0
        innovation_capacity = base_capacity * transport_factor * (1.0 - holonomy_penalty)
        innovation_capacity = max(0.0, min(1.0, innovation_capacity))
        mean_buffer = sum(self.buffers.values()) / max(len(self.buffers), 1)

        if mean_buffer < 0.3 and innovation_capacity > 0.5:
            regime = "SCARCITY_COHERENT"
            interpretation = (
                "Exploratory reading: low average buffers coexist with relatively strong geometry, "
                "so cross-domain adaptation may remain possible despite scarcity."
            )
        elif mean_buffer > 0.6 and innovation_capacity < 0.3:
            regime = "RESOURCE_RICH_STAGNANT"
            interpretation = (
                "Exploratory reading: resource levels look high, but cross-axis coherence appears weak, "
                "so surplus may not translate into adaptive flexibility."
            )
        elif innovation_capacity > 0.6:
            regime = "HIGH_INNOVATION_POTENTIAL"
            interpretation = "Exploratory reading: cross-axis geometry appears strong enough to support broad adaptation."
        else:
            regime = "LOW_INNOVATION_POTENTIAL"
            interpretation = "Exploratory reading: axis geometry appears to constrain cross-domain transport and adaptation."

        return {
            "innovation_capacity": innovation_capacity,
            "geometric_integrity": self.geometric_integrity,
            "transport_factor": transport_factor,
            "holonomy_penalty": holonomy_penalty,
            "mean_buffer": mean_buffer,
            "regime": regime,
            "interpretation": interpretation,
            "geometry_state": self.geometry_state.name,
        }

    def diagnose(self) -> str:
        lines = [
            "=" * 60,
            "Axis Geometry Direct Reading (Investigation Stage)",
            "=" * 60,
            "",
            "Status: exploratory module under investigation and review.",
            "",
            f"Geometry State: {self.geometry_state.name}",
            f"  {self.geometry_state.interpretation}",
            "",
            f"Geometric Integrity: {self.geometric_integrity:.3f}",
            "  (Heuristic proxy derived from pairwise axis coherence)",
            "",
            "Axis Coherence Matrix:",
        ]
        axes = list(OctahedralAxis)
        lines.append("  " + "".join(f"{a.name[:6]:>8s}" for a in axes))
        for axis_i in axes:
            row = f"  {axis_i.name[:6]:8s}"
            for axis_j in axes:
                row += f"{self.coherence_matrix.get((axis_i, axis_j), 0.0):8.3f}"
            lines.append(row)

        lines.append("")
        lines.append("Transport Costs (radians):")
        for (axis_i, axis_j), cost in sorted(self.transport_costs.items(), key=lambda item: item[1], reverse=True)[:6]:
            lines.append(f"  {axis_i.name[:12]:12s} -> {axis_j.name[:12]:12s}: {cost:.3f} rad")

        if self.decoupled_axes:
            lines.append("")
            lines.append(f"Decoupled Axis Pairs ({len(self.decoupled_axes)}):")
            for axis_i, axis_j in self.decoupled_axes:
                lines.append(
                    f"  {axis_i.name:20s} <-> {axis_j.name:20s}  coherence={self.coherence_matrix.get((axis_i, axis_j), 0.0):.3f}"
                )

        innovation = self.compute_innovation_capacity()
        lines.append("")
        lines.append(f"Innovation Regime: {innovation['regime']}")
        lines.append(f"  {innovation['interpretation']}")
        lines.append("")
        lines.append("Individual Buffer States (context only):")
        for axis, value in self.axis_values.items():
            bar = "#" * int(value * 30)
            lines.append(f"  {axis.name:20s}: {bar} {value:.2f}")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


__all__ = [
    "OctahedralAxis",
    "AxisGeometryState",
    "AxisGeometry",
]
