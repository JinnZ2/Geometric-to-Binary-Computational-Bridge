# #!/usr/bin/env python3
“””
QuTip Coherence Time Simulation Framework

This module uses QuTip to simulate the quantum dynamics of the Er³⁺ spin system
and predict T₂ coherence times at room temperature (300 K) based on DFT-derived
parameters.

Key inputs from DFT:

- Strain-optimized geometry (ε*)
- Co-doping configuration (d*)
- EFG tensor at Er site
- Force constants (k_well)

Output: Predicted T₂ coherence time
“””

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List, Optional
import json

try:
import qutip as qt
QUTIP_AVAILABLE = True
except ImportError:
QUTIP_AVAILABLE = False
qt = None  # Placeholder for type hints
print(“⚠ QuTip not installed. Install with: pip install qutip”)

# Physical constants

K_B = 8.617333e-5  # eV/K
HBAR = 6.582119e-16  # eV·s
HBAR_SI = 1.054571817e-34  # J·s
G_FACTOR_ER = 6.0  # Landé g-factor for Er³⁺ (approximate)
BOHR_MAGNETON = 5.7883818012e-5  # eV/T
M_ER_AMU = 167.259  # amu

@dataclass
class QuantumSystemConfig:
“”“Configuration for quantum system simulation”””
# Magnetic field
B_global: float = 1.0  # T (global field)
B_local: float = 0.05  # T (local micro-coil field)

```
# Temperature
temperature: float = 300.0  # K

# Er³⁺ spin properties
spin_quantum_number: float = 1.5  # J = 3/2 for Er³⁺ (ground state)
g_factor: float = G_FACTOR_ER

# DFT-derived parameters (to be set from analysis)
efg_tensor: Optional[np.ndarray] = None  # V/Å² (3x3 matrix)
force_constants: Optional[np.ndarray] = None  # eV/Å² (3x3 Hessian)
phonon_coupling_constant: float = 1e-3  # eV (estimated, to be refined)

# Isotopic purity
si29_fraction: float = 0.001  # 0.1% (highly enriched ²⁸Si)

# Simulation parameters
time_steps: int = 1000
max_time: float = 1.0  # seconds

# Target performance
target_T2: float = 0.1  # seconds (100 ms)
```

class ErQuantumSimulator:
“”“Quantum dynamics simulator for Er³⁺ in strained Si”””

