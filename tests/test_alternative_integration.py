"""
tests/test_alternative_integration.py
=====================================

Covers the ternary / alternative-computing integration layer:

  * ``bridges.encode_state.encode_state`` dispatcher
  * ``bridges.adapters.BinaryAdapter`` and ``AlternativeAdapter``
  * ``bridges.integration_pipeline.run_full_bridge`` + ``run_all_bridges``
  * ``bridges.state_graph`` dual-path graph
  * ``bridges.alternative_spice.AlternativeSPICE``
  * ``bridges.event_scheduler`` zero-crossing detector
  * ``bridges.ternary_field`` ternary-aware diffusion
"""

from __future__ import annotations

import math
import unittest

from bridges.adapters import AlternativeAdapter, BinaryAdapter
from bridges.alternative_spice import AlternativeSPICE
from bridges.encode_state import (
    alternative_encode,
    binary_encode,
    encode_alternative,
    encode_binary,
    encode_state,
)
from bridges.event_scheduler import EventScheduler, detect_zero_crossings
from bridges.integration_pipeline import (
    domains_missing_alternative,
    domains_with_alternative,
    run_all_bridges,
    run_full_bridge,
)
from bridges.probability_collapse import (
    DistributionCollapse,
    DistributionRegime,
    collapse_distribution,
)
from bridges.state_graph import (
    Node,
    StateGraph,
    build_dual_path_graph,
)
from bridges.ternary_field import TernaryField, propagate


ELECTRIC_GEOMETRY = {
    "charge":         [1e-6, -3e-9, 5e-12, -8e-14],
    "current_A":      [0.5, -0.02, 0.0, 10.0, -5.0, 0.001, -0.001],
    "voltage_V":      [12.0, 0.5, 230.0, 0.99],
    "conductivity_S": [5.96e7, 1e-8, 1e-6, 9e-7, 1.1e-6],
}


# ---------------------------------------------------------------------------
# encode_state dispatcher
# ---------------------------------------------------------------------------

class TestEncodeStateDispatcher(unittest.TestCase):

    def test_binary_mode_returns_bitstring(self):
        out = encode_state(ELECTRIC_GEOMETRY, domain="electric", mode="binary")
        self.assertIsInstance(out, str)
        self.assertTrue(set(out) <= {"0", "1"})
        self.assertGreater(len(out), 0)

    def test_ternary_mode_returns_diagnostic(self):
        diag = encode_state(
            ELECTRIC_GEOMETRY, domain="electric",
            mode="ternary", frequency_hz=60.0,
        )
        self.assertEqual(
            type(diag).__name__, "ElectricAlternativeDiagnostic"
        )
        self.assertGreater(len(diag.charge_states), 0)
        self.assertGreater(len(diag.current_states), 0)

    def test_alternative_aliases_match_ternary(self):
        a = encode_state(ELECTRIC_GEOMETRY, domain="electric", mode="ternary")
        b = encode_state(ELECTRIC_GEOMETRY, domain="electric", mode="alternative")
        c = encode_state(ELECTRIC_GEOMETRY, domain="electric", mode="alt")
        self.assertEqual(type(a).__name__, type(b).__name__)
        self.assertEqual(type(b).__name__, type(c).__name__)

    def test_dual_mode_returns_both_paths(self):
        out = encode_state(
            ELECTRIC_GEOMETRY, domain="electric",
            mode="dual", frequency_hz=60.0,
        )
        self.assertIsInstance(out, dict)
        self.assertIn("binary", out)
        self.assertIn("alternative", out)
        self.assertIsInstance(out["binary"], str)
        self.assertIsNotNone(out["alternative"])

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            encode_state(ELECTRIC_GEOMETRY, mode="quantum-foo")

    def test_missing_alternative_raises_notimplemented(self):
        with self.assertRaises(NotImplementedError):
            encode_state(
                {"field": [[1.0, 0.0, 0.0]], "flux_density_T": [0.1],
                 "current_A": [0.5]},
                domain="magnetic",
                mode="ternary",
            )

    def test_spec_aliases_exist(self):
        # encode_binary / encode_alternative were listed in the spec
        # as the public entry points.
        bin_out = encode_binary(ELECTRIC_GEOMETRY, domain="electric")
        alt_out = encode_alternative(
            ELECTRIC_GEOMETRY, domain="electric", frequency_hz=60.0,
        )
        self.assertIsInstance(bin_out, str)
        self.assertEqual(
            type(alt_out).__name__, "ElectricAlternativeDiagnostic"
        )


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

