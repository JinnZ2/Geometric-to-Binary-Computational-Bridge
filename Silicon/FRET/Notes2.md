The splat becomes a joint probability distribution over spatial position and discrete state, with covariance coupling between space and state.

Let me formalize this as an 8‑Field Gaussian Splat.

---

1. From 4D to 3+3 Dimensions

In the 4D case, we had:

· μ ∈ ℝ⁴ = (x, y, z, t)
· Σ ∈ ℝ⁴×⁴ with cross‑covariance between space and time.

Now, replace the scalar time dimension with a state vector of dimension d_s. Since you have 8 discrete states, one natural embedding is to use a 3‑dimensional binary space {0,1}³, or a continuous 3D latent space where each octant corresponds to a state.

Let’s define:

\mathbf{x} = (x, y, z, \mathbf{s}) \in \mathbb{R}^{3 + d_s}

where \mathbf{s} is a continuous state vector (e.g., d_s = 3 for three bits). The Gaussian density is:

G(\mathbf{x}) = \exp\left( -\frac{1}{2} (\mathbf{x} - \boldsymbol{\mu})^T \Sigma^{-1} (\mathbf{x} - \boldsymbol{\mu}) \right)

Now the covariance matrix Σ is (3+d_s) \times (3+d_s) and includes:

· Spatial covariance (3×3)
· State covariance (d_s \times d_s)
· Cross‑covariance between space and state (3 × d_s)

This cross‑covariance encodes how the spatial distribution changes depending on the state—exactly what you want for "manifesting across 8 fields."

---

2. Projecting to 8 Spatial Fields

To render or compute the field for a specific discrete state k \in \{0,\dots,7\}, you condition the Gaussian on that state's value in the continuous embedding.

2.1 State Embedding

Map each of the 8 symbolic states to a point in the latent space. A straightforward choice is the corners of a cube:

```python
state_centers = np.array([
    [-1, -1, -1],  # 000
    [-1, -1,  1],  # 001
    [-1,  1, -1],  # 010
    [-1,  1,  1],  # 011
    [ 1, -1, -1],  # 100
    [ 1, -1,  1],  # 101
    [ 1,  1, -1],  # 110
    [ 1,  1,  1]   # 111
])
```

Alternatively, you can use the tetrahedral basis vectors from the encoder, but a cube is simple and preserves orthogonality of bits.

2.2 Conditioning on State

Given a desired discrete state index k, we want the conditional spatial Gaussian:

\mu_{xyz|s=s_k} = \mu_{xyz} + \Sigma_{xyz,s} \Sigma_{ss}^{-1} (s_k - \mu_s)



\Sigma_{xyz|s=s_k} = \Sigma_{xyz} - \Sigma_{xyz,s} \Sigma_{ss}^{-1} \Sigma_{s,xyz}

This yields 8 different 3D Gaussians—one for each state—derived from the same parent 6D Gaussian.

2.3 Marginal Density per State

The total density contributed by the splat to state k is:

\rho_k(\mathbf{r}) = q \cdot G_{s=s_k}(\mathbf{r}) \cdot w_k

where w_k is the probability mass of the state (derived from integrating the state marginal). If you want the splat to represent a mixture of states, w_k can be computed from the Gaussian's state marginal evaluated at s_k (or you can explicitly set it).

Alternatively, you can sample the state dimension to produce discrete state assignments.

---

3. Implementation: 8‑Field Gaussian Splat Class

Here’s a concrete extension of the earlier Gaussian4DSource to an 8‑field version.

