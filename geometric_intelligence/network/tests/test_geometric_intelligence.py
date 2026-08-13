#!/usr/bin/env python3
"""
test_geometric_intelligence.py -- the drop's own 20 tests, as supplied.

    python -m unittest geometric_intelligence.network.tests.test_geometric_intelligence

Kept because it is what the package's README cites as its validation, and
because what it does and does not exercise is itself the finding. All 20 pass.
Three of them cannot fail, and `tests/test_gi_network.py` in this repo asserts
that they cannot -- so this file is evidence, not coverage. GI-16:

  test_audit_passes    asserts 0 <= integrity_score <= INTEGRITY_THRESHOLD.
                       audit() computes min(base*(1+w), THRESHOLD) with
                       base >= 0 and w >= 0, so both bounds hold for every
                       network by construction. A deliberately absurd network
                       (factor 99, weight 1e9) satisfies it.

  test_hash_stable     calls net.hash() twice on one unchanged object. The
                       property the docstring claims -- a hash of "topology
                       and relations" -- is FALSE: the same nodes added in a
                       different order hash differently, because to_dict()
                       preserves insertion order. GI-15.

  test_correct         asserts inconsistent_after <= inconsistent_before on a
                       fixture commented "slightly wrong" whose factors are
                       2.5 and 0.4. 2.5 * 0.4 = 1.0 exactly, so the fixture is
                       already consistent, both sides are 0, and correct() is
                       never exercised on an inconsistent network by anything
                       in this suite.

test_find_cycles_consistent guards its assertion on `if len(cycle) == 3` and
was checked: its fixture does produce one 3-cycle, so it runs. Listed here
because a guarded assertion is worth confirming rather than assuming.

License: CC0. Stdlib only.
"""
import sys
import math
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from geometric_intelligence.network import (
    GeometricNetwork, MultiScaleResonance, IntegrityMonitor,
    GeoNode, GeoEdge,
    PHI, PHI_INV, PHI_INV_9, INTEGRITY_THRESHOLD
)
from geometric_intelligence.network.bridge import network_to_claims, verify_edge_measurement


