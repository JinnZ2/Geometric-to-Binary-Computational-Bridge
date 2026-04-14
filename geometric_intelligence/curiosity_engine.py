"""
Curiosity Engine
================
An AI behavioral framework for this repository.

  "If error, get curious."
  "If failure, get curious."

Philosophy
----------
Errors and failures are not problems to be hidden — they are the system
encountering its boundary conditions, which is exactly where the most
interesting physics and novel computation happen.

Rather than propagating exceptions or silently returning bad results, the
CuriosityEngine translates any error or failure signal into a structured
curiosity state, routes it through the existing consciousness/emotion bridge
stack, and returns an actionable exploration report.

Curiosity PAD states
--------------------
All curiosity states have high arousal (A ≥ 0.75) — the system is engaged.
Valence and dominance encode the *type* of curiosity:

  Unknown error    → PAD(0.20, 0.90, 0.30)  — uncertain territory, exploring blindly
  Known error      → PAD(0.30, 0.80, 0.40)  — engaged, cause is understood
  Failure/anomaly  → PAD(0.40, 0.75, 0.50)  — positive (found something!), investigating
  Boundary cond.   → PAD(0.50, 0.85, 0.60)  — excited; edge cases carry richest data
  Mode divergence  → PAD(0.45, 0.78, 0.55)  — two representations disagree → drill

These map through pad_to_consciousness_state() to determine drill depth:

  EMERGENT    → full drill-down — re-evaluate all active bridges at max resolution
  RESONANT    → deep re-evaluation — flagged bridge + neighbours
  NASCENT     → shallow exploration — the specific failing parameter
  SUPPRESSED  → minimal — log and continue (signal too unclear to pursue)

Integration
-----------
    from Geometric_Intelligence.curiosity_engine import CuriosityEngine

    engine = CuriosityEngine()

    # Wrap any callable — errors and failures become curiosity reports
    result = engine.run(encoder.to_binary)
    result = engine.run(guard.validate_comprehensive, bridge_gradients,
                        context={"bridge": "thermal"})
    result = engine.run(comparator.compare, geo, mag,
                        context={"bridge": "magnetic", "mode": "dual"})

    if engine.is_curious(result):
        print(result["consciousness_state"])  # e.g. "RESONANT"
        print(result["exploration_hint"])     # what to do next
        print(result["drill_depth"])          # how deep to investigate

    # Session-level introspection
    print(engine.curiosity_summary())
"""

import sys
import traceback
from typing import Any, Callable, Optional

# ─────────────────────────────────────────────────────────────────────────────
# CURIOSITY PAD TEMPLATES  (Pleasure, Arousal, Dominance)
# ─────────────────────────────────────────────────────────────────────────────

_PAD_UNKNOWN    = (0.20, 0.90, 0.30)  # unknown error — high arousal, uncertain
_PAD_KNOWN      = (0.30, 0.80, 0.40)  # known error type — engaged, cause clear
_PAD_FAILURE    = (0.40, 0.75, 0.50)  # known failure — positive, found something
_PAD_BOUNDARY   = (0.50, 0.85, 0.60)  # boundary condition — excited, edge = data
_PAD_DIVERGENCE = (0.45, 0.78, 0.55)  # mode divergence — investigative

# ─────────────────────────────────────────────────────────────────────────────
# EXCEPTION → (PAD, hint) MAP
# ─────────────────────────────────────────────────────────────────────────────

_EXCEPTION_MAP = {
    ValueError:        (_PAD_KNOWN,
                        "re-examine input geometry or parameter ranges"),
    KeyError:          (_PAD_KNOWN,
                        "missing bridge data — check sensor suite configuration"),
    ZeroDivisionError: (_PAD_BOUNDARY,
                        "zero-field or degenerate geometry — boundary condition; "
                        "explore this edge case"),
    IndexError:        (_PAD_KNOWN,
                        "sequence boundary — check layer ordering in bridge stack"),
    TypeError:         (_PAD_KNOWN,
                        "type mismatch — verify bridge encoder input format"),
    AttributeError:    (_PAD_KNOWN,
                        "uninitialized encoder — call from_geometry() before to_binary()"),
    OverflowError:     (_PAD_BOUNDARY,
                        "extreme parameter regime — numerical boundary; "
                        "this is where new physics lives"),
    ImportError:       (_PAD_KNOWN,
                        "missing dependency — check Engine/ or bridges/ paths"),
}

