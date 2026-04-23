"""
Community Bridge Encoder
========================
Translates an urban-resilience-sim CommunityProfile dict into the
6-domain capacity + buffer geometry consumed by ResilienceBridgeEncoder,
then emits a 39-bit Gray-coded binary string.

The CommunityProfile fields map onto the six octahedral resilience axes:

    +X = food/water       ← grocery stores, farms, water sources
    −X = energy           ← grid, local generation, reserves
    +Y = social           ← healthcare, mutual aid, community orgs
    −Y = institutional    ← communication, EMS, alert systems
    +Z = knowledge        ← skill holders, ham operators, rail/transport
    −Z = infrastructure   ← highway, fuel stations, backup systems

Each domain is scored [0, 1] from the profile's boolean / numeric fields.
The buffer is the "reserve" component — how many days / backup layers remain.

This encoder is intentionally thin: it converts community observations to
the canonical octahedral domain representation, then delegates all binary
encoding to ResilienceBridgeEncoder.

Equations implemented
---------------------
  Food capacity    :  f(retail_days, local_pct) = min(1, retail_days/21 + local_pct/200)
  Energy capacity  :  e(grid, local_mw, backups) = weighted composite
  Social capacity  :  s(medical, aid, orgs) = weighted composite
  Institutional cap:  i(comms, ems, alert) = weighted composite
  Knowledge cap    :  k(skills, ham, rail) = weighted composite
  Infra capacity   :  n(highway, fuel, water) = weighted composite

  Buffer = reserve depth (days / redundant layers) normalised to [0, 1].

Bit layout
----------
39-bit Gray-coded output — identical layout to ResilienceBridgeEncoder.
Section A (18b): domain capacities 3b Gray each (food, energy, social,
                 institutional, knowledge, infrastructure)
Section B  (9b): crisis phase, buffer state, flags
Section C  (6b): cascade coupling
Section D  (6b): seed geometry

License: CC-BY-4.0
"""

from __future__ import annotations

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.resilience_encoder import ResilienceBridgeEncoder, crisis_phase, cascade_dominant

# ---------------------------------------------------------------------------
# Domain scoring — pure functions, accept raw profile field values
# ---------------------------------------------------------------------------

def food_capacity(
    days_food_supply_retail: float,
    active_farms_local: int,
    community_gardens_acres: float,
    population: int,
    farmers_market: bool = False,
    grain_elevator_present: bool = False,
    food_bank_present: bool = False,
) -> float:
    """
    Score food/water domain capacity [0, 1].

    Combines retail buffer days, local production, and resilience assets.
    A community is at capacity = 1.0 when it has 3+ weeks of retail stock
    AND enough local farms/gardens to sustain itself without resupply.
    """
    # Retail buffer component (0.25 weight): normalise to 21-day ceiling
    retail_score = min(1.0, days_food_supply_retail / 21.0) * 0.25

    # Local production component (0.45 weight)
    if population > 0:
        annual_need = population * 2000 * 365  # calories
        garden_cal  = community_gardens_acres * 3_000_000
        farm_cal    = active_farms_local * 80 * 6_000_000
        local_pct   = min(1.0, (garden_cal + farm_cal) / annual_need)
    else:
        local_pct = 0.0
    prod_score = local_pct * 0.45

    # Resilience assets (0.30 weight)
    asset_score = (
        (0.10 if farmers_market       else 0.0) +
        (0.10 if grain_elevator_present else 0.0) +
        (0.10 if food_bank_present     else 0.0)
    )

    return min(1.0, retail_score + prod_score + asset_score)


def energy_capacity(
    grid_connected: bool,
    local_generation_mw: float,
    solar_installations: int,
    wind_capacity_mw: float,
    backup_generators: int,
    fuel_reserve_days: float,
) -> float:
    """
    Score energy domain capacity [0, 1].

    Grid connectivity is baseline; local generation and redundancy raise it.
    """
    base     = 0.30 if grid_connected else 0.0
    local_mw = min(0.30, local_generation_mw / 10.0 * 0.30)   # 10 MW ceiling
    solar    = min(0.10, solar_installations / 20.0 * 0.10)
    wind     = min(0.10, wind_capacity_mw / 5.0 * 0.10)
    gen      = min(0.10, backup_generators / 10.0 * 0.10)
    fuel     = min(0.10, fuel_reserve_days / 30.0 * 0.10)
    return min(1.0, base + local_mw + solar + wind + gen + fuel)


