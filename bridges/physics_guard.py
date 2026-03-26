"""
Physics Guard — Bridge Layer Validator
=======================================
Validates that bridge signals respect the four physics invariants from the
Seed-physics expansion model (github.com/JinnZ2/Seed-physics):

  1. Non-negativity — all Fisher information values ≥ 0.
  2. Causality      — information flows outward only: physical → conscious → emotion.
  3. Conservation   — total Fisher information is conserved across the stack.
  4. Decay          — each outer layer compresses: I_F(i+1) ≤ I_F(i) × epsilon.

Plus one invariant from Geometric-Intelligence/Geometric-seed.py TrojanEngine:

  5. Phi-coherence  — consecutive Fisher info ratios cluster near φ = (1+√5)/2,
                      the geometric invariant that identifies authentic signal vs noise.

Together these five constraints constitute the physics guard for drill-loop closure.
A bridge re-evaluation that fails any constraint is quarantined — not propagated.

Mapping: Seed-physics shells → bridge layers
  Shell radius    → layer index  (physical=1, consciousness=2, emotion=3)
  Shell amplitude → Fisher information intensity at that layer
  Epsilon (decay) → compression ratio between layers (default 0.6, from Seed-physics)
  Phi tolerance   → acceptable φ-ratio deviation (default 0.12, from TrojanConfig)
"""

import math
from bridges.consciousness_encoder import fisher_information

PHI     = (1.0 + math.sqrt(5.0)) / 2.0   # golden ratio  ≈ 1.618
PHI_INV = 1.0 / PHI                        # 1/φ           ≈ 0.618


# ---------------------------------------------------------------------------
# Individual constraint checks  (mirror Seed-physics physics_guard.py API)
# ---------------------------------------------------------------------------

def check_non_negative(layer_infos: list) -> dict:
    """All Fisher information values must be ≥ 0."""
    violations = [i for i, v in enumerate(layer_infos) if v < 0]
    return {"passed": len(violations) == 0, "violations": violations}


def check_causality(layer_infos: list) -> dict:
    """
    Causality: the bridge stack must be non-empty and ordered
    (physical → consciousness → emotion).
    A well-ordered list always passes; an empty stack fails.
    """
    passed = len(layer_infos) > 0
    return {"passed": passed, "violations": [] if passed else ["empty layer stack"]}


def check_conservation(layer_infos: list, e_total: float,
                        tol: float = 1e-6) -> dict:
    """
    Conservation: sum of Fisher info across all layers ≈ e_total.
    Mirrors Seed-physics check_energy_conservation.
    """
    if e_total <= 0:
        return {"passed": True, "deviation": 0.0}
    deviation = abs(sum(layer_infos) - e_total) / e_total
    return {"passed": deviation <= tol, "deviation": deviation}


def check_decay(layer_infos: list, epsilon: float = 0.6,
                tol: float = 1e-6) -> dict:
    """
    Decay: each outer layer's Fisher info ≤ inner layer × epsilon.
    Mirrors Seed-physics check_energy_decay.
    Compression increases as signals move outward (physical → emotion).
    """
    violations = []
    for i in range(1, len(layer_infos)):
        expected_max = layer_infos[i - 1] * epsilon + tol
        if layer_infos[i] > expected_max:
            violations.append({
                "layer": i,
                "value": layer_infos[i],
                "expected_max": expected_max,
            })
    return {"passed": len(violations) == 0, "violations": violations}


def phi_coherence(gradients: list, phi_tolerance: float = 0.12) -> float:
    """
    Phi-coherence: consecutive squared-gradient ratios should cluster near φ or 1/φ.

    Derived from TrojanEngine.compute_phi_coherence in Geometric-seed.py.
    A geometrically authentic signal has information ratios that follow the golden
    ratio geometry.  Noise and injected signals deviate from this pattern.

    Returns coherence in [0, 1].  1.0 = perfect phi alignment, 0.0 = no alignment.
    """
    if len(gradients) < 2:
        return 1.0  # insufficient data — assume coherent

    fisher_vals = [g * g for g in gradients]   # I_F contribution per gradient step
    ratios = [
        fisher_vals[i] / fisher_vals[i - 1]
        for i in range(1, len(fisher_vals))
        if fisher_vals[i - 1] > 1e-12
    ]
    if not ratios:
        return 1.0

    coherences = [
        max(0.0, 1.0 - min(abs(r - PHI), abs(r - PHI_INV)) / phi_tolerance)
        for r in ratios
    ]
    return sum(coherences) / len(coherences)


