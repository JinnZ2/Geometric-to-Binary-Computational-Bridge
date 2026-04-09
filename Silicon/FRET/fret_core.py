# STATUS: infrastructure -- Forster radius, FRET rate, FRET efficiency core equations
"""
fret_core.py – Basic FRET physics: Förster radius, rate, efficiency.
"""

import numpy as np

def R0(kappa2: float, Phi_D: float, n: float, J: float) -> float:
    """
    Förster radius in Angstroms.
    
    Parameters
    ----------
    kappa2 : float
        Orientation factor (0 to 4)
    Phi_D : float
        Donor quantum yield
    n : float
        Refractive index of medium
    J : float
        Spectral overlap integral in M^-1 cm^-1 nm^4
    
    Returns
    -------
    float
        R0 in Angstroms (Å)
    """
    # Constant prefactor from literature (units: Å)
    prefactor = 0.02108  # (9000 * ln(10) / (128 * pi^5 * N_A))^(1/6) in appropriate units
    return prefactor * (kappa2 * Phi_D * n**-4 * J)**(1/6)

def k_FRET(r: float, R0: float, tau_D: float) -> float:
    """
    FRET rate constant (inverse time).
    
    Parameters
    ----------
    r : float
        Donor-acceptor distance (same units as R0)
    R0 : float
        Förster radius (same units as r)
    tau_D : float
        Donor lifetime in absence of acceptor (e.g., ns)
    
    Returns
    -------
    float
        k_FRET in 1/(tau_D units)
    """
    return (1.0 / tau_D) * (R0 / r)**6

def E_FRET(r: float, R0: float) -> float:
    """
    FRET efficiency (dimensionless, 0 to 1).
    """
    return 1.0 / (1.0 + (r / R0)**6)

# Example usage
if __name__ == "__main__":
    # Typical CFP-YFP pair
    kappa2 = 2.0/3.0
    Phi_D = 0.6
    n = 1.4
    J = 1e15   # example value (M^-1 cm^-1 nm^4)
    R0_val = R0(kappa2, Phi_D, n, J)
    print(f"R0 = {R0_val:.1f} Å")
    
    r = 50.0  # Å
    tau_D = 2.5  # ns
    kf = k_FRET(r, R0_val, tau_D)
    E = E_FRET(r, R0_val)
    print(f"At r={r} Å: k_FRET={kf:.4f} ns^-1, E={E:.3f}")
