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

   **Resolved 2026-07-13 — KEEP (owner decision).** Avery confirms the decision-15
   override stands: derived-tupleset-TTU support is retained and `demorgans_law_1`
   stays 4-way (not reverted to 3-way). Consistent with P5 #1 below, which corrected
   this path's semantics (TTU parents are STORED tupleset tuples) rather than removing
   it — the plan-node + feeder wiring stays.

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

   **Resolution (2026-07-13, fixture added — `tests/test_pure_union_ttu.py`).** The
   gap is **unreachable on the graph; closed as benign.** For rule-routed members to
   land on a tupleset node the tupleset relation would need a Computed/TTU arm (a
   rewrite rule only ever lands edges on the relation it *defines*, `_rewrite_rule` /
   `_emit_expr`), but `_validate_ttu_tuplesets` (zanzibar_utils_v1.py) **rejects** any
   untainted tupleset that is not directs-only with `UnsupportedByGraphIndex`. So the
   only untainted tuplesets that compile receive raw stored edges exclusively, and
   `tupleset_parents` cannot see a rule-routed member — the over-granting shape never
   materializes. The fixture pins this three ways: the graph *rejects* the rule-routed
   schema at compile time (both `enable_boolean` paths); the set engine and oracle
   (stored-only) *accept* it and agree it does **not** grant `can_read` through the
   rule-routed `backlink` arm (no over-grant), while a genuinely stored `linked` tuple
   does grant; and on the compilable directs-only sibling all three backends agree
   pointwise. No backend fix was needed — the guard already adjudicates to the
   oracle/Zanzibar stored-parent semantics.

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
   *(Correction, review round: this claim was wrong — the corner produced a FALSE
   POSITIVE (a legitimate same-transaction recreate reusing the max rowid would trip
   I7 and abort the commit), not a mask. Fixed: version-1 rows always restart their
   lineage; the residual blind spot is now an in-place regression to exactly 1.)*

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

## 2026-07-07 — external review round (triage + fixes)

An external code review raised seven issues; verified against the code, five were
real (two with wrong details), two were by-design/documentation items. All
addressed:

1. **Cross-session freshness-token gap (real, the important one).** The
   `at_least` fallback consulted the set engine's in-memory state, which is only as
   fresh as its last rebuild — a write committed after a reader opened was not
   honored by that reader's tokened reads. (Our own S7 test masked it: the reader
   opened *after* the write.) Fix: `TupleSource.evaluator_watermark` tracks exactly
   what the in-memory evaluator reflects; a tokened read whose token exceeds it
   rebuilds on demand (the honest cost: one rebuild per stale tokened read), and if
   the token is *still* not visible — the session's read snapshot predates the
   write — raises `StaleRead` rather than silently serving stale under an explicit
   freshness demand. Rollback paths reset (not max) the watermark so a discarded
   token can never overstate freshness.

2. **`lag()` materialized every pending row (real).** Now a `SELECT COUNT(*)`.

3. **Pure-union TTU divergence (real, previously logged as latent; now closed).**
   An *untainted* TTU tupleset with computed/rewritten arms would let the graph's
   TTU rule propagate rewrite-derived members that the oracle and set engine
   (stored-tuple semantics) never see. Fix: compile-time rejection
   (`UnsupportedByGraphIndex`, "stored tuples only") — exactly how OpenFGA
   validates its models. Derived (tainted) tuplesets are exempt: their storage
   leaves already isolate raw tuples. Fixture scan confirmed every untainted
   tupleset in the repo is Direct-only, so nothing existing was rejected.

