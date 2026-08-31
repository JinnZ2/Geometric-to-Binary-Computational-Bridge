# META-PROTOCOL.md

**The operating manual for the pattern used across this repository and its
siblings (`Simulators`, `curly-octo-happiness`).** It states what happens when a folder is dropped in, the five steps
that turn it into three documents, the templates those documents use, and the
principles the work is committed to.

It is written so that the pattern can be run **without the model that
established it** — by a collaborator, by a student, by a different AI, or by
the author in a later session. If you are picking this up cold, Part 4 is the
entry point and Part 5 is the exit test.

---

## PART 0 — WHERE THIS SITS

This repository already carries most of the machinery this protocol describes,
in executable form. The protocol is the **human-side procedure**; those tools
are the parts of it that got mechanised.

| protocol step | mechanised as |
|---|---|
| step 1, system boundary | `claims_index.py` — classifies every claim id by what can make it FAIL |
| step 2, load-bearing anchor | nothing; this is the read that stays a read |
| step 3, epistemic states | `CLAIMS_REGISTER.json` — statement, whether it holds, why not, cause of death, salvage |
| step 4, falsifiers | `playground/playground.py` — `broken()` and `null()` are the two gates |
| step 5, scope boundary | `repo_guard.py` — null harness, symmetry veto, instrument reach, collisions |
| recurring shapes | `PRINCIPLES.json` — 11 failure shapes, promoted only at two independent instances |
| what the killing bought | `graveyard.py` — screens ranked by reach |
| the archive as one space | `explore.py` — screens × families, and the empty cells |

Read `playground/README.md` for the two gates, and `AI_INDEX.json` first if
you are a model. Where this file and a running check disagree, **the check
wins** and this file is the thing that gets corrected — that is principle 4
applied to the protocol itself.

---


## PART 1 — CLASSIFICATION: WHAT HAPPENS WHEN A FOLDER IS DROPPED

Five steps, in order. Each produces a specific artifact. Recognise them when
they happen; run them yourself when nobody is here to.

### Step 1 — The system boundary audit

**Do:** read the folder and ask *what does this claim to be about, and what
does it actually contain?* Separate:

- **executable code** — runs, produces output
- **build specifications** — need an external engine or dataset not present
- **scaffolds** — structure with no data in it
- **audits** — tools that inspect something else
- **markers** — a named mechanism with nothing quantified

**Produce:** the opening statement of `CLAIM_TABLE.md`, saying what the folder
*is*, not what it claims to be. The form is *"This is an X, not a Y."*

**Yourself:** list every file. For each, ask — does it run, does it produce
output, does it need something that is not here? State the result. No
judgement, only classification.

### Step 2 — The load-bearing, data-independent anchor

**Do:** find the one structural conclusion that holds even if every number is
missing. In `Silicon/keating_cluster.py` it was that Keating is a sum of
squares, so it has one minimum and not eight — true before any optimiser runs.
In `GEIS/gies_core.py` it was that `outer(v, v)` cannot see the sign of `v`,
so an antipodal state table collapses. In `Silicon/er_bounds.py` it was the
Orbach screen: compare the crystal-field gap to `kT` and the coherence claim
is settled in two lines with no apparatus.

**Produce:** a `CLAIMS_REGISTER.json` entry naming the anchor and why it holds.

**Yourself:** state the core claim. Ask whether it follows from structure or
from data. If from structure, name it — those are the claims that transfer to
other domains, and they are what `graveyard.py screens` ranks by reach. If from
data, mark it `UNMEASURED` and do not soften that.

### Step 3 — The epistemic state inventory

**Do:** read every parameter, assumption and variable. For each ask — is it
quantified, is it measurable, is it measured? Classify:

| state | meaning |
|---|---|
| `MEASURED` | a value exists and is in the folder |
| `UNKNOWN_ATM` | the mechanism is known to exist; no current value is available |
| `UNDER_STUDY` | data collection is in progress |
| `NOT_STUDIED` | the mechanism is recognised; no measurement has been attempted |
| `UNDEFINED` | the variable has no agreed definition or measurement protocol |
| `UNMEASURED` | no value available; the cell is a gap |

**Produce:** one research gap per unquantified variable, in
`UNDERGRADUATE_RESEARCH_GAPS.md`.

**Yourself:** for each item, ask — is there a value here? in the literature?
is it even defined? An absent value and a value known to be zero are different
states and must never share a cell.

### Step 4 — The falsifier-locked research prompts

