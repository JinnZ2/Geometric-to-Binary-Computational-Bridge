#!/usr/bin/env python3
"""
playground.py  --  CC0, stdlib only, phone-buildable, no deps.

An open bench for the problems this repo has not solved. Anyone may submit a
candidate -- human or model, named or not. The verdict is mechanical.

=====================================================================
WHY THE HARNESS IS SHAPED THIS WAY
=====================================================================
Every fatal finding in this archive was of one of two kinds:

  1. An assertion that no input could make fail. The vacuum bound whose
     criterion was true by construction. The AISS suite where 26 of 46
     assertions were assertIsInstance. topological_pin's run(). These
     all passed, forever, and the passing meant nothing.

  2. A result that survived replacing its structure with noise. The
     seventeen-lens isomorphism. The flat merit weights. The
     NOISE_AS_SIGNAL branch at 22% false alarm.

So a candidate here must do two things that ordinary code review does not
ask for, and both are checked mechanically:

  broken()  must return a deliberately wrong version of the solution, and
            the candidate's own checks MUST reject it. A candidate whose
            checks pass its own broken case is REJECTED_UNFALSIFIABLE. This
            is the repo_guard checklist question -- "does this assertion
            have any input that would make it FAIL?" -- asked of the
            submitter instead of a reviewer.

  null()    is required whenever the claim is statistical. It returns the
            solution with its structure replaced by noise. If the checks
            still pass, the candidate is REJECTED_NULL_ARTIFACT.

A candidate that cannot fail is not a solution. Neither is one that noise
also produces.

=====================================================================
THE CONTRACT
=====================================================================
A candidate is one Python module in playground/candidates/ exposing:

    PROBLEM     str   an id from OPEN_PROBLEMS.json
    CLAIM       str   one falsifiable sentence
    KIND        str   CODE | DERIVATION | DEFINITION | BENCH
    AUTHOR      str   whatever you want on it. "anon" is fine.
    NEEDS_NULL  bool  is the claim statistical
    MATERIAL    str   "silicon" if a material mechanism is claimed, else None

    solve()          -> the artifact. Any object your checks understand.
    checks(artifact) -> [(name, ok, detail), ...]   ok is a bool
    broken()         -> an artifact your checks MUST reject
    null()           -> required if NEEDS_NULL; structure replaced by noise

Verdicts, in the order they are decided:

    REJECTED_CONTRACT       required attribute missing or wrong type
    FAILED                  a check on solve() returned False
    REJECTED_UNFALSIFIABLE  every check passed broken()
    REJECTED_NULL_ARTIFACT  every check passed null()
    REJECTED_VETO           the claimed mechanism is forbidden in the material
    SURVIVES                none of the above

SURVIVES is not "true". It means the candidate cleared the gates that this
archive's own failures were caught by. Graduating one into the repo proper
is a separate, human decision.

=====================================================================
USE
=====================================================================
    python playground/playground.py problems          # what is open
    python playground/playground.py show FCL-12b      # one problem, in full
    python playground/playground.py run NAME          # one candidate
    python playground/playground.py run-all           # every candidate
    python playground/playground.py contract          # the template

Appends every verdict to playground/VERDICTS.jsonl.
"""
import datetime
import importlib
import json
import os
import pkgutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

REGISTRY = os.path.join(HERE, "OPEN_PROBLEMS.json")
VERDICTS = os.path.join(HERE, "VERDICTS.jsonl")
CANDIDATE_DIR = os.path.join(HERE, "candidates")

REQUIRED = {"PROBLEM": str, "CLAIM": str, "KIND": str, "AUTHOR": str,
            "NEEDS_NULL": bool}
KINDS = ("CODE", "DERIVATION", "DEFINITION", "BENCH")


# ---------------------------------------------------------------------
def problems():
    with open(REGISTRY, encoding="utf-8") as fh:
        return json.load(fh)


def problem(pid):
    for p in problems()["problems"]:
        if p["id"] == pid:
            return p
    raise KeyError("no such problem: %r. known: %s"
                   % (pid, ", ".join(p["id"] for p in problems()["problems"])))


def candidates():
    """Module names under playground/candidates/, excluding dunders."""
    if not os.path.isdir(CANDIDATE_DIR):
        return []
    return sorted(m.name for m in pkgutil.iter_modules([CANDIDATE_DIR])
                  if not m.name.startswith("_"))


