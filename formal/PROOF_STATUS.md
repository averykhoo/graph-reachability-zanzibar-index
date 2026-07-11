# PROOF_STATUS.md — the append-only session ledger

**A fresh session reads `formal/HANDOFF.md` FIRST** (the compact entry point: state of
the world, the next task, house rules). This file is the append-only ledger backing it
— newest entry first; read only the TOP entry for resume-point detail, deeper entries
on demand. Before ending ANY session: add a session entry at the top here AND refresh
HANDOFF.md's "The next task".

---

## Session 2026-07-11e (W3d design + W3d-1a — the cascade scheduling layer: logged writes, delta→key mapping, `runCascade`, contentful T5)

Resuming from HANDOFF "W3d: design first." Two green+pushed increments: (1) the W3d design
committed to ROADMAP ("W3d — the multi-stratum cascade", modeling decisions 1–6 + sub-staging
1a/1b/1c/2); (2) W3d-1a delivered in new `GraphIndex/Cascade.lean` (+ `Audit.lean` 7 new
entries, root aggregator). `verify.sh` green (build + 0 sorries + zcli + standard-axioms audit
+ 60 conformance). Sorry count held at 0.

**Design-phase attack finding (analytic, recorded in ROADMAP decision 1): per-SEED delta
coalescing is WRONG.** Python emits one outbox row per materialized closure-pair flip; the
model materializes no closure, so rows must be reconstructed. Coalescing to one row per RAW
write fails: a computed rewrite routes the seed onto sibling family nodes (`editor@doc:1`
also lands `viewer@doc:1` under `viewer := editor or …`) with NO graph edge from the seed's
object node to the sibling node — the seed-node reach cone misses the sibling operand key.
Correct unit: one row per accepted ROUTED edge (`writeLoggedOne` inside the `writeRules`
fold), object ends recovered at cascade time as the routed edge head's reach cone (add-only
⇒ superset of the write-time per-flip set ⇒ at worst extra idempotent reconciles).

**Structural finding: the W3a–W3c chain shape cannot host the scheduler.** `ReachedByW3c` is
"one admitted base, then passes" — no write AFTER a reconcile is expressible, but the
scheduler interleaves (write txn → cascade → write txn → cascade). So W3d gets a NEW
interleaved closure `ReachedByW3d` (write legs carry `FoldAdmits`; cascade legs carry job
validity + two-sided key coverage `hcover`/`hscope`), and the W3c master/`Inv` transfer is
NOT pointwise — a mid-chain pass's residue row reflects a PREFIX store, and its current
validity rests on "later writes didn't touch this key's operand cone", which is exactly the
W3d-1b fan-out-completeness content (see HANDOFF "The next task").

**Increment — `GraphIndex/Cascade.lean` (W3d-1a, the scheduling layer).**
- Outbox primitives: `maxOutboxId` (+ fold-max algebra), `nextDeltaId = max maxOutboxId
  watermark + 1` (decision 2: strictly above BOTH — plain `maxId+1` could mint a
  born-drained row), `pushDelta` (+ core-untouched simps, `pushDelta_maxOutboxId`).
- Logged writes: `writeLoggedOne` (emit iff admitted) / `writeLoggedRules`; **`EvalEq`** (the
  read-relevant core: schema/edges/nodes/residue — `CoreEq` is too strong once outboxes
  genuinely differ) with the congruence spine: `admitEdge_evalEq`, `writeDirect_evalEq`,
  `writeLoggedRules_evalEq` (logged core = unlogged `writeRules` — ALL W2 edge facts
  transfer), and the pass side `reconcileResidueKey_evalEq` / `reconcileKeyC_evalEq` /
  `reconcileStarsKey_evalEq` / `reconcileJobsL_evalEq` (logged batch core = `reconcileJobsC`).
- The mapping: `affectedObjects` (row node + cascade-time reach cone), `affectedKeys`
  (declared derived keys reading a candidate object's predicate as a computed operand —
  `_map_deltas_to_keys` LeafFamily branch + `_fan_out` `via='computed'`, fragment-restricted;
  star-named objects excluded per `processor.py:604-605`), `frontierRows`, `cascadeKeys`.
