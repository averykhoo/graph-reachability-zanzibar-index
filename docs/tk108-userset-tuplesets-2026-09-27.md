# `TK108`: a `from`-tupleset may not restrict to a userset

**ACTIVE-PLAN (`docs/README.md` §3), opened 2026-09-27 (session `2026-09-27`).** Corrections
are appended dated at the top. FROZEN when `TK108` closes. Live state is
`python scripts/task.py show TK108`, never this file. Figures were measured on `2026-09-27`
against HEAD `7ac21c6` plus this session's working-tree diff.

Provenance labels: **READ** (first-hand, this session), **REASONED**, **MEASURED** (a run
whose output is quoted), **UNVERIFIED**, **SUBAGENT** (an agent's report, not re-run by the
session). Two subagents were used, both for § 4: a read-only census of the refusal sites,
then a comments-only edit, which the session verified mechanically (§ 4).

## § 0 The decision (the user's, 2026-09-27)

The user asked whether the graph index could handle `parent: [folder#member]` as a
tupleset, then: *"Okay then let's refuse the shape. Just to be sure, try the other shape to
accomplish the same thing and then document it somewhere."* In the same message the user
added a standing rule: *"whenever we refuse a shape can there be a comment in the parser
that explains why and the alternative"* (§ 4, and `CLAUDE.md` § Gotchas).

## § 1 Why the shape is refused (READ)

A stored tuple `doc:d1#parent@folder:f1#member` under `viewer from parent`:

- `tests/oracle.py::Oracle.check` (`ttu_leaf`) takes the stored parent's type and name and
  never reads its predicate: the parent is `folder:f1`.
- `setengine/engine.py::SetEngine.check` (`ttu_leaf`) does the same: it unpacks the parent
  key as `pt, pn, _pp` and discards `_pp`. Its comment calls userset tuplesets "unusual
  but handled for completeness".
- `zanzibar_utils_v1.py::_validate_ttu_tuplesets` refused the schema at graph compile time
  (`UnsupportedByGraphIndex`), calling it "drop-the-predicate parent semantics no spec
  defines (blind-audit D3)". `SetEngine.__init__` catches that and degrades.

So the oracle and the set engine agreed on a meaning nothing specified, and the graph
refused the schema: the "graph refuses, set engine accepts" divergence. OpenFGA refuses it
(tupleset relations must be directly assignable types).

**Could the graph have implemented it instead? (REASONED)** Mechanically yes: accept a
parent with any predicate as if it were bare. But the only type-consistent meaning IS
"ignore the predicate", because the `from` target must be declared on the restriction's
type (`folder`), while members of `folder#member` are `user`s. That meaning is exactly
`parent: [folder]`, so supporting the userset form buys no expressiveness; it only admits a
stored predicate that is silently ignored, the same "arm silently ignored" defect `TK106`
removed. Refusing closes the divergence at no cost in expressible schemas.

**D1: refuse at PARSE time in both parsers** (the `TK106` precedent, its D1): the check is in
`zanzibar_utils_v1.py::_validate_tuplesets_direct` and the oracle twin
`tests/oracle.py::_validate_tuplesets_direct`. The stable message substring is
`tupleset may not restrict to a userset` (`tests/genswarm.py::TUPLESET_NO_USERSET`).
Wildcard userset `[folder:*#member]` is refused too; bare wildcard `[folder:*]` stays legal
(`ASK-2`).

**D2: when a tupleset is BOTH non-direct and userset-restricted, `TK106`'s message wins**
(its check runs first), so no existing `tupleset must be direct` pin moves.

**D3: `_validate_ttu_tuplesets`'s userset branch stays**, as the last line of defence for a
hand-built AST; a checked parse no longer reaches it.

## § 2 The rewrite answers what the refused shape answered (MEASURED 2026-09-27)

Probe `.scratch/tk108/probe_rewrite.py` (gitignored; the durable form is
`tests/test_tk108_userset_tupleset_rewrite.py`), run BEFORE the refusal landed. OLD runs
through `tests/parity.py::ParityEngine` with the graph dropped (3-way: both set engines and
the oracle, unanimous); NEW runs 4-way with the graph in. Same data, tupleset links mapped.

