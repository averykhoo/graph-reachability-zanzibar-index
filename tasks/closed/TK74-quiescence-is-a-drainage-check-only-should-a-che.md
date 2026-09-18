---
id: TK74
title: quiescence is a DRAINAGE check only -- should a cheap per-write staleness check exist?
brief: TK73 fallout: I9 audit_fixpoint is the only correctness net and runs per-write ONLY under GraphBackend.post_op
pri: NOW
size: M
deps: []
related: [TK73]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-17
moved: 2026-09-18b
updated: 2026-09-18b
closed: 2026-09-18b
---

## What it is

`TK73` settled that the cascade's terminal assertion is a **drainage** check, not a
staleness check -- and after the fix it is a *fixpoint* assertion over the leftover keys
only, not over every derived key.

**The load-bearing observation (UNVERIFIED -- reported by a diagnosis verifier during
`TK73`, NOT reproduced first-hand; reproduce it before acting):** skipping a reconcile in
a *productive* round produced **2 wrong answers** against the oracle with **no raise from
either candidate fix**, paranoia off.

If that reproduces, the only real correctness net is I9 `audit_fixpoint`, which runs
per-write **only** under `tests/test_matrix.py::GraphBackend.post_op` -- i.e. in tests,
not in production. The question this row owns: should a cheap per-write staleness check
exist at all, and what would it cost?

## (!) Traps

- **(!) Reproduce the 2-wrong-answers claim FIRST.** It is the entire premise and it is
  unverified. If it does not reproduce, close this row rather than designing against it.
- **(!) Do not widen the settle pass into a full-store audit to "solve" this.** The settle
  pass is bounded at one extra reconcile per leftover key on purpose; making it O(store)
  per write trades a correctness gap for a performance cliff, and `audit_fixpoint` already
  exists for the full sweep.
- **(!) `ZANZIBAR_PARANOIA=residue` already exists** as the shipped runtime detector for
  the `ZT-P0-1` escalation class. Measure what it does and does NOT catch here before
  proposing a new knob -- the answer may be "widen paranoia", not "new check".

## Read first

- [`docs/tk73-cascade-quiesce-gc-2026-09-17.md`](../docs/tk73-cascade-quiesce-gc-2026-09-17.md)
  sec 7 -- where this question was raised and why it was left open.
- `index_v4/processor.py::DeltaProcessor.audit_fixpoint` -- the I9 net, and its cost shape.
- `index_v4/invariants.py` -- paranoia wiring and the sec 8.3 delta-scoped verifier.

## Log

### 2026-09-18

THE PREMISE REPRODUCES -- AND IT IS AN ASSURANCE GAP, NOT A LIVE BUG. Map: [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md) (ACTIVE-PLAN). 17-agent fan-out (6 angles, 2 adversarial skeptics each, 1 completeness critic) plus this session's own first-hand re-measurement of the two load-bearing numbers.

**(1) REPRODUCED.** Skipping one productive reconcile in a cascade round yields oracle divergences with no raise from the shipped settle pass, none from the rejected `rounds+1`, and none at ANY paranoia tier. Two independent probes, both instrument-controlled in both directions. The row's two-wrong-answers number lands exactly: seed 0 ordinal 18 and seed 2 ordinal 13 both give `div=2 raise=no` on both arms.

**(2) (!) BUT THE FLAG WAS WRONG AND I HAVE CORRECTED IT.** Two agents returned `is_wrong_answer_bug: true`; all four skeptics said false, and they are right -- every wrong answer required a deliberate monkeypatch, and the unmutated control arms are `divergences=0`. **The board's "Known live correctness bugs: 0" line STAYS AT 0.** Reconciled, not averaged (`CLAUDE.md` sec  Delegation).

**(3) MECHANISM, READ FIRST-HAND at `index_v4/processor.py:1628-1636`.** `leftover` has exactly two sources: outbox rows above the frontier, and `self._bumped` (sole append at `:1351`, INSIDE a reconcile). A reconcile that never runs writes nothing, emits nothing, bumps nothing -- so it cannot enter `leftover` by any path, and `self._settle = None; if not leftover: return` exits ABOVE both checks. Both candidate fixes are gated on the same outbox-derived set. This is not a defect in the `TK73` fix: that pass was aimed at work the cascade does not SCHEDULE, never at a scheduled reconcile that did not run.

**(4) THE DESIGN QUESTION IS NOW ANSWERED, and the answer is narrow.** Per-op `audit_fixpoint` raised at exactly the op of the first wrong answer in **8 of 8** divergent cases; end-of-run `audit_fixpoint` was **clean in 4 of 8**, because a later write re-reconciles the key and LAUNDERS the corruption. Staleness is often TRANSIENT and the wrong answers are served inside the window. **So "audit periodically" is not a design option** -- this row narrows to a per-write check or nothing. (Counts: the originating agent said 9/18 and 4/9; two skeptics independently measured 8/18 and 4/8. Use 8.)

