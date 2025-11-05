# #!/usr/bin/env python3
“””
Er-P Co-Doping Analysis Framework

This module handles the DFT analysis of Er-P complexes to find the optimal
dopant separation distance (d*) that maximizes binding energy and stabilizes
the Er³⁺ charge state.

Target: Maximize E_b = E_Er + E_P - E_complex
“””

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json
from er_dft_framework import DFTConfig, ErDFTAnalyzer

# Physical constants

K_B = 8.617333e-5  # eV/K
SI_LATTICE_CONST = 5.431  # Å

@dataclass
class CoDopingConfig:
“”“Configuration for Er-P co-doping calculations”””
# Optimal strain from single-dopant analysis
optimal_strain: float = 1.5  # % (to be determined from Er-only DFT)

```
# Distance scan parameters
distance_min: float = 3.0  # Å (nearest neighbor Si distance)
distance_max: float = 10.0  # Å
distance_increment: float = 1.0  # Å

# P dopant positioning
p_site_type: str = "substitutional"  # P replaces Si atom

# DFT parameters (inherit from base config)
base_dft_config: Optional[DFTConfig] = None

# Analysis parameters
temperature: float = 300.0  # K
target_binding_energy: float = 0.5  # eV (minimum for stable complex at 300K)
```

@dataclass
class CoDopingResult:
“”“Results from Er-P co-doping calculation”””
distance: float  # Er-P separation (Å)
binding_energy: float  # eV
er_position: np.ndarray  # Er relaxed position (Cartesian, Å)
p_position: np.ndarray  # P position (Cartesian, Å)
er_displacement: float  # Displacement from ideal O site (Å)
total_energy: float  # Total system energy (eV)
er_charge_state: float  # Bader charge on Er
efg_tensor: np.ndarray  # Electric field gradient at Er site (V/Å²)
force_constants: np.ndarray  # 3x3 Hessian matrix at Er site (eV/Å²)

class ErPCoDopingAnalyzer:
“”“Analyzer for Er-P co-doping in strained Si”””

