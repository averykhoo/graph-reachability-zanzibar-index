# TK111 / TK112 / TK113 -- stall-aware freshness and the live-bug fixes (2026-10-02b)

ACTIVE-PLAN (`docs/README.md` sec 3). Corrections are appended dated at the top. FROZEN when
`TK111`, `TK112` and `TK113` are all closed. The task rows are the index; this file is the body.

Provenance labels: **READ** (the code was read first-hand this session), **REASONED**, **PROBED**
(a probe was run and its literal output is quoted), **UNVERIFIED**.

## 0. Why this order

The user ranked the three known live correctness bugs ahead of `P4` on 2026-10-02b: `TK111`
to `NOW`, then `TK112` and `TK113` at `NEXT`. `TK111` and `TK112` share one mechanism. An
async log row that the index cannot apply stalls `ConnectedStore.catch_up` forever, and an
untokened `ConnectedStore.check` keeps serving the stale index, revoked grants included.
The witnesses are on the rows and in `docs/p10-scope-audit-2026-09-27.md` sec 5, H2 and H4.
The shared fix lands first because it closes the fail-open for both poison sources at once.

## 1. Sites (READ 2026-10-02b; line numbers rot, symbols do not)

- `connectedstore/store.py::ConnectedStore._fresh_enough` returns `at_least is None or
  cursor.applied_log_id >= at_least`. The `None` arm is documented as "bounded-stale by
  design". A poison row makes the staleness UNBOUNDED, and nothing distinguishes the two cases.
- `connectedstore/store.py::ConnectedStore.catch_up` rolls back and re-raises on any
  exception. It records nothing, so a reader cannot tell "the worker is behind" from "the
  worker can never advance".
- `connectedstore/apply.py::advance_index` sets `cursor.applied_log_id = head` and flushes.
  The caller commits.
- `connectedstore/apply.py::_apply_row` re-raises `ClosureFanoutExceeded` unchanged and
  promotes `ValueError` to `InvariantViolation`. `OverflowError` (SQLite) and `DataError`
  (PostgreSQL) are not `ValueError`, so they escape as themselves.
- `connectedstore/models.py::IndexCursorV1` has `index_store_id`, `source_store_id` and
  `applied_log_id`. There is no migration machinery anywhere in `connectedstore/`,
  `index_v4/` or `setengine/` (grep for `ALTER TABLE|add_column|migrat`, READ). Tables come
  from `SQLModel.metadata.create_all`, so a new nullable column needs no migration on a
  fresh database.

## 2. Decisions (REASONED; the model's call per `CLAUDE.md` "Who decides")

- **D1 -- persist the stall on the cursor row.** Add `IndexCursorV1.stalled_after: int |
  None`, the `applied_log_id` the apply step was stuck at, and `stall_error: str | None`
  for operators. A stall counts only while `stalled_after == applied_log_id`, so any
  successful advance invalidates it even if nothing clears it. `advance_index` clears it
  anyway. It must be PERSISTED, not held in memory, because the reader that serves the
  stale ALLOW is typically a different `ConnectedStore` instance (a replica) whose own
  `catch_up` never runs.
- **D2 -- `catch_up` records a stall on ANY failure, then re-raises the original.** It
  records in a fresh transaction after the rollback. This includes transient failures
  (`WatermarkGap`, `SQLITE_BUSY`, a lost connection). That is deliberate: a false stall
  costs only a set-engine fallback until the next successful batch, while a missed stall
  is the fail-open. Classifying errors as "poison" versus "transient" would put the
  fail-open back the first time the classifier is wrong.
- **D3 -- the untokened `check` on a stalled index is served by the set engine**, after
  `catch_up_evaluator`, which is O(delta). Tokened checks are UNCHANGED: a token at or
  below `applied_log_id` is satisfied by the index whether or not it is stalled, because
  the index really does reflect the log through that id.
- **D4 -- an untokened `lookup` or `lookup_reverse` on a stalled index REFUSES** with a new
  `IndexStalled(LookupNotFresh)`. The lookup surfaces have no fallback (see
  `LookupNotFresh`), and an unbounded-stale enumeration is how a revoked principal stays
  listed. A tokened lookup that the index satisfies is still served.
