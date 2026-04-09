# STATUS: infrastructure -- unified CLI for Silicon lattice simulations
"""
Silicon Lattice Simulation CLI
==============================
Entry point for all multi-node simulations:
  vff-single   Run single-octahedron Keating potential, find 8 minima
  vff-not      Coupled octahedra NOT gate simulation
  vff-toffoli  Phi-triangle Toffoli gate (3 nodes, 64-entry truth table)
  multi-bridge Multi-bridge octahedral node (strain+spin+optical+electric)
  lattice      2D neural lattice with coupled bridges and energy minimization
  validation   SPM/PL/ODMR experimental validation simulator

Usage:
  python -m Silicon.lattice.cli vff-single
  python -m Silicon.lattice.cli vff-not --k_coupling 2.0
  python -m Silicon.lattice.cli vff-toffoli --k0 2.0
  python -m Silicon.lattice.cli multi-bridge --B_field 0.5
  python -m Silicon.lattice.cli lattice --nx 4 --ny 4 --steps 100
  python -m Silicon.lattice.cli validation --noise 0.01
"""

import argparse
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def cmd_vff_single(args):
    """Run single-octahedron Keating potential simulation."""
    from Silicon.lattice.vff_keating import SiliconOctahedron
    cluster = SiliconOctahedron(d0=args.d0, alpha=args.alpha, beta=args.beta)
    print(f"[VFF] Single octahedron: d0={args.d0} A, alpha={args.alpha}, beta={args.beta}")
    minima = cluster.find_minima(n_starting_points=args.n_starts, temp=args.temp)
    print(f"Found {len(minima)} minima:")
    for i, m in enumerate(minima):
        e = cluster.keating_energy(m)
        print(f"  State {i+1}: [{m[0]:+.4f}, {m[1]:+.4f}, {m[2]:+.4f}]  E={e:.4f} eV")
    if len(minima) == 8:
        print("PASS: 8 distinct minima (octahedral states confirmed)")
    else:
        print(f"NOTE: Expected 8, found {len(minima)}. Adjust --n_starts or --temp.")


def cmd_vff_not(args):
    """Run coupled-octahedra NOT gate simulation."""
    from Silicon.lattice.vff_keating import SiliconOctahedron
    from Silicon.lattice.vff_coupled_not import CoupledOctahedra, FACE_NORMALS, classify_state
    import numpy as np
    system = CoupledOctahedra(k_coupling=args.k_coupling)
    print(f"[VFF] Coupled NOT gate: k_c={args.k_coupling} eV/A^2")
    input_disp = FACE_NORMALS[0] * 0.38
    output_disp, energy = system.energy_given_input(input_disp)
    in_state = classify_state(input_disp)
    out_state = classify_state(output_disp)
    print(f"  Input:  Face{in_state+1} [{input_disp[0]:+.3f}, {input_disp[1]:+.3f}, {input_disp[2]:+.3f}]")
    print(f"  Output: Face{out_state+1} [{output_disp[0]:+.3f}, {output_disp[1]:+.3f}, {output_disp[2]:+.3f}]")
    dot = np.dot(FACE_NORMALS[in_state], FACE_NORMALS[out_state])
    if dot < -0.9:
        print("  PASS: Inversion confirmed (NOT gate)")
    else:
        print(f"  Dot product: {dot:.3f} (need < -0.9 for inversion)")


def cmd_vff_toffoli(args):
    """Run phi-triangle Toffoli gate simulation."""
    from Silicon.lattice.vff_toffoli import PhiTriangleToffoli
    toffoli = PhiTriangleToffoli(k0=args.k0)
    phi = toffoli.phi
    print(f"[VFF] Phi-Triangle Toffoli: k0={args.k0} eV/A^2")
    print(f"  k_AB = phi^-2 * k0 = {toffoli.k_AB:.3f}")
    print(f"  k_BC = phi^0  * k0 = {toffoli.k_BC:.3f}")
    print(f"  k_AC = phi^1  * k0 = {toffoli.k_AC:.3f}")
    toffoli.compute_truth_table()


def cmd_multi_bridge(args):
    """Run multi-bridge octahedral node simulation."""
    from Silicon.lattice.multi_bridge_node import OctahedralNode
    import numpy as np
    node = OctahedralNode()
    B_vec = np.array([0.0, 0.0, args.B_field])
    node.apply_strain(args.strain / 100.0)
    node.apply_magnetic_field(B_vec)
    state = node.read_state()
    print(f"[Multi-Bridge] Node state at strain={args.strain}%, B_z={args.B_field} T:")
    print(f"  State: {state}")


def cmd_lattice(args):
    """Run 2D neural lattice simulation."""
    from Silicon.lattice.multi_bridge_neural_lattice import BridgeLattice
    lattice = BridgeLattice(nx=args.nx, ny=args.ny)
    print(f"[Lattice] {args.nx}x{args.ny} lattice, {args.steps} relaxation steps")
    lattice.relax(n_steps=args.steps)
    print(f"  Final energy: {lattice.total_energy():.4f} eV")


def cmd_validation(args):
    """Run experimental validation simulator."""
    from Silicon.lattice.experimental_validation_sim import run_validation
    print(f"[Validation] SPM/PL/ODMR simulator, noise={args.noise}")
    run_validation(noise_level=args.noise)


def main():
    parser = argparse.ArgumentParser(
        description="Silicon Lattice Simulation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Simulation to run')

    # vff-single
    p = subparsers.add_parser('vff-single', help='Single octahedron: find 8 Keating minima')
    p.add_argument('--d0', type=float, default=2.35, help='Bond length (A) [2.35]')
    p.add_argument('--alpha', type=float, default=3.0, help='Stretch constant (eV/A^2) [3.0]')
    p.add_argument('--beta', type=float, default=0.75, help='Bend constant (eV/A^2) [0.75]')
    p.add_argument('--n_starts', type=int, default=80, help='Basin-hopping starts [80]')
    p.add_argument('--temp', type=float, default=0.3, help='Basin-hopping temperature [0.3]')

    # vff-not
    p = subparsers.add_parser('vff-not', help='Coupled octahedra NOT gate')
    p.add_argument('--k_coupling', type=float, default=2.0, help='Spring constant (eV/A^2) [2.0]')

    # vff-toffoli
    p = subparsers.add_parser('vff-toffoli', help='Phi-triangle Toffoli gate (64-entry truth table)')
    p.add_argument('--k0', type=float, default=2.0, help='Base coupling constant (eV/A^2) [2.0]')

    # multi-bridge
    p = subparsers.add_parser('multi-bridge', help='Multi-bridge octahedral node')
    p.add_argument('--strain', type=float, default=1.2, help='Biaxial strain (pct) [1.2]')
    p.add_argument('--B_field', type=float, default=0.5, help='Magnetic field z-component (T) [0.5]')

    # lattice
    p = subparsers.add_parser('lattice', help='2D neural lattice relaxation')
    p.add_argument('--nx', type=int, default=4, help='Lattice width [4]')
    p.add_argument('--ny', type=int, default=4, help='Lattice height [4]')
    p.add_argument('--steps', type=int, default=100, help='Relaxation steps [100]')

    # validation
    p = subparsers.add_parser('validation', help='SPM/PL/ODMR experimental validation sim')
    p.add_argument('--noise', type=float, default=0.01, help='Noise level [0.01]')

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    dispatch = {
        'vff-single': cmd_vff_single,
        'vff-not': cmd_vff_not,
        'vff-toffoli': cmd_vff_toffoli,
        'multi-bridge': cmd_multi_bridge,
        'lattice': cmd_lattice,
        'validation': cmd_validation,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
