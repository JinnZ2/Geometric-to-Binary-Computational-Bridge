"""
tests/test_claim_schema.py
==========================

Covers ``CLAIM_SCHEMA.py``, the per-repo claim-encoding artifacts
(``CLAIM_TABLE.json``, ``.claims``, ``.claims.bin``), and the
``scripts/build_claims.py`` build pipeline.

What is tested:
* Codec round-trip on synthetic claims (line ↔ dict, dict ↔ binary).
* Sentinel handling (empty vs populated multi-valued fields).
* Forbidden-separator validation in ``claim_to_line``.
* The shipped artifacts at the repo root parse cleanly and stay in
  sync with each other.
* Re-running the build script is idempotent (output bytes don't
  drift on a clean re-run).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import CLAIM_SCHEMA as cs


# ---------------------------------------------------------------------------
# Codec contract
# ---------------------------------------------------------------------------

class TestCodec(unittest.TestCase):

    def _claim(self, **overrides):
        base = {
            "id":     "demo_a",
            "rate":   "dX/dt=k*X",
            "bounds": "lab,steady,1m",
            "cond":   ["k_positive", "X_bounded"],
            "rel":    ["other_demo"],
            "fail":   ["k_negative"],
            "meas":   ["scope"],
            "cyc":    0,
        }
        base.update(overrides)
        return base

    def test_line_round_trip(self):
        c = self._claim()
        self.assertEqual(cs.line_to_claim(cs.claim_to_line(c)), c)

    def test_line_rejects_pipe_in_value(self):
        with self.assertRaises(ValueError):
            cs.claim_to_line(self._claim(rate="dI/dt|I=0=ω"))

    def test_line_rejects_comma_in_multi_field(self):
        with self.assertRaises(ValueError):
            cs.claim_to_line(self._claim(cond=["a,b"]))

    def test_line_rejects_newline(self):
        with self.assertRaises(ValueError):
            cs.claim_to_line(self._claim(rate="dX/dt\n=0"))

    def test_binary_round_trip(self):
        claims = [
            self._claim(),
            self._claim(id="demo_b", rate="dY/dt=alpha*Y", cond=["Y_pos"], cyc=2),
        ]
        table = cs.build_table(claims)
        ids = cs.id_lookup_from_claims(claims)
        for c in claims:
            blob = cs.encode_claim(c, table)
            self.assertEqual(len(blob), cs.BIN_CLAIM_BYTES)
            decoded = cs.decode_claim(blob, table, id_lookup=ids)
            # Multi-valued fields come back sorted by table-index;
            # accept that ordering.
            decoded_sorted = {
                k: sorted(v, key=lambda x, _t=table.get(_TABLE_OF.get(k), [None]): _t.index(x) if x in _t else 0)
                if k in {"cond", "rel", "fail", "meas"} and isinstance(v, list)
                else v
                for k, v in decoded.items()
            }
            # Just verify set-equality on multi-fields.
            for f in ("cond", "rel", "fail", "meas"):
                self.assertEqual(set(decoded[f]), set(c[f]))
            for f in ("id", "rate", "bounds", "cyc"):
                self.assertEqual(decoded[f], c[f])

    def test_bin_size_matches_constant(self):
        self.assertEqual(cs.BIN_CLAIM_BYTES, 41)

    def test_mask_cap_enforced(self):
        # Synthesise a table with too many entries and verify the
        # encoder refuses rather than silently truncating.
        too_many = [f"v{i}" for i in range(cs.MASK_BITS + 1)]
        c = self._claim(cond=too_many[:cs.MASK_BITS + 1])
        table = cs.build_table([c])
        with self.assertRaises(ValueError):
            cs.encode_claim(c, table)

    def test_no_index_sentinel_on_empty_rate(self):
        # Empty rate / bounds round-trip via NO_INDEX.
        c = self._claim(rate="", bounds="")
        table = cs.build_table([c])
        blob = cs.encode_claim(c, table)
        decoded = cs.decode_claim(blob, table)
        self.assertEqual(decoded["rate"], "")
        self.assertEqual(decoded["bounds"], "")


_TABLE_OF = {
    "cond": "cond", "rel": "rel", "fail": "fail", "meas": "meas",
}


# ---------------------------------------------------------------------------
# Shipped artifacts
# ---------------------------------------------------------------------------

class TestRepoArtifacts(unittest.TestCase):
    """Verify the artifacts at the repo root are self-consistent."""

    @classmethod
    def setUpClass(cls):
        cls.table_path  = REPO_ROOT / "CLAIM_TABLE.json"
        cls.claims_path = REPO_ROOT / ".claims"
        cls.binary_path = REPO_ROOT / ".claims.bin"

    def test_artifacts_exist(self):
        self.assertTrue(self.table_path.exists(),
                        f"missing {self.table_path}")
        self.assertTrue(self.claims_path.exists(),
                        f"missing {self.claims_path}")
        self.assertTrue(self.binary_path.exists(),
                        f"missing {self.binary_path}")

    def test_table_has_required_fields(self):
        table = cs.read_table(self.table_path)
        for f in cs.TABLE_FIELDS:
            self.assertIn(f, table)
            self.assertIsInstance(table[f], list)

    def test_line_and_binary_agree(self):
        table = cs.read_table(self.table_path)
        text_claims = cs.read_claims(self.claims_path)
        ids = cs.id_lookup_from_claims(text_claims)
        bin_claims = cs.read_claims_binary(
            self.binary_path, table, id_lookup=ids,
        )
        self.assertEqual(text_claims, bin_claims)

    def test_binary_size_matches_count(self):
        text_claims = cs.read_claims(self.claims_path)
        expected = len(text_claims) * cs.BIN_CLAIM_BYTES
        self.assertEqual(self.binary_path.stat().st_size, expected)

    def test_table_within_mask_cap(self):
        table = cs.read_table(self.table_path)
        for field in ("cond", "rel", "fail", "meas"):
            self.assertLessEqual(
                len(table[field]), cs.MASK_BITS,
                f"CLAIM_TABLE[{field!r}] = {len(table[field])} entries "
                f"exceeds MASK_BITS={cs.MASK_BITS}",
            )

    def test_every_claim_has_required_fields(self):
        for claim in cs.read_claims(self.claims_path):
            for f in cs.LINE_FIELDS:
                self.assertIn(f, claim, f"{claim['id']} missing {f}")
            self.assertIn(claim["cyc"], cs.CYCLE_ENUM)

    def test_rate_field_is_a_derivative(self):
        # The schema rule: every rate must contain "/d" — i.e. it is a
        # derivative expression. "Never collapse to noun-identity."
        for claim in cs.read_claims(self.claims_path):
            rate = claim["rate"]
            self.assertIn(
                "/d", rate,
                f"{claim['id']} rate {rate!r} is not a differential form",
            )


# ---------------------------------------------------------------------------
# Build pipeline idempotency
# ---------------------------------------------------------------------------

class TestBuildScript(unittest.TestCase):

    def test_rerun_is_idempotent(self):
        # Snapshot, re-run, compare bytes.
        before_table   = (REPO_ROOT / "CLAIM_TABLE.json").read_bytes()
        before_claims  = (REPO_ROOT / ".claims").read_bytes()
        before_binary  = (REPO_ROOT / ".claims.bin").read_bytes()

        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import build_claims
            build_claims.build()
        finally:
            sys.path.pop(0)

        self.assertEqual(
            before_table, (REPO_ROOT / "CLAIM_TABLE.json").read_bytes(),
        )
        self.assertEqual(
            before_claims, (REPO_ROOT / ".claims").read_bytes(),
        )
        self.assertEqual(
            before_binary, (REPO_ROOT / ".claims.bin").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
