# `P6` part (iv) step 4′ — the scouting map (2026-09-15)

**ACTIVE-PLAN** (`docs/README.md` §3). Corrections are appended **dated at the top** of the
correction section; FROZEN when `P6` closes. Supersedes nothing — it is the measurement
[`docs/p6-part-iv-plan-2026-09-14.md`](p6-part-iv-plan-2026-09-14.md) § *"Still not
established at this line"* (the 2026-09-15 *eighth* correction) explicitly owed before step
4′ could be planned.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

All line numbers are **2026-09-15 snapshots of `a186419`** and will rot; the `file::symbol`
is the durable anchor. Every claim carries a provenance label: **READ** (top-level session
opened the file), **KERNEL/PROBE** (a rc=0 artifact in `formal/probes/`), **READ(agent)** (a
subagent read it and an adversarial verifier independently confirmed it — *not* re-checked
first-hand), **REASONED**, **UNVERIFIED**.

---

## Corrections appended 2026-09-15c (first) — blockers 1 and 4 are KERNEL-SETTLED

One new artifact, rc=0, literal transcript and a two-arm mutation sweep in its header:
[`formal/probes/p6_partiv_blocker1_kernel_2026-09-15.lean`](../formal/probes/p6_partiv_blocker1_kernel_2026-09-15.lean).
No Lean source under `formal/lean/` changed. All five findings below are **KERNEL/PROBE**.

**(a) BLOCKER 1 — all four REASONED verdicts CONFIRMED, and each is refuted by the SAME
single edge.** `¬ (conclusion)` is proved in the kernel for `reachedByRulesAdmitted_edge_
target_ne_wAny` (V1), `reachedByRules_edge_sound` (V2), `reachedByRulesAdmitted_edges_plain`
(V3) and `rulesAdmitted_edge_endpoints_bs` (V4), at a state the twin's own `step` reaches
(`FoldAdmitsBridged`, `by decide`). **Blocker 1 is closed.**

**Gate-pin status of the five casualties, grepped first-hand in `formal/audited_theorems.txt`
2026-09-15c** — this is what makes the ADDITIVE twin affordable, so record it with the
verdicts rather than re-deriving it at step 6:

| lemma | in `audited_theorems.txt` |
| --- | --- |
| `RulesCorrect.lean::reachedByRules_edge_sound` | **YES** |
| `RulesBareStar.lean::rulesAdmitted_edge_endpoints_bs` | **YES** |
| `RulesComplete.lean::reachedByRulesAdmitted_edges_plain` | no |
| `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_ne_wAny` | no |
| `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_notLeaf` | no |

All five remain TRUE of the plain `ReachedByRulesAdmitted`, which an additive twin does not
touch — so the two gate-pinned names are **not** a 4′ cost. The exposure is the reverse: the
three UNPINNED ones can be weakened silently while twinning, and two of them
(`…_ne_wAny`, `…_notLeaf`) are exactly the ones step 7 has to restate.

**(b) V2 survives neither its domain repair.** Swapping the existential's domain from
`rewriteClosure S t` to the twin's own `rewriteClosureL S (rawWriteTuples S t)` does NOT
rescue `reachedByRules_edge_sound` — the bridge edge is not any closure member's grant edge.
The shape that DOES cover it is the third disjunct `UsStarWrite.lean::foldl_writeBridgedOne_
edges_sound` already carries (pinned positively as `::v2c_third_disjunct_covers_the_witness`).
So **sub-step 6 is "lift the existing three-disjunct fold lemma", not new mathematics at the
disjunct level** — a narrowing of that step's `(L)` sizing.

**(c) ★ `LeafRules.lean::SlBridgeWitness`'s STORE IS NOT `StoreValidRules`-VALID** (measured
`false`). The concrete subject `group:g1#member` matches no restriction, because the schema
declares `group#member` WILDCARD-only — the same trap the (ninth) correction's grid hit at
`WideWitness.SwT`. None of V1–V4 carries that premise so the refutations stand, but
`::graph_correct_rulesBS` does. The probe's **fixture B** (`SlBridgeSV` = the fixture plus
one extra CONCRETE restriction, wildcard flag retained) closes it: every premise of all four
lemmas true, all four still refuted. ⚠ **Do not cite `SlBridgeWitness` alone for a
fragment-relevance claim.**

**(d) ⚠ BLOCKER 4 IS THE WRONG QUESTION, and its lemma is a FIFTH false one for a DIFFERENT
reason.** Its own question is answered **YES** (fixture C: `Core/Schema.lean::WF` constrains
declared relation KEYS only, so a schema may declare `[doc:*#viewer.0]` at a minted
`Leaf.lean::leafPred` name, and `UsStarWrite.lean::bridgePre`'s OBJECT-side call then bridges
to `w_any(doc, viewer.0)`). But `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_
target_notLeaf` does not need it: it is already false at `SlBridgeWitness` itself, refuted by
the ordinary **LEAF GRANT edge** `group:g1#member → doc:d1#viewer.0`. The bridge edge does
not refute it there at all (bridge target pred is the declared `member`). The separating
control: with the wildcard flag OFF — nothing bridged anywhere — `notLeaf` is **still false**.
**So `notLeaf` is falsified by the twin's ROUTING, one fold step before bridging is reached.**
⚠ **Do not carry this as a 4′ cost.** It is a cost of leaf ROUTING, which part (ii) already
landed — `LeafRules.lean::writeRulesRaw` falsifies `notLeaf` today, bridging or not. And it
is NOT repaired by step 7's `¬ σ0.bridgedInConcrete a` scope, which is the right instrument
for `::…_edge_target_ne_wAny` (its counterexample IS at a bridged source) and the wrong one
here (this counterexample's source is bridged at fixture A by coincidence, and is not bridged
at all under the flag-off control, where `notLeaf` still fails). Step 7 must therefore cover
two lemmas with two different repairs; it is amended in place below. Its ⚠ "not in
`audited_theorems.txt`, so a silent weakening costs no gate pin" is now MORE urgent, not less
— and it applies to `notLeaf` too, which I also grepped: **also absent** from
`formal/audited_theorems.txt`.

