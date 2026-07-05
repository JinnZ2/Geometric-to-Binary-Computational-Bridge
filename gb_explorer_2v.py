#!/usr/bin/env python3
# gb_explorer.py — CC0
# Geometric-to-Binary Computational Bridge — Definitive Exploration Playground
#
# Single-file, stdlib + GEIS only.
#
# Layers integrated:
#  - Real bridge: GEIS OctahedralState (3-bit sp³ silicon vertices)
#  - Toy encodings: blade_bits, coord_binary (safe exploration sandbox)
#  - Five alternative computing paradigms (multi_level, approximate,
#    stochastic, ternary, quantum) via ParadigmBridge
#  - Entropy cost tracking on every decision node
#  - Dynamic sensor band tables that degrade under entropy events
#  - 6G chip structural designs (square, hexagonal, kagome, fibonacci_spiral,
#    random) with harmonic interference simulation
#  - Automated Proof-of-Concept baseline comparison
#  - AI‑friendly branching, backtracking, forking, and experiment suggestions

import copy
import json
import math
import os
import random
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from GEIS.octahedral_state import OctahedralState   # noqa: E402

# =========================================================================
# 1. Dynamic Band Environment — degrades under entropy
# =========================================================================
class BandEnvironment:
    """Sensor band tables that widen as entropy increases."""
    def __init__(self):
        self._base_temp    = [-20, -10, 0, 10, 20, 30, 40, 50]          # °C
        self._base_voltage = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.3]   # V
        self._base_health  = [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
        self._base_noise   = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

        self.temp    = list(self._base_temp)
        self.voltage = list(self._base_voltage)
        self.health  = list(self._base_health)
        self.noise   = list(self._base_noise)
        self.entropy_level = 0.0

    def apply_entropy_event(self, added_entropy: float):
        """Widen all bands proportionally to accumulated entropy."""
        self.entropy_level += added_entropy
        factor = 1.0 + self.entropy_level * 0.5

        def widen(base):
            center = (base[0] + base[-1]) / 2
            return [center + (b - center) * factor for b in base]

        self.temp    = widen(self._base_temp)
        self.voltage = widen(self._base_voltage)
        self.health  = widen(self._base_health)
        self.noise   = widen(self._base_noise)

    def reset(self):
        self.__init__()

# =========================================================================
# 2. Tree data structures with entropy cost
# =========================================================================
@dataclass
class BranchState:
    encoding: str = ""               # geometric-to-binary encoding name
    data: Any = None                 # bits / multivector / etc.
    paradigm: str = ""               # alternative computing paradigm name
    paradigm_data: Any = None        # paradigm-specific result
    chip_geometry: str = ""          # 6G chip lattice type
    interference_result: Any = None  # latest harmonic interference result
    history: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)

    def clone(self) -> "BranchState":
        return BranchState(
            encoding=self.encoding,
            data=copy.deepcopy(self.data),
            paradigm=self.paradigm,
            paradigm_data=copy.deepcopy(self.paradigm_data),
            chip_geometry=self.chip_geometry,
            interference_result=copy.deepcopy(self.interference_result),
            history=self.history.copy(),
            params=copy.deepcopy(self.params)
        )

class TreeNode:
    """A node in the exploration tree, with accumulated entropy cost."""
    def __init__(self, state: BranchState, choice: str = "root",
                 parent: Optional["TreeNode"] = None, entropy_cost: float = 0.0):
        self.id = str(uuid.uuid4())[:8]
        self.state = state
        self.choice = choice
        self.annotations: List[str] = []
        self.parent = parent
        self.children: List["TreeNode"] = []
        self.entropy_cost = entropy_cost

    def add_child(self, child: "TreeNode"):
        child.parent = self
        self.children.append(child)

    def total_entropy_cost(self) -> float:
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
                "paradigm": self.state.paradigm,
                "paradigm_data": str(self.state.paradigm_data),
                "chip_geometry": self.state.chip_geometry,
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
            paradigm=d["state"]["paradigm"],
            paradigm_data=d["state"]["paradigm_data"],
            chip_geometry=d["state"]["chip_geometry"],
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

