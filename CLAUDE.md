# CLAUDE.md — graph-reachability-zanzibar-index

Zanzibar-style relationship/permission indexing. Two evaluation backends with **identical
semantics but opposite cost models** (a memoization spectrum), pinned together by a shared
independent reference oracle. Both backends support boolean operators (`and` / `but not`):
the set engine natively, the graph index via derived predicates maintained by a stratified
IVM delta processor.

This file is auto-loaded into every session, so every byte costs every session. It is
byte-capped (`scripts/handoff_lint.py::MAX_BYTES`): it holds RULES plus one line of why and a
pointer. Case histories go to the session log, detail to its home doc (`docs/README.md` §8).

## Who decides (user instruction, 2026-09-12b)
- **The user does not read or write Lean proofs and is not going to.** All key architectural
  decisions — in `formal/` and in the Python — are DELEGATED to the model. Do not hand a
  Lean-shaped choice back to the user ("narrow the predicate or add a lemma?"); decide it,
  record the decision and its reasoning on the task row (`task.py comment <id> --session
  <key>`), and move on. Ask the user only about goals and priorities, never about proof
  mechanics.
- **The primary consideration is EQUIVALENCE: the graph index must give the same answers as
  the set engine** (the oracle is the referee for both). Every decision is weighed as
  engineering complexity against that goal. If the two backends disagree, **the default
  assumption is that the Python is wrong and should be fixed** — not that the Lean fragment
  should be narrowed to exclude the case, and not that a golden or oracle result should be
  edited to match. A proof that describes something other than the shipped code is a proof
  of nothing (`formal/CORRESPONDENCE.md` §8).
- **When a session is stuck on an executive decision** (which of two sound designs, whether
  a cone is worth paying, whether a divergence is a Python bug or a fragment boundary), it
  may spawn a `claude-fable-5` subagent (`Agent` tool, `model: "fable"`) to think the issue
  through against the goal above and return a decision with reasoning. The subagent's
  answer is a recommendation, not an order — the session records it on the row with the
  reasoning, then acts. This applies whatever model the session itself runs on.

## Start here (every session)
- **Start with `python scripts/task.py board`** — the session-start view, a QUERY over the
  file-per-task tree in `tasks/` (bounded by `task.py::BOARD_MAX_LINES`; never restate it).
  It opens with the `## Banner` of [`HANDOFF.md`](HANDOFF.md), a **one-hop note** (banner,
  still-owed, where to go next; no row table, no item blocks; capped by
  `handoff_lint.py::MAX_LINES` / `MAX_BYTES`). `show <id>` is the per-item read (Log newest
  first), `ready` lists unblocked work, `list` is capped and says so. At session end write
  back via the Rhythm in [`docs/README.md`](docs/README.md) §7.
- **The current goal (user, 2026-09-22c): make the assurance surface honest and legible, not
  wider**; perf is deprioritized. Why: `docs/architecture/decision-log.md` § "The project goal".
- **The tree is the SOLE authority on open work** since the 2026-09-06 cutover (spec
  [`docs/tree-sole-authority-spec-2026-08-29.md`](docs/tree-sole-authority-spec-2026-08-29.md)
  and trial verdict [`docs/tasktool-trial-protocol.md`](docs/tasktool-trial-protocol.md), both
  FROZEN). Old runbooks mislead: `tasks/BANNER.md` is a tombstone (lint check 12 fails if it
  reappears), `task.py sync` / `ack` REFUSE and name their replacement, lint check 13 is
  retired and its number never reused, `source_hash` is frozen
  ([`docs/tasktool-spec.md`](docs/tasktool-spec.md) "The retired verbs").
  * **Every re-rank, close, and progress note goes through an op with `--session <key>`**
    — `promote` / `touch` / `close -m` / `set <id> brief` / `comment <id> -m` — never a
    hand edit of a task file's frontmatter. Schema and op contract: `docs/tasktool-spec.md`.
    The tool is pinned by `tests/test_tasktool.py`, inside the gate.
  * **Close the loop in your session-log entry with two literal lines** (enforced:
    `handoff_lint.py::check_session_receipt` makes `lean` RED without them): the output of
    `python scripts/task.py lint`, and `read: board only` / `read: board + note` — an honest
    self-report of what you actually read to start work. **A third line is conditional**
    (`TK96`): while any open `ASK-*` row sits at `NEXT` (or `NOW`), raise each with the user
    in chat and write `asked: ASK-<n>[, ASK-<m>]` naming all of them — `asked: none` is red
    then (`python scripts/task.py asks` lists them).
  * ⚠ **A `close -m` / `comment -m` message with backticks inside DOUBLE quotes is
    command-substituted by the shell** — the backticked text vanishes silently. Use single
    quotes, or a heredoc, or a file.
