"""
coil_schedule.py  (fabrication/emit/)

Magnetic-IR -> coil winding schedule. Two outputs from one source:

  .txt   bench instructions a human follows by hand
  .csv   pitch table for a stepper-driven bobbin winder

pitch = wire_diameter · pack_factor   (typical 1.05–1.10)

Layer transitions are explicit so the operator (human or
stepper) can pause for re-insulation between layers.

License: CC0. Stdlib only.
"""
import math

from ._common import emit_claim, slugify


def _layer_plan(N, bobbin_length_m, wire_dia_m, pack_factor=1.05):
    pitch = wire_dia_m * pack_factor
    turns_per_layer = max(1, int(bobbin_length_m / pitch))
    layers = []
    remaining = N
    layer_idx = 1
    while remaining > 0:
        t = min(remaining, turns_per_layer)
        layers.append({
            "layer": layer_idx,
            "turns_this_layer": t,
            "direction": "CW" if layer_idx % 2 == 1 else "CCW",
            "pitch_m": pitch,
        })
        remaining -= t
        layer_idx += 1
    return layers, turns_per_layer, pitch


def emit_coil_text(turns, bobbin_length_m, wire_dia_m,
                   wire_gauge="AWG", pack_factor=1.05, name="coil"):
    layers, tpl, pitch = _layer_plan(turns, bobbin_length_m,
                                     wire_dia_m, pack_factor)
    # rough wire-length estimate: π·d_bobbin·N, but we only know
    # the bobbin LENGTH here; leave a placeholder slot for the
    # operator to fill in once the form factor is fixed.
    lines = [
        f"COIL WINDING SCHEDULE -- {name}",
        f"target turns      : {turns}",
        f"bobbin length     : {bobbin_length_m*1000:.2f} mm",
        f"wire diameter     : {wire_dia_m*1e3:.3f} mm  ({wire_gauge})",
        f"pack factor       : {pack_factor}",
        f"pitch             : {pitch*1e3:.3f} mm",
        f"turns per layer   : {tpl}",
        f"layers required   : {len(layers)}",
        "",
        "STEP-BY-STEP:",
    ]
    for L in layers:
        lines.append(
            f"  Layer {L['layer']:>2}: wind {L['turns_this_layer']} "
            f"turns {L['direction']}, pitch {L['pitch_m']*1e3:.3f} mm; "
            f"pause to verify before next layer.")
    return "\n".join(lines) + "\n"


def emit_coil_csv(turns, bobbin_length_m, wire_dia_m,
                  pack_factor=1.05):
    layers, tpl, pitch = _layer_plan(turns, bobbin_length_m,
                                     wire_dia_m, pack_factor)
    rows = ["layer,turn_index,axial_position_m,direction"]
    turn_running = 0
    for L in layers:
        for k in range(L["turns_this_layer"]):
            turn_running += 1
            if L["direction"] == "CW":
                axial = k * pitch
            else:
                axial = bobbin_length_m - k * pitch
            rows.append(f"{L['layer']},{turn_running},"
                        f"{axial:.6f},{L['direction']}")
    return "\n".join(rows) + "\n"


def write_coil_schedule(ir, geo_hash, name="coil",
                        bobbin_length_m=0.05,
                        wire_dia_m=0.5e-3, wire_gauge="AWG24",
                        pack_factor=1.05, out_dir="."):
    N_sq = next((e.parameter for e in ir.elements
                 if e.kind == "store_flow"), None)
    if N_sq is None:
        raise ValueError("Magnetic IR has no store_flow (turns²) "
                         "element.")
    N = int(round(N_sq ** 0.5))
    path_txt = f"{out_dir}/{slugify(name)}_{geo_hash}.txt"
    path_csv = f"{out_dir}/{slugify(name)}_{geo_hash}.csv"
    with open(path_txt, "w") as fp:
        fp.write(emit_coil_text(N, bobbin_length_m, wire_dia_m,
                                wire_gauge, pack_factor, name))
    with open(path_csv, "w") as fp:
        fp.write(emit_coil_csv(N, bobbin_length_m, wire_dia_m,
                               pack_factor))
    emit_claim("coil_schedule", ir, path_txt, geo_hash,
               params={"N_turns": N,
                       "bobbin_length_m": bobbin_length_m,
                       "wire_dia_m": wire_dia_m})
    emit_claim("coil_schedule_csv", ir, path_csv, geo_hash,
               params={"N_turns": N})
    return path_txt, path_csv
