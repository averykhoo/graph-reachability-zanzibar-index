# TK151 docs pass: library bugs found, with repros (2026-10-20)

FROZEN once the rows below are filed. Found by the TK151 docs workflows (wf_e60a3842-f17 suspected,
wf_b32b8743-b9f reproduced). Each repro is the agent script, copied here verbatim; every one was
RE-RUN FIRST-HAND 2026-10-20b (session interpreter, PYTHONPATH=src) and behaved as reported. Verdict,
cause and fix text below are the agent's (evidence, not a finding): re-read the cited code before acting.
Run one: `PYTHONPATH=src python docs/tk151-repros-2026-10-20/<id>.py` from the repo root.

## B1 -- CONFIRMED (ergonomics)

Confirmed. With paranoia "full", when the check that runs after the commit fails, the caller gets sqlalchemy.exc.InvalidRequestError ("This session is in 'committed' state"). The InvariantViolation is attached only as __context__ (__cause__ is None). The write is stored in both the log and the index: a fresh Store reads it as True. The original Store is unusable afterwards: check, add and refresh all raise the same InvalidRequestError. session.close() brings reads back, but writes then fail with "IndexCursor is not persistent within this Session". A control run, where the check before the commit fails instead, behaves correctly: the caller gets InvariantViolation, nothing is stored, and the Store keeps working. Cause: ParanoiaGuard.after_commit raises from inside SQLAlchemy's after_commit hook. The transaction is already committed, but it stays stuck in the COMMITTED state. Store._write's except arm then calls session.rollback(), which SQLAlchemy refuses in that state, so a new InvalidRequestError replaces the InvariantViolation. The refresh_evaluator() and re-raise after it never run. The graph index and set engine still agree and no data is lost, so this is ergonomics, not equivalence or correctness. A caller may wrongly conclude the write failed; retrying the add is a harmless no-op duplicate. The Store docstring describes only the before-commit, fail-closed case. The userdocs pages already describe the observed behaviour as a known defect.

Code: `src/zanzibar/graphindex/invariants.py::ParanoiaGuard.after_commit (raises from inside the SQLAlchemy after_commit hook; the self.wm update after it is skipped)`; `src/zanzibar/graphindex/invariants.py::install_paranoia (_post_commit_check after_commit listener)`; `src/zanzibar/graphindex/invariants.py::_violations_tagged (re-tags the error as InvariantViolation with phase post-commit)`; `src/zanzibar/store/_store.py::Store._write (second except arm: session.rollback() in the COMMITTED state raises InvalidRequestError, which hides the InvariantViolation)`; `src/zanzibar/store/_store.py::Store.__init__ docstring (Fail-closed paragraph covers only the before_commit case)`; `src/zanzibar/store/_store.py other commit sites (__init__ bootstrap, catch_up, ~l.725 as of 2026-10-20): same pattern likely, UNVERIFIED`

Suggested fix (agent): Do not raise from the SQLAlchemy after_commit listener. In ParanoiaGuard.after_commit, catch the InvariantViolation and store it on the guard (for example guard.pending_post_commit_violation). Store (_write, catch_up, bootstrap) then re-raises it right after self.session.commit() returns, when the session is clean. The message should say that the write IS stored. The Store then stays usable and the caller gets InvariantViolation directly. Add a sabotage test shaped like repro.py: the caller receives InvariantViolation, the write is stored, and a later add/check on the same Store works. Then update the Store docstring and the userdocs "known defect" passages.

Pages that describe the current behaviour (update when fixed): userdocs/how-to/runtime-checks.md (When a check fails section + is_invariant_violation helper), userdocs/how-to/errors.md (What except ZanzibarError does not catch), userdocs/reference/configuration.md (paranoia levels paragraph), userdocs/reference/exceptions.md (InvariantViolation row), userdocs/explanation/assurance.md (~l.123, mentions the post-commit re-check; not the error type)

First-hand output 2026-10-20b (`B1.py`, last lines):

```text
    ...<2 lines>...
    )

session state: in_transaction = True | _transaction._state = SessionTransactionState.COMMITTED
check b RAISED InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.
add c RAISED InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.
refresh RAISED InvalidRequestError: This session is in 'committed' state; no further SQL can be emitted within this transaction.
fresh Store sees b: True | a: True
after session.close(): check b -> True
after session.close() RAISED InvalidRequestError Instance '<IndexCursor at 0x202c1ec6fd0>' is not persistent within this Session
control pre-commit caller type: InvariantViolation | store='s2' [pre-commit] SABOTAGE pre-commit
control: b stored? False | store usable, add c -> 3
```

## B2 -- CONFIRMED (ergonomics)

