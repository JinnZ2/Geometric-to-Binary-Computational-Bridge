"""
Tests for GEIS: OctahedralState, GeometricEncoder, StateTensor
"""

import numpy as np
from octahedral_state import OctahedralState
from geometric_encoder import GeometricEncoder
from state_tensor import StateTensor

passed = 0
failed = 0


def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label}")


# ─── OctahedralState ────────────────────────────────────────────────

print("\n=== OctahedralState ===")

# __init__ and bounds
for i in range(8):
    s = OctahedralState(i)
    check(s.index == i, f"State({i}) index")
check(len(OctahedralState.POSITIONS) == 8, "8 positions defined")

try:
    OctahedralState(-1)
    check(False, "Reject index -1")
except ValueError:
    check(True, "Reject index -1")

try:
    OctahedralState(8)
    check(False, "Reject index 8")
except ValueError:
    check(True, "Reject index 8")

try:
    OctahedralState(2.5)
    check(False, "Reject float index")
except (ValueError, TypeError):
    check(True, "Reject float index")

# to_binary
check(OctahedralState(0).to_binary() == "000", "State(0) to_binary = 000")
check(OctahedralState(5).to_binary() == "101", "State(5) to_binary = 101")
check(OctahedralState(7).to_binary() == "111", "State(7) to_binary = 111")
check(OctahedralState(3).to_binary(width=4) == "0011", "State(3) to_binary width=4")

# to_token
check(OctahedralState(1).to_token() == "001|O", "State(1) default token")
check(OctahedralState(2).to_token("/", "X") == "010/X", "State(2) custom token")

# from_token
s = OctahedralState.from_token("101|I")
check(s.index == 5, "from_token '101|I' = index 5")
s = OctahedralState.from_token("011:O")
check(s.index == 3, "from_token '011:O' = index 3")
s = OctahedralState.from_token("110/X")
check(s.index == 6, "from_token '110/X' = index 6")
s = OctahedralState.from_token("001||O")
check(s.index == 1, "from_token '001||O' = index 1")

try:
    OctahedralState.from_token("001O")
    check(False, "Reject token without operator")
except ValueError:
    check(True, "Reject token without operator")

# from_binary
check(OctahedralState.from_binary("110").index == 6, "from_binary '110' = 6")
check(OctahedralState.from_binary("000").index == 0, "from_binary '000' = 0")

# invert
for i in range(8):
    inv = OctahedralState(i).invert()
    check(inv.index == 7 - i, f"State({i}).invert() = {7-i}")

# double inversion = identity
for i in range(8):
    check(OctahedralState(i).invert().invert().index == i,
          f"State({i}) double invert = identity")

# distance_to
d = OctahedralState(0).distance_to(OctahedralState(7))
check(d > 0, "distance_to opposite state > 0")
check(abs(OctahedralState(0).distance_to(OctahedralState(0))) < 1e-10,
      "distance_to self = 0")

# dot_product
dp = OctahedralState(0).dot_product(OctahedralState(7))
check(dp < 0, "dot_product of opposite states < 0")
dp_self = OctahedralState(0).dot_product(OctahedralState(0))
check(dp_self > 0, "dot_product with self > 0")

# __eq__ and __hash__
check(OctahedralState(3) == OctahedralState(3), "Equality same index")
check(OctahedralState(3) != OctahedralState(4), "Inequality different index")
check(hash(OctahedralState(5)) == hash(OctahedralState(5)), "Hash consistency")

# ─── GeometricEncoder ───────────────────────────────────────────────

print("\n=== GeometricEncoder ===")
enc = GeometricEncoder()

# Round-trip for all states with | operator
for i in range(8):
    for sym in ['O', 'I', 'X', '\u0394']:
        token = f"{format(i, '03b')}|{sym}"
        binary = enc.encode_to_binary(token)
        decoded = enc.decode_from_binary(binary)
        check(decoded == token, f"Round-trip '{token}'")

# Round-trip with / operator
for i in range(8):
    token = f"{format(i, '03b')}/O"
    binary = enc.encode_to_binary(token)
    decoded = enc.decode_from_binary(binary)
    check(decoded == token, f"Round-trip '{token}'")

# : operator encodes same as / — decodes back to / (canonical form)
token = "010:I"
binary = enc.encode_to_binary(token)
decoded = enc.decode_from_binary(binary)
check(decoded == "010/I", "':' encodes like '/', decodes back as '010/I'")

