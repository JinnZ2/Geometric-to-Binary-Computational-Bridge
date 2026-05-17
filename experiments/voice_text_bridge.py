"""
voice_text_bridge.py

Protocol for handling the voice/text mode persistence gap in Claude
conversations. Bridges two distinct infrastructure issues:

  1. Voice mode generates tool-call-shaped text without invoking tools
  2. Voice mode outputs render visually but don't reliably persist
     into text-mode context windows

Workflow:

- In voice mode: Claude emits artifacts as text with VOICE_ARTIFACT
  headers (never claims tool calls)
- User copies artifacts back into text mode (or pastes session log)
- This module finds the markers, parses entries, materializes real
  files via real tool calls

ARTIFACT FORMAT:

    # VOICE_ARTIFACT: suggested_filename.ext
    # intent: one-line description
    # timestamp: 2026-05-17T22:00:00Z
    # session: optional_session_id

    [actual content - can be any number of lines]

    # END_ARTIFACT

The END_ARTIFACT marker is required -- it removes ambiguity about
where artifact content stops and conversation prose resumes.

License: CC0
Designed for: phone-only operation, stdlib only, mobile-buildable
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


# ===================================================================
# MARKER PROTOCOL
# ===================================================================

START_MARKER = re.compile(
    r"#\s*VOICE_ARTIFACT:\s*(?P<filename>[^\s\n]+)\s*\n"
    r"(?:#\s*intent:\s*(?P<intent>[^\n]+)\n)?"
    r"(?:#\s*timestamp:\s*(?P<timestamp>[^\n]+)\n)?"
    r"(?:#\s*session:\s*(?P<session>[^\n]+)\n)?",
    re.MULTILINE,
)

END_MARKER = re.compile(r"#\s*END_ARTIFACT\s*$", re.MULTILINE)


# ===================================================================
# ARTIFACT RECORD
# ===================================================================

@dataclass
class VoiceArtifact:
    """One artifact extracted from voice-mode conversation text."""
    filename:           str
    intent:             str = ""
    timestamp:          str = ""
    session:            str = ""
    content:            str = ""
    extracted_at:       str = ""    # when text-mode found it
    status:             str = "extracted"   # extracted|materialized|verified|failed
    notes:              str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ===================================================================
# EXTRACTION -- find artifacts in pasted conversation text
# ===================================================================

def extract_artifacts(conversation_text: str) -> list[VoiceArtifact]:
    """Scan conversation text for VOICE_ARTIFACT...END_ARTIFACT blocks.
    Each artifact's content is bounded by its header and the next
    END_ARTIFACT marker. Two failure modes detected:

      1. Header with no END_ARTIFACT anywhere after it -> abandoned
      2. Header A, then header B before A's END_ARTIFACT -> A abandoned
         (without this check, A would silently absorb B's header into
         its content, corrupting both artifacts)
    """
    starts = list(START_MARKER.finditer(conversation_text))
    if not starts:
        return []

    now = datetime.now(timezone.utc).isoformat()
    artifacts: list[VoiceArtifact] = []

    for m in starts:
        content_start = m.end()
        # find next END_ARTIFACT after this start
        end_match = END_MARKER.search(conversation_text, pos=content_start)
        if not end_match:
            artifacts.append(VoiceArtifact(
                filename=m.group("filename").strip(),
                intent=(m.group("intent") or "").strip(),
                timestamp=(m.group("timestamp") or "").strip(),
                session=(m.group("session") or "").strip(),
                content="",
                extracted_at=now,
                status="failed",
                notes="no END_ARTIFACT marker found after this header",
            ))
            continue

        # Defensive check: did another START marker appear before this END?
        # If yes, this artifact's header was abandoned -- fail it explicitly
        # rather than letting it swallow the next artifact's territory.
        next_start = START_MARKER.search(
            conversation_text,
            pos=content_start,
            endpos=end_match.start(),
        )
        if next_start:
            artifacts.append(VoiceArtifact(
                filename=m.group("filename").strip(),
                intent=(m.group("intent") or "").strip(),
                timestamp=(m.group("timestamp") or "").strip(),
                session=(m.group("session") or "").strip(),
                content="",
                extracted_at=now,
                status="failed",
                notes=("abandoned artifact header: another VOICE_ARTIFACT "
                       "header started before an END_ARTIFACT was encountered"),
            ))
            continue

        content = conversation_text[content_start:end_match.start()]
        # normalize: strip leading blank line, ensure trailing newline
        content = content.lstrip("\n").rstrip() + "\n"

        artifacts.append(VoiceArtifact(
            filename=m.group("filename").strip(),
            intent=(m.group("intent") or "").strip(),
            timestamp=(m.group("timestamp") or "").strip(),
            session=(m.group("session") or "").strip(),
            content=content,
            extracted_at=now,
        ))

    return artifacts


# ===================================================================
# MATERIALIZATION -- write extracted artifacts to disk
# ===================================================================

def materialize_artifact(art: VoiceArtifact, output_dir: Path,
                         overwrite: bool = False) -> VoiceArtifact:
    """Write artifact content to disk in output_dir/art.filename.
    Updates art.status and art.notes. Returns the same artifact."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / art.filename

    if target.exists() and not overwrite:
        art.status = "skipped"
        art.notes = f"file already exists at {target}, overwrite=False"
        return art

    try:
        target.write_text(art.content)
        art.status = "materialized"
        art.notes = f"wrote {len(art.content)} bytes to {target}"
    except Exception as e:
        art.status = "failed"
        art.notes = f"write failed: {e!r}"

    return art