UnsupportedByGraphIndex (and its subclass DoublyBridgedShapeError) inherit from ZanzibarError only. They are the only 2 of the 24 public ZanzibarError subclasses with no builtin base, so `except ValueError` around parse_openfga_schema / Store / compile_ruleset does not catch them. This is not a regression. git log -G shows the base was plain Exception from 279f08a (2026-07-06) until d94e307 (TK123), which changed it to ZanzibarError. So ZanzibarError's docstring promise to keep "the builtin base it always had" is technically kept. The graph index and set engine do not diverge, because SetEngine.__init__ re-raises DoublyBridgedShapeError and both backends refuse the shape. The userdocs already say correctly that these are not ValueErrors. The only overclaim is in the SchemaError docstring, which says it is raised for "every refused schema shape". DoublyBridgedShapeError is a refused shape (its raise has a REFUSED SHAPE block), but it is neither a SchemaError nor a ValueError.

Code: `src/zanzibar/schema/errors.py::UnsupportedByGraphIndex`; `src/zanzibar/schema/errors.py::DoublyBridgedShapeError`; `src/zanzibar/schema/errors.py::SchemaError (docstring: 'every refused schema shape')`; `src/zanzibar/schema/errors.py::ZanzibarError (docstring: keeps 'the builtin base it always had')`; `src/zanzibar/schema/compiler.py::_reject_doubly_bridged_shapes`; `src/zanzibar/schema/compiler.py::compile_ruleset`; `src/zanzibar/setengine/engine.py::SetEngine.__init__ (re-raises DoublyBridgedShapeError, swallows other UnsupportedByGraphIndex)`

Suggested fix (agent): Option A (consistency, recommended): change the class line in src to `class UnsupportedByGraphIndex(ZanzibarError, ValueError)`. The change is additive: existing `except UnsupportedByGraphIndex` and `except ZanzibarError` handlers still match, and only code that relies on `except ValueError` not catching it would behave differently. In SetEngine.__init__ the specific except clauses already come first. Before changing it, check tests/parity.py, which treats a bare ValueError from compile as "must surface". Then update userdocs/how-to/errors.md L5-8 and L104-107, how-to/rewrite-refused-shape.md L13 and the reference/exceptions.md tree. Option B (no code change): keep the hierarchy and narrow the SchemaError docstring to "every refused schema shape except DoublyBridgedShapeError". Under Option B the userdocs stay as they are, because they are already accurate.

Pages that describe the current behaviour (update when fixed): userdocs/how-to/errors.md, userdocs/how-to/rewrite-refused-shape.md, userdocs/reference/exceptions.md, userdocs/how-to/upgrade-0.1.md, userdocs/how-to/port-openfga.md, userdocs/explanation/two-backends.md, userdocs/reference/api/schema.md

First-hand output 2026-10-20b (`B2.py`, last lines):

```text
  UnsupportedByGraphIndex      ValueError=False builtin=[]
  WatermarkGap                 ValueError=False builtin=['RuntimeError']
  WriteLockUnsafe              ValueError=False builtin=['RuntimeError']
== MRO
  UnsupportedByGraphIndex: ['UnsupportedByGraphIndex', 'ZanzibarError', 'Exception', 'BaseException', 'object']
  DoublyBridgedShapeError: ['DoublyBridgedShapeError', 'UnsupportedByGraphIndex', 'ZanzibarError', 'Exception', 'BaseException', 'object']
== parse_openfga_schema(F1, object_wildcard_shapes=OWC) under `except ValueError`
  ESCAPED except ValueError: DoublyBridgedShapeError | is ZanzibarError: True
== Store(..., object_wildcard_shapes=OWC)
  ESCAPED except ValueError: DoublyBridgedShapeError
== compile_ruleset(enable_boolean=False) on a `but not` schema
  ESCAPED except ValueError: UnsupportedByGraphIndex | relation doc#viewer uses boolean operator 'but not', which enable_boolean=False refuses; compile wit
```

## B3 -- CONFIRMED (ergonomics)

CONFIRMED by running it. If catch_up() fails on an idle store (lag 0), it records a stall with stalled_after == applied_log_id. Later catch_up() calls succeed and return 0, but the stall stays. Only a write that then gets applied (by any instance), or rebuild_index, clears it. This contradicts the IndexStalled docstring, which says "any successful catch_up batch ends it" and "clears on the next good batch". It does happen in practice. advance_index takes the store write lock (a no-op UPDATE on SQLite, FOR UPDATE on PostgreSQL) before it finds out there are no rows to apply. So any transient failure during an idle poll records a lag-0 stall: a SQLite lock held past the busy timeout (shown for real in Part B, about 44 s), a dropped connection, or a PostgreSQL lock or statement timeout. Answers stay correct: untokened check falls back to the set engine. But untokened lookup and lookup_reverse raise IndexStalled with no end on a quiet store, and the error message says "STALLED at log id 1 (lag 0)" and tells you to run a successful catch_up(), which does not help. refresh() does not clear it either.