```
def __init__(self, config: CoDopingConfig):
    self.config = config
    self.results: List[CoDopingResult] = []
    self.reference_energies = {
        'E_Er_isolated': None,  # Energy of Er-only system
        'E_P_isolated': None,   # Energy of P-only system
        'E_host': None          # Energy of pure Si supercell
    }

def set_reference_energies(self, E_Er: float, E_P: float, E_host: float):
    """
    Set reference energies for binding energy calculation
    
    Args:
        E_Er: Total energy of supercell with only Er dopant (eV)
        E_P: Total energy of supercell with only P dopant (eV)
        E_host: Total energy of pure Si supercell (eV)
    """
    self.reference_energies['E_Er_isolated'] = E_Er
    self.reference_energies['E_P_isolated'] = E_P
    self.reference_energies['E_host'] = E_host
    print(f"✓ Set reference energies:")
    print(f"  E(Er-only) = {E_Er:.6f} eV")
    print(f"  E(P-only)  = {E_P:.6f} eV")
    print(f"  E(host)    = {E_host:.6f} eV")

def calculate_binding_energy(self, E_complex: float) -> float:
    """
    Calculate binding energy of Er-P complex
    
    E_b = E(Er-isolated) + E(P-isolated) - E(Er-P complex)
    
    Positive E_b indicates attractive interaction (stable complex)
    
    Args:
        E_complex: Total energy of supercell with Er-P complex (eV)
        
    Returns:
        Binding energy (eV)
    """
    if None in self.reference_energies.values():
        raise ValueError("Must set reference energies first")
    
    E_b = (self.reference_energies['E_Er_isolated'] + 
           self.reference_energies['E_P_isolated'] - 
           E_complex)
    
    return E_b

def get_p_substitutional_sites(self, distance_range: Tuple[float, float]) -> List[np.ndarray]:
    """
    Generate list of P substitutional site positions around Er at O site
    
    Args:
        distance_range: (min_dist, max_dist) in Å
        
    Returns:
        List of P positions (fractional coordinates)
    """
    # In diamond cubic Si, nearest neighbor shells around octahedral site
    a = SI_LATTICE_CONST * (1 + self.config.optimal_strain / 100.0)
    
    # Er at octahedral site: (0.5, 0.5, 0.5) in fractional coords
    er_frac = np.array([0.5, 0.5, 0.5])
    
    # Substitutional Si sites - generate neighbors
    sites = []
    
    # First shell: nearest Si atoms to octahedral site (6 atoms)
    # Distance ≈ a/2 ≈ 2.7 Å
    first_shell = [
        np.array([0.25, 0.25, 0.25]),
        np.array([0.75, 0.25, 0.25]),
        np.array([0.25, 0.75, 0.25]),
        np.array([0.25, 0.25, 0.75]),
        np.array([0.75, 0.75, 0.25]),
        np.array([0.75, 0.25, 0.75]),
        np.array([0.25, 0.75, 0.75]),
        np.array([0.75, 0.75, 0.75])
    ]
    
    # Calculate distances and filter
    for site in first_shell:
        # Convert to Cartesian
        site_cart = site * a
        er_cart = er_frac * a
        dist = np.linalg.norm(site_cart - er_cart)
        
        if distance_range[0] <= dist <= distance_range[1]:
            sites.append((site, dist))
    
    # Second shell: next-nearest neighbors
    # Distance ≈ a√3/4 ≈ 4.7 Å
    # Add more sites as needed...
    
    return sorted(sites, key=lambda x: x[1])

def generate_vasp_input_codoping(self, distance: float, output_dir: str):
    """
    Generate VASP input for Er-P co-doping at specified distance
    
    Args:
        distance: Target Er-P separation (Å)
        output_dir: Output directory for input files
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    a = SI_LATTICE_CONST * (1 + self.config.optimal_strain / 100.0)
    
    # Get P site closest to target distance
    sites = self.get_p_substitutional_sites((distance - 0.5, distance + 0.5))
    if not sites:
        print(f"⚠ No suitable P site found for distance {distance:.2f} Å")
        return
    
    p_site_frac, actual_dist = sites[0]
    print(f"  Using P site at distance {actual_dist:.3f} Å (target: {distance:.2f} Å)")
    
    # Generate supercell
    if self.config.base_dft_config:
        nx, ny, nz = self.config.base_dft_config.supercell_size
    else:
        nx, ny, nz = 3, 3, 3
    
    # Create lattice vectors
    lattice = np.array([
        [a * nx, 0, 0],
        [0, a * ny, 0],
        [0, 0, a * nz]
    ])
    
    # Generate Si atoms (simplified - should match er_dft_framework logic)
    # For now, placeholder
    n_si_atoms = 8 * nx * ny * nz - 1  # Minus one replaced by P
    
    # Er position (octahedral interstitial)
    er_pos_frac = np.array([0.5, 0.5, 0.5])
    er_pos_cart = er_pos_frac @ lattice
    
    # P position (substitutional)
    p_pos_cart = p_site_frac @ lattice
    
    # Write POSCAR
    poscar_file = os.path.join(output_dir, 'POSCAR')
    with open(poscar_file, 'w') as f:
        f.write(f"Er-P complex in Si, d={actual_dist:.3f} Å, ε={self.config.optimal_strain:.2f}%\n")
        f.write("1.0\n")
        for vec in lattice:
            f.write(f"  {vec[0]:16.10f} {vec[1]:16.10f} {vec[2]:16.10f}\n")
        f.write("Si P Er\n")
        f.write(f"{n_si_atoms} 1 1\n")
        f.write("Cartesian\n")
        f.write("# Si atoms (placeholder - generate full list)\n")
        f.write(f"# ... {n_si_atoms} Si positions ...\n")
        f.write(f"# P atom\n")
        f.write(f"  {p_pos_cart[0]:16.10f} {p_pos_cart[1]:16.10f} {p_pos_cart[2]:16.10f}\n")
        f.write(f"# Er atom\n")
        f.write(f"  {er_pos_cart[0]:16.10f} {er_pos_cart[1]:16.10f} {er_pos_cart[2]:16.10f}\n")
    
    # Write INCAR (similar to single-dopant but with Bader analysis)
    incar_file = os.path.join(output_dir, 'INCAR')
    with open(incar_file, 'w') as f:
        f.write("# DFT+U calculation for Er-P co-doping in strained Si\n")
        f.write(f"SYSTEM = ErP_Si_d_{actual_dist:.2f}_strain_{self.config.optimal_strain:.2f}\n\n")
        
        if self.config.base_dft_config:
            f.write(f"ENCUT = {self.config.base_dft_config.energy_cutoff}\n")
        else:
            f.write("ENCUT = 500.0\n")
        
        f.write("PREC = Accurate\n")
        f.write("LREAL = Auto\n")
        f.write("ALGO = Normal\n\n")
        f.write("# DFT+U for Er\n")
        f.write("GGA = PE\n")
        f.write("LDAU = .TRUE.\n")
        f.write("LDAUTYPE = 2\n")
        f.write("LDAUL = -1 -1 3  # Si, P, Er(f-orbital)\n")
        
        if self.config.base_dft_config:
            f.write(f"LDAUU = 0 0 {self.config.base_dft_config.hubbard_u_er}\n")
        else:
            f.write("LDAUU = 0 0 6.0\n")
        
        f.write("LDAUJ = 0 0 0\n\n")
        f.write("# Ionic relaxation\n")
        f.write("IBRION = 2\n")
        f.write("NSW = 200\n")
        
        if self.config.base_dft_config:
            f.write(f"EDIFFG = -{self.config.base_dft_config.force_convergence}\n")
        else:
            f.write("EDIFFG = -0.01\n")
        
        f.write("ISIF = 2\n\n")
        f.write("# Bader charge analysis\n")
        f.write("LAECHG = .TRUE.  # Write core charge density\n")
        f.write("LCHARG = .TRUE.  # Write CHGCAR for Bader\n\n")
        f.write("# Electric field gradient calculation\n")
        f.write("LEFG = .TRUE.  # Calculate EFG tensor\n")
        f.write("QUAD_EFG = 0.0 0.0 1.0  # Specify Er atom for EFG\n\n")
        f.write("# Output\n")
        f.write("LWAVE = .FALSE.\n")
        f.write("LORBIT = 11\n")
    
    # Write instructions for post-processing
    readme_file = os.path.join(output_dir, 'README_ANALYSIS.txt')
    with open(readme_file, 'w') as f:
        f.write("Er-P Co-Doping Analysis Pipeline\n")
        f.write("=================================\n\n")
        f.write("1. Run VASP calculation:\n")
        f.write("   mpirun -np 16 vasp_std > vasp.out\n\n")
        f.write("2. Extract binding energy:\n")
        f.write("   E_complex = (final energy from OSZICAR)\n")
        f.write("   E_b = E(Er-only) + E(P-only) - E_complex\n\n")
        f.write("3. Bader charge analysis:\n")
        f.write("   bader CHGCAR -ref CHGCAR_sum\n")
        f.write("   # Extract charge on Er atom from ACF.dat\n\n")
        f.write("4. EFG tensor extraction:\n")
        f.write("   grep 'Electric field gradient' OUTCAR\n")
        f.write("   # Extract 3x3 tensor at Er site\n\n")
        f.write("5. Force constants (Hessian) calculation:\n")
        f.write("   # Requires finite difference: displace Er ±0.01 Å in x,y,z\n")
        f.write("   # Calculate forces, construct Hessian matrix\n")
    
    print(f"✓ Generated co-doping input in {output_dir}")

def add_result(self, result: CoDopingResult):
    """Add a co-doping result"""
    self.results.append(result)

def find_optimal_distance(self) -> Tuple[float, float]:
    """
    Find optimal Er-P distance (d*) that maximizes binding energy
    
    Returns:
        (d*, E_b_max) in (Å, eV)
    """
    if not self.results:
        raise ValueError("No results available")
    
    distances = np.array([r.distance for r in self.results])
    binding_energies = np.array([r.binding_energy for r in self.results])
    
    max_idx = np.argmax(binding_energies)
    return distances[max_idx], binding_energies[max_idx]

def calculate_well_stiffness(self, result: CoDopingResult) -> Tuple[np.ndarray, float]:
    """
    Calculate well stiffness from force constants
    
    Args:
        result: CoDopingResult containing force_constants matrix
        
    Returns:
        (eigenvalues, average_stiffness) in (eV/Å², eV/Å²)
    """
    k_well = result.force_constants
    eigenvalues = np.linalg.eigvalsh(k_well)
    avg_stiffness = np.mean(eigenvalues)
    return eigenvalues, avg_stiffness

def calculate_thermal_displacement(self, k_well_avg: float) -> float:
    """
    Calculate RMS thermal displacement at operating temperature
    
    Args:
        k_well_avg: Average well stiffness (eV/Å²)
        
    Returns:
        σ_T: RMS thermal displacement (Å)
    """
    sigma_T = np.sqrt(K_B * self.config.temperature / k_well_avg)
    return sigma_T

def plot_binding_energy_curve(self, save_path: str = None):
    """Plot binding energy vs Er-P distance"""
    if not self.results:
        print("⚠ No results to plot")
        return
    
    distances = np.array([r.distance for r in self.results])
    binding_energies = np.array([r.binding_energy for r in self.results])
    displacements = np.array([r.er_displacement for r in self.results])
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left: Binding energy
    ax1.plot(distances, binding_energies, 'o-', color='#2E86AB', 
            linewidth=2, markersize=10)
    
    # Mark optimal distance
    d_star, E_b_max = self.find_optimal_distance()
    ax1.plot(d_star, E_b_max, '*', color='red', markersize=20, 
            label=f'd* = {d_star:.2f} Å, $E_b$ = {E_b_max:.3f} eV')
    
    # Add thermal stability threshold
    k_B_T = K_B * self.config.temperature
    ax1.axhline(y=k_B_T, color='orange', linestyle='--', alpha=0.7,
               label=f'$k_B T$ @ {self.config.temperature:.0f}K')
    ax1.axhline(y=0, color='k', linestyle=':', alpha=0.5)
    
    ax1.set_xlabel('Er-P Distance (Å)', fontsize=12)
    ax1.set_ylabel('Binding Energy $E_b$ (eV)', fontsize=12)
    ax1.set_title('Er-P Complex Stability', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Right: Er displacement from ideal O site
    ax2.plot(distances, displacements, 's-', color='#A23B72',
            linewidth=2, markersize=10)
    ax2.axhline(y=0.5, color='red', linestyle='--', alpha=0.7,
               label='Target precision (0.5 nm)')
    
    ax2.set_xlabel('Er-P Distance (Å)', fontsize=12)
    ax2.set_ylabel('Er Displacement $δr_{relax}$ (Å)', fontsize=12)
    ax2.set_title('Geometric Precision', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved plot to {save_path}")
    else:
        plt.show()

def plot_efg_analysis(self, save_path: str = None):
    """Plot EFG tensor analysis vs distance"""
    if not self.results:
        print("⚠ No results to plot")
        return
    
    distances = []
    efg_principal_values = []
    
    for r in self.results:
        distances.append(r.distance)
        eigenvals = np.linalg.eigvalsh(r.efg_tensor)
        efg_principal_values.append(eigenvals)
    
    distances = np.array(distances)
    efg_principal_values = np.array(efg_principal_values)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(distances, efg_principal_values[:, 0], 'o-', label='$V_{zz}$ (principal)', 
           color='#2E86AB', linewidth=2)
    ax.plot(distances, efg_principal_values[:, 1], 's-', label='$V_{yy}$', 
           color='#A23B72', linewidth=2)
    ax.plot(distances, efg_principal_values[:, 2], '^-', label='$V_{xx}$', 
           color='#F18F01', linewidth=2)
    
    ax.set_xlabel('Er-P Distance (Å)', fontsize=12)
    ax.set_ylabel('EFG Principal Values (V/Å²)', fontsize=12)
    ax.set_title('Electric Field Gradient at Er Site', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved EFG plot to {save_path}")
    else:
        plt.show()

def export_results(self, filepath: str):
    """Export co-doping results to JSON"""
    data = {
        'config': {
            'optimal_strain': self.config.optimal_strain,
            'distance_range': (self.config.distance_min, self.config.distance_max),
            'temperature': self.config.temperature
        },
        'reference_energies': self.reference_energies,
        'results': [
            {
                'distance': r.distance,
                'binding_energy': r.binding_energy,
                'er_displacement': r.er_displacement,
                'er_charge_state': r.er_charge_state,
                'efg_tensor': r.efg_tensor.tolist(),
                'force_constants': r.force_constants.tolist()
            }
            for r in self.results
        ]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Exported co-doping results to {filepath}")
```