- The logged pass: `W3cJob.key`/`applyLogged` (pass + ONE coalesced row at its derived key —
  faithful because ALL the pass's per-flip rows share that object end by R-node terminality),
  `reconcileJobsL` + watermark/outbox bookkeeping (`reconcileJobsL_outbox_sound`: every row is
  original or a pass row at a job key with id above the pre-batch frontier).
- **`runCascade`** (decision 5): reconcile the mapped keys, then Python's final leftover check
  (`InvariantViolation` at `processor.py:729-739`) as an accept/REJECT branch — reject = state
  unchanged (the abort rolls the transaction back), accept = watermark past everything.
- **T5, contentful, both halves**: `runCascade_no_abort` — on the fragment the reject NEVER
  fires: a leftover row is pass-emitted (outbox soundness + id arithmetic), sits at a terminal
  derived R-node (`reachedByW3d_edge_source_ne_R` re-proved by direct induction over the
  interleaved closure: write-leg sources are rewrite-closure subjects ≠ R via `NoTtuTarget` +
  prefix-weakened `NoStoreSubjectR`; cascade-leg sources are bare candidates ≠ R; plus the
  mid-batch variant `reconcileJobsL_Rnode_not_source`), so its reach cone is empty and its own
  predicate is derived — which no derived def reads as a computed operand (`hLU`) ⇒
  `affectedKeys = []`. `cascade_drains` — the post-cascade state is `Quiescent`, the watermark
  advance EARNED by no-abort, never asserted (the fix for the deleted-as-vacuous
  `cascade_converges` shape).

**Attack-first (machine-checked `#eval` vs the real `check`/`sem`; scratch deleted, recorded
in the Cascade.lean header).** `viewer := member ∖ banned` (`member` admitting `user`,
`user:*`, `group#mem`), 5 logged writes: all 5 frontier rows mapped to the viewer key (direct,
star, userset, group-flow cones); `runCascade` with one covering job ACCEPTED (watermark 0→6),
`Quiescent` held, and the 18-query grid matched `sem` exactly (bare incl. a ghost
concrete-under-star, star, userset subjects). **Cross-key hazard confirmed live**: a
post-cascade `banned` write re-mapped the EXISTING viewer key through the `banned` operand
cone; until the second cascade the derived read was STALE (`check = true ≠ sem = false` for
the newly-banned subject) — so the read-correctness claim scope is CASCADED states (faithful:
Python runs `run_cascade` inside every writing transaction). The second cascade's own pass row
mapped to `[]`; an empty-frontier cascade was a no-op accept. No refutation.

**Proof-engineering notes:** hypotheses mentioning the inductive's indices (`S`, `T`) must sit
RIGHT of the colon or `induction` auto-reverts them into the motive with surprising ih shapes
(`reachedByW3d_edge_source_ne_R` takes `NoTtuTarget`/`NoStoreSubjectR` as explicit arrows, the
store one re-derived per write leg by prefix weakening). `Prod` eta is definitional: `S.lookup
k` vs `S.lookup (k.1, k.2)` interchange freely, so `hLU k.1 k.2 e hlk` typechecks directly.

**Resume → W3d-1b (see HANDOFF "The next task").**

## Session 2026-07-11d (W3c read half step 3 — CLOSED: the linchpin, the batch completeness layer, `graph_correct_w3c`, T3/T6 `*_w3c`)

Resuming from HANDOFF "W3c read half, step 3: the linchpin lemma + `graph_correct_w3c`." Two
green+pushed axiom-clean increments (all in `GraphIndex/ReconcileStarsComplete.lean`, + `Equiv.lean`,
`Audit.lean` [10 new entries]); `verify.sh` green throughout (build + 0 sorries + zcli +
standard-axioms audit + 60 conformance). Sorry count held at 0. **This CLOSES W3c** — the full
read↔`sem` correspondence on star-carrying stores, all three `probeDerived` branches.

**Attack-first (recorded in the file's coverage-section header; scratch deleted).** Small
`viewer := member ∖ banned` corpus with a `user:*` grant, a concrete-under-star exclusion, a
userset member, and a group-routed concrete: (1) the planned `W3cComplete` read = `sem` on the
full grid; (2) a second full same-key pass is idempotent; (3) **NECESSITY finding**: a second
same-key pass whose `negCands` omit the excluded subject DROPS it from `neg` (the residue is a
WHOLESALE per-pass recompute) and the read flips to `true` ≠ `sem` — so the completeness clauses
MUST quantify over **every job targeting a key**, not one covering job (edges are monotone, so
edge coverage stays ∃-form). Faithful to Python: every `reconcile` call re-derives the full audit
enumeration (`_leaf_concretes` ∪ persisted ids). Linchpin sanity re-checked (`coveredFn` true
exactly on the declared shape).

**Increment 1 — the LINCHPIN + row char + batch completeness.**
- `coveredFn_declared` (**the linchpin**, Route 2 graph-level as planned): `coveredFn σ0 sh =
  true → sh ∈ wildcardShapes S`. Chain: `evalE_computedOnly_true_leaf` (a `ComputedOnly` tree is
  true only via a true `computed` leaf) → the star subject's probes leave from its own `wAny`
  node (probes 2/4 dead) → `nreaches_first_edge` → `reachedByRules_edge_sound` (the first edge is
  a materialised closure tuple with `subjNode u.subject = wAnyNode sh`) →
  `rewriteClosure_star_subject` (a star closure member carries its stored seed's subject) →
  `StoreValidRules` + `restrictionMatches`' wildcard flag → `mem_exprRestrictions_of_directs` →
  a `wildcardShapes` entry.
- `w3c_row_char`: on any W3c state, a persisted row reads at `sem` level — `stars.contains sh ↔
  (sh ∈ wildcardShapes S ∧ sem(starSubj sh))` (master + `checkFn_eq_sem_bs` at the master base;
  `hWSbare` makes declared star subjects BARE), `neg` members star-free ∧ `sem`-false, `upos`
  members star-free usersets ∧ `sem`-true.
- `W3cJob.keyMatch`, `reconcileJobsC_row_isSome` (row existence: a targeting job creates the row;
  rows never deleted), `reconcileJobsC_neg_complete` / `reconcileJobsC_upos_complete` (induction
  over the batch: a targeting pass re-derives membership from its own guard — `checkFn = sem` at
  every W3c-reached pass start via `checkFn_eq_sem_w3c`, pass-start `stars` = the canonical
  filter; a non-targeting pass leaves the row; the ∀-targeting-jobs enumeration hypothesis
  carries survival).

**Increment 2 — `W3cComplete` + the assembly + T3/T6.**
- `probeDerived_eq`: the full residue read unfolded on explicit components (star / bare / userset
  branches) at a concrete object.
- `W3cComplete`: admitted base + valid `W3cJob` batch + coverage clauses — edge cands ∃-covering
  (per `sem`-true bare), `upos`/`neg` cands ∀-targeting-jobs (per `sem`-true userset / per
  covered-`sem`-false star-free subject), and row existence (every key with a declared
  `sem`-covered shape is targeted). `w3cComplete_reached`.
- `w3cComplete_derived_edge`: a `sem`-true canonically-UNCOVERED bare's edge materialises — it
  survives the covering job's covered filter (pass-start row = canonical stars, `coveredFn σpre =
  sem` via the bridge), guard `sem`-true at every prefix mid-state (the master pattern:
  W3a-admitted shadow of the pass start + `graphRec_reconcileKey_inert` + `checkFn_congr` across
  the residue half), `reconcileKey_edge_present` at the terminal R-node, edges monotone through
  the tail.
- **T2b `graph_correct_w3c`**: `check = sem` for `W3cComplete` states over `BareStarStore` +
  `TtuStarFree` stores, query scope = concrete object + (concrete ∨ star-BARE ∨ userset) subject
  (`hqs : name = STAR → predicate = BARE`), fragment + `hWSbare` (decision-15: bare-only declared
  wildcard shapes). Branches: star ⇒ `stars` (row char forward; linchpin + row existence
  backward); bare ⇒ edge ∨ (`stars` ∖ `neg`) (reach ⇒ the shadow-collapsed single edge ⇒ master's
  canonical guard ⇒ `sem`; fallback sound by `neg` completeness — `sem`-false would be IN `neg`;
  backward: covered reads from the row, uncovered gets its edge); userset ⇒ `upos` exactly
  (`hWSbare` kills userset coverage: the `stars` gate is always false); untainted ⇒ shadow +
  `graphRec_reduce_base_adm_bs` + `graphRec_base_eq_bs`.
- T3/T6 at W3c scope (`Equiv.lean`): `backend_equivalence_w3c`, `exclusion_effective_w3c` (**a
  concrete subject excluded from UNDER a `T:*` wildcard grant — the space rule's `neg` actually
  excludes**, the headline W3c security content), `no_ghost_grant_w3c`. `Audit.lean`: 10 new
  entries, all `[propext, Classical.choice, Quot.sound]`.

**Proof-engineering notes:** `subst` eliminates the RHS variable — orient equations so the
JOB/∃-bound var is on the right (`have h1' : dt = jdt := h1.symm; subst h1'`). After
`obtain ⟨⟨st,sn,sp⟩, R, ⟨dt,on⟩⟩ := q`, RE-TYPE the query hypotheses (`replace hqs : sn = STAR →
sp = BARE := hqs`) — otherwise they carry unreduced `{…}.object.name` projections that break
later `rw`s. Pass `(s := …)` explicitly when a lemma's implicit subject is only determined
through `s.shape` (unification can't invert `.shape`). `cases hrow : σ.residue …` substitutes
the scrutinee in the goal — don't `rw [hrow]` afterwards.

**Resume → W3d (multi-stratum cascade; see HANDOFF "The next task").**

## Session 2026-07-11c (W3c read half step 2 — the batch layer `ReconcileStarsComplete.lean` + attack-first: the no-ghost-star linchpin identified)

Resuming from HANDOFF "W3c read half steps 2–3." One green+pushed axiom-clean increment (new
file `GraphIndex/ReconcileStarsComplete.lean`); `verify.sh` green (build + 0 sorries + zcli +
standard-axioms audit + 60 conformance). Sorry count held at 0. **This lands HANDOFF W3c read-half
step 2, part 1** (the batch scaffolding + the shadow `checkFn` bridge); the assembly
`graph_correct_w3c` is set up but NOT yet landed — see the precise plan + the linchpin below.

**Increment — the W3c batch layer (`ReconcileStarsComplete.lean`).**
- `checkFn_eq_sem_w3c`: the star-relaxed `checkFn = sem` on ANY W3c state, through the W3a-admitted
  shadow (`reachedByW3c_shadow` + `checkFn_congr` + `checkFn_eq_sem_bs`). Subject-generic up to
  star-BARE — the exact form the `coveredFn`/`stars ↔ sem` correspondence consumes. (The W3b
  analog is `checkFn_eq_sem_w3b`.)
- `reconcileStarsKey_edges_mono` (residue half edge-inert + `reconcileKeyC_edges_mono` through the
  collapse); `W3cJob` (dt/on/R/e/cands/negCands/uposCands — shapes fixed to `wildcardShapes S`),
  `W3cJob.apply` (parametrised by `S` for the fixed shapes), `reconcileJobsC`, `W3cJobValid` (=
  a `ReachedByW3c.reconcileS` leg's side conditions), `reconcileJobsC_pres`,
  `reconcileJobsC_edges_mono`. Mirror of the W3b `W3bJob`/`reconcileJobsB` layer, adapted to the
  COMBINED `reconcileStarsKey` pass (one job settles stars+neg+upos+edges for a key at once — W3b
  split edge and upos into separate job constructors).

**Attack-first — THE LINCHPIN (recorded here; scratch/analysis only, no refutation).** Before
designing the `probeDerived` assembly I traced the three branches (bare ⇒ edge ∨ (stars∖neg),
star ⇒ stars, userset ⇒ upos ∨ (stars∖neg)) against `sem`. **Finding: every branch's
space-rule correspondence needs a "no ghost star coverage" lemma — `coveredFn σ0 sh = true → sh
∈ wildcardShapes S`** (equivalently, a `sem`-true BARE-star subject has a DECLARED wildcard
shape). Reason: `res.stars = (wildcardShapes S).filter (coveredFn σ0)` (master), so
`res.stars.contains sh ↔ (sh ∈ wildcardShapes S ∧ coveredFn σ0 sh)`, while the space rule needs it
`↔ coveredFn σ0 sh` alone (= `sem` at the star subject, via `checkFn_eq_sem_bs`). The two agree
iff coverage implies declaredness. **This lemma is TRUE** — confirmed against the `sem` defs
(`Spec/Semantics.lean`): `restrictionMatches` gates a star grant by the wildcard flag
(`((tup.subject.name == STAR) == r.2.2)`, `:38`), so a stored star grant matches only a
`(type,pred,true)` restriction ⇒ its shape is in `wildcardShapes` (the `exprRestrictions`
wildcard collector); the `directLeaf` star-exact branch (`:66-67`) reads exactly such a grant, and
for a **bare** star the `ttuLeaf` exact-match branch is dead (`s.predicate = BARE ≠ targetRel`,
`:96/99`) so no ttu ghost — the recursion (flow-through / `instances`) preserves the star subject
and bottoms out at that gated directLeaf. The existing userset analog is
`isSWU_of_storeValid` (`UsStarClosure.lean:236`).

**Two proof routes for the linchpin (next session picks one):**
- **Route 2 (graph-level, likely cleaner):** `coveredFn σ0 sh = σ0.checkFn (starSubj sh) …` reads
  `graphRec σ0` at untainted leaves = `reach` from `wAnyNode sh` on σ0. A non-reflexive reach ⇒
  ∃ edge `(wAnyNode sh, y) ∈ σ0.edges` ⇒ (`reachedByRules_edge_sound`) a closure tuple with
  `subjNode = wAnyNode sh` ⇒ (`rewriteClosure_star_subject`/`BareStarStore`/`TtuStarFree`, cf.
  `RulesBareStar.lean`) a STORED bare-star seed of shape sh ⇒ (`StoreValidRules` +
  `restrictionMatches` wildcard flag, cf. `isSWU_of_storeValid`) `sh ∈ wildcardShapes S`.
  `wAnyNode_eq_subjNode` (`RulesBareStar.lean:758`) and `subjNode`-of-star = `wAnyNode` are the
  node glue.
- **Route 1 (sem-level):** turn `coveredFn σ0 sh` into `sem S T ⟨starSubj sh, R, o⟩` via
  `checkFn_eq_sem_bs`, then a `semAux` fuel induction "bare-star true ⇒ declared shape" over
  union/inter/excl/computed/direct/ttu.

**The remaining assembly plan (`graph_correct_w3c`), with the linchpin in hand.** Add fragment
hyps: `hWSbare : ∀ sh ∈ wildcardShapes S, sh.2 = BARE` (decision-15 defers userset-star coverage;
makes `starSubj sh` bare so `checkFn_eq_sem_bs` applies to `coveredFn`), `hqbareStar :
q.subject.name = STAR → q.subject.predicate = BARE` (bare-star queries only). Define `W3cComplete`
(base + jobs + `W3cJobValid` + coverage: edge cands ⊇ sem-true uncovered bares, negCands ⊇
neg-leaf concretes ∪ derived-neg ids, uposCands ⊇ sem-true uncovered usersets, AND a **row-
existence** clause: every derived (dt,R)/on with a covered shape or any sem-true member has a job
⇒ the row exists & is canonical by `reachedByW3c_master`). Soundness of all three branches is
NEARLY FREE from `reachedByW3c_master` (rows canonical; edges canonically uncovered+guard-true) +
`checkFn_eq_sem_w3c`/`_bs`; completeness needs the covering job (edge-present via
`reconcileKey_edge_present` through the collapse — note the covered filter drops covered cands, so
a sem-true UNCOVERED bare survives the filter — plus `reconcileJobsC_edges_mono`; upos/stars via
row existence). Star branch: `res.stars.contains s.shape ↔ coveredFn σ0 s.shape` (linchpin) `↔
sem` (bridge, `s = starSubj s.shape` since bare-star). Then T3/T6 `*_w3c` in `Equiv.lean`, and
Audit.lean entries for `graph_correct_w3c` + `checkFn_eq_sem_w3c`.



Resuming from HANDOFF "W3c read half: the star-relaxed base equation." Two green+pushed
axiom-clean increments (new file `GraphIndex/RulesBareStar.lean` ~700 lines; +
`RestrictBase.lean`, `ReconcileComplete.lean`, `Audit.lean` [12 new entries], root aggregator);
`verify.sh` green throughout (build + 0 sorries + zcli + standard-axioms audit + 60
conformance). Sorry count held at 0. **This closes HANDOFF step 1 of the W3c read half**: the
base `hag` equation and the `checkFn ↔ sem` bridge now hold WITHOUT `StarFreeStore`, over
`BareStarStore` + `TtuStarFree`, subject-generically up to star-BARE subjects — exactly the
form the `coveredFn`/`stars ↔ sem` correspondence consumes.

**Attack-first (recorded in `RulesBareStar.lean` header, scratch deleted).** Planned
`graph_correct_rulesBS` vs `sem` on a ~180-query grid over a mixed `computed`/`ttu`/`union`
schema: `user:*` feeding computed arms, D1 star flow-through (`user:* → group:g#mem`), a star
grant on a TTU *target* relation, a D1 chain crossing a rewrite output fed by a star grant,
star-bare + userset subjects, ghosts — zero mismatches; `semAux_star_to_bare` zero violations.
**Necessity of `TtuStarFree` CONFIRMED** (a genuine refutation of the unconditioned statement):
`folder:* → doc:d6#parent` makes `sem` true via `ttuLeaf`'s `instances` branch while the graph
answers false — the rule-routed write model (`writeRules`, a plain `writeDirect` fold)
materialises NO in-bridges; star TTU parents are W1c machinery, deferred. `TtuStarFree S T`
(no TTU arm matches a stored star tuple) is the honest fragment condition.

**Increment 1 — `graph_correct_rulesBS` (`RulesBareStar.lean`).** W2's untainted `check = sem`
over `BareStarStore`, query scope = concrete object + (concrete ∨ star-BARE) subject:
- closure star-characterisation `rewriteClosure_star_subject`/`_star_bare`: no ttu arm ever
  fires on a star-subject closure member (seed case: `TtuStarFree`; output case:
  `no_rewrite_outputs_tupleset`), and computed arms keep the subject — so star closure members
  carry the seed's full bare subject;
- subject-generic soundness: `semAux_seed_bs` (star seeds self-grant via the star branch's
  exact-shape disjunct, `directLeaf_grant_starSelf`), `semAux_of_rewriteClosure_bs`,
  `semAux_lift_untainted_bs` (lift with arm-provenance threading so `ttuLeaf_elim_nss` can
  instantiate `TtuStarFree` per leaf), chain composition `semAux_of_ruleChain_bs` via GLOBAL
  `subjNode` injectivity (`subjNode_inj_total` — star and plain nodes never collide);
- the star→concrete coverage transfer `semAux_star_to_bare` (fuel-for-fuel; `RecLe` +
  `memberOfGranted_mono` reused from FuelStable; probe-2 glue: a `wAny`-source chain IS the
  star-subject chain at `subjNode ⟨T, *, BARE⟩`);
- completeness `nreaches_of_semAux_rulesBS`: probe-1 ∨ probe-2 disjunction (star subject ⇒
  probe 1 at its own `wAny` node; bare ⇒ probe 1 ∨ probe 2; userset ⇒ probe 1; flow-through
  and `nreaches_relation_rewrite_bs` tail both disjuncts);
- assembly: probes 3–4 dead (plain targets), probe-2-dead-for-usersets via
  `rulesAdmitted_edge_endpoints_bs` (sources plain or `wAny`-BARE).

**Increment 2 — the base equation + bridge.** `ttuStarFree_restrict` + `graphRec_base_eq_bs`
(`RestrictBase.lean`): the schema-restriction route verbatim with `graph_correct_rulesBS` as
the untainted black box (`TtuStarFree` transfers to `S↾U` since `schemaRewrites` is
preserved). `graphRec_reduce_base_adm_bs` (`ReconcileComplete.lean`): NO `StarFreeStore` — the
plain-edges shortcut (which killed probes 2–4) is replaced by transferring ALL FOUR probes to
the base: both probe targets (`objNode ⟨dt,on⟩ r'`, `wAllNode dt r'`) carry the untainted key
`(dt, r')`, so `reachedByW3aAdmitted_reach_inert` (never star-dependent) applies per probe.
`checkFn_eq_sem_of_base_bs` + `checkFn_eq_sem_bs`: the composed star-relaxed bridge on
W3a-admitted states, subject-generic up to star-BARE.

**Resume → W3c read half steps 2–3 (see HANDOFF "The next task"):** the `W3cComplete`
batch/coverage layer (jobs = `reconcileStarsKey` passes; an ADMITTED variant of the W3c
closure is likely needed so `checkFn_eq_sem_bs` applies to the canonical base), then the
`graph_correct_w3c` assembly through `probeDerived` (bare ⇒ edge ∨ stars∖neg, star ⇒ stars =
canonical `coveredFn` = `sem` via the new bridge, userset ⇒ upos ∨ stars∖neg) + T3/T6 `*_w3c`.
Fragment hypotheses on the store are now `BareStarStore` + `TtuStarFree` (replacing
`StarFreeStore`).

## Session 2026-07-11 (W3c write half — CLOSED: stars/neg model, covered-filter collapse, T2a with all-contentful I6, guard canonicity)

Resuming from HANDOFF "W3c (star data on derived keys → `stars`/`neg`)." Two green+pushed
axiom-clean increments (new file `GraphIndex/ReconcileStars.lean`; + `Audit.lean` [5 new
entries], root aggregator); `verify.sh` green throughout (build + 0 sorries + zcli + audit
standard-axioms-only + 60 conformance). Sorry count held at 0. **This closes the W3c WRITE
half** (model + T2a + graph-internal correspondence); the READ half (`graph_correct_w3c`)
is blocked on the star-relaxed base equation — see "Resume" below.

**Attack-first (no refutation; recorded in `ReconcileStars.lean` header, scratch deleted).**
Planned model vs `sem` on a 342-query grid: `viewer := member ∖ banned`, `viewer2 := member
∩ editor`, `viewer3 := (member ∩ editor) ∖ banned` over 6 objects with `user:*` grants on
operands — starred subtrahend kills coverage; `and` of starred+unstarred uncovered, of two
starred covered; concrete-only exclusion does NOT defeat `*` (star query true while bob ∈
neg); covered subjects hold ZERO edges; userset-driven `neg` under a star base; star
coverage via **D1 flow-through** (`member@group:h#mem` + `group:h#mem@user:*` — no direct
star grant); nested boolean root. Idempotent; reversed key order + permuted/DUPLICATED
candidate lists agree. Load-bearing modeling discovery: **the compiled star fold
`plan.stars_fn` is pointwise the boolean evaluation on the star subject** (`∪/∩/−` over
leaf star sets = `∨/∧/∧¬` over leaf star membership; a closure leaf's star set is the
graph's star-subject read) — so the model's `stars` is just `shapes.filter (checkFn on
starSubj)`, and ALL `checkFn` machinery applies to coverage.

**Increment 1 — write model + T2a (`ReconcileStars.lean`).** `wildcardShapes` (the
schema-fixed `subject_wildcard_shapes`), `coveredFn` (star-subject `checkFn`),
`reconcileResidueKey` (wholesale stars/neg/upos recompute, one `putResidue`, faithful to
`reconcile` steps 1–3 `processor.py:388-446`), `reconcileKeyC` (covered-guarded edge fold,
`want_edge = should ∧ ¬covered` `:359`), `reconcileStarsKey` (residue-THEN-edges — the
faithful atomic unit; the order is load-bearing). Three structural devices:
1. **Covered-filter collapse** `reconcileKeyC_eq_filter`: the covered guard reads the
   persisted row, which `writeDirect` never touches ⇒ fold-constant ⇒ the W3c edge fold
   IS a W3a `reconcileKey` over the covered-filtered candidates. All W3a fold lemmas
   (edge soundness/guard, monotonicity, reach-inertness, CoreEq) transfer for free.
2. **Shadow projection** `reachedByW3c_shadow` (W3b pattern): residue writes core-inert +
   the collapse ⇒ every W3c state has a W3a-admitted shadow with identical core.
3. **Star-general operand-read inertness** `graphRec_reconcileKey_inert` — NO
   `StarFreeStore`: a reconcile pass adds only edges onto its terminal R-node; ALL FOUR
   `probeNonDerived` probe targets at untainted keys (`objNode ⟨dt',on'⟩ r'`, `wAllNode`)
   differ from it ⇒ the read is pass-invariant, subject-generically (star subjects incl.).
`reachedByW3c_master`: one canonical base `σ0` per chain — operand reads = base reads;
every residue row sits at a derived R-node key with `stars` = the CANONICAL star set
(`wildcardShapes.filter (coveredFn σ0)`); every R-node in-edge is base (killed by
`RootBoolean` no-inedge) or from a canonically-uncovered bare candidate. **T2a
`reachedByW3c_inv`: full `Inv` with ALL FOUR I6 clauses contentful for the first time** —
`negStarCovered` (write-time filter), `uposNegDisjoint` (covered vs ¬covered, same row),
`uposEdgeFree` (userset member vs bare-sourced collapsed edge), `negEdgeFree` (the space
rule cross-pass: a `neg` member is canonically covered, every edge source canonically
uncovered — contradiction). No `StarFreeStore` hypothesis anywhere in the file.

**Increment 2 — guard canonicity.** `reachedByW3c_master` extended: `neg` members are
canonically expr-FALSE, `upos` members canonically expr-TRUE (write-time filters +
`checkFn_agree_of_graphRec`), and every reconcile edge source canonically expr-TRUE
(`reconcileKey_edge_guard` gives the guard at a prefix mid-fold state; the prefix fold is
operand-inert — the mid-state is core-shadowed by a W3a-admitted state built from the
pass prefix — so the mid-state guard = the base guard). The W3c state content is now
FULLY characterized by the base's compiled boolean (`coveredFn σ0`/`checkFn σ0`).

**Resume → W3c read half (the star-relaxed base equation).** What remains for
`graph_correct_w3c`: (1) **`checkFn σ0 = sem` / `graphRec_base_eq` WITHOUT
`StarFreeStore`** — the W2 untainted correspondence re-proved on stores carrying bare
`user:*` grants (wildcard probes 1–2 go live on the base; W1's `graph_correct_bareStar`
has the pure-direct star machinery — compose with W2 rule routing; also needed for STAR
subjects, which `stars ↔ sem` requires — `graphRec_reduce_base_adm`'s star-free
plain-edges shortcut must be replaced by per-probe reasoning, for which the new
star-general inertness is the template); (2) the `W3cComplete` batch/coverage layer
(W3b-style jobs + persistence — residue rows are wholesale-recomputed, so persistence =
canonical-content stability + coverage clauses on the enumeration); (3) assembly through
the (already general) `probeDerived` read. Scope note: userset-star shapes/object
wildcards stay out (decision-15 rejects them on derived relations); `wildcardShapes` only
carries declared bare-subject-star shapes on this fragment.

## Session 2026-07-11 (W3b — CLOSED in one session: `graph_correct_w3b`, userset `upos`, T3/T6 at W3b scope)

Resuming from HANDOFF "W3b (userset subjects → `upos` residue)." Three green+pushed axiom-clean
increments (new files `GraphIndex/ReconcileUpos.lean`, `GraphIndex/ReconcileUposComplete.lean`;
+ `Equiv.lean`, `Audit.lean` [16 new entries], root aggregator); `verify.sh` green throughout
(build + 0 sorries + zcli + audit standard-axioms-only + 60 conformance). Sorry count held at 0.
**This CLOSES W3b** — the W3a bare-subject scope restriction is LIFTED: `graph_correct_w3b` proves
`check = sem` on EVERY star-free query (bare and userset subjects) over a `W3bComplete` state.

**Attack-first (no refutation; recorded in `ReconcileUpos.lean` header, scratch deleted).** On
`viewer := member but not banned` (member = direct ∪ computed editor) with userset grants
(`group:{g,h,i}#mem` member/banned/editor-only, ghosts, the derived key itself as subject): the
planned model's `check` = `sem` on a 180-query grid; bare/userset pass ORDER irrelevant; repeated
pass idempotent; P4 non-leak (a banned member of an upos-true userset stays denied); upos members
do NOT reach the R-node even though userset nodes carry operand out-edges (I6 confirmed). The
load-bearing structural discovery: **the upos fold never touches edges/nodes, so `checkFn` is
CONSTANT across the fold** — no prefix-mid-state bookkeeping (unlike the W3a edge fold, whose guard
sees earlier writes; there it was terminality that saved it, here it is congruence).

**Increment 1 — write model + read collapse (`ReconcileUpos.lean`).** `reconcileUposStep/Key`
(per-candidate insert/remove on the key's `upos` via `putResidue`; faithful to `reconcile_subject`
`processor.py:345-357`, star-free ⇒ `covered=false` ⇒ `want_upos=should`, `want_neg=false`; the
model stores a possibly-empty row where Python deletes it — read-equivalent via `getD`). Congruence
spine `reach_congr → probeNonDerived_congr → graphRec_congr → checkFn_congr` (agreement on
edges+nodes). Whole-fold membership characterization `reconcileUposKey_upos_mem`. `ResidueUposOnly`
+ preservation (writeDirect/reconcileKey/reconcileUposKey). W3b read collapse `probeDerived_uposOnly`
/ `check_derived_uposOnly` (star ⇒ false, userset ⇒ `upos.contains`, bare ⇒ W3a edge probe).

**Increment 2 — closure + shadow + soundness (`ReconcileUposComplete.lean`).** `CoreEq`
(residue-blind state agreement) with congruences (`writeDirect_coreEq`, `reconcileKey_coreEq`).
`ReachedByW3b` (admitted base + interleaved bare-edge/upos legs; `reconcileU` side conditions
faithful to the userset branch). **The shadow projection `reachedByW3b_shadow`** — every W3b state
has a W3a-admitted shadow with identical core (replay minus upos passes) — the session's key
economy: ALL W3a edge/reach facts (reach collapse, R-node terminality, derived-edge soundness,
`checkFn_eq_sem`) transfer with ZERO new induction. Residue provenance (rows only at derived
R-node keys; members concrete usersets). **T2a `reachedByW3b_inv`**: full `Inv` with contentful I6
— `uposEdgeFree` proved for real (userset-shaped member vs single bare-sourced edge onto the
`RootBoolean` R-node), `neg` clauses by emptiness; quiescence. `checkFn_eq_sem_w3b`
(subject-generic). **`upos` soundness** `reachedByW3b_upos_sound` (entry ⇒ `sem`; the guard at the
W3b pass-start state, no prefix machinery needed by fold-constancy).

**Increment 3 — completeness + assembly + Step C.** `W3bJob` (edge|upos) / `reconcileJobsB` /
validity / preservation / edge-monotonicity (upos jobs edge-inert). **`upos` persistence**
`reconcileJobsB_upos_persist` — a `sem`-true entry survives every later valid job (edge jobs never
touch residues; a same-key upos re-reconcile re-evaluates its fold-constant guard = `sem` = true ⇒
re-adds, never removes). `W3bComplete` (admitted base + coverage-complete batch: edge jobs
enumerate every `sem`-true BARE subject, upos jobs every `sem`-true USERSET — faithful to the
audit enumeration `processor.py:413-441`). `w3bComplete_derived_edge` (the W3a argument through
the covering edge job, shadow-transferred terminality) + `w3bComplete_derived_upos` (covering job
writes; persistence carries). **`graph_correct_w3b`** — untainted via shadow + base reduction,
derived-bare via edge probe, derived-userset via `upos`. **Step C**: `backend_equivalence_w3b` /
`exclusion_effective_w3b` / `no_ghost_grant_w3b` — T6a now covers a userset excluded by a derived
`but not` (P4 non-leak, both directions).

**Resume → W3c (star data → `stars`/`neg`).** See HANDOFF "The next task": attack-first the
star×boolean fold (`plan.stars_fn`) + `neg` recompute vs `sem`; the expensive half is relaxing
`StarFreeStore` (consider sub-staging W3c-i stars-on-derived-key-only vs W3c-ii star grants in
operand cones). The shadow-projection pattern survives (stars/neg writes are `putResidue`-only).

## Session 2026-07-11 (W3a Step B + C — CLOSED: `graph_correct_w3a`, T3/T6 at W3a scope)

Resuming W3a Step B from HANDOFF "candidate completeness + assembly." Three green+pushed
axiom-clean increments (new file `GraphIndex/ReconcileComplete.lean` + `Equiv.lean` + `Audit.lean`);
`verify.sh` green throughout (build + 0 sorries + zcli + audit standard-axioms-only + 60
conformance). Sorry count held at 0. **This CLOSES W3a** — the derived-boolean read correspondence
is proved end-to-end and the T3/T6 corollaries lifted.

**Attack-first (recorded a scope finding).** `#eval` on `viewer := member but not banned` with a
userset grant `doc:1#member@group:g#mem`: `sem ⟨group:g#mem, viewer, doc:1⟩ = true` (member ∧ ¬banned)
while the graph's residue-empty `probeDerived` reads a userset subject as `false`. So W3a's
derived-query correctness is **bare-subject only** — userset subjects on a derived key are exactly
W3b's `upos` residue. `graph_correct_w3a` is scoped to `q.subject.predicate = BARE`; the untainted
half stays subject-general (base reduction). Scratch deleted.

**Increment 1 — the `checkFn ↔ sem` bridge.** `semAux_qirrel` (`sem` never reads the query except
through `instances`, which discards it — so the operand `sem` at query `⟨s,r',o⟩` feeds
`checkFn_eq_semStep`'s enclosing query `⟨s,R,o⟩`). `ReachedByW3aAdmitted` (admitted base leg;
`hlke` def-lookup added to the reconcile constructor) + `reachedByW3aAdmitted_toW3a` (forgets to the
plain W3a closure, so all soundness lemmas transfer) + `graphRec_reduce_base_adm` (the admitted
analog of `graphRec_reduce_base`: the operand read reduces to an *admitted* base). **`checkFn_eq_sem`**
— on a W3a-admitted state, `checkFn` at a `ComputedOnly` derived key (untainted leaves) equals
`sem S T ⟨s,R,⟨dt,on⟩⟩` — composing `graphRec_reduce_base_adm` + Step A's `graphRec_base_eq` +
`semAux_qirrel` + T0a fuel stability.

**Increment 2 — derived-edge soundness (forward).** `reconcileKey_edge_guard` (every reconcile-fold
edge is pre-existing or materialised at a *prefix mid-state* whose `checkFn` guard held);
`reachedByRules_RootBoolean_no_inedge` (a `RootBoolean` R-node has no base in-edge, so the base leg
is vacuous). **`reachedByW3aAdmitted_derived_edge_sound`** — a materialised derived edge witnesses
`sem = true` (base leg vacuous; reconcile guard at a W3a-admitted mid-state ⟶ `checkFn_eq_sem`).

**Increment 3 — candidate completeness (backward) + assembly + Step C.** `reconcileKey_edge_present`
(a `sem`-true bare candidate's edge is materialised: guard fires at every prefix mid-state via
`checkFn_eq_sem`; the write admits because the `RootBoolean` R-node is terminal ⇒ no back-path;
persists to the pass end). `W3aJob`/`reconcileJobs`/`W3aComplete` — an admitted base + a
**coverage-complete** batch of reconcile jobs (faithful to `reconcile`/`_leaf_concretes`,
`processor.py:382-423,497-507`: the coverage clause is a property of the *enumeration*, not the edge
conclusion). **`w3aComplete_derived_edge`** (`sem`-true ⇒ edge present: the covering job writes it,
`reconcileJobs_edges_mono` persists it). **`graph_correct_w3a`** — `check = sem` on every
bare-subject star-free query: untainted via the base reduction (`graphRec_reduce_base_adm` +
`graphRec_base_eq`), derived via the residue-empty edge probe (`check_derived_ResidueEmpty`) glued by
soundness (reach ⟶ `reachedByW3a_reach_collapse_root` ⟶ edge ⟶ `sem`) and completeness (`sem` ⟶ edge
⟶ reach). `isDerived_declared` supplies the def. **Step C:** `backend_equivalence_w3a` /
`exclusion_effective_w3a` / `no_ghost_grant_w3a` in `Equiv.lean` (T1 ∘ `graph_correct_w3a`); T6a's
first real exclusion content.

**Resume → W3b (userset subjects → `upos` residue).** See HANDOFF "The next task": attack-first the
`upos` read/write path FIRST, then relax the residue-empty closure to a `upos`-carrying residue and
widen the coverage/completeness to `upos` membership. `checkFn_eq_sem` is already subject-generic.

## Session 2026-07-11 (W3a Step A — CLOSED: state transfer + base `hag` equation)

Resuming W3a Step A from HANDOFF "the remaining Step A: state transfer + base `hag` equation."
Two green+pushed axiom-clean increments (both in `GraphIndex/RestrictBase.lean` + `Audit.lean`);
`verify.sh` green throughout (build + 0 sorries + zcli + audit standard-axioms-only + 60
conformance). Sorry count held at 0. **This CLOSES Step A** — the mixed-schema `hag` base
correspondence is now a single reusable theorem.

**Increment 1 — the state transfer (`exists_admitted_restrict`, `foldAdmits_of_acyclic`).** The
roadmap's flagged "open subtlety": σ0 (admitted over mixed `S`) and its restricted counterpart σ'
(over `S↾U`) fold `writeDirect` over DIFFERENT lists (`rewriteClosure S t` vs `rewriteClosure
(S↾U) t`, differing by fuel/dups), and admission (`FoldAdmits`, cycle-rejection) is order-sensitive
— so the states are not literally equal. **The bridge:** admission depends only on the *final* edge
relation being acyclic. `foldAdmits_of_acyclic` — a `writeDirect` fold admits every write provided
each materialised edge lands in an acyclic target `Ef` already containing the running edges (a
self-loop is a 1-cycle in `Ef`; a back-path `b →* a` plus the new `a → b` is a cycle in `Ef`; the
write keeps the running edges inside `Ef` via `writeDirect_edges`). It is order-insensitive — the
only input from the list is its *set* of materialised edges. `exists_admitted_restrict` then builds
the canonical `ReachedByRulesAdmitted σ' (S↾U) T` by induction on the write path: at each step the
target `Ef := σ0.edges` is acyclic (`Inv.acyclic`), σ'-prev sits inside it (edge-IH + writeRules
monotonicity), and every restricted-closure write materialises there (fuel bridge `⊆` +
`reachedByRulesAdmitted_edge_complete`). Edge agreement of the finished σ' vs σ0 is then immediate
from the two edge characterizations (`reachedByRules_edge_sound` / `…Admitted_edge_complete`) + the
fuel bridge — no reference to intermediate states.

**Increment 2 — the base `hag` equation (`graphRec_base_eq`).** On an admitted rule-routed `σ0`
over mixed `S` and untainted operand `r'`: `graphRec σ0 s dt on r' = sem S T ⟨s,r',⟨dt,on⟩⟩`. Chain:
`graphRec σ0 = probeNonDerived σ0` (def) `= probeNonDerived σ'` (edge agreement ⇒ per-node `reach`
agreement, `probeNonDerived` being a disjunction of `reach` probes) `= check σ'`
(`check_eq_probeNonDerived`, `S↾U` untainted) `= sem (S↾U) T q'` (`graph_correct_rules` over `S↾U`
as a black box) `= sem S T q'` (`semAux_restrict` at `fuelBound S T`, then `sem_fuel_stable` over
the untainted `S↾U` to bridge `fuelBound (S↾U) T ≤ fuelBound S T`). The W2 restriction hypotheses
transfer: WF/TtuTuplesetsDirect by `defs`-subset, RewriteRanked by `rewriteRanked_restrict`,
StoreValidRules by `restrictUntainted_lookup` given stored relations untainted — which the fragment
premise **`hRootB`** (every derived def `RootBoolean`, superseding the old `hDrop`) forces: a
derived def would be `RootBoolean` ⇒ `exprDirects = []` ⇒ no `Direct` arm for `StoreValidRules` to
match. **Wiring note:** RestrictBase now imports `ReconcileCorrect` (for `graphRec`/`RootBoolean`/
`exprArms_rootBoolean`); no cycle (only `Audit.lean` imports RestrictBase).

**Attack-first.** Both increments are THEOREM consequences of already-attack-verified facts (the
fuel bridge, `semAux_restrict`, `graph_correct_rules`), so low refutation risk; the genuinely new
content (acyclic-admission, the reach/probe congruence) is combinatorial. No refutation.

**Resume → Step B (candidate completeness + assembly `graph_correct_w3a`).** See HANDOFF "The next
task." Feed `graphRec_base_eq` (needs an *admitted* W3a base) through `graphRec_reduce_base` — whose
`hag` half currently yields a `ReachedByRules` (not admitted) base, so either re-cut it to hand back
`ReachedByRulesAdmitted`, or prove the reduction preserves admission. Then edge-provenance
(`reconcileKey` peel), the admitted W3a closure `ReachedByW3aAdmitted`, and the derived/untainted
query assembly.

## Session 2026-07-11 (W3a Step A — the fuel bridge, closed both directions)

Resuming W3a Step A from HANDOFF "the fuel bridge is the one remaining subtlety." Three
green+pushed increments (all in `GraphIndex/RestrictBase.lean` + `Audit.lean`); `verify.sh`
green throughout (build + 0 sorries + zcli + audit standard-axioms-only + 60 conformance).
Sorry count held at 0. **This closes the fuel bridge — the crux the roadmap named** — so the
two canonical rewrite closures now have provably identical membership.

**The result — `rewriteClosure_restrict_mem_iff`.** `rewriteClosure S t` (fuel `|S.keys|+1`)
and `rewriteClosure (S↾U) t` (smaller fuel `|S↾U.keys|+1`) have identical membership on the W3a
fragment. Both are the SAME `S`-closure recurrence at two fuels (via `rewriteClosureAux_restrict`
from the prior session); the bridge is that the extra fuel adds nothing.

**Increment 1 — the `⊇` half (unconditional).** `rewriteClosureAux_mono` (more fuel never drops
a member — a member sits at some `stepN` layer `k ≤ n`, re-embedded at any `m ≥ k`, via the
existing `RulesSaturate` layer algebra `stepN_of_mem_aux` / `mem_aux_of_stepN`);
`restrictUntainted_keys_length_le` (`|S↾U.keys| ≤ |S.keys|`, filtered defs are a sublist, `map`
preserves length); `rewriteClosure_restrict_subset` composes them — the smaller closure embeds in
the bigger.

**Increment 2 — the `⊆` half (via saturation + rank compression).** The bigger closure adds no
new members past the smaller fuel because the `S↾U`-closure is SATURATED (closed under one more
`rewriteStep S`), so it swallows every `S`-closure layer (`rewriteClosure_subset_restrict`, layer
induction: seed at layer 0, each further step swallowed). Saturation needs
`RewriteRanked (S↾U)`, built from `RewriteRanked S` by **rank compression**
(`rewriteRanked_restrict`): reuse `S`'s rank `rrank`, compress to `restrictRank k :=`
`|{j ∈ S↾U.keys : rrank j < rrank k}|` — now bounded by `|S↾U.keys|` (`length_filter_le`) and
still strictly increased at each arm (`length_filter_lt_of_mem`, the strict filtered-length
monotonicity: the match key `a` is counted by the out-key threshold but not its own). The one
faithful side condition **`RewriteMatchDeclared S`** (every rewrite's match key
`(objectType, matchRel)` is a declared untainted relation) makes `a ∈ S↾U.keys` so the strictness
fires; it mirrors the compiler routing arms over declared operand relations, and must be
discharged in the fragment assembly (a clearly-flagged hypothesis, NOT a postulate of the
conclusion).

**Housekeeping.** A stray `Scratch_chk.lean` (an `import Mathlib` lemma-signature probe) leaked
into increment 2's commit when its cleanup was killed by a build timeout; removed in a follow-up
commit (library builds the `ZanzibarProofs` target, so `verify.sh` was never affected).

**Attack-first.** The bridge is a THEOREM consequence of `schemaRewrites` equality (attack-first
verified last session) + saturation, so lower refutation risk; the genuinely new facts (fuel
monotonicity, the key-count bound, rank compression) are pure combinatorics. No refutation.

**Resume → the remaining Step A: state transfer + base `hag` equation.** The fuel bridge gives
closure-membership equality; edges of a `ReachedByRulesAdmitted` state are EXACTLY the
materialised closure tuples (`reachedByRules_edge_sound` ⊆ + `reachedByRulesAdmitted_edge_complete`
⊇), so equal closure membership will give equal edges. **The open subtlety:** build a canonical
`ReachedByRulesAdmitted σ' (S↾U) T` and show `σ'.edges ≈ σ0.edges` — the states fold `writeDirect`
over DIFFERENT lists (`rewriteClosure S t` vs `rewriteClosure (S↾U) t`, differing by fuel/dups),
so the states are not literally equal; the transfer must go through the edge-membership
characterization, and `FoldAdmits` must transfer across the differing fold lists (fewer/equal
edges ⇒ still no cycle rejection). Then the base `hag` equation: `graphRec σ0 = probeNonDerived σ0`
`= check σ'` (edges agree) `= sem (S↾U) T q'` (`graph_correct_rules`) `= sem S T q'`
(`semAux_restrict` + fuel). Then Step B (candidate completeness + assembly) and Step C (T3/T6).

## Session 2026-07-11 (W3a Step A — the `hag` base reduction: schema restriction + `semAux` transfer + rewrite-preservation)

Resuming W3a from HANDOFF "Step A — discharge `hag` on the base" via the recommended
schema-restriction route. Two green+pushed axiom-clean increments (new file
`GraphIndex/RestrictBase.lean` + `Audit.lean`); `verify.sh` green throughout (build + 0 sorries
+ zcli + audit standard-axioms-only + 60 conformance). Sorry count held at 0. This lands the
**semantic heart** of Step A (the ledger's "genuine remaining core") plus the schema-combinatorial
groundwork for the state transfer.

**Attack-first (machine-checked `#eval` on a mixed `admin but not suspended` schema, then
deleted).** Confirmed the three route claims computationally before proving: taint isolates
exactly the derived key (`taintedKeys Smix = [(doc,can)]`), `schemaRewrites Smix =
schemaRewrites (restrictU Smix)` (the derived key is `RootBoolean`, emits no arms), and `semAux`
agrees on every operand relation (admin/viewer/suspended) at fuel 20. No refutation — statements
survived, then proved.

**Increment 1 — schema restriction + `semAux` transfer (`RestrictBase.lean`).**
- `restrictUntainted S` (`S↾U`): drop every tainted-key def, keep object-wildcards. Membership /
  subset / `NodupKeys`-preservation (`List.filter_sublist`-map-sublist).
- `untaintedSchema_restrict` (under `NodupKeys`): `S↾U` is untainted — a kept def has an untainted
  key, so its expr is boolean-free (`untainted_closed` ⇒ `baseTaint = false`, and `NodupKeys` makes
  `baseTaint` read exactly this def's `containsBool`). `isDerived_restrict` collapses.
- `restrictUntainted_lookup` (under `NodupKeys`): the schemas agree at every untainted key (declared
  ⇒ its unique def is kept; undeclared ⇒ both `none`).
- **`semAux_restrict` (the heart):** at every untainted key `(t,r)` and every name `m`, `semAux S`
  and `semAux (S↾U)` coincide (any fuel). Fuel induction: at an untainted key the two schemas'
  defs coincide (`restrictUntainted_lookup`), then `evalE_congr` (Confine) closes the step because
  `evalE` consults `rec` only at that def's `exprRefs`, all untainted by heredity
  (`untainted_closed`), where the IH supplies agreement. **Reduces the mixed-schema `hag` to a
  whole-schema-`UntaintedSchema` W2 fact over `S↾U` — `graph_correct_rules` as a black box.**

**Increment 2 — rewrite fan-out preserved (`RestrictBase.lean`).** The graph write path reads the
schema only through `schemaRewrites` (`writeDirect`/`admitEdge`/`reach` schema-blind).
- `filter_flatMap_eq`: flat-map over a filtered list is unchanged when removed elements map to `[]`.
- `schemaRewrites_restrict` (given the fragment fact `hDrop`: every tainted def emits no arms —
  `RootBoolean` ⇒ `exprArms_rootBoolean`): `schemaRewrites (S↾U) = schemaRewrites S`.
- `rewriteStep_restrict`; `rewriteClosureAux_restrict`: the bounded closure is preserved at ANY
  fixed fuel (pure structural — reads the schema only via `rewriteStep`).

**Resume → finish Step A's state transfer + assembly (the fuel bridge is the one remaining
subtlety).**
1. **The fuel bridge (the crux).** The canonical closures run at DIFFERENT fuels: `rewriteClosure
   S t` at `|S.keys|+1`, `rewriteClosure (S↾U) t` at the smaller `|S↾U.keys|+1`. With
   `rewriteClosureAux_restrict`, `rewriteClosure (S↾U) t = rewriteClosureAux S (|S↾U.keys|+1) [t]`,
   so the goal is **membership equality of the two S-closures across the fuel gap**. Both saturate:
   `rewriteClosure_saturated` (RewriteRanked S) gives the `|S.keys|+1` side; the `|S↾U.keys|+1`
   side needs that a rewrite chain from a stored (⇒ untainted, `exprDirects_rootBoolean` +
   `StoreValidRules`) seed STAYS untainted (an arm's `outRel` is its def's relation; tainted defs
   emit no arms ⇒ no rule outputs a tainted relation) and so has depth ≤ `|S↾U.keys|`. Formalize
   as either `RewriteRanked (S↾U)` (a rank compressed to `S↾U`'s key count) or a direct
   "untainted-cone saturates at `|S↾U.keys|+1`" lemma.
2. **State transfer.** On the fully-*admitted* write path (`FoldAdmits` ⇒ no cycle rejection), a
   `ReachedByRulesAdmitted` state's edges are characterized EXACTLY by `reachedByRules_edge_sound`
   (⊆) + `reachedByRulesAdmitted_edge_complete` (⊇): `(a,b) ∈ σ.edges ↔ ∃ t∈T, ∃ u ∈ rewriteClosure
   S t, materialise`. With (1) giving `rewriteClosure S t ≈ rewriteClosure (S↾U) t` (membership),
   build the canonical `ReachedByRulesAdmitted σ' (S↾U) T` and show `σ'.edges ≈ σ.edges`
   (membership). `reach` depends only on edge membership (`reach_iff_nreaches` + `edgesClosed`).
3. **Base `hag` equation.** `graphRec σ0 s dt on r' = probeNonDerived σ0 ⟨s,r',⟨dt,on⟩⟩`
   (`probeNonDerived_plainEdges`, plain edges) `= check σ' q'` (edges agree, `S↾U` untainted routes
   to the probe) `= sem (S↾U) T q'` (`graph_correct_rules` over `S↾U`) `= sem S T q'`
   (`semAux_restrict` + untainted-schema fuel stability to bridge `fuelBound (S↾U)` vs `fuelBound
   S`). This is `hag` for the untainted operands; compose with `graphRec_reduce_base`. NB the
   W3a base is currently `ReachedByRules` (not `…Admitted`) — the completeness (backward) half
   needs an admitted W3a closure, which is **Step B**'s `ReachedByW3aAdmitted`; Step A can land the
   soundness half + the equation over an *admitted* base as the reusable fact.
4. Then Step B (candidate completeness + assembly `graph_correct_w3a`) and Step C (T3/T6 widening).

## Session 2026-07-11 (review/cleanup + handoff restructure + `hag` leaf-restriction fix)

A consolidation session (user-directed): review everything for truth/cleanliness, fix
weirdness, and restructure the docs so future sessions resume from a small, precise entry
point. `verify.sh` green throughout; sorry count held at 0; one substantive proof fix landed.

**The substantive fix — `checkFn_eq_semStep`'s `hag` was UNDISCHARGEABLE as stated.** It
demanded `∀ r', graphRec σ s dt on r' = semAux … r'` — agreement at EVERY relation string,
including the derived `R` itself and unrelated/derived keys — but `graphRec_reduce_base` (and
any per-relation W2 restatement) can only ever supply it for *untainted* operands. The
assembly would have hit a wall. Fixed by restricting `hag` to the def's `computed` leaves:
new `computedRefs : Expr → List String`; `evalE_computedOnly` and `checkFn_eq_semStep` now
take `hag : ∀ r' ∈ computedRefs e, …`. The assembly needs only the fragment fact "every
computed leaf of a derived def is untainted" to compose with `graphRec_reduce_base`.

**Cleanups.**
- **Deduplicated node-projection simp lemmas** — `subjNode_pred` was declared IDENTICALLY in
  `ObjStarClosure.lean` and `ReconcileCorrect.lean` (both imported by `Audit`); all four
  projections (`subjNode_type`/`_pred`, `objNode_type`/`_pred`) now live once in `State.lean`
  next to the node constructors; local copies deleted.
- **Renamed `probeNonDerived_starFree` → `probeNonDerived_plainEdges`** (it takes only the
  plain-edges hypothesis; the star-free name was stale after the strengthening).
- **Stale docs fixed:** `README.md` (claimed "No Lean written yet"), the plan doc's header
  (claimed "not yet started"), ROADMAP's tail ("T4 blocker: do this first" — T4 closed).

**Handoff restructure (the main deliverable).** New **`formal/HANDOFF.md`** — the single
compact entry point a fresh session reads first: state-of-the-world theorem inventory, house
rules (honesty norm / attack-first / green gate / rhythm), build commands + Lean gotchas, the
precise NEXT TASK (W3a steps A/B/C with the recommended schema-restriction route for `hag`),
and the after-W3a road (W3b/c/d, W4, Phase 6). All other docs re-pointed at it (this file's
header, ROADMAP header, README orientation, plan-doc header). This file remains the
append-only ledger; end-of-session duty is now: session entry here + refresh HANDOFF's
"next task".

## Session 2026-07-11 (W3a read correspondence — the operand-read reduction to the untainted base)

Resuming W3a from "the multi-pass inertness fold (`reachedByW3a_reach_inert`) done; resume →
point 2 step 2, discharge `hag` (the per-relation untainted-correctness lemma, the deeper
blocker)." One green+pushed axiom-clean increment (`GraphIndex/ReconcileCorrect.lean` +
`State.lean` + `ReconcileWrite.lean` constructor + `Audit.lean`); `verify.sh` green throughout
(build + 0 sorries + 60 conformance + audit, standard axioms only — one new theorem axiom-free).
Sorry count held at 0. This lands the **reachability core of the `hag` reduction**: the operand
read `graphRec σ s dt on r'` W2's per-relation correctness consults now reduces, on the full W3a
state, to the read on the untainted base — leaving `hag` a *pure base-state* W2 fact with no
residual W3a-specific reasoning.

**The increment.**
- **`NReaches.mono_subset` (`State.lean`, axiom-free)** — general subset monotonicity of
  reachability (`edges ⊆ edges' → NReaches edges → NReaches edges'`), the edge-set-inclusion
  generalisation of the single-edge `NReaches.mono`. The reverse direction of the inertness
  transfer.
- **`reachedByW3a_reach_inert` strengthened** to also expose `σ0.edges ⊆ σ.edges` (reconcile
  passes only add edges — `reconcileKey_edges_mono` folded). **`reachedByW3a_reach_inert_iff`** —
  the biconditional: reachability into any untainted-key node agrees between the full W3a state
  and the untainted base (forward = the inertness fold; backward = `NReaches.mono_subset` on the
  subset inclusion).
- **`ReachedByW3a.reconcile` gained two faithful star-free fields** — `hcStar` (each candidate
  subject `c.name ≠ STAR`) and `honStar` (the reconciled object name `on ≠ STAR`). Faithful to the
  W3a star-free fragment (reconcile candidates are the `_leaf_concretes`, run per concrete object).
  They keep every reconcile edge's endpoints *plain*. The 7 `reconcile` match sites gained the two
  placeholders.
- **`reachedByW3a_edges_plain`** — every W3a edge endpoint is a plain node (base = rewrite-closure
  tuple names inherit the star-free store; reconcile = star-free candidate/object via the new
  fields). **`probeNonDerived_starFree`** (since renamed `probeNonDerived_plainEdges`) — a plain-edge read collapses to probe 1 (wildcard probes
  2–4 dead); strengthened vs `graph_correct_rules`'s inline version to need **only** plain edges
  (the query-star-free hypotheses drop out).
- **`graphRec_reduce_base` (the payoff)** — for every untainted operand relation `r'`
  (`isDerived S (dt, r') = false`), `graphRec σ s dt on r' = graphRec σ0 s dt on r'` on the
  untainted base `σ0`. Both reads collapse to probe 1 (plain edges on both states); the target
  `objNode ⟨dt,on⟩ r'` is an untainted-key node, so `reachedByW3a_reach_inert_iff` equates the two
  reachabilities. **Reduces `hag` to the base per-relation fact `graphRec σ0 s dt on r' = sem`.**

**Resume → close the W3a CORRESPONDENCE. `hag` is now a pure W2 base-state fact:**
1. **Discharge `hag` on the base — the per-relation untainted-correctness lemma (the remaining
   blocker, now W3a-free).** With `graphRec_reduce_base`, `hag`'s untainted operands reduce to
   `graphRec σ0 s dt on r' = semAux S s T q f dt on r'` on a `ReachedByRules` base `σ0` — a *W2*
   statement. `graph_correct_rules` proves the whole-schema `UntaintedSchema` version; W3's mixed
   schema needs it **per hereditarily-untainted relation `r'`**. Restate `graph_correct_rules` (and
   its soundness `sem_of_rules_reach` / completeness `nreaches_of_semAux_rules` chain) with a
   *hereditarily-untainted* hypothesis on `r'` in place of whole-schema `UntaintedSchema` (the
   relation's `sem`/graph only consult the untainted cone). Fuel via the T0a-stability sidestep.
   **This is the genuine remaining core** — a per-relation restatement threading through the W2
   proof chain; no W3a-specific reasoning left.
2. **Candidate completeness + assembly `graph_correct_w3a`** (an admitted `ReachedByW3aAdmitted`:
   every `sem`-member bare subject is in some `cands` and passes `checkFn`) + assembly: route →
   `probeDerived` → `check_derived_ResidueEmpty` → edge probe → `reachedByW3a_reach_collapse_root`
   → `checkFn_eq_semStep` (with `hag` from step 1) → `sem`. Then widen T3/T6.

## Session 2026-07-11 (W3a read correspondence — multi-pass reconcile inertness folded to the untainted base)

Resuming W3a from "reconcile-edge inertness resolved per-pass (`reconcileKey_reach_inert`);
resume → point 2's step 1, the **multi-pass inertness fold** down to the `ReachedByRules`
base". One green+pushed axiom-clean increment (`GraphIndex/ReconcileCorrect.lean` +
`ReconcileWrite.lean` constructor + `Audit.lean`); `verify.sh` green throughout (build + 0
sorries + 60 conformance + audit, standard axioms only — the new theorem `[propext,
Quot.sound]`). Sorry count held at 0. This lands **step 1 of point 2** (the reachability half
of the `hag` reduction): reachability into an untainted-key node on the full W3a state agrees
with the untainted base, so the reconcile-materialised derived edges are provably inert for the
operand reads W2's per-relation correctness consults.

**The increment.**
- **Constructor strengthened (`ReconcileWrite.lean`): `ReachedByW3a.reconcile` now carries
  `hder : isDerived S (dt, R) = true`** — faithful (reconcile only ever runs on a declared
  *derived* relation). This is the fact that separates a reconciled derived key from an untainted
  operand key of the same object type: equal keys share `isDerived`, so a `hder`-derived R-node is
  distinct from every untainted target. The five existing `| reconcile …` matches gained a `_hder`
  placeholder (harmless; no construction sites yet).
- **`reachedByW3a_reach_inert` (`ReconcileCorrect.lean`, `[propext, Quot.sound]`)** — the
  multi-pass fold. For a W3a state `σ` there is an untainted base `σ0` (`ReachedByRules σ0 S T`)
  with `∀ {u v}, isDerived S (v.type, v.pred) = false → NReaches σ.edges u v → NReaches σ0.edges
  u v`. By induction over the write path: **base** = identity; **reconcile** = peel one
  `reconcileKey_reach_inert` then apply the IH. The pass's target-distinctness `v ≠ objNode
  ⟨dt,on⟩ R` is discharged from `isDerived S (v.type,v.pred) = false` vs `hder` (equal keys share
  `isDerived`); the pre-pass R-node-not-a-source premise comes from `reachedByW3a_Rnode_not_source`
  on the sub-derivation, fed by the **schema-level terminal hypothesis** `hterm : ∀ dt R,
  isDerived S (dt,R) = true → NoTtuTarget S R ∧ NoStoreSubjectR T R` (faithful: W3a defers the
  non-terminal `PDerivedTTU`/`PDerivedUserset` shapes — carry `hterm` into the W3a/W4 fragment).

**Resume → close the W3a CORRESPONDENCE. Point 2 step 2 (the deeper blocker) + step 3 remain:**
1. ✅ **DONE this session** — the multi-pass inertness fold (`reachedByW3a_reach_inert`).
2. **Discharge `hag` — the per-relation untainted-correctness lemma (STILL the deeper blocker).**
   With the inertness fold, the operand read `probeNonDerived σ ⟨s, r', ⟨dt,on'⟩⟩` on the full W3a
   `σ` reduces to the read on the base `σ0` (move `probeNonDerived` → `NReaches` via
   `probeNonDerived_iff` + `reach_iff_nreaches` on both σ and σ0 — needs endpoint-closure `hcl`
   from `reachedByW3a_inv`/`reachedByRules_inv`; star-free ⇒ only probe 1 (plain) survives, so the
   read is exactly `NReaches …edges (subjNode s) (objNode ⟨dt,on'⟩ r')`, and `reachedByW3a_reach_
   inert` transfers it — note the operand node has type `dt` = the derived key's type and untainted
   relation `r'`, so `isDerived S (dt, r') = false` gives the target-key hypothesis). Then restate
   W2's `graph_correct_rules` **per hereditarily-untainted relation `r'`** within the mixed schema
   (whole-schema `UntaintedSchema` is too strong): its `sem`/graph only consult the untainted cone,
   so it factors out of the W2 proof but must be re-stated with a *hereditarily-untainted*
   hypothesis on `r'`. Fuel via the T0a-stability sidestep. **NB** the transfer above needs the
   reverse direction too (`NReaches σ0 → NReaches σ`), which is free (`σ0.edges ⊆ σ.edges` by
   `reconcileKey_edges_mono` folded — worth landing as a companion lemma, or strengthen
   `reachedByW3a_reach_inert` to an `↔`).
3. **Candidate completeness + assembly `graph_correct_w3a`** (an admitted `ReachedByW3aAdmitted`:
   every `sem`-member bare subject is enumerated in some `cands` and passes `checkFn`) + assembly:
   route → `probeDerived` → `check_derived_ResidueEmpty` → edge probe →
   `reachedByW3a_reach_collapse_root` → `checkFn_eq_semStep` + `hag` → `sem`. Then widen T3/T6.

## Session 2026-07-11 (W3a read correspondence — R-node-source subtlety RESOLVED + reconcile-edge reachability inertness)

Resuming W3a from "point 1 (`hsrcbare` via `NoRuleOutputs`) done; resume → point 2 (`hag` +
candidate completeness + assembly), **but the prior handoff flagged: resolve the R-node-source
subtlety FIRST — the inertness lemma may be false without an extra hypothesis.**" This session
does exactly that: one green+pushed axiom-clean increment (`GraphIndex/ReconcileCorrect.lean`);
`verify.sh` green throughout (build + 0 sorries + 60 conformance + audit, standard axioms only —
two new theorems `[propext]`, three `[propext, Quot.sound]`). Sorry count held at 0.

**The flagged subtlety, RESOLVED: is the derived R-node ever an edge SOURCE?** A reconcile edge
`subjNode c → objNode ⟨dt,on⟩ R` has a bare source (never a target) and an R-node target; for it
to be *reachability-inert* (so the operand read `probeNonDerived σ ⟨s, r', ⟨dt,on'⟩⟩` on the full
W3a σ matches the untainted base — what `hag` needs), the R-node must have **no out-edge**. But a
base (W2) edge source `subjNode u.subject` equals the R-node exactly when a stored/rewrite-closure
operand tuple carries a **userset subject over the derived relation R** (`⟨dt,on⟩#R`). The Python
DOES admit such usersets (`PDerivedUserset`, `zanzibar_utils_v1.py:1115`), so it is not
unconditionally impossible — the subtlety was real.

**Resolution — R is *terminal* on the single-stratum W3a fragment.** Two faithful fragment
conditions (analogs of W2's `NodupKeys`/`RewriteRanked`, carried into W4): **`NoStoreSubjectR T R`**
(no stored tuple has subject predicate R) and **`NoTtuTarget S R`** (no schema rewrite rule has
target relation R — the "target from tupleset with derived target" shapes `PDerivedTTU`/
`PDerivedTuplesetTTU` are deferred past W3a). A rewrite-closure tuple's subject predicate is the
seed's (computed rewrites keep the subject) or a TTU rule's `tr`; under both conditions neither is
R, so **no W3a edge is sourced at an R-userset node** and the R-node has no out-edge.

**The increment (`GraphIndex/ReconcileCorrect.lean`, axiom-clean).**
- **`nreaches_cons_inert`** (`[propext]`) — generic single-new-edge inertness: if the target `b` of
  a prepended edge is never a *source* in the old edges, a path to any `v ≠ b` in `(a,b)::edges` is
  already a path in `edges`. Via `nreaches_cons_split` (the new edge, if used, must exit `b` —
  impossible — or be the final hop to `b ≠ v`).
- **`NoTtuTarget` / `NoStoreSubjectR`** fragment predicates + subject-predicate avoidance across
  the rewrite closure: `rewriteStep_subject_pred_ne` (one hop keeps the subject off R — computed
  preserves it, `ttu tr` gives `tr ≠ R`) → `rewriteClosureAux_subject_pred_ne` →
  **`rewriteClosure_subject_pred_ne`**.
- **`reachedByW3a_edge_source_ne_R`** — no W3a edge is sourced at an R-userset node (base source =
  closure subject pred ≠ R; reconcile source = bare candidate pred `BARE ≠ R`), by induction over
  the write path. Corollary **`reachedByW3a_Rnode_not_source`** (`k.pred = R` ⇒ no out-edge). **This
  resolves the flagged subtlety.**
- **`reconcileKey_reach_inert`** (`[propext]`) — the payoff: one reconcile pass on key `(dt,R')`
  (bare candidates, `R' ≠ BARE`, R'-node not a source in σ) adds no reachability to any
  `v ≠ objNode ⟨dt,on⟩ R'`. Peels the guarded `writeDirect` fold one candidate at a time via
  `nreaches_cons_inert`, maintaining "R'-node not a source" (each new edge's bare source has
  predicate `BARE ≠ R'`). The **per-pass** inertness the multi-pass `hag` transfer folds over.

**Resume → close the W3a CORRESPONDENCE (point 2, the deeper blocker), now unblocked on inertness:**
1. **Multi-pass inertness (mechanical fold).** Induct over `ReachedByW3a` and fold
   `reconcileKey_reach_inert` at each reconcile pass down to the `ReachedByRules` base, giving
   `NReaches σ.edges (subjNode s) (objNode ⟨dt,on'⟩ r') → NReaches σ_base.edges …` for an untainted
   operand `r'` (`r' ≠` any reconcile `R'`, since `r'` untainted / `R'` derived). Needs the fragment
   to carry `NoTtuTarget`/`NoStoreSubjectR` for **every** derived relation with a reconcile pass
   (schema-level: `∀ R, isDerived S (dt,R) → NoTtuTarget S R ∧ NoStoreSubjectR T R`), and the R'-node
   not-a-source at each pre-pass sub-state (from `reachedByW3a_Rnode_not_source` on the sub-derivation).
   NB the base ↔ full state relation: `ReachedByW3a` doesn't expose `σ_base` — either strengthen the
   inductive to carry it, or prove the fold as a `σ`-relative statement (probeNonDerived on σ equals
   probeNonDerived on the stripped edges).
2. **Discharge `hag` — the per-relation untainted-correctness lemma (STILL the deeper blocker).**
   With inertness (1), the operand read reduces to the untainted-base read; then restate W2's
   `graph_correct_rules` **per hereditarily-untainted relation `r'`** within the mixed schema (the
   whole-schema `UntaintedSchema` is too strong). Fuel via the T0a-stability sidestep.
3. **Candidate completeness + assembly `graph_correct_w3a`** (an admitted `ReachedByW3aAdmitted`;
   route → `probeDerived` → `check_derived_ResidueEmpty` → edge probe →
   `reachedByW3a_reach_collapse_root` → `checkFn_eq_semStep` + `hag` → `sem`) + T3/T6 widening.

## Session 2026-07-11 (W3a read correspondence — `hsrcbare` discharged via `NoRuleOutputs`; the reach-collapse fires unconditionally)

Resuming W3a from "the reach-collapse spine done over a free `hsrcbare`; resume → (1)
discharge `hsrcbare` via `NoRuleOutputs`, (2) the per-relation `hag` + candidate
completeness + assembly." One green+pushed axiom-clean increment
(`GraphIndex/ReconcileCorrect.lean`); `verify.sh` green throughout (build + 0 sorries + 60
conformance + audit, standard axioms only — one new theorem axiom-free). Sorry count held at
0. This closes **point 1** of the two remaining W3a correspondence pieces: the reach-collapse
now fires with **no free hypothesis** on the boolean-rooted fragment.

**The increment — `hsrcbare` discharged (`GraphIndex/ReconcileCorrect.lean`, axiom-clean).**
The prior session left the reach-collapse (`reachedByW3a_reach_collapse`) stated over a free
`hsrcbare` (every R-node in-edge source is bare). This session discharges it on the fragment
where the derived def `e = lookup (dt, R)` is **`inter`/`excl`-rooted** — the analytic side
condition (`NoRuleOutputs`, the W3a analog of W2's `TtuTuplesetsDirect`).
- **`RootBoolean e`** (root is `inter`/`excl`) + `exprArms_rootBoolean` (emits no rewrite
  arms — `exprArms` walks into `union` but stops at `inter`/`excl`) + `exprDirects_rootBoolean`
  (carries no `Direct` storage arm).
- **`NoRuleOutputs S dt R`** (no schema rewrite rule outputs `(dt,R)`) + **`noRuleOutputs_of_
  root`** — via `schemaRewrites_provenance` + `NodupKeys` (`lookup_of_mem`): a rule with
  `(objectType,outRel) = (dt,R)` comes from the def at key `(dt,R)` = `e`, boolean-rooted,
  which emits no arms.
- **`reachedByW3a_Rnode_source_bare`** (the payoff) — by induction over the W3a write path:
  the **base** (rewrite-closure) leg landing on `objNode ⟨dt,on⟩ R` is IMPOSSIBLE (a closure
  tuple there is a stored `(dt,R)` tuple — none, by `exprDirects_rootBoolean` +
  `StoreValidRules`; or a rewrite output `(dt,R)` — none, by `noRuleOutputs_of_root`), so
  every R-node in-edge is a **reconcile** edge, whose source `subjNode c` is bare because the
  `reconcile` constructor now carries `hcands : ∀ c ∈ cands, c.predicate = BARE` (faithful —
  the `_leaf_concretes` candidates are bare concretes). **`ReachedByW3a.reconcile` strengthened
  with `hcands`** (the three existing inductions updated; harmless).
- **`reachedByW3a_reach_collapse_root`** — the fully-discharged collapse: a path to the derived
  object node is a *single* reconcile edge, no `hsrcbare` free. Ready to compose with
  `checkFn_eq_semStep` for `reach ↔ [reconcile wrote s's edge] ↔ checkFn ↔ sem`.
- Node-projection simp lemmas `objNode_type` / `subjNode_pred` added locally (the ObjStar
  copies aren't in the W3a import chain).

**Resume → close the W3a CORRESPONDENCE. One piece remains (point 2, the deeper blocker):**
1. ✅ **DONE this session** — `hsrcbare` via `NoRuleOutputs` (`reachedByW3a_reach_collapse_root`).
2. **Discharge `hag` — the per-relation untainted-correctness lemma**, then candidate
   completeness + assembly `graph_correct_w3a`. `hag` (`graphRec σ s dt on r' = semAux S s T q f
   dt on r'` for untainted operand `r'`) restates W2's `graph_correct_rules` per-relation within
   the mixed schema (reconcile edges into derived-R nodes are reachability-inert for untainted-`r'`
   object nodes — a derived edge's bare-candidate source is never an intermediate object node);
   fuel via the T0a-stability sidestep. Then candidate completeness (an admitted
   `ReachedByW3aAdmitted`: every `sem`-member bare subject is enumerated in some `cands` and
   passes `checkFn`) + assembly: route → `probeDerived` → `check_derived_ResidueEmpty` → edge
   probe → `reachedByW3a_reach_collapse_root` → `checkFn_eq_semStep` + `hag` → `sem`. Then widen
   T3/T6 as free corollaries. **This is the genuine remaining core** — the per-relation restatement
   of `graph_correct_rules` (whole-schema `UntaintedSchema` is too strong for W3's mixed schema).

   **Design notes for the next session (analytic, this session — de-risk the assembly):**
   - **`checkFn` is STABLE across reconcile passes on the fragment (the enabling fact).** A
     `ComputedOnly` derived def references only *untainted operand* relations `r'` (no self-ref
     to `R`). Reconcile passes add only derived-R-node edges; if those are **inert for operand
     reads** (`probeNonDerived ⟨·, r', ·⟩` unchanged), then `checkFn` computed mid-fold equals
     `checkFn` at the final σ — so the soundness link (edge present ⇒ `checkFn` was true ⇒ via
     `hag` ⇒ `sem`) needs no fold-accumulator gymnastics. This is why the fragment forbids
     `direct`/`ttu` leaves on the derived def and requires untainted operands.
   - **SUBTLETY to check before proving inertness — is the derived R-node ever an edge SOURCE?**
     A base (W2) edge source is `subjNode u.subject`; for a *userset* subject `⟨dt,on⟩#R`
     (type dt, name on, pred R) this equals `objNode ⟨dt,on⟩ R` (both `⟨dt,on,R,plain⟩`). So if
     a stored/rewritten operand tuple carries a userset subject over the **derived** relation `R`,
     the R-node HAS an out-edge and the new reconcile edge is NOT reachability-inert. Need either
     (a) a fragment condition forbidding usersets-over-derived-`R` as subjects (cf. the Python
     `UnsupportedByGraphIndex` scope rejection for *wildcard* usersets over derived relations —
     check whether plain usersets over derived relations are also excluded / admission-invalid),
     or (b) prove such subjects can't be a stored/rewrite-closure subject under `StoreValidRules`
     + `ComputedOnly`. Resolve this first; the inertness lemma (⇒ `hag` reduces to W2 per-relation
     ⇒ assembly) hinges on it. Do NOT land an inertness lemma without settling the R-node-source
     question — it may be false without an extra hypothesis.

## Session 2026-07-11 (W3a read correspondence — the bare-subject reach-collapse spine + attack-first NoRuleOutputs finding)

Resuming W3a from "two structural spines done; resume → close the CORRESPONDENCE (three
sharply-isolated points)." One green+pushed axiom-clean increment (`GraphIndex/
ReconcileCorrect.lean`); `verify.sh` green throughout (build + 0 sorries + 60 conformance
+ audit, standard axioms only — two of the four new theorems are **axiom-free**). Sorry
count held at 0. This lands the **reach-collapse spine** (ROADMAP W3a read, point 2's
structural half), plus an attack-first finding that narrows the fragment.

**Attack-first HEADLINE (analytic case-analysis, not a correctness refutation): the naive
single-edge reach-collapse is FALSE on the full `ComputedOnly` fragment — it needs a
`NoRuleOutputs S R` side condition, the W3a analog of W2's `TtuTuplesetsDirect`.** The
roadmap's stated collapse ("a derived edge's source is a bare candidate, never a target,
so no hop can precede it") assumes *every* edge into the derived R-node is a reconcile
edge from a **bare** source. But if the derived def `e = lookup (dt,R)` has a **top-level
`union`** exposing a `computed` arm (`member or (admin but not suspended)`), `exprArms`
emits a `computed` rewrite rule `… ↦ R`, so W2's base rewrite-closure *also* lands tuples
on the R-node — and a `computed` rewrite carries the operand chain's subject, which for a
ttu-derived operand is a **userset (non-bare)** node that CAN be an edge target. Then the
path is genuinely ≥ 2 hops (`subjNode s → g#x → objNode R`) and the collapse fails.
`check = sem` still HOLDS in both cases (both mechanisms agree — this is a *proof-shape*
limitation, not unsoundness); the single-edge collapse holds exactly when **no rewrite
rule outputs `R`** — i.e. the derived def is `inter`/`excl`-rooted (`exprArms … = []`).
`member but not banned` (`.excl`-rooted) and `(a or b) but not c` (`.excl` at the root,
union underneath) both satisfy this; only a union-rooted-with-tainted-arm def breaks it.

**The increment — the reach-collapse spine (`GraphIndex/ReconcileCorrect.lean`, axiom-clean).**
- **`ReachedByW3a.reconcile` strengthened** with `hRne : R ≠ BARE` (faithful — reconcile
  only runs on declared derived relations; the two existing inductions ignore it).
- **`nreaches_collapse_of_source_notarget`** (NO axioms) — generic: if every source of an
  edge into `v` has itself no in-edge, any path to `v` is a single edge (`nreaches_last`
  twice: the last-edge source's own in-edge would contradict the hypothesis).
- **`reachedByW3a_edge_target_ne_bare`** — every W3a edge target has a non-`BARE`
  predicate (base = `objNode u.object u.relation`, pred `u.relation ≠ BARE` via
  `rewriteClosure_rel_ne_bare`; reconcile = `objNode ⟨dt,on⟩ R`, pred `R ≠ BARE` via the
  new constructor field). Hence **`reachedByW3a_bareNode_no_inedge`** — a `BARE`-pred node
  is never an edge target (the structural fact behind the collapse).
- **`reachedByW3a_reach_collapse`** — assembly: a bare-subject path to the derived object
  node `objNode ⟨dt,on⟩ R` is a *single* edge, given `hsrcbare` (every R-node in-edge
  source is bare — the isolated `NoRuleOutputs` gap). This is the last structural link
  before `reach ↔ [reconcile wrote s's edge] ↔ checkFn ↔ sem`.

**Resume → close the W3a CORRESPONDENCE. Two pieces remain, further sharpened:**
1. **Discharge `hsrcbare` via `NoRuleOutputs S R`** (the fragment side-condition found this
   session). Prove: on an `inter`/`excl`-rooted derived def, no `schemaRewrites S` rule has
   `outRel = R` (`exprArms` of an `.inter`/`.excl` root is `[]`), and no store tuple has
   relation `R` (its `ComputedOnly` def has no direct arm ⇒ `exprDirects = []` ⇒ fails
   `StoreValidRules`). So every edge into the R-node is a reconcile edge (via
   `reachedByW3a_edge_sound`'s base leg being vacuous on relation `R`), whose source is a
   bare candidate `c` — giving `hsrcbare`. Then `reachedByW3a_reach_collapse` fires
   unconditionally on the fragment.
2. **Discharge `hag` — the per-relation untainted-correctness lemma (STILL the deeper
   blocker)**, then candidate completeness + assembly `graph_correct_w3a`. `hag`
   (`graphRec σ s dt on r' = semAux S s T q f dt on r'` for untainted operand `r'`)
   restates W2's `graph_correct_rules` per-relation within the mixed schema (the reconcile
   edges into derived-R nodes are reachability-inert for untainted-`r'` object nodes: a
   derived edge's bare-candidate source is never an intermediate object node); fuel via the
   T0a-stability sidestep. With `hag` + `checkFn_eq_semStep` + the collapse (piece 1) +
   candidate completeness (an admitted `ReachedByW3aAdmitted`: every `sem`-member bare
   subject is enumerated in some `cands` and passes `checkFn`): route → `probeDerived` →
   `check_derived_ResidueEmpty` → edge probe → `reachedByW3a_reach_collapse` → `checkFn` →
   `sem`. Then widen T3/T6 as free corollaries.

## Session 2026-07-11 (W3a read correspondence — checkFn↔sem-step reduction + reconcile edge characterization)

Resuming W3a from "write model + read collapse done; resume → the correspondence (three
sharply-isolated points)." Two green+pushed axiom-clean increments in a new file
(`GraphIndex/ReconcileCorrect.lean`); `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit, standard axioms only). Sorry count held at 0. This lands the two
*structural* spines of the W3a read correspondence, isolating the remaining work to
exactly the per-relation semantic fact.

**Increment 1 — the `checkFn` ↔ `sem`-step reduction (axiom-clean, `[propext]`).** The
W3a derived def is a boolean tree (`and`/`but not`/`or`) whose leaves are all `computed`
refs — captured by **`ComputedOnly : Expr → Prop`** (allows `computed`/`union`/`inter`/
`excl`; forbids `direct`/`ttu`, which would route onto leaf families, deferred past W3a).
- **`evalE_computedOnly`** (NO axioms) — on a `ComputedOnly` expr `evalE` consults its
  node-recursion `rec` only at `(dt, on, ·)` (never reaches a `direct`/`ttu` leaf), so two
  `rec`s agreeing there evaluate the whole tree identically — independent of subject/store/
  query/enclosing-relation. A one-shot `Expr` induction.
- **`checkFn_eq_semStep`** (`[propext]`) — `σ.checkFn T s dt on R e = semAux S s T q (f+1)
  dt on R`, given `S.lookup (dt,R) = some e`, `ComputedOnly e`, and the per-relation
  agreement `hag : ∀ r', graphRec σ s dt on r' = semAux S s T q f dt on r'`. `checkFn`'s
  graph node-recursion (`graphRec = probeNonDerived`) is swapped for `sem`'s fuel recursion
  via `evalE_computedOnly`. **This reduces the reconcile guard `checkFn = sem`-membership to
  exactly `hag` — the per-relation untainted graph↔`sem` fact, the stated W3a blocker.**

**Increment 2 — the reconcile edge characterization (axiom-clean, `[propext]`).** The
structural spine for the (bare-subject) reach-collapse — `reconcileKey` is a guarded
`writeDirect` fold, so its edge effect is exactly:
- **`reconcileKey_edges_mono`** — the fold only ever adds edges (old edges persist).
- **`reconcileKey_edge_sound`** — every edge of `σ.reconcileKey T dt on R e cands` is an
  old σ-edge or a candidate's derived edge `subjNode c → objNode ⟨dt,on⟩ R` (`c ∈ cands`).
- **`reachedByW3a_edge_sound`** — every edge of a W3a-reached state is either a materialised
  rewrite-closure tuple of a stored tuple (the untainted base — `reachedByRules_edge_sound`)
  or a reconcile derived edge, by induction over the write path. The W3a analog of
  `reachedByDirect_edge_sound` / the W2 edge-sound groundwork.

**Resume → close the W3a CORRESPONDENCE. Two pieces remain, now sharply isolated:**
1. **Discharge `hag` — the per-relation untainted-correctness lemma (THE blocker).** For an
   untainted operand relation `r'` in the mixed W3a schema, `graphRec σ s dt on r' =
   probeNonDerived σ ⟨s, r', ⟨dt,on⟩⟩` must equal `semAux S s T q f dt on r'` (at a fuel
   reconciled by the T0a-stability sidestep). `graph_correct_rules` proves this for a whole
   `UntaintedSchema`, too strong for W3's mixed schema — restate **per-relation** (an
   untainted relation's graph read = its `sem` within a partially-tainted schema; its `sem`/
   graph only consult the untainted cone, so it factors out of the W2 proof but must be
   re-stated with a *hereditarily-untainted* hypothesis on `r'`, not whole-schema
   `UntaintedSchema`). Also needs: the reconcile edges (into derived-`R` object nodes) are
   reachability-inert for untainted-`r'` object nodes — a derived edge's source `subjNode c`
   (bare candidate) is never an intermediate object node, so it cannot extend a path to an
   untainted-relation node.
2. **The reach-collapse + candidate completeness + assembly `graph_correct_w3a`.** With the
   edge characterization (increment 2): for a bare-subject derived query, `reach (subjNode
   s) (objNode ⟨dt,on⟩ R)` collapses to a *single* reconcile edge — a derived edge's source
   is a bare candidate node, which (predicate `BARE` ≠ any relation) is never an edge
   *target*, so no hop can precede it; hence `reach ↔ [reconcile wrote s's edge] ↔ checkFn
   s ↔ sem` (via increment 1 + `hag`). Needs: (a) the single-edge structural lemma (bare
   node never an object-node target — base edges via `rewriteClosure_rel_ne_bare`, derived
   `R ≠ BARE`); (b) candidate completeness (every `sem`-member bare subject is enumerated in
   some reconcile pass's `cands` and passes `checkFn` — an admitted `ReachedByW3aAdmitted`,
   the W3a analog of `ReachedByRulesAdmitted`); (c) route → `probeDerived` →
   `check_derived_ResidueEmpty` (already have) → the edge probe → the collapse. Then widen
   T3/T6 as free corollaries.

## Session 2026-07-10 (W3 STARTED — derived reconcile / residue path; attack-first + W3a read collapse + write model)

Resuming from W1 + W2 both closed → **ROADMAP stage W3** (derived reconcile: `and` /
`but not`, the per-key residue `(stars, neg, upos)`, the processor cascade). Two
green+pushed axiom-clean increments; `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit, standard axioms only). Sorry count held at 0. This starts the
W3a sub-stage (star-free, bare-subject derived booleans), matching how W1/W2 each began
with attack-first + a write model before the read correspondence.

**Sub-staging plan (designed this session):** W3a star-free bare booleans → W3b userset
subjects (`upos`) → W3c star data (`stars`/`neg`) → W3d multi-stratum cascade (the
cross-key re-reconcile hazard + contentful T5 outbox drain). W3a is the "zero residue
content" analog of W1a's "zero bridges".

**Attack-first HEADLINE (machine-checked `#eval` vs `sem`, then deleted): the W3a
residue-read ↔ `sem` correspondence HOLDS — no refutation.** On a `doc#viewer :=
member but not banned` (both direct) star-free store, `check` (routed to `probeDerived`)
equals `sem` on every query: the derived edge is materialised for the member-not-banned
subject, none for the banned one, and the residue is EMPTY. This confirmed the key W3a
modeling fact:

> **On the star-free bare-subject fragment the processor stores NO residue row.**
> `stars = neg = upos = ∅` ⇒ `_store_residue` never fires (I6's non-empty clause), so
> the state stays `ResidueEmpty` and a derived relation only adds **edges** — a derived
> edge being structurally an ordinary `writeDirect ⟨s, R, o⟩`. So W3a reuses ALL of W2's
> write + preservation machinery, and the derived read collapses to a pure edge probe.

**Increment 1 — the read-side collapse (`GraphIndex/Reconcile.lean`, axiom-clean).**
`probeDerived_residueEmpty` — the derived read on an empty residue is the bare edge
probe (object-wildcard / `'*'`-subject / userset all read `False` on empty
`stars`/`neg`/`upos`; a bare non-`'*'` subject reduces to `reach (subjNode s) (objNode
o R)`). `probeDerived_ResidueEmpty` (global corollary) + `check_derived_ResidueEmpty`
(routing: a derived read on an empty residue is decided by the same reachability the
non-derived read uses — the residue machinery is provably inert on W3a).

**Increment 2 — the WRITE model (`GraphIndex/ReconcileWrite.lean`, axiom-clean).**
Modeling discovery from `processor.py:_EvalContext`/`reconcile`: on the W3a fragment
(derived def = boolean tree over `computed` refs to UNTAINTED relations, single stratum)
the compiled `check_fn` evaluates that tree with every leaf dispatching to `leaf_check`
= `widx.check` = the graph's ≤4-probe read (`probeNonDerived`). So `check_fn` is exactly
`evalE` with `rec` reading the graph. Delivered:
- `graphRec` (`= probeNonDerived`) + `GraphState.checkFn` (`= evalE (graphRec) …`).
- `GraphState.reconcileKey` — a guarded `writeDirect` fold: materialise the derived
  edge for each candidate bare subject iff `checkFn` (the `reconcile_subject` rule
  `want_edge = should ∧ ¬covered`, `covered = false` star-free).
- `structInv_/residueEmpty_/inv_/quiescent_reconcileKey` (guarded fold preserves
  everything `writeDirect` does — each step is `writeDirect` or identity).
- **`ReachedByW3a`** (write-closure: W2's `ReachedByRules` base + reconcile passes) +
  **`reachedByW3a_inv`** (T2a `Inv` conjunct: `Inv ∧ ResidueEmpty ∧ Quiescent`, by
  induction over the concrete path) + `reachedByW3a_residueEmpty` (the read-side hook).

**Resume → the W3a CORRESPONDENCE (`checkFn = sem` + candidate completeness ⇒
`graph_correct_w3a`), sharply isolated. KEY FINDING for the next session:**
1. **`checkFn σ s = sem`-membership of `s` in the derived key.** Via `evalE_congr`
   (`Spec/Confine.lean`: `evalE` agrees if `rec` agrees on the referenced keys over
   `oname ∪ storedNames`) reducing it to: for each `computed r'` operand (untainted
   `r'`), `graphRec σ s dt on r' = sem`-membership. **BLOCKER discovered:**
   `graph_correct_rules` needs `UntaintedSchema S` (no `.inter`/`.excl` in ANY def) —
   but W3a's schema HAS the derived `.excl`, so it does NOT apply to the whole schema.
   The next increment needs a **per-relation** untainted-correctness lemma: an untainted
   relation `r'`'s graph read (`probeNonDerived`) equals its `sem`-membership *within a
   mixed (partially-tainted) schema*. The untainted relation's `sem`/graph only consult
   the untainted edges + its own def, so this should factor out of the existing W2
   proof, but it must be RE-STATED per-relation (the whole-schema `UntaintedSchema`
   hypothesis is too strong for W3). Fuel via the T0a-stability sidestep (`sem_fuel_
   stable`; the derived-key `sem` is `semAux` at `fuelBound`, `checkFn` reads the graph
   at "infinite" fuel — reconcile the two by stability, as W1c/W2 did).
2. **Candidate completeness.** `ReachedByW3a`'s `reconcile` leg fires on a GIVEN `cands`
   list. Completeness (`sem ⇒ edge`) needs the closure SATURATED: every `sem`-member
   bare subject is in some reconcile pass's `cands` AND passes `checkFn`. Model the
   candidate enumeration (`_leaf_concretes`: concretes of the positive leaves) and prove
   it covers every `sem`-member — the W3a analog of W2's edge-completeness / admitted
   closure. Likely an admitted `ReachedByW3aAdmitted` (grant + reconcile edges present).
3. **Assembly `graph_correct_w3a`.** For a derived query: route to `probeDerived`
   (`isDerived`), collapse to the edge probe (`check_derived_ResidueEmpty` +
   `reachedByW3a_residueEmpty`), then `reach (subjNode s) (objNode o R) ↔ [edge written]
   ↔ checkFn ↔ sem`. For an untainted query: the per-relation lemma from (1). Then widen
   T3/T6 (`Equiv.lean`) as free corollaries. NB W3a fragment: star-free, bare subjects,
   derived def = boolean over `computed` refs to untainted relations (no direct/ttu arms
   ON the derived relation — that adds leaf-family routing, defer). Attack-first any
   widening before proving.

## Session 2026-07-10 (W2 FULLY CLOSED — completeness `sem ⇒ reach` + `graph_correct_rules` + T3/T6 widened)

Resuming W2 from "soundness direction closed; resume → W2 COMPLETENESS + assembly".
Delivered the **whole W2 correspondence** — `graph_correct_rules` (full `check = sem` on
the untainted rule-routing fragment) — as three green+pushed axiom-clean increments, plus
the T3/T6 corollary widening. `verify.sh` green throughout (build + 0 sorries + 60
conformance + audit). Sorry count held at 0. **ROADMAP stage W2 is now closed end-to-end
(soundness + completeness), matching W1a/W1b/W1c.**

**Attack-first HEADLINE (machine-checked `#eval`, then deleted): closure-saturation HOLDS
at the write model's `|keys|+1` bound — no refutation.** The completeness `computed` case
needs the materialised rewrite-closure closed under one more rewrite step. Attack-first
stressed this against adversarial schemas: mutual-`ttu` cycles and **predicate-ratcheting
unions whose distinct reachable-tuple count exceeds `|keys|+1`** (`schemaRatchet2`: 6
distinct reachable > bound 4) — saturation held in every case. The finding: the **rewrite
DEPTH** (shortest rewrite-path length), not the count, is bounded by `|keys|`, because each
step advances the relation to a rule `outRel`. So `|keys|+1` closure levels capture every
reachable tuple *and* leave the top layer's rewrite-image already inside. Notably
saturation held even for the *cyclic* schemas, which the provable-path hypothesis
(`RewriteRanked`) excludes — so `RewriteRanked` is sufficient, not necessary.

**Increment 1 — the admitted W2 closure + edge-completeness (`GraphIndex/RulesComplete.lean`,
axiom-clean `[propext]`).** `writeRules` folds `writeDirect` (guarded, cycle-rejecting) over
the closure, so edge-completeness needs every fold write admitted. `FoldAdmits` records
exactly that; `foldl_writeDirect_edges_mono` (writeDirect only adds edges) +
`foldl_writeDirect_edge_complete` give it. `ReachedByRulesAdmitted` (the admitted W2
closure) + `reachedByRulesAdmitted_edge_complete` (every rewrite-closure tuple of every
stored write has its edge — the completeness analog of `reachedByRules_edge_sound`) +
`reachedByRulesAdmitted_seed_edge` (the stored-seed case the direct/ttu cases consult).

**Increment 2 — rewrite-closure saturation (`GraphIndex/RulesSaturate.lean`, axiom-clean
`[propext, Quot.sound]`).** `RewriteRanked S` (the faithful fragment condition: the rewrite
graph on relations is acyclic — a `|keys|`-bounded rank every rewrite rule strictly
increases; Python stratification rejects computed-userset cycles). The rewrite-layer
algebra `stepN` / `stepN_step_comm` / `mem_aux_of_stepN` / `stepN_of_mem_aux` decomposes
`rewriteClosureAux` into depth layers; `rwKey_rank_lt` (a step strictly bumps rank) +
`stepN_rank_ge` (a depth-`k` tuple has rank ≥ `k`) give the depth bound; **`rewriteClosure_
saturated`** — `w ∈ rewriteClosure S t`, `u ∈ rewriteStep S w ⇒ u ∈ rewriteClosure S t`.

**Increment 3 — the completeness core + assembly (`GraphIndex/RulesComplete.lean`,
axiom-clean).** `nreaches_of_semAux_rules` (`sem ⇒ reach`) by fuel induction × def-expr
inner induction:
- **direct** — verbatim `nreaches_of_semAux` (direct match = the stored grant's own edge
  via `reachedByRulesAdmitted_seed_edge`; flow-through = the recursion's path + the grant
  edge, appended by `NReaches.tail`).
- **computed** — the fuel IH gives a path to the `r'`-node; **`nreaches_relation_rewrite`**
  redirects it to the `r`-node by **last-edge surgery** (`nreaches_last` exposes the final
  edge = a closure tuple `w` on relation `r'`; its computed rewrite `⟨w.subject, r,
  w.object⟩` stays in the closure by `rewriteClosure_saturated`, so *its* edge into the
  `r`-node is materialised and replaces the last hop). This is the one case needing
  saturation.
- **ttu** — the stored tupleset tuple `w`'s ttu-rewrite is a **depth-1** closure member
  (`rewriteStep_mem_closure`, no saturation), so its edge is materialised; direct
  parent-match = that edge, `rec` disjunct = the parent-userset recursion + the edge.
- **union** — the true arm (arms' rewrite provenance split via `harms`).
**Key scope finding: completeness does NOT need `TtuTuplesetsDirect`** (that was a
*soundness*-only condition — it stops the graph landing non-seed tuples on tupleset
relations; going `sem ⇒ graph` the stored `w` genuinely exists). So `nreaches_of_semAux_
rules` carries only `UntaintedSchema ∧ RewriteRanked ∧ StarFree ∧ admitted`. Assembly
**`graph_correct_rules`** routes `check → probeNonDerived` (`check_eq_probeNonDerived`),
kills probes 2–4 (`reachedByRulesAdmitted_edges_plain` — star-free ⇒ only plain endpoints,
via `rewriteClosure_subjectName`/`_object`), and glues probe 1 through `reach ↔ NReaches`
to soundness (`sem_of_rules_reach`) + completeness. **T3/T6 widened** (`Equiv.lean`):
`backend_equivalence_rules` / `exclusion_effective_rules` / `no_ghost_grant_rules`
(T1 ∘ `graph_correct_rules`, `sem`-stratifiability from `stratifiable_untainted`).

**W2 fragment predicate (assembled):** `WF ∧ UntaintedSchema ∧ TtuTuplesetsDirect ∧
NodupKeys ∧ RewriteRanked ∧ StoreValidRules ∧ StarFreeStore` (soundness needs `TtuTuplesets
Direct`+`NodupKeys`; completeness needs `RewriteRanked`; both need the rest). Carry
`NodupKeys` + `RewriteRanked` into W4 as faithful hypotheses (dict keys; stratification).

**Next: ROADMAP W3** (derived reconcile — the residue path, `and`/`but not`, the processor
cascade). W1 (wildcard bridges) + W2 (rule routing) are now both closed. The *combined*
generality (wildcards + rules + booleans) lands at **W4** (full-scope restatement). NB the
W2 fragment isolates untainted rule routing on star-free data; wildcards-in-rules and the
residue path are still deferred. Attack-first the W3 reconcile output before proving.

## Session 2026-07-10 (W2 SOUNDNESS direction CLOSED — generalised lift + chain composition + `sem_of_rules_reach`)

Continuing W2 from the soundness core (per-tuple membership) → the **whole soundness
direction** (graph reachability ⇒ `sem`). One green+pushed axiom-clean increment
(`GraphIndex/RulesChain.lean`, sorry-free, `[propext, Classical.choice, Quot.sound]`).
`verify.sh` green (build + 0 sorries + 60 conformance + audit). Sorry count held at 0.

**Delivered — the stated blocker cleared: `semAux_lift_untainted`** (the userset lift
GENERALISED from `PureDirect` to `UntaintedSchema`). A userset now flows through a
`computed`/`ttu`/`union` node, not just a `direct` one. Structure: a nested induction —
fuel outside (`semAux_lift_untainted`), `Expr` inside (`evalE_lift`) — whose leaf cases
are:
- **direct** — the DirectCorrect logic verbatim (a direct match of `s'` at a grant is
  absorbed by `s`'s flow-through on the same grant via `mog_intro`/`directLeaf_of_mog`;
  a flow-through by the fuel IH). The DirectCorrect leaf lemmas (`directLeaf_elim`,
  `mog_elim`, `mog_intro`, `directLeaf_of_mog`) are NOT `PureDirect`-specific, so reused
  as-is.
- **computed** — the fuel IH at the sub-node (`evalE`'s `computed r'` case is `rec ot on
  r'`, so `s' ∈ (ot,on,r') ⇒ s ∈ (ot,on,r')` is `ih ot on r'`).
- **ttu** — the stored-parent loop. `ttuLeaf_elim`/`ttuLeaf_intro_rec` (star branch dead
  on star-free data): a *direct* parent-match (`s' = ⟨pt,pn,tr⟩`) becomes `hmem` (`s ∈
  s'`, mono to fuel); a *parent-membership* (`rec` disjunct) the fuel IH. `ttuLeaf`'s
  `rec`-disjunct is subject-independent, so `s` re-fires it identically.
- **union** — the OR (both arms untainted, `containsBool = false`).

**Chain composition + top-level.** `semAux_of_ruleChain` (mirror of DirectCorrect's
`semAux_of_chainN`, but each hop's base membership is `semAux_of_rewriteClosure` at
*some* fuel and the step is `semAux_lift_untainted`; fuel threaded existentially — no
tight bound). New preservation lemmas: `rewriteClosure_subjectName` (rewrites keep the
subject name ⇒ closure subjects star-free) and `rewriteClosure_rel_ne_bare` (a closure
tuple's relation is the seed's or a rewrite output relation — both declared, so the
userset intermediate's predicate ≠ `BARE`). **`sem_of_rules_reach`** (graph reachability
⇒ `sem`) closes the soundness direction end-to-end: `reachedByRules_edge_sound` pins
every edge to a `Tstar = ⋃_{t∈T} rewriteClosure S t` tuple, `chainN_of_trail` → chain,
`semAux_of_ruleChain` → `sem` at some fuel, T0a-stability sidestep
(`sem_fuel_stable` via `stratifiable_untainted` + `storeDeclared_of_validRules`) → `sem
= true`. No fuel-count arithmetic (like W1c).

**Resume → W2 COMPLETENESS + assembly.** Sharply isolated:
1. **Completeness (`sem ⇒ reach`)** — the remaining hard direction. `sem S T q = true`
   (at `fuelBound`) must be witnessed by a graph path over the materialised
   rewrite-closure. Fuel-induction unfolding the query def: `direct` = a stored grant's
   own edge (`admitted`-style edge-completeness for `writeRules`; NB the store tuple `t`
   *is* in `rewriteClosure S t` as the seed, so its edge is materialised) + flow-through;
   `computed`/`ttu`/`union` = the recursion is witnessed by a rewrite-closure chain. The
   graph edge for a computed/ttu step comes from the *rewrite output* tuple being
   materialised — so completeness needs "the rewrite-closure is saturated enough":
   whenever `sem` recurses `rec ot on r'` (computed) it must find the materialised
   rewrite edge. Attack-first the computed-case closure-saturation (the earlier W2 entry
   flagged this — a `T*` tuple on `R'` whose def has `computed R'`-armed `R` should also
   carry the `R`-rewrite in `T*`) before proving. Needs an *admitted* `writeRules`
   closure (`ReachedByRules` admits cycle-rejected edges silently; completeness needs the
   edge present) — the W2 analog of `ReachedByAdmitted`.
2. **Assembly `graph_correct_rules`** — route `check → probeNonDerived`
   (`check_eq_probeNonDerived`), kill probes 2–4 (star-free ⇒ no `wAny`/`wAll` endpoint,
   mirror of `graph_correct_direct`), glue probe 1 via `reach ↔ NReaches` to
   `sem_of_rules_reach` (forward) + completeness (backward). Then T3/T6 widening
   (`Equiv.lean`, free corollaries).

## Session 2026-07-10 (W2 SOUNDNESS core — the rewrite-closure realises `evalE`'s recursion)

Resuming W2 from "write model + read-routing + soundness groundwork + fragment nailed
down (`TtuTuplesetsDirect`); resume → the reachability↔`sem` core". Delivered the
**soundness half's heart** as one green+pushed axiom-clean increment
(`GraphIndex/RulesSound.lean`, sorry-free, `[propext, Classical.choice, Quot.sound]`).
`verify.sh` green throughout (build + 0 sorries + 60 conformance + audit). Sorry count
held at 0. This is the first W2 lemma that ties the graph's rewrite-fanout to `sem`.

**Headline: `semAux_of_rewriteClosure` — every rewrite-closure tuple of a stored tuple
is a `sem` membership at some fuel.** For `t ∈ T` and `u ∈ rewriteClosure S t`, `sem`
derives `u.subject ∈ (u.object, u.relation)`. This is *exactly* "the rewrite-closure
realises `evalE`'s `computed`/`ttu`/`union` recursion", proved by a
generalise-over-`cur` closure induction (mirrors `rewriteClosureAux_object`):
- **seed** (`u = t`): a direct self-grant — `t`'s relation carries a `Direct` arm the
  subject matches (`StoreValidRules`), fuel 1 (`semAux_seed`).
- **computed** hop (`u = ⟨s, R, o⟩` from `⟨s, R', o⟩`): `evalE`'s `computed R'` case is
  `rec o.type o.name R'`, which is *literally the predecessor's membership* — fuel `+1`,
  no rewriting of the recursion needed once `(objectType, matchRel)` are normalised to
  `x`'s fields.
- **ttu** hop (`u = ⟨s#tr, R, o⟩`): the tupleset tuple is a *stored* raw tuple —
  **`closure_tupleset_is_seed` (under `TtuTuplesetsDirect`) forces the predecessor `x`
  to be the seed `t ∈ T`** (a deeper closure tuple can't sit on a TTU tupleset relation:
  `no_rewrite_outputs_tupleset`). So `ttuLeaf`'s stored-tupleset read fires its **direct
  disjunct** (`s = x.subject#tr` matches `⟨pt,pn,tr⟩` in both the `pn≠STAR` and star
  branches) — **no recursion**, fuel 1. This is where the fragment condition earns its
  keep operationally.
- **union**: a true arm makes the OR-tree true (`evalE_{direct,computed,ttu}_arm`, one
  induction each — an `UntaintedSchema` def is a leaf-OR-tree, no `inter`/`excl`).

**Key modelling addition: `NodupKeys S`** (declared keys distinct — the Python schema is
a *dict*). `schemaRewrites` fans out over *all* defs (`flatMap`), but `sem`/`evalE` reads
`S.lookup` = the *first* def with a key; without key-uniqueness a rewrite rule's def
need not be the one `sem` evaluates, and soundness would be FALSE. `lookup_of_mem`
(`NodupKeys ⇒ d ∈ defs → lookup d.1 = some d.2`) is the payoff (hand-rolled `find?`
induction; `WF` currently records only `relNames`, so key-uniqueness is a *new* faithful
hypothesis, not derivable). **Worth flagging for W4:** the full-scope fragment should
carry `NodupKeys`.

**W2 read fragment (assembled):** `UntaintedSchema ∧ TtuTuplesetsDirect ∧ NodupKeys ∧
StoreValidRules ∧ StarFreeStore` (+ `WF`). Consequence lemmas landed: `untainted_noExclAll`
(⇒ `semAux_mono`), `stratifiable_untainted` + `storeDeclared_of_validRules` (⇒
`sem_fuel_stable` for the T0a-stability fuel sidestep), `exprDirects` +
`directTypes_mem_of_exprDirects`.

**Resume → the rest of the W2 soundness half + completeness + assembly.** Sharply
isolated:
1. **Chain composition (soundness end-to-end).** `reachedByRules_edge_sound` pins every
   edge to a rewrite-closure tuple of `Tstar := T.flatMap (rewriteClosure S)`; feed the
   `chainN_of_trail` soundness function to get `TupleChainN Tstar`, then compose hops
   with a **userset lift**. BLOCKER: `semAux_lift` (DirectCorrect) is stated for
   `PureDirect` — W2 needs it generalised to `UntaintedSchema` (a userset flowing
   through a `computed`/`ttu`/`union` node, not just a `direct` one). The per-hop base
   membership is `semAux_of_rewriteClosure` (at *some* fuel `f_w`, not fuel 1) — so use
   the W1c **T0a-stability sidestep** (`sem_fuel_stable`, whose hyps are the consequence
   lemmas above) to discharge total fuel, no tight bound. Intermediate userset predicate
   is `w.relation` (declared ⇒ ≠ `BARE`); subject names star-free (rewrites preserve
   subject name) — both need small preservation lemmas.
2. **Completeness (`sem ⇒ reach`).** `sem`'s computed/ttu/union recursion must be
   witnessed by graph edges (materialised rewrite-closure tuples). The harder direction;
   attack-first the computed-case closure-saturation the earlier entry flagged.
3. **Assembly** `graph_correct_rules` (route to `probeNonDerived` via
   `check_eq_probeNonDerived`; star-free ⇒ probes 2–4 dead) + T3/T6 widening.

## Session 2026-07-10 (W2 — attack-first KILLS the naive fragment; `TtuTuplesetsDirect` + rewrite-closure structure)

Resuming W2 (untainted rule routing) from "write model + read-routing + soundness
groundwork done; resume → the reachability↔`sem` core". Before proving that core,
ran the house move (**attack-first**) on the correspondence's TTU case — and it
**killed the naive W2 statement**: `check ≠ sem` without a storage-only tupleset
side condition. One green+pushed axiom-clean increment
(`GraphIndex/RulesCorrect.lean`, sorry count held at 0, `verify.sh` green: build +
0 sorries + 60 conformance + audit). This is the **fourth false-statement kill by
attack-first** (after additive `fuelBound`, the abstract `WriteStep` closure, and
T0a-without-`StoreDeclared`).

**Attack-first HEADLINE (machine-checked `#eval`, then deleted): the W2 `check =
sem` correspondence is FALSE without `_validate_ttu_tuplesets`.** Counterexample
(both `check`/`sem` evaluated in Lean on the operational `writeRules` state):
schema `doc#viewer := ttu member parent`, `doc#parent := computed linked`,
`doc#linked := direct [group]`, `group#member := direct [user]`; store
`(group:g, linked, doc:d)`, `(user:alice, member, group:g)`; query
`check(alice, viewer, doc:d)`. The graph rewrite-fanout of `(g, linked, d)`
cascades the computed rule `linked ↦ parent` producing `(g, parent, d)`, then fires
the TTU rule on that **rewrite-produced** triple → materialises
`g#member → viewer(d)`, so **`check = true`**. But `sem`'s `ttuLeaf` reads only
**stored** `parent` tuples (none — `parent` is computed) → **`sem = false`**.
Control with a directs-only `parent` (raw stored tupleset): both `true`, agree.

This is exactly `zanzibar_utils_v1.py:_validate_ttu_tuplesets` (:898): an *untainted*
tupleset relation with computed/rewritten arms is rejected at compile ("the graph
index cannot separate raw from rewritten members of an untainted relation"). **Key
subtlety: `GraphAccepts` clause (3) does NOT catch this** — a `computed`-armed
tupleset is untainted (`isDerived = false`), so it passes `GraphAccepts`. The W2
fragment needs the *stronger* directs-only condition, not just non-derived.

**Delivered (`GraphIndex/RulesCorrect.lean`, sorry-free, axiom-clean — all standard
axioms):**
- **`directsOnly : Expr → Bool`** (faithful `_directs_only`: `Direct` or `union`
  thereof) + **`TtuTuplesetsDirect S`** (faithful `_validate_ttu_tuplesets`: every
  TTU's tupleset relation, for every def carrying that key, is directs-only — stated
  over all matching defs so no key-uniqueness lemma is needed; implied by Python's
  dict keys).
- `exprArms_key` (a rule from `exprArms ot rel e` carries `(objectType,outRel) =
  (ot,rel)`) + **`exprArms_directsOnly`** (a directs-only expr yields NO rewrite arms
  — the core of the finding) + `schemaRewrites_provenance`.
- **`no_rewrite_outputs_tupleset`** — under `TtuTuplesetsDirect`, no schema rewrite
  outputs a TTU's tupleset relation (such a rule would come from a directs-only def,
  which contributes no arms).
- `applyRRule_object`/`applyRRule_outRel`, `rewriteStep_object`/`rewriteStep_outRel`,
  `rewriteClosureAux_object` → **`rewriteClosure_object`** (every closure tuple keeps
  the raw write's object — rewrites only change `(subject, relation)`) and
  **`rewriteClosure_seed`** (`t ∈ rewriteClosure S t`).
- `rewriteClosureAux_produced`/`rewriteClosure_produced` (every closure tuple is the
  raw seed or a rewrite output) → **`closure_tupleset_is_seed`** (the operational
  payoff: under the fragment condition a closure tuple sitting on a TTU tupleset
  relation IS the raw seed — so the graph only ever lands the raw seed on a tupleset
  relation, matching `ttuLeaf`'s stored-tupleset read; this is what will keep the
  deferred ttu correspondence sound).

**Resume → the W2 reachability↔`sem` core, now with the fragment nailed down.** The
fragment predicate is `UntaintedSchema S ∧ TtuTuplesetsDirect S` (+ `StoreValid`
analog). Structural groundwork is in place (object preservation, seed membership,
storage-only tuplesets). The remaining genuinely-new content is unchanged from the
prior entry — `TupleChain over the rewrite-closure T* ↔ sem over T` (computed = the
`rec`-indirection, absorbed by a rewrite hop; ttu = the stored-parent loop, now
provably reading only raw seeds via `closure_tupleset_is_seed`; union = the OR; fuel
via the W1c `sem_fuel_stable` sidestep) — then `graph_correct_rules` + T3/T6. NB the
computed case needs a "closure closed under the computed rewrite" step (a `T*` tuple
on relation `R'` whose def has a `computed R'`-armed relation `R` also has the
`R`-rewrite in `T*`); attack-first that closure-saturation before proving.

## Session 2026-07-10 (W2 STARTED — untainted rule routing; attack-first + the rewrite-fanout write model)

Resuming from W1 fully closed (all three sub-stages) → **ROADMAP stage W2** (rule
routing: `computed`, `union` of untainted operands, `ttu`). One green+pushed
axiom-clean increment: the **attack-first validation** and the **W2 write model**
(`GraphIndex/RulesWrite.lean`, sorry-free, axiom-clean `[propext, Classical.choice,
Quot.sound]`). `verify.sh` green (build + 0 sorries + 60 conformance + audit). Sorry
count held at 0. Mirrors how W1b/W1c landed their "write model DONE" increments before
the read correspondence.

**Attack-first HEADLINE (machine-checked `#eval` vs `sem`, then deleted): the
rewrite-fanout design is confirmed, no refutation.** The key modeling discovery from
reading `zanzibar_utils_v1.py` (`RuleSet.apply` / `_rewrite_rule` / `_emit_expr`): the
untainted graph index does NOT materialize edges *between* relation nodes. Instead **a
raw write of a public tuple `t` is expanded by `RuleSet.apply` into the rewrite-closure
of `t`** under the schema's Computed/TTU Rules (fan-in through unions, iterated to a
fixpoint), and *each* resulting triple is materialized as an ordinary direct closure
edge; **the ≤4-probe reachability read is unchanged**. The two rewrite kinds
(`_rewrite_rule`, `:834-852`):
- **Computed** `R := computed R'` on object type `ot`: a tuple `(s, R', o)` (o.type=ot)
  also produces `(s, R, o)` — same subject/object, relation `R'↦R`.
- **TTU** `R := ttu tr ts` on object type `ot`: a tuple `(s, ts, o)` (o.type=ot)
  produces `(⟨s.type, s.name, tr⟩, R, o)` — the tupleset parent `s` becomes the userset
  `s#tr`, relation `ts↦R`. (Stored-parent semantics: fires on the STORED tupleset
  tuple.) The produced edge is `objNode(⟨s.type,s.name⟩, tr) → objNode(o, R)`, which
  reachability then composes (`u → parent#tr → o#R`).
- **Union** `_emit_expr` walks INTO union nodes, so each arm's Computed/TTU leaf becomes
  a rule targeting the SAME relation; `Direct` arms are admission Filters (no fan-out).

Verified `sem` on a computed / chained-computed (`super:=editor:=viewer`) / ttu (±) /
union / userset-flow corpus — all seven `#eval`s matched hand expectations exactly, so
`sem`'s computed/union/ttu recursion is precisely what the rewrite-fanout materializes.
No statement-level surprise (like W1a/W1c; unlike W1b's bridges-mandatory finding).

**The write model (`GraphIndex/RulesWrite.lean`, axiom-clean):**
- `RuleKind` (`computed` | `ttu tr`) + `RRule` (objectType, matchRel, outRel, kind);
  `exprArms ot outRel : Expr → List RRule` (walks unions, one rule per Computed/TTU
  leaf, `[]` for Direct/inter/excl); `schemaRewrites S` = all rules of the schema.
- `applyRRule` (fire one rule on a matching tuple), `rewriteStep S t` (all matching
  rules fire — fan-in), `rewriteClosureAux`/`rewriteClosure S t` (bounded fixpoint,
  `|keys|+1` levels — the rewrite graph on relations is a DAG; duplicates harmless for
  reachability, §11-A4).
- **`GraphState.writeRules σ S t`** = `(rewriteClosure S t).foldl writeDirect σ` — the
  faithful `RuleSet.apply t` + per-triple `add_tuple`. Reuses ALL of W1's `writeDirect`
  machinery (cycle-rejection, residue-free).
- Fold-preservation helpers (`structInv_/residueEmpty_/inv_/quiescent_/schema_foldl_
  writeDirect`) ⇒ `structInv_writeRules`, `residueEmpty_writeRules`, **`inv_writeRules`**
  (full I-series `Inv` on the residue-free fragment — W2's T2a `Inv` conjunct), and
  `quiescent_writeRules`, all by folding the W1 single-write lemmas over the closure.
- **`ReachedByRules`** (the W2 write-closure; `ReachedByDirect` = the no-rules special
  case where `rewriteClosure = [t]`) + **`reachedByRules_inv`** (Inv ∧ ResidueEmpty ∧
  Quiescent at every W2-reachable state, by induction over the write path).

**Read-routing DONE (same session, `GraphIndex/RulesCorrect.lean`, axiom-clean).**
The fragment predicate `UntaintedSchema S` (no `.inter`/`.excl` in any def) collapses
taint: `baseTaint_untainted` → `taintStep_nil_untainted` → (`iterate_nil_fixed`)
`taintedKeys_untainted` (`= []`) → `isDerived_untainted` (`= false` for every key) →
**`check_eq_probeNonDerived`** — on this fragment `GraphModel.check` reduces to the
≤4-probe reachability read, the same one W1's `graph_correct_*` glue against. So the
residue path is provably never taken, and the correspondence now reduces to a pure
reachability ↔ `sem` argument.

**What remains for `graph_correct_rules` (`check = sem` on the untainted fragment),
the deferred next increment — the reachability ↔ `sem` core:**
1. (routing ✓ above) + the store-validity analog (`StoreValid`: raw writes name
   relations with a Direct arm). **Soundness groundwork ✓** —
   `reachedByRules_edge_sound` (`GraphIndex/RulesCorrect.lean`, axiom-clean): every edge
   of a `ReachedByRules` state materializes some `u ∈ rewriteClosure S t` for a stored
   `t` (the W2 analog of `reachedByDirect_edge_sound`, via `foldl_writeDirect_edges_sound`).
2. **The rewrite-closure ↔ `sem` correspondence** — the genuinely new content. The
   reduction that makes it tractable: `writeRules` materializes exactly the edges of the
   rewrite-closure `T*` of the store, so the goal factors as
   `probeNonDerived over T*-edges = sem over T`, and the existing W1 machinery already
   gives `reach ↔ NReaches ↔ TupleChain over T*`. The new lemma is **`TupleChain over
   T* ↔ sem over T`**: a rewrite-closure hop corresponds to `evalE`'s `computed`/`ttu`/
   `union` recursion. Soundness: a `T*` edge from a Computed/TTU rewrite is absorbed by
   the matching `evalE` case (computed = `rec otype oname R'`; ttu = the
   `ttuLeaf` stored-parent loop with the userset subject `s#tr`; union = the OR). NB the
   TTU rewrite produces a *userset* subject, so this reuses the userset-flow lift from
   DirectCorrect/UsStar. Completeness: `sem`'s computed/ttu/union recursion is witnessed
   by a rewrite-closure chain. Fuel: the T0a-stability sidestep (`sem_fuel_stable`) from
   W1c should transfer (the graph-hop/`sem`-fuel mismatch recurs — a rewrite chain of
   length `k` gives `semAux` at some fuel, lifted to `sem` by stability).
3. **Top-level glue** `graph_correct_rules` — route to `probeNonDerived` (point 1), glue
   the probe-1 disjunction via `reach ↔ NReaches` to the two directions. Then widen
   T3/T6 (`Equiv.lean`) as free corollaries.
NB W2's fragment is untainted rule routing ONLY; `and`/`but not` (residues, the
processor cascade) is **W3**, and the *combined* generality (wildcards + rules together)
lands at **W4**. Attack-first the correspondence's userset/TTU-flow lift before proving.

## Session 2026-07-10 (W1c FULLY CLOSED — `graph_correct_usStar`, full `check = sem`)

Resuming W1c from "both semantic cores closed; resume → the assembly + closure"
(the three sharply-isolated points below). Delivered all three as one green
increment plus a soundness sub-increment: **`graph_correct_usStar`**
(`GraphIndex/UsStarClosure.lean`, sorry-free, axiom-clean `[propext,
Classical.choice, Quot.sound]`) — the first *userset-wildcard* fragment where the
graph read provably equals `sem`. `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit, all standard-axioms-only). This closes ROADMAP stage **W1c
end-to-end** (soundness + completeness), matching W1a/W1b.

**Point 1 — fuel-bounded soundness assembly, SIDESTEPPED via T0a stability (the
headline).** The ROADMAP flagged that the W1b plain-node fuel count "NEEDS ADAPTING"
for W1c — and it genuinely does *not* transfer: a userset-star grant's source is a
`w_any` node (not plain), an in-bridge consumes a `w_any` as a target, and the
`UsStarReach` chain over-counts (an in-bridge is a separate hop that the `sem`
derivation *absorbs* into the following userset-star grant). A tight `m ≤ fuelBound`
count would need `#w_any ≤ |keys|` accounting (`w_any` nodes are keyed by
`(type,relation)`). **Avoided entirely:** `semAux_of_usStarReach` gives a membership
at fuel = the chain length `m` for *some* `m`; `sem_fuel_stable` (T0a) makes `sem`
stable above `fuelBound`, so `sem = semAux (max m fuelBound) = true` by `semAux_mono`
(up to the max) then stability (down to `sem`) — **no bound on `m` needed**.
Delivered: `storeDeclared_of_storeValid` (the T0a `hDecl` hypothesis, from
`restrictionMatches`), `sem_of_usStarReach`, and `sem_of_usStar_probe` (the forward
direction from a covering probe source, via `usStarReach_of_trail`). This trick is
reusable for W1's later stages where the graph-hop/`sem`-fuel mismatch recurs.

**Point 2 — the admitted bridge-complete closure discharging `hEC` + `hib`.**
`UsStarReachedAdmitted` (W1c analog of `WildReachedAdmitted`): each write's grant
edge (`hadmGrant`) and — for each concrete bridged-in endpoint — its `c → w_any`
in-bridge (`hadmInA`/`hadmInB`, guarded by `bridgedInConcrete`) passed
cycle-rejection (the "no in-bridge cycle" fragment).
- `hEC` = `usStarReachedAdmitted_edge_complete` (mirror of the W1b edge-complete).
- **`hib` = `usStarReachedAdmitted_hib`**, the contentful part. Discharged via the
  **liveness invariant `usStarReachedAdmitted_inbridge_live`**: in the admitted
  closure, every *live* concrete bridged-in node has its in-bridge — because a
  bridged-in node is plain, so it enters `nodes` only as a write endpoint
  (`writeUsStar_new_plain_node`: the bridge machinery only adds non-plain `w_all` /
  `w_any` nodes), and that write ran `ensureInBridges` on it, materializing the
  bridge under the admission guard. `hib`'s in-edge guard (Point 3) → node live
  (endpoint-closure) → invariant → bridge. Shape membership via
  `isSWU_of_storeValid` (a stored userset-star grant's `(T,P)` is a declared
  subject-wildcard-userset shape — the matched `(T,P,true)` restriction occurs in the
  schema).

**Point 3 — `reach_of_semAux_us`'s `hib` REFORMULATED (a correctness fix, not just
plumbing).** The prior *unconditional* `hib` ("every `instances` witness of a
userset-star grant has its in-bridge") is **FALSE and undischargeable**: a name
`inst ∈ instances T q T` can occur in the store only with a predicate `≠ P`, so the
node `⟨T,inst,P⟩` is never a tuple endpoint and never bridged. But `sem` only *flows
through* such an `inst` when `rec T inst P = true`, which forces a stored `P`-grant
on `⟨T,inst⟩` — hence an **in-edge** into `subjNode ⟨T,inst,P⟩`. So `hib` is now
**guarded by that in-edge** (`∃ x, (x, subjNode ⟨T,inst,P⟩) ∈ edges`), which the
completeness proof produces from the recursion's reachability (`nreaches_last_edge`)
and the store-built graph provides (a reachable declared-SWU node was touched as an
endpoint). Re-proved `reach_of_semAux_us` green with the guarded hypothesis. Without
this fix the completeness core, though "proved," was stated over an unsatisfiable
hypothesis — the attack-first "store-bridges ↔ `instances` agree" finding was right
about the *live* names but the earlier `hib` over-claimed on all `instances`.

**Top-level glue** (`graph_correct_usStar`, mirror of `graph_correct_bareStar`):
routes to `probeNonDerived`; probes 3,4 dead (`usStarReached_edge_target_ne_wAll` —
no edge targets a `w_all`, objects star-free); probe 1 ∨ probe 2, with **probe 2
LIVE** for a userset query subject (its `wAny(s.shape)` sees userset-star direct
grants) and dead for a *bare* query subject (`usStarReached_edge_source_char` — a
bare-`w_any` node is never a source). Forward = `sem_of_usStar_probe`; backward =
`reach_of_semAux_us` with `hEC`/`hib` discharged.

**T3/T6 widened for free** (`Equiv.lean`): `backend_equivalence_usStar` /
`exclusion_effective_usStar` / `no_ghost_grant_usStar` (T1 ∘ `graph_correct_usStar`),
axiom-clean; audit +10 lines (7 W1c assembly + 3 corollaries).

**Next: ROADMAP W2** (rule routing — `computed` / `union` of untainted operands /
TTU defs route onto rule-derived families). W1 (wildcard bridges) is now complete
across all three sub-stages (W1a bare star / W1b object wildcards / W1c userset
stars), each with `graph_correct_*` closing `check = sem`. Note the W1c fragment
isolates userset stars (objects star-free, no object wildcards in the store); W1's
*combined* generality (userset + object wildcards together) lands with the full-scope
restatement in W4. Attack-first the W2 rule-edge soundness before proving.

## Session 2026-07-10 (W1c BOTH SEMANTIC CORES CLOSED — completeness `reach_of_semAux_us` + soundness `UsStarReach`)

Resuming W1c from "write model + edge characterization done; the read-correspondence
core is the genuinely hard remaining work." Delivered **both semantic halves** of the
W1c read correspondence as two green+pushed axiom-clean increments — mirroring how W1b
landed its two cores (`ObjStarCorrect.lean`) before the assembly (`ObjStarClosure.lean`).
`verify.sh` green throughout (build + 0 sorries + 60 conformance + audit). Sorry count
held at 0. All new theorems standard-axioms-only.

**Increment 1 — the completeness core (`reach_of_semAux_us`, `sem ⇒ probe 1 ∨ probe 2`).**
Fuses W1a's probe-2 disjunction with W1b's bridge threading — here the `concrete →
w_any` **in-bridge**. Stated over the two operational facts it consumes: edge-completeness
`hEC` and **in-bridge completeness** `hib` (every `instances` witness of a userset-star
grant has its `c → w_any` bridge), deferring the discharging closure exactly as
`reach_of_semAux_os` deferred to `hEC`/`hbr`. Supporting:
- `instances_ne_star` — no `∃`-witness population name is the STAR sentinel (foldr
  peeling, mirrors `instances_subset_storedNames`).
- `directLeaf_elim_us` — userset-star-aware leaf elim (exact | userset-star direct match
  of the query's shape | flow-through); the bare-star disjunct dies by `UsStarStore`.
- `mog_elim_us` — flow-through elim admitting the `instances`-branch (plain userset |
  userset-star + instance witness) that `mog_elim`/`_os` could not fire.
- Cases: exact → probe 1; userset-star grant of `s`'s shape → probe 2 (`wAny(s.shape) →
  objNode`, unreachable via probe 1 for a query-only ghost — the attack-first
  endpoint-exclusion finding); plain flow → extend recursion by the grant edge;
  userset-star flow → thread the concrete instance's in-bridge (`hib`) then the grant.

**Increment 2 — the soundness core (`UsStarReach` chain + both directions).**
- **KEY SIMPLIFYING FINDING: an in-bridge hop needs NO instance witness for soundness.**
  A concrete `c` reaching a userset-star grant through its `c → w_any` in-bridge always
  corresponds to `c` matching that grant **directly** in `sem` (a pure shape-match, `c`
  has the grant's shape by construction — unconditionally valid, ghost or not). So
  `UsStarReach`'s `inbridge` constructor carries no `instances` field and
  `usStarReach_of_trail` needs **no** in-bridge-soundness hypothesis. The instance
  condition is a *completeness*-only concern (`hib`), where `sem`'s flow-through demands
  a genuine `instances` witness.
- The lift is the crux and genuinely NEW vs W1b: `semAux_lift_os` **cannot** absorb a
  userset-star grant (its `directLeaf_elim_os` has no userset-star disjunct). New
  `semAux_lift_us`: an intermediate userset `s'` matching a userset-star grant directly
  is absorbed via the **outer subject `s`'s `instances`-branch flow-through** (witness
  `s'.name`) — needing `s'.name ∈ instances`, always dischargeable because every chain
  intermediate is a tuple object (`objectName_mem_instances`). Where the instances
  condition genuinely lives in soundness: not in the chain, but in this lift's hypothesis.
- Supporting: `mog_intro_star`, `directLeaf_grant_usStar` / `semAux_one_of_usStarGrant`
  (userset-star direct-match intros), `objectName_mem_instances`, `semAux_one_of_tuple_us`,
  `UsCovers` (probe-1 ∨ probe-2 chain start, userset analog of W1a's `Covers`),
  `semAux_one_covers_us`.
- `UsStarReach T n u v` (base | hop | inbridge, no `q`/`instances`); `semAux_of_usStarReach`
  (chain ⇒ `sem` at fuel `n`: base/hop via the lift, inbridge = a direct shape-match on
  `c` + `semAux_mono` bump); `usStarReach_of_trail` (trail ⇒ chain: edge classification;
  out-bridges dead from a plain/`wAny` source, `w_any` targets excluded because the
  concrete query object node is plain). Existence only — no fuel bound threaded yet.
- Strengthened `usStarReached_grant_or_bridge` (+ `writeUsStar_edges_mem` /
  `bridgeLayers_edges_mem`) to expose `pred ≠ BARE` on in-bridge sources (needed for the
  `inbridge` constructor's `hcp`).

**What remains for `graph_correct_usStar` (full `check = sem`), sharply isolated:**
1. **Fuel-bounded soundness assembly** — `usStarReach_of_trail` gives existence `∃ m,
   UsStarReach m …`; the top-level needs `m ≤ fuelBound`. **The `isPlain`-source count
   argument (W1b's `grantReach_of_trail` strengthening) needs ADAPTING**: a userset-star
   grant's source is a `w_any` node, not plain, and an in-bridge consumes a `w_any` as a
   target — so "every hop source is plain" (W1b) is FALSE here. Likely bound: count
   distinct plain trail vertices + `w_any` vertices, or bound `m` by trail length
   directly (each graph edge = ≤ 1 chain hop, and trail length ≤ nodes.length after
   compression). Re-derive the tight `fuelBound` fit.
2. **The admitted, bridge-complete write-closure** discharging `reach_of_semAux_us`'s
   `hEC` + `hib` — the W1c analog of `ObjStarClosure.lean`'s `WildReachedAdmitted`. `hib`
   (in-bridge completeness) is the contentful part: every store userset-star grant `g`
   and every `inst ∈ instances T q g.subject.type` has its materialized `subjNode
   ⟨T,inst,P⟩ → w_any(T,P)` bridge. This is exactly the attack-first "store-bridges ↔
   `instances` agree by construction" finding, now to be proved operationally (a
   concrete of a bridged-in shape gets its in-bridge when touched as a tuple endpoint —
   `writeUsStar`'s `ensureInBridges`).
3. **Top-level `check = sem` glue** — route to `probeNonDerived`, kill probes 3,4 (objects
   star-free ⇒ no `w_all` target), glue probe 1 ∨ probe 2 via `reach ↔ NReaches` to
   completeness (backward) and the fuel-bounded chain (forward). Probe 2 is LIVE here
   (unlike W1b): a userset query subject's `wAny(s.shape)` sees userset-star direct
   grants. Mirror of `graph_correct_bareStar` (which also had probe 2 live).

## Session 2026-07-10 (W1c STARTED — userset stars `[group:*#member]`; attack-first + in-bridge write model + edge characterization)

Resuming from W1b fully closed → **ROADMAP stage W1c** (userset-wildcard *subject*
grants `[group:*#member]`, `concrete → w_any` **in-bridges** — the genuinely hard
sub-stage, spec §1.1). Two green+pushed axiom-clean increments; `verify.sh` green
throughout (build + 0 sorries + 60 conformance + audit). Sorry count held at 0.

**Attack-first HEADLINE (machine-checked, no `native_decide`): the correspondence
holds; `instances` ↔ store-bridges agree by construction.** Verified `GraphModel.check
= sem` on 12 userset-star scenarios in a scratch module (deleted after), incl. the
sharp **endpoint-exclusion** cases the ROADMAP flagged. The finding: a group name is
in `sem`'s `instances T q group` iff it appears in a **tuple** (not merely as a query
endpoint), which is **exactly** when the store-built graph has that concrete's
in-bridge — so the store-derived bridge set and `instances` coincide; a query-only
name (`ghost`) is in neither. No refutation. The one *apparent* divergence was an
**admission-invalid tuple** (a concrete userset `group:eng#member` grant against a
`[group:*#member]`-only restriction: `restrictionMatches` fails since the restriction
requires `wildcard=true`), re-confirming StoreValid is load-bearing exactly as in the
direct/objStar fragments. Unlike W1b (bridges proven MANDATORY), W1c had no
statement-level surprise — the design was confirmed as-is.

**Increment 1 — the faithful in-bridge write model (`GraphIndex/UsStarWrite.lean`,
sorry-free, axiom-clean):**
- `Schema.isSubjectWildcardUserset` — the `bridged_in_shapes` predicate
  (`zanzibar_utils_v1.py:264-270,784-789`): `p ≠ BARE` and some `[t:*#p]` restriction
  `(t,p,true)` occurs in the schema. (TTU-through-shape extension `:795-803` out of
  scope for this TTU-free fragment.)
- `GraphState.bridgedInConcrete` + `ensureInBridges` — lazily create
  `w_any(c.type,c.pred)` + the guarded `c → w_any` in-bridge (cycle-rejection,
  `wildcard.py:120-129`).
- `GraphState.writeUsStar` — faithful `add_tuple`: endpoint nodes, out-bridges (W1b,
  inert here) then in-bridges (bridge-before-grant), then the cycle-rejected grant; a
  rejected grant rolls back the whole write.
- `nodeEnc_wAnyNode` (needs NO axioms); `ensureInBridges_mono`/`_schema`.
- `structInv_ensureInBridges` — an in-bridge preserves `StructInv` (w_any
  encoding-valid; bridge edge cycle-admitted).
- `structInv_writeUsStar` — the whole write preserves `StructInv` (acyclicity through
  **both** bridge families + the grant).
- `UsStarReached` (the W1c write-closure) + `usStarReached_structInv`/`_schema` —
  `StructInv` at every W1c-reachable state.

**Increment 2 — the edge characterization (`GraphIndex/UsStarCorrect.lean`, sorry-free,
axiom-clean `[propext]`):** the structural fact the soundness chain will classify each
trail hop against. `UsStarStore` (fragment predicate: objects star-free, star subjects
non-bare); `bridgedInConcrete_elim`; `ensureInBridges_edges_mem`;
`bridgeLayers_edges_mem` (peels the 2 out + 2 in bridge layers of `writeUsStar`);
`writeUsStar_edges_mem`; **`usStarReached_grant_or_bridge`** — every edge of a
`UsStarReached` state is a stored **grant**, a `w_all → concrete` **out-bridge**, or a
`concrete → w_any` **in-bridge**, by induction over the write path.

**What remains for `graph_correct_usStar` (`check = sem`), sharply isolated (the
genuinely hard core — the ROADMAP-flagged W1c difficulty):**
1. **The in-bridge-absorbing chain** (analog of W1b's `GrantReach`). The new
   absorption: a `concrete c → w_any(shape)` in-bridge **followed by** a userset-star
   grant `w_any(shape) → objNode` is one generalized hop — the graph counterpart of
   `sem`'s `memberOfGranted` `instances`-branch (`Semantics.lean:50-56`: a userset-star
   grant `g=(T,*,P)` expands over `instances T q T`, checking `rec T inst P` for each
   `inst`). The soundness key: `inst = c.name` must be in `instances` (⇔ c appears in a
   tuple ⇔ c has its in-bridge — the attack-first finding). NB the userset `w_any` node
   here is BOTH an edge target (in-bridges) AND source (the grant) — unlike W1b's
   `w_all` (target only) and W1a's bare `w_any` (source only).
2. **The `instances`-branch of `memberOfGranted`** — the subject-side leaf lemmas
   (`mog_elim`/`directLeaf_elim`) must now admit the star-userset grant disjunct
   (currently killed by star-free-subject in W1b's `_os` versions). The `instances`
   ∃-witness expansion is the new content vs W1a/W1b.
3. **Probe 4** (`w_any → w_all`) — for a star *userset* query subject. Dead on W1b's
   object side; live here.
4. **Bridge-completeness** (an admitted closure, W1b-analog): every store concrete of a
   bridged-in shape has its `c → w_any` bridge — `instances`-coverage. The endpoint
   exclusion is what makes this match `instances` (store-derived, excludes query-only
   names).
5. **Fuel-bounded soundness assembly** — as W1b (`m ≤ 2|T|+1`); the in-bridge hops
   consume `w_any` nodes (not plain sources), so the plain-node accounting should
   transfer, but a `w_any` node is now also a source (the grant), so re-check the
   `isPlain`-source argument (`grantReach_of_trail`'s "every hop source is plain" no
   longer holds — a userset-star grant's source is `w_any`).

## Session 2026-07-10 (W1b FULLY CLOSED — `graph_correct_objStar`, full `check = sem`)

Resuming W1b from "both semantic cores done + completeness operationally closed;
what remains is the SOUNDNESS side + top-level assembly." Delivered the
**fuel-bounded soundness assembly** and the **top-level `check = sem` glue**, closing
**W1b end-to-end**: `graph_correct_objStar` (`GraphIndex/ObjStarClosure.lean`,
sorry-free, axiom-clean `[propext, Classical.choice, Quot.sound]`). `verify.sh` green
throughout (build + 0 sorries + 60 conformance + audit). Sorry count held at 0. This
is the first *object-wildcard* fragment where the graph read provably equals `sem`.

**The fuel bound was the genuine remaining piece** (ROADMAP-flagged multi-hour). The
soundness chain `semAux_of_grantReach` gives fuel = the `GrantReach` length `m`, and
`m ≤ fuelBound` needs the tight `m ≤ 2|T|+1` — the crude `m ≤ nodes.length` is too
weak because `writeWild` adds up to 4 nodes/tuple (2 endpoints + 2 `w_all`), so
`nodes.length ≤ 4|T|` overshoots `fuelBound = |keys|(2|T|+4)` at `|keys|=1`. The key
observation formalized: **every `GrantReach` hop's *source* is a `plain` node** —
`w_all` nodes are consumed mid-hop by a grant+bridge pair, never a hop source — so the
chain length is bounded by the count of *distinct plain* trail vertices, of which
there are ≤ `2|T|`.

**Delivered:**
- **`NodeKey.isPlain`** + **`trail_compress_nodup`** + **`nodup_countP_le`**
  (`GraphIndex/State.lean`) — a nodup-preserving trail compression, and the bound
  `l.Nodup → (∀ x∈l, x∈N) → l.countP p ≤ N.countP p` (distinct predicate-hits inject
  into `N.filter p`).
- **`grantReach_of_trail` strengthened** (`GraphIndex/ObjStarCorrect.lean`) — now also
  yields `m ≤ (subjNode s :: l).countP NodeKey.isPlain`. Each hop accounts for exactly
  one plain vertex (its source); the `w_all` node of a bridge hop contributes 0. Base
  hops account for the leading `subjNode s`. Threaded through the existing peeling
  induction with no change to its structure. `isPlain_subjNode`/`isPlain_wAllNode`
  helpers.
- **Plain-node accounting** (`GraphIndex/ObjStarClosure.lean`):
  `ensureBridges_plainCount` (bridges only ever add `w_all` nodes ⇒ plain count
  unchanged), `writeWild_plainCount_le` (≤ 2 plain nodes/write), and
  `wildReachedAdmitted_plainNodes` (`plain-node count ≤ 2|T|`).
- **Dead `w_any` probes** — `wildReached_edge_source_ne_wAny` (an edge source is a
  star-free `subjNode` grant source or a `w_all` bridge source, never `w_any`) +
  `nreaches_first_edge`, killing read probes 2 and 4.
- **`grantReach_mem`** — a `GrantReach` witnesses a stored tuple (for
  `lookup_keys_nonempty` in the fuel arithmetic).
- **`graph_correct_objStar`** — `check σ q = sem S T q` on the W1b fragment
  (object-star, admission-valid, object-wildcard-valid store; star-free query),
  end-to-end. Forward: probe-1/probe-3 hit → nodup trail → `GrantReach` →
  `semAux_of_grantReach` at fuel `m ≤ 2|T|+1 ≤ fuelBound` → `semAux_mono`. Backward:
  `graph_complete_objStar` + `reach_complete`. Probes 2,4 dead; audit updated
  (5 new `#print axioms` lines).

**T3/T6 widened for free (`Equiv.lean`):** since the equivalence + security
corollaries are one-line `rw`s through `graph_correct_*`, added
`backend_equivalence_objStar` / `exclusion_effective_objStar` /
`no_ghost_grant_objStar` — T3/T6a/T6b now hold on object-wildcard stores too
(T1 ∘ `graph_correct_objStar`). Axiom-clean; audit +3 lines.

**Next: ROADMAP W1c** (userset stars `[group:*#member]` — in-bridges + `instances` +
probe 4; the genuinely hard sub-stage). Attack-first first.

## Session 2026-07-10 (W1b COMPLETENESS CLOSED operationally — `graph_complete_objStar`)

Resuming W1b from "both semantic cores done, discharge the operational hypotheses."
Delivered the **admitted, bridge-complete write-closure** and used it to discharge
**both** operational hypotheses (`hEC`, `hbr`) that `reach_of_semAux_os`
(completeness core) was stated over — so the W1b completeness direction is now a
real, operationally-closed theorem. New file `GraphIndex/ObjStarClosure.lean`,
sorry-free, all six audited theorems axiom-clean (subset of the three standard
axioms). `verify.sh` green throughout (build + 0 sorries + 60 conformance + audit).
Sorry count held at 0.

**Delivered (`GraphIndex/ObjStarClosure.lean`):**
- `writeWildPre` (the fully-bridged pre-grant state) + `writeWild_eq_ite` (the write
  as an `ite` over it, definitional) — lets the closure state grant admission over
  the bridged state and lets edge lemmas skip the `let` chain.
- Edge-monotonicity through the bridge machinery (`ensureBridges_edges_mono`,
  `writeWildPre_edges_mono`, `writeWild_edges_mono`), the grant-edge and
  bridge-edge creation lemmas (`writeWild_grant_edge`, `ensureBridges_creates_bridge`).
- **`WildReachedAdmitted`** — the composed-system closure (W1b analog of
  `ReachedByAdmitted`): each write's grant edge (`hadmGrant`) AND its *subject*
  endpoint bridge (`hadmSub`) passed cycle-rejection. Carrying `hadmSub` is exactly
  the "no wildcard-own-shape cycle on subjects" fragment on which bridge-completeness
  holds; the object-endpoint bridge is handled internally by `ensureBridges` (both
  outcomes are valid states), so it is not required. Embeds into `WildReached`
  (`wildReached_of_admitted`); schema fixed (`wildReachedAdmitted_schema`).
- **`wildReachedAdmitted_edge_complete`** (`hEC`) — every stored grant's edge is
  present (mirror of `admitted_edge_complete`; new edges added, old edges monotone).
- **`wall_reach_isObjectWildcard`** (Lemma A) — a reachable `w_all(T,R)` node forces
  `S.isObjectWildcard T R`: its only in-edges are grant edges (bridge targets are
  plain, `nreaches_last_edge` + the grant-or-bridge characterization), from
  object-wildcard grants, which `ObjStarValid` puts on a declared object-wildcard
  shape.
- **`wildReachedAdmitted_bridge_complete`** (bridge-completeness) — every stored
  grant whose *subject* shape is a declared object-wildcard has its materialized
  `w_all → concrete` bridge (new writes create it via `writeWild_subjBridge`; old
  bridges persist). This is the invariant that, with Lemma A, discharges `hbr`.
- **`wildReachedAdmitted_hbr`** — the `hbr` discharge: reachability of `g.subject`'s
  `w_all` node forces the object-wildcard shape (Lemma A), and bridge-completeness
  then supplies the bridge.
- **`graph_complete_objStar`** — the operationally-closed W1b completeness theorem:
  on `WildReachedAdmitted` over an object-star, admission-valid, object-wildcard-valid
  store, a `sem` membership at `fuelBound` is reachability to probe 1 (concrete
  object node) ∨ probe 3 (`w_all` node). `reach_of_semAux_os`'s two operational
  hypotheses are gone.

**What remains for the full `graph_correct_objStar` (`check = sem`), sharply
isolated — only the SOUNDNESS side + assembly:**
1. **Fuel-bounded soundness assembly.** `semAux_of_grantReach` (done) gives fuel =
   the `GrantReach` length `m`; the top-level theorem needs `m ≤ fuelBound`. The
   crude `m ≤ nodes.length + 1` is too weak (duplicate `w_all` nodes inflate
   `nodes.length` past `fuelBound` when `|keys| = 1`). The tight bound is `m ≤ 2|T|`
   (distinct plain source nodes — each grant hop consumes a distinct plain source in
   a compressed/nodup trail; `w_all` nodes are not plain). Formalizing that
   distinctness bound (strengthen `grantReach_of_trail` to bound `m` by the plain
   vertex count) is the remaining arithmetic. The *completeness* side needs no fuel
   bound (this session).
2. **Top-level `check = sem` assembly** — route the read to `probeNonDerived`
   (pure-direct = untainted), kill probe 2 (star-free subjects) and probe 4, and
   glue probe 1 ∨ probe 3 via `reach ↔ NReaches` to the two directions
   (`graph_complete_objStar` backward; the fuel-bounded `GrantReach` chain forward).
   Mirror of `graph_correct_direct` / `graph_correct_bareStar`.

## Overnight autonomous run (2026-07-09 → 07-10)

User granted full autonomy ("keep going til you're done, I'll review tomorrow in one
go"). Plan, in priority order, committing each GREEN increment and documenting every
decision here:
1. Harden the spec: randomized conformance fuzzing (sem vs oracle vs set engine over
   random tuple subsets + grids). Safe (pure Python); catches spec bugs like the
   fuelBound one. Any unresolved divergence → adjudication log, don't block.
2. Concrete set-engine `expand` model (remove `opaque SetEngineModel.check`) + prove
   T1 with the algebra lemmas. Main proof effort.
3. Attempt T0a pigeonhole (`semAux_fuel_stable_step`) and T0b Kahn lemmas.
4. Attempt T4: define `pathCount` concretely, prove the first-edge recurrence + the
   counting theorem.
5. Shrink the opaque surface: concrete graph state types (even if T2/T5 stay sorry).
6. Final documentation + review summary.
Discipline: never commit a broken build; if a proof stalls past reasonable effort,
leave a documented `sorry` and move on. Update this file continuously.

## Overnight run RESULT (2026-07-10, end of session)

Delivered, all green + pushed (see REVIEW.md for the digest):
- **Found + fixed a real spec bug** (`fuelBound` additive→multiplicative), confirmed
  empirically, locked with the `deep_grid` regression. This was the headline outcome.
- **Conformance: 15 schemas, 60 tests green** (handwritten + randomized), three
  evaluators (`sem` / oracle / real set engine) agree everywhere. Added adversarial
  boolean corners (taint-over-boolean, nested boolean, double exclusion).
- **Proved (axiom-clean):** full MemberSet algebra + membership/constructor lemmas;
  `restrictionMatches_type` / T6c (real, not placeholder); `sem_fuel_stable` (T0a)
  reduced to one pigeonhole lemma. Axiom audit shows no custom axioms.
- **Tooling:** `zcli` CLI, `verify.sh` green gate, `Audit.lean` axiom check.
- **Handled a Gemini review:** adopted the valid fuelBound catch + WellDef
  decomposition (corrected); rejected the `phat_def` axiom (C4 cleanliness).

Remaining = the irreducible hard core (9 sorries): T1 (needs concrete expand model),
T2a/b + T5 (need concrete graph state machine), T4 counting (needs concrete pathCount
+ combinatorics), T0a pigeonhole core, T0b Kahn. All honestly deferred — NONE faked.
These want fresh context + the statement-review feedback; each is multi-hour.

**Next session resume:** see `formal/ROADMAP.md` (per-sorry plan, with corrections to
a Gemini roadmap). Phase 3 T1: the boolean STAR cases are done (`containsStar_*`); the
remaining nut is the INTENSIONAL `containsShape` distribution for concrete/ghost
subjects under a WF invariant — attempted this session, `simp; tauto` did NOT close
it (goal too large), so it's documented in ROADMAP with the intended route (a
`containsShape` normal-form lemma + per-atom split) rather than left as a `sorry`.
Gemini corrections logged: its set-engine model used `MemberSet String` (unsound —
name collisions across types; use `String × String`); its T0a pigeonhole is invalid
(our `semAux` has no visited-set); its T4 `phat_def` axiom rejected (C4 gate).

## Session 2026-07-10 (W1b SOUNDNESS + COMPLETENESS CORES — `GrantReach` + `reach_of_semAux_os`)

Resuming W1b (object wildcards `[T:*]`) from the write model (previous session).
Delivered **both semantic halves** of the read correspondence as self-contained
honest increments (two green+pushed commits), each stated over the operational
facts it consumes so the write-closure that discharges them can land next. New
file `GraphIndex/ObjStarCorrect.lean`, sorry-free, all six audited theorems
axiom-clean (`wildReached_grant_or_bridge` = `[propext]` only; the rest a subset
of the three standard axioms). `verify.sh` green throughout (build + 0 sorries +
60 conformance + audit). Sorry count held at 0.

**Completeness core (`reach_of_semAux_os`)** — the analog of W1a's
`reach_of_semAux_bs`, but the disjunction is on the **object** side (probe 1 =
concrete object node ∨ probe 3 = `w_all` node): a direct match on a concrete grant
hits probe 1, on a `T:*` grant hits probe 3; a flow-through prepends the
recursion's path, **through a bridge hop** when the recursion reached the userset
via its own `w_all` node. Stated over two operational facts (like the soundness
core is stated over the edge characterization): `hEC` (edge-completeness — every
stored grant's edge present) and `hbr` (a grant subject reachable via its `w_all`
node has its materialized `w_all → concrete` bridge). Needs **no fuel bound** (it
goes `sem ⇒ reach`, and `sem` is already at `fuelBound`). The write-closure that
discharges `hEC`/`hbr` (an admitted, bridge-complete closure) is the deferred
increment.

The soundness core (below) reads existing edges only, so it needs **neither
bridge-completeness nor the admitted-writes refinement**.

**The idea that tames the bridges.** A W1b graph path interleaves *grant* hops
(`subjNode s → objNode o R`, subjects star-free) and *bridge* hops
(`w_all(T,R) → concrete`, materialized by `writeWild`). The soundness argument
**absorbs each `grant-into-w_all` + `bridge-out` pair into a single generalized
grant against a *concrete* object**, keyed through `matchingObjects`: a `T:*`
grant is in `grantsOf` for *every* concrete object of type `T` (spec §3.4's
`subject → w_all(S) → concrete` composition, realized semantically). So a wildcard
grant plus its bridge is ONE hop in the abstracted chain; only the final target
may be a bare `w_all` node (the read's probe-3 endpoint).

**Delivered (`GraphIndex/ObjStarCorrect.lean`):**
- `ObjStarStore` (subjects star-free; objects may be `T:*`).
- **Edge characterization** `wildReached_grant_or_bridge` — every edge of a
  `WildReached` state is a stored grant (`subjNode t.subject → objNode t.object
  t.relation`, subject star-free) OR a `w_all → concrete` bridge
  (`a = wAllNode b.type b.pred`, `b` plain concrete). By induction over the
  bridge-materializing write path, via `writeWild_edges_mem` /
  `ensureBridges_edges_mem` (the edge effect of the nested bridge-before-grant
  write) and `bridgedConcrete_elim`.
- **`GrantReach`** — the bridge-absorbing generalized grant chain (3 constructors:
  `base` = one grant matching a concrete object via `matchingObjects`; `starBase`
  = a terminal grant landing on the `w_all` node; `hop` = a grant then continue
  from the concrete userset node). Every interior node is concrete; only the final
  target may be `w_all`.
- Object-star leaf lemmas (`mog_elim_os` / `directLeaf_elim_os` / `semAux_lift_os`
  / `semAux_one_of_grant`) — the subject-side leaf interface reused from
  DirectCorrect, needing only that grant *subjects* are star-free (object
  wildcards live on the object side; `semAux_one_of_grant` takes the
  `matchingObjects` match as a hypothesis so it covers both concrete and wildcard
  grants uniformly).
- **`semAux_of_grantReach`** (soundness's semantic half) — a `GrantReach` of
  length `n` from a star-free subject node to a node matching the concrete query
  object (`matchesObj`) is a `sem` membership at fuel `n`; base hops are
  self-grants keyed through `matchingObjects`, each `hop` lifts via
  `semAux_lift_os`. The bridge-aware analog of `semAux_of_chainN`.
- **`grantReach_of_trail`** (soundness's reachability half) — every graph trail
  from a star-free subject node is a `GrantReach`, by strong induction on trail
  length, peeling a grant (1 edge, `hop`/`base`/`starBase`) or a grant+bridge
  (2 edges, `hop`/`base`) at each step, classified by the edge characterization
  (a plain-source edge is a grant; a `w_all`-source edge is a bridge).

**What remains for `graph_correct_objStar`, sharply isolated (both semantic
halves are now DONE — what is left is the operational discharge + arithmetic):**
1. **The admitted, bridge-complete write-closure** that discharges `hEC`
   (edge-completeness — mirror of `admitted_edge_complete`) and `hbr` (the bridge
   hypothesis). This needs the **bridge-completeness invariant** (every live
   bridged-concrete node has its `w_all → c` bridge) maintained along a closure
   where grants AND the endpoint bridges are admitted (the "no wildcard-own-shape
   cycle" fragment), plus `ObjStarValid` (a `T:*` tuple is on a declared
   object-wildcard shape, so a reached `w_all` node's shape is bridged — turning a
   reached `w_all` into a live bridged-concrete whose bridge exists). The
   admission-threading through `writeWild`'s nested `ensureBridges` is the fiddly
   part; the semantic use-sites are already proved.
2. **Fuel-bounded top-level assembly** (soundness side only) —
   `semAux_of_grantReach` gives fuel = the `GrantReach` length `m`; the top-level
   theorem needs `m ≤ fuelBound`. The crude `m ≤ nodes.length + 1` is too weak here
   (the write can create up to `~4|T|` nodes incl. duplicate `w_all` nodes, and
   `fuelBound` with `|keys| = 1` is only `2|T|+4`). The tight bound is `m ≤
   (distinct plain source nodes) ≤ 2|T|` — each grant hop consumes a distinct plain
   source node in a compressed (nodup) trail. Formalizing that distinctness bound is
   the remaining arithmetic. (The *completeness* side needs no fuel bound.)
These are the next increment; both semantic cores (soundness `GrantReach ⇒ sem` +
`trail ⇒ GrantReach`, completeness `sem ⇒ probe 1 ∨ probe 3`) are done.

## Session 2026-07-10 (W1b STARTED — object wildcards; bridges proven MANDATORY + the bridge-materializing write model)

Resuming from W1a → **ROADMAP stage W1b** (object wildcards `[T:*]`, `w_all` +
out-bridges). `verify.sh` green throughout (build + 0 sorries + 60 conformance +
audit); all four new theorems axiom-clean (`nodeEnc_wAllNode` needs *no* axioms;
the rest `[propext, Classical.choice, Quot.sound]`). Sorry count held at 0.

**Attack-first HEADLINE (machine-checked): W1b is NOT bridge-free.** The natural
guess after W1a was symmetry: a bare-star *subject* node has no in-edges (pure
*leading* hop, probe 2 absorbs it, zero bridges), so maybe an object-wildcard
`w_all` node — never a `subjNode`, hence never an edge *source* — is a pure
*trailing* hop that probe 3 absorbs, also bridge-free. **Refuted against the real
`GraphModel.check`/`sem`** (`#eval`, no `native_decide`): an object-wildcard grant
that flows into a *further* userset hop needs the wildcard membership to reach the
**concrete** object node, which only a `w_all → concrete` bridge provides. The
refuting scenario: `viewer := [group#member, user]`, `editor := [doc#viewer]`,
`member := [user]`, object-wildcard `(doc, viewer)`; store `group:eng#member viewer
doc:*`, `doc:readme#viewer editor doc:readme`, `user:alice member group:eng`; query
`check(alice, editor, doc:readme)` — `sem = true` but the bridge-free `writeDirect`
state answers **false** (`alice → group:eng#member → w_all(doc,viewer)` dead-ends;
never reaches `⟨doc,readme,viewer,plain⟩` that `editor` routes through). Adding the
single bridge `w_all(doc,viewer) → ⟨doc,readme,viewer,plain⟩` restores `true`. This
realizes wildcard-spec §3.4's composition `subject → w_all(S) → concrete → …`. The
ROADMAP W1a note's optimistic "maybe W1b is also bridge-free" is now closed off.

**Cycle question RESOLVED from the Python** (`wildcard.py:222-259`): `add_tuple`
is **bridge-before-grant** (`_ensure_bridges(subject); _ensure_bridges(obj)` first,
creating `w_all` lazily + the out-bridge for each concrete endpoint of a bridged
shape, then the cycle-rejected grant edge). A wildcard tuple whose object
participates in its own shape would close a cycle through a bridge and is
**rejected at the grant edge** (`wildcard.py:250-256`) — so acyclicity (I2) is
preserved by cycle-rejection, not violated. A rejected write rolls back the whole
transaction (bridges included). Per-endpoint `ensureBridges` maintains
bridge-completeness with no separate `w_all`-arrival backfill: a concrete object
node exists only as an edge endpoint, so it self-bridges the first time it is
touched.

**Delivered — the faithful bridge-materializing write model
(`GraphIndex/ObjStarWrite.lean`, sorry-free, axiom-clean):**
- `GraphState.bridgedConcrete` (a concrete node whose object-shape `(type,pred)` is
  a declared `objectWildcards` shape — the nodes needing a `w_all → c` in-bridge).
- `GraphState.ensureBridges c` — create `w_all(c.type,c.pred)` lazily + the guarded
  bridge edge `w_all → c` (cycle-rejection via `admitEdge`, matching the core add).
- `GraphState.writeWild t` — bridge-before-grant: add endpoint nodes, ensure both
  endpoints' bridges, then the cycle-guarded grant edge; a rejected grant returns
  the original state (full rollback).
- `nodeEnc_wAllNode` (w_all nodes are encoding-valid); `ensureBridges_mono`
  (nodes grow); `ensureBridges_schema`/`writeWild_schema`; `writeWild_monoNodes`.
- **`structInv_ensureBridges`** — a bridge insertion preserves `StructInv` (the
  `w_all` node is encoding-valid; the bridge edge is cycle-admitted so
  `structInv_addEdge` applies; the concrete endpoint must already be live).
- **`structInv_writeWild`** — the whole write preserves `StructInv` (node encoding,
  endpoint closure, **acyclicity through both the bridges and the grant**).
- `WildReached` (the W1b operational write-closure, analog of `ReachedByDirect`) +
  **`wildReached_structInv`** — `StructInv` at every W1b-reachable state, by
  induction over the bridge-materializing write path.

**What remains for the W1b correspondence (`graph_correct_objStar`), sharply
isolated:** (1) **bridge-completeness invariant** maintained along `WildReached`
(every concrete of a bridged shape has its `w_all → c` bridge) — holds on the
fragment where no bridge cycle-rejects, i.e. no wildcard-own-shape cycle; (2) the
read = `sem` proof **with bridge hops**. The read reduces to probe 1 ∨ probe 3
(subjects star-free ⇒ probes 2,4 dead, mirror of W1a's dead 3,4). The new semantic
content: a graph path may now interleave **grant hops** (`subjNode s → objNode o R`)
and **bridge hops** (`w_all(T,R) → ⟨T,o,R,plain⟩`), and a grant-into-`w_all`
immediately followed by a bridge-out is EXACTLY the `matchingObjects on = [on, STAR]`
absorption in `sem` (a STAR-object grant is in `grantsOf` for concrete query object
`o`). The soundness/completeness inductions (analogs of `semAux_of_chainN_bs` /
`reach_of_semAux_bs`) must key the terminal/interior grant's object match through
`matchingObjects` rather than equality, and thread the bridge hop. This is the next
increment; the write model + structural invariant under it is now done.

## Session 2026-07-10 (W1a CLOSED — `graph_correct_bareStar`, bare star grants)

First scope-widening increment after the tree hit 0 sorries: **ROADMAP stage
W1a** — widen T2b (graph read = `sem`) to allow **bare star grants** `[user:*]`
(subject `(T,*,BARE)` tuples) in the store. Per wildcard-spec §3.2's bare-shape
rule this needs **ZERO materialized bridges**. `verify.sh` green (build + 0
sorries + 60 conformance + audit); `graph_correct_bareStar` axiom-clean
(`[propext, Classical.choice, Quot.sound]`). Sorry count held at 0.

**House move first (attack before prove):** machine-checked `check = sem` via
`#guard` on concrete bare-star scenarios in a scratch module — single grant,
wrong-type non-coverage, no-leak-to-usersets, 2-hop bare-star→userset
flow-through, concrete+star coexistence — **no refutation**, then deleted the
scratch and proved it.

**The modeling fact that makes W1a bridge-free** (spec §3.2): a bare-concrete
subject node `⟨T,u,BARE,plain⟩` has **no in-edges** (an in-edge target is an
`objNode`, whose predicate is a *relation* name, never `BARE`), and the star node
`wAny(T,BARE) = ⟨T,*,BARE,wAny⟩` has no in-edges either. So a bare-star grant is a
pure *leading* hop = the read-side `wAny` endpoint substitution of **probe 2**. No
interior hop exists to materialize. `subjNode` already sends `(T,*,BARE) ↦
wAny(T,BARE)`, so the write model is already correct — the work is entirely in the
correspondence.

**New file `GraphIndex/BareStarCorrect.lean` (sorry-free, axiom-clean):**
- `BareStarStore` (star subjects must be bare; objects star-free) / `NoUsersetStar`
  fragment predicates. `BareStarStore` is strictly weaker than `StarFreeStore`.
- `directLeaf_elim_bs` — **3-way** leaf elimination (exact `g.subject = s` | a
  bare-star grant covering a bare-concrete `s` | flow-through); the userset-star
  disjunct is killed by `NoUsersetStar`. The 2-way `directLeaf_elim` of
  DirectCorrect is *false* once bare-star grants can match a concrete subject.
  `mog_elim_nus` is the `NoUsersetStar` generalization of `mog_elim`.
- `semAux_lift_bs` — userset lifting, bare-star aware (the userset it lifts
  through is non-bare, so the extra bare-star match is vacuous).
- `Covers s u := u = subjNode s ∨ (s.predicate = BARE ∧ u = wAnyNode s.shape)` +
  `semAux_one_covers` + **`semAux_of_chainN_bs`** (soundness): generalizes the
  chain base from "the first tuple's subject *is* the query subject" to "*covers*
  it" — a `[T:*]` grant covers every bare-concrete subject of type `T`
  (`semAux_one_of_bareStar`, a pure type-match, `directLeaf`'s second bare-conc
  disjunct). Interior hops stay plain (bare-star can only be the *first* tuple of a
  chain, since after it every node is a plain `objNode`).
- **`reach_of_semAux_bs`** (completeness): `sem` ⟹ reachability from `subjNode s`
  **OR** from `wAny(s.shape)` — the probe-1 ∨ probe-2 disjunction. A bare-star
  direct match reaches from the star node, not the plain subject node; exact match
  and flow-through keep `s` fixed and preserve whichever disjunct the recursion
  produced.
- `admitted_edge_source_char` — every edge source is plain or a bare-`wAny` node
  (`pred = BARE`); a **userset**-`wAny` node is *never* an edge source (would need a
  userset-star tuple, forbidden by `BareStarStore`), so probe 2 is provably dead
  for a userset query subject.
- **`graph_correct_bareStar`** — `check = sem` on the widened fragment, end-to-end:
  probes 3–4 dead (star-free objects ⇒ no `wAll` target), probe 1 (plain) + probe 2
  (`wAny`-bare) live via `Covers`/`semAux_of_chainN_bs` (fwd) and
  `reach_of_semAux_bs` (bwd); probe 2 dead for userset subjects.

Reused unchanged from DirectCorrect: all pureDirect/lookup/node-algebra/grant/
matchingObjects/`TupleChainN`/`chainN_of_trail`/`admitted_*`/`ReachedByAdmitted`/
`directLeaf_grant_self`/`directLeaf_of_mog`/`mog_intro`/`semAux_mono` lemmas.
`graph_correct_direct` (StarFreeStore) is left intact — `BareStarStore` is the
weaker predicate; a future cleanup could make the star-free theorem a corollary,
but it is not needed. Audit updated (6 new `#print axioms` lines).

**Next: ROADMAP W1b** (object wildcards `wAll` + out-bridges) — the first stage
that *does* need bridge machinery. Attack first (a `[T:*]`-object grant vs probe 3).

## Session 2026-07-10 (T0a CLOSED — sorry count 0)

Same session as the falseness finding below: after restating over
`StoreDeclared`, the corrected theorem was **fully proved** — the last tracked
`sorry` is discharged, axiom-clean (`[propext, Classical.choice, Quot.sound]`,
audited). `verify.sh` green (build + 60 conformance + audit; **sorries = 0**).

**The proof architecture (4 green commits, each layer reusable):**

1. **Confinement (`Spec/Confine.lean`)** — `evalE_congr`/`step_congr`: two `rec`s
   agreeing on the consulted atom space (`exprRefs` keys × own-name ∪
   `storedNames`) evaluate identically. `directLeaf`'s certificate comes from
   `grantsOf`'s restriction filter (unconditional); `ttuLeaf`'s is exactly
   `StoreDeclared`. Undeclared keys are constantly `false` (`semAux_undeclared`).
2. **Untainted phase (`Spec/Stabilize.lean`)** —
   - `chain_stabilizes`: generic monotone + deterministic + `N`-bounded `Finset`
     chains from `∅` are stable from `N` on (used twice).
   - `untainted_closed`: `taintedKeys` is a genuine `taintStep` fixpoint (via the
     chain lemma on the taint iteration!), so untainted declared keys are
     boolean-free and reference only untainted keys.
   - `semAux_mono_untainted`: relative fuel-monotonicity at untainted relevant
     atoms — proved by **masking** `rec` outside the consulted space
     (`evalE_congr` says evaluation can't tell) and reusing the *global*
     `evalE_mono`; no second leaf induction. This trick halved the file.
   - `untainted_stable`: the true-set on `atomsU = untaintedKeys × relevantNames`
     grows monotonically, is deterministic (`step_congr`), hence stable from
     `N = |atomsU|` on.
3. **Kahn interface (`Spec/WellDef.lean`)** — `kahn_topo_strict` (dep edges point
   to STRICTLY earlier layers; a within-layer edge contradicts readiness),
   `stratify_covers` / `stratify_layers_tainted` (layers = exactly the tainted
   keys), `stratify_length`.
4. **Assembly (`Spec/WellDef.lean`)** — `layer_stable` (strong induction on the
   layer index: a layer-`i` key consults only undeclared / untainted / strictly
   lower layers, so it stabilizes at `N + 1 + i`), `all_stable` (every relevant
   atom stable from `N + 1 + |L|`), and the arithmetic
   `N + 1 + |L| ≤ K(2|T|+1) + 1 + K ≤ K(2|T|+4) = fuelBound` (needs `K ≥ 1`;
   `K = 0` is the everything-undeclared case, trivially stable).

**Where each hypothesis is load-bearing:** `hDecl` in `step_congr`'s ttu case
(without it the consulted space leaves `exprRefs` — the counterexample below);
`hStrat` in coverage + strict topology (without it a tainted key has no layer /
no strictly-decreasing rank).

**Phase-6 items pulled forward (same session):** `verify.sh` gates [2] and [4]
are now HARD — sorry count must be 0, and every audited theorem must show only
`propext`/`Classical.choice`/`Quot.sound` (any `sorryAx`, `ofReduceBool`, or
custom axiom fails the gate; validated end-to-end green). Also: ROADMAP W1 got
a grounded sub-staging design (W1a bare star grants = ZERO bridges via the
wildcard-spec §3.2 bare-shape rule → W1b object wildcards → W1c userset stars +
`instances`), each with the matching `sem` branch identified, plus an
attack-first note. **Recommended next session: the W1a attack + widening.**

## Session 2026-07-10 (T0a FOUND FALSE AS STATED — restated over `StoreDeclared`)

Attacking the last `sorry` (`semAux_fuel_stable_step`), the first move was to
stress-test the *statement* — and it is **FALSE over an arbitrary store**,
machine-checked in Lean (`Spec/Counterexample.lean`, axiom-clean, no
`native_decide`):

- **The hole:** `ttuLeaf` consults `rec` at the subject of every stored tupleset
  tuple with **no restriction check** (faithful to the oracle's `ttu_leaf`, which
  also has none). Taint/`depEdges` predict TTU consultations from the *declared*
  restriction types (`directTypes`). An admission-invalid tuple therefore creates
  a consultation edge invisible to stratification — and it can close a cycle
  through an `excl` subtrahend.
- **The counterexample** (2 keys, 3 tuples): `(A,p) := direct[user] but not
  ttu(q, ts)`, `(C,q) := ttu(p, ts)` — `(A,ts)`/`(C,ts)` UNDECLARED — plus store
  tuples `C:c ts A:o` and `A:o ts C:c` closing the loop `(A,p)@o → (C,q)@c →
  (A,p)@o`. `S` is stratifiable (`depEdges = []`); `semAux` **oscillates with
  period 4 forever**: the proved recurrence is `semAux (n+2) = !(semAux n)` at
  the query atom (`T0aCounter.oscillates`), refuting the old statement
  (`T0aCounter.fuel_stable_step_false`). Empirically confirmed by `#eval` first.
- **Resolution (documented precondition materialized, NOT a weakening):**
  `SEMANTICS.md` §8 already says stores hold *write-valid tuples*, and the real
  admission gate (`engine.py:_validate` (2), shared by both backends) rejects
  exactly such tuples ("matches no declared type restriction"). New
  `StoreDeclared S T` (`Spec/Confine.lean`) captures the needed clause — every
  stored tuple's `(object.type, relation)` is declared and its subject type is
  among the declared restriction types; it is *implied by* the gate, so every
  reachable store satisfies it. `semAux_fuel_stable_step` / `sem_fuel_stable`
  now carry `hDecl : StoreDeclared S T`. The counterexample store violates it
  (`T0aCounter.not_storeDeclared`).
- **Conformance note:** the corpora are admission-valid, so `sem` = oracle stays
  green; the divergence (oracle's visited-set answers `true` stably, `sem`
  oscillates) exists only on stores the system cannot hold.
- Also fixed pre-existing breakage: `Audit.lean` still referenced
  `writeDirect_writeStep`/`reachedBy_of_direct` (deleted with the abstract
  layer); the stale `.olean` had masked it. The audit now rebuilds clean.

This is the third statement-level defect caught by attack-before-prove (after
the additive `fuelBound` and the abstract-closure falsehood). The `sorry` count
stays 1 — now a TRUE statement worth proving.

## Review handled 2026-07-10 (second Gemini review, post-restatement)

User shared a Gemini review after the restatement. Vetted against the repo;
outcomes (logged per the review-handling norm):
- **T4 section MOOT / stale-state error:** it presents an algebraic path "to
  close the `sorry`" in `pathCount_addEdge` and calls T4 a "main remaining
  hurdle" — T4 was closed 2026-07-09 (sorry-free, axiom-clean, in the audit).
  Its proposed expansion also uses ℕ-subtraction (`phat g a b - [a=b]`), the
  exact trap the real proof avoided via `rec_unique`. No action.
- **T0a lattice framing ADOPTED as a tactical note** (ROADMAP T0a section):
  monotone iteration on a finite Bool-lattice bounded by height, + one fuel
  step per Kahn rank. With the vetting caveat it glossed: `Rec` is not finite
  a priori — the confinement-to-reachable-atoms lemma remains the load-bearing
  prerequisite.
- Endorsements (operational-trace restatement, `fuelBound` multiplicativity,
  `instances`/`universe` ghost handling, W3 `upos ∩ neg = ∅` expected easy)
  are consistent with the repo; no changes needed.

## Session 2026-07-10 (abstract closure DELETED — T-theorems restated operationally)

User adjudication: **"if anything is incorrect then delete it and rewrite the
plan; the end goal is still a formally verified Zanzibar/OpenFGA model tied to
the Python implementation."** Executed the deletion + restatement; `verify.sh`
green (build + audit + 60 conformance).

**What was deleted (false or assertion-backed, per the same-day FINDING):**
- `WriteStep` / `ReachedBy` (State.lean) — the abstract postcondition closure;
  admitted junk states (nothing tied `σ.edges`/`σ.residue` to the store).
- `graph_correct`, `graph_reached_inv` (Correct.lean) — **false as stated**;
  these were the 2 tracked T2 sorries.
- `backend_equivalence`, `exclusion_effective`, `no_ghost_grant` (Equiv.lean) —
  also false as stated (same junk-state counter-model); they had been "proved"
  only by `rw` through the false `graph_correct`.
- `cascade_converges` (old form) — true only because `WriteStep` *asserted*
  drainedness; `writeDirect_writeStep`, `reachedBy_of_direct` (Write.lean).

**⚠ `sorry` count 3 → 1 BY DELETION, NOT PROOF.** The full-scope obligations are
not gone — they return as ROADMAP stage W4 (restatement over the completed
operational write model). This is recorded loudly to keep the count honest.

**What replaced it (all real, proved, axiom-clean, sorry-free):**
- `graph_reached_inv` (T2a) + `cascade_converges` (T5) restated over
  `ReachedByDirect` in Correct.lean (one-liners off `reachedByDirect_inv`;
  fragment scope: writes produce no deltas, so T5 is trivially drained until
  the reconcile model lands).
- T2b = `graph_correct_direct` (DirectCorrect.lean, unchanged from the morning
  session).
- `backend_equivalence` (T3), `exclusion_effective` (T6a, deny-propagation at
  this scope — the fragment has no exclusions; the exclusion content arrives at
  W3/W4), `no_ghost_grant` (T6b) restated over `ReachedByAdmitted` in
  Equiv.lean, proved via T1 ∘ T2b-fragment + new `stratifiable_pureDirect`.
- Audit updated: `backend_equivalence` moved OUT of the sorryAx section; only
  `sem_fuel_stable` (T0a) remains there.

**Plan rewritten (ROADMAP top):** the end-goal architecture (sem↔Python via the
conformance harness; T1 done; T2 via staged operational write model; T3/T6
corollaries that widen per stage) + the staged T2 plan **W1 bridges → W2 rule
routing → W3 reconcile → W4 full-scope restatement**, plus a Phase-6
**graph-model conformance extension** (drive the Lean `writeDirect`/`check`
against the Python graph index) so the graph side gets the same executable tie
to the implementation that `sem` already has.

## Session 2026-07-10 (T2b SEMANTIC CORE CLOSED — `graph_correct_direct` on the fragment)

User: "assess, update the plan, then start on the hardest thing." Two assessment
outcomes, then the proof work:

**Assessment finding 1 (recorded in ROADMAP): the two T2 sorries are FALSE as
stated, not merely unproven.** `WriteStep`'s three thin postconditions (schema
fixed, nodes monotone, outbox drained) never tie `σ.edges`/`σ.residue` to the
store, and neither does `Inv` — a junk state carrying one arbitrary acyclic edge
satisfies `ReachedBy σ S [t]` + `Inv` + all schema hypotheses while `check` ≠
`sem`. So no proof effort can close `graph_correct`/`graph_reached_inv(Inv)` as
written; the operational write model is mandatory *for truth*. They stay as
tracked sorries only as placeholders for the eventual restatement over the
operational closure. Do not attack them as written.

**Assessment finding 2:** `ReachedByDirect` prepends a *rejected* write's tuple to
the store (writeDirect no-ops but `T` grows) — unfaithful to the composed system,
where the raised rejection rolls back the store insert too. Hence
`ReachedByAdmitted` (every step passed `admitEdge`), the faithful closure, on
which the edge set is **complete** for the store, not just sound.

**Proof work delivered (all green + pushed, axiom-clean, `verify.sh` full gate
incl. 60 conformance; `sorry` count held at 3 — nothing faked, the new theorem is
an addition, not a placeholder discharge):**

- **`semAux_mono`** (`Spec/FuelStable.lean`): fuel monotonicity of the evaluator
  on exclusion-free schemas (`Schema.noExclAll`), lifted from `evalE_mono`.
  Dual-use: T2b soundness fuel plumbing + a T0a untainted-layer ingredient.
- **New `GraphIndex/DirectCorrect.lean`** (~550 lines, sorry-free):
  - Fragment predicates `PureDirect` / `StoreValid` (the Python admission gate) /
    `StarFreeStore`, with `isDerived_pureDirect` (pure-direct ⇒ untainted ⇒ the
    read routes to `probeNonDerived`), `lookup_rel_ne_bare` (declared relation ≠
    `BARE`, via `WF.relNames` — `"..."` contains `'.'`), `lookup_keys_nonempty`.
  - `ReachedByAdmitted` + embedding into `ReachedByDirect`,
    **`admitted_edge_complete`** (every stored tuple's edge present), and
    `admitted_nodes_length` (`nodes = 2·|T|`, the fuel-bound arithmetic).
  - Star-free node algebra: `subjNode_plain`/`objNode_plain`, injectivity, and
    **`objNode_eq_subjNode`** — the flow-through identity that makes chain hops
    compose with `memberOfGranted`'s recursion.
  - `TupleChainN` (length-indexed chains) + `chainN_of_trail`.
  - The `directLeaf`/`memberOfGranted` interface: `grantsOf` pack/unpack,
    `directLeaf_grant_self`, `directLeaf_of_mog`, `mog_intro`, and the star-free
    eliminations `mog_elim`/`directLeaf_elim` (the `instances` branch cannot fire).
  - **`semAux_lift` — the semantic heart.** Membership propagates through a
    userset (`s ∈ s'` at fuel `f₀`, `s' ∈ v` at fuel `f` ⇒ `s ∈ v` at `f + f₀`):
    every direct match of `s'` at a grant is absorbed by `s`'s flow-through on the
    *same* grant (+ fuel monotonicity); every flow-through lifts by the fuel IH.
  - **`semAux_of_chainN`** (soundness): a length-`n` chain is a `sem` membership
    at fuel exactly `n` (base hop = self-grant at fuel 1; each hop lifts, f₀ = 1).
  - **`nreaches_of_semAux`** (completeness): fuel induction; direct match ⇒ the
    grant's own edge (edge-completeness), flow-through ⇒ IH + `.tail`.
  - **`graph_correct_direct`** — `check σ q = sem S T q` on the fragment,
    end-to-end: wildcard probes 2–4 die on star-free data (`nreaches_source/
    target_plain`), probe 1 bridges `reach ↔ NReaches ↔ compressed trail ↔
    TupleChainN ↔ sem`, chain fuel fits `fuelBound` (`2|T|+1 < |keys|·(2|T|+4)`).
  - Audit: `graph_correct_direct` = `[propext, Classical.choice, Quot.sound]`.

**This discharges the ROADMAP-isolated "T2b semantic core" (chain =
`memberOfGranted` recursion, both directions) on the honest fragment.** What
remains for T2: wildcard bridges (model + read, the `wAny`/`wAll` promotion only
covers the first hop), TTU/computed/union defs (rule-routed materialization),
the derived/residue path + faithful reconcile (T2a), then the restated full T2b.

## Session 2026-07-10 (T2b groundwork — read=sem base case + soundness scaffold)

User: "keep going with the proof part T2; commit and push when ready." Scope
continues the deliberate honest DEFER: no full T2b close (the `TupleChain ↔ sem`
core is multi-session), but **four green+pushed axiom-clean increments building the
read=`sem` correspondence from both ends.** `sorry` count held at 3; `verify.sh`
green throughout (build + 60 conformance + audit; audit now tracks all seven new
lemmas, no `sorryAx`).

**T2b base case CLOSED end-to-end (`GraphIndex/Correct.lean`):**
- `evalE_empty_store` / `semAux_empty_store` / **`sem_empty_store`** — `sem S [] q
  = false` (empty store grants nothing; `computed` recurses into a uniformly-`false`
  `rec`, by fuel induction).
- `probeNonDerived_empty` / `probeDerived_empty` / **`check_empty`** — the empty
  index reaches nothing and persists no residue, so `check (emptyState S) q = false`.
- **`graph_correct_empty`** : `check (emptyState S) q = sem S [] q`. This is exactly
  the `ReachedBy.empty` case of `graph_correct` — the genuine base of its eventual
  induction, no `sorry`.

**Read lifted into the relational world (`GraphIndex/State.lean`):**
- **`probeNonDerived_iff`** — on an endpoint-closed state the executable ≤4-probe
  read equals the disjunction of the four `NReaches` conditions (subject/object each
  literal or promoted to its wildcard node), via `reach_iff_nreaches`. Moves the read
  off the fixed-fuel probe `σ.reach` into fuel-free `NReaches`, where the semantic
  correspondence will be argued.

**Reachability→`sem` soundness scaffold (`GraphIndex/Write.lean`):**
- **`writeDirect_edges`** — an accepted write prepends exactly the one materialized
  edge `subjNode t.subject → objNode t.object t.relation`; a rejected write is the
  identity on edges.
- **`reachedByDirect_edge_sound`** — every edge of a `ReachedByDirect` state
  materializes some stored tuple (unconditional; induction over the write path).
- **`TupleChain`** + **`reachedByDirect_nreaches_chain`** — a graph path in the
  untainted fragment IS a stored-tuple membership chain (consecutive hops share the
  intermediate node = userset flow-through). Every `NReaches` path is a `TupleChain`.
  This is the soundness direction of T2b's reachability half, fully relational.

**The remaining T2b core, now sharply isolated:** the semantic content is
**`TupleChain T u v ↔ sem`-membership** — matching the membership chain against
`directLeaf`/`memberOfGranted`'s userset recursion, the wildcard nodes (`wAny`/`wAll`
promotion in `probeNonDerived_iff`), `instances`, and `matchingObjects`. Plus the
converse edge-completeness (`TupleChain → NReaches`) which needs an acyclic-*data*
hypothesis (`writeDirect` drops cycle-forming edges while `sem` fuel-evaluates them —
the T2b subtlety flagged last session). The read/reachability plumbing is now done
on both ends; what is left is the genuine `chain = recursion` semantic core. The
derived (residue) path of T2b and the full-generality `graph_reached_inv` `Inv`
conjunct (derived reconcile) remain the other deferred halves, unchanged.

## Session 2026-07-10 (T2a write model — untainted direct fragment)

User: "clear T2 as much as possible; commit often, push when done." Scope call
(user-adjudicated up front via a fidelity question): **build the concrete write
model, honest, no discharge expected this session.** Continues the deliberate
DEFER — the abstract `WriteStep` is now being *realized operationally* rather than
strengthened by postulate. Two green+pushed increments; `sorry` count held at 3;
all new results axiom-clean (audited).

**New file `GraphIndex/Write.lean` — the concrete single-tuple write for the
untainted (residue-free) fragment:**

- `writeDirect` — materialize one direct tuple as the edge `subjNode s → objNode o
  R`, **guarded by cycle-rejection** (§7.3: a self-loop or back-path-forming write
  is rejected and leaves the state unchanged; the back-path premise for
  `structInv_addEdge` comes from the executable admission probe via
  `reach_complete`). `admitEdge` is the decidable admission Bool.
- `nodeEnc_subjNode`/`nodeEnc_objNode` — endpoint nodes are always encoding-valid.
- `structInv_writeDirect` — structural invariant preserved by the write.
- `ResidueEmpty` + `residueEmpty_writeDirect` — the fragment (no persisted
  residues) is closed under writes; `inv_writeDirect` then preserves the **whole**
  `Inv` (residue clauses vacuous).
- `writeDirect_writeStep` — the concrete op realizes the abstract `WriteStep`
  (schema fixed, nodes monotone, quiescence preserved).
- `ReachedByDirect` (concrete write-closure) + `reachedByDirect_inv` — **T2a's
  `Inv` conjunct, honestly proved for the untainted fragment** (Inv ∧ ResidueEmpty
  ∧ Quiescent at every reached state, by induction over the write path).
  `reachedBy_of_direct` embeds it in the abstract `ReachedBy`.

**What this does NOT yet close, sharply isolated for the next pass:**
1. **Derived reconcile (rest of T2a).** `writeDirect` covers only untainted
   closure edges. The derived path (§7.6/§7.8) must (a) materialize residues via a
   faithful `reconcile`, and (b) handle the cross-key hazard the current fragment
   dodges by `ResidueEmpty`: an edge write can make an existing residue's `neg`/
   `upos` subject edge-reachable, breaking `negEdgeFree`/`uposEdgeFree` until the
   cascade re-reconciles. `inv_putResidue` (State.lean) is the per-key tool; the
   write must apply it to *all* reachability-affected keys with the correct
   residues.
2. **Read correspondence `check = sem` (T2b).** For the pure-direct fragment
   `check` reduces (no-wildcard) to `reach = NReaches`, and NReaches on the
   writeDirect-built edges *should* equal `directLeaf`'s transitive membership —
   BUT the subtlety is cycle-rejection: `writeDirect` silently drops cycle-forming
   edges, so on cyclic *data* the graph's edge set differs from "all tuples" while
   `sem` fuel-evaluates. The correspondence needs an acyclic-data hypothesis (or to
   account for rejected writes). Do NOT rush this — it is the genuine T2b core.

## Session 2026-07-10 (T2a groundwork — reachability layer fully proved)

User: "get the rest of T2 finished; commit often, push whenever you can." Scope
call (user-adjudicated mid-session via a fidelity question): **keep T2a honest,
DEFER** — do not postulate I6 as a `WriteStep` postcondition (the A1-style
operational shortcut was explicitly declined for `Inv`); instead **build toward the
genuine close** (the `reach ↔ NReaches` stabilization + a faithful reconcile). No
`sorry` discharged (count held at 3, as the user accepted); six green+pushed
increments of genuine, axiom-clean infrastructure delivered. `verify.sh` green
throughout (build + 60 conformance + audit).

**All in `GraphIndex/State.lean`, all axiom-clean (three standard axioms or fewer):**

- **Fuel-free reachability `NReaches`** (transitive closure of the edge list;
  distinct from WellDef's `Key`-typed `Reaches`). `Inv`'s reachability clauses
  (`acyclic`/`negEdgeFree`/`uposEdgeFree`) restated over it — this sidesteps the
  `nodes.length`-fuel churn that perturbs a capped probe when a write adds nodes.
  Lemmas: `NReaches.tail/trans/mono`, `NReachesR.trans`, `nreaches_nil`,
  `nreaches_cons_split` (first-use decomposition), **`acyclic_addEdge`**
  (cycle-rejection preserves acyclicity — the load-bearing I2 lemma).
- **Write-path primitives + preservation.** `addNode`/`addEdge`/`putResidue` with
  `@[simp]` projections; `StructInv` (the 4 structural clauses) + `structInv_addNode`
  / `structInv_addEdge` (genuine, cycle-rejection via `acyclic_addEdge`) /
  `structInv_empty` / `Inv.toStruct`; **`inv_putResidue`** (full `Inv` preserved by
  writing one I6-hygienic residue — other keys untouched; depends on *no* axioms).
- **`reach ↔ NReaches` BRIDGE — the ROADMAP-flagged "T2b blocker", now CLOSED.**
  `reachB_sound` + `reachB_mono` (soundness, any fuel); `reachB_of_nreaches` +
  `nreaches_iff_reachB` (unbounded equivalence); then the **shortest-walk
  compression** — `Trail` walk API (`trail_split`, `reachB_of_trail`,
  `trail_of_nreaches`, `trail_verts_mem`), pigeonhole plumbing (`mem_split_aux`,
  `exists_dup_split`, `nodup_len_le`), **`trail_compress`** (a walk with interiors
  in `nodes` shortens to ≤ `nodes.length` interiors), giving **`reach_complete`** and
  **`reach_iff_nreaches`**: the executable fixed-fuel probe `σ.reach` EXACTLY decides
  `NReaches` on any endpoint-closed state.

**What still blocks the two T2 sorries (unchanged in kind, now sharply isolated):**
the **faithful write/reconcile model** — how one tuple write produces the exact
edges + reconciled residues. Needed by BOTH: T2a (global I6 re-establishment after
edge changes — `inv_putResidue` handles one key; the write must cover all
reachability-affected keys with the *semantically correct* residues, so a
delete-only "reconcile-by-construction" is unfaithful and would break T2b) and T2b
(`check = sem` — the ≤4-probe decomposition now has its reachability half via the
bridge, but still needs the residue = `sem` half from the write model). This is the
genuine multi-session core; the reachability layer under it is now done.

## Session 2026-07-10 (T2 graph model CONCRETIZED — T5 closed)

**Scope decision (user-approved): "concretize + partial proofs," not the full T2
close** (T2 is the ~half-effort multi-session core; a faithful full close isn't
honestly doable in one pass, and a cooked `check := sem` model was explicitly
rejected). Delivered, `verify.sh` green (build + 60 conformance + audit),
count **4 → 3**:

- **All 7 opaque graph placeholders are now CONCRETE** (`GraphIndex/State.lean`,
  `sorry`-free): `GraphState` (nodes with `plain/wAny/wAll` variants, direct edges,
  residues `(stars,neg,upos)`, outbox+watermark), `GraphModel.check` (the faithful
  §7.5 ≤4-probe read + §7.6 residue path, routed by `isDerived`), `Inv` (I-series
  core: node encoding, I1 endpoint existence, I2 acyclicity, I6 residue hygiene incl.
  the load-bearing `neg ∩ edge-holders = ∅`), `ReachedBy` (inductive write-closure
  from `emptyState` via a minimal operational `WriteStep`), `Quiescent`
  (outbox-drain), `GraphAccepts` (decision-15 scope). The C4 "pending opaque" list
  for the graph model is cleared.
- **Reads model reachability, not path counts.** `check` probes a fuel-bounded
  transitive closure `reachB` of the direct edges (`p(u,v)>0`), factoring the
  path-*counting* layer out to `Closure.lean`/T4 — this dodges threading a
  `Fintype NodeKey` (infinite key space) through the read and keeps `check`
  executable. `Inv.acyclic` pins the DAG property T4 needs.
- **T5 `cascade_converges` CLOSED, axiom-clean** (`[propext]`). The model bakes the
  in-txn cascade into each write (§7.8 / A1, user-approved), so outbox-drain is a
  `WriteStep` postcondition and `Quiescent` holds at every reachable state by
  induction on `ReachedBy`.
- **T2a `graph_reached_inv`**: the `Quiescent` conjunct is closed (via
  `cascade_converges`); the `Inv` conjunct stays a tracked `sorry` (needs the full
  operational write path — edge/bridge/reconcile — which `WriteStep` abstracts).
- **Partial base-case lemmas, axiom-clean:** `inv_empty`, `quiescent_empty`,
  `reach_empty` (`reachB [] = false`).

**Remaining 3 sorries:** `semAux_fuel_stable_step` (T0a); `graph_reached_inv`'s `Inv`
half and `graph_correct` (T2b, the read = `sem` completeness argument) — the genuine
deep content, deferred as before. The concretization makes those statements relate
*real* definitions (not opaque constants), so the next attempt starts from a concrete
model rather than a stub.

## Session 2026-07-09 (T1 FULLY CLOSED — set engine = sem)

**T1 is DONE** — `setEngine_correct` is proved and axiom-clean (`[propext,
Classical.choice, Quot.sound]`, verified in `Audit.lean`). Count 5 → 4. `verify.sh`
green (build + 60 conformance + audit). The `opaque SetEngineModel.check` is replaced
by a concrete MemberSet-expand model. **T1 needs no WF/Stratifiable/AllValid** — the
hypotheses are retained (underscored) but unused: the expansion computes `semAux` at
*every* fuel, so equality at the shared `fuelBound` is unconditional.

**The model (`SetEngine/Eval.lean`).** `Id := SubjectRef`; `expandAux` is pure
fuel-recursion mirroring `semAux` (`expandStep`/`expandE` mirror `step`/`evalE`);
boolean nodes fold with `union`/`intersect`/`subtract`; leaves are `grantMS`/`parentMS`
(token `singletonEntity`/shape `star` + flow-through recursion), faithfully
transcribing `engine.py:direct_expand`/`ttu_expand`. `check` = `containsShape` of the
expanded query node at the query subject.

**The key modeling insight (makes the whole thing tractable).** `containsShape` *never
reads `pop`* — only `pos`/`stars`/`neg`. The distribution lemmas
(`containsShape_*_focus`) prove the probe answer is invariant across *any* population
satisfying `PopFocus`/`WFp`/`Grounded`. So I use a **query-focused population**
`popOf s σ = {s}` at `s`'s own shape, `∅` elsewhere — which makes all three invariants
hold *definitionally* (`popFocus_popOf`, `grounded_popOf` are trivial; `WFp` is every
`normalize` output). This discharges the "confinement" obligation the ROADMAP flagged
as the largest remaining piece, with **no** `pos ⊆ U` induction.

**Proof structure (`SetEngine/Correct.lean`, all axiom-clean).**
- `containsShape_unionFold` — probing a `union`-fold = `any` of the probes.
- `containsShape_grantMS` — one grant's probe = `grantMatch || grantFlow` (4-way on
  subject kind × wildness); `containsShape_expandDirect` assembles via `any_or_distrib`
  and a per-subject-kind match, `directLeaf`'s `memberOfGranted` = `any grantFlow` by
  `rfl`.
- `any_filter_guard` + `containsShape_expandTtu` — `ttuLeaf`'s guarded `T.any` =
  filtered `ttuParents.any`; per-parent probe matches by `pn == STAR` case split.
- `containsShape_expandE` (structural: boolean via `*_focus`, leaves via the above,
  `computed` = `HR`), `containsShape_expandAux` (fuel induction: `HR` = the fuel-IH,
  `HW` = `wfp_expandAux`), then `setEngine_correct`.
- Tactic notes for the leaf Bool-algebra: `beq_eq_decide` bridges `==`↔`decide`;
  `bool_eq_of_iff` + expanding `= true` lemmas + `SubjectRef.eq_iff` reduces to pure
  Props; `eq_comm` in *full* `simp_all` LOOPS with `decide`/`Bool` present (max-recursion)
  — keep it out; canonicalize orientation at Prop level or fall back to `tauto`/`aesop`.

**Now unblocked:** T3/T6a/T6b `rw`-route through T1∘T2b — they become real the moment
T2b lands. Remaining 4 sorries: T0a `semAux_fuel_stable_step`; T2a/T2b/T5 (need the
concrete graph state machine). Next-most-tractable: T0a (see ROADMAP option (a)).

## Session 2026-07-09 (T1 core corrected + T0a ingredient 1)

User asked to build T0a and T1. Both are multi-session (each needs its concrete
model/infrastructure first — see ROADMAP). This session delivered genuine, committed,
axiom-clean progress on both fronts; **no `sorry` discharged** (count held at 5), and
`verify.sh` stays green (build + 60 conformance + audit).

**Headline: the ROADMAP's T1 lemma was FALSE; corrected and proved.** The naive
intensional distribution `containsShape (op M N) = containsShape M ⟨op⟩ containsShape N`
under `WF` alone does NOT hold — `#eval`-confirmed counterexample with both operands
`WF`: `a={stars:={σ}}`, `b={stars:={shape}, neg:={uid}}`, `uid∈pop σ`, `σ≠shape` ⇒
both operands `false`, `union a b` `true`. This is exactly why last session's
`simp; tauto` never closed it. **Root cause:** the query shape must be the subject's
*own* shape and populations partition the id space by shape — the missing invariant
`PopFocus pop uid shape := ∀ σ, uid∈pop σ → σ=shape`. New file `SetEngine/Contains.lean`
(axiom-clean, `[propext, Classical.choice, Quot.sound]`):
- `containsShape_union_focus` (needs `PopFocus` + `WFp`),
- `containsShape_intersect_focus` / `containsShape_subtract_focus` (additionally need
  `Grounded pop uid shape m := uid∈m.pos → uid∈pop shape` — else a positive *ghost* is
  dropped by the extensional meet/difference; also `#eval`-confirmed false without it),
- support: `WFp`, `wfp_normalize`/`wfp_union/intersect/subtract`, `PopFocus`,
  `Grounded`, `mem_starpop_focus`, `mem_ext_focus`, `containsShape_normalize`,
  `wfp_atoms`, `bool_ext`. Technique: reduce to 7 membership atoms, then
  `by_cases`-on-all-7 `<;> simp_all` (tauto times out).
**T1 next:** build the concrete `SetEngineModel.check` expand model whose `pop`/`Id`
*satisfy `PopFocus`+`WFp`+`Grounded` per node*, then the `Direct`/`TTU` leaf-vs-`sem`
equalities. The distribution core is now done.

**T0a: decision + ingredient 1.** Chose option (a) (real proof, no spec change).
New file `Spec/FuelStable.lean` (axiom-clean): `evalE_mono` — untainted/positive
fragment monotonicity (`RecLe`-refinement preserves truth on exclusion-free exprs),
via `memberOfGranted_mono`/`directLeaf_mono`/`ttuLeaf_mono` + `Expr.noExcl`. This is
step 1 of the convergence argument (untainted fragment = monotone iteration). The
full worked-out structure (untainted monotone layer + tainted Kahn-DAG ranks + the
reachable-atom counting bound) is in the file header and ROADMAP. Confirmed: pure
pigeonhole is invalid (no visited-set; `Φ` non-monotone via `.excl`).

## Session 2026-07-09 (T0b fully closed — Kahn correctness)

**T0b is DONE** — `stratify_none_iff_cycle` and `stratify_topological` are proved and
axiom-clean (`[propext, Classical.choice, Quot.sound]`). All in `Spec/WellDef.lean`, built
from scratch on the concrete `kahn`/`readyNodes`/`depEdges` (no new model needed, as the
ROADMAP predicted). Count 7 → 5. `verify.sh` green (build + 60 conformance + audit).

Infrastructure proved (all axiom-clean, reusable):
- `mem_readyNodes_iff` — `n` ready ↔ remaining ∧ every out-edge leaves remaining.
- `kahn_succ` — one-step unfolding of `kahn` on a non-empty remaining set (isolates the
  definitional `if`/`let` churn once).
- `stuck_cycle` — **the pigeonhole core**: a non-empty stuck set (no ready nodes) has a
  cycle. Builds a total successor `g` (choice), iterates `g^[·]` into `R.toFinset`,
  `Finset.exists_ne_map_eq_of_card_lt_of_maps_to` gives a repeat, `reaches_orbit` turns
  the sub-walk into `Reaches edges k k`.
- `kahn_none_stuck` (⟹): `kahn = none` ⇒ a stuck set exists. The invariant
  `|remaining| ≤ fuel` (fuel starts at `|nodes|`, each round drops ≥1 via
  `List.length_filter_eq_length_iff`) rules out the fuel-exhaustion branch, so only a
  genuine stuck set can fail.
- `first_edge` / `cyc_out` — a cycle node has an out-edge to another cycle node.
- `kahn_cycle_none` (⟸): every cycle node persists in `remaining` (never ready), so the
  run never empties ⇒ `none`.
- `depEdges_mem` — both endpoints of a dependency edge are tainted keys (pins cycle
  nodes ⊆ initial `remaining`).
- `kahn_topo` — **the topological invariant**: threads (H1) `acc.reverse` is already
  topological + (H2) peeled nodes' out-edges have left `remaining`. Newly-peeled ready
  layer is appended last; readiness + H2 force its edges strictly earlier, so the
  invariant is preserved and the final `L` is `TopoLayered`. Needed hand-rolled
  `getD_app_lt`/`getD_app_ge`/`getD_ge_default`/`mem_getD_singleton` (this Mathlib has no
  `getD_append`).

**Next-most-tractable remaining:** T0a `semAux_fuel_stable_step` (subtle — see ROADMAP;
may want the visited-set spec refactor + conformance re-validation), then T1/T2 which need
their concrete models built first.

## Session 2026-07-09 (T4 fully closed)

**T4 is DONE** — `GraphIndex/Closure.lean` is `sorry`-free and axiom-clean. Built the
walk API the ROADMAP called the blocker, then the counting theorem, all from scratch on
the concrete `pathsOfLength`:
- `pathsOfLength_pos_iff` — walk-count positivity ↔ an `IsChain` vertex list (bridges to
  Mathlib's `List.IsChain` reachability API).
- `pathsOfLength_card_vanish` — **the pigeonhole vanishing lemma**: an acyclic graph has
  no length-`|V|` walk (`|V|+1` vertices ⇒ repeat ⇒ closed sub-walk via `IsChain.drop/take`
  + `getElem?_drop`/`getElem?_take_of_succ` ⇒ `pathCount x x > 0` ⇒ ⊥). Discharges the
  `hvanish` hypothesis of `phat_recurrence`.
- `pathsOfLength_succ_last` (last-edge decomposition), `pathsOfLength_mono`,
  `acyclic_of_addEdge`, `no_back_path` (the new edge can't close a cycle — needs L2).
- `rec_closed_form` / `rec_unique` — the affine recurrence `X a = c a + ∑ dcount·X`
  has a **unique** solution in a DAG (unroll `|V|` steps; the `X`-tail vanishes, leaving a
  matrix series in `c` only). No Nat subtraction anywhere.
- `pathCount_addEdge` — `phat g'` and the target formula both solve `g'`'s recurrence, so
  by `rec_unique` they coincide; the spurious back-path term vanishes by `no_back_path`.
- `pathCount_removeEdge` — the exact inverse: `(g.removeEdge u v).addEdge u v = g`, so it
  is `pathCount_addEdge` applied to `g.removeEdge u v`.

Count 9 → 7. `verify.sh` green (build + 60 conformance + audit). **Next-most-tractable
remaining: T0b Kahn** (self-contained, no new model needed); then T1/T2 need their
concrete models built first (see ROADMAP).

## Current phase & resume point

- **SORRY COUNT = 0 (2026-07-10).** Every stated theorem is proved at its
  documented scope; the remaining work is SCOPE WIDENING (ROADMAP W1–W4: wildcard
  bridges, rule routing, derived reconcile, full-scope restatement) plus Phase 6
  hardening (audit as hard gate, graph-model conformance extension).
- **W1a DONE (2026-07-10):** T2b widened to bare star grants `[user:*]`
  (`graph_correct_bareStar`, `GraphIndex/BareStarCorrect.lean`, axiom-clean).
- **W1b STARTED (2026-07-10):** object wildcards `[T:*]`. Attack-first proved
  (machine-checked) that bridges are **mandatory** here (unlike bridge-free W1a).
  The faithful bridge-materializing write model is delivered + structurally sound
  (`GraphIndex/ObjStarWrite.lean`: `writeWild`, `structInv_writeWild`,
  `WildReached`, `wildReached_structInv`, all axiom-clean). **Resume → the W1b
  read correspondence `graph_correct_objStar`** (bridge-completeness invariant +
  soundness/completeness with grant/bridge-hop interleaving = `matchingObjects`
  absorption; the read reduces to probe 1 ∨ probe 3, subjects star-free). See the
  W1b session block above and ROADMAP W1b for the sharply-isolated remaining work.
- **Phase 1 DONE** (Lean skeleton + all T0–T6 stated; `lake build` green with 9
  `sorry`s). **Phase 2 CORE DONE ahead of schedule**: conformance CLI (`zcli`) live;
  spec-vs-oracle answer conformance green (6/6 grid comparisons). No adjudication
  events — the executable `sem` matches the reference oracle.
- **User is reviewing `SEMANTICS.md` async** ("keep going, I'll review async"); A1 &
  A4 accepted. Continue proving; revisit if the review changes the spec.
- **Resume point → the W1b read correspondence** (`graph_correct_objStar`); the
  W1b bridge-materializing write model + structural invariant are done. Or Phase 6
  hardening; T0a is closed, nothing is blocked on the spec side.
- **Commands:** `cd formal/lean && lake build` (lib) / `lake build zcli` (CLI);
  `python -m pytest formal/conformance/ -q` (needs `zcli` built).

---

## Phase ledger

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 0 | Semantics extraction | **done** | SEMANTICS.md; 7 ambiguities logged |
| 0.5 | verify compiler undefined-reference behavior (A3) | todo | refine `WF` in Phase 3/4 |
| 1 | Lean skeleton + spec + theorem statements | **done** | builds green; all T0–T6 stated |
| 2 | Conformance bridge v1 | **done** | three-way `sem`/oracle/set-engine over 11 schemas, 33 tests green; graph backend TODO in P4 |
| 3 | Set-engine model + T1 | **done** | concrete expand model; T1 proved, axiom-clean |
| 4 | Graph-index model + T2/T4/T5 | **fragment scope done** | T4 ✅; T2a/T2b/T5 proved at star-free pure-direct scope over the operational closure; widening = ROADMAP W1–W4 |
| 5 | Equivalence T3 + security T6 | **fragment scope done** | T3/T6a/b real proved theorems at fragment scope; widen per W-stage |
| 6 | Hardening + CI + handoff | not started | |
| 7 | (optional) concurrency/crash in TLA+ | not started | separate go/no-go |

## Theorem ledger

Status: {planned, stated (compiles w/ sorry), proved-mod-deps, proved, blocked}.

| Theorem | Lean name | Status | Note |
|---------|-----------|--------|------|
| T0a spec well-defined (fuel-stable) | `sem_fuel_stable` | **proved** | axiom-clean; RESTATED over `StoreDeclared` (original FALSE — `Spec/Counterexample.lean`), then closed via confinement + untainted counting + Kahn rank induction |
| T0a stabilization core | `semAux_fuel_stable_step` | **proved** | `layer_stable`/`all_stable` assembly; arithmetic fits `fuelBound` |
| T0a confinement | `evalE_congr`, `step_congr`, `semAux_undeclared` | **proved** | Confine.lean; consulted atoms ⊆ `exprRefs × relevantNames` (ttu case = `StoreDeclared`) |
| T0a untainted phase | `chain_stabilizes`, `untainted_closed`, `semAux_mono_untainted`, `untainted_stable` | **proved** | Stabilize.lean; taint fixpoint + masked monotonicity + counting |
| T0a Kahn interface | `kahn_topo_strict`, `kahn_covers`, `kahn_layers_sub`, `kahn_length`, `stratify_covers`/`_layers_tainted`/`_length`/`_topo_strict` | **proved** | WellDef.lean; strict layering + coverage |
| T0a refutation record | `T0aCounter.oscillates`, `T0aCounter.fuel_stable_step_false` | **proved** | Counterexample.lean; the pre-`StoreDeclared` statement is FALSE (period-4 oscillation) |
| T0b stratify soundness | `stratify_none_iff_cycle`, `stratify_topological` | **proved** | Kahn correctness; axiom-clean. Pigeonhole `stuck_cycle` + fuel invariant `kahn_none_stuck` + cycle-persistence `kahn_cycle_none` + topo invariant `kahn_topo` |
| T0b pigeonhole core | `stuck_cycle` | **proved** | stuck set (no ready nodes) ⇒ cycle, via orbit + `Finset` pigeonhole |
| T0b Kahn helpers | `mem_readyNodes_iff`, `kahn_succ`, `kahn_none_stuck`, `kahn_cycle_none`, `kahn_topo`, `depEdges_mem` | **proved** | reusable Kahn/`readyNodes` API (WellDef.lean) |
| T1 set engine = sem | `setEngine_correct` | **proved** | axiom-clean; concrete expand model + fuel/AST induction; WF/Strat/AllValid unused |
| T1 leaf/structure/fuel | `containsShape_expandDirect/expandTtu/expandE/expandAux` | **proved** | grant/parent probe correspondence, structural + fuel inductions (Correct.lean) |
| T1 model + invariants | `expandAux`, `popOf`, `wfp_expandAux`, `popFocus_popOf`, `grounded_popOf` | **proved** | query-focused population makes PopFocus/WFp/Grounded definitional |
| T1 containsShape distribution | `containsShape_union/intersect/subtract_focus` | **proved** | Contains.lean; corrected (naive WF-only version is FALSE) — needs `PopFocus`(+`Grounded` for ∩/∖); axiom-clean |
| T1 distribution support | `WFp`, `wfp_normalize`, `mem_starpop_focus`, `mem_ext_focus`, `containsShape_normalize`, `wfp_atoms` | **proved** | Contains.lean building blocks |
| T0a untainted monotonicity | `evalE_mono` | **proved** | FuelStable.lean; ingredient 1 (excl-free ⇒ `RecLe` preserves truth); axiom-clean `[propext, Quot.sound]` |
| T0a monotonicity leaves | `memberOfGranted_mono`, `directLeaf_mono`, `ttuLeaf_mono` | **proved** | FuelStable.lean; positive `rec` use at leaves |
| T2a graph invariant + materialize | `graph_reached_inv` | **proved (fragment scope)** | RESTATED 2026-07-10 over `ReachedByDirect` (abstract version deleted as FALSE); full scope returns at ROADMAP W4 |
| T2b graph read = sem | `graph_correct_direct` | **proved (fragment scope)** | abstract `graph_correct` DELETED as FALSE; fragment instance proved end-to-end (DirectCorrect.lean); full scope returns at W4 |
| graph model concretization | `GraphState`/`GraphModel.check`/`Inv`/`Quiescent`/`GraphAccepts` | **concrete** | State.lean; opaque placeholders → real defs; the abstract `WriteStep`/`ReachedBy` closure deleted (operational closure lives in Write.lean/DirectCorrect.lean) |
| graph model base cases | `inv_empty`, `quiescent_empty`, `reach_empty` | **proved** | axiom-clean; `emptyState` ⊨ `Inv`/`Quiescent`, reaches nothing |
| T3 equivalence | `backend_equivalence` | **proved (fragment scope)** | RESTATED over `ReachedByAdmitted`; real `rw` through T1∘T2b-fragment + `stratifiable_pureDirect`; widens per W-stage |
| T4 counting-IVM (insert/delete) | `pathCount_addEdge/removeEdge` | **proved** | the crux; axiom-clean. Walk API + pigeonhole vanishing + recurrence-uniqueness |
| T4 pigeonhole vanishing | `pathsOfLength_card_vanish` | **proved** | `Acyclic → no length-\|V\| walk`; the ROADMAP-flagged blocker |
| T4 walk correspondence | `pathsOfLength_pos_iff` | **proved** | positivity ↔ `IsChain` vertex list |
| T4 recurrence uniqueness | `rec_unique`, `rec_closed_form` | **proved** | affine recurrence has unique solution in a DAG (matrix series) |
| T4 last-edge / monotonicity | `pathsOfLength_succ_last`, `pathsOfLength_mono`, `no_back_path` | **proved** | supporting lemmas for the counting expansion |
| T4 first-edge recurrence | `phat_recurrence` | **proved** | conditional on the DAG no-`|V|`-walk hyp; axiom-clean |
| T4 boundary sum-identity | `phat_boundary` | **proved** | the sum-manipulation heart, no acyclicity; axiom-clean |
| (lemma) sum-shift | `sum_Ico_shift_boundary` | **proved** | Nat induction |
| T5 cascade converges | `cascade_converges` | **proved (fragment scope)** | RESTATED over `ReachedByDirect` (old form held only by `WriteStep` assertion); becomes contentful at W3 (reconcile/outbox) |
| T6a exclusion-effective | `exclusion_effective` | **proved (fragment scope)** | RESTATED over `ReachedByAdmitted`; deny-propagation at this scope — exclusion content arrives W3/W4 |
| T6b no-ghost-grant | `no_ghost_grant` | **proved (fragment scope)** | RESTATED over `ReachedByAdmitted`; via T2b-fragment |
| T6c wildcard scoping | `wildcard_scoping` | **proved** | real theorem now: `T:*` grants are type-scoped, via `restrictionMatches_type` |
| (lemma) grant type-scoping | `restrictionMatches_type` | **proved** | axiom-clean `[propext, Quot.sound]` |
| (lemma) `ext_normalize` | `MemberSet.ext_normalize` | **proved** | MemberSet renorm correctness |
| (lemmas) membership/constructors | `mem_ext_union/intersect/subtract`, `ext_empty/singletonEntity/star`, `neg_subset_starpop` | **proved** | T1 leaf/composition building blocks (Algebra.lean) |
| (lemmas) algebra ext laws | `ext_union/ext_intersect/ext_subtract` | **proved** | `ext (a⊕b) = ext a ⊕ ext b` (Algebra.lean); T1 workhorses |
| (lemmas) star laws | `stars_union/intersect/subtract` | **proved** | `rfl` |
| (lemmas) star×boolean | `containsStar_union/intersect/subtract` | **proved** | the pinned intensional `'*'` table (§5.6) |
| T2a write model (untainted) | `writeDirect`, `structInv_writeDirect`, `inv_writeDirect` | **proved** | Write.lean; concrete guarded edge write preserves the whole `Inv` on the residue-free fragment; axiom-clean |
| T2a untainted write-closure | `ReachedByDirect`, `reachedByDirect_inv` | **proved** | Write.lean; the operational closure + its running invariant (`reachedBy_of_direct`/`writeDirect_writeStep` deleted with the abstract layer) |
| T2a write-effect projections | `quiescent_writeDirect`, `residueEmpty_writeDirect`, `writeDirect_outbox/watermark/schema/monoNodes` | **proved** | Write.lean |
| T2b base case | `graph_correct_empty` | **proved** | Correct.lean; `check (emptyState S) q = sem S [] q` — the `ReachedBy.empty` case, axiom-clean |
| T2b empty-store spec | `sem_empty_store`, `semAux_empty_store`, `evalE_empty_store` | **proved** | Correct.lean; `sem S [] q = false` by fuel induction |
| T2b empty read | `check_empty`, `probeNonDerived_empty`, `probeDerived_empty` | **proved** | Correct.lean; empty index answers `false` (no edges, no residue) |
| T2b read→reachability | `probeNonDerived_iff` | **proved** | State.lean; ≤4-probe read = disjunction of four `NReaches` conditions (endpoint-closed), via `reach_iff_nreaches` |
| T2b reachability→chain | `TupleChain`, `reachedByDirect_nreaches_chain`, `reachedByDirect_edge_sound`, `writeDirect_edges` | **proved** | Write.lean; untainted graph path = stored-tuple membership chain; edges trace to tuples |
| evaluator fuel monotonicity | `Schema.noExclAll`, `semAux_le_succ`, `semAux_mono` | **proved** | FuelStable.lean; exclusion-free schemas are fuel-monotone (T2b fuel plumbing + T0a ingredient) |
| **T2b fragment read = sem** | `graph_correct_direct` | **proved** | DirectCorrect.lean; end-to-end `check = sem` on the star-free pure-direct fragment, axiom-clean |
| T2b semantic core, soundness | `semAux_lift`, `semAux_of_chainN`, `semAux_one_of_tuple` | **proved** | DirectCorrect.lean; userset lifting (membership through a userset) + chain⇒`sem` at fuel = chain length |
| T2b semantic core, completeness | `nreaches_of_semAux` | **proved** | DirectCorrect.lean; `sem`⇒graph path (edge-completeness + flow-through `.tail`) |
| T2b fragment infrastructure | `ReachedByAdmitted`, `admitted_edge_complete`, `admitted_nodes_length`, `TupleChainN`, `chainN_of_trail`, `isDerived_pureDirect`, `objNode_eq_subjNode`, leaf intro/elim lemmas | **proved** | DirectCorrect.lean; admitted-writes closure (faithful to composed-system rollback), grant/leaf interface, node algebra |
| **T2b stage W1a — bare star grants** | `graph_correct_bareStar` | **proved** | BareStarCorrect.lean; `check = sem` widened to `[user:*]` grants (`BareStarStore`), ZERO bridges (wildcard-spec §3.2); axiom-clean |
| W1a soundness (covered chains) | `Covers`, `semAux_one_covers`, `semAux_of_chainN_bs`, `semAux_one_of_bareStar`, `semAux_lift_bs` | **proved** | BareStarCorrect.lean; chain base generalized from "is the subject" to "covers it" (leading bare-star hop) |
| W1a completeness (probe disjunction) | `reach_of_semAux_bs` | **proved** | BareStarCorrect.lean; `sem` ⟹ reach from `subjNode s` OR `wAny(s.shape)` (probe 1 ∨ probe 2) |
| W1a leaf elimination + edge chars | `directLeaf_elim_bs`, `mog_elim_nus`, `admitted_edge_source_char`, `admitted_edges_target_plain`, `nreaches_source_char` | **proved** | BareStarCorrect.lean; 3-way leaf elim (exact\|bare-star\|flow), userset-`wAny` never an edge source ⇒ probe 2 dead for usersets |

## `sorry` ledger

**Count = 0** (was 9). `semAux_fuel_stable_step` — the last one — was first
RESTATED (the original was FALSE over arbitrary stores; `StoreDeclared` added,
counterexample machine-checked in `Spec/Counterexample.lean`) and then PROVED
(2026-07-10; see the session entry). The `verify.sh` sorry inventory reports 0;
`sem_fuel_stable` is axiom-clean in the audit.

**⚠ HONESTY NOTE on the 3 → 1 drop (2026-07-10):** the two `GraphIndex/Correct.
lean` sorries (`graph_correct`, `graph_reached_inv`'s `Inv` conjunct) were
**DELETED as false-as-stated, not proved** (user-directed; the abstract
`WriteStep`/`ReachedBy` closure admitted junk states). Their obligations return
at full scope as ROADMAP stage W4. The theorem names survive, restated over the
operational closure at fragment scope, where they are genuinely proved
(`graph_reached_inv`/`cascade_converges` over `ReachedByDirect`;
`graph_correct_direct`/T3/T6a/T6b over `ReachedByAdmitted`).

**`GraphIndex/DirectCorrect.lean` is `sorry`-free** — the T2b semantic core
(userset lifting, chain ⇔ `sem`, both directions) and the end-to-end fragment
read-correctness theorem `graph_correct_direct`.

**`GraphIndex/State.lean` is `sorry`-free** — the 7 opaque graph placeholders are now
concrete definitions; `cascade_converges` (T5) is closed off the concrete `ReachedBy`.

**`GraphIndex/Write.lean` is `sorry`-free** — the concrete write model for the untainted
fragment (`writeDirect` + preservation + `ReachedByDirect`/`reachedByDirect_inv`); T2a's
`Inv` conjunct is proved honestly for the residue-free fragment. The abstract
`graph_reached_inv` sorry remains (its generality covers derived relations, which need
the reconcile/residue-materialization half — the isolated remaining T2a content). Now
also carries the reachability→`sem` soundness scaffold (`writeDirect_edges`,
`reachedByDirect_edge_sound`, `TupleChain`, `reachedByDirect_nreaches_chain`).

**`GraphIndex/Correct.lean`'s T2b base case is `sorry`-free** — `graph_correct_empty`
(`= sem S [] q`, both `false`) discharges the `ReachedBy.empty` case end-to-end. The
two full-generality `sorry`s (`graph_reached_inv`'s `Inv` conjunct, `graph_correct`)
remain; the T2b core left is `TupleChain ↔ sem`-membership (see the session entry).

**`SetEngine/Correct.lean` is now `sorry`-free** — `setEngine_correct` (T1) proved and
axiom-clean; the `opaque SetEngineModel.check` is replaced by a concrete expand model.

**`Spec/WellDef.lean`'s T0b theorems are now `sorry`-free** — `stratify_none_iff_cycle`
and `stratify_topological` proved and axiom-clean.

**`GraphIndex/Closure.lean` is now `sorry`-free** — `pathCount_addEdge` /
`pathCount_removeEdge` proved and axiom-clean (`[propext, Classical.choice, Quot.sound]`).

## Axiom audit snapshot (C4) — `lake build ZanzibarProofs.Audit`

Run 2026-07-09. `#print axioms` on representative results:
- `ext_normalize`, `ext_union`, `containsStar_subtract`, `mem_ext_union` →
  `[propext, Classical.choice, Quot.sound]` (the 3 standard axioms — clean).
- `restrictionMatches_type`, `wildcard_scoping`, `evalE_mono` → `[propext,
  Quot.sound]` (cleaner).
- `containsShape_union/intersect/subtract_focus` (T1 corrected core) → the 3 standard
  axioms.
- `sem_fuel_stable`, `backend_equivalence` → `[sorryAx]` (honestly flagged;
  route through tracked sorries). **No custom axioms** — Gemini's suggested
  `phat_def` axiom was rejected, keeping the surface clean for the final C4 gate.

## T4 progress (2026-07-10, this session)

`GraphIndex/Closure.lean`: `pathCount` **concretized** (weighted-walk sum over
`Fintype V`; the `opaque` is gone). Proved (axiom-clean): `pathsOfLength_zero/succ`,
`sum_Ico_shift_boundary` (Nat induction), `phat_boundary` (the first-edge recurrence
WITH the length-`|V|` boundary term, pure `Finset.sum` manipulation, no acyclicity),
and `phat_recurrence` (the clean recurrence, taking the DAG no-`|V|`-walk property as
an explicit hypothesis). Remaining T4 obligations (still `sorry`, count held at 9):
`pathCount_addEdge`/`removeEdge` — the algebraic expansion — plus discharging the
`hvanish` hypothesis via the pigeonhole vanishing lemma (needs a walk API; see
ROADMAP). Net: the mathematical heart of the counting theorem is proved; the
opaque is removed; count unchanged.

## Pending axioms (opaque placeholders — to be replaced, flagged by the C4 axiom audit)

The only remaining `opaque` is `ValidIdent` (Core/Ident — intended to stay abstract
per §2.1). **The entire graph model is now CONCRETE** — `GraphState`,
`GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`, `GraphAccepts` became real
definitions 2026-07-10 (State.lean); `pathCount` and `SetEngineModel.check` were
concretized earlier. The final axiom audit must show only `propext, Classical.choice,
Quot.sound` — no opaque model constants remain to eliminate (only the tracked
`sorry`s in `graph_reached_inv`/`graph_correct`/`semAux_fuel_stable_step`).

---

## Adjudications (spec/oracle/backend disagreements)

Per plan §8.2: any disagreement → STOP, record here (schema, ops, query, each
system's answer, analysis). Do NOT edit oracle/goldens/Python semantics or weaken a
theorem to match.

- **2026-07-09 — `fuelBound` too small (spec bug, not a semantic ambiguity). RESOLVED.**
  Found via a Gemini review of the Lean spec; **confirmed empirically**: a schema
  with `n` computed relations chained per object and linked across an `m`-object
  parent chain by TTU (a `deep_grid`, n=m=8) evaluates at depth ~`n·m`=64, but the
  additive `fuelBound = |keys| + 2|T| + 4` = 29 cut `semAux` off early → spec
  returned `false` where the oracle returned `true`. The oracle is ground truth; the
  bug was mine (under-provisioned fuel). **Fix:** `fuelBound = |keys| · (2|T| + 4)`
  (multiplicative — the recursion depth is bounded by the `(entity × relation)` state
  space, not their sum). Added `deep_grid` to the conformance corpus as a permanent
  regression; conformance 33→36 green. The shallow original corpus is why it slipped
  past — lesson logged. No user adjudication needed (spec bug, clear resolution).

---

## Decisions & variations log

Variations from the plan (`docs/formal-verification-plan.md`) or from the repo's
own specs, with rationale. (The user asked that variations be documented.)

- **2026-07-09 — Phase 0 delivered as SEMANTICS.md + PROOF_STATUS.md + README.md**
  under `formal/`, matching plan §8.4 layout. No deviation.
- **2026-07-09 — Executable spec will use per-stratum fixpoint iteration, NOT the
  oracle's Tarjan-lowlink provisional-False control flow** (SEMANTICS.md §11-A2).
  Rationale: cleaner T0a/termination proof; agreement with the oracle asserted by
  conformance C1 rather than by matching control flow. The oracle is being demoted
  from ground truth to cross-check, so this is sound.
- **2026-07-09 — Non-stratifiable schemas are OUT of the verified envelope**
  (SEMANTICS.md §4.4). All theorems carry `stratify S = some strata`. This matches
  the security audit's recommendation to reject cyclic-through-boolean upstream.
- **2026-07-09 — User approved: "lgtm, write everything." A1 & A4 accepted as
  proposed.** Proceeding: Lean graph model bakes the cascade into write ops (A1);
  graph modeled at the connectedstore deduped-set boundary (A4).

### Phase 1 (Lean) decisions

- **Toolchain:** Lean `v4.31.0` (stable) + Mathlib pinned to tag `v4.31.0`, built
  against the prebuilt cache (`lake exe cache get`). `elan` installed to
  `~/.elan`. Project at `formal/lean/`, lib `ZanzibarProofs`.
- **`sem` is fuel-based and primitive-recursive on the fuel `Nat`** (§ Semantics.lean):
  `semAux (fuel+1)` = one immediate-consequence `step` applied to `semAux fuel`.
  `step` is parameterized by the sub-node answer function `rec`, so no
  termination entanglement; the boolean/leaf logic is all in `step`. Mirrors the
  oracle's depth-bounded provisional-False recursion. `sem` runs at `fuelBound`.
- **Binary `union`/`inter`** in the AST instead of n-ary (associativity + WF arity≥2
  make it faithful; no empty-fold fail-open). Logged in Schema.lean.
- **Backend models are `opaque` placeholders in Phase 1** (`SetEngineModel.check`,
  `GraphState`, `GraphModel.check`, `Inv`, `ReachedBy`, `Quiescent`,
  `GraphAccepts`). This keeps T1/T2/T5 non-vacuous (they relate an opaque model to
  `sem`, provable only once the model is concrete). Phases 3–4 replace the opaque
  declarations with real definitions. T3/T6a/T6b are ALREADY proved by `rw`
  through T1/T2b (so they become real the moment T1/T2b are discharged).
- **`stratify`/taint is an independent reimplementation** of `compute_taint` +
  `_stratify` (Kahn layering over derived-dependency edges). Fidelity to the Python
  is a Phase-2 conformance check, not assumed.
- **Reality check on "T0 is mechanical" (plan §9 P1):** it is NOT. `sem_fuel_stable`
  (T0a) rests on the stratified fixpoint being reached by `fuelBound` — a genuine
  theorem because exclusion is non-monotone in fuel. `stratify_*` (T0b) is Kahn
  correctness. Both are STATED (compiling) in Phase 1 with `sorry`; proofs are
  tracked and deferred rather than force-fit. `MemberSet.ext_normalize` IS proved.
- **T6c (`wildcard_scoping`)** is a trivial `rfl` placeholder to be refined to the
  precise scoping statement in Phase 5.

---

## Key facts a fresh session must not re-derive

- The spec `sem` = **stratified Datalog¬ perfect model, queried pointwise** — both
  backends compute it; equivalence is a corollary (`theory.md:192-198`).
- The oracle (`tests/oracle.py`) is the operational reference we are *replacing* with
  the Lean executable spec; it becomes a cross-check, not a proof target.
- **I9 (fixpoint audit) is test-suite-only**, not per-commit — so cascade-runs-in-txn
  is an assumed precondition (SEMANTICS.md §7.8, §11-A1). Most load-bearing fact.
- The counting theorem (T4) is sound **only because cycles are rejected** — the group
  `(ℤ,+)` inverse argument fails with cycles (`theory.md:57-61`). Rejecting cyclic
  schemas is a *necessity*, not a policy.
- Toolchain (elan/Lean/lake) is **not yet installed**; installing requires user
  permission (repo rule). Lean lives outside the conda env; conformance harness runs
  under the `graph-reachability-zanzibar-index` conda env.
- Python is READ-ONLY for this project except test-only conformance code under
  `formal/conformance/` (plan §8.3).
