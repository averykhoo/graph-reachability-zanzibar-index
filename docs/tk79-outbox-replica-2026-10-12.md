# TK79 — does a `drain_deltas` replica really need the late reconcile-time-GC rows?

**FROZEN 2026-10-12 (`TK79` closed, session `2026-10-12c`) — provenance, not a living document.**
Was an ACTIVE-PLAN (`docs/README.md` §3), opened the same day. Status lines below are
as-of-then; live state is `python scripts/task.py show TK79`, never this file.
Corrections are appended dated at the top, never edited into the body.

Provenance labels are per claim: **READ** (verified first-hand against the live tree by
the session that wrote the line), **REASONED**, **UNVERIFIED** (reported by a subagent or
a prior session and *not* re-checked here).

---

## Correction 2026-10-12c (fix-1, after the adversarial review of TK79)

The review found that §4 and §5 overstated coverage, and that §3.3 mislabelled a step.
Each point below was re-measured by this session (READ unless labelled otherwise). Probes:
`.scratch/uc-2026-10-12c/tk79-fix/probe_sub.py` and `probe_recycle2.py`, transcribed here.

1. **There are THREE late-emission sites, not two, and the third was unpinned.**
   `_sync_entity_middles(*entity)` is called at the end of BOTH
   `DeltaProcessor._gc_subject_node` and `DeltaProcessor._gc_public_node`. The old S2 row
   suppressed both and saw 1 red, which read as both being pinned. Split per site, the
   review measured S2pub at 1 failed and S2sub at 7 passed. A probe asserting that the
   `_gc_subject_node` call emits no row ran 24 passed over `test_tk79_outbox_replica`,
   `test_i14_crossing_middles` and `test_cascade_quiesce_gc`. **Why it never emits there
   (REASONED, consistent with the probe):** on those fixtures every recorded residue
   subject is a user or a `group#member` userset, and neither type has a crossable shape,
   so `wildcard.py::WildcardIndex._sync_entity_middles` returns at its crossable-type check.
   **Witness (READ):** `tests/test_tk79_outbox_replica.py::SUBJECT_GC_SCHEMA`, which makes
   `folder#member` a subject of `doc.editor` / `doc.blocked` under
   `doc.restricted: editor but not blocked`. Adding and then removing
   `folder:f1#member editor doc:d1` works like this. Reconcile records the userset in
   `restricted`'s upos and promotes it explicit, so it outlives the raw remove. It is the
   entity `folder:f1`'s only real node. When the cascade un-records it, `_gc_subject_node`
   deletes it, and `_sync_entity_middles('folder','f1')` strips the middle
   `folder:f1#viewer`. Outbox rows 8..10 are all REMOVED:
   `viewer@folder:f1 -> viewer@folder:*`, `viewer@folder:* -> viewer@folder:*`, and
   `viewer@folder:* -> viewer@folder:f1` (node pairs (3,4), (5,4), (5,3)).
   `check_invariants` is green. On this fixture `proc._settle is None`, so the window is
   NOT the TK73 settle shape. The pin is about what a replica receives, not about lateness.
   Pin: `test_subject_gc_strip_arm_rows_reach_the_replica`.
2. **The oracle leg is transitive, and now says so.** The replica is an `Edge`-pair
   changelog, and residue rows are not in the stream, so it cannot answer derived
   membership on its own. Replica == oracle holds as replica == primary pair set (these
   tests) composed with primary == oracle:
   `tests/test_cascade_quiesce_gc.py::test_the_witness_generalises_on_its_star_target` for
   the TK73 family, and a per-write grid check inside the new test for its own fixture.
   The module docstring now carries this.
3. **§3.3 is superseded.** Its query, `folder:q#... viewer folder:x`, is impossible by
   type under `SCHEMA` (viewer is `[user] or admin from parent`), so oracle and primary say
   False whatever the bug does. The test now writes `user:u8 admin folder:q`, which takes
   ids 7 and 8, and then `user:u9 editor folder:x`, which makes id 9 = `('...','user','u9')`.
   The deficient replica's stale `(9, viewer@folder:x)` then reads as "user:u9 viewer
   folder:x". That claim is TYPE-LEGAL and FALSE: oracle False, primary False. The control,
   `user:u8 viewer folder:x`, is oracle True and primary True. **Label correction:**
   resolving id 9 to a key presumes a lookup against the primary's `Node` table, because
   `drain_deltas` carries ids only. That step is **REASONED**, not READ.
