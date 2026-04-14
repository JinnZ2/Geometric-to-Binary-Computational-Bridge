"""
32-state rhombic-triacontahedral Gaussian splats.

Replaces the 8-corner cube of the octahedral layer with the 32 vertices
of the rhombic triacontahedron. These vertices are exactly the union of
a regular dodecahedron (20) and a regular icosahedron (12) inscribed in
the same sphere, giving 32 discrete symbolic states (5 bits per splat).

The continuous state lives on (or near) the unit sphere in R^3; a
:class:`SphericalManifoldConstraint` uses a log-sum-exp of Gaussian
wells at each vertex to generate a smooth attraction force.

.. note::

    The draft code in ``docs/gaussian_splats/04_rhombic_triaconta_32state.md``
    contained a subtle bug: it generated the 12 "cyclic permutations of
    ``(0, +/- phi, +/- 1/phi)``" *twice* (once directly and once as
    "permutations of ``(+/- 1/phi, 0, +/- phi)``"), producing only 8+12=20
    unique vertices after ``np.unique`` instead of the expected 32. This
    module computes the canonical 32 vertices explicitly:

    - 8 dodecahedron cube corners ``(+/- 1, +/- 1, +/- 1)``,
    - 12 dodecahedron non-cube vertices (cyclic permutations of
      ``(0, +/- 1/phi, +/- phi)``),
    - 12 icosahedron vertices (cyclic permutations of
      ``(0, +/- 1, +/- phi)``).

Extracted from ``docs/gaussian_splats/04_rhombic_triaconta_32state.md``.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import multivariate_normal


class RhombicTriacontaEncoder:
    """Generates and queries the 32 vertices of the rhombic triacontahedron.

    The continuous state vector lives in R^3 and is attracted to these
    vertices. ``vertices`` is a ``(32, 3)`` array of unit-norm direction
    vectors.
    """

    def __init__(self):
        self.vertices = self._generate_vertices()
        self.num_states = 32

    @staticmethod
    def _generate_vertices():
        """Generate the 32 unit-sphere vertices (20 dodecahedral + 12 icosahedral).

        Uses the canonical coordinate sets
        (see https://en.wikipedia.org/wiki/Rhombic_triacontahedron), then
        normalizes each vertex to the unit sphere.
        """
        phi = (1 + np.sqrt(5)) / 2
        inv_phi = 1.0 / phi

        verts = []

        # Dodecahedron: 8 cube corners (+/-1, +/-1, +/-1).
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    verts.append((sx, sy, sz))

        # Dodecahedron: 12 cyclic permutations of (0, +/- 1/phi, +/- phi).
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                verts.append((0.0,            s1 * inv_phi, s2 * phi))
                verts.append((s1 * inv_phi,   s2 * phi,     0.0))
                verts.append((s2 * phi,       0.0,          s1 * inv_phi))

        # Icosahedron: 12 cyclic permutations of (0, +/- 1, +/- phi).
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                verts.append((0.0,        s1,        s2 * phi))
                verts.append((s1,         s2 * phi,  0.0))
                verts.append((s2 * phi,   0.0,       s1))

        arr = np.array(verts, dtype=float)
        assert arr.shape == (32, 3), f"expected 32 vertices, got {arr.shape[0]}"

        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / norms

    def nearest_state(self, s):
        """Return the index of the closest vertex to continuous ``s``."""
        dists = np.linalg.norm(self.vertices - np.asarray(s), axis=1)
        return int(np.argmin(dists))

    def vertex_moment(self, state_idx, magnitude=1.0):
        """Magnetic moment vector for a given state (aligned with vertex)."""
        return magnitude * self.vertices[state_idx]


class Gaussian32FieldSource:
    """6D Gaussian over ``(x, y, z, s1, s2, s3)`` with 32 rhombic states.

    Same structure as :class:`Engine.gaussian_splats.Gaussian8FieldSource`
    but with 32 target state centers on the unit sphere instead of 8 cube
    corners.
    """

    def __init__(self, mu, cov, charge=1.0, encoder=None):
        self.mu = np.asarray(mu, dtype=float)
        self.cov = np.asarray(cov, dtype=float)
        self.charge = float(charge)
        self.encoder = encoder if encoder is not None else RhombicTriacontaEncoder()

        if self.mu.shape != (6,):
            raise ValueError(f"mu must have shape (6,), got {self.mu.shape}")
        if self.cov.shape != (6, 6):
            raise ValueError(f"cov must have shape (6, 6), got {self.cov.shape}")

    def condition_on_state(self, state_idx):
        """Return spatial ``(mean, cov)`` conditioned on vertex ``state_idx``."""
        s_k = self.encoder.vertices[state_idx]
        mu_xyz = self.mu[:3]
        mu_s = self.mu[3:6]

        cov_xyz = self.cov[:3, :3]
        cov_xs = self.cov[:3, 3:6]
        cov_sx = self.cov[3:6, :3]
        cov_ss = self.cov[3:6, 3:6]

        inv_cov_ss = np.linalg.inv(cov_ss + 1e-8 * np.eye(3))
        ds = s_k - mu_s
        mu_cond = mu_xyz + cov_xs @ inv_cov_ss @ ds
        cov_cond = cov_xyz - cov_xs @ inv_cov_ss @ cov_sx
        cov_cond = (cov_cond + cov_cond.T) / 2.0
        return mu_cond, cov_cond

    def state_probabilities(self):
        """Return a length-32 probability vector over the rhombic vertices."""
        mu_s = self.mu[3:6]
        cov_ss = self.cov[3:6, 3:6]
        mvn = multivariate_normal(mean=mu_s, cov=cov_ss, allow_singular=True)
        probs = np.array(
            [mvn.pdf(self.encoder.vertices[i]) for i in range(self.encoder.num_states)]
        )
        total = probs.sum()
        if total > 0:
            probs = probs / total
        else:
            probs = np.ones(self.encoder.num_states) / self.encoder.num_states
        return probs

    def most_likely_state(self):
        """Return the vertex index with the highest marginal mass."""
        return int(np.argmax(self.state_probabilities()))


class ZeemanDynamics32:
    """Soft magnetic coupling across the 32 rhombic vertices.

    Same ``E = -m(s) . B_ext`` form as the 8-state version, but the
    effective moment ``m(s)`` is a softmax-weighted blend of all 32
    vertex moments.
    """

    def __init__(self, encoder=None, moment_magnitude=1.0, mobility=1.0,
                 temperature=0.03, softmax_beta=15.0):
        self.encoder = encoder if encoder is not None else RhombicTriacontaEncoder()
        self.m0 = float(moment_magnitude)
        self.gamma = float(mobility)
        self.kBT = float(temperature)
        self.softmax_beta = float(softmax_beta)

    def compute_moment(self, s):
        """Softmax-weighted interpolation of vertex moments."""
        centers = self.encoder.vertices
        dists = np.linalg.norm(centers - np.asarray(s), axis=1)
        weights = np.exp(-self.softmax_beta * dists)
        weights /= weights.sum()
        moment = np.zeros(3)
        for i in range(self.encoder.num_states):
            moment += weights[i] * self.encoder.vertex_moment(i, self.m0)
        return moment

    def force(self, s, B_ext):
        """Compute ``F_s = -grad_s E`` via central differences."""
        eps = 1e-5
        s = np.asarray(s, dtype=float)
        force = np.zeros(3)
        for i in range(3):
            s_plus = s.copy()
            s_plus[i] += eps
            s_minus = s.copy()
            s_minus[i] -= eps
            E_plus = -np.dot(self.compute_moment(s_plus), B_ext)
            E_minus = -np.dot(self.compute_moment(s_minus), B_ext)
            force[i] = -(E_plus - E_minus) / (2 * eps)
        return force


class SphericalManifoldConstraint:
    """Log-sum-exp potential attracting ``s`` to the 32 vertices.

    ::

        U(s) = -kappa * log( sum_k exp(-|s - v_k|^2 / (2 sigma^2)) )

    The force is a weighted sum of attractions toward each vertex, with
    the nearest vertices dominating. Analytically differentiable, so it
    composes cleanly with Zeeman dynamics in a Langevin update.
    """

    def __init__(self, encoder=None, kappa=5.0, sigma=0.3):
        self.encoder = encoder if encoder is not None else RhombicTriacontaEncoder()
        self.kappa = float(kappa)
        self.sigma2 = float(sigma) ** 2

    def force(self, s):
        """Return ``-grad U`` at continuous state ``s``."""
        centers = self.encoder.vertices
        diffs = centers - np.asarray(s)  # (32, 3)
        dists2 = np.sum(diffs ** 2, axis=1)
        # Subtract min for numerical stability before exp.
        dists2_norm = dists2 - np.min(dists2)
        weights = np.exp(-dists2_norm / (2 * self.sigma2))
        Z = np.sum(weights)
        grad_log = np.sum(weights[:, np.newaxis] * diffs, axis=0) / (Z * self.sigma2)
        return self.kappa * grad_log
