# STATUS: infrastructure -- octahedral node with strain-spin cross-talk
"""
Tensor-Constrained Octahedral Encoder (JSON Specification)
Implements the formal 8-state encoding with eigenvalue constraints.

Companion to :mod:`Silicon.lattice.multi_bridge`: defines the JSON-spec
tensor encoder used to drive ``MultiBridgeNode`` through its 8 discrete
octahedral states.
"""

import numpy as np

from Silicon.lattice.multi_bridge import MultiBridgeNode

class TensorOctahedronEncoder:
    """
    Encodes 3 bits into an octahedral strain tensor with trace conservation.
    Conforms to the Octahedral_State_Encoder JSON specification v1.0.
    """

    # Encoding map from JSON (3-bit → geometric description)
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

    # Canonical tensor patterns for each state (eigenvalues λ₁,λ₂,λ₃ with Σλ=1)
    # Derived from the JSON descriptions and octahedral symmetry
    EIGENVALUE_PATTERNS = {
        (0,0,0): np.array([0.6, 0.3, 0.1]),  # λ₁ dominant
        (0,0,1): np.array([0.3, 0.6, 0.1]),  # λ₂ dominant
        (0,1,0): np.array([0.45, 0.45, 0.1]), # strain aligned (equal λ₁,λ₂)
        (0,1,1): np.array([0.45, 0.1, 0.45]), # compressive alignment
        (1,0,0): np.array([0.1, 0.45, 0.45]), # conductive bias
        (1,0,1): np.array([0.1, 0.6, 0.3]),   # magnetic bias (λ₂>λ₃)
        (1,1,0): np.array([0.33, 0.33, 0.34]), # axial symmetry (nearly equal)
        (1,1,1): np.array([1/3, 1/3, 1/3])     # stable equilibrium (isotropic)
    }

    # Basis vectors for each state (orthonormal, aᵢ·aⱼ = δᵢⱼ)
    # These align with the octahedral face normals.
    @staticmethod
    def get_basis_vectors(state_bits):
        """
        Return orthonormal basis (a₁,a₂,a₃) for the given 3-bit state.
        Derived from tetrahedral symmetry and octahedral face orientations.
        """
        # The 8 states correspond to the 8 face normals (±1,±1,±1)/√3
        signs = np.array([(1 if b else -1) for b in state_bits])
        # Primary axis aligns with face normal
        a1 = signs / np.sqrt(3)
        # Construct orthonormal basis using Gram-Schmidt
        # Choose a2 perpendicular to a1, a3 = a1 × a2
        if abs(a1[0]) < 0.9:
            v2 = np.array([1,0,0])
        else:
            v2 = np.array([0,1,0])
        a2 = v2 - np.dot(v2, a1) * a1
        a2 /= np.linalg.norm(a2)
        a3 = np.cross(a1, a2)
        return a1, a2, a3

    def __init__(self):
        self.current_state_bits = (0,0,0)  # default
        self.current_tensor = None
        self._update_tensor()

    def encode(self, bits):
        """
        Encode 3 bits into a strain tensor and basis vectors.
        Returns a dictionary with the full tensor representation.
        """
        bits = tuple(bits)
        if bits not in self.STATE_MAP:
            raise ValueError(f"Invalid state: {bits}. Must be 3-bit tuple.")
        self.current_state_bits = bits
        self._update_tensor()
        return self.get_tensor_representation()

    def _update_tensor(self):
        """Construct the 3x3 strain tensor from eigenvalues and basis."""
        lambdas = self.EIGENVALUE_PATTERNS[self.current_state_bits]
        a1, a2, a3 = self.get_basis_vectors(self.current_state_bits)
        # Tensor = Σ λᵢ (aᵢ ⊗ aᵢ)
        tensor = (lambdas[0] * np.outer(a1, a1) +
                  lambdas[1] * np.outer(a2, a2) +
                  lambdas[2] * np.outer(a3, a3))
        # Ensure trace = 1 (numerical tolerance)
        tensor /= np.trace(tensor)
        self.current_tensor = tensor

    def get_tensor_representation(self):
        """Return the full tensor definition per JSON spec."""
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

    def decode_tensor(self, tensor, method='eigen'):
        """
        Given a 3x3 strain tensor, determine the closest 3-bit state.
        Uses eigenvalue pattern matching.
        """
        # Ensure tensor is symmetric and normalized trace=1
        tensor = (tensor + tensor.T) / 2
        tensor /= np.trace(tensor)
        # Compute eigenvalues
        evals, evecs = np.linalg.eigh(tensor)
        # Sort descending
        idx = np.argsort(evals)[::-1]
        evals = evals[idx]
        # Find closest pattern by Euclidean distance
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

    def zeeman_energy(self, B_field, M_tensor=None):
        """
        Magnetic read/write interface as per JSON:
        E_mag = -M : B_ext
        where M is the magnetization tensor coupled to strain.
        Simplified: M = χ * strain_tensor · B
        """
        if M_tensor is None:
            # Assume magnetostrictive coupling: M_ij = χ_ijkl ε_kl B_l
            # Simplified: M is proportional to strain tensor dotted with B
            chi = 1e-3  # susceptibility scaling
            M = chi * np.dot(self.current_tensor, B_field)
        else:
            M = M_tensor
        # Energy = - M · B (contraction)
        E = -np.dot(M, B_field)
        return E

    def to_displacement_field(self, scale=0.5):
        """
        Convert tensor to approximate central atom displacement.
        For integration with SiliconOctahedron model.
        Displacement vector ≈ scale * (principal axis of tensor).
        """
        evals, evecs = np.linalg.eigh(self.current_tensor)
        # Displacement along dominant eigenvector
        dominant_idx = np.argmax(evals)
        direction = evecs[:, dominant_idx]
        magnitude = scale * evals[dominant_idx]
        return direction * magnitude

