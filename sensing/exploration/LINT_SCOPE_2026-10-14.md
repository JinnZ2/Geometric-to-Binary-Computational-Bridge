# Ruff scope record — 2026-10-14

## `exploration_engine.py` / `F821`

**Original diagnostic:** `scores` is undefined in the dictionary returned by
`FrameRouter.step()` (line 455), recorded in
`/home/ubuntu/work-wo10/logs/Geometric-to-Binary-Computational-Bridge/44-ruff-after-all-mechanical.json`.

The returned `metrics`, `trial_results`, and `narrative` are established, but
there is no local `scores` value and the file/history supplies no definition of
whether this debugging field should be per-frame, per-claim, or derived from
metrics. Supplying a plausible value would invent runtime behavior.

Ruff remains enabled for the file except for this one `F821` rule. Remove the
scope after the owner specifies the score source/shape and add a focused test.
