# Goal census — what is this project's next GOAL? (2026-09-22c)

**ACTIVE-PLAN** (`docs/README.md` §3). Corrections append **dated at the top**. Freeze when a
direction is chosen and its first item closes.

## Correction, 2026-09-22d (appended; the body below is as-written)

**`TK94`'s row in the table below overstates the hole in two ways, and executing the item
is what found it.** Both are first-hand READ, and the full argument with the line cites is
[`docs/tk94-derived-userset-corpus-2026-09-22.md`](tk94-derived-userset-corpus-2026-09-22.md).

1. **The class was not unseen by the whole conformance surface.**
   `corpus.py::TTU_USERSET_SCHEMAS['derived_userset']` has been exactly this shape since
   2026-07-27. It is spec-side only (`test_conformance_spec.py`), so the accurate sentence
   is the narrower one the row's title makes: it was absent from `SCHEMAS`, and therefore
   from every arm that involves the **graph index**. That is still the equivalence-relevant
   half, so the ranking stands; the phrasing does not.

2. **"The enumerated, generated, remove AND bulk arms all draw from that corpus" is wrong
   for the first two.** `test_conformance_enum.py:197` parametrizes over its own six-name
   `_SHAPES` dict (`:136`), and `test_conformance_generated.py:150` parametrizes over
   `SEEDS` and never imports `SCHEMAS`. So the "cost is combinatorial" note in the cost
   column is conditioned on separately adding the name to `_SHAPES`, which the item did not
   do. The realised cost was **additive and small**: conformance `572 -> 582` collected
   (`+9` corpus parametrizations, `+1` new floor test), `tests/` unchanged.

Neither correction changes the chosen goal or the three steps.

Asked by the user 2026-09-22: *"not what task to do, but what goal to achieve — correctness,
perf, etc."* Three read-only censuses were dispatched (perf / equivalence / formal); their raw
reports are in the gitignored `.scratch/goal-census/{perf,equivalence,formal}.md` and this file
is the tracked transcription. **Provenance is labelled on every claim**: READ = the
orchestrating session read it first-hand; AGENT = a subagent's report, not re-verified;
REASONED = inference.

---

## 1. The shape of the repo, measured

**READ** (2026-09-22, `find`/`wc` over the tree; Lean excludes `.lake/packages`):

| | lines | files |
|---|---|---|
| product code (`index_v4/` + `setengine/` + `connectedstore/` + `zanzibar_utils_v1.py`) | **12,478** | — |
| tests (`tests/` + `formal/conformance/`) | 49,762 | 102 modules, 1,851 collected |
| Lean (`formal/`) | 65,345 | 84 |
| docs (`docs/` + `formal/*.md`) | 63,465 | 85 |
| process tooling (`scripts/`) | 6,671 | — |

Assurance + docs + process to shipped code is roughly **15:1**. Full ten-phase gate wall clock
from `.gate-runs/ledger.tsv` on 2026-09-22: **~2,160 s ≈ 36 min** (lean 185 s; conf tiles
224/226/151/160/308; tests tiles 314/194/192/206).

**READ**: `README.md` "# TODO" is struck through end to end. Everything unstruck is an explicit
non-goal or a documented hook (symmetric subject-keyed residues, a service wrapper, log
compaction). **The product's stated feature scope is complete.**

**READ**: 11 of 77 open rows (14%) are about the task-tool / handoff-lint / session-bookkeeping
machinery itself (`GC-1 HS-5 P13 TK100 TK85 TK86 TK96 TK97 TK98 TK99 ZT-P5`), and 4 of the last
6 commits were that kind of work.

**READ**: commits since 2026-08-01 by prefix — docs 54, formal 44, feat 23, fix 12, test 18,
tasktool 8, perf 5.

---

## 2. Correctness — the net has EMPTY cells, not just thin ones

**AGENT**, spot-verified: live correctness bugs in shipped evaluation code = **0**, arrived at
independently by a sweep of all 77 open rows. Matches the banner's re-affirmation of 2026-09-18.
**READ**: `pytest.mark.xfail` appears nowhere; `formal/verify.sh` sets `MAX_TESTS_XFAILED=0`.
The X1–X4 divergence inventory is fixed and pinned positively.

The eighteen named holes are in `.scratch/goal-census/equivalence.md`. The ones that matter:

