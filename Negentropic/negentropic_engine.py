# negentropic_engine.py
# Negentropic framework: resonance, adaptability, diversity, loss, M(S)
# Agent-based simulation with geometric coupling
# Extracted from 05-implementation.md
#
# DIMENSIONAL WARNING, applying to everything below that computes M:
# D is a variance (pattern^2) and L is a power (pattern^2 / time^2), so
# (R_e * A * D) - L subtracts quantities that are not in the same units.
# M is therefore an ordinal index that is only comparable against other M
# values computed with identical normalisation, and "M >= 10" is not a
# statement about anything. The dimensionally sound persistence criterion
# is NEG-8 in persistence.py: Phi = -S_exchange_dot - sigma, both W/K.
# See corrections.md.

import os
import sys
from datetime import timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Negentropic.core import distance_kernel, phase_alignment


# ---------------------------
# Core Calculations
# ---------------------------

def compute_resonance(patterns, signals):
    """
    Geometric mean of pairwise log-similarities.

    patterns: array of pattern states p_i (shape [n]), interpreted as PHASES
    signals:  array of signal strengths s_i (shape [n]) -- must be > 0

    Returns R_e in (0, max_signal].
    NOTE: R_e is not normalized to [0,1] -- normalise signals to unit
    magnitude if you want R_e in [0, 1].

    The pairwise term is a raised cosine of the signed phase difference,
    wrapped into (-pi, pi] first. Wrapping matters: without it the kernel is
    multi-valued in the separation, and two patterns 2*pi apart score as
    perfectly aligned. This function is only meaningful when `patterns` are
    phases; for Euclidean positions use compute_adaptability's kernel.
    """
    n = len(patterns)
    coupling_sum = 0
    epsilon = 1e-10

    for i in range(n):
        for j in range(i + 1, n):
            d_ij = float(patterns[i] - patterns[j])
            signal_product = np.sqrt(abs(signals[i] * signals[j]))
            g_ij = phase_alignment(d_ij) * signal_product
            coupling_sum += np.log(g_ij + epsilon)

    N_p = n * (n - 1) / 2
    R_e = np.exp(coupling_sum / N_p)
    return R_e


def compute_adaptability(patterns, alpha):
    """
    Mean pairwise exponential proximity.
    alpha: coupling sensitivity (larger = shorter effective range).
    Returns A in (0, 1].

    Accepts scalar patterns (shape [n]) or vector patterns (shape [n, dim]);
    separation is the Euclidean norm of the difference, which reduces to
    abs() in the scalar case.
    """
    n = len(patterns)
    if alpha <= 0:
        raise ValueError("alpha must be positive")
    coupling_strength = 0

    for i in range(n):
        for j in range(i + 1, n):
            d_ij = float(np.linalg.norm(np.asarray(patterns[i], dtype=float)
                                        - np.asarray(patterns[j], dtype=float)))
            coupling_strength += distance_kernel(d_ij, scale=1.0 / alpha)

    W = n * (n - 1) / 2
    A = coupling_strength / W
    return A


def compute_diversity(patterns):
    """
    Variance across pattern states.
    Returns D >= 0; D = 0 iff all patterns identical.
    """
    return np.var(patterns)


def compute_loss(noise_power, adaptability, lambda_param):
    """
    noise_power:   system noise / entropy production estimate
    adaptability:  from compute_adaptability()
    lambda_param:  inefficiency scaling factor (free parameter)
    Returns L >= 0.
    """
    return noise_power + lambda_param * (1 - adaptability)


def compute_M(patterns, signals, alpha, noise_power, lambda_param):
    """
    Full M(S) calculation.
    Returns (M, R_e, A, D, L).
    M > 0 when constructive coupling outweighs loss.

    Dimensionally invalid as written -- see the module header. Use it to
    rank states produced under one fixed normalisation, never to compare
    against a threshold or against M values from another run.
    """
    R_e = compute_resonance(patterns, signals)
    A = compute_adaptability(patterns, alpha)
    D = compute_diversity(patterns)
    L = compute_loss(noise_power, A, lambda_param)
    M = (R_e * A * D) - L
    return M, R_e, A, D, L


# ---------------------------
# Agent-Based Simulation
# ---------------------------

