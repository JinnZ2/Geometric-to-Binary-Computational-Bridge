#!/usr/bin/env python3
# CC0 — JinnZ2 ecosystem — Geometric-to-Binary-Computational-Bridge
# stdlib only, no cloud dependency
#
# rhombohedral_phase_menu.py
# ==========================
# GEOMETRY IS THE SELECTOR. Same carbon atoms, two stackings:
#
#   ABA (Bernal)          ABC (rhombohedral)
#   mirror-symmetric      chiral staircase translation along z
#   dispersive bands      FLAT bands, surface-localized
#   ordinary metal        4-state superconducting phase menu
#
# Anchor: Seo, Cotten, Ye et al., "Family of magnetic field-boosted
# superconductors in rhombohedral graphene", Nature (2026). MIT/Ju lab.
# 4-5 layer rhombohedral graphene, hole-doped side. Four SC states;
# three survive B_parallel to ~9 T; several STRENGTHEN under field.
# Consistent with spin-aligned (non-singlet) pairing. SOC adds phases.
#
# Bond-graph IR mapping (per repo contract):
#   substrate node : C-lattice, stacking = geometric configuration bit
#   effort ports   : D (displacement field), B_par, B_perp
#   flow port      : n (carrier density, sign = doping direction)
#   state output   : coherent phase verdict
#
# CONSTRAINT LINES
#   - T must be ultracold regime (dilution fridge scale) — all phases
#   - phase menu exists ONLY on ABC stacking; ABA returns EMPTY
#   - hole doping (n < 0 from neutrality) is where the new family lives
#   - numbers below are ORDINAL/REGIME encodings, not fitted values;
#     exact critical fields/densities live in the paper's data

from dataclasses import dataclass
from enum import Enum


class Stacking(Enum):
    ABA_BERNAL = "mirror"       # z-mirror symmetric
    ABC_RHOMBO = "staircase"    # chiral translation, broken z-mirror


class FieldResponse(Enum):
    FRAGILE = "dC/dB < 0"   # singlet-like: field kills coherence
    IMMUNE = "dC/dB ~ 0"    # field-indifferent
    BOOSTED = "dC/dB > 0"   # spin-aligned: field TIGHTENS coherence


@dataclass
class Knobs:
    stacking: Stacking
    layers: int            # 4 or 5 observed
    doping: str            # "electron" | "hole"
    density_regime: int    # ordinal slot along |n| axis, 0..3
    B_par_T: float         # tesla, in-plane
    B_perp_T: float        # tesla, out-of-plane
    soc_proximity: bool    # spin-orbit coupling layer present


# Phase menu: ordinal encoding of the four hole-side states.
# (slot, response_parallel, note)
PHASE_MENU = {
    0: (FieldResponse.BOOSTED, "survives B_par to ~9T, strengthens"),
    1: (FieldResponse.BOOSTED, "survives B_par to ~9T, strengthens"),
    2: (FieldResponse.BOOSTED, "survives B_par; one state also "
                               "survives B_perp at elevated T"),
    3: (FieldResponse.FRAGILE, "conventional-like member of family"),
}


def phase_verdict(k: Knobs) -> dict:
    """Geometry in, coherent-state menu out."""
    if k.stacking is not Stacking.ABC_RHOMBO:
        return {"verdict": "EMPTY",
                "why": "mirror stacking -> dispersive bands -> "
                       "no flat-band correlation channel"}
    if k.layers not in (4, 5):
        return {"verdict": "UNKNOWN",
                "why": "menu mapped only for tetra/penta layer"}
    if k.doping != "hole":
        return {"verdict": "PRIOR_FAMILY",
                "why": "electron side = earlier chiral SC results; "
                       "new 4-state family is hole side"}
    resp, note = PHASE_MENU[k.density_regime % 4]
    boosted = resp is FieldResponse.BOOSTED and k.B_par_T > 0
    return {
        "verdict": "COHERENT",
        "state_slot": k.density_regime % 4,
        "field_response": resp.value,
        "field_boosted_now": boosted,
        "soc_extra_phases": k.soc_proximity,
        "note": note,
    }


# GEOMETRIC INVARIANT (the repo-level claim):
#   coherence_menu = f(stacking_symmetry), NOT f(composition)
#   Broken z-mirror -> flat band -> high DOS at low |n| ->
#   correlation-driven pairing with locked (spin-aligned) option.
#
# FALSIFIABLE CLAIMS
#   F1: ABA samples at identical (n, D, B, T) show no SC family.
#   F2: field-boost is absent for any state confirmed spin-singlet.
#   F3: menu collapses if band flatness is destroyed (twist/strain)
#       without changing composition.
#
# REFUTATION_PROTOCOL: if paper data refutes an encoding above,
# update THIS file. Never adjust the simulation to save the claim.

if __name__ == "__main__":
    k = Knobs(Stacking.ABC_RHOMBO, 5, "hole", 1, 8.5, 0.0, False)
    print(phase_verdict(k))
    print(phase_verdict(Knobs(Stacking.ABA_BERNAL, 5, "hole",
                              1, 8.5, 0.0, False)))
