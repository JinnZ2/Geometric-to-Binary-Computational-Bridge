#!/usr/bin/env python3
"""
Octahedral State → Magnetic Bridge Pipeline
============================================
Closes the loop between the silicon physics layer and the binary bridge layer:

    physical geometry (ε, d)
        → k_well, T₂
            → 8 octahedral states (Gray-coded eigenvalue triplets)
                → magnetic geometry (field lines, current, resonance)
                    → MagneticBridgeEncoder
                        → bitstring
                            → parse polarity bits
                                → recover eigenvalue triplet → state Gray code

Round-trip guarantee
--------------------
The three N/S field-line polarity bits (bits 0, 8, 16 of the bitstring) directly
encode the eigenvalue triplet (λ₁, λ₂, λ₃).  Parsing them recovers the original
state index exactly.

Physical mapping
----------------
  B_local  = B_GLOBAL + n_active × B_PER_EIG   [T]
              n_active = number of active eigenvalues (= sum of triplet)
  κ_i      = k_well × KAPPA_SCALE × (+1 if λᵢ=1, −0.5 if λᵢ=0)   [m⁻¹]
  I_coil   = I_COIL  (micro-coil at d* from Er site, dl along z)   [A]
  resonance = n_active / 4                                           [0–1]
              (normalized Larmor shift relative to max 3-eigenvalue state)
"""

import sys
import os

# Allow running from repo root or from Silicon/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bridges.magnetic_encoder import (
    MagneticBridgeEncoder,
    magnetic_flux,
    magnetic_pressure,
    larmor_frequency,
    _gray_bits,
    _B_BANDS,
)
from Silicon.octahedral_sim import (
    STATES,
    predict_T2,
    k_well as k_well_fn,
    STRAIN_OPT,
    DIST_OPT,
)

# ── Physical parameters ───────────────────────────────────────────────────────
B_GLOBAL    = 1.0      # T    global Zeeman field
B_PER_EIG   = 0.05     # T    micro-coil contribution per active eigenvalue
I_COIL      = 0.004    # A    ~4 mA for a 10-turn, 1-μm coil at B_local
D_COIL      = 4.8e-10  # m    coil-to-site distance = d*
KAPPA_SCALE = 0.06     # m⁻¹/(eV/Å²)  maps k_well → field-line curvature


# ── Mapping ───────────────────────────────────────────────────────────────────

def state_to_geometry(state_idx: int,
                      strain_pct: float = STRAIN_OPT,
                      dist_ang:   float = DIST_OPT) -> dict:
    """
    Map one octahedral state to a magnetic geometry dict.

    Returns a dict with both simulation metadata and the geometry ready for
    MagneticBridgeEncoder.from_geometry().
    """
    gray, eigs, e_mev = STATES[state_idx]
    n_active = sum(eigs)

    sim    = predict_T2(strain_pct, dist_ang)
    kw     = sim["k_well"]
    T2_ms  = sim["T2_ms"]

    B_local = B_GLOBAL + n_active * B_PER_EIG

    field_lines = [
        {
            "direction":  "N" if eigs[i] else "S",
            "curvature":  kw * KAPPA_SCALE * (1.0 if eigs[i] else -0.5),
            "magnitude":  B_local,
            "area":       1e-20,                    # ~10 nm² lattice cross-section
            "flux_theta": i * 3.141592653589793 / 6,  # phase offset per axis
        }
        for i in range(3)
    ]

    current_elements = [
        {
            "current":  I_COIL,
            "dl":       [0.0, 0.0, 1.0],            # current along z
            "position": [D_COIL, 0.0, 0.0],         # coil at d* on x-axis
        }
    ]

    # Resonance: normalized Larmor shift (0 = min, 1 = fully active triplet)
    resonance_map = [n_active / 4.0]

    return {
        "state_idx":   state_idx,
        "gray_code":   f"{gray:03b}",
        "eigenvalues": eigs,
        "energy_meV":  e_mev,
        "n_active":    n_active,
        "B_local_T":   B_local,
        "k_well":      kw,
        "T2_ms":       T2_ms,
        "geometry": {
            "field_lines":      field_lines,
            "current_elements": current_elements,
            "resonance_map":    resonance_map,
        },
    }


# ── Gray decode helper ────────────────────────────────────────────────────────

def _gray_decode_int(gray_int: int) -> int:
    """Gray-coded integer → binary integer."""
    n, mask = gray_int, gray_int >> 1
    while mask:
        n ^= mask
        mask >>= 1
    return n


# ── Bitstring parser ──────────────────────────────────────────────────────────

