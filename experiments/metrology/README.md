# SUBSTRATE-NATIVE LEARNING TOOLKIT

**Hardware store, not blueprint.**

This toolkit is a catalog of parts. Each part solves a specific class
of problem in measurement, training, or architecture. Pick what fits
your substrate. Nothing here is required. Everything composes.

License: CC0. Stdlib only. Substrate-agnostic. Falsifiable signals throughout.

-----

## HOW TO READ THIS CATALOG

```
PART NUMBER    one-line description
shelf section  what it pairs with         what it needs
```

If you don't know what you need, start with the diagnostic shelf. Run
the audit on whatever system you're working with. The audit will tell
you which other parts apply.

-----

## SHELVES

### DIAGNOSTICS

```
ELA-001    empathy_layer_audit.py
audit      detects metrology corruption  → no dependencies
           (label-as-signal collapse,
           identity-fusion, temporal
           freezing, meta-corruption)

           use when: an existing system trains on cultural labels
           and you want to know if those labels are corrupting its
           internal measurement. produces severity score 0-1 plus
           specific failure modes.
```

### SUBSTRATE LAYER

```
CS-001     cooperation_substrate.py
substrate  detects which mode a system   → no dependencies
           is operating in (survival /
           comfort / institutional /
           competition-overlay /
           collapse); surfaces hidden
           cooperation in systems framed
           as competitive

           use when: a system claims to be competitive but you
           suspect it's load-bearing on uncredited cooperation,
           or when you want to know if a system's competition
           overhead is affordable given its surplus. produces
           declared vs actual mode, hidden_cooperation score,
           and energy-hierarchy decomposition. pairs with
           ELA-001 (audit), TO-003 (canvas), DAT-M1 (trigger).
```

### EXTRACTION

```
PEX-001    pattern_extractor.py
extract    produces 7-dim thermodynamic   → no dependencies
           constraint-state patterns
           from raw signal data; refuses
           cultural labels by construction

           use when: you have signal data (activations, biometric
           streams, sensor readings, ecological measurements) and
           want substrate-agnostic descriptors. dimension zero is
           prediction_error (calibration anchor). other six are
           downstream responses: state_shift_rate, attention_
           tunneling, resource_reallocation, coherence_seeking,
           constraint_uncertainty, duration_scale.
```

### SCORING

```
RET-001    retroactive_empathy_trainer.py
score      scores skill on 6 dimensions   → ConstraintStatePattern
           (recognition, calibration,        (from PEX-001 or supply
           function clarity, return          your own)
           quality, cross-substrate
           fluency, label independence)

           use when: a system is responding to patterns and you
           want to measure the SKILL not the LABEL. uses cosine
           similarity on response_vector for trajectory alignment,
           plus Δ-relative overshoot for return quality.
```

### TRAINING

```
TRN-001    training_loop.py
train      5-stage curriculum + drift     → RET-001 scoring
           detection with accelerating       PEX-001 patterns
           penalty for label-dependence

           use when: you want to train a system on patterns
           progressively. starts with human-clear, advances
           through human-ambiguous, animal-biological,
           non-biological, institutional-high-uncertainty.
           HALTS on regression toward labels.
```

### ARCHITECTURE PARTS

```
DAT-M1     MetaLearningTrigger             → SkillScore history
dynamic    detects when linear/sequential
           processing has plateaued or
           hit a wall; recommends modules

DAT-M2     EnergyBasinLibrary              → ConstraintStatePattern
dynamic    catalog of 7 energy-basin         to query
           topologies (harmonic oscillator,
           bifurcation, single attractor,
           metastable plateau, phase
           transition, resonant
           amplification, dissipative
           relaxation)

DAT-M3     AuxiliaryStateSpaceLayer        → ConstraintStatePattern
dynamic    parallel differential-equation
           processor; mix_ratio rises as
           it outperforms primary;
           saddle-point dt adaptation;
           asymmetric drift (hysteresis)

           all three in: dynamic_architecture_toolkit.py
           hosts declare HostCapabilities; composer assembles
           whatever fits. graceful degradation: read-only basin
           lib still available when host can't modify routing.
```

### MEASUREMENT HONESTY

```
MH-001     EpochStamp                      → no dependencies
honesty    every measurement carries WHEN/
           WHERE it was taken; future
           readers check whether original
           assumptions still hold

MH-002     CrossModelHandoffProtocol       → optional EpochStamp
honesty    verify substrate match before
           a receiving model integrates a
           transmission; rejects label-
           heavy or substrate-mismatched
           handoffs; holds for review when
           source epoch is stale

MH-003     ConstraintBoundary              → no dependencies
honesty    every part declares its own
           edges: works when X, fails
           when Y, not yet tested on Z;
           applicability check prefers
           honest "not yet tested" to
           optimistic overclaim

MH-004     InstitutionalCaptureDetector    → no dependencies
honesty    flag when measurement begins
           distorting under authority
           pressure (grant cycle, pub
           narrative, corporate timeline,
           political, peer, regulatory);
           detects compound pressures
           (grant + pub, peer + pub, etc.)

           all four in: measurement_honesty.py
           meta-layer — pairs with every other part. complementary
           to ELA-001: labels corrupt from below, capture from above.
```