Code: `src/zanzibar/store/_store.py::Store._record_stall (sets stalled_after = applied_log_id on ANY exception, even one raised before rows are read)`; `src/zanzibar/store/_store.py::Store._catch_up (zero-row result: rollback and return; nothing clears the marker)`; `src/zanzibar/store/_store.py::Store.index_stalled (live while stalled_after == applied_log_id)`; `src/zanzibar/store/apply.py::advance_index (takes widx.idx._lock_store() and refreshes the cursor before 'if not rows: return 0'; clears stalled_after/stall_error only on the path that advances the cursor)`; `src/zanzibar/graphindex/core.py::take_row_write_lock (a no-op UPDATE on SQLite takes the db write lock even on an idle poll)`; `src/zanzibar/store/build.py::rebuild_index (the other thing that clears the marker)`; `src/zanzibar/store/_store.py::IndexStalled (docstring: 'any successful catch_up batch ends it' is wrong for an idle store)`; `src/zanzibar/store/_store.py::Store._require_index_freshness (IndexStalled message advises 'a successful catch_up()', which does not clear a lag-0 stall)`

Suggested fix (agent): Change the code: in Store._catch_up (or the zero-row path of advance_index), when a batch succeeds with no rows and the cursor still shows stalled_after == applied_log_id, clear stalled_after and stall_error and commit. The zero-row path already holds the store lock and has just shown the index is at the head, so the staleness bound really is back. Do not try to decide in _record_stall whether a failure was a poison row or a transient error; that reopens the fail-open its docstring warns about. Then reword the IndexStalled docstring and the message, which should not print 'lag 0' next to 'run a successful catch_up()'. If the code stays as it is: correct the IndexStalled docstring and message to say that a catch_up() that applies nothing does not clear the stall, and name the workarounds (any write followed by catch_up(), or rebuild_index).

