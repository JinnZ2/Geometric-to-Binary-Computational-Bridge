"""solvers/rust_runner.py — rustc compile once at first call, run many.

Pattern matches c_runner: skip cleanly if rustc absent, build on first
real call, reuse the binary for subsequent calls.
"""
from __future__ import annotations
import subprocess, tempfile, os, sys, shutil, atexit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner

_BUILD_DIR = tempfile.mkdtemp(prefix="polyglot_rs_")
_EXE_PATH  = os.path.join(_BUILD_DIR, "p")
_BUILT     = False


def _cleanup():
    shutil.rmtree(_BUILD_DIR, ignore_errors=True)
atexit.register(_cleanup)


RUST_POLLARD = r"""
use std::env;

fn mulmod(a: u64, b: u64, m: u64) -> u64 {
    ((a as u128 * b as u128) % m as u128) as u64
}

fn gcd(mut a: u64, mut b: u64) -> u64 {
    while b != 0 { let t = a % b; a = b; b = t; }
    a
}

fn pollard_rho(n: u64) -> u64 {
    if n % 2 == 0 { return 2; }
    let mut seed: u64 = 0x9E3779B97F4A7C15;
    loop {
        // simple LCG for x, c — deterministic, no external rand crate
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let mut x: u64 = (seed % (n - 2)) + 2;
        let mut y: u64 = x;
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let c: u64 = (seed % (n - 1)) + 1;
        let mut d: u64 = 1;
        while d == 1 {
            x = (mulmod(x, x, n) + c) % n;
            y = (mulmod(y, y, n) + c) % n;
            y = (mulmod(y, y, n) + c) % n;
            let diff = if x > y { x - y } else { y - x };
            d = gcd(diff, n);
        }
        if d != n { return d; }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 { std::process::exit(1); }
    let n: u64 = args[1].parse().unwrap();
    let f = pollard_rho(n);
    println!("{} {}", f, n / f);
}
"""


def _ensure_built() -> tuple[bool, str]:
    global _BUILT
    if _BUILT:
        return True, ""
    if not shutil.which("rustc"):
        return False, "rustc not available"
    src = os.path.join(_BUILD_DIR, "p.rs")
    with open(src, "w") as f:
        f.write(RUST_POLLARD)
    r = subprocess.run(["rustc", "-O", "-o", _EXE_PATH, src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"rust compile failed: {r.stderr}"
    _BUILT = True
    return True, ""


@register_runner("rust")
def run_rust(problem: Problem) -> tuple[bool, str, float]:
    if not problem.name.startswith("factor"):
        return False, f"no rust solver for {problem.name}", 0.0
    n = problem.payload["n"]
    if n.bit_length() > 63:
        return False, f"rust runner limited to 63-bit n (got {n.bit_length()} bits)", 0.0
    ok, err = _ensure_built()
    if not ok:
        return False, err, 0.0
    r = subprocess.run([_EXE_PATH, str(n)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"run failed: {r.stderr}", 0.0
    a, b = r.stdout.strip().split()
    return True, f"{n} = {a} * {b}", 0.0