**(e) INSTRUMENT, three notes.** (i) `WF` is not `decide`-able here: `relNameOK` is
`¬ String.contains name '.'` and `String.contains → String.anyAux` is well-founded recursion
that does not reduce in the kernel. The probe's `relNames` pins are the `toList.contains`
formulation (character-identical to `isLeafPred`'s body), labelled as such. (ii) ★ **`TK68`
fired inside the probe itself**: arm `M1` first showed only 2 reds because the four
refutations consumed a NAMED helper for their witness, and Lean admits a failed declaration
at its stated type — so a mutation that DESTROYED the witness left the claims green. Every
refutation now proves its membership inline, off the primitive; the re-run gives 6 reds.
(iii) A Windows/Git-Bash path trap worth carrying: `/tmp/x` in the **Bash tool** is
`C:\Users\user\AppData\Local\Temp\x`, but a Windows `python` invoked from that same shell
reads `/tmp/x` as `C:\tmp\x`. A sweep script that writes its mutation with `python` and runs
it with `lake` therefore mutates one file and builds another — an all-green sweep of an
unmutated file. Use the Windows path in the `python` half, and assert the anchor matched.

---

## ★ The three things this session settled, and the one that decides the route

### 1. The route is CONFIRMED, on equivalence grounds — `PROBE`

[`formal/probes/p6_partiv_python_bridge_parity_2026-09-15.py`](../formal/probes/p6_partiv_python_bridge_parity_2026-09-15.py)
(rc=0). **The shipped Python bridges on the rule-routed write path; Lean's
`RulesWrite.lean::GraphState.writeRules` does not.** On the star-tupleset store, written
through the shipped analogue of the Lean fold (`ruleset.apply(triple)` →
`WildcardIndex.add_tuple`, i.e. `tests/test_matrix.py::GraphBackend._derived`), the edge
list contains

```text
(('viewer', 'folder', 'f1', ''), ('viewer', 'folder', '*', 'any'), 1, 1)
```

— byte for byte the in-bridge `folder:f1#viewer → w_any(folder,viewer)` that
`p6_partiv_step3_rulerouted_2026-09-15.lean` line (8) had to add **by hand** with
`ensureInBridges` to make `GraphModel.check` agree with `sem`. `check = True`, and the
independent oracle agrees. CONTROL b (concrete parent): `bridged_in_shapes` is empty, no
`w_any` edge, still correct — so the bridge is attributable to the STAR parent.

**This closes the sweep's blocker 6, which was the one that could have invalidated R1**, and
it closes it in R1's favour. It also **REFUTES the rival design the sweep's blocker 3 asked
to re-price** ("write a `FoldAdmitsBridged → FoldAdmits` transfer lemma and keep σ0
unbridged"). That rival is cheaper and leaves four currently-true lemmas true, but it
preserves a model of an algorithm *the shipped code does not run*. `CLAUDE.md`: *"A proof
that describes something other than the shipped code is a proof of nothing."* Decided here
per § *"Who decides"*; do not re-litigate on cost.

### 2. (C)'s payoff holds over a GRID, not one witness — `PROBE`

[`formal/probes/p6_partiv_stepC_grid_2026-09-15.lean`](../formal/probes/p6_partiv_stepC_grid_2026-09-15.lean)
(rc=0), the other measurement the eighth correction owed. On a store-valid star-tupleset
corpus under `WideWitness.SwT`, over a **175-distinct-query** routing-independent grid
(`182` raw; `25` answered TRUE by `sem`, so it is not vacuous):

| leg | mismatches vs `sem` | role |
|---|---|---|
| bridge-free `writeRules` fold | **6** | POSITIVE CONTROL / instrument — must be nonzero |
| bridged `writeRulesRaw` fold | **0** | ★ the number |
| CEILING (`ensureInBridges` over every node) | **0** | bounds what *any* write model could reach |
| REGRESSION (wrong bridged, right plain) | **`[]`** | the direction a net count hides |

The six repaired queries are exactly `{user:u, user:v, user:w} × {doc:d1, doc:d2} @ access`
— every grant through both star parents, i.e. the whole star-tupleset surface the corpus
exposes, not a corner of it. **`6 → 0 of 175`, no regression, and the ceiling says `0` is
optimal rather than merely better.**

⚠ **A failed control found a real defect in the instrument, and it is worth carrying.** The
first draft put a CONCRETE parent tuple in a `SwT` store — as
`p6_partiv_step3_rulerouted_2026-09-15.lean::tConc` does. That store is **not store-valid**:
`SwT` declares `doc#parent` as `[folder:*]`, the wildcard form *only*.
[`p6_partiv_stepC_diag_2026-09-15.lean`](../formal/probes/p6_partiv_stepC_diag_2026-09-15.lean)
(rc=0) measures it: `storeValidRulesB SwT [tConcPar] = false`, and at such a tuple
`sem = false` while `check = true` on **both** legs — a store-validity violation wearing the
costume of a divergence, contaminating every leg equally and making CONTROL b read `4`
instead of `0`. The concrete-parent control belongs on `WideWitness.SwTn`. The step-3
probe's own CONTROL b is on an invalid store; it is **not wrong** (it asks only the derived
query, where all three agree) but it is weaker than it looks. Recorded, not silently fixed.

### 3. The recorded "40 vs 24" — half reproduces, half is stale — `READ`

[`formal/probes/p6_partiv_cone_census_2026-09-15.py`](../formal/probes/p6_partiv_cone_census_2026-09-15.py)
(rc=0), written and run first-hand by the top-level session as an **independent instrument**
against the six agents' reports. It carries an `M0`-style `check_instrument` control that
refuses to print numbers if the matcher cannot see each symbol in its own defining module —
added because its **own first run reported zero code references for every `GraphState`
method**, the regex having excluded a preceding `.` and so missing every `σ.writeRules` call.
A broken harness wearing the costume of a finding, caught by the control.

Under the unit *transitive reverse import closure, excluding self and the root aggregator*:

| symbol | recorded | measured 2026-09-15 | code-ref modules | declarations |
|---|---|---|---|---|
| `writeRules` | 40 | **40** ✓ | 7 | 18 |
| `writeBridgedOne` | 24 | **32** ✗ (stale by 8) | 5 | 52 |
| `writeRulesRaw` | — | 21 | 5 | 22 |
| `ReachedByRulesAdmitted` | — | 32 | **13** | **86** |

The "24" was **exact on its own date** and went stale on 2026-09-14 when `RulesBareStar.lean`
gained `import ZanzibarProofs.GraphIndex.UsStarWrite`. The asymmetry the `LeafRules.lean`
docstring cites to justify keeping `writeRules` bare has shrunk from ~1.7× to ~1.25×.

**Two independent instruments agree.** The top-level census and the agents' (which used a
different stripper and a different BFS) return the same 40 / 32, the same 7 code-ref modules
for `writeRules`, and the same **13 modules / 86 declarations** for `ReachedByRulesAdmitted`.
That agreement is why the cost figures below are labelled READ rather than READ(agent).

⚠ **And the cone is the wrong cost metric anyway.** 28 of the 41 cone modules never mention
the string. What governs step 4′ is that `ReachedByRulesAdmitted.step`'s conclusion is
*definitionally* `σ.writeRules S t` — so the fold cannot be swapped at the shadow site at
all. See § *The anatomy of the cut*. **Declared additively, the existing repair set is 0, not
86** — that is what makes R1 affordable.

---

## How the sweep was run, and what it cost

Thirteen agents: six independent measurements (reverse cones ×2, the
`ReachedByRulesAdmitted` census, the shadow anatomy, the three stale assertions, the
shadow-swap blast radius), each then attacked by a dedicated adversarial verifier, then one
reconciling synthesis. 1.64M subagent tokens, 437 tool calls, 0 errors. **Every one of the
six measurements came back `PARTLY_REFUTED`** — the verify layer corrected a load-bearing
number or citation in all six, which is the argument for keeping it.

Standing constraint given to every agent, and the reason no build appears below: **no agent
was permitted to run `lake`**, because concurrent builds share one build directory. All
agent findings are therefore static reads. Every "this proof would break" verdict in the
body is consequently **REASONED, not kernel** — see blocker 1.

---

# The reconciled sweep

*What follows is the synthesis agent's reconciliation of the twelve measurement/verify
reports, retained substantially as written. It was directed to reconcile contradictions
rather than average them, and to say which side it believed and why. The top-level session
has verified first-hand the items marked READ in its § Provenance; the rest stand as
READ(agent). Corrections made by the top-level session after the sweep are inline and marked
**[TOP-LEVEL 2026-09-15]**.*

**[TOP-LEVEL 2026-09-15]** Two corrections to the body below, both from § *The three things
this session settled*: (a) blocker 6 is **SETTLED**, not unverified — the Python bridges, see
§1 above; (b) blocker 3's recommendation to re-price the unbridged-σ0 rival before committing
to R1 is **declined on equivalence grounds**, not on cost — see §1. Read those two before
acting on the corresponding rows.

### The headline

Re-measured first-hand at HEAD `a186419` on 2026-09-15 (70 `.lean` nodes, 219 internal `import ZanzibarProofs` edges, no build run): **the recorded "40 modules vs 24" is half-right, half-stale, and stated in two units that differ by one.** `RulesWrite.lean`'s transitive *reverse* import closure is **41 modules excluding the target / 40 excluding target+root aggregator / 42 including the target** — and it has been exactly those numbers, with an identical member list, at every rev I checked from `bd77fce` through HEAD. So the "40" reproduces exactly under "excl-self + excl-`ZanzibarProofs.lean`". The "24" was **exact on its own date** (`bd77fce`/`30ad44a`/`bff9297`, 2026-09-13: `UsStarWrite` reverse cone = 24 excl-self / 23 excl-root) and is now **stale by 9**: 25 at `af92af0`, **33 excl-self / 32 excl-root / 34 incl-self at `7735ab1` and HEAD**, the jump caused by `RulesBareStar.lean` gaining `import ZanzibarProofs.GraphIndex.UsStarWrite`. The asymmetry the docstring cites as "why the asymmetry is deliberate rather than lazy" has therefore gone from **~1.7×** (40:23 / 41:24) to **1.24×** (41:33) or **1.25×** (40:32) — and reverse-cone size is the wrong cost metric anyway: only **7 of 70 modules carry a code-level bare `writeRules` reference** (27 occurrences, comment-stripped, first-hand) and 28 of the 41 cone modules never mention the string. The cost that actually governs step 4′ is not the cone at all: it is that `RulesComplete.lean::ReachedByRulesAdmitted.step`'s conclusion is *definitionally* `σ.writeRules S t`, so 4′ is an edit to an inductive with **120 code-level references across 13 modules / 86 declarations / 46 of them gate-pinned names** — unless the twin is declared **additively**, in which case the existing repair set is **0**.

### Reconciled measurements

