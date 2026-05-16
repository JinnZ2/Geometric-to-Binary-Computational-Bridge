"""solvers/julia_runner.py -- prime sweep via Julia.

Julia's fit: JIT'd vectorized numeric loops, SIMD when available,
fast inner-loop performance with high-level syntax. Compares
against C (compiled, low-level) and Python (interpreted, high-level).

Graceful skip if julia not installed.
"""
from __future__ import annotations
import subprocess, tempfile, os, sys, shutil, atexit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner

_BUILD_DIR = tempfile.mkdtemp(prefix="polyglot_jl_")
_SRC_PATH  = os.path.join(_BUILD_DIR, "sweep.jl")
_WRITTEN   = False

def _cleanup():
    shutil.rmtree(_BUILD_DIR, ignore_errors=True)
atexit.register(_cleanup)

JULIA_SWEEP = """
function is_prime(n::Int64)::Bool
    n < 2 && return false
    n == 2 && return true
    n % 2 == 0 && return false
    i = 3
    while i * i <= n
        n % i == 0 && return false
        i += 2
    end
    return true
end

function main()
    lo = parse(Int64, ARGS[1])
    hi = parse(Int64, ARGS[2])
    c = 0
    for n in lo:hi
        is_prime(n) && (c += 1)
    end
    println(c)
end

main()
"""

SWEEP_TAG_HINT = {"parallel", "io_bound", "numeric_tight"}

def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")

def _tags_consistent(problem: Problem) -> bool:
    return bool({t.value for t in problem.tags} & SWEEP_TAG_HINT)

def _ensure_written() -> tuple[bool, str]:
    global _WRITTEN
    if _WRITTEN:
        return True, ""
    if not shutil.which("julia"):
        return False, "julia not available"
    with open(_SRC_PATH, "w") as f:
        f.write(JULIA_SWEEP)
    _WRITTEN = True
    return True, ""

@register_runner("julia")
def run_julia(problem: Problem) -> tuple[bool, str, float]:
    if not (_name_matches(problem.name, "prime_sweep")
            or _name_matches(problem.name, "parallel_prime_sweep")):
        return False, f"no julia solver for '{problem.name}'", 0.0
    if not _tags_consistent(problem):
        return False, "prime_sweep: tags don't include parallel/io/numeric", 0.0
    for k in ("lo", "hi"):
        if k not in problem.payload:
            return False, f"prime_sweep: missing payload key '{k}'", 0.0
        if not isinstance(problem.payload[k], int):
            return False, f"prime_sweep: '{k}' must be int", 0.0
    lo, hi = problem.payload["lo"], problem.payload["hi"]
    if hi < lo:
        return False, f"prime_sweep: hi={hi} < lo={lo}", 0.0

    ok, err = _ensure_written()
    if not ok:
        return False, err, 0.0
    r = subprocess.run(["julia", _SRC_PATH, str(lo), str(hi)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return False, f"julia run failed: {r.stderr}", 0.0
    try:
        count = int(r.stdout.strip())
    except ValueError:
        return False, f"julia output parse failed: {r.stdout!r}", 0.0
    return True, f"primes in [{lo},{hi}]: {count}", 0.0
