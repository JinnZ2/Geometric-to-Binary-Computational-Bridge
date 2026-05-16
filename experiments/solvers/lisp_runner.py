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

ROLE: CELL -- n-queens specialist (Common Lisp). Emits wall-time + overhead signals.

solvers/lisp_runner.py -- n-queens via Common Lisp (sbcl or clisp).

Lisp's fit: native recursion, symbolic search, low-overhead backtracking.
The (rel, stt) axis is its native habitat -- interesting comparison
against Python's backtracking.

Graceful skip if no Lisp compiler available.
"""
from __future__ import annotations
import subprocess, tempfile, os, sys, shutil, atexit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dispatcher import Problem, register_runner

_BUILD_DIR   = tempfile.mkdtemp(prefix="polyglot_lisp_")
_SRC_PATH    = os.path.join(_BUILD_DIR, "queens.lisp")
_COMPILED    = None     # path to fasl, or None if interpreted
_WRITTEN     = False
_LISP_BIN    = None
_LISP_FLAVOR = None     # "sbcl" | "clisp"

def _cleanup():
    shutil.rmtree(_BUILD_DIR, ignore_errors=True)
atexit.register(_cleanup)

LISP_QUEENS = """
(defun queens (n &optional (limit 5))
  (let ((solutions '()))
    (labels
        ((safe-p (col placed row)
           (loop for r from 1
                 for pc in placed
                 never (or (= pc col)
                           (= (abs (- pc col)) (abs (- r row))))))
         (place (row placed)
           (when (>= (length solutions) limit)
             (return-from place))
           (if (> row n)
               (push (reverse placed) solutions)
               (loop for c from 1 to n
                     when (safe-p c placed row)
                       do (place (1+ row) (cons c placed))))))
      (place 1 '())
      (nreverse solutions))))

(defun main ()
  (let* ((args #+sbcl (cdr sb-ext:*posix-argv*)
               #+clisp ext:*args*)
         (n (parse-integer (first args)))
         (limit (if (second args) (parse-integer (second args)) 5))
         (sols (queens n limit)))
    (format t "~a~%" (length sols))
    (when sols
      (format t "~{~a~^,~}~%" (first sols)))))

(main)
"""

NQUEENS_TAG_HINT = {"relational", "search"}

def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")

def _tags_consistent(problem: Problem) -> bool:
    return bool({t.value for t in problem.tags} & NQUEENS_TAG_HINT)

def _detect_lisp() -> tuple[bool, str]:
    global _LISP_BIN, _LISP_FLAVOR
    if _LISP_BIN:
        return True, ""
    if shutil.which("sbcl"):
        _LISP_BIN = shutil.which("sbcl")
        _LISP_FLAVOR = "sbcl"
        return True, ""
    if shutil.which("clisp"):
        _LISP_BIN = shutil.which("clisp")
        _LISP_FLAVOR = "clisp"
        return True, ""
    return False, "no Common Lisp implementation (sbcl/clisp) found"

def _ensure_written() -> tuple[bool, str]:
    global _WRITTEN
    if _WRITTEN:
        return True, ""
    ok, err = _detect_lisp()
    if not ok:
        return False, err
    with open(_SRC_PATH, "w") as f:
        f.write(LISP_QUEENS)
    _WRITTEN = True
    return True, ""

@register_runner("lisp")
def run_lisp(problem: Problem) -> tuple[bool, str, float]:
    if not _name_matches(problem.name, "nqueens"):
        return False, f"no lisp solver for '{problem.name}'", 0.0
    if not _tags_consistent(problem):
        return False, "nqueens: tags don't include relational/search", 0.0
    if "n" not in problem.payload:
        return False, "nqueens: missing payload key 'n'", 0.0
    n = problem.payload["n"]
    limit = problem.payload.get("limit", 5)
    if not isinstance(n, int) or n < 1:
        return False, f"nqueens: n must be positive int, got {n!r}", 0.0
    if not isinstance(limit, int) or limit < 1:
        return False, f"nqueens: limit must be positive int, got {limit!r}", 0.0

    ok, err = _ensure_written()
    if not ok:
        return False, err, 0.0

    if _LISP_FLAVOR == "sbcl":
        cmd = [_LISP_BIN, "--script", _SRC_PATH, str(n), str(limit)]
    else:  # clisp
        cmd = [_LISP_BIN, "-q", _SRC_PATH, str(n), str(limit)]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, f"lisp run failed: {r.stderr}", 0.0
    lines = r.stdout.strip().splitlines()
    if not lines:
        return False, "lisp: no output", 0.0
    try:
        count = int(lines[0])
    except ValueError:
        return False, f"lisp: unparseable count: {lines[0]!r}", 0.0
    if count == 0:
        return False, f"nqueens: no solutions for n={n}", 0.0
    first = lines[1] if len(lines) > 1 else ""
    return True, f"n={n}, found {count} solution(s); first: [{first}]", 0.0
