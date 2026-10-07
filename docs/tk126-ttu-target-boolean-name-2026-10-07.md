# `TK126` — a TTU target that shares its NAME with a boolean relation: the measured scout

**ACTIVE-PLAN, opened 2026-10-07 — the body is provenance, not a living status.** Scout-only
map for task row `TK126` (graph index refuses `x from parent` when `x` names a boolean
relation on ANY type; variant D crashes both backends with an internal `ValueError`).
Produced by one scouting agent on 2026-10-07; no source, test, Lean or task file was edited.
Live state is the task row (`python scripts/task.py show TK126`) — never this file.
Corrections append **dated at the top**, never edited into the body. Freeze it when `TK126`
closes.

Provenance labels used on every claim:
- **READ** — first-hand read of the cited `file::symbol` on 2026-10-07.
- **PROBE** — a script under `.scratch/tk126-scout/` was run on 2026-10-07; its literal
  output is quoted (the script itself is gitignored; its body is quoted where load-bearing).
- **REASONED** — inference from READ/PROBE facts, not executed.
- **UNVERIFIED** — stated by someone else and not re-checked here.

Line numbers are as of 2026-10-07 and will rot; the `file::symbol` is the anchor.

## Corrections

- **2026-10-07 (same session, after sec 4.3 was written):** 4.3's UNVERIFIED "whether `statement_pin.py` pins docstrings" is RESOLVED by READ: `formal/conformance/statement_pin.py::strip_comments` strips comments before statements and definitions are pinned, so the docstring edits design (a) needs move no pin (sec 5 (a) item 5).

## 0. The variants (from `docs/pypi-trial-0.0.2-2026-10-07.md` sec 1 B1)

The trial doc prints the schema for variant B only, and describes C and D in prose; the
trial's probe `p15` is not on disk any more (`.scratch/` holds no trial directory, READ
2026-10-07). The schemas used below are therefore reconstructions (REASONED from the
prose), stated exactly so the next session does not have to guess:

- **B** — containing type defines the boolean `viewer`; the TTU reaches `folder#viewer`
  (plain):

  ```
  type user
  type folder
    relations
      define viewer: [user]
  type doc
    relations
      define parent: [folder]
      define banned: [user]
      define reader: [user] or viewer from parent
      define viewer: reader but not banned
  ```
- **C** — an UNRELATED third type defines a boolean `viewer`; `doc` has no boolean at all:

  ```
  type user
  type folder
    relations
      define viewer: [user]
  type doc
    relations
      define parent: [folder]
      define reader: [user] or viewer from parent
  type report
    relations
      define banned: [user]
      define viewer: [user] but not banned
  ```
- **D** — the TTU is INSIDE the boolean relation and names its own relation:
  `define viewer: ([user] or viewer from parent) but not banned` on `doc`, with
  `parent: [folder]` and `folder#viewer: [user]`.

## 1. Reproduction, both backends (Q1)

**PROBE `p1_repro.py`** (2026-10-07, `PYTHONPATH=src`, env `graph-reachability-zanzibar-index`).
For each schema it calls `zanzibar.schema.parse_openfga_schema` (the graph compile),
`zanzibar.setengine.SetEngine(session, 's', schema)` and
`zanzibar.connectedstore.store.ConnectedStore(session, 'cs', schema=schema)`; on a
SetEngine that constructs it writes `folder:f1#viewer@user:u1` and `doc:d1#parent@folder:f1`
and checks. Literal output (rc=0):

```
=== B
  parse_openfga_schema: RAISES zanzibar.schema.errors.UnsupportedByGraphIndex: relation doc#reader: TTU 'viewer' from 'parent' targets the derived relation 'viewer', but the containing relation is not itself boolean-tainted, so it compiles to a plain rewrite rule that would carry derived state on its subject predicate (I5 exclusivity). Reached when the tupleset contributes no member type bearing the tainted target -- an undeclared tupleset relation being the usual cause (decision-15 family)
  SetEngine: OK
    SetEngine check(user:u1 reader doc:d1) = True
  ConnectedStore: RAISES zanzibar.schema.errors.UnsupportedByGraphIndex: <same message>
=== C
  parse_openfga_schema: RAISES zanzibar.schema.errors.UnsupportedByGraphIndex: <same message as B>
  SetEngine: OK
    SetEngine check(user:u1 reader doc:d1) = True
  ConnectedStore: RAISES zanzibar.schema.errors.UnsupportedByGraphIndex: <same message as B>
=== D
  parse_openfga_schema: RAISES builtins.ValueError: Rule then-pattern carries a derived subject predicate: Rule(if_pattern=RelationalTriplePattern(subject_predicate=None, subject_type=None, subject_name=None, relation='parent', object_type='doc', object_name=None, match_wildcards=True, object_match_wildcards=None), then_pattern=RelationalTriplePattern(subject_predicate='viewer', subject_type=None, subject_name=None, relation='viewer.1', object_type='doc', object_name=None, match_wildcards=True, object_match_wildcards=None))
  SetEngine: RAISES builtins.ValueError: <same message>
  ConnectedStore: RAISES builtins.ValueError: <same message>
=== B_renamed      (B with doc#viewer renamed can_view)
  parse_openfga_schema: OK
  SetEngine: OK
    SetEngine check(user:u1 reader doc:d1) = True
  ConnectedStore: OK
=== D_renamed      (D with folder#viewer renamed fviewer)
  parse_openfga_schema: OK
  SetEngine: OK
  [the probe's follow-up write to folder#viewer was refused: probe artifact, the relation was renamed]
  ConnectedStore: OK
```

