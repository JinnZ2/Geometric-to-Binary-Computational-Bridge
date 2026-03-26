"""
Tests for Engine: SymmetryDetector, SpatialGrid, SIMDOptimizer, GeometricEMSolver
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Engine.symmetry_detector import SymmetryDetector
from Engine.spatial_grid import SpatialGrid
from Engine.simd_optimizer import SIMDOptimizer
from Engine.geometric_solver import GeometricEMSolver

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


# ─── SymmetryDetector ───────────────────────────────────────────────

print("\n=== SymmetryDetector ===")
det = SymmetryDetector()
bounds = {"min": [-5, -5, -5], "max": [5, 5, 5]}

# No sources = no symmetries
check(det.findSymmetries([], bounds) == [], "Empty sources = no symmetry")

# Single source = no symmetries
single = [{"position": [1, 0, 0], "strength": 1e-9, "type": "charge"}]
check(det.findSymmetries(single, bounds) == [], "Single source = no symmetry")

# Two identical charges symmetric about origin on x-axis
sym_x = [
    {"position": [2, 0, 0], "strength": 1e-9, "type": "charge"},
    {"position": [-2, 0, 0], "strength": 1e-9, "type": "charge"},
]
syms = det.findSymmetries(sym_x, bounds)
sym_types = [s["type"] for s in syms]
check(len(syms) > 0, "Symmetric pair detected symmetries")
check("reflective" in sym_types, "Reflective symmetry found")

# x-axis reflection should be detected (mirror across yz plane at centroid=origin)
planes = [s["plane"] for s in syms if s["type"] == "reflective"]
check("x" in planes, "Reflective symmetry across x-plane")
check("y" in planes, "Reflective symmetry across y-plane")
check("z" in planes, "Reflective symmetry across z-plane")

# Two different charges — no x-reflection (different strengths break x-mirror)
# but y and z reflections still hold (both at y=0, z=0)
asym = [
    {"position": [2, 0, 0], "strength": 1e-9, "type": "charge"},
    {"position": [-2, 0, 0], "strength": 2e-9, "type": "charge"},
]
syms_asym = det.findSymmetries(asym, bounds)
x_reflections = [s for s in syms_asym if s["type"] == "reflective" and s["plane"] == "x"]
check(len(x_reflections) == 0, "Different strengths breaks x-reflection")

# Four charges in a square (should have 4-fold rotational)
square = [
    {"position": [1, 1, 0], "strength": 1e-9, "type": "charge"},
    {"position": [-1, 1, 0], "strength": 1e-9, "type": "charge"},
    {"position": [-1, -1, 0], "strength": 1e-9, "type": "charge"},
    {"position": [1, -1, 0], "strength": 1e-9, "type": "charge"},
]
syms_sq = det.findSymmetries(square, bounds)
rot_syms = [s for s in syms_sq if s["type"] == "rotational"]
check(len(rot_syms) > 0, "Square has rotational symmetry")

# get_reduction_factor
check(det.get_reduction_factor([]) == 1.0, "No symmetry = reduction 1.0")
check(det.get_reduction_factor(syms) >= 2.0, "Symmetric pair reduction >= 2.0")


# ─── SpatialGrid ───────────────────────────────────────────────────

print("\n=== SpatialGrid ===")
grid = SpatialGrid(adaptive_threshold=0.5, max_depth=3)

sources = [
    {"position": [0, 0, 0], "strength": 1e-9},
]
regions = grid.adaptiveDecomposition(bounds, sources)
check(len(regions) > 1, f"Adaptive decomposition produced {len(regions)} regions (>1)")

# All regions should have points
check(all("points" in r for r in regions), "All regions have points")
check(all(len(r["points"]) > 0 for r in regions), "All regions have >0 points")

# Regions near source should have higher field intensity
near = [r for r in regions if np.linalg.norm(np.array(r["center"])) < 2]
far = [r for r in regions if np.linalg.norm(np.array(r["center"])) > 4]
if near and far:
    avg_near_intensity = np.mean([r["fieldIntensity"] for r in near])
    avg_far_intensity = np.mean([r["fieldIntensity"] for r in far])
    check(avg_near_intensity > avg_far_intensity,
          f"Near regions stronger ({avg_near_intensity:.2e}) than far ({avg_far_intensity:.2e})")

# Uniform grid
points = grid.generateUniformGrid(bounds, 4)
check(len(points) == 64, f"4x4x4 uniform grid = 64 points, got {len(points)}")
check(len(points[0]) == 3, "Each point is 3D")

# Empty sources = single region (nothing to refine near)
regions_empty = grid.adaptiveDecomposition(bounds, [])
check(len(regions_empty) >= 1, "Empty sources produces at least 1 region")


# ─── SIMDOptimizer ──────────────────────────────────────────────────

print("\n=== SIMDOptimizer ===")
simd = SIMDOptimizer()

# Single charge at origin
chunk = {"points": [[1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0]]}
sources = [{"type": "charge", "position": [0, 0, 0], "strength": 1e-9}]
result = simd.calculateFieldChunk(chunk, sources)

check(len(result["electricField"]) == 4, "4 E-field vectors")
check(len(result["magneticField"]) == 4, "4 B-field vectors")
check(result["simdEfficiency"] > 0, "SIMD efficiency > 0")

# E-field points radially outward from positive charge
E0 = result["electricField"][0]  # at [1,0,0]
check(E0[0] > 0, "E-field at [1,0,0] points in +x (away from + charge)")
check(abs(E0[1]) < 1e-10 and abs(E0[2]) < 1e-10,
      "E-field at [1,0,0] has no y/z component")

# Opposite side: E points in -x
E3 = result["electricField"][3]  # at [-1,0,0]
check(E3[0] < 0, "E-field at [-1,0,0] points in -x")

# Magnitudes should be equal by symmetry
mag0 = np.linalg.norm(E0)
mag3 = np.linalg.norm(E3)
check(abs(mag0 - mag3) < 1e-6, "Equal magnitude at symmetric points")

# Negative charge: field points inward
sources_neg = [{"type": "charge", "position": [0, 0, 0], "strength": -1e-9}]
result_neg = simd.calculateFieldChunk(chunk, sources_neg)
E0_neg = result_neg["electricField"][0]
check(E0_neg[0] < 0, "E-field toward negative charge")

# Current element: produces magnetic field
chunk2 = {"points": [[0, 1, 0]]}
sources_cur = [{
    "type": "current",
    "position": [0, 0, 0],
    "start": [0, 0, -1],
    "end": [0, 0, 1],
    "strength": 1.0
}]
result_cur = simd.calculateFieldChunk(chunk2, sources_cur)
B = result_cur["magneticField"][0]
B_mag = np.linalg.norm(B)
check(B_mag > 0, "Current produces nonzero B-field")
# B should be perpendicular to both dl (z-axis) and r (y-axis) = x-direction
check(abs(B[0]) > abs(B[1]) and abs(B[0]) > abs(B[2]),
      "B-field from z-current at y-point is primarily in x-direction")

# Empty sources
empty_result = simd.calculateFieldChunk({"points": [[0, 0, 0]]}, [])
check(len(empty_result["electricField"]) == 0, "No sources = no fields")

# Empty points
empty_pts = simd.calculateFieldChunk({"points": []}, sources)
check(len(empty_pts["electricField"]) == 0, "No points = no fields")


# ─── GeometricEMSolver ─────────────────────────────────────────────

print("\n=== GeometricEMSolver ===")
solver = GeometricEMSolver()

# Solve with two charges
sources = [
    {"type": "charge", "position": [1, 0, 0], "strength": 1e-9},
    {"type": "charge", "position": [-1, 0, 0], "strength": -1e-9},
]
result = solver.calculateElectromagneticField(sources, bounds, 32)

check("electricField" in result, "Result has electricField")
check("magneticField" in result, "Result has magneticField")
check("points" in result, "Result has points")
check("symmetries" in result, "Result has symmetries")
check(len(result["points"]) == len(result["electricField"]),
      "Points and E-field same length")
check(len(result["points"]) > 0, f"Produced {len(result['points'])} evaluation points")

# Performance tracker
report = solver.performanceMetrics.getEfficiencyReport()
check(report["solutionsComputed"] == 1, "1 solution computed")
check("s" in report["totalComputeTime"], "Compute time has 's' suffix")
check(report["averageSpeedup"] != "N/A", "Speedup is calculated")

# Empty sources
result_empty = solver.calculateElectromagneticField([], bounds)
check(len(result_empty["electricField"]) == 0, "Empty sources = empty fields")

# Mixed sources
sources_mix = [
    {"type": "charge", "position": [2, 0, 0], "strength": 1e-9},
    {"type": "current", "position": [0, 0, 0], "start": [0, 0, -1],
     "end": [0, 0, 1], "strength": 0.1},
]
result_mix = solver.calculateElectromagneticField(sources_mix, bounds)
B_fields = result_mix["magneticField"]
has_nonzero_B = any(np.linalg.norm(b) > 1e-20 for b in B_fields)
check(has_nonzero_B, "Current source produces nonzero B-fields")

# Multiple solves accumulate in performance tracker (empty sources doesn't record)
check(solver.performanceMetrics.totalSolutions >= 2, "Multiple solutions tracked")


# ─── KT Annealer ────────────────────────────────────────────────────

import math
from Engine.kt_annealer import KTAnnealer, KTConfig, anneal_network_phases

print("\n── KTAnnealer ──────────────────────────────────────────────")

PHI_TEST = (1 + 5 ** 0.5) / 2

# T_KT formula
cfg_default = KTConfig()
check(
    abs(cfg_default.T_KT - math.pi * PHI_TEST / 2) < 1e-9,
    f"T_KT = π·φ/2 ≈ {cfg_default.T_KT:.4f}",
)

# Custom J
cfg_j2 = KTConfig(J=2.0)
check(abs(cfg_j2.T_KT - math.pi) < 1e-9, "T_KT(J=2) = π")

# Triangle: 3 nodes fully connected
triangle_adj = [[1, 2], [0, 2], [0, 1]]
phases_aligned = np.array([0.0, 0.0, 0.0])
ann = KTAnnealer(phases_aligned, triangle_adj, KTConfig(n_steps=10, seed=0))
E_aligned = ann._edge_energy(phases_aligned)
check(abs(E_aligned - (-3.0 * PHI_TEST)) < 1e-9, "Aligned triangle energy = -3J")

# Worst-case energy (fully misaligned 120° spacing)
phases_120 = np.array([0.0, 2 * math.pi / 3, 4 * math.pi / 3])
E_120 = ann._edge_energy(phases_120)
check(abs(E_120 - (1.5 * PHI_TEST)) < 1e-6, "120°-spaced triangle energy = +3J/2")

# Phase coherence
coh_aligned = ann._phase_coherence(phases_aligned)
check(abs(coh_aligned - 1.0) < 1e-9, "Aligned phases → coherence = 1.0")

coh_uniform = ann._phase_coherence(phases_120)
check(coh_uniform < 0.05, f"120°-spaced phases → coherence ≈ 0 (got {coh_uniform:.4f})")

# Vortex count — aligned triangle has no vortex
v_aligned = ann._count_vortices(phases_aligned)
check(v_aligned == 0, "Aligned triangle: 0 vortices")

# Annealing reduces energy on random 4×4 torus
rng = np.random.default_rng(7)
N = 16
adj_torus = []
for row in range(4):
    for col in range(4):
        adj_torus.append([
            row * 4 + (col + 1) % 4,
            row * 4 + (col - 1) % 4,
            ((row + 1) % 4) * 4 + col,
            ((row - 1) % 4) * 4 + col,
        ])
phases_rand = rng.uniform(0, 2 * math.pi, N)
cfg_anneal = KTConfig(J=PHI_TEST, T_start=5.0, T_final=0.3, n_steps=300, seed=42)
ann2 = KTAnnealer(phases_rand.copy(), adj_torus, cfg_anneal)
optimized = ann2.anneal()
E_init = ann2.history[0].energy
E_final = ann2.history[-1].energy
check(E_final < E_init, f"Annealing reduces energy: {E_init:.2f} → {E_final:.2f}")

coh_init  = ann2.history[0].phase_coherence
coh_final = ann2.history[-1].phase_coherence
check(coh_final > coh_init, f"Annealing improves coherence: {coh_init:.3f} → {coh_final:.3f}")

# History populated
check(len(ann2.history) == 300, "History has one entry per step")

# Summary dict has expected keys
s = ann2.summary()
for key in ("T_KT", "energy_final", "coherence_final", "vortices_final"):
    check(key in s, f"summary has '{key}'")

# anneal_network_phases convenience wrapper
phases_conv = rng.uniform(0, 2 * math.pi, 4)
adj_square = [[1, 3], [0, 2], [1, 3], [0, 2]]
opt2, s2 = anneal_network_phases(
    phases_conv, adj_square,
    KTConfig(n_steps=50, seed=1),
)
check(len(opt2) == 4, "anneal_network_phases returns correct length")
check("coherence_final" in s2, "anneal_network_phases summary is populated")


# ─── Summary ────────────────────────────────────────────────────────

print(f"\n{'='*50}")
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"WARNING: {failed} test(s) failed")
    exit(1)
