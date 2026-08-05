"""FCL-1..10: the field claim loop's router, and the gates it routes on.

Stdlib only. Every gate is tested in BOTH directions -- it must fire where
the effect is real and stay silent where it is not. A gate that only ever
passes is the defect it exists to catch, and two of the shipped ones were
exactly that: 22% false-alarm with 0% power on the same statistic.

The false-positive rates asserted here are the null harness from
``repo_guard.py`` applied to a router: replace the structure with noise and
check that the verdict goes away.
"""

import math
import os
import random
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from field import field_claim_loop as F  # noqa: E402


class Store(unittest.TestCase):
    """Each test gets its own jsonl store; the module writes to cwd."""

    def setUp(self):
        self._old = os.getcwd()
        self._dir = tempfile.mkdtemp()
        os.chdir(self._dir)

    def tearDown(self):
        os.chdir(self._old)
        shutil.rmtree(self._dir, ignore_errors=True)

    def band_breaking(self, n=40, p=0.34, anchor_dev=0.0, cov=None, seed=0,
                      clock=False):
        """n readings, a random ~p of them outside the band.

        Breaks are drawn independently, NOT every k-th reading. A fixed stride
        is a periodic rider, and since FCL-11 uncensored the series the
        correlation branch sees it -- correctly. That is its own test below,
        not something a NOVEL fixture should smuggle in.
        """
        rng = random.Random(seed)
        F.claim("piezo baseline", "piezo_trunk_n", 0.0, 1.0)
        for i in range(n):
            v = (2.0 + rng.random() if rng.random() < p
                 else rng.gauss(0.5, 0.08))
            F.reading("piezo_trunk_n", v, anchor_dev=anchor_dev,
                      covariates=cov, ts="t%03d" % i,
                      t_s=float(i) if clock else None)


# ---------------------------------------------------------------- FCL-1
class TestNovelIsReachable(Store):
    """A stable anchor used to switch off the branch that finds new ground."""

    def test_novel_fires_when_the_rig_is_clean(self):
        self.band_breaking(anchor_dev=0.0)
        r = F.route("c001")
        self.assertGreater(r["n_residuals"], 0)
        self.assertEqual([c["route"] for c in r["candidates"]], ["NOVEL"])

    def test_a_stable_anchor_contributes_no_candidate(self):
        """It used to append INSTRUMENT at weight 0.0, which is not evidence."""
        self.band_breaking(anchor_dev=0.0)
        r = F.route("c001")
        self.assertNotIn("INSTRUMENT", [c["route"] for c in r["candidates"]])

    def test_the_stable_anchor_is_recorded_as_negative_evidence(self):
        self.band_breaking(anchor_dev=0.0)
        r = F.route("c001")
        self.assertTrue(any("within tol" in n for n in r["negative_evidence"]))

    def test_novel_carries_the_negative_evidence_it_rests_on(self):
        self.band_breaking(anchor_dev=0.0)
        ev = F.route("c001")["candidates"][0]["evidence"]
        for phrase in ("within tol", "white", "no covariate bin"):
            self.assertIn(phrase, ev)

    def test_the_query_for_a_clean_break_is_spawn_not_cross_check(self):
        """The wrong route emits the wrong experiment. That was the cost."""
        self.band_breaking(anchor_dev=0.0)
        q = F.next_query("c001")
        self.assertEqual(q["route"], "NOVEL")
        self.assertIn("spawn child claim", q["action"])

    def test_novel_does_not_fire_when_there_are_no_residuals(self):
        F.claim("piezo baseline", "piezo_trunk_n", 0.0, 1.0)
        for i in range(30):
            F.reading("piezo_trunk_n", 0.5, anchor_dev=0.0, ts="t%03d" % i)
        r = F.route("c001")
        self.assertEqual(r["n_residuals"], 0)
        self.assertEqual(r["candidates"], [])


