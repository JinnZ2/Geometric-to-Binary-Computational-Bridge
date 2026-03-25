"""
tests/test_bridges.py — Unified test suite for all six BinaryBridgeEncoder subclasses.

Covers:
  - Pure physics helper functions (return-value accuracy)
  - Encoder instantiation, from_geometry(), to_binary() output
  - Bit-length contracts and binary alphabet
  - Input-validation / error paths
  - Round-trip determinism
"""

import math
import unittest

# ---------------------------------------------------------------------------
# Magnetic
# ---------------------------------------------------------------------------
from bridges.magnetic_encoder import (
    MagneticBridgeEncoder,
    biot_savart_magnitude,
    magnetic_flux,
    magnetic_pressure,
    larmor_frequency,
)

# ---------------------------------------------------------------------------
# Light
# ---------------------------------------------------------------------------
from bridges.light_encoder import (
    LightBridgeEncoder,
    photon_energy_eV,
    fringe_visibility,
    malus_intensity,
    brewster_angle,
    beer_lambert,
)

# ---------------------------------------------------------------------------
# Sound
# ---------------------------------------------------------------------------
from bridges.sound_encoder import (
    SoundBridgeEncoder,
    sound_pressure_level,
    beat_frequency,
    harmonic_ratio,
    standing_wave_nodes,
    doppler_shift,
)

# ---------------------------------------------------------------------------
# Gravity
# ---------------------------------------------------------------------------
from bridges.gravity_encoder import (
    GravityBridgeEncoder,
    gravitational_acceleration,
    escape_velocity,
    orbital_velocity,
    schwarzschild_radius,
    tidal_acceleration,
)

# ---------------------------------------------------------------------------
# Wave (quantum)
# ---------------------------------------------------------------------------
from bridges.wave_encoder import (
    WaveBridgeEncoder,
    de_broglie_wavelength,
    probability_density,
    particle_in_box_energy,
    uncertainty_product,
    wave_packet_group_velocity,
)

