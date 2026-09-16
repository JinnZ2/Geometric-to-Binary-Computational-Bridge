#!/usr/bin/env python3
"""
coast_divergence.py -- av-mob-1. Coast error vs coast time, from a live feed's own fix history.

    python coast_divergence.py fetch --source opensky --lat 47 --lon 8 --dist 250 --polls 20 --interval 15 --out fixes.jsonl
    python coast_divergence.py measure fixes.jsonl [--max-dt 300] [--bin 15] [--json out.json]
    python coast_divergence.py selftest        # mechanics on synthetic tracks; NOT the measurement

WHAT IS BEING TESTED
    GEV coasts an aircraft between polls with the same arithmetic as
    src/data/motionModel.js: `arcOffsetEnu` integrates a constant-rate turn
    from the last fix at the last speed, with the turn rate estimated from
    the fix history (`estimateTurnRateDps`), and cuts the coast at
    `staleCoastLimitSeconds` (60..300 s). That is a POINT forecast. The
    bridge's Kimchi engine (Kimchi/forward_predict.py) forecasts an INTERVAL
    that widens by a noise term per step, and horizon_sweep.py's headline is
    that false confidence compounds with prediction distance.

    This script measures the one number both sides need and neither has:
    |coasted position - the fix that actually arrived| as a function of coast
    time dt, on real aircraft. The p90 slope in m/s is the noise-per-second an
    honest interval would have to widen at.

WHAT WOULD MAKE av-mob-1 FAIL
    Divergence not growing with dt (then a point coast beats a widening
    interval here and Kimchi's premise does not transfer), or growing faster
    than the shipped noise would widen an interval (then staleCoastLimitSeconds
    is too long). Either is a finding; `measure` prints both slopes.

STATUS
    The harness is shipped and self-tested on synthetic tracks whose generator
    is NOT the coast model (great-circle motion, and a turn that begins after
    the last fix). The measurement on real fixes has NOT been run: OpenSky and
    adsb.lol were unreachable from the session that wrote this. `fetch` is the
    recorder; run it where the feeds are reachable, then `measure`.

FIX RECORD  (one JSON object per line)
    {"id": "4b1805", "t_s": 1726500000.0, "lat": 47.12, "lon": 8.31,
     "speed_mps": 231.4, "track_deg": 84.0, "on_ground": false}

PORT NOTES
    arcOffsetEnu, estimateTurnRateDps and staleCoastLimitSeconds are ported
    line for line. The ENU offset is applied on a flat tangent plane, as
    projectGroundArcLatLon does. Measured against a great-circle generator:
    ~120 m at 300 s and 230 m/s (69 km), i.e. 0.17% of the leg. That is the
    harness floor; GEV's own coast goes ENU -> ECEF and sits below it. Any
    real divergence worth acting on is kilometres. Distances are haversine.
    stdlib only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request

DEG = math.pi / 180
EARTH_R_M = 6_371_000.0
METRES_PER_DEG = 111_320.0
# motionModel.js constants
TURN_MIN_SPEED_MPS = 5.0
TURN_NOISE_FLOOR_DPS = 0.4
TURN_MAX_DPS = 4.0
HISTORY_SAMPLES = 6      # fixes the turn-rate estimate looks back over


# ----------------------------------------------------------------- ports

def norm360(deg: float) -> float:
    return ((deg % 360) + 360) % 360


def norm180(deg: float) -> float:
    n = norm360(deg)
    return n - 360 if n > 180 else n


def arc_offset_enu(speed_mps: float, track_deg: float, turn_rate_dps: float, dt_s: float) -> tuple[float, float, float]:
    """Port of motionModel.arcOffsetEnu. Returns (east_m, north_m, end_course_deg)."""
    tr = track_deg * DEG
    w = (turn_rate_dps or 0.0) * DEG
    if abs(w) < 1e-4:
        return (speed_mps * math.sin(tr) * dt_s, speed_mps * math.cos(tr) * dt_s, norm360(track_deg))
    east = (speed_mps / w) * (math.cos(tr) - math.cos(tr + w * dt_s))
    north = (speed_mps / w) * (math.sin(tr + w * dt_s) - math.sin(tr))
    return (east, north, norm360(track_deg + turn_rate_dps * dt_s))


def estimate_turn_rate_dps(samples: list[dict], noise_floor_dps: float = TURN_NOISE_FLOOR_DPS,
                           max_dps: float = TURN_MAX_DPS, min_speed_mps: float = TURN_MIN_SPEED_MPS) -> float:
    """Port of motionModel.estimateTurnRateDps over [{t_s, track_deg, speed_mps}]."""
    if not samples or len(samples) < 2:
        return 0.0
    total, n = 0.0, 0
    for i in range(1, len(samples)):
        dt = samples[i]["t_s"] - samples[i - 1]["t_s"]
        if dt < 2 or dt > 120:
            continue
        a, b = samples[i - 1].get("track_deg"), samples[i].get("track_deg")
        if a is None or b is None:
            continue
        if min_speed_mps > 0:
            v0, v1 = samples[i - 1].get("speed_mps"), samples[i].get("speed_mps")
            if (v0 is not None and v0 < min_speed_mps) or (v1 is not None and v1 < min_speed_mps):
                continue
        total += norm180(b - a) / dt
        n += 1
    if not n:
        return 0.0
    rate = total / n
    if abs(rate) < noise_floor_dps:
        return 0.0
    return max(-max_dps, min(max_dps, rate))


def stale_coast_limit_s(fix_epoch_s: float, last_contact_s: float, minimum_s: float = 60,
                        grace_s: float = 60, maximum_s: float = 300) -> float:
    """Port of motionModel.staleCoastLimitSeconds."""
    lead = max(0.0, last_contact_s - fix_epoch_s)
    return min(maximum_s, max(minimum_s, lead + grace_s))


def coast(fix: dict, turn_rate_dps: float, dt_s: float) -> tuple[float, float]:
    """Where the coast puts `fix` after dt_s, on the tangent plane at the fix."""
    east, north, _ = arc_offset_enu(fix["speed_mps"], fix["track_deg"], turn_rate_dps, dt_s)
    cos_lat = max(math.cos(fix["lat"] * DEG), 1e-6)
    return (fix["lat"] + north / METRES_PER_DEG, fix["lon"] + east / (METRES_PER_DEG * cos_lat))


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = lat1 * DEG, lat2 * DEG
    dp, dl = (lat2 - lat1) * DEG, (lon2 - lon1) * DEG
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_M * math.asin(min(1.0, math.sqrt(a)))


# ----------------------------------------------------------------- measure

def pairs(fixes: list[dict], max_dt_s: float):
    """Yield (fix_i, history_up_to_i, fix_j, dt) for every later fix within max_dt."""
    by_id: dict[str, list[dict]] = {}
    for f in fixes:
        by_id.setdefault(str(f["id"]), []).append(f)
    for _, track in by_id.items():
        track.sort(key=lambda f: f["t_s"])
        for i, fi in enumerate(track):
            if fi.get("on_ground") or fi.get("speed_mps") is None or fi.get("track_deg") is None:
                continue
            hist = track[max(0, i - HISTORY_SAMPLES + 1): i + 1]
            for fj in track[i + 1:]:
                dt = fj["t_s"] - fi["t_s"]
                if dt <= 0:
                    continue
                if dt > max_dt_s:
                    break
                yield fi, hist, fj, dt


def percentile(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


def measure(fixes: list[dict], max_dt_s: float = 300, bin_s: float = 15) -> dict:
    """Divergence vs coast time. Two coasts per pair: the shipped one (estimated turn) and straight."""
    bins: dict[int, dict[str, list[float]]] = {}
    n_pairs = 0
    for fi, hist, fj, dt in pairs(fixes, max_dt_s):
        w = estimate_turn_rate_dps(hist)
        lat_a, lon_a = coast(fi, w, dt)
        lat_s, lon_s = coast(fi, 0.0, dt)
        b = bins.setdefault(int(dt // bin_s), {"arc": [], "straight": []})
        b["arc"].append(haversine_m(lat_a, lon_a, fj["lat"], fj["lon"]))
        b["straight"].append(haversine_m(lat_s, lon_s, fj["lat"], fj["lon"]))
        n_pairs += 1
    rows = []
    for k in sorted(bins):
        arc, straight = bins[k]["arc"], bins[k]["straight"]
        rows.append({"dt_lo_s": k * bin_s, "dt_hi_s": (k + 1) * bin_s, "n": len(arc),
                     "arc_p50_m": percentile(arc, 0.5), "arc_p90_m": percentile(arc, 0.9),
                     "straight_p50_m": percentile(straight, 0.5), "straight_p90_m": percentile(straight, 0.9)})
    # p90 slope through the origin, m/s: the widening rate an honest interval needs
    num = sum(((r["dt_lo_s"] + r["dt_hi_s"]) / 2) * r["arc_p90_m"] for r in rows if r["n"] >= 5)
    den = sum(((r["dt_lo_s"] + r["dt_hi_s"]) / 2) ** 2 for r in rows if r["n"] >= 5)
    return {"n_fixes": len(fixes), "n_pairs": n_pairs, "max_dt_s": max_dt_s, "bin_s": bin_s,
            "rows": rows, "p90_widening_mps": (num / den) if den else None,
            "measured_on_real_fixes": None}   # the caller says; the script cannot know


def ascii_plot(rows: list[dict], key: str = "arc_p90_m", width: int = 46) -> str:
    """horizon_sweep.ascii_plot's shape: survives a phone screen, no libs."""
    ys = [r[key] for r in rows]
    hi = max(ys) if ys and max(ys) > 0 else 1.0
    out = [f"{key} vs coast time   (# scaled to max={hi:.0f} m)"]
    for r in rows:
        bar = "#" * int(round(width * r[key] / hi))
        out.append(f"  {r['dt_lo_s']:4.0f}-{r['dt_hi_s']:4.0f}s n={r['n']:4d} |{bar} {r[key]:.0f}")
    return "\n".join(out)


