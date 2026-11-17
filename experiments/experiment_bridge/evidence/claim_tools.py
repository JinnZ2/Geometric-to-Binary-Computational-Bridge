#!/usr/bin/env python3
"""Reusable checks on a received claim-emitting script. Co-authored. Stdlib only.

Written for the Kimi toys, whose main() builds claims through a local
pack(scope, rate_var, value, tol_frac, measurement, failure, measured, extra)
and writes a JSON record with a "claims" list. Nothing here edits a specimen:
scripts run on copies in a temporary directory.

  python experiments/experiment_bridge/evidence/claim_tools.py DIR \\
      --script NAME.py --saved NAME_seed0.json [--seed 0] --output NEW_FILE.json

Three checks, each recorded:

REPLAY  the script is run twice on a copy. Claims are compared pairwise by
    scope after removing only claims[].ts: saved against replay 1, replay 1
    against replay 2. Reported as "k of n equal", with every difference.

LITERAL MEASURED  a claim whose `measured` argument is a literal in the
    source was not measured by the run that reports it. It is flagged
    STRUCTURAL with its line. A verdict on such a claim compares one
    constant with another; what backs it, if anything, is a separate probe,
    which the record names when one is supplied with --probe SCOPE=TEXT and
    leaves null otherwise. This is an AST reading of the call, not a judgment
    of the claim.

TOLERANCE PROVENANCE  per claim: the tol_frac expression as written, whether
    it is a literal, and the reason stated for it. A reason is looked for only
    in comments on the lines of the call and the comment block directly above
    it that mention "tol". None found -> UNSOURCED. A reason stated elsewhere
    (a note file, a chat) is not seen by this check.
"""
import argparse
import ast
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path

VERSION = "experiment-bridge/claim-tools-1"
PACK_ARGS = ("scope", "rate_var", "value", "tol_frac", "measurement", "failure",
             "measured", "extra")


def _const(node):
    """The value of a literal expression (numbers, signs), else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        inner = _const(node.operand)
        if inner is not None:
            return -inner if isinstance(node.op, ast.USub) else inner
    return None


def _scope_pattern(node):
    """A regular expression for the scopes one call can produce: the literal
    itself, or an f-string with its computed parts left open. Else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return re.escape(node.value)
    if isinstance(node, ast.JoinedStr):
        return "".join(re.escape(v.value) if isinstance(v, ast.Constant) else ".+"
                       for v in node.values)
    return None


def call_for(scope, calls):
    """The pack call that produced a recorded claim, or None."""
    for call in calls:
        if call["scope_pattern"] and re.fullmatch(call["scope_pattern"], scope or ""):
            return call
    return None