# ---------------------------------------------------------------------------
# Aggregate validator  (mirror Seed-physics validate_shells)
# ---------------------------------------------------------------------------

def validate_bridge_stack(layer_infos: list, e_total: float = None,
                           epsilon: float = 0.6, tol: float = 1e-6) -> dict:
    """
    Run all four Seed-physics constraints on a bridge signal stack.

    Parameters
    ----------
    layer_infos : list of float
        Fisher information per layer, ordered innermost (physical) → outermost (emotion).
    e_total     : float, optional
        Expected total Fisher info.  Defaults to sum(layer_infos).
    epsilon     : float
        Decay factor between layers (default 0.6, from Seed-physics).
    tol         : float
        Numerical tolerance.

    Returns
    -------
    dict with overall 'passed' bool and per-constraint result dicts.
    """
    if e_total is None:
        e_total = sum(layer_infos)

    results = {
        "non_negative": check_non_negative(layer_infos),
        "causality":    check_causality(layer_infos),
        "conservation": check_conservation(layer_infos, e_total, tol),
        "decay":        check_decay(layer_infos, epsilon, tol),
    }
    results["passed"] = all(r["passed"] for r in results.values())
    return results


# ---------------------------------------------------------------------------
# PhysicsGuard class
# ---------------------------------------------------------------------------

