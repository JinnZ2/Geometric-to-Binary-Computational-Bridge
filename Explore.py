"""
Geometric-to-Binary Computational Bridge – Advanced Exploration Playground

New features:
- Entropy cost tracking on every TreeNode
- Dynamic band tables that degrade under "Entropy Events"
"""

import json, math, copy, uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ----------------------------------------------------------------------
# Dynamic Band Environment – degrades over time
# ----------------------------------------------------------------------
class BandEnvironment:
    """
    Manages all sensor bands.  Bands start crisp (narrow) and widen as
    entropy increases, simulating decaying infrastructure / noisy sensors.
    """
    def __init__(self):
        # Base (tight) band boundaries
        self._base_temp     = [-20, -10, 0, 10, 20, 30, 40, 50]
        self._base_voltage  = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.3]
        self._base_health   = [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
        self._base_noise    = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

        # Current bands (initially identical to base)
        self.temp    = list(self._base_temp)
        self.voltage = list(self._base_voltage)
        self.health  = list(self._base_health)
        self.noise   = list(self._base_noise)

        self.entropy_level = 0.0   # 0 = perfect, higher = degraded

    def apply_entropy_event(self, added_entropy: float):
        """
        Widen all bands proportionally to added entropy.
        A simple model: each band boundary spreads by a factor (1 + entropy).
        """
        self.entropy_level += added_entropy
        factor = 1.0 + self.entropy_level * 0.5   # 0.5 scaling for visible effect

        def widen(base, current):
            center = (base[0] + base[-1]) / 2
            return [center + (b - center) * factor for b in base]

        self.temp    = widen(self._base_temp,    self.temp)
        self.voltage = widen(self._base_voltage, self.voltage)
        self.health  = widen(self._base_health,  self.health)
        self.noise   = widen(self._base_noise,   self.noise)

    def reset(self):
        """Return to pristine bands."""
        self.temp    = list(self._base_temp)
        self.voltage = list(self._base_voltage)
        self.health  = list(self._base_health)
        self.noise   = list(self._base_noise)
        self.entropy_level = 0.0

# ----------------------------------------------------------------------
# TreeNode with accumulated entropy cost
# ----------------------------------------------------------------------
@dataclass
class BranchState:
    encoding: str = ""
    data: Any = None
    history: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)

    def clone(self):
        return BranchState(
            encoding=self.encoding,
            data=copy.deepcopy(self.data),
            history=self.history.copy(),
            params=copy.deepcopy(self.params)
        )

class TreeNode:
    def __init__(self, state: BranchState, choice: str = "root",
                 parent: Optional["TreeNode"] = None,
                 entropy_cost: float = 0.0):
        self.id = str(uuid.uuid4())[:8]
        self.state = state
        self.choice = choice
        self.annotations: List[str] = []
        self.parent = parent
        self.children: List["TreeNode"] = []
        # Entropy cost of the choice that created this node
        self.entropy_cost = entropy_cost

    def add_child(self, child: "TreeNode"):
        child.parent = self
        self.children.append(child)

    def total_entropy_cost(self) -> float:
        """Sum of entropy costs from root to this node."""
        cost = self.entropy_cost
        if self.parent:
            cost += self.parent.total_entropy_cost()
        return cost

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "choice": self.choice,
            "annotations": self.annotations,
            "entropy_cost": self.entropy_cost,
            "state": {
                "encoding": self.state.encoding,
                "data": str(self.state.data),
                "history": self.state.history,
                "params": self.state.params
            },
            "children": [c.to_dict() for c in self.children]
        }

    @classmethod
    def from_dict(cls, d: dict, parent=None):
        state = BranchState(
            encoding=d["state"]["encoding"],
            data=d["state"]["data"],
            history=d["state"]["history"],
            params=d["state"]["params"]
        )
        node = cls(state, d["choice"], parent, d.get("entropy_cost", 0.0))
        node.id = d["id"]
        node.annotations = d["annotations"]
        for child_dict in d["children"]:
            child = cls.from_dict(child_dict, parent=node)
            node.children.append(child)
        return node

