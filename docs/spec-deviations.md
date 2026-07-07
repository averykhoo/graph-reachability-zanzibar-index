# Spec deviations log — graph-boolean-ivm-spec.md

Per spec §0: dated entries recording where implementation diverges from the spec's
*adaptable* prescriptions (concrete names, signatures, layouts, mechanisms marked
*(adapt)*), and P0 recon findings where the spec's repo-facts differ from repo reality.
Frozen items (§0 list) are never logged here — a frozen conflict stops the work and goes
to the user instead.

---

## 2026-07-07 — P0 recon findings (spec-fact vs repo-fact)

Baseline: **309 passed in 42.12s** (full suite, green, commit `32ebcf4`).
Compile snapshots for all 6 pure-union fixtures captured in
`tests/snapshots/compiled_ruleset/` (boolean fixtures skip until the P7 flip).

Facts verified against the repo, with deviations from the spec text noted:

1. **Count invariant exact form** (spec §2 "match the core's actual count asserts"):
   `indirect_edge_count >= direct_edge_count` and `indirect_edge_count > 0` per
   persisted row (`index_v4/core.py:120-121`); zero-reachability rows are deleted,
   not persisted. I1 uses this form.

2. **`LookupResult` field names** (spec §6 says "concretes"/"markers"): actual fields
   are `node_ids: set[int]` and `markers: set[tuple[str, str, str]]` — markers are
   **3-tuples** `(type, predicate, variant)` with variant ∈ {'any','all'}
   (`index_v4/wildcard.py:26-29`), not 2-tuple shapes. Residue `stars` rendered as
   markers will use variant `'any'` (subject-side coverage). `excluded_node_ids` is
   added in P5 as specced (additive, default empty).

3. **Oracle surface** (spec §8.4 implies parity over lookups): the oracle is
   **check-only** (`tests/oracle.py:318`) — no lookup/lookup_reverse/add/remove; it is
   stateless and rebuilt from the raw-tuple multiset per comparison. ParityEngine
   therefore asserts *check*-parity 3-ways (oracle + set engine + graph) and
   lookup-parity only between the two live engines. This matches the existing matrix
   harness, which also compares checks only.

4. **No backend has `load_schema`** (spec §8.4 lists it in the common op API): every
   backend takes its schema at construction (`SetEngine.__init__`,
   `make_wildcard_index(schema_info)`, `Oracle(schema, tuples)`). ParityEngine keeps
   construction-time schema loading; `load_schema` exists on ParityEngine itself as
   the constructor argument, not as a retrofit onto the backends.

5. **`check` today is ≤4 *separate* SQL point reads**, not one round trip
   (`index_v4/wildcard.py:235-286` → `core.check_reachable_by_id` per probe). The
   single-round-trip consolidation is P5 work as planned, not a present fact.

