"""ILLUSTRATIVE software fixtures only; no empirical/statistical claims.

Run from repository root with a fresh output path:
  python experiments/experiment_bridge/adversarial/core_probe.py --output /tmp/core-replay.json
Every fixture, including deliberately nonterminating cooperative iterators, runs
in a subprocess with a hard timeout. Do not invoke the internal worker directly.
No received specimen is imported or modified; only legacy v1 and candidate v1_1.
"""

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
MODULES = {"legacy": "experiments.experiment_bridge.v1.core",
           "candidate": "experiments.experiment_bridge.v1_1.core"}

# Classification concerns the observed legacy behavior, not a statistical rate.
CASE_ROWS = [
    ("target_square_underflow", "bug_on_binary64_underflow", "ACCEPTED", "ValueError"),
    ("distance_square_underflow", "bug_on_binary64_underflow", "ACCEPTED", "ValueError"),
    ("component_square_underflow", "conservative_policy_on_binary64_underflow", "ACCEPTED", "ValueError"),
    ("representable_subnormal_square", "expected_numerical_rejection", "REJECTED", "REJECTED"),
    ("decimal_gate_roundoff", "inherent_binary64_limitation", "REJECTED", "REJECTED"),
    ("lossy_integer_target", "silent_input_loss_hazard", "ACCEPTED", "ValueError"),
    ("lossy_huge_finite_integer_code", "silent_input_loss_hazard", "RETURNED", "ValueError"),
    ("exact_huge_integer_code", "expected_supported_conversion", "RETURNED", "RETURNED"),
    ("integer_conversion_overflow", "expected_input_rejection", "ValueError", "ValueError"),
    ("lossy_integer_threshold", "silent_input_loss_hazard", "RETURNED", "ValueError"),
    ("lossy_integer_calibration", "silent_input_loss_hazard", "RETURNED", "ValueError"),
    ("rounded_fraction_input", "documented_noninteger_binary64_rounding", "ACCEPTED", "ACCEPTED"),
    ("cancellation_outside_tolerance", "producer_validator_contract_bug_on_binary64_limitation", "SELF_INVALID", "ValueError"),
    ("cancellation_inside_tolerance", "documented_tolerance_not_exact_identity", "SELF_VALID", "SELF_VALID"),
    ("tiny_final_mutation", "documented_tolerance_not_exact_integrity", "DIAGNOSTICS_EMPTY", "DIAGNOSTICS_EMPTY"),
    ("large_final_mutation", "expected_validation_rejection", "DIAGNOSTICS", "DIAGNOSTICS"),
    ("tiny_step_state_mutation", "documented_tolerance_not_exact_integrity", "DIAGNOSTICS_EMPTY", "DIAGNOSTICS_EMPTY"),
    ("tiny_distance_without_levels", "documented_tolerance_not_exact_integrity", "DIAGNOSTICS_EMPTY", "DIAGNOSTICS_EMPTY"),
    ("tiny_distance_with_levels", "expected_exact_codebook_check", "DIAGNOSTICS", "DIAGNOSTICS"),
    ("missing_step_field", "expected_malformed_trace_rejection", "DIAGNOSTICS", "DIAGNOSTICS"),
    ("nested_malformed_vector", "expected_malformed_trace_rejection", "DIAGNOSTICS", "DIAGNOSTICS"),
    ("nonfinite_trace_field", "expected_malformed_trace_rejection", "DIAGNOSTICS", "DIAGNOSTICS"),
    ("malformed_target_iterator", "diagnostics_contract_bug_for_ordinary_iterator", "RuntimeError", "DIAGNOSTICS"),
    ("malformed_step_iterator", "diagnostics_contract_bug_for_ordinary_iterator", "RuntimeError", "DIAGNOSTICS"),
    ("finite_generator_steps", "expected_shape_rejection_with_unnecessary_consumption", "DIAGNOSTICS", "DIAGNOSTICS"),
    ("infinite_generator_steps", "unbounded_consumption_before_shape_rejection", "TIMEOUT", "DIAGNOSTICS"),
    ("infinite_target", "missing_resource_limit", "TIMEOUT", "ValueError"),
    ("infinite_codes", "missing_resource_limit", "TIMEOUT", "ValueError"),
    ("infinite_levels", "missing_resource_limit", "TIMEOUT", "ValueError"),
    ("vector_at_limit", "new_bound_boundary", "RETURNED", "RETURNED"),
    ("vector_over_limit", "new_policy_rejection_not_old_numerical_bug", "RETURNED", "ValueError"),
    ("codes_at_limit", "new_bound_boundary", "RETURNED", "RETURNED"),
    ("codes_over_limit", "new_policy_rejection_not_old_numerical_bug", "RETURNED", "ValueError"),
    ("levels_at_limit", "new_bound_boundary", "RETURNED", "RETURNED"),
    ("levels_over_limit", "new_policy_rejection_not_old_numerical_bug", "RETURNED", "ValueError"),
    ("samples_at_limit", "new_bound_boundary", "RETURNED", "RETURNED"),
    ("samples_over_limit", "new_policy_rejection_not_old_numerical_bug", "RETURNED", "ValueError"),
    ("calibration_books_over_limit", "new_policy_rejection_not_old_numerical_bug", "RETURNED", "ValueError"),
    ("trace_steps_over_limit", "new_policy_diagnostic_not_old_numerical_bug", "DIAGNOSTICS_EMPTY", "DIAGNOSTICS"),
]
CASES = {row[0]: row for row in CASE_ROWS}


