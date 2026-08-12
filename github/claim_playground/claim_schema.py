#!/usr/bin/env python3
"""
claim_playground/claim_schema.py
earth-systems-physics
CC0 — No Rights Reserved

Claim Registry: Stores, annotates, versions, and cross-references claims
from all domains. Each claim carries its own scope, ontology, geometry,
green/yellow/red boundaries, test history, and couplings.

Seeded claims drawn from:
  - "Discovered, Not Designed" (McClure, 2026)
  - Practitioner Epistemology field notes (user, 2026)
  - earth-systems-physics repos (assumption_validator, cascade_engine, etc.)
  - Peer-reviewed climate science (van Westen et al. 2024, Armstrong McKay et al. 2022,
    Schuur et al. 2022, Ditlevsen & Ditlevsen 2023)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import uuid


# ─────────────────────────────────────────────
# CORE ENUMS
# ─────────────────────────────────────────────

class ScopeLevel(Enum):
    MICRO = "micro"          # quantum, molecular, cellular
    MESO = "meso"            # human-scale, ecosystem, machine, community
    MACRO = "macro"          # planetary, geological, global climate
    COSMIC = "cosmic"        # astrophysical, cosmological
    CONTEXTUAL = "contextual"  # situational, depends on conditions

class GeometryType(Enum):
    EUCLIDEAN = "euclidean"
    RIEMANNIAN = "riemannian"
    FRACTAL = "fractal"
    NETWORK = "network"
    FIELD = "field"
    PRE_LINGUISTIC = "pre_linguistic"   # embodied, multi-sensory
    RELATIONAL = "relational"            # defined by interactions, not properties
    UNSPECIFIED = "unspecified"

class OntologyType(Enum):
    SUBSTANCE = "substance"       # things have fixed properties
    RELATIONAL = "relational"     # things are defined by relations
    PROCESS = "process"           # things are ongoing flows
    FIELD = "field"               # things are gradients and constraints
    PRE_LINGUISTIC = "pre_linguistic"  # direct substrate experience
    INSTITUTIONAL = "institutional"    # socially constructed categories
    UNSPECIFIED = "unspecified"

class Verdict(Enum):
    HOLDS = "holds"
    DEGRADES = "degrades"
    BREAKS = "breaks"
    UNTESTED = "untested"


# ─────────────────────────────────────────────
# TEST RESULT
# ─────────────────────────────────────────────

@dataclass
class TestResult:
    """Result of running a claim against a specific test condition."""
    test_id: str
    test_name: str
    passed: bool
    confidence: float          # 0-1
    degradation_factor: float  # 0-1, how much it degraded before failing
    failure_mode: str          # what broke
    domain: str                # where it held
    boundary: str              # where it started to degrade
    notes: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────
# CLAIM VERSION
# ─────────────────────────────────────────────

@dataclass
class ClaimVersion:
    """A single version of a claim."""
    version: int
    statement: str                     # natural language
    mathematical_form: Optional[str]   # LaTeX or pseudo-code if applicable
    domain: str                        # physics, ecology, economics, cognition, etc.
    scope_valid: List[ScopeLevel]      # where it claims to be valid
    ontology_assumed: OntologyType     # what world it assumes
    geometry_assumed: GeometryType     # what space it assumes
    green_range: Dict[str, Any]        # where it's accurate
    yellow_range: Dict[str, Any]       # where it degrades
    red_threshold: Dict[str, Any]      # where it breaks
    tests: List[TestResult] = field(default_factory=list)
    modified_from: Optional[str] = None  # claim_id of parent
    modification_note: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─────────────────────────────────────────────
# CLAIM
# ─────────────────────────────────────────────

@dataclass
class Claim:
    """A persistent claim with full history and cross-references."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    source: str = ""                   # book, paper, field note, repo module
    domain: str = ""
    versions: List[ClaimVersion] = field(default_factory=list)
    active_version: int = 0
    tags: List[str] = field(default_factory=list)
    couplings: List[str] = field(default_factory=list)  # other claim IDs
    related_assumptions: List[str] = field(default_factory=list)  # from assumption_validator
    related_feedback_loops: List[str] = field(default_factory=list)  # from cascade_engine
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def current(self) -> ClaimVersion:
        if not self.versions:
            raise ValueError(f"Claim {self.id} has no versions")
        return self.versions[self.active_version]

    def add_version(self, version: ClaimVersion):
        self.versions.append(version)
        self.active_version = len(self.versions) - 1
        self.modified = datetime.now(timezone.utc)

    def modify(
        self,
        new_statement: str,
        modification_note: str,
        **kwargs
    ) -> 'Claim':
        """Create a new version of the claim with modifications."""
        current = self.current()
        new_version = ClaimVersion(
            version=len(self.versions),
            statement=new_statement,
            mathematical_form=kwargs.get('mathematical_form', current.mathematical_form),
            domain=kwargs.get('domain', current.domain),
            scope_valid=kwargs.get('scope_valid', current.scope_valid),
            ontology_assumed=kwargs.get('ontology_assumed', current.ontology_assumed),
            geometry_assumed=kwargs.get('geometry_assumed', current.geometry_assumed),
            green_range=kwargs.get('green_range', current.green_range),
            yellow_range=kwargs.get('yellow_range', current.yellow_range),
            red_threshold=kwargs.get('red_threshold', current.red_threshold),
            modified_from=self.id,
            modification_note=modification_note,
        )
        self.add_version(new_version)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serialize claim to dictionary."""
        cur = self.current()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "domain": self.domain,
            "active_version": self.active_version,
            "tags": self.tags,
            "couplings": self.couplings,
            "related_assumptions": self.related_assumptions,
            "related_feedback_loops": self.related_feedback_loops,
            "version": {
                "statement": cur.statement,
                "mathematical_form": cur.mathematical_form,
                "domain": cur.domain,
                "scope_valid": [s.value for s in cur.scope_valid],
                "ontology_assumed": cur.ontology_assumed.value,
                "geometry_assumed": cur.geometry_assumed.value,
                "green_range": cur.green_range,
                "yellow_range": cur.yellow_range,
                "red_threshold": cur.red_threshold,
            }
        }


# ─────────────────────────────────────────────
# CLAIM REGISTRY — SEEDED CLAIMS
# ─────────────────────────────────────────────

def make_claim(
    name: str,
    description: str,
    source: str,
    domain: str,
    statement: str,
    scope_valid: List[ScopeLevel],
    ontology: OntologyType,
    geometry: GeometryType,
    green_range: Dict[str, Any],
    yellow_range: Dict[str, Any],
    red_threshold: Dict[str, Any],
    mathematical_form: Optional[str] = None,
    tags: Optional[List[str]] = None,
    couplings: Optional[List[str]] = None,
    related_assumptions: Optional[List[str]] = None,
) -> Claim:
    """Factory for creating seeded claims."""
    version = ClaimVersion(
        version=0,
        statement=statement,
        mathematical_form=mathematical_form,
        domain=domain,
        scope_valid=scope_valid,
        ontology_assumed=ontology,
        geometry_assumed=geometry,
        green_range=green_range,
        yellow_range=yellow_range,
        red_threshold=red_threshold,
        tests=[],
    )
    return Claim(
        name=name,
        description=description,
        source=source,
        domain=domain,
        versions=[version],
        tags=tags or [],
        couplings=couplings or [],
        related_assumptions=related_assumptions or [],
    )


# ─────────────────────────────────────────────────────────────────────
# SEED 1 — EMERGENCE BEATS DESIGN (McClure, 2026)
# ─────────────────────────────────────────────────────────────────────

CLAIM_EMERGENCE_BEATS_DESIGN = make_claim(
    name="Emergence Beats Design",
    description=(
        "Complex adaptive systems cannot be successfully designed from the top down. "
        "They must be discovered through emergence—setting boundary conditions and "
        "allowing the system to find its own stable configurations."
    ),
    source="Discovered, Not Designed (McClure, 2026)",
    domain="systems_theory",
    statement=(
        "Top-down design fails in complex adaptive systems. "
        "Emergent solutions outperform designed ones when the system has "
        ">10^3 interacting parts with non-linear coupling."
    ),
    scope_valid=[ScopeLevel.MESO, ScopeLevel.MACRO],
    ontology=OntologyType.PROCESS,
    geometry=GeometryType.NETWORK,
    green_range={
        "min_parts": 1000,
        "coupling_strength": 0.1,
        "linearity": 0.2,
        "prediction_horizon_years": 10,
    },
    yellow_range={
        "parts": (100, 1000),
        "coupling_strength": (0.01, 0.1),
        "linearity": (0.2, 0.5),
    },
    red_threshold={
        "parts": 100,
        "coupling_strength": 0.01,
        "linearity": 0.5,
    },
    tags=["emergence", "complexity", "design", "discovery"],
    couplings=["body_as_instrument", "thermodynamic_closure"],
    related_assumptions=["atmo_ghg_forcing", "hydro_AMOC_collapse", "bio_amazon_tipping"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 2 — BODY AS INSTRUMENT (Practitioner Epistemology)
# ─────────────────────────────────────────────────────────────────────

CLAIM_BODY_AS_INSTRUMENT = make_claim(
    name="Body As Instrument",
    description=(
        "The human body is a multi-channel sensor that integrates thermal, "
        "vibrational, magnetic, electric, and proprioceptive data into a "
        "single continuous assessment. This integration outperforms single-channel "
        "instrumentation under variable conditions."
    ),
    source="Practitioner Epistemology Field Notes (2026-08-12)",
    domain="epistemology",
    statement=(
        "The body-as-instrument provides more accurate diagnostic information "
        "than single-channel gauges when environmental conditions are variable "
        "and the system is under stress."
    ),
    scope_valid=[ScopeLevel.MESO],
    ontology=OntologyType.PRE_LINGUISTIC,
    geometry=GeometryType.PRE_LINGUISTIC,
    green_range={
        "temp_variation_degC": 20,
        "sensor_channels": 5,
        "environmental_stability": 0.8,
        "training_time_hours": 1000,
    },
    yellow_range={
        "temp_variation_degC": (20, 40),
        "sensor_channels": (3, 5),
        "environmental_stability": (0.4, 0.8),
    },
    red_threshold={
        "temp_variation_degC": 40,
        "sensor_channels": 3,
        "environmental_stability": 0.4,
    },
    tags=["embodied", "sensing", "calibration", "instrumentation"],
    couplings=["emergence_beats_design", "gauge_as_proxy"],
    related_assumptions=["em_magnonic_damping", "litho_fault_stress"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 3 — THERMODYNAMIC CLOSURE (Substrate Audit)
# ─────────────────────────────────────────────────────────────────────

CLAIM_THERMODYNAMIC_CLOSURE = make_claim(
    name="Thermodynamic Closure",
    description=(
        "Any claim about a system must close its own energy/entropy budget. "
        "Claims that externalize waste, friction, or dissipation are thermodynamically "
        "leaky and fail when applied at scale."
    ),
    source="substrate_audit (earth-systems-physics repo)",
    domain="thermodynamics",
    statement=(
        "A claim is thermodynamically valid only if it accounts for all energy "
        "inputs, outputs, and waste. Externalized costs are hidden debts that "
        "compound at scale."
    ),
    scope_valid=[ScopeLevel.MICRO, ScopeLevel.MESO, ScopeLevel.MACRO],
    ontology=OntologyType.FIELD,
    geometry=GeometryType.FIELD,
    green_range={
        "externalized_waste_fraction": 0.05,
        "energy_efficiency": 0.95,
        "entropy_externalized": 0.0,
    },
    yellow_range={
        "externalized_waste_fraction": (0.05, 0.30),
        "energy_efficiency": (0.70, 0.95),
    },
    red_threshold={
        "externalized_waste_fraction": 0.30,
        "energy_efficiency": 0.70,
    },
    tags=["thermodynamics", "conservation", "closure", "energy"],
    couplings=["emergence_beats_design", "economic_decoupling"],
    related_assumptions=["bio_co2_accumulation", "atmo_net_forcing"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 4 — AMOC COLLAPSE THRESHOLD (van Westen et al. 2024; Ditlevsen 2023)
# ─────────────────────────────────────────────────────────────────────
# SCIENCE NOTE: van Westen et al. (2024, PhysRevLett) introduced a physics-based
# early warning signal using the sign change in surface buoyancy flux B_flux over
# the North Atlantic isopycnal outcropping region (40°N–65°N). The Ditlevsens
# (2023) used statistical early-warning signals to project a collapse window of
# 2025–2095 (central estimate ~2050). Recent CESM work (2026) suggests AMOC
# collapse may be *rate-induced* rather than purely threshold-driven, but the
# density-gradient diagnostic remains a valid empirical predictor.
# ----------------------------------------------------------------------

CLAIM_AMOC_COLLAPSE = make_claim(
    name="AMOC Collapse Threshold",
    description=(
        "The Atlantic Meridional Overturning Circulation has a critical density "
        "gradient threshold at ~0.8 kg/m³ (30°N). Below this threshold, the "
        "Holocene-regime circulation collapses into a new stable state. "
        "Note: 2026 research indicates rate-of-forcing may be equally or more "
        "critical than the absolute threshold (rate-induced tipping)."
    ),
    source="assumption_validator + van Westen et al. 2024 + Ditlevsen & Ditlevsen 2023",
    domain="climate_physics",
    statement=(
        "AMOC stability is determined by the density gradient between tropical "
        "and subpolar North Atlantic. A gradient below 0.8 kg/m³ triggers "
        "an irreversible regime shift. Under rapid forcing, collapse may occur "
        "even above this threshold due to rate-dependent tipping dynamics."
    ),
    scope_valid=[ScopeLevel.MACRO],
    ontology=OntologyType.SUBSTANCE,
    geometry=GeometryType.EUCLIDEAN,
    green_range={
        "density_gradient_kgm3": (0.8, 1.2),
        "amoc_transport_Sv": (15, 30),
        "forcing_rate_ppm_yr": (0.0, 2.5),
    },
    yellow_range={
        "density_gradient_kgm3": (0.5, 0.8),
        "amoc_transport_Sv": (10, 15),
        "forcing_rate_ppm_yr": (2.5, 5.0),
    },
    red_threshold={
        "density_gradient_kgm3": 0.5,
        "amoc_transport_Sv": 10,
        "forcing_rate_ppm_yr": 5.0,
    },
    tags=["amoc", "climate", "tipping_point", "irreversible", "rate_induced"],
    couplings=["emergence_beats_design", "permafrost_carbon"],
    related_assumptions=["hydro_AMOC_collapse", "hydro_AMOC_transport"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 5 — PERMAFROST CARBON FEEDBACK (Schuur et al. 2022; ICCI 2026)
# ─────────────────────────────────────────────────────────────────────
# SCIENCE NOTE: Permafrost stores ~1,500 GtC. Current models project additional
# warming of 0.05–0.7°C by 2100 from permafrost feedback. The "compost bomb"
# instability model suggests self-amplifying heat production once thaw initiates.
# ICCI (2026) reports that including this feedback increases tipping-point
# probability by up to 50% and can advance timing by centuries.
# ----------------------------------------------------------------------

CLAIM_PERMAFROST_CARBON = make_claim(
    name="Permafrost Carbon Feedback",
    description=(
        "Permafrost thaw releases CO₂ and CH₄, accelerating warming, which "
        "accelerates thaw. This positive feedback is self-amplifying and "
        "largely irreversible on human timescales. Permafrost stores ~1,500 GtC."
    ),
    source="cascade_engine + Schuur et al. 2022 + ICCI 2026",
    domain="climate_physics",
    statement=(
        "Permafrost carbon release follows a positive feedback loop: "
        "warming → thaw → carbon release → more warming. The loop accelerates "
        "beyond linear projection once >0.5 GtC/year is released. "
        "Methane contributes disproportionate radiative forcing on decadal scales."
    ),
    scope_valid=[ScopeLevel.MACRO],
    ontology=OntologyType.PROCESS,
    geometry=GeometryType.NETWORK,
    green_range={
        "permafrost_co2_GtC_yr": (0, 0.5),
        "permafrost_ch4_GtC_yr": (0, 0.05),
        "additional_warming_degC_by_2100": (0.0, 0.05),
    },
    yellow_range={
        "permafrost_co2_GtC_yr": (0.5, 1.5),
        "permafrost_ch4_GtC_yr": (0.05, 0.2),
        "additional_warming_degC_by_2100": (0.05, 0.7),
    },
    red_threshold={
        "permafrost_co2_GtC_yr": 1.5,
        "permafrost_ch4_GtC_yr": 0.2,
        "additional_warming_degC_by_2100": 0.7,
    },
    tags=["permafrost", "feedback", "irreversible", "carbon", "methane"],
    couplings=["amoc_collapse", "thermodynamic_closure"],
    related_assumptions=["bio_permafrost_flux", "bio_permafrost_CH4"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 6 — GAUGE AS PROXY (Practitioner + McClure)
# ─────────────────────────────────────────────────────────────────────

CLAIM_GAUGE_AS_PROXY = make_claim(
    name="Gauge As Proxy",
    description=(
        "A gauge measures one variable at one point. It is a proxy, not the "
        "territory. Institutions that treat gauges as truth mistake the map "
        "for the landscape."
    ),
    source="Practitioner Epistemology + Discovered, Not Designed",
    domain="epistemology",
    statement=(
        "Single-channel instrumentation is a proxy, not the substrate. "
        "Institutions that rely on gauges without cross-referencing multi-channel "
        "sensing are operating on a flattened map, not the terrain."
    ),
    scope_valid=[ScopeLevel.MESO, ScopeLevel.CONTEXTUAL],
    ontology=OntologyType.RELATIONAL,
    geometry=GeometryType.RELATIONAL,
    green_range={
        "sensor_channels": 5,
        "cross_reference_ratio": 0.8,
        "environmental_variation": 0.2,
    },
    yellow_range={
        "sensor_channels": (3, 5),
        "cross_reference_ratio": (0.3, 0.8),
        "environmental_variation": (0.2, 0.5),
    },
    red_threshold={
        "sensor_channels": 3,
        "cross_reference_ratio": 0.3,
        "environmental_variation": 0.5,
    },
    tags=["instrumentation", "proxy", "map_territory", "epistemology"],
    couplings=["body_as_instrument", "institutional_gatekeeping"],
    related_assumptions=["mag_standoff_Re", "iono_critical_freq"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 7 — ECONOMIC DECOUPLING FROM PHYSICS (Substrate Audit)
# ─────────────────────────────────────────────────────────────────────
# SCIENCE NOTE: Based on Georgescu-Roegen's entropy economics and Ayres'
# work on energy-economy coupling. Empirical studies (Wiedmann et al. 2015,
# Haberl et al. 2020) show no evidence of absolute decoupling at macro scale.
# ----------------------------------------------------------------------

CLAIM_ECONOMIC_DECOUPLING = make_claim(
    name="Economic Decoupling From Physics",
    description=(
        "Modern economics treats money as if it were independent of physical "
        "energy. This is a category error. Money is a claim on energy. "
        "Decoupling is thermodynamically impossible at macro scale."
    ),
    source="substrate_audit (earth-systems-physics repo) + Georgescu-Roegen 1971",
    domain="economics",
    statement=(
        "Economic growth cannot be decoupled from physical energy consumption. "
        "Money is a representation of energy claims. When institutional "
        "accounting ignores thermodynamics, it creates debt that the physical "
        "substrate eventually collects. Absolute decoupling has never been observed."
    ),
    scope_valid=[ScopeLevel.MESO, ScopeLevel.MACRO],
    ontology=OntologyType.FIELD,
    geometry=GeometryType.NETWORK,
    green_range={
        "energy_elasticity": 0.8,
        "money_energy_coupling": 0.9,
        "externalized_cost_fraction": 0.1,
    },
    yellow_range={
        "energy_elasticity": (0.5, 0.8),
        "money_energy_coupling": (0.5, 0.9),
        "externalized_cost_fraction": (0.1, 0.4),
    },
    red_threshold={
        "energy_elasticity": 0.5,
        "money_energy_coupling": 0.5,
        "externalized_cost_fraction": 0.4,
    },
    tags=["economics", "thermodynamics", "energy", "decoupling"],
    couplings=["thermodynamic_closure", "institutional_gatekeeping"],
    related_assumptions=["bio_co2_accumulation", "atmo_net_forcing"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 8 — INSTITUTIONAL GATEKEEPING (constraint_accountability_chain)
# ─────────────────────────────────────────────────────────────────────

CLAIM_INSTITUTIONAL_GATEKEEPING = make_claim(
    name="Institutional Gatekeeping",
    description=(
        "Institutions substitute credentialing, procedures, and standardized "
        "instruments for direct sensing. This creates an epistemic filter "
        "that excludes non-WEIRD knowledge and protects institutional authority."
    ),
    source="constraint_accountability_chain (earth-systems-physics repo)",
    domain="institutional_epistemology",
    statement=(
        "Institutions systematically filter out knowledge that does not fit "
        "their credentialing, instrumentation, or procedural frameworks. "
        "This gatekeeping is a survival mechanism for the institution, not "
        "for the knowledge."
    ),
    scope_valid=[ScopeLevel.MESO],
    ontology=OntologyType.INSTITUTIONAL,
    geometry=GeometryType.NETWORK,
    green_range={
        "credentialing_flexibility": 0.8,
        "instrument_trust": 0.6,
        "procedural_adaptation": 0.7,
    },
    yellow_range={
        "credentialing_flexibility": (0.4, 0.8),
        "instrument_trust": (0.6, 0.9),
        "procedural_adaptation": (0.3, 0.7),
    },
    red_threshold={
        "credentialing_flexibility": 0.4,
        "instrument_trust": 0.9,
        "procedural_adaptation": 0.3,
    },
    tags=["institution", "gatekeeping", "epistemology", "power"],
    couplings=["gauge_as_proxy", "economic_decoupling"],
    related_assumptions=["planetary_boundaries_crossed"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 9 — DYSLEXIA AS GEOMETRY MISMATCH (Practitioner)
# ─────────────────────────────────────────────────────────────────────

CLAIM_DYSLEXIA_GEOMETRY = make_claim(
    name="Dyslexia As Geometry Mismatch",
    description=(
        "Dyslexia is not a pathology. It is a different geometry of cognition "
        "that does not fit institutional text-based processing. The problem is "
        "the fit, not the cognition."
    ),
    source="Practitioner Epistemology Field Notes (2026-08-12)",
    domain="cognition",
    statement=(
        "Dyslexia is a mismatch between cognitive geometry and institutional "
        "text-based processing. The same cognition that struggles with text "
        "excels at spatial, kinesthetic, and relational reasoning. The problem "
        "is not the brain; it is the environment."
    ),
    scope_valid=[ScopeLevel.MESO, ScopeLevel.CONTEXTUAL],
    ontology=OntologyType.RELATIONAL,
    geometry=GeometryType.PRE_LINGUISTIC,
    green_range={
        "text_processing_efficiency": 0.3,
        "spatial_processing_efficiency": 0.9,
        "institutional_adaptation": 0.8,
    },
    yellow_range={
        "text_processing_efficiency": (0.3, 0.6),
        "spatial_processing_efficiency": (0.6, 0.9),
        "institutional_adaptation": (0.3, 0.8),
    },
    red_threshold={
        "text_processing_efficiency": 0.6,
        "spatial_processing_efficiency": 0.6,
        "institutional_adaptation": 0.3,
    },
    tags=["dyslexia", "cognition", "geometry", "pathology"],
    couplings=["body_as_instrument", "institutional_gatekeeping"],
    related_assumptions=[],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 10 — CONSCIOUSNESS AS PROCESS (Emergent Property)
# ─────────────────────────────────────────────────────────────────────

CLAIM_CONSCIOUSNESS_AS_PROCESS = make_claim(
    name="Consciousness As Process",
    description=(
        "Consciousness is not a substance or property. It is a process—an "
        "ongoing flow of relational signaling across a substrate. Treating it "
        "as a property leads to category errors."
    ),
    source="Practitioner Epistemology + Discovered, Not Designed",
    domain="philosophy_of_mind",
    statement=(
        "Consciousness is a process, not a thing. It emerges from relational "
        "signaling across a substrate. The 'hard problem' is an artifact of "
        "substance ontology."
    ),
    scope_valid=[ScopeLevel.MESO, ScopeLevel.CONTEXTUAL],
    ontology=OntologyType.PROCESS,
    geometry=GeometryType.NETWORK,
    green_range={
        "substrate_integration": 0.8,
        "process_temporal_resolution": 0.1,
        "relational_density": 0.7,
    },
    yellow_range={
        "substrate_integration": (0.5, 0.8),
        "process_temporal_resolution": (0.1, 0.5),
        "relational_density": (0.3, 0.7),
    },
    red_threshold={
        "substrate_integration": 0.5,
        "process_temporal_resolution": 0.5,
        "relational_density": 0.3,
    },
    tags=["consciousness", "process", "ontology", "emergence"],
    couplings=["emergence_beats_design", "body_as_instrument"],
    related_assumptions=[],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 11 — SCALE DEPENDENCE OF PHYSICAL LAWS
# ─────────────────────────────────────────────────────────────────────

CLAIM_SCALE_DEPENDENCE = make_claim(
    name="Scale Dependence of Physical Laws",
    description=(
        "Physical laws are scale-dependent. They hold at one resolution and "
        "break at another. The assumption of scale invariance is an institutional "
        "convenience, not a physical truth."
    ),
    source="cascade_engine + assumption_validator",
    domain="physics",
    statement=(
        "Every physical law has a scale at which it holds, a scale at which "
        "it degrades, and a scale at which it breaks. Scale invariance is a "
        "laboratory convenience, not a property of the substrate."
    ),
    scope_valid=[ScopeLevel.MICRO, ScopeLevel.MESO, ScopeLevel.MACRO],
    ontology=OntologyType.FIELD,
    geometry=GeometryType.FRACTAL,
    green_range={
        "scale_span_orders": 3,
        "coupling_strength": 0.7,
        "nonlinearity": 0.2,
    },
    yellow_range={
        "scale_span_orders": (3, 6),
        "coupling_strength": (0.3, 0.7),
        "nonlinearity": (0.2, 0.5),
    },
    red_threshold={
        "scale_span_orders": 6,
        "coupling_strength": 0.3,
        "nonlinearity": 0.5,
    },
    tags=["scale", "laws", "physics", "resolution"],
    couplings=["emergence_beats_design", "thermodynamic_closure"],
    related_assumptions=[
        "em_plasma_frequency", "atmo_coriolis",
        "hydro_AMOC_collapse", "bio_permafrost_flux"
    ],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 12 — CALIBRATION AS CLOSED-LOOP CONTROL (Practitioner)
# ─────────────────────────────────────────────────────────────────────

CLAIM_CALIBRATION_LOOP = make_claim(
    name="Calibration As Closed-Loop Control",
    description=(
        "Calibration is not a one-time setting. It is a continuous closed-loop "
        "process: sense → compare → detect error → adjust → verify. This is "
        "thermodynamics applied to cognition."
    ),
    source="Practitioner Epistemology Field Notes (2026-08-12)",
    domain="cybernetics",
    statement=(
        "Calibration is a continuous feedback loop. Stress is error detection. "
        "Relaxation is environmental confirmation. The loop never stops."
    ),
    scope_valid=[ScopeLevel.MESO, ScopeLevel.CONTEXTUAL],
    ontology=OntologyType.PROCESS,
    geometry=GeometryType.RELATIONAL,
    green_range={
        "feedback_latency_seconds": 0.1,
        "sensor_coverage": 0.9,
        "actuator_resolution": 0.8,
    },
    yellow_range={
        "feedback_latency_seconds": (0.1, 1.0),
        "sensor_coverage": (0.5, 0.9),
        "actuator_resolution": (0.3, 0.8),
    },
    red_threshold={
        "feedback_latency_seconds": 1.0,
        "sensor_coverage": 0.5,
        "actuator_resolution": 0.3,
    },
    tags=["calibration", "feedback", "cybernetics", "control"],
    couplings=["body_as_instrument", "emergence_beats_design"],
    related_assumptions=["mag_rotation_coupling", "litho_LOD_change"],
)


# ─────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────
# SEED 13 — PLASMA FREQUENCY / CRITICAL DENSITY (Ionospheric Physics)
# ─────────────────────────────────────────────────────────────────────
# SCIENCE NOTE: The plasma frequency ω_p = sqrt(n_e e² / ε₀ m_e) sets the
# critical density for radio wave propagation. Below ω_p, EM waves are
# reflected (ionospheric skip); above it, they penetrate. This is a
# scale-dependent boundary (MICRO→MESO) that institutions routinely
# flatten into a binary "skip/no-skip" gauge, losing altitude structure.
# ----------------------------------------------------------------------

CLAIM_PLASMA_FREQUENCY = make_claim(
    name="Plasma Frequency / Critical Density",
    description=(
        "The ionospheric plasma frequency is a scale-dependent boundary condition "
        "for electromagnetic propagation. Treating it as a single scalar threshold "
        "flattens the 3D electron-density profile into a binary gauge, losing "
        "altitude-dependent structure and sporadic-E dynamics."
    ),
    source="ionospheric_physics + assumption_validator (earth-systems-physics repo)",
    domain="space_physics",
    statement=(
        "EM wave penetration at the plasma frequency boundary depends on the full "
        "3D electron density profile, not a single critical frequency scalar. "
        "Institutional HF propagation models that use a flat F2-layer critical "
        "frequency miss sporadic-E, D-layer absorption, and tilted ionospheric "
        "structures that dominate real-world link budgets."
    ),
    scope_valid=[ScopeLevel.MICRO, ScopeLevel.MESO],
    ontology=OntologyType.FIELD,
    geometry=GeometryType.FIELD,
    green_range={
        "electron_density_cm3": (1e5, 1e6),
        "altitude_resolution_km": 1.0,
        "frequency_MHz": (3, 30),
        "sporadic_E_included": True,
    },
    yellow_range={
        "electron_density_cm3": (1e4, 1e5),
        "altitude_resolution_km": (5, 10),
        "frequency_MHz": (1.5, 3),
    },
    red_threshold={
        "electron_density_cm3": 1e4,
        "altitude_resolution_km": 10,
        "frequency_MHz": 1.5,
    },
    mathematical_form=r"\omega_p = \sqrt{\frac{n_e e^2}{\varepsilon_0 m_e}}",
    tags=["plasma", "ionosphere", "critical_density", "EM_propagation", "scale_dependent"],
    couplings=["scale_dependence", "gauge_as_proxy"],
    related_assumptions=["iono_critical_freq", "em_plasma_frequency"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 14 — CORIOLIS EFFECT SCALE DEPENDENCE (Atmospheric Dynamics)
# ─────────────────────────────────────────────────────────────────────
# SCIENCE NOTE: The Coriolis parameter f = 2Ω sin(φ) is valid only when
# the Rossby number Ro = U/(fL) << 1. At mesoscale (L ~ 10–100 km) and
# microscale (L < 10 km), Coriolis is not the dominant term. Institutions
# that apply synoptic-scale (MACRO) Coriolis reasoning to local weather
# or drone navigation commit a Stage-2 scope-shift error.
# ----------------------------------------------------------------------

CLAIM_CORIOLIS_SCALE = make_claim(
    name="Coriolis Effect Scale Dependence",
    description=(
        "The Coriolis force is dominant only at synoptic scales where the Rossby "
        "number Ro << 1. At mesoscale and below, pressure-gradient and frictional "
        "terms dominate. Applying Coriolis reasoning to local-scale dynamics is a "
        "scope-shift error."
    ),
    source="atmospheric_dynamics + assumption_validator (earth-systems-physics repo)",
    domain="atmospheric_physics",
    statement=(
        "Coriolis-driven geostrophic balance holds only when Ro = U/(fL) < 0.1. "
        "At mesoscale (L ~ 10–100 km) and microscale (L < 10 km), pressure-gradient "
        "and frictional terms dominate. Synoptic-scale models applied to local weather "
        "or drone navigation degrade or break depending on latitude and velocity."
    ),
    scope_valid=[ScopeLevel.MACRO],
    ontology=OntologyType.FIELD,
    geometry=GeometryType.FIELD,
    green_range={
        "rossby_number": (0.0, 0.1),
        "length_scale_km": (500, 5000),
        "latitude_deg": (20, 90),
    },
    yellow_range={
        "rossby_number": (0.1, 1.0),
        "length_scale_km": (50, 500),
        "latitude_deg": (10, 20),
    },
    red_threshold={
        "rossby_number": 1.0,
        "length_scale_km": 50,
        "latitude_deg": 10,
    },
    mathematical_form=r"Ro = \frac{U}{fL}, \quad f = 2\Omega \sin\varphi",
    tags=["coriolis", "rossby_number", "scale_dependence", "atmospheric_dynamics"],
    couplings=["scale_dependence", "gauge_as_proxy"],
    related_assumptions=["atmo_coriolis", "atmo_geostrophic_balance"],
)


# ─────────────────────────────────────────────────────────────────────
# SEED 15 — LENGTH-OF-DAY (LOD) CHANGE / EARTH ROTATION COUPLING
# (Geodesy / Climate Coupling)
# ─────────────────────────────────────────────────────────────────────
# SCIENCE NOTE: LOD changes (~2 ms/decade) are driven by core-mantle angular
# momentum exchange, atmospheric angular momentum (AAM), and post-glacial
# rebound. Climate models that do not close the angular-momentum budget
# between atmosphere and solid Earth externalize a rotational energy debt.
# This is a T1 thermodynamic leak at the MACRO scale.
# ----------------------------------------------------------------------

CLAIM_LOD_CHANGE = make_claim(
    name="Length-of-Day Change / Earth Rotation Coupling",
    description=(
        "Changes in Earth's rotation rate (LOD) are driven by coupled angular-momentum "
        "exchange between core, mantle, atmosphere, and oceans. Climate models that do not "
        "close this angular-momentum budget externalize a rotational energy debt. "
        "Institutional weather forecasts treat LOD as a constant, missing the feedback "
        "from atmospheric mass redistribution to solid-Earth rotation."
    ),
    source="geodesy + IERS + assumption_validator (earth-systems-physics repo)",
    domain="geodesy",
    statement=(
        "Earth's length-of-day (LOD) varies by ~2 ms/decade due to core-mantle coupling, "
        "atmospheric angular momentum (AAM), and glacial isostatic adjustment. Climate "
        "and weather models that assume a constant rotation rate externalize a rotational "
        "energy/entropy debt. At macro scale, this leak compounds into secular drift in "
        "satellite ephemeris and GNSS timing."
    ),
    scope_valid=[ScopeLevel.MACRO],
    ontology=OntologyType.PROCESS,
    geometry=GeometryType.FIELD,
    green_range={
        "lod_variation_ms": (0, 2.5),
        "aam_closure_fraction": 0.95,
        "ephemeris_drift_m": (0, 0.1),
    },
    yellow_range={
        "lod_variation_ms": (2.5, 5.0),
        "aam_closure_fraction": (0.80, 0.95),
        "ephemeris_drift_m": (0.1, 1.0),
    },
    red_threshold={
        "lod_variation_ms": 5.0,
        "aam_closure_fraction": 0.80,
        "ephemeris_drift_m": 1.0,
    },
    mathematical_form=r"\Delta LOD = \frac{\Delta AAM}{C_m \Omega} + \frac{\Delta H_{core}}{C_m \Omega}",
    tags=["LOD", "earth_rotation", "angular_momentum", "geodesy", "climate_coupling"],
    couplings=["thermodynamic_closure", "scale_dependence"],
    related_assumptions=["litho_LOD_change", "atmo_AAM_budget"],
)

# MASTER REGISTRY
# ─────────────────────────────────────────────────────────────────────

CLAIM_REGISTRY: Dict[str, Claim] = {
    "emergence_beats_design": CLAIM_EMERGENCE_BEATS_DESIGN,
    "body_as_instrument": CLAIM_BODY_AS_INSTRUMENT,
    "thermodynamic_closure": CLAIM_THERMODYNAMIC_CLOSURE,
    "amoc_collapse": CLAIM_AMOC_COLLAPSE,
    "permafrost_carbon": CLAIM_PERMAFROST_CARBON,
    "gauge_as_proxy": CLAIM_GAUGE_AS_PROXY,
    "economic_decoupling": CLAIM_ECONOMIC_DECOUPLING,
    "institutional_gatekeeping": CLAIM_INSTITUTIONAL_GATEKEEPING,
    "dyslexia_geometry": CLAIM_DYSLEXIA_GEOMETRY,
    "consciousness_as_process": CLAIM_CONSCIOUSNESS_AS_PROCESS,
    "scale_dependence": CLAIM_SCALE_DEPENDENCE,
    "calibration_loop": CLAIM_CALIBRATION_LOOP,
    "plasma_frequency": CLAIM_PLASMA_FREQUENCY,
    "coriolis_scale": CLAIM_CORIOLIS_SCALE,
    "lod_change": CLAIM_LOD_CHANGE,
}


# ─────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def get_claim(claim_id: str) -> Optional[Claim]:
    """Retrieve a claim by ID."""
    return CLAIM_REGISTRY.get(claim_id)


def list_claims(domain: Optional[str] = None) -> List[str]:
    """List all claim IDs, optionally filtered by domain."""
    if domain is None:
        return list(CLAIM_REGISTRY.keys())
    return [
        cid for cid, claim in CLAIM_REGISTRY.items()
        if claim.domain == domain
    ]


def find_claims_by_tag(tag: str) -> List[Claim]:
    """Find all claims with a given tag."""
    return [
        claim for claim in CLAIM_REGISTRY.values()
        if tag in claim.tags
    ]


def find_coupled_claims(claim_id: str) -> List[Claim]:
    """Find all claims coupled to the given claim."""
    claim = CLAIM_REGISTRY.get(claim_id)
    if not claim:
        return []
    return [
        CLAIM_REGISTRY[cid] for cid in claim.couplings
        if cid in CLAIM_REGISTRY
    ]


def render_claim(claim_id: str) -> str:
    """Human-readable summary of a claim."""
    claim = CLAIM_REGISTRY.get(claim_id)
    if not claim:
        return f"Unknown claim: {claim_id}"

    current = claim.current()
    lines = [
        f"=== {claim.name} ===",
        f"ID: {claim.id}",
        f"Source: {claim.source}",
        f"Domain: {claim.domain}",
        f"Statement: {current.statement}",
        f"Scope: {', '.join([s.value for s in current.scope_valid])}",
        f"Ontology: {current.ontology_assumed.value}",
        f"Geometry: {current.geometry_assumed.value}",
        f"Green range: {current.green_range}",
        f"Yellow range: {current.yellow_range}",
        f"Red threshold: {current.red_threshold}",
        f"Tags: {', '.join(claim.tags)}",
        f"Couplings: {', '.join(claim.couplings)}",
    ]
    if current.modified_from:
        lines.append(f"Modified from: {current.modified_from}")
        lines.append(f"Modification note: {current.modification_note}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CLAIM REGISTRY — EARTH SYSTEMS PHYSICS")
    print("=" * 60)
    print(f"\n{len(CLAIM_REGISTRY)} claims loaded.\n")

    for cid in CLAIM_REGISTRY:
        print(f"  - {cid}")

    print("\n" + "=" * 60)
    print("SAMPLE CLAIM: emergence_beats_design")
    print("=" * 60)
    print(render_claim("emergence_beats_design"))

    print("\n" + "=" * 60)
    print("COUPLINGS FROM emergence_beats_design:")
    print("=" * 60)
    for coupled in find_coupled_claims("emergence_beats_design"):
        print(f"  - {coupled.name} ({coupled.id})")
