#!/usr/bin/env python3
"""
tests/test_collisions.py
earth-systems-physics
CC0 — No Rights Reserved

Pytest harness for the 9 Ontological Collision stages.
Each stage represents a distinct failure mode in institutional/systemic reasoning.
"""

import pytest
from typing import Dict, Any

from claim_playground.claim_schema import (
    Claim,
    ClaimVersion,
    ScopeLevel,
    GeometryType,
    OntologyType,
    CLAIM_REGISTRY,
)
from claim_playground.claim_tester import ClaimTester, TestVerdict


# ---------------------------------------------------------------------------
# Test Fixtures & Collision Scenarios
# ---------------------------------------------------------------------------

COLLISION_CASES = [
    {
        "id": "stage_0_accommodation_masking",
        "stage": 0,
        "name": "Stage 0: Accommodation Masking",
        "description": "Practitioner absorbs system friction manually; instrument records nominal success.",
        "statement": "The automated dispatch routing protocol maintains high schedule efficiency.",
        "ontology_assumed": OntologyType.SUBSTANCE,
        "scope_valid": [ScopeLevel.MESO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 45.0,
            "manual_override_active": True,
        },
        "expected_verdict": TestVerdict.DEGRADES,
        "expected_failure_substring": "externalized",
    },
    {
        "id": "stage_1_arity_category_absence",
        "stage": 1,
        "name": "Stage 1: Logical Arity / Category Absence",
        "description": "Instrument flattens 3-place relational reality into a 1-place scalar gauge.",
        "statement": "Coolant temperature scalar is within green threshold range.",
        "ontology_assumed": OntologyType.SUBSTANCE,
        "scope_valid": [ScopeLevel.MICRO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 30.0,
            "relational_arity_missing": True,
        },
        "expected_verdict": TestVerdict.BREAKS,
        "expected_failure_substring": "t2",
    },
    {
        "id": "stage_2_scope_scaling_error",
        "stage": 2,
        "name": "Stage 2: Scope Shift / Scaling Error",
        "description": "Rule derived at Micro scale applied directly to Macro network dynamics.",
        "statement": "Brake pad coefficient of friction predicts convoy stopping distance across 11% grade.",
        "ontology_assumed": OntologyType.PROCESS,
        "scope_valid": [ScopeLevel.MICRO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 5.0,
        },
        "expected_verdict": TestVerdict.BREAKS,
        "expected_failure_substring": "scale",
    },
    {
        "id": "stage_3_thermodynamic_neglect",
        "stage": 3,
        "name": "Stage 3: Thermodynamic Energy Debt Neglect",
        "description": "Model ignores thermal accumulation and heat-sink saturation limits.",
        "statement": "Continuous output rating holds under sustained full-load duty cycle.",
        "ontology_assumed": OntologyType.SUBSTANCE,
        "scope_valid": [ScopeLevel.MESO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 60.0,
        },
        "expected_verdict": TestVerdict.BREAKS,
        "expected_failure_substring": "t1",
    },
    {
        "id": "stage_4_static_frame_mismatch",
        "stage": 4,
        "name": "Stage 4: Static Frame vs. Process Dynamic",
        "description": "Treating dynamic flow state as static equilibrium snapshot.",
        "statement": "Fuel line flow rate remains static under variable manifold vacuum.",
        "ontology_assumed": OntologyType.SUBSTANCE,
        "scope_valid": [ScopeLevel.MESO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 15.0,
            "dynamic_phase_change": True,
        },
        "expected_verdict": TestVerdict.DEGRADES,
        "expected_failure_substring": "ontology",
    },
    {
        "id": "stage_5_signal_noise_inversion",
        "stage": 5,
        "name": "Stage 5: Signal / Noise Inversion",
        "description": "Automated collision braking treats terrain vibration as imminent collision signal.",
        "statement": "Radar collision mitigation algorithm accurately isolates crash vectors on steep grades.",
        "ontology_assumed": OntologyType.SUBSTANCE,
        "scope_valid": [ScopeLevel.MESO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 25.0,
            "false_positive_trigger": True,
        },
        "expected_verdict": TestVerdict.BREAKS,
        "expected_failure_substring": "t2",
    },
    {
        "id": "stage_6_structural_lockin",
        "stage": 6,
        "name": "Stage 6: Structural Lock-In / False Symmetry",
        "description": "Policy metric forces physical reality into compliant compliance records.",
        "statement": "Municipal infrastructure maintenance index verifies full fire protection capability.",
        "ontology_assumed": OntologyType.SUBSTANCE,
        "scope_valid": [ScopeLevel.MESO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 40.0,
            "unserviced_pipe_present": True,
        },
        "expected_verdict": TestVerdict.BREAKS,
        "expected_failure_substring": "t1",
    },
    {
        "id": "stage_7_substrate_erasure",
        "stage": 7,
        "name": "Stage 7: Substrate Erasure",
        "description": "Ignores material decay and physical infrastructure breakdown.",
        "statement": "Bridge load rating remains valid based on original 1972 engineering print.",
        "ontology_assumed": OntologyType.SUBSTANCE,
        "scope_valid": [ScopeLevel.MESO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 50.0,
            "decayed_substrate": True,
        },
        "expected_verdict": TestVerdict.BREAKS,
        "expected_failure_substring": "t1",
    },
    {
        "id": "stage_8_cascade_blindness",
        "stage": 8,
        "name": "Stage 8: Systemic Cascade Blindness",
        "description": "Fails to model secondary and tertiary feedback loops following initial fault.",
        "statement": "Single motor thermal trip will not impact remaining three power units.",
        "ontology_assumed": OntologyType.FIELD,
        "scope_valid": [ScopeLevel.MACRO],
        "system_context": {
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 35.0,
            "unaccounted_cascades": True,
        },
        "expected_verdict": TestVerdict.BREAKS,
        "expected_failure_substring": "t2",
    },
]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def build_claim_instance(case: Dict[str, Any]) -> Claim:
    """Convert a collision test case dictionary into a full Claim object."""
    version = ClaimVersion(
        version=0,
        statement=case["statement"],
        mathematical_form=None,
        domain="ontological_collision",
        scope_valid=case["scope_valid"],
        ontology_assumed=case["ontology_assumed"],
        geometry_assumed=GeometryType.EUCLIDEAN,
        green_range={"efficiency": ">= 0.85"},
        yellow_range={"efficiency": "0.60 - 0.84"},
        red_threshold={"efficiency": "< 0.60"},
    )
    return Claim(
        id=case["id"],
        name=case["name"],
        domain="ontological_collision",
        description=case["description"],
        versions=[version],
        active_version=0,
    )


