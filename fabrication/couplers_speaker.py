"""
couplers_speaker.py  (fabrication/)

Dynamic-speaker coupler: a TRUE three-way gyrator chain

        electrical  <--BL-->  mechanical  <--Sd-->  acoustic

  BL : force factor  [T·m]       (electrical ⇌ mechanical)
       V = BL·v  ;  F = BL·I
  Sd : cone area     [m²]        (mechanical ⇌ acoustic)
       p = F/Sd  ;  Q = Sd·v

Free-cone (mechanical) resonance dominates all three:
    f_s = 1 / (2π·√(Mms·Cms))

Each substrate measurement should converge on f_s within tolerance.
Three independent paths give us triangulation: when exactly two
agree, the third tells us which side carries the error.

Thiele-Small derived quantities used for tolerance and Q prediction:
    Q_ms = (1/Rms)·√(Mms/Cms)
    Q_es = (Re/BL²)·√(Mms/Cms)
    Q_ts = Q_ms·Q_es / (Q_ms + Q_es)

License: CC0. Stdlib only.
"""
import math


def speaker_fs_Hz(Mms, Cms):
    """f_s = 1/(2π·√(Mms·Cms)) -- free-cone mechanical resonance."""
    return 1.0 / (2 * math.pi * math.sqrt(Mms * Cms))


def speaker_Q_mech(Mms, Cms, Rms):
    """Open-circuit (mechanical-only) Q."""
    return (1.0 / Rms) * math.sqrt(Mms / Cms)


def speaker_Q_elec(Mms, Cms, Re, BL):
    """Electrical Q (driver damping from reflected impedance)."""
    return (Re / (BL ** 2)) * math.sqrt(Mms / Cms)


def speaker_Q_total(Mms, Cms, Rms, Re, BL):
    """Total Q = parallel combination of mechanical and electrical."""
    Qm = speaker_Q_mech(Mms, Cms, Rms)
    Qe = speaker_Q_elec(Mms, Cms, Re, BL)
    return (Qm * Qe) / (Qm + Qe)


def speaker_motional_impedance_peak(Mms, Cms, Rms, Re, BL):
    """Peak electrical |Z| at f_s:  Z_max = Re + BL²/Rms."""
    return Re + (BL ** 2) / Rms


def speaker_coupling_quality(Mms, Cms, Rms, Re, BL, Sd):
    """
    Single 0..1 scalar summarizing how strongly the three domains are
    locked together at f_s. Higher = tighter cross-substrate agreement
    expected.

    Combines:
      - electromechanical coupling   κ²_em ≈ BL² / (Rms·Re)  (clipped)
      - radiation efficiency proxy   η_rad ≈ Sd / Sd_ref     (clipped)
    """
    kappa2 = (BL ** 2) / max(Rms * Re, 1e-12)
    # clip into [0, 1]: 1.0 corresponds to BL² ≈ Rms·Re (well-matched)
    kappa2 = min(1.0, kappa2 / 1.0)
    # Sd_ref = 30 cm² is a small full-range driver baseline; scaled to
    # cap at 1.0 for ≥ that size.
    eta_rad = min(1.0, Sd / 30e-4)
    return math.sqrt(kappa2 * eta_rad)


def expected_agreement_pct(coupling_quality):
    """
    Pairwise agreement budget across acoustic / electrical / mechanical.
    With tight coupling (q ≥ 0.7) all three should land within ≥ 97%.
    Loose coupling (q < 0.3) widens the budget to 92% because the
    radiation peak smears, and the electrical peak gets dragged by
    motor nonlinearities.
    """
    if coupling_quality >= 0.7:
        return 0.97
    if coupling_quality >= 0.4:
        return 0.95
    if coupling_quality >= 0.2:
        return 0.93
    return 0.90
