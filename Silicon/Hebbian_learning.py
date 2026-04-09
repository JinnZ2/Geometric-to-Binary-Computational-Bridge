"""
Plastic Multi-Bridge Neural Lattice
Adds Hebbian learning to the multi-bridge lattice.
Coupling strengths evolve based on correlated activity, enabling pattern reinforcement.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. REUSE MULTI-BRIDGE NODE AND LATTICE (from previous)
#    Assume MultiBridgeNode, LatticeCouplings, MultiBridgeLattice are defined.
# ============================================================
# (In practice, copy the classes here. I'll define a minimal version for clarity.)

class DummyNode:
    def __init__(self):
        self.displacement = np.zeros(3)
        self.spin_state = 0
        self.optical_excited = 0
        self.B_field = np.array([0.0, 0.0, 0.1])
        self.E_field = np.array([0.0, 0.0, 0.0])
    def total_energy(self, disp, spin, opt, B, E):
        # Simplified: just return a dummy value for demonstration
        return np.sum(disp**2) + spin*0.01 + opt*0.01

class PlasticLatticeCouplings(LatticeCouplings):
    """Extends LatticeCouplings with plasticity parameters."""
    def __init__(self, base_strain=2.0, base_spin=0.05, base_opt=0.01, phi=(1+np.sqrt(5))/2,
                 learning_rate=0.01, decay=0.001, clip_max=5.0):
        super().__init__(base_strain, base_spin, base_opt, phi)
        self.lr = learning_rate
        self.decay = decay
        self.clip_max = clip_max
        # We'll store per-edge plastic components separately.
        # In a real system, coupling is modified by local strain history.

class PlasticMultiBridgeLattice(MultiBridgeLattice):
    def __init__(self, N, couplings=None, node_class=None):
        super().__init__(N, couplings, node_class)
        # Initialize plastic coupling offsets (per edge)
        self.plastic_strain = {}   # (i,j,ni,nj) -> delta_k
        self.plastic_spin = {}     # (i,j,ni,nj) -> delta_J
        self.activity_history = [] # keep track for analysis

    def get_coupling(self, i, j, ni, nj, coupling_type='strain'):
        """Return effective coupling including plastic component."""
        base = self.couplings.k_strain_nn if coupling_type=='strain' else self.couplings.J_spin_nn
        edge = tuple(sorted(((i,j),(ni,nj))))
        if coupling_type == 'strain':
            delta = self.plastic_strain.get(edge, 0.0)
            return max(0.1, base + delta)  # minimum positive
        else:
            delta = self.plastic_spin.get(edge, 0.0)
            return base + delta

    def total_energy(self, state_vector=None):
        if state_vector is not None:
            self._unflatten_state(state_vector)
        E = 0.0
        # Single node energies (simplified)
        for i in range(self.N):
            for j in range(self.N):
                node = self.nodes[i][j]
                E += np.sum(node.displacement**2) + node.spin_state*0.01 + node.optical_excited*0.01

        # Inter-node with plastic couplings
        for i in range(self.N):
            for j in range(self.N):
                node = self.nodes[i][j]
                for ni, nj in self.get_neighbors(i,j, shell=1):
                    other = self.nodes[ni][nj]
                    diff = node.displacement - other.displacement
                    k_eff = self.get_coupling(i,j,ni,nj,'strain')
                    E += 0.5 * k_eff * np.dot(diff, diff)
                    s1 = 2*node.spin_state - 1
                    s2 = 2*other.spin_state - 1
                    J_eff = self.get_coupling(i,j,ni,nj,'spin')
                    E += J_eff * s1 * s2
        return E

    def hebbian_update(self, activity_pattern, duration=1.0):
        """
        Update plastic couplings based on co-activation.
        activity_pattern: NxN array of node activations (0 to 1)
        duration: effective "time" for learning rate scaling
        """
        lr = self.couplings.lr * duration
        decay = self.couplings.decay * duration

        for i in range(self.N):
            for j in range(self.N):
                ai = activity_pattern[i,j]
                for ni, nj in self.get_neighbors(i,j, shell=1):
                    aj = activity_pattern[ni,nj]
                    edge = tuple(sorted(((i,j),(ni,nj))))
                    # Hebbian: increase coupling if both active
                    delta = lr * ai * aj
                    # Update strain coupling plastic component
                    current = self.plastic_strain.get(edge, 0.0)
                    new_val = current + delta - decay * current
                    new_val = np.clip(new_val, -self.couplings.k_strain_nn*0.5, self.couplings.clip_max)
                    self.plastic_strain[edge] = new_val
                    # Update spin coupling similarly
                    current_s = self.plastic_spin.get(edge, 0.0)
                    new_s = current_s + delta*0.1 - decay * current_s  # slower spin plasticity
                    new_s = np.clip(new_s, -self.couplings.J_spin_nn*0.5, self.couplings.clip_max*0.1)
                    self.plastic_spin[edge] = new_s

        self.activity_history.append(activity_pattern.copy())

    def train_sequence(self, patterns, epochs=5):
        """Train the lattice on a sequence of patterns."""
        print(f"Training on {len(patterns)} patterns for {epochs} epochs...")
        for epoch in range(epochs):
            for pat in patterns:
                # Present pattern (set optical excitation)
                self.set_pattern(pat, 'optical_excited')
                # Relax to settle
                self.relax()
                # Compute activity as combined optical + spin + displacement magnitude
                activity = self._compute_activity()
                # Update couplings
                self.hebbian_update(activity, duration=0.1)
            print(f"Epoch {epoch+1} complete.")

    def _compute_activity(self):
        """Combine state variables into a single activity measure."""
        act = np.zeros((self.N, self.N))
        for i in range(self.N):
            for j in range(self.N):
                node = self.nodes[i][j]
                # Normalize displacement magnitude (0 to 1)
                disp_mag = np.clip(np.linalg.norm(node.displacement)/0.5, 0, 1)
                act[i,j] = 0.3*node.optical_excited + 0.3*node.spin_state + 0.4*disp_mag
        return act

    def visualize_coupling_strengths(self):
        """Show the learned coupling matrix as a heatmap."""
        N = self.N
        # Build effective coupling map (average per node)
        k_map = np.zeros((N,N))
        j_map = np.zeros((N,N))
        counts = np.zeros((N,N))
        for i in range(N):
            for j in range(N):
                for ni, nj in self.get_neighbors(i,j, shell=1):
                    edge = tuple(sorted(((i,j),(ni,nj))))
                    k_map[i,j] += self.get_coupling(i,j,ni,nj,'strain')
                    j_map[i,j] += self.get_coupling(i,j,ni,nj,'spin')
                    counts[i,j] += 1
        k_map /= (counts + 1e-9)
        j_map /= (counts + 1e-9)

        fig, axes = plt.subplots(1,2, figsize=(12,5))
        im1 = axes[0].imshow(k_map, cmap='viridis')
        axes[0].set_title('Strain Coupling Strengths')
        plt.colorbar(im1, ax=axes[0])
        im2 = axes[1].imshow(j_map, cmap='plasma')
        axes[1].set_title('Spin Coupling Strengths')
        plt.colorbar(im2, ax=axes[1])
        plt.tight_layout()
        plt.savefig('learned_couplings.png', dpi=150)
        plt.show()

# ============================================================
# DEMONSTRATION: Learning and Pattern Reinforcement
# ============================================================
def demo_hebbian_learning():
    print("="*70)
    print("PLASTIC MULTI-BRIDGE LATTICE: Hebbian Learning")
    print("="*70)

    N = 6
    lattice = PlasticMultiBridgeLattice(N, couplings=PlasticLatticeCouplings(learning_rate=0.05))

    # Create training patterns
    p1 = np.zeros((N,N)); p1[1:4, 1:4] = 1  # 3x3 block
    p2 = np.eye(N)                           # diagonal
    p3 = np.fliplr(np.eye(N))                # anti-diagonal

    patterns = [p1, p2, p3]

    # Visualize initial coupling
    print("Initial coupling map (uniform):")
    lattice.visualize_coupling_strengths()

    # Train
    lattice.train_sequence(patterns, epochs=10)

    # Visualize learned couplings
    print("\nLearned coupling map (after training):")
    lattice.visualize_coupling_strengths()

    # Test recall with noise
    print("\nTesting pattern completion after learning...")
    test_pattern = p1.copy()
    # Add 30% noise
    noise_mask = np.random.rand(N,N) < 0.3
    test_pattern[noise_mask] = 1 - test_pattern[noise_mask]

    lattice.set_pattern(test_pattern, 'optical_excited')
    initial_energy = lattice.total_energy()
    lattice.relax()
    recovered = lattice.get_pattern('optical_excited')

    fig, axes = plt.subplots(1,3, figsize=(12,4))
    axes[0].imshow(p1, cmap='binary')
    axes[0].set_title('Original Pattern')
    axes[1].imshow(test_pattern, cmap='binary')
    axes[1].set_title('Noisy Input')
    axes[2].imshow(recovered, cmap='binary')
    axes[2].set_title('Recovered')
    for ax in axes: ax.set_xticks([]); ax.set_yticks([])
    plt.savefig('learning_recall.png', dpi=150)
    plt.show()

    accuracy = np.mean(recovered == p1)
    print(f"Recall accuracy: {accuracy*100:.1f}%")

def demo_plasticity_energy_evolution():
    """Show how training lowers the energy of stored patterns."""
    print("\n"+"="*70)
    print("ENERGY EVOLUTION DURING LEARNING")
    print("="*70)
    N = 5
    lattice = PlasticMultiBridgeLattice(N, couplings=PlasticLatticeCouplings(learning_rate=0.03))

    pattern = np.zeros((N,N))
    pattern[1:4,1:4] = 1

    energies = []
    for epoch in range(20):
        lattice.set_pattern(pattern, 'optical_excited')
        e = lattice.relax()
        energies.append(e)
        activity = lattice._compute_activity()
        lattice.hebbian_update(activity, duration=0.1)

    plt.figure(figsize=(8,5))
    plt.plot(energies, 'o-')
    plt.xlabel('Epoch')
    plt.ylabel('Relaxed Energy (eV)')
    plt.title('Pattern Energy Decreases with Plasticity')
    plt.grid(alpha=0.3)
    plt.savefig('energy_evolution.png', dpi=150)
    plt.show()

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    demo_hebbian_learning()
    demo_plasticity_energy_evolution()
    print("\n✅ Plasticity demonstrations complete.")
    print("The lattice now learns and reinforces patterns via Hebbian updates.")
    print("Next: Hierarchical multi-layer lattices and real-time dynamics.")
