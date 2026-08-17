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
