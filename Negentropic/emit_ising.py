"""
Emit target: probabilistic-bit / Ising substrates.

Thermodynamic computing hardware stopped being a thought experiment.
p-bit machines (Camsari, Faria & Datta) and Ising annealers execute
sampling directly in physical noise instead of simulating it, which makes
them the natural destination for a framework whose state variable is a
population of coupled phases with a noise term. This module is the bridge's
emit path to that substrate.

The mapping is the standard one. A Kuramoto population is an XY model with
mean-field coupling; binarising each phase to its sign gives a
fully-connected Ising model::

    s_i = sign(cos theta_i)          spin
    J_ij = K / n                     coupling, ferromagnetic for K > 0
    h_i  = omega_i                   local bias from natural frequency

and the p-bit update rule is::

    s_i  <-  sign( tanh( beta * (sum_j J_ij s_j + h_i) ) - U(-1, 1) )

which is Gibbs sampling of the same Ising energy, implemented as one
comparison against a uniform random number -- one line in software, one
stochastic device in hardware.

Alongside the spin encoding this module emits the repository's native
3-bit octahedral encoding of each phase, Gray coded so that adjacent
octants differ in one bit (CLAUDE.md, development guideline 3). The two
encodings are complementary: spins are what the annealer anneals, the
octahedral triples are what the rest of this repository reads.

Dissipation is not free on this substrate either. Every p-bit flip that
destroys information costs at least ``k_B T ln 2``; :func:`flip_cost_floor`
reports the floor for a run, so a claimed energy advantage can be checked
against it rather than asserted.

Stdlib only.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

__all__ = [
    "IsingSpec",
    "from_core",
    "energy",
    "pbit_sweep",
    "anneal",
    "phase_to_octahedral_gray",
    "octahedral_bits",
    "spins_to_bits",
    "flip_cost_floor",
]

TWO_PI = 2.0 * math.pi


@dataclass
class IsingSpec:
    """A fully-connected Ising problem ready for a p-bit substrate.

    Attributes
    ----------
    n : int
        Number of spins.
    couplings : list of list of float
        Symmetric ``J_ij`` with zero diagonal.
    biases : list of float
        Local fields ``h_i``.
    beta : float
        Inverse temperature used by the sampler. On hardware this is set by
        the device's noise scale, not chosen.
    """

    n: int
    couplings: List[List[float]]
    biases: List[float]
    beta: float = 1.0
    metadata: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.n < 1:
            raise ValueError("n must be positive")
        if len(self.couplings) != self.n or any(len(row) != self.n for row in self.couplings):
            raise ValueError(f"couplings must be {self.n}x{self.n}")
        if len(self.biases) != self.n:
            raise ValueError(f"biases must have length {self.n}")
        if self.beta <= 0.0:
            raise ValueError("beta must be positive")


def from_core(core, beta: float = 1.0) -> IsingSpec:
    """Build an :class:`IsingSpec` from a :class:`core.DissipativeCore`.

    Uses the core's coupling strength and natural frequencies, not its
    instantaneous phases: the spec is the *problem*, and the phases are one
    sample of its solution.  Use :func:`spins_to_bits` on
    ``[sign(cos theta_i)]`` if you want to seed the annealer from the
    core's current state.
    """
    n = core.n
    j = core.K / n
    couplings = [[0.0 if i == k else j for k in range(n)] for i in range(n)]
    return IsingSpec(
        n=n,
        couplings=couplings,
        biases=list(core.omega),
        beta=beta,
        metadata={"K": float(core.K), "Dn": float(core.Dn)},
    )


def energy(spec: IsingSpec, spins: Sequence[int]) -> float:
    """Ising energy ``-sum_{i<j} J_ij s_i s_j - sum_i h_i s_i``."""
    if len(spins) != spec.n:
        raise ValueError(f"expected {spec.n} spins")
    total = 0.0
    for i in range(spec.n):
        for k in range(i + 1, spec.n):
            total -= spec.couplings[i][k] * spins[i] * spins[k]
        total -= spec.biases[i] * spins[i]
    return total


def pbit_sweep(spec: IsingSpec, spins: List[int],
               rng: Optional[random.Random] = None,
               beta: Optional[float] = None) -> int:
    """One asynchronous p-bit sweep, updating ``spins`` in place.

    Returns the number of spins that actually changed, which is the count
    :func:`flip_cost_floor` charges for.

    Asynchronous is not a detail: updating every spin from the same
    snapshot breaks detailed balance on a frustrated problem and the chain
    no longer samples the Boltzmann distribution.
    """
    r = rng or random
    b = spec.beta if beta is None else beta
    flips = 0
    order = list(range(spec.n))
    r.shuffle(order)
    for i in order:
        local = spec.biases[i] + sum(
            spec.couplings[i][k] * spins[k] for k in range(spec.n) if k != i
        )
        new = 1 if math.tanh(b * local) > r.uniform(-1.0, 1.0) else -1
        if new != spins[i]:
            flips += 1
        spins[i] = new
    return flips


def anneal(spec: IsingSpec, sweeps: int = 200,
           beta_start: float = 0.1, beta_end: float = 5.0,
           spins: Optional[Sequence[int]] = None,
           seed: Optional[int] = None) -> Dict[str, object]:
    """Geometric beta ramp over ``sweeps`` p-bit sweeps.

    Returns the final ``spins``, the final and best ``energy``, and the
    total ``flips`` -- the last so the run's Landauer floor can be computed.
    """
    if sweeps < 1:
        raise ValueError("sweeps must be at least 1")
    if beta_start <= 0.0 or beta_end <= 0.0:
        raise ValueError("beta values must be positive")

    rng = random.Random(seed)
    state = list(spins) if spins is not None else [rng.choice((-1, 1)) for _ in range(spec.n)]
    if len(state) != spec.n:
        raise ValueError(f"expected {spec.n} spins")

    ratio = (beta_end / beta_start) ** (1.0 / max(1, sweeps - 1))
    beta = beta_start
    total_flips = 0
    best = energy(spec, state)
    best_state = list(state)

    for _ in range(sweeps):
        total_flips += pbit_sweep(spec, state, rng, beta=beta)
        e = energy(spec, state)
        if e < best:
            best, best_state = e, list(state)
        beta *= ratio

    return {
        "spins": state,
        "energy": energy(spec, state),
        "best_energy": best,
        "best_spins": best_state,
        "flips": total_flips,
    }


# ---------------------------------------------------------------------------
# Octahedral encoding -- the repository's native 3 bits per unit
# ---------------------------------------------------------------------------

def phase_to_octahedral_gray(theta: float) -> int:
    """Map a phase to one of 8 octants, Gray coded.

    Silicon's octahedral coordination gives 8 states, 3 bits per unit
    (CLAUDE.md). Gray coding means neighbouring octants differ in exactly
    one bit, so a phase drifting across a boundary flips one bit rather
    than up to three -- the stability property the repository requires of
    every continuous-to-binary conversion.
    """
    octant = int(((theta + math.pi) % TWO_PI) / TWO_PI * 8) % 8
    return octant ^ (octant >> 1)


def octahedral_bits(theta: float) -> str:
    """Three-bit Gray-coded octahedral encoding of a phase, as a string."""
    return format(phase_to_octahedral_gray(theta), "03b")


def spins_to_bits(spins: Sequence[int]) -> str:
    """Pack Ising spins into a bit string, ``-1 -> 0`` and ``+1 -> 1``."""
    return "".join("1" if s > 0 else "0" for s in spins)


def flip_cost_floor(flips: int, temperature: float) -> float:
    """Landauer floor, in joules, for a run that performed ``flips`` flips.

    ``flips * k_B T ln 2``. This is the irreducible cost of the
    irreversible updates alone; a real device also pays for control,
    readout, and everything that is not the bit flip. Quote it as a floor,
    never as an estimate of what the hardware will draw.
    """
    if flips < 0:
        raise ValueError("flips must be non-negative")
    from Negentropic.landauer import landauer_floor

    return flips * landauer_floor(temperature)


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Negentropic.core import DissipativeCore

    core = DissipativeCore(n=24, K=1.5, Dn=0.045, dt=0.02, seed=3)
    core.run(steps=100, burn_in=100)

    spec = from_core(core, beta=1.0)
    print(f"IsingSpec: n={spec.n}  J={spec.couplings[0][1]:.4f}  "
          f"h range=[{min(spec.biases):+.3f}, {max(spec.biases):+.3f}]")

    seeded = [1 if math.cos(t) >= 0 else -1 for t in core.theta]
    print(f"  seeded from core phases: {spins_to_bits(seeded)}")
    print(f"  seed energy:  {energy(spec, seeded):+.4f}")

    result = anneal(spec, sweeps=300, spins=seeded, seed=11)
    print(f"  annealed:     {spins_to_bits(result['best_spins'])}")
    print(f"  best energy:  {result['best_energy']:+.4f} "
          f"after {result['flips']} flips")
    print(f"  Landauer floor for the run at 300 K: "
          f"{flip_cost_floor(int(result['flips']), 300.0):.4e} J")

    print("\n  octahedral Gray encoding of the first 6 phases:")
    for t in core.theta[:6]:
        print(f"    theta={t:+.4f}  ->  {octahedral_bits(t)}")
