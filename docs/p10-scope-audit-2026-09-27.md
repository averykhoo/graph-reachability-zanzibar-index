# `P10` — the scope audit, re-run hand-curated (2026-09-27)

**FROZEN 2026-09-27d, at `P10`'s close -- provenance, not a living document.** Status lines
below are as-of-then and several may now be false; live state: `HANDOFF.md` + the session
ledger (`python scripts/task.py board`). Corrections are appended dated at the top, never
edited into the body.
**Row ids (filed at close):** H1 = `TK114`, H2 = `TK112`, H3 = `TK113`, H4 = `TK111`,
H5 = `TK115`, H6 = `TK116`, H7 = `TK117`. `TK111` and `TK112` (the async stale-ALLOW) were
reproduced first-hand by the orchestrating session before filing; see those rows' logs.

**ACTIVE-PLAN, opened 2026-09-27 (session key `2026-09-27d`; audit and verify legs ran into
2026-09-28) — the body is provenance, not a living status.** This is the result of the `P10`
re-run of the 2026-08-10 scope-reduction audit: one discover-and-curate agent, twelve curated
items, each AUDITED by one agent and adversarially VERIFIED by a second, then reconciled here.
Every figure below is as-of its stated date. Live state is the task tree
(`python scripts/task.py show P10`, and the rows filed from § Proposed rows), never this file.
Corrections are appended **dated at the top**, never edited into the body. Freeze it when the
rows filed from it close.

**Provenance labels.** `READ` = first-hand read of the tree; `PROBED` = a script was run and its
literal output is quoted; `REASONED` = inference, not run; `UNVERIFIED` = claimed by one agent
and not re-checked by a second. Each claim names the agent: *discover*, *audit*, *verify*, or
*synth* (the session that wrote this file). A subagent report is evidence, not a finding: only
items a verifier UPHELD count as findings (see § Reconciliation).

Probe scripts and logs live under the gitignored `.scratch/wf-0927/probes/<item>/`, with the
audit and verify crash bags at `.scratch/wf-0927/p10-{audit,verify}-<item>.md`. **They will be
deleted.** The literal output needed to resume each item is transcribed below.

---

## 1. Why a re-run, and why candidates were re-discovered

`docs/subagent-fanout-runbook.md` § "The re-run this file is owed" told the next session to
mine the 279 transcripts of the failed 2026-08-10 fan-out (`wf_f8c85180-b74`) instead of
restarting from zero. **Those transcripts are gone.** On 2026-09-27 the orchestrator found no
`wf_f8c85180*` directory anywhere under `~/.claude`. *synth* re-checked this on 2026-09-28 with
`find ~/.claude/projects -maxdepth 5 -type d -name "wf_f8c85180*"`, which returned nothing
(`READ`, synth). So the candidate list was **re-discovered** from the live tree, not mined. The
runbook's other two rules still applied: a machine sweep DISCOVERS but does not DEFINE the
fan-out (rule 2), and the budget is set backwards from verification (rule 3).

## 2. The sweep, and the rule-2 predicate as applied

**Raw discovery** (*discover*, grep, 2026-09-27; `discovered_count` = `225`):

```
product scope-refusal raise sites ............................  37
REFUSED SHAPE blocks (product + oracle twin) .................  44
exclusion-marker lines in tests/ + formal/conformance/ ....... 144
total raw hits ............................................... 225
```

**Rule-2 predicate, applied by hand:** *does this exclude behaviour the system actually
ADMITS?* A parser refusal excludes nothing the system admits, so it fails at once. So does an
exclusion already owned by an open row, or already pinned exactly. From the survivors, twelve
were curated (`2026-09-27`), ranked by how likely each was to be a real hole. The budget came
from rule 3: twelve items, each with an audit and a verify.

**Rejected examples** (*discover*, `READ`; the full reasoning is in its crash bag):

- Parser / REFUSED SHAPE refusals (ASK-1 dangling refs and reference cycles, TK106 non-direct
  tuplesets, TK108 userset tuplesets, TK55 empty name, S-5/S-6, mixed or/and,
  `schema_version`, conditions): refused, so not admitted.
- `compile_ruleset(enable_boolean=False)` raising `UnsupportedByGraphIndex`: an opt-in
  refusal, not default-admitted behaviour.
- The untainted-tupleset computed-arm and tupleset-userset-restriction raises in
  `zanzibar_utils_v1.py`: unreachable from the checked parse since TK106/TK108. `TK107` owns
  the dead-path cleanup.
- `formal/conformance/test_conformance_remove_graph.py::_REMOVE_EXCLUDED`: a Lean-only
  exclusion owned by `P9`.
- `formal/conformance/test_conformance_enum.py::_tuple_space` never emitting object-`*`
  writes: owned by `TK101`.
- Refusal-absorbing drivers: owned by `TK110` (tests/) and pinned exactly by `TK71`
  (formal/conformance).
- The duplicate-add short-circuit in `tests/parity.py`: `WildcardIndex.add_tuple` declares
  ref-counted multigraph semantics, and `TupleSource` dedupes.
- Checked-parse bypass: every product schema entry point runs the validators.
- Graph-vs-set write-admission asymmetry: `ParityEngine._apply` asserts accept/reject
  agreement on every op, and `TK69` is closed.
- `check_invariants` calls without `schema_info`: all are on core-only, schema-less stores
  (`TK72`).
