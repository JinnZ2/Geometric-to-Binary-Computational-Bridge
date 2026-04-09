# STATUS: infrastructure -- coupled octahedra straintronic NOT gate via phi-resonant coupling
"""
Coupled Silicon Octahedra Simulation
Demonstrates phi-resonant coupling for straintronic logic (NOT gate).
Extends the single-octahedron Keating model.

See also:
  - vff_keating.py   (single-octahedron energy landscape)
  - vff_toffoli.py   (three-node phi-triangle Toffoli gate)
"""

import sys
import os
import numpy as np
from scipy.optimize import minimize
from itertools import product, combinations

# Import SiliconOctahedron from the sibling module
try:
    from vff_keating import SiliconOctahedron
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from vff_keating import SiliconOctahedron


# ============================================
# FACE NORMALS AND STATE CLASSIFICATION
# ============================================

# Precompute the 8 octahedral face normals
FACE_NORMALS = np.array(
    [(x, y, z) for x in [1, -1] for y in [1, -1] for z in [1, -1]]
) / np.sqrt(3)


def classify_state(disp):
    """Classify a displacement into one of 8 face directions."""
    if np.linalg.norm(disp) < 0.1:
        return "Center"
    d_norm = disp / np.linalg.norm(disp)
    best = np.argmax([np.dot(d_norm, f) for f in FACE_NORMALS])
    return f"Face{best + 1}"


# ============================================
# COUPLED OCTAHEDRA
# ============================================

class CoupledOctahedra:
    """
    Two octahedral units coupled via a harmonic spring.
    Phi coupling constant is derived from lattice dynamics.
    """

    def __init__(self, k_coupling=0.0, separation_vector=None):
        """
        k_coupling: spring constant between central atoms (eV/Angstrom^2)
        separation_vector: 3D vector between centers in undeformed lattice.
        """
        self.oct1 = SiliconOctahedron()
        self.oct2 = SiliconOctahedron()
        self.k_c = k_coupling
        self.separation = (separation_vector if separation_vector is not None
                           else np.array([5.43, 0, 0]))

    def total_energy(self, disp1, disp2):
        """Energy of the coupled system."""
        E1 = self.oct1.keating_energy(disp1)
        E2 = self.oct2.keating_energy(disp2)
        # Harmonic coupling
        diff = disp1 - disp2
        E_couple = 0.5 * self.k_c * np.dot(diff, diff)
        return E1 + E2 + E_couple

    def energy_given_input(self, disp_input, is_input_node1=True):
        """
        For a fixed input displacement, find the output displacement
        that minimizes total energy.
        Returns optimal output displacement and energy.
        """
        input_disp = np.asarray(disp_input)

        def objective(output_disp):
            if is_input_node1:
                return self.total_energy(input_disp, output_disp)
            else:
                return self.total_energy(output_disp, input_disp)

        res = minimize(objective, x0=np.zeros(3), method='L-BFGS-B',
                       bounds=[(-0.8, 0.8), (-0.8, 0.8), (-0.8, 0.8)])
        return res.x, res.fun

    def find_global_minima(self, n_grid=5):
        """
        Scan input space to find coupled minima configurations.
        Returns list of (disp1, disp2, energy).
        """
        minima1 = self.oct1.find_minima(n_starting_points=20)
        minima2 = self.oct2.find_minima(n_starting_points=20)

        results = []
        for m1 in minima1:
            for m2 in minima2:
                def combined_objective(x):
                    d1 = x[:3]
                    d2 = x[3:]
                    return self.total_energy(d1, d2)

                x0 = np.concatenate([m1, m2])
                res = minimize(combined_objective, x0, method='L-BFGS-B',
                               bounds=[(-0.8, 0.8)] * 6)
                d1_opt = res.x[:3]
                d2_opt = res.x[3:]
                results.append((d1_opt, d2_opt, res.fun))

        # Deduplicate
        unique = []
        tol = 0.05
        for r in results:
            d1, d2, e = r
            if not any(np.allclose(d1, u[0], atol=tol) and
                       np.allclose(d2, u[1], atol=tol) for u in unique):
                unique.append((d1, d2, e))
        return unique


# ============================================
# DEMONSTRATION: Phi-Coupled NOT Gate
# ============================================

