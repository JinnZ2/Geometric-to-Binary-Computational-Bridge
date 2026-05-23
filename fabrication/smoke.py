"""
smoke.py  (fabrication/)

Single runner that exercises every smoke test landed across the
substrate + coupler + emit wedges. Each smoke runs in its OWN
fresh tempdir because most write fixed filenames (sweep.wav,
impedance.csv, ...) that would otherwise collide across smokes
sharing a CWD.

CLI:
  python -m fabrication.smoke          # run all
  python -m fabrication.smoke cross    # only modules with "cross"

Returns exit 0 iff every smoke passed.

License: CC0. Stdlib only.
"""
import os
import runpy
import sys
import tempfile
import time
import traceback


SMOKE_MODULES = [
    # verify-side
    "fabrication.verify.tests.loop_smoke",
    "fabrication.verify.tests.sweep_smoke",
    "fabrication.verify.tests.baseline_smoke",
    "fabrication.verify.tests.multimode_smoke",
    "fabrication.verify.tests.fluidic_smoke",
    "fabrication.verify.tests.pipe_mode_smoke",
    "fabrication.verify.tests.electrical_smoke",
    "fabrication.verify.tests.fluidic_transient_smoke",
    "fabrication.verify.tests.cross_piezo_smoke",
    "fabrication.verify.tests.cross_speaker_smoke",
    "fabrication.verify.tests.thermal_smoke",
    "fabrication.verify.tests.magnetic_smoke",
    "fabrication.verify.tests.cross_heater_smoke",
    "fabrication.verify.tests.cross_transformer_smoke",
    "fabrication.verify.tests.cross_friction_smoke",
    "fabrication.verify.tests.cross_solenoid_smoke",
    # emit-side
    "fabrication.emit.tests.emit_all_smoke",
    # voice + archive
    "fabrication.voice.tests.voice_smoke",
    "fabrication.archive_tests.archive_smoke",
    # structural-repair audit
    "fabrication.passes.tests.structural_repair_smoke",
]


def _run_one(modpath):
    t0 = time.time()
    cwd0 = os.getcwd()
    tmp = tempfile.mkdtemp(prefix="fab_smoke_")
    try:
        os.chdir(tmp)
        runpy.run_module(modpath, run_name="__main__")
        return ("pass", time.time() - t0, None)
    except SystemExit as e:
        ok = (e.code in (0, None))
        return ("pass" if ok else "fail",
                time.time() - t0,
                None if ok else f"sys.exit({e.code})")
    except AssertionError as e:
        return ("fail", time.time() - t0, f"AssertionError: {e}")
    except Exception as e:
        return ("fail", time.time() - t0,
                f"{type(e).__name__}: {e}\n"
                f"{traceback.format_exc()[-400:]}")
    finally:
        os.chdir(cwd0)


def main(argv=None):
    argv = argv or sys.argv[1:]
    only = argv[0] if argv and not argv[0].startswith("-") else None
    targets = [m for m in SMOKE_MODULES if (not only or only in m)]
    print(f"running {len(targets)} smoke modules")
    print("-" * 64)
    n_pass = n_fail = 0
    failures = []
    for mod in targets:
        verdict, dt, err = _run_one(mod)
        mark = "OK  " if verdict == "pass" else "FAIL"
        print(f"  [{mark}]  {mod:54s}  {dt:5.2f}s")
        if err:
            failures.append((mod, err))
        if verdict == "pass":
            n_pass += 1
        else:
            n_fail += 1
    print("-" * 64)
    print(f"  pass: {n_pass}   fail: {n_fail}")
    if failures:
        print("\nfailures:")
        for mod, err in failures:
            print(f"  {mod}")
            for line in err.splitlines():
                print(f"    {line}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
