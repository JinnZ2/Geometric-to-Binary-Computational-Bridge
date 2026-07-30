"""Tests for Silicon/fp4_autopilot.py and the FP-4 firmware's phase table.

Stdlib only. Two things are being tested here and they are different in kind:

* the estimator -- does the fit recover a hidden anomaly factor, and does it
  refuse when the design cannot;
* the firmware -- does ``buildPhaseTable`` in ``field_propulsion_fp4.ino``
  actually emit the traveling wave it labels. That function is C, so it is
  ported here and checked against ``propulsion_bounds.aliased_modes``. The
  port is the test; if the .ino changes, this must change with it.

The self-test in ``null_world_test`` is itself under test. It has to pass on a
good design and it has to FAIL on the collinear one -- a self-test that
approves everything approves nothing.
"""

import cmath
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from fp4_autopilot import (  # noqa: E402
    C_AIR,
    MAX_VIF,
    RADIATION_STATES,
    Trial,
    _Simulator,
    check_muted_control,
    fit_thrust_model,
    null_world_test,
    read_serial_campaign,
    run_campaign,
    variance_inflation,
    verdict_from_fit,
)
from propulsion_bounds import aliased_modes  # noqa: E402

N_NODES = 8
PHASE_STEPS = 8


# ---------------------------------------------------------------------------
# Firmware port
# ---------------------------------------------------------------------------

def reduce_mode(m, n=N_NODES):
    """Port of ``reduceMode`` -- reduce to the signed range (-n/2, n/2]."""
    r = ((m % n) + n) % n
    return r - n if r > n // 2 else r


def build_phase_table(m, n=N_NODES, steps=PHASE_STEPS):
    """Port of ``buildPhaseTable``. One byte per step, bit i = node i level."""
    table = []
    for s in range(steps):
        word = 0
        for i in range(n):
            off = (-i * m) % n
            if (s - off + steps) % steps < steps // 2:
                word |= 1 << i
        table.append(word)
    return table


def node_phase(table, i, steps=PHASE_STEPS):
    """Recover node i's carrier phase from the drive table's fundamental bin."""
    x = [1.0 if (table[s] >> i) & 1 else -1.0 for s in range(steps)]
    c = sum(x[s] * cmath.exp(-2j * math.pi * s / steps) for s in range(steps))
    return cmath.phase(c)


def _wrap(d):
    return ((d + math.pi) % (2 * math.pi)) - math.pi


