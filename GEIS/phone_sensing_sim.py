# STATUS: infrastructure -- phone termux-sensor integration to 3D cube
import subprocess
import json
import time
import numpy as np
from collections import deque

# Reuse vector_to_token from earlier
def vector_to_token(x, y, z, phase=0):
    # ... same as before, but phase can be angle from gyro or just 0
    pass

def read_accelerometer(seconds=1):
    """Run termux-sensor and return list of (x,y,z) tuples."""
    cmd = ["termux-sensor", "-s", "android.sensor.accelerometer", 
           "-d", "100", "-n", str(int(seconds*10))]
    output = subprocess.check_output(cmd).decode()
    data = json.loads(output)
    readings = []
    for entry in data.get("android.sensor.accelerometer", {}).get("values", []):
        # entry is [x, y, z] as list of floats
        readings.append(tuple(entry))
    return readings

def stream_to_3d_cube(stream, side=4):
    """
    stream: list of tokens (strings like "001|O")
    side: cube side length (total cells = side^3)
    Returns a 3D numpy array of shape (side,side,side) with tokens?
    Actually we need numeric representation: each cell gets a 3-bit state.
    """
    cube = np.zeros((side, side, side), dtype=np.uint8)
    idx = 0
    for i in range(side):
        for j in range(side):
            for k in range(side):
                if idx < len(stream):
                    token = stream[idx]
                    vertex_bits = token[:3]
                    state = int(vertex_bits, 2)  # 0-7
                    cube[i,j,k] = state
                idx += 1
    return cube

# Main loop
def real_sensing_loop(duration=60, cube_side=4):
    token_buffer = deque(maxlen=cube_side**3)
    start = time.time()
    while time.time() - start < duration:
        readings = read_accelerometer(seconds=0.5)  # ~50 readings
        for (x,y,z) in readings:
            token = vector_to_token(x, y, z, phase=0)
            token_buffer.append(token)
            if len(token_buffer) == cube_side**3:
                cube = stream_to_3d_cube(list(token_buffer), cube_side)
                # Find geometric dependencies in cube (using earlier function)
                deps = find_geometric_dependencies([cube], max_comb=2)
                if deps:
                    print(f"Gesture detected! Dependency: {deps}")
                token_buffer.clear()
        time.sleep(0.1)