# ---------------------------------------------------------------------------
# Electric
# ---------------------------------------------------------------------------
from bridges.electric_encoder import (
    ElectricBridgeEncoder,
    ohms_law,
    power_dissipation,
    coulomb_force,
    electric_field_magnitude,
    skin_depth,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _is_binary(s: str) -> bool:
    return isinstance(s, str) and all(c in "01" for c in s)


def _make_mag():
    e = MagneticBridgeEncoder()
    e.from_geometry({
        "field_lines": [
            {"curvature": 0.2, "direction": "N"},
            {"curvature": -0.5, "direction": "S"},
            {"curvature": 0.8, "direction": "N"},
        ],
        "resonance_map": [0.7, -0.3, 0.1],
    })
    return e


def _make_lgt():
    e = LightBridgeEncoder()
    e.from_geometry({
        "polarization": ["H", "V", "V"],
        "spectrum_nm": [420, 580, 610],
        "interference_intensity": [0.9, 0.1, 0.6],
        "photon_spin": ["L", "R", "R"],
    })
    return e


def _make_snd():
    e = SoundBridgeEncoder(pitch_threshold=440, amp_threshold=0.5)
    e.from_geometry({
        "phase_radians": [0.1, 3.2],
        "frequency_hz": [220, 880],
        "amplitude": [0.3, 0.8],
        "resonance_index": [0.9, 0.2],
    })
    return e


def _make_grv():
    e = GravityBridgeEncoder()
    e.from_geometry({
        "vectors": [[0, -9.8], [0, 9.8]],
        "curvature": [1.1, -0.6],
        "orbital_stability": [0.8, 0.3],
        "potential_energy": [-5e7, 1e6],
    })
    return e


def _make_wav():
    import math as _math
    _EV     = 1.602e-19
    _M_ELEC = 9.109e-31
    _H      = 6.626e-34
    p_elec  = _math.sqrt(2 * _M_ELEC * 1.0 * _EV)
    e = WaveBridgeEncoder()
    e.from_geometry({
        "amplitudes":        [0.8, 0.4, 0.95],
        "phases_rad":        [0.3, 2.1, 5.8],
        "momenta_kg_m_s":    [p_elec, 1.5 * p_elec],
        "energy_eV":         [1.0, 4.0, 9.0],
        "uncertainty_pairs": [[1e-10, 1e-24], [5e-11, 2e-24]],
    })
    return e


def _make_elc():
    e = ElectricBridgeEncoder(Vref=1.0, conduction_threshold=1e-6)
    e.from_geometry({
        "charge": [1, -1],
        "current_A": [0.02, 0.0],
        "voltage_V": [1.2, 0.4],
        "conductivity_S": [5e-3, 0.0],
    })
    return e


# ═══════════════════════════════════════════════════════════════════════════
# 1. Magnetic
# ═══════════════════════════════════════════════════════════════════════════

class TestMagneticPhysics(unittest.TestCase):
    # biot_savart_magnitude(current, dl, position)
    # magnetic_flux(B_mag, area=1.0, theta=0.0)
    # magnetic_pressure(B_mag)
    # larmor_frequency(B_mag)

    def test_biot_savart_positive(self):
        # perpendicular dl and position → nonzero field
        val = biot_savart_magnitude(1.0, [0, 0, 1], [1, 0, 0])
        self.assertGreater(val, 0)

    def test_biot_savart_known(self):
        # |dB| = µ0*I*|dl×r̂| / (4π*r²); dl=[0,0,1], pos=[1,0,0] → |dl×r̂|=1, r=1
        # = µ0/(4π) = 1e-7
        val = biot_savart_magnitude(1.0, [0, 0, 1], [1, 0, 0])
        self.assertAlmostEqual(val, 1e-7, places=13)

    def test_biot_savart_scales_with_current(self):
        b1 = biot_savart_magnitude(1.0, [0, 0, 1], [1, 0, 0])
        b2 = biot_savart_magnitude(2.0, [0, 0, 1], [1, 0, 0])
        self.assertAlmostEqual(b2, 2 * b1, places=20)

    def test_biot_savart_parallel_zero(self):
        # dl parallel to r → cross product = 0 → B = 0
        val = biot_savart_magnitude(1.0, [1, 0, 0], [1, 0, 0])
        self.assertAlmostEqual(val, 0.0, places=15)

    def test_magnetic_flux_positive(self):
        self.assertGreater(magnetic_flux(0.5, 2.0), 0)

    def test_magnetic_flux_product(self):
        # Φ = B * A * cos(0) = 0.5 * 2.0 = 1.0
        self.assertAlmostEqual(magnetic_flux(0.5, 2.0), 1.0)

    def test_magnetic_flux_zero_area(self):
        self.assertAlmostEqual(magnetic_flux(10.0, 0.0), 0.0)

    def test_magnetic_pressure_positive(self):
        self.assertGreater(magnetic_pressure(1.0), 0)

    def test_magnetic_pressure_known(self):
        # P = B^2/(2*µ0)
        mu0 = 4e-7 * math.pi
        expected = 1.0 / (2 * mu0)
        self.assertAlmostEqual(magnetic_pressure(1.0), expected, places=0)

    def test_larmor_frequency_positive(self):
        # larmor_frequency(B_mag) — uses built-in charge/mass
        self.assertGreater(larmor_frequency(1.0), 0)

    def test_larmor_frequency_linear_in_B(self):
        f1 = larmor_frequency(1.0)
        f2 = larmor_frequency(2.0)
        self.assertAlmostEqual(f2, 2 * f1)


class TestMagneticEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        bits = _make_mag().to_binary()
        self.assertTrue(_is_binary(bits))

    def test_output_length(self):
        self.assertEqual(len(_make_mag().to_binary()), 43)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_mag().to_binary(),
            "1101100000010000110100001111001110001000000",
        )

    def test_deterministic(self):
        self.assertEqual(_make_mag().to_binary(), _make_mag().to_binary())

    def test_no_geometry_raises(self):
        e = MagneticBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_direction_polarity_flips_bits(self):
        def enc(directions):
            e = MagneticBridgeEncoder()
            e.from_geometry({
                "field_lines": [{"curvature": 0.5, "direction": d} for d in directions],
                "resonance_map": [0.5],
            })
            return e.to_binary()
        all_north = enc(["N", "N", "N"])
        all_south = enc(["S", "S", "S"])
        self.assertNotEqual(all_north, all_south)

    def test_resonance_map_affects_bits(self):
        def enc(resonance):
            e = MagneticBridgeEncoder()
            e.from_geometry({
                "field_lines": [{"curvature": 0.5, "direction": "N"}],
                "resonance_map": resonance,
            })
            return e.to_binary()
        self.assertNotEqual(enc([0.9]), enc([0.1]))

    def test_single_field_line(self):
        e = MagneticBridgeEncoder()
        e.from_geometry({
            "field_lines": [{"curvature": 0.0, "direction": "N"}],
            "resonance_map": [0.5],
        })
        bits = e.to_binary()
        self.assertTrue(_is_binary(bits))
        self.assertGreater(len(bits), 0)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Light
