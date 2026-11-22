# `TK-304` -- lookup_reverse / expand stop listing a userset key check() refuses (2026-11-23)

FROZEN 2026-11-23 (session 2026-11-22a): TK-304 closed (commit 019c3c3); below, the plan as it stood

**ACTIVE-PLAN, opened 2026-11-23 (session `2026-11-22a`) -- the body is provenance, not a living
status.** Live state is the row (`context-engine task show TK-304`) and
`python scripts/gate_status.py`, never this file. Corrections append **dated at the top**.
Freeze it when `TK-304` closes.

Provenance labels: **READ** = read first-hand by the task-owner agent; **REASONED**; **AGENT**
= a subagent's report, UNVERIFIED until marked otherwise. Line numbers are dated 2026-11-23.

## The repro (READ, first-hand, 2026-11-23 01:58)

Schema: `type user`; `team` declares only `member`; `folder` declares `viewer: [user]`; `doc`
declares `parent: [folder, team]` and `viewer: [user] or viewer from parent`. Tuples
`folder:f1 parent doc:4`, `team:t1 parent doc:4`, `user:u viewer folder:f1`.
Script: `.scratch/tk304-2026-11-23/repro.py` (gitignored; its output is quoted here).

- `Store.expand('viewer', 'doc', '4').keys` = `doc:4#viewer, folder:f1#viewer, team:t1#viewer, user:u`
- `SetEngine.lookup_reverse` keys and `SetEngine.expand(...).pos` keys: the same four.
- `Store.lookup_reverse` (graph path): node ids `{3, 4, 6, 7}`, the same four keys.
- `Store.check('viewer', 'team', 't1', 'viewer', 'doc', '4')`: refused,
  `UndeclaredTypeOrRelation` (TK-185, DEC-16).

## Where the key comes from (READ + REASONED)

- READ: the only way a `(T, n, p)` userset node or member with `(T, p)` undeclared arises is a
  TTU `p from ts` where a restriction type `T` of `ts` declares no `p`. Writes are admission-
  checked (a tuple can neither name nor target an undeclared relation), and a computed rewrite
  stays on its own type, whose relations the self-consistency rule (ASK-1) makes declared.
- REASONED: such a userset has NO members, ever: nothing can be written to `T:n#p`. So dropping
  it from a listing removes no user and no exclusion a caller could act on; it removes exactly
  the key `check` refuses to take back.

## Decision D1 (PROVISIONAL, claude-code/claude-opus-5-5, 2026-11-23)

**The listing rule is the refusal's twin, and lives exactly where the refusal lives.** A read
surface that refuses an undeclared subject (`Store`, `SetEngine`: DEC-16) never LISTS one:
every key, marker and exclusion whose `(type, predicate)` is not a bare subject (`'...'`) of a
declared type or a declared `(type, relation)` is dropped from the result. One predicate,
`src/zanzibar/schema/readcheck.py::lists_subject_shape`, is used by both backends.

- Set side: `SetEngine.expand`'s TOP-LEVEL call (the same `memo is None` boundary that holds
  its refusal), after the TK144 self-relation correction, through
  `::SetEngine._declared_members`. This reaches `SetEngine.lookup_reverse` (expand rendered)
  and `Store.expand` (delegation). The modelled recursion (`expand.do` / `do_expr`, the Lean
  `expandAux` shape twin) is unchanged: a boundary post-filter, like TK185's preconditions.
- Graph side: `Store.lookup_reverse`, right after `WildcardIndex.lookup_reverse`, through the
  shape post-filter `WildcardIndex.filter_result` already uses (TK156 precedent: filtering a
  computed result changes no modelled algorithm). `WildcardIndex` itself stays lenient
  (DEC-16 item 5): it neither refuses nor prunes, so its raw closure is still what G1-G4 of
  `tests/test_lookup_oracle.py` pin against the oracle.
- The oracle is NOT edited: `oracle.check` still says the userset is a member (it is, as a
  pointwise statement about a query the product refuses). The lookup-oracle's set-side
  reference (S1/S3) composes the oracle over DECLARED candidate subjects only, and pins every
  undeclared candidate as ABSENT from the set-side listing (a positive pin, never an xfail).
- Alternatives rejected: (a) let `check` answer such a subject (reverses DEC-16, an owner
  decision); (b) prune inside `WildcardIndex.lookup_reverse` (makes the lenient surface
  disagree with its own lenient `check`, and moves a content-pinned anchor for no gain).

## Correction (2026-11-23, READ): the lookup-oracle gate never reached D03

The plan above expected `tests/test_lookup_oracle.py` S1/S3 to go red on the prune. They did
not: `test_lookup_oracle_gate_undeclared_from_chain_subject_refused`'s seed-0 walk never adds
`folder:f1 parent doc:d1` (READ: its history holds only the `doc` parent), so no state ever
listed `folder:f1#r1`. Added `test_lookup_oracle_gate_undeclared_from_chain_userset_unlisted`
(deterministic adds, then drain) with a reach counter (`_Gate.set_unlisted_true`) and the
`_listed` set-side reference. Sabotage results: the docstring of
`tests/test_tk304_undeclared_userset_listing.py` (S1-S4, literal output).

## Review (2026-11-23, AGENT: read-only reviewer, `.scratch/tk304-2026-11-23/review.md`)

No blocker. Acted on: RISK-1 retired at the close; `userdocs/how-to/port-openfga.md` § 4 no
longer says a check on `team:1#viewer` is answered (pre-existing since 0.1.3); the Store
prune and the TK156 subject filter are one `_filter_shapes` call (one node load). The S2
sabotage was re-run on the merged form (red, same 3 failures).

## What landed (2026-11-23)

- `src/zanzibar/schema/readcheck.py::lists_subject_shape`; `src/zanzibar/setengine/engine.py::SetEngine._declared_members`
  (called from `SetEngine.expand`'s top level); `src/zanzibar/graphindex/wildcard.py::WildcardIndex._filter_shapes`
  (`filter_result`'s body, split out); `Store.lookup_reverse` calls it.
- Tests: `tests/test_tk304_undeclared_userset_listing.py` (7); one new lookup-oracle test.
- Docs: `formal/CORRESPONDENCE.md` (expand row + TK-304 re-read; content pin regenerated
  after the reading), `docs/spec-deviations.md` `## 2026-11-23`, the executed example in
  `userdocs/explanation/semantics-vs-openfga.md`. CHANGELOG: none here (entries are written
  at release); the next release's `### Fixed` owes one line for this.

## Status

| step | item | state |
|---|---|---|
| 1 | shared predicate + set-side prune + Store graph-side prune | LANDED |
| 2 | tests: positive pins on Store sync/async + SetEngine, lookup-oracle S1/S3 rule | LANDED |
| 3 | sabotage each prune, record literal output | DONE (S1-S4) |
| 4 | CORRESPONDENCE re-read note, RISK-1 retired, spec-deviations | LANDED (RISK-1 retire with the close) |
| 5 | review subagent, gate, commit | see the row |
