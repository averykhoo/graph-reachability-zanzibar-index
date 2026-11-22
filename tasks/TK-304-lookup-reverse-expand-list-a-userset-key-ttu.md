---
type: Task
id: TK-304
title: lookup_reverse/expand list a userset key (TTU target whose type doesn't declare the relation) that check() now refuses (TK-185 D03)
brief: prune identically in BOTH backends; read-algorithm change, so CORRESPONDENCE/Lean check first; never edit the oracle
pri: NEXT
state: closed
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-22a
updated: 2026-11-22a
status: deprecated
closed: 2026-11-22a
---

lookup_reverse/expand list a userset key (TTU target whose type doesn't declare the relation) that check() now refuses (TK-185 D03).

Since 0.1.3 (TK-185, DEC-16) a read naming an undeclared type or relation is refused. D03 is half closed:

- Repro (independent verifier, first-hand, 2026-11-20): schema with `viewer from parent`, `parent: [folder, team]`, and `team` declaring no `viewer`. `lookup_reverse('viewer', 'doc', '4')` and `expand` return `('team', 't1', 'viewer')` on both backends, while `check('viewer', 'team', 't1', 'viewer', 'doc', '4')` is refused (`UndeclaredTypeOrRelation`) on Store sync, stalled, tokened-lagging and SetEngine.
- So a list call can return a key that `check` refuses to take back.
- Both backends behave identically, so EQUIVALENCE holds. The CHANGELOG `### Changed` for 0.1.3 discloses it.
- Fix direction: prune such usersets from `lookup_reverse` / `expand` output in BOTH backends, identically. That changes the read algorithms and the Lean-modelled `expand` shape, so check `formal/CORRESPONDENCE.md` and the Lean model (CLAUDE.md, Perf work and the Lean model) before landing; the lookup oracle (`tests/test_lookup_oracle.py`) must agree.
- Rank (rerank 2026-11-20a): NEXT. EQUIV across read surfaces, and RELEASE: a 0.1.3 user can hit it.

## Traps

- Never edit an oracle result or golden to make the pruning pass; if the oracle disagrees, the spec question goes on this row first.

## Read first

- docs/tk185-0.1.3-batch-2026-11-20.md (section "Residual (filed at the close, not fixed here)")
- docs/decisions (DEC-16)

## Log

- 2026-11-22a (claude-code/claude-opus-5-5): 2026-11-23 (session 2026-11-22a). DECISION D1 (PROVISIONAL, claude-code/claude-opus-5-5): the listing rule is the refusal's twin and lives where the refusal lives. Store.lookup_reverse, Store.expand, SetEngine.lookup_reverse and SetEngine.expand drop every key, marker and exclusion whose (type, predicate) check() refuses as a subject, through ONE predicate src/zanzibar/schema/readcheck.py::lists_subject_shape (set side: SetEngine.expand's top-level call via ::SetEngine._declared_members; graph side: Store.lookup_reverse via WildcardIndex._filter_shapes). WildcardIndex stays lenient (DEC-16 item 5). Oracle NOT edited; the lookup-oracle set-side reference leaves such subjects out (tests/test_lookup_oracle.py::_listed). Why safe: such a userset has no members (no write can name it). Rejected: letting check answer it (reverses DEC-16, an owner decision); pruning inside WildcardIndex (lenient surface would disagree with its own lenient check). Finding: the lookup-oracle random walk never reached the D03 state (seed-0 history has no folder parent), so a new deterministic gate test was added. Sabotage S1-S4 seen red (literal output in tests/test_tk304_undeclared_userset_listing.py docstring). Plan doc: docs/tk304-prune-undeclared-usersets-2026-11-23.md.
- 2026-11-22a (claude-code/claude-opus-5-5): 2026-11-23 LANDED (pre-commit): prune in readcheck.py::lists_subject_shape, SetEngine._declared_members, Store.lookup_reverse (merged with the TK156 subject filter into one WildcardIndex._filter_shapes call, per review). Tests +8 (tests/test_tk304_undeclared_userset_listing.py 7, lookup-oracle 1); MIN_TESTS_ALL 3995 -> 4003 via doc_counts --generate. Review (read-only agent): no blocker; port-openfga.md sentence fixed; RISK-1 to retire at close. Sabotage S1-S4 + S2b red. Docs: CORRESPONDENCE TK-304 re-read + pin regen, spec-deviations 2026-11-23, semantics-vs-openfga example. Next: full gate, commit, retire RISK-1, close. The next release CHANGELOG owes a Fixed line.
- 2026-11-22a (claude-code/claude-opus-5-5): closed: lookup_reverse/expand prune the userset keys check() refuses, on Store and SetEngine (D1, commit 019c3c3); RISK-1 retired; plan doc frozen
  residual risk: none
