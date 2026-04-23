"""
field_adapter.py
================
Thin adapter connecting Engine.GeometricEMSolver output to downstream
interpreters — the binary SensorSuite and the dual-path alternative
dispatcher.

Architecture position
---------------------
  Engine.GeometricEMSolver
      ├→ field_to_suite()          binary path → SensorSuite.update()
      └→ field_to_alternative()    ternary path → encode_state(mode="dual")

Usage — binary path (unchanged)
-------------------------------
  from Engine.geometric_solver import GeometricEMSolver
  from bridges.sensor_suite import SensorSuite
  from bridges.field_adapter import field_to_suite

  solver = GeometricEMSolver()
  suite  = SensorSuite()
  field_data = solver.calculateElectromagneticField(sources, bounds)
  field_to_suite(field_data, suite)
  output = suite.compose()

Usage — alternative path
------------------------
  from bridges.field_adapter import field_to_alternative
  dual = field_to_alternative(field_data, mode="dual", frequency_hz=60.0)
  # dual = {"binary": "...", "alternative": <ElectricAlternativeDiagnostic>}

Sensor mappings (binary path)
-----------------------------
  ambient_field        mean |E| + mean |B| across all grid points
  coherence            alignment of E-field vectors  (1 = all same direction)
  vigilance            spike ratio: max(|E|) / mean(|E|)  (1 = uniform)
  pressure             mean EM energy density  E² + c²B²  (normalized)
  situational_awareness fraction of grid points with active field (|E| > 10%)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

# Speed of light — used to put E and B on the same energy-density scale.
_C = 2.998e8   # m/s


def field_to_suite(field_data: dict,
                   suite,
                   E_scale: float | None = None,
                   confidence: float = 1.0) -> None:
    """
    Update SensorSuite readings from GeometricEMSolver field data.

    Parameters
    ----------
    field_data : dict
        Output of GeometricEMSolver.calculateElectromagneticField().
        Required keys: 'electricField', 'magneticField', 'points'.
        Values are lists of [x, y, z] vectors.
    suite : SensorSuite
        The sensor suite to update in place.
    E_scale : float or None
        Characteristic E-field magnitude for normalization (V/m).
        When None (default) the 95th-percentile field magnitude in
        the current data is used, so readings always span [0, 1]
        regardless of source strength.  Pass an explicit value (e.g.
        1e4) to compare runs on an absolute physical scale.
    confidence : float
        Epistemic confidence applied to all readings from this call.
        Pass < 1.0 for coarse grids or estimated source configurations.
    """
    E_raw = field_data.get("electricField", [])
    B_raw = field_data.get("magneticField", [])
    pts   = field_data.get("points", [])

    if not E_raw:
        # No field data — quiesce the five physical sensors this adapter drives.
        for sensor_id in ("ambient_field", "coherence", "vigilance",
                          "pressure", "situational_awareness"):
            suite.reset(sensor_id)
        return

    E = np.asarray(E_raw, dtype=float)          # (N, 3)
    pts = np.asarray(pts, dtype=float)          # (N, 3)
    B = np.asarray(B_raw, dtype=float) if B_raw else np.zeros_like(E)

    E_mag = np.linalg.norm(E, axis=1)           # (N,)  magnitudes
    B_mag = np.linalg.norm(B, axis=1)

    # Determine normalization scale.
    if E_scale is None:
        # Auto-scale: use 95th percentile so a few extreme near-source
        # points don't compress everything else to near zero.
        E_scale = float(np.percentile(E_mag, 95)) or 1.0

    # Normalize to [0, 1] against characteristic scales.
    B_scale = E_scale / _C
    E_norm  = np.clip(E_mag / E_scale, 0.0, 1.0)
    B_norm  = np.clip(B_mag / B_scale, 0.0, 1.0)

    # ------------------------------------------------------------------
    # 1. ambient_field — mean field activity across the whole domain.
    #    signal_vector = mean E vector (direction of dominant field).
    # ------------------------------------------------------------------
    ambient   = float((E_norm.mean() + B_norm.mean()) / 2.0)
    mean_E    = E.mean(axis=0).tolist()
    suite.update("ambient_field",
                 signal_vector=mean_E,
                 magnitude=ambient,
                 confidence=confidence)

    # ------------------------------------------------------------------
    # 2. coherence — how aligned are the E-field vectors?
    #    1.0 = all vectors point the same way (organised field)
    #    0.0 = vectors cancel out (isotropic / random)
    # ------------------------------------------------------------------
    E_unit    = E / (E_mag[:, None] + 1e-30)    # unit vectors
    mean_unit = E_unit.mean(axis=0)
    alignment = float(np.linalg.norm(mean_unit))
    if ambient > 0.01:
        suite.update("coherence",
                     signal_vector=mean_unit.tolist(),
                     magnitude=alignment,
                     confidence=confidence)

    # ------------------------------------------------------------------
    # 3. vigilance — spike ratio: are some regions much stronger?
    #    Ratio of 1 = flat field.  Ratio >> 1 = concentrated hotspot.
    #    Normalised so ratio=10 → magnitude=1.
    # ------------------------------------------------------------------
    mean_norm = float(E_norm.mean())
    if mean_norm > 1e-6:
        spike_ratio = float(E_norm.max()) / mean_norm
        vigilance   = float(np.clip((spike_ratio - 1.0) / 9.0, 0.0, 1.0))
        hotspot     = pts[int(E_mag.argmax())].tolist()
        suite.update("vigilance",
                     signal_vector=hotspot,
                     magnitude=vigilance,
                     confidence=confidence)

    # ------------------------------------------------------------------
    # 4. pressure — mean EM energy density (E² + c²B² proxy).
    #    Relates to Maxwell stress: the force the field exerts on matter.
    # ------------------------------------------------------------------
    energy_density = E_norm ** 2 + B_norm ** 2
    pressure       = float(np.clip(energy_density.mean(), 0.0, 1.0))
    suite.update("pressure",
                 signal_vector=[pressure, 0.0, 0.0],
                 magnitude=pressure,
                 confidence=confidence)

    # ------------------------------------------------------------------
    # 5. situational_awareness — spatial coverage of active field.
    #    Magnitude = fraction of grid points where |E| > 10% of scale.
    #    signal_vector = bounding-box extents of the active region.
    # ------------------------------------------------------------------
    active_mask = E_norm > 0.10
    active_frac = float(active_mask.mean())
    active_pts  = pts[active_mask] if active_mask.any() else pts[:1]
    bbox        = (active_pts.max(axis=0) - active_pts.min(axis=0)).tolist()
    suite.update("situational_awareness",
                 signal_vector=bbox,
                 magnitude=active_frac,
                 confidence=confidence)


# ===========================================================================
# Alternative path — solver output → encode_state dispatcher
# ===========================================================================

def field_to_geometry(field_data: dict) -> Dict[str, Any]:
    """
    Project raw solver output into the ``geometry`` dict schema that
    ``bridges.encode_state`` and the ``ElectricBridgeEncoder`` expect.

    The solver returns per-point E and B vectors. The encoders want
    lists of scalars in named physical slots. The mapping below is the
    minimal, reversible projection:

      charge          ← source charges from sources[].charge (if present)
      current_A       ← radial component of E projected onto mean-E axis
                        (signed scalar per grid point — preserves AC
                        zero-crossing structure for the ternary analyser)
      voltage_V       ← |E| at each point scaled by 1m (Volts per metre
                        × nominal 1 m gauge length)
      conductivity_S  ← pass-through from sources[].conductivity if any

    This is a coarse projection, not a physics identity — it exists so
    the ternary / stochastic / quantum analysers can operate on real
    solver output without requiring callers to hand-craft geometry
    dicts. Downstream interpretation should use the full field data
    via ``field_to_suite`` when spatial structure matters.
    """
    E_raw = field_data.get("electricField", [])
    B_raw = field_data.get("magneticField", [])
    sources = field_data.get("sources", []) or []

    geometry: Dict[str, Any] = {}

    if E_raw:
        E = np.asarray(E_raw, dtype=float)
        E_mag = np.linalg.norm(E, axis=1)
        # Signed scalar: project every E vector onto the mean-direction
        # unit vector. Preserves sign so zero-crossings survive.
        mean_E = E.mean(axis=0)
        mean_norm = float(np.linalg.norm(mean_E))
        if mean_norm > 0:
            mean_unit = mean_E / mean_norm
            signed = (E @ mean_unit).astype(float).tolist()
            geometry["current_A"] = signed
        else:
            geometry["current_A"] = [0.0] * len(E_mag)

        geometry["voltage_V"] = E_mag.astype(float).tolist()

    # Source-level quantities (if the solver attached them).
    charges = [
        float(s["charge"]) for s in sources
        if isinstance(s, dict) and "charge" in s
    ]
    if charges:
        geometry["charge"] = charges

    conductivities = [
        float(s["conductivity"]) for s in sources
        if isinstance(s, dict) and "conductivity" in s
    ]
    if conductivities:
        geometry["conductivity_S"] = conductivities

    # Surface magnetic magnitudes are occasionally useful for future
    # magnetic-bridge wiring; attach as a non-standard key rather than
    # polluting the electric encoder schema.
    if B_raw:
        B = np.asarray(B_raw, dtype=float)
        geometry["_magnetic_magnitude"] = (
            np.linalg.norm(B, axis=1).astype(float).tolist()
        )

    return geometry


def field_to_alternative(
    field_data: dict,
    mode: str = "dual",
    domain: str = "electric",
    frequency_hz: Optional[float] = None,
) -> Any:
    """
    Route Engine solver output through the alternative-computing dispatcher.

    Parameters
    ----------
    field_data
        Output of ``GeometricEMSolver.calculateElectromagneticField``.
    mode
        Forwarded to :func:`bridges.encode_state.encode_state` — one of
        ``"binary"``, ``"ternary"``, or ``"dual"``.
    domain
        Target domain. Defaults to ``"electric"`` because solver output
        is electromagnetic; pass ``"magnetic"`` once that domain's
        alternative interpreter is wired up to route the B-field
        component separately.
    frequency_hz
        Excitation frequency for skin-effect / zero-crossing analyses.

    Returns
    -------
    str | object | dict
        Shape depends on ``mode`` — see ``encode_state`` docstring.
    """
    # Import locally so this module stays usable in environments where
    # only the binary-path half of the repo is available.
    from bridges.encode_state import encode_state

    geometry = field_to_geometry(field_data)
    return encode_state(
        geometry,
        domain=domain,
        mode=mode,
        frequency_hz=frequency_hz,
    )


__all__ = [
    "field_to_suite",
    "field_to_geometry",
    "field_to_alternative",
]
