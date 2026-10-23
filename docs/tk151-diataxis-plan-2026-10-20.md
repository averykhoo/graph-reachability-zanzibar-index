# TK151 — user docs (Diataxis) + GitHub Pages: plan, 2026-10-20

ACTIVE-PLAN (`docs/README.md` §3). Owner row: `TK151`. Corrections go at the top, dated.

## Correction 2026-10-23d — diagrams for the two "how it works" pages (session 2026-10-23c)

User request (2026-10-23): the explanation pages cover the mechanism but need illustrations,
especially the layered settling of derived relations (internal operand relations and
derived edges materialized one layer before the next reads them) and the path-counting
closure. Labels: **READ** / **RAN** / **REASONED** as above.

- **LANDED:** `userdocs/_diagrams/make_diagrams.py` draws 8 figures as plain SVG, each in a
  light and a dark variant (`userdocs/explanation/img/*.svg`, 16 files), shown with furo's
  `only-light` / `only-dark` image classes. No new dependency: no Sphinx diagram extension
  (none installed; `sphinxcontrib-mermaid` would add a package and client-side JS), no
  Graphviz (`dot` is not on this machine or the docs CI). RAN: furo's CSS hides the
  inactive variant (`html body .only-dark{display:none!important}`), and the built
  `graph-index.html` shows one figure per slot.
  * `graph-index.md`: tuples as a graph; the add-edge product grid; the two paths with the
    closure table before/after removing tuple 3; the `user:*` two-probe check; any/all
    nodes and bridges.
  * `boolean-operators.md`: the residue for `[user, user:*] but not banned`; the three
    layers (closure, `viewer`, `commenter`); one write cascading through them. The
    "Layers" prose now says how rounds work (each reads the outbox rows the previous step
    added) and names the internal relations.
