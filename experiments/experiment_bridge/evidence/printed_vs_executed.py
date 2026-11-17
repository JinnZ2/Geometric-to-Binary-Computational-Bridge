#!/usr/bin/env python3
"""T1: outputs printed in the working notes against what the scripts print. Co-authored.

The notes show two blocks of "output" for the two scripts they contain. This
reads those blocks out of raw/working_notes.txt, runs the unchanged
as-received scripts in a temporary directory, and diffs the two. It repairs
nothing; a difference is the finding.

  python experiments/experiment_bridge/evidence/printed_vs_executed.py --output NEW_FILE.json
  python experiments/experiment_bridge/evidence/printed_vs_executed.py --check SNAPSHOT.json

--output writes the record and refuses to overwrite an existing file. --check
recomputes and exits 1 if the stable part differs from the snapshot.
Exit: 0 written / snapshot agrees | 1 snapshot differs | 2 cannot run.

What is compared, per script:
  source     the python fence in the notes against the as-received file
             (trailing whitespace per line ignored)
  lines      printed against executed, trailing whitespace ignored; blank
             lines dropped on both sides
  numbers    every decimal number on a line, in order
  verdict    EQUAL | DIFFERS, with each differing line and number named

The speaker label in the notes ("DeepSeek:", once, before both scripts) is as
supplied and is not authenticated here. Stdlib only.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent / "raw" / "working_notes.txt"
REFERENCE = HERE.parent / "raw" / "lojban_wordslot_reference.json"
# script as received -> the heading in the notes that introduces its printed output
SCRIPTS = (("ncm_bridge_as_received.py", "Output of the Script"),
           ("ncm_level_walk_as_received.py", "Understanding the Output"))
NUMBER = re.compile(r"(?<![\w.])-?\d+\.\d+")
VERSION = "experiment-bridge/printed-vs-executed-1"


def fences(text):
    """[(language, first body line number, body lines)] for every fenced block."""
    out, lang, start, body = [], None, None, []
    for n, line in enumerate(text.split("\n"), 1):
        if line.startswith("```"):
            if lang is None:
                lang, start, body = line[3:].strip(), n + 1, []
            else:
                out.append((lang, start, body))
                lang = None
        elif lang is not None:
            body.append(line)
    return out


def printed_block(text, heading):
    """The first text fence after the heading. Returns (first line number, lines)."""
    lines = text.split("\n")
    at = next((i for i, line in enumerate(lines, 1) if line.strip() == heading), None)
    if at is None:
        raise ValueError(f"heading {heading!r} is not in the notes")
    for lang, start, body in fences(text):
        if lang == "text" and start > at:
            return start, body
    raise ValueError(f"no text fence after {heading!r}")


def tidy(lines):
    return [line.rstrip() for line in lines if line.strip()]


def compare(printed, executed):
    a, b = tidy(printed), tidy(executed)
    rows = []
    for i in range(max(len(a), len(b))):
        p = a[i] if i < len(a) else None
        e = b[i] if i < len(b) else None
        if p == e:
            continue
        col = None
        if p is not None and e is not None:
            col = next((k for k, (x, y) in enumerate(zip(p, e)) if x != y), min(len(p), len(e)))
        pn = NUMBER.findall(p or "")
        en = NUMBER.findall(e or "")
        rows.append({"line": i + 1, "first_differing_column": col,
                     "printed": p, "executed": e,
                     "numbers_printed": pn, "numbers_executed": en,
                     "numbers_differ": [{"position": k, "printed": x, "executed": y}
                                        for k, (x, y) in enumerate(zip(pn, en)) if x != y],
                     "number_count_differs": len(pn) != len(en)})
    return {"lines_printed": len(a), "lines_executed": len(b),
            "lines_equal": max(len(a), len(b)) - len(rows), "lines_differ": len(rows),
            "verdict": "EQUAL" if not rows else "DIFFERS", "differences": rows}


def source_matches(text, script):
    want = [line.rstrip() for line in (HERE / script).read_text(encoding="utf-8").split("\n")]
    while want and not want[-1]:
        want.pop()
    for lang, start, body in fences(text):
        got = [line.rstrip() for line in body]
        while got and not got[-1]:
            got.pop()
        if lang == "python" and got == want:
            return {"found": True, "notes_first_line": start}
    return {"found": False, "notes_first_line": None}


def build():
    text = NOTES.read_text(encoding="utf-8")
    speaker = next((i for i, line in enumerate(text.split("\n"), 1)
                    if line.strip() == "DeepSeek:"), None)
    record = {"version": VERSION, "status": "OBSERVED",
              "scope": "the two scripts in raw/working_notes.txt; nothing is repaired",
              "notes_sha256": hashlib.sha256(NOTES.read_bytes()).hexdigest(),
              "speaker_label": {"label": "DeepSeek", "notes_line": speaker,
                                "authenticated": False},
              "scripts": [], "human_interest": None, "ai_interest": None}
    with tempfile.TemporaryDirectory(prefix="experiment-bridge-t1-") as td:
        for script, heading in SCRIPTS:
            shutil.copy2(HERE / script, Path(td) / script)
        shutil.copy2(REFERENCE, Path(td) / REFERENCE.name)
        for script, heading in SCRIPTS:
            start, printed = printed_block(text, heading)
            proc = subprocess.run([sys.executable, script], cwd=td, text=True,
                                  capture_output=True, timeout=120)
            executed = proc.stdout.split("\n")
            record["scripts"].append({
                "script": script,
                "script_sha256": hashlib.sha256((HERE / script).read_bytes()).hexdigest(),
                "source_in_notes": source_matches(text, script),
                "printed_block": {"heading": heading, "notes_first_line": start,
                                  "lines": tidy(printed)},
                "execution": {"returncode": proc.returncode, "stderr": proc.stderr,
                              "lines": tidy(executed)},
                "comparison": compare(printed, executed)})
    record["summary"] = {s["script"]: s["comparison"]["verdict"] for s in record["scripts"]}
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description="printed outputs vs execution (T1)")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    if (args.output is None) == (args.check is None):
        parser.error("give exactly one of --output and --check")
    try:
        record = build()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"cannot run: {exc}", file=sys.stderr)
        return 2
    for s in record["scripts"]:
        c = s["comparison"]
        print(f"{s['script']}: {c['verdict']}  lines equal {c['lines_equal']}, "
              f"differ {c['lines_differ']}")
        for d in c["differences"]:
            for n in d["numbers_differ"]:
                print(f"   line {d['line']}: printed {n['printed']}  executed {n['executed']}")
    if args.check is not None:
        saved = json.loads(args.check.read_text(encoding="utf-8"))
        same = saved == record
        print("snapshot agrees" if same else "snapshot DIFFERS from this execution")
        return 0 if same else 1
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    args.output.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n",
                           encoding="ascii")
    print("written ->", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
