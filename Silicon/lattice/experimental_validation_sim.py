# STATUS: infrastructure -- SPM/PL/ODMR simulator with realistic noise
"""
Experimental Validation Simulator for Octahedral 8-State Encoding
Simulates SPM force curves, PL spectra, and ODMR for a single Er:P center in strained Si.
Includes realistic noise, temperature effects, and measurement resolution limits.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize, curve_fit
from scipy.signal import find_peaks

# ============================================================
# 1. PHYSICS MODELS (from previous work, condensed)
# ============================================================
class SiliconOctahedron:
    def __init__(self, d0=2.35, alpha=3.0, beta=0.75):
        self.d0 = d0
        self.alpha = alpha
        self.beta = beta
        v = 1.0 / np.sqrt(3)
        self.vertices = np.array([[ v, v, v], [-v,-v, v], [-v, v,-v], [ v,-v,-v]]) * self.d0

    def keating_energy(self, disp):
        bonds = self.vertices - disp
        stretch = sum((np.dot(b,b) - self.d0**2)**2 for b in bonds)
        E_stretch = (3/16) * (self.alpha/self.d0**2) * stretch
        from itertools import combinations
        bend = 0.0
        for i,j in combinations(range(4),2):
            bi, bj = bonds[i], bonds[j]
            ri, rj = np.linalg.norm(bi), np.linalg.norm(bj)
            if ri>1e-6 and rj>1e-6:
                cos = np.dot(bi,bj)/(ri*rj)
                bend += (cos + 1/3)**2
        E_bend = (3/8) * (self.beta/self.d0**2) * bend
        return E_stretch + E_bend

    def force(self, disp):
        """Negative gradient of energy."""
        eps = 1e-6
        grad = np.zeros(3)
        E0 = self.keating_energy(disp)
        for i in range(3):
            d = disp.copy()
            d[i] += eps
            grad[i] = (self.keating_energy(d) - E0) / eps
        return -grad  # Force = -dE/dx

class ErPSpinSystem:
    def __init__(self, g=15.0, D=10.0, strain_coupling=50.0):
        self.g = g
        self.D = D  # GHz
        self.strain_coupling = strain_coupling  # GHz/strain
        self.mu_B = 9.274e-24
        self.h = 6.626e-34
        self.ghz_to_ev = 4.13567e-6

    def energy_levels(self, B_field, strain_tensor):
        B_mag = np.linalg.norm(B_field)
        E_zee = self.g * self.mu_B * B_mag / self.h  # Hz
        eps = np.trace(strain_tensor)
        E_cf = self.D + self.strain_coupling * eps  # GHz
        E_total = (E_zee*1e-9 + E_cf) * self.ghz_to_ev  # eV
        return np.array([-E_total/2, E_total/2])  # symmetric splitting

    def resonance_frequency(self, B_field, strain_tensor):
        levels = self.energy_levels(B_field, strain_tensor)
        return (levels[1] - levels[0]) / 4.13567e-15  # Hz

class OpticalBridge:
    def __init__(self, E0=0.805, strain_coupling=10.0, linewidth=0.001):
        self.E0 = E0  # eV
        self.strain_coupling = strain_coupling  # eV/unit strain
        self.gamma = linewidth  # eV

    def emission_spectrum(self, photon_energy, strain_tensor):
        eps = np.trace(strain_tensor)
        center = self.E0 + self.strain_coupling * eps
        return 1.0 / (1 + ((photon_energy - center)/self.gamma)**2)

# ============================================================
# 2. SIMULATED EXPERIMENTAL APPARATUS
# ============================================================
class ExperimentSimulator:
    def __init__(self, temperature=300):
        self.T = temperature  # K
        self.kT = 8.617e-5 * temperature  # eV
        self.strain_model = SiliconOctahedron()
        self.spin_model = ErPSpinSystem()
        self.optical = OpticalBridge()
        # Define the 8 face directions for reference
        signs = np.array([(x,y,z) for x in [1,-1] for y in [1,-1] for z in [1,-1]])
        self.face_normals = signs / np.sqrt(3)
        # Equilibrium displacements for each state (will be computed)
        self.state_displacements = None

    def find_equilibrium_states(self):
        """Locate the 8 energy minima via basin-hopping."""
        from scipy.optimize import basinhopping
        minima = []
        bounds = [(-0.8,0.8)]*3
        class TakeStep:
            def __init__(self, bounds): self.bounds = bounds
            def __call__(self, x):
                return np.clip(x + np.random.uniform(-0.2,0.2,3),
                               [b[0] for b in bounds], [b[1] for b in bounds])
        take_step = TakeStep(bounds)
        for _ in range(50):
            x0 = np.random.uniform(-0.6,0.6,3)
            res = basinhopping(self.strain_model.keating_energy, x0, niter=30, T=0.3,
                               stepsize=0.2, take_step=take_step,
                               minimizer_kwargs={"method":"L-BFGS-B","bounds":bounds})
            rounded = np.round(res.x, 3)
            if not any(np.allclose(rounded, m, atol=0.05) for m in minima):
                minima.append(rounded)
        self.state_displacements = np.array(minima)
        return self.state_displacements

    # ------------------- SPM Force Curve Simulation -------------------
    def simulate_spm_force_curve(self, direction, state_index=None, noise_level=0.01):
        """
        Simulate an SPM tip pushing/pulling along a specific direction.
        direction: 3D vector (e.g., one of the face normals).
        state_index: if None, start from center; else start from that state.
        Returns: displacement array, force magnitude along direction, noise added.
        """
        if state_index is not None:
            start_disp = self.state_displacements[state_index]
        else:
            start_disp = np.zeros(3)
        # Generate path along direction
        d_vals = np.linspace(-0.6, 0.6, 200)
        disp_path = np.array([start_disp + d * direction for d in d_vals])
        forces = []
        for disp in disp_path:
            F = self.strain_model.force(disp)
            F_proj = np.dot(F, direction)
            forces.append(F_proj + np.random.normal(0, noise_level))
        return d_vals, np.array(forces)

    # ------------------- Photoluminescence Spectroscopy -------------------
    def simulate_pl_spectrum(self, state_index, energy_range, noise_level=0.05):
        """
        Simulate a PL spectrum for a given state.
        Returns photon energies and intensity (with shot noise).
        """
        disp = self.state_displacements[state_index]
        strain_tensor = self._strain_tensor_from_disp(disp)
        intensity = self.optical.emission_spectrum(energy_range, strain_tensor)
        # Add Poisson-like noise
        noisy_intensity = intensity + np.random.normal(0, noise_level, size=len(intensity))
        return energy_range, np.maximum(noisy_intensity, 0)

    def _strain_tensor_from_disp(self, disp):
        """Approximate strain tensor from displacement (as before)."""
        strain = np.zeros((3,3))
        for v in self.strain_model.vertices:
            b_dir = v / np.linalg.norm(v)
            for i in range(3):
                for j in range(3):
                    strain[i,j] += (disp[i]*b_dir[j] + disp[j]*b_dir[i])/(2*self.strain_model.d0**2)
        return strain / 4.0

    # ------------------- ODMR Simulation -------------------
    def simulate_odmr(self, state_index, B_field, freq_range, noise_level=0.02):
        """
        Simulate optically detected magnetic resonance.
        Returns frequency and ODMR contrast (change in PL).
        """
        disp = self.state_displacements[state_index]
        strain_tensor = self._strain_tensor_from_disp(disp)
        # Resonance frequency
        f_res = self.spin_model.resonance_frequency(B_field, strain_tensor)
        # Generate Lorentzian dip
        contrast = 1.0 / (1 + ((freq_range - f_res)/5e6)**2)  # 5 MHz linewidth
        noisy = contrast + np.random.normal(0, noise_level, size=len(freq_range))
        return freq_range, np.maximum(noisy, 0)

    # ------------------- Full State Mapping Experiment -------------------
    def run_full_characterization(self):
        """Simulate a complete experimental characterization of all 8 states."""
        print("="*70)
        print("EXPERIMENTAL VALIDATION OF 8-STATE ENCODING")
        print("="*70)

        # 1. Find theoretical states
        states = self.find_equilibrium_states()
        print(f"\nFound {len(states)} equilibrium displacement states:")
        for i, s in enumerate(states):
            print(f"State {i}: {np.round(s,3)} Å")

        # 2. Simulate SPM force curves along [111] direction
        direction = np.array([1,1,1])/np.sqrt(3)
        plt.figure(figsize=(12,8))
        colors = plt.cm.tab10(np.linspace(0,1,8))
        for i in range(min(8, len(states))):
            d, F = self.simulate_spm_force_curve(direction, state_index=i, noise_level=0.005)
            plt.plot(d, F, color=colors[i], alpha=0.7, label=f'State {i}')
        plt.xlabel('Displacement along [111] (Å)')
        plt.ylabel('Force (eV/Å)')
        plt.title('SPM Force Curves: Distinguishing 8 Strain States')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.savefig('spm_force_curves.png', dpi=150)
        plt.show()

        # 3. Simulate PL spectra for each state
        energies = np.linspace(0.80, 0.82, 500)
        plt.figure(figsize=(12,6))
        for i in range(min(8, len(states))):
            e, spec = self.simulate_pl_spectrum(i, energies, noise_level=0.03)
            plt.plot(e, spec, color=colors[i], alpha=0.7, label=f'State {i}')
        plt.xlabel('Photon Energy (eV)')
        plt.ylabel('PL Intensity (a.u.)')
        plt.title('Strain-Shifted Photoluminescence: 8 Distinct Spectra')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.savefig('pl_spectra.png', dpi=150)
        plt.show()

        # 4. Simulate ODMR for two example states to show magnetic contrast
        B = np.array([0,0,0.05])  # 50 mT
        freqs = np.linspace(1e9, 3e9, 500)
        plt.figure(figsize=(10,5))
        for i in [0, 4]:  # e.g., opposite faces
            f, odmr = self.simulate_odmr(i, B, freqs, noise_level=0.02)
            plt.plot(f/1e9, odmr, label=f'State {i}', alpha=0.8)
        plt.xlabel('Frequency (GHz)')
        plt.ylabel('ODMR Contrast')
        plt.title('Magnetic Resonance Differentiation')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.savefig('odmr_spectra.png', dpi=150)
        plt.show()

        # 5. State distinguishability analysis
        self._analyze_distinguishability()

    def _analyze_distinguishability(self):
        """Compute how well the states can be resolved experimentally."""
        print("\n--- Distinguishability Analysis ---")
        # Compute pairwise distances in (strain, optical shift, spin freq) space
        states = self.state_displacements
        n = len(states)
        metrics = np.zeros((n, 3))  # [strain_mag, optical_shift, spin_freq]
        B_ref = np.array([0,0,0.1])
        for i, disp in enumerate(states):
            strain_tensor = self._strain_tensor_from_disp(disp)
            eps = np.trace(strain_tensor)
            metrics[i,0] = np.linalg.norm(disp)
            metrics[i,1] = self.optical.strain_coupling * eps  # eV shift
            metrics[i,2] = self.spin_model.resonance_frequency(B_ref, strain_tensor)/1e9  # GHz

        print("State  Strain(A)  OptShift(meV)  SpinFreq(GHz)")
        for i in range(n):
            print(f"  {i}    {metrics[i,0]:.3f}      {metrics[i,1]*1000:.2f}         {metrics[i,2]:.2f}")

        # Minimum separation
        min_sep = np.inf
        for i in range(n):
            for j in range(i+1,n):
                sep = np.linalg.norm(metrics[i] - metrics[j])
                if sep < min_sep:
                    min_sep = sep
        print(f"\nMinimum separation in combined metric space: {min_sep:.4f}")
        if min_sep > 0.1:
            print("✅ States are well separated and experimentally resolvable.")
        else:
            print("⚠️ Some states may be difficult to distinguish; need higher resolution measurements.")

# ============================================================
# 3. RUN THE EXPERIMENT SIMULATION
# ============================================================
if __name__ == "__main__":
    exp = ExperimentSimulator(temperature=300)
    exp.run_full_characterization()
