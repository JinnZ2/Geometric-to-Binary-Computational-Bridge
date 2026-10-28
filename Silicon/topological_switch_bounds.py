"""Light-switched magnetic topology in MnBi2Te4: what a state channel would need.

TSW-1..6. Stdlib only. Co-authored, human + Claude, 2026-10-28.

Study (CITED_PRESS, read at press depth 2026-10-28; paper not read):
  Monash University, ACS Nano, published 2026-10-23,
  doi:10.1021/acsnano.6c06828. First-principles calculations predict that
  terahertz light driving confined magnetophononic polaritons in
  2-septuple-layer (2-SL) MnBi2Te4 changes the interlayer exchange, so the
  flake goes from antiferromagnetic and topologically trivial (OFF) to
  ferromagnetic with conducting edge states (ON).
  "Experiments have yet to test the prediction." Phys.org headlines it
  "uncover"; Nanowerk and RuntimeWire say "predict". The rendering drift is
  the press layer's, and the grade here is PREDICTION.

What this module does: puts the switch beside the reach and symmetry checks
this folder already runs (repo_guard stages 2-3), so the study is read as a
candidate state channel with its operating envelope stated. It does not
model the polariton, the exchange change, or the band structure.

Numbers carried, not computed here. Each is VERIFY unless marked:
  - Sattar, Stepanov, Canali, arXiv:2604.07315 (abstract depth): in 6-SL
    MnBi2Te4 the outer-SL spin alignment sets the Chern number; parallel
    C=1 gap 18.9 meV, antiparallel C=0 gap 91.6 meV. 2-SL not studied,
    no light.  [CITED_ABSTRACT]
  - Bulk MnBi2Te4 Neel temperature about 24-25 K.  [VERIFY]
  - Quantized anomalous Hall seen in odd-SL flakes only at kelvin
    temperatures (Deng et al. 2020, 5-SL, ~1.4 K).  [VERIFY]
  - Mn/Bi antisite defects leave as-grown crystals electron-doped, which can
    put the Fermi level outside the exchange gap.  [VERIFY]

TSW-6: the study is about 2-SL; every gap carried here is 6-SL. The 2-SL
gap is NOT_IN_TEXT in the coverage read, and none is invented. The ceilings
below are therefore a reading of the nearest published thickness, not of the
predicted device.
"""

from __future__ import annotations

import math
from typing import Dict

KB_MEV_PER_K = 8.617333262e-2      # meV/K (exact from k_B / e)
H_MEV_PER_THZ = 4.135667696        # meV per THz (h / e)

# Carried literature values (see module docstring for grades).
GAP_C1_6SL_MEV = 18.9
GAP_C0_6SL_MEV = 91.6
T_NEEL_BULK_K = 24.0               # VERIFY; lower end of the quoted 24-25 K
SI_TARGET_K = 300.0                # the Bridge's operating temperature

# [CHOICE 1] A gap counts as thermally protected when it is at least this
# many kT. Not a physical constant; a stated working margin, printed.
PROTECT_MARGIN = 10.0

STUDY = {
    "doi": "10.1021/acsnano.6c06828",
    "venue": "ACS Nano, 2026-10-23",
    "kind": "first-principles prediction, not measured",
    "grade": "CITED_PRESS",
    "rendering_drift": "Phys.org 'uncover' vs Nanowerk/RuntimeWire 'predict'",
}


def kt_mev(temp_k: float) -> float:
    """Thermal energy kT in meV at temperature temp_k (K)."""
    if temp_k < 0:
        raise ValueError("temperature must be >= 0 K")
    return KB_MEV_PER_K * temp_k


def thz_to_mev(f_thz: float) -> float:
    """Photon energy (meV) of a drive at f_thz terahertz."""
    return H_MEV_PER_THZ * f_thz


def gap_in_kt(gap_mev: float, temp_k: float) -> float:
    """Gap expressed in units of kT. Infinite at 0 K."""
    kt = kt_mev(temp_k)
    return math.inf if kt == 0 else gap_mev / kt


def intrinsic_activation(gap_mev: float, temp_k: float) -> float:
    """Boltzmann factor exp(-gap / 2kT) for carriers thermally across the gap.

    A proxy for how insulating the bulk stays, not a carrier density: the
    prefactor (effective masses) is not known here and is not invented.
    Returns 0.0 at 0 K.
    """
    kt = kt_mev(temp_k)
    return 0.0 if kt == 0 else math.exp(-gap_mev / (2.0 * kt))


