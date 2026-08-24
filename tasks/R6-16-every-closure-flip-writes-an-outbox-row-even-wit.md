---
id: R6-16
title: every closure flip writes an outbox row even with no boolean consumer (1.00 row/edge)
pri: LATER
size: L
deps: []
related: [R6-7, R6-8]
parent: R6
labels: [perf]
source: docs/perf-round6-audit-2026-08.md
source_hash:
created: 2026-08-15
moved: 2026-08-24b
updated: 2026-08-24b
closed:
---

`index_v4/core.py::ReachabilityIndex._add_db_edges_unsafe`

**Measured (2026-08-17 motivating-measurement pass):** exactly **1.00 outbox row per closure edge** on a schema with **no derived relations** (14,868 rows, nothing consumes them, manual prune only). The biggest combined space+write win in the round.

**Verdict: MOTIVATED — still to land.** Position **7 of 10** in the audit’s recommended order (`R6-6 → R6-11 → R6-5 → R6-4 → R6-9 → R6-18 → R6-16 → R6-7 → R6-8 → R6-1`). That order is a RECOMMENDATION and is deliberately NOT encoded as `deps`; neither is `R6-16`’s co-design requirement, which is simultaneity rather than precedence and lives in the traps of `R6-16`/`R6-7`/`R6-8`. **No row in this round has `deps`.**

## Traps

⚠ **Read your id’s entry in [`perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) — INCLUDING its verifier corrections — and that file’s §"Traps the numbers do not carry", before taking this id.** The audit’s own rule: *do not implement from titles alone*. Eighteen findings survived adversarial verification with **0 refuted**, but several impacts were downgraded, several fix sketches were corrected, and one fix was refuted outright while its finding stood.

⚠ **`R6-16` MUST be co-designed with `R6-7`/`R6-8`, never separately — and it is the round’s most dangerous fix.** Paranoia FULL uses the outbox as its worklist on **ALL** schemas, so gating emission without gating that consumer silently blinds the checker: an assurance step that fails by PASSING, which is this repo’s named house failure mode. **Take all three in one session, or take none of them.**

⚠ **`deps` is EMPTY here on purpose, and that is not a downgrade of the trap above.** This row carried `deps: [R6-7, R6-8]` until 2026-08-21. Co-design is a SIMULTANEITY constraint; `deps` is PRECEDENCE — `task.py ready` lists a task once its deps are *closed*. The encoding therefore said the opposite of the audit twice over: it hid the round’s biggest combined space+write win from `ready` until two items the audit’s own land order puts AFTER it (positions 8 and 9, against this one at 7) were finished, while still leaving `R6-7`/`R6-8` takeable alone — which is exactly the "never separately" the trap forbids. **Corrected 2026-08-24b: this trap used to end "the vocabulary has no mutual edge (lint rejects the cycle)", and that was wrong.** `deps` rejects cycles; `related` does not — `docs/tasktool-spec.md` §`related` states that `A related B` + `B related A` is the normal state and that acyclicity is meaningless for it. `related: [R6-7, R6-8]` is now set here, so `show` names the triple from all three ends (the incoming half is computed). It is navigation, NOT the constraint: `related` is untyped and cannot say "simultaneity", so the co-design requirement still lives in the traps of all three files, which is what you must read.

⚠ The auto-prune half must respect the `prune_outbox` MIN-cursor contract (the head row is kept so SQLite cannot recycle outbox ids under a held cursor).

⚠ **This changes a MODELED algorithm** — Lean model update plus the full phased gate and fuzz, or a logged gap in `CORRESPONDENCE.md` §7.

⚠ **Decompose every cumulative share before quoting it as a target.** `R6-10`’s headline 59.8% was CUMULATIVE; decomposed it was `_direct_incoming` 28.4% + `_nodes_by_ids` 30.7%, and the realised win came from the two SELECTs, not the headline. `R6-19` is the same trap caught earlier.

## Read first

- [`docs/perf-round6-audit-2026-08.md`](docs/perf-round6-audit-2026-08.md) §`### R6-16` — the entry, **including its verifier corrections**
- the same file, §"Traps the numbers do not carry" — the five round-wide traps (counted from that section at generation time, not restated: `migrate.py` refuses to build if the bullet count moves)
- [`R6_PROFILE_2026-08-17.md`](benchmarks/results/R6_PROFILE_2026-08-17.md) — verdicts, method, and the two honest limits (in-memory SQLite understates statement-count wins; cProfile depresses throughput)
- `index_v4/core.py::ReachabilityIndex._add_db_edges_unsafe` — the code
- [`docs/perf-next-round.md`](docs/perf-next-round.md) — the fence and the reopening rule
- `python task.py show R6` — the parent: round-wide order, traps and the re-run recipe (`python -m benchmarks.profile_r6[_write] --target <t>`, never beside another bench or a pytest run)

## Log

### 2026-08-21

**Migrated by `migrate.py`, and this row is a CORRECTION.** The first migration pass classified every id whose disposition string was not literally `closed` as retired, which wrote this live item into `retired-ids.txt` — an irreversible sink, since `task.py` refuses to re-mint a retired id. Its true disposition (`MOTIVATED, unlanded`) is taken from `docs/perf-round6-audit-2026-08.md`, the audit that owns these ids, not from the `R6` board row’s summary prose (which undercounts the land list by one and overcounts the declines by one). `parent: R6` makes the round a rollup: closing the last child is what reports that `R6` itself can close. **`created` (`2026-08-15`) is RECORDED, not approximated** — it is the date the audit doc that minted these ids states for itself; `moved` is the `R6` board row’s value.

### 2026-08-24b

related-edge sweep (trial finding F1): added `related: [R6-7, R6-8]`, and CORRECTED the second trap. It claimed 'the vocabulary has no mutual edge (lint rejects the cycle)' -- true of `deps`, false of `related`, which docs/tasktool-spec.md defines as untyped, symmetric-ish and deliberately NOT cycle-checked. The co-design requirement still lives in the traps of all three files: `related` navigates, it cannot say 'simultaneity'.