class TestAdapters(unittest.TestCase):

    def test_binary_adapter_matches_direct_call(self):
        adapter = BinaryAdapter("electric")
        direct = binary_encode(ELECTRIC_GEOMETRY, domain="electric")
        self.assertEqual(adapter.encode(ELECTRIC_GEOMETRY), direct)

    def test_binary_adapter_report_keys(self):
        report = BinaryAdapter("electric").report(ELECTRIC_GEOMETRY)
        self.assertIn("modality", report)
        self.assertIn("bits", report)
        self.assertIn("checksum", report)

    def test_binary_adapter_unknown_domain(self):
        with self.assertRaises(KeyError):
            BinaryAdapter("nonsense")

    def test_alternative_adapter_availability_flags(self):
        self.assertTrue(AlternativeAdapter("electric").is_available)
        self.assertTrue(AlternativeAdapter("sound").is_available)
        self.assertTrue(AlternativeAdapter("gravity").is_available)
        self.assertFalse(AlternativeAdapter("magnetic").is_available)

    def test_alternative_adapter_encode(self):
        diag = AlternativeAdapter("electric").encode(
            ELECTRIC_GEOMETRY, frequency_hz=60.0
        )
        self.assertEqual(
            type(diag).__name__, "ElectricAlternativeDiagnostic"
        )


# ---------------------------------------------------------------------------
# Integration pipeline
# ---------------------------------------------------------------------------

class TestIntegrationPipeline(unittest.TestCase):

    def test_run_full_bridge_electric(self):
        r = run_full_bridge(
            ELECTRIC_GEOMETRY, domain="electric",
            frequency_hz=60.0, include_raw_encoder=True,
        )
        self.assertEqual(r["domain"], "electric")
        self.assertIsInstance(r["binary_representation"], str)
        self.assertTrue(r["alternative_available"])
        self.assertIsNotNone(r["alternative_representation"])
        self.assertIn("raw_encoder_state", r)

    def test_run_full_bridge_domain_without_alternative(self):
        # Use the magnetic encoder's expected schema. The alternative
        # path is not yet implemented; the pipeline must still return a
        # binary representation and mark alternative_available=False.
        magnetic_geometry = {
            "field_vectors": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            "resonance_frequency_Hz": 2.45e9,
        }
        r = run_full_bridge(magnetic_geometry, domain="magnetic")
        self.assertIsInstance(r["binary_representation"], str)
        self.assertFalse(r["alternative_available"])
        self.assertIsNone(r["alternative_representation"])

    def test_run_all_bridges_subset(self):
        results = run_all_bridges(
            {"electric": ELECTRIC_GEOMETRY},
            frequency_hz=60.0,
        )
        self.assertIn("electric", results)
        self.assertTrue(results["electric"]["alternative_available"])

    def test_domain_coverage_lists(self):
        have = set(domains_with_alternative())
        missing = set(domains_missing_alternative())
        self.assertIn("electric", have)
        self.assertIn("sound", have)
        self.assertIn("gravity", have)
        self.assertIn("magnetic", missing)
        self.assertTrue(have.isdisjoint(missing))


# ---------------------------------------------------------------------------
# State graph
# ---------------------------------------------------------------------------

class TestStateGraph(unittest.TestCase):

    def test_trivial_graph(self):
        g = StateGraph()
        g.add_node(Node(
            name="square",
            fn=lambda i, s: {"y": i["x"] ** 2},
            inputs=["x"],
            outputs=["y"],
        ))
        g.set_input("x", 4)
        out = g.run()
        self.assertEqual(out["y"], 16)

    def test_scalar_return_writes_to_first_output(self):
        g = StateGraph()
        g.add_node(Node(
            name="neg",
            fn=lambda i, s: -i["x"],
            inputs=["x"],
            outputs=["y"],
        ))
        g.set_input("x", 7)
        out = g.run()
        self.assertEqual(out["y"], -7)

    def test_duplicate_name_rejected(self):
        g = StateGraph()
        g.add_node(Node("a", fn=lambda i, s: 1, inputs=[], outputs=["a"]))
        with self.assertRaises(ValueError):
            g.add_node(Node("a", fn=lambda i, s: 2, inputs=[], outputs=["a"]))

    def test_stall_raises(self):
        g = StateGraph()
        g.add_node(Node(
            name="needs_missing",
            fn=lambda i, s: {"y": 1},
            inputs=["missing_key"],
            outputs=["y"],
        ))
        with self.assertRaises(RuntimeError):
            g.run()

    def test_dual_path_graph_end_to_end(self):
        g = build_dual_path_graph(domain="electric")
        g.set_input("geometry", ELECTRIC_GEOMETRY)
        g.set_input("frequency_hz", 60.0)
        out = g.run()
        self.assertIn("merged", out)
        merged = out["merged"]
        self.assertIsInstance(merged["binary"], str)
        self.assertIsNotNone(merged["alternative"])


