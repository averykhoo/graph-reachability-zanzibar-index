# TK166 -- refuse a freshness token issued by another store (2026-10-23)

> **ACTIVE-PLAN** (`docs/README.md` sec 3): the working record for `TK166`. Corrections are
> appended dated at the top, never edited into the body; FROZEN when `TK166` closes.

Row: `python scripts/task.py show TK166`. Source: `docs/tk151-repros-2026-10-20/README.md`
sections B4 and B5 (repros `B4.py`, `B5.py`). Agent `tk166-impl` (workflow minion, run
`wf-0p1`), 2026-10-23. Provenance labels: **READ** = read first-hand by this agent in the
live tree; **RAN** = observed output of a command this agent ran; **REASONED** = inference.

## Corrections

### Review 2026-10-23 (agent `tk166-review`, workflow `wf-0p1`)

Adversarial review of the uncommitted change. Verdicts, each labelled:

- **Every tokened read refuses** -- REFUTE FAILED (READ). The only `at_least` entry points
  in `src/zanzibar` are `Store.check`, `Store._require_index_freshness` (`lookup`,
  `lookup_reverse`), `Store.expand` and `TupleSource.check`; all call
  `refuse_foreign_token` before any freshness test.
- **A same-store token wrongly refused** -- REFUTE FAILED (READ). The compare is exact
  string equality on `TupleLog.store_id`, so ids that prefix one another are distinct.
  `Store.__init__` always calls `ensure_cursor(session, store_id, store_id)`, so the index
  store id and the source store id cannot differ for a `Store`. No API drops a store;
  `TupleLog` rows are permanent. A token that names no row (0, or above the head) falls
  through unchanged (pinned by `test_own_tokens_still_serve`,
  `test_a_token_naming_no_row_keeps_its_old_refusal`).
- **Performance** -- no regression on untokened reads: `refuse_foreign_token` returns
  before querying when `at_least is None` (READ). A tokened read pays one primary-key
  lookup, as section 3 states.
- **DEFECT, FIXED: `token_diagnosis`'s foreign branch was shadowed, and the TK123 S11
  sabotage could no longer go red** (RAN). Probe `.scratch/wf-0p1/tk166-review/probe_s11.py`
  replaced `token_diagnosis` with `lambda *a, **k: ''` and ran
  `tests/test_tk123_safety_messages.py -k foreign_token_names`: `rc=0`, `1 passed, 36
  deselected`. The string branch was also still live in one case (REASONED): under
  PostgreSQL READ COMMITTED every statement takes a fresh snapshot, so a foreign row
  committed between `refuse_foreign_token` and the refusal would still give the old
  retry-first `StaleRead` / `LookupNotFresh` with the cause at the end (B5).
  Fix: `src/zanzibar/store/source.py::token_diagnosis` now calls `refuse_foreign_token`
  in place of its foreign-store string, so that case raises `ForeignToken` too. New pin:
  `tests/test_tk166_foreign_token.py::test_the_refusal_path_diagnosis_also_raises_foreign_token`.
  The S11 line in `tests/test_tk123_safety_messages.py`'s docstring is marked
  SUPERSEDED. Sabotage of the fix (`.scratch/wf-0p1/tk166-review/probe_sab_diag.py`:
  the module-global `refuse_foreign_token` made a no-op for `token_diagnosis` only) gave
  `rc=1`, `1 failed, 37 deselected`, `Failed: DID NOT RAISE ForeignToken`.
- **Messages** -- REFUTE FAILED (READ). `ForeignToken`'s text has no retry, refresh or
  `catch_up` advice. The tests assert this on all five surfaces.
- **Public surface** -- consistent (READ). Exported in `zanzibar.store.__all__`, in
  `zanzibar._LAZY`, and in the `TYPE_CHECKING` import, the same way as `StaleRead`.
  `test_tk123_top_level` classifies it.
- **Residual, not fixed:** `ForeignToken` sets its attributes after construction, so a
  pickled copy loses `token`, `issued_by` and `store_id`. Other exceptions in the package
  behave the same way. The PostgreSQL race above is REASONED only, because no DSN leg
  was run.
