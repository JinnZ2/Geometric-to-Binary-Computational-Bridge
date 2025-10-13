import numpy as np
import random, time

# --- Parameters ---
CELLS = 100
ANGLE_OPT = 109.47
TRACE_TARGET = 1.0
TOL_ANGLE = 2.0
TOL_TRACE = 0.02

def random_tensor():
    eigs = np.random.dirichlet(np.ones(3))
    angle = ANGLE_OPT + random.uniform(-3, 3)
    return {"λ": eigs, "angle": angle}

def validate_tensor(t):
    trace_ok = abs(sum(t["λ"]) - TRACE_TARGET) <= TOL_TRACE
    angle_ok = abs(t["angle"] - ANGLE_OPT) <= TOL_ANGLE
    return trace_ok and angle_ok

def simulate_lattice():
    lattice = [random_tensor() for _ in range(CELLS)]
    valid = sum(validate_tensor(t) for t in lattice)
    print(f"✅ {valid}/{CELLS} cells valid ({valid/CELLS*100:.1f}%)")
    fault_energy = (CELLS - valid) * 1.2  # aJ per correction
    print(f"Estimated correction energy: {fault_energy:.2f} aJ")

if __name__ == "__main__":
    print("🧮 Running Octahedral Lattice Simulation...")
    start = time.time()
    simulate_lattice()
    print(f"⏱ Completed in {time.time()-start:.2f}s")
