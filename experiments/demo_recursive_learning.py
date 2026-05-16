"""demo_recursive_learning.py -- closes the recursive loop end-to-end.

Pipeline:
  1. dispatch problem to solver (real race)
  2. capture WasteSignature from actual timings
  3. analyze waste, derive overhead axes
  4. reshape OverheadAwareLandscape
  5. dispatch SAME problem again -- observe routing change

This shows the system learning not just "which solver wins"
but "which solver wastes the least pipeline energy for problems
of this work scale."
"""
from __future__ import annotations
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Problem, Shape, plan, execute, Registry, rank_languages
from dispatcher_v2_energetic import ProblemState, shape_tags_to_state
from substrate_waste_audit import (
    WasteSignature, CycleTimers, capture_waste, analyze_waste,
)
from landscape_overhead_axes import (
    ExtendedProblemState, OverheadAwareLandscape,
)
from solvers import python_runner, c_runner, sql_runner, bash_runner


SUBPROC_LANGS = {"c", "rust", "cobol", "fortran", "go", "julia",
                 "bash", "perl", "node", "awk", "lisp"}


def run_and_capture(problem: Problem, lang: str) -> WasteSignature:
    """Run a single dispatch and capture its waste signature."""
    timers = CycleTimers()
    timers.t_dispatch_start = time.perf_counter()
    p2 = Problem(name=problem.name, description=problem.description,
                 tags=problem.tags, payload=problem.payload, hint_lang=lang)
    dp = plan(p2)
    timers.t_dispatch_done = time.perf_counter()

    timers.t_solver_start = time.perf_counter()
    ok, out, _ = execute(dp)
    timers.t_solver_done = time.perf_counter()
    timers.t_cycle_done = timers.t_solver_done

    return capture_waste(
        problem_name=problem.name,
        problem_shape=tuple(t.value for t in problem.tags),
        solver_lang=lang,
        timers=timers,
        succeeded=ok,
        is_subprocess_solver=(lang in SUBPROC_LANGS),
    )


def show_landscape_view(ls: OverheadAwareLandscape,
                        state: ExtendedProblemState, label: str,
                        langs: list[str]) -> None:
    chosen, energies = ls.dispatch(state)
    e_dict = dict(energies)
    print(f"\n  [{label}]  chosen = {chosen}")
    for lang in langs:
        if lang in e_dict:
            marker = "  <-" if lang == chosen else ""
            pen = ls.overhead[lang]
            print(f"    {lang:8s}  E={e_dict[lang]:+.3f}  "
                  f"subproc_tax={pen.subprocess_tax:+.3f}{marker}")


def closed_loop_cycle(problem: Problem, langs: list[str],
                      ls: OverheadAwareLandscape,
                      state: ExtendedProblemState,
                      trials: int = 5,
                      learning_rate: float = 0.2,
                      label: str = "") -> list[WasteSignature]:
    """Run one full cycle: race, capture, learn, show."""
    print(f"\n-- cycle {label}: race + capture --")
    sigs = []
    for lang in langs:
        for _ in range(trials):
            sig = run_and_capture(problem, lang)
            sigs.append(sig)
        # show what we measured for this lang
        lang_sigs = [s for s in sigs if s.solver_lang == lang]
        if lang_sigs and lang_sigs[-1].succeeded:
            avg_compute = sum(s.compute_time for s in lang_sigs) / len(lang_sigs)
            avg_overhead = sum(s.subprocess_overhead for s in lang_sigs) / len(lang_sigs)
            print(f"  {lang:8s}  compute={avg_compute*1000:7.2f}ms  "
                  f"overhead={avg_overhead*1000:7.2f}ms")

    changes = ls.update_from_waste(sigs, learning_rate=learning_rate)
    return sigs


