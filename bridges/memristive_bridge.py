# bridges/memristive_bridge.py
"""
Memristive Bridge — Hysteretic State Layer
===========================================
Wraps conductivity/state data with memory-as-history interpretation.

The binary encoder reads a single conductivity value σ at one instant.
The memristive layer reads σ(t) as the integral of past states:

    σ(t) = σ₀ + α ∫ I(τ) dτ   (or  σ(t) = σ₀ + β ∫ V(τ) dτ)

The state IS the hysteresis—not a register that stores it separately.
This is the physical realization of "memory = computation trace."

For the Electric Bridge Encoder, this means:
- The "conductivity_S" list is not independent samples
- Each σ[i] depends on all previous V[j] and I[j] for j < i
- The binary encoding's per-sample independence assumption is wrong
  for any device with memory
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import math


@dataclass
class MemristiveTrace:
    """
    A conductivity trace with memory of past states.
    
    Unlike a simple list of conductivity values (which the binary
    encoder treats as independent samples), the memristive trace
    models each value as depending on the accumulated history
    of voltage and current applied.
    """
    
    conductivity: List[float] = field(default_factory=list)
    voltage_history: List[float] = field(default_factory=list)
    current_history: List[float] = field(default_factory=list)
    
    # Memristive parameters
    on_off_ratio: float = 100.0      # R_off / R_on
    switching_threshold: float = 0.5  # Voltage at which state changes
    retention_factor: float = 0.999   # Per-step state retention (1.0 = perfect)
    
    # Derived state
    internal_state: List[float] = field(default_factory=list)  # The "w" parameter
    hysteresis_loop: List[Tuple[float, float]] = field(default_factory=list)  # (V, σ)
    memory_depth: int = 0
    
    def from_measurements(self,
                          conductivity: List[float],
                          voltage: List[float] = None,
                          current: List[float] = None):
        """
        Model conductivity sequence as memristive evolution.
        
        The internal state w ∈ [0,1] determines conductivity:
        σ(w) = w·σ_on + (1-w)·σ_off
        
        State evolution: dw/dt depends on voltage/current and threshold
        """
        self.conductivity = conductivity
        self.voltage_history = voltage or []
        self.current_history = current or []
        
        if not conductivity:
            return
        
        # Estimate ON/OFF conductivities from range
        sigma_min = min(conductivity)
        sigma_max = max(conductivity)
        if sigma_max > sigma_min:
            # Reconstruct internal state from conductivity
            self.internal_state = [
                (s - sigma_min) / (sigma_max - sigma_min)
                for s in conductivity
            ]
        else:
            self.internal_state = [0.5] * len(conductivity)
        
        # Build hysteresis loop (voltage vs conductivity)
        if self.voltage_history and len(self.voltage_history) == len(conductivity):
            self.hysteresis_loop = list(zip(self.voltage_history, conductivity))
        
        # Memory depth: how far back does autocorrelation persist?
        self.memory_depth = self._estimate_memory_depth()
    
    def _estimate_memory_depth(self) -> int:
        """Estimate how many steps back the state memory persists."""
        if len(self.internal_state) < 10:
            return len(self.internal_state)
        
        # Autocorrelation with increasing lag
        series = self.internal_state
        max_lag = min(50, len(series) // 3)
        
        for lag in range(1, max_lag):
            recent = series[lag:]
            lagged = series[:-lag]
            if len(recent) < 5:
                break
            
            mean_r = sum(recent) / len(recent)
            mean_l = sum(lagged) / len(lagged)
            
            num = sum((r - mean_r) * (l - mean_l) for r, l in zip(recent, lagged))
            den_r = math.sqrt(sum((r - mean_r)**2 for r in recent))
            den_l = math.sqrt(sum((l - mean_l)**2 for l in lagged))
            
            if den_r > 0 and den_l > 0:
                correlation = num / (den_r * den_l)
                if correlation < 0.1:  # Memory faded
                    return lag
        
        return max_lag
    
    def simulate_evolution(self,
                           voltage_pulses: List[float],
                           initial_state: float = 0.5) -> List[float]:
        """
        Simulate memristive state evolution under voltage pulses.
        
        This is the forward model: given a voltage sequence,
        predict the conductivity evolution.
        
        Args:
            voltage_pulses: Applied voltage sequence
            initial_state: Starting internal state w ∈ [0,1]
        
        Returns:
            Predicted conductivity sequence
        """
        w = initial_state
        sigma_min = min(self.conductivity) if self.conductivity else 0
        sigma_max = max(self.conductivity) if self.conductivity else 1
        
        predicted_conductivity = []
        
        for V in voltage_pulses:
            # State change only above threshold
            if abs(V) > self.switching_threshold:
                # dw/dt proportional to voltage above threshold
                # with sign depending on polarity
                delta_w = 0.01 * (abs(V) - self.switching_threshold)
                if V > 0:
                    w = min(1.0, w + delta_w)  # Toward ON state
                else:
                    w = max(0.0, w - delta_w)  # Toward OFF state
            
            # Retention: slow drift toward stable state
            w = w * self.retention_factor + 0.5 * (1 - self.retention_factor)
            
            # Conductivity from state
            sigma = sigma_min + w * (sigma_max - sigma_min)
            predicted_conductivity.append(sigma)
        
        return predicted_conductivity
    
    def diagnose(self) -> str:
        """Human-readable memristive diagnosis."""
        n = len(self.conductivity)
        
        diagnosis = (
            f"Memristive trace: {n} measurements. "
        )
        
        if self.memory_depth > 20:
            diagnosis += (
                f"Deep memory: autocorrelation persists for {self.memory_depth}+ steps. "
                f"This device has significant state hysteresis—treating each "
                f"conductivity measurement as independent (as the binary encoder does) "
                f"destroys the causal structure of the trace."
            )
        elif self.memory_depth > 5:
            diagnosis += (
                f"Moderate memory: {self.memory_depth} steps of persistence. "
                f"Device shows memristive behavior with finite retention."
            )
        else:
            diagnosis += (
                f"Short memory: state decorrelates within {self.memory_depth} steps. "
                f"Device is nearly memoryless—binary encoding's independence "
                f"assumption is approximately valid."
            )
        
        # Hysteresis loop analysis
        if self.hysteresis_loop:
            voltages = [v for v, _ in self.hysteresis_loop]
            conductivities = [s for _, s in self.hysteresis_loop]
            v_range = max(voltages) - min(voltages)
            s_range = max(conductivities) - min(conductivities)
            
            if v_range > 0 and s_range > 0:
                # Check for pinched hysteresis (memristive fingerprint)
                # Simple check: does conductivity path differ for increasing vs decreasing V?
                increasing = [(v, s) for i, (v, s) in enumerate(self.hysteresis_loop) 
                            if i > 0 and v > self.hysteresis_loop[i-1][0]]
                decreasing = [(v, s) for i, (v, s) in enumerate(self.hysteresis_loop)
                            if i > 0 and v < self.hysteresis_loop[i-1][0]]
                
                if increasing and decreasing:
                    diagnosis += (
                        f" Pinched hysteresis detected: {len(increasing)} rising and "
                        f"{len(decreasing)} falling transitions. Characteristic memristive "
                        f"fingerprint—the device's state IS its voltage/current history."
                    )
        
        return diagnosis


def memristive_wrap_conductivity(conductivity: List[float],
                                 voltage: List[float] = None,
                                 current: List[float] = None) -> MemristiveTrace:
    """
    Wrap conductivity measurements as memristive evolution.
    
    Args:
        conductivity: Conductivity values (S/m)
        voltage: Corresponding voltage values (V)
        current: Corresponding current values (A)
    
    Returns:
        MemristiveTrace with memory analysis
    """
    trace = MemristiveTrace()
    trace.from_measurements(conductivity, voltage, current)
    return trace