- **D5 -- the stall is only as fresh as the reader's snapshot.** It is read from the
  in-memory `cursor`, the same object tokened reads trust first, so a replica sees it after
  `refresh()`, its normal poll. The alternative, a per-check cursor re-read, puts a
  database round trip on every untokened check to cover a window the replica already
  accepts for every other write. Not taken.
- **Out of scope for the shared fix, owned by the rows:**
  - `TK111`: a clean admission refusal for the overflow on the SYNC path. Today it fails
    closed with a raw `OverflowError` or `DataError`.
  - `TK111`: async overflow stays a permanent stall, but reads are now correct. Rebuilding
    the index from scratch is the operator's recovery path.
  - `TK112`: (1) the subtrahend-leaf exemption from the cap, and (2) whether the async apply
    should cap at all. Once a row is logged, the cap can no longer refuse the write; it
    can only refuse to materialise it.
  - `TK113`: the `remove_node` refusals.

## 3. Status

| step | what | state |
| --- | --- | --- |
| S1 | D1-D5 implemented (`connectedstore/models.py::IndexCursorV1.stalled_after`, `connectedstore/store.py::ConnectedStore._record_stall` / `index_stalled` / `IndexStalled`, `connectedstore/apply.py::advance_index` clears) | LANDED 2026-10-02b |
| S2 | permanent tests, `tests/test_tk111_stall_aware_freshness.py` (5 tests) | LANDED 2026-10-02b |
| S3 | module mutation sweep with an M0 control (table below) | DONE 2026-10-02b, every mutant red |
| S4 | TK112: scouted 2026-10-03 (sec 6), DECIDED and landed 2026-10-03b (sec 7) | DONE 2026-10-03b, TK112 closed |
| S5 | TK111 clean path-count refusal (sync, async apply, both build constructors) | DONE 2026-10-03b, TK111 closed; residual async recovery is TK121 |
| S6 | TK113 refusals | moved to `docs/tk113-remove-node-fence-2026-10-03.md` |
| S7 | correct the CLAUDE.md "removals are exempt" bullet, the `core.py` comment, the TK33 premise, spec-deviations 2026-07-29c | DONE 2026-10-03b |

## 4. Scouting for the next session (READ 2026-10-02b unless labelled)

**`TK112` (1), the subtrahend exemption, is not a one-line exemption.** The cap is enforced
in `index_v4/core.py::ReachabilityIndex` (the `count > 0 and self.max_closure_fanout` test,
inside the edge-add path). That layer sees node ids, not leaf semantics, so an exemption
has to be passed down from `RuleSet.apply` / `WildcardIndex._add_tuple_trusted`, or decided
from `schema_info.leaf_families` plus the leaf's POLARITY. Polarity is the hard part
(REASONED): in `a but not (b but not c)`, `c`'s leaf is a subtrahend of a subtrahend, so
adds on it are GRANTS. "Exempt every subtrahend leaf" is therefore wrong; the exemption
must be "the leaf's net polarity in the owning plan is negative". The plan tree carries
`positive` in `zanzibar_utils_v1.py::_build_plan_tree::build`, so the compiler can emit a
`negative_leaf_families` set alongside `leaf_families`. That is the proposed shape,
UNVERIFIED. Case (b), the un-ban REMOVE capped through
`index_v4/processor.py::DeltaProcessor._write_derived`, fails CLOSED: it refuses a grant
restoration. It is an availability defect, not a fail-open, so rank it below (a). Case
(c), a capped async row, is closed by S1 for READS. The open question is whether the async
apply should cap at all (D-next, undecided).

