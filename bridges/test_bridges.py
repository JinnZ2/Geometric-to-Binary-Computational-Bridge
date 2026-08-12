#!/usr/bin/env python3
# test_bridges.py
# CC0 — No Rights Reserved
#
# Runs every bridge in the bridges/ folder through the claim playground.
# Tests translation fidelity, thermodynamic cost, scale behavior, and
# ontological consistency. Produces JSON output for AI consumption.

import os
import sys
import json
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import argparse
import traceback

# Add parent dir to path for claim_playground import
sys.path.insert(0, str(Path(__file__).parent))

try:
    from claim_playground.claim_schema import (
        Claim, ClaimVersion, ScopeLevel, OntologyType,
        GeometryType, Verdict, CLAIM_REGISTRY
    )
    from claim_playground.claim_tester import ClaimTester, DiagnosticReport
except ImportError:
    print("⚠  claim_playground not found. Ensure it's installed or in PYTHONPATH.")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# BRIDGE DISCOVERY
# ─────────────────────────────────────────────────────────────

BRIDGES_DIR = Path(__file__).parent / "bridges"
EXCLUDED_MODULES = {
    "__init__.py",
    "common.py",
    "orchestrator.py",
    "integration_pipeline.py",
}


def discover_bridges() -> List[Tuple[str, Path]]:
    """
    Walk bridges/ and find all .py files that are likely bridges.
    Returns list of (module_name, file_path).
    """
    bridges = []
    if not BRIDGES_DIR.exists():
        print(f"⚠  bridges directory not found at {BRIDGES_DIR}")
        return bridges

    for py_file in BRIDGES_DIR.rglob("*.py"):
        if py_file.name in EXCLUDED_MODULES:
            continue
        # Skip files that are clearly utilities or tests
        if py_file.name.startswith("test_") or py_file.name.startswith("_"):
            continue

        # Compute module name relative to bridges/
        rel_path = py_file.relative_to(BRIDGES_DIR)
        module_parts = list(rel_path.with_suffix("").parts)
        module_name = "bridges." + ".".join(module_parts)
        bridges.append((module_name, py_file))

    return bridges


def probe_bridge(module) -> Dict[str, Any]:
    """
    Inspect a loaded module to find its bridge interface.
    Returns a dict with:
      - has_encode_decode: bool
      - has_translate_inverse: bool
      - has_run: bool
      - methods: list of callable names
      - bridge_class: class or None
    """
    info = {
        "has_encode_decode": False,
        "has_translate_inverse": False,
        "has_run": False,
        "methods": [],
        "bridge_class": None,
    }

    # Look for classes named Bridge, *Bridge, or *Encoder
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            if "Bridge" in name or "Encoder" in name or name.endswith("Bridge"):
                info["bridge_class"] = obj
                # Check methods
                if hasattr(obj, "encode") and hasattr(obj, "decode"):
                    info["has_encode_decode"] = True
                if hasattr(obj, "translate") and hasattr(obj, "inverse"):
                    info["has_translate_inverse"] = True
                if hasattr(obj, "run"):
                    info["has_run"] = True

    # Check module-level functions
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):
            info["methods"].append(name)
            if name == "encode" and "decode" in info["methods"]:
                info["has_encode_decode"] = True
            if name == "translate" and "inverse" in info["methods"]:
                info["has_translate_inverse"] = True
            if name == "run":
                info["has_run"] = True

    return info


# ─────────────────────────────────────────────────────────────
# BRIDGE TESTER
# ─────────────────────────────────────────────────────────────