```
def __init__(self, config: QuantumSystemConfig):
    self.config = config
    
    if not QUTIP_AVAILABLE:
        raise ImportError("QuTip is required for quantum simulations")
    
    # Calculate dimension of Hilbert space
    self.spin_j = config.spin_quantum_number
    self.dim = int(2 * self.spin_j + 1)  # 4 states for J=3/2
    
    print(f"✓ Initialized Er³⁺ quantum simulator")
    print(f"  Spin: J = {self.spin_j}")
    print(f"  Hilbert space dimension: {self.dim}")
    print(f"  Temperature: {config.temperature} K")

def construct_hamiltonian(self):
    """
    Construct total system Hamiltonian
    
    H = H_Zeeman + H_Stark + H_Hyperfine
    
    Returns:
        QuTip Hamiltonian operator
    """
    # Spin operators
    Jx = qt.jmat(self.spin_j, 'x')
    Jy = qt.jmat(self.spin_j, 'y')
    Jz = qt.jmat(self.spin_j, 'z')
    
    # 1. Zeeman term: -μ·B = -g μ_B J·B
    omega_z = (self.config.g_factor * BOHR_MAGNETON * 
               self.config.B_global / HBAR)  # rad/s
    H_zeeman = -omega_z * Jz
    
    # 2. Stark shift from EFG (quadrupole interaction)
    if self.config.efg_tensor is not None:
        # Principal component of EFG tensor
        V_zz = np.max(np.abs(np.linalg.eigvalsh(self.config.efg_tensor)))
        
        # Quadrupole coupling constant (simplified)
        # ω_Q = eQV_zz/(4J(2J-1)ℏ) where Q is nuclear quadrupole moment
        # For Er³⁺ electronic state, use effective coupling
        Q_eff = 1.0  # effective quadrupole moment (a.u., to be refined)
        omega_q = Q_eff * V_zz / (4 * self.spin_j * (2*self.spin_j - 1))
        
        # Stark Hamiltonian (quadrupole term)
        H_stark = omega_q * (3*Jz*Jz - self.spin_j*(self.spin_j+1)*qt.qeye(self.dim))
    else:
        H_stark = 0 * qt.qeye(self.dim)
    
    # 3. Hyperfine coupling (minimal due to ²⁸Si enrichment)
    # Simplified: included in noise model rather than Hamiltonian
    H_hyperfine = 0 * qt.qeye(self.dim)
    
    H_total = H_zeeman + H_stark + H_hyperfine
    
    return H_total

def construct_lindblad_operators(self):
    """
    Construct Lindblad collapse operators for decoherence channels
    
    Returns:
        List of (collapse_operator, rate) tuples
    """
    Jx = qt.jmat(self.spin_j, 'x')
    Jy = qt.jmat(self.spin_j, 'y')
    Jz = qt.jmat(self.spin_j, 'z')
    
    collapse_ops = []
    
    # 1. Phonon-mediated decoherence
    gamma_phonon = self._calculate_phonon_decoherence_rate()
    
    # Dephasing operator (loss of phase coherence)
    L_dephasing = np.sqrt(gamma_phonon / 2) * Jz
    collapse_ops.append(L_dephasing)
    
    # Energy relaxation (T₁ process)
    gamma_T1 = gamma_phonon / 10  # Typically T₁ >> T₂
    L_relaxation = np.sqrt(gamma_T1) * (Jx - 1j*Jy)  # Lowering operator
    collapse_ops.append(L_relaxation)
    
    # 2. Isotopic spin bath (nuclear spin flip-flops)
    gamma_bath = self._calculate_spin_bath_rate()
    L_bath = np.sqrt(gamma_bath) * (Jx + Jy)
    collapse_ops.append(L_bath)
    
    # 3. Thermal Johnson noise from readout coils
    gamma_thermal = self._calculate_thermal_noise_rate()
    L_thermal = np.sqrt(gamma_thermal) * Jz
    collapse_ops.append(L_thermal)
    
    return collapse_ops

def _calculate_phonon_decoherence_rate(self) -> float:
    """
    Calculate phonon-mediated decoherence rate Γ₂
    
    Γ₂ = C² × ρ_ph(ω) × σ_T²
    
    where:
    - C: phonon coupling constant
    - ρ_ph(ω): phonon density of states
    - σ_T: thermal displacement
    """
    T = self.config.temperature
    C = self.config.phonon_coupling_constant
    
    # Calculate thermal displacement
    if self.config.force_constants is not None:
        k_well_avg = np.mean(np.linalg.eigvalsh(self.config.force_constants))
        
        # σ_T = sqrt(k_B T / k_well)
        # Convert units: k_well in eV/Å², need SI units
        k_well_si = k_well_avg * 1.602e-19 / (1e-10)**2  # J/m²
        sigma_T = np.sqrt(1.38e-23 * T / k_well_si)  # meters
        sigma_T_ang = sigma_T * 1e10  # Angstroms
    else:
        # Default estimate if no force constants
        sigma_T_ang = 0.1  # Å (rough estimate at 300K)
    
    # Phonon density of states (Debye model approximation)
    # ρ_ph ∝ ω² at low frequencies
    omega_zeeman = (self.config.g_factor * BOHR_MAGNETON * 
                   self.config.B_global / HBAR)  # rad/s
    
    # Debye frequency for Si
    omega_debye = 1.2e14  # rad/s (≈ 63 meV)
    
    if omega_zeeman < omega_debye:
        rho_ph = (omega_zeeman / omega_debye)**2
    else:
        rho_ph = 1.0
    
    # Decoherence rate (convert to Hz)
    # Γ₂ in units of inverse seconds
    Gamma_2 = (C / HBAR_SI)**2 * rho_ph * (sigma_T_ang * 1e-10)**2
    
    # Add temperature scaling
    Gamma_2 *= (1 + 1/(np.exp(HBAR_SI * omega_zeeman / (1.38e-23 * T)) - 1))
    
    return Gamma_2  # Hz

def _calculate_spin_bath_rate(self) -> float:
    """
    Calculate decoherence rate from ²⁹Si nuclear spin bath
    
    Heavily suppressed by isotopic enrichment
    """
    # Hyperfine coupling to ²⁹Si (≈ 100 MHz for nearest neighbors)
    A_hyperfine = 100e6  # Hz
    
    # Number of ²⁹Si spins in interaction volume
    # Rough estimate: ~10 nearest neighbors
    N_bath = 10
    
    # Decoherence rate scales with isotopic fraction
    f_29Si = self.config.si29_fraction
    
    # Γ_bath ∝ f × N × A²
    Gamma_bath = f_29Si * N_bath * (A_hyperfine / 1e6)**2 / (2 * np.pi)
    
    return Gamma_bath  # Hz

def _calculate_thermal_noise_rate(self) -> float:
    """
    Calculate Johnson-Nyquist thermal noise from readout electronics
    """
    # Typical microcoil resistance
    R = 50  # Ohms
    
    # Bandwidth (set by Zeeman splitting)
    omega_zeeman = (self.config.g_factor * BOHR_MAGNETON * 
                   self.config.B_global / HBAR)
    bandwidth = omega_zeeman / (2 * np.pi)  # Hz
    
    # Johnson noise voltage: V_n = sqrt(4 k_B T R Δf)
    V_noise = np.sqrt(4 * 1.38e-23 * self.config.temperature * R * bandwidth)
    
    # Convert to decoherence rate (simplified coupling)
    # Coupling strength ≈ μ_B B_local / V_noise
    coupling = BOHR_MAGNETON * 1.602e-19 * self.config.B_local / V_noise
    
    Gamma_thermal = (coupling / HBAR_SI)**2
    
    return Gamma_thermal  # Hz

def simulate_coherence_decay(self) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Simulate coherence decay and extract T₂
    
    Returns:
        (times, coherences, T2)
    """
    # Construct system
    H = self.construct_hamiltonian()
    c_ops = self.construct_lindblad_operators()
    
    # Initial state: superposition of |J=3/2, m=-1/2⟩ and |J=3/2, m=+1/2⟩
    psi0 = (qt.basis(self.dim, 1) + qt.basis(self.dim, 2)).unit()
    rho0 = qt.ket2dm(psi0)
    
    # Time points
    times = np.linspace(0, self.config.max_time, self.config.time_steps)
    
    # Solve master equation
    print("  Running Lindblad master equation solver...")
    result = qt.mesolve(H, rho0, times, c_ops, 
                       e_ops=[qt.basis(self.dim, 1) * qt.basis(self.dim, 2).dag()])
    
    # Extract off-diagonal coherence
    coherences = np.abs(result.expect[0])
    
    # Fit exponential decay to extract T₂
    # C(t) = C(0) × exp(-t/T₂)
    
    # Use points where coherence has decayed to avoid numerical noise
    valid_idx = coherences > 0.1 * coherences[0]
    if np.sum(valid_idx) > 10:
        t_fit = times[valid_idx]
        c_fit = coherences[valid_idx]
        
        # Log-linear fit
        log_c = np.log(c_fit)
        p = np.polyfit(t_fit, log_c, 1)
        T2 = -1 / p[0]
    else:
        # Decay too fast, estimate from initial slope
        T2 = times[np.argmax(coherences < 0.37 * coherences[0])]
    
    return times, coherences, T2

def plot_coherence_decay(self, times: np.ndarray, coherences: np.ndarray, 
                        T2: float, save_path: str = None):
    """Plot coherence decay curve"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(times * 1000, coherences, 'o-', color='#2E86AB', 
           linewidth=2, markersize=4, label='Simulated coherence')
    
    # Plot fitted exponential
    t_fit = np.linspace(0, min(times[-1], 5*T2), 500)
    c_fit = coherences[0] * np.exp(-t_fit / T2)
    ax.plot(t_fit * 1000, c_fit, '--', color='#F18F01', 
           linewidth=2, label=f'Exp. fit: T₂ = {T2*1000:.1f} ms')
    
    # Mark 1/e decay point
    ax.axhline(y=coherences[0]/np.e, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=T2*1000, color='gray', linestyle=':', alpha=0.5)
    
    # Add target line
    if self.config.target_T2:
        ax.axvline(x=self.config.target_T2*1000, color='red', 
                  linestyle='--', alpha=0.7, linewidth=2,
                  label=f'Target: {self.config.target_T2*1000:.0f} ms')
    
    ax.set_xlabel('Time (ms)', fontsize=12)
    ax.set_ylabel('Coherence |ρ₁₂(t)|', fontsize=12)
    ax.set_title(f'Quantum Coherence Decay at {self.config.temperature}K', 
                fontsize=14, fontweight='bold')
    ax.set_yscale('log')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which='both')
    
    # Add decoherence rates annotation
    gamma_phonon = self._calculate_phonon_decoherence_rate()
    gamma_bath = self._calculate_spin_bath_rate()
    gamma_thermal = self._calculate_thermal_noise_rate()
    
    text_str = f"Decoherence rates:\n"
    text_str += f"  Phonons: {gamma_phonon:.2e} Hz\n"
    text_str += f"  Spin bath: {gamma_bath:.2e} Hz\n"
    text_str += f"  Thermal: {gamma_thermal:.2e} Hz"
    
    ax.text(0.95, 0.95, text_str, transform=ax.transAxes,
           fontsize=9, verticalalignment='top', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved coherence plot to {save_path}")
    else:
        plt.show()

def run_parameter_sweep(self, strain_values: np.ndarray, 
                       force_constants_list: List[np.ndarray]) -> np.ndarray:
    """
    Run T₂ simulations for multiple geometric configurations
    
    Args:
        strain_values: Array of strain values (%)
        force_constants_list: List of force constant matrices (eV/Å²)
        
    Returns:
        Array of T₂ values (seconds)
    """
    T2_values = []
    
    print(f"\n{'='*60}")
    print("PARAMETER SWEEP: T₂ vs. Geometric Configuration")
    print(f"{'='*60}\n")
    
    for i, (strain, k_matrix) in enumerate(zip(strain_values, force_constants_list)):
        print(f"[{i+1}/{len(strain_values)}] Strain = {strain:.2f}%")
        
        # Update force constants
        self.config.force_constants = k_matrix
        
        # Run simulation
        times, coherences, T2 = self.simulate_coherence_decay()
        T2_values.append(T2)
        
        print(f"  → T₂ = {T2*1000:.2f} ms\n")
    
    return np.array(T2_values)

def generate_optimization_report(self, T2: float, save_path: str):
    """Generate detailed optimization report"""
    with open(save_path, 'w') as f:
        f.write("QUANTUM COHERENCE OPTIMIZATION REPORT\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("SYSTEM PARAMETERS\n")
        f.write("-" * 60 + "\n")
        f.write(f"Temperature: {self.config.temperature} K\n")
        f.write(f"B_global: {self.config.B_global} T\n")
        f.write(f"Spin: J = {self.spin_j}\n")
        f.write(f"Isotopic enrichment: {(1-self.config.si29_fraction)*100:.2f}% ²⁸Si\n\n")
        
        f.write("DECOHERENCE ANALYSIS\n")
        f.write("-" * 60 + "\n")
        gamma_phonon = self._calculate_phonon_decoherence_rate()
        gamma_bath = self._calculate_spin_bath_rate()
        gamma_thermal = self._calculate_thermal_noise_rate()
        gamma_total = gamma_phonon + gamma_bath + gamma_thermal
        
        f.write(f"Phonon decoherence:  {gamma_phonon:.3e} Hz ({gamma_phonon/gamma_total*100:.1f}%)\n")
        f.write(f"Spin bath:          {gamma_bath:.3e} Hz ({gamma_bath/gamma_total*100:.1f}%)\n")
        f.write(f"Thermal noise:      {gamma_thermal:.3e} Hz ({gamma_thermal/gamma_total*100:.1f}%)\n")
        f.write(f"Total:              {gamma_total:.3e} Hz\n\n")
        
        f.write("PERFORMANCE METRICS\n")
        f.write("-" * 60 + "\n")
        f.write(f"Predicted T₂:       {T2*1000:.2f} ms\n")
        f.write(f"Target T₂:          {self.config.target_T2*1000:.0f} ms\n")
        
        if T2 >= self.config.target_T2:
            f.write(f"Status:             ✓ TARGET ACHIEVED\n")
            f.write(f"Margin:             {(T2/self.config.target_T2 - 1)*100:.1f}%\n")
        else:
            f.write(f"Status:             ✗ Below target\n")
            f.write(f"Deficit:            {(1 - T2/self.config.target_T2)*100:.1f}%\n")
        
        f.write("\n")
        f.write("OPTIMIZATION RECOMMENDATIONS\n")
        f.write("-" * 60 + "\n")
        
        # Identify dominant decoherence channel
        rates = {'Phonon': gamma_phonon, 'Spin bath': gamma_bath, 
                'Thermal': gamma_thermal}
        dominant = max(rates, key=rates.get)
        
        f.write(f"Dominant decoherence: {dominant}\n\n")
        
        if dominant == 'Phonon':
            f.write("Recommendations:\n")
            f.write("1. Increase well stiffness (k_well) via strain optimization\n")
            f.write("2. Reduce Er-P distance to enhance geometric confinement\n")
            f.write("3. Consider operation at reduced temperature\n")
        elif dominant == 'Spin bath':
            f.write("Recommendations:\n")
            f.write("1. Further isotopic enrichment of ²⁸Si\n")
            f.write("2. Increase Er-P distance to reduce hyperfine coupling\n")
        else:
            f.write("Recommendations:\n")
            f.write("1. Optimize readout coil geometry for lower resistance\n")
            f.write("2. Use cryogenic amplifiers\n")
            f.write("3. Reduce measurement bandwidth\n")
    
    print(f"✓ Generated optimization report: {save_path}")
```