def generate_codoping_scan_inputs(config: CoDopingConfig, base_dir: str = “./codoping_inputs”):
“”“Generate all DFT inputs for Er-P co-doping distance scan”””
analyzer = ErPCoDopingAnalyzer(config)

```
distances = np.arange(
    config.distance_min,
    config.distance_max + config.distance_increment/2,
    config.distance_increment
)

print(f"\n{'='*60}")
print("GENERATING ER-P CO-DOPING DFT INPUT FILES")
print(f"{'='*60}\n")
print(f"Optimal strain: {config.optimal_strain:.2f}%")
print(f"Distance range: {config.distance_min:.1f} Å to {config.distance_max:.1f} Å")
print(f"Increment: {config.distance_increment:.1f} Å")
print(f"Total calculations: {len(distances)}\n")

for distance in distances:
    output_dir = f"{base_dir}/distance_{distance:.1f}A"
    analyzer.generate_vasp_input_codoping(distance, output_dir)
    print()

print(f"{'='*60}")
print(f"✓ Generated {len(distances)} co-doping input directories")
print(f"{'='*60}\n")

# Generate reference calculation instructions
ref_file = f"{base_dir}/REFERENCE_CALCULATIONS.txt"
with open(ref_file, 'w') as f:
    f.write("REFERENCE ENERGY CALCULATIONS\n")
    f.write("==============================\n\n")
    f.write("Before analyzing co-doping results, calculate:\n\n")
    f.write("1. E(Er-only): Er dopant at O site, no P\n")
    f.write("   - Use strain ε* from single-dopant optimization\n")
    f.write("   - Extract final energy from OSZICAR\n\n")
    f.write("2. E(P-only): P dopant substitutional, no Er\n")
    f.write("   - Same supercell size\n")
    f.write("   - Extract final energy from OSZICAR\n\n")
    f.write("3. E(host): Pure Si supercell\n")
    f.write("   - No dopants\n")
    f.write("   - Extract final energy from OSZICAR\n\n")
    f.write("Then use: analyzer.set_reference_energies(E_Er, E_P, E_host)\n")

print(f"✓ Written reference calculation instructions to {ref_file}\n")

return analyzer
```

if **name** == “**main**”:
# Example usage
config = CoDopingConfig(
optimal_strain=1.5,  # From single-dopant DFT
distance_min=3.0,
distance_max=10.0,
distance_increment=1.0,
temperature=300.0,
target_binding_energy=0.5
)

```
print("\n🧪 Er-P Co-Doping Analysis")
print("=" * 60)
print(f"Goal: Find d* that maximizes E_b")
print(f"Target: E_b > {config.target_binding_energy:.2f} eV for {config.temperature:.0f}K stability")
print("=" * 60)

analyzer = generate_codoping_scan_inputs(config)
```
