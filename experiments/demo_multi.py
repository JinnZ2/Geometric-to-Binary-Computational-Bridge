"""demo_multi.py — race across multiple problem shapes.

Each problem type has a different "natural" language by shape affinity.
We race the available runners and let the registry record the empirical truth.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Problem, Shape, plan, execute, Registry, rank_languages
from solvers import python_runner, c_runner, rust_runner, sql_runner, bash_runner
from pathlib import Path


def race(problem: Problem, langs: list[str], trials: int = 3,
         registry: Registry | None = None) -> dict[str, float]:
    # bit-width is only a meaningful label for number-theoretic operands.
    # n in nqueens / sweep is a structural parameter, not a numeric operand.
    is_numeric_operand = (problem.name == "factor"
                          or problem.name.startswith("factor_"))
    bits = problem.payload.get("n", 0)
    if is_numeric_operand and isinstance(bits, int) and bits:
        bits_str = f"  ({bits.bit_length()} bits)"
    else:
        bits_str = ""
    print(f"\n=== {problem.name}{bits_str} ===")
    print(f"  shapes: {[s.value for s in problem.tags]}")

    ranking = rank_languages(problem.tags)
    print(f"  ranking by prior affinity:")
    for lang, score in ranking[:5]:
        marker = " <-" if lang in langs else ""
        print(f"    {lang:8s}  {score:.3f}{marker}")

    print(f"  running {trials} trials each ({len(langs)} languages):")
    summary = {}
    for lang in langs:
        times = []
        ok_all = True
        skip_reason = None
        for _ in range(trials):
            p_run = Problem(name=problem.name, description=problem.description,
                            tags=problem.tags, payload=problem.payload,
                            hint_lang=lang)
            dp = plan(p_run)
            ok, out, t = execute(dp, registry=registry)
            if not ok:
                skip_reason = out
                break
            times.append(t)
        if skip_reason:
            print(f"    [{lang:6s}] SKIP   {skip_reason[:60]}")
            continue
        avg, best = sum(times)/len(times), min(times)
        print(f"    [{lang:6s}] OK    avg={avg*1000:8.2f}ms  best={best*1000:8.2f}ms")
        summary[lang] = best

    if summary:
        winner = min(summary.items(), key=lambda kv: kv[1])
        print(f"  -> winner: {winner[0]} ({winner[1]*1000:.2f}ms)")
    return summary


if __name__ == "__main__":
    reg_path = Path("/tmp/polyglot_multi.json")
    if reg_path.exists():
        reg_path.unlink()
    reg = Registry(reg_path)

    # warm compilers
    print("warming compiled-language runners...")
    for lang in ("c", "rust"):
        execute(plan(Problem("factor_warm", "warmup",
                             [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
                             {"n": 15}, hint_lang=lang)))

    # ─── FACTORING: bitwise + numeric_tight  -> expect compiled langs to win
    p_factor = Problem(
        "factor_62bit", "62-bit semiprime",
        [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
        {"n": 2147483647 * 2147483659},
    )
    race(p_factor, langs=["python", "c", "rust"], trials=3, registry=reg)

    # ─── N-QUEENS: relational + search  -> expect SQL to compete
    p_queens = Problem(
        "nqueens_8", "8-queens, 5 solutions",
        [Shape.RELATIONAL, Shape.SEARCH],
        {"n": 8, "limit": 5},
    )
    race(p_queens, langs=["python", "sql"], trials=3, registry=reg)

    # ─── PARALLEL SWEEP: parallel + io_bound  -> bash xargs -P shines
    p_sweep = Problem(
        "parallel_prime_sweep", "count primes in [1, 50000]",
        [Shape.PARALLEL, Shape.IO_BOUND],
        {"lo": 1, "hi": 50000, "workers": 4},
    )
    race(p_sweep, langs=["python", "bash"], trials=2, registry=reg)

    # ─── REGISTRY READOUT ──────────────────────────────────────
    print("\n=== registry final state ===")
    for r in reg.records:
        if r.success:
            print(f"  {r.problem_name:30s}  {r.language:8s}  "
                  f"{r.wall_time_sec*1000:8.2f}ms  shapes={r.shapes}")
