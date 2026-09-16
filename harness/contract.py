#!/usr/bin/env python3
"""
harness/contract.py -- spec in, result record out. stdlib only, so the contract runs anywhere.

PURPOSE
    Several implementations of one geometric spec, in different languages,
    selected by CONDITIONS. Not a leaderboard: nothing here ranks, and
    SELECTION.md has no winner row. An implementation declares itself in
    its own MANIFEST.json and nowhere else.

THE CONTRACT
    IN   one spec, one format, versioned (SPEC_VERSION). Built by make_spec()
         from a workload record and a resolution: sources, bounds, resolution,
         the workload's declared conditions, and a seeded set of probe points.
    OUT  one result record per (impl, workload, resolution):
           impl / workload / resolution / wall_time / peak_memory /
           accuracy_vs_reference / status
         status is one of STATUSES, every one first-class, none an error:
           OK
           NOT_RUNNABLE(reason)     missing dependency, no compiler
           TIMEOUT(limit)
           FAILED(error)
           NOT_APPLICABLE(reason)   the impl does not cover this workload
         render_status() never returns a blank, a zero or an omission: a
         reader on a phone sees which rows they could not run and why.

IMPLEMENTATION PROTOCOL  (what an impl's `entry` must do)
    The harness runs the manifest's `entry` as a subprocess with two
    arguments appended: --spec <path to spec.json> --out <path to result.json>.
    The impl computes whatever it computes, then answers the spec's probe
    points and calls finish(), which writes:
        {"wall_time": s, "points": n, "probe_field": {"E": [[...]...], "B": [[...]...]},
         "peak_memory_mb": ru_maxrss of the child}
    wall_time is the impl's own clock around its compute, not the process
    lifetime, so interpreter and import start-up do not count against a
    fast implementation. A nonzero exit is FAILED(stderr tail); exceeding
    the harness limit is TIMEOUT(limit).

ACCURACY
    accuracy_vs_reference is the median relative error of the impl's probe
    answers against reference_field(), a pure-Python evaluation of the spec's
    own source definitions (Coulomb for a charge; the Engine's current
    element: Biot-Savart from the element midpoint with dl = end - start).
    Reported for E and B separately. No implementation is the reference;
    uniform_grid is a peer.

STDLIB CONSTRAINT, scoped
    Repo-wide stdlib-only is replaced by per-folder declaration: each
    implementation's MANIFEST.json `dependencies` says what it needs, and
    harness/ imports nothing outside the standard library.
"""
from __future__ import annotations

import json
import math
import os
import random
import time

SPEC_VERSION = 1
STATUSES = ("OK", "NOT_RUNNABLE", "TIMEOUT", "FAILED", "NOT_APPLICABLE")
SPARSITY = ("dense", "mixed", "isolated")
SCALE_SEPARATION = ("single", "multi")
KNOBS = ("resolution", "tolerance", "none")   # "none": no accuracy knob; the sweep argument is ignored
PROBE_COUNT = 256
PROBE_SEED = 20260916

K_E = 8.9875517873681764e9
MU_OVER_4PI = 1e-7

# MANIFEST.json: field -> (allowed types, allowed values or None). All required.
MANIFEST_SCHEMA = {
    "name": (str, None),
    "language": (str, None),
    "dependencies": (list, None),          # [] means stdlib only
    "build_required": (bool, None),
    "build_command": ((str, type(None)), None),   # null if none
    "runs_on_phone": ((bool, str), (True, False, "unknown")),
    "algorithm": (str, None),              # one line
    "author_claim": (str, None),           # the conditions it expects to suit: a CLAIM, not a result
    "entry": (list, None),                 # argv; "{python}" is replaced by the running interpreter
    "covers": (list, None),                # workload names, or ["*"]
    "knob": (str, KNOBS),                  # what the harness sweeps for it: the accuracy knob it exposes
}


class ContractError(ValueError):
    pass


# ----------------------------------------------------------------- manifests

