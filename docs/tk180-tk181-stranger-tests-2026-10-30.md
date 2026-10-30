# TK180 + TK181 -- test like a stranger: self-references, multi-instance, docs re-runs (2026-10-30)

> **FROZEN** once `TK180` and `TK181` close (2026-10-30b). Filed after the 0.1.1 install trial;
> plan context in [`tk179-strict-public-args-plan-2026-10-30.md`](tk179-strict-public-args-plan-2026-10-30.md)
> ("Why the suite missed F19 (and TK172, TK175)").
>
> Provenance: the two sections below the rule are the agents' persisted reports, transcribed
> verbatim from the gitignored `.scratch/agents/tk180.md` and `.scratch/agents/tk181.md` (AGENT,
> UNVERIFIED unless listed here). Verified FIRST-HAND by the session, 2026-10-30b:
>
> * **TK180 proof re-run** with the agent's `sab_core.py` (guard lines deleted from
>   `src/zanzibar/graphindex/core.py` on disk, restored and sha256-checked: `restored True`):
>   `--hypothesis-seed=4` -> `1 failed, 33 deselected`, seed 7 (not in the agent's 1-6) ->
>   `1 failed, 33 deselected`, both on
>   `tests/test_hypothesis.py::test_self_reference_add_then_remove_restores_row_multiset`;
>   guard present, seed 4 -> `1 passed, 33 deselected`.
> * **TK181**: the agent's one red (`userdocs/reference/tuple-strings.md`, `store.check(None, ...)`)
>   was the session's own TK179 regression of a DOCUMENTED read rule (`None` subject predicate
>   = bare subject on reads). Fixed in `src/zanzibar/schema/tuplestr.py::require_parts` (reads
>   allow `None` there; writes keep `AdmissionRejected` as the 0.1.0 changelog promises), not
>   by changing the page. Re-run in the session's targeted suite: `tests/test_userdocs_examples.py`
>   green (part of `852 passed`, 2026-10-30b).

---

## TK180 agent report

# tk180 report (2026-10-30)
## progress
- baseline (before edits, ci profile): tests/test_hypothesis.py + tests/test_wildcard_property.py: 41 passed in 88.83s (wall 91s)
- added to tests/test_hypothesis.py: _self_refs, pool_ops (one_of(pool, self-refs)), _SELF_REF_MOTIF_*, _self_ref_motif, _schema_ast(self_ref_motif=False default; None draws 1/3), schema_asts(self_ref_motif=None default), new test test_self_reference_add_then_remove_restores_row_multiset
- probes (in-memory sabotage plugin .scratch/agents/tk180/sab_tk175_plugin.py): crash needs ref TAINTED (r0:[user] -> no crash; [user] and [user] -> crash) and outer a plain `from` ((r1 from parent) but not r0 -> no crash)
- hypothesis-minimal-value trap: intrange(0,2)>0 weights INVERT under hypothesis (0 is simplest); booleans() simplest is False -> empty base. Fixed by ch.one with preferred first / keep-on-False.
- in-memory sabotage, new test only, ci, seeds 1..8: 8/8 red (UNIQUE zanzibar_node), ~4-5s each
- first iteration (pool_ops bias only, existing 4 graph tests): only seed 5 of 1..6 found it (TestParityMachine), 236s with shrink
- added test_schema_asts_draws_the_self_reference_motif + _is_tk175_shape + _TK175_SHAPE_FLOOR=6 (sweep: 13/180 after, 0/180 before). Floor sabotage (sweep self_ref_motif=False): `AssertionError: only 0/180 generated schemas carry the TK175 self-reference shape (floor 6)`, 1 failed 4 passed.
- sweep re-measured after: four-way 157/180 (was 150), tk126 16 (was 9), all 6 tupleset bodies drawn.
- ON-DISK core.py sabotage (script .scratch/agents/tk180/sab_core.py, sha256 45ceaf84... before == after, restored ok True): new test seeds 1-6 all `1 failed, 33 deselected`, UNIQUE zanzibar_node IntegrityError, shrinks to TK175 schema. Guard present seeds 1-3: `1 passed, 33 deselected`.
- NOTE core.py had mypy-B's edits (git diff 48+/21-) at the time of sabotage; diff stat identical before/after.
- ruff: fixed 5 F401 unused imports in test_hypothesis.py (example, invariant, outbox_watermark, wildcard_userset_restriction_shapes, ALL_SETOPS); none re-imported elsewhere. test_wildcard_property.py clean, unchanged.
- broad (in-memory sabotage) seeds 1-3, the 4 pre-existing graph-only/stateful properties: still green (4 passed) -> only the new dedicated test is the discriminating instrument.
- under hypothesis, schema_asts() draws the strict TK175 shape in 37/300 (12%) examples; doc relation counts 2..5 all drawn.
- FINAL: tests/test_hypothesis.py + tests/test_wildcard_property.py: 43 passed in 42.71s (wall 44s; baseline 41 passed / 91s wall -- concurrent load varies). collected 43 (+2).
- neighbours importing the changed helpers (test_lookup_oracle, test_tk116, test_self_referential_tuples, test_zt_p5, test_tk175): 115 passed in 125s.
- core.py sha256 45ceaf84... unchanged; guard present.
DONE


