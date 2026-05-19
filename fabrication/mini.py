"""
mini.py  (fabrication/)

Menu-driven mini app over the whole fabrication subsystem.
Works in any Python 3.10+ REPL, Termux, Pyto, or a regular
terminal. Stdlib only.

Sections:
  1. SMOKE TEST       run-all health check
  2. LEDGER           inspect claims, measurements, baselines
  3. PREDICT          build an IR + write claims (per substrate)
  4. EMIT             reminder (PREDICT first, then emit_all)
  5. VERIFY           run a verifier against a CSV/WAV
  6. SWEEP TOOLS      generate / baseline phone-mic sweep
  7. ABOUT            version + doc pointers

Run with:
  python -m fabrication.mini

License: CC0. Stdlib only.
"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---- shared lightweight IR scaffolding ---------------------------

@dataclass
class _P:
    domain: str
    flow_name: str
    effort_name: str


@dataclass
class _E:
    kind: str
    geometry: dict
    parameter: float
    port_a: _P
    port_b: "_P" = None


@dataclass
class _I:
    domain: str
    elements: list = field(default_factory=list)
    topology: list = field(default_factory=list)


# ---- menu primitives --------------------------------------------

def _menu(title, options):
    print()
    print("=" * 64)
    print(f"  {title}")
    print("=" * 64)
    for i, (label, _) in enumerate(options, 1):
        print(f"  {i}. {label}")
    print("  0. back")
    print("-" * 64)
    raw = input("  > ").strip()
    if not raw or raw == "0":
        return None
    try:
        idx = int(raw) - 1
        return options[idx][1] if 0 <= idx < len(options) else None
    except (ValueError, IndexError):
        return None


def _prompt(label, default=None):
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"  {label}{suffix}: ").strip()
    return raw if raw else (str(default) if default is not None else "")


# ---- section bodies --------------------------------------------

def _run_smoke():
    from . import smoke
    return smoke.main([])


def _ledger_menu():
    while True:
        choice = _menu("LEDGER", [
            ("summary",                     "summary"),
            ("list all claims",             "list"),
            ("list claims by domain",       "list_domain"),
            ("show one claim by id/scope",  "show"),
            ("measurements for a scope",    "measure"),
            ("list emitted artifacts",      "list_emit"),
            ("list couplers",               "couplers"),
        ])
        if choice is None:
            return
        from . import ledger as L
        if choice == "summary":
            print(L._fmt_summary(L.summary()))
        elif choice == "list":
            for c in L.list_claims():
                print(f"  {c.get('id','?'):16s}  "
                      f"{c.get('scope','?')[:60]:60s}  "
                      f"{c.get('rate_var','?')}")
        elif choice == "list_domain":
            dom = _prompt("domain (acoustic/electrical/...)")
            for c in L.list_claims(f"fab::{dom}::"):
                print(f"  {c.get('id','?'):16s}  "
                      f"{c.get('scope','?')}")
        elif choice == "show":
            q = _prompt("id or scope")
            hit = L.show(q)
            print(json.dumps(hit, indent=2, default=str) if hit
                  else f"not found: {q}")
        elif choice == "measure":
            sp = _prompt("scope prefix")
            for m in L.measurements_for(sp):
                v = m.get("verdict") or m.get("overall") or "?"
                print(f"  {v:6s}  {m.get('method','?'):35s}  "
                      f"{m.get('scope') or m.get('scope_prefix','?')}")
        elif choice == "list_emit":
            for c in L.list_claims("fab::emit::"):
                print(f"  {c.get('format','?'):14s}  "
                      f"{c.get('value','?')}")
        elif choice == "couplers":
            p = Path("coupler_overlay.json")
            ov = json.loads(p.read_text()) if p.exists() else []
            for e in ov:
                k = (e.get("k_eff_squared")
                     or e.get("coupling_factor_k")
                     or "-")
                print(f"  {e.get('kind','?'):25s}  "
                      f"{e.get('name','?'):30s}  k={k}")


def _predict_menu():
    while True:
        choice = _menu("PREDICT (build IR + write claims)", [
            ("Helmholtz cavity (acoustic)",  "helmholtz"),
            ("RLC tank (electrical)",        "rlc"),
            ("mass-spring-damper",           "msd"),
            ("toroid inductor (magnetic)",   "tor_L"),
            ("thermal block + heater",       "therm_heater"),
        ])
        if choice is None:
            return
        try:
            _predict_dispatch(choice)
        except Exception as e:
            print(f"  ERROR: {e}")


def _predict_dispatch(kind):
    if kind == "helmholtz":
        import math
        from .claim_back_modes import (back_claims_multimode,
                                       append_modes_to_ledger)
        V_mL  = float(_prompt("cavity volume (mL)", "250"))
        Ln_mm = float(_prompt("neck length (mm)",  "30"))
        Rn_mm = float(_prompt("neck radius (mm)",  "7.5"))
        V  = V_mL * 1e-6
        Ln = Ln_mm * 1e-3
        An = math.pi * (Rn_mm * 1e-3) ** 2
        port = _P("acoustic", "Q", "P")
        ir = _I("acoustic", [
            _E("store_effort", {"volume": V},
               V / (1.225 * 343 ** 2), port),
            _E("store_flow",   {"length": Ln, "area": An},
               1.225 * Ln / An, port),
        ])
        h = _prompt("geometry hash tag", "HELM_USER")
        claims = back_claims_multimode(ir, h, tol_frac=0.08)
        append_modes_to_ledger(claims)
        print(f"  wrote {len(claims)} claims under fab::acoustic::{h}::")
        return

    if kind == "rlc":
        from .claim_back_electrical import (back_claims_electrical,
                                            append_electrical_claims)
        R = float(_prompt("R (ohm)", "5"))
        L = float(_prompt("L (H)",   "1e-3"))
        C = float(_prompt("C (F)",   "1e-7"))
        port = _P("electrical", "I", "V")
        ir = _I("electrical", [
            _E("dissipate",    {"R": R}, R, port),
            _E("store_flow",   {"L": L}, L, port),
            _E("store_effort", {"C": C}, C, port),
        ])
        h = _prompt("geometry hash tag", "RLC_USER")
        cs = back_claims_electrical(ir, h, tol_frac=0.05)
        append_electrical_claims(cs)
        print(f"  wrote {len(cs)} claims under fab::electrical::{h}::")
        return

    if kind == "msd":
        from .claim_back_mechanical import (back_claims_mechanical,
                                            append_mechanical_claims)
        m_kg  = float(_prompt("mass m (kg)", "0.3"))
        k_Nm  = float(_prompt("spring k (N/m)", "1200"))
        c_Nsm = float(_prompt("damping c (N·s/m)", "0.6"))
        port = _P("mechanical", "v", "F")
        ir = _I("mechanical", [
            _E("store_flow",   {"m": m_kg},  m_kg,        port),
            _E("store_effort", {"k": k_Nm},  1.0 / k_Nm,  port),
            _E("dissipate",    {"c": c_Nsm}, c_Nsm,       port),
        ])
        h = _prompt("geometry hash tag", "MSD_USER")
        cs = back_claims_mechanical(ir, h, tol_frac=0.10)
        append_mechanical_claims(cs)
        print(f"  wrote {len(cs)} claims under fab::mechanical::{h}::")
        return

    if kind == "tor_L":
        from .claim_back_magnetic import (back_claims_magnetic,
                                          append_magnetic_claims)
        from .backends.magnetic import (core_reluctance, MAGNETIC_CORE)
        mat_name = _prompt("core material", "ferrite_3C90")
        mat = MAGNETIC_CORE[mat_name]
        A  = float(_prompt("core cross-section (m²)", "50e-6"))
        le = float(_prompt("mean path length (m)",   "50e-3"))
        N  = int(float(_prompt("turns", "100")))
        R_core = core_reluctance(le, A, mat["mu_r"])
        port = _P("magnetic", "PhiB", "MMF")
        ir = _I("magnetic", [
            _E("dissipate",
               {"length": le, "area": A, "mu_r": mat["mu_r"]},
               R_core, port),
            _E("store_flow", {"turns": N}, N ** 2, port),
        ])
        h = _prompt("geometry hash tag", "TOR_USER")
        cs = back_claims_magnetic(ir, h, tol_frac=0.08)
        append_magnetic_claims(cs)
        print(f"  wrote {len(cs)} claims under fab::magnetic::{h}::")
        return

    if kind == "therm_heater":
        from .claim_back_thermal import (back_claims_thermal,
                                         append_thermal_claims)
        R_th = float(_prompt("R_th (K/W)", "16"))
        C_th = float(_prompt("C_th (J/K)", "75"))
        P_W  = float(_prompt("heater power (W) or 0 for none", "3"))
        port = _P("thermal", "qdot", "dT")
        ir = _I("thermal", [
            _E("dissipate",    {}, R_th, port),
            _E("store_effort", {}, C_th, port),
        ])
        h = _prompt("geometry hash tag", "THERM_USER")
        cs = back_claims_thermal(ir, h,
                                 heat_source_W=(P_W if P_W > 0 else None),
                                 tol_frac=0.10)
        append_thermal_claims(cs)
        print(f"  wrote {len(cs)} claims under fab::thermal::{h}::")
        return


def _emit_menu():
    print("-" * 64)
    print("  EMIT operates on an IR object in memory.")
    print("  Use PREDICT first to build one, OR import emit_all")
    print("  from fabrication.emit and pass your own IR.")
    print("  (Loading an IR back from the ledger is on the roadmap.)")
    print("-" * 64)


def _verify_menu():
    while True:
        choice = _menu("VERIFY", [
            ("acoustic swept-sine (single mode)", "sweep_single"),
            ("acoustic swept-sine (multi-mode)",  "sweep_multi"),
            ("fluidic steady CSV",                "fluid_steady"),
            ("fluidic transient CSV",             "fluid_trans"),
            ("electrical impedance CSV",          "elec_csv"),
            ("mechanical vibration CSV",          "mech_csv"),
            ("thermal heating/cooling CSV",       "therm_csv"),
            ("magnetic LCR CSV",                  "mag_lcr"),
            ("cross_piezo",                       "x_piezo"),
            ("cross_speaker",                     "x_spk"),
            ("cross_heater",                      "x_heat"),
            ("cross_transformer",                 "x_tx"),
            ("cross_friction",                    "x_fric"),
            ("cross_solenoid",                    "x_sol"),
        ])
        if choice is None:
            return
        try:
            _verify_dispatch(choice)
        except Exception as e:
            print(f"  ERROR: {e}")


def _verify_dispatch(k):
    if k == "sweep_single":
        from .verify.verifier_sweep import verify_sweep
        sw  = _prompt("sweep.wav path")
        rs  = _prompt("response.wav path")
        sc  = _prompt("scope (e.g. fab::acoustic::HASH::mode0)")
        bid = _prompt("baseline id (or blank)", "")
        kw = {"baseline_id": bid} if bid else {}
        r = verify_sweep(sw, rs, sc, **kw)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "sweep_multi":
        from .verify.verifier_modes import verify_multimode
        sw = _prompt("sweep.wav path")
        rs = _prompt("response.wav path")
        sp = _prompt("scope prefix (fab::acoustic::HASH)")
        r = verify_multimode(sw, rs, sp)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "fluid_steady":
        from .verify.verifier_fluidic import verify_fluidic
        csv = _prompt("flow.csv path")
        sc  = _prompt("scope (fab::fluidic::HASH)")
        rho = float(_prompt("fluid rho (kg/m³)", "1000"))
        mu  = float(_prompt("fluid mu (Pa·s)",  "1e-3"))
        rad = float(_prompt("channel radius (m)", "1.5e-3"))
        r = verify_fluidic(csv, sc, rho, mu, rad)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "fluid_trans":
        from .verify.verifier_fluidic_transient import verify_fluidic_transient
        csv = _prompt("transient.csv path")
        sc  = _prompt("scope (fab::fluidic::HASH)")
        r = verify_fluidic_transient(csv, sc)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "elec_csv":
        from .verify.verifier_electrical import verify_electrical_csv
        csv = _prompt("impedance.csv path")
        sc  = _prompt("scope (fab::electrical::HASH::LC0)")
        r = verify_electrical_csv(csv, sc)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "mech_csv":
        from .verify.verifier_mechanical import verify_mechanical
        csv = _prompt("vibration.csv path")
        sc  = _prompt("scope (fab::mechanical::HASH::mode0)")
        r = verify_mechanical(csv, sc)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "therm_csv":
        from .verify.verifier_thermal import verify_thermal
        csv  = _prompt("thermal.csv path")
        sc   = _prompt("scope prefix (fab::thermal::HASH)")
        mode = _prompt("mode (heating/cooling)", "heating")
        r = verify_thermal(csv, sc, mode=mode)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "mag_lcr":
        from .verify.verifier_magnetic import verify_magnetic_lcr
        csv = _prompt("LCR.csv path")
        sp  = _prompt("scope prefix (fab::magnetic::HASH)")
        r = verify_magnetic_lcr(csv, sp)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "x_piezo":
        from .verify.verifier_cross_piezo import verify_cross_piezo
        nm  = _prompt("coupler name")
        sw  = _prompt("sweep.wav")
        ar  = _prompt("acoustic_response.wav")
        bid = _prompt("baseline id (or blank)", "")
        imp = _prompt("impedance.csv")
        r = verify_cross_piezo(coupler_name=nm,
                               sweep_wav=sw,
                               acoustic_response_wav=ar,
                               acoustic_baseline_id=(bid or None),
                               electrical_impedance_csv=imp)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "x_spk":
        from .verify.verifier_cross_speaker import verify_cross_speaker
        nm  = _prompt("coupler name")
        sw  = _prompt("sweep.wav")
        ar  = _prompt("acoustic_response.wav")
        bid = _prompt("baseline id (or blank)", "")
        imp = _prompt("impedance.csv")
        vib = _prompt("vibration.csv")
        r = verify_cross_speaker(coupler_name=nm,
                                 sweep_wav=sw,
                                 acoustic_response_wav=ar,
                                 acoustic_baseline_id=(bid or None),
                                 electrical_impedance_csv=imp,
                                 mechanical_vibration_csv=vib)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "x_heat":
        from .verify.verifier_cross_heater import verify_cross_heater
        nm = _prompt("coupler name")
        vi = _prompt("VI.csv path")
        th = _prompt("thermal.csv path")
        r = verify_cross_heater(coupler_name=nm,
                                VI_csv=vi, thermal_csv=th)
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "x_tx":
        from .verify.verifier_cross_transformer import verify_cross_transformer
        nm = _prompt("coupler name")
        v  = _prompt("voltage.csv (or blank)", "")
        c  = _prompt("current.csv (or blank)", "")
        i  = _prompt("inductance.csv (or blank)", "")
        r = verify_cross_transformer(coupler_name=nm,
                                     voltage_csv=(v or None),
                                     current_csv=(c or None),
                                     inductance_csv=(i or None))
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "x_fric":
        from .verify.verifier_cross_friction import verify_cross_friction
        nm = _prompt("coupler name")
        fv = _prompt("Fv.csv (or blank)", "")
        ts = _prompt("therm_steady.csv (or blank)", "")
        dc = _prompt("decay.csv (or blank)", "")
        td = _prompt("therm_decay.csv (or blank)", "")
        r = verify_cross_friction(coupler_name=nm,
                                  force_velocity_csv=(fv or None),
                                  thermal_steady_csv=(ts or None),
                                  decay_csv=(dc or None),
                                  thermal_decay_csv=(td or None))
        print(json.dumps(r, indent=2, default=str))
        return
    if k == "x_sol":
        from .verify.verifier_cross_solenoid import verify_cross_solenoid
        nm = _prompt("coupler name")
        m  = _prompt("motor.csv (or blank)", "")
        g  = _prompt("generator.csv (or blank)", "")
        i  = _prompt("impedance.csv (or blank)", "")
        r = verify_cross_solenoid(coupler_name=nm,
                                  motor_csv=(m or None),
                                  generator_csv=(g or None),
                                  impedance_csv=(i or None))
        print(json.dumps(r, indent=2, default=str))
        return


def _sweep_menu():
    while True:
        choice = _menu("SWEEP TOOLS", [
            ("generate exponential sweep", "gen"),
            ("capture baseline",           "baseline"),
            ("list baselines",             "list_b"),
        ])
        if choice is None:
            return
        try:
            _sweep_dispatch(choice)
        except Exception as e:
            print(f"  ERROR: {e}")


def _sweep_dispatch(k):
    if k == "gen":
        from .verify.sweep import make_sweep_file
        path = _prompt("output path", "sweep.wav")
        f1 = float(_prompt("f1 Hz", "50"))
        f2 = float(_prompt("f2 Hz", "2000"))
        dur = float(_prompt("duration s", "4"))
        m = make_sweep_file(path=path, f1=f1, f2=f2, duration=dur)
        print(f"  wrote {path}: {m}")
        return
    if k == "baseline":
        from .verify.baseline import capture_baseline
        sw  = _prompt("sweep.wav path")
        bl  = _prompt("baseline.wav path")
        dev = _prompt("device tag",     "phone")
        vol = _prompt("volume setting", "50")
        geo = _prompt("geometry tag",   "free_space")
        meta = {"device_tag": dev, "volume_setting": vol,
                "sample_rate": 44100, "geometry_tag": geo,
                "sweep_f1": 50.0, "sweep_f2": 2000.0,
                "sweep_duration": 4.0}
        bid = capture_baseline(sw, bl, meta)
        print(f"  baseline id: {bid}")
        return
    if k == "list_b":
        from .verify.baseline import list_baselines
        for b in list_baselines():
            print(f"  {b}")
        return


def _about():
    print("-" * 64)
    print("  Geometric-to-Binary Computational Bridge")
    print("  fabrication subsystem")
    print()
    print("  6 substrates  6 cross-substrate edges  6 emit formats")
    print("  one ledger, one IR, stdlib only, CC0")
    print("-" * 64)
    print("  see fabrication/README.md + fabrication/ARCHITECTURE.md")
    print("-" * 64)


# ---- main loop --------------------------------------------------

def main():
    while True:
        choice = _menu("BRIDGE -- fabrication mini app", [
            ("run smoke tests (all)",        _run_smoke),
            ("ledger inspector",             _ledger_menu),
            ("predict (build IR + claims)",  _predict_menu),
            ("emit (fab artifacts)",         _emit_menu),
            ("verify (measurement)",         _verify_menu),
            ("sweep tools",                  _sweep_menu),
            ("about",                        _about),
            ("quit",                         "quit"),
        ])
        if choice is None or choice == "quit":
            print("  bye")
            return 0
        if callable(choice):
            choice()


if __name__ == "__main__":
    sys.exit(main() or 0)
