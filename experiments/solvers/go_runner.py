"""solvers/go_runner.py -- parallel prime sweep via goroutines.

Go's fit: goroutines + channels, lightweight concurrency, no GIL.
Different parallelism profile than bash (subprocess fork) or
Python (thread-bound). Native scheduler should crush small-job
parallel sweeps.

Graceful skip if go not installed.
"""
from __future__ import annotations
import subprocess, tempfile, os, sys, shutil, atexit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner

_BUILD_DIR = tempfile.mkdtemp(prefix="polyglot_go_")
_EXE_PATH  = os.path.join(_BUILD_DIR, "p")
_BUILT     = False

def _cleanup():
    shutil.rmtree(_BUILD_DIR, ignore_errors=True)
atexit.register(_cleanup)

GO_SWEEP = """
package main

import (
\t"fmt"
\t"os"
\t"runtime"
\t"strconv"
\t"sync"
)

func isPrime(n int64) bool {
\tif n < 2 {
\t\treturn false
\t}
\tif n == 2 {
\t\treturn true
\t}
\tif n%2 == 0 {
\t\treturn false
\t}
\tfor i := int64(3); i*i <= n; i += 2 {
\t\tif n%i == 0 {
\t\t\treturn false
\t\t}
\t}
\treturn true
}

func main() {
\tlo, _ := strconv.ParseInt(os.Args[1], 10, 64)
\thi, _ := strconv.ParseInt(os.Args[2], 10, 64)
\tworkers := runtime.NumCPU()
\tif len(os.Args) > 3 {
\t\tif w, err := strconv.Atoi(os.Args[3]); err == nil {
\t\t\tworkers = w
\t\t}
\t}
\tchunk := (hi - lo + 1) / int64(workers)
\tif chunk < 1 {
\t\tchunk = 1
\t}
\tvar wg sync.WaitGroup
\tvar mu sync.Mutex
\ttotal := int64(0)
\tfor w := 0; w < workers; w++ {
\t\tstart := lo + int64(w)*chunk
\t\tend := start + chunk - 1
\t\tif w == workers-1 {
\t\t\tend = hi
\t\t}
\t\twg.Add(1)
\t\tgo func(s, e int64) {
\t\t\tdefer wg.Done()
\t\t\tc := int64(0)
\t\t\tfor n := s; n <= e; n++ {
\t\t\t\tif isPrime(n) {
\t\t\t\t\tc++
\t\t\t\t}
\t\t\t}
\t\t\tmu.Lock()
\t\t\ttotal += c
\t\t\tmu.Unlock()
\t\t}(start, end)
\t}
\twg.Wait()
\tfmt.Println(total)
}
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
    if not shutil.which("go"):
        return False, "go not available"
    src = os.path.join(_BUILD_DIR, "p.go")
    with open(src, "w") as f:
        f.write(GO_SWEEP)
    r = subprocess.run(["go", "build", "-o", _EXE_PATH, src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"go build failed: {r.stderr}"
    _BUILT = True
    return True, ""

@register_runner("go")
def run_go(problem: Problem) -> tuple[bool, str, float]:
    if not (_name_matches(problem.name, "prime_sweep")
            or _name_matches(problem.name, "parallel_prime_sweep")):
        return False, f"no go solver for '{problem.name}'", 0.0
    if not _tags_consistent(problem):
        return False, "prime_sweep: tags don't include parallel/io/numeric", 0.0
    for k in ("lo", "hi"):
        if k not in problem.payload:
            return False, f"prime_sweep: missing payload key '{k}'", 0.0
        if not isinstance(problem.payload[k], int):
            return False, f"prime_sweep: '{k}' must be int", 0.0
    lo, hi = problem.payload["lo"], problem.payload["hi"]
    workers = problem.payload.get("workers", 4)
    if hi < lo:
        return False, f"prime_sweep: hi={hi} < lo={lo}", 0.0

    ok, err = _ensure_built()
    if not ok:
        return False, err, 0.0
    r = subprocess.run([_EXE_PATH, str(lo), str(hi), str(workers)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return False, f"go run failed: {r.stderr}", 0.0
    try:
        count = int(r.stdout.strip())
    except ValueError:
        return False, f"go output parse failed: {r.stdout!r}", 0.0
    return True, f"primes in [{lo},{hi}] via {workers} goroutines: {count}", 0.0