# ---------------------------------------------------------------- FCL-2
class TestAnchorIsADeviation(Store):

    def test_a_moving_anchor_does_route_to_instrument(self):
        self.band_breaking(anchor_dev=0.4)
        r = F.route("c001")
        self.assertEqual(r["candidates"][0]["route"], "INSTRUMENT")
        self.assertEqual(r["candidates"][0]["weight"], 1.0)

    def test_the_tolerance_is_honoured(self):
        self.band_breaking(anchor_dev=0.4)
        r = F.route("c001", anchor_tol=1.0)
        self.assertNotIn("INSTRUMENT", [c["route"] for c in r["candidates"]])

    def test_an_absent_anchor_is_unmeasured_not_ruled_out(self):
        """The distinction the skeleton could not draw."""
        self.band_breaking(anchor_dev=None)
        r = F.route("c001")
        self.assertTrue(any("only unmeasured" in n
                            for n in r["negative_evidence"]))

    def test_anchor_raw_is_stored_but_never_routed_on(self):
        self.band_breaking(anchor_dev=0.0)
        F.reading("piezo_trunk_n", 9.0, anchor_dev=0.0, anchor_raw=1004.0,
                  ts="tzz")
        r = F.route("c001")
        self.assertNotIn("INSTRUMENT", [c["route"] for c in r["candidates"]])


# ---------------------------------------------------------------- FCL-3
class TestAutocorrGateHasASampleFloor(unittest.TestCase):

    def test_a_short_series_is_insufficient_not_white(self):
        s = F.autocorr_scan([1.0, -1.0] * 5)
        self.assertEqual(s["status"], "INSUFFICIENT")
        self.assertEqual(s["n"], 10)

    def test_the_false_alarm_rate_on_white_noise_is_near_alpha(self):
        """Shipped gate: 23.5% at n=5, 21.9% at n=8, 8.3% at n=20."""
        for n in (20, 40, 100):
            rng = random.Random(11)
            fires = sum(
                1 for _ in range(1000)
                if F.autocorr_scan([rng.gauss(0, 1) for _ in range(n)]
                                   )["status"] == "STRUCTURED")
            self.assertLess(fires / 1000.0, 0.08, msg="n=%d" % n)

    def test_the_old_fixed_threshold_would_have_failed_that(self):
        """Recording the number the fix is against, so it cannot drift back."""
        rng = random.Random(11)
        fires = sum(1 for _ in range(1000)
                    if abs(F._autocorr([rng.gauss(0, 1) for _ in range(8)], 3))
                    > 0.35)
        self.assertGreater(fires / 1000.0, 0.15)


# ---------------------------------------------------------------- FCL-4
class TestAFixedLagIsBlind(unittest.TestCase):
    """rho(lag) = cos(2*pi*lag/T). At lag 3 that is zero at T=12."""

    def _rider(self, period, n=100, seed=5, noise=0.5):
        rng = random.Random(seed)
        ph = rng.random() * 6.283
        return [math.sin(2 * math.pi * i / period + ph) + rng.gauss(0, noise)
                for i in range(n)]

    def test_lag_three_is_blind_at_period_twelve(self):
        self.assertAlmostEqual(math.cos(2 * math.pi * 3 / 12), 0.0, places=12)
        detected = sum(1 for s in range(200)
                       if abs(F._autocorr(self._rider(12, seed=s), 3)) > 0.35)
        self.assertLess(detected, 10)

    def test_the_scan_catches_every_period_the_fixed_lag_missed(self):
        for T in (4, 10, 12, 14, 16):
            hits = sum(1 for s in range(60)
                       if F.autocorr_scan(self._rider(T, seed=s)
                                          )["status"] == "STRUCTURED")
            self.assertGreater(hits, 55, msg="period %d" % T)

    def test_the_scan_still_catches_the_periods_it_already_had(self):
        for T in (6, 8, 24):
            hits = sum(1 for s in range(60)
                       if F.autocorr_scan(self._rider(T, seed=s)
                                          )["status"] == "STRUCTURED")
            self.assertGreater(hits, 55, msg="period %d" % T)

    def test_the_reported_lag_tracks_the_rider_period(self):
        s = F.autocorr_scan(self._rider(12, n=200, noise=0.1))
        self.assertEqual(s["status"], "STRUCTURED")
        self.assertIn(s["lag"], (6, 12))          # antiphase or in phase

    def test_the_band_widens_as_the_series_shortens(self):
        wide = F.autocorr_scan([0.0] * 25)["threshold"]
        tight = F.autocorr_scan([0.0] * 400)["threshold"]
        self.assertGreater(wide, tight)


