#!/usr/bin/env python3
"""
examples/demo.py -- the drop's demonstration, as supplied except its imports.

    python geometric_intelligence/network/examples/demo.py

Three things it prints are findings rather than features, and are left visible
rather than tidied away:

  DEMO 2  "Edges modified: 10" appears between an integrity score of 1.600000
          and an integrity score of 1.600000. At max_iter=5 the correction
          step is ~0.66 % of the error per edge per pass, so nothing measurable
          moves; `modified` counts adjustments, not distinct edges. Run to
          convergence it does reach 5/5 consistent -- by splitting the injected
          23.6 % error across two edges rather than removing it. GI-13.

  DEMO 5  the fabrication bridge is handed an acyclic chain and writes
          `integrity_score = 0.000000 +/- 10.0%` with "0/0 cycles consistent".
          A correct design scores worst, and that zero is the value
          `verify_edge_measurement` divides by. GB-1, GB-2.

  DEMO 1  "Passes: YES" is computed in the demo, not returned by audit(): the
          gate `integrity_score >= INTEGRITY_THRESHOLD * 0.5` is written here
          and nowhere else. See GI-12 on what that score is made of.

License: CC0. Stdlib only.
"""
import sys
import math
from pathlib import Path

# Add parent to path if running standalone
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from geometric_intelligence.network import (
    GeometricNetwork, MultiScaleResonance, IntegrityMonitor,
    PHI, PHI_INV, PHI_INV_9, INTEGRITY_THRESHOLD
)
from geometric_intelligence.network.bridge import network_to_claims


def demo_nautilus_network():
    """
    Model a nautilus-shell chamber growth as a geometric network.
    Each chamber is ~φ times larger than the previous.
    """
    print("=" * 64)
    print("DEMO 1: Nautilus-shell geometric network")
    print("=" * 64)

    net = GeometricNetwork()

    # Chamber volumes follow φ-scaling
    n_chambers = 6
    for i in range(n_chambers):
        net.add_node(f"chamber_{i}", value=PHI ** i)

    # Each chamber scales by φ from the previous
    for i in range(n_chambers - 1):
        net.add_edge(f"chamber_{i}", f"chamber_{i+1}", 
                     "scale", factor=PHI, weight=1.0)
        # Inverse: going backward
        net.add_edge(f"chamber_{i+1}", f"chamber_{i}",
                     "scale", factor=PHI_INV, weight=1.0)

    # Cross-connections: every other chamber should scale by φ²
    for i in range(n_chambers - 2):
        net.add_edge(f"chamber_{i}", f"chamber_{i+2}",
                     "scale", factor=PHI ** 2, weight=0.8)

    print(f"Nodes: {len(net.nodes)}, Edges: {len(net.edges)}")

    # Audit
    audit = net.audit()
    print(f"\nAudit results:")
    print(f"  Cycles found: {audit['n_cycles']}")
    print(f"  Consistent: {audit['consistent_cycles']}")
    print(f"  Inconsistent: {audit['inconsistent_cycles']}")
    print(f"  Integrity score: {audit['integrity_score']:.6f} (threshold: {INTEGRITY_THRESHOLD})")
    print(f"  Passes: {'YES' if audit['integrity_score'] >= INTEGRITY_THRESHOLD * 0.5 else 'NO'}")

    if audit['violations']:
        print(f"  Violations:")
        for v in audit['violations']:
            print(f"    {v['cycle']}: error={v['closure_error']:.8f}")

    return net, audit


def demo_corrupted_network():
    """
    Same network but with one corrupted edge — simulating a
    fabrication defect or measurement error.
    """
    print("\n" + "=" * 64)
    print("DEMO 2: Corrupted network (simulated defect)")
    print("=" * 64)

    net = GeometricNetwork()
    n_chambers = 6
    for i in range(n_chambers):
        net.add_node(f"chamber_{i}", value=PHI ** i)

    for i in range(n_chambers - 1):
        net.add_edge(f"chamber_{i}", f"chamber_{i+1}", 
                     "scale", factor=PHI, weight=1.0)
        net.add_edge(f"chamber_{i+1}", f"chamber_{i}",
                     "scale", factor=PHI_INV, weight=1.0)

    # CORRUPTED: chamber_2 -> chamber_3 should be φ, but we set it to 2.0
    # (simulating a part made to wrong dimensions)
    for edge in net.edges:
        if edge.source == "chamber_2" and edge.target == "chamber_3":
            edge.factor = 2.0  # wrong!
            print(f"  INJECTED DEFECT: {edge.source} -> {edge.target} = 2.0 (should be {PHI:.4f})")

    audit = net.audit()
    print(f"\nAudit results:")
    print(f"  Cycles found: {audit['n_cycles']}")
    print(f"  Consistent: {audit['consistent_cycles']}")
    print(f"  Inconsistent: {audit['inconsistent_cycles']}")
    print(f"  Integrity score: {audit['integrity_score']:.6f} (threshold: {INTEGRITY_THRESHOLD})")
    print(f"  Passes: {'YES' if audit['integrity_score'] >= INTEGRITY_THRESHOLD * 0.5 else 'NO'}")

    if audit['violations']:
        print(f"  Violations:")
        for v in audit['violations']:
            print(f"    {v['cycle']}: error={v['closure_error']:.8f} (exceeds tol by {v['exceeds_tol_by']:.1f}x)")

    # Try to correct
    print(f"\n  Attempting correction...")
    modified = net.correct(max_iter=5)
    print(f"  Edges modified: {modified}")

    audit2 = net.audit()
    print(f"  Post-correction integrity: {audit2['integrity_score']:.6f}")

    return net, audit


