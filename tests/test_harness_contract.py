"""HC-1..6: the implementation contract, and what makes its guard FAIL.

Stdlib only. The harness exists so that several implementations of one geometric
spec can be compared by CONDITIONS without a leaderboard. These tests pin the
parts that would quietly rot: a manifest that lies about itself, a status that
renders as a blank, a SELECTION.md that grows a "best" column, a reference field
that drifts from the spec's own source definitions, and a harness that imports
something outside the standard library.
"""

import ast
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "harness"))

import contract as C  # noqa: E402
import probe as P  # noqa: E402
import run as R  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STDLIB = set(getattr(sys, "stdlib_module_names", ()))


def _manifest(**over):
    m = {"name": "fake", "language": "python", "dependencies": [], "build_required": False,
         "build_command": None, "runs_on_phone": "unknown", "algorithm": "does nothing",
         "author_claim": "suits nothing", "entry": ["{python}", "impl.py"], "covers": ["*"]}
    m.update(over)
    return m


class TestHC1Manifest(unittest.TestCase):
    """HC-1: a manifest is validated field by field, and its name must be its folder."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "implementations", "fake")
        os.makedirs(self.dir)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, m):
        p = os.path.join(self.dir, "MANIFEST.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(m, fh)
        return p

    def test_valid_manifest_loads(self):
        m = C.load_manifest(self._write(_manifest()))
        self.assertEqual(m["name"], "fake")
        self.assertTrue(m["_dir"].endswith("fake"))

    def test_every_required_field_is_required(self):
        for key in C.MANIFEST_SCHEMA:
            m = _manifest()
            del m[key]
            with self.assertRaises(C.ContractError, msg=key) as cm:
                C.load_manifest(self._write(m))
            self.assertIn(key, str(cm.exception))

    def test_name_must_equal_folder(self):
        with self.assertRaises(C.ContractError):
            C.load_manifest(self._write(_manifest(name="other")))

    def test_build_fields_must_agree(self):
        with self.assertRaises(C.ContractError):
            C.load_manifest(self._write(_manifest(build_required=True, build_command=None)))
        with self.assertRaises(C.ContractError):
            C.load_manifest(self._write(_manifest(build_required=False, build_command="make")))

    def test_runs_on_phone_is_three_valued(self):
        with self.assertRaises(C.ContractError):
            C.load_manifest(self._write(_manifest(runs_on_phone="maybe")))
        for v in (True, False, "unknown"):
            C.load_manifest(self._write(_manifest(runs_on_phone=v)))

    def test_algorithm_is_one_line(self):
        with self.assertRaises(C.ContractError):
            C.load_manifest(self._write(_manifest(algorithm="two\nlines")))

    def test_shipped_manifests_validate_and_are_two(self):
        names = [m["name"] for m in C.discover(ROOT)]
        self.assertEqual(names, ["py_octree", "uniform_grid"])


class TestHC2SpecAndReference(unittest.TestCase):
    """HC-2: the spec is versioned and the reference is the spec's own physics."""

    def test_spec_is_versioned_and_probes_are_seeded(self):
        w = C.load_workloads(os.path.join(ROOT, "harness", "workloads.json"))[0]
        a, b = C.make_spec(w, 16), C.make_spec(w, 16)
        self.assertEqual(a["spec_version"], C.SPEC_VERSION)
        self.assertEqual(a["probes"], b["probes"])
        self.assertEqual(len(a["probes"]), C.PROBE_COUNT)
        bad = dict(a, spec_version=99)
        with self.assertRaises(C.ContractError):
            C.validate_spec(bad)

    def test_single_charge_reference_is_coulomb(self):
        spec = {"spec_version": 1, "workload": "t", "conditions": {}, "bounds": {"min": [-1] * 3, "max": [1] * 3},
                "resolution": 2, "sources": [{"type": "charge", "position": [0, 0, 0], "strength": 1e-9}],
                "probes": [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0]]}
        ref = C.reference_field(spec)
        self.assertAlmostEqual(ref["E"][0][0], C.K_E * 1e-9, places=6)
        self.assertAlmostEqual(ref["E"][1][1], C.K_E * 1e-9 / 4, places=6)
        self.assertEqual(ref["B"][0], [0.0, 0.0, 0.0])

    def test_current_element_reference_matches_engine_definition(self):
        # the Engine's element: midpoint of start..end, dl = end - start, default end = position + 1
        spec = {"spec_version": 1, "workload": "t", "conditions": {}, "bounds": {"min": [-1] * 3, "max": [1] * 3},
                "resolution": 2, "sources": [{"type": "current", "position": [0, 0, 0], "strength": 2.0}],
                "probes": [[0.5, 0.5, 2.5]]}
        ref = C.reference_field(spec)
        # r from midpoint (0.5,0.5,0.5) is (0,0,2); dl=(1,1,1); dl x rhat = (1,-1,0); |B| = 1e-7*2*sqrt2/4
        self.assertAlmostEqual(ref["B"][0][0], 1e-7 * 2 / 4, places=12)
        self.assertAlmostEqual(ref["B"][0][1], -1e-7 * 2 / 4, places=12)
        self.assertEqual(ref["E"][0], [0.0, 0.0, 0.0])

    def test_accuracy_is_median_relative_error_and_none_without_reference(self):
        ref = {"E": [[1, 0, 0], [0, 2, 0], [0, 0, 4]], "B": [[0, 0, 0]] * 3}
        got = {"E": [[1.1, 0, 0], [0, 2, 0], [0, 0, 2]], "B": [[1, 0, 0]] * 3}
        acc = C.accuracy(ref, got)
        self.assertAlmostEqual(acc["E"], 0.1)
        self.assertIsNone(acc["B"])
        with self.assertRaises(C.ContractError):
            C.accuracy(ref, {"E": [[1, 0, 0]], "B": []})

    def test_workload_conditions_are_enumerated(self):
        w = {"name": "x", "sources": [], "bounds": {"min": [0] * 3, "max": [1] * 3},
             "conditions": {"sparsity": "sparse", "scale_separation": "single"}}
        with self.assertRaises(C.ContractError):
            C.validate_workload(w)


