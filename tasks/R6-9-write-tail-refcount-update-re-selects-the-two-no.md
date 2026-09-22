---
id: R6-9
title: write-tail refcount update re-SELECTs the two nodes already in node_map (4.51/write)
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

`index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`

**Measured (2026-08-17 motivating-measurement pass):** **4.51** `_db_node` point SELECTs per raw write, **17.7%** of a non-boolean build (context: **34.62 SQL statements per raw write** overall). The fix reuses the `node_map` batch-loaded three lines earlier.

**Verdict: MOTIVATED — still to land.** Position **5 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-9` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-09-22b

MEASURED THIS SESSION: the instrument is mis-keyed, so landing this fix cannot move its own
headline number. `benchmarks/profile_r6_write.py:198` keys the R6-9 verdict on
`_find(rows, func='_db_node', file_frag='index_v4/core.py')` and prints
"_db_node point SELECTs ... <- R6-9". But `index_v4/core.py::ReachabilityIndex._db_node`
(`:965`) resolves by (predicate, entity_type, entity_name, wildcard) -- it is the identity
SELECT shared by `node` and `cached_concrete_node`. The two SELECTs this row deletes are an
INLINE `select(NodeV4).where(NodeV4.store_id == ...).where(NodeV4.id == node_id)` in the write
tail of `::ReachabilityIndex._add_direct_edge_unsafe_impl` (`core.py:886-888`, dated
2026-09-22). They are not `_db_node` calls. The per-table `node_v4` statement counter in the
same printout is what drops ~2/write.

ACTION: re-key the instrument BEFORE landing, and treat that as its own gated step per
`docs/sabotage-procedure.md` sec "A MEASUREMENT is an assurance step too" -- it would be this
round's FOURTH instrument correction. Do not let a session claim the win off the unchanged
`_db_node` line. Lean: `_db_node` and `_load_nodes` have ZERO `CORRESPONDENCE.md` anchors
(mechanical census this session), so no Lean work is owed.

Full audit: docs/r6-sizing-census-2026-09-22.md