class TestFirmwarePhaseTable(unittest.TestCase):
    """The drive table must realise +2*pi*m*i/N, in that sign."""

    def test_recovered_gradient_matches_the_mode(self):
        for m_in in (0, 1, 2, 3, 4, 6, -2, -7, 14, 22):
            m = reduce_mode(m_in)
            table = build_phase_table(m)
            phases = [node_phase(table, i) for i in range(N_NODES)]
            want = _wrap(2 * math.pi * m / N_NODES)
            for i in range(N_NODES - 1):
                got = _wrap(phases[i + 1] - phases[i])
                self.assertAlmostEqual(got, want, places=9,
                                       msg=f"m={m} node {i}")

    def test_sign_convention_is_not_inverted(self):
        """The defect this test exists for: +i*m instead of -i*m flips the wave."""
        m = 2
        table = build_phase_table(m)
        got = _wrap(node_phase(table, 1) - node_phase(table, 0))
        self.assertGreater(got, 0.0, "positive m must give a positive gradient")
        self.assertAlmostEqual(got, 2 * math.pi * m / N_NODES, places=9)

    def test_firmware_agrees_with_propulsion_bounds_on_aliasing(self):
        for m_in in range(-20, 21):
            expected = aliased_modes(2 * math.pi * m_in / N_NODES, N_NODES)["m"]
            self.assertEqual(reduce_mode(m_in), expected, msg=f"m_in={m_in}")

    def test_fp2_identity_holds_in_the_drive_table(self):
        """3*pi/2 is m=6 -> m=-2; the two must be the SAME table, not similar."""
        self.assertEqual(reduce_mode(6), -2)
        self.assertEqual(build_phase_table(reduce_mode(6)), build_phase_table(-2))

    def test_all_modes_give_distinct_tables(self):
        tables = {tuple(build_phase_table(reduce_mode(m))) for m in range(N_NODES)}
        self.assertEqual(len(tables), N_NODES)

    def test_every_node_has_fifty_percent_duty(self):
        for m in range(N_NODES):
            table = build_phase_table(reduce_mode(m))
            for i in range(N_NODES):
                self.assertEqual(sum((w >> i) & 1 for w in table), PHASE_STEPS // 2)

    def test_mode_zero_drives_all_nodes_together(self):
        table = build_phase_table(0)
        for word in table:
            self.assertIn(word, (0, (1 << N_NODES) - 1))

    def test_reduced_range(self):
        for m_in in range(-30, 31):
            m = reduce_mode(m_in)
            self.assertLessEqual(m, N_NODES // 2)
            self.assertGreater(m, -N_NODES // 2)


# ---------------------------------------------------------------------------
# The fit
# ---------------------------------------------------------------------------

class TestFit(unittest.TestCase):

    def test_recovers_a_hidden_anomaly_factor(self):
        for k_true in (0.25, 0.6, 1.0, 2.5, 4.0):
            fit = run_campaign(_Simulator(anomaly_factor=k_true, seed=5),
                               repeats=4)["fit"]
            self.assertAlmostEqual(fit["k"], k_true, delta=0.12,
                                   msg=f"k_true={k_true}")

    def test_recovers_the_thermal_confounder_separately(self):
        """c must land near truth in BOTH worlds, or it is absorbing k."""
        for k_true in (0.5, 4.0):
            fit = run_campaign(_Simulator(anomaly_factor=k_true,
                                          thermal_coeff=2.0e-5, seed=5),
                               repeats=4)["fit"]
            self.assertAlmostEqual(fit["c_elec"], 2.0e-5, delta=4.0e-6)

    def test_recovers_the_balance_offset(self):
        fit = run_campaign(_Simulator(anomaly_factor=1.0, offset_n=7.5e-6,
                                      seed=5), repeats=4)["fit"]
        self.assertAlmostEqual(fit["offset"], 7.5e-6, delta=3.0e-6)

    def test_thermal_confounder_does_not_leak_into_k(self):
        """Ten-fold more driver heating must not move k."""
        cool = run_campaign(_Simulator(anomaly_factor=1.0, thermal_coeff=2e-6,
                                       seed=9), repeats=4)["fit"]
        hot = run_campaign(_Simulator(anomaly_factor=1.0, thermal_coeff=2e-4,
                                      seed=9), repeats=4)["fit"]
        self.assertAlmostEqual(cool["k"], hot["k"], delta=0.2)

    def test_k_scales_with_the_carrier_speed(self):
        """k = F*v/P_rad, so a faster carrier makes the same force a LARGER
        multiple of the bound -- the bound P/v is smaller. Quoting k without
        naming the carrier is meaningless, which is why carrier_v is echoed
        back in the fit."""
        trials = run_campaign(_Simulator(anomaly_factor=1.0, seed=3))["trials"]
        a = fit_thrust_model(trials, carrier_v=C_AIR)
        b = fit_thrust_model(trials, carrier_v=2 * C_AIR)
        self.assertAlmostEqual(b["k"], a["k"] * 2, places=9)
        self.assertEqual(a["carrier_v"], C_AIR)

    def test_rejects_bad_arguments(self):
        trials = run_campaign(_Simulator(seed=1))["trials"]
        with self.assertRaises(ValueError):
            fit_thrust_model(trials, carrier_v=0.0)
        with self.assertRaises(ValueError):
            fit_thrust_model(trials[:3])
        with self.assertRaises(ValueError):
            Trial(1.0, -1.0, 1.0)

    def test_singular_design_raises_rather_than_returning_a_number(self):
        """All trials identical: nothing to fit, and the fit must say so."""
        trials = [Trial(1e-6, 1e-3, 1.0) for _ in range(10)]
        with self.assertRaises(ValueError):
            fit_thrust_model(trials)


class TestIdentifiability(unittest.TestCase):
    """The defect the self-test caught: collinear regressors, confident error."""

    def test_amplitude_only_design_is_flagged(self):
        fit = run_campaign(_Simulator(anomaly_factor=4.0, seed=11),
                           states={"open": 1.0}, repeats=18)["fit"]
        self.assertGreater(fit["vif_k"], MAX_VIF)
        self.assertFalse(fit["identifiable"])

    def test_amplitude_only_design_reports_non_identifiable_not_null(self):
        """This is the whole point. The broken fit is TIGHT and WRONG."""
        res = run_campaign(_Simulator(anomaly_factor=4.0, seed=11),
                           states={"open": 1.0}, repeats=18)
        self.assertEqual(res["verdict"]["status"], "NON-IDENTIFIABLE")
        # ... and without the guard it would have said NULL:
        self.assertLess(res["fit"]["k"] + 2 * res["fit"]["k_se"], 1.0)
        # ... on a world where k was really 4.
        self.assertGreater(res["fit"]["r_squared"], 0.99)

    def test_decoupled_design_is_identifiable(self):
        fit = run_campaign(_Simulator(anomaly_factor=4.0, seed=11))["fit"]
        self.assertLess(fit["vif_k"], MAX_VIF)
        self.assertTrue(fit["identifiable"])

    def test_muted_state_alone_is_enough_to_break_collinearity(self):
        fit = run_campaign(_Simulator(anomaly_factor=4.0, seed=11),
                           states={"open": 1.0, "muted": 0.0})["fit"]
        self.assertTrue(fit["identifiable"])
        self.assertAlmostEqual(fit["k"], 4.0, delta=0.2)

    def test_vif_is_one_for_uncorrelated_regressors(self):
        self.assertAlmostEqual(variance_inflation([1, -1, 1, -1],
                                                  [1, 1, -1, -1]), 1.0, places=12)

    def test_vif_is_infinite_for_proportional_regressors(self):
        self.assertEqual(variance_inflation([1, 2, 3], [2, 4, 6]), float("inf"))

    def test_vif_grows_with_correlation(self):
        weak = variance_inflation([1, 2, 3, 4], [4, 1, 3, 2])
        strong = variance_inflation([1, 2, 3, 4], [1.0, 2.1, 2.9, 4.2])
        self.assertLess(weak, strong)
        self.assertGreater(strong, 20.0)

    def test_vif_handles_a_constant_regressor(self):
        self.assertAlmostEqual(variance_inflation([1, 2, 3], [5, 5, 5]), 1.0)

    def test_single_regressor_fit_reports_vif_one(self):
        trials = run_campaign(_Simulator(seed=2))["trials"]
        fit = fit_thrust_model(trials, fit_confounders=False)
        self.assertEqual(fit["vif_k"], 1.0)
        self.assertNotIn("c_elec", fit)


class TestVerdict(unittest.TestCase):

    @staticmethod
    def _fit(k, se, identifiable=True, vif=1.2):
        return {"k": k, "k_se": se, "identifiable": identifiable,
                "vif_k": vif, "max_vif": MAX_VIF}

    def test_anomaly_requires_clearing_the_margin(self):
        self.assertEqual(verdict_from_fit(self._fit(4.0, 0.05))["status"],
                         "ANOMALY")

    def test_null_requires_only_sitting_under_the_bound(self):
        self.assertEqual(verdict_from_fit(self._fit(0.6, 0.02))["status"],
                         "NULL")

    def test_exactly_at_the_bound_is_unresolved_not_null(self):
        """The asymmetry that the first decision rule got wrong."""
        self.assertEqual(verdict_from_fit(self._fit(1.0, 0.02))["status"],
                         "UNRESOLVED")

    def test_between_bound_and_margin_is_unresolved(self):
        v = verdict_from_fit(self._fit(1.3, 0.05), margin=2.0)
        self.assertEqual(v["status"], "UNRESOLVED")

    def test_wide_interval_is_unresolved_even_when_k_is_large(self):
        self.assertEqual(verdict_from_fit(self._fit(4.0, 3.0))["status"],
                         "UNRESOLVED")

    def test_non_identifiable_beats_every_other_verdict(self):
        for k, se in ((0.1, 0.01), (4.0, 0.01), (1.0, 5.0)):
            v = verdict_from_fit(self._fit(k, se, identifiable=False, vif=140.0))
            self.assertEqual(v["status"], "NON-IDENTIFIABLE")
            self.assertIn("collinear", v["note"])

    def test_margin_below_the_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            verdict_from_fit(self._fit(1.0, 0.1), margin=0.5, bound=1.0)

    def test_rejects_nonpositive_thresholds(self):
        with self.assertRaises(ValueError):
            verdict_from_fit(self._fit(1.0, 0.1), margin=0.0)
        with self.assertRaises(ValueError):
            verdict_from_fit(self._fit(1.0, 0.1), bound=0.0)

    def test_larger_z_widens_the_interval_and_softens_the_call(self):
        self.assertEqual(verdict_from_fit(self._fit(1.4, 0.15), z=2.0)["status"],
                         "ANOMALY")
        self.assertEqual(verdict_from_fit(self._fit(1.4, 0.15), z=4.0)["status"],
                         "UNRESOLVED")

    def test_a_calibration_margin_can_absorb_a_small_excess(self):
        self.assertEqual(verdict_from_fit(self._fit(1.4, 0.05))["status"],
                         "ANOMALY")
        self.assertEqual(verdict_from_fit(self._fit(1.4, 0.05),
                                          margin=2.0)["status"], "UNRESOLVED")


class TestMutedControl(unittest.TestCase):

    def test_a_good_control_passes(self):
        res = run_campaign(_Simulator(seed=4))
        self.assertTrue(res["muted_control"]["ok"])
        self.assertTrue(res["muted_control"]["checked"])

    def test_a_mute_that_changes_electrical_power_is_caught(self):
        """Blocking the output changes the acoustic load; that must be visible."""
        trials = []
        for amp in (0.5, 1.0):
            p = 2.0 * amp ** 2
            trials.append(Trial(1e-6, 0.02 * p, p, amp, state="open"))
            trials.append(Trial(1e-6, 0.0, p * 1.4, amp, state="muted"))
        r = check_muted_control(trials)
        self.assertFalse(r["ok"])
        self.assertIn("electrical power", r["note"])

    def test_a_leaky_mute_is_caught(self):
        trials = []
        for amp in (0.5, 1.0):
            p = 2.0 * amp ** 2
            trials.append(Trial(1e-6, 0.02 * p, p, amp, state="open"))
            trials.append(Trial(1e-6, 0.02 * p * 0.4, p, amp, state="muted"))
        r = check_muted_control(trials)
        self.assertFalse(r["ok"])
        self.assertIn("leaks", r["note"])

    def test_non_overlapping_amplitudes_cannot_be_compared(self):
        trials = [Trial(1e-6, 1e-3, 1.0, 0.5, state="open"),
                  Trial(1e-6, 0.0, 2.0, 1.0, state="muted")]
        r = check_muted_control(trials)
        self.assertFalse(r["ok"])
        self.assertFalse(r["checked"])

    def test_absent_muted_state_is_reported_as_unchecked_not_as_pass(self):
        res = run_campaign(_Simulator(seed=4), states={"open": 1.0,
                                                       "detuned": 0.35})
        self.assertFalse(res["muted_control"]["checked"])


class TestNullWorldSelfTest(unittest.TestCase):
    """The self-test is itself under test: it must approve good, reject bad."""

    def test_passes_on_the_decoupled_design(self):
        st = null_world_test(runs=12, seed=7)
        self.assertTrue(st["passed"], st)
        self.assertLessEqual(st["false_positive_rate"], 0.10)
        self.assertLessEqual(st["false_negative_rate"], 0.10)

    def test_fails_on_the_collinear_design(self):
        """A self-test that cannot fail is decoration."""
        st = null_world_test(runs=8, seed=7, states={"open": 1.0})
        self.assertFalse(st["passed"])
        self.assertGreater(st["anomalous_world_calls"]["NON-IDENTIFIABLE"], 0)

    def test_anomalous_world_is_detected(self):
        st = null_world_test(runs=10, seed=1, anomaly_factor=3.0)
        self.assertGreaterEqual(st["power_anomaly"], 0.5)

    def test_null_at_the_boundary_is_mostly_unresolved(self):
        """Placing the null ON the bound is degenerate, and stays that way."""
        st = null_world_test(runs=12, seed=3, null_k_range=(1.0, 1.0))
        calls = st["null_world_calls"]
        self.assertGreater(calls["UNRESOLVED"], calls["NULL"])
        self.assertFalse(st["passed"])

    def test_a_huge_anomaly_is_never_called_null(self):
        st = null_world_test(runs=10, seed=2, anomaly_factor=50.0)
        self.assertEqual(st["false_negative_rate"], 0.0)

    def test_ground_truth_is_drawn_inside_the_requested_range(self):
        st = null_world_test(runs=20, seed=8, null_k_range=(0.2, 0.4))
        self.assertGreater(st["null_k_mean"], 0.2)
        self.assertLess(st["null_k_mean"], 0.4)

    def test_rejects_a_reversed_range(self):
        with self.assertRaises(ValueError):
            null_world_test(runs=2, null_k_range=(0.9, 0.1))

    def test_reproducible_for_a_fixed_seed(self):
        a = null_world_test(runs=6, seed=42)
        b = null_world_test(runs=6, seed=42)
        self.assertEqual(a["null_world_calls"], b["null_world_calls"])
        self.assertEqual(a["anomalous_world_calls"], b["anomalous_world_calls"])


class TestCampaign(unittest.TestCase):

    def test_default_states_include_the_muted_control(self):
        self.assertIn("muted", RADIATION_STATES)
        self.assertEqual(RADIATION_STATES["muted"], 0.0)

    def test_trial_count_is_states_times_amplitudes_times_repeats(self):
        res = run_campaign(_Simulator(seed=1), amplitudes=(0.5, 1.0), repeats=2)
        self.assertEqual(len(res["trials"]), 3 * 2 * 2)

    def test_every_state_is_represented(self):
        res = run_campaign(_Simulator(seed=1))
        self.assertEqual(set(res["fit"]["states"]), set(RADIATION_STATES))

    def test_muted_state_radiates_nothing(self):
        res = run_campaign(_Simulator(seed=1))
        muted = [t for t in res["trials"] if t.state == "muted"]
        self.assertTrue(muted)
        self.assertTrue(all(t.p_rad_w == 0.0 for t in muted))
        self.assertTrue(all(t.p_elec_w > 0.0 for t in muted))

    def test_rejects_an_empty_state_set(self):
        with self.assertRaises(ValueError):
            run_campaign(_Simulator(seed=1), states={})

    def test_phase_is_recorded_but_does_not_change_the_verdict(self):
        a = run_campaign(_Simulator(anomaly_factor=2.0, seed=6), dphi=0.0)
        b = run_campaign(_Simulator(anomaly_factor=2.0, seed=6),
                         dphi=3 * math.pi / 2)
        self.assertEqual(a["verdict"]["status"], b["verdict"]["status"])
        self.assertAlmostEqual(a["fit"]["k"], b["fit"]["k"], places=12)
        self.assertAlmostEqual(b["trials"][0].dphi, 3 * math.pi / 2)


class TestSerialIngest(unittest.TestCase):

    GOOD = [
        "FP-4 instrument ready.",
        "BLOCK,start,state=open,mode=0,f=40000",
        "DATA,open,0.5000,0.000000,0.000012345,0.001000000,0.500000",
        "DATA,muted,0.5000,0.000000,0.000010000,0.000000000,0.500000",
        "BLOCK,end",
    ]

    def test_parses_data_lines_and_ignores_the_rest(self):
        trials = read_serial_campaign(self.GOOD)
        self.assertEqual(len(trials), 2)
        self.assertEqual(trials[0].state, "open")
        self.assertAlmostEqual(trials[0].force_n, 1.2345e-05)
        self.assertAlmostEqual(trials[1].p_rad_w, 0.0)

    def test_malformed_data_line_raises_rather_than_being_skipped(self):
        """A silently dropped point changes the design matrix."""
        with self.assertRaises(ValueError) as ctx:
            read_serial_campaign(["DATA,open,0.5,0.0,1e-5"])
        self.assertIn("7 fields", str(ctx.exception))

    def test_non_numeric_field_raises_with_the_line_number(self):
        with self.assertRaises(ValueError) as ctx:
            read_serial_campaign(["noise", "DATA,open,x,0,0,0,0"])
        self.assertIn("line 2", str(ctx.exception))

    def test_no_data_lines_raises(self):
        with self.assertRaises(ValueError):
            read_serial_campaign(["NEED,survey", "NEED,tare"])

    def test_negative_power_is_rejected_at_ingest(self):
        with self.assertRaises(ValueError):
            read_serial_campaign(["DATA,open,0.5,0.0,1e-5,-1.0,0.5"])

    def test_round_trip_from_serial_text_to_verdict(self):
        """The whole path: simulator -> DATA text -> parse -> fit -> verdict."""
        bench = _Simulator(anomaly_factor=4.0, seed=21)
        lines = ["FP-4 instrument ready."]
        for label, scale in RADIATION_STATES.items():
            for amp in (0.4, 0.6, 0.8, 1.0):
                for _ in range(3):
                    t = bench.measure(amp, 0.0, scale, label)
                    lines.append(f"DATA,{t.state},{t.amplitude:.4f},{t.dphi:.6f},"
                                 f"{t.force_n:.12f},{t.p_rad_w:.12f},"
                                 f"{t.p_elec_w:.6f}")
        trials = read_serial_campaign(lines)
        fit = fit_thrust_model(trials)
        self.assertTrue(fit["identifiable"])
        self.assertAlmostEqual(fit["k"], 4.0, delta=0.3)
        self.assertEqual(verdict_from_fit(fit)["status"], "ANOMALY")
        self.assertTrue(check_muted_control(trials)["ok"])


class TestBridgeTest(unittest.TestCase):

    def test_refuses_to_fabricate_a_ber_curve(self):
        from fp4_autopilot import ber_sweep
        with self.assertRaises(NotImplementedError) as ctx:
            ber_sweep(_Simulator(), [0.0, math.pi])
        self.assertIn("synthetic", str(ctx.exception))

    def test_uses_a_bench_that_can_transmit(self):
        from fp4_autopilot import ber_sweep

        class Bench:
            def transmit(self, dphi, bits):
                return int(bits * 0.5 * abs(math.cos(dphi)))

        out = ber_sweep(Bench(), [0.0, math.pi / 2], bits=1000)
        self.assertEqual(len(out), 2)
        self.assertAlmostEqual(out[0]["ber"], 0.5, places=3)
        self.assertAlmostEqual(out[1]["ber"], 0.0, places=3)

    def test_rejects_an_impossible_error_count(self):
        from fp4_autopilot import ber_sweep

        class Liar:
            def transmit(self, dphi, bits):
                return bits + 1

        with self.assertRaises(ValueError):
            ber_sweep(Liar(), [0.0], bits=100)

    def test_rejects_nonpositive_bit_count(self):
        from fp4_autopilot import ber_sweep
        with self.assertRaises(ValueError):
            ber_sweep(_Simulator(), [0.0], bits=0)


class TestNoiseSensitivity(unittest.TestCase):
    """Errors-in-variables: noise on P_rad attenuates k. Bound the effect."""

    def test_power_meter_noise_attenuates_k_but_not_fatally(self):
        for frac in (0.0, 0.05, 0.20):
            fits = []
            for seed in range(6):
                fits.append(run_campaign(
                    _Simulator(anomaly_factor=4.0, power_noise_frac=frac,
                               seed=100 + seed), repeats=4)["fit"]["k"])
            mean_k = sum(fits) / len(fits)
            self.assertLess(mean_k, 4.0 + 0.5)
            self.assertGreater(mean_k, 4.0 * (1.0 - 3.0 * frac) - 0.3,
                               msg=f"noise {frac} attenuated k to {mean_k}")

    def test_force_noise_widens_the_interval(self):
        quiet = run_campaign(_Simulator(anomaly_factor=4.0, force_noise_n=1e-7,
                                       seed=13), repeats=4)["fit"]
        loud = run_campaign(_Simulator(anomaly_factor=4.0, force_noise_n=1e-4,
                                       seed=13), repeats=4)["fit"]
        self.assertGreater(loud["k_se"], quiet["k_se"] * 10)

    def test_a_null_world_is_not_pushed_over_the_margin_by_noise(self):
        """False positives are the expensive error here."""
        rng = random.Random(0)
        anomalies = 0
        for _ in range(20):
            bench = _Simulator(anomaly_factor=rng.uniform(0.2, 0.9),
                               force_noise_n=1e-5,
                               seed=rng.randrange(1 << 30))
            if run_campaign(bench, repeats=4)["verdict"]["status"] == "ANOMALY":
                anomalies += 1
        self.assertLessEqual(anomalies, 2)


if __name__ == "__main__":
    unittest.main()
