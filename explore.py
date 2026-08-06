#!/usr/bin/env python3
"""
explore.py  --  the archive as one space, instead of folder by folder.

    python explore.py                 # screens x families: where each has been carried
    python explore.py gaps            # empty cells, with the precondition to judge them
    python explore.py bridges         # principles that span folders, and where they do not
    python explore.py neighbours ER-1 # what shares a screen, principle or cause with this
    python explore.py frontier        # open problems, and what already touches their family

Stdlib only. Reads CLAIMS_REGISTER.json, PRINCIPLES.json and the scan. Stores
nothing.

=====================================================================
WHAT THIS IS FOR
=====================================================================
This archive's best results have all been CROSS-FOLDER transfers, and none of
them were found by reading a folder.

  GIES-1 and KEA-7 are the same blindness in two formalisms that never met --
  outer(v,v) losing the sign of v, and a Keating energy exactly even in the
  displacement. Neither folder could have found the other.

  The Orbach screen was extracted from one dead Er claim and now screens any
  deep-level coherence proposal in any host.

  repo_guard's three stages each arrived from a different folder. The guard is
  the crystallised residue of three unrelated deaths.

So the useful question is not "what is in this folder" but "what has been
proven somewhere and never carried anywhere else". That is a coverage matrix,
and coverage matrices have the property that matters here: they make no
claims. An empty cell is not a suggestion, it is an absence, and a human reads
the screen's `applies_when` to decide whether the absence is a real gap or a
category error.

=====================================================================
WHAT THIS DELIBERATELY IS NOT
=====================================================================
It does not propose combinations. A tool that emitted "have you considered
applying X to Y" for every pair would produce a cross-product of
plausible-sounding suggestions with no way to rank them and no way to be
wrong -- which is P-UNFALSIFIABLE wearing the shape of a research assistant,
and this archive has spent its whole history removing that shape.

The line: this file reports STRUCTURE that is already in the register.
Deciding which empty cell is worth an afternoon is a judgement, and it stays
one. If a specific proposal comes out of reading this, playground/ is where it
gets scored.

Nor does it "expand into higher dimensions" in the domain sense -- 8 states to
32 states to some larger polytope is a physics question about what silicon
does, not something a script can enumerate. A generator of higher-dimensional
encodings with no falsifier attached would be the same defect again.
"""
import collections
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import claims_index as CI  # noqa: E402
import graveyard as G  # noqa: E402
from playground import principles as PR  # noqa: E402


def families(reg=None):
    reg = CI.register() if reg is None else reg
    return sorted({c["family"] for c in reg.values()})


def screen_coverage(reg=None):
    """screen -> {family: [claim ids]}. The empty cells are the space."""
    reg = CI.register() if reg is None else reg
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    meta = {}
    for c in reg.values():
        sc = (c.get("salvage") or {}).get("screen")
        if not sc:
            continue
        out[sc["name"]][c["family"]].append(c["id"])
        meta.setdefault(sc["name"], {"rule": sc["rule"],
                                     "applies_when": sc.get("applies_when"),
                                     "mechanised_by": sc.get("mechanised_by")})
    return {k: dict(v) for k, v in out.items()}, meta


def gaps(reg=None):
    """Screens, and the families they have never been carried into.

    Reported with the precondition, because most empty cells are category
    errors and only a reader can tell which.
    """
    reg = CI.register() if reg is None else reg
    cov, meta = screen_coverage(reg)
    fams = families(reg)
    out = []
    for name in sorted(cov):
        seen = set(cov[name])
        out.append({"screen": name, "reach": sum(len(v) for v in
                                                 cov[name].values()),
                    "applied_in": sorted(seen),
                    "absent_from": [f for f in fams if f not in seen],
                    "applies_when": meta[name]["applies_when"],
                    "rule": meta[name]["rule"],
                    "mechanised_by": meta[name]["mechanised_by"]})
    return sorted(out, key=lambda e: (-e["reach"], e["screen"]))


def _folder_of(path):
    return path.split(os.sep)[0] if os.sep in path else "."


def bridges():
    """Principles whose instances span folders, and the folders they miss.

    A principle found in two folders that share no code has already proved it
    travels. A third folder with claims and no instance is where to look next
    -- or where the principle genuinely does not apply, which is equally worth
    knowing and equally not decidable here.
    """
    idx = CI.scan()
    claim_folders = collections.defaultdict(set)
    for cid, sites in idx.items():
        for files in sites.values():
            for f in files:
                claim_folders[cid].add(_folder_of(f))
    out = []
    for p in PR.principles():
        folders = set()
        for i in p["instances"]:
            folders.add(_folder_of(i["where"]))
        out.append({"principle": p["id"], "name": p["name"],
                    "instances": len(p["instances"]),
                    "folders": sorted(folders), "spans": len(folders),
                    "mechanised_by": p.get("mechanised_by")})
    return sorted(out, key=lambda e: (-e["spans"], -e["instances"]))


