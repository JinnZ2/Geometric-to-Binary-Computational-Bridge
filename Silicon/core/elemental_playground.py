# elemental_playground.py
"""
The Elemental Playground: A Computational Phase Explorer

A framework for AI-guided exploration of the compositional manifold.
Generalizes the silicon manifold framework to the entire periodic table.

Architecture:
- ElementDatabase: physical properties for each element
- SFiberBundle: the S-manifold + fiber bundle for any composition
- PhaseExplorer: AI-driven discovery of computational phases
- TrajectoryDesigner: optimal path planning through compositional space
- HeterostructureBuilder: interface and heterostructure design
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Callable, Union, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import json
import warnings


# ═══════════════════════════════════════════════════════════════════════════
# 1. ELEMENT DATABASE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ElementProperties:
    """Physical properties that define an element's S-manifold character."""
    
    # Identity
    symbol: str
    atomic_number: int
    name: str
    
    # Electronic structure
    electron_configuration: str       # e.g., "[Ne] 3s² 3p²"
    valence_electrons: int
    bandgap_eV: float                 # 0 for metals
    bandgap_type: str                 # "direct", "indirect", "metallic", "insulating"
    
    # Crystal structure (preferred)
    crystal_structure: str            # "diamond", "fcc", "bcc", "hcp", "perovskite", etc.
    lattice_constant_ang: float
    coordination_number: int
    
    # Defect chemistry
    vacancy_formation_energy_eV: float
    interstitial_formation_energy_eV: float
    common_dopants: List[str]
    
    # Coupling modes (native strengths, 0-1)
    native_electrical_coupling: float  # conductivity character
    native_optical_coupling: float     # direct bandgap → photonic
    native_thermal_coupling: float     # phonon character
    native_magnetic_coupling: float    # magnetic moment
    
    # Regime affinities (pre-computed from properties)
    natural_regime: str = ""          # "semiconductor", "metallic", "quantum", etc.
    
    # Special properties
    is_superconductor: bool = False
    critical_temperature_K: float = 0.0
    has_heavy_fermions: bool = False
    is_topological_insulator: bool = False
    
    def __post_init__(self):
        if not self.natural_regime:
            self.natural_regime = self._classify_natural_regime()
    
    def _classify_natural_regime(self) -> str:
        """Classify the element's natural computational regime."""
        if self.bandgap_eV < 0.01:
            return "metallic"
        elif self.bandgap_eV < 1.5:
            return "semiconductor"
        elif self.bandgap_eV < 5.0:
            return "photonic"  # wide bandgap → transparent, photonic
        else:
            return "photonic"  # insulator
        
        # Magnetic elements
        if self.native_magnetic_coupling > 0.5:
            return "quantum" if "rare_earth" in self.electron_configuration else "metallic"


# ── Element Database ──

