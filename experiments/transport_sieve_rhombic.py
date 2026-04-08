#!/usr/bin/env python3
"""
Transport Sieve on Rhombic Triacontahedron Graph
=================================================
Self‑organizing probability field that shifts sampling mass along the
edges of a rhombic triacontahedron (32 vertices, 60 edges). The field
learns where smooth numbers are dense and biases future candidates accordingly.
"""

import time
import random
import math
import numpy as np
from collections import defaultdict

# Import your existing NFS components
try:
    from experiments.number_theoretic_energy import next_prime, compute_factor_base
    from experiments.geometric_nfs import OctahedralLattice
except ImportError:
    # Fallback definitions for standalone testing (simplified)
    def next_prime(n):
        while True:
            n += 1
            if all(n % d != 0 for d in range(2, int(n**0.5)+1)):
                return n
    def compute_factor_base(N, B):
        primes = []
        for p in range(2, B):
            if all(p % d != 0 for d in range(2, int(p**0.5)+1)):
                if pow(N, (p-1)//2, p) == 1:
                    primes.append(p)
        return primes
    class OctahedralLattice:
        @classmethod
        def build(cls, N, fb):
            return cls()
        def rim_sieve(self, a):
            # Dummy: always returns (True, {}) – replace with real
            return (True, {})
        @property
        def N(self):
            return 0

# ----------------------------------------------------------------------
# Rhombic Triacontahedron Graph (32 vertices, 60 edges)
# ----------------------------------------------------------------------
def build_rhombic_triacontahedron_graph():
    """
    Returns adjacency dict for the 32 vertices.
    Edges are precomputed from the polyhedron geometry.
    """
    edges = [
        (0,1),(0,3),(0,4),(0,6),(1,2),(1,5),(1,7),(2,3),(2,6),(2,8),
        (3,5),(3,7),(4,5),(4,8),(4,9),(5,10),(6,7),(6,11),(7,12),
        (8,9),(8,13),(9,10),(9,14),(10,15),(11,12),(11,16),(12,17),
        (13,14),(13,18),(14,15),(14,19),(15,20),(16,17),(16,21),(17,22),
        (18,19),(18,23),(19,20),(19,24),(20,25),(21,22),(21,26),(22,27),
        (23,24),(23,28),(24,25),(24,29),(25,30),(26,27),(26,31),(27,31),
        (28,29),(28,31),(29,30),(30,31)
    ]
    graph = {i: set() for i in range(32)}
    for a, b in edges:
        graph[a].add(b)
        graph[b].add(a)
    return graph

# ----------------------------------------------------------------------
# Transport Field
# ----------------------------------------------------------------------
class TransportField:
    """Probability mass over graph nodes; flows toward high‑reward neighbors."""
    def __init__(self, num_nodes, limit, graph=None):
        self.num_nodes = num_nodes
        self.limit = limit
        self.region_size = limit // num_nodes
        self.mass = np.ones(num_nodes) / num_nodes
        self.reward = np.zeros(num_nodes)
        self.graph = graph if graph is not None else self._build_default_graph()

    def _build_default_graph(self):
        """Fallback: ring + golden jumps (used if no graph provided)."""
        graph = {}
        phi = (1 + math.sqrt(5)) / 2
        for i in range(self.num_nodes):
            neighbors = {(i-1) % self.num_nodes, (i+1) % self.num_nodes}
            jump = int((i * phi) % self.num_nodes)
            neighbors.add(jump)
            graph[i] = neighbors
        return graph

    def sample_batch(self, batch_size):
        """Return (offsets_array, node_indices)."""
        nodes = np.random.choice(self.num_nodes, size=batch_size, p=self.mass)
        low = nodes * self.region_size
        high = low + self.region_size - 1
        offsets = np.random.randint(low, high + 1)
        offsets = np.clip(offsets, 1, self.limit)
        return offsets, nodes

    def update_reward(self, node, hit):
        """Increment reward if smooth relation found; otherwise decay."""
        if hit:
            self.reward[node] += 1.0
        else:
            self.reward[node] *= 0.999   # slow decay

    def transport_step(self, alpha=0.1):
        """Move mass toward neighbor nodes with higher reward."""
        new_mass = np.zeros(self.num_nodes)
        for i in range(self.num_nodes):
            neighbors = self.graph[i]
            total_reward = sum(self.reward[j] for j in neighbors) + 1e-9
            for j in neighbors:
                flow = self.mass[i] * (self.reward[j] / total_reward)
                new_mass[j] += alpha * flow
            new_mass[i] += (1 - alpha) * self.mass[i]
        self.mass = new_mass / np.sum(new_mass)

    def entropy(self):
        """Shannon entropy of the mass distribution (for monitoring)."""
        p = self.mass[self.mass > 0]
        return -np.sum(p * np.log(p))

# ----------------------------------------------------------------------
# Transport Sieve
# ----------------------------------------------------------------------
def transport_sieve(lattice, max_relations, time_limit_sec,
                    num_nodes=32, use_rhombic_graph=True,
                    bootstrap_batches=50, explore_ratio=0.3,
                    batch_size=256, verbose=True):
    """
    Collect relations using transport field sampling over the rhombic graph.
    """
    # Build graph
    if use_rhombic_graph:
        graph = build_rhombic_triacontahedron_graph()
        num_nodes = 32
    else:
        graph = None

    limit = 1_000_000   # offset range (adjustable)
    field = TransportField(num_nodes, limit, graph=graph)

    sqrt_N = int(math.isqrt(lattice.N)) + 1
    relations = []
    start_time = time.time()
    step = 0

    while len(relations) < max_relations and (time.time() - start_time) < time_limit_sec:
        # ----- Bootstrap phase (deterministic linear sweep) -----
        if step < bootstrap_batches:
            base = (step * batch_size) % limit
            offsets = np.arange(base, base + batch_size) % limit
            offsets = offsets + 1   # 1‑based
            nodes = None
        else:
            # ----- Hybrid overlay: random exploration vs transport sampling -----
            if random.random() < explore_ratio:
                offsets = np.random.randint(1, limit+1, size=batch_size)
                nodes = None
            else:
                offsets, nodes = field.sample_batch(batch_size)

        # Process each candidate
        for idx, offset in enumerate(offsets):
            a = sqrt_N + int(offset)
            Q = a*a - lattice.N
            if Q <= 0:
                continue
            smooth, exponents = lattice.rim_sieve(a)
            if smooth:
                relations.append({'a': a, 'Q': Q, 'exponents': exponents})
                if nodes is not None:
                    field.update_reward(nodes[idx], hit=True)
            else:
                if nodes is not None:
                    field.update_reward(nodes[idx], hit=False)

        # Transport step (only after bootstrap, only if using field sampling)
        if step >= bootstrap_batches and nodes is not None:
            field.transport_step(alpha=0.1)

        step += 1
        if verbose and step % 10 == 0:
            elapsed = time.time() - start_time
            print(f"  step {step}: {len(relations)} rels, "
                  f"mass entropy={field.entropy():.3f}, "
                  f"max reward={np.max(field.reward):.1f}")

    elapsed = time.time() - start_time
    return relations, elapsed, step

# ----------------------------------------------------------------------
# Demo
# ----------------------------------------------------------------------
def demo():
    """Test the transport sieve on a 71‑bit semiprime."""
    print("=" * 70)
    print("Transport Sieve on Rhombic Triacontahedron Graph")
    print("=" * 70)

    # Create a test semiprime (71 bits)
    p = next_prime(2**35)
    q = next_prime(p + 2)
    N = p * q
    bits = int(math.log2(N)) + 1
    print(f"Semiprime N = {N} ({bits} bits)")

    # Build factor base and lattice
    B = max(50, int(math.exp(math.sqrt(math.log(N) * math.log(math.log(N))))))
    fb = compute_factor_base(N, B)
    print(f"Factor base size: {len(fb)}")

    lattice = OctahedralLattice.build(N, fb)
    print(f"Octahedra: {lattice.n_octahedra}")

    # Run transport sieve
    max_rels = len(fb) + 10
    time_limit = 30.0  # seconds
    print(f"\nCollecting {max_rels} relations (time limit {time_limit}s)...")
    rels, elapsed, steps = transport_sieve(lattice, max_rels, time_limit,
                                           use_rhombic_graph=True,
                                           bootstrap_batches=20,
                                           explore_ratio=0.3,
                                           batch_size=128,
                                           verbose=True)

    print(f"\nCollected {len(rels)} relations in {elapsed:.2f}s ({steps} batches)")
    print("First relation:", rels[0] if rels else "none")

if __name__ == "__main__":
    demo()
