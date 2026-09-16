#!/usr/bin/env python3
"""
feed_state_epistemology.py -- av-fdi-1. The one table, and the precedence it must reproduce.

    python integrations/gods-eye-view/06-feed-integrity/feed_state_epistemology.py        # the table
    python integrations/gods-eye-view/06-feed-integrity/feed_state_epistemology.py json   # as JSON for a JS consumer

GEV reduces a layer's getStats() to one of six feed states in
`src/data/manager.js: layerFeedState()`. The bridge tags every Primitive
with one of four epistemology grades in `sensing/processing/epi_classifier.py`.
This module joins them.

    feed state    -> epistemology, confidence cap
    ------------------------------------------------
    nominal       -> measured    1.00
    stale         -> measured    1.00 - STALE_PENALTY   (age is a covariate, not a lie)
    degraded      -> measured    0.50                    (partial group failure; what arrived is real)
    fallback      -> inferred    0.60                    (a different source stood in: adsb.lol regional, or a sim)
    loading       -> None                                (no reading yet)
    unavailable   -> None                                (no reading; never a zero)

    mode == 'sim' -> asserted    <= 1 - MOCK_PENALTY     (a model, not a measurement)

The last row is the reason the table is code and not prose: GEV folds a
simulation into 'fallback', which is the right UI state and the wrong
epistemology. A simulated traffic dot and a real aircraft from a fallback
source are both 'fallback' on the chip; only one of them was observed.
`grade()` reads `mode` before the feed state so the distinction survives.

PRECEDENCE
    `layer_feed_state()` is a line-for-line port of layerFeedState(). It is
    tested against the cases GEV ships in `src/data/manager.test.mjs`
    (tests/test_integration_crosslinks.py). If GEV changes its precedence
    the port drifts and the test says so; that is the contract.

The penalties are the bridge's own (epi_classifier.ConfidenceFactors); the
stale penalty is new and is a placeholder until a feed's age distribution
has been measured (av-fdi-4).
"""
from __future__ import annotations

import json
import re
import sys

MOCK_PENALTY = 0.40      # epi_classifier.ConfidenceFactors.mock_penalty
STALE_PENALTY = 0.25     # PLACEHOLDER pending av-fdi-4
DEGRADED_CONF = 0.50
FALLBACK_CONF = 0.60

FEED_STATES = ("nominal", "loading", "degraded", "stale", "fallback", "unavailable")
EPISTEMOLOGY = ("measured", "inferred", "derived", "asserted")

TABLE = {
    "nominal":     ("measured", 1.0),
    "stale":       ("measured", round(1.0 - STALE_PENALTY, 3)),
    "degraded":    ("measured", DEGRADED_CONF),
    "fallback":    ("inferred", FALLBACK_CONF),
    "loading":     (None, None),
    "unavailable": (None, None),
}
SIM_ROW = ("asserted", round(1.0 - MOCK_PENALTY, 3))

_GUIDANCE = ("zoom-in", "empty", "idle")
_DOWN = ("unavailable", "offline", "down", "error")
_FALLBACK_SOURCE = re.compile(r"\bfallback\b", re.I)
_ADSB_LOL = re.compile(r"\badsb\.lol\b", re.I)


def _truthy(v) -> bool:
    # JS truthiness for the fields layerFeedState() tests with `||` / `if (x)`.
    return v not in (None, False, 0, "", 0.0)


def layer_feed_state(stats: dict | None = None) -> str:
    """Port of src/data/manager.js layerFeedState(). Same precedence, same six values."""
    s = stats or {}
    status = s["status"].lower() if isinstance(s.get("status"), str) else ""
    source = f"{s.get('source') or ''} {s.get('coverage') or ''}"
    has_explicit_fallback = isinstance(s.get("fallback"), bool)
    count = s.get("count")
    has_prior = (isinstance(count, (int, float)) and count > 0) or _truthy(s.get("lastUpdate"))
    presented_error = s.get("error") or s.get("lastError") or s.get("managerRefreshError")
    if status in _DOWN:
        return "unavailable"
    if ((_truthy(presented_error) or s.get("unavailable") is True or s.get("available") is False)
            and not has_prior and status not in _GUIDANCE):
        return "unavailable"
    if _truthy(s.get("loading")):
        return "loading"
    if status in _GUIDANCE:
        return "stale" if _truthy(s.get("stale")) else "nominal"
    if (s.get("fallback") is True or status == "fallback" or s.get("mode") == "sim"
            or _FALLBACK_SOURCE.search(source)
            or (not has_explicit_fallback and _ADSB_LOL.search(source))):
        return "fallback"
    if _truthy(s.get("stale")) or status == "stale":
        return "stale"
    if (_truthy(s.get("degraded")) or _truthy(presented_error)
            or s.get("unavailable") is True or s.get("available") is False):
        return "degraded"
    return "nominal"


def grade(stats: dict | None = None) -> dict:
    """Epistemology + confidence cap for one layer's stats. `mode:'sim'` wins over feed state."""
    s = stats or {}
    state = layer_feed_state(s)
    if s.get("mode") == "sim":
        epi, conf = SIM_ROW
    else:
        epi, conf = TABLE[state]
    return {"feed_state": state, "epistemology": epi, "confidence_cap": conf,
            "simulated": s.get("mode") == "sim"}


def as_json() -> str:
    return json.dumps({"table": {k: {"epistemology": v[0], "confidence_cap": v[1]}
                                 for k, v in TABLE.items()},
                       "sim": {"epistemology": SIM_ROW[0], "confidence_cap": SIM_ROW[1]},
                       "penalties": {"mock": MOCK_PENALTY, "stale": STALE_PENALTY,
                                     "stale_is_placeholder": True}},
                      indent=1) + "\n"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "json":
        sys.stdout.write(as_json())
    else:
        print(f"{'feed state':<12} {'epistemology':<12} conf")
        for k, (e, c) in TABLE.items():
            print(f"{k:<12} {str(e):<12} {'' if c is None else c}")
        print(f"{'mode=sim':<12} {SIM_ROW[0]:<12} <= {SIM_ROW[1]}")
