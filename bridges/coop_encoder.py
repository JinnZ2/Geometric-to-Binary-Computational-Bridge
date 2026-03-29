"""
Cooperative Network Bridge Encoder
====================================
Encodes a cooperative-network simulation snapshot (from Coop-framework)
into a 39-bit Gray-coded binary string.

The Coop-framework models three coupled dynamics:
  1. Trust propagation  — adoption spreads along weighted trust edges
  2. Network growth     — new coops form near adopted nodes
  3. Resource distribution — surplus flows along trust links

These map cleanly to two existing bridge modalities:

Trust propagation ↔ Thermal bridge
------------------------------------
Trust density (adoption %) is the "temperature".  Resource flow along
trust links is "heat flux".  The propagation probability:
    prob = trust × trust_rate × network_bonus × affinity
is the discrete analogue of Fourier's law:
    q = −κ · ∇T
where κ = trust conductance and ∇T = adoption gradient across the link.

Emotion bridge (PAD meta-layer)
---------------------------------
Network dynamics produce observable affect signals:
    Pleasure  ← adoption density (thriving = high pleasure)
    Arousal   ← new-adoption velocity + bridge events (spreading = arousal)
    Dominance ← resource-giving ratio (givers have agency; receivers do not)

The PAD triplet maps to the same 8 emotion glyphs used in emotion_encoder.

Equations implemented
---------------------
  Trust temperature    : T = adoption_pct / 100                     (normalised)
  Fourier trust flow   : q = conductance × links × ΔT               (Fourier analogue)
  Trust flux density   : φ = resource_transfers / N_coops            (flow per node)
  Trust resonance      : R = exp(−|prob_predicted − rate_observed|)  (accuracy of model)
  Network phase        : classify(T, velocity, decay_rate) → phase
  Emotion from network : PAD → glyph via adoption + decay + resource dynamics

Bit layout (39 bits)
--------------------
Section A — Adoption dynamics  (12 bits):
  [adoption_band   3b Gray]  adoption_pct  → 8 bands [0, 15, 30, 45, 60, 75, 90, 100]
  [velocity_band   3b Gray]  new_adoptions/N → spread rate [0, .01, .02, .05, .10, .15, .20, .30]
  [flux_band       3b Gray]  transfers/N → resource flow [0, .05, .10, .20, .40, .60, .80, 1.0]
  [decay_band      3b Gray]  decayed/N → decay rate [0, .01, .02, .05, .10, .20, .30, .50]

Section B — Network topology  (9 bits):
  [network_phase   2b Gray]  GROWING(00)→STABLE(01)→SATURATING(11)→DECAYING(10)
  [dominant_type   3b Gray]  NONE(000)→FOOD(001)→GRAIN(011)→ELECTRIC(010)→
                              CREDIT(110)→WORKER(101)→MIXED(100)
  [bridge_active   1b]       bridges_formed > 0 this tick (cross-region trust jump)
  [hub_active      1b]       any resource hub transferred > 20% avg resources
  [new_coops_hi    1b]       new_coops > 0 this tick (growing network)
  [multi_region    1b]       coops present in 3+ regions

Section C — Trust-thermal  (12 bits):
  [trust_temp_band 3b Gray]  trust temperature = adoption_pct (thermal state)
  [conductance_band 3b Gray] avg link trust strength [0, .10, .20, .30, .40, .60, .80, 1.0]
  [affinity_band   3b Gray]  max type-affinity multiplier [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.0]
  [gradient_band   3b Gray]  regional adoption std-dev [0, .05, .10, .15, .20, .30, .40, .50]

Section D — Emotion  (6 bits):
  [emotion_glyph   3b Gray]  trust-network affect state (8 glyphs, same as emotion_encoder)
  [resonance_band  2b Gray]  trust-model accuracy [0, 0.33, 0.67, 1.0]
  [spreading       1b]       adoption is accelerating (velocity this tick > last tick)

License: CC-BY-4.0
"""

from __future__ import annotations

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Network phase + emotion tables (Gray-coded)
# ---------------------------------------------------------------------------

_NETWORK_PHASES = ["growing", "stable", "saturating", "decaying"]

_DOMINANT_TYPES = [
    "none", "food", "grain", "electric",
    "credit", "worker", "mixed",
]

# 8-state emotion glyphs (same ordering as emotion_encoder)
# neutral(000)→presence(001)→grief(011)→adaptation(010)→
# resilience(110)→failure(111)→regenerating(101)→thriving(100)
_EMOTION_GLYPHS = [
    "neutral", "presence", "grief", "adaptation",
    "resilience", "failure", "regenerating", "thriving",
]

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------