class TestHC3Status(unittest.TestCase):
    """HC-3: every status is first-class and none renders blank."""

    def test_every_kind_renders_nonblank_and_carries_its_reason(self):
        self.assertEqual(C.render_status(C.status("OK")), "OK")
        for kind in ("NOT_RUNNABLE", "TIMEOUT", "FAILED", "NOT_APPLICABLE"):
            s = C.render_status(C.status(kind, "why"))
            self.assertTrue(s.startswith(kind + "("), s)
            self.assertIn("why", s)
            with self.assertRaises(C.ContractError):
                C.status(kind)                    # a non-OK status without a reason is refused

    def test_unknown_kind_refused(self):
        with self.assertRaises(C.ContractError):
            C.status("SKIPPED", "x")


class TestHC4Selection(unittest.TestCase):
    """HC-4: SELECTION.md ranks nothing, hides nothing, counts what it could not measure."""

    def _records(self):
        ws = C.load_workloads(os.path.join(ROOT, "harness", "workloads.json"))
        ok = C.result_record("py_octree", "dipole", 16, C.status("OK"), wall_time=0.1, peak_memory_mb=40.0,
                             accuracy_vs_reference={"E": 0.12, "B": None}, conditions=ws[0]["conditions"], run_id="r")
        nr = C.result_record("uniform_grid", "dipole", 16, C.status("NOT_RUNNABLE", "missing dependency numpy"),
                             conditions=ws[0]["conditions"], run_id="r")
        na = C.result_record("py_octree", "quadrupole", 16, C.status("NOT_APPLICABLE", "manifest covers ['dipole']"),
                             conditions=ws[1]["conditions"], run_id="r")
        return [ok, nr, na], ws

    def test_not_runnable_is_rendered_with_its_reason(self):
        recs, ws = self._records()
        text = R.render_selection(recs, C.discover(ROOT), ws)
        self.assertIn("NOT_RUNNABLE(missing dependency numpy)", text)
        self.assertIn("NOT_APPLICABLE(manifest covers ['dipole'])", text)
        self.assertIn("0.1000 s · 40 MB · E 1.20e-01", text)

    def test_no_best_no_rank_no_winner(self):
        recs, ws = self._records()
        text = R.render_selection(recs, C.discover(ROOT), ws).lower()
        for word in ("best", "rank", "winner", "fastest", "leader"):
            self.assertNotIn(word, text, word)

    def test_undeclared_conditions_are_counted_at_the_top_and_named(self):
        recs, ws = self._records()
        text = R.render_selection(recs, C.discover(ROOT), ws)
        self.assertIn("cells NOT_MEASURED", text)
        self.assertIn("NOT_MEASURED(no workload in this order declares sparsity=dense, scale_separation=single)", text)
        self.assertIn("NOT_MEASURED(no compiled implementation in this order", text)

    def test_generated_header_and_every_cell_present(self):
        recs, ws = self._records()
        text = R.render_selection(recs, C.discover(ROOT), ws)
        self.assertTrue(text.startswith("# SELECTION.md — GENERATED"))
        self.assertIn("NOT_MEASURED(no record)", text)   # uniform_grid on quadrupole has no record

    def test_committed_selection_is_the_render_of_committed_results(self):
        recs = R.load_results()
        if not recs:
            self.skipTest("no results committed")
        with open(R.SELECTION, encoding="utf-8") as fh:
            committed = fh.read()
        rendered = R.render_selection(recs, C.discover(ROOT), C.load_workloads(R.WORKLOADS), P.probe_all(ROOT))
        # the probe column depends on this machine; compare everything below it
        self.assertEqual(committed.split("## Field sparsity")[1], rendered.split("## Field sparsity")[1])


