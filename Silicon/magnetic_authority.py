"""Magnetic read/write authority in doped Si, and the strain channel that replaces it.

Settles FAB-1..7 and BRG-1..7. Stdlib only.

Scope: every arithmetic claim in Fabrication.md and Magnetic-bridge.md that
decides whether a magnetic state channel exists in silicon. It does not.
The same five numbers recur across six documents, so they are computed once
here and imported rather than restated.

Two of the audited figures did not reproduce and are corrected in place;
see `GRADIENT_NOTE` and `PIEZO_NOTE`.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

__all__ = [
    "MU0", "KB", "MUB", "HBAR", "PLANCK", "QE", "MUB_EV", "GYRO_HZ_PER_T",
    "CHI_SI", "XI_U_EV", "E_SI_PA", "PI_11", "PI_12", "PI_44", "PI_L_110",
    "GRADIENT_NOTE", "PIEZO_NOTE",
    "cell_moment", "dipole_field", "readout_shortfall",
    "curie_susceptibility", "er_vs_host",
    "zeeman_ev", "barrier_authority",
    "coil_field", "current_density", "electromigration_life",
    "eddy_diffusion_time", "stored_energy", "switching_power",
    "landauer_ev", "retention_barrier_ev", "arrhenius_lifetime",
    "gradient_addressing", "rabi_time", "rf_power_for_b1",
    "valley_splitting_ev", "piezoresistive_response", "authority_ratio",
    "flux_concentrator_gain", "main",
]

MU0 = 4e-7 * math.pi                # H/m
KB = 1.380649e-23                   # J/K
MUB = 9.2740100783e-24              # J/T
HBAR = 1.054571817e-34              # J.s
PLANCK = 6.62607015e-34             # J.s
QE = 1.602176634e-19                # C
MUB_EV = MUB / QE                   # eV/T
GYRO_HZ_PER_T = 2.0 * MUB / PLANCK  # 28.0 GHz/T, g = 2

CHI_SI = -4.0e-6                    # Si volume susceptibility, diamagnetic
XI_U_EV = 9.16                      # Si shear deformation potential, eV
E_SI_PA = 130e9                     # Si Young's modulus, Pa

# Smith 1954 piezoresistive coefficients for p-type Si, Pa^-1.
PI_11 = 6.6e-11
PI_12 = -1.1e-11
PI_44 = 138.1e-11
PI_L_110 = (PI_11 + PI_12 + PI_44) / 2.0     # 7.18e-10, <110> longitudinal

GRADIENT_NOTE = """\
The audited figure for gradient addressing was 1.4 kHz of Zeeman offset across
50 nm at 1000 T/m, a 700,000x shortfall against 1 GHz channel spacing. That is
1000x low. g*muB/h = 28.0 GHz/T, and 1000 T/m over 50 nm is 50 uT, so the
offset is 1.40 MHz and the shortfall is 714x. The gradient required for 1 GHz
spacing is 7.1e5 T/m, not 7e8.

This changes the verdict's character. 7.1e5 T/m is at the MFM tip state of the
art (~1e6 T/m), not three orders beyond it. Gradient addressing is not
impossible in principle; it is impossible with the 10-1000 T/m the document
specifies, and a tip-scale gradient exists only within tens of nm of the tip,
which is not a 4x4 array at 5 um pitch. BRG-5 stands, at 714x rather than
700,000x."""

PIEZO_NOTE = """\
The audited value pi_l = 6e-11 Pa^-1 was labelled "p-type <110> longitudinal".
6.6e-11 is pi_11, the <100> coefficient. The <110> longitudinal value is
(pi_11 + pi_12 + pi_44)/2 = 7.18e-10 Pa^-1, 12x larger, and it is the one
consistent with the same audit's "gauge factor ~100": pi_l * E = 93, whereas
6e-11 * E = 7.8.

