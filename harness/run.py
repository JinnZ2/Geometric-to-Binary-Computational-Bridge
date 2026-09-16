#!/usr/bin/env python3
"""
harness/run.py -- run every runnable implementation on every workload, then generate SELECTION.md.
stdlib only.

    python harness/run.py                                   # resolutions 16,32,48 ; repeats 3
    python harness/run.py --resolutions 16,32,48,64,96,128 --repeats 3 --timeout 600
    python harness/run.py --impl py_octree --workload dipole --resolutions 32
    python harness/run.py --regenerate                      # SELECTION.md from harness/results.jsonl, no runs
    python harness/run.py --impl py_octree_tol --tolerances 0.9,0.7,0.5,0.35,0.25   # the tolerance knob

Every (impl, workload, resolution) cell yields one result record (contract.result_record),
appended to harness/results.jsonl. NOT_RUNNABLE, TIMEOUT, FAILED and NOT_APPLICABLE are
records like any other; SELECTION.md renders them with their reason, never as a blank.

SELECTION.md is GENERATED and never hand-edited. Its axes are CONDITIONS, not scores:
field sparsity, resolution (swept), scale separation, build tolerance, memory ceiling.
Every impl that ran appears in its cell with its number. There is no "best" column and no
rank. Cells no impl could fill print NOT_MEASURED with the reason and are counted at the top.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import contract  # noqa: E402
import probe  # noqa: E402

RESULTS = os.path.join(HERE, "results.jsonl")
SELECTION = os.path.join(ROOT, "SELECTION.md")
WORKLOADS = os.path.join(HERE, "workloads.json")
HELD = os.path.join(HERE, "workloads_held.json")
MEMORY_CEILINGS_MB = (256, 1024, 4096, 16384)


# ----------------------------------------------------------------- one cell

def run_cell(m: dict, workload: dict, resolution: int, *, timeout: float, repeats: int,
             python: str = sys.executable, run_id: str | None = None, tolerance=None) -> dict:
    """One result record. Best-of-N wall time (the minimum is least contaminated by the
    scheduler); accuracy and memory from the last run."""
    name, wname = m["name"], workload["name"]
    spec = contract.make_spec(workload, resolution, tolerance)
    argv = [python if t == "{python}" else t for t in m["entry"]]
    walls, last, err = [], None, None
    with tempfile.TemporaryDirectory() as td:
        spec_path, out_path = os.path.join(td, "spec.json"), os.path.join(td, "result.json")
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(spec, fh)
        for _ in range(max(1, repeats)):
            if os.path.exists(out_path):
                os.remove(out_path)
            try:
                r = subprocess.run(argv + ["--spec", spec_path, "--out", out_path], cwd=m["_dir"],
                                   capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                return contract.result_record(name, wname, resolution,
                                              contract.status("TIMEOUT", f"{timeout:g}s"),
                                              conditions=spec["conditions"], run_id=run_id, repeats=repeats, tolerance=tolerance)
            except OSError as e:
                return contract.result_record(name, wname, resolution,
                                              contract.status("FAILED", str(e)[:160]),
                                              conditions=spec["conditions"], run_id=run_id, repeats=repeats, tolerance=tolerance)
            if r.returncode != 0 or not os.path.exists(out_path):
                tail = (r.stderr.strip().splitlines() or [f"exit {r.returncode}"])[-1][:160]
                return contract.result_record(name, wname, resolution,
                                              contract.status("FAILED", tail),
                                              conditions=spec["conditions"], run_id=run_id, repeats=repeats, tolerance=tolerance)
            with open(out_path, encoding="utf-8") as fh:
                last = json.load(fh)
            walls.append(float(last["wall_time"]))
    try:
        acc = contract.accuracy(contract.reference_field(spec), last["probe_field"])
    except (contract.ContractError, KeyError, TypeError) as e:
        return contract.result_record(name, wname, resolution,
                                      contract.status("FAILED", f"probe answer malformed: {e}"),
                                      conditions=spec["conditions"], run_id=run_id, repeats=repeats, tolerance=tolerance)
    return contract.result_record(name, wname, resolution, contract.status("OK"),
                                  wall_time=min(walls), peak_memory_mb=last.get("peak_memory_mb"),
                                  accuracy_vs_reference=acc, points=last.get("points"),
                                  conditions=spec["conditions"], run_id=run_id, repeats=repeats,
                                  extra={"notes": last.get("notes", "")}, tolerance=tolerance)


def covers(m: dict, wname: str) -> bool:
    return "*" in m["covers"] or wname in m["covers"]


# ----------------------------------------------------------------- a run

def run_all(resolutions, repeats, timeout, only_impl=None, only_workload=None, python=sys.executable,
            tolerances=()):
    """Sweep each impl along ITS knob: knob=resolution or none over `resolutions` (none ignores
    the value and says so in the record), knob=tolerance over `tolerances` at resolutions[0].
    Held workloads (harness/workloads_held.json) are never run."""
    manifests = contract.discover(ROOT)
    workloads = contract.load_workloads(WORKLOADS)
    rep = probe.probe_all(ROOT, python)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:6]
    records = []
    for m in manifests:
        if only_impl and m["name"] != only_impl:
            continue
        pr = rep["implementations"][m["name"]]
        if m["knob"] == "tolerance":
            cells = [(resolutions[0], float(t)) for t in tolerances]
        else:
            cells = [(res, None) for res in resolutions]
        for w in workloads:
            if only_workload and w["name"] != only_workload:
                continue
            for res, tolerance in cells:
                if not pr["runnable"]:
                    rec = contract.result_record(m["name"], w["name"], res,
                                                 contract.status("NOT_RUNNABLE", pr["reason"]),
                                                 conditions=w["conditions"], run_id=run_id, tolerance=tolerance)
                elif not covers(m, w["name"]):
                    rec = contract.result_record(m["name"], w["name"], res,
                                                 contract.status("NOT_APPLICABLE",
                                                                 f"manifest covers {m['covers']}"),
                                                 conditions=w["conditions"], run_id=run_id, tolerance=tolerance)
                else:
                    rec = run_cell(m, w, res, timeout=timeout, repeats=repeats, python=python, run_id=run_id,
                                   tolerance=tolerance)
                rec["machine"] = rep["machine"]
                rec["knob"] = m["knob"]
                records.append(rec)
                knob = f"tol {tolerance:<6}" if tolerance is not None else f"res {res:<4}"
                print(f"  {m['name']:<14} {w['name']:<12} {knob} {contract.render_status(rec['status'])}"
                      + (f"  {rec['wall_time']:.4f}s  {rec['peak_memory_mb'] or 0:.0f} MB  {rec['points']} pts"
                         if rec["status"]["kind"] == "OK" else ""), flush=True)
    with open(RESULTS, "a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    return run_id, records


def load_results(path=RESULTS):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def latest_per_cell(records):
    """The newest record for each (impl, workload, resolution) with no tolerance, across runs.
    Tolerance-swept records are a different cell kind; see latest_per_tol_cell."""
    latest = {}
    for rec in records:
        if rec.get("tolerance") is not None:
            continue
        key = (rec["impl"], rec["workload"], rec["resolution"])
        if key not in latest or rec["ts"] >= latest[key]["ts"]:
            latest[key] = rec
    return latest


def latest_per_tol_cell(records):
    """The newest record for each (impl, workload, tolerance), tolerance-swept records only."""
    latest = {}
    for rec in records:
        if rec.get("tolerance") is None:
            continue
        key = (rec["impl"], rec["workload"], rec["tolerance"])
        if key not in latest or rec["ts"] >= latest[key]["ts"]:
            latest[key] = rec
    return latest


# ----------------------------------------------------------------- SELECTION.md

def _fmt_acc(acc):
    if not acc:
        return "err ?"
    parts = []
    for k in ("E", "B"):
        v = acc.get(k)
        if v is not None:
            parts.append(f"{k} {v:.2e}")
    return " ".join(parts) if parts else "err ?"


def _cell(rec):
    if rec is None:
        return "NOT_MEASURED(no record)"
    if rec["status"]["kind"] != "OK":
        return contract.render_status(rec["status"])
    mem = f"{rec['peak_memory_mb']:.0f} MB" if rec.get("peak_memory_mb") is not None else "mem ?"
    return f"{rec['wall_time']:.4f} s · {mem} · {_fmt_acc(rec.get('accuracy_vs_reference'))}"


def render_selection(records, manifests, workloads, probe_report=None, held=()) -> str:
    latest = latest_per_cell(records)
    latest_tol = latest_per_tol_cell(records)
    impls = [m["name"] for m in manifests]                     # manifest order, alphabetical by folder
    tol_impls = [m["name"] for m in manifests if m.get("knob") == "tolerance"]
    resolutions = sorted({k[2] for k in latest})
    tolerances = sorted({k[2] for k in latest_tol}, reverse=True)
    L = []
    L.append("# SELECTION.md — GENERATED by `python harness/run.py`. Never hand-edited.")
    L.append("")
    L.append("Axes are CONDITIONS, not scores. Every implementation that ran appears in its cell")
    L.append("with its number. Nothing is ordered by merit or singled out. A cell no implementation")
    L.append("could fill says NOT_MEASURED and why; a row that could not run on this machine says")
    L.append("NOT_RUNNABLE and why. Numbers: wall seconds (minimum of N repeats) · peak MB of the child")
    L.append("process · median relative error of the probe answers vs `contract.reference_field`,")
    L.append("E and B separately. No implementation is the reference; `uniform_grid` is a peer.")
    L.append("")
    # counts at the top
    n_ok = sum(1 for r in list(latest.values()) + list(latest_tol.values()) if r["status"]["kind"] == "OK")
    not_ok = {}
    for r in list(latest.values()) + list(latest_tol.values()):
        if r["status"]["kind"] != "OK":
            not_ok.setdefault(contract.render_status(r["status"]), 0)
            not_ok[contract.render_status(r["status"])] += 1
    declared = {(w["conditions"]["sparsity"], w["conditions"]["scale_separation"]) for w in workloads}
    undeclared = [(s, sc) for s in contract.SPARSITY for sc in contract.SCALE_SEPARATION
                  if (s, sc) not in declared]
    compiled = [m for m in manifests if m["build_required"]]
    n_not_measured = len(undeclared) * max(1, len(resolutions)) + (0 if compiled else 1)
    if records:
        last = max(records, key=lambda r: r["ts"])
        mi = last.get("machine", {})
        L.append(f"Latest run `{last.get('run_id')}` on {mi.get('platform', '?')}, python {mi.get('python', '?')}, "
                 f"{mi.get('cpus', '?')} cpus, compiler {mi.get('compiler') or 'none'}. "
                 f"Records: {len(records)} total, {len(latest)} cells current.")
    L.append("")
    L.append("| count | what |")
    L.append("|---|---|")
    L.append(f"| {n_ok} | cells measured (status OK) |")
    for k, v in sorted(not_ok.items()):
        L.append(f"| {v} | cells {k} |")
    L.append(f"| {n_not_measured} | cells NOT_MEASURED: condition combinations no workload or implementation in this order instantiates (listed below) |")
    if held:
        L.append(f"| {len(held)} | workloads SPECCED and HELD, never run (listed at the end, with what un-holds each) |")
    L.append("")
    # implementations, from manifests only
    L.append("## Implementations (from each folder's MANIFEST.json; nothing else describes them)")
    L.append("")
    L.append("| name | language | dependencies | build | runs on phone | knob | algorithm | author claim | on this machine |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for m in manifests:
        pr = (probe_report or {}).get("implementations", {}).get(m["name"])
        here = "?" if pr is None else ("runnable" if pr["runnable"] else f"NOT_RUNNABLE({pr['reason']})")
        deps = ", ".join(m["dependencies"]) or "stdlib only"
        build = m["build_command"] if m["build_required"] else "none"
        L.append(f"| {m['name']} | {m['language']} | {deps} | {build} | {m['runs_on_phone']} | {m.get('knob', '?')} | "
                 f"{m['algorithm']} | {m['author_claim']} | {here} |")
    L.append("")
    # sparsity x scale, resolution swept
    L.append("## Field sparsity × scale separation, resolution swept")
    L.append("")
    for s in contract.SPARSITY:
        for sc in contract.SCALE_SEPARATION:
            L.append(f"### sparsity `{s}` · scale separation `{sc}`")
            L.append("")
            ws = [w for w in workloads if (w["conditions"]["sparsity"], w["conditions"]["scale_separation"]) == (s, sc)]
            if not ws:
                L.append(f"NOT_MEASURED(no workload in this order declares sparsity={s}, scale_separation={sc})")
                L.append("")
                continue
            for w in ws:
                L.append(f"**workload `{w['name']}`** — {w['conditions'].get('why', '')}")
                L.append("")
                L.append("| resolution | " + " | ".join(impls) + " |")
                L.append("|---|" + "---|" * len(impls))
                for res in resolutions:
                    row = [_cell(latest.get((i, w["name"], res))) for i in impls]
                    L.append(f"| {res} | " + " | ".join(row) + " |")
                L.append("")
    # tolerance swept: only impls whose knob is a tolerance have cells here
    L.append("## Tolerance swept (implementations whose knob is an error tolerance)")
    L.append("")
    L.append("Resolution means nothing to these; the sweep argument is the tolerance the implementation")
    L.append("refines to. Same probes, same reference, same error metric as the resolution tables.")
    L.append("")
    if not tol_impls:
        L.append("NOT_MEASURED(no implementation in this order declares knob=tolerance)")
        L.append("")
    elif not tolerances:
        L.append("NOT_MEASURED(no tolerance-swept record yet; run `python harness/run.py --tolerances ...`)")
        L.append("")
    else:
        for w in workloads:
            L.append(f"**workload `{w['name']}`**")
            L.append("")
            L.append("| tolerance | " + " | ".join(tol_impls) + " |")
            L.append("|---|" + "---|" * len(tol_impls))
            for tol in tolerances:
                row = []
                for i in tol_impls:
                    r = latest_tol.get((i, w["name"], tol))
                    row.append(_cell(r) + (f" · {r['points']:,} pts" if r and r["status"]["kind"] == "OK" else ""))
                L.append(f"| {tol:g} | " + " | ".join(row) + " |")
            L.append("")
    # build tolerance
    L.append("## Build tolerance")
    L.append("")
    L.append("| condition | implementations |")
    L.append("|---|---|")
    none_build = [m["name"] for m in manifests if not m["build_required"]]
    L.append("| none (no compiler) | " + (", ".join(none_build) if none_build else "NOT_MEASURED(no build-free implementation)") + " |")
    if compiled:
        L.append("| compiler available | " + ", ".join(m["name"] for m in compiled) + " |")
    else:
        cc = (probe_report or {}).get("machine", {}).get("compiler")
        L.append(f"| compiler available | NOT_MEASURED(no compiled implementation in this order; this machine's compiler: {cc or 'none'}) |")
    L.append("")
    # memory ceiling
    L.append("## Memory ceiling")
    L.append("")
    L.append("Which measured cells fit under a ceiling, from the child's peak RSS. A cell above every")
    L.append("ceiling is listed at the end; a cell with no memory reading says so.")
    L.append("")
    L.append("| ceiling | cells that fit (impl@resolution, worst workload) |")
    L.append("|---|---|")
    peak = {}
    nomem = []
    for (i, w, knob), r in list(latest.items()) + [((i, w, f"tol{t:g}"), r) for (i, w, t), r in latest_tol.items()]:
        if r["status"]["kind"] != "OK":
            continue
        if r.get("peak_memory_mb") is None:
            nomem.append(f"{i}@{knob}/{w}")
            continue
        peak[(i, knob)] = max(peak.get((i, knob), 0.0), r["peak_memory_mb"])
    for ceil in MEMORY_CEILINGS_MB:
        fits = sorted(f"{i}@{res} ({mb:.0f} MB)" for (i, res), mb in peak.items() if mb <= ceil)
        L.append(f"| {ceil} MB | " + (", ".join(fits) if fits else "NOT_MEASURED(no measured cell fits)") + " |")
    over = sorted(f"{i}@{res} ({mb:.0f} MB)" for (i, res), mb in peak.items() if mb > MEMORY_CEILINGS_MB[-1])
    L.append(f"| above {MEMORY_CEILINGS_MB[-1]} MB | " + (", ".join(over) if over else "none") + " |")
    if nomem:
        L.append(f"| no memory reading | {', '.join(sorted(nomem))} |")
    L.append("")
    L.append("## Undeclared condition cells")
    L.append("")
    for s, sc in undeclared:
        L.append(f"- sparsity={s}, scale_separation={sc}: NOT_MEASURED(no workload in this order declares it)")
    if not compiled:
        L.append("- build tolerance=compiler available: NOT_MEASURED(no compiled implementation in this order)")
    L.append("")
    if held:
        L.append("## Held workloads (specced, not built)")
        L.append("")
        L.append("Each validates as a workload and would run unchanged once its `held` field is removed.")
        L.append("None has a record. The reason each is held, what running it would settle, and what")
        L.append("un-holds it come from `harness/workloads_held.json`.")
        L.append("")
        L.append("| workload | sparsity | scale separation | why held | what it settles | build after |")
        L.append("|---|---|---|---|---|---|")
        for w in held:
            c, h = w["conditions"], w["held"]
            L.append(f"| {w['name']} | {c['sparsity']} | {c['scale_separation']} | {h['reason']} | {h['settles']} | {h['build_after']} |")
        L.append("")
    import matched_accuracy  # local import: matched_accuracy imports this module
    L.append("")
    L.append(matched_accuracy.render(matched_accuracy.matched_rows(records)))
    return "\n".join(L)


def regenerate(probe_report=None) -> str:
    text = render_selection(load_results(), contract.discover(ROOT), contract.load_workloads(WORKLOADS),
                            probe_report or probe.probe_all(ROOT),
                            held=contract.load_held_workloads(HELD))
    with open(SELECTION, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


# ----------------------------------------------------------------- cli

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resolutions", default="16,32,48")
    ap.add_argument("--tolerances", default="",
                    help="comma list for impls whose knob is a tolerance, e.g. 0.9,0.7,0.5,0.35,0.25")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--impl", default=None)
    ap.add_argument("--workload", default=None)
    ap.add_argument("--regenerate", action="store_true", help="only rebuild SELECTION.md from results.jsonl")
    a = ap.parse_args(argv)
    if a.regenerate:
        regenerate()
        print("wrote", os.path.relpath(SELECTION, ROOT))
        return 0
    resolutions = [int(x) for x in a.resolutions.split(",") if x.strip()]
    tolerances = [float(x) for x in a.tolerances.split(",") if x.strip()]
    run_id, records = run_all(resolutions, a.repeats, a.timeout, a.impl, a.workload, tolerances=tolerances)
    regenerate()
    print(f"run {run_id}: {len(records)} records appended to {os.path.relpath(RESULTS, ROOT)}; "
          f"wrote {os.path.relpath(SELECTION, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