Legend: **READ** = I (top-level) opened the file and saw it; **READ(agent)** = an agent read it and its verifier independently confirmed it, not re-checked by me; **REASONED**; **UNVERIFIED**.

### Angle `cone:writeRules` (cone-rules-write)

| Claim | Verdict after attack | Prov. |
|---|---|---|
| `RulesWrite` reverse cone = 41 excl-self / 40 excl-root / 42 incl-self, stable since 2026-09-06 | **CONFIRMED.** I re-derived it independently (own BFS, 70 nodes / 219 edges) at HEAD and at `bd77fce`,`30ad44a`,`bff9297`,`af92af0`,`7735ab1`: 41/40 at every one. | READ |
| "40 vs 24 were computed under DIFFERENT conventions … never 40-vs-24 under one unit" | **UNIT_AMBIGUOUS — I believe the verifier over the measurement, but only barely.** At `bd77fce` I measured RW 41/40 and US 24/23, so the two *natural* units give (41,24) or (40,23), never (40,24) — the measurement is right about that. But the verifier's counter-rule is arithmetically live and I checked it first-hand: `GraphIndex.LeafRules` ∈ cone(RulesWrite) and ∉ cone(UsStarWrite) at `bd77fce`, so "excl-self + excl the file the claim is written in" yields **(40, 24) simultaneously**. I believe the pair is *unit-ambiguous, not provably mixed*, because exactly one consistent rule reproduces it and I cannot recover the 2026-09-13d probe script to tell intent. **It does not matter for the plan** — under every unit the live pair is 41:33 or 40:32. | READ |
| "`RulesSound`'s import cone is 29 modules (LeafRules.lean:6) does not reproduce — I measure 16" | **WRONG — I believe the verifier, and I confirmed it myself.** Forward closure of `GraphIndex.RulesSound` = **16 ZanzibarProofs + 13 external (Mathlib/Aesop/Lean) = 29 exactly**; `GraphIndex.ReconcileCorrect` = **22 + 13 = 35 exactly**, matching the third recorded figure at `LeafRules.lean:1458`. Two exact hits under one unit is not coincidence. The real defect is that **`LeafRules.lean` carries two undeclared cone conventions**: the 2026-09-05 notes count ZP+external, the 2026-09-14 note (`:14-21`) counts ZP-only (`UsStarWrite` fwd = 9 — I measure ZP-only 9, ZP+ext 18). | READ |
| Decoy row "`writeBridgedOne` — 159 occurrences in 5 modules" | **WRONG.** First-hand: bare identifier = **124 textual / 79 code, 5 code modules**; substring family = **251 textual / 166 code, 8 modules**. 159/5 reproduces under no unit I tried. | READ |
| 18 proof sites / 7 code-level modules for bare `writeRules`; 121 decls / 20 modules for the `ReachedByRules*` family | **CONFIRMED** by the verifier with an independent stripper; my own comment-stripped pass gives **27 bare-`writeRules` code occurrences in 7 modules** (73 textual / 14 modules bare; 84 / 15 under `writeRules(?!Raw)`, which additionally catches `structInv_writeRules`-style lemma names). Three honest numbers, three units. | READ |
| Scratch4cii is build surface but not pin surface | **CONFIRMED** (verifier: `ZanzibarProofs.lean:86` imports it; no `audited_theorems.txt` row, no `Audit.lean` `#print axioms`). Count it as compile surface (17 downstream sites, not 14). | READ(agent) |
| Gate-pinned surface outside the 70-file universe: `audited_theorems.txt`, `CORRESPONDENCE.md` anchors, `formal/probes/*.lean` | **CONFIRMED and extended by me.** `formal/audited_theorems.txt` rows I grepped first-hand: `GraphState.writeRulesRaw`:25, `graph_correct_rules`:263, `graph_correct_rulesBS`:264, `inv_writeRules`:285, `reachedByRulesAdmitted_edge_complete`:368, `reachedByRulesAdmitted_seed_edge`:369, `reachedByRules_edge_sound`:370, `reachedByRules_inv`:371, `reachedByRules_of_admitted`:372, `reachedByW3d_shadow`:433, `shadow_graphRec_agree`:535, `structInv_writeRules`:558, `writeRulesRaw_untaintedSchema`:631. **NOT pinned:** `reachedByRulesAdmitted_edge_target_ne_wAny`, `bridgeNode_nonvacuous`. | READ |

### Angle `cone:writeBridgedOne` (cone-bridged)

| Claim | Verdict after attack | Prov. |
|---|---|---|
| cone(UsStarWrite) = 33 / 32, not 24; history 9→24→25→33 | **CONFIRMED twice over** — verifier by an independent awk BFS, and by me: `bd77fce`/`30ad44a`/`bff9297` = 24/23, `af92af0` = 25/24, `7735ab1`/HEAD = 33/32. | READ |
| The 8 modules added at `7735ab1` include `UsStarClosure`/`UsStarCorrect` | **WRONG** — verifier's `comm` shows those two predate the jump; the 8 are `ReconcileComplete, ReconcileDiff, ReconcileStars, ReconcileStarsComplete, ReconcileUpos, ReconcileUposComplete, RestrictBase, RulesBareStar`. I believe the verifier: `UsStarCorrect` is a *direct* importer of `UsStarWrite`, so it cannot have been outside the cone. | REASONED |
| Ratio "1.25× not 1.67×" | **UNIT_AMBIGUOUS.** 1.67 was never a real ratio under any consistent unit; consistently it was 1.74× (40:23) or 1.71× (41:24) and is now 1.24–1.25×. The direction holds; the baseline was understated. | READ |
| Import cycle: `writeRulesRaw` cannot be substituted at `RulesWrite.lean::ReachedByRules.step`; `RulesComplete` is the tractable site | **CONFIRMED first-hand by me.** `fwd(LeafRules) ∋ RulesWrite` = True (via `Leaf.lean:2`); `fwd(RulesWrite) ∋ LeafRules` = False. `RulesComplete`↔`LeafRules`: **both False** ⇒ acyclic. `RulesComplete`↔`UsStarWrite`: **both False** ⇒ also acyclic. `RulesComplete`'s only direct imports are `RulesChain`, `RulesSaturate`. | READ |
| "Repair set = 13 modules" for the `RulesComplete` substitution | **UNIT_AMBIGUOUS.** The cone intersection filtered nothing — all 13 are already inside cone(RulesComplete). State it as **13 modules / 120 non-comment sites / 86 declarations**, recompile set 34 nodes. My own census independently gives 13 code modules and 120 code occurrences. | READ |
| `writeRulesRaw_untaintedSchema` has no consumer | **CONFIRMED** (only its own decl at `LeafRules.lean:403` and `Audit.lean:1989`). | READ(agent) |
| `writeBridgedOne` has no `#print axioms` row; only `CORRESPONDENCE.md` anchors would red the gate — cited at `:1321` | **CONFIRMED on the pin, WRONG on the count.** `grep -n writeBridgedOne formal/CORRESPONDENCE.md` returns **5 lines (312, 964, 979, 1321, 1331)**, three of them `file::symbol` anchors the `lean` phase resolves. A rename reds the gate at **three** anchors. | READ |

### Angle `census:ReachedByRulesAdmitted` (admit-twin)

| Claim | Verdict after attack | Prov. |
|---|---|---|
| 86 declarations / 13 modules / 120 code lines reference `ReachedByRulesAdmitted`; 46 gate-pinned | **CONFIRMED** by the verifier with an independent stripper and by my own comment-stripped pass: **120 code occurrences in exactly 13 modules, 149 textual in 17**. | READ |
| 5 elimination sites, 8 `.step` / 6 `.empty` construction sites | **CONFIRMED** by both verifier routes. | READ(agent) |
| 43 upstream / 43 at-or-downstream of `Cascade.lean` (where `FoldAdmitsBridged` lives) | **CONFIRMED.** I re-derived the load-bearing direction myself: `fwd(RulesComplete) ∌ Cascade`, `fwd(Cascade) ∋ RulesComplete` — so `RulesComplete`, `RestrictBase`, `RulesBareStar`, all four `Reconcile*Complete` modules **cannot see `FoldAdmitsBridged` in place.** | READ |
| "`FoldAdmits` = 33 code lines across 8 built modules" | **WRONG on the module count — I believe the verifier.** Its own 7-entry list sums to 33. My pass: **34 bare occurrences / 7 code modules; 74 textual / 9 modules**; 12 files contain the substring (3 only via `FoldAdmitsBridged`). Add the unit the measurement omitted: **26 declarations**. | READ |
| "The built library is 17 modules" | **WRONG.** 17 is the count of modules with any `ReachedByRulesAdmitted` reference. The library is 68 (root + 67-module closure), 69 with `Audit.lean` which `verify.sh` builds explicitly, 70 files counting `Cli.lean`. | READ(agent) |
| Blast radius is 86/46 | **UNIT_AMBIGUOUS — I believe the verifier's three-number framing.** If the twin *replaces* RBRA, the one-hop closure through the six embedding wrappers (`ReachedByW3aAdmitted`, `ReachedByW3b`, `ReachedByW3c`, `W3aComplete`, `W3bComplete`, `W3cComplete`) is **134 declarations / 83 pinned names**. If the twin is **ADDITIVE**, the existing repair set is **0**. The plan says "a bridged *twin*", so 0 is the number the plan is actually buying — and that is the single most important correction in this document. | REASONED |
| `verify.sh` step 4 has three pins (4a names, 4b statements, 4c definitions); neither `headline_statements.txt` nor `headline_definitions.txt` mentions any of the 86 | **CONFIRMED** by the verifier. Useful negative result; no 4b/4c exposure. | READ(agent) |

