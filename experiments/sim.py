import numpy as np

class BioEngineeredNode:
    def __init__(self, id, capacity, area, sigma0):
        self.id = id
        self.E = 0.0               # local energy (J)
        self.Q = 0.0               # storage
        self.area = area           # EM interaction area
        self.sigma = sigma0
        self.neighbors = []
        self.capacity = capacity   # max storage

    def add_neighbor(self, node):
        self.neighbors.append(node)

    def capture_energy(self, flux, eta):
        self.E += eta * flux * self.area

    def redistribute_energy(self, dt):
        for n in self.neighbors:
            delta_E = self.sigma * (self.E - n.E) * dt
            self.E -= delta_E
            n.E += delta_E

    def store_energy(self, dt, P_metabolic):
        dQ = self.E - P_metabolic*dt
        dQ = max(min(dQ, self.capacity - self.Q), 0)
        self.Q += dQ
        self.E -= dQ

    def adapt_conductivity(self, kT_local, Ea):
        self.sigma = self.sigma * np.exp(-Ea/kT_local)

# Example setup
nodes = [BioEngineeredNode(i, capacity=100.0, area=1.0, sigma0=0.1) for i in range(10)]
# connect in chain for simplicity
for i in range(len(nodes)-1):
    nodes[i].add_neighbor(nodes[i+1])
    nodes[i+1].add_neighbor(nodes[i])

# simulation step
dt = 0.01
for step in range(1000):
    for node in nodes:
        node.capture_energy(flux=np.random.rand(), eta=0.5)
    for node in nodes:
        node.redistribute_energy(dt)
    for node in nodes:
        node.store_energy(dt, P_metabolic=0.1)
    for node in nodes:
        node.adapt_conductivity(kT_local=300, Ea=0.01)




# Octahedral Lattice + Phase Propagation Simulation
# Dependencies: numpy, matplotlib

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3D projection

# -----------------------------
# 1. Parameters
# -----------------------------
phi = 1.618   # golden ratio spacing
num_shells = 4
nodes_per_shell = 6  # simplified octahedron
kappa0 = 1.0
xi = 1.0  # coherence length
np.random.seed(42)

# -----------------------------
# 2. Generate φ-spaced octahedral lattice
# -----------------------------
def generate_octahedral_lattice(r0=1.0, phi=phi, shells=num_shells):
    positions = []
    for n in range(shells):
        r = r0 * (phi**n)
        # simple octahedral node positions (±x, ±y, ±z)
        coords = np.array([[r,0,0], [-r,0,0], [0,r,0], [0,-r,0], [0,0,r], [0,0,-r]])
        positions.append(coords)
    return np.vstack(positions)

positions = generate_octahedral_lattice()
num_nodes = positions.shape[0]

# -----------------------------
# 3. Initialize node phases randomly
# -----------------------------
phases = np.random.uniform(0, 2*np.pi, size=num_nodes)

# -----------------------------
# 4. Define directional factor D_ij (simplified as 1 for now)
# -----------------------------
D = np.ones((num_nodes, num_nodes))

# -----------------------------
# 5. Compute coupling kernel
# -----------------------------
def compute_kernel(positions, phases, kappa0=kappa0, xi=xi, D=D):
    K = np.zeros((num_nodes, num_nodes))
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i != j:
                d = np.linalg.norm(positions[i]-positions[j])
                delta_phi = phases[i] - phases[j]
                K[i,j] = kappa0 * np.exp(-d/xi) * np.cos(delta_phi) * D[i,j]
    return K

K = compute_kernel(positions, phases)

# -----------------------------
# 6. Propagation / simple update
# -----------------------------
# Example input vector
x = np.random.rand(num_nodes)
y = K @ x  # linear propagation

# Optional: one iteration of phase gradient update (simplified)
target = np.ones(num_nodes)  # example target
learning_rate = 0.01

# Compute gradient dL/dphi_i
grad = np.zeros(num_nodes)
for k in range(num_nodes):
    grad[k] = 0
    for i in range(num_nodes):
        for j in range(num_nodes):
            if k == i:
                grad[k] += (y[i]-target[i]) * (-kappa0 * np.exp(-np.linalg.norm(positions[i]-positions[j])/xi) * np.sin(phases[i]-phases[j]))
            elif k == j:
                grad[k] += (y[i]-target[i]) * (kappa0 * np.exp(-np.linalg.norm(positions[i]-positions[j])/xi) * np.sin(phases[i]-phases[j]))

# Update phases
phases -= learning_rate * grad

# -----------------------------
# 7. Visualization
# -----------------------------
fig = plt.figure(figsize=(8,6))
ax = fig.add_subplot(111, projection='3d')
sc = ax.scatter(positions[:,0], positions[:,1], positions[:,2], c=phases, cmap='hsv', s=100)
plt.colorbar(sc, label='Phase (rad)')
ax.set_title('Octahedral φ-Spaced Lattice - Node Phases')
plt.show()



# ----------------------------
# Simulation Parameters
# ----------------------------
phi = 1.618      # Golden ratio scaling for shells
num_shells = 3   # Number of phi-scaled octahedral shells
nodes_per_shell = 8  # Octahedral nodes per shell
timesteps = 50
learning_rate = 0.05  # Prototactic drift magnitude

# Environment: a 3D gradient field (example: radiation intensity)
def environment_field(pos):
    # Simple radial gradient from origin
    return np.exp(-np.linalg.norm(pos, axis=1)/5)

# ----------------------------
# Initialize Lattice Nodes
# ----------------------------
def init_phi_octahedral(phi, shells, nodes_per_shell):
    positions = []
    for n in range(shells):
        r = phi**n
        # Octahedral positions: ±x, ±y, ±z combinations
        shell_nodes = [
            [r,0,0], [-r,0,0],
            [0,r,0], [0,-r,0],
            [0,0,r], [0,0,-r]
        ]
        positions.extend(shell_nodes[:nodes_per_shell])
    return np.array(positions, dtype=float)

nodes = init_phi_octahedral(phi, num_shells, nodes_per_shell)
phases = np.random.rand(len(nodes))*2*np.pi  # Node phase for computation
velocities = np.zeros_like(nodes)

# ----------------------------
# Simulation Loop
# ----------------------------
for t in range(timesteps):
    # Compute environmental forces (gradient of field)
    field_values = environment_field(nodes)
    grad = np.zeros_like(nodes)
    delta = 1e-2
    for i,pos in enumerate(nodes):
        for j in range(3):
            d_pos = pos.copy()
            d_pos[j] += delta
            grad[i,j] = (environment_field(d_pos.reshape(1,3)) - field_values[i])/delta

    # Prototactic drift: move nodes along gradient weighted by phase (simple coupling)
    drift = learning_rate * grad * (0.5 + 0.5*np.sin(phases))[:,None]
    nodes += drift

    # Optional: simple phase update based on neighboring nodes
    # (nearest neighbors approximated by distance)
    for i, pos in enumerate(nodes):
        dists = np.linalg.norm(nodes - pos, axis=1)
        neighbors = np.where((dists>0) & (dists<phi**2))[0]
        if len(neighbors)>0:
            phase_avg = np.mean(phases[neighbors])
            phases[i] += 0.01*(phase_avg - phases[i])

# ----------------------------
# Visualization
# ----------------------------
fig = plt.figure(figsize=(7,7))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(nodes[:,0], nodes[:,1], nodes[:,2], c=np.sin(phases), cmap='viridis', s=80)
ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_zlabel('Z')
ax.set_title('Phi-Octahedral Prototactic Lattice after Simulation')
plt.show()