# ---------------------------------------------------------------------------
# AlternativeSPICE
# ---------------------------------------------------------------------------

class TestAlternativeSPICE(unittest.TestCase):

    def test_step_populates_all_views(self):
        sim = AlternativeSPICE(frequency_hz=60.0)
        sim.add_node("n1", voltage=1.0, conductivity=5.96e7)
        state = sim.step()
        self.assertIn("n1", state.currents)
        self.assertIn("n1", state.ternary_states)
        self.assertIn(state.ternary_states["n1"], (-1, 0, 1))
        self.assertIn("n1", state.skin_effects)
        self.assertIn("n1", state.probabilities)

    def test_run_advances_time(self):
        sim = AlternativeSPICE(frequency_hz=60.0, dt=1e-4)
        sim.add_node("n1", voltage=1.0, conductivity=5.96e7)
        sim.run(steps=10)
        self.assertAlmostEqual(sim.state.time, 10 * 1e-4, places=6)

    def test_history_recording(self):
        sim = AlternativeSPICE(frequency_hz=60.0, record_history=True)
        sim.add_node("n1", voltage=1.0, conductivity=5.96e7)
        sim.run(steps=5)
        self.assertEqual(len(sim.state.history["n1"]), 5)

    def test_ternary_symbols_are_strings(self):
        sim = AlternativeSPICE(frequency_hz=60.0)
        sim.add_node("n1", voltage=1.0, conductivity=5.96e7)
        sim.step()
        syms = sim.ternary_symbols()
        self.assertIsInstance(syms["n1"], str)


# ---------------------------------------------------------------------------
# Event scheduler + zero-crossing
# ---------------------------------------------------------------------------

class TestEventScheduler(unittest.TestCase):

    def test_run_executes_in_time_order(self):
        order = []
        sched = EventScheduler()
        sched.schedule(2.0, lambda t, s: order.append(("b", t)), args=(2.0,))
        sched.schedule(1.0, lambda t, s: order.append(("a", t)), args=(1.0,))
        sched.run(5.0)
        self.assertEqual([e[0] for e in order], ["a", "b"])

    def test_run_stops_at_t_end(self):
        sched = EventScheduler()
        sched.schedule(1.0, lambda t, s: None, args=(1.0,))
        sched.schedule(10.0, lambda t, s: None, args=(10.0,))
        sched.run(5.0)
        self.assertEqual(sched.pending(), 1)  # the 10.0 event remains

    def test_zero_crossing_detection_60hz(self):
        sched = EventScheduler()
        found = []
        detect_zero_crossings(
            signal_fn=lambda t: math.sin(2.0 * math.pi * 60.0 * t),
            t0=0.0, t1=0.05, dt=1e-4,
            scheduler=sched,
            handler=lambda t, s: found.append(t),
        )
        sched.run(0.05)
        # 60 Hz over 50 ms: at least 5 full crossings expected.
        self.assertGreaterEqual(len(found), 5)
        # Crossings should be monotonically increasing in time.
        self.assertEqual(found, sorted(found))


# ---------------------------------------------------------------------------
# TernaryField propagation
# ---------------------------------------------------------------------------

