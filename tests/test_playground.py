"""PG-1..8: the open bench, and whether its gates can actually close.

Stdlib only. A bench that certifies everything is worse than no bench, so
every verdict is tested by constructing a candidate that must receive it.
The candidates here are synthetic module objects -- the bench takes a module,
not a filename, precisely so this suite can hand it deliberately broken ones.
"""

import json
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from playground import playground as P  # noqa: E402
from playground.candidates import lomb_scargle_gls as GLS  # noqa: E402


def candidate(**kw):
    """Build a synthetic candidate module. Defaults are a valid one."""
    m = types.ModuleType(kw.pop("name", "synthetic"))
    m.PROBLEM = kw.pop("PROBLEM", "FCL-12b")
    m.CLAIM = kw.pop("CLAIM", "a claim")
    m.KIND = kw.pop("KIND", "CODE")
    m.AUTHOR = kw.pop("AUTHOR", "test")
    m.NEEDS_NULL = kw.pop("NEEDS_NULL", False)
    m.MATERIAL = kw.pop("MATERIAL", None)
    m.solve = kw.pop("solve", lambda: 1.0)
    m.broken = kw.pop("broken", lambda: -1.0)
    m.checks = kw.pop("checks",
                      lambda a: [("positive", a > 0, "value %s" % a)])
    if "null" in kw:
        m.null = kw.pop("null")
    for k, v in kw.items():
        setattr(m, k, v)
    return m


# ---------------------------------------------------------------- PG-1
class TestTheHappyPath(unittest.TestCase):

    def test_a_well_formed_candidate_survives(self):
        r = P.evaluate_module(candidate())
        self.assertEqual(r["verdict"], "SURVIVES")

    def test_survives_records_what_it_cleared(self):
        r = P.evaluate_module(candidate())
        self.assertIn("rejected broken()", r["reason"])

    def test_the_checks_are_reported_verbatim(self):
        r = P.evaluate_module(candidate())
        self.assertEqual(r["checks"][0]["check"], "positive")
        self.assertTrue(r["checks"][0]["ok"])


# ---------------------------------------------------------------- PG-2
class TestUnfalsifiableIsRejected(unittest.TestCase):
    """The gate that would have caught VAC-1, ATT-1's run(), and the AISS
    shape suite."""

    def test_checks_that_pass_their_own_broken_case_are_rejected(self):
        r = P.evaluate_module(candidate(
            checks=lambda a: [("non-negative variance", True, "always")]))
        self.assertEqual(r["verdict"], "REJECTED_UNFALSIFIABLE")

    def test_the_shipped_tautology_demo_is_rejected(self):
        r = P.evaluate("tautology_demo")
        self.assertEqual(r["verdict"], "REJECTED_UNFALSIFIABLE")

    def test_it_is_not_enough_for_only_some_checks_to_be_falsifiable(self):
        """One check that CAN fail is enough -- but it must actually fail on
        broken(), not merely be capable of it in principle."""
        r = P.evaluate_module(candidate(
            broken=lambda: 1.0,          # broken() is not actually broken
            checks=lambda a: [("positive", a > 0, str(a))]))
        self.assertEqual(r["verdict"], "REJECTED_UNFALSIFIABLE")

    def test_which_checks_caught_the_broken_case_are_named(self):
        r = P.evaluate_module(candidate())
        self.assertEqual(r["broken_caught"], ["positive"])


# ---------------------------------------------------------------- PG-3
class TestNullArtifactIsRejected(unittest.TestCase):
    """The gate that killed the seventeen-lens isomorphism and the flat
    merit weights."""

    def test_a_result_noise_also_produces_is_rejected(self):
        r = P.evaluate_module(candidate(
            NEEDS_NULL=True, null=lambda: 5.0))   # null passes 'positive'
        self.assertEqual(r["verdict"], "REJECTED_NULL_ARTIFACT")

    def test_a_result_noise_does_not_produce_survives(self):
        r = P.evaluate_module(candidate(NEEDS_NULL=True, null=lambda: -5.0))
        self.assertEqual(r["verdict"], "SURVIVES")
        self.assertEqual(r["null_caught"], ["positive"])

    def test_a_statistical_claim_without_a_null_is_a_contract_error(self):
        m = candidate(NEEDS_NULL=True)
        r = P.evaluate_module(m)
        self.assertEqual(r["verdict"], "REJECTED_CONTRACT")
        self.assertIn("null() is missing", r["reason"])

    def test_the_null_is_not_run_when_the_claim_is_not_statistical(self):
        r = P.evaluate_module(candidate(NEEDS_NULL=False,
                                        null=lambda: 5.0))
        self.assertEqual(r["verdict"], "SURVIVES")
        self.assertNotIn("null_caught", r)


