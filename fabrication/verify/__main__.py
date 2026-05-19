"""
__main__.py  (fabrication/verify/)

CLI entry -- subcommand-style.

  python -m fabrication.verify tap   in.wav       <scope>  [flo fhi]
  python -m fabrication.verify sweep sweep.wav resp.wav <scope> [flo fhi]
  python -m fabrication.verify gen   [out.wav f1 f2 dur sr amp]

Returns exit code 0 / 1 / 2 for pass / drift / fail so it chains
in shell pipelines.

License: CC0. Stdlib only.
"""
import sys

from .verifier import verify
from .verifier_sweep import verify_sweep
from .sweep import make_sweep_file


def _print(r):
    print("─" * 44)
    print(f"  scope     : {r['scope']}")
    print(f"  method    : {r.get('method', 'tap')}")
    print(f"  predicted : {r['predicted']:8.2f} Hz")
    print(f"  measured  : {r['measured']:8.2f} Hz   "
          f"({100*(r['measured']/r['predicted']-1):+5.1f}%)")
    print(f"  Q-factor  : {r['q_factor']:8.2f}")
    print(f"  tol band  : ±{100*r['tol_frac']:.1f}%")
    if 'bins_trusted' in r:
        print(f"  bins ok   : {r['bins_trusted']}")
    print(f"  VERDICT   : {r['verdict'].upper()}")
    for n in r["diagnostic"]:
        print(f"    • {n}")
    print("─" * 44)


def main():
    if len(sys.argv) < 2:
        print("usage: tap | sweep | gen  (see source)")
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
            print("usage: sweep <sweep_wav> <response_wav> <scope> [f_lo f_hi]")
            sys.exit(2)
        sw, rs, scope = sys.argv[2], sys.argv[3], sys.argv[4]
        band = (float(sys.argv[5]), float(sys.argv[6])) \
               if len(sys.argv) >= 7 else (50.0, 2000.0)
        r = verify_sweep(sw, rs, scope, search_band=band)
        _print(r)
        sys.exit({"pass": 0, "drift": 1, "fail": 2}[r["verdict"]])

    print("unknown cmd:", cmd)
    sys.exit(2)


if __name__ == "__main__":
    main()
