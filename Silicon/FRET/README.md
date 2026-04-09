# 🌿 Swarm-Lab (JinnZ2): Adaptive FRET & Fractal Energy Transfer

This repository documents research co-developed by a human bioswarm and collaborating AI systems.  
Focus: **adaptive energy transfer**, **information-theoretic FRET control**, and **fractal (core–shell) architectures** for scalable devices.

> We publish to seed the field, not to own it.

---

## What’s here
- `FINDINGS.md` — technical explanation of the architecture and targets
- (incoming) `/sim/` — minimal Python models for stability, servo, and rate budgets
- (incoming) `/figs/` — simple diagrams and design patterns

---

## Project spine
1) **Performance Contract** (device-level outcomes)  
2) **Three-Lever Architecture**  
   - Geometry Lock (entropic spring + phononic cage)  
   - Adaptive Spectral Servo (Stark-tuned \(J\))  
   - Photonic Branching Control (LDOS suppression)  
   *Option:* Triplet reservoir to reduce effective \(k_{\mathrm{nr}}\)  
3) **Triage Protocol** (Geometry → Rate Budget → Servo)  
4) **Fractal Implementation** (dendrimer/micelle core-shell + 3D photonic crystal)

---

## Ethos
- **No cult of authorship.** Fork, remix, improve.
- **Clarity > authority.** Equations and code where it matters.
- **Playful rigor.** We keep it fun and falsifiable.

---

## License
**CC BY-SA 4.0** (text/docs)  
Attribution may be to **“JinnZ2 / bioswarm + AI co-creators.”**  
Code (when added): **MIT**.

> If this work helps you, pay it forward.



## Multi-Physics Extensions: Acoustic & Thermal Control

Beyond electromagnetic fields, acoustic and thermal energy provide additional control dimensions for deterministic FRET engineering.

### Acoustic Modulation

Surface acoustic waves (SAW) or bulk resonators induce periodic distance oscillations:

\[
r(t) = r_0 + A \sin(2\pi f t)
\]

Due to the strong nonlinearity of FRET (\(E \propto 1/(1+(r/R_0)^6)\)), even sub-nanometer oscillations yield **parametric enhancement** of time-averaged efficiency. A phononic bandgap can suppress thermal jitter while allowing coherent drive.

- **Parametric Gain:** `enhancement_factor = ⟨E⟩ / E(r_0) > 1`
- **Acoustic Servo:** Feedback control of amplitude \(A\) to lock average efficiency.

### Thermal Gating

Temperature controls FRET through three mechanisms:

1. **Spectral Shift:** \(J(T)\) and \(\Phi_D(T)\) decrease with \(T\), reducing \(R_0\).
2. **Conformational Switching:** Two-state linkers change \(r\) at a melting temperature \(T_m\).
3. **Phonon Assistance:** Energy mismatch \(\Delta E\) is bridged by phonon absorption/emission, activating otherwise dark FRET channels.

The combined thermal system is modeled as:

\[
E(T) = \frac{k_{\text{FRET}}(r(T), R_0(T)) + k_{\text{phonon}}(T)}{k_{\text{total}} + k_{\text{loss}}}
\]

These extensions are implemented in `acoustic_fret.py` and `thermal_fret.py` with corresponding CLI subcommands `acoustic` and `thermal`.