# ---------------------------------------------------------------- PG-4
class TestContractIsEnforced(unittest.TestCase):

    def _missing(self, attr):
        m = candidate()
        delattr(m, attr)
        return P.evaluate_module(m)

    def test_every_required_attribute_is_required(self):
        for attr in ("PROBLEM", "CLAIM", "KIND", "AUTHOR", "NEEDS_NULL"):
            r = self._missing(attr)
            self.assertEqual(r["verdict"], "REJECTED_CONTRACT", msg=attr)
            self.assertIn(attr, r["reason"])

    def test_every_required_callable_is_required(self):
        for fn in ("solve", "checks", "broken"):
            r = self._missing(fn)
            self.assertEqual(r["verdict"], "REJECTED_CONTRACT", msg=fn)

    def test_an_unknown_problem_id_is_refused(self):
        r = P.evaluate_module(candidate(PROBLEM="FCL-9999"))
        self.assertEqual(r["verdict"], "REJECTED_CONTRACT")
        self.assertIn("no such problem", r["reason"])

    def test_an_unknown_kind_is_refused(self):
        r = P.evaluate_module(candidate(KIND="VIBES"))
        self.assertEqual(r["verdict"], "REJECTED_CONTRACT")

    def test_an_empty_claim_is_refused(self):
        r = P.evaluate_module(candidate(CLAIM="   "))
        self.assertEqual(r["verdict"], "REJECTED_CONTRACT")

    def test_a_wrongly_typed_attribute_is_refused(self):
        r = P.evaluate_module(candidate(NEEDS_NULL="yes"))
        self.assertEqual(r["verdict"], "REJECTED_CONTRACT")
        self.assertIn("must be bool", r["reason"])

    def test_a_candidate_with_no_checks_at_all_raises(self):
        with self.assertRaises(ValueError):
            P.evaluate_module(candidate(checks=lambda a: []))

    def test_malformed_check_rows_raise(self):
        with self.assertRaises(ValueError):
            P.evaluate_module(candidate(checks=lambda a: [("only", True)]))


# ---------------------------------------------------------------- PG-5
class TestFailedIsDistinctFromRejected(unittest.TestCase):

    def test_a_candidate_whose_own_checks_fail_is_FAILED(self):
        r = P.evaluate_module(candidate(solve=lambda: -1.0))
        self.assertEqual(r["verdict"], "FAILED")
        self.assertIn("positive", r["reason"])

    def test_failing_is_reported_before_the_falsifiability_gate(self):
        """A candidate that does not work is FAILED, not UNFALSIFIABLE --
        the two are different findings and get different next steps."""
        r = P.evaluate_module(candidate(solve=lambda: -1.0,
                                        broken=lambda: -2.0))
        self.assertEqual(r["verdict"], "FAILED")


# ---------------------------------------------------------------- PG-6
class TestSymmetryVeto(unittest.TestCase):

    def test_a_forbidden_mechanism_in_silicon_is_vetoed(self):
        r = P.evaluate_module(candidate(
            MATERIAL="silicon", PROBLEM="SI-E",
            CLAIM="read the state by ESR of the bond spin"))
        self.assertEqual(r["verdict"], "REJECTED_VETO")
        self.assertIn("esr", r["reason"])

    def test_an_allowed_mechanism_passes(self):
        r = P.evaluate_module(candidate(
            MATERIAL="silicon", PROBLEM="SI-E",
            CLAIM="read the state piezoresistively at 0.1% strain"))
        self.assertEqual(r["verdict"], "SURVIVES")

    def test_no_material_means_no_veto_surface(self):
        r = P.evaluate_module(candidate(
            MATERIAL=None, CLAIM="magnetostriction and esr everywhere"))
        self.assertEqual(r["verdict"], "SURVIVES")

    def test_the_veto_runs_last_so_a_broken_claim_fails_first(self):
        r = P.evaluate_module(candidate(
            MATERIAL="silicon", PROBLEM="SI-E", solve=lambda: -1.0,
            CLAIM="esr readout"))
        self.assertEqual(r["verdict"], "FAILED")


