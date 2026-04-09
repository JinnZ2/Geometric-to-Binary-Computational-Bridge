def cmd_acoustic(args):
    """Run acoustic modulation simulation."""
    import matplotlib.pyplot as plt
    from acoustic_fret import AcousticModulator, saw_fret_efficiency

    if args.sweep_amplitude:
        mod = AcousticModulator(args.r0, 0.1, args.frequency, args.R0, args.tau_D)
        A_vals, gains = mod.parametric_gain_curve((args.A_min, args.A_max))
        plt.figure()
        plt.plot(A_vals, gains, 'b-')
        plt.xlabel('Amplitude A (nm)')
        plt.ylabel('Enhancement Factor E_avg / E_static')
        plt.title('Parametric Gain from Acoustic Modulation')
        plt.grid(True)
        results = {'A_vals': A_vals.tolist(), 'gains': gains.tolist()}
    else:
        mod = AcousticModulator(args.r0, args.amplitude, args.frequency, args.R0, args.tau_D)
        E_static = E_FRET(args.r0, args.R0)
        E_avg = mod.average_efficiency()
        gain = E_avg / E_static
        print(f"Static efficiency: {E_static:.4f}")
        print(f"Average efficiency under {args.frequency} MHz, {args.amplitude} nm modulation: {E_avg:.4f}")
        print(f"Enhancement factor: {gain:.4f}")
        results = {'r0': args.r0, 'amplitude': args.amplitude, 'frequency': args.frequency,
                   'E_static': E_static, 'E_avg': E_avg, 'gain': gain}
        # Could also plot one cycle
        t = np.linspace(0, 1/args.frequency, 200)
        E_inst = [mod.E_inst(ti) for ti in t]
        plt.figure()
        plt.plot(t, E_inst)
        plt.axhline(E_static, color='r', linestyle='--', label='Static')
        plt.axhline(E_avg, color='g', linestyle='--', label='Average')
        plt.xlabel('Time (μs)')
        plt.ylabel('Efficiency')
        plt.legend()
        plt.title('Instantaneous FRET Efficiency')

    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
    if args.plot:
        plt.savefig(args.plot)
    else:
        plt.show()

def cmd_thermal(args):
    """Run thermal simulation."""
    import matplotlib.pyplot as plt
    from thermal_fret import (ThermalSpectralShift, ThermalSwitch,
                              PhononAssistedFRET, ThermalFRETSystem)
    T_vals = np.linspace(args.T_min, args.T_max, args.T_points)
    eff = np.zeros_like(T_vals)

    if args.mode == 'shift':
        ts = ThermalSpectralShift(args.J0, args.Phi_D0, alpha_J=args.alpha_J, alpha_Phi=args.alpha_Phi)
        system = ThermalFRETSystem(args.r0, args.R0, args.tau_D, thermal_shift=ts)
        for i, T in enumerate(T_vals):
            eff[i] = system.efficiency(T)
        plt.plot(T_vals, eff)
        plt.ylabel('Efficiency')
        plt.xlabel('Temperature (K)')
        plt.title('Temperature-Dependent R0')

    elif args.mode == 'switch':
        sw = ThermalSwitch(args.r_open, args.r_closed, args.Tm, args.dH, args.dCp)
        system = ThermalFRETSystem(args.r0, args.R0, args.tau_D, switch=sw)
        for i, T in enumerate(T_vals):
            eff[i] = system.efficiency(T)
        plt.plot(T_vals, eff)
        plt.ylabel('Efficiency')
        plt.xlabel('Temperature (K)')
        plt.title('Thermal Conformational Switch')

    elif args.mode == 'phonon':
        pa = PhononAssistedFRET(args.delta_E, args.phonon_energy, args.tau_D, args.R0)
        system = ThermalFRETSystem(args.r0, args.R0, args.tau_D, phonon_assist=pa)
        for i, T in enumerate(T_vals):
            eff[i] = system.efficiency(T)
        plt.plot(T_vals, eff)
        plt.ylabel('Efficiency')
        plt.xlabel('Temperature (K)')
        plt.title('Phonon-Assisted FRET')

    elif args.mode == 'combined':
        ts = ThermalSpectralShift(args.J0, args.Phi_D0, alpha_J=args.alpha_J, alpha_Phi=args.alpha_Phi)
        sw = ThermalSwitch(args.r_open, args.r_closed, args.Tm, args.dH, args.dCp)
        pa = PhononAssistedFRET(args.delta_E, args.phonon_energy, args.tau_D, args.R0)
        system = ThermalFRETSystem(args.r0, args.R0, args.tau_D, thermal_shift=ts, switch=sw, phonon_assist=pa)
        for i, T in enumerate(T_vals):
            eff[i] = system.efficiency(T)
        plt.plot(T_vals, eff)
        plt.ylabel('Efficiency')
        plt.xlabel('Temperature (K)')
        plt.title('Combined Thermal Effects')

    plt.grid(True)
    results = {'T_vals': T_vals.tolist(), 'efficiency': eff.tolist()}
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
    if args.plot:
        plt.savefig(args.plot)
    else:
        plt.show()
