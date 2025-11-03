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

 Add 1 small concept: bit_depth + encoding_version

Why? Because as soon as we go beyond pure binary to 8-state symbols (or later 3D tensor encodings), the bridge needs awareness of how many bits are expected.

Here is a version that does not break your code, just adds metadata handling:

from abc import ABC, abstractmethod
import hashlib
import time

class BinaryBridgeEncoder(ABC):
    """
    Abstract base for all bridge encoders (magnetic, gravitational, spectrum, polyhedral, GEIS).
    Each encoder maps domain geometry/fields into a binary signature.
    """

    def __init__(self, modality, bit_depth=1, encoding_version="1.0"):
        """
        modality: e.g., "magnetic", "gravitational", "spectrum", "polyhedral", "geis"
        bit_depth: number of bits per symbol (1 for binary, 3 for GEIS, etc.)
        encoding_version: version tag for evolution tracking
        """
        self.modality = modality
        self.bit_depth = bit_depth
        self.encoding_version = encoding_version
        self.input_geometry = None
        self.binary_output = None
        self.metadata = {
            "created": time.time(),
            "encoding_version": encoding_version,
            "bit_depth": bit_depth
        }

    @abstractmethod
    def from_geometry(self, geometry_data):
        """Load and interpret geometric field or shape data."""
        pass

    @abstractmethod
    def to_binary(self):
        """Convert field/geometry data to binary bitstring (string of 0/1)."""
        pass

    def checksum(self, bitstring):
        """Generate BLAKE3-like checksum using SHA256 for now."""
        return hashlib.sha256(bitstring.encode("utf-8")).hexdigest()

    def report(self):
        return {
            "modality": self.modality,
            "bit_depth": self.bit_depth,
            "bits": len(self.binary_output) if self.binary_output else 0,
            "checksum": self.checksum(self.binary_output or ""),
            "metadata": self.metadata
        }
