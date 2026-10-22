# `TK3` — the always-on cascade-owed mark: the measured plan

**ACTIVE-PLAN, opened 2026-10-22 — the body is provenance, not a living status.** This is
the execution map for `TK3` (0.1.0 blocker): refuse the COMMIT of a transaction in which a
`WildcardIndex` write on a boolean schema ran no `DeltaProcessor.run_cascade` /
`DeltaProcessor.backfill`. Every figure and line number below is as-of 2026-10-22. Live
state is the task row (`python scripts/task.py show TK3`), never this file. Corrections
append **dated at the top**, never edited into the body. Freeze it when `TK3` closes.

Provenance labels: **READ** = read first-hand in the tree this session; **PROBED** = a
script was run and its literal output is quoted; **REASONED** = argued, not run;
**UNVERIFIED** = stated but not yet checked. Scouting stage only: **no product file was
edited** for this doc. Probes live in `.scratch/tk158-tk3/` (gitignored), which is why
their outputs are transcribed here.

Concurrency note: lane `TK158` was editing `src/zanzibar/graphindex/core.py` (add-edge
counting) and `src/zanzibar/store/_store.py` (refusal undo) in the same tree while this
was written, and ran a 1M-member benchmark at the same time. The census below ran against
whatever those files held at 2026-10-22 ~16:03.

---

## Correction 2026-10-22 (FIX stage): both holes closed, four review nits applied, one new pre-existing bug

Fix lane. Product files edited: `src/zanzibar/graphindex/cascade_mark.py`,
`src/zanzibar/graphindex/wildcard.py` (three call sites); tests in
`tests/test_tk3_cascade_mark.py`; the §6 note in `formal/CORRESPONDENCE.md`. All PROBED on
SQLite. The PostgreSQL leg was NOT run (UNVERIFIED). Probes and runner are under
`.scratch/tk158-tk3/` (`fix-probes/`, `fix_sabotage.py`), which is gitignored, so the outputs
are copied here.

**Both holes reproduced first-hand before the fix (PROBED,
`.scratch/tk158-tk3/review-probes/p_holes.py`).** The probe printed
`P1 -> {'owed_after_sp_rollback': [], 'committed': True, 'graph_viewer': True,
'expected_viewer': False}`, and P1off printed the same. It also printed
`P2 -> {'owed': [], 'committed': True, 'graph_viewer': True, 'expected_viewer': False}`.

1. **Hole 1 (blocking): a cascade inside a savepoint that is then rolled back. FIXED.**
   `cascade_mark.py::clear` now handles a payment made inside a savepoint (innermost
   transaction has a `.parent`) as provisional. It moves each cleared entry to a new
   `session.info` key, `::PAID_KEY`, against the transaction it was paid in.
   `::_after_soft_rollback` first re-arms every paid entry whose payment transaction is
   the rolled-back savepoint or nested inside it. It then drops, as before, the debt whose
   write is inside it. A write that is undone together with its cascade therefore owes
   nothing. A payment at the root is not recorded, because only the root's own end can
   undo it and `::_after_transaction_end` discards both keys there. After the fix,
   `p_holes.py` printed `P1 -> {'owed_after_sp_rollback': ['g'], 'committed': False, ...}`
   (P1off: the same). `rev_tk3_p1.py` printed `P1: paranoia=off CascadeNotRun raised (OK,
   refused)`, the same for `P4` (the sibling savepoint case) and for `P1: paranoia=full`.
   New pins: `W7[off|full]` (the remedy is also checked: run the cascade at the root, the
   commit goes through, `viewer` is False), `W7b` (sibling savepoints), `W7c` (an inner
   payment released into an outer savepoint, then the outer savepoint rolled back).
   Controls: `N13` (a released savepoint's cascade pays) and `N13b` (write plus cascade in
   one savepoint that is rolled back: owes nothing).
2. **Hole 2 (should-fix): `processor_writes` as an opt-out the census does not count.
   FIXED.** `::note_write` no longer reads `widx.processor_writes`. It takes
   `derived_write=`, and the three `WildcardIndex` call sites pass
   `self._derived_write_ctx(relation, o_type)` (for `remove_node`:
   `(pred, entity_type)`). That value is true only when the window is open AND the target
   is a derived-public family, which is exactly the processor's own output (I5).
   `WildcardIndex.backfill` passes nothing, so it always owes. After the fix,
   `p_holes.py` printed `P2 -> {'owed': ['g'], 'committed': False, ...}`, and
   `rev_tk3_p9.py` now ends in `CascadeNotRun`. New pin: `W8`. Control: `N14` (a
   processor-flagged derived write owes nothing). `N11` (a reconcile outside
   `run_cascade`) still passes. The six hand-flip test sites the reviewers listed all
   write derived families or are refused before the mark, so none of them needed a
   change (their modules are green, below).
   **Bound, now stated in the module docstring (REASONED):** a derived-family write made
   with the flag flipped by hand is still exempt. It is an I5 bypass, and
   `_assert_derived_exclusivity` is the fence for that, not the mark.
3. **The fixpoint-tier claim was unpinned (should-fix). PINNED.** `N12b` monkeypatches
   `DeltaProcessor._check_cascade_fixpoint` to raise and expects `CascadeNotRun` at
   commit.
4. **CORRESPONDENCE.md §6 overclaimed (should-fix). FIXED.** The note now lists every
   bound: a cascade run with a too-high watermark, the processor-flagged derived-write
   exemption, the census-pinned test waiver, bare `ReachabilityIndex` writes, a commit on
   the raw Connection, and that savepoint rollback re-arms a payment (since this fix).
5. **Nit, waiver census scope. APPLIED.**
   `tests/test_tk3_cascade_mark.py::_waiver_sites` now scans `src/`, `tests/`, `formal/`,
   `benchmarks/` and `scripts/`. It matches the bare identifier `\b_cascade_check_waived\b`,
   so an import or an alias binding counts too, and it exempts only the defining module.
6. **Nit, a refused add still leaves the commit blocked. NOT CHANGED, documented here.**
   The mark is set before `_resolve(create=True)` interns nodes, so a
   `ClosureFanoutExceeded` refusal on the direct `WildcardIndex` API still owes a
   cascade. The check stays fail-closed: the `CascadeNotRun` message names both remedies,
   and `zanzibar.Store` rolls back. Moving the mark later would need proof that every
   refusal after it is a no-op, and TK158 is changing exactly that code
   (`core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`). For the userdocs: "after
   catching a refusal on the direct API, roll back or run the cascade".
7. **Nit, the `not compiled.plans` branch. LEFT, REASONED to be dead.** The probe that
   would settle it was not run; this stays UNVERIFIED and has no pin.
8. **Nit, MIN_TESTS_ALL.** This file now collects 40 (was 31). Set the floor from a
   fresh `--collect-only` of the integrated tree, not by adding deltas.

