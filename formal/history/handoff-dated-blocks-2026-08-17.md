# formal/HANDOFF.md archive — dated blocks retired 2026-08-17 (board row `HS-4`)

**FROZEN 2026-08-17 — provenance, not a living document.** Status lines below are
as-of-then and several are known false; live state: [`HANDOFF.md`](../../HANDOFF.md) +
[`../HANDOFF.md`](../HANDOFF.md) + the session ledgers.
Corrections are appended dated at the top, never edited into the body.

Retired from `formal/HANDOFF.md` because that file was at **517 lines against its 520-line
ceiling** (`scripts/handoff_lint.py::MAX_LINES`, enforced by `formal/verify.sh lean` step
4f), so the next dated block a session appended would have turned the gate red. Row `HS-4`
on the root board; the debt was carried unpaid from `2026-08-16g` through `2026-08-17`.

The text is **verbatim**, not condensed — the same rule
[`handoff-status-2026-08-16.md`](handoff-status-2026-08-16.md) states: condensing is where
content dies, and a line diff cannot see it. Two blocks came here, the two oldest in the
reverse-chronological run and both fully LANDED:

* **2026-08-09** — leg 7 steps 3 and 4a (`8291c3a`, `41b7029`). Landed. Its open
  question — the `pushDelta` design fork of §11.3 — was answered by the 2026-08-14 block
  (branch (α)), which is still live in `formal/HANDOFF.md`.
* **2026-08-08** — the `rewriteClosure` dedup leg. Landed and CLOSED
  (`CORRESPONDENCE.md` §7.2 item 6).

Neither is a citation target: nothing outside `.scratch/` cites a dated block of
`formal/HANDOFF.md` (checked 2026-08-17 by grep). Every dated block here has a fuller
session entry in [`PROOF_STATUS.md`](PROOF_STATUS.md) under the same date key, which is
the citation key the rest of the tree actually uses — this file was the fast path, not a
unique home.

---

## 2026-08-09 (retired block, verbatim)

**LANDED 2026-08-09 — LEG 7 IS UNDER WAY: steps 3 and 4a are in
(`8291c3a`, `41b7029`), and the scope doc is now right in one place and wrong in another.**
`GraphIndex/Leaf.lean` carries leaf addressing (`leafPred`/`isLeafPred`/`leafNode`), the
raw-write routing (`rawWriteRel`/`rawWriteNode`/`rawWriteTuple`), the forked write
`writeDirectRaw`, and the distinctness linchpin `leafPred_ne_relName`. Additive: audits
481 → 493, headline statements 38/38 and definition pin 155/155 **unmoved**.
* **§3's bet HELD** — no new sentinel axiom; `relNameOK` gives leaf-vs-bare distinctness
  for free, and `relNameOK_of_isDerived` derives declaredness from `isDerived`.
* **§4's prescription is REFUTED. Do not fork `writeDirect`; fork the TUPLE.** Python
  does not fork its write path — `RuleSet.apply` re-addresses the triple
  (`zanzibar_utils_v1.py:447`) and the ordinary write runs. So `writeDirect` stays
  byte-identical and §4's predicted duplication of the projection and fold lemmas is not
  owed at all.
* **WHERE IT STOPPED, and it is a design fork the scope doc does not contain**
  (`history/leaf-family-split-scope-2026-08-05.md` §11.3): once the EDGE moves to the leaf
  node, `writeLoggedOne`'s `pushDelta` is a separate unforced choice — move the row too
  (faithful to Python's outbox, but `affectedKeys` then needs a leaf → public map the model
  has no analogue of) or keep it public (cheap, less faithful, a declared carry). **The
  `Delta.leaf` tag does NOT answer this** — it says which leg wrote the row, not which node
  the row is keyed at. Attack-first this before coding either branch.
* Step-4c sizing was walked four modules deep and is far cheaper than §5's 55–65% suggests
  — but the counts are per-module FRONTIERS (`lake build` skips dependents of a failing
  module), so §5 is neither confirmed nor refuted. Detail: `history/PROOF_STATUS.md`
  2026-08-09 and scope doc §11.