def parse_bitstring(bits: str, n_field_lines: int = 3,
                    n_current: int = 1, n_resonance: int = 1) -> dict:
    """
    Parse a MagneticBridgeEncoder bitstring back into labeled fields.

    Layout (per section):
      Field line  (8b): polarity(1) curv_sign(1) curv_mag(3G) B_mag(3G)
      Current     (7b): I_mag(3G)   B_biot(3G)   flow_sign(1)
      Resonance   (4b): constructive(1) res_mag(3G)
      Summary     (7b): flux_sign(1) flux_mag(3G) pressure(3G)
    """
    pos = 0
    out: dict = {"field_lines": [], "current_elements": [],
                 "resonance": [], "summary": None}

    for _ in range(n_field_lines):
        polarity  = int(bits[pos]);     pos += 1
        curv_sign = int(bits[pos]);     pos += 1
        curv_gray = int(bits[pos:pos+3], 2); pos += 3
        b_gray    = int(bits[pos:pos+3], 2); pos += 3
        out["field_lines"].append({
            "polarity":      polarity,           # 1 = N, 0 = S
            "curv_sign":     curv_sign,          # 1 = convex
            "curv_band":     _gray_decode_int(curv_gray),
            "B_band":        _gray_decode_int(b_gray),
        })

    for _ in range(n_current):
        I_gray    = int(bits[pos:pos+3], 2); pos += 3
        B_gray    = int(bits[pos:pos+3], 2); pos += 3
        flow_sign = int(bits[pos]);          pos += 1
        out["current_elements"].append({
            "I_band":        _gray_decode_int(I_gray),
            "B_biot_band":   _gray_decode_int(B_gray),
            "flow_sign":     flow_sign,
        })

    for _ in range(n_resonance):
        constructive = int(bits[pos]);         pos += 1
        res_gray     = int(bits[pos:pos+3], 2); pos += 3
        out["resonance"].append({
            "constructive":  constructive,
            "res_band":      _gray_decode_int(res_gray),
        })

    if pos < len(bits):
        flux_sign = int(bits[pos]);          pos += 1
        flux_gray = int(bits[pos:pos+3], 2); pos += 3
        pres_gray = int(bits[pos:pos+3], 2); pos += 3
        out["summary"] = {
            "flux_sign":  flux_sign,
            "flux_band":  _gray_decode_int(flux_gray),
            "pres_band":  _gray_decode_int(pres_gray),
        }

    return out


# ── Round-trip verification ───────────────────────────────────────────────────

def recover_state_from_bits(parsed: dict) -> tuple:
    """
    Recover eigenvalue triplet and state index from parsed polarity bits.

    The polarity of field lines 0, 1, 2 directly encodes (λ₁, λ₂, λ₃):
      polarity bit = 1 (N) ↔ λᵢ = 1  (active eigenvalue)
      polarity bit = 0 (S) ↔ λᵢ = 0  (inactive)

    Returns (eigenvalues_tuple, state_idx, gray_code_str) or (None, None, None).
    """
    recovered_eigs = tuple(fl["polarity"] for fl in parsed["field_lines"][:3])

    for idx, (gray, eigs, _) in enumerate(STATES):
        if tuple(eigs) == recovered_eigs:
            return recovered_eigs, idx, f"{gray:03b}"

    return None, None, None   # should never happen with valid input


# ── Full pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(strain_pct: float = STRAIN_OPT,
                 dist_ang:   float = DIST_OPT) -> list:
    """
    Run the full pipeline for all 8 octahedral states.

    Returns a list of result dicts, one per state.
    """
    encoder = MagneticBridgeEncoder()
    results = []

    for idx in range(len(STATES)):
        mapping  = state_to_geometry(idx, strain_pct, dist_ang)
        bitstring = encoder.from_geometry(mapping["geometry"]).to_binary()
        parsed    = parse_bitstring(bitstring)
        rec_eigs, rec_idx, rec_gray = recover_state_from_bits(parsed)

        results.append({
            **mapping,
            "bitstring":   bitstring,
            "bit_count":   len(bitstring),
            "parsed":      parsed,
            "recovered_eigenvalues": rec_eigs,
            "recovered_state_idx":   rec_idx,
            "recovered_gray":        rec_gray,
            "round_trip_ok": rec_idx == idx,
        })

    return results


# ── Main report ───────────────────────────────────────────────────────────────