def demo_resonance():
    """
    Multi-scale resonance on a synthetic spectrum.
    """
    print("\n" + "=" * 64)
    print("DEMO 3: Multi-scale resonance analysis")
    print("=" * 64)

    # Generate a synthetic spectrum: 1/f noise + two resonant peaks
    freqs = [10 * (1.05 ** i) for i in range(200)]  # log-spaced

    # Base: 1/f noise
    amps = [1.0 / f for f in freqs]

    # Add two resonant peaks
    import math
    for i, f in enumerate(freqs):
        # Peak 1: 200 Hz, Q=10
        amps[i] += 0.5 * math.exp(-((f - 200) / 20) ** 2)
        # Peak 2: 800 Hz, Q=15 (anomalous — doesn't fit 1/f)
        amps[i] += 0.3 * math.exp(-((f - 800) / 15) ** 2)

    analyzer = MultiScaleResonance(f_min=10, f_max=1000, bands_per_octave=5)
    result = analyzer.analyze(freqs, amps, expected_slope=-1.0)

    print(f"  Bands analyzed: {result['n_bands']}")
    print(f"  Peaks found: {len(result['peaks'])}")
    for p in result['peaks']:
        print(f"    {p['scale_hz']:.1f} Hz: amp={p['amplitude']:.4f}, Q={p['q_factor']:.1f}")

    print(f"  Anomalies: {len(result['anomalies'])}")
    for a in result['anomalies']:
        print(f"    {a['scale_hz']:.1f} Hz: dev={a['deviation_pct']:.1f}%, severity={a['severity']}")

    print(f"  Anomaly score: {result['anomaly_score']:.4f}")
    print(f"  Fitted slope: {result['fitted_slope']:.4f}")

    return result


def demo_integrity():
    """
    Integrity monitoring with trusted vs. untrusted measurements.
    """
    print("\n" + "=" * 64)
    print("DEMO 4: Integrity monitoring")
    print("=" * 64)

    net = GeometricNetwork()
    net.add_node("sensor_A", value=10.0)
    net.add_node("sensor_B", value=16.18)  # ~10 * φ
    net.add_node("sensor_C", value=26.18)  # ~16.18 * φ

    net.add_edge("sensor_A", "sensor_B", "scale", factor=PHI, weight=1.0)
    net.add_edge("sensor_B", "sensor_C", "scale", factor=PHI, weight=1.0)
    net.add_edge("sensor_A", "sensor_C", "scale", factor=PHI**2, weight=0.9)

    monitor = IntegrityMonitor(net)

    # Good measurements
    monitor.add_measurement("sensor_A", 10.1)
    monitor.add_measurement("sensor_B", 16.2)
    monitor.add_measurement("sensor_C", 26.0)

    report = monitor.full_report()
    print(f"  Measured: {report['n_measured']}, Trusted: {report['n_trusted']}")
    print(f"  Integrity score: {report['integrity_score']:.4f}")
    print(f"  Passes: {'YES' if report['passes'] else 'NO'}")

    # Now corrupt sensor_B
    print(f"\n  INJECTING BAD MEASUREMENT: sensor_B = 25.0 (should be ~16.2)")
    monitor.add_measurement("sensor_B", 25.0)
    report2 = monitor.full_report()
    print(f"  Measured: {report2['n_measured']}, Trusted: {report2['n_trusted']}")
    print(f"  Untrusted nodes: {report2['untrusted_nodes']}")
    print(f"  Integrity score: {report2['integrity_score']:.4f}")
    print(f"  Passes: {'YES' if report2['passes'] else 'NO'}")

    # Reconstruct without the bad measurement
    recon = monitor.reconstruct()
    print(f"  Reconstructed values:")
    for k, v in recon.items():
        print(f"    {k}: {v:.4f}")

    return report2


def demo_fabrication_bridge():
    """
    Convert geometric network to fabrication claims.
    """
    print("\n" + "=" * 64)
    print("DEMO 5: Fabrication claim bridge")
    print("=" * 64)

    net = GeometricNetwork()
    net.add_node("part_L1", value=0.100)  # 100 mm
    net.add_node("part_L2", value=0.162)  # ~100 * φ mm
    net.add_node("part_L3", value=0.262)  # ~162 * φ mm

    net.add_edge("part_L1", "part_L2", "scale", factor=PHI, weight=1.0)
    net.add_edge("part_L2", "part_L3", "scale", factor=PHI, weight=1.0)

    claims = network_to_claims(net, scope_prefix="nautilus_fixture")

    print(f"  Generated {len(claims)} fabrication claims:")
    for c in claims:
        print(f"    {c['scope']}: {c['rate_var']} = {c['value']:.6f} ±{c['tol_frac']*100:.1f}%")

    # Show the integrity claim
    integrity_claims = [c for c in claims if "integrity" in c['scope']]
    if integrity_claims:
        ic = integrity_claims[0]
        print(f"\n  Integrity claim:")
        print(f"    Score: {ic['value']:.4f}")
        print(f"    Threshold: {INTEGRITY_THRESHOLD:.4f}")
        print(f"    Audit: {ic['audit']['consistent_cycles']}/{ic['audit']['n_cycles']} cycles consistent")

    return claims


def main():
    print("\n")
    print("╔" + "═" * 62 + "╗")
    print("║" + " " * 15 + "GEOMETRIC INTELLIGENCE DEMO" + " " * 20 + "║")
    print("╚" + "═" * 62 + "╝")

    demo_nautilus_network()
    demo_corrupted_network()
    demo_resonance()
    demo_integrity()
    demo_fabrication_bridge()

    print("\n" + "=" * 64)
    print("All demos complete.")
    print("=" * 64)


if __name__ == "__main__":
    main()
