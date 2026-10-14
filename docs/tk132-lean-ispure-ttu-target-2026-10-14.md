# `TK132`: the Lean `isPure` TTU arm asks by NAME, Python by `(type, relation)`. The measured scout

**ACTIVE-PLAN, opened 2026-10-14. The body is provenance, not a living status.** This is the
scout-only map for task row `TK132`. One scouting agent (`scout-TK132`) produced it on
2026-10-14 and edited no file under `src/`, `tests/`, `formal/` or `tasks/`. The live state
is the task row (`python scripts/task.py show TK132`), never this file. Corrections are
appended **dated at the top** and are never edited into the body. Freeze this file when
`TK132` closes.

Provenance labels used on every claim:
- **READ**: the cited `file::symbol` was read first-hand on 2026-10-14.
- **PROBE**: a script under `.scratch/now-next/probes/scout-TK132/` was run first-hand on
  2026-10-14. That directory is gitignored, so the literal output is quoted here wherever it
  is load-bearing, and so is the probe body where it is the proposal itself.
- **REASONED**: an inference from READ/PROBE facts that was not executed.
- **UNVERIFIED**: stated elsewhere and not re-checked here.

Line numbers are as of 2026-10-14 and will rot. The `file::symbol` is the anchor.

## Decision 2026-10-14

Executive decision by agent `decide-TK132` (CLAUDE.md "Who decides"). Anchors below were
re-READ first-hand 2026-10-14 unless marked REASONED. The scout's probes are evidence; this
section is the finding. Design **L-A, amended by X1/X2/X6**, is DECIDED. L-B is deferred to
`TK133` with its X5 cost estimate recorded there so it is not re-scouted.

