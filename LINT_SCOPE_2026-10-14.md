# Ruff scope record — 2026-10-14

## `gb_explorer_2v.py` / `F811`

**Original diagnostics:** repeated module-level definitions, including
`LatticeSimulator` (line 814), `TreeNode` (928), `BridgeFactory` (1187), and
`ChipArchitecture` (1260); see
`/home/ubuntu/work-wo10/logs/Geometric-to-Binary-Computational-Bridge/44-ruff-after-all-mechanical.json`.

This standalone file contains two complete, overlapping exploration-playground
implementations. Its tracked history records the second as an additive
LatticeSimulator change; no tracked code imports this file. WO-10 repaired the
mechanical parser defects only (the `additions:` marker and two malformed tuple
comprehensions). Choosing one complete implementation or merging their class
bodies would change the runtime model and is not mechanically knowable.

Accordingly, Ruff **continues to run on this file**, but only `F811` is scoped
for it. Do not remove this exception until an owner chooses the canonical
implementation and preserves the other as an explicit historical specimen.
