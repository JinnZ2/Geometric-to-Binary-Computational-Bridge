#!/usr/bin/env python3
"""Replay and read the Kimi round-2 specimens without changing them. Co-authored.

  python experiments/experiment_bridge/evidence/reproduce_kimi_round2.py --output NEW_FILE.json

Specimens: evidence/kimi_round2_as_received/ (three scripts, their seed-0
records, the revised entry), listed with sha256 in its MANIFEST.json. Every
script runs on a copy in a temporary directory. Refuses to overwrite an
existing output. Exit 0 when every check below holds, 1 when one does not,
2 when it cannot run. Stdlib only; takes about two minutes.

Per script, through claim_tools.py:
  replay      two runs; claims compared by scope, only claims[].ts left out;
              saved record against replay 1, replay 1 against replay 2
  literal     claims whose `measured` is a literal in the source: STRUCTURAL
  tolerance   one row per RECORDED claim (a call inside a loop makes several).
              band_text quotes, mechanically, every sentence of the claim's own
              measurement / failure text that mentions a band or a one-sided
              rule. A REASON is a reading, made by hand and listed in
              REASONS_READ below with the words it rests on; the harness checks
              those words are in the claim text. Everything else is UNSOURCED,
              including a band that is stated without saying why.

Independent census (this file's own, for the two RVQ scripts): the source is
loaded, the seed-0 codebooks and thresholds are rebuilt with the script's own
functions, and every held-out level is recounted: accepted although its
distance exceeds tau (a silent snap), or rejected although it does not. This
is what backs a STRUCTURAL void_escape_integrity, to the extent anything
does: a finite recount at seed 0 in the declared configuration, nothing wider.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import runpy
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "kimi_round2_as_received"
VERSION = "experiment-bridge/kimi-round2-replay-1"
SCRIPTS = (("toy_rvq_void_v2.py", "toy_rvq_void_v2_seed0.json"),
           ("toy_rvq_orthogonal.py", "toy_rvq_orthogonal_seed0.json"),
           ("snapshot_delta.py", "snapshot_delta_seed0.json"))

# READING (by hand, 2026-11-17): claims whose own text gives a reason for the
# tolerance. scope suffix -> the words of the claim text the reading rests on.
REASONS_READ = {
    "orth::projection_dominance": "projection is optimal in the span",
    "sink::adaptive_refresh_bound": "covering one-step overshoot",
    "lorenz::adaptive_refresh_bound": "covering one-step overshoot",
}
BAND_WORDS = re.compile(r"\bband\b|one-sided", re.I)

_spec = importlib.util.spec_from_file_location("claim_tools", HERE / "claim_tools.py")
CT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CT)


def manifest_check():
    listed = {f["path"]: f["sha256"] for f in
              json.loads((SOURCE / "MANIFEST.json").read_text(encoding="utf-8"))["files"]}
    actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(SOURCE.iterdir()) if p.is_file() and p.name != "MANIFEST.json"}
    return {"files": len(actual), "matches_manifest": listed == actual,
            "differences": sorted(set(listed.items()) ^ set(actual.items()))}


def census(script):
    """Recount threshold routing on the held-out split with the script's own functions."""
    with tempfile.TemporaryDirectory(prefix="experiment-bridge-census-") as td:
        shutil.copy2(SOURCE / script, Path(td) / script)
        m = runpy.run_path(str(Path(td) / script))
    seed = 0
    train = m["make_source"](m["N_TRAIN"], m["DIMS"], seed)
    test = m["make_source"](m["N_TEST"], m["DIMS"], seed + 500_000)
    books = m["train_rvq"](train, m["LEVELS"], m["CODES"], seed)
    if "set_thresholds_gated" in m:
        taus = m["set_thresholds_gated"](train, books, m["VOID_RATE_TARGET"])
    else:
        taus = m["set_thresholds"](train, books, m["VOID_RATE_TARGET"], gated=True)
    silent = wrongly_void = levels = voids = 0
    for v in test:
        idx, _ = m["encode"](v, books, taus)
        r = list(v)
        for k, j in enumerate(idx):
            levels += 1
            nearest, d2 = m["nearest"](r, books[k])
            if j is None:
                voids += 1
                wrongly_void += d2 <= taus[k]
            else:
                silent += d2 > taus[k] or j != nearest
                r = m["sub"](r, books[k][j])
    return {"script": script, "seed": seed, "held_out_samples": len(test),
            "levels_checked": levels, "void_levels": voids,
            "silent_over_threshold_snap_count": silent,
            "rejected_within_threshold_count": wrongly_void,
            "scope": "seed 0, the declared configuration, held-out split only"}


