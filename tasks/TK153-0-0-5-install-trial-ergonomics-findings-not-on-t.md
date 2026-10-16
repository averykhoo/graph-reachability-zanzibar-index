---
id: TK153
title: 0.0.5 install-trial ergonomics findings not on the TK123 accept list
brief: 0.0.5 trial: non-ASCII docstrings, DeltaProcessor not exported, refusal class name, 3 exceptions/1 cause
pri: NOW
size: M
deps: []
related: [TK123, TK151]
parent:
labels: [docs]
source: docs/pypi-trial-0.0.5-2026-10-15.md
source_hash:
created: 2026-10-15
moved: 2026-10-16
updated: 2026-10-16
closed:
---

These are the 0.0.5 install-trial CONFUSING / DOC GAP findings that are NOT already on
`TK123`'s accepted list (the mapping of the rest is on `TK123`, 2026-10-15). All are agent
findings, UNVERIFIED except F3, which the session confirmed first-hand.

- F3: public docstrings carry non-ASCII (`advance_index` has U+00A7 and U+2464), so `help()`
  piped to a redirected Windows stdout raises `UnicodeEncodeError`. Consider an ASCII-only pin
  on public docstrings.
- F8: the `MissingDeltaProcessor` message says pass `DeltaProcessor(widx, ruleset.compiled)`,
  but `DeltaProcessor` is in no `__all__`, and the message doesn't say where it is imported from
  (`zanzibar.graphindex.processor`).
- F9: the TK137 refusal class is publicly named `ShapeRefusedSinceTK137` and is not in
  `__all__`. Its `.instead` attribute is undocumented. `[team#member]` with no `type team`
  reports an undeclared RELATION, not an undeclared type.
- F11: a write to an undeclared relation says "matches no declared type restriction for
  doc#vewer" instead of saying that the relation is not declared.
- F17: one condition (a store persisted with a now-refused shape) raises three exception types,
  depending on the entry point: `PersistedSchemaRefused`, `SchemaMismatch` and
  `ShapeRefusedSinceTK137`.
- F6: `IndexCursor`'s repr is `IndexCursor()`; `save_schema` / `build_index` return values
  print the whole compiled RuleSet.
- F19 (doc, goes to TK151 if not done here): to list USERS from `lookup_reverse`, take the
  user-typed nodes plus markers minus exclusions. Never expand a userset node, because that
  re-includes excluded members.

## Read first

- docs/pypi-trial-0.0.5-2026-10-15.md

## Log

### 2026-10-16

USER 2026-10-16 (in chat): bumped LATER -> NEXT; in scope for 0.1.0. The renames (DeltaProcessor export, ShapeRefusedSinceTK137, the three-exceptions-one-cause F17) belong in the 0.1.0 break.

Two more help()-visible text findings from the TK150 scout (docs/closure-fanout-cost-2026-10-14.md, Correction 2026-10-16 (c), READ 2026-10-16): (1) src/zanzibar/schema/errors.py::ClosureFanoutExceeded docstring says the bug "does not bite at the 100,000 default, which is why no test caught it" -- FALSE (spec-deviations "Corrected 2026-10-03b (TK112)": a grant or ban over a >100,000-member group bites at the default); (2) core.py comment above DEFAULT_MAX_CLOSURE_FANOUT says "44 rows in tests/" -- re-measured 93 (2026-10-16). Check claim_rot pins before editing either.

NEXT -> NOW at the 2026-10-16 write-back (TK154 closed, NOW was empty). Why this row first: its exception-naming items (ShapeRefusedSinceTK137, the three-exceptions-one-cause F17, DeltaProcessor export) are API renames that belong in the 0.1.0 break, and TK154 just added StaleLookupIds / TablesOutdated to the same exception surface, so settle the naming once. User order for the rest of NEXT: TK147, then TK138/TK144 last.
