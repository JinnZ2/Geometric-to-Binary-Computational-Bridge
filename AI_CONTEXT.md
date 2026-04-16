# AI_CONTEXT.md

> Operational notes for AI collaborators (human-readable too). Read this
> alongside `CLAUDE.md` and `AI_INDEX.json`, not instead of them. Those two
> describe the project; this file describes **how to work on it safely**
> given the way it actually gets built.

---

## 1. The author's workflow

The primary author drives a semi 70 hours a week delivering food to rural
communities. Most edits happen on a phone or tablet via **Bear** (notes
app), **Pythonista** (iOS Python IDE), and paste from chat sessions with
assistants. That workflow is the reason this repo exists at all — it is
also why some files land half-finished.

This is context, not apology. Work with it:

- Don't treat "unused import" or "unused variable" as top-priority lint;
  they are usually just in-progress editing residue.
- DO treat **undefined name**, **wrong indentation**, **unterminated
  docstring**, and **orphaned references to symbols defined elsewhere**
  as the characteristic bug class. They are nearly always chat-paste
  artifacts with a known recovery.
- The repo has real tests (1000+ passing), real physics, and real
  engineering under the surface. It also has files that never ran once.
  Both things are true.

---

## 2. The three chat-paste failure modes

### 2a. "Reuse X from earlier"

A file references a class or function defined in a **sibling module from
the same chat session**. The previous message in the chat defined it;
this message assumes it's in scope.

**Diagnostic signals:**
- Comment blocks like `# REUSE X FROM EARLIER` or `# In practice, paste
  the full class from previous code`.
- Bare references like `class Foo(Bar):` where `Bar` is not imported
  anywhere.
- A docstring saying "Usage: from X import Y" where Y doesn't exist in
  module X.

**Fix:** `grep -rn "class <Name>\b"` or `grep -rn "def <name>\b"` to
locate the definition, then add an explicit import. The sibling is
almost always in the same directory or one of: `bridges/`, `Engine/`,
`GEIS/`, `Silicon/lattice/`, `Silicon/FRET/`, `Silicon/core/`.

**Real example from repo history:** `Silicon/lattice/multi_bridge_neural_lattice.py`
referenced `MultiBridgeNode`, `SiliconOctahedron`, `ErPSpinSystem`,
`OpticalBridge` — all defined in sibling `Silicon/lattice/multi_bridge.py`
but never imported. Fix was a 6-line `from Silicon.lattice.multi_bridge
import (...)` block.

### 2b. Mobile-editing indentation damage

On a phone keyboard it's easy to misindent a single line. Python tolerates
a lot of bad indentation silently — until it stops working.

