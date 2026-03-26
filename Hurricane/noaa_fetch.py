"""
Hurricane/noaa_fetch.py — NOAA / NDBC data fetcher
Geometric-to-Binary Computational Bridge
CC-BY-4.0

Fetches real hurricane data from NOAA public endpoints.
No API key required. Zero external dependencies (stdlib urllib only).

Data sources
------------
  NDBC buoy realtime  : https://www.ndbc.noaa.gov/data/realtime2/{ID}.txt
    Columns: WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
    Coverage: 45-day rolling window, hourly observations

  HURDAT2 (best track): https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2023-051124.txt
    6-hourly positions + intensity for all Atlantic storms since 1851

  NHC active storms   : https://www.nhc.noaa.gov/index-at.xml  (RSS)

Usage
-----
  from Hurricane.noaa_fetch import fetch_buoy, fetch_hurdat2_storm, BuoyObs

  # Live buoy near a storm
  obs = fetch_buoy("41049")   # N. Atlantic deep-water buoy
  for o in obs[:24]:           # last 24 hours
      print(o.timestamp, o.wind_speed_ms, o.pressure_hpa, o.sst_c)

  # Historical storm track
  track = fetch_hurdat2_storm("AL092017")  # Irma 2017
  for fix in track:
      print(fix["datetime"], fix["lat"], fix["lon"], fix["wind_kt"])
"""

import urllib.request
import urllib.error
import io
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Key NDBC buoy IDs by region
# ---------------------------------------------------------------------------
BUOYS = {
    # Atlantic / Gulf / Caribbean — common hurricane watch points
    "N_ATLANTIC_DEEP":   "41049",   # 27°N 62°W — prime steering layer
    "N_ATLANTIC_NEAR":   "41047",   # 27°N 72°W
    "N_ATLANTIC_NE":     "41046",   # 23°N 75°W
    "BAHAMAS":           "41048",   # 31°N 69°W
    "GULF_CENTRAL":      "42001",   # 25°N 90°W — deep Gulf
    "GULF_EAST":         "42003",   # 26°N 86°W
    "GULF_NE":           "42040",   # 29°N 88°W
    "CARIBBEAN_E":       "41056",   # 19°N 64°W — Lesser Antilles approach
    "CARIBBEAN_W":       "42058",   # 15°N 75°W
    "CARIBBEAN_NW":      "42057",   # 16°N 82°W
    # Eastern Pacific
    "EPAC_E":            "51001",   # 23°N 162°W
    "EPAC_CENTRAL":      "51004",   # 17°N 152°W
}

# NDBC missing-value sentinels (vary by column)
_MISSING = {99, 999, 9999, 99.0, 999.0, 9999.0}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BuoyObs:
    """
    One hourly observation from an NDBC buoy.

    Physical fields relevant to hurricane coupling analysis:
      wind_dir_deg   : wind direction (deg, meteorological from N)
      wind_speed_ms  : wind speed (m/s)
      gust_ms        : peak 5-second gust (m/s)
      wave_height_m  : significant wave height (m)
      wave_period_s  : dominant wave period (s)
      pressure_hpa   : sea-level pressure (hPa = mbar)
      air_temp_c     : air temperature (°C)
      sst_c          : sea surface temperature (°C)  ← SST for thermal coupling
      dewpoint_c     : dew point (°C)  → relative humidity / moisture
      salinity_proxy : None here (NDBC standard met doesn't report salinity;
                       use ARGO or PIRATA buoys for true salinity)
    """
    timestamp:       datetime
    buoy_id:         str
    lat:             Optional[float] = None
    lon:             Optional[float] = None
    wind_dir_deg:    Optional[float] = None
    wind_speed_ms:   Optional[float] = None
    gust_ms:         Optional[float] = None
    wave_height_m:   Optional[float] = None
    wave_period_s:   Optional[float] = None
    pressure_hpa:    Optional[float] = None
    air_temp_c:      Optional[float] = None
    sst_c:           Optional[float] = None
    dewpoint_c:      Optional[float] = None

    def delta_T(self) -> Optional[float]:
        """SST − air temp (°C). Positive → ocean warmer than air → unstable."""
        if self.sst_c is not None and self.air_temp_c is not None:
            return self.sst_c - self.air_temp_c
        return None

    def relative_humidity(self) -> Optional[float]:
        """
        Magnus approximation of RH from dewpoint and air temp.
        Returns fraction [0, 1].
        """
        if self.air_temp_c is None or self.dewpoint_c is None:
            return None
        # Magnus formula constants
        a, b = 17.625, 243.04  # Alduchov & Eskridge 1996
        gamma_dp  = a * self.dewpoint_c  / (b + self.dewpoint_c)
        gamma_T   = a * self.air_temp_c  / (b + self.air_temp_c)
        rh = math.exp(gamma_dp - gamma_T)
        return min(rh, 1.0)

    def latent_heat_flux_proxy(self) -> Optional[float]:
        """
        Simplified bulk latent heat flux: L_v × C_E × rho_a × U × Δq
        Approximated here as wind_speed × (1 - RH) × 100 (W/m²-ish proxy).
        Not calibrated — use for relative comparison only.
        """
        rh = self.relative_humidity()
        if rh is None or self.wind_speed_ms is None:
            return None
        return self.wind_speed_ms * (1.0 - rh) * 100.0


