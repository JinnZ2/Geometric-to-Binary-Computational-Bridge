"""
Tests for Engine.gaussian_splats: 4D, octahedral (8-state), and rhombic
triacontahedral (32-state) Gaussian splat field representations.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Engine.gaussian_splats import (
    Gaussian4DSource,
    SIMDOptimizer4D,
    GeometricEMSolver4D,
    bhattacharyya_distance,
    OctahedralStateEncoder,
    Gaussian8FieldSource,
    ZeemanDynamics,
    ManifoldConstraint,
    RhombicTriacontaEncoder,
    Gaussian32FieldSource,
    ZeemanDynamics32,
    SphericalManifoldConstraint,
)

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


def approx(a, b, tol=1e-6):
    return np.allclose(np.asarray(a), np.asarray(b), atol=tol, rtol=tol)


# ─── Gaussian4DSource ──────────────────────────────────────────────

print("\n=== Gaussian4DSource ===")

src = Gaussian4DSource(mu=[1.0, 2.0, 3.0, 0.5], cov=np.eye(4) * 0.25, charge=2.0)
check(src.mu.shape == (4,), "mu has shape (4,)")
check(src.cov.shape == (4, 4), "cov has shape (4, 4)")
check(src.charge == 2.0, "charge stored")

# condition_on_time at mu_t should return the spatial mean unchanged.
mu_c, cov_c = src.condition_on_time(0.5)
check(approx(mu_c, [1.0, 2.0, 3.0]), "condition_on_time(mu_t) returns mu_xyz")
check(cov_c.shape == (3, 3), "conditioned cov is 3x3")

# Velocity from cross-covariance: construct a splat with known velocity.
sigma_t2 = 0.04
vel = np.array([2.0, -1.0, 0.5])
cov = np.zeros((4, 4))
cov[:3, :3] = np.diag([0.1, 0.1, 0.1])
cov[:3, 3] = vel * sigma_t2
cov[3, :3] = vel * sigma_t2
cov[3, 3] = sigma_t2
moving = Gaussian4DSource(mu=[0, 0, 0, 0], cov=cov, charge=1.0)
check(approx(moving.get_velocity(), vel), "get_velocity recovers encoded velocity")

# Conditioning a moving splat one time-unit forward should drift the mean.
mu_forward, _ = moving.condition_on_time(1.0)
check(approx(mu_forward, vel, tol=1e-8),
      "condition_on_time(t=1) drifts mean by v*dt")

# Density peaks at the spatial mean (1, 2, 3) and decays with distance.
points = np.array([[1.0, 2.0, 3.0], [2.0, 2.0, 3.0]])
dens = src.evaluate_density_3d(points, 0.5)
check(np.all(dens > 0), "density is positive near center")
check(dens[0] > dens[1], "density peaks at center")
check(dens.shape == (2,), "density shape matches points")

# Invalid shapes raise.
try:
    Gaussian4DSource(mu=[1, 2, 3], cov=np.eye(4))
    check(False, "invalid mu shape raises ValueError")
except ValueError:
    check(True, "invalid mu shape raises ValueError")


# ─── SIMDOptimizer4D ───────────────────────────────────────────────

print("\n=== SIMDOptimizer4D ===")

# The batch path should agree with the scipy reference path.
sources = [src, moving]
query = np.random.RandomState(0).randn(20, 3) * 0.5
ref = SIMDOptimizer4D.calculate_field_chunk_4d(query, sources, 0.5)
batch = SIMDOptimizer4D.calculate_field_chunk_4d_batch(query, sources, 0.5)
check(approx(ref, batch, tol=1e-8), "batch and reference paths agree")

# Empty point list returns zeros.
empty = SIMDOptimizer4D.calculate_field_chunk_4d_batch(np.empty((0, 3)), sources, 0.0)
check(empty.shape == (0,), "empty points returns empty density")

# Empty sources returns zeros of correct length.
no_src = SIMDOptimizer4D.calculate_field_chunk_4d_batch(query, [], 0.0)
check(no_src.shape == (20,) and np.all(no_src == 0), "empty sources returns zeros")


# ─── GeometricEMSolver4D ───────────────────────────────────────────

print("\n=== GeometricEMSolver4D ===")

solver4d = GeometricEMSolver4D()
bounds = {"min": [-2.0, -2.0, -2.0], "max": [2.0, 2.0, 2.0]}
result = solver4d.calculate_field_4d(sources, bounds, t0=0.5)
check("density" in result and "points" in result, "result has density and points")
check(len(result["density"]) == len(result["points"]), "density len matches points len")
check(len(result["points"]) > 0, "solver produced sample points")

# Empty sources short-circuits.
empty_result = solver4d.calculate_field_4d([], bounds, t0=0.0)
check(empty_result["density"] == [], "empty sources returns empty density")


# ─── bhattacharyya_distance ────────────────────────────────────────

print("\n=== bhattacharyya_distance ===")

identical = Gaussian4DSource(mu=[0, 0, 0, 0], cov=np.eye(4) * 0.1)
check(abs(bhattacharyya_distance(identical, identical, 0.0)) < 1e-10,
      "identical splats have zero Bhattacharyya distance")

separated = Gaussian4DSource(mu=[3, 0, 0, 0], cov=np.eye(4) * 0.1)
d_far = bhattacharyya_distance(identical, separated, 0.0)
check(d_far > 0, "separated splats have positive distance")
near = Gaussian4DSource(mu=[0.5, 0, 0, 0], cov=np.eye(4) * 0.1)
d_near = bhattacharyya_distance(identical, near, 0.0)
check(d_near < d_far, "distance grows with separation")


# ─── OctahedralStateEncoder ────────────────────────────────────────

print("\n=== OctahedralStateEncoder ===")

enc = OctahedralStateEncoder()
check(enc.state_centers.shape == (8, 3), "8 cube corners")
check(np.all(np.abs(enc.state_centers) == 1.0), "all corners are +/- 1")

# Bit indexing matches the docstring contract.
check(approx(enc.state_centers[0], [-1, -1, -1]), "state 000 = (-1, -1, -1)")
check(approx(enc.state_centers[7], [1, 1, 1]), "state 111 = (1, 1, 1)")
check(approx(enc.state_centers[0b101], [1, -1, 1]), "state 101 = (1, -1, 1)")

# nearest_state round-trip for each corner.
all_ok = True
for i in range(8):
    if enc.nearest_state(enc.state_centers[i]) != i:
        all_ok = False
        break
check(all_ok, "nearest_state round-trips for all 8 corners")

# Slight perturbation still snaps to the same corner.
perturbed = enc.state_centers[5] + np.array([0.2, -0.2, 0.1])
check(enc.nearest_state(perturbed) == 5, "small perturbation still snaps to same corner")

# STATE_PROFILES is a dict over all 8 states.
check(set(enc.STATE_PROFILES.keys()) == set(range(8)),
      "STATE_PROFILES covers all 8 states")

# encode_state_to_gaussian returns a Gaussian4DSource with expected position.
g = enc.encode_state_to_gaussian(0b010, position=[1, 2, 3], time=0.0, charge=3.0)
check(isinstance(g, Gaussian4DSource), "encode_state_to_gaussian returns Gaussian4DSource")
check(approx(g.mu[:3], [1, 2, 3]), "encoded gaussian mu_xyz matches position")
check(g.charge == 3.0, "encoded gaussian charge matches")


# ─── Gaussian8FieldSource ──────────────────────────────────────────

print("\n=== Gaussian8FieldSource ===")

mu = np.array([0.0, 0.0, 0.0, -1.0, -1.0, -1.0])
cov = np.eye(6) * 0.25
g8 = Gaussian8FieldSource(mu, cov, charge=1.0)

mu_c, cov_c = g8.condition_on_state(0)
check(mu_c.shape == (3,), "conditioned mean is 3D")
check(cov_c.shape == (3, 3), "conditioned covariance is 3x3")

probs = g8.state_probabilities()
check(probs.shape == (8,), "state probabilities is length 8")
check(abs(probs.sum() - 1.0) < 1e-10, "state probabilities sum to 1")
check(g8.most_likely_state() == 0, "most likely state is 000 when centered at (-1,-1,-1)")

# Another centering: move to corner 7 and check.
g8_b = Gaussian8FieldSource(
    mu=np.array([0, 0, 0, 1.0, 1.0, 1.0]),
    cov=np.eye(6) * 0.25,
)
check(g8_b.most_likely_state() == 7, "most likely state is 111 when centered at (1,1,1)")

# evaluate_all_fields returns (N, 8) non-negative densities.
pts = np.array([[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
fields = g8.evaluate_all_fields(pts)
check(fields.shape == (2, 8), "evaluate_all_fields returns (N, 8)")
check(np.all(fields >= 0), "all field densities are non-negative")

# Invalid shapes raise.
try:
    Gaussian8FieldSource(np.zeros(5), np.eye(6))
    check(False, "invalid mu shape raises ValueError")
except ValueError:
    check(True, "invalid mu shape raises ValueError")


# ─── ZeemanDynamics ────────────────────────────────────────────────

print("\n=== ZeemanDynamics ===")

zeeman = ZeemanDynamics(encoder=enc, moment_magnitude=1.0, softmax_beta=30.0)

# At a corner, the interpolated moment should be close to that corner's moment.
corner_state = 0
expected_m = zeeman.state_moments[corner_state]
m_at_corner = zeeman.compute_moment(enc.state_centers[corner_state])
check(approx(m_at_corner, expected_m, tol=1e-3),
      "compute_moment at corner recovers that corner's moment")

# Force is finite for arbitrary s, B.
B = np.array([0.3, 0.1, -0.2])
F = zeeman.force(np.array([0.5, -0.5, 0.5]), B)
check(F.shape == (3,) and np.all(np.isfinite(F)), "Zeeman force is finite 3-vector")


# ─── ManifoldConstraint ────────────────────────────────────────────

print("\n=== ManifoldConstraint ===")

manifold = ManifoldConstraint(kappa=5.0)

# At any cube corner, force is zero (s_i^2 - 1 = 0 for all i).
for i in range(8):
    F = manifold.force(enc.state_centers[i])
    if not approx(F, np.zeros(3)):
        check(False, f"manifold force at corner {i} is zero")
        break
else:
    check(True, "manifold force at every cube corner is zero")

# Inside the cube, force pulls outward toward the nearest corner.
s_interior = np.array([0.3, 0.3, 0.3])
F = manifold.force(s_interior)
# s^2 - 1 = -0.91 < 0, so force = -4k*(-0.91)*0.3 > 0 along each axis.
check(np.all(F > 0), "inside the cube, force pushes outward toward +1 corner")

# Potential is non-negative and zero exactly at corners.
check(manifold.potential(enc.state_centers[3]) < 1e-12,
      "potential is ~0 at a cube corner")
check(manifold.potential(np.zeros(3)) > 0, "potential is positive at origin")


# ─── RhombicTriacontaEncoder ───────────────────────────────────────

print("\n=== RhombicTriacontaEncoder ===")

renc = RhombicTriacontaEncoder()
check(renc.vertices.shape == (32, 3), "rhombic encoder has 32 vertices")
check(renc.num_states == 32, "num_states == 32")

# All vertices on unit sphere.
norms = np.linalg.norm(renc.vertices, axis=1)
check(np.allclose(norms, 1.0), "all vertices are unit norm")

# All 32 are distinct (bug fix — the draft produced duplicates).
uniq = np.unique(np.round(renc.vertices, 8), axis=0)
check(uniq.shape == (32, 3), "all 32 vertices are distinct")

# nearest_state round-trip for every vertex.
all_ok = True
for i in range(32):
    if renc.nearest_state(renc.vertices[i]) != i:
        all_ok = False
        break
check(all_ok, "nearest_state round-trips for all 32 vertices")

# vertex_moment is aligned with vertex direction, scaled by magnitude.
m = renc.vertex_moment(5, magnitude=2.0)
check(approx(m, 2.0 * renc.vertices[5]), "vertex_moment aligned with vertex")


# ─── Gaussian32FieldSource ─────────────────────────────────────────

print("\n=== Gaussian32FieldSource ===")

mu32 = np.concatenate([[0.0, 0.0, 0.0], renc.vertices[0]])
cov32 = np.eye(6) * 0.05
g32 = Gaussian32FieldSource(mu32, cov32, charge=1.0)

mu_c, cov_c = g32.condition_on_state(0)
check(mu_c.shape == (3,), "conditioned mean is 3D")
check(cov_c.shape == (3, 3), "conditioned covariance is 3x3")

probs32 = g32.state_probabilities()
check(probs32.shape == (32,), "state probabilities is length 32")
check(abs(probs32.sum() - 1.0) < 1e-10, "state probabilities sum to 1")
check(g32.most_likely_state() == 0,
      "most likely state is vertex 0 when centered on vertex 0")

# Invalid shape raises.
try:
    Gaussian32FieldSource(np.zeros(5), np.eye(6))
    check(False, "invalid mu shape raises ValueError")
except ValueError:
    check(True, "invalid mu shape raises ValueError")


# ─── ZeemanDynamics32 ──────────────────────────────────────────────

print("\n=== ZeemanDynamics32 ===")

zeeman32 = ZeemanDynamics32(encoder=renc, moment_magnitude=1.0, softmax_beta=40.0)

# At a vertex, the interpolated moment should be close to that vertex direction.
m_at_vertex = zeeman32.compute_moment(renc.vertices[10])
check(approx(m_at_vertex, renc.vertices[10], tol=1e-3),
      "compute_moment at vertex recovers that vertex moment")

F32 = zeeman32.force(np.array([0.1, 0.2, 0.3]), np.array([0.5, 0.0, -0.2]))
check(F32.shape == (3,) and np.all(np.isfinite(F32)),
      "ZeemanDynamics32 force is finite 3-vector")


# ─── SphericalManifoldConstraint ───────────────────────────────────

print("\n=== SphericalManifoldConstraint ===")

smanifold = SphericalManifoldConstraint(encoder=renc, kappa=5.0, sigma=0.2)

# Force is finite everywhere we might sample.
for s in [np.array([0.0, 0.0, 0.0]), renc.vertices[5] * 0.5, renc.vertices[15]]:
    F = smanifold.force(s)
    if not (F.shape == (3,) and np.all(np.isfinite(F))):
        check(False, f"spherical manifold force finite at s={s}")
        break
else:
    check(True, "spherical manifold force is finite everywhere tested")

# Starting halfway between origin and a vertex, the force should point
# roughly toward that vertex (into the log-sum-exp well).
target = renc.vertices[0]
s_half = target * 0.5
F_half = smanifold.force(s_half)
# The force is proportional to grad_log (sum of weighted diffs to each
# vertex), so we check that it has a positive component along the target
# direction — i.e. there is attraction toward the nearest vertex.
check(np.dot(F_half, target) > 0,
      "spherical manifold pulls toward the nearest vertex")


# ─── Summary ───────────────────────────────────────────────────────

print("\n=== Summary ===")
total = passed + failed
print(f"{passed}/{total} passed")

if failed > 0:
    sys.exit(1)
