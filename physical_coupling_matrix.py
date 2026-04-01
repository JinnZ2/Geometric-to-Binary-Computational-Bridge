# physical_coupling_matrix.py
# First-Principles Energy Coupling
# Interactions between fundamental physical fields

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import math

# ---------------------------
# 1. Fundamental Nodes (Physical Fields)
# ---------------------------

class PhysicalNode:
    """A fundamental physical field that carries or transfers energy."""
    
    def __init__(self, name: str, description: str, entropy_rank: int):
        self.name = name
        self.description = description
        self.entropy_rank = entropy_rank  # 0 = lowest entropy, higher = more degraded
        self.energy = 0.0  # MW

# Define the physical nodes
nodes = {
    "EM": PhysicalNode("EM", "Organized electromagnetic transport (grid)", entropy_rank=0),
    "M": PhysicalNode("M", "Structured mechanical motion", entropy_rank=1),
    "C": PhysicalNode("C", "Chemical potential (bonds, gradients)", entropy_rank=2),
    "T": PhysicalNode("T", "Thermal reservoir (disordered EM)", entropy_rank=3),
    "R": PhysicalNode("R", "Radiative field (solar, IR)", entropy_rank=1),
    "F": PhysicalNode("F", "Fluid dynamics (wind, pressure)", entropy_rank=2),
    "G": PhysicalNode("G", "Gravitational potential", entropy_rank=0),
    "K": PhysicalNode("K", "Kinetic (Coriolis, rotation)", entropy_rank=1),
}

node_list = ["EM", "M", "C", "T", "R", "F", "G", "K"]
n_nodes = len(node_list)

# ---------------------------
# 2. Coupling Matrix (Physical Interactions)
# ---------------------------

