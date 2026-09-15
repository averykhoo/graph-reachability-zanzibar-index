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
moved: 2026-09-15d
updated: 2026-09-15d
closed:
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
