"""
tests/test_intersection_rules.py
=================================

Covers the intersection layer:

  * BasinSignature / CoupledSignature value-object contracts
  * RESONATE pair and many
  * GravityIntersectionRule (wires into gravity_alternative_compute)
  * ElectricIntersectionRule (wires into electric_alternative_compute)
  * SoundIntersectionRule (wires into sound_alternative_compute)
  * CommunityIntersectionRule (wires into community_alternative_compute)
  * Registry lookup + override
"""

from __future__ import annotations

import unittest

from bridges.intersection import (
    BasinSignature,
    CoupledSignature,
    DOMAIN_RULES,
    IntersectionRule,
    get_rule,
    register_rule,
    registered_domains,
    resonate,
    resonate_many,
)
from bridges.intersection.electric_rule import ElectricIntersectionRule
from bridges.intersection.community_rule import CommunityIntersectionRule
from bridges.intersection.gravity_rule import GravityIntersectionRule
from bridges.intersection.sound_rule import SoundIntersectionRule
from bridges.probability_collapse import DistributionRegime


# ---------------------------------------------------------------------------
# Canonical geometries used by multiple test classes
# ---------------------------------------------------------------------------

GRAVITY_GEOM_ATTRACT = {
    "vectors": [
        [0.0, -9.8, 0.0],
        [0.0, -9.8, 0.0],
        [0.0, -9.8, 0.0],
        [0.0, -9.8, 0.0],
    ],
}

GRAVITY_GEOM_LAGRANGE = {
    "vectors": [
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
    ],
}

ELECTRIC_GEOM_AC = {
    "charge": [1e-6, -1e-6, 1e-6, -1e-6],
    "current_A": [0.5, -0.5, 0.5, -0.5, 0.0, 0.5, -0.5],
    "voltage_V": [12.0, 0.5, 230.0, 0.99],
    "conductivity_S": [5.96e7, 1e-8],
    "frequency_hz": 60.0,
}

ELECTRIC_GEOM_DC = {
    "charge": [1e-6, 1e-6, 1e-6, 1e-6],
    "current_A": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    "voltage_V": [12.0, 12.0, 12.0, 12.0],
    "conductivity_S": [5.96e7, 5.96e7],
}

SOUND_GEOM = {
    "phase_radians": [0.1, 1.5, 3.1, 4.5, 6.0, 0.2, 1.4],
    "frequency_hz":  [440.0] * 7,
    "amplitude":     [0.5, 0.3, 0.4, 0.2, 0.3, 0.5, 0.3],
}

COMMUNITY_GEOM = {
    "population": 5000,
    "farms_ha": 200,
    "gardens_ha": 50,
    "cold_storage_tons": 50,
    "local_food_fraction": 0.6,
}


# ---------------------------------------------------------------------------
# BasinSignature / CoupledSignature contracts
# ---------------------------------------------------------------------------

class TestBasinSignature(unittest.TestCase):

    def test_construct_valid(self):
        sig = BasinSignature(
            domain="test",
            regime=DistributionRegime.FOCUSED,
            vector=(1.0, 0.0, 0.0),
            confidence=0.8,
            scalar_strength=2.5,
        )
        self.assertEqual(sig.domain, "test")
        self.assertAlmostEqual(sig.vector_magnitude, 1.0)

    def test_rejects_out_of_range_confidence(self):
        with self.assertRaises(ValueError):
            BasinSignature(
                domain="test",
                regime=DistributionRegime.FOCUSED,
                vector=(1.0,),
                confidence=1.5,
            )

    def test_rejects_empty_vector(self):
        with self.assertRaises(ValueError):
            BasinSignature(
                domain="test",
                regime=DistributionRegime.FOCUSED,
                vector=(),
            )

    def test_is_frozen(self):
        sig = BasinSignature(
            domain="test",
            regime=DistributionRegime.MIXED,
            vector=(1.0,),
        )
        with self.assertRaises(Exception):  # FrozenInstanceError inherits from AttributeError
            sig.domain = "other"  # type: ignore[misc]


class TestIntersectionRuleABC(unittest.TestCase):

    def test_cannot_instantiate_base(self):
        with self.assertRaises(TypeError):
            IntersectionRule()  # type: ignore[abstract]

    def test_subclass_must_set_domain(self):
        class Bad(IntersectionRule):
            def signature(self, geometry):
                return BasinSignature(
                    domain="bad", regime=DistributionRegime.MIXED,
                    vector=(1.0,),
                )

        with self.assertRaises(TypeError):
            Bad()


# ---------------------------------------------------------------------------
# RESONATE
# ---------------------------------------------------------------------------