| refused shape | rewrite |
|---|---|
| `parent: [folder#member]` | `parent: [folder]` and `parent_member: member from parent` |
| `parent: [folder:*#member]` | `parent: [folder:*]` and `parent_member: member from parent` |
| `parent: [folder, folder#member]` | `parent: [folder]`, `parent_via_member: [folder]`, `parent_member: member from parent_via_member`, and every `x from parent` also `or x from parent_via_member` |

Queries on the old `parent` are compared against `parent_member` (and against
`parent or parent_member` in the mixed case); `viewer` against `viewer`.

```
== userset: OLD graph=DROPPED (UnsupportedByGraphIndex: relation doc#viewer: tupleset 'pare)  NEW graph=IN
  54 queries, 0 differ (each check is unanimous across that engine's backends + oracle)
== mixed-bare-and-userset: OLD graph=DROPPED (UnsupportedByGraphIndex: relation doc#viewer: tupleset 'pare)  NEW graph=IN
  27 queries, 0 differ (each check is unanimous across that engine's backends + oracle)
== wildcard-userset: OLD graph=DROPPED (UnsupportedByGraphIndex: relation doc#viewer: tupleset 'pare)  NEW graph=IN
  54 queries, 0 differ (each check is unanimous across that engine's backends + oracle)
```

CONTROL (`.scratch/tk108/probe_control.py`): the naive rewrite, `parent: [folder]` with the
old `parent` compared against the new `parent`, must differ, and it does. It also counts the
positive answers, so a 0-differ result cannot be an all-False grid:

```
== userset: ...
  DIFF ...:user:alice parent->parent doc:d1: old=True new=False
  DIFF ...:user:dave parent->parent doc:d2: old=True new=False
  DIFF member:folder:f1 parent->parent doc:d1: old=True new=False
  DIFF member:folder:f2 parent->parent doc:d2: old=True new=False
  54 queries, 4 differ, old-True so far 8
== mixed-bare-and-userset: 27 queries, 0 differ, old-True so far 12
== wildcard-userset: 54 queries, 0 differ, old-True so far 20
```

The permanent test derives its expectation from the oracle over the UNCHECKED parse of the
refused schema (the semantics served before `TK108`), runs the rewrite 4-way, and carries
its own naive-rewrite control. Its two sabotages (S1: break the rewrite; S2: disable the
product refusal) are quoted in its module docstring.

## § 3 Breakage census (MEASURED 2026-09-27)

Full `tests/` and `formal/conformance/` with the refusal in place (and the genswarm /
blind-audit pins already moved), `-p no:cacheprovider -rfE --continue-on-collection-errors`,
run concurrently:

```
tests/               1 failed, 1411 passed in 1518.02s (0:25:18)
formal/conformance/  1 failed, 1080 passed in 1908.00s (0:31:48)
```

Both failures are an ARTIFACT OF THE INSTRUMENT, not of the refusal: each is a source-
introspection anti-vacuity check (`inspect.getsource(Z._plan_leaves)`) that found no
`LeafSpec` literal, because the § 4 comment sweep inserted lines into `zanzibar_utils_v1.py`
WHILE the runs were in flight, so the already-imported module's line numbers pointed into
shifted text:

```
FAILED tests/test_schema_shapes.py::test_fga_corpus_feature_coverage_does_not_regress
  E  AssertionError: ANTI-VACUITY: no LeafSpec kind literal found in _plan_leaves
FAILED formal/conformance/test_conformance_nary_strata.py::test_required_leaf_kinds_are_exactly_the_compilers_kinds
  E  AssertionError: ANTI-VACUITY: no `LeafSpec(..., '<kind>')` literal found in ...
```

Re-run alone on the settled tree: the first with `tests/test_generator_coverage.py`,
`34 passed`; the second `1 passed`. REASONED why the real breakage is zero where TK106's was
~90: the graph compiler already refused this shape, so every graph-side pin, corpus and
generator path already treated it as refused; only the two genswarm witnesses and the
blind-audit test named the old exception class, and they were moved first. Lesson worth
keeping: **do not edit a module under a running census that introspects its source.**

## § 4 Refusal comments (the user's standing rule, 2026-09-27)

