#!/usr/bin/env python3
"""Note 2026-11-17: executable audit of AS-RECEIVED correction specimens.

Not a bridge implementation or repair. Original files are copied unchanged into
TemporaryDirectory before ANY execution (including generator import side effects).
Only the standard library is required; optional cobc provides compiler evidence.
NaN/Infinity are serialized as strings, never non-standard JSON number tokens.
"""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "raw"
SPECIMENS = (
    "generate_copybook_as_received.py",
    "ncm_bridge_as_received.py",
    "ncm_level_walk_as_received.py",
)
BRIDGE_FIELDS = [("english", 26), ("class", 15), ("gismu", 10),
                 ("structure_status", 10), ("mapping_status", 10),
                 ("place_structure_verbatim", 147), ("audit_reason", 345)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


def split_record(record, fields):
    result, offset = {}, 0
    for name, width in fields:
        result[name] = record[offset:offset + width].rstrip()
        offset += width
    result["unparsed_characters"] = len(record) - offset
    return result


def run_command(command, cwd):
    try:
        proc = subprocess.run(command, cwd=cwd, text=True, encoding="utf-8",
                              errors="replace", capture_output=True, timeout=60)
        return {"command": command, "cwd": str(cwd), "returncode": proc.returncode,
                "stdout": proc.stdout, "stderr": proc.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "cwd": str(cwd), "error_type": type(exc).__name__,
                "error": str(exc)}


def outcome(function):
    try:
        return {"ok": True, "result": function()}
    except Exception as exc:
        return {"ok": False, "error_type": type(exc).__name__, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "original_reproduction.json")
    parser.add_argument("--artifacts-dir", type=Path, default=HERE / "original_compiler")
    parser.add_argument("--skip-compiler", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.artifacts_dir = args.artifacts_dir.resolve()
    args.artifacts_dir.mkdir(parents=True, exist_ok=True)
    originals = [HERE / name for name in SPECIMENS] + [RAW / "lojban_wordslot_reference.json", RAW / "working_notes.txt"]
    before = {str(p): digest(p) for p in originals}
    results = {"note": "2026-11-17: original snippets are correction specimens, not an implemented bridge.",
               "environment": {"python": sys.version, "platform": sys.platform},
               "original_sha256_before": before, "bridge_cases": {}, "level_cases": {},
               "generator_cases": {}}
    initial_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="experiment-bridge-originals-") as td:
        temp = Path(td)
        for path in originals:
            shutil.copy2(path, temp / path.name)
        os.chdir(temp)
        try:
            data_path = temp / "lojban_wordslot_reference.json"
            data = json.loads(data_path.read_text(encoding="utf-8"))
            results["temporary_cwd"] = str(temp)
            # This unguarded original runs on module load, safely inside temp.
            capture = io.StringIO()
            with contextlib.redirect_stdout(capture):
                generator = runpy.run_path(str(temp / SPECIMENS[0]))
            generated = temp / "lojban_ledger.cpy"
            copybook = generated.read_text(encoding="utf-8")
            shutil.copy2(generated, args.artifacts_dir / "original_lojban_ledger.cpy")
            declarations = copybook.split("      *> Place Structures", 1)[0]
            widths = [(name, int(width)) for name, width in re.findall(
                r"05\s+([A-Z-]+)\s+PIC X\((\d+)\)", declarations)]
            bridge_mod = runpy.run_path(str(temp / SPECIMENS[1]))
            walk_mod = runpy.run_path(str(temp / SPECIMENS[2]))
            Bridge, Walker = bridge_mod["NCMBridge"], walk_mod["NCMSemanticBridge"]
            results["original_main_runs"] = {
                name: run_command([sys.executable, name], temp) for name in SPECIMENS
            }
            # Also demonstrate the generator's import failure in an empty temp cwd.
            empty = temp / "empty_import_cwd"
            empty.mkdir()
            results["generator_import_without_json"] = run_command(
                [sys.executable, "-c", "import runpy; runpy.run_path(" + repr(str(temp / SPECIMENS[0])) + ")"], empty)
            results["generator_output"] = {
                "import_stdout": capture.getvalue(), "copybook_widths": widths,
                "record_bytes_declared": sum(w for _, w in widths),
                "copybook_sha256": digest(generated), "copybook_characters": len(copybook),
                "copybook_utf8_bytes": len(copybook.encode("utf-8")),
                "max_source_line_chars": max(map(len, copybook.splitlines())),
                "all_numeric_PICs": re.findall(r"PIC\s+([^\s.]+)", copybook),
                "entry_names": re.findall(r"01\s+(ENTRY-[^\n.]+)\.", copybook),
            }
            grouped = {}
            for item in data["place_structures"]:
                if item["gismu"]:
                    grouped.setdefault(item["gismu"], []).append(item)
            b = Bridge("/DOES_NOT_EXIST/codebook.json", str(data_path))
            w = Walker(str(data_path))
            results["schema"] = {
                "place_rows": len(data["place_structures"]),
                "evidential_rows": len(data["evidentials"]),
                "null_gismu_english": [i["english"] for i in data["place_structures"] if not i["gismu"]],
                "ledger_unique_keys": len(b.semantic_ledger),
                "duplicate_overwrites": {g: {"row_english_in_order": [i["english"] for i in rows],
                    "winning_english": b.semantic_ledger[g]["english"],
                    "winning_class": b.semantic_ledger[g]["class"],
                    "winning_mapping_status": b.semantic_ledger[g]["mapping_status"]}
                    for g, rows in grouped.items() if len(rows) > 1},
                "evidentials_absent_from_both_ledgers": all(i["gismu"] not in b.semantic_ledger and i["gismu"] not in w.semantic_ledger for i in data["evidentials"]),
                "ignored_codebook_path": {"provided_path_exists": False, "loaded_codebook": b.codebook},
                "ledger_aliases_loaded_json_row": b.semantic_ledger["xagmau"] is b.lojban_data["place_structures"][0],
            }

            def bridge_case(name, residual, threshold=0.3, configure=None, evidential="za'a", instance=None):
                def perform():
                    obj = instance or Bridge("missing-unused-codebook", str(data_path), threshold)
                    if configure:
                        configure(obj)
                    # For iterators do not consume before the original method.
                    record = obj.process_residual(residual, evidential)
                    distances = None if iter(residual) is residual else [obj._euclidean_distance(residual, code) for code in obj.codebook]
                    return {"residual": "one-shot iterator" if iter(residual) is residual else residual,
                            "threshold": obj.threshold, "distances": distances,
                            "record": record, "characters": len(record),
                            "utf8_bytes": len(record.encode("utf-8")),
                            "fields_using_bridge_layout": split_record(record, BRIDGE_FIELDS),
                            "fields_using_generated_layout": split_record(record, widths),
                            "void_reason_after_call": obj.void_record["mapping_reason"]}
                results["bridge_cases"][name] = outcome(perform)

            bridge_case("original_example_1", [0.15, 0.22, 0.28])
            bridge_case("original_example_2", [0.8, 0.1, 0.5], evidential="ru'a")
            bridge_case("exact_better_code", [0.1, 0.2, 0.3])
            bridge_case("exact_worse_code", [0.9, 0.8, 0.7])
            bridge_case("reserved_zero", [0.0, 0.0, 0.0])
            bridge_case("reserved_zero_neighborhood", [0.01, 0.01, 0.01])
            bridge_case("empty_residual", [])
            bridge_case("short_residual", [0.1])
            bridge_case("extra_dimension_ignored", [0.1, 0.2, 0.3, 1e9])
            bridge_case("one_shot_iterator", iter([0.15, 0.22, 0.28]))
            bridge_case("NaN_residual", [float("nan"), 0.2, 0.3])
            bridge_case("Infinity_residual", [float("inf"), 0.2, 0.3])
            bridge_case("overflow_residual", [1e308, 0.2, 0.3])
            bridge_case("NaN_threshold_accepts_far", [8, 8, 8], float("nan"))
            bridge_case("negative_threshold", [0, 0, 0], -1)
            bridge_case("string_threshold", [0.1, 0.2, 0.3], "0.3")
            bridge_case("nonnumeric_residual", ["oops", 0.2, 0.3])
            bridge_case("empty_codebook", [1, 1, 1], configure=lambda obj: setattr(obj, "codebook", []))
            bridge_case("empty_codebook_infinite_threshold", [1, 1, 1], float("inf"), configure=lambda obj: setattr(obj, "codebook", []))
            boundary = min(b._euclidean_distance([0.15, 0.22, 0.28], c) for c in b.codebook)
            bridge_case("threshold_equality_accepted", [0.15, 0.22, 0.28], boundary)
            bridge_case("just_below_threshold_rejected", [0.15, 0.22, 0.28], math.nextafter(boundary, -math.inf))
            def tied(obj):
                obj.codebook = [[0, 0, 0], [2, 0, 0]]
                obj.index_to_gismu = {0: "xagmau", 1: "xagme'a"}
            bridge_case("exact_tie_first_code_wins", [1, 0, 0], 2, tied)
            bridge_case("missing_index_map", [0.1, 0.2, 0.3], configure=lambda obj: obj.index_to_gismu.clear())
            bridge_case("unvalidated_evidential", [0.1, 0.2, 0.3], evidential="not-a-cmavo")
            bridge_case("evidential_overwrites_audit_aperture", [0.1, 0.2, 0.3], evidential="X" * 400)
            bridge_case("newline_in_evidential", [0.1, 0.2, 0.3], evidential="za'a\nINJECTED")
            shared = Bridge("missing", str(data_path), 0.3)
            bridge_case("mutation_first_far", [0.8, 0.1, 0.5], instance=shared)
            bridge_case("mutation_then_zero_stale_reason", [0, 0, 0], instance=shared)
            def snura_code(obj):
                obj.codebook = [[1, 1, 1]]
                obj.index_to_gismu = {0: "snura"}
            bridge_case("raw_unicode_recall_check", [1, 1, 1], configure=snura_code)
            oversized = {"english": "E" * 30, "class": "C" * 20, "gismu": "G" * 15,
                         "structure_status": "S" * 12, "mapping_status": "M" * 12,
                         "place_structure_verbatim": "é" * 200, "mapping_reason": "R" * 400}
            record = b._generate_cobol_record(oversized, "za'a", 1.23456789)
            results["bridge_explicit_truncation"] = {"input": oversized, "record": record,
                "characters": len(record), "utf8_bytes": len(record.encode("utf-8")),
                "fields": split_record(record, BRIDGE_FIELDS)}

            class ObservedWalker(Walker):
                """Observe arguments; call the original formatter and walker unchanged."""
                def __init__(self, path):
                    super().__init__(path)
                    self.transitions = []
                def format_cobol_entry(self, level_idx, z_hat, residual, code_gismu, distance, error_reduction):
                    record = super().format_cobol_entry(level_idx, z_hat, residual, code_gismu, distance, error_reduction)
                    self.transitions.append({"level_idx": level_idx, "z_hat": list(z_hat),
                        "residual": list(residual), "gismu": code_gismu, "distance": distance,
                        "L1_error": sum(abs(x) for x in residual), "L1_error_reduction": error_reduction,
                        "record_characters": len(record), "record_utf8_bytes": len(record.encode("utf-8")),
                        "record": record})
                    return record

            hierarchy = [
                {"threshold": 0.5, "map": {0: "xamgu", 1: "xlali"}, "codebook": [[0.5, 0.5, 0], [-0.5, -0.5, 0]]},
                {"threshold": 0.3, "map": {0: "xagmau", 1: "mapti"}, "codebook": [[0.3, 0.4, 0.1], [0, 0, 0.5]]},
                {"threshold": 0.1, "map": {0: "ckape", 1: "snura"}, "codebook": [[0.05, 0.1, 0], [0, 0.05, 0]]},
            ]
            def level_case(name, target, levels):
                def perform():
                    obj = ObservedWalker(str(data_path))
                    ledger = obj.walk_levels(target, levels)
                    return {"target": target, "levels": levels, "transitions": obj.transitions,
                            "record_count": len(ledger)}
                results["level_cases"][name] = outcome(perform)
            def level(code, threshold=0, mapping=None):
                return {"codebook": [code], "threshold": threshold,
                        "map": {0: "xagmau"} if mapping is None else mapping}
            level_case("original_three_level_example", [0.8, 0.9, 0.1], hierarchy)
            changed = copy.deepcopy(hierarchy)
            changed[0]["threshold"] = 0.51
            level_case("fixture_only_first_bound_0_51", [0.8, 0.9, 0.1], changed)
            level_case("no_levels", [1, 2], [])
            level_case("empty_target", [], [level([1, 2])])
            level_case("short_code_drops_dimension_false_perfection", [1, 99], [level([1]), level([1, 1])])
            level_case("empty_code_drops_all_dimensions", [1, 99], [level([])])
            level_case("long_code_ignored_dimensions", [1], [level([1, 99])])
            level_case("empty_codebook", [1], [{"codebook": [], "threshold": 1, "map": {}}])
            level_case("empty_codebook_infinite_bound", [1], [{"codebook": [], "threshold": float("inf"), "map": {-1: "xagmau"}}])
            level_case("NaN_target", [float("nan"), 1], [level([0, 0], 1), level([1, 1], 1)])
            level_case("Infinity_target", [float("inf")], [level([0], 1)])
            level_case("NaN_bound_accepts_far", [100], [level([1], float("nan"))])
            level_case("missing_map_accepts_effort_as_VOID", [1], [level([1], mapping={})])
            level_case("missing_semantic_row_xlali", [1], [level([1], mapping={0: "xlali"})])
            level_case("raw_snura_overwrite", [1], [level([1], mapping={0: "snura"})])
            level_case("negative_error_reduction_accepted", [1], [level([3], 2)])
            level_case("zero_target_not_checked_before_step", [0], [level([0.5], 1)])
            level_case("missing_threshold_key", [1], [{"codebook": [[1]], "map": {0: "xagmau"}}])
            level_case("overflow_target", [1e308], [level([0], 1)])
            level_case("nonnumeric_target", ["oops"], [level([0], 1)])
            examples = [(1, [1, -1], [1, -1], "xagmau", 0, 0),
                        (1, [0, 0], [0, 0], "xagmau", 0, 0),
                        (1, [-1], [-2], "xagmau", 1.234567, -1),
                        (123456, [12345678], [1], "xagmau", 1, 0),
                        (1, [float("nan")], [float("inf")], "xagmau", float("nan"), float("nan"))]
            results["level_formatter_cases"] = []
            for values in examples:
                text = w.format_cobol_entry(*values)
                results["level_formatter_cases"].append({"arguments": values, "record": text,
                    "characters": len(text), "utf8_bytes": len(text.encode("utf-8")),
                    "contains_verbatim_structure": data["place_structures"][0]["place_structure_verbatim"] in text})
            results["level_same_sum_vector_collision"] = results["level_formatter_cases"][0]["record"] == results["level_formatter_cases"][1]["record"]

            # Schema/format fixtures are inputs, not edits to the specimen.
            minimal_row = {"english": "test", "class": "judgment", "gismu": "mapti",
                           "structure_status": "OBSERVED", "mapping_status": "PROPOSED",
                           "place_structure_verbatim": "x1 fits x2.", "mapping_reason": "test reason"}
            fixtures = {"minimal_valid": {"place_structures": [minimal_row], "evidentials": []},
                        "empty_arrays": {"place_structures": [], "evidentials": []}}
            for name, changes in {
                "ascii_apostrophe": {"gismu": "xagme'a"},
                "unicode_char_byte_width": {"mapping_reason": "é" * 100},
                "overlong_status": {"mapping_status": "STATUS-TOO-LONG"},
                "name_parenthesis": {"english": "glare (recall check)"},
                "name_collision": {"english": "abcdefghijklmno FIRST"},
                "null_reason": {"mapping_reason": None},
                "null_struct_and_gismu": {"gismu": None, "place_structure_verbatim": None},
                "valsi_instead_of_gismu": {"valsi": "mapti"},
            }.items():
                row = dict(minimal_row, **changes)
                if name == "valsi_instead_of_gismu":
                    row.pop("gismu")
                rows = [row]
                if name == "name_collision":
                    rows.append(dict(row, english="abcdefghijklmno SECOND"))
                fixtures[name] = {"place_structures": rows, "evidentials": []}
            compiler = shutil.which("cobc") if not args.skip_compiler else None
            results["compiler"] = {"available": bool(compiler), "skipped": args.skip_compiler}
            if compiler:
                results["compiler"]["version"] = run_command([compiler, "-V"], temp)
                help_run = run_command([compiler, "--help"], temp)
                (args.artifacts_dir / "cobc_help.txt").write_text(help_run.get("stdout", "") + help_run.get("stderr", ""), encoding="utf-8")
                (args.artifacts_dir / "cobc_version.txt").write_text(results["compiler"]["version"].get("stdout", "") + results["compiler"]["version"].get("stderr", ""), encoding="utf-8")

            def compile_copybook(source, label):
                case_dir = temp / ("compile_" + label)
                case_dir.mkdir()
                (case_dir / "ledger.cpy").write_text(source, encoding="utf-8")
                wrapper = "identification division.\nprogram-id. original-audit.\ndata division.\nworking-storage section.\ncopy 'ledger.cpy'.\nprocedure division.\n    goback.\n"
                (case_dir / "wrapper.cob").write_text(wrapper, encoding="utf-8")
                dest = args.artifacts_dir / label
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(case_dir / "ledger.cpy", dest / "ledger.cpy")
                shutil.copy2(case_dir / "wrapper.cob", dest / "wrapper.cob")
                result = run_command([compiler, "-free", "-Wall", "-fsyntax-only", "-I", ".", "wrapper.cob"], case_dir)
                (dest / "command.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                (dest / "stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
                (dest / "stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
                return result
            if compiler:
                results["compiler"]["original_generated_copybook"] = compile_copybook(copybook, "original_generated")
                full = run_command([compiler, "-free", "-Wall", "-x", "-I", ".", "-o", "original-audit", "wrapper.cob"], temp / "compile_original_generated")
                results["compiler"]["original_generated_copybook_full_compile"] = full
                (args.artifacts_dir / "original_generated" / "full_compile.json").write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            for name, fixture in fixtures.items():
                fixture_path = temp / (name + ".json")
                fixture_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
                out_path = temp / (name + ".cpy")
                def produce():
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout):
                        generator["generate_cobol_copybook"](str(fixture_path), str(out_path))
                    text = out_path.read_text(encoding="utf-8")
                    result = {"input": fixture, "stdout": stdout.getvalue(), "copybook": text}
                    if compiler:
                        result["compiler"] = compile_copybook(text, name)
                        if name in ("unicode_char_byte_width", "overlong_status"):
                            case_dir = temp / ("compile_" + name)
                            runtime_wrapper = "identification division.\nprogram-id. fixture-observation.\ndata division.\nworking-storage section.\ncopy 'ledger.cpy'.\nprocedure division.\n    display ENTRY-TEST\n    goback.\n"
                            (case_dir / "runtime.cob").write_text(runtime_wrapper, encoding="utf-8")
                            built = run_command([compiler, "-free", "-Wall", "-x", "-I", ".", "-o", "runtime", "runtime.cob"], case_dir)
                            ran = run_command([str(case_dir / "runtime")], case_dir) if built.get("returncode") == 0 else None
                            result["runtime"] = {"compile": built, "run": ran,
                                "unicode_e_acute_count": ran.get("stdout", "").count("é") if ran else None}
                            shutil.copy2(case_dir / "runtime.cob", args.artifacts_dir / name / "runtime.cob")
                            (args.artifacts_dir / name / "runtime.json").write_text(json.dumps(result["runtime"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    return result
                results["generator_cases"][name] = outcome(produce)
                if name == "valsi_instead_of_gismu":
                    results["schema"]["valsi_key_bridge"] = outcome(lambda: Bridge("missing", str(fixture_path)))
                    results["schema"]["valsi_key_walker"] = outcome(lambda: Walker(str(fixture_path)))
            # outcome objects above would not JSON serialize if successful; these
            # calls are expected KeyError, and retain only class names if not.
            for key in ("valsi_key_bridge", "valsi_key_walker"):
                if results["schema"][key]["ok"]:
                    results["schema"][key]["result"] = type(results["schema"][key]["result"]).__name__

            if compiler:
                # Independent language probes; never repair the original copybook.
                # Demonstrate VALUE initialization is not immutability, and MOVE
                # to a short PIC X can silently truncate at runtime.
                probe_dir = temp / "language_probes"
                probe_dir.mkdir()
                probe_source = """identification division.
program-id. aperture-probe.
data division.
working-storage section.
01 initial-value pic x(4) value 'VOID'.
01 oversized-source pic x(6) value 'abcdef'.
01 aperture pic x(3).
01 decimal-aperture pic 9v99.
procedure division.
    move 'PASS' to initial-value
    move oversized-source to aperture
    move 1.239 to decimal-aperture
    display 'INITIAL=' initial-value
    display 'APERTURE=' aperture
    display 'DECIMAL=' decimal-aperture
    goback.
"""
                (probe_dir / "probe.cob").write_text(probe_source, encoding="utf-8")
                compiled = run_command([compiler, "-free", "-Wall", "-x", "-o", "probe", "probe.cob"], probe_dir)
                executed = run_command([str(probe_dir / "probe")], probe_dir) if compiled.get("returncode") == 0 else None
                results["compiler"]["independent_language_probes"] = {"source": probe_source, "compile": compiled, "run": executed}
                dest = args.artifacts_dir / "language_probes"
                dest.mkdir(exist_ok=True)
                (dest / "probe.cob").write_text(probe_source, encoding="utf-8")
                (dest / "evidence.json").write_text(json.dumps(results["compiler"]["independent_language_probes"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        finally:
            os.chdir(initial_cwd)
    after = {str(p): digest(p) for p in originals}
    results["original_sha256_after"] = after
    results["originals_unchanged"] = before == after
    results["temporary_execution_directory_removed"] = not Path(results["temporary_cwd"]).exists()
    def emitted(name):
        return results["bridge_cases"][name]["result"]["fields_using_bridge_layout"]
    checks = {
        "originals_unchanged": results["originals_unchanged"],
        "execution_cwd_removed": results["temporary_execution_directory_removed"],
        "dynamic_copybook_widths": [w for _, w in widths] == [12, 36, 15, 10, 10, 10, 402, 290],
        "bridge_example1_0_0574": "Dist: 0.0574" in emitted("original_example_1")["audit_reason"],
        "bridge_example2_0_7348": "Dist: 0.7348" in emitted("original_example_2")["audit_reason"],
        "empty_residual_false_better": emitted("empty_residual")["english"] == "better",
        "one_shot_iterator_false_worse": emitted("one_shot_iterator")["english"] == "worse",
        "reserved_zero_stale_reason": "Distance: 0.7348" in emitted("mutation_then_zero_stale_reason")["audit_reason"],
        "Unicode_bridge_not_byte_fixed": results["bridge_cases"]["raw_unicode_recall_check"]["result"]["utf8_bytes"] > 563,
        "original_level_example_all_VOID": all(t["gismu"] == "VOID" for t in results["level_cases"]["original_three_level_example"]["result"]["transitions"]),
        "short_code_drops_dimension": results["level_cases"]["short_code_drops_dimension_false_perfection"]["result"]["transitions"][0]["residual"] == [0.0],
        "same_sum_record_collision": results["level_same_sum_vector_collision"],
        "valsi_schema_KeyError": results["schema"]["valsi_key_bridge"].get("error_type") == "KeyError",
    }
    if compiler:
        checks["original_full_compile_failed"] = results["compiler"]["original_generated_copybook_full_compile"].get("returncode", 0) != 0
        checks["Unicode_original_generator_truncates_bytes"] = results["generator_cases"]["unicode_char_byte_width"]["result"]["runtime"]["unicode_e_acute_count"] == 50
        checks["VALUE_is_initialization_and_MOVE_truncates"] = results["compiler"]["independent_language_probes"]["run"]["stdout"] == "INITIAL=PASS\nAPERTURE=abc\nDECIMAL=1.23\n"
    results["checks"] = checks
    results["all_checks_passed"] = all(checks.values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(safe(results), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("Results:", args.output)
    print("Compiler artifacts:", args.artifacts_dir)
    print("Originals unchanged:", results["originals_unchanged"])
    print("Compiler available:", results["compiler"]["available"])
    print("Bridge cases:", len(results["bridge_cases"]), "Level cases:", len(results["level_cases"]), "Generator cases:", len(results["generator_cases"]))
    print("Checks passed:", results["all_checks_passed"])
    return 0 if results["all_checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