class TestHC5RunCell(unittest.TestCase):
    """HC-5: a failing, hanging or non-answering implementation becomes a record, not a crash."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "implementations", "fake")
        os.makedirs(self.dir)
        self.w = C.load_workloads(os.path.join(ROOT, "harness", "workloads.json"))[0]

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _impl(self, body):
        with open(os.path.join(self.dir, "impl.py"), "w", encoding="utf-8") as fh:
            fh.write("import sys, os, json, time\n"
                     f"sys.path.insert(0, {os.path.join(ROOT, 'harness')!r})\n"
                     "import contract\n"
                     "spec_path, out_path = contract.impl_args(sys.argv[1:])\n"
                     "spec = contract.read_spec(spec_path)\n" + body)
        m = _manifest()
        m["_dir"] = self.dir
        return m

    def test_failure_becomes_FAILED_with_stderr_tail(self):
        m = self._impl("raise RuntimeError('boom')\n")
        rec = R.run_cell(m, self.w, 8, timeout=30, repeats=1)
        self.assertEqual(rec["status"]["kind"], "FAILED")
        self.assertIn("boom", rec["status"]["reason"])

    def test_hang_becomes_TIMEOUT_with_limit(self):
        m = self._impl("time.sleep(30)\n")
        rec = R.run_cell(m, self.w, 8, timeout=1, repeats=1)
        self.assertEqual(rec["status"]["kind"], "TIMEOUT")
        self.assertEqual(rec["status"]["reason"], "1s")

    def test_honest_answer_becomes_OK_with_zero_error(self):
        m = self._impl("ref = contract.reference_field(spec)\n"
                       "contract.finish(out_path, 0.001, 1, ref)\n")
        rec = R.run_cell(m, self.w, 8, timeout=30, repeats=2)
        self.assertEqual(rec["status"]["kind"], "OK")
        self.assertAlmostEqual(rec["accuracy_vs_reference"]["E"], 0.0)
        self.assertEqual(rec["repeats"], 2)

    def test_malformed_answer_becomes_FAILED(self):
        m = self._impl("contract.finish(out_path, 0.001, 1, {'E': [[0,0,0]], 'B': []})\n")
        rec = R.run_cell(m, self.w, 8, timeout=30, repeats=1)
        self.assertEqual(rec["status"]["kind"], "FAILED")
        self.assertIn("probe answer malformed", rec["status"]["reason"])


class TestHC6StdlibScope(unittest.TestCase):
    """HC-6: harness/ imports nothing outside the standard library; dependencies live in manifests."""

    def test_harness_is_stdlib_only(self):
        for name in ("contract.py", "probe.py", "run.py"):
            path = os.path.join(ROOT, "harness", name)
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                for mod in mods:
                    self.assertTrue(mod in STDLIB or mod in ("contract", "probe", "run"),
                                    f"{name} imports {mod}")

    def test_probe_reports_a_missing_dependency_as_not_runnable(self):
        m = _manifest(dependencies=["no_such_module_xyz"])
        m["_dir"] = os.path.join(ROOT, "implementations", "py_octree")
        r = P.probe_one(m)
        self.assertFalse(r["runnable"])
        self.assertIn("missing dependency no_such_module_xyz", r["reason"])

    def test_probe_reports_missing_compiler_only_when_build_required(self):
        m = _manifest(build_required=True, build_command="make")
        m["_dir"] = os.path.join(ROOT, "implementations", "py_octree")
        r = P.probe_one(m)
        has_cc = P.compiler() is not None
        self.assertEqual(any("compiler" in c for c in r["checks"]), True)
        if not has_cc:
            self.assertIn("no compiler", r["reason"])


if __name__ == "__main__":
    unittest.main()
