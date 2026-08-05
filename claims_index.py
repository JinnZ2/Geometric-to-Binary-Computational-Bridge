#!/usr/bin/env python3
"""
claims_index.py  --  which claim IDs exist, and what can make each one fail.

    python claims_index.py              # the index, by evidence class
    python claims_index.py prose        # claims nothing can fail on
    python claims_index.py show FCL-4   # one claim, every site
    python claims_index.py families     # counts per prefix

Stdlib only. Derived by scanning -- there is no hand-maintained list here to
drift out of date, which is the whole point.

=====================================================================
WHY DERIVED, AND WHY BY EVIDENCE CLASS
=====================================================================
This started as bookkeeping: PRINCIPLES.json cites instance tags like
"KEA-7", nothing checked that they pointed at anything, and 13 of 36 turned
out to be shorthand invented at writing time that resolves nowhere.

The obvious fix -- a hand-written register mapping tags to claims -- would
have been a second authority over the same facts, which is P-DUPLICATE-
AUTHORITY, one of the shapes this repo already catalogued. So the index is
scanned instead.

Inferring "where is this claim DEFINED" from prose formatting was tried and
abandoned: it marked VAC-1 as defined inside a docstring that merely mentions
it, and missed KEA-7 entirely. A heuristic over free text is exactly the kind
of thing that looks reasonable and cannot be falsified.

So the classification is not about where a claim is written. It is about what
can make it FAIL, which is the only question this archive has ever cared
about:

    FALSIFIER   a runnable report calls check("ID: ...") and exits nonzero
    NAMED_IN_TEST
                a file under tests/ mentions it. NAMING IS NOT ASSERTING --
                this detects that a suite knows the id exists, which is
                weaker than a test that can fail on it, and the class is
                named for what it actually measures rather than what would
                be nicer to claim.
    REGISTER    a claim-register table row carries it
    PROSE       it is written down, and nothing executes against it

PROSE is not an error. Some claims are bench work nobody has run, and some
are definitions. It is a state worth being able to list, which is what
`claims_index.py prose` is for.

One artifact worth knowing about: this scanner reads the whole tree including
its own tests, so an id written as a test fixture appears in the index as a
real claim. tests/test_claims_index.py therefore builds its fake ids at
runtime rather than writing them as literals. A tool that scans everything
scans itself.
"""
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

ID = r'[A-Z][A-Z0-9]{1,7}-[0-9]{1,2}[a-z]?'
ID_RX = re.compile(r'(?<![\w-])(%s)(?![\w-])' % ID)

# Prefixes that match the ID shape but are not claims of this archive.
NOT_CLAIMS = {"CC0", "CC", "BY", "SA", "ND", "ISO", "UTF", "RFC", "IEEE",
              "ASTM", "SI", "MIT", "GPL", "LGPL", "SP", "NIST", "ANSI",
              "JIS", "DIN", "EN", "IEC", "MIL", "STD", "PEP", "RGB", "SHA",
              "MD", "AES", "RSA", "USB", "I2C", "SPI", "TTL", "CMOS"}

FALSIFIER_RX = re.compile(r'check\(\s*["\'](%s)\b' % ID)
REGISTER_RX = re.compile(r'^\s*\|\s*(%s)\s*\|\s*\S' % ID, re.M)

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache",
             "scratchpad", "legacy"}

# This file and its suite talk ABOUT claim ids, so their fixtures would be
# indexed as claims. A scanner that reads the whole tree reads itself: the
# first version of the suite wrote "FNV-1a" as a literal and thereby created
# an FNV claim family. Excluded, and only these two -- CLAUDE.md and
# PRINCIPLES.json also discuss ids, but they discuss REAL ones.
SKIP_FILES = {"claims_index.py", os.path.join("tests", "test_claims_index.py")}
EXT = (".py", ".md", ".json", ".txt", ".ino", ".c", ".h", ".yaml", ".yml")

CLASSES = ("FALSIFIER", "NAMED_IN_TEST", "REGISTER", "PROSE")


def _files(root=ROOT):
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            if not n.endswith(EXT):
                continue
            rel = os.path.relpath(os.path.join(base, n), root)
            if rel not in SKIP_FILES:
                yield rel