@dataclass
class HurdatFix:
    """One 6-hourly HURDAT2 position fix."""
    datetime:   datetime
    record:     str           # A=landfall, C=closest approach, etc.
    status:     str           # TD, TS, HU, EX, SS, etc.
    lat:        float
    lon:        float
    wind_kt:    int           # max sustained (1-minute, 10m)
    pressure_mb: Optional[int]
    r34_ne:     Optional[int] = None   # 34-kt wind radii (nm), quadrants
    r34_se:     Optional[int] = None
    r34_sw:     Optional[int] = None
    r34_nw:     Optional[int] = None


# ---------------------------------------------------------------------------
# NDBC fetcher
# ---------------------------------------------------------------------------

def fetch_buoy(buoy_id: str, timeout: int = 10) -> list[BuoyObs]:
    """
    Download the NDBC 45-day standard meteorological file for buoy_id.
    Returns a list of BuoyObs sorted newest-first.

    Raises urllib.error.URLError on network failure.
    Returns [] if the file cannot be parsed.
    """
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{buoy_id}.txt"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise

    return _parse_ndbc_txt(raw, buoy_id)


def load_buoy_file(path: str, buoy_id: str = "local") -> list[BuoyObs]:
    """
    Parse a locally saved NDBC .txt file (same format as fetch_buoy).
    Useful for offline reconstruction when you saved the original data.
    """
    with open(path, "r") as fh:
        raw = fh.read()
    return _parse_ndbc_txt(raw, buoy_id)


def _parse_ndbc_txt(raw: str, buoy_id: str) -> list[BuoyObs]:
    """Parse NDBC standard meteorological text format."""
    lines = raw.splitlines()
    if len(lines) < 3:
        return []

    # Header lines — columns vary slightly between stations
    # Line 0: column names    (#YY  MM DD hh mm WDIR WSPD ...)
    # Line 1: units           (#yr  mo dy hr mn degT m/s ...)
    # Line 2+: data
    header = lines[0].lstrip("#").split()
    col = {name: i for i, name in enumerate(header)}

    obs_list = []
    for line in lines[2:]:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 5:
            continue

        def _get(name, cast=float):
            i = col.get(name)
            if i is None or i >= len(parts):
                return None
            try:
                v = cast(parts[i])
                if v in _MISSING or v == cast(99) or v == cast(9999):
                    return None
                return v
            except (ValueError, TypeError):
                return None

        try:
            yr  = int(parts[col["YY"]])
            mo  = int(parts[col["MM"]])
            dy  = int(parts[col["DD"]])
            hr  = int(parts[col["hh"]])
            mn  = int(parts[col.get("mm", -1)]) if "mm" in col else 0
            dt  = datetime(yr, mo, dy, hr, mn, tzinfo=timezone.utc)
        except (ValueError, KeyError, IndexError):
            continue

        obs = BuoyObs(
            timestamp      = dt,
            buoy_id        = buoy_id,
            wind_dir_deg   = _get("WDIR"),
            wind_speed_ms  = _get("WSPD"),
            gust_ms        = _get("GST"),
            wave_height_m  = _get("WVHT"),
            wave_period_s  = _get("DPD"),
            pressure_hpa   = _get("PRES"),
            air_temp_c     = _get("ATMP"),
            sst_c          = _get("WTMP"),
            dewpoint_c     = _get("DEWP"),
        )

        # Basic sanity filter — atmospheric pressure should be 870–1050 hPa
        if obs.pressure_hpa is not None and not (870 < obs.pressure_hpa < 1060):
            obs.pressure_hpa = None

        obs_list.append(obs)

    # Newest first (file is oldest-first)
    obs_list.reverse()
    return obs_list


# ---------------------------------------------------------------------------
# HURDAT2 fetcher
# ---------------------------------------------------------------------------

_HURDAT2_URL = (
    "https://www.nhc.noaa.gov/data/hurdat/"
    "hurdat2-1851-2023-051124.txt"
)


