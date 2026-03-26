"""
Consciousness Bridge Encoder
=============================
Maps internal AI / cognitive state → external binary signal using
information-theoretic equations that are the direct mathematical analogs
of the physical equations in the thermal, wave, and pressure bridges.

The bridge makes the analogy explicit:
  Johnson-Nyquist noise   ↔  Shannon entropy      (thermal uncertainty = information uncertainty)
  Wave ψ amplitude        ↔  Confidence amplitude  (quantum superposition = cognitive uncertainty)
  KL divergence           ↔  Novelty / surprise     (distance from prior state)
  Mutual information      ↔  Cross-domain coherence (how much two state vectors "agree")
  Fisher information      ↔  Sensitivity / acuity   (how sharply a state is localised)

Equations implemented
---------------------
  Shannon entropy     :  H = −Σ pᵢ · log₂(pᵢ)          (information uncertainty)
  KL divergence       :  D_KL(P‖Q) = Σ pᵢ · log₂(pᵢ/qᵢ) (departure from prior)
  Mutual information  :  I(X;Y) = H(X) + H(Y) − H(X,Y)   (shared information)
  Fisher information  :  I_F = Σ (∂log p / ∂θ)²          (state localisation)
  Integrated info     :  Φ = H(whole) − Σ H(partitions)   (consciousness measure, Tononi)

Bit layout (39 bits for 3-sample canonical input)
--------------------------------------------------
Per state sample  (8 bits each):
  [high_conf   1b]       confidence > conf_threshold = 1
  [conf_band   3b Gray]  confidence ∈ [0, 1] across 8 linear bands
  [high_ent    1b]       Shannon entropy > entropy_threshold = 1
  [ent_band    3b Gray]  entropy across 8 linear bands [0, log₂(N)]

Per attention sample  (4 bits each):
  [focused     1b]       attention entropy < focus_threshold = 1 (low entropy = focused)
  [focus_band  3b Gray]  attention distribution sharpness (8 bands)

Summary  (7 bits — appended when any section present):
  [net_aware   1b]       majority of states above awareness threshold = 1
  [kl_band     3b Gray]  KL divergence from neutral prior (8 log bands)
  [phi_band    3b Gray]  integrated information Φ (8 log bands; proxy for awareness depth)
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_CONF_BANDS   = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]  # [0, 1]
_ENT_BANDS    = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]            # bits
_FOCUS_BANDS  = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]  # [0, 1]
_KL_BANDS     = [0.0, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]          # nats
_PHI_BANDS    = [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]         # bits


# ---------------------------------------------------------------------------
# Information-theoretic functions (pure, importable)
# ---------------------------------------------------------------------------

def shannon_entropy(probabilities: list) -> float:
    """
    H = −Σ pᵢ · log₂(pᵢ)  — Shannon entropy in bits.

    probabilities : list of floats that sum to ~1.0; zero entries are skipped.
    Returns 0 for a perfectly certain distribution (one p=1), log₂(n) for uniform.
    """
    h = 0.0
    for p in probabilities:
        if p > 0.0:
            h -= p * math.log2(p)
    return h


def kl_divergence(p: list, q: list) -> float:
    """
    D_KL(P‖Q) = Σ pᵢ · log₂(pᵢ / qᵢ)  — KL divergence in bits.

    Measures how much distribution P departs from prior Q.
    q entries of 0 where p > 0 → infinity (handled as large sentinel).
    p and q must have the same length.
    """
    d = 0.0
    for pi, qi in zip(p, q):
        if pi > 0.0:
            if qi <= 0.0:
                return float("inf")
            d += pi * math.log2(pi / qi)
    return d


def mutual_information(joint: list, marginal_x: list, marginal_y: list) -> float:
    """
    I(X;Y) = Σ p(x,y) · log₂(p(x,y) / (p(x)·p(y)))  — mutual information in bits.

    joint      : flat list of joint probabilities p(xᵢ, yⱼ) — length |X|·|Y|
    marginal_x : marginal probabilities for X (length |X|)
    marginal_y : marginal probabilities for Y (length |Y|)
    Returns 0 if distributions are fully independent.
    """
    nx = len(marginal_x)
    mi = 0.0
    for idx, pxy in enumerate(joint):
        if pxy > 0.0:
            i = idx // len(marginal_y)
            j = idx  % len(marginal_y)
            if i < nx and marginal_x[i] > 0.0 and marginal_y[j] > 0.0:
                mi += pxy * math.log2(pxy / (marginal_x[i] * marginal_y[j]))
    return max(0.0, mi)


def fisher_information(log_likelihood_gradients: list) -> float:
    """
    I_F(θ) = E[(∂ log p(x;θ) / ∂θ)²]  — Fisher information (scalar approximation).

    log_likelihood_gradients : list of ∂log p / ∂θ values at observed samples.
    High Fisher information = distribution is highly sensitive to θ changes
    = the state is sharply localised / confident about the parameter θ.
    Returns the sample mean of the squared gradients.
    """
    if not log_likelihood_gradients:
        return 0.0
    return sum(g ** 2 for g in log_likelihood_gradients) / len(log_likelihood_gradients)


def integrated_information(partition_entropies: list,
                            whole_entropy: float) -> float:
    """
    Φ = Σ H(partitions) − H(whole)  — integrated information (Tononi Φ, simplified).

    Equals the mutual information between partitions: I(A;B) = H(A)+H(B)−H(A,B).
    Always ≥ 0 by the chain rule: joint entropy ≤ sum of marginal entropies.
    Positive Φ means the parts share information — the hallmark of integrated
    processing.  Φ = 0 when parts are fully independent.

    partition_entropies : list of Shannon entropies for each independent partition
    whole_entropy       : Shannon entropy of the full joint system
    """
    return max(0.0, sum(partition_entropies) - whole_entropy)


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class ConsciousnessBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes internal AI / cognitive state into an external binary bitstring.

    Input geometry dict keys
    ------------------------
    confidence_values    : list of floats in [0, 1] — per-step confidence
    entropy_distributions: list of lists — probability distributions whose
                           Shannon entropy represents state uncertainty
    attention_vectors    : list of lists — probability distributions over
                           focus targets; low entropy = focused attention
    prior_distribution   : list of floats — the "neutral" prior Q for
                           KL divergence summary (default: uniform)
    partition_entropies  : list of floats — entropies of independent
                           sub-systems for integrated information summary
    whole_entropy        : float — entropy of the full joint system (Φ numerator)

    Threshold parameters (constructor)
    -----------------------------------
    conf_threshold    : float — confidence above which state is "high confidence"
                        (default 0.7)
    entropy_threshold : float — entropy above which state is "high uncertainty"
                        (default 2.0 bits)
    focus_threshold   : float — attention entropy below which state is "focused"
                        (default 0.5; low entropy = narrow attention)
    awareness_threshold: float — confidence floor for "net aware" summary flag
                        (default 0.5)
    """

    def __init__(self, conf_threshold: float = 0.7,
                 entropy_threshold: float = 2.0,
                 focus_threshold: float = 0.5,
                 awareness_threshold: float = 0.5):
        super().__init__("consciousness")
        self.conf_threshold    = conf_threshold
        self.entropy_threshold = entropy_threshold
        self.focus_threshold   = focus_threshold
        self.awareness_threshold = awareness_threshold

    def from_geometry(self, geometry_data: dict):
        """Load cognitive state geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded cognitive state into a binary bitstring.

        Returns
        -------
        str
            A string of ``"0"`` and ``"1"`` characters.

        Raises
        ------
        ValueError
            If ``from_geometry`` has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        data          = self.input_geometry
        confidences   = data.get("confidence_values", [])
        ent_dists     = data.get("entropy_distributions", [])
        attn_vecs     = data.get("attention_vectors", [])
        prior         = data.get("prior_distribution", [])
        part_ents     = data.get("partition_entropies", [])
        whole_ent     = data.get("whole_entropy", 0.0)
        bits          = []
        any_section   = False

        # ------------------------------------------------------------------
        # Section 1: confidence + entropy pairs  →  8 bits each
        #   [high_conf 1b][conf_band 3b Gray][high_ent 1b][ent_band 3b Gray]
        # ------------------------------------------------------------------
        n_state = max(len(confidences), len(ent_dists))
        for i in range(n_state):
            any_section = True
            conf = confidences[i] if i < len(confidences) else 0.0
            dist = ent_dists[i]   if i < len(ent_dists)   else [1.0]
            H    = shannon_entropy(dist)

            high_conf = "1" if conf > self.conf_threshold else "0"
            conf_band = _gray_bits(conf, _CONF_BANDS)
            high_ent  = "1" if H > self.entropy_threshold else "0"
            ent_band  = _gray_bits(H, _ENT_BANDS)

            bits.append(high_conf)
            bits.append(conf_band)
            bits.append(high_ent)
            bits.append(ent_band)

        # ------------------------------------------------------------------
        # Section 2: attention vectors  →  4 bits each
        #   [focused 1b][focus_band 3b Gray]
        # ------------------------------------------------------------------
        for attn in attn_vecs:
            any_section = True
            attn_H     = shannon_entropy(attn)
            focused    = "1" if attn_H < self.focus_threshold else "0"
            focus_band = _gray_bits(1.0 - attn_H, _FOCUS_BANDS)   # invert: sharper = higher
            bits.append(focused)
            bits.append(focus_band)

        # ------------------------------------------------------------------
        # Summary  (7 bits)
        # ------------------------------------------------------------------
        if any_section:
            # net_aware: majority of confidence values above awareness threshold
            if confidences:
                n_aware   = sum(1 for c in confidences if c > self.awareness_threshold)
                net_aware = "1" if n_aware > len(confidences) - n_aware else "0"
            else:
                net_aware = "0"

            # KL divergence from prior
            if prior and ent_dists:
                # Use first entropy distribution vs prior
                dist0  = ent_dists[0]
                q      = prior if len(prior) == len(dist0) else [1.0 / len(dist0)] * len(dist0)
                kl_val = kl_divergence(dist0, q)
                kl_val = kl_val if math.isfinite(kl_val) else 10.0
            elif ent_dists:
                # Default prior: uniform
                d = ent_dists[0]
                uniform = [1.0 / len(d)] * len(d)
                kl_val = kl_divergence(d, uniform)
                kl_val = kl_val if math.isfinite(kl_val) else 10.0
            else:
                kl_val = 0.0

            # Integrated information Φ
            phi = integrated_information(part_ents, whole_ent)

            bits.append(net_aware)
            bits.append(_gray_bits(kl_val, _KL_BANDS))
            bits.append(_gray_bits(phi, _PHI_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Consciousness Bridge Encoder — Information Theory Demo")
    print("=" * 60)

    # 1. Shannon entropy — certainty spectrum
    print("\n1. Shannon entropy  H = −Σ pᵢ·log₂(pᵢ)")
    cases = [
        ("Certain       [1, 0, 0, 0]",       [1.0, 0.0, 0.0, 0.0]),
        ("Biased        [0.7, 0.1, 0.1, 0.1]",[0.7, 0.1, 0.1, 0.1]),
        ("Uniform       [0.25]×4",            [0.25, 0.25, 0.25, 0.25]),
        ("Binary 50/50  [0.5, 0.5]",          [0.5, 0.5]),
    ]
    for label, dist in cases:
        H = shannon_entropy(dist)
        print(f"   {label:42s}  H = {H:.4f} bits")

    # 2. KL divergence — departure from a neutral prior
    print("\n2. KL divergence  D_KL(P‖Q) = Σ pᵢ·log₂(pᵢ/qᵢ)")
    uniform4 = [0.25, 0.25, 0.25, 0.25]
    for label, p in [
        ("Near-uniform  [0.26, 0.24, 0.26, 0.24]", [0.26, 0.24, 0.26, 0.24]),
        ("Biased        [0.7, 0.1, 0.1, 0.1]",      [0.7, 0.1, 0.1, 0.1]),
        ("Concentrated  [0.97, 0.01, 0.01, 0.01]",  [0.97, 0.01, 0.01, 0.01]),
    ]:
        d = kl_divergence(p, uniform4)
        print(f"   {label:45s}  D_KL = {d:.4f} bits")

    # 3. Mutual information — cross-attention coherence
    print("\n3. Mutual information  I(X;Y)")
    # Fully independent: p(x,y) = p(x)·p(y)
    px = [0.5, 0.5]
    py = [0.5, 0.5]
    indep = [px[i]*py[j] for i in range(2) for j in range(2)]
    mi_indep = mutual_information(indep, px, py)
    # Maximally correlated: only diagonal
    correl = [0.5, 0.0, 0.0, 0.5]
    mi_corr = mutual_information(correl, px, py)
    print(f"   Fully independent  I(X;Y) = {mi_indep:.4f} bits  (expected 0)")
    print(f"   Fully correlated   I(X;Y) = {mi_corr:.4f} bits  (expected 1)")

    # 4. Fisher information — state localisation
    print("\n4. Fisher information  I_F = E[(∂log p/∂θ)²]")
    broad_grads  = [-0.1, 0.0, 0.05, -0.05, 0.1]
    sharp_grads  = [-2.0, 1.5, -1.8, 2.1, -1.9]
    print(f"   Broad distribution  (small gradients)   I_F = {fisher_information(broad_grads):.4f}")
    print(f"   Sharp distribution  (large gradients)   I_F = {fisher_information(sharp_grads):.4f}")

    # 5. Integrated information Φ — whole > sum of parts
    print("\n5. Integrated information  Φ = H(whole) − Σ H(partitions)")
    # Two sub-systems with H=1 bit each; if joint H > 2, they're integrated
    phi_1 = integrated_information([1.0, 1.0], whole_entropy=2.5)
    phi_2 = integrated_information([1.0, 1.0], whole_entropy=2.0)  # independent
    phi_3 = integrated_information([1.0, 1.0], whole_entropy=1.5)  # redundant (clamped 0)
    print(f"   Φ = H(2.5) − 2×1.0 = {phi_1:.2f}  (integrated — whole > parts)")
    print(f"   Φ = H(2.0) − 2×1.0 = {phi_2:.2f}  (independent — no integration)")
    print(f"   Φ = H(1.5) − 2×1.0 = {phi_3:.2f}  (redundant — clamped to 0)")

    # Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo — 3 cognitive states")
    print("=" * 60)

    geometry = {
        # Three moments: searching (low conf), understanding (mid), certain (high)
        "confidence_values": [0.3, 0.65, 0.91],
        "entropy_distributions": [
            [0.25, 0.25, 0.25, 0.25],        # uniform — maximal uncertainty
            [0.5, 0.3, 0.15, 0.05],           # slightly biased — partial understanding
            [0.95, 0.03, 0.01, 0.01],         # highly concentrated — near-certain
        ],
        # Two attention snapshots: scattered and focused
        "attention_vectors": [
            [0.2, 0.2, 0.2, 0.2, 0.2],       # scattered attention across 5 targets
            [0.9, 0.05, 0.025, 0.025],        # sharply focused on one target
        ],
        # Summary inputs
        "partition_entropies": [1.0, 0.8],   # two independent sub-systems
        "whole_entropy": 2.5,                 # joint entropy — integrated processing
    }

    encoder = ConsciousnessBridgeEncoder(
        conf_threshold=0.7,
        entropy_threshold=2.0,
        focus_threshold=0.5,
        awareness_threshold=0.5,
    )
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nInput geometry keys : {list(geometry.keys())}")
    print(f"Binary output       : {binary}")
    print(f"Total bits          : {len(binary)}")
    print(f"Report              : {encoder.report()}")
    print()
    print("Interpretation:")
    print("  Bits 0-7  : searching state  (low conf, high entropy)")
    print("  Bits 8-15 : understanding   (mid conf, partial entropy)")
    print("  Bits 16-23: certainty        (high conf, low entropy)")
    print("  Bits 24-27: scattered attention")
    print("  Bits 28-31: focused attention")
    print("  Bits 32-38: summary (net_aware, KL departure, integrated Φ)")