6. **`backfill()` precedent is idempotent but NOT chunked** (spec §5.5 says "chunked,
   idempotent, mirroring the wildcard backfill precedent"): `wildcard.py:164-189`
   loads each shape's concrete list in one query. The new derived-relation backfill
   will chunk by object node; the *idempotency* pattern (presence-guarded writes) is
   the part actually mirrored.

7. **Filters do not rewrite and are first-match today**
   (`zanzibar_utils_v1.py:259-283`): Filters are pure admission gates (first match
   admits the raw triple, then `break`); all rewriting is Rule-driven and all-match.
   `Filter.rewrite_relation` (spec §3.3) is a new field with default `None`;
   `RuleSet.apply` keeps the existing first-match admission path for pure-union
   relations **unchanged** (byte-identity gate) and adds the all-match fan-in
   expansion only for triples admitted by rewriting Filters.

8. **`.` is currently a legal identifier char everywhere** (`IDENTIFIER_CHARSET`,
   `zanzibar_utils_v1.py:21`), and the DSL parser never runs the write-validators, so
   relation *declarations* are entirely unvalidated today. The §3.2 lexical lock
   ("schema declarations reject `.` in relation names") is enforced at parse time in
   P2 — a new check in the schema parser, not a change to tuple-side validation
   (entity names keep `.`; fixture data like `domain:example.com` stays legal).

9. **Spec-citation numbering in code comments**: existing code cites "spec §N" against
   `wildcard-materialization-spec.md` / `set-engine-spec.md` (per CLAUDE.md, the
   set-engine spec). New code citing the boolean spec says "boolean spec §N" to avoid
   aliasing.

10. **MemberSet fold is module functions, not operators** (spec §5.3 "lift the fold
    rules/table, not the type"): the star fold to lift is exactly
    `a.stars | b.stars` (union), `a.stars & b.stars` (intersection),
    `a.stars - b.stars` (exclusion) — `setengine/memberset.py:115,121,127` — over
    plain `frozenset[tuple[str, str]]`. `neg` is never folded there (it is
    renormalized against interner-backed populations); the processor computes `neg`
    per spec §5.3 step 2 instead. Nothing bitmap/interner-coupled is imported.

11. **`parse_openfga_schema(schema, object_wildcard_shapes=...)` is the compile
    entrypoint** (spec §3.4 calls it `compile_schema(ast, schema_info) ->
    CompiledSchema`). Kept: the existing entrypoint name and pipeline
    (`parse_schema_ast` → `derive_schema_info` → `compile_ruleset`), extended to
    return a `RuleSet` that additionally carries the compiled boolean artifacts
    (namespace map, plans, leaf_owner, dependents, strata). Names adapted to repo
    convention; contents as specced.

---

## 2026-07-07 — P1 (verification foundation)

1. **Paranoia wiring mechanism** (spec §8.1 *(adapt)*): SQLAlchemy session events.
   `index_v4.invariants.install_paranoia(session, store_id, schema_info)` listens on
   `before_commit` (flush + check inside the transaction; `InvariantViolation` aborts
   the commit) and `after_commit` (re-check in a fresh `Session` on the same bind).
   Wired on by default in `tests.wildcard_helpers.make_wildcard_index` — i.e. every
   test that builds a graph store now runs under paranoia (`paranoia=False` opt-out
   for benchmarks and for tests that corrupt state on purpose).

2. **ParityEngine parity scope** (spec §8.4): per-op parity is *check*-parity
   (unanimous accept/reject + full-grid check vs the oracle). `lookup` /
   `lookup_reverse` are served by the richest live backend without per-op
   cross-assertion, because the oracle is check-only (P0 finding #3) and the two live
   engines use different id spaces; lookup correctness stays pinned by its dedicated
   tests and P5 adds the derived-lookup ones. Grid: universe (names seen in applied
   ops) ∪ ghosts ∪ `'*'`, subjects from Direct restrictions, deterministically
   sampled above a cap.

3. **ParityEngine is additive, not a retrofit**: existing matrix/property tests keep
   their own harnesses (they are the pinned artifact P7 flips); ParityEngine drives
   the handwritten scenarios + new random walks, and is the default engine for all
   *new* phase tests going forward. Suite-wide paranoia comes via
   `make_wildcard_index` (see #1).

4. **Façade rejection-family fix** (validity parity, frozen): `WildcardIndex.
   remove_tuple` leaked `KeyError` when an endpoint node never existed, while the set
   engine and `ReachabilityIndex.remove_edge` reject the same op with `ValueError`.
   Surfaced by ParityEngine's unanimity assert; fixed by translating `KeyError` →
   `ValueError('Non-existent edge cannot be removed')` in the façade, matching
   core.remove_edge.

---

## 2026-07-07 — P2 (compile)

1. **⚠ Decision-15 override: derived-tupleset TTUs are SUPPORTED, not rejected.**
   Decision 15 rejects "a `TTU` whose *tupleset* relation is derived", but the §0
   **frozen** acceptance event requires `demorgans_law_1.fga` to flip 4-way — and that
   fixture is built on three such TTUs (`required_by from non_labels`,
   `assigned from matchable_conds`, `granted from matched_roles`). Frozen list beats
   the decision list, so the shape is implemented as a fourth plan-leaf kind,
   `PDerivedTuplesetTTU`: evaluation enumerates candidate parents from the *subject's
   own target edges* plus a residue scan keyed by the tupleset relation — data-bounded,
   never universe-bounded, so the cost-model row ("symbolic write: data-bounded") is
   preserved. New compile artifact `target_feeders` routes deltas on the (possibly
   untainted) target relations into the processor. The decision's underlying fear
   (object-star-shaped parent sets) is real but answerable: ghosts/star-covered parents
   contribute no members under strict ∀⇒∃ because they hold no target tuples.
   **If the rejection was intentional and demorgans_law_1 was meant to stay 3-way,
   say so — the plan-node + feeder wiring is cleanly removable.**

2. **`Filter.rewrite_relation` is a subclass** (`RewriteFilter(Filter)`), not a new
   field on `Filter`: keeps pure-union compile output (and its P0 snapshot reprs)
   byte-identical. Mechanism-only change; behavior as specced (§3.3).

3. **Namespace keys are `(object_type, predicate)`**, not bare predicate strings
   (§3.4 says `dict[predicate_str → Family]`): the same relation name may be tainted
   on one type and plain on another (`demorgans_law_2.fga` declares `_all_users` on
   two types), and node identity in the store is `(type, name, predicate)`. One dict
   hit either way.

4. **Boolean compilation is opt-in until P7** (`parse_openfga_schema(...,
   enable_boolean=False)` default): compile capability lands green in P2 while the
   default path still raises `UnsupportedByGraphIndex`, because a graph backend that
   compiles boolean schemas but has no delta processor yet would answer derived checks
   wrongly (ParityEngine auto-joins the graph on compile success — the P7 seam).
   P7 flips the default and replaces the refusal tests; until then they stay green.

5. **Added scope restriction (beyond decision 15): wildcard userset restrictions over
   derived relations (`[T:*#P]` with P tainted) are rejected** with a loud
   `UnsupportedByGraphIndex`. Star coverage of `T:*#P` composes through *residue*
   stars of every instance, which the leaf-probe star fold cannot see (needs
   symbolic composition through residues — same hook family as object wildcards on
   derived). No fixture or OpenFGA-standard schema uses this shape; the set engine
   still handles such schemas 3-way.

6. **Indexed dispatch preserves list order across buckets** (position-tagged merge),
   so pure-union first-match admission is provably byte-identical; verified by the P0
   snapshot suite plus the unchanged 330 green tests.

7. **Leaf indexes count both closure-leaves and userset storage leaves** in one
   pre-order sequence (§3.2 says "closure-leaf positions"; tainted userset
   restrictions also need a persisted family for their raw tuples, so they draw from
   the same counter — deterministic and collision-free either way).

8. **Derived-dependency cycles raise `ValueError`** (naming the cyclic keys), not
   `UnsupportedByGraphIndex` — §3.4 reserves the latter for decision-15 scope
   rejections. Cyclic boolean schemas stay set-engine-only permanently.

---

## 2026-07-07 — P3 (models + outbox)

1. **Residue `stars`/`neg` are JSON text columns**, not a JSON list + roaring-bitmap
   bytes (§4's sketch): graph node ids are plain autoincrement ints and residues are
   per-object small, so JSON keeps the column debuggable and avoids coupling the graph
   backend to pyroaring. Layout was explicitly *(adapt)*; uniqueness
   (`store_id, object_node_id`), the relation index, and `version` are as specced.

2. **Write-path return type is now `None`** (`add_edge`/`remove_edge`/`remove_node`/
   `add_tuple`/`remove_tuple`): flips go to `DeltaOutboxV1` inside the transaction.
   Back-compat drain: `index_v4.outbox.drain_deltas(session, store, after_id)` +
   `outbox_watermark`. `PermissionDelta` survives as the drained value type.
   Delta-consuming tests migrated to watermark+drain; stream equivalence pinned by
   `tests/test_outbox.py::test_outbox_stream_matches_legacy_flips` (order included).

3. **`EdgeV4.derived` is written by the façade's processor context** (`processor_writes`
   flag → `ReachabilityIndex._writing_derived` around the direct-edge update), set on
   direct-count increase, cleared when the direct count retires. Equivalent to I5's
   "incoming direct edge on a derived-public family" because exclusivity (P2) already
   guarantees only the processor writes those.

4. **Delta-scoped verification cost**: wired into paranoia's `before_commit` (per-
   transaction range from the last committed watermark; BFS over direct edges per
   affected pair). Full suite 60s → 110s with it on everywhere — accepted while
   prerelease per §8.1; `paranoia=False` opts out (benchmarks).

---

## 2026-07-07 — P4 (delta processor)

1. **Outbox rows denormalize their endpoints** (type/name/predicate captured at
   emission): implicit-node GC can delete an endpoint's node row *inside the same
   transaction* (e.g. removing a subject's last tuple), and the §5.2 delta→key mapping
   must still resolve the flip. Ids alone would leave unmappable rows and stale
   residue-neg ids (an id-reuse hazard under SQLite rowid recycling). A delta whose
   subject node is already gone maps to a *full-object* reconcile so the neg recompute
   prunes the dead id.

2. **Derived-public nodes are pinned non-implicit**: they anchor `ResidueV1` rows
   (star-only objects legitimately have residues with zero edges), and implicit GC on
   the last derived edge's removal would orphan the residue.

3. **§5.2 gap fixed — tupleset-tuple deltas**: a new/removed *tupleset* tuple of a
   `PDerivedTTU` (e.g. `doc:d1 parent doc:d2` under `inherited: viewer from parent`)
   changes the parent set but maps to no key under §5.2's enumeration. New compile
   artifact `tupleset_feeders` routes those deltas to the dependent on the same
   object; `target_feeders` also covers mixed-type untainted TTU targets.

4. **Canonical edge representation (order-independence)**: a derived edge exists iff
   eval-true AND NOT star-covered; star-covered subjects are answered exclusively by
   the residue (`neg` iff expr-false). Without the covered-⇒-no-edge half, a subject
   holding transient concrete support kept its edge across op orders that never
   re-audited it, breaking permutation invariance and the "star-only members: zero
   edges" space rule. Same read semantics, deterministic rows.

5. **§5.3 step-2 neg candidates pull the neg sets of ALL derived-leaf kinds**
   (computed, userset, ttu, tupleset-ttu) — exclusions propagate up strata through
   residues; the ttu case is what makes `inherited`'s neg inherit `viewer`'s
   exclusions on the tupleset parent.

6. **No revisit guard needed in the evaluator**: the compiled plans evaluate against
   persisted lower-stratum state only (edge probes + residues) — there is no recursive
   eval path to guard. The §5.3 guard's intent (a corrupted store must fail loudly,
   never spin) is carried by the cascade's quiescence check and the hard-fail cycle
   guard on derived writes (`InvariantViolation`, not a rejection).

7. **Cascade rounds process every mapped key per round** (spec §5.1's own structure),
   ordered by stratum inside a round; residue-version bumps are carried in-memory to
   the next round's key set (they emit no outbox rows). Quiescence is asserted after
   `len(strata)` rounds.

---

## 2026-07-07 — P5 (reads)

1. **⚠ TTU semantics correction (oracle-pinned): parents are STORED tupleset tuples,
   never computed membership.** The oracle's `ttu_leaf` (tests/oracle.py:429) iterates
   raw tuples with `tup.relation == tupleset_rel` — authentic Zanzibar semantics. My
   P4 derived-tupleset-TTU enumerated *computed* members of the derived tupleset,
   which disagreed with the oracle on demorgans_law_1 (caught by the P5 grid-parity
   walk). Consequence: a derived tupleset with no Direct restrictions can hold no
   stored tuples, so its dependent TTUs are constantly empty — exactly the oracle's
   answer (demorgans_law_1's `unmatchable_conds`/`matched_roles`/`matched_users` are
   ∅ by construction; the fixture's live semantics are in `non_labels` and
   `matchable_conds`). This also retro-simplifies the decision-15 override: no
   residue-scan parent enumeration exists; `target_feeders` fan-out uses the entity's
   stored tuples on the tupleset's storage leaves.

2. **Storage leaves are split from routed leaves**: Direct restrictions of a derived
   relation always compile into their OWN leaf (marked `storage=True` on
   PClosureLeaf/LeafSpec/LeafFamily), never merged with Computed/TTU references in
   the same pure subtree. Rule-routed edges on a shared leaf would otherwise be
   indistinguishable from raw stored tuples, corrupting TTU parent sets (the bug the
   grid walk exposed). Affects derived compile only; pure-union output remains
   byte-identical.

3. **`tupleset_parents` uses DIRECT incoming entity edges** on the tupleset node (not
   closure reachability): a member of a granted userset is not a tupleset parent.
   Note: rule-routed members of an *untainted* tupleset relation still count as
   parents (the pre-existing pure-union TTU-rule behavior); the oracle counts raw
   tuples only. No fixture exercises the difference; noted as a latent gap in the
   pure-union path, not introduced here.

4. **Untainted `check` consolidation counts**: node-id resolution (≤2 concrete
   lookups; w-ids cached) stays separate from the single edge-probe statement
   (`tuple_(subject_id, object_id).in_(keys) ... LIMIT 1`), per the spec's own
   description. The statement-counter test asserts exactly one edge_v4 statement per
   check (zero allowed on a no-key miss).

5. **`lookup_reverse` on derived relations returns the canonical representation**:
   star-covered members appear via markers + `excluded_node_ids` (never enumerated,
   and they hold no edges by the P4 canonical rule); `node_ids` carries only
   uncovered concrete members.

---

## 2026-07-07 — P6 (new-state invariants + backfill)

1. **I7 lineage is per residue ROW**, keyed `(row id, object_node_id)` with absent
   keys pruned each check: empty residues are deleted (spec §4), so a legitimate
   delete-then-recreate restarts at version 1 — the §8.2 wording ("checker keeps
   last-seen versions in memory") tripped on cascades whose intermediate rounds
   emptied a residue that a later round refilled (caught by the demorgans_reverse
   parity walk under paranoia). In-place regressions on a live row still fail.
   Residual corner: SQLite rowid reuse of a just-deleted max-id row for the same
   object could mask one regression — accepted for a prerelease checker.

2. **I9 wiring**: `audit_fixpoint` (all live keys — the paranoia dose) runs per-op in
   the P5/P7 parity walks and per scenario in the processor tests, not inside every
   `session.commit()` — it needs a processor instance, which the commit hook doesn't
   have; the per-commit paranoia layer covers I1–I7/I10–I12 plus §8.3.

3. **I8**: stratification acyclicity is compile-time (`_stratify` raises); the
   runtime re-assert is the cascade's quiescence check, which fails loudly if the
   strata bound is ever wrong.

4. **Backfill enumerates positive leaf families + the public family** per key
   (subtrahends never generate candidates), chunked and idempotent; residue-only
   objects are covered because derived-public nodes are pinned non-implicit (P4).

---

## 2026-07-07 — P7 (matrix flip — THE ACCEPTANCE EVENT)

**Boolean fixture stores run 4-way** (`boolean_wildcards.fga` in the randomized
matrix; the `demorgans_*` trio pointwise across every relation): graph (delta-
processor-maintained, I9-audited per op) · oracle · set engine under both `SetOps`,
unanimous accept/reject, identical checks over the same grids as before. Suite:
411 passed, 0 skipped.

1. **`enable_boolean` defaults flipped to True** in `compile_ruleset` and
   `parse_openfga_schema`; `enable_boolean=False` keeps the historical refusal
   reachable (one test pins it). Refusal tests replaced with compile-success +
   plan-shape assertions (test_schema_ast, test_zanzibar_utils, test_integration).

2. **Set-engine cycle parity now covers boolean schemas**: `compile_ruleset`
   succeeding means `SetEngine._ruleset` exists, so its flow-graph reproduces the
   graph's raw-write edge set (leaf-routed) and both backends reject the same data
   cycles — required for 4-way unanimity. Schemas the graph still refuses
   (decision-15 scope, cyclic derived deps → the new `except (UnsupportedByGraph
   Index, ValueError)`) degrade to no-cycle-rejection as before.

3. **Derived check with a `'*'` object answers False** without node resolution
   (decision 15: no object-star state can exist on a derived relation) — the grid's
   star-object queries surfaced that `_get_concrete` would otherwise reject the
   reserved name.

4. **Compile snapshots now cover boolean fixtures too** (they compile, so the P0
   golden gate extends to them automatically).

5. **Latent graph-vs-oracle divergence NOT introduced here (pre-existing)**: rule-
   routed members of an *untainted* TTU tupleset count as parents in the graph's
   rewrite semantics but not in the oracle's raw-tuple semantics (P5 entry #3). No
   fixture exercises it; the 4-way matrix pins all shapes that are exercised.

---

## 2026-07-07 — P8 (hypothesis campaign)

1. **The ParityEngine is the machine's oracle**: rather than re-implementing per-op
   assertions, both the property layer and the `RuleBasedStateMachine` drive
   ParityEngines, which already assert unanimity, I12, full-grid oracle parity,
   paranoia (I1–I7/I10/§8.3), and the graph's I9 audit on every accepted op.

2. **Schema strategy**: relations generated in topo order over a fixed `user`/`doc`
   universe with a `parent` tupleset — stratifiable by construction, exactly as §9
   prescribes; cyclic boolean schemas asserted separately as compile rejections.

3. **CI profile**: `max_examples=12`, `stateful_step_count=8`, `deadline=None`
   (each example spins up 3–4 full backends); `HYPOTHESIS_PROFILE=deep` gives
   120/25 for local/nightly runs.

4. **The deep profile found two real bugs** (CI profile was green; §11-P8's "fixes may
   reopen earlier phases" happened exactly as predicted). Both shrunk, triaged, fixed,
   frozen as named regressions:

   * **Pinned public-node leak** (`test_add_then_remove_restores_row_multiset` +
     `test_cascade_replay_from_zero`): derived-public nodes are pinned non-implicit
     (P4, residue anchoring), so add-then-remove left an empty pinned node behind,
     breaking exact row-multiset restoration. Fix: the processor GCs its own public
     node once neither residue nor edges remain (`_gc_public_node`; refcount 0 ⇒ no
     closure rows can reference it). Frozen:
     `test_processor.py::test_regression_public_node_gc_on_add_remove`.
   * **Duplicate-raw-add divergence** (stateful machine): adding the SAME raw tuple
     twice then removing once left the graph's ref-counted edge at count 1 while the
     set engine/oracle (raw tuples are a SET; TupleV1 unique) dropped it — a
     pre-existing pure-union divergence no pool ever exercised (matrix pools filter
     `raw not in present`). The graph core stays ref-counted (two *different* raw
     tuples may rewrite to the same derived edge — counts are load-bearing there);
     idempotence belongs at the raw-tuple API boundary, implemented in
     `ParityEngine._apply`. Frozen:
     `test_parity_engine.py::test_regression_duplicate_raw_add_is_idempotent`.

   Deep-profile status after fixes: all property tests + the stateful machine green
   at `max_examples=120` / `stateful_step_count=25`. Final suite: 425 passed.

## 2026-07-07 — P9 (docs)

README: boolean-operators section rewritten (both backends), rewrite-table rows
updated, memoization-spectrum + cost-model tables reflect derived predicates and the
outbox, new "Booleans in the graph index" section with the honesty notes (write
amplification multiplicative in strata depth; symbolic-write full-object reconcile
cost; TTU stored-tuple semantics; paranoia ~2× suite time), non-goals updated
(boolean-in-graph delivered; async workers/pruning/residue-GC hooks listed).
CLAUDE.md: layout notes for processor/outbox/invariants, compile-layer description,
4-way matrix + ParityEngine + paranoia + hypothesis testing conventions, derived
gotchas, spec pointer now names `graph-boolean-ivm-spec.md` (the earlier two spec
files were removed from the working tree by the author; noted as living in git
history).

---

## 2026-07-07 — connected-store round, S4 (build_index)

**P6 backfill enumeration gap found and fixed** by the built-vs-live equivalence
test: `_live_keys_of` discovered objects via leaf *families* only, so derived
relations with no storage family of their own — TTU-only (`inherited: viewer from
parent`) and computed-only (`approver: viewer`) shapes — were never reconciled by
`backfill()`/`audit_fixpoint` (live maintenance reaches those objects via
dependents-invalidation, so the gap was invisible until an offline build). Fix:
enumeration now follows what non-storage derived leaves *read* — the tupleset-tuple
family for `derived-ttu`, the referenced relation's live keys for
`derived-computed`/`derived-tupleset-ttu` (strictly lower stratum ⇒ recursion
terminates). P6's own backfill test had only closure-leaf relations, which is why it
passed.

---

## 2026-07-07 — connected-store round, S7 (concurrency & stale reads)

Three findings, all product-relevant:

1. **Cursor lost-update**: two concurrent appliers could read the same cursor value
   before either committed and double-apply log rows onto ref-counted state.
   `advance_index` now takes the index store's write lock (`_lock_store`) **before**
   reading the cursor and re-reads it fresh — FOR UPDATE on PostgreSQL/MySQL; on
   SQLite the database write lock + caller retry-on-busy give the same serialization.

2. **W-id cache cached misses**: the wildcard façade cached `None` for absent w
   nodes, invalidated only by the session's own writes — sound single-session, wrong
   for a replica reader (another session creates the w node; the reader's probes
   stay off forever). Misses are no longer cached; positive ids remain safe (a GC'd
   w node had no wildcard state left, so a dead-id probe is correctly False).
   `ConnectedStore.refresh()` is the replica poll API: fresh snapshot + rebuilt
   evaluator + cleared w-id cache.

3. **pysqlite defaults tear snapshots** (the spec §1.8 caveat, met in practice):
   SELECTs run in autocommit, so multi-statement reads straddle commits. The
   concurrency tests install the SQLAlchemy-documented workaround
   (`isolation_level=None` + BEGIN on the `begin` event) and `journal_mode=WAL` —
   snapshot-isolated readers that never block the writer, the honest local
   simulation of primary-write/replica-read.

---

*(subsequent phases append below)*
