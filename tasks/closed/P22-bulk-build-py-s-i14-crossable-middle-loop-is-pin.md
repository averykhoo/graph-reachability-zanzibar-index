---
id: P22
title: bulk_build.py's I14 crossable-middle loop is pinned by nothing (green sabotage)
brief: AGENT-PROBED 2026-09-15d: an input REACHING the loop exists (sabotage goes red); re-verify, then corpus + close
pri: NEXT
size: S
deps: []
related: []
parent:
labels: [formal]
source: board
source_hash: 887290727321
created: 2026-09-06b
moved: 2026-09-16
updated: 2026-09-16
closed: 2026-09-16
---

Found 2026-09-06b by the `P17` sabotage sweep. `index_v4/bulk_build.py:206-221` is the
I14 crossable-middle loop of the bulk closure builder. Deleting it outright stayed GREEN
across every `build_index` caller: `tests/test_bulk_build.py`, the new
`formal/conformance/test_conformance_bulk_state.py` (bulk vs incremental Python graph
state, exact, over all 25 `GRAPH_FRAGMENT` corpora) and the validation matrix. The
observed output is in that module's docstring under "green sabotages".

Two honest outcomes, pick one with evidence:

1. No corpus reaches a crossable middle under bulk. Write a corpus that does, watch the
   sabotage go RED, keep it as a permanent test (durability ranking in
   `docs/sabotage-procedure.md`).
2. The loop is dead code on every reachable input. Prove it (or show the incremental path
   never materialises what it would) and delete it.

A loop no sabotage can reach is unverified code on the DEFAULT constructor.

## Log

### 2026-09-06b

first reconciliation: filed from the board row this session; body and row say the same thing

### 2026-09-15d

A CANDIDATE INPUT THAT REACHES THE LOOP EXISTS -- AGENT-PROBED, NOT YET VERIFIED FIRST-HAND. From the 2026-09-15 adversarial audit; read `docs/adversarial-audit-2026-09-15.md` sec 2. This row stays OPEN precisely because the evidence is a subagent's and `CLAUDE.md` sec Delegation says that is evidence, not a finding -- re-run it before closing.

**THE CLAIM (AGENT-PROBED, literal output reported by the agent, NOT reproduced here):** an `owc_star_ttu`-class schema with `object_wildcard_shapes={('folder','viewer'),('doc','viewer')}` and three tuples (`u1 editor f1` as the witness; `u1 viewer folder:*`; `folder:* parent doc:d1`), queried at `check(u1, viewer, doc:d1)`, gives `inc=True bulk=True oracle=True` on the shipped tree and `SABOTAGE-RED: bulk_no_i14=False oracle=True` with the loop's `crossable_shapes` guard neutered -- i.e. exactly the deletion sabotage this row was filed for, now RED instead of green.

**WHY NO EXISTING CORPUS REACHES IT (AGENT-READ, unverified):** every entry of `tests/test_bulk_build.py::_CORPORA` has `crossable_shapes = ∅`, because `zanzibar_utils_v1.py::_reject_doubly_bridged_shapes` intersects only LITERAL `T:*#p` shapes, while star-tupleset THROUGH-shapes make the set non-empty on a schema the compiler admits. That is the gap the corpus never crossed.

**(!) A SECOND, SEPARATE HOLE CLAIMED IN PASSING (AGENT-READ, unverified, and it is NOT this row):** `tests/test_zt_p5_readjudication.py` is said to call `check_invariants` WITHOUT `schema_info`, which disables the I14 clause outright. If that reproduces it is its own finding and deserves its own row -- an invariant clause silently disabled in a state gate is the same shape as this row's green sabotage. Verify separately; do not fold it in here.

-> NEXT: re-run the probe first-hand, then add the corpus entry to `_CORPORA` and close. The agent's probe is `.scratch/probe_bulk_i14.py` and (!) `.scratch/` is gitignored, so transcribe it to `formal/probes/` in the same hour or it is gone.

### 2026-09-16

CLOSED. The loop is LIVE CODE on a reachable input, it is now pinned, and the pin is sabotage-verified three ways. Outcome 1 of the two the row offered (keep the loop), not outcome 2 (dead code).

**THE PROBE REPRODUCES FIRST-HAND.** `formal/probes/bulk_i14_crossable_middle_2026-09-16.py`, rc=0, transcript identical to its header. The 2026-09-15d agent claim is therefore CONFIRMED, as `CLAUDE.md` § Delegation requires before acting on it.

**(!) BUT THE ROW'S PLANNED FIX WAS NOT SUFFICIENT, AND THAT IS THE SESSION'S REAL FINDING.** The inherited corpus was defined but never wired into `_CORPORA` (dead code). Wiring it in and re-running the original deletion sabotage left the module **fully green** -- with `schema_info.crossable_shapes` non-empty, `{('folder','viewer')}`, where every other corpus has `frozenset()`. The corpus reached the loop by the row's own metric and pinned nothing.

CAUSE, measured per tuple: two of the four "extra coverage" tuples MASK the mechanism by giving the generic bridged-in/out loop a concrete `viewer(folder,_)` node to bridge, which completes the `w_all -> middle -> w_any` crossing without the I14 loop. Minimal 3 tuples -> sabotage RED; `+ folder:f2 parent doc:d2` -> GREEN (masks); `+ u2 viewer folder:f2` -> GREEN (masks); `+ u2 blocked/editor folder:f2` -> RED (safe). (!) Masking survived every SINGLE-tuple removal -- two independent maskers were present, so a one-at-a-time bisect says "not this one" four times. Add up from the minimal shape instead.

**LANDED:** corpus trimmed to the minimal shape + the two measured-safe tuples, with the table at the edit site; a structural clause in `tests/test_bulk_build.py::_assert_r4bf_features` pinning the loop's PRODUCT (the `viewer(folder,f1)` middle and both bridges -- `f1` holds no viewer triple, so nothing else can create it), DERIVED from the literal shipped state; and a mechanical anti-mask control that refuses the corpus if any folder gains a direct `viewer` grant.

**SABOTAGES (landed tree, `-k owc_star_ttu`):** S1 `crossable = frozenset()` -> RED at `snapshot_rows differ`; S2 keep the loop but drop only the `w_all -> mid` bridge (the narrowest plausible weakening) -> RED same site; S3 INSTRUMENT CONTROL, re-add the masking tuple -> RED at the anti-mask control, naming `f2`. (!) S3 is the only evidence the new clause can fire at all, since S1/S2 both redden earlier at the state comparison. The corpus is the witness; the clause guards the witness against a future masking edit. Different jobs, both needed.

The scouting deliverable is [`docs/p22-i14-corpus-masking-2026-09-16.md`](../docs/p22-i14-corpus-masking-2026-09-16.md) (FROZEN), and the probe header carries a dated correction pointing at it. The general lesson recorded there: "reaches the mechanism" and "pins the mechanism" are different claims, a configuration-level metric can only establish the first, and where the mechanism is a REDUNDANT path the answer-level grid is structurally incapable of pinning it -- pin the product, not the answer.

NOT CLOSED HERE: the second hole the 2026-09-15d agent claimed in passing (`tests/test_zt_p5_readjudication.py` calling `check_invariants` without `schema_info`, disabling the I14 clause outright) is still UNVERIFIED and still deserves its own row.
