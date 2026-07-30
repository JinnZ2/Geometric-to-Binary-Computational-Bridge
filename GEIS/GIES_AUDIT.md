# GIES audit — the representation could not see its own gate set

Numbers computed in `gies_core.py` / `gies_codec.py`, settled by
`tests/test_gies_core.py` (60 tests, stdlib only). `state_tensor.py`,
`octahedral_state.py` and `geometric_encoder.py` are left in place for
provenance and still pass `test_simple.py`; use the new modules for new work.

## GIES-1 — the collapse

`state_tensor.py` §8.3: `return np.outer(v, v)`, and
`outer(v,v) == outer(-v,-v)` identically. The position table is antipodal in
pairs — state `7-i` is exactly `-state i`.

    eigenvalues, all 8 states (rank 1, |v|^2 = 3*0.0625)   {0, 0, 0.1875}
    trace,       all 8 states                              0.1875
    determinant, all 8 states                              0
    project(n), state i vs state 7-i                       identical

Every scalar method returns the same number for all eight states.
Eigenvectors differ only up to sign, so states `i` and `7-i` are
indistinguishable by any operation the class offers. Since `NOT(i) = 7-i`,
**the gate set's only unary operation is undetectable by the representation.**

`GIES.md` §7.2 already specifies the correct form —
`T = SUM_i w_i * t_i (x) t_i` over bond directions with electron-density
weights. §8.3 implements a degenerate special case of its own spec. The spec
is right. (§7.2's matrix display is also mistyped: `Txy` appears twice in row
one, rows two and three are identical, and there is no `Tzz` anywhere — the
tensor was never written down.)

## The fix, in closed form

The four sp3 bonds are a spherical 2-design, so `SUM_i t_i (x) t_i = (4/3) I`
and the weighted sum telescopes:

    u = +t_k (lattice)       eigenvalues {4/3 + 8k/9, 4/3 - 4k/9, 4/3 - 4k/9}
    u = -t_k (interstitial)  eigenvalues {4/3 - 8k/9, 4/3 + 4k/9, 4/3 + 4k/9}

At kappa = 0.5: `{1.7778, 1.1111, 1.1111}` against `{1.5556, 1.5556, 0.8889}`.
Distinct — the collapse is gone. The doubly-degenerate pair is the C3v axial
symmetry of a `<111>` direction, correctly reproduced. At kappa = 0 everything
collapses again, which is correct: kappa is the anisotropy knob.

## Which invariant carries the bit — not the trace

The anisotropic part is traceless, so **trace = 4.0000 for all eight states**
and separates nothing. J2 is also common to both sublattices. The carrier is
**J3, the deviatoric determinant, which flips sign with parity**: +0.02195 on
the lattice sublattice, -0.02195 on the interstitial, at kappa = 0.5. That is
the same "J3 mode" invariant already listed in
`Silicon/silicon_error_correction.json`, so the check bit is readable by the
strain channel this repository settled on.

    J3 sign      -> 1 bit : site type, == index parity   <- the free check bit
    unique axis  -> 2 bits: which of the four bond directions
                    3 bits total

`decode_tensor()` recovers all three bits from four bond projections. This does
**not** contradict TTM-2 in `Silicon/tensor_readout.py`: TTM-2 says the four
sp3 projections are rank-deficient on a *general* symmetric tensor. These live
in the two-parameter family `alpha*I + beta*t_k (x) t_k`, where four
projections are complete. Reading an arbitrary strain tensor still needs the
six `<110>` directions.

## GIES-2 — index parity is site type, and it is physical

Walk 2.352 A from a lattice atom along each of the eight `<111>` directions:

    idx  bin   direction   #neg  parity  occupied   site
    ---  ----  ----------  ----  ------  --------   ---------------------
     0   000   +t1          0    even    yes        lattice (atom)
     3   011   +t4          2    even    yes        lattice
     5   101   +t2          2    even    yes        lattice
     6   110   +t3          2    even    yes        lattice
     1   001   -t3          1    odd     no         tetrahedral interstitial
     2   010   -t2          1    odd     no         interstitial
     4   100   -t4          1    odd     no         interstitial
     7   111   -t1          3    odd     no         interstitial

Checked against the diamond-cubic basis. The empty site's coordination shell
(4 neighbours at 2.352 A, 6 at 2.716 A) is **identical** to the tetrahedral
interstitial at (1/2,1/2,1/2).

This refines rather than contradicts `CLAUDE.md`'s note that the eight `<111>`
directions are "4 sublattice-A bonds + 4 sublattice-B bonds". Both hold: as
*directions* the eight are the two sublattices' bond sets, but from a *fixed*
atom only the four even-parity ones terminate on an atom.

**The address space already contains its own parity check, and the check is
physically meaningful** — it says whether the cell is an atom or a hole.
Nobody put it there deliberately and nothing in the document used it. That is
the error-detecting code the "geometric error correction" claim wanted and
never delivered.

## GIES-3 — every NOT is a Frenkel pair

`NOT(i) = 7-i` flips three bits, so it flips parity. Crossing the flag moves
an atom to an interstitial: **~4.5-5 eV, and it leaves a vacancy behind.** The
cheapest logic operation in the gate set is the most expensive physical event
in the crystal. Every *single*-bit transition is also a Frenkel pair; only
even-weight flips stay on a sublattice.

**So the honest state space is 4 states plus a site-type flag, not 8
interchangeable states.**