- **Counts** (RAN 2026-10-23, `--collect-only`): `tests/test_tk166_foreign_token.py` now
  has **38** tests (the 37 in sections 2 and 4 plus the new pin), so the counts
  regeneration needs +38. Targeted runs, all `rc=0`: tk166 + tk123 safety/top-level +
  zt_p1_8 + tk155 + tk111 gave `134 passed`; connectedstore* + zt_p1_hardening + tk121 +
  userdocs_examples gave `117 passed`.

## 1. The bug (READ, confirms B4 + B5)

A freshness token is a `TupleLog` id, and ids are numbered across every store in the
database. Before TK166 the freshness tests only compared ids
(`src/zanzibar/store/_store.py::Store._fresh_enough`,
`src/zanzibar/store/_store.py::Store._require_evaluator_at`,
`src/zanzibar/store/source.py::TupleSource.check`), and the ownership test existed only as
a message suffix on the refusal path (`src/zanzibar/store/source.py::token_diagnosis`). So:

- B4: a foreign token at or below this store's cursor was accepted silently by `check`,
  `lookup`, `lookup_reverse`, `expand` (and `TupleSource.check`).
- B5: a foreign token above the cursor was refused with refresh/catch_up-and-retry advice
  that cannot help; the cause was only the last sentence.

## 2. What changed (READ; line numbers as of 2026-10-23, they rot)

| file::symbol | change |
|---|---|
| `src/zanzibar/store/source.py::ForeignToken` | NEW. `class ForeignToken(StaleRead)`; attributes `token`, `issued_by`, `store_id` set on the instance. `StaleRead`'s docstring names it as the non-retryable exception. |
| `src/zanzibar/store/source.py::refuse_foreign_token` | NEW. `(session, store_id, at_least)`: returns on `None`; one PK query `select(TupleLog.store_id).where(TupleLog.id == at_least)`; returns when no row or own row; else raises `ForeignToken`. |
| `src/zanzibar/store/source.py::TupleSource.check` | calls it after `validate_token`, before the watermark test. |
| `src/zanzibar/store/_store.py::Store.check` | calls it after `validate_token`, before `_fresh_enough` (the fast path). Docstring names `ForeignToken`. |
| `src/zanzibar/store/_store.py::Store._require_index_freshness` | calls it after `validate_token` (covers `Store.lookup` and `Store.lookup_reverse`). |
| `src/zanzibar/store/_store.py::Store.expand` | calls it after `validate_token`. |
| `src/zanzibar/store/__init__.py` | imports `ForeignToken`; added to `__all__` after `StaleRead`. |
| `src/zanzibar/__init__.py::_LAZY` | `'ForeignToken': 'zanzibar.store.source'` (and the `TYPE_CHECKING` import), same as `StaleRead`. |
| `tests/test_tk123_top_level.py::_EXPECTED_ALL`, `::_BUILTIN_BASE` | `ForeignToken` added (`RuntimeError` via `StaleRead`). These tables classify every exception and pin `zanzibar.store.__all__`; a NEW class must be listed there. No assertion was weakened. |
| `tests/test_tk166_foreign_token.py` | NEW, 37 tests (`--collect-only`, RAN 2026-10-23). |
| `CHANGELOG.md` `[Unreleased]` | break summary bullet + a "Behaviour change" entry under Changed. |

The message (READ, `refuse_foreign_token`): `Token {N} was returned by a write to store
'{owner}', not '{this}': tokens are per-store, so pass this store a token returned by one
of its own writes.` It leads with the cause and contains none of `retry`, `refresh`,
`catch_up`, `check(`, `not visible` (pinned by
`tests/test_tk166_foreign_token.py::test_the_message_leads_with_the_cause_and_gives_no_retry_advice`).
The wording keeps the prefix `Token N was returned by a write to store 'b', not 'a'`, so the
pre-existing pin `tests/test_tk123_safety_messages.py::test_a_foreign_token_names_the_store_that_issued_it`
stays green UNCHANGED (it now passes via `ForeignToken` instead of the `token_diagnosis`
suffix; its S11 sabotage note in that module docstring is as-of 2026-10-15).

