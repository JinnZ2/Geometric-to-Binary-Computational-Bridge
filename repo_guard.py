#!/usr/bin/env python3
"""
repo_guard.py -- CC0, stdlib only, phone-buildable, no deps.

STAGE 5.5 OF THE SCAFFOLD: THE NULL STAGE.

Across the archive, five failure classes account for every fatal finding.
Three are mechanically checkable BEFORE a file enters the repo:

  1. NULL HARNESS   does the result survive replacing structure with noise?
                    (killed: the 17-lens isomorphism, the vacuum g_eff
                     assertions, topological attention's run())
  2. SYMMETRY VETO  does the material permit the mechanism at all?
                    (would have caught 9 instances across 6 files, free)
  3. REACH CHECK    is the claimed signal above the instrument floor?
                    (would have caught the 11-order Hall gap, the 500x
                     Er/diamagnetism swamp, the RBS 20-200x shortfall)
  4. COLLISIONS     do two artifacts carry the same content, or one name two
                    definitions? (P-DUPLICATE-AUTHORITY's own detector is
                    "hash the bodies", and it was mechanised by nothing until
                    a scan found two byte-identical document pairs nobody had
                    recorded: PROJECTS.md/PROJECTS2.md and Silicon/GIES.md /
                    GEIS/GEIS_organization.md)
  5. PROSE          does the repo's own README survive the questions it asks
                    of the physics? An external audit of the published README
                    found four things nothing here pointed at: a licence that
                    said CC0 in the header and MIT in LICENSE; a speedup table
                    whose rows did not multiply to its "Combined" line and
                    whose numbers no benchmark had produced; quick-start
                    commands naming directories that do not exist and a CLI
                    with no entry point; and model output addressed to the
                    author ("your projects") left on the crawler surface.
                    Five checks, each a REPORT with file and line; the run
                    fails on any hit and nothing is auto-fixed:
                      licence string mismatch across LICENSE / CITATION.cff /
                        metadata.json / README, and any licence identifier in
                        any tracked file that is not the one LICENSE declares
                        (.fieldlink.json sibling consents exempt; its own is not)
                      a numeric speedup claim in a .md with no benchmark
                        reference within three lines
                      a shell command in a .md fence whose first path
                        argument does not exist in the tree
                      second-person address to the author in a .md
                      a filename containing a space

The other two -- circular targets and unit errors -- need a human. Checklist
for those at the bottom, and ``human_checklist()`` prints it.

TWO CORRECTIONS TO THE TOOL AS FIRST DRAFTED
--------------------------------------------
1. ``null_harness`` could return SURVIVES for a claim that does not hold. If
   the real metric fails its own criterion and the nulls fail too, the worst
   null pass rate is 0 and the old verdict was SURVIVES. A claim that is simply
   false is not a claim that survived a null test. The verdict is now gated on
   ``real_passes`` and returns CLAIM_FAILS in that case.

2. ``reach`` raised a bare ``KeyError`` for an unknown instrument. It now names
   the available floors, because the point of the tool is to be usable without
   reading it.

WHAT THE FLOORS ARE FOR
-----------------------
Every entry is a number this archive had to derive the hard way. The piezo
figure is the one that corrects an earlier pass of my own: the gauge factor is
``pi_l * E``, and ``pi_l = 71.8e-11 Pa^-1`` is the <110> LONGITUDINAL
coefficient, so it pairs with ``E<110> = 169 GPa``, not ``E<100> = 130 GPa``.
That gives GF = 121, not 93, and dR/R = 12% at 0.1% strain rather than 9%.
"""

import math
import random

__all__ = [
    "null_harness", "report", "VETO", "veto", "veto_report",
    "FLOOR", "reach", "reach_report", "CHECKLIST", "human_checklist",
    "duplicate_bodies", "screen_collisions", "collision_report",
    "licence_strings", "licence_mismatch", "licence_scan", "licence_ref", "speedup_claims", "shell_commands",
    "second_person", "spaced_filenames", "prose_audit", "prose_report",
    "demo", "main",
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache",
             "scratchpad", "legacy", "evidence"}

# =====================================================================
# 1. NULL HARNESS
# =====================================================================