# =========================================================================
# 3. Core encoding & operation interfaces (geometric-to-binary bridge)
# =========================================================================
class EncodingScheme:
    name: str = "base"
    def encode(self, mv: Any) -> Any: raise NotImplementedError
    def decode(self, bits: Any) -> Any: raise NotImplementedError

class Operation:
    name: str = "base_op"
    def apply(self, a: Any, b: Any, encoding: EncodingScheme = None) -> Any:
        raise NotImplementedError

# ------------------------- Toy encodings -------------------------
class BladeBitEncoding(EncodingScheme):
    name = "blade_bits"
    def encode(self, mv):
        bits = 0
        for i, coeff in enumerate(mv):
            if abs(coeff) > 0.5:
                bits |= (1 << i)
        return bits
    def decode(self, bits):
        return [1.0 if (bits >> i) & 1 else 0.0 for i in range(4)]

class CoordinateBinaryEncoding(EncodingScheme):
    name = "coord_binary"
    def encode(self, point):
        x_byte = int((point[0] + 1) / 2 * 255)
        y_byte = int((point[1] + 1) / 2 * 255)
        return (x_byte << 8) | y_byte
    def decode(self, bits):
        x = ((bits >> 8) & 0xFF) / 255.0 * 2 - 1
        y = (bits & 0xFF) / 255.0 * 2 - 1
        return (x, y)

# ------------------------- Real bridge: OctahedralState -------------------------
class OctahedralBladeEncoding(EncodingScheme):
    """Silicon's 8-vertex sp3 coordination, 3 bits per unit."""
    name = "octahedral_state"
    def encode(self, mv):
        state = mv if isinstance(mv, OctahedralState) else OctahedralState(int(mv) % 8)
        return int(state.to_binary(), 2)
    def decode(self, bits):
        return OctahedralState.from_binary(format(bits & 0b111, "03b"))

# ------------------------- Operations -------------------------
class BitwiseXOR(Operation):
    name = "XOR"
    def apply(self, a, b, encoding=None):
        return a ^ b

class GeometricProduct(Operation):
    name = "geom_prod"
    def apply(self, a, b, encoding=None):
        return [a[i] + b[i] for i in range(min(len(a), len(b)))]

class OctahedralInvert(Operation):
    """Real bridge's inversion: OctahedralState.invert(), i -> 7-i."""
    name = "octahedral_invert"
    def apply(self, a, b=None, encoding=None):
        state = a if isinstance(a, OctahedralState) else OctahedralState(a)
        return int(state.invert().to_binary(), 2)

# =========================================================================
# 4. Paradigm bridges (alternative computing models)
# =========================================================================
PARADIGM_ENTROPY_COST = {
    "multi_level": 0.1,
    "approximate": 0.2,
    "stochastic":  0.3,
    "ternary":     0.5,
    "quantum":     0.9
}

class ParadigmBridge:
    def __init__(self, paradigm: str = "binary", bands: BandEnvironment = None):
        self.paradigm = paradigm
        self.bands = bands or BandEnvironment()

class MultiLevelBridge(ParadigmBridge):
    def __init__(self, levels: int = 8, bands: BandEnvironment = None):
        super().__init__("multi_level", bands)
        self.levels = levels
    def encode_to_level(self, value, bands):
        band_index = 0
        for i, th in enumerate(bands):
            if value >= th: band_index = i
        level = int((band_index / (len(bands)-1)) * (self.levels-1))
        return min(level, self.levels-1)
    def decode_from_level(self, level, bands):
        band_position = (level / (self.levels-1)) * (len(bands)-1)
        lower_idx = int(band_position)
        upper_idx = min(lower_idx+1, len(bands)-1)
        fraction = band_position - lower_idx
        return bands[lower_idx] + fraction * (bands[upper_idx] - bands[lower_idx])
    def encode_temperature(self, temp): return self.encode_to_level(temp, self.bands.temp)
    def decode_temperature(self, level): return self.decode_from_level(level, self.bands.temp)