```python
# engine/gaussian_8field_source.py

import numpy as np
from scipy.stats import multivariate_normal

class Gaussian8FieldSource:
    """
    A Gaussian over (x,y,z, s1,s2,s3) where the state dimensions encode
    the 8 octahedral states. Can be conditioned on a specific state to
    produce a 3D spatial Gaussian for that field.
    """
    def __init__(self, mu=None, cov=None, charge=1.0, colors=None):
        """
        mu: length 6 array [x,y,z, s1,s2,s3]
        cov: 6x6 covariance matrix
        charge: total amplitude
        colors: optional dict mapping state index (0-7) to RGB color
        """
        self.mu = np.array(mu, dtype=np.float64) if mu is not None else np.zeros(6)
        self.cov = np.array(cov, dtype=np.float64) if cov is not None else np.eye(6)
        self.charge = float(charge)
        self.colors = colors if colors else self._default_colors()

        # Precompute mapping from state index to cube corner
        self.state_centers = self._build_state_centers()

    def _build_state_centers(self):
        """Map 0..7 to corners of cube [-1,1]^3."""
        centers = np.zeros((8, 3))
        for i in range(8):
            centers[i, 0] = -1.0 if (i & 1) == 0 else 1.0   # bit0 (LSB)
            centers[i, 1] = -1.0 if (i & 2) == 0 else 1.0   # bit1
            centers[i, 2] = -1.0 if (i & 4) == 0 else 1.0   # bit2
        return centers

    def _default_colors(self):
        # Use a colormap for the 8 states
        from matplotlib.cm import tab10
        return {i: tab10(i)[:3] for i in range(8)}

    def condition_on_state(self, state_idx):
        """
        Condition the 6D Gaussian on the discrete state index.
        Returns mean (3,) and covariance (3,3) for spatial distribution
        when the state is exactly at the cube corner for that index.
        """
        s_k = self.state_centers[state_idx]  # (3,)

        mu_xyz = self.mu[:3]
        mu_s = self.mu[3:6]

        cov_xyz = self.cov[:3, :3]
        cov_xs = self.cov[:3, 3:6]
        cov_sx = self.cov[3:6, :3]
        cov_ss = self.cov[3:6, 3:6]

        # Regularize
        cov_ss_reg = cov_ss + 1e-8 * np.eye(3)
        inv_cov_ss = np.linalg.inv(cov_ss_reg)

        ds = s_k - mu_s
        mu_cond = mu_xyz + cov_xs @ inv_cov_ss @ ds
        cov_cond = cov_xyz - cov_xs @ inv_cov_ss @ cov_sx

        # Ensure symmetry and positive definiteness
        cov_cond = (cov_cond + cov_cond.T) / 2.0
        eigvals = np.linalg.eigvalsh(cov_cond)
        if np.min(eigvals) < 1e-6:
            cov_cond += np.eye(3) * (1e-6 - np.min(eigvals))

        return mu_cond, cov_cond

    def evaluate_field_for_state(self, points, state_idx):
        """
        Evaluate spatial density contributed to a specific state field.
        points: (N,3) array
        returns density array of length N
        """
        mu_cond, cov_cond = self.condition_on_state(state_idx)
        mvn = multivariate_normal(mean=mu_cond, cov=cov_cond)
        # Weight by the marginal probability of that state (or simply the
        # Gaussian's value at the state center). Here we use the PDF at the corner.
        # Alternatively, you could return just the conditional density.
        state_weight = self._state_marginal_weight(state_idx)
        return self.charge * state_weight * mvn.pdf(points)

    def _state_marginal_weight(self, state_idx):
        """Compute the probability mass associated with this discrete state."""
        s_k = self.state_centers[state_idx]
        mu_s = self.mu[3:6]
        cov_ss = self.cov[3:6, 3:6]
        mvn = multivariate_normal(mean=mu_s, cov=cov_ss)
        # Use PDF at the corner (not normalized over discrete states; we could softmax later)
        return mvn.pdf(s_k)

    def evaluate_all_fields(self, points):
        """
        Return an (N, 8) array of densities for each state field.
        """
        densities = np.zeros((len(points), 8))
        for k in range(8):
            densities[:, k] = self.evaluate_field_for_state(points, k)
        return densities
```

---

4. Integration with Octahedral State Encoder

Now we can directly link the 8‑field Gaussian to the octahedral states. The OctahedralStateEncoder already defines canonical covariance patterns for each state. We can use that to initialize the 6D covariance.

For a given discrete state k with primary axis vector a₁, eigenvalue profile (λ₁,λ₂,λ₃), and velocity v, we can build the 6D covariance as:

\Sigma = \begin{pmatrix}
\Sigma_{xyz} & \Sigma_{xyz,s} \\
\Sigma_{s,xyz} & \Sigma_{ss}
\end{pmatrix}

Where:

· \Sigma_{xyz} is the 3×3 spatial covariance from the encoder.
· \Sigma_{ss} is a 3×3 state covariance that defines the "fuzziness" of the state (e.g., \sigma_s^2 I).
· \Sigma_{xyz,s} couples space and state such that moving in state space shifts the spatial mean in a direction aligned with the state's primary axis.

For example, we can set:

\Sigma_{xyz,s} = \alpha \cdot \mathbf{a}_1 \mathbf{e}_k^T