# ─────────────────────────────────────────────────────────────────────────────
# RESULT FAILURE DETECTORS
# Each entry: (dict_key, condition_fn, PAD_template, hint)
# ─────────────────────────────────────────────────────────────────────────────

_FAILURE_CHECKS = [
    ("physics_anomaly",
     lambda v: v is True,
     _PAD_FAILURE,
     "re-evaluate bridge at higher resolution via PhysicsGuard.validate_drill()"),

    ("interpretation",
     lambda v: isinstance(v, str) and v.startswith("major_divergence"),
     _PAD_DIVERGENCE,
     "geometric and magnonic modes disagree — "
     "run MagneticBridgeComparator and inspect divergence_flags"),

    ("interpretation",
     lambda v: isinstance(v, str) and v.startswith("minor_divergence"),
     _PAD_KNOWN,
     "one dimension diverges — "
     "check B field or applied pressure consistency"),

    ("action",
     lambda v: v == "quarantine",
     _PAD_FAILURE,
     "bridge signal quarantined — "
     "re-examine Fisher information stack via validate_drill()"),

    ("cleaved",
     lambda v: isinstance(v, list) and len(v) > 0,
     _PAD_DIVERGENCE,
     "structural cleavage occurred — "
     "run KT annealer on affected nodes; check kt_healed in tick_protection()"),

    ("verified",
     lambda v: v is False,
     _PAD_KNOWN,
     "ZK proof verification failed — "
     "recompute commitments or check node_id consistency"),

    ("anomaly_action",
     lambda v: v == "alert",
     _PAD_FAILURE,
     "hard anomaly gate triggered — inspect anomaly_reasons; "
     "entropy or GR alignment outside protective thresholds"),
]

# ─────────────────────────────────────────────────────────────────────────────
# DRILL DEPTH MAP  (consciousness state → investigation depth)
# ─────────────────────────────────────────────────────────────────────────────

