# OpenFGA / SpiceDB claims audit — 2026-10-13 (before the 0.0.4 tag)

> **FROZEN 2026-10-13 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

**Why.** The user asked, before pushing the `v0.0.4` tag, that "anything mentioned about
openfga/spicedb is accurate". This records what was checked, what was wrong, what was
changed, and the behaviour gaps it surfaced (filed as rows, not fixed).

**Method.** Three read-only `general-purpose` agents (opus), one per slice: living docs,
shipped code (`src/`, `scripts/installed_smoke.py`, `benchmarks/`), and tests
(`tests/`, `formal/conformance/`, `formal/lean/` comments, `formal/probes/`). Each
graded every claim against official sources (openfga.dev docs, openfga/openfga
`pkg/typesystem/typesystem.go` and `pkg/tuple/tuple.go`, openfga/language
`OpenFGAParser.g4`, openfga/api `authzmodel.proto`). FROZEN docs, `docs/history/`,
`formal/history/` and `tasks/closed/` were skipped: they are as-of-then provenance. Their
raw reports were in gitignored `.scratch/openfga-claims/`; this file is the record.

**Provenance labels.** First-hand READ = the session fetched the source itself and read
the line. AGENT = an agent's report, not re-checked by the session. PROBE = a script run
by the session against this tree (HEAD `8e0d09d` + this session's edits).

## 1. Counts

No file in any slice mentions SpiceDB or Authzed (0 hits outside skipped history), so
every finding is about OpenFGA.

| slice | WRONG | MISLEADING | UNVERIFIABLE | ACCURATE (grouped rows) |
|---|---|---|---|---|
| docs | 1 | 6 | 1 | 29 |
| src | 0 | 4 | 2 | 25 |
| tests | 1 | 2 | 1 | 16 |

## 2. External facts the corrections rest on (first-hand READ, 2026-10-13)

1. **Tupleset restrictions.** https://openfga.dev/docs/configuration-language: "OpenFGA
   does not allow the referenced relation (the word after `from`, also called the
   tupleset) to reference another relation and does not allow non-concrete types (type
   bound public access (`<object_type>:*`) or usersets (`<object_type>#<relation>`)) in
   its type restrictions." So OpenFGA refuses a `[folder:*]` tupleset too: that one is
   this repo's extension.
2. **One direct block per definition.** `OpenFGAParser.g4`: `relationDefPartials` allows
   only `relationDefGrouping | relationRecurseNoDirect` after `or`, so `[a] or [b]` is not
   OpenFGA DSL. The `or` / `and` / `but not` partials are alternatives, so an
   unparenthesised `x or y but not z` is not OpenFGA DSL either.
3. **Wildcards.** https://openfga.dev/docs/modeling/public-access: "You cannot use the
   `<type>:*` syntax in the tuple's object field." and "You cannot use `<type>:*` as part
   of a userset in the tuple's user field." OpenFGA's wildcard is subject-side only
   (`user:*`).
4. **The "registry" idiom.** https://openfga.dev/docs/use-cases/multi-tenant-saas: "Model
   an `organization` (or `tenant`) type and make every other resource belong to it";
   resources "each declare a `parent` relation pointing at an `organization`". The
   README's "registry object" is that idiom under this repo's own name, not a
   hallucination.
5. **`IsSelfDefining`.** `pkg/tuple/tuple.go`: "IsSelfDefining returns true if the tuple
   is reflexive/self-defining. E.g. Document:1#viewer@document:1#viewer." The API docs
   (https://openfga.dev/docs/api/service/relationship-tuples/add-or-delete-tuples): "The
   API does not allow you to write tuples such as
   `document:2021-budget#viewer@document:2021-budget#viewer`, because they are implicit."
   It is NOT the attribute-marker idiom. That idiom is
   https://openfga.dev/docs/best-practices/modeling-abac: "use a self-referential relation,
   where an object points to itself to indicate an attribute is set"
   (`organization:acme sso_enabled organization:acme`).
6. **`"metadata": null`.** openfga/language
   `tests/data/transformer/01-only-type/authorization-model.json` is
   `{"type": "user", "relations": {}, "metadata": null}`, so the DSL-to-JSON transformer
   emits it. Whether the live API does was not checked.
7. **Announced changes.** https://openfga.dev/blog/weighted-graph-upcoming-changes
   (2026-07-21): a check with user `user:*` on a relation using `but not` will "return an
   error"; models with recursion through `and` / `but not`, or a TTU whose target relation
   is missing on some tupleset type, will fail to build. "A date for the final changeover
   has not been set."

## 3. What was wrong, and what changed (all edits landed 2026-10-13)

| where | claim | verdict | change |
|---|---|---|---|
| `README.md` § "`*` wildcard entities" | "whereas OpenFGA only suppots usersets" | WRONG: backwards (fact 3) | says OpenFGA supports wildcards as a subject only |
| same place | "Claude may have hallucinated something about registry objects" | MISLEADING (fact 4) | names the OpenFGA idiom the word stands for |
| `README.md` roadmap, "symmetric subject-keyed residues" | "low priority: the OpenFGA DSL doesn't support these either ... deliberate boundary, not a gap" | MISLEADING: `formal/FINAL_REVIEW.md` already rules that argument out for this repo's own extensions | low priority rests on "no need yet"; OpenFGA lacking them is stated, not used as a reason |
| `PYPI_README.md` intro | "written in the OpenFGA modelling DSL" | MISLEADING: a subset | "a subset ... (schema 1.1 ...; no conditions or modules)" |
| `PYPI_README.md` "Schema shapes" | "Some valid OpenFGA shapes are refused ...: for example, a `from` tupleset must be a direct relation" | MISLEADING: OpenFGA refuses that too (fact 1); star tuplesets were missing from the extensions list | conditions and modules named as unsupported; the direct rule framed "as in OpenFGA"; star tuplesets listed |
| `CLAUDE.md` tupleset rule | "union of Directs (wildcards allowed)" beside "as in OpenFGA" | MISLEADING (facts 1, 2) | "both looser than OpenFGA" |
| `docs/specs/wildcard-materialization-spec.md` objective | `group:*#member` listed outside "beyond OpenFGA" | MISLEADING (fact 3) | moved inside it |
| `CHANGELOG.md` 0.0.4, `tests/test_tk134_json_malformed_shapes.py::test_null_optional_fields_read_as_absent` | "OpenFGA's API emits `\"metadata\": null`" | UNVERIFIABLE as stated (fact 6) | credited to the DSL-to-JSON transformer |
| `src/zanzibar/schema/parser.py::_validate_tuplesets_direct` docstring | "OpenFGA refuses the rest" after listing `[folder] or [doc]` and keeping `[folder:*]` legal | MISLEADING (facts 1, 2) | names both as this library's extensions |
| `parser.py::_validate_tuplesets_direct`, TK108 refusal message | "(OpenFGA rule)" tagged onto the suggested rewrite, which for `[T:*#p]` suggests the non-OpenFGA `[T:*]` | MISLEADING | tag moved onto the refusal clause; the `tupleset may not restrict to a userset` witness text is unchanged |
| `parser.py::parse_schema_ast`, `src/zanzibar/schema/compiler.py::parse_openfga_schema` docstrings | "an OpenFGA DSL string" / "an OpenFGA schema" | MISLEADING: a subset plus extensions (PROBE: `with` conditions, `module`, `extend type` refused) | "OpenFGA-style", with the subset stated once in `parse_schema_ast` |
| `src/zanzibar/setengine/engine.py::SetEngine.check` (D1 comment), `tests/oracle.py` (same), `tests/test_blind_audit_regressions.py::test_star_subject_flows_through_granted_usersets_3way`, `docs/architecture/overview.md` § Key semantics, `docs/spec-deviations.md` D1 | "the OpenFGA literal-subject reading" | UNVERIFIABLE: no OpenFGA doc says it, and OpenFGA errors on `user:*` under `but not` (fact 7) | "a literal-subject reading, unverified against OpenFGA" + the `but not` difference; spec-deviations gets a dated correction |
| `tests/test_self_referential_tuples.py` module docstring + section comment, `formal/conformance/corpus.py` self-referential comments, `docs/spec-deviations.md` 2026-07-13 entry | "OpenFGA ... `IsSelfDefining` concept (e.g. `document:1#viewer@document:1#viewer`)" as the attribute-marker idiom | WRONG: a different concept, and OpenFGA refuses that tuple (fact 5) | cites the modeling-abac attribute marker; the IsSelfDefining confusion explained; spec-deviations gets a dated correction |
| `tests/test_tupleset_must_be_direct.py` docstring, `corpus.py` `REFUSED_TUPLESET_SCHEMAS` comment | "OpenFGA refuses anything else" after `[folder] or [doc]`, wildcards | MISLEADING (facts 1, 2) | the extras are named as beyond OpenFGA |
| `docs/spec-deviations.md` TK126 entry | "The set engine and OpenFGA serve all three" | ACCURATE today, time-limited (fact 7) | dated note added |
| `benchmarks/scale_bench.py` module docstring | "(the OpenFGA question)" | UNVERIFIABLE: no checkable content | dropped |

ACCURATE, among others (AGENT): every refusal said to match OpenFGA (computed / boolean
tupleset arms, userset tuplesets, dangling references, computed cycles, `ErrCycle`,
TTU recursion stays legal); the JSON front end's field names, the six rewrite operators,
`"wildcard": {}`; OpenFGA tolerates cyclic tuples; `UnprovenExtensionWarning`'s three
extensions are all outside OpenFGA; README's "Stock OpenFGA has no wildcard usersets,
star tuplesets or object wildcards".

## 4. Behaviour gaps found (PROBE, `.scratch/openfga-claims/probe_session2.py`, 2026-10-13)

Not doc claims, so not fixed here; filed as rows (see the session-log entry 2026-10-13c).

1. **The DSL parsers accept shapes OpenFGA refuses.** Both the product parser and the
   oracle twin accept: a `schema 1.2` / `schema 9.9` header (silently; the JSON front end
   refuses anything but 1.1), no `model`/`schema` header at all, `define viewer: [user] or
   [doc]`, and `define viewer: [user] or a but not b`, which both read as
   `([user] or a) but not b` (set engine and oracle agree: `u2` with `a` and `b` is
   denied). OpenFGA's grammar refuses the last two (fact 2).
2. **A userset is not related to itself here.** With `define viewer: [user, doc#viewer]`
   and no tuples, `check(doc:1#viewer, viewer, doc:1)` is `False` on the set engine and
   the oracle. OpenFGA treats that tuple as implicit (fact 5), so its check answers true
   (REASONED from the RFC that `tuple.go` cites, not run against a server). Writing the
   tuple is refused on both sides: here as `AdmissionRejected` ("would create a cycle in
   the userset membership topology"), there as implicit.
