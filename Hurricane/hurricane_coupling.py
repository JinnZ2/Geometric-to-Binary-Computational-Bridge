"""
Hurricane/hurricane_coupling.py — Multi-domain coupling analysis
Geometric-to-Binary Computational Bridge
CC-BY-4.0

Reconstructs the physical coupling analysis from the original GI.md
hurricane simulation. Uses physics functions from the existing bridge
encoders directly — no stubs.

Physical domains tracked
------------------------
  thermal    : SST, air temp, ΔT gradient (Fourier heat flux, Stefan-Boltzmann)
  pressure   : central pressure, pressure gradient force (hydrostatic)
  wind       : speed, direction, shear (acoustic frequency / SPL analogy)
  electric   : charge separation proxy from convective intensity (Coulomb)
  chemical   : salt gradient Nernst potential, Arrhenius reaction rates
  wave       : significant wave height, period (wave bridge)
  magnetic   : Coriolis-geomagnetic coupling proxy (Biot-Savart)

Couplings computed (all Pearson r, then phase coherence at Fibonacci scales)
-----------------------------------------------------------------------------
  thermal   ↔ pressure   : SST-driven convection → low pressure (primary mechanism)
  wind      ↔ pressure   : gradient wind balance (Coriolis + pressure gradient)
  electric  ↔ wind       : convective charge separation (lightning proxy)
  chemical  ↔ thermal    : Arrhenius rate shift across ΔT; Nernst salt gradient
  wave      ↔ wind       : wave generation (Phillips/Miles wave growth)
  magnetic  ↔ pressure   : geomagnetic modulation of Rossby wave steering

Usage
-----
  from Hurricane.noaa_fetch import fetch_buoy, BUOYS
  from Hurricane.hurricane_coupling import HurricaneCouplingAnalyzer

  obs = fetch_buoy(BUOYS["N_ATLANTIC_DEEP"])
  hca = HurricaneCouplingAnalyzer(obs)
  report = hca.full_coupling_report()
  print(report)
"""

import math
import sys
from dataclasses import dataclass
from typing import Optional

from Hurricane.noaa_fetch import BuoyObs

# ---------------------------------------------------------------------------
# Bridge encoder physics imports (pure functions, no side effects)
# ---------------------------------------------------------------------------
from bridges.thermal_encoder import (
    heat_flux_fourier, stefan_boltzmann_radiance, blackbody_peak_wavelength
)
from bridges.chemical_encoder import arrhenius_rate, nernst_potential
from bridges.electric_encoder import coulomb_force, electric_field_magnitude
from bridges.pressure_encoder import hydrostatic_pressure

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
SIGMA      = 5.670e-8    # Stefan-Boltzmann (W/m²·K⁴)
K_B        = 1.381e-23   # Boltzmann constant (J/K)
R_GAS      = 8.314       # Gas constant (J/mol·K)
F_FAR      = 96485.0     # Faraday's constant (C/mol)
RHO_SEAWATER = 1025.0    # kg/m³ (typical Atlantic surface)
G          = 9.80665     # m/s²
OMEGA_EARTH = 7.2921e-5  # Earth rotation rate (rad/s)

# Atmospheric electricity constants
FAIR_WEATHER_FIELD = 100.0   # V/m (background atmospheric electric field)
CLOUD_CHARGE_FACTOR = 0.15   # empirical: fraction of wind KE → charge separation

# Salt / ocean chemistry
SEAWATER_SALINITY = 35.0     # g/kg typical Atlantic surface
SALINITY_DEEP     = 36.5     # g/kg typical thermocline
NaCl_MOLAR        = 58.44    # g/mol

# Arrhenius sea spray aerosol oxidation (approximate)
Ea_SPRAY = 50000.0   # J/mol  (SO2 oxidation activation energy)
A_SPRAY  = 1e8       # s⁻¹   (pre-exponential factor)


# ---------------------------------------------------------------------------
# Per-observation physics computation
# ---------------------------------------------------------------------------

