# STATUS: infrastructure -- extended CLI for thermal/acoustic/entropy modes
# ----- acoustic (SAW/BAW modulation) -----
acoustic_parser = subparsers.add_parser('acoustic', help='Simulate acoustic modulation of FRET')
acoustic_parser.add_argument('--r0', type=float, default=3.0, help='Mean distance (nm) [3.0]')
acoustic_parser.add_argument('--R0', type=float, default=5.0, help='Förster radius (nm) [5.0]')
acoustic_parser.add_argument('--amplitude', type=float, default=0.2, help='Oscillation amplitude (nm) [0.2]')
acoustic_parser.add_argument('--frequency', type=float, default=10.0, help='Acoustic frequency (MHz) [10.0]')
acoustic_parser.add_argument('--tau_D', type=float, default=2.5, help='Donor lifetime (ns) [2.5]')
acoustic_parser.add_argument('--k_rad', type=float, default=0.1, help='Radiative rate (ns⁻¹) [0.1]')
acoustic_parser.add_argument('--k_nr', type=float, default=0.05, help='Non-radiative rate (ns⁻¹) [0.05]')
acoustic_parser.add_argument('--sweep_amplitude', action='store_true', help='Sweep amplitude and plot gain curve')
acoustic_parser.add_argument('--A_min', type=float, default=0.0)
acoustic_parser.add_argument('--A_max', type=float, default=1.0)
acoustic_parser.add_argument('--output', '-o', help='Save results JSON')
acoustic_parser.add_argument('--plot', '-p', help='Save plot PNG')

# ----- thermal (temperature effects) -----
thermal_parser = subparsers.add_parser('thermal', help='Simulate thermal gating and phonon-assisted FRET')
thermal_parser.add_argument('--mode', choices=['shift','switch','phonon','combined'], default='combined',
                            help='Thermal effect to simulate')
thermal_parser.add_argument('--r0', type=float, default=3.0, help='Base distance (nm) [3.0]')
thermal_parser.add_argument('--R0', type=float, default=5.0, help='Base R0 (nm) [5.0]')
thermal_parser.add_argument('--tau_D', type=float, default=2.5, help='Donor lifetime (ns) [2.5]')
thermal_parser.add_argument('--T_min', type=float, default=250, help='Min temperature (K) [250]')
thermal_parser.add_argument('--T_max', type=float, default=350, help='Max temperature (K) [350]')
thermal_parser.add_argument('--T_points', type=int, default=100)
# Thermal shift params
thermal_parser.add_argument('--J0', type=float, default=1e15, help='J at T0')
thermal_parser.add_argument('--Phi_D0', type=float, default=0.6, help='Φ_D at T0')
thermal_parser.add_argument('--alpha_J', type=float, default=-0.002, help='dJ/dT coefficient')
thermal_parser.add_argument('--alpha_Phi', type=float, default=-0.001, help='dΦ/dT coefficient')
# Switch params
thermal_parser.add_argument('--r_open', type=float, default=5.0, help='Open state distance (nm)')
thermal_parser.add_argument('--r_closed', type=float, default=2.5, help='Closed state distance (nm)')
thermal_parser.add_argument('--Tm', type=float, default=310.0, help='Melting temperature (K)')
thermal_parser.add_argument('--dH', type=float, default=100.0, help='Enthalpy change (kJ/mol)')
thermal_parser.add_argument('--dCp', type=float, default=0.0, help='Heat capacity change (kJ/mol·K)')
# Phonon assist params
thermal_parser.add_argument('--delta_E', type=float, default=10.0, help='Energy mismatch (meV)')
thermal_parser.add_argument('--phonon_energy', type=float, default=15.0, help='Phonon energy (meV)')
thermal_parser.add_argument('--S', type=float, default=0.1, help='Huang-Rhys factor')
thermal_parser.add_argument('--output', '-o', help='Save results JSON')
thermal_parser.add_argument('--plot', '-p', help='Save plot PNG')
