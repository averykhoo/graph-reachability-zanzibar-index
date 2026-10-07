---
id: TK125
title: a None subject predicate leaks a raw IntegrityError instead of AdmissionRejected
brief: add_tuple(None, ...) leaks sqlalchemy IntegrityError instead of AdmissionRejected
pri: LATER
size: S
deps: []
related: [TK122]
parent: TK127
labels: [infra]
source: hand
source_hash:
created: 2026-10-07b
moved: 2026-10-07b
updated: 2026-10-07b
closed:
---

`add_tuple(None, "user", "bob", "viewer", "doc", "d1")` raises `sqlalchemy.exc.IntegrityError:
NOT NULL constraint failed: zanzibar_tuple_log.subject_predicate` instead of `AdmissionRejected`
(CONFIRMED 2026-10-07, 0.0.2 install trial). Write-side identifier validation should refuse a
non-string field before anything reaches the database. Check every field of the write path,
not only the subject predicate.

## Traps

- (!) Reads are lenient by contract (an out-of-charset name just never matches, per `CLAUDE.md`
  sec "Gotchas"). Change the WRITE path only.

## Read first

- [`docs/pypi-trial-0.0.2-2026-10-07.md`](../docs/pypi-trial-0.0.2-2026-10-07.md) sec 1 B3.

## Log