- **SCOUTING IS A DELIVERABLE, NOT A BYPRODUCT** (user instruction 2026-09-13g). Measuring
  the tree (cone counts, call-site censuses, symbol/line maps, go/no-go adjudications) is the
  expensive half of an `L`-sized item; a session that measures and only *acts* makes the
  next session pay for it again. So:
  * **The measurement lands in a TRACKED file the same hour it is made**, before the edit it
    was made for: not `.scratch/`, not a chat summary, not the row's prose. The shape is an
    **ACTIVE-PLAN** doc (`docs/README.md` §3), `docs/<id>-<topic>-<YYYY-MM-DD>.md`,
    corrections appended **dated at the top**, FROZEN when the item closes. Precedent:
    [`docs/p6-step3b-plan-2026-09-13.md`](docs/p6-step3b-plan-2026-09-13.md).
  * **Label every claim by provenance**: first-hand READ, REASONED, or UNVERIFIED, naming
    the agent/probe. A subagent report is evidence, not a finding. Flag not-yet-verified
    items *in place*, not in a footnote.
  * **Cite `file::symbol`, and date any line number** (line numbers rot within a session).
  * **The task row is the index, the doc is the body.** Close with
    `task.py comment <id> --session <key>` naming the file, what LANDED, what BUILDS, what is
    RED, and the single next action. `show <id>` alone must be enough to resume.
  * **This applies to a session that runs out of room, too**: write the state down before
    clearing context or stopping mid-item.
- **Always run the gate before pushing; push only when asked.** Every `verify.sh` phase
  `PASSED` (+ a fuzz sweep for an algorithm change); see "Running things" below and
  [`docs/gate-runbook.md`](docs/gate-runbook.md). `tests/` runs THROUGH `verify.sh`; bare
  `pytest tests/` is fine while iterating, but it is not the gate.
- **COMMIT whenever the full gate is green and the session did work** (user instruction
  2026-08-28b; a green tree is the cheapest resume point). When `python
  scripts/gate_status.py` says **COVERED on this tree** and you changed something (docs-only
  edits count; a read-only session does not), commit without waiting to be asked. Push stays
  opt-in. If the gate is NOT fully green, do not commit to make progress look like
  assurance: say what is red and leave it.
  ⚠ Editing `*.md` stales the `lean` verdict, and edits to `tasks/`, `HANDOFF.md` or any
  other file in `gate_status.py::CODE_SCOPE_MD_KEEP` stale the tiles too (`docs/README.md` §7): write the session records FIRST, then run the gate, then
  commit, or the commit's own banner is a claim the tree no longer supports.
