# MnBi2Te4 light switch (Monash, ACS Nano 2026) — read against this folder

Co-authored, human + Claude, 2026-10-28. CC0.

## Source and grade

| field | value |
|---|---|
| paper | ACS Nano, published 2026-10-23, doi:10.1021/acsnano.6c06828 |
| kind | first-principles **prediction**; "experiments have yet to test" |
| read at | press depth (Phys.org, Nanowerk, RuntimeWire), 2026-10-28; paper not read |
| rendering drift | Phys.org headline "uncover"; Nanowerk / RuntimeWire "predict" |

Claim: THz light drives confined magnetophononic polaritons in **2-SL**
MnBi2Te4, changes the interlayer exchange, and flips the flake from AFM +
topologically trivial (OFF) to FM + conducting edge states (ON).

## Readout (`python Silicon/topological_switch_bounds.py`)

```
kT(300 K)                 25.85 meV
C=1 gap (6-SL, carried)   18.9 meV = 0.73 kT   -> >=10 kT only below 21.9 K
C=0 gap (6-SL, carried)   91.6 meV = 3.54 kT   -> >=10 kT only below 106 K
T_N bulk (VERIFY)         ~24 K                -> no order to switch above it
ceiling                   ~22 K, bound by the C=1 gap
silicon                   DOES_NOT_TRANSFER (no exchange in diamagnetic Si)
```

| id | finding | grade |
|---|---|---|
| TSW-1 | at the Bridge's 300 K target the C=1 gap is below kT | DERIVED |
| TSW-2 | operating ceiling = min(magnetic order, gap protection), ~22 K | DERIVED on carried + VERIFY |
| TSW-3 | bulk activation exp(-gap/2kT) 0.69 (C=1) at 300 K: bulk not insulating | DERIVED (proxy, no prefactor) |
| TSW-4 | mechanism acts on exchange; Si has none; joins FAB-1..7 | veto |
| TSW-5 | ON reads only if E_F sits inside the gap: doping is the constraint, light the knob | PROPOSED |
| TSW-6 | carried gaps are 6-SL; the 2-SL gap is NOT_IN_TEXT; nothing invented | absence |

## Where it sits

- **Not a silicon channel.** It is a candidate state channel in a different
  material, outside the Si encoding; same verdict shape as the magnetic
  channel in `magnetic_authority.py`.
- **Doping, inverted.** In `SiliconState` the knob is `n`. Here `n` (antisite
  electron doping, VERIFY) is what can hide the switch: if E_F sits in a band,
  edge conduction is shunted and ON and OFF read alike.
- **Cheapest checks:** the paper's 2-SL gap and its stated temperature; a
  2-SL T_N; whether the paper treats E_F or assumes it in the gap.

Related: Sattar, Stepanov, Canali arXiv:2604.07315 (6-SL, outer-SL alignment
sets C; no light). Interlayer magnetophononic coupling measured in
MnBi2Te4, Nature Communications 2022 (s41467-022-29545-5), VERIFY.
