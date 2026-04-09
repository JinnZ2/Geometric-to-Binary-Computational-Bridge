# STATUS: infrastructure -- frontier CLI registration for speculative physics modes
"""
Registers the 'frontier' subcommand on an argparse subparsers object.
Called by cli.py's main(). Covers: time crystals, vacuum, thermo,
axion, radical pair, QET, unified.
"""


def register_frontier_subcommands(subparsers):
    """Add the 'frontier' subcommand to the FRET CLI."""

    frontier_parser = subparsers.add_parser('frontier', help='Explore speculative physics arenas')
    frontier_parser.add_argument('arena', choices=['time', 'vacuum', 'thermo', 'axion', 'radical', 'qet', 'unified'],
                                 help='Arena to simulate')
    # Time crystal params
    frontier_parser.add_argument('--n0', type=float, default=1.5, help='Avg refractive index')
    frontier_parser.add_argument('--delta_n', type=float, default=0.1)
    frontier_parser.add_argument('--freq', type=float, default=10.0, help='Modulation frequency (MHz)')
    # Vacuum params
    frontier_parser.add_argument('--d_plate', type=float, default=100.0, help='Plate separation (nm)')
    frontier_parser.add_argument('--area', type=float, default=1e6, help='Area (nm^2)')
    # Thermo params
    frontier_parser.add_argument('--energy', type=float, default=2.0, help='Donor energy (eV)')
    frontier_parser.add_argument('--temp', type=float, default=300.0, help='Temperature (K)')
    # Axion params
    frontier_parser.add_argument('--B_field', type=float, default=10.0, help='Magnetic field (T)')
    frontier_parser.add_argument('--axion_mass', type=float, default=1e-5, help='Axion mass (eV)')
    # Radical pair params
    frontier_parser.add_argument('--B_strength', type=float, default=0.0, help='Magnetic field (mT)')
    # QET params
    frontier_parser.add_argument('--chain_len', type=int, default=10)
    frontier_parser.add_argument('--distance', type=int, default=5)
    # Output
    frontier_parser.add_argument('--output', '-o', help='Save results JSON')
    frontier_parser.add_argument('--plot', '-p', help='Save plot PNG')