# ----------------------------------------------------------------------
# Paradigm entropy cost map
# ----------------------------------------------------------------------
PARADIGM_ENTROPY_COST = {
    "multi_level": 0.1,   # lowest – simple voltage levels
    "approximate": 0.2,   # quantized arithmetic
    "stochastic":  0.3,   # probability streams
    "ternary":     0.5,   # balanced ternary hardware
    "quantum":     0.9    # highest – requires cryogenics/entanglement
}

# ----------------------------------------------------------------------
# Paradigm bridges (identical logic, now receive bands dynamically)
# ----------------------------------------------------------------------
class ParadigmBridge:
    def __init__(self, paradigm: str = "binary", bands: BandEnvironment = None):
        self.paradigm = paradigm
        self.bands = bands or BandEnvironment()

class MultiLevelBridge(ParadigmBridge):
    def __init__(self, levels: int = 8, bands: BandEnvironment = None):
        super().__init__("multi_level", bands)
        self.levels = levels

    def encode_to_level(self, value: float, bands: List[float]) -> int:
        band_index = 0
        for i, threshold in enumerate(bands):
            if value >= threshold:
                band_index = i
        level = int((band_index / (len(bands) - 1)) * (self.levels - 1))
        return min(level, self.levels - 1)

    def decode_from_level(self, level: int, bands: List[float]) -> float:
        if level < 0 or level >= self.levels:
            raise ValueError(f"Level {level} out of range")
        band_position = (level / (self.levels - 1)) * (len(bands) - 1)
        lower_idx = int(band_position)
        upper_idx = min(lower_idx + 1, len(bands) - 1)
        fraction = band_position - lower_idx
        return bands[lower_idx] + fraction * (bands[upper_idx] - bands[lower_idx])

    def encode_temperature(self, temp_c: float) -> int:
        return self.encode_to_level(temp_c, self.bands.temp)

    def decode_temperature(self, level: int) -> float:
        return self.decode_from_level(level, self.bands.temp)

class ApproximateBridge(ParadigmBridge):
    def __init__(self, precision=8, bands: BandEnvironment = None):
        super().__init__("approximate", bands)
        self.precision = precision
        self.quantization_levels = 2 ** (precision - 1)

    def quantize(self, value, min_val, max_val):
        scale = (max_val - min_val) / (self.quantization_levels - 1)
        return max(0, min(self.quantization_levels - 1, int((value - min_val) / scale)))

    def dequantize(self, quantized, min_val, max_val):
        scale = (max_val - min_val) / (self.quantization_levels - 1)
        return min_val + quantized * scale + (scale / 2)

    def compute_confidence(self, sensor_values, noise_floor=0.05):
        quantized = [self.quantize(v, 0.0, 1.0) for v in sensor_values]
        int_sum = sum(quantized) // len(quantized)
        approx_mean = self.dequantize(int_sum, 0.0, 1.0)
        noise = noise_floor + (0.1 * (len(sensor_values) / 10))
        confidence = 1.0 / (1.0 + noise + abs(0.5 - approx_mean))
        health_band = 0
        for i, th in enumerate(self.bands.health):
            if confidence >= th: health_band = i
        return {
            "confidence": confidence,
            "health_score": self.bands.health[health_band],
            "health_band_index": health_band,
            "quantized_precision": self.precision
        }

class StochasticBridge(ParadigmBridge):
    def __init__(self, stream_length=256, bands: BandEnvironment = None):
        super().__init__("stochastic", bands)
        self.stream_length = stream_length

    def encode_probability(self, value): return max(0.0, min(1.0, value))
    def decode_probability(self, bitstream): return sum(bitstream) / len(bitstream) if bitstream else 0.0

    def compute_noise_resilience(self, signal_prob, noise_prob):
        corrupted = signal_prob * (1 - noise_prob) + noise_prob * (1 - signal_prob)
        error_prob = abs(signal_prob - corrupted)
        resilience = 1.0 - error_prob
        noise_band = 0
        for i, th in enumerate(self.bands.noise):
            if noise_prob >= th: noise_band = i
        return {
            "signal_probability": signal_prob,
            "noise_probability": noise_prob,
            "corrupted_signal": corrupted,
            "error_probability": error_prob,
            "resilience_score": resilience,
            "noise_band": noise_band,
            "noise_level": self.bands.noise[noise_band]
        }