## 2026-08-08 (retired block, verbatim)

**LANDED 2026-08-08 — THE `rewriteClosure` DEDUP LEG (`CORRESPONDENCE.md` §7.2 item 6,
CLOSED).** The model's `rewriteClosure` did not deduplicate where `RuleSet.apply` does, so
on a *reconvergent* schema it counted DERIVATION PATHS where Python counts LIVE RAW TUPLES
(`lean=2 python=1`, growing `1 → 2 → 4` with the number of chained diamonds — with SCHEMA
SHAPE, not store content). It is now `(rewriteClosureRaw S t).dedup`, per stored tuple,
bridged by `mem_rewriteClosure_iff`. Two corpora (`reconvergent_diamond`,
`reconvergent_derived`) landed FIRST in a deliberately-red commit so the divergence was
attributable. The decisive argument was **house rule 5**: `RemoveOccCount.lean`'s header
*asserted Python's unit* and was false on any reconvergent schema, while the same file's
attack bullet said so — the file contradicted itself and R3/R4's faithfulness claim rested
on the wrong half. Sizing held: the count stack is list-generic, so `untOccCount`/R3/R4
needed **zero** proof rework. **Two things nobody predicted:** the over-count cost
RUNTIME (a zcli remove-stream timeout that the fix resolves), and the sabotage exposed a
LIMITATION rather than a confirmation — the new corpora do *not* catch the wrong (global)
dedup, `nary_union` does; they guard opposite errors. Detail:
`history/PROOF_STATUS.md` 2026-08-08b.

---

## Retired 2026-08-28c — the `2026-08-14` dated block

Same reason as the 2026-08-17 retirement above, and the same mechanism: appending the
`2026-08-28c` block took `formal/HANDOFF.md` to **547 lines against its 520-line ceiling**
(`scripts/handoff_lint.py::MAX_LINES`, enforced by `formal/verify.sh lean` step 4f), so the
gate was red until something moved. The oldest surviving dated block goes, verbatim and
unedited. It was already flagged **SUPERSEDED TWICE** in its own `Still owed` bullet, and
its live content (the (α) decision, the index-agnosticity trap, the 4c/step-7 co-landing
rule, the landing criterion) is carried forward by the `2026-08-16` and later blocks and by
scope doc §11.5/§11.11.

⚠ Its **landing criterion** figures (`dropped by P6` → 0, `compared against Lean` → 265,
"today 76 and 189") are as-of-2026-08-14 prose. Re-derive from `formal/FINAL_REVIEW.md`'s
generated counts block, never from this archive.

**2026-08-14 — THE §11.3 FORK IS DECIDED: branch (α). `ttuStarFree` PART (i) IS IN.**
Read `history/PROOF_STATUS.md` 2026-08-14 and scope-doc **§11.5** (appended; §11.3 is left
as written and is wrong in two places).