class PhysicalCouplingMatrix:
    """
    Coupling matrix based on fundamental physics.
    Each entry represents the maximum theoretical efficiency of converting
    one physical field to another.
    """
    IDX = {name: i for i, name in enumerate(node_list)}

    def __init__(self):
        self.matrix = np.zeros((n_nodes, n_nodes))
        self._build_matrix()
    
    def _build_matrix(self):
        """Build coupling matrix from first principles."""
        
        idx = self.IDX
        
        # ========== EM (Organized Electromagnetic) ==========
        # EM can be converted to many forms with high efficiency
        
        # EM → M (electric motor): 90-95% efficient
        self.matrix[idx["EM"], idx["M"]] = 0.92
        
        # EM → C (electrolysis, battery charging): 70-85%
        self.matrix[idx["EM"], idx["C"]] = 0.80
        
        # EM → T (resistive heating): ~100% (but degrades energy)
        self.matrix[idx["EM"], idx["T"]] = 0.98
        
        # EM → R (radio transmission): 50-70%
        self.matrix[idx["EM"], idx["R"]] = 0.60
        
        # ========== M (Mechanical Motion) ==========
        # M can be converted to EM (generator), T (friction), etc.
        
        # M → EM (generator): 85-95% efficient
        self.matrix[idx["M"], idx["EM"]] = 0.90
        
        # M → T (friction, braking): near 100% (but degrades)
        self.matrix[idx["M"], idx["T"]] = 0.95
        
        # M → C (compression, mechanical work): 70-85%
        self.matrix[idx["M"], idx["C"]] = 0.75
        
        # M → F (pump, fan): 80-90%
        self.matrix[idx["M"], idx["F"]] = 0.85
        
        # ========== C (Chemical Potential) ==========
        # Chemical energy can be converted to thermal (combustion), EM (fuel cell), etc.
        
        # C → T (combustion, metabolism): 90-95%
        self.matrix[idx["C"], idx["T"]] = 0.93
        
        # C → EM (fuel cell, battery): 50-70%
        self.matrix[idx["C"], idx["EM"]] = 0.65
        
        # C → M (engine): 25-40% (limited by Carnot)
        self.matrix[idx["C"], idx["M"]] = 0.35
        
        # ========== T (Thermal Reservoir) ==========
        # Thermal is degraded; conversions require gradient
        
        # T → EM (thermoelectric, Carnot): limited by Carnot efficiency
        # We'll set base efficiency at 10-15% (typical)
        self.matrix[idx["T"], idx["EM"]] = 0.12
        
        # T → M (heat engine): Carnot limit (ΔT/Thot)
        # We'll set a moderate value
        self.matrix[idx["T"], idx["M"]] = 0.20
        
        # T → R (thermal radiation): 50-80%
        self.matrix[idx["T"], idx["R"]] = 0.65
        
        # ========== R (Radiative Field) ==========
        # Solar radiation can be converted to EM (PV), T (thermal), C (photosynthesis)
        
        # R → EM (photovoltaic): 15-25%
        self.matrix[idx["R"], idx["EM"]] = 0.20
        
        # R → T (solar thermal): 60-80%
        self.matrix[idx["R"], idx["T"]] = 0.70
        
        # R → C (photosynthesis): 3-6%
        self.matrix[idx["R"], idx["C"]] = 0.05
        
        # ========== F (Fluid Dynamics) ==========
        # Wind, water flow can be converted to M (turbine), T (friction)
        
        # F → M (turbine): 40-60% (Betz limit)
        self.matrix[idx["F"], idx["M"]] = 0.50
        
        # F → T (friction, viscosity): near 100%
        self.matrix[idx["F"], idx["T"]] = 0.90
        
        # F → EM (MHD, rare): 10-20%
        self.matrix[idx["F"], idx["EM"]] = 0.15
        
        # ========== G (Gravitational) ==========
        # Gravity can be converted to M (hydro), T (potential → heat)

        # G → M (falling mass, hydro): 80-95%
        self.matrix[idx["G"], idx["M"]] = 0.90

        # G → T (tidal friction): near 100%
        self.matrix[idx["G"], idx["T"]] = 0.95

        # G → EM (gravitational potential → hydroelectric → grid): 70-85%
        # Two-step path G→M→EM is ~81%, but direct hydro turbine+generator
        # systems achieve 80-85% end-to-end.
        self.matrix[idx["G"], idx["EM"]] = 0.82

        # EM → G (electromagnetic pump/lift, crane, elevator): 75-90%
        # Electric motors lifting mass against gravity — limited by motor
        # efficiency and friction losses.
        self.matrix[idx["EM"], idx["G"]] = 0.85

        # C → G (chemical energy → gravitational potential): 25-35%
        # Biological: organisms climbing, sap rising. Mechanical: combustion
        # engine lifting mass. Limited by Carnot + mechanical chain.
        self.matrix[idx["C"], idx["G"]] = 0.30

        # G → C (gravitational pressure → chemical bonds): 5-15%
        # Geological: pressure-driven mineral formation, deep-sea
        # chemosynthesis driven by hydrostatic pressure gradients.
        self.matrix[idx["G"], idx["C"]] = 0.10
        
        # ========== K (Kinetic/Coriolis) ==========
        # Rotation, Coriolis shapes flows but doesn't directly convert
        
        # K shapes F (atmospheric circulation)
        self.matrix[idx["K"], idx["F"]] = 0.00  # Not a conversion, a modulator
        
        # K can be converted to EM (generator) via angular momentum
        self.matrix[idx["K"], idx["EM"]] = 0.85
    
    def get_efficiency(self, from_node: str, to_node: str) -> float:
        """Get coupling efficiency between two physical nodes."""
        return self.matrix[self.IDX[from_node], self.IDX[to_node]]
    
    def get_physical_path(self, from_node: str, to_node: str, 
                          intermediate: str = None) -> float:
        """Calculate efficiency of multi-step conversion."""
        if intermediate:
            return (self.get_efficiency(from_node, intermediate) * 
                    self.get_efficiency(intermediate, to_node))
        return self.get_efficiency(from_node, to_node)


# ---------------------------
# 3. Source Terms (External Inputs)
# ---------------------------

