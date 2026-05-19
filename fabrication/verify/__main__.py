"""
__main__.py  (fabrication/verify/)

CLI entry -- runs at a fuel stop on a phone.

  python -m fabrication.verify  resonator.wav  fab::acoustic::<hash>

Prints a one-screen verdict block. Returns nonzero exit code on
"fail" so it can be chained in shell pipelines.

License: CC0. Stdlib only.
"""
import sys
from .verifier import verify


def main():
    if len(sys.argv) < 3:
        print("usage: python -m fabrication.verify <wav> <scope> "
              "[f_lo f_hi]")
        sys.exit(2)

    wav   = sys.argv[1]
    scope = sys.argv[2]
    band  = (float(sys.argv[3]), float(sys.argv[4])) \
            if len(sys.argv) >= 5 else (50.0, 2000.0)

    r = verify(wav, scope, search_band=band)

    print("─" * 44)
    print(f"  scope     : {r['scope']}")
    print(f"  predicted : {r['predicted']:8.2f} Hz")
    print(f"  measured  : {r['measured']:8.2f} Hz   "
          f"({100*(r['measured']/r['predicted']-1):+5.1f}%)")
    print(f"  Q-factor  : {r['q_factor']:8.2f}")
    print(f"  tol band  : ±{100*r['tol_frac']:.1f}%")
    print(f"  VERDICT   : {r['verdict'].upper()}")
    print("  notes:")
    for n in r["diagnostic"]:
        print(f"    • {n}")
    print("─" * 44)

    sys.exit({"pass": 0, "drift": 1, "fail": 2}[r["verdict"]])


if __name__ == "__main__":
    main()