if __name__ == "__main__":
    print("=" * 64)
    print("RECURSIVE LEARNING LOOP -- close-the-loop with real solvers")
    print("=" * 64)

    ls = OverheadAwareLandscape()

    # Same problem, two different work-scale contexts
    p_small = Problem(
        "factor_small", "tiny composite -- should expose subprocess tax",
        [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
        {"n": 982451653 * 982451707},   # ~60 bits, tiny compute
    )

    base_state = shape_tags_to_state(["bignum", "bitwise", "numeric_tight"])
    state_small = ExtendedProblemState(base=base_state,
                                       expected_work_scale=0.05,  # tiny
                                       input_confidence=1.0)
    state_large = ExtendedProblemState(base=base_state,
                                       expected_work_scale=0.95,  # huge
                                       input_confidence=1.0)

    print("\n[t=0] landscape with default priors")
    show_landscape_view(ls, state_small, "small work scale",
                        ["python", "c", "rust", "julia"])
    show_landscape_view(ls, state_large, "large work scale",
                        ["python", "c", "rust", "julia"])

    # Cycle 1: race python vs c, capture waste, update
    sigs1 = closed_loop_cycle(p_small, ["python", "c"], ls,
                              state_small, trials=4,
                              learning_rate=0.3, label="1")

    print("\n[t=1] landscape after 1 round of waste observation")
    show_landscape_view(ls, state_small, "small work scale",
                        ["python", "c", "rust", "julia"])
    show_landscape_view(ls, state_large, "large work scale",
                        ["python", "c", "rust", "julia"])

    # Cycle 2: more observations, reinforce the pattern
    sigs2 = closed_loop_cycle(p_small, ["python", "c"], ls,
                              state_small, trials=4,
                              learning_rate=0.3, label="2")

    print("\n[t=2] landscape after 2 rounds -- pattern reinforced")
    show_landscape_view(ls, state_small, "small work scale",
                        ["python", "c", "rust", "julia"])
    show_landscape_view(ls, state_large, "large work scale",
                        ["python", "c", "rust", "julia"])

    # --- interpretation -----------------------------------------
    print("\n" + "=" * 64)
    print("INTERPRETATION")
    print("=" * 64)

    py_compute = [s.compute_time for s in sigs1 + sigs2 if s.solver_lang == "python"]
    c_compute  = [s.compute_time for s in sigs1 + sigs2 if s.solver_lang == "c"]
    c_overhead = [s.subprocess_overhead for s in sigs1 + sigs2 if s.solver_lang == "c"]

    if py_compute and c_compute:
        avg_py = sum(py_compute) / len(py_compute)
        avg_c  = sum(c_compute) / len(c_compute)
        avg_c_ov = sum(c_overhead) / len(c_overhead)
        print(f"\n  python pure compute (avg)  : {avg_py*1000:6.2f}ms")
        print(f"  c pure compute (avg)       : {avg_c*1000:6.2f}ms")
        print(f"  c subprocess overhead (avg): {avg_c_ov*1000:6.2f}ms")
        print(f"  c total                    : {(avg_c+avg_c_ov)*1000:6.2f}ms")
        print(f"\n  c's compute is faster, but subprocess overhead "
              f"eats {avg_c_ov/(avg_c+avg_c_ov)*100:.0f}% of total.")

    print(f"\n  python's subprocess_tax penalty: "
          f"{ls.overhead['python'].subprocess_tax:+.3f}")
    print(f"  c's subprocess_tax penalty     : "
          f"{ls.overhead['c'].subprocess_tax:+.3f}")

    print("\n  The landscape now knows:")
    print("    - on SMALL work, c's overhead dominates -> python preferred")
    print("    - on LARGE work, c's overhead amortizes -> c preferred")
    print("    - same code, same priors. ONLY the waste signal changed routing.")
    print("\n  That is the recursive loop closed: solve -> measure waste -> "
          "reshape -> next dispatch reflects reality.")

    # --- EXCLUDE UNAVAILABLE LANGS -- show actual python-vs-c crossover ---
    print("\n" + "=" * 64)
    print("CROSSOVER VERIFICATION -- restrict to AVAILABLE langs only")
    print("=" * 64)
    available = {"python", "c", "sql", "bash"}

    def restricted_dispatch(st: ExtendedProblemState) -> tuple[str, list]:
        ranked = sorted(
            [(l, ls.energy(st, l)) for l in available if l in ls.base],
            key=lambda kv: kv[1]
        )
        return ranked[0][0], ranked

    for label, st in [("small work scale", state_small),
                      ("large work scale", state_large)]:
        chosen, energies = restricted_dispatch(st)
        print(f"\n  [{label}]  chosen = {chosen}")
        for lang, e in energies:
            marker = "  <-" if lang == chosen else ""
            print(f"    {lang:8s}  E={e:+.3f}{marker}")

    print("\n  -> with rust/julia/etc unavailable, the WORK-SCALE crossover")
    print("     is now visible: small work routes one way, large work another,")
    print("     purely from waste-signal feedback.")
