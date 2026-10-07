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
moved: 2026-10-08
updated: 2026-10-08
closed: 2026-10-08
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

### 2026-10-08

impl-tk125 (uncommitted, working tree): ROOT CAUSE src/zanzibar/schema/rules.py::norm_pred maps None to ... (read normaliser); SetEngine._add_tuple_direct/_remove_tuple_direct normalised BEFORE validate_write_identifiers, so None passed as bare, and TupleSource logged raw None -> NOT NULL IntegrityError. Also a pre-existing backend divergence: SetEngine.add_tuple(None,...) ACCEPTED as bare, graph WildcardIndex/ReachabilityIndex refused. Only the subject_predicate=None hole existed; int/bytes/float already refused in every field. Second hole: errors.py::_require admitted * / ... sentinels by == alone (non-str with matching __eq__ reached the DB driver). DECISION: refuse, not normalise (fail-closed, graph already refused, documented write forms are ... and Ellipsis). FIX: validate raw predicate then normalise in both SetEngine sites; _require admits sentinels only as exact str (or Ellipsis). Reads unchanged (None still reads as bare; pinned). No batch/bulk public write exists; oracle has no write path, no twin. PIN tests/test_tk125_write_field_types.py (273 collected): pre-fix 40 failed/233 passed; sabotage A (sentinel isinstance off) 34 failed; sabotage B (add-site order reverted) 3 failed; fixed 273 passed. 49 affected modules 1336 passed. README identifier paragraph updated. OWED by orchestrator: CHANGELOG [Unreleased] Fixed line, FINAL_REVIEW counts regen, full gate. Scratch: .scratch/tk127-2026-10-08/impl-tk125.md

TK127 review follow-up (fix-tk127, 2026-10-08): store_id is now validated. Repro re-run first-hand: ConnectedStore(s, None, schema=S) -> raw IntegrityError NOT NULL zanzibar_schema_record.store_id; 5 / b"x" / "" / " " were accepted. New src/zanzibar/schema/errors.py::validate_store_id (a str with a non-whitespace char; the identifier charset deliberately NOT applied, tenant:acme stays legal), raising AdmissionRejected "invalid store_id ...", exported from zanzibar.schema and called FIRST in ConnectedStore.__init__, TupleSource.__init__, SetEngine.__init__, ReachabilityIndex.__init__ and connectedstore/schema_io.py::save_schema. New tests/test_tk127_store_id.py (65 collected): red first 61 failed, 4 passed; sabotage A (blanks allowed) 20 failed, B (ReachabilityIndex call dropped) 9, C (save_schema call dropped) 10, D (ConnectedStore call dropped) 2 -- literal in the docstring. README identifier paragraph gained one sentence. Claim-rot: core.py::ReachabilityIndex.__init__ body moved (row 385 is a rename note, still true).

Done 2026-10-08. Root cause: SetEngine normalised a None predicate to the bare one BEFORE validate_write_identifiers; ConnectedStore then logged a raw None. Fixed: validate the raw predicate first; sentinels '*'/'...' accepted only as exact str. Every write field x every entry point pinned (tests/test_tk125_write_field_types.py, red-before-green + 2 sabotages). Review follow-up: store_id validated too (tests/test_tk127_store_id.py). First-hand 2026-10-08: add_tuple(None,...) -> AdmissionRejected. Gated with the 2026-10-08 commit (0.0.3). Workflow reports: docs/history/tk127-fixes-2026-10-08.md.
