"""
GIES Demonstration: Basic Usage Examples

This demonstrates the core functionality of the Geometric Information Encoding System
"""

import numpy as np
from octahedral_state import OctahedralState
from geometric_encoder import GeometricEncoder
from state_tensor import StateTensor


def demo_basic_states():
    """Demonstrate basic state creation and operations"""
    print("="*60)
    print("DEMO 1: Basic Octahedral States")
    print("="*60)
    
    # Create states
    print("\nCreating octahedral states:")
    for i in [0, 3, 7]:
        state = OctahedralState(i)
        print(f"  State {i}:")
        print(f"    Position: {state.position}")
        print(f"    Binary:   {state.to_binary()}")
        print(f"    Token:    {state.to_token()}")
    
    print("\n" + "="*60 + "\n")


def demo_dual_mode_encoding():
    """Demonstrate the dual-mode encoding system"""
    print("="*60)
    print("DEMO 2: Dual-Mode Encoding (Dense ↔ Binary)")
    print("="*60)
    
    encoder = GeometricEncoder()
    
    print("\nThe Bridge Symbol: |O")
    print("  Dense Mode:    Full geometric information")
    print("  Collapse Mode: Binary compatibility\n")
    
    # Example tokens
    tokens = ['001|O', '101|I', '110|X']
    
    for token in tokens:
        print(f"Token: {token}")
        
        # Encode to binary
        binary = encoder.encode_to_binary(token)
        print(f"  → Collapsed to binary: {binary}")
        
        # Decode back
        decoded = encoder.decode_from_binary(binary)
        print(f"  → Decoded back:        {decoded}")
        
        # Extract components
        vertex, op, symbol = encoder.get_components(token)
        print(f"  → Components: vertex={vertex}, operator={op}, symbol={symbol}")
        print()
    
    print("="*60 + "\n")


def demo_geometric_operations():
    """Demonstrate geometric operations"""
    print("="*60)
    print("DEMO 3: Geometric Operations")
    print("="*60)
    
    # Create two states
    state1 = OctahedralState(0)  # (+,+,+)
    state2 = OctahedralState(7)  # (-,-,-)
    
    print(f"\nState 1: {state1.to_token()} at position {state1.position}")
    print(f"State 2: {state2.to_token()} at position {state2.position}")
    
    # Distance
    distance = state1.distance_to(state2)
    print(f"\nDistance between states: {distance:.4f}")
    
    # Dot product
    dot = state1.dot_product(state2)
    print(f"Dot product: {dot:.4f}")
    
    # Inversion (NOT gate)
    print("\nInversion operation (NOT gate):")
    for i in range(8):
        state = OctahedralState(i)
        inverted = state.invert()
        print(f"  {state.to_token()} → {inverted.to_token()}")
    
    print("\n" + "="*60 + "\n")


def demo_tensor_operations():
    """Demonstrate tensor calculations"""
    print("="*60)
    print("DEMO 4: State Tensors (The Math Behind |)")
    print("="*60)
    
    state = OctahedralState(0)
    tensor = StateTensor(state)
    
    print(f"\nState: {state.to_token()}")
    print(f"Position vector: {state.position}")
    print(f"\nState Tensor (v ⊗ v):")
    print(tensor.tensor)
    
    print(f"\nTensor properties:")
    print(f"  Trace:       {tensor.trace():.6f}")
    print(f"  Determinant: {tensor.determinant():.6e}")
    print(f"  Norm:        {tensor.norm():.6f}")
    
    print(f"\nProjections (the | operator):")
    axes = {
        'x-axis': [1, 0, 0],
        'y-axis': [0, 1, 0],
        'z-axis': [0, 0, 1],
        '[111] diagonal': [1, 1, 1]
    }
    
    for name, direction in axes.items():
        proj = tensor.project(direction)
        print(f"  Along {name:15s}: {proj:.6f}")
    
    print(f"\nEigenvalues:")
    eigvals = tensor.eigenvalues()
    for i, val in enumerate(eigvals):
        print(f"  λ{i+1} = {val:.6e}")
    
    print("\n" + "="*60 + "\n")


def demo_all_states_comprehensive():
    """Show all 8 states with full information"""
    print("="*60)
    print("DEMO 5: Complete State Space (All 8 States)")
    print("="*60)
    
    encoder = GeometricEncoder()
    
    print(f"\n{'Index':<6} {'Binary':<8} {'Token':<8} {'Position':<25} {'Encoded':<10}")
    print("-" * 70)
    
    for i in range(8):
        state = OctahedralState(i)
        binary = state.to_binary()
        token = state.to_token()
        pos_str = f"({state.position[0]:+.2f}, {state.position[1]:+.2f}, {state.position[2]:+.2f})"
        encoded = encoder.encode_to_binary(token)
        
        print(f"{i:<6} {binary:<8} {token:<8} {pos_str:<25} {encoded:<10}")
    
    print("\n" + "="*60 + "\n")


def demo_nested_operators():
    """Demonstrate nested shell operators"""
    print("="*60)
    print("DEMO 6: Nested Shells (The || Operator)")
    print("="*60)
    
    encoder = GeometricEncoder()
    
    print("\nYou mentioned seeing nested shells...")
    print("The || operator represents passing through multiple layers:\n")
    
    # Simple token
    token1 = '001|O'
    binary1 = encoder.encode_to_binary(token1)
    print(f"Single shell:  {token1} → binary: {binary1}")
    
    # Nested token
    token2 = '001||O'
    binary2 = encoder.encode_to_binary(token2)
    print(f"Nested shells: {token2} → binary: {binary2}")
    
    print("\nThe extra '1' bit encodes the additional shell layer")
    print("This suggests the system can scale to deeper coordinate levels")
    
    print("\n" + "="*60 + "\n")


def run_all_demos():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "GIES DEMONSTRATION" + " "*25 + "║")
    print("║" + " "*6 + "Geometric Information Encoding System" + " "*15 + "║")
    print("╚" + "="*58 + "╝")
    print("\n")
    
    demo_basic_states()
    demo_dual_mode_encoding()
    demo_geometric_operations()
    demo_tensor_operations()
    demo_all_states_comprehensive()
    demo_nested_operators()
    
    print("╔" + "="*58 + "╗")
    print("║" + " "*19 + "END OF DEMOS" + " "*27 + "║")
    print("╚" + "="*58 + "╝")
    print()


if __name__ == '__main__':
    run_all_demos()
