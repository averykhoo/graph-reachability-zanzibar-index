---
id: TK160
title: PG leg: lock-discipline test observer sampled once (non-vacuity guard flaked)
brief: test_lock_discipline_keeps_log_commits_in_id_order: observer scheduled after writers, 1 sample; make race deterministic
pri: LATER
size: S
deps: []
related: [TK154]
parent:
labels: []
source: tests/test_postgres_ha.py
source_hash:
created: 2026-10-16b
moved: 2026-10-16b
updated: 2026-10-16b
closed:
---

## What

`tests/test_postgres_ha.py::test_lock_discipline_keeps_log_commits_in_id_order` failed ONCE on
the PostgreSQL leg (2026-10-16b, local `pg_local.sh` cluster, full-module run):

    AssertionError: observer only sampled 1 times
    assert 1 >= 5
     +  where 1 = len([24])

`samples == [24]`: the observer thread was first scheduled after both writers had committed
all 24 rows. This is the test's own NON-VACUITY guard (`assert len(samples) >= 5`), not the
lock-order property: no out-of-order commit was observed. Did not reproduce: 3 solo runs and
2 full-module runs green straight after, and green in the same session's 4-tile DSN run.

## Next action

Make the race deterministic rather than retry it: e.g. have the writers wait on an Event the
observer sets after its first sample, or hold the writers' commit until the observer has
sampled N times. Never relax the `>= 5` floor and never mark it flaky (CLAUDE.md:
a vacuous pass is the house failure mode).

## Log