class ElementDatabase:
    """
    Database of elemental properties that feeds the S-manifold builder.
    
    Extensible: new elements can be added, properties refined from DFT,
    and AI can propose corrections based on experimental data.
    """
    
    def __init__(self):
        self._elements: Dict[str, ElementProperties] = {}
        self._initialize_core_elements()
    
    def _initialize_core_elements(self):
        """Initialize the most computationally significant elements."""
        
        core_elements = [
            ElementProperties(
                symbol="Si", atomic_number=14, name="Silicon",
                electron_configuration="[Ne] 3s² 3p²",
                valence_electrons=4,
                bandgap_eV=1.12, bandgap_type="indirect",
                crystal_structure="diamond", lattice_constant_ang=5.431,
                coordination_number=4,
                vacancy_formation_energy_eV=3.6,
                interstitial_formation_energy_eV=4.5,
                common_dopants=["P", "B", "As", "Sb"],
                native_electrical_coupling=0.7,
                native_optical_coupling=0.1,
                native_thermal_coupling=0.15,
                native_magnetic_coupling=0.0,
            ),
            ElementProperties(
                symbol="Ge", atomic_number=32, name="Germanium",
                electron_configuration="[Ar] 3d¹⁰ 4s² 4p²",
                valence_electrons=4,
                bandgap_eV=0.67, bandgap_type="indirect",
                crystal_structure="diamond", lattice_constant_ang=5.658,
                coordination_number=4,
                vacancy_formation_energy_eV=2.0,
                interstitial_formation_energy_eV=3.0,
                common_dopants=["P", "B", "As"],
                native_electrical_coupling=0.8,
                native_optical_coupling=0.05,
                native_thermal_coupling=0.1,
                native_magnetic_coupling=0.0,
            ),
            ElementProperties(
                symbol="C", atomic_number=6, name="Carbon",
                electron_configuration="[He] 2s² 2p²",
                valence_electrons=4,
                bandgap_eV=5.47, bandgap_type="indirect",  # diamond
                crystal_structure="diamond", lattice_constant_ang=3.567,
                coordination_number=4,
                vacancy_formation_energy_eV=7.0,
                interstitial_formation_energy_eV=10.0,
                common_dopants=["N", "B", "P"],
                native_electrical_coupling=0.0,  # insulating diamond
                native_optical_coupling=0.9,     # NV centers, diamond photonics
                native_thermal_coupling=0.05,
                native_magnetic_coupling=0.3,    # NV centers
            ),
            ElementProperties(
                symbol="GaAs", atomic_number=0, name="Gallium Arsenide",
                electron_configuration="[Ar] 3d¹⁰ 4s² 4p¹ + [Ar] 3d¹⁰ 4s² 4p³",
                valence_electrons=8,  # 3+5
                bandgap_eV=1.43, bandgap_type="direct",
                crystal_structure="zincblende", lattice_constant_ang=5.653,
                coordination_number=4,
                vacancy_formation_energy_eV=2.5,
                interstitial_formation_energy_eV=3.5,
                common_dopants=["Si", "Be", "Cr"],
                native_electrical_coupling=0.6,
                native_optical_coupling=0.8,      # direct bandgap
                native_thermal_coupling=0.05,
                native_magnetic_coupling=0.0,
            ),
            ElementProperties(
                symbol="Er", atomic_number=68, name="Erbium",
                electron_configuration="[Xe] 4f¹² 6s²",
                valence_electrons=3,
                bandgap_eV=0.0, bandgap_type="metallic",
                crystal_structure="hcp", lattice_constant_ang=3.56,
                coordination_number=12,
                vacancy_formation_energy_eV=1.5,
                interstitial_formation_energy_eV=2.0,
                common_dopants=[],
                native_electrical_coupling=0.3,
                native_optical_coupling=0.9,       # 1.54 μm telecom emission
                native_thermal_coupling=0.05,
                native_magnetic_coupling=0.8,      # large magnetic moment
            ),
            ElementProperties(
                symbol="NbN", atomic_number=0, name="Niobium Nitride",
                electron_configuration="[Kr] 4d⁴ 5s¹ + [He] 2s² 2p³",
                valence_electrons=5+3,
                bandgap_eV=0.0, bandgap_type="metallic",
                crystal_structure="rock_salt", lattice_constant_ang=4.39,
                coordination_number=6,
                vacancy_formation_energy_eV=1.0,
                interstitial_formation_energy_eV=1.5,
                common_dopants=[],
                native_electrical_coupling=0.9,
                native_optical_coupling=0.1,
                native_thermal_coupling=0.0,
                native_magnetic_coupling=0.2,
                is_superconductor=True,
                critical_temperature_K=16.0,
            ),
            ElementProperties(
                symbol="O", atomic_number=8, name="Oxygen",
                electron_configuration="[He] 2s² 2p⁴",
                valence_electrons=6,
                bandgap_eV=9.0, bandgap_type="insulating",
                crystal_structure="molecular", lattice_constant_ang=0.0,
                coordination_number=2,
                vacancy_formation_energy_eV=0.0,    # not meaningful for molecular
                interstitial_formation_energy_eV=0.0,
                common_dopants=[],
                native_electrical_coupling=0.0,
                native_optical_coupling=0.0,
                native_thermal_coupling=0.0,
                native_magnetic_coupling=0.0,       # triplet ground state
            ),
            ElementProperties(
                symbol="YBaCuO", atomic_number=0, name="YBCO Superconductor",
                electron_configuration="complex",
                valence_electrons=0,
                bandgap_eV=0.0, bandgap_type="metallic",
                crystal_structure="perovskite", lattice_constant_ang=3.82,
                coordination_number=6,
                vacancy_formation_energy_eV=0.5,
                interstitial_formation_energy_eV=0.5,
                common_dopants=["O_vacancy"],
                native_electrical_coupling=0.9,
                native_optical_coupling=0.1,
                native_thermal_coupling=0.0,
                native_magnetic_coupling=0.6,
                is_superconductor=True,
                critical_temperature_K=92.0,
            ),
        ]
        
        for elem in core_elements:
            self._elements[elem.symbol] = elem
    
    def get(self, symbol: str) -> Optional[ElementProperties]:
        return self._elements.get(symbol)
    
    def list_elements(self) -> List[str]:
        return sorted(self._elements.keys())
    
    def add_element(self, element: ElementProperties):
        """Extend the database with a new element or compound."""
        self._elements[element.symbol] = element
    
    def suggest_related(self, symbol: str) -> List[str]:
        """Suggest elements with similar S-manifold character."""
        elem = self.get(symbol)
        if not elem:
            return []
        
        similar = []
        for other_sym, other in self._elements.items():
            if other_sym == symbol:
                continue
            
            # Similarity score
            score = 0
            if other.bandgap_type == elem.bandgap_type:
                score += 1
            if abs(other.bandgap_eV - elem.bandgap_eV) < 0.5:
                score += 1
            if other.crystal_structure == elem.crystal_structure:
                score += 1
            if other.natural_regime == elem.natural_regime:
                score += 2
            
            if score >= 2:
                similar.append((other_sym, score))
        
        similar.sort(key=lambda x: -x[1])
        return [s[0] for s in similar[:5]]


