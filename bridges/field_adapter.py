"""
field_adapter.py
================
Thin adapter connecting Engine.GeometricEMSolver output to SensorSuite
sensor readings.

Architecture position
---------------------
  Engine.GeometricEMSolver
      └→ field_to_suite()          ← this module
              └→ SensorSuite.update()
                      └→ SensorSuite.compose()

Usage
-----
  from Engine.geometric_solver import GeometricEMSolver
  from bridges.sensor_suite import SensorSuite
  from bridges.field_adapter import field_to_suite

  solver = GeometricEMSolver()
  suite  = SensorSuite()

  field_data = solver.calculateElectromagneticField(sources, bounds)
  field_to_suite(field_data, suite)
  output = suite.compose()

Sensor mappings
---------------
  ambient_field        mean |E| + mean |B| across all grid points
  coherence            alignment of E-field vectors  (1 = all same direction)
  vigilance            spike ratio: max(|E|) / mean(|E|)  (1 = uniform)
  pressure             mean EM energy density  E² + c²B²  (normalized)
  situational_awareness fraction of grid points with active field (|E| > 10%)
"""

from __future__ import annotations

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