@dataclass
class SourceTerm:
    """External energy input to the system."""
    node: str
    power_mw: float
    description: str
    variability: float  # 0-1, 1 = constant


class SourceTerms:
    """Define external sources based on location and conditions."""
    
    @staticmethod
    def desert_coast_sources() -> List[SourceTerm]:
        """Sources typical of desert coastal location."""
        return [
            SourceTerm("R", 50.0, "Solar radiation (peak)", variability=0.7),
            SourceTerm("F", 15.0, "Coastal winds", variability=0.5),
            SourceTerm("G", 5.0, "Tidal gravitational", variability=0.3),
            SourceTerm("C", 2.0, "Biomass potential", variability=0.4),
        ]
    
    @staticmethod
    def geothermal_sources() -> List[SourceTerm]:
        """Geothermal sources from bedrock."""
        return [
            SourceTerm("T", 60.0, "Geothermal heat flux", variability=0.95),
        ]
    
    @staticmethod
    def all_sources() -> List[SourceTerm]:
        """Combine all realistic sources."""
        sources = SourceTerms.desert_coast_sources()
        sources.extend(SourceTerms.geothermal_sources())
        return sources


# ---------------------------
# 4. Coupling Modulators
# ---------------------------

@dataclass
class CouplingModulator:
    """
    A physical effect that modulates coupling efficiency between nodes.
    These are NOT nodes—they shape the interactions.
    """
    name: str
    description: str
    affects: List[Tuple[str, str]]  # (from_node, to_node)
    modulation_function: callable


class Modulators:
    """
    Physical effects that modulate coupling efficiency.
    Includes harmonic resonance, Coriolis, gravity gradients, etc.
    """
    
    @staticmethod
    def harmonic_resonance(frequency: float, natural_freq: float) -> float:
        """Harmonic resonance multiplier (1 at resonance, <1 elsewhere)."""
        if frequency == 0:
            return 1.0
        ratio = frequency / natural_freq
        # Lorentzian resonance peak
        return 1.0 / (1.0 + 10.0 * (ratio - 1.0)**2)
    
    @staticmethod
    def coriolis_effect(latitude: float, velocity: float) -> float:
        """Coriolis effect modulates fluid dynamics (F) to mechanical (M)."""
        # Maximum at poles (90°), zero at equator
        coriolis = abs(math.sin(math.radians(latitude)))
        return min(1.0, coriolis * (1 + velocity / 50))
    
    @staticmethod
    def gravitational_gradient(delta_z: float) -> float:
        """Gravity gradient affects gravitational to mechanical conversion."""
        # Steeper gradient = more potential
        return min(1.0, delta_z / 100)
    
    @staticmethod
    def thermal_gradient(delta_t: float, source_temp: float) -> float:
        """Thermal gradient affects T → EM and T → M conversions."""
        if source_temp <= 0:
            return 0
        carnot_limit = 1 - (300 / (source_temp + 273))  # Cold sink at 300K
        actual_gradient = min(1.0, delta_t / 500)
        return carnot_limit * actual_gradient
    
    @staticmethod
    def get_all_modulators() -> List[CouplingModulator]:
        """Return all coupling modulators."""
        return [
            CouplingModulator(
                "Harmonic Resonance",
                "Resonant coupling improves mechanical ↔ EM conversion",
                [("M", "EM"), ("EM", "M")],
                lambda f=60: Modulators.harmonic_resonance(f, 60)
            ),
            CouplingModulator(
                "Coriolis Effect",
                "Planetary rotation shapes fluid dynamics",
                [("F", "M")],
                lambda lat=30, v=10: Modulators.coriolis_effect(lat, v)
            ),
            CouplingModulator(
                "Gravity Gradient",
                "Elevation difference enables gravitational energy",
                [("G", "M")],
                lambda dz=50: Modulators.gravitational_gradient(dz)
            ),
            CouplingModulator(
                "Thermal Gradient",
                "Temperature difference enables heat engine efficiency",
                [("T", "EM"), ("T", "M")],
                lambda dt=200, T_hot=500: Modulators.thermal_gradient(dt, T_hot)
            ),
        ]