class TestResonate(unittest.TestCase):

    def _sig(self, domain, vec, regime=DistributionRegime.FOCUSED, conf=1.0):
        return BasinSignature(
            domain=domain, regime=regime, vector=vec, confidence=conf,
            scalar_strength=1.0,
        )

    def test_perfect_alignment_gives_coupling_1(self):
        a = self._sig("a", (1.0, 0.0, 0.0))
        b = self._sig("b", (2.0, 0.0, 0.0))
        c = resonate(a, b)
        self.assertAlmostEqual(c.coupling_strength, 1.0, places=6)

    def test_orthogonal_gives_coupling_0(self):
        a = self._sig("a", (1.0, 0.0, 0.0))
        b = self._sig("b", (0.0, 1.0, 0.0))
        c = resonate(a, b)
        self.assertAlmostEqual(c.coupling_strength, 0.0, places=6)

    def test_anti_alignment_gives_negative_coupling(self):
        a = self._sig("a", (1.0, 0.0, 0.0))
        b = self._sig("b", (-1.0, 0.0, 0.0))
        c = resonate(a, b)
        self.assertAlmostEqual(c.coupling_strength, -1.0, places=6)
        # Conflicting pair should collapse confidence.
        self.assertAlmostEqual(c.confidence, 0.0, places=6)

    def test_composed_domain_name(self):
        a = self._sig("gravity", (1.0,))
        b = self._sig("electric", (1.0,))
        c = resonate(a, b)
        self.assertIn("gravity", c.basin.domain)
        self.assertIn("electric", c.basin.domain)
        self.assertIn("⋈", c.basin.domain)

    def test_coupled_signature_is_fed_back_into_resonate(self):
        a = self._sig("a", (1.0, 0.0))
        b = self._sig("b", (1.0, 0.0))
        ab = resonate(a, b)
        c = self._sig("c", (1.0, 0.0))
        abc = resonate(ab.basin, c)
        self.assertIsInstance(abc, CoupledSignature)

    def test_heterogeneous_vector_lengths_are_padded(self):
        a = self._sig("a", (1.0,))
        b = self._sig("b", (0.0, 1.0, 0.0))
        # Shorter vector is zero-padded — must not raise.
        c = resonate(a, b)
        self.assertEqual(len(c.basin.vector), 3)

    def test_resonate_many_flattens_sources(self):
        a = self._sig("a", (1.0,))
        b = self._sig("b", (1.0,))
        c = self._sig("c", (1.0,))
        d = self._sig("d", (1.0,))
        fused = resonate_many([a, b, c, d])
        self.assertEqual(len(fused.sources), 4)
        self.assertEqual(
            [s.domain for s in fused.sources], ["a", "b", "c", "d"],
        )

    def test_resonate_many_requires_two(self):
        with self.assertRaises(ValueError):
            resonate_many([self._sig("a", (1.0,))])

    def test_tied_regimes_collapse_to_mixed(self):
        a = self._sig("a", (1.0, 0.0), regime=DistributionRegime.FOCUSED)
        b = self._sig("b", (0.0, 1.0), regime=DistributionRegime.DIFFUSE)
        c = resonate(a, b)
        self.assertEqual(c.regime, DistributionRegime.MIXED)


# ---------------------------------------------------------------------------
# GravityIntersectionRule (real physics)
# ---------------------------------------------------------------------------

class TestGravityIntersectionRule(unittest.TestCase):

    def test_attract_dominant_geometry_gives_negative_x(self):
        rule = GravityIntersectionRule()
        sig = rule.signature(GRAVITY_GEOM_ATTRACT)
        # All four vectors are attractors → x (repel - attract) should be strongly negative.
        self.assertLess(sig.vector[0], 0.0)
        self.assertEqual(sig.domain, "gravity")

    def test_lagrange_rich_geometry_gives_high_null_y(self):
        rule = GravityIntersectionRule()
        sig = rule.signature(GRAVITY_GEOM_LAGRANGE)
        self.assertGreater(sig.vector[1], 0.0)
        # x should be near zero since no attract or repel dominates.
        self.assertAlmostEqual(sig.vector[0], 0.0, places=6)

    def test_rule_preserves_last_diagnostic(self):
        rule = GravityIntersectionRule()
        rule.signature(GRAVITY_GEOM_ATTRACT)
        self.assertIsNotNone(rule.last_diagnostic)
        self.assertEqual(
            type(rule.last_diagnostic).__name__,
            "GravityAlternativeDiagnostic",
        )

    def test_empty_geometry_falls_back_to_neutral_signature(self):
        # Rule must not raise when the diagnostic has no ternary data.
        rule = GravityIntersectionRule()
        sig = rule.signature({})
        self.assertIsInstance(sig, BasinSignature)


