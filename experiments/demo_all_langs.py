"""demo_all_langs.py — 13-language dispatch demo.

Shows:
  1. v2 energetic landscape ranking across all 13 languages
  2. graceful skip when compiler is absent
  3. empirical race among AVAILABLE langs
  4. registry records reality

Languages in landscape: python, c, rust, sql, bash,
                       cobol, lisp, julia, fortran, go,
                       perl, node, awk
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Problem, Shape, plan, execute, Registry, rank_languages
from dispatcher_v2_energetic import dispatch as v2_dispatch, shape_tags_to_state

# import all runners — each registers itself, gracefully skips if compiler missing
from solvers import (
    python_runner, c_runner, rust_runner, sql_runner, bash_runner,
    cobol_runner, lisp_runner, julia_runner, fortran_runner, go_runner,
    perl_runner, node_runner, awk_runner,
)
from pathlib import Path


def show_ranking(problem: Problem) -> None:
    print(f"\n=== {problem.name} ===")
    print(f"  tags: {[s.value for s in problem.tags]}")

    print("\n  V1 affinity ranking (top 8):")
    v1 = rank_languages(problem.tags)
    for lang, score in v1[:8]:
        print(f"    {lang:8s}  {score:+.3f}")

    print("\n  V2 energetic landscape (top 8):")
    state = shape_tags_to_state([s.value for s in problem.tags])
    v2 = v2_dispatch(state)
    for lang, e in v2.energies[:8]:
        marker = " <- argmin" if lang == v2.chosen else ""
        print(f"    {lang:8s}  E={e:+.3f}{marker}")


def race_all_available(problem: Problem, candidates: list[str],
                       trials: int = 3) -> dict[str, float]:
    print(f"\n  racing {len(candidates)} candidate languages:")
    results: dict[str, float] = {}
    skipped: list[tuple[str, str]] = []
    for lang in candidates:
        times = []
        skip_reason = None
        for _ in range(trials):
            p_run = Problem(name=problem.name, description=problem.description,
                            tags=problem.tags, payload=problem.payload,
                            hint_lang=lang)
            dp = plan(p_run)
            ok, out, t = execute(dp)
            if not ok:
                skip_reason = out
                break
            times.append(t)
        if skip_reason:
            skipped.append((lang, skip_reason[:50]))
            continue
        best = min(times)
        results[lang] = best
        print(f"    [{lang:8s}] OK    best={best*1000:8.2f}ms")
    if skipped:
        print(f"\n  skipped (compiler/runtime missing):")
        for lang, reason in skipped:
            print(f"    [{lang:8s}] {reason}")
    return results


if __name__ == "__main__":
    print("=" * 64)
    print("13-LANGUAGE DISPATCH DEMO")
    print("=" * 64)

    # ─── FACTORING ──────────────────────────────────────────────
    # candidates: any lang with a factor solver
    p_factor = Problem(
        "factor_60bit", "60-bit semiprime",
        [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
        {"n": 982451653 * 982451707},
    )
    show_ranking(p_factor)
    factor_results = race_all_available(
        p_factor,
        ["python", "c", "rust", "cobol", "lisp", "perl"],
        trials=3,
    )
    if factor_results:
        winner = min(factor_results.items(), key=lambda kv: kv[1])
        print(f"\n  -> empirical winner: {winner[0]} ({winner[1]*1000:.2f}ms)")

    # ─── N-QUEENS ───────────────────────────────────────────────
    p_queens = Problem(
        "nqueens_8", "8-queens, 5 solutions",
        [Shape.RELATIONAL, Shape.SEARCH],
        {"n": 8, "limit": 5},
    )
    show_ranking(p_queens)
    queens_results = race_all_available(
        p_queens,
        ["python", "sql", "lisp"],
        trials=3,
    )
    if queens_results:
        winner = min(queens_results.items(), key=lambda kv: kv[1])
        print(f"\n  -> empirical winner: {winner[0]} ({winner[1]*1000:.2f}ms)")

    # ─── PARALLEL SWEEP ─────────────────────────────────────────
    p_sweep = Problem(
        "parallel_prime_sweep", "primes in [1, 30000]",
        [Shape.PARALLEL, Shape.IO_BOUND, Shape.NUMERIC_TIGHT],
        {"lo": 1, "hi": 30000, "workers": 4},
    )
    show_ranking(p_sweep)
    sweep_results = race_all_available(
        p_sweep,
        ["python", "bash", "julia", "fortran", "go", "node", "awk"],
        trials=2,
    )
    if sweep_results:
        winner = min(sweep_results.items(), key=lambda kv: kv[1])
        print(f"\n  -> empirical winner: {winner[0]} ({winner[1]*1000:.2f}ms)")

    print(f"\n{'='*64}")
    print("DONE — landscape priors set for 13 langs, "
          "available langs raced empirically")
    print(f"{'='*64}")
