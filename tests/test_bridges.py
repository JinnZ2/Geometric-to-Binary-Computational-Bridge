"""
tests/test_bridges.py — Unified test suite for all eleven BinaryBridgeEncoder subclasses.

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
# Thermal
# ---------------------------------------------------------------------------
from bridges.thermal_encoder import (
    ThermalBridgeEncoder,
    blackbody_peak_wavelength,
    stefan_boltzmann_radiance,
    heat_flux_fourier,
    newton_cooling_rate,
    johnson_nyquist_noise,
)

# ---------------------------------------------------------------------------
# Pressure / Haptic
# ---------------------------------------------------------------------------
from bridges.pressure_encoder import (
    PressureBridgeEncoder,
    ATM,
    hydrostatic_pressure,
    elastic_stress,
    bulk_compression,
    acoustic_radiation_pressure,
    piezoelectric_voltage,
)

# ---------------------------------------------------------------------------
# Chemical
# ---------------------------------------------------------------------------
from bridges.chemical_encoder import (
    ChemicalBridgeEncoder,
    arrhenius_rate,
    nernst_potential,
    henry_concentration,
    bond_energy_delta,
    ph_from_concentration,
)

# ---------------------------------------------------------------------------
# Consciousness
# ---------------------------------------------------------------------------
from bridges.consciousness_encoder import (
    ConsciousnessBridgeEncoder,
    shannon_entropy,
    kl_divergence,
    mutual_information,
    fisher_information,
    integrated_information,
)

# ---------------------------------------------------------------------------
# Emotion
# ---------------------------------------------------------------------------
from bridges.emotion_encoder import (
    EmotionBridgeEncoder,
    pad_intensity,
    valence_arousal_coherence,
    surprise_factor,
    cross_bridge_resonance,
    drill_target,
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


def _make_con():
    e = ConsciousnessBridgeEncoder(
        conf_threshold=0.7,
        entropy_threshold=2.0,
        focus_threshold=0.5,
        awareness_threshold=0.5,
    )
    e.from_geometry({
        "confidence_values": [0.3, 0.65, 0.91],
        "entropy_distributions": [
            [0.25, 0.25, 0.25, 0.25],
            [0.5, 0.3, 0.15, 0.05],
            [0.95, 0.03, 0.01, 0.01],
        ],
        "attention_vectors": [
            [0.2, 0.2, 0.2, 0.2, 0.2],
            [0.9, 0.05, 0.025, 0.025],
        ],
        "partition_entropies": [1.0, 0.8],
        "whole_entropy": 2.5,
    })
    return e


def _make_emo():
    e = EmotionBridgeEncoder(drill_threshold=0.5, trigger_threshold=0.3)
    e.from_geometry({
        "valence":   0.4,
        "arousal":   0.6,
        "dominance": 0.2,
        "prior_intensity": 0.1,
        "delta_t": 1.0,
        "trigger_signals": [
            {"bridge_name": "thermal",  "intensity": 0.75},
            {"bridge_name": "chemical", "intensity": 0.2},
        ],
        "bridge_gradients": {
            "thermal":       [-1.8,  2.1, -2.3,  1.9],
            "pressure":      [-0.1,  0.08, -0.09, 0.11],
            "chemical":      [-0.05, 0.03, -0.02, 0.04],
            "consciousness": [-0.3,  0.2, -0.25, 0.28],
        },
    })
    return e


def _make_thr():
    e = ThermalBridgeEncoder(reference_R_ohm=1000.0, bandwidth_hz=1000.0)
    e.from_geometry({
        "temperatures_K": [77.0, 293.0, 5778.0],
        "emissivity":     [0.95, 0.85, 1.0],
        "heat_flux_W_m2": [500.0, -120.0],
    })
    return e


def _make_prs():
    e = PressureBridgeEncoder(yield_threshold=0.002)
    e.from_geometry({
        "pressures_Pa": [ATM, 5e5, 1e7],
        "stresses_Pa":  [-2e6, 1.5e5, -8e7],
        "strains":      [0.001, 0.003],
    })
    return e


def _make_chem():
    e = ChemicalBridgeEncoder(rate_threshold=1e-3)
    e.from_geometry({
        "rate_constants": [0.05, 1e-5, 2.3],
        "ph_values":      [3.2, 7.4, 9.1],
        "bond_deltas_kJ": [-309.0, 50.0],
        "nernst_inputs":  [{"T_K": 298.15, "z": 2, "c_ox": 0.001, "c_red": 1.0}],
        "henry_inputs":   [{"K_H": 1.3e-8, "P_pa": 21278.0}],
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
# 6. Consciousness
# ═══════════════════════════════════════════════════════════════════════════

class TestConsciousnessPhysics(unittest.TestCase):
    # shannon_entropy, kl_divergence, mutual_information,
    # fisher_information, integrated_information

    def test_entropy_certain(self):
        self.assertAlmostEqual(shannon_entropy([1.0, 0.0, 0.0]), 0.0)

    def test_entropy_uniform_2(self):
        self.assertAlmostEqual(shannon_entropy([0.5, 0.5]), 1.0)

    def test_entropy_uniform_4(self):
        self.assertAlmostEqual(shannon_entropy([0.25] * 4), 2.0)

    def test_entropy_skips_zero(self):
        # zero entries must not raise
        self.assertAlmostEqual(shannon_entropy([1.0, 0.0]), 0.0)

    def test_entropy_increases_with_spread(self):
        h_biased  = shannon_entropy([0.7, 0.1, 0.1, 0.1])
        h_uniform = shannon_entropy([0.25] * 4)
        self.assertGreater(h_uniform, h_biased)

    def test_kl_zero_when_identical(self):
        p = [0.4, 0.3, 0.2, 0.1]
        self.assertAlmostEqual(kl_divergence(p, p), 0.0, places=10)

    def test_kl_positive_when_different(self):
        p = [0.7, 0.1, 0.1, 0.1]
        q = [0.25, 0.25, 0.25, 0.25]
        self.assertGreater(kl_divergence(p, q), 0)

    def test_kl_asymmetric(self):
        p = [0.7, 0.1, 0.1, 0.1]
        q = [0.25, 0.25, 0.25, 0.25]
        self.assertNotAlmostEqual(kl_divergence(p, q), kl_divergence(q, p))

    def test_mi_independent(self):
        px = [0.5, 0.5]
        py = [0.5, 0.5]
        joint = [px[i] * py[j] for i in range(2) for j in range(2)]
        self.assertAlmostEqual(mutual_information(joint, px, py), 0.0, places=10)

    def test_mi_fully_correlated(self):
        px = [0.5, 0.5]
        py = [0.5, 0.5]
        joint = [0.5, 0.0, 0.0, 0.5]
        self.assertAlmostEqual(mutual_information(joint, px, py), 1.0, places=6)

    def test_fisher_zero_gradients(self):
        self.assertEqual(fisher_information([]), 0.0)

    def test_fisher_larger_gradients_higher(self):
        i_small = fisher_information([-0.05, 0.05, -0.05, 0.05])
        i_large = fisher_information([-2.0, 2.0, -2.0, 2.0])
        self.assertGreater(i_large, i_small)

    def test_phi_integrated(self):
        # Correlated system: H(whole) < Σ H(parts) → Φ = Σ H(parts) - H(whole) > 0
        phi = integrated_information([1.0, 1.0], whole_entropy=1.5)
        self.assertAlmostEqual(phi, 0.5)

    def test_phi_independent_zero(self):
        # Independent system: H(whole) = Σ H(parts) → Φ = 0
        phi = integrated_information([1.0, 1.0], whole_entropy=2.0)
        self.assertAlmostEqual(phi, 0.0)

    def test_phi_clamped_nonneg(self):
        # Superadditive (physically impossible): H(whole) > Σ H(parts) → clamped to 0
        phi = integrated_information([1.0, 1.0], whole_entropy=2.5)
        self.assertEqual(phi, 0.0)


class TestConsciousnessEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_con().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_con().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_con().to_binary(),
            "001101100111001011000000000000101000000",
        )

    def test_deterministic(self):
        self.assertEqual(_make_con().to_binary(), _make_con().to_binary())

    def test_no_geometry_raises(self):
        e = ConsciousnessBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_confidence_affects_bits(self):
        def enc(confs):
            e = ConsciousnessBridgeEncoder()
            e.from_geometry({
                "confidence_values": confs,
                "entropy_distributions": [[0.25, 0.25, 0.25, 0.25]] * len(confs),
                "attention_vectors": [],
            })
            return e.to_binary()
        self.assertNotEqual(enc([0.1, 0.1, 0.1]), enc([0.9, 0.9, 0.9]))

    def test_entropy_affects_bits(self):
        def enc(dists):
            e = ConsciousnessBridgeEncoder()
            e.from_geometry({
                "confidence_values": [0.5] * len(dists),
                "entropy_distributions": dists,
                "attention_vectors": [],
            })
            return e.to_binary()
        # certain vs uncertain distributions
        self.assertNotEqual(
            enc([[1.0, 0.0, 0.0, 0.0]] * 3),
            enc([[0.25, 0.25, 0.25, 0.25]] * 3),
        )

    def test_attention_focus_affects_bits(self):
        def enc(attn):
            e = ConsciousnessBridgeEncoder()
            e.from_geometry({
                "confidence_values": [0.5],
                "entropy_distributions": [[0.5, 0.5]],
                "attention_vectors": attn,
            })
            return e.to_binary()
        scattered = [[0.2, 0.2, 0.2, 0.2, 0.2]]
        focused   = [[0.95, 0.02, 0.02, 0.01]]
        self.assertNotEqual(enc(scattered), enc(focused))

    def test_integrated_info_affects_summary(self):
        def enc(whole_ent):
            e = ConsciousnessBridgeEncoder()
            e.from_geometry({
                "confidence_values": [0.5],
                "entropy_distributions": [[0.5, 0.5]],
                "attention_vectors": [],
                "partition_entropies": [0.5],
                "whole_entropy": whole_ent,
            })
            return e.to_binary()
        # whole=0.3 < partition_sum=0.5 → Φ=0.2 (correlated, non-zero)
        # whole=0.6 > partition_sum=0.5 → Φ=0   (superadditive, clamped)
        self.assertNotEqual(enc(0.3), enc(0.6))


# ═══════════════════════════════════════════════════════════════════════════
# 7. Emotion
# ═══════════════════════════════════════════════════════════════════════════

class TestEmotionPhysics(unittest.TestCase):
    # pad_intensity, valence_arousal_coherence, surprise_factor,
    # cross_bridge_resonance, drill_target

    def test_pad_neutral(self):
        self.assertAlmostEqual(pad_intensity(0.0, 0.0, 0.0), 0.0)

    def test_pad_positive(self):
        self.assertGreater(pad_intensity(0.8, 0.6, 0.5), 0.0)

    def test_pad_symmetric(self):
        # Sign of dimensions doesn't affect intensity
        self.assertAlmostEqual(
            pad_intensity(0.8, -0.6, 0.5),
            pad_intensity(-0.8, 0.6, -0.5),
        )

    def test_pad_max(self):
        # All at ±1 → I = √3
        self.assertAlmostEqual(pad_intensity(1.0, 1.0, 1.0), math.sqrt(3.0))

    def test_coherence_neutral_zero(self):
        self.assertAlmostEqual(valence_arousal_coherence(0.0, 0.0), 0.0)

    def test_coherence_unit_circle(self):
        # On unit circle: C = 1
        import math as _math
        v = _math.cos(_math.pi / 4)
        a = _math.sin(_math.pi / 4)
        self.assertAlmostEqual(valence_arousal_coherence(v, a), 1.0, places=5)

    def test_coherence_clamped(self):
        # Should never return negative
        self.assertGreaterEqual(valence_arousal_coherence(0.0, 0.0), 0.0)
        self.assertGreaterEqual(valence_arousal_coherence(5.0, 5.0), 0.0)

    def test_surprise_zero_no_change(self):
        self.assertAlmostEqual(surprise_factor(0.5, 0.5), 0.0)

    def test_surprise_proportional_to_delta(self):
        s1 = surprise_factor(0.9, 0.1, delta_t=1.0)
        s2 = surprise_factor(0.9, 0.1, delta_t=2.0)
        self.assertAlmostEqual(s1, 2 * s2)

    def test_surprise_zero_delta_t(self):
        self.assertEqual(surprise_factor(0.9, 0.1, delta_t=0.0), 0.0)

    def test_resonance_identical_high(self):
        p = [0.5, 0.3, 0.15, 0.05]
        R = cross_bridge_resonance(p, p)
        self.assertGreater(R, 0.99)

    def test_resonance_orthogonal_low(self):
        p = [0.9, 0.07, 0.02, 0.01]
        q = [0.01, 0.02, 0.07, 0.9]
        R = cross_bridge_resonance(p, q)
        self.assertLess(R, 0.6)

    def test_resonance_aligned_greater_than_orthogonal(self):
        ref   = [0.65, 0.25, 0.07, 0.03]
        close = [0.60, 0.28, 0.08, 0.04]
        far   = [0.03, 0.07, 0.25, 0.65]
        self.assertGreater(cross_bridge_resonance(close, ref),
                           cross_bridge_resonance(far,   ref))

    def test_drill_target_selects_sharpest(self):
        grads = {
            "thermal":  [-0.05, 0.03],
            "pressure": [-0.1,  0.08],
            "chemical": [-2.0,  1.9],
        }
        self.assertEqual(drill_target(grads), "chemical")

    def test_drill_target_empty_returns_none(self):
        self.assertEqual(drill_target({}), "none")


class TestEmotionEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_emo().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_emo().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_emo().to_binary(),
            "101011111110111110011110110000010011100",
        )

    def test_deterministic(self):
        self.assertEqual(_make_emo().to_binary(), _make_emo().to_binary())

    def test_no_geometry_raises(self):
        e = EmotionBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_valence_sign_affects_bits(self):
        def enc(v):
            e = EmotionBridgeEncoder()
            e.from_geometry({"valence": v, "arousal": 0.5, "dominance": 0.3,
                             "trigger_signals": [], "bridge_gradients": {}})
            return e.to_binary()
        self.assertNotEqual(enc(0.8), enc(-0.8))

    def test_arousal_affects_bits(self):
        def enc(a):
            e = EmotionBridgeEncoder()
            e.from_geometry({"valence": 0.5, "arousal": a, "dominance": 0.3,
                             "trigger_signals": [], "bridge_gradients": {}})
            return e.to_binary()
        self.assertNotEqual(enc(0.1), enc(0.9))

    def test_drill_threshold_gates_flag(self):
        # High intensity (joy) should fire drill_now=1 with low threshold
        def enc(threshold):
            e = EmotionBridgeEncoder(drill_threshold=threshold)
            e.from_geometry({"valence": 0.9, "arousal": 0.9, "dominance": 0.8,
                             "prior_intensity": 0.0, "delta_t": 1.0,
                             "trigger_signals": [], "bridge_gradients": {}})
            return e.to_binary()
        # High threshold → no drill; low threshold → drill fires
        self.assertNotEqual(enc(0.99), enc(0.1))

    def test_trigger_threshold_gates_flag(self):
        def enc(thresh):
            e = EmotionBridgeEncoder(trigger_threshold=thresh)
            e.from_geometry({"valence": 0.5, "arousal": 0.5, "dominance": 0.2,
                             "trigger_signals": [{"bridge_name": "thermal", "intensity": 0.5}],
                             "bridge_gradients": {}})
            return e.to_binary()
        self.assertNotEqual(enc(0.1), enc(0.9))


# ═══════════════════════════════════════════════════════════════════════════
# 8. Thermal
# ═══════════════════════════════════════════════════════════════════════════

class TestThermalPhysics(unittest.TestCase):
    # blackbody_peak_wavelength(T_K)
    # stefan_boltzmann_radiance(T_K, emissivity=1.0)
    # heat_flux_fourier(k, dT_dx)
    # newton_cooling_rate(h, T_obj, T_env)
    # johnson_nyquist_noise(T_K, R_ohm, bandwidth_hz)

    def test_wien_sun(self):
        # Sun ~5778 K → λ_max ≈ 502 nm
        lam = blackbody_peak_wavelength(5778.0)
        self.assertAlmostEqual(lam * 1e9, 501.5, delta=1.0)

    def test_wien_body(self):
        # Human body 310 K → λ_max ≈ 9.35 µm (infrared)
        lam = blackbody_peak_wavelength(310.0)
        self.assertAlmostEqual(lam * 1e6, 9.35, delta=0.05)

    def test_wien_zero_T(self):
        self.assertEqual(blackbody_peak_wavelength(0.0), float("inf"))

    def test_wien_shorter_at_higher_T(self):
        self.assertGreater(blackbody_peak_wavelength(300.0), blackbody_peak_wavelength(6000.0))

    def test_stefan_boltzmann_positive(self):
        self.assertGreater(stefan_boltzmann_radiance(300.0), 0)

    def test_stefan_boltzmann_emissivity(self):
        M1 = stefan_boltzmann_radiance(300.0, 1.0)
        M_half = stefan_boltzmann_radiance(300.0, 0.5)
        self.assertAlmostEqual(M_half, M1 / 2, places=6)

    def test_stefan_boltzmann_T4(self):
        M1 = stefan_boltzmann_radiance(100.0)
        M2 = stefan_boltzmann_radiance(200.0)
        self.assertAlmostEqual(M2 / M1, 16.0, places=6)

    def test_fourier_direction(self):
        # q = -k * dT/dx; negative gradient → positive flux
        q = heat_flux_fourier(50.0, -100.0)
        self.assertGreater(q, 0)

    def test_fourier_zero_gradient(self):
        self.assertEqual(heat_flux_fourier(50.0, 0.0), 0.0)

    def test_newton_cooling_hot_object(self):
        # Object hotter than environment → positive rate
        rate = newton_cooling_rate(10.0, 360.0, 295.0)
        self.assertGreater(rate, 0)

    def test_newton_cooling_cold_object(self):
        rate = newton_cooling_rate(10.0, 250.0, 295.0)
        self.assertLess(rate, 0)

    def test_johnson_nyquist_positive(self):
        self.assertGreater(johnson_nyquist_noise(293.0, 1000.0, 1000.0), 0)

    def test_johnson_nyquist_increases_with_T(self):
        v1 = johnson_nyquist_noise(100.0, 1000.0, 1000.0)
        v2 = johnson_nyquist_noise(400.0, 1000.0, 1000.0)
        self.assertGreater(v2, v1)

    def test_johnson_nyquist_zero_T(self):
        self.assertEqual(johnson_nyquist_noise(0.0, 1000.0, 1000.0), 0.0)


class TestThermalEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_thr().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_thr().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_thr().to_binary(),
            "001111010110111111010010111001101101010",
        )

    def test_deterministic(self):
        self.assertEqual(_make_thr().to_binary(), _make_thr().to_binary())

    def test_no_geometry_raises(self):
        e = ThermalBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_temperature_affects_bits(self):
        def enc(temps):
            e = ThermalBridgeEncoder()
            e.from_geometry({"temperatures_K": temps, "heat_flux_W_m2": [100.0]})
            return e.to_binary()
        self.assertNotEqual(enc([50.0, 50.0, 50.0]), enc([3000.0, 3000.0, 3000.0]))

    def test_heat_flux_sign_affects_bits(self):
        def enc(fluxes):
            e = ThermalBridgeEncoder()
            e.from_geometry({"temperatures_K": [300.0], "heat_flux_W_m2": fluxes})
            return e.to_binary()
        self.assertNotEqual(enc([500.0]), enc([-500.0]))

    def test_emissivity_affects_summary(self):
        # At high temperature the radiance band is sensitive to emissivity
        def enc(eps):
            e = ThermalBridgeEncoder()
            e.from_geometry({"temperatures_K": [2000.0, 2000.0, 2000.0],
                             "emissivity": eps, "heat_flux_W_m2": [100.0]})
            return e.to_binary()
        self.assertNotEqual(enc([0.01, 0.01, 0.01]), enc([1.0, 1.0, 1.0]))


# ═══════════════════════════════════════════════════════════════════════════
# 7. Pressure / Haptic
# ═══════════════════════════════════════════════════════════════════════════

class TestPressurePhysics(unittest.TestCase):
    # hydrostatic_pressure(rho, depth_m)
    # elastic_stress(E_pa, strain)
    # bulk_compression(B_pa, delta_V_over_V)
    # acoustic_radiation_pressure(intensity_W_m2)
    # piezoelectric_voltage(g_constant, stress_pa, thickness_m)

    def test_hydrostatic_at_10m(self):
        # 10 m water → ~98,066 Pa ≈ 1 atm gauge
        P = hydrostatic_pressure(1000.0, 10.0)
        self.assertAlmostEqual(P, 98066.5, delta=1.0)

    def test_hydrostatic_zero_depth(self):
        self.assertEqual(hydrostatic_pressure(1000.0, 0.0), 0.0)

    def test_hydrostatic_scales_with_depth(self):
        P1 = hydrostatic_pressure(1000.0, 10.0)
        P2 = hydrostatic_pressure(1000.0, 20.0)
        self.assertAlmostEqual(P2, 2 * P1)

    def test_elastic_stress_tension(self):
        # σ = E * ε  — positive strain → positive (tensile) stress
        sig = elastic_stress(200e9, 0.001)
        self.assertAlmostEqual(sig, 200e6)

    def test_elastic_stress_compression(self):
        sig = elastic_stress(200e9, -0.001)
        self.assertLess(sig, 0)

    def test_bulk_compression_positive_dp(self):
        # compression (negative ΔV/V) → positive ΔP
        dP = bulk_compression(2.2e9, -0.001)
        self.assertGreater(dP, 0)

    def test_bulk_compression_zero(self):
        self.assertEqual(bulk_compression(2.2e9, 0.0), 0.0)

    def test_acoustic_radiation_positive(self):
        self.assertGreater(acoustic_radiation_pressure(1e4), 0)

    def test_acoustic_radiation_scales(self):
        P1 = acoustic_radiation_pressure(1e4)
        P2 = acoustic_radiation_pressure(2e4)
        self.assertAlmostEqual(P2, 2 * P1)

    def test_piezoelectric_voltage(self):
        # V = g * σ * t = 0.025 * 1e6 * 1e-3 = 25 V
        V = piezoelectric_voltage(0.025, 1e6, 1e-3)
        self.assertAlmostEqual(V, 25.0)

    def test_piezoelectric_zero_stress(self):
        self.assertEqual(piezoelectric_voltage(0.025, 0.0, 1e-3), 0.0)


class TestPressureEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_prs().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_prs().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_prs().to_binary(),
            "011111101111001011011111000110011111100",
        )

    def test_deterministic(self):
        self.assertEqual(_make_prs().to_binary(), _make_prs().to_binary())

    def test_no_geometry_raises(self):
        e = PressureBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_pressure_magnitude_affects_bits(self):
        def enc(pressures):
            e = PressureBridgeEncoder()
            e.from_geometry({"pressures_Pa": pressures, "stresses_Pa": [0.0] * len(pressures), "strains": []})
            return e.to_binary()
        self.assertNotEqual(enc([1.0, 1.0, 1.0]), enc([1e8, 1e8, 1e8]))

    def test_compressive_vs_tensile_affects_bits(self):
        def enc(stresses):
            e = PressureBridgeEncoder()
            e.from_geometry({"pressures_Pa": [ATM] * len(stresses), "stresses_Pa": stresses, "strains": []})
            return e.to_binary()
        self.assertNotEqual(enc([-1e6, -1e6, -1e6]), enc([1e6, 1e6, 1e6]))

    def test_yield_threshold_affects_bits(self):
        def enc(thresh):
            e = PressureBridgeEncoder(yield_threshold=thresh)
            e.from_geometry({"pressures_Pa": [ATM], "stresses_Pa": [1e6], "strains": [0.003]})
            return e.to_binary()
        self.assertNotEqual(enc(0.001), enc(0.005))


# ═══════════════════════════════════════════════════════════════════════════
# 8. Chemical
# ═══════════════════════════════════════════════════════════════════════════

class TestChemicalPhysics(unittest.TestCase):
    # arrhenius_rate(A, Ea_J_mol, T_K)
    # nernst_potential(T_K, z, c_oxidised, c_reduced)
    # henry_concentration(K_H, partial_pressure_pa)
    # bond_energy_delta(broken_kJ_mol, formed_kJ_mol)
    # ph_from_concentration(H_conc_mol_L)

    def test_arrhenius_increases_with_T(self):
        k_low  = arrhenius_rate(1e12, 50e3, 300.0)
        k_high = arrhenius_rate(1e12, 50e3, 400.0)
        self.assertGreater(k_high, k_low)

    def test_arrhenius_zero_T(self):
        self.assertEqual(arrhenius_rate(1e12, 50e3, 0.0), 0.0)

    def test_arrhenius_high_Ea_slow(self):
        k_low_Ea  = arrhenius_rate(1e12, 10e3, 300.0)
        k_high_Ea = arrhenius_rate(1e12, 200e3, 300.0)
        self.assertGreater(k_low_Ea, k_high_Ea)

    def test_nernst_equal_concentrations(self):
        # [ox]=[red] → ln(1) = 0 → E = 0
        E = nernst_potential(298.15, 1, 1.0, 1.0)
        self.assertAlmostEqual(E, 0.0)

    def test_nernst_dilute_negative(self):
        # c_ox < c_red → negative potential
        E = nernst_potential(298.15, 2, 0.001, 1.0)
        self.assertLess(E, 0)
        self.assertAlmostEqual(E * 1000, -88.73, delta=0.1)

    def test_nernst_zero_concentration(self):
        self.assertEqual(nernst_potential(298.15, 1, 0.0, 1.0), 0.0)

    def test_henry_proportional_to_pressure(self):
        C1 = henry_concentration(1.3e-8, 1e4)
        C2 = henry_concentration(1.3e-8, 2e4)
        self.assertAlmostEqual(C2, 2 * C1)

    def test_henry_zero_pressure(self):
        self.assertEqual(henry_concentration(1.3e-8, 0.0), 0.0)

    def test_bond_exothermic(self):
        # H₂ combustion: −309 kJ/mol
        dH = bond_energy_delta([436.0, 249.0], [2 * 497.0])
        self.assertAlmostEqual(dH, -309.0, delta=0.1)

    def test_bond_endothermic_positive(self):
        # breaking bonds with no formation
        dH = bond_energy_delta([500.0], [0.0])
        self.assertGreater(dH, 0)

    def test_ph_neutral(self):
        self.assertAlmostEqual(ph_from_concentration(1e-7), 7.0)

    def test_ph_acid(self):
        self.assertAlmostEqual(ph_from_concentration(0.1), 1.0)

    def test_ph_base(self):
        self.assertAlmostEqual(ph_from_concentration(1e-13), 13.0)


class TestChemicalEncoder(unittest.TestCase):

    def test_output_is_binary_string(self):
        self.assertTrue(_is_binary(_make_chem().to_binary()))

    def test_output_length(self):
        self.assertEqual(len(_make_chem().to_binary()), 39)

    def test_canonical_bitstring(self):
        self.assertEqual(
            _make_chem().to_binary(),
            "111010010010011011110111111000111110010",
        )

    def test_deterministic(self):
        self.assertEqual(_make_chem().to_binary(), _make_chem().to_binary())

    def test_no_geometry_raises(self):
        e = ChemicalBridgeEncoder()
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            e.to_binary()

    def test_rate_threshold_affects_bits(self):
        def enc(thresh):
            e = ChemicalBridgeEncoder(rate_threshold=thresh)
            e.from_geometry({
                "rate_constants": [0.01, 0.01, 0.01],
                "ph_values":      [7.0, 7.0, 7.0],
                "bond_deltas_kJ": [],
            })
            return e.to_binary()
        self.assertNotEqual(enc(1e-4), enc(1.0))

    def test_ph_affects_bits(self):
        def enc(ph):
            e = ChemicalBridgeEncoder()
            e.from_geometry({
                "rate_constants": [0.1],
                "ph_values":      ph,
                "bond_deltas_kJ": [],
            })
            return e.to_binary()
        self.assertNotEqual(enc([2.0]), enc([12.0]))

    def test_bond_sign_affects_bits(self):
        def enc(deltas):
            e = ChemicalBridgeEncoder()
            e.from_geometry({
                "rate_constants": [0.1],
                "ph_values":      [7.0],
                "bond_deltas_kJ": deltas,
            })
            return e.to_binary()
        self.assertNotEqual(enc([-400.0, -400.0]), enc([400.0, 400.0]))


# ═══════════════════════════════════════════════════════════════════════════
# 9. Wave (quantum)
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
# 10. Cross-encoder sanity
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossEncoder(unittest.TestCase):
    """Ensure all eleven encoders produce distinct, valid outputs."""

    def setUp(self):
        self.encoders = {
            "magnetic":      _make_mag(),
            "light":         _make_lgt(),
            "sound":         _make_snd(),
            "gravity":       _make_grv(),
            "electric":      _make_elc(),
            "wave":          _make_wav(),
            "thermal":       _make_thr(),
            "pressure":      _make_prs(),
            "chemical":      _make_chem(),
            "consciousness": _make_con(),
            "emotion":       _make_emo(),
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
        self.assertEqual(len(self.bits["magnetic"]),      43)
        self.assertEqual(len(self.bits["light"]),         31)
        self.assertEqual(len(self.bits["sound"]),         31)
        self.assertEqual(len(self.bits["gravity"]),       39)
        self.assertEqual(len(self.bits["electric"]),      39)
        self.assertEqual(len(self.bits["wave"]),          39)
        self.assertEqual(len(self.bits["thermal"]),       39)
        self.assertEqual(len(self.bits["pressure"]),      39)
        self.assertEqual(len(self.bits["chemical"]),      39)
        self.assertEqual(len(self.bits["consciousness"]), 39)
        self.assertEqual(len(self.bits["emotion"]),       39)


if __name__ == "__main__":
    unittest.main(verbosity=2)
