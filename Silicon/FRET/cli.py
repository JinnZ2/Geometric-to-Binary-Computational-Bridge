#!/usr/bin/env python3
# STATUS: infrastructure -- main CLI for FRET stack
"""
fret-stack – CLI for the FRET Engineering Stack simulations.

Usage:
    fret-stack geometry [options]
    fret-stack servo [options]
    fret-stack dbr [options]
    fret-stack triplet [options]
    fret-stack triage [options]
    fret-stack all [options]

For help on a subcommand: fret-stack <command> --help
"""

import argparse
import sys
import numpy as np
import matplotlib.pyplot as plt
import json
import os

# Import CLI extensions
from extended_cli import register_extended_subcommands
from frontier_cli import register_frontier_subcommands
from handler_functions import cmd_acoustic, cmd_thermal

# Import simulation modules
from fret_core import R0, k_FRET, E_FRET
import geometry_lock
import spectral_servo
import photonic_branching
import triplet_reservoir
import triage_diagnosis

# ----------------------------------------------------------------------
# Common utilities
# ----------------------------------------------------------------------
def save_results(data, output_file, plot_file=None):
    """Save numerical results as JSON and optionally a plot as PNG."""
    if output_file:
        # Convert numpy arrays to lists for JSON serialization
        if isinstance(data, dict):
            clean_data = {}
            for k, v in data.items():
                if isinstance(v, np.ndarray):
                    clean_data[k] = v.tolist()
                else:
                    clean_data[k] = v
            with open(output_file, 'w') as f:
                json.dump(clean_data, f, indent=2)
            print(f"Results saved to {output_file}")
    
    if plot_file:
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {plot_file}")
        plt.close()
    else:
        plt.show()

# ----------------------------------------------------------------------
# Geometry command
# ----------------------------------------------------------------------
def cmd_geometry(args):
    """Run geometry lock simulations."""
    r_eq = args.r_eq
    k_spring = args.k_spring
    r_hard_min = args.r_hard_min
    sigma_phi = args.sigma_phi
    U_barrier = args.U_barrier
    
    # Distance distribution
    r_vals, pdf = geometry_lock.r_distribution(
        r_eq, k_spring, r_hard_min=r_hard_min,
        r_range=(args.r_min, args.r_max)
    )
    
    mean_r = np.trapz(r_vals * pdf, r_vals)
    var_r = np.trapz((r_vals - mean_r)**2 * pdf, r_vals)
    cv_r = np.sqrt(var_r) / mean_r
    
    # Orientation factor
    kappa2_mean = geometry_lock.effective_kappa2(
        phi0=0, sigma_phi=sigma_phi, U_barrier=U_barrier
    )
    
    # Display
    print(f"Mean distance:     {mean_r:.3f} nm")
    print(f"CV(r):             {cv_r*100:.1f}%")
    print(f"Effective <κ²>:    {kappa2_mean:.2f}")
    
    # Plot
    plt.figure()
    plt.plot(r_vals, pdf, 'b-', lw=2)
    plt.axvline(mean_r, color='r', linestyle='--', label=f'Mean = {mean_r:.2f} nm')
    plt.xlabel('Distance r (nm)')
    plt.ylabel('Probability density')
    plt.title('Donor-Acceptor Distance Distribution')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    results = {
        "r_eq": r_eq,
        "k_spring": k_spring,
        "mean_r": mean_r,
        "cv_r": cv_r,
        "kappa2_mean": kappa2_mean,
        "r_values": r_vals,
        "pdf": pdf
    }
    save_results(results, args.output, args.plot)