@dataclass
class DomainReading:
    """
    Physics-derived scalar for each domain at one time step.
    All values are real physical quantities, not normalized indices.
    """
    timestamp:          object   # datetime

    # Thermal
    heat_flux_wm2:      Optional[float]   # Fourier conduction proxy (W/m²)
    radiance_wm2:       Optional[float]   # Stefan-Boltzmann at SST
    sst_k:              Optional[float]   # SST in Kelvin

    # Pressure
    pressure_pa:        Optional[float]   # surface pressure (Pa)
    pressure_gradient:  Optional[float]   # Δp proxy (Pa) — anomaly from 1013.25 hPa

    # Wind (acoustic analogy: wind speed → SPL)
    wind_spl_db:        Optional[float]   # sound pressure level analog (dB re 1 m/s)
    wind_power_wm2:     Optional[float]   # ½ρU³ kinetic power flux (W/m²)

    # Electric (charge separation proxy)
    electric_field_vm:  Optional[float]   # estimated E-field (V/m)
    charge_proxy_c:     Optional[float]   # estimated column charge (C)

    # Chemical (ocean)
    nernst_mv:          Optional[float]   # salt gradient Nernst potential (mV)
    arrhenius_rate:     Optional[float]   # spray aerosol oxidation rate (s⁻¹)

    # Wave
    wave_energy_jm2:    Optional[float]   # ½ρg H_s² wave energy density (J/m²)

    # Magnetic (Coriolis proxy)
    coriolis_force_ms2: Optional[float]   # 2Ω × U (m/s²) — Coriolis acceleration


def obs_to_domain(obs: BuoyObs) -> DomainReading:
    """
    Convert one BuoyObs into real physical quantities for each bridge domain.
    Uses the physics functions from the bridge encoders directly.
    """
    # --- Thermal ---
    sst_k = (obs.sst_c + 273.15) if obs.sst_c is not None else None
    air_k = (obs.air_temp_c + 273.15) if obs.air_temp_c is not None else None

    # Fourier heat flux proxy: ocean → atmosphere
    # dT/dz ≈ ΔT / 10 m (rough boundary layer depth)
    heat_flux = None
    if sst_k is not None and air_k is not None:
        k_air = 0.026       # thermal conductivity of air (W/m·K)
        heat_flux = heat_flux_fourier(k_air, (sst_k - air_k) / 10.0)

    radiance = stefan_boltzmann_radiance(sst_k) if sst_k else None

    # --- Pressure ---
    pres_pa = (obs.pressure_hpa * 100.0) if obs.pressure_hpa else None
    p_gradient = ((obs.pressure_hpa - 1013.25) * 100.0) if obs.pressure_hpa else None

    # --- Wind (acoustic SPL analog) ---
    # SPL analog: treat wind speed as amplitude, reference = 1 m/s
    wind_spl = None
    wind_power = None
    if obs.wind_speed_ms is not None and obs.wind_speed_ms > 0:
        wind_spl   = 20.0 * math.log10(obs.wind_speed_ms)   # dB re 1 m/s
        rho_air    = 1.225   # kg/m³
        wind_power = 0.5 * rho_air * obs.wind_speed_ms ** 3

    # --- Electric ---
    # Charge separation proxy: convective updrafts create dipoles.
    # Empirical: lightning flash rate ~ U^1.5 for tropical convection.
    # Estimate column charge Q ≈ CLOUD_CHARGE_FACTOR × (wind kinetic energy / e)
    e_field = None
    q_proxy = None
    if obs.wind_speed_ms is not None and obs.wind_speed_ms > 0:
        # Estimate vertical velocity from wind speed (very rough: w ≈ 0.1 U)
        w_vert = 0.1 * obs.wind_speed_ms
        # Charge separation ∝ ½m·w² / elementary charge (proxy only)
        q_proxy = CLOUD_CHARGE_FACTOR * 0.5 * 1.225 * w_vert**2 * 1e6   # nC/m³ proxy
        # Coulomb field at 1 km from charge column
        if q_proxy > 0:
            e_field = electric_field_magnitude(q_proxy * 1e-9, 1000.0)   # V/m

    # --- Chemical (ocean) ---
    # Nernst potential of salt gradient: deep upwelled water vs surface
    # In hurricane wake, cold deep water (salinity 36.5) upwells under surface (35.0)
    # Na⁺ concentration ratio approximates salinity ratio (monovalent, z=1)
    nernst_mv = None
    arr_rate   = None
    if sst_k is not None:
        c_surface = SEAWATER_SALINITY / NaCl_MOLAR    # mol/L (approx)
        c_deep    = SALINITY_DEEP    / NaCl_MOLAR
        nernst_mv = nernst_potential(sst_k, z=1,
                                     c_oxidised=c_deep,
                                     c_reduced=c_surface) * 1000.0  # V → mV
        arr_rate  = arrhenius_rate(A_SPRAY, Ea_SPRAY, sst_k)

    # --- Wave energy density ---
    wave_e = None
    if obs.wave_height_m is not None:
        wave_e = 0.5 * RHO_SEAWATER * G * obs.wave_height_m**2   # J/m²

    # --- Coriolis (magnetic analog) ---
    # 2Ω·U — at latitude ~25°N for Atlantic buoys
    coriolis = None
    if obs.wind_speed_ms is not None:
        lat_rad = math.radians(25.0)   # approximate for Atlantic buoys
        f_c     = 2.0 * OMEGA_EARTH * math.sin(lat_rad)
        coriolis = f_c * obs.wind_speed_ms

    return DomainReading(
        timestamp          = obs.timestamp,
        heat_flux_wm2      = heat_flux,
        radiance_wm2       = radiance,
        sst_k              = sst_k,
        pressure_pa        = pres_pa,
        pressure_gradient  = p_gradient,
        wind_spl_db        = wind_spl,
        wind_power_wm2     = wind_power,
        electric_field_vm  = e_field,
        charge_proxy_c     = q_proxy,
        nernst_mv          = nernst_mv,
        arrhenius_rate     = arr_rate,
        wave_energy_jm2    = wave_e,
        coriolis_force_ms2 = coriolis,
    )