### Angle `anatomy:shadow` (shadow-site)

| Claim | Verdict after attack | Prov. |
|---|---|---|
| `CascadeStable.lean:3735` is not a definition — it is the `write` branch's `exact` term inside `::reachedByW3d_shadow`, and `σ0.writeRules S t` is **forced** by `ReachedByRulesAdmitted.step` | **CONFIRMED first-hand.** I read both. This is the plan's principal factual error. | READ |
| Step 4′ makes `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_ne_wAny` **FALSE**, not merely unproved | **CONFIRMED first-hand.** Its step case (`:758-759`, snapshot) rewrites the goal to the `writeDirect` fold and closes with `objNode_ne_wAny`; `UsStarWrite.lean::GraphState.ensureInBridges` (`:296-303`) executes `addEdge c (wAnyNode (c.type, c.pred))`, so a bridged fold genuinely materialises a `wAny` target. 4 consumers (`:828`, `:836`, `:1538`, `:1547`). | READ |
| `ShadowOver` is a 6-field structure; `UntaintedShadow` already carries the third `BridgeNode` disjunct (so 5′ is a deletion); `classify` is covariant so its *producers*, not consumers, break | **CONFIRMED first-hand.** `CascadeStable.lean::ShadowOver` `:706-712`, `::UntaintedShadow` `:732-733` = `ShadowOver (fun k => DerNode S k ∨ LeafNode S k ∨ BridgeNode S k) σ σ0`. | READ |
| "`BridgeNode` = 47 occurrences, 2 modules" | **Both right, different units.** First-hand: exact predicate name **47 textual / 32 code**; whole `[Bb]ridgeNode` family **84 textual / 56 code**. **2 modules under both** (`CascadeStable.lean`, `CascadeStrataSettle.lean`). The verifier is right that 47 undercounts the deletion surface the report's own list describes. | READ |
| "the '24' most likely measured `writeRulesRaw`'s module (LeafRules cone 22/23)" | **REFUTED by me.** `UsStarWrite`'s cone was **exactly 24** at `bd77fce`/`30ad44a`/`bff9297`. The 24 measured what it said it measured; it went stale. Do not carry this conjecture forward. | READ |
| `shadow_graphRec_agree` has **two** three-branch `¬(…∨…∨…)` haves (`hv1` :3756, `hv3` :3814); the plan names only `hv1` | **CONFIRMED** by the verifier; 15 application sites in 13 decls across 5 modules, against a stale in-file comment saying "14 sites" (`CascadeStable.lean:3812`, and again at `Leaf.lean:653`). | READ(agent) |
| Doc drift at the surgical site = 3 stale statements | **WRONG — 4.** Verifier adds `GraphIndex/Scratch4cii.lean:511-512`. I confirmed the `UntaintedShadow` docstring (`:714-717`) still says "RE-POINTED at `DerNode ∨ LeafNode` by 4c-ii" against a live 3-disjunct body. | READ |
| "23 declarations PRODUCE a ShadowOver witness" | **UNVERIFIABLE** — hand count over line ranges. Use the reproducible figure instead: **19 top-level `untaintedShadow_*` theorems** (9 `CascadeStable` + 10 `CascadeStrataSettle`), of which exactly **2 terminally consume `hT`** (`::untaintedShadow_ensureInBridgesLogged` :2945, `::untaintedShadow_writeLegL` :3250). | UNVERIFIED |

### Angle `verify:stale-assertions` (stale)

| Claim | Verdict after attack | Prov. |
|---|---|---|
| All three flagged assertions exist, are PROSE (two `--` comments, one `/-! -/`), none is a theorem | **CONFIRMED first-hand.** See § *Stale assertions to fix*. | READ |
| The chain is five hops, not four | **CONFIRMED first-hand.** I read all five bodies: `Cascade.lean::GraphState.writeLoggedRules` :555-556 → `::writeLoggedOne` :532-536 → `::bridgePreLogged` :508-511 → `::ensureInBridgesLogged` :217-219 → `UsStarWrite.lean::GraphState.ensureInBridges` :296-303. `ensureInBridgesLogged`'s body calls `σ.ensureInBridges c` in **both** branches. | READ |
| Stale prose sites = 8 | **WRONG — ≥12.** I believe the verifier: it adds `Audit.lean:2016-2021` (a *sabotage-attribution* record whose premise was the inertness), `Cascade.lean:262-264`, `CascadeInv.lean:128-131`, and `formal/CORRESPONDENCE.md:1313-1320`. I confirmed `Audit.lean:2016-2021` first-hand — it is a separate claim from `:2012-2015` and needs a **re-run, not a reword**. | READ |
| "bridge-free survives ONLY for `RulesWrite::writeRules`" | **WRONG.** Verifier finds a second bridge-free schema-level fold: `GraphIndex/Leaf.lean::GraphState.writeDirectRaw` (`:806-807`), zero `ensureInBridges`/`bridgePre` hits in that file. Three units: 2 bridge-free schema-level folds / 1 bridge-free per-tuple primitive (`Write.lean::writeDirect`) / 1–2 "live legs" depending on adjudication. | READ(agent) |
| `Cascade.lean:185` is "stale for BOTH definitions it covers" | **WRONG — I believe the verifier and confirmed it first-hand.** The block names **three** compositions; two landed, and the third ("`ensureInBridges` into the unlogged `RulesWrite.lean::writeRules` twin, so `EvalEq` survives") did **not** — re-point #2 went into `LeafRules::writeRulesRaw` instead, and `writeRules` was deliberately left bare. Rewriting it as "LANDED" would erase a deliberate asymmetry. Also `GraphState.releaseInBridges` (unlogged, `Cascade.lean:249`) genuinely still has zero production callers — a sweep-fix would make a true statement false. | READ |
| "`writeLoggedRules` folds `writeBridgedOne`" | **WRONG (substring conflation), and the same error is already baked into `CORRESPONDENCE.md:962-965`.** `writeLoggedRules` folds `writeLoggedOne`; it reaches `ensureInBridges` via `bridgePreLogged`→`ensureInBridgesLogged`. Two independent bridged legs, not one nested in the other. The *assertion* is still stale — `writeLoggedRules` does transitively call `ensureInBridges` — but the corrected wording must not repeat this. | READ |

### Angle `blast:shadow-swap` (blast)

