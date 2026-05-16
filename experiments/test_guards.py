"""test_guards.py — regression tests for solver hardening.

Verifies that misrouted or malformed problems FAIL LOUDLY,
not silently produce nonsense like '8 = 2 * 4'.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Problem, Shape, plan, execute
from solvers import python_runner, c_runner, sql_runner, bash_runner


def expect_fail(label: str, problem: Problem, lang: str) -> None:
    p2 = Problem(name=problem.name, description=problem.description,
                 tags=problem.tags, payload=problem.payload, hint_lang=lang)
    dp = plan(p2)
    ok, out, _ = execute(dp)
    status = "PASS" if not ok else "FAIL"
    arrow  = "OK refused" if not ok else "!! BUG — accepted"
    print(f"  [{status}] {label:50s} {arrow}: {out[:60]}")


def expect_pass(label: str, problem: Problem, lang: str) -> None:
    p2 = Problem(name=problem.name, description=problem.description,
                 tags=problem.tags, payload=problem.payload, hint_lang=lang)
    dp = plan(p2)
    ok, out, _ = execute(dp)
    status = "PASS" if ok else "FAIL"
    arrow  = "OK solved" if ok else "!! BUG — refused valid input"
    print(f"  [{status}] {label:50s} {arrow}: {out[:60]}")


if __name__ == "__main__":
    print("=== silent-misroute regression tests ===\n")

    print("category 1: misrouted nqueens-shaped payload as 'factor'")
    # the exact bug Kavik flagged: a problem named "factor_..." with n=8
    # (clearly an n-queens board size) used to produce "8 = 2 * 4"
    p_misroute = Problem(
        name="factor_pattern_8", description="misrouted nqueens",
        tags=[Shape.RELATIONAL, Shape.SEARCH],
        payload={"n": 8},
    )
    expect_fail("factor_pattern_8 with n=8 (would have said 2*4)",
                p_misroute, "python")
    expect_fail("same misroute via C runner",
                p_misroute, "c")

    print("\ncategory 2: name collisions (substring vs prefix)")
    # 'factorial' should NOT match 'factor' family
    p_factorial = Problem(name="factorial_5", description="factorial",
                          tags=[Shape.NUMERIC_TIGHT], payload={"n": 5})
    expect_fail("factorial_5 must not match factor family",
                p_factorial, "python")
    # 'nqueens_graph' should match nqueens family if we want it to
    # — strict prefix policy says yes (nqueens_*) but we don't have solver for it
    # so it falls through correctly

    print("\ncategory 3: missing payload keys")
    p_no_n = Problem(name="factor_x", description="no n",
                     tags=[Shape.BIGNUM], payload={})
    expect_fail("factor_x with empty payload",
                p_no_n, "python")
    expect_fail("factor_x via C runner",
                p_no_n, "c")

    print("\ncategory 4: wrong payload types")
    p_str_n = Problem(name="factor_s", description="string n",
                      tags=[Shape.BIGNUM], payload={"n": "not_an_int"})
    expect_fail("factor with string n",
                p_str_n, "python")

    print("\ncategory 5: trivial / boundary inputs")
    p_tiny = Problem(name="factor_2", description="n=2 prime",
                     tags=[Shape.BIGNUM], payload={"n": 2})
    expect_fail("factor with n=2 (prime, refuse)",
                p_tiny, "python")
    p_one = Problem(name="factor_one", description="n=1",
                    tags=[Shape.BIGNUM], payload={"n": 1})
    expect_fail("factor with n=1",
                p_one, "python")

    print("\ncategory 6: valid inputs still pass through")
    p_real = Problem(name="factor_real", description="valid semiprime",
                     tags=[Shape.BIGNUM], payload={"n": 15})
    expect_pass("factor n=15 (legitimate)",
                p_real, "python")
    p_q = Problem(name="nqueens_4", description="4-queens",
                  tags=[Shape.RELATIONAL], payload={"n": 4})
    expect_pass("nqueens_4 (legitimate)",
                p_q, "python")
    expect_pass("nqueens_4 via SQL",
                p_q, "sql")

    print("\ncategory 7: unknown problem family")
    p_alien = Problem(name="cosmic_ray_trace", description="alien",
                      tags=[Shape.NUMERIC_TIGHT], payload={"n": 100})
    expect_fail("unknown family on python runner",
                p_alien, "python")
    expect_fail("unknown family on C runner",
                p_alien, "c")
    expect_fail("unknown family on SQL runner",
                p_alien, "sql")

    print("\n=== done ===")