- The `pytest.ini` `ignore:UNPROVEN` filter: pinned by
  `tests/test_unproven_extension_warning.py`.
- W4Fragment / GraphAdmission field CLASSIFICATION: already pinned. Only the *coverage* of
  the admitted halves was curated (item `silent-fields-differential-coverage`).

## 3. Per-item results

Final verdict = the verifier's `corrected_verdict`. Every verifier UPHELD its audit, so no
verdict needed reconciling. The corrections the verifiers made to the audits' *details* are
in § Reconciliation.

| # | key | site (`file::symbol`) | audit | verify upheld? | FINAL | witness (short) | existing row |
|---|---|---|---|---|---|---|---|
| 1 | negation-through-data-cycle | `setengine/engine.py::SetEngine._would_cycle`, `::SetEngine.__init__`; `tests/oracle.py::Oracle.check` | HOLE | yes | **HOLE** | `viewer: [user] but not viewer from parent` + `doc:a parent doc:a` | none (R6-1 mentions the class; ASK-1 closed) |
| 2 | fanout-cap-boolean-revocation | `index_v4/core.py::ReachabilityIndex` (cap guard); `connectedstore/apply.py::_apply_row`; `connectedstore/store.py::ConnectedStore._fresh_enough` | HOLE | yes | **HOLE** | ban of a big group refused; async stall keeps a revoked ALLOW | none (TK33 cites the premise only) |
| 3 | decision15-set-engine-oracle-only | `setengine/engine.py::SetEngine.__init__` (`_ruleset = None`) | HOLE | yes | **HOLE** (coverage) | owc-feeding-leaf, D4, wildcard-userset-over-derived, cyclic-derived: never driven set-vs-oracle with removes | none (SD-1 owns the LIFT) |
| 4 | remove-node-no-cascade | `index_v4/wildcard.py::WildcardIndex.remove_node` | HOLE | yes | **HOLE** | `remove_node('editor','doc','x')` leaves `viewer` stale | none (TK80 closed) |
| 5 | object-star-query-grid | `tests/parity.py::ParityEngine._note_names`, `::_grid` | HOLE | yes | **HOLE** (coverage) | `check(user:a, viewer, doc:*)` True everywhere, never asked | none (TK101 owns WRITES) |
| 6 | silent-fields-differential-coverage | `formal/conformance/test_w4fragment_scope_pin.py::W4FRAGMENT_SCOPE` | SOUND | yes (verify2) | **SOUND** | — | none (P10 parent; ASK-2 adjacent) |
| 7 | paranoia-config-skew | `connectedstore/store.py::ConnectedStore.DEFAULT_PARANOIA` vs `tests/wildcard_helpers.py::make_wildcard_index` | SOUND | yes | **SOUND** | — | none (TK11 adjacent) |
| 8 | pg-leg-outside-gate | `tests/conftest.py` (`collect_ignore`); really `index_v4/models.py::EdgeV4` (`indirect_edge_count`) | HOLE | yes (re-framed) | **HOLE** | K-layer diamond chain overflows the path count | none (P18 is concurrency) |
| 9 | parity-grid-cap-sampling | `tests/parity.py::ParityEngine._grid` (`grid_cap: int = 600`, `self._rng.sample`) | HOLE | yes (verify2) | **HOLE** (coverage) | planted lie on `hank maintainer repo:docs` GREEN at cap | none |
| 10 | json-frontend | `zanzibar_utils_v1.py::parse_openfga_json`, `::openfga_json_to_dsl`, `::unparse_schema_ast` | HOLE | yes | **HOLE** (fidelity) | relation name `reader: [user]\n    define viewer` renders to 3 relations | none (TK109 one REASONED line; P23 adjacent) |
| 11 | undeclared-bare-restriction-type | `zanzibar_utils_v1.py::_validate_ast_consistency` | SOUND | yes | **SOUND** | — | ASK-1 (closed) decided it |
| 12 | conformance-userset-subject-bound | `formal/conformance/grid.py::grid` (`_USERSET_NAME_BOUND`, `*` excluded) | HOLE | yes | **HOLE** (coverage, tests/ side) | `doc:*#r0` on derived `r4`, never check-gridded | none (ASK-2, TK102 adjacent) |

**Counts per final verdict (2026-09-28):** `HOLE 9`, `SOUND 3`, `DISMISS 0`.

Of the nine HOLEs, four are **product** holes that give a wrong or undefined answer on an
admitted input: 1, 2, 4 and 8. One is a front-end **fidelity** hole: 10. Four are **coverage**
holes in the test instrument, where no divergence was found: 3, 5, 9 and 12. No item showed a
graph-vs-set-engine divergence on an input both backends accept through the composed
`ConnectedStore`. Items 2 and 8 are graph-index-vs-source divergences on the *async untokened*
read path, and item 4 is a divergence on a public API that `connectedstore/` never calls.

## 4. Reconciliation (where the verifier corrected the audit)

No verdicts disagreed. Each of the following corrects a detail, and each is carried into the
proposed rows below.

