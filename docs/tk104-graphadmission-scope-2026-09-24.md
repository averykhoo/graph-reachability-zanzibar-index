# `TK104` — `GraphAdmission` sized per field: LOUD 10, MIXED 2, SILENT 2

**ACTIVE-PLAN from 2026-09-24 (`docs/README.md` §3).** The body is provenance. Corrections
are appended dated at the top, never edited into the body. The doc freezes when `TK104`
closes. Live state is `python scripts/task.py show TK104`, never this file. Every figure below
was measured on `2026-09-24` against HEAD `b08a262` plus this session's diff.

Provenance labels: **READ** (verified first-hand, `file::symbol`), **REASONED**, **PROBED**
(a script was run, literal output quoted), **UNVERIFIED**. No subagent was used. Every READ
below was read by the session.

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
