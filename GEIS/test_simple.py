"""
Simple test to verify GIES works
"""

import numpy as np
from octahedral_state import OctahedralState
from geometric_encoder import GeometricEncoder
from state_tensor import StateTensor

print("Testing GIES...")
print("="*50)

# Test 1: Create a state
state = OctahedralState(3)
print(f"✓ Created state: {state}")

# Test 2: Generate token
token = state.to_token()
print(f"✓ Token: {token}")

# Test 3: Encode to binary
encoder = GeometricEncoder()
binary = encoder.encode_to_binary(token)
print(f"✓ Encoded to binary: {binary}")

# Test 4: Decode back
decoded = encoder.decode_from_binary(binary)
print(f"✓ Decoded back: {decoded}")

# Test 5: Verify round-trip
assert decoded == token
print(f"✓ Round-trip successful!")

# Test 6: Calculate tensor
tensor = StateTensor(state)
projection = tensor.project([0, 0, 1])
print(f"✓ Tensor projection: {projection:.6f}")

# Test 7: Inversion
inverted = state.invert()
print(f"✓ Inversion: {state.to_token()} -> {inverted.to_token()}")

print("="*50)
print("ALL TESTS PASSED! ✓")
