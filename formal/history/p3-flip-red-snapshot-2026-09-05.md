# P3 write-leg flip — the RED snapshot, quoted (branch `p3-flip-red-2026-09-05`, `d6d2dfc`)

**FROZEN 2026-09-06 — provenance, not a living document.** Status lines below are
as-of-then and describe a tree that is NOT master; live state: [`HANDOFF.md`](../../HANDOFF.md)
+ [`../HANDOFF.md`](../HANDOFF.md) + the session ledgers. Corrections are appended dated
at the top, never edited into the body.

This is the only tracked copy of the literal refuting declarations from the RED snapshot —
commit `d6d2dfc` (parent `68f2c69`; 30 files, +3381/-653 per `git diff --stat`), the working
tree at the moment the adjudicated "write leg only" flip was found kernel-REFUTED. Every
quoted line below was re-read from `git show d6d2dfc:<path>` on 2026-09-06 and carries the
branch `file:line` it was read from. The mechanism lives INVERTED on master as positive pins
(`Exec.lean::graphRunOps_directArm_agrees`, `CascadeStrata.lean::writeThenRemove_edge_count_zero`
/ `::writeThenRemove_no_leaf_edge`; master `9f05fbf` carries none of the declarations below
and no `#check` command anywhere under `formal/lean/ZanzibarProofs/`). The story — what the
flip is, the finding, the two mechanisms, the co-requisites, the blind `sorry` belt, and the
decision — is `PROOF_STATUS.md` session `2026-09-05b` sections 1–8; this note is only the
evidence that story cites.

The snapshot never was and must never be gate-green. Per its own commit message and
`Exec.lean:204`/`:1345`: `lake build` rc=0 (1089 jobs) with FOUR `declaration uses `sorry``
warnings, and 40 of 584 audited theorems (`graph_correct`, `graph_correct_public`,
`backend_equivalence`, `exclusion_effective`, `no_ghost_grant`, `graph_reached_inv`,
`graphRun*_check_eq_sem`, …) depending on `sorryAx`. Those build figures are the commit's
self-report; they were not re-built for this note.

## The four staged sorries

Three sit on the `hcnt` closure-count equation inside an induction (`have hcnt : ((rewriteClosureL
S (rawWriteTuples S t)).map edgeOfTuple).count (a, b) = ((rewriteClosure S t).map
edgeOfTuple).count (a, b) := by sorry`); the own-key one is the whole proof body.

    CascadeStrata.lean:919         reachedByW3d2_untOccCount     (sorry at :954)
    CascadeStrata.lean:1293        reachedByW3d2_srcOccCount     (sorry at :1316)
    CascadeStrataSettle.lean:3317  writeLeg_own_key_dirty        (bare `:= by sorry`, token at :3342)
    RemoveOccCount.lean:143        reachedByW3d2E_untOccCount    (sorry at :165)

All paths are under `formal/lean/ZanzibarProofs/GraphIndex/`.

## The refutations, sorryAx-free, verbatim

`Exec.lean:980` — axioms `[propext, Classical.choice, Quot.sound]` (the docstring's own
`#print axioms` report at `Exec.lean:883-884`, and the commit message; not re-run here):

    theorem graph_correct_refuted :
        ¬ (∀ (S : Schema) (T : Store) (σ : GraphState) (q : Query),
            GraphAdmission S T → W4Fragment S T → ReachedBy σ S T → Drained S σ →
            (q.subject.name = STAR → q.subject.predicate = BARE) →
            q.object.name ≠ STAR →
            publicOfLeaf S q.object.type q.relation = none →
            GraphModel.check σ q = sem S T q)

