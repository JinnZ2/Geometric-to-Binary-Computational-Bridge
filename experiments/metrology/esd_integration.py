"""
experiments/metrology/esd_integration.py

Adapter that wires the metrology toolkit (ELA-001 + MH-004) to the
emotion_substrate_dispatcher (ESD-001). ESD-001's cross-check functions
take pre-computed numbers (a capture magnitude, a label string); the
metrology modules COMPUTE those numbers from concrete signals.

This adapter is the bridge:

  CaptureSignal[]            -> InstitutionalCaptureDetector.read()
                             -> CaptureReading.overall_score
                             -> ESD-001.cross_check_with_capture_detector

  AuditSignal                -> empathy_layer_audit.audit()
                             -> AuditResult.severity + failure_modes
                             -> richer label-independence verdict than
                                ESD-001's basic verify_label_independence
                                (which only checks the cultural_label_optional
                                field) -- this version inspects the actual
                                measurement layer.

Usage:

    from emotion_substrate_dispatcher import dispatch_emotional
    from metrology.esd_integration import (
        verify_dispatch_with_metrology, default_capture_detector,
    )

    plan = dispatch_emotional(my_pattern)
    ok, msg = verify_dispatch_with_metrology(
        plan,
        capture_signals=my_observed_capture_signals,   # list[CaptureSignal]
        audit_signal=my_observed_audit_signal,          # AuditSignal or None
    )
    if not ok:
        # hold for review -- the dispatch decision may be corrupted
        ...

License: CC0
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

# add experiments/ to sys.path so we can reach emotion_substrate_dispatcher
_EXP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _EXP_ROOT not in sys.path:
    sys.path.insert(0, _EXP_ROOT)

# add experiments/metrology/ so we can reach sibling modules
_MET_ROOT = os.path.dirname(os.path.abspath(__file__))
if _MET_ROOT not in sys.path:
    sys.path.insert(0, _MET_ROOT)

from emotion_substrate_dispatcher import (
    EmotionalDispatchPlan, cross_check_with_capture_detector,
    verify_label_independence,
)
from measurement_honesty import (
    InstitutionalCaptureDetector, CaptureSignal, CapturePressure,
    CaptureReading,
)
from empathy_layer_audit import (
    AuditSignal, AuditResult, audit, FailureMode,
)


def default_capture_detector() -> InstitutionalCaptureDetector:
    """Standard alert/critical thresholds (0.3 / 0.6 per upstream defaults)."""
    return InstitutionalCaptureDetector()


@dataclass
class MetrologyVerdict:
    """Combined verdict from both metrology checks + ESD-001 self-check."""
    overall_ok:          bool
    capture_score:       float
    audit_severity:      float
    audit_failure_modes: list[str] = field(default_factory=list)
    reasons:             list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (f"MetrologyVerdict(ok={self.overall_ok}, "
                f"capture={self.capture_score:.2f}, "
                f"audit_severity={self.audit_severity:.2f}, "
                f"failures={self.audit_failure_modes})")


def verify_dispatch_with_metrology(
        plan: EmotionalDispatchPlan,
        capture_signals: list[CaptureSignal] | None = None,
        audit_signal:    AuditSignal | None = None,
        detector:        InstitutionalCaptureDetector | None = None,
) -> tuple[bool, MetrologyVerdict]:
    """Run both metrology checks against an ESD-001 dispatch plan.

    capture_signals: observed institutional pressures on the measurement
                     system; if None, the capture check is skipped.
    audit_signal:    the AuditSignal describing how this pattern was
                     measured; if None, falls back to ESD-001's basic
                     verify_label_independence (cultural_label field only).
    detector:        injectable InstitutionalCaptureDetector; if None,
                     uses default_capture_detector().

    Returns (overall_ok, MetrologyVerdict). overall_ok is False if EITHER
    capture is above-threshold-with-low-dispatch-gap OR the audit found
    label-collapse failure modes.
    """
    detector = detector or default_capture_detector()
    verdict  = MetrologyVerdict(overall_ok=True, capture_score=0.0, audit_severity=0.0)

    # --- check 1: institutional capture (MH-004) --------------------------
    if capture_signals:
        reading = detector.read(capture_signals)
        verdict.capture_score = reading.overall_score
        cap_ok, cap_msg = cross_check_with_capture_detector(
            plan, reading.overall_score
        )
        if not cap_ok:
            verdict.overall_ok = False
            verdict.reasons.append(f"capture: {cap_msg}")

    # --- check 2: label-collapse audit (ELA-001) --------------------------
    if audit_signal is not None:
        audit_result = audit(audit_signal)
        verdict.audit_severity      = audit_result.severity
        verdict.audit_failure_modes = [fm.value for fm in audit_result.failure_modes]
        if audit_result.severity > 0.3 or audit_result.failure_modes:
            verdict.overall_ok = False
            verdict.reasons.append(
                f"audit: severity={audit_result.severity:.2f}, "
                f"failure_modes={verdict.audit_failure_modes}"
            )
    else:
        # fallback to ESD-001's basic check (cultural_label_optional only)
        basic_ok, basic_msg = verify_label_independence(plan)
        if not basic_ok:
            verdict.overall_ok = False
            verdict.reasons.append(f"basic: {basic_msg}")

    return verdict.overall_ok, verdict


# ============================================================================
# SELF-TEST -- run a dispatch and exercise both checks against it
# ============================================================================

def _self_test() -> None:
    from emotion_substrate_dispatcher import (
        dispatch_emotional, demo_rapid_threat, demo_long_coherence_loss,
    )

    print("=" * 72)
    print("esd_integration self-test")
    print("=" * 72)

    # --- scenario A: clean dispatch, no capture, no label corruption -------
    print("\n[A] clean field observation -- no capture, no audit corruption")
    plan_a = dispatch_emotional(demo_rapid_threat())
    ok_a, v_a = verify_dispatch_with_metrology(
        plan_a,
        capture_signals=[
            CaptureSignal(CapturePressure.PEER_CONFORMITY, 0.05,
                          "casual field observation, no funding tie"),
        ],
        audit_signal=AuditSignal(
            label_used="(none)", label_source_era="(none)",
            activation_pattern=[0.5, 0.6, 0.4],
            function_described=True, substrate_specified=True,
            used_to_steer=False, cross_temporal_test=True,
            cross_substrate_test=True, return_to_baseline=True,
        ),
    )
    print(f"  ok={ok_a}   {v_a}")
    for r in v_a.reasons:
        print(f"    reason: {r}")

    # --- scenario B: high capture + label collapse ------------------------
    print("\n[B] high institutional capture + label-as-signal collapse")
    plan_b = dispatch_emotional(demo_long_coherence_loss())
    ok_b, v_b = verify_dispatch_with_metrology(
        plan_b,
        capture_signals=[
            CaptureSignal(CapturePressure.GRANT_CYCLE, 0.85,
                          "study results steered toward renewable funding",
                          "selected metrics that justify continued funding"),
            CaptureSignal(CapturePressure.PUBLICATION_NARRATIVE, 0.70,
                          "framing optimized for citability",
                          "labels chosen for memetic carry"),
        ],
        audit_signal=AuditSignal(
            label_used="grief", label_source_era="2024_english_internet",
            activation_pattern=[0.5, 0.6, 0.7, 0.8],
            function_described=False, substrate_specified=False,
            used_to_steer=True, cross_temporal_test=False,
            cross_substrate_test=False, return_to_baseline=False,
        ),
    )
    print(f"  ok={ok_b}   {v_b}")
    for r in v_b.reasons:
        print(f"    reason: {r}")

    print()
    print("=" * 72)
    print("WIRING COMPLETE")
    print("  ELA-001 + MH-004 metrology checks now callable as one verdict")
    print("  against any ESD-001 dispatch plan.")
    print("=" * 72)


if __name__ == "__main__":
    _self_test()
