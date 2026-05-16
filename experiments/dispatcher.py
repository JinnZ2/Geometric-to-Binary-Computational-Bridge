"""
dispatcher.py — polyglot puzzle solver router

Energy flow:
    puzzle + tags  ->  classifier  ->  language ranking  ->  runner  ->  result
         ^                                                                  |
         |                                                                  v
       registry  <–  decision cache  <–––––––––––––––––––––––––––––––––––––+

The dispatcher does ONE job: pick the right language(s) for the problem shape.
It does not solve. Solvers in solvers/ do that.

License: CC0
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Callable


# ═══════════════════════════════════════════════════════════════════
# PROBLEM SHAPES — what KIND of computation does this puzzle need?
# ═══════════════════════════════════════════════════════════════════

class Shape(Enum):
    BITWISE         = "bitwise"          # bit ops, masks, packed ints
    BIGNUM          = "bignum"           # arbitrary-precision arithmetic
    SYMBOLIC        = "symbolic"         # algebra, constraint propagation
    SEARCH          = "search"           # tree/graph/state-space search
    NUMERIC_TIGHT   = "numeric_tight"    # hot inner loop, float-heavy
    RELATIONAL      = "relational"       # n-way matching, joins, set ops
    PARALLEL        = "parallel"         # embarrassingly parallel sweep
    METAPROG        = "metaprog"         # generate code as data
    IO_BOUND        = "io_bound"         # mostly waiting on data


# ═══════════════════════════════════════════════════════════════════
# LANGUAGE PROFILES — affinity for each shape (0.0 - 1.0)
# Higher = better fit. These are PRIORS, updated by registry over time.
# ═══════════════════════════════════════════════════════════════════

LANG_PROFILE: dict[str, dict[Shape, float]] = {
    "python": {
        Shape.BITWISE:       0.30,   # works but slow
        Shape.BIGNUM:        0.90,   # native big ints — actually excellent
        Shape.SYMBOLIC:      0.85,
        Shape.SEARCH:        0.70,
        Shape.NUMERIC_TIGHT: 0.20,   # the pain point
        Shape.RELATIONAL:    0.55,
        Shape.PARALLEL:      0.40,   # GIL tax
        Shape.METAPROG:      0.65,
        Shape.IO_BOUND:      0.75,
    },
    "c": {
        Shape.BITWISE:       0.95,   # native fit
        Shape.BIGNUM:        0.30,   # need GMP, friction
        Shape.SYMBOLIC:      0.15,
        Shape.SEARCH:        0.80,
        Shape.NUMERIC_TIGHT: 0.95,
        Shape.RELATIONAL:    0.30,
        Shape.PARALLEL:      0.80,   # pthreads
        Shape.METAPROG:      0.20,
        Shape.IO_BOUND:      0.50,
    },
    "rust": {
        Shape.BITWISE:       0.90,
        Shape.BIGNUM:        0.55,   # num-bigint crate
        Shape.SYMBOLIC:      0.30,
        Shape.SEARCH:        0.80,
        Shape.NUMERIC_TIGHT: 0.90,
        Shape.RELATIONAL:    0.40,
        Shape.PARALLEL:      0.95,   # fearless concurrency
        Shape.METAPROG:      0.55,
        Shape.IO_BOUND:      0.70,
    },
    "sql": {
        Shape.BITWISE:       0.10,
        Shape.BIGNUM:        0.20,
        Shape.SYMBOLIC:      0.30,
        Shape.SEARCH:        0.50,
        Shape.NUMERIC_TIGHT: 0.20,
        Shape.RELATIONAL:    0.95,   # this is what SQL IS
        Shape.PARALLEL:      0.60,
        Shape.METAPROG:      0.20,
        Shape.IO_BOUND:      0.40,
    },
    "bash": {
        Shape.BITWISE:       0.20,
        Shape.BIGNUM:        0.10,
        Shape.SYMBOLIC:      0.10,
        Shape.SEARCH:        0.20,
        Shape.NUMERIC_TIGHT: 0.05,
        Shape.RELATIONAL:    0.30,
        Shape.PARALLEL:      0.70,   # xargs -P is shockingly good
        Shape.METAPROG:      0.20,
        Shape.IO_BOUND:      0.85,
    },
}


# ═══════════════════════════════════════════════════════════════════
# CLASSIFIER — heuristic for now, learnable later
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Problem:
    name:        str
    description: str
    tags:        list[Shape]            # what shapes does it touch?
    payload:     dict                   # actual data for the solver
    hint_lang:   str | None = None      # user override


def classify(problem: Problem) -> list[Shape]:
    """For now: trust the tags. Later: NLP on description, learned classifier."""
    return problem.tags


# ═══════════════════════════════════════════════════════════════════
# RANKER — given shapes, pick languages
# ═══════════════════════════════════════════════════════════════════

def rank_languages(shapes: list[Shape],
                   profile: dict[str, dict[Shape, float]] = LANG_PROFILE
                   ) -> list[tuple[str, float]]:
    """Score each language by min-fit across required shapes.
    Min (not avg) — a language that's great at 4 shapes and terrible at 1
    will bottleneck on that 1. Min captures the weak link."""
    if not shapes:
        return []
    scored = []
    for lang, affinities in profile.items():
        worst = min(affinities[s] for s in shapes)
        avg   = sum(affinities[s] for s in shapes) / len(shapes)
        # combine: 70% min (bottleneck), 30% avg (overall fit)
        score = 0.7 * worst + 0.3 * avg
        scored.append((lang, score))
    return sorted(scored, key=lambda x: -x[1])


# ═══════════════════════════════════════════════════════════════════
# REGISTRY — decision cache. learns from past runs.
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RunRecord:
    problem_name:    str
    shapes:          list[str]
    language:        str
    wall_time_sec:   float
    success:         bool
    notes:           str = ""


class Registry:
    """Persistent decision cache. Stores what worked for what shape."""
    def __init__(self, path: Path):
        self.path = path
        self.records: list[RunRecord] = []
        if path.exists():
            data = json.loads(path.read_text())
            self.records = [RunRecord(**r) for r in data]

    def record(self, rec: RunRecord) -> None:
        self.records.append(rec)
        self.path.write_text(json.dumps([asdict(r) for r in self.records], indent=2))

    def best_for(self, shapes: list[Shape]) -> str | None:
        """Look up: have we solved this shape combo before? Which lang won?"""
        key = sorted(s.value for s in shapes)
        matches = [r for r in self.records
                   if sorted(r.shapes) == key and r.success]
        if not matches:
            return None
        winner = min(matches, key=lambda r: r.wall_time_sec)
        return winner.language


# ═══════════════════════════════════════════════════════════════════
# DISPATCHER — top-level entry point
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DispatchPlan:
    problem:        Problem
    shapes:         list[Shape]
    language:       str
    reason:         str
    alternatives:   list[tuple[str, float]]


def plan(problem: Problem, registry: Registry | None = None) -> DispatchPlan:
    if problem.hint_lang:
        return DispatchPlan(
            problem=problem,
            shapes=problem.tags,
            language=problem.hint_lang,
            reason="user hint",
            alternatives=[],
        )

    shapes = classify(problem)
    ranking = rank_languages(shapes)

    cached = registry.best_for(shapes) if registry else None
    if cached:
        return DispatchPlan(
            problem=problem,
            shapes=shapes,
            language=cached,
            reason="registry cache: previously won for shape set",
            alternatives=ranking,
        )

    chosen, _ = ranking[0]
    return DispatchPlan(
        problem=problem,
        shapes=shapes,
        language=chosen,
        reason="prior affinity ranking, no cache hit",
        alternatives=ranking,
    )


# ═══════════════════════════════════════════════════════════════════
# RUNNER REGISTRY — wires languages to solver modules
# ═══════════════════════════════════════════════════════════════════

RunnerFn = Callable[[Problem], tuple[bool, str, float]]
RUNNERS: dict[str, RunnerFn] = {}


def register_runner(lang: str):
    def deco(fn: RunnerFn):
        RUNNERS[lang] = fn
        return fn
    return deco


def execute(plan_: DispatchPlan, registry: Registry | None = None
            ) -> tuple[bool, str, float]:
    runner = RUNNERS.get(plan_.language)
    if runner is None:
        return False, f"no runner registered for {plan_.language}", 0.0

    t0 = time.perf_counter()
    success, output, _ = runner(plan_.problem)
    elapsed = time.perf_counter() - t0

    if registry is not None:
        registry.record(RunRecord(
            problem_name=plan_.problem.name,
            shapes=[s.value for s in plan_.shapes],
            language=plan_.language,
            wall_time_sec=elapsed,
            success=success,
        ))
    return success, output, elapsed


# ═══════════════════════════════════════════════════════════════════
# SELF-DEMO
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    p = Problem(
        name="factor_100bit",
        description="factor a ~100-bit semiprime",
        tags=[Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
        payload={"n": 1099511627791 * 1099511628211},
    )
    shapes = classify(p)
    ranking = rank_languages(shapes)
    print(f"problem: {p.name}")
    print(f"shapes:  {[s.value for s in shapes]}")
    print(f"ranking:")
    for lang, score in ranking:
        print(f"   {lang:8s}  {score:.3f}")