# ---------------------------------------------------------------- PG-7
class TestRegistry(unittest.TestCase):

    def test_it_parses_and_is_not_empty(self):
        self.assertGreater(len(P.problems()["problems"]), 0)

    def test_every_problem_is_well_formed(self):
        for p in P.problems()["problems"]:
            for k in ("id", "title", "state", "kind", "statement",
                      "acceptance"):
                self.assertIn(k, p, msg=p.get("id"))
            self.assertIn(p["kind"], P.KINDS, msg=p["id"])
            self.assertTrue(p["statement"].strip(), msg=p["id"])

    def test_problem_ids_are_unique(self):
        ids = [p["id"] for p in P.problems()["problems"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_bench_problem_names_what_would_settle_it(self):
        for p in P.problems()["problems"]:
            if p["kind"] == "BENCH":
                self.assertTrue(p.get("would_count"), msg=p["id"])

    def test_lookup_of_an_unknown_id_lists_the_known_ones(self):
        with self.assertRaises(KeyError) as ctx:
            P.problem("nope")
        self.assertIn("FCL-5a", str(ctx.exception))

    def test_the_shipped_candidates_all_name_a_real_problem(self):
        ids = {p["id"] for p in P.problems()["problems"]}
        for name in P.candidates():
            self.assertIn(P.load(name).PROBLEM, ids, msg=name)


# ---------------------------------------------------------------- PG-8
class TestTheWorkedCandidate(unittest.TestCase):
    """FCL-12b: the gap left open two commits earlier."""

    def test_it_survives(self):
        self.assertEqual(P.evaluate("lomb_scargle_gls")["verdict"], "SURVIVES")

    def test_it_recovers_a_known_period(self):
        import math
        import random
        rng = random.Random(3)
        t, ts = 0.0, []
        for _ in range(300):
            t += rng.expovariate(1.0)
            ts.append(t)
        ys = [math.sin(2 * math.pi * x / 7.5) + rng.gauss(0, 0.3) for x in ts]
        self.assertAlmostEqual(GLS.best_period(ts, ys)["period_s"], 7.5,
                               delta=0.05)

    def test_power_is_bounded_in_the_unit_interval(self):
        import random
        rng = random.Random(5)
        ts = [i * 0.7 for i in range(80)]
        ys = [rng.gauss(0, 1) for _ in range(80)]
        for p in GLS.gls_power(ts, ys, GLS.frequency_grid(ts)):
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 1.0)

    def test_a_constant_series_has_no_power(self):
        ts = [i * 1.0 for i in range(60)]
        self.assertEqual(max(GLS.gls_power(ts, [4.0] * 60,
                                           GLS.frequency_grid(ts))), 0.0)

    def test_it_refuses_a_degenerate_clock(self):
        with self.assertRaises(ValueError):
            GLS.frequency_grid([2.0] * 40)

    def test_it_refuses_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            GLS.gls_power([1.0, 2.0, 3.0, 4.0], [1.0], [0.1])

    def test_it_refuses_too_few_samples(self):
        with self.assertRaises(ValueError):
            GLS.gls_power([1.0, 2.0], [1.0, 2.0], [0.1])

    def test_the_floating_mean_survives_a_large_offset(self):
        """Plain Lomb-Scargle assumes a zero mean; the deviation series in
        field/ does not have one."""
        import math
        import random
        rng = random.Random(11)
        ts = [i * 0.5 for i in range(200)]
        base = [math.sin(2 * math.pi * x / 9.0) + rng.gauss(0, 0.2)
                for x in ts]
        a = GLS.best_period(ts, base)["period_s"]
        b = GLS.best_period(ts, [y + 1000.0 for y in base])["period_s"]
        self.assertAlmostEqual(a, b, places=9)


class TestVerdictLedger(unittest.TestCase):

    def test_a_verdict_is_appended_as_one_json_line(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "V.jsonl")
        P.record(P.evaluate_module(candidate()), path)
        P.record(P.evaluate_module(candidate(solve=lambda: -1.0)), path)
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(ln) for ln in fh if ln.strip()]
        self.assertEqual([r["verdict"] for r in rows], ["SURVIVES", "FAILED"])

    def test_the_contract_template_is_a_valid_candidate_skeleton(self):
        ns = {}
        exec(compile(P.CONTRACT_TEMPLATE, "<template>", "exec"), ns)
        for attr in ("PROBLEM", "CLAIM", "KIND", "AUTHOR", "NEEDS_NULL",
                     "solve", "checks", "broken", "null"):
            self.assertIn(attr, ns)


if __name__ == "__main__":
    unittest.main()