**Why L-A (weighed against the goal).** Equivalence is untouched: Python already matches the
oracle on `D`/`D_nested`/`SlXt` (P2/P6), so this is a model-fidelity fix, and CORRESPONDENCE §8
says fix the model. L-A makes `leafRewrites` describe `_build_plan_tree` again (P4/P7: 63/64
named schemas unchanged, `SlXt` becomes Python's allocation). Its cost is one binder on two
headline statements and a scope loss (X3) that is HONEST: today's coverage of `D` by
`runCascade2_no_abort` / `cascade2_drains` is coverage of a model that is not the code. L-B
buys that coverage back only for two termination theorems on shapes whose correctness theorem
(`graph_correct`, gated by `computedOrDirect`) and whose operational answers (C4, 2026-08-14
class) are both out of reach; that is not worth a typed closure lemma + a
no-rule-outputs-a-tupleset lemma + a store binder now. P-1 and L-0 stay rejected (§6).

**Lean edits, by `file::name`.**
1. `GraphIndex/Leaf.lean`: add `ttuParentTypes` (§2.5 verbatim, docstring cites
   `Spec/Stratify.lean::exprRefs`/`directTypes` as twin); change `isPure`'s `.ttu` arm to
   `!isDerived S (ty, ts) && (ttuParentTypes S ty ts).all (fun pt => !isDerived S (pt, tgt))`.
   Keep `derivedAnywhere` (the carry uses it). Docstrings: ⚠ paragraphs become dated history.
2. `GraphIndex/LeafRules.lean` (section `ObligationAPremise`):
   `def LeafTtuTargetsUnderived (S) : Prop := ∀ r ∈ leafRewrites S, ∀ tr ∈ ttuTargets r,
   derivedAnywhere S tr = false` + `Decidable` instance (pattern: `TtuTargetsSatL`). This is
   the NARROWEST carry the proof consumes (it keeps `W1`-class coverage: leaf TTU rule whose
   target is derived nowhere); `NoLeafTtu` was considered and rejected as strictly stronger.
   Restate `ttuTargetsSatL_ne_of_noTtuTarget` and `rewriteClosureL_subject_pred_ne_of_noTtuTarget`
   with `(hLTU : LeafTtuTargetsUnderived S)` after `hder`; the leaf arm is `hLTU r hr tr htr`.
   DELETE `derivedAnywhere_eq_false_of_mem_exprArms_of_isPure` and
   `derivedAnywhere_eq_false_of_mem_leafRewrites` (false under the new arm; no other consumer).
3. **Discharge (X1 accepted; it is ~10 lines, not 40).** The induction already exists:
   `GraphIndex/CascadeStable.lean::kind_computed_of_mem_leafRewrites_computedOrDirect (hNK :
   NodupKeys S) (hCO) : r ∈ leafRewrites S → r.kind = .computed` (L2157, 2026-10-14) and it
   already takes `hNK` via `lookup_of_mem`, which confirms X1. So put
   `leafTtuTargetsUnderived_of_computedOrDirect (hNK : NodupKeys S) (hCO : ∀ dt R e, S.lookup
   (dt,R) = some e → isDerived S (dt,R) = true → ComputedOrDirect e) : LeafTtuTargetsUnderived S`
   in `CascadeStable.lean` right after that lemma: `ttuTargets r = []` by `simp [ttuTargets]` at
   `.computed`, so the `∀ tr ∈ []` is vacuous. No `ReconcileCorrect` import into
   `LeafRules.lean`. Docstring states that the OLD leaf fact needed no `NodupKeys` and this
   premise is new. Every discharge site holds `hA.nodup` (`FullScope.lean::GraphAdmission` L214).
4. **Threading.** `hLTU` immediately after `hNBD` in the 52 `hNBD` carriers (P3) and in
   `writeLegSubjectsWide_L` (+ `_snlBoth`). Headline: `CascadeStrata.lean::runCascade2_no_abort`
   L1880 and `::cascade2_drains` L2049 gain `(hLTU : LeafTtuTargetsUnderived S)` after `hNBD`;
   update the 5 call sites (`CascadeStrata.lean:2063`, `CascadeStrataResettle.lean:940/1364/
   2189/2510`). Do NOT add `NodupKeys` to the headline statements; it belongs to the
   discharge only. Do NOT restate the type-blind intermediate lemma typed (X4): that is L-B.
5. **Witnesses (`LeafRules.lean`, namespace `LeafRuleWitness`, all `by decide`):**
   - `lrXt_cross_type_drop` → INVERTED as `lrXt_cross_type_kept : leafRewrites SlXt = [team
     z→viewer.0, team y→viewer.1, ⟨doc, parent, access.0, .ttu "viewer"⟩, ⟨doc, banned,
     access.1, .computed⟩]` (P4 literal).
   - `hLTU_load_bearing : (∀ r ∈ schemaRewrites SlXt, ∀ tr, r.kind = .ttu tr → tr ≠ "viewer")
     ∧ isDerived SlXt ("team","viewer") = true ∧ ¬ TtuTargetsSatL SlXt (· ≠ "viewer")`.
   - NEW `SMix` (X2: `doc#parent: [folder, team]`, `team#viewer` derived, `folder#viewer`
     plain, `access: viewer from parent but not banned`) with `lrMix_mixed_parent_drop :
     leafRewrites SMix = [team z→viewer.0, team y→viewer.1, ⟨doc, banned, access.0, .computed⟩]`.
   - NEW `SlW3` (X6, TK119's `W3_merged_computed_ttu`: `viewer: (a or viewer from parent) but
     not c`) with `lrW3_merged_computed_ttu : leafRewrites SlW3 = [⟨doc,a,viewer.0,.computed⟩,
     ⟨doc,parent,viewer.0,.ttu "viewer"⟩, ⟨doc,c,viewer.1,.computed⟩]` (TK119 sec 4 literal).
   - NEW `SDup` (X1's `DupKeys.lean`) with `leafTtuTargetsUnderived_needs_nodup :
     (SDup.keys.all (fun k => !isDerived SDup k || (match SDup.lookup k with | some e =>
     computedOrDirectB e | none => true))) = true ∧ ¬ NodupKeys SDup ∧ ¬ LeafTtuTargetsUnderived
     SDup` (`FragmentDecide.lean::computedOrDirectB` L38 is the Bool twin). Proves `hNK` is
     load-bearing on the discharge.
   - Unchanged: `lrStD_no_ttu_rule`, `Leaf.lean::stD_leaves`, `slXt_viewer_*`.
6. **Pins that move.** `headline_statements.txt`: 2 rows; `correspondence_anchor_pin.txt` L73/L79
   (the same two `theorem-statement` hashes); `headline_definitions.txt`: `isPure` row changes,
   new rows `ttuParentTypes`, `LeafTtuTargetsUnderived` (`directTypes`/`ttuTargets`/`NodupKeys`
   already present). `audited_theorems.txt` additions (superset rule): the discharge lemma,
   `hLTU_load_bearing`, `lrXt_cross_type_kept`, `lrMix_mixed_parent_drop`,
   `lrW3_merged_computed_ttu`, `leafTtuTargetsUnderived_needs_nodup`, each with `#print axioms`
   in `Audit.lean`. Regenerate with `statement_pin.py --generate`; the commit message, a
   `formal/history/tk132-*.md` note and the row comment all say WHY in one sentence: "the two
   statements gain a schema carry the faithful allocation needs; it is vacuous on `W4Fragment`,
   and it is FALSE on `D`/`D_nested`/`SlXt`, whose previous coverage was of the wrong model."
   `CORRESPONDENCE.md`: §4 `isPure` row rewritten; §7.1 `TK126` entry closed with a dated
   FIXED line; new HONEST-carry row for `LeafTtuTargetsUnderived` naming the X3 loss and L-B.

**TK119's four positive pins (`_TK132_EXPECTED`: `D`, `D_nested`, `SlXt`, `W3`).** Order stays
TK119 first (its X13). TK132's commit DELETES the four entries and the dict; the four sources
join the agreeing set of `test_leaf_rules_match_python`; "mismatching set == expected keys"
then means EMPTY, so no fifth mismatch can hide. `test_tk132_gap_is_exactly_the_recorded_diff`
is deleted (an empty pin is prose). `SMix` and `SlW3` are added to
`corpus.py::LEAF_RULE_WITNESSES` as agreeing sources (`SDup` stays Lean-only: a duplicate
key is not a schema Python serves). The shape floors ("≥1 matched source with
a leaf TTU rule / merged closure leaf") are re-measured and ratcheted UP (they gain
`D`/`D_nested`/`SlXt`/`W3`). If TK132 lands first instead, TK119's builder never writes the
dict and adds the four as agreeing sources; the acceptance is the same green sweep.
`tests/test_tk126_ttu_target_name_collision.py::test_slxt_python_allocation_is_the_recorded_gap`
→ `test_slxt_python_allocation_matches_the_model`, same assertion.

**T2 stays, as the second instrument AND as the positive pin of C4.** New
`formal/conformance/test_conformance_tk132_leaf_rows.py`: Lean vs Python `graph-state`
restricted to edges whose OBJECT predicate is a leaf name (X7: test the object side only,
`...` is a subject predicate), EQUAL on `SlXt`/`D`/`D_nested`/`SlXtR`/`StD`, non-vacuity ≥1 leaf
edge each; and a POSITIVE pin that the residual public-edge/residue diff is exactly the P2/P6
rows. File a new row for C4 (the 2026-08-14 `.ttu`-in-derived-def under-report, fail-closed,
outside `W4Fragment`) at LATER and name it in that pin's docstring: a known divergence with no
row and no pin is the house failure mode.

**Sabotages (each must go RED before it is believed; record the literal output):**
S1 revert the arm → `lrXt_cross_type_kept`, `hLTU_load_bearing`.3, `lrW3_*` fail to elaborate.
S2 same-type test `!isDerived S (ty, tgt)` → `lrStD_no_ttu_rule` / `stD_leaves` red.
S3 parent types off the CONTAINER def → same pair red. S5 `.all` → `.any` →
`lrMix_mixed_parent_drop` red; Python control: `_is_pure` with `any` makes `SMix` RAISE the I5
`ValueError`, and the TK119 sweep treats a refusal as FAILURE, so the Python side is pinned
too. S6 drop `hNK` from the discharge → `lookup_of_mem` no longer applies (build red); the
`SDup` pin is the semantic record. S4 Python `_is_pure` → name test → TK119 sweep red on exactly
`D`/`D_nested`/`SlXt`/`W3` and T2 red on `SlXt`/`D`/`D_nested`, green on `StD`/`SlXtR`.

**Cost (REASONED, from P3):** M math (the discharge reuses an existing induction), L edit
surface (~55 binder threadings, ~21 discharge sites, 2 headline regenerations, 4 new witnesses,
1 conformance module). Lean phase rebuilds every `Cascade*` module; iterate per module.

## Corrections

### Corrections 2026-10-14 (challenge)

Skeptic pass by agent `challenge-TK132`. Its probes are under
`.scratch/now-next/probes/challenge-TK132/`, which is gitignored, so load-bearing output is
quoted here. It edited nothing under `src/`, `tests/`, `formal/` or `tasks/`. **Verdict:
NEEDS-CHANGES.** The root cause, the direction (fix the model, not Python) and design L-A's
shape all hold up. But the discharge lemma as specified is false, one plausible slip has no
pin, and the headline-scope cost is understated.

**Confirmed first-hand:**
- PROBE: P4 was re-run verbatim (`IsPureT_rerun.lean`, `lake env lean`, rc=0). Its output
  is identical to §2.5, including the counterexample line `(true, true, true)`.
- PROBE: P2, P3, P5 and P6 were re-run. After CRLF normalisation each output is
  byte-identical to the scout's `.out`. P2 still shows 1 Lean-graph mismatch on each of
  `SlXt`, `SlXtR` and `StD` and 0 Python mismatches, so the 2026-08-14 class really is
  independent of `TK132`.
- READ: `Leaf.lean::isPure` L394, `boolean.py::_is_pure` L404-408, the
  `LeafRules.lean` chain at L1781/L1813/L1842/L1859, and
  `CascadeStrata.lean::reachedByW3d2_edge_source_ne_R` L1715. The `runCascade2_no_abort`
  (L1880) and `cascade2_drains` (L2049) signatures take `hterm, hNBD, hLU2` and no `hF`.
  All of these match §1 and §3.
- READ: the §7 UNVERIFIED item is resolved. `formal/headline_definitions.txt` already pins
  `ttuTargets` (L299), `directTypes` (L216) and `NodupKeys` (L128). The new definition
  rows are `ttuParentTypes` and `LeafTtuTargetsUnderived`.
- READ: P7's coverage holds. Its generator matches one-line `def X : Schema :=`, which
  finds 64 schemas. A grep finds no inline schema literal passed to `leafRewrites`,
  `persistedLeaves`, `schemaRewritesL`, `isPure`, `storageLeaves`, `rawWriteRels` or
  `keyLeafRewrites`, and no `private def … : Schema`.
- READ: C4 stands. Over `tasks/*.md`, only `P6` and `TK132` mention `computedOrDirect`, and
  `P6` is about the `Sd` vacuity, not the 2026-08-14 under-report.

**X1. The discharge lemma in §4 step 3(d) is FALSE as specified. It needs `NodupKeys S`.**
(PROBE `DupKeys.lean`, rc=0.)
- `LeafRules.lean::leafRewrites` (L122) iterates `S.defs.filter isDerived`.
  `W4Fragment.computedOrDirect` (`FullScope.lean` L364) quantifies over `S.lookup`. A
  duplicate key's second definition is invisible to `lookup` but still emits leaf rules.
- Witness `SDup` is `SlXt` with `doc#access` declared twice: first as
  `banned but not banned`, then as `viewer from parent but not banned`. Literal output:
  `computedOrDirect (over lookup) = true`, `NodupKeys = false`, the type-aware
  `leafRewrites` contains `{doc, parent, access.0, ttu "viewer"}`, and
  `LeafTtuTargetsUnderived (type-aware) = false`. Under today's name test the same carry is
  `true`.
- **Fix:** add `(hNK : NodupKeys S)` to the discharge lemma, and bridge with
  `RulesSound.lean::lookup_of_mem`. All 3 STOP sites take `hA : GraphAdmission S T`, so
  `hA.nodup` (`FullScope.lean` L214) supplies it (READ: `graph_correct` L479,
  `graph_reached_inv` L631, `LeafBridge.lean::leaf_probe_bridge` L615).
- Say in the docstring that today's leaf fact needs no `NodupKeys`
  (`LeafRules.lean` prose L1497/L1583), so this is a new premise on the discharge.
- Optional: add a permanent `decide` pin at `SDup` showing the premise is load-bearing.

**X2. Sabotage gap: a `.all` → `.any` slip over parent types is caught by NO planned pin.**
(PROBE `AnyAll.lean`, rc=0; PROBE `p_mix.py`, rc=1 by design.)
- Over all 64 named Lean schemas, `.any` differs from `.all` on exactly 1:
  `Zanzibar.T0aCounter.S` (`Spec/Counterexample.lean`), which has no allocation pin. `SlXt`
  and `StD` have single-parent tuplesets, so S1-S3 and every planned pin stay GREEN under
  `.any`.
- Witness `SMix`: `doc#parent: [folder, team]`, `team#viewer` derived, `folder#viewer`
  plain, `access: viewer from parent but not banned`.
  - Lean `.all`: `[team z→viewer.0, team y→viewer.1, doc banned→access.0]`.
  - Lean `.any`: adds `doc parent→access.0 ttu viewer`, and `banned` moves to `access.1`.
- Python as shipped compiles `SMix` with ONE `doc` closure leaf, `access.0` = `banned`. That
  equals Lean `.all`.
- With `.any` monkeypatched into `_is_pure`, Python **raises** the I5 exclusivity
  `ValueError` ("the rewrite rule from doc#parent into doc#access.0 carries a derived
  subject predicate 'viewer'"). So Python fails closed, while Lean `.any` would diverge
  silently.
- **Fix:**
  - Add a permanent pin, `lrMix_mixed_parent_drop : leafRewrites SMix = [...] := by decide`.
  - Add `SMix` to the T2 / `TK119` fixtures.
  - New sabotage S5 (`.all` → `.any`) must turn that pin red. Its Python-side control is
    "compile raises", not a leaf diff.

**X3. The headline statements get strictly NARROWER on served shapes, not just "vacuous on
`W4Fragment`".** (PROBE `ScopeD.lean`, rc=0.)
- On `SD` (= TK126 variant `D`, the mainstream idiom) and on `SlXt`, the schema-level
  premises of `runCascade2_no_abort` / `cascade2_drains` hold today. Bool twins of
  `hterm`'s `NoTtuTarget` half and of `NoBridgedDerived` are `true` on both. `hLU2` is
  vacuous: the only computed ref is `banned`, which is underived (REASONED).
- The proposed carry is `true` under today's allocation and `false` under the type-aware one,
  on both schemas.
- So after L-A, both headline statements stop covering `D`, `D_nested` and `SlXt`. Their
  nominal coverage today is coverage of a model that is not the code (§8). That is the
  honest reason to accept the loss, and it must be stated as such in the commit message,
  the `formal/history/` note and the row.
- This is an equivalence-vs-complexity call (CLAUDE.md "Who decides"). The coordinator
  should record it explicitly, with X5 in hand, rather than inherit "vacuous on
  `W4Fragment`".
- Also confirmed in Lean: `leafRewritesT SD = [doc parent→viewer.1 ttu viewer,
  doc banned→viewer.2]`, which is Python's P6 allocation.

**X4. §3.3, refined (READ + REASONED).**
- The intermediate lemma `rewriteClosureL_subject_pred_ne_of_noTtuTarget` is TYPE-BLIND: it
  concludes `u.subject.predicate ≠ R`. Under the faithful allocation it fails even for the
  WELL-typed write `doc:d1#parent@folder:f1`, whose subject `folder:f1#viewer` has
  predicate `viewer` = `R`.
- The consumer `reachedByW3d2_edge_source_ne_R` concludes the TYPED
  `a.type = dt → a.pred ≠ R`. That holds for well-typed writes (`folder ≠ team`) and fails
  only for an ill-typed one (`doc:d1#parent@team:t1`). So the scout's semantic-necessity
  claim is right for the consumer, but not for the reason the intermediate lemma breaks.
- Its `remove` arm ignores `_hty` and leans on the type-blind lemma. Any typed repair
  (L-B) must restate the lemma typed.

**X5. L-B is cheaper than §6 claims, but this is UNVERIFIED (REASONED).**
- `ReachedByW3d2.remove` already carries `hSVT : StoreValidRules S T` (`CascadeStrata.lean`,
  `inductive ReachedByW3d2`, ~L431, dated 2026-10-14).
- The write leg is a cons, so validity of `t :: T` gives `T` by tail.
- `GraphAdmission.storeValid : StoreValidRulesD S T` (`FullScope.lean` L221) is already in
  hand at every `hF` site.
- So a final-store validity premise threads by induction without §6's "store-weakening
  lambda at 22 sites".
- L-B still needs new math: a typed closure lemma, the leaf fact read off `isPure` directly
  (`(pt, tgt)` underived for `pt` in the tupleset's `directTypes`), and `ttuDirect` so
  that `parent` tuples come only from raw writes. It still moves both headline statements,
  with a store binder.
- L-B's advantage is that it loses no scope on `D` (X3). Weigh L-A against L-B
  deliberately, rather than deferring L-B to `TK133` by default.

**X6. The `TK119` 4-vs-3 count is reconciled (READ `docs/tk119-leaf-rules-differential-2026-10-14.md`
§4/§5), and the first-session correction above is wrong on the cause.**
- The 4th mismatch is `TK119`'s constructed `W3_merged_computed_ttu`
  (`viewer: (a or viewer from parent) but not c`), not a Lean witness.
- It exercises the pure-UNION merge path (`persistedLeaves` `.union` → `pureLeaves`), not
  `atomLeaves`' `.ttu` arm, and P7 cannot see it because it is not in the tree.
- Add a Lean twin of `W3` with its own `decide` pin. Both paths share `isPure`, so S1 hits
  both (REASONED), but the pin is cheap and covers the merge index arithmetic.

**X7. Minor items.**
- T2's leaf-row filter must test the OBJECT predicate only, because a BARE subject
  predicate `...` also contains `.` (REASONED).
- READ: Lean `ttuParentTypes`' `none => []` arm (vacuously pure) matches `_is_pure` on an
  undeclared tupleset, where `_member_types` returns the empty set and `all()` is True.
  Python additionally refuses that shape through the I5 guards
  (`tests/test_tk126_ttu_target_name_collision.py::test_undeclared_tupleset_falls_back_to_the_name_test`).
  That is outside the parse domain, so it does not affect fidelity.

- **2026-10-14 (same session, after §7 was written):** collision C1 is already handled on
  the `TK119` side (READ `docs/tk119-leaf-rules-differential-2026-10-14.md`, written by a
  parallel scout).
  - Its plan carries `D` / `D_nested` / `SlXt` in a `corpus.py` dict kept out of
    `_FAMILIES`, with an `_TK132_EXPECTED` positive pin. It reports 4 mismatching sources in
    its dry run.
  - It tells `TK132`'s builder to delete the `_TK132_EXPECTED` entries in the same commit.
  - So if `TK119` lands first, `TK132`'s step 10 / T2 acceptance becomes "the
    `_TK132_EXPECTED` set empties and the leaf-rules differential is green". T2's leaf-row
    graph-state test is then optional, kept only as a second, independent instrument.
  - The difference between its 4 and P5's 3 (P5 swept only Python compiles, while `TK119`
    also counts a Lean witness) was not reconciled here. UNVERIFIED.

## 0. Headline (read this first)

1. **The row's sizing premise is wrong. The fix is NOT "re-plumbing, not new math".**
   - The leaf half of a proved lemma depends on the name test (PROBE P4, READ §2.2):
     `GraphIndex/LeafRules.lean::ttuTargetsSatL_ne_of_noTtuTarget` gets `tr ≠ R` on the leaf
     layer from exactly that test.
   - Under a type-aware `isPure` the lemma is **false as stated**, and `LeafRuleWitness.SlXt`
     is the counterexample, checked in Lean (§3, P4).
   - The lemma feeds two **headline-pinned** statements, `runCascade2_no_abort` and
     `cascade2_drains` (P3). So any faithful fix adds a premise to those two statements.
   - The premise is needed for semantic reasons, not just to make the proof go through
     (REASONED §3.3). The `ReachedByW3d2` chain does not constrain a written tupleset
     tuple's subject type. Under the faithful allocation, a leaf TTU rule can therefore put an
     edge source on a derived node.
2. **The Python is right; the model is out of date** (PROBE P1/P2/P6):
   - On `SlXt` and on TK126 variant `D`, the Python graph index agrees with the oracle on
     every grid query (0 mismatches).
   - The Lean model allocates leaves differently from Python on those shapes. The
     graph-state leaf rows differ (P1, P6).
3. **The gap reaches a mainstream idiom, not only the exotic `SlXt`** (PROBE P5). Variant `D`
   is `define viewer: ([user] or viewer from parent) but not banned` with `folder#viewer`
   plain, i.e. the ordinary "inherit from parent, minus a ban" shape. Python allocates
   `viewer.0/1/2`; the model allocates `viewer.0/1`.
4. **Fixing `isPure` alone does NOT make Lean's `graph` mode answer these shapes right**
   (PROBE P2). Every `.ttu`-inside-a-derived-def shape gets one wrong answer from the Lean
   operational model, including the no-collision control `SlXtR` and `StD`.
   - That is the separate, already-recorded 2026-08-14 fail-closed finding
     (`formal/CORRESPONDENCE.md` §0, the "There is no rc for out of the proved fragment"
     note). It lies outside `W4Fragment.computedOrDirect` and is NOT in `TK132`'s scope.
   - What `TK132` fixes is the **leaf allocation** (rules and leaf rows).
5. **Recommendation (§6): design L-A.**
   - Make `isPure`'s `.ttu` arm test the tupleset's parent types, as `exprRefs` does.
   - Add ONE decidable schema-level carry, `LeafTtuTargetsUnderived S`. It is the old
     lemma's conclusion promoted to an explicit premise, and it is discharged from
     `W4Fragment.computedOrDirect` by one induction lemma.
   - Thread it beside `hNBD` (52 of the 66 affected declarations already thread `hNBD`).
   - Regenerate the two headline statements deliberately.
   - Size REASONED: **M in math, L in edit surface** (about 70 declarations across about 15
     files, mostly one binder plus one argument each).

## 1. The two sides, exactly

### 1.1 Lean (READ)

- `formal/lean/ZanzibarProofs/GraphIndex/Leaf.lean::derivedAnywhere` (L376):
  `S.keys.any (fun k => k.2 == R && isDerived S k)`. This is a type-agnostic NAME test.
- `formal/lean/ZanzibarProofs/GraphIndex/Leaf.lean::isPure` (L391-397), the `.ttu` arm (L394):
  `| .ttu tgt ts => !isDerived S (ty, ts) && !derivedAnywhere S tgt`.
- Consumers of `isPure` that decide allocation:
  - `Leaf.lean::atomLeaves`, `.ttu` arm (L435). It emits `.closure (.ttu tgt ts)` only
    under `isPure`.
  - `Leaf.lean::persistedLeaves`, `.union` arm (pure-union merge).
  - Through those, `GraphIndex/LeafRules.lean::keyLeafRewrites` (L114),
    `::leafRewrites` (L122) and `::schemaRewritesL` (L130).
  - These are the rules the operational model writes with (`rewriteClosureL`).
- `GraphIndex/Leaf.lean::isPure` is mentioned on 13 lines of `Leaf.lean`, 99 of
  `LeafRules.lean`, 9 of `CascadeStable.lean`, 12 of `CascadeStrataSettle.lean`, 4 of
  `LeafBridge.lean` and 1 of `Audit.lean` (READ, `grep -c` over `isPure|derivedAnywhere`,
  2026-10-14).
  - The CascadeStrataSettle and LeafBridge hits are `rw [isPure]` / `by_cases` on the
    `.direct` / `.union` arms. A `.ttu`-arm change does not touch them (REASONED).
- The type-aware parent-type computation **already exists** in Lean:
  `formal/lean/ZanzibarProofs/Spec/Stratify.lean::exprRefs` (L37-47), `.ttu` case:
  `(t, ts) :: (match S.lookup (t, ts) with | some e => (directTypes e).map (fun pt => (pt, tr)) | none => [])`,
  with `Spec/Stratify.lean::directTypes` (L28). So the Lean TAINT is already type-aware, and
  only the PURITY test is not.

### 1.2 Python (READ)

- `src/zanzibar/schema/boolean.py::_is_pure`, `TTU` branch:
  `all((t, expr.target_rel) not in tainted for t in _member_types(object_type, expr.tupleset_rel, ast, frozenset()))`.
  It has no tupleset-taint conjunct (comment: "a tupleset is never tainted ... (TK107)").
- `src/zanzibar/schema/boolean.py::_member_types` returns bare (`predicate == '...'`)
  restriction types of the tupleset relation. It recurses through Computed/TTU/both
  Exclusion arms, but a tupleset is direct-only since `TK106`, so on a checked parse it is
  just the restriction types.
  - A wildcard restriction `[folder:*]` parses to `Restriction(type='folder', predicate='...', wildcard=True)`
    and so IS counted (PROBE, one-liner, 2026-10-14).
- `src/zanzibar/schema/boolean.py::_mentions` uses the same `_member_types`. Taint and
  purity therefore read the same parent types, which is the twin of Lean's
  `exprRefs`/`directTypes` pairing.

### 1.3 Do `directTypes` (Lean) and `_member_types` (Python) agree? (REASONED)

- **They agree on every schema Python parses.**
  - Both parsers refuse a non-direct tupleset (`TK106`,
    `parser.py::_validate_tuplesets_direct`) and a userset-restricted tupleset (`TK108`).
  - On the remaining shapes, both functions return the restriction types, wildcards
    included.
- **They differ only off the parse domain.**
  - A Lean schema with `parent: [folder#member]` gets `folder` from `directTypes`, which
    Python's `_member_types` would drop. Python refuses that schema at parse.
  - Lean's `GraphAdmission.ttuDirect` (`GraphIndex/RulesCorrect.lean::TtuTuplesetsDirect`,
    L184: tupleset defs are `directsOnly`) covers the direct-only half, not the userset half.
  - This does not affect fidelity, because a schema Python refuses has no Python allocation
    to be faithful to.
- **The extra Lean conjunct `!isDerived S (ty, ts)` (tupleset not tainted) is harmless.** It
  is always true on parsed schemas: a direct-only, bare-only def mentions nothing, so it is
  never tainted. Keep it, because sabotage S14 in `LeafRules.lean` is built on the two
  adjacent conjuncts.

## 2. Measurements

### 2.1 P1: `SlXt` through every channel (PROBE `p1_slxt.py`)

Schema `SlXt` (the Lean witness `GraphIndex/LeafRules.lean::SlXt`, L2632, written as DSL;
identical to `tests/test_tk126_ttu_target_name_collision.py::SLXT`):

```text
type user
type team    relations: z: [user]; y: [user]; viewer: z but not y
type folder  relations: viewer: [user]
type doc     relations: parent: [folder]; banned: [user]; access: viewer from parent but not banned
```

Tuples: `folder:f1#viewer@user:alice`, `doc:d1#parent@folder:f1`, `doc:d2#parent@folder:f1`,
`doc:d2#banned@user:alice`, `team:t1#z@user:bob`. Literal output:

```text
PY leaf families (doc#access.*):
   ('doc', 'access.0') 0 True closure
   ('doc', 'access.1') 1 False closure
   ('team', 'viewer.0') 0 True closure
   ('team', 'viewer.1') 1 False closure
ORACLE: [True, False, False, True, True]
LEAN spec: [True, False, False, True, True]
LEAN graph: [False, False, False, True, True]
LEAN fragment rc 0 {"admission":{"admitted":true,...},"failures":["computedOrDirect"],...,"inFragment":false,"inPremise":false,...}
STATE DIFF:
  edge only in LEAN model : ('user', 'alice', '...', '') -> ('doc', 'd2', 'access.0', '')
  edge only in PYTHON     : ('folder', 'f1', 'viewer', '') -> ('doc', 'd1', 'access.0', '')
  edge only in PYTHON     : ('folder', 'f1', 'viewer', '') -> ('doc', 'd2', 'access.0', '')
  edge only in PYTHON     : ('user', 'alice', '...', '') -> ('doc', 'd1', 'access', '')
  edge only in PYTHON     : ('user', 'alice', '...', '') -> ('doc', 'd2', 'access.1', '')
  residue only in PYTHON     : ('doc', 'd1', 'access') = (frozenset(), frozenset(), frozenset({('folder', 'f1', 'viewer')}))
  residue only in PYTHON     : ('doc', 'd2', 'access') = (frozenset(), frozenset(), frozenset({('folder', 'f1', 'viewer')}))
```

Queries are `[alice access d1, alice access d2, bob access d1, bob viewer t1, alice viewer f1]`.

- `SlXt` is `GraphAdmission`-admitted but outside `W4Fragment`, failing only
  `computedOrDirect`. So **no headline theorem reaches it**, and the gap is invisible to
  every proof today. That matches the row's "dead inside `W4Fragment`".
- **The observable consequence of the `isPure` gap specifically is the leaf rows.**
  - In Lean, `banned` lands on `access.0`.
  - In Python, the TTU closure lands on `access.0` and `banned` on `access.1`.
  - The public-edge and residue rows are the separate 2026-08-14 class (P2).

### 2.2 P2: the family, over the full query grid (PROBE `p2_family.py`)

The grid is every `user × declared relation × object`.

- `SlXtR` is `SlXt` with `team#viewer` renamed `tviewer`, i.e. no name collision. There
  Lean's `isPure` already agrees with Python.
- `StD` is `Leaf.lean::LeafWitness.StD` (L1112): the target is derived on the ADMITTED type,
  and both sides treat the arm as impure.

```text
== SlXt: 30 queries   spec==oracle: True
  LEAN graph mismatches vs oracle: 1   (('...','user','alice','access','doc','d1'), True, False)
  PY graph mismatches vs oracle: 0
  STATE DIFF: 4 leaf-row edges + 1 public edge + 2 residues (as P1)
== SlXtR: 30 queries  spec==oracle: True
  LEAN graph mismatches vs oracle: 1   (('...','user','alice','access','doc','d1'), True, False)
  PY graph mismatches vs oracle: 0
  STATE DIFF:
  edge only in PYTHON     : ('user', 'alice', '...', '') -> ('doc', 'd1', 'access', '')
  residue only in PYTHON  : ('doc', 'd1', 'access') = (..., {('folder', 'f1', 'viewer')})
  residue only in PYTHON  : ('doc', 'd2', 'access') = (..., {('folder', 'f1', 'viewer')})
== StD: 27 queries    spec==oracle: True
  LEAN graph mismatches vs oracle: 1   (('...','user','alice','access','doc','d1'), True, False)
  PY graph mismatches vs oracle: 0
  STATE DIFF: (same 1 public edge + 2 residues as SlXtR)
```

- **Attribution (REASONED from P1 vs P2):**
  - On `SlXtR`, where both purity tests agree, the leaf rows already match Python. Only the
    public edge and residues differ, and that is the known 2026-08-14 under-report.
  - So after the `TK132` fix, `SlXt`'s state diff should shrink to exactly `SlXtR`'s. That
    is a measurable acceptance criterion (§5, test T2).
  - The Lean `graph` ANSWER on these shapes stays wrong after `TK132` (the one mismatch
    above). That is in scope of a different item, not this one (§7).
- **Python vs oracle, as required by CLAUDE.md "Who decides":** 0 mismatches on all three.
  The broader TK126 differential evidence is in
  `tests/test_tk126_ttu_target_name_collision.py`. That covers ParityEngine 4-way, the
  `ConnectedStore`/`build_index` paths and the lookup surfaces, for the `SERVED` dict, which
  includes `SlXt` (READ). So the Python is right, and the model is what needs fixing.

### 2.3 P5: where the purity test decides anything (PROBE `p5_corpus_sweep.py`)

Each schema is compiled once as shipped, and once with `_is_pure`'s TTU arm monkeypatched
to the Lean NAME test (`any(rel == target for (_t, rel) in tainted)`). The sample is 50
schemas: every `formal/conformance/corpus.py::SCHEMAS` entry, every
`tests/fga_schemas/*.fga`, and every `tests/test_tk126_ttu_target_name_collision.py::SERVED`
variant. Literal output:

```text
tk126:D DIFFERS:
   shipped leaves [(('doc', 'viewer.0'), 0, 'closure'), (('doc', 'viewer.1'), 1, 'closure'), (('doc', 'viewer.2'), 2, 'closure')]
   name    leaves [(('doc', 'viewer.0'), 0, 'closure'), (('doc', 'viewer.1'), 1, 'closure')]
tk126:D_nested DIFFERS:  (same viewer.0/1/2 vs viewer.0/1)
tk126:SlXt DIFFERS:
   shipped leaves [(('doc','access.0'),0,'closure'), (('doc','access.1'),1,'closure'), (('team','viewer.0'),0,'closure'), (('team','viewer.1'),1,'closure')]
   name    leaves [(('doc','access.0'),0,'closure'), (('team','viewer.0'),0,'closure'), (('team','viewer.1'),1,'closure')]
TOTAL 50: SAME 47, DIFFERS 3, compile-raised (skipped) 0
```

- **The conformance corpus contains ZERO schemas where the two tests differ.**
  - Today's conformance gates therefore cannot see this gap.
  - `TK119`'s planned leaf-rules differential runs "over the conformance corpus", so it will
    NOT go red on this gap unless `D` / `D_nested` / `SlXt` are added to its fixture list on
    purpose (§7, collision C1).
- B and C (the untainted-container variants) do not differ. Their TTU sits in an untainted
  def, so no plan tree is built.
- The monkeypatch is a live instrument: it moved 3 schemas, so a constant patch is ruled out.

### 2.4 P6: variant `D`, the mainstream idiom (PROBE `p6_variant_d.py`)

`D`: `doc#viewer: ([user] or viewer from parent) but not banned`, `doc#parent: [folder]`,
`folder#viewer: [user]`. Tuples: `folder:f1#viewer@alice`, `doc:d1/d2#parent@folder:f1`,
`doc:d2#banned@alice`, `doc:d1#viewer@bob`.

```text
== D: 21 queries   spec==oracle: True
  LEAN graph mismatches vs oracle: 1   (('...','user','alice','viewer','doc','d1'), True, False)
  PY graph mismatches vs oracle: 0
  STATE DIFF:
  edge only in LEAN model : ('user', 'alice', '...', '') -> ('doc', 'd2', 'viewer.1', '')
  edge only in PYTHON     : ('folder', 'f1', 'viewer', '') -> ('doc', 'd1', 'viewer.1', '')
  edge only in PYTHON     : ('folder', 'f1', 'viewer', '') -> ('doc', 'd2', 'viewer.1', '')
  edge only in PYTHON     : ('user', 'alice', '...', '') -> ('doc', 'd1', 'viewer', '')
  edge only in PYTHON     : ('user', 'alice', '...', '') -> ('doc', 'd2', 'viewer.2', '')
  residue only in PYTHON  : ('doc', 'd1', 'viewer') = (..., {('folder', 'f1', 'viewer')})
  residue only in PYTHON  : ('doc', 'd2', 'viewer') = (..., {('folder', 'f1', 'viewer')})
```

In Lean, `banned` lands on `viewer.1`. In Python, the TTU closure lands on `viewer.1` and
`banned` on `viewer.2`.

### 2.5 P4 + P7: the proposed definition, evaluated in Lean without touching the tree

These probes are `IsPureT.lean` and `IsPureT_sweep.lean`, run with `lake env lean`, rc=0.

The candidate, verbatim. It is a local copy of the allocation with ONE change in `isPureT`'s
`.ttu` arm; `atomLeavesT` / `persistedLeavesT` / `unionSpineLeavesT` / `keyLeafRewritesT` /
`leafRewritesT` are the shipped bodies with `isPure` replaced by `isPureT`:

```lean
def ttuParentTypes (S : Schema) (ty ts : String) : List String :=
  match S.lookup (ty, ts) with
  | some e => directTypes e
  | none => []

def isPureT (S : Schema) (ty : String) : Expr → Bool
  | .direct rs  => rs.all (fun r => !isTaintedUserset S r)
  | .computed R => !isDerived S (ty, R)
  | .ttu tgt ts => !isDerived S (ty, ts) && (ttuParentTypes S ty ts).all (fun pt => !isDerived S (pt, tgt))
  | .union a b  => isPureT S ty a && isPureT S ty b
  | .inter _ _  => false
  | .excl _ _   => false
```

P4 literal output (abridged to the rule lists):

```text
("SlXt  name-test",  [team z->viewer.0 computed, team y->viewer.1 computed, doc banned->access.0 computed])
("SlXt  type-aware", [team z->viewer.0 computed, team y->viewer.1 computed,
                      { objectType := "doc", matchRel := "parent", outRel := "access.0", kind := Zanzibar.RuleKind.ttu "viewer" },
                      { objectType := "doc", matchRel := "banned", outRel := "access.1", kind := Zanzibar.RuleKind.computed }])
("StD   name-test",  [folder e->viewer.0, folder b->viewer.1, doc banned->access.0])
("StD   type-aware", [folder e->viewer.0, folder b->viewer.1, doc banned->access.0])
("SnlBoth equal?", true)
("SlV equal?", true)
("counterexample at SlXt, R=viewer, dt=team", true, true, true)
```

- **The type-aware `SlXt` allocation equals Python's** (`access.0` = TTU closure,
  `access.1` = `banned`), and so does `StD`'s.
- **The last line is the counterexample** to `ttuTargetsSatL_ne_of_noTtuTarget` under the
  faithful model. Its three components:
  1. The untainted layer carries no TTU rule targeting `viewer`, so `hnt` holds.
  2. `isDerived SlXt ("team","viewer")` holds, so `hder` holds.
  3. The faithful leaf layer DOES carry a `.ttu "viewer"` rule, so
     `TtuTargetsSatL SlXt (· ≠ "viewer")` fails.

P7 compared `leafRewrites` with `leafRewritesT` on all 64 `def _ : Schema` in the Lean tree
(fully qualified, generated by `p7_gen_sweep.py`): **63 equal, 1 differs, and it is
`Zanzibar.LeafRuleWitness.SlXt`**. So the only `decide` pins over allocation that move are
the `SlXt` ones (§4, step 6).

## 3. Why the proof needs a new premise (READ + REASONED)

### 3.1 The dependency the row missed (READ)

`GraphIndex/LeafRules.lean`, section "Obligation (A)'s PREMISE — DISCHARGED, not assumed"
(prose L1440-1600). Its chain:

1. `::derivedAnywhere_eq_false_of_mem_exprArms_of_isPure` (L1781) reads `hp.2`, the
   `!derivedAnywhere S tgt` conjunct of `isPure`'s `.ttu` arm.
2. `::derivedAnywhere_eq_false_of_mem_leafRewrites` (L1813) concludes that every leaf rule's
   TTU target is derived NOWHERE.
3. `::ttuTargetsSatL_ne_of_noTtuTarget` (L1842) closes the leaf arm by a `Bool` collision
   with `::derivedAnywhere_of_isDerived hder` (L1610).
4. `::rewriteClosureL_subject_pred_ne_of_noTtuTarget` (L1859) consumes step 3.

Under a type-aware `.ttu` arm, step 1's conclusion weakens. The target is underived only on
the tupleset's parent types, so steps 2 and 3 are false as stated (P4 counterexample).

### 3.2 Who consumes it (PROBE P3, `p3_callers.py`)

This is the reverse whole-word reference closure from the three lemmas in §3.1, with
comments stripped. It stops at a declaration whose signature mentions `W4Fragment`, because
such a declaration can discharge a new carry locally.

```text
closure 69 stops(W4Fragment in sig) 3 carriers 66
carriers by file [Equiv 6, FullScope 6, Cascade 5, CascadeEnum 6, CascadeInv 2, CascadeSettle 4,
  CascadeStable 5, CascadeStrata 4, CascadeStrataAssemble 4, CascadeStrataEdge 3, CascadeStrataEnum 2,
  CascadeStrataResettle 7, CascadeStrataSettle 6, LeafRules 6]
STOPS: ['graph_correct', 'graph_reached_inv', 'leaf_probe_bridge']
carriers with NoBridgedDerived in signature: 52
carriers WITHOUT NoBridgedDerived: correct_applies, correct_applies_nonfence, coverage_applies,
  derivedAnywhere_eq_false_of_mem_leafRewrites(_nonvacuous), rewriteClosureL_subject_pred_ne_of_noTtuTarget(_nonvacuous),
  toC_applies, ttuTargetsSatL_ne_of_noTtuTarget, ttuTargetsSatL_snlBoth_ne_access_manufactured,
  w3d2E_correct_applies(_nonfence), writeLegSubjectsWide_L, writeLegSubjectsWide_L_snlBoth
```

The closure is an over-approximation, because a name match is not necessarily a use.

The direct consumers (READ):
- `GraphIndex/Cascade.lean::reachedByW3d_edge_source_ne_R` (L2153, call at L2170)
- `GraphIndex/CascadeStrata.lean::reachedByW3d2_edge_source_ne_R` (L1715; two calls, write
  and remove arms)
- `GraphIndex/CascadeStable.lean::writeLegSubjectsWide_L` (L3520). It is called from
  `CascadeStable.lean::reachedByW3d_shadow` (L3671) and from `CascadeStrataSettle.lean` at
  L919, L1691 and L1747, plus the witnesses at L4822 and L4922.

Headline-pinned carriers (cross-checked against `formal/headline_statements.txt`):
- `Zanzibar.runCascade2_no_abort` and `Zanzibar.cascade2_drains`. Both take `hterm`,
  `hNBD : NoBridgedDerived S` and `hLU2`, **not** `hF`. The path is
  `runCascade2_no_abort` → `CascadeStrata.lean::reachedByW3d2_Rnode_not_source` (call at
  L1931) → `reachedByW3d2_edge_source_ne_R` → §3.1. **Their statements must change.**
- `Zanzibar.W4WitnessDirect.{correct_applies, correct_applies_nonfence, coverage_applies, toC_applies, w3d2E_correct_applies, w3d2E_correct_applies_nonfence}`
  are concrete (`Sd`/`Td`). Their statements do not mention the premise, so the pins do not
  move; only the proofs gain a `by decide` discharge.

### 3.3 The premise is needed semantically, not just to repair the proof (REASONED)

- `ReachedByW3d2.write` (pinned definition, `formal/headline_definitions.txt` row
  `def:Zanzibar.ReachedByW3d2`) takes only
  `hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t))`. That is EDGE
  admission. Nothing in the chain says a stored `doc:d1#parent` tuple's subject type is one
  of `parent`'s declared types.
- Concretely, under the faithful allocation on `SlXt`, the chain admits writing
  `doc:d1#parent@team:t1`. The leaf rule `⟨doc, parent, access.0, .ttu "viewer"⟩` then emits
  `team:t1#viewer → doc:d1#access.0`. That edge is sourced at the DERIVED node
  `(team, viewer)`, so `reachedByW3d2_edge_source_ne_R`'s conclusion fails for
  `dt = team`, `R = viewer`.
  - Python refuses that write: `RuleSet.apply` raises on an undeclared restriction (the
    `matchDecl` admission).
  - The model's chain does not refuse it.
- So either a schema-level carry or a store-level declaredness premise is NECESSARY. UNVERIFIED:
  whether the headline conclusion of `runCascade2_no_abort` itself fails on such a run, or
  only its internal lemma. Either way the proof cannot go through unchanged.

## 4. The plan: design L-A (recommended), as numbered steps

**Name choices are suggestions. The builder decides and records the choice on the row.**

1. **The def (Leaf.lean).**
   - Add `ttuParentTypes` (as in §2.5) next to `derivedAnywhere`, citing
     `Spec/Stratify.lean::exprRefs` as its twin.
   - Change `isPure`'s `.ttu` arm (L394) to the `isPureT` arm.
   - Keep `derivedAnywhere`, because the carry in step 3 uses it.
   - Rewrite the `derivedAnywhere` section header (L326-352) and the
     `derivedAnywhere` / `isPure` docstrings. The ★/⚠ paragraphs become dated history with a
     one-line "fixed by `TK132`, 2026-10-xx" note. Do not delete the history.
   - `statement_pin.py::strip_comments` strips comments, so docstrings move no pin (READ in
     the TK126 doc's Corrections).
2. **The purity lemma family (LeafRules.lean).**
   - `isPure_of_mem_splitPure_snd`, `isPure_foldl_union`, `isPure_of_unionAll`,
     `isPure_of_closure_mem_pureLeaves`, `isPure_of_closure_mem_atomLeaves`,
     `isPure_closure_persistedLeaves_and_spine` and `isPure_of_closure_mem_persistedLeaves`
     are all generic in the `.ttu` arm's content.
   - They `rw [isPure]` and split `&&`, so they should re-check unchanged. `simp [isPure, hnd]`
     at `isPure_of_closure_mem_atomLeaves` (~L1702) is the one to watch. REASONED, not built.
3. **The carry (LeafRules.lean, section `ObligationAPremise`).**
   - (a) `def LeafTtuTargetsUnderived (S : Schema) : Prop := ∀ r ∈ leafRewrites S, ∀ tr ∈ ttuTargets r, derivedAnywhere S tr = false`,
     with a `Decidable` instance. It is a `∀` over a computed list, like `NoLeafSubjects`, so
     concrete sites discharge it `by decide`.
   - (b) Restate `ttuTargetsSatL_ne_of_noTtuTarget` and
     `rewriteClosureL_subject_pred_ne_of_noTtuTarget` with
     `(hLTU : LeafTtuTargetsUnderived S)` after `hder`. The leaf arm becomes
     `hLTU r hr tr htr` in place of `derivedAnywhere_eq_false_of_mem_leafRewrites hr tr htr`.
   - (c) **Delete** `derivedAnywhere_eq_false_of_mem_leafRewrites` and
     `derivedAnywhere_eq_false_of_mem_exprArms_of_isPure`, or rename them to a type-aware
     statement if one is wanted (none is consumed). Their `_nonvacuous` witness (L2691)
     becomes `leafTtuTargetsUnderived_snlBoth : LeafTtuTargetsUnderived SnlBoth := by decide`.
   - (d) **The discharge lemma** is
     `leafTtuTargetsUnderived_of_computedOrDirect : (∀ dt R e, S.lookup (dt, R) = some e → isDerived S (dt, R) = true → ComputedOrDirect e) → LeafTtuTargetsUnderived S`.
     It is the one piece of new math, an induction of the same shape as
     `isPure_closure_persistedLeaves_and_spine` (~40 lines). It shows:
     - every `.closure sub` of `persistedLeaves S ty e` is a `.ttu`-free subterm when
       `ComputedOrDirect e` holds;
     - `exprArms` over a `.ttu`-free expr emits no `.ttu` rule;
     - so `ttuTargets r = []` and the carry holds vacuously.
   - `ComputedOrDirect` lives in `GraphIndex/ReconcileCorrect.lean` (L145: `.ttu _ _ => False`).
     `LeafRules.lean` does not import it today. The L1440 prose records that the import is
     legal (cycle-checked 2026-09-05; UNVERIFIED today). Alternatively, put the lemma in
     `FullScope.lean` as `W4Fragment.leafTtuTargetsUnderived`, next to
     `GraphAdmission.noBridgedDerived` (L288), and keep only the def in `LeafRules.lean`.
4. **Thread the carry.** Put `hLTU` immediately after `hNBD` at every one of the 52
   `hNBD`-threaded carriers (P3).
   - This follows the `Cascade.lean::reachedByW3d_edge_source_ne_R` docstring's rule:
     "put the carry immediately after `hRne` ... so the argument position stays uniform". Use
     the same discipline with the new carry right after `hNBD`.
   - Add it to `writeLegSubjectsWide_L` (+ the witness `writeLegSubjectsWide_L_snlBoth`).
   - Discharge at the `hF`-holding sites: the 3 STOPS, plus the 18 existing
     `.noBridgedDerived` discharge sites as the likely co-sites (READ count, `grep -c`).
5. **The headline statements.** Add `(hLTU : LeafTtuTargetsUnderived S)` after `hNBD` in
   `CascadeStrata.lean::runCascade2_no_abort` (L1880) and `::cascade2_drains` (L2049).
   - Update their 5 call sites: `CascadeStrata.lean:2063`, `CascadeStrataResettle.lean:940`,
     `:1364`, `:2189` and `:2510`.
   - Regenerate with `formal/conformance/statement_pin.py --generate`. Say why in the commit
     message and in a `formal/history/` note: the claim gains an explicit carry that the
     model's honest allocation needs, and that is vacuous on `W4Fragment`.
6. **Witnesses (LeafRules.lean).**
   - `SlXt` docstring: drop "a MODEL-level probe ... Python refuses". It is now a CORPUS-class
     shape that Python serves.
   - **Invert** `lrXt_cross_type_drop` (L2649) into, for example, `lrXt_cross_type_kept`, with
     the P4 literal rule list (4 rules: `access.0` = `.ttu "viewer"` over `parent`,
     `access.1` = `banned`).
   - Keep `slXt_viewer_derived_anywhere` and `slXt_viewer_untainted_on_folder`, which are
     still true.
   - **Add the load-bearing refutation** as a permanent `decide` pin, the twin of
     `hder_load_bearing` (L2667):
     `hLTU_load_bearing : (∀ r ∈ schemaRewrites SlXt, ∀ tr, r.kind = RuleKind.ttu tr → tr ≠ "viewer") ∧ isDerived SlXt ("team","viewer") = true ∧ ¬ TtuTargetsSatL SlXt (· ≠ "viewer")`.
     This is P4's counterexample line made permanent, and it proves the carry is a premise
     and not decoration.
   - Update the attack prose (L1092-1110, L1456-1505) to say the cross-type arm is now KEPT,
     and that the leaf-layer fact is a carry, not a theorem.
   - `lrStD_no_ttu_rule` (L2607) and `Leaf.lean::stD_leaves` (L1120) are unchanged (P4/P7).
7. **Audit.** Add `#print axioms` for the discharge lemma, `hLTU_load_bearing` and the
   inverted pin in `Audit.lean`. Adding to `formal/audited_theorems.txt` is free (superset
   rule, READ in its header). `isPure` stays audited (`Audit.lean:1918`).
8. **CORRESPONDENCE.md.**
   - §4 `isPure` row: replace the two ⚠ history sentences with "the `.ttu` arm tests the
     tupleset's parent types (`Leaf.lean::ttuParentTypes`), the twin of `boolean.py::_is_pure`
     over `_member_types`". Keep the dated history sentence.
   - §7.1: close the `TK126` entry with a dated "FIXED by `TK132`" line. Per §8 discipline,
     keep it as history rather than deleting it.
   - Add a row or anchor for `GraphIndex/LeafRules.lean::LeafTtuTargetsUnderived` as an
     HONEST carry (Python imposes nothing; vacuous on `W4Fragment`).
   - `anchor_check.py` resolves every new `file::symbol`. Avoid writing an uncited ratio (for
     example "63/64"): `claim_rot.py` flags uncited ratios. Cite the test or omit the number.
9. **Python side: no product change.**
   - Re-document
     `tests/test_tk126_ttu_target_name_collision.py::test_slxt_python_allocation_is_the_recorded_gap`.
     Its assertion is Python's allocation, which is unchanged. Rename it, for example to
     `test_slxt_python_allocation_matches_the_model`, and drop "recorded gap" from the
     `SLXT` comment.
   - `src/zanzibar/schema/reports.py::w4_fragment_report` is unchanged, because
     `W4Fragment`'s fields are unchanged.
   - `tests/snapshots/` is unchanged, because Python compilation is unchanged.
10. **Tests (§5)**, then the full gate (all 10 phases). Fuzz is not required, because this
    is not a Python algorithm change. The Lean `lean` phase rebuilds nearly the whole tree,
    since `Leaf.lean` is upstream of every `Cascade*`.

## 5. Tests to add, each with its sabotage

The sabotages follow `docs/sabotage-procedure.md`: the narrowest plausible weakening,
instrument controlled.

- **T1 (Lean, permanent `decide` pins).**
  - The pins are `lrXt_cross_type_kept` and `hLTU_load_bearing` (§4, step 6).
  - **S1: revert `isPure`'s `.ttu` arm to `!derivedAnywhere S tgt`.** `lrXt_cross_type_kept`
    fails to elaborate (`decide` evaluates to false), so `lake build` goes red.
    `hLTU_load_bearing`'s third conjunct also flips (the leaf layer has no `viewer` rule).
  - **S2, the narrowest plausible slip: the SAME-type test `!isDerived S (ty, tgt)`.** It
    keeps `StD`'s arm, where Python drops it, so `lrStD_no_ttu_rule` / `stD_leaves` go red.
  - **S3: read parent types off the CONTAINER def instead of the tupleset def.** `doc#access`
    has no direct types, so the `all` over `[]` is vacuous-true and `StD` keeps the arm.
    Again `lrStD_no_ttu_rule` goes red.
  - Record the literal `lake build` error in the docstring.
- **T2 (conformance, the leaf-row projection of graph-state).** A new
  `formal/conformance/test_conformance_tk132_leaf_rows.py`, or the same fixtures as cases in
  `TK119`'s `test_conformance_leaf_rules.py` if that lands first (§7, C1).
  - Fixtures: `SlXt`, `D`, `D_nested` (where the two tests differ) plus `StD` and `SlXtR` as
    controls.
  - Compare Lean `graph-state` and Python `graph-state` RESTRICTED to edges whose object
    predicate is a leaf name (contains `.`). Assert EQUAL.
  - Separately, **positive-pin** (never xfail) that the remaining public-edge/residue diff is
    exactly the 2026-08-14 `.ttu`-in-derived-def set. P2/P6 give the literal rows. If that
    item is ever fixed, the pin fails loudly and gets re-adjudicated.
  - Non-vacuity: assert each fixture produced ≥1 leaf-row edge on both sides.
  - **S4 (Python-side instrument control): monkeypatch `boolean.py::_is_pure`'s TTU arm to
    the name test** (P5's `name_test_is_pure`). Python then allocates like the OLD model:
    T2 goes red on `SlXt`, `D` and `D_nested` and stays green on `StD` and `SlXtR`. P5
    measured exactly those three schemas as moving, so the expected red set is known in
    advance.
  - **S1 reused at this level:** on the unfixed Lean tree, T2 is red on those three. That
    is the before-state evidence and should be written down before the fix (P1/P6 are its
    preview).
- **T3 (Python, keep):** the re-documented `test_slxt_python_allocation_*` (§4, step 9). No
  new sabotage is needed; it already pins the Python half.

## 6. Options weighed

| | Design | Lean cost | Headline statement pins | Scope gain | Verdict |
|---|---|---|---|---|---|
| **L-A** | Type-aware `isPure` + schema-level carry `LeafTtuTargetsUnderived`, discharged from `computedOrDirect` | 1 def + 1 helper; 1 new induction lemma (~40 lines); 4 lemmas restated; ~52 binder threadings beside `hNBD`; ~18-21 discharge sites; 3 witness edits (P3; REASONED) | `runCascade2_no_abort`, `cascade2_drains` gain one binder | none at headline level (still gated by `computedOrDirect`); model faithful | **RECOMMENDED** |
| L-B | Type-aware `isPure` + a STORE-level declaredness premise (`StoreDeclared`-shape) and a type-aware closure lemma (the leaf TTU subject's type is in `directTypes` of the tupleset def, and `(pt, tgt)` is underived) | New math in the closure lemma; a store-indexed premise needs weakening at every `T.erase t` / `t :: T` leg (the `term`-style pain: "a two-line store-weakening lambda at 22" sites, `Cascade.lean` docstring); `cascade2_drains` has no store-validity premise today | same two, with a store-level binder | proves the cascade lemmas for `SlXt`-class stores | Defer: this is the natural first leg of `TK133` (type-aware `term`, SOMEDAY) |
| L-0 | Keep the name test; leave the §7.1 entry recorded | 0 | 0 | — | Rejected: it contradicts the row's goal and CORRESPONDENCE §8 ("a proof that describes something other than the shipped code") |
| P-1 | Change PYTHON's `_is_pure` to the name test, matching the model | Python allocation changes on served `D`/`D_nested`/`SlXt` (P5) | 0 | — | **Rejected.** (1) Python already matches the oracle (P2/P6), and the rule is to fix the model, not narrow the code. (2) It renumbers leaf families for a served 0.0.4 schema, so an index built under 0.0.4 for `D` would silently disagree with a recompiled ruleset (REASONED; compiled artifacts are cache, the schema text is the record). (3) It turns a closure-leaf O(1) arm into a derived-TTU residue path (perf). (4) It does not make Lean's `graph` answers right either, because the 2026-08-14 class is independent (P2) |

**Why L-A over L-B (REASONED):**
- The row's goal is "the model describes the shipped compiler again with no recorded gap".
  L-A achieves that with the narrowest premise that is exactly what the proof consumes. It
  is decidable and schema-level, so it rides `hNBD`'s threading verbatim with no
  store-weakening.
- L-B buys generality that no headline theorem can use while `computedOrDirect` gates them,
  and that is `TK133`'s job.
- L-A's carry is an honest W4-style carry: Python imposes nothing, and it is vacuous on
  `W4Fragment`. It is not an admission narrowing, so it must NOT go into `GraphAdmission`.
  `SlXt` is admitted (P1: `"admitted":true`).

Rejected inside L-A:
- Put the carry into `NoBridgedDerived`'s def. This would conflate two unrelated scope
  claims to save binders, and move a pinned def's meaning.
- Redefine `NoTtuTarget` over `schemaRewritesL`. This would move the 211-line, 24-file
  `NoTtuTarget` surface (TK126 doc §4.2, measured 2026-10-07) and push `SlXt`-class shapes
  out of `term`, changing `w4_fragment_report`'s differential.
- Use the full `computedOrDirect` predicate as the premise. That is stronger than needed,
  and `docs/sabotage-procedure.md` asks for the narrowest premise.

## 7. Gate impact, risks, collisions

**Gate impact (REASONED unless marked):**
- `MIN_TESTS_ALL` / `MIN_CONF_ALL`: raise them by exactly the tests added in T2/T3. They only
  go up.
- `formal/headline_statements.txt`: 2 rows move (`runCascade2_no_abort`, `cascade2_drains`).
- `formal/headline_definitions.txt` (transitive closure, auto-collected; READ the
  `statement_pin.py` header):
  - The `isPure` row changes.
  - New rows appear for `ttuParentTypes` and `LeafTtuTargetsUnderived`, plus anything they
    pull in. `ttuTargets` may already be present (UNVERIFIED).
  - `derivedAnywhere`, `atomLeaves`, `persistedLeaves`, `leafRewrites` and `schemaRewritesL`
    keep their text.
- `formal/audited_theorems.txt`: additions only.
- Snapshots: none.
- CORRESPONDENCE anchors: new anchors must resolve (`anchor_check.py`).
- `claim_rot`: no uncited ratios in new prose.
- `w4_fragment_report` / the CLI `fragment` mode differential:
  - Unchanged, because `W4Fragment` is unchanged.
  - The `GraphAdmission.noLeafSubjects` field is decided over `schemaRewritesL`, which now
    includes more TTU targets. Those are declared names and never dotted, so the verdict is
    unchanged on parsed schemas (REASONED).

**Risks:**
- R1: P3 is an over-approximation, so the true number of declarations needing the binder
  may be lower. It may also be higher if an `hNBD`-free path exists that P3's whole-word
  match missed (unlikely; the 14 `hNBD`-free carriers are all listed in §3.2). Lean has no
  forward declarations, so the order of edits is the file import order.
- R2: the `simp [isPure, ...]` sites in the purity-lemma family (§4, step 2) may need a
  `ttuParentTypes` unfold. Small.
- R3: build time. A change to `Leaf.lean` rebuilds almost every `GraphIndex/Cascade*` module.
  Iterate per module (`lake build ZanzibarProofs.GraphIndex.LeafRules`, then downstream)
  before the phased gate.

**Collisions:**
- **C1, `TK119` (NEXT; Lean `Cli.lean` gains a `leaf-rules` mode; a new
  `test_conformance_leaf_rules.py`).**
  - That test is the ideal acceptance instrument for `TK132`, but its plan says "over the
    conformance corpus", and P5 shows the corpus has ZERO divergent schemas.
  - **Recommended order: `TK119` first, with `D`, `D_nested` and `SlXt` added to its fixture
    list deliberately and their mismatch positive-pinned.** `TK132` then flips that pin to
    agreement, and that flip is `TK132`'s acceptance.
  - If `TK132` lands first, T2 (leaf-row projection) is the self-contained instrument, and
    `TK119` should still carry those three fixtures.
  - Both items edit `formal/CORRESPONDENCE.md` and `Audit.lean`, and both rebuild Lean. Run
    them sequentially: `scripts/gate_lock.py` refuses concurrent `verify.sh` runs.
- **C2, `TK123` (renames `connectedstore` → `store` this session).** `TK132` touches no
  `connectedstore` code. The risk is textual only, in `formal/CORRESPONDENCE.md` and in
  `tests/test_tk126_ttu_target_name_collision.py`, which imports
  `ConnectedStore`/`build_index` paths (READ: the test names
  `test_connected_store_and_build_paths_match_the_oracle`). Rebase onto `TK123`'s rename
  before editing those files.
- **C3, `TK133` (SOMEDAY, type-aware `term`).** Design L-B belongs there. `TK132` must not
  touch `term` / `NoTtuTarget` (row trap).
- **C4, the 2026-08-14 Lean-graph under-report on `.ttu` in a derived def** (CORRESPONDENCE
  §0 note). It is NOT fixed by `TK132`, and P2 proves it is independent. No task row for it
  was found by `grep` over `tasks/*.md` for `computedOrDirect|derivedAnywhere|isPure|NoTtuTarget`
  (hits: P6, TK119, TK132, TK133 only). Whether to file one is the coordinator's call. It is
  fail-closed and outside `W4Fragment`.

## 8. Scratch artefacts

These are gitignored. Their load-bearing outputs are quoted above.

- `.scratch/now-next/probes/scout-TK132/`: `p1_slxt.py`, `p2_family.py`, `p3_callers.py`,
  `IsPureT.lean`, `p5_corpus_sweep.py`, `p6_variant_d.py`, `p7_gen_sweep.py`,
  `IsPureT_sweep.lean`, each with its `.out`.
- `.scratch/now-next/scout-TK132.md` is the incremental log.