## GIES-4 — the encoder, traced rather than read

Two corrections to the diagnosis. `'||'` does **not** collapse onto `'|'` —
both `geometric_encoder.py` and `geometric_sensor_sim.py` special-case it
before the single-character lookup, and it emits 7 bits. The real defects:

1. **`':'` and `'/'` both map to `'0'`.** `'001:O'` and `'001/O'` both encode
   to `'001000'` and both decode to `'001/O'`. The file's own comment concedes
   it. A documented operator is silently lost — a non-bijection by
   construction.
2. **The output is variable-length and not prefix-free.** `'|'` -> `'1'`,
   `'||'` -> `'11'`. Single tokens round-trip only because `decode_from_binary`
   infers the operator width from total length. Streams are ambiguous:
   `'0011100001100'` parses as `('001||O','001|O')` *or* `('001|X','000||O')`.
3. All three worked examples in `GIES.md` quote 5 bits (`'00110'`, `'01010'`,
   `'01110'`) where the code emits 6, and the decoder rejects anything under 6.
   **Every worked example crashes the document's own decoder.**

Why no test caught it: `test_simple.py` validates one token, `'011|O'`, which
happens to work.

`gies_codec.py` fixes it with fixed-width fields — `vertex(3) + op(2) +
sym(2) = 7 bits` — which is prefix-free for free. 128 tokens, 128 distinct
codes, verified exhaustively.

## GIES-6 — the gate set is binary logic on labels

§7.5 `AND(Si, Sj) = Sk where k = i & j` operates on the **index label**, not
the position vector, not the tensor, not any geometric relation. Relabel the
states and the gate changes; a geometric operation cannot depend on the
labelling. States 1 and 2 are geometrically interchangeable (same parity, same
angle multiset to every other state) yet the AND table distinguishes them.

§11.1 asks whether the gate set is Turing complete. `{NOT, AND}` = NAND, so
yes, trivially — and answering it exposes the problem: completeness comes from
the binary relabelling, not from the geometry.

Direct contradiction, unresolved in the document: §7.5's AND is 2-in/1-out and
non-injective, hence lossy; §9.2 says "Reversibility: Yes" and §9.1 says
"Lossless collapse".

## Positions are cube corners — sixth occurrence

`(±¼,±¼,±¼)`, all eight sign combinations, are **cube corners**. An octahedron
has **6** vertices at `(±a,0,0)` and permutations. "O" is used throughout as
"Octahedral state class identifier" and §N as "Octahedral Model: N = 8
(vertices/coordination sites)". Si site symmetry is Td.

## Remaining claims, corrected

| claim | status | correct value |
|---|---|---|
| "Kramers doublet protection" (§3.3) alongside "Decoherence: N/A (classical)" (§9.3) | **INCOHERENT BOTH WAYS** | Kramers degeneracy needs an odd electron count and is a time-reversal-protected *quantum* degeneracy, so it decoheres. Si bonding electrons are paired and Si-28 (92.2%) has I = 0. |
| "6-fold coordination under doping/pressure" (§3.1) | **WRONG** | octahedral Si occurs in Si-II (beta-tin) above ~11 GPa. A different *phase*, not a state of diamond-cubic Si. Doping does not produce it. |
| "Information density: 1 bit vs ~3 bits" (§9.1) | **NOT SHOWN** | 3 binary cells also hold 8 states. GIES gains density only if one geometric cell is smaller than 3 binary cells. Cell **area** is the figure of merit and appears nowhere. |
| "Dense / Compressed / Collapse" modes (§2.2) | **NO COMPRESSION** | 6 bits in, 6 bits of independent content out. |
| numpy / scipy / matplotlib | **BREAKS STDLIB TIER** | the whole core needs none; `gies_core.py` and `gies_codec.py` are stdlib. |

## Claim table

| ID | CLAIM | FALSIFIER | STATUS |
|---|---|---|---|
| **GIES-1** | `outer(v,v)` makes states i and 7-i identical in every invariant and every projection | any method in `StateTensor` separating 0 from 7 | DEAD |
| **GIES-2** | index parity == site type: even -> lattice sublattice, odd -> tetrahedral interstitial | a listed position whose parity does not match its site | LIVE, **verified against the lattice** |
| **GIES-3** | `NOT(i)=7-i` flips parity, so every NOT is a Frenkel pair, ~4.5-5 eV | a NOT that stays on one sublattice | LIVE |
| **GIES-4** | the encoder is not a bijection | distinct outputs for `'001:O'` and `'001/O'` from the §8.2 code | DEAD (via `':'`, not `'||'`) |
| **GIES-5** | §7.2's weighted-sum tensor separates all inversion pairs for kappa != 0 | a kappa != 0 leaving pairs degenerate | LIVE |
| **GIES-6** | bitwise AND on index labels is not a geometric operation — relabel and the gate changes | a relabelling of 0-7 that preserves the gate table | LIVE |
| **GIES-7** | eigenvalues carry exactly 1 bit (site type); the other 2 live in the eigenframe | an invariant distinguishing two same-parity states | LIVE |
| **GIES-8** | the encoding is not prefix-free, so token streams are ambiguous | a unique parse of `'0011100001100'` under the old encoder | DEAD |

GIES-2 is the one worth pulling out: the address space already carries its own
parity check, the check is physically meaningful, and it is free.

*License: CC0*
