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
