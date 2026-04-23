"""Civilization Evaluator — Axis Geometry Through History (Investigation Stage)
=============================================================================

This module applies the exploratory axis-geometry layer to historical or
civilizational profiles. It is intentionally framed as a **research scaffold**
for comparative reasoning rather than a settled historical inference engine.

Status
------
This file is **under investigation and review**. The database values and the
resulting interpretations are heuristic placeholders for structured discussion,
not authoritative historical measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from bridges.investigation.axis_geometry_bridge import AxisGeometry, AxisGeometryState


class CivilizationPeriod(Enum):
    """Broad period labels retained for navigation and comparison."""

    PRE_AGRICULTURAL = "pre_agricultural"
    EARLY_AGRICULTURAL = "early_agricultural"
    CLASSICAL = "classical"
    POST_CLASSICAL = "post_classical"
    EARLY_MODERN = "early_modern"
    INDUSTRIAL = "industrial"
    CONTEMPORARY = "contemporary"


@dataclass
class CivilizationProfile:
    """A civilization profile mapped onto the same six domains as the community bridge."""

    name: str
    period: CivilizationPeriod
    location: str
    approximate_dates: str
    peak_population: int

    days_food_supply_retail: float
    active_farms_local: int
    community_gardens_acres: float
    farmers_market: bool
    grain_elevator_present: bool
    food_bank_present: bool

    grid_connected: bool
    local_generation_mw: float
    solar_installations: int
    wind_capacity_mw: float
    backup_generators: int
    fuel_reserve_days: float

    hospital_present: bool
    clinic_present: bool
    pharmacy_count: int
    ems_available: bool
    mutual_aid_networks: int
    faith_communities: int
    civic_organizations: int

    cell_towers: int
    internet_providers: int
    ham_radio_operators: int
    community_alert_system: bool
    water_treatment_functional: bool
    backup_power_water_plant: bool

    skill_holders_identified: int
    rail_access: bool
    highway_access: bool

    wells_private: int
    surface_water_sources: int
    days_water_reserve: float
    fuel_stations: int

    collapse_mechanism: str = ""
    axis_geometry_hypothesis: str = ""

    def to_profile_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "population": self.peak_population,
            "days_food_supply_retail": self.days_food_supply_retail,
            "active_farms_local": self.active_farms_local,
            "community_gardens_acres": self.community_gardens_acres,
            "farmers_market": self.farmers_market,
            "grain_elevator_present": self.grain_elevator_present,
            "food_bank_present": self.food_bank_present,
            "grid_connected": self.grid_connected,
            "local_generation_mw": self.local_generation_mw,
            "solar_installations": self.solar_installations,
            "wind_capacity_mw": self.wind_capacity_mw,
            "backup_generators": self.backup_generators,
            "fuel_reserve_days": self.fuel_reserve_days,
            "hospital_present": self.hospital_present,
            "clinic_present": self.clinic_present,
            "pharmacy_count": self.pharmacy_count,
            "ems_available": self.ems_available,
            "mutual_aid_networks": self.mutual_aid_networks,
            "faith_communities": self.faith_communities,
            "civic_organizations": self.civic_organizations,
            "cell_towers": self.cell_towers,
            "internet_providers": self.internet_providers,
            "ham_radio_operators": self.ham_radio_operators,
            "community_alert_system": self.community_alert_system,
            "water_treatment_functional": self.water_treatment_functional,
            "backup_power_water_plant": self.backup_power_water_plant,
            "skill_holders_identified": self.skill_holders_identified,
            "rail_access": self.rail_access,
            "highway_access": self.highway_access,
            "wells_private": self.wells_private,
            "surface_water_sources": self.surface_water_sources,
            "days_water_reserve": self.days_water_reserve,
            "fuel_stations": self.fuel_stations,
        }


CIVILIZATIONS: List[CivilizationProfile] = [
    CivilizationProfile(
        name="Toba Survivors (Pinnacle Point)",
        period=CivilizationPeriod.PRE_AGRICULTURAL,
        location="Southern Africa",
        approximate_dates="~74,000 BP",
        peak_population=500,
        days_food_supply_retail=2.0,
        active_farms_local=0,
        community_gardens_acres=0.0,
        farmers_market=False,
        grain_elevator_present=False,
        food_bank_present=False,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=3.0,
        hospital_present=False,
        clinic_present=False,
        pharmacy_count=0,
        ems_available=False,
        mutual_aid_networks=5,
        faith_communities=3,
        civic_organizations=4,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=False,
        backup_power_water_plant=False,
        skill_holders_identified=12,
        rail_access=False,
        highway_access=False,
        wells_private=0,
        surface_water_sources=5,
        days_water_reserve=1.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative survivor case used for exploratory comparison.",
        axis_geometry_hypothesis="Exploratory hypothesis: low resources but relatively coherent axis coupling.",
    ),
    CivilizationProfile(
        name="Göbekli Tepe Builders",
        period=CivilizationPeriod.PRE_AGRICULTURAL,
        location="Anatolia",
        approximate_dates="~9600-8000 BCE",
        peak_population=3000,
        days_food_supply_retail=5.0,
        active_farms_local=0,
        community_gardens_acres=0.0,
        farmers_market=False,
        grain_elevator_present=False,
        food_bank_present=True,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=7.0,
        hospital_present=False,
        clinic_present=False,
        pharmacy_count=0,
        ems_available=False,
        mutual_aid_networks=4,
        faith_communities=6,
        civic_organizations=5,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=False,
        backup_power_water_plant=False,
        skill_holders_identified=20,
        rail_access=False,
        highway_access=False,
        wells_private=2,
        surface_water_sources=3,
        days_water_reserve=3.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative ritual-construction society used for exploratory comparison.",
        axis_geometry_hypothesis="Exploratory hypothesis: monument coordination may reflect cross-axis coherence.",
    ),
    CivilizationProfile(
        name="Indus Valley (Harappan)",
        period=CivilizationPeriod.EARLY_AGRICULTURAL,
        location="Indus River Basin",
        approximate_dates="~3300-1300 BCE",
        peak_population=5000000,
        days_food_supply_retail=90.0,
        active_farms_local=500,
        community_gardens_acres=10000.0,
        farmers_market=True,
        grain_elevator_present=True,
        food_bank_present=True,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=30.0,
        hospital_present=False,
        clinic_present=True,
        pharmacy_count=5,
        ems_available=False,
        mutual_aid_networks=3,
        faith_communities=4,
        civic_organizations=8,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=True,
        backup_power_water_plant=False,
        skill_holders_identified=30,
        rail_access=False,
        highway_access=True,
        wells_private=100,
        surface_water_sources=2,
        days_water_reserve=60.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative climate-and-infrastructure stress case.",
        axis_geometry_hypothesis="Exploratory hypothesis: strong infrastructure may still decouple from adaptive transport.",
    ),
    CivilizationProfile(
        name="Norte Chico (Caral)",
        period=CivilizationPeriod.EARLY_AGRICULTURAL,
        location="Peruvian Coast",
        approximate_dates="~3500-1800 BCE",
        peak_population=30000,
        days_food_supply_retail=30.0,
        active_farms_local=20,
        community_gardens_acres=2000.0,
        farmers_market=True,
        grain_elevator_present=False,
        food_bank_present=True,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=14.0,
        hospital_present=False,
        clinic_present=False,
        pharmacy_count=0,
        ems_available=False,
        mutual_aid_networks=4,
        faith_communities=5,
        civic_organizations=4,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=False,
        backup_power_water_plant=False,
        skill_holders_identified=15,
        rail_access=False,
        highway_access=False,
        wells_private=5,
        surface_water_sources=4,
        days_water_reserve=14.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative small-scale exchange society for comparative review.",
        axis_geometry_hypothesis="Exploratory hypothesis: modest resources but relatively balanced geometry.",
    ),
    CivilizationProfile(
        name="Roman Empire (Peak)",
        period=CivilizationPeriod.CLASSICAL,
        location="Mediterranean Basin",
        approximate_dates="~100-200 CE",
        peak_population=65000000,
        days_food_supply_retail=180.0,
        active_farms_local=5000,
        community_gardens_acres=500000.0,
        farmers_market=True,
        grain_elevator_present=True,
        food_bank_present=True,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=60.0,
        hospital_present=True,
        clinic_present=True,
        pharmacy_count=20,
        ems_available=True,
        mutual_aid_networks=5,
        faith_communities=10,
        civic_organizations=8,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=True,
        backup_power_water_plant=False,
        skill_holders_identified=50,
        rail_access=False,
        highway_access=True,
        wells_private=500,
        surface_water_sources=10,
        days_water_reserve=90.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative large-imperial case with multi-domain complexity.",
        axis_geometry_hypothesis="Exploratory hypothesis: high capacity can still hide social or institutional path dependence.",
    ),
    CivilizationProfile(
        name="Classic Maya (Peak)",
        period=CivilizationPeriod.CLASSICAL,
        location="Mesoamerica",
        approximate_dates="~250-900 CE",
        peak_population=2000000,
        days_food_supply_retail=60.0,
        active_farms_local=200,
        community_gardens_acres=50000.0,
        farmers_market=True,
        grain_elevator_present=True,
        food_bank_present=True,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=30.0,
        hospital_present=False,
        clinic_present=True,
        pharmacy_count=5,
        ems_available=False,
        mutual_aid_networks=4,
        faith_communities=8,
        civic_organizations=6,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=True,
        backup_power_water_plant=False,
        skill_holders_identified=25,
        rail_access=False,
        highway_access=True,
        wells_private=0,
        surface_water_sources=3,
        days_water_reserve=180.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative drought-and-fragmentation case for review.",
        axis_geometry_hypothesis="Exploratory hypothesis: water knowledge may fail to transport across stressed domains.",
    ),
    CivilizationProfile(
        name="Angkor (Khmer Empire)",
        period=CivilizationPeriod.CLASSICAL,
        location="Southeast Asia",
        approximate_dates="~900-1431 CE",
        peak_population=1000000,
        days_food_supply_retail=120.0,
        active_farms_local=300,
        community_gardens_acres=100000.0,
        farmers_market=True,
        grain_elevator_present=True,
        food_bank_present=True,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=45.0,
        hospital_present=True,
        clinic_present=True,
        pharmacy_count=8,
        ems_available=False,
        mutual_aid_networks=4,
        faith_communities=7,
        civic_organizations=6,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=True,
        backup_power_water_plant=False,
        skill_holders_identified=30,
        rail_access=False,
        highway_access=True,
        wells_private=50,
        surface_water_sources=5,
        days_water_reserve=120.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative infrastructure-maintenance stress case.",
        axis_geometry_hypothesis="Exploratory hypothesis: heavy infrastructure dependency may amplify institutional decoupling.",
    ),
    CivilizationProfile(
        name="Easter Island (Rapa Nui, Pre-Contact Peak)",
        period=CivilizationPeriod.POST_CLASSICAL,
        location="Pacific Ocean",
        approximate_dates="~1200-1600 CE",
        peak_population=15000,
        days_food_supply_retail=30.0,
        active_farms_local=10,
        community_gardens_acres=500.0,
        farmers_market=True,
        grain_elevator_present=False,
        food_bank_present=True,
        grid_connected=False,
        local_generation_mw=0.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=0,
        fuel_reserve_days=14.0,
        hospital_present=False,
        clinic_present=False,
        pharmacy_count=0,
        ems_available=False,
        mutual_aid_networks=4,
        faith_communities=8,
        civic_organizations=4,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=0,
        community_alert_system=True,
        water_treatment_functional=False,
        backup_power_water_plant=False,
        skill_holders_identified=18,
        rail_access=False,
        highway_access=True,
        wells_private=3,
        surface_water_sources=2,
        days_water_reserve=7.0,
        fuel_stations=0,
        collapse_mechanism="Illustrative island fragility case used for review.",
        axis_geometry_hypothesis="Exploratory hypothesis: external shocks can force geometry from decoupling toward fracture.",
    ),
    CivilizationProfile(
        name="Soviet Union (Late Period)",
        period=CivilizationPeriod.INDUSTRIAL,
        location="Eurasia",
        approximate_dates="~1970-1991 CE",
        peak_population=293000000,
        days_food_supply_retail=45.0,
        active_farms_local=5000,
        community_gardens_acres=5000000.0,
        farmers_market=False,
        grain_elevator_present=True,
        food_bank_present=True,
        grid_connected=True,
        local_generation_mw=50000.0,
        solar_installations=0,
        wind_capacity_mw=0.0,
        backup_generators=100,
        fuel_reserve_days=180.0,
        hospital_present=True,
        clinic_present=True,
        pharmacy_count=50,
        ems_available=True,
        mutual_aid_networks=2,
        faith_communities=2,
        civic_organizations=1,
        cell_towers=0,
        internet_providers=0,
        ham_radio_operators=1,
        community_alert_system=True,
        water_treatment_functional=True,
        backup_power_water_plant=True,
        skill_holders_identified=40,
        rail_access=True,
        highway_access=True,
        wells_private=100,
        surface_water_sources=20,
        days_water_reserve=90.0,
        fuel_stations=5000,
        collapse_mechanism="Illustrative rigidity-and-legitimacy stress case.",
        axis_geometry_hypothesis="Exploratory hypothesis: institutional hypertrophy can reduce adaptive social buffering.",
    ),
    CivilizationProfile(
        name="Contemporary United States",
        period=CivilizationPeriod.CONTEMPORARY,
        location="North America",
        approximate_dates="~2000-2024 CE",
        peak_population=335000000,
        days_food_supply_retail=3.0,
        active_farms_local=2000000,
        community_gardens_acres=10000000.0,
        farmers_market=True,
        grain_elevator_present=True,
        food_bank_present=True,
        grid_connected=True,
        local_generation_mw=100000.0,
        solar_installations=5000000,
        wind_capacity_mw=150000.0,
        backup_generators=50000,
        fuel_reserve_days=30.0,
        hospital_present=True,
        clinic_present=True,
        pharmacy_count=67000,
        ems_available=True,
        mutual_aid_networks=3,
        faith_communities=6,
        civic_organizations=5,
        cell_towers=150000,
        internet_providers=50,
        ham_radio_operators=4,
        community_alert_system=True,
        water_treatment_functional=True,
        backup_power_water_plant=True,
        skill_holders_identified=35,
        rail_access=True,
        highway_access=True,
        wells_private=20000000,
        surface_water_sources=250,
        days_water_reserve=3.0,
        fuel_stations=150000,
        collapse_mechanism="No historical terminal outcome; contemporary placeholder for exploratory diagnosis.",
        axis_geometry_hypothesis="Exploratory hypothesis: high resources may coexist with thin buffers and cross-axis fragility.",
    ),
]


@dataclass
class CivilizationEvaluation:
    """A single exploratory civilization evaluation."""

    profile: CivilizationProfile
    geometry: AxisGeometry
    innovation: Dict[str, Any]
    resource_score: float
    geometry_score: float
    innovation_score: float
    collapse_risk: str
    collapse_alignment: bool

    def summary(self) -> str:
        return (
            f"{self.profile.name:35s} | "
            f"Resources: {self.resource_score:.2f} | "
            f"Geometry: {self.geometry_score:.2f} | "
            f"Innovation: {self.innovation_score:.2f} | "
            f"State: {self.geometry.geometry_state.name:12s} | "
            f"Risk: {self.collapse_risk}"
        )


class CivilizationEvaluator:
    """Exploratory evaluator for historical or civilizational profiles."""

    def __init__(self) -> None:
        self.evaluations: List[CivilizationEvaluation] = []

    def evaluate(self, civilization: CivilizationProfile) -> CivilizationEvaluation:
        geometry = AxisGeometry().from_profile(civilization.to_profile_dict())
        innovation = geometry.compute_innovation_capacity()
        resource_score = sum(geometry.buffers.values()) / max(len(geometry.buffers), 1)
        collapse_risk = self._assess_collapse_risk(geometry, innovation)
        collapse_alignment = self._check_historical_alignment(civilization, geometry)
        evaluation = CivilizationEvaluation(
            profile=civilization,
            geometry=geometry,
            innovation=innovation,
            resource_score=resource_score,
            geometry_score=geometry.geometric_integrity,
            innovation_score=innovation["innovation_capacity"],
            collapse_risk=collapse_risk,
            collapse_alignment=collapse_alignment,
        )
        self.evaluations.append(evaluation)
        return evaluation

    def evaluate_all(self) -> List[CivilizationEvaluation]:
        self.evaluations = []
        for civ in CIVILIZATIONS:
            self.evaluate(civ)
        return self.evaluations

    def _assess_collapse_risk(self, geometry: AxisGeometry, innovation: Dict[str, Any]) -> str:
        state = geometry.geometry_state
        if state == AxisGeometryState.COHERENT:
            if innovation["mean_buffer"] < 0.3:
                return "LOW (scarcity-adapted, exploratory)"
            return "LOW (exploratory)"
        if state == AxisGeometryState.DECOUPLING:
            if len(geometry.decoupled_axes) <= 1:
                return "MODERATE (exploratory)"
            if len(geometry.decoupled_axes) <= 3:
                return "ELEVATED (exploratory)"
            return "HIGH (exploratory)"
        if geometry.holonomy_risk:
            return "CRITICAL (exploratory)"
        return "TERMINAL-LIKE (exploratory)"

    def _check_historical_alignment(self, civilization: CivilizationProfile, geometry: AxisGeometry) -> bool:
        survivors = {
            "Toba Survivors (Pinnacle Point)",
            "Göbekli Tepe Builders",
            "Norte Chico (Caral)",
        }
        collapsed = {
            "Indus Valley (Harappan)",
            "Classic Maya (Peak)",
            "Angkor (Khmer Empire)",
            "Roman Empire (Peak)",
            "Easter Island (Rapa Nui, Pre-Contact Peak)",
            "Soviet Union (Late Period)",
        }
        if civilization.name in survivors:
            return geometry.geometry_state in {AxisGeometryState.COHERENT, AxisGeometryState.DECOUPLING}
        if civilization.name in collapsed:
            return geometry.geometry_state in {AxisGeometryState.DECOUPLING, AxisGeometryState.FRACTURED}
        return True

    def comparative_analysis(self) -> str:
        if not self.evaluations:
            self.evaluate_all()
        lines = [
            "=" * 90,
            "CIVILIZATION AXIS GEOMETRY — COMPARATIVE ANALYSIS (INVESTIGATION STAGE)",
            "=" * 90,
            "",
            "All values and interpretations below are exploratory and under review.",
            "",
            f"{'Civilization':35s} {'Era':15s} {'State':12s} {'Resources':>9s} {'Geometry':>9s} {'Innovation':>10s} {'Collapse Risk':24s}",
            f"{'-'*35} {'-'*15} {'-'*12} {'-'*9} {'-'*9} {'-'*10} {'-'*24}",
        ]
        for evaluation in self.evaluations:
            lines.append(
                f"{evaluation.profile.name:35s} "
                f"{evaluation.profile.period.value:15s} "
                f"{evaluation.geometry.geometry_state.name:12s} "
                f"{evaluation.resource_score:9.3f} "
                f"{evaluation.geometry_score:9.3f} "
                f"{evaluation.innovation_score:10.3f} "
                f"{evaluation.collapse_risk[:24]:24s}"
            )
        aligned = sum(1 for e in self.evaluations if e.collapse_alignment)
        assessed = len([e for e in self.evaluations if e.profile.period != CivilizationPeriod.CONTEMPORARY])
        lines.append("")
        lines.append(f"Historical alignment proxy (exploratory): {aligned}/{assessed}")
        lines.append("=" * 90)
        return "\n".join(lines)

    def diagnose_civilization(self, name: str) -> str:
        for evaluation in self.evaluations:
            if evaluation.profile.name == name:
                return evaluation.geometry.diagnose()
        for civ in CIVILIZATIONS:
            if civ.name == name:
                return self.evaluate(civ).geometry.diagnose()
        return f"Civilization '{name}' not found in investigation database."


__all__ = [
    "CivilizationPeriod",
    "CivilizationProfile",
    "CivilizationEvaluation",
    "CivilizationEvaluator",
    "CIVILIZATIONS",
]


if __name__ == "__main__":
    evaluator = CivilizationEvaluator()
    evaluator.evaluate_all()
    print(evaluator.comparative_analysis())