- **Numbers are observed, not drawn** (RAN 2026-10-23, probes in `.scratch/diagrams/`,
  results copied into each figure function's docstring): the counting example's closure
  rows `alice->doc:1#viewer` paths=2 (1 after removing `eng viewer doc:1`),
  `eng->doc:1#viewer` 2 -> 1, the rest 1; for `BOOL_SCHEMA`
  `strata == [[('doc','viewer')], [('doc','commenter')]]`, leaves `viewer.0` (storage),
  `viewer.1` (negative), `commenter.0`; writing `user:alice banned doc:1` appended outbox
  rows ADDED `banned`, ADDED `viewer.1`, REMOVED `viewer`, REMOVED `commenter`
  (`DeltaProcessor._run_cascade` reads rows since the previous round's frontier, READ).
- **Pinned:** `tests/test_userdocs_diagrams.py`: committed SVGs equal the
  generator's output; every figure is shown in both themes. Sabotage RAN: a label changed
  in `graph_two_paths` without regenerating -> `stale=['graph-index-paths-dark.svg',
  'graph-index-paths.svg']`; the dark `boolean-cascade` directive deleted -> `figures not
  shown with their theme class: ['boolean-cascade-dark.svg']`; both restored -> 2 passed.
- **Not done (REASONED):** `two-backends.md` (the memoization spectrum) and
  `consistency.md` (log -> set engine -> index) would also profit from a figure; not asked.
  The figures are 840-960 px wide and furo scales them to ~80% in its content column.

## Correction 2026-10-23c — fable round applied

Integrator: workflow unit `r2-integrate` (run `wf-0p1`), after four writer+reviewer units
(`landing`, `dedup-reads`, `errors-ops`, `edges-jargon`) applied the recommendations of
[`tk151-fable-review-2026-10-23.md`](tk151-fable-review-2026-10-23.md) § "Verdict and
ranked recommendations". Labels: **READ** (first-hand read of the page or source),
**RAN** (command run by the integrator), **REPORTED** (a unit's report, not re-checked
here). Nothing committed; the orchestrator runs the gate.

| # | Recommendation | Status | Notes |
| --- | --- | --- | --- |
| 1 | MUST landing first screen | APPLIED | REPORTED+READ: `userdocs/index.md` gains the in-process / two-backends / "use a `Store`, choose sync vs async" paragraph above Install, with the write-heavy exception linked to `limits.md#when-not-to-use-this-library`; extensions link and master-vs-PyPI note gone (the banner in `userdocs/conf.py::_announcement` carries it); License moved to the end. |
| 2 | MUST pre-release prose pinned | APPLIED (guard), prose kept on purpose | RAN: `tests/test_userdocs_prerelease_prose.py` fails at any non-0.0.x `__version__` while `unreleased` / `not yet released` / `reports … 0.0.5` / `is at version 0.0` survives. `how-to/errors.md` added to `KNOWN_CURRENT` by the integrator; sabotage (errors.md's `0.0.5` neutralised) gave `missing pre-release hits: ['how-to/errors.md']`, restored → 3 passed. The prose itself is deleted at the 0.1.0 cut, not now. |
| 3 | MUST one message on Store vs set engine | APPLIED | READ: `how-to/index.md` gloss, `how-to/backends-direct.md` "Prefer the Store" / "Decide whether you need this", `explanation/limits.md` "When not to use" and `index.md` all say: a `Store` for an application, the set engine on its own for tooling, experiments and write-dominated loads. |
| 4 | SHOULD one home per caveat | APPLIED | RAN (grep 2026-10-23), homes carrying the full caveat, review → now: stale-revoke 6 → 2 (`consistency.md` owns, `async-tokens.md` keeps the recipe); `ForeignToken` handling 6 → 1 (`errors.md` label `foreign-token-handling`; `exceptions.md` keeps the class entry; upgrade/changelog keep their migration lines); sync-writer-blocked-by-backlog 5 → 1 (`fanout-cap.md` label `sync-writers-blocked-by-backlog`; errors, limits, stall-recovery now a sentence + link — limits and stall-recovery done by the integrator); paranoia table 4 → 1 (`configuration.md` label `paranoia-levels`); marker shapes 4 → 1 (`reference/api/index.md` label `api-result-markers`); first-write-slow 4 → 2 (`fanout-cap.md` how-to section + `limits.md` measurements; upgrade links, changelog copy gone). |
| 5 | SHOULD cut errors.md to buckets | APPLIED | REPORTED: four buckets with 2-3 exceptions each linking `reference/exceptions.md`; `CascadeNotRun` / `MissingDeltaProcessor` / `IndexExists` moved to `backends-direct.md` "Errors only the backends raise" (with the correction that `Store.adopt` re-raises `IndexExists`, `src/zanzibar/store/_store.py::Store.adopt`). |
| 6 | SHOULD promote "a committed grant stays committed" | APPLIED | REPORTED: `{note}` in `tutorials/first-check.md` "Create a store"; bullet in `how-to/postgresql.md` "One session per thread"; both link `two-backends.md#who-owns-the-transaction`. |
| 7 | SHOULD jargon pass | PARTIAL | Done: tupleset defined at first use in `rewrite-refused-shape.md` and `port-openfga.md`; "closure fan-out cap" → "write fan-out cap" in user prose and headings (integrator: `limits.md` heading, `stall-recovery.md`, `async-tokens.md`; the exception message asserted in `fanout-cap.md` keeps its literal text); prune-outbox Note cut. NOT done: the `StaleRead` message in `src/zanzibar/store/source.py` still says "evaluator", so `errors.md` keeps a one-line gloss instead of the apology — a source change, out of a docs round. |
| 8 | NICE runtime-checks after-commit failure | NOT DONE | READ: `how-to/runtime-checks.md` "When a check fails" still documents the `InvalidRequestError` / unusable-Store behaviour at length. Not assigned this round; the right fix is in the code, before 0.1.0, or a one-sentence "known limitation" with a row. |
| 9 | NICE query-access back half | APPLIED | REPORTED: object-side "all" marker → `wildcard-extensions.md`; `covers()` helper → `reference/api/index.md` "Testing whether a subject is covered"; page 17.6 KB → 14.5 KB. |
| 10 | NICE upgrade step 8 → changelog link | APPLIED | REPORTED: one paragraph naming the additions plus links to the changelog, `query-access.md` and `bulk-load-adopt.md`. |

**Tests (RAN, 2026-10-23):** `tests/test_userdocs_examples.py`, `test_userdocs_build.py`
(strict `-W -n`), `test_userdocs_refused_shapes.py`, `test_userdocs_prerelease_prose.py`,
`test_tk122_release_metadata.py`, `test_tk123_pypi_page.py`: rc=0, all passed.

**Size (RAN, 2026-10-23):** the review's 437 KB reproduces as
`du -sb --exclude=_inventories --exclude=_ext userdocs` (pages plus `conf.py`); after this
round it is 436,297 bytes. The net is about flat, not the 60-80 KB the review predicted:
every cut fact had to keep a home, so the cuts in how-tos (errors.md, query-access.md,
upgrade step 8, prune-outbox) reappear in reference (`exceptions.md`, `api/index.md`,
`backends-direct.md`'s errors section, `fanout-cap.md`'s backlog section). The win is
one home per caveat, not bytes. The exact pre-round byte count was not saved (UNVERIFIED).

**Remains for TK151 before the cut (REASONED):**
- Recommendation 8 (runtime-checks after-commit failure) and the `StaleRead` "evaluator"
  wording (recommendation 7): both are code changes, to decide before 0.1.0.
- The `viewer_base` rewrite still has 5 homes (patterns, rewrite-refused-shape,
  boolean-operators, semantics-vs-openfga, schema-language); the review did not rank it, so
  it was not touched.
- At the cut: delete or date every hit of `tests/test_userdocs_prerelease_prose.py`
  (`limits.md`, `errors.md`, `upgrade-0.1.md`, `changelog.md`, `environments.md`,
  `tables.md`); the test goes red until they are gone.
- The full gate (`formal/verify.sh` phases) on this tree, then the commit.

## Correction 2026-10-23b — round result

Integrator: workflow unit `docs-integrate` (run `wf-0p1`), after the TK164 / TK166 code
stages and the three docs units (`fanout-refusal-cost`, `cascade-not-run-followthrough`,
`pypi-readme-shrink`). Labels as in the audit below: **READ** / **RAN** / **REASONED**.
Nothing committed; the orchestrator runs the gate.

**LANDED this round (uncommitted):**
- TK166 in the docs (READ, edited): `reference/exceptions.md` (tree: `ForeignToken` under
  `StaleRead`; table row; `py:exception:: zanzibar.ForeignToken` with `token` / `issued_by`
  / `store_id`; the foreign-token caveats on `StaleRead` / `LookupNotFresh` removed),
  `how-to/errors.md` (`ForeignToken` bullet plus an executed example; old workaround text
  removed), `how-to/async-tokens.md` (the `{warning}` replaced; the retry helper re-raises
  `ForeignToken`; the example catches `ForeignToken`), `explanation/consistency.md` (both
  passages), `how-to/query-access.md` ("all four"), `reference/api/store.md`,
  `how-to/upgrade-0.1.md` section 4.
- TK164 in the docs (READ, edited): `reference/exceptions.md` (every subclass has a builtin
  base; exceptions' one home is `zanzibar`; `UnsupportedByGraphIndex [ValueError]`;
  `SchemaError` / `UnsupportedByGraphIndex` entries), `how-to/errors.md`,
  `how-to/rewrite-refused-shape.md` ("every refusal is also a `ValueError`"),
  `how-to/upgrade-0.1.md` (section 1: import exceptions from `zanzibar`, with an executed
  check; section 4: the `ValueError` gain; section 8: `open_set_engine` and the four schema
  types), `reference/api/index.md`, the four API pages' "Exceptions re-exported here"
  sections replaced by a one-rule "Exceptions" section, `reference/api/schema.md`
  (`py:class` entries for `Entity`, `RelationalTriple`, `SchemaInfo`, `CompiledBooleans`;
  `RuleSet.schema_info` / `.compiled` typed), `reference/api/graphindex.md` (the "types
  that are not public" caveat removed), `reference/api/store.md` (`open_set_engine` entry),
  `userdocs/conf.py` (`nitpick_ignore` no longer lists `SchemaInfo` / `CompiledBooleans`;
  the build resolves them, RAN). `how-to/backends-direct.md` needed no change (READ: it names
  no newly public type).
- Audit reserved-page items (a) and (b): `reference/changelog.md` 0.1.0 section refreshed
  from `CHANGELOG.md` `[Unreleased]` (Ellipsis refusal, exceptions' one home, `ValueError`
  gain, `ForeignToken`, `SetEngine` `PersistedSchemaRefused`, lookup_reverse filters,
  `implicit_keys`, `DeltaProcessor` / `open_set_engine` / schema types, the fan-out and
  cascade fixes; heading still "0.1.0 (unreleased)"); `how-to/errors.md` has a
  `CascadeNotRun` bullet.
- `CHANGELOG.md` `[Unreleased]` (READ, edited): two claims contradicted TK164 and were
  fixed: the Added bullet "`zanzibar.store` re-exports the exceptions a `Store` raises ...;
  `zanzibar.graphindex` exports `WriteLockUnsafe`" and the Fixed bullet "`CascadeNotRun`
  (exported from `zanzibar` and `zanzibar.graphindex`)". RAN: neither name is in
  `zanzibar.graphindex.__all__`, and `zanzibar.store.__all__` lists no exception.
- From the docs units (their reports, not re-read here except where the tests cover them):
  `how-to/fanout-cap.md` first-write section (audit TK158 item), `how-to/upgrade-0.1.md`
  section 7 `CascadeNotRun` (TK3 item), `reference/api/graphindex.md` `run_cascade`, and
  phase 6: `PYPI_README.md` is now pitch / install / executed quickstart / links / license
  (READ: 98 lines, headings `Install`, `Quickstart`, `Documentation`, `License`), with
  `tests/test_tk123_pypi_page.py` now reading the hierarchy from `reference/exceptions.md`.
- Tests (RAN, 2026-10-23): `tests/test_userdocs_examples.py tests/test_userdocs_build.py
  tests/test_userdocs_refused_shapes.py tests/test_tk122_release_metadata.py
  tests/test_tk166_foreign_token.py tests/test_tk164_public_surface.py
  tests/test_tk123_pypi_page.py`: rc=0, `117 passed in 61.07s`. The build test is
  `sphinx -W -n --keep-going -E`.

**STILL OPEN for TK151 (excluding the cut and TK162):**
- The `fable` review of the whole site (user, 2026-10-23). Not started; file it as a TK151
  subtask (REASONED: what is left of TK151 is otherwise small).
- A second fresh-reader pass (phase 7) over the pages changed since round 2 is optional;
  REASONED: the executed examples cover the changed code, but no reader has followed the
  rewritten async-tokens / errors / upgrade pages end to end.
- Outside TK151 but owed before the cut: `benchmarks/fanout_cost_bench.py` ~L72 still
  imports `ClosureFanoutExceeded` from `zanzibar.schema` (TK164 residual; `benchmarks/` is
  the TK162 session's), and `formal/FINAL_REVIEW.md`'s counts block must be regenerated
  for the new TK164 / TK166 tests (gate stage).
- Estimate (REASONED): about 95% of TK151 excluding the cut and TK162; the fable review
  is the one substantive item left.

**BLOCKED ON TK162 (READ in the audit below, unchanged):** `explanation/limits.md`
"Lookups for a userset: a cost that has not been measured" (~L183-205) and the set-engine
read cost (~L252); whether `how-to/query-access.md` needs a performance warning.

**For the cut (unchanged, READ in the audit below):** `explanation/limits.md` ~L267,
`reference/environments.md` ~L23, `reference/tables.md` ~L93, the `userdocs/conf.py`
announcement (~L57), the changelog heading "0.1.0 (unreleased)".

## Correction 2026-10-23 — remaining-work audit

Auditor: workflow unit `tk151-audit` (read-only on `userdocs/` and `src/`), tree at `27f6af5`
plus whatever other live sessions had uncommitted. Labels: **READ** = read first-hand by the
auditor in the cited file; **REASONED** = inferred from READ facts; **UNVERIFIED** = not
checked. Line numbers are as of 2026-10-23. Scope excludes TK164/TK166 doc edits, TK162
(perf) and the 0.1.0 version cut itself.

Round 2 (`wf_b32b8743-b9f`, committed in `707259e`) was never written up here. Its record is
`docs/tk151-repros-2026-10-20/README.md` (B1-B10 repro verdicts; B1->TK163, B2/B10->TK164,
B3->TK165, B4/B5->TK166, B6->TK167, B7/B8->TK168, each READ from the row files; B11->TK169
by its title, REASONED, since the row does not cite B11; B9 is TK3, closed) and the
session-log entry that mentions the fresh-reader trial (`docs/history/session-log.md`).

**Critic items 1-7 (2026-10-20b list above):**
1. FIXED (READ): `userdocs/_ext/refused_shapes.py` now renders REFUSED SHAPE blocks from
   `schema/parser.py`, `json_frontend.py`, `compiler.py`, `boolean.py`, `setengine/engine.py`,
   `store/_store.py`, `graphindex/wildcard.py` (the per-file tables in that module).
2. FIXED (READ): `how-to/errors.md` L107-113 and the executed example at L147-170 say a
   `but not` recursion through the kept side raises `CyclicDerivedDependency`, which is not a
   `SchemaError`; `reference/exceptions.md` L85 agrees. Matches
   `src/zanzibar/schema/errors.py::CyclicDerivedDependency` (`ZanzibarError, ValueError`).
3. FIXED (READ): `how-to/runtime-checks.md` holds no cost figures; it links
   `explanation/limits.md#runtime-checks-add-to-the-write-cost` (dated table L71-76).
4. FIXED (READ): `how-to/backends-direct.md` keeps the SetEngine half and cuts the graph
   half to a warning that describes `CascadeNotRun` and its bound; the wording matches
   `src/zanzibar/graphindex/cascade_mark.py::CascadeNotRun` and the module docstring.
5. FIXED (READ): `reference/api/store.md` L44-77 documents `DEFAULT_PARANOIA`, `store_id`,
   `session`, `sync`, `paranoia` and names the internal attributes.
6. MOSTLY FIXED (READ): every listed fact has a home (`index.md`: alpha / no performance
   target / Apache-2.0; `reference/api/index.md`: underscore names are internal;
   `explanation/two-backends.md` L104: a committed grant stays committed; `how-to/prune-outbox.md`
   L83: the paranoia warning). `open_set_engine` is no longer named on any page.
   **STILL OPEN:** phase 6 is half done. `PYPI_README.md` still carries "Async mode in brief",
   the outbox-pruning recipe and a 21-row exception table that already lags the code (no
   `CascadeNotRun`, `UnsupportedByGraphIndex`, `DoublyBridgedShapeError`) and that TK164/TK166
   will change again. `tests/test_tk123_pypi_page.py::test_every_import_on_the_page_resolves`
   requires at least 5 imports on the page, and `test_every_store_attribute_the_page_names_exists`
   requires `catch_up`, `lag`, `refresh`, `watermark`, `index_stalled` and `stall_error` to be
   named. So shrinking the page means editing that test, which is a deliberate floor change.
7. MOSTLY FIXED (READ): `how-to/stall-recovery.md` has no "What a stall is" section;
   `how-to/index.md` is regrouped into four even groups; `how-to/runtime-checks.md` keeps only
   a short "use it for" table, which is fine. REASONED: `how-to/fanout-cap.md` "What the cap
   applies to" (L95-156) is task-framed, with an executed example, so it is acceptable;
   `explanation/semantics-vs-openfga.md` ends in a summary table (L413), which is acceptable
   for an explanation page.

**Stale or missing after TK158 / TK3 (READ):**
- `how-to/fanout-cap.md` L177-183 ("Expect a refusal of a very large write to be slow ...
  take a long time and a lot of memory ... split such groups rather than relying on the cap
  to refuse grants to them quickly") contradicts `explanation/limits.md` L163-181 (TK158,
  measured 2026-10-22: 0.15-0.20 s and no memory growth on an already-written store; only
  the first write after opening is slow, 15.8 s, because of the cycle-check graph build).
- `how-to/upgrade-0.1.md` §7 (L331-346) does not say that 0.0.x code driving a bare
  `WildcardIndex` on an `and` / `but not` schema now gets `CascadeNotRun` at commit (TK3;
  CHANGELOG `[Unreleased]` Fixed).
- `reference/api/graphindex.md` L156-161 (`run_cascade`) does not say that the commit is
  refused with `CascadeNotRun` if it is skipped.
- Reserved page `how-to/errors.md`: no `CascadeNotRun` entry (the exceptions reference has one).

**Spot checks that held (READ):** paranoia levels, the boolean words, precedence and the
`bad paranoia level` message (`src/zanzibar/graphindex/invariants.py::normalize_paranoia_level`,
`::resolve_paranoia_level`) match `reference/configuration.md` and `how-to/runtime-checks.md`;
the default is off (`src/zanzibar/store/_store.py::Store.DEFAULT_PARANOIA`). The fan-out
default of 100,000 and the env name (`src/zanzibar/graphindex/core.py::DEFAULT_MAX_CLOSURE_FANOUT`,
`::MAX_CLOSURE_FANOUT_ENV`) and the "this write would add N" message match `how-to/fanout-cap.md`.
The B1 post-commit behaviour described in `runtime-checks.md` / `configuration.md` is the one
`docs/tk151-repros-2026-10-20/README.md` § B1 reproduced (TK163 still open).

**Contents (target): every entry has a page (READ):** 2 tutorials; 15 how-tos (the 14 targets
plus `prune-outbox`); the full reference list; 9 explanation pages. Tutorials and explanation
pages spot-read for Diataxis drift: none found beyond item 7.

**Changelog (READ):** `userdocs/reference/changelog.md` "0.1.0 (unreleased)" lacks TK158 (cheap
fan-out refusal) and TK3 (`CascadeNotRun`) from CHANGELOG `[Unreleased]` Fixed, and in Added:
public `DeltaProcessor` (TK153), `LookupResult.implicit_keys` (TK144), the
`subject_type` / `subject_predicate` lookup filters (TK156), and the `Ellipsis` subject-predicate
refusal. It needs a refresh after TK164/TK166 land and before the cut (reserved for that stage).

**Blocked on TK162 (READ):** `explanation/limits.md` L183-205 "Lookups for a userset: a cost
that has not been measured" and L252 (set-engine read cost). Whether `how-to/query-access.md`
needs a performance note is TK162's decision.

**For the cut, not now (READ):** text that says 0.1.0 is unreleased, which the version cut
must flip: `explanation/limits.md` L267 ("at version 0.0.x"), `reference/environments.md` L23,
`reference/tables.md` L93, the `userdocs/conf.py` announcement (L57), the changelog heading.

**Not yet done (REASONED):** a `fable` review of the docs as a whole (user, 2026-10-23), the
phase 6 PYPI_README shrink, and a write-up of round 2 here. Baseline:
`tests/test_userdocs_build.py tests/test_userdocs_examples.py` rc=0, `38 passed in 405.91s`
(READ, 2026-10-23; slow because other sessions were running at the same time).

**Remaining fixable work, split into units with no page in common (REASONED):**
(a) `how-to/fanout-cap.md`: bring L177-183 in line with limits.md.
(b) `how-to/upgrade-0.1.md` and `reference/api/graphindex.md`: add the TK3 `CascadeNotRun` follow-through.
(c) `PYPI_README.md` and `tests/test_tk123_pypi_page.py`: finish phase 6. This must be
ordered after the TK164/TK166 edits to `PYPI_README.md`.
Reserved pages (`reference/changelog.md`, `how-to/errors.md`) go to the TK164/TK166
integration stage. A `fable` review of the whole site should be a separate subtask.

## Correction 2026-10-20b — first draft landed (workflow `wf_e60a3842-f17`)

LANDED (uncommitted at time of writing): 43 pages under `userdocs/`, `userdocs/conf.py`
(+ `_ext/refused_shapes.py`, offline intersphinx inventories in `userdocs/_inventories/`),
`tests/test_userdocs_examples.py`, `tests/test_userdocs_build.py`, `.github/workflows/docs.yml`,
`docs` extra in `pyproject.toml`, docs deps in `requirements.txt`, `userdocs/_build/` ignored.
Integrator, 2026-10-20 (agent report, UNVERIFIED first-hand): strict build rc=0 with no warnings;
`pytest tests/test_userdocs_examples.py tests/test_userdocs_build.py` 36 passed. Scaffold sabotage
(agent report): a wrong `# -> False` ran red, a dead `{py:class}` link ran red, an un-toctreed page
ran red; output literal in the two test modules' docstrings.

**Completeness critic findings still OPEN** (agent report, UNVERIFIED first-hand):
1. `reference/refused-shapes.md` is generated from `schema/parser.py` only
   (`userdocs/_ext/refused_shapes.py::DEFAULT_SOURCE`); REFUSED SHAPE blocks in `schema/compiler.py`,
   `schema/json_frontend.py`, `schema/boolean.py`, `setengine/engine.py`, `store/_store.py`,
   `graphindex/wildcard.py` are not rendered, so the wildcard-extension refusals have no page.
2. FALSE on `how-to/errors.md`: "any recursion through `but not` is a SchemaError". A cycle through
   `but not` raises `CyclicDerivedDependency` (not a `SchemaError` subclass) from both
   `parse_openfga_schema` and `Store`. `reference/exceptions.md` row says only "A Store refuses it".
3. Numbers disagree: `runtime-checks.md` vs `limits.md` on the `residue` / `full` costs.
4. `how-to/backends-direct.md` graph half needs non-public names (`Entity`, `RelationalTriple`,
   `ruleset.schema_info`, `widx.idx`) and claims, untested, that nothing detects a skipped cascade.
   Waits on TK3 anyway: cut to a warning + link, keep the SetEngine half.
5. `Store` public attributes undocumented (`store_id` is used by a tutorial).
6. PYPI_README content with no home: "no performance target", Apache-2.0, underscore names are
   internal, "a committed grant stays committed if your code later rolls back", outbox pruning recipe
   and its paranoia warning. `zanzibar.store.open_set_engine` is recommended by PYPI_README but is not
   in `zanzibar.store.__all__`.
7. Diataxis slips: cost table in `how-to/runtime-checks.md`, formula repeated in `how-to/fanout-cap.md`,
   "What a stall is" in `how-to/stall-recovery.md`, a reference list in
   `explanation/semantics-vs-openfga.md`; `how-to/index.md` grouping lopsided.

**Suspected library bugs reported by the unit agents** (UNVERIFIED first-hand; each needs a repro
before it becomes a row):
- B1 A post-commit `InvariantViolation` (paranoia `full`/`fixpoint`) reaches the caller as
  `sqlalchemy.exc.InvalidRequestError` (`InvariantViolation` as `__context__`); the write is stored
  and the `Store` is unusable afterwards (probe `.scratch/tk151-docs/probes-howto-ops/p3.out`).
- B2 `DoublyBridgedShapeError` and `UnsupportedByGraphIndex` are not `ValueError`s, unlike the other
  schema refusals.
- B3 A stall recorded while nothing was pending is never cleared by a `catch_up()` that applies
  nothing, contradicting the `IndexStalled` docstring.
- B4 A freshness token from another store is accepted silently when at or below this store's cursor.
- B5 The `StaleRead` message for another store's token still opens with "refresh and retry".
- B6 A row the index can never apply blocks every `sync=True` `add_tuple` on that store id.
- B7 `is_valid_identifier("...")` is True, so `type ...` parses and `[user#...]` reads as `[user]`.
- B8 `parse_user("user:a#b:c")` does not raise; `Store.lookup("group:g#...")` returns empty where
  `check` refuses the same subject.
- B9 A bare `WildcardIndex` on a `but not` schema with no `run_cascade` commits wrong answers
  silently (this is TK3).
- B10 Exception re-exports from `zanzibar.setengine` / `zanzibar.graphindex` are inconsistent;
  `Entity`, `RelationalTriple`, `SchemaInfo` are needed by public APIs but not public.
- B11 Docstring hygiene: public docstrings name internal ids / private paths or are missing
  (`help()` shows them); `ClosureFanoutExceeded` points at an argument a Store user cannot reach; a
  negative `ZANZIBAR_MAX_CLOSURE_FANOUT` message names the constructor argument; paranoia comments
  quote old costs and say "Default ON" (default is off); PYPI_README says the `StaleRead` message
  says "never issued" (it does not).

## Decisions (2026-10-20, in chat with the user unless marked)

- **Reader: a Python developer adding permissions to an app** (user). Lean readers use the
  repo; the site gets one honest "how correctness is checked" explanation page, no more.
- **Hosting: GitHub Pages**, built and deployed by a workflow (user approved the workflow and
  the publish, 2026-10-20; recorded on TK151's 2026-10-20 Log entry).
- **Generator: Sphinx + MyST-Parser (Markdown pages) + Furo theme + autodoc** (model decision,
  reasoning below).
- **Location: `userdocs/`**, not `docs/`. `docs/` is the internal development record and stays
  that way.
- **Async / freshness tokens: how-to + explanation, no tutorial** (model decision on the user's
  rule "if usage is stable, both types; if it will change, one type"). REASONED: the surface
  (`sync=False`, tokens from writes, `at_least=`, `catch_up`, stall recovery) has been
  described in `PYPI_README.md` since before TK123 and TK123 only renamed it; nothing open
  (TK3/TK158/TK162) changes how a caller uses it. Its sharp edges (an untokened read can
  still ALLOW a revoked grant) need the explanation page; it is too advanced for a tutorial.

### Why Sphinx (model decision, 2026-10-20)

Requirements: Python API reference generated from the docstrings (so it cannot drift), Markdown
authoring (the whole repo is Markdown), a build that FAILS on a broken reference (the repo's
"prefer a mechanical refusal" rule), a toolchain that will still work in two years, Pages via
Actions.

| option | for | against |
|---|---|---|
| **Sphinx + MyST + Furo** | The reference tool for Python libraries; autodoc reads the docstrings, which are already reST-flavoured (``` ``x`` ``` literals); `-W -n` (nitpicky) turns a broken cross-reference into a build failure; intersphinx links to Python/SQLAlchemy docs; stable governance, no ecosystem split | More configuration than MkDocs; autodoc imports the package (fine: pure Python, deps install in CI); MyST directive syntax is a small learning cost |
| MkDocs + Material + mkdocstrings | Nicest default look; simple config; good Markdown | **Ecosystem in flux as of 2026-10** (web search, UNVERIFIED secondary sources): Material in maintenance mode since 2025-11-05; MkDocs 1.x frozen at 1.6.1 (2024-08); MkDocs 2.0 pre-release drops the plugin system, so mkdocstrings would not run on it; successor Zensical is alpha (0.0.6x) with a subset of plugins. Choosing it now means a forced migration soon |
| Jekyll (as in the sibling `recipes` repo) | Native to Pages; already familiar | No Python API generation; Ruby toolchain beside a Python project; nothing to fail a build on a broken symbol |
| Hugo | Fast single binary | No Python API generation; Go templates |
| Docusaurus | Polished, versioning built in | Node toolchain; no Python API generation |
| pdoc | Zero-config API pages | API reference only; no place for tutorials/how-to/explanation |

## Contents (target)

**Tutorials** — run start to finish by a test
1. Your first permission check (SQLite, sync): install, schema, tuples, `check`, `lookup`.
2. Model a Drive-style app: folders, docs, groups, parent inheritance, public `*`, `but not`
   ban list.

**How-to guides**
- Port an OpenFGA model; rewrite a refused shape.
- Patterns: groups, parent inheritance, public access, block lists, `and`.
- Who can access X / what can Y access (`lookup`, `lookup_reverse`, filters, markers);
  `Store.expand`.
- Run on PostgreSQL (READ COMMITTED, session per thread, multiple instances).
- Use async mode and freshness tokens; recover a stalled index.
- Bulk-load / adopt an existing store (`build_index`, `Store.adopt`).
- Change a schema (schemas are static: a new store).
- Cap write fan-out, handle `ClosureFanoutExceeded` — waits on TK158.
- Runtime checks in production (`paranoia="residue"`).
- Handle errors (`ZanzibarError` hierarchy).
- Upgrade from 0.0.x to 0.1.0 (TK123 renames; TK144 ALLOW -> DENY). Required.
- Use the backends directly (`SetEngine`, `WildcardIndex`) — waits on TK3.

**Reference**
- Python API (autodoc): `Store`, `LookupResult`, `ExpandResult`, `parse_openfga_schema`, each
  subpackage's `__all__`.
- Schema language (accepted OpenFGA subset; not `with` conditions, not modules).
- Refused schema shapes — generated from the `REFUSED SHAPE / WHY / INSTEAD` blocks.
- Exceptions; tuple strings and identifiers; configuration (env vars, `Store` kwargs);
  database tables; supported environments; changelog.

**Explanation**
- Zanzibar / ReBAC in brief.
- The two backends (precomputed graph index vs computed-on-read set engine).
- How the graph index works; how `and` / `but not` work in it.
- Consistency: tuple log, tokens, sync vs async, stalls.
- Semantics and differences from OpenFGA (source: `docs/openfga-claims-audit-2026-10-13.md`).
- Wildcard extensions beyond OpenFGA and their warning.
- How correctness is checked, and what is not proven.
- Limits and costs — waits on TK162.

## Phases

0. Settle the marker shape (`ExpandResult.markers` pairs vs `LookupResult.markers` triples;
   model's call per TK151 2026-10-20).
1. Scaffold `userdocs/` + `conf.py`; Pages workflow; a test (inside the gate) that executes
   every code block on the site; `sphinx-build -W -n` in CI.
2. Reference. 3. Tutorials. 4. How-to. 5. Explanation.
6. Shrink `PYPI_README.md` to pitch + executed quickstart + link; `README.md` stays the
   contributor readme.
7. Fresh-reader trial: a subagent follows the tutorials verbatim from the site only.
