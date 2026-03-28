"""
Cyclic Bridge Encoder
=====================
Encodes cyclic field states (from the Cyclic-programming language model)
into binary using core field-dynamics equations and Gray-coded magnitude
bands for all continuous quantities.

Equations implemented
---------------------
  Resonance strength      :  R = exp(−|f₁ − f₂|)          (frequency coupling)
  Regeneration gain       :  C' = C·(1 + 0.3·E_in / 100)  (capacity growth rate)
  Phase-transition cost   :  E_cost = |Δ_phase| × 10       (energy to change phase)
  Fractal energy split    :  E_spawn = E_total / 2^depth   (energy per fractal copy)
  Spatial gradient        :  ∇E = (E₁ − E₂) / d           (inter-field energy flow)

Bit layout (39 bits for 3-field canonical input)
-------------------------------------------------
Per field  (8 bits × 3 fields = 24 bits):
  [phase_state  3b Gray]  crystalline(000)→normal(001)→liquid(011)→gas(010)→plasma(110)
  [energy_mag   3b Gray]  total_energy across 8 log bands (0.001 → 10 000 J)
  [coherence    2b Gray]  quantum_coherence in 4 linear bands ([0, 0.25, 0.5, 0.75])

Dynamics summary  (9 bits):
  [entropy_band  3b Gray]  mean entropy across 8 log bands (1e-6 → 100 J/K)
  [capacity_band 3b Gray]  mean regenerative capacity across 8 log bands (0.01 → 1000)
  [freq_band     3b Gray]  mean oscillation frequency across 8 log bands (0.01 → 1e6 Hz)

Interaction summary  (6 bits):
  [resonance_band 3b Gray]  R(f₀, f₁) across 8 linear bands ([0, 0.125, ..., 0.875])
  [any_entangled  1b]       any field has a quantum-entanglement partner = 1
  [fractal_active 1b]       any field has fractal_depth > 0 = 1
  [phase_spread   1b]       fields span more than one distinct phase state = 1

License: CC-BY-4.0
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Phase order
# ---------------------------------------------------------------------------

_PHASE_ORDER = ["crystalline", "normal", "liquid", "gas", "plasma"]

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------

_ENERGY_BANDS    = [0.0, 0.001, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0]   # J
_ENTROPY_BANDS   = [0.0, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0, 100.0]         # J/K
_CAPACITY_BANDS  = [0.0, 0.01, 0.1, 0.5, 1.0, 2.0, 10.0, 1000.0]          # dimensionless
_FREQ_BANDS      = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0, 1e4, 1e6]           # Hz
_RESONANCE_BANDS = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]     # [0, 1]
_COHERENCE_BANDS = [0.0, 0.25, 0.5, 0.75]                                  # 4 bands → 2 bits


# ---------------------------------------------------------------------------
# Phase-state Gray encoding helper
# ---------------------------------------------------------------------------
# Standard Gray codes for phase indices 0-4:
#   crystalline=0 → G(0)=000
#   normal     =1 → G(1)=001
#   liquid     =2 → G(2)=011
#   gas        =3 → G(3)=010
#   plasma     =4 → G(4)=110
# Adjacent phases differ by exactly 1 bit.

def _phase_bits(phase_state: str) -> str:
    idx = _PHASE_ORDER.index(phase_state) if phase_state in _PHASE_ORDER else 1
    g   = idx ^ (idx >> 1)
    return format(g, "03b")


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def resonance_strength(f1: float, f2: float) -> float:
    """
    Frequency-match resonance coupling: R = exp(−|f₁ − f₂|).

    Returns 1.0 when frequencies are identical; approaches 0 for large mismatch.
    Implements the coupling kernel from FieldState.resonate_with() — resonance
    amplification = 1 + 0.2·R, phase-lock fires when R > 0.5.
    """
    return math.exp(-abs(f1 - f2))


def regeneration_capacity_gain(capacity: float, input_energy: float) -> float:
    """
    New capacity after one regeneration cycle:
        C' = C · (1 + 0.3 · max(E_in, 0) / 100)

    Implements the 30 % capacity-growth fraction from FieldState.regenerate().
    Returns a value >= capacity for non-negative input_energy.
    """
    return capacity * (1.0 + 0.3 * max(float(input_energy), 0.0) / 100.0)


def phase_transition_cost(from_phase: str, to_phase: str) -> float:
    """
    Energy cost (J) to transition between phase states:
        E_cost = |idx(target) − idx(source)| × 10

    Matches the phase_diff × 10.0 formula in FieldState.phase_transition().
    Returns 0.0 when from_phase == to_phase.  Unknown phases map to 'normal' (idx 1).
    """
    src = _PHASE_ORDER.index(from_phase) if from_phase in _PHASE_ORDER else 1
    tgt = _PHASE_ORDER.index(to_phase)   if to_phase   in _PHASE_ORDER else 1
    return abs(tgt - src) * 10.0


def fractal_energy_per_spawn(total_energy: float, depth: int) -> float:
    """
    Energy carried by each fractal copy at recursion depth:
        E_spawn = E_total / 2^depth

    depth=0 → 1 copy with full energy;  depth=3 → 8 copies at E/8 each.
    Derived from FieldState.fractal_spawn() energy partitioning.
    """
    return float(total_energy) / max(2 ** depth, 1)


def spatial_gradient_strength(E1: float, E2: float, distance: float) -> float:
    """
    Inter-field energy gradient: ∇E = (E₁ − E₂) / max(d, 0.01).

    Positive when field 1 has higher energy — drives flow from field 1 to field 2.
    Implements the gradient_strength calculation in FieldState.spatial_gradient_flow().
    """
    return (float(E1) - float(E2)) / max(float(distance), 0.01)


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class CyclicBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes cyclic field geometry into a 39-bit binary bitstring.

    Input geometry dict keys
    ------------------------
    total_energy      : list[float] — field energy values (J)
    entropy           : list[float] — entropy per field (J/K)
    quantum_coherence : list[float] — superposition measure in [0, 1]
    capacity          : list[float] — regenerative capacity (dimensionless, ≥ 0)
    phase_state       : list[str]   — "crystalline"/"normal"/"liquid"/"gas"/"plasma"
    frequency         : list[float] — oscillation frequency (Hz)
    fractal_depth     : list[int]   — recursive depth 0–7
    entangled         : list[bool]  — has quantum-entanglement partner

    All lists may be shorter than 3; missing entries are padded with safe defaults.
    """

    def __init__(self):
        super().__init__("cyclic")

    def from_geometry(self, geometry_data: dict):
        """Load cyclic field data from a geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded cyclic field geometry into a binary bitstring.

        Returns
        -------
        str
            A string of ``"0"`` and ``"1"`` characters (39 bits for 3-field input).

        Raises
        ------
        ValueError
            If ``from_geometry`` has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        data       = self.input_geometry
        energies   = data.get("total_energy",      [])
        entropies  = data.get("entropy",            [])
        coherences = data.get("quantum_coherence",  [])
        capacities = data.get("capacity",           [])
        phases     = data.get("phase_state",        [])
        freqs      = data.get("frequency",          [])
        depths     = data.get("fractal_depth",      [])
        entangled  = data.get("entangled",          [])

        n    = max(len(energies), len(phases), 0)
        bits = []

        # ------------------------------------------------------------------
        # Section A: per-field  →  8 bits × 3 fields  (24 bits total)
        #   [phase_state 3b Gray][energy_mag 3b Gray][coherence 2b Gray]
        # ------------------------------------------------------------------
        for i in range(3):
            E   = float(energies[i])   if i < len(energies)   else 0.0
            coh = float(coherences[i]) if i < len(coherences) else 0.0
            ph  = phases[i]            if i < len(phases)      else "normal"

            bits.append(_phase_bits(ph))
            bits.append(_gray_bits(E,   _ENERGY_BANDS))
            bits.append(_gray_bits(coh, _COHERENCE_BANDS, n_bits=2))

        # ------------------------------------------------------------------
        # Section B: dynamics summary  →  9 bits
        #   [entropy_band 3b Gray][capacity_band 3b Gray][freq_band 3b Gray]
        # ------------------------------------------------------------------
        n_eff     = max(n, 1)
        mean_ent  = sum(float(e) for e in entropies[:n])  / n_eff if entropies  else 0.0
        mean_cap  = sum(float(c) for c in capacities[:n]) / n_eff if capacities else 1.0
        mean_freq = sum(float(f) for f in freqs[:n])      / n_eff if freqs      else 1.0

        bits.append(_gray_bits(mean_ent,  _ENTROPY_BANDS))
        bits.append(_gray_bits(mean_cap,  _CAPACITY_BANDS))
        bits.append(_gray_bits(mean_freq, _FREQ_BANDS))

        # ------------------------------------------------------------------
        # Section C: interaction summary  →  6 bits
        #   [resonance_band 3b Gray][any_entangled 1b][fractal_active 1b][phase_spread 1b]
        # ------------------------------------------------------------------
        f0  = float(freqs[0]) if len(freqs) > 0 else 1.0
        f1  = float(freqs[1]) if len(freqs) > 1 else f0
        res = resonance_strength(f0, f1)
        bits.append(_gray_bits(res, _RESONANCE_BANDS))

        any_ent    = "1" if any(entangled[:n])             else "0"
        frac_bit   = "1" if any(d > 0 for d in depths[:n]) else "0"
        unique_ph  = set(phases[:min(n, 3)])
        spread_bit = "1" if len(unique_ph) > 1             else "0"

        bits.append(any_ent)
        bits.append(frac_bit)
        bits.append(spread_bit)

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Cyclic Bridge Encoder — Field Dynamics Demo")
    print("=" * 60)

    # 1. Resonance strength
    print("\n1. Resonance strength  R = exp(−|f₁ − f₂|)")
    for label, f1, f2 in [("identical", 1.0, 1.0), ("near", 1.0, 1.1),
                           ("moderate",  1.0, 2.0), ("distant", 1.0, 5.0)]:
        r = resonance_strength(f1, f2)
        print(f"   {label:10s}  f1={f1:.1f}, f2={f2:.1f} → R = {r:.4f}")

    # 2. Regeneration capacity gain
    print("\n2. Regeneration gain  C' = C·(1 + 0.3·E_in/100)")
    for cap, E_in in [(1.0, 0.0), (1.0, 30.0), (1.5, 100.0), (2.0, 500.0)]:
        gain = regeneration_capacity_gain(cap, E_in)
        print(f"   C={cap:.1f}, E_in={E_in:.0f} → C' = {gain:.4f}")

    # 3. Phase transition costs
    print("\n3. Phase transition costs  E_cost = |Δphase| × 10 J")
    for src, tgt in [("normal", "liquid"), ("crystalline", "plasma"),
                     ("gas", "normal"),    ("plasma", "plasma")]:
        cost = phase_transition_cost(src, tgt)
        print(f"   {src:12s} → {tgt:12s}  E_cost = {cost:.0f} J")

    # 4. Fractal energy splits
    print("\n4. Fractal energy  E_spawn = E_total / 2^depth")
    for depth in range(4):
        e = fractal_energy_per_spawn(100.0, depth)
        print(f"   depth={depth}  spawns={2**depth:2d}  E_spawn = {e:.3f} J")

    # 5. Spatial gradient
    print("\n5. Spatial gradient  ∇E = (E₁ − E₂) / d")
    for E1, E2, d in [(100.0, 60.0, 2.0), (50.0, 50.0, 1.0), (0.0, 30.0, 0.5)]:
        g = spatial_gradient_strength(E1, E2, d)
        print(f"   E1={E1:.0f}, E2={E2:.0f}, d={d:.1f} → ∇E = {g:.2f} J/m")

    # 6. Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "total_energy":      [10.0,    50.0,   5.0],
        "entropy":           [0.1,     0.5,    0.05],
        "quantum_coherence": [0.8,     0.3,    0.95],
        "capacity":          [1.0,     2.5,    0.8],
        "phase_state":       ["normal", "liquid", "crystalline"],
        "frequency":         [1.0,     1.1,    5.0],
        "fractal_depth":     [0,       1,      0],
        "entangled":         [False,   True,   False],
    }

    encoder = CyclicBridgeEncoder()
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nInput fields    : {len(geometry['total_energy'])}")
    print(f"Phase states    : {geometry['phase_state']}")
    print(f"Binary output   : {binary}")
    print(f"Total bits      : {len(binary)}")
    print(f"Report          : {encoder.report()}")