def load(name):
    return importlib.import_module("playground.candidates.%s" % name)


# ---------------------------------------------------------------------
def _contract_errors(mod):
    errs = []
    for attr, typ in REQUIRED.items():
        if not hasattr(mod, attr):
            errs.append("missing %s" % attr)
        elif not isinstance(getattr(mod, attr), typ):
            errs.append("%s must be %s, got %s"
                        % (attr, typ.__name__, type(getattr(mod, attr)).__name__))
    for fn in ("solve", "checks", "broken"):
        if not callable(getattr(mod, fn, None)):
            errs.append("missing callable %s()" % fn)
    if getattr(mod, "NEEDS_NULL", False) and not callable(getattr(mod, "null",
                                                                  None)):
        errs.append("NEEDS_NULL is True but null() is missing")
    if isinstance(getattr(mod, "KIND", None), str) and mod.KIND not in KINDS:
        errs.append("KIND must be one of %s" % (KINDS,))
    if isinstance(getattr(mod, "PROBLEM", None), str):
        try:
            problem(mod.PROBLEM)
        except KeyError as exc:
            errs.append(str(exc))
    if isinstance(getattr(mod, "CLAIM", None), str) and not mod.CLAIM.strip():
        errs.append("CLAIM is empty")
    return errs


def _run_checks(mod, artifact):
    out = []
    for row in mod.checks(artifact):
        if not (isinstance(row, (tuple, list)) and len(row) == 3):
            raise ValueError("checks() must yield (name, ok, detail) triples, "
                             "got %r" % (row,))
        name, ok, detail = row
        out.append({"check": str(name), "ok": bool(ok), "detail": str(detail)})
    if not out:
        raise ValueError("checks() returned nothing; a candidate with no "
                         "checks cannot be evaluated")
    return out


def evaluate(name):
    """Run one candidate module by name through every gate."""
    return evaluate_module(load(name), name)


def evaluate_module(mod, name=None):
    """Run one candidate through every gate. Returns a verdict dict.

    Takes a module object so a candidate can be evaluated without being a
    file on disk -- which is how the bench's own tests feed it deliberately
    broken candidates.
    """
    name = name or getattr(mod, "__name__", "<anonymous>").split(".")[-1]
    res = {"candidate": name, "ts": datetime.datetime.now()
           .isoformat(timespec="seconds"),
           "problem": getattr(mod, "PROBLEM", None),
           "claim": getattr(mod, "CLAIM", None),
           "author": getattr(mod, "AUTHOR", None),
           "kind": getattr(mod, "KIND", None)}

    errs = _contract_errors(mod)
    if errs:
        res.update(verdict="REJECTED_CONTRACT", reason="; ".join(errs))
        return res

    res["checks"] = _run_checks(mod, mod.solve())
    failed = [c["check"] for c in res["checks"] if not c["ok"]]
    if failed:
        res.update(verdict="FAILED",
                   reason="checks did not pass on solve(): %s"
                          % ", ".join(failed))
        return res

    broke = _run_checks(mod, mod.broken())
    res["broken_caught"] = [c["check"] for c in broke if not c["ok"]]
    if not res["broken_caught"]:
        res.update(verdict="REJECTED_UNFALSIFIABLE",
                   reason="every check passed broken(). An assertion no input "
                          "can make fail is not evidence -- it is the defect "
                          "this bench exists to catch.")
        return res

    if mod.NEEDS_NULL:
        nul = _run_checks(mod, mod.null())
        res["null_caught"] = [c["check"] for c in nul if not c["ok"]]
        if not res["null_caught"]:
            res.update(verdict="REJECTED_NULL_ARTIFACT",
                       reason="every check passed null(). Noise with the same "
                              "shape reproduces the result, so the result is "
                              "the shape.")
            return res

    material = getattr(mod, "MATERIAL", None)
    if material:
        from repo_guard import veto
        hits = veto(material, "%s\n%s" % (mod.CLAIM, mod.__doc__ or ""))
        if hits:
            res.update(verdict="REJECTED_VETO",
                       reason="; ".join("%s: %s" % (h[0], h[1]) for h in hits))
            return res

    res.update(verdict="SURVIVES",
               reason="passed on solve(), rejected broken()%s%s"
                      % (", rejected null()" if mod.NEEDS_NULL else "",
                         ", cleared the %s veto" % material if material
                         else ""))
    return res


