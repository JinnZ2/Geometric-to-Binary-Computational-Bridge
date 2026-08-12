#!/usr/bin/env python3
"""
claim_playground/claim_tester.py
earth-systems-physics
CC0 — No Rights Reserved

T1–T4 Reality Test Harness for evaluating claims against:
  T1: Thermodynamic Closure
  T2: Cascade Exposure
  T3: Scale Invariance / Zoom
  T4: Ontology Translation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum

from claim_playground.claim_schema import (
    Claim, ClaimVersion, ScopeLevel, GeometryType, OntologyType,
    CLAIM_REGISTRY
)


# =============================================================================
# Enums & Dataclasses
# =============================================================================

class TestVerdict(Enum):
    __test__ = False  # prevent pytest collection
    HOLDS = "HOLDS"
    DEGRADES = "DEGRADES"
    BREAKS = "BREAKS"

@dataclass
class DiagnosticReport:
    claim_id: str
    claim_name: str
    claim_statement: str
    verdict: TestVerdict
    overall_confidence: float
    failures: List[str] = field(default_factory=list)
    modifications: List[str] = field(default_factory=list)
    # Detailed test outputs
    thermodynamic_account: Dict[str, Any] = field(default_factory=dict)
    cascade_footprint: Dict[str, Any] = field(default_factory=dict)
    scale_profile: Dict[str, str] = field(default_factory=dict)
    ontological_shifts: Dict[str, Any] = field(default_factory=dict)
    failure_mechanisms: List[str] = field(default_factory=list)
    recommended_modifications: List[str] = field(default_factory=list)


# =============================================================================
# Main Tester Class
# =============================================================================

class ClaimTester:
    def __init__(self,
                 assumption_validator_active: bool = True,
                 substrate_audit_active: bool = True,
                 verbose: bool = False):
        self.assumption_validator_active = assumption_validator_active
        self.substrate_audit_active = substrate_audit_active
        self.verbose = verbose

    # -------------------------------------------------------------------------
    # Helper: get a claim from the registry
    # -------------------------------------------------------------------------
    def _get_claim(self, claim_id: str) -> Optional[Claim]:
        return CLAIM_REGISTRY.get(claim_id)

    # -------------------------------------------------------------------------
    # T1: THERMODYNAMIC CLOSURE
    # -------------------------------------------------------------------------
    def _test_thermodynamic_closure(self,
                                    claim: Claim,
                                    system_context: Optional[Dict]) -> Dict[str, Any]:
        """
        Audit: Does the claim account for energy/waste balances?
        Returns detailed thermodynamic accounting.
        """
        input_energy = float(system_context.get("input_energy_joules", 100.0)) if system_context else 100.0
        externalized_waste = float(system_context.get("externalized_waste_entropy", 10.0)) if system_context else 10.0
        hidden_subsidies = float(system_context.get("hidden_subsidies", 0.0)) if system_context else 0.0

        total_leak = externalized_waste + hidden_subsidies
        net_efficiency = 1.0 - (total_leak / max(input_energy, 1e-9))
        is_closed = net_efficiency >= 0.8

        leakage_points = []
        if externalized_waste > 0:
            leakage_points.append("Externalized waste/heat stream not accounted in claim")
        if hidden_subsidies > 0:
            leakage_points.append("Hidden energy subsidies or deferred entropy costs")
        if system_context and system_context.get("manual_override_active"):
            leakage_points.append("Human labor absorbing system friction (accommodation masking)")
        if system_context and system_context.get("decayed_substrate"):
            leakage_points.append("Material decay / substrate degradation externalized")

        return {
            "passed": is_closed,
            "net_efficiency": net_efficiency,
            "energy_debt_detected": not is_closed,
            "externalized_waste_fraction": total_leak / max(input_energy, 1e-9),
            "hidden_subsidies_detected": hidden_subsidies > 0,
            "leakage_points": leakage_points,
            "input_energy": input_energy,
            "total_leak": total_leak,
        }

    # -------------------------------------------------------------------------
    # T2: CASCADE EXPOSURE
    # -------------------------------------------------------------------------
    def _test_cascade_exposure(self,
                               claim: Claim,
                               system_context: Optional[Dict] = None,
                               depth: int = 3) -> Dict[str, Any]:
        """
        Audit: What secondary and tertiary effects occur when this claim
        is applied at scale? Checks for feedback loops and coupled propagation.
        """
        cascade_map = {
            1: "Direct intervention successful",
            2: "Local depletion or strain on adjacent nodes",
            3: "Feedback loop destabilizes broader substrate",
        }

        affected_loops = []
        coupled_propagation = []
        unaccounted_effects_found = False

        # Check system context flags for known cascade failure modes
        if system_context:
            if system_context.get("unaccounted_cascades"):
                unaccounted_effects_found = True
                affected_loops.append({
                    "name": "unaccounted_cascades",
                    "description": "Systemic cascade blindness: 2nd/3rd order effects ignored",
                    "severity": "HIGH",
                })
            if system_context.get("false_positive_trigger"):
                unaccounted_effects_found = True
                affected_loops.append({
                    "name": "signal_noise_inversion",
                    "description": "Signal/noise inversion: terrain vibration treated as collision",
                    "severity": "HIGH",
                })
            if system_context.get("relational_arity_missing"):
                unaccounted_effects_found = True
                affected_loops.append({
                    "name": "arity_flattening",
                    "description": "3-place relational reality flattened to 1-place scalar",
                    "severity": "MEDIUM",
                })
            if system_context.get("unserviced_pipe_present"):
                unaccounted_effects_found = True
                affected_loops.append({
                    "name": "structural_lockin",
                    "description": "Policy metric forcing physical reality into compliant records",
                    "severity": "HIGH",
                })

        # Check coupled claims for propagation risk
        if claim.couplings:
            for cid in claim.couplings:
                coupled = self._get_claim(cid)
                if coupled:
                    coupled_propagation.append({
                        "coupled_id": cid,
                        "name": coupled.name,
                        "statement_preview": coupled.current().statement[:60] + "..."
                    })

        # Risk scoring
        risk_score = 0.1
        if affected_loops:
            risk_score += 0.25 * len(affected_loops)
        if coupled_propagation:
            risk_score += 0.15 * len(coupled_propagation) / max(len(claim.couplings), 1)
        risk_score = min(1.0, risk_score)

        if risk_score > 0.3:
            unaccounted_effects_found = True

        return {
            "cascade_depth_checked": depth,
            "unaccounted_effects_found": unaccounted_effects_found,
            "cascade_map": cascade_map,
            "affected_feedback_loops": affected_loops,
            "coupled_propagation": coupled_propagation,
            "risk_score": risk_score,
        }

    # -------------------------------------------------------------------------
    # T3: SCALE INVARIANCE / ZOOM
    # -------------------------------------------------------------------------
    def _test_scale_invariance(self, claim: Claim) -> Dict[str, Any]:
        """
        Audit: Test the claim across Micro, Meso, Macro, Cosmic, Contextual scales.
        Returns per-scale status: HOLDS, DEGRADES, or BREAKS.
        """
        scale_reasons = {
            ScopeLevel.MICRO: {
                "degradation": 0.6,
                "reason": "Quantum/fluctuation effects undermine macroscopic deterministic assumptions",
                "break_reason": "Atomic-scale interactions dominate; classical assumptions shatter",
            },
            ScopeLevel.MESO: {
                "degradation": 0.2,
                "reason": "Uncalibrated operational friction emerges",
                "break_reason": "System complexity exceeds computational tractability",
            },
            ScopeLevel.MACRO: {
                "degradation": 0.8,
                "reason": "Non-linear feedback loops and gravitational/field effects dominate",
                "break_reason": "Global coupling invalidates local assumptions",
            },
            ScopeLevel.COSMIC: {
                "degradation": 0.95,
                "reason": "Relativistic and cosmological effects dominate",
                "break_reason": "Spacetime curvature and dark energy effects invalidate flat-space assumptions",
            },
            ScopeLevel.CONTEXTUAL: {
                "degradation": 0.3,
                "reason": "Context-dependent variance introduces noise",
                "break_reason": "Non-stationary conditions make the claim untestable",
            }
        }

        results = {}
        for scope in ScopeLevel:
            if scope in claim.current().scope_valid:
                results[scope.value] = {
                    "status": "HOLDS",
                    "degradation": 0.0,
                    "reason": "Explicitly within claimed boundary",
                }
            else:
                reason_data = scale_reasons.get(scope, {
                    "degradation": 0.5,
                    "reason": "Untested at this scale",
                })
                deg = reason_data.get("degradation", 0.5)
                if deg > 0.7:
                    status = "BREAKS"
                elif deg > 0.3:
                    status = "DEGRADES"
                else:
                    status = "DEGRADES"
                results[scope.value] = {
                    "status": status,
                    "degradation": deg,
                    "reason": reason_data.get("reason", "Unknown scale effect"),
                }

        return results

    # -------------------------------------------------------------------------
    # T4: ONTOLOGY TRANSLATION
    # -------------------------------------------------------------------------
    def _translate_ontology(self, claim: Claim) -> Dict[str, Any]:
        """
        Re-interprets the claim under different ontological frames.
        Detects bias and translation friction.
        """
        assumed = claim.current().ontology_assumed
        translations = {}

        # Static / Substance frame
        translations["static"] = {
            "interpretation": f"Re-frames claim as isolated snapshot: {claim.current().statement[:80]}...",
            "validity": "High in isolated lab conditions; low in open dynamic fields.",
            "score": 0.7 if assumed == OntologyType.SUBSTANCE else 0.4,
            "bias_detected": ["Static frame assumption"] if assumed != OntologyType.SUBSTANCE else [],
        }

        # Process frame
        translations["process"] = {
            "interpretation": "Re-frames claim as interrupted or directed energy flow.",
            "validity": "Exposes hidden friction and rate-limiting bottlenecks.",
            "score": 0.9 if assumed in (OntologyType.PROCESS, OntologyType.FIELD) else 0.5,
            "bias_detected": [] if assumed in (OntologyType.PROCESS, OntologyType.FIELD)
                              else ["Static-to-process translation friction"],
        }

        # Field / Relational frame
        translations["field"] = {
            "interpretation": "Re-frames claim within relational constraints and field forces.",
            "validity": "Reveals coupling and hidden constraints.",
            "score": 0.85 if assumed == OntologyType.FIELD else 0.4,
            "bias_detected": [] if assumed == OntologyType.FIELD
                             else ["Missing boundary condition detection"],
        }

        # Pre-linguistic / Direct Substrate
        translations["pre_linguistic"] = {
            "interpretation": "Direct physical feedback (temperature, resistance, thermal limits).",
            "validity": "Absolute reference frame – ignores human institutional naming entirely.",
            "score": 0.95 if assumed == OntologyType.PRE_LINGUISTIC else 0.3,
            "bias_detected": [] if assumed == OntologyType.PRE_LINGUISTIC
                             else ["Institutional naming strips substrate detail"],
        }

        # Institutional frame
        translations["institutional"] = {
            "interpretation": "Re-frames claim within credentialing, measurement, and compliance frameworks.",
            "validity": "High in bureaucratic contexts; low in direct substrate interaction.",
            "score": 0.8 if assumed == OntologyType.INSTITUTIONAL else 0.5,
            "bias_detected": ["Gatekeeping filters", "Credentialing requirements"]
                             if assumed != OntologyType.INSTITUTIONAL else [],
        }

        return translations

    # -------------------------------------------------------------------------
    # MAIN EVALUATE METHOD
    # -------------------------------------------------------------------------
    def evaluate(self,
                 claim_id: str,
                 system_context: Optional[Dict] = None) -> DiagnosticReport:
        """
        Runs all 4 mandatory tests and returns the consolidated Diagnostic Report.
        """
        claim = self._get_claim(claim_id)
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found in registry")

        failures = []
        modifications = []
        failure_mechanisms = []
        recommended_modifications = []

        # ---- T1: Thermodynamic closure ----
        t1 = self._test_thermodynamic_closure(claim, system_context)
        if not t1["passed"]:
            failures.append("T1 Violation: Claim externalizes thermodynamic costs (unbalanced budget).")
            failure_mechanisms.append(f"T1: net_efficiency={t1['net_efficiency']:.2%}, leakage={t1['leakage_points']}")
            recommended_modifications.append(
                "Include environmental waste/entropy production directly into the equations."
            )

        # ---- T2: Cascade exposure ----
        t2 = self._test_cascade_exposure(claim, system_context)
        if t2["unaccounted_effects_found"] and t2["risk_score"] > 0.3:
            failures.append(
                f"T2 Violation: Unmapped secondary/tertiary cascade risks (risk score {t2['risk_score']:.1%})."
            )
            failure_mechanisms.append(f"T2: risk_score={t2['risk_score']:.2f}, loops={len(t2['affected_feedback_loops'])}")
            recommended_modifications.append("Extend boundary scope to account for 2nd and 3rd order effects.")

        # ---- T3: Scale invariance ----
        t3 = self._test_scale_invariance(claim)
        for scope, data in t3.items():
            if data["status"] == "BREAKS":
                failures.append(f"T3 Violation: Claim BREAKS at {scope} scale. {data['reason']}")
                failure_mechanisms.append(f"T3: BREAKS at {scope} (degradation={data['degradation']:.2f})")
                recommended_modifications.append(
                    f"Restrict claim to scales where it holds, or add corrections for {scope}."
                )
            elif data["status"] == "DEGRADES" and data["degradation"] > 0.5:
                failures.append(
                    f"T3 Degradation: Claim DEGRADES at {scope} scale ({data['degradation']:.0%} loss)."
                )
                failure_mechanisms.append(f"T3: DEGRADES at {scope} (degradation={data['degradation']:.2f})")
                recommended_modifications.append(f"Add scale-dependent corrections for {scope}.")

        scale_profile = {scope: data["status"] for scope, data in t3.items()}

        # ---- T4: Ontology translation ----
        t4 = self._translate_ontology(claim)
        ontology_scores = []
        for ont, data in t4.items():
            if data["score"] < 0.4:
                failures.append(
                    f"T4 Violation: Claim has low validity under {ont} ontology (score {data['score']:.2f})."
                )
                failure_mechanisms.append(f"T4: low score under {ont} ({data['score']:.2f})")
                recommended_modifications.append(f"Re-frame or re-test claim under {ont} ontology.")
            if data.get("bias_detected"):
                bias_list = data["bias_detected"]
                bias_str = "', '".join(bias_list)
                recommended_modifications.append(
                    f"Address biases under {ont} ontology: '{bias_str}'"
                )
            ontology_scores.append(data["score"])

        # ---- Determine final verdict ----
        if failures:
            break_failures = [f for f in failures if "BREAKS" in f or "Violation" in f]
            if break_failures:
                verdict = TestVerdict.BREAKS
                confidence = 0.35
            else:
                verdict = TestVerdict.DEGRADES
                confidence = 0.65
        else:
            verdict = TestVerdict.HOLDS
            confidence = 0.92

        # Adjust confidence based on ontology consistency
        if t4.get("pre_linguistic", {}).get("score", 0) < 0.5:
            confidence *= 0.9

        # If no failures but some degradation, downgrade
        if verdict == TestVerdict.HOLDS and any(
            data["degradation"] > 0.2 for data in t3.values() if data["status"] != "HOLDS"
        ):
            verdict = TestVerdict.DEGRADES
            confidence = 0.7

        # Deduplicate modifications
        recommended_modifications = list(dict.fromkeys(recommended_modifications))

        return DiagnosticReport(
            claim_id=claim.id,
            claim_name=claim.name,
            claim_statement=claim.current().statement,
            verdict=verdict,
            overall_confidence=confidence,
            failures=failures,
            modifications=modifications,
            thermodynamic_account=t1,
            cascade_footprint=t2,
            scale_profile=scale_profile,
            ontological_shifts=t4,
            failure_mechanisms=failure_mechanisms,
            recommended_modifications=recommended_modifications,
        )

    # -------------------------------------------------------------------------
    # BATCH EVALUATION
    # -------------------------------------------------------------------------
    def evaluate_all(self, domain: Optional[str] = None) -> List[DiagnosticReport]:
        """Evaluate all claims in the registry, optionally filtered by domain."""
        reports = []
        for cid, claim in CLAIM_REGISTRY.items():
            if domain and claim.domain != domain:
                continue
            try:
                report = self.evaluate(cid)
                reports.append(report)
            except Exception as e:
                if self.verbose:
                    print(f"Error evaluating {cid}: {e}")
                continue
        return reports


# =============================================================================
# Utility: Compare two reports
# =============================================================================

def compare_reports(report_a: DiagnosticReport, report_b: DiagnosticReport) -> Dict:
    """Compare two diagnostic reports side-by-side."""
    return {
        "claim_a": {
            "name": report_a.claim_name,
            "verdict": report_a.verdict.value,
            "confidence": report_a.overall_confidence,
            "failures": len(report_a.failures),
        },
        "claim_b": {
            "name": report_b.claim_name,
            "verdict": report_b.verdict.value,
            "confidence": report_b.overall_confidence,
            "failures": len(report_b.failures),
        },
        "comparison": {
            "same_verdict": report_a.verdict == report_b.verdict,
            "confidence_delta": report_a.overall_confidence - report_b.overall_confidence,
            "shared_failures": list(set(report_a.failures) & set(report_b.failures)),
        }
    }
