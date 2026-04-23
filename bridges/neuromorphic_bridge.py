# bridges/neuromorphic_bridge.py
"""
Neuromorphic Bridge — Event-Driven Computation Layer
=====================================================
Wraps any time-series encoder (Sound, Electric) with spiking
neural network interpretation.

The binary encoder processes a list of samples as a static array.
The neuromorphic layer treats each sample as a spike event with:
- Spike time (index in the sequence)
- Spike amplitude (encoded value)
- Inter-spike interval (carries frequency information)

This recovers temporal structure that the binary encoding's
position-independent bit layout compresses away.

Key neuromorphic properties:
- Energy scales with spike rate, not sample count
- Temporal pattern IS the information (not just values)
- Threshold-crossing events carry more information than
  continuous amplitude samples
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import math


@dataclass
class SpikeEvent:
    """A single spike in a neuromorphic representation."""
    time_index: int
    amplitude: float
    inter_spike_interval: float = 0.0  # Time since previous spike
    channel: str = "default"


@dataclass 
class NeuromorphicEncoding:
    """
    Converts time-series encoder data into spike-based representation.
    
    The binary encoder says: "here are N samples, encode each independently."
    The neuromorphic layer says: "here are N events; their timing, rate,
    and pattern carry information that independent encoding destroys."
    """
    
    spike_trains: Dict[str, List[SpikeEvent]] = field(default_factory=dict)
    
    # Derived neuromorphic metrics
    mean_firing_rate: float = 0.0
    spike_timing_entropy: float = 0.0
    burst_count: int = 0
    synchrony_score: float = 0.0  # Cross-channel spike coincidence
    
    def from_samples(self, 
                     values: List[float],
                     times: List[float] = None,
                     threshold: float = None,
                     channel: str = "default") -> 'NeuromorphicEncoding':
        """
        Convert continuous samples to spike events.
        
        Two encoding modes:
        1. Rate coding: spike rate proportional to value
        2. Threshold crossing: spike on significant change
        
        Args:
            values: Sample amplitudes
            times: Sample times (or None for index-based timing)
            threshold: Value change that triggers a spike
            channel: Label for this spike train
        """
        if times is None:
            times = list(range(len(values)))
        
        spikes = []
        
        if threshold is not None:
            # Threshold-crossing encoding
            for i in range(1, len(values)):
                delta = values[i] - values[i-1]
                if abs(delta) >= threshold:
                    isi = times[i] - times[i-1] if i > 0 else 0
                    spikes.append(SpikeEvent(
                        time_index=i,
                        amplitude=delta,
                        inter_spike_interval=isi,
                        channel=channel
                    ))
        else:
            # Rate coding: probability of spike ∝ amplitude
            import random
            max_val = max(abs(v) for v in values) if values else 1.0
            for i, v in enumerate(values):
                prob = abs(v) / max_val if max_val > 0 else 0
                if random.random() < prob:
                    isi = times[i] - times[i-1] if i > 0 else 0
                    spikes.append(SpikeEvent(
                        time_index=i,
                        amplitude=v,
                        inter_spike_interval=isi,
                        channel=channel
                    ))
        
        self.spike_trains[channel] = spikes
        self._compute_metrics()
        return self
    
    def _compute_metrics(self):
        """Compute neuromorphic population metrics."""
        all_spikes = []
        for train in self.spike_trains.values():
            all_spikes.extend(train)
        
        if not all_spikes:
            return
        
        # Mean firing rate
        if all_spikes:
            time_span = max(s.time_index for s in all_spikes) - min(s.time_index for s in all_spikes) + 1
            self.mean_firing_rate = len(all_spikes) / time_span if time_span > 0 else 0
        
        # Inter-spike interval entropy (temporal pattern complexity)
        isis = [s.inter_spike_interval for s in all_spikes if s.inter_spike_interval > 0]
        if isis:
            # Histogram of ISIs
            max_isi = max(isis)
            if max_isi > 0:
                bins = 10
                hist = [0] * bins
                for isi in isis:
                    idx = min(bins - 1, int(isi / max_isi * bins))
                    hist[idx] += 1
                total = sum(hist)
                if total > 0:
                    probs = [h / total for h in hist if h > 0]
                    self.spike_timing_entropy = -sum(p * math.log2(p) for p in probs)
        
        # Burst detection: spikes with ISI < 20% of mean ISI
        if isis:
            mean_isi = sum(isis) / len(isis)
            burst_threshold = mean_isi * 0.2
            self.burst_count = sum(1 for isi in isis if isi < burst_threshold)
        
        # Cross-channel synchrony
        if len(self.spike_trains) > 1:
            # Simplified: spike coincidence within small time window
            trains = list(self.spike_trains.values())
            coincident = 0
            total_pairs = 0
            for i in range(len(trains)):
                for j in range(i+1, len(trains)):
                    times_i = {s.time_index for s in trains[i]}
                    times_j = {s.time_index for s in trains[j]}
                    window = max(2, (max(times_i | times_j | {0}) - min(times_i | times_j | {0})) // 100)
                    for ti in times_i:
                        for offset in range(-window, window+1):
                            if ti + offset in times_j:
                                coincident += 1
                                break
                    total_pairs += len(times_i)
            self.synchrony_score = coincident / total_pairs if total_pairs > 0 else 0
    
    def diagnose(self) -> str:
        """Human-readable neuromorphic diagnosis."""
        total_spikes = sum(len(t) for t in self.spike_trains.values())
        n_channels = len(self.spike_trains)
        
        diagnosis = (
            f"{total_spikes} spikes across {n_channels} channels. "
            f"Mean firing rate: {self.mean_firing_rate:.3f} spikes/sample. "
        )
        
        if self.spike_timing_entropy > 2.0:
            diagnosis += (
                f"High temporal entropy ({self.spike_timing_entropy:.2f} bits): "
                f"complex spike timing pattern. Rich temporal structure that "
                f"binary encoding would flatten into independent samples."
            )
        elif self.spike_timing_entropy > 1.0:
            diagnosis += (
                f"Moderate temporal entropy ({self.spike_timing_entropy:.2f} bits): "
                f"some temporal structure present."
            )
        else:
            diagnosis += (
                f"Low temporal entropy: regular or sparse spiking. "
                f"Temporal structure is minimal or highly regular."
            )
        
        if self.burst_count > total_spikes * 0.1:
            diagnosis += (
                f" Bursting detected ({self.burst_count} bursts): "
                f"rapid spike sequences indicate event-triggered activity—"
                f"characteristic of threshold-crossing physical phenomena."
            )
        
        if self.synchrony_score > 0.3:
            diagnosis += (
                f" High cross-channel synchrony ({self.synchrony_score:.2f}): "
                f"coordinated activity across channels suggests coupled dynamics."
            )
        
        return diagnosis


def neuromorphic_wrap_encoder(encoder_output: Dict[str, List[float]],
                              threshold: float = None) -> NeuromorphicEncoding:
    """
    Wrap any time-series encoder output into neuromorphic representation.
    
    Args:
        encoder_output: Dict mapping channel names to value lists
                        (e.g., {"current_A": [...], "voltage_V": [...]})
        threshold: Value change triggering a spike (None = rate coding)
    
    Returns:
        NeuromorphicEncoding with spike trains
    """
    encoding = NeuromorphicEncoding()
    for channel, values in encoder_output.items():
        if isinstance(values, list) and len(values) > 0:
            encoding.from_samples(values, threshold=threshold, channel=channel)
    return encoding