(`<same message>` elisions are mine; the full lines were byte-identical in the raw output.)

Findings:
- **1a (PROBE).** B and C: graph refuses with `UnsupportedByGraphIndex` from
  `src/zanzibar/schema/compiler.py::_validate_ttu_tuplesets`; the set engine serves. C has
  NO boolean relation on `doc` or `folder` at all — the only boolean is on the unrelated
  `report` type — and is still refused. The trial doc's B1 claim is CONFIRMED first-hand.
- **1b (PROBE).** D: all three entry points raise the same bare `ValueError` from
  `src/zanzibar/schema/boolean.py::compile_boolean_schema` (the I5 exclusivity loop, the
  `then-pattern carries a derived subject predicate` raise; line ~727 on 2026-10-07).
- **1c (READ, `src/zanzibar/setengine/engine.py::SetEngine.__init__`, lines ~359-381
  2026-10-07).** The set engine's D failure is NOT a set-engine evaluation refusal. The
  set engine calls `compile_ruleset` itself (to mirror the graph's raw-write cycle
  rejection), swallows only `UnsupportedByGraphIndex` / `CyclicDerivedDependency` (degrading
  to ruleset-less), and deliberately lets any other `ValueError` surface ("a regression that
  must surface (review 3)"). So D fails in the set engine only because the GRAPH compiler
  raised the wrong exception class. The trial doc's "AGENT: the set engine refuses with the
  same `ValueError`" is CONFIRMED, and this is the mechanism.
- **1d (PROBE).** Renaming the boolean relation (B) or the TTU target (D) makes every entry
  point construct. The collision is purely one of NAMES.

## 2. Why the graph refuses B/C, and whether the NAME key is load-bearing (Q2)

### 2.1 The two name-keyed checks (READ)

There are exactly **two** raising compile-time checks that compare a TTU target / rule
subject predicate against derived relations by NAME across all types (grep
`for (_t, r)` / `derived_predicate` over `src/`, 2026-10-07; a third name-keyed site is the
non-raising report, sec 4):

1. `src/zanzibar/schema/compiler.py::_validate_ttu_tuplesets` (lines ~175-198 2026-10-07):
   `derived_predicate_names = {r for (_t, r) in tainted}`; for every TTU inside an UNTAINTED
   relation, `if e.target_rel in derived_predicate_names: raise UnsupportedByGraphIndex`.
   This is what B and C hit. Its own comment says it exists only to pre-empt check 2 with a
   friendlier exception class, and names the two reachable causes: an undeclared tupleset
   (refused at parse since `ASK-1`) and "a member type whose own `target_rel` is untainted
   while another type's is tainted (the exclusivity check compares NAMES, type-agnostically,
   so it fires there too)" -- i.e. B/C exactly. So the B/C refusal was a KNOWN, deliberately
   accepted coarseness, not an oversight; the message's "undeclared tupleset relation being
   the usual cause" is stale (that cause cannot come from a checked parse any more).
2. `src/zanzibar/schema/boolean.py::compile_boolean_schema`, the "Exclusivity, compile-time
   third (boolean spec §3.3)" loop (lines ~708-729 2026-10-07):
   `derived_predicates = {r for (_t, r) in derived}`; for every emitted `Rule`, `if sp in
   derived_predicates: raise ValueError('Rule then-pattern carries a derived subject
   predicate')`. This is what D hits: D's TTU arm `viewer from parent` is a PURE leaf
   (`folder#viewer` is untainted), so the leaf emitter produces a leaf rewrite `Rule` whose
   then-pattern carries `subject_predicate='viewer'` (PROBE 1, the dumped Rule:
   `relation='viewer.1'`). Check 1 skips it because the CONTAINING relation `doc#viewer` is
   tainted (`if (object_type, relation) in tainted: continue`), so nothing converts it to
   `UnsupportedByGraphIndex` first.

### 2.2 The rule machinery is NOT name-keyed on the subject TYPE it produces (READ)

- `src/zanzibar/schema/rules.py::_rewrite_rule`, TTU branch: if-pattern
  `(relation=tupleset_rel, object_type=<containing type>)`, then-pattern
  `(subject_predicate=target_rel, relation=<target>, object_type=<containing type>)`, no
  `subject_type`. `RelationalTriplePattern.replace` keeps the matched triple's subject
  entity when the pattern does not pin one (`EntityPattern.replace`: `type=self.type or
  entity.type`). So the produced subject node is `(T, name, target_rel)` where `T` is the
  type of the STORED tupleset tuple's subject.
- `src/zanzibar/schema/rules.py::RuleSet.apply`: rules run only on the forward chain of ONE
  admitted raw tuple (seeds -> worklist). A tupleset tuple is admitted only through a
  `Filter` whose pattern pins `subject_type` (`_restriction_pattern`), and since `TK106` a
  tupleset is direct-only, so no Rule rewrites INTO a tupleset relation. Hence `T` ranges
  exactly over the tupleset's declared restriction types (bare or `T:*`).
- Every runtime consumer of "is this derived" is `(type, relation)`-keyed: `WildcardIndex`
  (`src/zanzibar/graphindex/wildcard.py`, `schema_info.derived_families` /
  `leaf_families` membership tests at lines ~111, ~549, ~770-782, ~986-1040 2026-10-07),
  and the I4/I5 invariant checker
  (`src/zanzibar/graphindex/invariants.py::_check_derived_invariants`, `(o.type,
  o.predicate) in derived_families`). Plan TTU nodes carry `parent_types`
  (`boolean.py::_assert_ttu_parent_types_cover_admission` reads them per TTU node).