**`TK113`: routing sources are not just `RewriteFilter` sources.** In the row's witness,
`doc:x#editor` fans to `['editor', 'viewer.0']` under `viewer: editor but not blocked`.
`editor` is a `Computed` arm, so the fan-out comes from a `Rule` emitted by
`zanzibar_utils_v1.py::_emit_leaf_expr` (`Computed`/`TTU` -> `_rewrite_rule`), not from a
`RewriteFilter`. A refusal keyed on "matched by a RewriteFilter" would miss the witness
(REASONED). The fence must be computed from every compiled Rule/RewriteFilter whose
target relation is in `leaf_families`. UNVERIFIED: whether a PURE-union `Computed`
(`viewer: editor`, no boolean) has the same `remove_node` hole. The row says "boolean
routing source", and nobody has probed the pure case. Probe it before scoping the fence.

## 5. S3 evidence: the mutation sweep (PROBED 2026-10-02b)

The runner was `.scratch/tk111/sweep.py` (gitignored; the table IS the record). Each mutant
was applied in place, `pytest tests/test_tk111_stall_aware_freshness.py` was run, and the
file was restored in `finally`. Afterwards, `git diff --stat -- connectedstore` showed only
the intended change. The literal tails from the first pass (2026-10-02b), against 4 tests:

```
M0 control: flip a test claim            rc=1 | 1 failed, 3 passed  red: [test_transient_failure_...]
M1 _fresh_enough untokened always fresh  rc=1 | 4 failed            (the pre-fix line)
M2 _record_stall in-memory, no commit    rc=1 | 3 failed, 1 passed
M3 catch_up does not record the stall    rc=1 | 4 failed
M4 stalled branch serves the index       rc=1 | 4 failed
M5 stalled branch skips catch_up_eval    rc=0 | 4 passed            INERT
M6 untokened stalled lookup served       rc=1 | 3 failed, 1 passed
M7 advance_index never clears marker     rc=1 | 1 failed, 3 passed
M8 index_stalled ignores equality rule   rc=0 | 4 passed            INERT
M9 M7+M8 (stall never ends)              rc=1 | 2 failed, 2 passed
```

**Both INERT rows were real holes, and each has its own explanation.**
- **M5 was inert because no test's evaluator lagged the log.** The writer's own evaluator
  holds its writes in memory, and `refresh()` rebuilds the evaluator. This was fixed by
  adding `test_replica_polling_by_rollback_gets_a_caught_up_set_engine_answer`, a reader
  that polls with a bare `rollback()`.
- **M8 was inert because the equality rule is redundant while `advance_index` clears the
  marker.** `connectedstore/build.py::build_index` is the only other cursor writer, and it
  refuses an existing cursor (READ). The rule is now pinned directly as a stated contract,
  at the end of `test_transient_failure_stalls_until_the_next_good_batch`.

Second pass (2026-10-02b), against 5 tests:

```
M0 control                               rc=1 | 1 failed, 4 passed  red: [test_transient_failure_...]
M5 stalled branch skips catch_up_eval    rc=1 | 1 failed, 4 passed  red: [test_replica_polling_by_rollback_...]
M8 index_stalled ignores equality rule   rc=1 | 1 failed, 4 passed  red: [test_transient_failure_...]
```

## 6. `TK112` scouting, 2026-10-03 (subagent PROBED + orchestrator READ of its outputs)

**This SUPERSEDES the `TK112` row's 2026-10-02b NEXT ACTION and corrects sec 4 above.**
Provenance: a read-only scout subagent wrote probes `p1_polarity.py`, `p2_runtime.py`,
`p3_global_sign.py` and `p4_sibling.py`, plus a report, under the gitignored
`.scratch/tk112-scout/`. The orchestrator read `p2_out_cap20.txt` and `p3_out.txt`
first-hand (2026-10-03). Everything else below is agent-PROBED or agent-READ and is
labelled that way. Nothing here has been re-run by the orchestrator.

**Corrections to the row and to sec 4.**
- **"Exempt edges routed onto an Exclusion's subtrahend leaf" does NOT fix the row's own
  witness, A2.** Orchestrator READ of `p2_out_cap20.txt`: the refused edge is the PUBLIC
  one, `+edge group:big#member -> doc:d#banned  anc=30 desc=0 fanout=30`. Every raw write is
  routed onto the public relation AND its leaf (`['banned', 'viewer.1']`), and the public
  edge hits the cap first. So the exemption has to be decided per raw write, over
  everything that write is routed onto.
