"""
8-state octahedral Gaussian splats.

Builds on the 4D splat layer by replacing the scalar time dimension with
a 3D continuous state vector ``s = (s1, s2, s3) in [-1, 1]^3``. The 8
corners of the cube correspond to the 8 octahedral symbolic states
(000..111), grounded in silicon's sp3 tetrahedral geometry (109.47 deg).

Each :class:`Gaussian8FieldSource` is a 6D Gaussian over ``(x, y, z, s)``
whose cross-covariance ``Sigma_xs`` encodes how the spatial mean shifts
as the state drifts between corners. Conditioning on a particular state
index collapses the 6D Gaussian to a 3D spatial Gaussian for that state.

Two coupled dynamical components keep the state physically meaningful:

- :class:`ZeemanDynamics` computes a soft, state-dependent magnetic
  moment by interpolating the per-corner tetrahedral moments and derives
  the force ``F = grad(m . B_ext)`` that drives transitions.
- :class:`ManifoldConstraint` adds a quartic potential
  ``U(s) = kappa * sum((s_i^2 - 1)^2)`` with minima exactly at the 8
  cube corners, preventing the state from wandering into "no-mans-land".

Extracted and reconciled from ``docs/gaussian_splats/02_octahedral_encoder.md``
and ``docs/gaussian_splats/03_8field_zeeman_manifold.md``.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import multivariate_normal


class OctahedralStateEncoder:
    """Maps 3-bit symbolic states to canonical tetrahedral covariance patterns.

    Provides two complementary state embeddings:

    - ``state_centers`` : the 8 cube corners in [-1, 1]^3, used as the
      canonical target points for the 6D Gaussian's state subspace.
    - ``STATE_PROFILES`` : a per-state record giving a primary
      tetrahedral axis index (into :attr:`TETRA_VECTORS`), a secondary
      axis, and an eigenvalue profile ``(lam1, lam2, lam3)`` that sums
      to 1 and controls the spatial-covariance anisotropy of a splat
      occupying that state.

    Reconciles two independent definitions from the design notes: the
    encoder in ``02_octahedral_encoder.md`` with ``encode_state_to_gaussian``
    /``decode_gaussian_to_state``, and the encoder in
    ``03_8field_zeeman_manifold.md`` with ``state_centers`` /
    ``nearest_state``. Both feature sets are merged here.
    """

    #: Four vertices of a regular tetrahedron, normalized to unit length.
    TETRA_VECTORS = np.array(
        [
            [1, 1, 1],
            [1, -1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
        ],
        dtype=float,
    ) / np.sqrt(3)

    #: Canonical per-state profiles. The eigenvalue triple (lam1, lam2,
    #: lam3) sums to 1 and governs spatial-covariance anisotropy. State
    #: 0b111 is the isotropic equilibrium node with no primary axis.
    STATE_PROFILES = {
        0b000: {"primary": 0, "secondary": 1, "eig": (0.6, 0.2, 0.2),
                "desc": "North apex - low potential"},
        0b001: {"primary": 1, "secondary": 2, "eig": (0.2, 0.6, 0.2),
                "desc": "South apex - low potential"},
        0b010: {"primary": 0, "secondary": 2, "eig": (0.5, 0.3, 0.2),
                "desc": "East ridge - strain aligned"},
        0b011: {"primary": 1, "secondary": 3, "eig": (0.3, 0.5, 0.2),
                "desc": "West ridge - compressive alignment"},
        0b100: {"primary": 2, "secondary": 0, "eig": (0.4, 0.2, 0.4),
                "desc": "Front face - conductive bias"},
        0b101: {"primary": 2, "secondary": 3, "eig": (0.2, 0.4, 0.4),
                "desc": "Back face - magnetic bias"},
        0b110: {"primary": 3, "secondary": 0, "eig": (0.4, 0.4, 0.2),
                "desc": "Axial symmetry - resonance coupling"},
        0b111: {"primary": None, "secondary": None, "eig": (1 / 3, 1 / 3, 1 / 3),
                "desc": "Stable equilibrium node"},
    }

    def __init__(self, spatial_scale=1.0, temporal_scale=0.5, velocity_scale=1.0):
        self.spatial_scale = spatial_scale
        self.temporal_scale = temporal_scale
        self.velocity_scale = velocity_scale
        self.state_centers = self._build_state_centers()

    @staticmethod
    def _build_state_centers():
        """Return the 8 cube corners in [-1, 1]^3 ordered by bit index."""
        centers = np.zeros((8, 3))
        for i in range(8):
            centers[i, 0] = -1.0 if (i & 1) == 0 else 1.0
            centers[i, 1] = -1.0 if (i & 2) == 0 else 1.0
            centers[i, 2] = -1.0 if (i & 4) == 0 else 1.0
        return centers

    def nearest_state(self, s):
        """Return the integer state index closest to continuous vector ``s``."""
        distances = np.linalg.norm(self.state_centers - np.asarray(s), axis=1)
        return int(np.argmin(distances))

    def _build_basis(self, profile):
        """Construct an orthonormal spatial basis from the state profile."""
        if profile["primary"] is None:
            return np.eye(3)
        a1 = self.TETRA_VECTORS[profile["primary"]]
        a2_candidate = self.TETRA_VECTORS[profile["secondary"]]
        a2 = a2_candidate - np.dot(a2_candidate, a1) * a1
        a2 /= np.linalg.norm(a2)
        a3 = np.cross(a1, a2)
        return np.column_stack([a1, a2, a3])

    def encode_state_to_gaussian(self, state_bits, position, time, charge=1.0):
        """Build a :class:`Gaussian4DSource` from a 3-bit state label.

        The spatial covariance is aligned with the state's primary
        tetrahedral axis, and the velocity (encoded via cross-covariance
        in the 4th dimension) points along that same axis.
        """
        # Local import to avoid a circular dependency between the 4D and
        # octahedral layers when both are imported via the package.
        from Engine.gaussian_splats.gaussian_4d import Gaussian4DSource

        profile = self.STATE_PROFILES[state_bits]
        eig = np.array(profile["eig"])
        cov_eig = eig * (self.spatial_scale ** 2)

        basis = self._build_basis(profile)
        cov_xyz = basis @ np.diag(cov_eig) @ basis.T

        if profile["primary"] is not None:
            velocity = basis[:, 0] * self.velocity_scale
        else:
            velocity = np.zeros(3)

        sigma_t2 = self.temporal_scale ** 2
        cov_xyzt = velocity * sigma_t2

        cov_4d = np.zeros((4, 4))
        cov_4d[:3, :3] = cov_xyz
        cov_4d[:3, 3] = cov_xyzt
        cov_4d[3, :3] = cov_xyzt
        cov_4d[3, 3] = sigma_t2

        mu = np.array([position[0], position[1], position[2], time])
        return Gaussian4DSource(mu, cov_4d, charge=charge)

    def decode_gaussian_to_state(self, gaussian, time=None):
        """Classify a :class:`Gaussian4DSource` to its nearest octahedral state.

        Compares the dominant eigenvector of the spatial covariance to
        the four tetrahedral axes and returns ``(state_bits, confidence)``.
        """
        if time is not None:
            _, cov_cond = gaussian.condition_on_time(time)
        else:
            cov_cond = gaussian.cov[:3, :3]

        eigvals, eigvecs = np.linalg.eigh(cov_cond)
        idx = np.argsort(eigvals)[::-1]
        eigvecs = eigvecs[:, idx]
        primary_vec = eigvecs[:, 0]

        dots = np.abs(self.TETRA_VECTORS @ primary_vec)
        best_axis = int(np.argmax(dots))

        state_map = {0: 0b000, 1: 0b001, 2: 0b010, 3: 0b011}
        return state_map.get(best_axis, 0b111), float(dots[best_axis])


class Gaussian8FieldSource:
    """6D Gaussian over ``(x, y, z, s1, s2, s3)`` with 8 cube-corner states.

    The state subspace lives in ``[-1, 1]^3`` and its cross-covariance
    ``Sigma_xs`` couples symbolic state to spatial position. Conditioning
    on a particular state index yields a 3D spatial Gaussian for the
    field corresponding to that symbolic label.
    """

    def __init__(self, mu, cov, charge=1.0):
        self.mu = np.asarray(mu, dtype=float)
        self.cov = np.asarray(cov, dtype=float)
        self.charge = float(charge)
        self.encoder = OctahedralStateEncoder()

        if self.mu.shape != (6,):
            raise ValueError(f"mu must have shape (6,), got {self.mu.shape}")
        if self.cov.shape != (6, 6):
            raise ValueError(f"cov must have shape (6, 6), got {self.cov.shape}")

    def condition_on_state(self, state_idx):
        """Return spatial ``(mean, cov)`` conditioned on discrete ``state_idx``."""
        s_k = self.encoder.state_centers[state_idx]
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

    def evaluate_field_for_state(self, points, state_idx):
        """Evaluate charge-weighted density for the given state field."""
        mu_cond, cov_cond = self.condition_on_state(state_idx)
        mvn = multivariate_normal(mean=mu_cond, cov=cov_cond, allow_singular=True)
        state_weight = self._state_marginal_weight(state_idx)
        return self.charge * state_weight * mvn.pdf(np.asarray(points))

    def evaluate_all_fields(self, points):
        """Return a ``(N, 8)`` array of per-state densities at ``points``."""
        points = np.asarray(points)
        densities = np.zeros((len(points), 8))
        for k in range(8):
            densities[:, k] = self.evaluate_field_for_state(points, k)
        return densities

    def _state_marginal_weight(self, state_idx):
        s_k = self.encoder.state_centers[state_idx]
        mu_s = self.mu[3:6]
        cov_ss = self.cov[3:6, 3:6]
        mvn = multivariate_normal(mean=mu_s, cov=cov_ss, allow_singular=True)
        return float(mvn.pdf(s_k))

    def state_probabilities(self):
        """Return a length-8 probability vector over the 8 corners."""
        mu_s = self.mu[3:6]
        cov_ss = self.cov[3:6, 3:6]
        mvn = multivariate_normal(mean=mu_s, cov=cov_ss, allow_singular=True)
        probs = np.array(
            [mvn.pdf(self.encoder.state_centers[i]) for i in range(8)]
        )
        total = probs.sum()
        if total > 0:
            probs = probs / total
        else:
            probs = np.ones(8) / 8
        return probs

    def most_likely_state(self):
        """Return the integer state index with the highest marginal mass."""
        return int(np.argmax(self.state_probabilities()))

    def state_collapse(self):
        """Return a :class:`DistributionCollapse` over the 8 corners.

        Preserves the full distribution shape (dominant index, runner-up,
        entropy, ternary regime) instead of discarding everything but
        the argmax. ``state_collapse().dominant_index`` matches
        ``most_likely_state()`` exactly — this is a non-breaking
        superset view.
        """
        from bridges.probability_collapse import collapse_distribution

        return collapse_distribution(self.state_probabilities().tolist())


class ZeemanDynamics:
    """Soft magnetic coupling for 6D octahedral splats: ``E = -m(s) . B_ext``.

    Each of the 8 corner states carries a canonical moment vector
    aligned with its primary tetrahedral axis. For continuous ``s``, the
    effective moment is a softmax-weighted interpolation of the corner
    moments, which makes the Zeeman force smooth and differentiable.
    """

    def __init__(self, encoder=None, moment_magnitude=1.0, mobility=1.0,
                 temperature=0.05, softmax_beta=10.0):
        self.encoder = encoder if encoder is not None else OctahedralStateEncoder()
        self.m0 = float(moment_magnitude)
        self.gamma = float(mobility)
        self.kBT = float(temperature)
        self.softmax_beta = float(softmax_beta)
        self.state_moments = self._compute_state_moments()

    def _compute_state_moments(self):
        moments = {}
        for state in range(8):
            profile = self.encoder.STATE_PROFILES[state]
            if profile["primary"] is not None:
                axis = self.encoder.TETRA_VECTORS[profile["primary"]]
                moments[state] = self.m0 * axis
            else:
                moments[state] = np.zeros(3)
        return moments

    def compute_moment(self, s):
        """Return the interpolated magnetic moment at continuous ``s``."""
        centers = self.encoder.state_centers
        dists = np.linalg.norm(centers - np.asarray(s), axis=1)
        weights = np.exp(-self.softmax_beta * dists)
        weights /= weights.sum()
        moment = np.zeros(3)
        for state in range(8):
            moment += weights[state] * self.state_moments[state]
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


class ManifoldConstraint:
    """Quartic potential ``U(s) = kappa * sum((s_i^2 - 1)^2)``.

    Has 8 equal minima at the cube corners ``s_i = +/- 1``. Keeps the
    octahedral state near valid symbolic states during Langevin updates.
    """

    def __init__(self, kappa=5.0):
        self.kappa = float(kappa)

    def potential(self, s):
        s = np.asarray(s, dtype=float)
        return self.kappa * np.sum((s ** 2 - 1) ** 2)

    def force(self, s):
        """Return ``-grad_s U = -4 kappa (s^2 - 1) s``."""
        s = np.asarray(s, dtype=float)
        return -4 * self.kappa * (s ** 2 - 1) * s