# ═══════════════════════════════════════════════════════════════════════════

class TestLightPhysics(unittest.TestCase):
    # photon_energy_eV(wavelength_nm)
    # fringe_visibility(intensities: list)
    # malus_intensity(I0, theta_deg)
    # brewster_angle(n1, n2)
    # beer_lambert(I0, alpha, path_length)

    def test_photon_energy_visible(self):
        # 550 nm green photon ~ 2.25 eV  (takes nm directly)
        eV = photon_energy_eV(550)
        self.assertAlmostEqual(eV, 2.25, delta=0.05)

    def test_photon_energy_uv_more_than_ir(self):
        self.assertGreater(photon_energy_eV(300), photon_energy_eV(800))

    def test_fringe_visibility_max(self):
        # [I_max, I_min] = [2, 0] → V = 1
        self.assertAlmostEqual(fringe_visibility([2.0, 0.0]), 1.0)

    def test_fringe_visibility_zero(self):
        self.assertAlmostEqual(fringe_visibility([1.0, 1.0]), 0.0)

    def test_fringe_visibility_range(self):
        v = fringe_visibility([3.0, 1.0])
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.0)

    def test_malus_intensity(self):
        self.assertAlmostEqual(malus_intensity(I0=1.0, theta_deg=0.0), 1.0)
        self.assertAlmostEqual(malus_intensity(I0=1.0, theta_deg=90.0), 0.0, places=10)

    def test_malus_intensity_45(self):
        self.assertAlmostEqual(malus_intensity(1.0, 45.0), 0.5, places=10)

    def test_brewster_angle_glass(self):
        angle = brewster_angle(n1=1.0, n2=1.5)
        self.assertAlmostEqual(angle, 56.31, delta=0.1)

    def test_brewster_angle_air(self):
        self.assertAlmostEqual(brewster_angle(1.0, 1.0), 45.0, delta=0.01)

    def test_beer_lambert_decay(self):
        # beer_lambert(I0, alpha, path_length)
        T = beer_lambert(1.0, 1.0, 1.0)
        self.assertAlmostEqual(T, math.exp(-1.0), places=10)

    def test_beer_lambert_zero_path(self):
        self.assertAlmostEqual(beer_lambert(1.0, 5.0, 0.0), 1.0, places=10)


class TestLightEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_lgt().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_lgt().to_binary()), 31)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_lgt().to_binary(),
            "0010100011010001110111010110101",
        )

    def test_deterministic(self):
        self.assertEqual(_make_lgt().to_binary(), _make_lgt().to_binary())

    def test_no_geometry_raises(self):
        e = LightBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_polarization_affects_bits(self):
        def enc(pols):
            e = LightBridgeEncoder()
            e.from_geometry({
                "polarization": pols,
                "spectrum_nm": [550],
                "interference_intensity": [0.5],
                "photon_spin": ["L"],
            })
            return e.to_binary()
        self.assertNotEqual(enc(["H"]), enc(["V"]))

    def test_spectrum_affects_bits(self):
        def enc(nm):
            e = LightBridgeEncoder()
            e.from_geometry({
                "polarization": ["H"],
                "spectrum_nm": [nm],
                "interference_intensity": [0.5],
                "photon_spin": ["L"],
            })
            return e.to_binary()
        self.assertNotEqual(enc(400), enc(700))

    def test_spin_affects_bits(self):
        def enc(spin):
            e = LightBridgeEncoder()
            e.from_geometry({
                "polarization": ["H"],
                "spectrum_nm": [550],
                "interference_intensity": [0.5],
                "photon_spin": [spin],
            })
            return e.to_binary()
        self.assertNotEqual(enc("L"), enc("R"))


