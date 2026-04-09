# STATUS: infrastructure -- spectral overlap J computation and PI control servo
"""
spectral_servo.py – Spectral overlap computation and PI control for J stabilization.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simpson

def gaussian_spectrum(x, x0, sigma):
    """Normalized Gaussian."""
    return np.exp(-0.5 * ((x - x0)/sigma)**2) / (sigma * np.sqrt(2*np.pi))

def compute_J(wavelength, donor_em, acceptor_abs):
    """
    Spectral overlap integral J (arbitrary units, assuming wavelength in nm).
    donor_em and acceptor_abs are arrays of same length.
    """
    # J = ∫ f_D(λ) ε_A(λ) λ^4 dλ
    integrand = donor_em * acceptor_abs * wavelength**4
    return simpson(integrand, wavelength)

def stark_shift_spectrum(wavelength, spectrum, delta_lambda):
    """
    Apply a linear Stark shift (rigid shift of spectrum along wavelength axis).
    Uses linear interpolation.
    """
    shifted_wavelength = wavelength - delta_lambda
    return np.interp(wavelength, shifted_wavelength, spectrum, left=0, right=0)

class PIServo:
    """Simple PI controller with anti-windup."""
    def __init__(self, Kp, Ki, setpoint, dt, output_limits=(-np.inf, np.inf)):
        self.Kp = Kp
        self.Ki = Ki
        self.setpoint = setpoint
        self.dt = dt
        self.integral = 0.0
        self.output_limits = output_limits
    
    def update(self, measurement):
        error = self.setpoint - measurement
        self.integral += error * self.dt
        # Clamp integral to avoid windup
        output = self.Kp * error + self.Ki * self.integral
        if output > self.output_limits[1]:
            output = self.output_limits[1]
            self.integral -= error * self.dt  # back-calculation anti-windup
        elif output < self.output_limits[0]:
            output = self.output_limits[0]
            self.integral -= error * self.dt
        return output

def simulate_servo(wavelength, donor_em_nom, acceptor_abs_nom, J_target, Kp, Ki, dt,
                   total_time, aging_rate=0.01, max_stark_shift=5.0):
    """
    Simulate closed-loop control of spectral overlap J under slow drift (aging).
    Returns time array, J_history, stark_shift_history.
    """
    n_steps = int(total_time / dt)
    time = np.linspace(0, total_time, n_steps)
    J_hist = np.zeros(n_steps)
    shift_hist = np.zeros(n_steps)
    
    # Nominal spectra
    donor_em = donor_em_nom.copy()
    acceptor_abs = acceptor_abs_nom.copy()
    
    # Aging drift: red-shift both spectra linearly with time
    servo = PIServo(Kp, Ki, J_target, dt, output_limits=(-max_stark_shift, max_stark_shift))
    
    for i, t in enumerate(time):
        # Apply aging drift
        drift = aging_rate * t  # nm red-shift per unit time
        donor_current = np.interp(wavelength, wavelength - drift, donor_em_nom, left=0, right=0)
        acceptor_current = np.interp(wavelength, wavelength - drift, acceptor_abs_nom, left=0, right=0)
        
        # Measure current J (with Stark correction applied later)
        J_raw = compute_J(wavelength, donor_current, acceptor_current)
        
        # Servo correction
        stark = servo.update(J_raw)
        
        # Apply Stark shift (assume both spectra shift equally)
        donor_corrected = stark_shift_spectrum(wavelength, donor_current, stark)
        acceptor_corrected = stark_shift_spectrum(wavelength, acceptor_current, stark)
        J_corrected = compute_J(wavelength, donor_corrected, acceptor_corrected)
        
        J_hist[i] = J_corrected
        shift_hist[i] = stark
    
    return time, J_hist, shift_hist

# Demo
if __name__ == "__main__":
    # Create synthetic spectra
    wl = np.linspace(400, 600, 500)
    donor_em = gaussian_spectrum(wl, 480, 20)
    acceptor_abs = gaussian_spectrum(wl, 520, 25)
    
    J_nom = compute_J(wl, donor_em, acceptor_abs)
    print(f"Nominal J = {J_nom:.2e}")
    
    # Simulate servo
    time, J_vals, shifts = simulate_servo(
        wl, donor_em, acceptor_abs, J_target=J_nom,
        Kp=0.5, Ki=0.05, dt=0.1, total_time=50,
        aging_rate=0.05, max_stark_shift=3.0
    )
    
    plt.figure()
    plt.plot(time, J_vals, label='J (controlled)')
    plt.axhline(J_nom, color='k', linestyle='--', label='Target')
    plt.xlabel('Time')
    plt.ylabel('Spectral overlap J')
    plt.legend()
    plt.title('Servo Performance')
    plt.show()
    
    plt.figure()
    plt.plot(time, shifts, label='Stark shift (nm)')
    plt.xlabel('Time')
    plt.ylabel('Shift')
    plt.title('Control Signal')
    plt.show()
