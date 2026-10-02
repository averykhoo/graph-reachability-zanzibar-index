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
| S4 | TK112: scouted 2026-10-03 (sec 6); the cap-policy DECISION is owed before any code | owed |
| S5 | TK111 sync clean refusal | owed |
| S6 | TK113 refusals | owed |
| S7 | correct the CLAUDE.md "removals are exempt" bullet, the `core.py` comment, the TK33 premise, spec-deviations 2026-07-29c | owed |

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
