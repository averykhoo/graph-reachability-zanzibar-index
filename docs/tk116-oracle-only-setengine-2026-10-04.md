# TK116 -- set engine vs oracle, with removes, on every graph-refused family (2026-10-04)

**FROZEN 2026-10-04d, at `TK116`'s close -- provenance, not a living document.** Status lines
below are as-of-then. Corrections are appended dated at the top, never edited into the body.

Row: `python scripts/task.py show TK116`. Filed from `docs/p10-scope-audit-2026-09-27.md`
sec 5 H6. Provenance labels: **READ** (first-hand read of the tree), **RUN** (first-hand
run, output quoted), **REASONED**.

## 1. What changed since the row was filed (READ, 2026-10-04d)

The row's witness list predates `TK106` / `TK108` / `ASK-1` / `TK114`. Of the eleven
`tests/genswarm.py::REJECTION_WITNESSES`, seven are now PARSE refusals (`ValueError`): both
parsers refuse them, so the set engine never runs them and they are out of this row's
scope. The graph-only refusals left are the raise sites of `UnsupportedByGraphIndex` /
`CyclicDerivedDependency` in `zanzibar_utils_v1.py` -- twelve of them (2026-10-04d,
`tests/test_tk116_oracle_only_setengine.py::test_every_graph_refusal_site_has_a_witness`
counts them):

| family (witness name in the test) | raise site | set engine runs it? |
|---|---|---|
| `owc-on-derived` | `_reject_owc_scope`, shape on a tainted relation | yes (RUN) |
| `owc-names-a-leaf` | `_reject_owc_scope`, declared `.`-name shape | yes (RUN) |
| `owc-expands-onto-leaf` (P10 W1) | `_reject_owc_scope`, expansion onto a leaf | yes (RUN) |
| `owc-on-derived-ttu-tupleset` | `_reject_owc_scope`, shape on a derived TTU's tupleset | yes (RUN) |
| `owc-upstream-of-derived-ttu-target` (D4) | `_reject_owc_scope`, D4 | yes (RUN) |
| `star-tupleset-over-derived-target` | `_reject_owc_scope`, star tupleset | yes (RUN) |
| `wildcard-userset-over-derived` (P10 W2) | `_build_plan_tree` | yes (RUN) |
| `ttu-target-name-is-derived-elsewhere` | `compile_ruleset`, I5 name collision | yes (RUN) |
| `cyclic-derived-dependency` | `_stratify` | yes (RUN) |
| -- unreachable -- | `_emit_relation`, `enable_boolean=False` only | n/a |
| -- unreachable -- | `compile_ruleset`, computed tupleset (parse refuses, TK106) | n/a |
| -- unreachable -- | `compile_ruleset`, userset tupleset (parse refuses, TK108) | n/a |

For every reachable family, `ParityEngine` degrades to set:py + set:roaring + oracle and
both `SetEngine._ruleset`s are `None` (RUN).

## 2. FINDING: set-engine `lookup` fails open under `but not` with an object wildcard (RUN)

The new lookup gate (`_Gate(..., allow_graph_absent=True)`) went red on two families on its
first run. Minimal repro, `owc = {(doc, viewer)}`:

```
define public: [user:*]
define blocked: [user]
define viewer: ([user] or public) but not blocked

add user:n1 viewer doc:*      accepted
add user:n1 blocked doc:n2    accepted
check(user:n1, viewer, doc:n2)   set=False  oracle=False
lookup(user:n1)                  LookupResult(node_ids={2}, markers={('doc', 'viewer')})
```

Literal gate output:

```
lookup/oracle divergence (owc-on-derived: add ('...', 'user', 'n1', 'blocked', 'doc', 'n2')):
  set.lookup('...', 'user', 'n1') [py] vs oracle on viewer doc:n2: set=True oracle=False
lookup/oracle divergence (owc-expands-onto-leaf: add ('...', 'user', 'n1', 'banned', 'doc', 'n2')):
  set.lookup('...', 'user', 'n1') [py] vs oracle on view doc:n2: set=True oracle=False
```

Mechanism (READ, `setengine/engine.py::SetEngine.lookup`): the marker loop adds `(t, rel)`
whenever `check(subject, rel, t:*)` is true, and a marker means "every `t` object". Under
`but not` the star-object answer is true while a concrete object is subtracted, and
`LookupResult` had no field to say so. `check` is right; only the lookup surface lies.
It is a FAIL-OPEN: a caller listing "docs n1 can view" is told every doc, `doc:n2` included.

Reach (REASONED): a marker needs star-object state on `rel`. On a graph-joined schema an
object wildcard never reaches a derived relation (these two refusals are exactly that rule),
and an untainted relation has no subtraction, so the lie needs a graph-refused schema. Only
standalone `SetEngine` users see it: `connectedstore/schema_io.py::save_schema` refuses every
graph-refused schema.

The check grid (`test_set_engine_matches_oracle_with_removes`, 27 cases) was green on the
same schemas: it never reads `lookup`. This is the gap H6 named, and it held a bug.

