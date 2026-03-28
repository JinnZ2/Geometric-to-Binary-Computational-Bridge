"""
Resilience Bridge Encoder
=========================
Encodes urban/regional resilience state into binary using the 6-domain
octahedral geometry from the Resilience repository.

The six resilience domains map directly onto the six octahedral axes
defined in sim/seed_protocol.py OCTAHEDRAL_DIRS and sim/seed_mesh.py
DOMAIN_AXIS_MAP:

    +X = food/water      −X = energy
    +Y = social          −Y = institutional
    +Z = knowledge       −Z = infrastructure

This pairing is intentional: opposing axes encode coupled concerns.
Food needs energy; institutions need social legitimacy; infrastructure
embodies knowledge. Collapse in one stresses its axis-partner first.

The encoder formalises the existing seed_protocol.py 5-byte packet as
a 39-bit Gray-coded bridge output, compatible with the rest of the
bridge stack (sensor_suite, physics_guard, consciousness/emotion meta-layer).

Equations implemented
---------------------
  Seed entropy     :  H = −Σ pᵢ · log₂(pᵢ)                 (balance of domain proportions)
  Opposing balance :  B = 1 − mean(|p_axis − p_opposing|)    (paired-axis symmetry)
  Buffer stress    :  σ_buf = 1 − min(buffer_remaining)       (weakest buffer drives cascade)
  Cascade spillover:  S = max(0, shock − buffer)              (from DomainState.absorb_shock)
  Knowledge decay  :  τ_k ≈ 50 yrs (embodied) / 10 yrs (documented)  (regen window)

Bit layout (39 bits)
--------------------
Section A — Domain capacities  (18 bits = 3b Gray × 6 domains):
  [food_cap         3b Gray]  food/water capacity  [0, 0.125, ..., 0.875]
  [energy_cap       3b Gray]  energy capacity
  [social_cap       3b Gray]  social cohesion
  [institutional_cap 3b Gray] institutional capacity
  [knowledge_cap    3b Gray]  knowledge transmission
  [infra_cap        3b Gray]  physical infrastructure
  (domain order matches DOMAIN_AXIS_MAP: +X, −X, +Y, −Y, +Z, −Z)

Section B — Buffer & readiness  (9 bits):
  [crisis_phase     2b Gray]  STABLE(00)→STRESSED(01)→CASCADE(11)→COLLAPSE(10)
  [min_buffer_band  3b Gray]  minimum buffer across all domains ([0, 0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0])
  [cascading        1b]       any domain buffer_remaining < 0.05
  [knowledge_crit   1b]       knowledge buffer < 0.20 (generational loss risk)
  [load_bearing     1b]       cognitive_load_bearing — constraint_gradient > 0.60
  [lag_hi           1b]       decision_lag_hours > 24 (absentee / no protocol)

Section C — Cascade coupling  (6 bits):
  [dominant_domain  3b Gray]  domain driving primary cascade:
                               NONE(000)→FOOD(001)→ENERGY(011)→SOCIAL(010)→
                               INSTITUTIONAL(110)→KNOWLEDGE(111)→INFRA(101)→CLIMATE(100)
  [amplification    2b Gray]  max cascade amplification factor ([1.0, 1.2, 1.4, 1.6])
  [spillover        1b]       any active spillover crossing a coupling edge

Section D — Seed geometry  (6 bits):
  [seed_entropy     3b Gray]  H(proportions) across 8 bands ([0, 0.25, ..., 1.75] bits)
  [opposing_balance 2b Gray]  paired-axis symmetry across 4 bands ([0, 0.33, 0.67, 1.0])
  [transmissible    1b]       all 6 proportions > 0 (packet can be sent / decoded)

License: CC-BY-4.0
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Domain ordering (must match DOMAIN_AXIS_MAP in seed_mesh.py)
# ---------------------------------------------------------------------------

DOMAIN_ORDER = ["food", "energy", "social", "institutional", "knowledge", "infrastructure"]

# Opposing axis pairs: (axis_i, axis_i+1) by index
# food(0)↔energy(1), social(2)↔institutional(3), knowledge(4)↔infrastructure(5)
_OPPOSING_PAIRS = [(0, 1), (2, 3), (4, 5)]

# ---------------------------------------------------------------------------
# Ordered tables for Gray-coded categorical fields
# ---------------------------------------------------------------------------

_CRISIS_PHASES    = ["stable", "stressed", "cascade", "collapse"]

_DOMINANT_DOMAINS = [
    "none", "food", "energy", "social",
    "institutional", "knowledge", "infrastructure", "climate",
]

_AMPLIFICATION_LEVELS = [1.0, 1.2, 1.4, 1.6]   # 4-band 2b

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------

_CAP_BANDS         = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]
_BUFFER_BANDS      = [0.0, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.0]
_ENTROPY_BANDS     = [0.0, 0.25, 0.50, 0.75, 1.0, 1.25, 1.50, 1.75]   # bits
_OPP_BALANCE_BANDS = [0.0, 0.33, 0.67, 1.0]                            # 4-band 2b
_AMP_BANDS         = [1.0, 1.2, 1.4, 1.6]                              # 4-band 2b


def _table_bits(value: str, table: list, n_bits: int = 3) -> str:
    v   = value.lower().strip()
    idx = table.index(v) if v in table else 0
    g   = idx ^ (idx >> 1)
    return format(g, f"0{n_bits}b")


# ---------------------------------------------------------------------------
# Physics / systems functions (pure, importable)
# ---------------------------------------------------------------------------

def domain_seed(capacities: dict) -> list:
    """
    Convert a {domain: capacity} dict to a normalised 6-proportion list.

    Order follows DOMAIN_ORDER: food, energy, social, institutional,
    knowledge, infrastructure.  Missing domains default to 0.

    This is the input format expected by seed_protocol.encode_seed().
    """
    raw = [max(0.0, float(capacities.get(d, 0.0))) for d in DOMAIN_ORDER]
    total = sum(raw)
    if total < 1e-12:
        return [1.0 / 6.0] * 6
    return [x / total for x in raw]


def seed_entropy(proportions: list) -> float:
    """
    Shannon entropy of the 6-domain seed vector: H = −Σ pᵢ · log₂(pᵢ).

    Returns 0.0 for a completely concentrated seed (one domain = 1).
    Returns log₂(6) ≈ 2.585 for a perfectly balanced seed.
    Implements the information-theoretic measure of domain balance.
    """
    h = 0.0
    for p in proportions:
        if p > 1e-12:
            h -= p * math.log2(p)
    return h


def opposing_balance(proportions: list) -> float:
    """
    Mean balance across the three opposing axis pairs.

    Balance per pair = 1 − |p_i − p_j|.
    Returns 1.0 when all opposing pairs are equal; 0.0 when maximally asymmetric.

    Interprets the octahedral pairing:
      food ↔ energy  (biological need vs. energy supply)
      social ↔ institutional  (cohesion vs. structure)
      knowledge ↔ infrastructure  (embodied know-how vs. physical systems)
    """
    if len(proportions) < 6:
        return 0.0
    scores = [1.0 - abs(proportions[i] - proportions[j])
              for i, j in _OPPOSING_PAIRS]
    return sum(scores) / len(scores)


def cascade_dominant(capacities: dict, buffers: dict) -> str:
    """
    Identify the domain most likely driving a cascade.

    Selects the domain with the lowest buffer_remaining (most depleted).
    Returns "none" when all buffers are above the cascade threshold (0.05).
    """
    worst_buf  = 1.0
    worst_dom  = "none"
    for d in DOMAIN_ORDER:
        buf = float(buffers.get(d, 1.0))
        if buf < worst_buf:
            worst_buf = buf
            worst_dom = d
    if worst_buf >= 0.05:
        return "none"
    return worst_dom


def crisis_phase(capacities: dict, buffers: dict) -> str:
    """
    Classify overall system crisis phase from domain capacities and buffers.

    STABLE     : all capacities ≥ 0.7 and min buffer ≥ 0.4
    STRESSED   : any capacity < 0.7 or min buffer < 0.4
    CASCADE    : any buffer depleted (< 0.05) or min capacity < 0.3
    COLLAPSE   : min capacity < 0.1 or more than 2 domains depleted
    """
    caps  = [float(capacities.get(d, 1.0)) for d in DOMAIN_ORDER]
    bufs  = [float(buffers.get(d, 1.0))    for d in DOMAIN_ORDER]
    min_cap = min(caps)
    min_buf = min(bufs)
    n_depleted = sum(1 for b in bufs if b < 0.05)

    if min_cap < 0.10 or n_depleted > 2:
        return "collapse"
    if n_depleted > 0 or min_cap < 0.30:
        return "cascade"
    if min_cap < 0.70 or min_buf < 0.40:
        return "stressed"
    return "stable"


def knowledge_at_risk(knowledge_buffer: float,
                      knowledge_capacity: float) -> bool:
    """
    True when knowledge domain shows generational loss risk.

    Knowledge has the slowest regen rate (~50 years for embodied knowledge,
    ~10 years for documented).  Once the buffer is depleted, recovery
    spans generations — unlike economic or infrastructure recovery.
    Threshold: buffer < 0.20 OR capacity < 0.40.
    """
    return knowledge_buffer < 0.20 or knowledge_capacity < 0.40


def buffer_min(buffers: dict) -> float:
    """Return the minimum buffer_remaining across all six domains."""
    return min(float(buffers.get(d, 1.0)) for d in DOMAIN_ORDER)


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class ResilienceBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes urban/regional resilience state into a 39-bit binary bitstring.

    Input geometry dict keys
    ------------------------
    capacities          : dict[str, float] — domain capacity [0, 1] per domain
                          keys: food, energy, social, institutional, knowledge, infrastructure
    buffers             : dict[str, float] — buffer_remaining [0, 1] per domain
    crisis_phase        : str  — "stable"/"stressed"/"cascade"/"collapse"
                          (auto-computed from capacities+buffers if omitted)
    dominant_domain     : str  — primary cascade source domain (auto if omitted)
    max_amplification   : float — largest active coupling amplification factor
    spillover_active    : bool  — any coupling edge has active spillover
    load_bearing        : bool  — cognitive_load_bearing (constraint_gradient > 0.60)
    decision_lag_hours  : float — estimated decision lag (hours)
    """

    def __init__(self):
        super().__init__("resilience")

    def from_geometry(self, geometry_data: dict):
        """Load resilience domain state from a geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert resilience state to a 39-bit binary string.

        Raises
        ------
        ValueError
            If from_geometry() has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        d    = self.input_geometry
        caps = d.get("capacities", {})
        bufs = d.get("buffers",    {})

        # Auto-compute phase and dominant domain if not supplied
        phase = d.get("crisis_phase",
                      crisis_phase(caps, bufs))
        dom   = d.get("dominant_domain",
                      cascade_dominant(caps, bufs))

        max_amp      = float(d.get("max_amplification",  1.0))
        spillover    = bool(d.get("spillover_active",    False))
        load_bearing = bool(d.get("load_bearing",        False))
        lag_hours    = float(d.get("decision_lag_hours", 0.0))

        bits = []

        # ------------------------------------------------------------------
        # Section A: Domain capacities  →  18 bits (3b Gray × 6 domains)
        # ------------------------------------------------------------------
        for domain in DOMAIN_ORDER:
            cap = float(caps.get(domain, 1.0))
            bits.append(_gray_bits(cap, _CAP_BANDS))

        # ------------------------------------------------------------------
        # Section B: Buffer & readiness  →  9 bits
        # ------------------------------------------------------------------
        min_buf     = buffer_min(bufs)
        k_buf       = float(bufs.get("knowledge", 1.0))
        k_cap       = float(caps.get("knowledge", 1.0))
        n_depleted  = sum(1 for dom_name in DOMAIN_ORDER
                         if float(bufs.get(dom_name, 1.0)) < 0.05)

        bits.append(_table_bits(phase, _CRISIS_PHASES, n_bits=2))
        bits.append(_gray_bits(min_buf, _BUFFER_BANDS))
        bits.append("1" if n_depleted > 0               else "0")  # cascading
        bits.append("1" if knowledge_at_risk(k_buf, k_cap) else "0")  # knowledge_crit
        bits.append("1" if load_bearing                 else "0")  # load_bearing
        bits.append("1" if lag_hours > 24.0             else "0")  # lag_hi

        # ------------------------------------------------------------------
        # Section C: Cascade coupling  →  6 bits
        # ------------------------------------------------------------------
        bits.append(_table_bits(dom, _DOMINANT_DOMAINS, n_bits=3))
        bits.append(_gray_bits(max_amp, _AMP_BANDS, n_bits=2))
        bits.append("1" if spillover else "0")

        # ------------------------------------------------------------------
        # Section D: Seed geometry  →  6 bits
        # ------------------------------------------------------------------
        seed = domain_seed(caps)
        h    = seed_entropy(seed)
        bal  = opposing_balance(seed)
        tx   = all(p > 0.0 for p in seed)

        bits.append(_gray_bits(h,   _ENTROPY_BANDS))
        bits.append(_gray_bits(bal, _OPP_BALANCE_BANDS, n_bits=2))
        bits.append("1" if tx else "0")

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Resilience Bridge Encoder — Domain Field Demo")
    print("=" * 60)

    # 1. Seed entropy across balance states
    print("\n1. Seed entropy  H = −Σ pᵢ·log₂(pᵢ)")
    cases = [
        ("Balanced",     [1/6]*6),
        ("Food-dominant",[0.5, 0.1, 0.1, 0.1, 0.1, 0.1]),
        ("Collapsed",    [0.9, 0.02, 0.02, 0.02, 0.02, 0.02]),
    ]
    for label, seed in cases:
        h   = seed_entropy(seed)
        bal = opposing_balance(seed)
        print(f"   {label:18s}  H={h:.3f} bits  opposing_balance={bal:.3f}")

    # 2. Crisis phase progression
    print("\n2. Crisis phase from domain states")
    scenarios = [
        ("Normal",    {"food":0.9,"energy":0.8,"social":0.85,"institutional":0.75,"knowledge":0.9,"infrastructure":0.85},
                      {"food":0.7,"energy":0.6,"social":0.8,"institutional":0.6,"knowledge":0.7,"infrastructure":0.7}),
        ("Stressed",  {"food":0.6,"energy":0.5,"social":0.7,"institutional":0.55,"knowledge":0.8,"infrastructure":0.7},
                      {"food":0.3,"energy":0.2,"social":0.5,"institutional":0.3,"knowledge":0.6,"infrastructure":0.4}),
        ("Cascade",   {"food":0.4,"energy":0.3,"social":0.6,"institutional":0.4,"knowledge":0.7,"infrastructure":0.5},
                      {"food":0.05,"energy":0.02,"social":0.3,"institutional":0.2,"knowledge":0.4,"infrastructure":0.3}),
        ("Collapse",  {"food":0.1,"energy":0.05,"social":0.3,"institutional":0.2,"knowledge":0.5,"infrastructure":0.2},
                      {"food":0.0,"energy":0.0,"social":0.1,"institutional":0.0,"knowledge":0.15,"infrastructure":0.05}),
    ]
    for label, caps, bufs in scenarios:
        phase = crisis_phase(caps, bufs)
        dom   = cascade_dominant(caps, bufs)
        k_risk= knowledge_at_risk(bufs.get("knowledge",1.0), caps.get("knowledge",1.0))
        print(f"   {label:10s}  phase={phase:9s}  dominant={dom:14s}  k_risk={k_risk}")

    # 3. Opposing axis balance
    print("\n3. Opposing axis balance (food↔energy, social↔institutional, knowledge↔infra)")
    for caps, label in [
        ({"food":0.8,"energy":0.8,"social":0.7,"institutional":0.7,"knowledge":0.6,"infrastructure":0.6}, "symmetric"),
        ({"food":0.9,"energy":0.2,"social":0.8,"institutional":0.3,"knowledge":0.7,"infrastructure":0.1}, "opposing stress"),
    ]:
        seed = domain_seed(caps)
        bal  = opposing_balance(seed)
        print(f"   {label:20s}  balance = {bal:.3f}")

    # 4. Full encoding
    print("\n" + "=" * 60)
    print("Encoding demo — cascade scenario")
    print("=" * 60)

    geometry = {
        "capacities": {
            "food":           0.45,
            "energy":         0.30,
            "social":         0.65,
            "institutional":  0.50,
            "knowledge":      0.70,
            "infrastructure": 0.55,
        },
        "buffers": {
            "food":           0.10,
            "energy":         0.03,    # depleted — cascade source
            "social":         0.40,
            "institutional":  0.20,
            "knowledge":      0.35,
            "infrastructure": 0.25,
        },
        "max_amplification":  1.6,
        "spillover_active":   True,
        "load_bearing":       True,
        "decision_lag_hours": 6.0,
    }

    enc = ResilienceBridgeEncoder()
    enc.from_geometry(geometry)
    b = enc.to_binary()

    auto_phase = crisis_phase(geometry["capacities"], geometry["buffers"])
    auto_dom   = cascade_dominant(geometry["capacities"], geometry["buffers"])
    seed       = domain_seed(geometry["capacities"])

    print(f"\nAuto phase      : {auto_phase}")
    print(f"Dominant domain : {auto_dom}")
    print(f"Seed entropy    : {seed_entropy(seed):.3f} bits")
    print(f"Opposing balance: {opposing_balance(seed):.3f}")
    print(f"Binary output   : {b}")
    print(f"Total bits      : {len(b)}")
    print(f"Report          : {enc.report()}")