def slow_repeat(value):
    """Cooperative software fixture: small memory use until parent kills worker."""
    while True:
        time.sleep(0.0001)
        yield value


def broken_iterator():
    yield 1
    raise RuntimeError("ILLUSTRATIVE ordinary iterator failure")


def trace_summary(core, trace, levels):
    errors = core.validate_trace(trace, levels)
    return {"outcome": "RETURNED", "version": trace["version"],
            "target": trace["target"], "reconstruction": trace["reconstruction"],
            "residual": trace["residual"], "statuses": [s["numerical_status"] for s in trace["steps"]],
            "distances": [s["distance_squared"] for s in trace["steps"]],
            "diagnostics": errors}


def fixture(core, name):
    if name in ("target_square_underflow", "distance_square_underflow",
                "component_square_underflow", "representable_subnormal_square",
                "decimal_gate_roundoff", "lossy_integer_target", "rounded_fraction_input"):
        target, book, threshold = {
            "target_square_underflow": ([1e-200], [[0]], 0),
            "distance_square_underflow": ([1, 0], [[1, 1e-200]], 0),
            "component_square_underflow": ([1, 1e-200], [[0, 0]], 1),
            "representable_subnormal_square": ([1e-160], [[0]], 0),
            "decimal_gate_roundoff": ([0.1], [[0]], 0.01),
            "lossy_integer_target": ([2**53 + 1], [[2**53]], 0),
            "rounded_fraction_input": ([Fraction(1, 10)], [[0.1]], 0),
        }[name]
        levels = [core.make_level(book, threshold)]
        result = trace_summary(core, core.walk(target, levels), levels)
        result["outcome"] = result["statuses"][0]
        if name == "lossy_integer_target":
            result["original_integer"] = str(target[0])
            result["converted_integer"] = str(int(result["target"][0]))
        return result
    if name in ("lossy_huge_finite_integer_code", "exact_huge_integer_code",
                "integer_conversion_overflow", "lossy_integer_threshold"):
        value = {"lossy_huge_finite_integer_code": 2**1000 + 1,
                 "exact_huge_integer_code": 2**1000,
                 "integer_conversion_overflow": 10**400,
                 "lossy_integer_threshold": 2**53 + 1}[name]
        level = core.make_level([[0]], value) if name.endswith("threshold") else core.make_level([[value]], 0)
        converted = level.threshold_squared if name.endswith("threshold") else level.codebook[0][0]
        return {"outcome": "RETURNED", "original_integer": str(value),
                "converted_integer": str(int(converted)), "equal_to_input": int(converted) == value}
    if name == "lossy_integer_calibration":
        return {"outcome": "RETURNED", "thresholds": core.calibrate_thresholds([[2**53 + 1]], [[[2**53]]], 0)}
    if name.startswith("cancellation_"):
        levels = [core.make_level([[1e16]], 1e32), core.make_level([[-1e16]], 1e32)]
        target = [1] if name.endswith("outside_tolerance") else [1e-13]
        result = trace_summary(core, core.walk(target, levels), levels)
        result["outcome"] = "SELF_INVALID" if result["diagnostics"] else "SELF_VALID"
        result["final_additive_discrepancy"] = target[0] - (result["reconstruction"][0] + result["residual"][0])
        return result
    if name in ("vector_at_limit", "vector_over_limit"):
        n = 4096 + name.endswith("over_limit")
        trace = core.walk([0] * n, [core.make_level([[0] * n], 0)])
        return {"outcome": "RETURNED", "dimension": trace["dimension"]}
    if name in ("codes_at_limit", "codes_over_limit"):
        n = 4096 + name.endswith("over_limit")
        trace = core.walk([0], [core.make_level([[0]] * n, 0)])
        return {"outcome": "RETURNED", "codes": n, "nearest_index": trace["steps"][0]["nearest_index"]}
    if name in ("levels_at_limit", "levels_over_limit"):
        n = 64 + name.endswith("over_limit")
        trace = core.walk([0], [core.make_level([[0]], 0)] * n)
        return {"outcome": "RETURNED", "levels": len(trace["steps"])}
    if name in ("samples_at_limit", "samples_over_limit", "calibration_books_over_limit"):
        n = 4096 + name.endswith("over_limit")
        samples, books = ([[0]], [[[0]]] * 65) if name.startswith("calibration") else ([[0]] * n, [[[0]]])
        return {"outcome": "RETURNED", "thresholds": core.calibrate_thresholds(samples, books, 0)}
    if name == "infinite_target":
        core.walk(slow_repeat(0), [core.make_level([[0]], 0)])
    elif name == "infinite_codes":
        core.make_level(slow_repeat([0]), 0)
    elif name == "infinite_levels":
        core.walk([0], slow_repeat(core.make_level([[0]], 0)))
    else:
        levels = [core.make_level([[0]], 2)]
        trace = core.walk([1], levels)
        mutation = None
        if name in ("tiny_final_mutation", "large_final_mutation"):
            mutation = 5e-13 if name.startswith("tiny") else 5e-11
            trace["reconstruction"][0] += mutation
        elif name == "tiny_step_state_mutation":
            mutation = 5e-13
            trace["steps"][0]["reconstruction_after"][0] += mutation
        elif name in ("tiny_distance_without_levels", "tiny_distance_with_levels"):
            mutation = 5e-13
            trace["steps"][0]["distance_squared"] += mutation
        elif name == "missing_step_field":
            del trace["steps"][0]["contribution"]
        elif name == "nested_malformed_vector":
            trace["steps"][0]["residual_after"] = [[1]]
        elif name == "nonfinite_trace_field":
            trace["steps"][0]["error_squared_after"] = float("nan")
        elif name == "malformed_target_iterator":
            trace["target"] = broken_iterator()
        elif name == "malformed_step_iterator":
            trace["steps"][0]["contribution"] = broken_iterator()
        elif name == "infinite_generator_steps":
            trace["steps"] = slow_repeat(trace["steps"][0])
        elif name == "finite_generator_steps":
            consumed = []
            # Capture original list before replacing it with the generator.
            original_steps = trace["steps"]
            def counted_steps():
                consumed.append("consumed")
                yield original_steps[0]
            trace["steps"] = counted_steps()
            errors = core.validate_trace(trace)
            return {"outcome": "DIAGNOSTICS" if errors else "DIAGNOSTICS_EMPTY",
                    "diagnostics": errors, "items_consumed": len(consumed)}
        elif name == "trace_steps_over_limit":
            trace = core.walk([0], [core.make_level([[0]], 0)])
            trace["steps"] = [deepcopy(trace["steps"][0]) for _ in range(65)]
            for i, step in enumerate(trace["steps"], 1):
                step["level"] = i
            levels = None
        else:
            raise ValueError(f"unknown fixture: {name}")
        actual = None if name in ("tiny_distance_without_levels", "infinite_generator_steps",
                                 "trace_steps_over_limit") else levels
        errors = core.validate_trace(trace, actual)
        result = {"outcome": "DIAGNOSTICS" if errors else "DIAGNOSTICS_EMPTY", "diagnostics": errors}
        if mutation is not None:
            result["illustrative_mutation"] = mutation
        return result
    raise AssertionError("nonterminating fixture unexpectedly returned")