def fetch_hurdat2_storm(storm_id: str,
                        hurdat2_url: str = _HURDAT2_URL,
                        timeout: int = 30) -> list[HurdatFix]:
    """
    Download HURDAT2 and extract one storm by its ID.

    storm_id : NHC ID string, e.g. "AL092017" (Irma), "AL062022" (Ian)
               Format: {basin}{number}{year}  basin: AL=Atlantic, EP=E.Pacific

    Returns list of HurdatFix, chronological order.
    """
    try:
        with urllib.request.urlopen(hurdat2_url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise

    return _parse_hurdat2_storm(raw, storm_id.upper())


def load_hurdat2_file(path: str, storm_id: str) -> list[HurdatFix]:
    """Parse a locally saved HURDAT2 file for one storm."""
    with open(path, "r") as fh:
        raw = fh.read()
    return _parse_hurdat2_storm(raw, storm_id.upper())


def _parse_hurdat2_storm(raw: str, storm_id: str) -> list[HurdatFix]:
    """Parse HURDAT2 best-track format for a single storm."""
    lines = raw.splitlines()
    in_storm = False
    fixes = []

    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if not parts:
            continue

        # Header line: AL092017, IRMA, 61,
        if len(parts) >= 3 and parts[0] == storm_id:
            in_storm = True
            continue

        if in_storm:
            # Next header line = new storm
            if len(parts) >= 3 and len(parts[0]) == 8 and parts[0][0:2] in ("AL","EP","CP"):
                break

            # Data line: 20170830, 0000, , TD, 16.1N, 26.9W, 30, 1006, ...
            if len(parts) < 8:
                continue
            try:
                dt_str = parts[0] + parts[1].zfill(4)
                dt = datetime.strptime(dt_str, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
                record = parts[2].strip()
                status = parts[3].strip()

                lat_s = parts[4].strip()
                lat = float(lat_s[:-1]) * (-1 if lat_s.endswith("S") else 1)
                lon_s = parts[5].strip()
                lon = float(lon_s[:-1]) * (-1 if lon_s.endswith("W") else 1)

                wind_kt = int(parts[6])
                pres = int(parts[7]) if parts[7].strip() not in ("", "-999") else None

                r34 = [None, None, None, None]
                for qi, offset in enumerate([8, 9, 10, 11]):
                    if offset < len(parts):
                        v = parts[offset].strip()
                        try:
                            vi = int(v)
                            r34[qi] = None if vi <= 0 else vi
                        except ValueError:
                            pass

                fixes.append(HurdatFix(
                    datetime=dt, record=record, status=status,
                    lat=lat, lon=lon,
                    wind_kt=wind_kt, pressure_mb=pres,
                    r34_ne=r34[0], r34_se=r34[1],
                    r34_sw=r34[2], r34_nw=r34[3],
                ))
            except (ValueError, IndexError):
                continue

    return fixes


# ---------------------------------------------------------------------------
# NHC active storm list (RSS)
# ---------------------------------------------------------------------------

def list_active_storms(timeout: int = 10) -> list[dict]:
    """
    Parse the NHC Atlantic/Pacific RSS feeds for active tropical systems.
    Returns list of dicts with keys: id, name, headline, link.
    """
    feeds = [
        "https://www.nhc.noaa.gov/index-at.xml",
        "https://www.nhc.noaa.gov/index-ep.xml",
    ]
    storms = []
    for url in feeds:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            storms.extend(_parse_nhc_rss(raw))
        except urllib.error.URLError:
            pass
    return storms


def _parse_nhc_rss(xml: str) -> list[dict]:
    """Minimal RSS parser — no xml.etree needed for this simple feed."""
    import re
    storms = []
    # Find <item> blocks
    for item in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL):
        title   = re.search(r"<title>(.*?)</title>", item)
        link    = re.search(r"<link>(.*?)</link>", item)
        desc    = re.search(r"<description>(.*?)</description>", item)
        if title and "Advisory" in (title.group(1) + (desc.group(1) if desc else "")):
            storms.append({
                "name":     title.group(1).strip() if title else "",
                "headline": desc.group(1).strip()  if desc  else "",
                "link":     link.group(1).strip()  if link  else "",
            })
    return storms


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("NOAA fetch demo — Hurricane coupling data retrieval")
    print("=" * 60)

    # Try a live buoy read
    buoy_id = BUOYS["N_ATLANTIC_DEEP"]
    print(f"\nFetching NDBC buoy {buoy_id} (N. Atlantic deep water)...")
    try:
        obs = fetch_buoy(buoy_id)
        print(f"  Got {len(obs)} observations")
        if obs:
            o = obs[0]
            print(f"  Latest: {o.timestamp}")
            print(f"  Wind:   {o.wind_speed_ms} m/s from {o.wind_dir_deg}°")
            print(f"  Pres:   {o.pressure_hpa} hPa")
            print(f"  SST:    {o.sst_c}°C  (ΔT = {o.delta_T()}°C)")
            print(f"  RH:     {(o.relative_humidity() or 0)*100:.0f}%")
    except Exception as e:
        print(f"  [offline] {e}")
        print("  Use load_buoy_file('saved_buoy.txt', '41049') for offline analysis")

    # Check active storms
    print("\nChecking NHC active storms...")
    try:
        storms = list_active_storms()
        if storms:
            for s in storms[:3]:
                print(f"  {s['name']}: {s['headline'][:80]}")
        else:
            print("  No active tropical storms at this time.")
    except Exception as e:
        print(f"  [offline] {e}")

    print("\nTo reconstruct coupling analysis:")
    print("  from Hurricane.hurricane_coupling import HurricaneCouplingAnalyzer")
    print("  from Hurricane.noaa_fetch import fetch_buoy, BUOYS")
    print("  obs = fetch_buoy(BUOYS['N_ATLANTIC_DEEP'])")
    print("  hca = HurricaneCouplingAnalyzer(obs)")
    print("  results = hca.full_coupling_report()")
