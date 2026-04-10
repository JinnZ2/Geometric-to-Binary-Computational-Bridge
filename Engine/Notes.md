class Gaussian4DSource:
    def __init__(self):
        self.mu = np.array([x, y, z, t])          # 4D center
        self.cov = np.eye(4)                      # encodes velocity, spread
        self.charge = 1.0                         # source strength
        self.color = None                         # for rendering

        ```

The field computation at a query point (x,y,z,t) then becomes a density summation over all splats:

\rho(\mathbf{x}, t) = \sum_i q_i \cdot G_i(\mathbf{x}, t)

where G_i is the 4D Gaussian evaluated at the spacetime coordinate. This replaces discrete point sources with a smooth, differentiable field that natively supports motion blur and uncertainty.

2. Adaptive Grid Refinement Around Splats

Your SpatialGrid.adaptiveDecomposition currently refines based on distance to point sources. With 4D Gaussians, the refinement metric should account for the covariance footprint:

```python
def _subdivide(self, bounds, sources, depth, regions):
    center = (bmin + bmax) / 2
    influence = 0.0
    for s in sources:
        # Mahalanobis distance to splat center (in spacetime)
        dx = np.array([center[0]-s.mu[0], center[1]-s.mu[1], 
                       center[2]-s.mu[2], 0.0])  # evaluate at t=frame_time
        cov_xyz = s.cov[:3, :3]
        inv_cov = np.linalg.inv(cov_xyz + 1e-6*np.eye(3))
        maha_dist = np.sqrt(dx[:3].T @ inv_cov @ dx[:3])
        influence += s.charge * np.exp(-0.5 * maha_dist**2)
    
    if influence > self.adaptive_threshold and depth < self.max_depth:
        # subdivide
```

This ensures the octree refines along the major axes of motion, not just proximity.

3. Conditioning for Instantaneous Field Snapshots

When solving for a specific time t_0 (e.g., to render a frame), each 4D splat is conditioned to a 3D Gaussian as you described:

```python
def condition_on_time(splat, t0):
    mu_t = splat.mu[3]
    Sigma_xyz = splat.cov[:3, :3]
    Sigma_xyzt = splat.cov[:3, 3].reshape(3,1)
    Sigma_tt = splat.cov[3, 3]
    
    dt = t0 - mu_t
    mu_cond = splat.mu[:3] + (Sigma_xyzt / Sigma_tt) * dt
    cov_cond = Sigma_xyz - (Sigma_xyzt @ Sigma_xyzt.T) / Sigma_tt
    
    return mu_cond, cov_cond