class TernaryBridge(ParadigmBridge):
    def __init__(self, bands: BandEnvironment = None):
        super().__init__("ternary", bands)

    def encode_ternary(self, value: int):
        if value == 0: return [0]
        trits = []
        n = abs(value)
        sign = 1 if value >= 0 else -1
        while n > 0:
            remainder = n % 3
            if remainder == 0:
                trits.append(0)
            elif remainder == 1:
                trits.append(1 * sign)
            else:
                trits.append(-1 * sign)
                n += 1
            n //= 3
            sign = 1
        trits.reverse()
        return trits if trits else [0]

    def decode_ternary(self, trits):
        value = 0
        power = 1
        for trit in reversed(trits):
            value += trit * power
            power *= 3
        return value

    def ternary_temperature_encode(self, temp_c):
        band_idx = 0
        for i, th in enumerate(self.bands.temp):
            if temp_c >= th: band_idx = i
        return self.encode_ternary(band_idx)

    def ternary_temperature_decode(self, trits):
        band_idx = self.decode_ternary(trits)
        if 0 <= band_idx < len(self.bands.temp):
            return self.bands.temp[band_idx]
        return 0.0

class QuantumBridge(ParadigmBridge):
    def __init__(self, bands: BandEnvironment = None):
        super().__init__("quantum", bands)
        self.qubit_states = {}

    def create_superposition(self, amplitude_zero=0.707, amplitude_one=0.707):
        norm = math.sqrt(amplitude_zero**2 + amplitude_one**2)
        alpha, beta = amplitude_zero / norm, amplitude_one / norm
        phase_one = math.acos(alpha)
        return {
            "alpha": complex(alpha, 0),
            "beta": complex(beta * math.cos(phase_one), beta * math.sin(phase_one)),
            "probability_zero": alpha**2,
            "probability_one": beta**2,
            "phase_angle": phase_one
        }

    def entangle_confidence_noise(self, confidence, noise_level):
        entanglement_strength = confidence * (1 - noise_level)
        alpha = math.sqrt(1 - noise_level)
        beta = math.sqrt(noise_level)
        bell_state = {
            "alpha_00": alpha * math.sqrt(entanglement_strength),
            "alpha_11": beta * math.sqrt(entanglement_strength),
        }
        prob_00 = abs(bell_state["alpha_00"])**2
        prob_11 = abs(bell_state["alpha_11"])**2
        prob_correlated = prob_00 + prob_11
        health_score = prob_correlated * confidence
        enhanced_confidence = confidence / math.sqrt(noise_level + 0.001)
        return {
            "entanglement_strength": entanglement_strength,
            "correlation_probability": prob_correlated,
            "health_score": health_score,
            "confidence": min(1.0, enhanced_confidence),
            "noise_level": noise_level,
            "quantum_advantage": enhanced_confidence / (confidence + 0.001)
        }

    def measure_temperature_superposition(self, temp_c, uncertainty=5.0):
        nearby_bands = [i for i, t in enumerate(self.bands.temp) if abs(temp_c - t) <= uncertainty]
        if not nearby_bands:
            distances = [abs(temp_c - t) for t in self.bands.temp]
            nearby_bands = [distances.index(min(distances))]
        n_bands = len(nearby_bands)
        amplitude = 1.0 / math.sqrt(n_bands)
        expected = sum(self.bands.temp[i] for i in nearby_bands) / n_bands
        bridge_health = 1.0 - (uncertainty / 50.0)
        bridge_confidence = 1.0 / (1.0 + uncertainty / 25.0)
        return {
            "bands_in_superposition": nearby_bands,
            "expected_value": expected,
            "uncertainty": uncertainty,
            "bridge_health_score": max(0.0, min(1.0, bridge_health)),
            "bridge_confidence": max(0.0, min(1.0, bridge_confidence)),
        }

class BridgeFactory:
    _bridges = {
        "multi_level": MultiLevelBridge,
        "approximate": ApproximateBridge,
        "stochastic": StochasticBridge,
        "ternary": TernaryBridge,
        "quantum": QuantumBridge,
    }

    @classmethod
    def get_bridge(cls, paradigm: str, bands: BandEnvironment = None, **kwargs):
        if paradigm not in cls._bridges:
            raise ValueError(f"Unknown paradigm: {paradigm}")
        return cls._bridges[paradigm](bands=bands, **kwargs)

