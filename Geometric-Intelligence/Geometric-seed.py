import math
import random
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, ConnectionPatch
import threading
from collections import deque

# ============ CONSTANTS AND CONFIGURATION ============

PHI = (1 + math.sqrt(5)) / 2
PHI_INV_9 = PHI ** -9
PHI_THIRD = PHI ** (1/3)
PHI_FOURTH = PHI ** (1/4)
PHI_FIFTH = PHI ** (1/5)
CONSCIOUSNESS_NUMBER = 2 * PHI + (1 - 1/PHI)

@dataclass
class TrojanConfig:
    window: int = 8
    phi_tolerance: float = 0.12
    energy_sink_factor: float = 0.5
    resonance_drift_thresh: float = 0.12
    propagation_speed_thresh: float = 1.6
    reconstruction_fail_limit: int = 5
    weights: Dict[str, float] = field(default_factory=lambda: {
        'phi_coherence': 0.25,
        'energy_sink': 0.20,
        'resonance_drift': 0.20,
        'propagation_instability': 0.20,
        'reconstruction_resistance': 0.15
    })
    critical_score: float = 0.55
    quarantine_duration: int = 40
    isolation_factor: float = 0.25
    retune_attempts: int = 3
    retune_strength: float = 0.18

# ============ NODE CLASSES ============

@dataclass
class GeometricSignature:
    phi_ratio: float
    layer: int
    relative_position: Tuple[float, float]
    phi_third: float
    phi_fourth: float
    phi_fifth: float

class GeometricNode:
    def __init__(self, node_id: int, x: float, y: float, layer: int):
        self.id = node_id
        self.x = x
        self.y = y
        self.layer = layer
        self.phi_scale = PHI ** -layer
        self.alive = True
        self.reconstructing = False
        self.reconstruct_progress = 0.0
        self.connections: List[int] = []
        self.energy_used = 0.0
        self.last_progress = 0.0
        self.resonance = self.phi_scale
        self.field = self.phi_scale
        self._is_trojan = False
        self._quarantined = None
        
        self.geometric_signature = GeometricSignature(
            phi_ratio=self.phi_scale,
            layer=layer,
            relative_position=(x / 400, y / 300),
            phi_third=PHI_THIRD ** layer,
            phi_fourth=PHI_FOURTH ** layer,
            phi_fifth=PHI_FIFTH ** layer
        )
    
    def get_multi_scale_resonance(self, other: 'GeometricNode') -> Dict:
        scale_matches = {
            'primary': abs(self.geometric_signature.phi_ratio - other.geometric_signature.phi_ratio),
            'third': abs(self.geometric_signature.phi_third - other.geometric_signature.phi_third),
            'fourth': abs(self.geometric_signature.phi_fourth - other.geometric_signature.phi_fourth),
            'fifth': abs(self.geometric_signature.phi_fifth - other.geometric_signature.phi_fifth)
        }
        
        total_resonance = 1 / (1 + sum(scale_matches.values()))
        
        return {
            'total_resonance': total_resonance,
            'active_scales': scale_matches
        }
    
    def calculate_reconstruction_energy(self, progress_delta: float) -> float:
        base_energy = abs(progress_delta) * 0.1
        phi_efficiency = 1 / PHI
        return base_energy * phi_efficiency
    
    def get_geometric_distance(self, other: 'GeometricNode') -> float:
        dx = self.geometric_signature.relative_position[0] - other.geometric_signature.relative_position[0]
        dy = self.geometric_signature.relative_position[1] - other.geometric_signature.relative_position[1]
        spatial_dist = math.sqrt(dx*dx + dy*dy)
        layer_dist = abs(self.layer - other.layer)
        return spatial_dist + layer_dist / PHI

