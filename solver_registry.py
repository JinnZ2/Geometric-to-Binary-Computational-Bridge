# STATUS: infrastructure -- unified solver registry for AI-driven module composition
"""
solver_registry.py — Mix-and-match solver for the Geometric-to-Binary bridge
=============================================================================

Any AI can import this module and immediately compose computational pipelines
from the full stack: GEIS encoding, bridge encoders, Silicon physics, FRET
coupling, NFS factorization, and lattice simulations.

Usage:
    from solver_registry import Registry

    reg = Registry()

    # List available solvers
    reg.list_solvers()

    # Solve a specific problem
    result = reg.solve('encode_magnetic', field_lines=[...])
    result = reg.solve('dft_to_T2', dft_points=[...], strain=1.2, distance=4.8)
    result = reg.solve('factor', N=1073)

    # Discover composable chains
    reg.show_chains('binary_encoding')

    # Get a solver's signature
    reg.describe('fret_efficiency')

Design:
    Each solver is a thin wrapper around an existing module function.
    The registry tracks input/output types so an AI can discover which
    solvers chain together without reading source code.
"""

import sys
import os
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# Ensure project root is on path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# =========================================================================
# Solver descriptor
# =========================================================================

@dataclass
class Solver:
    """Metadata for one registered solver."""
    name: str
    category: str           # geis, bridge, silicon, fret, lattice, nfs
    description: str
    inputs: Dict[str, str]  # param_name -> "type (unit)"
    outputs: Dict[str, str] # output_name -> "type (unit)"
    func: Callable
    composable_from: List[str] = field(default_factory=list)  # solvers whose output feeds this input

    def __call__(self, **kwargs):
        return self.func(**kwargs)


# =========================================================================
# Registry
# =========================================================================

