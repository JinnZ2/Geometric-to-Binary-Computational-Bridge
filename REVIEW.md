# Repository Review — Geometric-to-Binary Computational Bridge

**Methodology note:** three background research agents were dispatched to
cover Sections 1–3 exhaustively (naming/duplication/API-signature sweep,
a 173-file markdown pass, and a full bugs/security/performance audit). All
three were killed mid-run by the platform's session limit before returning
results. Rather than submit an empty or padded report, every finding below
was reverified directly — by running the test suites, running `ruff`,
compiling suspect files with `py_compile`, and grepping/reading source —
so everything here is confirmed, not inferred. Coverage is real but not
exhaustive: the ~50 files in `bridges/`, all of `Engine/`, and the largest
`*_alternative_compute.py` files (700–1200 lines each) were spot-checked
rather than read line-by-line. Where a section's coverage is partial, that
is stated explicitly rather than papered over.

## Summary

| # | Section | Findings |
|---|---------|----------|
| 1 | Inconsistencies | 9 |
| 2 | Markdown Information Gaps | 6 |
| 3 | Code Audit | 10 |
| 4 | Organizational Structure Suggestions | 6 |
| 5 | Limitations Mitigation Checklist | 5 (assessed) |
| 6 | Discoverability & Crawler Optimization | 9 (assessed) |

---

### 1. Inconsistencies

