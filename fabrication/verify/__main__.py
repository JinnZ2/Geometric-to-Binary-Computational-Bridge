"""
__main__.py  (fabrication/verify/)

CLI entry -- subcommand-style.

  python -m fabrication.verify gen   [out.wav f1 f2 dur sr]
  python -m fabrication.verify tap   in.wav <scope> [flo fhi]
  python -m fabrication.verify sweep sw_wav rs_wav <scope>
                                     [--baseline <id>] [flo fhi]
  python -m fabrication.verify baseline capture <sweep> <recording>
                                     <device_tag> <volume> <geometry_tag>
                                     [f1 f2 duration captured_at]
  python -m fabrication.verify baseline list

Returns exit code 0 / 1 / 2 for pass / drift / fail (verify modes).

License: CC0. Stdlib only.
"""
import sys

from .verifier import verify
from .verifier_sweep import verify_sweep
from .verifier_modes import verify_multimode
from .verifier_cross_piezo import verify_cross_piezo
from .sweep import make_sweep_file
from .baseline import capture_baseline, list_baselines
from .wav_reader import read_wav


def _print_multi(r):
    print("─" * 56)
    print(f"  scope_prefix : {r['scope_prefix']}")
    print(f"  method       : {r['method']}")
    if r.get("baseline_id"):
        print(f"  baseline     : {r['baseline_id']}")
    print(f"  OVERALL      : {r['overall'].upper()}")
    print("  per-mode:")
    for pm in r["per_mode"]:
        if pm.get("measured") is None:
            print(f"    mode {pm['mode_index']}  predicted "
                  f"{pm['predicted']:8.2f} Hz   MISSING   FAIL")
        else:
            print(f"    mode {pm['mode_index']}  "
                  f"pred {pm['predicted']:8.2f}  "
                  f"meas {pm['measured']:8.2f}  "
                  f"({pm['delta_pct']:+5.1f}%)  "
                  f"Q={pm['q_factor']:6.1f}   {pm['verdict'].upper()}")
    if r["unmatched_measured"]:
        print("  unmatched measured peaks:")
        for x in r["unmatched_measured"]:
            print(f"    {x['f']:8.2f} Hz   Q={x['q']:6.1f}   "
                  f"coh={x['coh']:.2f}   ({x['note']})")
    if r["diagnostic"]:
        print("  notes:")
        for n in r["diagnostic"]:
            print(f"    • {n}")
    print("─" * 56)


def _print(r):
    print("─" * 44)
    print(f"  scope     : {r['scope']}")
    print(f"  method    : {r.get('method', 'tap')}")
    if r.get("baseline_id"):
        print(f"  baseline  : {r['baseline_id']}")
    print(f"  predicted : {r['predicted']:8.2f} Hz")
    print(f"  measured  : {r['measured']:8.2f} Hz   "
          f"({100*(r['measured']/r['predicted']-1):+5.1f}%)")
    print(f"  Q-factor  : {r['q_factor']:8.2f}")
    print(f"  tol band  : ±{100*r['tol_frac']:.1f}%")
    print(f"  VERDICT   : {r['verdict'].upper()}")
    for n in r["diagnostic"]:
        print(f"    • {n}")
    print("─" * 44)


