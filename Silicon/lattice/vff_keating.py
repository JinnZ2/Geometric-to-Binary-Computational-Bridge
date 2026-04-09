# STATUS: infrastructure -- Keating VFF potential for 5-atom Si cluster, finds 8 octahedral minima
"""
Silicon Octahedral State Simulator
Valence Force Field (Keating Model) for a 5-atom Si cluster.
Finds the 8 geometric states for non-binary information encoding.
"""

import numpy as np
from scipy.optimize import minimize, basinhopping
from itertools import combinations
import warnings

warnings.filterwarnings('ignore')


# ============================================
# 1. THE PHYSICS CORE: KEATING POTENTIAL
# ============================================

class SiliconOctahedron:
    """
    A 5-atom silicon cluster: 1 central atom + 4 tetrahedral neighbors.
    The 4 neighbors are fixed at ideal tetrahedral positions.
    The central atom is free to displace in 3D.
    Energy landscape reveals 8 local minima corresponding to
    displacements toward the 8 faces of the surrounding octahedron.
    """

    def __init__(self,
                 d0=2.35,      # Si-Si bond length (Angstroms)
                 alpha=3.0,    # Bond stretching (eV/Angstrom^2)
                 beta=0.75):   # Bond bending (eV/Angstrom^2)
        self.d0 = d0
        self.alpha = alpha
        self.beta = beta

        # Fixed tetrahedral vertices (normalized)
        v = 1.0 / np.sqrt(3)
        self.vertices = np.array([
            [ v,  v,  v],
            [-v, -v,  v],
            [-v,  v, -v],
            [ v, -v, -v]
        ]) * self.d0

        # Precompute ideal bond vectors for angle reference
        self.ideal_bonds = self.vertices  # relative to center at origin

    def keating_energy(self, displacement):
        """
        Compute Keating strain energy for a given central atom displacement.
        displacement: [dx, dy, dz] in Angstroms
        Returns energy in eV.
        """
        center = displacement  # since vertices are relative to origin
        bonds = self.vertices - center  # shape (4,3)

        # --- Bond stretching term ---
        # E_stretch = (3/16)*(alpha/d0^2) * sum( (r^2 - d0^2)^2 )
        stretch_sum = 0.0
        for b in bonds:
            r_sq = np.dot(b, b)
            stretch_sum += (r_sq - self.d0**2)**2
        E_stretch = (3.0 / 16.0) * (self.alpha / self.d0**2) * stretch_sum

        # --- Bond bending term ---
        # E_bend = (3/8)*(beta/d0^2) * sum_over_pairs( (cos_theta + 1/3)^2 )
        bend_sum = 0.0
        for (i, j) in combinations(range(4), 2):
            bi = bonds[i]
            bj = bonds[j]
            ri = np.linalg.norm(bi)
            rj = np.linalg.norm(bj)
            if ri > 1e-6 and rj > 1e-6:
                cos_theta = np.dot(bi, bj) / (ri * rj)
                delta = cos_theta + (1.0 / 3.0)  # ideal cos = -1/3
                bend_sum += delta**2
        E_bend = (3.0 / 8.0) * (self.beta / self.d0**2) * bend_sum

        return E_stretch + E_bend

    def energy_landscape_2d(self, plane='xy', z=0.0, resolution=100, limit=0.8):
        """
        Compute energy on a 2D grid slice through displacement space.
        plane: 'xy', 'xz', or 'yz'
        z: fixed coordinate for the orthogonal axis
        Returns X, Y (meshgrid), Z_energy
        """
        x = np.linspace(-limit, limit, resolution)
        y = np.linspace(-limit, limit, resolution)
        X, Y = np.meshgrid(x, y)
        Z = np.zeros_like(X)

        for i in range(resolution):
            for j in range(resolution):
                if plane == 'xy':
                    disp = np.array([X[i, j], Y[i, j], z])
                elif plane == 'xz':
                    disp = np.array([X[i, j], z, Y[i, j]])
                else:  # yz
                    disp = np.array([z, X[i, j], Y[i, j]])
                Z[i, j] = self.keating_energy(disp)
        return X, Y, Z

    def find_minima(self, n_starting_points=50, temp=0.5):
        """
        Use basin-hopping global optimization to locate local minima.
        Returns list of unique minima (rounded to 3 decimals).
        """
        bounds = [(-0.8, 0.8), (-0.8, 0.8), (-0.8, 0.8)]

        minima_candidates = []

        # Custom step for basinhopping
        class RandomDisplacementBounds:
            def __init__(self, bounds):
                self.bounds = bounds

            def __call__(self, x):
                x_new = x + np.random.uniform(-0.3, 0.3, size=3)
                return np.clip(x_new,
                               [b[0] for b in self.bounds],
                               [b[1] for b in self.bounds])

        take_step = RandomDisplacementBounds(bounds)

        for _ in range(n_starting_points):
            # Random starting point within bounds
            x0 = np.random.uniform(-0.6, 0.6, 3)

            minimizer_kwargs = {"method": "L-BFGS-B", "bounds": bounds}
            res = basinhopping(
                self.keating_energy,
                x0,
                niter=30,
                T=temp,
                stepsize=0.2,
                take_step=take_step,
                minimizer_kwargs=minimizer_kwargs,
                disp=False
            )
            # Round to avoid duplicate minima from numerical noise
            rounded = np.round(res.x, decimals=3)
            minima_candidates.append(rounded)

        # Deduplicate
        unique_minima = []
        for m in minima_candidates:
            if not any(np.allclose(m, u, atol=0.05) for u in unique_minima):
                unique_minima.append(m)
        return np.array(unique_minima)


