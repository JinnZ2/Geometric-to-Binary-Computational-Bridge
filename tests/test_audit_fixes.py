"""
test_audit_fixes — regression tests for the audit-fix sweep.

Each test asserts the behaviour of *one* fix. Grouped by audit-track
(contract / performance / security) so a future regression points
back at the originating audit.
"""

from __future__ import annotations

import logging
import math
import tempfile
import unittest
from pathlib import Path

from sensing.firmware.sensor_drivers.base import SensorReading
from sensing.processing.primitives_encoder import (
    MAX_OBS_LINE_BYTES,
    Primitive,
    obs_line_to_primitive,
)


# ===========================================================================
# AUDIT 1 — contract enforcement
# ===========================================================================

class TestSchedulerDeterministicOrdering(unittest.TestCase):
    """Audit 1, SEVERE #3 — events with equal time + priority must
    fire in scheduling order, not in heap-quirk order."""

    def test_equal_time_and_priority_fires_in_scheduled_order(self):
        from bridges.event_scheduler import EventScheduler

        sched = EventScheduler()
        order = []
        for tag in ("a", "b", "c", "d"):
            sched.schedule(
                1.0,
                lambda t, s, _tag=tag: order.append(_tag),
                args=(1.0,),
                priority=0,
            )
        sched.run(2.0)
        self.assertEqual(order, ["a", "b", "c", "d"])

    def test_priority_breaks_time_tie(self):
        from bridges.event_scheduler import EventScheduler

        sched = EventScheduler()
        order = []
        sched.schedule(1.0, lambda t, s: order.append("low"),
                       args=(1.0,), priority=10)
        sched.schedule(1.0, lambda t, s: order.append("high"),
                       args=(1.0,), priority=-1)  # lower number = higher
        sched.run(2.0)
        self.assertEqual(order, ["high", "low"])


class TestAlternativeSpiceValidation(unittest.TestCase):
    """Audit 1, SEVERE #2 — frequency_hz=0 silently flatlined the sim."""

    def test_zero_frequency_rejected(self):
        from bridges.alternative_spice import AlternativeSPICE
        with self.assertRaises(ValueError):
            AlternativeSPICE(frequency_hz=0.0)

    def test_negative_frequency_rejected(self):
        from bridges.alternative_spice import AlternativeSPICE
        with self.assertRaises(ValueError):
            AlternativeSPICE(frequency_hz=-1.0)

    def test_zero_dt_rejected(self):
        from bridges.alternative_spice import AlternativeSPICE
        with self.assertRaises(ValueError):
            AlternativeSPICE(frequency_hz=60.0, dt=0.0)


class TestQueueCursorValidation(unittest.TestCase):
    """Audit 1, SEVERE #1 — corrupted cursor file used to silently
    re-pop already-sent items."""

    def _q(self, td: Path):
        from sensing.transmission.queue_manager import QueueManager
        return QueueManager(queue_path=td / "test.queue")

    def _push(self, q):
        from sensing.processing.primitives_encoder import build_primitive
        prim = build_primitive(
            concept_id="x", domain="measured_kinesthetic",
            role="direct_observation", couplings=(),
            bounds=("a", "b", "c"),
            readings=[SensorReading(
                timestamp_iso="2026-04-27T00:00:00+00:00",
                sensor_id="DS18B20.surface",
                values={"celsius": 12.5},
                is_mock=False,
            )],
            base_confidence_grades=[0.9],
        )
        q.push(prim)

    def test_corrupted_cursor_resets_to_zero(self):
        with tempfile.TemporaryDirectory() as td:
            q = self._q(Path(td))
            self._push(q)
            self._push(q)
            # Corrupt the cursor file with non-numeric content.
            cursor_path = Path(td) / "test.queue.cursor"
            cursor_path.write_text("garbage")
            # Should fall back to 0, not raise, and read everything.
            with self.assertLogs(level=logging.WARNING):
                pending = q.pending_count()
            self.assertEqual(pending, 2)

    def test_cursor_past_eof_clamps_to_size(self):
        with tempfile.TemporaryDirectory() as td:
            q = self._q(Path(td))
            self._push(q)
            cursor_path = Path(td) / "test.queue.cursor"
            cursor_path.write_text("999999999")
            with self.assertLogs(level=logging.WARNING):
                pending = q.pending_count()
            # Cursor clamped to file size → queue treated as empty.
            self.assertEqual(pending, 0)