## 3. Decisions (REASONED)

- **D1. `ForeignToken` is a `StaleRead`, NOT a `LookupNotFresh`, on every surface
  including `lookup` / `lookup_reverse`.** `LookupNotFresh` is documented as RECOVERABLE
  ("run catch_up() and retry"); a foreign token is not, and `IndexStalled` already shows
  the family is "subclass = narrower recoverable cause". Raising one class on all five
  surfaces makes the handler uniform: `except StaleRead` catches it everywhere (as it
  catches every lookup refusal already), and `except ForeignToken` is the precise handler.
  Cost: a caller who wrote `except LookupNotFresh: catch_up(); retry` around a lookup no
  longer catches a foreign token there; that is the intended outcome (the retry loop
  could never succeed), and the error now propagates with the real cause. A
  multiple-inheritance class (`ForeignToken(LookupNotFresh)` on lookups) was rejected:
  two classes or a diamond for one cause, and it would re-attach "retry" semantics.
- **D2. The check runs BEFORE every freshness test**, including `Store.check`'s fast path,
  so it costs one PK lookup per tokened read (none for untokened reads, `at_least=None`
  returns first). Below-the-cursor is exactly the case the fast path used to accept.
- **D3. A token that names no visible row keeps its old behaviour** (task text; B4's
  suggested fix): `token_diagnosis` still explains "past the newest log id" on the
  freshness path. Pinned by
  `tests/test_tk166_foreign_token.py::test_a_token_naming_no_row_keeps_its_old_refusal`.
  `at_least=0` names no row and still serves (`test_own_tokens_still_serve`).
- **D4. `token_diagnosis`'s foreign branch is kept.** Under READ COMMITTED each statement
  sees new commits, so a foreign row can become visible between the precheck and a
  refusal (REASONED; not exercised by a test). It is now a near-dead defensive branch.

## 4. Tests and sabotage (RAN 2026-10-23)

- `tests/test_tk166_foreign_token.py`: 37 passed (in-memory SQLite, `StaticPool`, one
  shared session as in `B5.py`). Covers each surface x {below, above} the cursor x
  {sync, async}; message content x surface x mode; `isinstance StaleRead` and not
  `LookupNotFresh`; own-token and no-row controls; B4 case 4 (async backlog); export.
- Related modules run green: `test_cascade_fixpoint_tier`, `test_connectedstore`,
  `test_connectedstore_async`, `test_connectedstore_concurrency`,
  `test_connectedstore_multi_instance`, `test_tk111_stall_aware_freshness`,
  `test_tk121_stall_recovery`, `test_tk123_pypi_page`, `test_tk123_safety_messages`,
  `test_tk123_top_level` (after the census edit), `test_tk155_store_expand`, `test_zt_p1_8`,
  `test_zt_p1_hardening`, `test_tk154_stale_lookup_ids`, `test_tk122_release_metadata`,
  `test_userdocs_examples` (36 passed: the `async-tokens.md` foreign-token example still
  prints `True`, because `ForeignToken` is a `StaleRead` and the message contains
  `not 'my-app'`). `test_postgres_ha` not run (needs a DSN). No existing test asserted the
  silent accept.
- First run of `test_tk123_top_level` was RED, as designed:
  `test_every_exception_is_rooted_and_keeps_its_builtin_base` refuses an unclassified new
  exception. Fixed by classifying it (section 2).
