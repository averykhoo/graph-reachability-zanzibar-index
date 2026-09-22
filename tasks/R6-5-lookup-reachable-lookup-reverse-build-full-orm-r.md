---
id: R6-5
title: lookup_reachable/lookup_reverse build full ORM rows to read 3-4 columns (32.7%)
brief:
pri: LATER
size: ?
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

`index_v4/core.py::ReachabilityIndex.lookup_reachable`

**Measured (2026-08-17 motivating-measurement pass):** **22,410 ORM rows built (32.7% of profiled time)** to read 3–4 columns; `lookup_reachable` + `_classify_ids` together are **52%** of a boolean lookup. Filed medium, measured as the largest single block.

**Verdict: MOTIVATED — still to land.** Position **3 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-5` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the round-wide traps. Read the section; it is short, and it is the only home for how many there are. (This line used to say "the five", attributed to the tree generator recounting them at generation time. That generator was deleted with `.scratch/tasktool/` on 2026-09-07, so the attribution named a mechanism that could not run — `TK61`, reworded 2026-09-07b. A bare "five" with no attribution would have been worse: that is an unsourced restated count.)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `index_v4/core.py::ReachabilityIndex.lookup_reachable` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python scripts/task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-09-22b

MEASURED 2026-09-22b: THE 32.7% IS NOT THIS ROW'S, AND ~26.8% OF IT BELONGS TO R6-4.

The figure is one profile line -- `22410 ... sqlalchemy/orm/loading.py:1068(_instance)` -- which
is SQLAlchemy's GENERIC ORM-instance constructor, i.e. every ORM construction in the run.
`benchmarks/profile_r6.py::target_graph_lookup`'s banner is literally "[R6-4, R6-5]": ONE run
serves both rows, and `_collect_residue_memberships` builds ResidueV1 rows inside it.

Probe: `.scratch/r6-decomp/probe_instance_by_class.py`, same workload as the 2026-08-17 pass
(demorgans_law_2, scale 40, 60 lookups, 980 raw tuples, 100 residue rows). It counts a
SQLAlchemy InstanceEvents.load per mapped class. Literal output:

  ORM instances materialised during the 60 lookups: 22,410
       8,280  ( 36.9%)  NodeV4     <- R6-5
       8,130  ( 36.3%)  EdgeV4     <- R6-5
       6,000  ( 26.8%)  ResidueV1  <- R6-4
  R6-4 (residue rows)   : 6,000  (26.8%)
  R6-5 (node/edge rows) : 16,410 (73.2%)
  unattributed          : 0

INSTRUMENT CONTROL: the deduped total is EXACTLY 22,410, reconciling to the profile's own
recorded line. The first run of the probe reported 38,820 because `dir(index_v4.models)` exposes
NodeV4/EdgeV4/StoreV4 under two names each and it registered two listeners per class -- the
disagreement with the recorded figure is what exposed it. Dedupe by class identity.

CONSEQUENCES: this row's true share is 73.2% x 32.7% ~= 23.9 points, not 32.7. R6-4 is
UNDERCOUNTED, not overcounted -- its 6,000 constructions sit inside its own 30.1% cum and are
then attributed a second time here. The two headline numbers OVERLAP BY ~8.8 POINTS AND CANNOT
BE ADDED; the row's "52%" is also `22.6 + 29.6` where the 29.6 `_classify_ids` cum CONTAINS the
28.0 `_load_nodes` cum. R6-4 is the better true win of the pair.

`size: ?` here is an unset field, not a measured size -- no session has ever costed this row.

Full audit: docs/r6-sizing-census-2026-09-22.md

Path correction, same session: the probe cited in the 2026-09-22b entry above now lives in the TRACKED tree at benchmarks/probe_r6_instance_by_class.py. It was first cited at a gitignored .scratch/ path, which would have rotted the citation and lost the instrument -- the measurement is evidence, so the instrument belongs in the tree. Re-run from the repo root; output is byte-identical (6,000 ResidueV1 / 16,410 NodeV4+EdgeV4, deduped total 22,410 reconciling to the profile line).