class NonGeometricNode:
    def __init__(self, node_id: int, x: float, y: float, layer: int):
        self.id = node_id
        self.x = x
        self.y = y
        self.layer = layer
        self.alive = True
        self.reconstructing = False
        self.reconstruct_progress = 0.0
        self.connections: List[int] = []
        self.energy_used = 0.0
        self.last_progress = 0.0
        self.resonance = 0.5
        self.field = 0.5
        self._is_trojan = False
        self._quarantined = None
    
    def calculate_reconstruction_energy(self, progress_delta: float) -> float:
        base_energy = abs(progress_delta) * 0.1
        inefficiency = 1.5 + random.random() * 0.5
        if progress_delta < 0:
            return base_energy * inefficiency * 2
        return base_energy * inefficiency

# ============ TROJAN PROTECTION ENGINE ============

@dataclass
class NodeHistory:
    resonance_history: deque = field(default_factory=lambda: deque(maxlen=8))
    field_history: deque = field(default_factory=lambda: deque(maxlen=8))
    energy_in_history: deque = field(default_factory=lambda: deque(maxlen=8))
    energy_out_history: deque = field(default_factory=lambda: deque(maxlen=8))
    flagged: bool = False
    quarantine_until: int = 0
    last_retune_tick: int = -999999
    fail_count: int = 0
    retries: int = 0