4. **`remove_node` dangling-edge worry (speculative — the counting theorem +
   `_lock_store` + I1's missing-node check cover it).** Hardened anyway with a
   cheap in-transaction post-condition: any edge row still referencing the deleted
   node fails loudly instead of persisting a ghost.

5. **I7 rowid corner (reviewer right, our log wrong).** The corner was a false
   positive, not a mask — corrected above and fixed in code (version-1 lineage
   restart).

6. **Façade multigraph semantics (by design).** `WildcardIndex.add_tuple` is
   deliberately ref-counted (rewrite fan-in requires it: two different raw tuples
   may derive the same edge and must retire independently); set-semantics
   idempotence lives at the raw-tuple boundary (`TupleSource`, harness adapters).
   Now documented loudly on the method itself.

7. **`is_valid_identifier` naming (fair nit).** Docstring now states the sentinels
   (`'*'`, `'...'`) are admitted positionally by `_require`, never by the charset
   predicate.

---

## 2026-07-08 — external review round 2 (triage + fixes)

Two claims; one confirmed, one half-right:

1. **`_find_leaf_node` crash on derived-userset leaves (CONFIRMED).** The helper
   only knew TTU node kinds, so a FULL reconcile of any plan holding a tainted
   userset restriction (`[T#P]` with P derived) died with "plan node not found".
   The reviewer's diagnosis of the blind spot was exact: no fixture places a
   tainted userset inside a plan, and the cheap per-subject path masked the naive
   repro — the trigger is any full reconcile (symbolic delta, dependency
   invalidation, `audit_fixpoint`, `backfill`). Fixed (userset leaves match on
   their storage predicate); the previously-unexercised PDerivedUserset path is
   now covered end-to-end against the oracle, including the three-relation
   invalidation chain (`gblocked` → `member` → `banned` → `viewer`) both ways.

2. **`WildcardIndex.remove_node` missing (half-right).** The quoted "docstring" is
   actually `wildcard-materialization-spec.md` §remove_tuple — a spec-mandated
   façade API that was never implemented; that part stands, and it now exists
   (bridge-strip first, derived-exclusivity guard, KeyError→ValueError parity).
   The claimed SYMPTOM was empirically refuted: core `remove_node` retires bridge
   edge rows fine via the count math (no dangling rows, no post-condition trip).
   The *actual* value of strip-bridges-first, which the review missed: the core's
   node-removal shortcut doesn't decrement neighbour reference counts, so façade-
   level bridge removal keeps w-node refcounts honest and lets an orphaned w node
   be implicit-GC'd instead of lingering with a stale count. (The general
   neighbour-refcount staleness of core `remove_node` is pre-existing and remains
   — noted as a core wart; it affects only GC eagerness, never reachability.)

---

## 2026-07-08 — blind self-audit (7 fresh-context agents; consolidated fixes)

Seven agents audited the code blind (oracle, set engine, graph core, wildcard
façade, processor, schema layer, connected store). Findings triaged to 7 CRITICAL
+ 12 HIGH confirmed; everything below is fixed and pinned in
`tests/test_blind_audit_regressions.py` (plus suite-local additions). Four were
**semantic decisions**, flagged for veto:

**D1 — `'*'`-subject queries are flow-through (SEMANTIC CHANGE).** Live 3-way
divergence: for a star that reaches a relation only *through a granted userset*
(`user:*` member of `group:g`, `g#member` granted viewer), the graph answered True
while oracle + set engine answered False ("per-branch only"). Per-branch was
structurally unimplementable in the graph (the closure cannot distinguish how the
star arrived), and the flow-through reading matches OpenFGA's literal-subject
treatment (`user:*` is a subject like any other; membership composes). Oracle and
set engine now flow through; the graph was already correct. The wildcard spec's
"intensional, per branch" wording (§7) now applies to **object**-side stars only.

**D2/P4 — userset subjects on derived relations are edge-free (`ResidueV1.upos`).**
CRITICAL: a derived EDGE from a userset node (`group:g#member` satisfying the
expression) is transitive — the closure grants every member, silently defeating
each member's own pointwise exclusion (`a but not b` leaked to excluded members).
Boolean membership does not distribute over a userset's members, so it must not be
an edge. New residue column `upos` records true userset memberships
(pos-without-transitivity); check/lookup/lookup_reverse answer userset-shaped
subjects from `upos` ∪ (stars ∖ neg) with no closure probe; reconcile settles
usersets wholesale (step 2c) and audits edges over bare-entity subjects only. I6
extended (upos: live + userset-shaped + uncovered + edge-free + disjoint from neg).