`Exec.lean:932` `graph_correct_public_refuted` is the same statement without the `publicOfLeaf`
binder, over `GraphModel.checkPublic`. Each rests on one `decide` at the project's own
in-fragment witness (`W4WitnessDirect.Sd`/`Td`, hypotheses discharged from `::admission` /
`::w4fragment` at `Exec.lean:951` and `:1000`): the public one on
`graphRunOps_directArm_diverges` (`Exec.lean:903`), the raw-`check` one on its twin
`graphRunOps_directArm_diverges_check` (`Exec.lean:959`, same shape over `GraphModel.check`).

    theorem graphRunOps_directArm_diverges :                                   -- Exec.lean:903
        ((graphRunOps W4WitnessDirect.Sd sdDirectArmOps).map
            (fun p => (p.2, GraphModel.checkPublic p.1 sdDirectArmQuery,
                       drainedB W4WitnessDirect.Sd p.1)))
          = some (W4WitnessDirect.Td, false, true) := by
      decide

    def sdDirectArmQuery : Query := ⟨⟨"user", "alice", BARE⟩, "approver", ⟨"doc", "d1"⟩⟩   -- Exec.lean:893

`sem` grants the same query: `sem_directArm_grants` (`Exec.lean:912`),
`sem W4WitnessDirect.Sd W4WitnessDirect.Td sdDirectArmQuery = true := by decide`.

`CascadeStrataSettle.lean:3380` / `:3390` — the own-key mechanism; axioms `[propext]` only
(per `Exec.lean:1123`, not re-run here):

    theorem swTw_own_key_not_dirty :
        ("doc", "approver", "d1") ∉
          cascadeKeys LeafWitness.Sw
            ((emptyState LeafWitness.Sw).writeLoggedRules LeafWitness.Sw LeafWitness.tw)
    theorem writeLeg_own_key_dirty_refuted :
        ¬ (∀ (σ : GraphState) (S : Schema) (t : Tuple), NodupKeys S →
            FoldAdmits σ (rewriteClosureL S (rawWriteTuples S t)) →
            isDerived S (t.object.type, t.relation) = true →
            t.object.name ≠ STAR →
            (t.object.type, t.relation, t.object.name)
              ∈ cascadeKeys S (σ.writeLoggedRules S t))

`CascadeStrata.lean:1088` / `:1383`, `RemoveOccCount.lean:195` — R3 at the leaf edge
`(user:alice, doc:d1#viewer.0)`. Witnesses: `lrV_chain` (`CascadeStrata.lean:1065`, over
`LeafRuleWitness.SlV` / `LeafRuleWitness.tlEditor`, defined at `LeafRules.lean:1774` / `:1869`)
and `tlUsEditor_chain` (`CascadeStrata.lean:1358`, subject `⟨"group", "g1", "member"⟩`,
`def tlUsEditor` at `:1339`). Count > 0 by `lrV_writeLeg_has_leaf_edge` (`:1043`) against
`untOccCount = 0` by `lrV_untOccCount_leaf_zero` (`:1033`):

    theorem reachedByW3d2_untOccCount_refuted :                                -- CascadeStrata.lean:1088
        ¬ (∀ (σ : GraphState) (S : Schema) (T : Store), ReachedByW3d2 σ S T →
            ∀ a b : NodeKey, isDerived S (b.type, b.pred) = false →
              σ.edges.count (a, b) = untOccCount S T a b)
    theorem reachedByW3d2_srcOccCount_refuted :   -- CascadeStrata.lean:1383; guard `a.pred ≠ BARE` instead
    theorem reachedByW3d2E_untOccCount_refuted :  -- RemoveOccCount.lean:195; over ReachedByW3d2E, same SlV/tlEditor witness