- **Sec 4's "polarity needs a new compiler output" is wrong** (agent READ). The sign is
  already stored as `LeafFamily.positive` in `CompiledBooleans.namespace`, computed by
  `zanzibar_utils_v1.py::_build_plan_tree::build`. That function flips the sign only on
  the subtrahend side of `but not` and passes it straight through `and` and `or`. Each
  `alloc()` mints a fresh leaf, so a leaf family has exactly one per-plan sign.
- **The sign that matters is GLOBAL, not per-plan.** Orchestrator READ of `p3_out.txt`,
  case `g_computed_neg`: under `restricted: everyone but not viewer`, viewer's own leaves
  are per-plan positive (`viewer.0`), yet a write onto them REVOKES `restricted`.
  `p2_out_cap20.txt` case G shows that write refused at cap 20, with `restricted u0
  after: True | set engine: True`. Signs must therefore propagate through every
  reference to a boolean-defined relation: a computed ref, a `[T#rel]` userset
  restriction, or a TTU target. The prototype fixpoint is
  `.scratch/tk112-scout/p3_global_sign.py::global_signs` (agent-PROBED on 7 hand-written
  schemas, NOT a generated differential).
- **Revocations can touch no leaf at all.** Orchestrator READ of `p2_out_cap20.txt` case
  K: adding `user:victim` to an already-banned `group:big` is a plain `group#member` add,
  `anc=0 desc=60`, and its descendants include `('doc','viewer.1')`. It was REFUSED, and
  both backends keep the user allowed. Agent-PROBED `p4_sibling.py`: with `also: member`
  and `banned: [group#also]`, the refused edge is `group:big#member`, which reaches no
  revocation family itself; its sibling `group:big#also` is the edge that reaches the leaf.
- **Fan-out is linear only when the edge's target is a leaf.** Orchestrator READ of
  `p2_out_cap20.txt`: leaf nodes have no outgoing edges. K-type adds cost |anc| x |desc|.
- **D3 (the un-ban REMOVE) fails CLOSED.** Orchestrator READ: the refused edge is
  `+edge user:u0#... -> doc:d#viewer ... derivedctx=True`, a pure GRANT written through
  `DeltaProcessor._write_derived`. Leaving it capped is correct.

**Every path that reaches the cap** (agent READ; line numbers dated 2026-10-03):
- The cap itself is the `count > 0` test in
  `index_v4/core.py::ReachabilityIndex._add_direct_edge_unsafe_impl`.
- It is reached from `add_edge`, `add_edge_by_id` and `_add_edge_locked`.
- Through `WildcardIndex._add_tuple_trusted` it is reached from
  `connectedstore/apply.py::_apply_row` (sync and async), from
  `connectedstore/build.py::build_index` (non-bulk) and from
  `DeltaProcessor._write_derived`.
- Wildcard bridge adds also reach it.
- Removals, `bulk_build` and `bulk_backfill` are never capped.
- Precedent for passing a flag down the stack: the thread-local
  `ReachabilityIndex._writing_derived`.

**Proposed design** (agent, REASONED; NOT yet decided by the orchestrator):
1. Compute `revocation_families` with the global fixpoint in `_compile_booleans`, and
   carry it on `CompiledBooleans` / `SchemaInfo`.
2. At the cap site, refuse only if neither the target's family nor any of its descendants'
   families is in `revocation_families`. The site's position already guarantees that a
   refusal leaves no partial state. This covers callers that have no row context:
   processor writes, bridges, and the non-bulk `build_index`.
3. In `_apply_row`, decide per ROW over the routed list, so that the sibling case is
   exempt too.
4. Reword the "removals are exempt" contract to "revocations are exempt".
5. Positive pins, each sabotaged: A2, G, K and the sibling case. Still-capped controls:
   the grant (case b) and D3.