# ---------------------------------------------------------------- FCL-5
class TestCovariateGateIsCalibrated(unittest.TestCase):

    def _null(self, n_read, n_lev, p, trials=400, seed=7):
        rng = random.Random(seed)
        fires = 0
        for _ in range(trials):
            rs = [{"covariates": {"phase": rng.randrange(n_lev)}}
                  for _ in range(n_read)]
            hit = {i for i in range(n_read) if rng.random() < p}
            if F.covariate_concentration(hit, rs):
                fires += 1
        return fires / float(trials)

    def test_null_false_positive_rate_is_at_or_below_alpha(self):
        """Shipped gate on the same nulls: 34.7%, 34.0%, 41.0%."""
        for n_read, n_lev, p in ((40, 4, 0.3), (200, 8, 0.3), (200, 4, 0.1)):
            self.assertLessEqual(self._null(n_read, n_lev, p), 0.05,
                                 msg="n=%d lev=%d p=%.2f" % (n_read, n_lev, p))

    def test_the_old_rule_would_have_failed_that(self):
        rng = random.Random(7)
        fires = 0
        for _ in range(400):
            rs = [{"covariates": {"phase": rng.randrange(4)}}
                  for _ in range(200)]
            hit = {i for i in range(200) if rng.random() < 0.1}
            base = len(hit) / 200.0
            bins = {}
            for i, r in enumerate(rs):
                k = r["covariates"]["phase"]
                t, h = bins.get(k, (0, 0))
                bins[k] = (t + 1, h + (1 if i in hit else 0))
            if any(t >= 8 and h / float(t) > base * 1.5
                   for t, h in bins.values()):
                fires += 1
        self.assertGreater(fires / 400.0, 0.20)

    def test_a_real_concentration_is_still_found(self):
        rng = random.Random(9)
        rs, hit = [], set()
        for i in range(200):
            rain = 1 if i % 4 == 0 else 0
            rs.append({"covariates": {"rain": rain}})
            if rng.random() < (0.9 if rain else 0.05):
                hit.add(i)
        out = F.covariate_concentration(hit, rs)
        self.assertTrue(out)
        self.assertEqual(out[0]["covariate"], "rain")
        self.assertEqual(out[0]["value"], "1")

    def test_bins_below_min_samples_are_not_tested(self):
        rs = [{"covariates": {"phase": "rare" if i < 3 else "common"}}
              for i in range(60)]
        out = F.covariate_concentration(set(range(3)), rs)
        self.assertEqual([d["value"] for d in out], [])

    def test_the_correction_scales_with_the_number_of_bins(self):
        rs2 = [{"covariates": {"a": i % 2}} for i in range(80)]
        rs8 = [{"covariates": {"a": i % 2, "b": i % 4, "c": i % 8}}
               for i in range(80)]
        hit = set(range(0, 80, 3))
        a = F.covariate_concentration(hit, rs2, alpha=0.5)
        b = F.covariate_concentration(hit, rs8, alpha=0.5)
        self.assertGreater(a[0]["alpha_adj"] if a else 1.0,
                           b[0]["alpha_adj"] if b else 0.0)


# ---------------------------------------------------------------- FCL-6
class TestMembershipIsByIndex(unittest.TestCase):

    def test_duplicate_readings_do_not_all_count_as_residuals(self):
        """20 identical-content readings, ONE residual. Old code: rate 1.00."""
        rs = ([{"covariates": {"phase": "dusk"}, "value": 1.0}] * 10
              + [{"covariates": {"phase": "dawn"}, "value": 9.0}] * 10)
        self.assertEqual(F.covariate_concentration({0}, rs), [])

    def test_identical_dicts_would_have_compared_equal(self):
        a = {"covariates": {"phase": "dusk"}, "value": 1.0}
        b = {"covariates": {"phase": "dusk"}, "value": 1.0}
        self.assertEqual(a, b)
        self.assertIsNot(a, b)