# ---------------------------
# 5. Physical Energy Flow Model
# ---------------------------

class PhysicalEnergyFlow:
    """
    Energy flow model based on physical interactions.
    Follows: Energy is conserved; utility is lost when structure collapses into thermal equilibrium.
    """
    
    def __init__(self, coupling_matrix: PhysicalCouplingMatrix, sources: List[SourceTerm]):
        self.coupling = coupling_matrix
        self.sources = sources
        self.energy = {node: 0.0 for node in node_list}
        self._initialize_sources()
        
    def _initialize_sources(self):
        """Apply external sources."""
        for source in self.sources:
            self.energy[source.node] += source.power_mw
    
    def _modulated_efficiency(self, from_node: str, to_node: str,
                               modulators: List[CouplingModulator] = None) -> float:
        """Get coupling efficiency, scaled by any active modulators."""
        eff = self.coupling.get_efficiency(from_node, to_node)
        if eff == 0 or not modulators:
            return eff
        for mod in modulators:
            if (from_node, to_node) in mod.affects:
                eff *= mod.modulation_function()
        return min(eff, 1.0)

    def apply_couplings(self, modulators: List[CouplingModulator] = None):
        """
        Propagate energy through couplings.
        Energy flows from higher-entropy to lower-entropy (when possible),
        but more importantly, it degrades toward thermal equilibrium.
        """
        thermal_accumulation = 0.0
        structured_nodes = ["EM", "M", "C", "R", "F", "G", "K"]

        # Convert structured forms to other structured forms
        for from_node in structured_nodes:
            if self.energy[from_node] <= 0:
                continue

            for to_node in structured_nodes:
                if from_node == to_node:
                    continue

                eff = self._modulated_efficiency(from_node, to_node, modulators)
                if eff > 0:
                    transfer = min(self.energy[from_node],
                                   self.energy[from_node] * eff * 0.1)
                    self.energy[from_node] -= transfer
                    self.energy[to_node] += transfer

        # Convert structured to thermal (degradation)
        for from_node in structured_nodes:
            if self.energy[from_node] <= 0:
                continue

            eff_to_thermal = self._modulated_efficiency(from_node, "T", modulators)
            if eff_to_thermal > 0:
                transfer = min(self.energy[from_node],
                               self.energy[from_node] * eff_to_thermal * 0.2)
                self.energy[from_node] -= transfer
                thermal_accumulation += transfer

        # Convert thermal back to structured (limited by Carnot)
        thermal_available = self.energy["T"] + thermal_accumulation

        for to_node in structured_nodes:
            eff = self._modulated_efficiency("T", to_node, modulators)
            if eff > 0:
                max_transfer = min(thermal_available,
                                   thermal_available * eff * 0.05)
                self.energy[to_node] += max_transfer
                thermal_available -= max_transfer

        self.energy["T"] = thermal_available
    
    def iterate(self, iterations: int = 50, modulators: List[CouplingModulator] = None):
        """Iterate the energy flow model until convergence."""
        history = []
        
        for i in range(iterations):
            self.apply_couplings(modulators)
            history.append(self.energy.copy())
            
            # Check convergence
            if i > 5:
                delta = sum(abs(history[-1][k] - history[-2][k]) for k in node_list)
                if delta < 0.01:
                    break
        
        return history
    
    def get_results(self) -> Dict:
        """Get final energy distribution."""
        # Convert to original node naming for comparison
        mapping = {
            "EM": "EM (Grid)",
            "M": "M (Mobility)",
            "C": "C (Chemical/Biological)",
            "T": "T (Thermal)",
            "R": "R (Radiative)",
            "F": "F (Fluid)",
            "G": "G (Gravitational)",
            "K": "K (Kinetic/Coriolis)"
        }
        
        result = {}
        for node, energy in self.energy.items():
            result[mapping.get(node, node)] = energy
        
        return {
            "distribution": result,
            "total_power": sum(self.energy.values()),
            "thermal_power": self.energy["T"],
            "structured_power": sum(self.energy[n] for n in ["EM", "M", "C", "R", "F", "G", "K"])
        }


