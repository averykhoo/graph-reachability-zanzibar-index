---
id: R6-8
title: delta verifier runs one BFS per flipped PAIR instead of per distinct source (11.0%)
brief: CO-DESIGN TRIPLE with R6-16 + R6-7: take all three in one session or none -- see R6-16
pri: LATER
size: ?
deps: []
related: [R6-7, R6-16]
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-09-22b
updated: 2026-09-22b
closed:
---

`index_v4/invariants.py::verify_outbox_deltas`

**Measured (2026-08-17 motivating-measurement pass):** **11.0%** of a paranoid build — O(pairs × edges) per commit where O(sources × edges) suffices. Gate wall-clock, not a production win; already recorded as a known cost in `perf-next-round.md`’s minor notes.

**Verdict: MOTIVATED — still to land.** Position **9 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **This item rewrites an ASSURANCE CHECKER**, so [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) binds it: the rewritten check must be sabotaged red before it is trusted. A faster checker that no longer checks is this repo’s house failure mode.

⚠ **The fix must test BFS *neighbours*, not the seen-set** — otherwise `(s, s)` reads as reachable on corrupt state and the verifier stops catching exactly the corruption it exists to catch.

⚠ **Co-design with `R6-16` — do not take this one alone** (see its entry); no `deps` edge encodes it, because `deps` is precedence and this is simultaneity.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-8` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `index_v4/invariants.py::verify_outbox_deltas` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-09-22b

2026-09-22b: MEASURED ZERO LEAN COST, and this is the cheapest real win in the round on its own
merits.

Mechanical anchor census this session: `verify_outbox_deltas` and `bfs_reaches` have ZERO
occurrences in `formal/CORRESPONDENCE.md` (grep -c = 0 for both). The only mention anywhere under
`formal/` is one line of prose in `formal/SEMANTICS.md:562`. Neither symbol is a gate anchor, so
`verify.sh lean` cannot see this change at all -- no Lean def edit, no sec 7 entry, nothing owed.
That makes it the ONLY open R6 row with a genuinely zero Lean bill.

`size: ?` on this row is an UNSET FIELD, not a measured size. On surface evidence it is an S and
is SMALLER than R6-7: two symbols in one file (`verify_outbox_deltas` ~47 lines plus its nested
`bfs_reaches` closure), with two ready-made sabotage pins already in the tree
(`tests/test_outbox.py::test_delta_verifier_catches_seeded_closure_bug` and
`::test_delta_verifier_catches_false_removal_claim`).

THE (s,s) TRAP IS REAL AND IS THE WHOLE RISK. `bfs_reaches` opens `seen = {src}` and returns
True only on a `m == dst` NEIGHBOUR hit, so today `(s,s)` is True only via an actual cycle. A
rewrite that tests membership in `seen` instead returns True for every `(s,s)` unconditionally
and silently destroys the corruption case the verifier exists to catch -- an assurance step that
fails by passing. Sabotage against both existing pins before trusting the rewrite.

THE BLOCKER IS NOT THE CODE, IT IS THE CO-DESIGN TRAP. R6-16 says verbatim "Take all three in
one session, or take none of them", and R6-16 is ~10 symbols across five modules with a modelled
algorithm change. A session wanting this win alone must first get an explicit recorded decision
to break the triple. Note the 11.0% is GATE WALL-CLOCK, not production latency: PARANOIA FULL
never runs in production but IS the `tests/` default.

Full audit: docs/r6-sizing-census-2026-09-22.md