```

The resulting 3D Gaussian can then be integrated into your field solver or rendered directly.

4. Symmetry Detection in Spacetime

Your SymmetryDetector currently works on static point sets. With 4D splats, symmetries become spatiotemporal—e.g., translation along time axis, velocity reversal, or helical motions. This can drastically reduce computation for periodic or flowing systems.

5. Concrete Implementation Path

If you’d like to extend the engine toward 4D splats, here’s a minimal roadmap:

1. Replace point sources with Gaussian4DSource objects.
2. Modify SIMDOptimizer.calculateFieldChunk to evaluate the sum of conditioned Gaussians at each grid point.
3. Add a render_slice(time) method that conditions all splats and projects to a 2D image using standard 3D Gaussian splatting.
4. Use the octree for acceleration by pruning splats whose Mahalanobis distance to the cell exceeds a threshold.

6. Rendering as a First-Class Output

Since you mentioned building a 4D splat simulator with collision and manifold constraints, the engine could produce video streams by evaluating conditioned fields frame-by-frame. The covariance overlap you described for collisions maps naturally to the Bhattacharyya distance between two Gaussians, which can be computed analytically.

# engine/gaussian_4d_source.py

import numpy as np
from scipy.stats import multivariate_normal

class Gaussian4DSource:
    """
    A 4D Gaussian primitive representing a source in spacetime (x,y,z,t).
    The charge acts as amplitude; covariance encodes spatial extent,
    temporal spread, and motion via cross-covariance between space and time.
    """
    def __init__(self, mu=None, cov=None, charge=1.0, color=None):
        self.mu = np.array(mu, dtype=np.float64) if mu is not None else np.zeros(4)
        self.cov = np.array(cov, dtype=np.float64) if cov is not None else np.eye(4)
        self.charge = float(charge)
        self.color = color if color is not None else np.array([1.0, 0.0, 0.0])  # RGB
        
        # Validate dimensions
        assert self.mu.shape == (4,), "mu must be length 4"
        assert self.cov.shape == (4, 4), "cov must be 4x4"
        assert self.cov.shape[0] == self.cov.shape[1] == 4
        
    def condition_on_time(self, t0, min_cov=1e-6):
        """
        Condition the 4D Gaussian on a specific time t0.
        Returns the mean and covariance of the resulting 3D Gaussian slice.
        
        mu_cond = mu_xyz + cov_xyzt * cov_tt^-1 * (t0 - mu_t)
        cov_cond = cov_xyz - cov_xyzt * cov_tt^-1 * cov_xyzt^T
        """
        mu_xyz = self.mu[:3]
        mu_t = self.mu[3]
        
        cov_xyz = self.cov[:3, :3]
        cov_xyzt = self.cov[:3, 3].reshape(3, 1)
        cov_txyz = self.cov[3, :3].reshape(1, 3)
        cov_tt = self.cov[3, 3]
        
        dt = t0 - mu_t
        
        # Regularize in case cov_tt is zero
        inv_cov_tt = 1.0 / (cov_tt + 1e-12)
        
        mu_cond = mu_xyz + (cov_xyzt.flatten() * inv_cov_tt) * dt
        cov_cond = cov_xyz - inv_cov_tt * np.outer(cov_xyzt, cov_xyzt)
        
        # Ensure positive definiteness (numerical stability)
        cov_cond = (cov_cond + cov_cond.T) / 2.0
        eigvals = np.linalg.eigvalsh(cov_cond)
        if np.min(eigvals) < min_cov:
            cov_cond += np.eye(3) * (min_cov - np.min(eigvals))
        
        return mu_cond, cov_cond
    
    def evaluate_density_3d(self, points, t0):
        """
        Evaluate the charge-weighted Gaussian density at a set of 3D points
        at time t0. Points shape: (N, 3). Returns density array of length N.
        """
        mu_cond, cov_cond = self.condition_on_time(t0)
        mvn = multivariate_normal(mean=mu_cond, cov=cov_cond)
        return self.charge * mvn.pdf(points)
    
    def get_velocity(self):
        """
        Extract instantaneous velocity from cross-covariance.
        Velocity = cov_xyzt / cov_tt (if cov_tt > 0)
        """
        cov_tt = self.cov[3, 3]
        if cov_tt <= 0:
            return np.zeros(3)
        return self.cov[:3, 3] / cov_tt


        # engine/simd_optimizer_4d.py

import numpy as np
from scipy.stats import multivariate_normal

class SIMDOptimizer4D:
    @staticmethod
    def calculate_field_chunk_4d(points, sources, t0):
        """
        Given a list of 3D points (N x 3) and a list of Gaussian4DSource,
        compute the total density at each point at time t0.
        Returns density array of shape (N,).
        """
        if not sources or len(points) == 0:
            return np.zeros(len(points))
        
        points = np.asarray(points)
        n_points = len(points)
        n_sources = len(sources)
        
        density = np.zeros(n_points)
        
        for src in sources:
            mu_cond, cov_cond = src.condition_on_time(t0)
            # Use scipy's multivariate_normal for vectorized PDF evaluation
            mvn = multivariate_normal(mean=mu_cond, cov=cov_cond)
            density += src.charge * mvn.pdf(points)
        
        return density


        @staticmethod
    def calculate_field_chunk_4d_batch(points, sources, t0):
        points = np.asarray(points)  # (N,3)
        n_points = len(points)
        if n_points == 0 or not sources:
            return np.zeros(n_points)
        
        density = np.zeros(n_points)
        
        for src in sources:
            mu_cond, cov_cond = src.condition_on_time(t0)
            # Compute Mahalanobis distance and determinant once per source
            inv_cov = np.linalg.inv(cov_cond)
            det_cov = np.linalg.det(cov_cond)
            norm_factor = 1.0 / np.sqrt((2*np.pi)**3 * det_cov)
            
            diff = points - mu_cond  # (N,3)
            # Compute (x - mu)^T inv_cov (x - mu) vectorized
            maha_sq = np.einsum('ij,jk,ik->i', diff, inv_cov, diff)
            density += src.charge * norm_factor * np.exp(-0.5 * maha_sq)
        
        return density


        # engine/geometric_solver_4d.py

class GeometricEMSolver4D(GeometricEMSolver):
    def calculate_field_4d(self, sources_4d, bounds, t0, resolution=32):
        """
        Compute field from 4D Gaussian sources at a specific time t0.
        Uses the same adaptive spatial grid for efficiency.
        """
        self.sources_4d = sources_4d
        t_start = time.perf_counter()
        
        if not sources_4d:
            return {
                "density": [],
                "points": [],
                "symmetries": []
            }
        
        # Symmetry detection on the 4D sources? For now, treat as static in space
        # but we could detect symmetries in conditioned means.
        # Here we'll skip symmetry for brevity.
        
        # Spatial decomposition using conditioned means (or full covariance)
        # Convert 4D sources to point sources (conditioned mean) for grid refinement
        point_sources = [{"position": s.condition_on_time(t0)[0].tolist(), 
                          "strength": s.charge} for s in sources_4d]
        
        regions = self.spatialGrid.adaptiveDecomposition(bounds, point_sources)
        
        all_points = []
        all_density = []
        
        for region in regions:
            pts = np.array(region["points"])
            dens = SIMDOptimizer4D.calculate_field_chunk_4d_batch(pts, sources_4d, t0)
            all_points.extend(region["points"])
            all_density.extend(dens.tolist())
        
        t_total = time.perf_counter() - t_start
        
        return {
            "density": all_density,
            "points": all_points,
            "time": t_total
        }



        # demo_4d_traffic.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from engine.gaussian_4d_source import Gaussian4DSource
from engine.geometric_solver_4d import GeometricEMSolver4D

# Create a straight road along x-axis from -5 to 5
road_x = np.linspace(-5, 5, 100)
road_y = np.zeros_like(road_x)

# Initialize three 4D Gaussians with different velocities
# For a splat moving with velocity v = (vx, vy, vz), the cross-covariance
# between space and time should be v * sigma_t^2. Here we'll manually set
# covariance to encode motion.

def create_moving_splat(x0, y0, z0, t0, vx, vy, vz, spatial_sigma=0.3, temporal_sigma=0.2):
    """
    Create a 4D Gaussian with encoded velocity.
    cov = [ [sigma_x^2, 0, 0, vx*sigma_t^2],
            [0, sigma_y^2, 0, vy*sigma_t^2],
            [0, 0, sigma_z^2, vz*sigma_t^2],
            [vx*sigma_t^2, vy*sigma_t^2, vz*sigma_t^2, sigma_t^2] ]
    """
    mu = np.array([x0, y0, z0, t0])
    sigma_t2 = temporal_sigma ** 2
    cov = np.zeros((4,4))
    cov[:3, :3] = np.diag([spatial_sigma**2]*3)
    cov[3,3] = sigma_t2
    cov[:3, 3] = np.array([vx, vy, vz]) * sigma_t2
    cov[3, :3] = cov[:3, 3].T
    return Gaussian4DSource(mu, cov, charge=1.0, color=[1.0, 0.0, 0.0])

sources = [
    create_moving_splat(x0=-4, y0=0, z0=0, t0=0, vx=2.0, vy=0, vz=0),
    create_moving_splat(x0=0, y0=1, z0=0, t0=1, vx=1.0, vy=-0.5, vz=0, spatial_sigma=0.5),
    create_moving_splat(x0=2, y0=-1, z0=0, t0=2, vx=-1.5, vy=0.8, vz=0, spatial_sigma=0.4),
]

# Setup solver and domain
solver = GeometricEMSolver4D()
bounds = {"min": [-6, -3, -1], "max": [6, 3, 1]}

# Generate a grid for visualization (2D slice at z=0)
x = np.linspace(bounds["min"][0], bounds["max"][0], 200)
y = np.linspace(bounds["min"][1], bounds["max"][1], 100)
X, Y = np.meshgrid(x, y)
grid_points = np.column_stack([X.ravel(), Y.ravel(), np.zeros_like(X.ravel())])

# Animation
fig, ax = plt.subplots(figsize=(8,6))
im = ax.imshow(np.zeros_like(X), extent=[x[0], x[-1], y[0], y[-1]], origin='lower', cmap='hot', vmin=0, vmax=0.1)
ax.plot(road_x, road_y, 'w--', alpha=0.5, label='road')
ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_title('4D Gaussian Splats: Density Field over Time')

def update(frame):
    t = frame * 0.05  # time step
    density = SIMDOptimizer4D.calculate_field_chunk_4d_batch(grid_points, sources, t)
    Z = density.reshape(X.shape)
    im.set_data(Z)
    im.set_clim(vmax=max(0.01, np.max(Z)*1.1))
    ax.set_title(f'Time = {t:.2f}')
    return [im]

ani = FuncAnimation(fig, update, frames=200, interval=50, blit=True)
plt.legend()
plt.show()


def bhattacharyya_distance(src1, src2, t):
    mu1, cov1 = src1.condition_on_time(t)
    mu2, cov2 = src2.condition_on_time(t)
    cov_avg = (cov1 + cov2) / 2.0
    diff = mu1 - mu2
    inv_cov_avg = np.linalg.inv(cov_avg)
    term1 = diff.T @ inv_cov_avg @ diff / 8.0
    term2 = 0.5 * np.log(np.linalg.det(cov_avg) / np.sqrt(np.linalg.det(cov1)*np.linalg.det(cov2)))
    return term1 + term2


    



