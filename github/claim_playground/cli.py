#!/usr/bin/env python3
"""
claim_playground/cli.py
earth-systems-physics
CC0 — No Rights Reserved

CLI interface for the Claim Playground.
Takes raw field observations, claim definitions, or JSON payloads and runs them
against the 4 mandatory reality checks (T1-T4).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from claim_playground.claim_schema import (
    Claim, ClaimVersion, ScopeLevel, GeometryType, OntologyType,
    CLAIM_REGISTRY
)
from claim_playground.claim_tester import ClaimTester, TestVerdict, DiagnosticReport
from claim_playground.json_schema import validate_claim_json_string, ValidationError


def build_claim_from_raw_text(statement: str, domain: str = "field_observation") -> Claim:
    """Parses an unformatted field observation into a provisional Claim."""
    version = ClaimVersion(
        version=0,
        statement=statement,
        mathematical_form=None,
        domain=domain,
        scope_valid=[ScopeLevel.MESO],
        ontology_assumed=OntologyType.SUBSTANCE,
        geometry_assumed=GeometryType.EUCLIDEAN,
        green_range={"context": "ideal_conditions"},
        yellow_range={"context": "variable_environment"},
        red_threshold={"context": "extreme_stress"},
    )
    return Claim(
        name="Field-Derived Claim",
        domain=domain,
        description="Parsed directly from raw practitioner observation or text input.",
        versions=[version],
        active_version=0,
    )


def build_claim_from_json(data: Dict[str, Any]) -> Claim:
    """Reconstructs a fully specified Claim object from a JSON schema payload."""
    v_data = data.get("version", data)

    scope_valid = [ScopeLevel(s) for s in v_data.get("scope_valid", ["meso"])]
    ontology = OntologyType(v_data.get("ontology_assumed", "substance"))
    geometry = GeometryType(v_data.get("geometry_assumed", "euclidean"))

    version = ClaimVersion(
        version=v_data.get("version_number", 0),
        statement=v_data.get("statement", data.get("name", "Unnamed Claim")),
        mathematical_form=v_data.get("mathematical_form"),
        domain=v_data.get("domain", data.get("domain", "general")),
        scope_valid=scope_valid,
        ontology_assumed=ontology,
        geometry_assumed=geometry,
        green_range=v_data.get("green_range", {}),
        yellow_range=v_data.get("yellow_range", {}),
        red_threshold=v_data.get("red_threshold", {}),
    )

    return Claim(
        id=data.get("id"),
        name=data.get("name", "JSON Claim"),
        domain=data.get("domain", "general"),
        description=data.get("description", ""),
        versions=[version],
        active_version=0,
    )


def print_formatted_report(report: DiagnosticReport, raw_mode: bool = False):
    """Prints the DiagnosticReport to stdout with clear section boundaries."""
    if raw_mode:
        output = {
            "claim_id": report.claim_id,
            "claim_name": report.claim_name,
            "statement": report.claim_statement,
            "verdict": report.verdict.value,
            "confidence": round(report.overall_confidence, 3),
            "thermodynamics_T1": report.thermodynamic_account,
            "cascades_T2": report.cascade_footprint,
            "scale_profile_T3": report.scale_profile,
            "ontological_shifts_T4": {
                k: {
                    "score": v.get("score"),
                    "validity": v.get("validity"),
                    "bias_detected": v.get("bias_detected", []),
                }
                for k, v in report.ontological_shifts.items()
            },
            "failures": report.failure_mechanisms,
            "modifications": report.recommended_modifications,
        }
        print(json.dumps(output, indent=2, default=str))
        return

    # Visual terminal presentation
    print("\n" + "=" * 80)
    print(" CLAIM PLAYGROUND DIAGNOSTIC REPORT ")
    print("=" * 80)
    print(f"Claim ID:   {report.claim_id}")
    print(f"Name:       {report.claim_name}")
    print(f"Statement:   {report.claim_statement[:70]}{'...' if len(report.claim_statement) > 70 else ''}")

    verdict_str = report.verdict.value
    bar = "█" * int(report.overall_confidence * 20) + "░" * (20 - int(report.overall_confidence * 20))
    print(f"Verdict:    {verdict_str} (Confidence: {report.overall_confidence:.2f}) [{bar}]")

    print("\n[T1: THERMODYNAMIC CLOSURE]")
    t1 = report.thermodynamic_account
    status_t1 = "PASS" if t1.get("passed") else "FAIL"
    print(f"  Status: {status_t1}")
    print(f"  Net Efficiency: {t1.get('net_efficiency', 0.0) * 100:.1f}%")
    if t1.get("leakage_points"):
        print("  Leakage Points:")
        for pt in t1["leakage_points"]:
            print(f"    - {pt}")

    print("\n[T2: CASCADE EXPOSURE]")
    t2 = report.cascade_footprint
    risk = "HIGH RISK" if t2.get("unaccounted_effects_found") else "LOW RISK"
    print(f"  Status: {risk} (Depth: {t2.get('cascade_depth_checked')})")
    print(f"  Risk Score: {t2.get('risk_score', 0):.2f}")
    cmap = t2.get("cascade_map", {})
    print(f"  Primary:   {cmap.get(1, 'N/A')}")
    print(f"  Secondary: {cmap.get(2, 'N/A')}")
    print(f"  Tertiary:  {cmap.get(3, 'N/A')}")
    if t2.get("affected_feedback_loops"):
        print("  Affected Loops:")
        for loop in t2["affected_feedback_loops"]:
            print(f"    - {loop['name']}: {loop['description']}")

    print("\n[T3: SCALE INVARIANCE (ZOOM)]")
    for scope, val in report.scale_profile.items():
        icon = "✓" if val == "HOLDS" else "⚠" if val == "DEGRADES" else "✗"
        print(f"  {icon} {scope.capitalize():<10}: {val}")

    print("\n[T4: ONTOLOGY TRANSLATION]")
    for ont, data in report.ontological_shifts.items():
        score = data.get("score", 0)
        icon = "✓" if score >= 0.7 else "⚠" if score >= 0.4 else "✗"
        print(f"  {icon} {ont.capitalize():<15}: score={score:.2f} — {data.get('validity', '')[:50]}")
        if data.get("bias_detected"):
            for bias in data["bias_detected"]:
                print(f"      ⚠ Bias: {bias}")

    if report.failure_mechanisms:
        print("\nFAILURE MECHANISMS:")
        for fail in report.failure_mechanisms:
            print(f"  ! {fail}")

    if report.recommended_modifications:
        print("\nREQUIRED MODIFICATIONS TO EXTEND SCOPE:")
        for mod in report.recommended_modifications:
            print(f"  -> {mod}")

    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run claims or field observations through the T1-T4 Reality Test Harness."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file", "-f", type=str, help="Path to a JSON file containing the claim schema."
    )
    group.add_argument(
        "--claim", "-c", type=str, help="Raw text statement of the claim or field observation."
    )
    group.add_argument(
        "--registry-id", "-r", type=str, help="Evaluate a seeded claim from the registry by ID."
    )
    group.add_argument(
        "--list-registry", action="store_true", help="List all seeded claims in the registry."
    )

    parser.add_argument(
        "--domain", "-d", type=str, default="field_observation", help="Domain category for the claim."
    )
    parser.add_argument(
        "--input-energy", type=float, default=100.0, help="Input energy in Joules for T1 accounting."
    )
    parser.add_argument(
        "--waste-entropy", type=float, default=10.0, help="Externalized waste/heat in Joules for T1 accounting."
    )
    parser.add_argument(
        "--hidden-subsidies", type=float, default=0.0, help="Hidden energy subsidies in Joules."
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output raw JSON instead of human-readable text."
    )

    args = parser.parse_args()

    if args.list_registry:
        print("=" * 60)
        print("SEEDED CLAIM REGISTRY")
        print("=" * 60)
        for cid, claim in CLAIM_REGISTRY.items():
            print(f"  {cid:<30} | {claim.name} ({claim.domain})")
        print(f"\nTotal: {len(CLAIM_REGISTRY)} claims")
        return

    # Load or construct the claim
    if args.registry_id:
        claim_obj = CLAIM_REGISTRY.get(args.registry_id)
        if not claim_obj:
            print(f"Error: Registry claim '{args.registry_id}' not found.", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File {args.file} not found.", file=sys.stderr)
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            claim_data = json.load(f)
        claim_obj = build_claim_from_json(claim_data)
    else:
        claim_obj = build_claim_from_raw_text(args.claim, domain=args.domain)

    # Context setup for T1 evaluation
    system_context = {
        "input_energy_joules": args.input_energy,
        "externalized_waste_entropy": args.waste_entropy,
        "hidden_subsidies": args.hidden_subsidies,
    }

    # Execute harness
    tester = ClaimTester()
    # For registry claims, we need to inject the claim into the registry temporarily
    # or evaluate by ID. The tester evaluates by ID, so for raw/JSON claims we
    # register them temporarily.
    if args.registry_id:
        report = tester.evaluate(args.registry_id, system_context=system_context)
    else:
        # Temporarily register for evaluation
        temp_id = f"__temp__{claim_obj.id}"
        CLAIM_REGISTRY[temp_id] = claim_obj
        try:
            report = tester.evaluate(temp_id, system_context=system_context)
        finally:
            del CLAIM_REGISTRY[temp_id]

    # Output results
    print_formatted_report(report, raw_mode=args.json_output)


if __name__ == "__main__":
    main()