def social_capacity(
    population: int,
    hospital_present: bool,
    clinic_present: bool,
    pharmacy_count: int,
    ems_available: bool,
    mutual_aid_networks: int,
    faith_communities: int,
    civic_organizations: int,
) -> float:
    """
    Score social cohesion domain capacity [0, 1].

    Healthcare infrastructure anchors social resilience; community
    organisations provide the connective tissue.
    """
    medical = (
        (0.20 if hospital_present else 0.0) +
        (0.15 if clinic_present   else 0.0) +
        min(0.10, pharmacy_count / 3.0 * 0.10) +
        (0.10 if ems_available    else 0.0)
    )
    social_net = (
        min(0.20, mutual_aid_networks  / 3.0 * 0.20) +
        min(0.15, faith_communities    / 10.0 * 0.15) +
        min(0.10, civic_organizations  / 5.0 * 0.10)
    )
    return min(1.0, medical + social_net)


def institutional_capacity(
    cell_towers: int,
    internet_providers: int,
    ham_radio_operators: int,
    community_alert_system: bool,
    ems_available: bool,
    water_treatment_functional: bool,
    backup_power_water_plant: bool,
) -> float:
    """
    Score institutional domain capacity [0, 1].

    Reliable communication and water governance represent institutional
    resilience: protocols that work even when normal channels fail.
    """
    comms = (
        min(0.20, cell_towers          / 4.0 * 0.20) +
        min(0.15, internet_providers   / 2.0 * 0.15) +
        min(0.15, ham_radio_operators  / 5.0 * 0.15) +
        (0.10 if community_alert_system else 0.0)
    )
    governance = (
        (0.15 if ems_available              else 0.0) +
        (0.15 if water_treatment_functional else 0.0) +
        (0.10 if backup_power_water_plant   else 0.0)
    )
    return min(1.0, comms + governance)


def knowledge_capacity(
    skill_holders_identified: int,
    ham_radio_operators: int,
    rail_access: bool,
    highway_access: bool,
    active_farms_local: int,
) -> float:
    """
    Score knowledge transmission domain capacity [0, 1].

    Skill holders and low-tech communication channels (ham) preserve
    embodied knowledge.  Transport links allow knowledge transfer between
    communities.  Active farms encode agricultural knowledge in practice.
    """
    skills  = min(0.40, skill_holders_identified / 10.0 * 0.40)
    ham     = min(0.20, ham_radio_operators / 5.0 * 0.20)
    transit = (
        (0.15 if rail_access    else 0.0) +
        (0.10 if highway_access else 0.0)
    )
    farm_k  = min(0.15, active_farms_local / 20.0 * 0.15)
    return min(1.0, skills + ham + transit + farm_k)


def infrastructure_capacity(
    highway_access: bool,
    rail_access: bool,
    fuel_stations: int,
    wells_private: int,
    surface_water_sources: int,
    days_water_reserve: float,
    backup_power_water_plant: bool,
) -> float:
    """
    Score physical infrastructure domain capacity [0, 1].

    Physical transport, fuel supply, and water infrastructure.
    """
    transport = (
        (0.20 if highway_access else 0.0) +
        (0.15 if rail_access    else 0.0) +
        min(0.10, fuel_stations / 5.0 * 0.10)
    )
    water_infra = (
        min(0.20, wells_private          / 10.0 * 0.20) +
        min(0.15, surface_water_sources  / 3.0  * 0.15) +
        min(0.10, days_water_reserve     / 7.0  * 0.10) +
        (0.10 if backup_power_water_plant else 0.0)
    )
    return min(1.0, transport + water_infra)


# ---------------------------------------------------------------------------
# Buffer scoring — "reserve depth" for each domain
# ---------------------------------------------------------------------------