4. **Sabotage table, re-run 2026-10-12c** (`-q -rf -p no:randomly`; S2pub and S2sub also
   ran `test_i14_crossing_middles` and `test_cascade_quiesce_gc`; every mutation was
   restored from a temp copy and checked with `cmp`):

| id | what was broken | result |
|---|---|---|
| S1 | `_maybe_remove_bridges` rows in `_gc_subject_node` deleted | 5 failed, 3 passed (unchanged attribution) |
| S2 | the `_sync_entity_middles` rows suppressed at BOTH sites | 2 failed, 6 passed: both strip-arm tests |
| S2pub | only the `_gc_public_node` site | 1 failed, 24 passed: `test_strip_arm_rows_reach_the_replica`, `{(3, 4), (5, 3), (5, 4)} == set()` |
| S2sub | only the `_gc_subject_node` site | 1 failed, 24 passed: `test_subject_gc_strip_arm_rows_reach_the_replica`, `AssertionError: after remove` / `{(3, 4), (5, 3), (5, 4)} == set()` |
| S2subprobe | assert that the `_gc_subject_node` site emits nothing | 1 failed: `AssertionError: SUBJECT-STRIP-EMITTED` (the review saw 24 passed before the test) |
| S3 | `_Replica` ignores REMOVED | 8 failed |
| S4 | `_deficient_pairs` skips nothing | 3 failed: both strip-arm "redundant" guards, plus load-bearing `stale=[]` |
| S5 | `oracle_true_seen` given no tuples | 1 failed: `grid never answers True -- vacuous` |

---

## 1. Verdict

**The justification is TRUE, and it was unpinned; it is now pinned.** The comment in
`src/zanzibar/graphindex/processor.py::DeltaProcessor._run_cascade` (the quiescence block,
"an external ``drain_deltas`` replica must see them") does not need correcting. Measured
below: a replica that applies the drained stream reproduces the primary's closure row set
exactly. The same replica fed the stream minus the rows emitted inside a reconcile-time GC
keeps the GC'd node's pairs forever. On SQLite, the next node that recycles that id
inherits them, which gives a membership-WRONG answer (§3.3).

One nuance the comment already states correctly (READ): the rows are membership-NEUTRAL
*at the semantic level*. The stale pairs a deficient replica keeps are true facts about a
userset that the primary now expresses through a wildcard bridge instead (§3.2). The harm
is to the replica's mirror of the closure, and through id recycling to membership.

Pin: `tests/test_tk79_outbox_replica.py` (§4).

## 2. What the outbox stream IS (READ, 2026-10-12)

- `src/zanzibar/graphindex/core.py::ReachabilityIndex._emit` is called with `"ADDED"` when
  an `Edge` row is created (`indirect_edge_count` goes 0 -> positive) and with `"REMOVED"`
  when an `Edge` row is deleted (both counts reach 0). So the stream is an exact changelog
  of the store's `Edge` (subject_id, object_id) pair set, with no counts. The replica this
  item is about is therefore a SET of pairs: ADDED inserts and REMOVED deletes. "Balanced"
  means ADDED only ever names an absent pair and REMOVED a present one.
- `src/zanzibar/graphindex/outbox.py::drain_deltas` renders rows as `PermissionDelta`
  (store_id, subject_id, object_id, action). That is node IDS only, so a `drain_deltas`
  consumer keys by id. The denormalized endpoint columns exist only on `DeltaOutbox`
  (`outbox_rows`).
- `src/zanzibar/graphindex/invariants.py::verify_outbox_deltas` (§8.3) checks every row that
  IS present against BFS reachability. It cannot see a row that was never emitted, so it
  does not guard this property (REASONED from its body: it iterates `outbox_rows` only).
- No in-tree consumer replays the stream (the row's 2026-09-18 / 2026-10-04g grep,
  UNVERIFIED here beyond `grep drain_deltas src/`: it occurs only in `outbox.py` and in
  the processor comment).

## 3. Measurements (READ, 2026-10-12; probes `.scratch/uc-2026-10-12c/tk79/probe{1,2}.py`, transcribed here because `.scratch/` is gitignored)

### 3.1 TK73 witness (`tests/test_cascade_quiesce_gc.py::SCHEMA`, `_witness(E)`)

An id-keyed replica was fed `outbox_rows` after each committed write, alongside a
"deficient" replica that skipped every row emitted inside
`DeltaProcessor._gc_subject_node` / `_gc_public_node` (window = the outbox watermark
before and after the call):

    [x] add  folder:* parent folder:x : settle=None  full==prim True  deficient==prim True
    [x] add  folder:x parent folder:y : settle=None  full==prim True  deficient==prim True
    [x] remove folder:x parent folder:y: settle=SettlePass(keys=(('folder','owner','x'),), changed=())
                                         full==prim True  deficient==prim False
                                         extra-in-deficient=[(9, 3), (9, 4), (9, 5)]