def null_harness(metric, real, nulls, passes, name="claim", trials=200):
    """Does the criterion still pass when the structure is removed?

    metric  : callable(obj) -> float
    real    : the structured object your claim is about
    nulls   : list of callables() -> object with the STRUCTURE REMOVED but the
              same shape/type (random, shuffled, degenerate)
    passes  : callable(float) -> bool, your stated success criterion

    Verdict:
      CLAIM_FAILS  the real object does not meet its own criterion
      ARTIFACT     >50% of null draws meet it too
      SUSPECT      >10%
      SURVIVES     the criterion discriminates
    """
    if not nulls:
        raise ValueError("need at least one null generator")
    if trials < 1:
        raise ValueError("need at least one trial")
    m_real = metric(real)
    real_passes = bool(passes(m_real))
    rows = []
    for i, gen in enumerate(nulls):
        vals = [metric(gen()) for _ in range(trials)]
        frac = sum(1 for v in vals if passes(v)) / len(vals)
        vals.sort()
        rows.append({"null": getattr(gen, "__name__", "null%d" % i),
                     "median": vals[len(vals) // 2],
                     "frac_passing": frac})
    worst = max(r["frac_passing"] for r in rows)
    if not real_passes:
        verdict = "CLAIM_FAILS"
    elif worst > 0.5:
        verdict = "ARTIFACT"
    elif worst > 0.1:
        verdict = "SUSPECT"
    else:
        verdict = "SURVIVES"
    return {"name": name, "real": m_real, "real_passes": real_passes,
            "nulls": rows, "worst_null_pass_rate": worst, "verdict": verdict}


def report(res):
    print("NULL HARNESS: %s" % res["name"])
    print("  real metric = %.6f   passes = %s" % (res["real"], res["real_passes"]))
    for r in res["nulls"]:
        print("    %-24s median %12.6f   passes %5.1f%% of the time"
              % (r["null"], r["median"], 100 * r["frac_passing"]))
    print("  VERDICT: %s" % res["verdict"])
    if res["verdict"] == "CLAIM_FAILS":
        print("  -> the real object does not meet its own criterion.")
        print("     nothing about the nulls matters until that is fixed.")
    elif res["verdict"] != "SURVIVES":
        print("  -> the criterion is met by inputs with no structure.")
        print("     the claim is about the arithmetic, not the subject.")
    print()


# =====================================================================
# 2. SYMMETRY / MATERIAL VETO
# =====================================================================

VETO = {
    "silicon": {
        "_facts": "diamond cubic Fd-3m; point group Oh (CENTROSYMMETRIC); "
                  "site symmetry Td; chi = -4e-6 (diamagnetic); "
                  "92.2% Si-28 with I=0; bonding electrons paired",
        "piezoelectric": ("ZERO by inversion symmetry",
                          "electrostriction (even order) IS allowed"),
        "inverse piezo": ("ZERO by inversion symmetry",
                          "photothermal + deformation-potential stress"),
        "pockels": ("ZERO -- chi(2) = 0 in Oh", "plasma dispersion; Kerr chi(3)"),
        "chi2": ("ZERO -- chi(2) = 0 in Oh", "Kerr chi(3), n2 ~ 4.5e-18 m^2/W"),
        "second harmonic": ("ZERO -- forbidden in Oh", "third harmonic (odd order)"),
        "magnetostriction": ("negligible -- diamagnetic",
                             "strain via piezoresistance readout"),
        "magneto-optic": ("negligible Verdet const",
                          "no monolithic Si isolator exists"),
        "faraday": ("negligible Verdet const", "polarization-resolved Raman"),
        "exchange": ("no magnetic order", "elastic coupling via stiffness tensor"),
        "esr": ("no unpaired spins in perfect Si",
                "reads DEFECTS/dopants, not lattice"),
        "spin coherence": ("no intrinsic spin", "P donors in enriched 28Si, <4 K"),
        "thermal anisotropy": ("ZERO -- cubic symmetry, k_ij = k*delta_ij",
                               "none; it is isotropic"),
        "conductivity anisotropy": ("ZERO -- cubic symmetry", "none"),
    },
}


def veto(material, text):
    """Grep a claim or abstract for mechanisms the material forbids."""
    tbl = VETO.get(str(material).lower())
    if not tbl:
        return [("?", "no veto table for %r" % material, "")]
    low = str(text).lower()
    return [(k, v[0], v[1]) for k, v in tbl.items()
            if not k.startswith("_") and k in low]


def veto_report(material, text):
    key = str(material).lower()
    print("SYMMETRY VETO: %s" % material)
    if key in VETO:
        print("  %s" % VETO[key]["_facts"])
    hits = veto(material, text)
    if not hits:
        print("  no forbidden mechanism named. (absence of a hit is not a pass.)")
    for k, why, alt in hits:
        print("  [X] %-24s %s" % (k, why))
        if alt:
            print("      allowed instead: %s" % alt)
    print()
    return hits


# =====================================================================
# 3. REACH CHECK -- signal vs instrument floor
# =====================================================================

FLOOR = {   # (value, unit, note)
    "hall sensor": (2e-5, "T", "A1324 class, ~0.2 G noise"),
    "squid moment": (1e-11, "A.m^2", "commercial MPMS"),
    "raman strain": (1e-4, "strain", "520.7 cm^-1 shift, ~0.02 cm^-1"),
    "rbs areal": (1e13, "cm^-2", "heavy-in-light"),
    "piezoresistive": (1e-5, "dR/R", "4-point probe; GF~121 p-Si <110>"),
    "landauer 300K": (2.87e-21, "J", "kT*ln2; floor for ONE bit erase"),
    "kT 300K": (0.02585, "eV", "thermal energy"),
    "debye-waller theta": (1.9, "deg", "Si bond-angle RMS at 300 K"),
}


#: Case-insensitive lookup. Built from FLOOR rather than duplicating it, so a
#: new floor cannot be reachable under one spelling and not the other.
_FLOOR_LC = {k.lower(): k for k in FLOOR}


def reach(signal, instrument):
    key = _FLOOR_LC.get(str(instrument).lower())
    if key is None:
        raise KeyError("unknown instrument %r; known floors: %s"
                       % (instrument, ", ".join(sorted(FLOOR))))
    if signal < 0:
        raise ValueError("signal must be non-negative")
    f, unit, note = FLOOR[key]
    r = signal / f
    return {"signal": signal, "floor": f, "unit": unit, "ratio": r, "note": note,
            "verdict": "DETECTABLE" if r >= 3 else
                       "MARGINAL" if r >= 1 else "BELOW FLOOR"}


def reach_report(signal, instrument, label=""):
    d = reach(signal, instrument)
    print("REACH: %s  vs  %s" % (label or "signal", instrument))
    print("  signal %.3e %s   floor %.3e %s   ratio %.2e   %s"
          % (d["signal"], d["unit"], d["floor"], d["unit"], d["ratio"], d["note"]))
    print("  VERDICT: %s" % d["verdict"])
    if 0 < d["ratio"] < 1:
        print("  -> short by %.1f orders of magnitude." % (-math.log10(d["ratio"])))
    print()
    return d



# =====================================================================
# 4. COLLISIONS
# =====================================================================
#
# Two artifacts carrying the same content, or one name carrying two
# definitions. Neither is a physics error and both are cheap to detect, which
# is why they survive: nothing was looking. P-DUPLICATE-AUTHORITY has been
# ESTABLISHED since it was written with `mechanised_by: None` and a detector
# that reads, in full, "Hash the bodies. Then ask which one the code imports."
#
# `legacy/` and `evidence/` are skipped on purpose. A file kept for provenance
# is SUPPOSED to duplicate the thing that replaced it -- that is what it is
# for -- so flagging it would train a reader to ignore this stage.


def duplicate_bodies(root=".", exts=(".md", ".py", ".json", ".txt"),
                     max_bytes=3_000_000):
    """Files with byte-identical content. Returns [[path, path, ...], ...].

    Identity, not similarity: two files that merely say the same thing are an
    editorial question, and this stage only reports what is decidable.
    """
    import hashlib
    import os
    seen = {}
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            if not n.endswith(exts):
                continue
            path = os.path.join(base, n)
            try:
                if not 0 < os.path.getsize(path) <= max_bytes:
                    continue
                with open(path, "rb") as fh:
                    digest = hashlib.md5(fh.read()).hexdigest()
            except OSError:
                continue
            seen.setdefault(digest, []).append(os.path.relpath(path, root))
    return sorted((sorted(v) for v in seen.values() if len(v) > 1))


def screen_collisions(register=None):
    """Screen names carrying more than one definition in the claim register.

    A screen is meant to be one reusable check. Two definitions under one name
    means the reach count -- how many independent claims it has already killed,
    which is the whole basis for ranking them -- is summing two different
    things. `measure-the-null` carried two rule texts and two applies_when
    clauses across five claims before this was written.

    Returns [(name, [ (rule, applies_when, mechanised_by), ... ]), ...].
    """
    import json
    import os
    path = register or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "CLAIMS_REGISTER.json")
    try:
        with open(path, encoding="utf-8") as fh:
            claims = json.load(fh).get("claims", [])
    except (OSError, ValueError):
        return []
    variants = {}
    for c in claims:
        s = (c.get("salvage") or {}).get("screen")
        if not s:
            continue
        variants.setdefault(s["name"], set()).add(
            (s["rule"], s.get("applies_when"), s.get("mechanised_by")))
    return sorted((n, sorted(v)) for n, v in variants.items() if len(v) > 1)


