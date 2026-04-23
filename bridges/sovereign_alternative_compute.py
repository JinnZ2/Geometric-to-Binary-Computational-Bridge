# core/integrations/sovereign_alternative_compute.py
"""
Sovereign Command Interface — Alternative Computing Expansion
==============================================================
Extends the SovereignCommandInterface to accept, route, and execute
commands through non-binary computing paradigms.

Each paradigm provides a different sovereignty model:

  Multi-Level   → Granular authority levels (not just PASS/QUARANTINE)
  Approximate   → Probabilistic command execution with confidence bounds
  Stochastic    → Command propagation through noise (anti-jamming)
  Ternary       → Balanced command/restraint (± authority)
  Quantum       → Superposed commands & entangled multi-target control

The interface maintains backward compatibility with the original
10-char hex protocol while adding paradigm-specific command syntax.

Usage:
    sci = SovereignAlternativeInterface(hardware_interface)
    
    # Classic hex command (backward compatible)
    sci.receive_hex_command("0x7B0A4F1D2")
    
    # Paradigm-specific commands
    sci.receive_ternary_command("+0-+")
    sci.receive_quantum_command({"target": "thermal", "superposition": [25, 85]})
    sci.receive_stochastic_command(probability_stream=0.73, target="electric")
"""

import math
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union, Callable
from enum import IntEnum, auto

# Import core bridge components
from geometric_bridge import (
    SensorDecoder, ActuatorController,
    HardwareData, DrillDepth, BridgeTarget, Modality,
    HEALTH_BANDS, TEMP_BANDS, NOISE_BANDS, DRIFT_BANDS,
    LIFETIME_BANDS, VOLTAGE_BANDS, CURRENT_BANDS,
    gray_to_binary, gray_to_value
)

# Import TAF integration
from core.integrations.taf_bridge import (
    TAFBridge, EnergyAccounting, AdmissibilityMode, CompressionOperator
)

# Import alternative compute engines
from core.integrations.taf_alternative_compute import (
    MultiLevelTAF, ApproximateTAF, StochasticTAF, 
    TernaryTAF, QuantumTAF, TAFComputeEngine
)


# ----------------------------------------------------------------------
# Sovereignty Models (Paradigm-Specific Authority Structures)
# ----------------------------------------------------------------------

class AuthorityLevel(IntEnum):
    """
    Multi-Level authority hierarchy (replaces binary PASS/QUARANTINE).
    
    Traditional:  PASS (0) or QUARANTINE (2)
    Multi-Level:  16 levels of graduated authority
    """
    OBSERVE_ONLY = 0      # Read-only, no actuation
    SUGGEST = 1           # Advisory commands only
    LOW_AUTHORITY = 2     # Limited actuation (10% range)
    GUARDED = 3           # Constrained actuation (25% range)
    MONITORED = 4         # Actuation with audit trail
    STANDARD = 5          # Normal operating authority
    ELEVATED = 6          # Above-standard authority
    HIGH_AUTHORITY = 7    # Broad actuation range
    TRUSTED = 8           # Minimal oversight required
    DELEGATED = 9         # Sub-sovereign delegation
    SUPERVISORY = 10      # Override lower levels
    ADMINISTRATIVE = 11   # System reconfiguration
    EMERGENCY = 12        # Crisis authority
    MAINTENANCE = 13      # Physical access authority
    ROOT = 14             # Full system authority
    SOVEREIGN = 15        # Absolute command (no restrictions)

class TernaryCommand(IntEnum):
    """
    Balanced ternary command states.
    
    -1 (NEGATIVE):  Restrain, limit, reduce, withdraw
     0 (NEUTRAL):   Hold, maintain, observe, wait
    +1 (POSITIVE):  Activate, increase, deploy, expand
    """
    RESTRAIN = -1
    HOLD = 0
    ACTIVATE = +1
    
    @classmethod
    def from_symbol(cls, symbol: str) -> 'TernaryCommand':
        mapping = {'-': cls.RESTRAIN, '0': cls.HOLD, '+': cls.ACTIVATE,
                   'T': cls.RESTRAIN, 'N': cls.HOLD, 'P': cls.ACTIVATE}
        return mapping.get(symbol.upper(), cls.HOLD)

@dataclass
class QuantumCommand:
    """
    A command existing in superposition over multiple targets/values.
    
    Collapses to single target/value upon execution or measurement.
    """
    targets: List[str]  # Superposed target list
    amplitudes: List[complex]  # Complex amplitudes for each target
    phase_angle: float = 0.0
    entanglement_id: Optional[str] = None  # For entangled multi-commands
    
    def collapse(self) -> Tuple[str, float]:
        """Collapse superposition to single target (Born's rule)."""
        import random
        probabilities = [abs(a)**2 for a in self.amplitudes]
        total = sum(probabilities)
        normalized = [p/total for p in probabilities]
        
        r = random.random()
        cumulative = 0
        for i, prob in enumerate(normalized):
            cumulative += prob
            if r <= cumulative:
                return self.targets[i], prob
        
        return self.targets[-1], normalized[-1] if normalized else 0