def analyze_dft_to_t2(dft_results_path: str, config: QuantumSystemConfig):
“””
Complete pipeline: DFT results → T₂ prediction

```
Args:
    dft_results_path: Path to JSON file with DFT results
    config: Quantum system configuration
"""
# Load DFT results
with open(dft_results_path, 'r') as f:
    dft_data = json.load(f)

print("\n🔬 DFT → T₂ PREDICTION PIPELINE")
print("=" * 60)

# Extract optimal configuration
optimal_result = dft_data['optimal_configuration']

# Set EFG tensor
config.efg_tensor = np.array(optimal_result['efg_tensor'])
print(f"✓ Loaded EFG tensor")

# Set force constants
config.force_constants = np.array(optimal_result['force_constants'])
print(f"✓ Loaded force constants")

# Create simulator
simulator = ErQuantumSimulator(config)

# Run simulation
print("\nRunning quantum dynamics simulation...")
times, coherences, T2 = simulator.simulate_coherence_decay()

print(f"\n{'='*60}")
print(f"RESULT: T₂ = {T2*1000:.2f} ms at {config.temperature}K")
print(f"{'='*60}\n")

# Plot
simulator.plot_coherence_decay(times, coherences, T2, 
                               save_path='coherence_decay.png')

# Generate report
simulator.generate_optimization_report(T2, 'optimization_report.txt')

return T2
```