def collision_report(root=".", register=None):
    """Print stage 4 and return the number of collisions found."""
    dups = duplicate_bodies(root)
    screens = screen_collisions(register)
    print("  byte-identical file bodies        %d" % len(dups))
    for group in dups:
        print("      %s" % "  ==  ".join(group))
    print("  screen names with two definitions %d" % len(screens))
    for name, vs in screens:
        print("      %s  (%d definitions)" % (name, len(vs)))
        for rule, _aw, _m in vs:
            print("          %s" % rule[:66])
    n = len(dups) + len(screens)
    print("  %s" % ("no collisions" if not n else
                    "%d collision group(s) -- name a canonical one or merge "
                    "the definitions" % n))
    return n


# =====================================================================
# 5. PROSE -- the README is a claim surface like any other
# =====================================================================

import json
import os
import re
import shlex
import shutil

MD_SKIP = SKIP_DIRS | {"atlas"}      # atlas/remote is mounted sibling content, not ours

_LICENCE_ALIASES = {
    "CC0": "CC0-1.0", "CC0 1.0": "CC0-1.0", "CC0 1.0 UNIVERSAL": "CC0-1.0", "CC0-1.0": "CC0-1.0",
    "MIT LICENSE": "MIT", "MIT": "MIT",
    "CC-BY-4.0": "CC-BY-4.0", "CC BY 4.0": "CC-BY-4.0", "CC-BY 4.0": "CC-BY-4.0",
    "ATTRIBUTION 4.0 INTERNATIONAL": "CC-BY-4.0",
    "APACHE LICENSE": "Apache-2.0", "APACHE-2.0": "Apache-2.0",
}
# every identifier this scan knows. CC variants fold NC/SA/ND and the version into one token.
_LICENCE_TOKEN = re.compile(
    r"\b(CC0(?:[- ]1\.0)?(?: Universal)?|MIT License|MIT|"
    r"CC[- ]?BY(?:[- ](?:NC|SA|ND))*(?:[- ]\d\.\d)?|"
    r"Attribution 4\.0 International|Apache(?: License)?(?:[- ]2\.0)?|"
    r"[AL]?GPL-?v?[23](?:\.0)?|BSD-[23]-Clause|PDDL(?:-1\.0)?|ODbL(?:-1\.0)?)\b")