The same holds for E in `x, z, w, q` (`STAR_TARGETS`). For E=`y` (`STAR_TARGET_NO_GC`)
nothing is GC'd and both replicas match. The skipped window is `_gc_subject_node(9)`,
rows 13..15, which are exactly the "rows #13/#14/#15" of the TK73 docstring.

### 3.2 What the late rows are

    late row 13 REMOVED ('admin','folder','x') -> ('admin','folder','*')
    late row 14 REMOVED ('admin','folder','x') -> ('viewer','folder','x')
    late row 15 REMOVED ('admin','folder','x') -> ('owner.0','folder','x')

Node 9 is the implicit userset node `admin@folder:x`, collected at reconcile time. With
the star parent `folder:* parent folder:x` still present, `admin@folder:x` is still
semantically a viewer of `folder:x`. The primary now expresses that through the
`admin@folder:*` bridge rather than a concrete node, so the late rows are
membership-neutral at the userset level (REASONED, consistent with the comment and with
`tests/test_cascade_quiesce_gc.py::test_witness_commits_and_agrees_with_the_oracle`).

### 3.3 Id recycling turns a neutral miss into a wrong answer (SQLite)

**SUPERSEDED 2026-10-12c, see Correction 3 at the top: the query below is impossible by type, and the id resolution is REASONED.**

After the x-witness, two further writes were applied: `user:u9 admin folder:q`, then
`folder:q parent folder:x`. The new node `('...','folder','q')` takes **id 9** (SQLite
rowid is max+1, and 9 was the max when it was deleted). The deficient replica still
holds `(9,3),(9,4),(9,5)`, which now resolve to "`folder:q` reaches `viewer@folder:x`". The
primary holds no such pair, and the full replica matched the primary after both writes.
On PostgreSQL a sequence does not recycle ids. The stale pairs still survive there and
still diverge from the primary's closure, but no wrong *resolution* follows (REASONED).

### 3.4 Second emission site (`tests/test_i14_crossing_middles.py` fixture)

The `_sync_entity_middles` strip arm (TK75) is also load-bearing. Replaying
`_WITNESS add, remove, _OWC_GRANT add, _STAR_PARENT add, _WITNESS add, remove,
_STAR_PARENT remove`, the full replica equals the primary after every write. The
deficient replica diverges from the first remove onward (3 GC-window rows, later 11).

## 4. The pin (landed 2026-10-12, uncommitted at time of writing)

`tests/test_tk79_outbox_replica.py`:
- `test_drained_replica_matches_primary_closure[E]`: the TK73 witness for every E,
  balanced replay through `drain_deltas`, replica == `Edge` pair set after every commit,
  plus vacuity guards (a GC window emitted rows and a settle pass ran, for E != y).
- `test_strip_arm_rows_reach_the_replica`: the same property on the I14 fixture.
- `test_late_gc_rows_are_load_bearing`: the permanent sabotage. A replica that skips the
  GC-window rows diverges, and after id recycling it claims a pair that the primary's
  `check` and the oracle both deny.

Sabotage record: see the module docstring (the literal red output lives there).

## 5. Sabotage log (SUPERSEDED by Correction 4 at the top; READ, 2026-10-12c; `pytest tests/test_tk79_outbox_replica.py -q -rf -p no:randomly`)

| id | what was broken | result |
|---|---|---|
| S1 | product: outbox rows emitted by `_maybe_remove_bridges` inside `_gc_subject_node` deleted (the "just drop them" alternative TK73 rejected) | 5 failed: `[x,z,w,q]` replica-only `[(9, 3), (9, 4), (9, 5)]`; load-bearing test on its settle guard |
| S2 | product: the same suppression around `_sync_entity_middles(*entity)` in both GC functions (TK75 strip arm) | 1 failed: `test_strip_arm_rows_reach_the_replica`, `{(3, 4), (5, 3), (5, 4)} == set()` |
| S3 | instrument: `_Replica` ignores REMOVED | 7 failed |
| S4 | instrument: `_deficient_pairs` skips nothing | 2 failed (strip-arm "redundant", load-bearing `stale=[]`) |

Each product site is caught by a different test. Neither test covers both sites. All four
were restored from a temp copy, and `git status --short src/` was clean afterwards. The
processor.py comment then gained a pointer to the pin (a comment-only change).
