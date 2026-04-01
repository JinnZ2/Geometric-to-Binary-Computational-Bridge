# Node-to-Interaction Mapping

> Maps each energy node in `physical_coupling_matrix.py` to its dominant physical
> interaction, reframes the original model labels, and documents the Ambient split.

---

## 1. Map Nodes to Dominant Interactions

### G (Grid)

What it really is: electromagnetic field transport (conductors, voltage gradients)

- **Primary interaction:** electromagnetic
- **Secondary:** thermal (losses: I^2R)
- **Reframe:** G = organized EM transport layer

### T (Thermal)

What it is: statistical EM (randomized particle motion)

- **Primary interaction:** electromagnetic (degraded form)
- **Secondary:** radiative (IR emission), mechanical (expansion, convection)
- **Reframe:** T = high-entropy energy reservoir

### M (Mobility / Mechanical)

What it is: bulk motion under EM + gravitational constraints

- **Primary interactions:** mechanical (emergent from EM), gravitational
- **Secondary:** thermal (friction -> loss)
- **Reframe:** M = low-entropy structured energy in motion

### B (Biological)

What it is: chemical + electrochemical + thermal regulation

- **Primary interactions:** chemical (delta-mu), electromagnetic (bonding, signaling)
- **Secondary:** thermal (metabolism losses)
- **Reframe:** B = adaptive chemical energy processor

### A (Ambient) -- SPLIT

This one was mixed. It hid too much. Now split into three:

- **A1: Radiative field** -- solar input (photons)
- **A2: Fluid field** -- wind, pressure gradients
- **A3: Environmental thermal** -- background grad-T

Primary interactions: electromagnetic (radiation), mechanical (fluid motion), gravitational (driving large-scale flows)

**Reframe:** A = external forcing fields (radiative + fluid + thermal)

---

## 2. Cleaned Structure

```
EM_transport      (G)   ->  node "EM"
Thermal_reservoir (T)   ->  node "T"
Mechanical_flow   (M)   ->  node "M"
Chemical_system   (B)   ->  node "C"
Radiative_input   (A1)  ->  node "R"
Fluid_dynamics    (A2)  ->  node "F"
Ambient_thermal   (A3)  ->  merged into node "T" (background gradient)
```

Coupling = Interaction Conversion

The coupling matrix becomes physically meaningful:

| Conversion | Direction | Example |
|-----------|-----------|---------|
| Mechanical -> EM | M -> EM | generator, piezo |
| Thermal -> EM | T -> EM | Seebeck |
| EM -> Thermal | EM -> T | resistance losses |
| Chemical -> Thermal | C -> T | combustion, metabolism |
| Radiative -> EM | R -> EM | solar PV |
| Fluid -> Mechanical | F -> M | wind turbine |

---

## 3. What This Fixes

### Removes ambiguity

"A" is no longer a catch-all.

### Prevents invalid couplings

You won't accidentally imply:
- thermal -> mechanical at high efficiency without gradient
- ambient -> grid without intermediate mechanism

---

## 4. Optimization Principle

The system is not maximizing energy.

It is **minimizing irreversible flow into the thermal reservoir**.

Instead of "no waste" (imprecise):

> "Energy is conserved; utility is lost when structure collapses into thermal equilibrium."

---

## 5. Where Earlier Ideas Fit

| Concept | Path | Regime |
|---------|------|--------|
| Piezo roads | M -> EM | narrow |
| Biogas | C -> T -> EM | -- |
| Solar PV | R -> EM | -- |
| Solar thermal | R -> T -> EM | -- |
| Wind | F -> M -> EM | -- |
| Thermal storage | T <-> T | time shifting |

---

## 6. The Missing Layer: Modulators

Those earlier concepts (harmonic, coriolis, etc.) are NOT nodes.

They are **modulators of coupling efficiency between nodes**:

- **Harmonic** -> improves M <-> EM coupling
- **Coriolis** -> shapes F (fluid paths)
- **Gravity** -> shapes M and F

---

## 7. Fully Compressed View

```
SOURCES:
  - Radiative (R)
  - Nuclear (not in system yet)

STRUCTURED ENERGY:
  - Mechanical (M)
  - Electrical (EM)
  - Chemical (C)

DEGRADED:
  - Thermal (T)

FIELDS THAT SHAPE FLOW:
  - Gravity (G)
  - Rotation / Coriolis (K)
  - Geometry / resonance
```

The coupling matrix, rewritten as interaction-to-interaction, exposes:
- which conversions are physically weak
- where gains are overestimated
- where new couplings actually matter
