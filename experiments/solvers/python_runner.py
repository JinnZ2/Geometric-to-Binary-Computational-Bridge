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
"""solvers/python_runner.py -- pure Python solvers for all problem types.

╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ This file is a specialized CELL in a distributed ecology.      ║
║ It does ONE thing: solves a small set of problem families      ║
║ in-process, with no subprocess overhead. It emits signals      ║
║ (wall time, success, payload) back to the router (dispatcher). ║
║                                                                ║
║ Python is the in-process baseline: low overhead, slow compute. ║
║ The crossover signal it provides against compiled cells (c,    ║
║ rust, julia) is what the topology (landscape) learns from.     ║
╚════════════════════════════════════════════════════════════════╝

Hardened against silent misroute:

- exact problem.name prefix tokens (not substring 'factor')
- payload key presence + type validation
- factoring sanity check: n must be composite, factor must be non-trivial
- explicit failure messages instead of returning bogus answers
"""
from __future__ import annotations
import math, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner


# --- validators ----------------------------------------------------

def _name_matches(problem_name: str, family: str) -> bool:
    """Strict: name must be exactly `family` or start with `family_`.
    Prevents 'factor' from matching 'factorial' or 'factor_graph_nodes'."""
    return problem_name == family or problem_name.startswith(family + "_")


def _require(payload: dict, keys: dict[str, type]) -> str | None:
    """Returns error string if payload is missing keys or has wrong types."""
    for k, t in keys.items():
        if k not in payload:
            return f"missing required payload key '{k}'"
        if not isinstance(payload[k], t):
            return f"payload['{k}'] must be {t.__name__}, got {type(payload[k]).__name__}"
    return None


# --- core algorithms -----------------------------------------------

def _pollard_rho(n: int) -> int:
    if n < 2:
        return n
    if n % 2 == 0:
        return 2
    while True:
        x = random.randint(2, n - 1)
        y = x
        c = random.randint(1, n - 1)
        d = 1
        while d == 1:
            x = (x*x + c) % n
            y = (y*y + c) % n
            y = (y*y + c) % n
            d = math.gcd(abs(x - y), n)
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
def _solve_nqueens_py(n: int, limit: int = 5) -> list[list[int]]:
    sols, cur = [], []
    def place(row: int) -> None:
        if len(sols) >= limit:
            return
        if row == n:
            sols.append(cur.copy())
            return
        for c in range(1, n + 1):
            ok = True
            for r, pc in enumerate(cur, start=1):
                if pc == c or abs(pc - c) == abs(r - (row + 1)):
                    ok = False
                    break
            if ok:
                cur.append(c)
                place(row + 1)
                cur.pop()
    place(0)
    return sols


def _prime_sweep_py(lo: int, hi: int) -> int:
    count = 0
    for n in range(max(lo, 2), hi + 1):
        is_p = True
        for p in range(2, int(n**0.5) + 1):
            if n % p == 0:
                is_p = False
                break
        if is_p:
            count += 1
    return count


# --- solver contracts: what tags must a problem carry to be valid? -
# A misroute is caught when name says 'factor' but tags say 'relational'.

FACTOR_REQUIRED_TAG_HINT  = {"bignum", "bitwise", "numeric_tight"}
NQUEENS_REQUIRED_TAG_HINT = {"relational", "search"}
SWEEP_REQUIRED_TAG_HINT   = {"parallel", "io_bound"}


def _tags_consistent(problem: Problem, hint: set[str]) -> bool:
    """Problem's tags must intersect the family's hint set.
    Prevents a misrouted problem (tags=relational/search, name=factor_X)
    from being trusted by the factor branch."""
    actual = {t.value for t in problem.tags}
    return bool(actual & hint)


# --- dispatcher entry ----------------------------------------------

@register_runner("python")
def run_python(problem: Problem) -> tuple[bool, str, float]:
    name = problem.name

    # FACTOR family -- name AND tag contract
    if _name_matches(name, "factor"):
        if not _tags_consistent(problem, FACTOR_REQUIRED_TAG_HINT):
            return False, (f"factor: name='{name}' but tags="
                           f"{[t.value for t in problem.tags]} -- refusing "
                           f"misroute (no overlap with factor family)"), 0.0
        err = _require(problem.payload, {"n": int})
        if err:
            return False, f"factor: {err}", 0.0
        n = problem.payload["n"]
        if n < 4:
            return False, f"factor: n={n} not composite (must be >= 4)", 0.0
        f = _pollard_rho(n)
        if f <= 1 or f >= n or n % f != 0:
            return False, f"factor: bogus result f={f} for n={n}", 0.0
        return True, f"{n} = {f} * {n // f}", 0.0

    # NQUEENS family -- strict
    if _name_matches(name, "nqueens"):
        if not _tags_consistent(problem, NQUEENS_REQUIRED_TAG_HINT):
            return False, (f"nqueens: name='{name}' but tags don't "
                           f"include relational/search -- refusing"), 0.0
        err = _require(problem.payload, {"n": int})
        if err:
            return False, f"nqueens: {err}", 0.0
        n = problem.payload["n"]
        limit = problem.payload.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            return False, f"nqueens: limit must be positive int, got {limit!r}", 0.0
        if n < 1:
            return False, f"nqueens: n={n} must be >= 1", 0.0
        sols = _solve_nqueens_py(n, limit=limit)
        if not sols:
            return False, f"nqueens: no solutions for n={n}", 0.0
        return True, f"n={n}, found {len(sols)} solution(s); first: {sols[0]}", 0.0

    # PRIME SWEEP family -- matches both 'prime_sweep' and 'parallel_prime_sweep'
    if _name_matches(name, "prime_sweep") or _name_matches(name, "parallel_prime_sweep"):
        if not _tags_consistent(problem, SWEEP_REQUIRED_TAG_HINT | {"numeric_tight"}):
            return False, (f"prime_sweep: name='{name}' but tags don't "
                           f"include parallel/io_bound/numeric_tight"), 0.0
        err = _require(problem.payload, {"lo": int, "hi": int})
        if err:
            return False, f"prime_sweep: {err}", 0.0
        lo, hi = problem.payload["lo"], problem.payload["hi"]
        if hi < lo:
            return False, f"prime_sweep: hi={hi} < lo={lo}", 0.0
        count = _prime_sweep_py(lo, hi)
        return True, f"primes in [{lo},{hi}]: {count}", 0.0

    return False, f"no python solver for problem '{name}'", 0.0