class Registry:
    """
    Central registry of all computational solvers in the project.

    Provides:
      - solve(name, **params) — run any registered solver
      - list_solvers(category=None) — list all or filter by category
      - describe(name) — show a solver's inputs, outputs, and chains
      - show_chains(output_type) — find all solvers that produce a given output
      - compose(names) — chain multiple solvers together
    """

    def __init__(self):
        self._solvers: Dict[str, Solver] = {}
        self._register_all()

    def _register(self, solver: Solver):
        self._solvers[solver.name] = solver

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def solve(self, name: str, **kwargs) -> Any:
        """Run a named solver with the given parameters."""
        if name not in self._solvers:
            raise KeyError(
                f"Unknown solver '{name}'. "
                f"Available: {', '.join(sorted(self._solvers))}"
            )
        return self._solvers[name](**kwargs)

    def list_solvers(self, category: str = None) -> List[str]:
        """List solver names, optionally filtered by category."""
        solvers = []
        for name, s in sorted(self._solvers.items()):
            if category is None or s.category == category:
                solvers.append(name)
                print(f"  [{s.category:8s}] {name:30s} -- {s.description}")
        return solvers

    def describe(self, name: str) -> Dict:
        """Return full metadata for a solver."""
        s = self._solvers[name]
        info = {
            'name': s.name,
            'category': s.category,
            'description': s.description,
            'inputs': s.inputs,
            'outputs': s.outputs,
            'composable_from': s.composable_from,
        }
        print(f"\n{s.name} [{s.category}]")
        print(f"  {s.description}")
        print(f"  Inputs:")
        for k, v in s.inputs.items():
            print(f"    {k}: {v}")
        print(f"  Outputs:")
        for k, v in s.outputs.items():
            print(f"    {k}: {v}")
        if s.composable_from:
            print(f"  Feeds from: {', '.join(s.composable_from)}")
        return info

    def show_chains(self, output_type: str) -> List[str]:
        """Find all solvers that produce outputs matching a keyword."""
        matches = []
        for name, s in self._solvers.items():
            for out_name, out_type in s.outputs.items():
                if output_type.lower() in out_name.lower() or output_type.lower() in out_type.lower():
                    matches.append(name)
                    break
        if matches:
            print(f"\nSolvers producing '{output_type}':")
            for m in matches:
                s = self._solvers[m]
                print(f"  {m} -> {s.outputs}")
        return matches

    def compose(self, names: List[str], **initial_kwargs) -> Any:
        """
        Chain multiple solvers: output of each feeds the next.

        The first solver receives **initial_kwargs. Each subsequent solver
        receives the dict returned by the previous one (merged with any
        remaining kwargs).
        """
        result = initial_kwargs
        for name in names:
            s = self._solvers[name]
            # Filter kwargs to only what this solver accepts
            accepted = set(s.inputs.keys())
            call_kwargs = {k: v for k, v in result.items() if k in accepted}
            output = s(**call_kwargs)
            if isinstance(output, dict):
                result.update(output)
            else:
                result[f'{name}_result'] = output
        return result

    def categories(self) -> List[str]:
        """List all registered categories."""
        cats = sorted(set(s.category for s in self._solvers.values()))
        for c in cats:
            count = sum(1 for s in self._solvers.values() if s.category == c)
            print(f"  {c}: {count} solvers")
        return cats

    # -----------------------------------------------------------------
    # Registration of all modules
    # -----------------------------------------------------------------

    def _register_all(self):
        self._register_geis()
        self._register_bridges()
        self._register_silicon_core()
        self._register_silicon_fret()
        self._register_silicon_lattice()
        self._register_nfs()

    # --- GEIS ---

    def _register_geis(self):
        from GEIS.geometric_encoder import GeometricEncoder
        from GEIS.octahedral_state import OctahedralState

        encoder = GeometricEncoder()

        self._register(Solver(
            name='encode_token',
            category='geis',
            description='Encode a geometric token (e.g. "001|O") to binary string',
            inputs={'token': 'str (vertex_bits|operator|symbol)'},
            outputs={'binary': 'str (binary bitstring)'},
            func=lambda token: {'binary': encoder.encode_to_binary(token)},
        ))

        self._register(Solver(
            name='decode_binary',
            category='geis',
            description='Decode a binary string back to geometric token',
            inputs={'binary': 'str (binary bitstring)'},
            outputs={'token': 'str (vertex_bits|operator|symbol)'},
            func=lambda binary: {'token': encoder.decode_from_binary(binary)},
        ))

        self._register(Solver(
            name='octahedral_state',
            category='geis',
            description='Create an octahedral state from vertex index (0-7)',
            inputs={'index': 'int (0-7)'},
            outputs={'state': 'OctahedralState', 'binary': 'str (3-bit)', 'position': 'tuple (x,y,z)'},
            func=lambda index: {
                'state': OctahedralState(index),
                'binary': OctahedralState(index).to_binary(),
                'position': OctahedralState(index).position,
            },
        ))

    # --- Bridges ---

    def _register_bridges(self):
        from bridges.magnetic_encoder import MagneticBridgeEncoder
        from bridges.light_encoder import LightBridgeEncoder
        from bridges.gravity_encoder import GravityBridgeEncoder
        from bridges.thermal_encoder import ThermalBridgeEncoder
        from bridges.wave_encoder import WaveBridgeEncoder
        from bridges.sound_encoder import SoundBridgeEncoder
        from bridges.electric_encoder import ElectricBridgeEncoder
        from bridges.pressure_encoder import PressureBridgeEncoder
        from bridges.chemical_encoder import ChemicalBridgeEncoder
        from bridges.community_encoder import CommunityBridgeEncoder
        from Silicon.core.bridges.geometric_fiber_encoder import GeometricFiberEncoder
        from bridges.cognitive.consciousness_encoder import ConsciousnessBridgeEncoder
        from bridges.cognitive.emotion_encoder import EmotionBridgeEncoder

        bridge_map = {
            'magnetic':      (MagneticBridgeEncoder,      43),
            'light':         (LightBridgeEncoder,         31),
            'sound':         (SoundBridgeEncoder,         31),
            'gravity':       (GravityBridgeEncoder,       39),
            'electric':      (ElectricBridgeEncoder,      39),
            'wave':          (WaveBridgeEncoder,           39),
            'thermal':       (ThermalBridgeEncoder,       39),
            'pressure':      (PressureBridgeEncoder,      39),
            'chemical':        (ChemicalBridgeEncoder,      39),
            'community':       (CommunityBridgeEncoder,     39),
            'geometric_fiber': (GeometricFiberEncoder,      39),
            'consciousness':   (ConsciousnessBridgeEncoder, 39),
            'emotion':       (EmotionBridgeEncoder,       39),
        }

        for domain, (cls, bits) in bridge_map.items():
            self._register(Solver(
                name=f'encode_{domain}',
                category='bridge',
                description=f'Encode {domain} field geometry to {bits}-bit binary (Gray coded)',
                inputs={'geometry': f'dict ({domain} field parameters)'},
                outputs={'binary': f'str ({bits}-bit)', 'report': 'dict'},
                func=self._make_bridge_func(cls),
            ))

    @staticmethod
    def _make_bridge_func(encoder_cls):
        def bridge_encode(geometry):
            enc = encoder_cls()
            enc.from_geometry(geometry)
            binary = enc.to_binary()
            return {'binary': binary, 'report': enc.report()}
        return bridge_encode

    # --- Silicon Core ---

    def _register_silicon_core(self):
        from Silicon.core.bridges.hardware_bridge import (
            dft_to_kwell, physical_magnetic_energy,
            fret_confinement_stiffness, total_kwell, dft_to_T2,
            fret_coupling_energy, DFTPoint,
        )
        from Silicon.core.geometry.octahedral_sim import k_well, sigma_T, T2_from_kwell

        self._register(Solver(
            name='dft_to_kwell',
            category='silicon',
            description='Extract confinement stiffness from DFT formation energies',
            inputs={'points': 'list of DFTPoint', 'strain_pct': 'float (%)'},
            outputs={'k_well': 'float (eV/A^2)', 'x_eq': 'float (A)', 'E_min': 'float (eV)'},
            func=lambda points, strain_pct: dict(zip(
                ['k_well', 'x_eq', 'E_min'], dft_to_kwell(points, strain_pct)
            )),
        ))

        self._register(Solver(
            name='fret_stiffness',
            category='silicon',
            description='FRET coupling contribution to confinement stiffness',
            inputs={'d_ang': 'float (A, Er-P distance)'},
            outputs={'k_fret': 'float (eV/A^2)', 'U_fret': 'float (eV)'},
            func=lambda d_ang: {
                'k_fret': fret_confinement_stiffness(d_ang),
                'U_fret': fret_coupling_energy(d_ang),
            },
        ))

        self._register(Solver(
            name='magnetic_energy',
            category='silicon',
            description='Physical magnetic energy from tensor eigenvalues and B field',
            inputs={'eigenvalues': 'tuple (l1,l2,l3)', 'B_vec': 'array (T)'},
            outputs={'E_mag': 'float (eV)'},
            func=lambda eigenvalues, B_vec: {
                'E_mag': physical_magnetic_energy(eigenvalues, np.asarray(B_vec)),
            },
        ))

        self._register(Solver(
            name='coherence_time',
            category='silicon',
            description='T2 coherence time from strain and Er-P distance',
            inputs={'strain_pct': 'float (%)', 'dist_ang': 'float (A)'},
            outputs={'k_well': 'float (eV/A^2)', 'T2_ms': 'float (ms)', 'sigma_T': 'float (A)'},
            func=lambda strain_pct, dist_ang: {
                'k_well': k_well(strain_pct, dist_ang),
                'T2_ms': T2_from_kwell(k_well(strain_pct, dist_ang)),
                'sigma_T': sigma_T(k_well(strain_pct, dist_ang)),
            },
            composable_from=['dft_to_kwell'],
        ))

        self._register(Solver(
            name='full_hardware_chain',
            category='silicon',
            description='Full DFT -> k_well -> FRET -> T2 pipeline',
            inputs={'points': 'list of DFTPoint', 'strain_pct': 'float (%)',
                    'd_ang': 'float (A)', 'temperature': 'float (K)'},
            outputs={'k_dft': 'float', 'k_fret': 'float', 'k_total': 'float',
                     'T2_ms': 'float', 'sigma_T_ang': 'float'},
            func=lambda points, strain_pct, d_ang, temperature=300.0: dft_to_T2(
                points, strain_pct, d_ang, temperature
            ),
            composable_from=['dft_to_kwell', 'fret_stiffness'],
        ))

    # --- Silicon FRET ---

    def _register_silicon_fret(self):
        from Silicon.FRET.fret_core import R0 as R0_func, k_FRET, E_FRET

        self._register(Solver(
            name='fret_efficiency',
            category='fret',
            description='FRET efficiency E = 1/(1+(r/R0)^6)',
            inputs={'r': 'float (distance)', 'R0': 'float (Forster radius)'},
            outputs={'efficiency': 'float (0-1)'},
            func=lambda r, R0: {'efficiency': E_FRET(r, R0)},
        ))

        self._register(Solver(
            name='fret_rate',
            category='fret',
            description='FRET rate constant k = (1/tau_D)(R0/r)^6',
            inputs={'r': 'float', 'R0': 'float', 'tau_D': 'float (donor lifetime)'},
            outputs={'rate': 'float (1/tau_D units)'},
            func=lambda r, R0, tau_D: {'rate': k_FRET(r, R0, tau_D)},
        ))

        self._register(Solver(
            name='forster_radius',
            category='fret',
            description='Compute Forster radius from molecular parameters',
            inputs={'kappa2': 'float (orientation)', 'Phi_D': 'float (quantum yield)',
                    'n': 'float (refractive index)', 'J': 'float (spectral overlap)'},
            outputs={'R0': 'float (A)'},
            func=lambda kappa2, Phi_D, n, J: {'R0': R0_func(kappa2, Phi_D, n, J)},
        ))

    # --- Silicon Lattice ---

    def _register_silicon_lattice(self):
        from Silicon.lattice.vff_keating import SiliconOctahedron

        self._register(Solver(
            name='keating_energy',
            category='lattice',
            description='Keating VFF strain energy for central atom displacement',
            inputs={'displacement': 'array (dx,dy,dz in A)',
                    'd0': 'float (bond length A)', 'alpha': 'float (eV/A^2)',
                    'beta': 'float (eV/A^2)'},
            outputs={'energy': 'float (eV)'},
            func=lambda displacement, d0=2.35, alpha=3.0, beta=0.75: {
                'energy': SiliconOctahedron(d0, alpha, beta).keating_energy(
                    np.asarray(displacement)
                ),
            },
        ))

        self._register(Solver(
            name='find_8_states',
            category='lattice',
            description='Find 8 octahedral minima in Keating energy landscape',
            inputs={'d0': 'float (A)', 'alpha': 'float (eV/A^2)',
                    'beta': 'float (eV/A^2)', 'n_starts': 'int'},
            outputs={'minima': 'array (N,3)', 'energies': 'list of float (eV)',
                     'n_found': 'int'},
            func=lambda d0=2.35, alpha=3.0, beta=0.75, n_starts=80: (
                lambda cluster, minima: {
                    'minima': minima.tolist() if len(minima) > 0 else [],
                    'energies': [float(cluster.keating_energy(m)) for m in minima],
                    'n_found': len(minima),
                }
            )(SiliconOctahedron(d0, alpha, beta),
              SiliconOctahedron(d0, alpha, beta).find_minima(n_starts)),
        ))

    # --- NFS ---

    def _register_nfs(self):
        self._register(Solver(
            name='factor',
            category='nfs',
            description='Factor an integer using the geometric NFS pipeline',
            inputs={'N': 'int (number to factor)',
                    'B_bound': 'int (smoothness bound, optional)'},
            outputs={'factor': 'int', 'other_factor': 'int', 'found': 'bool',
                     'method': 'str', 'T2_ms': 'float'},
            func=self._nfs_factor,
        ))

    @staticmethod
    def _nfs_factor(N, B_bound=None):
        from experiments.geometric_nfs import geometric_nfs
        result = geometric_nfs(N, B_bound=B_bound)
        return {
            'found': result.found,
            'factor': result.factor,
            'other_factor': result.other_factor,
            'method': result.method,
            'sieve_ms': result.sieve_ms,
            'total_ms': result.total_ms,
            'smooth_found': result.smooth_found,
        }