- **REASONED conclusion.** The only thing check 2 protects is "no plain rewrite produces an
  edge whose SUBJECT node is a derived-public node `(T, n, r)` with `(T, r)` derived". Given
  the first two bullets, the exact condition is type-aware: `(T, sp) in derived` for some
  `T` admission accepts on the rule's if-pattern relation. The name-only version is a sound
  OVER-approximation, nothing more. And for check 1: `compute_taint` already taints any
  relation whose TTU reaches a tainted `(t, target_rel)` for `t in _member_types(tupleset)`
  (`boolean.py::_mentions`, TTU branch), so after `ASK-1` and the RC2 invariant
  (`_assert_ttu_parent_types_cover_admission`: admitted is a subset of `parent_types`) a
  type-aware check 1 can never fire from a checked parse -- it degrades to a defensive
  assertion.

### 2.3 What the graph computes if the checks are relaxed to (type, relation) (PROBE)

**`.scratch/tk126-scout/typeaware_patch.py`** monkeypatches, in-process only:
(1) `compiler._validate_ttu_tuplesets` -> refuse only if the tupleset is undeclared or
`(t, target_rel) in tainted` for some `t in _member_types(tupleset)` (then delegates to the
original with `tainted=frozenset()` so its tupleset-shape checks still run); (2) re-execs
`boolean.compile_boolean_schema` with the one line
`if isinstance(sp, str) and sp in derived_predicates:` replaced by
`if isinstance(sp, str) and any((t, sp) in derived for t in <types>)`, where `<types>` is
the UNION of `_member_types(if.object_type, if.relation)` and the subject types of every
plain `Filter` on that `(object_type, relation)` (two derivations, so the probe is not a
mirror of `_member_types` alone). The replacement anchor is asserted to match exactly once.

**`.scratch/tk126-scout/p2_parity.py`** then drives `tests/parity.py::ParityEngine` (oracle +
both `SetOps` set engines + graph index; paranoia ON; full-grid check parity after EVERY op;
I9 `audit_fixpoint` per op) with random add/remove sequences over every admissible tuple on
names `{a, b}` (wildcard restrictions use `*`), 6 seeds x 40 ops per schema. Extra schemas
beyond B/C/D (all in `.scratch/tk126-scout/schemas.py`):
`B_multi` = B with `parent: [folder, doc]`; `C_cross` = C with `parent: [folder, report]`;
`D_nested` = D but `folder` has `parent: [folder]` and `viewer: [user] or viewer from parent`
(plain recursion on the colliding name); `B_star` = B with `parent: [folder, folder:*]`;
`D_self` = D with `parent: [folder, doc]`.

Unpatched baseline (`p2_parity.py unpatched`, rc=0, literal; the probe cuts each message at
120 chars; the `?` is a cp1252 rendering of `§`):

```
B: UNPATCHED graph compile raises UnsupportedByGraphIndex: relation doc#reader: TTU 'viewer' from 'parent' targets the derived relation 'viewer', but the containing relation is no
C: UNPATCHED graph compile raises UnsupportedByGraphIndex: relation doc#reader: TTU 'viewer' from 'parent' targets the derived relation 'viewer', but the containing relation is no
D: UNPATCHED graph compile raises ValueError: Rule then-pattern carries a derived subject predicate: Rule(if_pattern=RelationalTriplePattern(subject_predicate=None, s
B_multi: UNPATCHED graph compile raises CyclicDerivedDependency: derived relations form a dependency cycle (boolean spec ?1.9 forbids recursion through boolean relations): [('doc', 'rea
C_cross: graph compiles UNPATCHED
D_nested: UNPATCHED graph compile raises UnsupportedByGraphIndex: relation folder#viewer: TTU 'viewer' from 'parent' targets the derived relation 'viewer', but the containing relation is
B_star: UNPATCHED graph compile raises UnsupportedByGraphIndex: relation doc#reader: TTU 'viewer' from 'parent' targets the derived relation 'viewer', but the containing relation is no
D_self: UNPATCHED graph compile raises CyclicDerivedDependency: derived relations form a dependency cycle (boolean spec ?1.9 forbids recursion through boolean relations): [('doc', 'vie
```

Patched (`p2_parity.py patched`, rc=0, literal):

```
mode = patched
B: 4-way OK, 16 candidate tuples, 6 seeds x 40 ops = 240 ops, every op grid-checked (30.9s)
C: 4-way OK, 20 candidate tuples, 6 seeds x 40 ops = 240 ops, every op grid-checked (28.0s)
D: 4-way OK, 16 candidate tuples, 6 seeds x 40 ops = 240 ops, every op grid-checked (33.8s)
B_multi: GRAPH DROPPED (CyclicDerivedDependency: derived relations form a dependency cycle (boolean spec ?1.9 forbids recursion through boolean relations): [('doc', 'reader'), ('doc', )
C_cross: 4-way OK, 24 candidate tuples, 6 seeds x 40 ops = 240 ops, every op grid-checked (59.5s)
D_nested: 4-way OK, 20 candidate tuples, 6 seeds x 40 ops = 240 ops, every op grid-checked (29.2s)
B_star: 4-way OK, 18 candidate tuples, 6 seeds x 40 ops = 240 ops, every op grid-checked (37.2s)
D_self: GRAPH DROPPED (CyclicDerivedDependency: derived relations form a dependency cycle (boolean spec ?1.9 forbids recursion through boolean relations): [('doc', 'viewer')])
patched-check refusals recorded: []
```