- **1, negation-through-data-cycle** (*verify*, `READ`). The class *is* documented, which the
  audit's "0 hits" undercounted: `formal/SEMANTICS.md` §4.4 marks non-stratifiable schemas
  as outside the verified envelope and ends "(Audit recommendation: reject upstream.)". That
  recommendation was never acted on. Worse, `formal/ARCHITECTURE.md` (`:62`, `:677` as of
  2026-09-28) and `formal/FINAL_REVIEW.md` (`:656` as of 2026-09-28) state that
  non-stratifiable schemas are "rejected upstream". That is **false for the standalone
  `SetEngine` and the oracle**, and true only for the graph and `ConnectedStore`
  (`connectedstore/schema_io.py::ensure_schema` compiles, so it refuses).
- **2, fanout-cap** (*verify*, `PROBED`). The audit lowered the cap after setup. The verifier
  re-ran with `ZANZIBAR_MAX_CLOSURE_FANOUT=20` set before import and a group grown one
  member at a time, which is a realistic path. It reproduced. It narrowed sync case A: it is
  loud, and other revocation forms still work. The real fail-open is the async stall, and it
  reproduces on a **plain non-boolean** schema.
- **8, pg-leg** (*verify*, `PROBED`). **Re-framed.** This is not a PostgreSQL SQL-semantics
  difference. It is an unbounded **path count** (`EdgeV4.indirect_edge_count`, which grows
  as `2^K` on a diamond chain) in a fixed-width integer column. It reproduces on **SQLite**
  at `K=63` (2026-09-28), inside the dialect the gate already runs. PostgreSQL only lowers
  the threshold to `K=31`. The PostgreSQL run is *audit* `PROBED`. The verifier started no
  cluster, so its `K=31` figure is `REASONED` from the compiled DDL. The audit's
  matrix-on-PostgreSQL control (`17 passed`) is *audit* only.
- **9, parity-grid-cap** (*verify2*, `PROBED`). Reproduced on an independent second store:
  9 oracle-TRUE queries were never compared on any op, and a last-write lie escaped on 15 of
  20 seeds (2026-09-28). The suite-wide census figures (`10.3%` of grids capped, `6.8%` of
  queries dropped) are **UNVERIFIED** by the verifier, which spot-checked two census points
  only (both matched). Declared vs undeclared: `docs/spec-deviations.md` item 2
  ("ParityEngine parity scope") says both "full-grid check" and "sampled above a cap", which
  contradict each other. `docs/specs/graph-boolean-ivm-spec.md` requires "the delta-affected
  pairs ∪ a sampled grid", and the delta-affected term is neither implemented nor waived.
- **10, json-frontend** (*verify*). Scope: this is JSON-to-DSL **fidelity**, not a
  graph-vs-set break. Both backends read the same rendered DSL.
- **12, conformance-userset-subject-bound** (*verify*, `READ`). Slightly overstated:
  `tests/test_irrelevant_alternatives.py::_iia_probe` *does* call `graph.check` on star
  from-chain subjects. But it only compares before against after an irrelevant add, never
  against the oracle, and only on 4 fixed corpora. The substance holds: nothing pins check
  exactness for star-userset subjects.
- **6, silent-fields** (*verify2*). The audit counted per W4 field. The verifier split
  sub-cases (`bareStar.objWildcard` vs `bareStar.usersetStar`, TTU onto derived vs untainted
  targets, and so on), and every admitted sub-case is still covered. One correction:
  `tests/test_matrix.py::test_matrix_4way_union_wildcard[0]` covers the object-wildcard
  sub-case, **not** a stored userset-star subject. Other tests cover the latter.
- **7, paranoia** (*verify*, `PROBED`). The count is 15 files that build `ConnectedStore`
  without `paranoia=`, not "about 20" (2026-09-28). The optional hardening was confirmed
  empirically: exporting `ZANZIBAR_PARANOIA=full` makes the off-gated sabotage pass
  (`3 passed`), so the matrix leg silently leaves the production default.
- **11, undeclared type** (*verify*, `PROBED`). Extended to the JSON front end, a TTU
  tupleset, and the real Lean `zcli` in spec, graph and fragment modes. All five backends
  agree on a 147-query grid (2026-09-28). SOUND stands.

## 5. The HOLEs — witness and proposed row

Suggested priorities use the `docs/README.md` vocabulary. The orchestrator files the rows;
this file does not. Where a hole touches an open row, § 6 gives the comment to add.

### H1 — negation through a data cycle (item 1)

**Witness** (*audit* `PROBED`, reproduced by *verify* with its own `vprobe.py`, 2026-09-27):

```
schema: type user / type doc / relations / define parent: [doc]
        define viewer: [user] but not viewer from parent
product parse_schema_ast OK dict / oracle parse_schema_ast OK dict
graph compile: EXC CyclicDerivedDependency ... [('doc', 'viewer')]
ConnectedStore EXC CyclicDerivedDependency ...
self-parent (user:u viewer doc:a; doc:a parent doc:a):
  se._ruleset is None: True; both adds -> True
  set.check {'a': True}; oracle {'a': True}
  RHS(set answer) = {'a': False} NOT A FIXPOINT; all fixpoints: NONE (paradox)
2-cycle (a<->b, u direct viewer of both):
  set.check {'a': False, 'b': False}; oracle the same
  RHS ... {'a': True, 'b': True} NOT A FIXPOINT
  all fixpoints: [{'a': False, 'b': True}, {'a': True, 'b': False}]
3-cycle: all True on both; NOT A FIXPOINT; NONE (paradox)
acyclic control: {'a': False, 'b': True}  (a fixpoint)
```