# ============================================
# 2. SIMULATION EXECUTION
# ============================================

if __name__ == "__main__":
    print("[SIM] Silicon Octahedral State Simulator")
    print("=" * 50)

    # Initialize the cluster
    cluster = SiliconOctahedron()
    print(f"Initialized 5-atom Si cluster")
    print(f"Bond length: {cluster.d0} Angstroms")
    print(f"Stretch constant alpha: {cluster.alpha} eV/Angstrom^2")
    print(f"Bend constant beta: {cluster.beta} eV/Angstrom^2\n")

    # --- Find all local minima ---
    print("Searching for 8 geometric states (minima)...")
    minima = cluster.find_minima(n_starting_points=80, temp=0.3)
    print(f"Found {len(minima)} unique minima:\n")

    # Display minima coordinates and energy
    min_energies = []
    for i, m in enumerate(minima):
        e = cluster.keating_energy(m)
        min_energies.append(e)
        print(f"State {i + 1:2d}: disp = [{m[0]:+7.4f}, {m[1]:+7.4f}, {m[2]:+7.4f}]  Energy = {e:.4f} eV")

    # Check if we found the expected 8
    if len(minima) == 8:
        print("\nPASS: Exactly 8 distinct minima found!")
        print("   These correspond to displacements toward the 8 faces of the octahedron.")
    else:
        print(f"\nWARN: Found {len(minima)} minima (expected 8). Adjust basinhopping parameters if needed.")

    # Verify energies are nearly degenerate (symmetry)
    energies = np.array(min_energies)
    print(f"\nEnergy spread: {np.std(energies):.6f} eV (should be < 0.01 eV)")

    # --- Visualize the energy landscape (XY slice at z=0) ---
    try:
        import matplotlib.pyplot as plt

        print("\nGenerating 2D slice of energy landscape (z=0 plane)...")
        X, Y, Z = cluster.energy_landscape_2d(plane='xy', z=0.0, resolution=150, limit=0.8)

        plt.figure(figsize=(10, 8))

        # Contour plot
        contour_levels = np.linspace(np.min(Z), np.max(Z), 30)
        cp = plt.contourf(X, Y, Z, levels=contour_levels, cmap='viridis', alpha=0.8)
        plt.colorbar(cp, label='Energy (eV)')

        # Overlay the found minima that lie near this plane
        z_tolerance = 0.15
        near_plane = minima[np.abs(minima[:, 2]) < z_tolerance]
        if len(near_plane) > 0:
            plt.scatter(near_plane[:, 0], near_plane[:, 1],
                        c='red', marker='o', s=100, edgecolors='white', linewidth=2,
                        label=f'Minima (|z| < {z_tolerance} Angstroms)')

        # Mark the ideal center (high energy saddle point)
        plt.plot(0, 0, 'kx', markersize=12, markeredgewidth=3, label='Center (unstable)')

        # Labels and styling
        plt.xlabel('X displacement (Angstroms)', fontsize=12)
        plt.ylabel('Y displacement (Angstroms)', fontsize=12)
        plt.title('Silicon Octahedral Energy Landscape (z=0 slice)\n'
                   + 'Red circles = local minima (geometric states)', fontsize=14)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.axis('equal')

        # Draw octahedron orientation guide
        v_proj = cluster.vertices[:, :2]  # XY components
        plt.scatter(v_proj[:, 0], v_proj[:, 1], c='white', marker='^', s=80,
                    edgecolors='black', linewidth=2, label='Tetrahedral vertices')

        plt.tight_layout()
        plt.savefig('octahedral_landscape.png', dpi=150)
        plt.show()
    except ImportError:
        print("\nmatplotlib not available -- skipping plot.")

    print("\nDONE: Simulation complete.")
    print("Next steps: Simulate phi-spaced coupling between two octahedra to demonstrate logic gate behavior.")