- **The standing footguns.** Each has bitten a session in this repo; the write-ups are in
  [`docs/gate-runbook.md`](docs/gate-runbook.md) and the session log.
  * ⚠ **An exit status reported by a wrapper can lie.** A pipe through `tail`/`tee` reports
    the PIPE's status, and ANY trailing command after `rc=$?` (a `grep`) sets the status the
    harness shows (2026-09-16b). Run `cmd > "$(mktemp /tmp/gate-XXXXXX.log)" 2>&1; rc=$?`,
    **echo the verdict where you will read it** (`[ $rc -eq 0 ] || echo RED`), and read the
    log's `PASSED` / last line every time. **One phase per command** (a killed loop orphans a
    `pytest` that writes the next phase's log), and **never a fixed log path** (two runs into
    one file pair one run's `rc` with the other's tail; `scripts/gate_lock.py` now makes
    `verify.sh` refuse a concurrent run). On any exit-code/log disagreement, check for a
    stray interpreter and re-run alone to a fresh log before believing either.
  * ⚠ **`HYPOTHESIS_SEED=N` does nothing** — hypothesis never reads that variable, so a
    "multi-seed sweep" written with it runs the SAME seed every time. Only
    `--hypothesis-seed=N` works; `tests/conftest.py` refuses the env var outright.
  * ⚠ **A divergence gets a positive pin, never an xfail** — an xfail is itself a failure
    that passes. The declared budget knob is `MAX_TESTS_XFAILED`, and `formal/verify.sh` is
    the only place its value belongs (do not restate it in prose).
  * ⚠ **`MIN_CONF_ALL` / `MIN_TESTS_ALL` have ZERO headroom** — they equal the live
    collected counts, so deleting a single test turns the gate red. Adding tests is always
    free; lowering a floor must be a deliberate, reviewed edit.
  * ⚠ **On a red gate, snapshot with a TEMP INDEX — never `git stash` or
    `git checkout --`.** `core.autocrlf` rewrites LF → CRLF on the way back out, so the
    "restored" tree is not the tree you saved and the next diff is noise (trap (ee) in
    `formal/history/leaf-family-split-scope-2026-08-05.md`).
- **Shared doc conventions live in [`docs/README.md`](docs/README.md)** — liveness states
  (LIVING / FROZEN / ACTIVE-PLAN) and the frozen banner, the session-ledger entry format,
  citation keys, the priority vocabulary (`NOW`/`NEXT`/`LATER`/`HOLD`/`SOMEDAY`) and its
  budgets, and the one-home-per-statement routing table. Read it before restructuring any doc.
- **Two record-keeping rules** (repo-wide; the incidents are in the 2026-08-20b session-log
  entry).
  * ⚠ **`.scratch/` is gitignored — anything recorded ONLY there is already lost.** If a run
    is evidence (a green sabotage included), it goes in a tracked file the same hour.
  * ⚠ **A trap must cite a symbol that EXISTS.** Grep `file::symbol` before writing it down.
    The same applies to counts: get one from `pytest <target> -q --collect-only`, never from
    a run's tail (a multi-module `N passed` is not one module's count).

## Delegation — the repo-specific half
**The rule itself lives in `~/.claude/CLAUDE.md` § Delegation and is NOT restated here**
(deduplicated 2026-09-20e, user instruction). Its provenance in this repo, kept because the
machine-wide file lacks it: the user's preference was **stated 2026-08-28**, and the
`ultracode` / `Workflow` standing approval is **2026-09-20d**. Only what is true HERE follows.

