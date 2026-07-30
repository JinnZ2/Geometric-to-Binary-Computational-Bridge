"""Common-mode suppression in a bifilar write coil: R2-1..8. Stdlib only.

Settles the arithmetic in ``Proposal-addendum.md``'s R_2 protocol. The geometry
in that document is self-consistent -- counter-wound bifilar plus differential
drive adds, plus common-mode drive cancels -- and the two-mode measurement
procedure is correct and standard. What does not follow is the conclusion.

THE MODE MISMATCH (R2-1)
------------------------
The stated purpose is to show "the 5 ps Holographic Write pulse can be executed
without collapsing spin coherence". But the write pulse *is* the differential
drive: its field is the one mode the geometry is built to PASS, at full
amplitude, by design. R_2 measures rejection of the mode the write pulse does
not use, then concludes something about the mode it does.

What R_2 genuinely de-risks: ground bounce, shield currents, capacitive pickup
from the generator, EMI. All really common-mode, all worth suppressing. State
that as the purpose and the protocol becomes true.

WHAT THE WRITE PULSE ACTUALLY DOES TO A SPIN (R2-8) -- the premise is inverted
------------------------------------------------------------------------------
Not in the original audit, and it decides the document's subject. At the field
an on-chip coil can legally deliver -- 5.03 mT at the electromigration limit,
from ``magnetic_authority.py`` -- a 5 ps pulse rotates a spin by

    theta = 2*pi*gamma*B*t = 4.42 mrad = 0.14% of a pi pulse

and a 5 ps pi pulse would need B1 = 3.57 T, which is 710x the coil. So the
write pulse cannot collapse spin coherence: it is ~700x too weak to move the
spin at all. The risk is not that the write pulse is too violent for the spins;
it is that the write does not happen. Engineering a 60 dB suppression of a
transient that could at most produce 4 mrad of unwanted rotation is optimising
the wrong quantity by three orders.

R_2 IS NOT MEASURABLE AS DEFINED (R2-2)
---------------------------------------
``R_2 = B_CM,input / B_CM,residual`` where the numerator is the field "WITHOUT
cancellation". The cancellation *is* the geometry; removing it means unwinding
a helix and building a different device. So the numerator is necessarily
theoretical, R_2 is a model-vs-measurement ratio rather than a measurement, and
any modelling error in the numerator inflates the reported suppression in the
flattering direction.

The replacement uses only the two drives already specified, and both terms are
measured::

    CMRR = (response to DM drive) / (response to CM drive)

at matched input current, same sensor, same position. Note the order: the
original audit wrote CM/DM, which is the reciprocal and goes to zero for a good
structure. A rejection ratio should be large when rejection is good.

TWO MISMATCH CHANNELS, AND THEY ADD IN QUADRATURE
-------------------------------------------------
Amplitude mismatch and arrival-time skew are independent, so
``Delta_total = sqrt(Delta_amp^2 + Delta_time^2)`` and both must independently
reach 1e-3. Two channels at 1e-2 give 37 dB, not 40.

REJECTION IS FREQUENCY-DEPENDENT, SO A SINGLE R_2 IS UNDERSPECIFIED
-------------------------------------------------------------------
Skew-limited rejection is ``1 / (2 |sin(pi f tau)|)``. At 5 fs skew that is
90 dB at 1 GHz and 44 dB at 200 GHz. A CMRR measured at 1 GHz says nothing
about the top of a 5 ps pulse's spectrum, so the criterion has to name a
frequency.

The two natural criteria differ by ~6x, and the original audit used the looser
one without saying so:

    time-domain peak residual, tau <= T/(1.4 R)      3.57 fs -> 0.31 um
    spectral, at f_max = 1/T,   tau <= 1/(2 pi f R)  0.80 fs -> 0.068 um

The time-domain figure is the right one if the concern is peak unwanted
rotation; the spectral figure is right if a narrow-band transition sits near
the top of the band.

THE SPIN SYSTEM IS UNSPECIFIED, AND Si DOES NOT SUPPLY ONE (R2-7)
-----------------------------------------------------------------
Perfect crystalline Si has all bonding electrons paired -- no unpaired spins --
and Si-28 at 92.2% natural abundance has I = 0. This is the seventh file in the
set to require a magnetic degree of freedom the material does not have.

The one real candidate is P donors in isotopically enriched 28Si, which is
genuinely superb (T2 reaching seconds) but needs enrichment, typically < 10 K,
and is a *different device* from the strain/tensor encoding in the other six
documents.

Fork to name before this test is worth running:

    strain      -> there is no spin coherence to protect and this document is
                   moot. The piezoresistive read path has no coherence
                   requirement at all.
    donor spin  -> it is a spin qubit, and the tensor encoding, octahedral
                   state space and Frenkel-pair gate set do not apply to it.

The two branches share no physics.

WHAT SURVIVES, AND IT IS NOT LITTLE
-----------------------------------
The two-mode drive protocol is correct and standard -- keep it verbatim.
"Latency-free: works at the speed of physics, no control loop" is right, and
right for the right reason: passive symmetry beats feedback at ps timescales.
"Fabrication-bound, not algorithm-bound" is the correct framing, and it is what
makes the tolerance number the whole story.

One caveat on the latency argument: the document rejects "algorithmic"
solutions as latency-bound, which conflates a control loop with a pulse
sequence. Composite and dynamically-corrected pulses (BB1, CORPSE,
SCROFULOUS) and refocusing sequences (Hahn echo, CPMG) suppress rotation error
to second order or better and are OPEN-LOOP -- no feedback, no latency. They
preserve exactly the property the document wants.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

__all__ = [
    "C_LIGHT", "MU0", "MUB", "PLANCK", "GAMMA_HZ_PER_T", "N_SI",
    "COIL_FIELD_T", "PULSE_S", "PROBES",
    "to_db", "from_db", "rejection_from_mismatch", "combine_mismatch",
    "matching_for_rejection", "coil_size_for_rejection",
    "skew_for_rejection", "skew_rejection_at", "path_length_for_skew",
    "pulse_bandwidth", "selectivity", "zeeman_hz",
    "rotation_angle", "field_for_pi_pulse", "write_pulse_authority",
    "area_stability_for_infidelity", "infidelity_from_area_error",
    "probe_shortfall", "cmrr", "main",
]

C_LIGHT = 2.99792458e8
MU0 = 4e-7 * math.pi
MUB = 9.2740100783e-24
PLANCK = 6.62607015e-34
GAMMA_HZ_PER_T = 2.0 * MUB / PLANCK      # 28.0 GHz/T, g = 2
N_SI = 3.5                                # on-chip group index, near IR

COIL_FIELD_T = 5.03e-3                    # legal on-chip coil, magnetic_authority
PULSE_S = 5e-12                           # the stated write pulse

#: Probe bandwidths, Hz. An OPM is an atomic-vapour spin-precession device and
#: is fundamentally DC-to-kHz; it is not a ps-transient probe at any price.
PROBES: Dict[str, float] = {
    "opm_typical": 1e3,
    "opm_best": 1e4,
    "sampling_scope": 1.1e11,
    "realtime_scope_fastest": 1.6e11,
    "mo_sampling_100fs": 1.0e13,
}


def to_db(ratio: float) -> float:
    """Field/amplitude ratio to dB. 20*log10, not 10*log10."""
    if ratio <= 0.0:
        raise ValueError("ratio must be positive")
    return 20.0 * math.log10(ratio)


def from_db(db: float) -> float:
    return 10.0 ** (db / 20.0)


# ---------------------------------------------------------------------------
# R2-3: geometric mismatch
# ---------------------------------------------------------------------------

def rejection_from_mismatch(fractional_mismatch: float) -> float:
    """``R = 1/Delta``. Residual scales with fractional arm mismatch."""
    if fractional_mismatch <= 0.0:
        raise ValueError("mismatch must be positive")
    return 1.0 / fractional_mismatch


def combine_mismatch(*channels: float) -> float:
    """Independent mismatch channels add in quadrature.

    Amplitude mismatch and arrival-time skew are independent, so each must
    reach the target on its own: two channels at 1e-2 give 37 dB, not 40.
    """
    if not channels or any(c < 0.0 for c in channels):
        raise ValueError("need at least one non-negative channel")
    return math.sqrt(sum(c * c for c in channels))


def matching_for_rejection(rejection: float, coil_dimension_m: float) -> float:
    """Absolute matching tolerance, metres, for a target rejection."""
    if rejection <= 0.0 or coil_dimension_m <= 0.0:
        raise ValueError("need rejection > 0 and dimension > 0")
    return coil_dimension_m / rejection


def coil_size_for_rejection(rejection: float, matching_m: float) -> float:
    """Coil dimension needed to reach a rejection at a given matching.

    The trap: growing the coil to relax the fractional tolerance drops
    field-per-amp, which lands back in the shortfall found in
    ``magnetic_authority.py``.
    """
    if rejection <= 0.0 or matching_m <= 0.0:
        raise ValueError("need rejection > 0 and matching > 0")
    return rejection * matching_m


# ---------------------------------------------------------------------------
# R2-4: timing
# ---------------------------------------------------------------------------

def skew_for_rejection(rejection: float, pulse_s: float = PULSE_S,
                       criterion: str = "time_domain") -> float:
    """Arrival-time match needed for a rejection, seconds.

    ``time_domain``: peak residual is ``tau * max|dB/dt|``, and a Gaussian of
    FWHM T has ``max|dB/dt| = 1.4 B/T``, so ``tau <= T/(1.4 R)``. Use this when
    the concern is peak unwanted rotation.

    ``spectral``: rejection at frequency f is ``1/(2 pi f tau)``, worst at the
    top of the band ``f_max ~ 1/T``, so ``tau <= 1/(2 pi f_max R)``. Use this
    when a narrow-band transition sits near the top of the band. About 6x
    tighter than the time-domain figure.
    """
    if rejection <= 0.0 or pulse_s <= 0.0:
        raise ValueError("need rejection > 0 and pulse > 0")
    if criterion == "time_domain":
        return pulse_s / (1.4 * rejection)
    if criterion == "spectral":
        return 1.0 / (2.0 * math.pi * (1.0 / pulse_s) * rejection)
    raise ValueError("criterion must be 'time_domain' or 'spectral'")


def skew_rejection_at(freq_hz: float, skew_s: float) -> float:
    """Skew-limited rejection at one frequency: ``1/(2|sin(pi f tau)|)``.

    This is why a single R_2 number is underspecified. At 5 fs skew the same
    structure gives 90 dB at 1 GHz and 44 dB at 200 GHz.
    """
    if freq_hz <= 0.0 or skew_s < 0.0:
        raise ValueError("need f > 0 and skew >= 0")
    if skew_s == 0.0:
        return float("inf")
    s = abs(math.sin(math.pi * freq_hz * skew_s))
    if s <= 0.0:
        return float("inf")
    return 1.0 / (2.0 * s)


def path_length_for_skew(skew_s: float, index: float = N_SI) -> float:
    """Path-length match, metres, for a time skew on chip."""
    if skew_s < 0.0 or index <= 0.0:
        raise ValueError("need skew >= 0 and index > 0")
    return skew_s * C_LIGHT / index


# ---------------------------------------------------------------------------
# R2-5: bandwidth vs splitting
# ---------------------------------------------------------------------------

def pulse_bandwidth(pulse_s: float = PULSE_S,
                    convention: str = "inverse") -> float:
    """Bandwidth of a short pulse, Hz.

    ``inverse`` = 1/dt (the loosest, and what the audit's "200 GHz" uses),
    ``gaussian`` = 0.441/dt, ``sech2`` = 0.315/dt. The conclusion is robust
    across all three, but the quoted ratio is not, so name the convention.
    """
    if pulse_s <= 0.0:
        raise ValueError("pulse must be positive")
    factors = {"inverse": 1.0, "gaussian": 0.441, "sech2": 0.315}
    if convention not in factors:
        raise ValueError(f"convention must be one of {sorted(factors)}")
    return factors[convention] / pulse_s


def zeeman_hz(b_t: float, g: float = 2.0) -> float:
    """Zeeman splitting in Hz. 28.0 GHz/T at g = 2."""
    return (g / 2.0) * GAMMA_HZ_PER_T * b_t


def selectivity(b_t: float, pulse_s: float = PULSE_S,
                convention: str = "inverse") -> Dict[str, object]:
    """Can a pulse of this length address one transition at this field?

    Selectivity needs bandwidth << splitting. A ratio at or above 1 means the
    pulse drives every transition plus everything off-resonant, so a
    "pi-pulse" of that bandwidth is not a pi-pulse.
    """
    bw = pulse_bandwidth(pulse_s, convention)
    split = zeeman_hz(b_t)
    if split <= 0.0:
        raise ValueError("field must be positive")
    ratio = bw / split
    return {"bandwidth_hz": bw, "splitting_hz": split, "ratio": ratio,
            "selective": ratio < 1.0, "convention": convention}


# ---------------------------------------------------------------------------
# R2-8: what the write pulse does to a spin
# ---------------------------------------------------------------------------

def rotation_angle(b_t: float, duration_s: float, g: float = 2.0) -> float:
    """Rotation produced by a rectangular pulse, radians. ``2 pi gamma B t``."""
    if duration_s < 0.0:
        raise ValueError("duration must be non-negative")
    return 2.0 * math.pi * (g / 2.0) * GAMMA_HZ_PER_T * b_t * duration_s


def field_for_pi_pulse(duration_s: float, g: float = 2.0) -> float:
    """B1 needed for a pi pulse of this duration, tesla."""
    if duration_s <= 0.0:
        raise ValueError("duration must be positive")
    return math.pi / (2.0 * math.pi * (g / 2.0) * GAMMA_HZ_PER_T * duration_s)


def write_pulse_authority(b_t: float = COIL_FIELD_T,
                          duration_s: float = PULSE_S) -> Dict[str, float]:
    """How much of a pi pulse the write field actually delivers.

    The finding that inverts the document's premise: at the field an on-chip
    coil can legally deliver, a 5 ps pulse is ~700x too weak to rotate a spin,
    so there is no coherence collapse to engineer against.
    """
    theta = rotation_angle(b_t, duration_s)
    b_pi = field_for_pi_pulse(duration_s)
    return {"theta_rad": theta, "theta_mrad": theta * 1e3,
            "fraction_of_pi": theta / math.pi,
            "percent_of_pi": 100.0 * theta / math.pi,
            "b_for_pi_t": b_pi, "field_shortfall": b_pi / b_t}


# ---------------------------------------------------------------------------
# The well-posed criterion: pulse area reproducibility
# ---------------------------------------------------------------------------

def infidelity_from_area_error(fractional_area_error: float,
                               target_rad: float = math.pi) -> float:
    """``(delta theta)^2 / 4`` for a rotation error on a target angle.

    The fractional area error multiplies the TARGET angle to give the absolute
    rotation error, which is the step the original audit skipped.
    """
    if fractional_area_error < 0.0:
        raise ValueError("area error must be non-negative")
    dtheta = fractional_area_error * target_rad
    return dtheta * dtheta / 4.0


def area_stability_for_infidelity(infidelity: float,
                                  target_rad: float = math.pi) -> Dict[str, float]:
    """Area stability needed for a target infidelity.

    Corrects the audit: infidelity 1e-4 gives ``delta theta = 0.02 rad``, which
    is an ABSOLUTE rotation error. The FRACTIONAL area stability is
    ``0.02/pi = 0.64%``, not 2%. The 2% figure is the right answer to a
    different question -- it corresponds to infidelity 1e-3.
    """
    if infidelity <= 0.0:
        raise ValueError("infidelity must be positive")
    dtheta = 2.0 * math.sqrt(infidelity)
    return {"infidelity": infidelity, "dtheta_rad": dtheta,
            "fractional": dtheta / target_rad,
            "percent": 100.0 * dtheta / target_rad}


# ---------------------------------------------------------------------------
# R2-6: probes, and R2-2: the measurable replacement
# ---------------------------------------------------------------------------

def probe_shortfall(needed_hz: float,
                    probes: Optional[Dict[str, float]] = None
                    ) -> List[Tuple[str, float, float, bool]]:
    """(name, bandwidth, shortfall, adequate) for each probe."""
    if needed_hz <= 0.0:
        raise ValueError("needed bandwidth must be positive")
    if probes is None:
        probes = PROBES
    out = []
    for name, bw in sorted(probes.items(), key=lambda kv: kv[1]):
        out.append((name, bw, needed_hz / bw, bw >= needed_hz))
    return out


def cmrr(dm_response: float, cm_response: float) -> Dict[str, float]:
    """``CMRR = DM response / CM response``, both measured.

    Note the order. The original audit wrote CM/DM, which is the reciprocal and
    tends to zero for a good structure; a rejection ratio should be large when
    rejection is good. Nothing here is theoretical, so this replaces R_2's
    model-vs-measurement ratio with a measurement.
    """
    if cm_response <= 0.0:
        raise ValueError("common-mode response must be positive; "
                         "a zero reading means the probe is not sensitive "
                         "enough, which is a different result")
    if dm_response <= 0.0:
        raise ValueError("differential response must be positive")
    r = dm_response / cm_response
    return {"cmrr": r, "db": to_db(r), "dm": dm_response, "cm": cm_response}


# ---------------------------------------------------------------------------

def main() -> None:
    print("BIFILAR TRANSIENT SUPPRESSION\n" + "=" * 68)

    print("\nR2-8  what the write pulse does to a spin -- settle this first")
    w = write_pulse_authority()
    print(f"  at {COIL_FIELD_T*1e3:.2f} mT for {PULSE_S*1e12:.0f} ps: "
          f"theta = {w['theta_mrad']:.2f} mrad = {w['percent_of_pi']:.3f}% of pi")
    print(f"  B1 for a 5 ps pi pulse: {w['b_for_pi_t']:.2f} T "
          f"({w['field_shortfall']:.0f}x the coil)")
    print("  the write pulse is ~700x too weak to collapse anything.")
    print("  the stated worry is inverted: the risk is that the write fails.")

    print("\nR2-3  mismatch -> rejection, R = 1/Delta")
    print(f"  {'coil':>8} {'match':>9} {'Delta':>9} {'R':>8} {'dB':>7}")
    for dim, match in ((10e-6, 10e-9), (10e-6, 100e-9), (10e-6, 1e-6),
                       (100e-6, 100e-9)):
        d = match / dim
        print(f"  {dim*1e6:>6.0f}um {match*1e9:>6.0f}nm {d:>9.1e} "
              f"{rejection_from_mismatch(d):>8.1f} {to_db(1/d):>7.1f}")
    print("  'sub-um' at 100 nm -> 40 dB; at 1 um -> 20 dB.")
    print("  the shortfall against 60 dB is 20-40 dB, not 20.")
    print(f"  60 dB at 100 nm matching needs a "
          f"{coil_size_for_rejection(1e3, 100e-9)*1e6:.0f} um coil, which drops")
    print("  field-per-amp back into the magnetic_authority shortfall.")

    print("\n  two independent channels add in quadrature:")
    for a, t in ((1e-2, 1e-2), (1e-3, 1e-2), (1e-3, 1e-3)):
        d = combine_mismatch(a, t)
        print(f"    amp {a:.0e} + skew {t:.0e} -> {to_db(1/d):.1f} dB")

    print("\nR2-4  timing, two criteria that differ by 6x")
    for crit in ("time_domain", "spectral"):
        tau = skew_for_rejection(1e3, criterion=crit)
        print(f"  60 dB, {crit:>11}: tau <= {tau*1e15:5.2f} fs "
              f"= {path_length_for_skew(tau)*1e6:.3f} um path")
    print("  the audit's 5 fs / 0.43 um is the time-domain criterion.")
    print("  rejection at 5 fs skew, versus frequency:")
    for f in (1e9, 1e10, 1e11, 2e11):
        print(f"    {f/1e9:>6.0f} GHz -> {to_db(skew_rejection_at(f, 5e-15)):5.1f} dB")
    print("  => R_2 without a stated frequency is underspecified.")

    print("\nR2-5  a 5 ps pulse cannot be transition-selective")
    for conv in ("inverse", "gaussian", "sech2"):
        row = f"  {conv:>9}: {pulse_bandwidth(convention=conv)/1e9:6.1f} GHz"
        for b in (1.0, 2.0):
            s = selectivity(b, convention=conv)
            row += f"   {s['ratio']:4.2f}x at {b:g} T"
        print(row + f"   selective: {selectivity(2.0, convention=conv)['selective']}")
    print("  ratio >= 1 in every convention. the '4-7x' figure is the 1/dt")
    print("  convention; Gaussian gives 1.6-3.2x. conclusion unchanged.")

    print("\nR2-6  probe bandwidth against 200 GHz")
    for name, bw, short, ok in probe_shortfall(2e11):
        tag = "OK" if ok else f"{short:.1e}x short"
        print(f"  {name:>24}: {bw:.1e} Hz   {tag}")
    print(f"  OPM is {math.log10(2e11/1e3):.1f} orders short -- it is an atomic")
    print("  vapour precession device, DC-to-kHz by construction.")
    print("  the right tool is magneto-optic (Faraday/Kerr) pump-probe sampling:")
    print("  resolution set by the ~100 fs optical pulse, no digitizer in path.")
    print("  note electro-optic sampling reads E, not B -- use MO for B.")

    print("\nThe well-posed criterion: shot-to-shot pulse AREA")
    for inf in (1e-3, 1e-4, 1e-5):
        a = area_stability_for_infidelity(inf)
        print(f"  infidelity {inf:.0e}: dtheta {a['dtheta_rad']:.4f} rad, "
              f"area stability {a['percent']:.3f}%")
    print("  the audit's '2e-2 (2%)' conflates the absolute rotation error in")
    print("  radians with the fractional area error. 2% is the 1e-3 answer;")
    print("  1e-4 needs 0.64%.")

    print("\nR2-2  the measurable replacement")
    demo = cmrr(dm_response=1.0, cm_response=1e-2)
    print(f"  CMRR = DM/CM = {demo['cmrr']:.0f} = {demo['db']:.1f} dB, "
          "both terms measured, no model, no unwinding")


if __name__ == "__main__":
    main()
