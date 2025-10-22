# Addendum: Entropy and Resonance Analyzer
# Optional plugin for BridgeOrchestrator
# Computes entropy, φ-ratio correlations, and cross-domain phase coherence.

import numpy as np
from math import log2, sqrt

class EntropyResonanceAnalyzer:
    """
    Optional analyzer that can attach to BridgeOrchestrator.
    Provides deeper diagnostics:
      - Shannon entropy of the master bitstring
      - φ (golden ratio) resonance check
      - Cross-domain correlation matrix
    """

    def __init__(self, phi=1.6180339887):
        self.phi = phi
        self.results = {}

    def attach_to(self, orchestrator):
        """Attach analyzer to a BridgeOrchestrator instance."""
        self.orchestrator = orchestrator
        return self

    def compute_entropy(self):
        """Calculate Shannon entropy of the merged bitstring."""
        if not self.orchestrator.master_bitstring:
            raise ValueError("No master bitstring found.")
        bits = np.array([int(b) for b in self.orchestrator.master_bitstring])
        p = np.mean(bits)
        H = - (p * log2(p) + (1 - p) * log2(1 - p)) if 0 < p < 1 else 0
        self.results["entropy_bits"] = H
        return H

    def phi_resonance_index(self):
        """Estimate φ-resonance via bit periodicity pattern."""
        bits = np.array([int(b) for b in self.orchestrator.master_bitstring])
        n = len(bits)
        autocorr = np.correlate(bits - np.mean(bits), bits - np.mean(bits), mode="full")
        autocorr = autocorr[n-1:]
        phi_index = int(round(n / self.phi))
        resonance = autocorr[phi_index] / autocorr[0] if phi_index < len(autocorr) else 0
        self.results["phi_resonance"] = resonance
        return resonance

    def cross_domain_coherence(self):
        """Compute simple pairwise correlation between domain bitstrings."""
        names = list(self.orchestrator.results.keys())
        bitstreams = [list(map(int, self.orchestrator.results[n]["bits"])) for n in names]
        m = len(names)
        corr = np.zeros((m, m))
        for i in range(m):
            for j in range(m):
                if len(bitstreams[i]) != len(bitstreams[j]):
                    min_len = min(len(bitstreams[i]), len(bitstreams[j]))
                    a = bitstreams[i][:min_len]
                    b = bitstreams[j][:min_len]
                else:
                    a, b = bitstreams[i], bitstreams[j]
                corr[i, j] = np.corrcoef(a, b)[0, 1]
        self.results["coherence_matrix"] = corr.tolist()
        self.results["domains"] = names
        return corr

    def full_analysis(self):
        """Run all available analyses."""
        return {
            "entropy_bits": self.compute_entropy(),
            "phi_resonance": self.phi_resonance_index(),
            "coherence_matrix": self.cross_domain_coherence().tolist(),
        }

    def report(self):
        """Return results."""
        return self.results

  ##Integration (optional)

##You can activate this analyzer only when needed:

from bridge.bridge_orchestrator import BridgeOrchestrator
from bridge.addendum_entropy_analyzer import EntropyResonanceAnalyzer

orchestrator = BridgeOrchestrator()
# (register and run all encoders as usual...)

# Optional addendum:
analyzer = EntropyResonanceAnalyzer().attach_to(orchestrator)
analysis = analyzer.full_analysis()

print("Entropy (bits):", analysis["entropy_bits"])
print("Φ-resonance index:", analysis["phi_resonance"])
print("Cross-domain coherence matrix:")
for row in analysis["coherence_matrix"]:
    print(row)
