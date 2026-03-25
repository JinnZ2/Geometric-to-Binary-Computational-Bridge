"""
Quantum Wave Bridge Encoder
===========================
Encodes quantum wave geometry into binary using core quantum physics equations
and Gray-coded magnitude bands for all continuous quantities.

Equations implemented
---------------------
  de Broglie wavelength  :  λ = h / p
  Probability density    :  P = |ψ|²
  Particle-in-a-box      :  E_n = n²π²ℏ² / (2mL²)
  Uncertainty product    :  Δx·Δp  (compared to ℏ/2)
  Wave packet velocity   :  v_group = Δω / Δk  (two-point finite difference)

Bit layout (39 bits for 3-sample canonical input)
--------------------------------------------------
Per wave-function sample  (8 bits each):
  [high_amp   1b]       |ψ| ≥ 0.5 = 1
  [amp_mag    3b Gray]  |ψ| across 8 linear bands [0, 1]
  [phase_quad 1b]       φ in [0, π) = 1, [π, 2π) = 0
  [phase_mag  3b Gray]  φ across 8 linear phase bands [0, 2π)

Per momentum value  (4 bits each):
  [quantum    1b]       λ_dB < 1 nm = 1  (quantum regime)
  [lambda_mag 3b Gray]  λ_dB across 8 log bands (pm → µm)

Summary  (7 bits — appended when any section present):
  [prob_peak  1b]       any |ψ|² > 0.5 = 1
  [energy_mag 3b Gray]  mean energy across 8 log eV bands
  [uncertain  1b]       mean Δx·Δp > ℏ/2 (classically spread) = 1
  [vel_mag    2b Gray]  group velocity magnitude (4 log bands, m/s)
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
H_PLANCK = 6.626e-34   # Planck's constant (J·s)
HBAR     = H_PLANCK / (2 * math.pi)  # ℏ (J·s)
M_ELEC   = 9.109e-31   # Electron mass (kg)
EV       = 1.602e-19   # 1 eV in Joules

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_AMP_BANDS    = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]         # |ψ| [0, 1]
_PHASE_BANDS  = [0.0, math.pi/4, math.pi/2, 3*math.pi/4,
                 math.pi, 5*math.pi/4, 3*math.pi/2, 7*math.pi/4]            # φ [0, 2π)
_LAMBDA_BANDS = [0.0, 1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6]        # λ (m): pm→µm
_ENERGY_BANDS = [0.0, 1e-3, 1e-2, 0.1, 1.0, 10.0, 100.0, 1000.0]          # E (eV)
_VGRP_BANDS   = [0.0, 1e3, 1e5, 1e7]                                        # v_group (m/s)


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def de_broglie_wavelength(momentum_kg_m_s: float) -> float:
    """λ = h/p  (de Broglie wavelength). Returns inf if p=0."""
    if momentum_kg_m_s == 0.0:
        return float("inf")
    return H_PLANCK / abs(momentum_kg_m_s)


def probability_density(amplitude: float) -> float:
    """P = |ψ|²  (probability density for a normalised wave function)."""
    return amplitude * amplitude


def particle_in_box_energy(n: int, mass_kg: float, length_m: float) -> float:
    """
    E_n = n²π²ℏ² / (2mL²)

    Energy of the n-th quantum level for a 1D infinite square well.
    Returns 0 if mass or length is zero.
    """
    if mass_kg == 0.0 or length_m == 0.0:
        return 0.0
    return (n * n * math.pi * math.pi * HBAR * HBAR) / (2.0 * mass_kg * length_m * length_m)


def uncertainty_product(delta_x: float, delta_p: float) -> float:
    """
    Δx · Δp  (Heisenberg uncertainty product, J·m).

    The Heisenberg principle requires  Δx·Δp ≥ ℏ/2.
    Returns the product directly; compare to HBAR/2 to check the bound.
    """
    return delta_x * delta_p


def wave_packet_group_velocity(omega1: float, k1: float,
                                omega2: float, k2: float) -> float:
    """
    v_group = Δω / Δk  (finite-difference group velocity).

    For a wave packet composed of two components (ω₁,k₁) and (ω₂,k₂).
    Returns 0 if k₁=k₂ (degenerate case).
    """
    dk = k2 - k1
    if dk == 0.0:
        return 0.0
    return (omega2 - omega1) / dk


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class WaveBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes quantum wave-function geometry into a binary bitstring.

    Input geometry dict keys
    ------------------------
    amplitudes       : list of floats in [0, 1]  — |ψ| values (normalised)
    phases_rad       : list of floats in [0, 2π) — wave-function phases
    momenta_kg_m_s   : list of floats            — particle momenta (kg·m/s)
    energy_eV        : list of floats            — energy levels in eV
    uncertainty_pairs: list of [Δx, Δp] pairs   — position/momentum spreads

    For the canonical 39-bit output use 3 amplitude/phase samples and
    2 momentum values (the uncertainty and group-velocity summary are always
    appended when at least one section is present).
    """

    def __init__(self):
        super().__init__("wave")

    def from_geometry(self, geometry_data: dict):
        """Load quantum wave geometry data dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded wave geometry into a binary bitstring.

        Returns
        -------
        str
            A string of ``"0"`` and ``"1"`` characters.

        Raises
        ------
        ValueError
            If ``from_geometry`` has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        data = self.input_geometry
        bits = []
        any_section = False

        amplitudes  = data.get("amplitudes", [])
        phases_rad  = data.get("phases_rad", [])
        momenta     = data.get("momenta_kg_m_s", [])
        energies_eV = data.get("energy_eV", [])
        unc_pairs   = data.get("uncertainty_pairs", [])

        # ------------------------------------------------------------------
        # Section 1: wave-function samples  →  8 bits each
        #   [high_amp 1b][amp_mag 3b Gray][phase_quad 1b][phase_mag 3b Gray]
        # ------------------------------------------------------------------
        for amp, phase in zip(amplitudes, phases_rad):
            any_section = True
            abs_amp = abs(amp)
            abs_phase = abs(phase) % (2 * math.pi)

            high_amp   = "1" if abs_amp >= 0.5 else "0"
            amp_mag    = _gray_bits(abs_amp, _AMP_BANDS)
            phase_quad = "1" if abs_phase < math.pi else "0"
            phase_mag  = _gray_bits(abs_phase, _PHASE_BANDS)

            bits.append(high_amp)
            bits.append(amp_mag)
            bits.append(phase_quad)
            bits.append(phase_mag)

        # ------------------------------------------------------------------
        # Section 2: momenta  →  4 bits each
        #   [quantum 1b][lambda_mag 3b Gray]
        # ------------------------------------------------------------------
        for p in momenta:
            any_section = True
            lam = de_broglie_wavelength(p)
            quantum = "1" if (math.isfinite(lam) and lam < 1e-9) else "0"
            clamp_lam = lam if math.isfinite(lam) else 0.0
            bits.append(quantum)
            bits.append(_gray_bits(clamp_lam, _LAMBDA_BANDS))

        # ------------------------------------------------------------------
        # Summary  (7 bits, appended when any section has data)
        # ------------------------------------------------------------------
        if any_section:
            # prob_peak: any |ψ|² > 0.5
            prob_peak = "0"
            for amp in amplitudes:
                if probability_density(abs(amp)) > 0.5:
                    prob_peak = "1"
                    break

            # energy_mag: mean energy in eV (log-band Gray coded)
            mean_eV = (sum(energies_eV) / len(energies_eV)) if energies_eV else 0.0
            energy_mag = _gray_bits(abs(mean_eV), _ENERGY_BANDS)

            # uncertain: mean uncertainty product > ℏ/2
            if unc_pairs:
                mean_prod = sum(uncertainty_product(dx, dp) for dx, dp in unc_pairs) / len(unc_pairs)
                uncertain = "1" if mean_prod > HBAR / 2 else "0"
            else:
                uncertain = "0"

            # vel_mag: group velocity from first two momenta (E=p²/2m → ω=E/ℏ, k=p/ℏ)
            if len(momenta) >= 2:
                p1, p2 = momenta[0], momenta[1]
                E1 = (p1 * p1) / (2.0 * M_ELEC)
                E2 = (p2 * p2) / (2.0 * M_ELEC)
                omega1 = E1 / HBAR
                omega2 = E2 / HBAR
                k1 = p1 / HBAR
                k2 = p2 / HBAR
                v_grp = abs(wave_packet_group_velocity(omega1, k1, omega2, k2))
            else:
                v_grp = 0.0

            bits.append(prob_peak)
            bits.append(energy_mag)
            bits.append(uncertain)
            bits.append(_gray_bits(v_grp, _VGRP_BANDS, n_bits=2))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Quantum Wave Bridge Encoder — Physics Demo")
    print("=" * 60)

    # 1. de Broglie wavelength of an electron at 1 eV kinetic energy
    KE = 1.0 * EV               # 1 eV in Joules
    p_elec = math.sqrt(2 * M_ELEC * KE)
    lam = de_broglie_wavelength(p_elec)
    print(f"\n1. de Broglie wavelength (electron, KE = 1 eV)")
    print(f"   p = {p_elec:.4e} kg·m/s")
    print(f"   λ = h/p = {lam*1e9:.4f} nm  (expected ≈ 1.226 nm)")

    # 2. Probability density at peak amplitude
    psi_peak = 0.9
    P = probability_density(psi_peak)
    print(f"\n2. Probability density  |ψ|² at ψ = {psi_peak}")
    print(f"   P = {P:.4f}")

    # 3. Particle-in-a-box energy levels (electron, L = 1 nm)
    L = 1e-9   # 1 nm well
    print(f"\n3. Particle-in-a-box energy levels (electron, L = 1 nm)")
    for n in range(1, 4):
        E_J = particle_in_box_energy(n, M_ELEC, L)
        E_eV = E_J / EV
        print(f"   E_{n} = {E_eV:.4f} eV")

    # 4. Heisenberg uncertainty check
    delta_x = 1e-10   # 0.1 nm position uncertainty
    delta_p = 1e-24   # momentum uncertainty
    prod = uncertainty_product(delta_x, delta_p)
    limit = HBAR / 2
    print(f"\n4. Uncertainty product  Δx·Δp")
    print(f"   Δx = {delta_x:.1e} m,  Δp = {delta_p:.1e} kg·m/s")
    print(f"   Δx·Δp = {prod:.4e} J·m")
    print(f"   ℏ/2   = {limit:.4e} J·m  → bound {'satisfied' if prod >= limit else 'violated'}")

    # 5. Group velocity of a free-electron wave packet
    p1 = 1.0 * p_elec
    p2 = 1.1 * p_elec
    E1 = p1**2 / (2 * M_ELEC)
    E2 = p2**2 / (2 * M_ELEC)
    v_g = wave_packet_group_velocity(E1/HBAR, p1/HBAR, E2/HBAR, p2/HBAR)
    print(f"\n5. Wave-packet group velocity (free electron, 1–1.1 eV spread)")
    print(f"   v_group = Δω/Δk = {v_g:.4e} m/s  (expected ~p/m ≈ {p_elec/M_ELEC:.4e} m/s)")

    # Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "amplitudes":        [0.8, 0.4, 0.95],
        "phases_rad":        [0.3, 2.1, 5.8],
        "momenta_kg_m_s":    [p_elec, 1.5 * p_elec],
        "energy_eV":         [1.0, 4.0, 9.0],
        "uncertainty_pairs": [[1e-10, 1e-24], [5e-11, 2e-24]],
    }

    encoder = WaveBridgeEncoder()
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nInput geometry keys : {list(geometry.keys())}")
    print(f"Binary output       : {binary}")
    print(f"Total bits          : {len(binary)}")
    print(f"Report              : {encoder.report()}")