- **Sizing claims in this repo have come in LOW, repeatedly**, so the `file::symbol` rule is
  not optional (`P3`'s re-verified "~123 sites / 7 files" was live ~136 / 8 on 2026-08-28).
  An agent that returns prose has spent the tokens without buying the certainty.
- **`.scratch/` here is governed by § SCOUTING IS A DELIVERABLE above**, which is stricter
  than the machine-wide rule: a TRACKED file, the same hour, in the ACTIVE-PLAN shape,
  labelled first-hand READ / REASONED / UNVERIFIED.
- **Verified FIRST-HAND before an agent's report is written down**: anything headed for
  `formal/history/` (append-only), a gate pin, a golden, or an `audited_theorems.txt` entry.
  Contradicted reports get reconciled, not averaged.
- ⚠ **One file per agent** — two writers on one filename is the fixed-log-path footgun one
  level up.

## Running things
- Conda env named after the folder, `graph-reachability-zanzibar-index`, under
  `C:/Users/user/anaconda3/envs/`. `verify.sh` resolves the interpreter itself (`resolve_py`);
  `ZANZIBAR_PY` is an optional override, not a prerequisite (`docs/gate-runbook.md`
  "Interpreter"). ⚠ **The Lean toolchain is not on `PATH`**: `lake`/`lean` live in
  `~/.elan/bin`, which `verify.sh` prepends; building by hand needs
  `export PATH="$HOME/.elan/bin:$PATH"` first.
- **How the code is found (TK120).** `pytest.ini` sets `pythonpath = src`, `formal/verify.sh`
  exports `PYTHONPATH=<repo>:<repo>/src`, and the repo-root `conftest.py` passes `src` to
  child interpreters and REFUSES to run if `import zanzibar` resolves outside this checkout's
  `src/` (`tests/test_tk120_package_layout.py`). So every checkout and worktree tests its own
  code with nothing installed; `pip install -e . --no-deps --no-build-isolation` is only for
  benchmarks, probes and ad-hoc scripts.
- The full suite is the gate (`tests/` + `formal/conformance/`; more in `tests/` with a
  PostgreSQL DSN), with `-ge` floors on both (`MIN_TESTS_ALL` / `MIN_CONF_ALL`). **No
  figures here, deliberately**: a count in this file once understated the suite by hundreds
  of tests within weeks (`ZT-P3-5`). Live figures live in ONE machine-checked place,
  `formal/FINAL_REVIEW.md`'s generated counts block (`verify.sh` step 4e; regenerate with
  `python -m formal.conformance.doc_counts --generate`). Re-measure with
  `pytest <dir> -q --collect-only` before quoting one anywhere.
- **The gate = `bash formal/verify.sh <phase>`**, because the one-shot blows the harness's
  ~10-min command cap: `lean` → `conf-tile:1/5`…`conf-tile:5/5` → `tests-tile:1/4`…`4/4`.
  The tiles are a structural partition (collected fresh, index mod K), so a new test file
  needs no list update. Every phase asserts a count floor, a nonzero pass count, the pytest
  exit code, and zero `skipped`/`xpassed`/`deselected`; `xfailed` is zero for conformance and
  budgeted for `tests/` (`MAX_TESTS_XFAILED`). `lean` also pins the audited theorem NAMES,
  the headline theorem STATEMENTS, every `CORRESPONDENCE.md` anchor, and runs
  `handoff_lint.py` and `task.py lint`. **Push only after every phase is green** (+ a fuzz
  sweep for an algorithm change). Each run appends to the gitignored `.gate-runs/ledger.tsv`;
  `python scripts/gate_status.py` reports which phases are green **on the current tree**.
  Details and sabotage evidence: [`docs/gate-runbook.md`](docs/gate-runbook.md) §4.
- **GitHub Actions runs the same gate (`TK122`)**: `.github/workflows/gate.yml` is one job
  per phase on Linux, and `.github/workflows/fuzz.yml` is the multi-seed sweep, **on demand
  and before a release only, never scheduled** (user decision). The workflows only provision
  and call `verify.sh`; floors and budgets stay there. CI does NOT replace the local gate
  (CI installs the newest dependency versions, the local env the pinned ones).
  **Releases deploy ONLY from a `v*` tag** via `.github/workflows/publish.yml`; its header is
  the release recipe and `workflow_dispatch` is a dry run. ⚠ The file name `publish.yml` and
  the environment `pypi` are registered on PyPI as the trusted publisher, so renaming either
  breaks the upload at its last step. A tag is a RELEASE: push one only on the user's
  explicit word. Every push gets a CI-babysitter subagent (`~/.claude/CLAUDE.md` § Git).
- **The PostgreSQL leg is opt-in and therefore easy to think you ran.**
  `bash scripts/pg_local.sh start` prints a DSN; export it as `ZANZIBAR_TEST_DSN` to re-run
  the HA/concurrency modules against a real server plus `tests/test_postgres_ha.py`. Without
  a DSN that module is dropped at COLLECTION (a tolerated skip is how coverage leaks out of a
  gate); `ZANZIBAR_PG_REQUIRED=1` makes a missing DSN a hard error. Run it for anything
  touching locking, watermarks, isolation or multi-instance state (`docs/gate-runbook.md`).