### Decision (session, under `CLAUDE.md` "Who decides", 2026-10-04d)

Fix the surface rather than refuse the schemas in the set engine. The set engine is the
reference backend for exactly these schemas, and the repair is local: `LookupResult` gains
`excluded_node_ids` (the name and meaning of `index_v4/wildcard.py::LookupResult`'s field,
"everyone of a starred shape EXCEPT these"), filled for each marker with the interned
concrete `(t, X, rel)` keys that `check` refutes. Completeness rests on the X1 claim that
every tuple-anchored object key is write-time interned; the gate's ghost-object candidates
test the uninterned side.

### Landed (RUN, 2026-10-04d)

`setengine/engine.py::LookupResult.excluded_node_ids` and the exclusion loop in
`SetEngine.lookup`; `tests/test_lookup_oracle.py::_check_set_forward` now reads coverage as
"marker minus exclusions" and asserts every excluded id is concrete, marker-covered and
oracle-false. Pinned exact by
`tests/test_tk116_oracle_only_setengine.py::test_lookup_marker_carries_its_exclusions`
(both SetOps). `tests/test_lookup_oracle.py` stays green over the graph-joined fixtures,
where the field is always empty.

## 3. The admission asymmetry (decision, 2026-10-04d)

KEPT and pinned (`test_admission_asymmetry_is_deliberate`): the same `group#member` data
cycle is refused when the schema joins the graph and accepted when it is graph-refused.
Reasoning is in that module's docstring; in short, cycle rejection is the graph's admission
constraint, not a semantic rule, and the accepted cycles are now oracle-checked.

## 4. Not in scope, noted (READ)

`SetEngine.lookup_reverse` still drops `neg` by design (documented one-sided, S3 in
`tests/test_lookup_oracle.py`; `docs/spec-deviations.md` "drops information by design").
That is the reverse surface on graph-JOINED schemas too, and it is documented, so it is not
this row's.

## 5. The other row items (RUN, 2026-10-04d)

- `tests/test_lookup_oracle.py::_Gate` takes `allow_graph_absent=True` and then checks the
  set surfaces only; `test_lookup_oracle_gate_generated_schemas` uses it on a recorded
  refusal instead of returning. That test is hypothesis-drawn, so
  `test_generated_refused_schemas_run_the_set_only_lookup_gate` is the deterministic floor
  (first 4 refused draws of the seeded join-rate generator, each with an accepted remove).
- The stale "Boolean schemas have no graph partner" comment in `SetEngine._would_cycle` is
  rewritten (graph-REFUSED schemas have none; compiled booleans do since P7).
- The dead `continue` in
  `tests/test_hypothesis.py::test_every_tupleset_kind_is_driven_against_the_oracle` is
  gone: a probe cell that stops joining the graph now raises out of the test.
- H1 (`TK114`, stratified negation) landed first, as the row anticipated: negative cycles
  are parse refusals, so the cyclic witness is the positive TTU-target cycle.

## 6. Mutation sweep of the new module (RUN, 2026-10-04d)

`.scratch/tk116/sweep.py` (gitignored; the table is the record): each mutation applied
alone, `tests/test_tk116_oracle_only_setengine.py` run, files restored and verified
byte-identical (`RESTORED byte-identical: True`). Every anchor matched exactly once.

| id | mutation | verdict | first-attributed red |
|---|---|---|---|
| M0 | CONTROL: the walk's floor claims `removes == 0` | RED | `test_set_engine_matches_oracle_with_removes` (all 27) |
| M1 | the fix removed (`excluded_node_ids.add` -> `pass`) | RED | exact pin x2, lookup gate on owc-on-derived / owc-expands-onto-leaf, both tampers |
| M2 | checker coverage ignores exclusions | RED | lookup gate x2, both tampers |
| M3 | checker exclusion-soundness loop removed | RED | tamper `spurious` only |
| M4 | `_Gate` skips the set battery when the graph is absent | RED | lookup gate x9 (`set_checks` floor) |
| M5 | `ParityEngine` skips grid parity when the graph is absent | RED | `test_walk_catches_a_planted_set_engine_lie` |
| M6 | one `UNREACHABLE` entry dropped | RED | census |
| M7 | a witness message widened to `object-wildcard shape` | RED | `test_witness_families_are_distinct` |
| M8 | `_would_cycle` refuses same-shape usersets with no RuleSet | RED | asymmetry pin + wildcard-userset witness x4 |
| M9 | `_Gate.apply` applies set:py twice (this session's own first bug) | RED | generated set-only floor + lookup gate x9 |
| M10 | the exclusion loop probes `*` instead of the object | RED | exact pin x2, lookup gate x2, both tampers |

M3 was PREDICTED INERT and was not. The spurious exclusion (`doc:n1#viewer`) is also in
`node_ids`, so the coverage clause reads it as covered and cannot see the bad exclusion.
Re-run alone: `Failed: DID NOT RAISE AssertionError`. The soundness clause is load-bearing.
M5 is the one the planted-lie control exists for: without it, a ParityEngine that stopped
comparing on graph-absent schemas stays green on a bug-free engine.
