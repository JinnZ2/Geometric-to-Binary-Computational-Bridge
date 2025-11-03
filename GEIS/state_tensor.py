"""
StateTensor: Tensor representation and operations for geometric states

Calculates and manipulates 3x3 symmetric tensors representing
electron density distributions in octahedral states.
"""

import numpy as np
from typing import Tuple, List
from octahedral_state import OctahedralState


class StateTensor:
    """Calculate and manipulate state tensors"""
    
    def __init__(self, state: OctahedralState, weight: float = 1.0):
        """
        Initialize state tensor
        
        Args:
            state: Octahedral state
            weight: Weighting factor (electron density)
        """
        self.state = state
        self.weight = weight
        self.vector = state.position
        self.tensor = self._calculate_tensor()
    
    def _calculate_tensor(self) -> np.ndarray:
        """Calculate symmetric rank-2 tensor from state vector"""
        v = self.vector * self.weight
        # Outer product: T = v ⊗ v
        return np.outer(v, v)
    
    def project(self, direction: np.ndarray) -> float:
        """
        Project tensor along a direction (the | operator)
        
        Returns scalar: n̂ · T · n̂
        
        Args:
            direction: Direction vector to project onto
            
        Returns:
            Projected scalar value
        """
        direction = np.array(direction)
        n = direction / np.linalg.norm(direction)
        return float(n @ self.tensor @ n)
    
    def eigenvalues(self) -> np.ndarray:
        """Get eigenvalues of state tensor"""
        return np.linalg.eigvalsh(self.tensor)
    
    def eigenvectors(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get eigenvalues and eigenvectors of state tensor"""
        return np.linalg.eigh(self.tensor)
    
    def trace(self) -> float:
        """Calculate trace of tensor"""
        return float(np.trace(self.tensor))
    
    def determinant(self) -> float:
        """Calculate determinant of tensor"""
        return float(np.linalg.det(self.tensor))
    
    def norm(self) -> float:
        """Calculate Frobenius norm of tensor"""
        return float(np.linalg.norm(self.tensor))
    
    @staticmethod
    def combine(tensors: List['StateTensor']) -> np.ndarray:
        """
        Combine multiple state tensors
        
        Args:
            tensors: List of StateTensor objects
            
        Returns:
            Combined tensor (sum of individual tensors)
        """
        if not tensors:
            return np.zeros((3, 3))
        
        combined = np.zeros((3, 3))
        for t in tensors:
            combined += t.tensor
        return combined
    
    def rotate(self, rotation_matrix: np.ndarray) -> 'StateTensor':
        """
        Rotate the tensor by a rotation matrix
        
        T' = R · T · R^T
        
        Args:
            rotation_matrix: 3x3 rotation matrix
            
        Returns:
            New StateTensor with rotated tensor
        """
        R = rotation_matrix
        rotated_tensor = R @ self.tensor @ R.T
        
        # Create new state with rotated position
        rotated_pos = R @ self.vector
        # Find closest state to rotated position
        distances = [np.linalg.norm(rotated_pos - np.array(OctahedralState.POSITIONS[i])) 
                    for i in range(8)]
        closest_idx = np.argmin(distances)
        
        new_state = OctahedralState(closest_idx)
        result = StateTensor(new_state, self.weight)
        result.tensor = rotated_tensor
        return result
    
    def __repr__(self) -> str:
        return f"StateTensor(state={self.state.index}, weight={self.weight})"
    
    def __str__(self) -> str:
        return f"Tensor for {self.state}:\n{self.tensor}"
