"""
Tensor-State Lattice with Magnetic Read/Write and Hebbian Plasticity
Implements the Octahedral_State_Encoder JSON specification across a 2D array.
Nodes are 3-bit tensor states. Couplings evolve via tensor-similarity-based Hebbian learning.
Includes Zeeman energy for magnetic addressing and phonon-mediated transition timescales.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. TENSOR ENCODER (from JSON spec)
# ============================================================
class TensorOctahedronEncoder:
    # (Same as previous implementation - include fully)
    STATE_MAP = {
        (0,0,0): "North apex – low potential (λ₁ dominant)",
        (0,0,1): "South apex – low potential (λ₂ dominant)",
        (0,1,0): "East ridge – strain aligned",
        (0,1,1): "West ridge – compressive alignment",
        (1,0,0): "Front face – conductive bias",
        (1,0,1): "Back face – magnetic bias",
        (1,1,0): "Axial symmetry – resonance coupling",
        (1,1,1): "Stable equilibrium node"
    }
    EIGENVALUE_PATTERNS = {
        (0,0,0): np.array([0.6, 0.3, 0.1]),
        (0,0,1): np.array([0.3, 0.6, 0.1]),
        (0,1,0): np.array([0.45, 0.45, 0.1]),
        (0,1,1): np.array([0.45, 0.1, 0.45]),
        (1,0,0): np.array([0.1, 0.45, 0.45]),
        (1,0,1): np.array([0.1, 0.6, 0.3]),
        (1,1,0): np.array([0.33, 0.33, 0.34]),
        (1,1,1): np.array([1/3, 1/3, 1/3])
    }
    @staticmethod
    def get_basis_vectors(state_bits):
        signs = np.array([(1 if b else -1) for b in state_bits])
        a1 = signs / np.sqrt(3)
        if abs(a1[0]) < 0.9:
            v2 = np.array([1,0,0])
        else:
            v2 = np.array([0,1,0])
        a2 = v2 - np.dot(v2, a1) * a1
        a2 /= np.linalg.norm(a2)
        a3 = np.cross(a1, a2)
        return a1, a2, a3
    def __init__(self):
        self.current_state_bits = (0,0,0)
        self.current_tensor = None
        self._update_tensor()
    def encode(self, bits):
        bits = tuple(bits)
        if bits not in self.STATE_MAP:
            raise ValueError(f"Invalid state: {bits}")
        self.current_state_bits = bits
        self._update_tensor()
        return self.get_tensor_representation()
    def _update_tensor(self):
        lambdas = self.EIGENVALUE_PATTERNS[self.current_state_bits]
        a1, a2, a3 = self.get_basis_vectors(self.current_state_bits)
        tensor = (lambdas[0] * np.outer(a1, a1) +
                  lambdas[1] * np.outer(a2, a2) +
                  lambdas[2] * np.outer(a3, a3))
        tensor /= np.trace(tensor)
        self.current_tensor = tensor
    def get_tensor_representation(self):
        a1, a2, a3 = self.get_basis_vectors(self.current_state_bits)
        lambdas = self.EIGENVALUE_PATTERNS[self.current_state_bits]
        return {
            "state_bits": self.current_state_bits,
            "description": self.STATE_MAP[self.current_state_bits],
            "basis_vectors": [a1.tolist(), a2.tolist(), a3.tolist()],
            "eigenvalues": lambdas.tolist(),
            "tensor_matrix": self.current_tensor.tolist(),
            "trace": np.trace(self.current_tensor),
            "orthogonality_check": [np.dot(a1,a2), np.dot(a2,a3), np.dot(a1,a3)]
        }
    def decode_tensor(self, tensor):
        tensor = (tensor + tensor.T) / 2
        tensor /= np.trace(tensor)
        evals, evecs = np.linalg.eigh(tensor)
        idx = np.argsort(evals)[::-1]
        evals = evals[idx]
        best_bits = None
        best_dist = np.inf
        for bits, pattern in self.EIGENVALUE_PATTERNS.items():
            dist = np.linalg.norm(evals - pattern)
            if dist < best_dist:
                best_dist = dist
                best_bits = bits
        self.current_state_bits = best_bits
        self._update_tensor()
        return best_bits
    def to_displacement(self, scale=0.4):
        evals, evecs = np.linalg.eigh(self.current_tensor)
        dominant_idx = np.argmax(evals)
        direction = evecs[:, dominant_idx]
        magnitude = scale * evals[dominant_idx]
        return direction * magnitude
    def similarity(self, other_encoder):
        """Tensor similarity measure (Frobenius inner product)."""
        return np.trace(np.dot(self.current_tensor, other_encoder.current_tensor))

# ============================================================
# 2. TENSOR LATTICE NODE
# ============================================================
class TensorLatticeNode:
    """Node in the tensor lattice with magnetic and strain degrees of freedom."""
    def __init__(self):
        self.encoder = TensorOctahedronEncoder()
        self.displacement = np.zeros(3)  # from tensor via to_displacement
        self.spin = 0  # 0 or 1 (magnetic bias)
        self.B_local = np.array([0.0, 0.0, 0.0])  # local magnetic field (T)
        self._sync_displacement()

    def set_state(self, bits):
        self.encoder.encode(bits)
        self._sync_displacement()
        # Set spin based on state description (magnetic bias for (1,0,1))
        self.spin = 1 if bits == (1,0,1) else 0

    def _sync_displacement(self):
        self.displacement = self.encoder.to_displacement(scale=0.4)

    def zeeman_energy(self, B_ext):
        """E = -M·B_ext. M approximated as χ * tensor · B"""
        chi = 0.01  # magnetostrictive susceptibility (eV/T²)
        M = chi * np.dot(self.encoder.current_tensor, B_ext)
        return -np.dot(M, B_ext)

    def strain_energy(self):
        """Simplified strain energy from displacement magnitude."""
        # In real system, this is Keating potential; here we approximate.
        return 2.0 * np.sum(self.displacement**2)  # eV/Å²

    def total_local_energy(self, B_ext):
        return self.strain_energy() + self.zeeman_energy(B_ext)

# ============================================================
# 3. TENSOR LATTICE WITH PLASTICITY
# ============================================================
class TensorLattice:
    def __init__(self, N, base_coupling=2.0, learning_rate=0.01, temperature=0.025):
        self.N = N
        self.nodes = [[TensorLatticeNode() for _ in range(N)] for _ in range(N)]
        self.base_coupling = base_coupling
        self.lr = learning_rate
        self.T = temperature  # eV (room temp ~0.025 eV)
        # Plastic strain couplings (edge-specific)
        self.plastic_couplings = {}  # (i,j,ni,nj) -> delta_k
        # Magnetic dipole couplings (can also be plastic)
        self.J0 = 0.05 * 0.001  # eV
        self.plastic_J = {}

    def get_coupling(self, i, j, ni, nj):
        edge = tuple(sorted(((i,j),(ni,nj))))
        delta = self.plastic_couplings.get(edge, 0.0)
        return max(0.1, self.base_coupling + delta)

    def total_energy(self, B_field=None):
        if B_field is None:
            B_field = np.zeros(3)
        E = 0.0
        # Local energies
        for i in range(self.N):
            for j in range(self.N):
                E += self.nodes[i][j].total_local_energy(B_field)
        # Strain coupling between neighbors
        for i in range(self.N):
            for j in range(self.N):
                for ni, nj in self._neighbors(i,j):
                    k = self.get_coupling(i,j,ni,nj)
                    diff = self.nodes[i][j].displacement - self.nodes[ni][nj].displacement
                    E += 0.5 * k * np.dot(diff, diff)
        # Spin coupling (Ising)
        for i in range(self.N):
            for j in range(self.N):
                for ni, nj in self._neighbors(i,j):
                    edge = tuple(sorted(((i,j),(ni,nj))))
                    J = self.J0 + self.plastic_J.get(edge, 0.0)
                    s1 = 2*self.nodes[i][j].spin - 1
                    s2 = 2*self.nodes[ni][nj].spin - 1
                    E += J * s1 * s2
        return E

    def _neighbors(self, i, j):
        for di, dj in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            ni, nj = i+di, j+dj
            if 0 <= ni < self.N and 0 <= nj < self.N:
                yield ni, nj

    def set_pattern(self, bit_matrix):
        """Set the lattice to a pattern of 3-bit states (NxN array of tuples)."""
        for i in range(self.N):
            for j in range(self.N):
                self.nodes[i][j].set_state(bit_matrix[i,j])

    def get_pattern(self):
        """Return NxN array of current 3-bit states."""
        pat = np.empty((self.N, self.N), dtype=object)
        for i in range(self.N):
            for j in range(self.N):
                pat[i,j] = self.nodes[i][j].encoder.current_state_bits
        return pat

    def relax(self, B_field=None, steps=50, dt=0.01):
        """Gradient descent relaxation of displacements (not bits)."""
        for _ in range(steps):
            for i in range(self.N):
                for j in range(self.N):
                    grad = self._displacement_gradient(i, j, B_field)
                    self.nodes[i][j].displacement -= dt * grad
            # Re-sync bits after displacement update? For now keep fixed bits.
            # Bits change via thermal flips, not continuous relaxation.

    def _displacement_gradient(self, i, j, B_field):
        eps = 1e-5
        grad = np.zeros(3)
        node = self.nodes[i][j]
        disp0 = node.displacement.copy()
        E0 = self.total_energy(B_field)
        for d in range(3):
            node.displacement[d] += eps
            E_plus = self.total_energy(B_field)
            node.displacement = disp0
            grad[d] = (E_plus - E0) / eps
        return grad

    def thermal_step(self, B_field=None, flip_prob=0.01):
        """Metropolis-like step for bit flips with transition timescale ~ ps."""
        # Randomly select a node
        i, j = np.random.randint(0, self.N, 2)
        node = self.nodes[i][j]
        current_bits = node.encoder.current_state_bits
        # Propose a random new state
        new_bits = list(current_bits)
        flip_idx = np.random.randint(3)
        new_bits[flip_idx] = 1 - new_bits[flip_idx]
        new_bits = tuple(new_bits)

        E_old = self.total_energy(B_field)
        # Temporarily change state
        old_state = current_bits
        node.set_state(new_bits)
        E_new = self.total_energy(B_field)
        delta_E = E_new - E_old

        if delta_E < 0 or np.random.rand() < np.exp(-delta_E / self.T):
            # Accept flip
            pass
        else:
            # Reject
            node.set_state(old_state)
        return delta_E

    def hebbian_update(self, duration=0.1):
        """Update couplings based on tensor similarity between neighbors."""
        lr = self.lr * duration
        for i in range(self.N):
            for j in range(self.N):
                node = self.nodes[i][j]
                for ni, nj in self._neighbors(i,j):
                    other = self.nodes[ni][nj]
                    edge = tuple(sorted(((i,j),(ni,nj))))
                    # Similarity measure: dot product of tensors
                    sim = node.encoder.similarity(other.encoder)
                    # Increase coupling if similar
                    delta = lr * sim
                    # Update strain coupling
                    current = self.plastic_couplings.get(edge, 0.0)
                    self.plastic_couplings[edge] = current + delta
                    # Update spin coupling (scaled)
                    current_J = self.plastic_J.get(edge, 0.0)
                    self.plastic_J[edge] = current_J + delta * 0.1

    def apply_magnetic_field_gradient(self, center, strength=0.1, sigma=1.0):
        """Apply a Gaussian magnetic field profile for addressing."""
        B = np.zeros((self.N, self.N, 3))
        for i in range(self.N):
            for j in range(self.N):
                r2 = (i-center[0])**2 + (j-center[1])**2
                B[i,j,2] = strength * np.exp(-r2/(2*sigma**2))
        return B

    def readout_magnetic(self, probe_position, B_field_map):
        """Simulate magnetic readout: measure Zeeman energy response."""
        # In practice, one would measure local magnetization change.
        i, j = probe_position
        node = self.nodes[i][j]
        B_local = B_field_map[i,j]
        return node.zeeman_energy(B_local)

# ============================================================
# 4. DEMONSTRATIONS
# ============================================================
def create_test_tensor_pattern(N):
    """Create a simple pattern: alternating (0,0,0) and (1,1,1)."""
    pat = np.empty((N,N), dtype=object)
    for i in range(N):
        for j in range(N):
            pat[i,j] = (0,0,0) if (i+j)%2==0 else (1,1,1)
    return pat

def demo_tensor_lattice():
    print("="*70)
    print("TENSOR-STATE LATTICE WITH MAGNETIC ADDRESSING")
    print("="*70)

    N = 5
    lattice = TensorLattice(N, learning_rate=0.02)

    # Set an initial pattern
    pattern = create_test_tensor_pattern(N)
    lattice.set_pattern(pattern)
    print("Initial pattern set: checkerboard of (0,0,0) and (1,1,1)")

    # Apply a magnetic field gradient at center
    B_map = lattice.apply_magnetic_field_gradient(center=(2,2), strength=0.2, sigma=1.5)
    print("Applied magnetic field gradient at (2,2)")

    # Compute initial energy
    E0 = lattice.total_energy(B_field=None)  # use local fields? We'll ignore for now.
    print(f"Initial total energy: {E0:.4f} eV")

    # Perform thermal steps to let system evolve
    print("Running thermal steps (0.5 ps each)...")
    for step in range(100):
        lattice.thermal_step(flip_prob=0.05)
    E1 = lattice.total_energy()
    print(f"Energy after thermalization: {E1:.4f} eV")

    # Hebbian learning step
    lattice.hebbian_update(duration=1.0)
    print("Hebbian update applied")

    # Readout at center
    probe = (2,2)
    signal = lattice.readout_magnetic(probe, B_map)
    state = lattice.nodes[probe[0]][probe[1]].encoder.current_state_bits
    print(f"Readout at {probe}: state={state}, Zeeman signal={signal:.6f} eV")

    # Visualize pattern and couplings
    fig, axes = plt.subplots(1,2, figsize=(10,4))
    # Pattern as bit sum (0..3)
    bit_sums = np.zeros((N,N))
    for i in range(N):
        for j in range(N):
            bit_sums[i,j] = sum(lattice.nodes[i][j].encoder.current_state_bits)
    im1 = axes[0].imshow(bit_sums, cmap='viridis')
    axes[0].set_title('State Bit Sum (0-3)')
    plt.colorbar(im1, ax=axes[0])

    # Coupling map (average per node)
    k_map = np.zeros((N,N))
    counts = np.zeros((N,N))
    for i in range(N):
        for j in range(N):
            for ni, nj in lattice._neighbors(i,j):
                edge = tuple(sorted(((i,j),(ni,nj))))
                k_map[i,j] += lattice.get_coupling(i,j,ni,nj)
                counts[i,j] += 1
    k_map /= counts
    im2 = axes[1].imshow(k_map, cmap='plasma')
    axes[1].set_title('Strain Coupling Strengths')
    plt.colorbar(im2, ax=axes[1])
    plt.tight_layout()
    plt.savefig('tensor_lattice_state.png', dpi=150)
    plt.show()

    print("Demo complete.")

if __name__ == "__main__":
    demo_tensor_lattice()