where \mathbf{e}_k is the unit vector in state space corresponding to the bit that flips from that state's canonical corner.

This gives a direct mapping: the splat's spatial location changes predictably as we interpolate between states.

---

5. Usage: Rendering the 8 Fields

With the 8‑field Gaussian, you can render a separate "channel" for each state, or combine them into a single visualization (e.g., color composite).

```python
# Example: create a splat that is a mixture of state 000 and state 110
mu = np.array([0, 0, 0,  -1, -1, -1])  # centered at state 000 corner
cov = np.eye(6) * 0.5
# Add cross-covariance so that moving toward state 110 shifts spatial position
cov[:3, 3] = [1.0, 0, 0]  # x shifts with s1
cov[3, :3] = [1.0, 0, 0]
cov[:3, 4] = [0, 1.0, 0]  # y shifts with s2
cov[4, :3] = [0, 1.0, 0]

splat = Gaussian8FieldSource(mu, cov, charge=1.0)

# Evaluate all 8 fields on a grid
points = ...  # Nx3
field_densities = splat.evaluate_all_fields(points)  # shape (N,8)
```

The output is an 8‑channel volumetric field, which can be visualized as 8 separate scalar fields or reduced via PCA.

---

6. Physical Interpretation & Applications

Concept 8‑Field Gaussian Splat
State as intrinsic property The Gaussian carries a distribution over the 8 octahedral states, not just a single label.
State‑dependent shape The spatial covariance can differ per state via conditioning.
Smooth transitions Interpolating in state space yields continuous spatial shifts (morphing between field patterns).
Magnetic coupling Transitions between states can be driven by external fields that apply a "force" in state space (gradient of energy with respect to s).
Error correction The covariance in state space can represent uncertainty in the symbolic state, enabling probabilistic decoding.

This framework turns the discrete symbolic sensor into a continuous, probabilistic field model—exactly the kind of "thermodynamic packet in phase space" you described earlier, but now with an internal discrete structure.



possibilities:

Let's fully specify both the Zeeman‑driven state dynamics and the manifold constraints that keep the Gaussian anchored to the 8 discrete states. This completes the bridge from continuous field theory to discrete symbolic computation.

---

1. The 6D Gaussian State

We have a Gaussian in \mathbb{R}^6:

\mathbf{x} = (x, y, z, s_1, s_2, s_3)



G(\mathbf{x}) = \exp\left(-\frac{1}{2}(\mathbf{x}-\boldsymbol{\mu})^T \Sigma^{-1} (\mathbf{x}-\boldsymbol{\mu})\right)

· \boldsymbol{\mu} \in \mathbb{R}^6 is the mean position in space and state.
· \Sigma \in \mathbb{R}^{6\times 6} is the full covariance.

The state part \mathbf{s} = (s_1,s_2,s_3) lives in a continuous cube [-1,1]^3, where the corners correspond to the 8 octahedral symbolic states (000 to 111). Our goal is to evolve \boldsymbol{\mu} and \Sigma under:

1. External magnetic field coupling (Zeeman energy) that drives transitions between corners.
2. Manifold constraints that keep \mathbf{s} near the corners.

---

2. Zeeman Coupling Dynamics

From the sensor spec:

E_{\text{mag}} = - \mathbf{M} : \mathbf{B}_{\text{ext}}

where \mathbf{M} is a magnetic moment tensor that depends on the octahedral state, and \mathbf{B}_{\text{ext}} is an external magnetic field vector (or tensor). The double contraction : implies a scalar energy.

2.1 Defining the Magnetic Moment Tensor

For each of the 8 states, we assign a canonical moment tensor derived from the tetrahedral geometry. A simple choice is to use the primary axis of the state (from the OctahedralStateEncoder) to define a vector magnetic moment:

\mathbf{m}(\mathbf{s}) = m_0 \cdot \text{soft\_direction}(\mathbf{s})

where \text{soft\_direction}(\mathbf{s}) interpolates between the tetrahedral axes based on the state coordinates.

Alternatively, we can define a state‑dependent tensor:

M_{ij}(\mathbf{s}) = \sum_{k=0}^{7} w_k(\mathbf{s}) \, M^{(k)}_{ij}

with w_k(\mathbf{s}) being a softmax over the distance to each corner, and M^{(k)} a precomputed tensor for state k. For simplicity, we'll use a vector moment \mathbf{m}(\mathbf{s}) and a scalar Zeeman energy:

E_{\text{mag}}(\mathbf{s}) = - \mathbf{m}(\mathbf{s}) \cdot \mathbf{B}_{\text{ext}}

2.2 Force on the State Mean

The force in state space is the negative gradient of the energy:

\mathbf{F}_s = -\nabla_{\mathbf{s}} E_{\text{mag}} = \nabla_{\mathbf{s}} (\mathbf{m}(\mathbf{s}) \cdot \mathbf{B}_{\text{ext}})

This force drives \boldsymbol{\mu}_s (the state part of the mean) toward alignments that lower the energy.

2.3 Evolution Equations

We can update the mean using overdamped Langevin dynamics:

\frac{d\boldsymbol{\mu}_s}{dt} = \gamma \mathbf{F}_s + \sqrt{2\gamma k_B T} \, \boldsymbol{\eta}(t)

where \gamma is a mobility, T is an effective temperature (allowing stochastic transitions), and \boldsymbol{\eta} is white noise.

For the covariance, we may also include diffusion or keep it fixed, but a more complete treatment would use a Fokker‑Planck or ensemble Kalman approach.

2.4 Implementation Sketch

```python
# engine/zeeman_dynamics.py

import numpy as np
from engine.octahedral_state_encoder import OctahedralStateEncoder

class ZeemanDynamics:
    def __init__(self, encoder, moment_magnitude=1.0, mobility=1.0, temperature=0.01):
        self.encoder = encoder
        self.m0 = moment_magnitude
        self.gamma = mobility
        self.kBT = temperature
        # Precompute moment vectors for each corner state
        self.state_moments = self._compute_state_moments()

    def _compute_state_moments(self):
        """Map each of the 8 states to a magnetic moment vector."""
        moments = {}
        for state in range(8):
            profile = self.encoder.STATE_PROFILES[state]
            if profile["primary"] is not None:
                # Use the primary tetrahedral axis as the moment direction
                axis = self.encoder.TETRA_VECTORS[profile["primary"]]
                moments[state] = self.m0 * axis
            else:
                # State 111: isotropic, zero net moment
                moments[state] = np.zeros(3)
        return moments

    def compute_moment(self, s):
        """
        Interpolate magnetic moment based on continuous state vector s.
        Uses softmax weighting to blend corner moments.
        """
        # Distance to each corner
        centers = self.encoder.state_centers  # (8,3)
        diffs = centers - s[np.newaxis, :]    # (8,3)
        dists = np.linalg.norm(diffs, axis=1)
        # Softmax weights
        beta = 10.0  # sharpness
        weights = np.exp(-beta * dists)
        weights /= np.sum(weights)
        # Blend moments
        moment = np.zeros(3)
        for state in range(8):
            moment += weights[state] * self.state_moments[state]
        return moment

    def force_on_state(self, s, B_ext):
        """
        Compute force F_s = ∇_s (m(s)·B_ext).
        Uses finite differences for simplicity (or analytical if m(s) is simple).
        """
        eps = 1e-5
        force = np.zeros(3)
        for i in range(3):
            s_plus = s.copy()
            s_plus[i] += eps
            s_minus = s.copy()
            s_minus[i] -= eps
            E_plus = -np.dot(self.compute_moment(s_plus), B_ext)
            E_minus = -np.dot(self.compute_moment(s_minus), B_ext)
            force[i] = -(E_plus - E_minus) / (2*eps)  # F = -∇E
        return force

    def step(self, gaussian, B_ext, dt):
        """
        Update the state part of the Gaussian mean under Zeeman force.
        gaussian: Gaussian8FieldSource instance
        """
        mu_s = gaussian.mu[3:6]
        F_s = self.force_on_state(mu_s, B_ext)
        # Overdamped Langevin step
        noise = np.random.randn(3) * np.sqrt(2 * self.gamma * self.kBT * dt)
        dmu_s = self.gamma * F_s * dt + noise
        gaussian.mu[3:6] += dmu_s
        # Optionally add diffusion to covariance (not implemented here)
```

---

3. Manifold Constraints: Keeping States Near Corners

The continuous state vector should ideally reside near the corners of the cube to represent discrete symbolic states. We can enforce this via:

3.1 Hard Projection (Snap to Nearest Corner)

After each dynamics step, we simply project \boldsymbol{\mu}_s onto the nearest corner.

