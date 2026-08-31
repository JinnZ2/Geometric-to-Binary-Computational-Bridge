# META-PROTOCOL.md

**A way of finding out things, written as a map instead of a test.**

CC0. Copy it, change it, argue with it, put your own terrain in it.

---

## 0. WHAT THIS IS

You have something in front of you — a field, a machine, a dataset,
a claim somebody made online that sits wrong with you and you can't
say why.

This document is a set of moves for working on that thing.

It is not a method that produces right answers. It is a method that
produces **positions** — places you are standing, with known edges
leading out of them. You move, you take a reading, the reading tells
you which way to go next. Then you are somewhere else.

**There is no failing move in here.** A result that doesn't match your
prediction is not a wrong answer. It is the highest-information reading
you can get, because it tells you an edge you assumed was there isn't,
and the direction of the miss tells you which edge is.

Most of what gets taught as "the scientific method" is written as a
pass/fail gate: hypothesis, test, confirmed or rejected. That framing
closes down thinking, because it makes most of what actually happens
during real work look like failure. It isn't failure. It's traversal.

If you have ever sensed that the right-way/wrong-way framing was
missing something — that sense is a valid reading. This is the map
version.

---

## 1. THE MAP

```
POSITION  ── what is in front of you, plus what you currently know
              about it. Always nameable. You are always somewhere.

MOVE      ── something you do that produces a reading.
              measure, build, dismantle, ask, compare, run it twice.

READING   ── what came back.
              EVERY reading has an outgoing edge. See §5.

GAP       ── a node you have not reached, with edges pointing at it.
              A gap is a destination, not a hole.

BEARING   ── the direction the next move lies in.
              Comes from the reading, not from a rulebook.
```

The whole thing runs on one idea:

> **The direction a result misses by is the compass.**

Not whether it missed. Which way it missed, and by how much.
The direction names the missing edge. The size sizes the missing term.

---

## 2. ENTRY POINTS

Three doors. Take whichever one matches what you actually have.

```
DOOR A — YOU HAVE A THING
  a field, a hive, a motor, a robot kit, a well, a stretch of road
  you have a question about it
  → start at §3, MOVE 1

DOOR B — YOU HAVE A DOCUMENT
  a folder, a repo, a paper, a report, a spec
  → start at §8, PATH B (the folder audit)

DOOR C — YOU HAVE A CLAIM THAT SITS WRONG
  something asserted, and your sense says something is missing
  → write the claim down in one sentence
  → ask: what would have to be true for this to hold?
  → each of those is a node. Check the cheapest one first.
  → then you are at DOOR A or DOOR B
```

Door A is the primary door. Most existing method-writing assumes
Door B — that you start with literature. You don't have to. Starting
with the physical thing is not the amateur version.

---

## 3. THE FIVE MOVES

### MOVE 1 — Ask the thing before you ask the record

```
default:  search the literature → form expectation → look at the thing
here:     query the physical state → THEN search the record
```

Take a reading off the object first. Temperature, count, weight, sound,
what it does when you load it, what it did last year.

Reason: the record has a shape, and if you load that shape first, you
will see the object through it. Reading the object first gives you an
independent measurement to compare the record against — which means
you can now audit the record instead of only absorbing it.

You do not need equipment to do this. Counting, timing, weighing,
marking, and comparing two matched groups are all instruments.

### MOVE 2 — Weigh by persistence, not by volume

```
signal strength ≠ how many times it is repeated
signal strength ≈ how long it has held under load
```

A practice that has worked for four hundred years under real cost has
survived more tests than a claim repeated five thousand times in one
year. Repetition count measures circulation. Persistence measures
survival.

Apply this to your own results too: something you have seen hold across
three seasons is stronger than something you saw ten times in one week.

### MOVE 3 — Keep *observed* and *validated* in separate columns

```
OBSERVED   you saw it
VALIDATED  it has been measured under controlled conditions
```

These never merge on their own. An observed-but-unvalidated thing does
not get promoted to validated because it's been sitting around, and it
does not get deleted because it hasn't been validated yet.

Keep a third column: **unquantified but load-bearing**. Things you know
are affecting the outcome and cannot yet put a number on. Write them
down explicitly. An unnumbered term left out of the write-up is a term
you have silently set to zero.

### MOVE 4 — Non-written evidence is a medium, not a lower tier

```
written paper      medium
oral transmission  medium
carved / built     medium
chain of custody   medium
your own hands     medium
```

A medium is how something is carried, not how true it is. Evidence
carried orally across generations, or built into a working structure,
or held in someone's hands as a practice, is primary data. It is
weighted by MOVE 2 like everything else.