def claim_rows(script, saved_name):
    """One row per recorded claim, joined to the call that made it."""
    source = (SOURCE / script).read_text(encoding="utf-8")
    saved = json.loads((SOURCE / saved_name).read_text(encoding="utf-8"))
    calls = CT.pack_calls(source)
    literal = {r["call_line"]: r for r in CT.literal_measured(source)}
    tol = {r["call_line"]: r for r in CT.tolerance_provenance(source)}
    rows = []
    for c in saved["claims"]:
        call = CT.call_for(c["scope"], calls)
        line = call["line"] if call else None
        lit, t = literal.get(line, {}), tol.get(line, {})
        text = c.get("measurement", "") + "\n" + c.get("failure", "")
        bands = [x.strip() for x in re.split(r"(?<=[.;])\s+|\n", text) if BAND_WORDS.search(x)]
        words = next((w for k, w in REASONS_READ.items() if c["scope"].endswith(k)), None)
        if words is not None and words not in " ".join(text.split()):
            raise ValueError(f"reason read for {c['scope']} is not in its claim text")
        provenance = "STATED_IN_SOURCE" if t.get("stated_reason") else \
            "STATED_IN_CLAIM_TEXT" if words else "UNSOURCED"
        rows.append({"script": script, "scope": c["scope"], "verdict": c["verdict"],
                     "call_line": line,
                     "call_makes_several_claims": bool(call) and call["scope"] is None,
                     "tol_frac": c["tol_frac"],
                     "tol_frac_expression": t.get("tol_frac_expression"),
                     "tol_frac_is_literal": t.get("tol_frac_is_literal"),
                     "stated_reason": t.get("stated_reason") or words,
                     "reason_is_a_reading": words is not None,
                     "band_text": bands,
                     "tolerance_provenance": provenance,
                     "measured_expression": lit.get("measured_expression"),
                     "measured_line": lit.get("measured_line"),
                     "measured_is_literal": lit.get("measured_is_literal"),
                     "flag": lit.get("flag")})
    return rows


def build():
    record = {"version": VERSION, "status": "OBSERVED",
              "note": "Kimi round 2 replayed as unchanged specimens; synthetic toys, "
                      "not a neural codec and not a physical measurement",
              "environment": {"python": sys.version.split()[0], "platform": sys.platform},
              "manifest": manifest_check(), "scripts": [], "claims": [], "census": [],
              "human_interest": None, "ai_interest": None}
    censuses = {s: census(s) for s in ("toy_rvq_void_v2.py", "toy_rvq_orthogonal.py")}
    record["census"] = list(censuses.values())
    for script, saved in SCRIPTS:
        print(f"replaying {script} twice ...", flush=True)
        rep = CT.replay(SOURCE, script, saved)
        record["scripts"].append({
            "script": script, "saved": saved,
            "claims": rep["saved_vs_replay"]["claims"],
            "saved_vs_replay_equal": rep["saved_vs_replay"]["equal"],
            "replay_vs_replay_equal": rep["replay_vs_replay"]["equal"],
            "differences": [r for r in rep["saved_vs_replay"]["rows"]
                            + rep["replay_vs_replay"]["rows"] if not r["equal"]],
            "specimens_unchanged": rep["specimens_unchanged"]})
        for row in claim_rows(script, saved):
            if row["flag"] == "STRUCTURAL":
                c = censuses.get(script)
                integrity = row["scope"].endswith("void_escape_integrity")
                row["backing_probe"] = (
                    {"probe": "reproduce_kimi_round2.py census",
                     "silent_over_threshold_snap_count": c["silent_over_threshold_snap_count"],
                     "levels_checked": c["levels_checked"], "scope": c["scope"]}
                    if c and integrity else None)
            record["claims"].append(row)
    rows = record["claims"]
    record["summary"] = {
        "claims": len(rows),
        "saved_vs_replay_equal": sum(s["saved_vs_replay_equal"] for s in record["scripts"]),
        "replay_vs_replay_equal": sum(s["replay_vs_replay_equal"] for s in record["scripts"]),
        "structural": [r["scope"] for r in rows if r["flag"] == "STRUCTURAL"],
        "structural_without_backing_probe": [r["scope"] for r in rows
                                             if r["flag"] == "STRUCTURAL"
                                             and not r.get("backing_probe")],
        "tolerance_provenance": {k: sum(1 for r in rows if r["tolerance_provenance"] == k)
                                 for k in ("STATED_IN_SOURCE", "STATED_IN_CLAIM_TEXT", "UNSOURCED")},
        "unsourced_with_a_band_stated": [r["scope"] for r in rows
                                         if r["tolerance_provenance"] == "UNSOURCED"
                                         and r["band_text"]],
        "verdicts": {v: sum(1 for r in rows if r["verdict"] == v)
                     for v in sorted({r["verdict"] for r in rows})}}
    s = record["summary"]
    record["checks"] = {
        "manifest_matches": record["manifest"]["matches_manifest"],
        "all_claims_equal_saved_vs_replay": s["saved_vs_replay_equal"] == s["claims"],
        "all_claims_equal_replay_vs_replay": s["replay_vs_replay_equal"] == s["claims"],
        "specimens_unchanged": all(x["specimens_unchanged"] for x in record["scripts"]),
        "census_finds_no_silent_snap": all(c["silent_over_threshold_snap_count"] == 0
                                           and c["rejected_within_threshold_count"] == 0
                                           for c in record["census"]),
        "every_claim_joined_to_a_call": all(r["call_line"] for r in rows)}
    record["all_checks_passed"] = all(record["checks"].values())
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description="replay Kimi round 2")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    try:
        record = build()
    except (OSError, ValueError, KeyError, SyntaxError, RuntimeError) as exc:
        print(f"cannot run: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    args.output.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n",
                           encoding="ascii")
    s = record["summary"]
    print(f"claims {s['claims']}: saved vs replay equal {s['saved_vs_replay_equal']}, "
          f"replay vs replay equal {s['replay_vs_replay_equal']}")
    print("STRUCTURAL:", ", ".join(x.split("rvq::")[-1].split("snapshot::")[-1]
                                   for x in s["structural"]))
    print("tolerance provenance:", s["tolerance_provenance"])
    print("checks:", record["checks"])
    return 0 if record["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