class BridgeTester:
    """
    Runs claims against a bridge's translation fidelity.
    """

    def __init__(self, claim_tester: ClaimTester):
        self.tester = claim_tester

    def test_bridge(
        self,
        bridge_module,
        bridge_info: Dict[str, Any],
        claim_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Test a bridge against a set of claims.
        """
        claim_ids = claim_ids or [
            "thermodynamic_closure",
            "scale_dependence",
            "gauge_as_proxy",
            "calibration_loop",
        ]

        results = {}
        module_name = bridge_module.__name__

        # Try to instantiate the bridge
        bridge_instance = None
        if bridge_info["bridge_class"]:
            try:
                bridge_instance = bridge_info["bridge_class"]()
            except Exception as e:
                results["instantiation_error"] = str(e)

        # Define test geometry
        test_geometry = {
            "type": "point",
            "coordinates": [1.0, 2.0, 3.0],
            "temperature": 20.0,
            "pressure": 101.3,
            "flux": [0.1, 0.2, 0.3],
        }

        # Run translation if possible
        translation_result = self._run_translation(
            bridge_module, bridge_instance, test_geometry
        )
        results["translation"] = translation_result

        # Evaluate claims using the translation output
        for claim_id in claim_ids:
            claim = CLAIM_REGISTRY.get(claim_id)
            if not claim:
                results[claim_id] = {"error": f"Claim {claim_id} not found in registry"}
                continue

            # Create a dynamic version that incorporates bridge fidelity
            current = claim.current()
            fidelity = translation_result.get("fidelity", 0.0)
            loss = translation_result.get("loss", 0.0)

            # Modify the claim's statement to include bridge context
            modified_statement = (
                f"{current.statement} "
                f"(Bridge fidelity: {fidelity:.2f}, loss: {loss:.2f})"
            )

            # Create a temporary claim version with adjusted boundaries
            test_version = ClaimVersion(
                version=0,
                statement=modified_statement,
                domain=claim.domain,
                scope_valid=current.scope_valid,
                ontology_assumed=current.ontology_assumed,
                geometry_assumed=current.geometry_assumed,
                green_range=current.green_range,
                yellow_range=current.yellow_range,
                red_threshold=current.red_threshold,
            )

            # Run the claim through the tester
            temp_claim = Claim(
                name=f"{claim.name}_bridge_test",
                description=f"Testing {claim.name} on {module_name}",
                source=f"bridge_tester_{module_name}",
                domain=claim.domain,
                versions=[test_version],
                couplings=claim.couplings,
            )

            # Evaluate with context that includes bridge performance
            context = {
                "input_energy": 1.0,
                "externalized_waste_entropy": loss,
                "bridge_fidelity": fidelity,
            }

            try:
                report = self.tester.evaluate(temp_claim, system_context=context)
                results[claim_id] = {
                    "verdict": report.verdict.value,
                    "confidence": report.overall_confidence,
                    "thermodynamic_account": report.thermodynamic_account,
                    "cascade_footprint": report.cascade_footprint,
                    "scale_profile": {
                        k.value: v for k, v in report.scale_profile.items()
                    },
                    "ontological_shifts": report.ontological_shifts,
                    "failure_mechanisms": report.failure_mechanisms,
                    "recommended_modifications": report.recommended_modifications,
                }
            except Exception as e:
                results[claim_id] = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }

        return results

    def _run_translation(self, module, instance, geometry):
        """
        Attempt to translate geometry through the bridge.
        Returns fidelity metrics.
        """
        result = {
            "success": False,
            "fidelity": 0.0,
            "loss": 0.0,
            "roundtrip_error": None,
        }

        # Try instance methods first
        encode_fn = None
        decode_fn = None

        if instance:
            if hasattr(instance, "encode") and hasattr(instance, "decode"):
                encode_fn = instance.encode
                decode_fn = instance.decode
            elif hasattr(instance, "translate") and hasattr(instance, "inverse"):
                encode_fn = instance.translate
                decode_fn = instance.inverse
            elif hasattr(instance, "run"):
                # Some bridges just have run() — call it and capture output
                try:
                    output = instance.run(geometry)
                    result["success"] = True
                    result["output"] = str(output)
                    result["fidelity"] = 0.5  # unknown fidelity, assume partial
                    return result
                except Exception as e:
                    result["error"] = str(e)
                    return result

        # Try module-level functions
        if not encode_fn:
            if hasattr(module, "encode") and hasattr(module, "decode"):
                encode_fn = module.encode
                decode_fn = module.decode
            elif hasattr(module, "translate") and hasattr(module, "inverse"):
                encode_fn = module.translate
                decode_fn = module.inverse

        if encode_fn and decode_fn:
            try:
                binary = encode_fn(geometry)
                roundtrip = decode_fn(binary)

                # Compute fidelity: compare roundtrip to original
                error = self._compute_error(geometry, roundtrip)
                fidelity = max(0.0, 1.0 - error)

                result["success"] = True
                result["fidelity"] = fidelity
                result["loss"] = 1.0 - fidelity
                result["roundtrip_error"] = error
                result["binary_output"] = str(binary)
                result["roundtrip_output"] = str(roundtrip)
                return result

            except Exception as e:
                result["error"] = str(e)
                result["traceback"] = traceback.format_exc()
                return result

        # No interface found
        result["error"] = "No encode/decode or translate/inverse interface found"
        return result

    def _compute_error(self, original, roundtrip):
        """Simple error metric for roundtrip fidelity."""
        if isinstance(original, dict) and isinstance(roundtrip, dict):
            # Compare scalar fields
            error = 0.0
            count = 0
            for key in original:
                if key in roundtrip:
                    ov = original.get(key, 0)
                    rv = roundtrip.get(key, 0)
                    if isinstance(ov, (int, float)) and isinstance(rv, (int, float)):
                        if ov != 0:
                            error += abs((rv - ov) / ov)
                        else:
                            error += abs(rv)
                        count += 1
            return error / max(count, 1)
        elif isinstance(original, list) and isinstance(roundtrip, list):
            # Compare coordinate lists
            if len(original) == len(roundtrip):
                error = 0.0
                for o, r in zip(original, roundtrip):
                    if isinstance(o, (int, float)) and isinstance(r, (int, float)):
                        error += abs(o - r)
                return error / max(len(original), 1)
        return 1.0  # fallback


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test all bridges against claim playground."
    )
    parser.add_argument(
        "--claim-ids",
        nargs="+",
        default=["thermodynamic_closure", "scale_dependence", "gauge_as_proxy"],
        help="Claim IDs to test against"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first bridge error"
    )
    args = parser.parse_args()

    # Initialize tester
    tester = ClaimTester(
        substrate_audit_active=True,
        cascade_engine_active=True,
        validator_active=True,
    )
    bridge_tester = BridgeTester(tester)

    # Discover bridges
    bridges = discover_bridges()
    print(f"Found {len(bridges)} bridge modules.")

    if not bridges:
        print("No bridges found. Exiting.")
        sys.exit(0)

    all_results = {}
    for module_name, file_path in bridges:
        print(f"\n🔍 Testing {module_name} ({file_path})")
        try:
            # Import the module
            module = importlib.import_module(module_name)
            info = probe_bridge(module)
            results = bridge_tester.test_bridge(module, info, args.claim_ids)
            all_results[module_name] = {
                "file": str(file_path),
                "interface": info,
                "results": results,
            }

            # Print summary
            print(f"  Interface: encode/decode={info['has_encode_decode']}, "
                  f"translate/inverse={info['has_translate_inverse']}, "
                  f"run={info['has_run']}")

            for claim_id, result in results.items():
                if claim_id == "translation":
                    print(f"  Translation: fidelity={result.get('fidelity', 0.0):.2f}")
                elif isinstance(result, dict) and "verdict" in result:
                    print(f"  {claim_id}: {result['verdict']} "
                          f"(conf={result.get('confidence', 0.0):.2f})")
                elif isinstance(result, dict) and "error" in result:
                    print(f"  {claim_id}: ⚠ {result['error']}")

        except Exception as e:
            print(f"  ❌ Failed to load/test {module_name}: {e}")
            if args.fail_fast:
                raise
            all_results[module_name] = {
                "file": str(file_path),
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # Output
    all_results["timestamp"] = datetime.utcnow().isoformat()
    all_results["summary"] = {
        "total": len(all_results) - 1,
        "successful": len([k for k, v in all_results.items() if k != "timestamp" and "error" not in v]),
        "failed": len([k for k, v in all_results.items() if k != "timestamp" and "error" in v]),
    }

    if args.json_output:
        print("\n" + "=" * 60)
        print(json.dumps(all_results, indent=2, default=str))
    else:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total: {all_results['summary']['total']}")
        print(f"Successful: {all_results['summary']['successful']}")
        print(f"Failed: {all_results['summary']['failed']}")
        print("\nDetailed results saved in variable 'all_results'.")


if __name__ == "__main__":
    main()