def main():
    if len(sys.argv) < 2:
        print("usage: gen | tap | sweep | baseline (capture|list)")
        sys.exit(2)
    cmd = sys.argv[1]

    if cmd == "gen":
        kw = {}
        if len(sys.argv) >= 3: kw["path"]     = sys.argv[2]
        if len(sys.argv) >= 4: kw["f1"]       = float(sys.argv[3])
        if len(sys.argv) >= 5: kw["f2"]       = float(sys.argv[4])
        if len(sys.argv) >= 6: kw["duration"] = float(sys.argv[5])
        if len(sys.argv) >= 7: kw["sr"]       = int(sys.argv[6])
        if len(sys.argv) >= 8: kw["amp"]      = float(sys.argv[7])
        meta = make_sweep_file(**kw)
        print("wrote sweep:", meta)
        sys.exit(0)

    if cmd == "baseline":
        sub = sys.argv[2] if len(sys.argv) > 2 else ""

        if sub == "capture":
            sweep_wav    = sys.argv[3]
            baseline_wav = sys.argv[4]
            device_tag   = sys.argv[5]
            volume       = sys.argv[6]
            geometry_tag = sys.argv[7]

            # read sweep just to pick up the sample rate
            _, sr = read_wav(sweep_wav)
            meta = {
                "device_tag":     device_tag,
                "volume_setting": volume,
                "geometry_tag":   geometry_tag,
                "sample_rate":    sr,
                "sweep_f1":       float(sys.argv[8])  if len(sys.argv) > 8 else 50.0,
                "sweep_f2":       float(sys.argv[9])  if len(sys.argv) > 9 else 2000.0,
                "sweep_duration": float(sys.argv[10]) if len(sys.argv) > 10 else 4.0,
                "captured_at":    sys.argv[11]        if len(sys.argv) > 11 else "",
            }
            bid = capture_baseline(sweep_wav, baseline_wav, meta)
            print("baseline captured:", bid)
            sys.exit(0)

        if sub == "list":
            for b in list_baselines():
                print(b)
            sys.exit(0)

        print("unknown baseline subcommand:", sub)
        sys.exit(2)

    if cmd == "tap":
        if len(sys.argv) < 4:
            print("usage: tap <wav> <scope> [f_lo f_hi]")
            sys.exit(2)
        wav, scope = sys.argv[2], sys.argv[3]
        band = (float(sys.argv[4]), float(sys.argv[5])) \
               if len(sys.argv) >= 6 else (50.0, 2000.0)
        r = verify(wav, scope, search_band=band)
        _print(r)
        sys.exit({"pass": 0, "drift": 1, "fail": 2}[r["verdict"]])

    if cmd == "sweep":
        if len(sys.argv) < 5:
            print("usage: sweep <sweep_wav> <response_wav> <scope> "
                  "[--baseline <id>] [f_lo f_hi]")
            sys.exit(2)
        sw, rs, scope = sys.argv[2], sys.argv[3], sys.argv[4]
        # optional flags
        baseline_id = None
        rest = sys.argv[5:]
        if "--baseline" in rest:
            i = rest.index("--baseline")
            baseline_id = rest[i+1]
            rest = rest[:i] + rest[i+2:]
        band = (float(rest[0]), float(rest[1])) if len(rest) >= 2 \
               else (50.0, 2000.0)
        r = verify_sweep(sw, rs, scope, search_band=band,
                         baseline_id=baseline_id)
        _print(r)
        sys.exit({"pass": 0, "drift": 1, "fail": 2}[r["verdict"]])

    if cmd == "cross_piezo":
        if len(sys.argv) < 3:
            print("usage: cross_piezo <coupler_name> "
                  "--sweep <sweep.wav> "
                  "--acoustic <acoustic_resp.wav> "
                  "[--baseline <id>] --imp <electrical.csv> "
                  "[--band <f_lo> <f_hi>]")
            sys.exit(2)
        name = sys.argv[2]
        opts = list(sys.argv[3:])

        def _take(flag, n=1):
            if flag in opts:
                i = opts.index(flag)
                vals = opts[i+1:i+1+n]
                del opts[i:i+1+n]
                return vals if n > 1 else vals[0]
            return None

        sweep = _take("--sweep")
        aresp = _take("--acoustic")
        bid   = _take("--baseline")
        imp   = _take("--imp")
        band  = _take("--band", 2)
        band = (float(band[0]), float(band[1])) if band else (50.0, 4000.0)
        r = verify_cross_piezo(
            coupler_name=name,
            sweep_wav=sweep,
            acoustic_response_wav=aresp,
            acoustic_baseline_id=bid,
            acoustic_search_band=band,
            electrical_impedance_csv=imp,
        )
        print("─" * 60)
        print(f"  coupler        : {r['coupler']}")
        print(f"  f_acoustic     : {r['f_acoustic']:8.2f} Hz   "
              f"(verdict {r['verdict_acoustic'].upper()})")
        print(f"  f_electrical   : {r['f_electrical']:8.2f} Hz   "
              f"(verdict {r['verdict_electrical'].upper()})")
        print(f"  agreement      : {100*r['agreement_pct']:6.2f}%  "
              f"(expected {100*r['expected_pct']:.2f}% ± "
              f"{100*r['tol_frac']:.1f}%)")
        print(f"  cross verdict  : {r['verdict_cross'].upper()}")
        print(f"  OVERALL        : {r['overall'].upper()}")
        for n in r["diagnostic"]:
            print(f"    • {n}")
        print("─" * 60)
        sys.exit({"pass": 0, "drift": 1, "fail": 2}[r["overall"]])

    if cmd == "multimode":
        if len(sys.argv) < 5:
            print("usage: multimode <sweep_wav> <response_wav> "
                  "<scope_prefix> [--baseline <id>] [f_lo f_hi]")
            sys.exit(2)
        sw, rs, scope_prefix = sys.argv[2], sys.argv[3], sys.argv[4]
        baseline_id = None
        rest = sys.argv[5:]
        if "--baseline" in rest:
            i = rest.index("--baseline")
            baseline_id = rest[i+1]
            rest = rest[:i] + rest[i+2:]
        band = (float(rest[0]), float(rest[1])) if len(rest) >= 2 \
               else (50.0, 4000.0)
        r = verify_multimode(sw, rs, scope_prefix,
                             search_band=band, baseline_id=baseline_id)
        _print_multi(r)
        sys.exit({"pass": 0, "drift": 1, "fail": 2}[r["overall"]])

    print("unknown cmd:", cmd)
    sys.exit(2)


if __name__ == "__main__":
    main()
