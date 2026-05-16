"""
dispatcher_v2_energetic.py

Same job as dispatcher.py v1 (route problem -> best solver),
but a completely different epistemology.

V1 (sequential / symbolic):
    text problem -> Shape tags -> rank by affinity table -> pick lang

V2 (energetic / substrate):
    problem state vector (no text) -> compute energy cost across substrates
    -> argmin = solver. landscape reshapes as registry observes reality.

What changes:
  - input is NUMERIC (memory_pattern, bit_density, parallelism_grain, …),
    not symbolic tags
  - each language is a POTENTIAL WELL — a function from problem-space to
    energy cost. depth varies by problem location in parameter space.
  - selection is gradient descent: argmin(E(problem, lang)) — no rules
  - learning reshapes the wells (coefficient update), not the rule table

Same registry. Same solvers. Different routing physics.

License: CC0
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable


# ═══════════════════════════════════════════════════════════════════
# PROBLEM STATE — numeric signature, NOT text
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProblemState:
    """A problem as physical parameters. No name, no tags, no description.
    Each axis is a real dimension of the computation.
    All values normalized [0,1] where 1 = maximum on that axis."""

    bit_density:        float   # 0=symbolic strings, 1=raw bit ops
    numeric_intensity:  float   # 0=branchy, 1=tight FP/INT inner loop
    memory_locality:    float   # 0=random/scattered, 1=tight cache-resident
    parallelism_grain:  float   # 0=fully sequential, 1=embarrassingly parallel
    relational_density: float   # 0=imperative, 1=pure set/join semantics
    state_space_size:   float   # 0=tiny, 1=huge search space
    bignum_scale:       float   # 0=fits in word, 1=arbitrary precision
    io_fraction:        float   # 0=pure compute, 1=mostly waiting

    def as_vec(self) -> tuple[float, ...]:
        return (self.bit_density, self.numeric_intensity, self.memory_locality,
                self.parallelism_grain, self.relational_density,
                self.state_space_size, self.bignum_scale, self.io_fraction)

    def axis_names(self) -> tuple[str, ...]:
        return ("bit", "num", "mem", "par", "rel", "stt", "big", "io")


# ═══════════════════════════════════════════════════════════════════
# POTENTIAL WELLS — each language is a function of problem state
# ═══════════════════════════════════════════════════════════════════
#
# Well depth = energy cost when the problem sits at that point in space.
# LOW depth = good fit (steep well draws the problem in).
# Cost decomposes into:  (substrate_overhead + axis_costs)
#
#   substrate_overhead = fixed cost for using this language at all
#                        (subprocess fork, compile, GIL, JIT warmup)
#   axis_cost          = per-axis penalty if the problem is heavy on an axis
#                        the language handles poorly
#
# These are PRIORS. Registry updates them empirically.

@dataclass
class PotentialWell:
    """E(p) = substrate_overhead + sum(weight_i * problem.axis_i)

    Negative weights = the language LIKES that axis (well deepens there).
    Positive weights = the language hates that axis (well shallows).
    """
    name:               str
    substrate_overhead: float                  # base energy to use this lang
    weights:            dict[str, float]       # per-axis cost coefficients

    def energy(self, p: ProblemState) -> float:
        e = self.substrate_overhead
        vals = dict(zip(p.axis_names(), p.as_vec()))
        for axis, w in self.weights.items():
            e += w * vals[axis]
        return e


# ─── INITIAL LANDSCAPE — physics-grounded priors ────────────────────
#
# Read as: "language L has well-depth profile across (bit, num, mem, par,
# rel, stt, big, io)". Negative = good at this. Positive = bad at this.

LANDSCAPE: dict[str, PotentialWell] = {
    "python": PotentialWell(
        name="python",
        substrate_overhead=0.05,    # minimal — already running in-process
        weights={
            "bit":  +0.40,           # slow at raw bit ops (interp overhead)
            "num":  +0.50,           # tight loops are its worst case
            "mem":  +0.10,           # GC + object headers hurt locality
            "par":  +0.20,           # GIL tax
            "rel":  -0.10,           # decent at dicts/sets
            "stt":  -0.15,           # native big search is fine
            "big":  -0.40,           # native arbitrary precision — STRENGTH
            "io":   -0.10,           # async is OK
        }),

    "c": PotentialWell(
        name="c",
        substrate_overhead=0.40,    # fork+exec subprocess cost
        weights={
            "bit":  -0.50,           # native bit ops — STRENGTH
            "num":  -0.55,           # tight loops are its strength
            "mem":  -0.40,           # full control over layout
            "par":  -0.15,           # pthreads but manual
            "rel":  +0.40,           # no native relational
            "stt":  -0.10,
            "big":  +0.40,           # GMP friction
            "io":   +0.10,           # works but boilerplate
        }),

    "rust": PotentialWell(
        name="rust",
        substrate_overhead=0.50,    # compile cost higher than C
        weights={
            "bit":  -0.45,
            "num":  -0.50,
            "mem":  -0.40,
            "par":  -0.50,           # fearless concurrency — DEEPEST par well
            "rel":  +0.35,
            "stt":  -0.10,
            "big":  +0.20,           # num-bigint exists, friction
            "io":   -0.10,
        }),

    "sql": PotentialWell(
        name="sql",
        substrate_overhead=0.10,    # sqlite stdlib — minimal
        weights={
            "bit":  +0.60,
            "num":  +0.55,
            "mem":  +0.20,
            "par":  -0.20,           # native intra-query parallelism
            "rel":  -0.60,           # set/join semantics ARE the lang
            "stt":  +0.10,           # recursive CTE is verbose
            "big":  +0.50,
            "io":   +0.10,
        }),

    "bash": PotentialWell(
        name="bash",
        substrate_overhead=0.30,    # subprocess fork tax
        weights={
            "bit":  +0.50,
            "num":  +0.65,
            "mem":  +0.30,
            "par":  -0.40,           # xargs -P / GNU parallel — STRENGTH
            "rel":  +0.30,
            "stt":  +0.40,
            "big":  +0.60,
            "io":   -0.40,           # io_bound is its native habitat
        }),
}


# ═══════════════════════════════════════════════════════════════════
# DISPATCH — pure gradient descent. no rules, no shape table.
# ═══════════════════════════════════════════════════════════════════

@dataclass
class EnergeticPlan:
    state:            ProblemState
    chosen:           str
    energies:         list[tuple[str, float]]   # all candidates, sorted
    gap_to_runner_up: float                     # selection confidence

    def show(self) -> str:
        lines = [f"  chosen: {self.chosen}   "
                 f"(gap to next: {self.gap_to_runner_up:.3f})"]
        for lang, e in self.energies:
            marker = " <-" if lang == self.chosen else ""
            lines.append(f"    {lang:8s}  E={e:+.3f}{marker}")
        return "\n".join(lines)


def dispatch(state: ProblemState,
             landscape: dict[str, PotentialWell] = LANDSCAPE
             ) -> EnergeticPlan:
    """Roll the problem onto the landscape. It accumulates in the deepest well."""
    energies = [(name, well.energy(state)) for name, well in landscape.items()]
    energies.sort(key=lambda kv: kv[1])
    chosen = energies[0][0]
    gap = energies[1][1] - energies[0][1] if len(energies) > 1 else float("inf")
    return EnergeticPlan(state=state, chosen=chosen, energies=energies,
                         gap_to_runner_up=gap)


# ═══════════════════════════════════════════════════════════════════
# LEARNING — reshape the wells from observation
# ═══════════════════════════════════════════════════════════════════
#
# When a race shows lang X beat lang Y on a problem with axis vector v,
# we DEEPEN X's well along the directions v points (lower its weights
# on those axes), and SHALLOW Y's well along same directions.
#
# This is gradient descent on the REGISTRY, not on the problem.

def update_landscape(landscape: dict[str, PotentialWell],
                     state: ProblemState,
                     measured: dict[str, float],   # lang -> wall_time_sec
                     learning_rate: float = 0.05) -> None:
    """Reshape wells so future runs route closer to observed reality."""
    valid = [(lang, t) for lang, t in measured.items() if t > 0]
    if len(valid) < 2:
        return

    # rank: winner = lang with lowest measured time
    valid.sort(key=lambda kv: kv[1])
    winner = valid[0][0]
    loser  = valid[-1][0]

    axes = dict(zip(state.axis_names(), state.as_vec()))

    # for axes the problem is heavy on, push winner's weights DOWN
    # (deeper well = lower E) and loser's UP
    for axis, val in axes.items():
        # only adjust along axes that matter for this problem (val > 0.3)
        if val < 0.3:
            continue
        landscape[winner].weights[axis] -= learning_rate * val
        landscape[loser ].weights[axis] += learning_rate * val


# ═══════════════════════════════════════════════════════════════════
# BRIDGE — translate v1 Shape tags to v2 ProblemState, for cross-check
# ═══════════════════════════════════════════════════════════════════
#
# When you have a v1-style tagged problem, project it into v2 space.
# Lets us run BOTH dispatchers on the SAME problem and compare picks.

def shape_tags_to_state(tag_names: list[str]) -> ProblemState:
    """Heuristic projection: shape tags -> energetic state vector.

    A real problem-encoder would measure the problem directly. This is the
    compatibility shim for the v1 demo problems."""
    s = {a: 0.0 for a in ("bit", "num", "mem", "par", "rel", "stt", "big", "io")}
    mapping = {
        "bitwise":       {"bit": 1.0, "num": 0.7, "mem": 0.6},
        "bignum":        {"big": 1.0, "num": 0.5},
        "symbolic":      {"stt": 0.8, "rel": 0.3},
        "search":        {"stt": 0.9, "mem": 0.3},
        "numeric_tight": {"num": 1.0, "mem": 0.7},
        "relational":    {"rel": 1.0, "stt": 0.4},
        "parallel":      {"par": 1.0},
        "metaprog":      {"stt": 0.5, "rel": 0.2},
        "io_bound":      {"io": 1.0, "par": 0.5},
    }
    for tag in tag_names:
        for k, v in mapping.get(tag, {}).items():
            s[k] = max(s[k], v)        # take strongest signal per axis
    return ProblemState(
        bit_density=s["bit"], numeric_intensity=s["num"],
        memory_locality=s["mem"], parallelism_grain=s["par"],
        relational_density=s["rel"], state_space_size=s["stt"],
        bignum_scale=s["big"], io_fraction=s["io"],
    )


# ═══════════════════════════════════════════════════════════════════
# SELF-DEMO
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("ENERGETIC DISPATCHER — landscape selection by gradient")
    print("=" * 60)

    # Problem A: tight bitwise numeric (factoring)
    pA = ProblemState(bit_density=1.0, numeric_intensity=1.0, memory_locality=0.7,
                      parallelism_grain=0.0, relational_density=0.0,
                      state_space_size=0.1, bignum_scale=0.4, io_fraction=0.0)
    print(f"\n[A] factoring-like (bit+num heavy)")
    print(dispatch(pA).show())

    # Problem B: relational search (n-queens)
    pB = ProblemState(bit_density=0.0, numeric_intensity=0.0, memory_locality=0.3,
                      parallelism_grain=0.0, relational_density=1.0,
                      state_space_size=0.9, bignum_scale=0.0, io_fraction=0.0)
    print(f"\n[B] relational search (rel+stt heavy)")
    print(dispatch(pB).show())

    # Problem C: parallel sweep
    pC = ProblemState(bit_density=0.0, numeric_intensity=0.3, memory_locality=0.2,
                      parallelism_grain=1.0, relational_density=0.0,
                      state_space_size=0.5, bignum_scale=0.0, io_fraction=0.6)
    print(f"\n[C] parallel sweep (par+io heavy)")
    print(dispatch(pC).show())

    # Problem D: arbitrary-precision symbolic (Python's deepest well)
    pD = ProblemState(bit_density=0.1, numeric_intensity=0.2, memory_locality=0.4,
                      parallelism_grain=0.0, relational_density=0.2,
                      state_space_size=0.6, bignum_scale=1.0, io_fraction=0.0)
    print(f"\n[D] bignum symbolic (big heavy)")
    print(dispatch(pD).show())

    # Show learning: simulate race outcomes that contradict the prior
    print("\n" + "=" * 60)
    print("LEARNING — landscape reshapes from empirical race")
    print("=" * 60)
    measured = {"python": 0.0005, "sql": 0.030}   # python beat SQL on n-queens
    print(f"\nbefore update — n-queens dispatch:")
    print(dispatch(pB).show())
    update_landscape(LANDSCAPE, pB, measured, learning_rate=0.08)
    update_landscape(LANDSCAPE, pB, measured, learning_rate=0.08)
    update_landscape(LANDSCAPE, pB, measured, learning_rate=0.08)
    print(f"\nafter 3 updates — same problem, reshaped landscape:")
    print(dispatch(pB).show())
