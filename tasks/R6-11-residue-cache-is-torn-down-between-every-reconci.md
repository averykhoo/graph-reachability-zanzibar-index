---
id: R6-11
title: residue cache is torn down between every reconcile_subject of a cascade (~4x/reconcile)
brief:
pri: LATER
size: S
deps: []
related: []
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-09-22b
updated: 2026-09-22b
closed:
---

`src/zanzibar/graphindex/processor.py::DeltaProcessor._run_cascade`

**Measured (2026-08-17 motivating-measurement pass):** **120** residue-cache scopes for **30** reconciles — built and torn down **~4× per reconcile**; re-confirmed 2026-08-21 at `184 scopes / 40 reconciles = 4.6×`. The fix is the digest’s one-line scoping change; invalidation already exists.

**Verdict: MOTIVATED — still to land.** Position **2 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **The filed "8×" is 2× INFLATED and the number is not the win.** It was a cProfile generator-resume artifact — a `@contextmanager` records two counts per `with`. Corrected to ~4× in all four places on 2026-08-21, and because a doc fix does not stop the next probe re-deriving it, the halving now lives in the INSTRUMENT: `benchmarks/profile_r6.py::_ctxmgr_entries`, which also refuses an odd ncalls (an odd count means a `with` never completed, and then halving is the wrong correction). The verdict is unchanged (`MOTIVATED`); only the size moved. And the figure measures the **mechanism**, not a win — re-measure before spending a ten-phase gate on it.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-11` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `src/zanzibar/graphindex/processor.py::DeltaProcessor._run_cascade` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-09-22b

CORRECTION 2026-09-22b: the `CORRESPONDENCE.md` edit this row inherits from the audit is ALREADY
DONE, and the owed edit is a different one.

The audit's verifier correction says line 339 describes `run_cascade` as "a thin
`_node_cache_scope()` wrapper" and must be updated to mention the second scope. R6-10 already
landed that. Live text at `formal/CORRESPONDENCE.md:355` and `:370` (dated 2026-09-22) reads
"TWO perf caches" -- `idx._node_cache_scope()` (N15) and `::DeltaProcessor._stored_cache_scope`
(R6-10). So the owed edit is TWO -> THREE, IN TWO PLACES, not the one the audit names.

Also: the audit's fix sketch names `_run_cascade` as the scope install site. It is not.
`::DeltaProcessor.run_cascade` holds the `with self.idx._node_cache_scope(),
self._stored_cache_scope():` line; `_run_cascade` is the bare loop.

STILL THE CHEAPEST CLEAN LANDING, with the cost in the right place. Behaviour-preserving, no
Lean def change (caching is explicitly not part of the modelled algorithm; anchors this session:
`run_cascade` 10, `_residue_cache_scope` 1, `_store_residue` 4 -- names must survive), no
migration, no new benchmark (`profile_r6_write.py --target cascade` already prints the counter).
The real cost is the invalidation test module: `tests/test_stored_cache_scope.py` is the
template at 692 lines / 9 tests. Budget most of the sitting there, not on the change.

Two hazards to answer for residue that `_stored_cache_scope`'s own docstring already answers for
stored: (i) the stored cache is DELIBERATELY not installed by `advance_index`, because that scope
spans the raw-write apply loop; (ii) TK82's 'fixpoint' tier runs after both scopes close.
The figure is the mechanism, not a win: ~4.6x, re-measured; the raw 8x is a cProfile
`@contextmanager` artifact and the halving lives in `benchmarks/profile_r6.py::_ctxmgr_entries`.

Full audit: docs/r6-sizing-census-2026-09-22.md
