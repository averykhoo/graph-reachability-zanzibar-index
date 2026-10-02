---
id: P4
title: leg 7 4b -- leaf-probe <-> directLeaf bridge
brief: sec 7.3 correspondence item, NOT the milestone: 4b premise is FALSE; 6 witness pins landed, general theorem owed
pri: NOW
size: M
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 015e6dd88c0d
created: 2026-08-16
moved: 2026-10-03b
updated: 2026-10-03b
closed:
---

leg 7 **4b** — leaf-probe ↔ `directLeaf` bridge. Unblocked 2026-09-05b (`P3` closed; deps
swept): the whole leaf-routed write path is live in the model (`Cascade.lean:190-191`,
`:340-341`, `affectedKeys` `:542-546`), so the bridge target is the landed leg, not a plan.

## Traps

⚠ **Do not cancel `P4` without reading why it must not be cancelled first.** Two frozen
records say so, and neither is reachable from this row's title or brief:

- `formal/history/leaf-family-split-scope-2026-08-05.md:1099` — under Route B, σ/σ0 reach
  agreement is **no longer supplied at leaf-node targets**. Nothing probes those today; the
  post-4b derived read path will, and that surface is this row. "Do not cancel `P4` without
  revisiting this."
- `formal/history/PROOF_STATUS.md:5146` — the same narrowing from the proof side: "If P4
  were ever cancelled, this narrowing is where the loss would surface."

The warning is reproduced here as a POINTER, not a copy: `formal/history/` is append-only
and frozen as-of-then, so a second copy of the sentence would be a second home for a claim
nothing updates (`docs/README.md`, one-home rule). Read the lines; do not trust this
summary of them.

⚠ **The general case is bigger than `P4`, and is filed as `TK66`.** The board-to-tree
migration could only carry what the board held, so ANY directive that lived only in
`formal/history/` is in this same position. `P4` is the instance that was measured; a
2026-09-07b sweep found sixteen more candidates. Do not read "P4 is fixed" as "the class is
fixed".

## Read first

