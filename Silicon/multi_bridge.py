"""
Multi-Bridge Octahedral Node: Harmonic + Magnetic + Optical + Electric
Unified simulation of all four bridges interacting through a single silicon octahedron.
Demonstrates write (strain/voltage), process (spin), and read (optical) operations.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scipy.linalg import expm
from itertools import product

# ============================================================
# 1. BASE OCTAHEDRON (Strain Bridge)
# ============================================================
class SiliconOctahedron:
    def __init__(self, d0=2.35, alpha=3.0, beta=0.75):
        self.d0 = d0
        self.alpha = alpha
        self.beta = beta
        v = 1.0 / np.sqrt(3)
        self.vertices = np.array([
            [ v,  v,  v],
            [-v, -v,  v],
            [-v,  v, -v],
            [ v, -v, -v]
        ]) * self.d0

    def keating_energy(self, disp):
        center = disp
        bonds = self.vertices - center
        stretch_sum = sum((np.dot(b, b) - self.d0**2)**2 for b in bonds)
        E_stretch = (3.0/16.0) * (self.alpha / self.d0**2) * stretch_sum
        from itertools import combinations
        bend_sum = 0.0
        for i, j in combinations(range(4), 2):
            bi, bj = bonds[i], bonds[j]
            ri, rj = np.linalg.norm(bi), np.linalg.norm(bj)
            if ri > 1e-6 and rj > 1e-6:
                cos_theta = np.dot(bi, bj) / (ri * rj)
                delta = cos_theta + 1.0/3.0
                bend_sum += delta**2
        E_bend = (3.0/8.0) * (self.beta / self.d0**2) * bend_sum
        return E_stretch + E_bend

    def strain_tensor_from_displacement(self, disp):
        """Convert central displacement to local strain tensor."""
        strain = np.zeros((3,3))
        for v in self.vertices:
            b_dir = v / np.linalg.norm(v)
            for i in range(3):
                for j in range(3):
                    strain[i,j] += (disp[i] * b_dir[j] + disp[j] * b_dir[i]) / (2 * self.d0**2)
        return strain / 4.0

# ============================================================
# 2. SPIN SYSTEM (Magnetic Bridge)
# ============================================================
class ErPSpinSystem:
    def __init__(self, g_eff=15.0, A_hf=1.0, D_cf=10.0, strain_coupling=50.0):
        self.g = g_eff
        self.A = A_hf
        self.D = D_cf
        self.strain_coupling = strain_coupling
        self.mu_B = 9.274e-24
        self.h = 6.626e-34
        self.ghz_to_ev = 4.13567e-6

    def hamiltonian(self, B_field, strain_tensor=None, E_field=None):
        B_mag = np.linalg.norm(B_field)
        H_zee = self.g * self.mu_B * B_mag / self.h
        H_zee_ev = H_zee * self.ghz_to_ev

        H_cf = self.D * self.ghz_to_ev
        if strain_tensor is not None:
            eps = np.trace(strain_tensor)
            H_cf += self.strain_coupling * eps * self.ghz_to_ev

        # Electric field effect (Stark shift) - simplified
        if E_field is not None:
            # Assume Stark coefficient ~ 10 kHz/(V/m) for Er in Si
            stark_coeff = 1e4 * 1e-6 * self.ghz_to_ev  # convert to eV per V/m
            E_mag = np.linalg.norm(E_field)
            H_cf += stark_coeff * E_mag

        H = np.array([[H_zee_ev + H_cf, 0],
                      [0, -H_zee_ev - H_cf]])
        return H

    def energy_levels(self, B_field, strain_tensor=None, E_field=None):
        H = self.hamiltonian(B_field, strain_tensor, E_field)
        return np.linalg.eigvalsh(H)

# ============================================================
# 3. OPTICAL BRIDGE (1.54 μm Er³⁺ transition)
# ============================================================
class OpticalBridge:
    """
    Er³⁺ ⁴I₁₅/₂ ↔ ⁴I₁₃/₂ transition at 1.54 μm (0.805 eV).
    Absorption/emission couples to strain via deformation potential.
    """
    def __init__(self, transition_energy=0.805, osc_strength=1e-6, strain_coupling=10.0):
        self.E_trans = transition_energy  # eV
        self.osc = osc_strength
        self.strain_coupling = strain_coupling  # eV per unit strain

    def absorption_cross_section(self, photon_energy, strain_tensor=None, linewidth=0.001):
        """Lorentzian lineshape with strain-shifted center."""
        center = self.E_trans
        if strain_tensor is not None:
            eps = np.trace(strain_tensor)
            center += self.strain_coupling * eps
        gamma = linewidth / 2
        return self.osc / (1 + ((photon_energy - center)/gamma)**2)

    def optical_rabi_frequency(self, E_field_optical, strain_tensor=None):
        """Estimate Rabi frequency for a given optical E-field."""
        # Simplified: Ω ∝ μ·E where μ is transition dipole
        dipole_moment = 1e-29  # C·m (typical for f-f transition)
        hbar = 1.054e-34
        omega = dipole_moment * np.linalg.norm(E_field_optical) / hbar  # rad/s
        return omega / (2*np.pi)  # Hz

# ============================================================
# 4. UNIFIED MULTI-BRIDGE NODE
# ============================================================
class MultiBridgeNode:
    """
    Single octahedral node with all four bridges:
      - Harmonic (strain displacement)
      - Magnetic (electron/nuclear spin)
      - Optical (1.54 μm photonic)
      - Electric (Stark shift via gate voltage)
    """
    def __init__(self):
        self.strain = SiliconOctahedron()
        self.spin = ErPSpinSystem()
        self.optical = OpticalBridge()

        # State variables
        self.displacement = np.zeros(3)          # Å
        self.spin_state = 0                       # 0=↓, 1=↑
        self.optical_excited = 0                  # 0=ground, 1=excited
        self.B_field = np.array([0.0, 0.0, 0.1])  # T
        self.E_field = np.array([0.0, 0.0, 0.0])  # V/m

    def total_energy(self, displacement, spin_state=None, optical_excited=None,
                     B_field=None, E_field=None):
        if spin_state is None: spin_state = self.spin_state
        if optical_excited is None: optical_excited = self.optical_excited
        if B_field is None: B_field = self.B_field
        if E_field is None: E_field = self.E_field

        E_strain = self.strain.keating_energy(displacement)
        strain_tensor = self.strain.strain_tensor_from_displacement(displacement)

        # Spin energy
        spin_levels = self.spin.energy_levels(B_field, strain_tensor, E_field)
        E_spin = spin_levels[spin_state]

        # Optical energy (if excited)
        E_opt = self.optical.E_trans if optical_excited else 0.0
        # Optical transition also shifts with strain (already accounted via energy levels if we consider excited state as different electronic config)
        # For simplicity, treat optical excitation as adding a fixed energy plus strain coupling
        if optical_excited:
            eps = np.trace(strain_tensor)
            E_opt += self.optical.strain_coupling * eps

        return E_strain + E_spin + E_opt

    def equilibrium_displacement(self, spin_state=None, optical_excited=None,
                                 B_field=None, E_field=None):
        def objective(disp):
            return self.total_energy(disp, spin_state, optical_excited, B_field, E_field)
        res = minimize(objective, x0=self.displacement, method='L-BFGS-B',
                      bounds=[(-0.8,0.8)]*3)
        return res.x, res.fun

    def update_state(self, spin_state=None, optical_excited=None,
                     B_field=None, E_field=None):
        """Set new control parameters and relax to equilibrium."""
        if spin_state is not None: self.spin_state = spin_state
        if optical_excited is not None: self.optical_excited = optical_excited
        if B_field is not None: self.B_field = B_field
        if E_field is not None: self.E_field = E_field

        disp, energy = self.equilibrium_displacement(
            self.spin_state, self.optical_excited, self.B_field, self.E_field)
        self.displacement = disp
        return energy

    def optical_readout(self, probe_energy=0.805, optical_power=1e-6):
        """
        Simulate photoluminescence readout.
        Returns absorption signal based on current strain and spin state.
        """
        strain_tensor = self.strain.strain_tensor_from_displacement(self.displacement)
        cross_section = self.optical.absorption_cross_section(probe_energy, strain_tensor)
        # In reality, spin state affects PL intensity due to selection rules.
        # Here we model as different oscillator strength for spin states.
        spin_factor = 1.0 if self.spin_state == 0 else 0.3  # example contrast
        return cross_section * spin_factor

# ============================================================
# 5. MULTI-BRIDGE DEMONSTRATIONS
# ============================================================
def demo_strain_writes_spin_reads_optical():
    """
    Show how mechanical strain (write) changes spin levels,
    which can be read out optically.
    """
    print("="*60)
    print("DEMO 1: Strain Write → Spin Process → Optical Read")
    print("="*60)

    node = MultiBridgeNode()

    # Vary displacement manually along [111]
    direction = np.array([1,1,1])/np.sqrt(3)
    disp_vals = np.linspace(-0.5, 0.5, 50)

    absorption = []
    for d in disp_vals:
        node.displacement = direction * d
        abs_signal = node.optical_readout()
        absorption.append(abs_signal)

    plt.figure(figsize=(8,4))
    plt.plot(disp_vals, absorption)
    plt.xlabel('Displacement along [111] (Å)')
    plt.ylabel('Optical Absorption (a.u.)')
    plt.title('Strain-Modulated Optical Readout')
    plt.grid(alpha=0.3)
    plt.savefig('strain_optical_readout.png', dpi=150)
    plt.show()
    print("Plot saved: strain_optical_readout.png")

def demo_electric_controls_spin():
    """
    Show how electric field (gate voltage) shifts spin resonance.
    """
    print("\n" + "="*60)
    print("DEMO 2: Electric Field Control of Spin")
    print("="*60)

    node = MultiBridgeNode()
    node.displacement = np.zeros(3)  # fix strain

    E_fields = np.linspace(0, 1e7, 50)  # 0 to 10 MV/m
    spin_gaps = []
    for Ez in E_fields:
        E = np.array([0,0,Ez])
        levels = node.spin.energy_levels(node.B_field, E_field=E)
        gap = levels[1] - levels[0]
        spin_gaps.append(gap * 1000)  # meV

    plt.figure(figsize=(8,4))
    plt.plot(E_fields/1e6, spin_gaps)
    plt.xlabel('Electric Field (MV/m)')
    plt.ylabel('Spin Energy Gap (meV)')
    plt.title('Stark Shift of Spin Levels')
    plt.grid(alpha=0.3)
    plt.savefig('electric_spin_control.png', dpi=150)
    plt.show()
    print("Plot saved: electric_spin_control.png")

def demo_optical_write_strain_response():
    """
    Optical excitation changes equilibrium displacement.
    This is the inverse of Demo 1.
    """
    print("\n" + "="*60)
    print("DEMO 3: Optical Write → Strain Response")
    print("="*60)

    node = MultiBridgeNode()

    # Ground state equilibrium
    disp_ground, e_ground = node.equilibrium_displacement(optical_excited=0)
    # Excited state equilibrium
    disp_excited, e_excited = node.equilibrium_displacement(optical_excited=1)

    print(f"Ground state displacement: {np.round(disp_ground, 3)} Å")
    print(f"Excited state displacement: {np.round(disp_excited, 3)} Å")
    delta = np.linalg.norm(disp_excited - disp_ground)
    print(f"Optically induced strain shift: {delta:.3f} Å")
    print("→ Optical pulse can toggle the octahedral state.")

def demo_full_cross_coupling():
    """
    Show how all bridges interact: electric field changes strain,
    which shifts optical resonance, which modifies spin readout.
    """
    print("\n" + "="*60)
    print("DEMO 4: Full Cross-Bridge Interaction")
    print("="*60)

    node = MultiBridgeNode()

    # Vary electric field, relax displacement, then measure optical absorption
    E_vals = np.linspace(0, 5e6, 30)
    abs_down = []
    abs_up = []

    for Ez in E_vals:
        E = np.array([0,0,Ez])
        # Relax for spin down
        node.update_state(spin_state=0, E_field=E)
        abs_down.append(node.optical_readout())
        # Relax for spin up
        node.update_state(spin_state=1, E_field=E)
        abs_up.append(node.optical_readout())

    plt.figure(figsize=(8,5))
    plt.plot(E_vals/1e6, abs_down, 'b-', label='Spin ↓')
    plt.plot(E_vals/1e6, abs_up, 'r-', label='Spin ↑')
    plt.xlabel('Electric Field (MV/m)')
    plt.ylabel('Optical Absorption (a.u.)')
    plt.title('Electric Field Modulates Optical Readout of Spin State')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig('full_cross_coupling.png', dpi=150)
    plt.show()
    print("Plot saved: full_cross_coupling.png")

def demo_multi_bridge_truth_table():
    """
    Construct a truth table showing how different bridge inputs
    map to the final octahedral state (3-bit face index).
    """
    print("\n" + "="*60)
    print("DEMO 5: Multi-Bridge State Encoding")
    print("="*60)

    # Define the 8 face normals
    signs = np.array([(x,y,z) for x in [1,-1] for y in [1,-1] for z in [1,-1]])
    face_normals = signs / np.sqrt(3)
    def classify_face(disp):
        if np.linalg.norm(disp) < 0.1: return -1
        d_norm = disp / np.linalg.norm(disp)
        return np.argmax([np.dot(d_norm, f) for f in face_normals])

    node = MultiBridgeNode()
    # Inputs: spin, optical excitation, E-field polarity (simplified)
    configs = [
        (0,0, 0.0),   # spin down, ground, zero E
        (0,0, 1e6),   # spin down, ground, +E
        (0,1, 0.0),   # spin down, excited, zero E
        (0,1, 1e6),
        (1,0, 0.0),
        (1,0, 1e6),
        (1,1, 0.0),
        (1,1, 1e6),
    ]
    print(f"{'Spin':^5} {'Opt':^5} {'E (MV/m)':^10} → {'Face':^6} {'Displacement':^20}")
    print("-"*50)
    for s, o, ez in configs:
        E = np.array([0,0,ez])
        disp, _ = node.equilibrium_displacement(spin_state=s, optical_excited=o, E_field=E)
        face = classify_face(disp)
        face_label = ['111','110','101','100','011','010','001','000'][face] if face>=0 else 'center'
        print(f"{'↓' if s==0 else '↑':^5} {o:^5} {ez/1e6:^10.1f} → {face_label:^6} {np.round(disp,3)}")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    demo_strain_writes_spin_reads_optical()
    demo_electric_controls_spin()
    demo_optical_write_strain_response()
    demo_full_cross_coupling()
    demo_multi_bridge_truth_table()

    print("\n✅ All multi-bridge demonstrations complete.")
    print("The unified node can be addressed by strain, B-field, E-field, or light.")
    print("Next: Network these nodes into a multi-bridge neural lattice.")