# ============================================================
# INTEGRATION WITH MULTI-BRIDGE NODE
# ============================================================
class JSONCompatibleMultiBridgeNode(MultiBridgeNode):
    """
    Extends MultiBridgeNode with the JSON tensor encoder interface.
    """
    def __init__(self):
        super().__init__()
        self.encoder = TensorOctahedronEncoder()

    def set_state_from_bits(self, bits):
        """Set node to the specified 3-bit state."""
        self.encoder.encode(bits)
        # Convert tensor to displacement for strain model
        disp = self.encoder.to_displacement_field(scale=0.4)
        self.displacement = disp
        # Optionally align spin state with magnetic bias
        # For states with "magnetic bias", set spin accordingly
        if bits == (1,0,1):
            self.spin_state = 1
        else:
            self.spin_state = 0
        # Relax to find equilibrium displacement
        self.relax()

    def get_current_bits(self):
        """Decode current displacement to 3-bit state."""
        # Approximate tensor from displacement
        strain_tensor = self.strain.strain_tensor_from_displacement(self.displacement)
        return self.encoder.decode_tensor(strain_tensor)

    def relax(self):
        """Override to incorporate tensor constraints during relaxation."""
        # Simple gradient descent to minimize total energy
        disp = self.displacement.copy()
        for _ in range(20):
            grad = self._energy_gradient(disp)
            disp -= 0.05 * grad
        self.displacement = disp

    def _energy_gradient(self, disp):
        """Numerical gradient of total energy w.r.t displacement."""
        eps = 1e-5
        grad = np.zeros(3)
        E0 = self.total_energy(disp, self.spin_state, self.optical_excited,
                               self.B_field, self.E_field)
        for i in range(3):
            d_eps = disp.copy()
            d_eps[i] += eps
            E_eps = self.total_energy(d_eps, self.spin_state, self.optical_excited,
                                      self.B_field, self.E_field)
            grad[i] = (E_eps - E0) / eps
        return grad

# ============================================================
# DEMONSTRATION OF JSON ENCODER
# ============================================================
def demo_json_encoder():
    print("="*70)
    print("JSON OCTAHEDRAL ENCODER DEMONSTRATION")
    print("="*70)

    encoder = TensorOctahedronEncoder()

    # Enumerate all 8 states per JSON spec
    print("\n1. Encoding all 8 states:")
    for bits in [(0,0,0),(0,0,1),(0,1,0),(0,1,1),(1,0,0),(1,0,1),(1,1,0),(1,1,1)]:
        rep = encoder.encode(bits)
        print(f"  {bits} → {rep['description'][:30]}... Trace={rep['trace']:.3f}")

    # Test decode
    print("\n2. Tensor decode test:")
    test_tensor = encoder.current_tensor  # from last state (111)
    decoded = encoder.decode_tensor(test_tensor)
    print(f"  Decoded tensor → {decoded} (expected {encoder.current_state_bits})")

    # Test Zeeman interface
    print("\n3. Magnetic read/write interface:")
    B = np.array([0.0, 0.0, 0.1])  # 0.1 T along z
    encoder.encode((1,0,1))  # magnetic bias state
    E_mag = encoder.zeeman_energy(B)
    print(f"  State {encoder.current_state_bits}: Zeeman energy = {E_mag:.6f} eV at B={B} T")

    # Test integration with multi-bridge node
    print("\n4. Integration with MultiBridgeNode:")
    node = JSONCompatibleMultiBridgeNode()
    node.set_state_from_bits((1,1,0))  # axial symmetry state
    bits = node.get_current_bits()
    print(f"  Set state (1,1,0), decoded as {bits}")
    print(f"  Displacement: {node.displacement}")

# Run if executed directly
if __name__ == "__main__":
    demo_json_encoder()
