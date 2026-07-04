#!/usr/bin/env python3
# simd_rf_proximity.py — CC0
# Geometric-to-Binary-Computational-Bridge — experimental expansion of
# Engine/simd_optimizer.py using Random-Forest proximity as a similarity
# metric for SIMD chunk grouping.
#
# Requires: numpy, scikit-learn. NOT added to requirements.txt — this is
# an optional, experimental module; the core Engine test suite (58 tests,
# tests/test_engine.py) does not import it and does not depend on
# scikit-learn being installed.
#
# THE IDEA
# ========
# SIMDOptimizer.calculateFieldChunk (Engine/simd_optimizer.py) vectorizes
# one CONTIGUOUS batch of points against all sources via numpy
# broadcasting. Vector-lane work is most uniform when every point in a
# chunk is physically similar — same dominant source, same near/far
# regime — since that's what keeps the arithmetic (and any future
# branchy fast-path) doing "the same kind of work" per lane. Naive
# contiguous chunking (e.g. straight off SpatialGrid's octree order) has
# no such guarantee.
#
# Random-Forest proximity is a data-driven similarity metric: train a
# classifier on point coordinates against a REAL label, then for every
# pair of points count the fraction of trees that route them to the same
# leaf. That count is high exactly when the forest thinks two points
# behave the same way for the task at hand.
#
# This module keeps that technique (the useful kernel of a generic
# RF-proximity + MDS reference script) but re-grounds both ends of it:
#   - the label is REAL — which source's field dominates at that point —
#     instead of sklearn.datasets.make_classification's synthetic noise.
#   - the question asked of the embedding is REAL — does proximity-order
#     chunking reduce within-chunk field-magnitude spread versus naive
#     spatial order — instead of a generic PCA/t-SNE/MDS comparison plot.
#
# REFUTATION_PROTOCOL: this is a HEURISTIC, not a proven optimization.
# The demo below reports one falsifiable comparison on one configuration.
# It is not assumed to generalize; if a run shows proximity chunking
# doesn't help, that is a valid (and reportable) result, not a bug to
# hide.

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.manifold import MDS

from Engine.simd_optimizer import SIMDOptimizer


def dominant_source_labels(points: np.ndarray, sources: list) -> np.ndarray:
    """Which source contributes the largest |E| at each point? A
    physically real classification target, grounded in the same Coulomb
    field the SIMD optimizer already computes — not a synthetic feature."""
    opt = SIMDOptimizer()
    contributions = np.zeros((len(sources), len(points)))
    for i, source in enumerate(sources):
        if source.get("type", "charge") == "charge":
            E = opt._electric_field_charge(points, source)
        else:
            E, _ = opt._fields_current(points, source)
        contributions[i] = np.linalg.norm(E, axis=1)
    return np.argmax(contributions, axis=0)


def rf_proximity(X: np.ndarray, y: np.ndarray, n_estimators: int = 100,
                  random_state: int = 42) -> np.ndarray:
    """Fraction of trees that route each pair of samples to the same leaf.
    This is the reusable kernel from the reference RF-proximity script;
    only its inputs (X, y) changed, not the technique."""
    rf = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)
    rf.fit(X, y)
    leaf_indices = np.column_stack([tree.apply(X) for tree in rf.estimators_])
    n_samples = X.shape[0]
    n_trees = leaf_indices.shape[1]
    prox = np.zeros((n_samples, n_samples))
    for i in range(n_samples):
        prox[i] = np.sum(leaf_indices == leaf_indices[i], axis=1) / n_trees
    return prox


def proximity_chunk_order(points: np.ndarray, sources: list) -> np.ndarray:
    """Order points by a 1D MDS embedding of RF-proximity dissimilarity,
    so that contiguous slices of the returned order are SIMD chunks whose
    members the forest considers physically alike."""
    labels = dominant_source_labels(points, sources)
    prox = rf_proximity(points, labels)
    dissim = 1.0 - prox
    np.fill_diagonal(dissim, 0.0)
    embedding = MDS(n_components=1, dissimilarity="precomputed",
                     random_state=42, normalized_stress=False).fit_transform(dissim)
    return np.argsort(embedding[:, 0])


def _chunk_field_spread(points: np.ndarray, sources: list, order: np.ndarray,
                         chunk_size: int) -> float:
    """Mean within-chunk std-dev of |E|, averaged over chunks — lower means
    each SIMD chunk is more numerically homogeneous."""
    opt = SIMDOptimizer()
    ordered = points[order]
    spreads = []
    for start in range(0, len(ordered), chunk_size):
        chunk_points = ordered[start:start + chunk_size]
        if len(chunk_points) < 2:
            continue
        result = opt.calculateFieldChunk({"points": chunk_points.tolist()}, sources)
        E = np.array(result["electricField"])
        mag = np.linalg.norm(E, axis=1)
        spreads.append(float(np.std(mag)))
    return float(np.mean(spreads)) if spreads else 0.0


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    sources = [
        {"position": [3.0, 0.0, 0.0], "strength": 2e-9, "type": "charge"},
        {"position": [-3.0, 1.0, 0.0], "strength": -1.5e-9, "type": "charge"},
        {"position": [0.0, -3.0, 2.0], "strength": 1e-9, "type": "charge"},
    ]
    points = rng.uniform(-5, 5, size=(120, 3))

    labels = dominant_source_labels(points, sources)
    print(f"Dominant-source labels: {np.bincount(labels)} "
          f"(points per source, {len(sources)} sources)")

    prox = rf_proximity(points, labels)
    same_label = labels[:, None] == labels[None, :]
    within = prox[same_label].mean()
    across = prox[~same_label].mean()
    print(f"\nRF-proximity sanity check (label was NOT given to rf_proximity's "
          f"caller as a feature, only as the training target):")
    print(f"  mean proximity within same dominant-source label: {within:.3f}")
    print(f"  mean proximity across different labels:           {across:.3f}")
    print(f"  {'PASS' if within > across else 'FAIL'}: forest recovers real structure "
          f"from raw (x,y,z) alone")

    chunk_size = 8
    naive_order = np.arange(len(points))
    prox_order = proximity_chunk_order(points, sources)

    naive_spread = _chunk_field_spread(points, sources, naive_order, chunk_size)
    prox_spread = _chunk_field_spread(points, sources, prox_order, chunk_size)

    print(f"\nSIMD chunk homogeneity (mean within-chunk std-dev of |E|, "
          f"chunk_size={chunk_size}):")
    print(f"  naive contiguous order   : {naive_spread:.6e}")
    print(f"  RF-proximity sorted order: {prox_spread:.6e}")
    improved = prox_spread < naive_spread
    print(f"  {'IMPROVED' if improved else 'NO IMPROVEMENT'}: "
          f"proximity-sorted chunks are "
          f"{'more' if improved else 'not more'} numerically homogeneous "
          f"than naive order on this configuration.")
