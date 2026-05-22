"""
ledger.py  (fabrication/)

Single inspector over CLAIM_TABLE.fab.json and its siblings.
Four queries cover most field use:

  summary    -> counts per domain / kind / verdict / emit format
  list       -> all claims (optionally filtered by scope prefix)
  show       -> one claim by id or scope
  measure    -> measurements logged against a scope prefix

CLI:
  python -m fabrication.ledger summary
  python -m fabrication.ledger list [scope_prefix]
  python -m fabrication.ledger show <id|scope>
  python -m fabrication.ledger measure <scope_prefix>

License: CC0. Stdlib only.
"""
import json
import sys
from pathlib import Path


LEDGER       = Path("CLAIM_TABLE.fab.json")
MEASUREMENTS = Path("CLAIM_TABLE.fab.measurements.json")
BASELINES    = Path("CLAIM_TABLE.fab.baselines.json")
OVERLAY      = Path("coupler_overlay.json")


def _load(p):
    return json.loads(p.read_text()) if p.exists() else []


def list_claims(prefix=None):
    claims = _load(LEDGER)
    if prefix:
        claims = [c for c in claims
                  if c.get("scope", "").startswith(prefix)]
    return claims


def show(query):
    for c in _load(LEDGER):
        if c.get("id") == query or c.get("scope") == query:
            return c
    return None


def measurements_for(scope_prefix):
    out = []
    for m in _load(MEASUREMENTS):
        s = m.get("scope") or m.get("scope_prefix", "")
        if s.startswith(scope_prefix):
            out.append(m)
    return out


def summary():
    claims = _load(LEDGER)
    ms     = _load(MEASUREMENTS)
    by_domain, by_kind, by_emit, by_verdict = {}, {}, {}, {}
    for c in claims:
        parts = c.get("scope", "").split("::")
        if len(parts) >= 2 and parts[0] == "fab":
            # compound domains like "electrical-magnetic" tally both
            for dom in parts[1].split("-"):
                by_domain[dom] = by_domain.get(dom, 0) + 1
        k = c.get("kind", "?")
        by_kind[k] = by_kind.get(k, 0) + 1
        if c.get("format"):
            by_emit[c["format"]] = by_emit.get(c["format"], 0) + 1
    for m in ms:
        v = m.get("verdict") or m.get("overall") or "?"
        by_verdict[v] = by_verdict.get(v, 0) + 1
    return {
        "n_claims":       len(claims),
        "n_measurements": len(ms),
        "n_baselines":    len(_load(BASELINES)),
        "n_couplers":     len(_load(OVERLAY)),
        "by_domain":      by_domain,
        "by_kind":        by_kind,
        "by_emit_format": by_emit,
        "by_verdict":     by_verdict,
    }


def _fmt_summary(s):
    out = ["-" * 64]
    out.append(f"  total claims        : {s['n_claims']}")
    out.append(f"  total measurements  : {s['n_measurements']}")
    out.append(f"  total baselines     : {s['n_baselines']}")
    out.append(f"  total couplers      : {s['n_couplers']}")
    for label, d in (("by domain",  s["by_domain"]),
                     ("by kind",    s["by_kind"]),
                     ("by emit",    s["by_emit_format"]),
                     ("by verdict", s["by_verdict"])):
        if d:
            out.append(f"  {label}:")
            for k, n in sorted(d.items(), key=lambda kv: -kv[1]):
                out.append(f"    {k:25s} {n}")
    out.append("-" * 64)
    return "\n".join(out)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: ledger summary | list [prefix] | "
              "show <id|scope> | measure <scope_prefix>")
        return 0
    cmd = argv[0]
    if cmd == "summary":
        print(_fmt_summary(summary()))
        return 0
    if cmd == "list":
        prefix = argv[1] if len(argv) > 1 else None
        for c in list_claims(prefix):
            print(f"  {c.get('id','?'):16s}  "
                  f"{c.get('scope','?')[:60]:60s}  "
                  f"{c.get('rate_var','?')}")
        return 0
    if cmd == "show":
        if len(argv) < 2:
            print("show needs id or scope"); return 2
        hit = show(argv[1])
        # `hit is not None` matters because a legitimate empty-dict
        # claim entry (e.g. one with only id+scope set) should not
        # render as "not found".
        print(json.dumps(hit, indent=2, default=str)
              if hit is not None
              else f"not found: {argv[1]}")
        return 0
    if cmd == "measure":
        if len(argv) < 2:
            print("measure needs scope prefix"); return 2
        # Sort by timestamp so a measurement history reads in
        # chronological order regardless of insertion order in the log.
        for m in sorted(measurements_for(argv[1]),
                        key=lambda x: x.get("ts", 0)):
            v = m.get("verdict") or m.get("overall") or "?"
            print(f"  ts={m.get('ts',0):.0f}  {v:6s}  "
                  f"{m.get('method','?'):40s}  "
                  f"{m.get('scope') or m.get('scope_prefix','?')}")
        return 0
    print(f"unknown cmd: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