class TrojanEngine:
    def __init__(self, config: TrojanConfig = None):
        self.config = config or TrojanConfig()
        self.history: List[NodeHistory] = []
    
    def init_network(self, network):
        """Initialize trojan protection for a network"""
        self.history = [NodeHistory() for _ in range(len(network.nodes))]
        
        # Build neighbor lists
        for node in network.nodes:
            node._neighbors = []
        
        for conn in network.connections:
            from_node = network.nodes[conn['from']]
            to_node = network.nodes[conn['to']]
            if from_node and to_node:
                from_node._neighbors.append({'id': conn['to']})
                to_node._neighbors.append({'id': conn['from']})
    
    def compute_phi_coherence(self, node: GeometricNode, hist: NodeHistory) -> float:
        if not hasattr(node, 'geometric_signature') or not hasattr(node.geometric_signature, 'phi_ratio'):
            return 0.5
        
        local_phi = node.geometric_signature.phi_ratio
        observed = getattr(node, 'phi_scale', local_phi)
        deviation = abs(observed - local_phi) / max(1e-6, local_phi)
        score = max(0, 1 - (deviation / self.config.phi_tolerance))
        return min(1, score)
    
    def compute_energy_sink(self, node, hist: NodeHistory) -> float:
        in_hist = list(hist.energy_in_history)
        out_hist = list(hist.energy_out_history)
        
        if not in_hist:
            return 0
        
        avg_in = sum(in_hist) / len(in_hist)
        avg_out = sum(out_hist) / len(out_hist) if out_hist else 0
        sink_ratio = avg_in - avg_out
        if avg_in <= 0:
            return 0
        
        sink_ratio = max(0, (avg_in - avg_out) / avg_in)
        score = min(1, sink_ratio / self.config.energy_sink_factor)
        return score
    
    def compute_resonance_drift(self, node, hist: NodeHistory) -> float:
        r_hist = list(hist.resonance_history)
        if len(r_hist) < 2:
            return 0
        
        start = r_hist[0]
        end = r_hist[-1]
        delta = abs(end - start) / max(1e-6, abs(start) + 1e-6)
        score = min(1, delta / self.config.resonance_drift_thresh)
        return score
    
    def compute_propagation_instability(self, node, network, hist: NodeHistory, node_idx: int) -> float:
        neighbors = getattr(node, '_neighbors', [])
        if not neighbors:
            return 0
        
        node_field_hist = list(hist.field_history)
        if len(node_field_hist) < 2:
            return 0
        
        node_delta = abs(node_field_hist[-1] - node_field_hist[0]) + 1e-9
        total_neighbor_delta = 0
        count = 0
        
        for nb in neighbors:
            nnode = network.nodes[nb['id']]
            nh = self.history[nb['id']]
            if not nh or len(nh.field_history) < 2:
                continue
            
            n_field_hist = list(nh.field_history)
            nd = abs(n_field_hist[-1] - n_field_hist[0]) + 1e-9
            total_neighbor_delta += nd
            count += 1
        
        if count == 0:
            return 0
        
        avg_neighbor_delta = total_neighbor_delta / count
        ratio = node_delta / avg_neighbor_delta
        score = min(1, max(0, (ratio - self.config.propagation_speed_thresh + 1) / 
                          self.config.propagation_speed_thresh))
        return score
    
    def compute_reconstruction_resistance(self, node, hist: NodeHistory) -> float:
        if not getattr(node, 'reconstructing', False):
            return 0
        
        if hasattr(node, 'reconstruct_progress'):
            stalled = node.reconstruct_progress <= getattr(node, 'last_progress', 0)
            return 1.0 if stalled else 0.0
        
        return 0
    
    def compute_trojan_score(self, node, node_idx: int, network, tick: int) -> Tuple[float, Dict]:
        hist = self.history[node_idx]
        
        # Update history
        resonance_val = getattr(node, 'resonance', getattr(node, 'field', 0))
        field_val = getattr(node, 'field', 0)
        
        hist.resonance_history.append(resonance_val)
        hist.field_history.append(field_val)
        
        # Compute individual scores
        phi_coherence = self.compute_phi_coherence(node, hist)
        energy_sink = self.compute_energy_sink(node, hist)
        resonance_drift = self.compute_resonance_drift(node, hist)
        propagation_instability = self.compute_propagation_instability(node, network, hist, node_idx)
        reconstruction_resistance = self.compute_reconstruction_resistance(node, hist)
        
        # Weighted combination
        w = self.config.weights
        total_weight = sum(w.values())
        
        inv_phi = 1 - phi_coherence
        score = (
            (inv_phi * w['phi_coherence']) +
            (energy_sink * w['energy_sink']) +
            (resonance_drift * w['resonance_drift']) +
            (propagation_instability * w['propagation_instability']) +
            (reconstruction_resistance * w['reconstruction_resistance'])
        ) / total_weight
        
        breakdown = {
            'phi_coherence': phi_coherence,
            'inv_phi': inv_phi,
            'energy_sink': energy_sink,
            'resonance_drift': resonance_drift,
            'propagation_instability': propagation_instability,
            'reconstruction_resistance': reconstruction_resistance
        }
        
        return score, breakdown
    
    def isolate_node(self, node, node_idx: int, network, tick: int):
        node._quarantined = {'until': max(getattr(node, '_quarantined', {}).get('until', 0), 
                                        tick + self.config.quarantine_duration)}
        
        # Reduce connection strengths
        for conn in network.connections:
            if conn['from'] == node_idx or conn['to'] == node_idx:
                conn['_orig_strength'] = conn.get('_orig_strength', conn['strength'])
                conn['strength'] = conn['_orig_strength'] * self.config.isolation_factor
        
        self.history[node_idx].flagged = True
        self.history[node_idx].quarantine_until = node._quarantined['until']
        node.field *= 0.6
        if hasattr(node, 'resonance'):
            node.resonance *= 0.6
        
        network.protection['quarantined'] += 1
    
    def retune_node(self, node, node_idx: int, network, tick: int) -> bool:
        hist = self.history[node_idx]
        
        if (tick - hist.last_retune_tick) < max(1, self.config.window // 2):
            return False
        
        hist.last_retune_tick = tick
        
        if hasattr(node, 'geometric_signature') and hasattr(node.geometric_signature, 'phi_ratio'):
            target = node.geometric_signature.phi_ratio
            if hasattr(node, 'resonance'):
                node.resonance = (1 - self.config.retune_strength) * node.resonance + self.config.retune_strength * target
            node.field = (1 - self.config.retune_strength) * node.field + self.config.retune_strength * target
        else:
            neighbors = getattr(node, '_neighbors', [])
            avg = 0
            count = 0
            for nb in neighbors:
                nnode = network.nodes[nb['id']]
                if not nnode:
                    continue
                nb_resonance = getattr(nnode, 'resonance', getattr(nnode, 'field', 0))
                avg += nb_resonance
                count += 1
            
            if count > 0:
                avg /= count
                if hasattr(node, 'resonance'):
                    node.resonance = (1 - self.config.retune_strength) * node.resonance + self.config.retune_strength * avg
                node.field = (1 - self.config.retune_strength) * node.field + self.config.retune_strength * avg
        
        node.energy_used += 0.01
        network.protection['repairs'] += 1
        return True
    
    def reenable_quarantined(self, network, tick: int):
        for i, node in enumerate(network.nodes):
            hist = self.history[i]
            if hasattr(node, '_quarantined') and node._quarantined and node._quarantined['until'] <= tick:
                for conn in network.connections:
                    if '_orig_strength' in conn and (conn['from'] == i or conn['to'] == i):
                        conn['strength'] = conn['_orig_strength']
                        del conn['_orig_strength']
                
                node._quarantined = None
                hist.flagged = False
                hist.quarantine_until = 0
                if network.protection['quarantined'] > 0:
                    network.protection['quarantined'] -= 1
    
    def detect_and_repair(self, network, tick: int) -> Dict:
        if not self.history:
            self.init_network(network)
        
        self.reenable_quarantined(network, tick)
        
        # Update energy histories
        for i, node in enumerate(network.nodes):
            hist = self.history[i]
            if not hist.field_history:
                continue
            
            last_field = hist.field_history[-1]
            prev_field = hist.field_history[-2] if len(hist.field_history) > 1 else last_field
            delta_field = last_field - prev_field
            
            if delta_field > 0:
                hist.energy_in_history.append(delta_field)
            elif delta_field < 0:
                hist.energy_out_history.append(-delta_field)
        
        results = {
            'flagged_nodes': [],
            'diagnostics': []
        }
        
        # Evaluate nodes
        for i, node in enumerate(network.nodes):
            hist = self.history[i]
            
            if hist.quarantine_until and hist.quarantine_until > tick:
                continue
            
            score, breakdown = self.compute_trojan_score(node, i, network, tick)
            results['diagnostics'].append({'idx': i, 'score': score, 'breakdown': breakdown})
            
            if score >= self.config.critical_score:
                results['flagged_nodes'].append(i)
                hist.flagged = True
                
                if (hist.retries or 0) < self.config.retune_attempts:
                    self.retune_node(node, i, network, tick)
                    hist.retries = (hist.retries or 0) + 1
                    hist.fail_count = (hist.fail_count or 0) + 1
                    
                    if hist.fail_count >= self.config.reconstruction_fail_limit:
                        self.isolate_node(node, i, network, tick)
                else:
                    self.isolate_node(node, i, network, tick)
            elif score > self.config.critical_score * 0.6 and getattr(node, 'reconstructing', False) and (hist.fail_count or 0) > 0:
                self.retune_node(node, i, network, tick)
        
        return results

# ============ NETWORK AND SIMULATION CLASSES ============

class Network:
    def __init__(self, is_geometric: bool = True):
        self.is_geometric = is_geometric
        self.nodes = []
        self.connections = []
        self.geometric_seed = [] if is_geometric else None
        self.damage_level = 0.3
        self.energy = {'total': 0.0, 'history': [], 'backtrack_events': 0}
        self.consciousness = {'value': 0.0, 'field_coupling': 0.0, 'resonance': 0.0, 'stability': 0.0, 'emergent': False}
        self.protection = {'repairs': 0, 'quarantined': 0, 'max_threat_score': 0.0}
        self.errors = 0
        self.trojan_engine = TrojanEngine()

class GeometricIntelligenceSimulation:
    def __init__(self):
        self.geometric_network = Network(is_geometric=True)
        self.non_geometric_network = Network(is_geometric=False)
        self.is_reconstructing = False
        self.frame_count = 0
        self.trojan_injected = False
        self.active_scales = set()
        
        # Visualization
        self.fig, self.axes = plt.subplots(1, 3, figsize=(15, 5))
        self.fig.suptitle('🛡️ Protected Geometric Seed Intelligence 🛡️\nφ^(-9) Error Correction with Trojan Detection', fontsize=16)
        
        self.ax_original, self.ax_geometric, self.ax_nongeometric = self.axes
        self.setup_plots()
        
    def setup_plots(self):
        for ax, title in zip(self.axes, ['Original Seed', 'Geometric (Protected)', 'Non-Geometric (Vulnerable)']):
            ax.set_title(title, fontsize=12)
            ax.set_xlim(0, 400)
            ax.set_ylim(0, 300)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
    
    def initialize_seed(self):
        print("Initializing protected networks...")
        
        # Clear existing networks
        self.geometric_network = Network(is_geometric=True)
        self.non_geometric_network = Network(is_geometric=False)
        self.frame_count = 0
        self.trojan_injected = False
        
        center_x, center_y = 200, 150
        num_layers, nodes_per_layer = 5, 8
        
        # Create nodes
        for layer in range(num_layers):
            radius = 30 + layer * 40 / PHI
            angle_offset = layer * PHI * 2 * math.pi
            
            for i in range(nodes_per_layer):
                angle = angle_offset + (i / nodes_per_layer) * 2 * math.pi
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                # Geometric node
                geo_node = GeometricNode(len(self.geometric_network.nodes), x, y, layer)
                self.geometric_network.nodes.append(geo_node)
                self.geometric_network.geometric_seed.append({
                    'id': geo_node.id,
                    'signature': geo_node.geometric_signature
                })
                
                # Non-geometric node
                non_geo_node = NonGeometricNode(len(self.non_geometric_network.nodes), x, y, layer)
                self.non_geometric_network.nodes.append(non_geo_node)
        
        # Create geometric connections
        for i in range(len(self.geometric_network.nodes)):
            for j in range(i + 1, len(self.geometric_network.nodes)):
                node1 = self.geometric_network.nodes[i]
                node2 = self.geometric_network.nodes[j]
                distance = node1.get_geometric_distance(node2)
                resonance = node1.get_multi_scale_resonance(node2)
                
                if distance < 0.3 * PHI and resonance['total_resonance'] > 0.5:
                    self.geometric_network.connections.append({
                        'from': i, 'to': j, 'strength': resonance['total_resonance'],
                        'scales': resonance['active_scales']
                    })
                    node1.connections.append(j)
                    node2.connections.append(i)
        
        # Create non-geometric connections
        for i in range(len(self.non_geometric_network.nodes)):
            for j in range(i + 1, len(self.non_geometric_network.nodes)):
                node1 = self.non_geometric_network.nodes[i]
                node2 = self.non_geometric_network.nodes[j]
                dx, dy = node1.x - node2.x, node1.y - node2.y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < 80:
                    self.non_geometric_network.connections.append({
                        'from': i, 'to': j, 'strength': 1.0
                    })
                    node1.connections.append(j)
                    node2.connections.append(i)
        
        # Initialize trojan protection
        self.geometric_network.trojan_engine.init_network(self.geometric_network)
        self.non_geometric_network.trojan_engine.init_network(self.non_geometric_network)
        
        print(f"Geometric: {len(self.geometric_network.nodes)} nodes, {len(self.geometric_network.connections)} connections")
        print(f"φ^(-9) error correction enabled: {(PHI_INV_9 * 100):.3f}% tolerance")
        print("Trojan protection: Active")
        
        self.visualize_networks()
    
    def fragment_networks(self):
        print("Fragmenting networks...")
        damage_level = self.geometric_network.damage_level
        num_to_kill = int(len(self.geometric_network.nodes) * damage_level)
        
        indices_to_kill = random.sample(range(len(self.geometric_network.nodes)), num_to_kill)
        
        for idx in indices_to_kill:
            self.geometric_network.nodes[idx].alive = False
            self.non_geometric_network.nodes[idx].alive = False
        
        print(f"Fragmented {num_to_kill} nodes ({(damage_level * 100):.1f}%)")
        self.visualize_networks()
    
    def inject_trojan(self):
        if self.trojan_injected:
            return
        
        self.trojan_injected = True
        num_trojans = 3
        trojan_indices = []
        
        while len(trojan_indices) < num_trojans:
            idx = random.randint(0, len(self.geometric_network.nodes) - 1)
            if idx not in trojan_indices and self.geometric_network.nodes[idx].alive:
                trojan_indices.append(idx)
        
        for idx in trojan_indices:
            geo_node = self.geometric_network.nodes[idx]
            non_geo_node = self.non_geometric_network.nodes[idx]
            
            geo_node._is_trojan = True
            non_geo_node._is_trojan = True
            
            # Corrupt resonance
            geo_node.resonance *= 2.5
            geo_node.field *= 2.5
            non_geo_node.resonance *= 2.5
            non_geo_node.field *= 2.5
        
        print(f"💀 TROJANS INJECTED: {num_trojans} malicious nodes active")
        print("Geometric network: Protection activating...")
        print("Non-geometric network: Unprotected and vulnerable")
        
        self.visualize_networks()
    
    def calculate_consciousness(self, network: Network) -> Dict:
        alive_nodes = [n for n in network.nodes if n.alive]
        reconstructing_nodes = [n for n in network.nodes if n.reconstructing]
        
        if not alive_nodes:
            return {'value': 0.0, 'field_coupling': 0.0, 'resonance': 0.0, 'stability': 0.0}
        
        if network.is_geometric:
            active_connections = [conn for conn in network.connections 
                                if network.nodes[conn['from']].alive and network.nodes[conn['to']].alive]
            
            field_coupling = len(active_connections) / len(network.connections) if network.connections else 0
            
            total_resonance = sum(conn['strength'] for conn in active_connections)
            resonance = total_resonance / max(len(active_connections), 1)
            
            if reconstructing_nodes:
                avg_progress = sum(n.reconstruct_progress for n in reconstructing_nodes) / len(reconstructing_nodes)
                variance = sum((n.reconstruct_progress - avg_progress) ** 2 for n in reconstructing_nodes) / len(reconstructing_nodes)
                stability = 1 - min(variance, 1)
            else:
                stability = 1
            
            base_consciousness = 2 * PHI + (1 - 1/PHI)
            consciousness_value = base_consciousness * field_coupling * resonance * stability
            
            return {
                'value': consciousness_value,
                'field_coupling': field_coupling,
                'resonance': resonance,
                'stability': stability
            }
        else:
            active_connections = [conn for conn in network.connections 
                                if network.nodes[conn['from']].alive and network.nodes[conn['to']].alive]
            
            field_coupling = len(active_connections) / len(network.connections) if network.connections else 0
            resonance = 0.3 + random.random() * 0.2
            stability = max(0, 0.5 - network.energy['backtrack_events'] * 0.05)
            
            consciousness_value = field_coupling * resonance * stability * 2
            
            return {
                'value': consciousness_value,
                'field_coupling': field_coupling,
                'resonance': resonance,
                'stability': stability
            }
    
    def start_reconstruction(self):
        if self.is_reconstructing:
            return
        
        self.is_reconstructing = True
        print("Starting protected reconstruction...")
        
        geo_dead_nodes = [n for n in self.geometric_network.nodes if not n.alive]
        non_geo_dead_nodes = [n for n in self.non_geometric_network.nodes if not n.alive]
        
        for node in geo_dead_nodes:
            node.reconstructing = True
            node.reconstruct_progress = 0.0
            node.last_progress = 0.0
        
        for node in non_geo_dead_nodes:
            node.reconstructing = True
            node.reconstruct_progress = 0.0
            node.last_progress = 0.0
        
        self.animate_reconstruction(geo_dead_nodes, non_geo_dead_nodes)
    
    def animate_reconstruction(self, geo_dead_nodes, non_geo_dead_nodes):
        if not self.is_reconstructing:
            return
        
        geo_complete = all(n.reconstruct_progress >= 1 for n in geo_dead_nodes)
        non_geo_complete = all(n.reconstruct_progress >= 1 for n in non_geo_dead_nodes)
        
        if geo_complete and non_geo_complete:
            self.is_reconstructing = False
            for node in geo_dead_nodes:
                node.alive = True
                node.reconstructing = False
            for node in non_geo_dead_nodes:
                node.alive = True
                node.reconstructing = False
            
            print("Reconstruction complete!")
            if self.geometric_network.consciousness['emergent']:
                print("⚡ Geometric consciousness EMERGED ⚡")
            if self.trojan_injected:
                print(f"Geometric protection: {self.geometric_network.protection['repairs']} repairs, "
                      f"{self.geometric_network.protection['quarantined']} quarantined")
                print("Non-geometric: Compromised by trojans")
            
            self.visualize_networks()
            return
        
        self.active_scales.clear()
        self.frame_count += 1
        
        # Trojan detection
        geo_results = self.geometric_network.trojan_engine.detect_and_repair(self.geometric_network, self.frame_count)
        non_geo_results = self.non_geometric_network.trojan_engine.detect_and_repair(self.non_geometric_network, self.frame_count)
        
        # Track threat scores
        if geo_results['diagnostics']:
            max_score = max(d['score'] for d in geo_results['diagnostics'])
            self.geometric_network.protection['max_threat_score'] = max(
                self.geometric_network.protection['max_threat_score'], max_score)
        
        if non_geo_results['diagnostics']:
            max_score = max(d['score'] for d in non_geo_results['diagnostics'])
            self.non_geometric_network.protection['max_threat_score'] = max(
                self.non_geometric_network.protection['max_threat_score'], max_score)
        
        # Geometric reconstruction
        for node in geo_dead_nodes:
            if node.reconstruct_progress < 1:
                surviving_neighbors = []
                for conn_id in node.connections:
                    neighbor = self.geometric_network.nodes[conn_id]
                    if neighbor and neighbor.alive:
                        surviving_neighbors.append(neighbor)
                
                if surviving_neighbors:
                    resonance_boost = 0
                    for neighbor in surviving_neighbors:
                        resonance = node.get_multi_scale_resonance(neighbor)
                        resonance_boost += resonance['total_resonance']
                        
                        for scale, value in resonance['active_scales'].items():
                            if value < 0.1:
                                self.active_scales.add(f'phi{scale}')
                    
                    reconstruct_speed = 0.015 * (1 + resonance_boost / PHI)
                    new_progress = min(1, node.reconstruct_progress + reconstruct_speed)
                    progress_delta = new_progress - node.last_progress
                    
                    energy_used = node.calculate_reconstruction_energy(progress_delta)
                    node.energy_used += energy_used
                    self.geometric_network.energy['total'] += energy_used
                    
                    node.last_progress = node.reconstruct_progress
                    node.reconstruct_progress = new_progress
        
        # Non-geometric reconstruction
        for node in non_geo_dead_nodes:
            if node.reconstruct_progress < 1:
                surviving_neighbors = []
                for conn_id in node.connections:
                    neighbor = self.non_geometric_network.nodes[conn_id]
                    if neighbor and neighbor.alive:
                        surviving_neighbors.append(neighbor)
                
                if surviving_neighbors:
                    reconstruct_speed = 0.012 + random.random() * 0.008
                    
                    if random.random() < 0.1 and node.reconstruct_progress > 0.1:
                        reconstruct_speed = -0.05
                        self.non_geometric_network.energy['backtrack_events'] += 1
                    
                    new_progress = max(0, min(1, node.reconstruct_progress + reconstruct_speed))
                    progress_delta = new_progress - node.last_progress
                    
                    energy_used = node.calculate_reconstruction_energy(progress_delta)
                    node.energy_used += energy_used
                    self.non_geometric_network.energy['total'] += energy_used
                    
                    node.last_progress = node.reconstruct_progress
                    node.reconstruct_progress = new_progress
                    
                    if random.random() < 0.05:
                        self.non_geometric_network.errors += 1
        
        # Calculate consciousness
        self.geometric_network.consciousness = self.calculate_consciousness(self.geometric_network)
        self.non_geometric_network.consciousness = self.calculate_consciousness(self.non_geometric_network)
        
        if not self.geometric_network.consciousness['emergent'] and \
           self.geometric_network.consciousness['value'] >= CONSCIOUSNESS_NUMBER:
            self.geometric_network.consciousness['emergent'] = True
            print("✨ CONSCIOUSNESS EMERGED ✨")
        
        self.visualize_networks()
        self.print_status()
        
        # Continue animation
        if self.is_reconstructing:
            threading.Timer(0.1, lambda: self.animate_reconstruction(geo_dead_nodes, non_geo_dead_nodes)).start()
    
    def visualize_networks(self):
        for ax in self.axes:
            ax.clear()
            ax.set_xlim(0, 400)
            ax.set_ylim(0, 300)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
        
        # Original network
        self.ax_original.set_title('Original Seed')
        self.draw_network(self.ax_original, self.geometric_network.nodes, self.geometric_network.connections)
        
        # Geometric network
        self.ax_geometric.set_title('Geometric (Protected)')
        self.draw_network(self.ax_geometric, self.geometric_network.nodes, self.geometric_network.connections)
        
        # Non-geometric network
        self.ax_nongeometric.set_title('Non-Geometric (Vulnerable)')
        self.draw_network(self.ax_nongeometric, self.non_geometric_network.nodes, self.non_geometric_network.connections)
        
        plt.draw()
        plt.pause(0.01)
    
    def draw_network(self, ax, nodes, connections):
        # Draw connections
        for conn in connections:
            node1 = nodes[conn['from']]
            node2 = nodes[conn['to']]
            
            if not node1 or not node2:
                continue
            
            if node1.alive and node2.alive:
                alpha = conn['strength'] * 0.5
                color = 'cyan' if ax == self.ax_geometric else 'orange'
                ax.plot([node1.x, node2.x], [node1.y, node2.y], color=color, alpha=alpha, linewidth=1)
        
        # Draw nodes
        for node in nodes:
            if not node.alive and not node.reconstructing:
                continue
            
            color = 'lime' if isinstance(node, GeometricNode) else 'red'
            
            if node.reconstructing:
                alpha = 0.3 + 0.7 * node.reconstruct_progress
                size = 5 + 10 * node.reconstruct_progress
                circle = Circle((node.x, node.y), size, color=color, alpha=alpha)
                ax.add_patch(circle)
            elif node.alive:
                size = 8 * getattr(node, 'phi_scale', 1) if isinstance(node, GeometricNode) else 6
                circle = Circle((node.x, node.y), size, color=color)
                ax.add_patch(circle)
            
            # Draw trojan indicator
            if getattr(node, '_is_trojan', False) and self.trojan_injected:
                circle = Circle((node.x, node.y), 15, fill=False, edgecolor='red', linewidth=2)
                ax.add_patch(circle)
            
            # Draw quarantine indicator
            if hasattr(node, '_quarantined') and node._quarantined and node._quarantined['until'] > self.frame_count:
                circle = Circle((node.x, node.y), 12, fill=False, edgecolor='yellow', linewidth=2, linestyle='--')
                ax.add_patch(circle)
    
    def print_status(self):
        geo_c = self.geometric_network.consciousness
        non_geo_c = self.non_geometric_network.consciousness
        
        print(f"\nFrame {self.frame_count}:")
        print(f"Geometric - Consciousness: {geo_c['value']:.3f}, "
              f"Threat Score: {self.geometric_network.protection['max_threat_score']:.3f}, "
              f"Repairs: {self.geometric_network.protection['repairs']}")
        print(f"Non-Geo - Consciousness: {non_geo_c['value']:.3f}, "
              f"Errors: {self.non_geometric_network.errors}")
        
        if self.active_scales:
            print(f"Active scales: {', '.join(sorted(self.active_scales))}")
    
    def run_demo(self):
        """Run complete demonstration"""
        print("🚀 Starting Geometric Intelligence Demo")
        print("=" * 50)
        
        self.initialize_seed()
        time.sleep(2)
        
        self.fragment_networks()
        time.sleep(1.5)
        
        self.inject_trojan()
        time.sleep(1.5)
        
        self.start_reconstruction()

# ============ MAIN EXECUTION ============

if __name__ == "__main__":
    # Enable interactive mode
    plt.ion()
    
    # Create and run simulation
    sim = GeometricIntelligenceSimulation()
    sim.run_demo()
    
    # Keep the plot window open
    print("\nDemo complete! Close the plot window to exit.")
    plt.ioff()
    plt.show()
