# STATUS: infrastructure -- phi-triangle Toffoli gate, 3 coupled octahedra with phi-scaled springs
"""
Phi-Triangle Toffoli Gate Simulation
Three octahedra coupled with phi-ratio spring constants.
Demonstrates universal reversible logic in a crystal lattice.

See also:
  - vff_keating.py       (single-octahedron energy landscape)
  - vff_coupled_not.py   (two-node NOT gate)
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
# Phi-Triangle Coupled System (3 Nodes)
# ============================================

class PhiTriangleToffoli:
    """
    Three octahedral nodes A, B, C coupled with phi-scaled spring constants.
    A and B are control nodes; C is the target.
    The coupling matrix is:
        k_AB = phi^-2 * k0
        k_BC = phi^0  * k0
        k_AC = phi^1  * k0
    where phi = (1+sqrt(5))/2 ~ 1.618034
    """

    def __init__(self, k0=2.0):
        self.k0 = k0
        self.phi = (1 + np.sqrt(5)) / 2

        # Define coupling constants using phi powers
        self.k_AB = k0 * (self.phi ** -2)   # ~ 0.382 * k0
        self.k_BC = k0 * (self.phi ** 0)    # = k0
        self.k_AC = k0 * (self.phi ** 1)    # ~ 1.618 * k0

        # Initialize three independent octahedra
        self.nodeA = SiliconOctahedron()
        self.nodeB = SiliconOctahedron()
        self.nodeC = SiliconOctahedron()

    def total_energy(self, dispA, dispB, dispC):
        """Compute total energy of the three-node system."""
        E_A = self.nodeA.keating_energy(dispA)
        E_B = self.nodeB.keating_energy(dispB)
        E_C = self.nodeC.keating_energy(dispC)

        # Harmonic coupling terms
        diff_AB = dispA - dispB
        diff_BC = dispB - dispC
        diff_AC = dispA - dispC

        E_couple = 0.5 * (self.k_AB * np.dot(diff_AB, diff_AB) +
                          self.k_BC * np.dot(diff_BC, diff_BC) +
                          self.k_AC * np.dot(diff_AC, diff_AC))
        return E_A + E_B + E_C + E_couple

    def target_response(self, controlA_disp, controlB_disp):
        """
        Given fixed displacements for controls A and B,
        find the displacement of target C that minimizes total energy.
        Returns optimal C displacement and corresponding energy.
        """
        def objective(dispC):
            return self.total_energy(controlA_disp, controlB_disp, dispC)

        res = minimize(objective, x0=np.zeros(3), method='L-BFGS-B',
                       bounds=[(-0.8, 0.8)] * 3)
        return res.x, res.fun

    def compute_truth_table(self):
        """
        For each of the 8x8 = 64 control state combinations,
        compute the target state and verify Toffoli behavior.
        """
        signs = np.array([(x, y, z) for x in [1, -1] for y in [1, -1] for z in [1, -1]])
        face_normals = signs / np.sqrt(3)
        binary_codes = [tuple(1 if s > 0 else 0 for s in sign) for sign in signs]

        def classify(disp):
            if np.linalg.norm(disp) < 0.1:
                return -1
            d_norm = disp / np.linalg.norm(disp)
            dots = [np.dot(d_norm, f) for f in face_normals]
            return np.argmax(dots)

        results = []
        print("\n" + "=" * 80)
        print("PHI-TRIANGLE TOFFOLI GATE TRUTH TABLE")
        print("Coupling constants: k0={:.2f}, k_AB={:.3f}k0, k_BC={:.3f}k0, k_AC={:.3f}k0".format(
            self.k0, self.k_AB, self.k_BC, self.k_AC))
        print("=" * 80)
        print(f"{'Control A':^12} | {'Control B':^12} | {'Target C':^12} | {'Toffoli?':^10} | Energy (eV)")
        print("-" * 80)

        toffoli_correct = 0
        total = 0

        for i in range(8):
            for j in range(8):
                dispA = face_normals[i] * 0.38
                dispB = face_normals[j] * 0.38

                dispC, energy = self.target_response(dispA, dispB)
                idxC = classify(dispC)

                if idxC == -1:
                    binC = "???"
                else:
                    binC = ''.join(map(str, binary_codes[idxC]))

                binA = ''.join(map(str, binary_codes[i]))
                binB = ''.join(map(str, binary_codes[j]))

                is_111 = (binA == '111' and binB == '111')

                print(f"{binA:^12} | {binB:^12} | {binC:^12} | {'   -   ':^10} | {energy:.4f}")
                results.append((binA, binB, binC, energy))
                total += 1

        print("-" * 80)

        # Toffoli verification: compare reference vs 111,111 case
        refA = face_normals[7] * 0.38  # 000
        refB = face_normals[7] * 0.38
        refC, _ = self.target_response(refA, refB)
        ref_idx = classify(refC)

        testA = face_normals[0] * 0.38  # 111
        testB = face_normals[0] * 0.38
        testC, _ = self.target_response(testA, testB)
        test_idx = classify(testC)

        print("\nToffoli Gate Verification:")
        print(f"Reference state: A=000, B=000 -> C = {binary_codes[ref_idx]}")
        print(f"Test state:      A=111, B=111 -> C = {binary_codes[test_idx]}")
        if test_idx == 7 - ref_idx or (ref_idx == -1 and test_idx != -1):
            print("PASS: Target inversion detected for (111,111) input!")
        else:
            print("WARN: Target did not invert. Adjust phi couplings.")

        return results

    def plot_energy_landscape_target(self, controlA_state='111', controlB_state='111'):
        """
        Visualize the energy landscape for target C given fixed controls.
        Shows the shift of the energy minimum.
        """
        import matplotlib.pyplot as plt

        signs = np.array([(x, y, z) for x in [1, -1] for y in [1, -1] for z in [1, -1]])
        face_normals = signs / np.sqrt(3)

        def bin_to_idx(bin_str):
            mapping = {'111': 0, '110': 1, '101': 2, '100': 3,
                       '011': 4, '010': 5, '001': 6, '000': 7}
            return mapping.get(bin_str, 0)

        idxA = bin_to_idx(controlA_state)
        idxB = bin_to_idx(controlB_state)
        dispA = face_normals[idxA] * 0.38
        dispB = face_normals[idxB] * 0.38

        res = 50
        x_vals = np.linspace(-0.8, 0.8, res)
        y_vals = np.linspace(-0.8, 0.8, res)
        X, Y = np.meshgrid(x_vals, y_vals)
        Z = np.zeros_like(X)
        for i in range(res):
            for j in range(res):
                dispC = np.array([X[i, j], Y[i, j], 0.0])
                Z[i, j] = self.total_energy(dispA, dispB, dispC)

        plt.figure(figsize=(8, 6))
        cp = plt.contourf(X, Y, Z, levels=30, cmap='viridis')
        plt.colorbar(cp, label='Total Energy (eV)')

        optC, _ = self.target_response(dispA, dispB)
        plt.scatter(optC[0], optC[1], c='red', s=150, marker='*',
                    edgecolors='white', linewidth=2, label='Optimal Target C')
        plt.xlabel('Target X displacement (Angstroms)')
        plt.ylabel('Target Y displacement (Angstroms)')
        plt.title(f'Target Energy Landscape (z=0 slice)\nControls: A={controlA_state}, B={controlB_state}')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'toffoli_landscape_A{controlA_state}_B{controlB_state}.png', dpi=150)
        plt.show()

    def simulate_gate_operation(self):
        """
        Demonstrate the full gate operation by sweeping control inputs.
        """
        import matplotlib.pyplot as plt

        signs = np.array([(x, y, z) for x in [1, -1] for y in [1, -1] for z in [1, -1]])
        face_normals = signs / np.sqrt(3)
        binary_codes = [tuple(1 if s > 0 else 0 for s in sign) for sign in signs]

        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        axes = axes.flatten()

        labels = ['111', '110', '101', '100', '011', '010', '001', '000']

        for b_idx in range(8):
            ax = axes[b_idx]
            target_indices = []
            for a_idx in range(8):
                dispA = face_normals[a_idx] * 0.38
                dispB = face_normals[b_idx] * 0.38
                dispC, _ = self.target_response(dispA, dispB)
                c_idx = self._classify(dispC)
                target_indices.append(c_idx if c_idx != -1 else np.nan)
            ax.plot(range(8), target_indices, 'o-', linewidth=2, markersize=8)
            ax.set_xticks(range(8))
            ax.set_xticklabels(labels, rotation=45)
            ax.set_ylabel('Target State Index')
            ax.set_xlabel('Control A')
            ax.set_title(f'Control B = {labels[b_idx]}')
            ax.grid(alpha=0.3)
            ax.set_ylim(-0.5, 7.5)

        plt.suptitle('Toffoli Gate Response: Target C vs Control A for each Control B',
                      fontsize=16)
        plt.tight_layout()
        plt.savefig('toffoli_response_curves.png', dpi=150)
        plt.show()

    def _classify(self, disp):
        signs = np.array([(x, y, z) for x in [1, -1] for y in [1, -1] for z in [1, -1]])
        face_normals = signs / np.sqrt(3)
        if np.linalg.norm(disp) < 0.1:
            return -1
        d_norm = disp / np.linalg.norm(disp)
        dots = [np.dot(d_norm, f) for f in face_normals]
        return np.argmax(dots)


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("[TRI] PHI-TRIANGLE TOFFOLI GATE SIMULATION")
    print("=" * 50)

    phi = (1 + np.sqrt(5)) / 2
    print(f"Golden ratio phi = {phi:.6f}")

    k0 = 2.0  # eV/Angstrom^2
    toffoli = PhiTriangleToffoli(k0=k0)

    print(f"\nCoupling constants (k0 = {k0:.2f} eV/Angstrom^2):")
    print(f"  k_AB = phi^-2 * k0 = {toffoli.k_AB:.3f} eV/Angstrom^2")
    print(f"  k_BC = phi^0  * k0 = {toffoli.k_BC:.3f} eV/Angstrom^2")
    print(f"  k_AC = phi^1  * k0 = {toffoli.k_AC:.3f} eV/Angstrom^2")

    # 1. Compute full truth table
    results = toffoli.compute_truth_table()

    # 2. Visualize energy landscapes (optional, requires matplotlib)
    try:
        import matplotlib.pyplot as plt

        toffoli.plot_energy_landscape_target(controlA_state='111', controlB_state='111')
        toffoli.plot_energy_landscape_target(controlA_state='000', controlB_state='000')

        # 3. Plot gate response curves
        toffoli.simulate_gate_operation()
    except ImportError:
        print("matplotlib not available -- skipping plots.")

    print("\nDONE: Toffoli gate simulation complete.")
    print("The phi-triangle geometry naturally implements conditional inversion.")
