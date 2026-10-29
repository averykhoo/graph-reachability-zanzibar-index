---
id: TK173
title: 0.1.0 install trial doc gaps: five CONFUSING / DOC GAP findings (F7, F9, F12, F14, F22)
brief: 0.1.0 trial F7/F9/F12/F14/F22: refusal rewrites, old-keyword arity error, PySets(), or-operand order, perms.db reuse
pri: LATER
size: S
deps: []
related: [TK171, TK172]
parent:
labels: [docs]
source: hand
source_hash:
created: 2026-10-30
moved: 2026-10-30b
updated: 2026-10-30b
closed: 2026-10-30b
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-10-30

Source: docs/pypi-trial-0.1.0-2026-10-30.md (AGENT findings, not re-run first-hand). F7: some parse refusals are token-level with no INSTEAD (trailing `# comment`, `[user: *]`; the `but not` chain hint still talks about 0.0.4). F9: old 0.0.x keywords (`s_type=`, `o_type=`) get an arity error ("takes 3 or 6 arguments; got 5") that never names the bad keyword; "1 arguments" grammar; 6-part keyword form needs subject_predicate="..." with no hint. F12: `RoaringSets` / `PySets` are SetOps instances, so `ops=PySets()` -> TypeError: say "pass the object" in the configuration reference. F14: swapping `or` operands raises SchemaMismatch while docs say "reordered" schemas are accepted -- decide: normalise commutative operand order or narrow the docs to declaration order, and name what differs in the message. F22: README + four docs pages share sqlite:///perms.db + store "my-app" with different schemas, so following two in one folder hits SchemaMismatch. Next action: triage which ride 0.1.1 (docs-only ones are cheap).

### 2026-10-30b

All five folded into 0.1.1 (user: "do both"), each re-run first-hand against src/ first. F7: trailing `#` comment, `[user: *]`, `type us er` and the `but not` chain now name the rewrite; the `.instead` no longer cites 0.0.4. F9: tuplestr._bind names unknown keywords (with the 0.1 name for s_type/s_name/o_type/o_name), singular "1 argument", and the six-part form hints subject_predicate=... . F12: SetOps.__call__ raises "pass ops=PySets, without the parentheses"; configuration reference says so. F14: DECIDED keep refused (compiled leaf numbering follows operand order; already pinned by tests/test_tk136_schema_reopen_semantic.py), so schema/syntax.py::explain_difference adds the reason to both SchemaMismatch messages and configuration.md / exceptions.md now say which orders are free. F22: five pages moved off perms.db to their own file; pinned no-shared-file. Pins: tests/test_tk173_trial_messages.py (10 tests, 9 sabotages all red, tails in its docstring).
