"""
claim_playground — Earth Systems Physics Claim Registry & T1-T4 Test Harness

A framework for storing, versioning, and cross-referencing claims across domains,
with mandatory reality checks:
  T1: Thermodynamic Closure
  T2: Cascade Exposure
  T3: Scale Invariance
  T4: Ontology Translation
"""

from claim_playground.claim_schema import (
    Claim,
    ClaimVersion,
    ScopeLevel,
    GeometryType,
    OntologyType,
    Verdict,
    TestResult,
    CLAIM_REGISTRY,
    get_claim,
    list_claims,
    find_claims_by_tag,
    find_coupled_claims,
    render_claim,
)

from claim_playground.claim_tester import (
    ClaimTester,
    TestVerdict,
    DiagnosticReport,
    compare_reports,
)

from claim_playground.json_schema import (
    validate_claim_json,
    validate_claim_json_string,
    ValidationError,
)

__version__ = "0.2.0"
__all__ = [
    "Claim",
    "ClaimVersion",
    "ScopeLevel",
    "GeometryType",
    "OntologyType",
    "Verdict",
    "TestResult",
    "CLAIM_REGISTRY",
    "get_claim",
    "list_claims",
    "find_claims_by_tag",
    "find_coupled_claims",
    "render_claim",
    "ClaimTester",
    "TestVerdict",
    "DiagnosticReport",
    "compare_reports",
    "validate_claim_json",
    "validate_claim_json_string",
    "ValidationError",
]