# ═══════════════════════════════════════════════════════════════════════════
# 3. Sound
# ═══════════════════════════════════════════════════════════════════════════

class TestSoundPhysics(unittest.TestCase):
    # sound_pressure_level(amplitude, a_ref=1.0)  → 20*log10(amp/a_ref)
    # beat_frequency(f1, f2)
    # harmonic_ratio(f1, f2)  → min/max  (always ≤ 1)
    # standing_wave_nodes(freq, length, v=343)  → floor(2*f*L/v)
    # doppler_shift(f_source, v_source, v_sound=343)  → f*v/(v-vs); positive vs = approaching

    def test_spl_reference(self):
        # SPL(a, a_ref=a) = 20*log10(1) = 0
        self.assertAlmostEqual(sound_pressure_level(1.0, 1.0), 0.0, places=6)

    def test_spl_increases_with_amplitude(self):
        self.assertGreater(sound_pressure_level(1.0, 0.1), sound_pressure_level(1.0, 1.0))

    def test_beat_frequency(self):
        self.assertAlmostEqual(beat_frequency(440.0, 441.0), 1.0)

    def test_beat_frequency_symmetric(self):
        self.assertAlmostEqual(beat_frequency(441.0, 440.0), 1.0)

    def test_harmonic_ratio_unison(self):
        self.assertAlmostEqual(harmonic_ratio(440.0, 440.0), 1.0)

    def test_harmonic_ratio_range(self):
        # always in (0, 1]
        r = harmonic_ratio(880.0, 440.0)
        self.assertGreater(r, 0.0)
        self.assertLessEqual(r, 1.0)

    def test_standing_wave_nodes_positive(self):
        # floor(2*100*1/343) = 0; use values that give > 0
        n = standing_wave_nodes(1000.0, 1.0, 343.0)
        self.assertGreater(n, 0)

    def test_standing_wave_nodes_zero_freq(self):
        self.assertEqual(standing_wave_nodes(0.0, 1.0), 0)

    def test_doppler_shift_approaching(self):
        # positive v_source → approaching → freq increases
        f_obs = doppler_shift(440.0, 10.0, 343.0)
        self.assertGreater(f_obs, 440.0)

    def test_doppler_shift_receding(self):
        # negative v_source → receding → freq decreases
        f_obs = doppler_shift(440.0, -10.0, 343.0)
        self.assertLess(f_obs, 440.0)


class TestSoundEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_snd().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_snd().to_binary()), 31)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_snd().to_binary(),
            "1000010001101101110000011110110",
        )

    def test_deterministic(self):
        self.assertEqual(_make_snd().to_binary(), _make_snd().to_binary())

    def test_no_geometry_raises(self):
        e = SoundBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_pitch_threshold_stored(self):
        # pitch_threshold is accepted and stored (even if not yet used in encoding)
        e = SoundBridgeEncoder(pitch_threshold=880.0)
        self.assertEqual(e.pitch_threshold, 880.0)

    def test_amplitude_threshold_affects_bits(self):
        def enc(thresh):
            e = SoundBridgeEncoder(amp_threshold=thresh)
            e.from_geometry({
                "phase_radians": [1.0],
                "frequency_hz": [440],
                "amplitude": [0.5],
                "resonance_index": [0.5],
            })
            return e.to_binary()
        self.assertNotEqual(enc(0.3), enc(0.7))

    def test_frequency_affects_bits(self):
        def enc(freq):
            e = SoundBridgeEncoder()
            e.from_geometry({
                "phase_radians": [0.0],
                "frequency_hz": [freq],
                "amplitude": [0.5],
                "resonance_index": [0.5],
            })
            return e.to_binary()
        self.assertNotEqual(enc(100), enc(8000))


