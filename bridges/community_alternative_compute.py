# bridges/community_alternative_compute.py
"""
Community Resilience — Alternative Computing Extensions
=======================================================
Extends CommunityBridgeEncoder with non-binary representations
that expose structural properties latent in the six-domain
octahedral resilience model.

Each paradigm captures a specific truth:

  Ternary   → Buffer states are inherently three-valued:
              DEPLETE / STABLE / ABUNDANT (not 0-100%)
  Quantum   → Skill holders exist in superposition until crisis;
              knowledge capacity collapses at measurement time
  Stochastic → Fuel/energy reserves are probability streams,
               not deterministic inventory counts
  Approximate → Institutional redundancy is a confidence-bound
                problem—how sure are you the backup works?

These are NOT replacements for the binary encoder.
They are diagnostic lenses that reveal what the binary
encoding compresses away.

Usage:
    from bridges.community_alternative_compute import (
        TernaryBufferState, QuantumKnowledgeCapacity,
        StochasticEnergyReserve, ApproximateInstitutionalRedundancy,
        community_alternative_diagnostic
    )
    
    state = community_alternative_diagnostic(community_profile)
    # state.ternary_buffers  → {"food": DEPLETE, "energy": STABLE, ...}
    # state.quantum_knowledge → superposition over skill domains
    # state.stochastic_energy → P(energy_sufficient) with confidence bounds
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import IntEnum, auto

# Import the existing encoder's domain functions
from bridges.community_encoder import (
    profile_to_capacities, profile_to_buffers,
    food_buffer, energy_buffer, social_buffer,
    institutional_buffer, knowledge_buffer, infrastructure_buffer
)


# ======================================================================
# 1. TERNARY BUFFER STATES
# ======================================================================

class TernaryBufferState(IntEnum):
    """
    Three-valued buffer classification.
    
    Binary says "buffer = 0.73" — a continuous value.
    Ternary says "buffer = DEPLETE" — a qualitative regime.
    
    The continuous value is still useful, but the ternary
    classification tells you what ACTION the buffer implies:
    
      DEPLETE  (−1): Draw down is active. Organism is consuming
                     reserves faster than they regenerate.
                     IMPLICATION: RESTRAIN consumption or RESTOCK.
    
      STABLE    (0): Reserves are holding. Input ≈ output.
                     IMPLICATION: MONITOR, maintain current rate.
    
      ABUNDANT (+1): Reserves are building. Surplus exists.
                     IMPLICATION: Can ACTIVATE new capacity,
                     lend to neighbors, or weather disruption.
    
    Thresholds are domain-specific because "3 days of food"
    means something different from "3 days of fuel."
    """
    DEPLETE  = -1
    STABLE   =  0
    ABUNDANT = +1
    
    @property
    def symbol(self) -> str:
        return {self.DEPLETE: '−', self.STABLE: '0', self.ABUNDANT: '+'}[self]
    
    @property
    def action(self) -> str:
        return {
            self.DEPLETE:  "RESTRAIN consumption; restock immediately",
            self.STABLE:   "MONITOR; maintain current rate",
            self.ABUNDANT: "ACTIVATE surplus capacity; lend to neighbors"
        }[self]
    
    @property
    def taf_stance(self) -> str:
        """Map to TAF TernaryCommand stance."""
        return {
            self.DEPLETE:  "RESTRAIN",
            self.STABLE:   "HOLD",
            self.ABUNDANT: "ACTIVATE"
        }[self]


def classify_buffer_ternary(value: float, 
                            deplete_threshold: float,
                            abundant_threshold: float) -> TernaryBufferState:
    """
    Classify a continuous buffer value [0,1] into ternary state.
    
    Thresholds are domain-specific. The gap between deplete_threshold
    and abundant_threshold is the STABLE zone—wide enough to prevent
    oscillation, narrow enough to catch real regime changes.
    """
    if value <= deplete_threshold:
        return TernaryBufferState.DEPLETE
    elif value >= abundant_threshold:
        return TernaryBufferState.ABUNDANT
    else:
        return TernaryBufferState.STABLE


def ternary_food_buffer(profile: dict) -> Tuple[TernaryBufferState, float, str]:
    """
    Ternary classification of food buffer.
    
    DEPLETE:  < 3 days retail supply (one missed delivery = crisis)
    ABUNDANT: > 14 days retail supply + food bank present
    STABLE:   between these thresholds
    
    The gap between 3 and 14 days is wide intentionally:
    it's the difference between "we need a truck tomorrow"
    and "we can wait out a supply chain disruption."
    """
    days = float(profile.get("days_food_supply_retail", 3.0))
    has_bank = bool(profile.get("food_bank_present", False))
    
    raw_buffer = food_buffer(days, has_bank)
    
    # Domain-specific thresholds
    deplete_threshold = 3.0 / 14.0  # 3 days normalized to 14-day ceiling ≈ 0.21
    abundant_threshold = 0.75       # 10.5+ days or 7+ days with food bank
    
    if has_bank:
        deplete_threshold *= 0.8  # Food bank lowers the DEPLETE threshold
        abundant_threshold *= 0.9  # And makes ABUNDANT slightly easier to reach
    
    state = classify_buffer_ternary(raw_buffer, deplete_threshold, abundant_threshold)
    
    diagnosis = {
        TernaryBufferState.DEPLETE: (
            f"Food buffer critical: {days:.1f} days retail supply. "
            f"One supply chain interruption triggers immediate shortage."
        ),
        TernaryBufferState.STABLE: (
            f"Food buffer adequate: {days:.1f} days retail supply. "
            f"Can absorb short disruptions."
        ),
        TernaryBufferState.ABUNDANT: (
            f"Food buffer robust: {days:.1f} days retail supply"
            f"{' + food bank' if has_bank else ''}. "
            f"Surplus capacity exists for neighboring communities."
        ),
    }[state]
    
    return state, raw_buffer, diagnosis


def ternary_energy_buffer(profile: dict) -> Tuple[TernaryBufferState, float, str]:
    """
    Ternary classification of energy buffer.
    
    DEPLETE:  < 3 days fuel reserve, no backup generation
    ABUNDANT: > 14 days fuel + multiple backup generators + local generation
    """
    fuel_days = float(profile.get("fuel_reserve_days", 3.0))
    backups = int(profile.get("backup_generators", 0))
    local_mw = float(profile.get("local_generation_mw", 0.0))
    
    raw_buffer = energy_buffer(fuel_days, backups, local_mw)
    
    # Energy-specific thresholds
    deplete_threshold = 0.20   # < ~1 day equivalent or no redundancy
    abundant_threshold = 0.70  # > ~10 days fuel + generation diversity
    
    state = classify_buffer_ternary(raw_buffer, deplete_threshold, abundant_threshold)
    
    diagnosis = {
        TernaryBufferState.DEPLETE: (
            f"Energy buffer critical: {fuel_days:.1f} days fuel, "
            f"{backups} backup generators, {local_mw:.1f} MW local generation. "
            f"Grid-dependent with minimal resilience."
        ),
        TernaryBufferState.STABLE: (
            f"Energy buffer adequate: {fuel_days:.1f} days fuel, "
            f"{backups} backup generators, {local_mw:.1f} MW local generation. "
            f"Can sustain critical loads through short outages."
        ),
        TernaryBufferState.ABUNDANT: (
            f"Energy buffer robust: {fuel_days:.1f} days fuel, "
            f"{backups} backup generators, {local_mw:.1f} MW local generation. "
            f"Generation diversity enables islanding and neighbor support."
        ),
    }[state]
    
    return state, raw_buffer, diagnosis


def ternary_social_buffer(profile: dict) -> Tuple[TernaryBufferState, float, str]:
    """
    Ternary classification of social buffer.
    
    Social buffer is the density of mutual aid networks and
    faith communities—the informal support structures that
    activate when formal institutions are overwhelmed.
    
    DEPLETE:  No mutual aid networks, < 3 faith communities
    ABUNDANT: 3+ mutual aid networks, 8+ faith communities
    """
    mutual = int(profile.get("mutual_aid_networks", 0))
    faiths = int(profile.get("faith_communities", 0))
    
    raw_buffer = social_buffer(mutual, faiths)
    
    deplete_threshold = 0.25  # 1 mutual aid network or 2-3 faith groups
    abundant_threshold = 0.70  # 3+ mutual aid + 8+ faith groups
    
    state = classify_buffer_ternary(raw_buffer, deplete_threshold, abundant_threshold)
    
    diagnosis = {
        TernaryBufferState.DEPLETE: (
            f"Social buffer thin: {mutual} mutual aid networks, "
            f"{faiths} faith communities. "
            f"Limited informal support capacity. Highly dependent on "
            f"functioning institutional channels."
        ),
        TernaryBufferState.STABLE: (
            f"Social buffer present: {mutual} mutual aid networks, "
            f"{faiths} faith communities. "
            f"Informal support structures can supplement formal channels."
        ),
        TernaryBufferState.ABUNDANT: (
            f"Social buffer dense: {mutual} mutual aid networks, "
            f"{faiths} faith communities. "
            f"Strong informal resilience. Community can self-organize "
            f"when formal institutions are degraded."
        ),
    }[state]
    
    return state, raw_buffer, diagnosis


def ternary_institutional_buffer(profile: dict) -> Tuple[TernaryBufferState, float, str]:
    """
    Ternary classification of institutional buffer.
    
    DEPLETE:  No alert system, no ham operators, no backup power for water
    ABUNDANT: Alert system + 3+ ham operators + backup water power
    """
    alert = bool(profile.get("community_alert_system", False))
    ham = int(profile.get("ham_radio_operators", 0))
    water_backup = bool(profile.get("backup_power_water_plant", False))
    
    raw_buffer = institutional_buffer(alert, ham, water_backup)
    
    deplete_threshold = 0.30  # Missing alert system or backup power
    abundant_threshold = 0.75  # All three components present
    
    state = classify_buffer_ternary(raw_buffer, deplete_threshold, abundant_threshold)
    
    diagnosis = {
        TernaryBufferState.DEPLETE: (
            f"Institutional buffer fragile: "
            f"{'alert system present' if alert else 'NO alert system'}, "
            f"{ham} ham operators, "
            f"{'backup water power' if water_backup else 'NO backup water power'}. "
            f"Single-point failures cascade through institutional channels."
        ),
        TernaryBufferState.STABLE: (
            f"Institutional buffer adequate: "
            f"{'alert system present' if alert else 'NO alert system'}, "
            f"{ham} ham operators, "
            f"{'backup water power' if water_backup else 'NO backup water power'}. "
            f"Some redundancy exists in communication and water infrastructure."
        ),
        TernaryBufferState.ABUNDANT: (
            f"Institutional buffer redundant: "
            f"{'alert system present' if alert else ''}"
            f"{ham} ham operators provide low-tech comms fallback, "
            f"{'backup water power' if water_backup else ''}. "
            f"Multiple independent channels maintain institutional function."
        ),
    }[state]
    
    return state, raw_buffer, diagnosis


def ternary_knowledge_buffer(profile: dict) -> Tuple[TernaryBufferState, float, str]:
    """
    Ternary classification of knowledge buffer.
    
    Knowledge is the most fragile domain: skills disappear when
    skill-holders leave or die. The buffer is entirely human.
    
    DEPLETE:  < 3 identified skill holders, no ham operators
    ABUNDANT: 8+ identified skill holders, 3+ ham operators
    """
    skills = int(profile.get("skill_holders_identified", 0))
    ham = int(profile.get("ham_radio_operators", 0))
    
    raw_buffer = knowledge_buffer(skills, ham)
    
    # Knowledge thresholds are lower because the domain is inherently fragile
    deplete_threshold = 0.25   # 2-3 skill holders, maybe 1 ham
    abundant_threshold = 0.65  # 6+ skill holders, 3+ ham
    
    state = classify_buffer_ternary(raw_buffer, deplete_threshold, abundant_threshold)
    
    diagnosis = {
        TernaryBufferState.DEPLETE: (
            f"Knowledge buffer critical: {skills} identified skill holders, "
            f"{ham} ham operators. "
            f"Critical skills concentrated in few individuals. "
            f"One illness or departure creates capability gap."
        ),
        TernaryBufferState.STABLE: (
            f"Knowledge buffer present: {skills} identified skill holders, "
            f"{ham} ham operators. "
            f"Skills distributed across multiple individuals. "
            f"Some redundancy in critical capabilities."
        ),
        TernaryBufferState.ABUNDANT: (
            f"Knowledge buffer deep: {skills} identified skill holders, "
            f"{ham} ham operators. "
            f"Skill redundancy enables teaching, delegation, and "
            f"knowledge transfer to neighboring communities."
        ),
    }[state]
    
    return state, raw_buffer, diagnosis


def ternary_infrastructure_buffer(profile: dict) -> Tuple[TernaryBufferState, float, str]:
    """Ternary classification of infrastructure buffer."""
    wells = int(profile.get("wells_private", 0))
    surface = int(profile.get("surface_water_sources", 0))
    days_water = float(profile.get("days_water_reserve", 1.0))
    
    raw_buffer = infrastructure_buffer(wells, surface, days_water)
    
    deplete_threshold = 0.25   # < 3 wells, 1 surface source, < 2 days water
    abundant_threshold = 0.65  # 8+ wells, 2+ surface, 5+ days water
    
    state = classify_buffer_ternary(raw_buffer, deplete_threshold, abundant_threshold)
    
    diagnosis = {
        TernaryBufferState.DEPLETE: (
            f"Infrastructure buffer thin: {wells} private wells, "
            f"{surface} surface sources, {days_water:.1f} days water reserve. "
            f"Water supply is single-threaded with minimal backup."
        ),
        TernaryBufferState.STABLE: (
            f"Infrastructure buffer adequate: {wells} private wells, "
            f"{surface} surface sources, {days_water:.1f} days water reserve. "
            f"Multiple water sources provide redundancy."
        ),
        TernaryBufferState.ABUNDANT: (
            f"Infrastructure buffer robust: {wells} private wells, "
            f"{surface} surface sources, {days_water:.1f} days water reserve. "
            f"Diverse water portfolio enables sustained operation "
            f"and neighbor support during infrastructure stress."
        ),
    }[state]
    
    return state, raw_buffer, diagnosis


# ======================================================================
# 2. QUANTUM KNOWLEDGE CAPACITY
# ======================================================================

@dataclass
class QuantumKnowledgeCapacity:
    """
    Knowledge capacity modeled as quantum superposition.
    
    A community doesn't "have a skill" the way it has a fuel tank.
    Skills exist in superposition over skill-holders:
    
      |knowledge⟩ = α|available⟩ + β|unavailable⟩
    
    The skill "exists" in the community, but whether it can be
    accessed at crisis time depends on:
    - Is the skill-holder present? (not evacuated, not incapacitated)
    - Is the skill-holder identifiable? (does anyone know they have it?)
    - Is the skill transferable? (can they teach it or delegate?)
    
    Measurement (crisis) collapses the superposition.
    The probability of successful collapse is the community's
    true knowledge resilience—NOT the headcount of skill-holders.
    """
    
    skill_holders: int
    ham_operators: int
    rail_access: bool
    highway_access: bool
    active_farms: int
    population: int
    
    # Derived quantum state
    superposition_amplitudes: Dict[str, complex] = field(default_factory=dict)
    collapse_probability: float = 0.0
    entanglement_strength: float = 0.0
    
    def __post_init__(self):
        self._compute_superposition()
    
    def _compute_superposition(self):
        """
        Compute knowledge superposition state.
        
        Four basis states:
          |med⟩  = medical/healthcare knowledge
          |comm⟩ = communication knowledge (ham radio)
          |agri⟩ = agricultural knowledge (farming)
          |mech⟩ = mechanical/infrastructure knowledge
        
        Each skill-holder contributes amplitude to one or more
        basis states. The total amplitude squared = probability
        that the knowledge can be accessed when needed.
        """
        if self.population <= 0:
            self.collapse_probability = 0.0
            return
        
        # Skill density per capita
        density = self.skill_holders / self.population
        
        # Each skill-holder can cover ~3 domains (generalist assumption)
        domains_covered = min(4, self.skill_holders * 3 / 4)
        
        # Base amplitude: skill density normalized
        base_amplitude = min(1.0, density * 10)  # 0.1 density = 100% amplitude
        
        # Ham operators provide comms redundancy (phase coherence)
        ham_amplitude = min(1.0, self.ham_operators / 5.0)
        
        # Transport links enable knowledge transfer (entanglement)
        transport_amplitude = (
            (0.6 if self.highway_access else 0.0) +
            (0.4 if self.rail_access else 0.0)
        )
        
        # Agricultural knowledge is embodied in active farms
        farm_amplitude = min(1.0, self.active_farms / 20.0)
        
        # Compute superposition state
        self.superposition_amplitudes = {
            "|med⟩":  complex(base_amplitude * 0.3, 0),
            "|comm⟩": complex(ham_amplitude, 0),
            "|agri⟩": complex(farm_amplitude, 0),
            "|mech⟩": complex(base_amplitude * 0.3 + transport_amplitude * 0.4, 0),
        }
        
        # Born's rule: collapse probability = |amplitude|²
        # averaged over all basis states
        probabilities = [abs(a)**2 for a in self.superposition_amplitudes.values()]
        self.collapse_probability = sum(probabilities) / len(probabilities)
        
        # Entanglement strength: how much knowledge transfer
        # (transport links) increases collapse probability
        isolated_prob = (base_amplitude**2 + ham_amplitude**2 + farm_amplitude**2) / 4
        self.entanglement_strength = max(0, self.collapse_probability - isolated_prob)
    
    def measure(self, crisis_domain: str = None) -> Tuple[str, float]:
        """
        Simulate measurement collapse during crisis.
        
        Without specifying crisis_domain: random collapse via Born's rule.
        With crisis_domain: biased collapse toward relevant knowledge.
        
        Returns:
            (collapsed_domain, measurement_probability)
        """
        import random
        
        amplitudes = dict(self.superposition_amplitudes)
        
        # Bias toward crisis-relevant domain
        domain_bias = {
            "medical": "|med⟩",
            "communication": "|comm⟩",
            "food": "|agri⟩",
            "infrastructure": "|mech⟩",
        }
        
        if crisis_domain and crisis_domain in domain_bias:
            target = domain_bias[crisis_domain]
            if target in amplitudes:
                # Amplify the target domain (coherent measurement)
                amplitudes[target] *= 2.0
        
        # Normalize
        total_prob = sum(abs(a)**2 for a in amplitudes.values())
        if total_prob <= 0:
            return "|none⟩", 0.0
        
        normalized = {k: abs(a)**2 / total_prob for k, a in amplitudes.items()}
        
        # Collapse
        r = random.random()
        cumulative = 0
        for domain, prob in normalized.items():
            cumulative += prob
            if r <= cumulative:
                return domain, prob
        
        return list(normalized.keys())[-1], list(normalized.values())[-1]
    
    def diagnose(self) -> str:
        """Human-readable diagnosis of quantum knowledge state."""
        if self.collapse_probability < 0.3:
            return (
                f"Knowledge capacity critically fragile. "
                f"Only {self.skill_holders} identified skill-holders "
                f"across {self.population} population. "
                f"Collapse probability {self.collapse_probability:.2f}: "
                f"skills unlikely to be accessible during crisis."
            )
        elif self.collapse_probability < 0.6:
            return (
                f"Knowledge capacity present but uncertain. "
                f"{self.skill_holders} skill-holders provide partial coverage. "
                f"Collapse probability {self.collapse_probability:.2f}: "
                f"some skills accessible, gaps exist in specific domains."
            )
        else:
            return (
                f"Knowledge capacity robust. "
                f"{self.skill_holders} skill-holders provide dense coverage. "
                f"Collapse probability {self.collapse_probability:.2f}: "
                f"skills likely accessible across multiple domains. "
                f"Entanglement strength {self.entanglement_strength:.2f} "
                f"indicates knowledge transfer capability between domains."
            )


# ======================================================================
# 3. STOCHASTIC ENERGY RESERVE
# ======================================================================

@dataclass
class StochasticEnergyReserve:
    """
    Energy reserves modeled as probability stream.
    
    A fuel reserve of "10 days" is not deterministic.
    It's a probability distribution:
    - Delivery might arrive early (P(reserve > 10) > 0)
    - Delivery might be delayed (P(reserve < 10) > 0)
    - Consumption rate varies with temperature, activity, crisis phase
    
    Stochastic encoding captures this uncertainty:
      P(energy_sufficient) = f(reserve_days, delivery_reliability, consumption_variance)
    
    This matters because "10 days reserve" with reliable delivery
    is fundamentally different from "10 days reserve" with
    stochastic delivery—but binary encoding gives both the same score.
    """
    
    fuel_reserve_days: float
    backup_generators: int
    local_generation_mw: float
    grid_connected: bool
    population: int
    
    # Stochastic parameters
    delivery_reliability: float = 0.8      # P(delivery on schedule)
    consumption_variance: float = 0.2       # σ of daily consumption
    stream_length: int = 256
    
    # Derived
    sufficiency_probability: float = 0.0
    effective_days: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    
    def __post_init__(self):
        self._compute_stochastic_sufficiency()
    
    def _compute_stochastic_sufficiency(self):
        """
        Compute P(energy_sufficient) using stochastic model.
        
        Model:
        - Base consumption: population-dependent
        - Delivery: Bernoulli process with P(reliable)
        - Local generation: reduces consumption from reserves
        - Backup generators: provide step-function resilience
        
        The probability stream integrates over all possible
        consumption/delivery scenarios within the stream_length window.
        """
        if self.population <= 0:
            self.sufficiency_probability = 1.0
            self.effective_days = float('inf')
            return
        
        # Base daily consumption (arbitrary units)
        base_consumption = self.population * 0.001  # MW equivalent
        
        # Local generation offsets consumption
        net_consumption = max(0.1, base_consumption - self.local_generation_mw)
        
        # Effective reserve: fuel days adjusted for consumption rate
        self.effective_days = self.fuel_reserve_days * (base_consumption / net_consumption)
        
        # Backup generators extend effective days by providing
        # step-function capacity when reserves are low
        generator_extension = self.backup_generators * 0.5  # days each
        
        # Stochastic sufficiency model
        # Integrate over possible delivery scenarios
        scenarios = 1000  # Monte Carlo samples
        
        sufficient_count = 0
        for _ in range(scenarios):
            # Simulate delivery pattern
            import random
            
            total_days = self.effective_days
            delivery_day = 0
            days_survived = 0
            
            for day in range(int(self.effective_days + generator_extension + 10)):
                # Consume energy
                consumption = net_consumption * (1 + random.gauss(0, self.consumption_variance))
                total_days -= consumption / base_consumption
                
                # Check for delivery
                if day >= delivery_day and random.random() < self.delivery_reliability:
                    total_days = max(total_days, self.effective_days * 0.5)  # Partial resupply
                    delivery_day = day + int(7 * random.random())  # Next delivery window
                
                # Generator activation when reserves critically low
                if total_days < 1.0 and self.backup_generators > 0:
                    total_days += generator_extension
                
                if total_days <= 0:
                    break
                
                days_survived += 1
            
            # Sufficient if survived longer than stream_length window
            if days_survived >= self.stream_length:
                sufficient_count += 1
        
        self.sufficiency_probability = sufficient_count / scenarios
        
        # Confidence interval (Wilson score interval, simplified)
        z = 1.96  # 95% confidence
        p = self.sufficiency_probability
        n = scenarios
        margin = z * math.sqrt(p * (1 - p) / n)
        self.confidence_interval = (
            max(0, p - margin),
            min(1, p + margin)
        )
    
    def diagnose(self) -> str:
        """Human-readable stochastic energy diagnosis."""
        ci_low, ci_high = self.confidence_interval
        
        if self.sufficiency_probability < 0.5:
            return (
                f"Energy sufficiency unlikely: P(sufficient) = {self.sufficiency_probability:.2f} "
                f"[{ci_low:.2f}, {ci_high:.2f}]. "
                f"Effective reserve: {self.effective_days:.1f} days (after local generation offset). "
                f"Delivery reliability {self.delivery_reliability:.2f} creates significant "
                f"uncertainty in long-duration scenarios."
            )
        elif self.sufficiency_probability < 0.8:
            return (
                f"Energy sufficiency probable but uncertain: P(sufficient) = {self.sufficiency_probability:.2f} "
                f"[{ci_low:.2f}, {ci_high:.2f}]. "
                f"Effective reserve: {self.effective_days:.1f} days. "
                f"Stochastic delivery and consumption variance create tail risk."
            )
        else:
            return (
                f"Energy sufficiency robust: P(sufficient) = {self.sufficiency_probability:.2f} "
                f"[{ci_low:.2f}, {ci_high:.2f}]. "
                f"Effective reserve: {self.effective_days:.1f} days. "
                f"Local generation ({self.local_generation_mw:.1f} MW) and "
                f"{self.backup_generators} backup generators provide resilience "
                f"against delivery stochasticity."
            )


# ======================================================================
# 4. APPROXIMATE INSTITUTIONAL REDUNDANCY
# ======================================================================

@dataclass
class ApproximateInstitutionalRedundancy:
    """
    Institutional redundancy as confidence-bound computation.
    
    "We have a backup water plant" is not binary.
    The question is: what's the confidence that it works when needed?
    
    Factors:
    - Has it been tested recently? (tested = higher confidence)
    - Is maintenance current?
    - Are operators trained and available?
    - Does it depend on the same power grid as the primary?
    
    Approximate computing captures this as a confidence interval
    rather than a boolean. The institution "has" the backup with
    some confidence, not with certainty.
    """
    
    alert_system: bool
    ham_operators: int
    backup_water_power: bool
    water_treatment_functional: bool
    cell_towers: int
    internet_providers: int
    
    # Approximate parameters
    precision_bits: int = 8
    
    # Derived
    redundancy_confidence: float = 0.0
    common_mode_risk: float = 0.0
    single_points_of_failure: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self._compute_approximate_redundancy()
    
    def _compute_approximate_redundancy(self):
        """
        Compute approximate institutional redundancy.
        
        Uses low-precision arithmetic (simulated NPU) to estimate
        confidence that institutional backups will function.
        
        This is inherently approximate because:
        - Backup systems are rarely tested under real load
        - Common-mode failures are hard to predict
        - Human factors (operator availability) are stochastic
        """
        # Quantize inputs to INT8 range (0-127)
        q_alert = 127 if self.alert_system else 20  # Even "no" gets some probability
        q_ham = min(127, self.ham_operators * 25)    # 5+ operators = full confidence
        q_backup = 127 if self.backup_water_power else 15
        q_water = 100 if self.water_treatment_functional else 30
        q_cell = min(127, self.cell_towers * 30)
        q_internet = min(127, self.internet_providers * 60)
        
        # Approximate multiply-accumulate (simulated NPU)
        # Each channel provides independent confidence
        confidence_int = (
            q_alert * 30 +     # Alert system weight
            q_ham * 25 +       # Ham radio weight
            q_backup * 25 +    # Backup power weight
            q_water * 10 +     # Water treatment weight
            q_cell * 5 +       # Cell towers (less weight: fragile)
            q_internet * 5     # Internet (less weight: single-threaded)
        ) // 100  # Normalize
        
        self.redundancy_confidence = confidence_int / 127.0
        
        # Common-mode risk: what failures affect multiple channels?
        self.common_mode_risk = 0.0
        self.single_points_of_failure = []
        
        # Grid dependency is a common mode
        if not self.backup_water_power:
            self.common_mode_risk += 0.3
            self.single_points_of_failure.append(
                "Water infrastructure depends entirely on grid power"
            )
        
        # Communication single-threading
        if self.cell_towers <= 1 and self.internet_providers <= 1:
            self.common_mode_risk += 0.3
            self.single_points_of_failure.append(
                "Single communication channel: one tower or provider failure = isolation"
            )
        
        # Alert system absent
        if not self.alert_system:
            self.common_mode_risk += 0.2
            self.single_points_of_failure.append(
                "No community alert system: all emergency communication is ad-hoc"
            )
        
        # Ham operators provide common-mode mitigation
        if self.ham_operators >= 3:
            self.common_mode_risk = max(0, self.common_mode_risk - 0.2)
        if self.ham_operators >= 5:
            self.common_mode_risk = max(0, self.common_mode_risk - 0.15)
        
        self.common_mode_risk = min(1.0, self.common_mode_risk)
    
    def diagnose(self) -> str:
        """Human-readable institutional redundancy diagnosis."""
        if self.redundancy_confidence < 0.4:
            diagnosis = (
                f"Institutional redundancy critically low: "
                f"confidence {self.redundancy_confidence:.2f}. "
            )
        elif self.redundancy_confidence < 0.7:
            diagnosis = (
                f"Institutional redundancy marginal: "
                f"confidence {self.redundancy_confidence:.2f}. "
            )
        else:
            diagnosis = (
                f"Institutional redundancy adequate: "
                f"confidence {self.redundancy_confidence:.2f}. "
            )
        
        if self.common_mode_risk > 0.4:
            diagnosis += (
                f"Common-mode risk {self.common_mode_risk:.2f} indicates "
                f"multiple channels share failure dependencies. "
            )
        
        if self.single_points_of_failure:
            diagnosis += f"Single points of failure: {len(self.single_points_of_failure)} identified. "
        
        return diagnosis


# ======================================================================
# 5. POPULATION PARADOX ACKNOWLEDGMENT
# ======================================================================

def population_paradox_adjustment(profile: dict) -> Dict[str, Any]:
    """
    Compute and document the population denominator effect.
    
    A community of 10,000 with the same infrastructure as one of 50,000
    scores higher on per-capita resilience. This is mathematically correct
    (same resources ÷ fewer people = more per person) but systemically
    ambiguous: population decline is often a symptom of extraction,
    not a resilience strategy.
    
    This function computes:
    1. Raw per-capita capacity scores
    2. Absolute capacity scores (total resources, not per-capita)
    3. The "paradox ratio" between them
    4. A diagnostic interpretation
    
    Returns both perspectives so the analyst can see what
    the binary encoding compresses.
    """
    population = int(profile.get("population", 1))
    
    # Per-capita (standard) scoring
    caps_per_capita = profile_to_capacities(profile)
    
    # Absolute scoring: multiply each capacity by population
    # to get total resource pool rather than per-person availability
    caps_absolute = {}
    for domain, per_capita_score in caps_per_capita.items():
        # Food capacity has population baked in; for absolute,
        # we want: how much food does this community produce total?
        if domain == "food":
            farms = int(profile.get("active_farms_local", 0))
            gardens = float(profile.get("community_gardens_acres", 0.0))
            total_cal_production = farms * 80 * 6_000_000 + gardens * 3_000_000
            caps_absolute[domain] = total_cal_production / 1e9  # Gigacalories
        elif domain == "energy":
            local_mw = float(profile.get("local_generation_mw", 0.0))
            caps_absolute[domain] = local_mw  # MW (already absolute)
        elif domain == "social":
            orgs = (int(profile.get("mutual_aid_networks", 0)) +
                    int(profile.get("faith_communities", 0)) +
                    int(profile.get("civic_organizations", 0)))
            caps_absolute[domain] = orgs  # Count of organizations
        elif domain == "knowledge":
            caps_absolute[domain] = int(profile.get("skill_holders_identified", 0))
        else:
            caps_absolute[domain] = per_capita_score * population / 1000  # Scaled
    
    # Paradox ratio: per-capita / absolute (normalized)
    max_per_capita = max(caps_per_capita.values()) if caps_per_capita else 1
    max_absolute = max(caps_absolute.values()) if caps_absolute else 1
    
    paradox_ratios = {}
    for domain in caps_per_capita:
        pc_normalized = caps_per_capita[domain] / max_per_capita if max_per_capita > 0 else 0
        abs_normalized = caps_absolute[domain] / max_absolute if max_absolute > 0 else 0
        if abs_normalized > 0:
            paradox_ratios[domain] = pc_normalized / abs_normalized
        else:
            paradox_ratios[domain] = float('inf')
    
    # Diagnostic
    high_paradox_domains = [d for d, r in paradox_ratios.items() if r > 2.0]
    
    if high_paradox_domains:
        diagnosis = (
            f"Population paradox active in: {', '.join(high_paradox_domains)}. "
            f"Population {population} inflates per-capita scores relative to "
            f"absolute resource availability. This community appears more "
            f"resilient per person, but its total resource base may be "
            f"insufficient to maintain critical infrastructure or withstand "
            f"compound shocks. Consider: is population decline here a "
            f"resilience strategy or a symptom of extraction?"
        )
    else:
        diagnosis = (
            f"No significant population paradox detected. "
            f"Per-capita and absolute capacity scores are proportionally aligned "
            f"for population {population}."
        )
    
    return {
        "population": population,
        "capacities_per_capita": caps_per_capita,
        "capacities_absolute": caps_absolute,
        "paradox_ratios": paradox_ratios,
        "high_paradox_domains": high_paradox_domains,
        "diagnosis": diagnosis
    }


# ======================================================================
# 6. COMPOSITE DIAGNOSTIC
# ======================================================================

@dataclass
class CommunityAlternativeDiagnostic:
    """
    Complete alternative computing diagnostic for a community profile.
    
    Aggregates ternary, quantum, stochastic, approximate, and paradox
    analyses into a single report that reveals what the binary
    encoding compresses.
    """
    
    profile_name: str
    population: int
    
    # Ternary buffer states
    ternary_buffers: Dict[str, Tuple[TernaryBufferState, float, str]] = field(default_factory=dict)
    overall_ternary_stance: TernaryBufferState = TernaryBufferState.STABLE
    
    # Quantum knowledge
    quantum_knowledge: Optional[QuantumKnowledgeCapacity] = None
    
    # Stochastic energy
    stochastic_energy: Optional[StochasticEnergyReserve] = None
    
    # Approximate institutional
    approximate_institutional: Optional[ApproximateInstitutionalRedundancy] = None
    
    # Population paradox
    paradox_analysis: Optional[Dict[str, Any]] = None
    
    # Binary encoding (for comparison)
    binary_encoding: Optional[str] = None
    crisis_phase: Optional[str] = None
    
    def summary(self) -> str:
        """Multi-line diagnostic summary."""
        lines = [
            f"{'='*60}",
            f"Community Alternative Diagnostic: {self.profile_name}",
            f"Population: {self.population}",
            f"{'='*60}",
            "",
            "TERNARY BUFFER STATES:",
        ]
        
        for domain, (state, value, diagnosis) in self.ternary_buffers.items():
            lines.append(f"  {domain:20s}: {state.symbol} {state.name:10s} ({value:.2f})")
        
        # Count states
        deplete_count = sum(1 for s, _, _ in self.ternary_buffers.values() if s == TernaryBufferState.DEPLETE)
        abundant_count = sum(1 for s, _, _ in self.ternary_buffers.values() if s == TernaryBufferState.ABUNDANT)
        
        lines.append(f"\n  DEPLETE domains: {deplete_count}/6")
        lines.append(f"  ABUNDANT domains: {abundant_count}/6")
        lines.append(f"  Overall stance: {self.overall_ternary_stance.name}")
        
        if self.quantum_knowledge:
            lines.append(f"\nQUANTUM KNOWLEDGE CAPACITY:")
            lines.append(f"  Collapse probability: {self.quantum_knowledge.collapse_probability:.2f}")
            lines.append(f"  Entanglement strength: {self.quantum_knowledge.entanglement_strength:.2f}")
            lines.append(f"  {self.quantum_knowledge.diagnose()}")
        
        if self.stochastic_energy:
            lines.append(f"\nSTOCHASTIC ENERGY RESERVE:")
            lines.append(f"  P(sufficient): {self.stochastic_energy.sufficiency_probability:.2f}")
            lines.append(f"  {self.stochastic_energy.diagnose()}")
        
        if self.approximate_institutional:
            lines.append(f"\nAPPROXIMATE INSTITUTIONAL REDUNDANCY:")
            lines.append(f"  Confidence: {self.approximate_institutional.redundancy_confidence:.2f}")
            lines.append(f"  Common-mode risk: {self.approximate_institutional.common_mode_risk:.2f}")
            if self.approximate_institutional.single_points_of_failure:
                lines.append(f"  Single points of failure:")
                for spof in self.approximate_institutional.single_points_of_failure:
                    lines.append(f"    - {spof}")
        
        if self.paradox_analysis:
            lines.append(f"\nPOPULATION PARADOX:")
            lines.append(f"  {self.paradox_analysis['diagnosis']}")
        
        if self.binary_encoding:
            lines.append(f"\nBINARY ENCODING (for reference):")
            lines.append(f"  {self.binary_encoding}")
            lines.append(f"  Crisis phase: {self.crisis_phase}")
        
        lines.append(f"\n{'='*60}")
        return '\n'.join(lines)


def community_alternative_diagnostic(profile: dict) -> CommunityAlternativeDiagnostic:
    """
    Generate complete alternative computing diagnostic for a community profile.
    
    This is the main entry point. Pass a CommunityProfile dict and
    receive a comprehensive diagnostic showing what each alternative
    paradigm reveals about the community's resilience structure.
    
    Args:
        profile: CommunityProfile as dict or dataclass
        
    Returns:
        CommunityAlternativeDiagnostic with all paradigm analyses
    """
    if not isinstance(profile, dict):
        profile = profile.__dict__
    
    name = profile.get("name", "Unnamed Community")
    population = int(profile.get("population", 1))
    
    diagnostic = CommunityAlternativeDiagnostic(
        profile_name=name,
        population=population
    )
    
    # Ternary buffer states
    diagnostic.ternary_buffers = {
        "food": ternary_food_buffer(profile),
        "energy": ternary_energy_buffer(profile),
        "social": ternary_social_buffer(profile),
        "institutional": ternary_institutional_buffer(profile),
        "knowledge": ternary_knowledge_buffer(profile),
        "infrastructure": ternary_infrastructure_buffer(profile),
    }
    
    # Overall ternary stance: modal state
    states = [s for s, _, _ in diagnostic.ternary_buffers.values()]
    deplete_count = sum(1 for s in states if s == TernaryBufferState.DEPLETE)
    abundant_count = sum(1 for s in states if s == TernaryBufferState.ABUNDANT)
    
    if deplete_count >= 3:
        diagnostic.overall_ternary_stance = TernaryBufferState.DEPLETE
    elif abundant_count >= 3:
        diagnostic.overall_ternary_stance = TernaryBufferState.ABUNDANT
    else:
        diagnostic.overall_ternary_stance = TernaryBufferState.STABLE
    
    # Quantum knowledge capacity
    diagnostic.quantum_knowledge = QuantumKnowledgeCapacity(
        skill_holders=int(profile.get("skill_holders_identified", 0)),
        ham_operators=int(profile.get("ham_radio_operators", 0)),
        rail_access=bool(profile.get("rail_access", False)),
        highway_access=bool(profile.get("highway_access", True)),
        active_farms=int(profile.get("active_farms_local", 0)),
        population=population
    )
    
    # Stochastic energy reserve
    diagnostic.stochastic_energy = StochasticEnergyReserve(
        fuel_reserve_days=float(profile.get("fuel_reserve_days", 3.0)),
        backup_generators=int(profile.get("backup_generators", 0)),
        local_generation_mw=float(profile.get("local_generation_mw", 0.0)),
        grid_connected=bool(profile.get("grid_connected", True)),
        population=population
    )
    
    # Approximate institutional redundancy
    diagnostic.approximate_institutional = ApproximateInstitutionalRedundancy(
        alert_system=bool(profile.get("community_alert_system", False)),
        ham_operators=int(profile.get("ham_radio_operators", 0)),
        backup_water_power=bool(profile.get("backup_power_water_plant", False)),
        water_treatment_functional=bool(profile.get("water_treatment_functional", True)),
        cell_towers=int(profile.get("cell_towers", 1)),
        internet_providers=int(profile.get("internet_providers", 1))
    )
    
    # Population paradox
    diagnostic.paradox_analysis = population_paradox_adjustment(profile)
    
    # Binary encoding (for comparison)
    try:
        from bridges.community_encoder import CommunityBridgeEncoder
        enc = CommunityBridgeEncoder()
        enc.from_geometry(profile)
        diagnostic.binary_encoding = enc.to_binary()
        from bridges.resilience_encoder import crisis_phase
        caps = profile_to_capacities(profile)
        bufs = profile_to_buffers(profile)
        diagnostic.crisis_phase = crisis_phase(caps, bufs)
    except ImportError:
        pass  # Binary encoder not available in this context
    
    return diagnostic


# ======================================================================
# Demo
# ======================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Community Alternative Computing — Diagnostic Demo")
    print("=" * 60)
    
    # Test with both profiles from the original demo
    profiles = [
        {
            "name": "Strong rural town",
            "population": 10_000,
            "days_food_supply_retail": 5.0,
            "active_farms_local": 50,
            "community_gardens_acres": 2.0,
            "farmers_market": True,
            "grain_elevator_present": True,
            "food_bank_present": True,
            "grid_connected": True,
            "local_generation_mw": 2.0,
            "solar_installations": 10,
            "backup_generators": 5,
            "fuel_reserve_days": 10.0,
            "hospital_present": True,
            "clinic_present": True,
            "pharmacy_count": 3,
            "ems_available": True,
            "mutual_aid_networks": 3,
            "faith_communities": 8,
            "civic_organizations": 6,
            "cell_towers": 4,
            "internet_providers": 2,
            "ham_radio_operators": 5,
            "community_alert_system": True,
            "wells_private": 20,
            "surface_water_sources": 3,
            "days_water_reserve": 3.0,
            "backup_power_water_plant": True,
            "water_treatment_functional": True,
            "highway_access": True,
            "rail_access": True,
            "fuel_stations": 5,
            "skill_holders_identified": 10,
        },
        {
            "name": "Vulnerable urban neighbourhood",
            "population": 50_000,
            "days_food_supply_retail": 2.0,
            "active_farms_local": 0,
            "community_gardens_acres": 0.1,
            "farmers_market": False,
            "grain_elevator_present": False,
            "food_bank_present": True,
            "grid_connected": True,
            "local_generation_mw": 0.0,
            "solar_installations": 1,
            "backup_generators": 0,
            "fuel_reserve_days": 1.0,
            "hospital_present": False,
            "clinic_present": True,
            "pharmacy_count": 2,
            "ems_available": True,
            "mutual_aid_networks": 0,
            "faith_communities": 2,
            "civic_organizations": 1,
            "cell_towers": 2,
            "internet_providers": 1,
            "ham_radio_operators": 0,
            "community_alert_system": False,
            "wells_private": 0,
            "surface_water_sources": 0,
            "days_water_reserve": 0.5,
            "backup_power_water_plant": False,
            "water_treatment_functional": True,
            "highway_access": True,
            "rail_access": False,
            "fuel_stations": 2,
            "skill_holders_identified": 1,
        },
    ]
    
    for prof in profiles:
        diag = community_alternative_diagnostic(prof)
        print(diag.summary())
        print()