- Deps: `sqlmodel`, `pytest`, `pyroaring` (set-engine default bitmap backend), `hypothesis`
  (property/stateful fuzzing); `psycopg2-binary` for the server leg only. A missing
  `pyroaring` would halve the validation matrix, so collection refuses to start
  (`tests/conftest.py`), and so does `verify.sh`'s preflight.

## Layout / mental model
Module map and pointers: `docs/architecture/overview.md`.
- **The library is ONE package, `src/zanzibar/` (`TK120`), distribution `zanzibar-index`
  (`pyproject.toml`; the import name stays `zanzibar`), Apache-2.0.** The PyPI long
  description is `PYPI_README.md`, NOT `README.md`, and its quickstart is executed by
  `tests/test_tk122_release_metadata.py`; the version lives ONLY in
  `src/zanzibar/__init__.py::__version__`, and `CHANGELOG.md`'s newest heading must match.
  **Every table, explicit constraint and explicit index is named `zanzibar_*` /
  `ix_zanzibar_*`, and no table sets `extend_existing`** (`TK122`): a consumer's clashing
  table must fail loudly, never merge (`tests/test_tk122_table_namespace.py`). A new model
  follows both rules. `tests/`, `formal/` (Lean + conformance), `benchmarks/`, `scripts/`,
  `docs/` sit OUTSIDE the package on purpose: Lean is the evidence, not the library. Pre-TK120
  names (`index_v4/`, `NodeV4`, `legacy/`, ...) survive on purpose in FROZEN/ACTIVE-PLAN docs
  and closed rows; the key is `docs/architecture/overview.md` § "Renamed in TK120". No
  compatibility shims exist.
- **`src/zanzibar/graphindex/`** — the graph index. `ReachabilityIndex` (core.py)
  materializes the full transitive closure as ref-counted edges, so `check` is O(1);
  `WildcardIndex` (wildcard.py) adds materialized `*` bridges and the derived-relation read
  path (edge probe + residue). **Boolean operators are derived predicates**: `processor.py`
  (the delta processor: reconcile + per-stratum cascade over the outbox), `outbox.py`
  (`DeltaOutbox`; write paths return None, deltas are rows), `invariants.py` (I1–I12
  checker, paranoia mode, §8.3 delta-scoped verifier), `models.py` (`Edge.derived`,
  `Residue`). Offline bulk bootstrap for `build_index`: `bulk_build.py` + `bulk_backfill.py`.
- **`src/zanzibar/setengine/`** — the set engine. Stores only raw tuples (`RelationTuple`),
  builds no closure, computes memberships on the fly with bitmap algebra, and **supports
  `and` / `but not`**. `setops.py` is the pluggable `SetOps` seam (`RoaringSets` default /
  `PySets`; never `isinstance`-check the underlying set type); `memberset.py` the
  star-closed `MemberSet` (`pos` / `stars` / `neg`); `engine.py` `SetEngine` (`check` /
  `expand` / `lookup`, `rebuild()` replays from `RelationTuple`).
- **`src/zanzibar/schema/`** — the shared schema layer (`__init__` re-exports the public
  names). Recursive-descent parser → `SchemaAST`; `compile_ruleset` produces the graph
  index's Filters/Rules **plus, for boolean (tainted) relations, the AOT derived-predicate
  artifacts** (`RuleSet.compiled`). `UnsupportedByGraphIndex` survives only for scope
  rejections and `enable_boolean=False`; derived-dependency cycles raise `ValueError`. `.` is
  reserved in declared relation names (leaf predicates are `<relation>.<index>`).
  `w4_fragment_report` mirrors the Lean `W4Fragment` decider and is differential-pinned to it
  (`formal/conformance/test_conformance_fragment.py`), so fix the Python, not Lean, on a red.
- **`tests/oracle.py`** — independent reference oracle (pointwise, boolean-aware).
  **Independence contract:** it imports nothing from the package and parses the DSL itself,
  so one parser bug can't corrupt both sides of the validation matrix.
