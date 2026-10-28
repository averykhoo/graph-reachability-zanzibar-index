# TK169 public-docstring census (2026-10-28)

> **FROZEN 2026-10-28 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

## Scope and method

What a user sees through `help()`: every name in the `__all__` of `zanzibar`,
`zanzibar.graphindex`, `zanzibar.setengine`, `zanzibar.schema` and `zanzibar.store`
(87 names in all, 2026-10-28), their classes' public methods and properties, the module
docstrings of public modules, and the message text at every `raise` site in `src/zanzibar`.
Comments are out of scope. Private names (`_x`) are out of scope: `pydoc` hides them.

Instruments (gitignored, so they are recorded here by what they did):

1. **Runtime dump** (first-hand READ): imported each package, walked `__all__`, and wrote
   every class, function, public method and property docstring with `inspect` (144
   docstrings, about 100 KB). The whole dump was read by hand. That reading found most of
   the rows below.
2. **AST leak scan** (first-hand READ): a regex over every docstring in `src/zanzibar`
   for `TK\d+`, `ZT-*`, `R6-*`, `P\d+`, `ASK-*`, repo paths, `spec §`, dates and Lean
   names. It found 131 hits, and all but about 12 are on private symbols, which are out of
   scope. The public hits are in the tables.
3. **Message scan** (first-hand READ): the same regex over every non-docstring string
   constant in `src/zanzibar`, which covers raise messages. It found **0 hits**, so
   messages carry no task ids, paths or dates. A second scan listed the 33 raise messages
   that tell the caller to pass, call or use something. Each was read for reachability.
4. **MISSING**: a public class or method whose `__doc__` is `None`, or the auto-generated
   dataclass signature.

Every STALE or UNREACHABLE row was checked against the code, and the cell says how.
Provenance labels: **READ** means first-hand from the source; **REASONED** means
inferred and not executed.

Severity: a **leak** of a task id, private path or test harness name counts higher than a
private `_name` reference. A private name in a public docstring still points the reader at
something `help()` will not show.

Coordination: `Store.__init__`'s "Fail-closed" paragraph describes the TK163 path.
Whoever fixes TK163 rewrites that paragraph. Group 5 should take it with TK163 or leave it
alone.

---

## Group 1: `src/zanzibar/schema/errors.py` (exception docstrings)

