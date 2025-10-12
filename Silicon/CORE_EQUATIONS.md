# CORE_EQUATIONS.md  
*Part of the `SYSTEM_ENERGY_DYNAMICS` suite — base physical, biological, and mechanical equations underpinning energy and control models.*

---

## ⚙️ MECHANICS & ROBOTICS

### 1. Newton’s Laws of Motion
**F = ma**  
→ Force equals mass × acceleration

### 2. Work and Energy
**W = F · d · cos(θ)** — Work = force × displacement × angle  
**KE = ½mv²** — Kinetic Energy  
**PE = mgh** — Potential Energy

### 3. Torque and Rotational Motion
**τ = r × F** — Torque = lever arm × force  
**I = Σmr²** — Moment of Inertia  
**τ = Iα** — Torque = Inertia × Angular Acceleration  
**ω = θ/t**, **α = Δω/t** — Angular velocity and acceleration

### 4. Lagrangian Mechanics (Control Applications)
**L = T - V** — Lagrangian = Kinetic − Potential Energy  
**d/dt(∂L/∂ẋᵢ) - ∂L/∂xᵢ = 0** — Euler-Lagrange Equation (motion basis for robotic arms)

### 5. Control Theory
**PID Controller:**  
`u(t) = Kₚe(t) + Kᵢ∫e(t)dt + K_d(de/dt)`  
Used for feedback control in actuators and autonomous systems.

---

## 🧬 BIOLOGY / BIOPHYSICS

### 6. Michaelis–Menten Kinetics
**v = (Vmax [S]) / (Km + [S])**  
Describes enzyme-catalyzed reaction rate vs substrate concentration.

### 7. Hill Equation (Cooperative Binding)
**Y = [L]ⁿ / (K_d + [L]ⁿ)**  
Models cooperative ligand binding (e.g., hemoglobin O₂ affinity).

### 8. Fick’s Law of Diffusion
**J = -D(dC/dx)**  
Flux = − Diffusivity × Concentration Gradient.

### 9. Nernst Equation (Membrane Potential)
**E = (RT/zF) · ln([ion]_out / [ion]_in)**  
Electrochemical equilibrium potential for ion species.

### 10. Hodgkin–Huxley Neuron Model
**C_m dV/dt = - ∑ I_ion + I_ext**  
Captures neuronal voltage dynamics through ion currents.

### 11. Logistic Growth
**dN/dt = rN(1 - N/K)**  
Population dynamics — self-limiting exponential model.

---

## 🔬 PHYSICS (THERMO, FLUIDS, DYNAMICS)

### 12. Conservation of Energy
**ΔE = Q - W**  
Change in internal energy = heat added − work done.

### 13. First Law of Thermodynamics
**dU = TdS - PdV**

### 14. Bernoulli’s Equation (Fluid Flow)
**P + ½ρv² + ρgh = constant**

### 15. Navier–Stokes (Fluid Dynamics)
**ρ(∂v/∂t + v·∇v) = -∇p + μ∇²v + f**

### 16. Hooke’s Law (Elasticity)
**F = -kx**

### 17. Stress–Strain Relation
**σ = Eε**  
Stress = Young’s Modulus × Strain.

### 18. Fourier’s Law (Heat Conduction)
**q = -k dT/dx**

---

## 🤖 ROBOT KINEMATICS

### 19. Forward Kinematics
**T = A₁ · A₂ · ... · Aₙ**  
Transformation-matrix chain from base to end-effector pose.

### 20. Inverse Kinematics
**θ = f⁻¹(x, y, z)**  
Solves joint angles from desired end-effector position.

### 21. Denavit–Hartenberg Parameters
Defines each joint by: **θ, d, a, α**  
→ Used to build homogeneous transformation matrices.

### 22. Jacobian Matrix (Velocity Mapping)
**J(θ) · ẋ = v**  
Maps joint velocities to end-effector linear/angular velocity.

---

## 🧠 NOTES

- This core set anchors energy-flow and motion models in the `SYSTEM_ENERGY_DYNAMICS` framework.  
- Equations feed directly into thermodynamic, biological, and mechanical analyses.  
- Especially relevant for **soft robotics**, **prosthetic design**, **biomechanics**, and **AI-driven control systems**.  

**Reference Link:**  
→ [SYSTEM_ENERGY_DYNAMICS.md](../systems/SYSTEM_ENERGY_DYNAMICS.md)

---
