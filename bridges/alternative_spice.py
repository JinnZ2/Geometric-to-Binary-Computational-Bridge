"""
AlternativeSPICE — minimal ternary/stochastic SPICE-like stepper
================================================================

A timestep-driven field backend that treats every node as carrying
three concurrent interpretations of its electrical state:

* a ternary current class (REVERSE / ZERO / FORWARD),
* a stochastic contact probability (via Johnson-Nyquist noise), and
* a frequency-coupled skin-effect descriptor.

This is intentionally *not* a full modified-nodal-analysis SPICE
engine — it is a teaching / diagnostic backend that demonstrates the
branch-point architecture from ``alternative_computing_bridge.md``
without introducing a heavy simulation dependency.

Typical usage
-------------
>>> sim = AlternativeSPICE(frequency_hz=60.0)
>>> sim.add_node("n1", voltage=1.0, conductivity=5.96e7)
>>> state = sim.run(steps=100)
>>> state.ternary_states["n1"] in (-1, 0, 1)
True
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bridges.electric_alternative_compute import (
    QuantumSkinEffect,
    StochasticContactResistance,
    TernaryCurrentState,
    classify_current_ternary,
)


@dataclass
class CircuitState:
    """
    Bookkeeping for one simulation timestep.

    Every dict is keyed by node name. ``ternary_states`` stores the
    integer value of the ternary classification (-1, 0, +1) so the
    state object is trivially serialisable.
    """

    time: float = 0.0
    dt: float = 1e-3

    voltages: Dict[str, float] = field(default_factory=dict)
    currents: Dict[str, float] = field(default_factory=dict)
    conductivities: Dict[str, float] = field(default_factory=dict)

    ternary_states: Dict[str, int] = field(default_factory=dict)
    skin_effects: Dict[str, QuantumSkinEffect] = field(default_factory=dict)
    probabilities: Dict[str, float] = field(default_factory=dict)

    # Full history keyed by node name → list of (time, current, ternary).
    # Populated lazily by ``AlternativeSPICE.record_history``.
    history: Dict[str, List] = field(default_factory=dict)


class AlternativeSPICE:
    """
    Time-stepping simulator over a set of named circuit nodes.

    Parameters
    ----------
    frequency_hz
        Excitation frequency for the sinusoidal voltage source. Also
        drives the skin-effect computation for each node.
    dt
        Timestep in seconds.
    record_history
        When true, each call to ``step`` appends a
        ``(time, current, ternary)`` triple to
        ``state.history[node]``. Off by default to keep long runs
        cheap.
    """

    def __init__(
        self,
        frequency_hz: float = 60.0,
        dt: float = 1e-3,
        record_history: bool = False,
    ) -> None:
        self.frequency_hz = frequency_hz
        self.state = CircuitState(dt=dt)
        self.record_history = record_history

    def add_node(
        self,
        name: str,
        voltage: float = 0.0,
        conductivity: float = 1e-6,
    ) -> "AlternativeSPICE":
        """Register a node with its excitation voltage and conductivity."""
        self.state.voltages[name] = voltage
        self.state.conductivities[name] = conductivity
        if self.record_history:
            self.state.history.setdefault(name, [])
        return self

    def step(self) -> CircuitState:
        """
        Advance one timestep, refreshing ternary / stochastic / skin views.

        Each node's current is taken as ``V_node · sin(2π f t)`` — a
        single-source toy model that is sufficient to exercise the
        ternary zero-crossing logic and the stochastic-contact /
        skin-effect updates.
        """
        t = self.state.time
        phase = 2.0 * math.pi * self.frequency_hz * t

        for node, v in self.state.voltages.items():
            current = math.sin(phase) * v
            ternary = classify_current_ternary(current)

            self.state.currents[node] = current
            self.state.ternary_states[node] = int(ternary)

            sigma = self.state.conductivities[node]
            self.state.probabilities[node] = (
                StochasticContactResistance(conductivity_S=sigma)
                .conducting_probability
            )
            self.state.skin_effects[node] = QuantumSkinEffect(
                frequency_hz=self.frequency_hz,
                conductivity_S=sigma,
            )

            if self.record_history:
                self.state.history[node].append((t, current, int(ternary)))

        self.state.time += self.state.dt
        return self.state

    def run(self, steps: int = 1000) -> CircuitState:
        """Step ``steps`` times and return the final state."""
        for _ in range(steps):
            self.step()
        return self.state

    def ternary_symbols(self) -> Dict[str, str]:
        """Return ``{node: symbol}`` using the TernaryCurrentState symbol map."""
        out: Dict[str, str] = {}
        for node, code in self.state.ternary_states.items():
            out[node] = TernaryCurrentState(code).symbol
        return out


__all__ = ["CircuitState", "AlternativeSPICE"]
