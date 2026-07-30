"""Er3+ coherence, local vibrational modes, and the $10k gate: ER-1..8. Stdlib only.

Settles the arithmetic in ``Proposal.md``. Two results decide the document:
ER-1 (the claimed T2 is 8 orders above the Er ceiling at 300 K) and ER-2 (the
flagship experiment searches a spectral window where a heavy impurity cannot
have a mode). Neither needs apparatus.

ER-1 -- AND IT IS WORSE THAN "ORBACH IS OPEN"
---------------------------------------------
Er3+ is 4f11, an odd electron count, so it is a Kramers ion and the doublet is
protected from static strain and electric-field splitting. That protection says
nothing about phonon-driven relaxation through the crystal field, which is
Orbach, and Orbach is what kills Er at temperature.

The crystal-field gap to the first excited doublet is ~40-60 cm^-1 against
kT = 208.5 cm^-1 at 300 K, so ``Delta << kT``. In that regime
``exp(Delta/kT) - 1 ~ Delta/kT``, the Orbach rate goes *linear* in T rather
than exponentially activated, and the Bose occupation of the intermediate
doublet is ``n_bar = 3-5``. Quoting ``exp(-Delta/kT) ~ 0.8`` and calling the
channel "fully open" understates it: the channel is saturated, several phonons
deep, and there is no activation barrier left to hide behind.

Measured Er3+ T1 in the best host (Er:Y2SiO5) is ~10 ms at 1.5-2 K, ~us at
10 K, and above ~20-30 K the EPR lines are lifetime-broadened past detection.
At 300 K T1 sits at the phonon floor, ps-ns. With ``T2 <= 2 T1`` that caps T2
in the ns class, so a claimed 166 ms is ~8 orders high.

Calibration that does not depend on Er at all: the best room-temperature
solid-state spin coherence in ANY system is the NV centre in isotopically
purified diamond at T2 ~ 1-2 ms. 166 ms is ~110x that world record, claimed
for an ion from the fast-relaxing end of the lanthanides, in a host with 4.7%
29Si (I = 1/2) and no isotopic enrichment mentioned anywhere.

Er is used for quantum memory *because* of its 1.5 um telecom line, and always
below 4 K. That is not a funding limitation; it is Orbach.

ER-2 -- THE $10k FLAGSHIP GATE HAS NO TARGET
--------------------------------------------
A localized impurity mode appears above the host phonon maximum only for a
LIGHTER impurity. The gate is one mass ratio:

    impurity   m/m_Si   gap mode?   observed in Si
    B          0.38     possible    620 / 644 cm^-1
    C          0.43     possible    607 cm^-1
    O          0.57     possible    1136 cm^-1
    Si         1.00     no          520.7 (host maximum)
    P          1.10     no          none
    Er         5.96     no          none

Every sharp LVM in Si comes from an impurity lighter than Si. Er is 6x heavier,
so its ceiling is ``520.7 * sqrt(28.09/167.26) = 213 cm^-1`` and heavy defects
land well below even that, inside the acoustic continuum. The document searches
300-400 cm^-1, which is *above* the ceiling. A resonance inside the host band is
broadened by the continuum it sits in -- it is not a sharp Raman line, which is
precisely why heavy-impurity LVMs are hard to see.

The same gate kills the "P local mode at ~500 cm^-1": P is heavier than Si, so
no gap mode, and 500 cm^-1 sits in the tail of the vastly stronger 520.7 line.

ER-3 -- THE GATE'S OWN ARITHMETIC IS INCONSISTENT BY 8x
-------------------------------------------------------
With ``k = m omega^2`` and ``m_Er = 2.777e-25 kg``, the stated pair
(350 cm^-1, k_well = 150 N/m) cannot both hold: 350 cm^-1 gives 1207 N/m, and
150 N/m gives 123 cm^-1. Inconsistent by 8.0x. The pivot criterion is mis-set
too: "k < 100 N/m <-> omega < 250 cm^-1" should read k = 100 N/m <-> 101 cm^-1,
or omega = 250 cm^-1 <-> 616 N/m, so the threshold that decides 60% of the
budget is wrong by 6.2x in k.

ER-4 -- k_well DOES NOT DETERMINE T2, AND THIS IS DIMENSIONAL
------------------------------------------------------------
``k_well`` has dimensions M/T^2; T2 is a time. The only time constructible from
(k, m) is ``sqrt(m/k) = 1/omega``, which at 350 cm^-1 is a 95.3 fs vibrational
period -- 12.2 orders from 166 ms. Getting a coherence time out of a force
constant requires a spin-phonon coupling coefficient and a phonon density of
states, and neither appears anywhere in the document. Worse, ``k = m omega^2``
returns the frequency that was just measured, so the derived quantity carries
no information the measurement did not already have.

There is a second, structural problem with Obj 1.1: ``k_well = F_P / dr`` where
``dr`` is measured and ``F_P`` comes "from DFT-validated charge distribution".
That makes k_well (measurement) x (the model it is supposed to test). Same
shape as the R_2 protocol's theoretical numerator in ``Proposal-addendum.md``,
and as the FRET simulator whose estimator was its own generative process. Third
instance of the model supplying the part that would falsify it.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

__all__ = [
    "KB", "PLANCK", "C_LIGHT", "AMU", "QE", "HC_CM", "SI_PHONON_MAX_CM",
    "M_SI_U", "M_ER_U", "N_SI_PER_CM3", "A_SI", "A_GE", "MASSES_U",
    "kT_wavenumber", "bose_occupation", "orbach_factor", "orbach_regime",
    "t2_ceiling_from_t1", "coherence_shortfall",
    "force_constant", "wavenumber_from_k", "k_omega_consistency",
    "vibrational_period", "mass_ratio", "gap_mode_possible",
    "heavy_mass_ceiling", "lvm_gate",
    "implant_concentration", "dose_for_concentration", "areal_density",
    "ge_fraction_for_strain", "sige_mismatch",
    "thermal_phonon_window_thz", "landauer_aj", "energy_per_bit_check",
    "main",
]

KB = 1.380649e-23
PLANCK = 6.62607015e-34
C_LIGHT = 2.99792458e8
AMU = 1.66053906660e-27
QE = 1.602176634e-19
HC_CM = PLANCK * C_LIGHT * 100.0          # joules per cm^-1

SI_PHONON_MAX_CM = 520.7                  # Si optical phonon at Gamma
M_SI_U = 28.0855
M_ER_U = 167.26
N_SI_PER_CM3 = 5.0e22
A_SI = 5.431
A_GE = 5.658

#: Atomic masses, u. The observed-LVM column in ``lvm_gate`` is literature.
MASSES_U: Dict[str, float] = {
    "B": 10.811, "C": 12.011, "N": 14.007, "O": 15.999,
    "Si": 28.0855, "P": 30.974, "Ge": 72.63, "Er": 167.26,
}

_OBSERVED_LVM_CM: Dict[str, Optional[str]] = {
    "B": "620/644", "C": "607", "N": "653/766", "O": "1136",
    "Si": "520.7 (host max)", "P": None, "Ge": None, "Er": None,
}


# ---------------------------------------------------------------------------
# ER-1: Orbach
# ---------------------------------------------------------------------------

def kT_wavenumber(temp_k: float = 300.0) -> float:
    """kT expressed in cm^-1. 208.5 at 300 K."""
    if temp_k <= 0.0:
        raise ValueError("temperature must be positive")
    return KB * temp_k / HC_CM


def bose_occupation(gap_cm: float, temp_k: float = 300.0) -> float:
    """Mean phonon occupation of the intermediate level, 1/(exp(D/kT)-1).

    This is the number the exponential factor hides. At a 40 cm^-1 crystal-field
    gap and 300 K it is 4.7, meaning the level Orbach relaxes through is
    thermally populated several phonons deep.
    """
    if gap_cm <= 0.0:
        raise ValueError("gap must be positive")
    x = gap_cm / kT_wavenumber(temp_k)
    return 1.0 / (math.expm1(x))


def orbach_factor(gap_cm: float, temp_k: float = 300.0) -> float:
    """``exp(-Delta/kT)`` -- the usual quoted figure, and the misleading one."""
    if gap_cm <= 0.0:
        raise ValueError("gap must be positive")
    return math.exp(-gap_cm / kT_wavenumber(temp_k))


def orbach_regime(gap_cm: float, temp_k: float = 300.0) -> Dict[str, object]:
    """Is Orbach activated, or saturated into its linear-in-T limit?

    ``Delta/kT >> 1`` is the activated regime where ``exp(-Delta/kT)`` is a
    genuine suppression. ``Delta/kT << 1`` is the saturated regime: the rate
    goes linear in T and there is no barrier left. Er at 300 K is the latter.
    """
    kt = kT_wavenumber(temp_k)
    x = gap_cm / kt
    return {
        "gap_cm": gap_cm, "kT_cm": kt, "gap_over_kT": x,
        "exp_factor": math.exp(-x), "bose_occupation": bose_occupation(gap_cm, temp_k),
        "saturated": x < 1.0,
        "regime": "saturated, rate linear in T" if x < 1.0 else "activated",
    }


def t2_ceiling_from_t1(t1_s: float) -> float:
    """``T2 <= 2 T1``. The bound no dephasing improvement can beat."""
    if t1_s <= 0.0:
        raise ValueError("T1 must be positive")
    return 2.0 * t1_s


def coherence_shortfall(claimed_t2_s: float, t1_s: float,
                        reference_t2_s: float = 1.5e-3) -> Dict[str, float]:
    """Orders of magnitude between a claimed T2, the T1 bound, and the record.

    ``reference_t2_s`` defaults to the NV-in-purified-diamond room-temperature
    figure, ~1-2 ms, which is the best in any material.
    """
    ceiling = t2_ceiling_from_t1(t1_s)
    return {
        "claimed_t2_s": claimed_t2_s, "t1_s": t1_s, "t2_ceiling_s": ceiling,
        "orders_over_ceiling": math.log10(claimed_t2_s / ceiling),
        "times_world_record": claimed_t2_s / reference_t2_s,
        "exceeds_ceiling": claimed_t2_s > ceiling,
    }


# ---------------------------------------------------------------------------
# ER-3, ER-4: force constant and frequency
# ---------------------------------------------------------------------------

def force_constant(wavenumber_cm: float, mass_u: float = M_ER_U) -> float:
    """``k = m omega^2``, N/m, from a wavenumber in cm^-1."""
    if wavenumber_cm <= 0.0 or mass_u <= 0.0:
        raise ValueError("need wavenumber > 0 and mass > 0")
    omega = 2.0 * math.pi * C_LIGHT * 100.0 * wavenumber_cm
    return mass_u * AMU * omega * omega


def wavenumber_from_k(k_n_per_m: float, mass_u: float = M_ER_U) -> float:
    """Inverse of ``force_constant``."""
    if k_n_per_m <= 0.0 or mass_u <= 0.0:
        raise ValueError("need k > 0 and mass > 0")
    omega = math.sqrt(k_n_per_m / (mass_u * AMU))
    return omega / (2.0 * math.pi * C_LIGHT * 100.0)


def k_omega_consistency(wavenumber_cm: float, k_n_per_m: float,
                        mass_u: float = M_ER_U) -> Dict[str, float]:
    """Are a stated (omega, k) pair consistent? Reports the factor either way."""
    k_implied = force_constant(wavenumber_cm, mass_u)
    wn_implied = wavenumber_from_k(k_n_per_m, mass_u)
    return {
        "stated_wavenumber_cm": wavenumber_cm, "stated_k": k_n_per_m,
        "k_implied_by_wavenumber": k_implied,
        "wavenumber_implied_by_k": wn_implied,
        "k_ratio": k_implied / k_n_per_m,
        "wavenumber_ratio": wavenumber_cm / wn_implied,
        "consistent": abs(math.log10(k_implied / k_n_per_m)) < math.log10(1.2),
    }


def vibrational_period(wavenumber_cm: float) -> float:
    """``1/(c * wavenumber)``, seconds. The only time (k, m) can produce.

    95.3 fs at 350 cm^-1. Any claim that a force constant validates a coherence
    time has to bridge from here, and the document offers no equation that does.
    """
    if wavenumber_cm <= 0.0:
        raise ValueError("wavenumber must be positive")
    return 1.0 / (C_LIGHT * 100.0 * wavenumber_cm)


# ---------------------------------------------------------------------------
# ER-2: the mass gate
# ---------------------------------------------------------------------------

def mass_ratio(impurity: str, host: str = "Si") -> float:
    for name in (impurity, host):
        if name not in MASSES_U:
            raise ValueError(f"unknown species {name!r}")
    return MASSES_U[impurity] / MASSES_U[host]


def gap_mode_possible(impurity: str, host: str = "Si") -> bool:
    """A mode above the host phonon maximum needs a LIGHTER impurity."""
    return mass_ratio(impurity, host) < 1.0


def heavy_mass_ceiling(impurity: str, host: str = "Si",
                       host_max_cm: float = SI_PHONON_MAX_CM) -> float:
    """Upper bound on a heavy impurity's mode, ``w_max * sqrt(m_host/m_imp)``.

    Heavy defects actually land well below this, inside the acoustic continuum,
    where the mode is a broadened resonance rather than a sharp line.
    """
    return host_max_cm / math.sqrt(mass_ratio(impurity, host))


def lvm_gate(search_lo_cm: float, search_hi_cm: float,
             impurity: str = "Er") -> Dict[str, object]:
    """Can a search window contain this impurity's local mode?"""
    if search_lo_cm <= 0.0 or search_hi_cm < search_lo_cm:
        raise ValueError("need 0 < lo <= hi")
    ratio = mass_ratio(impurity)
    ceiling = heavy_mass_ceiling(impurity)
    light = ratio < 1.0
    reachable = light or search_lo_cm <= ceiling
    return {
        "impurity": impurity, "mass_ratio": ratio,
        "gap_mode_possible": light,
        "ceiling_cm": ceiling,
        "window": (search_lo_cm, search_hi_cm),
        "window_reachable": reachable,
        "observed_lvm_cm": _OBSERVED_LVM_CM.get(impurity),
        "verdict": ("light impurity: gap mode above the host maximum is possible"
                    if light else
                    f"heavy impurity: ceiling {ceiling:.0f} cm^-1, and the mode "
                    "is an in-band broadened resonance"
                    + ("" if reachable else
                       "; the window starts above the ceiling")),
    }