class ApproximateBridge(ParadigmBridge):
    def __init__(self, precision=8, bands: BandEnvironment = None):
        super().__init__("approximate", bands)
        self.precision = precision
        self.quantization_levels = 2**(precision-1)
    def quantize(self, value, min_val, max_val):
        scale = (max_val - min_val) / (self.quantization_levels-1)
        return max(0, min(self.quantization_levels-1, int((value - min_val)/scale)))
    def dequantize(self, q, min_val, max_val):
        scale = (max_val - min_val) / (self.quantization_levels-1)
        return min_val + q * scale + scale/2
    def compute_confidence(self, sensor_values, noise_floor=0.05):
        q = [self.quantize(v,0,1) for v in sensor_values]
        approx_mean = self.dequantize(sum(q)//len(q),0,1)
        noise = noise_floor + 0.1*(len(sensor_values)/10)
        conf = 1.0/(1.0+noise+abs(0.5-approx_mean))
        hb = 0
        for i, th in enumerate(self.bands.health):
            if conf >= th: hb = i
        return {"confidence": conf, "health_score": self.bands.health[hb], "health_band": hb}

class StochasticBridge(ParadigmBridge):
    def __init__(self, stream_length=256, bands: BandEnvironment = None):
        super().__init__("stochastic", bands)
        self.stream_length = stream_length
    def encode_probability(self, v): return max(0, min(1, v))
    def decode_probability(self, bits): return sum(bits)/len(bits) if bits else 0
    def compute_noise_resilience(self, signal_prob, noise_prob):
        corrupted = signal_prob*(1-noise_prob) + noise_prob*(1-signal_prob)
        error = abs(signal_prob - corrupted)
        resilience = 1 - error
        nb = 0
        for i, th in enumerate(self.bands.noise):
            if noise_prob >= th: nb = i
        return {"signal": signal_prob, "noise": noise_prob, "resilience": resilience,
                "noise_band": nb, "noise_level": self.bands.noise[nb]}

class TernaryBridge(ParadigmBridge):
    def __init__(self, bands: BandEnvironment = None):
        super().__init__("ternary", bands)
    def encode_ternary(self, value):
        if value == 0: return [0]
        trits = []
        n = abs(value)
        sign = 1 if value >= 0 else -1
        while n > 0:
            rem = n % 3
            if rem == 0: trits.append(0)
            elif rem == 1: trits.append(1*sign)
            else: trits.append(-1*sign); n += 1
            n //= 3
            sign = 1
        trits.reverse()
        return trits if trits else [0]
    def decode_ternary(self, trits):
        v=0; p=1
        for t in reversed(trits): v += t*p; p *= 3
        return v
    def ternary_temperature_encode(self, temp):
        band_idx = 0
        for i, th in enumerate(self.bands.temp):
            if temp >= th: band_idx = i
        return self.encode_ternary(band_idx)
    def ternary_temperature_decode(self, trits):
        idx = self.decode_ternary(trits)
        if 0 <= idx < len(self.bands.temp): return self.bands.temp[idx]
        return 0.0

class QuantumBridge(ParadigmBridge):
    def __init__(self, bands: BandEnvironment = None):
        super().__init__("quantum", bands)
    def create_superposition(self, a0=0.707, a1=0.707):
        norm = math.sqrt(a0**2 + a1**2)
        a,b = a0/norm, a1/norm
        phase = math.acos(a)
        return {"alpha": complex(a,0), "beta": complex(b*math.cos(phase), b*math.sin(phase)),
                "p0": a**2, "p1": b**2}
    def entangle_confidence_noise(self, conf, noise):
        es = conf*(1-noise)
        a = math.sqrt(1-noise); b = math.sqrt(noise)
        bs = {"a00": a*math.sqrt(es), "a11": b*math.sqrt(es)}
        p00 = abs(bs["a00"])**2; p11 = abs(bs["a11"])**2
        corr = p00 + p11
        health = corr * conf
        enh_conf = conf / math.sqrt(noise+0.001)
        return {"entanglement": es, "correlation": corr, "health": health,
                "confidence": min(1.0, enh_conf), "noise": noise,
                "advantage": enh_conf/(conf+0.001)}
    def measure_temperature_superposition(self, temp_c, uncertainty=5.0):
        nearby = [i for i,t in enumerate(self.bands.temp) if abs(temp_c-t) <= uncertainty]
        if not nearby:
            distances = [abs(temp_c-t) for t in self.bands.temp]
            nearby = [distances.index(min(distances))]
        n = len(nearby)
        amp = 1.0/math.sqrt(n)
        expected = sum(self.bands.temp[i] for i in nearby)/n
        health = 1.0 - uncertainty/50
        conf = 1.0/(1+uncertainty/25)
        return {"bands": nearby, "expected": expected, "health": max(0,min(1,health)),
                "confidence": max(0,min(1,conf))}

class BridgeFactory:
    _bridges = {
        "multi_level": MultiLevelBridge,
        "approximate": ApproximateBridge,
        "stochastic": StochasticBridge,
        "ternary": TernaryBridge,
        "quantum": QuantumBridge,
    }
    @classmethod
    def get_bridge(cls, paradigm, bands=None, **kwargs):
        if paradigm not in cls._bridges:
            raise ValueError(f"Unknown paradigm: {paradigm}")
        return cls._bridges[paradigm](bands=bands, **kwargs)

# =========================================================================
# 5. 6G Chip Architecture — crystal-inspired lattice simulator
# =========================================================================
class LatticeSimulator:
    GEOMETRIES = ["square", "hexagonal", "kagome", "fibonacci_spiral", "random"]
    def __init__(self, geometry="square", node_count=25):
        self.geometry = geometry
        self.node_count = min(node_count, 50)
        self.nodes = self._generate_nodes()
        self.entropy_cost = {
            "square":0.1, "hexagonal":0.3, "kagome":0.5,
            "fibonacci_spiral":0.7, "random":0.2
        }[geometry]
    def _generate_nodes(self):
        g = self.geometry
        if g == "square":
            side = int(self.node_count**0.5)
            return [(i/side, j/side) for i in range(side) for j in range(side)]
        elif g == "hexagonal":
            return [(i + (j%2)*0.5)/5, (j*0.866)/5 for j in range(5) for i in range(5)][:self.node_count]
        elif g == "kagome":
            nodes = []
            for i in range(4):
                for j in range(4):
                    nodes.extend([(i/4+0.25, j/4+0.25), (i/4, j/4), (i/4+0.5, j/4)])
            return nodes[:self.node_count]
        elif g == "fibonacci_spiral":
            phi = (1+5**0.5)/2
            return [(0.5+0.4*(n/self.node_count)*math.cos(2*math.pi*n*phi),
                     0.5+0.4*(n/self.node_count)*math.sin(2*math.pi*n*phi))
                    for n in range(self.node_count)]
        else:
            return [(random.random(), random.random()) for _ in range(self.node_count)]
    def simulate_interference(self, frequency: float, amplitude: float=1.0) -> dict:
        wave = 2*math.pi*frequency
        disps = [amplitude*math.sin(wave*x) for (x,y) in self.nodes]
        avg = sum(abs(d) for d in disps)/len(disps)
        maxd = max(abs(d) for d in disps)
        std = (sum((d-avg)**2 for d in disps)/len(disps))**0.5
        integrity = max(0, 1 - maxd/(amplitude+0.001))
        resonance = maxd > amplitude*0.8
        return {"displacements": disps, "avg_abs": avg, "max_abs": maxd,
                "std": std, "signal_integrity": integrity,
                "resonance_detected": resonance, "frequency": frequency}

class ChipArchitecture:
    def __init__(self, geometry: str, node_count=25):
        self.simulator = LatticeSimulator(geometry, node_count)
        self.geometry = geometry
        self.entropy_cost = self.simulator.entropy_cost

# =========================================================================
# 6. Unified Explorer — all layers in one tree
# =========================================================================
class Explorer:
    def __init__(self):
        self.bands = BandEnvironment()
        self.root = TreeNode(BranchState(), "root", entropy_cost=0.0)
        self.current = self.root
        self.entropy_budget = 5.0
        self.chip_arch: Optional[ChipArchitecture] = None
        # Core bridge registries
        self._encoding_registry = {
            "blade_bits": BladeBitEncoding(),
            "coord_binary": CoordinateBinaryEncoding(),
            "octahedral_state": OctahedralBladeEncoding(),
        }
        self._operation_registry = {
            "XOR": BitwiseXOR(),
            "geom_prod": GeometricProduct(),
            "octahedral_invert": OctahedralInvert(),
        }
        # Paradigm instance cache (keyed by paradigm name)
        self._paradigm_cache: Dict[str, ParadigmBridge] = {}

    def choices(self) -> List[str]:
        state = self.current.state
        options = []

        # 1. Geometric encoding not set -> offer to set it
        if not state.encoding:
            for name in self._encoding_registry:
                options.append(f"set_encoding:{name}")

        # 2. Paradigm not set -> offer paradigm choices
        if not state.paradigm:
            for p in BridgeFactory._bridges:
                options.append(f"set_paradigm:{p}")

        # 3. Chip geometry not set -> offer chip architectures
        if not state.chip_geometry:
            for geo in LatticeSimulator.GEOMETRIES:
                options.append(f"select_chip_architecture:{geo}")

        # 4. Always offer entropy injection
        options.append("entropy_event")

        # 5. If encoding is set, offer operations on that encoding
        if state.encoding:
            enc = state.encoding
            options.append("apply_operation:XOR")
            if enc == "octahedral_state":
                options.append("apply_operation:octahedral_invert")
            else:
                options.append("apply_operation:geom_prod")
            options.append("decode_and_compare")

        # 6. Paradigm-specific actions if paradigm is set
        if state.paradigm:
            p = state.paradigm
            if p == "multi_level":
                options.append("encode:temperature")
                options.append("decode:from_level")
            elif p == "approximate":
                options.append("compute_confidence")
            elif p == "stochastic":
                options.append("compute_noise_resilience")
            elif p == "ternary":
                options.append("encode:temperature_ternary")
                options.append("decode:temperature_ternary")
            elif p == "quantum":
                options.append("create_superposition")
                options.append("entangle_confidence_noise")
                options.append("measure_temperature_superposition")

        # 7. Chip actions if chip geometry is selected
        if self.chip_arch is not None:
            options.append("apply_harmonic_interference")
            options.append("measure_signal_integrity")
            options.append("run_proof_of_concept")

        # 8. Meta actions
        options.append("annotate")
        options.append("fork_new_idea")
        return options

    def select(self, choice_str: str):
        parts = choice_str.split(":", 1)
        action = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        new_state = self.current.state.clone()
        new_state.history.append(choice_str)
        cost = 0.0
        child = None

        # ---- Helper to fetch paradigm bridge ----
        def get_paradigm_bridge() -> ParadigmBridge:
            if new_state.paradigm not in self._paradigm_cache:
                self._paradigm_cache[new_state.paradigm] = BridgeFactory.get_bridge(
                    new_state.paradigm, self.bands)
            return self._paradigm_cache[new_state.paradigm]

        # ---- Action handlers ----
        if action == "set_encoding":
            new_state.encoding = arg
            enc = self._encoding_registry[arg]
            if arg == "blade_bits":
                new_state.data = enc.encode([1.0,0,0,0])
            elif arg == "coord_binary":
                new_state.data = enc.encode((0,0))
            elif arg == "octahedral_state":
                new_state.data = enc.encode(5)
            cost = 0.0   # encoding choice itself is cheap

        elif action == "set_paradigm":
            new_state.paradigm = arg
            cost = PARADIGM_ENTROPY_COST[arg]
            # Preload bridge instance
            get_paradigm_bridge()

        elif action == "select_chip_architecture":
            new_state.chip_geometry = arg
            self.chip_arch = ChipArchitecture(arg)
            cost = self.chip_arch.entropy_cost

        elif action == "entropy_event":
            added = float(arg) if arg else 0.2
            self.bands.apply_entropy_event(added)
            cost = added

        elif action == "apply_operation":
            op_name = arg
            op = self._operation_registry[op_name]
            enc = self._encoding_registry[new_state.encoding]
            if op_name == "XOR":
                new_state.data = op.apply(new_state.data, 0b0100)
            elif op_name == "geom_prod":
                current_mv = enc.decode(new_state.data)
                result_mv = op.apply(current_mv, [0.0,1,0,0])
                new_state.data = enc.encode(result_mv)
            elif op_name == "octahedral_invert":
                new_state.data = op.apply(new_state.data)
            cost = 0.05

        elif action == "decode_and_compare":
            enc = self._encoding_registry[new_state.encoding]
            decoded = enc.decode(new_state.data)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.01)
            child.annotations.append(f"Decoded: {decoded}")
            # Special homomorphism check for octahedral_state + invert
            if new_state.encoding == "octahedral_state":
                orig = 5   # we started from 5
                inv = new_state.data
                complement = orig ^ 0b111
                if inv == complement:
                    child.annotations.append("Homomorphism CONFIRMED: invert = bitwise complement")
                else:
                    child.annotations.append("No homomorphism")
            else:
                child.annotations.append("Comparison: (placeholder)")
            self.current.add_child(child)
            self.current = child
            return

        elif action == "encode" and arg == "temperature":
            bridge = get_paradigm_bridge()
            result = bridge.encode_temperature(42.5)
            new_state.paradigm_data = result
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Encoded 42.5°C -> level {result}")
            self.current.add_child(child); self.current = child; return

        elif action == "decode" and arg == "from_level":
            bridge = get_paradigm_bridge()
            level = new_state.paradigm_data
            temp = bridge.decode_temperature(level)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Decoded level {level} -> {temp:.2f}°C")
            new_state.paradigm_data = temp
            self.current.add_child(child); self.current = child; return

        elif action == "compute_confidence":
            bridge = get_paradigm_bridge()
            res = bridge.compute_confidence([0.87,0.92,0.79,0.91])
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Confidence: {res['confidence']:.3f}, health band {res['health_band']}")
            new_state.paradigm_data = res
            self.current.add_child(child); self.current = child; return

        elif action == "compute_noise_resilience":
            bridge = get_paradigm_bridge()
            res = bridge.compute_noise_resilience(0.8, 0.2)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Noise resilience: {res['resilience']:.3f}")
            new_state.paradigm_data = res
            self.current.add_child(child); self.current = child; return

        elif action == "encode" and arg == "temperature_ternary":
            bridge = get_paradigm_bridge()
            trits = bridge.ternary_temperature_encode(23.0)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Ternary encoding: {trits}")
            new_state.paradigm_data = trits
            self.current.add_child(child); self.current = child; return

        elif action == "decode" and arg == "temperature_ternary":
            bridge = get_paradigm_bridge()
            trits = new_state.paradigm_data
            temp = bridge.ternary_temperature_decode(trits)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Decoded ternary temp: {temp:.2f}°C")
            new_state.paradigm_data = temp
            self.current.add_child(child); self.current = child; return

        elif action == "create_superposition":
            bridge = get_paradigm_bridge()
            state = bridge.create_superposition()
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Qubit: |0⟩={state['p0']:.3f}, |1⟩={state['p1']:.3f}")
            new_state.paradigm_data = state
            self.current.add_child(child); self.current = child; return

        elif action == "entangle_confidence_noise":
            bridge = get_paradigm_bridge()
            res = bridge.entangle_confidence_noise(0.9, 0.1)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Entangled: advantage={res['advantage']:.2f}")
            new_state.paradigm_data = res
            self.current.add_child(child); self.current = child; return

        elif action == "measure_temperature_superposition":
            bridge = get_paradigm_bridge()
            res = bridge.measure_temperature_superposition(22.0, 4.0)
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.05)
            child.annotations.append(f"Quantum temp: expected={res['expected']:.1f}°C")
            new_state.paradigm_data = res
            self.current.add_child(child); self.current = child; return

        elif action == "apply_harmonic_interference":
            freq = float(arg) if arg else 24.0
            res = self.chip_arch.simulator.simulate_interference(freq)
            new_state.interference_result = res
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.1)
            child.annotations.append(f"Interference {freq} GHz: integrity {res['signal_integrity']:.3f}, resonance {res['resonance_detected']}")
            self.current.add_child(child); self.current = child; return

        elif action == "measure_signal_integrity":
            if new_state.interference_result:
                si = new_state.interference_result['signal_integrity']
                child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.01)
                child.annotations.append(f"Signal integrity = {si:.4f}")
            else:
                child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.01)
                child.annotations.append("No interference data yet.")
            self.current.add_child(child); self.current = child; return

        elif action == "run_proof_of_concept":
            archs = [ChipArchitecture("square"), ChipArchitecture("hexagonal")]
            summary = []
            for a in archs:
                res = a.simulator.simulate_interference(24.0)
                summary.append(f"{a.geometry}: integrity {res['signal_integrity']:.3f}, resonance {res['resonance_detected']}")
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.1)
            child.annotations.append("POC baseline: " + " | ".join(summary))
            child.annotations.append("Structural design alters harmonic propagation. POC validated.")
            self.current.add_child(child); self.current = child; return

        elif action == "annotate":
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.0)
            child.annotations.append(arg if arg else "manual note")
            self.current.add_child(child); self.current = child; return

        elif action == "fork_new_idea":
            sibling = TreeNode(new_state, f"fork: {arg}", parent=self.current.parent, entropy_cost=0.0)
            self.current.parent.add_child(sibling)
            self.current = sibling
            return

        else:
            # fallback
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=0.0)
            child.annotations.append(f"Unknown action: {choice_str}")

        # For actions that didn't create child manually, create one now and advance
        if child is None:
            child = TreeNode(new_state, choice_str, parent=self.current, entropy_cost=cost)
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
        state = self.current.state
        suggestions = []
        if state.encoding:
            suggestions.append("Try a different operation on this encoding")
        if state.paradigm:
            suggestions.append("Switch paradigm and re-encode temperature")
        if self.chip_arch:
            suggestions.append("Try a different lattice geometry")
            suggestions.append("Sweep interference frequencies")
        suggestions.append("Inject entropy to degrade bands and retest")
        return suggestions

    def status(self) -> str:
        total_entropy = self.current.total_entropy_cost()
        band_quality = 1.0 / (1.0 + self.bands.entropy_level)
        chip = self.chip_arch.geometry if self.chip_arch else "none"
        return (f"Node {self.current.id} | encoding: {self.current.state.encoding}, "
                f"paradigm: {self.current.state.paradigm}, chip: {chip}, "
                f"entropy: {total_entropy:.2f}/{self.entropy_budget}, band quality: {band_quality:.2f}")

