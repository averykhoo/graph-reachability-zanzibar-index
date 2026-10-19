---
id: TK162
title: measure the brute-force graph lookup / lookup_reverse implicit-userset channel on large stores
brief: TK144 D3a implicit-key channel is brute force; unmeasured on large stores; perf deprioritized
pri: LATER
size: M
deps: []
related: [TK144, TK138]
parent:
labels: [perf]
source: docs/tk138-userset-self-relation-2026-10-14.md
source_hash:
created: 2026-10-19
moved: 2026-10-19
updated: 2026-10-19
closed:
---

Follow-up from TK144 (TK138 landing 2), OPEN item 3. TK144's D3a key channel lists OpenFGA's implicit usersets in the graph index's lookups by a brute-force pass (`src/zanzibar/graphindex/wildcard.py::WildcardIndex._self_lookup`, `::_self_reverse_extra`, `::_self_reverse_derived`; translated at the store by `src/zanzibar/store/_store.py` result_keys / excluded_keys). Its cost on large stores is UNMEASURED: nothing in benchmarks/ exercises it.

Measure lookup / lookup_reverse with and without implicit-userset answers at a few store sizes (e.g. 1k / 10k / 100k tuples, schemas with deep computed-seed chains) against the pre-TK144 baseline, and record the numbers (dated) in a tracked doc. Perf is deprioritized (user, 2026-09-22c), so this is a measurement first; any optimisation that changes the modelled algorithm needs a Lean update (CLAUDE.md "Perf work & the Lean model").

## Read first

- `docs/tk138-userset-self-relation-2026-10-14.md`, Corrections 2026-10-17.
- `docs/perf-next-round.md` (the reopening rule: a motivating measurement first).

## Log
