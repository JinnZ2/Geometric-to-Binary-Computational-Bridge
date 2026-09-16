"""IX-1..6: the God's Eye View integration map, and what makes its guard FAIL.

Stdlib only. The map is eleven folders of links.json under
integrations/gods-eye-view/. Its README.md files and INTEGRATION_INDEX.json
are views; the guard fails when a view drifts, when a crosslink is not
reciprocated, when a path does not exist, or when an avenue cannot fail.
Several tests here build a broken map in a temp dir and require the guard
to notice -- the playground `broken()` gate applied to the guard itself.

IX-6 is the join: the feed-state port must reproduce every case GEV ships
in src/data/manager.test.mjs, so the epistemology table cannot drift from
the precedence it claims to mirror.

IX-7 is the coast harness (av-mob-1): the ports of arcOffsetEnu,
estimateTurnRateDps and staleCoastLimitSeconds, and the mechanics of the
divergence measurement on synthetic tracks whose generator is not the coast
model. It is NOT the measurement, which needs real fixes and is unrun.
"""

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAP = os.path.join(ROOT, "integrations", "gods-eye-view")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CL = _load("gev_crosslinks", os.path.join(MAP, "crosslinks.py"))
FE = _load("gev_feed_state", os.path.join(MAP, "06-feed-integrity", "feed_state_epistemology.py"))
CD = _load("gev_coast", os.path.join(MAP, "04-mobility-transport", "coast_divergence.py"))
import claims_index as CI  # noqa: E402


class TestIX1MapHolds(unittest.TestCase):
    """IX-1: the committed map passes every check, with GEV paths verified when a checkout is present."""

    def test_no_errors(self):
        errs, notes = CL.check()
        self.assertEqual(errs, [], "\n".join(errs))

    def test_eleven_domains_each_with_avenues(self):
        doms = [d for d in CL.load() if "_error" not in d]
        self.assertEqual(len(doms), 11)
        for d in doms:
            self.assertGreaterEqual(len(d["avenues"]), 3, d["id"])

    def test_every_avenue_names_a_failure(self):
        for d in CL.load():
            for a in d["avenues"]:
                self.assertTrue(a["fails_if"].strip(), f"{d['id']}/{a['id']}")
                self.assertGreater(len(a["fails_if"]), 40, f"{d['id']}/{a['id']}: too short to name an input")

    def test_gev_checkout_status_is_stated(self):
        errs, notes = CL.check()
        if CL.gev_root() is None:
            self.assertTrue(any("UNVERIFIED" in n for n in notes))
        else:
            self.assertFalse(any("gev paths UNVERIFIED" in n for n in notes))


