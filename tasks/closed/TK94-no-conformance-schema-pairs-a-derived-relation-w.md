---
id: TK94
title: no conformance schema pairs a derived relation with a userset subject (0 of 26)
brief: censused 2026-09-21: the class TK92 needed exists nowhere in SCHEMAS; enum cost is combinatorial
pri: NOW
size: M
deps: []
related: [TK92]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-21
moved: 2026-09-22d
updated: 2026-09-22d
closed: 2026-09-22d
---

## What it is

**MEASURED 2026-09-21 (census, first-hand, while closing `TK92`).** Of the 26 entries in
`formal/conformance/corpus.py::SCHEMAS`, **zero** pair a DERIVED relation with a userset
subject. Four use a userset subject at all — `group_userset`, `wildcard_group_member`,
`taint_union_userset_arm`, `residue_rich` — and in every one the referenced
`group.member` is a plain-direct relation. The intersection with each schema's compiled
`plans` keys is empty across all 26.

So `type doc: define viewer: [user, group#member]` where `group.member` is itself boolean
— ordinary Zanzibar, and accepted by `parse_openfga_schema` — is an input class the whole
conformance surface has never run on. Not just the bulk identity gate: the enumerated,
generated and remove arms all draw from this corpus.

`TK92` closed one hole in it from the `tests/` side
([`tests/test_reg_tk92_bulk_rel_term.py`](../tests/test_reg_tk92_bulk_rel_term.py) pins
`bulk == bulk=False` on ONE such schema) and deliberately did not widen scope.

## Why it is worth a row

The class is not a curiosity — it is the only way a node lands in a derived relation's
PUBLIC family at LOAD time rather than at backfill time, which is what made `TK92`'s
refutation possible at all. Anything keyed off "the public family is written only by the
processor" is unexamined against it.

## First action

Add ONE `SCHEMAS` entry whose userset subject names a derived relation, then measure —
per module — what newly runs and what newly reddens. **Measure before predicting**: the
`TK92` sweep found a mutation (`M3`) that was reached and masked for a reason nobody
would have guessed from reading.

## (!) Traps

- **(!) A new corpus entry is not free and its cost is not uniform.** `SCHEMAS` is
  parametrized over by many modules at once; `formal/conformance/test_conformance_enum.py`
  enumerates every store up to a bound, so one schema there is a combinatorial cost, not
  an additive one. Size the entry against the enum bound before adding it.
- **(!) `MIN_CONF_ALL` / `MIN_TESTS_ALL` have ZERO headroom.** Adding tests is free;
  the floors move up and must be re-measured, never estimated
  (`pytest <dir> -q --collect-only`).
- **(!) Do not assume the new arms are vacuous because they pass.** That is the whole
  lesson of the four modules that measured the `[rel]` term inert for a reason that was
  about corpus content, not about the code. Say which branch each new arm reaches.

## Read first

