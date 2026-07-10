# PROOF_STATUS.md — living status / ledger / adjudications

The session-persistent brain for the formal-verification build (plan §8.3). Update
this before ending ANY session. A fresh session should read, in order:
`docs/formal-verification-plan.md` → this file → `formal/SEMANTICS.md`.

---

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
