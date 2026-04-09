"""
vortex_bridge.py
================
Bridge encoder: topological phase-field memory -> binary.

Connects VortexMemory (Silicon/topological_memory.py) to the
BinaryBridgeEncoder pipeline so vortex state can flow into the
SensorSuite, consciousness encoder, and field_adapter.

Bit layout per registered memory slot (4 bits):
    [side_bit  1b]   1 = positive core on right,  0 = on left
    [strength  3b Gray-coded]  max |winding| in slot, 8 bands [0..1]

Total output length = 4 * number_of_registered_bits

Plug into SensorSuite via memory_to_suite().

Usage
-----
    from Silicon.core.topological_memory import VortexMemory
    from bridges.vortex_bridge import VortexBridgeEncoder, memory_to_suite

    mem = VortexMemory(grid_size=64)
    mem.write(0, 1); mem.write(1, 0)

    enc = VortexBridgeEncoder()
    enc.from_geometry(mem)
    bits = enc.to_binary()          # e.g. "10011000"

    # Or integrate with sensor suite
    from bridges.sensor_suite import SensorSuite
    suite = SensorSuite()
    memory_to_suite(mem, suite)
"""

from __future__ import annotations
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits, bits_from_int

# Winding magnitude bands: 8 linear bands covering [0, 1]
_W_BANDS = [i / 8 for i in range(8)]   # [0.0, 0.125, 0.25, ..., 0.875]


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class VortexBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes topological memory state to binary.

    from_geometry() accepts either a VortexMemory instance or a dict:
        {
          "winding_field":  np.ndarray (N x N),
          "registry":       {bit_index: (row_pos, col_pos, row_neg, col_neg)},
        }

    Bit layout per slot:
        [side  1b]       1 = col_pos > col_neg (positive core on right)
        [strength 3b]    Gray-coded winding magnitude at positive core pixel
    """

    def __init__(self):
        super().__init__(modality="vortex_topological", bit_depth=4)
        self._winding_field = None
        self._registry      = None

    # ------------------------------------------------------------------
    # BinaryBridgeEncoder interface
    # ------------------------------------------------------------------

    def from_geometry(self, geometry_data) -> "VortexBridgeEncoder":
        """
        Load vortex state from a VortexMemory or a plain dict.

        Parameters
        ----------
        geometry_data : VortexMemory  or  dict with keys
                        "winding_field" (np.ndarray) and
                        "registry"      (dict of slot tuples)
        """
        # Accept VortexMemory directly
        if hasattr(geometry_data, "winding_snapshot") and \
           hasattr(geometry_data, "_registry"):
            self._winding_field = geometry_data.winding_snapshot()
            self._registry      = dict(geometry_data._registry)
        elif isinstance(geometry_data, dict):
            self._winding_field = np.asarray(geometry_data["winding_field"],
                                             dtype=float)
            self._registry      = dict(geometry_data["registry"])
        else:
            raise TypeError(
                "geometry_data must be a VortexMemory instance or a dict "
                "with 'winding_field' and 'registry' keys."
            )
        self.input_geometry = geometry_data
        self.metadata["n_bits_registered"] = len(self._registry)
        return self

    def to_binary(self) -> str:
        """
        Encode each registered memory slot as 4 bits.

        Returns a bitstring of length 4 * len(registry), or "" if empty.
        """
        if self._registry is None:
            raise RuntimeError("Call from_geometry() before to_binary().")

        w   = self._winding_field
        out = []

        for bit_idx in sorted(self._registry.keys()):
            row_pos, col_pos, row_neg, col_neg = self._registry[bit_idx]

            # --- side bit: 1 = positive core is to the right ---
            side = "1" if col_pos > col_neg else "0"

            # --- strength: |winding| at positive core, Gray-coded ---
            peak_w = abs(float(w[row_pos, col_pos])) if (
                0 <= row_pos < w.shape[0] and 0 <= col_pos < w.shape[1]
            ) else 0.0
            strength = gray_bits(min(peak_w, 1.0), _W_BANDS, n_bits=3)

            out.append(side + strength)

        self.binary_output = "".join(out)
        return self.binary_output

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @staticmethod
    def from_memory(memory) -> "VortexBridgeEncoder":
        """One-liner: wrap a live VortexMemory."""
        enc = VortexBridgeEncoder()
        enc.from_geometry(memory)
        return enc


# ---------------------------------------------------------------------------
# SensorSuite adapter
# ---------------------------------------------------------------------------

def memory_to_suite(memory, suite) -> None:
    """
    Map VortexMemory state to three SensorSuite channels.

    Channel mapping
    ---------------
    coherence            -- topological integrity: fraction of bits
                           whose positive core has |winding| > threshold
    vigilance            -- max |winding| across all registered cores,
                           normalised to [0, 1]
    situational_awareness -- memory utilisation: used / total capacity

    Parameters
    ----------
    memory : VortexMemory
    suite  : SensorSuite (from bridges/sensor_suite.py)
    """
    registry = memory._registry
    if not registry:
        return

    w         = memory.winding_snapshot()
    threshold = memory._WINDING_THRESHOLD

    peaks     = []
    n_intact  = 0

    for bit_idx, (rp, cp, rn, cn) in registry.items():
        wp = abs(float(w[rp, cp])) if (
            0 <= rp < w.shape[0] and 0 <= cp < w.shape[1]) else 0.0
        peaks.append(wp)
        if wp > threshold:
            n_intact += 1

    coherence   = n_intact / len(registry)          # [0, 1]
    vigilance   = float(max(peaks)) if peaks else 0.0  # already in [0, 1]
    cap         = memory.capacity()
    utilisation = cap["used"] / max(cap["total_slots"], 1)

    suite.update("coherence",             magnitude=coherence)
    suite.update("vigilance",             magnitude=vigilance)
    suite.update("situational_awareness", magnitude=utilisation)
