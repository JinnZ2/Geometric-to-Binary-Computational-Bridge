# #!/usr/bin/env python3
“””
DFT Framework for Erbium in Strained Silicon

This module generates input files and analyzes output for DFT calculations
aimed at finding the optimal strain (ε*) for self-assembly of Er dopants
into octahedral interstitial sites in silicon.

Target: Maximize ΔE_barrier = E_f(Er, T) - E_f(Er, O)
“””

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Tuple, Dict
import json

# Physical constants

K_B = 8.617333e-5  # eV/K (Boltzmann constant)
HBAR = 6.582119e-16  # eV·s (reduced Planck constant)
SI_LATTICE_CONST = 5.431  # Å (silicon lattice constant at 300K)
M_ER = 167.259  # amu (erbium atomic mass)
AMU_TO_EV = 931.494e6 / (299792458**2 * 1e20)  # Conversion factor for mass

@dataclass
class DFTConfig:
“”“Configuration for DFT calculations”””
# Supercell parameters
supercell_size: Tuple[int, int, int] = (3, 3, 3)  # Multiple of conventional unit cells

```
# Strain scan parameters
strain_min: float = 0.0  # Minimum biaxial strain (%)
strain_max: float = 2.5  # Maximum biaxial strain (%)
strain_increment: float = 0.5  # Strain step size (%)

# DFT parameters
functional: str = "GGA+U"  # Exchange-correlation functional
hubbard_u_er: float = 6.0  # eV (Hubbard U for Er 4f electrons)
energy_cutoff: float = 500.0  # eV (plane-wave cutoff)
k_point_grid: Tuple[int, int, int] = (3, 3, 3)  # k-point mesh

# Convergence criteria
force_convergence: float = 0.01  # eV/Å
energy_convergence: float = 1e-6  # eV

# Temperature for analysis
temperature: float = 300.0  # K

# Target coherence time
target_T2: float = 0.1  # seconds (100 ms)
```

@dataclass
class FormationEnergyResult:
“”“Results from formation energy calculation”””
strain: float  # Applied biaxial strain (%)
site_type: str  # ‘O’ (octahedral) or ‘T’ (tetrahedral)
formation_energy: float  # eV
relaxed_position: np.ndarray  # Final atomic position (fractional coordinates)
displacement: float  # Displacement from ideal site (Å)
total_energy: float  # Total system energy (eV)
force_max: float  # Maximum residual force (eV/Å)

class ErDFTAnalyzer:
“”“Analyzer for Er dopant DFT calculations in strained Si”””

