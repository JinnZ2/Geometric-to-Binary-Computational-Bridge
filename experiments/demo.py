"""demo.py — polyglot dispatch in action

Three things demonstrated:
  1. shape-based ranking
  2. real wall-time race (Python vs C, multiple trials)
  3. registry learns: second pass with no hint picks the prior winner
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Problem, Shape, plan, execute, Registry, rank_languages
from solvers import python_runner, c_runner   # registers runners
from pathlib import Path


def race(problem: Problem, trials: int = 5, registry: Registry | None = None) -> None:
    print(f"\n=== {problem.name}  ({problem.payload['n'].bit_length()} bits) ===")
    print(f"  shapes: {[s.value for s in problem.tags]}")

    ranking = rank_languages(problem.tags)
    print(f"  affinity ranking (top 3):")
    for lang, score in ranking[:3]:
        print(f"    {lang:8s}  {score:.3f}")

    print(f"  running {trials} trials per language:")
    summary = {}
    for lang in ("python", "c"):
        times = []
        ok_all = True
        for _ in range(trials):
            p_run = Problem(name=problem.name, description=problem.description,
                            tags=problem.tags, payload=problem.payload,
                            hint_lang=lang)
            dp = plan(p_run)
            ok, out, t = execute(dp, registry=registry)
            ok_all = ok_all and ok
            times.append(t)
        avg = sum(times) / len(times)
        best = min(times)
        status = "OK" if ok_all else "FAIL"
        print(f"    [{lang:6s}] {status}  avg={avg*1000:7.2f}ms  best={best*1000:7.2f}ms")
        summary[lang] = best

    if summary.get("c", 0) > 0:
        ratio = summary["python"] / summary["c"]
        if ratio > 1:
            print(f"  -> C is {ratio:.1f}x faster on best-of-{trials}")
        else:
            print(f"  -> Python is {1/ratio:.1f}x faster (IPC tax > compute gain)")


if __name__ == "__main__":
    reg_path = Path("/tmp/polyglot_registry.json")
    if reg_path.exists():
        reg_path.unlink()
    reg = Registry(reg_path)

    # warm up C compile
    print("warming C runner (one-time compile)...")
    warm = Problem("factor_warm", "warmup",
                   [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
                   {"n": 15}, hint_lang="c")
    execute(plan(warm))
    print("ready.")

    # 60-bit
    p1 = Problem("factor_60bit", "60-bit semiprime",
                 [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
                 {"n": 982451653 * 982451707})
    race(p1, trials=5, registry=reg)

    # 62-bit — harder
    p2 = Problem("factor_62bit", "62-bit semiprime",
                 [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
                 {"n": 2147483647 * 2147483659})
    race(p2, trials=5, registry=reg)

    print("\n--- registry decision (no hint, shape-only) ---")
    p1_nohint = Problem("factor_60bit", "60-bit semiprime",
                        [Shape.BIGNUM, Shape.BITWISE, Shape.NUMERIC_TIGHT],
                        {"n": 982451653 * 982451707})
    dp = plan(p1_nohint, registry=reg)
    print(f"  shapes -> picked: {dp.language}")
    print(f"  reason: {dp.reason}")
