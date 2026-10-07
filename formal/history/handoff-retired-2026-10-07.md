# formal/HANDOFF.md archive — blocks retired 2026-10-07 (task `TK131`)

**FROZEN 2026-10-07 — provenance, not a living document.** Status lines below are
as-of-then and several are known false; live state: the task tree (`python scripts/task.py
board`) + [`../HANDOFF.md`](../HANDOFF.md) + the session ledgers.
Corrections are appended dated at the top, never edited into the body.

Retired from `formal/HANDOFF.md` because that file sat at **exactly its 520-line ceiling**
(`scripts/handoff_lint.py::MAX_LINES`, enforced by `formal/verify.sh lean` step 4f; measured
520 lines / 40412 bytes on 2026-10-07), so the next line any session added would have turned
the gate red. Task `TK131` (item 4 of `docs/context-audit-2026-10-07.md`).

The text is **verbatim**, not condensed — the rule
[`handoff-status-2026-08-16.md`](handoff-status-2026-08-16.md) and
[`handoff-dated-blocks-2026-08-17.md`](handoff-dated-blocks-2026-08-17.md) follow: condensing
is where content dies, and a line diff cannot see it. Relative links inside the moved text
were written from `formal/`, so read `history/X` there as this directory and `../docs/X` as
`../../docs/X`. What came here, in source order (line numbers are of the 2026-10-07 file):