The two evaluators agree only because they share the in-progress ⇒ False convention
(`tests/oracle.py::Oracle.check`, inner `sat`). The answers are not models of the schema.
Every generator self-reference is positive, so no generator reaches this (`READ`, audit +
verify).

**Proposed row** — *"Refuse non-stratifiable negation: a derived cycle through a TTU target
with a `but not` subtrahend edge"*, **LATER**, size S-M.
Brief: after ASK-1, a derived cycle through a TTU target is still legal. When an edge on that
cycle sits in a `but not` subtract position (e.g. `viewer: [user] but not viewer from
parent`), the schema has no fixpoint, or several, on cyclic data. The graph and
`ConnectedStore` refuse it (`CyclicDerivedDependency`). The standalone `SetEngine` and the
oracle admit it and agree on answers that are not models (probe above). Refuse it at parse
time in both parsers, in a `_validate_*` function in `zanzibar_utils_v1.py` with an
independent twin in `tests/oracle.py`, each with REFUSED SHAPE / WHY / INSTEAD. INSTEAD:
`blocked: [user] or blocked from parent` plus `viewer: [user] but not blocked`. Keep positive
TTU-target cycles legal: `tests/genswarm.py` `self_ttu` and the ASK-1 witnesses depend on
them. Pin both schemas as refused, with sabotage. Correct `formal/ARCHITECTURE.md` and
`formal/FINAL_REVIEW.md`, whose "rejected upstream" becomes true only then, and act on
`formal/SEMANTICS.md` §4.4's standing recommendation. This is a schema-refusal decision of
the same kind as ASK-1 and TK106. Under "Who decides" the session may take it, since the
refused shape has no defined semantics. Until it lands: a positive characterization pin of
the answers, never an xfail.

### H2 — the fan-out cap can refuse a revocation, and a capped row stalls async revocations (item 2)

**Witness** (*verify* `PROBED`, fixed cap `ZANZIBAR_MAX_CLOSURE_FANOUT=20` set before import,
2026-09-27; schema `group{member:[user]}`,
`doc{grant:[user, group#member]; banned:[user, group#member]; viewer: grant but not banned}`,
which both parsers accept):

```
A2 sync:  grant (3 members): OK -> 4 ... member add u29: OK -> 31
          viewer u0 before ban: True
          ban group:big (30 members): REFUSED ClosureFanoutExceeded: ... 30 closure rows (30 ancestors x 0 descenda...
          graph viewer u0 after refused ban: True | set engine: True ; oracle if ban had landed: False
          ban user:u0 individually: OK -> 32 ; REMOVE grant: OK -> 33
C2 async, PLAIN schema: tokens grant/remove: 32 33 ; catch_up REFUSED ClosureFanoutExceeded ; lag: 2
          untokened check u0 viewer doc:old (revoked in source): True
          tokened check (at_least=remove token): False ; set engine: False
D3 sync:  doc{grant;banned;viewer: grant but not banned} + folder{reader:[doc#viewer]}, 30 folders
          un-ban REMOVE: REFUSED ClosureFanoutExceeded: ... 30 closure rows (0 ancestors x 30 descenda...
```

Sites (`READ`, verify, line numbers as of 2026-09-27): `index_v4/core.py` `:805`
`if count > 0 and self.max_closure_fanout and fanout > ...`, with the "REMOVALS ARE
DELIBERATELY EXEMPT" comment at `:793`. `connectedstore/apply.py::_apply_row` re-raises
("the cursor cannot advance past this row"). `connectedstore/store.py::ConnectedStore._fresh_enough`
returns `at_least is None or ...`. `index_v4/processor.py::DeltaProcessor._write_derived`
calls `widx.add_tuple` (`:712`). `tests/test_reg17_closure_fanout_cap.py` has 0 hits for
`but not|subtrahend|banned|revoc` (synth re-grep, 2026-09-28).

**Proposed row** — *"Fan-out cap vs revocation: under `but not` a revocation is an ADD, and a
capped async row strands every later removal"*, **NEXT**, size M.
Brief: CLAUDE.md says removals are exempt from the cap "because a cap that can refuse a
revocation is a fail-open". Three admitted paths contradict that (witness above):
(a) sync: banning a large group through a `but not` subtrahend is an ADD, and it is refused;
(b) sync: an un-ban REMOVE is capped through `DeltaProcessor._write_derived`, which fails
closed;
(c) async, any schema: a capped logged row stalls `catch_up`, and untokened
`ConnectedStore.check` keeps serving revoked grants without bound.
Fix: (1) exempt edges routed onto an Exclusion's subtrahend leaf. The compiler knows them
in `RuleSet.compiled`, and their fan-out is linear. (2) Make freshness stall-aware:
`_fresh_enough(None)` stops certifying index reads while the cursor is stalled on a refused
row, and falls back to the set engine as tokened reads already do. (2) is shared with H4.
Pin A2, C2 and D3 as positive tests in `tests/test_reg17_closure_fanout_cap.py`, sabotaged.
Correct the CLAUDE.md "removals are exempt" bullet, the `core.py` comment, the TK33 premise,
and `docs/spec-deviations.md` 2026-07-29c's "Does not bite at the 100,000 default" (false for
a group of more than 100k members).

### H3 — `remove_node` on a routing source leaves derived relations stale (item 4)