# ═══════════════════════════════════════════════════════════════════════════
# 4. Gravity
# ═══════════════════════════════════════════════════════════════════════════

class TestGravityPhysics(unittest.TestCase):
    # gravitational_acceleration(M, r)  → G*M/r^2
    # escape_velocity(specific_potential)  → sqrt(2*|U|)
    # orbital_velocity(specific_potential) → sqrt(|U|)
    # schwarzschild_radius(M)  → 2*G*M/c^2
    # tidal_acceleration(M, r, d)

    def test_grav_accel_earth_surface(self):
        g = gravitational_acceleration(5.972e24, 6.371e6)
        self.assertAlmostEqual(g, 9.82, delta=0.05)

    def test_grav_accel_positive(self):
        self.assertGreater(gravitational_acceleration(1e24, 1e6), 0)

    def test_grav_accel_decreases_with_radius(self):
        g1 = gravitational_acceleration(1e24, 1e6)
        g2 = gravitational_acceleration(1e24, 2e6)
        self.assertGreater(g1, g2)

    def test_escape_velocity_positive(self):
        # specific_potential = -G*M/r for Earth surface ≈ -6.25e7 J/kg
        U = -6.25e7
        self.assertGreater(escape_velocity(U), 0)

    def test_escape_velocity_earth(self):
        # v_esc = sqrt(2*G*M/r) ≈ 11186 m/s; U = -G*M/r ≈ -6.254e7
        G = 6.674e-11
        U = -G * 5.972e24 / 6.371e6  # ≈ -6.254e7 J/kg
        v = escape_velocity(U)
        self.assertAlmostEqual(v / 1e3, 11.18, delta=0.1)

    def test_orbital_velocity_positive(self):
        self.assertGreater(orbital_velocity(-6.25e7), 0)

    def test_orbital_vs_escape(self):
        U = -6.254e7
        self.assertAlmostEqual(
            orbital_velocity(U) * math.sqrt(2),
            escape_velocity(U),
            places=0,
        )

    def test_schwarzschild_radius_sun(self):
        rs = schwarzschild_radius(1.989e30)
        self.assertAlmostEqual(rs / 1e3, 2.95, delta=0.05)

    def test_schwarzschild_radius_positive(self):
        self.assertGreater(schwarzschild_radius(1e30), 0)

    def test_tidal_acceleration_positive(self):
        self.assertGreater(tidal_acceleration(1e20, 1e6, 1e3), 0)

    def test_tidal_acceleration_falls_with_distance(self):
        a1 = tidal_acceleration(1e20, 1e6, 1e3)
        a2 = tidal_acceleration(1e20, 2e6, 1e3)
        self.assertGreater(a1, a2)


class TestGravityEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_grv().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_grv().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_grv().to_binary(),
            "111001101111011011010011111000100110110",
        )

    def test_deterministic(self):
        self.assertEqual(_make_grv().to_binary(), _make_grv().to_binary())

    def test_no_geometry_raises(self):
        e = GravityBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_potential_energy_affects_bits(self):
        def enc(pe):
            e = GravityBridgeEncoder()
            e.from_geometry({
                "vectors": [[0, -9.8]],
                "curvature": [0.0],
                "orbital_stability": [0.5],
                "potential_energy": pe,
            })
            return e.to_binary()
        self.assertNotEqual(enc([-1e9]), enc([1e9]))

    def test_curvature_affects_bits(self):
        def enc(curv):
            e = GravityBridgeEncoder()
            e.from_geometry({
                "vectors": [[0, -9.8]],
                "curvature": curv,
                "orbital_stability": [0.5],
                "potential_energy": [-1e6],
            })
            return e.to_binary()
        self.assertNotEqual(enc([-10.0]), enc([10.0]))

    def test_stability_affects_bits(self):
        def enc(stab):
            e = GravityBridgeEncoder()
            e.from_geometry({
                "vectors": [[0, -9.8]],
                "curvature": [0.0],
                "orbital_stability": stab,
                "potential_energy": [-1e6],
            })
            return e.to_binary()
        self.assertNotEqual(enc([0.01]), enc([0.99]))