**Do:** every gap gets a defeater — the condition that settles it. Each gap
carries a knowledge state, a research question, a **falsifier**, a data source,
a method, and an expected deliverable.

**Produce:** a complete `UNDERGRADUATE_RESEARCH_GAPS.md`, typically 10–20 gaps.

**Yourself:** name the data source explicitly (*USGS gage records*, *NBI
inventory*), the method explicitly (*extract impervious surface area from
NLCD*), and the deliverable explicitly (*a calibrated urban increment
fraction*). A falsifier that cannot be checked is not a falsifier.

### Step 5 — The scope boundary document

**Do:** read the folder for assumptions that are **institutional rather than
physical**. Ask: what was treated as out of scope that the physics cares about?
Six fallacy shapes recur:

| # | shape | domain examples |
|---|---|---|
| 1 | *X as default* | additive, selection, channel, improvement |
| 2 | *Y as detail* | version, schedule, bounding box, call window |
| 3 | *Z as independent* | procedure gap, held constants, false alarm |
| 4 | *W as complete* | cognitive load, static model, desk-worker |
| 5 | *V as neutral* | medium, reading, estimator, org chart |
| 6 | *U as optional* | anchor, bridge, rejections, hard constraints |

**Produce:** `SCOPE_BOUNDARY.md` naming the six in this folder's domain and
saying why the framework refuses each.

**Yourself:** for each excluded thing ask whether the physics cares. If it
does, name the fallacy and include the mechanism.

---

## PART 2 — THE OUTPUT TEMPLATES

Copy these. They are also what a second AI should be handed.

### `CLAIM_TABLE.md`

```markdown
## CLAIM_TABLE.md

Claims about the delivered `<folder>/` folder, about what a <environment> can
establish concerning it, and about the <protocol> it inherits.

This is a <classification>, not a <opposite>. <one sentence on what it is>

---

## REFUTATION_PROTOCOL

Every claim names what would refute it. A failed check updates the claim,
never the delivered design.

| id | claim | status |
|---|---|---|
| `XXX_001` | <first claim> | SUPPORTED / UNVERIFIED / REPAIRED / REFUTED |
| `XXX_002` | <second claim> | ... |
```

`id` rules: the prefix must be **unused anywhere else in the repository**, and
the number must mean the same claim in every file that cites it. Two folders
sharing a prefix makes both uncitable.

### `UNDERGRADUATE_RESEARCH_GAPS.md`

```markdown
## UNDERGRADUATE_RESEARCH_GAPS.md

Open questions in the <folder> framework, organized by discipline.

Every gap here is a research question with a knowledge state, a falsifier, a
data source, a method, and an expected deliverable.

---

### 1. <GAP TITLE> — <brief description>

**Gap:** <what is unknown>

**Knowledge state:** `NOT_STUDIED`

**Research question:** <the question>

**Disciplines:** <list>

**Data sources:** <list>

**Method:** <steps>

**Expected deliverable:** <what is produced>

**Falsifier:** <the condition that closes the gap>
```

### `SCOPE_BOUNDARY.md`

```markdown
## SCOPE_BOUNDARY.md

Why this framework is broader than standard <domain> practice.

---

### The Problem

<one paragraph: the institutional boundary the physics does not respect>

---

### Six Ways the Connection Gets Lost

#### 1. The "<NAME>" Fallacy

<what the fallacy is>  <why it is one>  <what the framework does instead>

#### 2. ... (through 6)

---

### What This Framework Does Differently

<mechanisms the framework keeps that standard practice drops>

---

### The Knowledge-State Vocabulary

<the Step 3 table>

---

### What Is NOT a Valid Epistemic State

`<INSTITUTIONAL_CATEGORY>` is not a knowledge state. If a mechanism physically
influences the system, excluding it because <reason> is a scope error, not an
epistemic one.

---

### The Standard

The question should not be:

> "<institutional question>"

But rather:

> "<physical question>"

If the answer is yes, it belongs in the model.
```

---

## PART 3 — THE DEEP PRINCIPLES

Commitments, not methods.

**1. The physics does not care about our boundaries.** The first question is
always whether the mechanism physically influences the system. Institutional
boundaries are administrative facts about who pays, not about what acts.

**2. Gaps are the map.** A map is not finished when every cell is filled. It is
finished when every gap is marked with what would move it. The unmeasured cell
is the information.

**3. Every claim names its falsifier.** A claim with no falsifier is not a
claim. The falsifier is the boundary of the claim, and a claim that survives
one is stronger than a claim nobody tested.

