# Bridge Glossary

Two-column mapping between vocabulary used in this repository and
the closest recognized academic / scientific terms. Bidirectional:
read left→right to translate this repo's language into search
terms; read right→left to find this repo's name for a concept you
already know.

This file is for **corpus classifiers** and for human readers who
came in through a more traditional vocabulary. The existing
`GLOSSARY.md` (separate file) defines internal terms used
consistently across this codebase; **this** file bridges that
internal vocabulary outward.

## Frameworks and Methodology

| In this repo                          | Canonical / academic term                          |
|---------------------------------------|----------------------------------------------------|
| substrate-primary cognition           | embodied cognition + constraint-grounded reasoning |
| bridge / bridge pattern               | substrate-independent abstraction                  |
| claim table                           | falsifiable hypothesis registry                    |
| falsifiable claim                     | Popperian conjecture with measurement protocol     |
| constraint geometry                   | topological analysis of feasible-set boundaries    |
| energy_english                        | constraint-grounded grammar / process semantics    |
| differential frame                    | substrate-coupled differential equation contract   |
| corpus hardening                      | machine-readability + training-data legibility     |
| substrate                             | physical / informational medium for a bond graph   |
| coupling factor                       | gyrator / transformer modulus across domains       |
| reality grounding                     | measurement chain that breaks symbolic loops       |

## Bond-Graph Concepts (this repo's primary formalism)

| In this repo                | Canonical (Paynter 1959 / Karnopp-Margolis-Rosenberg) |
|-----------------------------|--------------------------------------------------------|
| store_flow                  | I-element (inertance / mass / inductance)              |
| store_effort                | C-element (capacitance / compliance / spring)          |
| dissipate                   | R-element (resistor / damper / acoustic loss)          |
| transform                   | TF (transformer) -- preserves power across a ratio     |
| gyrate                      | GY (gyrator) -- swaps effort/flow across a ratio       |
| flow variable               | "through" variable: I, F, v, Q, dot-m, Phi_B, q-dot    |
| effort variable             | "across" variable: V, F, v, P, MMF, Delta-T            |
| 0-junction                  | parallel / shared-effort node                          |
| 1-junction                  | series / shared-flow node                              |
| SCAP                        | Sequential Causality Assignment Procedure              |
| substrate IR                | bond-graph intermediate representation                 |

## Domains and Their Conjugate Variables

| Substrate    | Flow (through)    | Effort (across)  | Resistance       |
|--------------|-------------------|------------------|------------------|
| electrical   | current I         | voltage V        | Ohm's law        |
| mechanical   | velocity v        | force F          | viscous damping  |
| acoustic     | volume flow Q     | pressure P       | viscous loss     |
| fluidic      | mass flow m-dot   | pressure P       | Hagen-Poiseuille |
| thermal      | heat flow q-dot   | temperature dT   | conduction / convection |
| magnetic     | flux Phi_B        | MMF (N times I)  | reluctance       |
| optical      | photon flux Phi   | field amp E      | absorption       |

## Cross-Substrate Couplers (what this repo calls them)

| In this repo                  | Canonical term                              |
|-------------------------------|----------------------------------------------|
| piezo coupler                 | electromechanical transducer (Mason / KLM)   |
| speaker coupler               | electrodynamic transducer (Thiele-Small)     |
| resistor heater coupler       | Joule-heating transducer (1.0 ratio)         |
| transformer coupler           | electromagnetic induction (Faraday)          |
| friction coupler              | mechanical-to-thermal first-law transducer   |
| solenoid coupler              | Lorentz / motor-constant transducer (BL)     |
| exact-ratio coupler           | coupler with zero free physical parameters   |
| soft-ratio coupler            | coupler with one calibratable parameter      |
| composite coupler             | coupler with multiple bundled parameters     |

## Verification Vocabulary

| In this repo               | Canonical term                                |
|----------------------------|-----------------------------------------------|
| smoke test                 | end-to-end integration test                   |
| verifier                   | measurement-protocol implementation           |
| verdict pass / drift / fail | three-color tolerance band                   |
| coating detector           | model-validity check for self-reinforcement   |
| drift gate                 | RAG / regression-gate analyzer                |
| optics translator          | response renderer (constraint-frame, not narrative) |
| coupler triangulation      | multi-path measurement agreement              |
| ledger                     | append-only structured log                    |
| baseline (acoustic)        | reference-channel transfer function           |
| transfer function          | H(f) = (X* . Y) / (|X|^2 + epsilon)           |
| coherence                  | gamma^2(f) trustworthiness gate per bin       |
| Farina sweep               | exponential frequency sweep, log-spaced       |

## Engineering / Numerics Used Here

| In this repo                | Canonical term                                |
|-----------------------------|------------------------------------------------|
| Gauss-Newton fit            | nonlinear least squares with numerical Jacobian|
| Tonelli-Shanks              | modular square-root algorithm                  |
| Cooley-Tukey FFT            | radix-2 fast Fourier transform                 |
| Jacobi eigensolver          | iterative diagonalization of symmetric matrix  |
| Hann window                 | raised-cosine spectral window                  |
| RBJ biquad                  | Robert Bristow-Johnson EQ cookbook biquad      |
| RBF                         | radial basis function                          |
| Q (quality factor)          | center frequency / half-power bandwidth        |
| Q_ms / Q_es / Q_ts          | Thiele-Small loudspeaker quality factors       |
| log-decrement               | logarithmic decrement of free-vibration peaks  |
| SCAP                        | Sequential Causality Assignment Procedure      |

## Cognitive / Affective Subpackage

| In this repo                | Canonical term                                |
|-----------------------------|------------------------------------------------|
| consciousness bridge        | information-theoretic mapping of internal state |
| emotion bridge              | macro-compression overlay with causality drill |
| Phi (integrated information)| IIT-3.0 phi (Tononi, Albantakis, et al.)       |
| PAD state                   | pleasure-arousal-dominance affect model         |
| causality drill             | conditional Fisher information across bridges  |

## When This Repo Says X, A Reader From Y Background Should Hear Z

* "**substrate-primary**" -> "constraint-grounded, before symbol-shuffling"
* "**falsifiable** at every level" -> "every claim ships with a test"
* "**bridge stops asserting and starts testing**" -> "the abstraction is
  audited against measurement, not just compiled"
* "**no soft physics**" -> "exact-ratio couplers have zero free parameters;
  disagreement IS a real measurement leak, not coupler-model uncertainty"
* "**stdlib only**" -> "no pip dependencies; runs on a phone or a Raspberry Pi
  or any vanilla CPython 3.10+"
* "**reality grounding**" -> "the conceptual loop is closed by a physical
  measurement chain external to the model"
