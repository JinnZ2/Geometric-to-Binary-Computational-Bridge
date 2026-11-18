"""T4 snapshot_class: what kind of snapshot is this, and may a run resume from it. Co-authored. CC0.

PROPOSED. Stdlib only; Python 3.10. Built from the four findings EBR_016 to
EBR_019 in ../CLAIM_TABLE.md, which rest on the received snapshot_delta.py
and its seed-0 record. Those are two toy systems; the classes are a way to
sort snapshot claims, not a theory of checkpointing.

  python -m experiments.experiment_bridge.snapshot.snapshot_class --output NEW_FILE.json
  python -m experiments.experiment_bridge.snapshot.snapshot_class --selftest

A snapshot is described by three things:
  content    FULL_STATE (everything the stepper reads) | SUMMARY (a many-to-one
             reduction of it, such as counts)
  fidelity   EXACT (stored without loss) | LOSSY (rounded, quantised, compressed)
  growth     for a LOSSY snapshot only: error at the horizon divided by the
             error injected at the snapshot, MEASURED on that system. Not
             given -> the class is VOID; it is never assumed.

CLASS                 when                                   RESUME RULE
CONTEXT_FREE_EXACT    FULL_STATE + EXACT                      always allowed
STABLE_LOSSY          FULL_STATE + LOSSY, growth <= 1         allowed only with a stated bound
                                                              (a refresh threshold counts as one)
CHAOTIC_REFRESH       FULL_STATE + LOSSY, growth > 1          allowed only with refresh (a resync
                                                              threshold tau); otherwise REFUSED
SUMMARY_ONLY          SUMMARY                                 VOID: the state cannot be resumed
                                                              from it. Resuming the summary's own
                                                              chain is a different snapshot, whose
                                                              content is that chain's full state.

GROWTH_LIMIT = 1 is a definition: at or below it the injected error did not
grow over the horizon measured. Above it the error grew; that is what the
record shows, and it is not a proof of chaos. The class name follows the
order; "growing" is all the rule tests. One horizon on one system decides the
class, so a class is a statement about that horizon.

resume() returns ALLOWED, REFUSED or VOID with the reason. It decides; it does
not run anything. An undeclared field, an unknown value, or a missing
measurement is VOID, never ALLOWED.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

VERSION = "experiment-bridge/snapshot-class-1"
HERE = Path(__file__).resolve().parent
RECORD = HERE.parent / "evidence" / "kimi_round2_as_received" / "snapshot_delta_seed0.json"
CLASSES = ("CONTEXT_FREE_EXACT", "STABLE_LOSSY", "CHAOTIC_REFRESH", "SUMMARY_ONLY")
CONTENT = ("FULL_STATE", "SUMMARY")
FIDELITY = ("EXACT", "LOSSY")
GROWTH_LIMIT = 1.0
SNAPSHOT_FIELDS = ("content", "fidelity", "growth")
REQUEST_FIELDS = ("bound", "refresh_tau")


def classify(snapshot):
    """{class, void_reason, basis}. class is None when it cannot be given."""
    out = {"class": None, "void_reason": None, "basis": None}
    if not isinstance(snapshot, dict):
        out["void_reason"] = "the snapshot is not a record"
        return out
    extra = [k for k in snapshot if k not in SNAPSHOT_FIELDS]
    if extra:
        out["void_reason"] = f"undeclared field {extra[0]!r}"
        return out
    content, fidelity, growth = (snapshot.get(k) for k in SNAPSHOT_FIELDS)
    if content not in CONTENT:
        out["void_reason"] = f"content {content!r} is not one of " + ", ".join(CONTENT)
        return out
    if content == "SUMMARY":
        out.update({"class": "SUMMARY_ONLY", "basis": "a many-to-one reduction of the state"})
        return out
    if fidelity not in FIDELITY:
        out["void_reason"] = f"fidelity {fidelity!r} is not one of " + ", ".join(FIDELITY)
        return out
    if fidelity == "EXACT":
        out.update({"class": "CONTEXT_FREE_EXACT", "basis": "the full state, stored without loss"})
        return out
    if isinstance(growth, bool) or not isinstance(growth, (int, float)):
        out["void_reason"] = "a LOSSY snapshot needs a measured growth; none is given"
        return out
    if growth != growth or growth < 0 or growth == float("inf"):
        out["void_reason"] = f"growth {growth!r} is not a finite ratio at or above 0"
        return out
    if growth <= GROWTH_LIMIT:
        out.update({"class": "STABLE_LOSSY",
                    "basis": f"injected error did not grow over the horizon (ratio {growth:.4g})"})
    else:
        out.update({"class": "CHAOTIC_REFRESH",
                    "basis": f"injected error grew over the horizon (ratio {growth:.4g})"})
    return out


def _positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and 0 < x < float("inf")


def resume(snapshot, request=None):
    """May a run resume from this snapshot? {decision, class, reason, condition}."""
    c = classify(snapshot)
    out = {"decision": "VOID", "class": c["class"], "reason": None, "condition": None}
    if c["class"] is None:
        out["reason"] = "no class: " + c["void_reason"]
        return out
    request = {} if request is None else request
    if not isinstance(request, dict) or any(k not in REQUEST_FIELDS for k in request):
        out["reason"] = "the request is not a {bound, refresh_tau} record"
        return out
    bound, tau = request.get("bound"), request.get("refresh_tau")
    for name, value in (("bound", bound), ("refresh_tau", tau)):
        if value is not None and not _positive(value):
            out["reason"] = f"{name} {value!r} is not a number above 0"
            return out
    if c["class"] == "CONTEXT_FREE_EXACT":
        out.update(decision="ALLOWED", reason="exact snapshot of the full state: always")
    elif c["class"] == "STABLE_LOSSY":
        if bound is None and tau is None:
            out.update(decision="REFUSED", reason="a lossy snapshot resumes only with a stated bound")
        elif bound is not None:
            out.update(decision="ALLOWED", reason="lossy, error not growing, bound stated",
                       condition={"bound": bound})
        else:                                     # a resync threshold is a stated bound
            out.update(decision="ALLOWED", reason="lossy, error not growing; the refresh "
                       "threshold is the stated bound", condition={"refresh_tau": tau})
    elif c["class"] == "CHAOTIC_REFRESH":
        if tau is None:
            out.update(decision="REFUSED", reason="error grows from a lossy snapshot: refresh is "
                       "required" + ("; a bound alone does not hold" if bound is not None else ""))
        else:
            out.update(decision="ALLOWED", reason="refresh declared",
                       condition={"refresh_tau": tau, "note": "resync when the deviation passes tau"})
    else:
        out.update(decision="VOID", reason="a summary does not determine the state it came from")
    return out


# ---------------------------------------------------------------- the received claims
# READING (by hand, 2026-11-17): what each snapshot_delta claim's snapshot holds.
# content and fidelity are read from the claim's own measurement text; growth is
# never typed here: it is looked up in the record at the path given.
READ = {
    "fib::word_resume_exact": ("FULL_STATE", "EXACT", None, {}),
    "fib::count_resume_exact": ("FULL_STATE", "EXACT", None, {}),
    "fib::word_from_counts": ("SUMMARY", None, None, {}),
    "float::bitwise_resume": ("FULL_STATE", "EXACT", None, {}),
    "sink::lossy_snapshot_drift": ("FULL_STATE", "LOSSY",
                                   ("drift_sink", "horizon_error_over_delta"), {}),
    "lorenz::lossy_snapshot_drift": ("FULL_STATE", "LOSSY",
                                     ("drift_lorenz", "horizon_error_over_delta"), {}),
    "sink::adaptive_refresh_bound": ("FULL_STATE", "LOSSY",
                                     ("drift_sink", "horizon_error_over_delta"), {"tau": True}),
    "lorenz::adaptive_refresh_bound": ("FULL_STATE", "LOSSY",
                                       ("drift_lorenz", "horizon_error_over_delta"), {"tau": True}),
    "lorenz::random_access_speedup": ("FULL_STATE", "EXACT", None, {}),
    "fib::random_access_work_ratio": ("FULL_STATE", "EXACT", None, {}),
}
READ_NOTES = {
    "fib::count_resume_exact": "the snapshot is the count pair and the chain resumed is the count "
                               "chain, so the counts ARE its full state",
    "fib::word_from_counts": "the same counts, asked for the word: a summary of the word",
    "sink::adaptive_refresh_bound": "the receiver's state is an approximation of the sender's; "
                                    "growth is taken from the same system's lossy-drift measurement",
    "lorenz::adaptive_refresh_bound": "as the sink row; the claim itself supplies the refresh",
}


def read_record(path=RECORD):
    data = Path(path).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def classify_claims(record):
    """One row per received snapshot claim: its class and what the resume rule says."""
    rows = []
    for c in record["claims"]:
        key = c["scope"].split("snapshot::", 1)[1]
        if key not in READ:
            rows.append({"scope": c["scope"], "class": None, "void_reason": "no reading for "
                         "this claim", "resume": None})
            continue
        content, fidelity, path, opts = READ[key]
        growth = record[path[0]][path[1]] if path else None
        snap = {"content": content, "fidelity": fidelity, "growth": growth}
        tau = c["value"] if opts.get("tau") else None
        got = classify(snap)
        rows.append({
            "scope": c["scope"], "claim_verdict": c["verdict"], "snapshot": snap,
            "growth_from": "/".join(path) if path else None,
            "class": got["class"], "basis": got["basis"], "void_reason": got["void_reason"],
            "reading_note": READ_NOTES.get(key),
            "resume": {"bare": resume(snap),
                       "with_bound": resume(snap, {"bound": 3.0}),
                       "with_refresh": resume(snap, {"refresh_tau": tau if tau else 0.5})},
            "refresh_declared_by_the_claim": tau})
    return rows


def build():
    record, digest = read_record()
    rows = classify_claims(record)
    return {"version": VERSION, "status": "PROPOSED",
            "scope": "sorts the ten received snapshot_delta claims; two toy systems, one seed",
            "record": {"path": "evidence/kimi_round2_as_received/snapshot_delta_seed0.json",
                       "sha256": digest},
            "growth_limit": GROWTH_LIMIT, "classes": list(CLASSES),
            "reading": "content and fidelity per claim are read by hand; growth is looked up",
            "claims": rows,
            "counts": {k: sum(1 for r in rows if r["class"] == k) for k in CLASSES},
            "unclassified": [r["scope"] for r in rows if r["class"] is None],
            "ebr": {
                "EBR_016": [r["scope"] for r in rows if r["class"] == "CONTEXT_FREE_EXACT"
                            and "resume" in r["scope"]],
                "EBR_017": [r["scope"] for r in rows if r["scope"].endswith("sink::lossy_snapshot_drift")],
                "EBR_018": [r["scope"] for r in rows if "lorenz" in r["scope"]
                            and r["class"] == "CHAOTIC_REFRESH"],
                "EBR_019": [r["scope"] for r in rows if r["class"] == "SUMMARY_ONLY"]},
            "human_interest": None, "ai_interest": None}


def selftest():
    exact = {"content": "FULL_STATE", "fidelity": "EXACT", "growth": None}
    stable = {"content": "FULL_STATE", "fidelity": "LOSSY", "growth": 0.05}
    grows = {"content": "FULL_STATE", "fidelity": "LOSSY", "growth": 16980.0}
    summary = {"content": "SUMMARY", "fidelity": None, "growth": None}
    checks = [
        ("exact resumes always", resume(exact)["decision"] == "ALLOWED"),
        ("lossy with no bound is refused", resume(stable)["decision"] == "REFUSED"),
        ("lossy with a bound is allowed", resume(stable, {"bound": 3.0})["decision"] == "ALLOWED"),
        ("growing error with no refresh is refused", resume(grows)["decision"] == "REFUSED"),
        ("a bound does not rescue a growing error",
         resume(grows, {"bound": 100.0})["decision"] == "REFUSED"),
        ("growing error with refresh is allowed",
         resume(grows, {"refresh_tau": 0.5})["decision"] == "ALLOWED"),
        ("a summary is VOID whatever is offered",
         resume(summary, {"bound": 1.0, "refresh_tau": 0.5})["decision"] == "VOID"),
        ("lossy with no measured growth has no class",
         classify({"content": "FULL_STATE", "fidelity": "LOSSY", "growth": None})["class"] is None),
        ("the ten received claims all get a class", not build()["unclassified"]),
    ]
    for name, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
    print(f"checks: {len(checks)}   failed: {sum(1 for _, ok in checks if not ok)}")
    return 0 if all(ok for _, ok in checks) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="T4 snapshot_class")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.output is None:
        parser.error("--output is required (or --selftest)")
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    rec = build()
    args.output.write_text(json.dumps(rec, indent=1, ensure_ascii=True) + "\n", encoding="ascii")
    for r in rec["claims"]:
        res = r["resume"]
        print(f"{r['scope'].split('snapshot::')[1]:32s} {str(r['class']):20s} "
              f"bare {res['bare']['decision']:8s} bound {res['with_bound']['decision']:8s} "
              f"refresh {res['with_refresh']['decision']}")
    print("counts:", rec["counts"])
    print("written ->", args.output)
    return 0 if not rec["unclassified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