def verify_artifact(art: VoiceArtifact, output_dir: Path) -> VoiceArtifact:
    """Verify the materialized file exists, has the right content,
    and (if Python) parses cleanly."""
    target = Path(output_dir) / art.filename
    if not target.exists():
        art.status = "failed"
        art.notes = f"verification: {target} does not exist"
        return art

    on_disk = target.read_text()
    if on_disk != art.content:
        art.status = "failed"
        art.notes = "verification: disk content differs from extracted content"
        return art

    if art.filename.endswith(".py"):
        try:
            import ast
            ast.parse(on_disk)
        except SyntaxError as e:
            art.status = "failed"
            art.notes = f"verification: Python syntax error: {e}"
            return art

    art.status = "verified"
    art.notes = f"verified: {len(on_disk)} bytes on disk, content matches"
    return art


# ===================================================================
# AUDIT -- full pipeline + summary report
# ===================================================================

def audit_conversation(conversation_text: str, output_dir: Path,
                       overwrite: bool = False) -> dict:
    """Full pipeline: extract -> materialize -> verify -> summarize.
    Returns a dict report suitable for printing or JSON dump."""
    artifacts = extract_artifacts(conversation_text)

    for art in artifacts:
        materialize_artifact(art, output_dir, overwrite=overwrite)
        if art.status == "materialized":
            verify_artifact(art, output_dir)

    summary = {
        "extracted":    sum(1 for a in artifacts if a.status != "skipped"),
        "materialized": sum(1 for a in artifacts if a.status == "materialized"),
        "verified":     sum(1 for a in artifacts if a.status == "verified"),
        "skipped":      sum(1 for a in artifacts if a.status == "skipped"),
        "failed":       sum(1 for a in artifacts if a.status == "failed"),
        "total":        len(artifacts),
    }

    return {
        "summary":   summary,
        "artifacts": [a.to_dict() for a in artifacts],
    }


# ===================================================================
# SESSION LOG -- persistent manifest of all bridge operations
# ===================================================================

def append_to_session_log(report: dict, log_path: Path) -> None:
    """Append an audit report to a JSON-lines session log.
    One report per line, never overwrites -- append-only ledger."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "report":    report,
    }
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ===================================================================
# SELF-TEST -- synthetic conversation, verify end-to-end pipeline
# ===================================================================

SAMPLE_VOICE_CONVERSATION = """
Earlier voice-mode exchange about building something.

Here is the first artifact I generated:

# VOICE_ARTIFACT: hello.py
# intent: simple greeting function
# timestamp: 2026-05-17T22:00:00Z
# session: test_session_001

def hello(name):
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("Kavik"))

# END_ARTIFACT

Then we talked about something else for a while.

Here is a second artifact:

# VOICE_ARTIFACT: math_helpers.py
# intent: small math utility module
# timestamp: 2026-05-17T22:05:00Z

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

# END_ARTIFACT

End of voice mode session.
"""


def _self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "artifacts"
        log = Path(td) / "session_log.jsonl"

        report = audit_conversation(SAMPLE_VOICE_CONVERSATION, out)
        append_to_session_log(report, log)

        print("=" * 60)
        print("voice_text_bridge self-test")
        print("=" * 60)
        print(f"summary: {report['summary']}")
        print()
        for a in report["artifacts"]:
            print(f"  {a['filename']:25s}  status={a['status']:12s}  "
                  f"intent={a['intent']!r}")
            print(f"    notes: {a['notes']}")
        print()

        # confirm files actually exist
        print("on-disk verification:")
        for f in sorted(out.iterdir()):
            size = f.stat().st_size
            print(f"  {f.name:25s}  {size:6d} bytes")

        print()
        print(f"session log entries: {sum(1 for _ in log.open())}")


if __name__ == "__main__":
    _self_test()
