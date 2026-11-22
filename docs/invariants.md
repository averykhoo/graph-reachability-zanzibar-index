# Residual-risk register

LIVING. Residual risks (FRAMEWORK P17, §7.4): each is a risk that was not reasonably practicable to
eliminate, with whom it affects, why it stays, the control that holds it and where it came from.
`task close` appends the residuals of a task's `## Design review`; edit an entry only when the
code changes. Ids are `RISK-n`, never reused.

## RISK-1: (retired 2026-11-22a: eliminated by TK-304 D1, commit 019c3c3: readcheck.py::lists_subject_shape prunes it from Store and SetEngine listings) lookup_reverse and expand list a userset key reached through a TTU target whose type does not declare the relation, which check() refuses (D03 half closed); both backends identical, so equivalence holds

- **affects:** a 0.1.3 user who feeds a lookup_reverse or expand result back into check
- **why not eliminated:** pruning it changes both backends read algorithms and the Lean-modelled expand shape, out of the 0.1.3 batch scope
- **control:** individual: the 0.1.3 CHANGELOG Changed section discloses it; tracked as TK-304
- **from:** TK-185, session 2026-11-20a
- **retired:** session 2026-11-22a (claude-code/claude-opus-5-5): eliminated by TK-304 D1, commit 019c3c3: readcheck.py::lists_subject_shape prunes it from Store and SetEngine listings; kept so its id is never reused

## RISK-2: ensure_schema skips require_shapes when the schema row exists, so a bad object_wildcard_shapes entry there raises SchemaMismatch, not TypeError (wrong class, never a wrong answer)

- **affects:** a caller of the internal schema_io.ensure_schema
- **why not eliminated:** internal path, not in zanzibar.store __all__; every public caller (Store, Store.adopt) runs require_shapes first
- **control:** reduce: the public callers require_shapes call; tracked in TK-305
- **from:** TK-185, session 2026-11-20a

## RISK-3: a malformed hashable object_wildcard_shapes entry such as (doc, 5) is ShapeNoLongerAccepted while an unhashable one such as [doc, 5] is TypeError

- **affects:** a user who catches one class for every malformed shape entry
- **why not eliminated:** the TK147 ShapeNoLongerAccepted class was kept by decision (TK-185 plan step 2)
- **control:** individual: the 0.1.3 CHANGELOG wording that any entry that cannot be a set member is a TypeError
- **from:** TK-185, session 2026-11-20a
