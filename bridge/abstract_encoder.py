# Abstract base for all domain encoders in the Geometric-to-Binary Bridge
# Each encoder maps a geometric field into a binary signature (0/1)

from abc import ABC, abstractmethod
import hashlib

class BinaryBridgeEncoder(ABC):
    """Abstract base for all bridge encoders (magnetic, light, etc.)"""

    def __init__(self, modality):
        self.modality = modality
        self.input_geometry = None
        self.binary_output = None
        self.metadata = {}

    @abstractmethod
    def from_geometry(self, geometry_data):
        """Load and interpret geometric field or shape data."""
        pass

    @abstractmethod
    def to_binary(self):
        """Convert field/geometry data to binary bitstring."""
        pass

    def checksum(self, bitstring):
        """Generate BLAKE3-like checksum using SHA256 for now."""
        return hashlib.sha256(bitstring.encode("utf-8")).hexdigest()

    def report(self):
        return {
            "modality": self.modality,
            "bits": len(self.binary_output) if self.binary_output else 0,
            "checksum": self.checksum(self.binary_output or "")
        }
