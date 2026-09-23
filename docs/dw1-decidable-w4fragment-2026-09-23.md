# `DW-1` — a decidable `W4Fragment`, sized per field, and the ordered plan

**FROZEN 2026-09-23e, at `DW-1`'s close — provenance, not a living document.** Status lines
below are as-of-then and several may now be false; live state: `HANDOFF.md` + the session
ledger. Corrections are appended dated at the top, never edited into the body. (Was
ACTIVE-PLAN from 2026-09-23d, `docs/README.md` §3.) Live state is `python scripts/task.py show DW-1`, never this file. Every figure below
was measured on `2026-09-23` against HEAD `0ef89ab`.

Provenance labels: **READ** (verified first-hand, `file::symbol`), **REASONED**, **PROBED**
(a script was run, literal output quoted), **UNVERIFIED**. Two read-only subagents did the
census (called *agent L* for the Lean side and *agent P* for the Python side below). Anything
marked READ-by-agent was read by that agent and **not** re-read by the session. The session
re-read the citations marked **READ (session)**.

## Progress, 2026-09-23e: steps 3 and 4 LANDED, and `DW-1` closes (appended; the body below is as-written)

Everything in this block was MEASURED this session, against HEAD `8b3ab46` plus the
session's diff, with the `zcli` that `8b3ab46` built.

- **Step 3: `zanzibar_utils_v1.py::w4_fragment_report(schema, tuples)`.**
  - It is a pure per-field report, `W4FragmentReport` with `fields` / `failures` /
    `in_fragment` / `tainted`, placed after `unparse_schema_ast`. It changes no behaviour:
    nothing calls it on a write path, and it never raises on an out-of-scope input
    (`tests/test_w4_fragment_report.py` pins a compile-RAISED schema being *reported*).
  - It takes the raw AST or DSL text. Tuples may be `TupleV1`, `OracleTuple` or plain
    6-sequences, and `...` / `Ellipsis` / `None` all read as bare.
  - Each field helper cites the Lean definition it mirrors. The union-only walk for
    `noUnionDirects` carries the S2 trap in a comment.
- **The probe fixtures: `formal/conformance/w4_scope_probes.py::SCOPE_PROBES`.** These
  are the scope pin's 2026-08-31 probe labels re-created as inputs. The originals survived
  only as labels.
  - There are 12 schema-side and 5 store-side probes, plus 1 added by the sweep (M16).
    Each field is the ONLY failure of at least one probe.
  - `expected_failures` was hand-derived from the Lean definitions (REASONED) before
    either decider was run.
  - **The hand derivation was wrong twice. Both errors were the hand's**, and Lean and
    Python agreed with each other on the first run:
    - `wsBare/wildcard-userset-over-DERIVED`: a userset restriction over a derived
      relation taints its holder, so the probe also fails `directArmsBare`,
      `directArmsConcrete` and `noUnionDirects`.
    - `term.NoTtuTarget/mixed-member-types`: the first reconstruction (`parent: [org,
      team]`) COMPILED. The raising corner is the one `_validate_ttu_tuplesets`' comment
      names: the tupleset's only member type has a PLAIN `member`, while another type's
      `member` is derived. Both Python's refusal and `NoTtuTarget` compare names only.
  - `PYTHON_OUTCOME` re-checks ADMITTED / RAISED for every schema-side probe. All 13
    match the 2026-08-31 record.
- **The differential lives in `formal/conformance/test_conformance_fragment.py`:**
  - (D) the report equals Lean per field and on `tainted`, over the 36 corpora and 18
    probes;
  - (E) each probe's verdict equals the hand derivation, by both sides;
  - (F) `PYTHON_OUTCOME` still holds;
  - `test_production_field_list_is_the_lean_structure` requires the production field list,
    the module's own `W4_FIELDS` and the fields parsed from `FullScope.lean` to be ONE
    list in one order.
  - The first run was green (`182 passed`), so the sweep below followed.