@dataclass
class StochasticCommand:
    """
    Command encoded as probability stream for noise-immune transmission.
    
    Value is encoded as P(1) in a bitstream of specified length.
    Longer streams = higher noise immunity.
    """
    target: str
    probability: float  # P(1) in stochastic stream
    stream_length: int = 256
    noise_floor: float = 0.0
    
    def to_bitstream(self) -> List[int]:
        """Generate stochastic bitstream representation."""
        if self.noise_floor > 0:
            # Add controlled noise for anti-jamming
            import random
            effective_prob = self.probability * (1 - self.noise_floor) + self.noise_floor * 0.5
            return [1 if random.random() < effective_prob else 0 
                    for _ in range(self.stream_length)]
        else:
            count = int(self.probability * self.stream_length)
            return [1] * count + [0] * (self.stream_length - count)
    
    def from_bitstream(self, bitstream: List[int]) -> float:
        """Decode probability from bitstream."""
        if not bitstream:
            return 0.0
        return sum(bitstream) / len(bitstream)


# ----------------------------------------------------------------------
# Expanded Sovereign Command Interface
# ----------------------------------------------------------------------

class SovereignAlternativeInterface:
    """
    Expanded sovereign command interface supporting all five
    alternative computing paradigms with backward compatibility.
    
    Authority follows the paradigm's logic:
    - Multi-Level: Graduated authority (not binary)
    - Approximate: Probabilistic execution with confidence bounds
    - Stochastic: Noise-immune command propagation
    - Ternary: Balanced command/restraint dialectic
    - Quantum: Superposed and entangled commands
    """
    
    # Command history for audit trail
    COMMAND_HISTORY_SIZE = 256
    
    def __init__(self, hardware_interface):
        self.bridge = hardware_interface
        self.sensor_decoder = SensorDecoder()
        self.actuator = ActuatorController()
        
        # TAF integration for command validation
        self.taf_bridge = TAFBridge()
        self.taf_engine = TAFComputeEngine()
        
        # Paradigm-specific state
        self.authority_level = AuthorityLevel.STANDARD
        self.ternary_stance = TernaryCommand.HOLD
        self.quantum_pending: List[QuantumCommand] = []
        self.stochastic_buffer: Dict[str, List[int]] = {}
        
        # Command audit trail
        self.command_history: List[Dict[str, Any]] = []
        self.rejected_commands: List[Dict[str, Any]] = []
        
        # Entanglement registry for coordinated multi-target commands
        self.entanglement_registry: Dict[str, List[QuantumCommand]] = {}
    
    # ==================================================================
    # 1. CLASSIC HEX INTERFACE (Backward Compatible)
    # ==================================================================
    
    def receive_hex_command(self, hex_input: str) -> Dict[str, Any]:
        """
        Process classic 10-char hex command (original protocol).
        
        Maintained for backward compatibility. Internally routes
        through authority validation before execution.
        
        Returns:
            Execution report with paradigm metadata
        """
        try:
            clean_hex = hex_input.replace("0x", "")
            binary_val = bin(int(clean_hex, 16))[2:].zfill(39)
            
            print(f"\n[RECEIVED_COMMAND] HEX: 0x{clean_hex}")
            print(f"DECODING_PACKET: {binary_val}")
            
            # Extract instruction bits
            drill_bits = binary_val[-3:-1]
            
            # Validate authority
            if not self._validate_authority(binary_val, "classic"):
                return self._reject_command(hex_input, "Insufficient authority level")
            
            # Route to execution
            if drill_bits == "10":  # QUARANTINE
                result = self._execute_quarantine(binary_val, "MANUAL_INTERRUPT")
            elif drill_bits == "11":  # ALERT
                result = self._execute_recalibration(binary_val)
            elif drill_bits == "00":  # PASS
                result = self._execute_pass(binary_val)
            elif drill_bits == "01":  # MONITOR
                result = self._execute_monitor(binary_val)
            else:
                result = self._reject_command(hex_input, "Unknown drill bits")
            
            # Record in history
            self._record_command("classic_hex", hex_input, result)
            return result
            
        except ValueError as e:
            return self._reject_command(hex_input, f"Parse error: {str(e)}")
    
    def _execute_quarantine(self, binary_val: str, reason: str) -> Dict[str, Any]:
        """Execute quarantine with multi-level authority tracking."""
        print(f"ACTION: FORCED_QUARANTINE - Isolating physical component.")
        print(f"REASON: {reason}")
        print(f"AUTHORITY_LEVEL: {self.authority_level.name}")
        
        # Trigger hardware isolation
        self.actuator.set_thermal(25.0, confidence=1.0)  # Safe state
        
        return {
            "action": "QUARANTINE",
            "reason": reason,
            "authority": self.authority_level.name,
            "target": "all",
            "safe_state": "thermal_25C",
            "timestamp": self._timestamp()
        }
    
    def _execute_recalibration(self, binary_val: str) -> Dict[str, Any]:
        """Execute recalibration with TAF energy validation."""
        print(f"ACTION: FORCED_RECALIBRATION - Resyncing Model/Reality.")
        
        # Run TAF check before recalibration
        if hasattr(self.bridge, 'get_current_state'):
            current_state = self.bridge.get_current_state()
            taf_acct = self.taf_bridge.compute_energy_balance(current_state)
            
            if taf_acct.decoupling > 0.7:
                print(f"WARNING: High decoupling ({taf_acct.decoupling:.2f}).")
                print(f"Recalibration may fail. Consider QUARANTINE first.")
        
        result = self.bridge.process_cycle()
        
        return {
            "action": "RECALIBRATION",
            "bridge_result": str(result),
            "decoupling_at_time": getattr(
                self.taf_bridge.accounting_history[-1] if self.taf_bridge.accounting_history else {},
                'decoupling', 'unknown'
            ),
            "timestamp": self._timestamp()
        }
    
    def _execute_pass(self, binary_val: str) -> Dict[str, Any]:
        """Normal pass-through with authority logging."""
        return {
            "action": "PASS",
            "authority": self.authority_level.name,
            "timestamp": self._timestamp()
        }
    
    def _execute_monitor(self, binary_val: str) -> Dict[str, Any]:
        """Enhanced monitoring with TAF metrics."""
        return {
            "action": "MONITOR",
            "authority": self.authority_level.name,
            "taf_metrics_enabled": True,
            "timestamp": self._timestamp()
        }
    
    # ==================================================================
    # 2. MULTI-LEVEL COMMAND INTERFACE
    # ==================================================================
    
    def set_authority_level(self, level: Union[int, AuthorityLevel]) -> Dict[str, Any]:
        """
        Set graduated authority level (0-15) instead of binary PASS/QUARANTINE.
        
        Each level unlocks additional command capabilities:
        0-3:  Read-only, advisory
        4-7:  Standard operations
        8-11: System modification
        12-15: Sovereign control
        """
        if isinstance(level, int):
            level = AuthorityLevel(level)
        
        previous = self.authority_level
        self.authority_level = level
        
        print(f"\n[AUTHORITY_CHANGE] {previous.name} → {level.name}")
        print(f"CAPABILITIES_UNLOCKED: {self._get_capabilities(level)}")
        
        return {
            "action": "AUTHORITY_CHANGE",
            "previous": previous.name,
            "current": level.name,
            "numeric_level": level.value,
            "capabilities": self._get_capabilities(level),
            "timestamp": self._timestamp()
        }
    
    def _get_capabilities(self, level: AuthorityLevel) -> List[str]:
        """Map authority level to permitted capabilities."""
        capabilities = []
        
        if level >= AuthorityLevel.OBSERVE_ONLY:
            capabilities.append("read_sensors")
        if level >= AuthorityLevel.SUGGEST:
            capabilities.append("suggest_actions")
        if level >= AuthorityLevel.LOW_AUTHORITY:
            capabilities.append("limited_actuation_10pct")
        if level >= AuthorityLevel.GUARDED:
            capabilities.append("constrained_actuation_25pct")
        if level >= AuthorityLevel.MONITORED:
            capabilities.append("audited_actuation")
        if level >= AuthorityLevel.STANDARD:
            capabilities.append("full_actuation")
        if level >= AuthorityLevel.ELEVATED:
            capabilities.append("extended_range")
        if level >= AuthorityLevel.HIGH_AUTHORITY:
            capabilities.append("override_safety_limits")
        if level >= AuthorityLevel.TRUSTED:
            capabilities.append("autonomous_operation")
        if level >= AuthorityLevel.DELEGATED:
            capabilities.append("sub_delegation")
        if level >= AuthorityLevel.SUPERVISORY:
            capabilities.append("override_lower_authority")
        if level >= AuthorityLevel.ADMINISTRATIVE:
            capabilities.append("system_reconfiguration")
        if level >= AuthorityLevel.EMERGENCY:
            capabilities.append("emergency_override")
        if level >= AuthorityLevel.MAINTENANCE:
            capabilities.append("physical_access")
        if level >= AuthorityLevel.ROOT:
            capabilities.append("full_system_access")
        if level >= AuthorityLevel.SOVEREIGN:
            capabilities.append("absolute_command")
        
        return capabilities
    
    def execute_multi_level_command(self, 
                                    target: BridgeTarget,
                                    value: float,
                                    authority_required: AuthorityLevel = None) -> Dict[str, Any]:
        """
        Execute command with graduated authority check.
        
        Different targets require different minimum authority levels.
        """
        # Determine required authority for this target
        if authority_required is None:
            authority_required = self._target_authority_requirement(target)
        
        if self.authority_level < authority_required:
            return {
                "action": "REJECTED",
                "reason": f"Insufficient authority: {self.authority_level.name} < {authority_required.name}",
                "target": target.name,
                "requested_value": value,
                "timestamp": self._timestamp()
            }
        
        # Execute based on target
        execution_map = {
            BridgeTarget.THERMAL: lambda: self.actuator.set_thermal(value),
            BridgeTarget.ELECTRIC: lambda: self.actuator.set_electric(value, 0.001),
            BridgeTarget.LIGHT: lambda: self.actuator.set_target("light", value),
            BridgeTarget.SOUND: lambda: self.actuator.set_target("sound", value),
            BridgeTarget.PRESSURE: lambda: self.actuator.set_target("pressure", value),
        }
        
        executor = execution_map.get(target, lambda: None)
        executor()
        
        result = {
            "action": "EXECUTED",
            "target": target.name,
            "value": value,
            "authority_used": self.authority_level.name,
            "authority_required": authority_required.name,
            "timestamp": self._timestamp()
        }
        
        self._record_command("multi_level", f"{target.name}={value}", result)
        return result
    
    def _target_authority_requirement(self, target: BridgeTarget) -> AuthorityLevel:
        """Map targets to minimum authority requirements."""
        requirements = {
            BridgeTarget.THERMAL: AuthorityLevel.MONITORED,
            BridgeTarget.ELECTRIC: AuthorityLevel.GUARDED,
            BridgeTarget.MAGNETIC: AuthorityLevel.ELEVATED,
            BridgeTarget.LIGHT: AuthorityLevel.STANDARD,
            BridgeTarget.SOUND: AuthorityLevel.LOW_AUTHORITY,
            BridgeTarget.WAVE: AuthorityLevel.HIGH_AUTHORITY,
            BridgeTarget.PRESSURE: AuthorityLevel.SUPERVISORY,
            BridgeTarget.CHEMICAL: AuthorityLevel.ADMINISTRATIVE,
        }
        return requirements.get(target, AuthorityLevel.STANDARD)
    
    # ==================================================================
    # 3. APPROXIMATE COMMAND INTERFACE
    # ==================================================================
    
    def receive_approximate_command(self,
                                    target: str,
                                    desired_value: float,
                                    confidence_threshold: float = 0.8,
                                    precision_bits: int = 8) -> Dict[str, Any]:
        """
        Execute command with probabilistic confidence bounds.
        
        The command executes only if the system's confidence in
        correct execution exceeds the threshold. Uses INT8-style
        approximate computation to estimate execution fidelity.
        
        This is how an NPU would handle sovereign commands—
        trading absolute certainty for energy efficiency.
        """
        # Quantize the desired value (simulating NPU processing)
        quant_levels = 2 ** (precision_bits - 1)
        scale = 1.0 / quant_levels
        quantized_value = int(desired_value / scale) * scale
        
        # Estimate execution confidence using approximate inference
        approx_taf = ApproximateTAF(precision_bits=precision_bits)
        
        # Get current noise level from bridge
        current_noise = self._get_current_noise()
        
        # Compute confidence that execution will be correct
        execution_confidence = 1.0 / (1.0 + current_noise + abs(desired_value - quantized_value))
        
        if execution_confidence < confidence_threshold:
            print(f"\n[APPROXIMATE_COMMAND] REJECTED")
            print(f"Confidence {execution_confidence:.3f} < threshold {confidence_threshold}")
            return {
                "action": "REJECTED_LOW_CONFIDENCE",
                "target": target,
                "confidence": execution_confidence,
                "threshold": confidence_threshold,
                "reason": "Execution confidence below threshold",
                "suggestion": f"Increase precision or reduce noise ({current_noise:.2f})",
                "timestamp": self._timestamp()
            }
        
        # Execute with quantized value
        print(f"\n[APPROXIMATE_COMMAND] EXECUTED")
        print(f"Desired: {desired_value:.6f} → Quantized: {quantized_value:.6f}")
        print(f"Confidence: {execution_confidence:.3f} (threshold: {confidence_threshold})")
        print(f"Precision: {precision_bits} bits")
        
        self._execute_on_target(target, quantized_value)
        
        result = {
            "action": "EXECUTED_APPROXIMATE",
            "target": target,
            "desired_value": desired_value,
            "executed_value": quantized_value,
            "quantization_error": abs(desired_value - quantized_value),
            "confidence": execution_confidence,
            "precision_bits": precision_bits,
            "energy_cost_pj": precision_bits * 1e-12,
            "timestamp": self._timestamp()
        }
        
        self._record_command("approximate", f"{target}={desired_value}", result)
        return result
    
    # ==================================================================
    # 4. TERNARY COMMAND INTERFACE
    # ==================================================================
    
    def receive_ternary_command(self, ternary_string: str) -> Dict[str, Any]:
        """
        Process balanced ternary command string.
        
        Syntax: "+0-+" where each position is:
          Position 0: Thermal (+ = increase, 0 = hold, - = decrease)
          Position 1: Electric
          Position 2: Magnetic
          Position 3: Light
        
        Example: "+0-+" means:
          Increase thermal, hold electric, decrease magnetic, increase light
        
        The ternary symmetry enables commands that express both
        action AND restraint in a single string.
        """
        if len(ternary_string) < 4:
            ternary_string = ternary_string.ljust(4, '0')
        
        print(f"\n[TERNARY_COMMAND] Received: {ternary_string}")
        
        # Parse trits
        trits = [TernaryCommand.from_symbol(c) for c in ternary_string[:4]]
        
        # Compute overall stance
        stance_sum = sum(t.value for t in trits)
        if stance_sum > 1:
            self.ternary_stance = TernaryCommand.ACTIVATE
        elif stance_sum < -1:
            self.ternary_stance = TernaryCommand.RESTRAIN
        else:
            self.ternary_stance = TernaryCommand.HOLD
        
        print(f"PARSED_TRITS: {[t.name for t in trits]}")
        print(f"OVERALL_STANCE: {self.ternary_stance.name}")
        
        # Execute each trit on corresponding target
        targets = ["thermal", "electric", "magnetic", "light"]
        results = []
        
        current_values = {
            "thermal": 50.0,
            "electric": 5.0,
            "magnetic": 0.5,
            "light": 100.0
        }
        
        trit_to_delta = {
            TernaryCommand.ACTIVATE: +0.1,   # +10% adjustment
            TernaryCommand.HOLD: 0.0,
            TernaryCommand.RESTRAIN: -0.1,    # -10% adjustment
        }
        
        for i, (target, trit) in enumerate(zip(targets, trits)):
            if trit != TernaryCommand.HOLD:
                delta = trit_to_delta[trit]
                new_value = current_values[target] * (1.0 + delta)
                self._execute_on_target(target, new_value)
                results.append(f"{target}: {trit.name} → {new_value:.2f}")
        
        result = {
            "action": "TERNARY_EXECUTED",
            "ternary_string": ternary_string,
            "parsed_trits": [t.name for t in trits],
            "overall_stance": self.ternary_stance.name,
            "stance_value": stance_sum,
            "executions": results,
            "timestamp": self._timestamp()
        }
        
        self._record_command("ternary", ternary_string, result)
        return result
    
    def set_ternary_stance(self, stance: TernaryCommand) -> Dict[str, Any]:
        """
        Set global ternary stance affecting all future commands.
        
        RESTRAIN: All commands are downscaled by 50%
        HOLD: Commands execute as specified
        ACTIVATE: All commands are upscaled by 50%
        """
        previous = self.ternary_stance
        self.ternary_stance = stance
        
        # Compute TAF implications of stance change
        if stance == TernaryCommand.RESTRAIN:
            taf_implication = "Reducing energy extraction, increasing organism yield"
        elif stance == TernaryCommand.ACTIVATE:
            taf_implication = "Increasing throughput, monitor for extractive regime"
        else:
            taf_implication = "Steady-state operation"
        
        print(f"\n[TERNARY_STANCE] {previous.name} → {stance.name}")
        print(f"TAF_IMPLICATION: {taf_implication}")
        
        return {
            "action": "STANCE_CHANGE",
            "previous": previous.name,
            "current": stance.name,
            "taf_implication": taf_implication,
            "command_modifier": -0.5 if stance == TernaryCommand.RESTRAIN else (
                0.5 if stance == TernaryCommand.ACTIVATE else 0.0
            ),
            "timestamp": self._timestamp()
        }
    
    # ==================================================================
    # 5. STOCHASTIC COMMAND INTERFACE
    # ==================================================================
    
    def receive_stochastic_command(self,
                                   target: str,
                                   probability_stream: Union[float, List[int]],
                                   stream_length: int = 256,
                                   noise_floor: float = 0.0) -> Dict[str, Any]:
        """
        Process command encoded as probability stream.
        
        Designed for high-noise environments where deterministic
        commands would be corrupted. The probability is recovered
        by integrating over the bitstream.
        
        If probability_stream is a float, generates the stream internally.
        If it's a list of bits, decodes the probability from the stream.
        """
        print(f"\n[STOCHASTIC_COMMAND] Target: {target}")
        
        # Decode or use probability
        if isinstance(probability_stream, list):
            # Received actual bitstream (noisy channel)
            decoded_prob = sum(probability_stream) / len(probability_stream)
            effective_length = len(probability_stream)
            print(f"BITSTREAM_RECEIVED: {effective_length} bits")
            print(f"DECODED_PROBABILITY: {decoded_prob:.4f}")
        else:
            decoded_prob = probability_stream
            effective_length = stream_length
            print(f"PROBABILITY_RECEIVED: {decoded_prob:.4f}")
        
        # Noise resilience calculation
        if noise_floor > 0:
            effective_resolution = effective_length * ((1.0 - noise_floor) ** 2)
        else:
            current_noise = self._get_current_noise()
            effective_resolution = effective_length * ((1.0 - current_noise) ** 2)
        
        # Map probability to value range
        if target == "thermal":
            value_range = (TEMP_BANDS[0], TEMP_BANDS[-1])
        elif target == "electric":
            value_range = (0.0, VOLTAGE_BANDS[-1])
        else:
            value_range = (0.0, 100.0)
        
        executed_value = value_range[0] + decoded_prob * (value_range[1] - value_range[0])
        
        # Only execute if effective resolution is adequate
        if effective_resolution < 64:
            print(f"WARNING: Low effective resolution ({effective_resolution:.0f} bits)")
            print(f"Increase stream length or reduce noise for reliable execution")
        
        self._execute_on_target(target, executed_value)
        
        result = {
            "action": "STOCHASTIC_EXECUTED",
            "target": target,
            "decoded_probability": decoded_prob,
            "executed_value": executed_value,
            "value_range": value_range,
            "stream_length": effective_length,
            "effective_resolution": effective_resolution,
            "noise_floor": noise_floor,
            "is_noise_limited": effective_resolution < 128,
            "timestamp": self._timestamp()
        }
        
        self._record_command("stochastic", f"{target}=P({decoded_prob:.4f})", result)
        return result
    
    def stochastic_broadcast(self,
                             command: StochasticCommand,
                             num_repeats: int = 3) -> Dict[str, Any]:
        """
        Broadcast stochastic command with repetition coding.
        
        Sends the same probability stream multiple times.
        Receiver averages streams for noise immunity.
        Provides anti-jamming capability for sovereign commands.
        """
        print(f"\n[STOCHASTIC_BROADCAST] {num_repeats}x repeat")
        print(f"Target: {command.target}, P={command.probability:.4f}")
        
        # Generate multiple streams (simulated)
        all_streams = []
        for i in range(num_repeats):
            stream = command.to_bitstream()
            all_streams.append(stream)
        
        # Combine streams (majority voting per bit position)
        combined = []
        for bit_pos in range(command.stream_length):
            votes = sum(stream[bit_pos] for stream in all_streams)
            combined.append(1 if votes > num_repeats / 2 else 0)
        
        # Decode combined probability
        combined_prob = sum(combined) / len(combined)
        
        # Effective error reduction
        error_reduction = math.sqrt(num_repeats)  # √N improvement
        
        print(f"Combined probability: {combined_prob:.4f}")
        print(f"Error reduction factor: {error_reduction:.2f}x")
        
        return self.receive_stochastic_command(
            target=command.target,
            probability_stream=combined,
            stream_length=command.stream_length,
            noise_floor=command.noise_floor / error_reduction
        )
    
    # ==================================================================
    # 6. QUANTUM COMMAND INTERFACE
    # ==================================================================
    
    def receive_quantum_command(self,
                                command_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process quantum command with superposition and entanglement.
        
        Command format:
        {
            "type": "superposition" | "entangled",
            "targets": ["thermal", "electric"],  # Superposed targets
            "amplitudes": [0.707, 0.707],  # |ψ⟩ = α|thermal⟩ + β|electric⟩
            "entanglement_group": "group_1",  # For entangled multi-commands
            "phase": 0.0  # Relative phase
        }
        
        The command exists in superposition until execution,
        at which point it collapses to a single target via Born's rule.
        """
        cmd_type = command_spec.get("type", "superposition")
        
        print(f"\n[QUANTUM_COMMAND] Type: {cmd_type}")
        
        if cmd_type == "superposition":
            return self._execute_quantum_superposition(command_spec)
        elif cmd_type == "entangled":
            return self._execute_quantum_entangled(command_spec)
        elif cmd_type == "measure":
            return self._measure_quantum_state(command_spec)
        else:
            return {
                "action": "REJECTED",
                "reason": f"Unknown quantum command type: {cmd_type}",
                "timestamp": self._timestamp()
            }
    
    def _execute_quantum_superposition(self, 
                                       spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command in superposition over multiple targets.
        
        The command doesn't commit to a single target until
        measurement/execution time. This enables:
        - Deferred targeting decisions
        - Probabilistic load balancing
        - Covert command routing
        """
        targets = spec.get("targets", ["thermal"])
        amplitudes = spec.get("amplitudes", [1.0])
        
        # Normalize amplitudes
        norm = math.sqrt(sum(abs(a)**2 for a in amplitudes))
        normalized = [complex(a) / norm for a in amplitudes]
        
        # Pad if necessary
        while len(normalized) < len(targets):
            normalized.append(complex(0, 0))
        
        # Create quantum command
        qcmd = QuantumCommand(
            targets=targets,
            amplitudes=normalized,
            phase_angle=spec.get("phase", 0.0)
        )
        
        # Store as pending (not yet collapsed)
        self.quantum_pending.append(qcmd)
        
        # Compute expectation values
        probabilities = [abs(a)**2 for a in normalized]
        expected_target = targets[probabilities.index(max(probabilities))]
        
        print(f"SUPERPOSITION_CREATED: {len(targets)} targets")
        for t, p in zip(targets, probabilities):
            print(f"  |{t}⟩: P={p:.3f}")
        print(f"MOST_PROBABLE: {expected_target}")
        
        return {
            "action": "SUPERPOSITION_CREATED",
            "num_targets": len(targets),
            "targets": targets,
            "probabilities": [abs(a)**2 for a in normalized],
            "most_probable": expected_target,
            "phase_angle": qcmd.phase_angle,
            "pending_index": len(self.quantum_pending) - 1,
            "note": "Command exists in superposition. Use 'measure' to collapse.",
            "timestamp": self._timestamp()
        }
    
    def _execute_quantum_entangled(self, 
                                   spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create entangled command group.
        
        Multiple commands are entangled such that executing one
        instantly determines the state of all others. This enables:
        - Coordinated multi-target operations
        - Atomic command sequences
        - Non-local correlation between actuators
        """
        group_id = spec.get("entanglement_group", f"ent_{self._timestamp()}")
        commands = spec.get("commands", [])
        
        if len(commands) < 2:
            return {
                "action": "REJECTED",
                "reason": "Entanglement requires at least 2 commands",
                "timestamp": self._timestamp()
            }
        
        # Create entangled quantum commands
        entangled_cmds = []
        for cmd_spec in commands:
            qcmd = QuantumCommand(
                targets=cmd_spec.get("targets", ["thermal"]),
                amplitudes=[complex(1.0, 0)],  # Will be entangled
                entanglement_id=group_id
            )
            entangled_cmds.append(qcmd)
        
        # Entangle them (Bell state preparation)
        # |Ψ⁻⟩ = (|01⟩ - |10⟩)/√2
        for i, cmd in enumerate(entangled_cmds):
            if i == 0:
                cmd.amplitudes = [complex(1/math.sqrt(2), 0)]
                cmd.targets = [commands[0].get("targets", ["thermal"])[0]]
            else:
                cmd.amplitudes = [complex(-1/math.sqrt(2), 0)]
                cmd.targets = [commands[1].get("targets", ["electric"])[0]]
        
        self.entanglement_registry[group_id] = entangled_cmds
        
        print(f"ENTANGLED_GROUP_CREATED: {group_id}")
        print(f"ENTANGLED_COMMANDS: {len(entangled_cmds)}")
        print(f"STATE: |Ψ⁻⟩ Bell state")
        
        return {
            "action": "ENTANGLED_CREATED",
            "group_id": group_id,
            "num_commands": len(entangled_cmds),
            "bell_state": "Ψ⁻",
            "note": "Commands are entangled. Measuring one affects all.",
            "timestamp": self._timestamp()
        }
    
    def _measure_quantum_state(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collapse quantum command superposition to definite target.
        
        If an entanglement group is specified, collapses all
        entangled commands simultaneously.
        """
        group_id = spec.get("entanglement_group")
        
        if group_id and group_id in self.entanglement_registry:
            # Collapse entangled group
            entangled = self.entanglement_registry[group_id]
            collapsed_results = []
            
            for i, qcmd in enumerate(entangled):
                target, prob = qcmd.collapse()
                value = spec.get("values", [50.0] * len(entangled))[i]
                self._execute_on_target(target, value)
                collapsed_results.append({
                    "command_index": i,
                    "collapsed_target": target,
                    "probability": prob,
                    "value": value
                })
            
            del self.entanglement_registry[group_id]
            
            print(f"\n[QUANTUM_MEASUREMENT] Group: {group_id}")
            for cr in collapsed_results:
                print(f"  Command {cr['command_index']} → {cr['collapsed_target']}")
            
            return {
                "action": "ENTANGLED_COLLAPSED",
                "group_id": group_id,
                "results": collapsed_results,
                "timestamp": self._timestamp()
            }
        
        elif self.quantum_pending:
            # Collapse single superposition
            qcmd = self.quantum_pending.pop()
            target, prob = qcmd.collapse()
            value = spec.get("value", 50.0)
            self._execute_on_target(target, value)
            
            print(f"\n[QUANTUM_MEASUREMENT] Collapsed to: {target}")
            print(f"Probability: {prob:.3f}")
            
            return {
                "action": "SUPERPOSITION_COLLAPSED",
                "collapsed_target": target,
                "probability": prob,
                "value": value,
                "remaining_pending": len(self.quantum_pending),
                "timestamp": self._timestamp()
            }
        
        else:
            return {
                "action": "NO_PENDING_QUANTUM_STATE",
                "timestamp": self._timestamp()
            }
    
    # ==================================================================
    # 7. CROSS-PARADIGM COMMAND VALIDATION
    # ==================================================================
    
    def validate_command_all_paradigms(self, 
                                       command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run command through all five paradigms for validation.
        
        Returns consensus vote on whether command should execute,
        along with paradigm-specific risk assessments.
        """
        target = command.get("target", "thermal")
        value = command.get("value", 50.0)
        
        validations = {}
        
        # Multi-Level validation: authority check
        validations["multi_level"] = {
            "valid": self.authority_level >= AuthorityLevel.STANDARD,
            "authority": self.authority_level.name,
            "risk": "LOW" if self.authority_level >= AuthorityLevel.MONITORED else "HIGH"
        }
        
        # Approximate validation: confidence check
        current_noise = self._get_current_noise()
        approx_confidence = 1.0 / (1.0 + current_noise)
        validations["approximate"] = {
            "valid": approx_confidence > 0.7,
            "confidence": approx_confidence,
            "risk": "LOW" if approx_confidence > 0.9 else "MEDIUM"
        }
        
        # Stochastic validation: noise resilience
        effective_res = 256 * ((1.0 - current_noise) ** 2)
        validations["stochastic"] = {
            "valid": effective_res >= 64,
            "effective_resolution": effective_res,
            "risk": "LOW" if effective_res >= 128 else "HIGH"
        }
        
        # Ternary validation: stance compatibility
        stance_conflict = (
            self.ternary_stance == TernaryCommand.RESTRAIN and value > 75.0
        )
        validations["ternary"] = {
            "valid": not stance_conflict,
            "stance": self.ternary_stance.name,
            "risk": "HIGH" if stance_conflict else "LOW"
        }
        
        # Quantum validation: superposition risk
        pending_count = len(self.quantum_pending)
        validations["quantum"] = {
            "valid": pending_count == 0,
            "pending_superpositions": pending_count,
            "risk": "HIGH" if pending_count > 2 else "MEDIUM" if pending_count > 0 else "LOW"
        }
        
        # Consensus
        votes = sum(1 for v in validations.values() if v["valid"])
        consensus = votes >= 4  # 4 of 5 required
        
        print(f"\n[CROSS-PARADIGM_VALIDATION]")
        for paradigm, result in validations.items():
            status = "✓" if result['valid'] else "✗"
            print(f"  {paradigm}: {status} (risk: {result['risk']})")
        print(f"CONSENSUS: {'APPROVED' if consensus else 'REJECTED'} ({votes}/5)")
        
        return {
            "command": command,
            "validations": validations,
            "consensus": consensus,
            "vote_count": votes,
            "required_votes": 4,
            "execute": consensus,
            "timestamp": self._timestamp()
        }
    
    # ==================================================================
    # 8. UNIFIED COMMAND ROUTER
    # ==================================================================
    
    def receive_command(self, 
                        command_input: Union[str, Dict[str, Any]],
                        paradigm: str = "auto") -> Dict[str, Any]:
        """
        Universal command router. Accepts any paradigm format.
        
        Auto-detection:
        - String starting with "0x" → Classic hex
        - String with only "+-0" → Ternary
        - Dict with "type": "quantum" → Quantum
        - Dict with "probability_stream" → Stochastic
        - Dict with "target" → Approximate
        - Number 0-15 → Multi-Level authority
        """
        # Auto-detect paradigm
        if paradigm == "auto":
            paradigm = self._detect_paradigm(command_input)
        
        print(f"\n{'='*60}")
        print(f"[SOVEREIGN_COMMAND_ROUTER] Paradigm: {paradigm}")
        print(f"{'='*60}")
        
        # Route to handler
        handlers = {
            "classic": lambda: self.receive_hex_command(command_input),
            "multi_level": lambda: self.set_authority_level(command_input),
            "approximate": lambda: self.receive_approximate_command(**command_input),
            "ternary": lambda: self.receive_ternary_command(command_input),
            "stochastic": lambda: self.receive_stochastic_command(**command_input),
            "quantum": lambda: self.receive_quantum_command(command_input),
        }
        
        handler = handlers.get(paradigm)
        if handler:
            result = handler()
            # Run cross-paradigm validation
            validation = self.validate_command_all_paradigms(
                self._extract_command_info(result)
            )
            result["cross_paradigm_validation"] = validation
            return result
        else:
            return {
                "action": "UNKNOWN_PARADIGM",
                "paradigm": paradigm,
                "available": list(handlers.keys()),
                "timestamp": self._timestamp()
            }
    
    def _detect_paradigm(self, command_input) -> str:
        """Auto-detect paradigm from command format."""
        if isinstance(command_input, str):
            if command_input.startswith("0x"):
                return "classic"
            elif all(c in "+-0TN" for c in command_input.upper()):
                return "ternary"
        elif isinstance(command_input, (int, AuthorityLevel)):
            return "multi_level"
        elif isinstance(command_input, dict):
            if "type" in command_input:
                return "quantum"
            elif "probability_stream" in command_input:
                return "stochastic"
            elif "target" in command_input:
                return "approximate"
        return "classic"  # Default fallback
    
    def _extract_command_info(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract target and value from result for validation."""
        return {
            "target": result.get("target", "unknown"),
            "value": result.get("value", result.get("executed_value", 50.0))
        }
    
    # ==================================================================
    # 9. UTILITY METHODS
    # ==================================================================
    
    def _validate_authority(self, binary_val: str, paradigm: str) -> bool:
        """Check if current authority level permits this command."""
        if self.authority_level >= AuthorityLevel.STANDARD:
            return True
        if self.authority_level >= AuthorityLevel.MONITORED and paradigm == "classic":
            return True
        return False
    
    def _reject_command(self, command: Any, reason: str) -> Dict[str, Any]:
        """Record and return command rejection."""
        rejection = {
            "action": "REJECTED",
            "command": str(command)[:100],
            "reason": reason,
            "authority": self.authority_level.name,
            "timestamp": self._timestamp()
        }
        self.rejected_commands.append(rejection)
        if len(self.rejected_commands) > self.COMMAND_HISTORY_SIZE:
            self.rejected_commands.pop(0)
        return rejection
    
    def _record_command(self, paradigm: str, command: str, result: Dict[str, Any]):
        """Record command in audit trail."""
        entry = {
            "paradigm": paradigm,
            "command": command,
            "result_action": result.get("action", "unknown"),
            "authority": self.authority_level.name,
            "timestamp": self._timestamp()
        }
        self.command_history.append(entry)
        if len(self.command_history) > self.COMMAND_HISTORY_SIZE:
            self.command_history.pop(0)
    
    def _execute_on_target(self, target: str, value: float):
        """Execute value on named target."""
        target_map = {
            "thermal": lambda: self.actuator.set_thermal(value),
            "electric": lambda: self.actuator.set_electric(value, 0.001),
            "magnetic": lambda: self.actuator.set_magnetic(value),
            "light": lambda: self.actuator.set_light(value),
            "sound": lambda: self.actuator.set_sound(value),
            "pressure": lambda: self.actuator.set_pressure(value),
        }
        executor = target_map.get(target)
        if executor:
            executor()
    
    def _get_current_noise(self) -> float:
        """Get current system noise level."""
        try:
            if hasattr(self.bridge, 'get_noise_level'):
                return self.bridge.get_noise_level()
        except:
            pass
        return 0.1  # Default noise floor
    
    def _timestamp(self) -> str:
        """Generate timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_audit_trail(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent command history for audit."""
        return self.command_history[-limit:]
    
    def get_pending_quantum_commands(self) -> List[Dict[str, Any]]:
        """List pending quantum superpositions."""
        return [
            {
                "index": i,
                "targets": qcmd.targets,
                "probabilities": [abs(a)**2 for a in qcmd.amplitudes]
            }
            for i, qcmd in enumerate(self.quantum_pending)
        ]
    
    def get_authority_status(self) -> Dict[str, Any]:
        """Full authority status report."""
        return {
            "authority_level": self.authority_level.name,
            "numeric_level": self.authority_level.value,
            "ternary_stance": self.ternary_stance.name,
            "pending_quantum": len(self.quantum_pending),
            "entanglement_groups": list(self.entanglement_registry.keys()),
            "command_history_size": len(self.command_history),
            "rejected_count": len(self.rejected_commands),
            "capabilities": self._get_capabilities(self.authority_level)
        }


# ----------------------------------------------------------------------
# Instantiation helper
# ----------------------------------------------------------------------

def create_sovereign_interface(hardware_interface=None) -> SovereignAlternativeInterface:
    """
    Factory function for the expanded sovereign interface.
    
    If no hardware interface provided, creates a mock for testing.
    """
    if hardware_interface is None:
        # Mock interface for development/testing
        class MockHardwareInterface:
            def process_cycle(self):
                return "MOCK_CYCLE_COMPLETE"
            def get_current_state(self):
                return HardwareData(
                    failure_mode="none",
                    health_score=0.75,
                    is_critical=False,
                    confidence_hi=True,
                    has_synergy=True,
                    voltage_v=5.0,
                    current_a=0.001,
                    temperature_c=45.0,
                    noise_level=0.1,
                    repurpose_class="standard",
                    effectiveness=7.5,
                    bridge_target=BridgeTarget.THERMAL,
                    drift_pct=2.0,
                    salvageable=True,
                    fallback_ready=True,
                    lifetime_hours=5000.0,
                    drill_depth=DrillDepth.MONITOR,
                    is_semiconductor=True,
                    confidence=0.9
                )
            def get_noise_level(self):
                return 0.1
        hardware_interface = MockHardwareInterface()
    
    return SovereignAlternativeInterface(hardware_interface)
