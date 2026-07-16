# R4-BF — bulk boolean `backfill()` for `build_index` (design, 2026-07-15)

Goal: apply the P13 pattern one layer out. P13 (`docs/architecture/p13-bulk-build-design.md`,
`index_v4/bulk_build.py`) bulk-builds the **pre-backfill** closure state; on boolean
schemas the total build is then dominated by the unchanged per-object
`DeltaProcessor.backfill()` (P13 boolean total = 1.44× vs 33.6× on the isolated load
phase — the residual IS the backfill). This design computes the **final derived
state** (derived edges, residues, from-chain nodes, their closure/outbox/refcount
effects) **in memory** during the same bulk build, and writes everything in one
extended Phase W.

**Correctness bar (same as P13, deliberately): the bulk-built store state is
IDENTICAL to `build_index(..., bulk=False)` + incremental `proc.backfill()`, modulo
auto-assigned row ids** — pinned by the existing differential identity gate
(`tests/test_bulk_build.py`), extended with new corpus schemas (§5). The incremental
path's whole verification story transfers by equality; `DeltaProcessor.backfill()`
itself is UNCHANGED (it remains the repair path and the `bulk=False` reference side).

## 1. The exact state incremental `backfill()` adds on a fresh build (code-verified)

References as of 2026-07-15: `index_v4/processor.py`, `index_v4/wildcard.py`,
`index_v4/core.py`. On a fresh build (empty derived state, add-only), `backfill()`
iterates `compiled.strata` in order, relations within a stratum in list order,
object names sorted (`_live_keys_of` → `sorted(names)`), and calls
`reconcile(object_type, rel, obj_name)` once per live key. Chunking/flush boundaries
do not shape state. Each reconcile, from empty per-key state, produces:

1. **stars** = `plan.stars_fn(ctx)` — the pinned star×boolean fold. Closure-leaf
   star probes are `widx.check(p, t, '*', leaf_pred, obj)` per declared subject
   shape, i.e. the 4-probe wildcard check (§2.3).
2. **neg** = candidate ids that are star-covered ∧ `check_fn`-false. Candidates:
   concrete members of every negative-polarity leaf (`_leaf_concretes`) ∪ neg sets
   of every referenced derived leaf (`_derived_leaf_neg_ids`, any kind — lower
   strata via residues) ∪ the step-2a from-chain additions below.
3. **From-chain userset subjects** (`_from_chain_keys`, step 2a): one key
   `(target_rel, pt, pn)` per stored tupleset parent of every TTU leaf (any
   polarity). Evaluated by KEY; a node is **interned only when the outcome must be
   recorded** (`should != covered`), with `implicit=False` and
   `widx._ensure_bridges(n)` run on the fresh node (bridge edges are real direct
   edges: closure + refcount + outbox effects). A pre-existing node joins the
   candidates regardless.
4. **upos** = userset-shaped audit members (predicate ≠ `'...'`, concrete),
   NOT star-covered, `check_fn`-true. Audit set = candidates ∪ concretes of every
   positive leaf ∪ current derived incoming (empty on fresh) ∪ old upos (empty).
5. **Residue row**: written iff `(stars, neg, upos)` non-empty; `version=1` on a
   fresh build (created once; step-4 subject reconciles cannot bump it — their
   want_neg/want_upos already match step 2/2c, since derived edges of one subject
   never change `check_fn` of another subject of the same object: derived edges
   land on the PUBLIC family, leaves are untouched). JSON arrays sorted;
   `object_node_id` = the public node, interned `implicit=False` by
   `_store_residue`.
6. **Derived edges** (step 4 via `_reconcile_subject` → `_write_derived`): for each
   BARE-ENTITY audit member (predicate `'...'`), uncovered ∧ `check_fn`-true ⇒ one
   direct edge `subject → public(rel, object_type, obj_name)`, **multiplicity
   exactly 1** (existence-checked), through `add_tuple` with
   `processor_writes=True`: the public node interned/promoted `implicit=False`,
   +1 `reference_count` on BOTH endpoints, full closure region update, outbox
   emission on every 0→positive pair flip. Userset subjects NEVER hold edges (P4).
7. **`derived` flag** (core `_add_db_edges_unsafe`): `derived=True` iff the pair's
   direct edge was written under `_writing_derived` with direct_count>0; pairs that
   are pure-indirect (including those created THROUGH derived edges) stay
   `derived=False`. By I5 exclusivity, the derived-direct pairs are exactly the
   processor-written `(subject, public-node)` pairs.
