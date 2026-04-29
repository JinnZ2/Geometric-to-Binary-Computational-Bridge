"""
hidden_channel_detector — flag substrate-as-signal geometry.

The pattern (see ``docs/hidden_channel_pattern.md``):

    *system_X uses field_F as substrate; field_F also carries a*
    *signal at a geometry the system_X equations do not expose;*
    *translation requires basis change.*

Three known instances:

* **DmAlka** — Cl⁻ channel reads K⁺ geometry via O-coordination
  mimicry.
* **EDC** — endocrine receptor reads pollutant geometry via
  hormone-shape mimicry; thermal field modulates the effective
  amplitude.
* **vector_spin** — EM detector reads polarization geometry via
  spin-component separation.

This module names the pattern as a first-class type so drivers and
encoders can declare it explicitly. A future *audit-engine* version
of this module will scan a system description for the pattern and
flag scalar-model insufficiency. Today's surface is intentionally
small:

* :class:`ShapeChannel` — frozen value object describing one
  hidden-channel basis (name, axes, DOF, projection-op name).
* :class:`SupportsShapeChannels` — runtime-checkable Protocol any
  driver / encoder can implement to advertise its shape channels.
* :data:`SHAPE_CHANNEL_REGISTRY` — central catalogue of recognised
  channels so cross-references stay consistent.
* :func:`detect_hidden_channels` — minimal heuristic. Today: returns
  the receiver's declared shape channels (if any) and flags
  scalar-only when the claimed channel matches none of them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    runtime_checkable,
)


# ----------------------------------------------------------------------
# ShapeChannel
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ShapeChannel:
    """One hidden-channel basis in a field.

    Attributes
    ----------
    name
        Stable identifier — ``"polarization"``, ``"spin_separation"``,
        ``"hormone_geometry"``. Used as a key in
        :data:`SHAPE_CHANNEL_REGISTRY` and as a token in Primitive
        ``couplings``.
    basis_axes
        Names of the basis vectors. For polarization this is
        ``("E_x", "E_y")`` (linear) or
        ``("S_0", "S_1", "S_2", "S_3")`` (full Stokes). For an EDC
        binding pose: ``("ring_A", "ring_B", "linker")``.
    dof
        Number of independent degrees of freedom. The whole point of
        the pattern: ``dof`` exceeds what the scalar / amplitude /
        concentration channel exposes.
    projection_op
        Name of the operator that maps the field onto this basis.
        Free-form string; today a label, not a callable. Examples:
        ``"stokes_decomposition"``, ``"polarizer_at_angle"``,
        ``"receptor_pose_alignment"``.
    description
        One-sentence English description for human readers / docs.
    metadata
        Optional ``dict[str, Any]`` for paradigm-specific extras
        (e.g. ``{"normalised": True}`` for Stokes parameters that
        are intensity-normalised).
    """

    name: str
    basis_axes: Tuple[str, ...]
    dof: int
    projection_op: str
    description: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ShapeChannel.name must be non-empty")
        if self.dof <= 0:
            raise ValueError(
                f"ShapeChannel.dof must be positive; got {self.dof}"
            )
        if len(self.basis_axes) != self.dof:
            raise ValueError(
                f"ShapeChannel {self.name!r}: basis_axes has "
                f"{len(self.basis_axes)} entries but dof={self.dof}. "
                f"They must match."
            )


# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------

# Centralised vocabulary so cross-references stay consistent across
# bridges, sensing drivers, and downstream consumers. Add entries
# here as new shape channels are recognised.
SHAPE_CHANNEL_REGISTRY: Dict[str, ShapeChannel] = {
    "polarization": ShapeChannel(
        name="polarization",
        basis_axes=("S_0", "S_1", "S_2", "S_3"),
        dof=4,
        projection_op="stokes_decomposition",
        description=(
            "Linear and circular polarization components of an EM "
            "field. The intensity / amplitude channel exposes only "
            "S_0; S_1..S_3 are orthogonal information channels that "
            "scalar photometry collapses."
        ),
    ),
    "polarization_linear": ShapeChannel(
        name="polarization_linear",
        basis_axes=("S_0", "S_1", "S_2"),
        dof=3,
        projection_op="rotating_polarizer",
        description=(
            "Reduced linear-only polarization basis (DoLP + AoP "
            "without circular component). Default basis for a "
            "rotating-polarizer photodiode driver."
        ),
    ),
    "spin_separation": ShapeChannel(
        name="spin_separation",
        basis_axes=("spin_axis_x", "spin_axis_y", "spin_axis_z"),
        dof=3,
        projection_op="spin_component_decomposition",
        description=(
            "Vectorial spin distribution inside a structured EM "
            "field (Light: Sci & Appl 2026). Carries information "
            "orthogonal to amplitude and phase."
        ),
    ),
    "hormone_geometry": ShapeChannel(
        name="hormone_geometry",
        basis_axes=("ring_pose", "linker_pose", "polar_head_pose"),
        dof=3,
        projection_op="receptor_pose_alignment",
        description=(
            "Ligand-pose basis at a hormone-receptor binding site "
            "(npj Emerging Contaminants 2026). Endocrine-disrupting "
            "compounds occupy this basis with the same shape as the "
            "endogenous hormone — concentration-as-scalar misses it."
        ),
    ),
    "ion_coordination": ShapeChannel(
        name="ion_coordination",
        basis_axes=("O_1", "O_2", "O_3", "O_4"),
        dof=4,
        projection_op="oxygen_coordination_geometry",
        description=(
            "Oxygen-coordination geometry that the DmAlka chloride "
            "channel reads to infer K⁺ presence. Concentration alone "
            "does not switch the mode — coordination geometry does."
        ),
    ),
}


def register_shape_channel(channel: ShapeChannel) -> None:
    """Add a :class:`ShapeChannel` to the registry. Idempotent if the
    same channel object is registered twice; raises if the name
    already maps to a *different* channel."""
    existing = SHAPE_CHANNEL_REGISTRY.get(channel.name)
    if existing is None:
        SHAPE_CHANNEL_REGISTRY[channel.name] = channel
        return
    if existing != channel:
        raise ValueError(
            f"ShapeChannel name {channel.name!r} is already registered "
            f"with a different definition. Use a fresh name."
        )


def get_shape_channel(name: str) -> ShapeChannel:
    """Return a registered :class:`ShapeChannel` or raise ``KeyError``."""
    if name not in SHAPE_CHANNEL_REGISTRY:
        raise KeyError(
            f"No shape channel registered under {name!r}. "
            f"Known: {sorted(SHAPE_CHANNEL_REGISTRY)}"
        )
    return SHAPE_CHANNEL_REGISTRY[name]


# ----------------------------------------------------------------------
# Protocol — driver/encoder advertises shape channels
# ----------------------------------------------------------------------

@runtime_checkable
class SupportsShapeChannels(Protocol):
    """Anything with a ``shape_channels()`` method that returns a list
    of :class:`ShapeChannel`. Drivers, encoders, intersection rules
    can all opt in.

    Returning an empty list is meaningful — it explicitly says
    "this object operates on the scalar / amplitude channel only,
    and the receiver's reading is sufficient for its claimed
    measurement." That distinction matters for the audit engine."""

    def shape_channels(self) -> List[ShapeChannel]:
        ...


