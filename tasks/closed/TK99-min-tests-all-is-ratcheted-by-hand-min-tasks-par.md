---
id: TK99
title: MIN_TESTS_ALL is ratcheted by hand; min_tasks_parsed already solved this mechanically
brief: third consecutive raise found pre-existing headroom; a session that only ADDS tests never sees a red
pri: LATER
size: S
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-22
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
---

`MIN_TESTS_ALL` in `formal/verify.sh` is ratcheted BY HAND, and the third consecutive raise
again found pre-existing headroom -- i.e. tests that could have been deleted while the gate
stayed green. Size and provenance are in the floor's own comment in `formal/verify.sh`.

`tasks/config.json`'s `min_tasks_parsed` solved exactly this problem MECHANICALLY on
2026-09-06: `task.py::ratchet_min_parsed` raises the floor to `max(floor, files on disk)`
after every `new`, never lowers it, so headroom cannot re-accumulate. That key's
`_provenance` string records FOUR consecutive sessions forgetting the manual step before
the mechanical fix landed, and calls itself "the evidence that a note in a provenance string
is not sufficient to cause it".

The gate has no equivalent. A session that only ADDS tests never sees a red to remind it, so
the floor drifts below the live count silently and the zero-headroom property -- the entire
point of the floor -- is lost until someone re-measures by hand.

Carried in `HANDOFF.md`'s `## Still owed` as "Unfiled" until the 2026-09-22 disposition
filed it here.

## Traps

- (!) **Adding tests must stay free; only LOWERING is the defect.** Any mechanical ratchet
  must raise and never lower, exactly as `ratchet_min_parsed` does. A ratchet that can lower
  the floor to make a run green IS the thing the floor exists to catch.
- (!) **`MIN_CONF_ALL` is the same shape** and should be decided together, not separately.
- (!) `CLAUDE.md` states that these floors have ZERO headroom deliberately; do not
  reintroduce headroom as a way to stop the reminder firing.
- (!) **Sabotage it** (`docs/sabotage-procedure.md`): deleting a single test must still turn
  the gate red after the ratchet lands, and a ratchet that runs must not be able to paper
  over a genuine loss of coverage.

## Read first

- `formal/verify.sh` -- the `MIN_TESTS_ALL` / `MIN_CONF_ALL` floors and the floor's own
  provenance comment (the only place the value belongs; do not restate it in prose).
- [`config.json`](config.json) -- `min_tasks_parsed`'s `_provenance`, which is the worked
  precedent for mechanising a hand-ratcheted zero-headroom floor, including what it cost to
  leave it manual.
- `scripts/task.py::ratchet_min_parsed` -- the landed mechanical form, and
  `tests/test_tasktool.py::test_new_ratchets_the_floor_to_the_measured_total_and_never_lowers_it`
  for how it was pinned (with an instrument control).

## Log

### 2026-10-13

LANDED 2026-10-13 (lane L1-TK99). `formal/conformance/doc_counts.py::ratchet_floors` runs inside `python -m formal.conformance.doc_counts --generate`. It raises verify.sh's MIN_TESTS_ALL / MIN_CONF_HEAVY / MIN_CONF_REST to the live collected counts with max(floor, live), the `scripts/task.py::ratchet_min_parsed` rule, and NEVER lowers one. A breach (floor > live) stays red, untouched. The edit substitutes digits on raw bytes, so verify.sh keeps its CRLF line endings. It refuses (SystemExit, file untouched) if a floor line is missing or duplicated, or if the identity is already broken. `--generate` ratchets first, then re-reads the floors, so the block shows what the gate enforces. NEW REFUSAL: `doc_counts.py::floor_headroom` makes `--check` (verify.sh step 4e) FAIL when any of the four floors sits below its live count. This closes the hand-lowered-floor-plus-regenerated-block route, which the block comparison alone cannot see. ENV: `doc_counts._collect` drops ZANZIBAR_TEST_DSN and ZANZIBAR_PG_REQUIRED (tests/conftest.py:80 keeps test_postgres_ha.py only under them; line READ 2026-10-13), so the counts describe the default gate.

DECISION (HEAVY/REST split; delegated, decided here): HEAVY and REST are each ratcheted to max(floor, live) against their OWN live counts. HEAVY is the HEAVY_CONF file, parsed from verify.sh by `doc_counts.py::heavy_conf_name`. REST is the directory minus that file, computed by subtraction, which the existing per-file anti-vacuity check makes equal to the --ignore construction. MIN_CONF_ALL is then DEFINED as HEAVY + REST and is never ratcheted on its own. REASONED: any 'ratchet ALL, then split the growth' rule can LOWER a component. When tests move from REST into the heavy file, live_all stays flat, so REST := ALL - HEAVY falls. Sabotage 2 showed exactly this: the REST floor dropped 958 -> 953. Per-component maxima can never lower anything, and they keep the identity true by construction. The deliberate cost is that a REST->HEAVY move lifts ALL above live, so the gate goes red. That is correct, because REST lost tests. An intended move is resolved by hand-lowering REST and ALL.

MEASURED (READ, first-hand, 2026-10-13). Before landing: MIN_TESTS_ALL=1749 vs `pytest tests/ -q --collect-only` -> 2283 on clean d03156f, i.e. 534 headroom (agent-C triage, re-confirmed). Mid-batch, a read-only probe of `doc_counts.measure()` + `floor_headroom` gave tests/ 2342 (includes the concurrent lanes' additions) and reported `MIN_TESTS_ALL=1749 but tests/ collects 2342: 593 test(s) could be deleted with the gate green`. Conformance: 1093 = HEAVY 135 (test_conformance_remove.py) + REST 958, equal to the floors, so zero headroom on that side.

TESTS: tests/test_tk99_floor_ratchet.py, 12 tests, green. Fixtures are byte copies of the real verify.sh. SABOTAGE, each run then reverted and byte-compared: (1) `MIN_TESTS_ALL: live_tests` instead of max -> 2 failed, `assert [('MIN_TESTS_..., 1749, 1700)] == []`; (2) the split-the-growth design -> 2 failed, `assert 953 == 958`; (3) write_text instead of write_bytes -> 1 failed, `\r\r\n` vs `\r\n` (Windows-only by nature); (4) env scrub removed -> 1 failed, `'ZANZIBAR_TEST_DSN' not in {...}`; (5) headroom refusal deleted from --check -> 1 failed, `assert 0 == 1`. The literal outputs are in the test module docstring. verify.sh got provenance comments only (+18 lines; `bash -n` OK). No floor VALUE was hand-edited.

RED UNTIL --generate: on this tree `doc_counts --check` is red twice over: the block is stale (2283 vs 2342) and MIN_TESTS_ALL has headroom. One `python -m formal.conformance.doc_counts --generate` fixes both, raising MIN_TESTS_ALL to the live count. NEXT ACTION: that single --generate run, then the gate.

Mechanised 2026-10-13: `doc_counts --generate` ratchets MIN_TESTS_ALL / MIN_CONF_HEAVY / MIN_CONF_REST upward only (max(floor, live)) and derives MIN_CONF_ALL = HEAVY + REST. `--check` (step 4e) refuses any floor below live (`doc_counts.py::floor_headroom`). Pinned with 5 sabotages in tests/test_tk99_floor_ratchet.py. The HEAVY/REST decision and the measured 534/593 gap are in the comment above. The first --generate after landing closes the existing headroom.
