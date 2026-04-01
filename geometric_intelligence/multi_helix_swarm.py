"""
Multi-Helix Swarm — Integrated consciousness via DNA strand mechanics + swarm dynamics
======================================================================================
Reverse-engineered from Multi-helix-swarm.md using:
  1. DNA double-helix mechanics: base pairing, complementarity, phi-amplification
     (from multi_helix_cognition.py)
  2. Proven swarm equations: Vicsek alignment, Cucker-Smale flocking, Reynolds boids
  3. BioswarmAgent dynamics: W matrix, B coupling, trust, manipulation detection
     (from relational_bioswarm.py)

The core insight: each cognitive strand is an agent in a swarm. Cross-strand
pairing is the DNA "base pair" bond. Swarm consensus across strands produces
emergent decisions without hierarchical control.

Extracted from geometric_intelligence/Multi-helix-swarm.md
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from geometric_intelligence.multi_helix_cognition import (
    AttentionType, FocusBase, MultiStrandPair, MultiHelixFocus,
    COMPLEMENTS, PHI,
)
from geometric_intelligence.relational_bioswarm import (
    BioswarmAgent, RelationalGameLayer, phase_compatibility, synergy_score,
)


# ── Cognitive strand types (the 4 DNA-like strands) ─────────────────────

class StrandDomain(Enum):
    """The four cognitive dimensions — analogous to DNA base types."""
    MENTAL = "mental"         # Analytical, pattern, memory
    EMOTIONAL = "emotional"   # Emotional resonance, intuition
    PHYSICAL = "physical"     # Kinesthetic, spatial
    INTEGRATIVE = "integrative"  # Synthesis, divergent, creative

# Map strand domains to their primary attention types
STRAND_ATTENTION_MAP: Dict[StrandDomain, List[AttentionType]] = {
    StrandDomain.MENTAL:      [AttentionType.ANALYTIC, AttentionType.PATTERN, AttentionType.MEMORY],
    StrandDomain.EMOTIONAL:   [AttentionType.EMOTIONAL, AttentionType.INTUITIVE, AttentionType.TEMPORAL],
    StrandDomain.PHYSICAL:    [AttentionType.KINESTHETIC, AttentionType.SPATIAL, AttentionType.CONTEXT],
    StrandDomain.INTEGRATIVE: [AttentionType.SYNTHESIS, AttentionType.DIVERGENT, AttentionType.CREATIVE],
}

# DNA-like complementary pairing rules between strand domains
STRAND_COMPLEMENTS: Dict[StrandDomain, StrandDomain] = {
    StrandDomain.MENTAL:      StrandDomain.EMOTIONAL,    # A-T analog
    StrandDomain.EMOTIONAL:   StrandDomain.MENTAL,       # T-A analog
    StrandDomain.PHYSICAL:    StrandDomain.INTEGRATIVE,  # C-G analog
    StrandDomain.INTEGRATIVE: StrandDomain.PHYSICAL,     # G-C analog
}


# ── Swarm equations (proven dynamics) ──────��────────────────────────────

def vicsek_alignment(headings: np.ndarray, noise_eta: float = 0.1,
                      rng: Optional[np.random.Generator] = None) -> np.ndarray:
    """
    Vicsek model alignment (1995):
    theta_i(t+1) = <theta_j>_neighbors + eta * noise

    headings: array of angles (radians), one per agent
    noise_eta: noise strength [0, 1]

    Returns updated headings after consensus step.
    """
    if rng is None:
        rng = np.random.default_rng()
    # Mean direction (circular mean)
    mean_cos = np.mean(np.cos(headings))
    mean_sin = np.mean(np.sin(headings))
    mean_heading = np.arctan2(mean_sin, mean_cos)
    noise = noise_eta * rng.uniform(-np.pi, np.pi, size=headings.shape)
    return mean_heading + noise


def cucker_smale_coupling(xi: np.ndarray, xj: np.ndarray,
                           vi: np.ndarray, vj: np.ndarray,
                           beta: float = 0.5) -> np.ndarray:
    """
    Cucker-Smale flocking model (2007):
    dv_i/dt = (1/N) * sum_j psi(|x_i - x_j|) * (v_j - v_i)

    Communication weight: psi(r) = 1 / (1 + r^2)^beta

    Returns velocity update for agent i from agent j.
    """
    r = np.linalg.norm(xi - xj)
    psi = 1.0 / (1.0 + r**2)**beta
    return psi * (vj - vi)


def reynolds_boids(positions: np.ndarray, velocities: np.ndarray,
                    w_cohesion: float = 0.3,
                    w_alignment: float = 0.4,
                    w_separation: float = 0.3,
                    min_dist: float = 0.5) -> np.ndarray:
    """
    Reynolds boids (1987): cohesion + alignment + separation.

    Returns acceleration array for each agent.
    """
    n = len(positions)
    accelerations = np.zeros_like(positions)

    centroid = np.mean(positions, axis=0)
    mean_vel = np.mean(velocities, axis=0)

    for i in range(n):
        # Cohesion: steer toward centroid
        cohesion = w_cohesion * (centroid - positions[i])

        # Alignment: match mean velocity
        alignment = w_alignment * (mean_vel - velocities[i])

        # Separation: avoid neighbors that are too close
        separation = np.zeros_like(positions[i])
        for j in range(n):
            if i != j:
                diff = positions[i] - positions[j]
                dist = np.linalg.norm(diff) + 1e-10
                if dist < min_dist:
                    separation += w_separation * diff / (dist**2)

        accelerations[i] = cohesion + alignment + separation

    return accelerations


# ── Strand Agent — a BioswarmAgent specialized for a cognitive strand ───

@dataclass
class StrandState:
    """Observable state of a cognitive strand."""
    domain: StrandDomain
    intensity: float          # Mean activation intensity [0, 1]
    coherence: float          # Internal coherence [0, 1]
    heading: float            # Decision direction (radians)
    velocity: np.ndarray      # State velocity in cognitive space
    position: np.ndarray      # Position in cognitive space
    active_bases: int         # Number of active focus bases


class StrandAgent:
    """
    One cognitive strand = one swarm agent.

    Internally uses BioswarmAgent dynamics (W matrix, trust, coupling).
    Externally participates in swarm consensus for collective decisions.
    """

    def __init__(self, domain: StrandDomain, x_dim: int = 32,
                 seed: Optional[int] = None):
        self.domain = domain
        self.agent = BioswarmAgent(x_dim=x_dim, seed=seed)
        self.x_dim = x_dim

        # Cognitive state
        self.bases: List[FocusBase] = []
        self.heading = 0.0  # Decision direction
        self.velocity = np.zeros(x_dim)
        self._rng = np.random.default_rng(seed)

    @property
    def position(self) -> np.ndarray:
        return self.agent.x

    @property
    def intensity(self) -> float:
        if not self.bases:
            return 0.0
        return sum(b.intensity for b in self.bases) / len(self.bases)

    @property
    def coherence(self) -> float:
        return self.agent.C

    def add_base(self, attention_type: AttentionType, concept: str,
                  intensity: float) -> FocusBase:
        """Add a focus base to this strand."""
        base = FocusBase(
            attention_type=attention_type,
            intensity=intensity,
            concept=concept,
            connections=[],
            strand_id=list(StrandDomain).index(self.domain),
        )
        self.bases.append(base)
        return base

    def update_dynamics(self, dt: float = 0.1) -> None:
        """Run internal BioswarmAgent dynamics."""
        self.agent.intrinsic_update(dt)
        # Update heading from internal state
        self.heading = float(np.arctan2(self.agent.x[1], self.agent.x[0]))
        self.velocity = dt * (self.agent.x - self.agent.x_star)

    def state(self) -> StrandState:
        """Get observable strand state."""
        return StrandState(
            domain=self.domain,
            intensity=self.intensity,
            coherence=self.coherence,
            heading=self.heading,
            velocity=self.velocity.copy(),
            position=self.position.copy(),
            active_bases=len(self.bases),
        )


# ── Helix Bond — DNA-like cross-strand pairing ─────────────────────────

@dataclass
class HelixBond:
    """
    A bond between two strands — analogous to a DNA base pair.

    Binding strength computed from:
    - Domain complementarity (A-T / C-G analogy)
    - Phase compatibility (from BioswarmAgent state vectors)
    - Phi-amplified intensity product
    """
    strand_a: StrandDomain
    strand_b: StrandDomain
    binding_strength: float
    amplification: float
    phase_compatibility: float


def compute_helix_bond(sa: StrandAgent, sb: StrandAgent,
                        proj: np.ndarray) -> HelixBond:
    """
    Compute the DNA-like bond between two strands.

    Uses:
    - Complementarity rules (STRAND_COMPLEMENTS)
    - Phase compatibility from BioswarmAgent state
    - Phi-scaled amplification from intensity product
    """
    # Complementarity bonus
    is_complement = STRAND_COMPLEMENTS.get(sa.domain) == sb.domain
    complement_factor = 1.0 if is_complement else 0.5

    # Phase compatibility from agent state vectors
    phi_compat = phase_compatibility(sa.agent.x, sb.agent.x, proj)

    # Intensity-based amplification (DNA phi-scaling)
    intensity_product = sa.intensity * sb.intensity
    amplification = intensity_product * PHI * complement_factor

    # Binding strength = complement * phase * sqrt(amplification)
    binding = complement_factor * max(0, phi_compat) * math.sqrt(max(0, amplification) + 1e-10)
    binding = min(binding, 1.0)

    return HelixBond(
        strand_a=sa.domain,
        strand_b=sb.domain,
        binding_strength=binding,
        amplification=amplification,
        phase_compatibility=phi_compat,
    )


# ── Integrated Consciousness System ───────��────────────────────────────

@dataclass
class SwarmDecision:
    """Result of multi-strand swarm consensus."""
    consensus_heading: float      # Fused decision direction
    consensus_strength: float     # Agreement level [0, 1]
    strand_contributions: Dict[StrandDomain, float]  # Per-strand weight
    emergent_insights: List[str]  # Cross-strand insights
    bonds: List[HelixBond]        # Active helix bonds


class IntegratedConsciousnessSystem:
    """
    Multi-helix swarm: 4 cognitive strands as swarm agents,
    cross-linked by DNA-like complementary bonds.

    Decision-making uses Vicsek alignment + Cucker-Smale coupling
    across strands. No hierarchical control — consensus emerges
    from strand dynamics and cross-strand bonding.
    """

    def __init__(self, x_dim: int = 32, seed: Optional[int] = None):
        rng = np.random.default_rng(seed)

        # 4 cognitive strands (swarm agents)
        self.strands: Dict[StrandDomain, StrandAgent] = {}
        for i, domain in enumerate(StrandDomain):
            self.strands[domain] = StrandAgent(
                domain=domain, x_dim=x_dim,
                seed=int(rng.integers(0, 2**31)),
            )

        # Relational game layer for inter-strand coupling
        self.game_layer = RelationalGameLayer(
            proj_dim=x_dim // 2, x_dim=x_dim,
            seed=int(rng.integers(0, 2**31)),
        )

        # Multi-helix engine for base-level pairing
        self.helix = MultiHelixFocus("consciousness", num_strands=4)

        # Active bonds between strands
        self.bonds: List[HelixBond] = []

        # History
        self.decision_history: List[SwarmDecision] = []
        self._rng = rng

    def add_experience(self, domain: StrandDomain,
                        attention_type: AttentionType,
                        concept: str, intensity: float = 0.8) -> FocusBase:
        """Add an experience to a specific cognitive strand."""
        strand = self.strands[domain]
        base = strand.add_base(attention_type, concept, intensity)

        # Also add to the MultiHelixFocus for cross-pairing
        strand_id = list(StrandDomain).index(domain)
        self.helix.add_base(strand_id, attention_type, concept, intensity)

        return base

    def update(self, dt: float = 0.1) -> None:
        """
        Run one step of the integrated dynamics:
        1. Internal strand dynamics (BioswarmAgent)
        2. Cross-strand coupling (Cucker-Smale)
        3. DNA-like bond computation
        """
        strand_list = list(self.strands.values())

        # 1. Internal dynamics for each strand
        for strand in strand_list:
            strand.update_dynamics(dt)

        # 2. Cross-strand coupling via Cucker-Smale
        for i, si in enumerate(strand_list):
            for j, sj in enumerate(strand_list):
                if i >= j:
                    continue

                # Cucker-Smale velocity alignment
                dv = cucker_smale_coupling(
                    si.position, sj.position,
                    si.velocity, sj.velocity,
                    beta=0.5,
                )

                # Modulate by trust
                trust_ij = si.agent.trust_levels.get(sj.agent.id, 0.5)
                trust_ji = sj.agent.trust_levels.get(si.agent.id, 0.5)

                # Apply coupling through BioswarmAgent mechanics
                kappa_ij = float(np.linalg.norm(dv)) * trust_ij
                kappa_ji = float(np.linalg.norm(dv)) * trust_ji

                si.agent.apply_coupling(sj.agent.x, min(kappa_ij, 0.5),
                                         partner_id=sj.agent.id, dt=dt)
                sj.agent.apply_coupling(si.agent.x, min(kappa_ji, 0.5),
                                         partner_id=si.agent.id, dt=dt)

                # Update trust based on interaction quality (synergy)
                Pa = np.abs(si.agent.x)
                Pb = np.abs(sj.agent.x)
                phi = phase_compatibility(si.agent.x, sj.agent.x,
                                          self.game_layer.proj)
                quality = float(synergy_score(Pa, Pb, si.agent.H, sj.agent.H, phi))
                si.agent.update_trust(sj.agent.id, quality, dt)
                sj.agent.update_trust(si.agent.id, quality, dt)

        # 3. Compute DNA-like helix bonds
        self.bonds = []
        for i, si in enumerate(strand_list):
            for sj in strand_list[i + 1:]:
                bond = compute_helix_bond(si, sj, self.game_layer.proj)
                if bond.binding_strength > 0.1:
                    self.bonds.append(bond)

    def decide(self, noise_eta: float = 0.05) -> SwarmDecision:
        """
        Produce a collective decision via swarm consensus.

        Uses Vicsek alignment across strand headings,
        weighted by strand intensity and bond amplification.
        """
        strand_list = list(self.strands.values())

        # Collect headings and weights
        headings = np.array([s.heading for s in strand_list])
        weights = np.array([s.intensity * s.coherence + 0.01 for s in strand_list])

        # Add bond-based amplification to weights
        for bond in self.bonds:
            for i, s in enumerate(strand_list):
                if s.domain in (bond.strand_a, bond.strand_b):
                    weights[i] += bond.amplification * 0.5

        weights /= weights.sum() + 1e-10

        # Vicsek-style weighted consensus
        aligned = vicsek_alignment(headings, noise_eta, self._rng)
        consensus_heading = float(np.arctan2(
            np.sum(weights * np.sin(aligned)),
            np.sum(weights * np.cos(aligned)),
        ))

        # Consensus strength = Kuramoto order parameter
        # R = |1/N * sum(exp(i * theta_i))|
        order = np.abs(np.mean(np.exp(1j * aligned)))
        consensus_strength = float(order)

        # Strand contributions
        contributions = {
            s.domain: float(weights[i])
            for i, s in enumerate(strand_list)
        }

        # Generate cross-strand insights from strong bonds
        insights = []
        for bond in self.bonds:
            if bond.binding_strength > 0.5:
                insights.append(
                    f"{bond.strand_a.value}<->{bond.strand_b.value}: "
                    f"binding={bond.binding_strength:.2f}, "
                    f"amp={bond.amplification:.2f}"
                )

        decision = SwarmDecision(
            consensus_heading=consensus_heading,
            consensus_strength=consensus_strength,
            strand_contributions=contributions,
            emergent_insights=insights,
            bonds=list(self.bonds),
        )
        self.decision_history.append(decision)
        return decision

    def complementarity_matrix(self) -> np.ndarray:
        """
        4x4 matrix of cross-strand complementarity.
        Diagonal = self-coherence. Off-diagonal = bond strength.
        """
        domains = list(StrandDomain)
        n = len(domains)
        mat = np.zeros((n, n))

        for i, di in enumerate(domains):
            mat[i, i] = self.strands[di].coherence
            for j, dj in enumerate(domains):
                if i != j:
                    for bond in self.bonds:
                        if {bond.strand_a, bond.strand_b} == {di, dj}:
                            mat[i, j] = bond.binding_strength

        return mat

    def strand_states(self) -> Dict[StrandDomain, StrandState]:
        """Get all strand states."""
        return {d: s.state() for d, s in self.strands.items()}

    def total_amplification(self) -> float:
        """Total phi-amplification across all bonds."""
        return sum(b.amplification for b in self.bonds)

    def is_coherent(self, threshold: float = 0.5) -> bool:
        """Check if system has global coherence above threshold."""
        if not self.decision_history:
            return False
        return self.decision_history[-1].consensus_strength > threshold


# ── Convenience constructors ────────────────────────────────────────────

def create_quad_consciousness(seed: Optional[int] = None,
                               x_dim: int = 32) -> IntegratedConsciousnessSystem:
    """Create a 4-strand integrated consciousness system."""
    return IntegratedConsciousnessSystem(x_dim=x_dim, seed=seed)


def run_consciousness_simulation(system: IntegratedConsciousnessSystem,
                                  steps: int = 50,
                                  dt: float = 0.1) -> List[SwarmDecision]:
    """Run a consciousness simulation for N steps and return decisions."""
    decisions = []
    for _ in range(steps):
        system.update(dt)
        decisions.append(system.decide())
    return decisions