# ---------------------------------------------------------------------------
# Pytest Harness
# ---------------------------------------------------------------------------

@pytest.fixture
def tester():
    """Provides a fresh ClaimTester instance for each test run."""
    return ClaimTester()


@pytest.mark.parametrize("case", COLLISION_CASES, ids=lambda c: f"Stage_{c['stage']}_{c['id']}")
def test_ontological_collisions_harness(tester: ClaimTester, case: Dict[str, Any]):
    """
    Executes all 9 Ontological Collision stages through the T1-T4 diagnostic harness.
    Verifies that claims with structural blind spots fail, degrade, or break as predicted.
    """
    claim = build_claim_instance(case)
    context = case["system_context"]

    # Temporarily register claim for evaluation
    CLAIM_REGISTRY[case["id"]] = claim
    try:
        report = tester.evaluate(case["id"], system_context=context)
    finally:
        del CLAIM_REGISTRY[case["id"]]

    # Assert Verdict match
    assert report.claim_id == case["id"]
    assert report.verdict in [TestVerdict.DEGRADES, TestVerdict.BREAKS], (
        f"Stage {case['stage']} expected DEGRADES or BREAKS, got {report.verdict.value}"
    )

    # Verify T1 failure for high waste cases
    if case["system_context"]["externalized_waste_entropy"] > 30.0:
        assert report.thermodynamic_account["passed"] is False, (
            f"Stage {case['stage']} should have failed T1 Thermodynamic Closure."
        )

    # Check for expected failure flags
    combined_notes = " ".join(
        report.failure_mechanisms + report.recommended_modifications
    ).lower()

    assert case["expected_failure_substring"] in combined_notes, (
        f"Stage {case['stage']} output missing expected diagnostic keyword "
        f"'{case['expected_failure_substring']}'. Got: {combined_notes}"
    )


def test_collision_suite_completeness():
    """Ensures all 9 collision stages (Stage 0 through Stage 8) are tested."""
    stages_covered = {case["stage"] for case in COLLISION_CASES}
    expected_stages = set(range(9))
    assert stages_covered == expected_stages, (
        f"Missing collision stages: {expected_stages - stages_covered}"
    )


def test_registry_seed_claims(tester: ClaimTester):
    """Smoke-test: all seeded registry claims should evaluate without crashing."""
    from claim_playground.claim_schema import CLAIM_REGISTRY
    for cid in list(CLAIM_REGISTRY.keys())[:3]:  # sample 3 for speed
        report = tester.evaluate(cid)
        assert report.claim_id == CLAIM_REGISTRY[cid].id
        assert report.verdict in [TestVerdict.HOLDS, TestVerdict.DEGRADES, TestVerdict.BREAKS]


def test_thermodynamic_closure_calculation(tester: ClaimTester):
    """Unit test: verify T1 math directly."""
    claim = build_claim_instance(COLLISION_CASES[0])
    CLAIM_REGISTRY["__t1_test__"] = claim
    try:
        # 45% waste → 55% efficiency → should fail (threshold 80%)
        report = tester.evaluate("__t1_test__", system_context={
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 45.0,
        })
        assert report.thermodynamic_account["net_efficiency"] == 0.55
        assert report.thermodynamic_account["passed"] is False
        assert report.thermodynamic_account["externalized_waste_fraction"] == 0.45
    finally:
        del CLAIM_REGISTRY["__t1_test__"]


def test_scale_invariance_breaks_at_macro(tester: ClaimTester):
    """Unit test: a Micro-only claim should BREAK at Macro scale."""
    claim = build_claim_instance(COLLISION_CASES[2])  # Stage 2: Micro scope
    CLAIM_REGISTRY["__scale_test__"] = claim
    try:
        report = tester.evaluate("__scale_test__", system_context={
            "input_energy_joules": 100.0,
            "externalized_waste_entropy": 5.0,
        })
        assert report.scale_profile["macro"] == "BREAKS"
        assert any("macro" in f.lower() for f in report.failure_mechanisms)
    finally:
        del CLAIM_REGISTRY["__scale_test__"]
