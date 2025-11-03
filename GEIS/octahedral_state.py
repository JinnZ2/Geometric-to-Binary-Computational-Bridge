"""
OctahedralState: Core geometric state representation for GIES

Represents a single octahedral coordination state in silicon with:
- 8 possible vertex positions in cubic coordinates
- Mapping to binary representation
- Token notation support
"""

import numpy as np
from typing import Tuple, Optional


class OctahedralState:
    """Represents a single octahedral geometric state"""
    
    # 8 octahedral vertex positions in cubic coordinates
    POSITIONS = {
        0: (0.25, 0.25, 0.25),    # (+,+,+)
        1: (0.25, -0.25, 0.25),   # (+,-,+) 
        2: (-0.25, 0.25, 0.25),   # (-,+,+)
        3: (-0.25, -0.25, 0.25),  # (-,-,+)
        4: (0.25, 0.25, -0.25),   # (+,+,-)
        5: (0.25, -0.25, -0.25),  # (+,-,-)
        6: (-0.25, 0.25, -0.25),  # (-,+,-)
        7: (-0.25, -0.25, -0.25)  # (-,-,-)
    }
    
    def __init__(self, index: int):
        """Initialize octahedral state (index 0-7)"""
        if not isinstance(index, int) or not (0 <= index <= 7):
            raise ValueError("Index must be integer 0-7")
        self.index = index
        self.position = np.array(self.POSITIONS[index])
        
    def to_binary(self, width: int = 3) -> str:
        """Convert state index to binary representation"""
        return format(self.index, f'0{width}b')
    
    def to_token(self, operator: str = '|', symbol: str = 'O') -> str:
        """Convert to geometric token notation like '001|O'"""
        return f"{self.to_binary()}{operator}{symbol}"
    
    @classmethod
    def from_token(cls, token: str) -> 'OctahedralState':
        """Parse token back to state"""
        operators = ['||', '|', '/', ':']
        operator_found = None
        
        for op in operators:
            if op in token:
                operator_found = op
                break
                
        if operator_found is None:
            raise ValueError("Token must contain operator ('|', '/', ':')")
        
        parts = token.split(operator_found, 1)
        binary_str = parts[0]
        index = int(binary_str, 2)
        return cls(index)
    
    @classmethod
    def from_binary(cls, binary_str: str) -> 'OctahedralState':
        """Create state from binary string"""
        return cls(int(binary_str, 2))
    
    def invert(self) -> 'OctahedralState':
        """Octahedral inversion (NOT operation): i -> (7-i)"""
        return OctahedralState(7 - self.index)
    
    def distance_to(self, other: 'OctahedralState') -> float:
        """Calculate Euclidean distance to another state"""
        return np.linalg.norm(self.position - other.position)
    
    def dot_product(self, other: 'OctahedralState') -> float:
        """Calculate dot product with another state"""
        return np.dot(self.position, other.position)
    
    def __eq__(self, other) -> bool:
        return isinstance(other, OctahedralState) and self.index == other.index
    
    def __hash__(self) -> int:
        return hash(self.index)
    
    def __repr__(self) -> str:
        return f"OctahedralState(index={self.index}, pos={tuple(self.position)})"
    
    def __str__(self) -> str:
        return f"O{self.index}@{self.to_binary()}"