**Witness** (*verify* `PROBED`, independent `vprobe.py` with three references, 2026-09-27;
schema `group{member:[user, group#member]}`,
`doc{blocked:[user]; editor:[user, group#member]; viewer: editor but not blocked}`; tuples
through `RuleSet.apply` + `run_cascade`:
`group:h#member@user:alice, group:g#member@group:h#member, doc:x#editor@group:g#member,
doc:x#editor@user:bob, doc:x#editor@user:carol, doc:x#blocked@user:carol`):

```
leaf_families: [('doc', 'viewer.0'), ('doc', 'viewer.1')]
routing of bob editor tuple -> ['editor', 'viewer.0']
Victim ('editor','doc','x'), identical at paranoia off/full, cascade_after False/True:
  alice viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  bob   editor  graph=False oracle=False setengine=False sanctioned_graph=False OK
  bob   viewer  graph=True  oracle=False setengine=False sanctioned_graph=False DIVERGES
  check_invariants(schema_info) on committed state: PASSED
Victim ('blocked','doc','x'):
  carol viewer  graph=False oracle=True  setengine=True  sanctioned_graph=True  DIVERGES
```

`bob editor=False` next to `bob viewer=True` under `viewer = editor but not blocked` means
the graph is inconsistent with itself, whichever reference is chosen (`REASONED`, verify).
The internal leaf names `viewer.0` / `viewer.1` are also admitted as `remove_node` victims:
*audit* `PROBED`, *verify* `READ` only. `connectedstore/` has no `remove_node` caller (`READ`).

**Proposed row** — *"`WildcardIndex.remove_node` on a boolean routing source or a leaf family
leaves derived edges stale; the invariants are blind to it"*, **LATER**, size S-M.
Brief: `index_v4/wildcard.py::WildcardIndex.remove_node` refuses only `*`, derived-public
names (`_assert_derived_exclusivity`) and residue-recorded nodes (`_residue_records_node`,
TK80). It runs no cascade. `RuleSet.apply` fans a routing-source tuple onto the public node
AND a separate leaf node, so removing the public node leaves the leaf copy, and the derived
answer goes wrong at every paranoia tier (witness above). Fix with mechanical refusals, no
algorithm change: (1) a leaf-family fence mirroring `WildcardIndex.check`'s; (2) on a boolean
schema, refuse a node whose (type, predicate) routes into a leaf family, and name the
sanctioned route (remove the incident tuples through `RuleSet.apply` + `run_cascade`). Both
get REFUSED SHAPE / WHY / INSTEAD blocks. Pin the editor and blocked arms, plus a subject-only
control that still removes cleanly, and run a sweep with an M0 control. The exposure is the
public admin API only.

### H4 — path-count overflow poisons the async cursor (item 8)

**Witness.** Schema `type user / type group relations define member: [user, group#member]`,
which both parsers accept. Writes: `user:u member group:L0`, then for each layer `i`:
`L_i#member → A_i`, `L_i#member → B_i`, `A_i#member → L_{i+1}`, `B_i#member → L_{i+1}`.

*verify* `PROBED` on SQLite, `K=63`, 2026-09-28:

```
VK=63 async: writes=255 refused=0
  catch_up attempt 0/1/2: OverflowError: Python int too large to convert to SQLite INTEGER | lag=255
  check(u member L1): ConnectedStore.check(untokened)=False set_engine=True oracle=True
VK=63 async, VBATCH=1 (revoke of mallory viewer doc:secret logged behind the poison row): lag=2
  check(mallory viewer doc:secret): ConnectedStore.check(untokened)=True set_engine=False oracle=False
  tokened check(at_least=255) mallory=False ; tokened lookup(u): LookupNotFresh
VK=63 sync: refused: ('+', ('member','group','B62','member','group','L63'), 'OverflowError', ...)
```

*audit* `PROBED` on PostgreSQL, `K=31` (125 tuples), 2026-09-27:

```
pg sync=True  K=31 accepted=124/125 first_refusal=(('member','group','B30','member','group','L31'), 'DataError', 'integer out of range')
pg sync=False K=31 accepted=125/125 catch_up_err=('DataError', 'integer out of range') lag=125 | check(u member L31): graph=False set_engine=True oracle=True
pg after revoke: untokened check (graph)=True | set_engine=False | tokened check(at_least=127)=False
```

Column widths (`READ`/`PROBED`, both agents): every integer column is `INTEGER`, which is
int4 on PostgreSQL (ids `SERIAL`) and int64 on SQLite, including `index_v4/models.py::EdgeV4`
`indirect_edge_count`. The closure fan-out cap never fires on this witness.