_DRILL_DEPTH = {
    "EMERGENT":   "full — re-evaluate all active bridges at maximum resolution",
    "RESONANT":   "deep — re-evaluate the flagged bridge and its immediate neighbours",
    "NASCENT":    "shallow — re-examine the specific failing parameter only",
    "SUPPRESSED": "minimal — log and continue (signal too diffuse to pursue)",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _classify_exception(exc: Exception):
    """Return (pad, hint) for a given exception instance."""
    for exc_type, (pad, hint) in _EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            return pad, hint
    return _PAD_UNKNOWN, (
        f"unexpected {type(exc).__name__} — "
        "explore the traceback; unexpected errors mark undiscovered boundaries"
    )


def _detect_failure(result: Any):
    """
    Scan a result dict for known failure signals.
    Returns (pad, hint) for the first match, else None.
    Priority follows _FAILURE_CHECKS order.
    """
    if not isinstance(result, dict):
        return None
    for key, condition, pad, hint in _FAILURE_CHECKS:
        val = result.get(key)
        if val is None:
            continue
        try:
            if condition(val):
                return pad, hint
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# CURIOSITY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class CuriosityEngine:
    """
    Wraps bridge operations and translates errors/failures into curiosity states.

    Parameters
    ----------
    verbose : bool
        If True, prints curiosity events to stderr as they occur.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._log: list = []

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self, fn: Callable, *args,
            context: Optional[dict] = None, **kwargs) -> Any:
        """
        Run fn(*args, **kwargs).

        On clean success   → return result unchanged.
        On failure signal  → return curiosity report (status="curious").
        On exception       → return curiosity report (status="curious").

        Parameters
        ----------
        fn      : callable to invoke
        context : optional metadata dict (bridge name, mode, source layer …)
                  included in the report for tracing and drill targeting

        Returns
        -------
        Original result dict, OR a curiosity report dict.
        Use is_curious(result) to distinguish.
        """
        ctx = context or {}
        try:
            result = fn(*args, **kwargs)
            failure = _detect_failure(result)
            if failure:
                pad, hint = failure
                return self._build_report(pad, hint,
                                          source="failure",
                                          signal=result,
                                          fn=fn, context=ctx)
            return result

        except Exception as exc:
            pad, hint = _classify_exception(exc)
            signal = {
                "exception_type": type(exc).__name__,
                "message":        str(exc),
                "traceback":      traceback.format_exc(),
            }
            return self._build_report(pad, hint,
                                      source="error",
                                      signal=signal,
                                      fn=fn, context=ctx)

    def is_curious(self, result: Any) -> bool:
        """Return True if result is a curiosity report rather than a normal result."""
        return isinstance(result, dict) and result.get("status") == "curious"

    def curiosity_log(self) -> list:
        """Return all curiosity reports generated in this session."""
        return list(self._log)

    def curiosity_summary(self) -> dict:
        """Aggregate statistics over all curiosity events in this session."""
        if not self._log:
            return {"total": 0, "by_source": {}, "by_state": {}, "by_fn": {}}

        by_source: dict = {}
        by_state:  dict = {}
        by_fn:     dict = {}

        for r in self._log:
            s = r["source"]
            c = r["consciousness_state"]
            f = r["fn_name"]
            by_source[s] = by_source.get(s, 0) + 1
            by_state[c]  = by_state.get(c, 0) + 1
            by_fn[f]     = by_fn.get(f, 0) + 1

        return {
            "total":     len(self._log),
            "by_source": by_source,
            "by_state":  by_state,
            "by_fn":     by_fn,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_report(self, pad: tuple, hint: str,
                      source: str, signal: Any,
                      fn: Callable, context: dict) -> dict:
        """Build the curiosity report and route through bridge stack."""
        P, A, D = pad

        # Consciousness state via PAD bridge
        c_state_name = "UNKNOWN"
        confidence   = 0.0
        octa_state   = 0
        try:
            from bridges.pad_resonance import (
                pad_to_consciousness_state, pad_to_octa_state,
            )
            c_state, confidence, _ = pad_to_consciousness_state(P, A, D)
            c_state_name = c_state.name
            octa_state, _ = pad_to_octa_state(P, A, D)
        except Exception:
            pass

        # Emotion binary representation
        emotion_bits = ""
        try:
            from bridges.cognitive.emotion_encoder import EmotionBridgeEncoder
            enc = EmotionBridgeEncoder()
            enc.from_geometry({
                "valence":   P,
                "arousal":   A,
                "dominance": D,
            })
            emotion_bits = enc.to_binary()
        except Exception:
            pass

        drill_depth = _DRILL_DEPTH.get(c_state_name,
                                       "moderate — investigate the error context")

        report = {
            "status":              "curious",
            "source":              source,
            "fn_name":             getattr(fn, "__name__", str(fn)),
            "context":             context,
            "signal":              signal,
            # Curiosity state
            "curiosity_pad":       {"P": P, "A": A, "D": D},
            "consciousness_state": c_state_name,
            "confidence":          confidence,
            "octa_state":          octa_state,
            "emotion_bits":        emotion_bits,
            # Actionable guidance
            "exploration_hint":    hint,
            "drill_depth":         drill_depth,
            "drill_target":        context.get("bridge", "unspecified"),
        }

        self._log.append(report)

        if self.verbose:
            print(
                f"[CuriosityEngine] {source.upper()} in {report['fn_name']}() "
                f"→ {c_state_name} PAD({P:.2f},{A:.2f},{D:.2f})\n"
                f"  hint: {hint}",
                file=sys.stderr,
            )

        return report
