#!/usr/bin/env python3
"""
review.py  --  re-score every archived candidate against today's gates.

    python playground/review.py            # the report
    python playground/review.py --quiet    # exit code only

Exits nonzero when the archive no longer describes reality. That is not a
failure, it is news: something needs a human to look and re-record.

=====================================================================
WHY THIS EXISTS
=====================================================================
A verdict is not a fact. It is a fact under a set of gates, at a commit, with
stated tolerances. All three move.

They moved three times in one session on the field loop's correlation gate:
the threshold went from a fixed 0.35 to z/sqrt(n) to a permutation null, and
the lag went from a single fixed 3 to a scan to slots in seconds. Anything
scored against an earlier version was silently non-comparable afterwards, and
nothing said so. That is the whole failure mode this file addresses -- not
wrong answers, but answers that quietly stopped meaning what they said.

The dangerous case is NOT "a rejected candidate now passes". That is fine and
expected; knowledge moves. The dangerous case is a candidate that still passes
because it loosened its own tolerance. So the archive records the numbers that
decided each verdict, and this compares them BY VALUE -- the report names
`TOL_FRAC 0.01 -> 0.05`, rather than showing two hashes that differ.

=====================================================================
FINDINGS
=====================================================================
    UNCHANGED           same verdict, same thresholds, same checks
    VERDICT_CHANGED     it scores differently now. Read it.
    THRESHOLDS_MOVED    same verdict, but a constant that decided it changed.
                        The verdict is not comparable to the recorded one.
    CHECKS_REWRITTEN    same verdict, but checks() is different code
    UNRECORDED          a candidate exists with no archive entry
    ORPHANED            an archive entry whose module is gone
    TRIGGERED           a constant this record asked to be revisited on moved
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from playground import playground as P  # noqa: E402

CLEAN = ("UNCHANGED",)

# Candidates draw from seeded generators, so an evaluation is a pure function
# of the module's thresholds and its checks() source. Memoising on exactly
# those two means the cache cannot hide the thing this file exists to find:
# change either, and the key changes with it.
_EVAL_CACHE = {}


def evaluate_cached(name, mod):
    key = (name, repr(sorted(P.thresholds(mod).items())), P.checks_sha(mod))
    if key not in _EVAL_CACHE:
        _EVAL_CACHE[key] = P.evaluate_module(mod, name)
    return _EVAL_CACHE[key]


def _threshold_delta(old, new):
    """Named value changes, in both directions, including added and removed."""
    out = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k, "<absent>"), new.get(k, "<absent>")
        if a != b:
            out.append("%s %s -> %s" % (k, a, b))
    return out


def review_one(name, rec):
    """Compare one archived record against a fresh evaluation."""
    mod = P.load(name)
    now = evaluate_cached(name, mod)
    out = {"candidate": name, "problem": rec.get("problem"),
           "residence": rec.get("residence"),
           "was": rec.get("verdict"), "now": now["verdict"],
           "deltas": _threshold_delta(rec.get("thresholds", {}),
                                      P.thresholds(mod)),
           "checks_sha_was": rec.get("checks_sha"),
           "checks_sha_now": P.checks_sha(mod),
           "would_change_verdict": rec.get("would_change_verdict")}

    triggered = [d for d in out["deltas"]
                 if d.split(" ", 1)[0] in (rec.get("revisit_if_changed") or [])]
    out["triggered"] = triggered

    if out["was"] != out["now"]:
        out["finding"] = "VERDICT_CHANGED"
    elif out["deltas"]:
        out["finding"] = "TRIGGERED" if triggered else "THRESHOLDS_MOVED"
    elif out["checks_sha_was"] != out["checks_sha_now"]:
        out["finding"] = "CHECKS_REWRITTEN"
    else:
        out["finding"] = "UNCHANGED"
    return out


def review(path=None):
    recs = P.archive_records(path or P.ARCHIVE)
    live = set(P.candidates())
    rows = [review_one(n, recs[n]) for n in sorted(live & set(recs))]
    rows += [{"candidate": n, "finding": "UNRECORDED", "now": None,
              "was": None, "deltas": [], "triggered": [],
              "problem": getattr(P.load(n), "PROBLEM", None),
              "residence": None, "would_change_verdict": None}
             for n in sorted(live - set(recs))]
    rows += [{"candidate": n, "finding": "ORPHANED",
              "was": recs[n].get("verdict"), "now": None, "deltas": [],
              "triggered": [], "problem": recs[n].get("problem"),
              "residence": recs[n].get("residence"),
              "source_sha": recs[n].get("source_sha"),
              "would_change_verdict": recs[n].get("would_change_verdict")}
             for n in sorted(set(recs) - live)]
    return rows


def report(rows, out=sys.stdout):
    stale = [r for r in rows if r["finding"] not in CLEAN]
    print("ARCHIVE REVIEW  --  %d candidates, %d need a look"
          % (len(rows), len(stale)), file=out)
    print(file=out)
    for r in rows:
        head = "  %-12s %-22s %-12s" % (r["finding"], r["candidate"],
                                        r.get("residence") or "-")
        print(head, file=out)
        if r["finding"] == "VERDICT_CHANGED":
            print("      recorded %s, now %s" % (r["was"], r["now"]), file=out)
            if r.get("would_change_verdict"):
                print("      the record expected: %s"
                      % r["would_change_verdict"], file=out)
        elif r["finding"] in ("THRESHOLDS_MOVED", "TRIGGERED"):
            print("      verdict still %s, but the numbers that decided it "
                  "moved:" % r["now"], file=out)
            for d in r["deltas"]:
                mark = "!" if d in r["triggered"] else " "
                print("       %s  %s" % (mark, d), file=out)
            print("      a verdict under different constants is not the same "
                  "verdict. re-record it.", file=out)
        elif r["finding"] == "CHECKS_REWRITTEN":
            print("      verdict still %s, but checks() is different code "
                  "(%s -> %s)" % (r["now"], r["checks_sha_was"],
                                  r["checks_sha_now"]), file=out)
        elif r["finding"] == "UNRECORDED":
            print("      scores but has no archive entry. Nothing records why "
                  "it lives where it does.", file=out)
        elif r["finding"] == "ORPHANED":
            print("      archive says %s, but the module is gone." % r["was"],
                  file=out)
            if r.get("source_sha"):
                print("      recover: git cat-file -p %s" % r["source_sha"],
                      file=out)
            else:
                print("      no source_sha recorded, so it cannot be "
                      "recovered or re-scored. Principles transfer the "
                      "lesson; they do not restore the module.", file=out)
    print(file=out)
    if stale:
        print("  archive is out of date for: %s"
              % ", ".join(r["candidate"] for r in stale), file=out)
        print("  re-record with playground.archive(name, residence, ...) "
              "once you have decided what the change means.", file=out)
    else:
        print("  archive describes reality.", file=out)
    return len(stale)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--quiet", action="store_true",
                    help="exit code only, no report")
    args = ap.parse_args(argv)
    rows = review()
    if args.quiet:
        import io
        n = report(rows, out=io.StringIO())
    else:
        n = report(rows)
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
