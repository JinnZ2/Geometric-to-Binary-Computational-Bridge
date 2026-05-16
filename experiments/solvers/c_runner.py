"""solvers/c_runner.py — compile once at import, run many"""
from __future__ import annotations
import subprocess, tempfile, os, sys, shutil, atexit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner

_BUILD_DIR = tempfile.mkdtemp(prefix="polyglot_c_")
_EXE_PATH  = os.path.join(_BUILD_DIR, "p")
_BUILT     = False


def _cleanup():
    shutil.rmtree(_BUILD_DIR, ignore_errors=True)
atexit.register(_cleanup)


C_POLLARD = r"""
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

typedef unsigned __int128 u128;
typedef unsigned long long u64;

static u64 mulmod(u64 a, u64 b, u64 m) {
    return (u64)((u128)a * b % m);
}
static u64 gcd(u64 a, u64 b) { while (b) { u64 t=a%b; a=b; b=t; } return a; }

static u64 pollard_rho(u64 n) {
    if (n % 2 == 0) return 2;
    while (1) {
        u64 x = (u64)rand() % (n-2) + 2;
        u64 y = x;
        u64 c = (u64)rand() % (n-1) + 1;
        u64 d = 1;
        while (d == 1) {
            x = (mulmod(x,x,n) + c) % n;
            y = (mulmod(y,y,n) + c) % n;
            y = (mulmod(y,y,n) + c) % n;
            u64 diff = x>y ? x-y : y-x;
            d = gcd(diff, n);
        }
        if (d != n) return d;
    }
}

int main(int argc, char **argv) {
    if (argc < 2) return 1;
    u64 n = strtoull(argv[1], NULL, 10);
    srand(42);
    u64 f = pollard_rho(n);
    printf("%llu %llu\n", (unsigned long long)f, (unsigned long long)(n/f));
    return 0;
}
"""


def _ensure_built() -> tuple[bool, str]:
    global _BUILT
    if _BUILT:
        return True, ""
    if not shutil.which("gcc"):
        return False, "gcc not available"
    src = os.path.join(_BUILD_DIR, "p.c")
    with open(src, "w") as f:
        f.write(C_POLLARD)
    r = subprocess.run(["gcc", "-O2", "-o", _EXE_PATH, src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"compile failed: {r.stderr}"
    _BUILT = True
    return True, ""


@register_runner("c")
def run_c(problem: Problem) -> tuple[bool, str, float]:
    if not problem.name.startswith("factor"):
        return False, f"no C solver for {problem.name}", 0.0

    n = problem.payload["n"]
    if n.bit_length() > 63:
        return False, f"C runner limited to 63-bit n (got {n.bit_length()} bits)", 0.0

    ok, err = _ensure_built()
    if not ok:
        return False, err, 0.0

    r = subprocess.run([_EXE_PATH, str(n)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"run failed: {r.stderr}", 0.0
    a, b = r.stdout.strip().split()
    return True, f"{n} = {a} * {b}", 0.0
