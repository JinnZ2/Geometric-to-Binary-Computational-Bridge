# gies_encoder.py
# Geometric Information Encoding System (GIES) — Silicon-level reference
# OctahedralState, GeometricEncoder, StateTensor
# Extracted from Silicon/GIES.md

import numpy as np


# ---------------------------
# Octahedral State
# ---------------------------

class OctahedralState:
    """Represents a single octahedral geometric state (8 vertices = 3 bits)."""

    POSITIONS = {
        0: (0.25, 0.25, 0.25),
        1: (0.25, -0.25, 0.25),
        2: (-0.25, 0.25, 0.25),
        3: (-0.25, -0.25, 0.25),
        4: (0.25, 0.25, -0.25),
        5: (0.25, -0.25, -0.25),
        6: (-0.25, 0.25, -0.25),
        7: (-0.25, -0.25, -0.25),
    }

    def __init__(self, index):
        if not 0 <= index <= 7:
            raise ValueError("Index must be 0-7")
        self.index = index
        self.position = np.array(self.POSITIONS[index])

    def to_binary(self, width=3):
        """Convert to binary representation."""
        return format(self.index, f"0{width}b")

    def to_token(self, operator="|", symbol="O"):
        """Convert to geometric token notation."""
        return f"{self.to_binary()}{operator}{symbol}"

    @classmethod
    def from_token(cls, token):
        """Parse token back to state."""
        if "|" not in token:
            raise ValueError("Token must contain '|' operator")
        binary = token.split("|")[0]
        return cls(int(binary, 2))

    def __repr__(self):
        return f"OctahedralState({self.index}, pos={self.position})"


# ---------------------------
# Geometric Encoder
# ---------------------------

class GeometricEncoder:
    """Bidirectional encoder between geometric tokens and binary."""

    SYMBOL_MAP = {"O": "00", "I": "01", "X": "10", "\u0394": "11"}
    REVERSE_MAP = {v: k for k, v in SYMBOL_MAP.items()}

    OPERATOR_MAP = {"|": "1", "/": "0"}
    REVERSE_OPERATOR = {v: k for k, v in OPERATOR_MAP.items()}

    def encode_to_binary(self, token, width=3):
        """
        Convert geometric token to flat binary.
        Example: '001|O' -> '00110'
        """
        for op in ["|", "/"]:
            if op in token:
                parts = token.split(op, 1)
                vertex_bits = parts[0]
                symbol = parts[1][0] if parts[1] else "O"
                operator = op
                break
        else:
            raise ValueError("Token must contain operator ('|' or '/')")

        if len(vertex_bits) != width:
            raise ValueError(f"Vertex bits must be {width} bits wide")

        operator_bit = self.OPERATOR_MAP.get(operator, "1")
        symbol_bits = self.SYMBOL_MAP.get(symbol, "00")
        return vertex_bits + operator_bit + symbol_bits

    def decode_from_binary(self, binary_string, width=3):
        """
        Convert flat binary back to geometric token.
        Example: '00110' -> '001|O'
        """
        expected_length = width + 3
        if len(binary_string) < expected_length:
            raise ValueError(f"Binary string too short (need {expected_length} bits)")

        vertex_bits = binary_string[:width]
        operator_bit = binary_string[width]
        symbol_bits = binary_string[width + 1 : width + 3]

        operator = self.REVERSE_OPERATOR.get(operator_bit, "|")
        symbol = self.REVERSE_MAP.get(symbol_bits, "O")
        return f"{vertex_bits}{operator}{symbol}"

    def validate_token(self, token):
        """Verify token round-trips correctly."""
        try:
            binary = self.encode_to_binary(token)
            decoded = self.decode_from_binary(binary)
            return decoded == token
        except Exception:
            return False


# ---------------------------
# State Tensor
# ---------------------------

class StateTensor:
    """Calculate and manipulate state tensors."""

    def __init__(self, state: OctahedralState):
        self.state = state
        self.vector = state.position
        self.tensor = self._calculate_tensor()

    def _calculate_tensor(self):
        """Symmetric rank-2 tensor from state vector: T = v (x) v."""
        return np.outer(self.vector, self.vector)

    def project(self, direction):
        """Project tensor along a direction (the | operator). Returns scalar."""
        n = np.array(direction, dtype=float)
        n = n / np.linalg.norm(n)
        return n @ self.tensor @ n

    def eigenvalues(self):
        return np.linalg.eigvalsh(self.tensor)

    def eigenvectors(self):
        return np.linalg.eigh(self.tensor)

    def trace(self):
        return np.trace(self.tensor)

    def determinant(self):
        return np.linalg.det(self.tensor)


# ---------------------------
# Example
# ---------------------------

if __name__ == "__main__":
    print("=== GIES Encoder Demo ===\n")

    # State round-trip
    s = OctahedralState(5)
    token = s.to_token()
    print(f"State 5 -> token: {token}")
    s2 = OctahedralState.from_token(token)
    print(f"Token -> state:   {s2}\n")

    # Encoder round-trip
    enc = GeometricEncoder()
    for tok in ["001|O", "110/X", "000|I", "111|\u0394"]:
        binary = enc.encode_to_binary(tok)
        back = enc.decode_from_binary(binary)
        ok = "OK" if back == tok else "FAIL"
        print(f"  {tok} -> {binary} -> {back}  [{ok}]")

    # Tensor
    print("\nState Tensor for state 3:")
    st = StateTensor(OctahedralState(3))
    print(f"  Tensor:\n{st.tensor}")
    print(f"  Eigenvalues: {st.eigenvalues()}")
    print(f"  Trace: {st.trace():.4f}")
    print(f"  Projection along [1,0,0]: {st.project([1, 0, 0]):.4f}")
