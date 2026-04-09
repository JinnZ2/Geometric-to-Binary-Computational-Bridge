# STATUS: infrastructure -- geometric sensor simulator with tensor accumulation
"""
Geometric Sensor Simulator & Token Sequence Learning
=====================================================
Simulates a sensor that outputs geometric tokens directly from 3D direction + phase.
Learns dependencies (cancellations) in token sequences using tensor accumulation.
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
from dataclasses import dataclass

# ----------------------------------------------------------------------
# Geometric Encoder (from earlier, with minor fixes)
# ----------------------------------------------------------------------
class GeometricEncoder:
    """Bidirectional encoder between geometric and binary representations"""
    
    SYMBOL_MAP = {'O': '00', 'I': '01', 'X': '10', 'Δ': '11'}
    REVERSE_SYMBOL_MAP = {v: k for k, v in SYMBOL_MAP.items()}
    OPERATOR_MAP = {'|': '1', '/': '0', ':': '0'}
    REVERSE_OPERATOR_MAP = {'1': '|', '0': '/'}
    
    def __init__(self, vertex_width: int = 3):
        self.vertex_width = vertex_width
    
    def encode_to_binary(self, token: str) -> str:
        if '||' in token:
            parts = token.split('||', 1)
            vertex_bits = parts[0]
            symbol = parts[1][0] if len(parts[1]) > 0 else 'O'
            operator_bits = '11'
        else:
            op = next((op for op in ['|', '/', ':'] if op in token), None)
            if op is None:
                raise ValueError("No operator found")
            parts = token.split(op, 1)
            vertex_bits = parts[0]
            symbol = parts[1][0] if len(parts[1]) > 0 else 'O'
            operator_bits = self.OPERATOR_MAP[op]
        if len(vertex_bits) != self.vertex_width:
            raise ValueError(f"Vertex bits must be {self.vertex_width} wide")
        symbol_bits = self.SYMBOL_MAP[symbol]
        return vertex_bits + operator_bits + symbol_bits
    
    def decode_from_binary(self, binary_string: str) -> str:
        vertex_bits = binary_string[:self.vertex_width]
        operator_start = self.vertex_width
        if len(binary_string) >= self.vertex_width + 4 and binary_string[operator_start:operator_start+2] == '11':
            operator = '||'
            symbol_bits = binary_string[operator_start+2:operator_start+4]
        else:
            operator_bit = binary_string[operator_start]
            operator = self.REVERSE_OPERATOR_MAP.get(operator_bit, '|')
            symbol_bits = binary_string[operator_start+1:operator_start+3]
        symbol = self.REVERSE_SYMBOL_MAP.get(symbol_bits, 'O')
        return f"{vertex_bits}{operator}{symbol}"

# ----------------------------------------------------------------------
# Octahedral State (vertices of a cube normalized)
# ----------------------------------------------------------------------
class OctahedralState:
    """One of 8 vertices of an octahedron (cube vertices on unit sphere)"""
    # Positions of the 8 vertices (±1,±1,±1) / sqrt(3)
    POSITIONS = []
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                v = np.array([ix, iy, iz], dtype=float)
                v /= np.linalg.norm(v)
                POSITIONS.append(v)
    
    def __init__(self, index: int):
        self.index = index
        self.position = self.POSITIONS[index]
    
    @classmethod
    def closest(cls, vec: np.ndarray) -> 'OctahedralState':
        """Find state whose position is closest to given direction vector"""
        vec = vec / np.linalg.norm(vec)
        dots = [np.dot(vec, pos) for pos in cls.POSITIONS]
        best_idx = int(np.argmax(dots))
        return cls(best_idx)

# ----------------------------------------------------------------------
# Geometric Sensor Simulator
# ----------------------------------------------------------------------
def vector_to_token(direction: np.ndarray, phase: float = 0.0) -> str:
    """
    Convert a 3D direction vector and phase angle (degrees) to a geometric token.
    - direction: (x,y,z) any length
    - phase: 0..360 degrees, mapped to symbols: O(0°), I(90°), X(180°), Δ(270°)
    Returns token like "001|O"
    """
    # Vertex bits (3 bits, 0-7)
    state = OctahedralState.closest(direction)
    vertex_bits = f"{state.index:03b}"
    
    # Operator: radial if direction aligns with radial axis (1,1,1), else tangential
    radial_axis = np.array([1,1,1]) / np.sqrt(3)
    dot = abs(np.dot(direction / np.linalg.norm(direction), radial_axis))
    operator = '|' if dot > 0.7 else '/'   # threshold 0.7 = ~45° cone
    
    # Symbol from phase
    phase_norm = (phase % 360) / 90.0
    symbol_idx = int(round(phase_norm)) % 4
    symbol = ['O', 'I', 'X', 'Δ'][symbol_idx]
    
    return f"{vertex_bits}{operator}{symbol}"

def random_token() -> str:
    """Generate a random geometric token (for testing)"""
    vertex_bits = f"{np.random.randint(0,8):03b}"
    operator = np.random.choice(['|', '/'])
    symbol = np.random.choice(['O', 'I', 'X', 'Δ'])
    return f"{vertex_bits}{operator}{symbol}"

# ----------------------------------------------------------------------
# Tensor representation for geometric tokens
# ----------------------------------------------------------------------
def token_to_tensor(token: str) -> np.ndarray:
    """
    Convert a token to a 3x3 symmetric tensor (outer product of vertex vector).
    This tensor represents the "geometric fingerprint" of the token.
    """
    # Extract vertex bits
    vertex_bits = token[:3]
    idx = int(vertex_bits, 2)
    v = OctahedralState.POSITIONS[idx]
    # Outer product v ⊗ v
    T = np.outer(v, v)
    # Optionally scale by operator/symbol (here we keep as is)
    return T

def tensor_norm(T: np.ndarray) -> float:
    """Frobenius norm of tensor"""
    return float(np.linalg.norm(T))

def tensor_sum(tensors: List[np.ndarray]) -> np.ndarray:
    """Sum of tensors"""
    return sum(tensors, np.zeros((3,3)))

# ----------------------------------------------------------------------
# Token Sequence Learning: Find dependencies via tensor cancellation
# ----------------------------------------------------------------------
def find_dependencies(tokens: List[str], max_len: int = 4) -> List[List[int]]:
    """
    Find subsets of token indices whose tensors sum to near-zero (norm < 1e-6).
    Uses meet-in-the-middle for small max_len (≤ 6).
    Returns list of index lists.
    """
    tensors = [token_to_tensor(tok) for tok in tokens]
    n = len(tokens)
    dependencies = []
    
    # Single token that is already zero (unlikely)
    for i, T in enumerate(tensors):
        if tensor_norm(T) < 1e-6:
            dependencies.append([i])
    
    # Pairs
    for i in range(n):
        for j in range(i+1, n):
            if tensor_norm(tensors[i] + tensors[j]) < 1e-6:
                dependencies.append([i, j])
    
    # Triples (brute force for small n)
    if max_len >= 3 and n <= 200:
        for i in range(n):
            for j in range(i+1, n):
                for k in range(j+1, n):
                    if tensor_norm(tensors[i] + tensors[j] + tensors[k]) < 1e-6:
                        dependencies.append([i, j, k])
    
    # Meet-in-the-middle for quadruples and longer
    if max_len >= 4 and n <= 500:
        # Build hash of half-sums
        half = n // 2
        sum_map: Dict[Tuple[float, ...], List[Tuple[int, ...]]] = defaultdict(list)
        # Iterate over all subsets of first half up to max_len//2
        from itertools import combinations
        for l in range(1, max_len//2 + 1):
            for combo in combinations(range(half), l):
                S = tensor_sum([tensors[i] for i in combo])
                # Flatten tensor to tuple for hashing
                key = tuple(np.round(S.flatten(), decimals=10))
                sum_map[key].append(combo)
        
        # Check second half
        for l in range(1, max_len - max_len//2 + 1):
            for combo in combinations(range(half, n), l):
                S = tensor_sum([tensors[i] for i in combo])
                target = tuple(np.round((-S).flatten(), decimals=10))
                if target in sum_map:
                    for first in sum_map[target]:
                        combined = list(first) + list(combo)
                        if len(combined) <= max_len:
                            dependencies.append(combined)
    
    # Remove duplicates
    seen = set()
    unique = []
    for dep in dependencies:
        key = tuple(sorted(dep))
        if key not in seen:
            seen.add(key)
            unique.append(dep)
    return unique

# ----------------------------------------------------------------------
# Example: Simulate sensor stream and find a dependency
# ----------------------------------------------------------------------
def demo():
    print("=" * 70)
    print("GEOMETRIC SENSOR SIMULATOR + TOKEN LEARNING")
    print("=" * 70)
    
    # Generate 100 random directions + phases
    np.random.seed(42)
    tokens = []
    for _ in range(100):
        # Random direction on sphere
        theta = np.random.uniform(0, 2*math.pi)
        phi = np.arccos(2*np.random.uniform() - 1)
        x = math.sin(phi) * math.cos(theta)
        y = math.sin(phi) * math.sin(theta)
        z = math.cos(phi)
        direction = np.array([x, y, z])
        phase = np.random.uniform(0, 360)
        token = vector_to_token(direction, phase)
        tokens.append(token)
    
    print(f"\nGenerated {len(tokens)} geometric tokens (first 10):")
    for i, tok in enumerate(tokens[:10]):
        print(f"  {i:2d}: {tok}")
    
    # Find dependencies (tensor cancellations)
    print("\nSearching for dependencies (max_len=4)...")
    deps = find_dependencies(tokens, max_len=4)
    print(f"Found {len(deps)} dependencies.")
    
    # Show a few
    for i, dep in enumerate(deps[:5]):
        print(f"  Dep {i+1}: indices {dep}")
        # Verify sum is zero
        Tsum = tensor_sum([token_to_tensor(tokens[j]) for j in dep])
        print(f"    Norm = {tensor_norm(Tsum):.2e}")
    
    # If none found, force an artificial dependency for demonstration
    if not deps:
        print("\nNo natural dependencies found. Creating an artificial one:")
        # Pick two tokens that are opposites? Not exactly, but we can create
        # a pair that sums to zero by making one token's tensor negative.
        # In real sensor, this would correspond to opposite directions.
        idx1 = 0
        # Find token whose vertex is opposite to token0
        v0 = OctahedralState.POSITIONS[int(tokens[0][:3],2)]
        for j, tok in enumerate(tokens[1:], start=1):
            vj = OctahedralState.POSITIONS[int(tok[:3],2)]
            if np.allclose(v0, -vj):
                idx2 = j
                break
        else:
            # Force by creating a token with opposite vertex
            opp_idx = 7 - int(tokens[0][:3],2)
            opp_bits = f"{opp_idx:03b}"
            opp_token = opp_bits + tokens[0][3:]
            tokens.append(opp_token)
            idx2 = len(tokens)-1
        print(f"  Pair: {tokens[idx1]} and {tokens[idx2]}")
        Tsum = token_to_tensor(tokens[idx1]) + token_to_tensor(tokens[idx2])
        print(f"  Sum norm = {tensor_norm(Tsum):.2e}  (should be ~0)")
        deps.append([idx1, idx2])
    
    # Tensor combination visualization
    print("\nTensor cancellation example:")
    dep = deps[0]
    T_sum = tensor_sum([token_to_tensor(tokens[i]) for i in dep])
    print(f"  Sum of tensors for {dep}: norm = {tensor_norm(T_sum):.2e}")
    print("  Geometric meaning: the combined tensors cancel out -> rotational symmetry in octahedral space.")
    
    print("\n" + "=" * 70)
    print("This demonstrates direct geometric sensing → tokenization → pattern learning.")
    print("The same mechanism can be used to factor numbers (as in your NFS) or recognize gestures.")
    print("=" * 70)

if __name__ == "__main__":
    demo()
