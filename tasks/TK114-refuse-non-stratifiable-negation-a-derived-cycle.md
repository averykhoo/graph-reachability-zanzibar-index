---
id: TK114
title: refuse non-stratifiable negation: a derived cycle through a TTU target with a but-not subtrahend
brief: schema-refusal decision (model may take it): negation around a TTU-target cycle has no/many fixpoints
pri: NOW
size: M
deps: []
related: []
parent:
labels: [formal]
source: docs/p10-scope-audit-2026-09-27.md
source_hash:
created: 2026-09-27d
moved: 2026-10-03e
updated: 2026-10-03e
closed:
---

Filed from the P10 re-run (2026-09-27d). Full witness, provenance and reconciliation: [`docs/p10-scope-audit-2026-09-27.md`](../docs/p10-scope-audit-2026-09-27.md) §5 H1. The section is copied below as it stood when filed; the doc is the body of record.


**Witness** (*audit* `PROBED`, reproduced by *verify* with its own `vprobe.py`, 2026-09-27):

```
schema: type user / type doc / relations / define parent: [doc]
        define viewer: [user] but not viewer from parent
product parse_schema_ast OK dict / oracle parse_schema_ast OK dict
graph compile: EXC CyclicDerivedDependency ... [('doc', 'viewer')]
ConnectedStore EXC CyclicDerivedDependency ...
self-parent (user:u viewer doc:a; doc:a parent doc:a):
  se._ruleset is None: True; both adds -> True
  set.check {'a': True}; oracle {'a': True}
  RHS(set answer) = {'a': False} NOT A FIXPOINT; all fixpoints: NONE (paradox)
2-cycle (a<->b, u direct viewer of both):
  set.check {'a': False, 'b': False}; oracle the same
  RHS ... {'a': True, 'b': True} NOT A FIXPOINT
  all fixpoints: [{'a': False, 'b': True}, {'a': True, 'b': False}]
3-cycle: all True on both; NOT A FIXPOINT; NONE (paradox)
acyclic control: {'a': False, 'b': True}  (a fixpoint)
```

The two evaluators agree only because they share the in-progress ⇒ False convention
(`tests/oracle.py::Oracle.check`, inner `sat`). The answers are not models of the schema.
Every generator self-reference is positive, so no generator reaches this (`READ`, audit +
verify).

**Proposed row** — *"Refuse non-stratifiable negation: a derived cycle through a TTU target
with a `but not` subtrahend edge"*, **LATER**, size S-M.
Brief: after ASK-1, a derived cycle through a TTU target is still legal. When an edge on that
cycle sits in a `but not` subtract position (e.g. `viewer: [user] but not viewer from
parent`), the schema has no fixpoint, or several, on cyclic data. The graph and
`ConnectedStore` refuse it (`CyclicDerivedDependency`). The standalone `SetEngine` and the
oracle admit it and agree on answers that are not models (probe above). Refuse it at parse
time in both parsers, in a `_validate_*` function in `zanzibar_utils_v1.py` with an
independent twin in `tests/oracle.py`, each with REFUSED SHAPE / WHY / INSTEAD. INSTEAD:
`blocked: [user] or blocked from parent` plus `viewer: [user] but not blocked`. Keep positive
TTU-target cycles legal: `tests/genswarm.py` `self_ttu` and the ASK-1 witnesses depend on
them. Pin both schemas as refused, with sabotage. Correct `formal/ARCHITECTURE.md` and
`formal/FINAL_REVIEW.md`, whose "rejected upstream" becomes true only then, and act on
`formal/SEMANTICS.md` §4.4's standing recommendation. This is a schema-refusal decision of
the same kind as ASK-1 and TK106. Under "Who decides" the session may take it, since the
refused shape has no defined semantics. Until it lands: a positive characterization pin of
the answers, never an xfail.

## Log

### 2026-10-03c

PROMOTED LATER -> NEXT (user decision 2026-10-03c). Why: on this shape the set engine and the oracle agree on answers that are NOT models of the schema, because both use the in-progress=>False convention -- the oracle is not an independent referee here, which is a confidence leak in the equivalence gate itself. Triage (AGENT-REPORTED 2026-10-03c, PROBED) reproduced the row's witness: `viewer: [user] but not viewer from parent` parses in both parsers; graph compile raises `CyclicDerivedDependency`; a standalone `SetEngine` accepts the cycle-closing parent write; self-parent gives set = oracle = {a: True} (not a model), 2-cycle gives {a: False, b: False} (not a fixpoint). NOT adversarially verified -- re-probe first-hand before designing. The schema-refusal decision is the model's to take (`CLAUDE.md` "Who decides"). Map: `docs/promote-next-triage-2026-10-03.md`.

### 2026-10-03e

NEXT -> NOW at the 2026-10-03e write-back: P23 closed and lint needs exactly one NOW. TK114 is the second of the user 2026-10-03c NEXT picks (banner order P23, TK114, TK115). No new ranking decision is implied.