def load_manifest(path: str) -> dict:
    """Read and validate one MANIFEST.json. Raises ContractError naming the field."""
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)
    for key, (types, allowed) in MANIFEST_SCHEMA.items():
        if key not in m:
            raise ContractError(f"{path}: missing field {key!r}")
        if not isinstance(m[key], types):
            raise ContractError(f"{path}: field {key!r} has type {type(m[key]).__name__}")
        if allowed is not None and m[key] not in allowed:
            raise ContractError(f"{path}: field {key!r} must be one of {allowed}")
    if "\n" in m["algorithm"]:
        raise ContractError(f"{path}: algorithm must be one line")
    if m["build_required"] and not m["build_command"]:
        raise ContractError(f"{path}: build_required is true but build_command is null")
    if not m["build_required"] and m["build_command"]:
        raise ContractError(f"{path}: build_command given but build_required is false")
    if not m["entry"] or not all(isinstance(t, str) for t in m["entry"]):
        raise ContractError(f"{path}: entry must be a non-empty list of strings")
    if not all(isinstance(d, str) for d in m["dependencies"]):
        raise ContractError(f"{path}: dependencies must be strings")
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if m["name"] != folder:
        raise ContractError(f"{path}: name {m['name']!r} must equal its folder name {folder!r}")
    m["_dir"] = os.path.dirname(os.path.abspath(path))
    return m


def discover(root: str) -> list[dict]:
    """Every implementations/<name>/MANIFEST.json under root, validated, sorted by name."""
    base = os.path.join(root, "implementations")
    out = []
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        p = os.path.join(base, name, "MANIFEST.json")
        if os.path.isfile(p):
            out.append(load_manifest(p))
    return out


# ----------------------------------------------------------------- spec

