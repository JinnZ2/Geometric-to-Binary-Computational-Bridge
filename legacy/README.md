# legacy/

Superseded material, kept for **provenance only**.

Nothing in here should be built on, cited, or used to justify a design
decision. Each file was replaced by work elsewhere in the repository; the
replacement is named below. They are kept because the claim register
(`Negentropic/NEG_CLAIMS.md`, the `audit_v1` blocks in the Silicon specs)
refers to what these files said, and a correction ledger that points at
deleted files is not auditable.

## Criterion for moving something here

A file belongs in `legacy/` when **all** of these hold:

1. It has been superseded by a named replacement that is tested or specified.
2. Its defects are recorded somewhere that survives — an audit block, a
   correction ledger, or a claim register entry.
3. Nothing imports it, and no live document depends on its content being
   true.

A file with defects that have *not* been recorded stays where it is until
they are, because moving it here would quietly bury the error rather than
fix it.

## Contents

| File | Superseded by | Why |
|---|---|---|
| `Negentropic-05-implementation.md` | `Negentropic/core.py`, `negentropic_engine.py`, and the rest of the module tier | Original code listings carrying the inverted Kuramoto sign, the constant-D Fokker-Planck form, `A = avg_R_e`, compounding curiosity, and the raised cosine applied to Euclidean distances. All five are in `Negentropic/corrections.md` |
| `Silicon-3D_LIGHT_ENHANCED_OCTAHEDRAL_PROCESSING.md` | `Silicon/optical_interface.md` | Three FATAL defects: magneto-optic control of a diamagnetic material, photon-driven site-level state switching against a ~1e8-site mode-size mismatch, and indirect-gap optical addressing. Audited in the replacement's `audit_v1` section |

## Deliberately NOT moved

Recorded so the next pass does not have to re-derive the reasoning:

- **`Negentropic/lens_playground.py`** — NEG-7 is dead, but the divergence
  table (which actions the lenses actually split on) is the part that
  carries information, and it still runs.
- **`Negentropic/lenses.py`** — imported by the falsifier. The lens
  definitions are the *subject* of a live test, not dead weight.
- **`Negentropic/consciousness_metric.py`, `alignment_thermodynamics.py`,
  `empirical_audit.py`** — the numpy tier. Fixed in place and still
  referenced by the framework documents.
- **`Silicon/Magnetic-bridge.md`, `MAGNETIC_BRIDGE_ADDENDUM.md`** — these
  concern the *magnetic bridge encoder*, which acts on external magnetic
  fields. That is a different claim from "silicon responds magnetically"
  and is not refuted by silicon's diamagnetism. Not audited here; left
  alone rather than swept up by a grep for "magnet".
