# oral-record

Status: PROPOSED, co-authored, CC0. One case: a reconstruction from first
principles (Stage A), corrected by an old oral tradition's holder (Stage B),
then rebuilt (Stage C). Not established: any Stage C reading; the bench test
has not run and its outcome slots are VOID.

- `oral_record_case_01.json`: the record (source of truth).
- `oral_record_case_01.md`: rendered from the JSON; never edited by hand.
- `case_check.py`: `--write` renders; bare run checks md == render plus the
  record rules (no identity-bearing keys, origins VOID or allowed, LOST not
  filled, bench outcomes VOID, holder_review VOID per row and record-level,
  links resolve to a gap key, feasibility refs stay CARRIED, observer slots
  null); `--selftest` plants one
  defect per rule.

```bash
python Negentropic/oral-record/case_check.py             # md == render, record rules hold
python Negentropic/oral-record/case_check.py --selftest  # one planted defect per rule; 14 checks
```

## Where this came from

Moved here from the `drift-archive-audit` repository, branch
`claude/oral-record-case`, commit `0ea80af` (which holds `549547c` plus the
holder_review, B1 link and B5 feasibility-ref additions). The JSON, the
rendered `.md` and `case_check.py` are byte copies of that commit; only this
README was added to. The source branch is left in place as the archive.

## The July record this case sits beside

The case's Stage C is dated 2026-07. The same reconstruction is written out
as prose, with its optics and its tests, in the pass of 2026-07-29:

- [`../08-oral-technology.md`](../08-oral-technology.md): the instrument as
  a pole-referenced field polarimeter (calcite analyser, quartz retarder,
  still water, emplaced stone, the Great Bear as finder), a status table,
  and seven discriminating tests T1-T7.
- [`../02-empirical-audit.md`](../02-empirical-audit.md), Claim 5, second
  pass: where "crystal gives direction" was re-read as a calcite
  polarisation compass (Ropars et al. 2012).
- [`../precession.py`](../precession.py): the dating computation that page
  rests on.

How the two records line up. This is a reading made here (DERIVED); the
holder has read neither.

```text
case 01                               08-oral-technology.md           relation
C1 calcite analyzer                   instrument table: Calcite       same element
C2 quartz retarder (color null)       "two-mineral combination"       same element
C3 water = horizon + Brewster         "Still water does four jobs"    July page lists four jobs, the case two
C4 Great Bear -> home latitude        "The datum is the pole, not     same element; July page adds the
                                      the Bear"; test T6              pole-vs-Bear question
C5 emplaced stone = monument          "home stone must be in place"   same element
G1 kit_ordering, 6 orderings,         test T5, six orderings,         same bench test
   bench test not run                 not run
B1 singer carries the stone:          "Sings back": LIVE, test T1     different handling, see below
   NOT_MAPPED; G2 song_routes LOST
B5 moon better than sun:              status table: CLOSED,           different handling, see below
   NOT_MAPPED; "better" UNRESOLVED    with a stated mechanism
```

Two rows are handled differently in the two records, and this move does not
reconcile them:

- **B5.** The July page marks "moon better than sun" CLOSED and gives a
  geometric reason. The case keeps B5 NOT_MAPPED, carries one feasibility
  reference at read depth CARRIED, and leaves "better" UNRESOLVED until
  bench step 5 is run. The case is the stricter of the two; neither has a
  measurement behind it.
- **B1.** The July page treats the carried stone's hum as a live physical
  question (T1). The case maps no Stage C element to B1 and links it to the
  gap `song_routes`, which is LOST and is not filled.

One difference of terms, recorded and left for the holder and the owner:
the case's consent terms exclude names and places and its checker enforces
that on the JSON. The July page was written before this record and is not
checked against those terms; it is not edited by this move.
