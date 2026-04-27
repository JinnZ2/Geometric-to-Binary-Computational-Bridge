"""
test_transmission — queue manager + LoRa stub + HAM KISS + CB script.

Coverage:

* Queue persists across instances and survives a process restart.
* Cursor advances on pop, preserves on peek.
* compact() actually shrinks the file.
* LoRa stub returns False without a send_bytes callable.
* LoRa chunking splits oversized payloads correctly.
* KISS encode/decode round-trip.
* HamKissTransmitter rejects callsign='NOCALL' once a real
  ``write_kiss`` is wired up.
* format_for_cb_relay produces a string with the callsign + concept
  + values + confidence + 'OUT' on it.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sensing.firmware.sensor_drivers.base import SensorReading
from sensing.processing.primitives_encoder import build_primitive
from sensing.transmission import (
    HamKissTransmitter,
    LoRaTransmitter,
    QueueManager,
    format_for_cb_relay,
)
from sensing.transmission.ham_kiss_wrapper import (
    FEND,
    kiss_decode,
    kiss_encode,
)


def _primitive(claim_ref="fourier_heat"):
    return build_primitive(
        concept_id="soil_regime",
        domain="measured_kinesthetic",
        role="direct_observation",
        couplings=("temperature", "moisture"),
        bounds=("Superior_MN", "2026_ongoing", "0-50cm"),
        readings=[SensorReading(
            timestamp_iso="2026-04-27T00:00:00+00:00",
            sensor_id="DS18B20.surface",
            values={"celsius": 12.5},
            is_mock=False,
        )],
        base_confidence_grades=[0.95],
        claim_ref=claim_ref,
    )


# ---------------------------------------------------------------------------
# QueueManager
# ---------------------------------------------------------------------------

class TestQueueManager(unittest.TestCase):

    def test_push_pending_pop_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            q = QueueManager(queue_path=Path(td) / "node.obs.queue")
            self.assertEqual(q.pending_count(), 0)
            for _ in range(3):
                q.push(_primitive())
            self.assertEqual(q.pending_count(), 3)

            popped = q.pop_batch(max_items=2)
            self.assertEqual(len(popped), 2)
            self.assertEqual(q.pending_count(), 1)

    def test_peek_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td:
            q = QueueManager(queue_path=Path(td) / "node.obs.queue")
            q.push(_primitive())
            q.push(_primitive())
            peeked = q.peek(2)
            self.assertEqual(len(peeked), 2)
            self.assertEqual(q.pending_count(), 2)

    def test_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "node.obs.queue"
            q1 = QueueManager(queue_path=path)
            q1.push(_primitive())
            q1.push(_primitive())

            # New instance picks up the same state.
            q2 = QueueManager(queue_path=path)
            self.assertEqual(q2.pending_count(), 2)
            popped = q2.pop_batch(max_items=10)
            self.assertEqual(len(popped), 2)

            # And the cursor change persists too.
            q3 = QueueManager(queue_path=path)
            self.assertEqual(q3.pending_count(), 0)

    def test_compact_reclaims_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "node.obs.queue"
            q = QueueManager(queue_path=path)
            for _ in range(5):
                q.push(_primitive())
            q.pop_batch(max_items=4)
            size_before = path.stat().st_size
            self.assertGreater(q.compact(), 0)
            self.assertLess(path.stat().st_size, size_before)
            self.assertEqual(q.pending_count(), 1)  # one survivor


# ---------------------------------------------------------------------------
# LoRa stub
# ---------------------------------------------------------------------------

class TestLoRaTransmitter(unittest.TestCase):

    def test_no_op_returns_false(self):
        tx = LoRaTransmitter(send_bytes=None)
        self.assertFalse(tx(_primitive()))

    def test_real_send_returns_true(self):
        sent = []
        def send(payload: bytes) -> bool:
            sent.append(payload)
            return True
        tx = LoRaTransmitter(send_bytes=send, max_payload_bytes=4096)
        self.assertTrue(tx(_primitive()))
        self.assertEqual(len(sent), 1)
        self.assertIn(b"soil_regime", sent[0])

    def test_chunking_oversized_payload(self):
        sent = []
        def send(payload: bytes) -> bool:
            sent.append(payload)
            return True
        # Force tiny max so the Primitive splits.
        tx = LoRaTransmitter(send_bytes=send, max_payload_bytes=32)
        self.assertTrue(tx(_primitive()))
        self.assertGreater(len(sent), 1)
        # Last chunk has the END marker; earlier chunks have MORE.
        self.assertTrue(sent[-1].startswith(b"END\x1f"))
        for chunk in sent[:-1]:
            self.assertTrue(chunk.startswith(b"MORE\x1f"))


# ---------------------------------------------------------------------------
# HAM KISS
# ---------------------------------------------------------------------------

class TestHamKiss(unittest.TestCase):

    def test_kiss_encode_decode_round_trip(self):
        for body in [b"hello", b"with FEND \xc0 inside",
                     b"with FESC \xdb inside", b""]:
            frame = kiss_encode(body)
            self.assertEqual(frame[0], FEND)
            self.assertEqual(frame[-1], FEND)
            self.assertEqual(kiss_decode(frame), body)

    def test_no_op_without_writer(self):
        tx = HamKissTransmitter(callsign="NOCALL", write_kiss=None)
        self.assertFalse(tx(_primitive()))

    def test_rejects_real_writer_without_callsign(self):
        with self.assertRaises(ValueError):
            HamKissTransmitter(callsign="NOCALL", write_kiss=lambda b: True)

    def test_real_writer_returns_true(self):
        sent = []
        def writer(frame: bytes) -> bool:
            sent.append(frame)
            return True
        tx = HamKissTransmitter(callsign="K0AAA", write_kiss=writer)
        self.assertTrue(tx(_primitive()))
        self.assertEqual(len(sent), 1)
        # Decoded payload starts with the callsign prefix.
        decoded = kiss_decode(sent[0])
        self.assertTrue(decoded.startswith(b"K0AAA > "))


# ---------------------------------------------------------------------------
# CB relay
# ---------------------------------------------------------------------------

class TestCBRelayFormat(unittest.TestCase):

    def test_script_contains_callsign_and_concept(self):
        script = format_for_cb_relay(_primitive(), callsign="KV")
        self.assertIn("KV", script)
        self.assertIn("SOIL REGIME", script)
        self.assertIn("CONFIDENCE", script)
        self.assertIn("OUT", script)

    def test_values_phrase_uses_form_when_readings_absent(self):
        # Simulate a Primitive that came back from disk (no in-memory
        # readings). The CB script must still recover values from
        # primitive.form.
        p = _primitive()
        p.readings.clear()
        script = format_for_cb_relay(p, callsign="KV")
        self.assertNotIn("NO VALUES", script)


if __name__ == "__main__":
    unittest.main()