# an identifier counts when the line is DECLARING a licence (it names the word, or the line is
# nothing but the identifier, as a docstring footer is), so "MIT/Ju lab", a denylist of tokens
# and "`AGPL-3` drops out" stay silent.
_DECLARES = re.compile(r"licen[cs]e|released under|public domain|copyright|spdx", re.I)
_ONLY_TOKEN = re.compile(r"^[\s*_`#>/\-]*(?P<tok>[A-Za-z0-9 .\-]+?)[\s*_`.]*$")
# files the scan must not read as declarations: the guard and its tests name every identifier
# in order to detect them, and the snapshot is the guard's own output
_LICENCE_SELF = {"repo_guard.py", "tests/test_repo_guard.py", "PROSE_AUDIT.md"}
# third-party dependency manifests declare OTHER projects' licences
_LOCKFILES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock")
_TEXT_EXT = (".md", ".py", ".json", ".txt", ".cff", ".toml", ".yaml", ".yml", ".js", ".jsx",
             ".mjs", ".sh", ".ino", ".c", ".h", ".html", ".css", ".rst", ".cfg", ".ini")


def _norm_licence(tok):
    t = re.sub(r"\s+", " ", tok.strip()).upper().replace("CC BY", "CC-BY").replace("CC-BY ", "CC-BY-")
    if t in _LICENCE_ALIASES:
        return _LICENCE_ALIASES[t]
    if t.startswith("CC-BY") or t.startswith("CCBY"):
        return t.replace("CCBY", "CC-BY").replace(" ", "-")
    return _LICENCE_ALIASES.get(t, tok.strip())


def _tracked_files(root):
    """git-tracked files when a checkout is present, else a walk. legacy/ and evidence/ are
    skipped for the same reason stage 4 skips them: kept as received, they carry the headers
    they arrived with, and rewriting those would destroy the provenance they exist for."""
    import subprocess
    files = None
    if os.path.isdir(os.path.join(root, ".git")):
        try:
            out = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True,
                                 check=True, timeout=30).stdout
            files = [f for f in out.decode("utf-8", "replace").split("\0") if f]
        except (OSError, subprocess.SubprocessError):
            files = None
    if files is None:
        files = []
        for base, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for n in names:
                files.append(os.path.relpath(os.path.join(base, n), root))
    keep = []
    for f in sorted(files):
        parts = f.replace("\\", "/").split("/")
        if any(p in ("legacy", "evidence") or p in SKIP_DIRS for p in parts[:-1]):
            continue
        if f.lower().endswith(_TEXT_EXT) or parts[-1] in ("LICENSE", "LICENCE", "COPYING"):
            keep.append(f)
    return keep


# The licence-ref marker: prose that names ANOTHER project's licence, or records a past
# state of this repo's, is a different object from this repo's declaration. It is not
# silenced; it is marked, and the marker must say whose licence it is:
#     <!-- licence-ref: external, GEV data pack -->
#     <!-- licence-ref: historical, REVIEW.md audit of the pre-CC0 state -->
# In JSON, the same text inside a string or a "licence_ref" value on the line works.
# A marker without the attribution, or an "external" marker on a line that says
# "this repo", is a defect and still fails the run.
_LICENCE_REF = re.compile(r"licen[cs]e[-_]ref\W{0,4}(external|historical)\s*(?:,\s*([^\"<>\n]*?))?\s*(?:-->|\"|$)", re.I)
_THIS_REPO = re.compile(r"\bthis (?:repo|repository)\b", re.I)
_CLAUSE_SPLIT = re.compile(r"[;.]\s|\s/\s|\s(?:while|whereas|but)\s", re.I)


def licence_ref(ln, canonical="CC0-1.0"):
    """(kind, attribution, defect) for a marked line; (None, None, None) for an unmarked one.

    A marker marked `external` is a defect when the line attributes a NON-canonical identifier
    to this repo: the clause naming "this repo" carries a licence id that is not the canonical
    one and no canonical id beside it. "MIT (their code) / CC0-1.0 (this repo)" is fine;
    "this repo is MIT" under an external marker is the defect the order says the guard must
    still catch. Clauses split on `; `, `. `, ` / ` and while/whereas/but."""
    m = _LICENCE_REF.search(ln)
    if not m:
        return None, None, None
    kind = m.group(1).lower()
    who = (m.group(2) or "").strip()
    if not who:
        return kind, who, "licence-ref marker names nobody: say whose licence it is"
    if kind == "external":
        body = ln[:m.start()] + " " + ln[m.end():]
        for clause in _CLAUSE_SPLIT.split(body):
            if not _THIS_REPO.search(clause):
                continue
            ids = {_norm_licence(t.group(1)) for t in _LICENCE_TOKEN.finditer(clause)}
            if ids and canonical not in ids:
                return kind, who, "marked external but the line attributes %s to this repo" % "/".join(sorted(ids))
    return kind, who, None


def _fieldlink_sibling_line(rel, ln):
    """In .fieldlink.json the consent entries under sources[] describe SIBLING repos and are
    exempt; the top-level consent (4-space indent) is this repo's own and is not."""
    return rel == ".fieldlink.json" and '"consent"' in ln and (len(ln) - len(ln.lstrip(" "))) > 4