def food_buffer(days_food_supply_retail: float,
                food_bank_present: bool) -> float:
    """Buffer = normalised retail days on hand + food-bank padding."""
    b = min(1.0, days_food_supply_retail / 14.0)
    if food_bank_present:
        b = min(1.0, b + 0.10)
    return b


def energy_buffer(fuel_reserve_days: float,
                  backup_generators: int,
                  local_generation_mw: float) -> float:
    """Buffer = fuel reserve normalised to 30 days + generator redundancy."""
    b = min(0.60, fuel_reserve_days / 30.0 * 0.60)
    b += min(0.25, backup_generators / 5.0 * 0.25)
    b += min(0.15, local_generation_mw / 5.0 * 0.15)
    return min(1.0, b)


def social_buffer(mutual_aid_networks: int,
                  faith_communities: int) -> float:
    """Buffer = mutual aid / informal support density."""
    return min(1.0,
               min(0.60, mutual_aid_networks / 3.0 * 0.60) +
               min(0.40, faith_communities   / 10.0 * 0.40))


def institutional_buffer(community_alert_system: bool,
                         ham_radio_operators: int,
                         backup_power_water_plant: bool) -> float:
    """Buffer = redundant institutional channels."""
    b = (0.30 if community_alert_system    else 0.0)
    b += min(0.40, ham_radio_operators / 5.0 * 0.40)
    b += (0.30 if backup_power_water_plant else 0.0)
    return min(1.0, b)


def knowledge_buffer(skill_holders_identified: int,
                     ham_radio_operators: int) -> float:
    """Buffer = identified skills + low-tech comms (most fragile domain)."""
    return min(1.0,
               min(0.70, skill_holders_identified / 10.0 * 0.70) +
               min(0.30, ham_radio_operators / 5.0 * 0.30))


def infrastructure_buffer(wells_private: int,
                          surface_water_sources: int,
                          days_water_reserve: float) -> float:
    """Buffer = backup water supply depth."""
    return min(1.0,
               min(0.40, wells_private         / 10.0 * 0.40) +
               min(0.30, surface_water_sources / 3.0  * 0.30) +
               min(0.30, days_water_reserve    / 7.0  * 0.30))


# ---------------------------------------------------------------------------
# Profile → domain dict helpers
# ---------------------------------------------------------------------------

def profile_to_capacities(p: dict) -> dict:
    """
    Convert a flat CommunityProfile dict to a 6-domain capacity dict.

    Accepts both dataclass instances (via __dict__) and plain dicts.
    """
    if not isinstance(p, dict):
        p = p.__dict__
    return {
        "food": food_capacity(
            days_food_supply_retail  = float(p.get("days_food_supply_retail", 3.0)),
            active_farms_local       = int(p.get("active_farms_local", 0)),
            community_gardens_acres  = float(p.get("community_gardens_acres", 0.0)),
            population               = int(p.get("population", 1)),
            farmers_market           = bool(p.get("farmers_market", False)),
            grain_elevator_present   = bool(p.get("grain_elevator_present", False)),
            food_bank_present        = bool(p.get("food_bank_present", False)),
        ),
        "energy": energy_capacity(
            grid_connected      = bool(p.get("grid_connected", True)),
            local_generation_mw = float(p.get("local_generation_mw", 0.0)),
            solar_installations = int(p.get("solar_installations", 0)),
            wind_capacity_mw    = float(p.get("wind_capacity_mw", 0.0)),
            backup_generators   = int(p.get("backup_generators", 0)),
            fuel_reserve_days   = float(p.get("fuel_reserve_days", 3.0)),
        ),
        "social": social_capacity(
            population          = int(p.get("population", 1)),
            hospital_present    = bool(p.get("hospital_present", False)),
            clinic_present      = bool(p.get("clinic_present", True)),
            pharmacy_count      = int(p.get("pharmacy_count", 1)),
            ems_available       = bool(p.get("ems_available", True)),
            mutual_aid_networks = int(p.get("mutual_aid_networks", 0)),
            faith_communities   = int(p.get("faith_communities", 0)),
            civic_organizations = int(p.get("civic_organizations", 0)),
        ),
        "institutional": institutional_capacity(
            cell_towers               = int(p.get("cell_towers", 1)),
            internet_providers        = int(p.get("internet_providers", 1)),
            ham_radio_operators       = int(p.get("ham_radio_operators", 0)),
            community_alert_system    = bool(p.get("community_alert_system", False)),
            ems_available             = bool(p.get("ems_available", True)),
            water_treatment_functional= bool(p.get("water_treatment_functional", True)),
            backup_power_water_plant  = bool(p.get("backup_power_water_plant", False)),
        ),
        "knowledge": knowledge_capacity(
            skill_holders_identified = int(p.get("skill_holders_identified", 0)),
            ham_radio_operators      = int(p.get("ham_radio_operators", 0)),
            rail_access              = bool(p.get("rail_access", False)),
            highway_access           = bool(p.get("highway_access", True)),
            active_farms_local       = int(p.get("active_farms_local", 0)),
        ),
        "infrastructure": infrastructure_capacity(
            highway_access           = bool(p.get("highway_access", True)),
            rail_access              = bool(p.get("rail_access", False)),
            fuel_stations            = int(p.get("fuel_stations", 1)),
            wells_private            = int(p.get("wells_private", 0)),
            surface_water_sources    = int(p.get("surface_water_sources", 0)),
            days_water_reserve       = float(p.get("days_water_reserve", 1.0)),
            backup_power_water_plant = bool(p.get("backup_power_water_plant", False)),
        ),
    }