Instrument control (`p2_parity.py sabotage`, rc=0, literal): patched checks PLUS the graph's
`Rule`(s) with if-pattern `doc#parent` deleted after compile (graph side only; the set
engines import their own `compile_ruleset` binding and are untouched):

```
mode = sabotage
  [sabotage dropped 1 rule(s)]
  [sabotage dropped 1 rule(s)]
B: RED (AssertionError) check parity broken after add ('...', 'user', 'b', 'viewer', 'folder', 'b'): q=('...', 'user', 'b', 'reader', 'doc', 'a') graph=False oracle=True
  [sabotage dropped 1 rule(s)]
  [sabotage dropped 1 rule(s)]
D: RED (AssertionError) check parity broken after add ('...', 'user', 'b', 'viewer', 'folder', 'b'): q=('...', 'user', 'b', 'viewer', 'doc', 'a') graph=False oracle=True
```

Findings:
- **2a (PROBE).** With the two checks keyed on `(type, relation)` and NOTHING ELSE changed --
  no rule-emission change, no processor change -- B, C, D, `D_nested`, `B_star` and `C_cross`
  all run 4-way in lockstep with the oracle and both set engines, paranoia + I9 green on every
  op (1,440 grid-checked ops across the six). The instrument goes red within one seed when
  the TTU rule is removed, so it was live on exactly these schemas.
- **2b (PROBE + REASONED).** Rule emission does NOT need to become type-aware. The rule's
  produced subject type is already pinned by admission (2.2), so the worry "a type-aware
  check is unsound unless emission becomes type-aware too" does not materialise.
  `patched-check refusals recorded: []`: the type-aware check 1 never fired on any of these,
  consistent with 2.2's argument that it is vacuous after a checked parse.
- **2c (PROBE).** `B_multi` / `D_self` (a parent of the type that owns the boolean `viewer`)
  are refused as `CyclicDerivedDependency` both before and after the patch. That is a
  genuine, separately documented scope limit (recursion through a boolean relation, boolean
  spec §1.9; the `REFUSED SHAPE` above the raise in `boolean.py::_stratify`), NOT `TK126`.
  The set engine serves them (ruleset-less by design). Do not fold it into this item.
- **2d (UNVERIFIED).** The probe did not exercise the `ConnectedStore` async path,
  `build_index` / `src/zanzibar/graphindex/bulk_build.py` / `bulk_backfill.py` (offline
  bootstrap), or the PostgreSQL leg. Those were not read first-hand for name-keyed logic; a
  fix must put these schemas through a differential that covers `build_index` (bulk and
  non-bulk) and `ConnectedStore` before it is believed.