# ---------------------------------------------------------------------------
# ER-7: implants
# ---------------------------------------------------------------------------

def implant_concentration(dose_per_cm2: float, depth_nm: float) -> Dict[str, float]:
    """Dose over a depth -> volume concentration and atomic fraction."""
    if dose_per_cm2 < 0.0 or depth_nm <= 0.0:
        raise ValueError("need dose >= 0 and depth > 0")
    depth_cm = depth_nm * 1e-7
    c = dose_per_cm2 / depth_cm
    return {"concentration_per_cm3": c,
            "atomic_fraction": c / N_SI_PER_CM3,
            "atomic_percent": 100.0 * c / N_SI_PER_CM3,
            "exceeds_solubility": c > 1e18}


def dose_for_concentration(conc_per_cm3: float, depth_nm: float) -> float:
    """The dose a target concentration actually needs, cm^-2."""
    if conc_per_cm3 < 0.0 or depth_nm <= 0.0:
        raise ValueError("need concentration >= 0 and depth > 0")
    return conc_per_cm3 * depth_nm * 1e-7


def areal_density(conc_per_cm3: float, depth_nm: float,
                  rbs_limit_per_cm2: float = 1e13) -> Dict[str, object]:
    """Areal density and whether RBS can see it."""
    n = dose_for_concentration(conc_per_cm3, depth_nm)
    return {"areal_per_cm2": n, "rbs_limit_per_cm2": rbs_limit_per_cm2,
            "shortfall": rbs_limit_per_cm2 / n if n > 0 else float("inf"),
            "detectable": n >= rbs_limit_per_cm2}


