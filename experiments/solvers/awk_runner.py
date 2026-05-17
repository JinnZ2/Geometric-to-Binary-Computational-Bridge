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

ROLE: CELL -- prime-sweep specialist (awk stream). Emits wall-time + overhead signals.

solvers/awk_runner.py -- prime sweep via awk.

Awk's fit: stream processing, tight inner loops in C-implemented awk
(gawk/mawk). Surprisingly fast for numeric scans. Different profile
than bash (subprocess spawning) or Python (interpreter).

Graceful skip if awk not installed.
"""
from __future__ import annotations
import subprocess, sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner_api import Problem, register_runner

AWK_SWEEP = r"""
BEGIN {
    lo = ARGV[1] + 0
    hi = ARGV[2] + 0
    c = 0
    for (n = lo; n <= hi; n++) {
        if (n < 2) continue
        if (n == 2) { c++; continue }
        if (n % 2 == 0) continue
        is_p = 1
        for (i = 3; i * i <= n; i += 2) {
            if (n % i == 0) { is_p = 0; break }
        }
        if (is_p) c++
    }
    print c
    exit
}
"""

SWEEP_TAG_HINT = {"parallel", "io_bound", "numeric_tight"}

def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")

def _tags_consistent(problem: Problem) -> bool:
    return bool({t.value for t in problem.tags} & SWEEP_TAG_HINT)

@register_runner("awk")
def run_awk(problem: Problem) -> tuple[bool, str, float]:
    if not (_name_matches(problem.name, "prime_sweep")
            or _name_matches(problem.name, "parallel_prime_sweep")):
        return False, f"no awk solver for '{problem.name}'", 0.0
    if not _tags_consistent(problem):
        return False, "prime_sweep: tag mismatch", 0.0
    if not shutil.which("awk"):
        return False, "awk not available", 0.0
    for k in ("lo", "hi"):
        if k not in problem.payload:
            return False, f"prime_sweep: missing payload key '{k}'", 0.0
        if not isinstance(problem.payload[k], int):
            return False, f"prime_sweep: '{k}' must be int", 0.0
    lo, hi = problem.payload["lo"], problem.payload["hi"]
    if hi < lo:
        return False, f"prime_sweep: hi={hi} < lo={lo}", 0.0

    r = subprocess.run(["awk", AWK_SWEEP, str(lo), str(hi)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"awk run failed: {r.stderr}", 0.0
    try:
        count = int(r.stdout.strip())
    except ValueError:
        return False, f"awk output parse failed: {r.stdout!r}", 0.0
    return True, f"primes in [{lo},{hi}]: {count}", 0.0
