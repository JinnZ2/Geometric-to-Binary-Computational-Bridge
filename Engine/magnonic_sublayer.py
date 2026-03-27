"""
Magnonic Sub-Layer
==================
Magnonic physics as a sub-layer of Layer 0 (Electromagnetics).
Spin wave propagation, damping, and coupling interfaces.

This is not a simulation of a specific magnonic device.
It is the equation inventory for spin-wave energy transport
in magnetic media, with coupling interfaces to:
  - Layer 0 (EM fields, plasma frequency, skin depth)
  - Layer 1 (magnetospheric plasma spin waves)
  - Quartz/iron-defect crystal work (magnon-phonon coupling)

License: CC0 — No Rights Reserved
"""

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MU_0      = 4 * np.pi * 1e-7       # permeability of free space (T·m/A)
GAMMA     = 1.7608597e11            # gyromagnetic ratio (rad/s/T)
MU_B      = 9.2740100783e-24        # Bohr magneton (J/T)
HBAR      = 1.0545718e-34           # reduced Planck constant (J·s)
K_B       = 1.380649e-23            # Boltzmann constant (J/K)
E_CHARGE  = 1.602176634e-19         # elementary charge (C)
M_E       = 9.1093837015e-31        # electron mass (kg)
EPSILON_0 = 8.8541878128e-12        # permittivity of free space (F/m)


# ─────────────────────────────────────────────────────────────────────────────
# CORE MAGNONIC EQUATIONS
# ─────────────────────────────────────────────────────────────────────────────

def dispersion_relation(k, H0, M_s, A_ex, theta_deg=90.0):
    """
    Full magnon dispersion relation (Damon-Eshbach / backward volume).

    Uses the bulk magnetostatic form with exchange correction:
      ω² = (ω_H + ω_M λ_ex k²)(ω_H + ω_M λ_ex k² + ω_M sin²θ)

    At k=0 this recovers the Kittel FMR frequency:
      ω² = ω_H · (ω_H + ω_M sin²θ)

    Note: this is the bulk formula.  Thin-film geometries require additional
    thickness-dependent form factors (Kalinikos-Slavin).

    Parameters
    ----------
    k         : wavevector (rad/m)
    H0        : applied field (T)
    M_s       : saturation magnetization (A/m)
    A_ex      : exchange stiffness (J/m)
    theta_deg : angle between k and M (degrees)
                90° = Damon-Eshbach (surface wave)
                 0° = backward volume wave

    Returns
    -------
    angular frequency ω (rad/s)
    """
    theta   = np.radians(theta_deg)
    omega_H = GAMMA * MU_0 * H0
    omega_M = GAMMA * MU_0 * M_s
    lambda_ex = (2 * A_ex) / (MU_0 * M_s ** 2)

    ex_term = omega_M * lambda_ex * k ** 2
    term1   = omega_H + ex_term
    term2   = omega_H + ex_term + omega_M * np.sin(theta) ** 2
    return np.sqrt(np.maximum(term1 * term2, 0.0))


def group_velocity(k, H0, M_s, A_ex, theta_deg=90.0, dk=1e4):
    """
    Group velocity v_g = dω/dk (numerical derivative).

    Parameters
    ----------
    dk : finite-difference step (rad/m); default 1e4 is safe for k ≥ 1e5.

    Returns
    -------
    v_g (m/s)
    """
    omega_plus  = dispersion_relation(k + dk / 2, H0, M_s, A_ex, theta_deg)
    omega_minus = dispersion_relation(k - dk / 2, H0, M_s, A_ex, theta_deg)
    return (omega_plus - omega_minus) / dk


def propagation_length(k, H0, M_s, A_ex, alpha, theta_deg=90.0):
    """
    Spin wave propagation length before amplitude decays to 1/e.

    l_prop = v_g · τ = v_g / (α · ω)

    Parameters
    ----------
    alpha : Gilbert damping constant (dimensionless)

    Returns
    -------
    propagation length (m); 0.0 if undamped or dispersionless.

    Note: scalar inputs only — pass individual k values, not arrays.
    """
    vg    = group_velocity(k, H0, M_s, A_ex, theta_deg)
    omega = float(dispersion_relation(k, H0, M_s, A_ex, theta_deg))
    if omega == 0.0 or alpha == 0.0:
        return 0.0
    return abs(vg) / (alpha * omega)


def exchange_length(A_ex, M_s):
    """
    Exchange length — crossover scale where exchange dominates dipolar.

    l_ex = sqrt(2A / μ₀M_s²)

    Returns
    -------
    exchange length (m)
    """
    return np.sqrt((2 * A_ex) / (MU_0 * M_s ** 2))