```python
def project_to_nearest_corner(mu_s):
    """Snap state vector to closest cube corner."""
    # corners are at [-1,1] for each dimension
    snapped = np.sign(mu_s)
    # If exactly zero, choose +1 (arbitrary)
    snapped[snapped == 0] = 1
    return snapped
```

This yields purely discrete states but loses the continuous interpolation needed for smooth forces.

3.2 Soft Constraint via Potential Well

A better approach is to add a manifold potential that creates energy minima at the 8 corners:

U_{\text{manifold}}(\mathbf{s}) = \lambda \sum_{k=0}^{7} \prod_{i=1}^{3} (1 - s_i^2)^2 \cdot \text{(some repulsion from other corners)}?

A simple quartic well per corner is:

U(\mathbf{s}) = \lambda \min_{k} \left( \|\mathbf{s} - \mathbf{c}_k\|^2 \right)

but this is not smooth. Instead, use a sum of Gaussians centered at corners (attractive) plus a uniform background repulsion.

Alternatively, use a periodic potential in each dimension with minima at ±1, e.g.:

U_{\text{manifold}}(s_1,s_2,s_3) = \kappa \sum_{i=1}^{3} (s_i^2 - 1)^2

This creates 8 equal minima at the corners. The force from this potential is:

\mathbf{F}_{\text{manifold}} = -\nabla U = -4\kappa \sum_{i=1}^{3} (s_i^2 - 1) s_i \, \mathbf{e}_i

This force pulls the state back toward the nearest corner whenever it drifts.

3.3 Combined Dynamics

Total force on state mean:

\mathbf{F}_{\text{total}} = \mathbf{F}_{\text{Zeeman}} + \mathbf{F}_{\text{manifold}}

Update step with noise as before.

3.4 Implementation of Soft Manifold Constraint

```python
class ManifoldConstraint:
    def __init__(self, kappa=10.0):
        self.kappa = kappa

    def potential(self, s):
        return self.kappa * np.sum((s**2 - 1)**2)

    def force(self, s):
        # F = -∇U
        return -4 * self.kappa * (s**2 - 1) * s
```

Then in the dynamics step:

```python
F_manifold = manifold_constraint.force(mu_s)
F_total = F_zeeman + F_manifold
```

---

4. Coupling Space and State via Covariance

The cross‑covariance \Sigma_{xyz,s} ensures that when the state changes, the spatial position shifts accordingly. This is already built into the Gaussian8FieldSource. During dynamics, we may also update the covariance to reflect changes in uncertainty (e.g., heating near transitions). For now, we keep Σ constant, but a full treatment would evolve it using a Riccati equation or ensemble methods.

---

5. Integration into the Solver Pipeline

The full update loop for a single timestep might look like:

```python
# Pseudocode for one simulation step
for gaussian in splats:
    # 1. Compute local external field B_ext (could be from other splats, environment)
    B_ext = compute_B_field(gaussian, all_splats)

    # 2. Compute Zeeman force
    F_zeeman = zeeman_dyn.force_on_state(gaussian.mu[3:6], B_ext)

    # 3. Compute manifold force
    F_manifold = manifold.force(gaussian.mu[3:6])

    # 4. Update state mean
    noise = np.random.randn(3) * np.sqrt(2*gamma*kBT*dt)
    gaussian.mu[3:6] += gamma * (F_zeeman + F_manifold) * dt + noise

    # 5. Update spatial mean according to cross-covariance (if desired)
    #    μ_xyz += Σ_xyz,s * Σ_ss^{-1} * dμ_s   (deterministic part)
    #    This keeps the splat's position consistent with its state change.

    # 6. Optionally, project state back to nearest corner if too far
    if np.linalg.norm(gaussian.mu[3:6] - project_to_nearest_corner(gaussian.mu[3:6])) > 0.5:
        gaussian.mu[3:6] = project_to_nearest_corner(gaussian.mu[3:6])
```

---

6. Rendering the 8 Fields Over Time

As the state mean evolves, the 8 fields (one per symbolic state) change because conditioning on a state index uses the current \boldsymbol{\mu} and \Sigma. You can render an animation showing:

· A color composite of all 8 fields, where each channel's opacity is weighted by the state marginal probability.
· A trajectory of the most likely state over time.
· Field intensity that shifts in space as the splat transitions between states.

---

7. Emergent Behaviors

With these dynamics, you can observe:

· State flips driven by external B fields (simulating magnetic writing).
· Thermal hopping between minima (bit flips at finite temperature).
· Collective resonance when multiple splats couple via their fields (e.g., state 110 "resonance coupling" could synchronize transitions).
· Error correction if you implement a feedback loop that nudges states back toward valid corners.