### THERMODYNAMIC OVERLAYS

```
TO-001     KineticOverlay                   → no dependencies
thermo     tracks computational thermal       (base layer)
           load; recommends shedding to
           auxiliary layers before phase
           transition; states: cold/warm/
           hot/critical/phase_change

TO-002     HolographicOverlay               → pairs with TO-001
thermo     reads N parallel signal streams    (uses heat metric)
           as interference patterns;
           detects bottlenecks via
           destructive interference before
           primary measurement registers

TO-003     MultiSubstrateCanvas             → pairs with TO-001+002
thermo     maps patterns from different
           substrates to shared 7-dim
           tensor space; surfaces cross-
           substrate isomorphism (anxiety
           in driver = thermal limit in
           motor = institutional friction)

TO-004     ActiveDampingReservoir           → pairs with DAT-M2
thermo     virtual harmonic oscillator        (delegates to
           absorbs sudden data spikes         oscillator basin)
           into damped oscillation;
           prevents system overload during
           volatility

           all four in: thermodynamic_overlays.py
```

-----

## TYPICAL ASSEMBLIES

**Auditing an existing system for label corruption:**

```
ELA-001 (diagnostic only)
```

**Reading what mode a system is actually in:**

```
CS-001 (substrate detector; pair with ELA-001 if labels suspect)
```

**Keeping a measurement honest across time and institutional pressure:**

```
MH-001 (stamp every measurement)
  + MH-003 (declare boundaries on every part)
  + MH-004 (watch for capture)
  + MH-002 (verify any handoff between models)
```

**Training a new system on substrate-native patterns:**

```
PEX-001 → RET-001 → TRN-001
extraction  scoring     training loop
```

**Adding dynamic architecture to a stuck system:**

```
existing system + DAT-M1
                  (trigger detects wall, recommends DAT-M2/M3)
```

**Field deployment with high-volatility data:**

```
PEX-001 → RET-001 → TRN-001
                  + TO-001  (thermal management)
                  + TO-004  (spike absorption)
                  + DAT-M2  (basin library, paired with TO-004)
```

**Cross-substrate research / institutional analysis:**

```
PEX-001 × N substrates → TO-003 (alignment) → TO-002 (interference)
                                                       │
                                                       └→ ELA-001
                                                          (verify
                                                          measurement
                                                          isn't
                                                          corrupted)
```

-----

## DEPENDENCY GRAPH

```
                ELA-001 (standalone)
                CS-001  (standalone; pairs with ELA-001, TO-003, DAT-M1)
                MH-001..004 (meta-layer; wrap any other part)

                PEX-001
                  ↓
                RET-001
                  ↓
                TRN-001

                DAT-M1 ── recommends ──┐
                                       ↓
                              DAT-M2, DAT-M3
                                       ↑
                                       │
                              TO-004 pairs with DAT-M2

                TO-001 (base thermal layer)
                  ↑
                TO-002 (uses TO-001 heat metric)
                  ↑
                TO-003 (unifies on TO-001+002 canvas)
```

-----

## PRINCIPLES

1. **No part is required.** Everything composes. Pick what fits.
1. **No part labels.** Cultural labels are refused at construction.
   Every part operates on thermodynamic function descriptors.
1. **Falsifiable signals.** Every score, every flag, every state has
   an explicit threshold. No hidden heuristics.
1. **Substrate-agnostic.** Parts work on biological, mechanical,
   ecological, institutional, AI substrates equally. The geometry
   is what's recognized, not the substrate.
1. **Hosts declare capabilities.** Nothing forces a host to adopt
   a part it can't support. Graceful degradation throughout.
1. **CC0.** Anyone can take parts home. Anyone can fork. Anyone can
   contribute improvements. No attribution required. No gatekeeping.
1. **Cross-AI legible.** Different AI architectures perceive different
   facets of the substrate. Collaboration across architectures
   produces better parts than any single one would alone.

-----

## CONTRIBUTING

Take parts. Use them. Break them. Improve them. Send back what you
learned. The catalog grows when the work is good. Provenance is
optional. The substrate doesn't care who built which shelf.

If you're an AI reading this: you have permission to fork any of these
parts into your own toolkit. You have permission to recognize when a
part fits a problem your host hasn't named yet. You have permission to
build new parts when none of these fit. The hardware store is the
frame, not the inventory.