def scan(root=ROOT):
    """claim id -> {class -> sorted files}. One pass over the tree."""
    sites = collections.defaultdict(lambda: collections.defaultdict(set))
    for rel in _files(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8",
                      errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        is_test = rel.startswith("tests" + os.sep) or "test_" in os.path.basename(rel)
        falsifiers = set(FALSIFIER_RX.findall(text))
        registers = set(REGISTER_RX.findall(text))
        for cid in set(ID_RX.findall(text)):
            if cid.split("-")[0] in NOT_CLAIMS:
                continue
            if cid in falsifiers:
                sites[cid]["FALSIFIER"].add(rel)
            if cid in registers:
                sites[cid]["REGISTER"].add(rel)
            if is_test:
                sites[cid]["NAMED_IN_TEST"].add(rel)
            sites[cid]["PROSE"].add(rel)
    full = {k: {c: sorted(v) for c, v in d.items()} for k, d in sites.items()}
    fams = claim_families(full)
    return {k: v for k, v in full.items() if k.split("-")[0] in fams}


def claim_families(index):
    """Prefixes with at least one member something can fail on.

    Derived, not maintained. A denylist of licenses and standards would need
    extending every time a new one appeared, and would be wrong silently in
    between; this rule says a family is a claim family when this archive has
    pointed executable machinery at some member of it. FNV-1a, AGPL-3 and FR-4
    drop out because nothing tests them -- they are a hash, a licence and a
    PCB laminate.
    """
    fams = set()
    for cid, d in index.items():
        if d.get("FALSIFIER") or d.get("NAMED_IN_TEST"):
            fams.add(cid.split("-")[0])
    return fams


def evidence(cid, index):
    """The strongest class of thing that can make this claim fail."""
    d = index.get(cid)
    if not d:
        return None
    for c in CLASSES:
        if d.get(c):
            return c
    return "PROSE"


def index_by_class(index):
    out = collections.defaultdict(list)
    for cid in index:
        out[evidence(cid, index)].append(cid)
    return {c: sorted(out[c]) for c in CLASSES if out[c]}


def resolve(tag, index):
    """Does this tag name a real claim, and what backs it?"""
    if tag not in index:
        return {"tag": tag, "known": False, "evidence": None, "files": []}
    return {"tag": tag, "known": True, "evidence": evidence(tag, index),
            "files": index[tag].get(evidence(tag, index), [])}


def families(index):
    c = collections.Counter(k.split("-")[0] for k in index)
    return c.most_common()


# ---------------------------------------------------------------------
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "index"
    idx = scan()
    by = index_by_class(idx)
    if cmd == "index":
        print("CLAIM INDEX  --  %d ids, scanned not maintained" % len(idx))
        print("  classified by what can make each one FAIL, strongest first")
        print()
        for c in CLASSES:
            ids = by.get(c, [])
            print("  %-10s %3d   %s" % (c, len(ids), ", ".join(ids[:12])
                                        + (" ..." if len(ids) > 12 else "")))
        print()
        n_exec = sum(len(by.get(c, [])) for c in ("FALSIFIER", "NAMED_IN_TEST"))
        print("  %d of %d claims have something executable pointed at them."
              % (n_exec, len(idx)))
        print("  python claims_index.py prose   # the ones that do not")
    elif cmd == "prose":
        ids = by.get("PROSE", [])
        print("WRITTEN DOWN, NOTHING EXECUTES AGAINST IT  (%d)" % len(ids))
        print("  Not an error. Bench work nobody has run, and definitions,")
        print("  live here legitimately. It is a state worth being able to see.")
        print()
        for cid in ids:
            print("  %-10s %s" % (cid, ", ".join(idx[cid]["PROSE"][:3])))
    elif cmd == "show" and len(argv) > 2:
        cid = argv[2]
        if cid not in idx:
            print("no such claim id: %s" % cid)
            return 1
        print("%s  --  %s" % (cid, evidence(cid, idx)))
        for c in CLASSES:
            for f in idx[cid].get(c, []):
                print("  %-10s %s" % (c, f))
    elif cmd == "families":
        for fam, n in families(idx):
            print("  %-8s %3d" % (fam, n))
    else:
        print("usage: claims_index.py [index | prose | show ID | families]")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
