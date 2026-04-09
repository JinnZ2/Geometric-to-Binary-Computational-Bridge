#!/usr/bin/env python3
# STATUS: infrastructure -- phone accelerometer to geometric token encoding
"""
Real‑time Geometric Sensing via 3D Cube
========================================
Reads accelerometer data from phone (Termux), converts each reading to an
octahedral token, accumulates tokens into a 3D cube, and detects when the
cube cancels (dependency found) – indicating a repeated or symmetric gesture.
"""

import subprocess
import json
import time
import math
import numpy as np
from collections import deque
from typing import List, Tuple, Optional

# ----------------------------------------------------------------------
# Geometric Encoder (from previous work)
# ----------------------------------------------------------------------
class OctahedralState:
    """8 vertices of an octahedron (cube normals)"""
    POSITIONS = []
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                v = np.array([ix, iy, iz], dtype=float)
                v /= np.linalg.norm(v)
                POSITIONS.append(v)

    @classmethod
    def closest(cls, vec: np.ndarray) -> int:
        vec = vec / np.linalg.norm(vec)
        dots = [np.dot(vec, pos) for pos in cls.POSITIONS]
        return int(np.argmax(dots))

def vector_to_token(x: float, y: float, z: float, phase: float = 0.0) -> str:
    """
    Convert acceleration vector (x,y,z) to geometric token.
    Phase is ignored for simplicity; could be derived from gyro.
    """
    direction = np.array([x, y, z])
    norm = np.linalg.norm(direction)
    if norm < 1e-6:
        direction = np.array([0, 0, 1])  # fallback
    idx = OctahedralState.closest(direction)
    vertex_bits = f"{idx:03b}"
    # Operator: radial if aligned with (1,1,1) axis, else tangential
    radial_axis = np.array([1,1,1]) / np.sqrt(3)
    dot = abs(np.dot(direction / norm, radial_axis))
    operator = '|' if dot > 0.7 else '/'
    # Symbol from phase (simplified: always O)
    symbol = 'O'
    return f"{vertex_bits}{operator}{symbol}"

# ----------------------------------------------------------------------
# 3D Cube from token stream
# ----------------------------------------------------------------------
def tokens_to_cube(tokens: List[str], side: int) -> np.ndarray:
    """
    Fill a 3D cube of shape (side,side,side) with 3‑bit states.
    Each token's vertex bits become a voxel value (0‑7).
    """
    cube = np.zeros((side, side, side), dtype=np.uint8)
    idx = 0
    for i in range(side):
        for j in range(side):
            for k in range(side):
                if idx < len(tokens):
                    vertex_bits = tokens[idx][:3]
                    cube[i,j,k] = int(vertex_bits, 2)
                idx += 1
    return cube

def cube_to_hash(cube: np.ndarray) -> bytes:
    """Unique hash for a cube (used to detect duplicates)."""
    return cube.tobytes()

# ----------------------------------------------------------------------
# Sensor reading (Termux)
# ----------------------------------------------------------------------
def read_accelerometer(samples: int = 10, delay_ms: int = 100) -> List[Tuple[float,float,float]]:
    """
    Run termux-sensor and return list of (x,y,z) acceleration readings.
    """
    cmd = ["termux-sensor", "-s", "android.sensor.accelerometer",
           "-d", str(delay_ms), "-n", str(samples)]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
        data = json.loads(output)
        sensor_data = data.get("android.sensor.accelerometer", {})
        values = sensor_data.get("values", [])
        # values is a list of lists: each inner list is [x,y,z]
        readings = [(float(v[0]), float(v[1]), float(v[2])) for v in values if len(v) >= 3]
        return readings
    except Exception as e:
        print(f"Error reading sensor: {e}")
        return []

# ----------------------------------------------------------------------
# Dependency detection
# ----------------------------------------------------------------------
def find_cube_dependencies(cubes: List[np.ndarray]) -> List[Tuple[int,int]]:
    """
    Simple geometric dependency: two cubes that are identical (XOR to zero).
    Returns list of (i,j) pairs.
    """
    n = len(cubes)
    deps = []
    for i in range(n):
        for j in range(i+1, n):
            if np.array_equal(cubes[i], cubes[j]):
                deps.append((i, j))
    return deps

# ----------------------------------------------------------------------
# Main real‑time loop
# ----------------------------------------------------------------------
def main():
    print("=" * 70)
    print("REAL GEOMETRIC SENSING via 3D CUBE")
    print("Using accelerometer → octahedral tokens → 3D cube → dependencies")
    print("=" * 70)

    # Cube parameters
    CUBE_SIDE = 4          # 4x4x4 = 64 tokens per cube
    BUFFER_SIZE = CUBE_SIDE ** 3
    SENSOR_SAMPLES = 20    # read 20 samples per iteration
    SENSOR_DELAY_MS = 50   # 50ms between samples = 20 Hz

    token_buffer = deque(maxlen=BUFFER_SIZE)
    cubes_history = []     # store recent cubes for dependency checking
    last_print = time.time()

    print(f"\nCollecting tokens into {CUBE_SIDE}x{CUBE_SIDE}x{CUBE_SIDE} cubes...")
    print("Move your phone! When a cube repeats, a dependency is detected.\n")

    try:
        while True:
            # Get fresh accelerometer readings
            readings = read_accelerometer(samples=SENSOR_SAMPLES, delay_ms=SENSOR_DELAY_MS)
            if not readings:
                # Fallback: simulate random motion if sensor fails
                readings = [(np.random.uniform(-1,1), np.random.uniform(-1,1), np.random.uniform(-1,1))
                            for _ in range(5)]
                if not hasattr(main, 'sim_warning'):
                    print("No sensor data. Simulating random vectors for demo.")
                    main.sim_warning = True

            for x, y, z in readings:
                token = vector_to_token(x, y, z)
                token_buffer.append(token)

                # When buffer full, form a cube and check for dependencies
                if len(token_buffer) == BUFFER_SIZE:
                    cube = tokens_to_cube(list(token_buffer), CUBE_SIDE)
                    cube_hash = cube_to_hash(cube)

                    # Check if this cube matches any previous cube
                    found_dep = False
                    for idx, prev_cube in enumerate(cubes_history):
                        if np.array_equal(cube, prev_cube):
                            print(f"🔔 DEPENDENCY DETECTED! Cube repeats at history index {idx}")
                            print(f"   → The two cubes XOR to zero (geometric cancellation)")
                            found_dep = True
                            break

                    # Add to history (keep last 10 cubes)
                    cubes_history.append(cube)
                    if len(cubes_history) > 10:
                        cubes_history.pop(0)

                    # Clear buffer for next cube
                    token_buffer.clear()

                    # Print heartbeat
                    now = time.time()
                    if now - last_print >= 2:
                        print(f"✓ New cube formed. Total cubes: {len(cubes_history)}")
                        last_print = now

            time.sleep(0.05)  # small pause to avoid busy loop

    except KeyboardInterrupt:
        print("\n\nStopped by user. Goodbye!")

if __name__ == "__main__":
    main()