- **2e (PROBE; narrows 2d).** `.scratch/tk126-scout/p3_paths.py`, type-aware patch installed:
  per schema, 4 seeds x 40 random add/remove ops written to FOUR construction paths at once
  -- `ConnectedStore(sync=True)`, `ConnectedStore(sync=False)` + `catch_up()`, and two
  `TupleSource` logs bootstrapped by `build_index(..., bulk=True)` and `bulk=False` -- then
  every path's `check` compared against `tests/oracle.py::Oracle` over a grid of bare and
  userset subjects x every declared `(type, relation)` on names `{a, b}` (+ ghost `zz`
  subjects). Literal output (rc=0; the 20 write refusals, all
  `AdmissionRejected ... would create a cycle in the userset membership topology` on
  `D_nested`'s `folder#parent` self/two-cycles, are elided -- `grep -vc "would create a cycle"`
  over the refusal lines printed `0`):

  ```
  B: 760 grid queries x 4 paths vs oracle, mismatches=0, oracle-True answers=57
  C: 880 grid queries x 4 paths vs oracle, mismatches=0, oracle-True answers=55
  D: 544 grid queries x 4 paths vs oracle, mismatches=0, oracle-True answers=39
  D_nested: 760 grid queries x 4 paths vs oracle, mismatches=0, oracle-True answers=61
  B_star: 760 grid queries x 4 paths vs oracle, mismatches=0, oracle-True answers=83
  C_cross: 880 grid queries x 4 paths vs oracle, mismatches=0, oracle-True answers=83
  ```

  Still NOT exercised: the PostgreSQL leg, lookups (`lookup` / `lookup_reverse` / `expand`),
  and `rebuild_index`. The positive-answer counts show the grid is not vacuous; this probe has
  no sabotage of its own (p2's sabotage controls the ParityEngine instrument only).

- **2f (PROBE).** Lookup surfaces. `.scratch/tk126-scout/p4_lookup.py`, type-aware patch
  installed: `tests/test_lookup_oracle.py::_Gate` (graph REQUIRED present -- the default
  `allow_graph_absent=False` -- plus both set engines; `assert_surfaces` checks `lookup` /
  `lookup_reverse` / `expand` against oracle-composed references) after the initial state
  and every accepted op of a 20-op seeded walk, seeds 1-2. Literal output (rc=0):

  ```
  B: lookup/lookup_reverse/expand vs oracle OK, graph present, 42 surface batteries
  C: lookup/lookup_reverse/expand vs oracle OK, graph present, 42 surface batteries
  D: lookup/lookup_reverse/expand vs oracle OK, graph present, 42 surface batteries
  D_nested: lookup/lookup_reverse/expand vs oracle OK, graph present, 37 surface batteries
  B_star: lookup/lookup_reverse/expand vs oracle OK, graph present, 42 surface batteries
  C_cross: lookup/lookup_reverse/expand vs oracle OK, graph present, 42 surface batteries
  ```

  Remaining NOT exercised by any probe here: the PostgreSQL leg, `rebuild_index`, and the
  hypothesis campaign / `tests/genswarm.py` over generated schemas with colliding names.

## 3. Variant D: where the error comes from, and the proper outcome (Q3)

- **3a (READ + PROBE).** One raise site, reached from both backends: the
  `Rule then-pattern carries a derived subject predicate` `ValueError` in
  `src/zanzibar/schema/boolean.py::compile_boolean_schema`. The set engine has NO
  independent objection to D -- it reaches the raise only because
  `SetEngine.__init__` compiles the graph `RuleSet` for cycle-rejection parity and lets a
  bare `ValueError` surface on purpose (1c). Mechanism (2.1 item 2): D's arm
  `viewer from parent` is pure (`folder#viewer` untainted), so it becomes the closure leaf
  `doc#viewer.1` via a leaf rewrite `Rule` whose then-pattern subject predicate is `viewer`,
  and `viewer` is a derived NAME because `doc#viewer` itself is derived.
- **3b (READ).** The comment above `_validate_ttu_tuplesets` calls this `ValueError` "the
  unreachable last line of defence". It is reachable from a checked parse because the
  friendlier check only inspects UNTAINTED containers, and D's container is tainted. The
  `tests/test_generator_coverage.py::test_no_enumerated_config_is_silently_dropped`
  docstring shows this exact `ValueError` was already reached once before (2026-08-11, the
  undeclared-tupleset family), so "unreachable" has been wrong before.
- **3c (PROBE + REASONED). Proper outcome: SERVED.** Under the type-aware patch D compiles,
  the set engine constructs WITH a ruleset (cycle rejection on), and D runs 4-way clean (2a),
  across all four construction paths (2e) and on the lookup surfaces (2f). The leaf rule
  produces subject nodes `(folder, f, viewer)` only (admission pins `parent: [folder]`),
  and `(folder, viewer)` is not derived, so the I5 property the check exists for holds
  exactly. There is no semantic reason to refuse D, and refusing it would be a narrowing the
  "Who decides" rule forbids. A `REFUSED SHAPE` with WHY/INSTEAD is the right outcome only if
  design (a) is rejected (see sec 5 (b)).
- **3d (PROBE).** The genuinely refusable neighbour is `D_self` (`parent: [folder, doc]`, so
  the TTU reaches the derived `doc#viewer` itself): it is a derived dependency cycle and
  stays `CyclicDerivedDependency` (2c), already a documented `REFUSED SHAPE` in
  `boolean.py::_stratify`. Not this item.

## 4. The Lean side (Q4)

### 4.1 `GraphAdmission` does NOT encode the name check (READ)

`formal/lean/ZanzibarProofs/FullScope.lean::GraphAdmission` has fourteen fields (`wf`,
`nodup`, `strat`, `ttuDirect`, `matchDecl`, `ranked`, `objWild`, `usWild`, `storeValid`,
`ttuNotLeaf`, `directRestrNotLeaf`, `computedRefsNotLeaf`, `noLeafSubjects`,
`keysNonempty`); the decider `GraphIndex/AdmissionDecide.lean::graphAdmissionFieldsB`
lists the same fourteen. None says "a TTU target is not a derived name". `ttuNotLeaf` /
`noLeafSubjects` are about the reserved `.` leaf namespace, not derived names. The Lean
taint (`Spec/Stratify.lean::exprRefs`, `.ttu` case) is TYPE-AWARE: it adds `(pt, tr)` for
each `pt` in `directTypes` of the tupleset's definition, the twin of Python's
`_mentions` / `_member_types`. So **B and C satisfy `GraphAdmission`** (REASONED from the
field list; not run through `zcli`).

### 4.2 The name check lives in Lean in TWO places (READ)

1. **`W4Fragment.term`** (`FullScope.lean::W4Fragment`, field `term : ∀ dt R, isDerived S
   (dt, R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R`), with
   `GraphIndex/ReconcileCorrect.lean::NoTtuTarget S R := ∀ r ∈ schemaRewrites S, ∀ tr,
   r.kind = RuleKind.ttu tr → tr ≠ R` -- NAME-keyed. It is in every headline theorem's
   premise (`formal/headline_statements.txt`: `graph_correct`, `backend_equivalence`,
   `exclusion_effective`, `no_ghost_grant`, ... all take `hF : W4Fragment S T`; and
   `runCascade2_no_abort` / `cascade2_drains` take an `hterm` of the same shape directly),
   and `NoTtuTarget`'s text is pinned in `formal/headline_definitions.txt`
   (`def:Zanzibar.NoTtuTarget`). The proofs track the subject PREDICATE NAME only
   (`ReconcileCorrect.lean`, the "subject-predicate chain, generic in the predicate"
   section: *"track exactly one scalar -- the subject's PREDICATE NAME"*). Measured
   2026-10-07: `NoTtuTarget` occurs on 211 lines across 24 `.lean` files.
   **Consequence: B and C, once served, are OUTSIDE `W4Fragment` (field `term`), i.e.
   served-but-unproved**, exactly like D, which is already outside via
   `computedOrDirect` (a `.ttu` inside a derived def). `src/zanzibar/schema/reports.py::
   w4_fragment_report` mirrors `term` name-keyed (`derived_names = {rel for (_t, rel) in
   tainted}`) and is differential-pinned to Lean, so it will report this truthfully with no
   change. Nothing about the headline theorems becomes false; their scope simply does not
   grow.
2. **`GraphIndex/Leaf.lean::isPure`'s `.ttu` case uses `derivedAnywhere S tgt`**
   (`S.keys.any (fun k => k.2 == R && isDerived S k)`), a type-agnostic NAME test, where
   Python's `boolean.py::_is_pure` asks over `_member_types(tupleset)`. The `Leaf.lean`
   section header and `formal/CORRESPONDENCE.md`'s `isPure` row both justify the deviation
   with exactly the Python refusal `TK126` would remove: *"on exactly that shape
   `compile_ruleset`'s exclusivity pass refuses to compile at all ... So on the domain of
   schemas Python compiles, `derivedAnywhere` **is** the `parent_types` test for this
   purpose."* `GraphIndex/LeafRules.lean` carries a decide-pinned witness `SlXt` (the
   cross-type drop) described as "a MODEL-level probe and not a corpus schema" because
   Python refuses it. Both `derivedAnywhere` and `isPure` are pinned in
   `formal/headline_definitions.txt`. Uses: 51 lines (`LeafRules.lean` 41, `CascadeStable.lean`
   6, `Leaf.lean` 4; measured 2026-10-07).
   **REASONED: this deviation is unobservable inside `W4Fragment`.** `isPure`'s `.ttu` case
   is only evaluated on a derived def's subtree, and `W4Fragment.computedOrDirect` bans
   `.ttu` in derived defs, so on every input of the headline theorems the branch is dead.
   But the CORRESPONDENCE claim ("backed by a Python refusal") becomes FALSE the moment D is
   served, and `CLAUDE.md` / `CORRESPONDENCE.md` §8 forbid leaving that unrecorded.

