# RESEARCH_RENDER.md

**The schema behind the worked instances — so any gap in any folder
can be rendered into something someone can pick up and run.**

CC0.

---

## 0. WHERE THIS SITS

```
META-PROTOCOL.md      how to find and traverse a gap
                      physical entry, map, bearings, base rates
                      → produces: a gap, positioned, with edges

RESEARCH_RENDER.md    how to render a found gap so someone with
(this file)           a lab, a semester, and no context can start
                      → produces: three documents

worked instances      nonidentity-census/, divergence-playground/
                      → what the output looks like when filled
```

Same spine, two densities. The map is the door. This is what a gap
looks like once it has been walked far enough to hand off.

---

## 1. THE THREE DOCUMENTS

Every rendered folder produces exactly these:

```
CLAIM_TABLE.md      what is actually here, and what would change it
RESEARCH_GAPS.md    what is not here, and how to go get it
SCOPE_BOUNDARY.md   what got left out, and whether the physics
                    cares that it did
```

They are not summaries of each other. Claim table faces the delivered
thing. Gaps face forward. Scope boundary faces the field the thing
sits in.

---

## 2. CLAIM_TABLE.md

### Shape

```markdown
# CLAIM_TABLE.md

Claims about the delivered [folder]/ folder, about what a [environment]
can establish concerning it, and about the [protocol] it inherits.

**This is a [honest classification], not a [what it might be mistaken
for].** [One or two sentences stating plainly what is and is not here.]

---

### REFUTATION_PROTOCOL

Every claim names what would change it. A check that comes back OFF
updates the claim, never the delivered design.

| id | claim | status |
|---|---|---|
| `[PREFIX]_001` | **[claim]** | **[STATUS]** |
```

### Rules

```
ID SCHEME
  three-letter folder prefix + sequence
  NID_001, DP_001
  ids are permanent. A superseded claim keeps its id and changes
  its status. Never renumber.

STATUS SET  (this is CLAIM STATUS, not knowledge state — see §5)
  SUPPORTED    the claim holds as stated
  UNVERIFIED   stated, not checked, and the reason is named
  REPAIRED     was OFF, the cause was found, the fix is in

THE OPENING CLASSIFICATION LINE IS LOAD-BEARING
  it states what the thing IS before anyone can mistake it for
  something else. "a marker, not a measurement."
  "an instrument, not a measurement of any real fork."
  Write this first. If it is hard to write, the folder is not
  ready to render.

SELF-INDICTING CLAIMS GO FIRST
  the strongest claim table opens with what the thing does wrong.
  NID_001: the detector built to escape lexical detection decides
           83% of cases lexically
  DP_002:  the XOR is not a cryptographic seal
  This is not modesty. It is the claim table doing its job — an
  audit that only reports success has not audited anything.

WHAT NEVER RAN, SAYS SO
  NID_009: the command was never executed, the network was refused,
           the date is given
  Code written and never run is UNVERIFIED with the reason attached,
  not quietly presented as a tested path.

STANDING CLAIMS AT THE TAIL
  stdlib-only, runnable, selftest passes
  same two or three every time, last rows
```

### Every claim carries its own refuter

Not in a separate document. If a claim's refuting condition can't be
stated in the same breath, the claim is not yet a claim about the world.

---

## 3. RESEARCH_GAPS.md

### Shape

```markdown
# RESEARCH_GAPS.md

Open questions in the [folder] framework, organized by discipline.

---

### N. [CLASS] — [Gap title]

**Gap:** what is unknown, and why it is unknown rather than just unfilled

**Knowledge state:** `[§5 state]`

**Research question:** stated so that an answer would be recognisable

**Disciplines:** who already has the tools for this

**Data sources:**
  EXISTING RECORD: [database, archive, agency, corpus]
  YOUR OWN DATA:   [what to measure, with what, over what period]
  SOMEONE'S HANDS: [who already does this and could be asked]
  — at least one. Not necessarily the first.

**Method:** numbered steps, specific enough to hand to a stranger

**Expected deliverable:** what exists at the end that didn't before

**Falsifier:** the specific result that settles it

**What it opens:** if it settles, which node are you standing at next
```

### Rules

```
CLASS PREFIXES
  EMPIRICAL       a measurement nobody has made
  METHODOLOGICAL  a procedure nobody has defined
  INSTRUMENTAL    a tool that would have to be built first
  TRANSLATION     a rendering for people outside the field

COUNT
  as many as the folder actually has.
  A folder with four real gaps gets four. Padding to hit ten
  produces the filler failure — see §6.

THE FALSIFIER MUST BE CHECKABLE
  good:  "ecology does not have a higher non-identity rate than
          economics"
  good:  "the empirical p-value stays unstable at high draw counts"
  weak:  "readers find the guide unhelpful"
         — that is an opinion poll, not a settling condition.
         If a gap's falsifier is somebody's reaction, either
         operationalise it (what measured behaviour changes?) or
         mark the gap UNDEFINED and say so.

WHAT IT OPENS — this line is new and it is not optional
  the worked instances stop at the falsifier. A gap that closes and
  points nowhere is a dead end built on purpose.
  Every gap names the position you occupy once it resolves.

DATA SOURCES ARE NOT REQUIRED TO BE A CORPUS
  the instances lean on OpenAlex, USGS, NBI. Fine where they apply.
  A field, a machine, a season of your own records is a data source
  and often the only one that exists for that terrain.
```