- **Step 4: `test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` gained a `reported_by`
  column.** `test_every_field_is_reported_and_has_a_rerunnable_probe` requires three
  things of each row: `reported_by` resolves to a callable in `zanzibar_utils_v1.py`, that
  report emits the field, and at least one probe labelled `<field>/` or `<field>.<half>/`
  fails it.
- **Decision (the session's):** the classification vocabulary did NOT gain a fourth value,
  and SILENT stays SILENT. Classification describes the WRITE path. The report is opt-in,
  so an out-of-scope write is still accepted with no signal unless someone asks. A
  "REPORTED" value would claim more than the code does. The plan's step 4 allowed a fourth
  value; it did not require one.

**Mutation sweep of step 3, literal.** One anchored edit each. The file was restored and
byte-compared after every run. Targets: `test_conformance_fragment.py` +
`tests/test_w4_fragment_report.py`. Baseline `186 passed` (`189` after M16's probe).

    M0  rc=1 2 failed   CONTROL: flip twoStrata/three-strata's expectation to ()
        test_scope_probes_are_not_vacuous
        test_scope_probe_verdict_matches_the_hand_derivation[twoStrata/three-strata]
    M1  rc=1 7 failed   computedOrDirect: TTU leaf allowed
    M2  rc=1 2 failed   directArmsBare: union-only walk
    M3  rc=1 2 failed   directArmsConcrete: union-only walk
    M4  rc=1 2 failed   computedOnly: Direct leaf allowed
    M5  rc=1 15 failed  noUnionDirects via exprDirectsAll (the S2 trap)
    M6  rc=1 3 failed   twoStrata: skip first ref
    M7  rc=1 5 failed   wsBare: derived defs only
    M8  rc=1 3 failed   bareStar: object-star clause dropped
    M9  rc=1 4 failed   bareStar: userset-star clause dropped
    M10 rc=1 2 failed   ttuStarFree: (ot, rel) key swapped
    M11 rc=1 5 failed   term: NoTtuTarget half dropped
    M12 rc=1 4 failed   term: NoStoreSubjectR half dropped
    M13 rc=0 186 passed schemaRewrites arms also walk inter/excl -- EQUIVALENT, not inert:
                        compute_taint taints every def containing a boolean node, so an
                        UNTAINTED def (the only kind the arms are read from) has none
    M14 rc=1 4 failed   schemaRewrites: taint filter dropped
    M15 rc=1 1 failed   tuple normalisation: Ellipsis not mapped
        test_every_bare_predicate_spelling_is_the_bare_predicate   (the differential is
        BLIND to this one -- corpus tuples arrive pre-normalised -- which is why the
        tests/ module exists)
    M16 rc=0 186 passed derived operands: first ref only.  INERT on first run: every
                        probe's derived operand was its def's FIRST computed ref. Fixed
                        by adding probe computedOnlyOperands/derived-operand-second;
                        re-run: rc=1 2 failed (that probe, in (D) and (E))
    M17 rc=1 1 failed   (F) instrument: flip one PYTHON_OUTCOME entry
    M18 rc=1 1 failed   production field ORDER swapped
        test_production_field_list_is_the_lean_structure

M0 attributed correctly: it named the probe whose claim was flipped, plus the anti-vacuity
test, because `twoStrata` then had no isolating probe. That is an honest second red. Every
field mutation reddened at least one (D) row naming a probe for that field.

**Sabotage of step 4, literal** (target `test_w4fragment_scope_pin.py`, baseline `25 passed`):

    S4a rc=1 1 failed  bareStar row cites w4_fragment_reports (nonexistent)
        ...::test_every_field_is_reported_and_has_a_rerunnable_probe[bareStar]
    S4b rc=1 1 failed  the only probe failing ttuStarFree relabelled ttuStarFreeX/...
        ...::test_every_field_is_reported_and_has_a_rerunnable_probe[ttuStarFree]
    S4c rc=1 1 failed  computedOnlyOperands row loses its reported_by
        ...::test_every_field_is_reported_and_has_a_rerunnable_probe[computedOnlyOperands]

**What is still NOT covered** (this is why the row closes without "the theorem applies"):
the report covers the `W4Fragment` half of the premise only. `GraphAdmission` has no
decider and no field classification. That is `TK104`, promoted to `NOW` at this close as
the remaining owner of goal step 3.

## Progress, 2026-09-23d (appended; the body below is as-written)

**Steps 1 and 2 LANDED; steps 3 and 4 are open.** Everything below is MEASURED this session.

- **Step 1: `GraphIndex/FragmentDecide.lean`.**
  - It provides `w4FragmentB`, `w4FragmentB_iff` (exact, both directions),
    `instDecidableW4Fragment`, `w4FragmentFieldsB` (by field name),
    `w4FragmentFailures` and `_nil_iff`.
  - Pins: two positives (`W4Witness.Sx`/`Tx`, and `LeafWitness.Sw`/`P5Witness.store`) and
    ten per-field controls. Each control is `Sx`/`Tx` with ONE edit, and each pins its exact
    failure list.
  - The controls elaborated green on their first run. Because that is the suspicious case,
    they then got a **14-mutation sweep**, whose literal table is in the module's docstring:
    - M0 (flip one pin's own claim) reddened exactly that pin.
    - Every field mutation reddened BOTH its `_iff` and its own per-field pin.
    - M13 (`lookupAll`'s `none` branch returns `false`) reddened `lookupAll_iff` only. No
      schema can observe that branch: a tainted key always has a definition.
  - The `lake build` rc was 0. 28 names were added to `Audit.lean` / `audited_theorems.txt`,
    and none were removed.
- **Step 2: `zcli mode="fragment"`, `runner.py::run_fragment` and
  `formal/conformance/test_conformance_fragment.py`.** The module collects 98 tests.
  - (A) holds every `_THEOREM_BACKED` corpus inside the fragment.
  - (B) pins Lean's per-field verdict on all 36 curated corpora against the probe-derived
    `_EXPECTED_FAILURES`.
  - (C) pins Lean `taintedKeys` == `compute_taint`.
  - First run: `98 passed`, green immediately, so four sabotages followed.
- **Decision: `mode="graph"` does NOT refuse** (`formal/CORRESPONDENCE.md`, the 2026-09-23d
  note). A refusal would abolish `_DIFFERENTIAL_ONLY`. REPORTING scope meets the
  driver-honesty goal.
- **The three `GRAPH_FRAGMENT` disagreements are settled for the `W4Fragment` half.** Lean
  agrees with the Python probe that `ttu_fromchain`, `ttu_fromchain_group` and `self_flag`
  are IN. `corpus.py` carries dated notes. None was moved into `GRAPH_FRAGMENT`, because the
  `GraphAdmission` half is unargued.

**Sabotage of step 2, literal.** Each run rebuilt `zcli` with the mutation, ran the module,
then restored the source and rebuilt. `cmp` confirmed the restored source was byte-identical.

    S1-as-first-run  wsBare decider -> true, in FragmentDecide.lean
                     build rc=1 (the module's own proofs/pins refuse it) -> pytest ran the
                     STALE zcli: 98 passed.  INSTRUMENT FAILURE, not evidence: a failed
                     `lake build zcli` leaves the old binary in place and the Python test
                     then certifies the OLD decider. The harness was changed to ABORT on a
                     nonzero build rc.
    S1  zcli seam: report wsBare = true            build rc=0  1 failed, 97 passed
        FAILED ...::test_lean_verdict_matches_the_independent_mirror[TTU_USERSET:wildcard_userset]
    S2  zcli seam: noUnionDirects over exprDirectsAll (the trap agent P named)
                                                   build rc=0  3 failed, 95 passed
        FAILED ...::test_theorem_backed_corpora_are_inside_w4fragment[direct_arm_exclusion]
        FAILED ...::test_lean_verdict_matches_the_independent_mirror[SCHEMAS:direct_arm_exclusion]
        FAILED ...::test_lean_verdict_matches_the_independent_mirror[TTU_USERSET:derived_tupleset_ttu]
    S3  instrument: drop 3 of 4 corpus families    1 failed, 79 passed
        AssertionError: only 27 curated corpora found; floor 36.
    S4  zcli seam: emit taintedKeys minus its head build rc=0  25 failed, 73 passed
        (all 25 corpora with a nonempty derived set; every failure a taint test)

S1-as-first-run carries a lesson the gate already handles, because `verify.sh lean` builds
`zcli` and fails on its rc. The hazard is a HAND run of conformance after a Lean edit.

**Still open.**
- **Step 3:** the production Python `w4_fragment_report` and its differential against
  `mode="fragment"`. The scope pin's probe schemas also have to become fixtures.
- **Step 4:** the `W4FRAGMENT_SCOPE` column.

`GraphAdmission` decidability is filed as its own row.

---

## § 0 What the row is for

This is goal step 3 of `docs/goal-census-2026-09-22.md`: *surface the silent narrowing*.
`graph_correct` and every other headline theorem take `(hA : GraphAdmission S T)
(hF : W4Fragment S T)`. `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE`
classifies the ten `W4Fragment` fields as LOUD 0, MIXED 3 and SILENT 7. So Python runs a schema
outside the theorem's scope without saying so. `formal/CORRESPONDENCE.md` (the `DW-1`
paragraph after the 2026-08-14 `mode=graph` measurement) states the completion criterion:
*"an `admissionB`-style boolean form for `W4Fragment` plus its soundness equivalence lemma,
wired as a zcli `mode=graph` pre-check that REFUSES an out-of-fragment schema instead of
answering."*

**Correction to that criterion (READ, session): `admissionB` does not exist.** A grep of
`formal/lean`, `*.py` and `*.md` for `admissionB` finds only prose mentions of it
(`formal/CORRESPONDENCE.md` and `docs/history/handoff-status-2026-08.md`). `GraphAdmission` has
no Boolean form and no `Decidable` instance either (READ-by-agent-L:
`GraphIndex/Exec.lean::slV_admission_nil`'s docstring, measured 2026-09-05). The real
precedent is `GraphIndex/Exec.lean::removeGateB` together with its component twins
(`bareStarStoreB_iff`, `ttuStarFreeB_iff`, `htermB_iff`), which are READ (session).

## § 1 Lean side: per-field decidability (agent L, spot-checked by the session)

**The quantifier problem.** Six fields quantify `∀ dt R e, S.lookup (dt, R) = some e →
isDerived S (dt, R) = true → …` over all strings, which `decide` cannot handle as written.
- `Core/Schema.lean::Schema.lookup` is `defs.find?`, which returns the first match. READ (session).
- `Core/Schema.lean::WF` has no nodup clause. `NodupKeys` appears only as
  `FullScope.lean::GraphAdmission.nodup` (READ, session).

So quantifying over `∀ p ∈ S.defs` would be strictly STRONGER than the field when keys repeat.
It would still be sound, but it would lose completeness unless `NodupKeys` were threaded in
through `RulesSound.lean::lookup_of_mem` (READ, session: that lemma takes `NodupKeys S`). The
converse lemma, `RestrictBase.lean::mem_defs_of_lookup`, needs no hypothesis (READ, session).

**Decision (the session's, recorded on the row).** Quantify over `taintedKeys S` and
`match S.lookup k` instead. `isDerived S k` is `(taintedKeys S).contains k`
(`Spec/Stratify.lean::isDerived`, READ-by-agent-L). That makes the rewrite EXACT, with no nodup
premise. `Exec.lean::htermB_iff` is already this proof shape, via `List.contains_iff_mem`
(READ, session).

| field | verdict | what is needed |
|---|---|---|
| `computedOrDirect` | CHEAP | Bool twin of `ReconcileCorrect.lean::ComputedOrDirect` (Prop, structural) + iff by induction |
| `directArmsBare` | CHEAP | Bool twin of `ReconcileCorrect.lean::DirectArmsBare` + iff |
| `directArmsConcrete` | CHEAP | body already decidable (`exprDirectsAll`, Bool flag); outer quantifier only |
| `computedOnlyOperands` | CHEAP (upper end) | Bool twin of `ReconcileCorrect.lean::ComputedOnly` + a fixed-key inner `match` |
| `noUnionDirects` | CHEAP | body is `exprDirects e = []`, already decidable; outer quantifier only |
| `twoStrata` | CHEAP | no Prop predicate at all; nested fixed-key `match` only |
| `wsBare` | EXISTS | bounded `∀ sh ∈ declaredWildcardShapes S`; the witnesses already close it `by decide` |
| `bareStar` | EXISTS | `Exec.lean::bareStarStoreB_iff` (READ, session) |
| `ttuStarFree` | EXISTS | `Exec.lean::ttuStarFreeB_iff` (READ, session) |
| `term` | EXISTS | `Exec.lean::htermB_iff` has exactly the field's statement as its RHS (READ, session) |

The three Prop definitions and `exprDirectsAll` / `exprDirects` / `computedRefs` were READ
(session) at `GraphIndex/ReconcileCorrect.lean` and `GraphIndex/RulesSound.lean::exprDirects`.
Agent L's estimate (REASONED) was about 120–170 lines and one session, with every step
following a template already in the tree.

**Placement caveat (READ-by-agent-L).** `P6` part (iv) would flip `ttuStarFree` to
`RulesBareStar.lean::TtuStarFreeW`. Its Bool twin, `TtuStarWide.lean::ttuStarFreeWB`, is
downstream of `Exec.lean`, so after that flip the decider has to move with it. `P6` is parked
(2026-09-15d), so `Exec.lean` is correct today.

**Direction (REASONED).**
- SOUNDNESS (`B = true → W4Fragment`) is what makes "accepted ⇒ covered by the theorem" true.
- COMPLETENESS (`W4Fragment → B = true`) is what makes "refuses exactly the outside" true, so
  that no in-scope input is refused.

A `Decidable` instance needs both. On the route above both cost the same, so the deliverable is
the iff.

**`GraphAdmission` is the other half of the premise and is OUT OF THIS ROW (decision).**
- READ (session): `RulesSaturate.lean::RewriteRanked` is `∃ rrank : (String × String) → Nat,
  … ∧ (∀ k, rrank k ≤ S.keys.length)`. Deciding it means an acyclicity check plus a witness
  construction.
- READ (session): `Spec/Stratify.lean::Stratifiable` is `(stratify S).isSome`, which is Bool
  already.

A `W4Fragment` decider is still the whole of *this* row's purpose. The SILENT classification
belongs to `W4Fragment`'s fields, and `GraphAdmission` is largely mirrored by Python compile and
write refusals. That last point is UNVERIFIED: nothing classifies `GraphAdmission`'s fields the
way `W4FRAGMENT_SCOPE` does. It is filed as a separate row.

## § 2 Python side (agent P)

- **No Python function evaluates any field over an arbitrary schema** (READ-by-agent-P, grep
  census). The one exact mirror is `wsBare`, which is equivalent to
  `zanzibar_utils_v1.py::wildcard_userset_restriction_shapes(ast) == frozenset()`
  (REASONED-by-agent-P).
- `len(compiled.strata) <= 2` is stricter than `twoStrata`, because Python's plan dependencies
  also follow userset and TTU edges. The two coincide once the other schema fields hold
  (REASONED-by-agent-P).
- `tests/test_hypothesis.py::_build_in_fragment` means "the graph index compiles it"
  (GraphAccepts), which is a strict superset of `W4Fragment`.
- **The raw `SchemaAST` is required.** `compiled.plans` is lossy: a pure TTU inside a derived
  definition folds into a `PClosureLeaf` in `zanzibar_utils_v1.py::_build_plan_tree`
  (READ-by-agent-P). `SetEngine.ast` retains the AST. `RuleSet` does not.
- **Where each field is checked:** seven fields are schema-only. `term` is split (its
  `NoTtuTarget` half is schema-only, its `NoStoreSubjectR` half is per-tuple). `bareStar` and
  `ttuStarFree` are per-tuple, with the natural hook `SetEngine._validate`.
- **There are no warning or logging calls in production code** (READ-by-agent-P: zero grep hits
  for `warnings.warn` / `logging`). The simplest honest surface is a pure function that returns a
  per-field report.

**PROBED (agent P, 2026-09-23): a straw-man mirror of all ten fields** (about 55 lines of AST
walk, now `formal/probes/dw1_python_mirror_2026-09-23.py`; the session re-ran it from there, rc 0, same summary) was run over the 36 curated corpora
and compared with the hand-kept `formal/conformance/corpus.py::GRAPH_FRAGMENT`. Literal summary:
`agree=33 disagree=3`. The three disagreements, where the mirror says IN on all ten fields and
the list says OUT:

    DIFF TTU_USERSET:ttu_fromchain mirror=IN listed=OUT strata=0 compile=ok twoStrata=True fails=[]
    DIFF TTU_USERSET:ttu_fromchain_group mirror=IN listed=OUT strata=0 compile=ok twoStrata=True fails=[]
    DIFF SELF_REF:self_flag mirror=IN listed=OUT strata=1 compile=ok twoStrata=True fails=[]

Agent P's reading (REASONED, **not** Lean-checked):
- In `ttu_fromchain` and `ttu_fromchain_group` the TTU sits in an UNTAINTED definition, and
  `computedOrDirect` constrains only derived ones. So the `corpus.py` header's stated reason
  for excluding them appears not to apply. A `GraphAdmission` reason was not examined.
- `corpus.py` records `self_flag` as an OPEN question.

Once step 1 lands, all three are exactly the questions `w4FragmentB` settles `by decide`.

**Mirror or differential (decision).** A hand-written Python mirror WILL drift. `W4Fragment`
has been reshaped repeatedly: leg 5, the `wsBare` re-point on 2026-09-14h, and `P5` on
2026-09-23b. A stale mirror would then say "proven" when that is false. So the Python mirror
ships only together with a differential against a Lean-side decider, driven through `zcli`.

One caveat on that differential (READ-by-agent-P): `zcli` reads schemas through the oracle-side
`formal/conformance/encode.py`, while an operator pre-check reads the production parser. A red
has to be attributed to parser versus mirror before the mirror is changed.

## § 3 The ordered plan

1. **Lean decider** (`GraphIndex/Exec.lean`, after `removeGateB_gate`):
   - `derivedDefsAll` + `_iff`
   - `computedOrDirectB` / `directArmsBareB` / `computedOnlyB` + iffs
   - `w4FragmentB` (ten conjuncts, one per field, exposed as a per-field list so `zcli` can
     report which field failed), `w4FragmentB_iff`, and
     `instance : Decidable (W4Fragment S T)`

   Evidence: `by decide` pins that the decider says TRUE at an existing hand-proved witness,
   plus one out-of-fragment schema per field that flips THAT field alone, with the other nine
   pinned TRUE. Without the latter, a decider that returned `false` everywhere would pass. Then
   the sabotage sweep.
2. **`zcli mode=fragment`**: emit the per-field Bools and `taintedKeys` (which also finally
   makes `isDerived ≡ compute_taint` mechanical, per agent P §4). Make `mode=graph` refuse an
   out-of-fragment input with a new rc. That second part is the CORRESPONDENCE completion
   criterion.
3. **Python `w4_fragment_report(ast, tuples)`** in production code, as a pure function that
   returns a per-field report. It is not a refusal: Python behaviour does not change. A
   conformance differential compares it with `zcli mode=fragment` over every corpus plus the
   scope pin's probe schemas, turned into re-runnable fixtures (today they exist only as prose
   in that module's docstring).
4. **Scope-pin column.** `W4FRAGMENT_SCOPE` gains a `reported_by` column. SILENT becomes
   "accepted, but reported", and the classification vocabulary gets a fourth value only if the
   differential is green. Settle `GRAPH_FRAGMENT`'s three disagreements (§ 2) by the decider,
   not by prose.

Out of this row: a `GraphAdmission` decider (filed separately).

## § 4 Step-3 carriers and hooks (agent P, READ-by-agent-P, transcribed 2026-09-23d)

This section was transcribed from agent P's scratch report before `.scratch/` was cleaned.
Nothing in it was re-read by the session.

| field | kind | what the Python check needs |
|---|---|---|
| computedOrDirect | schema | the AST defs of tainted keys contain no `TTU` node anywhere |
| directArmsBare | schema | every `Restriction.predicate == '...'` in any `Direct` of a tainted def, at any nesting |
| directArmsConcrete | schema | no `Restriction.wildcard` in any `Direct` of a tainted def, at any nesting (Lean `exprDirectsAll`) |
| computedOnlyOperands | schema | each `Computed` ref of a tainted def that is itself tainted has a Computed-only def |
| noUnionDirects | schema | no `Direct` is reachable from a tainted def's root through `Union` nodes ONLY (Lean `exprDirects`) |
| twoStrata | schema | AST computed refs + taint (`len(compiled.strata) <= 2` is STRICTER; it follows userset/TTU deps too) |
| wsBare | schema | `zanzibar_utils_v1.py::wildcard_userset_restriction_shapes(ast) == frozenset()`; NOT `SchemaInfo.subject_wildcard_shapes`, which spans both passes |
| bareStar | per tuple | `s_name == '*' ⇒ s_pred == '...'`, and `o_name != '*'` |
| ttuStarFree | per tuple + schema precompute | precompute `{(dt, tupleset)}` over the union-reachable TTU arms of UNTAINTED defs (Lean `schemaRewrites`); a star-subject tuple must not land on one |
| term | schema + per tuple | `NoTtuTarget`: no untainted-def TTU `target_rel` is a derived NAME (implied by a successful compile). `NoStoreSubjectR`: no tuple's `s_pred` is a derived relation name |

Carriers:
- The raw AST is `zanzibar_utils_v1.py::parse_schema_ast`. It is n-ary, whereas Lean's is
  binary via `encode.py::_fold_binary`; all ten fields are homomorphic over that fold. It is
  retained as `SetEngine.ast` and NOT on `RuleSet`.
- The derived set is `compute_taint(ast)`, which equals `RuleSet.compiled.tainted` and
  `schema_info.derived_families`.
- The persisted text is `connectedstore/models.py::SchemaV4.schema_text`. It is compiled once
  at `connectedstore/schema_io.py::save_schema` / `::load_schema`.
- Every write reaches `setengine/engine.py::SetEngine._validate`, from both `add_tuple` and
  `TupleSource.add`.

Hooks:
- `UnsupportedByGraphIndex` is NOT a fit. Raising it would change behaviour and the matrix's
  4-way/3-way split.
- The precedent for an opt-in kwarg is `compile_ruleset(..., *, enable_boolean=True)`.
- The precedent for an operator knob with explicit > env > default precedence, where a typo
  raises, is `index_v4/invariants.py::resolve_paranoia_level`.
- The production packages contain zero `warnings`/`logging` calls. A pure report function
  called by the operator (or by `save_schema`) is the natural non-raising shape.
- The store fields quantify over tuples, so they are monotone under add. The headline chain
  is add-only, so a per-write check equals a final-store scan until the first remove, and a
  remove takes the store off the `ReachedBy` chain anyway (REASONED-by-agent-P).
