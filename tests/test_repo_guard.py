"""Tests for repo_guard.py -- the null stage.

Stdlib only. The point of a guard is that it can fire and can stay silent, so
every check here is tested in both directions. A guard that always passes is the
defect it exists to catch.
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repo_guard import (  # noqa: E402
    CHECKLIST,
    FLOOR,
    VETO,
    null_harness,
    reach,
    veto,
)


class TestNullHarness(unittest.TestCase):

    def test_a_discriminating_criterion_survives(self):
        r = null_harness(metric=lambda x: x, real=100.0,
                         nulls=[lambda: random.Random().uniform(0, 1)],
                         passes=lambda v: v > 50.0, trials=50)
        self.assertEqual(r["verdict"], "SURVIVES")
        self.assertTrue(r["real_passes"])
        self.assertEqual(r["worst_null_pass_rate"], 0.0)

    def test_a_criterion_random_noise_meets_is_an_artifact(self):
        rng = random.Random(0)
        r = null_harness(metric=lambda x: x, real=0.9,
                         nulls=[lambda: rng.uniform(0.0, 1.0)],
                         passes=lambda v: v > 0.1, trials=200)
        self.assertEqual(r["verdict"], "ARTIFACT")
        self.assertGreater(r["worst_null_pass_rate"], 0.5)

    def test_an_intermediate_rate_is_suspect(self):
        rng = random.Random(1)
        r = null_harness(metric=lambda x: x, real=0.99,
                         nulls=[lambda: rng.uniform(0.0, 1.0)],
                         passes=lambda v: v > 0.75, trials=400)
        self.assertEqual(r["verdict"], "SUSPECT")

    def test_a_claim_that_fails_its_own_criterion_is_not_survival(self):
        """The correction: a false claim used to be reported as SURVIVES."""
        r = null_harness(metric=lambda x: x, real=0.1,
                         nulls=[lambda: 0.0],
                         passes=lambda v: v > 0.5, trials=10)
        self.assertEqual(r["verdict"], "CLAIM_FAILS")
        self.assertFalse(r["real_passes"])
        self.assertEqual(r["worst_null_pass_rate"], 0.0)

    def test_a_tautological_criterion_is_caught(self):
        """'at least one mode survives' -- true for every input by construction."""
        r = null_harness(metric=lambda x: 0.0, real=None,
                         nulls=[lambda: None],
                         passes=lambda v: abs(v) < 0.15, trials=20)
        self.assertEqual(r["verdict"], "ARTIFACT")
        self.assertEqual(r["worst_null_pass_rate"], 1.0)

    def test_multiple_nulls_report_the_worst(self):
        rng = random.Random(2)
        r = null_harness(metric=lambda x: x, real=5.0,
                         nulls=[lambda: 0.0, lambda: rng.uniform(0.0, 10.0)],
                         passes=lambda v: v > 1.0, trials=100)
        self.assertEqual(len(r["nulls"]), 2)
        self.assertAlmostEqual(r["worst_null_pass_rate"],
                               max(n["frac_passing"] for n in r["nulls"]))

    def test_null_names_are_reported(self):
        def shuffled():
            return 0.0
        r = null_harness(lambda x: x, 1.0, [shuffled], lambda v: v > 0.5,
                         trials=5)
        self.assertEqual(r["nulls"][0]["null"], "shuffled")

    def test_rejects_no_nulls_or_no_trials(self):
        with self.assertRaises(ValueError):
            null_harness(lambda x: x, 1.0, [], lambda v: True)
        with self.assertRaises(ValueError):
            null_harness(lambda x: x, 1.0, [lambda: 0.0], lambda v: True,
                         trials=0)


class TestSymmetryVeto(unittest.TestCase):

    def test_it_fires_on_a_forbidden_mechanism(self):
        hits = veto("silicon", "we drive it with an inverse piezo actuator")
        self.assertEqual([h[0] for h in hits], ["inverse piezo"])

    def test_it_fires_on_every_magnetic_mechanism_this_archive_found(self):
        text = ("magnetostriction, faraday rotation, esr readout, "
                "exchange coupling, and spin coherence")
        found = {h[0] for h in veto("silicon", text)}
        for k in ("magnetostriction", "faraday", "esr", "exchange",
                  "spin coherence"):
            self.assertIn(k, found)

    def test_it_stays_silent_on_an_allowed_mechanism(self):
        self.assertEqual(veto("silicon", "we use electrostriction and "
                                         "piezoresistive readout"), [])

    def test_every_veto_names_a_replacement_or_says_there_is_none(self):
        for k, v in VETO["silicon"].items():
            if k.startswith("_"):
                continue
            self.assertEqual(len(v), 2, msg=k)
            self.assertTrue(v[0].strip(), msg=k)
            self.assertTrue(v[1].strip(), msg=k)

    def test_the_cubic_isotropy_entries_are_present(self):
        """EPG-7 and the kappa_[111] claim both live here."""
        found = {h[0] for h in veto("silicon", "thermal anisotropy and "
                                               "conductivity anisotropy")}
        self.assertEqual(found, {"thermal anisotropy", "conductivity anisotropy"})

    def test_an_unknown_material_is_flagged_not_silently_passed(self):
        hits = veto("unobtainium", "magnetostriction everywhere")
        self.assertEqual(len(hits), 1)
        self.assertIn("no veto table", hits[0][1])

    def test_matching_is_case_insensitive(self):
        self.assertTrue(veto("SILICON", "INVERSE PIEZO"))


class TestReachCheck(unittest.TestCase):

    def test_the_hall_gap_this_archive_derived(self):
        d = reach(7.96e-17, "hall sensor")
        self.assertEqual(d["verdict"], "BELOW FLOOR")
        self.assertAlmostEqual(-math.log10(d["ratio"]), 11.4, delta=0.1)

    def test_the_squid_gap(self):
        d = reach(3.98e-19, "squid moment")
        self.assertEqual(d["verdict"], "BELOW FLOOR")
        self.assertAlmostEqual(-math.log10(d["ratio"]), 7.4, delta=0.1)

    def test_the_rbs_shortfall(self):
        d = reach(5e11, "rbs areal")
        self.assertEqual(d["verdict"], "BELOW FLOOR")
        self.assertAlmostEqual(d["ratio"], 0.05, places=6)

    def test_the_piezoresistive_signal_clears_by_orders(self):
        d = reach(0.121, "piezoresistive")
        self.assertEqual(d["verdict"], "DETECTABLE")
        self.assertGreater(d["ratio"], 1e4)

    def test_the_three_verdict_bands(self):
        f = FLOOR["hall sensor"][0]
        self.assertEqual(reach(f * 10, "hall sensor")["verdict"], "DETECTABLE")
        self.assertEqual(reach(f * 1.5, "hall sensor")["verdict"], "MARGINAL")
        self.assertEqual(reach(f * 0.5, "hall sensor")["verdict"], "BELOW FLOOR")

    def test_exactly_at_the_floor_is_marginal_not_detectable(self):
        f = FLOOR["squid moment"][0]
        self.assertEqual(reach(f, "squid moment")["verdict"], "MARGINAL")

    def test_landauer_floor_matches_kt_ln2(self):
        kb = 1.380649e-23
        self.assertAlmostEqual(FLOOR["landauer 300K"][0], kb * 300 * math.log(2),
                               delta=2e-24)

    def test_kt_floor_matches_the_electronvolt_value(self):
        kb, qe = 1.380649e-23, 1.602176634e-19
        self.assertAlmostEqual(FLOOR["kT 300K"][0], kb * 300 / qe, places=5)

    def test_an_energy_below_landauer_is_caught(self):
        """0.01 eV, the value this archive found below the bound."""
        d = reach(0.01 * 1.602176634e-19, "landauer 300K")
        self.assertEqual(d["verdict"], "BELOW FLOOR")

    def test_the_gauge_factor_note_uses_the_matching_modulus(self):
        """pi_l is the <110> coefficient, so it pairs with E<110> = 169 GPa."""
        self.assertIn("121", FLOOR["piezoresistive"][2])
        self.assertAlmostEqual(71.8e-11 * 169e9, 121.3, delta=0.5)

    def test_unknown_instrument_names_the_available_floors(self):
        with self.assertRaises(KeyError) as ctx:
            reach(1.0, "tricorder")
        self.assertIn("known floors", str(ctx.exception))

    def test_rejects_a_negative_signal(self):
        with self.assertRaises(ValueError):
            reach(-1.0, "hall sensor")

    def test_every_floor_entry_is_well_formed(self):
        for name, entry in FLOOR.items():
            self.assertEqual(len(entry), 3, msg=name)
            value, unit, note = entry
            self.assertGreater(value, 0.0, msg=name)
            self.assertTrue(unit.strip(), msg=name)
            self.assertTrue(note.strip(), msg=name)


class TestChecklist(unittest.TestCase):

    def test_it_covers_the_two_unmechanisable_classes(self):
        self.assertIn("CIRCULAR TARGET", CHECKLIST)
        self.assertIn("UNITS AND ORDERS", CHECKLIST)

    def test_it_carries_the_landauer_number(self):
        self.assertIn("0.0179", CHECKLIST)

    def test_it_carries_the_direction_matching_rule(self):
        """The correction that came out of the gauge-factor slip."""
        self.assertIn("169 GPa", CHECKLIST)

    def test_it_asks_whether_an_assertion_can_fail(self):
        self.assertIn("would make it FAIL", CHECKLIST)


if __name__ == "__main__":
    unittest.main()