def neighbours(cid, reg=None):
    """What else in the archive shares this claim's screen, cause or principle."""
    reg = CI.register() if reg is None else reg
    if cid not in reg:
        raise KeyError("%s is not in the register. `python claims_index.py "
                       "unregistered` lists what is not." % cid)
    me = reg[cid]
    sv = me.get("salvage") or {}
    out = {"claim": cid, "statement": me["statement"], "by_screen": [],
           "by_cause": [], "by_principle": []}
    myscreen = (sv.get("screen") or {}).get("name")
    for other in sorted(reg.values(), key=lambda c: c["id"]):
        if other["id"] == cid:
            continue
        osv = other.get("salvage") or {}
        if myscreen and (osv.get("screen") or {}).get("name") == myscreen:
            out["by_screen"].append(other["id"])
        if sv.get("cause") and osv.get("cause") == sv["cause"]:
            out["by_cause"].append(other["id"])
    for p in PR.principles():
        ids = {i.get("claim") for i in p["instances"] if i.get("claim")}
        if cid in ids:
            out["by_principle"].append({"principle": p["id"],
                                        "with": sorted(ids - {cid})})
    return out


def frontier():
    """Open problems, and which screens have already been used in their family.

    Not a recommendation. A problem whose family already carries a screen is a
    place to check the screen was actually applied before treating the problem
    as untouched.
    """
    import json
    with open(os.path.join(ROOT, "playground", "OPEN_PROBLEMS.json"),
              encoding="utf-8") as fh:
        probs = json.load(fh)["problems"]
    cov, meta = screen_coverage()
    by_family = collections.defaultdict(list)
    for name, fams in cov.items():
        for f in fams:
            by_family[f].append(name)
    out = []
    for p in probs:
        fam = p["id"].split("-")[0]
        out.append({"problem": p["id"], "title": p["title"], "kind": p["kind"],
                    "family": fam,
                    "screens_in_family": sorted(by_family.get(fam, []))})
    return out


# ---------------------------------------------------------------------
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "coverage"
    if cmd == "coverage":
        cov, meta = screen_coverage()
        fams = families()
        w = max(len(n) for n in cov) + 2
        print("SCREENS x FAMILIES  --  where each proven check has been carried")
        print("  An empty cell is an absence, not a suggestion. Read")
        print("  `explore.py gaps` for the precondition before judging one.")
        print()
        print("  %-*s %s" % (w, "", " ".join("%-5s" % f[:5] for f in fams)))
        for name in sorted(cov, key=lambda n: (-sum(len(v) for v in
                                                    cov[n].values()), n)):
            row = " ".join("%-5s" % (len(cov[name].get(f, [])) or ".")
                           for f in fams)
            print("  %-*s %s  %s" % (w, name, row,
                                     meta[name]["mechanised_by"] or ""))
        print()
        print("  %d screens over %d families" % (len(cov), len(fams)))
    elif cmd == "gaps":
        gs = gaps()
        print("WHERE A PROVEN SCREEN HAS NOT BEEN CARRIED  (%d screens)"
              % len(gs))
        print("  Most empty cells are category errors. The precondition is")
        print("  printed so you can tell which are not.")
        for e in gs:
            print()
            print("  %-32s reach %d   %s"
                  % (e["screen"], e["reach"],
                     e["mechanised_by"] or "NOT MECHANISED"))
            print("      applies when: %s" % e["applies_when"])
            print("      used in:      %s" % ", ".join(e["applied_in"]))
            print("      never in:     %s" % ", ".join(e["absent_from"]))
    elif cmd == "bridges":
        bs = bridges()
        print("PRINCIPLES BY HOW FAR THEY TRAVEL")
        print("  A shape found in folders that share no code has proved it")
        print("  travels. GIES-1 and KEA-7 are the worked example.")
        print()
        for e in bs:
            print("  %-26s spans %d folder(s), %d instances  %s"
                  % (e["principle"], e["spans"], e["instances"],
                     e["mechanised_by"] or "NOT MECHANISED"))
            print("      %s" % ", ".join(e["folders"]))
    elif cmd == "neighbours" and len(argv) > 2:
        n = neighbours(argv[2])
        print("%s  %s" % (n["claim"], n["statement"]))
        print()
        print("  same screen:    %s" % (", ".join(n["by_screen"]) or "-"))
        print("  same cause:     %s" % (", ".join(n["by_cause"]) or "-"))
        for p in n["by_principle"]:
            print("  %-15s %s" % (p["principle"] + ":",
                                  ", ".join(p["with"]) or "(only instance "
                                  "with an id)"))
        if not n["by_principle"]:
            print("  principles:     -")
    elif cmd == "frontier":
        fs = frontier()
        print("OPEN PROBLEMS, AND WHAT ALREADY TOUCHES THEIR FAMILY  (%d)"
              % len(fs))
        print("  A problem whose family already carries a screen is a place to")
        print("  check the screen was applied before calling it untouched.")
        print()
        for e in fs:
            print("  %-10s %-9s %s" % (e["problem"], e["kind"], e["title"]))
            if e["screens_in_family"]:
                print("      screens already used in %s: %s"
                      % (e["family"], ", ".join(e["screens_in_family"])))
    else:
        print("usage: explore.py [coverage | gaps | bridges | "
              "neighbours ID | frontier]")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
