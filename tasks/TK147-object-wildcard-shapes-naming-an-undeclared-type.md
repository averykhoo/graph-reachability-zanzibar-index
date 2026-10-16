---
id: TK147
title: object_wildcard_shapes naming an undeclared type or relation is silently accepted (TK137 C7)
brief: a typo in owc shapes is a silent no-op (fails closed); refuse it with a REFUSED SHAPE block
pri: NEXT
size: S
deps: []
related: [TK137]
parent:
labels: []
source: docs/tk137-dsl-openfga-refusals-2026-10-14.md
source_hash:
created: 2026-10-14
moved: 2026-10-16
updated: 2026-10-16
closed:
---

Sibling of TK137 (challenge C7, `docs/tk137-dsl-openfga-refusals-2026-10-14.md`), deliberately kept out of TK137's DSL scope.

`object_wildcard_shapes` naming an undeclared type or relation is silently ACCEPTED. Challenge PROBE X9, 2026-10-14: `parse_openfga_schema(..., object_wildcard_shapes={('nosuch','viewer')})` and `{('doc','nosuchrel')}` both accept. REASONED: it fails closed (the shape is a no-op, no access is granted), so it is not a grant like TK137's S8 (undeclared restriction type), but it is the same typo class: the caller believes an object wildcard is enabled and it is not.

Proposed (REASONED): refuse at construction, in every path that accepts `object_wildcard_shapes` (`parse_openfga_schema`, `SetEngine`, and wherever the store/JSON front end passes it through), with a REFUSED SHAPE / WHY / INSTEAD block per the refused-shape rule; mirror in the oracle if the oracle accepts the same argument, so the parity tests stay two-sided.

Done when: both an undeclared type and an undeclared relation are refused with a message naming the shape, pinned by tests that go red when the check is deleted.

## Traps

- Persisted stores: if any persisted record carries owc shapes, a new refusal may stop an old store reopening (the same question as TK137 R1); check before landing.

## Read first

- `docs/tk137-dsl-openfga-refusals-2026-10-14.md` (Corrections, C7).
- `src/zanzibar/schema/parser.py`.

## Log

### 2026-10-16

USER 2026-10-16 (in chat): bumped LATER -> NEXT; in scope for 0.1.0.