def main():
    W = 70
    print("=" * W)
    print("  Octahedral State → Magnetic Bridge Pipeline".center(W))
    print(f"  ε* = {STRAIN_OPT}%  |  d* = {DIST_OPT} Å  |  T = 300 K".center(W))
    print("=" * W)

    results = run_pipeline()

    # ── 1. State → geometry → bitstring ──────────────────────────────────────
    print("\n[1]  State → Bitstring\n")
    print(f"  {'St':>2}  {'Gray':>4}  {'(λ₁,λ₂,λ₃)':>12}  "
          f"{'B_local (T)':>11}  {'T₂ (ms)':>8}  {'Bits':>4}  Bitstring (first 16b…)")
    print(f"  {'--':>2}  {'----':>4}  {'----------':>12}  "
          f"{'----------':>11}  {'-------':>8}  {'----':>4}  " + "-" * 20)

    for r in results:
        print(f"  {r['state_idx']:>2}  {r['gray_code']:>4}  "
              f"{str(r['eigenvalues']):>12}  "
              f"{r['B_local_T']:>11.3f}  "
              f"{r['T2_ms']:>8.1f}  "
              f"{r['bit_count']:>4}  "
              f"{r['bitstring'][:16]}…")

    # ── 2. Bitstring anatomy for state 5 ─────────────────────────────────────
    r5 = results[5]
    print(f"\n[2]  Bitstring Anatomy — State 5  (Gray {r5['gray_code']},"
          f" eigenvalues {r5['eigenvalues']})\n")
    bits = r5["bitstring"]
    labels = []
    for i in range(3):
        base = i * 8
        labels += [
            (base,     base+1,  f"FL{i} polarity ({bits[base]}={'N' if bits[base]=='1' else 'S'})"),
            (base+1,   base+2,  f"FL{i} curv_sign"),
            (base+2,   base+5,  f"FL{i} curv_mag (Gray {bits[base+2:base+5]})"),
            (base+5,   base+8,  f"FL{i} B_mag    (Gray {bits[base+5:base+8]})"),
        ]
    labels += [
        (24, 27, f"CE0 I_mag    (Gray {bits[24:27]})"),
        (27, 30, f"CE0 B_biot   (Gray {bits[27:30]})"),
        (30, 31, f"CE0 flow_sign"),
        (31, 32, f"RES constructive"),
        (32, 35, f"RES mag     (Gray {bits[32:35]})"),
        (35, 36, f"SUM flux_sign"),
        (36, 39, f"SUM flux_mag (Gray {bits[36:39]})"),
        (39, 42, f"SUM pressure (Gray {bits[39:42]})"),
    ]
    for start, end, label in labels:
        print(f"  bits {start:>2}–{end-1:>2}  [{bits[start:end]}]  {label}")

    # ── 3. Round-trip verification ────────────────────────────────────────────
    print("\n[3]  Round-Trip Verification  (polarity bits → eigenvalues → state)\n")
    print(f"  {'St':>2}  {'Sent':>4}  {'Polarity bits':>14}  "
          f"{'Recovered':>9}  {'Match':>5}")
    print(f"  {'--':>2}  {'----':>4}  {'-------------':>14}  "
          f"{'---------':>9}  {'-----':>5}")
    all_ok = True
    for r in results:
        pol_bits = "".join(str(r["parsed"]["field_lines"][i]["polarity"])
                           for i in range(3))
        match  = "✓" if r["round_trip_ok"] else "✗ FAIL"
        all_ok = all_ok and r["round_trip_ok"]
        print(f"  {r['state_idx']:>2}  {r['gray_code']:>4}  "
              f"  [{pol_bits}] = {r['recovered_eigenvalues']}  "
              f"  → st {r['recovered_state_idx']} {r['recovered_gray']:>4}  "
              f"{match:>5}")
    print(f"\n  All-state round-trip: {'PASS ✓' if all_ok else 'FAIL ✗'}")

    # ── 4. Physics coherence check ────────────────────────────────────────────
    print("\n[4]  Physics Coherence Check\n")
    print(f"  {'St':>2}  {'B_local':>8}  {'B band':>6}  "
          f"{'Res val':>8}  {'Res band':>8}  {'T₂ (ms)':>8}")
    print(f"  {'--':>2}  {'-------':>8}  {'------':>6}  "
          f"{'-------':>8}  {'--------':>8}  {'-------':>8}")
    from bridges.magnetic_encoder import _RES_BANDS
    for r in results:
        B       = r["B_local_T"]
        b_gray  = r["parsed"]["field_lines"][0]["B_band"]
        res_val = r["n_active"] / 4.0
        res_band= r["parsed"]["resonance"][0]["res_band"] if r["parsed"]["resonance"] else -1
        print(f"  {r['state_idx']:>2}  {B:>8.3f}  {b_gray:>6}  "
              f"{res_val:>8.3f}  {res_band:>8}  {r['T2_ms']:>8.1f}")

    # ── 5. End-to-end summary ─────────────────────────────────────────────────
    print("\n[5]  End-to-End Pipeline Summary\n")
    bit_counts = [r["bit_count"] for r in results]
    print(f"  States encoded      : {len(results)}")
    print(f"  Bits per state      : {bit_counts[0]}  "
          f"(3×FL×8 + 1×CE×7 + 1×RES×4 + 1×SUM×7 = {3*8}+{7}+{4}+{7} = {3*8+7+4+7})")
    print(f"  All bitstrings equal length: "
          f"{'yes' if len(set(bit_counts)) == 1 else 'no'}")
    print(f"  Round-trip accuracy : {sum(r['round_trip_ok'] for r in results)}"
          f"/{len(results)} states")
    print(f"  k_well at (ε*, d*)  : {results[0]['k_well']:.2f} eV/Å²")
    print(f"  T₂ at (ε*, d*)      : {results[0]['T2_ms']:.1f} ms")

    print("\n" + "=" * W)
    print("  Pipeline complete.".center(W))
    print("=" * W)


if __name__ == "__main__":
    main()