**Proposed row** — *"Path-count overflow: an admitted write whose apply overflows
`indirect_edge_count` wedges async `catch_up`, and untokened reads keep a stale ALLOW"*,
**NEXT**, size M.
Brief: `EdgeV4.indirect_edge_count` counts derivations. A K-layer diamond chain makes it
`2^K`, which overflows at `K=31` on PostgreSQL (the only supported server) and at `K=63` on
SQLite. Sync fails closed with a raw `DataError` / `OverflowError`. Async logs the write,
`catch_up` retries the poison row forever, and every later row, revocations included, never
reaches the index. Untokened `ConnectedStore.check` then serves a stale ALLOW without bound
(witness above). Widening to `BigInteger` only moves the ceiling. Decide instead between a
clean admission refusal, raised before the `TupleLogV1` row commits on both dialects, and
count saturation. Saturation breaks exact decrement, so refusal is probably right. Add H2's
stall-aware freshness (shared fix). Permanent test on SQLite at `K=63`, async, with the
revoke-behind-the-poison-row variant, sabotaged. Optionally add a PostgreSQL leg of the matrix
behind `ZANZIBAR_TEST_DSN`: *audit* measured `17 passed in 453.83s` on 2026-09-27 via a
redirect plugin. The `.scratch/wf-0927/probes/pg-leg-outside-gate/` probes are the starting
point. *audit* also flagged, `REASONED` only: `SERIAL` int4 primary keys cap a store's
lifetime log and node ids at `2^31-1` on PostgreSQL (fails closed).

### H5 — JSON front end: names are pasted unescaped into the DSL (item 10)

**Witness** (*verify* `PROBED`, independent `vprobe.py`, 2026-09-27):

```
V1 relation name 'x: [user]\n    define secret' (computedUserset of owner)
   rendered DSL: define owner: [user] / define x: [user] / define secret: owner
   ROUND-TRIP equal: False
   add user:alice x doc:d1: OK -> 1 ; check alice x d1: OK -> True
V2 {"type":"user","wildcard":false} -> define viewer: [user:*]
   add user:alice ... RAISES AdmissionRejected ; add user:* ... OK -> 1 ; check ghost viewer d1: OK -> True
V3 JSON string with duplicate "viewer" key: accepted, last value wins (DSL twin: duplicate relation definition)
V4 type name 'doc\ntype folder2' re-parses with keys [('folder2','viewer')]
V5 control (well-formed model): ROUND-TRIP equal: True
```

Sites (`READ`, verify): `zanzibar_utils_v1.py::parse_openfga_json` checks no whitespace,
newline or `:` in declared names, and calls `json.loads` with no `object_pairs_hook`.
`::_json_restrictions` has `wildcard = 'wildcard' in e and e['wildcard'] is not None`.
`::unparse_schema_ast` writes names raw. `::openfga_json_to_dsl` never re-parses its own
output. The oracle has no JSON front end.

**Proposed row** — *"JSON front-end fidelity: `openfga_json_to_dsl` can render a different
schema than the JSON declared"*, **LATER**, size S-M.
Brief: the JSON path admits declared names containing a newline, `:` or whitespace, a
duplicate JSON key (last wins), and `"wildcard": false` (which widens to `[T:*]`). The
rendered DSL then declares different relations or types, and `ConnectedStore` admits writes
against a relation the JSON never declared (witness above). The front end's own header
promises unsupported input is "rejected loudly, never skipped". Fix, strongest first:
(1) refuse unless `parse_schema_ast(unparse_schema_ast(ast)) == ast`, which closes the class;
(2) refuse non-DSL-safe declared names, reusing P23's contract once it is decided;
(3) refuse duplicate keys via `object_pairs_hook`;
(4) require `wildcard` to be a JSON object.
Each refusal lives in a `_validate_*` / `_reject_*` function with REFUSED SHAPE / WHY /
INSTEAD, and raises `tests/test_refused_shape_comments.py`'s `MIN_HEADERS`. Pin V1–V4 in
`tests/test_openfga_json.py`, sabotaged. This is not a graph-vs-set divergence, because both
read the rendered DSL. Operator nesting is fine: *audit* measured `checked 32 queries,
mismatches 0` (2026-09-27).

### H6 — decision-15 schemas: set engine vs oracle is not driven with removes (item 3)

**Witness** (*verify* `PROBED`, `v_probe.py`, 2026-09-28):

```
W1 owc (doc,editor), view: editor but not banned
   graph compile: REFUSED UnsupportedByGraphIndex: object-wildcard shape (doc, view) expands onto the compiled leaf predicate (doc, view.0)
   graph joined: False | _ruleset None: [True, True]
   add ('...','user','u1','editor','doc','*') -> accepted=True ; remove ... -> accepted=True
   W1 seed 0: 3-way parity OK, accepted {'add': 27, 'remove': 18}
W2 reader: [group:*#ok, group#member]  (ok = member but not blocked)
   REFUSED UnsupportedByGraphIndex: ... wildcard userset restriction [group:*#ok] over the derived relation group#ok
   add ('member','group','g2','member','group','g1') -> accepted=True   (closes a data cycle)
W2C control (reader: [group#member]): graph joined: True, close cycle accepted = False
v_bsb_decomp: ANY applicable family ...: {'star-tupleset-over-derived': 768, 'owc-tupleset-of-derived-ttu': 384, 'owc-on-derived': 384}
```

No divergence was found. The gap is that the owc-feeding-leaf family, D4 (owc upstream of a
derived TTU target), wildcard-userset-over-derived, and cyclic-derived-with-removes are never
driven set-vs-oracle. Only `pytest.raises` pins cover them
(`tests/test_boolean_compile.py::test_object_wildcard_expanding_onto_leaf_rejected`,
`::test_object_wildcard_upstream_of_derived_ttu_target_rejected`), and every other driver
skips refused schemas (`tests/test_generator_coverage.py::_sweep`,
`tests/test_lookup_oracle.py::test_lookup_oracle_gate_generated_schemas`,
`tests/test_zt_p5_readjudication.py`). `connectedstore/schema_io.py::save_schema` refuses all
of them, so only standalone `SetEngine` users are exposed.