### 4.3 Which pins change under each design (READ; counts as of 2026-10-07)

Python-side pins that hard-code today's refusal:
- `formal/conformance/w4_scope_probes.py::PYTHON_OUTCOME["term.NoTtuTarget/mixed-member-types"]
  = "RAISED"` -- the probe IS variant C's shape (`member` derived on `org`, plain on `team`,
  `parent: [team]`). Enforced by
  `formal/conformance/test_conformance_fragment.py::test_scope_probe_python_outcome_still_holds`,
  whose failure message says "Re-adjudicate test_w4fragment_scope_pin.py's row". Under
  design (a) it flips to ADMITTED. Its `expected_failures = ("term",)` does NOT change (Lean's
  `term` is name-keyed), so the Lean differential (D) stays green.
- `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE["term"]` -- MIXED; its
  `note` says the LOUD sub-case is "an undeclared tupleset or mixed member types (both
  probe-confirmed RAISED)". Under (a) the undeclared-tupleset corner is still RAISED (at
  parse, ASK-1) and the `NoStoreSubjectR` half is ADMITTED, so the row stays MIXED; the note
  and the module docstring's quoted 2026-08-31 probe line need a DATED update, not an edit.
- `tests/test_tk116_oracle_only_setengine.py::WITNESSES`, family
  `ttu-target-name-is-derived-elsewhere` (message `'targets the derived relation'`), and
  `::test_every_graph_refusal_site_has_a_witness` (zero-headroom census of
  `raise UnsupportedByGraphIndex(` / `raise CyclicDerivedDependency(` sites across
  `src/zanzibar/schema/`). Under (a): if `_validate_ttu_tuplesets`' first loop is kept as a
  type-aware defensive raise, the witness moves to `UNREACHABLE` with its reason; if the loop
  is deleted, the witness is retired with it. Either keeps the census exact.
- `tests/test_refused_shape_comments.py::MIN_HEADERS` (`LIB: 37`) /
  `MIN_IN_SCOPE_RAISES` (`LIB: 25`), zero headroom: any `REFUSED SHAPE` block or in-scope
  raise added or removed moves these by exactly that many.
- `tests/test_generator_coverage.py`, `tests/genswarm.py`, `tests/test_pure_union_ttu.py`,
  `tests/test_boolean_compile.py`, `formal/conformance/test_conformance_nary_strata.py`,
  `formal/conformance/graphadmission_scope_probes.py` mention `_validate_ttu_tuplesets` in
  prose/history only (grep hits read 2026-10-07); none asserts the name-collision refusal.
  `genswarm.REJECTION_WITNESSES` has no name-collision family (it was replaced by
  `dangling-reference` at ASK-1).

Lean-side:
- Design (a) WITHOUT a Lean change: no `.lean` definition or statement pin moves. What must
  change is prose: the `Leaf.lean` `derivedAnywhere` section header, the `LeafRules.lean`
  `SlXt` docstring, and `CORRESPONDENCE.md`'s `isPure` row, which all assert the Python
  refusal; plus a `CORRESPONDENCE.md` §7 gap entry (out-of-fragment leaf-allocation
  deviation, dead inside `W4Fragment` per 4.2 item 2). UNVERIFIED: whether
  `statement_pin.py` pins docstrings (the `headline_definitions.txt` rows read 2026-10-07
  record `def` text only, e.g. `def:Zanzibar.derivedAnywhere [def] def derivedAnywhere ...`).
