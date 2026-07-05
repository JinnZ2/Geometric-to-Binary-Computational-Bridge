#!/usr/bin/env python3
"""
faithful_quantum_resilience_sweep.py

Uses the REAL models (QuantumBridge, LatticeSimulator, BandEnvironment)
to produce the same resilience curves that the full Explorer would generate,
without the branching tree overhead.

Sweep:
  - Paradigm: quantum
  - Chip: kagome lattice
  - Entropy increased stepwise (bands degrade)
  - At each step:
      * QuantumBridge.entangle_confidence_noise(confidence=0.9, noise=entropy)
        → extract advantage
      * LatticeSimulator.simulate_interference(frequency=24.0)
        → extract signal_integrity
  - Stop when advantage < 0.10 or integrity < 0.05
"""

import math
import random
import sys
import os

# Make sure the parent directory is on the path so we can import gb_explorer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gb_explorer import (
    BandEnvironment,
    QuantumBridge,
    LatticeSimulator,
    ChipArchitecture,
)

# ----------------------------------------------------------------------
# Sweep function
# ----------------------------------------------------------------------

def run_quantum_resilience_sweep(steps=20, entropy_increment=0.5):
    """Run a faithful sweep using the real QuantumBridge and Kagome lattice."""

    # Initialise real objects
    bands = BandEnvironment()                         # starts clean
    bridge = QuantumBridge(bands=bands)               # quantum paradigm
    chip = ChipArchitecture(geometry="kagome")        # kagome crystal-inspired lattice

    print(f"{'Entropy':<10} | {'Advantage':<10} | {'Signal Integrity':<20}")
    print("-" * 48)

    for _ in range(steps):
        # Inject entropy → bands widen
        bands.apply_entropy_event(entropy_increment)
        current_entropy = bands.entropy_level

        # 1. Quantum advantage via entanglement
        #    Use entropy_level as the noise parameter (0..1)
        noise = min(1.0, current_entropy)
        result = bridge.entangle_confidence_noise(confidence=0.9, noise_level=noise)
        advantage = result["advantage"]

        # 2. Signal integrity on the kagome chip under 24 GHz interference
        interference = chip.simulator.simulate_interference(frequency=24.0)
        integrity = interference["signal_integrity"]

        print(f"{current_entropy:<10.2f} | {advantage:<10.3f} | {integrity:<20.4f}")

        if advantage < 0.10 or integrity < 0.05:
            print("\n[!] BREAKDOWN DETECTED")
            print(f"    Entropy Level : {current_entropy:.2f}")
            print(f"    Advantage     : {advantage:.3f}")
            print(f"    Integrity     : {integrity:.4f}")
            break

# ----------------------------------------------------------------------
# Demo
# ----------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)   # for reproducibility (kagome geometry is deterministic)
    run_quantum_resilience_sweep(steps=20, entropy_increment=0.5)