**(5) (!) THE BOUND NOBODY NOTICED -- MEASURED FIRST-HAND, AND IT IS THE REAL DELIVERABLE.** A pytest plugin wrapping `_run_cascade` and reading `self._settle` in a `finally`, bucketed by `len(compiled.strata)`:

    run 1 (4 modules, 34 passed): 118 cascades -- 3 SETTLE_RAN, all strata=1
    run 2 (6 modules, 104 passed): 440 cascades -- 0 SETTLE_RAN; 415 of them strata>=2

**558 cascades, the settle pass executed on 3 (0.54%), all at `strata == 1`, all three inside the module written to make it run. It has NEVER been observed to execute on a multi-stratum schema.** INSTRUMENT CONTROL: run 1 moved BOTH arms, so run 2's zero is a measured zero from a live counter (the plugin prints an explicit INERT warning on a one-arm run, and run 2 printed it). Mechanical reason, READ: `::_map_deltas_to_keys` (`:1379`) routes a `DerivedFamily` object row through `::_fan_out` to its DEPENDENTS, never to its own key.

**This bounds (3).** Every skip experiment ran at `rounds` 1 or 2. The one shape where the settle pass could plausibly catch a skip -- skip a LOWER-stratum reconcile, let a higher stratum compute off stale input and emit rows that `_fan_out` maps BACK onto the skipped key -- was never driven. "Blind by construction" is proven only for the single-stratum case.

**NEXT ACTION (single):** one skipped-reconcile experiment on a multi-stratum schema -- `tests/fga_schemas/demorgans_law_2.fga` (6 strata) or `wildcard_userset_cross.fga` (4) -- skipping a reconcile in a NON-final stratum. Do that BEFORE designing any per-write check.

Spun out: `TK76` (a shipped pin's stated control is inert), `TK77` (the matrix/hypothesis campaign cannot reach the `_sync_entity_middles` surface), `TK78` (`bulk_backfill.py` unaudited; `backfill()` drops `_bumped`), `TK79` (the late-GC rows' own design justification is pinned by nothing). `TK3` demoted to LATER: its census question is answered in sec 3 of the doc (`audit_fixpoint` has zero production callers, READ).

(!) PROCESS: four of six agents detected a CONCURRENT WRITER mutating `index_v4/processor.py` (`_sk[:-1]`, a skip-the-last-key sabotage) at ~23:28-23:35 on 2026-09-17, reverted before I looked. It produced false readings in two agents' runs. Tree verified clean at HEAD 6c5b97c before and after; nothing from that window was committed. Rule earned, doc sec 7: pin a `git archive HEAD` export and check `git status --porcelain` before AND after any probe that matters.

### 2026-09-18b

THE EXPERIMENT IS RUN AND THE DESIGN QUESTION IS ANSWERED. Map: [`docs/tk74-staleness-net-2026-09-18.md`](../docs/tk74-staleness-net-2026-09-18.md) §8 (round 1) and §9 (round 2). Two fan-outs, 19 agents; every load-bearing claim re-verified first-hand by the session.

**THE ANSWER.** The `TK73` settle pass is **structurally incapable** of detecting a skipped/stale reconcile **at any schema shape** — `leftover` is built exclusively from things that were WRITTEN (outbox rows above the final frontier, plus the `_bumped` fan-out whose sole append is `_store_residue`, `index_v4/processor.py:1351`), and a stale reconcile is a *non-write*. Its teeth are real and correctly aimed at a DIFFERENT class (late reconcile-time GC emission): forcing the key into the post-loop map at `:1629` makes it raise 4/4 and 2/2. **Do not widen it.** The only detector for this class is `audit_fixpoint` (I9, `:1732`) — **zero production callers**, confirmed first-hand.

**(!) TWO CORRECTIONS TO §8, BOTH FROM ROUND 2.** (1) §8.2 blamed the null on `if not keys: break` (`:1583`) decapitating strict chains — that is ONE SUFFICIENT CAUSE, NOT THE REASON. `het` built a diamond that defeats decapitation: the final round DID write and emit (1/3/4 outbox rows in 3 of 32 arms) and `_map_deltas_to_keys` still returned ZERO keys. §9.2 has the stronger law. (2) §8.4's "no paranoia tier fires" OVERCLAIMS — the FULL tier incidentally catches a dangling-id side-effect on ~2.4% of arms on one fixture (I6, dead node id in a residue's neg). It still never detects the staleness itself.

**n WENT FROM 6 TO ~62 AND THE NET STAYED EMPTY.** Round 1's 104 arms were really 6 (98 were structurally unreachable). Round 2 adds 54 (`demorgans_law_2`, skeptic-corrected from the probe's inflated 130), 4 (`heterogeneous_tupleset`), 4 (`demorgans_reverse`). In every one: settle executed 0, raised 0, leftover non-empty 0.

