# TK164 -- one public exception and type surface before 0.1.0 (2026-10-23)

> **ACTIVE-PLAN** (`docs/README.md` sec 3): the working record for `TK164`. Corrections are
> appended dated at the top, never edited into the body; FROZEN when `TK164` closes.

Row: `python scripts/task.py show TK164`. Source: `docs/tk151-repros-2026-10-20/README.md`
sections B2 and B10 (repros `B2.py`, `B10.py`). Agent `tk164-impl` (workflow minion, run
`wf-0p1`), 2026-10-23. Provenance labels: **READ** = read first-hand by this agent in the
live tree; **RAN** = observed output of a command this agent ran; **REASONED** = inference.
Line numbers are as of 2026-10-23.

## Corrections

- **2026-10-23 (review, agent `tk164-review`):** the census line "None in ...
  `benchmarks/`, `scripts/` ..." was wrong (READ, grep): `scripts/installed_smoke.py`
  ~L346-347 imported `SchemaMismatch` / `AdmissionRejected` from subpackages as a "public
  name exists" check (fixed), and `benchmarks/fanout_cost_bench.py` ~L72 imports
  `ClosureFanoutExceeded` from `zanzibar.schema` (still resolves; left, `benchmarks/` is
  another session's). See "Review 2026-10-23" at the end.

## 1. What was wrong (READ, RAN)

- **B2.** `src/zanzibar/schema/errors.py::UnsupportedByGraphIndex` derived from
  `ZanzibarError` only, so it and its subclass `DoublyBridgedShapeError` were the only two
  package exceptions with no builtin base. `except ValueError` around
  `parse_openfga_schema` / `Store(...)` / `compile_ruleset` let them escape (B2.py output,
  re-observed by the new test's S1 sabotage below). `SchemaError`'s docstring claimed it
  covers "every refused schema shape", which `DoublyBridgedShapeError` contradicted.
- **B10.** Each subpackage `__all__` listed its own subset of exceptions with no rule;
  `Entity`, `RelationalTriple`, `SchemaInfo`, `CompiledBooleans` appear in public signatures
  (`RuleSet` fields, `RuleSet.apply`, `compile_ruleset`, `WildcardIndex.__init__`,
  `DeltaProcessor.__init__`) without being in any `__all__`; and
  `typing.get_type_hints(RuleSet)` raised `NameError: name 'CompiledBooleans' is not
  defined` (RAN, B10.py).

## 2. Scouting (READ unless marked)

- **Who catches `ValueError` in `src/` and could now swallow a compile refusal?**
  `graphindex/core.py` ~L111 (an `int()` of an env var), `graphindex/processor.py` ~L633
  (`widx.add_tuple` / `remove_tuple`), `schema/json_frontend.py` ~L257 (wraps
  `parse_schema_ast` only), `store/apply.py::_apply_row` ~L107 (wraps `ruleset.apply`).
  None reaches `compile_ruleset`, so none can see an `UnsupportedByGraphIndex`. Every
  `except Exception` site already caught it. Verdict: no handler changes behaviour.
- **`tests/parity.py`** (`ParityEngine.__init__`) catches
  `(UnsupportedByGraphIndex, CyclicDerivedDependency)` by name, so a bare `ValueError` from
  compile still surfaces, unchanged. `src/zanzibar/setengine/engine.py::SetEngine.__init__`
  catches `DoublyBridgedShapeError` (re-raise) BEFORE `(UnsupportedByGraphIndex,
  CyclicDerivedDependency)`; order unaffected.
- **Tests that relied on the old base.** `tests/test_tk123_top_level.py::_BUILTIN_BASE`
  pinned `Exception` (now `ValueError`); `tests/test_hypothesis.py` ~L2274 had a comment
  saying it is not a `ValueError` (comment updated, handler unchanged). No test asserted
  `not isinstance(e, ValueError)` for these classes (grep of `tests/`).
- **Census of exception imports from subpackages** (RAN, probe
  `.scratch/wf-0p1/tk164-impl/census.py`, regex over `tests/ src/ benchmarks/ scripts/
  formal/conformance/ userdocs/ README.md PYPI_README.md`): about 130 import sites, all in
  `tests/` plus 4 in `src/` (`setengine/engine.py`, `store/apply.py`, `store/_store.py`
  importing from `zanzibar.schema`). **None in `userdocs/`, `README.md`, `PYPI_README.md`,
  `benchmarks/`, `scripts/` or `formal/conformance/`.** Largest: `zanzibar.schema`
  `AdmissionRejected` (34 sites), `UnsupportedByGraphIndex` (19).
- **Tests that pinned exceptions IN a subpackage `__all__`:**
  `test_tk123_top_level.py::_EXPECTED_ALL`, `test_tk123_equivalence_refusals.py::
  test_a16_missing_proc_is_a_value_error_exported_from_connectedstore`,
  `test_tk153_install_trial_ergonomics.py::test_the_class_is_one_object_everywhere`,
  `test_tk154_stale_lookup_ids.py::test_stale_lookup_ids_and_tables_outdated_are_exported`,
  `test_tk166_foreign_token.py::test_foreign_token_is_exported_like_staleread`. All five
  now pin the new rule (in `zanzibar.__all__`, NOT in the subpackage `__all__`, same class
  by attribute).
- **The docs build already treats `zanzibar` as the home**:
  `userdocs/_ext/refused_shapes.py::_EXCEPTION_HOMES = ["zanzibar"]`. The API pages use
  explicit `autoclass` / `py:class` targets, not `automodule :members:`, so changing
  `__all__` adds or removes nothing on them by itself (RAN: `tests/test_userdocs_build.py`
  green after the change).
- **`open_set_engine`.** Dropped from `zanzibar.store.__all__` by TK123 item 5 as a helper,
  but `setengine/engine.py::_assert_schema_matches_record` puts
  `zanzibar.store.open_set_engine(session, <id>)` in BOTH of its `SchemaMismatch` messages
  as the remedy, and `CHANGELOG.md` 0.0.x entries recommended it. `PYPI_README.md` and
  `userdocs/` no longer mention it (grep).

## 3. Decisions

- **D1 -- `UnsupportedByGraphIndex(ZanzibarError, ValueError)`** (B2 option A). Additive:
  `except UnsupportedByGraphIndex` / `except ZanzibarError` still match, and section 2
  shows no handler in `src/` or `tests/parity.py` changes behaviour. Every schema refusal,
  parse or compile, is now a `ValueError`. It stays NOT a `SchemaError` (the text parsed;
  the graph compile refused it), and `SchemaError`'s docstring now says "every shape the
  PARSER refuses" and names `UnsupportedByGraphIndex` for compile refusals. Rejected:
  option B (narrow the docstring, keep the hole), because a user-facing `except ValueError`
  around schema loading should not leak one family.
- **D2 -- the export rule: no subpackage `__all__` lists an exception or warning; their
  one public home is `zanzibar`.** Chosen over "each subpackage re-exports everything it
  raises" because that rule cannot be kept honest (what a subpackage "raises" changes with
  every refactor, which is how the ragged subsets arose) and because the user docs already
  say "import exceptions from `zanzibar`". `UnprovenExtensionWarning` is included (a
  warning is a `BaseException` subclass and has the same home).
  **The import lines stay**, following the TK123 item 5 precedent (`__all__` IS the API;
  dropped names still import by name, pinned by
  `tests/test_tk123_top_level.py::test_subpackage_all_is_the_real_surface`, which now also
  checks each dropped exception is the same object as `zanzibar.<Name>`). REASONED: a hard
  removal would turn ~130 test imports into edits in a tree shared with live sessions, and
  break 0.0.5 callers loudly for no correctness gain; a name outside `__all__` can still be
  removed later without a semver break. The CHANGELOG says those imports are no longer API.
- **D3 -- `SchemaInfo`, `Entity`, `RelationalTriple`, `CompiledBooleans` join
  `zanzibar.schema.__all__`, each with its own docstring** (a dataclass without one gets its
  generated signature as `__doc__`, which the new test rejects). `CompiledBooleans` is
  public as an **OPAQUE** type: its docstring says to pass it through and that its fields
  are compiler internals. REASONED: it is the declared type of `RuleSet.compiled` and of
  `DeltaProcessor(widx, compiled)`, a public constructor callers drive by hand
  (`docs`: backends-direct); keeping it private would leave a public signature naming an
  undocumented type, and the alternative (an opaque `object` annotation) loses the type
  for checkers. `Rule`, `Filter` (in `RuleSet.rules_and_filters`), `DeclaredRelations` and
  `IndexCursor` stay internal: out of TK164's named scope; their `nitpick_ignore` entries in
  `userdocs/conf.py` remain. Not changed: `WildcardIndex(idx, schema_info)` and
  `RuleSet.apply(RelationalTriple)` keep their signatures (B10 option "make the types
  public", not "take them out of signatures"), which also leaves TK3's bare `WildcardIndex`
  surface alone.
- **D4 -- `RuleSet.compiled`'s string annotation resolves.** A `TYPE_CHECKING` import (the
  B10 suggestion) is NOT enough: `typing.get_type_hints` evaluates the string in the
  module's globals at runtime, where a `TYPE_CHECKING` name does not exist. Instead
  `src/zanzibar/schema/rules.py` ends with `from .boolean import CompiledBooleans`, a
  deliberate bottom-of-module circular import (`boolean` imports from `rules` at its top).
  It is safe in every order because the package `__init__` imports `rules` before
  `boolean`, and importing any submodule runs the package `__init__` first; pinned by a
  fresh interpreter per first-import order (`zanzibar.schema.boolean`,
  `zanzibar.schema.rules`, `zanzibar.graphindex.processor`, `zanzibar`) (RAN).
- **D5 -- `zanzibar.store.open_set_engine` is public** (in `__all__`, docstring rewritten:
  what it opens, `StoreNotFound` / `PersistedSchemaRefused`, the `ruleset` shortcut). Reason:
  the library's own `SchemaMismatch` message names it as THE fix, and an error message must
  not send a user to a non-API function. `open_graph_index` stays internal (no message
  names it; it returns the low-level `WildcardIndex` + `RuleSet` pair).

## 4. What landed (uncommitted; RAN where marked)

- `src/zanzibar/schema/errors.py`: D1; `ZanzibarError`, `SchemaError`,
  `UnsupportedByGraphIndex` docstrings.
- `src/zanzibar/{schema,store,graphindex,setengine}/__init__.py`: D2 (each carries a
  comment stating the rule), D3, D5. `src/zanzibar/__init__.py` docstring: "the exceptions'
  ONE public home".
- `src/zanzibar/schema/rules.py`: docstrings for `Entity`, `RelationalTriple`,
  `SchemaInfo`; D4 bottom import. `src/zanzibar/schema/boolean.py`: `CompiledBooleans`
  docstring. `src/zanzibar/store/schema_io.py::open_set_engine` docstring.
- Tests: new `tests/test_tk164_public_surface.py` (25 tests, RAN green); updated
  `tests/test_tk123_top_level.py` (`_EXPECTED_ALL`, new `_DROPPED_EXCEPTIONS`,
  `_DROPPED['zanzibar.store']` minus `open_set_engine`, `_BUILTIN_BASE`),
  `test_tk123_equivalence_refusals.py`, `test_tk153_install_trial_ergonomics.py`,
  `test_tk154_stale_lookup_ids.py`, `test_tk166_foreign_token.py`, a comment in
  `test_hypothesis.py`. Nothing weakened: each changed pin asserts the new, stricter rule.
- `CHANGELOG.md` `[Unreleased]`: two summary bullets; under Changed a **Breaking** entry
  (exceptions' one home) and a **Behaviour change** entry (`ValueError` base); under Added
  the public types and `open_set_engine`.
- **Sabotage** (RAN, literal output in the test module docstring): S1 drop `ValueError` ->
  `5 failed, 20 passed`; S2 `"StaleRead"` into `zanzibar.store.__all__` -> `1 failed, 24
  passed`; S3 delete `Entity`'s docstring -> `1 failed, 24 passed`; S4 delete the D4 import ->
  `6 failed, 19 passed`. Each file restored and its sha256 re-checked.
- **For the gate:** 25 new tests, so `formal/FINAL_REVIEW.md`'s counts block needs
  `python -m formal.conformance.doc_counts --generate`.

## 5. Userdocs pages that must change (NOT edited here; a later TK151 stage)

Each says the current pre-TK164 behaviour. Line numbers as of 2026-10-23.

| page | where | what it must say |
|---|---|---|
| `userdocs/how-to/errors.md` | ~L3-10 | Every deliberate exception has a builtin base; drop "the exceptions are `UnsupportedByGraphIndex` and `DoublyBridgedShapeError`, which derive from `ZanzibarError` only". |
| `userdocs/how-to/errors.md` | ~L117-126 | Last sentence becomes: both are `ValueError`s (not `SchemaError`s), so `except ValueError` around schema loading catches them. |
| `userdocs/how-to/rewrite-refused-shape.md` | ~L13-14 | "Every refusal is also a `ValueError`" (drop the `DoublyBridgedShapeError` exception). |
| `userdocs/reference/exceptions.md` | ~L5-8 | Drop "have none"; every subclass has a builtin base. |
| `userdocs/reference/exceptions.md` | ~L10-13 | Replace "subpackages re-export some of them, each a different selection" with: exceptions are exported from `zanzibar` only; no subpackage lists them (an old subpackage import still resolves but is not API). |
| `userdocs/reference/exceptions.md` | ~L30 (tree) | `UnsupportedByGraphIndex [ValueError]` (the subclass line inherits it). |
| `userdocs/reference/exceptions.md` | ~L176-182 (`SchemaError` entry) | "Two refusals are not `SchemaError` (but are `ValueError`)"; `CyclicDerivedDependency` sentence unchanged. |
| `userdocs/reference/exceptions.md` | ~L255-258 | `Bases: zanzibar.ZanzibarError, ValueError` for `UnsupportedByGraphIndex` (+ "a `ValueError` since 0.1.0"). |
| `userdocs/how-to/upgrade-0.1.md` | ~L69-76 | Add: exceptions are no longer in any subpackage `__all__`; import them from `zanzibar` (old subpackage imports still resolve, not API). `open_set_engine` is public. |
| `userdocs/how-to/upgrade-0.1.md` | ~L161-166 (section 4) | "Exception classes keep their builtin bases" -> they keep them, and `UnsupportedByGraphIndex` / `DoublyBridgedShapeError` GAIN `ValueError`: an `except ValueError` now catches them. |
| `userdocs/reference/api/index.md` | ~L66-71 | Replace the "each subpackage re-exports some of the exceptions ... not every exception" paragraph with the one rule: exceptions are exported from `zanzibar` only. |
| `userdocs/reference/api/schema.md` | ~L66-94 (`RuleSet`) | `schema_info` is a `SchemaInfo`, `compiled` a `CompiledBooleans` (opaque), `apply` takes a public `RelationalTriple` of two `Entity`s: drop "importable from `zanzibar.schema` but is not public"; add `autoclass` entries for the four types. |
| `userdocs/reference/api/schema.md` | ~L236-247 | Delete "Exceptions re-exported here"; point to `zanzibar` / the Exceptions page. |
| `userdocs/reference/api/graphindex.md` | ~L214-220 | Delete "Exceptions re-exported here" (same). `WildcardIndex` / `DeltaProcessor` entries may now link `SchemaInfo` / `CompiledBooleans`. |
| `userdocs/reference/api/setengine.md` | ~L186-193 | Delete "Exceptions re-exported here" (same). |
| `userdocs/reference/api/store.md` | ~L261-277 | Delete "Exceptions re-exported here" (same); add an entry for `open_set_engine` (the remedy a `SchemaMismatch` names). |
| `userdocs/conf.py` | ~L105-114 `nitpick_ignore` | Remove `zanzibar.schema.rules.SchemaInfo`, `SchemaInfo` and `CompiledBooleans` once the pages document them (keep `Rule`, `Filter`, `DeclaredRelations`, `IndexCursor`); the `_resolve_internal_paths` resolver will then map `zanzibar.schema.rules.SchemaInfo` to `zanzibar.schema.SchemaInfo`. |
| `userdocs/how-to/port-openfga.md`, `explanation/two-backends.md` | ~L54; ~L268 | No change required (READ): neither claims `UnsupportedByGraphIndex` is not a `ValueError`. |
| `userdocs/reference/changelog.md` | whole | Refresh from `CHANGELOG.md`, as TK151 already plans. |

## 6. Residual (not done; REASONED)

- `RuleSet.rules_and_filters` still names internal `Rule` / `Filter`; deliberately left.
- The `zanzibar.<subpackage>.<Exception>` attributes remain importable; removing them would
  be a later, separate decision (allowed by the rule, since they are not in `__all__`).
- `SchemaInfo` is a frozen dataclass whose constructor is now public by export; its docstring
  says not to build one. No refusal was added.

## Review 2026-10-23

Adversarial review by agent `tk164-review` (workflow `wf-0p1`). Labels as above.

**Refutation attempts that held (the change survived):**

- **No `except ValueError` newly swallows a compile refusal** (READ, grep of every
  `except ... ValueError` in `src/`, `tests/`, `formal/conformance/`, `scripts/`). The `src/`
  handlers never reach `compile_ruleset`: `graphindex/core.py` ~L111 (int parse of the
  fan-out env var), `graphindex/processor.py` ~L633 (derived write), `schema/json_frontend.py`
  ~L257 (`parse_schema_ast` round trip), `store/apply.py::_apply_row` (index apply).
  `SetEngine.__init__` names the classes, `DoublyBridgedShapeError` first; `Store`'s handlers
  are `except Exception` (re-raise) or narrowed. The conformance helpers
  `test_conformance_fragment.py::_refused_by` / `_mirror_inputs` and
  `test_p23_parser_refusal_parity.py::_verdict` are fed `parse_schema_ast` only (no compile);
  `test_conformance_nary_strata.py` ~L357 / ~L684 re-raise or assert on the TK106 fragment;
  `formal/conformance/backends.py::GraphDriver.apply` ~L294 wraps writes, not compiles.
  `tests/parity.py`, `tests/genswarm.py` and every `except UnsupportedByGraphIndex` site
  name the class, so their behaviour is unchanged.
- **Every exported `ZanzibarError` subclass has a builtin base** (RAN, probe
  `.scratch/wf-0p1/tk164-review/bases.py`): the `ZanzibarError` docstring's new claim holds;
  the only `ZanzibarError` with no builtin base is the root itself.
- **No star import relies on a subpackage `__all__`** (READ, grep of
  `from zanzibar... import *` across the repo): only the upgrade page's prose mentions one.
- **The export pin is not vacuous for a NEW exception**: `test_tk164_public_surface.py`
  only walks `zanzibar._LAZY`, but `test_tk123_top_level.py::
  test_every_exception_is_exported_from_the_top_level` censuses every exception class
  DEFINED in the package (with `test_census_detects_a_missing_export` as its control), so an
  exception added without a top-level export is red (READ).
- **New docstrings match the code** (READ): `Entity.wildcard` exists and tests `name == '*'`;
  `RelationalTriple.subject_predicate` defaults to `Ellipsis` and `__str__` prints
  `object#relation@subject#predicate`; `WildcardIndex.__init__(idx, schema_info)` and
  `DeltaProcessor.__init__(widx, compiled)` take what the `SchemaInfo` / `CompiledBooleans`
  docstrings say; `open_set_engine`'s `StoreNotFound` (`load_schema`) and
  `PersistedSchemaRefused` (`_persisted_schema_parse`) claims hold, and
  `setengine/engine.py` ~L252 / ~L266 name it in the `SchemaMismatch` message.

**Defects found and fixed:**

1. `scripts/installed_smoke.py` ~L346-347 checked "public name exists" by importing
   `SchemaMismatch` from `zanzibar.store` and `AdmissionRejected` from `zanzibar.schema`,
   which TK164 made non-API. Now `from zanzibar import AdmissionRejected, SchemaMismatch`
   (py_compile clean; the script runs only in the install trial).
2. `CHANGELOG.md` `[Unreleased]` said `PersistedSchemaRefused` "now lives in
   `zanzibar.schema`" (summary bullet) and "is exported from `zanzibar.schema`;
   `zanzibar.store.PersistedSchemaRefused` [is] the same class" (Changed, TK153 entry),
   contradicting the TK164 rule in the same section. Both now say import it from `zanzibar`.

**Residual (not fixed):**

- `benchmarks/fanout_cost_bench.py` ~L72 imports `ClosureFanoutExceeded` from
  `zanzibar.schema`. It still resolves; `benchmarks/` belongs to a concurrent TK162 session.
  Change it to `from zanzibar import ClosureFanoutExceeded` when that session is done.
- The userdocs pages in sec 5 still describe the old surface (e.g.
  `reference/api/schema.md` calls `SchemaInfo` "importable but not public"). The docs build
  is green regardless (RAN); the edits are TK151's.

**Test status** (RAN, 2026-10-23): `tests/test_userdocs_build.py`,
`tests/test_userdocs_examples.py`, `tests/test_tk122_release_metadata.py`,
`tests/test_tk164_public_surface.py`, `tests/test_tk123_top_level.py`: rc=0, `84 passed`
before the fixes; re-run after them below.
After the two fixes: `test_tk122_release_metadata`, `test_tk164_public_surface`,
`test_tk123_top_level`, `test_userdocs_build`: rc=0, `48 passed`; `scripts/handoff_lint.py`
rc=0, `clean (13 checks)`.
