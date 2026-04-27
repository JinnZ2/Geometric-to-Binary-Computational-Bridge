"""
test_local_logger — orchestration + scheduler integration.

Verifies that a LocalLogger built from real driver instances (in
mock mode) produces well-formed Primitives, persists them to disk,
hands them to the transmitter, and increments stats correctly. Also
exercises the Scheduler's ``next_tick`` / ``run_forever`` paths
without sleeping.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sensing.firmware.local_logger import LocalLogger, PrimitiveRecipe
from sensing.firmware.sensor_drivers import (
    CapacitiveSoilMoistureDriver,
    DS18B20Driver,
)
from sensing.firmware.sleep_wake_scheduler import Scheduler
from sensing.processing.primitives_encoder import read_obs


def _build(td: Path, transmit=None):
    drivers = [
        DS18B20Driver(channel="surface", mock=True, seed=1),
        CapacitiveSoilMoistureDriver(channel="primary", mock=True, seed=1),
    ]
    recipe = PrimitiveRecipe(
        concept_id="soil_regime",
        couplings=("temperature", "moisture"),
        bounds=("Superior_MN", "2026_ongoing", "0-50cm"),
        claim_ref="fourier_heat",
    )
    return LocalLogger(
        drivers=drivers,
        recipe=recipe,
        obs_path=td / "node.obs",
        transmit=transmit,
    )


class TestLocalLogger(unittest.TestCase):

    def test_tick_emits_one_primitive(self):
        with tempfile.TemporaryDirectory() as td:
            logger = _build(Path(td))
            p = logger.tick(0)
            self.assertEqual(p.concept_id, "soil_regime")
            self.assertEqual(p.claim_ref, "fourier_heat")
            self.assertEqual(logger.stats()["primitives_emitted"], 1)
            on_disk = read_obs(Path(td) / "node.obs")
            self.assertEqual(len(on_disk), 1)

    def test_transmit_called_per_tick(self):
        sent = []
        with tempfile.TemporaryDirectory() as td:
            logger = _build(Path(td), transmit=lambda p: sent.append(p) or True)
            for i in range(3):
                logger.tick(i)
            self.assertEqual(len(sent), 3)
            self.assertEqual(logger.stats()["transmissions_queued"], 0)

    def test_failed_transmit_increments_queued_counter(self):
        with tempfile.TemporaryDirectory() as td:
            logger = _build(Path(td), transmit=lambda p: False)
            logger.tick(0)
            logger.tick(1)
            self.assertEqual(logger.stats()["transmissions_queued"], 2)

    def test_close_is_safe_to_call_repeatedly(self):
        with tempfile.TemporaryDirectory() as td:
            logger = _build(Path(td))
            logger.close()
            logger.close()


class TestScheduler(unittest.TestCase):

    def test_next_tick_runs_callback_once(self):
        ticks_seen = []
        sched = Scheduler(interval_seconds=0.0, minimum_sleep=0.0)
        sched.next_tick(
            lambda n: ticks_seen.append(n),
            sleep_fn=lambda _s: None,
            clock=lambda: 0.0,
        )
        self.assertEqual(ticks_seen, [0])
        self.assertEqual(sched.ticks, 1)

    def test_run_forever_with_max_ticks(self):
        ticks_seen = []
        sched = Scheduler(interval_seconds=0.0, minimum_sleep=0.0)
        completed = sched.run_forever(
            lambda n: ticks_seen.append(n),
            max_ticks=4,
            sleep_fn=lambda _s: None,
            clock=lambda: 0.0,
        )
        self.assertEqual(completed, 4)
        self.assertEqual(ticks_seen, [0, 1, 2, 3])

    def test_callback_exception_does_not_abort_loop(self):
        from collections import Counter
        attempts = Counter()
        def cb(n):
            attempts[n] += 1
            if n == 1:
                raise RuntimeError("boom")
        sched = Scheduler(interval_seconds=0.0, minimum_sleep=0.0)
        sched.run_forever(
            cb, max_ticks=4,
            sleep_fn=lambda _s: None,
            clock=lambda: 0.0,
        )
        # Each tick attempted exactly once even though tick 1 raised.
        self.assertEqual(dict(attempts), {0: 1, 1: 1, 2: 1, 3: 1})


if __name__ == "__main__":
    unittest.main()