# ----------------------------------------------------------------- fetch

def _get_json(url: str, timeout: float = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "coast_divergence/av-mob-1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def poll_opensky(lat: float, lon: float, dist_km: float) -> list[dict]:
    """OpenSky states/all inside a box. Anonymous: ~10 s resolution, 400 credits/day."""
    dlat = dist_km / 111.0
    dlon = dist_km / (111.0 * max(math.cos(lat * DEG), 1e-6))
    url = ("https://opensky-network.org/api/states/all?"
           f"lamin={lat - dlat:.3f}&lomin={lon - dlon:.3f}&lamax={lat + dlat:.3f}&lomax={lon + dlon:.3f}")
    d = _get_json(url)
    out = []
    for s in d.get("states") or []:
        # index: 0 icao24, 3 time_position, 4 last_contact, 5 lon, 6 lat, 8 on_ground, 9 velocity, 10 true_track
        if s[5] is None or s[6] is None or s[3] is None:
            continue
        out.append({"id": s[0], "t_s": float(s[3]), "last_contact_s": float(s[4] or s[3]),
                    "lat": float(s[6]), "lon": float(s[5]), "speed_mps": s[9], "track_deg": s[10],
                    "on_ground": bool(s[8]), "source": "opensky"})
    return out


def poll_adsblol(lat: float, lon: float, dist_km: float) -> list[dict]:
    """adsb.lol v2 point query (ODbL). gs is knots, seen_pos is seconds since the position."""
    nm = dist_km / 1.852
    d = _get_json(f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{min(250, nm):.0f}")
    now_s = float(d.get("now", time.time() * 1000)) / 1000.0
    out = []
    for a in d.get("ac") or []:
        if a.get("lat") is None or a.get("lon") is None:
            continue
        gs = a.get("gs")
        out.append({"id": a.get("hex"), "t_s": now_s - float(a.get("seen_pos") or 0.0), "last_contact_s": now_s,
                    "lat": float(a["lat"]), "lon": float(a["lon"]),
                    "speed_mps": (float(gs) * 0.514444) if gs is not None else None,
                    "track_deg": a.get("track"), "on_ground": a.get("alt_baro") == "ground", "source": "adsblol"})
    return out


def fetch(source: str, lat: float, lon: float, dist_km: float, polls: int, interval_s: float, out_path: str) -> int:
    poll = poll_opensky if source == "opensky" else poll_adsblol
    n = 0
    with open(out_path, "a", encoding="utf-8") as fh:
        for i in range(polls):
            try:
                rows = poll(lat, lon, dist_km)
            except Exception as e:      # noqa: BLE001 - a recorder must keep recording
                print(f"poll {i}: {e}", file=sys.stderr)
                rows = []
            for r in rows:
                fh.write(json.dumps(r) + "\n")
            n += len(rows)
            print(f"poll {i}: {len(rows)} fixes", file=sys.stderr)
            if i + 1 < polls:
                time.sleep(interval_s)
    return n


# ----------------------------------------------------------------- selftest

def _great_circle_track(lat0, lon0, course_deg, speed_mps, t0, n, step_s, turn_dps=0.0, turn_after_s=None):
    """Synthetic generator on the SPHERE, not the tangent plane: a different model from the coast."""
    fixes, lat, lon, crs = [], lat0 * DEG, lon0 * DEG, course_deg
    for k in range(n):
        t = t0 + k * step_s
        fixes.append({"id": "syn", "t_s": t, "lat": lat / DEG, "lon": lon / DEG,
                      "speed_mps": speed_mps, "track_deg": norm360(crs), "on_ground": False})
        turning = turn_after_s is not None and (t - t0) >= turn_after_s
        w = turn_dps if turning else 0.0
        # integrate in 1 s substeps along the sphere
        for _ in range(int(step_s)):
            d = speed_mps / EARTH_R_M
            b = crs * DEG
            lat2 = math.asin(math.sin(lat) * math.cos(d) + math.cos(lat) * math.sin(d) * math.cos(b))
            lon2 = lon + math.atan2(math.sin(b) * math.sin(d) * math.cos(lat),
                                    math.cos(d) - math.sin(lat) * math.sin(lat2))
            lat, lon, crs = lat2, lon2, crs + w
    return fixes


def selftest() -> int:
    ok = True
    straight = _great_circle_track(47.0, 8.0, 84.0, 230.0, 0.0, 21, 15)
    r = measure(straight, max_dt_s=300, bin_s=60)
    worst = max(x["arc_p90_m"] for x in r["rows"])
    print("straight great-circle track, 230 m/s, 15 s fixes: worst p90 over 300 s =", f"{worst:.1f} m")
    ok &= worst < 200.0         # tangent-plane vs sphere over 69 km: the harness floor, ~120 m
    turn = _great_circle_track(47.0, 8.0, 84.0, 230.0, 0.0, 21, 15, turn_dps=2.0, turn_after_s=150)
    r2 = measure(turn, max_dt_s=300, bin_s=60)
    p90 = [x["arc_p90_m"] for x in r2["rows"]]
    print("turn of 2 deg/s beginning at 150 s:", " ".join(f"{v:.0f}" for v in p90), "m (p90 per 60 s bin)")
    print(ascii_plot(r2["rows"]))
    # divergence grows with horizon until the arc wraps (2 deg/s closes a circle in 180 s),
    # so the growth check is on the bins before saturation
    ok &= all(b > a for a, b in zip(p90[:3], p90[1:4]))
    ok &= p90[3] > 1000.0
    print("selftest", "OK" if ok else "FAIL", "(mechanics only; the measurement on real fixes is unrun)")
    return 0 if ok else 1


# ----------------------------------------------------------------- cli

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--source", choices=("opensky", "adsblol"), default="opensky")
    f.add_argument("--lat", type=float, required=True)
    f.add_argument("--lon", type=float, required=True)
    f.add_argument("--dist", type=float, default=250.0, help="km")
    f.add_argument("--polls", type=int, default=20)
    f.add_argument("--interval", type=float, default=15.0)
    f.add_argument("--out", default="fixes.jsonl")
    m = sub.add_parser("measure")
    m.add_argument("path")
    m.add_argument("--max-dt", type=float, default=300.0)
    m.add_argument("--bin", type=float, default=15.0)
    m.add_argument("--json", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv[1:])
    if a.cmd == "fetch":
        n = fetch(a.source, a.lat, a.lon, a.dist, a.polls, a.interval, a.out)
        print(f"{n} fixes appended to {a.out}")
        return 0
    if a.cmd == "measure":
        with open(a.path, encoding="utf-8") as fh:
            fixes = [json.loads(ln) for ln in fh if ln.strip()]
        r = measure(fixes, a.max_dt, a.bin)
        r["measured_on_real_fixes"] = True
        print(f"{r['n_fixes']} fixes, {r['n_pairs']} (fix, later fix) pairs within {a.max_dt:.0f} s")
        print(ascii_plot(r["rows"]))
        if r["p90_widening_mps"] is not None:
            print(f"p90 widening rate: {r['p90_widening_mps']:.2f} m/s  "
                  "(the noise-per-second an honest interval needs; compare Kimchi Coupling.noise)")
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump(r, fh, indent=1)
        return 0
    if a.cmd == "selftest":
        return selftest()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