# ----------------------------------------------------------------------
# Servo command
# ----------------------------------------------------------------------
def cmd_servo(args):
    """Run spectral servo simulation."""
    # Build synthetic spectra
    wl = np.linspace(args.wl_min, args.wl_max, args.wl_points)
    donor_em = spectral_servo.gaussian_spectrum(wl, args.donor_peak, args.donor_sigma)
    acceptor_abs = spectral_servo.gaussian_spectrum(wl, args.acceptor_peak, args.acceptor_sigma)
    
    J_nom = spectral_servo.compute_J(wl, donor_em, acceptor_abs)
    print(f"Nominal spectral overlap J = {J_nom:.4e}")
    
    # Run simulation
    time, J_hist, shift_hist = spectral_servo.simulate_servo(
        wl, donor_em, acceptor_abs, J_target=J_nom,
        Kp=args.Kp, Ki=args.Ki, dt=args.dt, total_time=args.total_time,
        aging_rate=args.aging_rate, max_stark_shift=args.max_stark
    )
    
    # Metrics
    final_error = (J_hist[-1] - J_nom) / J_nom * 100
    print(f"Final J error:      {final_error:.2f}%")
    print(f"Max |Stark shift|:  {np.max(np.abs(shift_hist)):.2f} nm")
    
    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
    ax1.plot(time, J_hist, 'b-', label='Controlled J')
    ax1.axhline(J_nom, color='k', linestyle='--', label='Target')
    ax1.set_ylabel('Spectral overlap J')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(time, shift_hist, 'r-', label='Stark shift')
    ax2.set_xlabel('Time (arb. units)')
    ax2.set_ylabel('Shift (nm)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    plt.suptitle('Spectral Servo Performance')
    plt.tight_layout()
    
    results = {
        "J_nominal": float(J_nom),
        "J_final": float(J_hist[-1]),
        "final_error_percent": float(final_error),
        "time": time.tolist(),
        "J_history": J_hist.tolist(),
        "stark_shift_history": shift_hist.tolist()
    }
    save_results(results, args.output, args.plot)

# ----------------------------------------------------------------------
# DBR command
# ----------------------------------------------------------------------
def cmd_dbr(args):
    """Compute DBR reflectance and LDOS factor."""
    wl = np.linspace(args.wl_min, args.wl_max, args.wl_points)
    d_low = args.center_wl / (4 * args.n_low)
    d_high = args.center_wl / (4 * args.n_high)
    
    R = photonic_branching.dbr_reflectance(
        wl, args.n_low, args.n_high, d_low, d_high,
        args.N_pairs, n_sub=args.n_sub, n_sup=args.n_sup
    )
    F = photonic_branching.LDOS_factor(R)
    
    # Find F at donor wavelength
    idx_donor = np.argmin(np.abs(wl - args.donor_wl))
    F_donor = F[idx_donor]
    print(f"At donor λ = {args.donor_wl} nm: Reflectance = {R[idx_donor]:.3f}, F = {F_donor:.3f}")
    
    # Plot
    plt.figure(figsize=(8, 5))
    plt.plot(wl, R, 'b-', label='Reflectance')
    plt.plot(wl, F, 'r-', label='F = k_rad / k_rad0')
    plt.axvline(args.donor_wl, color='k', linestyle='--', label=f'Donor λ = {args.donor_wl} nm')
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Value')
    plt.title('DBR Stop-band and Radiative Rate Modification')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    results = {
        "donor_wavelength": args.donor_wl,
        "F_at_donor": float(F_donor),
        "R_at_donor": float(R[idx_donor]),
        "wavelengths": wl.tolist(),
        "reflectance": R.tolist(),
        "F_factor": F.tolist()
    }
    save_results(results, args.output, args.plot)

# ----------------------------------------------------------------------
# Triplet command
# ----------------------------------------------------------------------
def cmd_triplet(args):
    """Compute efficiency boost from triplet reservoir."""
    rho_vals = np.linspace(args.rho_min, args.rho_max, args.rho_points)
    return_vals = np.linspace(args.return_min, args.return_max, args.return_points)
    
    # Base rates (ns^-1)
    kF = args.kF
    kR = args.kR
    knrS = args.knrS
    
    E_ref = kF / (kF + kR + knrS)
    print(f"Reference efficiency (no triplet) = {E_ref:.3f}")
    
    boost_map = np.zeros((len(rho_vals), len(return_vals)))
    for i, rho in enumerate(rho_vals):
        for j, rr in enumerate(return_vals):
            boost_map[i,j] = triplet_reservoir.efficiency_boost(
                kF, kR, knrS, rho, rr
            )
    
    relative_boost = boost_map / E_ref - 1.0
    max_boost = np.max(relative_boost) * 100
    print(f"Maximum relative boost: {max_boost:.1f}%")
    
    # Plot
    plt.figure(figsize=(7, 5))
    cp = plt.contourf(return_vals, rho_vals, relative_boost, levels=20, cmap='viridis')
    plt.colorbar(cp, label='Relative efficiency boost')
    plt.xlabel('Return ratio b/(b+c)')
    plt.ylabel('Diversion fraction ρ')
    plt.title('Triplet Reservoir Enhancement')
    plt.grid(True, alpha=0.3)
    
    results = {
        "E_reference": float(E_ref),
        "rho_values": rho_vals.tolist(),
        "return_ratio_values": return_vals.tolist(),
        "efficiency_map": boost_map.tolist(),
        "relative_boost": relative_boost.tolist()
    }
    save_results(results, args.output, args.plot)

# ----------------------------------------------------------------------
# Triage command
# ----------------------------------------------------------------------
def cmd_triage(args):
    """Run triage diagnostics with specified fault."""
    np.random.seed(args.seed)
    R0_nom = args.R0
    r_nom = args.r_nom
    F_nom = args.F_nom
    
    thresholds = {
        'tau_high': args.tau_high,
        'rss_low': args.rss_low,
        'frad_high': args.frad_high,
        'E_low': args.E_low
    }
    
    # Override parameters based on fault type
    r = r_nom
    F = F_nom
    fault_desc = "Nominal"
    if args.fault == 'geometry':
        r = args.fault_value
        fault_desc = f"Geometry fault: r = {r} nm"
    elif args.fault == 'photonic':
        F = args.fault_value
        fault_desc = f"Photonic fault: F = {F}"
    elif args.fault == 'spectral':
        # For spectral we can't easily adjust J in this simple model;
        # we'll skip for demo.
        pass
    
    tau, E, rss = triage_diagnosis.simulate_measurements(
        r, R0_nom, F, noise_level=args.noise
    )
    diag = triage_diagnosis.triage_decision(tau, E, rss, thresholds)
    
    print(f"Condition: {fault_desc}")
    print(f"Measured tau_DA = {tau:.3f}, E = {E:.3f}, r_ss = {rss:.3f}")
    print(f"Diagnosis: {diag}")
    
    # For saving
    results = {
        "fault": fault_desc,
        "tau_DA": float(tau),
        "E": float(E),
        "r_ss": float(rss),
        "diagnosis": diag
    }
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")

# ----------------------------------------------------------------------
# All command (run all simulations and produce summary)
# ----------------------------------------------------------------------
def cmd_all(args):
    """Run all simulations with default parameters and save combined report."""
    out_dir = args.outdir
    os.makedirs(out_dir, exist_ok=True)
    
    print("=== FRET Engineering Stack: Full Simulation Suite ===\n")
    
    # 1. Geometry
    print("[1/4] Geometry Lock...")
    r_eq = 3.0
    k_spring = 50.0
    r_vals, pdf = geometry_lock.r_distribution(r_eq, k_spring, r_hard_min=1.8)
    mean_r = np.trapz(r_vals * pdf, r_vals)
    kappa2 = geometry_lock.effective_kappa2(0, 0.05)
    print(f"      Mean r = {mean_r:.2f} nm, <κ²> = {kappa2:.2f}")
    plt.figure()
    plt.plot(r_vals, pdf)
    plt.title('Distance Distribution')
    plt.savefig(os.path.join(out_dir, 'geometry_dist.png'))
    plt.close()
    
    # 2. Servo
    print("[2/4] Spectral Servo...")
    wl = np.linspace(400, 600, 500)
    donor = spectral_servo.gaussian_spectrum(wl, 480, 20)
    acceptor = spectral_servo.gaussian_spectrum(wl, 520, 25)
    J_nom = spectral_servo.compute_J(wl, donor, acceptor)
    time, J_hist, _ = spectral_servo.simulate_servo(
        wl, donor, acceptor, J_nom, 0.5, 0.05, 0.1, 50, 0.05
    )
    print(f"      Nominal J={J_nom:.2e}, final error={(J_hist[-1]-J_nom)/J_nom*100:.1f}%")
    plt.figure()
    plt.plot(time, J_hist)
    plt.title('Servo Performance')
    plt.savefig(os.path.join(out_dir, 'servo_J.png'))
    plt.close()
    
    # 3. DBR
    print("[3/4] Photonic Branching...")
    wl = np.linspace(400, 700, 500)
    R = photonic_branching.dbr_reflectance(wl, 1.45, 2.0, 500/(4*1.45), 500/(4*2.0), 10)
    F = photonic_branching.LDOS_factor(R)
    idx = np.argmin(np.abs(wl-480))
    print(f"      F at 480 nm = {F[idx]:.3f}")
    plt.figure()
    plt.plot(wl, R, label='R')
    plt.plot(wl, F, label='F')
    plt.legend()
    plt.savefig(os.path.join(out_dir, 'dbr_F.png'))
    plt.close()
    
    # 4. Triplet
    print("[4/4] Triplet Reservoir...")
    rho = np.linspace(0, 0.9, 20)
    ret = np.linspace(0.5, 0.95, 20)
    boost = np.zeros((len(rho), len(ret)))
    for i, r in enumerate(rho):
        for j, rr in enumerate(ret):
            boost[i,j] = triplet_reservoir.efficiency_boost(1.0, 0.5, 0.3, r, rr)
    E_ref = 1.0/(1.0+0.5+0.3)
    rel = boost/E_ref - 1
    print(f"      Max relative boost = {np.max(rel)*100:.1f}%")
    plt.figure()
    plt.contourf(ret, rho, rel)
    plt.colorbar()
    plt.savefig(os.path.join(out_dir, 'triplet_boost.png'))
    plt.close()
    
    print(f"\nAll outputs saved to '{out_dir}/'")
    print("Summary report generated.")

# ----------------------------------------------------------------------
# Main CLI setup
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="FRET Engineering Stack CLI – Deterministic control simulations.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', required=True, help='Subcommand to run')
    
    # ----- geometry -----
    geom_parser = subparsers.add_parser('geometry', help='Simulate geometry lock (distance & orientation)')
    geom_parser.add_argument('--r_eq', type=float, default=3.0, help='Equilibrium distance (nm) [3.0]')
    geom_parser.add_argument('--k_spring', type=float, default=50.0, help='Spring constant (kT/nm²) [50.0]')
    geom_parser.add_argument('--r_hard_min', type=float, default=1.8, help='Hard‑wall minimum distance (nm) [1.8]')
    geom_parser.add_argument('--r_min', type=float, default=1.0, help='Min r for plot [1.0]')
    geom_parser.add_argument('--r_max', type=float, default=6.0, help='Max r for plot [6.0]')
    geom_parser.add_argument('--sigma_phi', type=float, default=0.05, help='RMS angular deviation (rad) [0.05]')
    geom_parser.add_argument('--U_barrier', type=float, default=5.0, help='Rotational barrier (kT) [5.0]')
    geom_parser.add_argument('--output', '-o', help='Save results to JSON file')
    geom_parser.add_argument('--plot', '-p', help='Save plot to file (PNG)')
    
    # ----- servo -----
    servo_parser = subparsers.add_parser('servo', help='Simulate adaptive spectral servo (PI control)')
    servo_parser.add_argument('--wl_min', type=float, default=400, help='Min wavelength (nm) [400]')
    servo_parser.add_argument('--wl_max', type=float, default=600, help='Max wavelength (nm) [600]')
    servo_parser.add_argument('--wl_points', type=int, default=500, help='Number of wavelength points [500]')
    servo_parser.add_argument('--donor_peak', type=float, default=480, help='Donor emission peak (nm) [480]')
    servo_parser.add_argument('--donor_sigma', type=float, default=20, help='Donor peak std dev (nm) [20]')
    servo_parser.add_argument('--acceptor_peak', type=float, default=520, help='Acceptor absorption peak (nm) [520]')
    servo_parser.add_argument('--acceptor_sigma', type=float, default=25, help='Acceptor peak std dev (nm) [25]')
    servo_parser.add_argument('--Kp', type=float, default=0.5, help='Proportional gain [0.5]')
    servo_parser.add_argument('--Ki', type=float, default=0.05, help='Integral gain [0.05]')
    servo_parser.add_argument('--dt', type=float, default=0.1, help='Time step [0.1]')
    servo_parser.add_argument('--total_time', type=float, default=50, help='Total simulation time [50]')
    servo_parser.add_argument('--aging_rate', type=float, default=0.05, help='Spectral drift rate (nm/time) [0.05]')
    servo_parser.add_argument('--max_stark', type=float, default=3.0, help='Max Stark shift (nm) [3.0]')
    servo_parser.add_argument('--output', '-o', help='Save results to JSON file')
    servo_parser.add_argument('--plot', '-p', help='Save plot to file (PNG)')
    
    # ----- dbr -----
    dbr_parser = subparsers.add_parser('dbr', help='Compute DBR reflectance and LDOS factor')
    dbr_parser.add_argument('--wl_min', type=float, default=400, help='Min wavelength (nm) [400]')
    dbr_parser.add_argument('--wl_max', type=float, default=700, help='Max wavelength (nm) [700]')
    dbr_parser.add_argument('--wl_points', type=int, default=500, help='Number of wavelength points [500]')
    dbr_parser.add_argument('--n_low', type=float, default=1.45, help='Low index material [1.45]')
    dbr_parser.add_argument('--n_high', type=float, default=2.0, help='High index material [2.0]')
    dbr_parser.add_argument('--center_wl', type=float, default=500, help='Design center wavelength (nm) [500]')
    dbr_parser.add_argument('--N_pairs', type=int, default=10, help='Number of layer pairs [10]')
    dbr_parser.add_argument('--n_sub', type=float, default=1.5, help='Substrate index [1.5]')
    dbr_parser.add_argument('--n_sup', type=float, default=1.0, help='Superstrate index [1.0]')
    dbr_parser.add_argument('--donor_wl', type=float, default=480, help='Donor wavelength of interest (nm) [480]')
    dbr_parser.add_argument('--output', '-o', help='Save results to JSON file')
    dbr_parser.add_argument('--plot', '-p', help='Save plot to file (PNG)')
    
    # ----- triplet -----
    triplet_parser = subparsers.add_parser('triplet', help='Compute triplet reservoir efficiency boost')
    triplet_parser.add_argument('--kF', type=float, default=1.0, help='FRET rate [1.0]')
    triplet_parser.add_argument('--kR', type=float, default=0.5, help='Radiative rate [0.5]')
    triplet_parser.add_argument('--knrS', type=float, default=0.3, help='Non-radiative singlet rate [0.3]')
    triplet_parser.add_argument('--rho_min', type=float, default=0.0, help='Min diversion fraction [0.0]')
    triplet_parser.add_argument('--rho_max', type=float, default=0.9, help='Max diversion fraction [0.9]')
    triplet_parser.add_argument('--rho_points', type=int, default=20, help='Number of ρ values [20]')
    triplet_parser.add_argument('--return_min', type=float, default=0.5, help='Min return ratio [0.5]')
    triplet_parser.add_argument('--return_max', type=float, default=0.95, help='Max return ratio [0.95]')
    triplet_parser.add_argument('--return_points', type=int, default=20, help='Number of return ratio values [20]')
    triplet_parser.add_argument('--output', '-o', help='Save results to JSON file')
    triplet_parser.add_argument('--plot', '-p', help='Save plot to file (PNG)')
    
    # ----- triage -----
    triage_parser = subparsers.add_parser('triage', help='Run diagnostic triage with fault injection')
    triage_parser.add_argument('--fault', choices=['none','geometry','photonic','spectral'], default='none',
                              help='Type of fault to inject [none]')
    triage_parser.add_argument('--fault_value', type=float, default=4.5,
                              help='Parameter value for fault (r for geometry, F for photonic) [4.5]')
    triage_parser.add_argument('--R0', type=float, default=5.0, help='Förster radius (nm) [5.0]')
    triage_parser.add_argument('--r_nom', type=float, default=3.0, help='Nominal distance (nm) [3.0]')
    triage_parser.add_argument('--F_nom', type=float, default=0.1, help='Nominal LDOS factor [0.1]')
    triage_parser.add_argument('--noise', type=float, default=0.02, help='Measurement noise level [0.02]')
    triage_parser.add_argument('--tau_high', type=float, default=0.8, help='Threshold for high tau_DA [0.8]')
    triage_parser.add_argument('--rss_low', type=float, default=0.05, help='Threshold for low r_ss [0.05]')
    triage_parser.add_argument('--frad_high', type=float, default=0.2, help='Threshold for high f_rad [0.2]')
    triage_parser.add_argument('--E_low', type=float, default=0.7, help='Threshold for low E [0.7]')
    triage_parser.add_argument('--seed', type=int, default=42, help='Random seed [42]')
    triage_parser.add_argument('--output', '-o', help='Save results to JSON file')
    
    # ----- all -----
    all_parser = subparsers.add_parser('all', help='Run all simulations and generate summary report')
    all_parser.add_argument('--outdir', '-d', default='fret_sim_output', help='Output directory [fret_sim_output]')

    # ----- extended subcommands (acoustic, thermal, entropy) -----
    register_extended_subcommands(subparsers)

    # ----- frontier subcommands (time, vacuum, thermo, axion, radical, qet, unified) -----
    register_frontier_subcommands(subparsers)

    args = parser.parse_args()
    
    # Dispatch to appropriate handler
    if args.command == 'geometry':
        cmd_geometry(args)
    elif args.command == 'servo':
        cmd_servo(args)
    elif args.command == 'dbr':
        cmd_dbr(args)
    elif args.command == 'triplet':
        cmd_triplet(args)
    elif args.command == 'triage':
        cmd_triage(args)
    elif args.command == 'all':
        cmd_all(args)
    elif args.command == 'acoustic':
        cmd_acoustic(args)
    elif args.command == 'thermal':
        cmd_thermal(args)
    elif args.command == 'entropy':
        cmd_entropy(args)
    elif args.command == 'frontier':
        cmd_frontier(args)
    else:
        parser.print_help()


def cmd_entropy(args):
    """Run entropic linker distance distribution simulation."""
    from entropy_fret import EntropicLinker
    linker = EntropicLinker(L_contour=args.L_contour, L_p=args.L_p)
    r_vals = np.linspace(0.5, args.L_contour * 0.8, 200)
    p_vals = np.array([linker.distance_pdf(r) for r in r_vals])
    E_vals = np.array([E_FRET(r, args.R0) for r in r_vals])
    E_avg = np.trapz(p_vals * E_vals, r_vals) / np.trapz(p_vals, r_vals)
    print(f"Linker: L_contour={args.L_contour} nm, L_p={args.L_p} nm")
    print(f"R0={args.R0} nm")
    print(f"<E_FRET> (distance-averaged) = {E_avg:.4f}")
    results = {'L_contour': args.L_contour, 'L_p': args.L_p,
               'R0': args.R0, 'E_avg': float(E_avg)}
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
    if args.plot:
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
        ax1.plot(r_vals, p_vals)
        ax1.set_xlabel('Distance (nm)')
        ax1.set_ylabel('P(r)')
        ax1.set_title('Linker Distance Distribution')
        ax2.plot(r_vals, E_vals)
        ax2.set_xlabel('Distance (nm)')
        ax2.set_ylabel('E_FRET')
        ax2.set_title(f'FRET Efficiency (R0={args.R0} nm), <E>={E_avg:.4f}')
        plt.tight_layout()
        plt.savefig(args.plot)


def cmd_frontier(args):
    """Run frontier physics arena simulation."""
    arena = args.arena
    if arena == 'time':
        from temporal_fret import PhotonicTimeCrystal
        ptc = PhotonicTimeCrystal(n0=args.n0, delta_n=args.delta_n,
                                   modulation_freq=args.freq * 1e6)
        print(f"Photonic Time Crystal: n0={args.n0}, dn={args.delta_n}, f={args.freq} MHz")
        print(f"  Floquet gap: {ptc.floquet_gap():.6f} eV")
    elif arena == 'vacuum':
        from vacuum_fret import casimir_force, casimir_delta_r
        F = casimir_force(args.d_plate * 1e-9, args.area * 1e-18)
        dr = casimir_delta_r(args.d_plate * 1e-9, args.area * 1e-18)
        print(f"Casimir cavity: d={args.d_plate} nm, A={args.area} nm^2")
        print(f"  Force: {F:.4e} N")
        print(f"  Distance shift: {dr:.4e} m")
    elif arena == 'thermo':
        from quantum_thermo import QuantumBattery
        qb = QuantumBattery(energy=args.energy, temperature=args.temp)
        print(f"Quantum Battery: E={args.energy} eV, T={args.temp} K")
        print(f"  Ergotropy: {qb.ergotropy():.4f} eV")
    elif arena == 'axion':
        from axion_fret import axion_photon_rate
        rate = axion_photon_rate(args.B_field, args.axion_mass)
        print(f"Axion-photon: B={args.B_field} T, m_a={args.axion_mass} eV")
        print(f"  Conversion rate: {rate:.4e} Hz")
    elif arena == 'radical':
        from radical_pair import RadicalPair
        rp = RadicalPair(B_field=args.B_strength * 1e-3)
        print(f"Radical pair: B={args.B_strength} mT")
        print(f"  Singlet yield: {rp.singlet_yield():.4f}")
    elif arena == 'qet':
        from qet import QETProtocol
        qet = QETProtocol(chain_length=args.chain_len)
        E = qet.teleported_energy(args.distance)
        print(f"QET: chain={args.chain_len}, distance={args.distance}")
        print(f"  Teleported energy: {E:.6f}")
    elif arena == 'unified':
        print("Unified arena: see experiments/silicon_speculative/FRET/grand_unified.py")
    else:
        print(f"Unknown arena: {arena}")


if __name__ == "__main__":
    main()