- Design (a) WITH the faithful model: change `Leaf.lean::isPure`'s `.ttu` case to the
  parent-types test (`directTypes` of the tupleset's def, as `Stratify.lean::exprRefs`
  already computes), regenerate the two `headline_definitions.txt` rows, and repair the 51
  `derivedAnywhere` use sites (the `SlXt` attack pins invert: with a type-aware test the
  cross-type arm is NOT dropped). Size UNVERIFIED; REASONED to be M because the branch is
  dead inside `W4Fragment`, so headline proofs should only need re-plumbing, not new math.
- Bringing B/C INSIDE the proved scope (making `term` type-aware) is a separate, larger item:
  REASONED that a type-aware `NoTtuTarget` is implied by `GraphAdmission.matchDecl` (the
  tupleset is declared) plus the type-aware taint fixpoint (an untainted owner cannot reach a
  derived `(pt, tr)`), so the field might even become derivable -- but the chain that
  consumes it is stated over predicate NAMES on 211 lines / 24 files, so it means re-proving
  the subject-predicate chain over `(type, predicate)`. UNVERIFIED size; REASONED XL. Not
  needed for equivalence; it only grows the proved scope.

## 5. Candidate designs (Q5)

### (a) Key both checks on `(type, relation)`; serve B, C and D. Rule emission unchanged.

- **Soundness vs the oracle (REASONED + PROBE).** The checks exist to keep a plain rewrite
  from producing an edge whose SUBJECT is a derived-public node (I5). A TTU rule's produced
  subject type is the stored tupleset subject's type, which admission pins to the tupleset's
  declared restriction types (2.2), and every runtime "is it derived" test is already
  `(type, relation)`-keyed. So testing `(T, sp) ∈ derived` over the admitted `T` is the exact
  condition and the name test an over-approximation. PROBE: 1,440 ParityEngine ops (2a), four
  construction paths (2e) and the lookup surfaces (2f) agree with the oracle on B, C, D and
  three neighbours, with a sabotage control proving the instrument live.