_ADOPTION_BANDS    = [0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 100.0]   # %
_VELOCITY_BANDS    = [0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
_FLUX_BANDS        = [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00]
_DECAY_BANDS       = [0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50]
_CONDUCTANCE_BANDS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.60, 0.80, 1.00]
_AFFINITY_BANDS    = [1.0, 1.1,  1.2,  1.3,  1.4,  1.5,  1.6,  2.0]
_GRADIENT_BANDS    = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
_RESONANCE_BANDS   = [0.0, 0.33, 0.67, 1.00]


def _table_bits(value: str, table: list, n_bits: int = 3) -> str:
    v   = value.lower().strip()
    idx = table.index(v) if v in table else 0
    g   = idx ^ (idx >> 1)
    return format(g, f"0{n_bits}b")


# ---------------------------------------------------------------------------
# Physics / network-theory functions (pure, importable)
# ---------------------------------------------------------------------------

def trust_temperature(adoption_pct: float) -> float:
    """
    Trust temperature = adoption density normalised to [0, 1].

    Analogous to temperature in Fourier's law: higher adoption density
    means more trust "heat" available for further propagation.
    """
    return max(0.0, min(1.0, adoption_pct / 100.0))


def fourier_trust_flow(
    conductance: float,
    link_count: int,
    delta_adoption: float,
) -> float:
    """
    Fourier analogue of heat flow through a trust network.

        q = conductance × link_count × |Δadoption|

    conductance   : avg trust strength across active links [0, 1]
    link_count    : number of active trust edges from the node
    delta_adoption: adoption proportion difference across the link [0, 1]

    Returns the expected trust-flow rate per tick.
    """
    return conductance * max(0, link_count) * max(0.0, delta_adoption)


def trust_flux_density(resource_transfers: int, total_coops: int) -> float:
    """
    Resource-flow flux density: transfers per node per tick.

    This is the "heat flux" dual — resources flow down trust gradients
    just as heat flows down temperature gradients.
    """
    if total_coops <= 0:
        return 0.0
    return resource_transfers / total_coops


def trust_resonance(
    predicted_prob: float,
    observed_adoption_rate: float,
) -> float:
    """
    Accuracy of the trust-propagation model for this tick.

        R = exp(−|P_predicted − P_observed|)

    Returns 1.0 when the model perfectly matches reality, approaching 0
    when the model is far off.  The same formula as field resonance in
    cyclic_encoder to maintain cross-bridge consistency.
    """
    return math.exp(-abs(predicted_prob - max(0.0, observed_adoption_rate)))


def propagation_probability(
    trust_strength: float,
    partner_trust_rate: float,
    adopted_neighbors: int,
    affinity: float = 1.0,
) -> float:
    """
    Expected per-tick adoption probability for a non-adopted coop.

        prob = trust × trust_rate × (1 + 0.05 × n_adopted_neighbors) × affinity

    This mirrors the exact formula in CoopNetwork._propagate_trust().
    """
    network_bonus = 1.0 + 0.05 * max(0, adopted_neighbors)
    return min(1.0, trust_strength * partner_trust_rate * network_bonus * affinity)


def network_adoption_phase(
    adoption_pct: float,
    velocity: float,
    decay_rate: float,
) -> str:
    """
    Classify the network's current adoption phase.

    DECAYING    : decay_rate > 0.02 or (adoption_pct > 50 and velocity < 0)
    SATURATING  : adoption_pct >= 80
    GROWING     : velocity > 0.01 and adoption_pct < 80
    STABLE      : otherwise
    """
    if decay_rate > 0.02:
        return "decaying"
    if adoption_pct >= 80.0:
        return "saturating"
    if velocity > 0.01:
        return "growing"
    return "stable"


def regional_trust_gradient(regional_adoption: dict) -> float:
    """
    Standard deviation of adoption percentages across regions.

    High gradient = trust heat is unevenly distributed across geography —
    some regions are "hot" while others remain cold.
    Normalised by dividing by 100 to bring into [0, 1].
    """
    if not regional_adoption:
        return 0.0
    vals = [v / 100.0 for v in regional_adoption.values()]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(variance)


