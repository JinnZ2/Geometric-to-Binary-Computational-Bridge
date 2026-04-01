"""
Energy Framework: Cross-Domain Energy Comparison
=================================================

Extracted from Silicon/SYSTEM_ENERGY_DYNAMICS.md

Implements metabolic equations (aerobic respiration), restoration rates,
Q10 temperature coefficients, thermoregulation costs, battery/mechanical
efficiency, and a unified cross-domain comparison framework for
biological, mechanical, and AI energy systems.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ATP_YIELD_PER_GLUCOSE = (30, 32)          # range
ENERGY_PER_ATP_KJ_MOL = 30.5             # kJ/mol
BIOLOGICAL_EFFICIENCY_RANGE = (0.34, 0.40)  # 34-40 %

# Comparative efficiency table (from Section 5.2)
SYSTEM_SPECS = {
    "human_biological": {
        "energy_density_J_per_kg": 3e6,
        "efficiency": (0.34, 0.40),
        "rest_cycle_hours_per_day": 8.0,
    },
    "ai_digital": {
        "energy_density_J_per_kg": 1e8,   # battery
        "efficiency": (0.10, 0.20),
        "rest_cycle_hours_per_day": (1.0, 3.0),
    },
    "mechanical_industrial": {
        "energy_density_J_per_kg": None,   # variable
        "efficiency": None,
        "rest_cycle_hours_per_day": None,
    },
}


# ---------------------------------------------------------------------------
# 2.1  Core Metabolic Equation  (aerobic respiration)
# ---------------------------------------------------------------------------

def aerobic_respiration_energy(n_glucose: float = 1.0,
                                atp_per_glucose: int = 32) -> float:
    """Return total energy yield (kJ) from *n_glucose* molecules.

    C6H12O6 + 6O2  -->  6CO2 + 6H2O + Energy
    Each glucose yields ~30-32 ATP; each ATP ~ 30.5 kJ/mol.
    """
    return n_glucose * atp_per_glucose * ENERGY_PER_ATP_KJ_MOL


def biological_efficiency(thermoregulation_fraction: float = 0.0) -> float:
    """Effective biological efficiency accounting for thermoregulation cost.

    Base efficiency is ~34-40 %; *thermoregulation_fraction* (0-1) reduces it.
    """
    base = np.mean(BIOLOGICAL_EFFICIENCY_RANGE)
    return base * (1.0 - np.clip(thermoregulation_fraction, 0.0, 1.0))


# ---------------------------------------------------------------------------
# 2.2  Rest and Recharge -- Energy Restoration Rate
# ---------------------------------------------------------------------------

def energy_restoration(e_max: float, e_t: float, t: float,
                       tau_r: float) -> float:
    """Metabolic energy restoration rate.

    E_r = (E_max - E_t) * exp(-t / tau_r)

    Parameters
    ----------
    e_max : float  -- maximum energy capacity
    e_t   : float  -- energy at time *t*
    t     : float  -- elapsed time (hours)
    tau_r : float  -- recovery time constant (hours)
    """
    return (e_max - e_t) * np.exp(-t / tau_r)


def restored_energy_at(e_max: float, e_start: float, t: float,
                       tau_r: float) -> float:
    """Energy level after resting for *t* hours starting at *e_start*.

    Integrates the restoration model:  E(t) = E_max - (E_max - E_start) * exp(-t / tau_r)
    """
    return e_max - (e_max - e_start) * np.exp(-t / tau_r)


# ---------------------------------------------------------------------------
# 2.3  Climate Modulation -- Q10 Temperature Coefficient
# ---------------------------------------------------------------------------

def q10_metabolic_rate(base_rate: float, delta_T: float,
                       q10: float = 2.0) -> float:
    """Metabolic rate adjusted by Q10 rule.

    Rate doubles for every 10 deg-C rise (within biological tolerance).

    Parameters
    ----------
    base_rate : float  -- rate at reference temperature
    delta_T   : float  -- temperature difference from reference (deg C)
    q10       : float  -- Q10 coefficient (default 2.0)
    """
    return base_rate * q10 ** (delta_T / 10.0)


def thermoregulation_cost(t_env: float, t_core: float,
                          k_t: float = 0.01) -> float:
    """Thermoregulation energy cost.

    E_T = k_T * (T_env - T_core)^2

    Parameters
    ----------
    t_env  : float  -- environmental temperature (deg C)
    t_core : float  -- core body temperature (deg C)
    k_t    : float  -- insulation/adaptation coefficient
    """
    return k_t * (t_env - t_core) ** 2


# ---------------------------------------------------------------------------
# 3.  Mechanical / AI Energy Framework
# ---------------------------------------------------------------------------

def energy_per_bit(capacitance: float, voltage: float) -> float:
    """Energy per digital operation: E_bit = C * V^2 (Joules)."""
    return capacitance * voltage ** 2


def battery_efficiency(e_out: float, e_in: float) -> float:
    """Battery charge/discharge efficiency (fraction).

    eta_charge = E_out / E_in   (typically 0.85 - 0.95)
    """
    if e_in == 0:
        return 0.0
    return e_out / e_in


def thermal_loss(current: float, resistance: float, time: float) -> float:
    """Ohmic thermal loss: E_loss = I^2 * R * t (Joules)."""
    return current ** 2 * resistance * time


def thermal_degradation(t_env: float, t_opt: float,
                        alpha: float = 0.001) -> float:
    """Thermal degradation energy penalty for mechanical/AI systems.

    delta_E = alpha * (T_env - T_opt)^2
    """
    return alpha * (t_env - t_opt) ** 2


# ---------------------------------------------------------------------------
# 4.  Cultural and Adaptive Modifiers
# ---------------------------------------------------------------------------

def basal_metabolic_rate(e0: float, f_climate: float = 1.0,
                         f_adapt: float = 1.0) -> float:
    """Adjusted BMR: E_BMR = E_0 * f_climate * f_adapt."""
    return e0 * f_climate * f_adapt


def social_infrastructure_cost(n_agents: int, c_comm: float,
                               c_maint: float) -> float:
    """Coordination overhead: E_social = N * (C_comm + C_maint)."""
    return n_agents * (c_comm + c_maint)


def cognitive_load_cost(n_tasks: int, k_focus: float = 1.0) -> float:
    """Decision-fatigue energy: E_cog = k_focus * ln(S).

    Parameters
    ----------
    n_tasks : int    -- number of simultaneous cognitive tasks (>= 1)
    k_focus : float  -- focus coefficient
    """
    return k_focus * np.log(max(n_tasks, 1))


# ---------------------------------------------------------------------------
# 5.  Cross-Domain Comparison Framework
# ---------------------------------------------------------------------------

@dataclass
class EnergySystem:
    """Unified energy model for any system type (biological, AI, mechanical).

    Attributes match the total-energy equation from Section 5.1:
        E_total = E_core + E_maint + E_social + E_env
    """
    name: str
    system_type: str            # "biological", "ai", "mechanical"
    e_core: float = 0.0        # core operational energy (J)
    e_maint: float = 0.0       # maintenance / recharge energy (J)
    e_social: float = 0.0      # coordination overhead (J)
    e_env: float = 0.0         # environmental adaptation cost (J)

    @property
    def e_total(self) -> float:
        """E_total = E_core + E_maint + E_social + E_env"""
        return self.e_core + self.e_maint + self.e_social + self.e_env


def compare_systems(*systems: EnergySystem) -> dict:
    """Return a comparison dict keyed by system name with totals and ratios.

    The ratio is relative to the most efficient (lowest E_total) system.
    """
    totals = {s.name: s.e_total for s in systems}
    if not totals:
        return {}
    min_total = min(totals.values()) or 1.0
    return {
        name: {"e_total": total, "ratio_to_best": total / min_total}
        for name, total in totals.items()
    }


# ---------------------------------------------------------------------------
# Convenience: build a biological system from first principles
# ---------------------------------------------------------------------------

def build_biological_system(
    name: str = "human",
    n_glucose: float = 1.0,
    t_env: float = 25.0,
    t_core: float = 37.0,
    k_t: float = 0.01,
    n_agents: int = 1,
    c_comm: float = 0.0,
    c_maint: float = 0.0,
) -> EnergySystem:
    """Construct an EnergySystem for a biological organism."""
    e_core = aerobic_respiration_energy(n_glucose) * 1000  # kJ -> J
    e_env = thermoregulation_cost(t_env, t_core, k_t)
    e_social = social_infrastructure_cost(n_agents, c_comm, c_maint)
    return EnergySystem(
        name=name,
        system_type="biological",
        e_core=e_core,
        e_maint=0.0,
        e_social=e_social,
        e_env=e_env,
    )


def build_ai_system(
    name: str = "gpu_node",
    n_operations: float = 1e9,
    capacitance: float = 1e-12,
    voltage: float = 1.0,
    t_env: float = 25.0,
    t_opt: float = 25.0,
    alpha: float = 0.001,
    n_agents: int = 1,
    c_comm: float = 0.0,
    c_maint: float = 0.0,
) -> EnergySystem:
    """Construct an EnergySystem for an AI / digital system."""
    e_core = n_operations * energy_per_bit(capacitance, voltage)
    e_env = thermal_degradation(t_env, t_opt, alpha)
    e_social = social_infrastructure_cost(n_agents, c_comm, c_maint)
    return EnergySystem(
        name=name,
        system_type="ai",
        e_core=e_core,
        e_maint=0.0,
        e_social=e_social,
        e_env=e_env,
    )


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Energy Framework Self-Test ===\n")

    # Aerobic respiration
    e = aerobic_respiration_energy(1.0, 32)
    print(f"1 mol glucose -> {e:.1f} kJ  (32 ATP x 30.5 kJ/mol)")

    # Restoration curve
    times = [0, 2, 4, 8]
    for t in times:
        level = restored_energy_at(100.0, 40.0, t, tau_r=3.0)
        print(f"  Restoration at t={t}h: {level:.1f}")

    # Q10
    rate = q10_metabolic_rate(1.0, 10.0)
    print(f"Q10 rate at +10C: {rate:.2f}x  (expect 2.0)")

    # Thermoregulation
    cost = thermoregulation_cost(5.0, 37.0, k_t=0.01)
    print(f"Thermoreg cost at 5C env, 37C core: {cost:.2f}")

    # Digital op energy
    e_op = energy_per_bit(1e-15, 0.7)
    print(f"Energy per op (1fF, 0.7V): {e_op:.2e} J  ({e_op*1e12:.2f} pJ)")

    # Battery efficiency
    eta = battery_efficiency(90, 100)
    print(f"Battery efficiency: {eta*100:.0f}%")

    # Social overhead
    e_s = social_infrastructure_cost(100, 0.5, 0.3)
    print(f"Social overhead (100 agents): {e_s:.1f}")

    # Cognitive load
    e_c = cognitive_load_cost(5, k_focus=1.0)
    print(f"Cognitive load (5 tasks): {e_c:.3f}")

    # Cross-domain comparison
    bio = build_biological_system(t_env=0.0)
    ai = build_ai_system()
    comparison = compare_systems(bio, ai)
    print(f"\nCross-domain comparison:")
    for name, data in comparison.items():
        print(f"  {name}: E_total={data['e_total']:.4g}, ratio={data['ratio_to_best']:.2f}")

    print("\nAll checks passed.")