# ---------------------------------------------------------------- FCL-7
class TestDeepenMustTighten(Store):

    def setUp(self):
        Store.setUp(self)
        F.claim("piezo baseline", "piezo_trunk_n", 0.0, 1.0)

    def test_a_tighter_band_is_accepted_and_increments_depth(self):
        child = F.deepen("c001", 0.2, 0.8)
        self.assertEqual(child["depth"], 1)
        self.assertEqual(child["parent"], "c001")

    def test_a_wider_band_is_refused(self):
        with self.assertRaises(ValueError):
            F.deepen("c001", -1e9, 1e9)

    def test_an_equal_band_is_refused(self):
        with self.assertRaises(ValueError):
            F.deepen("c001", 0.0, 1.0)

    def test_a_shifted_band_of_equal_width_is_refused(self):
        with self.assertRaises(ValueError):
            F.deepen("c001", 0.5, 1.5)

    def test_a_wider_band_is_allowed_only_with_a_named_axis(self):
        child = F.deepen("c001", -1.0, 2.0, added_axis="temp_c")
        self.assertEqual(child["added_axis"], "temp_c")

    def test_an_inverted_band_is_refused(self):
        with self.assertRaises(ValueError):
            F.deepen("c001", 0.9, 0.1)
        with self.assertRaises(ValueError):
            F.claim("bad", "ch", 1.0, 0.0)


# ---------------------------------------------------------------- FCL-8
class TestSpendLedger(Store):

    def setUp(self):
        Store.setUp(self)
        self.band_breaking(anchor_dev=0.0)

    def test_a_query_charges_the_ledger(self):
        self.assertEqual(F.spent(), 0.0)
        F.next_query("c001")
        self.assertEqual(F.spent(), F.QUERY_COST["NOVEL"])

    def test_an_identical_pending_query_is_refused_not_reissued(self):
        F.next_query("c001")
        again = F.next_query("c001")
        self.assertEqual(again["refused"], "duplicate")
        self.assertEqual(F.spent(), F.QUERY_COST["NOVEL"])

    def test_the_budget_is_a_hard_cap(self):
        r = F.next_query("c001", budget=0.5)
        self.assertEqual(r["refused"], "budget")
        self.assertEqual(F.spent(), 0.0)

    def test_yield_is_unknown_until_a_query_is_resolved(self):
        F.next_query("c001")
        self.assertIsNone(F.yield_rate()["rate"])

    def test_resolving_records_whether_the_spend_bought_anything(self):
        q = F.next_query("c001")
        F.resolve_query(q["id"], moved=True)
        y = F.yield_rate()
        self.assertEqual((y["resolved"], y["moved"], y["rate"]), (1, 1, 1.0))

    def test_a_query_that_moved_nothing_is_counted_as_heat(self):
        q = F.next_query("c001")
        F.resolve_query(q["id"], moved=False)
        self.assertEqual(F.yield_rate()["rate"], 0.0)

    def test_a_query_cannot_be_resolved_twice(self):
        q = F.next_query("c001")
        F.resolve_query(q["id"], moved=True)
        with self.assertRaises(ValueError):
            F.resolve_query(q["id"], moved=False)

    def test_resolving_frees_the_route_to_be_asked_again(self):
        q = F.next_query("c001")
        F.resolve_query(q["id"], moved=False)
        self.assertNotIn("refused", F.next_query("c001"))

    def test_an_unknown_query_id_raises(self):
        with self.assertRaises(KeyError):
            F.resolve_query("q999", moved=True)

    def test_every_route_has_a_cost(self):
        self.assertEqual(set(F.QUERY_COST), set(F.ROUTES))


# ---------------------------------------------------------------- FCL-9
class TestScalarizationIsExplicit(Store):

    def test_a_shape_without_a_named_projection_is_refused(self):
        with self.assertRaises(ValueError):
            F.reading("chem_soil_a", 0.5, shape=[0.1, 0.2, 0.45])

    def test_a_named_projection_is_stored_with_the_reading(self):
        r = F.reading("chem_soil_a", 0.5, shape=[0.1, 0.2, 0.45],
                      projection="l2")
        self.assertEqual(r["projection"], "l2")

    def test_a_scalar_only_reading_needs_no_projection(self):
        self.assertIsNone(F.reading("lux_canopy", 812.0)["projection"])

    def test_test_compares_the_scalar_and_the_docstring_says_so(self):
        """FCL-9 is PARTIAL. Recording that, so it is not read as closed."""
        self.assertIn("value", F.test.__doc__)
        self.assertIn("FCL-9", F.test.__doc__)