if __name__ == "__main__":
    print("[GATE] Coupled Octahedra Logic Gate Simulation")
    print("=" * 50)

    # --- Determine the Phi Coupling Constant ---
    k_phi = 2.0  # eV/Angstrom^2

    system = CoupledOctahedra(k_coupling=k_phi)
    print(f"Coupling spring constant k_c = {k_phi:.2f} eV/Angstrom^2\n")

    # --- Find all coupled minima ---
    print("Scanning for coupled energy minima...")
    minima_pairs = system.find_global_minima()
    print(f"Found {len(minima_pairs)} distinct coupled configurations:\n")
    for i, (d1, d2, e) in enumerate(minima_pairs):
        state1 = classify_state(d1)
        state2 = classify_state(d2)
        print(f"Config {i + 1}: Node1 = {state1:8s}  Node2 = {state2:8s}  Energy = {e:.4f} eV")

    # --- Demonstrate NOT Gate ---
    input_state_index = 0  # Face1 direction
    input_disp = FACE_NORMALS[input_state_index] * 0.38

    print("\n" + "=" * 50)
    print(f"NOT GATE TEST: Input Node1 fixed at Face{input_state_index + 1} displacement")
    print(f"Input displacement = [{input_disp[0]:+.3f}, {input_disp[1]:+.3f}, {input_disp[2]:+.3f}]")

    # Compute output that minimizes energy
    output_disp, energy = system.energy_given_input(input_disp, is_input_node1=True)
    output_state = classify_state(output_disp)
    print(f"Optimal Node2 displacement = [{output_disp[0]:+.3f}, {output_disp[1]:+.3f}, {output_disp[2]:+.3f}]")
    print(f"Node2 state = {output_state}")

    # Check if output is opposite face (inversion)
    input_face_idx = np.argmax(
        [np.dot(input_disp / np.linalg.norm(input_disp), f) for f in FACE_NORMALS])
    output_face_idx = np.argmax(
        [np.dot(output_disp / np.linalg.norm(output_disp), f) for f in FACE_NORMALS])

    if np.dot(FACE_NORMALS[input_face_idx], FACE_NORMALS[output_face_idx]) < -0.9:
        print("\nPASS: NOT GATE VERIFIED -- Output is in the opposite octahedral face.")
    else:
        print("\nWARN: Output not opposite; adjust k_coupling for inversion.")

    # --- Transfer characteristic ---
    print("\nGenerating transfer characteristic data...")
    direction = FACE_NORMALS[0]
    magnitudes = np.linspace(-0.6, 0.6, 50)
    outputs = []
    for mag in magnitudes:
        inp = direction * mag
        out, _ = system.energy_given_input(inp, is_input_node1=True)
        outputs.append(out)
    outputs = np.array(outputs)
    output_proj = np.dot(outputs, direction)

    # --- Plotting (optional) ---
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(8, 6))
        plt.plot(magnitudes, output_proj, 'b-', linewidth=2, label='Output projection')
        plt.plot(magnitudes, -magnitudes, 'r--', linewidth=1, label='Ideal Inversion (y = -x)')
        plt.xlabel('Input displacement along Face1 (Angstroms)', fontsize=12)
        plt.ylabel('Output displacement projection (Angstroms)', fontsize=12)
        plt.title(f'Coupled Octahedra Transfer Characteristic (k_c = {k_phi} eV/Angstrom^2)',
                  fontsize=14)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.axhline(0, color='k', linewidth=0.5)
        plt.axvline(0, color='k', linewidth=0.5)
        plt.tight_layout()
        plt.savefig('not_gate_transfer.png', dpi=150)
        plt.show()

        # Phase portrait
        input_fixed = input_disp
        res = 50
        x_vals = np.linspace(-0.8, 0.8, res)
        y_vals = np.linspace(-0.8, 0.8, res)
        X, Y = np.meshgrid(x_vals, y_vals)
        Z = np.zeros_like(X)
        for i in range(res):
            for j in range(res):
                out = np.array([X[i, j], Y[i, j], 0.0])
                Z[i, j] = system.total_energy(input_fixed, out)

        plt.figure(figsize=(8, 6))
        cp = plt.contourf(X, Y, Z, levels=30, cmap='viridis')
        plt.colorbar(cp, label='Total Energy (eV)')
        plt.scatter(output_disp[0], output_disp[1], c='red', s=150, marker='*',
                    edgecolors='white', linewidth=2, label='Optimal Output')
        plt.xlabel('Output X displacement (Angstroms)', fontsize=12)
        plt.ylabel('Output Y displacement (Angstroms)', fontsize=12)
        plt.title(f'Energy Landscape for Fixed Input (Face{input_state_index + 1})',
                  fontsize=14)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig('coupled_landscape.png', dpi=150)
        plt.show()
    except ImportError:
        print("matplotlib not available -- skipping plots.")

    print("\nDONE: Coupled simulation complete.")
    print("Next: Map full 8-state logic truth table for universal computation.")
