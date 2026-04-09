# STATUS: validated — tested by tests/test_silicon_modules.py
"""
core_equations.py
=================
Executable Python implementations of the physics equations defined in
Silicon/CORE_EQUATIONS.md.

Part of the SYSTEM_ENERGY_DYNAMICS suite -- base physical, biological, and
mechanical equations underpinning energy and control models.

Categories
----------
- Mechanics & Robotics  (Newton, Work/Energy, Torque, Lagrangian, PID)
- Biology / Biophysics   (Michaelis-Menten, Hill, Fick, Nernst, Hodgkin-Huxley, Logistic)
- Physics (Thermo, Fluids, Dynamics)  (Conservation of Energy, 1st Law, Bernoulli,
  Navier-Stokes helpers, Hooke, Stress-Strain, Fourier)
- Robot Kinematics       (Forward/Inverse Kinematics, DH matrices, Jacobian)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from typing import Callable, List, Sequence, Tuple, Union

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

#: Universal gas constant  (J / (mol·K))
R_GAS: float = 8.314462618

#: Faraday constant  (C / mol)
FARADAY: float = 96485.33212

#: Standard gravitational acceleration  (m/s²)
G_ACCEL: float = 9.80665

#: Boltzmann constant  (J/K)
K_BOLTZMANN: float = 1.380649e-23

#: Pi
PI: float = np.pi

# =========================================================================
# §1  MECHANICS & ROBOTICS
# =========================================================================

# ---- 1. Newton's Laws of Motion -----------------------------------------

def force(mass: float, acceleration: float) -> float:
    """F = m·a  —  Newton's second law.

    Parameters
    ----------
    mass : float
        Mass in kg.
    acceleration : float
        Acceleration in m/s².

    Returns
    -------
    float
        Force in Newtons (N).
    """
    return mass * acceleration


# ---- 2. Work and Energy -------------------------------------------------

def work(f: float, d: float, theta: float = 0.0) -> float:
    """W = F·d·cos(θ)  —  Mechanical work.

    Parameters
    ----------
    f : float
        Applied force (N).
    d : float
        Displacement (m).
    theta : float
        Angle between force and displacement vectors (radians). Default 0.

    Returns
    -------
    float
        Work in Joules (J).
    """
    return f * d * np.cos(theta)


def kinetic_energy(mass: float, velocity: float) -> float:
    """KE = ½mv²  —  Kinetic energy.

    Parameters
    ----------
    mass : float
        Mass in kg.
    velocity : float
        Speed in m/s.

    Returns
    -------
    float
        Kinetic energy in Joules (J).
    """
    return 0.5 * mass * velocity ** 2


def potential_energy(mass: float, height: float, g: float = G_ACCEL) -> float:
    """PE = mgh  —  Gravitational potential energy.

    Parameters
    ----------
    mass : float
        Mass in kg.
    height : float
        Height above reference in m.
    g : float
        Gravitational acceleration (m/s²). Defaults to 9.80665.

    Returns
    -------
    float
        Potential energy in Joules (J).
    """
    return mass * g * height


# ---- 3. Torque and Rotational Motion ------------------------------------

def torque_cross(r: NDArray[np.floating], f: NDArray[np.floating]) -> NDArray[np.floating]:
    """τ = r × F  —  Torque as the cross product of lever arm and force.

    Parameters
    ----------
    r : array_like, shape (3,)
        Position vector from pivot to point of force application (m).
    f : array_like, shape (3,)
        Force vector (N).

    Returns
    -------
    ndarray, shape (3,)
        Torque vector (N·m).
    """
    return np.cross(np.asarray(r, dtype=float), np.asarray(f, dtype=float))


def moment_of_inertia(masses: Sequence[float], radii: Sequence[float]) -> float:
    """I = Σ m_i·r_i²  —  Moment of inertia for discrete point masses.

    Parameters
    ----------
    masses : sequence of float
        Point masses (kg).
    radii : sequence of float
        Perpendicular distances from rotation axis (m).

    Returns
    -------
    float
        Moment of inertia (kg·m²).
    """
    m = np.asarray(masses, dtype=float)
    r = np.asarray(radii, dtype=float)
    return float(np.sum(m * r ** 2))


def torque_rotational(inertia: float, angular_accel: float) -> float:
    """τ = I·α  —  Torque from moment of inertia and angular acceleration.

    Parameters
    ----------
    inertia : float
        Moment of inertia (kg·m²).
    angular_accel : float
        Angular acceleration (rad/s²).

    Returns
    -------
    float
        Torque (N·m).
    """
    return inertia * angular_accel


def angular_velocity(theta: float, t: float) -> float:
    """ω = θ/t  —  Average angular velocity.

    Parameters
    ----------
    theta : float
        Angular displacement (rad).
    t : float
        Elapsed time (s).

    Returns
    -------
    float
        Angular velocity (rad/s).
    """
    return theta / t


def angular_acceleration(delta_omega: float, t: float) -> float:
    """α = Δω/t  —  Average angular acceleration.

    Parameters
    ----------
    delta_omega : float
        Change in angular velocity (rad/s).
    t : float
        Elapsed time (s).

    Returns
    -------
    float
        Angular acceleration (rad/s²).
    """
    return delta_omega / t


# ---- 4. Lagrangian Mechanics --------------------------------------------

def lagrangian(kinetic: float, potential: float) -> float:
    """L = T − V  —  Lagrangian of a mechanical system.

    Parameters
    ----------
    kinetic : float
        Kinetic energy T (J).
    potential : float
        Potential energy V (J).

    Returns
    -------
    float
        Lagrangian L (J).
    """
    return kinetic - potential


# ---- 5. Control Theory – PID Controller ---------------------------------

def pid_control(
    error: NDArray[np.floating],
    dt: float,
    kp: float,
    ki: float,
    kd: float,
) -> NDArray[np.floating]:
    """u(t) = Kp·e(t) + Ki·∫e dt + Kd·de/dt  —  Discrete PID controller.

    Computes the control signal at each time step given the full error
    history sampled at uniform intervals *dt*.

    Parameters
    ----------
    error : array_like, shape (N,)
        Error signal e(t) sampled at uniform time steps.
    dt : float
        Time step between samples (s).
    kp : float
        Proportional gain.
    ki : float
        Integral gain.
    kd : float
        Derivative gain.

    Returns
    -------
    ndarray, shape (N,)
        Control output u(t) at each time step.
    """
    e = np.asarray(error, dtype=float)
    integral = np.cumsum(e) * dt
    derivative = np.gradient(e, dt)
    return kp * e + ki * integral + kd * derivative


# =========================================================================
# §2  BIOLOGY / BIOPHYSICS
# =========================================================================

# ---- 6. Michaelis-Menten Kinetics ----------------------------------------

def michaelis_menten(substrate: float, vmax: float, km: float) -> float:
    """v = Vmax·[S] / (Km + [S])  —  Enzyme reaction rate.

    Parameters
    ----------
    substrate : float
        Substrate concentration [S] (mol/L).
    vmax : float
        Maximum reaction velocity (mol/(L·s)).
    km : float
        Michaelis constant (mol/L).

    Returns
    -------
    float
        Reaction velocity v (mol/(L·s)).
    """
    return vmax * substrate / (km + substrate)


# ---- 7. Hill Equation ----------------------------------------------------

def hill_equation(ligand: float, kd: float, n: float) -> float:
    """Y = [L]^n / (Kd + [L]^n)  —  Cooperative binding fraction.

    Parameters
    ----------
    ligand : float
        Ligand concentration [L].
    kd : float
        Dissociation constant Kd.
    n : float
        Hill coefficient (cooperativity).

    Returns
    -------
    float
        Fractional saturation Y (0–1).
    """
    ln = ligand ** n
    return ln / (kd + ln)


# ---- 8. Fick's Law of Diffusion -----------------------------------------

def ficks_flux(diffusivity: float, dc_dx: float) -> float:
    """J = −D·(dC/dx)  —  Diffusive flux (Fick's first law).

    Parameters
    ----------
    diffusivity : float
        Diffusion coefficient D (m²/s).
    dc_dx : float
        Concentration gradient dC/dx (mol/m⁴ or equivalent).

    Returns
    -------
    float
        Flux J (mol/(m²·s)).
    """
    return -diffusivity * dc_dx


# ---- 9. Nernst Equation -------------------------------------------------

def nernst_potential(
    ion_out: float,
    ion_in: float,
    z: int,
    temperature: float = 310.15,
) -> float:
    """E = (RT / zF)·ln([ion]_out / [ion]_in)  —  Equilibrium membrane potential.

    Parameters
    ----------
    ion_out : float
        Extracellular ion concentration.
    ion_in : float
        Intracellular ion concentration.
    z : int
        Ion valence (e.g. +1 for Na⁺, −1 for Cl⁻).
    temperature : float
        Absolute temperature in Kelvin. Default 310.15 K (≈ 37 °C).

    Returns
    -------
    float
        Nernst potential E (V).
    """
    return (R_GAS * temperature / (z * FARADAY)) * np.log(ion_out / ion_in)


# ---- 10. Hodgkin-Huxley Neuron Model ------------------------------------

def hodgkin_huxley_dv(
    v: float,
    i_ion_sum: float,
    i_ext: float,
    c_m: float,
) -> float:
    """C_m·dV/dt = −Σ I_ion + I_ext  →  dV/dt  —  Membrane voltage dynamics.

    Parameters
    ----------
    v : float
        Current membrane potential (V). *Unused in the ODE form but kept
        for interface symmetry with higher-order HH models.*
    i_ion_sum : float
        Sum of all ionic currents (A).
    i_ext : float
        Externally injected current (A).
    c_m : float
        Membrane capacitance (F).

    Returns
    -------
    float
        dV/dt  —  Rate of change of membrane potential (V/s).
    """
    return (-i_ion_sum + i_ext) / c_m


# ---- 11. Logistic Growth ------------------------------------------------

def logistic_growth(n: float, r: float, k: float) -> float:
    """dN/dt = r·N·(1 − N/K)  —  Logistic population growth rate.

    Parameters
    ----------
    n : float
        Current population size.
    r : float
        Intrinsic growth rate (1/time).
    k : float
        Carrying capacity.

    Returns
    -------
    float
        dN/dt  —  Population growth rate.
    """
    return r * n * (1.0 - n / k)


# =========================================================================
# §3  PHYSICS — THERMO, FLUIDS, DYNAMICS
# =========================================================================

# ---- 12. Conservation of Energy -----------------------------------------

def energy_change(q: float, w: float) -> float:
    """ΔE = Q − W  —  Change in internal energy (first law, closed system).

    Parameters
    ----------
    q : float
        Heat added to the system (J).
    w : float
        Work done by the system (J).

    Returns
    -------
    float
        Change in internal energy ΔE (J).
    """
    return q - w


# ---- 13. First Law of Thermodynamics (differential) --------------------

def first_law_thermo(temperature: float, ds: float, pressure: float, dv: float) -> float:
    """dU = T·dS − P·dV  —  First law of thermodynamics (differential form).

    Parameters
    ----------
    temperature : float
        Temperature T (K).
    ds : float
        Infinitesimal entropy change dS (J/K).
    pressure : float
        Pressure P (Pa).
    dv : float
        Infinitesimal volume change dV (m³).

    Returns
    -------
    float
        Infinitesimal change in internal energy dU (J).
    """
    return temperature * ds - pressure * dv


# ---- 14. Bernoulli's Equation -------------------------------------------

def bernoulli_constant(
    pressure: float,
    density: float,
    velocity: float,
    height: float,
    g: float = G_ACCEL,
) -> float:
    """P + ½ρv² + ρgh = const  —  Bernoulli's equation (incompressible flow).

    Computes the Bernoulli constant for a given point in the flow.

    Parameters
    ----------
    pressure : float
        Static pressure (Pa).
    density : float
        Fluid density ρ (kg/m³).
    velocity : float
        Flow velocity v (m/s).
    height : float
        Elevation h (m).
    g : float
        Gravitational acceleration (m/s²).

    Returns
    -------
    float
        Bernoulli constant (Pa).
    """
    return pressure + 0.5 * density * velocity ** 2 + density * g * height


def bernoulli_solve_velocity(
    p1: float, v1: float, h1: float,
    p2: float, h2: float,
    density: float,
    g: float = G_ACCEL,
) -> float:
    """Solve for v2 given two points in a Bernoulli flow.

    Parameters
    ----------
    p1, v1, h1 : float
        Pressure (Pa), velocity (m/s), and height (m) at point 1.
    p2, h2 : float
        Pressure (Pa) and height (m) at point 2.
    density : float
        Fluid density (kg/m³).
    g : float
        Gravitational acceleration (m/s²).

    Returns
    -------
    float
        Velocity v2 at point 2 (m/s).
    """
    lhs = p1 + 0.5 * density * v1 ** 2 + density * g * h1
    rhs_without_v2 = p2 + density * g * h2
    v2_sq = 2.0 * (lhs - rhs_without_v2) / density
    return np.sqrt(max(v2_sq, 0.0))


# ---- 15. Navier-Stokes helpers ------------------------------------------

def navier_stokes_acceleration(
    v: NDArray[np.floating],
    grad_v: NDArray[np.floating],
    grad_p: NDArray[np.floating],
    laplacian_v: NDArray[np.floating],
    f_body: NDArray[np.floating],
    rho: float,
    mu: float,
) -> NDArray[np.floating]:
    """ρ(∂v/∂t + v·∇v) = −∇p + μ∇²v + f  →  returns ∂v/∂t.

    This is a pointwise evaluation of the Navier-Stokes momentum equation
    for an incompressible Newtonian fluid.

    Parameters
    ----------
    v : ndarray, shape (3,)
        Velocity vector at the point.
    grad_v : ndarray, shape (3, 3)
        Velocity gradient tensor ∇v (grad_v[i][j] = ∂v_i/∂x_j).
    grad_p : ndarray, shape (3,)
        Pressure gradient ∇p.
    laplacian_v : ndarray, shape (3,)
        Laplacian of velocity ∇²v.
    f_body : ndarray, shape (3,)
        Body force per unit volume (e.g. ρg).
    rho : float
        Fluid density (kg/m³).
    mu : float
        Dynamic viscosity (Pa·s).

    Returns
    -------
    ndarray, shape (3,)
        ∂v/∂t  — Local acceleration vector (m/s²).
    """
    v = np.asarray(v, dtype=float)
    grad_v = np.asarray(grad_v, dtype=float)
    grad_p = np.asarray(grad_p, dtype=float)
    laplacian_v = np.asarray(laplacian_v, dtype=float)
    f_body = np.asarray(f_body, dtype=float)
    convective = grad_v @ v  # v·∇v
    return (-grad_p + mu * laplacian_v + f_body) / rho - convective


# ---- 16. Hooke's Law ----------------------------------------------------

def hookes_law(k: float, x: float) -> float:
    """F = −kx  —  Restoring force of a spring.

    Parameters
    ----------
    k : float
        Spring constant (N/m).
    x : float
        Displacement from equilibrium (m).

    Returns
    -------
    float
        Restoring force (N). Negative when displaced in the positive direction.
    """
    return -k * x


# ---- 17. Stress-Strain --------------------------------------------------

def stress_strain(youngs_modulus: float, strain: float) -> float:
    """σ = E·ε  —  Uniaxial linear elastic stress.

    Parameters
    ----------
    youngs_modulus : float
        Young's modulus E (Pa).
    strain : float
        Engineering strain ε (dimensionless).

    Returns
    -------
    float
        Stress σ (Pa).
    """
    return youngs_modulus * strain


# ---- 18. Fourier's Law of Heat Conduction --------------------------------

def fourier_heat_flux(conductivity: float, dt_dx: float) -> float:
    """q = −k·(dT/dx)  —  Heat flux by conduction.

    Parameters
    ----------
    conductivity : float
        Thermal conductivity k (W/(m·K)).
    dt_dx : float
        Temperature gradient dT/dx (K/m).

    Returns
    -------
    float
        Heat flux q (W/m²). Negative sign indicates flow from hot to cold.
    """
    return -conductivity * dt_dx


# =========================================================================
# §4  ROBOT KINEMATICS
# =========================================================================

# ---- 19. Forward Kinematics ---------------------------------------------

def forward_kinematics(transforms: Sequence[NDArray[np.floating]]) -> NDArray[np.floating]:
    """T = A₁·A₂·…·Aₙ  —  Forward kinematics via transformation chain.

    Parameters
    ----------
    transforms : sequence of ndarray, each shape (4, 4)
        Homogeneous transformation matrices from base to tip.

    Returns
    -------
    ndarray, shape (4, 4)
        Combined homogeneous transformation (end-effector pose).
    """
    result = np.eye(4)
    for a in transforms:
        result = result @ np.asarray(a, dtype=float)
    return result


# ---- 20. Inverse Kinematics (2-link planar) -----------------------------

def inverse_kinematics_2link(
    x: float,
    y: float,
    l1: float,
    l2: float,
    elbow_up: bool = True,
) -> Tuple[float, float]:
    """θ = f⁻¹(x, y)  —  Analytical inverse kinematics for a 2-link planar arm.

    Parameters
    ----------
    x, y : float
        Desired end-effector position in the plane (m).
    l1, l2 : float
        Lengths of link 1 and link 2 (m).
    elbow_up : bool
        If True, choose the elbow-up solution.

    Returns
    -------
    tuple of float
        (theta1, theta2) joint angles in radians.

    Raises
    ------
    ValueError
        If the target is unreachable.
    """
    d_sq = x ** 2 + y ** 2
    d = np.sqrt(d_sq)
    if d > l1 + l2 or d < abs(l1 - l2):
        raise ValueError(
            f"Target ({x}, {y}) is unreachable with link lengths l1={l1}, l2={l2}."
        )
    cos_theta2 = (d_sq - l1 ** 2 - l2 ** 2) / (2 * l1 * l2)
    cos_theta2 = np.clip(cos_theta2, -1.0, 1.0)
    sin_theta2 = np.sqrt(1.0 - cos_theta2 ** 2)
    if not elbow_up:
        sin_theta2 = -sin_theta2
    theta2 = np.arctan2(sin_theta2, cos_theta2)
    k1 = l1 + l2 * cos_theta2
    k2 = l2 * sin_theta2
    theta1 = np.arctan2(y, x) - np.arctan2(k2, k1)
    return float(theta1), float(theta2)


# ---- 21. Denavit-Hartenberg Transformation Matrix -----------------------

def dh_matrix(
    theta: float,
    d: float,
    a: float,
    alpha: float,
) -> NDArray[np.floating]:
    """Build a 4×4 homogeneous transformation from DH parameters.

    Uses the *standard* Denavit-Hartenberg convention.

    Parameters
    ----------
    theta : float
        Joint angle (rad) — rotation about z_{i-1}.
    d : float
        Link offset (m) — translation along z_{i-1}.
    a : float
        Link length (m) — translation along x_i.
    alpha : float
        Link twist (rad) — rotation about x_i.

    Returns
    -------
    ndarray, shape (4, 4)
        Homogeneous transformation matrix A_i.
    """
    ct, st = np.cos(theta), np.sin(theta)
    ca, sa = np.cos(alpha), np.sin(alpha)
    return np.array([
        [ct, -st * ca,  st * sa, a * ct],
        [st,  ct * ca, -ct * sa, a * st],
        [0.0,     sa,       ca,      d],
        [0.0,    0.0,      0.0,    1.0],
    ])


# ---- 22. Jacobian (numerical, via finite differences) -------------------

def numerical_jacobian(
    fk_func: Callable[[NDArray[np.floating]], NDArray[np.floating]],
    joint_angles: NDArray[np.floating],
    delta: float = 1e-6,
) -> NDArray[np.floating]:
    """J(θ)  —  Numerical Jacobian mapping joint velocities to task-space velocity.

    Approximates the Jacobian by central finite differences on an
    arbitrary forward-kinematics function.

    Parameters
    ----------
    fk_func : callable
        Forward kinematics function  θ → x  where x has shape (M,).
    joint_angles : array_like, shape (N,)
        Current joint configuration.
    delta : float
        Perturbation size for finite differences.

    Returns
    -------
    ndarray, shape (M, N)
        Jacobian matrix J(θ).
    """
    q = np.asarray(joint_angles, dtype=float)
    x0 = np.asarray(fk_func(q), dtype=float)
    n = q.shape[0]
    m = x0.shape[0]
    jac = np.zeros((m, n))
    for i in range(n):
        q_plus = q.copy()
        q_minus = q.copy()
        q_plus[i] += delta
        q_minus[i] -= delta
        jac[:, i] = (np.asarray(fk_func(q_plus)) - np.asarray(fk_func(q_minus))) / (2 * delta)
    return jac


# =========================================================================
# Module self-test
# =========================================================================

if __name__ == "__main__":
    print("core_equations.py — smoke test")
    print("=" * 50)

    def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
        return abs(a - b) < tol

    # Mechanics
    assert force(10.0, 3.0) == 30.0
    assert kinetic_energy(2.0, 3.0) == 9.0
    assert _approx(potential_energy(1.0, 10.0), G_ACCEL * 10.0)

    # Biology
    assert _approx(michaelis_menten(10.0, 100.0, 5.0), 100.0 * 10.0 / 15.0)

    # Hooke
    assert hookes_law(5.0, 2.0) == -10.0

    # DH matrix shape
    assert dh_matrix(0, 0, 1, 0).shape == (4, 4)

    # Forward kinematics identity
    assert np.allclose(forward_kinematics([np.eye(4), np.eye(4)]), np.eye(4))

    print("All smoke tests passed.")