- **`src/zanzibar/connectedstore/`** — the composed system (Zanzibar/Leopard split):
  `RelationTuple` + permanent `TupleLog` = source of truth, graph index = materialized view.
  `TupleSource` (admission-validated writes returning log-id freshness tokens),
  `advance_index` (THE apply step — sync inlines it, async loops it via
  `ConnectedStore.catch_up`), `build_index` (offline bootstrap), `SchemaRecord` (write-once
  schema source; compiled artifacts are cache). Composition layer only: it imports both
  backends, they never import it. Schemas are static — a new schema means a new store/index.
- **Specs** live in `docs/specs/`; code comments cite them by section: bare "spec §N" in
  `graphindex/*` → wildcard-materialization-spec.md, in `setengine/*` → set-engine-spec.md;
  "boolean spec §N" → graph-boolean-ivm-spec.md. Divergences: `docs/spec-deviations.md`.
  Where a spec and the code disagree on a name, the code wins.

## Testing conventions
- The **validation matrix** (`tests/test_matrix.py`) is what pins "same semantics":
  handwritten expectations · oracle · set engine · graph index, compared over a full query
  grid, under **both** `SetOps`. Boolean schemas run **4-way** (graph included, processor-
  maintained, I9-audited per op).
- The **ParityEngine** (`tests/parity.py`) is the default engine for integration-style
  tests: every op fans out to all backends with unanimity, I12, and full-grid oracle parity
  asserted internally. **Paranoia mode** (default ON via `make_wildcard_index`) runs the
  invariant checker + delta-scoped verifier inside every commit; pass `paranoia=False` in
  benchmarks or when a test corrupts state on purpose.
- The **hypothesis campaign** (`tests/test_hypothesis.py`): metamorphic schema pairs,
  multiset restoration, permutation invariance, cascade replay-from-zero, schema
  round-trips, and a stateful ParityEngine machine. Profiles: `ci` (default) /
  `HYPOTHESIS_PROFILE=deep` locally. Property tests share a candidate pool + grid
  (`tests/test_wildcard_property.py`).
- **`tests/test_lookup_oracle.py` is the lookup-surface oracle gate**: brute-force reference
  lookups from `oracle.check` pin `lookup` / `lookup_reverse` / `expand` on both backends.
  **Any strict xfail there pins a genuine divergence** — fix the surface and then flip the
  xfail; never relax the properties.
- **Never edit a golden or oracle result to make a refactor pass** — the oracle and goldens
  ARE the behavioral spec, and the compiled-RuleSet snapshots (`tests/snapshots/`) are the
  byte-identity gate for untainted compilation. A missing golden is a hard FAIL; regenerate
  deliberately with `ZANZIBAR_UPDATE_SNAPSHOTS=1`.
- **An assurance step that fails by PASSING is this project's house failure mode; the
  response is [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md)** (its "Why" table is
  the case history). Read it before adding any test, floor, assertion, pin, or gate phase:
  break the narrowest *plausible* weakening, control your *instrument* as well as your
  subject, prefer the most durable form (a permanent sabotage test > a derived expectation >
  a floor with provenance > a docstring), and record the literal observed output in the
  test's docstring and the commit message. **When you add a check, sabotage the thing it
  guards and watch it go red before you believe it.** Prefer a mechanical refusal over a doc
  warning, and convert an `xfail` into a positive pin.

## Gotchas / invariants
- **Schemas must be self-consistent (user decision 2026-09-26, `ASK-1`).** Both parsers
  refuse a dangling relation reference (computed ref, TTU tupleset, TTU target, `[T#P]`) and
  any cycle of computed / TTU-tupleset references
  (`src/zanzibar/schema/parser.py::_validate_ast_consistency`, oracle twin
  `tests/oracle.py::_validate_consistency`). Recursion through stored tuples stays legal. A
  test that needs "graph refuses, set engine accepts" uses a derived cycle through a TTU
  TARGET. Non-raising reports, the conformance encoder and grammar tests read
  `_parse_schema_ast_unchecked`. Map: `docs/ask1-schema-self-consistency-2026-09-26.md`.
