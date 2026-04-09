# STATUS: speculative -- electron/nuclear spin coupling demo in octahedral geometry
"""
Multi-Bridge Octahedral Node: Strain + Spin Coupling
Adds electron spin (Er³⁺) and nuclear spin (³¹P) to the octahedral strain model.
Demonstrates cross-talk between harmonic (phonon) and magnetic (spin) bridges.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from itertools import product

# ============================================================
# 1. BASE OCTAHEDRON (Strain only, as before)
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

# ============================================================
# 2. SPIN HAMILTONIAN FOR Er³⁺:P COMPLEX
# ============================================================
class ErPSpinSystem:
    """
    Simplified spin Hamiltonian for an Er³⁺ ion coupled to a ³¹P nuclear spin.
    Includes:
      - Electronic Zeeman (g ≈ 15 for Er³⁺ in Si)
      - Hyperfine coupling to ³¹P (A ≈ 1 GHz)
      - Crystal field (simplified as uniaxial anisotropy)
      - Strain-spin coupling (deformation potential)
    """
    def __init__(self, 
                 g_eff=15.0,          # Er³⁺ effective g-factor
                 A_hf=1.0,            # Hyperfine constant (GHz)
                 D_cf=10.0,           # Crystal field splitting (GHz)
                 strain_coupling=50.0): # Strain-spin coupling (GHz per strain)
        self.g = g_eff
        self.A = A_hf
        self.D = D_cf
        self.strain_coupling = strain_coupling  # ∂D/∂ε
        
        # Physical constants for conversion
        self.mu_B = 9.274e-24  # J/T
        self.h = 6.626e-34     # J·s
        # Convert GHz to eV: 1 GHz = 4.13567e-6 eV
        self.ghz_to_ev = 4.13567e-6
        
    def hamiltonian(self, B_field, strain_tensor=None):
        """
        Return 2x2 Hamiltonian for the effective spin-1/2 Kramers doublet.
        B_field: magnetic field vector (T)
        strain_tensor: 3x3 symmetric strain matrix (unitless)
        """
        # Electronic Zeeman (simplified: isotropic for demonstration)
        B_mag = np.linalg.norm(B_field)
        H_zee = self.g * self.mu_B * B_mag / self.h  # in Hz
        H_zee_ev = H_zee * self.ghz_to_ev
        
        # Crystal field (axial, along z)
        H_cf = self.D * self.ghz_to_ev  # in eV
        
        # Strain coupling: strain modifies D parameter
        if strain_tensor is not None:
            # Use trace as scalar strain measure (simplified)
            eps = np.trace(strain_tensor)
            H_cf += self.strain_coupling * eps * self.ghz_to_ev
        
        # Hyperfine: For simplicity, treat as effective field along z
        # In real system, this would be a 4x4 matrix (electron + nuclear)
        H_hf = self.A * self.ghz_to_ev  # in eV
        
        # Total effective Hamiltonian (2x2 for electron spin)
        # We use Pauli matrices
        H = np.array([[H_zee_ev + H_cf, 0],
                      [0, -H_zee_ev - H_cf]])
        return H
    
    def energy_levels(self, B_field, strain_tensor=None):
        """Return eigenvalues of spin Hamiltonian in eV."""
        H = self.hamiltonian(B_field, strain_tensor)
        return np.linalg.eigvalsh(H)

# ============================================================
# 3. COMBINED STRAIN-SPIN NODE
# ============================================================
class SpinStrainNode:
    """
    A single octahedral node with both strain displacement and spin state.
    Total energy = Keating(strain) + Spin_Energy(strain, B)
    The strain-spin coupling allows the two bridges to interact.
    """
    def __init__(self, 
                 d0=2.35, alpha=3.0, beta=0.75,
                 g_eff=15.0, A_hf=1.0, D_cf=10.0, strain_coupling=50.0):
        self.strain_model = SiliconOctahedron(d0, alpha, beta)
        self.spin_model = ErPSpinSystem(g_eff, A_hf, D_cf, strain_coupling)
        
        # Current state
        self.displacement = np.zeros(3)
        self.spin_state = 0  # 0 for ground, 1 for excited (within doublet)
        self.B_field = np.array([0.0, 0.0, 0.1])  # default 0.1 T along z
        
    def strain_tensor_from_displacement(self, disp):
        """
        Convert central atom displacement to an approximate local strain tensor.
        For a tetrahedral cluster, the strain is roughly proportional to disp.
        We use a simple model: strain_ij = (disp_i * d_j + disp_j * d_i) / (2 d0^2)
        where d is the ideal vertex vector average.
        """
        # Average over 4 bonds to get effective strain
        strain = np.zeros((3,3))
        for v in self.strain_model.vertices:
            # Bond direction unit vector
            b_dir = v / np.linalg.norm(v)
            # Strain contribution from this bond
            for i in range(3):
                for j in range(3):
                    strain[i,j] += (disp[i] * b_dir[j] + disp[j] * b_dir[i]) / (2 * self.strain_model.d0**2)
        return strain / 4.0  # average
    
    def total_energy(self, displacement, spin_state=None, B_field=None):
        """
        Compute total energy including strain and spin contributions.
        spin_state: 0 for ground spin state, 1 for excited
        """
        if spin_state is None:
            spin_state = self.spin_state
        if B_field is None:
            B_field = self.B_field
            
        E_strain = self.strain_model.keating_energy(displacement)
        strain_tensor = self.strain_tensor_from_displacement(displacement)
        levels = self.spin_model.energy_levels(B_field, strain_tensor)
        E_spin = levels[spin_state]  # 0 = lower, 1 = upper
        
        return E_strain + E_spin
    
    def find_equilibrium(self, spin_state=None, B_field=None):
        """
        Find displacement that minimizes total energy for a given spin state.
        """
        if spin_state is None:
            spin_state = self.spin_state
        if B_field is None:
            B_field = self.B_field
            
        def objective(disp):
            return self.total_energy(disp, spin_state, B_field)
        
        res = minimize(objective, x0=np.zeros(3), method='L-BFGS-B',
                      bounds=[(-0.8, 0.8)]*3)
        return res.x, res.fun
    
    def spin_flip_energy_barrier(self, B_field=None):
        """
        Compute energy difference between spin states at equilibrium displacement.
        Also compute barrier for strain-mediated flip.
        """
        # Equilibrium for spin down (0)
        disp0, E0 = self.find_equilibrium(spin_state=0, B_field=B_field)
        # Equilibrium for spin up (1)
        disp1, E1 = self.find_equilibrium(spin_state=1, B_field=B_field)
        
        # Energy at crossing point (where levels are degenerate)
        # For a strain-coupled system, there's a specific strain that makes H_cf + H_zee = 0
        # Find that displacement
        def find_crossing():
            # Simple search along direction connecting the two minima
            direction = disp1 - disp0
            if np.linalg.norm(direction) < 1e-6:
                direction = np.array([0.1, 0.0, 0.0])
            # Scan for minimum energy gap
            best_disp = None
            min_gap = np.inf
            for t in np.linspace(0, 1, 50):
                d_test = disp0 + t * direction
                strain_tensor = self.strain_tensor_from_displacement(d_test)
                levels = self.spin_model.energy_levels(B_field, strain_tensor)
                gap = np.abs(levels[1] - levels[0])
                if gap < min_gap:
                    min_gap = gap
                    best_disp = d_test
            return best_disp, min_gap
        
        cross_disp, min_gap = find_crossing()
        E_cross = self.total_energy(cross_disp, spin_state=0, B_field=B_field)
        barrier = E_cross - E0
        
        return {
            'E_down': E0, 'disp_down': disp0,
            'E_up': E1, 'disp_up': disp1,
            'E_cross': E_cross, 'disp_cross': cross_disp,
            'barrier': barrier, 'min_gap': min_gap
        }

# ============================================================
# 4. SIMULATION AND VISUALIZATION
# ============================================================
def simulate_spin_strain_coupling():
    print("🔗 SPIN-STRAIN COUPLED OCTAHEDRAL NODE")
    print("="*60)
    
    node = SpinStrainNode()
    
    # 1. Show how strain changes spin energy levels
    print("\n1. Strain dependence of spin levels:")
    displacements = np.linspace(-0.6, 0.6, 100)
    # Displace along [111] direction (face normal)
    direction = np.array([1,1,1]) / np.sqrt(3)
    
    spin_levels = []
    strain_energy = []
    for d in displacements:
        disp = direction * d
        E_strain = node.strain_model.keating_energy(disp)
        strain_tensor = node.strain_tensor_from_displacement(disp)
        levels = node.spin_model.energy_levels(node.B_field, strain_tensor)
        spin_levels.append(levels)
        strain_energy.append(E_strain)
    
    spin_levels = np.array(spin_levels)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    ax = axes[0]
    ax.plot(displacements, spin_levels[:,0]*1000, 'b-', label='Spin ↓')
    ax.plot(displacements, spin_levels[:,1]*1000, 'r-', label='Spin ↑')
    ax.set_xlabel('Displacement along [111] (Å)')
    ax.set_ylabel('Spin Energy (meV)')
    ax.set_title('Strain-Modified Spin Levels')
    ax.legend()
    ax.grid(alpha=0.3)
    
    ax = axes[1]
    ax.plot(displacements, strain_energy, 'g-', label='Strain Energy')
    ax.set_xlabel('Displacement along [111] (Å)')
    ax.set_ylabel('Strain Energy (eV)')
    ax.set_title('Keating Strain Potential')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Total energy for both spin states
    ax = axes[2]
    E_total_down = strain_energy + spin_levels[:,0]
    E_total_up = strain_energy + spin_levels[:,1]
    ax.plot(displacements, E_total_down, 'b-', label='Total (Spin ↓)')
    ax.plot(displacements, E_total_up, 'r-', label='Total (Spin ↑)')
    ax.set_xlabel('Displacement along [111] (Å)')
    ax.set_ylabel('Total Energy (eV)')
    ax.set_title('Combined Strain-Spin Landscape')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('spin_strain_landscape.png', dpi=150)
    plt.show()
    
    # 2. Find equilibrium for each spin state and compute barrier
    print("\n2. Equilibrium analysis:")
    B0 = np.array([0.0, 0.0, 0.1])  # 0.1 T
    result = node.spin_flip_energy_barrier(B_field=B0)
    
    print(f"Spin down equilibrium:")
    print(f"  Displacement: {result['disp_down']} Å")
    print(f"  Energy: {result['E_down']:.4f} eV")
    print(f"Spin up equilibrium:")
    print(f"  Displacement: {result['disp_up']} Å")
    print(f"  Energy: {result['E_up']:.4f} eV")
    print(f"Crossing point:")
    print(f"  Displacement: {result['disp_cross']} Å")
    print(f"  Energy: {result['E_cross']:.4f} eV")
    print(f"  Minimum gap: {result['min_gap']*1000:.2f} meV")
    print(f"Barrier height: {result['barrier']*1000:.2f} meV")
    
    # 3. Show how magnetic field shifts the equilibrium
    print("\n3. Magnetic field effect:")
    B_fields = np.linspace(0.0, 0.5, 20)
    barriers = []
    gaps = []
    for Bz in B_fields:
        B = np.array([0,0,Bz])
        res = node.spin_flip_energy_barrier(B_field=B)
        barriers.append(res['barrier']*1000)  # meV
        gaps.append(res['min_gap']*1000)
    
    plt.figure(figsize=(10,4))
    plt.subplot(1,2,1)
    plt.plot(B_fields, barriers, 'o-')
    plt.xlabel('Magnetic Field (T)')
    plt.ylabel('Spin Flip Barrier (meV)')
    plt.title('Magnetic Control of Strain Barrier')
    plt.grid(alpha=0.3)
    
    plt.subplot(1,2,2)
    plt.plot(B_fields, gaps, 's-')
    plt.xlabel('Magnetic Field (T)')
    plt.ylabel('Minimum Gap (meV)')
    plt.title('Avoided Crossing Gap')
    plt.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('magnetic_control.png', dpi=150)
    plt.show()
    
    return node

# ============================================================
# 5. TWO-NODE SPIN-STRAIN COUPLING (Magnetic Bridge)
# ============================================================
class CoupledSpinStrainNodes:
    """
    Two octahedral nodes with spin, coupled via strain (phonon) and magnetic dipole.
    Demonstrates multi-bridge interaction.
    """
    def __init__(self, k_strain_coupling=2.0, J_dipole=0.01):
        self.node1 = SpinStrainNode()
        self.node2 = SpinStrainNode()
        self.k_c = k_strain_coupling  # strain-strain coupling (eV/Å²)
        self.J = J_dipole  # magnetic dipole coupling (meV)
        
    def total_energy(self, disp1, disp2, spin1, spin2, B_field=None):
        E1 = self.node1.total_energy(disp1, spin1, B_field)
        E2 = self.node2.total_energy(disp2, spin2, B_field)
        
        # Strain coupling (harmonic)
        diff = disp1 - disp2
        E_strain_couple = 0.5 * self.k_c * np.dot(diff, diff)
        
        # Magnetic dipole coupling (simplified as Ising)
        # J > 0 for antiferromagnetic, J < 0 for ferromagnetic
        # spin state: 0 = ↓, 1 = ↑ -> map to -1, +1
        s1 = 2*spin1 - 1
        s2 = 2*spin2 - 1
        E_mag = self.J * s1 * s2 * 0.001  # convert meV to eV
        
        return E1 + E2 + E_strain_couple + E_mag
    
    def find_ground_state(self, B_field=None):
        """Find the lowest energy configuration of both nodes."""
        best_energy = np.inf
        best_config = None
        
        # Search over spin states (4 combos) and optimize displacements for each
        for s1 in [0,1]:
            for s2 in [0,1]:
                def objective(x):
                    d1 = x[:3]
                    d2 = x[3:]
                    return self.total_energy(d1, d2, s1, s2, B_field)
                
                res = minimize(objective, x0=np.zeros(6), method='L-BFGS-B',
                              bounds=[(-0.8,0.8)]*6)
                energy = res.fun
                if energy < best_energy:
                    best_energy = energy
                    best_config = (res.x[:3], res.x[3:], s1, s2, energy)
        
        return best_config

def simulate_two_node_spin_strain():
    print("\n" + "="*60)
    print("🔗🔗 COUPLED SPIN-STRAIN NODES (Two Bridges)")
    print("="*60)
    
    system = CoupledSpinStrainNodes(k_strain_coupling=2.0, J_dipole=0.05)
    
    # Find ground state at zero field
    B0 = np.array([0.0, 0.0, 0.1])
    gs = system.find_ground_state(B_field=B0)
    print(f"\nGround state at B = 0.1 T:")
    print(f"  Node1: spin={'↑' if gs[2] else '↓'}, disp={np.round(gs[0],3)}")
    print(f"  Node2: spin={'↑' if gs[3] else '↓'}, disp={np.round(gs[1],3)}")
    print(f"  Total Energy: {gs[4]:.4f} eV")
    
    # Show how magnetic coupling affects strain configuration
    J_values = np.linspace(-0.1, 0.1, 20)
    spin_correlations = []
    for J in J_values:
        system.J = J * 0.001  # meV to eV
        gs = system.find_ground_state(B_field=B0)
        # Spin correlation: +1 if aligned, -1 if anti-aligned
        corr = (2*gs[2]-1) * (2*gs[3]-1)
        spin_correlations.append(corr)
    
    plt.figure(figsize=(8,5))
    plt.plot(J_values, spin_correlations, 'o-')
    plt.axhline(0, color='k', linestyle='--')
    plt.xlabel('Magnetic Coupling J (meV)')
    plt.ylabel('Spin Correlation (+1 aligned, -1 anti)')
    plt.title('Strain-Mediated Magnetic Order')
    plt.grid(alpha=0.3)
    plt.savefig('strain_magnetic_order.png', dpi=150)
    plt.show()

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    # Single node spin-strain coupling
    node = simulate_spin_strain_coupling()
    
    # Two-node multi-bridge interaction
    simulate_two_node_spin_strain()
    
    print("\n✅ Multi-bridge simulation complete.")
    print("Next bridges to add: Optical (1.54 μm excitation) and Electric (Stark shift).")