# ---------------------------------------------------------------------------
# ER-5, ER-6: strain and phonons
# ---------------------------------------------------------------------------

def sige_mismatch(ge_fraction: float) -> float:
    """Fractional lattice mismatch of Si(1-x)Ge(x) against Si, by Vegard."""
    if not 0.0 <= ge_fraction <= 1.0:
        raise ValueError("Ge fraction must be in [0, 1]")
    a = A_SI + ge_fraction * (A_GE - A_SI)
    return (a - A_SI) / A_SI


def ge_fraction_for_strain(strain: float) -> float:
    """Ge fraction needed for a target lattice strain. 1.2% needs 0.287."""
    target_a = A_SI * (1.0 + strain)
    x = (target_a - A_SI) / (A_GE - A_SI)
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"strain {strain} needs Ge fraction {x:.3f}, out of range")
    return x


def thermal_phonon_window_thz(temp_c: float) -> float:
    """``kT/h`` in THz -- the width of the thermally occupied phonon window.

    17.2 THz at a 550 C growth temperature. Blocking a 0.1-0.2 THz minigap
    removes ~1% of it, and phonons are the bath supplying activation rather
    than a carrier that can be reflected. Matthews-Blakeslee is an energy
    balance, so a kinetic barrier does not move the critical thickness.
    """
    t = temp_c + 273.15
    if t <= 0.0:
        raise ValueError("temperature must be above absolute zero")
    return KB * t / PLANCK / 1e12


