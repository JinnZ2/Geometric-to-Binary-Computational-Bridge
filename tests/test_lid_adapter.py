"""Tests for bridges/lid_adapter.py"""

import unittest
import importlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bridges.lid_adapter import (
    LIDAdapter,
    ENTITY_ENCODER_MAP,
    CATEGORY_BRIDGE_MAP,
)


class TestLIDAdapterInstantiation(unittest.TestCase):
    def test_create_without_lid_path(self):
        adapter = LIDAdapter()
        self.assertIsInstance(adapter, LIDAdapter)

    def test_create_with_nonexistent_path(self):
        adapter = LIDAdapter("/tmp/nonexistent_lid_path_xyz")
        self.assertIsInstance(adapter, LIDAdapter)
        self.assertFalse(adapter._lid_available)

    def test_load_index_without_lid(self):
        adapter = LIDAdapter("/tmp/nonexistent_lid_path_xyz")
        index = adapter.load_index()
        self.assertIsInstance(index, dict)
        self.assertEqual(index.get("entities"), [])

    def test_load_entity_without_lid(self):
        adapter = LIDAdapter("/tmp/nonexistent_lid_path_xyz")
        self.assertIsNone(adapter.load_entity("MAG_BRIDGE"))

    def test_summary_returns_string(self):
        adapter = LIDAdapter()
        s = adapter.summary()
        self.assertIsInstance(s, str)
        self.assertIn("LID available", s)


class TestClassifyToBridge(unittest.TestCase):
    def setUp(self):
        self.adapter = LIDAdapter()

    def test_magnetic_text(self):
        result = self.adapter.classify_to_bridge("magnetic field resonance at 40T")
        self.assertEqual(result, "magnetic")

    def test_quantum_text(self):
        result = self.adapter.classify_to_bridge("quantum wave function collapse")
        self.assertEqual(result, "wave")

    def test_light_text(self):
        result = self.adapter.classify_to_bridge("photon wavelength spectrum")
        self.assertEqual(result, "light")

    def test_sound_text(self):
        result = self.adapter.classify_to_bridge("acoustic pitch resonance")
        self.assertEqual(result, "sound")

    def test_gravity_text(self):
        result = self.adapter.classify_to_bridge("gravitational orbit curvature")
        self.assertEqual(result, "gravity")

    def test_electric_text(self):
        result = self.adapter.classify_to_bridge("electric charge voltage")
        self.assertEqual(result, "electric")

    def test_thermal_text(self):
        result = self.adapter.classify_to_bridge("thermal temperature heat")
        self.assertEqual(result, "thermal")

    def test_chemical_text(self):
        result = self.adapter.classify_to_bridge("chemical reaction molecule bond")
        self.assertEqual(result, "chemical")

    def test_consciousness_text(self):
        result = self.adapter.classify_to_bridge("consciousness awareness entropy")
        self.assertEqual(result, "consciousness")

    def test_emotion_text(self):
        result = self.adapter.classify_to_bridge("emotion affect pleasure arousal")
        self.assertEqual(result, "emotion")

    def test_no_match_returns_none(self):
        result = self.adapter.classify_to_bridge("absolutely nothing relevant here")
        self.assertIsNone(result)


class TestEncodersForCategory(unittest.TestCase):
    def setUp(self):
        self.adapter = LIDAdapter()

    def test_energy_category(self):
        result = self.adapter.encoders_for_category("energy")
        self.assertIsInstance(result, list)
        self.assertIn("magnetic", result)
        self.assertIn("electric", result)

    def test_plasma_category(self):
        result = self.adapter.encoders_for_category("plasma")
        self.assertIn("electric", result)
        self.assertIn("wave", result)
        self.assertIn("thermal", result)

    def test_animal_category(self):
        result = self.adapter.encoders_for_category("animal")
        self.assertIn("sound", result)
        self.assertIn("consciousness", result)

    def test_unknown_category(self):
        result = self.adapter.encoders_for_category("nonexistent")
        self.assertEqual(result, [])


class TestEntityEncoderMap(unittest.TestCase):
    def test_all_entries_importable(self):
        for entity_id, (module_path, class_name) in ENTITY_ENCODER_MAP.items():
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name, None)
            self.assertIsNotNone(
                cls, f"{class_name} not found in {module_path} (entity {entity_id})"
            )

    def test_encoder_for_known_entity(self):
        adapter = LIDAdapter()
        encoder = adapter.encoder_for("MAG_BRIDGE")
        self.assertIsNotNone(encoder)

    def test_encoder_for_unknown_entity(self):
        adapter = LIDAdapter()
        self.assertIsNone(adapter.encoder_for("DOES_NOT_EXIST"))


class TestCrossValidateCouplings(unittest.TestCase):
    def test_returns_well_formed_report(self):
        adapter = LIDAdapter()
        report = adapter.cross_validate_couplings()
        self.assertIsInstance(report, dict)
        self.assertIn("status", report)
        self.assertIn("comparisons", report)
        self.assertIsInstance(report["comparisons"], list)


if __name__ == "__main__":
    unittest.main()