8. **Sticky explicit promotion** (`core.node`): a public node that pre-exists
   IMPLICIT from the load — possible when a raw tuple has a userset subject whose
   predicate is a derived relation, e.g. `('member','group','g','x','doc','d')`
   with `member` derived on `group` — is PROMOTED to `implicit=False` when the
   processor touches it (`_store_residue` / `_write_derived` add). Same for
   from-chain nodes.
9. **No removals, no GC**: a fresh-build backfill is add-only (each key reconciled
   once, from empty, against fully-built lower strata), so `_gc_subject_node` /
   `_gc_public_node` never delete and no REMOVED outbox rows are emitted.
   Consequence (shared with P13): **the final outbox is exactly one ADDED row per
   final closure pair** (load-era and backfill-era flips together), endpoint
   identities denormalized from the node keys; order inert, content a multiset.
10. **Path counts stay the T4 closed form**: the final `indirect_edge_count` of
    every pair equals the weighted path count over the FINAL direct multigraph
    (load m + bridge edges + derived edges, all integer multiplicities). Cycles
    are impossible (stratification); hitting one is `InvariantViolation`.

### Visibility subtleties the mirror MUST reproduce

- **Cross-stratum**: stratum k evaluates against fully-materialized strata < k
  (derived edges, residues, from-chain nodes, their closure extensions).
- **Within-stratum, immediate visibility**: interning a from-chain node with a
  bridged shape adds bridge edges whose closure extensions ARE visible to later
  probes in the SAME stratum (e.g. `w_all → n` makes every subject granted on the
  object-wildcard reach `n`, and probe 1 of a later same-stratum TTU member_check
  can read that pair). The incremental backfill sees this through SQL immediately;
  the in-memory mirror must maintain **reachability incrementally on every edge
  add**, not per-stratum-boundary.
- **`_live_keys_of` enumeration order**: names are enumerated when the relation's
  turn comes (nodes interned by earlier strata AND earlier same-stratum relations
  are visible), then sorted. Mirror the iteration structure exactly; a reconcile of
  a support-free name is a no-op either way, but the bar is identity, not
  plausibility.

## 2. Bulk algorithm

Restructure `index_v4/bulk_build.py` minimally: phases R/B/C/P build the in-memory
graph as today; **when `compiled.plans` is non-empty, run the new in-memory
backfill (Phase D below) before Phase W**; Phase W then writes the union of load
and derived state. `connectedstore/build.py`'s bulk branch no longer calls
`proc.backfill()` (the `bulk=False` branch keeps it, unchanged).

### 2.1 In-memory state (extends what phases R/B already hold)

- `m: (NodeKey, NodeKey) → int` — direct multigraph, now also gaining derived
  edges (mult 1) and mid-backfill bridge edges (mult 1).
- `derived_pairs: set[(NodeKey, NodeKey)]` — pairs holding a processor direct edge.
- `explicit: set[NodeKey]` — nodes pinned `implicit=False` (public nodes touched
  by the processor, recorded from-chain nodes).
- `reach` — incrementally-maintained reachability over the direct graph
  (ancestor/descendant sets or equivalent), updated on EVERY edge add with
  immediate visibility (§1 visibility). Exact counts are NOT maintained here.
- `residues: Key → (stars: frozenset[(type,pred)], neg: set[NodeKey],
  upos: set[NodeKey])` — node KEYS, translated to ids at write time.
- Family indexes over the node set (`(type, pred) → names`) and direct-edge
  adjacency (in/out lists with subject-node metadata) for the enumerations.

### 2.2 Phase D (derived state, in memory)

Mirror `backfill()`'s iteration exactly: strata in order; relations in stratum
order; `_live_keys_of` mirrored over the in-memory family indexes (including its
derived-computed recursion and TTU tupleset-family arms), names sorted. Per key,
compute §1's outcome directly (fresh state ⇒ no diffing): stars fold, candidates,
from-chain interning (+bridges, immediately), neg, upos, derived edges, residue.
Every mutation goes through the shared in-memory graph so later evaluation sees it.

The evaluation callbacks reuse the COMPILED plan closures — `plan.check_fn` /
`plan.stars_fn` are called with a new `_BulkEvalContext` implementing the same
callback protocol as `processor._EvalContext` (`leaf_check`, `leaf_stars`,
`derived_check`, `derived_stars`, `userset_check`, `userset_stars`, `ttu_check`,
`ttu_stars`, `tupleset_ttu_check`, `tupleset_ttu_stars`) against the in-memory
state. The boolean expression logic is therefore SHARED, not reimplemented; what is
mirrored is state access only:

