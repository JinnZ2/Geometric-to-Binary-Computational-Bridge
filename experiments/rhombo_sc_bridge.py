# rhombo_sc_bridge.py — CC0
# Integrates: Geometric-to-Binary-Computational-Bridge (bond-graph IR)
#             PhysicsGuard (claim → constraint closure)
#             assumption_validator (GREEN/YELLOW/RED scope drift)
#
# GEOMETRY → BINARY CHAIN (the actual finding, stripped of narrative):
#
#   stacking code        electronic geometry       attractor set
#   ┌──────────┐   →    ┌────────────────┐    →   ┌─────────────────┐
#   │ ABCAB(C) │        │ flat bands,     │        │ ≥4 SC states,   │
#   │ discrete │        │ surface-localized│       │ selectable by   │
#   │ sequence │        │ wavefunctions   │        │ (n, D, B∥)      │
#   └──────────┘        └────────────────┘        └─────────────────┘
#   1 bit/layer          continuous field           multi-well regime
#   (A/B/C shift)        (density of states)        (your spinodal map)

from dataclasses import dataclass

# ── BOND-GRAPH IR NODE ──────────────────────────────────────
# Domain: electrical. Effort=voltage, Flow=current.
# Novel element: R collapses to 0 *conditionally* — R is a
# regime-gated resistor, not a constant. Gate vector = (n, D, B∥, T).

IR_NODE = {
    "domain": "electrical",
    "element": "regime_gated_R",
    "R(state)": {"SC": 0.0, "normal": "R_n"},
    "gate_vector": ["carrier_density_n", "displacement_D",
                    "B_parallel", "temperature_T"],
    "state_count": 4,                 # observed SC states, pentalayer
    "coupling": {
        "magnetic→electrical": "+dTc/dB > 0 for 3 of 4 states",
        # sign inversion vs. conventional SC: B is a PUMP not a sink
        "substrate_geometry": "ABC stacking, N=4-5 layers",
        "SOC_proximity": "adds states, no disorder cost",
    },
}

# ── PHYSICSGUARD CONSTRAINT SET ─────────────────────────────
# Claims from coverage → closure-checkable form.

CONSTRAINTS = [
    # claim                          # closure condition
    ("zero resistance",              "R=0 ONLY within (Tc, Ic, Bc) box; "
                                     "unscoped 'zero' = OPEN claim → flag"),
    ("field-boosted SC",             "Pauli limit Bp≈1.86*Tc[K] tesla; "
                                     "observed B∥≈8.5-9T at sub-K Tc → "
                                     "spin-singlet pairing EXCLUDED; "
                                     "requires triplet/finite-momentum"),
    ("multiple states",              "distinct = distinct order params; "
                                     "verified via separate (n,D) domes + "
                                     "different B-response signs"),
    ("natural graphite structure",   "ABC is metastable minority phase; "
                                     "'natural' ≠ 'bulk-abundant' → "
                                     "identification is the bottleneck"),
]

# ── ASSUMPTION_VALIDATOR — transfer scope ───────────────────
SCOPE = {
    "GREEN": [
        "stacking-order-as-code (geometry programs attractor set)",
        "multi-well regime map under external field — direct import "
        "to field_collapse.py switchable-Φ_ext formalism",
        "B∥ as multiplier with POSITIVE coupling (sign-inverted vs. "
        "conventional; compare apex-broadcast crossing h*)",
    ],
    "YELLOW": [
        "Tc scale: sub-kelvin. Dilution fridge territory.",
        "sample = exfoliated flake, hBN-encapsulated, dual-gated — "
        "not bulk pencil graphite",
        "pairing mechanism unresolved (chiral PDW candidate per PRL "
        "136.026603, quarter-metal parent: 1 spin, 1 valley, 1 pocket)",
    ],
    "RED": [
        "any transfer claiming room-T or bulk-material relevance",
        "'simple carbon' framing — the states exist BECAUSE of "
        "engineered gate control, not despite it",
    ],
}

# ── STRUCTURAL FINDING FOR THE BRIDGE REPO ──────────────────
# The stacking sequence is a base-3 word (A/B/C per layer) where
# only the RELATIVE shift matters → effectively binary choice per
# interface: (continue chirality) vs (reverse). ABC = all-continue.
# One discrete geometric bit per interface selects between:
#   Bernal (ABA): dispersive bands, single boring metal
#   Rhombo (ABC): flat surface bands → 4+ programmable attractors
# → minimal known example of GEOMETRIC CODE → REGIME MULTIPLICITY
#   at the single-interface-bit resolution.