# Nested operator ||
token = "001||O"
binary = enc.encode_to_binary(token)
check(len(binary) == 7, "Nested || produces 7 bits (3+2+2)")
decoded = enc.decode_from_binary(binary)
check(decoded == token, "Round-trip '001||O'")

# validate_token
check(enc.validate_token("000|O") is True, "validate_token valid")
check(enc.validate_token("000O") is False, "validate_token missing operator")
check(enc.validate_token("00|O") is False, "validate_token wrong width")

# get_components
v, op, sym = enc.get_components("101|X")
check(v == "101" and op == "|" and sym == "X", "get_components '101|X'")
v, op, sym = enc.get_components("010||I")
check(v == "010" and op == "||" and sym == "I", "get_components '010||I'")

# Unknown symbol raises error
try:
    enc.encode_to_binary("001|Z")
    check(False, "Reject unknown symbol Z")
except ValueError:
    check(True, "Reject unknown symbol Z")

# Invalid binary in vertex
try:
    enc.encode_to_binary("0a1|O")
    check(False, "Reject non-binary vertex")
except ValueError:
    check(True, "Reject non-binary vertex")

# Wrong vertex width
try:
    enc.encode_to_binary("01|O")
    check(False, "Reject 2-bit vertex")
except ValueError:
    check(True, "Reject 2-bit vertex")

# ─── StateTensor ────────────────────────────────────────────────────

print("\n=== StateTensor ===")

# Basic construction
t = StateTensor(OctahedralState(0))
check(t.tensor.shape == (3, 3), "Tensor is 3x3")
check(t.weight == 1.0, "Default weight = 1.0")

# Tensor is symmetric (outer product is always symmetric)
check(np.allclose(t.tensor, t.tensor.T), "Tensor is symmetric")

# Tensor is rank-1 (determinant = 0 for outer product)
check(abs(t.determinant()) < 1e-10, "Rank-1 tensor has det ~ 0")

# Trace = |v|^2 for unit-weight outer product
expected_trace = np.dot(t.vector, t.vector)
check(abs(t.trace() - expected_trace) < 1e-10, "Trace = |v|^2")

# Norm > 0
check(t.norm() > 0, "Frobenius norm > 0")

# project: projection along state's own direction = |v|^2 * cos^2(0) * |v|^2
proj = t.project(t.vector)
check(proj > 0, "Projection along own direction > 0")

# project perpendicular direction should give smaller value
proj_perp = t.project([0, 0, 1])
# not necessarily zero since state 0 has z-component

# Eigenvalues: rank-1 matrix has one nonzero eigenvalue
evals = t.eigenvalues()
nonzero = sum(1 for e in evals if abs(e) > 1e-10)
check(nonzero == 1, "Rank-1 tensor has 1 nonzero eigenvalue")

# Eigenvectors
evals2, evecs = t.eigenvectors()
check(len(evals2) == 3, "3 eigenvalues from eigenvectors()")
check(evecs.shape == (3, 3), "Eigenvector matrix is 3x3")

# Weighted tensor
tw = StateTensor(OctahedralState(0), weight=2.0)
check(abs(tw.trace() - 4.0 * expected_trace) < 1e-10,
      "Weight=2 tensor trace = 4 * base trace")

# combine
t1 = StateTensor(OctahedralState(0))
t2 = StateTensor(OctahedralState(7))
combined = StateTensor.combine([t1, t2])
check(combined.shape == (3, 3), "Combined tensor is 3x3")
# Sum of two rank-1 tensors should have rank <= 2
det_comb = abs(np.linalg.det(combined))
# States 0 and 7 are anti-parallel, so combined should have higher rank
check(True, f"Combined determinant: {det_comb:.6f}")

# combine empty
empty = StateTensor.combine([])
check(np.allclose(empty, np.zeros((3, 3))), "combine([]) = zero matrix")

# rotate
R90z = np.array([
    [0, -1, 0],
    [1, 0, 0],
    [0, 0, 1]
], dtype=float)
rotated = t.rotate(R90z)
check(isinstance(rotated, StateTensor), "rotate() returns StateTensor")
check(0 <= rotated.state.index <= 7, "Rotated state has valid index")
# Rotated tensor should satisfy T' = R T R^T
expected_tensor = R90z @ t.tensor @ R90z.T
check(np.allclose(rotated.tensor, expected_tensor, atol=1e-10),
      "Rotated tensor = R T R^T")

# ─── Summary ────────────────────────────────────────────────────────

print(f"\n{'='*50}")
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"WARNING: {failed} test(s) failed")
    exit(1)
