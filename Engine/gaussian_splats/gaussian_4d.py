"""
4D Gaussian splats over spacetime (x, y, z, t).

A Gaussian4DSource is a 4D multivariate normal whose mean lives in R^4
and whose 4x4 covariance encodes spatial spread, temporal spread, and
instantaneous motion (via space-time cross-covariance).

For a splat moving with velocity v = (vx, vy, vz), the natural
parameterization is::

    cov = [ [sigma_x^2, 0, 0, vx * sigma_t^2],
            [0, sigma_y^2, 0, vy * sigma_t^2],
            [0, 0, sigma_z^2, vz * sigma_t^2],
            [vx*sigma_t^2, vy*sigma_t^2, vz*sigma_t^2, sigma_t^2] ]

Conditioning on a specific time t0 collapses the 4D Gaussian to a
3D Gaussian whose mean has drifted along v by (t0 - mu_t) and whose
spatial covariance is slightly tighter than the marginal.

This module also defines :class:`GeometricEMSolver4D`, a thin subclass
of :class:`Engine.geometric_solver.GeometricEMSolver` that reuses the
adaptive spatial grid for time-sliced field evaluation of 4D sources.

Extracted from ``docs/gaussian_splats/01_4d_splats.md``.
"""

from __future__ import annotations

import time

import numpy as np
from scipy.stats import multivariate_normal

from Engine.geometric_solver import GeometricEMSolver


class Gaussian4DSource:
    """4D Gaussian primitive over (x, y, z, t).

    Parameters
    ----------
    mu : array-like of shape (4,), optional
        Mean in spacetime. Defaults to the origin.
    cov : array-like of shape (4, 4), optional
        Covariance matrix. Defaults to the identity.
    charge : float, optional
        Amplitude used when rendering. Defaults to 1.0.
    color : array-like of shape (3,), optional
        RGB color used by the frontend visualizer. Defaults to red.
    """

    def __init__(self, mu=None, cov=None, charge=1.0, color=None):
        self.mu = np.array(mu, dtype=np.float64) if mu is not None else np.zeros(4)
        self.cov = np.array(cov, dtype=np.float64) if cov is not None else np.eye(4)
        self.charge = float(charge)
        self.color = (
            np.array(color, dtype=np.float64)
            if color is not None
            else np.array([1.0, 0.0, 0.0])
        )

        if self.mu.shape != (4,):
            raise ValueError(f"mu must have shape (4,), got {self.mu.shape}")
        if self.cov.shape != (4, 4):
            raise ValueError(f"cov must have shape (4, 4), got {self.cov.shape}")

    def condition_on_time(self, t0, min_cov=1e-6):
        """Condition the 4D Gaussian on a specific time ``t0``.

        Returns the mean and covariance of the resulting 3D Gaussian slice::

            mu_cond  = mu_xyz + cov_xyzt * cov_tt^-1 * (t0 - mu_t)
            cov_cond = cov_xyz - cov_xyzt * cov_tt^-1 * cov_xyzt^T
        """
        mu_xyz = self.mu[:3]
        mu_t = self.mu[3]

        cov_xyz = self.cov[:3, :3]
        cov_xyzt = self.cov[:3, 3]
        cov_tt = self.cov[3, 3]

        dt = t0 - mu_t
        inv_cov_tt = 1.0 / (cov_tt + 1e-12)

        mu_cond = mu_xyz + cov_xyzt * inv_cov_tt * dt
        cov_cond = cov_xyz - inv_cov_tt * np.outer(cov_xyzt, cov_xyzt)

        # Ensure symmetry and positive definiteness.
        cov_cond = (cov_cond + cov_cond.T) / 2.0
        eigvals = np.linalg.eigvalsh(cov_cond)
        if np.min(eigvals) < min_cov:
            cov_cond = cov_cond + np.eye(3) * (min_cov - np.min(eigvals))

        return mu_cond, cov_cond

    def evaluate_density_3d(self, points, t0):
        """Evaluate charge-weighted density at ``points`` (N, 3) at time ``t0``."""
        mu_cond, cov_cond = self.condition_on_time(t0)
        mvn = multivariate_normal(mean=mu_cond, cov=cov_cond, allow_singular=True)
        return self.charge * mvn.pdf(np.asarray(points))

    def get_velocity(self):
        """Extract instantaneous velocity from the cross-covariance.

        Returns ``cov_xyzt / cov_tt`` if ``cov_tt > 0``, otherwise zeros.
        """
        cov_tt = self.cov[3, 3]
        if cov_tt <= 0:
            return np.zeros(3)
        return self.cov[:3, 3] / cov_tt