# ---------------------------
# 6. Run Physical Model
# ---------------------------

def run_physical_model():
    """Run the first-principles physical coupling model."""
    
    print("=" * 80)
    print("PHYSICAL COUPLING MATRIX")
    print("First-Principles Energy Flow Between Fundamental Fields")
    print("=" * 80)
    
    # Initialize
    coupling = PhysicalCouplingMatrix()
    sources = SourceTerms.all_sources()
    flow = PhysicalEnergyFlow(coupling, sources)
    
    # Display coupling matrix
    print("\n" + "=" * 60)
    print("COUPLING EFFICIENCIES (Source → Target)")
    print("=" * 60)
    
    print("\n   " + "".join(f"{n:>8}" for n in node_list))
    for i, from_node in enumerate(node_list):
        row = [coupling.matrix[i, j] for j in range(n_nodes)]
        print(f"{from_node:3} " + "".join(f"{v:>8.2f}" for v in row))
    
    # Display sources
    print("\n" + "=" * 60)
    print("EXTERNAL SOURCES")
    print("=" * 60)
    
    total_source = 0
    for source in sources:
        print(f"  {source.node}: {source.power_mw:.1f} MW ({source.description})")
        total_source += source.power_mw
    print(f"  Total: {total_source:.1f} MW")
    
    # Run the flow model
    print("\n" + "=" * 60)
    print("ENERGY FLOW CONVERGENCE")
    print("=" * 60)
    
    history = flow.iterate(iterations=50)
    results = flow.get_results()
    
    print(f"\nFinal Distribution:")
    for node, energy in sorted(results["distribution"].items(), key=lambda x: -x[1]):
        bar = "█" * int(energy * 0.5)
        print(f"  {node:20} {energy:6.2f} MW {bar}")
    
    print(f"\nTotal Power: {results['total_power']:.2f} MW")
    print(f"Thermal Reservoir: {results['thermal_power']:.2f} MW")
    print(f"Structured Power: {results['structured_power']:.2f} MW")
    
    # Compare to original model
    print("\n" + "=" * 60)
    print("COMPARISON: Physical vs Original Model")
    print("=" * 60)
    
    original_dist = {
        "G (Grid)": 3.24,
        "T (Thermal)": 4.85,
        "M (Mobility)": 0.81,
        "B (Biological)": 2.34,
        "A (Ambient)": 6.46
    }
    
    print("\nOriginal Model (from matrix):")
    for node, energy in sorted(original_dist.items(), key=lambda x: -x[1]):
        bar = "█" * int(energy * 0.5)
        print(f"  {node:20} {energy:6.2f} MW {bar}")
    
    print("\nPhysical Model (first principles):")
    for node, energy in sorted(results["distribution"].items(), key=lambda x: -x[1]):
        bar = "█" * int(energy * 0.5)
        print(f"  {node:20} {energy:6.2f} MW {bar}")
    
    # Physical interpretation
    print("\n" + "=" * 80)
    print("💡 PHYSICAL INTERPRETATION")
    print("=" * 80)
    
    print("""
    ENERGY DEGRADATION PRINCIPLE:
    
    Energy is conserved; utility is lost when structure collapses into thermal equilibrium.
    
    The physical model tracks:
        • Structured forms (EM, M, C, R, F, G, K) — can do work
        • Thermal reservoir (T) — degraded, limited work potential
    
    KEY INSIGHTS:
    
    1. THERMAL IS A RESERVOIR, NOT A SOURCE
       • T can only do work when there's a temperature gradient
       • Carnot limit applies to all T → structured conversions
    
    2. COUPLINGS ARE PHYSICAL, NOT ARBITRARY
       • EM ↔ M: up to 95% (motor/generator)
       • C → M: 35% (Carnot-limited heat engine)
       • R → EM: 20% (PV limit)
       • F → M: 50% (Betz limit)
    
    3. MODULATORS SHAPE EFFICIENCY
       • Harmonic resonance improves M ↔ EM
       • Coriolis shapes fluid paths (F)
       • Thermal gradient limits T → structured
    
    4. YOUR EARLIER CONCEPTS NOW HAVE PHYSICAL BASIS
    
       Concept          Physical Node     Coupling
       ─────────────────────────────────────────────
       Piezo roads      M → EM            (mechanical to EM)
       Biogas           C → T → EM        (chemical to thermal to EM)
       Solar PV         R → EM            (radiative to EM)
       Solar thermal    R → T → EM        (radiative to thermal to EM)
       Wind             F → M → EM        (fluid to mechanical to EM)
       Sand battery     T ↔ T             (thermal storage, time shifting)
    
    5. WHAT THE ORIGINAL MODEL HID
    
       Original model had "A (Ambient)" as a catch-all.
       Physical model splits it into:
           • R (Radiative) — solar input
           • F (Fluid) — wind, pressure
           • T (Thermal) — ambient temperature
    
       This prevents invalid couplings like "ambient → grid" without mechanism.
    
    6. THE TRUE OPTIMIZATION
    
       System is not maximizing energy.
       System is MINIMIZING irreversible flow into the thermal reservoir.
    
       "No waste" is imprecise.
       "Energy is conserved; utility is lost when structure collapses into thermal equilibrium" is exact.
    
    7. NEXT STEPS
    
       • Implement modulators in the flow model
       • Add time-dependent gradients (diurnal cycles)
       • Calculate entropy generation rate
       • Optimize for minimum entropy production
    """)
    
    return flow, results

