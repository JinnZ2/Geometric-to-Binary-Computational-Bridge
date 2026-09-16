#!/usr/bin/env python3
"""
crosslinks.py -- the guard and the renderer for the God's Eye View integration map.

    python integrations/gods-eye-view/crosslinks.py            # check, exit nonzero
    python integrations/gods-eye-view/crosslinks.py render     # README.md per folder + INTEGRATION_INDEX.json
    python integrations/gods-eye-view/crosslinks.py matrix     # domains x ecosystem mounts, report only
    python integrations/gods-eye-view/crosslinks.py gev-view   # the GEV-side view, to stdout

AUTHORITY
    Each NN-<id>/links.json is the authority for its domain. README.md and
    INTEGRATION_INDEX.json are VIEWS rendered from it, and `check` fails when
    a view has drifted from its source. One content, one file: this is the
    P-DUPLICATE-AUTHORITY rule applied to the map itself.

CHECKS  (each one names an input that makes it FAIL)
    1  folder layout     every NN-<id>/ has links.json + README.md; folder == links.folder; ids unique
    2  reciprocity       every sibling link resolves, and points back
    3  bridge paths      every bridge[].path exists in this repo
    4  gev paths         every gev[].path exists in the GEV checkout when one is found
                         (GEV_ROOT, ../gods-eye-view-fork, ../gods-eye-view); else UNVERIFIED, not FAIL
    5  ecosystem mounts  every ecosystem[].mount is a source name in .fieldlink.json
    6  avenue contract   id, title, direction in DIRECTIONS, cost in COSTS, moves, fails_if -- non-empty.
                         `fails_if` is META-PROTOCOL principle 3: a claim must name what would change it.
    7  id hygiene        no avenue id matches claims_index.ID_RX, so this map cannot leak a
                         claim family into the index by being scanned
    8  views fresh       README.md and INTEGRATION_INDEX.json equal render()
    9  consent           05-infrastructure/consent.json: every pack has license + share_ok; a pack
                         with share_ok:false has mount:null (av-inf-2, the NC boundary made mechanical)
   10  the map           integrations/gods-eye-view/README.md exists and names every folder

SCOPE
    Reports. Does not propose. A generator of "plausible" domain x mount pairs
    would have no ranking and no way to be wrong (tests/test_explore.py names
    that shape); `matrix` prints which cells are filled and stops there.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
INDEX = os.path.join(HERE, "INTEGRATION_INDEX.json")
FIELDLINK = os.path.join(ROOT, ".fieldlink.json")
GEV_REPO = "https://github.com/JinnZ2/gods-eye-view-fork"
BRIDGE_REPO = "https://github.com/JinnZ2/Geometric-to-Binary-Computational-Bridge"

DIRECTIONS = ("gev->bridge", "bridge->gev", "both", "bridge->bridge", "gev->ecosystem")
COSTS = ("trivial", "low", "medium", "high")
FOLDER_RX = re.compile(r"^(\d{2})-([a-z][a-z-]*)$")
# Same pattern claims_index.py scans for. Kept literal here so this file has no
# import edge into the index; test_integration_crosslinks asserts they agree.
CLAIM_ID_RX = re.compile(r"(?<![\w-])([A-Z][A-Z0-9]{1,7}-[0-9]{1,2}[a-z]?)(?![\w-])")


# ---------------------------------------------------------------- loading

def gev_root() -> str | None:
    """The GEV checkout, if one is beside this repo or named by GEV_ROOT."""
    cands = [os.environ.get("GEV_ROOT"),
             os.path.join(ROOT, "..", "gods-eye-view-fork"),
             os.path.join(ROOT, "..", "gods-eye-view")]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "package.json")):
            return os.path.abspath(c)
    return None


def folders(here: str = HERE) -> list[str]:
    return sorted(n for n in os.listdir(here)
                  if FOLDER_RX.match(n) and os.path.isdir(os.path.join(here, n)))


def load(here: str = HERE) -> list[dict]:
    out = []
    for n in folders(here):
        p = os.path.join(here, n, "links.json")
        if not os.path.isfile(p):
            out.append({"id": None, "folder": n, "_error": "links.json missing"})
            continue
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        d["_dir"] = n
        out.append(d)
    return out


def fieldlink_mounts(path: str = FIELDLINK) -> set[str]:
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as fh:
        return {s["name"] for s in json.load(fh)["fieldlink"]["sources"]}


# ---------------------------------------------------------------- checks

def check(here: str = HERE, root: str = ROOT, gev: str | None = None,
          mounts: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, notes). Empty errors means the map holds."""
    errs, notes = [], []
    doms = load(here)
    mounts = fieldlink_mounts() if mounts is None else mounts
    gev = gev_root() if gev is None else gev
    by_id = {}

    for d in doms:
        n = d["_dir"]
        if "_error" in d:
            errs.append(f"{n}: {d['_error']}")
            continue
        if not os.path.isfile(os.path.join(here, n, "README.md")):
            errs.append(f"{n}: README.md missing")
        if d.get("folder") != n:
            errs.append(f"{n}: links.folder is {d.get('folder')!r}")
        if FOLDER_RX.match(n).group(2) != d.get("id"):
            errs.append(f"{n}: folder suffix != id {d.get('id')!r}")
        if d["id"] in by_id:
            errs.append(f"{n}: duplicate id {d['id']}")
        by_id[d["id"]] = d
        for key in ("title", "shape", "flow", "notes", "gev", "bridge",
                    "ecosystem", "siblings", "avenues", "interference"):
            if key not in d:
                errs.append(f"{n}: missing field {key}")
        for key in ("bottleneck", "leverage", "harmonics", "tertiary"):
            if not d.get("notes", {}).get(key):
                errs.append(f"{n}: notes.{key} empty")

    # 2 reciprocity
    for d in by_id.values():
        for s in d.get("siblings", []):
            if s not in by_id:
                errs.append(f"{d['id']}: sibling {s!r} does not exist")
            elif d["id"] not in by_id[s].get("siblings", []):
                errs.append(f"{d['id']} -> {s} is not reciprocated")

    # 3 / 4 paths
    for d in by_id.values():
        for e in d.get("bridge", []):
            if not os.path.exists(os.path.join(root, e["path"])):
                errs.append(f"{d['id']}: bridge path missing: {e['path']}")
        for e in d.get("gev", []):
            if gev is None:
                continue
            if not os.path.exists(os.path.join(gev, e["path"])):
                errs.append(f"{d['id']}: gev path missing: {e['path']}")
    if gev is None:
        notes.append("gev paths UNVERIFIED: no checkout found (set GEV_ROOT)")

    # 5 mounts
    for d in by_id.values():
        for e in d.get("ecosystem", []):
            if mounts and e["mount"] not in mounts:
                errs.append(f"{d['id']}: mount {e['mount']!r} not in .fieldlink.json")
    if not mounts:
        notes.append("mounts UNVERIFIED: .fieldlink.json not readable")

    # 6 / 7 avenues
    seen = set()
    for d in by_id.values():
        for a in d.get("avenues", []):
            aid = a.get("id", "")
            for key in ("id", "title", "direction", "cost", "moves", "fails_if"):
                if not a.get(key):
                    errs.append(f"{d['id']}/{aid or '?'}: avenue.{key} empty")
            if a.get("direction") not in DIRECTIONS:
                errs.append(f"{d['id']}/{aid}: direction {a.get('direction')!r}")
            if a.get("cost") not in COSTS:
                errs.append(f"{d['id']}/{aid}: cost {a.get('cost')!r}")
            if aid in seen:
                errs.append(f"{d['id']}/{aid}: duplicate avenue id")
            seen.add(aid)
            if CLAIM_ID_RX.search(aid or ""):
                errs.append(f"{d['id']}/{aid}: avenue id matches the claim-id pattern")

    # 9 consent
    cpath = os.path.join(here, "05-infrastructure", "consent.json")
    if os.path.isfile(cpath):
        with open(cpath, encoding="utf-8") as fh:
            packs = json.load(fh).get("packs", [])
        for pk in packs:
            src = pk.get("source", "?")
            for key in ("path", "license", "attribution"):
                if not pk.get(key):
                    errs.append(f"consent/{src}: {key} empty")
            if not isinstance(pk.get("share_ok"), bool):
                errs.append(f"consent/{src}: share_ok must be a bool")
            elif pk["share_ok"] is False and pk.get("mount") is not None:
                errs.append(f"consent/{src}: share_ok is false but a mount is declared")
            elif pk["share_ok"] is True and not pk.get("mount"):
                errs.append(f"consent/{src}: share_ok is true but no mount is declared")
            if gev is not None and pk.get("path") and not os.path.exists(os.path.join(gev, pk["path"])):
                errs.append(f"consent/{src}: gev path missing: {pk['path']}")
    elif os.path.isdir(os.path.join(here, "05-infrastructure")):
        errs.append("05-infrastructure/consent.json missing")

    # 10 the map
    top = os.path.join(here, "README.md")
    if not os.path.isfile(top):
        errs.append("README.md (the map) missing")
    else:
        with open(top, encoding="utf-8") as fh:
            body = fh.read()
        for d in by_id.values():
            if d["_dir"] not in body:
                errs.append(f"README.md (the map) does not name {d['_dir']}")

    # 8 views fresh
    for d in by_id.values():
        want = render_readme(d)
        p = os.path.join(here, d["_dir"], "README.md")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                if fh.read() != want:
                    errs.append(f"{d['id']}: README.md stale (run render)")
    idx = os.path.join(here, "INTEGRATION_INDEX.json")
    if os.path.isfile(idx):
        with open(idx, encoding="utf-8") as fh:
            if fh.read() != render_index(list(by_id.values())):
                errs.append("INTEGRATION_INDEX.json stale (run render)")
    else:
        errs.append("INTEGRATION_INDEX.json missing (run render)")
    return errs, notes