- **closure-leaf check** mirrors `widx.check`'s untainted path: up to 4 probes —
  `(subj, obj)`, `(w_any, obj)`, `(subj, w_all)`, `(w_any, w_all)` — with the exact
  declared-shape conditions and missing-node-drops-probe rule, answered by `reach`.
- **derived check** mirrors `widx._check_derived`: `s_name == '*'` → intensional
  stars lookup; userset subject → upos / stars-minus-neg (edge-free, P4); bare
  entity → derived-pair reach probe, then stars-minus-neg; ghost subjects answered
  by stars alone.
- enumerations mirror `tupleset_parents` / `stored_userset_subjects` /
  `derived_stored_parents` / `_leaf_concretes` / `_derived_leaf_neg_ids` /
  `_from_chain_keys` / `_ttu_target_upos_nodes` (X4a/X4b rules included) over the
  in-memory adjacency/residues. `_incoming_concretes` = concrete ancestors via
  `reach`.

### 2.3 Phase W (extended)

1. Final acyclicity check + **path-count DP over the FINAL direct multigraph**
   (rerun of the existing Phase C/P code — P is a pure function of the final
   graph, so one DP at the end replaces per-add region updates).
2. Nodes: `implicit = key not in explicit` (else False), `reference_count` = Σ of
   incident direct multiplicities (derived + bridge edges included). Flush once
   for ids.
3. Edges: `direct = m`, `indirect = P`, `derived = (pair in derived_pairs)`.
4. Residues: per non-empty residue, `version=1`, sorted JSON arrays, neg/upos
   node keys → flushed ids.
5. Outbox: one ADDED row per final pair with `P > 0`, identities denormalized
   from node keys, deterministic sort order (content compared as multiset).

## 3. Risk register (why the gate is shaped as it is)

Medium-high, concentrated in: the 4-probe wildcard mirror (missing-node and
declared-shape conditions), from-chain interning rules (record-only-when-outcome-
recorded, bridges, within-stratum visibility), the derived-flag rule, sticky
explicit promotion of pre-existing implicit public nodes, refcount accounting of
mid-backfill bridge edges, and residue `version` matching. Every one of these is a
projection the identity gate compares byte-for-byte; the corpus must reach them
(§5).

## 4. Lean / CORRESPONDENCE

Identical disposition to P13: the incremental cascade/backfill is the modeled
algorithm; the bulk backfill is an **alternative constructor of the same modeled
state**. No Lean definition becomes dead code (the incremental processor still
runs for every online write, and `backfill()` itself survives as repair path +
reference side). Log in `CORRESPONDENCE.md §8.1` at landing with the extended
identity gate named as the net.

## 5. Identity-gate extensions (land WITH the builder, same commit)

`tests/test_bulk_build.py` already builds every corpus both ways and compares the
four projections + invariants + oracle parity — the boolean/demorgan corpora pin
the new path automatically. ADD corpus coverage for the state-shaping features the
current corpora do not reach:

- (a) raw tuples with a **userset subject over a derived relation** (pre-existing
  implicit public node → sticky promotion, and a derived node with OUTGOING edges,
  so derived edges extend the closure through it);
- (b) **TTU with derived target** (X4b upos lift) AND **TTU with untainted target
  whose from-chain node has a bridged shape** (bridge-on-intern, within-stratum
  closure visibility);
- (c) a **derived tupleset** (`derived-tupleset-ttu` leaf kind);
- (d) **≥3 boolean strata** (nested derived-computed references);
- (e) a case where a from-chain node is recorded in `neg`/`upos` with NO bridges
  (rc=0, implicit=False, edge-free node row anchored by the residue alone).

Each new corpus keeps the existing anti-vacuity style: assert the feature is
actually reached (e.g. a residue with non-empty upos exists; some node is
explicit+rc=0), so the corpus can't silently degrade into not testing the thing.

## 6. Gates before push (gate-runbook)

Extended identity gate + split full suite (§1) + phased `verify.sh`
(`lean` → `conf-heavy` → `conf-rest`, §2) + **multi-seed fuzz sweep (§3 — R4-BF is
named in the worklist as modeled-territory)** + build-throughput before/after for
the boolean/demorgan corpora at ≥2 scales recorded in
`benchmarks/results/PERF_ANALYSIS.md` "Applied". Never two heavy jobs at once.

## 7. Rollback / escape hatch

Unchanged from P13: `bulk=False` keeps the fully incremental build (per-tuple loop
+ incremental `backfill()`), which IS the identity gate's reference side, so it
stays maintained by construction. `DeltaProcessor.backfill()` is not modified.
