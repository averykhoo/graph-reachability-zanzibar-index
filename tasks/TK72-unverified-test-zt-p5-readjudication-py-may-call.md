---
id: TK72
title: UNVERIFIED: test_zt_p5_readjudication.py may call check_invariants without schema_info (I14 off)
brief: agent claim from 2026-09-15, never reproduced; verify FIRST, then census other call sites
pri: LATER
size: S
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-16b
moved: 2026-09-16b
updated: 2026-09-16b
closed:
---

## What it is

An UNVERIFIED claim, made in passing by the 2026-09-15 adversarial audit agent while
probing `P22`, and never checked by anyone since. Recorded here so it stops travelling as a
footnote on someone else's row.

THE CLAIM (AGENT-READ, NOT reproduced): `tests/test_zt_p5_readjudication.py` calls
`check_invariants` WITHOUT `schema_info`, which disables the I14 clause outright. If that
reproduces, an invariant clause is silently switched off inside a state gate -- the same
shape as `P22`'s green sabotage, where a clause existed and nothing could reach it.

## (!) Traps

- **(!) THE CLAIM IS A SUBAGENT'S AND IS EVIDENCE, NOT A FINDING** (`CLAUDE.md`
  sec Delegation). Step one is to reproduce it: read the call sites, and if `schema_info` is
  genuinely absent, confirm FIRST-HAND that the I14 clause is thereby skipped rather than
  defaulted. Do not act on the claim as stated.
- **(!) If it reproduces, the fix is not just "pass `schema_info`".** Ask what ELSE the
  clause would have caught in that module while it was off, and whether passing it turns
  the module red today. A clause that has been disabled for a while may be guarding
  something that has since drifted.
- **(!) The generalisable question is the valuable one:** is there any OTHER
  `check_invariants` call site in the tree that omits `schema_info`? A census is cheap and
  is the difference between fixing one module and closing the class. `P22` proved the class
  exists; this row is the second instance found.

## Read first

- `tests/test_zt_p5_readjudication.py` -- the call sites in question.
- `index_v4/invariants.py::check_invariants` -- what `schema_info` gates, and what the I14
  clause asserts when it is present.
- [`docs/p22-i14-corpus-masking-2026-09-16.md`](../docs/p22-i14-corpus-masking-2026-09-16.md)
  -- the sibling case, for the shape of "the clause was there and nothing reached it".
- `docs/adversarial-audit-2026-09-15.md` sec 2 -- where the claim was made, for provenance.

## Log