| id | hole | measured? | cost |
|---|---|---|---|
| **TK94** (H1) | derived relation as a **userset subject** (`[group#member]` with `member` boolean) — **0 of 26** `corpus.py::SCHEMAS`. The enumerated, generated, remove AND bulk arms all draw from that corpus. | MEASURED 2026-09-21 | one corpus entry, but `test_conformance_enum.py` cost is combinatorial |
| TK44 (H2) | ~30% of generator pair-cell space unreached (891/1275 best union) | MEASURED | structural, adjudication-first |
| H4 | **object-wildcard WRITES are unenumerable** — `_tuple_space` emits `"*"` only as a subject. **No owning row.** | MEASURED | structural |
| P25 (H6) | star tupleset over a derived through-relation: Python accepts, no corpus contains it | MEASURED | corpus half cheap, Lean half structural |
| TK95 (H5) | refused mid-fan-out write leaves a seed-dependent applied prefix | MEASURED | cheap |
| P23 (H7) | out-of-charset declared names: graph refuses, set engine accepts | MEASURED | cheap |

**READ, and worth carrying**: `tests/parity.py::ParityEngine._apply:222-230` short-circuits a
duplicate raw add *before any backend sees it*, because the graph core is ref-counted
(`add;add;remove` leaves the tuple present) while `TupleV1` and the oracle are set semantics.
Raw-level idempotence really is enforced at the API boundary
(`connectedstore/source.py::TupleSource.add`, duplicate → no log row) so the **layering is
sound** — but the only artefact stating that contract is a comment inside a test.

---

## 3. Formal — the debt is not proofs, it is SILENT narrowness

**AGENT**, grepped 2026-09-22 over `formal/lean/ZanzibarProofs/**`: `sorry` **0** real (34
textual hits, all docstrings, incl. deliberate grep-instrument controls), `axiom` **0**, `admit`
**0**, `native_decide` **0**, `opaque`/`unsafe` **0**. 617 audited names, 51 byte-pinned headline
statements, 266 pinned definitions, axioms restricted to propext / Classical.choice / Quot.sound.

**Nobody needs to finish the proofs.** What is unfinished is the *fragment*, and:

> **READ, `formal/conformance/test_w4fragment_scope_pin.py:2`** — the bundle is
> *"a SILENT NARROWING, and nothing in this repo could see it."* `:52` — *"Nine of the ten rows
> are SILENT or MIXED."* Classification: **LOUD 0 · SILENT 7 · MIXED 3.**

So Python accepts, runs and answers on schemas the headline theorem says nothing about, with no
operator-visible signal. `CORRESPONDENCE.md` §7.3 additionally lists ~a dozen live Python
surfaces with **no** Lean model (read surfaces, backfill/audit_fixpoint, interner, node GC,
derived TTU through-shape, phantom userset subject, …), and Phase 7 (TLA+, concurrency) never
started.

**AGENT**: there is no credible path where the fragment converges on the shipped surface — every
widening row's own notes say finishing it does not end the queue. But **one coherent milestone
is in reach and cheap**: the T2a chain **P4 → P5 (+P14)**, three M rows, `deps: []`, evidence
already in hand (`formal/probes/d3_negedgefree_postflip_2026-09-05.lean`). Landing it retires
`W4NarrowT2a` and buys one clean sentence: *all six headline theorems hold under the same two
bundles, with no theorem-specific extra carry.*

**P6 stays parked** (user decision 2026-09-15d). It blocks only P7 and P25-option-1;
25 of 28 non-container formal rows are startable today.

---

## 4. Perf — rigorous, well-instrumented, and answerable to nothing

**AGENT**, and the two load-bearing halves **verified READ by this session**:

- **There is no performance target.** No SLA, no p99/p95, no throughput budget, no customer
  workload, no production deployment anywhere in `docs/ tasks/ benchmarks/ README.md`. (The only
  `p99` hits are a sabotage fixture id.) Benchmarks are two synthetic fixtures under **in-memory
  SQLite** and **cProfile**, both of which `R6_PROFILE_2026-08-17.md` says invalidate the seconds
  column.
- Round 6 has landed **2 of 20 ids in 5 weeks**, both genuinely good: `R6-10` 2.54× on the
  incremental boolean write wall, `R6-6` −63.2% statements per `check`.