**D3 — userset restrictions in tuplesets rejected (OpenFGA model rule).** A
userset restriction on a tupleset relation bypassed taint analysis entirely and
had drop-the-predicate parent semantics no spec defines. Wildcard restrictions in
tuplesets stay ALLOWED — star tuplesets are this repo's deliberate object-wildcard
extension (w_all machinery, pinned by `test_wildcard_through_from_chain`);
`derive_schema_info` now derives their TTU through-shapes
(`(parent_type, target_rel)`) so the rewritten write resolves on the graph (this
was the oracle-agent's wildcard-tupleset divergence).

**D4 — object-wildcard shapes on TTU targets of tainted plans rejected**
(decision-15 family). Derived evaluation probes the closure directly and cannot
see w_all state, so such a grant would be silently invisible to the plan.

**D4 widened (review 3) — the decision-15-family guards run on the EXPANDED
shape set and cover every TTU position.** `_reject_object_wildcard_scope` runs
twice in `compile_ruleset`: on the declared shapes before plan construction and
again after `_expand_object_wildcard_shapes` closes them over the rewrite rules
(a shape one Computed/TTU hop upstream of a rejected position is the same shape
post-expansion — guarding declared shapes only re-admitted the rejected class,
and the first legal star-object write crashed the delta processor). Newly
rejected alongside the original two: shapes expanding onto compiled leaf
predicates, shapes on the TUPLESET relation of a tainted plan's TTU
(`tupleset_parents` reads direct stored tuples and never consults w_all —
silent wrong denials with no invariant tripping), and star-tupleset
through-shapes landing on a derived TTU target (an underived wildcard userset
over a derived relation; it structurally violated I3). The set engine now
adopts the compiled RuleSet's expanded `SchemaInfo`, so star-object write
admission agrees across backends.

The rest, by area:

* **Memo poisoning under the recursion guard (CRITICAL, oracle + set engine +
  expand).** The revisit guard returns a provisional False, but frames computed
  *while the guard was active* were memoized as final — `reader=True`,
  `editor=True`, `reader and editor=False`, internally inconsistent; and since the
  oracle shared the scheme, the validation matrix was structurally blind to it.
  Fixed with a Tarjan-lowlink-style guard in all three evaluators (memoize a frame
  only if its subtree consulted no in-stack key above it). Both auditor repros
  pinned.
* **Processor:** `_fan_out` called a method deleted in the P5 rework
  (AttributeError on any tainted-target fan-out); `_find_leaf_node` resolved leaves
  by first-match instead of the compile-time binding (wrong-node reconciles) — plans
  now carry `leaf_nodes` zipped to `leaves`; userset-storage deltas with a userset
  subject now force a full reconcile; `userset_check` answers the exact-granted
  userset directly from stored tuples.
* **Graph core:** the node-removal shortcut never decremented neighbour
  reference_counts (the review-2 "wart", upgraded to CRITICAL: it defeats bridge GC
  and `_gc_public_node` under churn) — debits are computed from incident direct
  edges and applied at the tail with the same implicit-GC rule, *after* the
  expansion loops so every REMOVED delta still denormalizes live endpoints (I10).
  New **I13**: `reference_count` == direct-edge degree, checked after I3 (bridges
  are the more specific diagnosis for bridge corruption). `add/remove_edge_by_id`
  re-verify endpoint liveness inside the store lock (TOCTOU); self-edges rejected
  as 1-cycles; `add_edge`/`remove_edge` lock before resolution.
* **Wildcard façade:** the `_w_id` cache returned stale ids across
  rollback/session boundaries — removed (resolve fresh; `_invalidate_w_cache` kept
  as a documented no-op); `remove_node` rejects `name='*'` cleanly.
* **Schema layer:** tokenizer hung on a stray `]` (zero-progress loop) — now a
  ValueError; multi-`#` and empty-predicate restrictions rejected; unrecognized
  schema lines and duplicate type/define blocks rejected; `'.'`-reservation
  enforced on restriction/Computed/TTU references; exclusivity asserts promoted to
  ValueError; single-child union/intersection collapsed (and empty children
  rejected) in `_json_rewrite`.
* **Oracle (O4):** its independent parser had the same stray-`]` hang and silent
  multi-`#` misparse — mirrored fixes (independence contract kept: no production
  imports).
* **Connected store:** `build_index` re-reads the watermark after snapshotting and
  raises on movement (lost-write race); idle `catch_up` rolls back instead of
  pinning its read snapshot (and, on PostgreSQL, holding the store lock) forever;
  the constructor commits its bootstrap so a second session can reopen
  self-describing; ParityEngine catches ValueError too, so cyclic boolean schemas
  degrade to 3-way instead of being unconstructible (X7 — exactly the schema class
  where the memo bug lived); tokens documented as store-local (X6).

Full suite after: 497 passed (18 of them the new regression pins).

---

## 2026-07-12 — lookup-surface oracle gate (`tests/test_lookup_oracle.py`)

Closes the gap logged as P0 recon finding #3 / P1 finding #2: the oracle is
check-only, so `lookup` / `lookup_reverse` / `expand` had **no independent
reference** — ParityEngine serves them from a single "richest live backend"
with no cross-assertion. The new gate composes `oracle.check` over a
schema-derived candidate universe into brute-force reference lookups
(`oracle_lookup(subject, rel, T) = {n | check(subject, rel, T:n)}` and its
reverse) and asserts BOTH backends' lookup surfaces against it after every
accepted op of seeded add/remove walks (drained to the empty store) plus
dense scripted states — **exact (two-sided) where the API is exact, one-sided
where the API drops information by design** (set `lookup_reverse` drops `neg`,
`setengine/engine.py:738-740`). Coverage: `wildcards.fga` (+object wildcards),
`boolean_wildcards.fga`, `demorgans_reverse.fga`. Permanent tamper tests
(leaked id, dropped id, cleared exclusions, dropped neg) prove the checkers
bite. 15 tests: 10 pass + 5 **strict xfails** — the xfails pin GENUINE
divergences (the properties were NOT weakened around them; fix the surface,
then flip the xfail):

1. **X4 — CHECK-level graph divergence on derived-TTU userset subjects (the
   significant one; wider than lookups).** On a derived TTU, userset-shaped
   subjects whose truth flows through a stored tupleset parent answer False
   on the graph index where the oracle AND both set engines answer True. Two
   shapes: (a) the from-chain userset itself — after `doc:d1 parent doc:d2`,
   `check('viewer','doc','d1','inherited','doc','d2')` = graph False / others
   True (the graph's own *untainted* TTU path answers the analogous
   `wildcards.fga` query True via the rewrite edge); (b) cross-object userset
   membership lift — after `group:g1#member editor doc:d2` +
   `doc:d2 parent doc:d1`, `check('member','group','g1','inherited','doc','d1')`
   = graph False / others True, even though the graph answers the `viewer`
   query on `doc:d2` True: the dependent's residue `upos` never receives
   cross-object userset memberships (reconcile settles usersets from the
   object's OWN stored tuples only). Also reproduces on
   `demorgans_reverse.fga`. The matrix/property grids never query userset
   subjects on derived-TTU families, which is why it survived P7. Formal
   scope note: the shape is outside `W4Fragment` (`computedOnly` bans `ttu`
   leaves in derived defs; `PDerivedTTU` was already a documented proof gap),
   so the Lean theorems are untouched — but the repo-wide "identical
   semantics" claim now carries this known, pinned exception
   (`formal/FINAL_REVIEW.md` §3 note) awaiting a fix.
2. **X1 — set forward `lookup` drops TTU-only objects.** Objects reachable
   ONLY via TTU whose `(type, name, relation)` key was never interned are
   silently missing (`engine.py:753`: the candidate universe is interned keys
   only) where set-engine spec §6.4 prescribes reverse propagation including
   TTU. The graph returns them.
3. **X2 — graph `lookup_reverse` on a derived relation with `o_name='*'`
   raises `ValueError`** (the `_get_concrete` → `core.node` reserved-name
   guard) where `check` answers False (P7 #3) and the set engine returns
   empty — an inconsistent refusal, not a wrong grant.
4. **X3 — set `expand`/`lookup_reverse` cannot represent an oracle-true
   uninterned from-chain userset subject** (no interned id exists; `check`
   answers it True via the from-chain rule, and the graph returns its node).
   Representational, not evaluative.

---

## 2026-07-13 — set-engine lookup completeness (X1 + X3 fixed)

Both set-engine entries from the 2026-07-12 gate are fixed and their strict
xfails flipped to plain regression pins (`tests/test_lookup_oracle.py`); the
gate's S1/S3/S4 properties are now **exact two-sided over the whole candidate
grid** (the one-sided uninterned escapes were removed, not relaxed).

1. **X1 root cause**: `SetEngine.lookup`'s candidate universe was the interned
   keys, and an object reachable only through TTU (or a Computed hop over
   another relation's stored tuples) never interns its own
   `(type, name, relation)` key — no id existed to return. **Fix (spec
   set-engine §6.4 reverse propagation, mechanism adapted)**: reverse
   propagation is realized at WRITE time instead of per-lookup. Compile-time
   tables (`_candidate_reverse_deps`) invert the schema: for each stored tuple
   of relation `r` on `(T, n)`, `_apply_add` also interns `(T, n, R)` for every
   relation `R` on `T` that reaches `r` through Computed chains or holds a TTU
   over tupleset `r` (any TTU-derived membership implies exactly such a stored
   tuple on the object — TTU parents are stored tuples, P5 #1). All expression
   positions count (subtrahends included): over-approximate candidates are
   pruned by lookup's check-verification. `_apply_remove` releases
   symmetrically, so interner refcounts stay balanced, `rebuild()` replays
   identically (conformance `driven == rebuilt` fingerprints re-verified, incl.
   full-churn drain-to-empty), and reads remain side-effect-free. Forward
   `lookup` markers are now intensional and exact by construction: one
   star-object `check` per **declared** relation (instead of per interned star
   key), so star coverage arriving through Computed/TTU hops surfaces as a
   marker. Cost: lookup stays a check semi-join, `O(declared relations +
   interned relation keys)` checks; interner growth is linear in stored tuples
   (× schema-bounded fan-out), never universe-bounded.

2. **X3 adjudication: fixable, not representational.** The missing piece was
   only the id: `ttu_expand` already emitted the from-chain userset when its id
   existed (`singleton_entity(fid)`). The same write-time pass interns the
   from-chain userset key `(subject_type, subject_name, target_rel)` for every
   stored tupleset tuple with a bare concrete subject (star parents stay
   symbolic via `stars`; userset-shaped parents are D3-rejected), so
   `expand`/`lookup_reverse` now carry it in `pos`. No read-time interning, ids
   stay recycled-int32, the `(type, name, predicate)` key remains the
   surrogate.

   Population note: pre-interned keys join `ids_of_shape[(T, rel)]`, so a
   `[T:*#rel]` star's extensional population can now include from-chain-only
   usersets — strictly more faithful (their exclusions become representable in
   `neg`); no fixture stars a shape that pre-interning feeds.

---

## 2026-07-13 — graph derived-TTU userset subjects (X4 + X2 fixed)

Both graph entries from the 2026-07-12 gate are fixed and their strict xfails
flipped to plain regression pins (`tests/test_lookup_oracle.py`); the walks no
longer skip any (subject, object) pair (`_make_derived_ttu_userset_gap`
removed) and derived `'*'`-object reverse lookups are asserted like every
other object. The repo-wide "identical semantics" claim no longer carries the
X4 exception.

1. **X4 root cause (both shapes).** The boolean spec is **silent** on
   userset-shaped subjects flowing through a derived TTU's stored parents —
   §5.3/§6 define residues over closure-leaf state and same-object usersets
   only; the oracle (`ttu_leaf`) is the pin. (a) *From-chain*: the plan
   evaluator's `ttu_check`/`tupleset_ttu_check` never implemented the
   from-chain identity rule (a stored tupleset parent `p` makes `p#target_rel`
   itself a member — exactly what the untainted path materializes as the
   rewrite edge), and no reconcile step enumerated the from-chain keys.
   (b) *Cross-object lift*: userset memberships of a tainted TTU target are
   edge-free (`upos`, P4), so the dependent's audit set — built from closure
   reverse lookups on the parents' public nodes — could never see them.
   **Fix (processor only)**: `ttu_check`/`tupleset_ttu_check` gain the
   identity rule; `reconcile` gains a from-chain pass (step 2a: keys per
   stored parent, both polarities, interning a subject node ONLY when the
   outcome must be recorded — upos: true∧uncovered, neg: false∧covered; the
   other two outcomes are already exact via stars) and `_leaf_concretes`
   lifts the tainted targets' residue `upos` members into the audit.
   Cross-object recordings are not edge-justified on the recording object, so
   two lifecycle pieces close the id-liveness loop: `_gc_public_node` keeps a
   node that another residue's `neg`/`upos` still references (and the new
   `_gc_subject_node` collects dropped anchor nodes symmetrically, keeping
   add-then-remove a row-multiset round trip), and `_map_deltas_to_keys`
   full-reconciles every residue referencing a subject node GC'd in the
   transaction. Read paths unchanged — `check`/`lookup`/`lookup_reverse`
   answer userset subjects from the (now complete) residue exactly as before.
   Formal scope: derived-TTU shapes are outside `W4Fragment` (`computedOnly`),
   and every new processor path is gated on `derived-ttu`/`derived-tupleset-ttu`
   leaf kinds or on states (cross-residue references of dead/ref-0 nodes) that
   in-fragment runs never reach; the state-level conformance gate (exact
   edge+residue equality vs Lean) stayed green unchanged.

   Residual THEORETICAL note (recorded, not observed): if a from-chain TARGET
   were an untainted subject-wildcard-bridged shape with grants already sitting
   in its `w_any`, interning a from-chain subject node mid-cascade could create
   new bridge-fed truth and so require extra cascade rounds. No
   currently-compilable schema class reaches this shape, and if one ever did it
   fails LOUD — the cascade-quiescence check raises `InvariantViolation` —
   never silently wrong.

2. **X2**: `lookup_reverse` on a derived relation with `o_name='*'` now
   short-circuits to the empty result before node resolution (decision 15: no
   object-star state can exist), matching `check`'s False (P7 #3) and the set
   engine's empty result instead of raising through the reserved-name guard.

Grid widening (regression cover beyond the lookup gate): `_boolean_grid` adds
the `doc#viewer` from-chain subjects, and the De Morgan grid derives every TTU
from-chain userset shape from the AST (`_from_chain_userset_subjects`), so the
matrix now queries userset subjects on derived-TTU families after every op.

---

## 2026-07-13 — FIXED: self-referential TTU-parent add/remove state non-restoration (answer-benign)

**Status: FIXED 2026-07-13** (`index_v4/processor.py` reconcile step 2a; regression
`tests/test_self_referential_tuples.py`). Found by the hypothesis campaign
(`tests/test_hypothesis.py::test_add_then_remove_restores_row_multiset`); a
falsifying example was discovered and persisted to the (gitignored) `.hypothesis/`
DB. Pre-existing — reproduced on a clean tree; not introduced by the surrounding
session's work.

**Self-referential tuples ARE supported** (OpenFGA `IsSelfDefining`; the
self-defining / attribute-marker idiom — `document:1#viewer@document:1#viewer`, or
a `resource:r1 activated resource:r1` flag). The bug was a canonicalization drift,
not an evaluation error, so the fix keeps accepting them (does NOT reject).

**Shape.** A self-referential tupleset tuple `doc:d1 parent doc:d1` (d1 is its own
`parent`) present in the store, a derived intersection `r0: [user] and [user]`, and
a TTU that reads it back on the same object `r4: r0 from parent or [user, user:*]`.
Adding then removing `u1 r0 d1` does **not** restore the materialized state.

**Symptom (answer-benign).** After the add/remove: `check` is CORRECT on every
query (`check(u1,r0,d1)` and `check(u1,r4,d1)` both False, matching the oracle),
and `DeltaProcessor.audit_fixpoint()` PASSES — the ending state is a valid
fixpoint. What drifts is a single NODE row (`snapshot_rows`): the node
`(r0, doc, d1)` ends with `implicit=False` where the before-state and a fresh
add-only build have `implicit=True`, both at `reference_count=0`. So it is a
refcount-0 node left un-GC'd with a stale `implicit` flag on the remove path — the
"node GC" representation class the formal state gate deliberately projects out
(`extractor.py` P5). It violates the repo's canonical-representation *uniqueness*
guarantee (add/remove exact-state restoration), which `test_add_then_remove_...`
pins, but does NOT affect answers, the fixpoint, or any check-level parity.

**Root cause.** By node keying `(predicate, type, name)`, the object's own derived
node `(r0, doc, d1)` is the SAME node as the from-chain userset subject `doc:d1#r0`
that the self-referential TTU records in `r4@d1`'s residue `upos` (X4a from-chain
rule). That node therefore plays two roles: a derived-public node (pinned
`implicit=False` while it holds an edge) AND a recorded from-chain subject (kept
alive by the `upos` reference). Reconcile step 2a interned the from-chain subject
node with the DEFAULT `implicit=True`, so a fresh build created it implicit; but on
the add path it had first held r0's derived edge, which promoted it to explicit
(`implicit=False`, and "explicit is sticky", `core.py:284-287`). Add-then-remove
thus ended explicit where a fresh build was implicit — a one-node canonical-form
divergence. Answers were never affected (the read path resolves the from-chain
identity directly; `audit_fixpoint` passed). Note the graph's closure-cycle
rejection (`core.py:319-342`, T4 acyclicity) does not catch this: `parent` tuples
are tupleset/entity edges consumed by the TTU rule, not closure self-loops.

**Fix (allow, don't reject).** From-chain subject nodes are now interned
**NON-implicit** in reconcile step 2a (`processor.py`): a recorded subject must
survive on its `upos`/`neg` reference alone and be collected only by
`_gc_subject_node` (step 5) — an implicit one would be premature-GC'd and dangle
the reference. Both the incremental and fresh-build paths now intern it explicit,
so add/remove is again an exact row-multiset round trip. Rejecting self-referential
tuples was NOT chosen: OpenFGA supports them and they have real use (the flag
pattern above).

**Formal scope:** unaffected. Derived-TTU shapes are outside `W4Fragment`; the
Lean chain is add-only (no remove legs); and the state-level conformance gate
projects the node-GC class out (P5). No theorem, gate, or bound is touched.

---

## 2026-07-15 — set-engine lookup completeness ×2 + accept/reject parity (star tuplesets)

Three pre-existing set-engine divergences, all on states combining star tupleset
parents (`[T, T:*]`) with TTU chains — a constellation NO prior corpus built. The
first was found by the N17 design review (a `check`-recursion vs walk-hop audit),
the other two by N17's new fuzz artifacts on their first runs. All fixed
2026-07-15 (`setengine/engine.py`), landed with N17; the graph index and oracle
were never wrong — these are set-engine-only surface/admission bugs.

1. **Walk drops downstream objects behind a STAR bare parent (H3 gap).** A stored
   star parent tuple `Q:q ts T:*` makes every tuple-mentioned instance of `T` a
   parent of `Q:q` (`ttu_leaf`'s ∀⇒∃ star branch), but `_reverse_neighbors`' H3
   hop folded only the CONCRETE bare sibling — so a subject confirmed on
   `(T, X, rel)` never hopped to `(Q, q, R)`. `check` said True (engine AND
   oracle), `lookup` dropped the object, no marker covered it — an S4 violation
   live on any walked schema with a star-able tupleset. **Fix:** H3 also folds the
   star bare sibling `(t, '*', '...')` through the same `member_of × _ttu_map`
   cross. Pinned: `test_reg1_star_bare_parent_from_chain` + the `owc_star_ttu`
   corpus gates.

2. **Walk seed empty for uninterned from-chain star-identity subjects.** A userset
   subject `T:X#r` (ghost, or the `*` shape itself) is a member of every object
   with a stored `T`/`T:*` tupleset parent whose TTU targets `r` (`ttu_leaf`'s
   identity branches) — with NO stored tuple at the subject key, so the old
   interned-id seed (and its star-sentinel fallback) produced nothing. Found by
   the walk≡sweep differential on its first run, oracle-confirmed. **Fix:** the
   seed is addressed by SHAPE (`_reverse_neighbors_key`); H2/H3 need only the
   bare siblings interned, not the subject node.

3. **Accept/reject divergence: routed same-shape wildcard self-reference.** A
   same-type star parent `folder:* parent folder:f2` routes (TTU-rewrite
   through-shape) to `folder:*#viewer viewer folder:f2`, which the graph rejects
   by construction (bridge-before-grant: the object's in-bridge to the star
   userset node + the grant edge = two-cycle; `index_v4/wildcard.py`'s reworded
   cycle error). The set engine's §1.5 same-shape check only saw the RAW tuple
   (bare subject) and its flow graph carries only RuleSet-derived edges, never
   the materialized bridges — so it ACCEPTED. Found by the seed-7 hypothesis
   sweep over the new corpus (`_Gate` unanimity assert). **Fix:** the same-shape
   wildcard self-reference test now also runs over every DERIVED pair
   (`_would_cycle`), guarded by the through-shape's presence in
   `subject_wildcard_shapes` (always true for routed stars — the D3 derivation —
   so it never blocks a pair the graph accepts). Pinned:
   `test_reg9_same_type_star_parent_accept_reject_parity` (both backends reject
   same-type, both accept cross-type).

   **Known residual — NOW FIXED (2026-07-16, see the dated entry at the end of this
   file).** The multi-hop version turned out to be *constructible* after all (the
   "no current corpus" claim was true only of the existing fuzz pool, not of
   reachability): a 3-relation schema + 2 writes builds it. The flow graph is now
   bridge-aware and rejects it, restoring accept/reject parity.

**Formal scope:** unaffected. Forward `lookup` is unmodeled (CORRESPONDENCE §8.1
N17 entry); set-engine write admission is unmodeled (`GraphAdmission` mirrors the
GRAPH's admission, unchanged); conformance corpora contain no star tupleset
parents, and all three verify.sh phases re-ran green.

---

## 2026-07-16 — bridge-aware set-engine admission (the "Known residual" §3 above, FIXED)

**What.** The multi-hop star-bridge accept/reject divergence documented as the
"Known residual" in §3 (set engine accepts a bridge-mediated cycle the graph
rejects) was believed unbuildable ("no current corpus/pool can build it"). It is
**buildable** — a minimal red repro (pinned as
`tests/test_lookup_oracle.py::test_reg10_multihop_star_bridge_cycle_accept_reject_parity`):

```
type folder
  relations
    define parent: [folder, folder:*]
    define admin:  [user, folder:*#admin, folder#viewer]
    define viewer: [user] or admin from parent
```
writes `folder:* parent folder:c` then `folder:c#viewer admin folder:y`. The graph
rejects the 2nd (cycle `(folder,c,viewer) → (folder,y,admin) →[in-bridge] w_any(folder,admin)
→[rule] (folder,c,viewer)`); the set engine's flow graph carried the two rule edges
but not the materialized in-bridge, so it accepted. `ParityEngine` fires.

**Fix (set engine only — `setengine/engine.py`).** The write-time cycle check
(`_flow_reaches` / `_would_cycle`) is now **bridge-aware**, mirroring
`index_v4/wildcard.py` `_ensure_bridges`: concrete `(T,x,p)` → `w_any(T,p)` for
`bridged_in_shapes`, and `w_all(T,p)` → concrete for `bridged_out_shapes`, with
`w_any`/`w_all` kept **distinct** (flow-graph star nodes are position-tagged 4-tuples
`(T,'*',p,'any'|'all')`) so an in-bridge and an out-bridge on the same shape can't fuse
into a spurious path. Bridges are computed virtually during traversal (no new state, no
DB reads); an OUT-bridge shape→concrete index is maintained only when the schema
declares object wildcards. Both `SetOps` now reject the repro, matching the graph.

**Fix direction rationale.** The graph's exact path-counting closure fundamentally
requires an acyclic routed graph; its admission is the authoritative acyclicity gate,
and Lean's `GraphAdmission` models *it*. The set engine must mirror that gate (reject),
not the other way round — so **no Lean change** (set-engine write admission is unmodeled;
the graph/Lean side already rejected). Verified: full `pytest tests/` (544+24), all three
`verify.sh` phases (lean + conf 68+195), and a 6-seed hypothesis fuzz sweep — all green.

**Residual (hardening follow-up, not a divergence).** The fuzzer's schema generator
still can't *build* this shape class (that's why the bug hid); `test_reg10` pins the
instance. Teaching the generator to emit star-tupleset-parent + self-referential-userset
shapes would fuzz the class — filed in `HANDOFF.md` backlog.

*(subsequent phases append below)*

## 2026-07-16 — star-bridge fuzzer generator + out-bridge regression (reg11); two new latent OWC divergences filed

**What (hardening, the follow-up above, DONE).** Closed the fuzzer blind spot that let the
reg10 bug hide. Two additions:
- `tests/test_lookup_oracle.py::test_reg11_out_bridge_object_wildcard_self_cycle_accept_reject_parity`
  — the **object-wildcard / OUT-bridge analog of reg10**. Where reg10 closes a cycle through
  a subject-wildcard IN-bridge (concrete→`w_any`), reg11 closes one through an object-wildcard
  OUT-bridge (`w_all`→concrete): `folder:a parent folder:*` (with `(folder,parent)` and
  `(folder,viewer)` object-wildcard shapes) routes via the `viewer from parent` TTU to
  `folder:a#viewer → folder:*#viewer`, and the `w_all(folder,viewer) → folder:a#viewer`
  out-bridge closes the two-cycle. Both backends reject; blinding `bridged_out_shapes` to
  empty flips the set engine to *accept* (the pre-fix divergence), so reg11 gives real
  coverage to the OUT-bridge branch of the fix (reg10 exercises only the IN-bridge branch).
  **Only this single-hop out-bridge self-cycle is realizable**: any derived edge into
  `w_all(T,p)` is minted by a `T:x <tupleset> T:*` write whose own subject is a same-shape
  concrete `T:x#p`, which the out-bridge immediately reaches back — so such a write always
  self-cycles at admission and can never persist for a later write to build a longer loop on.
  The multi-hop generalization of reg10 is therefore **unreachable** in the out-bridge
  direction (verified: `folder:b parent folder:a` then `folder:a parent folder:*` is still
  rejected on the second write, both backends).
- `tests/test_hypothesis.py` — a dedicated **star-bridge schema generator** (`star_bridge_configs`
  + `_star_bridge_pool`) emitting the `parent:[T,T:*]` / `A:[user,T:*#A,T#B]` /
  `B:[user] or A from parent` class the stock `schema_asts` cannot build, plus a deterministic
  pin and a `StarBridgeParityMachine` (order-dependent admission fuzzing through a 4-way
  ParityEngine). Authoring check: blinding the set engine's bridge awareness makes both fire
  the reg10 accept/reject disagreement, confirming the class is now actually fuzzed.

**Two NEW latent divergences surfaced by the generator (NOT chased — out of scope; filed).**
Both require an **object wildcard on the relation that also carries the `T:*#A`
wildcard-userset restriction** (i.e. `(T, A) ∈ object_wildcard_shapes`) — a pathological
config where the `T:*` star node plays both the object-wildcard and the subject-userset role.
This is an orthogonal axis to the star-bridge *cycle* class, so the generator draws OWC only
over `{(T,'parent'), (T, B)}` and these stay unexercised by the committed fuzzer. Minimal repros:
- **F1 (graph incomplete — check divergence).** Schema `viewer:[user,folder:*#viewer,folder#admin]`,
  `admin:[user] or viewer from parent`; OWC `{(folder,parent),(folder,viewer)}`; writes
  `folder:* parent folder:*` then `folder:x#admin viewer folder:*`. Then
  `check(folder:x#admin, admin, folder:x)` = **graph `False`, set + oracle `True`** — the graph
  misses a membership routed through the double-wildcard (`folder:* parent folder:*`) parent.
- **F2 (graph over-permissive — accept/reject divergence).** Schema
  `admin:[user,folder:*#admin,folder#viewer]`; OWC `{(folder,admin)}`; write
  `folder:*#admin admin folder:*` = **graph accepts, set rejects** (the reg9 same-shape
  wildcard self-reference, but with the wildcard *object* — the graph's cycle check doesn't
  catch it when the object is itself `T:*`). Set (rejecting) matches the reg9 semantics.

These are genuinely exotic OWC-on-self-referential-userset-relation corners (OpenFGA does not
support wildcard usersets at all), consistent with the "latent/theoretical, no corpus forces
it" class — **do not chase speculatively**; filed in the HANDOFF backlog for triage. F1 is a
graph *completeness* gap (graph vs oracle), so if either is ever prioritized, F1 first.