---

## 4. SCOPE_BOUNDARY.md

### Shape

```markdown
# SCOPE_BOUNDARY.md

Why this framework is broader than standard [domain] practice

## The Problem
[the boundary that got drawn, and the physics that ignores it]

## Ways the Connection Gets Lost
[up to six — see rules]

## What This Framework Does Differently
[the mechanisms it carries that standard practice drops]

## The Knowledge-State Vocabulary
[§5 table, only the states actually used here]

## What Is NOT a Valid State
[the institutional category that got recorded as if it were knowledge]

## The Standard
The question is not: [the administrative question]
It is:               [the physical question]
```

### The six shapes

```
1  X AS DEFAULT      one option is the baseline everything else
                     is measured as deviation from
2  Y AS DETAIL       something that moves the answer, filed as
                     a footnote
3  Z AS INDEPENDENT  two things treated as separate that move
                     together
4  W AS COMPLETE     a list treated as covering the whole space
5  V AS NEUTRAL      the instrument or medium treated as adding
                     nothing
6  U AS OPTIONAL     a load-bearing part treated as nice-to-have
```

### Per-shape entry

```
NAME       the shape as it appears in THIS domain
PRACTICE   what gets treated as settled
COUNTER    what the framework found instead
DROPPED    the specific mechanism the practice excludes
INFLUENCE  does that mechanism affect the system?  yes / no / unknown
```

`INFLUENCE` is the load-bearing field. If it's "no", the exclusion was
correct and the shape does not belong in the document.

---

## 5. TWO VOCABULARIES, KEPT SEPARATE

The worked instances mix these, and it is the schema's main defect.
`SUPPORTED` and `NOT_STUDIED` are not the same kind of thing and do not
belong in one table.

```
CLAIM STATUS — the condition of a claim in THIS folder
  SUPPORTED    holds as stated
  UNVERIFIED   stated, unchecked, reason named
  REPAIRED     was OFF, cause found, fix in

KNOWLEDGE STATE — the condition of the RECORD on a question
  MEASURED     a value exists and is available
  UNKNOWN_ATM  mechanism known, no current value
  UNDER_STUDY  collection in progress, value provisional
  NOT_STUDIED  mechanism recognised, never measured
  UNDEFINED    no agreed definition or protocol
  UNMEASURED   no value; the cell is a gap

READING STATE — the condition of YOUR OWN measurement
  (from META-PROTOCOL §4B — HELD / OFF / SILENT / MIXED /
   UNREPEATED / BLOCKED)
```

```
CLAIM_TABLE     uses CLAIM STATUS
RESEARCH_GAPS   uses KNOWLEDGE STATE
your notebook   uses READING STATE
```

None of the three contains a `FAILED`, `WRONG`, or `REJECTED`.

---

## 6. KNOWN FAILURE MODE OF THIS SCHEMA

The six-shape section will fill itself if you let it. The instances
show the mechanism:

```
a sentence formula gets built —
  "not wrong for X, but may be wrong for Y.
   The Z was causal — just not represented."
— and then run six times whether or not there are six shapes.

nonidentity instance 6, "field as container":
  "not wrong for the field's REPUTATION"
  reputation is not a measured quantity.
  The formula filled its own slot.
```

```
RULE
  six is a ceiling, not a quota.
  An empty slot is a finding. A filled slot with nothing measured
  in it is noise that looks like a finding — which is worse than
  the gap it covered.

TEST
  for each shape, name the DROPPED mechanism and answer INFLUENCE.
  If you cannot name a mechanism, delete the entry.
```

Same rule applies to gap count. Ten to twenty was a target in the
original protocol; a target on a count produces padding.

---

## 7. UNSETTLED

Two things the instances don't resolve. Both are yours to call.

```
NAMING
  the files say UNDERGRADUATE_RESEARCH_GAPS
  the work is described as postgrad-grade
  these recruit different people.
  → pick one, or split: same gap, two entry densities,
    the way META-PROTOCOL and this file split

BILINGUAL RENDER
  both instances are English / 中文, full parallel
  is that per-folder, or does the target language follow the
  terrain the gap sits in?
```

---

## 8. RUNNING IT ON A NEW FOLDER

```
1  write the opening classification line
   "this is a ___, not a ___"
   if it won't write, stop — the folder is not ready

2  list every file, sort it
   executable / build spec / scaffold / audit / marker

3  find the claim that holds with all numbers removed
   that is the anchor. Everything else is downstream of it.

4  walk every parameter and assumption
   assign a KNOWLEDGE STATE to each
   each non-MEASURED one is a candidate gap

5  for each candidate, write the full gap entry
   if you cannot write a checkable falsifier, it is not yet a gap
   — it is a marker. Say so and leave it as one.

6  run the six shapes against the folder's field
   name DROPPED and INFLUENCE for each
   delete every shape you cannot fill honestly

7  write the claim table last
   self-indicting claims first, standing claims last
```

Step 7 last is deliberate. The claim table is the only document that
can be written accurately after the other two, because the gaps and the
scope boundary are what tell you what the folder actually is.
