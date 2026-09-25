# `TK104` — `GraphAdmission` sized per field: LOUD 10, MIXED 2, SILENT 2

**FROZEN 2026-09-25, at `TK104`'s close — provenance, not a living document.** Status lines
below are as-of-then and several may now be false; live state: `HANDOFF.md` + the session
ledger. Corrections are appended dated at the top, never edited into the body. (Was
ACTIVE-PLAN from 2026-09-24, `docs/README.md` §3.) Live state is `python scripts/task.py show TK104`, never this file. Every figure below
was measured on `2026-09-24` against HEAD `b08a262` plus this session's diff.

Provenance labels: **READ** (verified first-hand, `file::symbol`), **REASONED**, **PROBED**
(a script was run, literal output quoted), **UNVERIFIED**. No subagent was used. Every READ
below was read by the session.

## Progress, 2026-09-25: steps 1, 2 and 3 of § 3 LANDED, and `TK104` closes (appended; the body below is as-written)

Measured `2026-09-25` against HEAD `cc3b9f5` plus this session's diff. No subagent was used.

**Step 1: `GraphAdmission` is decided (READ, built).**
`formal/lean/ZanzibarProofs/GraphIndex/AdmissionDecide.lean::graphAdmissionB_iff` is exact in
both directions. The file also has the `Decidable` instance, the per-field report
`graphAdmissionFieldsB`, and `headlinePremiseB_iff`, which decides the WHOLE premise
`GraphAdmission S T ∧ W4Fragment S T`.

- **`RewriteRanked`** went as § 3 sketched, with one change of form. The candidate is
  `rkF rules n k`, the longest rule-walk of length `≤ n` ending at `k`, taken at
  `n = |keys| + 1`. `rankCheck_rkF_iff` decides the existential for ANY rule list and
  bound. Completeness uses three lemmas: `rkF_le_rank`, `rkF_mono`, and `rkF_jump` (a value
  changes at layer `n+1` only by becoming `n+1`). The bound is checked only at out-keys, and
  `rkF_eq_zero_or_outKey` covers every other key.
- **The executable form is a table, not the closure.** `rkL` is let-bound per layer, and
  `lookD_rkL` proves it equal to `rkF` pointwise. As a closure, `rkF` costs `|rules|^n`.
- **The other thirteen fields.**
  - Six are `decide` against their own statement.
  - `wf` uses `toList.contains`, because `String.contains` does not reduce under `decide`.
    The first build's `decide` pins all failed on exactly this.
  - `ttuNotLeaf` reads `ttuTargets`.
  - `storeValid` matches on `S.lookup` and picks the disjunct by `isDerived`. It is exact with
    no `NodupKeys` premise, for `FragmentDecide.lean::lookupAll`'s reason.
- **Pins** (module `AdmissionDecideWitness`, all `decide`):
  - Seven positives: the six hand-proved admission witnesses plus `chainS`.
  - Fourteen field controls plus four extras (`refutes_matchDecl_ttu`, `refutes_ranked_self`,
    `refutes_storeValid_derived`, `outside_S3_by_decide`). Each pins its EXACT failure list,
    and each is that field alone except `ttuNotLeaf`. `ttuNotLeaf` cannot fail alone, because
    `CascadeStable.lean::ttuTargetsSat_notLeafName_of_noLeafSubjects` derives it.
  - `rank_tight`: a walk as long as the bound allows.
  - `rank_needs_iteration`: the all-zero rank is refuted at `chainS`.
  - `premise_reads_both_halves`: `S6` is admitted but outside `W4Fragment`.
- **A finding the pins made visible: `chainS` is the first admitted witness in the tree
  with a non-zero rank** (READ). All six earlier hand proofs discharge `ranked` with
  `⟨fun _ => 0, …⟩`. So `RewriteRanked`'s content had never been exercised at a witness.

**Step 2: zcli reports both halves (built, gated).**
- `Cli.lean::fragmentJson` emits `"inPremise"` and `"admission": {"admitted", "fields",
  "failures"}`.
- `runner.py::run_fragment` asserts both key sets exactly. It also checks each verdict
  against its failures, and `inPremise` against the two verdicts.