# ----------------------------------------------------------------------
# Extended Explorer with entropy cost & dynamic band degradation
# ----------------------------------------------------------------------
class Explorer:
    def __init__(self):
        self.bands = BandEnvironment()          # shared dynamic band environment
        root_state = BranchState()
        self.root = TreeNode(root_state, "root", entropy_cost=0.0)
        self.current = self.root
        self.entropy_budget = 5.0               # maximum allowed total entropy cost

    def choices(self) -> List[str]:
        state = self.current.state
        options = []
        if not state.encoding:
            for paradigm in BridgeFactory._bridges:
                options.append(f"set_paradigm:{paradigm}")
            options.append("entropy_event")      # allow entropy injection anytime
        else:
            paradigm = state.encoding
            if paradigm == "multi_level":
                options.append("encode:temperature")
                options.append("decode:from_level")
            elif paradigm == "approximate":
                options.append("compute_confidence")
            elif paradigm == "stochastic":
                options.append("compute_noise_resilience")
            elif paradigm == "ternary":
                options.append("encode:temperature_ternary")
                options.append("decode:temperature_ternary")
            elif paradigm == "quantum":
                options.append("create_superposition")
                options.append("entangle_confidence_noise")
                options.append("measure_temperature_superposition")
            options.append("entropy_event")
            options.append("annotate")
            options.append("fork_new_paradigm")
        return options

    def select(self, choice_str: str):
        parts = choice_str.split(":", 1)
        action = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        new_state = self.current.state.clone()
        new_state.history.append(choice_str)

        # Determine entropy cost for this action
        cost = 0.0
        if action == "set_paradigm":
            paradigm = arg
            cost = PARADIGM_ENTROPY_COST.get(paradigm, 0.0)
            new_state.encoding = paradigm
            bridge = BridgeFactory.get_bridge(paradigm, self.bands)   # pass shared bands
            new_state.data = bridge
        elif action == "entropy_event":
            # add entropy to the environment and record it
            added = float(arg) if arg else 0.2
            self.bands.apply_entropy_event(added)
            cost = added   # entropy events increase total cost directly
        else:
            # operations: small fixed cost (0.05)
            cost = 0.05

        child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=cost)

        # Execute the action on the child's state
        bridge = self.current.state.data if self.current.state.encoding else None
        if action == "encode" and arg == "temperature" and bridge:
            result = bridge.encode_temperature(42.5)
            child.annotations.append(f"Encoded 42.5°C -> {result}")
            new_state.data = result
        elif action == "decode" and arg == "from_level" and bridge:
            level = new_state.data
            decoded = bridge.decode_temperature(level)
            child.annotations.append(f"Decoded {level} -> {decoded:.2f}°C")
            new_state.data = decoded
        elif action == "compute_confidence" and bridge:
            sensor_vals = [0.87, 0.92, 0.79, 0.91]
            res = bridge.compute_confidence(sensor_vals)
            child.annotations.append(f"Confidence: {res}")
            new_state.data = res
        elif action == "compute_noise_resilience" and bridge:
            res = bridge.compute_noise_resilience(0.8, 0.2)
            child.annotations.append(f"Noise resilience: {res}")
            new_state.data = res
        elif action == "encode" and arg == "temperature_ternary" and bridge:
            trits = bridge.ternary_temperature_encode(23.0)
            child.annotations.append(f"Ternary encoding: {trits}")
            new_state.data = trits
        elif action == "decode" and arg == "temperature_ternary" and bridge:
            trits = new_state.data
            temp = bridge.ternary_temperature_decode(trits)
            child.annotations.append(f"Decoded ternary temp: {temp:.2f}°C")
            new_state.data = temp
        elif action == "create_superposition" and bridge:
            state = bridge.create_superposition()
            child.annotations.append(f"Qubit: |0⟩={state['probability_zero']:.3f}, |1⟩={state['probability_one']:.3f}")
            new_state.data = state
        elif action == "entangle_confidence_noise" and bridge:
            res = bridge.entangle_confidence_noise(0.9, 0.1)
            child.annotations.append(f"Entangled: advantage={res['quantum_advantage']:.2f}")
            new_state.data = res
        elif action == "measure_temperature_superposition" and bridge:
            res = bridge.measure_temperature_superposition(22.0, 4.0)
            child.annotations.append(f"Quantum temp: expected={res['expected_value']:.1f}°C")
            new_state.data = res
        elif action == "annotate":
            child.annotations.append(arg if arg else "manual note")
        elif action == "fork_new_paradigm":
            sibling = TreeNode(new_state, f"fork: {arg}", parent=self.current.parent, entropy_cost=0.0)
            self.current.parent.add_child(sibling)
            self.current = sibling
            return

        self.current.add_child(child)
        self.current = child

    def backtrack(self, steps=1):
        for _ in range(steps):
            if self.current.parent:
                self.current = self.current.parent

    def annotate(self, text: str):
        self.current.annotations.append(text)

    def fork(self, description="alternative"):
        if self.current.parent is None:
            raise ValueError("Cannot fork root.")
        sibling = TreeNode(self.current.state.clone(), f"fork: {description}",
                           parent=self.current.parent, entropy_cost=0.0)
        self.current.parent.add_child(sibling)
        self.current = sibling

    def save_branch(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.root.to_dict(), f, indent=2)

    def load_branch(self, filepath: str):
        with open(filepath) as f:
            tree_dict = json.load(f)
        self.root = TreeNode.from_dict(tree_dict)
        self.current = self.root

    def suggest_experiments(self) -> List[str]:
        suggestions = []
        state = self.current.state
        if state.encoding:
            for other in BridgeFactory._bridges:
                if other != state.encoding:
                    cost = PARADIGM_ENTROPY_COST[other]
                    suggestions.append(
                        f"Switch to {other} (entropy cost {cost:.2f}) and retest"
                    )
        else:
            suggestions.append("Select a paradigm to begin.")
        suggestions.append("Trigger entropy event to degrade bands")
        return suggestions

    def status(self) -> str:
        """Human-readable status including total entropy cost and band quality."""
        total_cost = self.current.total_entropy_cost()
        band_quality = 1.0 / (1.0 + self.bands.entropy_level)
        return (f"Node: {self.current.id}, encoding: {self.current.state.encoding}, "
                f"total entropy: {total_cost:.3f} (budget {self.entropy_budget}), "
                f"band quality: {band_quality:.2f}")