**NEW pre-existing bug, not TK3 (PROBED, `fix-probes/n13.py` and `n13_cause.py`).** With
paranoia `'full'` on in-memory SQLite, RELEASING a savepoint fires
`src/zanzibar/graphindex/invariants.py::ParanoiaGuard.after_commit` (a spy recorded
`in_nested_transaction() == True` for that call). Its fresh `Session(sess.get_bind())`
shares the `SingletonThreadPool` connection, and the writes made in the savepoint are
lost. Output: `full inside sp after cascade False` / `full after release True` /
`full fresh session True`. Under `off`, every stage printed False. With `after_commit`
patched to a no-op: `noop after release viewer False`. This is probably also the cause of
the BUILD stage's `no such savepoint: sa_savepoint_1` (REASONED). Not fixed, because it is
outside this lane. The likely one-line fix is to return early from `after_commit` when
`sess.in_nested_transaction()` (REASONED). `N13` runs with `paranoia='off'` for this
reason, and its docstring says so. It needs its own row.

**Sabotage, FIX stage.** Runner: `.scratch/tk158-tk3/fix_sabotage.py`. Each mutant is one
exact-anchor replacement, run over `tests/test_tk3_cascade_mark.py`, after which the
bytes are restored and checked by SHA-256.
- F1 (no re-arm in `_after_soft_rollback`): `4 failed, 36 passed` (W7[off], W7[full], W7b,
  W7c).
- F2 (`clear` records no paid entry): `4 failed, 36 passed` (same four).
- F3 (exempt every write while `processor_writes` is on, i.e. the pre-fix behaviour):
  `1 failed, 39 passed` (W8).
- F4 (never exempt a derived write): `2 failed, 38 passed` (N11, N14).
- F5 (clear moved between `_run_cascade` and `_check_cascade_fixpoint`, reviewer R2):
  `1 failed, 39 passed` (N12b).
- F6 (the old census scope plus a planted `benchmarks/_tk3_f6_probe.py` that imports the
  waiver as an alias): `40 passed`, so the old census was blind. Control, the real census
  with the same probe: `1 failed` with `Extra items in the left set:` /
  `'benchmarks/_tk3_f6_probe.py'`. The probe was deleted afterwards.

## Correction 2026-10-22 (second adversarial REVIEW, correctness lens): corroboration + one new false refusal

Reviewer lane 2, no product file edited. Probes `.scratch/tk158-tk3/probes/rev_tk3_p*.py`
(gitignored; outputs transcribed). All PROBED on SQLite; the PostgreSQL leg was NOT run
(UNVERIFIED there).

1. **Corroborates hole 1 below independently (PROBED):** add `user:a viewer doc:d` at the
   root, `sp = begin_nested(); proc.run_cascade(wm); sp.rollback(); commit()` ->
   `COMMITTED ... viewer=False` (control, cascade at the root: `viewer = True`; a fresh
   Session re-read also `False`). A SIBLING variant fails the same way: write inside a
   released savepoint A, cascade inside savepoint B, roll back B, commit ->
   `('COMMITTED', 'viewer=', False)`. Both also with paranoia `'full'`. Neither path is
   reachable through `zanzibar.Store` (READ: no `begin_nested` in `src/zanzibar/store/`).
2. **Corroborates hole 2 below (PROBED):** `widx.processor_writes = True` around a leaf
   write, commit -> `COMMITTED without cascade; viewer = False (expected True)`.
3. **NEW, fail-closed false refusal (PROBED):** with `ZANZIBAR_MAX_CLOSURE_FANOUT=2`, a
   direct-API `add_tuple` refused with `ClosureFanoutExceeded` (edges before/after `3 3`)
   still leaves the store owing a cascade (`owed after refused add: ['g']`), so the
   caller who catches the atomic refusal and commits gets `CascadeNotRun`, although the
   add changed no edge. `note_write` sits before `_resolve(create=True)`, which can intern
   nodes, so this is by design per its docstring ("one refused part-way still owes"); it is
   a usability cost, not a wrong answer. Remedy is in the message (run the cascade / roll back).
4. **Census scanner scope (READ):** `tests/test_tk3_cascade_mark.py::_waiver_sites` scans
   `tests/` and `formal/conformance/` only, so a `_cascade_check_waived(` use added under
   `src/` would not turn the census red.
5. **Negatives that held (PROBED):** after `CascadeNotRun` the transaction is still active
   (`in_transaction() == True`), and `run_cascade(wm)` + commit then succeeds with
   `viewer = True` (paranoia off and full); two threads with their own Sessions are
   isolated (`{'B': 'committed', 'A': 'refused'}`); remove + `DeltaProcessor.backfill()`
   (which clears the mark) does repair the derived edge (`viewer = False (expected False)`);
   a write as the first statement of a fresh Session records a real `SessionTransaction`
   (not `None`) as its owner.

## Correction 2026-10-22 (adversarial REVIEW stage): two holes, one unpinned claim

Reviewer lane, no product file edited. Probes: `.scratch/tk158-tk3/review-probes/`
(`p_holes.py`, `sabotage.py`, `test_probe_fixpoint_tier.py`); outputs transcribed here
because `.scratch/` is gitignored. Every sabotaged file was restored and SHA-256 checked.

1. **FAIL-OPEN, PROBED: a cascade run inside a savepoint that is then rolled back still
   pays the debt.** `cascade_mark.py::clear` pops every nesting level, and
   `::_after_soft_rollback` only discards debt, never restores it. Witness (P1): commit a
   `viewer` grant with a cascade; `wm = outbox_watermark(...)`; write `user:alice banned
   doc:d1` at the root; `sp = begin_nested(); proc.run_cascade(wm); sp.rollback();
   session.commit()`. Literal output:
   `P1 -> {'owed_after_sp_rollback': [], 'committed': True, 'graph_viewer': True, 'expected_viewer': False}`
   (also with paranoia `'off'`; the `'full'` guard did not catch it either). A stale
   ALLOW is committed. Neither the module docstring's bound nor the `CORRESPONDENCE.md`
   §6 note ("ENFORCED ... for every WildcardIndex write") names this case.
2. **Uncensused second opt-out, PROBED (P2):** setting the public `WildcardIndex.processor_writes`
   setter around a leaf write makes `note_write` skip it, and the commit goes through:
   `P2 -> {'owed': [], 'committed': True, 'graph_viewer': True, 'expected_viewer': False}`.
   Five test files set it by hand (`test_boolean_compile.py`, `test_outbox.py`,
   `test_reg_tk80_remove_node_residue.py`, `test_wildcard_remove_node.py`,
   `test_reg16_processor_writes_thread_scope.py`); `test_waiver_sites_are_the_census` does
   not see them.