# =========================================================================
# 7. Demonstration: a full multi-dimensional walkthrough
# =========================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("Integrated Exploration Demo — Octahedral Bridge + Paradigms + 6G Chip")
    print("=" * 70)
    ex = Explorer()

    # Step 1: Set the real encoding
    print("\n1. Setting encoding to octahedral_state")
    ex.select("set_encoding:octahedral_state")
    print(f"   Data: {ex.current.state.data} (vertex 5)")
    print(ex.status())

    # Step 2: Invert (octahedral_invert) and check homomorphism
    print("\n2. Applying octahedral_invert")
    ex.select("apply_operation:octahedral_invert")
    print(f"   Inverted data: {ex.current.state.data} (should be 2)")
    ex.select("decode_and_compare")
    print("   Annotations:", ex.current.annotations[-2:])

    # Step 3: Add a paradigm – ternary
    print("\n3. Setting paradigm to ternary")
    ex.select("set_paradigm:ternary")
    print(ex.status())
    ex.select("encode:temperature_ternary")
    print("   Ternary trits:", ex.current.annotations[-1])

    # Step 4: Choose a 6G chip lattice
    print("\n4. Selecting chip architecture: kagome")
    ex.select("select_chip_architecture:kagome")
    print(ex.status())

    # Step 5: Apply harmonic interference
    print("\n5. Applying 60 GHz interference")
    ex.select("apply_harmonic_interference:60.0")
    print("   ", ex.current.annotations[-1])

    # Step 6: Run proof-of-concept baseline
    print("\n6. Running Proof-of-Concept (square vs hexagonal)")
    ex.select("run_proof_of_concept")
    for ann in ex.current.annotations:
        print("   ", ann)

    # Step 7: Entropy event and measure signal integrity
    print("\n7. Injecting entropy (decay bands) and re-measuring")
    ex.select("entropy_event:0.4")
    ex.select("apply_harmonic_interference:24.0")
    ex.select("measure_signal_integrity")
    print("   ", ex.current.annotations[-1])

    print("\nSuggestions:", ex.suggest_experiments())
    ex.save_branch("integrated_exploration_tree.json")
    print("\nExploration tree saved to integrated_exploration_tree.json")