- **A `from`-tupleset must be DIRECT-ONLY (user decision 2026-09-26, `TK106`), as in
  OpenFGA.** The relation after `from` may only be Directs or a union of Directs (wildcards
  allowed); both parsers refuse the rest at parse time
  (`src/zanzibar/schema/parser.py::_validate_tuplesets_direct`, oracle twin of the same
  name), because `from` walks STORED tuples and a boolean or computed arm there was silently
  ignored. The rewrite is `parent_link: [<types>]`, used by the `from`. So a tupleset is
  never tainted (`TK107` deleted the code that served one). Maps:
  `docs/tk106-boolean-tuplesets-2026-09-26.md`, `docs/tk107-tainted-tupleset-removal-2026-10-05.md`.
- **A tupleset may not restrict to a userset (user decision 2026-09-27, `TK108`).**
  `parent: [folder#member]` / `[folder:*#member]` under `x from parent` is a parse refusal in
  both parsers: `from` ignores a stored parent's predicate. Rewrite: `parent: [folder]` plus
  `parent_member: member from parent` (`tests/test_tk108_userset_tupleset_rewrite.py`).
- **Every refused schema shape says WHY and what to write INSTEAD, at the refusal (user
  instruction 2026-09-27).** A `# REFUSED SHAPE (<id>): <what>.` / `# WHY: ...` /
  `# INSTEAD: <DSL that parses in both parsers>` (or `none -- <reason>`) block sits directly
  above the `raise`, in EVERY parser that refuses it (product and oracle twin), enforced by
  `tests/test_refused_shape_comments.py`. Put a new refusal in a `_validate_*` / `_reject_*`
  function, or only review will catch it.
- **Identifiers** are validated on writes to `[A-Za-z0-9_./@+=-]` (1–256 chars). Reserved:
  a name may be `*` (wildcard sentinel), a subject predicate may be `...` (bare). Reads are
  lenient. **Declared names are held to the same charset at PARSE time (`P23`)** in both
  parsers and the JSON front end (`src/zanzibar/schema/parser.py::_validate_declared_name`,
  oracle twin of the same name); a relation name may not contain `.`. The two checked parsers
  must accept exactly the same schema texts (`tests/test_p23_parser_refusal_parity.py`), so a
  new refusal in one parser without its twin is red.
- **Object wildcards** (`folder:*`) have no DSL syntax — pass `object_wildcard_shapes` to
  `parse_openfga_schema` / `SetEngine`.
- **Wildcard extensions beyond OpenFGA warn** (`ASK-2`, user decision 2026-09-26: kept, but
  unproven). Wildcard usersets `[T:*#p]`, star tuplesets and object wildcards are outside
  `W4Fragment`, so `src/zanzibar/schema/compiler.py::derive_schema_info` emits
  `UnprovenExtensionWarning` on every construction path (`tests/test_unproven_extension_warning.py`); a bare `[T:*]`
  stays silent. **Do not propose the OpenFGA registry idiom to close that gap** (user
  decision 2026-09-29; why: `docs/architecture/decision-log.md` § "Wildcards beyond OpenFGA").
- **Set-engine ids** are recycled int32 (roaring is uint32); the `(type, name, predicate)`
  key is the stable surrogate. State is in-memory — `rebuild()` replays from `RelationTuple`.
- **Operational knobs** (all default to the historical behaviour):
  * `ZANZIBAR_PARANOIA=residue` — recommended in production (the runtime detector for the
    `ZT-P0-1` escalation class); it does NOT catch an I14 regression, only `full`/`fixpoint`
    do (`TK118`).
  * `ZANZIBAR_MAX_CLOSURE_FANOUT` (`0` disables) — a SYNC-ADMISSION bound only (`TK112`):
    every sync edge ADD is capped whatever it does to access, revocation-shaped adds under
    `but not` included, and the refusal (`ClosureFanoutExceeded`) is atomic across log, set
    engine and index. Do NOT reintroduce "revocations are exempt" (a sound exemption needs a
    global sign analysis). Edge REMOVALS are never capped. `ConnectedStore.catch_up` and the
    non-bulk `build_index` run inside `ReachabilityIndex.fanout_cap_suspended` (rows already
    committed are applied with a warning). Why: `docs/tk111-stall-aware-freshness-2026-10-02.md`.
  * Path counts past `src/zanzibar/graphindex/core.py::MAX_PATH_COUNT` are refused with
    `PathCountExceeded`, never suspended (`TK111`). On async that stalls the index, and a
    stalled index is not SERVED: untokened reads fall back to the set engine (`check`) or
    refuse with `IndexStalled` (lookups) — an availability loss, not a stale ALLOW.
  * `zanzibar.graphindex.outbox.prune_outbox` — manual retention, never auto-called; it keeps
    the head row so SQLite cannot recycle outbox ids under a held cursor.
  * `SetEngine.log_governed` — set by `TupleSource`; a direct `add_tuple` on a logged store
    raises `UnloggedWriteRefused` instead of silently diverging the source from the index.
