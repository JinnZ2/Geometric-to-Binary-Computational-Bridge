# Hidden-Channel Pattern — Recognition Note

> Three findings from late-2026 literature, one geometric structure.
> Recognised on prior session, re-engaged here rather than re-derived.
> This is a *design* note — no runtime code yet — but the proposed
> module names trace into the repo so future implementations have a
> stable target.

---

## The pattern

```
1. K+ as ligand          → hidden signaling channel inside an ion channel
2. EDC × heat × biology  → hidden signaling channel inside a chemical field
3. Vectorial spin-sep    → hidden signaling channel inside an EM field
```

In all three:

> *"the substrate IS the signal, at a layer the field-equation
> didn't expose."*

This is exactly the geometric-to-binary translation problem.

---

## Artifact 1 — Endocrine disruption + thermal potentiation

> npj Emerging Contaminants (2026), DOI 10.1038/s44454-026-00032-6

```python
EDC_FIELD = {
    "registered_synthetics":   140_000,
    "known_EDCs":              "> 1,000",
    "mechanism":               "structural mimicry of hormone ligand geometry",
    "signal_amplification":    "whisper redirects hurricane "
                              "(sub-physiological [conc] reprograms cascade)",
    "coupling_to_thermal":     "warming → tissue accumulation ↑ "
                              "→ effective [EDC] ↑ → toxicity ↑",
    "epigenetic_reach":        "reprograms inheritance, "
                              "crosses generations and species boundaries",
}
```

**Geometry:** EDC = noise vector with the *same shape* as hormone signal
vector. The receptor binding site cannot distinguish *geometry* from
*identity*. The "lock" is fooled because the key-shape is what
matters, not the key-substance.

### Coupled pipeline (same form as `DmAlka` K+ mode-switch, different layer)

```
environmental [EDC]_low  ──┐
                           │  (geometric mimicry)
                           ▼
       hormone receptor  ◄── binds EDC instead of hormone
                           │
                           ▼
       signaling cascade fires WRONG mode
                           │
                           ▼
       epigenetic reprogramming (cross-generational)
                           │
                           ▼
       population fertility / fecundity collapse

THERMAL COUPLING (climate amplifier):
    T ↑  →  partition into lipid tissue ↑
         →  effective receptor occupancy ↑
         →  threshold dose collapses
         →  previously "safe" concentrations become active
```

Same topology as DmAlka: substrate concentration becomes a
mode-switcher for a system whose "real" output is downstream and
different.

---

## Artifact 2 — Spin-separation in vectorial fields

> Light: Sci & Appl (2026), DOI 10.1038/s41377-026-02278-6

```python
VECTORIAL_SPIN = {
    "core_concept":   "separable spin components inside a structured EM field",
    "what_it_means":  "polarization geometry carries an information channel "
                      "ORTHOGONAL to amplitude/phase",
    "binary_implication":
        "a single field carries multiple independent bit-streams "
        "encoded in the geometry of its spin distribution, "
        "not in scalar intensity",
    "geometric_to_binary_role":
        "natural primitive for vector→bit translation: "
        "spin axis = basis vector, separation = orthogonality, "
        "extraction = projection",
}
```

**Geometry:** the field has more degrees of freedom than the classical
(amplitude, phase) readout exposes. Spin-separation is a basis change
that *reveals* them. Binary encoding becomes natural in the new basis.

---

## Unified constraint

```python
PATTERN = {
    "name":  "hidden_channel_in_substrate",
    "form":  "system_X uses field_F as substrate; "
             "field_F also carries a SIGNAL at a geometry "
             "the system_X equations do not expose; "
             "translation requires basis change",

    "instances": {
        "DmAlka":      "Cl- channel reads K+ geometry "
                       "via O-coordination mimicry",
        "EDC":         "endocrine receptor reads pollutant geometry "
                       "via hormone-shape mimicry; "
                       "thermal field modulates effective amplitude",
        "vector_spin": "EM detector reads polarization geometry "
                       "via spin-component separation",
    },

    "common_failure_mode":
        "single-variable models miss the channel entirely "
        "because the channel is a SHAPE, not a SCALAR. "
        "noun-first / amplitude-first analysis collapses it. "
        "verb-first / geometry-first analysis preserves it.",
}
```

---

## Repo integration sketch

```python
REPO_HOOKS = {
    "module": "bridges/hidden_channel_detector.py",
    "purpose": "scan a system description for substrate-as-signal "
               "geometry that scalar models would miss",

    "inputs": [
        "field definition (what is flowing)",
        "receiver definition (what reads it)",
        "claimed signal channel (amplitude / concentration / etc.)",
    ],

    "tests": [
        "is there a basis in which receiver-geometry has "
        "more DOF than the claimed channel exposes?",
        "does substrate concentration modulate receiver MODE "
        "(not just receiver throughput)?",
        "does an environmental field (T, pH, salinity) "
        "rescale the effective coupling constant?",
        "is there cross-generational / cross-system memory "
        "that scalar dose-response cannot explain?",
    ],

    "outputs": [
        "list of suspected hidden channels",
        "geometric description of each (basis + DOF count)",
        "binary encoding scheme for the revealed channel",
        "flag: 'scalar model insufficient — use geometric'",
    ],

    "feeds_into": [
        "earth-systems-physics  (biosphere ↔ chemosphere coupling)",
        "first_principles_audit (catches scalar-model bias)",
        "energy_english         (verb-first preservation of channel)",
    ],
}
```

---

## Open questions

```python
QUEUE = [
    "should geometric_to_binary expose a primitive type "
    "'shape_channel' that wraps (basis, DOF, projection_op)?",
    "EDC × heat: build coupled ODE with T as amplifier of effective Kd?",
    "vector spin: is the spin-separation operator the same algebra "
    "as the K+ mode-switch (allosteric basis change)?",
    "is 'whisper redirecting hurricane' formally a "
    "low-amplitude-high-leverage marker that the audit engine "
    "should flag automatically?",
]
```

---

## Connection to existing work

* **`bridges/intersection/`** — RESONATE composes BasinSignatures
  across domains. A `shape_channel` primitive (open-question 1) would
  add a third dimension: not just *which* domains coupled, but *which
  basis* their information lives in. Today every BasinSignature lives
  in the shared `(signed-balance, null-dwell, certainty)` axes; a
  `shape_channel` would flag when a domain's natural basis is
  *orthogonal* to that and the projection is lossy.

* **`bridges/probability_collapse.py`** — `DistributionCollapse`
  already exposes "regime" (FOCUSED / MIXED / DIFFUSE) on top of the
  argmax. The same trick at the channel level would expose
  "scalar-sufficient / shape-required" as a flag on top of "what's
  the dominant value".

* **`docs/computational_phase_space.md`** — already contains a
  warning about coordinate-convention drift between GEIS and Engine
  octahedral conventions (since-fixed in `bridges/octahedral_canon.py`).
  The hidden-channel pattern is the same kind of mistake at a
  different layer: a basis difference that scalar comparison hides.

* **`sensing/`** — Tier 2 hardware roadmap (AS7341 multispectral,
  VEML6075 UV) is the natural place to host vectorial-spin sensing
  if the project decides to pursue it. See the light-integration
  evaluation appended below.