# ---------------------------------------------------------------- FCL-10
class TestClaimIds(Store):

    def test_ids_stay_contiguous_across_claim_updates(self):
        F.claim("a", "ch", 0, 1)
        F.claim("b", "ch", 0, 1)
        F.refresh("c001")
        F.refresh("c002")
        F.refresh("c002")
        self.assertEqual(F.claim("c", "ch", 0, 1)["id"], "c003")

    def test_refresh_writes_the_support_count_that_was_always_zero(self):
        self.band_breaking(n=30, anchor_dev=0.0)
        c = F.refresh("c001")
        self.assertEqual(c["support"] + c["n_residuals"], 30)
        self.assertGreater(c["support"], 0)
        self.assertGreater(c["n_residuals"], 0)

    def test_the_latest_record_wins(self):
        F.claim("a", "ch", 0, 1)
        F.refresh("c001")
        self.assertEqual(len(F._claims()), 1)


# ---------------------------------------------------------------- 5b
class TestHoldoutBeforePromotion(unittest.TestCase):

    def _rider(self, period, n, seed):
        rng = random.Random(seed)
        ph = rng.random() * 6.283
        return [math.sin(2 * math.pi * i / period + ph) + rng.gauss(0, 0.4)
                for i in range(n)]

    def test_structure_in_both_windows_at_the_same_lag_promotes(self):
        r = F.promote_channel("tide", self._rider(8, 120, 1),
                              self._rider(8, 120, 2))
        self.assertTrue(r["promoted"])

    def test_structure_in_the_fit_window_alone_does_not(self):
        rng = random.Random(3)
        r = F.promote_channel("ghost", self._rider(8, 120, 1),
                              [rng.gauss(0, 1) for _ in range(120)])
        self.assertFalse(r["promoted"])

    def test_a_short_holdout_refuses_rather_than_promotes(self):
        r = F.promote_channel("tide", self._rider(8, 120, 1),
                              self._rider(8, 5, 2))
        self.assertFalse(r["promoted"])
        self.assertIn("below", r["reason"])

    def test_a_different_lag_in_the_holdout_does_not_promote(self):
        r = F.promote_channel("drift", self._rider(6, 200, 1),
                              self._rider(20, 200, 2))
        self.assertFalse(r["promoted"])


# ---------------------------------------------------------------- FCL-11
class TestSeriesIsUncensored(unittest.TestCase):
    """test() is censored on purpose; deviation() is what gets correlated."""

    def _drifting(self, n=120, period=10.0, amp=0.9, seed=4):
        """Sinusoid about the band centre, crossing the edge on the peaks."""
        rng = random.Random(seed)
        return [0.5 + amp * math.sin(2 * math.pi * i / period)
                + rng.gauss(0, 0.05) for i in range(n)]

    def _censor(self, vals, lo=0.0, hi=1.0):
        out = []
        for v in vals:
            if v < lo:
                out.append(v - lo)
            elif v > hi:
                out.append(v - hi)
        return out

    def test_censoring_discards_most_of_the_record(self):
        vals = self._drifting()
        self.assertLess(len(self._censor(vals)), len(vals))

    def test_censoring_recovers_the_wrong_lag(self):
        """It does not always blind you -- it biases you, which is worse."""
        vals = self._drifting()
        cens = F.autocorr_scan(self._censor(vals))
        unc = F.autocorr_scan([v - 0.5 for v in vals])
        self.assertEqual(cens["status"], "STRUCTURED")
        self.assertEqual(unc["status"], "STRUCTURED")
        self.assertEqual(unc["lag"], 5)          # true half-period
        self.assertNotEqual(cens["lag"], 5)

    def test_the_uncensored_series_correlates_more_strongly(self):
        vals = self._drifting()
        self.assertGreater(
            abs(F.autocorr_scan([v - 0.5 for v in vals])["rho"]),
            abs(F.autocorr_scan(self._censor(vals))["rho"]))