# ---------------------------
# 7. Node-to-Interaction Mapping
# ---------------------------
#
# NODE       REFRAME                           PRIMARY INTERACTION        SECONDARY
# -----      -------                           -------------------        ---------
# EM (Grid)  Organized EM transport layer       Electromagnetic            Thermal (I^2R losses)
# T          High-entropy energy reservoir      Electromagnetic (degraded) Radiative (IR), Mechanical (convection)
# M          Low-entropy structured motion      Mechanical (emergent EM)   Gravitational, Thermal (friction)
# C (Bio)    Adaptive chemical energy proc.     Chemical (delta-mu)        Electromagnetic (bonding), Thermal (metabolism)
# R          External radiative forcing         Electromagnetic (photons)  --
# F          External fluid forcing             Mechanical (fluid motion)  Gravitational (large-scale flows)
# G          Gravitational potential field       Gravitational              Mechanical (hydro)
# K          Rotational / Coriolis modulator    Mechanical (angular mom.)  Fluid (atmospheric shaping)
#
# COMPRESSED VIEW
# ---------------
# SOURCES:           Radiative (R), Nuclear (not yet modelled)
# STRUCTURED ENERGY: Mechanical (M), Electrical (EM), Chemical (C)
# DEGRADED:          Thermal (T)
# FLOW SHAPERS:      Gravity (G), Rotation/Coriolis (K), Geometry/resonance
#
# The coupling matrix expresses interaction-to-interaction conversion.
# This exposes: which conversions are physically weak, where gains are
# overestimated, and where new couplings actually matter.
#
# KEY CONVERSIONS
# ---------------
# Piezo roads   : M  -> EM            (narrow regime)
# Biogas        : C  -> T  -> EM
# Solar PV      : R  -> EM
# Solar thermal : R  -> T  -> EM
# Wind          : F  -> M  -> EM
# Thermal store : T  <-> T            (time shifting)
#
# OPTIMIZATION PRINCIPLE
# ----------------------
# The system minimizes irreversible flow into the thermal reservoir.
# "Energy is conserved; utility is lost when structure collapses
#  into thermal equilibrium."

if __name__ == "__main__":
    run_physical_model()