## The second mechanism — the leaf edge leaks and the internal read grants it

    theorem writeThenRemove_leaks_leaf_edge :                                  -- CascadeStrata.lean:1154
        (subjNode ⟨"user", "alice", BARE⟩, objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0))
          ∈ (((emptyState LeafRuleWitness.SlV).writeLoggedRules LeafRuleWitness.SlV
                LeafRuleWitness.tlEditor).removeLoggedRules LeafRuleWitness.SlV
                LeafRuleWitness.tlEditor).edges

    theorem graphRunOps_writeRemove_leaks_leaf_edge :                          -- Exec.lean:589
        ((graphRunOps LeafRuleWitness.SlV
            [GraphOp.add LeafRuleWitness.tlEditor,
             GraphOp.remove LeafRuleWitness.tlEditor]).map (fun p => (p.1.edges, p.2)))
          = some ([(subjNode ⟨"user", "alice", BARE⟩,
                    objNode ⟨"doc", "d1"⟩ (leafPred "viewer" 0))], []) := by
      decide

    def leakLeafQuery : Query :=                                               -- Exec.lean:698
      ⟨⟨"user", "alice", BARE⟩, leafPred "viewer" 0, ⟨"doc", "d1"⟩⟩

    theorem graphRunOps_leak_unfenced_grants :                                 -- Exec.lean:706
        ((graphRunOps LeafRuleWitness.SlV
            [GraphOp.add LeafRuleWitness.tlEditor,
             GraphOp.remove LeafRuleWitness.tlEditor]).map (fun p =>
              (p.2, drainedB LeafRuleWitness.SlV p.1,
               GraphModel.check p.1 leakLeafQuery,
               GraphModel.checkPublic p.1 leakLeafQuery)))
          = some ([], true, true, false) := by
      decide

## The bridges: each refutation targets the NAMED theorem, not a lookalike

`*_explicit` = the named theorem eta-expanded into the binder shape the `¬∀` negates
(`Exec.lean:1059`, `:1073`, `:1085`, `:1099`, `:1108`, `:1256`, `:1382`;
`RemoveOccCount.lean:221`); each `#check` applies the refutation to the bridge, so the pair
elaborates only at type `False` (rationale at `Exec.lean:1031-1036`; the commit message
records `graph_correct_refuted graph_correct_explicit : False` re-checked first-hand
2026-09-05). Eight `#check` commands on the branch — the only ones under
`formal/lean/ZanzibarProofs/`:

    Exec.lean:1069  #check graph_correct_refuted graph_correct_explicit
    Exec.lean:1082  #check graph_correct_public_refuted graph_correct_public_explicit
    Exec.lean:1095  #check writeLeg_own_key_dirty_refuted writeLeg_own_key_dirty_explicit
    Exec.lean:1105  #check reachedByW3d2_untOccCount_refuted reachedByW3d2_untOccCount_explicit
    Exec.lean:1114  #check reachedByW3d2_srcOccCount_refuted reachedByW3d2_srcOccCount_explicit
    Exec.lean:1272  #check reachedByW3d2E_untOccCount_refuted_of_general
                      reachedByW3d2E_untOccCount_admitted_drained_explicit        (continues on :1273)
    Exec.lean:1423  #check writeLeg_own_key_dirty_refuted_under_admission writeLeg_own_key_dirty_admitted_explicit
    RemoveOccCount.lean:227  #check reachedByW3d2E_untOccCount_refuted reachedByW3d2E_untOccCount_explicit

## Instrument control (`docs/sabotage-procedure.md`), observed verbatim — `Exec.lean:1038-1049`

Narrowest plausible weakening: R3's guard gains `NotLeafName b.pred`, simulated by an `axiom`
`fake_weakened_R3` of that shape in place of the theorem. The bridge refused (quoted from the
docstring at `Exec.lean:1043-1049`):

    error: Type mismatch
      fake_weakened_R3 x✝² x✝¹ x✝ h
    has type
      ∀ (a b : NodeKey),
        isDerived x✝¹ (b.type, b.pred) = false → NotLeafName b.pred → List.count (a, b) x✝².edges = untOccCount x✝¹ x✝ a b
    but is expected to have type
      ∀ (a b : NodeKey), isDerived x✝¹ (b.type, b.pred) = false → List.count (a, b) x✝².edges = untOccCount x✝¹ x✝ a b

## Reaching the snapshot

Reproduce any of the above: check out the branch and run `lake build` under
`formal/lean` (with `~/.elan/bin` on `PATH`); the commit's self-report is four
`declaration uses `sorry`` warnings and eight `#check` infos of type `False`. As of
2026-09-06 the commit `d6d2dfc` is reachable as branch `p3-flip-red-2026-09-05` (verified with
`git branch --contains d6d2dfc`); whether it also gets a tag is a pending user decision. It
lives off `68f2c69` and must not reach master.