def protected_below_k(gap_mev: float, margin: float = PROTECT_MARGIN) -> float:
    """Highest temperature (K) at which gap >= margin * kT.  TSW-2."""
    if gap_mev <= 0 or margin <= 0:
        raise ValueError("gap and margin must be positive")
    return gap_mev / (margin * KB_MEV_PER_K)


def operating_ceiling_k(gap_mev: float, t_order_k: float = T_NEEL_BULK_K,
                        margin: float = PROTECT_MARGIN) -> Dict[str, float]:
    """The switch's ceiling is the LOWER of two temperatures.  TSW-1/2.

    1. Magnetic order: above t_order_k there is no AFM or FM state to switch.
    2. Gap protection: above protected_below_k the ON edge state is not
       separated from bulk carriers by the stated margin.
    """
    t_gap = protected_below_k(gap_mev, margin)
    return {"t_order_k": t_order_k, "t_gap_k": t_gap,
            "ceiling_k": min(t_order_k, t_gap),
            "binding": "magnetic_order" if t_order_k <= t_gap else "gap"}


def silicon_transfer() -> Dict[str, str]:
    """TSW-4: does the mechanism transfer to the Si substrate?  No.

    The switch acts on magnetic exchange. Si has no magnetic order to modify:
    it is diamagnetic, and Silicon/magnetic_authority.py already shows no
    magnetic state channel exists in it. Symmetry/material veto, not a reach
    shortfall.
    """
    return {"verdict": "DOES_NOT_TRANSFER",
            "reason": "no exchange interaction in diamagnetic Si to modify",
            "see": "Silicon/magnetic_authority.py (FAB-1..7)"}


def doping_window(gap_mev: float) -> Dict[str, object]:
    """TSW-5: the doping requirement the ON state reads through.

    Edge conduction reads as ON only if the Fermi level sits inside the
    exchange gap, a window of width gap_mev. In the SiliconState vector the
    knob is n (doping); here doping is the constraint and light is the knob.
    The antisite electron doping carried in the docstring is VERIFY.
    """
    return {"fermi_window_mev": gap_mev,
            "requires": "E_F inside the exchange gap (compensation or gating)",
            "role_of_doping": "constraint, not the switch",
            "grade": "PROPOSED"}


def readout_summary(temp_k: float = SI_TARGET_K) -> Dict[str, object]:
    """TSW-3: the carried 6-SL gaps read at temp_k."""
    out = {}
    for label, gap in (("C1_parallel", GAP_C1_6SL_MEV),
                       ("C0_antiparallel", GAP_C0_6SL_MEV)):
        out[label] = {"gap_mev": gap,
                      "gap_in_kT": gap_in_kt(gap, temp_k),
                      "activation": intrinsic_activation(gap, temp_k),
                      "protected_below_k": protected_below_k(gap)}
    out["kT_mev"] = kt_mev(temp_k)
    out["temp_k"] = temp_k
    return out


def main() -> int:
    r = readout_summary()
    c = operating_ceiling_k(GAP_C1_6SL_MEV)
    print(f"MnBi2Te4 light switch ({STUDY['grade']}, {STUDY['kind']})")
    print(f"  kT at {r['temp_k']:.0f} K = {r['kT_mev']:.2f} meV")
    for k in ("C1_parallel", "C0_antiparallel"):
        v = r[k]
        print(f"  {k:16s} gap {v['gap_mev']:5.1f} meV = {v['gap_in_kT']:.2f} kT,"
              f" exp(-gap/2kT) {v['activation']:.3f},"
              f" >= {PROTECT_MARGIN:.0f} kT below {v['protected_below_k']:.1f} K")
    print(f"  ceiling (C=1 gap, T_N {c['t_order_k']:.0f} K VERIFY): "
          f"{c['ceiling_k']:.1f} K, bound by {c['binding']}")
    print(f"  1 THz drive = {thz_to_mev(1.0):.2f} meV photon")
    print(f"  silicon: {silicon_transfer()['verdict']}")
    print(f"  [CHOICE 1] protection margin = {PROTECT_MARGIN:.0f} kT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