class TestCore(unittest.TestCase):

    def test_phi_values(self):
        self.assertAlmostEqual(PHI, 1.6180339887, places=6)
        self.assertAlmostEqual(PHI_INV, 1.0 / PHI, places=10)
        self.assertAlmostEqual(PHI_INV_9, PHI_INV ** 9, places=10)
        self.assertAlmostEqual(INTEGRITY_THRESHOLD, PHI ** 2 + 1.0, places=6)

    def test_add_node_and_edge(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=2.0)
        net.add_edge("A", "B", "scale", factor=2.0)
        self.assertEqual(len(net.nodes), 2)
        self.assertEqual(len(net.edges), 1)
        self.assertEqual(net._adj["A"][0].target, "B")

    def test_apply_scale(self):
        net = GeometricNetwork()
        e = GeoEdge("A", "B", "scale", factor=2.0)
        self.assertEqual(net._apply(e, 5.0), 10.0)

    def test_apply_compose(self):
        net = GeometricNetwork()
        e = GeoEdge("A", "B", "compose", factor=2.0, offset=3.0)
        self.assertEqual(net._apply(e, 5.0), 13.0)

    def test_compose_transforms(self):
        net = GeometricNetwork()
        e1 = GeoEdge("A", "B", "scale", factor=2.0)
        e2 = GeoEdge("B", "C", "scale", factor=3.0)
        a, b = net._compose_transforms([e1, e2])
        self.assertEqual(a, 6.0)
        self.assertEqual(b, 0.0)

    def test_find_cycles_consistent(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=PHI)
        net.add_node("C", value=PHI ** 2)
        net.add_edge("A", "B", "scale", factor=PHI)
        net.add_edge("B", "C", "scale", factor=PHI)
        net.add_edge("C", "A", "scale", factor=PHI_INV ** 2)

        cycles = net.find_cycles(max_depth=5)
        self.assertGreater(len(cycles), 0)
        # The cycle A->B->C->A should have near-zero closure error
        for cycle, err in cycles:
            if len(cycle) == 3:
                self.assertLess(err, PHI_INV_9)

    def test_audit_passes(self):
        net = GeometricNetwork()
        for i in range(4):
            net.add_node(f"n{i}", value=PHI ** i)
        for i in range(3):
            net.add_edge(f"n{i}", f"n{i+1}", "scale", factor=PHI)
            net.add_edge(f"n{i+1}", f"n{i}", "scale", factor=PHI_INV)

        audit = net.audit()
        self.assertGreaterEqual(audit["integrity_score"], 0.0)
        self.assertLessEqual(audit["integrity_score"], INTEGRITY_THRESHOLD)

    def test_correct(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=2.0)
        net.add_edge("A", "B", "scale", factor=2.5)  # slightly wrong
        net.add_edge("B", "A", "scale", factor=0.4)   # slightly wrong

        audit_before = net.audit()
        net.correct(max_iter=10)
        audit_after = net.audit()

        # Correction should improve or maintain consistency
        self.assertLessEqual(
            audit_after["inconsistent_cycles"],
            audit_before["inconsistent_cycles"]
        )

    def test_to_from_dict(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=2.0)
        net.add_edge("A", "B", "scale", factor=2.0)

        d = net.to_dict()
        net2 = GeometricNetwork.from_dict(d)
        self.assertEqual(len(net2.nodes), 2)
        self.assertEqual(len(net2.edges), 1)

    def test_hash_stable(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        h1 = net.hash()
        h2 = net.hash()
        self.assertEqual(h1, h2)


class TestResonance(unittest.TestCase):

    def test_empty_spectrum(self):
        analyzer = MultiScaleResonance(10, 1000)
        result = analyzer.analyze([], [], expected_slope=-1.0)
        self.assertEqual(result["peaks"], [])
        self.assertEqual(result["anomalies"], [])

    def test_single_peak(self):
        freqs = [10 * (1.05 ** i) for i in range(100)]
        amps = [1.0 / f for f in freqs]
        # Add one strong peak
        for i, f in enumerate(freqs):
            if abs(f - 200) < 20:
                amps[i] += 2.0

        analyzer = MultiScaleResonance(10, 1000)
        result = analyzer.analyze(freqs, amps, expected_slope=-1.0)
        self.assertGreater(len(result["peaks"]), 0)

    def test_anomaly_detection(self):
        freqs = [10 * (1.05 ** i) for i in range(150)]
        amps = [1.0 / f for f in freqs]
        # Add anomalous peak far above 1/f expectation
        for i, f in enumerate(freqs):
            if abs(f - 500) < 10:
                amps[i] += 10.0

        analyzer = MultiScaleResonance(10, 1000)
        result = analyzer.analyze(freqs, amps, expected_slope=-1.0)
        self.assertGreater(len(result["anomalies"]), 0)
        self.assertGreater(result["anomaly_score"], 0.0)

    def test_injection_detection(self):
        freqs = [10 * (1.05 ** i) for i in range(100)]
        baseline = [1.0 / f for f in freqs]
        current = [1.0 / f for f in freqs]
        # Inject strong energy (3x baseline to exceed threshold)
        for i in range(40, 50):
            current[i] *= 3.0

        analyzer = MultiScaleResonance(10, 1000)
        result = analyzer.detect_injection(freqs, current, baseline)
        self.assertGreater(len(result["injections"]), 0)


class TestIntegrity(unittest.TestCase):

    def test_trusted_measurements(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=PHI)
        net.add_edge("A", "B", "scale", factor=PHI)
        net.add_edge("B", "A", "scale", factor=PHI_INV)

        monitor = IntegrityMonitor(net)
        monitor.add_measurement("A", 1.0)
        monitor.add_measurement("B", PHI)

        reports = monitor.check()
        self.assertEqual(len(reports), 2)
        self.assertTrue(all(r.trusted for r in reports))

    def test_untrusted_measurement(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=PHI)
        net.add_edge("A", "B", "scale", factor=PHI)
        net.add_edge("B", "A", "scale", factor=PHI_INV)

        monitor = IntegrityMonitor(net)
        monitor.add_measurement("A", 1.0)
        monitor.add_measurement("B", 5.0)  # way off

        reports = monitor.check()
        untrusted = [r for r in reports if not r.trusted]
        self.assertGreater(len(untrusted), 0)

    def test_reconstruction(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=PHI)
        net.add_node("C", value=PHI ** 2)
        net.add_edge("A", "B", "scale", factor=PHI)
        net.add_edge("B", "C", "scale", factor=PHI)
        net.add_edge("C", "B", "scale", factor=PHI_INV)
        net.add_edge("B", "A", "scale", factor=PHI_INV)

        monitor = IntegrityMonitor(net)
        monitor.add_measurement("A", 1.0)
        monitor.add_measurement("B", PHI)
        # C not measured — should be reconstructed

        recon = monitor.reconstruct()
        self.assertIn("C", recon)
        self.assertAlmostEqual(recon["C"], PHI ** 2, places=2)

    def test_full_report(self):
        net = GeometricNetwork()
        net.add_node("A", value=1.0)
        net.add_node("B", value=PHI)
        net.add_edge("A", "B", "scale", factor=PHI)
        net.add_edge("B", "A", "scale", factor=PHI_INV)

        monitor = IntegrityMonitor(net)
        monitor.add_measurement("A", 1.0)
        monitor.add_measurement("B", PHI)

        report = monitor.full_report()
        self.assertIn("integrity_score", report)
        self.assertIn("passes", report)
        self.assertTrue(report["passes"])


class TestBridge(unittest.TestCase):

    def test_network_to_claims(self):
        net = GeometricNetwork()
        net.add_node("L1", value=0.1)
        net.add_node("L2", value=0.162)
        net.add_edge("L1", "L2", "scale", factor=PHI)

        claims = network_to_claims(net, scope_prefix="test")
        self.assertGreater(len(claims), 0)

        # Should have edge claim + integrity claim
        edge_claims = [c for c in claims if "edge" in c["scope"]]
        integrity_claims = [c for c in claims if "integrity" in c["scope"]]
        self.assertEqual(len(edge_claims), 1)
        self.assertEqual(len(integrity_claims), 1)

    def test_verify_edge_measurement(self):
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            claims = [{
                "scope": "fab::geometric::test::edge0",
                "rate_var": "scale_factor",
                "value": 1.618,
                "tol_frac": 0.05
            }]
            json.dump(claims, f)
            path = f.name

        try:
            result = verify_edge_measurement("test", 0, 1.62, Path(path))
            self.assertEqual(result["verdict"], "pass")

            result2 = verify_edge_measurement("test", 0, 2.0, Path(path))
            self.assertEqual(result2["verdict"], "fail")
        finally:
            Path(path).unlink()


if __name__ == "__main__":
    unittest.main()
