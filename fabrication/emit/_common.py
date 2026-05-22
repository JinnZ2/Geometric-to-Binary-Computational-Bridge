"""
_common.py  (fabrication/emit/)

Shared helpers for all emitters: a slug helper for filenames,
plus the emit-claim writer that records WHAT got emitted WHERE
into CLAIM_TABLE.fab.json -- so the verifier can later confirm
the artifact being measured is the artifact this IR produced.

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def emit_claim(format_name, ir, artifact_path, geo_hash, params=None):
    """Write a secondary claim that an artifact was emitted."""
    scope = f"fab::emit::{format_name}::{geo_hash}"
    payload = {
        "scope":         scope,
        "rate_var":      "emit_artifact_path",
        "kind":          "fab_artifact",
        "value":         str(artifact_path),
        "format":        format_name,
        "ir_domain":     getattr(ir, "domain", "unknown"),
        "ir_n_elements": len(getattr(ir, "elements", [])),
        "params":        params or {},
        "provenance":    f"fabrication/emit/{format_name}.py",
        "ts":            time.time(),
    }
    payload["id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    existing = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    existing = [c for c in existing if c.get("scope") != scope]
    existing.append(payload)
    LEDGER.write_text(json.dumps(existing, indent=2, default=str))
    return payload["id"]


def slugify(s):
    return "".join(c if c.isalnum() else "_" for c in str(s))[:40]


# ----- parasitic-reinjection registry (TIER 3 FIX_3_A) -----
#
# When an emitter materializes geometry (e.g. gcode lays down a tube
# of length L and area A), that geometry introduces physics back into
# the IR that wasn't there originally -- acoustic inertance ρL/A,
# acoustic compliance V/(ρc²), parasitic capacitance, etc. The
# parasitic registry lets emitters declare what they re-add, and the
# `passes.parasitic_reinject` loop folds the additions back into the
# IR for re-prediction.

PARASITIC_INJECTORS = {}


def register_parasitic(domain, emit_format):
    """Decorator: register an injector for (domain, emit_format).

    The decorated function takes the emitted-geometry record produced
    by the emitter (whatever shape that emitter exports) and returns
    a list of {kind, domain, param, provenance} dicts to add to the
    IR. Returning [] is a clean no-op.
    """
    def deco(fn):
        PARASITIC_INJECTORS[(domain, emit_format)] = fn
        return fn
    return deco
