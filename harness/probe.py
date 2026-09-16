#!/usr/bin/env python3
"""
harness/probe.py -- what THIS machine can run, before any run. stdlib only.

    python harness/probe.py

For every implementations/<name>/MANIFEST.json: are its dependencies
importable by the interpreter that would run it, is a compiler present if
build_required, has the build been done. Prints one row per impl and
returns the same as data for run.py. Exit code is 0 either way: this is a
report, and a machine that can run nothing is a valid reading.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import contract  # noqa: E402

COMPILERS = ("cc", "gcc", "clang")


def _importable(module: str, python: str = sys.executable) -> tuple[bool, str]:
    top = module.split("==")[0].split(">=")[0].strip()
    try:
        r = subprocess.run([python, "-c", f"import {top}"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    if r.returncode == 0:
        return True, ""
    return False, (r.stderr.strip().splitlines() or ["import failed"])[-1][:100]


def compiler() -> str | None:
    for c in COMPILERS:
        if shutil.which(c):
            return c
    return None


def probe_one(m: dict, python: str = sys.executable) -> dict:
    """{'runnable': bool, 'reason': str, 'checks': [...]} for one manifest."""
    checks, reasons = [], []
    for dep in m["dependencies"]:
        ok, why = _importable(dep, python)
        checks.append({"dependency": dep, "ok": ok, "detail": why})
        if not ok:
            reasons.append(f"missing dependency {dep}")
    if m["build_required"]:
        cc = compiler()
        checks.append({"compiler": cc, "ok": cc is not None})
        if cc is None:
            reasons.append("no compiler on PATH (" + "/".join(COMPILERS) + ")")
    head = m["entry"][0]
    if head != "{python}" and not shutil.which(head) and not os.path.exists(os.path.join(m["_dir"], head)):
        reasons.append(f"entry {head!r} not found")
    for tok in m["entry"][1:]:
        cand = os.path.join(m["_dir"], tok)
        if (tok.endswith(".py") or "/" in tok) and not os.path.exists(cand) and not os.path.exists(tok):
            reasons.append(f"entry file {tok!r} not found" + (" (build it)" if m["build_required"] else ""))
    return {"runnable": not reasons, "reason": "; ".join(reasons), "checks": checks}


def machine() -> dict:
    return {"platform": platform.platform(), "python": platform.python_version(),
            "cpus": os.cpu_count(), "compiler": compiler(), "machine": platform.machine()}


def probe_all(root: str = ROOT, python: str = sys.executable) -> dict:
    out = {"machine": machine(), "implementations": {}}
    for m in contract.discover(root):
        out["implementations"][m["name"]] = probe_one(m, python)
    return out


def main() -> int:
    rep = probe_all()
    mi = rep["machine"]
    print(f"machine: {mi['platform']}  python {mi['python']}  cpus {mi['cpus']}  compiler {mi['compiler'] or 'none'}")
    print(f"{'implementation':<16} {'runnable':<9} reason")
    for name, r in rep["implementations"].items():
        print(f"{name:<16} {'yes' if r['runnable'] else 'NO':<9} {r['reason']}")
    if not rep["implementations"]:
        print("(no implementations found)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