def magnon_energy(omega):
    """Single magnon energy E = ℏω (J)."""
    return HBAR * omega


def thermal_magnon_number(omega, T):
    """
    Bose-Einstein occupation number for magnons at temperature T.

    ⟨n⟩ = 1 / (exp(ℏω / k_B T) - 1)

    Returns 0.0 for T ≤ 0 or ω ≤ 0.
    """
    if T <= 0 or omega <= 0:
        return 0.0
    x = (HBAR * omega) / (K_B * T)
    if x > 500:
        return 0.0
    return 1.0 / (np.exp(x) - 1.0)


def magnon_specific_heat_contribution(omega, T, n_modes=1):
    """
    Magnonic contribution to specific heat per mode (Einstein model).

    C = k_B · x² · eˣ / (eˣ - 1)²   where x = ℏω / k_B T

    Returns
    -------
    specific heat contribution per mode (J/K)
    """
    if T <= 0 or omega <= 0:
        return 0.0
    x = (HBAR * omega) / (K_B * T)
    if x > 500:
        return 0.0
    ex = np.exp(x)
    return n_modes * K_B * x ** 2 * ex / (ex - 1) ** 2


# ─────────────────────────────────────────────────────────────────────────────
# DAMPING CHANNELS
# ─────────────────────────────────────────────────────────────────────────────

def magnon_magnon_scattering_rate(omega, T):
    """
    Approximate magnon-magnon scattering rate.

    Scales as T² at low T (two-magnon), T³ at high T (three-magnon).
    This is a simplified model — the full calculation requires the magnon
    density of states and four-magnon interaction matrix elements.

    Returns
    -------
    scattering rate (1/s)
    """
    if omega <= 0:
        return 0.0
    n = thermal_magnon_number(omega, T)
    return n * omega * min((K_B * T) / (HBAR * omega), 100.0)


def magnon_phonon_coupling_strength(A_ex, M_s, c_sound=5000.0):
    """
    Magnon-phonon coupling via the dispersion crossover method.

    Magnon dispersion (exchange-dominated): ω = ω_M λ_ex k²
    Phonon dispersion:                       ω = c_s k
    Crossover k: A_eff · k = c_s  →  k_cross = c_s / A_eff

    Parameters
    ----------
    c_sound : speed of sound in medium (m/s); default 5000 (quartz-like)

    Returns
    -------
    dict with crossover_k, crossover_freq_Hz, coupling_regime, etc.
    """
    lambda_ex = (2 * A_ex) / (MU_0 * M_s ** 2)
    omega_M   = GAMMA * MU_0 * M_s
    A_eff     = omega_M * lambda_ex   # effective spin stiffness (rad·m²/s)

    if A_eff <= 0:
        return {"crossover_k": 0, "crossover_freq_Hz": 0,
                "coupling_regime": "no coupling",
                "crossover_wavelength_m": np.inf,
                "A_eff_rad_m2_per_s": 0.0}

    k_cross   = c_sound / A_eff
    omega_cross = c_sound * k_cross
    f_cross   = omega_cross / (2 * np.pi)

    return {
        "crossover_k":             k_cross,
        "crossover_freq_Hz":       f_cross,
        "crossover_wavelength_m":  2 * np.pi / k_cross if k_cross > 0 else np.inf,
        "coupling_regime":         "hybridized" if k_cross < 1e10 else "weak",
        "A_eff_rad_m2_per_s":      A_eff,
    }


def eddy_current_damping(omega, conductivity, thickness):
    """
    Eddy current contribution to damping in conducting films.
    Dominant in metallic ferromagnets; negligible in insulators.

    Returns
    -------
    effective damping enhancement factor (dimensionless, added to α_Gilbert)
    """
    if conductivity <= 0 or omega <= 0:
        return 0.0
    skin  = np.sqrt(2.0 / (omega * MU_0 * conductivity))
    ratio = thickness / skin
    return ratio ** 2 / (1 + ratio ** 2)


# ─────────────────────────────────────────────────────────────────────────────
# COUPLING INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