**Proposed row** — *"Oracle-only SetEngine mode: set-vs-oracle differential with removes for
every decision-15 family"*, **LATER**, size S-M.
Brief: on a graph-refused schema, `setengine/engine.py::SetEngine.__init__` sets
`_ruleset = None`. That makes `::_would_cycle` return False, so data-cycle rejection is off,
and the only cross-check is the oracle. Add a deterministic parametrized test over
`tests/genswarm.py::REJECTION_WITNESSES` plus the `tests/test_boolean_compile.py` refusal
witnesses. For each: build a `ParityEngine`, assert the graph is absent and `_ruleset is None`,
run a seeded add/remove walk that includes star-object and cycle-closing writes, and floor the
accepted removes above zero. Run the lookup-oracle gate on refused schemas instead of skipping
them. Decide and record the admission asymmetry (the same `group#member` accepts a cycle only
when an unrelated relation makes the schema graph-refused). Fix the stale "Boolean schemas
have no graph partner" comment in `_would_cycle`. Delete or assert-out the dead `continue` in
`tests/test_hypothesis.py::test_every_tupleset_kind_is_driven_against_the_oracle`: *audit*
measured 0 of 10 cells refused (2026-09-27). If H1 lands first, its negative cycles leave this
row's cyclic-derived witness set.

### H7 — `ParityEngine._grid` coverage: object `*`, star from-chain subjects, cap sampling (items 5, 9, 12)

All three sit in one function, `tests/parity.py::ParityEngine._grid`, and every one of them
changes the `rng.sample` pool. **Recommended as ONE row** so the pool shifts once, not three
times. No product divergence was found in any of the three.

**Witness 5, object `*`** (*verify* `PROBED`, 2026-09-28). Schema `folder{viewer:[user]}`,
`doc{parent:[folder]; viewer: viewer from parent}`, `object_wildcard_shapes={('doc','parent')}`,
tuples `('...','folder','f1','parent','doc','*')` and `('...','user','a','viewer','folder','f1')`:

```
grid size=24 object-* queries=0 subject-* queries=8 ; witness in grid? False
check(user:a, viewer, doc:*): oracle, graph, set:py, set:roaring all True
sabotage (backends return False for object '*') on tests/test_parity_engine.py:
  M0: 19 passed ... {"graph_objstar": 0, "set_objstar": 0} ; MG: 19 passed ; MS: 19 passed
control tests/test_matrix.py -k union_wildcard: M0 3 passed ; MG 2 failed, 1 passed ; MS 2 failed, 1 passed
```

**Witness 12, star from-chain userset subject** (*verify* `PROBED`, seed-24 schema, 2026-09-28):
`doc{parent:[doc, doc:*]; r0:[user]; r1: r0 from parent; r2: r1; r3:[user, user:*];
r4: r2 from parent and (r0 from parent or r0 from parent)}`. Writes
`('...','doc','d2','parent','doc','d1')`, `('...','user','u1','r3','doc','d2')`,
`('...','doc','*','parent','doc','d1')`, `('...','user','u1','r0','doc','d1')`,
`('...','user','u1','r3','doc','d1')`.

```
graph joined: True None ; derived_families: [('doc', 'r4')]
Q ('r0','doc','*','r1','doc','d1') {'graph': True, 'set:py': True, 'set:roaring': True, 'oracle': True}  (same for r2, r4)
IN-GRID ... parity= False conf= False hyp= False   (all 3 queries)
star-userset subjects in parity grid: []
```

**Witness 9, cap sampling** (*verify2* `PROBED`, `v2_probe.py`, 2026-09-28; `github.fga`, 14
accepted writes, the last being `user:hank maintainer repo:docs`):

```
M0 no-lie cap=600: GREEN  graph_present=True leaf_families=0
final pool=1056 final compared=600 ever compared=931 never=125
never-compared TRUE: ('...', 'user', 'hank', 'maintainer', 'repo', 'docs')
planted lie cap=600: GREEN
planted lie cap=10**9: RED: check parity broken after add ('...', 'user', 'hank', 'maintainer', 'repo', 'docs'): q=('...', 'user', 'hank', 'maintainer', 'repo', 'docs') graph=False oracle=True
lie on the last write's own check escapes at cap=600 on 8/20 seeds   (independent store: 15/20)
```