3. **Unpinned claim, PROBED:** "a cascade (or fixpoint tier) that raised leaves the mark
   armed". Sabotage R2 (move the clear between `_run_cascade` and
   `_check_cascade_fixpoint`) -> `31 passed` on `tests/test_tk3_cascade_mark.py`. The
   probe `test_probe_fixpoint_tier.py` (monkeypatch `_check_cascade_fixpoint` to raise)
   passes on the real tree (`1 passed`) and goes red under R2 (`1 failed`), so it is the
   missing test.
4. Reviewer sabotages that WERE caught (literal tails): R1 rollback matches the exact txn
   only -> `1 failed, 30 passed` (N4d); R4 drop the clear in `DeltaProcessor.backfill` ->
   `2 failed, 29 passed` (N2, N10); R5 any transaction end clears -> `13 failed, 18 passed`;
   R6 delete the mark in `_add_tuple_trusted` -> `12 failed, 19 passed`. R3 (drop the
   `not compiled.plans` test) -> `31 passed`, REASONED equivalent: `schema/boolean.py`
   returns `None` instead of an empty `CompiledBooleans`, so the branch looks unreachable.

## Correction 2026-10-22 (BUILD stage): what landed, measured outputs

**Built (READ, this tree, 2026-10-22):** `src/zanzibar/graphindex/cascade_mark.py`
(`::note_write`, `::clear`, `::owed_stores`, `::CascadeNotRun`, `::_cascade_check_waived`,
listeners `::_before_commit` / `::_after_soft_rollback` / `::_after_transaction_end`), wired
per §3: `wildcard.py::WildcardIndex._add_tuple_trusted` (after `_lock_store`, before
`_resolve(create=True)`), `::_remove_tuple_trusted` (after the endpoint resolve, before
`remove_edge_by_id`), `::remove_node` (after the TK80 / TK113 fences, before
`_neighbour_entities` / `_strip_bridges`), `::backfill` (after `_lock_store`);
`processor.py::DeltaProcessor.run_cascade` clears AFTER `_check_cascade_fixpoint`, and
`::DeltaProcessor.backfill` at its end. Exported: `zanzibar._LAZY` + `TYPE_CHECKING`,
`zanzibar.graphindex.__all__`; pins updated in `tests/test_tk123_top_level.py`
(`_EXPECTED_ALL['zanzibar.graphindex']`, `_BUILTIN_BASE['CascadeNotRun'] = RuntimeError`).
Two deviations from the §3 sketch: (1) the listeners are installed lazily on the FIRST
arming write (`note_write` → `::_ensure_guard`), not in `WildcardIndex.__init__`, so
`__init__` is untouched and a pure-union session still never carries them (N5 asserts
it); (2) the boolean test is evaluated per write from `schema_info.compiled` (two attribute
reads) instead of a cached bool.

**Tests:** `tests/test_tk3_cascade_mark.py`, 31 collected (W1-W6 + W2b, N1-N12 with N3b /
N4a-e / N7b, waiver pins, export pin). W5 uses a core CYCLE refusal (not the fan-out cap
of §6), so this lane never depends on `TK158`'s edits to the cap counting.

**§4.2 census sites, as fixed (all PROBED green 2026-10-22):**
- SLOPPY: `test_boolean_compile.py::test_facade_derived_family_exclusivity` and
  `test_wildcard_property.py::test_middle_sync_record_excludes_the_wildcard_entity` gained
  `run_cascade(wm)` (the latter OUTSIDE `record_middle_syncs`, so the recorder still sees
  the user write alone). `test_outbox.py::test_derived_flag_set_only_by_processor_writes`
  got `flush()` + `rollback()` instead: a cascade there would mint the derived edge that its
  next step writes by hand, breaking `direct_edge_count == 1`.
- REMOVE_NODE (rows 4, 6, 12-15): the harnesses gained
  `test_reg_tk80_remove_node_residue.py::_Harness.remove_node_cascaded` and
  `test_tk113_remove_node_fence.py::_G.remove_node`, which run the cascade and ASSERT it
  changed nothing (row snapshot; tk80 also residues + the reverse index). **Result: no
  change in any of the six (PROBED, all pass).** So the §4.2 escalation is answered "no
  pre-existing `remove_node` staleness on these fixtures": evidence on six cases, not
  proof in general, and the arming stays fail-closed.
- DELIBERATE: one waiver, in `test_reg_tk91_live_keys_repair.py::_stale_store`, covers
  all five tests. Waiver census (`test_waiver_sites_are_the_census`) = {that file, the TK3
  test file itself}.

**Finding, pre-existing, NOT TK3 (PROBED, `.scratch/tk158-tk3/probes/tk3_n4d*.py`):** with
the `'full'` paranoia guard installed, `outer = begin_nested(); inner = begin_nested();
<write>; inner.commit(); outer.rollback()` on SQLite fails with
`(sqlite3.OperationalError) no such savepoint: sa_savepoint_1`. It fails the same way with
`note_write` patched to a no-op, and works at `paranoia='off'`, so N4d runs at
`paranoia='off'`. Cause UNVERIFIED (the paranoia guard's listeners on a savepoint release
are the suspect).

**Cost (PROBED, `.scratch/tk158-tk3/probes/tk3_cost.py`, 2026-10-22, laptop, SQLite
in-memory, paranoia off):** `note_write` 0.56 µs/call on a boolean schema and 0.10 µs on a
pure-union one; `_before_commit` on a clean session 0.16 µs; one cascaded write + commit
about 9,000 µs. Overhead is about 0.006% per write. Tier: none (always on), as decided.

**Regression (PROBED 2026-10-22, bare pytest, not the gate):** `tests/test_matrix.py` +
`tests/test_hypothesis.py` + `tests/test_connectedstore*.py`: 98 passed. Conformance
(`test_conformance_graph`, `_state`, `_remove`, `_direct_arm`, `_enum`, `_nary_strata`,
`test_graphadmission_scope_pin`, `test_w4fragment_scope_pin`): 392 passed. Whole `tests/`
(shared tree, lane TK158 live): 2969 passed, 10 failed, none in a TK3 file:
- 8 in `tests/test_claim_rot_gate.py`: the CORRESPONDENCE anchor CONTENT pin is stale.
  TK3 changed the bodies of `run_cascade`, `DeltaProcessor.backfill`, `_add_tuple_trusted`,
  `_remove_tuple_trusted` and `remove_node` and anchored three new `cascade_mark` symbols;
  TK158 changed `core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`. The rows citing
  the TK3 symbols were re-read and are still true; `claim_rot.py --generate` is owed.
- 2 in `tests/test_tk123_no_internal_refs.py`, both TK158-lane text (a `core.py` raise
  citing `I1`; the `source.py::TupleSource.undo_last_admission` docstring citing `TK158`).

