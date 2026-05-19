"""
baseline.py  (fabrication/verify/)

Baseline capture, storage, and lookup.

A baseline is the phone's own transfer function -- speaker
coloration, mic roll-off, case resonance -- captured by recording
the sweep with NO resonator present. Reusable across many
resonator measurements as long as: same phone, same volume, same
sample rate, same approximate speaker-mic geometry.

Stored separately from the substrate-claim ledger because
baselines have their own validity scope and shouldn't pollute the
physics predictions.

License: CC0. Stdlib only.
"""
import json
import time
import hashlib
from pathlib import Path

from .transfer import transfer_function


BASELINES = Path("CLAIM_TABLE.fab.baselines.json")


def _baseline_id(meta: dict) -> str:
    """Stable hash of the conditions that must match for reuse.
    Changing ANY of these fields -> new baseline_id -> recapture."""
    keyed = {k: meta[k] for k in
             ("device_tag", "volume_setting", "sample_rate",
              "geometry_tag", "sweep_f1", "sweep_f2", "sweep_duration")}
    return hashlib.sha256(
        json.dumps(keyed, sort_keys=True).encode()
    ).hexdigest()[:16]


def capture_baseline(sweep_wav, baseline_wav, meta):
    """
    Compute and store the phone's own transfer function.
      sweep_wav    : the reference sweep that was played
      baseline_wav : phone recording with NO resonator present
      meta         : dict describing the capture conditions
    Returns the baseline_id and writes the spectrum to disk.
    """
    freqs, mag, phase, coh = transfer_function(sweep_wav, baseline_wav)
    bid = _baseline_id(meta)

    entry = {
        "id":         bid,
        "freqs":      freqs,
        "mag":        mag,
        "phase":      phase,
        "coh":        coh,
        "meta":       meta,
        "ts":         time.time(),
        "provenance": "fabrication/verify/baseline.py",
    }

    existing = json.loads(BASELINES.read_text()) if BASELINES.exists() else []
    # replace any prior baseline with same id (re-captures supersede)
    existing = [e for e in existing if e["id"] != bid]
    existing.append(entry)
    BASELINES.write_text(json.dumps(existing, indent=2))
    return bid


def load_baseline(bid):
    if not BASELINES.exists():
        raise FileNotFoundError("No baselines captured yet.")
    for e in json.loads(BASELINES.read_text()):
        if e["id"] == bid:
            return e
    raise KeyError(f"baseline id {bid} not found")


def list_baselines():
    if not BASELINES.exists():
        return []
    return [{"id": e["id"], "meta": e["meta"], "ts": e["ts"]}
            for e in json.loads(BASELINES.read_text())]
