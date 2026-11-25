---
type: Task
id: TK-155
aliases: [TK155]
title: 'Store.expand: Zanzibar Expand on the composed store, returning keys'
brief: "TK123 SPLIT A26: do not move SetEngine.expand's body (CORRESPONDENCE anchors it)"
pri: NOW
state: closed
status: deprecated
size: S
deps: []
related: [TK123]
parent:
labels: []
source: docs/tk123-api-review-2026-10-14.md
source_hash:
created: 2026-10-15
taskpy_created: 2026-10-15b
taskpy_moved: 2026-10-19b
taskpy_updated: 2026-10-19b
taskpy_closed: 2026-10-19b
updated: 2026-11-25a
---

SPLIT from `TK123` (review item A26, `docs/tk123-api-review-2026-10-14.md`, call SPLIT).
`Store` has no `expand`; a user who wants Zanzibar's Expand must drop to
`SetEngine.expand`, which returns a raw `MemberSet` of bitmap ids (and `pos` omits subjects
covered by a star, so the reading is pos + stars - neg). Add `Store.expand` delegating to the
evaluator with `at_least` freshness semantics mirroring `Store.check`, plus a key helper.
Constraint: `formal/CORRESPONDENCE.md` anchors `setengine/engine.py::SetEngine.expand` and its
nested closures, so do not move its body (it reds `verify.sh lean`). It is a feature with its
own freshness semantics, which is why it is not in the TK123 API break.

## Read first

- `docs/tk123-api-review-2026-10-14.md` — row A26 (the SPLIT call and its probe)
- `src/zanzibar/setengine/engine.py::SetEngine.expand` — what `Store.expand` would delegate to
- `src/zanzibar/store/_store.py::Store.check` — the `at_least` semantics to mirror

## Log

### 2026-10-19

Promoted LATER -> NOW (TK156, TK157 -> NEXT) at the 2026-10-19 write-back: TK138/TK144 closed, and the user order stated 2026-10-16 (banner 2026-10-16b; TK151 Log) runs TK155-TK157 next, then TK151 last. The lint needs exactly one NOW.

### 2026-10-19b

LANDED (agent TK155/implement, uncommitted): Store.expand + ExpandResult in src/zanzibar/store/_store.py (keys / markers / excluded_keys, covers and __contains__; set-engine served; catch_up_evaluator then at_least -> StaleRead, same rung as Store.check). Exported via zanzibar.store.__all__ and zanzibar._LAZY; tests/test_tk123_top_level.py _EXPECTED_ALL gains ExpandResult. SetEngine.expand untouched (CORRESPONDENCE anchor); the A26 memo->_memo rename NOT done. Tests: tests/test_tk155_store_expand.py, 13 passed (oracle gates on both SetOps + graph lookup_reverse tie + freshness + call forms + checker control); sabotage S1-S5 and E3-alone all RED, literal lines in the module docstring. CHANGELOG [Unreleased] Added entry. Targeted runs: 94 passed and 900 passed. Plan doc: docs/tk155-store-expand-2026-10-19.md. RED: none known. Full gate NOT run; FINAL_REVIEW counts block likely needs doc_counts --generate. NEXT: orchestrator gates, regenerates counts, commits, then closes TK155.

Review fixes (fixer, 2026-10-19). LANDED: tests/test_tk155_store_expand.py::test_expand_userset_star_marker pins a [group:*#member] grant (markers == {('group','member')}, ghost userset covered, oracle + graph agree); reviewer mutation M8 (bare-only markers) was green, now RED (1 failed, 13 passed), recorded as S6 in the module docstring. The m.ineg excluded_keys term is unreachable by any probe so far and is declared NOT covered in the docstring (M1 re-run: 14 passed). src/zanzibar/store/_store.py: ExpandResult docstring now says a userset key's members are already included (keys or a marker), and documents that markers are (type, predicate) pairs vs lookup_reverse's (type, predicate, 'any') triples (pinned in the new test; not aligned, which is an API call for the 0.1.0 cut). Store.check and Store.expand share a new Store._require_evaluator_at for the StaleRead; sabotaging it fails 4 tests across both callers. DECLINED: SetEngine.expand docstring (anchored, TK155 D3), defer to TK151. Tests: test_tk155 14 passed; with multi_instance/concurrency/tk123 suites 87 passed. Gate NOT run (orchestrator). Report: .scratch/tk155-157/TK155/fix.md.

LANDED (uncommitted at close; the orchestrator gates and commits by path): `Store.expand(relation, object | object_type, object_name, *, at_least=None)` in `src/zanzibar/store/_store.py`, returning the new frozen `ExpandResult` (`keys`, `markers`, `excluded_keys`, `covers()`, `__contains__`), exported from `zanzibar.store` and the top level (`_EXPECTED_ALL` raised by that one name). Delegates to `SetEngine.expand`; engine.py body untouched, so no CORRESPONDENCE anchor or content pin moved. Always set-engine served: `catch_up_evaluator()` then `StaleRead` via the new shared `Store._require_evaluator_at` (also used by `Store.check`). CHANGELOG [Unreleased]/Added; version stays 0.0.5.
DOC: docs/tk155-store-expand-2026-10-19.md (FROZEN at this close; review/fix correction at the top).
TESTS: tests/test_tk155_store_expand.py, 14 tests, oracle gates (boolean + wildcards, both SetOps) plus a graph lookup_reverse tie; "14 passed"; with the multi-instance/concurrency/top-level modules "87 passed".
SABOTAGE (all RED): S1 no exclusions, S2 keys without ipos, S3 no catch-up, S4 no StaleRead, S5 no markers, S6/M8 non-bare markers dropped ("1 failed, 13 passed"), helper never raises ("4 failed, 83 passed"). Literal lines in the module docstring.
NOT COVERED (declared): the `ineg` term of excluded_keys (M1 stays green; no reachable state found).
OPEN for 0.1.0: ExpandResult.markers are (type, predicate) pairs, LookupResult.markers (type, predicate, any) triples; documented, not aligned. SetEngine.expand docstring pointer deferred to TK151. PG leg: reasoned skip (no locks/watermarks/isolation).
- 2026-11-25a (claude-code/claude-opus-5-5): SALVAGE (2026-11-25a, from gitignored .scratch/tk155-157/TK155/review-equivalence.md + review-equiv/probe_walks.py, probe_edges.py, the equivalence-lens review dated 2026-10-19; READ by the 2026-11-25a salvage agent, not re-run; the probes saved no output files, so the numbers are the reviewer's report). Coverage recorded nowhere else (docs/tk155-store-expand-2026-10-19.md keeps only "90 fixture walks + 116 generated-schema walks, 0 FAIL"): `probe_walks.py fixtures 3 10`, all 15 tests/fga_schemas x both SetOps x seeds 0-2, 10 steps + drain: 90 walks, 1328 states, 0 FAIL, 761136 checks (module checker E1-E3 plus an extra '*'-subject key `in res` vs oracle); `probe_walks.py gen 150 6`, 150 seeded generated schemas (seeds 1000..1149, SetOps alternating): 116 walks (34 Store-refused, graph out of scope), 1120 states, 0 FAIL; probe_edges.py (but-not, userset, nested group, `and`, TK144 self-relation, ghost object, invalid name, undeclared relation/type, doc:* object): expand `in` == oracle == Store.check on every probed key. Verdict: no equivalence divergence reproduced; its one nit (markers pairs vs triples) is tracked on this row's 2026-10-19 review-fix line.