**Proposed row** — *"`ParityEngine._grid` never asks object-`*` targets or star from-chain
subjects, and its cap sample can skip the last op's own effect"*, **LATER**, size S-M.
Brief: three coverage gaps in the default integration engine's grid, with no divergence found.
(a) `_note_names` drops object `*`, so no object-`*` query is ever asked, even after `doc:*`
is stored. Sabotaging the backends' object-`*` answers leaves `tests/test_parity_engine.py`
green. (b) Subject shapes come only from Direct restrictions, so star-userset subjects created
by a star tupleset (`doc:*#r0`, including on a derived target) are asked only on the lookup
surfaces. Mirror `tests/test_lookup_oracle.py::_subject_candidates`. (c) Above `grid_cap`,
Layer A is `rng.sample`d per op with no floor, so a divergence confined to the last write's
own queries escapes with probability about `(N-cap)/N`.
Fix: object `*` in Layer A for object-wildcard shapes, plus an rng-free Layer-B guarantee;
TTU from-chain shapes, including `*`, in `subject_shapes`; an rng-free WRITE-LOCAL floor
appended after the cap, and optionally a rotating cursor in place of `rng.sample`. Apply the
same to `tests/genswarm.py::grid_for` (cap 400) and `tests/test_hypothesis.py::_grid`.
Reconcile `docs/spec-deviations.md` item 2 ("full-grid" vs "sampled") with the spec's
"delta-affected pairs ∪ a sampled grid". Pin each witness positively. The planted-lie probe
must go GREEN → RED after the fix, with an M0 control. Leave
`formal/conformance/grid.py::grid` and
`formal/conformance/test_conformance_enum.py::_graph_query_filter` alone: they mirror the
Lean `hqs` / `hqo` scope, and `TK101` revisits the second.

## 6. Comments for existing open rows (not new rows)

- **`ASK-2`** (wildcard extensions): star-userset subjects created by a star tupleset
  (`doc:*#r0`) agree 4-way but are asked on the check surface by no grid. The fix is in H7.
- **`TK109`**: its REASONED JSON line ("parse_openfga_json has no empty-relation-name check")
  is subsumed by H5. *audit* probed that empty names fail loudly downstream; the live JSON holes
  are newline / `:` names, duplicate keys and `wildcard: false`.
- **`P23`** (declared-name charset): H5's name refusal should reuse P23's contract once it is
  decided. P23 currently never mentions the JSON path.
- **`SD-1`**: if SD-1 lifts a refusal, that family leaves H6's oracle-only witness set.
  Until then, H6 owns the set-vs-oracle coverage.
- **`TK33`**: its premise cites "removals are exempt" from the fan-out cap. H2 shows the
  premise is false under `but not` and on the async schedule.

## 7. SOUND items — optional hardenings, not holes

- **Item 6, silent fields.** Every SILENT/MIXED admitted sub-case has at least one
  deterministic graph+set+oracle test (*verify2* plugin, `records=502, failed=0`, 2026-09-28).
  The weakness is durability: the coverage is incidental, and nothing ties a
  `W4FRAGMENT_SCOPE` row to a differential (`REASONED`). An optional LATER hardening: drive
  every ADMITTED `formal/conformance/w4_scope_probes.py::SCOPE_PROBES` input through
  `ParityEngine`, with a per-field floor. *audit*'s instrument control (negate the oracle)
  turned all 16 graph-joining probes red.
- **Item 7, paranoia.** The production default (off, no hooks) is in the differential through
  `tests/test_matrix.py::ConnectedBackend` and `ParityEngine(paranoia=False)`. Optional S
  hardening: pin `paranoia='off'` in `ConnectedBackend.__init__`, or assert it equals
  `ConnectedStore.DEFAULT_PARANOIA`, because an exported `ZANZIBAR_PARANOIA=full` silently
  moves the leg (*verify* `PROBED`: `3 passed` under the off-gated sabotage).
- **Item 11, undeclared bare type.** A type's declared-ness reaches no AST, no Lean `Schema`
  and no conformance JSON, so `[ghost]` is the ordinary relation-less `[user]` case. ASK-1
  (closed) decided not to refuse it. No row.

## 8. Side finding (outside the twelve)

`tests/test_invariants_docstring_matches_body.py::test_every_schema_backed_check_invariants_call_passes_schema_info`
walks `root.rglob('*.py')` with a skip set that lacks `.claude` (`READ`, synth, 2026-09-28).
So it scans any workflow worktree under `.claude/worktrees/`. *audit*
(silent-fields-differential-coverage) observed this test FAIL on the main tree for exactly
that reason. `git worktree list` on 2026-09-28 shows several `.claude/worktrees/wf_*`
entries, so a `tests-tile` phase on the main tree can go red until they are removed. The fix
is one token (`'.claude'` in the skip set), or removing the worktrees before the gate.

## 9. Honest limits — what was NOT audited

- **Curated, not exhaustive.** 12 of the `225` raw hits were audited (2026-09-27). The other
  hits were triaged by *discover* with the rule-2 predicate, by hand, in one pass, **without
  an audit or verify leg**. Most are parser refusals, which are not admitted by construction,
  or exclusions already owned by an open row (P9, TK101, TK110/TK71, TK107, SD-1, P25, P23,
  TK44, TK109, P15, P16, P18, P19, P24). A mis-triage there would not have been caught. The
  runbook's rule 3 (budget backwards from verification) is why: twelve items at two agents
  each, several of them multi-hour probes (the *verify2* silent-fields plugin alone took
  `1722.30s` + `513.17s` on 2026-09-28), is what one session can verify and reconcile.
- **The 2026-08-10 transcripts were not mined** (they no longer exist, § 1), so no
  cross-check against the original 278-item list was possible. The two lists were built by
  different methods.
- **PostgreSQL** was exercised only by *audit* on item 8 (a private cluster, since
  destroyed). No verifier ran PostgreSQL.
- **Lean** was run only by the item-11 verifier (`zcli`). No other item's claim about the
  Lean scope was executed. Those claims are `READ` of the `.lean` sources.
- **No product or test file was edited** by any agent in this run. Every witness is a scratch
  probe until the rows above land it as a permanent, sabotaged test.
