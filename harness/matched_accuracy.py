#!/usr/bin/env python3
"""
harness/matched_accuracy.py -- the time ratio at EQUAL error, which is the only ratio that
may be called a speedup. stdlib only.

    python harness/matched_accuracy.py            # table, from harness/results.jsonl
    python harness/matched_accuracy.py --json     # the same rows as JSON

The unmatched table (SELECTION.md, README) divides two wall times at the SAME resolution
argument, and the two paths do not deliver the same accuracy at the same argument: the
octree emits a fixed ~2000 points whatever resolution it is asked for (ENG-5) and its error
is flat, while the uniform grid's error falls as the cube root of its point count. A ratio
at unmatched accuracy is a statement about how much of the box one path was asked to fill.

This module asks the question the other way round. For a TARGET record (impl T, workload w,
resolution r, component c in {E, B}) it finds the resolution r* at which the SWEEP impl S
reaches the same error on the same probes, by log-log interpolation between the two sweep
records that bracket it, interpolates S's wall time at r* the same way, and reports

    ratio = wall_S(r*) / wall_T(r)

so a ratio above 1 means T is faster at equal accuracy and below 1 means slower. Both errors
come from contract.accuracy(): median relative error at the 256 seeded probes against the
pure-Python reference, so the metric is the same on both sides by construction.

A row is MATCHED only when the target error is bracketed by two OK sweep records whose
errors are monotone in resolution across the bracket. Otherwise it is NOT_BRACKETED (the
sweep never reached that error, and the row says on which side) or NON_MONOTONE. A row is
never blank and no row is dropped.

When a target impl's error does not change with resolution (fixed point count), its rows
collapse to one per (workload, component), with the wall time taken as the median over its
resolutions and the spread recorded; the collapse is reported, not assumed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run as _run  # noqa: E402

FLAT_TOL = 1e-9          # error spread below this across resolutions -> the impl is resolution-blind
COMPONENTS = ("E", "B")


def _ok(rec):
    return rec["status"]["kind"] == "OK" and rec.get("wall_time") is not None


def _err(rec, comp):
    acc = rec.get("accuracy_vs_reference") or {}
    return acc.get(comp)


def _loglog(x0, y0, x1, y1, y):
    """x at which the log-log line through (x0,y0),(x1,y1) reaches y."""
    lx0, lx1, ly0, ly1, ly = map(math.log, (x0, x1, y0, y1, y))
    t = (ly - ly0) / (ly1 - ly0)
    return math.exp(lx0 + t * (lx1 - lx0))


def sweep_curve(latest, impl, workload, comp):
    """[(resolution, error, wall)] for the OK records of impl on workload, by resolution."""
    pts = []
    for (i, w, r), rec in latest.items():
        if i == impl and w == workload and _ok(rec) and _err(rec, comp) is not None:
            pts.append((r, _err(rec, comp), rec["wall_time"]))
    return sorted(pts)


def match_one(target_err, curve):
    """(status, r*, wall*, bracket) for one target error against one sweep curve."""
    if len(curve) < 2:
        return "NOT_BRACKETED", None, None, "fewer than two sweep records"
    errs = [e for _, e, _ in curve]
    if target_err < min(errs):
        return "NOT_BRACKETED", None, None, f"sweep never got below {min(errs):.4g} (target {target_err:.4g})"
    if target_err > max(errs):
        return "NOT_BRACKETED", None, None, f"sweep never got above {max(errs):.4g} (target {target_err:.4g})"
    for (r0, e0, w0), (r1, e1, w1) in zip(curve, curve[1:]):
        lo, hi = min(e0, e1), max(e0, e1)
        if lo <= target_err <= hi:
            if e0 == e1:
                return "NON_MONOTONE", None, None, f"flat between {r0} and {r1}"
            if e0 < e1:  # error rising with resolution inside the bracket
                return "NON_MONOTONE", None, None, f"error rises from {r0} to {r1}"
            r_star = _loglog(r0, e0, r1, e1, target_err)
            w_star = _wall_at(r0, w0, r1, w1, r_star)
            return "MATCHED", r_star, w_star, f"{r0}..{r1}"
    return "NON_MONOTONE", None, None, "no monotone bracket"


def _wall_at(r0, w0, r1, w1, r):
    """wall at r on the log-log line through (r0,w0),(r1,w1)."""
    t = (math.log(r) - math.log(r0)) / (math.log(r1) - math.log(r0))
    return math.exp(math.log(w0) + t * (math.log(w1) - math.log(w0)))


def matched_rows(records, target=None, sweep=None):
    """One dict per (target impl, sweep impl, workload, component[, resolution])."""
    latest = _run.latest_per_cell(records)
    impls = sorted({k[0] for k in latest})
    workloads = sorted({k[1] for k in latest})
    rows = []
    for T in impls:
        if target and T != target:
            continue
        for S in impls:
            if S == T or (sweep and S != sweep):
                continue
            for w in workloads:
                for c in COMPONENTS:
                    t_pts = sweep_curve(latest, T, w, c)
                    if not t_pts:
                        continue
                    curve = sweep_curve(latest, S, w, c)
                    t_errs = [e for _, e, _ in t_pts]
                    flat = max(t_errs) - min(t_errs) < FLAT_TOL
                    groups = [t_pts] if flat else [[p] for p in t_pts]
                    for g in groups:
                        walls = [wl for _, _, wl in g]
                        t_wall = statistics.median(walls)
                        status, r_star, w_star, note = match_one(g[0][1], curve)
                        rows.append({
                            "target": T, "sweep": S, "workload": w, "component": c,
                            "target_resolutions": [r for r, _, _ in g],
                            "target_error": g[0][1],
                            "target_wall": t_wall,
                            "target_wall_spread": (min(walls), max(walls)),
                            "target_points": latest[(T, w, g[0][0])].get("points"),
                            "target_is_resolution_blind": flat,
                            "status": status,
                            "matched_resolution": r_star,
                            "matched_wall": w_star,
                            "matched_points": (round(r_star) ** 3) if r_star else None,
                            "ratio_sweep_over_target": (w_star / t_wall) if w_star else None,
                            "note": note,
                        })
    return rows


def render(rows) -> str:
    out = ["## Matched accuracy", "",
           "Time ratio at EQUAL error, the one figure that may be called a speedup. For each target",
           "record the sweep impl's resolution r* at which its error equals the target's is found by",
           "log-log interpolation of the sweep records bracketing it, and the sweep wall time at r*",
           "the same way. `ratio` = wall(sweep at r*) / wall(target): above 1 the target is faster at",
           "equal accuracy, below 1 slower. Same probes, same reference, same error metric on both",
           "sides (`contract.accuracy`). NOT_BRACKETED and NON_MONOTONE rows say why.", "",
           "| target | sweep | workload | comp | target err | target pts | target wall | r* | sweep pts | sweep wall at r* | ratio | status |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        res = ("all (resolution-blind)" if r["target_is_resolution_blind"]
               else str(r["target_resolutions"][0]))
        if r["status"] == "MATCHED":
            tail = (f"{r['matched_resolution']:.1f} | {r['matched_points']:,} | {r['matched_wall']:.4f} s | "
                    f"{r['ratio_sweep_over_target']:.3f}x | MATCHED ({r['note']})")
        else:
            tail = f"— | — | — | — | {r['status']}: {r['note']}"
        tp = f"{r['target_points']:,}" if r["target_points"] is not None else "?"
        out.append(f"| {r['target']} @ {res} | {r['sweep']} | {r['workload']} | {r['component']} | "
                   f"{r['target_error']:.4f} | {tp} | {r['target_wall']:.4f} s | {tail} |")
    out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--target", default=None)
    ap.add_argument("--sweep", default=None)
    a = ap.parse_args(argv)
    rows = matched_rows(_run.load_results(), a.target, a.sweep)
    if a.json:
        print(json.dumps(rows, indent=1))
    else:
        print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
