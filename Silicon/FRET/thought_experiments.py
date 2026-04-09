"""
thought_experiments.py – Executable simulations for the five speculative scenarios.
Uses the existing multi-physics modules.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# Import all the modules we've built
from fret_core import R0, k_FRET, E_FRET
from extended_range import NSETDonor, unified_efficiency
from gravity_fret import GravitationalFRET, GravitationalRedshift, GravitationalTimeDilation, TidalStrain
from plasma_fret import PlasmaFRET, PlasmaDielectric, DebyeScreening, CollisionalDecoherence
from acoustic_fret import AcousticModulator
from thermal_fret import ThermalSwitch, EntropicLinker
from polariton_fret import PolaritonRelay
from magneto_fret import MagnetoFRET
from entropy_fret import EntropicLinker as EntropyLinker

# ----------------------------------------------------------------------
# Experiment 1: Accretion Disk Beacon
# ----------------------------------------------------------------------
def accretion_disk_beacon(orbit_phase=None, output_file=None):
    """
    Simulate FRET efficiency for a probe orbiting a black hole.
    Combines gravitational effects, plasma screening, and NSET.
    """
    # Black hole parameters (10 solar masses)
    M_bh = 10 * 1.989e30  # kg
    # Orbital distance: 3 Schwarzschild radii
    Rs = 2 * 6.67e-11 * M_bh / (3e8)**2
    r_orbit = 3 * Rs

    # Gravitational potential at orbit (relative to infinity)
    Phi = -6.67e-11 * M_bh / r_orbit

    # Plasma parameters (inner accretion disk)
    n_e = 1e20  # m^-3
    T_plasma = 1e6  # K

    # FRET base parameters
    tau_D = 2.5  # ns
    R0 = 5.0  # nm
    lambda_D = 500  # nm
    r_nominal = 3.0  # nm

    # Setup modules
    redshift = GravitationalRedshift(lambda_D, Phi)
    dilation = GravitationalTimeDilation(Phi)
    tidal = TidalStrain(M_bh, r_orbit, r_nominal, stiffness=0.1)

    plasma_diel = PlasmaDielectric(n_e)
    debye = DebyeScreening(T_plasma, n_e)
    # NSET donor
    nset = NSETDonor(tau_D, Phi_D=0.6, kappa2=2/3, lambda_D=lambda_D, metal='Au')

    # Phase-dependent modulation: orbital eccentricity causes variation in r and plasma density
    if orbit_phase is None:
        phases = np.linspace(0, 2*np.pi, 100)
    else:
        phases = np.array([orbit_phase])

    eff_fret = []
    eff_nset = []
    for phase in phases:
        # Modulate distance: 3.0 ± 0.5 nm due to tidal stretching
        r_eff = r_nominal + 0.5 * np.sin(phase)
        # Modulate plasma density: higher at periapsis
        n_e_phase = n_e * (1 + 0.3 * np.cos(phase))

        # Gravitational FRET
        grav_fret = GravitationalFRET(tau_D, R0, redshift, dilation, tidal)
        E_g = grav_fret.efficiency(r_eff)

        # Plasma + NSET combined
        plasma_fret = PlasmaFRET(tau_D, R0, lambda_D, plasma_diel, debye, Phi_D0=0.6)
        E_p = plasma_fret.efficiency(r_eff)
        # NSET part
        k_nset = nset.k_NSET(r_eff)
        k_rad = 0.1
        k_nr = 0.05
        E_nset = k_nset / (k_nset + k_rad + k_nr)

        eff_fret.append(E_g)
        eff_nset.append(E_nset)

    if orbit_phase is None:
        plt.figure(figsize=(8,5))
        plt.plot(phases, eff_fret, label='FRET (gravitational)')
        plt.plot(phases, eff_nset, label='NSET (plasma-resistant)')
        plt.xlabel('Orbital Phase (rad)')
        plt.ylabel('Efficiency')
        plt.title('Accretion Disk Beacon Efficiency')
        plt.legend()
        plt.grid(True)
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()
    else:
        return {'phase': phases[0], 'E_fret': eff_fret[0], 'E_nset': eff_nset[0]}

# ----------------------------------------------------------------------
# Experiment 2: Plasma-Lensed FRET Communication
# ----------------------------------------------------------------------
def plasma_lens_communication(distance_ly=1.0, n_e_ism=1e5, output_file=None):
    """
    Model a self-focusing FRET beacon through the interstellar medium.
    Uses plasma dielectric to compute beam waist after distance L.
    """
    # FRET source parameters
    lambda_D = 500e-9  # m
    omega = 2 * np.pi * 3e8 / lambda_D
    # ISM plasma frequency
    omega_p = np.sqrt(n_e_ism * 1.6e-19**2 / (9.11e-31 * 8.85e-12))

    # Only possible if ω > ω_p
    if omega <= omega_p:
        raise ValueError("Frequency below plasma cutoff; no propagation.")

    # Refractive index and its gradient (simplified model)
    n_plasma = np.sqrt(1 - (omega_p/omega)**2)
    # Assume a transverse density gradient (lensing)
    dn_dx = 1e-10  # m^-1, arbitrary but plausible for ISM turbulence

    # Focal length of a GRIN lens of thickness d
    d = 1e11  # 0.1 AU plasma cloud thickness
    focal_length = 1 / (np.sqrt(n_plasma) * dn_dx * np.sin(d * np.sqrt(dn_dx/n_plasma)))

    # Distance to receiver in meters
    L = distance_ly * 9.46e15

    # Beam waist at receiver using ABCD matrix for GRIN lens + free space
    # Simplified: if focal length matches L, beam is collimated.
    w0 = 1e-3  # initial waist 1 mm
    # Divergence after lens
    if np.isfinite(focal_length):
        # Effective waist after lens
        w = w0 * np.sqrt(1 + (L / focal_length - 1)**2)
    else:
        w = w0 * L / (np.pi * w0**2 / lambda_D)  # diffraction limit

    # Collection efficiency scales as (aperture / w)^2
    aperture = 1.0  # meter
    efficiency = min(1.0, (aperture / w)**2)

    print(f"Plasma frequency: {omega_p:.2e} rad/s")
    print(f"Refractive index: {n_plasma:.4f}")
    print(f"GRIN focal length: {focal_length:.2e} m ({focal_length/9.46e15:.2f} ly)")
    print(f"Beam waist at {distance_ly} ly: {w:.2f} m")
    print(f"Geometric collection efficiency: {efficiency:.2e}")

    # Plot beam profile
    z = np.linspace(0, L, 1000)
    w_z = w0 * np.sqrt(1 + (z / focal_length - 1)**2) if np.isfinite(focal_length) else w0 * np.sqrt(1 + (z * lambda_D / (np.pi * w0**2))**2)
    plt.figure(figsize=(8,5))
    plt.plot(z / 9.46e15, w_z)
    plt.xlabel('Distance (light years)')
    plt.ylabel('Beam waist (m)')
    plt.title('Plasma-Lensed FRET Beam')
    plt.yscale('log')
    plt.grid(True)
    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()

    return {'distance_ly': distance_ly, 'beam_waist': w, 'efficiency': efficiency}

# ----------------------------------------------------------------------
# Experiment 3: GW-FRET Detector
# ----------------------------------------------------------------------
def gw_fret_detector(h_strain=1e-21, f_gw=100, L_bic=100e-6, output_file=None):
    """
    Simulate FRET efficiency modulation due to a gravitational wave.
    Uses BIC phase shift and magneto-FRET lock-in.
    """
    # BIC parameters
    lambda_BIC = 500e-9
    L = L_bic  # propagation length in BIC
    # GW parameters
    h = h_strain
    f = f_gw  # Hz
    omega_gw = 2 * np.pi * f

    # Time array over a few GW cycles
    t = np.linspace(0, 3/f, 500)

    # Phase modulation due to GW: delta_phi = h * (L / lambda_BIC) * sin(omega_gw t)
    delta_phi = h * (L / lambda_BIC) * np.sin(omega_gw * t)

    # BIC detuning effect on FRET (simplified)
    # Efficiency ~ 1 / (1 + (delta_phi/phi_0)^2) where phi_0 is linewidth
    phi_0 = 0.1  # radians, typical BIC linewidth
    E0 = 0.8  # base efficiency
    efficiency = E0 / (1 + (delta_phi / phi_0)**2)

    # Add magneto-FRET lock-in: assume we dither magnetic field at 1 kHz
    # and demodulate to extract GW signal. Here we just compute modulation depth.
    modulation_depth = (np.max(efficiency) - np.min(efficiency)) / E0

    print(f"GW strain: {h}")
    print(f"BIC length: {L*1e6:.1f} µm")
    print(f"Max phase shift: {h * L / lambda_BIC:.2e} rad")
    print(f"FRET modulation depth: {modulation_depth*100:.2e}%")

    plt.figure(figsize=(8,5))
    plt.plot(t*1000, efficiency)  # ms
    plt.xlabel('Time (ms)')
    plt.ylabel('FRET Efficiency')
    plt.title(f'GW-FRET Detector (h={h}, f={f} Hz)')
    plt.grid(True)
    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()

    return {'modulation_depth': modulation_depth, 'h': h, 'f_gw': f}

# ----------------------------------------------------------------------
# Experiment 4: Entropic Heat Engine FRET Cycle
# ----------------------------------------------------------------------
def entropic_heat_engine(T_cold=280, T_hot=320, acoustic_freq=10, output_file=None):
    """
    Simulate a FRET-based heat engine using a thermal switch and acoustic assist.
    """
    # Linker parameters
    Lc = 10.0  # nm contour
    Lp = 2.0   # nm persistence
    r_open = 5.0
    r_closed = 2.5
    Tm = 300   # K
    dH = 100   # kJ/mol
    R0 = 5.0

    # Create thermal switch
    switch = ThermalSwitch(r_open, r_closed, Tm, dH)
    # Entropic linker (for free energy landscape)
    linker = EntropyLinker(Lc, Lp, binding_sites=[(r_closed, -5, 0.5)])

    # Acoustic modulator to lower barrier
    acoustic = AcousticModulator(r0=3.0, amplitude=0.3, frequency=acoustic_freq, R0=R0)

    # Temperature cycle
    t_cycle = np.linspace(0, 1, 100)
    T = T_cold + (T_hot - T_cold) * (1 + np.sin(2*np.pi*t_cycle)) / 2

    # Efficiency along cycle
    E = []
    for Ti in T:
        r_mean = switch.mean_distance(Ti)
        # Acoustic enhancement factor (simplified)
        acoustic.r0 = r_mean
        gain = acoustic.enhancement_factor()
        E_static = E_FRET(r_mean, R0)
        E.append(E_static * gain)

    # Compute work: area of hysteresis loop
    # Here we just compute power as average efficiency * delta_T
    avg_E = np.mean(E)
    power = avg_E * (T_hot - T_cold) / T_hot  # normalized

    print(f"Temperature cycle: {T_cold} K → {T_hot} K")
    print(f"Average FRET efficiency: {avg_E:.3f}")
    print(f"Normalized power output: {power:.3f}")

    plt.figure(figsize=(8,5))
    plt.plot(T, E)
    plt.xlabel('Temperature (K)')
    plt.ylabel('FRET Efficiency')
    plt.title('Entropic Heat Engine Cycle')
    plt.grid(True)
    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()

    return {'avg_efficiency': avg_E, 'power': power}

# ----------------------------------------------------------------------
# Experiment 5: Polariton Black Hole Analog
# ----------------------------------------------------------------------
def polariton_black_hole(v_flow=0.8, c_sound=1.0, output_file=None):
    """
    Simulate Hawking-like spontaneous FRET from a sonic horizon in a polariton condensate.
    """
    # Polariton relay parameters
    Omega_R = 10  # meV
    gamma_D = 0.1
    gamma_cav = 0.2
    v_g = 1.0  # μm/ps
    tau_LP = 100  # ps
    eta_abs = 0.5

    relay = PolaritonRelay(Omega_R, gamma_D, gamma_cav, v_g, tau_LP, eta_abs)

    # Create spatial grid with flow velocity gradient
    x = np.linspace(-50, 50, 200)  # μm
    # Sonic horizon at x=0 where v_flow = c_sound
    v = v_flow * (1 + np.tanh(x / 10)) / 2
    c = c_sound * np.ones_like(x)

    # Hawking temperature (analog) proportional to velocity gradient at horizon
    dv_dx = np.gradient(v, x)
    T_H = (1 / (2*np.pi)) * dv_dx[np.argmin(np.abs(v - c_sound))]

    # Spontaneous FRET signal outside horizon (x>0)
    # Model as thermal distribution with temperature T_H
    # Efficiency ~ Bose-Einstein factor
    omega = 1.0  # arbitrary frequency
    occupation = 1 / (np.exp(omega / T_H) - 1) if T_H > 0 else 0
    E_spontaneous = occupation * relay.total_efficiency(10)  # at some distance

    print(f"Flow velocity range: {v.min():.2f} to {v.max():.2f} μm/ps")
    print(f"Hawking temperature: {T_H:.3f} (arb. units)")
    print(f"Spontaneous FRET efficiency: {E_spontaneous:.2e}")

    # Plot velocity profile
    plt.figure(figsize=(8,5))
    plt.plot(x, v, label='Flow velocity')
    plt.axhline(c_sound, color='r', linestyle='--', label='Sound speed')
    plt.axvline(0, color='k', alpha=0.3, label='Horizon')
    plt.xlabel('Position (μm)')
    plt.ylabel('Velocity (μm/ps)')
    plt.title('Polariton Black Hole Analog')
    plt.legend()
    plt.grid(True)
    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()

    return {'T_H': T_H, 'E_spontaneous': E_spontaneous}