# ═══════════════════════════════════════════════════════════════════════════
# 2. GENERIC S-MANIFOLD BUILDER
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GenericSFiberBundle:
    """
    The S-manifold + octahedral fiber bundle for ANY element or compound.
    
    This is the universal construction that generalizes the silicon
    framework. Given an element's properties, it builds:
    - The S-manifold coordinates (n, d, ℓ, κ)
    - The octahedral fiber (8 states, Z₂³ torsor)
    - The free energy landscape F(S)
    - The Riemannian metric g_ij
    - The computational phase boundaries
    - The holonomy group
    """
    
    element: ElementProperties
    temperature: float = 300.0
    
    # Derived properties
    _built: bool = False
    
    def build_manifold(self):
        """Construct the S-manifold from elemental properties."""
        
        # ── Native regime basins based on element type ──
        self._regime_basins = self._compute_regime_basins()
        
        # ── Free energy landscape F(S) ──
        self._free_energy_function = self._build_free_energy()
        
        # ── Metric tensor ──
        self._metric_function = self._build_metric()
        
        # ── Octahedral fiber compatibility ──
        self._fiber_compatibility = self._compute_fiber_compatibility()
        
        # ── Holonomy prediction ──
        self._predicted_holonomy = self._predict_holonomy()
        
        self._built = True
    
    def _compute_regime_basins(self) -> Dict:
        """
        Determine which computational regimes are naturally accessible
        for this element.
        """
        regimes = {
            "semiconductor": 0,
            "metallic": 0,
            "quantum": 0,
            "photonic": 0,
            "defect_dominated": 0,
            "superconducting": 0,
        }
        
        e = self.element
        
        # Semiconductor basin
        if 0.1 < e.bandgap_eV < 3.0:
            regimes["semiconductor"] = 0.8
        elif e.bandgap_eV < 0.1:
            regimes["semiconductor"] = 0.1  # metallic, but can be gated
        
        # Metallic basin
        if e.bandgap_eV < 0.1:
            regimes["metallic"] = 0.9
        elif e.bandgap_eV < 1.0:
            regimes["metallic"] = 0.3  # approachable via heavy doping
        
        # Quantum basin
        if e.native_magnetic_coupling > 0.5:
            regimes["quantum"] = 0.7
        if e.bandgap_type == "direct" and e.bandgap_eV > 0.5:
            regimes["quantum"] = 0.5  # quantum dots possible
        if e.has_heavy_fermions:
            regimes["quantum"] = 0.9
        
        # Photonic basin
        if e.bandgap_type == "direct":
            regimes["photonic"] = 0.8
        if e.native_optical_coupling > 0.5:
            regimes["photonic"] = max(regimes["photonic"], 0.6)
        
        # Defect-dominated basin
        if e.vacancy_formation_energy_eV < 2.0:
            regimes["defect_dominated"] = 0.6
        elif e.vacancy_formation_energy_eV < 4.0:
            regimes["defect_dominated"] = 0.3
        
        # Superconducting basin
        if e.is_superconductor:
            regimes["superconducting"] = 0.9
            if e.critical_temperature_K > 77:
                regimes["superconducting"] = 1.0
        
        # Normalize so dominant is ~1.0
        max_val = max(regimes.values()) if max(regimes.values()) > 0 else 1.0
        
        return {k: v / max_val for k, v in regimes.items()}
    
    def _build_free_energy(self):
        """
        Build the free energy function F(S) for this element.
        
        The free energy landscape combines:
        - Element's native band structure
        - Defect chemistry
        - Confinement energy
        - Magnetic/coupling contributions
        """
        e = self.element
        
        def F(S: np.ndarray, T: float = 300.0) -> float:
            n, d, ell, k_eff = S
            
            # Band energy
            if e.bandgap_eV > 0:
                # Semiconductor: energy decreases with carrier population
                E_band = e.bandgap_eV * (1 - 0.1 * np.log10(max(n, 1e8) / 1e16))
            else:
                # Metal: energy increases with carrier scattering
                E_band = 0.1 * np.log10(max(n, 1e8) / 1e22)**2
            
            # Defect energy
            E_defect = e.vacancy_formation_energy_eV * d
            
            # Confinement energy
            if ell > 0.1:
                E_conf = 0.05 * (3.0 - ell)**2 / ell
            else:
                E_conf = 10.0
            
            # Coupling energy
            E_coupling = -0.1 * k_eff
            
            # Magnetic energy
            E_mag = -e.native_magnetic_coupling * k_eff * 0.05
            
            # Superconducting condensation energy
            if e.is_superconductor and T < e.critical_temperature_K:
                E_sc = -0.01 * (1 - T / e.critical_temperature_K)**2
            else:
                E_sc = 0.0
            
            E_internal = E_band + E_defect + E_conf + E_coupling + E_mag + E_sc
            
            # Entropy
            S_entropy = 0
            if 0 < d < 1:
                S_entropy += -8.617e-5 * (d * np.log(d + 1e-30) + (1-d) * np.log(1-d + 1e-30))
            
            return E_internal - T * S_entropy
        
        return F
    
    def _build_metric(self):
        """Build the Riemannian metric from the free energy."""
        def compute_g(S: np.ndarray, T: float = 300.0, h: float = 1e-4) -> np.ndarray:
            F = self._free_energy_function
            dim = len(S)
            g = np.zeros((dim, dim))
            
            F0 = F(S, T)
            scales = np.maximum(np.array([S[0]*h, h, h, h]), 1e-12)
            
            for i in range(dim):
                S_fwd = S.copy(); S_fwd[i] += scales[i]
                S_bwd = S.copy(); S_bwd[i] -= scales[i]
                g[i, i] = (F(S_fwd, T) - 2*F0 + F(S_bwd, T)) / (scales[i]**2)
            
            for i in range(dim):
                for j in range(i+1, dim):
                    S_pp = S.copy(); S_pp[i] += scales[i]; S_pp[j] += scales[j]
                    S_pm = S.copy(); S_pm[i] += scales[i]; S_pm[j] -= scales[j]
                    S_mp = S.copy(); S_mp[i] -= scales[i]; S_mp[j] += scales[j]
                    S_mm = S.copy(); S_mm[i] -= scales[i]; S_mm[j] -= scales[j]
                    g[i, j] = (F(S_pp, T) - F(S_pm, T) - F(S_mp, T) + F(S_mm, T)) / (4*scales[i]*scales[j])
                    g[j, i] = g[i, j]
            
            return g
        
        return compute_g
    
    def _compute_fiber_compatibility(self) -> Dict[int, Dict[str, float]]:
        """
        How compatible is each octahedral state with this element's native regime?
        """
        from inverse_regime_design import compute_structural_metrics, CANONICAL_EIGENVALUES
        
        compatibility = {}
        
        for state_idx in range(8):
            metrics = compute_structural_metrics(state_idx)
            
            # Match octahedral state affinities to elemental regime basins
            scores = {}
            for regime, basin_strength in self._regime_basins.items():
                if regime == "quantum":
                    affinity = metrics.quantum_affinity
                elif regime in ("semiconductor", "metallic"):
                    affinity = metrics.classical_affinity
                elif regime == "photonic":
                    affinity = metrics.photonic_affinity
                elif regime == "defect_dominated":
                    affinity = 1 - metrics.degeneracy_score
                elif regime == "superconducting":
                    affinity = metrics.memory_affinity  # isotropic favored
                else:
                    affinity = 0.5
                
                scores[regime] = affinity * basin_strength
            
            # Best regime match
            best_regime = max(scores, key=scores.get)
            
            compatibility[state_idx] = {
                "scores": scores,
                "best_regime": best_regime,
                "overall_compatibility": max(scores.values()),
            }
        
        return compatibility
    
    def _predict_holonomy(self) -> Dict:
        """
        Predict whether the fiber bundle has nontrivial holonomy
        for this element.
        
        Holonomy is expected when:
        1. The element has multiple accessible regimes (phase boundaries exist)
        2. The regimes have different symmetry character
        3. The octahedral states have different regime affinities
        """
        
        n_accessible_regimes = sum(
            1 for v in self._regime_basins.values() if v > 0.3
        )
        
        # Check if fiber states prefer different regimes
        preferred_regimes = set()
        for state_idx, compat in self._fiber_compatibility.items():
            if compat["overall_compatibility"] > 0.5:
                preferred_regimes.add(compat["best_regime"])
        
        regime_diversity = len(preferred_regimes)
        
        # Predict holonomy
        if n_accessible_regimes >= 2 and regime_diversity >= 2:
            holonomy_expected = True
            holonomy_type = "Z₂" if regime_diversity == 2 else "Z₂×Z₂" if regime_diversity == 3 else "Z₂³"
        else:
            holonomy_expected = False
            holonomy_type = "trivial"
        
        return {
            "holonomy_expected": holonomy_expected,
            "holonomy_type": holonomy_type,
            "n_accessible_regimes": n_accessible_regimes,
            "regime_diversity": regime_diversity,
            "preferred_regimes": preferred_regimes,
        }
    
    def classify_state(self, n: float, d: float, ell: float, k_coherent: float) -> str:
        """Classify which computational regime a point belongs to."""
        S = np.array([np.log10(n), d, ell, k_coherent])
        F = self._free_energy_function(S, self.temperature)
        
        # Determine dominant regime based on basin proximity
        # Simplified: use the free energy gradient
        scores = self._regime_basins.copy()
        
        # Adjust by position in S-space
        if ell < 1.0:
            scores["quantum"] += 0.3
        if d > 0.3:
            scores["defect_dominated"] += 0.4
        if n > 1e19:
            scores["metallic"] += 0.3
        
        return max(scores, key=scores.get)
    
    def get_summary(self) -> str:
        if not self._built:
            self.build_manifold()
        
        e = self.element
        lines = [
            f"╔══════════════════════════════════════════╗",
            f"║  {e.symbol:6s} — {e.name:30s} ║",
            f"╠══════════════════════════════════════════╣",
            f"║  Z={e.atomic_number}, {e.crystal_structure}, a={e.lattice_constant_ang} Å",
            f"║  Bandgap: {e.bandgap_eV:.2f} eV ({e.bandgap_type})",
            f"║  Vacancy E_f: {e.vacancy_formation_energy_eV:.1f} eV",
            f"╠══════════════════════════════════════════╣",
            f"║  NATIVE BASINS:",
        ]
        
        for regime, strength in sorted(self._regime_basins.items(), key=lambda x: -x[1]):
            if strength > 0.1:
                bar = "█" * int(strength * 10) + "░" * (10 - int(strength * 10))
                lines.append(f"║    {regime:20s} [{bar}] {strength:.2f}")
        
        h = self._predicted_holonomy
        lines.append(f"╠══════════════════════════════════════════╣")
        lines.append(f"║  Holonomy: {h['holonomy_type']} "
                    f"({'expected' if h['holonomy_expected'] else 'unlikely'})")
        lines.append(f"║  Accessible regimes: {h['n_accessible_regimes']}")
        lines.append(f"╚══════════════════════════════════════════╝")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# 3. COMPOSITIONAL SPACE NAVIGATOR