# ---------------------------------------------------------------------------
# Q4.2: energy per bit, and which values are legal
# ---------------------------------------------------------------------------

def landauer_aj(temp_k: float = 300.0) -> float:
    """kT*ln2 in attojoules. 0.0029 aJ at 300 K."""
    if temp_k <= 0.0:
        raise ValueError("temperature must be positive")
    return KB * temp_k * math.log(2.0) * 1e18


def energy_per_bit_check(value_aj: float,
                         temp_k: float = 300.0) -> Dict[str, object]:
    """Is a stated energy-per-bit above the Landauer bound, and by how much?

    The three values in circulation differ in *legality*, not just magnitude:
    1-2 aJ is ~350 kT ln2 and legal; 0.1 eV is 5.6 kT ln2 and legal; 0.01 eV is
    0.56 kT ln2 and BELOW the bound. For scale, a conventional switching event
    at C = 1 fF, V = 0.8 V dissipates CV^2 = 640 aJ.
    """
    floor = landauer_aj(temp_k)
    return {"value_aj": value_aj, "landauer_aj": floor,
            "in_kt_ln2": value_aj / floor,
            "above_bound": value_aj > floor,
            "cv2_1ff_0v8_aj": 1e-15 * 0.8 ** 2 * 1e18}


# ---------------------------------------------------------------------------