- **Files / symbols (READ, 2026-10-07):**
  1. `src/zanzibar/schema/boolean.py::compile_boolean_schema`, the exclusivity loop: replace
     `sp in derived_predicates` by "`(t, sp) ∈ derived` for some `t` the rule can produce",
     `t` read off the emitted plain `Filter`s on `(if.object_type, if.relation)` (the
     independent derivation `_assert_ttu_parent_types_cover_admission` already uses, so the
     guard is not a mirror of `_member_types`), unioned with `_member_types` (over-approximation
     is safe here). If that set is EMPTY (hand-built AST, undeclared tupleset) keep the
     current name test, so the defensive behaviour does not weaken.
  2. `src/zanzibar/schema/compiler.py::_validate_ttu_tuplesets`, first loop: same
     type-aware condition (or undeclared tupleset); rewrite the message (drop the stale
     "undeclared tupleset relation being the usual cause") and the `REFUSED SHAPE` block's
     WHY / INSTEAD (the current INSTEAD, "rename the boolean relation ... EVERY tainted
     relation sharing the name needs a new name", becomes false). REASONED: from a checked
     parse this raise becomes unreachable (2.2), so it belongs in
     `tests/test_tk116_oracle_only_setengine.py::UNREACHABLE` with that reason.
  3. Pins (4.3): `w4_scope_probes.py::PYTHON_OUTCOME` (1 value), the `term` row note in
     `test_w4fragment_scope_pin.py` (dated), TK116 `WITNESSES` -> `UNREACHABLE` (1 entry),
     `test_refused_shape_comments.py` floors only if a block is added/removed.
  4. A new pin module, e.g. `tests/test_tk126_ttu_target_name_collision.py`: B, C, D,
     `D_nested`, `B_star`, `C_cross` through `ParityEngine` with `assert pe.graph is not None`,
     plus `_Gate` lookups and `build_index(bulk=True/False)`; sabotage = revert each check to
     its name test (the constructor raises -> red), recorded literally per
     `docs/sabotage-procedure.md`.
  5. Docs: `docs/spec-deviations.md` dated entry; `formal/CORRESPONDENCE.md` `isPure` row +
     a §7 gap entry; dated notes on the `Leaf.lean` `derivedAnywhere` header and the
     `LeafRules.lean` `SlXt` docstring (READ 2026-10-07:
     `formal/conformance/statement_pin.py::strip_comments` strips comments before pinning, so
     docstring edits move no statement/definition pin); `CHANGELOG.md` for 0.0.3.
- **Lean / pin impact.** No `.lean` definition or statement changes are REQUIRED (4.3).
  B/C become served-but-outside-`W4Fragment` (`term`), D stays outside (`computedOrDirect`);
  `w4_fragment_report` already says so, with no code change.
- **Size (REASONED).** Python ~40 changed lines in two functions, one new test module,
  three pin edits, four doc edits: **M**. Optional faithful-`isPure` Lean change: M
  (UNVERIFIED). `term` widening: XL, separate.
- **Risks.**
  - **R1 (biggest): the safety net goes quiet.** After (a), BOTH guards are unreachable from
    a checked parse (2.2: `compute_taint` already taints any container whose TTU reaches a
    derived `(t, target)`). A later regression in `_member_types` / `compute_taint` (the RC1
    class) would then not be caught at compile time by these guards; only
    `_assert_ttu_parent_types_cover_admission` (admission-vs-`parent_types`) and the
    differentials remain. Mitigation: read admitted types off the Filters (independent
    derivation, as above), and pin the guard with a hand-built-AST test, because deleting it
    is a sabotage NO checked-parse test can see.
  - **R2: served-but-unproved.** B/C/D sit outside `W4Fragment`; their equivalence evidence
    is differential only (matrix, hypothesis, ParityEngine), as for every other
    out-of-fragment shape the repo already serves.
  - **R3: Lean prose drift.** `Leaf.lean` / `LeafRules.lean` / `CORRESPONDENCE.md` claim the
    `derivedAnywhere` deviation is "backed by a Python refusal"; (a) removes the backing.
    Must be re-recorded in the same commit (CORRESPONDENCE §8) -- dead inside `W4Fragment`
    per 4.2 item 2, but false as written.
  - **R4: not yet probed** -- PostgreSQL leg, `rebuild_index`, generated schemas (2f).

### (b) Keep the refusal; make it accurate and name the workaround.

- B/C: rewrite the `_validate_ttu_tuplesets` message to say what is true ("the graph index
  compares a TTU target to boolean relations by NAME across every type; `viewer` is boolean
  on `doc`") and name the rename workaround. D: move the case out of the bare `ValueError`
  into a `_reject_*` function raising `UnsupportedByGraphIndex` with a `REFUSED SHAPE` /
  WHY / INSTEAD block, so `SetEngine.__init__` degrades to ruleset-less and SERVES D (3-way,
  oracle-checked by TK116's machinery) instead of crashing.
- **"In both parsers" does NOT apply (REASONED).** The `REFUSED SHAPE` rule's "both parsers"
  is for parse refusals mirrored by the oracle twin. This is a GRAPH-ONLY scope refusal
  (decision-15 family): putting it in `tests/oracle.py` too would make the oracle and set
  engine refuse a schema that is semantically fine and that OpenFGA accepts -- a narrowing.
- Soundness: trivially sound (refuses more). Files: `compiler.py`, `boolean.py`, TK116
  `WITNESSES` (+1 witness for D), `MIN_HEADERS`/`MIN_IN_SCOPE_RAISES` floors, messages. Lean:
  none; the `derivedAnywhere` backing claim stays true. Size: **S**.
- Risk: it ships a permanent scope gap on the ordinary OpenFGA idiom (every type defining its
  own `viewer`), and under "Who decides" the graph refusing what the set engine serves is a
  gap to close, not a design. A rename also changes the public relation name an application
  queries.

### (c) Considered and rejected: internal name-mangling of derived predicates.

Compile every derived relation under an internal, type-qualified predicate (e.g.
`doc/viewer`) so names cannot collide. It touches every derived-family key, the residue,
the outbox, `schema_info`, the Lean leaf namespace and the snapshot goldens -- XL -- to fix
a problem that (a)'s PROBE shows does not exist at runtime. Rejected.

### (a+) = (a) plus the faithful Lean model (the recommended shape, below).

(a), and in a follow-up row make `Leaf.lean::isPure`'s `.ttu` case use the tupleset's
parent types, so the model again describes the shipped compiler with no recorded gap.

## 6. RECOMMENDATION (REASONED, 2026-10-07)

**Take design (a) now; record the Lean prose and the §7 gap in the same commit; file the
faithful-`isPure` model change as its own row (a+); do not widen `term` under this item.**

Weighed against `CLAUDE.md` "Who decides": the goal is that the graph index gives the
set engine's answers. B and C are a scope gap on a mainstream OpenFGA idiom, and D is a
crash in BOTH backends that the set engine has no semantic reason for. The PROBE evidence
is that the name test guards nothing the `(type, relation)` test does not: with only the
two compile-time checks changed, the graph matches the oracle and both set engines on every
probed path. (b) leaves the gap and only rewords it, and the rule says narrowing is not the
fix. (c) is cost with no benefit.

**Single biggest risk: R1.** After the fix both guards are unreachable from any checked
parse, so a future taint or `_member_types` regression (the RC1 class) would no longer be
stopped at compile time by them, and deleting a guard is a sabotage no schema-text test can
see. The guard must read admitted types from the emitted Filters (an independent
derivation), and it must be pinned by a hand-built-AST test.

### Ordered next steps (for the session that implements)

1. Write the new pin module first (step 4 of (a)) and watch it go RED on today's tree
   (B/C `UnsupportedByGraphIndex`, D `ValueError`). That is the before-state evidence.
2. Change `boolean.py::compile_boolean_schema` (type-aware I5 subject check, Filter-derived
   types, name-test fallback on an empty set), then `compiler.py::_validate_ttu_tuplesets`
   (type-aware + new message + new `REFUSED SHAPE` WHY/INSTEAD).
3. Flip `PYTHON_OUTCOME["term.NoTtuTarget/mixed-member-types"]` to `ADMITTED`; add a dated
   note to the `term` row; move the TK116 witness to `UNREACHABLE`; add the
   hand-built-AST guard test and its sabotage.
4. Record the Lean prose (dated notes on `Leaf.lean`, `LeafRules.lean` `SlXt`,
   `CORRESPONDENCE.md` `isPure` row + §7 entry) and `docs/spec-deviations.md`.
5. Full gate (all ten phases) plus a fuzz sweep (this is an admission change), then
   `ZANZIBAR_TEST_DSN` for the PostgreSQL leg (R4).
6. File the a+ row (faithful `isPure`) and, as SOMEDAY, the type-aware `term` widening.

Scratch artefacts (gitignored; their outputs are quoted above in full where load-bearing):
`.scratch/tk126-scout/{schemas.py, typeaware_patch.py, p1_repro.py, p2_parity.py,
p3_paths.py, p4_lookup.py}` and their `.out` files.