| Claim | Verdict after attack | Prov. |
|---|---|---|
| Step 4′ cannot be a local substitution; `hadm` moves too (`FoldAdmits` → `FoldAdmitsBridged`) | **CONFIRMED first-hand.** `RulesComplete.lean::ReachedByRulesAdmitted.step` carries `(hadm : FoldAdmits σ (rewriteClosure S t))` at `:115` and concludes at `:116`. | READ |
| 4 lemmas outright falsified: `reachedByRulesAdmitted_edge_target_ne_wAny`, `reachedByRulesAdmitted_edges_plain`, `rulesAdmitted_edge_endpoints_bs`, `reachedByRules_edge_sound` | **PLAUSIBLE, not kernel-checked.** All four statements read first-hand or by two agents; the falsifier (`LeafRules.lean::SlBridgeWitness.writeRulesRaw_creates_the_bridge` `:2140`, `by decide`) exists and its target `wGrp = wAnyNode ("group","member")` has `variant = wAny`. **This is the strongest REASONED claim in the whole sweep and it is the one to probe first.** | REASONED |
| "4 gate-pinned names touching this change" | **WRONG.** First-hand: **13 rows** match `writeRules|ReachedByRules|reachedByRules` in `audited_theorems.txt`, including all five `reachedByRules*` rows the measurement omitted — one of which is `reachedByRules_edge_sound`, its own "deepest casualty". | READ |
| "82 RBRA statements across 14 modules (incl. Scratch4cii)" | **WRONG — 13 modules.** All three `Scratch4cii` hits are inside the `/-! … -/` block opening at `:419`. My comment-stripped pass agrees: 13. | READ |
| 28 code call sites of `reachedByRules_edge_sound` in 9 consuming modules | **CONFIRMED.** My pass: 41 textual / **30 code occurrences in 11 code modules**; minus the defining line (`RulesCorrect.lean:125`) and `Audit.lean:270` = **28 in 9 consuming modules**. | READ |
| "every one of those 28 becomes a 3-way `rcases`" | **WRONG.** Only **9** are `obtain ⟨…⟩ :=` destructurings; the other 19 are term-mode applications that break by result-type change. All 28 still go red; the repair *shape* estimate was wrong. | READ(agent) |
| All 5 lemmas in `LeafRules.lean:427-449` are **already** discharged by `*_foldl_writeBridgedOne` | **CONFIRMED.** So the docstring's "cheap re-point" is about a re-point that already happened; it does not transfer to 4′. | READ(agent) |
| 14 `foldl_writeDirect*` lemmas → 9 clean twins / 4 wider-or-new-premise / 1 binder mismatch; the bridged side carries no surplus | **CONFIRMED.** | READ(agent) |
| Fuel objection: `bridgePre`'s two unconditional `addNode`s shift `GraphState.reach`'s fuel, so `writeRulesRaw = writeRules` is unrecoverable under any premise | **CONFIRMED first-hand** against `LeafRules.lean::writeRulesRaw_untaintedSchema`'s docstring (`:377-386`, snapshot) and `UsStarWrite.lean::GraphState.bridgePre` `:357-359`. | READ |
| Open: does `ensureInBridges` ever create an **outgoing** edge from the `wAny` node (which would violate `ShadowOver.term` on the σ0 side)? | **SETTLED — NO.** I read `UsStarWrite.lean::GraphState.ensureInBridges` `:296-303` in full: every branch is `addNode (wAnyNode …)` or `addEdge c (wAnyNode …)`. Only the incoming edge. **`ShadowOver.term` is not a sixth blocker.** | READ |

### The anatomy of the cut

All line numbers are **2026-09-15 snapshots of `a186419`** and will rot; every `file::symbol` was grepped and resolves.

**The 4′ site — and what the plan gets wrong about it.** The plan says *"4′ BRIDGE THE SHADOW: `CascadeStable.lean:3735`'s `writeRules` → `writeRulesRaw`"*. That is not an available edit.

- `formal/lean/ZanzibarProofs/GraphIndex/CascadeStable.lean::reachedByW3d_shadow` — decl `:3611` (snapshot); goal `∃ σ0, ReachedByRulesAdmitted σ0 S T ∧ UntaintedShadow S σ σ0` at `:3624`; the `write` branch's witness at **`:3735-3739`** reads verbatim
  `exact ⟨σ0.writeRules S t, ReachedByRulesAdmitted.step t h0 hadmV, untaintedShadow_writeLegL hTshadow hSshadow (rewriteClosureL S (rawWriteTuples S t)) (rewriteClosure S t) σp σ0 hsh (reachedByW3d_schema hprev) hsubjWL hextraL hsubL hadm hadmV⟩`.
- The first component is **forced** by the second. `formal/lean/ZanzibarProofs/GraphIndex/RulesComplete.lean::ReachedByRulesAdmitted` — inductive at `:111`, `| step` opening `:113`, `(hadm : FoldAdmits σ (rewriteClosure S t))` at `:115`, conclusion `ReachedByRulesAdmitted (σ.writeRules S t) S (t :: T)` at `:116`. Substituting `writeRulesRaw` in slot 1 type-errors against slot 2.
- **The real 4′ site is `RulesComplete.lean::ReachedByRulesAdmitted`, not `CascadeStable.lean:3735`.** The fold moves *and* the `hadm` binder moves: `FoldAdmits` cannot describe a bridged fold (kernel-refuted in-tree at `GraphIndex/Cascade.lean::FoldAdmitsHonestyWitness.foldl_edge_complete_is_false_for_the_bridged_fold`, `:2461`).
- There are **three** witness sites in the same shape, not one, and they must move together: `CascadeStable.lean::reachedByW3d_shadow` `:3735-3739`; `CascadeStrataSettle.lean::reachedByW3d2_shadow` `:955-959`; `CascadeStrataSettle.lean::reachedByW3d2_shadow_d` `:1770-1774` (its derived-key sibling at `:1726-1729` carries σ0 unchanged with `vs = []`).
- **Import geometry, verified first-hand.** `fwd(LeafRules) ∋ RulesWrite` = **True** (`LeafRules.lean:1` → `Leaf.lean:2`), so `RulesWrite` can never import `LeafRules` — the `ReachedByRules` inductive is structurally out of reach. `RulesComplete`↔`LeafRules` = **False/False** and `RulesComplete`↔`UsStarWrite` = **False/False**, so `RulesComplete` may import either acyclically. But `FoldAdmitsBridged` lives in `Cascade.lean` (`:1957`), and `fwd(RulesComplete) ∌ Cascade` while `fwd(Cascade) ∋ RulesComplete` — **the binder the twin needs is downstream of the module the twin must live in.** This is the hard structural blocker and it is not in the plan.

**The 5′ site.**

- `CascadeStable.lean::UntaintedShadow` `:732-733` = `ShadowOver (fun k => DerNode S k ∨ LeafNode S k ∨ BridgeNode S k) σ σ0`. The widening **is landed**, so 5′ is a one-line deletion — the plan is right here.
- `CascadeStable.lean::ShadowOver` `:706-712`: `classify` (`:707`) is **covariant** in `P`, `term` (`:712`) **anti-variant**. Shrinking `P` therefore makes consumers easier and only **classify producers** harder — the plan has this backwards.
- Exactly **two** generic proof sites terminally consume the `hT` obligation: `CascadeStable.lean::untaintedShadow_ensureInBridgesLogged` `:2945` and `::untaintedShadow_writeLegL` `:3250`. Both are generic in `Extra`, so they break only at the **three `hTshadow` instantiations**, which I verified first-hand: `CascadeStable.lean:3707`, `CascadeStrataSettle.lean:931`, `:1636`. At `DerNode ∨ LeafNode` those become unprovable (a `wAnyNode` is neither) — **so 5′ type-fails unless 4′ has landed first.**
- Also touched by 5′, from the anatomy list: `CascadeStable.lean::writeLegExtrasWide_L` `:3543-3556` (pure deletion, its own comment says widening-only); `::shadow_graphRec_agree` `hv1` `:3756-3774` **and** `hv3` `:3814-3827` (the plan names only `hv1`); `::reachedByW3d_shadow` `hsubjWL` `:3681-3689` / `hSshadow` `:3711-3729`; the `CascadeStrataSettle` twins at `:922-946` and `:1636-1640`/`:1710-1728`/`:1752-1762`; and the whole `bridgeNode_*` family (`::BridgeNode` `:640`, `::bridgeNode_wAnyNode` `:649`, `::bridgeNode_elim` `:658`, `::not_bridgedInConcrete_of_bridgeNode` `:673`, `::not_derNode_of_bridgeNode` `:684`, `::bridgeNode_nonvacuous` `:2500`) becomes dead. `formal/CORRESPONDENCE.md:982` carries a bare `` `::BridgeNode` `` anchor that `verify.sh` step 4d resolves (`formal/conformance/anchor_check.py::BARE_RE`), so deleting the predicate **reds the gate** until that paragraph is rewritten.

**The 7′ anchor is rotted.** The plan says *"flip `FullScope.lean:340` to `TtuStarFreeW`"*. First-hand: `formal/lean/ZanzibarProofs/FullScope.lean::W4Fragment` opens at **`:334`** and the field is `ttuStarFree : TtuStarFree S T` at **`:352`** (snapshot). `:340` is `directArmsConcrete`. The widened predicate `TtuStarFreeW` lives at `GraphIndex/RulesBareStar.lean:68` (moved there 2026-09-14i per `CORRESPONDENCE.md:312`), and `FullScope.lean` does not currently reach it — check the import direction before scheduling 7′.

### Ordered sub-steps for 4′