def run_worker(module, name, timeout):
    try:
        completed = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                    "--worker", module, "--case", name],
                                   cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"outcome": "TIMEOUT", "hard_timeout_seconds": timeout}
    if completed.returncode != 0:
        return {"outcome": "WORKER_FAILURE", "returncode": completed.returncode,
                "stdout": completed.stdout, "stderr": completed.stderr}
    return json.loads(completed.stdout)


def replay(timeout=2.0):
    rows = []
    for name, classification, old_expected, new_expected in CASE_ROWS:
        old = run_worker("legacy", name, timeout)
        new = run_worker("candidate", name, timeout)
        rows.append({"case": name, "legacy_classification": classification,
                     "expected_legacy_outcome": old_expected, "legacy_observed": old,
                     "expected_candidate_outcome": new_expected, "candidate_observed": new,
                     "expectations_met": old["outcome"] == old_expected and new["outcome"] == new_expected,
                     "falsifier": "A fresh isolated replay produces a different outcome or value for this fixture."})
        print(f"{name}: legacy={old['outcome']}; candidate={new['outcome']}", file=sys.stderr, flush=True)
    sources = {}
    for name, module in MODULES.items():
        path = ROOT / (module.replace(".", "/") + ".py")
        sources[name] = {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return {"scope": "ILLUSTRATIVE deterministic software fixtures; no empirical, statistical, semantic, security, or physical claims.",
            "python": platform.python_version(), "platform": platform.platform(),
            "hard_timeout_seconds_per_worker": timeout, "fixture_count": len(rows),
            "worker_count": 2 * len(rows), "expectations_met_count": sum(row["expectations_met"] for row in rows),
            "sources": sources, "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--worker", choices=MODULES, help=argparse.SUPPRESS)
    parser.add_argument("--case", choices=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        try:
            result = fixture(importlib.import_module(MODULES[args.worker]), args.case)
        except Exception as exc:
            result = {"outcome": type(exc).__name__, "error": str(exc)}
        print(json.dumps(result, allow_nan=False))
        return
    if args.output is None:
        parser.error("--output must name a fresh JSON path")
    if not 1.5 <= args.timeout <= 10:
        parser.error("--timeout must be between 1.5 and 10 seconds")
    if args.output.exists():
        parser.error("output already exists; choose a fresh path to preserve evidence")
    result = replay(args.timeout)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    if result["expectations_met_count"] != result["fixture_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
