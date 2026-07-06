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

*(subsequent phases append below)*