```
def __init__(self, config: DFTConfig):
    self.config = config
    self.results_O: List[FormationEnergyResult] = []
    self.results_T: List[FormationEnergyResult] = []
    
def calculate_lattice_constant(self, strain: float) -> float:
    """
    Calculate strained lattice constant
    
    Args:
        strain: Biaxial strain in percent
        
    Returns:
        Strained lattice constant in Å
    """
    return SI_LATTICE_CONST * (1 + strain / 100.0)

def get_octahedral_position(self) -> np.ndarray:
    """Get ideal octahedral interstitial position (fractional coordinates)"""
    return np.array([0.5, 0.5, 0.5])

def get_tetrahedral_position(self) -> np.ndarray:
    """Get ideal tetrahedral interstitial position (fractional coordinates)"""
    return np.array([0.75, 0.75, 0.75])

def generate_supercell_positions(self, strain: float, site_type: str = 'O') -> np.ndarray:
    """
    Generate atomic positions for supercell with Er dopant
    
    Args:
        strain: Applied biaxial strain (%)
        site_type: 'O' for octahedral, 'T' for tetrahedral
        
    Returns:
        Array of atomic positions (Cartesian coordinates in Å)
    """
    a = self.calculate_lattice_constant(strain)
    nx, ny, nz = self.config.supercell_size
    
    # Generate Si atoms in diamond cubic structure
    positions = []
    
    # Basis atoms in conventional cubic cell (8 atoms)
    basis = np.array([
        [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.0],
        [0.5, 0.0, 0.5],
        [0.0, 0.5, 0.5],
        [0.25, 0.25, 0.25],
        [0.75, 0.75, 0.25],
        [0.75, 0.25, 0.75],
        [0.25, 0.75, 0.75]
    ])
    
    # Replicate supercell
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                offset = np.array([i, j, k])
                for atom in basis:
                    pos = (atom + offset) / np.array([nx, ny, nz])
                    positions.append(pos)
    
    positions = np.array(positions)
    
    # Add Er dopant at appropriate interstitial site
    if site_type == 'O':
        er_pos = self.get_octahedral_position()
    else:
        er_pos = self.get_tetrahedral_position()
    
    # Convert to Cartesian coordinates
    lattice_vectors = np.array([
        [a * nx, 0, 0],
        [0, a * ny, 0],
        [0, 0, a * nz]
    ])
    
    positions_cart = positions @ lattice_vectors
    er_pos_cart = er_pos @ lattice_vectors
    
    return positions_cart, er_pos_cart, lattice_vectors

def generate_vasp_input(self, strain: float, site_type: str, output_dir: str):
    """
    Generate VASP input files (POSCAR, INCAR, KPOINTS, POTCAR info)
    
    Args:
        strain: Applied biaxial strain (%)
        site_type: 'O' or 'T'
        output_dir: Directory to write input files
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    si_positions, er_position, lattice = self.generate_supercell_positions(strain, site_type)
    
    # Write POSCAR
    poscar_file = os.path.join(output_dir, 'POSCAR')
    with open(poscar_file, 'w') as f:
        f.write(f"Er in Si, strain={strain:.2f}%, site={site_type}\n")
        f.write("1.0\n")
        for vec in lattice:
            f.write(f"  {vec[0]:16.10f} {vec[1]:16.10f} {vec[2]:16.10f}\n")
        f.write("Si Er\n")
        f.write(f"{len(si_positions)} 1\n")
        f.write("Cartesian\n")
        for pos in si_positions:
            f.write(f"  {pos[0]:16.10f} {pos[1]:16.10f} {pos[2]:16.10f}\n")
        f.write(f"  {er_position[0]:16.10f} {er_position[1]:16.10f} {er_position[2]:16.10f}\n")
    
    # Write INCAR
    incar_file = os.path.join(output_dir, 'INCAR')
    with open(incar_file, 'w') as f:
        f.write("# DFT+U calculation for Er in strained Si\n")
        f.write(f"SYSTEM = Er_Si_strain_{strain:.2f}_site_{site_type}\n\n")
        f.write("# Electronic structure\n")
        f.write(f"ENCUT = {self.config.energy_cutoff}\n")
        f.write("PREC = Accurate\n")
        f.write("LREAL = Auto\n")
        f.write("ALGO = Normal\n\n")
        f.write("# Exchange-correlation\n")
        f.write("GGA = PE  # PBE functional\n")
        f.write("LDAU = .TRUE.\n")
        f.write("LDAUTYPE = 2  # Dudarev approach\n")
        f.write("LDAUL = -1 3  # s,p,d for Si; f for Er\n")
        f.write(f"LDAUU = 0 {self.config.hubbard_u_er}  # U for Si, Er\n")
        f.write("LDAUJ = 0 0\n\n")
        f.write("# Ionic relaxation\n")
        f.write("IBRION = 2  # CG algorithm\n")
        f.write("NSW = 200  # Maximum ionic steps\n")
        f.write(f"EDIFFG = -{self.config.force_convergence}\n")
        f.write("ISIF = 2  # Relax ions, fix cell\n\n")
        f.write("# Electronic convergence\n")
        f.write(f"EDIFF = {self.config.energy_convergence}\n")
        f.write("NELM = 200\n\n")
        f.write("# Output\n")
        f.write("LWAVE = .FALSE.\n")
        f.write("LCHARG = .FALSE.\n")
        f.write("LORBIT = 11  # Write DOS\n")
    
    # Write KPOINTS
    kpoints_file = os.path.join(output_dir, 'KPOINTS')
    with open(kpoints_file, 'w') as f:
        f.write("Automatic mesh\n")
        f.write("0\n")
        f.write("Gamma\n")
        kx, ky, kz = self.config.k_point_grid
        f.write(f"{kx} {ky} {kz}\n")
        f.write("0 0 0\n")
    
    # Write POTCAR instructions
    potcar_info = os.path.join(output_dir, 'POTCAR_INFO.txt')
    with open(potcar_info, 'w') as f:
        f.write("POTCAR construction instructions:\n")
        f.write("================================\n\n")
        f.write("Concatenate the following PAW pseudopotentials:\n")
        f.write("1. Si: POTCAR.Si_GW or POTCAR.Si (PAW_PBE)\n")
        f.write("2. Er: POTCAR.Er_3 (PAW_PBE, valence: 4f^12 5s^2 5p^6 6s^2)\n")
        f.write("\nExample command:\n")
        f.write("cat ~/POTCAR_database/Si/POTCAR ~/POTCAR_database/Er_3/POTCAR > POTCAR\n")
        f.write("\nNote: Ensure the Er POTCAR treats 4f electrons as valence!\n")
    
    print(f"✓ Generated VASP input files in {output_dir}")
    print(f"  Strain: {strain:.2f}%, Site: {site_type}")
    print(f"  Supercell: {self.config.supercell_size}")
    print(f"  Total atoms: {len(si_positions) + 1} (Si: {len(si_positions)}, Er: 1)")

def add_result(self, result: FormationEnergyResult):
    """Add a formation energy result to the database"""
    if result.site_type == 'O':
        self.results_O.append(result)
    else:
        self.results_T.append(result)

def calculate_energy_barrier(self) -> Tuple[float, float]:
    """
    Find optimal strain (ε*) that maximizes ΔE_barrier
    
    Returns:
        (optimal_strain, max_barrier) in (%, eV)
    """
    if not self.results_O or not self.results_T:
        raise ValueError("Need results for both O and T sites")
    
    # Create interpolated functions
    strains_O = np.array([r.strain for r in self.results_O])
    energies_O = np.array([r.formation_energy for r in self.results_O])
    
    strains_T = np.array([r.strain for r in self.results_T])
    energies_T = np.array([r.formation_energy for r in self.results_T])
    
    # Find common strain range
    common_strains = np.intersect1d(strains_O, strains_T)
    
    max_barrier = -np.inf
    optimal_strain = 0.0
    
    for strain in common_strains:
        E_O = energies_O[strains_O == strain][0]
        E_T = energies_T[strains_T == strain][0]
        barrier = E_T - E_O
        
        if barrier > max_barrier:
            max_barrier = barrier
            optimal_strain = strain
    
    return optimal_strain, max_barrier

def calculate_thermal_displacement(self, k_well: float, temperature: float) -> float:
    """
    Calculate RMS thermal displacement using equipartition theorem
    
    Args:
        k_well: Well stiffness (eV/Å²)
        temperature: Temperature (K)
        
    Returns:
        σ_T: RMS thermal displacement (Å)
    """
    # Convert k_well from eV/Å² to proper units
    # σ_T = sqrt(k_B * T / k_well)
    sigma_T = np.sqrt(K_B * temperature / k_well)
    return sigma_T

def plot_formation_energies(self, save_path: str = None):
    """Plot formation energies vs strain for O and T sites"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left plot: Formation energies
    if self.results_O:
        strains_O = [r.strain for r in self.results_O]
        energies_O = [r.formation_energy for r in self.results_O]
        ax1.plot(strains_O, energies_O, 'o-', label='Octahedral (O)', 
                color='#2E86AB', linewidth=2, markersize=8)
    
    if self.results_T:
        strains_T = [r.strain for r in self.results_T]
        energies_T = [r.formation_energy for r in self.results_T]
        ax1.plot(strains_T, energies_T, 's-', label='Tetrahedral (T)', 
                color='#A23B72', linewidth=2, markersize=8)
    
    ax1.set_xlabel('Biaxial Strain ε (%)', fontsize=12)
    ax1.set_ylabel('Formation Energy $E_f$ (eV)', fontsize=12)
    ax1.set_title('Er Formation Energy vs Strain', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # Right plot: Energy barrier
    if self.results_O and self.results_T:
        strains = np.array([r.strain for r in self.results_O])
        barriers = []
        for strain in strains:
            E_O = [r.formation_energy for r in self.results_O if r.strain == strain]
            E_T = [r.formation_energy for r in self.results_T if r.strain == strain]
            if E_O and E_T:
                barriers.append(E_T[0] - E_O[0])
            else:
                barriers.append(np.nan)
        
        ax2.plot(strains, barriers, 'o-', color='#F18F01', 
                linewidth=2, markersize=8)
        ax2.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        
        # Mark optimal strain
        if np.any(~np.isnan(barriers)):
            optimal_idx = np.nanargmax(barriers)
            ax2.plot(strains[optimal_idx], barriers[optimal_idx], '*', 
                    color='red', markersize=20, label=f'ε* = {strains[optimal_idx]:.2f}%')
            
            # Add thermal energy reference
            k_B_T = K_B * self.config.temperature
            ax2.axhline(y=k_B_T, color='r', linestyle=':', alpha=0.7, 
                       label=f'$k_B T$ @ {self.config.temperature:.0f}K')
    
    ax2.set_xlabel('Biaxial Strain ε (%)', fontsize=12)
    ax2.set_ylabel('Energy Barrier $ΔE_{barrier}$ (eV)', fontsize=12)
    ax2.set_title('Self-Assembly Selectivity', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved plot to {save_path}")
    else:
        plt.show()

def export_results(self, filepath: str):
    """Export results to JSON file"""
    data = {
        'config': {
            'supercell_size': self.config.supercell_size,
            'strain_range': (self.config.strain_min, self.config.strain_max),
            'functional': self.config.functional,
            'hubbard_u': self.config.hubbard_u_er,
            'temperature': self.config.temperature
        },
        'results_O': [
            {
                'strain': r.strain,
                'formation_energy': r.formation_energy,
                'displacement': r.displacement,
                'position': r.relaxed_position.tolist()
            }
            for r in self.results_O
        ],
        'results_T': [
            {
                'strain': r.strain,
                'formation_energy': r.formation_energy,
                'displacement': r.displacement,
                'position': r.relaxed_position.tolist()
            }
            for r in self.results_T
        ]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Exported results to {filepath}")
```