def load_workloads(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        ws = json.load(fh)["workloads"]
    for w in ws:
        validate_workload(w)
    return ws


def load_held_workloads(path: str) -> list[dict]:
    """Workloads that are SPECCED and deliberately NOT RUN. Each validates as a workload and
    carries `held`: {"reason", "settles", "build_after"}. They render in SELECTION.md as held,
    counted at the top, and never produce a record."""
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        ws = json.load(fh)["workloads"]
    for w in ws:
        validate_workload(w)
        h = w.get("held")
        if not isinstance(h, dict) or not all(isinstance(h.get(k), str) and h.get(k) for k in ("reason", "settles", "build_after")):
            raise ContractError(f"held workload {w['name']}: held needs reason/settles/build_after")
    return ws


def validate_workload(w: dict) -> None:
    for key in ("name", "sources", "bounds", "conditions"):
        if key not in w:
            raise ContractError(f"workload missing {key!r}")
    c = w["conditions"]
    if c.get("sparsity") not in SPARSITY:
        raise ContractError(f"workload {w['name']}: sparsity must be one of {SPARSITY}")
    if c.get("scale_separation") not in SCALE_SEPARATION:
        raise ContractError(f"workload {w['name']}: scale_separation must be one of {SCALE_SEPARATION}")
    for s in w["sources"]:
        if s.get("type") not in ("charge", "current") or "position" not in s or "strength" not in s:
            raise ContractError(f"workload {w['name']}: source needs type/position/strength")


def _probes(bounds: dict, n: int = PROBE_COUNT, seed: int = PROBE_SEED) -> list[list[float]]:
    rng = random.Random(seed)
    lo, hi = bounds["min"], bounds["max"]
    return [[lo[i] + rng.random() * (hi[i] - lo[i]) for i in range(3)] for _ in range(n)]


def make_spec(workload: dict, resolution: int, tolerance: float | None = None) -> dict:
    """tolerance is the second knob: an impl whose manifest says knob=tolerance reads it and
    refines until its estimated local error is below it; every other impl ignores it. It is
    carried in the record so a tolerance-swept cell is never confused with a resolution one."""
    validate_workload(workload)
    if not isinstance(resolution, int) or resolution < 2:
        raise ContractError("resolution must be an integer >= 2")
    if tolerance is not None and not (isinstance(tolerance, (int, float)) and tolerance > 0):
        raise ContractError("tolerance must be a positive number or None")
    return {
        "spec_version": SPEC_VERSION,
        "workload": workload["name"],
        "conditions": dict(workload["conditions"]),
        "sources": [dict(s) for s in workload["sources"]],
        "bounds": {"min": list(workload["bounds"]["min"]), "max": list(workload["bounds"]["max"])},
        "resolution": resolution,
        "tolerance": tolerance,
        "probes": _probes(workload["bounds"]),
    }


def validate_spec(spec: dict) -> None:
    if spec.get("spec_version") != SPEC_VERSION:
        raise ContractError(f"spec_version {spec.get('spec_version')!r} is not {SPEC_VERSION}")
    for key in ("workload", "conditions", "sources", "bounds", "resolution", "probes"):
        if key not in spec:
            raise ContractError(f"spec missing {key!r}")


# ----------------------------------------------------------------- reference

def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def reference_field(spec: dict) -> dict:
    """E and B at every probe, from the spec's own source definitions. Pure Python."""
    E = [[0.0, 0.0, 0.0] for _ in spec["probes"]]
    B = [[0.0, 0.0, 0.0] for _ in spec["probes"]]
    for s in spec["sources"]:
        if s["type"] == "charge":
            q = float(s["strength"])
            for i, p in enumerate(spec["probes"]):
                r = _sub(p, s["position"])
                m = max(_norm(r), 1e-10)
                f = K_E * q / (m * m * m)
                E[i] = [E[i][k] + f * r[k] for k in range(3)]
        elif s["type"] == "current":
            I = float(s["strength"])
            start = s.get("start", s["position"])
            end = s.get("end", [c + 1 for c in s["position"]])
            dl = _sub(end, start)
            mid = [(start[k] + end[k]) / 2 for k in range(3)]
            for i, p in enumerate(spec["probes"]):
                r = _sub(p, mid)
                m = max(_norm(r), 1e-10)
                rhat = [c / m for c in r]
                c = _cross(dl, rhat)
                B[i] = [B[i][k] + MU_OVER_4PI * I * c[k] / (m * m) for k in range(3)]
    return {"E": E, "B": B}


def _median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def accuracy(reference: dict, reported: dict) -> dict:
    """Median relative error per field, over probes where the reference is nonzero.
    None when a field has no nonzero reference (a charge-only workload has no B)."""
    out = {}
    for key in ("E", "B"):
        ref, got = reference.get(key, []), reported.get(key, [])
        if len(got) != len(ref):
            raise ContractError(f"probe_field[{key}] has {len(got)} rows, spec has {len(ref)} probes")
        errs = []
        for r, g in zip(ref, got):
            nr = _norm(r)
            if nr <= 0.0:
                continue
            errs.append(_norm(_sub(g, r)) / nr)
        out[key] = _median(errs)
    return out


# ----------------------------------------------------------------- result records

def status(kind: str, reason: str | None = None) -> dict:
    if kind not in STATUSES:
        raise ContractError(f"unknown status {kind!r}")
    if kind != "OK" and not reason:
        raise ContractError(f"status {kind} needs a reason")
    return {"kind": kind, "reason": reason}


def render_status(st: dict) -> str:
    """Never blank. OK renders as OK; every other kind carries its reason."""
    if st["kind"] == "OK":
        return "OK"
    return f"{st['kind']}({st['reason']})"


def result_record(impl: str, workload: str, resolution: int, st: dict, *, wall_time=None,
                  peak_memory_mb=None, accuracy_vs_reference=None, points=None,
                  conditions=None, run_id=None, repeats=None, extra=None, tolerance=None) -> dict:
    rec = {
        "impl": impl, "workload": workload, "resolution": resolution, "tolerance": tolerance,
        "wall_time": wall_time, "peak_memory_mb": peak_memory_mb,
        "accuracy_vs_reference": accuracy_vs_reference, "status": st,
        "points": points, "conditions": conditions or {}, "run_id": run_id,
        "repeats": repeats, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if extra:
        rec.update(extra)
    return rec


# ----------------------------------------------------------------- impl-side helper

def read_spec(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    validate_spec(spec)
    return spec


def finish(out_path: str, wall_time: float, points: int, probe_field: dict, notes: str = "") -> None:
    """Called by an implementation at the end of its entry. Adds the child's own peak memory."""
    peak = None
    try:
        import resource
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak = kb / 1024.0 if os.uname().sysname != "Darwin" else kb / (1024.0 * 1024.0)
    except (ImportError, AttributeError, OSError):
        peak = None
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"wall_time": float(wall_time), "points": int(points),
                   "probe_field": probe_field, "peak_memory_mb": peak, "notes": notes}, fh)


def impl_args(argv: list[str]) -> tuple[str, str]:
    """Parse the two arguments the harness appends to every entry."""
    spec = out = None
    it = iter(argv)
    for a in it:
        if a == "--spec":
            spec = next(it, None)
        elif a == "--out":
            out = next(it, None)
    if not spec or not out:
        raise ContractError("entry needs --spec <path> --out <path>")
    return spec, out