# ═══════════════════════════════════════════════════════════════════════════
# 5. Electric
# ═══════════════════════════════════════════════════════════════════════════

class TestElectricPhysics(unittest.TestCase):
    # ohms_law(V, I)  → R = V/I
    # power_dissipation(V, I)  → P = V*I
    # coulomb_force(q1, q2, r)
    # electric_field_magnitude(q, r)
    # skin_depth(frequency_hz, conductivity_S)

    def test_ohms_law_basic(self):
        # R = V/I = 10/2 = 5
        R = ohms_law(V=10.0, I=2.0)
        self.assertAlmostEqual(R, 5.0)

    def test_ohms_law_scales(self):
        R1 = ohms_law(10.0, 2.0)
        R2 = ohms_law(20.0, 2.0)
        self.assertAlmostEqual(R2, 2 * R1)

    def test_power_dissipation(self):
        # P = V * I = 5 * 2 = 10
        P = power_dissipation(V=5.0, I=2.0)
        self.assertAlmostEqual(P, 10.0)

    def test_power_dissipation_zero_I(self):
        self.assertAlmostEqual(power_dissipation(10.0, 0.0), 0.0)

    def test_coulomb_force_nonzero(self):
        F = coulomb_force(q1=1e-6, q2=-1e-6, r=0.1)
        self.assertNotEqual(F, 0.0)

    def test_coulomb_force_like_repels(self):
        F_like = coulomb_force(1e-6, 1e-6, 0.1)
        F_opp = coulomb_force(1e-6, -1e-6, 0.1)
        self.assertNotEqual(math.copysign(1, F_like), math.copysign(1, F_opp))

    def test_coulomb_force_distance_scaling(self):
        F1 = abs(coulomb_force(1e-6, 1e-6, 1.0))
        F2 = abs(coulomb_force(1e-6, 1e-6, 2.0))
        self.assertAlmostEqual(F1 / F2, 4.0, places=6)

    def test_electric_field_positive(self):
        E = electric_field_magnitude(q=1e-6, r=0.1)
        self.assertGreater(E, 0)

    def test_electric_field_distance_scaling(self):
        E1 = electric_field_magnitude(1e-6, 1.0)
        E2 = electric_field_magnitude(1e-6, 2.0)
        self.assertAlmostEqual(E1 / E2, 4.0, places=6)

    def test_skin_depth_copper(self):
        # copper: σ=5.96e7 S/m, f=60Hz → ~8.5 mm
        delta = skin_depth(frequency_hz=60.0, conductivity_S=5.96e7)
        self.assertAlmostEqual(delta * 1e3, 8.5, delta=0.5)

    def test_skin_depth_decreases_with_frequency(self):
        d1 = skin_depth(60.0, 5.96e7)
        d2 = skin_depth(600.0, 5.96e7)
        self.assertGreater(d1, d2)


class TestElectricEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_elc().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_elc().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_elc().to_binary(),
            "110001001010000010100011101000001010110",
        )

    def test_deterministic(self):
        self.assertEqual(_make_elc().to_binary(), _make_elc().to_binary())

    def test_no_geometry_raises(self):
        e = ElectricBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_voltage_affects_bits(self):
        def enc(volts):
            e = ElectricBridgeEncoder(Vref=1.0)
            e.from_geometry({
                "charge": [1],
                "current_A": [0.01],
                "voltage_V": volts,
                "conductivity_S": [1e-3],
            })
            return e.to_binary()
        self.assertNotEqual(enc([0.01]), enc([100.0]))

    def test_charge_sign_affects_bits(self):
        def enc(q):
            e = ElectricBridgeEncoder()
            e.from_geometry({
                "charge": q,
                "current_A": [0.01],
                "voltage_V": [1.0],
                "conductivity_S": [1e-3],
            })
            return e.to_binary()
        self.assertNotEqual(enc([1]), enc([-1]))

    def test_conduction_threshold_affects_bits(self):
        def enc(thresh):
            e = ElectricBridgeEncoder(conduction_threshold=thresh)
            e.from_geometry({
                "charge": [1],
                "current_A": [0.01],
                "voltage_V": [1.0],
                "conductivity_S": [1e-3],
            })
            return e.to_binary()
        self.assertNotEqual(enc(1e-9), enc(1.0))