* **(α) — the `Delta` row moves to the leaf node.** Python's outbox row IS keyed at the leaf
  (`index_v4/models.py::DeltaOutboxV1` has no relation column; the relation is the object
  node's predicate), and `index_v4/processor.py::DeltaProcessor._map_deltas_to_keys`
  recovers the public name from the compiled `LeafFamily` table. The Lean probe did not
  refute (α); its control — the half-done (α), row moved with `affectedKeys` untouched —
  produced the **empty** cascade key set, so the instrument is real.
* **⚠ `publicOfLeaf` MUST BE INDEX-AGNOSTIC.** §11.3's prescribed "string surgery on the
  `.i` suffix" is measurably wrong: Python routes `(viewer but not banned) or [user]` to
  `approver.2`, where a `".0"`-stripper returns `none`. `Leaf.lean`'s former singular
  `rawWriteRel` (since replaced by `Leaf.lean::rawWriteRels`) hardcoded index `0` and was
  therefore a known-wrong model, not merely unmeasured.
* **`writeLoggedOne` does NOT need an `S` parameter** — `GraphState.schema` already
  exists and a `σ.schema`-reading variant is definitionally equal under `σ.schema = S`.
  That removes ~145 mention-lines from the budget (61 + 84 re-measured, not §11.3's 58),
  at the price of a per-site schema hypothesis.
* **⚠ 4c CANNOT LAND ALONE — it must co-land with step 7.** P6 is a Python-side-only
  filter (`formal/conformance/extractor.py::_edge_projection`), so the moment 4c re-points
  `Exec.lean` the state gate reports ~76 leaf edges "only in LEAN model". Scope doc §7's
  "each step green and pushable" is refuted at 4c.
* **Live landing criterion** (re-derive from `FINAL_REVIEW.md`'s generated block, never from
  prose): **`dropped by P6` → 0 and `compared against Lean` → 265** (today 76 and 189).
* **`ttuStarFree` part (i) LANDED**: `Schema.isStarTuplesetThrough` + the widened
  `Schema.isSubjectWildcardUserset` = both loops of `derive_schema_info`, as Python.
  ⚠ **INERT on every live chain** — `writeRules`/`writeLoggedRules` never call
  `ensureInBridges`, so part (ii) is what materializes the edge. Do NOT read part (i) as
  closing the 2026-08-10 counterexample. Six `decide` pins carry it because, being inert,
  the obvious sabotage reddens nothing else in the tree.
* **Still owed** ⚠ **— SUPERSEDED TWICE; read the 2026-08-16 block at the top.** "Step 4c"
  as named here does not exist any more (it is 4c-i + 4c-ii), **4c-i is DONE**, and part
  (iv)'s blocking question is **ANSWERED: NO-BLOCK** (`GraphIndex/TtuStarWide.lean`) — do
  not defer (iv) on decidability again. Genuinely still owed: leg 7 **4c-ii + 7 (co-land)**,
  4b, 5, 6; `ttuStarFree` parts (ii) and (iii), and (iv)'s remaining effort. Occurrence
  split re-measured: **163 in 18 modules**, only **5 genuinely CONSUMED**.

**⚠ 2026-08-10 — ATTACK-FIRST KILL: `W4Fragment.ttuStarFree` CANNOT BE DROPPED.**
The user asked to undo it as a mere scope cut. It is not one: dropping it makes
`graph_correct` and `backend_equivalence` **FALSE**, machine-checked sorry-free and
axiom-clean (`W4FragmentNoTS` = `W4Fragment` minus the one clause; `ReachedBy` from the
tree's own `graphRun_reached`, never hand-assembled; 120 comparisons, control a
one-character delta `folder:*` → `folder:f1`).
**The predicted mechanism was REFUTED and the conclusion still holds** — the
counterexample uses **no object wildcard**, so this is not the I14 bug; `bareStar` keeps
that shape out of scope anyway. The real gap is one layer earlier: Lean's W1c **in-bridge**
has no star-tupleset **through-shape** notion (`UsStarWrite.lean::Schema.isStarTuplesetThrough`
models the shape; `::GraphState.ensureInBridges` is what ignores it), and
`writeRules`/`writeLoggedRules` materialise **no bridges at all**. Python handles the shape
correctly; Lean's `ensureInBridges` on it is a literal no-op (`edges 3 → 3`).
Lifting it is a **four-part leg** (through-shape derivation; bridges on the rule-routed
write path; re-proving `ttuLeaf_elim_nss` + `StarSeed`, which exist BECAUSE of the clause;
the remove leg) across **162 occurrences in 18 modules**. Not blocking. Detail:
`history/PROOF_STATUS.md` 2026-08-10.

Older dated blocks — **2026-08-09** (leg 7 steps 3 and 4a, landed) and **2026-08-08** (the
`rewriteClosure` dedup leg, closed) — were retired verbatim on 2026-08-17 to
[`history/handoff-dated-blocks-2026-08-17.md`](history/handoff-dated-blocks-2026-08-17.md)
to keep this file under its line ceiling. Their fuller entries are in
`history/PROOF_STATUS.md` under the same date keys.

---