---

## TK181 agent report

# tk181 agent log (2026-10-30)
- baseline tests/test_userdocs_examples.py: 37 passed in 29.39s (2026-10-30, before edits).
- edited tests/test_userdocs_examples.py: test_page_examples_run runs each page twice in one tmp dir + compares stdout; new test_all_pages_in_one_shared_directory.
- first run after edit: 12 failed, all NameError persisted_id in src/zanzibar/graphindex/wildcard.py::_add_tuple_trusted -- another agent mid-edit of src (not mine). Retry later.
- smoke: HEAD version 67 checks 19.4s; new version 102 checks passed, 0 failed, 19.7s (--allow-checkout, PYTHONPATH=src).
- smoke sabotage via .scratch/tk181/sabotage.py (monkeypatch, no src edit): tk172 old lag -> 3 FAIL (rc=1); tk175 guard removed -> 2 FAIL IntegrityError (rc=1); tk176 _check_open_args no-op -> 1 FAIL sync=None (ops='pysets' still refused by SetEngine's require_setops).
- userdocs timing (loaded machine, other agents running): HEAD test file 32.6s (36 pass + tuple-strings red from another agent's src edit); new file 60.6s. Added ~28s: twice-run only for pages that leave a file (14/32), shared-dir test only for pages matching _TOUCHES_FILES (~16s, one test). Full version (every page twice + all pages shared) measured 110s.
- SABOTAGE S1 consistency.md unlink removed: GREEN (2 passed) -- the page is self-idempotent without it (reopen same store, re-add writes nothing). Not a hole: output really is identical.
- SABOTAGE S2 stall-recovery.md:45 unlink removed (restored, cmp ok): RED: "how-to/stall-recovery.md examples failed (SECOND run in the same directory): ... AssertionError: how-to/stall-recovery.md:78: printed 1, but the page says # -> 27". Shared test in that run was red for an unrelated reason (NameError require_setops: another agent mid-edit of src).
- SABOTAGE S3 stall-recovery.md: unlink removed + sqlite:///stall.db -> sqlite:///fanout.db (restored, cmp ok): shared test RED "1 page(s) failed in a shared directory: how-to/stall-recovery.md ... SchemaMismatch (doc#viewer declared only in the persisted schema)"; 1 failed in 14.96s.
- refactored twice-run into _twice_failure + new self-test test_the_run_twice_check_really_fires (synthetic drift/reset/hidden-dir pages). Mutants (scratch copies): M1 stdout compare off -> red; M2 _TOUCHES_FILES guard off -> red; M3 never re-run -> red.
- ruff: fixed 3 B023 in scripts/installed_smoke.py (1 pre-existing lambda last_tok, 2 in my settle()).
- FINAL: tests/test_userdocs_examples.py 1 failed, 38 passed in 65.99s -- the 1 is test_page_examples_run[reference/tuple-strings.md] FIRST run: TypeError "check(): subject_predicate must be a str, not NoneType None" at tuple-strings.md:197 (`print(store.check(None, "user", "alice", "viewer", "doc", "1"))  # -> True`). Caused by the concurrent uncommitted edit of src/zanzibar/schema/tuplestr.py (TK179 strict args); also red under the HEAD version of the test file. Not mine: page or src must be reconciled by the TK179 owner.
- FINAL smoke: 102 checks passed, 0 failed, 21.7s (HEAD: 67 checks, 19.4s).
- DONE.