def generate_strain_scan_inputs(config: DFTConfig, base_dir: str = “./dft_inputs”):
“””
Generate all DFT input files for strain scan

```
Args:
    config: DFT configuration
    base_dir: Base directory for outputs
"""
analyzer = ErDFTAnalyzer(config)

strains = np.arange(
    config.strain_min,
    config.strain_max + config.strain_increment/2,
    config.strain_increment
)

print(f"\n{'='*60}")
print("GENERATING DFT INPUT FILES FOR STRAIN SCAN")
print(f"{'='*60}\n")
print(f"Strain range: {config.strain_min}% to {config.strain_max}%")
print(f"Increment: {config.strain_increment}%")
print(f"Total calculations: {len(strains) * 2} ({len(strains)} strains × 2 sites)\n")

for strain in strains:
    # Octahedral site
    output_dir_O = f"{base_dir}/strain_{strain:.2f}_site_O"
    analyzer.generate_vasp_input(strain, 'O', output_dir_O)
    
    # Tetrahedral site
    output_dir_T = f"{base_dir}/strain_{strain:.2f}_site_T"
    analyzer.generate_vasp_input(strain, 'T', output_dir_T)
    print()

print(f"{'='*60}")
print(f"✓ Generated {len(strains) * 2} input directories in {base_dir}/")
print(f"{'='*60}\n")

return analyzer
```

if **name** == “**main**”:
# Example usage
config = DFTConfig(
supercell_size=(3, 3, 3),
strain_min=0.0,
strain_max=2.5,
strain_increment=0.5,
hubbard_u_er=6.0,
energy_cutoff=500.0,
k_point_grid=(3, 3, 3),
temperature=300.0,
target_T2=0.1
)

```
print("\n🔬 Er in Strained Si - DFT Framework")
print("=" * 60)
print(f"Target: Find ε* that maximizes ΔE_barrier")
print(f"Goal: Enable T₂ ≥ {config.target_T2*1000:.0f} ms at {config.temperature:.0f} K")
print("=" * 60)

analyzer = generate_strain_scan_inputs(config)
```