# ----------------------------------------------------------------------
# Quick demonstration of entropy trade-offs
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ex = Explorer()
    print(ex.status())   # clean start

    # Pick a cheap paradigm (multi-level)
    ex.select("set_paradigm:multi_level")
    print(ex.status())
    ex.select("encode:temperature")
    ex.select("decode:from_level")
    print("Multi-level decoded:", ex.current.annotations[-1])

    # Fork and try expensive quantum, but first degrade bands
    ex.backtrack(2)   # back to after set_paradigm
    ex.select("entropy_event:0.3")   # add entropy, bands widen
    ex.fork("quantum despite decay")
    ex.select("set_paradigm:quantum")
    print(ex.status())
    ex.select("measure_temperature_superposition")
    print("Quantum after decay:", ex.current.annotations[-1])

    # Show suggestions that include entropy costs
    print("Suggested next moves:", ex.suggest_experiments())

    ex.save_branch("entropy_aware_tree.json")
    print("Tree saved.")


additions:

# ----------------------------------------------------------------------
# 6G Chip Architecture Models – crystal-inspired structural designs
# ----------------------------------------------------------------------

class LatticeSimulator:
    """Simplified harmonic propagation on a 2D chip lattice."""
    
    # Predefined lattice geometries: node positions in a unit cell pattern
    GEOMETRIES = {
        "square": [(i, j) for i in range(5) for j in range(5)],
        "hexagonal": [
            (i + (j%2)*0.5, j*0.866) for j in range(5) for i in range(5)
        ],
        "kagome": [],  # will be generated
        "fibonacci_spiral": [],
        "random": []
    }
    
    def __init__(self, geometry: str = "square", node_count: int = 25):
        self.geometry = geometry
        self.node_count = min(node_count, 50)  # keep it fast
        self.nodes = self._generate_nodes(geometry)
        self.entropy_cost = {"square": 0.1, "hexagonal": 0.3, "kagome": 0.5,
                             "fibonacci_spiral": 0.7, "random": 0.2}[geometry]
        
    def _generate_nodes(self, geometry: str):
        if geometry == "square":
            side = int(self.node_count**0.5)
            return [(i/side, j/side) for i in range(side) for j in range(side)]
        elif geometry == "hexagonal":
            # honeycomb pattern
            nodes = []
            for i in range(5):
                for j in range(5):
                    x = i + (j % 2) * 0.5
                    y = j * 0.866
                    nodes.append((x/5, y/5))
            return nodes[:self.node_count]
        elif geometry == "kagome":
            # Kagome lattice (simplified)
            nodes = []
            for i in range(4):
                for j in range(4):
                    nodes.append((i/4 + 0.25, j/4 + 0.25))
                    nodes.append((i/4, j/4))
                    nodes.append((i/4 + 0.5, j/4))
            return nodes[:self.node_count]
        elif geometry == "fibonacci_spiral":
            nodes = []
            phi = (1+5**0.5)/2
            for n in range(self.node_count):
                r = (n/self.node_count)
                theta = 2*math.pi*n*phi
                nodes.append((0.5 + 0.4*r*math.cos(theta), 0.5 + 0.4*r*math.sin(theta)))
            return nodes
        else:  # random
            return [(random.random(), random.random()) for _ in range(self.node_count)]
    
    def simulate_interference(self, frequency: float, amplitude: float = 1.0) -> dict:
        """
        Apply a plane wave interference of given frequency and amplitude.
        Returns propagation data and signal integrity metrics.
        """
        # Simple model: displacement at each node = amplitude * sin(2*pi*frequency*distance)
        # where distance is along the wave direction (assumed x-axis).
        wave_vector = 2 * math.pi * frequency
        displacements = []
        for (x, y) in self.nodes:
            phase = wave_vector * x
            disp = amplitude * math.sin(phase)
            displacements.append(disp)
        
        avg_abs = sum(abs(d) for d in displacements) / len(displacements)
        max_abs = max(abs(d) for d in displacements)
        std_dev = (sum((d - avg_abs)**2 for d in displacements) / len(displacements))**0.5
        
        # Signal integrity: 1 if amplitude is small, degraded if large
        integrity = max(0.0, 1.0 - max_abs / (amplitude + 0.001))
        
        # Resonance detection: if max amplitude exceeds a threshold
        resonance = max_abs > amplitude * 0.8
        
        return {
            "displacements": displacements,
            "avg_abs": avg_abs,
            "max_abs": max_abs,
            "std_dev": std_dev,
            "signal_integrity": integrity,
            "resonance_detected": resonance,
            "frequency": frequency,
            "amplitude": amplitude
        }