# ---------------------------------------------------------------------------
# Coupling computation
# ---------------------------------------------------------------------------

def _pearson(xs: list, ys: list) -> Optional[float]:
    """Pearson correlation coefficient. Returns None if < 3 valid pairs."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((p[0]-mx)*(p[1]-my) for p in pairs)
    sx  = math.sqrt(sum((p[0]-mx)**2 for p in pairs))
    sy  = math.sqrt(sum((p[1]-my)**2 for p in pairs))
    if sx < 1e-12 or sy < 1e-12:
        return None
    return num / (sx * sy)


def _running_mean(xs: list, window: int) -> list:
    """Simple boxcar smoothing — approximates low-pass at period `window`."""
    result = []
    valid = [x for x in xs if x is not None]
    if not valid:
        return [None] * len(xs)
    fill = sum(valid) / len(valid)
    xs_f = [x if x is not None else fill for x in xs]
    for i in range(len(xs_f)):
        lo = max(0, i - window // 2)
        hi = min(len(xs_f), i + window // 2 + 1)
        result.append(sum(xs_f[lo:hi]) / (hi - lo))
    return result


def fibonacci_coupling(series_a: list, series_b: list) -> dict:
    """
    Compute phase coherence between series_a and series_b at each
    consecutive Fibonacci scale pair (s_n, s_{n+1}).

    Implementation
    --------------
    For each Fibonacci scale s, smooth both series with a window of width s
    (boxcar approximates low-pass). The coupling at scale pair (s_n, s_{n+1})
    is the Pearson correlation between the s_n-smoothed A and s_{n+1}-smoothed B.

    This captures whether A's coarser structure (period s_n) predicts B's
    finer structure (period s_{n+1}) — i.e., whether energy transfers
    between Fibonacci-adjacent timescales in a coordinated way.

    Returns
    -------
    dict mapping (s_n, s_{n+1}) → correlation coefficient (or None)
    """
    fibs = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    results = {}
    for i in range(len(fibs) - 1):
        s_a, s_b = fibs[i], fibs[i+1]
        smooth_a = _running_mean(series_a, s_a)
        smooth_b = _running_mean(series_b, s_b)
        r = _pearson(smooth_a, smooth_b)
        results[(s_a, s_b)] = r
    return results


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

class HurricaneCouplingAnalyzer:
    """
    Multi-domain coupling analysis for hurricane observations.

    Takes a list of BuoyObs (from noaa_fetch.fetch_buoy or load_buoy_file),
    converts each to DomainReading, then computes all pairwise couplings
    and Fibonacci-scale coherence across the time series.
    """

    COUPLING_PAIRS = [
        # (label, field_a_attr, field_b_attr, physical_meaning)
        ("thermal↔pressure",  "heat_flux_wm2",     "pressure_gradient",  "SST-driven convection → pressure drop"),
        ("thermal↔pressure2", "radiance_wm2",       "pressure_gradient",  "Blackbody emission vs pressure anomaly"),
        ("wind↔pressure",     "wind_power_wm2",     "pressure_gradient",  "Wind kinetic energy ↔ pressure gradient (gradient wind)"),
        ("electric↔wind",     "electric_field_vm",  "wind_power_wm2",     "Charge separation ↔ convective intensity"),
        ("chemical↔thermal",  "arrhenius_rate",     "heat_flux_wm2",      "Spray aerosol rxn rate ↔ heat flux (Arrhenius T-dependence)"),
        ("nernst↔thermal",    "nernst_mv",          "heat_flux_wm2",      "Salt gradient potential ↔ heat flux (upwelling coupling)"),
        ("wave↔wind",         "wave_energy_jm2",    "wind_power_wm2",     "Wave energy ↔ wind power (Phillips wave growth)"),
        ("coriolis↔pressure", "coriolis_force_ms2", "pressure_gradient",  "Coriolis acceleration ↔ pressure gradient (geostrophic balance)"),
        ("electric↔pressure", "electric_field_vm",  "pressure_gradient",  "Atmospheric E-field ↔ central pressure (lightning activity)"),
    ]

    def __init__(self, obs: list):
        """
        obs : list of BuoyObs, newest-first (as returned by fetch_buoy)
        """
        # Reverse to chronological order for time-series analysis
        self.obs = list(reversed(obs))
        self.readings: list[DomainReading] = [obs_to_domain(o) for o in self.obs]

    def _series(self, attr: str) -> list:
        return [getattr(r, attr) for r in self.readings]

    def pairwise_correlations(self) -> list[dict]:
        """
        Pearson r for each domain pair across the full time series.
        Returns list of dicts with keys: pair, r, n_valid, meaning.
        """
        results = []
        for label, a_attr, b_attr, meaning in self.COUPLING_PAIRS:
            xs = self._series(a_attr)
            ys = self._series(b_attr)
            pairs_valid = sum(
                1 for x, y in zip(xs, ys)
                if x is not None and y is not None
            )
            r = _pearson(xs, ys)
            results.append({
                "pair":    label,
                "r":       r,
                "n_valid": pairs_valid,
                "meaning": meaning,
            })
        return results

    def fibonacci_analysis(self, pair: tuple[str, str]) -> dict:
        """
        Fibonacci-scale coupling between two domain field attributes.

        pair : (attr_a, attr_b)  — attribute names on DomainReading

        Returns dict of {(s_n, s_{n+1}): r} for all Fibonacci scale pairs.
        """
        a_attr, b_attr = pair
        return fibonacci_coupling(self._series(a_attr), self._series(b_attr))

    def intensification_signal(self) -> dict:
        """
        Compute rapid intensification indicators from the time series.

        RI definition (NHC): +35 kt (18 m/s) wind increase in 24 hours.
        Here approximated as pressure drop proxy: Δp / Δt over 24h windows.

        Returns: {max_24h_drop_hpa, mean_sst_c, thermal_pressure_r,
                  fibonacci_peak_scales, fibonacci_peak_r}
        """
        pressures_hpa = [o.pressure_hpa for o in self.obs]
        sst_vals      = [o.sst_c for o in self.obs]

        # 24-hour pressure drops (index step = 1 hour per obs)
        drops = []
        for i in range(24, len(pressures_hpa)):
            p_now  = pressures_hpa[i]
            p_prev = pressures_hpa[i - 24]
            if p_now is not None and p_prev is not None:
                drops.append(p_prev - p_now)   # positive = deepening

        max_drop = max(drops) if drops else None
        valid_sst = [s for s in sst_vals if s is not None]
        mean_sst  = sum(valid_sst) / len(valid_sst) if valid_sst else None

        # Thermal-pressure Pearson coupling
        tp_r = _pearson(self._series("heat_flux_wm2"),
                        self._series("pressure_gradient"))

        # Fibonacci peak for thermal-pressure
        fib_tp = fibonacci_coupling(
            self._series("heat_flux_wm2"),
            self._series("pressure_gradient"),
        )
        fib_valid = {k: v for k, v in fib_tp.items() if v is not None}
        if fib_valid:
            peak_scale = max(fib_valid, key=lambda k: abs(fib_valid[k]))
            peak_r     = fib_valid[peak_scale]
        else:
            peak_scale = None
            peak_r     = None

        return {
            "max_24h_pressure_drop_hpa": max_drop,
            "mean_sst_c":                mean_sst,
            "thermal_pressure_r":        tp_r,
            "fibonacci_peak_scales":     peak_scale,
            "fibonacci_peak_r":          peak_r,
        }

    def full_coupling_report(self) -> str:
        """
        Human-readable report of all couplings and Fibonacci analysis.
        """
        n = len(self.readings)
        if n == 0:
            return "No observations loaded."

        lines = [
            "=" * 68,
            "  HURRICANE MULTI-DOMAIN COUPLING REPORT",
            f"  {n} observations  |  buoy: {self.obs[0].buoy_id if self.obs else '?'}",
            f"  Period: {self.obs[0].timestamp} → {self.obs[-1].timestamp}" if self.obs else "",
            "=" * 68,
        ]

        # --- Pairwise correlations ---
        lines.append("\nPAIRWISE DOMAIN COUPLINGS  (Pearson r)")
        lines.append("-" * 68)
        pairs = self.pairwise_correlations()
        for p in sorted(pairs, key=lambda x: abs(x["r"] or 0), reverse=True):
            r = p["r"]
            n_v = p["n_valid"]
            if r is None:
                bar = "  [insufficient data]"
            else:
                bar_len = int(abs(r) * 30)
                direction = "+" if r >= 0 else "-"
                bar = f"  {direction}{'|' * bar_len:<30}  r={r:+.3f}  n={n_v}"
            lines.append(f"  {p['pair']:<22}{bar}")
            lines.append(f"    {p['meaning']}")

        # --- Fibonacci analysis for the primary coupling ---
        lines.append("\nFIBONACCI-SCALE COHERENCE  (thermal ↔ pressure)")
        lines.append("-" * 68)
        fib = self.fibonacci_analysis(("heat_flux_wm2", "pressure_gradient"))
        lines.append("  Scale pair (hrs)   r          Interpretation")
        for (s_a, s_b), r in fib.items():
            if r is None:
                interp = "insufficient data"
                r_str  = "   N/A"
            else:
                r_str = f"{r:+.3f}"
                if abs(r) > 0.7:
                    interp = "STRONG — Fibonacci coherence detected"
                elif abs(r) > 0.4:
                    interp = "moderate"
                else:
                    interp = "weak"
            lines.append(f"  ({s_a:2d}, {s_b:2d})           {r_str}      {interp}")

        # --- Fibonacci for wind↔pressure ---
        lines.append("\nFIBONACCI-SCALE COHERENCE  (wind power ↔ pressure)")
        lines.append("-" * 68)
        fib_wp = self.fibonacci_analysis(("wind_power_wm2", "pressure_gradient"))
        for (s_a, s_b), r in fib_wp.items():
            if r is None:
                interp = "insufficient data"
                r_str  = "   N/A"
            else:
                r_str = f"{r:+.3f}"
                interp = "STRONG" if abs(r) > 0.7 else ("moderate" if abs(r) > 0.4 else "weak")
            lines.append(f"  ({s_a:2d}, {s_b:2d})           {r_str}      {interp}")

        # --- Intensification signals ---
        lines.append("\nINTENSIFICATION INDICATORS")
        lines.append("-" * 68)
        ri = self.intensification_signal()
        lines.append(f"  Max 24h pressure drop : {ri['max_24h_pressure_drop_hpa']:.1f} hPa"
                     if ri['max_24h_pressure_drop_hpa'] else "  Max 24h pressure drop : N/A")
        lines.append(f"  Mean SST              : {ri['mean_sst_c']:.1f}°C"
                     if ri['mean_sst_c'] else "  Mean SST              : N/A")
        lines.append(f"  Thermal-pressure r    : {ri['thermal_pressure_r']:+.3f}"
                     if ri['thermal_pressure_r'] else "  Thermal-pressure r    : N/A")
        if ri["fibonacci_peak_scales"]:
            s_a, s_b = ri["fibonacci_peak_scales"]
            lines.append(f"  Peak Fibonacci scales : ({s_a}, {s_b}) hours,  r = {ri['fibonacci_peak_r']:+.3f}")
        else:
            lines.append("  Peak Fibonacci scales : N/A")

        lines.append("=" * 68)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HURDAT2 coupling (historical storm track version)
# ---------------------------------------------------------------------------

def hurdat_coupling(fixes: list) -> dict:
    """
    Compute intensity-change correlations from a HURDAT2 track.

    Takes the list of HurdatFix from noaa_fetch.fetch_hurdat2_storm.
    Returns a summary dict of coupling metrics derived from the track alone
    (no buoy data needed — intensity and pressure are in the best track).

    Note: HURDAT2 lacks SST and chemical fields — for full coupling you
    need to merge with buoy obs or ERA5 reanalysis.
    """
    winds    = [f.wind_kt     for f in fixes]
    pressures= [f.pressure_mb for f in fixes]

    # Wind-pressure coupling (should be strong negative: higher wind = lower pressure)
    r_wp = _pearson(winds, pressures)

    # 24-hour intensification rate (6-hourly fixes → 4 steps per 24h)
    di_24h = []
    for i in range(4, len(winds)):
        if winds[i] is not None and winds[i-4] is not None:
            di_24h.append(winds[i] - winds[i-4])

    max_ri  = max(di_24h) if di_24h else None
    mean_di = sum(di_24h) / len(di_24h) if di_24h else None

    # Count rapid intensification events (≥ 35 kt / 24h)
    ri_events = sum(1 for d in di_24h if d >= 35)

    # Fibonacci coherence on intensity series
    fib_ww = fibonacci_coupling(winds, pressures)
    fib_valid = {k: v for k, v in fib_ww.items() if v is not None}
    peak_scale = max(fib_valid, key=lambda k: abs(fib_valid[k])) if fib_valid else None
    peak_r     = fib_valid[peak_scale] if peak_scale else None

    return {
        "n_fixes":               len(fixes),
        "wind_pressure_r":       r_wp,
        "max_ri_24h_kt":         max_ri,
        "mean_di_24h_kt":        mean_di,
        "ri_events_35kt":        ri_events,
        "fibonacci_peak_scales": peak_scale,
        "fibonacci_peak_r":      peak_r,
        "peak_intensity_kt":     max(w for w in winds if w is not None) if any(w for w in winds if w) else None,
        "min_pressure_mb":       min(p for p in pressures if p is not None) if any(p for p in pressures if p) else None,
    }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Hurricane coupling analysis — reconstruction demo")
    print("=" * 68)

    # Option A: Live buoy data
    print("\nAttempting live NOAA fetch...")
    try:
        from Hurricane.noaa_fetch import fetch_buoy, BUOYS, fetch_hurdat2_storm
        obs = fetch_buoy(BUOYS["N_ATLANTIC_DEEP"])
        if obs:
            print(f"  Got {len(obs)} buoy observations")
            hca = HurricaneCouplingAnalyzer(obs)
            print(hca.full_coupling_report())
        else:
            print("  No observations returned.")
    except Exception as e:
        print(f"  Live fetch failed: {e}")

    # Option B: Historical storm (HURDAT2 — intensity/pressure only)
    print("\nFetching Hurricane Irma (AL092017) from HURDAT2...")
    try:
        fixes = fetch_hurdat2_storm("AL092017")
        if fixes:
            print(f"  {len(fixes)} track fixes, "
                  f"{fixes[0].datetime} → {fixes[-1].datetime}")
            summary = hurdat_coupling(fixes)
            print(f"\n  Wind-pressure coupling r       : {summary['wind_pressure_r']:+.3f}")
            print(f"  Peak intensity                 : {summary['peak_intensity_kt']} kt")
            print(f"  Min pressure                   : {summary['min_pressure_mb']} mb")
            print(f"  Max 24h intensification        : {summary['max_ri_24h_kt']} kt")
            print(f"  RI events (>=35 kt/24h)        : {summary['ri_events_35kt']}")
            if summary["fibonacci_peak_scales"]:
                s_a, s_b = summary["fibonacci_peak_scales"]
                print(f"  Fibonacci peak scales (6h)     : ({s_a}, {s_b}),  r = {summary['fibonacci_peak_r']:+.3f}")
    except Exception as e:
        print(f"  HURDAT2 fetch failed: {e}")

    print("\nFor offline use:")
    print("  from Hurricane.noaa_fetch import load_buoy_file, load_hurdat2_file")
    print("  obs   = load_buoy_file('your_saved_buoy.txt', '41049')")
    print("  fixes = load_hurdat2_file('hurdat2.txt', 'AL092017')")