class SIMDOptimizer4D:
    """Vectorized field evaluator for 4D Gaussian sources."""

    @staticmethod
    def calculate_field_chunk_4d(points, sources, t0):
        """Reference implementation using :mod:`scipy.stats.multivariate_normal`.

        Preferred for clarity; see :meth:`calculate_field_chunk_4d_batch`
        for the vectorized hot path.
        """
        points = np.asarray(points)
        if len(points) == 0 or not sources:
            return np.zeros(len(points))

        density = np.zeros(len(points))
        for src in sources:
            mu_cond, cov_cond = src.condition_on_time(t0)
            mvn = multivariate_normal(mean=mu_cond, cov=cov_cond, allow_singular=True)
            density += src.charge * mvn.pdf(points)
        return density

    @staticmethod
    def calculate_field_chunk_4d_batch(points, sources, t0):
        """Vectorized batch evaluator.

        Computes the Mahalanobis distance and normalization constant once
        per source, then uses a single ``einsum`` across all query points.
        """
        points = np.asarray(points)
        n_points = len(points)
        if n_points == 0 or not sources:
            return np.zeros(n_points)

        density = np.zeros(n_points)
        for src in sources:
            mu_cond, cov_cond = src.condition_on_time(t0)
            inv_cov = np.linalg.inv(cov_cond)
            det_cov = np.linalg.det(cov_cond)
            norm_factor = 1.0 / np.sqrt((2 * np.pi) ** 3 * max(det_cov, 1e-18))

            diff = points - mu_cond  # (N, 3)
            maha_sq = np.einsum("ij,jk,ik->i", diff, inv_cov, diff)
            density += src.charge * norm_factor * np.exp(-0.5 * maha_sq)

        return density


class GeometricEMSolver4D(GeometricEMSolver):
    """Extends :class:`GeometricEMSolver` with a 4D time-sliced field method.

    The adaptive spatial grid is reused: each 4D source is conditioned to
    its spatial mean at ``t0`` so the existing octree refinement logic
    still applies.
    """

    def calculate_field_4d(self, sources_4d, bounds, t0, resolution=32):
        """Compute the conditioned density field at time ``t0``.

        Parameters
        ----------
        sources_4d : list[Gaussian4DSource]
        bounds : dict
            ``{"min": [xmin, ymin, zmin], "max": [xmax, ymax, zmax]}``
        t0 : float
            Time at which to evaluate the field.
        resolution : int, optional
            Fallback uniform-grid resolution (unused when the adaptive
            octree decides for itself).

        Returns
        -------
        dict
            ``{"density": [...], "points": [...], "time": float}``
        """
        self.sources_4d = sources_4d
        t_start = time.perf_counter()

        if not sources_4d:
            return {"density": [], "points": [], "time": 0.0}

        # Project 4D sources to point sources for octree refinement.
        point_sources = []
        for src in sources_4d:
            mu_cond, _ = src.condition_on_time(t0)
            point_sources.append(
                {"position": mu_cond.tolist(), "strength": src.charge}
            )

        regions = self.spatialGrid.adaptiveDecomposition(bounds, point_sources)

        all_points = []
        all_density = []
        for region in regions:
            pts = np.array(region["points"])
            if len(pts) == 0:
                continue
            dens = SIMDOptimizer4D.calculate_field_chunk_4d_batch(
                pts, sources_4d, t0
            )
            all_points.extend(region["points"])
            all_density.extend(dens.tolist())

        return {
            "density": all_density,
            "points": all_points,
            "time": time.perf_counter() - t_start,
        }


def bhattacharyya_distance(src1, src2, t):
    """Bhattacharyya distance between two 4D splats at time ``t``.

    ::

        D_B = (1/8) (mu1 - mu2)^T Sigma^-1 (mu1 - mu2)
              + (1/2) log( det(Sigma) / sqrt(det(Sigma1) det(Sigma2)) )

    where ``Sigma = (Sigma1 + Sigma2) / 2``. Used to measure splat overlap
    (e.g. collision candidates). Returns 0 for identical splats.
    """
    mu1, cov1 = src1.condition_on_time(t)
    mu2, cov2 = src2.condition_on_time(t)

    cov_avg = (cov1 + cov2) / 2.0
    diff = mu1 - mu2
    inv_cov_avg = np.linalg.inv(cov_avg)

    term1 = diff @ inv_cov_avg @ diff / 8.0
    det_avg = max(np.linalg.det(cov_avg), 1e-18)
    det1 = max(np.linalg.det(cov1), 1e-18)
    det2 = max(np.linalg.det(cov2), 1e-18)
    term2 = 0.5 * np.log(det_avg / np.sqrt(det1 * det2))

    return float(term1 + term2)