class TestIX2Reciprocity(unittest.TestCase):
    """IX-2: a one-way sibling link is an error, and the guard says which direction is missing."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        shutil.copytree(MAP, os.path.join(self.tmp, "map"), dirs_exist_ok=True)
        self.here = os.path.join(self.tmp, "map")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _edit(self, folder, fn):
        p = os.path.join(self.here, folder, "links.json")
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        fn(d)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1, ensure_ascii=False)

    def _check(self):
        return CL.check(here=self.here, root=ROOT, gev=None if CL.gev_root() is None else CL.gev_root(),
                        mounts=CL.fieldlink_mounts())

    def test_committed_copy_passes(self):
        errs, _ = self._check()
        self.assertEqual(errs, [])

    def test_dropping_one_direction_fails(self):
        self._edit("01-geo-seismic", lambda d: d["siblings"].remove("feed-integrity"))
        errs, _ = self._check()
        self.assertTrue(any("feed-integrity -> geo-seismic is not reciprocated" in e for e in errs), errs)

    def test_unknown_sibling_fails(self):
        self._edit("01-geo-seismic", lambda d: d["siblings"].append("ghost"))
        errs, _ = self._check()
        self.assertTrue(any("sibling 'ghost' does not exist" in e for e in errs), errs)

    def test_missing_bridge_path_fails(self):
        self._edit("01-geo-seismic", lambda d: d["bridge"].append({"path": "no/such/file.py", "role": "x"}))
        errs, _ = self._check()
        self.assertTrue(any("bridge path missing: no/such/file.py" in e for e in errs), errs)

    def test_unknown_mount_fails(self):
        self._edit("01-geo-seismic", lambda d: d["ecosystem"].append({"mount": "not-a-repo", "why": "x"}))
        errs, _ = self._check()
        self.assertTrue(any("mount 'not-a-repo' not in .fieldlink.json" in e for e in errs), errs)

    def test_avenue_without_fails_if_fails(self):
        def fn(d):
            d["avenues"][0]["fails_if"] = ""
        self._edit("01-geo-seismic", fn)
        errs, _ = self._check()
        self.assertTrue(any("avenue.fails_if empty" in e for e in errs), errs)

    def test_bad_direction_and_cost_fail(self):
        def fn(d):
            d["avenues"][0]["direction"] = "sideways"
            d["avenues"][0]["cost"] = "free"
        self._edit("01-geo-seismic", fn)
        errs, _ = self._check()
        self.assertTrue(any("direction 'sideways'" in e for e in errs), errs)
        self.assertTrue(any("cost 'free'" in e for e in errs), errs)

    def test_stale_view_fails(self):
        p = os.path.join(self.here, "03-orbital", "README.md")
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\nhand edit\n")
        errs, _ = self._check()
        self.assertTrue(any("orbital: README.md stale" in e for e in errs), errs)

    def test_consent_share_ok_false_with_mount_fails(self):
        p = os.path.join(self.here, "05-infrastructure", "consent.json")
        with open(p, encoding="utf-8") as fh:
            c = json.load(fh)
        cables = [k for k in c["packs"] if k["share_ok"] is False][0]
        cables["mount"] = "atlas/remote/gods-eye-view/cables.json"
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(c, fh)
        errs, _ = self._check()
        self.assertTrue(any("share_ok is false but a mount is declared" in e for e in errs), errs)

    def test_map_must_name_every_folder(self):
        p = os.path.join(self.here, "README.md")
        with open(p, encoding="utf-8") as fh:
            body = fh.read()
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body.replace("11-visualization", "11-visualisation"))
        errs, _ = self._check()
        self.assertTrue(any("does not name 11-visualization" in e for e in errs), errs)


class TestIX3Views(unittest.TestCase):
    """IX-3: render is deterministic and the committed views equal it."""

    def test_render_is_a_pure_function_of_links(self):
        doms = [d for d in CL.load() if "_error" not in d]
        by_id = {d["id"]: d for d in doms}
        for d in doms:
            self.assertEqual(CL.render_readme(d, by_id), CL.render_readme(d, by_id))
        self.assertEqual(CL.render_index(doms), CL.render_index(doms))

    def test_index_is_a_view_not_a_second_authority(self):
        with open(os.path.join(MAP, "INTEGRATION_INDEX.json"), encoding="utf-8") as fh:
            idx = json.load(fh)
        self.assertIn("VIEW", idx["_comment"])
        for entry in idx["domains"]:
            with open(os.path.join(MAP, entry["folder"], "links.json"), encoding="utf-8") as fh:
                src = json.load(fh)
            self.assertEqual(entry["siblings"], src["siblings"])
            self.assertEqual([a["id"] for a in entry["avenues"]], [a["id"] for a in src["avenues"]])

    def test_gev_view_names_every_folder(self):
        doms = [d for d in CL.load() if "_error" not in d]
        view = CL.render_gev_view(doms)
        for d in doms:
            self.assertIn(d["_dir"], view)
        self.assertIn("A VIEW", view)


class TestIX4IdHygiene(unittest.TestCase):
    """IX-4: the map cannot leak a claim family into claims_index by being scanned."""

    def test_guard_pattern_matches_the_index_pattern(self):
        self.assertEqual(CL.CLAIM_ID_RX.pattern, CI.ID_RX.pattern)

    def test_no_avenue_id_reads_as_a_claim_id(self):
        for d in CL.load():
            for a in d["avenues"]:
                self.assertIsNone(CI.ID_RX.search(a["id"]), a["id"])

    def test_an_uppercase_avenue_id_would_fail(self):
        # Built at runtime so this file does not itself put the id into the index.
        self.assertIsNotNone(CL.CLAIM_ID_RX.search("GEO" + "-" + "1"))


class TestIX5Scope(unittest.TestCase):
    """IX-5: the matrix reports filled cells and stops; nothing in the module generates pairs."""

    def test_matrix_marks_only_declared_taps(self):
        doms = [d for d in CL.load() if "_error" not in d]
        out = CL.matrix(doms, CL.fieldlink_mounts())
        for d in doms:
            row = [ln for ln in out.splitlines() if ln.startswith(f"| {d['id']} ")][0]
            self.assertEqual(row.count("x"), len(d["ecosystem"]), d["id"])

    def test_untapped_mounts_are_called_absences(self):
        doms = [d for d in CL.load() if "_error" not in d]
        out = CL.matrix(doms, CL.fieldlink_mounts())
        self.assertIn("absence, not a suggestion", out)

    def test_no_proposer_in_the_module(self):
        names = [n for n in dir(CL) if callable(getattr(CL, n)) and not n.startswith("_")]
        for n in names:
            self.assertNotRegex(n, r"propose|suggest|generate_pairs|recommend", n)


class TestIX6FeedStatePort(unittest.TestCase):
    """IX-6: the port reproduces the cases GEV ships in src/data/manager.test.mjs."""

    SHIPPED = [
        ({"error": "feed down", "count": 0, "lastUpdate": None}, "unavailable"),
        ({"mode": "sim", "count": 100, "lastUpdate": 1}, "fallback"),
        ({"source": "adsb.lol", "count": 10, "lastUpdate": 1}, "fallback"),
        ({"stale": True, "count": 0, "lastUpdate": 1}, "stale"),
        ({"error": "partial group failure", "count": 50, "lastUpdate": 1}, "degraded"),
        ({"loading": True}, "loading"),
        ({"count": 5, "lastUpdate": 1}, "nominal"),
        ({"status": "zoom-in", "error": "zoom in to search", "count": 12}, "nominal"),
        ({"status": "idle"}, "nominal"),
        ({"status": "empty", "error": "no records in view"}, "nominal"),
        ({"status": "zoom-in", "stale": True, "count": 12}, "stale"),
        ({"status": "zoom-in", "loading": True}, "loading"),
        ({"status": "unavailable", "error": "down"}, "unavailable"),
        ({"error": "boom"}, "unavailable"),
    ]

    def test_shipped_cases(self):
        for stats, want in self.SHIPPED:
            self.assertEqual(FE.layer_feed_state(stats), want, stats)

    def test_cases_are_still_in_gev_when_present(self):
        gev = CL.gev_root()
        if gev is None:
            self.skipTest("no GEV checkout")
        with open(os.path.join(gev, "src", "data", "manager.test.mjs"), encoding="utf-8") as fh:
            body = fh.read()
        for stats, want in self.SHIPPED:
            self.assertIn(f"'{want}'", body)
        self.assertGreaterEqual(body.count("layerFeedState("), len(self.SHIPPED))

    def test_sim_is_asserted_not_inferred(self):
        g = FE.grade({"mode": "sim", "count": 100, "lastUpdate": 1})
        self.assertEqual(g["feed_state"], "fallback")
        self.assertEqual(g["epistemology"], "asserted")
        self.assertLessEqual(g["confidence_cap"], 1 - FE.MOCK_PENALTY)
        h = FE.grade({"source": "adsb.lol", "count": 10, "lastUpdate": 1})
        self.assertEqual(h["feed_state"], "fallback")
        self.assertEqual(h["epistemology"], "inferred")

    def test_no_reading_states_carry_no_grade(self):
        for stats in ({"loading": True}, {"error": "boom"}):
            g = FE.grade(stats)
            self.assertIsNone(g["epistemology"])
            self.assertIsNone(g["confidence_cap"])

    def test_every_feed_state_has_a_row(self):
        self.assertEqual(set(FE.TABLE), set(FE.FEED_STATES))
        for epi, _ in FE.TABLE.values():
            self.assertIn(epi, FE.EPISTEMOLOGY + (None,))

    def test_stale_penalty_is_declared_placeholder(self):
        self.assertIn("stale_is_placeholder", FE.as_json())
        with open(FE.__file__, encoding="utf-8") as fh:
            self.assertIn("PLACEHOLDER", fh.read())


class TestIX7CoastHarness(unittest.TestCase):
    """IX-7: the coast ports and the harness mechanics. Not the measurement."""

    def test_straight_offset_matches_trigonometry(self):
        e, n, c = CD.arc_offset_enu(100.0, 90.0, 0.0, 10.0)
        self.assertAlmostEqual(e, 1000.0, places=6)
        self.assertAlmostEqual(n, 0.0, places=6)
        self.assertEqual(c, 90.0)
        e, n, _ = CD.arc_offset_enu(100.0, 0.0, 0.0, 10.0)
        self.assertAlmostEqual(n, 1000.0, places=6)

    def test_turn_offset_closes_a_circle(self):
        # 1 deg/s for 360 s at any speed returns to the start; end course wraps to the start course
        e, n, c = CD.arc_offset_enu(50.0, 30.0, 1.0, 360.0)
        self.assertAlmostEqual(e, 0.0, places=6)
        self.assertAlmostEqual(n, 0.0, places=6)
        self.assertAlmostEqual(c, 30.0, places=9)

    def test_turn_rate_port_gates_like_the_original(self):
        s = [{"t_s": 0, "track_deg": 10, "speed_mps": 100}, {"t_s": 10, "track_deg": 20, "speed_mps": 100}]
        self.assertAlmostEqual(CD.estimate_turn_rate_dps(s), 1.0)
        # below the noise floor reads as straight
        s2 = [{"t_s": 0, "track_deg": 10, "speed_mps": 100}, {"t_s": 10, "track_deg": 12, "speed_mps": 100}]
        self.assertEqual(CD.estimate_turn_rate_dps(s2), 0.0)
        # clamped at +-4 deg/s
        s3 = [{"t_s": 0, "track_deg": 0, "speed_mps": 100}, {"t_s": 10, "track_deg": 170, "speed_mps": 100}]
        self.assertEqual(CD.estimate_turn_rate_dps(s3), 4.0)
        # dt outside 2..120 s is skipped; hover speed is skipped
        s4 = [{"t_s": 0, "track_deg": 0, "speed_mps": 100}, {"t_s": 1, "track_deg": 90, "speed_mps": 100}]
        self.assertEqual(CD.estimate_turn_rate_dps(s4), 0.0)
        s5 = [{"t_s": 0, "track_deg": 0, "speed_mps": 2}, {"t_s": 10, "track_deg": 90, "speed_mps": 2}]
        self.assertEqual(CD.estimate_turn_rate_dps(s5), 0.0)
        # angle unwrapping across north
        s6 = [{"t_s": 0, "track_deg": 355, "speed_mps": 100}, {"t_s": 10, "track_deg": 5, "speed_mps": 100}]
        self.assertAlmostEqual(CD.estimate_turn_rate_dps(s6), 1.0)

    def test_stale_coast_limit_port(self):
        self.assertEqual(CD.stale_coast_limit_s(1000, 1030), 90)
        self.assertEqual(CD.stale_coast_limit_s(1000, 1000), 60)
        self.assertEqual(CD.stale_coast_limit_s(1000, 1500), 300)

    def test_straight_track_sits_on_the_harness_floor(self):
        fixes = CD._great_circle_track(47.0, 8.0, 84.0, 230.0, 0.0, 21, 15)
        r = CD.measure(fixes, max_dt_s=300, bin_s=60)
        worst = max(x["arc_p90_m"] for x in r["rows"])
        self.assertLess(worst, 200.0)
        self.assertGreater(worst, 20.0)   # the floor is real and stated, not zero

    def test_unseen_turn_diverges_with_horizon(self):
        fixes = CD._great_circle_track(47.0, 8.0, 84.0, 230.0, 0.0, 21, 15, turn_dps=2.0, turn_after_s=150)
        r = CD.measure(fixes, max_dt_s=300, bin_s=60)
        p90 = [x["arc_p90_m"] for x in r["rows"]]
        self.assertTrue(all(b > a for a, b in zip(p90[:3], p90[1:4])), p90)
        self.assertGreater(p90[3], 1000.0)
        self.assertIsNotNone(r["p90_widening_mps"])
        self.assertGreater(r["p90_widening_mps"], 0.0)

    def test_measure_skips_ground_and_reports_no_rows_on_empty(self):
        self.assertEqual(CD.measure([])["rows"], [])
        fixes = CD._great_circle_track(47.0, 8.0, 84.0, 230.0, 0.0, 5, 15)
        for f in fixes:
            f["on_ground"] = True
        self.assertEqual(CD.measure(fixes)["n_pairs"], 0)

    def test_harness_says_it_is_not_the_measurement(self):
        self.assertIsNone(CD.measure([])["measured_on_real_fixes"])
        with open(CD.__file__, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("NOT been run", body)


if __name__ == "__main__":
    unittest.main()
