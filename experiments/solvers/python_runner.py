"""python_runner — pure-Python solvers with strict validation.

Two problem families supported: factor_* (Pollard's rho + small-prime sweep)
and nqueens_* (backtracking). Both refuse misrouted or malformed inputs
loudly rather than silently producing nonsense.
"""
from __future__ import annotations

import random
import time
from math import gcd

from dispatcher import Problem, register_runner


def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")


FACTOR_TAG_HINT  = {"bignum", "bitwise", "numeric_tight"}
NQUEENS_TAG_HINT = {"relational", "search"}


def _tags_overlap(problem: Problem, hints: set[str]) -> bool:
    return bool({t.value for t in problem.tags} & hints)


# ─── factor family ──────────────────────────────────────────────

def _pollard_rho(n: int) -> int:
    if n % 2 == 0:
        return 2
    while True:
        x = random.randrange(2, n)
        y = x
        c = random.randrange(1, n)
        d = 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = gcd(abs(x - y), n)
        if d != n:
            return d


def _factor(n: int) -> tuple[int, int]:
    if n % 2 == 0:
        return (2, n // 2)
    p = 3
    while p < 1000 and p * p <= n:
        if n % p == 0:
            return (p, n // p)
        p += 2
    f = _pollard_rho(n)
    g = n // f
    return (min(f, g), max(f, g))


# ─── nqueens family ─────────────────────────────────────────────

def _solve_nqueens(n: int, limit: int) -> list[list[int]]:
    """Backtracking. Returns up to `limit` solutions as column-per-row lists."""
    solutions: list[list[int]] = []
    cols: set[int] = set()
    diag1: set[int] = set()
    diag2: set[int] = set()
    current: list[int] = []

    def backtrack(row: int) -> None:
        if len(solutions) >= limit:
            return
        if row == n:
            solutions.append(current.copy())
            return
        for col in range(1, n + 1):
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                continue
            cols.add(col); diag1.add(row - col); diag2.add(row + col)
            current.append(col)
            backtrack(row + 1)
            current.pop()
            cols.remove(col); diag1.remove(row - col); diag2.remove(row + col)

    backtrack(0)
    return solutions


# ─── dispatch entry point ──────────────────────────────────────

@register_runner("python")
def run_python(problem: Problem) -> tuple[bool, str, float]:
    if _name_matches(problem.name, "factor"):
        if not _tags_overlap(problem, FACTOR_TAG_HINT):
            return False, (f"factor: name='{problem.name}' but tags="
                           f"{[t.value for t in problem.tags]} — refusing misroute"), 0.0
        if "n" not in problem.payload:
            return False, "factor: missing required payload key 'n'", 0.0
        n = problem.payload["n"]
        if not isinstance(n, int):
            return False, f"factor: payload['n'] must be int, got {type(n).__name__}", 0.0
        if n < 4:
            return False, f"factor: n={n} not composite (must be >= 4)", 0.0

        t0 = time.perf_counter()
        p, q = _factor(n)
        elapsed = time.perf_counter() - t0
        if p <= 1 or p >= n or p * q != n:
            return False, f"factor: bogus python result f={p} for n={n}", elapsed
        return True, f"{n} = {p} * {q}", elapsed

    if _name_matches(problem.name, "nqueens"):
        if not _tags_overlap(problem, NQUEENS_TAG_HINT):
            return False, (f"nqueens: name='{problem.name}' but tags="
                           f"{[t.value for t in problem.tags]} — refusing misroute"), 0.0
        if "n" not in problem.payload:
            return False, "nqueens: missing required payload key 'n'", 0.0
        n = problem.payload["n"]
        if not isinstance(n, int) or n < 1:
            return False, f"nqueens: n must be positive int, got {n!r}", 0.0
        limit = problem.payload.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            return False, f"nqueens: limit must be positive int, got {limit!r}", 0.0

        t0 = time.perf_counter()
        sols = _solve_nqueens(n, limit=limit)
        elapsed = time.perf_counter() - t0
        if not sols:
            return False, f"nqueens: no solutions for n={n}", elapsed
        return True, f"n={n}, found {len(sols)} solution(s); first: {sols[0]}", elapsed

    return False, f"no python solver for '{problem.name}'", 0.0