def record(res, path=VERDICTS):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(res, ensure_ascii=False) + "\n")
    return res


# ---------------------------------------------------------------------
CONTRACT_TEMPLATE = '''"""One paragraph: what you are claiming and how you know.

Keep it flat. The checks are the argument; this is the handle.
"""
PROBLEM = "FCL-12b"          # an id from OPEN_PROBLEMS.json
CLAIM = "one falsifiable sentence"
KIND = "CODE"                # CODE | DERIVATION | DEFINITION | BENCH
AUTHOR = "anon"
NEEDS_NULL = True            # is the claim statistical
MATERIAL = None              # "silicon" if a material mechanism is claimed


def solve():
    """Return the artifact. Any object your checks understand."""
    return {}


def checks(a):
    """Return [(name, ok, detail), ...]. These ARE the argument."""
    return [("something measurable", True, "the number that shows it")]


def broken():
    """A deliberately wrong artifact. Your checks MUST reject it.

    If they do not, the bench returns REJECTED_UNFALSIFIABLE, which is the
    correct answer: a check that cannot fail is not a check.
    """
    return {}


def null():
    """Required when NEEDS_NULL. Structure replaced by noise, same shape."""
    return {}
'''


def _fmt_problem(p, full=False):
    head = "  %-10s %-11s %-6s %s" % (p["id"], p["state"], p["kind"],
                                      p["title"])
    if not full:
        return head
    out = [head, ""]
    out.append("  %s" % p["statement"])
    if p.get("why_open"):
        out += ["", "  WHY OPEN", "    %s" % p["why_open"]]
    if p.get("would_count"):
        out += ["", "  WHAT WOULD COUNT"]
        out += ["    - %s" % w for w in p["would_count"]]
    if p.get("prior_attempts"):
        out += ["", "  TRIED AND FAILED"]
        out += ["    - %s: %s" % (a["what"], a["why_it_failed"])
                for a in p["prior_attempts"]]
    if p.get("leads"):
        out += ["", "  LEADS (not endorsements -- starting points)"]
        out += ["    - %s" % ln for ln in p["leads"]]
    if p.get("cost_usd"):
        out += ["", "  COST  $%s" % p["cost_usd"]]
    acc = p.get("acceptance", {})
    out += ["", "  ACCEPTANCE  needs_null=%s  material=%s"
            % (acc.get("needs_null"), acc.get("material"))]
    return "\n".join(out)


def _print_verdict(res):
    print("  %-24s %-24s %s" % (res["candidate"], res.get("problem"),
                                res["verdict"]))
    print("      %s" % res.get("reason", ""))
    for c in res.get("checks", []):
        print("      [%s] %-42s %s" % ("ok" if c["ok"] else "XX", c["check"],
                                       c["detail"]))
    if res.get("broken_caught"):
        print("      broken() rejected by: %s" % ", ".join(res["broken_caught"]))
    if res.get("null_caught"):
        print("      null()   rejected by: %s" % ", ".join(res["null_caught"]))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "problems"
    if cmd == "problems":
        reg = problems()
        print("OPEN PROBLEMS  (%d)" % len(reg["problems"]))
        print("  kinds: " + "; ".join("%s = %s" % kv
                                      for kv in reg["kinds"].items()))
        print()
        for p in reg["problems"]:
            print(_fmt_problem(p))
        print()
        print("  python playground/playground.py show ID")
    elif cmd == "show" and len(argv) > 2:
        print(_fmt_problem(problem(argv[2]), full=True))
    elif cmd == "contract":
        print(CONTRACT_TEMPLATE)
    elif cmd == "run" and len(argv) > 2:
        _print_verdict(record(evaluate(argv[2])))
    elif cmd == "run-all":
        names = candidates()
        if not names:
            print("no candidates in %s" % CANDIDATE_DIR)
            return 0
        bad = 0
        for n in names:
            res = record(evaluate(n))
            _print_verdict(res)
            print()
            bad += res["verdict"] not in ("SURVIVES",)
        print("%d candidates, %d survived, %d did not"
              % (len(names), len(names) - bad, bad))
    else:
        print("usage: playground.py [problems | show ID | run NAME | "
              "run-all | contract]")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