# ---------------------------------------------------------------- rendering

def _table(rows: list[list[str]], head: list[str]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


def _folder_of(doms_by_id: dict, sid: str) -> str:
    return doms_by_id[sid]["_dir"] if sid in doms_by_id else sid


def render_readme(d: dict, doms_by_id: dict | None = None) -> str:
    """One domain README, rendered from its links.json. Deterministic."""
    if doms_by_id is None:
        doms_by_id = {x["id"]: x for x in load(os.path.dirname(os.path.join(HERE, d["_dir"])))}
    L = []
    L.append(f"# {d['title']}")
    L.append("")
    L.append(f"> {d['shape']}")
    L.append("")
    L.append("Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.")
    L.append("")
    L.append("## Flow")
    L.append("")
    L.append("```")
    L.extend(d["flow"])
    L.append("```")
    L.append("")
    L.append("## Shape")
    L.append("")
    n = d["notes"]
    L.append(_table([["bottleneck", n["bottleneck"]], ["leverage", n["leverage"]],
                     ["harmonics", n["harmonics"]], ["tertiary", n["tertiary"]]],
                    ["", ""]))
    L.append("")
    L.append("## Entry points")
    L.append("")
    L.append(f"GEV ({GEV_REPO})")
    L.append("")
    L.append(_table([[f"`{e['path']}`", e["role"]] for e in d["gev"]], ["file", "role"]))
    L.append("")
    L.append("Bridge (this repo)")
    L.append("")
    L.append(_table([[f"`{e['path']}`", e["role"]] for e in d["bridge"]], ["file", "role"]))
    L.append("")
    L.append("## Avenues")
    L.append("")
    L.append("Each one names what would make it FAIL. An avenue that cannot fail is not listed.")
    L.append("")
    for a in d["avenues"]:
        L.append(f"### `{a['id']}` {a['title']}")
        L.append("")
        L.append(f"- direction `{a['direction']}` · cost `{a['cost']}`")
        L.append(f"- **moves:** {a['moves']}")
        L.append(f"- **fails if:** {a['fails_if']}")
        if a.get("status"):
            L.append(f"- **status:** {a['status']}")
        L.append("")
    L.append("## Interference")
    L.append("")
    for s in d["interference"]:
        L.append(f"- {s}")
    L.append("")
    L.append("## Ecosystem taps")
    L.append("")
    L.append(_table([[f"`{e['mount']}`", e["why"]] for e in d["ecosystem"]],
                    ["fieldlink mount", "why it plugs in here"]))
    L.append("")
    L.append("## Crosslinks")
    L.append("")
    for s in d["siblings"]:
        L.append(f"- [{s}](../{_folder_of(doms_by_id, s)}/README.md)")
    L.append("- [map](../README.md)")
    L.append("")
    return "\n".join(L)


def render_index(doms: list[dict]) -> str:
    """Machine-readable view of every links.json. Deterministic, sorted."""
    out = {"_comment": "VIEW rendered by crosslinks.py render. Authority is each folder's links.json.",
           "gev_repo": GEV_REPO, "bridge_repo": BRIDGE_REPO,
           "directions": list(DIRECTIONS), "costs": list(COSTS),
           "domains": []}
    for d in sorted(doms, key=lambda x: x["_dir"]):
        out["domains"].append({
            "id": d["id"], "folder": d["_dir"], "title": d["title"], "shape": d["shape"],
            "gev_paths": [e["path"] for e in d["gev"]],
            "bridge_paths": [e["path"] for e in d["bridge"]],
            "mounts": [e["mount"] for e in d["ecosystem"]],
            "siblings": list(d["siblings"]),
            "avenues": [{"id": a["id"], "title": a["title"], "direction": a["direction"],
                         "cost": a["cost"], **({"status": a["status"]} if a.get("status") else {})}
                        for a in d["avenues"]],
        })
    return json.dumps(out, indent=1, ensure_ascii=False) + "\n"


def render_gev_view(doms: list[dict]) -> str:
    """The GEV-side pointer document. A view; the folders here stay the authority."""
    L = ["# Integration avenues with Geometric-to-Binary-Computational-Bridge", "",
         "> A VIEW. The authority is `integrations/gods-eye-view/*/links.json` in",
         f"> {BRIDGE_REPO}, rendered by `crosslinks.py gev-view`. Edit there.", "",
         "One folder per domain. Each names the GEV entry points, the bridge entry",
         "points, the ecosystem repos that plug in, and the avenues with what would",
         "make each one FAIL.", "",
         "```",
         "  GEV  = SINK + RENDER    public feeds → proxies (cache, serve-stale) → layer records → globe / voice",
         "  Bridge = MEASURE + JUDGE  transducer → Gray bits → claim table → router → residual → query",
         "  Seam = the layer record (plain {lat, lon, ...} + feed state)  ⇄  reading() / Primitive",
         "```", ""]
    for d in sorted(doms, key=lambda x: x["_dir"]):
        L.append(f"## {d['_dir']}")
        L.append("")
        L.append(f"{d['shape']}")
        L.append("")
        L.append(f"Bridge folder: `integrations/gods-eye-view/{d['_dir']}/`")
        L.append("")
        L.append("GEV entry points")
        L.append("")
        L.append(_table([[f"`{e['path']}`", e["role"]] for e in d["gev"]], ["file", "role"]))
        L.append("")
        L.append("Avenues")
        L.append("")
        L.append(_table([[f"`{a['id']}`", a["title"], a["direction"], a["cost"],
                          a.get("status", "")] for a in d["avenues"]],
                        ["id", "title", "direction", "cost", "status"]))
        L.append("")
        L.append("Ecosystem: " + ", ".join(f"`{e['mount']}`" for e in d["ecosystem"]))
        L.append("")
    return "\n".join(L)


def render(here: str = HERE) -> list[str]:
    doms = [d for d in load(here) if "_error" not in d]
    by_id = {d["id"]: d for d in doms}
    written = []
    for d in doms:
        p = os.path.join(here, d["_dir"], "README.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(render_readme(d, by_id))
        written.append(p)
    p = os.path.join(here, "INTEGRATION_INDEX.json")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(render_index(doms))
    written.append(p)
    return written


def matrix(doms: list[dict], mounts: set[str] | None = None) -> str:
    """domains x mounts. Filled cells only; empty cells are absences, not proposals."""
    doms = sorted(doms, key=lambda x: x["_dir"])
    cols = sorted({e["mount"] for d in doms for e in d.get("ecosystem", [])})
    rows = []
    for d in doms:
        got = {e["mount"] for e in d.get("ecosystem", [])}
        rows.append([d["id"]] + ["x" if c in got else "" for c in cols])
    untouched = sorted((mounts or set()) - set(cols))
    s = _table(rows, ["domain"] + cols)
    if untouched:
        s += "\n\nmounts no domain taps (absence, not a suggestion): " + ", ".join(untouched)
    return s


# ---------------------------------------------------------------- cli

def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "render":
        for p in render():
            print("wrote", os.path.relpath(p, ROOT))
        return 0
    if cmd == "matrix":
        print(matrix([d for d in load() if "_error" not in d], fieldlink_mounts()))
        return 0
    if cmd == "gev-view":
        sys.stdout.write(render_gev_view([d for d in load() if "_error" not in d]))
        return 0
    errs, notes = check()
    for n in notes:
        print("note:", n)
    for e in errs:
        print("FAIL:", e)
    doms = [d for d in load() if "_error" not in d]
    print(f"{len(doms)} domains, {sum(len(d['avenues']) for d in doms)} avenues, "
          f"{len(errs)} errors")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