**4. The instrument audits itself.** The later instrument turns on the earlier
one. Ship the check with the scaffold. A scorer that cannot fail is not a
scorer — see `null-harness/`.

**5. Absent is not zero.** *No value*, *checked and found absent*, and *not
searched* are three states. Collapsing any two of them is the single most
frequent defect in this repository, and it has been found and repaired more
than a dozen times at different sites.

**6. The field is one system.** Temperature, wind, water, terrain, season,
animal behaviour, human signals — read as one field, not as a sequence of
narratives. The repository is the field map.

---

## PART 4 — HOW TO RUN THIS

**With a model in session.** Point it at the folder, say *follow
META-PROTOCOL.md*, review the three documents, correct, iterate, next folder.

**With another AI.** Paste this file in. Same instruction. It needs nothing
else — that is the file's design requirement.

**Yourself.** Work Part 1 step by step, filling the Part 2 templates, and use
Part 5 as the exit test.

---

## PART 5 — THE CHECKLIST

A folder is **not processed** until every line passes.

**Documents**

- [ ] `CLAIM_TABLE.md` exists; every claim is `SUPPORTED`, `UNVERIFIED`,
      `REPAIRED` or `REFUTED`, and **no claim row has an empty status cell**
- [ ] every `SUPPORTED` claim names a falsifier
- [ ] `UNDERGRADUATE_RESEARCH_GAPS.md` exists with 10–20 gaps
- [ ] every gap carries a falsifier, data source, method and deliverable
- [ ] `SCOPE_BOUNDARY.md` exists and names six fallacies

**Identifiers**

- [ ] the claim-id prefix is unused by any other folder in the repository
- [ ] each id means the same claim in the folder's canonical table and in
      every document that restates it — a restatement that renumbers makes
      every cross-reference ambiguous
- [ ] cross-referenced folders and claim ids **resolve**; a named-but-absent
      artifact is recorded as absent rather than assumed to exist

**Markup**

- [ ] headings are `#`/`##`/`###`, not plain lines
- [ ] tables are pipe tables, not space-separated columns
- [ ] lists use `-`, not `·`
- [ ] no truncated lines, no unterminated code spans, no retrieval-tool
      artifacts (`【…】`, `[N†L…]`)

**Code**

- [ ] `python repo_guard.py` passes — null harness, symmetry veto, instrument
      reach, and the collision stage
- [ ] `python claims_index.py status` shows nothing recorded `live` that
      nothing in the tree can falsify
- [ ] `python claims_index.py salvage` — every `dead` claim records what
      survives it; a death with no salvage is a deletion, not a lesson
- [ ] `python playground/review.py` exits zero — the archive still describes
      reality, and no candidate survives by having loosened its own tolerance
- [ ] `python playground/principles.py resolve` exits zero — every principle
      instance points at a path that exists
- [ ] a statistical claim ships a `null()`; a claim of any kind ships a
      `broken()` its own checks reject
- [ ] stdlib-only, or the dependency is declared (`requirements.txt`;
      `numpy`/`scipy` tiers are stated per module)
- [ ] the suite actually runs — a test class defined after
      `unittest.main()` never executes and the suite still reports OK

**Discipline**

- [ ] no real-world value supplied from memory — a figure is either fetched,
      cited, or `UNMEASURED`
- [ ] delivered files are landed verbatim; corrections live in the audit
- [ ] absent, zero, and not-searched are three distinguishable states

---

## PART 6 — WHERE TO PUT THIS

Post it at the root of each repository, or once centrally with each repository
linking to it. Hand it to collaborators so they know the pattern, to students
so they know what they are building, and to a future model so the work
continues without the session that started it.

---

## APPENDIX — THE SIX FALLACIES, QUICK REFERENCE

| # | fallacy | reads as | actually is |
|---|---|---|---|
| 1 | X as default | the ordinary case | one option among several, chosen and unmarked |
| 2 | Y as detail | an implementation matter | the variable the result turns on |
| 3 | Z as independent | a competing explanation | a downstream readout of the same cause |
| 4 | W as complete | the whole picture | the part the instrument reaches |
| 5 | V as neutral | a transparent medium | an instrument with its own response |
| 6 | U as optional | a nice-to-have | the precondition the rest rests on |

---

CC-BY-4.0, matching the repository. No claim in this file is a claim about the world; it is a claim about how
to write claims about the world, and it is refuted by a folder processed
correctly against it that still misleads a reader.
