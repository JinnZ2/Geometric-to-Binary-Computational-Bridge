"""Value-level tests for AISS scoring -- what tests/test_aiss.py does not cover.

``tests/test_aiss.py`` exists and passes, but 26 of its 46 assertions are
``assertIsInstance`` / ``assertIn`` shape checks. It verifies that
``evaluate_pattern`` returns a dict containing a float; it does not check what
the float is. The demonstration: removing 40% of ``_check_internal_coherence``
and renormalising ``total_score`` left all 27 of those tests passing.

That is the ``repo_guard`` checklist item -- *does the assertion have any input
that would make it FAIL?* -- answered for a suite that exists. A shape assertion
fails only when a function is renamed or crashes.

Two of ``repo_guard``'s three mechanical stages do not apply to this folder:
the symmetry veto has no surface (AISS is a governance framework, not a physics
one) and the reach check has no instrument claims. The third, the null harness,
applies squarely and fires -- ``TestMeritWeightsAreFlat``.
"""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AISS.assessment_framework import (  # noqa: E402
    cognitive_diversity_metric,
    structural_health,
    trust_effectiveness_score,
    trust_score,
)
from AISS.sovereignty_evaluator import (  # noqa: E402
    EvaluationDomain,
    EvaluatorConfig,
    Pattern,
    PatternSovereigntyEvaluator,
)

CRITERIA = ("internal_coherence", "empirical_testability",
            "mathematical_validity", "experiential_resonance",
            "predictive_power")


def _pattern(math_struct=None, geom=None, preds=None):
    return Pattern(content="x", domain=EvaluationDomain.MATHEMATICAL,
                   testable_predictions=preds or [],
                   mathematical_structure=math_struct,
                   geometric_representation=geom)


class TestInternalCoherencePlaceholderRemoved(unittest.TestCase):
    """``score += 0.4  # placeholder for logical consistency`` was 40% of it."""

    def setUp(self):
        self.ev = PatternSovereigntyEvaluator()

    def test_an_empty_pattern_now_scores_zero(self):
        """It scored 0.4 with nothing measured at all."""
        self.assertEqual(self.ev._check_internal_coherence(_pattern()), 0.0)

    def test_a_fully_specified_pattern_scores_one(self):
        p = _pattern(math_struct={"dimensions": 3}, geom={"kind": "octahedral"})
        self.assertEqual(self.ev._check_internal_coherence(p), 1.0)

    def test_each_inspected_component_contributes_half(self):
        self.assertEqual(
            self.ev._check_internal_coherence(_pattern(math_struct={"a": 1})), 0.5)
        self.assertEqual(
            self.ev._check_internal_coherence(_pattern(geom={"b": 2})), 0.5)

    def test_the_score_now_spans_the_full_range(self):
        """The old floor of 0.4 made 40% of the range unreachable, so no two
        patterns could differ by more than 0.6."""
        seen = {self.ev._check_internal_coherence(p) for p in
                (_pattern(), _pattern(math_struct={"a": 1}),
                 _pattern(math_struct={"a": 1}, geom={"b": 2}))}
        self.assertEqual(min(seen), 0.0)
        self.assertEqual(max(seen), 1.0)

    def test_unmeasured_components_are_named_rather_than_given_a_value(self):
        self.assertIn("logical_consistency",
                      PatternSovereigntyEvaluator.unmeasured_components)