- [`docs/tk92-bulk-rel-term-2026-09-21.md`](../docs/tk92-bulk-rel-term-2026-09-21.md)
  §2 (the census and its literal output) and §7 (this item's provenance).
- `tests/test_reg_tk92_bulk_rel_term.py` — the one schema of this class that exists, and
  the fixture-guard shape worth copying.
- `formal/conformance/corpus.py::SCHEMAS` — the corpus, and `::GRAPH_FRAGMENT` for which
  entries the graph arms take.

## Log

### 2026-09-21b

Promoted NEXT -> NOW at the 2026-09-21b write-back (closing TK93 left the board with no NOW). Ranked above TK71 and the new TK95 on the primary consideration: this is a whole SCHEMA CLASS that no generated or enumerated conformance arm can reach, i.e. a hole in the equivalence net itself, where TK71 is an assertion-strength question and TK95 is an outcome-equivalence pin on a path already known green at four hash seeds. The M sizing and the combinatorial cost in test_conformance_enum.py are the reason it is ranked first rather than deferred again -- it has been the cheapest-to-defer item twice now.

### 2026-09-22c

2026-09-22c -- TK94 is now STEP 1 OF A CHOSEN GOAL, not just the top-ranked row. The user
asked for a goal rather than a task ("not like what task to do, but what goal to achieve --
correctness, perf, etc"), three read-only censuses were run (perf / equivalence / formal),
and the user chose: **make the assurance surface HONEST AND LEGIBLE, not wider.** Map and
full evidence: docs/goal-census-2026-09-22.md.

Why TK94 is step 1, in the goal's own terms. The project has ~115k lines of Lean plus tests
around 12.5k lines of implementation (measured 2026-09-22c, census sec 1), and NEITHER
assurance system can state which inputs it covers. On the Lean side that is the silent
narrowing -- test_w4fragment_scope_pin.py:2 says the bundle is "a SILENT NARROWING, and
nothing in this repo could see it", LOUD 0 / SILENT 7 / MIXED 3. On the test side it is this
row: an EMPTY corpus cell, not a thin one. Of the eighteen holes censused, TK94 is the only
one where the class is absent outright rather than under-sampled, and because all four arms
(enumerated, generated, remove, bulk) draw from SCHEMAS, one entry widens four at once.

The precedent that decides the ranking: the last by-construction corpus hole of exactly this
shape -- the hardcoded `parent` tupleset in tests/test_hypothesis.py -- is where BOTH
2026-08-10 divergences (RC1, RC2) were hiding. By-construction holes are empirically where
this repo's real bugs have lived.

The steps after this one, so the goal is resumable if this row stalls: (2) land the T2a chain
P4 -> P5 (+P14) as THE formal milestone and stop widening the fragment -- three M rows,
deps [], evidence already in hand -- which buys the sentence "all six headline theorems hold
under the same two bundles, with no theorem-specific extra carry"; (3) make the silent
narrowing visible, ideally machine-checked rather than a doc.

Explicitly NOT the goal: perf. Censused first-hand 2026-09-22c -- there is no SLA, no p99, no
throughput budget, no customer workload and no production deployment anywhere in docs/,
tasks/, benchmarks/ or README.md, so a perf win is currently unfalsifiable as value. That is
a deprioritization with a reason, not an abandonment; it is recorded on the R6 parent too.

Nothing about this row's own first action or traps changes: size the new SCHEMAS entry
against the test_conformance_enum.py bound BEFORE adding it (combinatorial, not additive),
re-measure MIN_CONF_ALL / MIN_TESTS_ALL rather than estimating, and say per module which
branch each new arm reaches -- a new arm that passes is not evidence that it ran.

Filed alongside: TK101, hole H4 (object-wildcard WRITES are unenumerable -- _tuple_space
emits "*" only as a subject), which had lived in TK71's traps since 2026-09-16b with no
owner of its own.

### 2026-09-22d

LANDED. `formal/conformance/corpus.py::SCHEMAS['derived_userset_subject']` -- a DERIVED
relation (`member: allowed but not blocked`) as the predicate of a stored userset subject
(`doc.viewer: [user, group#member]`). Map, with every figure and its provenance:
`docs/tk94-derived-userset-corpus-2026-09-22.md` (ACTIVE-PLAN -> freeze with this close).

TWO CORRECTIONS TO THIS ROW'S OWN FRAMING, both first-hand READ, both found by executing it.
A dated correction is appended to `docs/goal-census-2026-09-22.md`, whose TK94 row carried
both.

(1) The class was NOT unseen by the whole conformance surface. `corpus.py::
TTU_USERSET_SCHEMAS['derived_userset']` has been exactly this shape since 2026-07-27 -- it is
SPEC-SIDE ONLY (`test_conformance_spec.py`), so the accurate sentence is this row's own title:
absent from `SCHEMAS`, hence from every arm involving the GRAPH INDEX. Ranking unchanged;
phrasing was wrong.

(2) The first trap ("`test_conformance_enum.py` ... one schema there is a combinatorial
cost") is over-stated. That module parametrizes over its own six-name `_SHAPES` dict
(`:136`, indexed at `:197`), NOT over `SCHEMAS`; `test_conformance_generated.py:150`
parametrizes over `SEEDS` and never imports `SCHEMAS`. So of the four arms the row says one
entry widens at once, the first two do not widen at all. Cost was ADDITIVE: conformance
572 -> 582 collected, `tests/` unchanged at 1279. The trap is re-pointed, not deleted -- it
is a trap about `_SHAPES`.

THE SCOPE DECISION, taken by the session per CLAUDE.md "Who decides": `SCHEMAS` YES,
`GRAPH_FRAGMENT` NO. The class is outside `FullScope.lean::W4Fragment` by a NAMED field --
`term`'s `NoStoreSubjectR` half forbids exactly a stored userset subject naming a derived
relation, and Python ADMITS such a write, so `test_w4fragment_scope_pin.py` classifies it
SILENT (probe line `:83`). zcli does not gate on the fragment, so `GRAPH_FRAGMENT`
membership would silently compare two models no theorem relates -- the ZT-P3-3 mistake, for
the third time. `SCHEMAS` membership alone is scope-clean: the spec legs compare `sem`,
which carries no fragment hypotheses, and the three GRAPH legs of
`test_conformance_remove.py` compare the graph index against the ORACLE and a fresh
add-only build ("Scope: sem/Lean deferred"), making no Lean claim. The exclusion is
COMPUTED, not promised: graph/state/bulk_state parametrize over `GRAPH_FRAGMENT` and
`test_conformance_remove_graph.py::_REMOVABLE` is built from it plus a `_THEOREM_BACKED`
assertion.

WHICH BRANCH EACH NEW ARM REACHES (the third trap, answered mechanically rather than
assumed). Tracked probe `formal/probes/tk94_new_arm_reach_2026-09-22.py` drives the real
gate path at the same five seeds and asks, per corpus, whether the leading `rel` term of
`index_v4/bulk_backfill.py::_BulkBackfill._live_keys_of` ever enumerated a name the
positive-leaf half did not. Over all 27 entries, 2026-09-22: `derived_userset_subject` is
the ONLY True (seed 0, `('group','member')`, rel-only `['g1','g2','x_group_2']`); eighteen
corpora CALL the function 5-15 times and never get an exclusive name; nine never call it.
So the branch TK91 hypothesised unreachable and TK92 refuted from `tests/` is now reached
by the conformance gate, and by exactly one corpus.

(!) THE PROBE'S INSTRUMENT LIED FIRST, in the direction that reads as a finding: run 1
reported eight corpora SKIPPED on a TypeError. It was the wrapper -- the shipped
`_live_keys_of` RECURSES through `self._live_keys_of` and unions into a set, and the wrapper
returned a list. Eight "could not measure" rows would have passed for a property of those
corpora. GL-1 lesson; the fix is commented at the line that caused it.

PERMANENT PIN: `test_conformance_nary_strata.py::test_schemas_carries_a_derived_userset_subject`
-- (a) some `SCHEMAS` corpus stores a userset subject over a derived relation, and (b) some
such subject object carries NO state of its own (the rel-exclusive shape). (b) is the
load-bearing half; without it the corpus reaches the branch and cannot discriminate it,
which is the state all 26 predecessors were in. The floor is over `SCHEMAS` SPECIFICALLY --
written over the harness-wide corpora it would stay green with the entry deleted, rescued by
the spec-side twin, i.e. an assurance step that fails by passing. Sabotage S1 is that
control. CLEAN `20 passed`; S1 (delete the entry) / S2 (delete only the rel-exclusive tuple)
/ S3 (invert the helper) each `1 failed, 19 passed` naming their own claim; restored
`20 passed`. S0 is recorded too: the first cut of S1 RENAMED the dict key and came back
green -- correctly, since the floor tests the class and not the name.

GATE FLOORS -- a DRIFT REPAIR this row's second trap caused me to find. Re-measuring rather
than estimating showed both floors had stopped honouring the zero-headroom contract:
`MIN_CONF_ALL` 546 vs live 572 BEFORE this item (26 of slack), `MIN_CONF_HEAVY` 104 vs 130
(26), `MIN_TESTS_ALL` 1209 vs 1279 (70, and TK94 adds nothing under `tests/`). All ratcheted
to live (582 = 135 + 447, and 1279) with the instrument check the prior ratchets set as
precedent -- floor at live+1, literal failure observed, restored:
  FAIL: formal/conformance/ collects only 582 test(s); the gate floor is 583.
  FAIL: tests/ collects only 1279 test(s); the gate floor is 1280.
both rc 1.

Also same-commit: `formal/FINAL_REVIEW.md`'s generated counts block regenerated via
`doc_counts --generate`; three `26 corpora` prose sites re-dated with a pastness word
(`test_conformance_remove.py:602`, `:725`, `docs/tk92-bulk-rel-term-2026-09-21.md:77`) --
`doc_counts --check` now reports `0 stale claim(s)`.

NOT DONE, deliberately, and filed as `TK102`: taking this corpus into
`test_conformance_enum.py::_SHAPES` is the genuinely combinatorial widening and needs its
own runtime budget. One UNVERIFIED item left flagged in the map: `formal/probes/
p6_inbridge_stability_2026-09-12.lean:478` claims a property INERT "on all 26
`corpus.SCHEMAS`" -- a P6 scope claim no checker sees, unknown at 27. `P6` is parked.
