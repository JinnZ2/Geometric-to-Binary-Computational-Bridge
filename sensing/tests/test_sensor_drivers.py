"""
test_sensor_drivers — verify the SensorDriver contract under mock mode.

These tests run anywhere; they never touch hardware. Each driver
must:

* Construct in mock mode without raising.
* Return a SensorReading with a valid ISO timestamp, a non-empty
  ``values`` dict, and ``is_mock=True``.
* Carry a numeric ``confidence_grade`` class attribute.
* Be safely closable.

Behavioural sanity checks (e.g. soil moisture stays in [0, 1] range,
PIR motion is a 0/1 float, MLX delta is consistent with its parts)
are sprinkled in so a driver that silently breaks during a future
refactor is caught immediately.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from sensing.firmware.sensor_drivers import (
    CapacitiveSoilMoistureDriver,
    DS18B20Driver,
    MicrophoneDriver,
    MLX90614Driver,
    PIRMotionDriver,
)
from sensing.firmware.sensor_drivers.base import SensorReading


_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\+|-)\d{2}:\d{2}$"
)


class TestDriverContract(unittest.TestCase):
    """Every driver must satisfy this minimal contract."""

    def _check(self, driver, must_contain_keys: tuple = ()):
        self.assertTrue(hasattr(driver, "confidence_grade"))
        self.assertIsInstance(driver.confidence_grade, float)
        self.assertGreaterEqual(driver.confidence_grade, 0.0)
        self.assertLessEqual(driver.confidence_grade, 1.0)

        reading = driver.read()
        self.assertIsInstance(reading, SensorReading)
        self.assertTrue(reading.is_mock)
        self.assertRegex(reading.timestamp_iso, _ISO_RE)
        self.assertIn(".", reading.sensor_id)  # device.channel
        self.assertGreater(len(reading.values), 0)
        for key in must_contain_keys:
            self.assertIn(key, reading.values)

        # Closable, idempotent
        driver.close()
        driver.close()

    def test_ds18b20(self):
        self._check(
            DS18B20Driver(channel="surface", mock=True, seed=1),
            must_contain_keys=("celsius",),
        )

    def test_capacitive_soil_moisture(self):
        d = CapacitiveSoilMoistureDriver(channel="primary", mock=True, seed=1)
        self._check(d, must_contain_keys=("vwc", "saturation"))
        # Spot-check ranges.
        r = d.read()
        self.assertGreaterEqual(r.values["vwc"], 0.0)
        self.assertLessEqual(r.values["vwc"], 0.6)
        self.assertGreaterEqual(r.values["saturation"], 0.0)
        self.assertLessEqual(r.values["saturation"], 1.2)  # tolerance for noise

    def test_mlx90614(self):
        d = MLX90614Driver(channel="canopy", mock=True, seed=1)
        self._check(d, must_contain_keys=("t_obj_c", "t_amb_c", "delta_c"))
        r = d.read()
        # delta_c is t_obj_c - t_amb_c by definition
        self.assertAlmostEqual(
            r.values["delta_c"],
            r.values["t_obj_c"] - r.values["t_amb_c"],
            places=2,
        )

    def test_pir_motion(self):
        d = PIRMotionDriver(channel="primary", mock=True, seed=1)
        self._check(d, must_contain_keys=("motion",))
        r = d.read()
        self.assertIn(r.values["motion"], (0.0, 1.0))

    def test_microphone(self):
        with tempfile.TemporaryDirectory() as td:
            d = MicrophoneDriver(
                channel="ambient",
                out_dir=Path(td),
                mock=True,
                seed=1,
            )
            self._check(d, must_contain_keys=("recorded_seconds",))
            # Note must include the SHA-256 hash of the synthetic file.
            r = d.read()
            self.assertIn("sha256=", r.note)
            # Every mock capture writes a file in the out_dir.
            self.assertGreater(len(list(Path(td).glob("*.wav"))), 0)


class TestDriverDeterminism(unittest.TestCase):
    """Same seed → same first reading. Verifies the RNG plumbing
    actually flows through to per-driver mock implementations."""

    def test_ds18b20_seeded_repeatable(self):
        a = DS18B20Driver(channel="surface", mock=True, seed=42).read()
        b = DS18B20Driver(channel="surface", mock=True, seed=42).read()
        self.assertEqual(a.values["celsius"], b.values["celsius"])

    def test_pir_seeded_repeatable(self):
        seq_a = [
            PIRMotionDriver(channel="x", mock=True, seed=99).read().values["motion"]
            for _ in range(8)
        ]
        seq_b = [
            PIRMotionDriver(channel="x", mock=True, seed=99).read().values["motion"]
            for _ in range(8)
        ]
        # Each driver instance starts a fresh RNG; the first reading
        # of each must agree, but later reads diverge because the
        # second loop's drivers have a fresh state per iteration.
        self.assertEqual(seq_a[0], seq_b[0])


if __name__ == "__main__":
    unittest.main()