# ===========================================================================
# AUDIT 2 — performance / scale
# ===========================================================================

class TestSpiceHistoryCap(unittest.TestCase):
    """Audit 2, MODERATE — history grew without bound when
    record_history=True."""

    def test_history_bounded(self):
        from bridges.alternative_spice import AlternativeSPICE
        sim = AlternativeSPICE(
            frequency_hz=60.0, record_history=True,
            max_history_per_node=5,
        )
        sim.add_node("n1", voltage=1.0, conductivity=5.96e7)
        for _ in range(50):
            sim.step()
        self.assertEqual(len(sim.state.history["n1"]), 5)


class TestAnomalyTrackerLRU(unittest.TestCase):
    """Audit 2, MODERATE — _baselines could grow unboundedly when
    sensor IDs varied (timestamps in names, mesh peers, etc.)."""

    def test_evicts_oldest_when_cap_exceeded(self):
        from sensing.processing.anomaly_detector import AnomalyTracker
        tr = AnomalyTracker(max_channels=3)
        for i in range(5):
            tr.evaluate(f"chan_{i}", 1.0)
        self.assertEqual(len(tr._baselines), 3)
        # The first two channels should have been evicted.
        self.assertNotIn("chan_0", tr._baselines)
        self.assertNotIn("chan_1", tr._baselines)
        self.assertIn("chan_4", tr._baselines)

    def test_re_evaluating_existing_channel_refreshes_recency(self):
        from sensing.processing.anomaly_detector import AnomalyTracker
        tr = AnomalyTracker(max_channels=2)
        tr.evaluate("a", 1.0)
        tr.evaluate("b", 1.0)
        tr.evaluate("a", 1.0)        # touch a → b is now LRU
        tr.evaluate("c", 1.0)        # b evicted, not a
        self.assertIn("a", tr._baselines)
        self.assertNotIn("b", tr._baselines)
        self.assertIn("c", tr._baselines)


class TestMicrophoneStorageManagement(unittest.TestCase):
    """Audit 2, SEVERE — mic captures filled the SD card after
    ~3.6 K reads with no cleanup."""

    def test_max_files_enforced(self):
        from sensing.firmware.sensor_drivers import MicrophoneDriver
        with tempfile.TemporaryDirectory() as td:
            mic = MicrophoneDriver(
                channel="ambient", out_dir=Path(td),
                mock=True, seed=1, max_files=3, max_age_hours=0,
            )
            for _ in range(8):
                mic.read()
            captures = list(Path(td).glob("ambient_*.wav"))
            self.assertLessEqual(len(captures), 3)

    def test_age_eviction_runs_on_read(self):
        from sensing.firmware.sensor_drivers import MicrophoneDriver
        with tempfile.TemporaryDirectory() as td:
            mic = MicrophoneDriver(
                channel="ambient", out_dir=Path(td),
                mock=True, seed=1,
                max_files=10, max_age_hours=1.0,
            )
            mic.read()
            # Backdate the file by 2 hours so it's older than the cap.
            old = next(Path(td).glob("*.wav"))
            two_hours_ago = (
                old.stat().st_mtime - 2 * 3600.0
            )
            import os
            os.utime(old, (two_hours_ago, two_hours_ago))

            mic.read()
            # Old file removed; new file remains.
            survivors = list(Path(td).glob("*.wav"))
            self.assertEqual(len(survivors), 1)
            self.assertNotEqual(survivors[0], old)


# ===========================================================================
# AUDIT 3 — security / data handling
# ===========================================================================