def licence_scan(root=".", canonical=None, marked=None):
    """[(file, line, id, text)] for every UNMARKED licence identifier in a tracked file that is
    not the canonical one, plus marker defects. canonical defaults to what LICENSE declares.
    Pass a dict as `marked` to receive the marked lines: {"external": [...], "historical": [...]}."""
    root = os.path.abspath(root)
    if canonical is None:
        lic = licence_strings(root).get("LICENSE")
        canonical = lic[1] if lic else "CC0-1.0"
    hits = []
    for rel in _tracked_files(root):
        if rel in _LICENCE_SELF or os.path.basename(rel) in _LOCKFILES:
            continue
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError:
            continue
        for i, ln in enumerate(lines):
            for m in _LICENCE_TOKEN.finditer(ln):
                tok = m.group(1)
                only = _ONLY_TOKEN.match(ln)
                whole_line = bool(only) and _norm_licence(only.group("tok")) == _norm_licence(tok)
                if not (_DECLARES.search(ln) or whole_line):
                    continue
                lid = _norm_licence(tok)
                if lid == canonical:
                    continue
                if _fieldlink_sibling_line(rel, ln):
                    continue
                kind, who, defect = licence_ref(ln, canonical)
                if kind and not defect:
                    if marked is not None:
                        marked.setdefault(kind, []).append((rel, i + 1, lid, who, ln.strip()[:80]))
                    break
                if defect:
                    hits.append((rel, i + 1, lid, "MARKER DEFECT: " + defect))
                    break
                hits.append((rel, i + 1, lid, ln.strip()[:80]))
                break
    return hits


def _md_files(root):
    """Every .md outside MD_SKIP, except the guard's own snapshot, which quotes every hit."""
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in MD_SKIP)
        for n in sorted(names):
            if n.endswith(".md") and not (n == "PROSE_AUDIT.md" and os.path.abspath(base) == os.path.abspath(root)):
                yield os.path.join(base, n)


