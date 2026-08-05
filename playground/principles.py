#!/usr/bin/env python3
"""
principles.py  --  the failure shapes, compressed, and what still catches none.

    python playground/principles.py               # the library
    python playground/principles.py show P-FIXED-PROBE
    python playground/principles.py coverage      # which are mechanised
    python playground/principles.py gaps          # only the ones that are not

=====================================================================
WHAT COMPRESSION BUYS, AND WHAT IT DOES NOT
=====================================================================
Tags are for TRANSFER and SCREENING. They are not for storage and they are
not a substitute for the module.

  You cannot re-run a candidate from its principles. If the module is gone,
  no summary brings back the ability to re-score it under new gates. That
  problem has a different answer and it costs 40 bytes: record the git blob
  sha of the source. Git already stores the content; the archive only needs
  to point at it. See playground.source_sha().

  What compression DOES buy: roughly 60 findings across this archive collapse
  to eleven shapes, and several of them turned up in files that share no code
  and no author intent. GIES-1 and KEA-7 are the same blindness in two
  formalisms that never met. That is the useful direction -- given a new
  candidate, which known shapes does it match?

A principle needs TWO independent instances. One instance is an anecdote.
Entries with one are marked PROVISIONAL rather than dropped or promoted,
because dropping loses the lesson and promoting overstates it.

The column that matters is `mechanised_by`. Four of eleven are caught
automatically today. The rest are the gap list, and the gap list is the point
of the file -- a principle nothing checks is a principle you will re-learn.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LIBRARY = os.path.join(HERE, "PRINCIPLES.json")
MIN_INSTANCES = 2


def library(path=LIBRARY):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def principles(path=LIBRARY):
    return library(path)["principles"]


def principle(pid, path=LIBRARY):
    for p in principles(path):
        if p["id"] == pid:
            return p
    raise KeyError("no such principle: %r. known: %s"
                   % (pid, ", ".join(p["id"] for p in principles(path))))


def status_of(p):
    """ESTABLISHED needs MIN_INSTANCES; anything less is PROVISIONAL.

    Computed, not trusted -- the file states a status and this checks it,
    so an entry cannot be promoted by editing one field.
    """
    return "ESTABLISHED" if len(p["instances"]) >= MIN_INSTANCES \
        else "PROVISIONAL"


def disagreements(path=LIBRARY):
    """Entries whose declared status does not match their instance count."""
    return [(p["id"], p["status"], status_of(p))
            for p in principles(path) if p["status"] != status_of(p)]


def coverage(path=LIBRARY):
    ps = principles(path)
    mech = [p for p in ps if p.get("mechanised_by")]
    return {"total": len(ps), "mechanised": len(mech),
            "gaps": [p["id"] for p in ps if not p.get("mechanised_by")],
            "established": sum(1 for p in ps if status_of(p) == "ESTABLISHED"),
            "instances": sum(len(p["instances"]) for p in ps)}


def tags(path=LIBRARY):
    """Every instance tag -> the principle it belongs to."""
    out = {}
    for p in principles(path):
        for i in p["instances"]:
            out.setdefault(i["tag"], []).append(p["id"])
    return out


def match(record, path=LIBRARY):
    """Which principles an archive record cites. Cheap, and deliberately so.

    This does NOT infer shapes from a candidate's code. Pattern-matching a
    failure shape out of source is exactly the kind of thing that would look
    clever and be unfalsifiable; the citation is a human act and stays one.
    """
    cited = list(record.get("principles") or [])
    known = {p["id"] for p in principles(path)}
    return {"cited": [c for c in cited if c in known],
            "unknown": [c for c in cited if c not in known]}


# ---------------------------------------------------------------------
def _fmt(p, full=False):
    head = "  %-26s %-12s %2d inst  %s" % (
        p["id"], status_of(p), len(p["instances"]),
        "mechanised" if p.get("mechanised_by") else "NOT MECHANISED")
    if not full:
        return head + "\n      " + p["name"]
    out = [head, "", "  %s" % p["name"], "", "  %s" % p["statement"], ""]
    if p.get("provisional_because"):
        out += ["  PROVISIONAL BECAUSE", "    %s" % p["provisional_because"],
                ""]
    out += ["  DETECTOR", "    %s" % p["detector"], ""]
    out += ["  MECHANISED BY", "    %s" % (p.get("mechanised_by")
                                           or "nothing. " + (p.get("gap_note")
                                                             or "gap.")), ""]
    out += ["  INSTANCES"]
    out += ["    %-14s %s" % (i["tag"], i["what"]) for i in p["instances"]]
    if p.get("cost_when_missed"):
        out += ["", "  COST WHEN MISSED", "    %s" % p["cost_when_missed"]]
    return "\n".join(out)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "list"
    lib = library()
    if cmd == "list":
        c = coverage()
        print("FAILURE SHAPES  --  %d principles, %d instances, "
              "%d mechanised, %d gaps"
              % (c["total"], c["instances"], c["mechanised"],
                 len(c["gaps"])))
        print("  %s" % lib["why_this_file"].split(". ")[0] + ".")
        print()
        for p in principles():
            print(_fmt(p))
            print()
        bad = disagreements()
        if bad:
            print("  DECLARED STATUS DISAGREES WITH INSTANCE COUNT:")
            for pid, declared, computed in bad:
                print("    %s declared %s, computes %s" % (pid, declared,
                                                           computed))
        print("  python playground/principles.py gaps")
    elif cmd == "show" and len(argv) > 2:
        print(_fmt(principle(argv[2]), full=True))
    elif cmd == "coverage":
        c = coverage()
        print("%d principles, %d instances" % (c["total"], c["instances"]))
        print("%d ESTABLISHED (>=%d instances), %d PROVISIONAL"
              % (c["established"], MIN_INSTANCES,
                 c["total"] - c["established"]))
        print("%d mechanised, %d not" % (c["mechanised"], len(c["gaps"])))
        print()
        for p in principles():
            print("  %-26s %s" % (p["id"], p.get("mechanised_by") or "--"))
    elif cmd == "gaps":
        gaps = [p for p in principles() if not p.get("mechanised_by")]
        print("NOT MECHANISED  (%d of %d)" % (gaps and len(gaps) or 0,
                                              len(principles())))
        print("  A principle nothing checks is a principle you will re-learn.")
        print()
        for p in gaps:
            print("  %-26s %s" % (p["id"], p["name"]))
            print("      detector: %s" % p["detector"])
            if p.get("gap_note"):
                print("      %s" % p["gap_note"])
            print()
    elif cmd == "tags":
        for tag, pids in sorted(tags().items()):
            print("  %-14s %s" % (tag, ", ".join(pids)))
    else:
        print("usage: principles.py [list | show ID | coverage | gaps | tags]")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