**THE OPEN DECISION, to make and record on the row before any code** (orchestrator,
REASONED). Cases K and G show that on a schema with any `but not`, almost every edge
upstream of a negative family is "revocation-capable". A sound exemption therefore
switches the cap OFF for most of the graph on exactly those schemas. That is a real
trade-off, not a detail:
- **(i)** Exempt every revocation-capable write. Revocations never fail, but the
  blast-radius bound mostly goes away on boolean schemas.
- **(ii)** Keep capping, and accept that a refused revocation is LOUD. A2 refuses with an
  error, the backends agree, and the caller knows the ban did not land. This is an
  operational fail-open, not a divergence. Document it instead of fixing it.
- **(iii)** A separate, higher cap for revocation-capable writes.

The equivalence goal (`CLAUDE.md` "Who decides") is not at stake in any of the three: in
every case the backends agree. This is a policy call on the cap. Because it is not a
user-goal question, it is the model's call, and a `fable` consult is warranted.
Separately, the async half (whether `catch_up` should cap at all) is still undecided.

## 7. `TK112` cap-policy DECISION, 2026-10-03b (REASONED; `fable` consult, adopted by the session)

The user's steer (chat, 2026-10-03b): the result "shouldn't be broken or too surprising", and
they guessed "make the cap less strict". The session asked a `fable` subagent to decide
against that and the equivalence goal. It read sec 4 and sec 6, the cap site, `_apply_row`,
`ConnectedStore._write` / `catch_up` / `_record_stall`, and the `reg17` docstring. Its report
was `.scratch/tk112-decision/fable.md`, which is transcribed here. The session agreed with it
and adopted it.

**DECISION: option (iv). The cap is a SYNC-ADMISSION bound only.** None of (i)-(iii) from
sec 6 was taken.
- **Sync** (`ConnectedStore(sync=True)`, and direct `WildcardIndex` / `ReachabilityIndex`
  writes): unchanged, which is option (ii). Every edge ADD is capped, whatever its sign.
  That covers the `but not` ban (A2), a member-add into a banned group (K), the sibling case,
  and the un-ban REMOVE that restores a grant through `DeltaProcessor._write_derived` (D3).
  The refusal is atomic across the log, the set engine and the index:
  `ConnectedStore._write` rolls back and calls `refresh_evaluator()`. It is also loud:
  `ClosureFanoutExceeded` names the fix. There is no polarity classifier and no second cap.
- **Async** (`ConnectedStore.catch_up`) **and the non-bulk `build_index`**: the cap is NOT
  consulted. `ReachabilityIndex` gets a thread-local suspend window (the `_ThreadFlag`
  precedent of `_writing_derived`). Both callers enter it, and an over-cap apply inside it
  logs one warning instead of refusing. The TK111 stall marker and the read fallback stay
  exactly as landed. They still cover the path-count bound (`PathCountExceeded`, which no
  window suspends) and transient failures.