def main() -> None:
    print("Er3+ BOUNDS\n" + "=" * 70)

    print("\nER-1  Orbach at 300 K is saturated, not merely open")
    for gap in (40.0, 60.0):
        r = orbach_regime(gap)
        print(f"  gap {gap:.0f} cm^-1 vs kT {r['kT_cm']:.1f}: "
              f"D/kT = {r['gap_over_kT']:.3f}, exp = {r['exp_factor']:.3f}, "
              f"n_bar = {r['bose_occupation']:.2f}  -> {r['regime']}")
    s = coherence_shortfall(166e-3, 1e-9)
    print(f"  claimed T2 {s['claimed_t2_s']*1e3:.0f} ms against a T1 of 1 ns:")
    print(f"    T2 ceiling 2*T1 = {s['t2_ceiling_s']*1e9:.0f} ns, "
          f"{s['orders_over_ceiling']:.1f} orders over")
    print(f"    and {s['times_world_record']:.0f}x the NV-in-diamond RT record")

    print("\nER-2  the mass gate: a gap mode needs a lighter impurity")
    print(f"  {'imp':>4} {'m/m_Si':>7} {'gap?':>6} {'ceiling':>9}  observed in Si")
    for imp in ("B", "C", "N", "O", "Si", "P", "Ge", "Er"):
        r = mass_ratio(imp)
        ceil = "-" if r < 1.0 else f"{heavy_mass_ceiling(imp):.0f} cm^-1"
        print(f"  {imp:>4} {r:>7.2f} {('yes' if r < 1 else 'NO'):>6} {ceil:>9}"
              f"  {_OBSERVED_LVM_CM[imp] or 'none'}")
    g = lvm_gate(300.0, 400.0, "Er")
    print(f"  searching {g['window'][0]:.0f}-{g['window'][1]:.0f} cm^-1 for Er: "
          f"reachable = {g['window_reachable']}")
    print(f"  {g['verdict']}")

    print("\nER-3  the gate's own arithmetic")
    c = k_omega_consistency(350.0, 150.0)
    print(f"  stated (350 cm^-1, 150 N/m): 350 implies {c['k_implied_by_wavenumber']:.0f} N/m,"
          f" 150 implies {c['wavenumber_implied_by_k']:.0f} cm^-1")
    print(f"  inconsistent by {c['k_ratio']:.1f}x in k. consistent = {c['consistent']}")
    print(f"  pivot: k=100 N/m is {wavenumber_from_k(100.0):.0f} cm^-1, "
          f"250 cm^-1 is {force_constant(250.0):.0f} N/m "
          f"-> mis-set by {force_constant(250.0)/100:.1f}x")

    print("\nER-4  k_well cannot yield T2, dimensionally")
    p = vibrational_period(350.0)
    print(f"  the only time in (k, m) is 1/omega = {p*1e15:.1f} fs at 350 cm^-1")
    print(f"  claimed T2 is {math.log10(166e-3/p):.1f} orders away")
    print("  k = m*omega^2 returns the frequency just measured: no new information")

    print("\nER-7  implant dose vs the document's own concentration")
    for label, dose in (("Er", 5e16), ("P", 2e17)):
        r = implant_concentration(dose, 50.0)
        print(f"  {label} {dose:.0e} cm^-2 over 50 nm -> "
              f"{r['concentration_per_cm3']:.1e} cm^-3 = {r['atomic_percent']:.0f} at.%"
              f"  solubility exceeded: {r['exceeds_solubility']}")
    need = dose_for_concentration(1e17, 50.0)
    print(f"  dose for the stated 1e17 cm^-3: {need:.1e} cm^-2 "
          f"-> recipe is {5e16/need:.0e}x too high")
    a = areal_density(1e17, 50.0)
    print(f"  RBS-C: {a['areal_per_cm2']:.1e} cm^-2 vs a {a['rbs_limit_per_cm2']:.0e} "
          f"limit -> {a['shortfall']:.0f}x short, detectable = {a['detectable']}")

    print("\nER-5  Ge fraction")
    print(f"  2% Ge gives {sige_mismatch(0.02)*100:.3f}% mismatch (document says 0.8%)")
    x = ge_fraction_for_strain(0.012)
    print(f"  +1.2% strain needs x = {x:.3f} = {x*100:.0f}% Ge, not 2% "
          f"({x/0.02:.0f}x)")

    print("\nER-6  phonons are the bath")
    w = thermal_phonon_window_thz(550.0)
    print(f"  kT/h at 550 C = {w:.1f} THz; a 0.2 THz minigap is "
          f"{0.2/w*100:.1f}% of it")
    print("  Matthews-Blakeslee is an energy balance: a kinetic barrier does")
    print("  not move the critical thickness (~5-10 nm at 1.2%, design wants 50)")

    print("\nQ4.2  the three energy-per-bit values differ in legality")
    for label, aj in (("1 aJ (Q4.2)", 1.0), ("0.1 eV", 0.1 * QE * 1e18),
                      ("0.01 eV", 0.01 * QE * 1e18)):
        r = energy_per_bit_check(aj)
        print(f"  {label:>14}: {aj:.4f} aJ = {r['in_kt_ln2']:6.2f} kT*ln2  "
              f"{'legal' if r['above_bound'] else 'BELOW THE BOUND'}")
    print(f"  for scale, CV^2 at 1 fF and 0.8 V = "
          f"{energy_per_bit_check(1.0)['cv2_1ff_0v8_aj']:.0f} aJ")


if __name__ == "__main__":
    main()