def shape_channels_of(obj: Any) -> List[ShapeChannel]:
    """Return ``obj.shape_channels()`` if obj implements the protocol,
    else an empty list. Convenience for callers that don't want to
    isinstance-check at every site."""
    fn = getattr(obj, "shape_channels", None)
    if callable(fn):
        try:
            channels = fn()
        except Exception:  # noqa: BLE001
            return []
        return list(channels) if channels else []
    return []


# ----------------------------------------------------------------------
# Detection helper
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class HiddenChannelReport:
    """Output of :func:`detect_hidden_channels`."""

    hidden_channels: Tuple[ShapeChannel, ...]
    """Channels the receiver advertises but the claimed scalar
    channel does not cover."""

    scalar_sufficient: bool
    """True iff the receiver advertises no shape channels OR the
    claimed channel already names every advertised channel."""

    notes: Tuple[str, ...]


def detect_hidden_channels(
    receiver: Any,
    claimed_channel: str,
    *,
    extra_known_channels: Optional[Iterable[str]] = None,
) -> HiddenChannelReport:
    """Minimal heuristic — flag receivers whose advertised shape
    channels are not covered by the claimed scalar channel.

    Future versions will run the full four-point check from
    ``docs/hidden_channel_pattern.md`` (basis DOF count, mode
    modulation, environmental coupling, cross-generational memory).
    This first cut is the structural test alone: does the receiver
    declare a basis the claimed channel name does not cover?

    Parameters
    ----------
    receiver
        Any object — typically a driver instance or an encoder. If
        it implements :class:`SupportsShapeChannels`, its declared
        channels are inspected. Otherwise the report is "scalar
        sufficient" by default (no contradictory evidence).
    claimed_channel
        The label the system *claims* its measurement reads —
        ``"intensity"``, ``"concentration"``, ``"current"``. Used
        for the trivial coverage check.
    extra_known_channels
        Optional iterable of channel names the caller already
        accounts for. A receiver that declares ``"polarization"``
        as a shape channel is *not* flagged as hidden if
        ``extra_known_channels`` includes ``"polarization"``.

    Returns
    -------
    HiddenChannelReport
    """
    advertised = shape_channels_of(receiver)
    if not advertised:
        return HiddenChannelReport(
            hidden_channels=(),
            scalar_sufficient=True,
            notes=(
                "receiver advertises no shape channels; "
                "scalar reading is taken as sufficient",
            ),
        )

    known: set = {claimed_channel.lower()}
    if extra_known_channels:
        known |= {c.lower() for c in extra_known_channels}

    hidden = tuple(
        c for c in advertised if c.name.lower() not in known
    )
    notes_list: List[str] = []
    if hidden:
        notes_list.append(
            f"receiver declares {len(hidden)} channel(s) not covered "
            f"by claimed={claimed_channel!r}: "
            f"{[c.name for c in hidden]!r}. Scalar model insufficient."
        )
    else:
        notes_list.append(
            "every advertised channel is covered by the claimed "
            "channel or the extras list"
        )

    return HiddenChannelReport(
        hidden_channels=hidden,
        scalar_sufficient=not bool(hidden),
        notes=tuple(notes_list),
    )


__all__ = [
    "ShapeChannel",
    "SHAPE_CHANNEL_REGISTRY",
    "register_shape_channel",
    "get_shape_channel",
    "SupportsShapeChannels",
    "shape_channels_of",
    "HiddenChannelReport",
    "detect_hidden_channels",
]
