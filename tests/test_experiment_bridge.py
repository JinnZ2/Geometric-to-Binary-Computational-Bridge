"""Experiment bridge: preservation checks, not model or physics validation.

Run from repository root: python tests/test_experiment_bridge.py
Only the standard library is used. Original snippets are not imported here.
"""

import hashlib
import json
from pathlib import Path
import re
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "experiments" / "experiment_bridge"


class TestExperimentBridgePreservation(unittest.TestCase):
    def test_received_files_match_manifest(self):
        manifest = json.loads((BENCH / "raw" / "manifest.json").read_text())
        self.assertEqual(len(manifest["files"]), 3)
        for item in manifest["files"]:
            with self.subTest(path=item["path"]):
                payload = (BENCH / item["path"]).read_bytes()
                self.assertEqual(len(payload), item["bytes"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])

    def test_corrupted_payload_fails_its_hash(self):
        manifest = json.loads((BENCH / "raw" / "manifest.json").read_text())
        item = manifest["files"][0]
        payload = (BENCH / item["path"]).read_bytes() + b"changed"
        self.assertNotEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])

    def test_python_specimens_are_exact_fence_extractions(self):
        notes = (BENCH / "raw" / "working_notes.txt").read_text()
        blocks = re.findall(r"```python\n(.*?)```", notes, re.S)
        names = ["generate_copybook_as_received.py", "ncm_bridge_as_received.py",
                 "ncm_level_walk_as_received.py"]
        self.assertEqual(len(blocks), len(names))
        for name, block in zip(names, blocks):
            with self.subTest(name=name):
                self.assertEqual((BENCH / "evidence" / name).read_text(), block)

    def test_kimi_extractions_match_archive_bytes(self):
        manifest = json.loads((BENCH / "raw" / "manifest.json").read_text())
        with ZipFile(BENCH / "raw" / "kimi_notes.zip") as archive:
            for item in manifest["kimi_archive_members"]:
                with self.subTest(member=item["archive_member"]):
                    payload = archive.read(item["archive_member"])
                    self.assertEqual((BENCH / item["extracted_path"]).read_bytes(), payload)
                    self.assertEqual(len(payload), item["bytes"])
                    self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])

    def test_semantic_instances_match_without_replacing_either(self):
        supplied = json.loads((BENCH / "raw" / "lojban_wordslot_reference.json").read_text())
        kimi = json.loads((BENCH / "evidence" / "kimi_as_received" /
                           "lojban_wordslot_reference.json").read_text())
        self.assertEqual(supplied, kimi)
        self.assertEqual(len(supplied["place_structures"]), 30)
        self.assertEqual(len(supplied["evidentials"]), 11)

    def test_distinct_contexts_for_repeated_identifiers_are_preserved(self):
        supplied = json.loads((BENCH / "raw" / "lojban_wordslot_reference.json").read_text())
        snura = [row for row in supplied["place_structures"] if row["gismu"] == "snura"]
        self.assertEqual(len(snura), 2)
        self.assertEqual({row["class"] for row in snura}, {"fear", "recall_check"})
        self.assertEqual({row["mapping_status"] for row in snura}, {"PROPOSED", "DIFFERS"})

    def test_declared_gaps_are_not_filled(self):
        supplied = json.loads((BENCH / "raw" / "lojban_wordslot_reference.json").read_text())
        gaps = [row for row in supplied["place_structures"] if row["mapping_status"] == "VOID"]
        self.assertEqual({row["english"] for row in gaps}, {"efficient", "cold", "imminent"})
        for row in gaps:
            self.assertIsNone(row["gismu"])
            self.assertIsNone(row["place_structure_verbatim"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
