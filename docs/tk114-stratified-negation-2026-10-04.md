# TK114 -- refuse recursion through negation at parse time: the probe and the decision (2026-10-04)

**FROZEN 2026-10-04, at `TK114`'s close -- provenance, not a living document.** Status lines
below are as-of-then and may now be false; live state: `HANDOFF.md` + the session
ledger (`python scripts/task.py board`). Corrections are appended dated at the top, never
edited into the body.

Row: `python scripts/task.py show TK114`. Filed from `docs/p10-scope-audit-2026-09-27.md`
sec 5 H1; promoted by `docs/promote-next-triage-2026-10-03.md`.

## 1. What was measured (PROBED first-hand 2026-10-04, this session)

Probe: `.scratch/tk114/probe.py` (gitignored; this section is the tracked record). Each shape
was put through both checked parsers (`zanzibar_utils_v1.py::parse_schema_ast`,
`tests/oracle.py::parse_schema_ast`), the graph compile (`parse_openfga_schema`), a standalone
`SetEngine` and the oracle. Before the fix, BOTH parsers accepted EVERY shape below, and the
graph compile refused every one with `CyclicDerivedDependency`.

| shape | schema (the cycle) | data | set = oracle | a model? |
|---|---|---|---|---|
| A | `viewer: [user] but not viewer from parent` | `u viewer a`, `a parent a` | `[True]` | NO -- no fixpoint exists (paradox) |
| B | group: `member: [user] but not blocked`, `blocked: [group#member]` | `u member g`, `g#member blocked g` | `[True, True]` | NO -- `member = not member` |
| B2 | group: `member: [user] but not [group#member]` | `u member g`, `g#member member g` | `[True]` | NO |
| C | group: `member: [user, group#member] but not banned` | nested groups | `[True]` | yes -- recursion is POSITIVE (the base arm) |
| D | `viewer: [user] but not (blk but not viewer from parent)` | `u viewer a`, `u blk a`, `a parent a` | `[False]` | yes (least of two fixpoints) |
| E | `viewer: ([user] but not blk) or viewer from parent` | chain | `[False]` | yes -- positive |
| F | `a: [user] but not b`, `b: a from parent` | `u a x`, `x parent x` | `[True]` | NO |
| G | `viewer: [user] but not (ed and viewer from parent)` | self-parent | `[True]` | NO |
| H | folder `fv: [user] but not dv from child`, doc `dv: [user] or fv from parent` | cross-type | `[True, True]` | NO |

**Finding (first-hand, wider than the row):** the defect is not specific to a TTU target.
A negative cycle through a USERSET RESTRICTION (B, B2) gives the same non-model answer, and
so does one through a computed ref plus a TTU (F) and one across types (H). The row's title
named the only form the audit had found.

## 2. The decision (taken by the session under `CLAUDE.md` "Who decides", 2026-10-04)

**Refuse, in both checked parsers, any schema whose relation dependency graph has a cycle
through a negative edge.** This is classical Datalog stratified negation.

* **Edges** (`(type, relation)` -> `(type, relation)`): a computed ref; a TTU's tupleset; a
  TTU's target on every type the tupleset admits that declares it; a userset restriction
  `[T#p]` / `[T:*#p]`. A bare type restriction makes no edge.
* **Sign**: an edge is NEGATIVE if its node sits anywhere inside the subtract of a
  `but not`, at any depth (inside `and` / `or` / a nested `but not` too).
* **Why any depth, and so D is refused although it has a least fixpoint:** standard
  stratification is the rule that is easy to state, has an independent twin that is easy to
  write, and matches the per-stratum cascade. Counting negations (refuse only odd) admits D,
  whose answer depends on the evaluator choosing the LEAST fixpoint, which nothing pins.
  Refusing D costs no expressiveness: `x but not (y but not z)` is
  `(x but not y) or (x and z)`, which is positive in `z`.
* **Positive recursion stays legal** (C, E; `tests/genswarm.py` `self_ttu`, the ASK-1
  witnesses, `REJECTION_WITNESSES['cyclic-derived-dependency']`). The graph still refuses it
  at compile (`_stratify`), the set engine and oracle evaluate it as a least fixpoint. That
  divergence is a declared scope boundary, not this row.
* **Why refusal and not a semantics:** the refused shape has no fixpoint (A), or several
  (the 2-cycle in the audit), so there is no answer to be equivalent TO. The set engine and
  the oracle agreed only because both seed in-progress recursion with False; the oracle was
  not an independent referee there. Equivalence is the goal; refusing the shape is the only
  way both backends and the referee give the same, defined answer.
