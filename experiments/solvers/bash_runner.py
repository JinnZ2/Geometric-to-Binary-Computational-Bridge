"""solvers/bash_runner.py — parallel sweep via xargs -P.

Shape: PARALLEL + IO_BOUND. The win isn't single-thread speed,
it's running N independent jobs concurrently with near-zero overhead.

Demo problem: parallel primality check across a range.
"""
from __future__ import annotations
import subprocess, os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner


@register_runner("bash")
def run_bash(problem: Problem) -> tuple[bool, str, float]:
    if not shutil.which("bash"):
        return False, "bash not available", 0.0

    if problem.name.startswith("parallel_prime_sweep"):
        lo = problem.payload["lo"]
        hi = problem.payload["hi"]
        workers = problem.payload.get("workers", 4)

        # chunk work: each worker handles a contiguous range, not one number.
        # spawn-cost is amortized over the whole chunk.
        chunk_size = max(1, (hi - lo + 1) // workers)
        ranges = []
        cur = lo
        while cur <= hi:
            end = min(cur + chunk_size - 1, hi)
            ranges.append(f"{cur}-{end}")
            cur = end + 1

        script = f"""
printf '%s\\n' {' '.join(ranges)} | xargs -P {workers} -I{{}} bash -c '
range="{{}}"
lo=${{range%-*}}
hi=${{range#*-}}
python3 -c "
import sys
lo,hi = int(sys.argv[1]), int(sys.argv[2])
c = 0
for n in range(max(lo,2), hi+1):
    is_p = True
    for p in range(2, int(n**0.5)+1):
        if n % p == 0:
            is_p = False; break
    if is_p: c += 1
print(c)
" $lo $hi
' | awk '{{s+=$1}} END {{print s}}'
"""
        r = subprocess.run(["bash", "-c", script],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return False, f"bash sweep failed: {r.stderr}", 0.0
        count = r.stdout.strip()
        return True, f"primes in [{lo},{hi}] via {workers} chunked workers: {count}", 0.0

    return False, f"no bash solver for {problem.name}", 0.0
