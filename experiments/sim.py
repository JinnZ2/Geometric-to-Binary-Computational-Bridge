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
from mpl_toolkits.mplot3d import Axes3D

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