Ordering principle: **every additive step first, so the tree stays green until the single unavoidable re-point.** The tree goes RED for the first time at step 8.

1. **(S) Relocate the bridged admission predicate.** Move `GraphIndex/Cascade.lean::FoldAdmitsBridged` (`:1957`), `::decFoldAdmitsBridged` (`:1967`), `::instDecidableFoldAdmitsBridged` (`:1978`), `::foldAdmitsBridgedB` (`:1987`), `::foldAdmitsBridgedB_iff` (`:1995`) into `GraphIndex/UsStarWrite.lean`, immediately after `::GraphState.writeBridgedOne` (`:363`). **Why this is safe and why it is the key move:** I read the body — it needs only `bridgePre`, `writeBridgedOne`, `admitEdge`, `subjNode`, `objNode`, all in `UsStarWrite` or upstream. `Cascade` already imports `UsStarWrite`, so the move is transparent to its 8 current consumers. Leave `FoldAdmitsHonestyWitness` (`Cascade.lean:2361-2517`) where it is — *that* is what needs to see both predicates. **Expected breakage:** none. **Twin exists:** n/a. ⚠ This **overrides the in-tree placement note at `Cascade.lean:1942-1946`** ("Do not 'tidy' it up next to its subject"); that note's stated reason is about seeing `FoldAdmits` *and* `writeBridgedOne` together, which applies to the witnesses, not the definition. Record the override with this reasoning on the task row.
2. **(S) `import ZanzibarProofs.GraphIndex.LeafRules` into `GraphIndex/RulesComplete.lean`.** Acyclic — verified first-hand both directions. Transitively brings `UsStarWrite` (and hence step 1's relocated predicate), `writeRulesRaw`, `rewriteClosureL`, `rawWriteTuples`. **Breakage:** none; cost is cone growth (everything in `RulesComplete`'s 33-module reverse cone now transitively imports `LeafRules`/`UsStarWrite` — re-measure the asymmetry figures after this lands, they will move again). **Twin:** n/a.
3. **(M) Declare the twin ADDITIVELY.** New `GraphIndex/RulesComplete.lean::ReachedByRulesRawAdmitted` beside (not replacing) `::ReachedByRulesAdmitted`, with `| empty` and `| step … (hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t))) : ReachedByRulesRawAdmitted (σ.writeRulesRaw S t) S (t :: T)`. **Because it is additive, the existing repair set is 0 declarations, not 86** — this is the whole reason R1 is affordable. The binder shape is proven-workable: it is the shape `GraphIndex/Cascade.lean::ReachedByW3d.write` already carries (`hadm : FoldAdmitsBridged σ (rewriteClosureL S (rawWriteTuples S t))`, `:2058`, agent-READ). **Breakage:** none. **Twin:** n/a (this *is* the twin).
4. **(M) Twin the five state-invariant corollaries** onto the new inductive. `structInv_` / `residueEmpty_` / `inv_` / `quiescent_` / `_schema`. **Twin exists: YES ×5, already proved** — `UsStarWrite.lean::structInv_foldl_writeBridgedOne` `:798`, `::residueEmpty_foldl_writeBridgedOne` `:805`, `::inv_foldl_writeBridgedOne` `:812`, `::quiescent_foldl_writeBridgedOne` `:821`, `::schema_foldl_writeBridgedOne` `:828`. `LeafRules.lean:427-449` already discharges the `*_writeRulesRaw` layer with exactly these, so this is a name-swap. **Breakage:** none (additive).
5. **(S) Twin `reachedByRulesAdmitted_nodesFromEdges`** (`CascadeStrataSettle.lean:730`). **Twin exists: YES** — `UsStarWrite.lean::foldl_writeBridgedOne_nodesFromEdges` `:1341`, statement explicitly unchanged, no `edgesClosed` premise. One-name swap. **Breakage:** none (additive).
6. **(L) State the twin's edge-soundness law — this is new mathematics, not a swap.** `RulesCorrect.lean::reachedByRules_edge_sound` (`:125`) has a two-part existential; the bridged fold lemma `UsStarWrite.lean::foldl_writeBridgedOne_edges_sound` (`:937-942`) has a **third disjunct** `(σ.bridgedInConcrete a = true ∧ b = wAnyNode (a.type, a.pred))` with no existential. **Twin exists: partially** — the fold lemma exists; the `ReachedBy`-level lemma does not. **Breakage:** none yet (additive), but every downstream consumer of the twin inherits a third case. Budget against the 28 call sites / 9 modules of the *plain* lemma as the shape the twin's consumers will need, of which only 9 are `obtain`-destructurings.
7. **⚠ AMENDED 2026-09-15c (see § *Corrections appended 2026-09-15c*).** Its "FALSE, not
   unproved" premise is now KERNEL-confirmed (a), and **option (a) is the one the evidence
   supports**: the probe's `::v2c_third_disjunct_covers_the_witness` pins that the refuting
   edge's SOURCE satisfies `bridgedInConcrete`, so a `¬ σ0.bridgedInConcrete a` scope does
   discriminate the counterexample. **Also: this step must now cover a SECOND lemma it does
   not name** — `::reachedByRulesAdmitted_edge_target_notLeaf` (`:693`) is likewise false for
   the twin, but by leaf ROUTING rather than bridging (d), so the same scope does NOT repair
   it and it is already false of part (ii)'s landed `writeRulesRaw`.
   **(L) Decide the fate of `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_ne_wAny` (`:751`).** For the twin it is **FALSE**, not unproved. Two options: (a) restate for the twin with a `¬ σ0.bridgedInConcrete a` scope, (b) replace its 4 consumers (`:828`, `:836` in `::untaintedShadow_removeLeg`; `:1538`, `:1547` in `::untaintedShadow_removeLeg_d`). ⚠ **It is NOT in `formal/audited_theorems.txt`** (I grepped) — so a silent weakening here costs no gate pin and would not be noticed. **Run the sabotage procedure on whatever replaces it before believing it.** **Twin exists: NO.**
8. **(M) ⟵ THE TREE GOES RED HERE. Re-point the three shadow witnesses together**, in one commit: `CascadeStable.lean::reachedByW3d_shadow` `:3735-3739`, `CascadeStrataSettle.lean::reachedByW3d2_shadow` `:955-959`, `::reachedByW3d2_shadow_d` `:1770-1774` (+ the `vs = []` sibling `:1726-1729`). Each swaps `ReachedByRulesAdmitted.step`/`σ0.writeRules` for the twin, and `hadmV : FoldAdmits σ0 (rewriteClosure S t)` for `FoldAdmitsBridged σ0 (rewriteClosureL …)`. **Twin exists:** the `untaintedShadow_writeLegL` argument list is already L-list-shaped, so only the first two components move. **Breakage:** the 5 application sites of `reachedByW3d_shadow` (`CascadeEnum.lean:365`, `CascadeSettle.lean:566`, `:919`, `CascadeStable.lean:4130`, `:4132`) see a changed conclusion type and must be re-typed.
9. **(M) Retire or restate `CascadeStable.lean::foldAdmits_plain_of_L` (`:3572`).** Today it transfers L-list admission to plain-list admission precisely *because* `.step` wants the plain list; after step 8 its reason for existing is gone. ⚠ **This is where R1 and its cheaper rival meet** — see *Blockers*.
10. **(S) `formal/CORRESPONDENCE.md` in the same commit as step 8.** Add `file::symbol` anchors for the new twin; correct `:977-985` (the "still bridge-free, on purpose" paragraph, which step 4′ reverses as an adjudication), `:962-965` (the `writeLoggedRules`-folds-`writeBridgedOne` error), `:1313-1320` (uncorrected, contradicts `:956-985` in the same file by ~350 lines). `verify.sh lean` resolves every anchor, so this is gate-visible, not cosmetic.

Only after steps 1–10 are green: **3′** (additive widened twin of `RulesBareStar.lean::ttuLeaf_elim_nss`), then **5′** (delete `BridgeNode` from `UntaintedShadow` — a 2-module Lean deletion plus the `CORRESPONDENCE.md:982` anchor), then **6′**, then **7′** at the corrected anchor `FullScope.lean:352`.

### Blockers and unknowns

