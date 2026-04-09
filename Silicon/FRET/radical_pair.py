# STATUS: infrastructure -- radical pair magnetic sensing via hyperfine coupling
"""
radical_pair.py – Radical pair mechanism for magnetic field sensing.
Nature's magneto-FRET.
"""

import numpy as np
from scipy.linalg import expm
from scipy.integrate import solve_ivp

class RadicalPair:
    """
    Two unpaired electrons (donor and acceptor radicals) with hyperfine couplings.
    Magnetic field modulates singlet-triplet interconversion.
    """
    def __init__(self, hyperfine_A: np.ndarray, hyperfine_B: np.ndarray, B_field: np.ndarray, k_reaction: float):
        """
        Parameters
        ----------
        hyperfine_A, hyperfine_B : array (3)
            Hyperfine tensors (isotropic approx, in MHz)
        B_field : array (3)
            External magnetic field (mT)
        k_reaction : float
            Reaction rate from singlet state (μs⁻¹)
        """
        self.A = np.array(hyperfine_A)
        self.B_nuc = np.array(hyperfine_B)  # second radical hyperfine
        self.B = np.array(B_field)
        self.k = k_reaction
        self.g_e = 2.0023
        self.mu_B = 1.3996  # MHz/mT

    def hamiltonian(self):
        """Spin Hamiltonian (MHz)."""
        # Electron Zeeman
        H_Z = self.g_e * self.mu_B * np.dot(self.B, self.pauli_vector())
        # Hyperfine coupling (simplified isotropic)
        H_hf = np.dot(self.A, self.pauli_vector()) + np.dot(self.B_nuc, self.pauli_vector())
        return H_Z + H_hf

    def pauli_vector(self):
        """Return [σ_x, σ_y, σ_z] as 4x4 matrices for two spins."""
        sx = np.array([[0,1],[1,0]])
        sy = np.array([[0,-1j],[1j,0]])
        sz = np.array([[1,0],[0,-1]])
        I = np.eye(2)
        # Two-spin operators
        Sx = np.kron(sx, I) + np.kron(I, sx)
        Sy = np.kron(sy, I) + np.kron(I, sy)
        Sz = np.kron(sz, I) + np.kron(I, sz)
        return np.array([Sx, Sy, Sz])

    def singlet_projector(self):
        """Projector onto singlet state |S> = (|↑↓> - |↓↑>)/√2."""
        S = np.zeros((4,4), dtype=complex)
        S[0,0] = S[3,3] = 0.5
        S[0,3] = S[3,0] = -0.5
        S[1,1] = S[2,2] = 0.5
        S[1,2] = S[2,1] = -0.5
        return S

    def singlet_yield(self, t_max: float = 10.0):
        """
        Solve Liouville equation for spin density matrix,
        compute singlet reaction yield.
        """
        H = self.hamiltonian()
        P_S = self.singlet_projector()
        rho0 = P_S / 2  # initial singlet state (normalized)

        def liouville(t, rho_flat):
            rho = rho_flat.reshape(4,4)
            drho = -1j * (H @ rho - rho @ H) - self.k * (P_S @ rho + rho @ P_S) / 2
            return drho.flatten()

        sol = solve_ivp(liouville, [0, t_max], rho0.flatten(), method='BDF')
        rho_final = sol.y[:,-1].reshape(4,4)
        return np.real(np.trace(P_S @ rho_final))

    def magnetic_sensitivity(self, B_range):
        """Compute singlet yield vs magnetic field."""
        yields = []
        B_orig = self.B.copy()
        for B_val in B_range:
            self.B = np.array([0, 0, B_val])
            yields.append(self.singlet_yield())
        self.B = B_orig
        return np.array(yields)
