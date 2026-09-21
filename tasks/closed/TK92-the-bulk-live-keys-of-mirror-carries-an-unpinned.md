---
id: TK92
title: the bulk _live_keys_of mirror carries an unpinned copy of the line TK91 just pinned
brief: deleting [rel] from bulk_backfill.py:811 leaves 4 modules at 29 passed; unreachable-by-construction is UNPROVED
pri: NOW
size: S
deps: []
related: [TK91]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-20f
moved: 2026-09-21
updated: 2026-09-21
closed: 2026-09-21
---

`index_v4/bulk_backfill.py:811` carries its OWN `_live_keys_of`, a mirror of
`index_v4/processor.py::DeltaProcessor._live_keys_of` including the leading `rel` term in
`preds`. `TK91` pinned the processor's copy on 2026-09-20f
(`tests/test_reg_tk91_live_keys_repair.py`). The mirror is UNPINNED.

MEASURED 2026-09-20f, first-hand, twice by two agents independently:

* Deleting `[rel]` from the BULK mirror leaves `tests/test_reg_tk91_live_keys_repair.py`,
  `tests/test_backfill_enumeration.py`, `tests/test_bulk_build.py` and
  `tests/test_invariants_derived.py` at `29 passed`.
* The `TK91` bulk arm cannot see it either: over all 130 (corpus, seed) survivor cells the
  top-level live-key enumeration is IDENTICAL clean vs mutated
  (`LIVE-KEY ENUMERATION IDENTICAL clean vs M16`).

WHY THAT IS NOT AUTOMATICALLY A HOLE, and why this row exists rather than a fix.
The processor's `rel` term is a REPAIR AFFORDANCE reachable only on an INCONSISTENT store
(that is the whole finding of `TK91` -- see
[`docs/tk91-tk80-removal-coverage-2026-09-20.md`](../docs/tk91-tk80-removal-coverage-2026-09-20.md)
section 4.2). The bulk path may have no inconsistent store to repair:
`connectedstore/build.py::build_index` "refuses to run on an index that already has state",
so the bulk backfill arguably only ever runs over a pre-backfill state it constructed itself.

(!) THAT ARGUMENT IS **REASONED, AND NOBODY HAS PROVED IT.** It is recorded in
`tests/test_reg_tk91_live_keys_repair.py`'s docstring as a hypothesis, explicitly labelled.
Scope was deliberately not widened on 2026-09-20f.

## The two honest outcomes

1. **The term is unreachable by construction in the bulk path.** Then it is DEAD CODE in a
   mirror, and the right move is to delete it and say so -- or to leave it with a comment
   that cites the proof. Either way the proof has to exist.
2. **It is reachable.** Then it is an unpinned copy of a line whose deletion is a live
   authorization FAIL-OPEN on the processor side (`check` stays True after a retracted
   grant, and I9 reports OK because it enumerates through the same crippled function). That
   would want the same treatment `TK91` gave the original.

## First action

Decide which, with evidence, before writing any test. The cheap probe is to ask whether any
reachable call sequence puts the bulk backfill in front of a store carrying derived state
that outlives its leaf -- `.scratch/tk91-tk80/probe_stale.py` is the shape of the
reproduction on the processor side and was promoted into
`tests/test_reg_tk91_live_keys_repair.py`.

(!) Do NOT pin it by mutating the mirror and hunting for something that reddens. That is
how an INERT row gets written up as a clean pin. Say what the edit is supposed to move, and
check it moved (`docs/sabotage-procedure.md`).

## Read first

- [`docs/tk91-tk80-removal-coverage-2026-09-20.md`](../docs/tk91-tk80-removal-coverage-2026-09-20.md)
  section 4.2 (what the `rel` term guards, and the fail-open it prevents) and section 8.2
  (this trap, alongside the other still-unpinned weakenings found by the same sweeps).
- `tests/test_reg_tk91_live_keys_repair.py` -- the processor-side pin and the hypothesis.