class GeometricAgent:
    def __init__(self, dim, signal_strength):
        self.dim = dim
        self.pattern = np.random.randn(dim)
        self.signal = signal_strength
        self.C = 1.0       # curiosity
        self.R_e = 0.0     # set by coupling

    def couple_with(self, other, alpha):
        """Pairwise coupling: distance kernel times geometric-mean signal.

        The old version also multiplied in 0.5*(cos(d)+1) with d a Euclidean
        norm. Nothing in this model carries a phase for that cosine to
        measure, and it wraps, so agents 2*pi apart scored as perfectly
        aligned. The factor is removed rather than replaced.
        """
        d = float(np.linalg.norm(self.pattern - other.pattern))
        sig = np.sqrt(self.signal * other.signal)
        return distance_kernel(d, scale=1.0 / alpha) * sig

    def update_resonance(self, all_agents, alpha):
        Ks = [self.couple_with(o, alpha) for o in all_agents if o is not self]
        self.R_e = np.exp(np.mean(np.log(np.array(Ks) + 1e-10))) if Ks else 0.0

    def update_curiosity(self, alpha_0, E, E_crit=1.0, C_max=100.0, dt=1.0):
        """Logistic curiosity growth: dC/dt = alpha * R_e * C * (1 - C/C_max).

        The old form was C *= (1 + alpha * R_e), which compounds: it is a
        discrete exponential clamped at C_max, so C pinned to the ceiling
        within a few steps and stayed there regardless of dynamics. The
        saturating term makes the approach to C_max asymptotic, which is
        what the framework text describes (01-framework.md notes the missing
        saturation as an open item).
        """
        alpha = alpha_0 if E >= E_crit else 0.0
        dC = alpha * self.R_e * self.C * (1.0 - self.C / C_max) * dt
        self.C = float(min(max(self.C + dC, 0.0), C_max))

    def explore(self, beta):
        D = self.C ** 2
        noise = np.random.normal(0, np.sqrt(2 * D), size=self.dim)
        self.pattern += beta * noise

    def compute_joy(self, diversity):
        return diversity * (1 + self.R_e) * self.C


class GeometricNetwork:
    def __init__(self, n_agents, dim):
        self.agents = [GeometricAgent(dim, signal_strength=1.0) for _ in range(n_agents)]
        # A, D and L are recorded alongside M so that a run can be inspected
        # component by component. M itself is an ordinal index (see the
        # module header) and tells you least of the four.
        self.history = {'M': [], 'R_e': [], 'C': [], 'J': [],
                        'A': [], 'D': [], 'L': []}

    def step(self, alpha=1.0, beta=0.1, alpha_0=0.5, E=2.0, lambda_param=0.1):
        for agent in self.agents:
            agent.update_resonance(self.agents, alpha)
        for agent in self.agents:
            agent.update_curiosity(alpha_0, E)
            agent.explore(beta)

        patterns = np.array([a.pattern for a in self.agents])
        D = np.var(patterns)
        avg_R_e = np.mean([a.R_e for a in self.agents])
        avg_C = np.mean([a.C for a in self.agents])
        total_J = sum(a.compute_joy(D) for a in self.agents)

        # A was previously set to avg_R_e, which collapsed M to R_e^2 * D
        # minus a constant -- adaptability contributed nothing of its own.
        # It is now the pairwise proximity measure the framework defines.
        A = compute_adaptability(patterns, alpha)

        # L was previously the literal constant 0.1. It is now the variance
        # actually injected by explore(): each agent adds beta * N(0, sqrt(2C^2))
        # per dimension, so the injected power is 2 * beta^2 * C^2.
        noise_power = float(np.mean([2.0 * beta ** 2 * a.C ** 2 for a in self.agents]))
        L = compute_loss(noise_power, A, lambda_param)
        M = (avg_R_e * A * D) - L

        self.history['M'].append(M)
        self.history['R_e'].append(avg_R_e)
        self.history['C'].append(avg_C)
        self.history['J'].append(total_J)
        self.history['A'].append(A)
        self.history['D'].append(D)
        self.history['L'].append(L)
        return M

    def run(self, timesteps=500, **kw):
        for t in range(timesteps):
            M = self.step(**kw)
            if t % 100 == 0:
                print(f"t={t:4d}  M={M:.3f}  R_e={self.history['R_e'][-1]:.3f}"
                      f"  C={self.history['C'][-1]:.3f}")
        return self.history


# ---------------------------
# Fibonacci Therapy Scheduler
# ---------------------------

def fibonacci_schedule(start_date, n_sessions):
    """Cumulative Fibonacci day-offset schedule.

    Kept for reproducing the original figures. Nothing derives Fibonacci
    spacing specifically, and the empirical claim that was supposed to
    support it does not survive audit (02-empirical-audit.md, Claim 1).
    For new work use maintenance.expanding_schedule, where the growth ratio
    is a fitted parameter with a confidence interval rather than a premise;
    ratio = PHI reproduces this schedule asymptotically.
    """
    fib = [1, 1]
    while len(fib) < n_sessions:
        fib.append(fib[-1] + fib[-2])
    schedule = [start_date]
    cumulative = 0
    for i in range(1, n_sessions):
        cumulative += fib[i]
        schedule.append(start_date + timedelta(days=cumulative))
    return schedule, fib


# ---------------------------
# Example Run
# ---------------------------

if __name__ == "__main__":
    print("=== Core M(S) Calculation ===")
    patterns = np.array([0.5, 1.2, 0.8, 1.5, 0.3])
    signals = np.array([1.0, 0.8, 1.2, 0.9, 1.1])
    M, R_e, A, D, L = compute_M(patterns, signals, alpha=1.0,
                                  noise_power=0.05, lambda_param=0.1)
    print(f"  M={M:.4f}  R_e={R_e:.4f}  A={A:.4f}  D={D:.4f}  L={L:.4f}")

    print("\n=== Agent Network (50 steps) ===")
    net = GeometricNetwork(n_agents=5, dim=3)
    net.run(timesteps=50, alpha=1.0, beta=0.05, alpha_0=0.3, E=2.0)
    print(f"  Final M={net.history['M'][-1]:.4f}")