**THE HABITAT CONTROL SEPARATES "BLIND" FROM "NEVER RUNS"** — reproduced first-hand: the settle pass DOES execute naturally on a 3-stratum schema with no skip and no injection, on a STRATUM-0 leftover key, returning `changed=()`. So the nulls are genuine nulls, not dormancy. But the habitat is brittle (one extra tuple silences it) and had to be engineered: 2385 fuzzed multi-stratum cascades gave `SETTLE_RAN = 0`.

**LANDED THIS SESSION (the next action, and it is the INSTRUMENT, not the detector):** `tests/wildcard_helpers.py::make_wildcard_index` silently DROPPED its tier argument — signature `paranoia: bool`, body `if paranoia: install_paranoia(...)` with no `level=`, and `install_paranoia` defaults to FULL. So `paranoia='off'` was a truthy string that installed the STRONGEST checker. A live assurance step failing by PASSING, in tracked test code; it already invalidated one round-2 probe's entire three-tier sweep (it ran off/FULL/FULL). Fixed to forward the level; pinned by `tests/test_paranoia_wiring.py::test_helper_forwards_the_tier` and `::test_helper_rejects_a_typod_tier`. **Sabotage observed RED before the fix** (`assert 'full' == None`, `assert 'full' == 'residue'`, typos `DID NOT RAISE`) — and the FIRST red was an instrument failure (`AttributeError: 'str' object has no attribute 'schema_info'`), fixed before the red was believed.

**(!) A PHANTOM SYMBOL NEARLY REACHED A TRACKED DOC.** An agent cited `index_v4/core.py::_adjust_reference_counts` as an unguarded implicit-node-delete path. MEASURED: that symbol does not exist anywhere in the tree. The CODE is real; the enclosing symbol is `ReachabilityIndex._add_direct_edge_unsafe_impl` (`core.py:714`), branches at `:877`/`:894`, no residue-reference check, reachable via `_gc_subject_node` -> `WildcardIndex._maybe_remove_bridges` (`wildcard.py:437`). Unobserved in 208 arm executions, excluded by no guard. Spun out as `TK81`.

**NEXT (spun out, this row's question is answered):** `TK80` implements the opt-in tier — I9 fixpoint over the cascade's SCHEDULED-key union (NOT the reconciled set: the skipped key is absent from that by construction), default OFF. `TK81` is the unguarded delete. `TK82` is the transient-staleness finding that demotes any periodic audit.

`read: board + note`

CLOSED — the row's question is answered, recorded, and the blocking instrument fix has landed.

**(!) ID CORRECTION to the entry above, which was written before the ids were allocated.** The spin-outs are: **`TK80`** = the unguarded `core.py` implicit-node delete; **`TK81`** = staleness is transient so a periodic audit is worth ~zero; **`TK82`** = implement the opt-in I9 tier (promoted to the work queue). The previous entry's "TK80 implements the tier / TK82 is transient" mapping is WRONG — `new` allocates on creation order and the tier row was refused at NEXT and re-created last. Cite the ids in THIS entry.

**THE DECISION, so nobody re-litigates it.** A cheap per-write staleness check SHOULD exist, as a NEW OPT-IN PARANOIA TIER beside off/residue/full (`index_v4/invariants.py::install_paranoia`), DEFAULT OFF, asking the I9 fixpoint question over the cascade's SCHEDULED-key union. Three things are settled and must not be re-opened without new evidence:
1. **NOT by widening the settle pass.** It is structurally blind to this class at any schema shape (§9.2) and its teeth are correctly aimed at a different one. `rounds+1` was already rejected in `TK73` for repairing what it should detect.
2. **NOT by a periodic or end-of-run `audit_fixpoint` sweep.** Staleness here is TRANSIENT — 31/34 arms transiently divergent, 0/34 still divergent after the workload, because later writes launder it (`TK81`). A periodic audit is worth ~zero as a DETECTOR; ship the production entry point framed as REPAIR/DIAGNOSIS (its own docstring already names `backfill()`).
3. **The union must come from the SCHEDULING side** (`keys` at `index_v4/processor.py:1591`), never the reconciled set — the skipped key is absent from the latter BY CONSTRUCTION, so specified that way the tier ships DEAD. The mandatory sabotage for `TK82` is exactly that narrowest plausible weakening: take the union from the RECONCILED set and watch the test go green.

**SCOPE BOUND that must survive into `TK82`:** the tier covers EXECUTION-side misses only. No arm in either round falsified the SCHEDULING side (`_fan_out`, `_map_deltas_to_keys` key derivation, `compiled.dependents`), so a key that is never scheduled at all stays uncovered — full-key `audit_fixpoint` remains the only net for that.

**Known live correctness bugs stays 0.** Every wrong answer across ~166 arms required a deliberate instance-level monkeypatch; every unmutated control is `divergences=0`.

Gate: full `verify.sh` green on this tree before commit (see the session-log entry).

`read: board + note`
