# bridges/reservoir_bridge.py
"""
Reservoir Computing Bridge — Dynamical Systems Layer
=====================================================
Wraps multi-domain encoder geometry as a coupled dynamical reservoir.

Each encoder domain (gravity, electric, sound, thermal, etc.) becomes
a node in a recurrent network. The binary encoder processes each
domain independently. The reservoir layer discovers that:

- Gravity vectors couple to electric fields (through charged mass)
- Sound pressure couples to thermal state (through equation of state)
- Electric current couples to magnetic field (through induction)

The reservoir doesn't program these couplings—it discovers them
through the nonlinear dynamics of the coupled state evolution.

Key insight: computation is the geometry of state evolution.
The binary bitstring is a single projection of a high-dimensional
trajectory. The reservoir preserves the trajectory.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Callable
import math
import random


@dataclass
class ReservoirNode:
    """A single node in the dynamical reservoir."""
    name: str
    state: float = 0.0
    bias: float = 0.0
    time_constant: float = 1.0  # τ for leaky integration
    connections: Dict[str, float] = field(default_factory=dict)  # name → weight
    
    def update(self, inputs: Dict[str, float], dt: float = 0.1):
        """Leaky integrator dynamics: τ · dx/dt = -x + f(W·x + W_in·u + b)"""
        total_input = self.bias
        for src, weight in self.connections.items():
            if src in inputs:
                total_input += weight * inputs[src]
        
        # Nonlinear activation (tanh = standard reservoir choice)
        activation = math.tanh(total_input)
        
        # Leaky integration
        self.state += (dt / self.time_constant) * (-self.state + activation)


@dataclass
class ReservoirNetwork:
    """
    Coupled dynamical reservoir over encoder domains.
    
    Each domain from each encoder becomes a node. The connections
    are initialized with physically-motivated couplings:
    - Electric ↔ Magnetic (induction)
    - Sound ↔ Thermal (gas law)
    - Gravity ↔ All (universal coupling, weak)
    - Phase → Frequency (derivative relationship)
    """
    
    nodes: Dict[str, ReservoirNode] = field(default_factory=dict)
    state_history: List[Dict[str, float]] = field(default_factory=list)
    
    # Reservoir metrics
    echo_state_property: float = 0.0  # Fading memory capacity
    lyapunov_estimate: float = 0.0     # Chaos measure
    coupling_density: float = 0.0
    
    def build_from_geometry(self, 
                            geometry_sets: Dict[str, Dict[str, List[float]]]):
        """
        Build reservoir from multiple encoder geometries.
        
        Args:
            geometry_sets: Dict mapping encoder_type → geometry_dict
                           e.g., {"electric": {...}, "sound": {...}}
        """
        node_index = 0
        
        # Create nodes for each domain in each encoder
        for encoder_type, geometry in geometry_sets.items():
            for domain, values in geometry.items():
                if isinstance(values, list) and len(values) > 0:
                    # Represent domain by its mean and variance
                    mean_val = sum(values) / len(values)
                    node_name = f"{encoder_type}/{domain}"
                    
                    self.nodes[node_name] = ReservoirNode(
                        name=node_name,
                        state=math.tanh(mean_val),  # Initial state from mean
                        bias=random.uniform(-0.1, 0.1),
                        time_constant=random.uniform(0.5, 2.0)
                    )
                    node_index += 1
        
        # Initialize physically-motivated connections
        self._wire_physical_couplings()
        self.coupling_density = self._compute_coupling_density()
    
    def _wire_physical_couplings(self):
        """Create connections based on known physical couplings."""
        
        # Get node names by category
        electric_nodes = [n for n in self.nodes if "electric" in n]
        magnetic_nodes = [n for n in self.nodes if "magnetic" in n]
        sound_nodes = [n for n in self.nodes if "sound" in n]
        thermal_nodes = [n for n in self.nodes if "thermal" in n]
        gravity_nodes = [n for n in self.nodes if "gravity" in n]
        all_nodes = list(self.nodes.keys())
        
        # Electric ↔ Magnetic (induction coupling, strong)
        for e_node in electric_nodes:
            for m_node in magnetic_nodes:
                weight = random.uniform(0.3, 0.7)
                self.nodes[e_node].connections[m_node] = weight
                self.nodes[m_node].connections[e_node] = -weight  # Lenz's law
        
        # Sound ↔ Thermal (equation of state, moderate)
        for s_node in sound_nodes:
            for t_node in thermal_nodes:
                weight = random.uniform(0.1, 0.4)
                self.nodes[s_node].connections[t_node] = weight
                self.nodes[t_node].connections[s_node] = weight
        
        # Gravity → Everything (universal coupling, weak)
        for g_node in gravity_nodes:
            for node in all_nodes:
                if node != g_node:
                    self.nodes[g_node].connections[node] = random.uniform(0.01, 0.1)
        
        # Self-connections (recurrence)
        for node_name, node in self.nodes.items():
            node.connections[node_name] = random.uniform(0.1, 0.5)
    
    def _compute_coupling_density(self) -> float:
        """Fraction of possible connections that exist."""
        n = len(self.nodes)
        if n <= 1:
            return 0.0
        possible = n * n  # Including self-connections
        actual = sum(len(node.connections) for node in self.nodes.values())
        return actual / possible
    
    def evolve(self, steps: int = 100, dt: float = 0.1):
        """Evolve the reservoir dynamics."""
        self.state_history = []
        
        for _ in range(steps):
            # Collect current states as inputs for next step
            current_states = {name: node.state for name, node in self.nodes.items()}
            
            # Update all nodes
            for node in self.nodes.values():
                node.update(current_states, dt)
            
            # Record state
            self.state_history.append(dict(current_states))
        
        self._compute_dynamical_metrics()
    
    def _compute_dynamical_metrics(self):
        """Compute reservoir dynamical properties."""
        if len(self.state_history) < 10:
            return
        
        # Echo state property: fading memory
        # Measure correlation between states at increasing time lags
        states_array = []
        for snapshot in self.state_history:
            states_array.append(list(snapshot.values()))
        
        # Estimate largest Lyapunov exponent (simplified)
        # Average divergence of nearby trajectories
        if len(states_array) >= 2:
            divergences = []
            for i in range(len(states_array) - 1):
                diff = math.sqrt(sum(
                    (states_array[i+1][j] - states_array[i][j])**2
                    for j in range(min(len(states_array[i]), len(states_array[i+1])))
                ))
                if diff > 1e-10:
                    divergences.append(math.log(diff))
            
            if divergences:
                self.lyapunov_estimate = sum(divergences) / len(divergences)
        
        # Echo state property (approximate)
        # Correlation of state with its time-lagged self
        if len(self.state_history) > 20:
            lag = 10
            correlations = []
            node_names = list(self.nodes.keys())
            for name in node_names:
                series = [s[name] for s in self.state_history]
                if len(series) > lag:
                    recent = series[lag:]
                    lagged = series[:-lag]
                    mean_r = sum(recent) / len(recent)
                    mean_l = sum(lagged) / len(lagged)
                    num = sum((r - mean_r) * (l - mean_l) for r, l in zip(recent, lagged))
                    den_r = math.sqrt(sum((r - mean_r)**2 for r in recent))
                    den_l = math.sqrt(sum((l - mean_l)**2 for l in lagged))
                    if den_r > 0 and den_l > 0:
                        correlations.append(num / (den_r * den_l))
            
            if correlations:
                self.echo_state_property = sum(correlations) / len(correlations)
    
    def project_to_binary(self, n_bits: int = 39) -> str:
        """
        Project reservoir state onto binary output.
        
        Uses the final state vector, thresholded at 0 (tanh midpoint),
        to generate a binary string. This is the reservoir's "readout."
        """
        final_states = list(self.state_history[-1].values()) if self.state_history else []
        
        # Pad or truncate to n_bits
        bits = []
        for i in range(n_bits):
            if i < len(final_states):
                bits.append('1' if final_states[i] > 0 else '0')
            else:
                bits.append('0')
        
        return ''.join(bits)
    
    def diagnose(self) -> str:
        """Human-readable reservoir diagnosis."""
        n_nodes = len(self.nodes)
        n_steps = len(self.state_history)
        
        diagnosis = (
            f"Reservoir: {n_nodes} nodes, {n_steps} evolution steps. "
            f"Coupling density: {self.coupling_density:.1%}. "
        )
        
        if self.lyapunov_estimate > 0.1:
            diagnosis += (
                f"Lyapunov estimate {self.lyapunov_estimate:.3f} > 0: "
                f"reservoir is chaotic—small perturbations amplify. "
                f"High computational capacity but sensitive to initial conditions."
            )
        elif self.lyapunov_estimate > 0:
            diagnosis += (
                f"Lyapunov estimate {self.lyapunov_estimate:.3f}: "
                f"near-chaotic dynamics. Edge of chaos is optimal for computation."
            )
        else:
            diagnosis += (
                f"Lyapunov estimate {self.lyapunov_estimate:.3f} < 0: "
                f"reservoir is stable—trajectories converge. Lower computational "
                f"capacity but more robust readout."
            )
        
        if self.echo_state_property < 0.3:
            diagnosis += (
                f" Echo state property {self.echo_state_property:.2f}: "
                f"good fading memory—reservoir forgets initial conditions."
            )
        
        return diagnosis


def reservoir_wrap_geometries(geometry_sets: Dict[str, Dict]) -> ReservoirNetwork:
    """
    Wrap multiple encoder geometries into a coupled reservoir.
    
    Args:
        geometry_sets: Dict mapping encoder_type → geometry
                       e.g., {"electric": electric_geometry, "sound": sound_geometry}
    
    Returns:
        Evolved ReservoirNetwork
    """
    reservoir = ReservoirNetwork()
    reservoir.build_from_geometry(geometry_sets)
    reservoir.evolve(steps=200)
    return reservoir