**The rule.** Every refused schema shape carries, directly above its `raise`, a block
`# REFUSED SHAPE (<id>): <what>.` / `# WHY: ...` / `# INSTEAD: <DSL>` (or `none -- <reason>`),
in every parser that refuses it. Recorded in `CLAUDE.md` § Gotchas; enforced by
`tests/test_refused_shape_comments.py`.

**Census (SUBAGENT, HEAD `7ac21c6`; report `.scratch/tk108/refusal-census.md`, gitignored).**
One `raise` per row across `zanzibar_utils_v1.py`, `tests/oracle.py`, `setengine/engine.py`:
SHAPE 43, SYNTAX 29 (+1 mixed), NOT-SCHEMA 31. Of the SHAPE rows, only
`_validate_tuplesets_direct` (TK106) stated both a why and an alternative. Two error MESSAGES
suggest a stale alternative: `zanzibar_utils_v1.py::_emit_expr` ("use the set engine";
the real fix is the default `enable_boolean=True`) and
`zanzibar_utils_v1.py::_validate_ttu_tuplesets` ("make the whole chain boolean", refused at
parse since TK106). The messages were left as they are (tests may match them); the comment
at each carries a `NOTE: the message's own suggestion is stale` line and the right
alternative.

**Sweep (SUBAGENT edit, VERIFIED first-hand).** 40 sites commented (30 product, 9 oracle,
1 set engine; the TK106/TK108 blocks were written by this session). First-hand check
(`.scratch/tk108/verify_comments.py`): `ast.dump` identical to the pre-sweep files for all
three, 167 + 32 + 3 lines added, every one a `#` line, none removed; `setengine/engine.py`
is AST-identical to HEAD. Every INSTEAD containing DSL was parsed by the agent through BOTH
`zanzibar_utils_v1.parse_schema_ast` and `tests.oracle.parse_schema_ast`, and graph-only
refusals were also compiled (orig REFUSED, alternative compiles). Its per-site log,
transcribed (SUBAGENT-PROBED, not re-run by the session):

