"""
╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ This system is NOT a central controller making decisions.      ║
║ It is a distributed ecology of specialized solvers (cells)     ║
║ organized by a learned topology (landscape) that reads signals ║
║ (waste, latency, overhead) and routes work accordingly.        ║
║                                                                ║
║ • Each runner: one specialized function                        ║
║ • Dispatcher: a router reading cell signals, not a thinker     ║
║ • Landscape: topology learned from observed flows              ║
║ • Waste audit: how cells talk back to the router               ║
║                                                                ║
║ Intelligence emerges from specialization + signal flow +       ║
║ topology learning. Not from central control.                   ║
╚════════════════════════════════════════════════════════════════╝

ROLE: CELL -- prime-sweep specialist (gfortran). Emits wall-time + overhead signals.

solvers/fortran_runner.py -- prime sweep via gfortran.

Fortran's fit: dense numeric loops, native array semantics, decades
of compiler optimization for tight INTEGER arithmetic. Different
register/cache profile than C -- interesting v2 landscape signal.

Graceful skip if gfortran not installed.
"""
from __future__ import annotations
import subprocess, tempfile, os, sys, shutil, atexit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner

_BUILD_DIR = tempfile.mkdtemp(prefix="polyglot_f90_")
_EXE_PATH  = os.path.join(_BUILD_DIR, "p")
_BUILT     = False

def _cleanup():
    shutil.rmtree(_BUILD_DIR, ignore_errors=True)
atexit.register(_cleanup)

FORTRAN_SWEEP = """
program prime_sweep
    implicit none
    integer(kind=8) :: lo, hi, n, i, count
    character(len=32) :: arg
    call get_command_argument(1, arg)
    read(arg, *) lo
    call get_command_argument(2, arg)
    read(arg, *) hi
    count = 0
    do n = max(lo, 2_8), hi
        if (is_prime(n)) count = count + 1
    end do
    print '(I0)', count
contains
    logical function is_prime(n)
        integer(kind=8), intent(in) :: n
        integer(kind=8) :: i
        is_prime = .false.
        if (n < 2) return
        if (n == 2) then; is_prime = .true.; return; end if
        if (mod(n, 2_8) == 0) return
        i = 3
        do while (i * i <= n)
            if (mod(n, i) == 0) return
            i = i + 2
        end do
        is_prime = .true.
    end function is_prime
end program
"""

SWEEP_TAG_HINT = {"parallel", "io_bound", "numeric_tight"}

def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")

def _tags_consistent(problem: Problem) -> bool:
    return bool({t.value for t in problem.tags} & SWEEP_TAG_HINT)

def _ensure_built() -> tuple[bool, str]:
    global _BUILT
    if _BUILT:
        return True, ""
    if not shutil.which("gfortran"):
        return False, "gfortran not available"
    src = os.path.join(_BUILD_DIR, "p.f90")
    with open(src, "w") as f:
        f.write(FORTRAN_SWEEP)
    r = subprocess.run(["gfortran", "-O2", "-o", _EXE_PATH, src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"gfortran compile failed: {r.stderr}"
    _BUILT = True
    return True, ""

@register_runner("fortran")
def run_fortran(problem: Problem) -> tuple[bool, str, float]:
    if not (_name_matches(problem.name, "prime_sweep")
            or _name_matches(problem.name, "parallel_prime_sweep")):
        return False, f"no fortran solver for '{problem.name}'", 0.0
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

    ok, err = _ensure_built()
    if not ok:
        return False, err, 0.0
    r = subprocess.run([_EXE_PATH, str(lo), str(hi)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"fortran run failed: {r.stderr}", 0.0
    try:
        count = int(r.stdout.strip())
    except ValueError:
        return False, f"fortran output parse failed: {r.stdout!r}", 0.0
    return True, f"primes in [{lo},{hi}]: {count}", 0.0
