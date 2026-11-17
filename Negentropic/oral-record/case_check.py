"""Render oral_record_case_01.md from its JSON and check the record.
PROPOSED, co-authored, CC0. Stdlib only.

  python3 case_check.py --write      write the .md from the .json
  python3 case_check.py              check: .md == render, record rules hold
  python3 case_check.py --selftest   plant one defect per rule, each must fire
"""
import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
JSON = HERE / "oral_record_case_01.json"
MD = HERE / "oral_record_case_01.md"

# keys that would carry an identity the consent terms exclude
BANNED_KEYS = {"tribe", "nation", "people", "name", "names", "place", "location",
               "region", "elder", "elder_name", "holder_name", "lat", "lon"}


def render(r):
    o = []
    a = o.append
    a("# Oral-record reconstruction case 01")
    a("")
    a(f"Status: {r['status']}. {r['license']}, {r['authorship']}. "
      "Rendered from `oral_record_case_01.json` by `case_check.py --write`; do not edit by hand.")
    a("")
    a("## Consent terms")
    a("")
    a(f"> {r['consent_terms']['verbatim_intent']}")
    a("")
    for x in r["consent_terms"]["applied_as"]:
        a(f"- {x}")
    a("")
    a("Observer slots: " + ", ".join(f"{k} = null" for k, v in r["observers"].items() if v is None))
    a("")
    s = r["source"]
    a("## 1 Source")
    a("")
    a(f"{s['description']}. Status {s['status']}: {s['observed_means']}.")
    a("")
    A = r["stage_a"]
    a(f"## 2 Stage A ({A['date']}), {A['status']}")
    a("")
    a(f"{A['basis']}.")
    a("")
    a(f"- array: {A['build']['array']}")
    a(f"- references: {' / '.join(A['build']['references'])}")
    a(f"- readout: {A['build']['readout']}")
    a("")
    B = r["stage_b"]
    a("## 3 Stage B, corrections")
    a("")
    a(f"{B['basis']}. Origin per item ({' / '.join(B['origin_values_allowed'])}): {B['origin_note']}.")
    a("")
    a("| id | correction | origin |")
    a("|---|---|---|")
    for c in B["corrections"]:
        a(f"| {c['id']} | {c['text']} | {c['origin']} |")
    a("")
    C = r["stage_c"]
    a(f"## 4 Stage C ({C['date']}), {C['status']}")
    a("")
    for c in C["build"]:
        a(f"- {c['id']} {c['element']}")
    a("")
    D = r["delta_a_to_c"]
    a(f"## 5 Delta A to C, {D['status']}")
    a("")
    a(f"Reading by {D['reading_by']}. Holder review (record): {D['holder_review']}; "
      f"{D['holder_review_note']}.")
    a("")
    a("| correction | effect | Stage C | basis | holder review |")
    a("|---|---|---|---|---|")
    for p in D["per_correction"]:
        sc = p["stage_c"]
        sc = "--" if sc is None else (", ".join(sc) if isinstance(sc, list) else sc)
        a(f"| {p['id']} | {p['effect']} | {sc} | {p['basis']} | {p['holder_review']} |")
    a("")
    for p in D["per_correction"]:
        if "link" in p:
            L = p["link"]
            a(f"- {p['id']} link to gap `{L['gap']}` ({L['status']}): {L['note']}. Effect stays {p['effect']}.")
        if "feasibility_ref" in p:
            F = p["feasibility_ref"]
            a(f"- {p['id']} feasibility ref ({F['status']}, read depth {F['read_depth']}): {F['cite']}, "
              f"{F['topic']}. Scope: {F['scope']}. \"better\": {p['better']}.")
    a("")
    a("Stage A elements:")
    a("")
    for e in D["stage_a_elements"]:
        a(f"- {e['element']}: {e['effect']} ({e['basis']})")
    a("")
    a("Gaps:")
    a("")
    for g in D["gaps"]:
        det = g["detail"] if g["detail"] is not None else "(not filled)"
        a(f"- {g['id']} `{g['key']}` {g['state']}: {g['what']}. {det}")
    a("")
    a(f"Rule: {D['lost_rule']}.")
    a("")
    T = r["open"]["bench_test"]
    a(f"## 6 Open: bench test ({T['status']})")
    a("")
    a(f"Purpose: {T['purpose']}.")
    a("")
    for i, st in enumerate(T["protocol"], 1):
        a(f"{i}. {st}")
    a("")
    a("Outcome: " + ", ".join(f"{k} = {'null' if v is None else v}" for k, v in T["outcome"].items()))
    a("")
    R = r["discriminator_row"]
    a(f"## 7 Discriminator row, {R['status']}")
    a("")
    a("| shared/communal | multi-generation | checkable claims | teller not central |")
    a("|---|---|---|---|")
    c = R["columns"]
    a(f"| {c['shared_communal']} | {c['multi_generation']} | {c['checkable_claims']} | {c['teller_not_central']} |")
    a("")
    a(f"{R['reading']}.")
    a("")
    return "\n".join(o)