def profile_to_buffers(p: dict) -> dict:
    """Convert a CommunityProfile dict to a 6-domain buffer dict."""
    if not isinstance(p, dict):
        p = p.__dict__
    return {
        "food": food_buffer(
            days_food_supply_retail = float(p.get("days_food_supply_retail", 3.0)),
            food_bank_present       = bool(p.get("food_bank_present", False)),
        ),
        "energy": energy_buffer(
            fuel_reserve_days   = float(p.get("fuel_reserve_days", 3.0)),
            backup_generators   = int(p.get("backup_generators", 0)),
            local_generation_mw = float(p.get("local_generation_mw", 0.0)),
        ),
        "social": social_buffer(
            mutual_aid_networks = int(p.get("mutual_aid_networks", 0)),
            faith_communities   = int(p.get("faith_communities", 0)),
        ),
        "institutional": institutional_buffer(
            community_alert_system   = bool(p.get("community_alert_system", False)),
            ham_radio_operators      = int(p.get("ham_radio_operators", 0)),
            backup_power_water_plant = bool(p.get("backup_power_water_plant", False)),
        ),
        "knowledge": knowledge_buffer(
            skill_holders_identified = int(p.get("skill_holders_identified", 0)),
            ham_radio_operators      = int(p.get("ham_radio_operators", 0)),
        ),
        "infrastructure": infrastructure_buffer(
            wells_private         = int(p.get("wells_private", 0)),
            surface_water_sources = int(p.get("surface_water_sources", 0)),
            days_water_reserve    = float(p.get("days_water_reserve", 1.0)),
        ),
    }


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class CommunityBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes a CommunityProfile (urban-resilience-sim) into a 39-bit
    Gray-coded binary string via the 6-domain octahedral resilience model.

    Input geometry dict keys
    ------------------------
    Flat CommunityProfile fields — or a CommunityProfile dataclass instance
    passed as the geometry_data argument.  Supported fields:

      name, population, county, state,
      grocery_stores, days_food_supply_retail, farmers_market,
      community_gardens_acres, active_farms_local, grain_elevator_present,
      food_bank_present,
      municipal_water, wells_private, surface_water_sources,
      water_treatment_functional, backup_power_water_plant, days_water_reserve,
      grid_connected, local_generation_mw, solar_installations,
      wind_capacity_mw, backup_generators, fuel_reserve_days,
      hospital_present, clinic_present, pharmacy_count, ems_available,
      cell_towers, internet_providers, ham_radio_operators,
      community_alert_system,
      highway_access, rail_access, fuel_stations,
      skill_holders_identified, mutual_aid_networks, faith_communities,
      civic_organizations,

    Optional override keys
    ----------------------
    crisis_phase      : str  — override auto-computed phase
    dominant_domain   : str  — override auto-computed dominant
    max_amplification : float
    spillover_active  : bool
    load_bearing      : bool
    decision_lag_hours: float
    """

    def __init__(self):
        super().__init__("community")

    def from_geometry(self, geometry_data):
        """Load community profile (dict or CommunityProfile dataclass)."""
        if not isinstance(geometry_data, dict):
            geometry_data = geometry_data.__dict__
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert community profile to a 39-bit binary string.

        Raises
        ------
        ValueError
            If from_geometry() has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        p    = self.input_geometry
        caps = profile_to_capacities(p)
        bufs = profile_to_buffers(p)

        # Build resilience geometry dict, forwarding any override keys
        geometry = {"capacities": caps, "buffers": bufs}
        for key in ("crisis_phase", "dominant_domain", "max_amplification",
                    "spillover_active", "load_bearing", "decision_lag_hours"):
            if key in p:
                geometry[key] = p[key]

        enc = ResilienceBridgeEncoder()
        enc.from_geometry(geometry)
        self.binary_output = enc.to_binary()
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Community Bridge Encoder — Demo")
    print("=" * 60)

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
        caps = profile_to_capacities(prof)
        bufs = profile_to_buffers(prof)
        enc  = CommunityBridgeEncoder()
        enc.from_geometry(prof)
        bits = enc.to_binary()

        print(f"\n── {prof['name']} ──")
        print(f"  Capacities : {', '.join(f'{k}={v:.2f}' for k, v in caps.items())}")
        print(f"  Buffers    : {', '.join(f'{k}={v:.2f}' for k, v in bufs.items())}")
        print(f"  Crisis     : {crisis_phase(caps, bufs)}")
        print(f"  Binary     : {bits}  ({len(bits)}b)")


# core/integrations/community_taf_bridge.py
class CommunityTAFBridge:
    """
    Maps CommunityBridgeEncoder outputs to TAF energy accounting.
    
    A community is just another organism in the TAF framework—
    it consumes energy (food, fuel), produces output (labor, services),
    and can be extracted from (by distant supply chains, absentee
    ownership, institutional neglect).
    
    The six octahedral domains map to TAF's compression operators:
      +X food/water    → Π_embodied (physical sustenance)
      -X energy        → Π_econ (energy is the economic substrate)
      +Y social        → Π_embodied (informal, pre-institutional)
      -Y institutional → Π_schema / Π_legal (formal systems)
      +Z knowledge     → Π_raw (closest to 𝒞 coupling)
      -Z infrastructure → Π_econ / Π_schema (built capital)
    """

Where it could go deeper (not broken, just expandable):

1. The population denominator in food_capacity is doing heavy lifting. A community of 10,000 with the same farm/garden infrastructure as one of 50,000 scores significantly higher—correctly, because the same calories go further. But this also means population decline (a real resilience pattern) inflates capacity scores. Worth a comment acknowledging this is a feature, not a bug: a shrinking town becomes more food-resilient per capita, but that's a symptom of systemic decline.
2. The buffer functions could benefit from alternative computing representations. Think about what each buffer means in non-binary terms:
   · food_buffer → Ternary: negative when reserves are below 3 days (RESTRAIN), positive above 14 (ACTIVATE)
   · energy_buffer → Stochastic: fuel reserves are inherently probabilistic (delivery may or may not arrive)
   · knowledge_buffer → Quantum: skill holders represent superposed capability—someone might have the skill when needed (Born's rule collapse at crisis time)
   · institutional_buffer → Approximate: redundancy is inherently a confidence-bound problem, not a binary one
3. The coupling to ResilienceBridgeEncoder is clean but opaque. You delegate to enc.to_binary() and trust it. That's fine for the encoder's stated purpose, but for debugging/audit you might want a method that returns both the binary string and the intermediate geometry dict it's feeding to ResilienceBridgeEncoder—so you can inspect what capacities/buffers actually got passed.

One design question: The crisis_phase auto-computation (line at the bottom: crisis_phase(caps, bufs)) isn't defined in this file—it's imported from resilience_encoder. Is the crisis phase a function of capacities+buffers alone, or does it also need the coupling terms from Section C? If the latter, computing it before the binary encoding exists creates a chicken-and-egg problem.