- [`formal/HANDOFF.md`](../formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule — stated there, and enforced by nothing since 2026-09-07, when the checker was deleted with `.scratch/tasktool/`. Naming that symbol here would itself be a dead pointer, which is why this line only describes it; `TK59` is the row that would re-enforce the rule.)
- [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §7 — and §11.10 at `:1099` for the do-not-cancel warning above

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-16`), which is an upper bound on the real creation date, not a measurement. Body is the board cell: summary line plus the row’s pointer.

### 2026-09-05b

2026-09-05b: dep P3 swept (landed). Re-scope before starting: the leaf-probe <-> directLeaf bridge now has the whole leaf-routed write path live in the model (Cascade.lean:190-191, :340-341, affectedKeys :542-546), and the toolkit it was going to bridge to is the one CascadeStrataSettle.lean:3721 rawWriteRels_ne_nil_of_exprDirectsAll already walks (persistedLeaves/unionSpineLeaves/atomLeaves/pureLeaves/splitPure vs exprDirectsAll).

### 2026-09-06b

Board cell appended 2026-09-05b: 'Unblocked 2026-09-05b (P3 closed; deps swept)'. Task summary + brief now carry it (the 2026-09-05b Log entry already had the re-scope detail). Diff source: git 51642dc -> HEAD.

### 2026-09-22c

2026-09-22c -- **P4 is STEP 2 of the goal chosen this session** ("make the assurance surface
honest and legible, not wider"; map docs/goal-census-2026-09-22.md). Not re-ranked: NEXT is at
its cap of 3 and TK94 owns NOW, so this is recorded here rather than promoted, and the sequence
lives in the banner.

The decision the goal makes for this chain, so a later session does not re-litigate it:
**P4 -> P5 (+P14) IS the formal milestone, and the fragment stops widening after it.** The
formal census (2026-09-22c, agent leg, spot-verified) found the proof artefact has no debt at
all -- zero sorry, zero axiom, zero admit, zero native_decide, 617 audited names on the three
standard axioms, statements and definitions byte-pinned. Nobody needs to "finish the proofs."
What is unfinished is WIDTH, and width is an open-ended long tail: seven of ten W4Fragment
fields are SILENT (test_w4fragment_scope_pin.py:2 -- "a SILENT NARROWING, and nothing in this
repo could see it"), CORRESPONDENCE.md sec 7.3 lists about a dozen live Python surfaces with no
Lean model at all, and every widening row's own notes say finishing it does not end the queue.

So the T2a chain was picked because it is the one CLOSED thing in reach: three M rows, deps [],
evidence already in hand (formal/probes/d3_negedgefree_postflip_2026-09-05.lean measures
negFree := true on the model's own write leg, and the sabotage control reproduces the old kill).
Landing it retires W4NarrowT2a and buys one clean sentence -- all six headline theorems hold
under the same two bundles, with no theorem-specific extra carry. Today graph_reached_inv is the
odd one out, carrying a third bundle whose stated justification was already retired 2026-09-05
while the carry survived.

After it lands: P15 / P16 / P25-option-2 / DW-1 are assurance work to be ranked against product
risk, NOT "the rest of the proof." P6 stays parked (user decision 2026-09-15d) and this does not
touch it -- P6 blocks only P7 and P25 option 1.

### 2026-09-22d

Promoted LATER -> NOW at the 2026-09-22d write-back: TK94 (step 1 of the chosen goal) closed and left the board with no NOW, and P4 is step 2 as already recorded on this row and in docs/goal-census-2026-09-22.md. deps [] and the evidence is in hand. This is the ranking the goal note states, not a new decision.

### 2026-09-23

2026-09-23 -- P4 EXECUTED AS FAR AS IT GOES, AND ITS STATED PREMISE IS FALSE. Map:
docs/p4-leaf-probe-bridge-2026-09-23.md (ACTIVE-PLAN). Row stays OPEN; re-scoped and
demoted LATER, with P5 taking NOW -- see below for why that is not a downgrade.

THE PREMISE. Scope doc section 8.1 owed the bridge "once checkFn reads a leaf NODE instead
of the store". That day never came inside this model and cannot. checkFn
(ReconcileWrite.lean:72) and checkFnR (CascadeStrata.lean:113) both evaluate the RAW def,
and evalE's .direct arm (Spec/Semantics.lean:114) calls directLeaf (:65), which reads the
STORE through grantsOf (:45) at the PUBLIC relation. Every route by which a name could
reach rec is closed against leaf names by a GraphAdmission field -- computedRefsNotLeaf
(CascadeStable.lean:783, field FullScope.lean:196), directRestrNotLeaf, ttuNotLeaf -- and
FullScope.lean::sxLeafRef_other_admission_fields_hold :985 proves no OTHER field would
notice the difference. The tree took the REFUSAL route, not the BRIDGE route. That is a
landed design decision nobody wrote down, and it is why 4b sat unstartable.

BUT THE OBLIGATION IS REAL -- as a Lean<->Python item, not a fragment one. Pythons compiled
plan does exactly what section 8.1 assumed: zanzibar_utils_v1.py::_compile_check_fn :1940
sends a PClosureLeaf to index_v4/processor.py::_EvalContext.leaf_check :146, which probes
the INDEX at the minted leaf name. CORRESPONDENCE.md section 7.3 recorded that whole layer
as netted by the differential matrix and "not by any theorem about the compiler". That is
P4s real consumer, and it is squarely the chosen goal: convert a netted claim into a stated
one.

WHAT LANDED. (1) ATTACK FIRST, house rule 2: formal/probes/p4_leaf_probe_bridge_2026-09-23.lean,
rc=0. NO-KILL -- zero disagreements at three allocations over a store-derived subject grid.
(2) Six by-decide WITNESS PINS in GraphIndex/Exec.lean, namespace P4Bridge:
bridge_holds_Sw (storage leaf index 0), bridge_holds_SwU (index 2, the index Python really
mints), bridge_holds_SwF (two storage leaves, a fan-out), plus the two discriminating
controls bridge_needs_the_leaf_name_Sw/_SwU (probe the PUBLIC name: agreement 5 -> 3,
bothTrue -> 0) and bridge_is_per_leaf_SwF (cross-pair leaf i name with leaf j restrictions:
10 -> 8). Each pins a BridgeTally whose third field is the number of rows where BOTH sides
answered true, so agreement-by-universal-denial cannot pass. Audited, standard axioms only;
identity pin 617 -> 623. (3) CORRESPONDENCE.md section 7.3 updated: the PClosureLeaf clause
now names the pins and says in the same breath that the other four plan-leaf kinds are
still netted only.

SABOTAGE RECORD (docs/sabotage-procedure.md), literal outcomes. M0 instrument control --
flip bridge_holds_Sw own rows 5 -> 4: RED at exactly one declaration, Exec.lean:1445, its
own by-decide. M1 -- un-flip the logged write leg (seed writeLoggedRules with [t] instead of
rawWriteTuples S t): NEVER REACHED Exec.lean, Cascade.lean:757 fails first on the
logged/unlogged EvalEq coupling to writeRulesRaw. M2 -- hardcode the leaf index at 0 in
Leaf.lean::rawWriteRels: also never reached it, six declarations inside Leaf.lean fail first
(:743, :746, :1034, :1067, :1074, :1216), three AFTER their own pins were re-stated to
match. The honest reading is a SCOPE statement: the leaf-routed WRITE leg is so densely
pinned in Leaf.lean and Cascade.lean that no mutation of it survives to be evaluated here,
so these pins are evidence about the READ side -- which is exactly the side section 7.3
says is unmodelled. The two in-statement controls, not M1/M2, are what certifies them.

WHY P5 TAKES NOW AND THIS ROW DOES NOT. P5 and P14 both carried deps [P4]; both edges are
REMOVED this session, measured -- Inv (State.lean:717-730) is about nodes/edges/residue and
NReaches only, and probeNonDerived/directLeaf occur ZERO times in CascadeStrataEdge.lean and
CascadeStrataInv.lean. So the goals formal milestone is P5+P14 and it is startable today;
the residual cost is on P5s row. This row is now the section 7.3 correspondence item, real
but not the milestone.

WHAT THIS ROW STILL OWES, and the order. (1) The general theorem, blocked on a STATEMENT
problem before a proof one: it cannot be phrased inside the admitted fragment while
computedRefsNotLeaf stands, so either a second bundle permitting leaf names, or -- the cheap
one -- a statement phrased off the probe directly and never routed through evalE. The latter
works because the payload needs no rec at all: under DirectArmsBare + DirectArmsConcrete,
ReconcileCorrect.lean::memberOfGranted_of_bareGrants :214-220 kills the userset
flow-through, leaving "an edge subjNode s -> objNode o (leafPred R i) exists iff s matches
leaf i merged restrictions in T". The schema-free machinery transplants free
(DirectCorrect.lean::grantsOf_elim :286, ::grantsOf_intro :297); what must be restated over
leaf names is the declaredness-carrying half (WF, StoreValid, StoreValidRules{,D} are all
statements about S.defs, and Leaf.lean::leafPred_ne_relName :235 proves a leaf name is not
in it). Sized at about one file, unchanged from the 2026-08-05 estimate. (2) The .userset
leaf kind: rawWriteRels routes it (Leaf.lean:707, the .userset branch) and NO pin landed
here touches it -- every witness allocates .storage leaves only.

TRAPS THAT SURVIVE. The do-not-cancel warning at the top of this row is UNAFFECTED and still
binds: nothing here cancels P4. Two cite corrections found en route: scope doc section 8.1
cites graphRec at ReconcileWrite.lean:47-48, today :49-50; and State.lean:706 for
Inv.negEdgeFree is stale by 11 lines (:717-730, the field at :724-725) in the scope doc, in
P5s row and in the W4NarrowT2a docstring. Also stale: that docstring says the hypothesis is
used "in exactly four places"; ten Inv-preservation declarations exist today, four of them
on the leaf/bridged write path (Leaf.lean:836, LeafRules.lean:435, UsStarWrite.lean:769 and
:812, all gated on ResidueEmpty so they say nothing about the hard negEdgeFree case).

### 2026-09-27d

LATER -> NOW by user choice (2026-09-28): the NOW slot needed exactly one row once TK111 and TK112 were both put at NEXT; the user picked P4, the first step of the 2026-09-22 formal milestone (P4 -> P5 + P14).

### 2026-10-02b

NOW -> NEXT by user instruction 2026-10-02b: the three known live correctness bugs (TK111, TK112, TK113) are handled first. Resume P4 after they close.
