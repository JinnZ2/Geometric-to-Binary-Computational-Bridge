"""
Community Bridge Encoder
========================
Translates a **community-specific** resilience profile into the six-domain
capacity and buffer geometry consumed by ``ResilienceBridgeEncoder``, then
emits the canonical 39-bit Gray-coded binary string.

The important architectural distinction is that ``ResilienceBridgeEncoder`` is
**substrate-independent**: it encodes viability, reserves, coupling, and
cascade structure across any domain that can be expressed in the shared
six-axis resilience geometry. ``CommunityBridgeEncoder`` is one concrete
instantiation of that broader model for human-organism and settlement-scale
systems.

The CommunityProfile fields map onto the six octahedral resilience axes:

    +X = food/water       ← grocery stores, farms, water sources
    −X = energy           ← grid, local generation, reserves
    +Y = social           ← healthcare, mutual aid, community orgs
    −Y = institutional    ← communication, EMS, alert systems
    +Z = knowledge        ← skill holders, ham operators, rail/transport
    −Z = infrastructure   ← highway, fuel stations, backup systems

Each domain is scored in ``[0, 1]`` from the profile's boolean and numeric
fields. The buffer is the reserve component: how many days, backup layers, or
redundant channels remain when stress arrives.

This encoder is intentionally thin. It converts community viability,
redundancy, and reserve observations to the canonical octahedral domain
representation, then delegates the final binary encoding to
``ResilienceBridgeEncoder``.

Equations implemented
---------------------
  Food capacity    :  f(retail_days, local_pct) = min(1, retail_days/21 + local_pct/200)
  Energy capacity  :  e(grid, local_mw, backups) = weighted composite
  Social capacity  :  s(medical, aid, orgs) = weighted composite
  Institutional cap:  i(comms, ems, alert) = weighted composite
  Knowledge cap    :  k(skills, ham, rail) = weighted composite
  Infra capacity   :  n(highway, fuel, water) = weighted composite

  Buffer = reserve depth (days / redundant layers) normalised to ``[0, 1]``.

Bit layout
----------
39-bit Gray-coded output — identical layout to ``ResilienceBridgeEncoder``.
Section A (18b): domain capacities 3b Gray each (food, energy, social,
                 institutional, knowledge, infrastructure)
Section B  (9b): crisis phase, buffer state, flags
Section C  (6b): cascade coupling
Section D  (6b): seed geometry

License: CC-BY-4.0
"""

from __future__ import annotations