def licence_strings(root="."):
    """The licence each of the four surfaces declares. Returns {file: (line, id) | None}."""
    out = {}
    p = os.path.join(root, "LICENSE")
    out["LICENSE"] = None
    if os.path.isfile(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for i, ln in enumerate(fh, 1):
                m = _LICENCE_TOKEN.search(ln)
                if m:
                    out["LICENSE"] = (i, _norm_licence(m.group(1)))
                    break
    p = os.path.join(root, "CITATION.cff")
    out["CITATION.cff"] = None
    if os.path.isfile(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for i, ln in enumerate(fh, 1):
                m = re.match(r"\s*license\s*:\s*[\"']?([^\"'\s]+)", ln)
                if m:
                    out["CITATION.cff"] = (i, _norm_licence(m.group(1)))
                    break
    p = os.path.join(root, "metadata.json")
    out["metadata.json"] = None
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            if isinstance(d, dict) and d.get("license"):
                with open(p, encoding="utf-8") as fh:
                    ln_no = next((i for i, ln in enumerate(fh, 1) if '"license"' in ln), 0)
                out["metadata.json"] = (ln_no, _norm_licence(str(d["license"])))
        except (OSError, ValueError):
            pass
    p = os.path.join(root, "README.md")
    out["README.md"] = None
    if os.path.isfile(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")
        # the License section if there is one, else the first licence token anywhere
        start = next((i for i, ln in enumerate(lines) if re.match(r"#+\s*licen[cs]e\b", ln, re.I)), 0)
        for i in range(start, len(lines)):
            m = _LICENCE_TOKEN.search(lines[i])
            if m:
                out["README.md"] = (i + 1, _norm_licence(m.group(1)))
                break
    return out


def licence_mismatch(root="."):
    """[(file, line, id)] for every surface when they do not all agree; [] when they do."""
    found = licence_strings(root)
    ids = {v[1] for v in found.values() if v}
    if len(ids) <= 1:
        return []
    return [(f, v[0], v[1]) if v else (f, 0, "(none)") for f, v in found.items()]


# an `Nx` / `N-Mx` / `N×` token that is a multiplier, not a product (`3 × 5`, `$15 × 2`)
_SPEEDUP = re.compile(
    r"(?<![\w.$])\d+(?:[.,]\d+)?(?:\s*[-\u2013]\s*\d+(?:[.,]\d+)?)?\s?[x\u00d7](?!\s*[\d(])(?![\w])")
# ...on a line that is talking about performance
_PERF = re.compile(r"speed|faster|slower|perf|throughput|accelerat|efficien|improvement|"
                   r"reduction|gain|advantage|compression|better|cost|overhead", re.I)
_BENCH = re.compile(r"benchmark", re.I)
# A claim that carries its own status is not an unsupported claim. The marker convention
# (PROSE_AUDIT.md, "claim-status markers"): `[refuted: <why, claim id, file>]` for a figure
# something in the tree kills, `[unmeasured]` / `[unmeasured: <what is missing>]` for one nothing
# in the tree produced, `[unmeasured operand: <which>]` for arithmetic on such a figure, and
# `[refutation of <id>]` for a line that derives a number in order to kill it. `[refuted]` with
# no reason is a defect: a refutation names what did the killing.
_CLAIM_STATUS = re.compile(r"\[(refuted|unmeasured(?: operand)?|refutation of)\b\s*:?\s*([^\]]*)\]", re.I)


def claim_status(ln):
    """(kind, body, defect) for a status-marked line; (None, None, None) for an unmarked one."""
    m = _CLAIM_STATUS.search(ln)
    if not m:
        return None, None, None
    kind, body = m.group(1).lower(), m.group(2).strip()
    if kind in ("refuted", "refutation of") and not body:
        return kind, body, "a refuted marker names what refuted it"
    return kind, body, None


def speedup_claims(root=".", window=3, marked=None):
    """[(file, line, text)] for a numeric `Nx` performance claim with no 'benchmark' within `window`
    lines and no claim-status marker on the line. Pass a dict as `marked` to receive the marked
    lines by kind; a defective marker is a hit."""
    hits = []
    for path in _md_files(root):
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")
        for i, ln in enumerate(lines):
            if not (_SPEEDUP.search(ln) and _PERF.search(ln)):
                continue
            kind, body, defect = claim_status(ln)
            if kind and not defect:
                if marked is not None:
                    marked.setdefault(kind, []).append((os.path.relpath(path, root), i + 1, body[:60], ln.strip()[:80]))
                continue
            if defect:
                hits.append((os.path.relpath(path, root), i + 1, "MARKER DEFECT: " + defect + " -- " + ln.strip()[:60]))
                continue
            lo, hi = max(0, i - window), min(len(lines), i + window + 1)
            if any(_BENCH.search(l2) for l2 in lines[lo:hi]):
                continue
            hits.append((os.path.relpath(path, root), i + 1, ln.strip()[:80]))
    return hits


_FENCE = re.compile(r"^\s*```\s*(\w*)")
_SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh"}
# tools whose arguments are not paths in this tree, or are checked specially. Real tools that
# may be absent on the machine running the guard are listed so the check is about the TREE.
_KNOWN = {"python", "python3", "cd", "pip", "pip3", "npm", "npx", "node", "make", "git", "cat",
          "ls", "echo", "export", "source", "curl", "wget", "head", "tail", "grep", "sed",
          "awk", "column", "for", "do", "done", "if", "then", "fi", "else", "pytest", "ruff",
          "rm", "mkdir", "cp", "mv", "touch", "wc", "sort", "uniq", "tr", "xargs", "find",
          "diff", "chmod", "sudo", "apt", "apt-get", "brew", "docker", "sh", "bash", "time",
          "watch", "openscad", "kicad", "raspi-config", "nvm", "printf", "true", "false",
          "exit", "set", "unset", "env", "which", "less", "more", "tee", "date", "sleep",
          "jq", "conda", "mpirun", "vasp_std", "arduino-cli", "picotool", "ssh", "scp",
          "rsync", "tar", "unzip", "zip", "gcc", "cc", "clang", "cmake", "ninja"}
_CREATES = {"mkdir", "touch", "tee", "rm", "cp", "mv", "rsync", "scp", "tar", "unzip", "zip"}
_PLACEHOLDER = re.compile(r"[<>{}$*?\[\]|]|^https?://|^-|^\.\.\.$")
_IDENT = re.compile(r"^[a-z][\w.+-]*$")
_PY_STATEMENT = {"import", "from", "class", "def", "return", "print", "if", "for", "while",
                 "with", "try", "except", "raise", "assert", "pass", "yield", "lambda",
                 "and", "or", "not", "in", "is", "the", "a", "an", "you", "we", "it", "this"}


def _looks_like_path(tok):
    return ("/" in tok or "." in tok) and not _PLACEHOLDER.search(tok)


def _exists(tok, *bases):
    """A path counts as present if it resolves from ANY base: the block's tracked cwd, the repo
    root (a command list is a menu, not a script) or the .md file's own directory (a folder's
    README assumes you are standing in it). Absolute paths are outside the tree and not judged."""
    if os.path.isabs(tok):
        return True
    return any(os.path.exists(os.path.normpath(os.path.join(b, tok))) for b in bases if b)


def _module_present(name, *bases):
    rel = name.replace(".", os.sep)
    if _exists(rel + ".py", *bases) or _exists(rel, *bases):
        return True
    import sys                              # stdlib modules are not tree claims; nothing else is exempt
    top = name.split(".")[0]
    return top in getattr(sys, "stdlib_module_names", ()) or top in ("pip", "pytest", "ruff")


def _shell_lines(lines):
    """Yield (line_no, text) for lines inside shell fences, with `\\` continuations joined and
    heredoc bodies dropped. Resets on every fence so cwd tracking starts fresh per block."""
    in_shell, heredoc, buf, buf_no = False, None, "", 0
    for i, raw in enumerate(lines):
        m = _FENCE.match(raw)
        if m:
            lang = m.group(1).lower()
            in_shell = (not in_shell) and lang in _SHELL_LANGS
            heredoc, buf = None, ""
            yield (i + 1, None)             # block boundary
            continue
        if not in_shell:
            continue
        if heredoc is not None:
            if raw.strip() == heredoc:
                heredoc = None
            continue
        ln = raw.strip()
        if ln.startswith("$ "):
            ln = ln[2:]
        if buf:
            ln, buf = buf + " " + ln, ""
        else:
            buf_no = i + 1
        if ln.endswith("\\"):
            buf = ln[:-1].strip()
            continue
        hd = re.search(r"<<-?\s*['\"]?(\w+)", ln)
        if hd:
            heredoc = hd.group(1)
        if not ln or ln.startswith("#"):
            continue
        yield (buf_no, ln)


def shell_commands(root="."):
    """[(file, line, text, why)] for fenced shell lines whose command or first path does not exist.

    A path is judged against the block's tracked cwd, the repo root and the .md's own folder
    (see _exists). `cd X` moves the tracked cwd only when X resolves. An unknown command is
    reported only when the line is shaped like a CLI call (a lowercase name with flags or
    path arguments), so prose and Python inside a mislabelled ```bash fence stay silent."""
    hits = []
    root = os.path.abspath(root)
    root_name = os.path.basename(root)
    for path in _md_files(root):
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")
        mddir = os.path.dirname(path)
        cwd = root
        for line_no, ln in _shell_lines(lines):
            if ln is None:
                cwd = root
                continue
            for seg in re.split(r"&&|\|\||;|\|", ln.split(" #")[0]):
                seg = seg.strip()
                if not seg:
                    continue
                try:
                    toks = shlex.split(seg)
                except ValueError:
                    toks = seg.split()
                while toks and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0]):
                    toks = toks[1:]
                if not toks:
                    continue
                # drop redirect targets: they are created, not referenced
                clean = []
                skip = False
                for t in toks:
                    if skip:
                        skip = False
                        continue
                    if t in (">", ">>", "<", "<<", "2>", "&>"):
                        skip = True
                        continue
                    if re.match(r"^[12]?>>?\S", t) or t.startswith("<<"):
                        continue
                    clean.append(t)
                toks = clean
                if not toks:
                    continue
                cmd, args = toks[0], toks[1:]
                loc = (os.path.relpath(path, root), line_no, seg[:80])
                if cmd == "cd":
                    if not args or _PLACEHOLDER.search(args[0]):
                        continue
                    if args[0].strip("/") == root_name:         # `git clone X && cd X`
                        cwd = root
                        continue
                    for base in (cwd, root, mddir):
                        cand = os.path.normpath(os.path.join(base, args[0]))
                        if os.path.isdir(cand):
                            cwd = cand
                            break
                    else:
                        hits.append(loc + ("cd target missing: %s" % args[0],))
                    continue
                if cmd in ("python", "python3"):
                    if args[:1] == ["-m"] and len(args) > 1:
                        if not _module_present(args[1], cwd, root, mddir):
                            hits.append(loc + ("module missing: %s" % args[1],))
                        continue
                    first = next((a for a in args if not a.startswith("-")), None)
                    if first and _looks_like_path(first) and not _exists(first, cwd, root, mddir):
                        hits.append(loc + ("file missing: %s" % first,))
                    continue
                if cmd.startswith("./") or cmd.startswith("../"):
                    if not _PLACEHOLDER.search(cmd) and not _exists(cmd, cwd, root, mddir):
                        hits.append(loc + ("script missing: %s" % cmd,))
                    continue
                if cmd in _CREATES:
                    continue
                if cmd not in _KNOWN:
                    cli_shaped = (_IDENT.match(cmd) and cmd not in _PY_STATEMENT
                                  and any(a.startswith("-") or _looks_like_path(a) for a in args))
                    if cli_shaped and not (shutil.which(cmd) or _exists(cmd, cwd, root, mddir)):
                        hits.append(loc + ("command not found: %s" % cmd,))
                    continue
                first = next((a for a in args if _looks_like_path(a)), None)
                if first and not _exists(first, cwd, root, mddir):
                    hits.append(loc + ("path missing: %s" % first,))
    return hits


_SECOND_PERSON = re.compile(r"\byour (?:projects?|repos?|repositories|other (?:work|projects))\b", re.I)


def second_person(root="."):
    """[(file, line, text)] where a .md addresses the author's own projects in the second person."""
    hits = []
    for path in _md_files(root):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for i, ln in enumerate(fh, 1):
                if _SECOND_PERSON.search(ln):
                    hits.append((os.path.relpath(path, root), i, ln.strip()[:80]))
    return hits


def spaced_filenames(root="."):
    """[path] for every file or directory whose own name contains a space."""
    hits = []
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(dirs + names):
            if " " in n:
                hits.append(os.path.relpath(os.path.join(base, n), root))
    return hits


def prose_audit(root="."):
    """All five checks. Returns {check: [hits]}; a run with any hit fails."""
    marked = {}
    scan = licence_scan(root, marked=marked)
    status_marked = {}
    speed = speedup_claims(root, marked=status_marked)
    return {
        "licence": licence_mismatch(root),
        "licence_scan": scan,
        "licence_refs": marked,
        "speedup": speed,
        "speedup_marked": status_marked,
        "shell": shell_commands(root),
        "second_person": second_person(root),
        "spaces": spaced_filenames(root),
    }


def prose_report(root="."):
    """Print stage 5 and return the number of hits. Reports; fixes nothing."""
    res = prose_audit(root)
    n = 0
    print("  licence strings                   %d surface(s) disagree" % len(res["licence"]))
    for f, ln, lid in res["licence"]:
        print("      %s:%d  %s" % (f, ln, lid))
    print("  licence ids != LICENSE, unmarked %d" % len(res["licence_scan"]))
    for f, ln, lid, txt in res["licence_scan"]:
        print("      %s:%d  [%s]  %s" % (f, ln, lid, txt))
    refs = res.get("licence_refs", {})
    for kind in ("external", "historical"):
        rows = refs.get(kind, [])
        print("  licence-ref %-10s (not a mismatch) %d" % (kind, len(rows)))
        for f, ln, lid, who, _txt in rows:
            print("      %s:%d  [%s]  %s" % (f, ln, lid, who))
    print("  speedup claims, no benchmark near %d" % len(res["speedup"]))
    for f, ln, txt in res["speedup"]:
        print("      %s:%d  %s" % (f, ln, txt))
    sm = res.get("speedup_marked", {})
    for kind in ("refuted", "refutation of", "unmeasured", "unmeasured operand"):
        rows = sm.get(kind, [])
        if rows:
            print("  claim-status %-19s (not a claim) %d" % (kind, len(rows)))
    print("  shell commands that cannot run    %d" % len(res["shell"]))
    for f, ln, txt, why in res["shell"]:
        print("      %s:%d  %s  <- %s" % (f, ln, txt, why))
    print("  second-person address             %d" % len(res["second_person"]))
    for f, ln, txt in res["second_person"]:
        print("      %s:%d  %s" % (f, ln, txt))
    print("  filenames with a space            %d" % len(res["spaces"]))
    for p in res["spaces"]:
        print("      %s" % p)
    n = sum(len(v) for k, v in res.items() if k not in ("licence_refs", "speedup_marked"))
    print("  %s" % ("prose holds" if not n else
                    "%d hit(s) -- each is a fix in a separate pass; nothing was changed" % n))
    return n


# =====================================================================
# HUMAN CHECKLIST -- the two classes no code catches
# =====================================================================

CHECKLIST = """
NOT MECHANISABLE. ask these by hand before committing:

  CIRCULAR TARGET
    [ ] is the target/reference computed from the model being tested?
    [ ] can the numerator be MEASURED on the same device as the
        denominator? if not, it is model-vs-measurement.
    [ ] would an independently-known value work instead?
        (an integer invariant, a handbook constant, a null result)

  UNITS AND ORDERS
    [ ] every number carries a unit, including in tables
    [ ] one quantity has ONE value across the whole repo
    [ ] convert once by hand: eV<->J<->aJ, cm^-1<->N/m, cm^-2<->cm^-3
    [ ] compare each energy to kT*ln2 = 0.0179 eV at 300 K
    [ ] compare each retention claim to tau = tau0*exp(Ea/kT)
    [ ] pair each material coefficient with the modulus for the SAME
        direction (pi_l <110> goes with E<110> = 169 GPa, not E<100>)

  ONE MORE, FREE
    [ ] does the assertion in the test suite have any input that
        would make it FAIL? if not, delete it.
"""


def human_checklist():
    print(CHECKLIST)


# =====================================================================
# DEMO -- run the three checks against findings this archive already made
# =====================================================================

def demo(seed=0):
    rng = random.Random(seed)

    print("=" * 70)
    print("1. NULL HARNESS -- against a claim this archive already killed")
    print("=" * 70)

    def correlation_floor(lenses):
        """Minimum pairwise correlation across a set of scalar lenses."""
        n = len(lenses)
        best = 1.0
        for i in range(n):
            for j in range(i + 1, n):
                a, b = lenses[i], lenses[j]
                ma, mb = sum(a) / len(a), sum(b) / len(b)
                sxy = sum((x - ma) * (y - mb) for x, y in zip(a, b))
                sxx = math.sqrt(sum((x - ma) ** 2 for x in a))
                syy = math.sqrt(sum((y - mb) ** 2 for y in b))
                best = min(best, sxy / (sxx * syy) if sxx * syy > 0 else 0.0)
        return best

    trace = [(rng.random(), rng.random()) for _ in range(120)]

    def make(coeffs):
        return [[c[0] * r + c[1] * a for r, a in trace] for c in coeffs]

    named = make([(1.0, 1.0), (1.2, 0.8), (1.5, 0.7), (0.8, 0.6), (1.1, 1.3)])

    def random_lenses():
        return make([(rng.uniform(0.8, 1.6), rng.uniform(0.6, 1.4))
                     for _ in range(5)])
    random_lenses.__name__ = "random coefficients"

    report(null_harness(correlation_floor, named, [random_lenses],
                        lambda v: v > 0.88, name="17-lens isomorphism (shape of)",
                        trials=120))

    print("=" * 70)
    print("2. SYMMETRY VETO -- against an abstract this archive had to audit")
    print("=" * 70)
    veto_report("silicon",
                "We encode state via magnetostriction and read it out with a "
                "Faraday magneto-optic probe, exploiting the thermal "
                "anisotropy of the [111] direction and an inverse piezo "
                "actuator, with ESR confirming spin coherence.")

    print("=" * 70)
    print("3. REACH CHECK -- three gaps this archive derived the hard way")
    print("=" * 70)
    reach_report(7.96e-17, "hall sensor", "5um cell moment at 50 mT, field at 1 mm")
    reach_report(3.98e-19, "squid moment", "same cell, moment directly")
    reach_report(5e11, "rbs areal", "Er at 1e17 cm^-3 over 50 nm")
    reach_report(0.121, "piezoresistive", "dR/R at 0.1% strain, GF=121")

    print("=" * 70)
    print("4. COLLISIONS -- one content in two files, or one name in two")
    print("=" * 70)
    import os
    collision_report(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 70)
    print("5. PROSE -- the README is a claim surface like any other")
    print("=" * 70)
    prose_hits = prose_report(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 70)
    print("6. HUMAN CHECKLIST -- the two classes no code catches")
    print("=" * 70)
    human_checklist()
    return prose_hits


def main(argv=None):
    """Exit nonzero on any prose hit. Stages 1-4 report; stage 5 fails the run.
    `python repo_guard.py prose` runs stage 5 alone."""
    import os
    import sys
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["prose"]:
        return 1 if prose_report(os.path.dirname(os.path.abspath(__file__))) else 0
    return 1 if demo() else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
