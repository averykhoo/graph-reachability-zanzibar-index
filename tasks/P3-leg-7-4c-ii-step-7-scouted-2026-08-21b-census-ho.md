---
id: P3
title: leg 7 4c-ii + step 7 -- scouted 2026-08-21b: census hole + headline-guard human call
pri: NOW
size: L
deps: []
related: [P6]
parent:
labels: [formal]
source: board
source_hash: 90a1f8ce5f73
created: 2026-08-21b
moved: 2026-08-28
updated: 2026-08-28
closed:
---

Re-point the rule-routed write path onto leaf-indexed targets and retire projection `P6`
in the same commit. Critical path. Route B (weaken `UntaintedShadow`) stands adjudicated
(2026-08-20b, user call), absorbs `P14`'s classification half; scouted 2026-08-21b into
an executable design — full record in PROOF_STATUS `## Session 2026-08-21b`. Movers:
**census hole** — `CascadeStable.lean::shadow_graphRec_agree` (audited, 14 call sites, one
in `CascadeEnum.lean`, outside the 7-file/84-site budget) discharges from
`hunt : isDerived S (dt',r') = false`, which does not imply `publicOfLeaf = none` — a new
hypothesis on an audited signature + 14 repairs, unbudgeted; **`FoldAdmits`** — 21 sites
move, 3 stay σ0-side, not "all 24 in lockstep"; **decision taken** — keep names, change
bodies of the live write leg, `rewriteClosure` keeps its meaning (the σ0 chain is
rules-built by design), `writeRules` untouched (= the rejected Route C); **unowned
obligation** — `CascadeStable.lean::reachedByW3d_shadow` (via `untaintedShadow_writeLeg`)
pairs the same list on both folds; post-re-point the leaf list is a strict superset on a
mixed schema even for untainted tuples — no slice owned it, the Lean budget grows.

🧭 **MACHINE-CHECKED, and it needs a HUMAN CALL before 4c-ii lands: after the re-point
the headline theorems are FALSE AS WRITTEN — not merely unproven — at minted leaf-name
queries.** Two independent kernel `by decide` constructions; probe 2 typechecked
`graph_correct qLeaf admission w4fragment h hq b1 b2` verbatim, then the re-pointed
drained state grants it while `sem` denies. Probe 1's literal output (`SlV`, `tlEditor`):

    ("minted leaf name", "viewer.0")
    ("hd: isDerived at leaf name", false)
    ("hqs holds", true, "hqo holds", true)
    ("probeNonDerived sR qLeaf", true)
    ("check sR qLeaf", true)
    ("sem qLeaf", false)
    ("drainedB sRLc", true, "check sRLc qLeaf", true, "sem qLeaf", false, "check sRLc qPub", true)

The ~10 pinned headlines (`formal/headline_statements.txt`) each need a guard — accept
the narrowest, `hql : publicOfLeaf S q.object.type q.relation = none`; refuse the
`isLeafPred`- and `isDerived`/taint-keyed shapes (analysis + probe-2 caveat: PROOF_STATUS).

## Traps

⚠ **Seven traps live in scope doc §11.10** — the backwards own-key premise, the
leading-conjunct ordering, the `FoldAdmits` sites (21/3 above), the derived golden
expectation, Route B's two premises. **Read §11.10 before touching the cone.**

## Read first

- [`formal/HANDOFF.md`](formal/HANDOFF.md) — **first, for any formal item**: the proof frontier, what is proved and what the next lemma is (`HANDOFF.md`’s pointer rule; enforced by `migrate.py::check_formal_pointer`, not merely stated)
- board pointer: [scope doc](formal/history/leaf-family-split-scope-2026-08-05.md) §11.9

PROOF_STATUS `## Session 2026-08-21b` then `2026-08-20b`, scope doc §11.9
then **§11.10 (the traps)**, `GraphIndex/Scratch4cii.lean`, §11.7, §11.5; completion
criterion: PROOF_STATUS `2026-08-16c`, its numbers re-derived from `formal/FINAL_REVIEW.md`'s
generated ledger, never prose. Then `CascadeStable.lean::shadow_graphRec_agree` /
`::reachedByW3d_shadow` / `::untaintedShadow_writeLeg`, `LeafRules.lean::GraphState.writeRulesRaw`,
`Leaf.lean::publicOfLeaf`, `Exec.lean::foldAdmitsB`, `extractor.py::_edge_projection`.

## Log

### 2026-08-21

Migrated from the `HANDOFF.md` board by `migrate.py` (SPEC.md section 7). **`created` is an approximation**: the board never recorded one, so it is set to this row’s `moved` value (`2026-08-21b`), which is an upper bound on the real creation date, not a measurement. Summary, traps and read-first come from the `### P3` item block verbatim; the board pointer is the first line of Read first.

### 2026-08-28

Six-agent live census + both human calls adjudicated (user delegated 2026-08-28): hql ACCEPTED; Route B RETAINED on corrected grounds -- its 'zero additional cone' argument is FALSIFIED (census hole propagates ~45 second-ring sites through checkFn_agree_of_graphRec into 4 files outside the cone). hql itself is cheap: 8 declarations, depth 2, audit pin untouched -- but it lands on the leg-5 non-vacuity instrument (final_applies), so the fence-modeling endgame (checkPublic mirroring BL-2's public deny) is the recommended repair shape. Full census: scope doc sec 11.11; adjudication record: PROOF_STATUS 2026-08-28. Stale-comment debt from 2026-08-21b discharged (4 sites). Sizing: ~136 sites / 8 files, third consecutive low count.