## Log

### 2026-09-21

CLOSED — and the row's own menu of two outcomes was wrong. Map:
`docs/tk92-bulk-rel-term-2026-09-21.md`.

VERDICT: the bulk mirror's `[rel]` term is **REACHABLE** — "unreachable by
construction" is REFUTED — **and INERT**, so it is neither dead code (outcome 1)
nor an unpinned fail-open (outcome 2). It is a harmless superset. DECISION: the
term STAYS.

WHAT THE DEFENCE MISSED. It argued from `build_index`'s fresh-store refusal, which
is about INCONSISTENT stores. It says nothing about the other way the public family
gets a node: a stored USERSET SUBJECT `group:eng#member` interns `(member, group,
eng)` during the bulk LOAD, on an add-only build. Where `member` is itself derived,
the `[rel]` term is the only thing that enumerates `eng`. MEASURED first-hand
2026-09-21: `_live_keys_of('group','member')` returns `['eng','ops']` where the rest
of `preds` returns `['ops']`.

WHY FOUR MODULES SAW NOTHING — the census, not a guess. Over all 26
`formal/conformance/corpus.py::SCHEMAS`, four use a userset subject
(`group_userset`, `wildcard_group_member`, `taint_union_userset_arm`,
`residue_rich`) and in EVERY one the referenced `group.member` is plain-direct. The
intersection with the derived relations is EMPTY across all 26, so no corpus can
reach the branch. `tests/test_backfill_enumeration.py`'s "the corpus is add-only, so
the branch cannot move" was the right verdict for the wrong reason and now carries a
dated correction.

WHY INERT. `preds`' second term sees only POSITIVE leaves, so the sharp case is an
object with SUBTRAHEND-only state. Three arms measured (blocked-only + userset
subject; blocked-only alone; no state + userset subject): built state byte-identical
with and without the term, and identical to `bulk=False`, in all three. REASONED
(doc sec 3.4, labelled): a rel-exclusive name has no positive-leaf state of any of
the five `LeafSpec.kind` values, positive leaves are the only candidate generators in
`_reconcile`, so it reconciles to the empty membership.

LANDED. `tests/test_reg_tk92_bulk_rel_term.py`, 4 pins: the refutation (asserted on
what the enumerator RETURNED, not on a consequence — the consequence is nothing, so a
state-comparison pin would be green under the mutation); a ceiling control holding
the test's model of `preds` in lockstep with the shipped body; a fixture guard; and
bulk == bulk=False on an input class the corpus has never contained. The refuted
hypothesis in `tests/test_reg_tk91_live_keys_repair.py`'s docstring is corrected in
place.

SWEEP. 11 monkeypatches + 2 byte-level sabotages. `M_ID` (reconstruction unchanged)
green = the harness is faithful. 5 of 10 caught; 4 UNREACHABLE on this fixture
(no computed/TTU leaf, no wildcard node — verified by reading the plans, not
inferred); 1 REACHED and MASKED (`M10`, `_intern`'s `family_names` update: the line
runs, but a family populated during the run is unobservable across two strata) —
measured and deliberately not pinned. (!) `M3` (drop the `spec.positive` filter) was
GREEN on the first pass while being reached the whole time — the subtrahend family
was a SUBSET of the positive one. One tuple (`u9 blocked group:qa`) makes the filter
load-bearing and M3 caught. The single sabotage would never have found it.

SCOPE. The processor's copy is untouched and still the `TK91` fail-open.
"Live correctness bugs: 0" is undisturbed — this was an assurance question and the
assurance turned out adequate for the wrong reason.

NOT DONE, filed in doc sec 7: the corpus gap is wider than this test. Zero of 26
`SCHEMAS` pair a derived relation with a userset subject, so every generated and
enumerated conformance arm is blind to the class, not just the bulk identity gate.
One new `SCHEMAS` entry would widen several modules at once. Separate, larger item.
