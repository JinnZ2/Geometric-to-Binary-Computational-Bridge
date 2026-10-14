# Ruff scope record — 2026-10-14

## `lowering.py` / `F601`

**Original diagnostic:** `("thermal", "radiative_surface")` is defined twice
(line 105: legacy linearized `dissipate`; line 118: nonlinear
`dissipate_dynamic`), recorded in
`/home/ubuntu/work-wo10/logs/Geometric-to-Binary-Computational-Bridge/26-lowering-ownership-decision-evidence.txt`.

The second entry currently overrides the first. The supplied structural-repair
history explicitly says both the linearized path is kept with a warning and the
new nonlinear path is the Tier-2 path. Renaming one key, merging the lambdas,
or selecting a default each changes the lowering API and physical model; this
cannot be chosen mechanically.

Ruff remains enabled for the file except for this one `F601` rule. Remove the
scope after the owner specifies whether callers need distinct primitive keys or
a selector, and preserve the non-selected formulation as a historical specimen.