- **Supported backends: SQLite (dev/test) and PostgreSQL (the server). MySQL is NOT
  supported** — don't reason about it, and don't leave InnoDB facts in comments (one was half
  the justification for a live fail-open, `docs/spec-deviations.md` 2026-07-27). **`READ
  COMMITTED` is the only accepted isolation level** — `TupleSource`/`ConnectedStore` raise
  `UnsafeIsolationLevel` at construction for anything else, SERIALIZABLE included. The
  dialect-specific surface is deliberately tiny and must stay that way:
  `src/zanzibar/graphindex/core.py::is_sqlite` + `take_row_write_lock`, and
  `src/zanzibar/connectedstore/source.py::assert_read_isolation`. New dialect branching goes
  *there*, not sprinkled through call sites or prose.
- **Concurrency**: `ReachabilityIndex._lock_store` (a `FOR UPDATE` store-row lock)
  serializes writers per store on PostgreSQL; it's a no-op on SQLite, which serializes
  writers itself (concurrent SQLite writers need retry on `SQLITE_BUSY` / node-creation
  `IntegrityError`). Use one `Session` per thread — never share one. **Multi-instance
  (HA):** writers take the source lock (`TupleSource._lock_source`, the `SchemaRecord` row)
  BEFORE the graph store lock (lock ordering), and `TupleSource.add/remove` catch the
  evaluator up under the lock (validate against current committed state; log ids commit in
  id order per store); replica readers tail via
  `catch_up_evaluator` (O(delta)).
- **Derived-relation exclusivity (I5)**: only the delta processor writes incoming direct
  edges on derived-public families (`WildcardIndex.processor_writes` flag); users write
  public names, `RuleSet.apply` routes them onto leaf families. A graph write on a boolean
  schema must run `DeltaProcessor.run_cascade(watermark)` in the same transaction
  (synchronous v1) — see
  `GraphBackend.apply` in `tests/test_matrix.py`.
- **TTU parents are STORED tupleset tuples**, never computed membership (oracle-pinned
  Zanzibar semantics; hence the direct-only tupleset rule above). Storage leaves are still
  split from rule-routed leaves on DERIVED relations, where a Direct arm's stored tuples must
  not mix with computed state.
- **Status lines inside `docs/history/` and `formal/history/` are FROZEN as-of-then.** Read
  them for METHOD, never for state; state lives in the tree (`task.py show <id>`) and in
  `formal/HANDOFF.md`.
- **Perf work & the Lean model.** The Lean proofs (`formal/`) verify *algorithm-twins* of
  the Python (`formal/CORRESPONDENCE.md` is the model↔code map). A behavior-preserving
  micro-optimization needs no Lean change. An optimization that **changes the modeled
  algorithm** (candidate pruning, cascade order, closure/residue update, a new fast path)
  makes the Lean definition describe dead code: update the Lean model and re-run
  `formal/verify.sh` (phased), or log the gap in `CORRESPONDENCE.md` §7. Don't let code and
  model drift unrecorded (§8). `verify.sh lean` resolves every `file::symbol` anchor in
  `CORRESPONDENCE.md`, so renaming a modelled function fails the gate until the map is
  updated — but that only proves the pointers resolve, not that the claims are true.
