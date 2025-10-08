import numpy as np
from .common import gray_code, bits_from_int

def gravity_features(mass: float, velocity: float, radius: float, G: float = 6.67430e-11) -> dict:
    """
    Extract gravitational features from a simple orbital system.

    Args:
        mass: central mass in kg
        velocity: orbital velocity (m/s)
        radius: orbital radius (m)
        G: gravitational constant

    Returns:
        dict of gravitational state features
    """
    # Escape velocity at given radius
    v_escape = np.sqrt(2 * G * mass / radius)

    # Bound vs unbound
    bound = 1 if velocity < v_escape else 0

    # Curvature approximation (concave vs convex)
    # concave well = attractive field
    curvature = -G * mass / (radius**2)
    curvature_sign = 1 if curvature >= 0 else 0  # 1 = concave, 0 = convex/repulsive

    # Stability: compare orbital velocity to circular velocity
    v_circ = np.sqrt(G * mass / radius)
    stability = 0
    if abs(velocity - v_circ) / v_circ < 0.05:
        stability = 2  # stable
    elif velocity < v_circ:
        stability = 1  # decaying
    else:
        stability = 3  # escaping/unstable

    # Depth of potential well
    potential = -G * mass / radius

    return {
        "bound": bound,
        "curvature_sign": curvature_sign,
        "stability": stability,
        "potential": potential
    }

def encode_gravity_gray(features: dict, target_bits: int = 256) -> str:
    """
    Encode gravity features → binary bitstring.
    """
    # Bound/unbound
    bound_bit = '1' if features["bound"] else '0'

    # Curvature sign
    curve_bit = '1' if features["curvature_sign"] else '0'

    # Stability (2 bits)
    stab_bits = bits_from_int(gray_code(features["stability"]), 2)

    # Potential well depth quantization (4 bits)
    # normalize potential relative to arbitrary scale
    scaled = int(np.clip(abs(features["potential"]) / 1e7, 0, 15))
    pot_bits = bits_from_int(gray_code(scaled), 4)

    payload = bound_bit + curve_bit + stab_bits + pot_bits

    return (payload * ((target_bits // len(payload)) + 1))[:target_bits]