class TestDeviationVsTest(Store):

    def setUp(self):
        Store.setUp(self)
        F.claim("piezo baseline", "piezo_trunk_n", 0.0, 1.0)

    def test_test_is_zero_inside_the_band_and_deviation_is_not(self):
        r = F.reading("piezo_trunk_n", 0.9)
        self.assertEqual(F.test("c001", r), 0.0)
        self.assertAlmostEqual(F.deviation("c001", r), 0.4)

    def test_deviation_is_signed_about_the_centre(self):
        lo = F.reading("piezo_trunk_n", 0.1)
        hi = F.reading("piezo_trunk_n", 0.9)
        self.assertAlmostEqual(F.deviation("c001", lo),
                               -F.deviation("c001", hi))

    def test_they_agree_on_direction_outside_the_band(self):
        r = F.reading("piezo_trunk_n", 3.0)
        self.assertGreater(F.test("c001", r), 0.0)
        self.assertGreater(F.deviation("c001", r), 0.0)

    def test_the_router_uses_every_reading_not_just_the_breaks(self):
        rng = random.Random(4)
        for i in range(120):
            F.reading("piezo_trunk_n",
                      0.5 + 0.9 * math.sin(2 * math.pi * i / 10.0)
                      + rng.gauss(0, 0.05), ts="t%03d" % i)
        r = F.route("c001")
        self.assertIn("NOISE_AS_SIGNAL", [c["route"] for c in r["candidates"]])
        self.assertIn("n=120", r["candidates"][0]["evidence"])


# ---------------------------------------------------------------- FCL-12
class TestLagIsADuration(unittest.TestCase):

    def _poisson(self, n, seed, rate=1.0):
        rng = random.Random(seed)
        t, out = 0.0, []
        for _ in range(n):
            t += rng.expovariate(rate)
            out.append(t)
        return out

    def test_a_regular_clock_recovers_the_half_period_in_seconds(self):
        rng = random.Random(4)
        ts = [i * 2.5 for i in range(120)]
        xs = [0.9 * math.sin(2 * math.pi * i / 10.0) + rng.gauss(0, 0.05)
              for i in range(120)]
        s = F.slotted_scan(ts, xs, n_perm=200, seed=0)
        self.assertEqual(s["status"], "STRUCTURED")
        self.assertAlmostEqual(s["lag_s"], 12.5, places=6)   # T/2, T = 25 s
        self.assertLess(s["rho"], -0.9)

    def test_the_slot_width_tracks_the_sampling_interval(self):
        """Deriving it from the record SPAN made each slot half a period wide,
        which averaged a real rider down to rho=0.23 at an arbitrary lag."""
        ts = [i * 2.5 for i in range(120)]
        s = F.slotted_scan(ts, [0.0] * 119 + [1.0], n_perm=20, seed=0)
        self.assertAlmostEqual(s["slot_width"], 2.5, places=6)

    def test_null_rate_on_an_irregular_clock_is_near_alpha(self):
        fires = 0
        for s in range(150):
            ts = self._poisson(80, s)
            rng = random.Random(1000 + s)
            xs = [rng.gauss(0, 1) for _ in range(80)]
            fires += F.slotted_scan(ts, xs, n_perm=100,
                                    seed=s)["status"] == "STRUCTURED"
        self.assertLess(fires / 150.0, 0.10)

    def test_it_finds_a_rider_that_index_lag_cannot_even_express(self):
        for T in (3.0, 6.0, 12.0):
            hits = 0
            for s in range(20):
                ts = self._poisson(80, s)
                rng = random.Random(2000 + s)
                xs = [math.sin(2 * math.pi * t / T) + rng.gauss(0, 0.5)
                      for t in ts]
                hits += F.slotted_scan(ts, xs, n_perm=100,
                                       seed=s)["status"] == "STRUCTURED"
            self.assertEqual(hits, 20, msg="period %.1f s" % T)

    def test_the_scanned_lag_range_is_reported(self):
        """So WHITE cannot quietly mean 'white inside a window I never named'."""
        ts = [i * 2.5 for i in range(120)]
        s = F.slotted_scan(ts, [float(i % 7) for i in range(120)],
                           n_slots=12, n_perm=20, seed=0)
        self.assertAlmostEqual(s["lag_range_s"], 30.0, places=6)

    def test_no_period_is_claimed(self):
        """Both textbook handles were measured and both were refused."""
        ts = [i * 2.5 for i in range(120)]
        rng = random.Random(4)
        xs = [math.sin(2 * math.pi * i / 10.0) + rng.gauss(0, 0.05)
              for i in range(120)]
        s = F.slotted_scan(ts, xs, n_perm=50, seed=0)
        self.assertIsNone(s["period_s"])
        self.assertIn("Lomb-Scargle", s["period_note"])

    def test_a_dead_clock_is_reported_not_assumed(self):
        s = F.slotted_scan([7.0] * 40, [float(i) for i in range(40)])
        self.assertEqual(s["status"], "NO_CLOCK")

    def test_slotted_autocorr_rejects_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            F.slotted_autocorr([1.0, 2.0], [1.0], 1.0, 3)

    def test_local_normalisation_keeps_rho_bounded(self):
        rng = random.Random(2)
        ts = self._poisson(120, 3)
        xs = [rng.gauss(0, 1) * (1 + 10 * (i % 5 == 0)) for i in range(120)]
        for s in F.slotted_autocorr(ts, xs, 0.5, 20):
            if s["rho"] is not None:
                self.assertLessEqual(abs(s["rho"]), 1.0 + 1e-12)