from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.resilience_encoder import (
    ResilienceBridgeEncoder,
    cascade_dominant,
    crisis_phase,
)


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
    Score food/water domain capacity in ``[0, 1]``.

    The quantity is intended as a thermodynamic viability proxy rather than a
    demographic label. A lower population can therefore raise per-capita food
    resilience, which is analytically meaningful even when it reflects a wider
    pattern of decline.
    """
    retail_score = min(1.0, days_food_supply_retail / 21.0) * 0.25

    if population > 0:
        annual_need = population * 2000 * 365
        garden_cal = community_gardens_acres * 3_000_000
        farm_cal = active_farms_local * 80 * 6_000_000
        local_pct = min(1.0, (garden_cal + farm_cal) / annual_need)
    else:
        local_pct = 0.0
    prod_score = local_pct * 0.45

    asset_score = (
        (0.10 if farmers_market else 0.0)
        + (0.10 if grain_elevator_present else 0.0)
        + (0.10 if food_bank_present else 0.0)
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
    """Score energy domain capacity in ``[0, 1]``."""
    base = 0.30 if grid_connected else 0.0
    local_mw = min(0.30, local_generation_mw / 10.0 * 0.30)
    solar = min(0.10, solar_installations / 20.0 * 0.10)
    wind = min(0.10, wind_capacity_mw / 5.0 * 0.10)
    gen = min(0.10, backup_generators / 10.0 * 0.10)
    fuel = min(0.10, fuel_reserve_days / 30.0 * 0.10)
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
    """Score social cohesion domain capacity in ``[0, 1]``."""
    del population  # reserved for future normalization choices
    medical = (
        (0.20 if hospital_present else 0.0)
        + (0.15 if clinic_present else 0.0)
        + min(0.10, pharmacy_count / 3.0 * 0.10)
        + (0.10 if ems_available else 0.0)
    )
    social_net = (
        min(0.20, mutual_aid_networks / 3.0 * 0.20)
        + min(0.15, faith_communities / 10.0 * 0.15)
        + min(0.10, civic_organizations / 5.0 * 0.10)
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
    """Score institutional domain capacity in ``[0, 1]``."""
    comms = (
        min(0.20, cell_towers / 4.0 * 0.20)
        + min(0.15, internet_providers / 2.0 * 0.15)
        + min(0.15, ham_radio_operators / 5.0 * 0.15)
        + (0.10 if community_alert_system else 0.0)
    )
    governance = (
        (0.15 if ems_available else 0.0)
        + (0.15 if water_treatment_functional else 0.0)
        + (0.10 if backup_power_water_plant else 0.0)
    )
    return min(1.0, comms + governance)


def knowledge_capacity(
    skill_holders_identified: int,
    ham_radio_operators: int,
    rail_access: bool,
    highway_access: bool,
    active_farms_local: int,
) -> float:
    """Score knowledge transmission domain capacity in ``[0, 1]``."""
    skills = min(0.40, skill_holders_identified / 10.0 * 0.40)
    ham = min(0.20, ham_radio_operators / 5.0 * 0.20)
    transit = (0.15 if rail_access else 0.0) + (0.10 if highway_access else 0.0)
    farm_k = min(0.15, active_farms_local / 20.0 * 0.15)
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
    """Score physical infrastructure domain capacity in ``[0, 1]``."""
    transport = (
        (0.20 if highway_access else 0.0)
        + (0.15 if rail_access else 0.0)
        + min(0.10, fuel_stations / 5.0 * 0.10)
    )
    water_infra = (
        min(0.20, wells_private / 10.0 * 0.20)
        + min(0.15, surface_water_sources / 3.0 * 0.15)
        + min(0.10, days_water_reserve / 7.0 * 0.10)
        + (0.10 if backup_power_water_plant else 0.0)
    )
    return min(1.0, transport + water_infra)


# ---------------------------------------------------------------------------
# Buffer scoring — reserve depth for each domain
# ---------------------------------------------------------------------------

def food_buffer(days_food_supply_retail: float, food_bank_present: bool) -> float:
    """Normalised retail food days plus food-bank padding."""
    buf = min(1.0, days_food_supply_retail / 14.0)
    if food_bank_present:
        buf = min(1.0, buf + 0.10)
    return buf


def energy_buffer(
    fuel_reserve_days: float,
    backup_generators: int,
    local_generation_mw: float,
) -> float:
    """Fuel reserve normalised to 30 days plus generation redundancy."""
    buf = min(0.60, fuel_reserve_days / 30.0 * 0.60)
    buf += min(0.25, backup_generators / 5.0 * 0.25)
    buf += min(0.15, local_generation_mw / 5.0 * 0.15)
    return min(1.0, buf)


def social_buffer(mutual_aid_networks: int, faith_communities: int) -> float:
    """Mutual aid and informal support density."""
    return min(
        1.0,
        min(0.60, mutual_aid_networks / 3.0 * 0.60)
        + min(0.40, faith_communities / 10.0 * 0.40),
    )


def institutional_buffer(
    community_alert_system: bool,
    ham_radio_operators: int,
    backup_power_water_plant: bool,
) -> float:
    """Redundant institutional communication and support channels."""
    buf = 0.30 if community_alert_system else 0.0
    buf += min(0.40, ham_radio_operators / 5.0 * 0.40)
    buf += 0.30 if backup_power_water_plant else 0.0
    return min(1.0, buf)


def knowledge_buffer(skill_holders_identified: int, ham_radio_operators: int) -> float:
    """Identified skills plus low-tech communication redundancy."""
    return min(
        1.0,
        min(0.70, skill_holders_identified / 10.0 * 0.70)
        + min(0.30, ham_radio_operators / 5.0 * 0.30),
    )


def infrastructure_buffer(
    wells_private: int,
    surface_water_sources: int,
    days_water_reserve: float,
) -> float:
    """Backup water and physical reserve depth."""
    return min(
        1.0,
        min(0.40, wells_private / 10.0 * 0.40)
        + min(0.30, surface_water_sources / 3.0 * 0.30)
        + min(0.30, days_water_reserve / 7.0 * 0.30),
    )


# ---------------------------------------------------------------------------
# Profile → domain dict helpers
# ---------------------------------------------------------------------------

def profile_to_capacities(p: dict) -> dict:
    """Convert a flat community profile to a six-domain capacity dict."""
    if not isinstance(p, dict):
        p = p.__dict__
    return {
        "food": food_capacity(
            days_food_supply_retail=float(p.get("days_food_supply_retail", 3.0)),
            active_farms_local=int(p.get("active_farms_local", 0)),
            community_gardens_acres=float(p.get("community_gardens_acres", 0.0)),
            population=int(p.get("population", 1)),
            farmers_market=bool(p.get("farmers_market", False)),
            grain_elevator_present=bool(p.get("grain_elevator_present", False)),
            food_bank_present=bool(p.get("food_bank_present", False)),
        ),
        "energy": energy_capacity(
            grid_connected=bool(p.get("grid_connected", True)),
            local_generation_mw=float(p.get("local_generation_mw", 0.0)),
            solar_installations=int(p.get("solar_installations", 0)),
            wind_capacity_mw=float(p.get("wind_capacity_mw", 0.0)),
            backup_generators=int(p.get("backup_generators", 0)),
            fuel_reserve_days=float(p.get("fuel_reserve_days", 3.0)),
        ),
        "social": social_capacity(
            population=int(p.get("population", 1)),
            hospital_present=bool(p.get("hospital_present", False)),
            clinic_present=bool(p.get("clinic_present", True)),
            pharmacy_count=int(p.get("pharmacy_count", 1)),
            ems_available=bool(p.get("ems_available", True)),
            mutual_aid_networks=int(p.get("mutual_aid_networks", 0)),
            faith_communities=int(p.get("faith_communities", 0)),
            civic_organizations=int(p.get("civic_organizations", 0)),
        ),
        "institutional": institutional_capacity(
            cell_towers=int(p.get("cell_towers", 1)),
            internet_providers=int(p.get("internet_providers", 1)),
            ham_radio_operators=int(p.get("ham_radio_operators", 0)),
            community_alert_system=bool(p.get("community_alert_system", False)),
            ems_available=bool(p.get("ems_available", True)),
            water_treatment_functional=bool(p.get("water_treatment_functional", True)),
            backup_power_water_plant=bool(p.get("backup_power_water_plant", False)),
        ),
        "knowledge": knowledge_capacity(
            skill_holders_identified=int(p.get("skill_holders_identified", 0)),
            ham_radio_operators=int(p.get("ham_radio_operators", 0)),
            rail_access=bool(p.get("rail_access", False)),
            highway_access=bool(p.get("highway_access", True)),
            active_farms_local=int(p.get("active_farms_local", 0)),
        ),
        "infrastructure": infrastructure_capacity(
            highway_access=bool(p.get("highway_access", True)),
            rail_access=bool(p.get("rail_access", False)),
            fuel_stations=int(p.get("fuel_stations", 1)),
            wells_private=int(p.get("wells_private", 0)),
            surface_water_sources=int(p.get("surface_water_sources", 0)),
            days_water_reserve=float(p.get("days_water_reserve", 1.0)),
            backup_power_water_plant=bool(p.get("backup_power_water_plant", False)),
        ),
    }


def profile_to_buffers(p: dict) -> dict:
    """Convert a flat community profile to a six-domain buffer dict."""
    if not isinstance(p, dict):
        p = p.__dict__
    return {
        "food": food_buffer(
            days_food_supply_retail=float(p.get("days_food_supply_retail", 3.0)),
            food_bank_present=bool(p.get("food_bank_present", False)),
        ),
        "energy": energy_buffer(
            fuel_reserve_days=float(p.get("fuel_reserve_days", 3.0)),
            backup_generators=int(p.get("backup_generators", 0)),
            local_generation_mw=float(p.get("local_generation_mw", 0.0)),
        ),
        "social": social_buffer(
            mutual_aid_networks=int(p.get("mutual_aid_networks", 0)),
            faith_communities=int(p.get("faith_communities", 0)),
        ),
        "institutional": institutional_buffer(
            community_alert_system=bool(p.get("community_alert_system", False)),
            ham_radio_operators=int(p.get("ham_radio_operators", 0)),
            backup_power_water_plant=bool(p.get("backup_power_water_plant", False)),
        ),
        "knowledge": knowledge_buffer(
            skill_holders_identified=int(p.get("skill_holders_identified", 0)),
            ham_radio_operators=int(p.get("ham_radio_operators", 0)),
        ),
        "infrastructure": infrastructure_buffer(
            wells_private=int(p.get("wells_private", 0)),
            surface_water_sources=int(p.get("surface_water_sources", 0)),
            days_water_reserve=float(p.get("days_water_reserve", 1.0)),
        ),
    }


def profile_to_resilience_geometry(p: dict) -> dict:
    """
    Convert a community profile into the substrate-independent resilience geometry.

    This is the main conceptual adapter between the community-specific bridge and
    the generic resilience encoder.
    """
    if not isinstance(p, dict):
        p = p.__dict__

    capacities = profile_to_capacities(p)
    buffers = profile_to_buffers(p)
    geometry = {"capacities": capacities, "buffers": buffers}

    for key in (
        "crisis_phase",
        "dominant_domain",
        "max_amplification",
        "spillover_active",
        "load_bearing",
        "decision_lag_hours",
    ):
        if key in p:
            geometry[key] = p[key]

    geometry.setdefault("crisis_phase", crisis_phase(capacities, buffers))
    geometry.setdefault("dominant_domain", cascade_dominant(capacities, buffers))
    return geometry


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class CommunityBridgeEncoder(BinaryBridgeEncoder):
    """
    Encode a community-specific profile through the substrate-independent
    resilience geometry and emit the standard 39-bit bridge representation.
    """

    def __init__(self):
        super().__init__("community")
        self._resilience_geometry = None

    def from_geometry(self, geometry_data):
        """Load a community profile from a dict or dataclass-like object."""
        if not isinstance(geometry_data, dict):
            geometry_data = geometry_data.__dict__
        self.input_geometry = geometry_data
        self._resilience_geometry = None
        return self

    def to_resilience_geometry(self) -> dict:
        """Expose the intermediate substrate-independent geometry for audit/debug."""
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before requesting the resilience geometry."
            )
        self._resilience_geometry = profile_to_resilience_geometry(self.input_geometry)
        return self._resilience_geometry

    def to_binary(self) -> str:
        """Convert the loaded community profile into the canonical 39-bit binary string."""
        geometry = self.to_resilience_geometry()
        enc = ResilienceBridgeEncoder().from_geometry(geometry)
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
        capacities = profile_to_capacities(prof)
        buffers = profile_to_buffers(prof)
        encoder = CommunityBridgeEncoder().from_geometry(prof)
        geometry = encoder.to_resilience_geometry()
        bits = encoder.to_binary()

        print(f"\n── {prof['name']} ──")
        print(f"  Capacities : {', '.join(f'{k}={v:.2f}' for k, v in capacities.items())}")
        print(f"  Buffers    : {', '.join(f'{k}={v:.2f}' for k, v in buffers.items())}")
        print(f"  Crisis     : {geometry['crisis_phase']}")
        print(f"  Dominant   : {geometry['dominant_domain']}")
        print(f"  Binary     : {bits}  ({len(bits)}b)")
