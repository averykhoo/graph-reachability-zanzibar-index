# TK151 — user docs (Diataxis) + GitHub Pages: plan, 2026-10-20

ACTIVE-PLAN (`docs/README.md` §3). Owner row: `TK151`. Corrections go at the top, dated.

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
