# CROSSLINKS

Other repositories this one is in direct conversation with. The full
ecosystem (~30 repos) is documented in `CLAUDE.md`'s **Ecosystem**
section and the `.fieldlink.json` source list. This file lists the
specific repos with *code-level integration* — modules pulled in,
modules calling out, or shared architectural patterns.

---

## Emotions-as-Sensors

- **Upstream**: https://github.com/JinnZ2/Emotions-as-Sensors
- **Fieldlink mount name**: `emotions`
- **Direction**: inbound (we pull from them)
- **License**: CC0 (their toolkit) / CC-BY-4.0 (this repo)

### What flows from Emotions-as-Sensors → this repo

Vendored from `Emotions-as-Sensors/metrology/` into
`experiments/metrology/` (one-shot copy at SHA observed 2026-05-19,
no upstream modifications):

| Source                              | Local path                                    | Role            |
|-------------------------------------|-----------------------------------------------|-----------------|
| `metrology/pattern_extractor.py`    | `experiments/metrology/pattern_extractor.py`  | PEX-001         |
| `metrology/empathy_layer_audit.py`  | `experiments/metrology/empathy_layer_audit.py`| ELA-001         |
| `metrology/measurement_honesty.py`  | `experiments/metrology/measurement_honesty.py`| MH-001 .. MH-004|
| `metrology/cooperation_substrate.py`| `experiments/metrology/cooperation_substrate.py`| CS-001        |
| `metrology/README.md`               | `experiments/metrology/README.md`             | catalog         |

Deferred upstream modules (still in their repo, not yet pulled here):
`training_loop`, `retroactive_empathy_trainer`, `dynamic_architecture_toolkit`,
`thermodynamic_overlays`.

### What flows from this repo → Emotions-as-Sensors

Conceptually rather than file-wise:

- **`experiments/emotion_substrate_dispatcher.py` (ESD-001)** — applies
  the dispatcher_v2_energetic potential-well architecture from this repo
  to emotional substrates instead of computational ones. Cites the
  upstream pedagogical sequence and calls ELA-001 + MH-004 via
  `experiments/metrology/esd_integration.py`.

- The architecture itself (gradient-descent routing on numeric problem
  state vectors with empirical learning) is mirrored across three
  dispatcher peers in this repo: `dispatcher_v2_energetic` (computational),
  `emotion_substrate_dispatcher` (emotional), and
  `comfort_layer_dispatcher` (cognitive labor).

### Reciprocal pointer for the upstream side

Ready-to-paste into `Emotions-as-Sensors/README.md` or a parallel
`CROSSLINKS.md` there:

> ### Geometric-to-Binary-Computational-Bridge
>
> The `metrology/` toolkit on this repo is vendored downstream into
> https://github.com/JinnZ2/Geometric-to-Binary-Computational-Bridge
> at `experiments/metrology/`, where `ELA-001` (empathy_layer_audit)
> and `MH-004` (InstitutionalCaptureDetector) are called from
> `experiments/metrology/esd_integration.py` to audit
> `experiments/emotion_substrate_dispatcher.py` (ESD-001) — a sibling
> dispatcher applying the same potential-well architecture from that
> repo's `dispatcher_v2_energetic.py` to emotional substrates instead
> of computational ones.

---

## How to add another crosslink to this file

When another repo starts having code-level integration with this one,
add a new section above with:

1. Upstream repo URL
2. Fieldlink mount name (if any — add it to `.fieldlink.json` too)
3. Direction (inbound / outbound / bidirectional)
4. License compatibility
5. What flows each way (modules, concepts, schemas)
6. Reciprocal pointer text for the other side