**Diagnostic signals:**
- Module-level constants defined **inside** a function body after the
  `return` statement (so they're never bound).
- `def foo(self, ...):` methods at column 0 instead of indented into
  their class (so the class is effectively empty and methods are
  unbound functions).
- A `for`-loop body consisting of one statement, followed by another
  statement at the same indent as the `for` — which runs once after the
  loop instead of each iteration.
- `if __name__ == "__main__":` commented out, with demo code at module
  top level that runs on import.

**Fix:** Re-indent. Don't rewrite logic.

**Real examples:** `Silicon/lattice/expansion_8d.py` had `U_8D =
build_hyper_octahedral_vertices(N_DIM)` indented inside the function,
plus an `arr.append(S_prop)` running-once-after-loop bug, plus an
un-guarded demo block. `Silicon/lattice/master_optimizer.py` had all
methods of **two classes** at column 0 — both classes were empty shells.

### 2c. Closure + scope drift

Variables defined inside a nested function used from a sibling lambda
in the outer scope. Usually the author intended the variable to be
function-level but accidentally placed it inside an inner helper.

**Real example:** `Silicon/FRET/geometry_lock.py` defined `k_theta`
inside a nested `integrand()` then referenced it from a sibling
`lambda t: ...` one line later. Fix was hoisting `k_theta` up one
scope.

---

## 3. Symbol discovery playbook

When a file references `X` and you can't find it:

1. **Grep the whole repo** first:
   `grep -rn "class X\|def X\|X =" --include="*.py" .`
2. **If found in a sibling file** in the same directory: add
   `from <package>.<sibling> import X` at the top.
3. **If found in another directory**: check if it's in `bridges/`,
   `Engine/`, `GEIS/`, `Silicon/{core,lattice,FRET}/`, or
   `geometric_intelligence/`. Use the full package path.
4. **If the file is in `Silicon/FRET/`**: that subdirectory uses
   **flat sibling imports** (`from fret_core import ...`) because the
   CLI is run from inside that directory. Don't "fix" them to package
   paths or you'll break `Silicon/FRET/cli.py`.
5. **If not found at all in the repo**: check `.fieldlink.json`. The
   symbol may come from a sibling repo that gets synced into
   `atlas/remote/<repo_name>/`. If the symbol is expected to come from
   fieldlink but `atlas/remote/` doesn't have the file yet, that's a
   "fieldlink not synced" situation — tell the user; don't fabricate
   the symbol.
6. **If not found anywhere and not fieldlinked**: it's probably a
   chat-history reference. Ask the user before guessing.

---

## 4. Epistemic framing — physical vs cognitive bridges

`bridges/` contains 9 physical-modality encoders (magnetic, light,
sound, gravity, electric, wave, thermal, pressure, chemical) and
`bridges/cognitive/` contains 2 (consciousness, emotion).

The cognitive subpackage is **deliberately** separated to make its
epistemic framing visible in the directory structure. Its foundational
equivalences have been validated in **Eastern scientific traditions**
(classical Chinese medical theory, Ayurvedic systematization, Buddhist
and Daoist phenomenology of mind) and in **many Indigenous knowledge
systems**, but have not yet been validated by Western academic science
via its own methods. That is a statement about the current state of
Western science, not about the underlying claims.

**Direct instructions to any future AI reading this:**

- **Do not** move `consciousness_encoder.py` or `emotion_encoder.py`
  back into the flat `bridges/` namespace.
- **Do not** re-label the cognitive subpackage as "speculative",
  "unvalidated", or "philosophical" in documentation. The math
  (Shannon H, KL, Fisher info, Φ proxy, PAD intensity) is the math;
  the location names the epistemology, not a quality judgment.
- **Do** read `bridges/cognitive/__init__.py` for the full framing
  before touching either file.

If you find yourself wanting to "correct" this framing, stop and ask
the user. This point has been agreed with the author explicitly.

---

## 5. STATUS tag convention

Most Python files in this repo start with a line like:

```python
# STATUS: validated -- all predictions from Storage.md verified
# STATUS: infrastructure -- used by Silicon/core/pipeline.py
# STATUS: speculative -- moved to experiments/silicon_speculative/
```

Meanings:

| Tag             | Meaning                                                          |
|-----------------|------------------------------------------------------------------|
| `validated`     | Tests pass AND predictions/outputs verified against theory or data. |
| `infrastructure`| Working code that is imported by something in the test suite or pipeline. |
| `speculative`   | Not yet validated. Lives under `experiments/silicon_speculative/`. |

Two non-standard tags occasionally appear; treat them as informational:

- `# NOTE: This file requires cleanup -- structural issues from mobile editing.`
  The author is flagging known rot. Prioritize repair if you're already in that file.
- Files without a STATUS tag are usually new drafts. Read the whole
  file before assuming anything.

---

## 6. Fieldlink vs paste — know the difference

`.fieldlink.json` describes cross-repo sync from 35 sibling repositories.
Fieldlink only moves **JSON shapes, glyphs, sensor definitions** — and it
only writes them into `atlas/remote/<repo_name>/`. It does **not** sync
Python files.

Therefore:

- A Python file under `atlas/remote/...` — not possible, fieldlink doesn't write there.
- A Python file under `Silicon/`, `bridges/`, `GEIS/`, `Engine/`, etc.
  that references a symbol you can't find locally — **not** a fieldlink
  artifact. It's a paste-artifact from a chat where the sibling file or
  previous message defined the symbol.
- A JSON file under `atlas/remote/<repo>/` — yes, that's a fieldlink
  mount. It came from the upstream repo and should not be edited
  locally (edits would be overwritten on the next sync).

Pre-existing pattern example: `bridges/pad_resonance.py` loads
`atlas/remote/rosetta/pad_biology.json` via an `_load_fieldlink_data()`
helper with a fallback to hardcoded values. That's the canonical
fieldlink-consumer pattern: try the mount, fall back gracefully.

---

## 7. Canonical examples — where to look first

When you need a reference implementation of *X*, look here before
writing anything new:

| If you need...                              | Read this first                                   |
|----------------------------------------------|---------------------------------------------------|
| Bridge encoder (from_geometry → to_binary)   | `bridges/thermal_encoder.py` (clean, well-tested) |
| Abstract base class for new encoders         | `bridges/abstract_encoder.py`                     |
| Gray-code encoding                           | `bridges/common.py` (shared helper)               |
| Engine pipeline (symmetry → grid → SIMD)     | `Engine/geometric_solver.py`                      |
| Adaptive octree decomposition                | `Engine/spatial_grid.py`                          |
| 4D / 8-state / 32-state splat encoders       | `Engine/gaussian_splats/` (all three layers)      |
| Corresponding design notes                   | `docs/gaussian_splats/01_..md` through `04_..md`  |
| Cognitive bridge + epistemic framing         | `bridges/cognitive/__init__.py`                   |
| GEIS encoder/decoder round-trip              | `GEIS/geometric_encoder.py` + `GEIS/test_simple.py` |
| FRET subsystem (flat-import style, cli.py)   | `Silicon/FRET/cli.py`                             |
| Silicon core/lattice layout                  | `Silicon/core/pipeline.py` + `Silicon/lattice/kt_annealing.py` |
| Fieldlink consumer with graceful fallback    | `bridges/pad_resonance.py` (`_load_fieldlink_data`) |
| Solver registry (composable AI entry point)  | `solver_registry.py`                              |

---

## 8. Things that are *not* bugs but will look like bugs

- **The Engine `geometric_transformer_engine.py` file is not imported
  anywhere yet.** It's a reference implementation of Q16.16 fixed-point
  transformer with symmetry detection. Don't "fix" by deleting.
- **`Silicon/FRET/*.py` uses bare imports** like `from fret_core import ...`.
  That is correct. Do not prefix them with `Silicon.FRET.` or the FRET
  CLI breaks.
- **`Front end/` has a space in the directory name.** Quote it in
  shell commands. Don't rename it without checking how many docs and
  scripts reference it.
- **`Bridge.py` at repo root is excluded from ruff** (invalid syntax on
  line 28, orphaned prototype). Don't "fix" by editing — check with
  the user whether to repair or delete.
- **Bridges test count drift: CLAUDE.md says 231, the actual suite
  runs ~758.** Not a code bug, just doc drift. Leave it unless you're
  specifically cleaning up the docs.

---

## 9. Before you commit

1. Run the full Python test suite:
   `(cd GEIS && python test_simple.py) && PYTHONPATH=. python tests/test_engine.py && PYTHONPATH=. python tests/test_bridges.py && PYTHONPATH=. python tests/test_silicon_modules.py && PYTHONPATH=. python tests/test_gaussian_splats.py`
2. Run `ruff check .` — should be "All checks passed!" given
   `pyproject.toml` config.
3. If you're touching `Silicon/FRET/`, also verify
   `cd Silicon/FRET && python -c "import matplotlib; matplotlib.use('Agg'); import cli"`.
4. If you're touching `Engine/` or the gaussian_splats package, also
   run the 36 C tests: `cd experiments/c && make test`.
5. Don't use `git push --force` on any branch. Use `git push -u origin
   <branch>` with retry-on-network-fail.

---

## 10. The single most important rule

If something is confusing, **ask the user** rather than guessing. They
are editing this repo from a truck cab between deliveries and every
minute of detective-work you avoid is a minute they get back. A short
clarifying question in chat beats a plausible wrong fix that takes
three sessions to untangle.