| file::symbol | class | offending text | proposed replacement |
|---|---|---|---|
| `schema/errors.py::ShapeNoLongerAccepted` (L347, 2026-10-28) | LEAK | "Raised by `parser.py::_validate_header_line`, `parser.py::_reject_unparenthesised_but_not` and `parser.py::_validate_restriction_types_declared` ... by `compiler.py::_validate_object_wildcard_shapes`"; "(S7)", "(S8)" | "Raised by the parser (`parse_schema_ast`, `parse_openfga_schema`, `Store(schema=...)`) and, for an `object_wildcard_shapes` entry, by `compile_ruleset`." Drop S7/S8. |
| `schema/errors.py::AdmissionRejected` (L61) | LEAK | "every existing caller and test catches ValueError ... (`zanzibar.store._store._write`'s narrow rejection path, the test harnesses' backends, `zanzibar.graphindex.processor`'s cycle guard, `zanzibar.store.apply._apply_row`'s ...)" and the "NOTE the caller-relativity" paragraph naming `_apply_row` | "It subclasses `ValueError`, so code that catches `ValueError` around a write keeps working; catch `AdmissionRejected` to tell a correct refusal from a bug." Cut the internal call-site list and the `_apply_row` paragraph. |
| `schema/errors.py::AdmissionRejected` | STALE | "The exact mirror of `zanzibar.graphindex.invariants.InvariantViolation`"; "`zanzibar.graphindex.core` re-exports it for convenience" (READ: since TK164 the only public home of exceptions is the top level, `src/zanzibar/graphindex/__init__.py` comment) | `zanzibar.InvariantViolation`; drop the re-export sentence. |
| `schema/errors.py::IndexResourceLimit` (L114) | LEAK | "The common base of the refusals `zanzibar.store.apply._apply_row` must NOT promote ... `_apply_row` catches THIS class" | "The base of the index-side resource limits. A store replaying its log treats these as limits, never as corruption. Members: `ClosureFanoutExceeded`, `PathCountExceeded`." |
| `schema/errors.py::ClosureFanoutExceeded` (L145) | UNREACHABLE | "or `ReachabilityIndex(max_closure_fanout=...)`" (READ: `Store.__init__` (L376) takes no `max_closure_fanout` and builds its own index, so a `Store` user can only set the env var) | "It is set by the `ZANZIBAR_MAX_CLOSURE_FANOUT` environment variable (default 100,000; `0` disables it); a `ReachabilityIndex` built directly also takes `max_closure_fanout=`." |
| `schema/errors.py::ClosureFanoutExceeded` | LEAK | "which `zanzibar.store.apply._apply_row` does not promote to `InvariantViolation`" | "so a replayed over-cap row is never reported as corruption." |
| `schema/errors.py::PathCountExceeded` (L129) | LEAK | "`MAX_PATH_COUNT`" (not exported); "which `Store._write` treated as an unknown bug"; "Before this refusal the write failed at FLUSH with a raw DataError ... Saturating the count instead was rejected" (history) | "A write would push a closure row's path count past 2**31-1 (the int4 limit, applied on both SQLite and PostgreSQL)." Keep the diamond-chain explanation. Drop the history and the private names. |
| `schema/errors.py::DoublyBridgedShapeError` (L303) | LEAK | "the 'doubly-bridged' precondition of the F1/F2 divergences"; "degrade to a ruleset-less/oracle-only mode" (the oracle is test-only) | "...precondition of a latent cycle". For the set engine: "the set engine still evaluates the other scope rejections; it refuses this one too, so the shape is refused on both backends." (REASONED: `setengine/engine.py` L667 catches `UnsupportedByGraphIndex`/`CyclicDerivedDependency` at compile.) |
| `schema/errors.py::CyclicDerivedDependency` (L324) | LEAK | "graph-optional consumers (ParityEngine, the set engine's cycle-parity compile)" (ParityEngine is `tests/parity.py`) | "...its own type, so a caller can handle exactly this refusal without catching every `ValueError`." |
| `schema/errors.py::ZanzibarError` (L34) | STALE | "`zanzibar.graphindex.InvariantViolation`" (READ: not in `zanzibar.graphindex.__all__` since TK164) | `zanzibar.InvariantViolation` |
| `schema/errors.py::is_valid_identifier` | UNREACHABLE | "through `_require`'s `allow_star`/`allow_ellipsis` flags ... should go through `validate_write_identifiers`" (READ: `validate_write_identifiers` (L233) is not in `zanzibar.schema.__all__`; `_require` is private) | "`'*'` and `'...'` are reserved by position: `*` is accepted only as a name and `...` only as a subject predicate. Writes through `Store` validate both." |

## Group 2: the rest of `src/zanzibar/schema/` (parser, unparse, compiler, rules, syntax, reports, boolean)