* **Error family:** plain `ValueError`, message contains `recursion through negation` (the
  oracle twin's message is worded differently, by design). Not added to
  `tests/genswarm.py::REJECTION_WITNESSES`: no generator reaches the shape (the row's audit,
  READ), and a witness family the enumerator never produces is red by
  `test_every_rejection_witness_family_is_actually_exercised_by_the_enumerator`. It is pinned
  in its own module instead.

## 3. Where it landed (READ: the gate ran on it, 2026-10-04)

* `zanzibar_utils_v1.py::_validate_stratified_negation`, called by `parse_schema_ast` and
  `parse_openfga_json` after `_validate_tuplesets_direct`.
* `tests/oracle.py::_validate_stratified_negation`, an independent twin (path-closure
  algorithm, not the product's per-edge search).
* `tests/test_tk114_stratified_negation.py`: every refused shape in both parsers, the
  positive controls in both, the INSTEAD rewrites parse in both, and a sabotage per parser.
* `tests/test_refused_shape_comments.py::MIN_HEADERS` +1 per parser.
* Docs: `formal/SEMANTICS.md` sec 4.4, `formal/ARCHITECTURE.md`, `formal/FINAL_REVIEW.md`
  ("rejected upstream" becomes true for NEGATION only), `_stratify`'s and
  `_validate_ast_consistency`'s comments.

**1b. Why the standalone set engine could reach the paradox at all (PROBED 2026-10-04,
`.scratch/tk114/why.py`).** Under a schema the graph COMPILES, a parent cycle is refused at
write admission on the set engine too:

```
EXC ('...', 'doc', 'a', 'parent', 'doc', 'b') AdmissionRejected tuple doc:a#... parent doc:b would create a cycle in the userset membership topology
EXC ('...', 'doc', 'c', 'parent', 'doc', 'c') AdmissionRejected tuple doc:c#... parent doc:c would create a cycle in the userset membership topology
```

(schema: the sec 2 INSTEAD rewrite.) In the original witness the graph compile FAILED, so the
set engine had no ruleset (`se._ruleset is None` in the audit's probe) and ran no such check,
and `doc:a parent doc:a` was admitted. That is the same mechanism for positive derived
recursion (shape E), which stays legal: there the set engine admits data cycles and answers
with the least fixpoint. It is not a wrong answer, but it is the one place where a parent
cycle is writable. This is noted for whoever owns that scope, not acted on here.

## 4. Mutation sweep (2026-10-04, `.scratch/tk114/sweep.py`, literal summary lines)

Each mutation edits one anchor (count asserted 1) in one file, runs
`tests/test_tk114_stratified_negation.py`, restores the file and checks its sha256. Baseline
`29 passed`. The first run had 27 cases and S9 came back **INERT** (`27 passed`): every
refused case closed its cycle in at most two steps, so an oracle closure that joined only
once refused them all. `J/three-step-cycle` was added for it. The table is the second run.

| id | mutation | verdict | summary | what went red |
|---|---|---|---|---|
| M0 | control: production treats every step as negative | RED | `6 failed, 23 passed` | the five accept controls + the 4-way INSTEAD test |
| S1 | production validator a no-op | RED | `13 failed, 16 passed` | all ten production cases, JSON, SetEngine, message |
| S2 | oracle twin a no-op | RED | `10 failed, 19 passed` | all ten oracle cases |
| S3 | production drops the userset-restriction edge | RED | `3 failed, 26 passed` | B, B2, B3 (production) |
| S4 | production drops the TTU-target edge | RED | `10 failed, 19 passed` | A, D, F, G, H, I, J, JSON, SetEngine, message |
| S5 | production: `and`/`or` under a subtrahend reset to positive | RED | `1 failed, 28 passed` | G |
| S6 | production: odd-negation-count rule instead of any depth | RED | `1 failed, 28 passed` | D |
| S7 | oracle drops the userset-restriction step | RED | `3 failed, 26 passed` | B, B2, B3 (oracle) |
| S8 | oracle drops the TTU-target step | RED | `7 failed, 22 passed` | A, D, F, G, H, I, J (oracle) |
| S9 | oracle path closure stops after one join | RED | `1 failed, 28 passed` | J (oracle) |
| S10 | production cycle search follows only negative steps | RED | `7 failed, 22 passed` | B, B3, F, H, I, J, message |

M0 attributed exactly the accept side, so the harness can see a pass turn red. S5, S6 and
S9 each have ONE witness. A future case that changes any of G, D or J needs a replacement
before it lands.
