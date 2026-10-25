---
id: TK162
title: measure the brute-force graph lookup / lookup_reverse implicit-userset channel on large stores
brief: 0.1.0: time the TK144 brute-force implicit-userset lookup on large stores; decide if docs need a warning
pri: NEXT
size: M
deps: []
related: [TK144, TK138]
parent:
labels: [perf]
source: docs/tk138-userset-self-relation-2026-10-14.md
source_hash:
created: 2026-10-19
moved: 2026-10-26
updated: 2026-10-26
closed: 2026-10-26
---

Follow-up from TK144 (TK138 landing 2), OPEN item 3. TK144's D3a key channel lists OpenFGA's implicit usersets in the graph index's lookups by a brute-force pass (`src/zanzibar/graphindex/wildcard.py::WildcardIndex._self_lookup`, `::_self_reverse_extra`, `::_self_reverse_derived`; translated at the store by `src/zanzibar/store/_store.py` result_keys / excluded_keys). Its cost on large stores is UNMEASURED: nothing in benchmarks/ exercises it.

Measure lookup / lookup_reverse with and without implicit-userset answers at a few store sizes (e.g. 1k / 10k / 100k tuples, schemas with deep computed-seed chains) against the pre-TK144 baseline, and record the numbers (dated) in a tracked doc. Perf is deprioritized (user, 2026-09-22c), so this is a measurement first; any optimisation that changes the modelled algorithm needs a Lean update (CLAUDE.md "Perf work & the Lean model").

## Read first

- `docs/tk138-userset-self-relation-2026-10-14.md`, Corrections 2026-10-17.
- `docs/perf-next-round.md` (the reopening rule: a motivating measurement first).

## Log

### 2026-10-20b

0.1.0 item (user, 2026-10-20b, in chat): measure before the cut. TK144 ships in 0.1.0 and adds a brute-force pass to graph lookup / lookup_reverse that nothing has timed on large stores. A known unknown in the release. Measurement only (perf stays deprioritized): the deliverable is dated numbers in a tracked doc, plus a yes/no on whether the user docs (TK151) need a cost warning for implicit-userset lookups. Feeds TK151, not the other way round.

### 2026-10-26

Measured 2026-10-26: docs/tk162-self-lookup-cost-2026-10-26.md (FROZEN), bench benchmarks/tk162_self_lookup_bench.py, raw benchmarks/results/tk162-self-lookup-2026-10-26.jsonl. Verdict YES, docs need a warning: a graph lookup for a USERSET subject on a schema with and/but-not is linear in the entities of each derived family type (WildcardIndex._self_lookup checks every one): 0.2 s / 2-2.6 s / 21-29 s at 1k / 10k / 100k tuples, 60-170x without the pass. Reverse lookups 2-16 ms flat; plain-user lookups unaffected; on the same schema without but-not the userset lookup is 4-7 ms at every size. Graph answers equal the set engine on every query. Warning landed in userdocs/explanation/limits.md + pointer in how-to/query-access.md. No optimisation (changes the modelled algorithm; perf deprioritized). Side finding recorded on R6-4.
