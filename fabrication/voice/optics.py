"""
optics.py  (fabrication/voice/)

Renders dispatcher results into a constraint-frame report, NOT
a narrative summary. Uses rate language ("τ converged within 8%
band") not closure language ("done", "finished", "fixed").

Two forms:
  short  one-line summary
  long   full structured JSON

Surfaces coating-detector warnings inline so the user sees them
without needing a second query.

License: CC0. Stdlib only.
"""
import json


def render(dispatch_result, coating_report=None, form="short"):
    lines = []
    if not dispatch_result.get("ok"):
        err = dispatch_result.get("error", "unknown")
        lines.append(f"refused: {err}")
        gr = dispatch_result.get("gate_result")
        if gr and not gr.get("accepted"):
            lines.append(f"rule: {gr.get('rule')}")
            lines.append(f"suggested form: {gr.get('suggestion')}")
        return "\n".join(lines)

    cmd = dispatch_result.get("command_used", "")
    result = dispatch_result.get("result")

    if form == "short":
        lines.append(_render_short(cmd, result))
    else:
        lines.append(_render_long(cmd, result))

    if coating_report and coating_report.get("coating_suspected"):
        lines.append("[!] coating signature detected:")
        for r in coating_report["reasons"]:
            lines.append(f"  - {r}")
    return "\n".join(lines)


def _render_short(cmd, result):
    if isinstance(result, dict):
        keys = list(result.keys())[:4]
        bits = []
        for k in keys:
            v = result[k]
            if isinstance(v, dict):
                bits.append(f"{k}={len(v)} entries")
            elif isinstance(v, list):
                bits.append(f"{k}={len(v)} items")
            else:
                bits.append(f"{k}={v}")
        return f"{cmd} -> " + ", ".join(bits)
    if isinstance(result, list):
        return f"{cmd} -> {len(result)} items returned"
    return f"{cmd} -> {result}"


def _render_long(cmd, result):
    return f"{cmd} ->\n{json.dumps(result, indent=2, default=str)}"