- `test_conformance_fragment.py` gains sections (A') and (G)-(J):
  - **(A')** every `_THEOREM_BACKED` corpus meets the whole premise by Lean.
  - **(G)** Lean's admission verdict on every curated corpus equals a table PREDICTED from
    § 0 before zcli could be asked: three corpora, `storeValid` ×2 and `ttuDirect` ×1, all
    MIXED silent halves.
  - **(H)** on every corpus, an admission failure implies that its `W4Fragment` shadow also
    fails. This is § 0's SHADOWED claim, machine-checked.
  - **(I)** each sizing probe fails the field its label names, BY LEAN. § 0 had this as
    REASONED; it is now checked.
  - **(J)** the silent-field report equals Lean on `matchDecl` / `ranked`, over 36 corpora
    plus the 11 schema probes the production parser accepts (47 inputs).

**Step 3: the operator report (built, gated).**
- `zanzibar_utils_v1.py::graph_admission_report` covers `matchDecl` and `ranked` only. It is
  pure and non-raising, and its cycle search is iterative.
- `GRAPH_ADMISSION_REPORTED_FIELDS` is its field list. The two SILENT rows of
  `GRAPHADMISSION_SCOPE` now carry `reported_by`, checked to resolve and to emit the field.
- `graphadmission_scope_probes.py::silent_admission_failures` DELEGATES to it, and the hand
  mirror is deleted. Before deletion, the hand mirror and the new report agreed on all 47
  inputs (PROBED).
- `tests/test_graph_admission_report.py` pins what (J) cannot see: input forms, derived defs
  contributing no rule, and a 4000-deep chain that a recursive search would die on.

**Why the report covers two fields and not fourteen (the session's call, `CLAUDE.md` "Who
decides").** A Python mirror of the ten LOUD fields would re-derive refusals that Python
already enforces, and each such field would need its own differential to stay honest. The two
MIXED silent halves are already reported through `w4_fragment_report` (shadow claim (H)).
The two SILENT fields are the whole gap § 0 found, so the report is sized to the gap.

**Still not taken: refusing dangling references in Python.** Filed as `ASK-1` (LATER): it
changes what the product accepts, so it is the user's call (§ 3).

**Two findings made en route (PROBED).**
- `tests/oracle.py::parse_schema_ast` keeps the LAST of two duplicate `define`s without
  complaint, while production refuses them. So the `nodup` probe reaches zcli with one key,
  and Lean rightly admits it. This is pinned as `_ORACLE_COLLAPSES` and filed as `TK105`.
  Two further probes are refused by the oracle's own parser (`_ORACLE_REFUSES`). Both have
  Lean controls.
- Lean's `Json.mkObj` sorts object keys, so zcli's JSON cannot carry field ORDER. (G)
  compares the field SET; order is `graphAdmissionFieldsB`'s. The first run failed 37 tests
  on exactly this.
- (G)'s prediction table matched Lean on the first run that could compare them.

**Sabotage, Lean (`docs/sabotage-procedure.md`).** A 21-mutation sweep of
`AdmissionDecide.lean` with an M0 attribution control. The runner was a throwaway
`.scratch/` script: one byte-exact edit, `lake env lean` on the module, the declarations with
an error listed, then restore. The file was byte-identical afterwards (`cmp`). Literal:

```
BASELINE rc=0 errors=[]
M0 control: refutes_ranked claims ["matchDecl"]: RED rc=1 : refutes_ranked
M1 rankTerm +1 -> +0: RED rc=1 : rkF_jump rankCheck_rkF_iff accepts_chainS premise_chainS rank_viewer_chainS rank_tight refutes_ttuDirect refutes_matchDecl refutes_matchDecl_ttu refutes_ttuNotLeaf refutes_noLeafSubjects
M2 rankedB layer |keys|+1 -> |keys|: RED rc=1 : rankedB_iff
M3 rankedB layer |keys|+1 -> |keys|-1: RED rc=1 : rankedB_iff rank_tight
M4 rankCheck strict < -> <=: RED rc=1 : rankCheck_rkF_iff rank_needs_iteration
M5 rankCheck drops the bound clause: RED rc=1 : rankCheck_rkF_iff
M6 lookD miss -> 1: RED rc=1 : lookD_map lookD_rkL rank_viewer_chainS rank_tight
M7 storeTupleOkB drops the all-bare restriction check: RED rc=1 : storeTupleOkB_iff refutes_storeValid_derived
M8 storeTupleOkB drops the bare-subject check: RED rc=1 : storeTupleOkB_iff
M9 storeTupleOkB untainted branch reads exprDirectsAll: RED rc=1 : storeTupleOkB_iff
M10 storeTupleOkB lookup miss -> true: RED rc=1 : storeTupleOkB_iff refutes_storeValid
M11 admMatchDeclB drops the isDerived conjunct: RED rc=1 : admMatchDeclB_iff
M12 swap the matchDecl / ranked deciders: RED rc=1 : graphAdmissionB_iff rank_tight refutes_matchDecl refutes_matchDecl_ttu refutes_ranked refutes_ranked_self
M13 ttuNotLeaf conjunct -> true: RED rc=1 : graphAdmissionB_iff refutes_ttuNotLeaf
M14 noLeafSubjects conjunct -> ttuNotLeaf's decider: RED rc=1 : graphAdmissionB_iff refutes_noLeafSubjects
M15 wf conjunct -> true: RED rc=1 : graphAdmissionB_iff refutes_wf
M16 headlinePremiseB drops the W4Fragment half: RED rc=1 : headlinePremiseB_iff premise_reads_both_halves
M17 rkL never iterates (prev := layer 0): RED rc=1 : lookD_rkL accepts_chainS premise_chainS rank_viewer_chainS rank_tight refutes_ttuDirect refutes_matchDecl refutes_matchDecl_ttu refutes_ranked refutes_ranked_self refutes_ttuNotLeaf refutes_noLeafSubjects
M18 storeValid conjunct -> true: RED rc=1 : graphAdmissionB_iff refutes_storeValid refutes_storeValid_derived
M19 objWild conjunct -> true: RED rc=1 : graphAdmissionB_iff refutes_objWild
M20 usWild conjunct -> true: RED rc=1 : graphAdmissionB_iff refutes_usWild
RESTORED rc=0 errors=[] identical=True
```

- **Five reds are proof-only: M2, M5, M8, M9, M11.** Each is EQUIVALENT by construction, so
  no pin could see it (REASONED):
  - **M2:** an acyclic walk ending at a match key never reaches length `|keys|`, so layer
    `|keys|` is already stationary there.
  - **M5:** a strictly increasing candidate means the graph is acyclic, and acyclic means the
    bound holds.
  - **M8:** an all-bare restriction list that matches forces a bare subject.
  - **M9:** untainted defs have no `inter` / `excl` nodes.
  - **M11:** referencing a derived relation taints the referrer, so no untainted rule matches
    a derived key.

  The `_iff` reddening is correct in each case: the proof no longer describes the code.
- **Three pins exist BECAUSE of predicted INERT rows, and each then took its mutation:**
  `rank_tight` (M3), `refutes_storeValid_derived` (M7), and `premise_reads_both_halves` (M16).
  All were added before the sweep ran.

**Sabotage, Python.** A mutation sweep of `graph_admission_report` and the new test sections,
with a P0 control. It ran over the three affected modules, `-x`. Literal, valid runs only:

```
BASELINE rc=0 ['403 passed in 10.88s'] failed=[]
P0 control: prediction table drops derived_tupleset_ttu: RED rc=1 ['1 failed, 289 passed in 8.30s'] first-failed=['formal/conformance/test_conformance_fragment.py::test_lean_admission_verdict_matches_the_prediction[TTU_USERSET:derived_tupleset_ttu]']
P1 matchDecl ignores declared-ness: RED rc=1 ['1 failed, 1 passed in 0.46s'] first-failed=['tests/test_graph_admission_report.py::test_known_answers']
P2 matchDecl ignores taint: INERT rc=0 ['403 passed in 9.88s'] first-failed=[]
P3 TTU arm matches its TARGET, not its tupleset: RED rc=1 ['1 failed, 1 passed in 0.54s'] first-failed=['tests/test_graph_admission_report.py::test_known_answers']
BASELINE rc=0 ['403 passed in 9.41s'] failed=[]
P4 cycle search drops self-edges: RED rc=1 ['1 failed, 67 passed in 2.60s'] first-failed=['formal/conformance/test_graphadmission_scope_pin.py::test_silent_field_mirror_known_answers[ranked/computed-self-loop]']
P5 tainted defs contribute rules: RED rc=1 ['1 failed, 70 passed in 2.81s'] first-failed=['formal/conformance/test_graphadmission_scope_pin.py::test_theorem_backed_corpora_pass_the_silent_fields']
P6 recursive cycle search: RED rc=1 ['1 failed, 4 passed in 38.11s'] first-failed=['tests/test_graph_admission_report.py::test_a_long_computed_chain_does_not_recurse']
P7 (H) shadow check disabled: INERT rc=0 ['403 passed in 8.32s'] first-failed=[]
P8 (I) control/violation branch inverted: RED rc=1 ['1 failed, 331 passed in 6.62s'] first-failed=['formal/conformance/test_conformance_fragment.py::test_lean_admission_fails_each_probes_named_field[computedRefsNotLeaf/dotted-computed-ref]']
RESTORED rc=0 ['403 passed in 9.38s']
P7b (H) storeValid's shadow re-pointed at wsBare: RED rc=1 ['1 failed, 301 passed in 6.51s'] first-failed=['formal/conformance/test_conformance_fragment.py::test_no_corpus_is_in_w4fragment_but_outside_admission[SCHEMAS:derived_userset_subject]']
```

- **P2 is INERT for M11's reason** (equivalent by construction), so Python and Lean agree on
  it.
- **P7 is INERT, and the edit could not have moved anything.** It weakens (H)'s assertion,
  but (H)'s claim is TRUE on every corpus, so a weaker check of a true claim stays green. The
  subject sabotage P7b (point `storeValid`'s shadow at the wrong field) is what reddened it.
  So (H) is live.
- **⚠ THE INSTRUMENT FAILED ONCE, and a red baseline caught it.** The first sweep ran under
  an outer `timeout 590` and was killed mid-P5, AFTER it had written the mutated
  `zanzibar_utils_v1.py` and BEFORE its `finally` could restore it. SIGTERM skips `finally`.
  - The session checked for P4's edit (absent) and missed P5's.
  - The next rerun's BASELINE came back `1 failed`, and P5's anchor matched 0 times. That
    rerun is VOID and is not quoted above.
  - The file was diffed against the block's source, one line differed, and it was restored.
    The block is identical to its source again.
  - First, P4's first form (a self-edge skipped inside the search) HUNG rather than passing:
    `rc=143` from the kill. It was re-expressed as "drop self-edges when building the graph".
  - **Carry-forward: never put an outer `timeout` around a mutation runner. Run it in the
    background, and run the baseline FIRST, every time.**

**Floors (`formal/verify.sh`), re-measured 2026-09-25 by `--collect-only`:**
- `MIN_CONF_ALL` 843 → 990, and `MIN_CONF_REST` 708 → 855. All +147 are
  `test_conformance_fragment.py`.
- `MIN_TESTS_ALL` 1279 → 1288. +5 are the new module; +4 are DRIFT (1283 with it ignored).

## § 0 What the row asked, and the answer

`TK104`'s first action was sizing: classify each `FullScope.lean::GraphAdmission` field
LOUD / SILENT / MIXED, as `test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` does for
`W4Fragment`. The `DW-1` plan's claim that `GraphAdmission` is "largely mirrored by Python
compile and write refusals" was UNVERIFIED. The row said to decide on the decider after sizing.

**Answer (PROBED): LOUD 10, MIXED 2, SILENT 2.** The claim is mostly true. Where it is false,
the gap is narrow and has a name:

| field | class | what Python does with a violating input | refusing / admitting site |
|---|---|---|---|
| `wf` | LOUD | `ValueError` ('.' in a declared name) | `zanzibar_utils_v1.py::parse_schema_ast` |
| `nodup` | LOUD | `ValueError` (duplicate relation definition) | `::parse_schema_ast` |
| `strat` | LOUD | `CyclicDerivedDependency` | `::_stratify` |
| `ttuDirect` | MIXED | untainted non-direct tupleset RAISES; a DERIVED tupleset is ADMITTED | `::_validate_ttu_tuplesets` (`ts_key not in tainted`) |
| `matchDecl` | **SILENT** | a dangling computed ref / TTU tupleset is ADMITTED | `::_validate_ast_references` checks the '.' lock only |
| `ranked` | **SILENT** | an untainted computed cycle is ADMITTED | nothing refuses it; `Spec/Stratify.lean` header: "untainted relations may be positively recursive" |
| `objWild` | LOUD | `UnsupportedByGraphIndex` | `::_reject_object_wildcard_scope` (first loop) |
| `usWild` | LOUD | `UnsupportedByGraphIndex`, both disjuncts | `::_build_plan_tree` (a), `::_reject_object_wildcard_scope` (b) |
| `storeValid` | MIXED | an untainted mismatch RAISES `AdmissionRejected`; a derived Direct arm with a userset restriction ADMITS | `::RuleSet.apply`, then `setengine/engine.py::SetEngine._validate` |
| `ttuNotLeaf` | LOUD | `ValueError` (reserved leaf namespace) | `::_validate_ast_references` |
| `directRestrNotLeaf` | LOUD | same | same |
| `computedRefsNotLeaf` | LOUD | same | same |
| `noLeafSubjects` | LOUD | same, derived arms included | same |
| `keysNonempty` | LOUD | `ValueError` (empty name, `TK55`) | `::parse_schema_ast` |

- **The two MIXED rows are SHADOWED (PROBED on the probes, REASONED in general).** Their
  silent halves also fail a `W4Fragment` field, and the production report
  (`zanzibar_utils_v1.py::w4_fragment_report`, differential-pinned to Lean) flags that field:
  - `ttuDirect`: a derived tupleset taints its container (`Spec/Stratify.lean::exprRefs`, the
    `.ttu` case lists `(t, ts)`). The container is then a derived def with a `.ttu` leaf, so
    `computedOrDirect` fails.
  - `storeValid`: a tuple that matches a non-bare restriction on a derived Direct arm means
    the arm is not bare, so `directArmsBare` fails. The subtle probe is a BARE subject written
    beside a `[group#member]` restriction. `StoreValidRulesD` demands an all-bare restriction
    LIST, so even `user:alice` fails the field there.
  So the JOINT premise never silently covers these inputs.
- **The two SILENT rows are the whole unreported surface of the headline premise.** Neither
  is shadowed: an untainted schema passes `W4Fragment` vacuously (`w4Fragment_of_untainted`).
  - `matchDecl` = **dangling references.** `define viewer: [user] or editor` with no `editor`,
    or `define view: viewer from parent` with no `parent`, compiles to 0 strata.
  - `ranked` = **untainted computed cycles.** `a: [user] or b` with `b: [user] or a`, and the
    self-loop `viewer: [user] or viewer`, both compile.
  - TTU recursion (nested folders, `viewer: [user] or viewer from parent`) is NOT excluded
    (PROBED control, REASONED in general). A TTU rule's edge runs `(ot, ts) → (ot, out)`, and
    `ttuDirect` makes every declared tupleset direct-only, so no rule has a tupleset as its
    output and a TTU edge cannot close a cycle.
- **No curated corpus fails either SILENT field (PROBED).** A REASONED Python mirror
  (`graphadmission_scope_probes.py::silent_admission_failures`) was swept over all 36
  corpora: 0 failures. So no `_THEOREM_BACKED` prose argument is refuted.

## § 1 Probe output, literal

The inputs are `formal/conformance/graphadmission_scope_probes.py` (`SCHEMA_PROBES`,
`STORE_PROBES`). The first run used a throwaway script with the same inputs, and two labels
were renamed afterwards (`ttuDirect/...` became `ttuDirect.untainted/...` and
`ttuDirect.derived/...`).

```
wf/dotted-relation-name: RAISED ValueError: relation 'a.b': '.' is reserved for compiled leaf predicates and cannot appear in a declared relation name
nodup/duplicate-define: RAISED ValueError: duplicate relation definition: doc#viewer
strat/derived-cycle: RAISED CyclicDerivedDependency: derived relations form a dependency cycle (boolean spec 1.9 forbids recursion through boolean relations): [('doc', 'a'), ('doc', 'b')]
ttuDirect/untainted-tupleset-computed: RAISED UnsupportedByGraphIndex: relation doc#view: tupleset 'parent' has computed/rewritten arms; Zanzibar tupleset semantics read stored tuples only, and the graph index cannot sepa
ttuDirect/derived-tupleset: ADMITTED (strata=2)
matchDecl/undeclared-computed-ref: ADMITTED (strata=0)
matchDecl/undeclared-tupleset-untainted-target: ADMITTED (strata=0)
ranked/computed-two-cycle: ADMITTED (strata=0)
ranked/computed-self-loop: ADMITTED (strata=0)
ranked/in-scope-control(ttu-recursion): ADMITTED (strata=0)
objWild/object-wildcard-on-derived: RAISED UnsupportedByGraphIndex: object-wildcard shape (doc, view) targets a derived (boolean-tainted) relation; symbolic object state on derived relations needs a subject-keyed resid
usWild.a/wildcard-userset-over-derived: RAISED UnsupportedByGraphIndex: relation doc#viewer: wildcard userset restriction [group:*#member] over the derived relation group#member needs symbolic composition through residues
usWild.b/star-tupleset-through-derived: RAISED UnsupportedByGraphIndex: relation doc#view: star tupleset [folder:*] on 'parent' derives the wildcard userset shape (folder, viewer) over the derived relation folder#viewer, w
ttuNotLeaf/dotted-ttu-target: RAISED ValueError: doc#view: 'viewer.0' is inside the reserved leaf namespace ('.' in referenced relation names)
directRestrNotLeaf/dotted-restriction-predicate: RAISED ValueError: doc#viewer: 'member.0' is inside the reserved leaf namespace ('.' in referenced relation names)
computedRefsNotLeaf/dotted-computed-ref: RAISED ValueError: doc#view: 'viewer.0' is inside the reserved leaf namespace ('.' in referenced relation names)
noLeafSubjects/dotted-ttu-target-in-derived-arm: RAISED ValueError: doc#view: 'viewer.0' is inside the reserved leaf namespace ('.' in referenced relation names)
keysNonempty/empty-relation-name: RAISED ValueError: type 'doc': a declared relation name may not be empty ('define : [user]')
== store side: ConnectedStore.add_tuple | SetEngine.add_tuple ==
storeValid.untainted/userset-subject-on-bare-arm: CS RAISED AdmissionRejected: tuple doc:d1#viewer@group:g1#member matches no declared type restriction for doc#viewer
                                                  SE RAISED AdmissionRejected: tuple doc:d1#viewer@group:g1#member matches no declared type restriction for doc#viewer
storeValid.untainted/write-on-computed-only-relation: CS RAISED AdmissionRejected: tuple doc:d1#view@user:alice#... matches no declared type restriction for doc#view
                                                      SE RAISED AdmissionRejected: (same)
storeValid.untainted/write-on-undeclared-relation: CS RAISED AdmissionRejected: tuple doc:d1#editor@user:alice#... matches no declared type restriction for doc#editor
                                                   SE RAISED AdmissionRejected: (same)
storeValid.derived/userset-subject-on-derived-direct-arm: CS ADMITTED (check=True)   SE ADMITTED (check=True)
storeValid.derived/bare-subject-beside-a-userset-restriction: CS ADMITTED (check=True)   SE ADMITTED (check=True)
storeValid/in-scope-control(bare-on-derived): CS ADMITTED (check=True)   SE ADMITTED (check=True)
== corpus sweep: 36 curated corpora, SILENT-field mirror ==
corpora failing a SILENT GraphAdmission field: 0
== mirror self-check on the schema probes ==
matchDecl/undeclared-computed-ref: ('matchDecl',)
matchDecl/undeclared-tupleset-untainted-target: ('matchDecl',)
ranked/computed-two-cycle: ('ranked',)
ranked/computed-self-loop: ('ranked',)
ranked/in-scope-control(ttu-recursion): ()
```

## § 2 What landed

- `formal/conformance/graphadmission_scope_probes.py`: the fixtures, the `SHADOWED` map and
  the REASONED mirror `silent_admission_failures`.
- `formal/conformance/test_graphadmission_scope_pin.py`: the `W4Fragment` pin's contract,
  applied to `structure GraphAdmission` with the same field parser, plus a mechanical tie
  between classification and evidence:
  - a LOUD row's probes all RAISE, a SILENT row's are all ADMITTED, and a MIXED row has one
    of each;
  - every probe outcome is re-measured (schema side through `parse_openfga_schema`, store side
    through BOTH `ConnectedStore.add_tuple` and `SetEngine.add_tuple`);
  - a MIXED row's `shadowed_by` is checked through `w4_fragment_report`;
  - the mirror has known-answer controls and sweeps every `_THEOREM_BACKED` corpus.
- `FullScope.lean::GraphAdmission`'s docstring carries dated corrections. Its first sentence
  and its `matchDecl` / `ranked` bullets claimed Python enforcement that does not exist.
- `formal/verify.sh`: `MIN_CONF_ALL` goes 582 → 843 and `MIN_CONF_REST` goes 447 → 708
  (§ 4 has the instrument check). **195 of those 261 were an unratcheted leak left by
  `DW-1`**: the live count on clean `b08a262` was 777 against a floor of 582.

## § 3 Decision: what the rest of `TK104` is (REASONED, the session's call per `CLAUDE.md` "Who decides")

**The decider is still worth building, but only two fields need it for honesty.** The 10
LOUD fields are Python refusals, and the 2 MIXED silent halves are already reported through
`W4Fragment`. What an operator cannot learn today is `matchDecl` and `ranked`. A Python report
of those two alone would be a hand mirror with no differential, which is exactly what `DW-1`
showed to be unsafe (the hand derivation was wrong twice). So the order is:

1. **Lean `graphAdmissionB` + exact `_iff`**, in the `FragmentDecide.lean` style.
   - Per-field decidability (REASONED from the definitions READ this session):
     - Already decidable or Bool: `DirectRestrictionsNotLeaf`, `ComputedRefsNotLeaf`,
       `NoLeafSubjects` (instances exist), `keysNonempty` (`.all`), `Stratifiable`
       (`Option.isSome`), `NodupKeys` (`List.Nodup` over `String × String`).
     - Bounded quantifiers that need only an instance or an iff: `WF` (a one-field
       structure over `S.defs`), `TtuTuplesetsDirect`, `RewriteMatchDeclared`, `objWild`,
       `usWild`.
     - Need a `match` rewrite, the way `FragmentDecide.lean` handles its lookup fields:
       `TtuTargetsSat S NotLeafName` (a `∀ tr` fixed by `r.kind`) and `StoreValidRulesD`
       (`∃ e` fixed by `S.lookup`).
     - **`RewriteRanked` is the only real proof.** It is `∃ rrank`. The plan: compute the
       candidate `r_n(k) = max over rules with out = k of r_{n-1}(match) + 1`, with
       `n = S.keys.length + 1`, and check it.
       - Soundness is trivial, because the candidate IS the witness.
       - Completeness, given any `rrank`: by induction `r_n ≤ rrank`, so every value is
         `≤ S.keys.length`. A value can only change at step `n` if it becomes exactly `n`, so
         the iteration is stationary once `n > S.keys.length`, and a stationary candidate is
         strictly increasing along every rule.
       - Only the out-keys of rules need the bound check, since every other key is 0.
2. **zcli `mode="fragment"` gains an `"admission"` key**, and (A) in
   `test_conformance_fragment.py` widens to the full premise.
3. **Python `graph_admission_report`** for `matchDecl` + `ranked` (and optionally all 14),
   differential-pinned to (2). Only then does an operator see the two SILENT fields.

**Option NOT taken: make `matchDecl` LOUD by refusing dangling references in Python.** OpenFGA
refuses them, and it would cost one check in `_validate_ast_references`. But it changes what
the product accepts in order to fit a proof. The oracle and Lean both give dangling references
a well-defined meaning (undefined ⇒ empty), and the user's goal is "honest and legible, not
wider". Whether the product should refuse them is a product question, so it is not the
model's to take here. If raised, it is an `ASK-*` row. `ranked` cannot be made LOUD without
refusing legitimate recursive schemas, so that one is off the table.

## § 4 Sabotage (`docs/sabotage-procedure.md`), literal

A mutation sweep of `test_graphadmission_scope_pin.py` with an M0 attribution control. The
runner was a throwaway `.scratch/` script: it applies one byte-exact edit, runs the module,
and restores the file byte-for-byte. Every edit's anchor matched exactly once. Baseline:
`66 passed`.

```
BASELINE rc=0 66 passed in 0.83s failed=[]
M0 control: ranked row re-classified LOUD: RED rc=1 [2 failed, 64 passed in 0.83s]
    FAILED test_classification_agrees_with_its_probes[ranked]
    FAILED test_the_classification_ratio_is_the_finding
M1 new Lean field in GraphAdmission: RED rc=1 [2 failed, 64 passed in 0.83s]
    FAILED test_graphadmission_field_count_is_the_pinned_constant
    FAILED test_graphadmission_fields_match_the_hand_classified_scope_pin
M2 Python drops the duplicate-define refusal: RED rc=1 [1 failed, 65 passed in 0.83s]
    FAILED test_schema_probe_outcome_still_holds[nodup/duplicate-define]
M3 Python drops the '.' lock on computed refs: RED rc=1 [1 failed, 65 passed in 0.78s]
    FAILED test_schema_probe_outcome_still_holds[computedRefsNotLeaf/dotted-computed-ref]
M4 Python drops the star-tupleset through-derived refusal: RED rc=1 [1 failed, 65 passed in 0.80s]
    FAILED test_schema_probe_outcome_still_holds[usWild.b/star-tupleset-through-derived]
M5 SetEngine skips the strict-Filter admission: INERT rc=0 [66 passed in 0.78s]
M6 SHADOWED names the wrong W4 field: RED rc=1 [1 failed, 65 passed in 0.77s]
    FAILED test_mixed_silent_half_is_shadowed_by_w4fragment[ttuDirect.derived/derived-tupleset]
M7 MIXED row loses shadowed_by: RED rc=1 [3 failed, 63 passed in 0.76s]
    FAILED test_every_scope_row_is_well_formed[storeValid]
    FAILED test_mixed_silent_half_is_shadowed_by_w4fragment[storeValid.derived/bare-subject-beside-a-userset-restriction]
    FAILED test_mixed_silent_half_is_shadowed_by_w4fragment[storeValid.derived/userset-subject-on-derived-direct-arm]
M8 LOUD probe relabelled ADMITTED: RED rc=1 [2 failed, 64 passed in 0.76s]
    FAILED test_classification_agrees_with_its_probes[strat]
    FAILED test_schema_probe_outcome_still_holds[strat/derived-cycle]
M9 mirror blind to TTU tuplesets: RED rc=1 [1 failed, 65 passed in 0.74s]
    FAILED test_silent_field_mirror_known_answers[matchDecl/undeclared-tupleset-untainted-target]
M10 mirror cycle check disabled: RED rc=1 [2 failed, 64 passed in 0.82s]
    FAILED test_silent_field_mirror_known_answers[ranked/computed-self-loop]
    FAILED test_silent_field_mirror_known_answers[ranked/computed-two-cycle]
RESTORED rc=0 66 passed in 0.76s
M5b RuleSet.apply plain arm admits via its first candidate Filter: INERT rc=0 [66 passed in 0.79s]
M5c both gates weakened (M5 + M5b): RED rc=1 [1 failed, 65 passed in 0.87s]
    FAILED test_store_probe_outcome_still_holds[storeValid.untainted/userset-subject-on-bare-arm]
RESTORED rc=0 66 passed in 0.79s
```

- **M5 was INERT, and it CHANGED THE ROW.**
  - What the edit should have moved: the store probes' RAISED outcome. It did not move.
  - The observed message (`tuple doc:d1#viewer@group:g1#member ...`) is
    `zanzibar_utils_v1.py::RuleSet.apply`'s format, not `SetEngine._validate`'s. The set
    engine calls `RuleSet.apply` first, from `_derived_pairs`, so two gates run in series.
  - M5b (the first gate alone) is INERT too, and M5c (both gates) goes RED. So the INERT
    results are defence in depth, not a hole in the pin.
  - The `storeValid` row's `evidence` originally cited `setengine/engine.py::SetEngine._validate`,
    the gate that never fires first. It now cites `RuleSet.apply`, and the note names both.
- M1 was not built with `lake`, by design: the check reads source text, as the `W4Fragment`
  pin does.
- **Floor instrument check.** With `MIN_CONF_ALL=844` and `MIN_CONF_REST=709` (one above
  live), `bash formal/verify.sh conf-tile:1/5` gave
  `FAIL: formal/conformance/ collects only 843 test(s); the gate floor is 844.` and rc=1.
  After restoring, the file was byte-identical (`cmp`).