**Why** (the agent's reasoning, condensed; the session concurs):
- On async the row is already committed truth. The cap cannot refuse it; it can only turn
  "apply slowly" into "never apply until an operator raises the cap". The data will not
  shrink, so that stall is never transient, and the cap buys only unavailability.
- The cap's stated purpose does not hold on async: that one write holds the SOURCE lock and
  stalls every writer. `catch_up` holds only the graph store lock, and writers take the
  source lock. Absorbing a long apply is what async exists for.
- Async was the only path where the writer never sees the refusal, so this removes the only
  SILENT case. Sync was always loud, and a loud, atomic refusal on which both backends agree
  is not a fail-open: the ban is absent from all three, and the caller is told.
- Options (i) and (iii) both need the global-sign fixpoint (sec 6). That is a prototype
  checked on 7 hand-written schemas with no generated differential, and cases K and G show
  it would classify nearly every add on a boolean schema as revocation-capable. So (i)
  amounts to "cap off on boolean schemas" behind a hidden classifier. An operator who wants
  that can set the cap to `0` and get it honestly. (iii) adds a knob nobody can derive, with
  the same classifier risk.
- So "less strict" lands where it is free and principled (async), and the one place where
  the bound still means something keeps it.
- Caveat: on SQLite (dev/test only) a long async apply still blocks the file's single
  writer. PostgreSQL is unaffected.

**Consequences for the row's prose.** "Removals are exempt because a cap that can refuse a
revocation is a fail-open" is retired. The contract is now: the cap bounds closure GROWTH at
sync admission; it is atomic and loud; a revocation-shaped ADD is capped like any other add;
the REMOVE op itself is never capped; async apply and `build_index` are never capped. The
"async capped row stalls" half of `TK112` stops existing. A stall can now come only from
`PathCountExceeded` or a transient failure.

**TK111 S5 landed in the same session (2026-10-03b, PROBED first-hand).** The path-count
bound is `index_v4/core.py::MAX_PATH_COUNT`, the int4 ceiling on both dialects. It is
checked in `ReachabilityIndex._add_indirect_edges_batch_unsafe` before the first mutation,
and it covers the direct edge's own row through `direct_pair`. The refusal is
`zanzibar_utils_v1.py::PathCountExceeded`, under a new base `IndexResourceLimit` that also
parents `ClosureFanoutExceeded`; `connectedstore/apply.py::_apply_row` catches the base. The
probe used `.scratch/tk111-s5/probe.py`, sync, SQLite, with the sec 1 diamond:

```
K=30: 122 of 122 writes admitted
K=31: 124 of 125 admitted; refused ('member','group','B30','member','group','L31')
      PathCountExceeded: path count bound exceeded: this edge would give closure row
      (3 -> 96) 2147483648 distinct ...
      after the refusal: graph check(u member L31) == oracle == True; next write admitted
```

**Mutation sweep (PROBED first-hand 2026-10-03b; runner `.scratch/tk112-sweep/sweep.py`,
gitignored, so this table IS the record).** Each mutant was applied in place by an anchor that
had to match exactly once, then four modules were run (`tests/test_tk112_cap_policy.py`,
`tests/test_tk111_path_count_bound.py`, `tests/test_tk111_stall_aware_freshness.py`,
`tests/test_reg17_closure_fanout_cap.py`), and the file was restored in `finally`.
`git status` afterwards showed only the intended edits. Every mutant went red, and M0 (the
control) was attributed to the test it flipped. Literal lines, truncated at 200 chars:

```
BASELINE rc=0 | 29 passed in 24.73s
M0 control: flip a claim in the sync test: rc=1 red | 3 failed, 26 passed in 26.93s | ['test_sync_over_cap_write_is_refused_loudly_and_atomically[ban]', 'test_sync_over_cap_write_is_refused_loudly_...
M1 catch_up opens no window: rc=1 red | 4 failed, 25 passed in 23.45s | ['test_fanout_over_cap_row_no_longer_stalls_the_async_apply', 'test_async_apply_is_never_capped[ban]', 'test_async_apply_is_n...
M2 build_index opens no window: rc=1 red | 1 failed, 28 passed in 23.88s | ['test_non_bulk_build_index_is_never_capped']
M3 suspended branch never taken: rc=1 red | 5 failed, 24 passed in 23.16s | ['test_fanout_over_cap_row_no_longer_stalls_the_async_apply', 'test_async_apply_is_never_capped[ban]', 'test_async_apply_...
M4 cap suspended everywhere (sync too): rc=1 red | 8 failed, 21 passed in 24.34s | ['test_cap_boundary_is_the_exact_region_size', 'test_cap_through_connectedstore_is_a_refusal_not_a_corruption_repo...
M5 no warning on a suspended over-cap row: rc=1 red | 4 failed, 25 passed in 24.00s | ['test_fanout_over_cap_row_no_longer_stalls_the_async_apply', 'test_async_apply_is_never_capped[ban]', 'test_as...
M6 window not restored on exit: rc=1 red | 5 failed, 24 passed in 25.64s | ['test_fanout_over_cap_row_no_longer_stalls_the_async_apply', 'test_async_apply_is_never_capped[ban]', 'test_async_apply_i...
M7 window not thread-scoped: rc=1 red | 1 failed, 28 passed in 23.72s | ['test_suspend_window_is_reentrant_and_thread_scoped']
M8 _write apply-failure arm skips evaluator rebuild: rc=1 red | 3 failed, 26 passed in 26.58s | ['test_sync_over_cap_write_is_refused_loudly_and_atomically[ban]', 'test_sync_over_cap_write_is_refus...
P1 direct_pair never passed: rc=1 red | 1 failed, 28 passed in 26.60s | ['test_direct_edge_row_alone_is_checked']
P2 bound is exclusive (>=): rc=1 red | 1 failed, 28 passed in 26.48s | ['test_bound_is_inclusive_and_exact[8-False]']
P3 removals checked too: rc=1 red | 1 failed, 28 passed in 27.69s | ['test_refusal_leaves_no_partial_state_and_removals_are_never_refused']
P4 _apply_row escapes only ClosureFanoutExceeded: rc=1 red | 5 failed, 24 passed in 30.60s | ['test_bound_is_inclusive_and_exact[7-True]', 'test_sync_overflow_is_a_clean_refusal_at_the_int4_ceiling...
P5 PathCountExceeded not a refusal type: rc=1 red | 5 failed, 24 passed in 33.30s | ['test_bound_is_inclusive_and_exact[7-True]', 'test_sync_overflow_is_a_clean_refusal_at_the_int4_ceiling', 'test_...
P6 bound one too high (2**31): rc=1 red | 4 failed, 25 passed in 26.68s | ['test_sync_overflow_is_a_clean_refusal_at_the_int4_ceiling', 'test_overflow_poison_row_stalls_and_untokened_check_stops_se...
P7 direct pair not in the checked set: rc=1 red | 1 failed, 28 passed in 26.30s | ['test_direct_edge_row_alone_is_checked']
DONE
```

**The bulk constructor's bound, sabotaged separately (PROBED 2026-10-03b).** Added after the sweep:
`index_v4/bulk_build.py::bulk_build` applies `MAX_PATH_COUNT` too. Replacing its test with
`if False:` turned `tests/test_tk111_path_count_bound.py` red: `1 failed, 9 passed`,
`FAILED ...::test_both_build_index_constructors_apply_the_same_bound[7-True-True]`. The
original bytes were restored from a copy.

## 8. Salvage from `.scratch/tk112-scout/` (transcribed 2026-10-03b, before that directory was deleted)

Sec 6 pointed at this directory, and option (i) would have needed the prototype. Option (i)
was NOT taken (sec 7). The two artifacts a future revisit would need are copied here
verbatim, so the directory could be deleted.

**The scout's polarity probe** (`p1_polarity.py`, agent-PROBED 2026-10-03; literal excerpt
from its `report.md` sec Q2):
```
a  viewer: grant but not banned        -> leaf viewer.0 positive=True ; viewer.1 positive=False
   write doc:d#banned@group:big#member routes to: ['banned', 'viewer.1']
b  viewer: a but not (b but not c)     -> viewer.0 True ; viewer.1 False ; viewer.2 True   (c is a GRANT: flip is correct)
c  viewer: (a and b) but not c         -> viewer.0 True ; viewer.1 True ; viewer.2 False
d  viewer: a and b                     -> NEGATIVE leaf families: []
e  viewer: grant but not [user, group#member] -> viewer.1 positive=False storage=True ; write doc:d#viewer@... routes to ['viewer.1']
f  viewer: (grant or banned) but not banned -> write doc:d#banned@... routes to ['banned', 'viewer.0', 'viewer.1']
g  viewer: grant but not banned ; restricted: everyone but not viewer
   -> plan restricted: leaf 'viewer' kind=derived-computed positive=False ; NEGATIVE leaf families: [('doc','viewer.1')] only
   write doc:d#grant@... routes to ['grant', 'viewer.0']   (both "positive" per-plan, yet it REVOKES restricted)
h  viewer: grant (pure) ; restricted: everyone but not viewer
   write doc:d#grant@group:big#member routes to: ['grant', 'restricted.1', 'viewer']
```