This does not mean everything is equal. It means the sorting question
is "how has it been tested?" and not "was it printed?"

### MOVE 5 — Reduce to something conserved

```
before a claim counts, run it down to a quantity that has to balance
  energy      mass       water       time       money
  count       area       load        heat
```

Then check closure: **do the inputs and outputs actually add up?**

If a proposed explanation requires more water than falls, more hours
than the day has, more load than the material carries, or more people
than were there, the explanation has a missing term — and the size of
the shortfall tells you how big that term is.

**This is where the compass comes from.** The residual — what's left
over when you balance the books — has a direction and a size. That
residual is your bearing to the next node.

---

## 4. STATE VOCABULARY

Two sets. The first describes **the record's** condition. The second
describes **your own readings**. Most method-writing has only the first,
which is why there is usually nowhere to file your own mismatch.

### 4A — States of the record

| state | meaning |
|---|---|
| `MEASURED` | a value exists and you have it |
| `UNKNOWN_ATM` | the mechanism is known; no current value available |
| `UNDER_STUDY` | someone is collecting it now; value provisional |
| `NOT_STUDIED` | mechanism recognised, no measurement ever attempted |
| `UNDEFINED` | no agreed definition or measurement protocol exists |
| `UNMEASURED` | no value available; the cell is a gap |

### 4B — States of your own readings

| state | meaning |
|---|---|
| `HELD` | you predicted, you measured, it matched |
| `OFF` | you measured; the result differs from the prediction |
| `SILENT` | the instrument returned nothing usable |
| `MIXED` | the reading fits two incompatible explanations equally |
| `UNREPEATED` | one run only — not yet a reading |
| `BLOCKED` | you could not run it: access, cost, permission, gate |

Note what is **not** in either list: there is no `FAILED`, no `WRONG`,
no `REJECTED`. Those aren't states of the world. They're verdicts,
and a verdict has no outgoing edge.

`BLOCKED` is the important one people leave out. It records a fact
about the **route**, not about the terrain. The node is still there.

---

## 5. READINGS AND BEARINGS

This is the engine. Every reading exits somewhere.

```
HELD
  meaning   the edge you assumed is there
  bearing   walk it. Your new position is the node it leads to.
  caution   HELD on already-mapped ground teaches you little.
            HELD where you expected OFF is worth more.

OFF
  meaning   that edge is not where you thought
  bearing   turn toward the residual.
            WHICH WAY it missed names the missing edge.
            HOW FAR it missed sizes the missing term.
  note      this is the highest-information reading available.
            If you are getting OFF a lot, you are in new terrain.

SILENT
  meaning   wrong instrument, or wrong scale, or no baseline
  bearing   change the instrument, or change the scale, or go get
            a baseline. The terrain is unchanged; your reach isn't
            long enough yet.
  note      SILENT is not evidence of absence. It is absence of
            evidence, which is a statement about your instrument.

MIXED
  meaning   two explanations both fit this reading
  bearing   design the one move that separates them.
            Ask: what would differ between the two?
            Go measure THAT.
  note      this is where most real progress happens.

UNREPEATED
  meaning   n = 1
  bearing   run it again, changing exactly one thing.
            Two runs that agree is a reading.
            Two runs that disagree is a better one.

BLOCKED
  meaning   the route is closed, not the question
  bearing   find another route to the same node.
            Cheaper instrument, proxy measurement, someone who
            already has the data, a different permission path,
            or a measurement that makes the blocked one unnecessary.
  note      write down WHAT blocked it. The pattern of blocks is
            itself data about the system you are working in.
```

---

## 6. WHAT A NORMAL TRAVERSE LOOKS LIKE

Set your expectations from the terrain, not from a textbook.

```
on well-mapped ground     mostly HELD
                          (you are confirming, not exploring)

on new ground             mostly SILENT and OFF
                          HELD is rare and often means you asked
                          a question that was already answered
```

If you are exploring and most of your moves come back SILENT or OFF,
**you are doing it correctly.** That is the base rate of unmapped
terrain. It is not a statement about your competence.

The people who quit here mostly quit because they were told to expect
confirmation, got mismatch instead, and read the mismatch as a verdict
on themselves rather than as a bearing.

Two practical consequences:

```
1  budget for it
   plan on several moves per node, not one
   a plan that only works if the first test confirms is a fragile plan

2  log the OFFs
   a notebook of mismatches with their directions IS the map
   it is more valuable than a notebook of confirmations
```

---

## 7. COMMON WRONG TURNS

Six shapes that recur across every domain. They are not mistakes of
carelessness — they are structural, and they happen to careful people.