# ═══════════════════════════════════════════════════════════════════════════
# 6. Wave (quantum)
# ═══════════════════════════════════════════════════════════════════════════

import math as _math_mod

_EV_J    = 1.602e-19   # 1 eV in Joules
_M_ELEC  = 9.109e-31   # electron mass (kg)
_H       = 6.626e-34   # Planck's constant
_HBAR    = _H / (2 * _math_mod.pi)
_P_1EV   = _math_mod.sqrt(2 * _M_ELEC * _EV_J)   # momentum of 1 eV electron


class TestWavePhysics(unittest.TestCase):
    # de_broglie_wavelength(momentum_kg_m_s)
    # probability_density(amplitude)
    # particle_in_box_energy(n, mass_kg, length_m)
    # uncertainty_product(delta_x, delta_p)
    # wave_packet_group_velocity(omega1, k1, omega2, k2)

    def test_de_broglie_electron_1eV(self):
        # λ = h/p for 1 eV electron ≈ 1.226 nm
        lam = de_broglie_wavelength(_P_1EV)
        self.assertAlmostEqual(lam * 1e9, 1.226, delta=0.005)

    def test_de_broglie_positive(self):
        self.assertGreater(de_broglie_wavelength(_P_1EV), 0)

    def test_de_broglie_zero_momentum(self):
        self.assertEqual(de_broglie_wavelength(0.0), float("inf"))

    def test_de_broglie_shorter_at_higher_momentum(self):
        lam1 = de_broglie_wavelength(_P_1EV)
        lam2 = de_broglie_wavelength(2 * _P_1EV)
        self.assertGreater(lam1, lam2)

    def test_probability_density_peak(self):
        # |ψ|² = 1 at ψ = 1
        self.assertAlmostEqual(probability_density(1.0), 1.0)

    def test_probability_density_zero(self):
        self.assertAlmostEqual(probability_density(0.0), 0.0)

    def test_probability_density_half_amplitude(self):
        self.assertAlmostEqual(probability_density(0.5), 0.25)

    def test_particle_in_box_ground_state(self):
        # E_1 = π²ℏ²/(2mL²) for electron in 1 nm box ≈ 0.376 eV
        E = particle_in_box_energy(1, _M_ELEC, 1e-9)
        self.assertAlmostEqual(E / _EV_J, 0.376, delta=0.005)

    def test_particle_in_box_scaling(self):
        # E_n ∝ n²  →  E_2 = 4 * E_1
        E1 = particle_in_box_energy(1, _M_ELEC, 1e-9)
        E2 = particle_in_box_energy(2, _M_ELEC, 1e-9)
        self.assertAlmostEqual(E2 / E1, 4.0, places=6)

    def test_particle_in_box_zero_length(self):
        self.assertEqual(particle_in_box_energy(1, _M_ELEC, 0.0), 0.0)

    def test_uncertainty_product_value(self):
        prod = uncertainty_product(1e-10, 1e-24)
        self.assertAlmostEqual(prod, 1e-34, places=40)

    def test_uncertainty_product_satisfies_bound(self):
        # Δx=1e-10, Δp=1e-24 → product > ℏ/2
        prod = uncertainty_product(1e-10, 1e-24)
        self.assertGreater(prod, _HBAR / 2)

    def test_group_velocity_free_electron(self):
        # v_group = Δω/Δk; for a free electron ω=p²/(2mℏ), k=p/ℏ
        # finite-difference between 1.0 and 1.1 eV gives ~midpoint velocity
        p1, p2 = _P_1EV, 1.1 * _P_1EV
        E1 = p1**2 / (2 * _M_ELEC)
        E2 = p2**2 / (2 * _M_ELEC)
        v_g = wave_packet_group_velocity(E1/_HBAR, p1/_HBAR, E2/_HBAR, p2/_HBAR)
        # midpoint momentum ≈ 1.05 * p_1eV → v ≈ 1.05 * p/m
        self.assertGreater(v_g, 0)
        self.assertAlmostEqual(v_g / 1e5, _P_1EV / _M_ELEC / 1e5, delta=0.8)

    def test_group_velocity_degenerate(self):
        # k1 = k2 → returns 0
        self.assertEqual(wave_packet_group_velocity(1.0, 1.0, 2.0, 1.0), 0.0)


class TestWaveEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_wav().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_wav().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_wav().to_binary(),
            "110110000010101111000100011010101110111",
        )

    def test_deterministic(self):
        self.assertEqual(_make_wav().to_binary(), _make_wav().to_binary())

    def test_no_geometry_raises(self):
        e = WaveBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_high_amplitude_affects_bits(self):
        def enc(amps):
            e = WaveBridgeEncoder()
            e.from_geometry({
                "amplitudes":     amps,
                "phases_rad":     [0.3] * len(amps),
                "momenta_kg_m_s": [_P_1EV],
                "energy_eV":      [1.0],
                "uncertainty_pairs": [],
            })
            return e.to_binary()
        self.assertNotEqual(enc([0.1, 0.1, 0.1]), enc([0.9, 0.9, 0.9]))

    def test_phase_affects_bits(self):
        def enc(phases):
            e = WaveBridgeEncoder()
            e.from_geometry({
                "amplitudes":     [0.5],
                "phases_rad":     phases,
                "momenta_kg_m_s": [_P_1EV],
                "energy_eV":      [1.0],
                "uncertainty_pairs": [],
            })
            return e.to_binary()
        self.assertNotEqual(enc([0.1]), enc([3.5]))

    def test_momentum_affects_bits(self):
        def enc(momenta):
            e = WaveBridgeEncoder()
            e.from_geometry({
                "amplitudes":     [0.5, 0.5],
                "phases_rad":     [0.5, 0.5],
                "momenta_kg_m_s": momenta,
                "energy_eV":      [1.0],
                "uncertainty_pairs": [],
            })
            return e.to_binary()
        self.assertNotEqual(enc([_P_1EV, _P_1EV]), enc([100 * _P_1EV, 100 * _P_1EV]))

    def test_energy_affects_bits(self):
        def enc(eV_list):
            e = WaveBridgeEncoder()
            e.from_geometry({
                "amplitudes":     [0.5],
                "phases_rad":     [0.5],
                "momenta_kg_m_s": [_P_1EV],
                "energy_eV":      eV_list,
                "uncertainty_pairs": [],
            })
            return e.to_binary()
        self.assertNotEqual(enc([0.001]), enc([500.0]))


# ═══════════════════════════════════════════════════════════════════════════
# 7. Cross-encoder sanity
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossEncoder(unittest.TestCase):
    """Ensure all six encoders produce distinct, valid outputs."""

    def setUp(self):
        self.encoders = {
            "magnetic": _make_mag(),
            "light":    _make_lgt(),
            "sound":    _make_snd(),
            "gravity":  _make_grv(),
            "electric": _make_elc(),
            "wave":     _make_wav(),
        }
        self.bits = {name: e.to_binary() for name, e in self.encoders.items()}

    def test_all_binary(self):
        for name, b in self.bits.items():
            with self.subTest(encoder=name):
                self.assertTrue(_is_binary(b))

    def test_all_non_empty(self):
        for name, b in self.bits.items():
            with self.subTest(encoder=name):
                self.assertGreater(len(b), 0)

    def test_outputs_are_distinct(self):
        values = list(self.bits.values())
        unique = set(values)
        self.assertGreater(len(unique), 1)

    def test_expected_lengths(self):
        self.assertEqual(len(self.bits["magnetic"]), 43)
        self.assertEqual(len(self.bits["light"]),    31)
        self.assertEqual(len(self.bits["sound"]),    31)
        self.assertEqual(len(self.bits["gravity"]),  39)
        self.assertEqual(len(self.bits["electric"]), 39)
        self.assertEqual(len(self.bits["wave"]),     39)


if __name__ == "__main__":
    unittest.main(verbosity=2)
