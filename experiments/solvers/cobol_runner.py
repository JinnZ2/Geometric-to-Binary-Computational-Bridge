"""solvers/cobol_runner.py — Pollard rho in COBOL via GnuCOBOL (cobc).

COBOL's fit: fixed-width packed-decimal numerics, register arithmetic,
batch-oriented. Different memory profile than C — interesting for the
v2 energy landscape to discover.

Graceful skip if cobc not installed.
"""
from __future__ import annotations
import subprocess, tempfile, os, sys, shutil, atexit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner

_BUILD_DIR = tempfile.mkdtemp(prefix="polyglot_cob_")
_EXE_PATH  = os.path.join(_BUILD_DIR, "p")
_BUILT     = False


def _cleanup():
    shutil.rmtree(_BUILD_DIR, ignore_errors=True)
atexit.register(_cleanup)


# COBOL Pollard rho.
# COMP-5 = native binary int, fastest numeric type in GnuCOBOL.
# Uses iterative rho with cycle detection (Brent's variant simplified).
COBOL_POLLARD = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. POLLARD.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  N           PIC 9(18) COMP-5.
       01  X           PIC 9(18) COMP-5 VALUE 2.
       01  Y           PIC 9(18) COMP-5 VALUE 2.
       01  C           PIC 9(18) COMP-5 VALUE 1.
       01  D           PIC 9(18) COMP-5 VALUE 1.
       01  DIFF        PIC 9(18) COMP-5.
       01  A           PIC 9(18) COMP-5.
       01  B           PIC 9(18) COMP-5.
       01  T           PIC 9(18) COMP-5.
       01  INPUT-ARG   PIC X(32).
       LINKAGE SECTION.
       PROCEDURE DIVISION.
           ACCEPT INPUT-ARG FROM ARGUMENT-VALUE.
           COMPUTE N = FUNCTION NUMVAL(INPUT-ARG).
           IF FUNCTION MOD(N, 2) = 0
               DISPLAY "2 " (N / 2)
               STOP RUN
           END-IF.
           MOVE 2 TO X.
           MOVE 2 TO Y.
           MOVE 1 TO C.
           MOVE 1 TO D.
           PERFORM UNTIL D NOT = 1 OR D = N
               COMPUTE X = FUNCTION MOD((X * X + C), N)
               COMPUTE Y = FUNCTION MOD((Y * Y + C), N)
               COMPUTE Y = FUNCTION MOD((Y * Y + C), N)
               IF X > Y
                   COMPUTE DIFF = X - Y
               ELSE
                   COMPUTE DIFF = Y - X
               END-IF
               MOVE DIFF TO A
               MOVE N TO B
               PERFORM UNTIL B = 0
                   MOVE B TO T
                   COMPUTE B = FUNCTION MOD(A, B)
                   MOVE T TO A
               END-PERFORM
               MOVE A TO D
           END-PERFORM.
           IF D = N
               DISPLAY "0 0"
           ELSE
               DISPLAY D " " (N / D)
           END-IF.
           STOP RUN.
"""


FACTOR_TAG_HINT = {"bignum", "bitwise", "numeric_tight"}


def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")


def _tags_consistent(problem: Problem) -> bool:
    return bool({t.value for t in problem.tags} & FACTOR_TAG_HINT)


def _ensure_built() -> tuple[bool, str]:
    global _BUILT
    if _BUILT:
        return True, ""
    if not shutil.which("cobc"):
        return False, "cobc (GnuCOBOL) not available"
    src = os.path.join(_BUILD_DIR, "p.cob")
    with open(src, "w") as f:
        f.write(COBOL_POLLARD)
    r = subprocess.run(["cobc", "-x", "-O2", "-o", _EXE_PATH, src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, f"cobc compile failed: {r.stderr}"
    _BUILT = True
    return True, ""


@register_runner("cobol")
def run_cobol(problem: Problem) -> tuple[bool, str, float]:
    if not _name_matches(problem.name, "factor"):
        return False, f"no cobol solver for '{problem.name}'", 0.0
    if not _tags_consistent(problem):
        return False, (f"factor: name='{problem.name}' but tags="
                       f"{[t.value for t in problem.tags]} — refusing misroute"), 0.0
    if "n" not in problem.payload:
        return False, "factor: missing required payload key 'n'", 0.0
    n = problem.payload["n"]
    if not isinstance(n, int):
        return False, f"factor: payload['n'] must be int, got {type(n).__name__}", 0.0
    if n < 4:
        return False, f"factor: n={n} not composite (must be >= 4)", 0.0
    if n.bit_length() > 60:
        return False, f"COBOL runner limited to ~60-bit n (got {n.bit_length()})", 0.0

    ok, err = _ensure_built()
    if not ok:
        return False, err, 0.0
    r = subprocess.run([_EXE_PATH, str(n)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"run failed: {r.stderr}", 0.0
    try:
        a_s, b_s = r.stdout.strip().split()
        a, b = int(a_s), int(b_s)
    except Exception as e:
        return False, f"COBOL output parse failed: {e!r}; stdout={r.stdout!r}", 0.0
    if a <= 1 or a >= n or a * b != n:
        return False, f"factor: bogus COBOL result f={a} for n={n}", 0.0
    return True, f"{n} = {a} * {b}", 0.0
