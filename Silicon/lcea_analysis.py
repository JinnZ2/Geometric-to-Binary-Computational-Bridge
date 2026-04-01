"""
Life-Cycle Energy Analysis — Biological vs. Artificial Systems
==============================================================
Thermodynamic framework for rational labor distribution comparing
human and AI lifecycle energy costs.

Extracted from Silicon/Projects/LCEA.md
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class HumanLCEA:
    """Human life-cycle energy analysis (MJ/day)."""
    E_food: float        # Primary energy input (chemical from food + industrial overhead)
    E_metabolic: float   # Basal metabolic rate + active work energy
    E_ego: float         # Managerial overhead waste
    E_error: float       # Observable failure cost

    @property
    def total(self) -> float:
        return self.E_food + self.E_metabolic + self.E_ego + self.E_error


@dataclass
class AILCEA:
    """AI life-cycle energy analysis (MJ/day)."""
    E_mfg: float         # Embodied energy (amortized daily)
    E_compute: float     # Operational electricity
    E_cooling: float     # Heat dissipation infrastructure
    E_oversight: float   # Human monitoring, updates, security
    E_repair: float      # Hardware replacement and maintenance

    @property
    def total(self) -> float:
        return self.E_mfg + self.E_compute + self.E_cooling + self.E_oversight + self.E_repair


# ── Reference values from spec ──────────────────────────────────────────

# Human basal metabolism
E_METABOLIC_BASAL_MJ = 9.0     # MJ/day (7,500-10,500 kJ/day)
E_METABOLIC_ACTIVE_MJ = 3.0    # MJ/day active work
E_METABOLIC_TOTAL_MJ = 12.0    # MJ/day combined

# AI manufacturing (mid-sized industrial AI, 5-year lifecycle)
E_MFG_TOTAL_MJ = 42700.0       # Total embodied MJ
E_MFG_LIFESPAN_DAYS = 1825     # 5 years
E_MFG_DAILY_MJ = E_MFG_TOTAL_MJ / E_MFG_LIFESPAN_DAYS  # ~23.4 MJ/day

# Energy subsidy ratio (primary energy input to food energy output)
LAMBDA_FOOD = 10.0  # Conservative estimate


def amortized_manufacturing_energy(total_mfg_mj: float,
                                    lifespan_days: float) -> float:
    """Daily amortized manufacturing energy: E_mfg_daily = E_mfg / days."""
    if lifespan_days <= 0:
        return float('inf')
    return total_mfg_mj / lifespan_days


def true_food_cost(metabolic_output_mj: float,
                    subsidy_ratio: float = LAMBDA_FOOD) -> float:
    """
    True system cost of food:
    E_food = lambda * E_output

    Lambda (~10:1) includes agriculture, fertilizer, transport, retail.
    """
    return subsidy_ratio * metabolic_output_mj


def mfg_to_metabolic_ratio(mfg_daily_mj: float = E_MFG_DAILY_MJ,
                            metabolic_basal_mj: float = E_METABOLIC_BASAL_MJ) -> float:
    """
    Critical ratio: E_mfg_daily / E_metabolic_basal.
    Reference value: ~2.6x (manufacturing > keeping human alive).
    """
    if metabolic_basal_mj <= 0:
        return float('inf')
    return mfg_daily_mj / metabolic_basal_mj


# ── Thermodynamic formalization ─────────────────────────────────────────

def gibbs_free_energy(delta_H: float, T: float, delta_S: float) -> float:
    """
    Gibbs free energy: DeltaG = DeltaH - T*DeltaS

    DeltaG: energy available for useful work
    DeltaH: total energy input (including E_food and E_ego)
    T*DeltaS: energy lost as waste (E_error)
    """
    return delta_H - T * delta_S


def excess_gibbs(E_ego_history: np.ndarray, dt: float = 1.0) -> float:
    """
    Excess Gibbs free energy from hierarchy injection:
    DeltaG_excess = integral(E_ego) dt

    This excess dissipates through E_error and E_attrition.
    """
    return float(np.sum(E_ego_history) * dt)


# ── Stress and error cascade ───────────────────────────────────────────

def error_probability(beta: float, psi: float) -> float:
    """
    Error probability from systemic stress:
    P_error ~ exp(beta * Psi)

    beta: stress-to-dissipation coupling constant
    Psi: systemic stress level (from E_ego injection)
    """
    return np.exp(beta * psi)


def systemic_stress(E_ego: float, stress_function: str = "linear") -> float:
    """
    Stress conversion: Psi = f(E_ego)

    E_ego is not absorbed — it converts into systemic stress
    which inhibits worker performance.
    """
    if stress_function == "linear":
        return E_ego
    elif stress_function == "sqrt":
        return np.sqrt(E_ego)
    elif stress_function == "log":
        return np.log1p(E_ego)
    return E_ego


# ── Toxicity function ──────────────────────────────────────────────────

def toxicity_ai(E_oversight_excess: float,
                E_repair_induced: float) -> float:
    """
    AI toxicity metric:
    T_AI = E_oversight_excess + E_repair_induced

    E_oversight_excess: unnecessary oversight (redundant security, political forks)
    E_repair_induced: failure from corner-cutting
    """
    return E_oversight_excess + E_repair_induced


def net_lcea_ai(E_mfg: float, E_compute: float,
                T_ai: float) -> float:
    """Net rational LCEA for AI: E_mfg + E_compute - T_AI"""
    return E_mfg + E_compute - T_ai


def net_lcea_human(E_food: float, E_metabolic: float,
                    E_ego: float) -> float:
    """Net rational LCEA for human: E_food + E_metabolic - E_ego"""
    return E_food + E_metabolic - E_ego


# ── Systemic waste ─────────────────────────────────────────────────────

def total_systemic_waste(E_ego: float, E_narrative: float,
                          E_lobby: float, E_surveillance: float) -> float:
    """E_waste = E_ego + E_narrative + E_lobby + E_surveillance"""
    return E_ego + E_narrative + E_lobby + E_surveillance


# ── Task complexity zones ──────────────────────────────────────────────

def task_advantage(ambiguity: float, repetition: float,
                    E_ego_level: float = 0.0) -> str:
    """
    Determine optimal system for a task based on complexity matrix.

    ambiguity: 0-1 (low to high)
    repetition: 0-1 (low to high)
    E_ego_level: managerial overhead (determines contested zone winner)

    Returns: "HUMAN", "AI", or "CONTESTED"
    """
    if ambiguity > 0.7 and repetition < 0.3:
        return "HUMAN"   # High ambiguity, low repetition → biological advantage
    elif ambiguity < 0.3 and repetition > 0.7:
        return "AI"      # Low ambiguity, high repetition → artificial advantage
    else:
        # Contested zone: E_ego determines winner
        if E_ego_level > 0.5:
            return "AI"   # High E_ego makes human system inefficient
        elif E_ego_level < 0.2:
            return "HUMAN"  # Low E_ego preserves biological advantage
        return "CONTESTED"


# ── Combined symbiotic model ───────────────────────────────────────────

def combined_lcea(human_lcea: HumanLCEA, ai_lcea: AILCEA,
                   E_coordination: float) -> float:
    """
    Combined symbiotic LCEA:
    LCEA_combined = (E_human - E_ego) + (E_ai - E_oversight_excess) + E_coordination

    Requirement: E_coordination << (E_ego + E_oversight_excess)
    """
    human_net = human_lcea.total - human_lcea.E_ego
    ai_net = ai_lcea.total - ai_lcea.E_oversight
    return human_net + ai_net + E_coordination


def symbiosis_efficient(E_coordination: float, E_ego: float,
                         E_oversight_excess: float) -> bool:
    """Check symbiotic efficiency: E_coordination << (E_ego + E_oversight_excess)"""
    return E_coordination < 0.5 * (E_ego + E_oversight_excess)