# ---------------------------------------------------------------------------
# ElectricIntersectionRule
# ---------------------------------------------------------------------------

class TestElectricIntersectionRule(unittest.TestCase):

    def test_ac_balanced_is_diffuse_with_low_net_current(self):
        rule = ElectricIntersectionRule()
        sig = rule.signature(ELECTRIC_GEOM_AC)
        # AC balanced waveform → net current near zero.
        self.assertAlmostEqual(sig.vector[0], 0.0, delta=0.5)

    def test_dc_geometry_is_focused_with_positive_net_current(self):
        rule = ElectricIntersectionRule()
        sig = rule.signature(ELECTRIC_GEOM_DC)
        # All FORWARD → net current strongly positive.
        self.assertGreater(sig.vector[0], 0.5)
        self.assertEqual(sig.regime, DistributionRegime.FOCUSED)


# ---------------------------------------------------------------------------
# SoundIntersectionRule
# ---------------------------------------------------------------------------

class TestSoundIntersectionRule(unittest.TestCase):

    def test_produces_three_axis_vector(self):
        rule = SoundIntersectionRule()
        sig = rule.signature(SOUND_GEOM)
        self.assertEqual(len(sig.vector), 3)
        self.assertEqual(sig.domain, "sound")


# ---------------------------------------------------------------------------
# CommunityIntersectionRule
# ---------------------------------------------------------------------------

class TestCommunityIntersectionRule(unittest.TestCase):

    def test_produces_signature_with_buffer_metadata(self):
        rule = CommunityIntersectionRule()
        sig = rule.signature(COMMUNITY_GEOM)
        self.assertEqual(sig.domain, "community")
        self.assertIn("deplete_fraction", sig.metadata)
        self.assertIn("stable_fraction", sig.metadata)
        self.assertIn("abundant_fraction", sig.metadata)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry(unittest.TestCase):

    def test_four_domains_registered(self):
        self.assertIn("gravity", registered_domains())
        self.assertIn("electric", registered_domains())
        self.assertIn("sound", registered_domains())
        self.assertIn("community", registered_domains())

    def test_get_rule_returns_correct_subclass(self):
        self.assertIsInstance(get_rule("gravity"), GravityIntersectionRule)
        self.assertIsInstance(get_rule("electric"), ElectricIntersectionRule)
        self.assertIsInstance(get_rule("sound"), SoundIntersectionRule)
        self.assertIsInstance(get_rule("community"), CommunityIntersectionRule)

    def test_unknown_domain_raises(self):
        with self.assertRaises(KeyError):
            get_rule("nonsense-domain-xyz")

    def test_domain_rules_facade_is_dict_shaped(self):
        self.assertIn("gravity", DOMAIN_RULES)
        self.assertIsInstance(
            DOMAIN_RULES["gravity"], GravityIntersectionRule,
        )
        self.assertIsNotNone(DOMAIN_RULES.get("gravity"))
        self.assertIsNone(DOMAIN_RULES.get("nonexistent"))

    def test_register_rule_overrides(self):
        class Fake(IntersectionRule):
            domain = "fake-test-domain"

            def signature(self, geometry):
                return BasinSignature(
                    domain=self.domain,
                    regime=DistributionRegime.MIXED,
                    vector=(0.5,),
                )

        fake = Fake()
        register_rule("fake-test-domain", fake)
        self.assertIs(get_rule("fake-test-domain"), fake)

    def test_register_rule_type_check(self):
        with self.assertRaises(TypeError):
            register_rule("bogus", object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# End-to-end: four-domain RESONATE over real physics
# ---------------------------------------------------------------------------

class TestFourDomainResonate(unittest.TestCase):

    def test_all_four_rules_fuse(self):
        g_sig = DOMAIN_RULES["gravity"].signature(GRAVITY_GEOM_ATTRACT)
        e_sig = DOMAIN_RULES["electric"].signature(ELECTRIC_GEOM_AC)
        s_sig = DOMAIN_RULES["sound"].signature(SOUND_GEOM)
        c_sig = DOMAIN_RULES["community"].signature(COMMUNITY_GEOM)

        fused = resonate_many([g_sig, e_sig, s_sig, c_sig])
        self.assertEqual(len(fused.sources), 4)
        self.assertIn("gravity", fused.basin.domain)
        self.assertIn("community", fused.basin.domain)
        self.assertIn(
            fused.regime,
            {
                DistributionRegime.FOCUSED,
                DistributionRegime.MIXED,
                DistributionRegime.DIFFUSE,
            },
        )


if __name__ == "__main__":
    unittest.main()