def pack_calls(source):
    """Every call pack(...) in the source, with its arguments by name."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "pack":
            args = dict(zip(PACK_ARGS, node.args))
            args.update({k.arg: k.value for k in node.keywords if k.arg})
            scope = args.get("scope")
            out.append({"scope": scope.value if isinstance(scope, ast.Constant) else None,
                        "scope_pattern": _scope_pattern(scope),
                        "line": node.lineno, "end_line": node.end_lineno, "args": args})
    return sorted(out, key=lambda c: c["line"])


def literal_measured(source):
    """Claims whose measured value is written in the source, not computed."""
    rows = []
    for call in pack_calls(source):
        node = call["args"].get("measured")
        value = _const(node) if node is not None else None
        rows.append({"scope": call["scope"], "scope_pattern": call["scope_pattern"],
                     "call_line": call["line"],
                     "measured_line": node.lineno if node is not None else None,
                     "measured_expression": ast.get_source_segment(source, node)
                     if node is not None else None,
                     "measured_is_literal": value is not None,
                     "flag": "STRUCTURAL" if value is not None else None})
    return rows


def _comments(source):
    out = {}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            out[tok.start[0]] = tok.string.lstrip("#").strip()
    return out


def tolerance_provenance(source):
    """Per claim: the tolerance as written and the reason stated beside it."""
    comments, lines = _comments(source), source.split("\n")
    rows = []
    for call in pack_calls(source):
        node = call["args"].get("tol_frac")
        near = [comments[n] for n in range(call["line"], call["end_line"] + 1) if n in comments]
        n = call["line"] - 1                       # the comment block directly above
        above = []
        while n >= 1 and lines[n - 1].strip().startswith("#"):
            above.insert(0, comments.get(n, ""))
            n -= 1
        reasons = [c for c in above + near if "tol" in c.lower()]
        rows.append({"scope": call["scope"], "scope_pattern": call["scope_pattern"],
                     "call_line": call["line"],
                     "tol_frac_expression": ast.get_source_segment(source, node)
                     if node is not None else None,
                     "tol_frac_is_literal": node is not None and _const(node) is not None,
                     "stated_reason": " ".join(reasons) if reasons else None,
                     "tolerance_provenance": "STATED_IN_SOURCE" if reasons else "UNSOURCED"})
    return rows


def differences(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for key in sorted(set(a) | set(b)) for d in
                (differences(a[key], b[key], f"{path}.{key}") if key in a and key in b
                 else [{"path": f"{path}.{key}", "left": a.get(key), "right": b.get(key)}])]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, f"{path}[{i}]")]
    return [] if a == b else [{"path": path, "left": a, "right": b}]


def compare_claims(left, right):
    """Pair claims by scope; ts is the only field left out."""
    def by_scope(record):
        return {c.get("scope"): {k: v for k, v in c.items() if k != "ts"}
                for c in record.get("claims", [])}
    a, b = by_scope(left), by_scope(right)
    rows = []
    for scope in sorted(set(a) | set(b), key=str):
        diff = differences(a[scope], b[scope]) if scope in a and scope in b \
            else [{"path": "$", "left": scope in a, "right": scope in b}]
        rows.append({"scope": scope, "equal": not diff, "differences": diff})
    return {"claims": len(rows), "equal": sum(1 for r in rows if r["equal"]),
            "all_equal": all(r["equal"] for r in rows) and bool(rows), "rows": rows}


def replay(directory, script, saved_name, seed=0, runs=2, timeout=600):
    """Run the script `runs` times on a copy; compare claims. Raises on failure."""
    directory = Path(directory)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(directory.iterdir()) if p.is_file()}
    saved = json.loads((directory / saved_name).read_text(encoding="utf-8"))
    records, logs = [], []
    with tempfile.TemporaryDirectory(prefix="experiment-bridge-replay-") as td:
        for p in directory.iterdir():
            if p.is_file():
                shutil.copy2(p, Path(td) / p.name)
        for _ in range(runs):
            proc = subprocess.run([sys.executable, script, str(seed)], cwd=td, text=True,
                                  capture_output=True, timeout=timeout)
            logs.append({"returncode": proc.returncode, "stderr": proc.stderr[-2000:]})
            if proc.returncode:
                raise RuntimeError(f"{script} exited {proc.returncode}: {proc.stderr[-300:]}")
            records.append(json.loads((Path(td) / saved_name).read_text(encoding="utf-8")))
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(directory.iterdir()) if p.is_file()}
    return {"script": script, "saved": saved_name, "seed": seed, "runs": logs,
            "excluded_fields": ["claims[].ts"],
            "saved_vs_replay": compare_claims(saved, records[0]),
            "replay_vs_replay": compare_claims(records[0], records[-1]),
            "specimen_sha256": before, "specimens_unchanged": before == after}


def build(directory, script, saved, seed, probes):
    source = (Path(directory) / script).read_text(encoding="utf-8")
    flags = literal_measured(source)
    for row in flags:
        row["backing_probe"] = probes.get(row["scope"]) if row["flag"] else None
    rep = replay(directory, script, saved, seed)
    return {"version": VERSION, "status": "OBSERVED", "directory": Path(directory).name,
            "environment": {"python": sys.version.split()[0], "platform": sys.platform},
            "replay": rep, "literal_measured": flags,
            "tolerance_provenance": tolerance_provenance(source),
            "summary": {
                "claims": rep["saved_vs_replay"]["claims"],
                "saved_vs_replay_equal": rep["saved_vs_replay"]["equal"],
                "replay_vs_replay_equal": rep["replay_vs_replay"]["equal"],
                "structural": [r["scope"] for r in flags if r["flag"]],
                "unsourced_tolerances": sum(
                    1 for r in tolerance_provenance(source)
                    if r["tolerance_provenance"] == "UNSOURCED")},
            "human_interest": None, "ai_interest": None}


def main(argv=None):
    parser = argparse.ArgumentParser(description="replay, literal-measured and tolerance checks")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--script", required=True)
    parser.add_argument("--saved", required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--probe", action="append", default=[], metavar="SCOPE=TEXT",
                        help="names the probe that backs a STRUCTURAL claim")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    try:
        probes = dict(p.split("=", 1) for p in args.probe)
        record = build(args.directory, args.script, args.saved, args.seed, probes)
    except (OSError, ValueError, SyntaxError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"cannot run: {exc}", file=sys.stderr)
        return 2
    args.output.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n",
                           encoding="ascii")
    s = record["summary"]
    print(f"{args.script}: claims {s['claims']}; saved vs replay equal "
          f"{s['saved_vs_replay_equal']}/{s['claims']}; replay vs replay equal "
          f"{s['replay_vs_replay_equal']}/{s['claims']}")
    for r in record["literal_measured"]:
        if r["flag"]:
            print(f"   STRUCTURAL  {r['scope']}  measured = {r['measured_expression']} "
                  f"(line {r['measured_line']}); backing probe: {r['backing_probe']}")
    for r in record["tolerance_provenance"]:
        print(f"   tol {r['tol_frac_expression']:>8}  {r['tolerance_provenance']:<16}  "
              f"{r['scope'] or r['scope_pattern']}")
    ok = record["replay"]["saved_vs_replay"]["all_equal"] \
        and record["replay"]["replay_vs_replay"]["all_equal"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
