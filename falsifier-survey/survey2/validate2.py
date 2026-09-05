
import json, glob, collections

GM = json.load(open("/mnt/agents/output/survey2/folders_gm.json"))
G2B = json.load(open("/mnt/agents/output/survey2/folders_g2b.json"))
REQ = {"folder","claim_id","source_file","falsifier_text","status","measured_as","scope_transform","downgrade_reason","notes"}
LEGAL = {"MEASURED","SCOPE-DIFFERENT","MISSING","UNKNOWN"}
errors, records = [], []

for path, legal_folders in [(f"/mnt/agents/output/survey2/batches2/{n}.jsonl", lf)
                            for n, lf in [("gm", GM), ("g2b_a", G2B), ("g2b_b", G2B)]]:
    repo = "gm" if path.endswith("/gm.jsonl") else "g2b"
    for ln, line in enumerate(open(path), 1):
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except Exception as e:
            errors.append(f"{path}:{ln} bad JSON {e}"); continue
        mk = REQ - set(r)
        if mk: errors.append(f"{path}:{ln} missing keys {mk}"); continue
        if r["status"] not in LEGAL: errors.append(f"{path}:{ln} illegal status {r['status']}")
        if r["folder"] not in legal_folders: errors.append(f"{path}:{ln} unknown unit {r['folder']!r}")
        if r["status"]=="MEASURED":
            ma = r["measured_as"]
            if not isinstance(ma, dict) or not all(ma.get(k) for k in ("quantity","units","how_obtained")):
                errors.append(f"{path}:{ln} MEASURED w/o complete measured_as [{r['folder']}/{r['claim_id']}]")
        if r["status"]=="SCOPE-DIFFERENT":
            st = r["scope_transform"]
            if not isinstance(st, dict) or not all(st.get(k) for k in ("reference","maps_to","breaks_at")):
                errors.append(f"{path}:{ln} SCOPE-DIFFERENT w/o complete transform [{r['folder']}/{r['claim_id']}]")
        r["repo"] = repo
        records.append(r)

for name, legals in [("gm", GM), ("g2b", G2B)]:
    cov = set(r["folder"] for r in records if r["repo"]==name)
    unc = set(legals) - cov
    print(name, "covered:", len(cov), "/", len(legals), "| uncovered:", sorted(unc) if unc else "none")
print("records:", len(records), "| statuses:", dict(collections.Counter(r["status"] for r in records)))
print("ERRORS:", len(errors))
for e in errors[:40]: print(" -", e)