- ⚠ **READ: `docs/perf-next-round.md:24` still says round 6 "landed nothing"**, and `:32-40`
  still lists `R6-10` then `R6-6` as the first two items to land. The *living* perf doc is ~1
  month stale and would send a session to re-open two closed items.
- Diminishing returns, the honest signal: of the ten open rows, **four had their prose corrected
  on 2026-09-22b for describing a surface or number the code does not have**, three had headline
  figures downgraded/overlapped/reclassified. `R6-5`'s famous 32.7% was measured to be mostly
  `R6-4`'s — the two overlap ~8.8 points and **cannot be added**. Unimpeached large measured
  wins remaining: **`R6-4`** (30.1%, grows with #derived) and **`R6-18`** (53.1% off the biggest
  table, owes a hand PG migration).
- `R6-7`+`R6-8` (~31.7% combined) buy **gate wall-clock, not production throughput**, and cannot
  be taken without `R6-16` — the triple is one unit (`tasks/R6-16-*.md:29`: *"Take all three in
  one session, or take none of them."*). Gating emission without gating the consumers makes
  `verify_outbox_deltas` **silently vacuous** — the house failure mode. Realistic cost 3–4
  sessions.
- The triple's one genuinely interesting payoff (**REASONED, never attempted**):
  `GraphIndex/LeafRules.lean::writeRulesRaw_untaintedSchema` is already stated at
  `∀ d ∈ S.defs, isDerived S d.1 = false` — exactly R6-16's gate — so gating emission the same
  way may **collapse** the logged/unlogged distinction and retire a branch of reasoning instead
  of adding one.
- `TK34` (the nightly canary) is fully specified at `docs/gate-runbook.md:752-762` and **never
  built** — 2.5× changes are landing with no regression tripwire behind them.

---

## 5. Two cheap defects that will mislead the next session regardless of direction

1. **READ** `docs/perf-next-round.md:24` — see above. Fix or the next perf session re-opens
   `R6-10`/`R6-6`.
2. **READ** `tests/test_generator_coverage.py:15` — *"★★★ THIS MODULE IS EXPECTED TO BE RED UNTIL
   RC1/RC2 ARE FIXED ★★★"*, and `:761` *"THEY ARE RED TODAY"*. RC1/RC2 closed at `0838bcf`; the
   module is green. A module that announces its own redness cannot signal a real one. Owned by
   **TK88** (S).

---

## 6. Recommendation

**REASONED.** The project has two assurance systems totalling ~115k lines around a 12.5k-line
implementation, and **neither can currently state which inputs it covers**: the Lean fragment
narrows silently in 7 of 10 fields, and the conformance corpus has at least one wholly empty
cell for a shape ordinary Zanzibar allows. That is the coherent next goal —

> **Make the assurance surface HONEST AND LEGIBLE, not wider.**

in three moves, in order:

1. **TK94** — close the one *empty* corpus cell. One entry widens four arms at once, and it is
   the only route by which a node lands in a derived relation's PUBLIC family at load time
   rather than backfill time, so everything keyed off "the public family is written only by the
   processor" (the assumption `TK92` just refuted) is currently unexamined. Precedent: the last
   by-construction corpus hole of this shape — the hardcoded `parent` tupleset in
   `tests/test_hypothesis.py` — is where **both** 2026-08-10 divergences hid. Size the entry
   against the enum bound first; say per module which branch each new arm reaches.
2. **P4 → P5 (+P14)** — land the T2a chain, declare it the formal milestone, and stop widening
   the fragment. Then treat P15/P16/P25-opt-2/DW-1 as assurance ranked against product risk, not
   as "the rest of the proof."
3. **Surface the silent narrowing** — the scope pin knows the classification; nothing puts it in
   front of an operator. The strongest version is a machine-checked coverage statement, not a doc.

**Explicitly NOT perf.** With no target, a perf win is unfalsifiable as value, and the round's
own 5.0% ceiling is already retiring candidates. If perf is wanted anyway, the honest first move
is **TK34** (the canary), not an `R6-N` row — and **fix `docs/perf-next-round.md` before anyone
starts**.

**The legitimate fourth option is to stop.** The README TODO is complete, live bugs are 0, proof
debt is 0, and 14% of the open backlog is now about the bookkeeping machinery. "Consolidate,
state the coverage honestly, and declare the exploratory project finished" is a defensible goal
and nobody outside the repo is asking for anything else.