# =========================================================================
# Demo / self-test
# =========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Solver Registry — Mix-and-Match Computational Bridge")
    print("=" * 70)

    reg = Registry()

    print("\n--- Categories ---")
    reg.categories()

    print("\n--- All Solvers ---")
    reg.list_solvers()

    print("\n--- Example: Encode a geometric token ---")
    result = reg.solve('encode_token', token='001|O')
    print(f"  Token '001|O' -> binary '{result['binary']}'")

    print("\n--- Example: Decode back ---")
    result2 = reg.solve('decode_binary', binary=result['binary'])
    print(f"  Binary '{result['binary']}' -> token '{result2['token']}'")

    print("\n--- Example: FRET efficiency ---")
    result3 = reg.solve('fret_efficiency', r=3.0, R0=5.0)
    print(f"  E_FRET(r=3, R0=5) = {result3['efficiency']:.4f}")

    print("\n--- Example: Coherence time ---")
    result4 = reg.solve('coherence_time', strain_pct=1.2, dist_ang=4.8)
    print(f"  T2 at optimal (1.2%, 4.8A) = {result4['T2_ms']:.1f} ms")

    print("\n--- Example: Magnetic energy ---")
    result5 = reg.solve('magnetic_energy',
                         eigenvalues=(1, 0, 0),
                         B_vec=[0.0, 0.0, 1.0])
    print(f"  E_mag(state 0, B_z=1T) = {result5['E_mag']*1e6:.1f} uev")

    print("\n--- Example: Keating energy ---")
    result6 = reg.solve('keating_energy', displacement=[0.2, 0.2, 0.2])
    print(f"  E_keating([0.2,0.2,0.2]) = {result6['energy']:.4f} eV")

    print("\n--- Chains producing 'binary' ---")
    reg.show_chains('binary')

    print("\n--- Describe full_hardware_chain ---")
    reg.describe('full_hardware_chain')

    print("\n" + "=" * 70)
    print(f"Registry: {len(reg._solvers)} solvers across "
          f"{len(set(s.category for s in reg._solvers.values()))} categories")
    print("=" * 70)
