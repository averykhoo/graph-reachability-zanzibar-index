---
id: TK163
title: post-commit InvariantViolation surfaces as InvalidRequestError and leaves the Store unusable
brief: paranoia full/fixpoint: after_commit raise -> caller sees InvalidRequestError, write stored, Store dead
pri: LATER
size: M
deps: []
related: [TK151]
parent:
labels: []
source: docs/tk151-repros-2026-10-20/README.md
source_hash:
created: 2026-10-20b
moved: 2026-10-23b
updated: 2026-10-23b
closed:
---

Under paranoia full/fixpoint, a check that fails in the after_commit listener reaches the caller as sqlalchemy.exc.InvalidRequestError (InvariantViolation only as __context__); the write is already committed in log and index, and the Store refuses every later call. Agent-suggested fix: record the violation on the guard in after_commit and re-raise it from Store after session.commit() returns. Check whether residue is affected (repro uses full).

Repro and first-hand output: `docs/tk151-repros-2026-10-20/README.md` section B1 (`docs/tk151-repros-2026-10-20/B1.py`). Found by the TK151 docs pass 2026-10-20b; the user docs describe the CURRENT behaviour as a caveat, so fixing this means updating the pages that section lists.

## Read first

- `docs/tk151-repros-2026-10-20/README.md`

## Log

### 2026-10-23b

From the TK151 fable review 2026-10-23 (rec 8): userdocs how-to/runtime-checks.md "When a check fails" documents this bug at length (InvalidRequestError wrapping, unusable Store, workaround helper). When TK163 is fixed, cut that section to the fixed behaviour; until then the review suggests one sentence tagged known limitation.