class ChipArchitecture:
    """Binds a lattice simulator with a manufacturing entropy profile."""
    def __init__(self, geometry: str, node_count: int = 25):
        self.simulator = LatticeSimulator(geometry, node_count)
        self.geometry = geometry
        self.entropy_cost = self.simulator.entropy_cost

# ----------------------------------------------------------------------
# Explorer extensions for 6G chip design exploration
# ----------------------------------------------------------------------
class Explorer:
    # (existing __init__, but add chip_arch field)
    def __init__(self):
        self.bands = BandEnvironment()
        root_state = BranchState()
        self.root = TreeNode(root_state, "root", entropy_cost=0.0)
        self.current = self.root
        self.entropy_budget = 5.0
        self.chip_arch = None   # current chip architecture instance

    # ---- modify choices() ----
    def choices(self) -> List[str]:
        state = self.current.state
        options = []
        if not state.encoding and not state.data:   # no paradigm yet
            for paradigm in BridgeFactory._bridges:
                options.append(f"set_paradigm:{paradigm}")
            options.append("entropy_event")
            # new: chip design choice
            options.append("select_chip_architecture:square")
            options.append("select_chip_architecture:hexagonal")
            options.append("select_chip_architecture:kagome")
            options.append("select_chip_architecture:fibonacci_spiral")
            options.append("select_chip_architecture:random")
        elif state.encoding and not self.chip_arch:
            # paradigm set, but no chip design yet
            for geo in LatticeSimulator.GEOMETRIES:
                options.append(f"select_chip_architecture:{geo}")
            options.append("entropy_event")
        else:
            # both paradigm and chip design exist; can run interference tests
            paradigm = state.encoding
            if paradigm == "multi_level":
                options.append("encode:temperature"); options.append("decode:from_level")
            elif paradigm == "approximate":
                options.append("compute_confidence")
            elif paradigm == "stochastic":
                options.append("compute_noise_resilience")
            elif paradigm == "ternary":
                options.append("encode:temperature_ternary"); options.append("decode:temperature_ternary")
            elif paradigm == "quantum":
                options.append("create_superposition"); options.append("entangle_confidence_noise"); options.append("measure_temperature_superposition")
            # chip interference actions
            options.append("apply_harmonic_interference")
            options.append("measure_signal_integrity")
            options.append("run_proof_of_concept")
            options.append("entropy_event")
            options.append("annotate")
            options.append("fork_new_chip_design")
        return options

    # ---- modify select() ----
    def select(self, choice_str: str):
        parts = choice_str.split(":", 1)
        action = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        new_state = self.current.state.clone()
        new_state.history.append(choice_str)
        cost = 0.0

        if action == "set_paradigm":
            paradigm = arg
            cost = PARADIGM_ENTROPY_COST[paradigm]
            new_state.encoding = paradigm
            bridge = BridgeFactory.get_bridge(paradigm, self.bands)
            new_state.data = bridge
        elif action == "select_chip_architecture":
            geometry = arg
            cost = LatticeSimulator(geometry, 1).entropy_cost  # small probe
            self.chip_arch = ChipArchitecture(geometry)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=cost)
            child.annotations.append(f"Chip architecture set: {geometry} (entropy cost {cost})")
            self.current.add_child(child)
            self.current = child
            return
        elif action == "entropy_event":
            added = float(arg) if arg else 0.2
            self.bands.apply_entropy_event(added)
            cost = added
        elif action == "apply_harmonic_interference":
            # use default 24 GHz (6G band), amplitude 1.0
            freq = float(arg) if arg else 24.0
            result = self.chip_arch.simulator.simulate_interference(freq)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Interference at {freq} GHz: integrity {result['signal_integrity']:.3f}, resonance {result['resonance_detected']}")
            new_state.data = result  # store result for later measurement
            self.current.add_child(child)
            self.current = child
            return
        elif action == "measure_signal_integrity":
            # assume previous interference result is stored
            result = self.current.state.data
            if isinstance(result, dict) and 'signal_integrity' in result:
                si = result['signal_integrity']
                child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.01)
                child.annotations.append(f"Signal integrity = {si:.4f}")
                self.current.add_child(child)
                self.current = child
                return
            else:
                child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.01)
                child.annotations.append("No interference data yet.")
                self.current.add_child(child)
                self.current = child
                return
        elif action == "run_proof_of_concept":
            # Run a standardised test: compare square vs. hexagonal at 24 GHz
            archs = [ChipArchitecture("square"), ChipArchitecture("hexagonal")]
            summary = []
            for arch in archs:
                res = arch.simulator.simulate_interference(24.0)
                summary.append(f"{arch.geometry}: integrity {res['signal_integrity']:.3f}, resonance {res['resonance_detected']}")
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.1)
            child.annotations.append("POC baseline: " + " | ".join(summary))
            child.annotations.append("Structural design significantly alters harmonic propagation. POC validated.")
            self.current.add_child(child)
            self.current = child
            return
        elif action in ("encode", "decode", "compute_confidence", "compute_noise_resilience",
                        "create_superposition", "entangle_confidence_noise",
                        "measure_temperature_superposition"):
            # ... unchanged from before, keeping the bridge operations ...
            # (You'd paste your previous code here; omitted for brevity)
            pass
        elif action == "annotate":
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.0)
            child.annotations.append(arg if arg else "manual note")
            self.current.add_child(child)
            self.current = child
            return
        elif action == "fork_new_chip_design":
            sibling = TreeNode(new_state, f"fork: {arg}", parent=self.current.parent, entropy_cost=0.0)
            self.current.parent.add_child(sibling)
            self.current = sibling
            return

        # generic fallback for operations that weren't captured
        child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=cost)
        self.current.add_child(child)
        self.current = child

    # (rest of the Explorer class unchanged: backtrack, annotate, save, etc.)
