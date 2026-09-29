---
id: ASK-2
title: keep the wildcard extensions OpenFGA lacks (userset stars, star tuplesets, object wildcards)?
brief: user 2026-09-26: KEEP wildcard extensions beyond OpenFGA; UnprovenExtensionWarning tells callers
pri: LATER
size: S
deps: []
related: [ASK-1, TK106, TK104]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-26b
moved: 2026-09-29
updated: 2026-09-29
closed:
---

**Question for the user (product behaviour, not an engineering call):** should the repo keep
its three wildcard extensions that OpenFGA does not have?

1. wildcard USERSETS: `viewer: [group:*#member]` ("every member of every group");
2. STAR TUPLESETS: a stored `doc:d1#parent@folder:*` walked by `viewer from parent`
   ("d1's parent is every folder");
3. OBJECT WILDCARDS: a grant on `folder:*` itself, API-only via `object_wildcard_shapes`
   (no DSL syntax).

The bare public grant `[user:*]` is standard OpenFGA and is NOT part of this question.

**State (READ 2026-09-26, `formal/lean/ZanzibarProofs/FullScope.lean`):** both backends
implement all three and the differential matrix / oracle pin that they agree, but the
headline theorems do not cover them. `W4Fragment.wsBare`, `W4Fragment.bareStar` and
`W4Fragment.ttuStarFree` exist to exclude them, and `GraphAdmission.objWild` /
`GraphAdmission.usWild` restrict where they meet derived (boolean) relations. A schema or
store using one rests on the tests alone.

**Options put to the user 2026-09-26:** drop all three (OpenFGA-aligned; those fields go
vacuous; UNVERIFIED claim from the ASK-1 session that the premise would then cover every
accepted non-boolean schema; unmeasured size-L change), drop some, keep and widen the
proofs (`ttuStarFree` part (iv) is partly started), or keep and track.

**User answer 2026-09-26: KEEP THEM, JUST TRACK IT.** No code or proof change. The gap
stays documented by the fields above. This row stays open so the question is visible if
the priorities change (e.g. if proof coverage of every accepted schema becomes a goal, or
a real consumer turns up). If reopened for action, the first step is a census in the
ASK-1 shape (`docs/ask1-schema-self-consistency-2026-09-26.md`) before any edit.

## Log

### 2026-09-26b

**Follow-up, same day (user request): callers are now TOLD.** "can you add python warnings or something so anyone using it is told it's not been proven correct".

LANDED: `zanzibar_utils_v1.py::UnprovenExtensionWarning` (a `UserWarning`), emitted by `::_warn_unproven_extensions` from `::derive_schema_info`, the step every construction path shares (`parse_openfga_schema`, `SetEngine.__init__`, `connectedstore/schema_io.py`). `::unproven_extensions` lists the features found. It fires on a literal `[T:*#p]`, on a from-tupleset admitting `[T:*]`, and on non-empty `object_wildcard_shapes`. A bare `[T:*]` is silent, because it is standard OpenFGA. The warning is schema-level: it fires when a schema ADMITS a star tupleset, even before one is stored.

`pytest.ini` ignores it suite-wide (`ignore:UNPROVEN:UserWarning`; a colon cannot appear in the message field, and a dotted category would import the module at config time). PROBED: the same probe test shows `1 passed, 1 warning` without the ini and `1 passed` with it.

Pinned by `tests/test_unproven_extension_warning.py` (8 tests). SABOTAGE 2026-09-26: with the call deleted, the result was `6 failed, 2 passed`: all six warning tests went red and the two silence tests stayed green. Restored: `8 passed`. `MIN_TESTS_ALL` 1328 -> 1336 (collect-only 1336, +8, no drift).

Gate: see the session-log entry `2026-09-26b`.

### 2026-09-27d

P10 re-run (2026-09-27d, docs/p10-scope-audit-2026-09-27.md sec 6): star-userset subjects created by a star tupleset (e.g. doc:*#r0) agree 4-way but no grid asks them on the check surface. The coverage fix is owned by TK117.

### 2026-09-29

Follow-up, user decision 2026-09-29: the OpenFGA registry / organization idiom (one bookkeeping tuple linking each instance to a registry object) is NOT supported as a substitute for `*`. It is a hand-maintained `*`: a missed registration is silently wrong, fail-open under `but not`, and it moves the proof gap into an unchecked application invariant rather than closing it. Nothing refuses it (plain tuples). Recorded in docs/architecture/decision-log.md sec "Wildcards beyond OpenFGA", README.md sec "`*` wildcard entities", and the CLAUDE.md ASK-2 bullet. Also fixed: README called `group:*#member` an OpenFGA wildcard; it is one of the extensions. Row stays open at LATER; the answer to the original question is unchanged (keep them).