def emotion_from_network(
    adoption_pct: float,
    velocity: float,
    decay_rate: float,
    resource_flow: float,
    bridges_active: bool = False,
) -> str:
    """
    Map trust-network state to an emotion glyph (PAD analogue).

    Glyph semantics:
      thriving      — adoption > 75%, resources flowing, no decay
      presence      — adoption 50–75%, steady, engaged
      adaptation    — growing (velocity > 0.02), network reorganising
      resilience    — bridges active (cross-region trust jumps)
      grief         — decay_rate > 0.05 (trust is being lost)
      regenerating  — recovering after decay (velocity > 0 after decay)
      failure       — adoption < 10%
      neutral       — default baseline
    """
    if adoption_pct < 10.0:
        return "failure"
    if decay_rate > 0.05:
        return "grief"
    if decay_rate > 0.01 and velocity > 0.0:
        return "regenerating"
    if bridges_active:
        return "resilience"
    if adoption_pct >= 75.0 and resource_flow > 0.10:
        return "thriving"
    if adoption_pct >= 50.0:
        return "presence"
    if velocity > 0.02:
        return "adaptation"
    return "neutral"


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class CoopBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes a Coop-framework network snapshot into a 39-bit binary string.

    Input geometry dict keys
    ------------------------
    Required (from CoopNetwork._snapshot()):
      tick              : int
      total_coops       : int
      adopted           : int
      adoption_pct      : float   — % of coops that have adopted
      new_adoptions     : int     — adoptions this tick
      new_coops         : int     — new coops spawned this tick
      resource_transfers: int     — resource transfers this tick
      avg_resources     : float   — average resources per coop
      bridges_formed    : int     — cross-region connections this tick
      decayed           : int     — coops that dropped out this tick

    Optional:
      prev_adoption_pct : float   — last tick's adoption_pct (for spreading flag)
      avg_trust_strength: float   — mean trust weight across all edges [0,1], default 0.5
      max_affinity      : float   — largest type-affinity multiplier active, default 1.0
      regional_adoption : dict[str, float]  — region → adoption_pct
      dominant_type     : str     — most common adopted co-op type
      hub_active        : bool    — any hub transferred >20% avg resources
      multi_region      : bool    — coops in 3+ regions
    """

    def __init__(self):
        super().__init__("coop")

    def from_geometry(self, geometry_data: dict):
        """Load a Coop-framework snapshot dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert network snapshot to a 39-bit binary string.

        Raises
        ------
        ValueError
            If from_geometry() has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(snapshot) before to_binary()."
            )

        d = self.input_geometry
        total      = max(int(d.get("total_coops",  1)), 1)
        adopted    = int(d.get("adopted",           0))
        adpt_pct   = float(d.get("adoption_pct",    0.0))
        new_adpt   = int(d.get("new_adoptions",     0))
        new_coops  = int(d.get("new_coops",         0))
        transfers  = int(d.get("resource_transfers",0))
        bridges    = int(d.get("bridges_formed",    0))
        decayed    = int(d.get("decayed",           0))

        velocity   = new_adpt  / total
        flux       = trust_flux_density(transfers, total)
        decay_rate = decayed   / total

        prev_pct   = float(d.get("prev_adoption_pct",    adpt_pct))
        conductance= float(d.get("avg_trust_strength",   0.50))
        max_aff    = float(d.get("max_affinity",         1.00))
        reg_adpt   = d.get("regional_adoption",          {})
        dom_type   = str(d.get("dominant_type",          "none")).lower()
        hub_active = bool(d.get("hub_active",            transfers > 0))
        multi_reg  = bool(d.get("multi_region",          len(reg_adpt) >= 3))

        gradient   = regional_trust_gradient(reg_adpt)
        phase      = network_adoption_phase(adpt_pct, velocity, decay_rate)
        emotion    = emotion_from_network(adpt_pct, velocity, decay_rate,
                                          flux, bridges_active=(bridges > 0))
        spreading  = adpt_pct > prev_pct

        # trust resonance: compare predicted prob at avg conductance vs observed velocity
        pred_prob  = propagation_probability(conductance, 0.12, 1, max_aff)
        resonance  = trust_resonance(pred_prob, velocity)

        bits = []

        # ------------------------------------------------------------------
        # Section A: Adoption dynamics  →  12 bits
        # ------------------------------------------------------------------
        bits.append(_gray_bits(adpt_pct,   _ADOPTION_BANDS))
        bits.append(_gray_bits(velocity,   _VELOCITY_BANDS))
        bits.append(_gray_bits(flux,       _FLUX_BANDS))
        bits.append(_gray_bits(decay_rate, _DECAY_BANDS))

        # ------------------------------------------------------------------
        # Section B: Network topology  →  9 bits
        # ------------------------------------------------------------------
        bits.append(_table_bits(phase,    _NETWORK_PHASES, n_bits=2))
        dom = dom_type if dom_type in _DOMINANT_TYPES else "none"
        bits.append(_table_bits(dom, _DOMINANT_TYPES, n_bits=3))
        bits.append("1" if bridges > 0   else "0")  # bridge_active
        bits.append("1" if hub_active    else "0")  # hub_active
        bits.append("1" if new_coops > 0 else "0")  # new_coops_hi
        bits.append("1" if multi_reg     else "0")  # multi_region

        # ------------------------------------------------------------------
        # Section C: Trust-thermal  →  12 bits
        # ------------------------------------------------------------------
        trust_temp = adpt_pct   # same scale as adoption bands
        bits.append(_gray_bits(trust_temp,  _ADOPTION_BANDS))   # reuse adoption bands
        bits.append(_gray_bits(conductance, _CONDUCTANCE_BANDS))
        bits.append(_gray_bits(max_aff,     _AFFINITY_BANDS))
        bits.append(_gray_bits(gradient,    _GRADIENT_BANDS))

        # ------------------------------------------------------------------
        # Section D: Emotion  →  6 bits
        # ------------------------------------------------------------------
        bits.append(_table_bits(emotion, _EMOTION_GLYPHS, n_bits=3))
        bits.append(_gray_bits(resonance, _RESONANCE_BANDS, n_bits=2))
        bits.append("1" if spreading else "0")

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Coop Bridge Encoder — Trust Propagation Demo")
    print("=" * 60)

    # 1. Trust-thermal physics
    print("\n1. Trust-thermal functions")
    for adpt in [10.0, 40.0, 70.0, 95.0]:
        T = trust_temperature(adpt)
        q = fourier_trust_flow(conductance=0.45, link_count=3, delta_adoption=T * 0.3)
        print(f"   adoption={adpt:5.1f}%  T={T:.2f}  q_trust={q:.4f}")

    # 2. Propagation probability
    print("\n2. Propagation probability (trust × rate × bonus × affinity)")
    for trust, rate, neighbors, affinity in [
        (0.3, 0.15, 1, 1.0),
        (0.5, 0.15, 3, 1.3),
        (0.7, 0.18, 5, 1.5),
    ]:
        p = propagation_probability(trust, rate, neighbors, affinity)
        print(f"   trust={trust}  rate={rate}  nbrs={neighbors}  aff={affinity}  → prob={p:.4f}")

    # 3. Network state snapshots
    print("\n3. Network snapshot encoding")
    snapshots = [
        {
            "name": "Early spread",
            "total_coops": 30, "adopted": 6, "adoption_pct": 20.0,
            "new_adoptions": 3, "new_coops": 1, "resource_transfers": 8,
            "bridges_formed": 0, "decayed": 0,
            "avg_trust_strength": 0.35, "max_affinity": 1.3,
            "regional_adoption": {"Minnesota": 30, "Wisconsin": 10, "Oregon": 5},
        },
        {
            "name": "Saturating",
            "total_coops": 45, "adopted": 38, "adoption_pct": 84.4,
            "new_adoptions": 2, "new_coops": 1, "resource_transfers": 22,
            "bridges_formed": 2, "decayed": 0,
            "avg_trust_strength": 0.55, "max_affinity": 1.5,
            "regional_adoption": {"Minnesota": 90, "Wisconsin": 80, "Oregon": 75,
                                   "Vermont": 85, "Appalachia": 70, "Dakotas": 92},
            "dominant_type": "food", "hub_active": True, "multi_region": True,
        },
        {
            "name": "Decay event",
            "total_coops": 40, "adopted": 28, "adoption_pct": 70.0,
            "new_adoptions": 1, "new_coops": 0, "resource_transfers": 5,
            "bridges_formed": 0, "decayed": 4,
            "prev_adoption_pct": 82.5,
            "avg_trust_strength": 0.30, "max_affinity": 1.0,
            "regional_adoption": {"Minnesota": 50, "Wisconsin": 60},
        },
    ]

    for snap in snapshots:
        velocity   = snap["new_adoptions"] / snap["total_coops"]
        decay_rate = snap["decayed"] / snap["total_coops"]
        flux       = trust_flux_density(snap["resource_transfers"], snap["total_coops"])
        phase      = network_adoption_phase(snap["adoption_pct"], velocity, decay_rate)
        emotion    = emotion_from_network(snap["adoption_pct"], velocity, decay_rate,
                                          flux, bridges_active=snap["bridges_formed"] > 0)
        resonance  = trust_resonance(
            propagation_probability(snap["avg_trust_strength"], 0.12, 1,
                                    snap.get("max_affinity", 1.0)),
            velocity)

        enc = CoopBridgeEncoder()
        enc.from_geometry(snap)
        bits = enc.to_binary()

        print(f"\n── {snap['name']} ──")
        print(f"  adoption={snap['adoption_pct']:.1f}%  phase={phase}  emotion={emotion}")
        print(f"  flux={flux:.3f}  resonance={resonance:.3f}  "
              f"gradient={regional_trust_gradient(snap.get('regional_adoption', {})):.3f}")
        print(f"  binary={bits}  ({len(bits)}b)")