```
zanzibar_utils_v1.py::_RelationParser._parse_chain | mixed or/and | OK/OK (mixed.alt1, mixed.alt2)
zanzibar_utils_v1.py::_parse_schema_ast_unchecked | duplicate type block | OK/OK (duptype.alt)
zanzibar_utils_v1.py::_parse_schema_ast_unchecked | empty relation name | OK/OK (emptyname.alt)
zanzibar_utils_v1.py::_parse_schema_ast_unchecked | `.` in declared name | OK/OK (dotdecl.alt)
zanzibar_utils_v1.py::_parse_schema_ast_unchecked | duplicate define | OK/OK (duprel.alt)
zanzibar_utils_v1.py::_validate_ast_references | `.` in referenced name | OK/OK (dotref.alt)
zanzibar_utils_v1.py::_validate_ast_consistency | undeclared [T#P] | OK/OK (dangle_us.alt, dangle_us.alt2)
zanzibar_utils_v1.py::_validate_ast_consistency | undeclared computed ref | OK/OK (dangle_c.alt)
zanzibar_utils_v1.py::_validate_ast_consistency | undeclared tupleset | OK/OK (dangle_ts.alt)
zanzibar_utils_v1.py::_validate_ast_consistency | TTU target on no tupleset type | OK/OK (dangle_tgt.alt)
zanzibar_utils_v1.py::_validate_ast_consistency | reference cycle | OK/OK (cycle.alt_group, cycle.alt_folder)
zanzibar_utils_v1.py::_emit_expr | and/but not under enable_boolean=False | n/a (no DSL); bool.alt parse OK/OK, compile OK default, REFUSED with enabl
zanzibar_utils_v1.py::_validate_ttu_tuplesets | untainted TTU onto derived target NAME | OK/OK; compile: ttuname.orig REFUSED -> ttuname.alt OK (probe
zanzibar_utils_v1.py::_validate_ttu_tuplesets | untainted non-direct tupleset | OK/OK, compile OK (ndts.alt)
zanzibar_utils_v1.py::_reject_doubly_bridged_shapes | doubly-bridged shape | OK/OK; compile: doubly.orig REFUSED -> alt_restr OK, alt_shape OK
zanzibar_utils_v1.py::_reject_object_wildcard_scope | owc shape on derived relation | n/a (no DSL); compile owc_derived.orig REFUSED -> .alt OK
zanzibar_utils_v1.py::_reject_object_wildcard_scope | declared shape names a leaf pred | n/a (no DSL)
zanzibar_utils_v1.py::_reject_object_wildcard_scope | shape expands onto a derived leaf | n/a (no DSL)
zanzibar_utils_v1.py::_reject_object_wildcard_scope | owc shape on derived-TTU tupleset | n/a (no DSL)
zanzibar_utils_v1.py::_reject_object_wildcard_scope | owc shape on derived-TTU target | n/a (no DSL)
zanzibar_utils_v1.py::_reject_object_wildcard_scope | star tupleset over derived target | OK/OK; compile startts.orig REFUSED -> .alt OK
zanzibar_utils_v1.py::_build_plan_tree | wildcard userset over derived relation | OK/OK; compile wus.orig REFUSED -> .alt OK
zanzibar_utils_v1.py::_stratify | derived dependency cycle | OK/OK; compile strat.orig + strat.orig_ttu REFUSED (probed; census REASONED) -> strat.alt
zanzibar_utils_v1.py::parse_openfga_json | schema_version != 1.1 | n/a (JSON); json.this_meta (1.1) OK
zanzibar_utils_v1.py::parse_openfga_json | model-level conditions | OK/OK (cond.alt)
zanzibar_utils_v1.py::parse_openfga_json | duplicate type_definitions entry | n/a (JSON)
zanzibar_utils_v1.py::parse_openfga_json | `.` in declared name | n/a (JSON); json.can_view OK
zanzibar_utils_v1.py::_json_restrictions | conditional restriction | OK/OK (cond.alt)
zanzibar_utils_v1.py::_json_rewrite | `this` without metadata | n/a (JSON); json.this_meta OK, json.this_nometa REFUSED
zanzibar_utils_v1.py::_json_rewrite | unknown rewrite operator | n/a (JSON); json.unknown_op REFUSED as expected
tests/oracle.py::_parse_restrictions | `.` in userset pred (mixed SYNTAX/SHAPE row; `.` part only) | OK/OK (dotref.alt)
tests/oracle.py::_Parser._chain | mixed or/and | OK/OK
tests/oracle.py::parse_schema_ast_unchecked | empty relation name | OK/OK
tests/oracle.py::_validate_consistency | undeclared [T#P] | OK/OK (dangle_us.alt, .alt2)
tests/oracle.py::_validate_consistency | undeclared computed ref | OK/OK (dangle_c.alt)
tests/oracle.py::_validate_consistency | undeclared tupleset | OK/OK (dangle_ts.alt)
tests/oracle.py::_validate_consistency | TTU target on no tupleset type | OK/OK (dangle_tgt.alt)
tests/oracle.py::_validate_consistency | reference cycle | OK/OK (cycle.alt_group, cycle.alt_folder)
tests/oracle.py::parse_schema | boolean op in legacy union-only view | n/a (API, not DSL)
setengine/engine.py::SetEngine.__init__ | doubly-bridged re-raise | n/a (pointer)
```

Corrections the sweep made to the census (SUBAGENT, first-hand by that agent): the
name-collision refusal in `_validate_ttu_tuplesets` IS reachable from a checked parse (probed),
and renaming one boolean relation is not enough when a second tainted relation shares the
name; both `_stratify` examples were probed to raise `CyclicDerivedDependency`. Comments say
"closest legal form" where an alternative is not exact, and the `_stratify` one says outright
that its rewrite is NOT equivalent (per-level exclusion has no legal form).

**Enforcement (`tests/test_refused_shape_comments.py`, MEASURED 2026-09-27).** 9 tests: every
in-scope raise (any `UnsupportedByGraphIndex` / `CyclicDerivedDependency`, any raise in a
`_validate_*` / `_reject_*` function) has a header; every header block has WHY and INSTEAD;
per-file header floors with zero headroom (32 / 11 / 1). Three sabotages each went red on the
rule meant to catch them (literal output in the module docstring). Limit, stated there too:
a plain `ValueError` refusal outside the naming convention is caught only by review.

**Side finding filed as `TK109` (PROBED first-hand):** the oracle parser silently accepts
seven schema shapes the product parser refuses (`[]`, duplicate type, malformed `type` line,
`.` in a declared name, duplicate relation (`TK105`), unrecognised line, `[user,]`).