class TestClockOnTheRouter(Store):

    def test_without_a_clock_the_router_says_lag_is_a_reading_count(self):
        self.band_breaking(clock=False)
        n = F.route("c001")["negative_evidence"]
        self.assertTrue(any("not a duration" in x for x in n))

    def test_with_a_clock_it_does_not(self):
        self.band_breaking(clock=True)
        n = F.route("c001")["negative_evidence"]
        self.assertFalse(any("not a duration" in x for x in n))

    def test_reading_times_prefers_the_monotonic_clock(self):
        self.assertEqual(F._reading_times([{"t_s": 3.0, "ts": "t000"}]), [3.0])

    def test_reading_times_falls_back_to_iso(self):
        t = F._reading_times([{"t_s": None, "ts": "2026-08-05T12:00:00"},
                              {"t_s": None, "ts": "2026-08-05T12:00:30"}])
        self.assertAlmostEqual(t[1] - t[0], 30.0)

    def test_reading_times_gives_up_on_an_unparseable_stamp(self):
        self.assertIsNone(F._reading_times([{"t_s": None, "ts": "t000"}]))


# ---------------------------------------------------------------- FCL-13
class TestMultiplicityCorrection(unittest.TestCase):

    def test_bh_and_bonferroni_agree_on_the_single_smallest_p(self):
        """At rank 1, k*alpha/m IS alpha/m. BH buys nothing with one effect,
        and saying so is the point of measuring it."""
        p = [0.001, 0.4, 0.6, 0.9]
        self.assertEqual(F.bh_reject(p, 0.05, "bh")[0],
                         F.bh_reject(p, 0.05, "bonferroni")[0])

    def test_bh_rejects_more_when_several_are_truly_small(self):
        p = [0.008, 0.012, 0.02, 0.9]
        bh, _ = F.bh_reject(p, 0.05, "bh")
        bon, _ = F.bh_reject(p, 0.05, "bonferroni")
        self.assertGreater(len(bh), len(bon))
        self.assertTrue(bon.issubset(bh))

    def test_by_is_strictly_more_conservative_than_bh(self):
        p = [0.008, 0.012, 0.02, 0.9]
        by, _ = F.bh_reject(p, 0.05, "by")
        bh, _ = F.bh_reject(p, 0.05, "bh")
        self.assertTrue(by.issubset(bh))

    def test_nothing_small_means_nothing_rejected(self):
        self.assertEqual(F.bh_reject([0.4, 0.6, 0.9], 0.05, "bh")[0], set())

    def test_an_empty_family_is_not_a_division(self):
        self.assertEqual(F.bh_reject([], 0.05, "bh"), (set(), 0.0))

    def test_an_unknown_method_is_refused(self):
        with self.assertRaises(ValueError):
            F.bh_reject([0.01], 0.05, "holm")

    def test_the_null_rate_holds_under_bh_too(self):
        rng = random.Random(7)
        fires = 0
        for _ in range(400):
            rs = [{"covariates": {"phase": rng.randrange(4)}}
                  for _ in range(200)]
            hit = {i for i in range(200) if rng.random() < 0.1}
            if F.covariate_concentration(hit, rs, method="bh"):
                fires += 1
        self.assertLessEqual(fires / 400.0, 0.05)

    def test_the_method_used_is_recorded_on_every_finding(self):
        rng = random.Random(9)
        rs, hit = [], set()
        for i in range(200):
            rain = 1 if i % 4 == 0 else 0
            rs.append({"covariates": {"rain": rain}})
            if rng.random() < (0.9 if rain else 0.05):
                hit.add(i)
        self.assertEqual(F.covariate_concentration(hit, rs)[0]["method"], "bh")