1. **SETTLED 2026-09-15c — ALL FOUR CONFIRMED IN THE KERNEL, plus a fifth; see § *Corrections
   appended 2026-09-15c* (a)/(b)/(c). The rest of this item is the pre-settlement text.**
   ~~UNVERIFIED (kernel): the four "outright FALSE" verdicts.~~ `reachedByRulesAdmitted_edge_target_ne_wAny`, `reachedByRules_edge_sound`, `RulesComplete.lean::reachedByRulesAdmitted_edges_plain` (`:363`), `RulesBareStar.lean::rulesAdmitted_edge_endpoints_bs` (`:767`). Every agent labelled these REASONED; no build was run anywhere in this sweep. **Cheapest probe:** one `formal/probes/*.lean` file that `decide`s the negation of `reachedByRulesAdmitted_edge_target_ne_wAny`'s conclusion on the existing fixture `LeafRules.lean::SlBridgeWitness` — the pin `::writeRulesRaw_creates_the_bridge` (`:2140`) already puts `(subjNode tlGrp.subject, wGrp)` in the edges and `wGrp = wAnyNode ("group","member")` has `variant = wAny`. That is ~10 lines and settles all four at once by exhibiting the witness.
2. **BLOCKER (structural, established): `FoldAdmitsBridged` is downstream of where the twin must live.** First-hand: `fwd(RulesComplete) ∌ Cascade`. Step 1 of the plan above is the proposed fix; it is a judgement call about a definition's home that contradicts an in-tree "do not move this" note. **Cheapest settlement:** none needed — the body read (`Cascade.lean:1957-1961`) shows it needs nothing Cascade-local. Record the decision, do not re-litigate it.
3. **⚠ THIS REOPENS A REJECTED ROUTE.** `docs/p6-step3b-plan-2026-09-13.md:1337` records as a REJECTED ALTERNATIVE: *"bridging σ0 too makes `classify` free but pays the `RulesWrite` reverse cone (40 modules) and re-opens the reference the shadow exists to reach."* **Two of that rejection's three premises no longer hold as stated.** (a) The cone figure was for `RulesWrite`, but R1 does **not** bridge `writeRules` — it forks an additive twin in `RulesComplete`, whose reverse cone is 33/32, and the existing-declaration repair set is **0**, not 86. (b) The paired "24" it was weighed against is now 33. The surviving premise — *re-opening `checkFn_eq_sem_bs` via `rulesAdmitted_edge_endpoints_bs`* (`RulesBareStar.lean:767` → `::graph_correct_rulesBS` `:805`) — is real and is item 1's probe target. **Recommendation:** before committing to R1, re-price the rival design that `CascadeStable.lean::foldAdmits_plain_of_L` (`:3572`) already points at — *write a `FoldAdmitsBridged → FoldAdmits` transfer lemma and keep σ0 unbridged*. Nothing in this sweep priced it, and it is the only route that leaves all four "FALSE" lemmas true. If it works it is strictly cheaper than R1; if it fails, the failure is informative and cheap. **This is an executive decision the next session owns.**
4. **SETTLED 2026-09-15c — the answer is YES, but this is the WRONG QUESTION: `notLeaf` is
   already false for the twin via the LEAF GRANT edge, with no bridging involved. See
   § *Corrections appended 2026-09-15c* (d), which also re-scopes sub-step 7. The rest of
   this item is the pre-settlement text.**
   ~~UNVERIFIED: is a bridged-in node's predicate ever a minted leaf name?~~ No lemma of the form `isSubjectWildcardUserset … → isLeafPred … = false` was found. If none exists, `CascadeStrataSettle.lean::reachedByRulesAdmitted_edge_target_notLeaf` (`:693`) is a **fifth** outright-false lemma rather than a repair-with-a-new-case. **Cheapest probe:** grep `LeafScope` / `NoLeafSubjects` for a clause bounding `isSubjectWildcardUserset` at leaf predicates; if absent, a `decide` on the `SlBridgeWitness` fixture settles it.