class TestMeritWeightsAreFlat(unittest.TestCase):
    """The null-harness stage, applied to this scorer."""

    def setUp(self):
        self.ev = PatternSovereigntyEvaluator()

    def test_the_shipped_weights_are_all_equal(self):
        """Five criteria at 0.20 is an unweighted MEAN, not a weighting."""
        self.assertTrue(self.ev.weights_are_flat())
        self.assertEqual(set(self.ev.config.merit_weights.values()), {0.20})

    def test_flatness_is_reported_with_every_score(self):
        r = self.ev.evaluate_pattern(_pattern(math_struct={"dimensions": 3}))
        self.assertTrue(r["pattern_merit"]["weights_are_flat"])

    def test_unequal_weights_are_detected(self):
        cfg = EvaluatorConfig()
        cfg.merit_weights = dict(cfg.merit_weights)
        cfg.merit_weights["predictive_power"] = 0.6
        self.assertFalse(PatternSovereigntyEvaluator(cfg).weights_are_flat())

    def test_reweighting_does_not_change_the_verdict(self):
        """Most random reweightings reproduce the flat-weight high-merit rate."""
        rng = random.Random(0)
        patterns = [{c: rng.random() for c in CRITERIA} for _ in range(40)]
        r = self.ev.verdict_is_weight_sensitive(patterns, trials=300, seed=0)
        self.assertGreater(r["fraction_agreeing"], 0.5)
        self.assertFalse(r["weights_carry_information"])
        self.assertIn("ARTIFACT", r["verdict"])

    def test_a_sharply_peaked_weighting_does_carry_information(self):
        """So the check is not vacuous -- it can come back the other way."""
        cfg = EvaluatorConfig()
        cfg.merit_weights = {c: (0.96 if c == "predictive_power" else 0.01)
                             for c in CRITERIA}
        rng = random.Random(1)
        patterns = [{c: rng.random() for c in CRITERIA} for _ in range(60)]
        r = PatternSovereigntyEvaluator(cfg).verdict_is_weight_sensitive(
            patterns, trials=300, seed=1)
        self.assertTrue(r["weights_carry_information"])

    def test_rejects_an_empty_pattern_set(self):
        with self.assertRaises(ValueError):
            self.ev.verdict_is_weight_sensitive([])


class TestTotalScoreNormalisation(unittest.TestCase):
    """A latent bug the flat defaults were hiding."""

    def test_rescaling_every_weight_leaves_the_total_unchanged(self):
        """The defaults sum to 1.0. Any other choice used to rescale
        total_score silently, breaking every threshold in the config."""
        p = _pattern(math_struct={"dimensions": 3, "conserved_quantities": 1},
                     geom={"k": 1}, preds=["a", "b"])
        base = PatternSovereigntyEvaluator().evaluate_pattern(p)
        cfg = EvaluatorConfig()
        cfg.merit_weights = {c: 1.0 for c in CRITERIA}          # sums to 5.0
        scaled = PatternSovereigntyEvaluator(cfg).evaluate_pattern(p)
        self.assertAlmostEqual(base["pattern_merit"]["total_score"],
                               scaled["pattern_merit"]["total_score"],
                               places=12)

    def test_total_score_stays_within_zero_and_one(self):
        rng = random.Random(3)
        for _ in range(40):
            p = _pattern(
                math_struct={"dimensions": 1} if rng.random() > 0.5 else None,
                geom={"k": 1} if rng.random() > 0.5 else None,
                preds=["p"] * rng.randrange(0, 4))
            t = PatternSovereigntyEvaluator().evaluate_pattern(
                p)["pattern_merit"]["total_score"]
            self.assertGreaterEqual(t, 0.0)
            self.assertLessEqual(t, 1.0)

    def test_a_zero_weight_sum_is_refused_rather_than_dividing(self):
        cfg = EvaluatorConfig()
        cfg.merit_weights = {c: 0.0 for c in CRITERIA}
        with self.assertRaises(ValueError):
            PatternSovereigntyEvaluator(cfg).evaluate_pattern(_pattern())

    def test_an_empty_pattern_scores_below_a_specified_one(self):
        """The ordering the scorer exists to produce, checked on values."""
        ev = PatternSovereigntyEvaluator()
        bare = ev.evaluate_pattern(_pattern())["pattern_merit"]["total_score"]
        full = ev.evaluate_pattern(
            _pattern(math_struct={"dimensions": 3, "conserved_quantities": 1,
                                  "geometric_invariants": 1, "topology": 1},
                     geom={"k": 1},
                     preds=["a", "b", "c"]))["pattern_merit"]["total_score"]
        self.assertLess(bare, full)