# ═══════════════════════════════════════════════════════════════════════════

class CompositionalNavigator:
    """
    Navigate the full compositional manifold.
    
    Given two elements (or compounds), this computes:
    - The combined S-manifold
    - Interface properties
    - Inter-element FRET coupling
    - Optimal paths between basins
    """
    
    def __init__(self, database: ElementDatabase):
        self.database = database
        self._manifold_cache = {}
    
    def get_manifold(self, symbol: str) -> GenericSFiberBundle:
        """Get or build the S-manifold for an element."""
        if symbol not in self._manifold_cache:
            elem = self.database.get(symbol)
            if elem is None:
                raise ValueError(f"Unknown element: {symbol}")
            manifold = GenericSFiberBundle(element=elem)
            manifold.build_manifold()
            self._manifold_cache[symbol] = manifold
        return self._manifold_cache[symbol]
    
    def compare_elements(
        self, symbol_a: str, symbol_b: str
    ) -> Dict:
        """
        Compare the S-manifolds of two elements.
        
        Returns overlap metrics, interface predictions,
        and FRET coupling possibilities.
        """
        m_a = self.get_manifold(symbol_a)
        m_b = self.get_manifold(symbol_b)
        
        e_a = m_a.element
        e_b = m_b.element
        
        # Regime overlap
        overlap = {}
        for regime in m_a._regime_basins:
            a_val = m_a._regime_basins.get(regime, 0)
            b_val = m_b._regime_basins.get(regime, 0)
            overlap[regime] = min(a_val, b_val)
        
        # Interface properties
        lattice_mismatch = abs(e_a.lattice_constant_ang - e_b.lattice_constant_ang) / max(e_a.lattice_constant_ang, e_b.lattice_constant_ang, 1e-10)
        
        interface_quality = "excellent" if lattice_mismatch < 0.01 else \
                           "good" if lattice_mismatch < 0.05 else \
                           "strained" if lattice_mismatch < 0.1 else \
                           "defective" if lattice_mismatch < 0.2 else \
                           "incoherent"
        
        # FRET compatibility
        fret_possible = (
            e_a.native_optical_coupling > 0.3 and
            e_b.native_optical_coupling > 0.3
        ) or (
            e_a.native_magnetic_coupling > 0.3 and
            e_b.native_magnetic_coupling > 0.3
        )
        
        # Shared basins
        shared_regimes = [r for r, v in overlap.items() if v > 0.3]
        
        return {
            "element_a": symbol_a,
            "element_b": symbol_b,
            "lattice_mismatch": lattice_mismatch,
            "interface_quality": interface_quality,
            "shared_regimes": shared_regimes,
            "regime_overlap": overlap,
            "fret_coupling_possible": fret_possible,
            "suggested_heterostructure": len(shared_regimes) >= 1,
        }
    
    def explore_composition(
        self,
        base_symbol: str,
        dopant_symbol: str,
        concentration: float = 0.01,
    ) -> Dict:
        """
        Explore how doping one element into another modifies the S-manifold.
        
        Returns the shifted basin structure, new accessible regimes,
        and any emergent computational phases.
        """
        m_base = self.get_manifold(base_symbol)
        m_dopant = self.get_manifold(dopant_symbol)
        
        # Dopant shifts the manifold
        e_base = m_base.element
        e_dopant = m_dopant.element
        
        # Bandgap bowing (empirical: Vegard's law with bowing)
        bg_bowing = 0.5  # typical for semiconductors
        effective_bandgap = (
            e_base.bandgap_eV * (1 - concentration) +
            e_dopant.bandgap_eV * concentration -
            bg_bowing * concentration * (1 - concentration) * abs(e_base.bandgap_eV - e_dopant.bandgap_eV)
        )
        
        # Defect introduction
        effective_defect_formation = min(
            e_base.vacancy_formation_energy_eV,
            e_dopant.vacancy_formation_energy_eV + 0.5  # dopant introduces strain
        )
        
        # New magnetic character
        effective_magnetic = (
            e_base.native_magnetic_coupling * (1 - concentration) +
            e_dopant.native_magnetic_coupling * concentration
        )
        
        # Shifted regime basins
        shifted_basins = m_base._regime_basins.copy()
        
        if effective_bandgap < 0.1:
            shifted_basins["metallic"] = min(1.0, shifted_basins.get("metallic", 0) + 0.3)
        if effective_magnetic > 0.3:
            shifted_basins["quantum"] = min(1.0, shifted_basins.get("quantum", 0) + 0.4)
        if effective_defect_formation < 2.0:
            shifted_basins["defect_dominated"] = min(1.0, shifted_basins.get("defect_dominated", 0) + 0.3)
        
        # Emergent phases
        emergent = []
        for regime, strength in shifted_basins.items():
            original = m_base._regime_basins.get(regime, 0)
            if strength > 0.5 and original < 0.2:
                emergent.append(regime)
        
        return {
            "composition": f"{base_symbol}_{1-concentration:.3f}{dopant_symbol}_{concentration:.3f}",
            "effective_bandgap_eV": effective_bandgap,
            "effective_defect_eV": effective_defect_formation,
            "effective_magnetic": effective_magnetic,
            "shifted_basins": shifted_basins,
            "emergent_regimes": emergent,
            "original_dominant": max(m_base._regime_basins, key=m_base._regime_basins.get),
            "doped_dominant": max(shifted_basins, key=shifted_basins.get),
        }