def _keys(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _keys(v)
    elif isinstance(x, list):
        for v in x:
            yield from _keys(v)


def problems(r):
    p = []
    bad = sorted(set(_keys(r)) & BANNED_KEYS)
    if bad:
        p.append(f"identity-bearing keys present: {bad}")
    if any(v is not None for v in r["observers"].values()):
        p.append("observer slot filled")
    allowed = set(r["stage_b"]["origin_values_allowed"])
    for c in r["stage_b"]["corrections"]:
        if c["origin"] not in allowed:
            p.append(f"{c['id']}: origin {c['origin']!r} not in {sorted(allowed)}")
    for g in r["delta_a_to_c"]["gaps"]:
        if g["state"] == "LOST" and g["detail"] is not None:
            p.append(f"{g['id']}: LOST gap is filled")
    ids = {c["id"] for c in r["stage_b"]["corrections"]}
    mapped = {x["id"] for x in r["delta_a_to_c"]["per_correction"]}
    if ids != mapped:
        p.append(f"delta does not cover every correction: {sorted(ids ^ mapped)}")
    D = r["delta_a_to_c"]
    if D.get("holder_review") != "VOID":
        p.append("record-level holder_review set; only the holder fills it")
    keys = {g["key"] for g in D["gaps"]}
    for x in D["per_correction"]:
        if x.get("holder_review") != "VOID":
            p.append(f"{x['id']}: holder_review set; only the holder fills it")
        if "link" in x and x["link"]["gap"] not in keys:
            p.append(f"{x['id']}: link to unknown gap {x['link']['gap']!r}")
        if "feasibility_ref" in x and x["feasibility_ref"].get("read_depth") != "CARRIED":
            p.append(f"{x['id']}: feasibility_ref read depth above what was read")
    for k, v in r["open"]["bench_test"]["outcome"].items():
        if v not in ("VOID", None):
            p.append(f"bench outcome {k} filled before any run")
    if set(r["discriminator_row"]["columns"].values()) - {"y", "n", "VOID"}:
        p.append("discriminator value outside y/n/VOID")
    return p


def check():
    r = json.loads(JSON.read_text())
    p = problems(r)
    if not MD.exists() or MD.read_text() != render(r):
        p.append("markdown differs from render of the json")
    return p


def selftest():
    base = json.loads(JSON.read_text())
    assert problems(base) == [], problems(base)
    plants = [
        ("key", lambda r: r["source"].__setitem__("place", "x")),
        ("observer", lambda r: r["observers"].__setitem__("ai_reader", "claude")),
        ("origin", lambda r: r["stage_b"]["corrections"][0].__setitem__("origin", "guess")),
        ("lost", lambda r: r["delta_a_to_c"]["gaps"][1].__setitem__("detail", "a route")),
        ("cover", lambda r: r["delta_a_to_c"]["per_correction"].pop()),
        ("bench", lambda r: r["open"]["bench_test"]["outcome"].__setitem__("ordering_selected", "3")),
        ("review_row", lambda r: r["delta_a_to_c"]["per_correction"][2].__setitem__("holder_review", "agrees")),
        ("review_rec", lambda r: r["delta_a_to_c"].__setitem__("holder_review", "agrees")),
        ("review_missing", lambda r: r["delta_a_to_c"]["per_correction"][0].pop("holder_review")),
        ("link", lambda r: r["delta_a_to_c"]["per_correction"][0]["link"].__setitem__("gap", "nowhere")),
        ("depth", lambda r: r["delta_a_to_c"]["per_correction"][4]["feasibility_ref"].__setitem__("read_depth", "FULL_TEXT")),
        ("disc", lambda r: r["discriminator_row"]["columns"].__setitem__("multi_generation", "maybe")),
    ]
    n = 1
    for name, f in plants:
        r = copy.deepcopy(base)
        f(r)
        assert problems(r), f"plant {name} did not fire"
        n += 1
    assert render(base).count("| B") >= 12
    n += 1
    print(f"checks: {n}   failed: 0")
    return 0


def main(argv):
    if argv[1:] == ["--write"]:
        MD.write_text(render(json.loads(JSON.read_text())))
        return 0
    if argv[1:] == ["--selftest"]:
        return selftest()
    p = check()
    for x in p:
        print("PROBLEM:", x)
    print("OK" if not p else f"{len(p)} problem(s)")
    return 1 if p else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
