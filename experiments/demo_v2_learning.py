"""demo_v2_learning.py — feed empirical race results into v2 landscape.

Shows the energetic dispatcher LEARNING from observation:

  - prior: SQL deepest well on (rel, stt) — affinity table guess
  - reality: python crushed SQL by ~100x on n-queens
  - update_landscape() reshapes wells -> python's (rel, stt) well deepens
  - subsequent dispatch picks python for the same problem class

This is what Kavik flagged: cross-cutting empirical correction.
The two outstanding patches together (sql_runner + python guards) made
the measurement trustworthy. Now we use it.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Problem, Shape, plan as v1_plan, execute, Registry
from dispatcher_v2_energetic import (
    ProblemState, dispatch, LANDSCAPE, update_landscape, shape_tags_to_state,
)
from solvers import python_runner, c_runner, sql_runner, bash_runner
from pathlib import Path
import time


def race_for_real(problem: Problem, langs: list[str], trials: int = 5
                  ) -> dict[str, float]:
    """Measure wall-time per language. Returns best-of-N per lang."""
    out: dict[str, float] = {}
    for lang in langs:
        times = []
        for _ in range(trials):
            p_run = Problem(name=problem.name, description=problem.description,
                            tags=problem.tags, payload=problem.payload,
                            hint_lang=lang)
            ok, _, t = execute(v1_plan(p_run))
            if not ok:
                times = []
                break
            times.append(t)
        if times:
            out[lang] = min(times)
    return out


def show_landscape_slice(state: ProblemState, langs: list[str]) -> None:
    plan_ = dispatch(state)
    chosen = plan_.chosen
    print(f"    landscape at this state:")
    for lang, e in plan_.energies:
        if lang in langs:
            tag = " <- chosen" if lang == chosen else ""
            print(f"      {lang:8s}  E={e:+.3f}{tag}")


if __name__ == "__main__":
    print("=" * 64)
    print("V2 LANDSCAPE LEARNING — empirical correction of (rel, stt) prior")
    print("=" * 64)

    # n-queens problem in v2 state space
    state = shape_tags_to_state(["relational", "search"])
    print(f"\nn-queens state vector:")
    for axis, val in zip(state.axis_names(), state.as_vec()):
        if val > 0:
            print(f"  {axis} = {val}")

    print("\n--- BEFORE observation (prior landscape) ---")
    show_landscape_slice(state, ["python", "sql"])

    # run the actual race
    problem = Problem(
        name="nqueens_8", description="8-queens",
        tags=[Shape.RELATIONAL, Shape.SEARCH],
        payload={"n": 8, "limit": 5},
    )
    print("\n--- measuring empirical reality (5 trials each) ---")
    measured = race_for_real(problem, ["python", "sql"], trials=5)
    for lang, t in measured.items():
        print(f"  {lang:8s}  best={t*1000:8.3f}ms")

    if "python" in measured and "sql" in measured:
        ratio = measured["sql"] / measured["python"]
        print(f"  -> python is {ratio:.0f}x faster")

    # feed measurements into the landscape — multiple updates for clarity
    print("\n--- feeding measurements to update_landscape() x5 ---")
    for _ in range(5):
        update_landscape(LANDSCAPE, state, measured, learning_rate=0.05)

    print("\n--- AFTER learning (reshaped landscape) ---")
    show_landscape_slice(state, ["python", "sql"])

    # show the weight shift
    print("\n--- weight changes for python on (rel, stt) ---")
    py  = LANDSCAPE["python"]
    sql = LANDSCAPE["sql"]
    print(f"  python.rel = {py.weights['rel']:+.3f}  "
          f"(prior was -0.100 — should be more negative now)")
    print(f"  python.stt = {py.weights['stt']:+.3f}  "
          f"(prior was -0.150)")
    print(f"  sql.rel    = {sql.weights['rel']:+.3f}  "
          f"(prior was -0.600 — should be less negative now)")
    print(f"  sql.stt    = {sql.weights['stt']:+.3f}  "
          f"(prior was +0.100)")

    print("\n--- interpretation ---")
    print("  python's (rel, stt) well DEEPENED — it pulls relational/search "
          "problems\n  toward itself by lower energy cost.")
    print("  sql's (rel, stt) well SHALLOWED — its rel-affinity prior was "
          "overweighted\n  for problems at this scale (small board, "
          "low cardinality).")
    print("\n  next dispatch for an nqueens-shaped state will pick python "
          "by gradient.\n  no rule was edited. landscape simply remembered "
          "what won.")