| file::symbol | class | offending text | proposed replacement |
|---|---|---|---|
| `schema/parser.py::parse_schema_ast` (L305) | LEAK | "(`_validate_restriction_types_declared`)", "(`_validate_ast_consistency`)" | Drop both parentheticals. Say instead "every restriction type must be declared" and "no dangling or cyclic relation references". |
| `schema/unparse.py::unparse_schema_ast` (L12) | LEAK | "is refused now (S7)", "is refused now (S8)" | Drop "(S7)" and "(S8)". Say "refused since 0.0.5". |
| `schema/compiler.py::compile_ruleset` (L367) | LEAK (mild) | "untainted relations byte-identically to the pure-union path, tainted ones into leaf routing + executable plans" | "Relations without `and` / `but not` compile exactly as before; boolean relations compile into derived predicates on `RuleSet.compiled`." |
| `schema/rules.py::RuleSet` (L287) | MISSING | `help()` shows only the dataclass signature `RuleSet(rules_and_filters: list[...], ...)` | Add a docstring: "The compiled form of a schema for the graph index. Build one with `parse_openfga_schema` / `compile_ruleset`, never by hand. `schema_info` is a `SchemaInfo`, `compiled` is a `CompiledBooleans` (None without boolean relations), and `apply` routes one `RelationalTriple`." |
| `schema/rules.py::RuleSet.apply` (L340) | MISSING | no docstring (and `SchemaInfo`/`RelationalTriple` docstrings cite `RuleSet.apply` as the way in) | Say what it takes and returns. READ the body first: it returns the routed triples. |
| `schema/rules.py::SchemaInfo.crossable_shapes` (L263) | LEAK | "(the reference oracle witnesses it ...)", "(`WildcardIndex._ensure_entity_middles`)" | "...the graph index creates `(T, x, p)`, with both bridges, for every live entity `x` of type `T`." Drop the oracle and the private name. |
| `schema/syntax.py::Union` / `Intersection` / `Exclusion` (L46/51/56) | MISSING | auto-generated `Union(children: tuple['Expr', ...])` | One line each, in the style of `Computed`/`TTU`: "`a or b` -> `Union((a, b))`", "`a and b`", "`base but not subtract`". |
| `schema/reports.py` module docstring | LEAK | "`w4_fragment_report` (mirror of the Lean decider)" (module `zanzibar.schema.reports` is listed in `zanzibar.schema`'s module docstring) | "`w4_fragment_report` reports whether a schema is inside the fragment the formal proofs cover." Do the same for `W4FragmentReport` and `w4_fragment_report` (Lean / `W4Fragment` names; READ by AST scan; not in `__all__`, so low priority). |
| `schema/boolean.py` raise in `_assert_ttu_parent_types_cover_admission` (L74 message) | LEAK (low) | "This is the RC1 class -- suspect _member_types, not this check." | An internal-contract assertion: a user sees it only on a library bug. Replace with "This is a library bug; please report it with the schema." |

## Group 3: `src/zanzibar/graphindex/` core, invariants, outbox, cascade_mark

| file::symbol | class | offending text | proposed replacement |
|---|---|---|---|
| `graphindex/invariants.py` module docstring | STALE | "Default ON while prerelease; pass `paranoia=False` at the wiring site for benchmarks." (READ: `Store.DEFAULT_PARANOIA = PARANOIA_OFF`, `store/_store.py` L372; the default of `resolve_paranoia_level` is `PARANOIA_OFF`. Only a direct `install_paranoia` call defaults to `'full'`.) | "`Store` defaults to `'off'`. `install_paranoia` called directly defaults to `'full'`." The tail of the same docstring already says this; make the head agree. |
| `graphindex/invariants.py` module docstring | STALE | "(I4-I10 arrive with the derived-predicate state in later phases.)" (READ: `_check_derived_invariants` exists in the same module, AST scan L517) | Delete the sentence, or list I4-I10. |
| `graphindex/invariants.py` module docstring | LEAK | "the ParityEngine does the comparison"; "a regression of the 2026-08-09 middle fix"; "(2026-08-09)"; "(`DeltaProcessor._check_cascade_fixpoint`)"; "the historical production behaviour"; "measured 4.8x-10x" | Drop the ParityEngine clause, the dates and the private method name. Keep the tier table. Keep at most one cost figure per tier. |
| `graphindex/core.py::ReachabilityIndex` (L292) | LEAK (private) | "every write funnels through `_lock_store` ... See `_lock_store` for why" | "every write takes a per-store row lock (`SELECT ... FOR UPDATE` on PostgreSQL) ..." Drop "See `_lock_store`". |
| `graphindex/core.py::ReachabilityIndex.resolve_node_ids` (L1175) | LEAK | "each was its own `_db_node` point SELECT ... `WildcardIndex._check_internal` ... measured at **4.00 `node` statements per `check`** ... (`models.py::Node.__table_args__`) ... `_EvalContext.leaf_check`" | Keep the first paragraph and the read-only contract. Drop the measurements, private names and the repo path. |
| `graphindex/core.py::ReachabilityIndex.cached_concrete_node` (L1154) | LEAK | "byte-identical to the former `DeltaProcessor._node`, whose sole implementation this is" | Drop the sentence. |
| `graphindex/core.py::ReachabilityIndex.node`, `add_edge`, `remove_edge`, `remove_node`, `check_reachable`, `lookup_reachable`, `lookup_reverse` (L1075-1421) | MISSING | no docstring | One line each. The `*_by_id` twins already have one to copy from. |
| `graphindex/core.py::take_row_write_lock` (L186; public module, not exported) | LEAK (low) | "first exercised for real on 2026-07-27"; "Unchanged from before this fix" | Drop the date and the "before this fix" narrative. |
| `graphindex/outbox.py::prune_outbox` (L36) | STALE | "`delta_outbox` had no `DELETE` anywhere" (READ: the table is `zanzibar_delta_outbox`, `graphindex/models.py` L206) | Drop the history sentence. If the table must be named, write `zanzibar_delta_outbox`. |
| `graphindex/outbox.py::prune_outbox` | LEAK | "`DeltaProcessor._run_cascade` starts from ..., `ParanoiaGuard` from ..."; "its only in-tree consumer"; "the one dialect CI runs" | "The cascade reads from the watermark taken before the write, and the paranoia checker reads from the last commit." Replace "the one dialect CI runs" with "on SQLite". |
| `graphindex/cascade_mark.py::note_write`, `clear` (public module, not exported) | LEAK (low) | "(fix-stage hole 2, 2026-10-22)", "(fix-stage hole 1, 2026-10-22)", "`WildcardIndex._derived_write_ctx`", "`_after_soft_rollback`" | Drop the parentheticals. Low priority: not in `__all__`. |

## Group 4: `src/zanzibar/graphindex/` wildcard and processor

| file::symbol | class | offending text | proposed replacement |
|---|---|---|---|
| `graphindex/wildcard.py::WildcardIndex.check` (L847) | LEAK | "the BL-2 leaf-name fence"; "(`<rel>.<idx>`, spec deviations 2026-08-21b)"; "(BL-2)"; "the set engine and the oracle"; "`_EvalContext.leaf_check` / `leaf_stars` ... `_check_internal`" | "Is the subject related to the object? A compiled leaf name (`<relation>.<n>`) is internal and always reads False, the same as any undeclared name." |
| `graphindex/wildcard.py::WildcardIndex.processor_writes` (L166) | LEAK (private) | "Read by `_assert_derived_exclusivity` ... and `_derived_write_ctx`" | "Is the calling thread inside the delta processor's write window? Writes to a derived relation outside it are refused." |
| `graphindex/wildcard.py::WildcardIndex.add_tuple` (L629) | LEAK | "(store.TupleSource / the harness adapters)" | "(`zanzibar.store.TupleSource` / `Store`)" |
| `graphindex/wildcard.py::WildcardIndex.remove_tuple` (L706) | MISSING | no docstring | Mirror `add_tuple`, multigraph warning included. |
| `graphindex/processor.py::DeltaProcessor.derived_check` (L331) | LEAK (private) | "Delegates to the facade's `_check_derived` ... (see `_EvalContext`)" | "...shares one implementation with the read path. `reflexive` applies OpenFGA's implicit userset self-relation." |
| `graphindex/processor.py::DeltaProcessor.tupleset_parents` (L503) | LEAK | "the pinned TTU semantics (oracle ttu_leaf)"; "(RC2)"; "`_from_chain_keys`, `_leaf_concretes`, `_derived_leaf_neg_ids`"; "`_EvalContext` TTU methods" | "Only stored tupleset tuples count, never computed members. A stored `T:*` parent is expanded into every instance of `T`; `tupleset_star_types` carries the shape part." |
| `graphindex/processor.py::DeltaProcessor.stored_userset_subjects` (L404) | LEAK (private) | "inside an open `_stored_cache_scope` -- see that method's docstring" | Drop the sentence, or "memoized for the duration of a cascade". |
| `graphindex/processor.py::DeltaProcessor.run_cascade` (L1440) | LEAK | "(test-matrix GraphBackend)"; "`ReachabilityIndex._node_cache_scope`"; "`_stored_cache_scope`'s own docstring"; "`_run_cascade`'s normal exits"; "an earlier staleness measurement ... (its instrument wrapped this public method)" | First paragraph, plus: "Call it in the same transaction as the graph writes, with the `outbox_watermark` read before the first write, before committing (else `CascadeNotRun`)." Move the three-cache rationale to a comment. |
| `graphindex/processor.py::DeltaProcessor.audit_fixpoint` (L1717) | LEAK | "`_bumped` is cleared only on the clean path"; "(`_check_cascade_fixpoint`)"; "Production callers: none -- it is reached from the test suite" | Keep the contract bullets (diagnose in a rolled-back txn; repair with `backfill()`). Drop the private names and the test-suite line. `Store.proc` is real (READ: `store/_store.py` L504), so keep it. |
| `graphindex/processor.py::DeltaProcessor.residue_stars`, `member_stars`, `reconcile_subject`, `reconcile` (L328/358/757/859) | MISSING | no docstring | One line each, or rename to `_x` if not meant to be API. That is the fixer's call; record it on the row. |

## Group 5: `src/zanzibar/store/` (_store, source, build)

| file::symbol | class | offending text | proposed replacement |
|---|---|---|---|
| `store/_store.py::IndexStalled` (L139) | UNREACHABLE | "Remove the tuple at the source, then `store.rebuild_index`." (READ: `Store` has no `rebuild_index` method; it is the function `zanzibar.store.rebuild_index(session, source_store_id)`, `store/build.py` L188) | "...then call `zanzibar.store.rebuild_index(session, store_id)`." |
| `store/_store.py` IndexStalled raise message (L939 message) | UNREACHABLE | "...remove the tuple at the source and then rebuild_index()) and retry." (sits beside the methods `catch_up()` / `check()`, so it reads as a method) | "...then `zanzibar.store.rebuild_index(session, <store_id>)`" |
| `store/_store.py::LookupNotFresh` (L105) | LEAK | "Unifying that contract is a real, breaking API change with its own oracle-gate arc. Until it lands, ..." (internal roadmap) | "The two backends do not return the same id domain, so under an explicit freshness demand the lookup refuses rather than serve a stale enumeration." |
| `store/_store.py::Store.__init__` (L376) | LEAK | "Before this parameter existed the layer had two callers, both tests, so every runtime corruption detector was dark in production." | Delete. |
| `store/_store.py::Store.__init__` | LEAK (private) + TK163 | "a violation raises `InvariantViolation` inside `before_commit`, so the write's commit never happens and `_write`'s handler rolls back both halves and rebuilds the evaluator" | Rewrite with the TK163 fix to describe the fixed behaviour. No private names. |
| `store/_store.py::Store.refresh` | STALE (term) | "(fresh transaction + rebuilt evaluator; ...)" (TK169's first slice renamed "evaluator" to "set engine" in messages) | "rebuilt set engine" |
| `store/source.py::TupleSource.refresh_evaluator` (L822) | LEAK | "The watermark/rebuild pair goes through `_consistent_rebuild` (2026-07-27). It used to be a bare read-then-rebuild ... this method sits on `Store._write`'s error path" | Keep the first paragraph only. |
| `store/source.py::TupleSource.catch_up_evaluator` (L750) | LEAK (private) | "relies on the writer lock discipline (`_lock_source`)"; "exactly the pre-existing contract" | "...relies on the per-store writer lock: log ids commit in id order per store." |
| `store/source.py::TupleSource.undo_last_admission` (L796) | LEAK (private) | "one `_apply_add` / `_apply_remove` of one tuple ... under `_lock_source`" | "...one tuple since a watermark reached under the store's writer lock" |
| `store/source.py::TupleSource.pop_pending_rows` (L708) | LEAK (internal API) | "The sync write path drains this ... to hand `advance_index` the exact rows" (`advance_index` is not in `__all__`) | It is plumbing for `Store`: rename to `_pop_pending_rows` or say "Internal: used by `Store`'s sync write path." |
| `store/source.py::TupleSource.watermark` (L837) | MISSING | no docstring | "The newest log id the set engine reflects (its freshness watermark)." |
| `store/source.py::TupleSource` (all methods) | STALE (term, low) | "the online evaluator" / "evaluator watermark" throughout `engine`, `check`, `catch_up_evaluator`, `evaluator_lag` | "the set engine", where the method names allow it. The method names are API and stay. |
| `store/build.py::BuildReport` (L66) | LEAK | "WHY THIS FIELD EXISTS ... downgrade every 'bulk' test in the repo ... Measured 2026-09-20: forcing `if bulk:` to `if False:` left the bulk-build conformance test green ... an assurance step that fails by PASSING" | Keep the first two paragraphs. Replace the rest with "`constructor` lets a caller confirm which path ran; the two produce identical state." Move the rest to a comment. |
| `store/build.py::build_index` (L118) | LEAK | "it is byte-identical in effect and is the identity gate's reference side" | "it produces the same state, more slowly" |
| `store/build.py::rebuild_index` (L188) | STALE (low) | "Stop the store's async worker first" (READ: `Store` docstring says "no worker ships") | "Stop every writer and any `catch_up` loop first" |

## Group 6: `src/zanzibar/setengine/`

| file::symbol | class | offending text | proposed replacement |
|---|---|---|---|
| `setengine/__init__.py` module docstring | LEAK | "(spec: set-engine)" | Delete. |
| `setengine/engine.py::UnloggedWriteRefused` (L62) | UNREACHABLE + LEAK | "the graph index advances off it (`advance_index`)" (not in `__all__`); "no invariant or gate looks for source/index divergence" ("gate" is repo jargon); "the evaluator of a LOGGED store" | "...the graph index advances from it (`Store.catch_up`), replicas tail it (`TupleSource.catch_up_evaluator`) ... and nothing else detects the divergence." "the evaluator" becomes "the set engine". |
| `setengine/engine.py::SetEngine.add_tuple` (L823) | LEAK (low) | "(Store's rejection path relies on this to skip the evaluator rebuild)"; "the attribute holding this engine is reachable from anywhere the TupleSource is" | Drop both clauses. |
| `setengine/engine.py::SetEngine.lookup_reverse` (L1810) | LEAK (private) | "by construction (`memberset._normalize`)" | "by construction" |
| `setengine/engine.py::SetEngine.population` (L812) | LEAK (private) | "ids_of_type[T] for bare, ids_of_shape[(T,P)]" (private attributes) | "Concrete member ids (instance-local) of a `(type, predicate)` shape." |
| `setengine/engine.py::SetEngine.apply_logged` | LEAK (private, low) | "the `_apply_add` / `_apply_remove` sequence `rebuild()` would" | "the same mutation `rebuild()` would" |
| `setengine/memberset.py::MemberSet` (L49) | MISSING | auto-generated `MemberSet(pos: 'object', stars: 'frozenset', ...)` | "What `SetEngine.expand` returns: `pos` concrete member ids, `stars` wildcard shapes, `neg` ids a star covers but excludes; `ipos`/`ineg` the same for keys with no id. Ids are instance-local." |
| `setengine/memberset.py::MemberSet.contains_star`, `contains_entity`, `contains_userset` (L65/71/75) | MISSING | no docstring | One line each, like `contains_key`. |
| `setengine/models.py::RelationTuple` (L20) | LEAK / STALE | "Deliberately independent of the graph index's `store` table (no FK): the set engine is a standalone backend that happens to share a database in the test harness." (READ: that table is `zanzibar_store`; a `Store` shares the database in production too) | "One stored tuple, in table `zanzibar_relation_tuple`." Then the field gloss. (READ: `__tablename__` is `zanzibar_relation_tuple`.) |
| `setengine/setops.py::SetOps` (L23) | LEAK (private) | "(see `memberset._starpop`)" | Delete the parenthetical. |

## Verified clean (READ)

- Every raise message: 0 task ids, paths or dates (scan 3). One message mentions RC1
  (Group 2) because it carries the name of a private function.
- The `ClosureFanoutExceeded` raise message names only the env var, which every user can
  reach. The row's "fan-out messages name unreachable args" is now true only of the
  exception **docstring** (Group 1).
- The StaleRead messages say "set engine" (fixed in TK169 part 1, 2026-10-23e).
- The `zanzibar`, `zanzibar.graphindex`, `zanzibar.store` and `zanzibar.schema` module
  docstrings, and `Store`'s read and write methods (`check`, `lookup`, `lookup_reverse`,
  `expand`, `result_keys`, `add_tuple`, ...), have no defects.

## Totals (2026-10-28)

There are 66 rows. Several of them group methods: the MISSING rows cover 7 + 4 + 3 + 3
methods.

- Group 1: 11 rows
- Group 2: 9 rows
- Group 3: 11 rows
- Group 4: 10 rows
- Group 5: 15 rows
- Group 6: 10 rows