- SABOTAGE (`.scratch/wf-0p1/tk166-impl/sabotage.py`, gitignored; anchor
  `if owner is None or owner == store_id:` -> `if True:`, count == 1, restored and
  sha256-checked): `rc= 1`, `33 failed, 4 passed in 28.03s`. Below the cursor:
  `Failed: DID NOT RAISE ForeignToken` (B4's silent accept back); above it: the old
  `StaleRead: token 4 is not visible in this session snapshot (evaluator at 3); call
  refresh() ...` and `LookupNotFresh: lookup(at_least=4) cannot be served ...` (B5 back).
  The full tally is in the test module docstring.
- NOT done here: `formal/verify.sh` (the orchestrator runs the gate).
  `formal/FINAL_REVIEW.md`'s generated counts block will need regenerating
  (`python -m formal.conformance.doc_counts --generate`) for the +37 tests (REASONED).

## 5. userdocs pages that must change (READ by grep, 2026-10-23; NOT edited here)

Line numbers as of 2026-10-23.

| page | now says | must say |
|---|---|---|
| `userdocs/how-to/async-tokens.md` ~L201-213 (the `{warning}`) | a foreign token "is not rejected reliably"; accepted without error at or below the cursor | every tokened read refuses a token from another store with `ForeignToken` (a `StaleRead`), above or below the cursor; the message names both stores; no retry helps. |
| same page ~L215-225 (example) | "Here the foreign token is newer ..., so it is refused"; catches `StaleRead` | drop "newer than" (any foreign token is refused); prefer `except ForeignToken` (catching `StaleRead` still works). The `"not 'my-app'" in str(exc)` assertion stays true. |
| same page ~L179-200 (Handle `StaleRead`) | refresh-and-retry helper | add: do not retry a `ForeignToken` (the helper's `except StaleRead` would retry it once and fail again; catch `ForeignToken` first, or re-raise it). |
| `userdocs/explanation/consistency.md` ~L103-108 | foreign token "silently meaningless" below, refused with `StaleRead`/`LookupNotFresh` above | passed to B, it is refused with `ForeignToken` on every read, above or below B's cursor. |
| same page ~L170-176 | "The message also says, at its end, when the token was returned by a write to a different store ... an older one is accepted" | delete; replace with one line pointing to `ForeignToken` (message leads with the cause). |
| `userdocs/how-to/errors.md` ~L248-257 (`StaleRead` bullet) | "If the message says the token was returned by a write to another store ... even though the message opens with 'call refresh() ... and retry'"; "refused only when it is newer" | remove the foreign-token workaround text; add a `ForeignToken` bullet: token from another store, never retry, pass this store's own token. |
| same page ~L258-260 (`LookupNotFresh` bullet) | catch_up and retry | add: a foreign token raises `ForeignToken`, not `LookupNotFresh`. |
| `userdocs/reference/exceptions.md` ~L41-43 (tree) | `StaleRead` -> `LookupNotFresh` -> `IndexStalled` | add `ForeignToken` as a second child of `StaleRead`. |
| same page ~L98-99 (summary table) | no row | add a `ForeignToken` row: "a tokened read was passed another store's token. Not retryable; pass this store's own token." |
| same page ~L338-358 (`py:exception` entries) | `StaleRead`: "If the message ends by saying ... another store ... refused only when it is newer"; `LookupNotFresh`: "Neither helps when the token came from another store (the message ends by saying so)" | remove both foreign-token sentences; add a `.. py:exception:: zanzibar.ForeignToken` entry (Bases: `zanzibar.StaleRead`) with attributes `token`, `issued_by`, `store_id`. |
| `userdocs/how-to/query-access.md` ~L381-392 | "one family: IndexStalled < LookupNotFresh < StaleRead ... `except StaleRead` catches all three" | "all four": add `ForeignToken` as the other `StaleRead` subclass, raised by every tokened read. |
| `userdocs/reference/api/store.md` ~L265 | lists `StaleRead`, `LookupNotFresh` | add `ForeignToken` to the list of exceptions a tokened read raises. |
| `userdocs/explanation/two-backends.md` ~L88, `userdocs/how-to/postgresql.md` ~L148-167, `userdocs/explanation/limits.md` ~L260 | generic `StaleRead` / `LookupNotFresh` mentions | no change required (REASONED); optional: postgresql.md's "tokens a reader passes come from the same store" sentence if one is added. |
| `userdocs/reference/changelog.md` | mirrors CHANGELOG | refresh before release (already planned in TK151). |
| `userdocs/how-to/upgrade-0.1.md` | lists 0.1 breaks; no foreign-token item | add: "a token from another store is now refused (`ForeignToken`) where it was silently accepted". |