class TestMicrophoneChannelValidation(unittest.TestCase):
    """Audit 3, SEVERE 1.1 — channel names containing path separators
    used to write outside out_dir."""

    def _attempt(self, channel):
        from sensing.firmware.sensor_drivers import MicrophoneDriver
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                MicrophoneDriver(
                    channel=channel, out_dir=Path(td),
                    mock=True,
                )

    def test_rejects_path_traversal(self):
        self._attempt("../../etc/passwd")

    def test_rejects_slash(self):
        self._attempt("ambient/secret")

    def test_rejects_backslash(self):
        self._attempt("ambient\\secret")

    def test_rejects_null_byte(self):
        self._attempt("ambient\0evil")

    def test_rejects_empty(self):
        self._attempt("")

    def test_accepts_safe_characters(self):
        from sensing.firmware.sensor_drivers import MicrophoneDriver
        with tempfile.TemporaryDirectory() as td:
            # Should not raise:
            MicrophoneDriver(
                channel="ambient_north-east.1", out_dir=Path(td),
                mock=True,
            )


class TestObsLineSizeCap(unittest.TestCase):
    """Audit 3, MODERATE 2.2 — adversarial obs lines could allocate
    arbitrary memory at parse time."""

    def test_oversized_line_is_rejected(self):
        # Build a line whose ``form`` field alone exceeds the cap.
        oversized_form = "x" * (MAX_OBS_LINE_BYTES + 1)
        line = "\t".join([
            "concept", "domain", oversized_form, "role",
            "couplings", "a,b,c", "measured", "0.500",
            "2026-04-27T00:00:00+00:00", "-",
        ])
        with self.assertRaises(ValueError):
            obs_line_to_primitive(line)


class TestClaimsBinaryFileSizeCap(unittest.TestCase):
    """Audit 3, MODERATE 2.3 — read_claims_binary used to load any
    file size into memory."""

    def test_oversize_file_is_rejected(self):
        import CLAIM_SCHEMA as cs
        with tempfile.TemporaryDirectory() as td:
            big = Path(td) / "huge.claims.bin"
            # 100 KB > a 32-byte cap.
            big.write_bytes(b"\x00" * (100 * 1024))
            table = {f: [] for f in cs.TABLE_FIELDS}
            with self.assertRaises(ValueError):
                cs.read_claims_binary(big, table, max_bytes=32)


class TestHamCallsignEnforcement(unittest.TestCase):
    """Audit 3, MODERATE 5.1 — NOCALL placeholder accepted in no-op
    log path used to leak the placeholder into logs."""

    def test_nocall_rejected_unconditionally(self):
        from sensing.transmission.ham_kiss_wrapper import HamKissTransmitter
        for callsign in ("NOCALL", "nocall", "NoCall", ""):
            with self.assertRaises(ValueError):
                HamKissTransmitter(callsign=callsign)

    def test_real_callsign_accepted(self):
        from sensing.transmission.ham_kiss_wrapper import HamKissTransmitter
        # No raise:
        tx = HamKissTransmitter(callsign="K0AAA")
        self.assertEqual(tx.callsign, "K0AAA")


class TestLogPayloadScrubbing(unittest.TestCase):
    """Audit 3, MODERATE 4.x — LoRa / HAM no-op logs used to echo the
    payload prefix, leaking timestamp + location."""

    def test_lora_noop_log_contains_only_byte_count(self):
        from sensing.processing.primitives_encoder import build_primitive
        from sensing.transmission.lora_transmit import LoRaTransmitter

        prim = build_primitive(
            concept_id="secret_location_id",
            domain="measured_kinesthetic",
            role="direct_observation",
            couplings=(),
            bounds=("Superior_MN", "2026_April", "0-30cm"),
            readings=[SensorReading(
                timestamp_iso="2026-04-27T00:00:00+00:00",
                sensor_id="DS18B20.surface",
                values={"celsius": 12.5},
                is_mock=False,
            )],
            base_confidence_grades=[0.9],
        )
        tx = LoRaTransmitter(send_bytes=None)
        with self.assertLogs(level=logging.INFO) as caught:
            tx(prim)
        joined = "\n".join(caught.output)
        # Sensitive content must NOT appear in the log.
        self.assertNotIn("secret_location_id", joined)
        self.assertNotIn("Superior_MN", joined)
        self.assertNotIn("2026-04-27", joined)
        # The byte count IS allowed.
        self.assertIn("would send", joined)


if __name__ == "__main__":
    unittest.main()