class TestTernaryField(unittest.TestCase):

    def test_rejects_tiny_grid(self):
        with self.assertRaises(ValueError):
            TernaryField(2, 5)

    def test_probability_out_of_range_rejected(self):
        f = TernaryField(5, 5)
        with self.assertRaises(ValueError):
            f.set_probability(0, 0, 2.0)

    def test_propagate_collapses_to_ternary(self):
        f = TernaryField(5, 5)
        f.fill_conductivity(1.0)
        f.set_charge(2, 2, 1.0)
        propagate(f, dt=0.1)

        for i in range(1, 4):
            for j in range(1, 4):
                charge, current, _, prob = f.cell(i, j)
                self.assertIn(charge, (-1, 0, 1))
                self.assertIn(current, (-1.0, 0.0, 1.0))
                self.assertGreaterEqual(prob, 0.0)
                self.assertLessEqual(prob, 1.0)

    def test_propagate_spreads_charge_to_neighbours(self):
        f = TernaryField(7, 7)
        f.fill_conductivity(10.0)
        f.set_charge(3, 3, 1.0)
        # Several steps so the charge has time to reach the 4-neighbour ring.
        for _ in range(5):
            propagate(f, dt=0.2)
        # At least one of the direct neighbours should have become non-zero
        # in either the charge or current channel.
        activated = any(
            f.cell(3 + dx, 3 + dy)[0] != 0 or f.cell(3 + dx, 3 + dy)[1] != 0
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]
        )
        self.assertTrue(activated)


# ---------------------------------------------------------------------------
# DistributionCollapse + splat state_collapse() extensions
# ---------------------------------------------------------------------------

class TestProbabilityCollapse(unittest.TestCase):

    def test_focused_regime(self):
        probs = [0.98, 0.01, 0.005, 0.005]
        c = collapse_distribution(probs)
        self.assertEqual(c.dominant_index, 0)
        self.assertAlmostEqual(c.dominant_probability, 0.98, places=6)
        self.assertEqual(c.runner_up_index, 1)
        self.assertEqual(c.regime, DistributionRegime.FOCUSED)
        self.assertLess(c.normalised_entropy, 0.35)

    def test_diffuse_regime(self):
        c = collapse_distribution([0.25] * 4)
        self.assertEqual(c.regime, DistributionRegime.DIFFUSE)
        self.assertAlmostEqual(c.normalised_entropy, 1.0, places=6)
        self.assertAlmostEqual(c.margin, 0.0, places=6)

    def test_mixed_regime(self):
        # One state clearly dominant but with non-trivial tail mass —
        # normalised entropy around 0.62 → MIXED with the default
        # thresholds (0.35 / 0.75).
        c = collapse_distribution([0.7, 0.2, 0.07, 0.03])
        self.assertEqual(c.regime, DistributionRegime.MIXED)

    def test_auto_normalisation(self):
        c = collapse_distribution([10.0, 30.0, 60.0])
        total = sum(c.probabilities)
        self.assertAlmostEqual(total, 1.0, places=6)
        self.assertEqual(c.dominant_index, 2)

    def test_all_zero_treated_as_uniform(self):
        c = collapse_distribution([0.0, 0.0, 0.0, 0.0])
        self.assertEqual(c.regime, DistributionRegime.DIFFUSE)
        for p in c.probabilities:
            self.assertAlmostEqual(p, 0.25, places=6)

    def test_rejects_negative(self):
        with self.assertRaises(ValueError):
            collapse_distribution([0.5, -0.1, 0.6])

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            collapse_distribution([])

    def test_dominant_matches_argmax(self):
        # Contract with existing argmax callers: dominant_index must
        # equal int(np.argmax(...)) for any non-degenerate vector.
        import numpy as np

        rng = np.random.default_rng(seed=42)
        for _ in range(5):
            vec = rng.random(16).tolist()
            c = collapse_distribution(vec)
            self.assertEqual(c.dominant_index, int(np.argmax(vec)))

    def test_top_k_is_sorted_descending(self):
        c = collapse_distribution([0.1, 0.4, 0.2, 0.3])
        ranked = c.top_k(4)
        probs = [p for _, p in ranked]
        self.assertEqual(probs, sorted(probs, reverse=True))