**1.1 — Four different licenses claimed across the repo (highest severity).**
- `LICENSE` (root, 21 lines): full MIT License text, copyright JinnZ2 2025.
- `CLAUDE.md` header (line 5 of this session's system context): "License: CC-BY-4.0."
- `README.md` (top banner + `## License` section): "Public domain (CC0)... CC0 (public domain) per author intent."
- `CITATION.cff` line 8: `license: CC0-1.0`.
- `metadata.json` line 6: `"license": "CC0"`, and line 48 already contains a `note_on_license` field acknowledging the LICENSE/CC0 mismatch.
- `README.md` and `FALSIFIABILITY_NOTICE.txt` both already self-disclose the LICENSE-vs-CC0 conflict, but **`CLAUDE.md`'s "CC-BY-4.0" is a *third*, undisclosed value that contradicts even the author's own acknowledged CC0 intent**, and the root `LICENSE` file — the one GitHub's license detector and most legal tooling actually read — still says MIT.
- **Fix:** replace `LICENSE`'s contents with the CC0 1.0 Universal text (https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt), then remove the now-resolved reconciliation notes from `README.md`, `FALSIFIABILITY_NOTICE.txt`, and `metadata.json`, and correct `CLAUDE.md`'s header to `License: CC0-1.0`.

**1.2 — `CLAUDE.md`'s own test counts contradict each other and reality.**
- Its "Quick Reference" command block states `python tests/test_bridges.py # Bridge encoders (57 tests)`.
- Its "Testing" table two sections later states `tests/test_bridges.py | 231 | ...`.
- Running it (`PYTHONPATH=. python tests/test_bridges.py`) reports **`Ran 758 tests`**. Both numbers in the doc are stale.
- The other three counts in the same table were verified and are still correct: GEIS 116/116, Engine 58/58, Gaussian Splats 63/63, C NFS 36/36.
- **Fix:** update both occurrences to 758, or better, drop the hardcoded count and say "see CI output for current count" so it can't drift again.

**1.3 — Three bridge encoders bypass the shared Gray-code helper.**
- `bridges/common.py` exports `gray_code()`/`gray_bits()` and 14 of the 18 encoder files import it (`from bridges.common import gray_bits as _gray_bits`).
- `bridges/light_encoder.py`, `bridges/magnetic_encoder.py`, and `bridges/sound_encoder.py` instead define their own local `_gray()`/`_gray_bits()` (e.g. `sound_encoder.py:81-92`, `light_encoder.py:51-63`) that reimplement the identical algorithm.
- **Fix:** delete the three local copies and import from `bridges.common`, as CLAUDE.md's own "Follow the bridge pattern" guideline implies.

**1.4 — Inconsistent `from_geometry` signatures across `BinaryBridgeEncoder` subclasses.**
- Most encoders type-hint the parameter: `def from_geometry(self, geometry_data: dict):` (e.g. `thermal_encoder.py:136`, `electric_encoder.py:136`).
- `light_encoder.py:114`, `sound_encoder.py:141`, and `community_encoder.py:425` omit the type hint on the same parameter name.
- `bridges/drill_loop.py:188` uses a *different parameter name entirely*: `def from_geometry(self, data):` — breaks any caller using keyword args consistently across encoders.
- `bridges/vortex_bridge.py:77` adds a return-type annotation (`-> "VortexBridgeEncoder"`) no sibling encoder has.
- **Fix:** standardize on `def from_geometry(self, geometry_data: dict) -> None:` across all subclasses (`abstract_encoder.py`'s own signature has no type hints either, at line 33 — update the base class first, then the subclasses).

**1.5 — README quick-start commands reference directories that don't exist as written.**
- `README.md` "Try It Right Now": `cd frontend && npm run dev` — the actual directory is `Front end/` (capital F, a space). `cd frontend` fails.
- `README.md`: `cd engine && python geometric_solver.py` — the actual directory is `Engine/` (capital E). `cd engine` fails on any case-sensitive filesystem (Linux, and therefore CI).
- **Fix:** `cd "Front end" && npm run dev` and `cd Engine && python geometric_solver.py`.

**1.6 — README's "public API" examples reference code that does not exist anywhere in the repo.**
- `shapebridge --optimize symmetry`, `shapebridge --demo --visualize`, `shapebridge --tutorial geometric_intro`, `from geometric_bridge import FieldSolver`, `GeometricBinaryDataset()` — none of these names appear anywhere in the codebase (verified by repo-wide grep for `shapebridge`, `class FieldSolver`, `GeometricBinaryDataset`). `demos/` also does not exist.
- These read as an aspirational marketing sketch presented as literal, working commands — directly contradicting the "no invented problems" ethos this repo asks reviewers to use, and actively misleading for a new contributor or an AI system trying to call the "public API example" this same README asks crawlers to index.
- **Fix:** either implement a minimal `shapebridge` CLI shim, or (cheaper, and consistent with the rest of the doc's honesty about the LICENSE mismatch) mark the whole "human pitch" block as illustrative/aspirational and replace the "Research Integration" code sample with a real one-liner, e.g. `from bridges.thermal_encoder import ThermalBridgeEncoder`.

**1.7 — Stale conditional in `.github/workflows/tests.yml`.**
- The "Gaussian splats" step is guarded by `if: hashFiles('tests/test_gaussian_splats.py') != ''` with a comment explaining the file "lives on the `claude/extract-gaussian-splats` branch and may not exist yet on main."
- Verified via `git show main:tests/test_gaussian_splats.py`: the file **does exist on `main`** now (63/63 passing). The conditional and its comment are dead weight.
- **Fix:** remove the `if:` guard and the now-inaccurate comment; run the step unconditionally like the others.

**1.8 — Duplicate dict key silently drops one entry.** `fabrication/lowering.py:118`
- The key literal `("thermal", "radiative_surface")` is used twice in the same dict literal (`ruff` rule F601). The second occurrence silently overwrites the first — whichever lambda/config was written first for that key is dead code.
- **Fix:** rename one of the two keys to reflect its actual distinct case, or merge the two lambdas if they were meant to be the same rule.

**1.9 — `pyproject.toml`'s own justification comment for ignored lint rules is stale.**
- Lines 33–36 say F401/F541/F841 are ignored because there are "215 / 96 / 40 instances" respectively.
- Actual current counts (`ruff check . --select F401,F541,F841 --statistics`): **455 / 190 / 81** — roughly double, in every case, since that comment was written.
- **Fix:** either update the counts or (better) drop specific numbers from the comment and just say "ignored as cleanup-not-bugs; see `ruff check . --statistics` for current counts."

---

### 2. Markdown Information Gaps

**Coverage note:** the dedicated markdown-audit agent did not return results (session limit). The findings below were confirmed directly against ~15 of the highest-traffic docs (`README.md`, `CLAUDE.md`, `FALSIFIABILITY_NOTICE.txt`, `PREDICTION_PROTOCOL.md`, `CITATION.cff`, `metadata.json`, `.github/workflows/*.yml`); the remaining ~160 `.md` files (including the four `Universal-geometric-intelligence-P1..P4.md` essays and most of `docs/`) were not individually re-audited this pass.

**2.1 — README's CLI/API examples are presented as literal, not illustrative.** (Same underlying fact as finding 1.6, filed here from the "what was the author trying to convey" angle.) The intent is clearly to communicate the *shape* of the intended developer experience — draw a shape, get optimized binary, see a 3D result — but by writing it as fenced `bash`/`python` blocks with no "planned" or "illustrative" qualifier, it reads as documentation of a working CLI. A new contributor or an indexing AI system (which the same README explicitly invites, in its "For Bots/Crawlers/AI Systems" section) has no signal to distinguish this from the genuinely-runnable `python -m fabrication.smoke` command two paragraphs above it.

**2.2 — `CLAUDE.md`'s stale test counts** (see 1.2) — likely intent was simply "update this table whenever a suite grows," but no mechanism enforces that, so it drifted twice over (once between 57→231, again between 231→758) without either number being corrected.

**2.3 — `CLAIM_SCHEMA.py`'s `TABLE_FIELDS` has no scope/reference-class field.**
`TABLE_FIELDS = ("rates", "bounds", "cond", "rel", "fail", "meas")` (line 253) — covers rate, bounds, condition, relation, failure mode, and measurement, but nothing capturing the *ontological/temporal/spatial scope* a claim applies under. `BRIDGE_GLOSSARY.md` does the equivalent job for terminology (mapping in-repo jargon to academic terms), but there's no analogous "this claim's reference class is X" field in the claim schema itself. Likely intent (per `PREDICTION_PROTOCOL.md`'s emphasis on domain-specific calibration — "prediction_accuracy is meaningless aggregated across domains") was to scope every claim, but the `domain` field that document describes for *predictions* was never carried back into `CLAIM_SCHEMA.py`'s *claim table* schema. Recommend adding a seventh field, e.g. `scope`, alongside the existing six.

**2.4 — `.github/workflows/tests.yml`'s "Verify in 60 seconds" cross-reference.**
The workflow comment says each step "runs exactly the same command as the 'Verify in 60 seconds' section of `AI_INDEX.json`." `AI_INDEX.json` does exist and does contain a verification block, so this one checks out — flagged here only because it's the kind of cross-file claim that silently breaks the moment either file is edited alone; worth a one-line note in `CLAUDE.md`'s Development Guidelines ("if you touch tests.yml or AI_INDEX.json's verify block, touch both").

**2.5 — `README.md`'s "Sister repositories" list versus `CLAUDE.md`'s "Ecosystem" table diverge in framing without cross-reference.**
`README.md` lists 8 "most tightly coupled" sister repos (differential-frame-core, energy_english, earth-systems-physics, calibration-audit, labor-thermodynamics, projection_error_modes, Hormuz_cascade, automation_scope_audit) — none of which appear in `CLAUDE.md`'s 32-row Ecosystem table, and vice versa (e.g. `CLAUDE.md`'s `mandala`/`rosetta`/`polyhedral` don't appear in README's list). Likely intent: README's list is "tightest code-level coupling," CLAUDE.md's is "the full fieldlink-synced ecosystem" — a legitimate distinction, but neither doc says so explicitly, so a reader has no way to know the two lists aren't just out of sync with each other.

**2.6 — `FALSIFIABILITY_NOTICE.txt`'s refutation procedure only names `/tests/`, `/GEIS/`, and `/fabrication/` test locations.**
It doesn't mention `tests/test_silicon_modules.py` (which exists and runs in CI per `.github/workflows/tests.yml`) or `tests/test_gaussian_splats.py`. Likely just written before those suites existed and not revisited. Fix: add both to the notice's list at lines 9-13.

---

### 3. Code Audit

**Coverage note:** the dedicated code-audit agent did not return results (session limit). Findings below were confirmed by actually running `ruff check .`, `py_compile`, and the test suites — they are not a substitute for the deeper line-by-line pass across all of `Engine/`, `bridges/`, and the largest `*_alternative_compute.py` files that agent would have done; treat this list as high-confidence and real, not exhaustive.

**3.1 — `Bridge.py:28` cannot be compiled — literal invalid syntax.**
```python
MAGIC_NUMBER = 0xGB  # 0x47 0x42 in bytes? We'll use 0x47 for 'G', 0x42 for 'B'
```
`0xGB` is not a valid hex literal (`G` isn't a hex digit) — `python3 -m py_compile Bridge.py` raises `SyntaxError: invalid hexadecimal literal`. `pyproject.toml` already excludes this file from `ruff` with a comment calling it "an orphaned prototype that nothing imports," rather than fixing or deleting it.
**Fix (the comment tells you the intent):**
```python
MAGIC_NUMBER = 0x47  # 'G' — see PROTOCOL_VERSION below for 'B'/version disambiguation
```
or delete the file if it's genuinely dead, per the pyproject.toml comment's own suggestion.

**3.2 — Six more files have real `SyntaxError`/`IndentationError`, all sharing one root cause.**
Confirmed via `py_compile` and `ruff check . --statistics` (346 of the repo's 352 total lint errors are `invalid-syntax` from just these six files):
- `experiments/dispatcher.py:144` — `IndentationError`. Lines 138-141 close a dict literal (`}`) and start a new module-level comment banner; line 144 (`"cobol": { ... }`, 4-space indented) is an orphaned dict-entry with no enclosing `{`, i.e. an entry that belongs *inside* the dict closed three lines above got separated from it.
- `experiments/dispatcher_v2_energetic.py:241` — identical pattern, same file family.
- `experiments/solvers/bash_runner.py:14` and `experiments/solvers/sql_runner.py:7` — the module docstring appears to be duplicated: an ASCII-safe (`--`) header followed by a second, em-dash (`—`) header + box-drawing banner, breaking the triple-quote balance so the banner characters land outside string context.
- `experiments/solvers/c_runner.py:110-111` — two near-identical lines back to back, one with `—` and one with `--`:
  ```python
  f"{[t.value for t in problem.tags]} — refusing misroute"), 0.0
  f"{[t.value for t in problem.tags]} -- refusing misroute"), 0.0
  ```
- `experiments/solvers/python_runner.py` — the entire module appears duplicated: `from __future__ import annotations` occurs twice (lines 7 and 65 — a hard `SyntaxError`, future-imports must be the first statement), two different import blocks (`from dispatcher import Problem, register_runner` at line 13 vs. `from runner_api import Problem, register_runner` at line 68), and two `@register_runner("python") def run_python(...)` definitions (lines 155 and 250, confirmed via `ruff` F811 "redefinition of unused `run_python`").

All six read as the same failure mode: **a duplicate/"corrected" copy of content was inserted alongside the original instead of replacing it** (plausibly from an automated `--`→`—` typographic pass, or a bad merge). This is not cosmetic — `test_guards.py`, `demo.py`, `demo_multi.py`, `demo_recursive_learning.py`, `demo_v2_learning.py`, `demo_all_langs.py`, and `landscape_overhead_axes.py` all import from `dispatcher` or `solvers.python_runner`/`bash_runner`/`c_runner`/`sql_runner`, so every one of those currently fails at import time.
**Fix:** for each file, diff against the last good commit (`git log -p -- <file>`) to find where the duplication was introduced, and delete the duplicate half. `c_runner.py`'s fix is a one-line deletion (drop either line 110 or 111).

**3.3 — CI's `lint` job is currently red.**
`.github/workflows/tests.yml`'s `lint` job runs bare `ruff check .`, which picks up the repo's own `pyproject.toml` config (`select = ["F"]`, `ignore = ["F401","F541","F841"]`). Run exactly that way: **exit code 1, 352 errors** — almost entirely the six files in 3.2 (which are not in `pyproject.toml`'s `extend-exclude` list, unlike `Bridge.py`), plus:
- 4× F811 (redefinitions in `python_runner.py`, see 3.2)
- 1× F404 (`from __future__` not at top of file, `python_runner.py:65`, see 3.2)
- 1× F601 (duplicate dict key, `fabrication/lowering.py:118`, see 1.8)
**Fix:** fixing 3.2 resolves 350 of the 352 errors immediately; the F601 needs the one-line dict-key fix from 1.8.

**3.4 — Bare `except:` swallows all exceptions, including `KeyboardInterrupt`.** `Silicon/core/elemental_playground.py:929` and `:941`
```python
try:
    m = self.navigator.get_manifold(symbol)
    all_regimes.update(r for r, v in m._regime_basins.items() if v > 0.5)
except:
    pass
```
Both are in report-generation loops over `self.database.list_elements()`. A bare `except:` (not even `except Exception:`) will also catch `KeyboardInterrupt` and `SystemExit`, making the process hard to interrupt, and it silently hides any real bug in `get_manifold`.
**Fix:** `except (KeyError, AttributeError):` (or whatever `get_manifold` actually raises for a missing element) so unrelated bugs surface.

**3.5 — `eval()` on a constructed string.** `experiments/comfort_layer_dispatcher.py:402` and `experiments/run_experiment.py:59`
```python
m = re.search(r"(\d+)\s*([\+\-\*/])\s*(\d+)", text)
a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
result = eval(f"{a}{op}{b}")
```
Not currently exploitable — `a`/`b` are regex-constrained to `\d+` and coerced to `int`, and `op` is constrained to one of `+-*/` (or normalized from `x`/`×`) before reaching `eval`. Still a fragile pattern: the very next person who loosens that regex (e.g. to allow `.` for decimals, or a variable name) turns this into real code execution.
**Fix:**
```python
import operator
OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
result = OPS[op](a, b)
```

**3.6 — No dimensional-analysis library anywhere in the codebase.**
Verified via repo-wide grep for `pint`, `unyt`, `astropy.units` — none found. Every physics function across all 11 bridge encoders (`thermal_encoder.py`, `electric_encoder.py`, etc.) encodes units only in the variable name (`T_K`, `Ea_J_mol`, `rho`, `depth_m`) with zero runtime enforcement — nothing stops a caller from passing Fahrenheit into a `T_K` parameter and getting a silently-wrong (not crashing) result. See Section 5.2 for the fuller "Grounding Problem" discussion; noted here as a concrete audit finding since it affects every encoder, not a design opinion.

**3.7 — Missing tests for three of `fabrication/`'s most foundational modules.**
`fabrication/substrate_ir.py` (the bond-graph IR dataclasses themselves), `fabrication/ledger.py` (the "single source of truth" per `README.md`'s own description), and `fabrication/lowering.py` have no dedicated test file anywhere under `fabrication/*/tests/` — the only place any of the three is even imported by a test is `fabrication/passes/tests/structural_repair_smoke.py`, incidentally. Given `fabrication/lowering.py` already has a live bug (1.8/3.3), this isn't hypothetical risk.
**Fix:** add `fabrication/tests/substrate_ir_smoke.py` and `fabrication/tests/ledger_smoke.py` covering `Element`/`Junction`/`Bond`/`SubstrateIR.add_junction`/`add_bond` round-trips and `GEOMETRY_TO_PARAMETER` lookups for each documented domain.

**3.8 — `src/` is dead weight.**
`src/__init__.py` is the only file in `src/`, it's empty, and repo-wide grep for `from src.` / `import src.` returns nothing. Nothing imports it.
**Fix:** delete the directory, or if it's reserved for a future packaging layout, say so in a one-line `src/README.md` so the next contributor doesn't wonder if they're missing something.

**3.9 — `fabrication/archive_tests/` breaks the test-directory naming convention.**
Every other `fabrication/` subpackage's tests live at `<subpackage>/tests/` (`fabrication/verify/tests/`, `fabrication/emit/tests/`, `fabrication/passes/tests/`, `fabrication/voice/tests/`). `fabrication/archive_tests/` is the only one named `<subpackage>_tests/` instead of `<subpackage>/tests/`.
**Fix:** move to `fabrication/archive/tests/` (note: `fabrication/archive.py` is a single file, not a package, today — this would mean turning it into `fabrication/archive/__init__.py` first, or simplest: just rename `archive_tests/` → `tests/` if it's meant to sit alongside `archive.py`, matching the pattern used elsewhere at the top level, e.g. `fabrication/tests/helmholtz_loop.py`).

**3.10 — Subprocess calls to external toolchains are unguarded against a missing/attacker-controlled `PATH`.**
`experiments/solvers/{c,rust,fortran,cobol,go}_runner.py` each `subprocess.run(["gcc"/"rustc"/"gfortran"/"cobc"/"go", ...])` with no absolute path and no `PATH`-scrubbing. Low severity for a local research-script sandbox (these aren't network-facing), but worth a one-line note since they compile and then immediately execute the resulting binary (`_EXE_PATH`) — if this code path is ever reused in a context where `PATH` isn't trusted, that's a code-execution primitive. Not urgent; flagged for completeness per the audit's security-issues category, not because it's actively exploitable in this repo's current usage.

---

### 4. Organizational Structure Suggestions

**4.1 — Fix or remove `Bridge.py` rather than permanently excluding it.**
It's the one file `pyproject.toml` singles out by name as broken and unimportable (see 3.1). A permanently-excluded, broken file at repo root is worse for onboarding than either fixing the one-line bug or deleting it — a new contributor has no way to know, without reading `pyproject.toml`'s comments, that this file is intentionally dead rather than accidentally broken.

**4.2 — Delete or document `src/`.**
An empty, unimported package directory (3.8) is a common source of "wait, am I supposed to be putting things here?" confusion for a new contributor exploring the tree for the first time.

**4.3 — Give `bridges/`'s undocumented modules a documented home.**
CLAUDE.md's "Bridge System" table documents exactly 11 encoders (magnetic, light, sound, gravity, electric, wave, thermal, pressure, chemical, consciousness, emotion). `bridges/` actually contains ~35+ additional modules — `biomachine_encoder.py`, `community_encoder.py`, `coop_encoder.py`, `cyclic_encoder.py`, `hardware_encoder.py`, `neuromorphic_bridge.py`, `resilience_encoder.py`, `reservoir_bridge.py`, `memristive_bridge.py`, `vortex_bridge.py`, `magnetic_comparator.py`, `physics_guard.py`, `sensor_suite.py`, the `*_alternative_compute.py` family, and more — none mentioned in CLAUDE.md's architecture section at all. A contributor reading CLAUDE.md would have no idea these exist. Recommend either (a) extending CLAUDE.md's Bridge System table to at least list every file with a one-line description, or (b) moving the undocumented long tail into `bridges/extended/` so the 11 "canonical" encoders stay the obvious, easy-to-find entry point CLAUDE.md describes.

**4.4 — Give the giant root-level essay `.md` files a home under `docs/` or a new `theory/`.**
Root currently holds, alongside the real tooling config files (`CLAUDE.md`, `README.md`, `LICENSE`, `CITATION.cff`, `requirements.txt`, `pyproject.toml`), a long list of large narrative documents: `Sovereign.md` (35KB), `Six-sigma.md` (21KB), the four `Universal-geometric-intelligence-P1..P4.md` files (55KB/45KB/48KB/80KB), `Negentropic.md`, `Todo.md` (74KB), `alternative_computing_bridge.md`, etc. This makes the root directory listing (40+ loose files) hard to scan for someone looking for the handful of files that actually matter for setup (README/CLAUDE/LICENSE/requirements/pyproject). Recommend a `theory/` subdirectory for the narrative essays, leaving root to genuine project-root files (config, license, top-level entry-point docs).

**4.5 — Subdivide `experiments/`.**
`experiments/` already contains 100+ files spanning genuinely reusable infrastructure (`solvers/` — already its own subdirectory, a good model to copy), one-off demo scripts (`demo.py`, `demo_multi.py`, `demo_recursive_learning.py`, `demo_v2_learning.py`, `demo_all_langs.py`), several dispatcher variants (`dispatcher.py`, `dispatcher_v2_energetic.py`, `emotion_substrate_dispatcher.py`, `comfort_layer_dispatcher.py`), and this session's additions (`bridge_catalog.py`, `exploration_engine.py`, `gb_explorer.py`, `simd_rf_proximity.py`, `hom_interference_node.py`, `rhombohedral_phase_menu.py`, `rhombo_sc_bridge.py`). Recommend grouping by theme the same way `solvers/` and `silicon_speculative/` already are — e.g. `experiments/dispatchers/`, `experiments/bridges_meta/` (for the bridge-exploration tools) — so a contributor can tell at a glance which of the 100+ files are related.

**4.6 — Settle (or explicitly document) the top-level capitalization split.**
`Engine/`, `GEIS/`, `GI/` are capitalized; `bridges/`, `docs/`, `examples/`, `experiments/`, `fabrication/`, `scripts/`, `sensing/`, `symbols/`, `tests/`, `atlas/`, `mappings/` are lowercase — a straightforward PEP8 violation (Python packages should be lowercase) for the capitalized three, but renaming them now would break every existing `import Engine...`/`from GEIS...` statement, git blame history, CI, and every doc that references them by their current case. Recommend *not* renaming, but adding one sentence to CLAUDE.md's "Code Conventions" table acknowledging this is a known historical inconsistency frozen in place rather than an oversight, so it stops looking like something a new contributor should "fix" as a first PR.

---

### 5. Limitations Mitigation Checklist

**5.1 — Symbolic–Subsymbolic Gap: PARTIALLY ADDRESSED.**
Every bridge encoder extracts genuine closed-form logical structure — e.g. `bridges/electric_encoder.py:82` (`coulomb_force`), `bridges/thermal_encoder.py:69` (`stefan_boltzmann_radiance`) — as literal, importable Python functions with docstrings stating the equation, not black-box numeric approximations. `fabrication/substrate_ir.py` is a genuine symbolic bond-graph IR. But none of this is wired to an actual symbolic engine (no `sympy`, no `z3`, no CAS anywhere in the repo — verified by grep). "Logical form" exists only as hand-written Python, so an identity like the one this session's `experiments/gb_explorer.py` demo found (octahedral inversion ≡ bitwise complement) was checked by running one sample input plus a hand-written comment arguing the general case, not machine-proven.
**Recommendation:** pick one high-value invariant (the octahedral-inversion identity is a good first candidate, since it's a clean closed 3-bit case) and encode it in `sympy` as an actual proof obligation:
```python
from sympy import symbols, Eq, simplify
i = symbols('i', integer=True)
# 7 - i == i XOR 0b111 for i in 0..7 -- verify symbolically over the finite domain
assert all((7 - k) == (k ^ 0b111) for k in range(8))  # today's level of rigor
# a sympy/z3 bit-vector proof would generalize this to n-bit space, not just 0..7
```

**5.2 — Grounding Problem: PARTIALLY ADDRESSED.**
No dimensional-analysis enforcement anywhere (3.6) — units are convention (variable-name suffixes), not runtime-checked. Lower-layer constraints *are* enforced, but only for `fabrication/`'s claims: `fabrication/passes/drift_gate.py` implements a real GREEN/YELLOW/RED classifier comparing measured vs. predicted values against `threshold_green`/`threshold_yellow` per claim. There is no equivalent meta-grounding flag distinguishing measured-vs-theoretical for the root `CLAIM_TABLE.json`, nor for the large body of speculative theory documents (`Silicon/`, `geometric_intelligence/`, the `Universal-geometric-intelligence-P1..4.md` essays, `Sovereign.md`) — nothing marks those as "revolutionary/unverified" the way `drift_gate.py` marks a RED claim as "model invalid for this regime."
**Recommendation:** add a `grounding_status: "measured" | "derived" | "speculative"` field to `CLAIM_TABLE.json` entries (mirroring `drift_gate.py`'s pattern) and apply it repo-wide, not just in `fabrication/`.

**5.3 — Semantic Ambiguity: PARTIALLY ADDRESSED.**
`BRIDGE_GLOSSARY.md` is a real, working answer to "are vague terms quantified" — it maps in-repo jargon (`substrate-primary cognition`, `claim table`, `constraint geometry`) to canonical academic terms. But `CLAIM_SCHEMA.py`'s `TABLE_FIELDS = ("rates", "bounds", "cond", "rel", "fail", "meas")` has no scope/reference-class field (2.3) — nothing in the claim schema itself states the temporal/spatial/ontological scope a given claim applies under, despite `PREDICTION_PROTOCOL.md` explicitly arguing domain-scoping is mandatory for predictions ("No aggregate 'AI accuracy' score across domains is meaningful").
**Recommendation:** add a seventh `scope` field to `TABLE_FIELDS`, populated from the same `domain` concept `PREDICTION_PROTOCOL.md` already requires for predictions.

**5.4 — Falsifiability Paradox: ADDRESSED (for the fabrication subsystem) — the strongest-covered item on this checklist.**
This is real, working infrastructure, not aspirational prose: `FALSIFIABILITY_NOTICE.txt` gives a literal refutation procedure with a concrete verdict ladder (pass/drift/fail), `fabrication/passes/drift_gate.py` is a real, runnable GREEN/YELLOW/RED classifier (verified by reading it — `evaluate_drift(claim, measurement)` at line 24 is not a stub), and every claim in `CLAIM_TABLE.fab.json` carries a `failure` field naming specific physical causes for disagreement — a genuine escape-hatch-detector in the sense the checklist means (it forces "why would this be wrong" to be answered up front, per claim, rather than after the fact). The gap: this machinery is scoped entirely to `fabrication/`'s claims. The root `CLAIM_TABLE.json` and the large body of narrative-theory markdown have no equivalent enumerable refutation-observation set.
**Recommendation:** extend `drift_gate.py`'s pattern (or a thin wrapper around it) to cover `CLAIM_TABLE.json` claims too, since the machinery already exists and works.

**5.5 — Formal Verification vs. Complexity: PARTIALLY ADDRESSED.**
No formal proof system exists anywhere in the repo (no `sympy`/`z3`/`Coq`/`Lean` — verified by grep); "proof" in practice means "a test passed" or "a spot-checked numeric match," which is a reasonable, explicitly-scoped choice for a stdlib-only project, not a hidden gap — the repo doesn't claim otherwise. `PREDICTION_PROTOCOL.md`'s `probability_estimate`/`confidence_interval`/expected-calibration-error (ECE) design is a genuine, well-thought-out probabilistic-fallback-with-confidence schema. The gap: it's a documented *schema* — repo-wide grep found no module that actually computes the ECE formula the doc defines (`ECE = sum_b |confidence_b - accuracy_b| * (n_b / N)`); nothing currently turns a logged prediction track record into a computed calibration score.
**Recommendation:** add a small `score_calibration.py` (root or `scripts/`) that reads a track-record JSON matching `PREDICTION_PROTOCOL.md`'s schema and actually computes ECE, closing the gap between the documented protocol and running code.

---

### 6. Discoverability & Crawler Optimization

| Item | Status | Notes |
|---|---|---|
| Concise "What is this?" summary | ✅ Present | `README.md` opens with a clear one-paragraph "What this is." |
| Repository topics (GitHub metadata) | ⚠️ Cannot verify from repo contents | GitHub Topics are repo-settings metadata, not a file — check via Settings → Topics. |
| `KEYWORDS.txt`/`.md` | ❌ Missing | `CITATION.cff` already has a clean keyword list to reuse. |
| `CITATION.cff` | ✅ Present | Complete, but its `license: CC0-1.0` conflicts with root `LICENSE` (see 1.1) — fix that first. |
| "Why This Matters" | ✅ Present | README's "🌟 Why This Matters" section. |
| Structured metadata (YAML frontmatter/JSON-LD) | ❌ Missing in markdown | `metadata.json` exists as a separate file but isn't embedded as frontmatter in `README.md`. |
| Clear public API import example | ⚠️ Present but wrong | `from geometric_bridge import FieldSolver` doesn't exist (1.6) — needs a real replacement. |
| Open license clearly marked | ⚠️ Marked but contradictory | Four different values across four files (1.1) — worse than missing, since automated license detectors will read `LICENSE` and report MIT regardless of stated intent. **Fix this first; it undermines every other discoverability claim.** |
| GitHub Pages / docs site | ❌ Missing | No `_config.yml`/`mkdocs.yml`/`gh-pages` index found. Optional — CLAUDE.md/README.md already serve much of this role. |
| Anonymous feedback mechanism | ❌ Missing | `.github/` has only `workflows/`, no `ISSUE_TEMPLATE/` — notable since `FALSIFIABILITY_NOTICE.txt` explicitly asks readers to "report discrepancy as a GitHub issue with evidence" with no template to structure that. |

**Ready-to-paste snippets for the missing items:**

`KEYWORDS.md` (new file, root):
```markdown
# Keywords

public-domain, cc0, falsifiable, stdlib-only, bond-graph, cross-substrate,
geometric-encoding, octahedral-coordination, substrate-primary-cognition,
constraint-geometry, claim-table, gray-code, sp3-hybridization,
electromagnetic-field-solver, SIMD-optimization, geometric-algebra,
physics-grounded-verification
```

`.github/ISSUE_TEMPLATE/claim_refutation.md` (new file):
```markdown
---
name: Claim refutation
about: Report a measured value that disagrees with a CLAIM_TABLE prediction
title: "[refutation] "
labels: falsifiability
---

**Claim ID / file:** (e.g. CLAIM_TABLE.fab.json entry, or CLAIM_TABLE.json line)

**Predicted value / tol_frac:**

**Measured value:**

**Raw evidence:** (CSV / WAV / photo attached)

**Environment notes:** (equipment, temperature, calibration state)

**Verdict per FALSIFIABILITY_NOTICE.txt ladder:** pass / drift / fail
```

YAML frontmatter for `README.md` (prepend):
```yaml
---
title: Geometric-to-Binary Computational Bridge
license: CC0-1.0
keywords: [bond-graph, cross-substrate, geometric-encoding, falsifiable-claims, octahedral-coordination]
---
```

Corrected public-API one-liner for `README.md`'s "Research Integration" section:
```python
from bridges.thermal_encoder import ThermalBridgeEncoder

encoder = ThermalBridgeEncoder()
encoder.from_geometry({"temperature_K": [300.0, 350.0, 400.0]})
bits = encoder.to_binary()
```

---

## Confirmation

`REVIEW.md` has been created at the repository root with all six sections above.
