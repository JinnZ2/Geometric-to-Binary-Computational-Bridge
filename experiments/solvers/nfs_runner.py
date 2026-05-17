"""solvers/nfs_runner.py -- geometric NFS factorization CELL.

╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ This file is a specialized CELL in a distributed ecology.      ║
║ It does ONE thing: factors integers via the project's          ║
║ geometric_nfs pipeline (octahedral lattice + RIM sieve), not   ║
║ via toy Pollard rho.                                           ║
║                                                                ║
║ Registers under lang='nfs' to NOT collide with python_runner   ║
║ or c_runner. Invoke via Problem(..., hint_lang='nfs'). Not in  ║
║ the canonical 13-language roster -- it's an opt-in algorithm   ║
║ variant, not a new language.                                   ║
║                                                                ║
║ The point: a real NFS run takes longer on small N (huge        ║
║ overhead) but scales better on large N. Racing it against the  ║
║ toy Pollard-rho cells gives the landscape a meaningful         ║
║ work-scale-dependent signal at the ALGORITHM level instead of  ║
║ just the language level.                                       ║
╚════════════════════════════════════════════════════════════════╝

OPT-IN: import this module explicitly to register the runner; nothing
else in the stack depends on it. After import:

    from runner_api import RUNNERS, Problem
    from dispatcher import Shape, plan, execute
    import solvers.nfs_runner   # noqa: F401   (registers 'nfs')

    p = Problem("factor_big", "", [Shape.BIGNUM, Shape.NUMERIC_TIGHT],
                {"n": 982451653 * 982451707}, hint_lang="nfs")
    execute(plan(p))
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner_api import Problem, register_runner


def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")


FACTOR_TAG_HINT = {"bignum", "bitwise", "numeric_tight"}


def _tags_consistent(problem: Problem) -> bool:
    actual = {t.value for t in problem.tags}
    return bool(actual & FACTOR_TAG_HINT)


@register_runner("nfs")
def run_nfs(problem: Problem) -> tuple[bool, str, float]:
    if not _name_matches(problem.name, "factor"):
        return False, f"no nfs solver for '{problem.name}'", 0.0
    if not _tags_consistent(problem):
        return False, (f"factor: name='{problem.name}' but tags="
                       f"{[t.value for t in problem.tags]} -- refusing "
                       f"misroute (no overlap with factor family)"), 0.0
    if "n" not in problem.payload:
        return False, "factor: missing required payload key 'n'", 0.0
    n = problem.payload["n"]
    if not isinstance(n, int):
        return False, f"factor: payload['n'] must be int, got {type(n).__name__}", 0.0
    if n < 4:
        return False, f"factor: n={n} not composite (must be >= 4)", 0.0

    # Lazy import: geometric_nfs is heavy. Only pay the cost when actually invoked.
    try:
        from experiments.geometric_nfs import geometric_nfs
    except ImportError:
        # fallback: try direct neighbour import (when experiments/ is on path)
        try:
            from geometric_nfs import geometric_nfs
        except ImportError as e:
            return False, f"nfs: could not import geometric_nfs: {e}", 0.0

    B_bound = problem.payload.get("B_bound")   # optional override
    try:
        result = geometric_nfs(n, B_bound=B_bound) if B_bound is not None \
                 else geometric_nfs(n)
    except Exception as e:
        return False, f"nfs: geometric_nfs raised {type(e).__name__}: {e}", 0.0

    if not getattr(result, "found", False):
        return False, (f"nfs: did not find a factor of n={n} "
                       f"(method={getattr(result, 'method', '?')})"), 0.0

    a = result.factor
    b = result.other_factor
    if a is None or b is None or a * b != n:
        return False, f"nfs: bogus result a={a}, b={b} for n={n}", 0.0

    method = getattr(result, "method", "geometric_nfs")
    return True, f"{n} = {a} * {b} (method={method})", 0.0