# ═══════════════════════════════════════════════════════════════════════════
# 4. AI EXPLORATION AGENT
# ═══════════════════════════════════════════════════════════════════════════

class PhaseExplorerAgent:
    """
    An AI agent that explores the compositional manifold.
    
    Given a target computational phase, it:
    1. Searches for elements/compounds that can access it
    2. Proposes doping strategies to shift basins
    3. Designs interfaces to create hybrid regimes
    4. Predicts emergent computational phases
    """
    
    def __init__(self, database: ElementDatabase):
        self.database = database
        self.navigator = CompositionalNavigator(database)
        self._exploration_log = []
    
    def find_elements_for_regime(
        self,
        target_regime: str,
        min_strength: float = 0.5,
    ) -> List[Tuple[str, float]]:
        """
        Find all elements that naturally access a target computational regime.
        """
        results = []
        
        for symbol in self.database.list_elements():
            manifold = self.navigator.get_manifold(symbol)
            strength = manifold._regime_basins.get(target_regime, 0)
            
            if strength >= min_strength:
                results.append((symbol, strength))
        
        results.sort(key=lambda x: -x[1])
        return results
    
    def propose_doping_for_regime(
        self,
        base_symbol: str,
        target_regime: str,
    ) -> List[Dict]:
        """
        Propose doping strategies to access a target regime
        from a base element that doesn't naturally access it.
        """
        proposals = []
        
        for dopant_symbol in self.database.list_elements():
            if dopant_symbol == base_symbol:
                continue
            
            # Test at various concentrations
            for concentration in [0.001, 0.01, 0.05, 0.1]:
                result = self.navigator.explore_composition(
                    base_symbol, dopant_symbol, concentration
                )
                
                strength = result["shifted_basins"].get(target_regime, 0)
                
                if strength > 0.3:
                    proposals.append({
                        "dopant": dopant_symbol,
                        "concentration": concentration,
                        "resulting_strength": strength,
                        "emergent": target_regime in result["emergent_regimes"],
                        "full_result": result,
                    })
        
        proposals.sort(key=lambda x: -x["resulting_strength"])
        return proposals[:10]
    
    def discover_emergent_phases(
        self,
        symbol_a: str,
        symbol_b: str,
    ) -> Dict:
        """
        Explore the interface between two elements for emergent
        computational phases that neither possesses alone.
        """
        comparison = self.navigator.compare_elements(symbol_a, symbol_b)
        
        m_a = self.navigator.get_manifold(symbol_a)
        m_b = self.navigator.get_manifold(symbol_b)
        
        # Emergent phases: regimes strong in one but absent in the other
        emergent_from_a = [
            r for r, v in m_a._regime_basins.items()
            if v > 0.5 and m_b._regime_basins.get(r, 0) < 0.2
        ]
        emergent_from_b = [
            r for r, v in m_b._regime_basins.items()
            if v > 0.5 and m_a._regime_basins.get(r, 0) < 0.2
        ]
        
        # Interface-specific emergent phases
        interface_regimes = []
        if comparison["lattice_mismatch"] > 0.1:
            interface_regimes.append("defect_dominated")
        if comparison["fret_coupling_possible"]:
            interface_regimes.append("photonic")
        if (m_a.element.native_magnetic_coupling > 0.3 or 
            m_b.element.native_magnetic_coupling > 0.3):
            interface_regimes.append("quantum")
        
        return {
            "pair": (symbol_a, symbol_b),
            "shared_regimes": comparison["shared_regimes"],
            "emergent_from_a_at_interface": emergent_from_a,
            "emergent_from_b_at_interface": emergent_from_b,
            "interface_specific_regimes": interface_regimes,
            "heterostructure_quality": comparison["interface_quality"],
            "suggestion": (
                f"Interface between {symbol_a} and {symbol_b}: "
                f"{comparison['interface_quality']} match. "
                f"Shared regimes: {comparison['shared_regimes']}. "
                f"Interface may host: {interface_regimes}."
            ),
        }
    
    def map_entire_compositional_region(
        self,
        base_elements: List[str],
        n_dopants: int = 3,
    ) -> Dict:
        """
        Map an entire region of the compositional manifold.
        
        For a set of base elements, explores all pairwise combinations
        and dopant possibilities, building a graph of accessible
        computational phases.
        """
        import itertools
        
        graph = {
            "nodes": {},  # element → regimes
            "edges": [],  # (a, b) → shared regimes, interface properties
        }
        
        # Nodes
        for symbol in base_elements:
            m = self.navigator.get_manifold(symbol)
            graph["nodes"][symbol] = {
                "regimes": {r: v for r, v in m._regime_basins.items() if v > 0.2},
                "dominant": max(m._regime_basins, key=m._regime_basins.get),
                "holonomy": m._predicted_holonomy["holonomy_type"],
            }
        
        # Edges
        for a, b in itertools.combinations(base_elements, 2):
            comparison = self.navigator.compare_elements(a, b)
            if comparison["shared_regimes"] or comparison["fret_coupling_possible"]:
                graph["edges"].append({
                    "nodes": (a, b),
                    "shared_regimes": comparison["shared_regimes"],
                    "interface_quality": comparison["interface_quality"],
                    "fret_possible": comparison["fret_coupling_possible"],
                })
        
        return graph
    
    def generate_exploration_report(self) -> str:
        """Generate a human/AI-readable exploration report."""
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║     COMPOSITIONAL MANIFOLD EXPLORATION REPORT           ║",
            "╠══════════════════════════════════════════════════════════╣",
        ]
        
        # Statistics
        n_elements = len(self.database.list_elements())
        n_manifolds = len(self.navigator._manifold_cache)
        
        lines.append(f"║  Database: {n_elements} elements, {n_manifolds} manifolds built")
        
        # Regime coverage
        all_regimes = set()
        for symbol in self.database.list_elements():
            try:
                m = self.navigator.get_manifold(symbol)
                all_regimes.update(
                    r for r, v in m._regime_basins.items() if v > 0.5
                )
            except:
                pass
        
        lines.append(f"║  Accessible regimes across all elements: {sorted(all_regimes)}")
        
        # Most versatile elements
        versatility = []
        for symbol in self.database.list_elements():
            try:
                m = self.navigator.get_manifold(symbol)
                n_regimes = sum(1 for v in m._regime_basins.values() if v > 0.3)
                versatility.append((symbol, n_regimes))
            except:
                pass
        
        versatility.sort(key=lambda x: -x[1])
        lines.append(f"║  Most versatile elements:")
        for sym, n in versatility[:5]:
            lines.append(f"║    {sym}: {n} regimes accessible")
        
        lines.append("╚══════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# 5. DEMO: THE PLAYGROUND IN ACTION
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("THE ELEMENTAL PLAYGROUND")
    print("Computational Phase Exploration Across the Periodic Table")
    print("=" * 70)
    
    # Initialize
    db = ElementDatabase()
    navigator = CompositionalNavigator(db)
    explorer = PhaseExplorerAgent(db)
    
    # ── Available elements ──
    print(f"\n1. ELEMENT DATABASE")
    print("-" * 50)
    print(f"   Available elements: {db.list_elements()}")
    
    # ── Individual element summaries ──
    print(f"\n2. ELEMENT S-MANIFOLD SUMMARIES")
    
    for symbol in ["Si", "C", "GaAs", "Er", "NbN"]:
        manifold = navigator.get_manifold(symbol)
        print(f"\n{manifold.get_summary()}")
    
    # ── Element comparison ──
    print(f"\n\n3. INTER-ELEMENT COMPARISONS")
    print("-" * 50)
    
    for pair in [("Si", "Ge"), ("Si", "Er"), ("Si", "C"), ("GaAs", "Si")]:
        result = navigator.compare_elements(*pair)
        print(f"\n  {pair[0]} ↔ {pair[1]}:")
        print(f"    Interface: {result['interface_quality']}")
        print(f"    Shared regimes: {result['shared_regimes']}")
        print(f"    FRET possible: {result['fret_coupling_possible']}")
    
    # ── Doping exploration ──
    print(f"\n\n4. DOPING EXPLORATION")
    print("-" * 50)
    print(f"   Doping Si to access quantum regime:")
    
    proposals = explorer.propose_doping_for_regime("Si", "quantum")
    for p in proposals[:3]:
        print(f"\n    {p['dopant']} at {p['concentration']*100:.1f}%:")
        print(f"      Quantum strength: {p['resulting_strength']:.2f}")
        print(f"      Emergent: {p['emergent']}")
    
    # ── Emergent phases at interfaces ──
    print(f"\n\n5. EMERGENT INTERFACE PHASES")
    print("-" * 50)
    
    for pair in [("Si", "Er"), ("C", "NbN"), ("GaAs", "Si")]:
        result = explorer.discover_emergent_phases(*pair)
        print(f"\n  {pair[0]}/{pair[1]} interface:")
        print(f"    {result['suggestion']}")
    
    # ── Compositional region map ──
    print(f"\n\n6. COMPOSITIONAL REGION MAP")
    print("-" * 50)
    
    region = explorer.map_entire_compositional_region(
        ["Si", "Ge", "C", "GaAs", "Er"]
    )
    
    print(f"  Nodes: {len(region['nodes'])}")
    for symbol, data in region["nodes"].items():
        print(f"    {symbol}: {data['dominant']} (holonomy: {data['holonomy']})")
    
    print(f"\n  Edges: {len(region['edges'])}")
    for edge in region["edges"]:
        print(f"    {edge['nodes'][0]}↔{edge['nodes'][1]}: "
              f"{edge['shared_regimes']} ({edge['interface_quality']})")
    
    # ── Exploration report ──
    print(f"\n\n{explorer.generate_exploration_report()}")
    
    print("\n" + "=" * 70)
    print("PLAYGROUND READY")
    print("=" * 70)
    print("""
    The Elemental Playground is now active. You can:
    
    1. Add new elements to the database:
       db.add_element(ElementProperties(...))
    
    2. Explore any element's S-manifold:
       m = navigator.get_manifold("Si")
       m.get_summary()
    
    3. Compare any two elements:
       navigator.compare_elements("Si", "C")
    
    4. Discover emergent phases:
       explorer.discover_emergent_phases("Si", "Er")
    
    5. Map entire compositional regions:
       explorer.map_entire_compositional_region([...])
    
    6. Ask the AI to find elements for a target regime:
       explorer.find_elements_for_regime("quantum")
    
    The framework generalizes to any element, any compound,
    any interface, any heterostructure. The silicon example
    was the first map. The rest is waiting.
    """)