def magnonic_coupling_state(
    H0=0.1,            # applied field (T)
    M_s=1.4e5,         # saturation magnetization (A/m) — YIG default
    A_ex=3.65e-12,     # exchange stiffness (J/m)
    alpha=3e-5,        # Gilbert damping
    T=300.0,           # temperature (K)
    theta_deg=90.0,    # propagation angle (degrees)
    conductivity=0.0,  # electrical conductivity (S/m); 0 for insulators
    thickness=1e-6,    # film thickness (m)
    c_sound=5000.0,    # speed of sound (m/s)
    n_e=0.0,           # electron density for plasma coupling (m⁻³)
):
    """
    Full magnonic state export for coupling to other layers.

    This is the interface contract — same dict-return pattern as other
    layer coupling_state() functions in this project.

    Returns a flat dict of state variables and derived quantities suitable
    for seeding the magnetic bridge encoder (magnonic mode) or for
    cross-layer physics validation via PhysicsGuard.
    """
    k_low  = 1e5    # 10 μm wavelength  (dipolar regime)
    k_mid  = 1e7    # 100 nm wavelength (exchange regime)
    k_high = 1e8    # 10 nm wavelength  (deep exchange)

    omega_bottom = float(dispersion_relation(0,      H0, M_s, A_ex, theta_deg))
    omega_low    = float(dispersion_relation(k_low,  H0, M_s, A_ex, theta_deg))
    omega_mid    = float(dispersion_relation(k_mid,  H0, M_s, A_ex, theta_deg))
    omega_high   = float(dispersion_relation(k_high, H0, M_s, A_ex, theta_deg))

    vg_low  = float(group_velocity(k_low,  H0, M_s, A_ex, theta_deg))
    vg_mid  = float(group_velocity(k_mid,  H0, M_s, A_ex, theta_deg))

    lp_low  = propagation_length(k_low,  H0, M_s, A_ex, alpha, theta_deg)
    lp_mid  = propagation_length(k_mid,  H0, M_s, A_ex, alpha, theta_deg)

    l_ex    = float(exchange_length(A_ex, M_s))

    n_therm_low = thermal_magnon_number(omega_low,  T)
    n_therm_mid = thermal_magnon_number(omega_mid,  T)

    mp_coupling = magnon_phonon_coupling_strength(A_ex, M_s, c_sound)
    alpha_eddy  = eddy_current_damping(omega_mid, conductivity, thickness)
    alpha_total = alpha + alpha_eddy
    mm_rate     = magnon_magnon_scattering_rate(omega_mid, T)
    c_magnon    = magnon_specific_heat_contribution(omega_mid, T)

    plasma_freq        = 0.0
    magnon_plasma_ratio = 0.0
    if n_e > 0:
        plasma_freq = (1 / (2 * np.pi)) * np.sqrt(
            (n_e * E_CHARGE ** 2) / (EPSILON_0 * M_E)
        )
        f_mid = omega_mid / (2 * np.pi)
        magnon_plasma_ratio = f_mid / plasma_freq if plasma_freq > 0 else 0.0

    E_magnon_density = n_therm_mid * HBAR * omega_mid

    if omega_bottom == 0:
        regime = "gapless"
    elif K_B * T > 10 * HBAR * omega_bottom:
        regime = "classical"
    elif K_B * T < 0.1 * HBAR * omega_bottom:
        regime = "quantum"
    else:
        regime = "crossover"

    return {
        # Frequencies (Hz)
        "magnon_band_bottom_Hz":       omega_bottom / (2 * np.pi),
        "magnon_freq_dipolar_Hz":      omega_low    / (2 * np.pi),
        "magnon_freq_exchange_Hz":     omega_mid    / (2 * np.pi),
        "magnon_freq_deep_exchange_Hz": omega_high  / (2 * np.pi),

        # Group velocities (m/s)
        "magnon_vg_dipolar_m_s":       vg_low,
        "magnon_vg_exchange_m_s":      vg_mid,

        # Propagation lengths (m)
        "magnon_prop_length_dipolar_m":  lp_low,
        "magnon_prop_length_exchange_m": lp_mid,
        "exchange_length_m":             l_ex,

        # Damping
        "alpha_gilbert":       alpha,
        "alpha_eddy_current":  alpha_eddy,
        "alpha_total":         alpha_total,
        "magnon_magnon_rate_Hz": mm_rate,

        # Thermal
        "thermal_occupation_dipolar":  n_therm_low,
        "thermal_occupation_exchange": n_therm_mid,
        "magnon_specific_heat_J_K":    c_magnon,
        "magnon_energy_density_J":     E_magnon_density,
        "thermal_regime":              regime,

        # Magnon-phonon coupling
        "magnon_phonon_crossover_Hz":        mp_coupling["crossover_freq_Hz"],
        "magnon_phonon_crossover_k":         mp_coupling["crossover_k"],
        "magnon_phonon_regime":              mp_coupling["coupling_regime"],
        "magnon_phonon_crossover_wavelength_m": mp_coupling["crossover_wavelength_m"],

        # Plasma coupling (Layer 0/1 interface)
        "plasma_frequency_Hz":      plasma_freq,
        "magnon_plasma_freq_ratio": magnon_plasma_ratio,
        "magnon_below_plasma":      (magnon_plasma_ratio < 1.0) if plasma_freq > 0 else None,

        # Material parameters (pass-through)
        "M_s_A_m":  M_s,
        "A_ex_J_m": A_ex,
        "H0_T":     H0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL PRESETS
# ─────────────────────────────────────────────────────────────────────────────

MATERIALS = {
    "YIG": {
        "M_s": 1.4e5, "A_ex": 3.65e-12, "alpha": 3e-5,
        "conductivity": 1e-10, "c_sound": 7209.0,
        "desc": "Yttrium Iron Garnet — ultra-low damping gold standard",
    },
    "Permalloy": {
        "M_s": 8.6e5, "A_ex": 1.3e-11, "alpha": 0.008,
        "conductivity": 1.6e6, "c_sound": 4900.0,
        "desc": "Ni80Fe20 — high M_s, moderate damping, metallic",
    },
    "CoFeB": {
        "M_s": 1.2e6, "A_ex": 1.5e-11, "alpha": 0.004,
        "conductivity": 6e5, "c_sound": 5200.0,
        "desc": "Spintronics workhorse — tunnel junction interfaces",
    },
    "Magnetite": {
        "M_s": 4.8e5, "A_ex": 1.2e-11, "alpha": 0.05,
        "conductivity": 2e4, "c_sound": 5500.0,
        "desc": "Fe3O4 — natural magnetic mineral, magnetotactic bacteria",
    },
    "Quartz_Fe_defect": {
        "M_s": 1e3, "A_ex": 1e-14, "alpha": 0.1,
        "conductivity": 1e-18, "c_sound": 5720.0,
        "desc": "SiO2 with iron defect centers — weak magnetic, strong piezo",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DEMO / SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

def _print_state(name, state):
    print(f"\n{'─' * 60}")
    print(f"  MAGNONIC STATE: {name}")
    print(f"{'─' * 60}")
    for key, val in state.items():
        if isinstance(val, float):
            print(f"  {key:45s} {val:+.6e}")
        elif isinstance(val, str):
            print(f"  {key:45s} {val}")
        elif val is None:
            print(f"  {key:45s} N/A")
        else:
            print(f"  {key:45s} {val}")


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNONIC SUB-LAYER — MATERIAL SURVEY")
    print("=" * 60)

    for mat_name, params in MATERIALS.items():
        state = magnonic_coupling_state(
            H0=0.1, M_s=params["M_s"], A_ex=params["A_ex"],
            alpha=params["alpha"], T=300.0, theta_deg=90.0,
            conductivity=params["conductivity"], thickness=100e-9,
            c_sound=params["c_sound"],
        )
        _print_state(f"{mat_name} — {params['desc']}", state)

    print("\n" + "=" * 60)
    print("MAGNETOSPHERIC PLASMA — SPIN WAVE REGIME")
    print("=" * 60)
    mag_state = magnonic_coupling_state(
        H0=5e-5, M_s=1e2, A_ex=1e-16, alpha=0.01,
        T=1e4, theta_deg=45.0, n_e=1e12,
    )
    _print_state("Magnetospheric plasma (Layer 1 interface)", mag_state)

    print("\n" + "=" * 60)
    print("QUARTZ/IRON DEFECT — MAGNON-PHONON COUPLING")
    print("=" * 60)
    qfe = MATERIALS["Quartz_Fe_defect"]
    qfe_state = magnonic_coupling_state(
        H0=0.01, M_s=qfe["M_s"], A_ex=qfe["A_ex"],
        alpha=qfe["alpha"], T=300.0, theta_deg=90.0,
        conductivity=qfe["conductivity"], c_sound=qfe["c_sound"],
    )
    _print_state("Quartz + Fe defects (magnon-phonon hybridization)", qfe_state)
    print(f"\n  MAGNON-PHONON CROSSOVER NOTE:")
    print(f"  At k_cross = {qfe_state['magnon_phonon_crossover_k']:.3e} rad/m,")
    print(f"  magnon and phonon dispersions intersect.")
    print(f"  Below this k: phonon-like. Above: magnon-like.")
    print(f"  In the hybridized zone: magnon-polaron states.")

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