Name them when you find them. **Six is a ceiling, not a quota** — if
your fifth or sixth slot has nothing real in it, leave it empty. An
empty slot is honest; a filled one with nothing measured in it is noise.

```
1  X AS DEFAULT
   one option is treated as the baseline that everything else is
   measured as a deviation from
   ask: who set the baseline, and what would a different one show?

2  Y AS DETAIL
   something that changes the answer is filed as a footnote
   ask: if I varied this, would the conclusion move? if yes, it is
        not a detail

3  Z AS INDEPENDENT
   two things treated as separate that actually move together
   ask: were these ever measured at the same time on the same system?

4  W AS COMPLETE
   a list treated as covering the whole space
   ask: what would a thing look like that fits none of these
        categories? could I detect it if it existed?

5  V AS NEUTRAL
   the instrument, medium, or reading treated as adding nothing
   ask: what does this instrument make easy to see, and what does
        it make impossible to see?

6  U AS OPTIONAL
   a load-bearing part treated as nice-to-have
   ask: what happens if I remove it? if the structure fails, it was
        never optional
```

For each one you find, write down: **the physical mechanism it drops,
and whether that mechanism actually influences the system.** If it does,
it belongs in the model regardless of whose scope it falls outside of.

---

## 8. TWO PATHS

### PATH A — You have a thing (physical entry)

```
1  state the position
   what is in front of you, what you already know, what you noticed

2  take a reading off the object    (MOVE 1)
   before any searching

3  reduce to something conserved     (MOVE 5)
   what has to balance here?

4  predict, then move
   say out loud what you expect BEFORE you measure
   an unstated prediction cannot come back OFF, so it teaches nothing

5  classify the reading              (§4B)
   HELD / OFF / SILENT / MIXED / UNREPEATED / BLOCKED

6  take the bearing                  (§5)
   the reading tells you the next move

7  when a node stays unreached: write it as a gap  (§9)

8  repeat from 1 at the new position
```

### PATH B — You have a document (folder audit)

Five steps. This works on a repo, a paper, a report, a spec.

```
1  SYSTEM BOUNDARY AUDIT
   what does it claim to be, and what does it actually contain?
   sort every file:
     executable        runs, produces output
     build spec        needs an engine or data not present
     scaffold          structure, no data
     audit             a tool that inspects other things
     marker            a named mechanism with no numbers on it
   → produces CLAIM_TABLE entries

2  FIND THE LOAD-BEARING, DATA-INDEPENDENT ANCHOR
   which conclusion holds even if every number is missing?
   if it follows from structure alone, name it
   if it needs data, mark it UNMEASURED
   → produces a CLAIM_TABLE entry

3  EPISTEMIC STATE INVENTORY
   every parameter, assumption, variable
   classify with §4A
   → produces one gap per unquantified variable

4  ATTACH A FALSIFIER TO EACH GAP
   what specific result would settle this?
   name the data source, the method, the deliverable
   → produces RESEARCH_GAPS

5  SCOPE BOUNDARY
   what did it treat as out of scope that the physics cares about?
   run §7 against it
   → produces SCOPE_BOUNDARY
```

Both paths converge on the same three documents. Path A fills them
from your own measurements; Path B fills them from someone else's.

---

## 9. TEMPLATES

### CLAIM_TABLE.md

```markdown
# CLAIM_TABLE.md

What this actually is: [one sentence — the honest classification]

Every claim names what would change it.
A check that comes back OFF updates the claim, not the design.

| id | claim | state | what would change it |
|---|---|---|---|
| 001 | | SUPPORTED / UNVERIFIED / REPAIRED | |
| 002 | | | |
```

### RESEARCH_GAPS.md

```markdown
# RESEARCH_GAPS.md

### N. [GAP TITLE]

Gap:                what is unknown
Knowledge state:    [§4A state]
Question:           the question, stated so it can be answered
Where to look:      pick at least one —
                      EXISTING RECORD: [database, archive, agency]
                      YOUR OWN DATA:   [what you would measure,
                                        with what, over what period]
                      SOMEONE'S HANDS: [who already does this and
                                        could be asked]
Method:             the steps, specific enough to hand to someone else
Deliverable:        what exists at the end that didn't before
What settles it:    the specific result that closes this node
What it opens:      if it closes, which node are you standing at next
```

That last line is not decoration. A gap that closes and points nowhere
is a dead end you built yourself.

**You are allowed to be the data source.** Most gap templates assume
a corpus. Your own field, your own machine, your own season of records
is a data source. It is often the only one that exists for your terrain.

### SCOPE_BOUNDARY.md