Pages that describe the current behaviour (update when fixed): userdocs/explanation/consistency.md (L258-261: already describes the limitation correctly), userdocs/how-to/stall-recovery.md (L105-112: already describes it and gives the any-write-then-catch_up workaround), userdocs/how-to/async-tokens.md (L85-88: already describes it), userdocs/reference/exceptions.md (IndexStalled entry, about L333-338: 'the next successful catch_up() that applies at least one row' is accurate but does not warn about the idle case; hand-written, not autodoc), userdocs/reference/api/store.md (L264: only links IndexStalled, not autodoc'd, so the wrong docstring reaches users only through help()), userdocs/explanation/limits.md, userdocs/explanation/two-backends.md, userdocs/how-to/errors.md, userdocs/how-to/bulk-load-adopt.md (general stall mentions, not affected)

First-hand output 2026-10-20b (`B3.py`, last lines):

```text
  [caught up, idle] lag=0 applied=1 stalled_after=None index_stalled=False
  catch_up() raised OperationalError after 44.3s: (sqlite3.OperationalError) database is locked
  [after lock-timeout on idle poll] lag=0 applied=1 stalled_after=1 index_stalled=True
  stall_error = applied through 1: OperationalError: (sqlite3.OperationalError) database is locked
[SQL: UPDATE zanzibar_store SET description=zanzibar_store.description WHERE 
  catch_up() (healthy, nothing pending) -> 0
  [after zero-row catch_up] lag=0 applied=1 stalled_after=1 index_stalled=True
  lookup -> IndexStalled: lookup() cannot be served: the index for store 'my-app' is STALLED at log id 1 (lag 0): the last catch_up() failed to advance past it -- applied through 1: Oper ...
  check(alice viewer d1) -> True
  [after refresh()] lag=0 applied=1 stalled_after=1 index_stalled=True
  write carol; catch_up() -> 1
  [after a write was applied] lag=0 applied=2 stalled_after=None index_stalled=False
```

## B4 -- CONFIRMED (ergonomics)

Confirmed. A freshness token is just a TupleLog id, and ids count up across all stores without saying which store wrote them. So any token from another store that is at or below this store's cursor passes the freshness check. It happens silently on every surface that takes a token: check, lookup, lookup_reverse and expand, not just check as the claim said. The ownership check (token_diagnosis) only runs when a read is already being refused. The answers themselves are correct for the store that was asked, and the graph index and set engine agree. What goes wrong is that a caller who passes the wrong store's token gets no error. In async mode that caller can also believe they read their own writes when they did not (case 4).

Code: `src/zanzibar/store/_store.py::Store._fresh_enough (return self.cursor.applied_log_id >= at_least; no store-ownership check)`; `src/zanzibar/store/_store.py::Store.check`; `src/zanzibar/store/_store.py::Store._require_index_freshness (lookup/lookup_reverse)`; `src/zanzibar/store/_store.py::Store._require_evaluator_at (expand and check's fallback; only compares the watermark)`; `src/zanzibar/store/_store.py::Store.expand`; `src/zanzibar/store/source.py::token_diagnosis (the owner != store_id test exists, but runs only when a read is refused)`; `src/zanzibar/store/source.py::validate_token (checks type and sign only)`

Suggested fix (agent): When a token is passed (not None), look up TupleLog.store_id for id == at_least with one primary-key query, before the freshness checks, on check, lookup, lookup_reverse and expand (for example in a shared helper next to validate_token). If the row names a different store, raise a dedicated error or a ValueError that says the token belongs to that store. If the row is not visible yet (no owner found), keep today's behaviour. The cost is one PK lookup per read that carries a token. The other option is to put the store id inside the token, but that breaks the API. After the fix, update how-to/async-tokens.md, whose 'not rejected reliably' paragraph would then be wrong.

Pages that describe the current behaviour (update when fixed): userdocs/how-to/async-tokens.md (~L193: already says a foreign token is accepted and guarantees nothing when it is not newer than the store's cursor; matches the code today, but would need changing after a fix), userdocs/explanation/consistency.md (~L175: says the StaleRead message names a different store's token; true only when the read is refused, and it does not mention the silent accept), userdocs/how-to/errors.md (~L194: the StaleRead bullet has the same only-when-refused framing)

First-hand output 2026-10-20b (`B4.py`, last lines):

```text
b.expand(viewer, doc:d1, at_least=t_a) keys: returned [('doc', 'd1', 'viewer'), ('user', 'bob', '...')]
--- CASE 2 (control): foreign token ABOVE b's cursor
t_a2 = 4  b.cursor.applied_log_id = 3
b.check(carol viewer d9, at_least=t_a2): raised StaleRead: token 4 is not visible in this session snapshot (evaluator at 3); call refresh() to start a fresh read transaction and retry. Token 4 was ret
b.lookup(carol, at_least=t_a2): raised LookupNotFresh: lookup(at_least=4) cannot be served: the index for store 'store-b' has applied through 3 (lag 0). Unlike check(), the lookup surfaces have no set
--- CASE 3: same-store control, b's own token
b.check(dave viewer d2, at_least=t_b2): returned True
--- CASE 4: async store-c with a backlog; foreign token below its cursor
t_c1 = 5  t_c2 = 6  c.cursor = 5  lag = 1
c.check(gina viewer d3)  [untokened]: returned False
c.check(gina viewer d3, at_least=t_a)  [foreign, <= cursor]: returned False
c.check(gina viewer d3, at_least=t_c2)  [own token]: returned True
```

## B5 -- CONFIRMED (ergonomics)

Confirmed. When a store is passed a freshness token issued by another store, and that token is newer than the store's own writes, StaleRead and LookupNotFresh both start with retry advice that cannot help. StaleRead (from check and expand) says "token N is not visible in this session snapshot ...; call refresh() ... and retry". LookupNotFresh says "Run catch_up() and retry; for a single decision use check(..., at_least=N), which does fall back", and that check then raises StaleRead. The real cause is only the last sentence of the message ("Token N was returned by a write to store 'store-b', not 'store-a'"). The opening clause "not visible in this session snapshot" is also false: the row is visible but belongs to another store. Doing what the message says (refresh() then catch_up()) gives exactly the same errors. The reads are refused and never answered wrongly, so this is ergonomics, not correctness.

Code: `src/zanzibar/store/_store.py::Store._require_evaluator_at (fixed 'call refresh() ... and retry.' prefix + token_diagnosis suffix; used by Store.check fallback and Store.expand)`; `src/zanzibar/store/source.py::TupleSource.check (same shape: 'rollback ..., refresh the evaluator, and retry.' + token_diagnosis)`; `src/zanzibar/store/_store.py::Store._require_index_freshness (LookupNotFresh: 'Run catch_up() and retry; ... use check(...), which does fall back' + token_diagnosis)`; `src/zanzibar/store/source.py::token_diagnosis (detects the foreign-owner case correctly, but only returns a suffix, so callers never replace the retry advice)`

Suggested fix (agent): Check for foreign ownership before writing the generic message. For example, token_diagnosis could return a kind as well as text, or a helper could return the owning store. When another store owns the token, raise a message that starts with the cause: "token N was returned by a write to store 'X', not 'Y'; tokens are per-store, so pass this store a token from its own writes". That message should leave out the refresh/catch_up/retry advice and the check() fallback suggestion. Apply this in all three raise sites. Optionally add a subclass such as ForeignToken(StaleRead), so existing `except StaleRead` handlers still catch it. Pin the fix with a test asserting the foreign-token message contains no 'retry' and does not say 'not visible in this session snapshot'. Related: B4 (a foreign token at or below the cursor is accepted silently) is a separate bug that a message change cannot fix.

Pages that describe the current behaviour (update when fixed): userdocs/how-to/errors.md (StaleRead bullet ~L192-197 works around the misleading message: 'If the message says the token was returned by a write to another store ... retrying further will not help'), userdocs/how-to/async-tokens.md (~L193-206 foreign-token example; asserts the store name is in the message, which stays true), userdocs/explanation/consistency.md (~L103-108 'Refreshing and retrying does not help in the second case'; describes the behaviour correctly), userdocs/how-to/query-access.md, userdocs/how-to/postgresql.md, userdocs/explanation/two-backends.md, userdocs/reference/exceptions.md, userdocs/reference/api/store.md (mention StaleRead/LookupNotFresh in general only)

First-hand output 2026-10-20b (`B5.py`, last lines):

```text
zanzibar from: C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index\src\zanzibar\__init__.py
token from a: 1  token from b: 3  a.watermark(): 1
--- round 1 ---
a.check(at_least=tb) -> StaleRead: token 3 is not visible in this session snapshot (evaluator at 1); call refresh() to start a fresh read transaction and retry. Token 3 was returned by a write to stor
a.expand(at_least=tb) -> StaleRead: token 3 is not visible in this session snapshot (evaluator at 1); call refresh() to start a fresh read transaction and retry. Token 3 was returned by a write to sto
a.lookup(at_least=tb) -> LookupNotFresh: lookup(at_least=3) cannot be served: the index for store 'store-a' has applied through 1 (lag 0). Unlike check(), the lookup surfaces have no set-engine fallba
following the advice: a.refresh(); a.catch_up()
--- round 2 ---
a.check(at_least=tb) -> StaleRead: token 3 is not visible in this session snapshot (evaluator at 1); call refresh() to start a fresh read transaction and retry. Token 3 was returned by a write to stor
a.expand(at_least=tb) -> StaleRead: token 3 is not visible in this session snapshot (evaluator at 1); call refresh() to start a fresh read transaction and retry. Token 3 was returned by a write to sto
a.lookup(at_least=tb) -> LookupNotFresh: lookup(at_least=3) cannot be served: the index for store 'store-a' has applied through 1 (lag 0). Unlike check(), the lookup surfaces have no set-engine fallba
```

## B6 -- CONFIRMED (ergonomics)

Confirmed, and the problem is wider than the claim. The library is behaving as designed. A sync=False store logs a tuple that overflows the path count, and catch_up then stalls. After that, every write through a sync=True instance on the same store id is refused with PathCountExceeded and rolled back. That covers unrelated add_tuple calls, remove_tuple calls, and even the remove_tuple of the bad tuple itself. Other store ids are not affected. Answers stay correct: the rolled-back write is absent from both backends, and check agrees with the set engine. The error message names the closure row of the backlog row (alice -> a32), not the tuple the caller wrote. The row is only identified in exc.failing_log_row and the exception note. A failed sync write records no stall. The fix is to remove the tuple through a sync=False instance and then run rebuild_index; after that, sync writes work again. stall-recovery.md already documents that sync add_tuple fails. Several other pages say "remove_tuple works while stalled", which is only true for a sync=False instance.

Code: `src/zanzibar/store/_store.py::Store._write (sync branch: advance_index over the whole pending backlog inside the caller's write txn; rollback + refresh_evaluator + re-raise; no stall recorded)`; `src/zanzibar/store/apply.py::advance_index (rows_hint used only when contiguous with the cursor, else log_rows from the cursor, so the poison row comes first)`; `src/zanzibar/store/apply.py::_apply_row (IndexResourceLimit re-raised unchanged)`; `src/zanzibar/store/apply.py::_attach_failing_row (row identified only via failing_log_row / note)`; `src/zanzibar/graphindex/core.py::MAX_PATH_COUNT and the path-count bound raising PathCountExceeded (never suspended; fanout_cap_suspended covers only the fan-out cap)`; `src/zanzibar/store/_store.py::Store._catch_up / _record_stall (only place a stall is recorded)`; `src/zanzibar/store/build.py::rebuild_index (recovery)`

Suggested fix (agent): Library: no change is required for correctness. To improve ergonomics, when a sync write fails on a backlog row whose log id is not the caller's, raise it with (or wrap it in) a message that says "the index backlog contains an unappliable row <id>: <row>; write through a sync=False instance and see rebuild_index". Optionally record the stall on this path too. Docs: (1) In explanation/consistency.md (~l.265) and reference/api/store.md rebuild_index (~l.170), change "Store.remove_tuple works while stalled" to "works through a sync=False instance; a sync=True instance refuses it with PathCountExceeded". (2) In reference/exceptions.md (table l.85 and py:exception l.296) and how-to/errors.md (~l.227), add that once an async-logged row is unappliable, every write (adds and removes) through a sync=True instance on that store id is refused, and the message names the backlog row's closure, not the caller's tuple. (3) In how-to/stall-recovery.md "Writes through a sync instance fail too", say that removals fail too, including removing the bad tuple, and point to exc.failing_log_row / stall_error.

Pages that describe the current behaviour (update when fixed): userdocs/how-to/stall-recovery.md, userdocs/explanation/consistency.md, userdocs/reference/api/store.md, userdocs/reference/exceptions.md, userdocs/how-to/errors.md, userdocs/how-to/async-tokens.md

First-hand output 2026-10-20b (`B6.py`, last lines):

```text
sync store, later unrelated add: OK -> 127
async catch_up: PathCountExceeded: path count bound exceeded: this edge would give closure row user:alice -> group:a32#member 2147483648 distinct derivation paths, over the storage limit of 21474
index_stalled: True lag: 127
sync add unrelated tuple: PathCountExceeded: path count bound exceeded: this edge would give closure row user:alice -> group:a32#member 2147483648 distinct derivation paths, over the storage limit of 
sync remove existing tuple: PathCountExceeded: path count bound exceeded: this edge would give closure row user:alice -> group:a32#member 2147483648 distinct derivation paths, over the storage limit o
sync remove of the poison tuple itself: PathCountExceeded: path count bound exceeded: this edge would give closure row user:alice -> group:a32#member 2147483648 distinct derivation paths, over the sto
bob in zz (sync inst check): False
bob in zz (set engine): n/a
sync add on other store id: OK -> 255
rebuild_index: OK -> 'BuildReport'
sync add after rebuild: OK -> 257
bob in zz after rebuild: True
```

## B7 -- PARTLY (docs)

The three facts in the claim are true, but they cause no wrong answers. is_valid_identifier('...') returns True because '.' is in IDENTIFIER_CHARSET. A TYPE named '...' parses in both the product parser and the oracle; a RELATION named '...' is refused by the '.'-lock. `[user#...]` gives the same AST as `[user]`, and this is on purpose: _parse_leaf maps a missing predicate to '...', and _validate_ast_references exempts '...'. The oracle, the set engine under both SetOps and the graph index agree on a schema that uses `type ...` with a userset, a wildcard, a TTU and `but not`. ParityEngine asserts unanimity and full-grid oracle parity on every op. The only real defect is the is_valid_identifier docstring, which says '...' is NOT a valid identifier. A minor inconsistency also remains: the DSL accepts `[user#...]`, but the tuple-string form 'user:carol#...' is refused with MalformedTupleString.

Code: `src/zanzibar/schema/errors.py::IDENTIFIER_CHARSET`; `src/zanzibar/schema/errors.py::_IDENTIFIER_RE`; `src/zanzibar/schema/errors.py::is_valid_identifier (docstring wrong about '...')`; `src/zanzibar/schema/parser.py::_validate_declared_name`; `src/zanzibar/schema/parser.py::Parser._parse_leaf`; `src/zanzibar/schema/parser.py::_validate_ast_references`; `tests/oracle.py::_validate_declared_name`

Suggested fix (agent): Fix the is_valid_identifier docstring. '*' is outside the charset, but '...' is inside it (it is just three '.' characters). Its reservation as the bare predicate is enforced by position, through _require(allow_ellipsis=True). Optional product decision, which equivalence does not need: refuse a declared type name made only of dots, and/or refuse an explicit '#...' in a restriction so the DSL matches the tuple-string rule. Either change must go in both parsers, with a REFUSED SHAPE comment block and the P23 parity test.

Pages that describe the current behaviour (update when fixed): userdocs/reference/tuple-strings.md, userdocs/reference/api/schema.md, userdocs/reference/schema-language.md, userdocs/how-to/rewrite-refused-shape.md, userdocs/how-to/port-openfga.md, userdocs/how-to/errors.md

First-hand output 2026-10-20b (`B7.py`, last lines):

```text
2 equal          : True
3 `type ...` parses: {('doc', 'viewer'): Direct(restrictions=(Restriction(type='...', predicate='...', wildcard=False),))}
4 `define ...` refused: SchemaError relation '...': '.' is reserved for compiled leaf predicates and cannot appear in a declared relation name
5 oracle accepts [user#...]
5 oracle accepts type ...
6 check ...:x viewer doc:d1 = True
6 set engine check          = n/a
6 lookup_reverse doc:d1 viewer = LookupResult(node_ids={1, 2}, markers=set(), excluded_node_ids=set(), implicit_keys=set(), implicit_excluded_keys=set())
7 [user#...] check user:alice = True
8 [user, user#...] AST: Direct(restrictions=(Restriction(type='user', predicate='...', wildcard=False), Restriction(type='user', predicate='...', wildcard=False)))
8 tuplestr names: ['MalformedTupleString', 'ZanzibarError', '_LOOKUP_LONG', '_LOOKUP_SHORT', '_OBJECT_FORM', '_REVERSE_LONG', '_REVERSE_SHORT', '_TUPLE_LONG', '_TUPLE_SHORT', '_USER_FORM', '_bind', '_
8 add 'user:carol#...' refused: MalformedTupleString user 'user:carol#...': write the bare subject as 'user:carol', without '#...' (the form is 'type:name', 'type:name#relation' or 'type:*')
```

## B8 -- PARTLY (ergonomics)

Half 1 is CONFIRMED (first-hand run). parse_user("user:a#b:c") returns ('b:c','user','a') without raising, and so does "user:a#b c". tuplestr.py::parse_user only rejects a predicate that is empty, contains a second '#', or is '...'. _split_type_name rejects a second ':' in the name, but nothing checks the predicate's charset. As a result, check("group:g#b:c",...) returns False and lookup("group:g#b:c") returns an empty result, which matches what an undeclared predicate like #nope gives. The write add_tuple("group:g#b:c",...) is refused, but with AdmissionRejected (from the charset check in errors.py::validate_write_identifiers), not MalformedTupleString. The answers are correct and both backends agree: source.check and widx.check both return False. Half 2 is REFUTED (first-hand run). Store.check("group:g#...",...) and Store.lookup("group:g#...") both raise the same MalformedTupleString ("write the bare subject as 'group:g', without '#...'"), because both go through parse_user (via tuple_args and lookup_args respectively). The long form with a bare group subject is also symmetric: check("...","group","g",...) returns False, and lookup("...","group","g") and lookup("group:g") both return an empty result. I could not save the report file: the harness refused the Write call with "Subagents should return findings as text". The repro script and its output file were saved.

Code: `src/zanzibar/schema/tuplestr.py::parse_user (predicate is checked only for empty, a second '#' and '...'; no charset or ':' check)`; `src/zanzibar/schema/tuplestr.py::_split_type_name (rejects ':' in the name, not in the predicate)`; `src/zanzibar/schema/tuplestr.py module docstring (says ':' and '#' are outside the charset, so the split is never ambiguous; enforced only for type/name)`; `src/zanzibar/schema/errors.py::validate_write_identifiers (catches 'b:c' on the write as AdmissionRejected)`; `src/zanzibar/store/_store.py::Store.check (via tuplestr.py::tuple_args -> parse_user)`; `src/zanzibar/store/_store.py::Store.lookup (via tuplestr.py::lookup_args -> parse_user; same refusal of '#...' as check)`

Suggested fix (agent): In tuplestr.py::parse_user, raise MalformedTupleString when the predicate contains ':'. Better still, apply the identifier charset to the predicate (and to type and name) there. Then "user:a#b:c" is malformed on reads and writes alike, as the userdocs and the module docstring already say. No change is needed for "#...": check and lookup already refuse it the same way. Add a userdocs or test line pinning that check("group:g#b:c",...) raises MalformedTupleString once this is fixed.

Pages that describe the current behaviour (update when fixed): userdocs/explanation/semantics-vs-openfga.md (section 'Writes are strict, reads are lenient': says a string not of the form type:name#relation raises MalformedTupleString on reads and writes alike; but 'user:a#b:c' reads as False and its write raises AdmissionRejected), userdocs/how-to/errors.md (MalformedTupleString / AdmissionRejected bullets and 'Reads are lenient'), userdocs/reference/exceptions.md (MalformedTupleString entry and table row), userdocs/reference/api/store.md (line 273, mentions MalformedTupleString), userdocs/reference/api/schema.md (line 246, mentions MalformedTupleString)

First-hand output 2026-10-20b (`B8.py`, last lines):

```text
lookup("group:g#b:c"): OK -> LookupResult(node_ids=set(), markers=set(), excluded_node_ids=set(), implicit_keys=set(), implicit_excluded_keys=set())
add_tuple("group:g#b:c","viewer","doc:d1"): AdmissionRejected: invalid subject_predicate 'b:c': must match [A-Za-z0-9_./@+=-] (1-256 chars) or '...'
--- undeclared predicate ---
check("group:g#nope", "viewer", "doc:d1"): OK -> False
lookup("group:g#nope"): OK -> LookupResult(node_ids=set(), markers=set(), excluded_node_ids=set(), implicit_keys=set(), implicit_excluded_keys=set())
--- control: valid userset ---
check("group:g#member","viewer","doc:d1"): OK -> True
lookup("group:g#member"): OK -> LookupResult(node_ids={2, 3}, markers=set(), excluded_node_ids=set(), implicit_keys=set(), implicit_excluded_keys=set())
--- set engine directly ---
source.check("...","group","g","viewer","doc","d1"): OK -> False
source.check("b:c","group","g","viewer","doc","d1"): OK -> False
widx.check(...,"group","g","viewer","doc","d1"): OK -> False
```

## B10 -- CONFIRMED (ergonomics)

Both halves of the claim reproduce. Severity is ergonomics: answers are correct, and every re-exported exception is the same object as the top-level one.

1. Exception re-exports: zanzibar.__init__._LAZY exports all 29 exceptions and warnings. Each subpackage __all__ picks its own subset with no shared rule:
   - zanzibar.graphindex exports AdmissionRejected, WriteLockUnsafe and InvariantViolation. It omits ClosureFanoutExceeded and PathCountExceeded, although graphindex/core.py raises both.
   - zanzibar.setengine exports only UnloggedWriteRefused and StaleLookupIds. It omits AdmissionRejected and SchemaError, which SetEngine raises.
   - zanzibar.store exports a third subset. It includes StaleLookupIds and WriteLockUnsafe but leaves out InvariantViolation, UnloggedWriteRefused and ZanzibarError.

2. Non-public types in public signatures: Entity, RelationalTriple and SchemaInfo are defined in zanzibar/schema/rules.py. They can be imported from zanzibar.schema but are in no __all__. They appear in these public signatures:
   - compile_ruleset(schema_info: SchemaInfo)
   - RuleSet.schema_info: SchemaInfo | None
   - RuleSet.apply(relational_triple: RelationalTriple), whose fields are Entity
   - WildcardIndex.__init__(idx, schema_info: 'SchemaInfo')
   - DeltaProcessor.__init__(compiled: 'CompiledBooleans'), where CompiledBooleans is also private.

Side finding: typing.get_type_hints(zanzibar.schema.RuleSet) raises NameError on 'CompiledBooleans'. The string annotation in schema/rules.py cannot be resolved there.

Code: `src/zanzibar/__init__.py::_LAZY`; `src/zanzibar/graphindex/__init__.py::__all__`; `src/zanzibar/setengine/__init__.py::__all__`; `src/zanzibar/store/__init__.py::__all__`; `src/zanzibar/schema/__init__.py::__all__`; `src/zanzibar/schema/rules.py::Entity`; `src/zanzibar/schema/rules.py::RelationalTriple`; `src/zanzibar/schema/rules.py::SchemaInfo`; `src/zanzibar/schema/rules.py::RuleSet (schema_info, compiled: 'CompiledBooleans | None', apply)`; `src/zanzibar/schema/compiler.py::compile_ruleset`; `src/zanzibar/graphindex/wildcard.py::WildcardIndex.__init__`; `src/zanzibar/graphindex/processor.py::DeltaProcessor.__init__`; `src/zanzibar/graphindex/core.py (raise ClosureFanoutExceeded ~L916, raise PathCountExceeded ~L722, as of 2026-10-20)`

Suggested fix (agent): 1. Pick one export rule and pin it with a test. Either each subpackage __all__ re-exports every exception that subpackage raises (graphindex adds ClosureFanoutExceeded, PathCountExceeded and IndexResourceLimit; setengine adds AdmissionRejected, SchemaError and ZanzibarError), or the subpackages stop re-exporting exceptions and the docs say "import exceptions from zanzibar".
2. Either make Entity, RelationalTriple and SchemaInfo public (add them to zanzibar.schema.__all__ with docstrings), or take them out of public signatures. Options for the latter: WildcardIndex(idx, ruleset), and a tuple-taking RuleSet.apply variant. Then remove the matching userdocs/conf.py nitpick_ignore entries.
3. Add a TYPE_CHECKING import of CompiledBooleans in schema/rules.py so that get_type_hints(RuleSet) resolves.

Pages that describe the current behaviour (update when fixed): userdocs/conf.py, userdocs/reference/api/schema.md, userdocs/reference/api/graphindex.md, userdocs/reference/exceptions.md, userdocs/how-to/backends-direct.md

First-hand output 2026-10-20b (`B10.py`, last lines):

```text
-- non-public types in public signatures --
Entity: in zanzibar.schema.__all__=False, importable from zanzibar.schema=True, defined in zanzibar.schema.rules
RelationalTriple: in zanzibar.schema.__all__=False, importable from zanzibar.schema=True, defined in zanzibar.schema.rules
SchemaInfo: in zanzibar.schema.__all__=False, importable from zanzibar.schema=True, defined in zanzibar.schema.rules
compile_ruleset (in schema.__all__): (ast: dict[tuple[str, str], zanzibar.schema.syntax.Union | zanzibar.schema.syntax.Intersection | zanzibar.schema.syntax.Exclusion | zanzibar.schema.syntax.Direct |
RuleSet.schema_info field type: zanzibar.schema.rules.SchemaInfo | None
typing.get_type_hints(RuleSet) -> NameError name 'CompiledBooleans' is not defined
RuleSet.apply: (self, relational_triple: zanzibar.schema.rules.RelationalTriple)
WildcardIndex.__init__ (in graphindex.__all__): (self, idx: 'ReachabilityIndex', schema_info: 'SchemaInfo')
DeltaProcessor.__init__: (self, widx: 'WildcardIndex', compiled: 'CompiledBooleans')
RuleSet.apply(RelationalTriple(...)) -> <generator object RuleSet.apply at 0x0000017311B6C5C0>
<generator object RuleSet.apply at 0x0000017311B6C5C0>
```