class TestBinomTail(unittest.TestCase):

    def test_it_matches_a_hand_computed_case(self):
        self.assertAlmostEqual(F._binom_tail(2, 3, 0.5), 0.5, places=12)

    def test_the_full_tail_is_one(self):
        self.assertAlmostEqual(F._binom_tail(0, 10, 0.3), 1.0, places=12)

    def test_beyond_n_is_zero(self):
        self.assertEqual(F._binom_tail(11, 10, 0.3), 0.0)

    def test_it_is_monotone_decreasing_in_k(self):
        vals = [F._binom_tail(k, 20, 0.4) for k in range(1, 20)]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_large_n_does_not_overflow(self):
        """math.comb(2000, i) is an exact int that will not convert to float.
        The first draft multiplied it by p**i and raised OverflowError."""
        self.assertGreater(F._binom_tail(700, 2000, 0.3), 0.0)
        self.assertGreater(F._binom_tail(3000, 10000, 0.3), 0.0)

    def test_it_is_close_to_the_normal_approximation_at_large_n(self):
        """Close, not equal -- the exact tail is the one being used."""
        n, p = 2000, 0.3
        k = int(n * p + 2 * math.sqrt(n * p * (1 - p)))
        mu, sd = n * p, math.sqrt(n * p * (1 - p))
        approx = 0.5 * math.erfc(((k - 0.5 - mu) / sd) / math.sqrt(2.0))
        self.assertAlmostEqual(F._binom_tail(k, n, p), approx, places=2)

    def test_p_at_least_one_is_one_minus_the_empty_case(self):
        self.assertAlmostEqual(F._binom_tail(1, 50, 0.2),
                               1.0 - 0.8 ** 50, places=12)


class TestRouterContract(Store):

    def test_it_proposes_and_says_so(self):
        self.band_breaking(anchor_dev=0.0)
        self.assertIn("PROPOSAL ONLY", F.route("c001")["note"])

    def test_every_route_name_is_one_of_the_four(self):
        self.band_breaking(anchor_dev=0.4, cov={"rain": 1})
        for c in F.route("c001")["candidates"]:
            self.assertIn(c["route"], F.ROUTES)

    def test_candidates_are_ranked_by_weight(self):
        self.band_breaking(anchor_dev=0.4, cov={"rain": 1})
        w = [c["weight"] for c in F.route("c001")["candidates"]]
        self.assertEqual(w, sorted(w, reverse=True))

    def test_no_candidate_carries_zero_weight(self):
        """The FCL-1 mechanism in general form: no evidence, no candidate."""
        for dev in (0.0, 0.4, None):
            self.band_breaking(anchor_dev=dev, seed=1)
            for c in F.route(sorted(F._claims())[-1])["candidates"]:
                self.assertGreater(c["weight"], 0.0)

    def test_two_routes_can_fire_at_once(self):
        """A residual is allowed to be more than one thing."""
        rng = random.Random(2)
        F.claim("piezo baseline", "piezo_trunk_n", 0.0, 1.0)
        for i in range(200):
            rain = 1 if i % 4 == 0 else 0
            broke = rng.random() < (0.9 if rain else 0.02)
            F.reading("piezo_trunk_n", 2.0 if broke else 0.5,
                      anchor_dev=0.4 if broke else 0.0,
                      covariates={"rain": rain}, ts="t%03d" % i)
        routes = {c["route"] for c in F.route("c001")["candidates"]}
        self.assertIn("INSTRUMENT", routes)
        self.assertIn("MISSING_VARIABLE", routes)


if __name__ == "__main__":
    unittest.main()
