#!/usr/bin/env python3
"""
graveyard.py  --  what this archive stopped believing, and what it bought.

    python graveyard.py             # the deaths, grouped by cause
    python graveyard.py screens     # the reusable checks, ranked by reach
    python graveyard.py todo        # proven screens nothing has mechanised
    python graveyard.py loose       # deaths in the tree the register missed

Stdlib only. Reads CLAIMS_REGISTER.json and scans; stores nothing of its own.

=====================================================================
WHY LOOK AT THE DEAD
=====================================================================
Every other view in this repo answers "what do we believe". This one answers
"what did we stop believing, and what did it cost" -- which is the more
useful question, because the archive's most reusable output has consistently
been the SCREEN rather than the result.

A screen is the two-line check that kills the whole class, not just the one
claim that died. The Orbach comparison -- crystal-field gap against kT -- was
extracted from one dead Er claim and now screens any deep-level coherence
proposal in any host. The gap-mode mass criterion killed two independent
claims in one stroke. Those are permanent; the proposals they killed were not.

So the ranking that matters is REACH: how many independent claims a screen has
already killed. A screen with reach >= 2 has proved it generalises, and
`todo` lists the ones nothing catches automatically. Each entry there is a
mistake this archive has already paid for once and can still make again.

=====================================================================
WHAT IT CANNOT DO
=====================================================================
It cannot find deaths nobody recorded. `loose` scans for the words a person
writes when abandoning something -- superseded, deprecated, withdrawn -- and
reports files carrying them with no register entry, but that is a prompt for a
human, not a detection. A proposal that died quietly and left no word behind
is invisible here and there is no honest way around that.
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import claims_index as CI  # noqa: E402

# What a person writes when abandoning something. Deliberately few and
# specific: broadening this turns it into a word-frequency toy.
ABANDON_RX = re.compile(
    r'\b(superseded|deprecated|withdrawn)\b', re.I)
LOOSE_SKIP = ("legacy", "node_modules", "package-lock.json", "CLAIMS.md",
              "CLAUDE.md", "CLAIMS_REGISTER.json", "claims_index.py",
              "graveyard.py", "playground/", "tests/")


def deaths(reg=None):
    """Every recorded death: what died, what killed it, of what."""
    reg = CI.register() if reg is None else reg
    out = []
    for c in sorted(reg.values(), key=lambda x: x["id"]):
        sv = c.get("salvage")
        if not sv:
            continue
        if c["status"] == "dead":
            out.append({"killed": c["statement"], "by": None, "id": c["id"],
                        "cause": sv["cause"], "keep": sv["keep"],
                        "screen": sv.get("screen")})
        elif sv.get("killed"):
            out.append({"killed": sv["killed"], "by": c["id"],
                        "id": c["id"], "cause": sv["cause"],
                        "keep": sv["keep"], "screen": sv.get("screen")})
    return out


def screens(reg=None):
    """Screen name -> the claims that used it. Reach is how many it killed."""
    reg = CI.register() if reg is None else reg
    by = collections.defaultdict(lambda: {"claims": [], "rule": None,
                                          "mechanised_by": None})
    for c in reg.values():
        sc = (c.get("salvage") or {}).get("screen")
        if not sc:
            continue
        e = by[sc["name"]]
        e["claims"].append(c["id"])
        e["rule"] = sc["rule"]
        e["mechanised_by"] = e["mechanised_by"] or sc.get("mechanised_by")
    for e in by.values():
        e["claims"].sort()
        e["reach"] = len(e["claims"])
    return dict(by)


def unmechanised(reg=None, min_reach=1):
    """Screens nothing catches automatically, worst first by reach."""
    return sorted((dict(e, name=n) for n, e in screens(reg).items()
                   if not e["mechanised_by"] and e["reach"] >= min_reach),
                  key=lambda e: (-e["reach"], e["name"]))


def mechanisation_is_real(reg=None):
    """A screen claiming to be mechanised must name something that exists.

    Otherwise the todo list shortens by assertion, which is the one way this
    file could quietly stop being useful.
    """
    import importlib
    bad = []
    for name, e in sorted(screens(reg).items()):
        target = e["mechanised_by"]
        if not target:
            continue
        mod, _, attr = target.rpartition(".")
        try:
            if not hasattr(importlib.import_module(mod), attr):
                bad.append((name, target, "no such attribute"))
        except ImportError:
            bad.append((name, target, "no such module"))
    return bad


def loose(root=ROOT, reg=None):
    """Files that read as abandoned but carry no register entry.

    A prompt for a human, not a detection.
    """
    reg = CI.register() if reg is None else reg
    idx = CI.scan(root)
    registered_files = set()
    for cid in reg:
        for files in idx.get(cid, {}).values():
            registered_files.update(files)
    out = []
    for rel in CI._files(root):
        if any(s in rel for s in LOOSE_SKIP):
            continue
        try:
            with open(os.path.join(root, rel), encoding="utf-8",
                      errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        if CI.GENERATED_MARK in text[:400]:
            continue
        hits = ABANDON_RX.findall(text)
        if hits and rel not in registered_files:
            for ln in text.splitlines():
                if ABANDON_RX.search(ln):
                    out.append({"file": rel, "line": " ".join(ln.split())[:110],
                                "word": ABANDON_RX.search(ln).group(0).lower()})
                    break
    return sorted(out, key=lambda d: d["file"])


# ---------------------------------------------------------------------
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "deaths"
    reg = CI.register()
    if cmd == "deaths":
        ds = deaths(reg)
        cz = CI.causes()
        groups = collections.defaultdict(list)
        for d in ds:
            groups[d["cause"]].append(d)
        print("THE GRAVEYARD  --  %d recorded deaths" % len(ds))
        print("  what this archive stopped believing, and what it bought.")
        for cause in sorted(groups):
            print()
            print("== %s  (%d)" % (cause, len(groups[cause])))
            print("   %s" % cz.get(cause, ""))
            for d in groups[cause]:
                print()
                print("   %s" % d["killed"])
                print("      killed by  %s%s" % (d["id"],
                                                 "" if d["by"] else
                                                 "  (the claim itself)"))
                if d["screen"]:
                    print("      screen     %s" % d["screen"]["name"])
        print()
        print("  python graveyard.py screens")
    elif cmd == "screens":
        sc = screens(reg)
        print("SCREENS BY REACH  --  %d screens, %d claims"
              % (len(sc), sum(e["reach"] for e in sc.values())))
        print("  Reach is how many independent claims a screen has already")
        print("  killed. Reach >= 2 has proved it generalises.")
        print()
        for name, e in sorted(sc.items(), key=lambda kv: (-kv[1]["reach"],
                                                          kv[0])):
            print("  %-32s reach %d   %s"
                  % (name, e["reach"], e["mechanised_by"] or "NOT MECHANISED"))
            print("      %s" % e["rule"])
            print("      from: %s" % ", ".join(e["claims"]))
            print()
    elif cmd == "todo":
        un = unmechanised(reg)
        proven = [e for e in un if e["reach"] >= 2]
        print("PROVEN SCREENS NOTHING CATCHES AUTOMATICALLY")
        print("  Each is a mistake this archive has already paid for once")
        print("  and can still make again.")
        print()
        print("  reach >= 2 (already generalised):  %d" % len(proven))
        for e in proven:
            print("    %-32s %s" % (e["name"], ", ".join(e["claims"])))
            print("        %s" % e["rule"])
        print()
        print("  reach 1 (worked once, unproven):   %d"
              % (len(un) - len(proven)))
        for e in un:
            if e["reach"] < 2:
                print("    %-32s %s" % (e["name"], ", ".join(e["claims"])))
        bad = mechanisation_is_real(reg)
        if bad:
            print()
            print("  CLAIMED MECHANISED BUT NOT PRESENT:")
            for name, target, why in bad:
                print("    %-32s %s: %s" % (name, target, why))
            return 1
    elif cmd == "loose":
        ls = loose(reg=reg)
        print("READS AS ABANDONED, NOT IN THE REGISTER  (%d)" % len(ls))
        print("  A prompt for a human, not a detection. A proposal that died")
        print("  quietly and left no word behind is invisible here.")
        print()
        for d in ls:
            print("  %-52s %s" % (d["file"], d["word"]))
            print("      %s" % d["line"])
    else:
        print("usage: graveyard.py [deaths | screens | todo | loose]")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