if **name** == “**main**”:
# Example usage with placeholder DFT data
config = QuantumSystemConfig(
B_global=1.0,
temperature=300.0,
spin_quantum_number=1.5,
phonon_coupling_constant=1e-3,
si29_fraction=0.001,
target_T2=0.1
)

```
# Placeholder force constants (from hypothetical DFT)
# These would come from real DFT Hessian calculation
k_well = 5.0  # eV/Å² (stiff well from optimal strain)
config.force_constants = np.diag([k_well, k_well, k_well])

# Placeholder EFG tensor
V_zz = 1e-3  # V/Å²
config.efg_tensor = np.diag([V_zz, V_zz, V_zz])

print("\n⚛️ Er³⁺ Quantum Coherence Simulation")
print("=" * 60)
print(f"Target: Demonstrate T₂ ≥ {config.target_T2*1000:.0f} ms at {config.temperature}K")
print("=" * 60)

if QUTIP_AVAILABLE:
    simulator = ErQuantumSimulator(config)
    times, coherences, T2 = simulator.simulate_coherence_decay()
    
    print(f"\n{'='*60}")
    print(f"✓ Predicted T₂ = {T2*1000:.2f} ms")
    print(f"{'='*60}\n")
    
    simulator.plot_coherence_decay(times, coherences, T2)
    simulator.generate_optimization_report(T2, 'optimization_report.txt')
else:
    print("\n⚠ Install QuTip to run simulations: pip install qutip\n")
```