* **`P14` absorbed + the 2026-08-05 option-(c) decision** (source lines 63-83). Both closed
  (`P14` 2026-09-23c; the decision's work landed 2026-09-05). ⚠ This block carries the
  **only** statement of a correction to
  [`leaf-family-split-scope-2026-08-05.md`](leaf-family-split-scope-2026-08-05.md): its
  "exactly four places" consuming `Inv` is **five** preservation steps plus
  `Inv.toStruct` (re-measured 2026-08-19). That frozen file cannot be edited, so this
  file is now the correction's home, and `formal/HANDOFF.md`'s doc table points here.
* **The dated blocks 2026-08-15 … 2026-08-28c, and the "dated blocks STOP" pointer above
  them** (source lines 85-216). All landed or retired; every one has a fuller entry under
  the same date key in [`PROOF_STATUS.md`](PROOF_STATUS.md). The three live traps they
  carried each have a gated home elsewhere, which `formal/HANDOFF.md` now cites:
  the `graphModeAnswers_eq_sem` statement pin (`formal/CORRESPONDENCE.md`'s
  `GraphIndex/Exec.lean::graphRun` row, and the comment above that entry in
  `formal/conformance/statement_pin.py::HEADLINE`); `fence_changes_answer` as the only
  fence-removal catch (`formal/CORRESPONDENCE.md`'s `GraphModel.checkPublic` row); the
  binary-`Expr` n-ary allocation limit (`formal/CORRESPONDENCE.md` §7.2, refused at
  `formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`);
  and `String.contains` not kernel-reducing (`GraphIndex/Leaf.lean`'s `toList` docstring).
* **The "Board — two ORPHANED findings" section: `B1`, `B2` and the 2026-08-16 note**
  (source lines 322-434). `B1` CLOSED 2026-08-16; `B2` verdict final (Python overtaken,
  Lean declared out of scope, conformance closed — and the `derived-tupleset-ttu` half
  made unreachable by `TK106`). Lean comments that cite "`HANDOFF.md` Board B1"
  (`CascadeStrataAssemble.lean`, `ReconcileCorrect.lean`) resolve here now.
* **"Landed 2026-09-05 — leg 7, the leaf-family split"** (source lines 451-478). Landed;
  "Owed next: nothing on the flip itself". Record: `PROOF_STATUS.md` 2026-09-05b.
* **"The T2a scope carry — CLOSED 2026-09-23 (`P5`)" and the `P4` notes under it**
  (source lines 503-512). Both closed (`P5` 2026-09-23, `P4` 2026-10-03d).

---

## From the top of the file (source lines 63-83)

**Leg 7 step 5 (`P14`) closed as absorbed 2026-09-23c — nothing was owed.** The reach-collapse
family is proved over the leaf-routed chain (`CascadeStrataSettle.lean::reachedByW3d2_reach_collapse_root_d`),
and a probe of the headline theorems' dependency closure shows they use only that `_d` family
(plus the scope-free `reconcileJobsLR_reach_collapse`). No narrow, W3d or W3a collapse lemma is
used. Record: [`docs/p14-reach-collapse-absorbed-2026-09-23.md`](../docs/p14-reach-collapse-absorbed-2026-09-23.md).

**The design decision that was owed here was made 2026-08-05 — option (c), model the leaf
family and retire P6 — and its work landed 2026-09-05.** The deliberation, the two rejected
options ((a) restate at drained states only, (b) weaken `negEdgeFree`), the "nothing
consumes `Inv`" finding that decided it, the 2026-07-11j precedent against (b), and the
blast radius (55–65% of the tree; `Spec/`/`SetEngine/` entirely spared) are in
[`history/leaf-family-split-scope-2026-08-05.md`](history/leaf-family-split-scope-2026-08-05.md)
and `history/PROOF_STATUS.md` 2026-08-05e.
⚠ **The one correction that lives only here:** that finding's "exactly four places" is
wrong, and two of its anchors (`State.lean:813`, `:854`) had drifted onto
`putResidue_residue` and `structInv_addEdge`, neither of which mentions `Inv`. Re-measured
2026-08-19 by `grep -rn '(h : Inv S σ)\|Inv S σ →'`: **five** preservation steps, not four —
`State.lean::inv_putResidue`, `Write.lean::inv_writeDirect`,
`RulesWrite.lean::inv_foldl_writeDirect`, `RulesWrite.lean::inv_writeRules`,
`ReconcileWrite.lean::inv_reconcileKey` — plus the forgetful `State.lean::Inv.toStruct`.
The finding it supports (nothing consumes `Inv`) is unchanged.

## The dated blocks (source lines 85-216)

⚠ **Dated blocks STOP at 2026-08-28c; every session since is in `history/PROOF_STATUS.md`,
not here** — `2026-08-30`…`2026-09-02c`, `2026-09-05`, `2026-09-05b` (leg 7's flip landed; leg-7
block below), `2026-09-06` (`TK56`: undischargeable `hValid`/`opaque ValidIdent` deleted; T3 takes
exactly T2b's hypotheses, INSTANTIATED by `W4WitnessDirect.equivalence_applies`; zero opaques;
pins 51 + 251), `2026-09-06b` (`P17`/`TK55` closed: bulk pinned by `test_conformance_bulk_state.py`
+ scope statement, `keysNonempty` accepted, empty declared names refused by both parsers; red-branch
evidence → `history/p3-flip-red-snapshot-2026-09-05.md`; `P22`–`P24` filed). Sizing: `2026-09-01e`
sized the flip at **5 sites / 4 decls / 2 files**; **step 9 done (2026-09-02)**; **2026-09-02b**'s
"CLOSED 14/12/6" is retired by **2026-09-02c** as a lower bound — live **62 + 13 decls / ELEVEN files**; §11.13 (v)/(w).

**2026-08-28c — the public surface is migrated, and the `hql` surface is one row.**
Seven declarations (`backend_equivalence`, `exclusion_effective`, `no_ghost_grant`,
`Exec.graphRun_check_eq_sem`, `::graphRunOps_check_eq_sem`,
`W4WitnessDirect.final_applies`/`final_applies4`) state `GraphModel.checkPublic`, proved
through `graph_correct_public`. **None gained a hypothesis** — `graph_correct_public` takes
exactly `graph_correct`'s bundles — and every proof stayed a 1–2 line delegation.
`Cli.lean`'s graph mode migrated with them (it prints `Exec.lean::graphModeAnswers` now),
because a capstone that names a different read than the driver calls makes its own
docstring false.

🚨 The "one row" half was **false when written** — it was three rows (27, 46, 56), refuted
2026-08-31c by consumer-set enumeration — and was made true again by the 2026-09-01b
migration rather than by the 2026-08-28c argument: rows 46/56 are restated over
`GraphModel.checkPublic`, and the `hql` binder is refused on both, because `q` is
universally quantified there and the binder would put a schema-dependent hypothesis on the
two satisfiability instruments (the house failure mode). Row 27 is deliberately kept as the
internal-layer statement; `unfenced_grants` (`:52`) stays unfenced as
`fence_changes_answer`'s foil, and `Equiv.lean`'s 27-rung ladder stays on `check` as a
per-stage record of that layer. The consumer enumeration, the three pinned instruments and
both sabotages: `history/PROOF_STATUS.md` `2026-08-31c` and `2026-09-01b`; the
`docs/latent-gaps.md` "six theorems" recount is in `2026-08-28c`.

⚠ **A hole was found and closed here.** The driver↔capstone coupling was UNPINNED:
reverting `Cli.lean` to the unfenced read left the full conformance suite green
(`495 passed`), and structurally no corpus can catch it pre-4c-ii. Fix is TEXTUAL —
`Exec.lean::graphModeAnswers` is a named definition whose body is pinned verbatim
(`headline_definitions.txt:212`), dragged into the closure by `graphModeAnswers_eq_sem` in
`statement_pin.py::HEADLINE`. Its own sabotage: build stayed green (1089 jobs), definition
pin fired, **statement pin matched 46/46 and was blind**. Do not remove that theorem from
`HEADLINE` — it un-pins the driver. Detail: `history/PROOF_STATUS.md` `2026-08-28c`.

**2026-08-28b — the fence-modeling endgame landed green, without `hql` and without opening
the 4c-ii cone.** `GraphIndex/Fence.lean::GraphModel.checkPublic` +
`FullScope.lean::graph_correct_public`: the public read equals `sem` under exactly
`graph_correct`'s hypotheses, no leaf-name guard, purely additive. Narrative and sizing:
`history/PROOF_STATUS.md` 2026-08-28b.
⚠ **`graph_correct_public` is NOT what makes the fence non-vacuous** — pre-4c-ii it proves
green even under a fence that never fires; the six `W4WitnessDirect.fence_*` pins at `Sd`
are, and only `fence_changes_answer` catches a fence REMOVAL (§3 has the sabotage record).

**2026-08-28 — both `P3` human calls are made** (`hql` accepted; Route B retained on
corrected grounds — its "zero additional cone" argument is falsified), after a live census
re-sized the cone for the third consecutive time. Its recommended fence-modeling repair
landed the next day, and the technical choice it left open (WF-clause vs threading for
computed-ref dot-freeness) was overtaken by the 2026-09-05 flip, which threads
`NoLeafSubjects` from `GraphAdmission`. The 2026-08-16c block below stands as history; its
`FoldAdmits` "24" is superseded — 19 Prop sites + 2 exec gates move / 3 stay, scope doc
§11.11 item 7, which also supersedes the sizing in §11.9/2026-08-20b. Narrative:
`history/PROOF_STATUS.md` 2026-08-28.

**2026-08-16c — history: 4c-ii was blocked here on a proof-design adjudication, not on
coding, and the shadow chain's cheap route was refuted (unblocked, and landed, 2026-09-05).
No Lean file changed; detail in `history/PROOF_STATUS.md` 2026-08-16c and scope-doc §11.8.**

* ⚠ **ROUTE A IS REFUTED.** Re-pointing `ReachedByRulesAdmitted.step` cannot work:
  `ReconcileComplete.lean::reachedByW3aAdmitted_toW3a` needs a `ReachedByRules σ S T` witness
  for a `writeRulesRaw`-built σ (its `base` case), and
  `LeafRules.lean::lrV_writeRulesRaw_edges_ne` already
  proves those two states' edges DIFFER. The surviving branch weakens `UntaintedShadow` — a
  slice of board row `P14`, whose deps close a cycle `P3 → P14 → P4 → P3`. Settle this
  first; it is cheap to attack with `#eval` and it decides the cone.
* ⚠ **The own-key premise is BACKWARDS.** On the `ComputedOnly` fragment the leaf list is
  EMPTY, not multi-element (`Leaf.lean::atomLeaves` returns `[]` for a derived `.computed`
  arm; `Leaf.lean::rawWriteRels` has `| .closure _ => none`), so `writeLeg_own_key_dirty`
  goes FALSE and needs a
  non-emptiness premise (`StoreValidRules`), not `WF`. Measure whether
  `StoreValidRules` + `ComputedOnly` admits a stored tuple on a derived key at all.
* ⚠ **The criterion only counts CONJOINED with a green gate.** `dropped by P6 → 0` /
  `compared → 265` was a pure function of the Python side, publishable by commenting out one
  branch of `extractor.py::_edge_projection` with no Lean change. **Discharged 2026-09-05,
  conjoined**: the branch is gone, so that attack is no longer available, and the successor
  control is the positive floor `_MIN_LEAF_COMPARED = 76` asserted by
  `formal/conformance/test_conformance_state.py::test_leaf_rows_reach_the_compare_arm`.
  Measured ledger, the sabotage and its control: `history/PROOF_STATUS.md` 2026-09-05b §7.
* Verified while attacking: the `FoldAdmits` lockstep is **24** spelled-list sites, not 7;
  `Audit.lean` is an EDITED file of this step (`:314` pins `reachedByRules_of_admitted`);
  and `_MIN_LEDGER_ROWS`/`_MIN_LEDGER_STACKED = 19/19` sit before the golden read.

**2026-08-16 — LEG 7 STEP 4c-i IS IN (`GraphIndex/LeafRules.lean`), the ALLOCATION was
refuted THREE more times first, and `ttuStarFree` part (iv)'s BLOCKING QUESTION IS
ANSWERED: NO-BLOCK. Read `history/PROOF_STATUS.md` 2026-08-16 and scope-doc §11.7 FIRST.**

* **4c-i landed with a zero recompile cone, and §11.6's cost cell is refuted.** As an
  extension downstream of `RulesWrite` the cone is **one file**, and the `Cascade →
  LeafRules` import 4c-ii needs is cycle-free; additivity is *proved*
  (`schemaRewrites_leafRewrites_disjoint`), not observed. Detail: scope-doc §11.7.
* **⚠ THE ALLOCATION WAS WRONG THREE MORE TIMES**, all caught before 4c-i was built on it:
  Python MERGES a maximal pure subtree (`(a or b) but not banned` → `r.0={a,b}`,
  `r.1=banned`, not three leaves, storage always first); a tainted userset restriction gets
  its OWN storage leaf (reachable from the live fixture `userset_over_derived.fga`); and —
  **invisibly to the instrument that validated the first two** — the n-ary union SPINE.
* **The method lesson** — *a transcription of the right rule over the wrong input
  representation is the mirror instrument with extra steps* — is written up, with the
  "82/82" run that produced it, in
  [`docs/sabotage-procedure.md`](../docs/sabotage-procedure.md).
* **⚠ A LIMIT OF THE BINARY `Expr` LEG 7 MUST CARRY.** `Core/Schema.lean` justifies
  left-folding n-ary unions by associativity+commutativity — true of `sem`, **false of the
  leaf ALLOCATION**. Measured: `a or b or safe` → 2 leaves, `(a or b) or safe` → **1**, and
  `_fold_binary` maps both to the SAME `Expr`. The model is faithful to the FLAT form; the
  other shape is refused mechanically at
  `formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`.
  Making it faithful to both means an n-ary `Expr` — a trust-root change, out of scope.
* **`ttuStarFree` PART (iv) IS UNBLOCKED.** `GraphIndex/TtuStarWide.lean` answers the
  standing question with a theorem: `TtuStarFree` is a bounded quantification over finite
  lists, the widening only weakens the BODY, and the new conjunct
  `Schema.isSubjectWildcardUserset` is **already `Bool`-valued** — so `ttuStarFreeWB`
  decides `TtuStarFreeW` and `removeGateB` widens by the same textual edit
  (`removeGateBW_gate`). Proved a genuine weakening AND strictly wider at a store.
  ⚠ `W4Fragment.ttuStarFree` is UNCHANGED and must stay so until part (ii).
* Audits 520 → **573**, anchors 471 → **497**, statements 38/38 and definitions 155/155
  UNMOVED. Re-measured: *"17 of 25 corpora mint indices 1 AND 2"* overstates the index-2
  breadth 3.4× — index ≥1 in 17, index 2 in **5**.

**2026-08-15 — LEG 7 4c-PRE is RETIRED from this file (2026-09-23).** Its allocation half was
already marked SUPERSEDED by the 2026-08-16 block above, its cone estimate refuted and its
index-breadth figure stale; 4c-i and 4c-ii have both LANDED (2026-08-16, 2026-09-05), and its
closing "→ 4b/5/6/7; 4c-ii + 7 still co-land" is refuted outright — 4b's premise turned out to
be false and 7 co-landed with the flip. The block is provenance now: read
`history/PROOF_STATUS.md` 2026-08-15 and scope-doc §11.6/§11.7, which it cited itself, and
`docs/p4-leaf-probe-bridge-2026-09-23.md` for what became of 4b.
⚠ The one still-live line it carried, kept here because nothing else states it: **`String.contains`
does not kernel-reduce** — leaf-layer defs stay `toList`-based or `decide` pins stall.

## The orphaned-findings board (source lines 322-434)

---

## Board — the two ORPHANED findings, adjudicated 2026-07-27 (ZT-P4 item 4)

Both lived only in `history/` and had reached no board. Each was re-verified
against the working tree (commands quoted). **Paste-ready paragraphs for the root
board are the two blocks below, verbatim.**

### B1 — `w3cJobValid_enumJob2D` star-freeness hole · verdict: **CLOSED 2026-08-16** (proved 2026-07-28/08-04; the record simply never caught up)

> **Closed, both halves, and machine-checked.** The 2026-07-27 verdict below said the
> finding needed "a decision, not a proof session": choose between a star-filter inside
> `storedDirectSubjects` and a new fragment clause banning wildcard restrictions on derived
> Direct arms. The E-chain plan §B took **both**, the next day, and they landed:
>
> * **The `storedDirectSubjects` half** — closed unconditionally by the faithfulness
>   star-filter (`CascadeStrataEnum.lean::storedDirectSubjects`, mirroring
>   `src/zanzibar/graphindex/processor.py`'s `_incoming_concretes` wildcard filter), giving
>   `storedDirectSubjects_name_ne_star` with no fragment premise at all.
> * **The `edgeHolders` half** — discharged at the call sites by
>   `CascadeStrataSettle.lean::reachedByW3d2_Rnode_source_name_ne_star_d`, under the new
>   `W4Fragment` clause `directArmsConcrete`.
>
> Both feed `CascadeStrataAssemble.lean::w3cJobValid_enumJob2D`, which is audited and
> axiom-clean, and reach the final theorems through `enumJobs2At_valid` (four call sites in
> `CascadeStrataAssemble` and `CascadeStrataEdge`) and `FullScope.lean`'s
> `W4Fragment.directArmsConcrete`. So clause (ii) of the old verdict — *"the lemma does not
> exist, so no landed theorem depends on it"* — is now false in both of its parts.
>
> **Sabotage, 2026-08-16** (`docs/sabotage-procedure.md`): the star-filter was defeated in
> place (`fun s => s.name != STAR` to `fun _ => true`) and `lake build` of
> `ZanzibarProofs.GraphIndex.CascadeStrataEnum` went red at the `simpa` closing
> `CascadeStrataEnum.lean::storedDirectSubjects_name_ne_star`.
> So this half is held by the type checker, not by measurement. Restored and re-verified.
> ⚠ Do not confuse that filter with the `freshDirectCands` presence diff a few lines away:
> **that one IS measurement-pinned** and the tree compiles with it defeated, which is why
> its docstring carries a conformance-ledger observation instead of a proof.
>
> **The honest carry that came with the fix, unchanged:** `directArmsConcrete` excludes a
> shape Python admits — `define approver: [user, user:*] but not banned` compiles and all
> three backends agree on it. It is a **vacuity** boundary, not an unsoundness one: on such
> a schema `W3cJobValid` fails for every enumerated job at the key, so the operational chain
> has no cascade constructor there. The paragraph stating this lives at
> `FullScope.lean::W4Fragment`, and the clause is machine-confirmed load-bearing — a
> 262-run driver sweep saw 824 in-edges at derived R-nodes with none STAR-sourced, and with
> the clause dropped 122 stores produce one.
>
> **Why it stayed open on paper for three weeks:** the verdict was written 2026-07-27, the
> fix landed 2026-07-28 and 2026-08-04, and nothing connected them. `Audit.lean` said "the
> `storedDirectSubjects` half of the Board-B1 star-freeness hole is closed" the whole time.
> The repo board retired the id; this file kept the open verdict. That gap is the argument
> for the rule that a finding is closed where it is RECORDED, not where it is fixed.

### B2 — `PDerivedUserset` never modelled in Lean · verdict: **OVERTAKEN Python-side; a DECLARED Lean scope gap; the CONFORMANCE half was a real hole and is now closed**

> **`PDerivedUserset` — Python-side overtaken, Lean-side a declared scope gap, and
> it had ZERO conformance coverage until 2026-07-27.** The X4 shape (a userset
> restriction `[group#member]` whose predicate is itself derived) was fixed
> Python-side 2026-07-13 and extended 2026-07-17, and never modelled in Lean — in
> the exact plan-leaf area where five real divergences were found. Re-verified
> 2026-07-27: Python-side it is **overtaken** — `define member: base but not kicked`
> + `define viewer: [group#member]` compiles to a real `PDerivedUserset` leaf
> (`LeafSpec('viewer.0','derived-userset', storage=True)`, 2 strata) and oracle ==
> set engine == real graph index over the full 126-query grid (alice True, kicked
> bob False); `tests/test_lookup_oracle.py`'s former strict xfails are plain
> regression pins. Lean-side it is a **declared** scope gap, not a silent one:
> `FullScope.lean::W4Fragment`'s doc says `PDerivedTTU`/`PDerivedUserset` leaves are
> "out of scope (W3a decision)", and `term`/`NoStoreSubjectR` forbids the stored
> userset tuple the shape needs. **The genuinely new finding is the conformance
> half:** walking every `RuleSet.compiled.plans[..].leaves` over all 69 schemas the
> harness reads gave the leaf-kind histogram `closure 211 · derived-computed 42 ·
> derived-ttu 50 · derived-userset 0 · derived-tupleset-ttu 0` — i.e. **no corpus
> compiled a `PDerivedUserset` leaf at all**, so no differential ever exercised that
> compiler branch. Closed for `derived-userset` by
> `corpus.py::TTU_USERSET_SCHEMAS['derived_userset']` (spec-side; scope argument in
> situ) and floored by
> `test_conformance_nary_strata.py::test_every_plan_leaf_kind_is_reached_by_some_corpus`.
> ~~**`derived-tupleset-ttu` (`PDerivedTuplesetTTU`) is still at ZERO and is the
> remaining plan-leaf hole — deliberately not faked into the floor.**~~
> **CLOSED 2026-07-28** by `TTU_USERSET_SCHEMAS['derived_tupleset_ttu']`, together
> with the other zero-coverage hole (wildcard usersets `[T:*#p]`,
> `TTU_USERSET_SCHEMAS['wildcard_userset']`). The floor now names EVERY kind
> `zanzibar.schema._plan_leaves` can emit, and
> `test_required_leaf_kinds_are_exactly_the_compilers_kinds` reads those kinds out
> of the compiler's own source so the list cannot go stale. Conformance 450 → 464.
> Two reachability corrections worth carrying: a wildcard userset over a DERIVED
> relation is a compile-time scope rejection raised out of `parse_openfga_schema`,
> so it can never be a corpus (only the UNTAINTED surface is reachable); and
> `derived-tupleset-ttu` was always reachable — the obstacle was that TTU parents
> are STORED tupleset tuples, so a derived tupleset without a `Direct` restriction
> compiles the leaf and drives it EMPTY (which is why `demorgans_law_1.fga` could
> not serve). Both corpora are spec-side + a python-only 3-backend leg and are
> asserted OUT of `SCHEMAS`/`GRAPH_FRAGMENT`: `wildcard_userset` falsifies
> `W4Fragment.wsBare`; `derived_tupleset_ttu` falsifies `W4Fragment.computedOnly`
> AND `GraphAdmission.ttuDirect`. Detail + all seven sabotage runs:
> `formal/history/nary-strata-coverage-2026-07-27.md` (2026-07-28 addendum).
> ⚠ **2026-09-26 (`TK106`):** a boolean tupleset is now a parse refusal, so
> `derived_tupleset_ttu` moved from `TTU_USERSET_SCHEMAS` to a refused-schema registry
> and the `derived-tupleset-ttu` leaf kind is EXCLUDED from the floor as unreachable by
> design (asserted refused, so the exclusion is revoked if the refusal relaxes). The
> "CLOSED" above is history.
> Verdict: Python OVERTAKEN · Lean DECLARED-OUT-OF-SCOPE (no action) · conformance
> CLOSED for both.


### Note 2026-08-16 — the `B1` board disagreement, resolved

Earlier the same day this file still verdicted `B1` open while the repo board had retired
the id, and that gap was recorded here as an open question. It is now answered: the finding
really is closed, the evidence is in the `B1` block above, and both boards agree. The
mechanism that produced the gap is worth keeping, though — **retiring an id is not the same
act as closing a finding**, and for three weeks nothing in the tree distinguished them. If
you retire an id, say in the same edit whether the finding died with it.
## From "Status" — leg 7 landed (source lines 451-478)

**Landed 2026-09-05 — leg 7, the leaf-family split (repo board rows `P3`, `P4`, `P5`,
`P14`): the flip is in.** Both logged legs now fold the leaf-routed closure —
`Cascade.lean:190-191::GraphState.writeLoggedRules` and `:340-341::removeLoggedRules` fold
`rewriteClosureL S (rawWriteTuples S t)` instead of `rewriteClosure S t` over public
relation names — and `affectedKeys` (`:542-546`) reads the public relation back through
`publicOfLeaf`; `writeRules`, `rewriteClosure` and `reachedByRules_edge_sound` are
unchanged. The write-leg-only flip was kernel-refuted first, so branch (α) and R5 co-landed
in the same commit (`untOccCount` restated over the L closure at
`CascadeStrata.lean:687`, `:716::count_removeLoggedRules`). `GraphAdmission` gained
`noLeafSubjects` and `keysNonempty`, both honest Python-side scope claims mirroring
`src/zanzibar/schema/parser.py::_validate_ast_references`; the second is an accepted scope narrowing
flagged to the user. **Step 7 co-landed: projection P6 is retired** (the 2026-08-16c block's
discharged criterion above). The tree is sorry-free, statement pin 49/49, definition pin
regenerated 232 → 250 after a control run on the old pins.
Mechanics, the refutation, the co-requisite sizing, the P6 Python half and the pin control:
`history/PROOF_STATUS.md` 2026-09-05b §1, §2, §7, §9.
⚠ **The flip doubled an ALREADY-exponential derived-arm stacking**; ten conformance tests
timed out (`two_stratum_cascade`, five adds: control 1013 edges, post-flip 2026). Two Python
mirrors landed with it, both core `List.eraseDups`: `CascadeStrata.lean::cascadeKeysAbove`
(the `_map_deltas_to_keys` keys-dict; `cascadeKeys_eq_above` → `mem_cascadeKeys_iff_above`)
and `enumJob2`/`enumJob2D`'s `cands` (the `_reconcile` candidates dict; `edgeHolders` is
one entry per held EDGE — the doubling). Post-fix `1…5` in 0.1 s, answers unchanged. Golden
`derived_arm_multiplicity.json` regenerated after a control run, `_MIN_LEDGER_STACKED`
19 → 18, definition pin 250/250 after its control. `CORRESPONDENCE.md` §7.2 item 5c; item 6
stays open, residual `+1` per reconcile. Record: `history/PROOF_STATUS.md` 2026-09-05b §10.
Owed next: nothing on the flip itself. The T2a/`negEdgeFree` re-read is done; T2a did not
widen with the flip, and caught up on 2026-09-23 (`P5`) — see the T2a note at the top of
this file.

## From "Status" — the T2a scope carry (source lines 503-512)

**The T2a scope carry — CLOSED 2026-09-23 (`P5`)**; see the T2a note at the top of this
file. The pre-work measurements that sat here (the Sd/Td probe, `graph_reached_inv`'s zero
proof consumers ⇒ a positive witness owed with the restatement, the proof map) are recorded
in `docs/p5-negedgefree-under-leaf-routing-2026-09-23.md`.
**`P4` did NOT block it** (`deps` edge removed 2026-09-23): §8.1's bridge premise is
false — `checkFn` never reads a leaf node and `GraphAdmission.computedRefsNotLeaf` refuses
the schemas that would make it — so 4b became a `CORRESPONDENCE.md` §7.3 item, landed as six
`Exec.lean::P4Bridge` witness pins. Map: `docs/p4-leaf-probe-bridge-2026-09-23.md`.
**2026-10-03d: `P4` CLOSED** — the general statement is `GraphIndex/LeafBridge.lean::leaf_probe_bridge`
(off the probe, not `evalE`; statement-pinned); detail in `history/PROOF_STATUS.md` 2026-10-03d.
