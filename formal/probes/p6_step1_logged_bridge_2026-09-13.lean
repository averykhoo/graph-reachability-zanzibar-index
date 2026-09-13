/-
  ★ P6 / increment-B STEP 1 — the zero-cone GO/NO-GO, re-measured on the IN-FRAGMENT store
  with the bridge on EVERY leg (prefix included) and with the bridge LOGGED.

  Kept OUTSIDE the lake package on purpose (same reason as
  `d3_negedgefree_postflip_2026-09-05.lean:3-5` and
  `p6_inbridge_stability_2026-09-12.lean:6-9`): it costs ZERO cone, it is not part of the
  gated build, it is evidence that can be re-run.  Run from formal/lean (needs the built
  oleans):

      export PATH="$HOME/.elan/bin:$PATH"
      cd formal/lean && lake env lean ../probes/p6_step1_logged_bridge_2026-09-13.lean

  ⚠ Expect tens of seconds.  rc=0 with no output means a `#eval` silently elaborated to
  `()` — that is a FAILED run, not a green one.

  ── WHY THIS FILE EXISTS: a CORRECTION to the 2026-09-12b / 2026-09-13 row entries ────────

  Task row `P6`'s 2026-09-12b entry recorded, and the 2026-09-13 step-0 entry carried
  forward, that *"the '14 → 9 of 546 mismatches' payoff failure was measured on … the
  out-of-fragment store `Sd`"* / *"a store increment B owes nothing to"*.

  **That attribution is FALSE, and the probe's own source says so.**
  `p6_inbridge_stability_2026-09-12.lean:872-887 P6BridgeProbe.repair` is written entirely
  against `Sp` — `cascadeLeg Sp`, `legB Sp`, `sem Sp` — and `Sp` is the IN-FRAGMENT
  `WideWitness.SwT`-shaped store (`:488-503`), pinned by that file's own
  `("NARROW rejects / WIDE admits the prefix store", some (false, true))`.  `Sd` appears
  only in `§7 routing` (`:902-941`), a different measurement with different numbers
  (`bridgesOnLeafRouted := 0` etc.).  Two sections were conflated into one sentence.

  Re-run first-hand 2026-09-13 before writing a line of this file: rc=0, 335 lines,
  byte-identical to the recorded transcript, `("REPAIR", some { … baseMismatch := 14 …
  bridgedMismatch := 9 })`.  So the payoff criterion for step 1 was NOT "unmeasured"; it
  was measured IN scope, and it FAILED.

  ── THE ACTUAL DEFECT, and what this probe decides ───────────────────────────────────────

  The residual 9 is an INSTRUMENT defect, not a finding about bridges — the hypothesis this
  file tests.  `repair` builds its pre-state with
  `graphRunOps Sp prefixOps` (`:873`), i.e. the PLAIN post-flip driver, and only then
  applies `legB` to the single write `tObj`.  So `tView`'s object endpoint
  `folder:f1#viewer` — the concrete node the whole star-tupleset through-shape hangs off,
  and `alice`'s only route into `doc:d1#access` — is written by a leg that materialises no
  bridge, and no later arm ever goes back for it.  `legB` bridges the endpoints of the
  tuple being written, and `folder:f1#viewer` is not an endpoint of `tObj`.

  Increment B composes `ensureInBridges` into `writeLoggedRules`/`writeRules` themselves, so
  in the shipped design EVERY write bridges, prefix included.  This file measures that
  design: a bridged twin of the op driver (`bridgedRunOps`), not a bridged single write on
  top of a plain prefix.

  Step 1's stated go/no-go (task row `P6`, 2026-09-12b plan): *"does a logged bridge on the
  leaf-routed list bring graph-vs-`sem` mismatches to ZERO after drain?  If not zero, STOP
  and re-plan before any cone is paid."*  §5 answers it; §5's `R-OLD` arm reproduces
  `14 / 9` from the same instrument so the delta is attributable to the prefix and to
  nothing else, and `R-CEIL` is the ceiling control: if maximal bridging still mismatches,
  the bridge is not the missing mechanism and no routing of it can be.

  ── (!) PER-ARM NON-VACUITY, the step-0 lesson, mechanised ────────────────────────────────

  Step 0 (2026-09-13) established that an arm measured where `schemaRewrites S = []` is
  measuring nothing — both `ttuStarFreeB` and `ttuStarFreeWB` are VACUOUSLY true there, so a
  "wide admits" reading means only that nothing was asked.  Every arm below therefore
  carries `Vac` and NO number is to be read without it:

    * `rewrites  > 0`  — the widening predicates are ENGAGED at this store at all;
    * `bridges   > 0`  — this arm's bridge actually fired (0 ⇒ the arm is its own baseline);
    * `narrowRej && wideAdm` — the store is in the newly-admitted region, not merely legal;
    * `unmapped  > 0`  — the stability sweep has a non-empty domain (a green at 0 is vacuous).

  ── THE WITNESS TRAP (scope doc S9.1; inherited from the 2026-09-12 probe :418-427) ───────

  Every domain is ROUTING-INDEPENDENT: built from the CORPUS tuples' objects/subjects and
  the SCHEMA's declared relations (bare and at leaf indices 0/1), NEVER from `σ.nodes` and
  never from `σ.edges`.  A leaf-routed write and a bridge both CHANGE `σ.nodes`, so a
  σ-derived domain would measure nothing.

  ── LITERAL TRANSCRIPT ────────────────────────────────────────────────────────────────────

  ── THE VERDICT: **GO**, with three named residuals, none of them a bridge defect ───────

  1. **THE PAYOFF CRITERION IS MET.**  On the in-fragment store, with the bridge composed
     into every write leg (`bridgedRunOps`), grid mismatches go **14 → 2 of 546**, and the
     CEILING control (`R-CEIL`, every schema-declared bridged-in concrete bridged) reaches
     **0**.  So the bridge is the COMPLETE mechanism for every node a write leg touches, and
     the residual 2 belongs to nodes no write leg creates — see (4).  The `R-OLD-*` arms
     reproduce the 2026-09-12 probe's `14` and `9` exactly, so the improvement is
     attributable to bridging the PREFIX and to nothing else.

  2. **THE LOGGED BRIDGE IS THE WALL-2 REPAIR, CONFIRMED, and the 2026-09-12b prediction
     was right.**  Per-domain (§6), on the subject-endpoint write the 2026-09-12 probe
     called FALSE:
       * `D-SUB` (bridge UNLOGGED): `uReachStable`/`uGraphRecStable`/`uCheckFnStable` all
         **false** at 3 UNMAPPED keys — the tier-1 statements are FALSE, not merely
         in need of a premise;
       * `D-SUB-S` / `D-SUB-T` (bridge LOGGED): the same instruments are all **true**,
         because the delta moves those keys from unmapped (3 → 1) into `cascadeKeys`.
     So `hunmapped` excludes exactly the perturbed keys and **all 23 at-risk stability
     theorems keep their statements**; only the proofs need a "new edges are routed-or-
     bridged" case.  ⚠ SRC and TGT logging are INDISTINGUISHABLE on every number measured
     here — the 2026-09-12b step-2 choice of TGT is therefore free, not pinned, and this
     probe is not evidence for it.

  3. **WALL 2 IS TWO MECHANISMS, NOT ONE — the second is NEW and is a MODEL-FIDELITY BUG.**
       (a) The dead-node bridge GC the 2026-09-12b Wall-2 decision specified is CORRECT:
           `W2-DOM-TGT` (a fresh bridged concrete, `folder:f9#viewer`) leaves `residue := 1`
           and `releaseInBridgesProto` collects it exactly (`releaseFixes := true`), while
           declining on a node that is still live — the `_maybe_remove_bridges` guard.
       (b) ★ **`ensureInBridges` is NOT idempotent on the EDGE MULTISET**: measured
           `(0 calls, 1, 2, 3) = (0, 1, 2, 3)`.  `legB` calls it once per member of the
           leaf-routed list, so `tSub`'s 2-member list (`banned`, `admin.1`, both with
           subject `folder:f1`) leaves `residue := 2` that `RESIDUE DETAIL` shows is
           **EMPTY of new edges** — two extra COPIES of a bridge already present.  The GC
           correctly declines (the node is still live), so the copies accumulate per write.
           **Python does not do this**: `index_v4/wildcard.py::WildcardIndex.
           _ensure_own_bridges` guards with `if not self.idx.direct_edge_exists_by_id(
           node.id, w_any.id)` before `add_edge_by_id`.  The Lean definition
           (`UsStarWrite.lean:213-218`) has no such guard; its docstring claims only
           reachability-level idempotence ("`NReaches` is membership, not multiplicity"),
           which is true and is not enough once a live chain calls it once per routed
           member.  Today this is inert — nothing calls `ensureInBridges` on a live chain
           (`UsStarWrite.lean:112`) — and increment B is exactly what makes it live.
           **DECISION (taken here, `CLAUDE.md` "Who decides"): step 2 adds the presence
           guard to `ensureInBridges`, mirroring Python.**  The direction is forced: the
           proof must describe the shipped code, and the shipped code guards.  Cost: the
           definition change re-opens `structInv_ensureInBridges` (audited
           `Audit.lean:159`) and `ensureInBridges_edges_mem` (audited `Audit.lean:166`),
           both in `UsStarWrite.lean`'s 8-module reverse cone — step-2 work, not step-3.

  4. **THE RESIDUAL 2 IS A PHANTOM SUBJECT, AND IT IS A LEAN-MODEL GAP, NOT A SHIPPED BUG.**
     Both residual mismatches are `folder:f9#viewer` on `doc:d1` at the DERIVED relations
     `admin` and `gate`.  `folder:f9` is mentioned by NO written tuple (`tDom` is
     domain-only), so no write leg ever creates the node — `PHANTOM NODE PRESENT?` reads
     `false` on both the plain and the bridged leg and `true` only at the ceiling.  The
     asymmetry is the content: at that same subject the PLAIN relation `access` answers
     **correctly** (`true`) in the bridged graph model, and only the DERIVED relations are
     wrong.  So the Lean graph model's derived read path needs a materialised concrete node
     where its plain read path answers symbolically.
     **Measured against the shipped Python the same day — there is NO divergence.**
     `tests/parity.py::ParityEngine` (graph index + both `SetOps` + oracle, unanimity
     asserted) on the DSL twin of this schema and store, verbatim:

         graph side present: True | drop reason: None
         phantom f9   ('viewer', 'folder', 'f9', 'access', 'doc', 'd1') -> UNANIMOUS True
         phantom f9   ('viewer', 'folder', 'f9', 'admin',  'doc', 'd1') -> UNANIMOUS True
         phantom f9   ('viewer', 'folder', 'f9', 'gate',   'doc', 'd1') -> UNANIMOUS True
         control f1   ('viewer', 'folder', 'f1', 'access', 'doc', 'd1') -> UNANIMOUS True
         control f1   ('viewer', 'folder', 'f1', 'admin',  'doc', 'd1') -> UNANIMOUS True
         control f1   ('viewer', 'folder', 'f1', 'gate',   'doc', 'd1') -> UNANIMOUS True
         control f2   ('viewer', 'folder', 'f2', 'gate',   'doc', 'd1') -> UNANIMOUS True

     Python answers the phantom correctly on the derived relations because
     `WildcardIndex`'s derived read path is edge probe **plus residue** (`CLAUDE.md`,
     "Layout / mental model"), i.e. symbolic, where the Lean model's is edges alone.  That
     is a `CORRESPONDENCE.md` §7 boundary of the same class as the entity-middle half — NOT
     something increment B owes, and NOT a reason to stop.

  5. **THE TIER-2 GUARD NEEDED DIAGNOSIS, NOT REPLACEMENT — and half of it survives.**
     `guardPre`/`guardPost` read false in all EIGHT arms of the 2026-09-12 probe, BASE
     included, so nothing in tier 2 was measured.  The reason is now named: at `G-PLAIN`
     the failures number **8**, and bridging halves them to **4** (`G-BR-TGT`, `G-CEIL`
     alike) — they were false at BASE because this is exactly the store the unbridged graph
     gets WRONG (`TtuStarWide.lean:32-39`, the 2026-08-10 refutation), which is the whole
     point of the widening.  The residual 4 are NOT a bridge question and are printed as
     rows: all four are `gate` — **stratum 2 only**, never `admin` — at userset subjects
     `folder:f1#viewer`, `folder:f2#viewer`, `folder:f9#viewer`, with
     `checkFn = false`, `GraphModel.check = true`, `sem = true`.  So at the ceiling the two
     READERS disagree with each other: the model's `check` is right and the proof-side
     `checkFn` under-reads the stratum-2 derived relation at a userset subject.  That is a
     bounded, named step-2 item (`writeLeg_sem_stable2`'s tier) and the tier-2 instrument
     itself needs no replacement.

  ── WHAT STEP 2 INHERITS FROM THIS RUN ──────────────────────────────────────────

  * `ensureInBridges` gains the `direct_edge_exists_by_id` presence guard (3(b)) — this is
    ADDITIONAL to the 2026-09-12b step-2 list and re-opens two audited names.
  * `ensureInBridgesLogged` must exist (2), but SRC-vs-TGT is unpinned by measurement; pick
    TGT for `writeLoggedOne` symmetry and say so, do not cite this probe as evidence.
  * `releaseInBridges` is confirmed as specified (3(a)); its guard must be "the concrete's
    only remaining incident edges are its bridges", which declines correctly on live nodes.
  * Two boundary entries for `CORRESPONDENCE.md` §7, both measured here, neither a Python
    bug: the phantom-subject derived read path (4) and the stratum-2 `checkFn`-vs-`check`
    gap (5).

  ── LITERAL TRANSCRIPT ─────────────────────────────────────────────────────────────────

  RAN 2026-09-13, rc=0, 244 lines.  Command:
  `export PATH="$HOME/.elan/bin:$PATH" && cd formal/lean && lake env lean
  ../probes/p6_step1_logged_bridge_2026-09-13.lean`.  Everything between the rules below is
  the VERBATIM stdout: nothing added, removed, reordered or re-indented.

  ---------------------------------- BEGIN VERBATIM ----------------------------------------

("SCHEMA REWRITES (0 would make every widening reading VACUOUS)", 1, [("doc", "access")])
("DOMAINS (subjects, semSubjects, nodes, derivedKeys, grid, ceilNodes)", 42, 42, 144, 4, 546, 7)
("CEIL NODES (every schema-declared bridged-in concrete in the domain)",
  [("folder", "f1", "viewer"), ("folder", "f1", "viewer"), ("folder", "f2", "viewer"), ("folder", "f9", "viewer"),
    ("folder", "f1", "viewer"), ("folder", "f2", "viewer"), ("folder", "f9", "viewer")])
("BRIDGED-IN SHAPE (folder,viewer): (isSubjectWildcardUserset, isStarTuplesetThrough)", true, true)
("CONTROL - BARE pred excluded (must be false)", false)
("PLAIN FULL RUN accepted? / store size", some (true, 3, 6))
("REPAIR ARMS",
 [{ arm := "R-OLD-BASE  (2026-09-12 shape: plain prefix + plain write)",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 6,
             bridges := 0,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 14,
    agree := false,
    sample := [{ s := "user:alice", sp := "...", rel := "access", obj := "doc:d1", graph := false, semv := true },
               { s := "user:bob", sp := "...", rel := "access", obj := "doc:d1", graph := false, semv := true },
               { s := "user:alice", sp := "...", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "user:bob", sp := "...", rel := "admin", obj := "doc:d1", graph := false, semv := true }] },
  { arm := "R-OLD-BR    (2026-09-12 shape: plain prefix + BRIDGED write) -- must be 9",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 10,
             bridges := 4,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 9,
    agree := false,
    sample := [{ s := "user:alice", sp := "...", rel := "access", obj := "doc:d1", graph := false, semv := true },
               { s := "user:alice", sp := "...", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "folder:f1", sp := "viewer", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "folder:f1", sp := "viewer", rel := "admin", obj := "doc:d1", graph := false, semv := true }] },
  { arm := "R-BASE      (whole op stream, plain leg)",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 6,
             bridges := 0,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 14,
    agree := false,
    sample := [{ s := "user:alice", sp := "...", rel := "access", obj := "doc:d1", graph := false, semv := true },
               { s := "user:bob", sp := "...", rel := "access", obj := "doc:d1", graph := false, semv := true },
               { s := "user:alice", sp := "...", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "user:bob", sp := "...", rel := "admin", obj := "doc:d1", graph := false, semv := true }] },
  { arm := "R-BR-OFF    (whole op stream, bridged leg, delta OFF)",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 17,
             bridges := 11,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 2,
    agree := false,
    sample := [{ s := "folder:f9", sp := "viewer", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "folder:f9", sp := "viewer", rel := "gate", obj := "doc:d1", graph := false, semv := true }] },
  { arm := "R-BR-SRC    (whole op stream, bridged leg, delta at bridge SOURCE)",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 17,
             bridges := 11,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 2,
    agree := false,
    sample := [{ s := "folder:f9", sp := "viewer", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "folder:f9", sp := "viewer", rel := "gate", obj := "doc:d1", graph := false, semv := true }] },
  { arm := "R-BR-TGT    (whole op stream, bridged leg, delta at bridge TARGET)",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 17,
             bridges := 11,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 2,
    agree := false,
    sample := [{ s := "folder:f9", sp := "viewer", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "folder:f9", sp := "viewer", rel := "gate", obj := "doc:d1", graph := false, semv := true }] },
  { arm := "R-BR-OBJ    (whole op stream, OBJECT endpoint only, delta at TARGET)",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 17,
             bridges := 11,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 2,
    agree := false,
    sample := [{ s := "folder:f9", sp := "viewer", rel := "admin", obj := "doc:d1", graph := false, semv := true },
               { s := "folder:f9", sp := "viewer", rel := "gate", obj := "doc:d1", graph := false, semv := true }] },
  { arm := "R-CEIL      (plain leg + MAXIMAL schema-declared bridging) -- the ceiling",
    ok := some true,
    vac := { rewrites := 1,
             narrowRej := true,
             wideAdm := true,
             hterm := true,
             legEdges := 6,
             edges := 19,
             bridges := 13,
             frontier := 0,
             drained := true },
    gridSize := 546,
    mismatch := 0,
    agree := true,
    sample := [] }])
("DOMAIN VERDICTS",
 [{ arm := "D-BASE   (plain pre, plain write)",
    keys := 4,
    unmapped := 3,
    mapped := 1,
    uReachStable := true,
    uGraphRecStable := true,
    uCheckFnStable := true,
    mDrained := true,
    mAgree := true,
    mMismatch := 0 },
  { arm := "D-SUB    (plain pre, SUBJ bridge, off)",
    keys := 4,
    unmapped := 3,
    mapped := 1,
    uReachStable := false,
    uGraphRecStable := false,
    uCheckFnStable := false,
    mDrained := true,
    mAgree := true,
    mMismatch := 0 },
  { arm := "D-SUB-S  (plain pre, SUBJ bridge, src)",
    keys := 4,
    unmapped := 1,
    mapped := 3,
    uReachStable := true,
    uGraphRecStable := true,
    uCheckFnStable := true,
    mDrained := true,
    mAgree := false,
    mMismatch := 6 },
  { arm := "D-SUB-T  (plain pre, SUBJ bridge, tgt)",
    keys := 4,
    unmapped := 1,
    mapped := 3,
    uReachStable := true,
    uGraphRecStable := true,
    uCheckFnStable := true,
    mDrained := true,
    mAgree := false,
    mMismatch := 6 },
  { arm := "D-BOTH-T (BRIDGED pre, both, tgt)",
    keys := 4,
    unmapped := 1,
    mapped := 3,
    uReachStable := true,
    uGraphRecStable := true,
    uCheckFnStable := true,
    mDrained := true,
    mAgree := false,
    mMismatch := 2 }])
("GUARD",
 [{ arm := "G-PLAIN (bridge-free pre-state -- the 2026-09-12 configuration)",
    guardPre := false,
    guardPost := false,
    preFails := 8,
    postFails := 8 },
  { arm := "G-BR-TGT(fully bridged pre-state, delta at TARGET)",
    guardPre := false,
    guardPost := false,
    preFails := 4,
    postFails := 4 },
  { arm := "G-CEIL  (plain pre-state + MAXIMAL bridging)",
    guardPre := false,
    guardPost := false,
    preFails := 4,
    postFails := 4 }])
("RESIDUE",
 [{ arm := "W2-SUB-OFF (write+remove tSub, bridge unlogged)",
    preEdges := 17,
    postWrite := 21,
    postRemove := 19,
    residue := 2,
    withRelease := 19,
    releaseFixes := false },
  { arm := "W2-SUB-TGT (write+remove tSub, bridge logged at TARGET)",
    preEdges := 17,
    postWrite := 21,
    postRemove := 19,
    residue := 2,
    withRelease := 19,
    releaseFixes := false },
  { arm := "W2-DOM-TGT (write+remove tDom -- a FRESH bridged concrete, folder:f9#viewer)",
    preEdges := 17,
    postWrite := 19,
    postRemove := 18,
    residue := 1,
    withRelease := 17,
    releaseFixes := true }])
("RESIDUAL DETAIL (bridged leg mismatches, in full; last Bool = the CEILING's answer)",
  [("folder:f9", "viewer", "admin", "doc:d1", false, true, true),
    ("folder:f9", "viewer", "gate", "doc:d1", false, true, true)])
("PHANTOM SUBJECT folder:f9#viewer on doc:d1 (rel, graphBridged, sem, graphCeiling)",
  [("access", true, true, true), ("admin", false, true, true), ("gate", false, true, true),
    ("banned", false, false, false)])
("PHANTOM NODE PRESENT?", [("plain leg", false), ("bridged leg", false), ("ceiling", true)])
("GUARD RESIDUAL at the CEILING (rel, obj, subj, subjPred, checkFn, check, sem)",
  [("gate", "d1", "folder:f1", "viewer", false, true, true), ("gate", "d1", "folder:f1", "viewer", false, true, true),
    ("gate", "d1", "folder:f2", "viewer", false, true, true), ("gate", "d1", "folder:f9", "viewer", false, true, true)])
("ensureInBridges EDGE-MULTISET IDEMPOTENCE (0 calls, 1, 2, 3)", 0, 1, 2, 3)
("RESIDUE DETAIL (edges left after write-then-remove of tSub)", [])
("tSub LEAF-ROUTED LIST (length, members)", 2, [("banned", "folder:f1"), ("admin.1", "folder:f1")])

  ----------------------------------- END VERBATIM -----------------------------------------
-/

import ZanzibarProofs

open Zanzibar

namespace P6Step1

/-! ## §1  The store — verbatim `p6_inbridge_stability_2026-09-12.lean:504-537`

Copied rather than imported: probe files are standalone (outside the lake package), and a
byte-identical copy is what makes the `R-OLD` control a *reproduction* rather than a
re-design.  `(folder, "viewer")` is a declared subject-wildcard userset shape through
disjunct (b) (`UsStarWrite.lean:89 isStarTuplesetThrough` → `:115
isSubjectWildcardUserset`); `doc#admin` is stratum 1, `doc#gate` stratum 2. -/
def Sp : Schema :=
  ⟨[(("folder", "viewer"), .direct [("user", BARE, false)]),
    (("doc", "parent"),    .direct [("folder", BARE, true)]),
    (("doc", "access"),    .ttu "viewer" "parent"),
    (("doc", "banned"),    .direct [("user", BARE, false), ("folder", "viewer", false)]),
    (("doc", "admin"),     .excl (.computed "access") (.computed "banned")),
    (("doc", "gate"),      .inter (.computed "admin") (.computed "access"))], []⟩

def tPar : Tuple := ⟨⟨"folder", STAR, BARE⟩, "parent", ⟨"doc", "d1"⟩⟩
def tView : Tuple := ⟨⟨"user", "alice", BARE⟩, "viewer", ⟨"folder", "f1"⟩⟩
def tObj : Tuple := ⟨⟨"user", "bob", BARE⟩, "viewer", ⟨"folder", "f2"⟩⟩
def tSub : Tuple := ⟨⟨"folder", "f1", "viewer"⟩, "banned", ⟨"doc", "d2"⟩⟩
def tAdm : Tuple := ⟨⟨"user", "dave", BARE⟩, "admin", ⟨"doc", "d1"⟩⟩
def tDom : Tuple := ⟨⟨"user", "carol", BARE⟩, "viewer", ⟨"folder", "f9"⟩⟩

def corpus : List Tuple := [tPar, tView, tObj, tSub, tAdm, tDom]

/-- The 2026-09-12 probe's pre-state: `tView` written by a BRIDGE-FREE leg. -/
def prefixOps : List GraphOp := [GraphOp.add tPar, GraphOp.add tView]

/-- Step 1's pre-state: the same writes, but every one of them goes through the leg under
    test.  `tAdm` (a stored DERIVED-relation tuple) and `tDom` (domain-only) are NOT
    written — they exist to widen the routing-independent domains, exactly as in the
    2026-09-12 probe. -/
def fullOps : List GraphOp := [GraphOp.add tPar, GraphOp.add tView, GraphOp.add tObj]

/-! ## §2  The routing-independent domains  (!) NEVER `σ.nodes`, NEVER `σ.edges` -/

def subjPreds (S : Schema) : List String := BARE :: S.keys.map (·.2)

def objPreds (S : Schema) : List String :=
  S.keys.flatMap (fun k => [k.2, leafPred k.2 0, leafPred k.2 1])

def objsOf (ts : List Tuple) : List ObjectRef :=
  ts.foldl (fun acc t => if acc.contains t.object then acc else acc ++ [t.object]) []

def subjsOf (ts : List Tuple) : List SubjectRef :=
  ts.foldl (fun acc t => if acc.contains t.subject then acc else acc ++ [t.subject]) []

def subjDomain (S : Schema) (ts : List Tuple) : List SubjectRef :=
  subjsOf ts ++ (wildcardShapes S).map starSubj
    ++ (objsOf ts).flatMap (fun o => (subjPreds S).map (fun p => ⟨o.type, o.name, p⟩))

def nodeDomain (S : Schema) (ts : List Tuple) : List NodeKey :=
  (subjDomain S ts).map subjNode
    ++ (objsOf ts).flatMap (fun o => (objPreds S).map (fun p => objNode o p))
    ++ S.keys.map (fun k => wAnyNode (k.1, k.2))
    ++ S.keys.map (fun k => wAllNode k.1 k.2)

structure DKey where
  dt : String
  R : String
  on : String
  e : Expr
deriving Repr, Inhabited

def dkeys (S : Schema) (ts : List Tuple) : List DKey :=
  S.defs.flatMap (fun d =>
    if isDerived S d.1 then
      (objsOf ts).filterMap (fun o =>
        if o.type == d.1.1 && o.name != STAR then some ⟨d.1.1, d.1.2, o.name, d.2⟩ else none)
    else [])

def SUBS : List SubjectRef := subjDomain Sp corpus
def SEMSUBS : List SubjectRef := SUBS.filter (fun s => !(s.name == STAR) || (s.predicate == BARE))
def NODES : List NodeKey := nodeDomain Sp corpus
def KEYS : List DKey := dkeys Sp corpus

def queryGrid (S : Schema) (ts : List Tuple) : List Query :=
  S.keys.flatMap (fun k =>
    (objsOf ts).flatMap (fun o =>
      if o.type == k.1 then (subjDomain S ts).map (fun s => ⟨s, k.2, o⟩) else []))

def GRID : List Query := queryGrid Sp corpus

/-! ## §3  The bridge legs — and the TWO logging conventions, which are not the same edit

`legB`'s `logBridge` in the 2026-09-12 probe pushes the delta at the bridge SOURCE `c`
(`:609`, `pushDelta a a.pred true`).  The 2026-09-12b plan's step 2 specifies
`ensureInBridgesLogged = ensureInBridges + pushDelta (wAnyNode (c.type, c.pred)) c.pred
true` — at the bridge TARGET, which is what `writeLoggedOne` does (delta at the edge's
OBJECT node).  Those are different states, so both are arms here; assuming they agree is
the kind of unmeasured step this row has already paid for twice. -/

inductive LogMode where
  | off  -- no delta
  | src  -- delta at the bridge SOURCE  — the 2026-09-12 `legB logBridge:=true` convention
  | tgt  -- delta at the bridge TARGET  — the 2026-09-12b step-2 spec convention
deriving Repr, DecidableEq, Inhabited

/-- Bridge-before-grant at one endpoint, `UsStarWrite.lean:228 writeUsStar`'s order: the
    endpoint must be live before `ensureInBridges` (its docstring's precondition). -/
def bridgeAt (m : LogMode) (σ : GraphState) (c : NodeKey) : GraphState :=
  if (σ.addNode c).bridgedInConcrete c then
    let σ1 := (σ.addNode c).ensureInBridges c
    match m with
    | .off => σ1
    | .src => σ1.pushDelta c c.pred true
    | .tgt => σ1.pushDelta (wAnyNode (c.type, c.pred)) c.pred true
  else σ

/-- Increment B, candidate routing: bridge the endpoints of every member of the LEAF-ROUTED
    list, then the logged grant.  `bs` bridges the subject endpoint, `bo` the object. -/
def legB (S : Schema) (bs bo : Bool) (m : LogMode) (σ : GraphState) (t : Tuple) : GraphState :=
  (rewriteClosureL S (rawWriteTuples S t)).foldl
    (fun acc u =>
      let a := subjNode u.subject
      let b := objNode u.object u.relation
      let acc1 := if bs then bridgeAt m acc a else acc
      let acc2 := if bo then bridgeAt m acc1 b else acc1
      acc2.writeLoggedOne u) σ

/-- The BRIDGED twin of `Exec.lean:449 graphRunOpsAux`: identical in every respect except
    that the add leg is `legB` instead of `GraphState.writeLoggedRules`.  This is what
    increment B actually is — the bridge composed INTO the write leg, so every write
    bridges, not a bridged write bolted onto a bridge-free prefix. -/
def bridgedRunAux (S : Schema) (bs bo : Bool) (m : LogMode) :
    List GraphOp → GraphState → Store → Option (GraphState × Store)
  | [], σ, T => some (σ, T)
  | GraphOp.add t :: ops, σ, T =>
      if foldAdmitsB σ (rewriteClosureL S (rawWriteTuples S t)) then
        bridgedRunAux S bs bo m ops (cascadeLeg S (t :: T) (legB S bs bo m σ t)) (t :: T)
      else none
  | GraphOp.remove t :: ops, σ, T =>
      if removeGateB S σ T t then
        bridgedRunAux S bs bo m ops (cascadeLeg S (T.erase t) (σ.removeLoggedRules S t))
          (T.erase t)
      else none

def bridgedRunOps (S : Schema) (bs bo : Bool) (m : LogMode) (ops : List GraphOp) :
    Option (GraphState × Store) :=
  bridgedRunAux S bs bo m ops (emptyState S) []

/-- ★ THE CEILING CONTROL.  Every concrete node in the routing-independent domain that the
    SCHEMA declares a bridged-in shape, bridged — regardless of whether any write leg would
    reach it.  This is strictly more bridging than any routing of `ensureInBridges` can
    produce.  If mismatches survive HERE, the bridge is not the missing mechanism and step 3
    must not be paid. -/
def CEILNODES : List NodeKey := NODES.filter (fun n => (emptyState Sp).bridgedInConcrete n)

def ceilBridge (σ : GraphState) : GraphState := CEILNODES.foldl (bridgeAt .tgt) σ

/-! ## §4  Non-vacuity, per arm (the step-0 lesson) -/

structure Vac where
  rewrites   : Nat   -- |schemaRewrites Sp| — 0 ⇒ the widening predicates are NOT ENGAGED
  narrowRej  : Bool  -- ttuStarFreeB  Sp T = false  (the narrow predicate rejects)
  wideAdm    : Bool  -- ttuStarFreeWB Sp T = true   (the widened one admits)
  hterm      : Bool  -- htermB Sp T                 (the fragment's `term` carry)
  legEdges   : Nat   -- |edges| of the PLAIN twin of this arm
  edges      : Nat   -- |edges| of this arm
  bridges    : Nat   -- edges − legEdges: 0 ⇒ this arm IS its baseline, read nothing into it
  frontier   : Nat
  drained    : Bool
deriving Repr

/-! ## §5  ★ THE GO/NO-GO — graph-vs-`sem` over the routing-independent grid -/

structure Miss where
  s : String
  sp : String
  rel : String
  obj : String
  graph : Bool
  semv : Bool
deriving Repr

def missesOf (S : Schema) (T : Store) (σ : GraphState) : List Miss :=
  (GRID.filterMap (fun q =>
    let g := GraphModel.check σ q
    let sv := sem S T q
    if g == sv then none
    else some ⟨q.subject.type ++ ":" ++ q.subject.name, q.subject.predicate,
               q.relation, q.object.type ++ ":" ++ q.object.name, g, sv⟩))

structure RepairArm where
  arm      : String
  ok       : Option Bool        -- `none` = the driver REFUSED the op stream (gate failure)
  vac      : Vac
  gridSize : Nat
  mismatch : Nat
  agree    : Bool
  sample   : List Miss          -- first 4 residuals, so a nonzero is ATTRIBUTABLE
deriving Repr

def mkVac (T : Store) (σplain σ : GraphState) : Vac :=
  { rewrites := (schemaRewrites Sp).length
    narrowRej := ttuStarFreeB Sp T == false
    wideAdm := ttuStarFreeWB Sp T
    hterm := htermB Sp T
    legEdges := σplain.edges.length
    edges := σ.edges.length
    bridges := σ.edges.length - σplain.edges.length
    frontier := σ.frontierRows.length
    drained := drainedB Sp σ }

def mkRepair (nm : String) (σplain : GraphState) (r : Option (GraphState × Store)) : RepairArm :=
  match r with
  | none => { arm := nm, ok := none
              vac := mkVac [] σplain σplain, gridSize := GRID.length
              mismatch := 0, agree := false, sample := [] }
  | some (σ, T) =>
      let ms := missesOf Sp T σ
      { arm := nm, ok := some true
        vac := mkVac T σplain σ
        gridSize := GRID.length
        mismatch := ms.length
        agree := ms.isEmpty
        sample := ms.take 4 }

/-- The 2026-09-12 shape, reproduced EXACTLY: plain prefix, then one bridged write.  Its
    two numbers must come back `14` and `9` or this file's instrument is not that one and
    the comparison below means nothing. -/
def oldShape (bridged : Bool) : Option (GraphState × Store) :=
  (graphRunOps Sp prefixOps).map (fun p =>
    let σ0 := p.1
    let T0 := p.2
    let To := tObj :: T0
    let σw := if bridged then legB Sp true true .off σ0 tObj
              else σ0.writeLoggedRules Sp tObj
    (cascadeLeg Sp To σw, To))

def plainFull : Option (GraphState × Store) := graphRunOps Sp fullOps

def plainFullState : GraphState :=
  match plainFull with | some p => p.1 | none => emptyState Sp

def ceilArm : Option (GraphState × Store) :=
  plainFull.map (fun p => (cascadeLeg Sp p.2 (ceilBridge p.1), p.2))

def repairArms : List RepairArm :=
  let oldPlainState : GraphState :=
    match oldShape false with | some p => p.1 | none => emptyState Sp
  [ mkRepair "R-OLD-BASE  (2026-09-12 shape: plain prefix + plain write)"
      oldPlainState (oldShape false)
  , mkRepair "R-OLD-BR    (2026-09-12 shape: plain prefix + BRIDGED write) -- must be 9"
      oldPlainState (oldShape true)
  , mkRepair "R-BASE      (whole op stream, plain leg)"
      plainFullState plainFull
  , mkRepair "R-BR-OFF    (whole op stream, bridged leg, delta OFF)"
      plainFullState (bridgedRunOps Sp true true .off fullOps)
  , mkRepair "R-BR-SRC    (whole op stream, bridged leg, delta at bridge SOURCE)"
      plainFullState (bridgedRunOps Sp true true .src fullOps)
  , mkRepair "R-BR-TGT    (whole op stream, bridged leg, delta at bridge TARGET)"
      plainFullState (bridgedRunOps Sp true true .tgt fullOps)
  , mkRepair "R-BR-OBJ    (whole op stream, OBJECT endpoint only, delta at TARGET)"
      plainFullState (bridgedRunOps Sp false true .tgt fullOps)
  , mkRepair "R-CEIL      (plain leg + MAXIMAL schema-declared bridging) -- the ceiling"
      plainFullState ceilArm ]

/-! ## §6  Per-domain stability — the verdict the 2026-09-12 probe could not give

`reachStableAll` conflated two populations.  Here the probed keys are SPLIT and each half
gets its own verdict, which is what the 2026-09-12b plan asked for:

* UNMAPPED keys — literally `writeLeg_reach_stable`'s `hunmapped`
  (`CascadeStable.lean:367`).  These must be stable or the theorem is FALSE, not merely
  in need of a premise.
* MAPPED keys — the bridge dirtied them.  The theorems do not speak here; what must hold
  instead is that the DRAINED cascade agrees with `sem`, i.e. the dirt is reconciled. -/

structure Domains where
  arm            : String
  keys           : Nat
  unmapped       : Nat
  mapped         : Nat
  -- unmapped half: the tier-1 instruments, restricted
  uReachStable   : Bool
  uGraphRecStable: Bool
  uCheckFnStable : Bool
  -- mapped half: does the drained cascade agree with `sem` at exactly those keys?
  mDrained       : Bool
  mAgree         : Bool
  mMismatch      : Nat
deriving Repr

def domainsOf (nm : String) (σ σ' : GraphState) (T' : Store) : Domains :=
  let ck := cascadeKeys Sp σ'
  let ksU := KEYS.filter (fun k => !(ck.contains (k.dt, k.R, k.on)))
  let ksM := KEYS.filter (fun k => ck.contains (k.dt, k.R, k.on))
  let drained := cascadeLeg Sp T' σ'
  { arm := nm
    keys := KEYS.length
    unmapped := ksU.length
    mapped := ksM.length
    uReachStable :=
      ksU.all (fun k => (computedRefs k.e).all (fun r' =>
        NODES.all (fun x =>
          σ'.reach x (objNode ⟨k.dt, k.on⟩ r') == σ.reach x (objNode ⟨k.dt, k.on⟩ r'))))
    uGraphRecStable :=
      ksU.all (fun k => (computedRefs k.e).all (fun r' =>
        SUBS.all (fun s =>
          GraphModel.graphRec σ' s k.dt k.on r' == GraphModel.graphRec σ s k.dt k.on r')))
    uCheckFnStable :=
      ksU.all (fun k => SUBS.all (fun s =>
        σ'.checkFn T' s k.dt k.on k.R k.e == σ.checkFn T' s k.dt k.on k.R k.e))
    mDrained := drainedB Sp drained
    mAgree :=
      ksM.all (fun k => SEMSUBS.all (fun s =>
        GraphModel.check drained ⟨s, k.R, ⟨k.dt, k.on⟩⟩ == sem Sp T' ⟨s, k.R, ⟨k.dt, k.on⟩⟩))
    mMismatch :=
      (ksM.flatMap (fun k => SEMSUBS.filter (fun s =>
        !(GraphModel.check drained ⟨s, k.R, ⟨k.dt, k.on⟩⟩ == sem Sp T' ⟨s, k.R, ⟨k.dt, k.on⟩⟩)))).length }

/-- The write under test is `tSub` (subject-endpoint bridging, the arm the 2026-09-12 probe
    called FALSE) applied to each arm's own pre-state. -/
def domainArms : List Domains :=
  let mk := fun (nm : String) (pre : Option (GraphState × Store)) (m : LogMode) (bs bo : Bool) =>
    match pre with
    | none => domainsOf (nm ++ " [DRIVER REFUSED]") (emptyState Sp) (emptyState Sp) []
    | some (σ0, T0) =>
        let Ts := tSub :: T0
        domainsOf nm σ0 (legB Sp bs bo m σ0 tSub) Ts
  [ mk "D-BASE   (plain pre, plain write)"        plainFull .off false false
  , mk "D-SUB    (plain pre, SUBJ bridge, off)"   plainFull .off true  false
  , mk "D-SUB-S  (plain pre, SUBJ bridge, src)"   plainFull .src true  false
  , mk "D-SUB-T  (plain pre, SUBJ bridge, tgt)"   plainFull .tgt true  false
  , mk "D-BOTH-T (BRIDGED pre, both, tgt)"
      (bridgedRunOps Sp true true .tgt fullOps) .tgt true true ]

/-! ## §7  The tier-2 guard, diagnosed rather than reported

`guardPre`/`guardPost` (`σ.checkFn T = sem S T`) read FALSE in all EIGHT arms of the
2026-09-12 probe, BASE included — so the tier-2 premises were never satisfied and nothing
in tier 2 was measured.  The 2026-09-12b plan asked: "find what state they need and build
it".

The answer this section tests: they read false at BASE **because the store is exactly the
one the graph gets WRONG without a bridge** (`TtuStarWide.lean:32-39`; the 2026-08-10
refutation).  `checkFn_eq_sem_w3d` carries `ttuStarFree`, which is FALSE here — that is the
entire point of the widening.  If so, the guard is not broken and needs no replacement: it
becomes TRUE exactly when the bridge is present everywhere, and that is a stronger statement
than a repaired instrument would be. -/

structure Guard where
  arm       : String
  guardPre  : Bool   -- σ.checkFn T = sem S T at the PRE state
  guardPost : Bool   -- σ'.checkFn T' = sem S T' at the POST state
  preFails  : Nat
  postFails : Nat
deriving Repr

def guardOf (nm : String) (σ : GraphState) (T : Store) (σ' : GraphState) (T' : Store) : Guard :=
  let bad := fun (st : GraphState) (S : Store) =>
    (KEYS.flatMap (fun k => SEMSUBS.filter (fun s =>
      !(st.checkFn S s k.dt k.on k.R k.e == sem Sp S ⟨s, k.R, ⟨k.dt, k.on⟩⟩)))).length
  { arm := nm
    guardPre := bad σ T == 0
    guardPost := bad σ' T' == 0
    preFails := bad σ T
    postFails := bad σ' T' }

def guardArms : List Guard :=
  let g := fun (nm : String) (pre : Option (GraphState × Store)) =>
    match pre with
    | none => guardOf (nm ++ " [DRIVER REFUSED]") (emptyState Sp) [] (emptyState Sp) []
    | some (σ0, T0) =>
        let Ts := tSub :: T0
        guardOf nm σ0 T0 (cascadeLeg Sp Ts (σ0.writeLoggedRules Sp tSub)) Ts
  [ g "G-PLAIN (bridge-free pre-state -- the 2026-09-12 configuration)" plainFull
  , g "G-BR-TGT(fully bridged pre-state, delta at TARGET)"
      (bridgedRunOps Sp true true .tgt fullOps)
  , g "G-CEIL  (plain pre-state + MAXIMAL bridging)" ceilArm ]

/-! ## §8  Wall 2 — the bridge-only residue on a write-then-remove, as a NUMBER

`removeLoggedRules` (`Cascade.lean:340`) folds `removeLoggedOne` over the same leaf-routed
list the write folds — so it retracts the routed edges and NOT the bridges.  Write then
remove the SAME tuple and the graph should return to its pre-write edge multiset; whatever
is left is the bridge residue increment B's `releaseInBridges` (2026-09-12b Wall-2 decision)
exists to collect.

`releaseInBridgesProto` is a PROTOTYPE only — it lives in this probe, not in the model, and
its job here is to turn "some GC is needed" into "this much residue, and this collects it".
It mirrors `index_v4/wildcard.py::WildcardIndex._maybe_remove_bridges` (`:363-386`): drop
the bridge iff the concrete node's only remaining incident edge IS its bridge. -/

def GraphState.releaseInBridgesProto (σ : GraphState) (c : NodeKey) : GraphState :=
  if σ.bridgedInConcrete c then
    let w := wAnyNode (c.type, c.pred)
    let others := σ.edges.filter (fun e =>
      (e.1 == c || e.2 == c) && !(e.1 == c && e.2 == w))
    if others.isEmpty then σ.removeEdgeOne c w else σ
  else σ

structure Residue where
  arm          : String
  preEdges     : Nat
  postWrite    : Nat
  postRemove   : Nat
  residue      : Nat   -- postRemove − preEdges: bridge edges the retract leg left behind
  withRelease  : Nat   -- the same, with the `releaseInBridges` prototype composed in
  releaseFixes : Bool  -- withRelease = preEdges
deriving Repr

def residueArms : List Residue :=
  let mk := fun (nm : String) (m : LogMode) (t : Tuple) =>
    match bridgedRunOps Sp true true m fullOps with
    | none => ({ arm := nm ++ " [DRIVER REFUSED]", preEdges := 0, postWrite := 0,
                 postRemove := 0, residue := 0, withRelease := 0, releaseFixes := false } : Residue)
    | some (σ0, _) =>
        let σw := legB Sp true true m σ0 t
        let σr := σw.removeLoggedRules Sp t
        let ends := (rewriteClosureL Sp (rawWriteTuples Sp t)).flatMap
          (fun u => [subjNode u.subject, objNode u.object u.relation])
        let σg := ends.foldl (fun acc c => GraphState.releaseInBridgesProto acc c) σr
        { arm := nm
          preEdges := σ0.edges.length
          postWrite := σw.edges.length
          postRemove := σr.edges.length
          residue := σr.edges.length - σ0.edges.length
          withRelease := σg.edges.length
          releaseFixes := σg.edges.length == σ0.edges.length }
  [ mk "W2-SUB-OFF (write+remove tSub, bridge unlogged)" .off tSub
  , mk "W2-SUB-TGT (write+remove tSub, bridge logged at TARGET)" .tgt tSub
  , mk "W2-DOM-TGT (write+remove tDom -- a FRESH bridged concrete, folder:f9#viewer)" .tgt tDom ]

/-! ## §10  ATTRIBUTION — every residual number above, named

Run 1 (2026-09-13) produced three nonzero numbers with no name attached: the bridged leg's
`mismatch := 2`, the guard's `preFails := 4` at the CEILING, and the write-then-remove
`residue := 2` that the GC prototype declined to collect.  A number whose cause is not
named is indistinguishable from a broken instrument — the lesson `P6` step 0 paid for when
an inverted regex made a clean module read as a discovery.  This section names all three. -/

/-- The residual grid mismatches of the bridged leg, in FULL (not a `take 4` sample), each
    beside the same query at the CEILING arm — so "the ceiling fixes it" is visible per row
    rather than inferred from two totals. -/
def residualDetail : List (String × String × String × String × Bool × Bool × Bool) :=
  match bridgedRunOps Sp true true .tgt fullOps, ceilArm with
  | some (σb, Tb), some (σc, _) =>
      GRID.filterMap (fun q =>
        let g := GraphModel.check σb q
        let sv := sem Sp Tb q
        if g == sv then none
        else some (q.subject.type ++ ":" ++ q.subject.name, q.subject.predicate,
                   q.relation, q.object.type ++ ":" ++ q.object.name, g, sv,
                   GraphModel.check σc q))
  | _, _ => []

/-- ★ The asymmetry the residual exposes: at the SAME phantom subject, the PLAIN relation
    `access` and the DERIVED relations `admin`/`gate` do not answer alike.  If `access`
    agrees while `admin` does not, the missing in-bridge is load-bearing only on the DERIVED
    read path — a boundary statement, not a bridge defect. -/
def phantomSubject : SubjectRef := ⟨"folder", "f9", "viewer"⟩

def phantomProbe : List (String × Bool × Bool × Bool) :=
  match bridgedRunOps Sp true true .tgt fullOps, ceilArm with
  | some (σb, Tb), some (σc, _) =>
      ["access", "admin", "gate", "banned"].map (fun r =>
        (r, GraphModel.check σb ⟨phantomSubject, r, ⟨"doc", "d1"⟩⟩,
            sem Sp Tb ⟨phantomSubject, r, ⟨"doc", "d1"⟩⟩,
            GraphModel.check σc ⟨phantomSubject, r, ⟨"doc", "d1"⟩⟩))
  | _, _ => []

/-- Is `folder:f9#viewer` a node the write leg ever creates?  `tDom` is deliberately never
    written, so this must be `false` in every arm except the CEILING — which is the whole
    content of the residual. -/
def phantomNodePresent : List (String × Bool) :=
  match bridgedRunOps Sp true true .tgt fullOps, ceilArm, plainFull with
  | some (σb, _), some (σc, _), some (σp, _) =>
      [("plain leg", σp.nodes.contains (subjNode phantomSubject)),
       ("bridged leg", σb.nodes.contains (subjNode phantomSubject)),
       ("ceiling", σc.nodes.contains (subjNode phantomSubject))]
  | _, _, _ => []

/-- The guard's residual failures, NAMED: which (key, subject) pairs still have
    `checkFn ≠ sem` at the CEILING, where `GraphModel.check` agrees on the whole grid.
    The `check` column is printed BESIDE `checkFn` so "these two readers disagree" is a
    row, not an inference from two totals. -/
def guardResidual : List (String × String × String × String × Bool × Bool × Bool) :=
  match ceilArm with
  | none => []
  | some (σ, T) =>
      KEYS.flatMap (fun k => SEMSUBS.filterMap (fun s =>
        let c := σ.checkFn T s k.dt k.on k.R k.e
        let sv := sem Sp T ⟨s, k.R, ⟨k.dt, k.on⟩⟩
        if c == sv then none
        else some (k.R, k.on, s.type ++ ":" ++ s.name, s.predicate, c,
                   GraphModel.check σ ⟨s, k.R, ⟨k.dt, k.on⟩⟩, sv)))

/-- ★ **Is `ensureInBridges` idempotent on the EDGE MULTISET?**  Its docstring
    (`UsStarWrite.lean:210-212`) claims only reachability-level idempotence — "`NReaches` is
    membership, not multiplicity".  But `legB` calls it once per member of the leaf-routed
    list, and a subject endpoint shared by two members is therefore bridged TWICE.  If each
    call appends a copy, increment B leaks one bridge copy per extra routed member on every
    write, and the retract leg — which erases ONE copy (`removeEdgeOne`) — cannot keep up.
    That is the `_leak_accumulates` shape (`history/PROOF_STATUS.md` sec 3 at :404-411),
    which is why this is measured rather than assumed. -/
def bridgeIdempotence : (Nat × Nat × Nat × Nat) :=
  let c : NodeKey := ⟨"folder", "f1", "viewer", Variant.plain⟩
  let σ0 := (emptyState Sp).addNode c
  let σ1 := σ0.ensureInBridges c
  let σ2 := σ1.ensureInBridges c
  let σ3 := σ2.ensureInBridges c
  (σ0.edges.length, σ1.edges.length, σ2.edges.length, σ3.edges.length)

/-- The write-then-remove residue, itemised: the actual edges left behind, so
    "2 bridge edges" can be read as "one bridge, twice" or "two distinct bridges". -/
def residueDetail : List (String × String × String × String) :=
  match bridgedRunOps Sp true true .tgt fullOps with
  | none => []
  | some (σ0, _) =>
      let σw := legB Sp true true .tgt σ0 tSub
      let σr := σw.removeLoggedRules Sp tSub
      -- edges present after the retract that were NOT present before the write
      let extra := σr.edges.filter (fun e => !(σ0.edges.contains e))
      extra.map (fun e =>
        (e.1.type ++ ":" ++ e.1.name, e.1.pred, e.2.type ++ ":" ++ e.2.name, e.2.pred))

/-- How many members of `tSub`'s leaf-routed list share the bridged subject endpoint —
    the multiplier on the duplication above. -/
def tSubRouting : (Nat × List (String × String)) :=
  let us := rewriteClosureL Sp (rawWriteTuples Sp tSub)
  (us.length, us.map (fun u => (u.relation, u.subject.type ++ ":" ++ u.subject.name)))

/-! ## §9  Output -/

/-! ### The store, and that the region is ENGAGED at all (step-0's lesson) -/
#eval ("SCHEMA REWRITES (0 would make every widening reading VACUOUS)",
       (schemaRewrites Sp).length, (schemaRewrites Sp).map (fun r => (r.objectType, r.outRel)))
#eval ("DOMAINS (subjects, semSubjects, nodes, derivedKeys, grid, ceilNodes)",
       SUBS.length, SEMSUBS.length, NODES.length, KEYS.length, GRID.length, CEILNODES.length)
#eval ("CEIL NODES (every schema-declared bridged-in concrete in the domain)",
       CEILNODES.map (fun n => (n.type, n.name, n.pred)))
#eval ("BRIDGED-IN SHAPE (folder,viewer): (isSubjectWildcardUserset, isStarTuplesetThrough)",
       Sp.isSubjectWildcardUserset "folder" "viewer", Sp.isStarTuplesetThrough "folder" "viewer")
#eval ("CONTROL - BARE pred excluded (must be false)", Sp.isSubjectWildcardUserset "folder" BARE)
#eval ("PLAIN FULL RUN accepted? / store size",
       plainFull.map (fun p => (drainedB Sp p.1, p.2.length, p.1.edges.length)))

/-! ### ★ THE GO/NO-GO -/
#eval ("REPAIR ARMS", repairArms)

/-! ### Per-domain stability (unmapped half vs bridge-mapped half) -/
#eval ("DOMAIN VERDICTS", domainArms)

/-! ### The tier-2 guard, diagnosed -/
#eval ("GUARD", guardArms)

/-! ### Wall 2: the bridge-only residue, and whether a GC prototype collects it -/
#eval ("RESIDUE", residueArms)

/-! ### §10 ATTRIBUTION — every residual above, named -/
#eval ("RESIDUAL DETAIL (bridged leg mismatches, in full; last Bool = the CEILING's answer)",
       residualDetail)
#eval ("PHANTOM SUBJECT folder:f9#viewer on doc:d1 (rel, graphBridged, sem, graphCeiling)",
       phantomProbe)
#eval ("PHANTOM NODE PRESENT?", phantomNodePresent)
#eval ("GUARD RESIDUAL at the CEILING (rel, obj, subj, subjPred, checkFn, check, sem)", guardResidual)
#eval ("ensureInBridges EDGE-MULTISET IDEMPOTENCE (0 calls, 1, 2, 3)", bridgeIdempotence)
#eval ("RESIDUE DETAIL (edges left after write-then-remove of tSub)", residueDetail)
#eval ("tSub LEAF-ROUTED LIST (length, members)", tSubRouting)

end P6Step1