class TestTrustScore(unittest.TestCase):
    """This one is well designed, and the tests record why."""

    def test_it_is_a_product_so_either_factor_at_zero_kills_it(self):
        self.assertEqual(trust_score(0.0, 1.0), 0.0)
        self.assertEqual(trust_score(1.0, 0.0), 0.0)

    def test_perfect_dependability_cannot_buy_back_zero_transparency(self):
        """A sum would have let it. The docstring says so and the code agrees."""
        self.assertEqual(trust_score(1.0, 0.0), 0.0)
        self.assertNotEqual(trust_score(1.0, 0.0), (1.0 + 0.0) / 2)

    def test_it_is_monotone_in_both_arguments(self):
        self.assertLess(trust_score(0.5, 0.5), trust_score(0.6, 0.5))
        self.assertLess(trust_score(0.5, 0.5), trust_score(0.5, 0.6))

    def test_effectiveness_matches_the_ratio_definition(self):
        self.assertAlmostEqual(trust_effectiveness_score(8, 10, 9, 10),
                               0.8 * 0.9, places=12)

    def test_zero_attempts_returns_zero_rather_than_dividing(self):
        self.assertEqual(trust_effectiveness_score(0, 0, 1, 1), 0.0)
        self.assertEqual(trust_effectiveness_score(1, 1, 0, 0), 0.0)


class TestOtherMetrics(unittest.TestCase):

    def test_structural_health_is_the_mean_of_four(self):
        self.assertAlmostEqual(structural_health(1.0, 1.0, 1.0, 1.0), 1.0)
        self.assertAlmostEqual(structural_health(1.0, 0.0, 1.0, 0.0), 0.5)

    def test_cognitive_diversity_is_one_minus_a_ratio(self):
        self.assertAlmostEqual(cognitive_diversity_metric(0.4, 1.0), 0.6)

    def test_cognitive_diversity_guards_a_zero_denominator(self):
        self.assertEqual(cognitive_diversity_metric(0.5, 0.0), 0.0)

    def test_cognitive_diversity_is_unbounded_below(self):
        """Worth recording: the docstring gives a target of >0.6 but no floor,
        and linearity above complexity drives it negative."""
        self.assertLess(cognitive_diversity_metric(2.0, 1.0), 0.0)


class TestWhichGuardStagesApply(unittest.TestCase):
    """Recording the scoping judgement so it is not re-litigated."""

    def test_the_symmetry_veto_has_no_surface_here(self):
        from repo_guard import veto
        path = os.path.join(os.path.dirname(__file__), "..", "AISS",
                            "sovereignty_evaluator.py")
        with open(path) as fh:
            self.assertEqual(veto("silicon", fh.read()), [])

    def test_the_null_harness_does_apply_and_returns_artifact(self):
        from repo_guard import null_harness
        rng = random.Random(0)
        patterns = [{c: rng.random() for c in CRITERIA} for _ in range(40)]
        keys = list(CRITERIA)

        def rate(weights):
            wsum = sum(weights[k] for k in keys)
            return sum(
                (sum(weights[k] * s[k] for k in keys) / wsum) >= 0.70
                for s in patterns) / len(patterns)

        flat = {c: 0.2 for c in CRITERIA}
        base = rate(flat)

        def random_weights():
            return {c: rng.random() for c in CRITERIA}
        random_weights.__name__ = "random weights"

        r = null_harness(rate, flat, [random_weights],
                         lambda v: abs(v - base) <= 0.05,
                         name="AISS merit verdict", trials=200)
        self.assertEqual(r["verdict"], "ARTIFACT")


if __name__ == "__main__":
    unittest.main()
