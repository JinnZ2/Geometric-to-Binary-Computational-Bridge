import numpy as np

# -------------------------------
# Parameters
# -------------------------------
NUM_NODES = 50              # Number of geometric nodes
DIM_8D = 8                  # 8D lattice
DIM_3D = 3                  # Project into 3D
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio
BASE_RADIUS = 1.0           # Base radius for φ-shells
TIME_STEPS = 20             # Simulation steps
COUPLING_EXP = 2            # Coupling ∝ 1/distance^p

# -------------------------------
# 1. Generate 8D nodes with φ-shells
# -------------------------------
def generate_8d_nodes(num_nodes):
    nodes = np.random.randn(num_nodes, DIM_8D)  # Random 8D coordinates
    # Scale nodes to φ-shells
    shells = np.random.randint(1, 5, size=(num_nodes, 1))  # Shell levels 1-4
    nodes *= BASE_RADIUS * PHI ** shells
    return nodes

# -------------------------------
# 2. Project 8D nodes to 3D
# -------------------------------
def project_to_3d(nodes_8d):
    # Simple linear projection: take first 3 dimensions
    return nodes_8d[:, :3]

# -------------------------------
# 3. Initialize binary states
# -------------------------------
def initialize_states(num_nodes):
    # Random 0/1 states
    return np.random.choice([0, 1], size=num_nodes)

# -------------------------------
# 4. Compute coupling based on distance
# -------------------------------
def compute_coupling(nodes_3d):
    num_nodes = len(nodes_3d)
    coupling_matrix = np.zeros((num_nodes, num_nodes))
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i != j:
                dist = np.linalg.norm(nodes_3d[i] - nodes_3d[j])
                coupling_matrix[i, j] = 1 / (dist ** COUPLING_EXP + 1e-6)
    return coupling_matrix

# -------------------------------
# 5. Update states based on coupling
# -------------------------------
def update_states(states, coupling_matrix):
    new_states = states.copy()
    for i in range(len(states)):
        influence = np.dot(coupling_matrix[i], states)
        # Binary threshold
        new_states[i] = 1 if influence > 0.5 * np.sum(coupling_matrix[i]) else 0
    return new_states

# -------------------------------
# 6. Run dynamics
# -------------------------------
nodes_8d = generate_8d_nodes(NUM_NODES)
nodes_3d = project_to_3d(nodes_8d)
states = initialize_states(NUM_NODES)
coupling = compute_coupling(nodes_3d)

print("Initial States:\n", states)

for t in range(TIME_STEPS):
    states = update_states(states, coupling)

print("Final States:\n", states)