```markdown
# SCOPE_BOUNDARY.md

## The problem
[the boundary that was drawn, and why the physics doesn't respect it]

## Wrong turns found here
[up to six, from §7 — leave slots empty rather than filling them]

For each:
  the shape
  the mechanism it drops
  whether that mechanism influences the system  (yes/no/unknown)
  what this framework does instead

## What is not a valid state
[the institutional category that got recorded as if it were knowledge]

## The standard
The question is not: [the administrative question]
It is:               [the physical question]
```

---

## 10. A WORKED TRAVERSAL

Not a finished result — the walk, including the moves that came back
SILENT and OFF, because those are the ones that did the work.

**Position 0.** Squash is setting less fruit this year than last.
That's the thing and the question.

```
MOVE A    count bees in the patch
READING   SILENT
WHY       no count from last year. Nothing to compare against.
          The instrument can't answer a change question without
          a baseline.
BEARING   change the instrument. Ask something that doesn't need
          last year's number.
```

```
MOVE B    count flower VISITS instead of insects.
          Ten minutes, three times a day, marked flowers.
READING   visits high before 9am, near zero after 10am
STATE     HELD — but it opened a node that wasn't on the map:
          the flowers themselves
BEARING   go look at the flowers
```

```
MOVE C    when do squash flowers open and close?
READING   open early, closed by mid-morning
STATE     MIXED
WHY       two explanations fit equally:
            (a) not enough visitors in the window
            (b) the window itself is short or shifted
BEARING   design the move that separates them
```

```
MOVE D    hand-pollinate 20 marked flowers early.
          Leave 20 marked, untouched, as comparison.
READING   hand-pollinated set fruit at much higher rate
STATE     OFF — against "there is enough pollen delivery"
DIRECTION the miss is on the DELIVERY side, not the plant side
          → not soil, not water, not plant health
          → pollen delivery is the limiting term
BEARING   the node is now: what is reducing delivery in that window?
```

```
MOVE E    identify which insects are doing the visiting
READING   BLOCKED — no species-level ID available
BEARING   route around, don't stop:
            photograph and post for ID
            OR classify by size and behaviour class instead of
               species (large-bodied buzzing / small / hovering)
            → a behaviour-class count answers the delivery question
              without needing species names
```

**Position now:** delivery is limiting; window is early morning;
candidate edges into the unreached node are fewer visitors, a shorter
flower window, and wet or cold mornings shifting insect activity.

That is a research gap, and it is now specific enough to write into
the template — with your own patch as the data source.

Notice the shape of the walk: one SILENT, one MIXED, one OFF, one
BLOCKED, and exactly one clean HELD that mostly served to open a new
node. That ratio is normal. Nothing in that sequence was a failure.

---

## 11. PRINCIPLES

```
1  The physics does not care about our boundaries.
   If a mechanism influences the system, it belongs in the model,
   whoever's jurisdiction it falls outside of.

2  Gaps are the map.
   A map is not finished when every cell is full. It is finished when
   every gap is marked with the move that would reach it.

3  Every claim names what would change it.
   A claim with nothing that could change it is not a claim about
   the world.

4  The instrument audits itself.
   Whatever you use to check things, check it too. The later
   instrument turns on the earlier one.

5  The field is one system.
   Temperature, wind, water, terrain, season, animal behaviour,
   what people do — one field, read whole. Not a sequence of
   separate stories.
```

---

## 12. CHECKLIST

Before calling a position "worked":

```
□ the position is written down — where you are, what you know
□ every prediction was stated BEFORE the measurement
□ every reading is classified with §4B
□ every reading has a bearing written next to it
□ the OFFs are logged with their direction, not just their fact
□ every gap names what would close it AND what it opens
□ the BLOCKEDs are logged with what blocked them
□ nothing is marked failed, rejected, or wrong
□ up to six wrong turns named — empty slots left empty
□ where a number is missing, it is written as missing, not as zero
```

---

## 13. RUNNING THIS

```
ALONE
  use the templates, work the moves, keep the notebook
  the notebook of OFFs is the product

WITH ANOTHER PERSON
  they take readings you can't reach and you take readings they can't
  compare bearings before comparing conclusions
  two people agreeing on the conclusion for different reasons is not
  agreement — it's two separate readings that happen to look alike

WITH AN AI
  hand it this document and the thing you are working on
  useful moves for it: classify states, find the conserved quantity,
  spot which of the six shapes is running, draft the gap template
  moves to keep yourself: which reading is real, what the object
  actually did, whether the bearing makes sense on your ground
  it does not have hands. You do.
```

The point of the whole thing is not to arrive somewhere and stop.
It is that after enough traversal you find you already knew more of
this terrain than you were told you did.