5. **SETTLED (no longer a blocker): `ShadowOver.term` on the σ0 side.** I read `UsStarWrite.lean::GraphState.ensureInBridges` `:296-303` in full — every branch adds only `addNode (wAnyNode …)` or the **incoming** `addEdge c (wAnyNode …)`. No outgoing edge from a bridge node is ever created, so `term : ∀ k, P k → ∀ y, (k, y) ∉ σ.edges` is not violated by a bridged σ0. Drop this from the risk list.
6. **UNVERIFIED: Python-side parity.** Nobody checked whether `index_v4/wildcard.py`'s rule-routed write path bridges. Per CLAUDE.md the Lean must track the shipped Python, and R1's entire justification is that it should. **Cheapest probe:** read `index_v4/wildcard.py::WildcardIndex._add_tuple_trusted` and `::_ensure_own_bridges` and confirm the bridge is materialised on the rule-routed leg. If the Python does **not** bridge there, R1 is chasing a model change the code does not have, and the honest move is a `CORRESPONDENCE.md` §7 gap entry instead.
7. **Rotted anchors that will mislead a resuming session** (all snapshot 2026-09-15, all inside blocks already on an edit list): `FullScope.lean:340` (plan's 7′ target; real field `:352`); `Cascade.lean:214` cites `UsStarWrite.lean:213` (real def `:296`); `CascadeInv.lean:134` cites `UsStarWrite.lean:274` (real theorem `:593`); `Scratch4cii.lean:425` cites `CascadeStrataSettle.lean:1179-1190` (real decl `:1587`) and `:432` cites `RulesComplete.lean:87-92` (real `:111-116`); `Leaf.lean:656-657` names three `shadow_graphRec_agree` sites as `CascadeSettle.lean:1123`, `CascadeStrataResettle.lean:1543`, `:2690` — live are `:1128`, `:1499`, `:2674`.
8. **Process hazard, recorded because it is the repo's documented footgun firing live:** one verifier observed a concurrent process on this machine clobbering generic `/tmp/*.awk` files mid-run, producing an all-zeros result at **exit 0**. Use `mktemp`-style private paths and dated script names for any re-measurement.

### Stale assertions to fix

All three flagged assertions **exist, are stale, and are PROSE — none is a theorem.** Locations verified first-hand 2026-09-15.

**(a) `formal/lean/ZanzibarProofs/Audit.lean:2012-2015`** — `--` line comments in the block preceding `#print axioms Schema.isStarTuplesetThrough` (`:2021`). Live text: *"★ THE HONEST LIMIT: part (i) is INERT on every live chain. `writeRules`/`writeLoggedRules` are bridge-free folds that never call `ensureInBridges`, so no edge is materialized until part (ii)."* **STALE.** Corrected wording — note the precision the earlier draft got wrong:

> `-- ★ THE LIMIT, updated 2026-09-14 (P6 step 3b): part (i) is NO LONGER inert. Two`
> `-- independent live legs now bridge. LOGGED: Cascade.lean::GraphState.writeLoggedRules`
> `-- folds ::writeLoggedOne -> ::bridgePreLogged -> ::ensureInBridgesLogged, whose body IS`
> `-- UsStarWrite.lean::GraphState.ensureInBridges. UNLOGGED: LeafRules.lean::`
> `-- GraphState.writeRulesRaw folds UsStarWrite.lean::GraphState.writeBridgedOne ->`
> `-- ::bridgePre -> ::ensureInBridges. These are two legs, NOT one nested in the other.`
> `-- Still bridge-free: RulesWrite.lean::GraphState.writeRules and Leaf.lean::`
> `-- GraphState.writeDirectRaw, both plain Write.lean::writeDirect folds.`

⚠ **`Audit.lean:2016-2021` is a SECOND, separate claim in the same block and needs a RE-RUN, not a reword.** It records a sabotage attribution — *"because part (i) is inert, short-circuiting `isStarTuplesetThrough` to `false` reddens NOTHING else in the tree … while all four controls stay GREEN"* — whose stated premise is the inertness that just became false. Rewording it would convert a now-unsupported assurance result into a fresh-looking claim. Re-run the sabotage or strike the attribution.

**(b) `formal/lean/ZanzibarProofs/Audit.lean:2105-2109`** — `--` comments before `#print axioms TtuStarFreeW` (`:2118`). Live text: *"The 2026-08-10 refutation stands: `writeRules`/`writeLoggedRules` are bridge-free folds that never call `ensureInBridges`, so the in-bridge the widened predicate ASSUMES EXISTS is not materialized."* **STALE IN PART.** The `writeLoggedRules` half is false; the `writeRules` half is true (`RulesWrite.lean::GraphState.writeRules` `:181-182` still folds `writeDirect`). The surrounding ⚠ at `:2105` (*"`W4Fragment.ttuStarFree` IS NOT CHANGED HERE"*) is **still true** — I confirmed `FullScope.lean:352` carries the un-widened `TtuStarFree`, with `TtuStarFreeW` a separate definition at `RulesBareStar.lean:68`. Corrected wording:

> `-- The 2026-08-10 refutation stands ONLY for RulesWrite.lean::GraphState.writeRules,`
> `-- still a bridge-free writeDirect fold. Cascade.lean::GraphState.writeLoggedRules`
> `-- stopped being one at P6 step 3b (2026-09-14, re-point #1), and LeafRules.lean::`
> `-- GraphState.writeRulesRaw at re-point #2 — so the PRECONDITION for widening is met.`
> `-- W4Fragment.ttuStarFree (FullScope.lean:352, 2026-09-15 snapshot) is still UNCHANGED:`
> `-- flipping it is part (iv) step 7', a separate owed step.`

**(c) `formal/lean/ZanzibarProofs/GraphIndex/Cascade.lean:183-209`**, sentence at `:185-186` — a `/-! … -/` module-doc block, not a docstring on a declaration. Live text: *"**These definitions are ADDITIVE and nothing calls them yet.** Step 3 of the `P6` plan composes `ensureInBridgesLogged` into `writeLoggedOne` below (and `ensureInBridges` into the unlogged `RulesWrite.lean::writeRules` twin, so `EvalEq` survives) and `releaseInBridgesLogged` into `removeLoggedOne`."* **STALE IN 2 OF ITS 3 PREDICTED COMPOSITIONS** — and the third is a plan-vs-landed divergence, not a rot. Corrected wording:

> `**LANDED at P6 step 3b (2026-09-14), in 2 of the 3 positions this block predicted.**`
> `` `ensureInBridgesLogged` is applied twice by `::bridgePreLogged` (`:508`), which ``
> `` `::writeLoggedOne` (`:532`) runs (RE-POINT #1). `releaseInBridgesLogged` is applied twice ``
> `` by `::releasePostLogged` (`:939`), which `::removeLoggedOne` (`:978`) wraps its then-branch ``
> `` in (RE-POINT #3). ⚠ The THIRD position did NOT land as predicted: `ensureInBridges` went ``
> `` into `LeafRules.lean::GraphState.writeRulesRaw` (RE-POINT #2), NOT into ``
> `` `RulesWrite.lean::GraphState.writeRules`, which was DELIBERATELY left bare. Do not ``
> `` "finish" the prediction without re-opening that adjudication — that is P6 part (iv) 4'. ``
> `` Still genuinely uncalled: `::GraphState.releaseInBridges` (`:249`, the UNLOGGED release). ``

**Do not fix by sweep.** `Cascade.lean:249`'s `releaseInBridges` has zero production callers, so a blanket "nothing calls them yet → LANDED" edit would make a *true* statement false. Four `bridge-free` lines are also still correct and must not be touched: `Audit.lean:144`, `ObjStarWrite.lean:17`, `:31`, `RulesBareStar.lean:46`.

**Beyond the three flagged:** at least 9 more sites carry the same 2026-09-14 rot — `Cascade.lean:262-264`, `:492`, `:1262-1263`, `CascadeInv.lean:128-131`, `TtuStarWide.lean:36-37`, `UsStarWrite.lean:122-124`, `:1690-1695`, `formal/CORRESPONDENCE.md:1313-1320` (highest priority: it is the gate-anchored LIVING map and it self-contradicts `:956-985` in the same file), and `CORRESPONDENCE.md:962-965` (states the `writeLoggedRules` chain incorrectly in the *corrected* passage). Plus the 4 `UntaintedShadow`-is-two-disjuncts sites: `CascadeStable.lean:630-634`, `:714-717`, `:3778`, `Scratch4cii.lean:511-512`. **Total prose-repair surface ≥ 16 sites across 8 modules + `CORRESPONDENCE.md`.**

**And the 40-vs-24 correction surface, measured first-hand:** 5 lines / 4 claim sites / 3 files under `formal/` (`LeafRules.lean:345`, `:397`, `CascadeStable.lean:2894-2895`, `CORRESPONDENCE.md:979`) plus 4+ under `docs/`+`tasks/` (`p6-part-iv-plan-2026-09-14.md:167`, `p6-step3b-plan-2026-09-13.md:1330`, `:1337`, `tasks/P6-ttustarfree-ii-bridges-on-rule-routed-write-path.md:2042`, `docs/history/session-log.md:117`). ⚠ `formal/history/PROOF_STATUS.md:3874` and `formal/history/leaf-family-split-scope-2026-08-05.md:1304` also contain the string "24 modules" — that is a **different, unrelated 2026-08-30b shadow-family census**, and history files are FROZEN. Do not edit them.

### Provenance

- **`cone:writeRules` (cone-rules-write)** — asked to measure `RulesWrite.lean`'s reverse import cone and the `writeRules` reference surface against the recorded "40". Its cone numbers are CONFIRMED; its "the RulesSound 29 is wrong" finding is REFUTED (I re-derived 16 ZP + 13 external = 29 and 22 + 13 = 35 myself); its `writeBridgedOne` decoy row (159/5) is REFUTED (I measure 124/5 bare, 251/8 family).
- **`cone:writeBridgedOne` (cone-bridged)** — asked to measure `UsStarWrite.lean`'s reverse cone and the bridged-symbol surface. Its headline (33/32, stale by 9) and its import-cycle adjudication are CONFIRMED by me first-hand at 6 revs; its enumeration of the 8 modules added at `7735ab1` is corrected by its verifier; its "13-module repair set" is unit-ambiguous.
- **`census:ReachedByRulesAdmitted` (admit-twin)** — asked to census the inductive's blast radius. Its 86/13/120 figures are CONFIRMED (I re-derived 120 code occurrences in 13 modules); its `FoldAdmits` "8 modules" is corrected to 7; its single-number blast radius is superseded by the three-number framing (86 naming / 134 one-hop through the six wrappers / **0 if additive**).
- **`anatomy:shadow` (shadow-site)** — asked to anatomise `CascadeStable.lean:3735` and the `ShadowOver`/`BridgeNode` surface. Its two structural findings (the constructor forces the fold; the twin falsifies `edge_target_ne_wAny`) are CONFIRMED by me first-hand and are the load-bearing results of the whole sweep. Its conjecture that the "24" measured `LeafRules`' cone is REFUTED by me. Its `BridgeNode` count is right for the predicate name, low for the symbol family.
- **`verify:stale-assertions` (stale)** — asked to locate and rule on three flagged prose assertions. All three CONFIRMED stale; its five-hop chain CONFIRMED by me first-hand (all five bodies read); its "8 stale sites" is low (≥12); its "`writeLoggedRules` folds `writeBridgedOne`" is a substring conflation that must not enter the corrected wording; its "bridge-free survives ONLY for `writeRules`" misses `Leaf.lean::GraphState.writeDirectRaw`.
- **`blast:shadow-swap` (blast)** — asked to size the shadow-swap's blast radius over fold lemmas and gate pins. Its structural findings CONFIRMED; its "4 gate-pinned names" is REFUTED by my own grep (13 rows); its "82 statements / 14 modules" is 13 modules; its "all 28 become a 3-way `rcases`" is 9 `obtain` sites + 19 term applications. Its fuel objection (`bridgePre`'s two unconditional `addNode`s) is CONFIRMED and is the reason `writeRulesRaw = writeRules` is unrecoverable.
- **Top-level session (this document)** — re-derived first-hand and independently: the full import graph (70 nodes / 219 edges) and all reverse/forward cones at HEAD and at `bd77fce`, `30ad44a`, `bff9297`, `af92af0`, `7735ab1`; the `LeafRules`-exclusion unit that reproduces (40, 24); comment-stripped censuses of `BridgeNode`, `writeBridgedOne`, `ReachedByRulesAdmitted`, `writeRules`, `FoldAdmits`, `reachedByRules_edge_sound` under both bare-identifier and substring units; all four acyclicity checks for candidate new imports; the `audited_theorems.txt` pin set; the bodies of `ReachedByRulesAdmitted`, `ShadowOver`, `UntaintedShadow`, `reachedByRulesAdmitted_edge_target_ne_wAny`, `foldl_writeBridgedOne_edges_sound`, `FoldAdmitsBridged`, the full five-hop logged chain, `ensureInBridges`, `bridgePre`, `writeBridgedOne`, and `FullScope.lean::W4Fragment`. **Not verified first-hand by this session:** the 5 elimination sites, the 52/40 declaration attributions, the `shadow_graphRec_agree` 15-site list, `CORRESPONDENCE.md:1313-1320`'s exact text, and every "this proof would break" verdict — no build was run anywhere in this sweep.
