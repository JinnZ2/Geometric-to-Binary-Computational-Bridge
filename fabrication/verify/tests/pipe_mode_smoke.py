"""
pipe_mode_smoke.py  (fabrication/verify/tests/)

Synthetic cylinder cavity at 4 cm radius × 20 cm length:
  - lowest lumped mode prediction would be off (ka > 0.3)
  - distributed prediction captures axial + transverse modes
  - sanity: first axial mode equals c/(2L) exactly
  - ka_check correctly fires

This smoke verifies the PREDICTOR end of the pipe-mode wedge. The
verifier loop (measure -> match -> verdict) is exercised by
multimode_smoke; once a real device is built, the same loop runs
on top of these distributed-mode claims unchanged.

Run with:
    PYTHONPATH=/path/to/repo  python -m fabrication.verify.tests.pipe_mode_smoke

License: CC0. Stdlib only.
"""
from ...pipe_modes import cylinder_modes, ka_check, C_AIR


if __name__ == "__main__":
    radius, length = 0.04, 0.20
    # For a sealed cylinder at 4 cm radius, the lumped chain model
    # stays valid only while ka < 0.3. Pick a "lumped lowest mode"
    # high enough that ka tips over the threshold and the
    # distributed predictor is the honest choice. (At ~500 Hz with
    # a=0.04 m, ka = 2π·500/343 · 0.04 ≈ 0.37.)
    geom_hints = {
        "distributed":          "cylinder",
        "radius":               radius,
        "length":               length,
        "n_axial":              3,
        "m_radial":             2,
        "characteristic_dim_m": radius,
        "lumped_f_lowest_Hz":   500.0,
    }
    ka = ka_check(geom_hints)
    print(f"ka = {ka:.3f}   (>0.3 => promote to distributed)")
    assert ka > 0.3, "test setup expects ka > 0.3"

    modes = cylinder_modes(radius, length, n_axial=3, m_radial=2)
    print("first 8 cylinder modes:")
    for m in modes[:8]:
        print(f"  idx={m['mode_index']:2d}  "
              f"f={m['f']:7.1f} Hz   "
              f"axial_n={m['axial_n']}  radial={m['radial']}")

    # sanity: first axial mode = c/(2L)
    f_axial_1 = next(m for m in modes
                     if m["axial_n"] == 1 and m["radial"] == (0, 0))["f"]
    assert abs(f_axial_1 - C_AIR / (2*length)) < 1e-6, \
        f"axial-1 mode mismatch: {f_axial_1} vs {C_AIR/(2*length)}"
    print("pipe-mode smoke OK")