This is a hybrid symbolic‑continuous computing substrate where the 8 fields are the computational basis, and the 6D Gaussian splats are the physical carriers.

"""
8-Field Gaussian Splat with Zeeman Dynamics and Manifold Constraints
====================================================================
Simulates hybrid continuous/discrete objects whose internal state (3-bit)
evolves under magnetic coupling and remains anchored to cube corners.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.stats import multivariate_normal
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 (needed for 3D projection)

# ---------------------------
# 1. Octahedral State Encoder
# ---------------------------
class OctahedralStateEncoder:
    """Maps 8 symbolic states to tetrahedral axes and eigenvalues."""
    
    # Four vertices of a regular tetrahedron (normalized)
    TETRA_VECTORS = np.array([
        [ 1,  1,  1],
        [ 1, -1, -1],
        [-1,  1, -1],
        [-1, -1,  1]
    ], dtype=float) / np.sqrt(3)

    # State profiles: primary axis index and eigenvalue distribution
    STATE_PROFILES = {
        0b000: {"primary": 0, "secondary": 1, "eig": (0.6, 0.2, 0.2)},
        0b001: {"primary": 1, "secondary": 2, "eig": (0.2, 0.6, 0.2)},
        0b010: {"primary": 0, "secondary": 2, "eig": (0.5, 0.3, 0.2)},
        0b011: {"primary": 1, "secondary": 3, "eig": (0.3, 0.5, 0.2)},
        0b100: {"primary": 2, "secondary": 0, "eig": (0.4, 0.2, 0.4)},
        0b101: {"primary": 2, "secondary": 3, "eig": (0.2, 0.4, 0.4)},
        0b110: {"primary": 3, "secondary": 0, "eig": (0.4, 0.4, 0.2)},
        0b111: {"primary": None, "secondary": None, "eig": (1/3, 1/3, 1/3)},
    }

    def __init__(self):
        # Cube corners for state embedding
        self.state_centers = self._build_state_centers()

    def _build_state_centers(self):
        centers = np.zeros((8, 3))
        for i in range(8):
            centers[i, 0] = -1.0 if (i & 1) == 0 else 1.0
            centers[i, 1] = -1.0 if (i & 2) == 0 else 1.0
            centers[i, 2] = -1.0 if (i & 4) == 0 else 1.0
        return centers

    def nearest_state(self, s):
        """Return the integer state index closest to continuous vector s."""
        distances = np.linalg.norm(self.state_centers - s, axis=1)
        return np.argmin(distances)


# ---------------------------
# 2. 8-Field Gaussian Source
# ---------------------------
class Gaussian8FieldSource:
    """
    Gaussian over (x,y,z, s1,s2,s3) with 6D mean and covariance.
    """
    def __init__(self, mu, cov, charge=1.0):
        self.mu = np.asarray(mu, dtype=float)
        self.cov = np.asarray(cov, dtype=float)
        self.charge = charge
        self.encoder = OctahedralStateEncoder()

    def condition_on_state(self, state_idx):
        """Return spatial mean & cov conditioned on discrete state index."""
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

    def state_probabilities(self):
        """Return probability mass for each of the 8 discrete states."""
        mu_s = self.mu[3:6]
        cov_ss = self.cov[3:6, 3:6]
        mvn = multivariate_normal(mean=mu_s, cov=cov_ss)
        probs = np.array([mvn.pdf(self.encoder.state_centers[i]) for i in range(8)])
        probs /= probs.sum()
        return probs

    def most_likely_state(self):
        return np.argmax(self.state_probabilities())


# ---------------------------
# 3. Zeeman Dynamics
# ---------------------------
class ZeemanDynamics:
    """Magnetic coupling energy: E = -m(s)·B_ext."""
    def __init__(self, encoder, moment_magnitude=1.0, mobility=1.0, temperature=0.05):
        self.encoder = encoder
        self.m0 = moment_magnitude
        self.gamma = mobility
        self.kBT = temperature
        # Precompute moment vectors for each corner state
        self.state_moments = {}
        for state in range(8):
            prof = encoder.STATE_PROFILES[state]
            if prof["primary"] is not None:
                axis = encoder.TETRA_VECTORS[prof["primary"]]
                self.state_moments[state] = self.m0 * axis
            else:
                self.state_moments[state] = np.zeros(3)

    def compute_moment(self, s, beta=10.0):
        """Soft moment interpolation based on distance to corners."""
        centers = self.encoder.state_centers
        dists = np.linalg.norm(centers - s, axis=1)
        weights = np.exp(-beta * dists)
        weights /= weights.sum()
        moment = np.zeros(3)
        for state in range(8):
            moment += weights[state] * self.state_moments[state]
        return moment

    def force(self, s, B_ext):
        """F = ∇_s (m·B) using finite differences."""
        eps = 1e-5
        force = np.zeros(3)
        for i in range(3):
            s_plus = s.copy()
            s_plus[i] += eps
            s_minus = s.copy()
            s_minus[i] -= eps
            E_plus = -np.dot(self.compute_moment(s_plus), B_ext)
            E_minus = -np.dot(self.compute_moment(s_minus), B_ext)
            force[i] = -(E_plus - E_minus) / (2*eps)  # -∇E
        return force


# ---------------------------
# 4. Manifold Constraint
# ---------------------------
class ManifoldConstraint:
    """Potential U(s) = κ Σ (s_i^2 - 1)^2 with minima at cube corners."""
    def __init__(self, kappa=5.0):
        self.kappa = kappa

    def force(self, s):
        return -4 * self.kappa * (s**2 - 1) * s


# ---------------------------
# 5. Helper: Create Splats
# ---------------------------
def create_initial_splat(x, y, z, state_idx, spatial_scale=0.3, state_scale=0.2, cross_coupling=0.1):
    """
    Build a 6D Gaussian near a specific cube corner with plausible cross-covariance.
    """
    encoder = OctahedralStateEncoder()
    s_center = encoder.state_centers[state_idx]
    prof = encoder.STATE_PROFILES[state_idx]

    # Spatial covariance (anisotropic, aligned with tetrahedral axis if available)
    if prof["primary"] is not None:
        a1 = encoder.TETRA_VECTORS[prof["primary"]]
        a2 = encoder.TETRA_VECTORS[prof["secondary"]]
        a2 = a2 - np.dot(a2, a1) * a1
        a2 /= np.linalg.norm(a2)
        a3 = np.cross(a1, a2)
        basis = np.column_stack([a1, a2, a3])
        eig = np.array(prof["eig"]) * (spatial_scale**2)
        cov_xyz = basis @ np.diag(eig) @ basis.T
    else:
        cov_xyz = np.eye(3) * (spatial_scale**2 / 3)

    cov_ss = np.eye(3) * (state_scale**2)

    # Cross-covariance: moving state toward other corners shifts position along primary axis
    cov_xs = np.zeros((3,3))
    if prof["primary"] is not None:
        primary_axis = encoder.TETRA_VECTORS[prof["primary"]]
        # For each state dimension, couple to primary axis
        cov_xs[:, 0] = primary_axis * cross_coupling
        cov_xs[:, 1] = primary_axis * cross_coupling * 0.5
        cov_xs[:, 2] = primary_axis * cross_coupling * 0.3

    # Assemble 6x6 covariance
    cov = np.block([
        [cov_xyz,      cov_xs],
        [cov_xs.T,     cov_ss]
    ])

    mu = np.concatenate([[x, y, z], s_center])
    return Gaussian8FieldSource(mu, cov, charge=1.0)


# ---------------------------
# 6. Simulation and Animation
# ---------------------------
def run_simulation():
    # Setup
    encoder = OctahedralStateEncoder()
    zeeman = ZeemanDynamics(encoder, moment_magnitude=1.0, mobility=0.8, temperature=0.03)
    manifold = ManifoldConstraint(kappa=6.0)

    # Create three splats with different initial states
    splats = [
        create_initial_splat(x=-2.0, y=0.0, z=0.0, state_idx=0b000),  # 000
        create_initial_splat(x= 0.0, y=1.0, z=0.0, state_idx=0b010),  # 010
        create_initial_splat(x= 2.0, y=-1.0, z=0.0, state_idx=0b110), # 110
    ]

    dt = 0.05
    time_steps = 300

    # Store history for plotting
    history = {
        'time': [],
        'states': [[] for _ in splats],       # discrete state index over time
        'positions': [[] for _ in splats],     # spatial mean (x,y)
        'state_vectors': [[] for _ in splats], # continuous s vector
    }

    # External B-field: rotating in xy plane + static z component
    def B_ext(t):
        omega = 0.5
        return np.array([np.cos(omega * t), np.sin(omega * t), 0.2])

    # Evolve
    for step in range(time_steps):
        t = step * dt
        B = B_ext(t)
        history['time'].append(t)

        for i, g in enumerate(splats):
            mu_s = g.mu[3:6].copy()
            # Forces
            F_z = zeeman.force(mu_s, B)
            F_m = manifold.force(mu_s)
            F_total = F_z + F_m

            # Langevin step on state mean
            noise = np.random.randn(3) * np.sqrt(2 * zeeman.gamma * zeeman.kBT * dt)
            dmu_s = zeeman.gamma * F_total * dt + noise
            g.mu[3:6] += dmu_s

            # Update spatial mean consistently using cross-covariance
            cov_xs = g.cov[:3, 3:6]
            cov_ss = g.cov[3:6, 3:6]
            inv_cov_ss = np.linalg.inv(cov_ss + 1e-8 * np.eye(3))
            g.mu[:3] += cov_xs @ inv_cov_ss @ dmu_s

            # Record
            history['states'][i].append(g.most_likely_state())
            history['positions'][i].append(g.mu[:2].copy())
            history['state_vectors'][i].append(mu_s.copy())

    # Visualization: two subplots
    fig = plt.figure(figsize=(12,5))
    ax1 = fig.add_subplot(121)  # 2D spatial trajectory
    ax2 = fig.add_subplot(122, projection='3d')  # 3D state cube

    # Precompute cube edges for plotting
    corners = encoder.state_centers
    edges = [(0,1), (0,2), (0,4), (1,3), (1,5), (2,3), (2,6), (3,7), (4,5), (4,6), (5,7), (6,7)]

    # Colors for each splat
    colors = ['red', 'green', 'blue']

    def animate(frame):
        ax1.clear()
        ax2.clear()

        # Plot cube wireframe
        for e in edges:
            ax2.plot3D(*zip(corners[e[0]], corners[e[1]]), color='gray', alpha=0.3)
        ax2.set_xlim(-1.5, 1.5)
        ax2.set_ylim(-1.5, 1.5)
        ax2.set_zlim(-1.5, 1.5)
        ax2.set_xlabel('s1')
        ax2.set_ylabel('s2')
        ax2.set_zlabel('s3')
        ax2.set_title('State Space (Cube Corners = 8 States)')

        # Plot spatial domain
        ax1.set_xlim(-4, 4)
        ax1.set_ylim(-3, 3)
        ax1.set_xlabel('x')
        ax1.set_ylabel('y')
        ax1.set_title('Spatial Mean Trajectories')
        ax1.grid(True)

        # Draw each splat's history up to current frame
        for i, g in enumerate(splats):
            pos = np.array(history['positions'][i][:frame+1])
            state_vec = np.array(history['state_vectors'][i][:frame+1])

            # Spatial plot
            if len(pos) > 0:
                ax1.plot(pos[:,0], pos[:,1], color=colors[i], alpha=0.6, linewidth=1)
                ax1.scatter(pos[-1,0], pos[-1,1], color=colors[i], s=80,
                            marker='o', edgecolor='black', linewidth=1.5)
                # Annotate with current state
                state_idx = history['states'][i][frame]
                ax1.annotate(f"{state_idx:03b}", (pos[-1,0], pos[-1,1]),
                             textcoords="offset points", xytext=(5,5), fontsize=9)

            # State space plot
            if len(state_vec) > 0:
                ax2.plot(state_vec[:,0], state_vec[:,1], state_vec[:,2],
                         color=colors[i], alpha=0.6, linewidth=1)
                ax2.scatter(state_vec[-1,0], state_vec[-1,1], state_vec[-1,2],
                            color=colors[i], s=60, marker='o', edgecolor='black')

        ax1.legend([f"Splat {i}" for i in range(len(splats))], loc='upper right')
        fig.suptitle(f'Time: {history["time"][frame]:.2f}  |  B-field: ({B_ext(history["time"][frame])[0]:.2f}, {B_ext(history["time"][frame])[1]:.2f}, {B_ext(history["time"][frame])[2]:.2f})')
        return fig,

    ani = FuncAnimation(fig, animate, frames=time_steps, interval=50, blit=False)
    plt.tight_layout()
    plt.show()
    # To save: ani.save('8field_splats.mp4', writer='ffmpeg')


if __name__ == "__main__":
    run_simulation()