**The runtime probe at cap 20** (`p2_out_cap20.txt`, literal, lines truncated by the probe
itself):
```
CAP=20
== A2: grant but not banned; ban a 30-member group ==
  ban group:big: REFUSED closure fan-out cap exceeded: this edge would materialise 30 closure rows (30 ancestors x 
     +edge group:big#member -> doc:d#banned  anc=30 desc=0 fanout=30 derivedctx=False <-- over cap
           object+desc families: [('doc', 'banned')]
  edge rows before/after ban: 33 33
  viewer u0: True | set engine: True
  leaf nodes / edges whose SUBJECT is a leaf node: (31, 33)

== K: revocation by a PURE add (group membership) -- no leaf routed ==
  viewer victim d0 before: True
  add victim to group:big (bans victim on d0..d29): REFUSED closure fan-out cap exceeded: this edge would materialise 60 closure rows (0 ancestors x 6
     +edge user:victim#... -> group:big#member  anc=0 desc=60 fanout=60 derivedctx=False <-- over cap
           object+desc families: [('doc', 'banned'), ('doc', 'viewer.1'), ('group', 'member')]
  viewer victim d0 after: True | set engine: True

== G: grant (per-plan POSITIVE leaf) that revokes restricted = everyone but not viewer ==
  restricted u0 before: True
  grant group:big on doc:d (revokes restricted for u0): REFUSED closure fan-out cap exceeded: this edge would materialise 30 closure rows (30 ancestors x 
     +edge group:big#member -> doc:d#grant  anc=30 desc=0 fanout=30 derivedctx=False <-- over cap
           object+desc families: [('doc', 'grant')]
  restricted u0 after: True | set engine: True

== D3: un-ban REMOVE whose processor consequence is a capped derived ADD ==
  un-ban REMOVE: REFUSED closure fan-out cap exceeded: this edge would materialise 30 closure rows (0 ancestors x 3
     +edge user:u0#... -> doc:d#viewer  anc=0 desc=30 fanout=30 derivedctx=True <-- over cap
           object+desc families: [('doc', 'viewer'), ('folder', 'reader.0')]
  leaf nodes / edges whose SUBJECT is a leaf node: (33, 4)
```