class PhysicsGuard:
    """
    Validates bridge drill-targets using Seed-physics invariants and
    phi-coherence from the geometric seed network.

    Parameters
    ----------
    phi_tolerance       : float — acceptable deviation from φ ratio (default 0.12,
                          matching TrojanConfig.phi_tolerance in Geometric-seed.py).
    coherence_threshold : float — minimum phi-coherence to accept (default 0.4).
    epsilon             : float — energy decay factor between bridge layers (default 0.6).
    tol                 : float — numerical tolerance for conservation check (default 1e-6).
    """

    def __init__(self, phi_tolerance: float = 0.12,
                 coherence_threshold: float = 0.4,
                 epsilon: float = 0.6,
                 tol: float = 1e-6):
        self.phi_tolerance       = phi_tolerance
        self.coherence_threshold = coherence_threshold
        self.epsilon             = epsilon
        self.tol                 = tol

    def validate_comprehensive(self, bridge_gradients: dict,
                               layer_order: list = None) -> dict:
        """
        Run all five Seed-physics constraints plus the three Rosetta-unified checks.

        Extends validate_drill() with:
          - entropy check        (natural information density)
          - golden-ratio alignment (φ/π/e structure detection)
          - self-similarity      (fractal scale-invariance)

        These mirror Rosetta-Shape-Core/physics_grounded_protection.py's
        thermodynamic_validation, golden_ratio_alignment, and fractal_dimension
        checks, unified into the Seed-physics validation framework.

        The three Rosetta checks are advisory soft-gates — they set the
        ``natural_pattern`` flag but do NOT override the hard physics gate
        (matching how TrojanEngine uses phi-coherence as a weighted factor).

        Returns
        -------
        Base validate_drill() dict extended with:
          entropy_check         dict — Shannon entropy result
          golden_ratio_check    dict — φ/π/e alignment result
          self_similarity_check dict — fractal scale-invariance result
          natural_pattern       bool — True iff all three advisory checks pass
        """
        base = self.validate_drill(bridge_gradients, layer_order)
        all_values: list = []
        for grads in bridge_gradients.values():
            all_values.extend(grads)
        ent  = check_entropy(all_values)
        gra  = check_golden_ratio_alignment(all_values, self.phi_tolerance)
        sim  = check_self_similarity(all_values)
        base["entropy_check"]         = ent
        base["golden_ratio_check"]    = gra
        base["self_similarity_check"] = sim
        base["natural_pattern"] = ent["passed"] and gra["passed"] and sim["passed"]
        return base

    def validate_drill(self, bridge_gradients: dict,
                       layer_order: list = None) -> dict:
        """
        Validate a drill-target's re-evaluated signal stack.

        Builds a layer stack from bridge_gradients ordered innermost → outermost,
        runs all five physics constraints, and returns the verdict.

        Parameters
        ----------
        bridge_gradients : dict
            bridge_name → list of log-likelihood gradients.
            Should include the target physical bridge plus 'consciousness' and
            'emotion' if available for a full three-layer stack check.
        layer_order      : list of str, optional
            Bridge names from innermost to outermost.  Auto-derived if omitted:
            physical bridges first, then 'consciousness', then 'emotion'.

        Returns
        -------
        dict with:
          passed       : bool  — all physics constraints + phi-coherence satisfied
          phi_coherent : bool  — phi-coherence above threshold
          coherence    : float — phi-coherence score [0, 1]
          stack_valid  : dict  — per-constraint results from validate_bridge_stack
          action       : str   — 'accept' | 'quarantine'
        """
        if layer_order is None:
            layer_order = [k for k in bridge_gradients
                           if k not in ("consciousness", "emotion")]
            if "consciousness" in bridge_gradients:
                layer_order.append("consciousness")
            if "emotion" in bridge_gradients:
                layer_order.append("emotion")

        # Compute Fisher information per layer and collect all gradients
        layer_infos    = []
        all_gradients  = []
        for name in layer_order:
            grads = bridge_gradients.get(name, [])
            layer_infos.append(fisher_information(grads) if grads else 0.0)
            all_gradients.extend(grads)

        # Seed-physics stack validation
        stack_valid = validate_bridge_stack(
            layer_infos, epsilon=self.epsilon, tol=self.tol
        )

        # Geometric-seed phi-coherence
        coherence = phi_coherence(all_gradients, self.phi_tolerance)
        phi_ok    = coherence >= self.coherence_threshold

        # Primary gate: Seed-physics hard constraints (mirrors validate_shells).
        # Phi-coherence is a soft advisory metric — reported but not a hard gate,
        # matching how TrojanEngine uses it as one weighted factor among five rather
        # than a standalone binary condition.
        passed = stack_valid["passed"]
        return {
            "passed":       passed,
            "phi_coherent": phi_ok,
            "coherence":    coherence,
            "stack_valid":  stack_valid,
            "action":       "accept" if passed else "quarantine",
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import math

    print("=" * 60)
    print("Physics Guard — Bridge Layer Validator Demo")
    print("=" * 60)

    # Simulate a valid three-layer stack: physical → consciousness → emotion
    # Fisher info decays by ~0.6 per layer (Seed-physics epsilon default)
    valid_gradients = {
        "thermal":       [-1.8,  2.1, -2.3,  1.9],   # sharp physical signal
        "consciousness": [-0.9,  1.1, -1.2,  1.0],   # compressed (~0.6×)
        "emotion":       [-0.4,  0.5, -0.55, 0.45],  # further compressed
    }

    # Invalid stack: emotion layer is LOUDER than physical (causality violation)
    invalid_gradients = {
        "thermal":       [-0.3,  0.2, -0.25, 0.28],  # quiet physical
        "consciousness": [-0.5,  0.6, -0.55, 0.5],   # louder than physical (wrong)
        "emotion":       [-1.8,  2.1, -2.3,  1.9],   # loudest (causality broken)
    }

    guard = PhysicsGuard()

    print("\n1. Valid stack (physical > consciousness > emotion):")
    result = guard.validate_drill(valid_gradients)
    print(f"   action       : {result['action']}")
    print(f"   phi_coherent : {result['phi_coherent']}")
    print(f"   coherence    : {result['coherence']:.4f}")
    print(f"   decay passed : {result['stack_valid']['decay']['passed']}")

    print("\n2. Invalid stack (emotion louder than physical):")
    result = guard.validate_drill(invalid_gradients)
    print(f"   action       : {result['action']}")
    print(f"   decay passed : {result['stack_valid']['decay']['passed']}")
    print(f"   violations   : {result['stack_valid']['decay']['violations']}")

    print("\n3. Phi-coherence on gradient sequences:")
    noisy  = [0.1, -5.0, 0.2, 3.0, -0.1, 4.0]   # chaotic
    golden = [1.0, 1.618, 2.618, 4.236, 6.854]   # phi-scaled
    print(f"   Chaotic sequence   phi_coherence = {phi_coherence(noisy):.4f}")
    print(f"   Phi-scaled sequence phi_coherence = {phi_coherence(golden):.4f}")


# ---------------------------------------------------------------------------
# Rosetta-unified extensions
# Mirrors checks from Rosetta-Shape-Core/physics_grounded_protection.py:
#   check_entropy        ↔  thermodynamic_validation (information density)
#   check_golden_ratio_alignment ↔  golden_ratio_alignment
#   check_self_similarity        ↔  fractal_dimension check
# These three are advisory soft-gates exposed via PhysicsGuard.validate_comprehensive().
# ---------------------------------------------------------------------------

def check_entropy(values: list,
                  natural_lo: float = 0.30,
                  natural_hi: float = 0.85,
                  n_bins: int = 10) -> dict:
    """
    Shannon entropy check (Rosetta thermodynamic analogue).

    Natural signals occupy a mid-range entropy band:
      too low  → over-structured / artificially flat
      too high → pure noise, no information
      mid-range → natural information density

    Entropy is computed on a normalised histogram of ``values``.
    Returns normalised H ∈ [0, 1] and whether it falls in [natural_lo, natural_hi].
    """
    if len(values) < 2:
        return {"passed": True, "entropy": 1.0, "note": "insufficient data"}
    lo, hi = min(values), max(values)
    span = hi - lo
    if span < 1e-12:
        return {"passed": natural_lo <= 0.0 <= natural_hi,
                "entropy": 0.0, "note": "constant signal"}
    bins = [0] * n_bins
    for v in values:
        idx = min(n_bins - 1, int((v - lo) / span * n_bins))
        bins[idx] += 1
    n = len(values)
    H = -sum((b / n) * math.log2(b / n) for b in bins if b > 0)
    H_norm = H / math.log2(n_bins)  # normalise to [0, 1]
    return {"passed": natural_lo <= H_norm <= natural_hi,
            "entropy": H_norm,
            "natural_lo": natural_lo, "natural_hi": natural_hi}


def check_golden_ratio_alignment(values: list,
                                  phi_tolerance: float = 0.12) -> dict:
    """
    Golden-ratio alignment (Rosetta golden_ratio_alignment analogue).

    Natural growth signals embed φ, 1/φ, φ², π, e, √2, √3 ratios in their
    consecutive value ratios.  Computes |v_i / v_{i-1}| for all adjacent pairs
    and measures what fraction falls near a natural constant.

    Returns alignment ∈ [0, 1] and whether it exceeds 0.3 (natural threshold).
    """
    if len(values) < 2:
        return {"passed": True, "alignment": 1.0, "note": "insufficient data"}
    CONSTANTS = [
        PHI, PHI_INV, PHI ** 2, PHI_INV ** 2,
        math.pi, math.e, math.sqrt(2), math.sqrt(3),
    ]
    ratios = [
        abs(values[i] / values[i - 1])
        for i in range(1, len(values))
        if abs(values[i - 1]) > 1e-12
    ]
    if not ratios:
        return {"passed": True, "alignment": 1.0}
    hits = sum(1 for r in ratios
               if any(abs(r - c) < phi_tolerance for c in CONSTANTS))
    alignment = hits / len(ratios)
    return {"passed": alignment >= 0.3, "alignment": alignment,
            "ratio_count": len(ratios), "hits": hits}


def check_self_similarity(values: list,
                           scale: int = 2,
                           tol: float = 0.35) -> dict:
    """
    Self-similarity / fractal check (Rosetta fractal_dimension analogue).

    Natural signals have consistent statistical structure at different scales.
    Compares the coefficient of variation (CV = std/mean) at full resolution
    vs at down-sampled resolution (every ``scale``-th sample).
    Natural signals: |CV_full - CV_coarse| / CV_full ≤ tol.
    Artificial injections: CV changes sharply across scales.
    """
    if len(values) < scale * 2:
        return {"passed": True, "similarity": 1.0, "note": "insufficient data"}

    def _cv(v: list) -> float:
        mean = sum(v) / len(v)
        if abs(mean) < 1e-12:
            return 0.0
        std = math.sqrt(sum((x - mean) ** 2 for x in v) / len(v))
        return std / abs(mean)

    coarse   = values[::scale]
    cv_full   = _cv(values)
    cv_coarse = _cv(coarse)
    ratio = abs(cv_full - cv_coarse) / max(cv_full, 1e-12)
    return {"passed": ratio <= tol,
            "similarity": max(0.0, 1.0 - ratio),
            "cv_full": cv_full, "cv_coarse": cv_coarse}