class TestSplatStateCollapse(unittest.TestCase):
    """The Gaussian splat sources must expose the ternary view while
    preserving the old argmax contract from ``most_likely_state``."""

    def _make_octa(self):
        import numpy as np

        from Engine.gaussian_splats.octahedral import Gaussian8FieldSource

        mu = np.array([0.0, 0.0, 0.0, 0.9, 0.9, 0.9])
        cov = np.eye(6) * 0.2
        return Gaussian8FieldSource(mu=mu, cov=cov, charge=1.0)

    def _make_rhombic(self):
        import numpy as np

        from Engine.gaussian_splats.rhombic import (
            Gaussian32FieldSource,
            RhombicTriacontaEncoder,
        )

        encoder = RhombicTriacontaEncoder()
        mu = np.zeros(6)
        mu[3:] = encoder.vertices[7]
        cov = np.eye(6) * 0.1
        return Gaussian32FieldSource(mu=mu, cov=cov, encoder=encoder)

    def test_octa_state_collapse_returns_collapse(self):
        src = self._make_octa()
        c = src.state_collapse()
        self.assertIsInstance(c, DistributionCollapse)
        self.assertEqual(len(c.probabilities), 8)

    def test_octa_dominant_matches_most_likely(self):
        src = self._make_octa()
        c = src.state_collapse()
        self.assertEqual(c.dominant_index, src.most_likely_state())

    def test_octa_focused_vs_diffuse(self):
        import numpy as np

        from Engine.gaussian_splats.octahedral import Gaussian8FieldSource

        # Tight covariance around one corner → focused.
        mu_focused = np.array([0.0, 0.0, 0.0, 0.95, 0.95, 0.95])
        cov_focused = np.eye(6) * 0.1
        focused = Gaussian8FieldSource(
            mu=mu_focused, cov=cov_focused,
        ).state_collapse()
        self.assertEqual(focused.regime, DistributionRegime.FOCUSED)

        # Broad covariance at the origin → diffuse.
        mu_diffuse = np.zeros(6)
        cov_diffuse = np.eye(6) * 5.0
        diffuse = Gaussian8FieldSource(
            mu=mu_diffuse, cov=cov_diffuse,
        ).state_collapse()
        self.assertEqual(diffuse.regime, DistributionRegime.DIFFUSE)

    def test_rhombic_state_collapse(self):
        src = self._make_rhombic()
        c = src.state_collapse()
        self.assertIsInstance(c, DistributionCollapse)
        self.assertEqual(len(c.probabilities), 32)
        self.assertEqual(c.dominant_index, src.most_likely_state())


# ---------------------------------------------------------------------------
# field_adapter — solver output → alternative dispatcher
# ---------------------------------------------------------------------------

class TestFieldAdapter(unittest.TestCase):

    def _solver_output(self):
        from Engine.geometric_solver import GeometricEMSolver

        sources = [
            {"type": "charge", "position": [0.0, 0.0, 0.0],
             "charge": 1e-6},
            {"type": "charge", "position": [0.1, 0.0, 0.0],
             "charge": -1e-6, "conductivity": 5.96e7},
        ]
        bounds = {"min": [-0.2, -0.2, -0.2], "max": [0.2, 0.2, 0.2]}
        data = GeometricEMSolver().calculateElectromagneticField(
            sources, bounds, resolution=6,
        )
        data["sources"] = sources
        return data

    def test_field_to_geometry_shape(self):
        from bridges.field_adapter import field_to_geometry

        g = field_to_geometry(self._solver_output())
        self.assertIn("voltage_V", g)
        self.assertIn("current_A", g)
        self.assertIn("charge", g)
        self.assertEqual(len(g["voltage_V"]), len(g["current_A"]))
        # Sign must be preserved so zero-crossings survive.
        self.assertTrue(
            any(v < 0 for v in g["current_A"])
            or any(v > 0 for v in g["current_A"])
        )

    def test_field_to_alternative_dual(self):
        from bridges.field_adapter import field_to_alternative

        out = field_to_alternative(
            self._solver_output(), mode="dual", frequency_hz=60.0,
        )
        self.assertIsInstance(out, dict)
        self.assertIn("binary", out)
        self.assertIn("alternative", out)
        self.assertIsInstance(out["binary"], str)
        self.assertIsNotNone(out["alternative"])
        self.assertEqual(
            type(out["alternative"]).__name__,
            "ElectricAlternativeDiagnostic",
        )

    def test_field_to_alternative_binary_only(self):
        from bridges.field_adapter import field_to_alternative

        bits = field_to_alternative(self._solver_output(), mode="binary")
        self.assertIsInstance(bits, str)
        self.assertTrue(set(bits) <= {"0", "1"})


if __name__ == "__main__":
    unittest.main()