**Sabotage (trap (d), PROBED 2026-10-22).** Runner `.scratch/tk158-tk3/tk3_sabotage.py`:
one exact-anchor replacement, the named tests, then the original bytes restored and checked
by SHA-256; S9 by a planted file, then deleted. Literal outputs:
- M0 (control: break `test_top_level_export`'s assertion) → `FAILED
  tests/test_tk3_cascade_mark.py::test_top_level_export`, `1 failed, 1 passed` (only the
  named test).
- S1 drop the clear in `run_cascade` → `27 failed, 21 passed` over the TK3 file +
  `tests/test_matrix.py`. Every boolean matrix case is red
  (`test_matrix_4way_boolean[0..2]`, `test_matrix_4way_crossable_star_ttu[0..2]`, all 8
  `test_demorgan_oracle_equals_setengine_equals_graph[...]`) with
  `CascadeNotRun: commit refused: store 'g' (first unpaired write: add_tuple) ...`, plus
  N1, N3, N4c, N7, N7b, N8, N9, N10 (the composed `Store` path), N11, W2, W2b, W3, W5.
- S2 hook returns at once → `14 failed, 17 passed`: W1, W2, W2b, W3, W4, W5, W6, N4b,
  N4e, N7, N8, N9, N12, waiver-scope.
- S3 no mark in `_remove_tuple_trusted` → `1 failed, 30 passed`: W2.
- S4 drop the root `after_transaction_end` clear → `1 failed, 30 passed`: N3b (close)
  only. REASONED: a root ROLLBACK also clears through `_after_soft_rollback` (every entry
  descends from the root), so the root-end clear is load-bearing for `close()` and is the
  backstop for commit.
- S5 key the mark by `id(widx)` (the note side only, coarser than §7's two-sided form) →
  `18 failed, 13 passed`, N7b among them.
- S6 clear at the START of `run_cascade` → `1 failed, 30 passed`: N12.
- S7 hook ignores `in_nested_transaction()` → `3 failed, 28 passed`: N4b, N4c, N4d.
- S8 drop the `processor_writes` skip → first run `31 passed`: **the original N11 was
  vacuous**, because its reconcile on a clean key wrote nothing. N11 was rebuilt to repair a
  stale key built under a waiver, asserting the answer changed. Re-run → `1 failed, 30
  passed`: N11.
- S9 plant `_cascade_check_waived(` in an unlisted `tests/_tk3_s9_probe.py` → `FAILED
  ...::test_waiver_sites_are_the_census` (`Extra items in the left set:
  'tests/_tk3_s9_probe.py'`); probe deleted, re-run `1 passed`.

**Lean / CORRESPONDENCE:** no Lean change (§8 stands). `formal/CORRESPONDENCE.md` §5
`runCascade2` row and §6 `ReachedBy` row gained the one-line notes; `anchor_check.py`
resolves every anchor (846/846, PROBED).

**Next:** orchestrator integration (the §9 list, plus `claim_rot.py --generate` and the
`MIN_TESTS_ALL` floor, +31 TK3 tests), then the gate.

---

## 1. The decision (binding, from the row) and what this doc adds

From `show TK3` (2026-10-13 A1 + 2026-10-20b, READ): build an O(1), ALWAYS-ON mark, outside
the paranoia ladder, set by a `WildcardIndex` write when the ruleset has compiled boolean
plans, cleared by `run_cascade` and `DeltaProcessor.backfill`, asserted clear in a
`before_commit` hook that refuses the commit. Keep `WildcardIndex` public. Traps (a)–(d) are
binding and are addressed in §§3, 4, 6, 7 below.

This doc adds: the transaction boundary (§2), the exact design (§3), the census (§4), the
opt-out (§5), the test and sabotage plans (§§6–7), the Lean impact (§8), and what the
orchestrator owes the files this lane must not touch (§9).

## 2. Where the mark hangs: the transaction boundary

### 2.1 The write sites (READ 2026-10-22)

All user-reachable `WildcardIndex` mutations, `src/zanzibar/graphindex/wildcard.py`:

| symbol | line (2026-10-22) | reached from |
|---|---|---|
| `WildcardIndex.add_tuple` → `::_add_tuple_trusted` | :625 → :640 | tests/harnesses directly; `store/build.py::_materialise` (`bulk=False`); `store/apply.py::_apply_row` calls `_add_tuple_trusted` |
| `WildcardIndex.remove_tuple` → `::_remove_tuple_trusted` | :698 → :704 | same, `_apply_row` for `REMOVE` rows |
| `WildcardIndex.remove_node` | :731 | public admin API only (no `src/` caller) |
| `WildcardIndex.backfill` (wildcard bridges / I14 middles) | :568 | **no `src/` caller** (grep `backfill(` 2026-10-22) — tests only |

The processor's own writes go through the SAME public methods:
`src/zanzibar/graphindex/processor.py::DeltaProcessor._write_derived` (:618) sets
`widx.processor_writes = True` and calls `widx.add_tuple` / `widx.remove_tuple`. So the mark
must be skipped when `processor_writes` is on, or every cascade would re-arm it.
`processor_writes` is thread-scoped (`core.py::_ThreadFlag`, :42), which is exactly right:
the bypass belongs to the thread that opened the window.

The clear sites, `processor.py`: `DeltaProcessor.run_cascade` (:1439, the cache-scope wrapper
around `::_run_cascade` :1482) and `DeltaProcessor.backfill` (:1692).

### 2.2 Candidates, and the choice

**(i) An attribute on the `WildcardIndex` instance.** REJECTED. Nothing ties one facade to
one processor: `DeltaProcessor(widx, compiled)` is built by the caller, a test may build a
second facade or processor over the same `(session, store)`, and `run_cascade` drains the
STORE's outbox, not the facade's. A per-instance mark would refuse a correct
"write via facade A, cascade via processor on facade B" sequence and, worse, the reverse
mismatch could clear a mark the other facade owes. It also outlives a rollback unless every
caller's rollback reaches it.

**(ii) An attribute on `ReachabilityIndex` / in `core.py`.** REJECTED. The core is
schema-blind (it does not know whether plans exist), every widx write and every processor
write funnel through it so it cannot tell a user write from a cascade write, and lane `TK158`
is editing it now.

**(iii) `Session.info`, keyed by `store_id`, cleared by Session transaction events.
CHOSEN.** Reasons (REASONED, with the PROBED facts in §2.3):
- **The transaction IS the session's transaction.** "In the same transaction" is a property
  of the `Session`, so the state lives where the transaction lives. Every widx and every
  processor reach it as `idx.session` (`DeltaProcessor.__init__` sets `self.session =
  widx.idx.session`, READ :255-258).
- **Keyed by `store_id`**, because one session can carry several stores, and a cascade on
  store `a` must not clear store `b`'s debt.
- **Threads:** the repo rule is one `Session` per thread (CLAUDE.md § Concurrency), so a
  per-session mark is per-thread for every conforming caller with no extra machinery. A
  caller that shares one Session across threads already violates the rule; the mark then
  becomes shared (a cascade on thread A clears thread B's debt). That bound is stated in
  the docstring, not engineered around.
- **Precedent:** `src/zanzibar/graphindex/invariants.py::install_paranoia` (:988) keeps its
  per-store registry in `session.info['paranoia_guards']` and registers per-session
  `before_commit` / `after_commit` / `after_flush` listeners idempotently. The new guard
  copies that shape, so the repo keeps one pattern.
- **Rollback for free.** The mark is dropped by `after_transaction_end` on the ROOT
  transaction (fires on both commit and rollback, and on `Session.close()`), so no caller's
  rollback path has to remember it. Every composed failure path in `src/zanzibar/store`
  already rolls back (`_store.py::Store._write` :594, `::Store._catch_up` :680,
  `build.py::build_index` / `::rebuild_index`, READ).

### 2.3 SQLAlchemy 2.0.51 facts the design rests on (PROBED 2026-10-22)

Probe `.scratch/tk158-tk3/probes/sa_events.py`, literal output:

```
1. commit raised: refused
1. same root txn after refusal: True is_active: True
1b. retry commit ok
2. nested txn id 1673084216720 root id 1673084154320 get_transaction is root: True
2. events after savepoint rollback: [('txn_end', 'nested', 1673084216720), ('soft_rb', 'nested', 1673084216720)]
3. events after savepoint release: [('before_commit',), ('txn_end', 'nested', 1673087284624)]
4. events after root rollback: [('txn_end', 'root', 1673084154320), ('soft_rb', 'root', 1673084154320)]
5. events after root commit: [('before_commit',), ('txn_end', 'root', 1673083622480)]
```

Consequences, each load-bearing:
1. **A `before_commit` raise leaves the root transaction ACTIVE and retryable** (lines 1/1b).
   So after a refusal the caller can roll back, OR run the cascade and commit again. The
   message offers both.
2. ⚠ **`before_commit` ALSO fires on a SAVEPOINT RELEASE** (line 3). The hook must therefore
   check only on a root commit (`session.in_nested_transaction()` false), or it would refuse
   releasing a savepoint mid-transaction, which is legal: the cascade may come later in the
   root transaction.
3. **Savepoint rollback fires `after_transaction_end` BEFORE `after_soft_rollback`** (line 2).
   So "was this nested end a rollback?" is known only in `after_soft_rollback`; the design
   discards there, not in `after_transaction_end`.
4. Root rollback and root commit both end in `after_transaction_end(root)` (lines 4/5), the
   single clear-all point.

## 3. The design

New module `src/zanzibar/graphindex/cascade_mark.py` (a new file avoids editing `core.py`, and
breaks no import cycle: `wildcard.py` and `processor.py` both import it, and it imports
neither). Sketch (REASONED, unbuilt):

- `session.info['zanzibar_cascade_owed']: dict[store_id, list[SessionTransaction]]`. Each entry
  is the INNERMOST transaction live when the write ran
  (`session.get_nested_transaction() or session.get_transaction()`).
- `note_write(widx)`: called from `_add_tuple_trusted`, `_remove_tuple_trusted`,
  `remove_node`, `WildcardIndex.backfill`. Returns at once unless the facade's schema has
  compiled plans (cached bool computed once in `WildcardIndex.__init__`:
  `compiled is not None and compiled.plans`, exactly the condition of
  `store/apply.py::_require_proc_for_boolean_schema`). Also returns when
  `widx.processor_writes` is on, or inside a waiver (§5). Cost when it does mark: one
  `session.info` lookup, one `get_*_transaction()` pair, one list append (or an identity
  check that skips a duplicate of the last entry). O(1), no SQL, no flush.
  - **Placement inside each write:** AFTER the pure pre-checks
    (`validate_write_identifiers`, `_assert_derived_exclusivity`; in `remove_node` also the
    `name == '*'`, TK80 and TK113 refusals), BEFORE the first index mutation
    (`_resolve(create=True)` in `_add_tuple_trusted`, which interns nodes; `remove_edge_by_id`
    in `_remove_tuple_trusted`; `_strip_bridges` in `remove_node`; the first bridge add in
    `backfill`). `_lock_store` is not an index mutation and may precede the mark. So a write refused before it mutates owes nothing, and a write
    refused AFTER it started mutating (a cycle refusal after `_ensure_bridges`, a
    `ClosureFanoutExceeded` mid-closure) still owes a cascade or a rollback. Fail-closed on
    purpose: the I12 rejection-cleanliness claim is exactly the kind of thing this check
    must not trust.
- `clear(session, store_id)`: called at the END of `DeltaProcessor.run_cascade` (after
  `_run_cascade` and the fixpoint tier return normally) and of `DeltaProcessor.backfill`.
  A cascade that raises leaves the mark armed. Clears every entry of that store, at every
  nesting level.
- `after_soft_rollback(prev)`: drop each entry whose transaction is `prev` or a descendant
  of `prev` (walk `.parent`). Handles a write inside a savepoint that is rolled back, and a
  released inner savepoint inside a rolled-back outer one. PROBED 2026-10-22
  (`.scratch/tk158-tk3/probes/sa_parent.py`): an ENDED `SessionTransaction` keeps its
  `.parent` chain; literal output
  `after s1 rollback: s2.parent is s1: True ; s1.parent is root: True ; root active: True`
  and `after root rollback: s1.parent is root: True ; root.parent: None`. So the
  descendant walk is sound.
- `after_transaction_end(t)` with `t.parent is None`: pop the whole dict. Covers commit,
  rollback, and `close()`.
- `before_commit(sess)`: return if `sess.in_nested_transaction()` (§2.3 item 2); otherwise,
  for every store with a non-empty list, raise `CascadeNotRun`. Registered with
  `insert=True`, so it runs BEFORE the paranoia guard's `before_commit` and the caller sees
  the actionable message rather than a paranoia report of the stale state.
- Listener install: `ensure_cascade_guard(session)`, idempotent through a
  `session.info` flag, called from `WildcardIndex.__init__` on a boolean schema only, so a
  pure-union session never carries the listeners.

**The exception.** `CascadeNotRun(ZanzibarError, RuntimeError)`, defined in
`cascade_mark.py`. Why `RuntimeError`: it is a call-ORDER / state error, the same family as
`WriteLockUnsafe`, `UnloggedWriteRefused`, `StaleRead` (all `ZanzibarError, RuntimeError`,
READ `core.py:140`, `setengine/engine.py:62`, `store/source.py:61`). Not `ValueError` (no
argument was bad — contrast `MissingDeltaProcessor`, which is a bad `proc=None` argument), and
not `AssertionError` / `InvariantViolation` (nothing is corrupt yet: the refusal fires BEFORE
the stale state commits). Message (draft): store id, the write op that armed it, then
*"a graph-index write on a schema with boolean (and / but not) relations ran no
DeltaProcessor.run_cascade in this transaction, so committing it would leave the derived
relations stale and the graph index would disagree with the set engine. Either roll back,
or call proc.run_cascade(wm) in this transaction, with wm = outbox_watermark(session,
store_id) captured BEFORE the first write, and commit again; or write through
zanzibar.Store, which does both."* Exported: `zanzibar._LAZY` + the `TYPE_CHECKING` block
(`src/zanzibar/__init__.py`), and `zanzibar.graphindex.__all__`.

**The docstring bound (trap (b))**, verbatim intent: the mark proves a cascade was CALLED in
the transaction after the last unpaired write, not that it was called CORRECTLY. A
`run_cascade(wm)` with a too-high `wm` (rows skipped), or a cascade over a different store's
processor on the same store id, clears it. Execution-side misses inside a cascade that ran
belong to the `'fixpoint'` paranoia tier (TK82); never-scheduled keys to TK85's
`audit_fixpoint`. Also out of reach: raw `ReachabilityIndex` writes (the schema-blind core;
I5 routing is bypassed there too), a Session shared across threads, and a commit issued
through the raw `Connection` rather than the `Session`.

**Trap (a), honoured:** nothing compares the outbox head with a drained frontier. The mark
is pure Python call-order state and never reads the outbox, so the late reconcile-time GC
rows pinned by `tests/test_tk79_outbox_replica.py` cannot misfire it (REASONED).

**Cost statement (the row's trap):** tier = none (always on). Per write: a cached-bool test
on a pure-union schema; on a boolean schema the O(1) dict/list work above. Per commit: one
dict lookup, plus the nested check. No SQL anywhere. No measurement yet; the implement stage
should time `tests/test_matrix.py` before/after and report it (UNVERIFIED: "~free").

### 3.1 The composed path keeps working (REASONED from READ code)

| path | writes | clears | verdict |
|---|---|---|---|
| `store/apply.py::advance_index` (:139), sync `Store._write` | `_apply_row` → `_add/_remove_tuple_trusted` | `proc.run_cascade(wm)` in the same call, before the caller commits | clear before commit |
| `Store._catch_up` (async) | same, per batch | same, per batch, then `commit()` | clear before commit |
| `advance_index` raises mid-batch (`IndexResourceLimit`, `WatermarkGap`, ...) | partial | none | armed; every caller rolls back (`_write` / `_catch_up` / `_record_stall` opens a NEW transaction after the rollback) — so the stall-recording commit is not refused |
| `advance_index(..., proc=None)` on a boolean schema | none | — | refused earlier by `MissingDeltaProcessor` |
| `build_index(bulk=False)` → `_materialise` | `widx.add_tuple` replay | `DeltaProcessor(widx, compiled).backfill()` | clear before commit |
| `build_index(bulk=True)`, `rebuild_index`, `bulk_build` | direct ORM inserts, no widx write method | — | never armed |
| `Store.__init__`, `open_graph_index`, `Store.adopt` | no widx write | — | never armed |
| async `Store._write` (`sync=False`) | log only | — | never armed |

A subtle one, flagged for the implement stage: `advance_index` captures `wm` BEFORE the apply
loop, so its cascade clears exactly the debt it created. Nothing in `src/` writes to a widx
outside these rows (grep 2026-10-22).

## 4. Census (trap (c)): every test/conformance site that would be refused

### 4.1 Method

Empirical, not grep: a pytest plugin (`.scratch/tk158-tk3/tk3_census_plugin.py`) monkeypatches
the four write methods and the two clear methods to SIMULATE §3's mark (boolean schema only,
skipped under `processor_writes`, cleared on run_cascade/backfill success and on root
rollback) and, instead of raising, records:
- `REFUSED_AT_COMMIT` — the test committed while owed (these go red when the check lands);
- `OWED_NEVER_COMMITTED` — the test owed a cascade at teardown but never committed (the
  check cannot see these; they matter for sabotage visibility, not for breakage).
Each record carries the first write site outside `src/` and whether the arming writes
succeeded (`ok`) or raised (`raised`).

**Instrument control (PROBED 2026-10-22):** a two-test witness
(`.scratch/tk158-tk3/witness/test_tk3_witness_probe.py`: a leaf write on
`can_view: viewer but not banned` then `commit()`, and the same with no commit) produced
exactly one record of each kind:
```
{"kind": "REFUSED_AT_COMMIT", ..., "op": "_add_tuple_trusted", "ok": 1, "raised": 0}
{"kind": "OWED_NEVER_COMMITTED", ..., "op": "_add_tuple_trusted", "ok": 1, "raised": 0}
```
and `tests/test_matrix.py` (17 tests, its `GraphBackend.apply` cascades then commits) produced
zero, as it must.

Bound of the instrument: it marks at ENTRY of `_add_tuple_trusted` etc., i.e. slightly BEFORE
§3's placement (it does not skip a write refused by `_assert_derived_exclusivity`). Records
with `ok == 0` are therefore over-counts to be re-read by hand (§4.2 says which).

### 4.2 Result

**Coverage (PROBED 2026-10-22, ~16:03-17:30):** the WHOLE of `tests/` (2932 collected) and
`formal/conformance/` (1246 collected), default `ci` hypothesis profile, no DSN (so
`tests/test_postgres_ha.py` is not collected), run in shards because a single run under the
concurrent 1M benchmark was too slow: one run over `tests/` stopped after test 705 (files
through `tests/test_lookup_oracle.py`), then shards over the remaining files: 392 + 574 + 629
+ 635 passed; conformance: a first run stopped inside `test_conformance_direct_arm.py` after
`test_cli_mode.py` + `test_conformance_bulk_state.py` (33 tests), then shards 572 + 302 + 339
passed. Every shard rc=0, zero failures (the plugin observes, it never raises). **21 records,
all from `tests/`; `formal/conformance/` produced NONE** (its backends,
`formal/conformance/backends.py` :85-90 and :262-289, cascade then commit, READ).

**(A) `REFUSED_AT_COMMIT` — these go red when the check lands.** "Final" = after applying
§3's placement (pure pre-checks do not arm), i.e. records whose only arming write was refused
before mutating are dropped.

| # | test (`tests/…`) | arming site (2026-10-22) | op | final? | classification → fix |
|---|---|---|---|---|---|
| 1 | `test_boolean_compile.py::test_facade_derived_family_exclusivity` | :468 | add, raised (I5 refusal) | **no** (pre-check) | — |
| 2 | same test | :479 leaf write `viewer.0`, then `commit()` | add | yes | SLOPPY: the test is about I5, not staleness → `run_cascade(wm)` before the commit |
| 3 | `test_outbox.py::test_derived_flag_set_only_by_processor_writes` | :112 leaf write then `commit()` | add | yes | SLOPPY → `run_cascade` (or `flush()` in place of `commit()`, the assertion reads `Edge.derived` only) |
| 4 | `test_reg_tk80_remove_node_residue.py::test_an_unreferenced_node_is_still_removable_and_commits_clean` | :478 `remove_node` then `commit()` | remove_node | yes | REMOVE_NODE → cascade after it (see the note below) |
| 5 | `test_reg_tk80_remove_node_residue.py::test_the_refusal_leaves_the_state_untouched` | :500 | remove_node, raised (TK80 refusal) | **no** (pre-check) | — |
| 6 | `test_reg_tk80_remove_node_residue.py::test_the_sanctioned_path_removes_the_recording_then_the_node` | :547 | remove_node | yes | REMOVE_NODE → cascade after it |
| 7-11 | `test_reg_tk91_live_keys_repair.py::` `test_fixture_keeps_the_public_family_the_only_route`, `test_live_keys_of_finds_state_that_outlived_its_leaf`, `test_backfill_repairs_the_stale_grant`, `test_repaired_state_equals_a_fresh_bulk_build`, `test_i9_reports_the_stale_key_at_all` | helper `_route` :179-187 ("no cascade", by its own docstring) | remove | yes | **DELIBERATE STALE STATE** (the module builds a grant that outlived its leaf, to test repair) → `_cascade_check_waived(widx, reason='TK91: builds stale derived state on purpose')` around the uncascaded `_route` call(s) |
| 12-14 | `test_tk113_remove_node_fence.py::test_remove_node_is_exact_or_refused[boolean-user:alice#...]`, `[boolean-user:bob#...]`, `[boolean-user:carol#...]` | :180 | remove_node | yes | REMOVE_NODE → cascade after it (the harness `_G` already has `proc`, :104-123) |
| 15 | `test_tk113_remove_node_fence.py::test_non_vacuity_user_nodes_are_still_removable[boolean]` | :221 | remove_node | yes | REMOVE_NODE → same |
| 16 | `test_wildcard_property.py::test_middle_sync_record_excludes_the_wildcard_entity` | :108 (`_apply`, called at :400 / :403) on `owc_star_ttu.fga` | add/remove | yes | SLOPPY: an I14 instrument control, not a staleness test → `run_cascade` after each `_apply` |

**Final count: 14 refused tests in 7 files**: 3 SLOPPY (rows 2, 3, 16), 6 REMOVE_NODE (rows 4,
6, 12-15), 5 DELIBERATE (rows 7-11, one helper). So the waiver is needed in exactly ONE file,
`tests/test_reg_tk91_live_keys_repair.py`, and §5's waiver-census pin starts as that
one-element list.

**The REMOVE_NODE decision (model, under "Who decides").** `WildcardIndex.remove_node` on a
boolean schema ARMS the mark. Rejected alternative: exempt it because the TK80 / TK113 fences
already refuse the shapes whose removal provably goes stale. Why rejected: those fences prove
specific shapes stale, not the rest exact; `remove_node` retires edges and so emits outbox
rows that only a cascade consumes, and the claim "an admitted `remove_node` never moves
derived state" is UNVERIFIED in general. The fail-closed choice costs these six tests one
`run_cascade` each. ⚠ **Owed in the implement stage, as evidence either way:** after adding
the cascade to rows 4, 6, 12-15, check whether the cascade CHANGED anything (`proc._settle`,
or the reconcile counter idiom of `tests/test_backfill_enumeration.py::_live_arm`). A change
there is a pre-existing `remove_node` staleness bug on a boolean schema, i.e. an equivalence
finding to escalate on the row, not to paper over. (Row 12-14's own oracle comparison,
`'A: diverged after removal'`, already passed WITHOUT a cascade for those three nodes, which
is evidence, not proof, that the answer there is "no change".)

**(B) `OWED_NEVER_COMMITTED` — the check cannot see these, and none needs a change:**

| test | site | why harmless |
|---|---|---|
| `test_backfill_enumeration.py::test_fixture_keeps_the_enumeration_load_bearing`, `::test_live_keys_of_reaches_every_key_the_live_cascade_wrote` | `_bootstrap_arm` → `_route` :173 | the build_index-shaped bootstrap (raw leaf writes, `flush()`, then `backfill`); never commits |
| `test_stored_cache_scope.py::test_a_scope_spanning_a_raw_write_serves_a_stale_answer` | :452 | demonstrates staleness on purpose, never commits |
| `test_tk113_remove_node_fence.py::test_remove_node_is_exact_or_refused[boolean-doc:x#viewer]` | :180, raised | TK113 refusal (pre-check: not armed under §3), then `rollback()` |
| `test_wildcard_remove_node.py::test_remove_node_respects_derived_exclusivity` | :91, raised | I5 refusal (pre-check), never commits |

**What the census did NOT measure:** how many boolean-schema commits clear the mark (the S1
sabotage's blast radius). REASONED large: `tests/test_matrix.py::GraphBackend.apply`,
`tests/parity.py` (:75-87), `formal/conformance/backends.py` all cascade then commit on every
boolean op. S1 will measure it.

## 5. The opt-out (trap (c)): named, greppable, scoped

`zanzibar.graphindex.cascade_mark._cascade_check_waived(widx, reason=...)`, a context manager:
writes made through `widx` (same session, same store) INSIDE the block do not arm the mark.
Rules:
- **`reason` is required and non-empty**, so every site says why it is allowed to commit
  stale derived state (e.g. `'TK74: measures staleness on purpose'`).
- **Underscore name**: test machinery, not a public API, so the 0.1.0 surface does not grow a
  "turn the check off" switch. It is a per-SESSION flag in `session.info`, never a module
  global, so a waiver on one thread cannot open a window on another.
- **Scoped to the writes, not the commit**: a waived block followed by an ordinary write
  still refuses, so a waiver cannot silently cover later code.
- **Pinned**: a census test (`tests/test_tk3_cascade_mark.py::test_waiver_sites_are_the_census`)
  greps `tests/` and `formal/conformance/` for `_cascade_check_waived(` and asserts the set of
  files equals a declared list carried in the test (initially
  `{'tests/test_reg_tk91_live_keys_repair.py'}`, per §4.2), so a new waiver is a reviewed diff, never
  a quiet one. Sabotage: add a waiver to an unlisted file → red.

Preferred fix per site, in order: (1) add the missing `run_cascade` (the test was sloppy);
(2) roll back instead of committing (the test never needed the commit); (3) waive, only where
the test exists to observe uncascaded or corrupt state.

## 6. Test plan — `tests/test_tk3_cascade_mark.py`

Positive pins (a refusal must happen) — each one writes, does NOT cascade, commits, and
expects `CascadeNotRun`:
- W1 add (`widx.add_tuple` leaf write on `viewer but not banned`);
- W2 remove (`remove_tuple` after a properly cascaded add);
- W3 `remove_node` on an unrouted, unreferenced node of a boolean schema;
- W4 `WildcardIndex.backfill()` on a boolean schema;
- W5 a write refused AFTER mutating (a fan-out-cap refusal), caught, then commit → refused;
- W6 the message names the store id and both remedies (`run_cascade`, `Store`).

Negative pins (no false refusal):
- N1 write + `run_cascade(wm)` + commit → ok; N2 write + `DeltaProcessor.backfill()` + commit
  → ok;
- N3 write + `rollback()` + an unrelated commit → ok (rollback clears);
- N4 write inside `begin_nested()`, savepoint rolled back, commit → ok; the same with the
  savepoint RELEASED → refused (the write survived);
- N5 pure-union schema, write without cascade, commit → ok (and the listeners are not even
  installed: assert on `session.info`);
- N6 a write refused BEFORE mutating (`_assert_derived_exclusivity`), commit → ok;
- N7 two stores on one session: owe on `a`, cascade on `b` → still refused, naming `a`;
- N8 two threads, one Session each: thread A owes, thread B commits fine; then A refused;
- N9 recoverability: after the refusal, `run_cascade(wm)` then `commit()` succeeds and
  `audit_fixpoint()` is clean (uses §2.3 item 1);
- N10 the composed path: `Store(sync=True)` writes, `Store(sync=False)` + `catch_up`,
  `build_index(bulk=False)` and `bulk=True` on a boolean schema, all commit;
- N11 `processor_writes` window: `proc.reconcile(...)` / `audit_fixpoint()` then commit → ok;
- N12 a cascade that RAISES (monkeypatched `_run_cascade`), caught, commit → refused (the
  clear is at the end, not the start).

Regression runs (as the brief lists): `tests/test_matrix.py`, `tests/test_hypothesis.py`
(ci profile), `tests/test_connectedstore*.py`, every `formal/conformance` module touching a
WildcardIndex (`test_conformance_graph.py`, `_state.py`, `_remove.py`, `_direct_arm.py`,
`_enum.py`, `_nary_strata.py`, `test_graphadmission_scope_pin.py`,
`test_w4fragment_scope_pin.py`), plus the export pins in `tests/test_tk123_top_level.py`
and the userdocs tests (`tests/test_userdocs_*.py`), and the census sites of §4.2 after they
are fixed.

## 7. Sabotage plan (trap (d), mandatory)

Per `docs/sabotage-procedure.md`: narrowest plausible weakening, literal output recorded in
the test docstring and the commit message.

| id | sabotage | must go red | why it is the plausible one |
|---|---|---|---|
| S1 | delete the `clear(...)` call in `run_cascade` | every boolean-schema commit in the suite: `test_matrix.py`, the ParityEngine, N1 | the brief's (d.1); the innocent refactor that moves the wrapper |
| S2 | make `before_commit` return early (hook dropped) | W1–W5 | the brief's (d.2) |
| S3 | mark only in `_add_tuple_trusted` (forget remove) | W2 | one write path forgotten is the likeliest regression |
| S4 | drop the `after_transaction_end` root clear | N3 | rollback-clear is the half nobody exercises |
| S5 | key the mark by `id(widx)` instead of `session.info` | N7-style two-facade test | the "obvious" simpler design of §2.2 (i) |
| S6 | move the clear to the START of `run_cascade` | N12 | looks equivalent, is not |
| S7 | skip the `in_nested_transaction()` test in the hook | N4 (released savepoint mid-txn) | §2.3 item 2 is easy to miss |
| S8 | drop the `processor_writes` skip | N11 (and every cascade re-arms: matrix red) | the processor writes through the public API |
| S9 | add `_cascade_check_waived` to an unlisted test file | the waiver census pin | §5 |
| M0 | control: an edit with a NAMED expected red, run first | its named test only | instrument control (sabotage-procedure "A sweep needs an M0") |

Also control the INSTRUMENT: run W1 with the check on and confirm it is red for the right
reason (`CascadeNotRun`, not a paranoia `InvariantViolation`), which is what `insert=True`
buys.

## 8. Lean / CORRESPONDENCE impact

READ `formal/CORRESPONDENCE.md` 2026-10-22: §5 row `GraphIndex/CascadeStrata.lean::runCascade2`
maps to `src/zanzibar/graphindex/processor.py::DeltaProcessor.run_cascade`, described as "a
thin wrapper installing TWO perf caches ... neither is part of the modeled algorithm"; §6 row
`GraphIndex/CascadeStrataAssemble.lean::ReachedByW3d2E` = `ReachedBy` is "the write path as
*admitted write + same-transaction cascade*" (`store/apply.py::advance_index` →
`run_cascade`, and `tests/test_matrix.py` `GraphBackend.apply`). SEMANTICS §11 A1 (decided
2026-10-13) already accepted that Lean cannot speak to Python call discipline and that
baking the cascade into each modelled write op is the faithful model.

Verdict (REASONED): **no Lean change.** The mark adds no step to any modelled algorithm: it
reads and writes only `session.info`, never index state, and the clear is bookkeeping after
`_run_cascade` returns. What it does is make the Python side MECHANICALLY match the
precondition the model already assumes (`ReachedBy` only has same-transaction-cascade
constructors). Owed in the implement stage, in `formal/CORRESPONDENCE.md` (not in this lane's
no-touch list, but the anchors are gate-checked, so cite only symbols that exist after the
build):
- the §5 `run_cascade` row note: "...and clears the `TK3` cascade-owed mark
  (`src/zanzibar/graphindex/cascade_mark.py`), call discipline, not modelled";
- the §6 `ReachedBy` row: the same-transaction-cascade premise is now enforced at the commit
  boundary by `cascade_mark` for every `WildcardIndex` write on a boolean schema (bound: §3).
`verify.sh lean` must then be re-run (the anchor check resolves the new `file::symbol`s).

## 9. What the orchestrator owes the files this lane must not touch

- `CHANGELOG.md`: "Added: commits on a boolean schema that wrote to a `WildcardIndex`
  without running `DeltaProcessor.run_cascade` are refused with the new `CascadeNotRun`."
- `userdocs/`: `reference/exceptions.md` (new class, base `RuntimeError`, when raised, the
  two remedies); the `backends-direct` how-to (which the row says waits on TK3) must show
  the watermark → write → `run_cascade(wm)` → commit pattern and the refusal;
  `reference/changelog.md`.
- `formal/FINAL_REVIEW.md`: regenerate the counts block (`python -m
  formal.conformance.doc_counts --generate`) once the new tests land (counts move).
- `HANDOFF.md`, `docs/history/session-log.md`: the session write-back.
- Also, in-lane but gate-pinned: `tests/test_tk123_top_level.py::_BUILTIN_BASE` gains
  `'CascadeNotRun': RuntimeError` (the census test refuses an unclassified exception), and
  `formal/verify.sh`'s `MIN_TESTS_ALL` floor rises by the new test count (orchestrator's call,
  since it owns the gate).

## 10. Next action

Implement stage: build `cascade_mark.py` and the four
call sites, land `tests/test_tk3_cascade_mark.py` (W/N pins) RED against a no-op
`before_commit` first, fix the §4.2 census sites, then run §7 S1–S9 and record outputs.