**The global-sign fixpoint prototype** (`p3_global_sign.py`, agent-written, PROBED on 7
hand-written schemas only, no generated differential). It imports `PDerivedComputed`,
`PDerivedUserset`, `PDerivedTTU`, `PDerivedTuplesetTTU`, `LeafFamily` and `DerivedFamily` from
`zanzibar_utils_v1`, and takes a `CompiledBooleans`:
```python
def global_signs(comp):
    """sign[R] for every derived relation R: the set of signs (+1/-1) with which a
    GROWTH of R propagates to SOME public relation (R itself counts as +1)."""
    sign = {k: {1} for k in comp.plans}
    changed = True
    while changed:
        changed = False
        for qkey, plan in comp.plans.items():
            for spec, node in zip(plan.leaves, plan.leaf_nodes):
                local = 1 if spec.positive else -1
                if isinstance(node, PDerivedComputed):
                    refs = [(qkey[0], node.relation)]
                elif isinstance(node, PDerivedUserset):
                    refs = [(node.subject_type, node.subject_predicate)]
                elif isinstance(node, (PDerivedTTU, PDerivedTuplesetTTU)):
                    refs = [(t, node.target_rel) for t in node.parent_types]
                else:
                    continue
                for r in refs:
                    if r not in sign:
                        continue
                    add = {local * s for s in sign[qkey]}
                    if not add <= sign[r]:
                        sign[r] |= add
                        changed = True
    return sign


def revocation_families(comp):
    sign = global_signs(comp)
    out = set()
    for k, v in comp.namespace.items():
        if isinstance(v, LeafFamily):
            owner = (v.object_type, v.owner_relation)
            local = 1 if v.positive else -1
            if -1 in {local * s for s in sign[owner]}:
                out.add(k)
        elif isinstance(v, DerivedFamily):
            if -1 in sign[k]:
                out.add(k)
    return sign, out
```