Consequence for the recommendation, which strengthens: dR/R = GF * strain, so
93% at 1% strain and 9.3% at 0.1%. The quoted 7.8% at 1% strain was right in
magnitude only because a 12x-low coefficient was paired with a 10x-high
strain. Si fractures at 1-2% tensile and piezoresistance saturates well below
that, so the defensible claim is dR/R ~ 9% at 0.1% strain -- a strain that is
actually reachable."""


# --------------------------------------------------------------------------
# FAB-1: magnetisation readout
# --------------------------------------------------------------------------

def cell_moment(volume_m3: float, b_applied_t: float,
                chi: float = CHI_SI) -> float:
    """Induced magnetic moment of a cell, A.m^2. Signed: negative = diamagnetic.

    m = chi * H * V, H = B/mu0. Linear in both susceptibility and field, and
    for Si the susceptibility is the problem -- no field available on a bench
    moves this into instrument range.
    """
    if volume_m3 <= 0.0:
        raise ValueError("volume must be positive")
    return chi * (b_applied_t / MU0) * volume_m3


def dipole_field(moment_am2: float, r_m: float) -> float:
    """|B| from a point dipole on its axis, T. mu0*m/(2*pi*r^3)."""
    if r_m <= 0.0:
        raise ValueError("distance must be positive")
    return MU0 * abs(moment_am2) / (2.0 * math.pi * r_m ** 3)


def readout_shortfall(moment_am2: float, r_m: float = 1e-3,
                      hall_floor_gauss: float = 0.2,
                      squid_floor_am2: float = 1e-11) -> Dict[str, float]:
    """Orders of magnitude by which a cell moment misses each instrument.

    ``hall_orders`` compares a field at ``r_m`` against a Hall noise floor;
    ``squid_orders`` compares the moment directly against a commercial MPMS
    moment sensitivity, which is the more generous comparison and still fails.
    """
    b = dipole_field(moment_am2, r_m)
    b_gauss = b * 1e4
    return {
        "moment_am2": moment_am2,
        "field_t": b,
        "field_gauss": b_gauss,
        "hall_snr": b_gauss / hall_floor_gauss,
        "hall_orders": math.log10(hall_floor_gauss / b_gauss),
        "squid_orders": math.log10(squid_floor_am2 / abs(moment_am2)),
    }


# --------------------------------------------------------------------------
# FAB-2: the one paramagnetic dopant, and the host it sits in
# --------------------------------------------------------------------------

def curie_susceptibility(n_per_m3: float, mu_eff_bohr: float,
                         temp_k: float = 300.0) -> float:
    """Curie-law volume susceptibility, dimensionless. n*mu0*mu_eff^2/(3kT)."""
    if n_per_m3 < 0.0 or temp_k <= 0.0:
        raise ValueError("need n >= 0 and T > 0")
    mu = mu_eff_bohr * MUB
    return n_per_m3 * MU0 * mu * mu / (3.0 * KB * temp_k)


def er_vs_host(n_per_cm3: float = 1e16, temp_k: float = 300.0,
               mu_eff_bohr: float = 9.6,
               solubility_per_cm3: float = 1e18) -> Dict[str, object]:
    """Er3+ paramagnetism against the Si host diamagnetism.

    Er3+ (4f11, J = 15/2) is genuinely paramagnetic, so it is the strongest
    case the magnetic route has. It still loses to the host by ~500x at the
    stated dose and temperature. Both escape routes are reported: the dose
    that would win is above Er solubility in Si, and the temperature that
    would win is cryogenic.
    """
    chi_er = curie_susceptibility(n_per_cm3 * 1e6, mu_eff_bohr, temp_k)
    ratio = abs(CHI_SI) / chi_er if chi_er > 0 else float("inf")
    n_needed = n_per_cm3 * ratio
    return {
        "chi_er": chi_er,
        "chi_host": CHI_SI,
        "host_larger_by": ratio,
        "n_needed_per_cm3": n_needed,
        "n_exceeds_solubility": n_needed > solubility_per_cm3,
        "temp_needed_k": temp_k / ratio,
        "verdict": ("Er signal is below the host diamagnetism"
                    if ratio > 1.0 else "Er signal exceeds the host"),
    }


# --------------------------------------------------------------------------
# FAB-7 / BRG-1: write authority
# --------------------------------------------------------------------------

def zeeman_ev(b_t: float, g: float = 2.0) -> float:
    """Zeeman splitting in eV. g*muB*B."""
    return g * MUB_EV * b_t


def barrier_authority(b_t: float, barrier_ev: float,
                      g: float = 2.0) -> Dict[str, float]:
    """Fraction of a state barrier a magnetic field can modulate."""
    if barrier_ev <= 0.0:
        raise ValueError("barrier must be positive")
    split = zeeman_ev(b_t, g)
    return {"splitting_ev": split, "barrier_ev": barrier_ev,
            "fraction": split / barrier_ev,
            "percent": 100.0 * split / barrier_ev}


def coil_field(n_turns: int, current_a: float, radius_m: float) -> float:
    """On-axis centre field of a short coil, T. mu0*N*I/(2r)."""
    if radius_m <= 0.0 or n_turns <= 0:
        raise ValueError("need N > 0 and r > 0")
    return MU0 * n_turns * current_a / (2.0 * radius_m)


def current_density(current_a: float, area_m2: float) -> float:
    """A/m^2."""
    if area_m2 <= 0.0:
        raise ValueError("area must be positive")
    return current_a / area_m2


def electromigration_life(j_a_per_cm2: float, rated_years: float = 10.0,
                          limit_a_per_cm2: float = 1e6,
                          black_n: float = 2.0) -> Dict[str, float]:
    """Black's-equation lifetime scaling above the electromigration limit.

    t ~ J^-n. Only the ratio to the design limit is used, so the activation
    term cancels and no temperature is needed.
    """
    if j_a_per_cm2 <= 0.0:
        raise ValueError("current density must be positive")
    over = j_a_per_cm2 / limit_a_per_cm2
    years = rated_years * over ** (-black_n)
    return {"over_limit_by": over, "years": years,
            "hours": years * 365.25 * 24.0, "days": years * 365.25,
            "days_at_1pct_duty": years * 365.25 * 100.0}


def flux_concentrator_gain(area_base_m2: float, area_tip_m2: float,
                           mu_r: float = 1.0,
                           b_sat_t: float = 1.0,
                           b_in_t: float = 0.0) -> Dict[str, object]:
    """Field gain of a tapered flux concentrator, bounded by flux conservation.

    Gain is A_base/A_tip. ``mu_r`` governs collection efficiency, not gain,
    and multiplying by it is the error being checked. Saturation is reported
    because a concentrator above B_sat has stopped concentrating.
    """
    if area_tip_m2 <= 0.0 or area_base_m2 <= 0.0:
        raise ValueError("areas must be positive")
    gain = area_base_m2 / area_tip_m2
    return {"gain": gain, "claimed_if_mu_r_multiplied": gain * mu_r,
            "b_out_t": b_in_t * gain,
            "saturated": b_in_t * gain > b_sat_t, "b_sat_t": b_sat_t}


# --------------------------------------------------------------------------
# BRG-2 / BRG-7: timing and energy
# --------------------------------------------------------------------------

def eddy_diffusion_time(length_m: float, sigma_s_per_m: float = 5.96e7,
                        mu: float = MU0) -> float:
    """Magnetic diffusion time, s. tau ~ mu*sigma*L^2/pi^2."""
    if length_m <= 0.0:
        raise ValueError("length must be positive")
    return mu * sigma_s_per_m * length_m ** 2 / math.pi ** 2


def stored_energy(b_t: float, volume_m3: float) -> float:
    """Field energy, J. B^2*V/(2*mu0)."""
    if volume_m3 <= 0.0:
        raise ValueError("volume must be positive")
    return b_t ** 2 * volume_m3 / (2.0 * MU0)


def switching_power(b_t: float, volume_m3: float, time_s: float) -> float:
    """Power to establish or collapse a field in a given time, W."""
    if time_s <= 0.0:
        raise ValueError("time must be positive")
    return stored_energy(b_t, volume_m3) / time_s


# --------------------------------------------------------------------------
# Thermodynamic floors
# --------------------------------------------------------------------------

def landauer_ev(temp_k: float = 300.0) -> float:
    """kT*ln2 in eV -- the floor for erasing one bit."""
    if temp_k <= 0.0:
        raise ValueError("temperature must be positive")
    return KB * temp_k * math.log(2.0) / QE


def arrhenius_lifetime(barrier_ev: float, temp_k: float,
                       tau0_s: float = 1e-13) -> float:
    """Thermally activated lifetime, s."""
    if temp_k <= 0.0 or tau0_s <= 0.0:
        raise ValueError("need T > 0 and tau0 > 0")
    return tau0_s * math.exp(barrier_ev * QE / (KB * temp_k))


def retention_barrier_ev(years: float, temp_k: float,
                         tau0_s: float = 1e-13) -> float:
    """Barrier required for a given retention. The inverse of arrhenius_lifetime."""
    if years <= 0.0:
        raise ValueError("retention must be positive")
    t = years * 365.25 * 24.0 * 3600.0
    return (KB * temp_k / QE) * math.log(t / tau0_s)


# --------------------------------------------------------------------------
# BRG-4/5: addressing and drive
# --------------------------------------------------------------------------

def gradient_addressing(gradient_t_per_m: float, pitch_m: float,
                        channel_hz: float = 1e9,
                        g: float = 2.0) -> Dict[str, float]:
    """Zeeman frequency offset between neighbouring cells in a field gradient.

    See ``GRADIENT_NOTE``: the audited version of this calculation was 1000x
    low because it used a kHz-scale conversion where 28 GHz/T belongs.
    """
    if gradient_t_per_m < 0.0 or pitch_m <= 0.0:
        raise ValueError("need gradient >= 0 and pitch > 0")
    db = gradient_t_per_m * pitch_m
    offset = GYRO_HZ_PER_T * db
    return {
        "delta_b_t": db,
        "offset_hz": offset,
        "channel_hz": channel_hz,
        "shortfall": channel_hz / offset if offset > 0 else float("inf"),
        "gradient_needed_t_per_m": channel_hz / GYRO_HZ_PER_T / pitch_m,
        "resolvable": offset >= channel_hz,
    }


def rabi_time(b1_t: float, g: float = 2.0) -> float:
    """pi/2 Rabi time, s. pi*hbar/(g*muB*B1).

    The audited version substituted pi*hbar = 3.14e-15 s -- wrong by 19 orders
    and dimensionally wrong, seconds where J.s belongs.
    """
    if b1_t <= 0.0:
        raise ValueError("B1 must be positive")
    return math.pi * HBAR / (g * MUB * b1_t)


def rf_power_for_b1(b1_t: float, freq_hz: float = 1e10,
                    q: float = 1000.0,
                    mode_volume_m3: Optional[float] = None) -> Dict[str, float]:
    """Drive power to sustain a given B1 in a resonant mode, W.

    Mode volume defaults to (lambda/2)^3. Also reports the pulsed-ESR
    calibration, which is the empirical check: ~1 kW gives B1 ~ 1 mT, and
    B1 scales as sqrt(P).
    """
    if b1_t <= 0.0 or freq_hz <= 0.0 or q <= 0.0:
        raise ValueError("need B1 > 0, f > 0, Q > 0")
    if mode_volume_m3 is None:
        mode_volume_m3 = (2.998e8 / freq_hz / 2.0) ** 3
    u = b1_t ** 2 / (2.0 * MU0)
    energy = u * mode_volume_m3
    return {
        "energy_density_j_per_m3": u,
        "mode_volume_m3": mode_volume_m3,
        "stored_j": energy,
        "power_w": 2.0 * math.pi * freq_hz * energy / q,
        "esr_calibrated_w": 1e3 * (b1_t / 1e-3) ** 2,
    }


# --------------------------------------------------------------------------
# The replacement channel
# --------------------------------------------------------------------------

def valley_splitting_ev(strain: float, xi_u_ev: float = XI_U_EV) -> float:
    """Conduction-valley splitting from strain, eV. Xi_u * strain."""
    return xi_u_ev * strain


def piezoresistive_response(strain: float, pi_l: float = PI_L_110,
                            youngs_pa: float = E_SI_PA) -> Dict[str, float]:
    """dR/R from strain via piezoresistance. See ``PIEZO_NOTE``.

    ``fractures`` flags strain at or beyond the ~1-2% tensile fracture range
    of bulk Si, where the linear coefficient no longer applies anyway.
    """
    stress = youngs_pa * strain
    return {
        "strain": strain,
        "stress_pa": stress,
        "gauge_factor": pi_l * youngs_pa,
        "dr_over_r": pi_l * stress,
        "percent": 100.0 * pi_l * stress,
        "fractures": abs(strain) >= 0.01,
    }


def authority_ratio(strain: float, b_t: float, g: float = 2.0) -> float:
    """Strain write authority over magnetic, as a ratio of state splittings."""
    mag = zeeman_ev(b_t, g)
    if mag <= 0.0:
        return float("inf")
    return valley_splitting_ev(strain) / mag


# --------------------------------------------------------------------------

def main() -> None:
    w = 62
    print("MAGNETIC AUTHORITY IN DOPED Si\n" + "=" * w)

    print("\nFAB-1  magnetisation readout, 5um x 5um x 100nm cell at 50 mT")
    m = cell_moment(5e-6 * 5e-6 * 100e-9, 0.050)
    r = readout_shortfall(m)
    print(f"  moment          {r['moment_am2']:+.3e} A.m^2")
    print(f"  field at 1 mm   {r['field_t']:.3e} T = {r['field_gauss']:.2e} G")
    print(f"  Hall  SNR       {r['hall_snr']:.1e}   short by {r['hall_orders']:.1f} orders")
    print(f"  SQUID           short by {r['squid_orders']:.1f} orders")

    print("\nFAB-2  Er3+ at 1e16 cm^-3, 300 K, against the Si host")
    e = er_vs_host()
    print(f"  chi_Er {e['chi_er']:.2e}  vs chi_Si {e['chi_host']:.1e}"
          f"  -> host larger by {e['host_larger_by']:.0f}x")
    print(f"  dose to win {e['n_needed_per_cm3']:.1e} cm^-3"
          f" (above solubility: {e['n_exceeds_solubility']})")
    print(f"  temperature to win {e['temp_needed_k']:.1f} K")

    print("\nFAB-5  coil at 50nm x 200nm, 10 mA")
    j = current_density(10e-3, 50e-9 * 200e-9)
    life = electromigration_life(j / 1e4)
    print(f"  J = {j/1e4:.1e} A/cm^2, {life['over_limit_by']:.0f}x the 1e6 limit")
    print(f"  Black n=2: {life['hours']:.1f} h continuous,"
          f" {life['days_at_1pct_duty']:.0f} d at 1% duty")

    print("\nBRG-1  same coil at the limit this repo states elsewhere")
    b = coil_field(10, 1e10 * (100e-9 * 200e-9), 250e-9)
    print(f"  I_max {1e10 * 100e-9 * 200e-9 * 1e3:.2f} mA -> B = {b*1e3:.2f} mT"
          f"  ({1.0/b:.0f}x short of 1 T)")
    for bb, barrier in ((b, 0.100), (2.0, 0.100)):
        a = barrier_authority(bb, barrier)
        print(f"  at {bb*1e3:8.2f} mT: {a['splitting_ev']*1e3:.4f} meV"
              f" = {a['percent']:.4f}% of a 100 meV barrier")

    print("\nenergy and retention arithmetic")
    print(f"  0.01 eV = {0.01*QE*1e18:.4f} aJ   (documented as 1.6 aJ,"
          f" which is {1.6e-18/QE:.1f} eV)")
    print(f"  Landauer kT*ln2 at 300 K = {landauer_ev():.4f} eV"
          f"  -> a 0.01 eV write is below the bound")
    need = retention_barrier_ev(10.0, 358.15)
    print(f"  10 yr at 85 C needs Ea = {need:.2f} eV")
    for ea in (0.01, 0.1):
        print(f"    Ea = {ea} eV -> {arrhenius_lifetime(ea, 358.15):.2e} s")

    print("\nBRG-2  timing floors")
    for L in (1e-3, 1e-4, 1e-5):
        print(f"  eddy diffusion at {L*1e6:6.0f} um: {eddy_diffusion_time(L):.2e} s")
    print("  4 field rotations at the documented 100 ns switching = 400 ns")

    print("\nBRG-7  2 T over 1 cm^3")
    print(f"  stored {stored_energy(2.0, 1e-6):.2f} J,"
          f" {switching_power(2.0, 1e-6, 100e-9)/1e6:.1f} MW to switch in 100 ns")
    print(f"  dB/B < 1e-5 at 2 T = {2.0*1e-5*1e6:.0f} uT stability")

    print("\nBRG-5  gradient addressing")
    g = gradient_addressing(1000.0, 50e-9)
    print(f"  1000 T/m over 50 nm = {g['delta_b_t']*1e6:.0f} uT"
          f" -> {g['offset_hz']/1e6:.2f} MHz")
    print(f"  vs 1 GHz channels: {g['shortfall']:.0f}x short")
    print(f"  gradient needed: {g['gradient_needed_t_per_m']:.2e} T/m")

    print("\nBRG-4  drive")
    print(f"  T_Rabi at B1 = 0.1 T: {rabi_time(0.1)*1e12:.0f} ps"
          f" (documented 0.54 ps)")
    p = rf_power_for_b1(0.1)
    print(f"  power at 10 GHz, Q=1000: {p['power_w']/1e3:.0f} kW"
          f"; ESR-calibrated {p['esr_calibrated_w']/1e6:.0f} MW")

    print("\nBRG-6  the replacement channel")
    for eps in (0.01, 0.001):
        pr = piezoresistive_response(eps)
        print(f"  strain {eps*100:4.1f}%: valley split"
              f" {valley_splitting_ev(eps)*1e3:6.1f} meV,"
              f" dR/R {pr['percent']:5.1f}%"
              f"{'  [at/above fracture]' if pr['fractures'] else ''}")
    print(f"  gauge factor {piezoresistive_response(0.001)['gauge_factor']:.0f}")
    print(f"  strain authority over 2 T: {authority_ratio(0.001, 2.0):.0f}x"
          f" at 0.1% strain")

    print("\n" + "=" * w)
    print(GRADIENT_NOTE)
    print()
    print(PIEZO_NOTE)


if __name__ == "__main__":
    main()
