# CLAUDE.md — graph-reachability-zanzibar-index

Zanzibar-style relationship/permission indexing. Two evaluation backends with **identical
semantics but opposite cost models** (a memoization spectrum), pinned together by a shared
independent reference oracle. Both backends support boolean operators (`and` / `but not`):
the set engine natively, the graph index via derived predicates maintained by a stratified
IVM delta processor.

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
- **Start with `python scripts/task.py board`** — the session-start view, printed as a
  QUERY over the file-per-task tree in `tasks/` (bounded by `task.py::BOARD_MAX_LINES`,
  asserted by a test, never restated as prose here). It opens with the `## Banner`
  section of [`HANDOFF.md`](HANDOFF.md), which is now a **one-hop note** (≤60 lines:
  banner, still-owed, where to go next — no row table, no item blocks). `show <id>` is
  the per-item read (Log newest-first), `ready` lists unblocked work, `list` is capped
  at 20 rows and says so. This file (`CLAUDE.md`) is the durable contract; the tree is
  what changes session-to-session. At end of session write back via the Rhythm in
  [`docs/README.md`](docs/README.md) §7 (session-log entry, banner, tree ops).
- **The tree is the SOLE authority on open work since the 2026-09-06 cutover (Phase B′,
  user go 2026-09-06d).** The 2026-08-23 → 2026-09-06 trial ran the tree and the board
  in parallel as treatment and control; DELETE was taken off the table 2026-08-30 and
  the decision on 2026-09-06c was cutover. The cutover commit is ONE revertable commit
  (its message carries the `git revert` line); the spec and its landed status table are
  [`docs/tree-sole-authority-spec-2026-08-29.md`](docs/tree-sole-authority-spec-2026-08-29.md)
  (FROZEN), the trial's protocol and verdict
  [`docs/tasktool-trial-protocol.md`](docs/tasktool-trial-protocol.md) (FROZEN).
  What changed at the cutover, so old runbooks do not mislead: `tasks/BANNER.md` is a
  tombstone (lint check 12 fails if it reappears); `task.py sync` and `ack` REFUSE
  (rc 2) and name their replacement; lint check 13 is retired and its number is never
  reused; `source_hash` is frozen; `HANDOFF.md`'s cap is 60 lines
  (`handoff_lint.py::MAX_LINES`). Nothing about the gate changed.
  * **Every re-rank, close, and progress note goes through an op with `--session <key>`**
    — `promote` / `touch` / `close -m` / `set <id> brief` / `comment <id> -m` — never a
    hand edit of a task file's frontmatter. Full schema and op contract:
    [`docs/tasktool-spec.md`](docs/tasktool-spec.md). The gitignored `.scratch/tasktool/`
    build directory (and the `migrate.py --rebuild` landmine this bullet used to warn
    about) was **DELETED 2026-09-07**; what it proved — decisions absent from the spec,
    the cited evidence sections, and nine findings that were never fixed — is
    [`docs/history/tasktool-scratch-archive-2026-09-07.md`](docs/history/tasktool-scratch-archive-2026-09-07.md).
  * **Close the loop in your session-log entry with two literal lines** (enforced:
    `handoff_lint.py::check_session_receipt` makes the `lean` phase RED without them):
    the output of `python scripts/task.py lint`, and `read: board only` /
    `read: board + note` — an honest self-report of what you actually read to start
    work. The lint line is the visible hole if the tree was left unlinted; the read line
    is the only way to learn whether the query actually REPLACED the file read. **A third
    line is conditional** (`TK96`, 2026-09-27): while any open `ASK-*` row sits at `NEXT`
    (or `NOW`), raise each with the user in chat and write `asked: ASK-<n>[, ASK-<m>]` naming all of
    them — `asked: none` is red then (`python scripts/task.py asks` lists them).
  * ⚠ **A `close -m` / `comment -m` message with backticks inside DOUBLE quotes is
    command-substituted by the shell** — the backticked text vanishes silently. Use single
    quotes, or a heredoc, or a file.
  * Correctness of the tool is pinned by `tests/test_tasktool.py`, INSIDE the gate since
    2026-08-29d (the sabotage cases are permanent tests; the historical record is
    [`docs/history/tasktool-proof-2026-08.md`](docs/history/tasktool-proof-2026-08.md)).
- **SCOUTING IS A DELIVERABLE, NOT A BYPRODUCT** (rule added 2026-09-13g, user instruction:
  *"hand off whatever state you have … so the next session doesn't need to do so much
  scouting"*). Measuring the tree is the expensive half of an `L`-sized item — cone counts,
  call-site censuses, symbol/line maps, go/no-go adjudications, "which of these seven claims
  survives first-hand". A session that measures and then only *acts* has thrown the
  measurement away, and the next session pays for it again. So:
  * **The measurement lands in a TRACKED file the same hour it is made**, before the edit it
    was made for. Not `.scratch/`, not a subagent report you summarised in chat, not the task
    row's prose — a file. The shape is an **ACTIVE-PLAN** doc (`docs/README.md` §3),
    `docs/<id>-<topic>-<YYYY-MM-DD>.md`, corrections appended **dated at the top**, FROZEN when
    the item closes. The worked precedent is
    [`docs/p6-step3b-plan-2026-09-13.md`](docs/p6-step3b-plan-2026-09-13.md) — a nine-agent
    sweep reconciled first-hand, which turned "step 3b is three re-points" into an ordered
    fifteen-step map with the blockers named.
  * **Label every claim by provenance**: first-hand READ, REASONED, or UNVERIFIED, and say
    which agent/probe produced it. A subagent report is evidence, not a finding
    (§ Delegation) — an unlabelled one gets re-verified from scratch, which is the scouting
    done twice. Flag the not-yet-verified items *in place*, not in a footnote.
  * **Cite `file::symbol`, and date any line number.** Line numbers rot within one session
    (steps 1–2 of `P6` moved every `UsStarWrite.lean` cite in the plan above). A map whose
    anchors do not resolve sends the next session back to grepping.
  * **The task row is the index, the doc is the body.** Close with
    `task.py comment <id> --session <key>` naming the file, what LANDED, what BUILDS, what is
    RED, and the single next action. `show <id>` alone must be enough to resume.
  * **This applies to a session that runs out of room, not just one that finishes.** Before
    clearing context or stopping mid-item, write the state down first — a half-finished item
    with its map recorded is resumable; a finished measurement that was never written is lost.
- **Always run the gate before pushing.** Never push red or unverified: the phased
  `verify.sh` (`lean` → `conf-tile:1/5`…`5/5` → `tests-tile:1/4`…`4/4`) all `PASSED`
  (+ a fuzz sweep for an algorithm change). The cap-safe recipe is in
  [`docs/gate-runbook.md`](docs/gate-runbook.md); details under "Running things"
  below. **Push only when asked.**
- **COMMIT whenever the full gate is green and the session did work** (rule added
  2026-08-28b, user instruction). Not "only when asked" — that was the old rule, and it
  left green, gated, fully-recorded trees sitting uncommitted at session end, which is
  pure downside: a green tree is the cheapest possible resume point, and an uncommitted
  one is the easiest thing to lose. When `python scripts/gate_status.py` says
  **COVERED on this tree** and you changed something, commit it. Corollaries:
  * A green gate is the trigger, not a request. Do not wait to be asked.
  * "Did work" excludes a session that only read; it includes docs-only edits.
  * **Push is still opt-in and unchanged** — commit ≠ push.
  * If the gate is NOT fully green, the old rule stands: do not commit to make progress
    look like assurance. Say what is red and leave it.
  * ⚠ Editing any `*.md` changes the `t2a` tree id and stales the `lean` verdict (the
    pytest tiles key off `t2c`, which excludes `*.md`). So write the session records
    FIRST, then re-run `lean`, then commit — otherwise the commit's own banner is a
    claim the tree no longer supports.
  **As of 2026-07-27 `tests/` runs THROUGH `verify.sh`, not beside it.** It used to
  be "type `pytest tests/` and read the tail" — no count floor, no
  skipped/xfailed/xpassed parse, no exit-code assertion, no proof a tile collected
  anything. Bare `pytest tests/` is fine while iterating; it is not the gate.
- **The five standing footguns.** Each of these has bitten a session in this repo, and
  the first one has bitten three. They live here because `CLAUDE.md` is auto-loaded
  every session, so carrying them costs the reader nothing; the full write-ups are in
  [`docs/gate-runbook.md`](docs/gate-runbook.md).
  * ⚠ **An exit code piped through `tail`/`tee` reports the PIPE's status.** A genuinely
    FAILED phase then looks like exit 0 — and if it is followed by `&& <next phase>`,
    the chain continues happily past the failure. Bit 2026-08-10 (a `4 failed` run
    reported exit 0), and again on 2026-08-11 and 2026-08-14. Run
    `cmd > "$(mktemp /tmp/gate-XXXXXX.log)" 2>&1; rc=$?`, branch on `$rc`, and **read the
    `PASSED` line**.
    ⚠ **2026-09-16b generalises it past pipes: it is ANY trailing command in the chain,
    and `rc=$?` does not save you if something runs after it.** A backgrounded
    `pytest > "$L" 2>&1; rc=$?; echo "rc=$rc"; grep -E ... "$L"` was reported by the harness
    as **"exit code 0"** while the log ended `1 failed, 29 passed` — the task's status was
    GREP's (it matched nothing it considered an error), not pytest's. The captured `rc` was
    correct and never looked at. So: **put the verdict where you will READ it, not only
    where you compute it** — `echo` the branch (`[ $rc -eq 0 ] || echo RED`) rather than
    trusting any exit status reported by a wrapper, and read the log's last line every time.
    This is the fourth distinct mechanism for the same lie.
    The 2026-09-08b variant runs the OTHER way — `EXIT=0` under a log ending `25 failed`
    — because looping phases in one command lets the harness kill the shell while its
    `pytest` child survives, and the orphan then writes the next phase's log. **One phase
    per command**; on any exit-code/log disagreement, check for a stray interpreter and
    re-run alone to a fresh log before believing either.
    ⚠ **The 2026-09-10 variant needs neither a pipe nor an orphan: two runs and one
    filename.** `EXIT=0` under a log ending `60 failed`, with no stray interpreter and no
    loop — two overlapping runs both redirecting into the FIXED `/tmp/p.log` this file
    used to prescribe, so the caller got the passing run's honest `rc` beside the failing
    run's tail. **A fixed log path is a shared resource; use `mktemp`.** `verify.sh` now
    takes an exclusive run lock (`scripts/gate_lock.py`) and a second concurrent run
    refuses nonzero in under a second, so this cannot recur silently — but the same
    reasoning applies to any command you run twice. Note what this one cost: it was filed
    as a hole in `verify.sh`'s exit-code guard, and the guard was fine.
  * ⚠ **`HYPOTHESIS_SEED=N` does nothing** — hypothesis never reads that variable, so a
    "multi-seed sweep" written with it runs the SAME seed every time. Only
    `--hypothesis-seed=N` works; `tests/conftest.py` now refuses the env var outright.
  * ⚠ **A divergence gets a positive pin, never an xfail** — an xfail is itself a
    failure that passes. The declared budget knob is `MAX_TESTS_XFAILED`, and
    `formal/verify.sh` is the only place its value belongs (do not restate it in prose;
    `docs/gate-runbook.md` carried a wrong value for three weeks by doing so).
  * ⚠ **`MIN_CONF_ALL` / `MIN_TESTS_ALL` have ZERO headroom** — they are set equal to
    the live collected counts, so deleting a single test turns the gate red. Adding
    tests is always free; lowering a floor must be a deliberate, reviewed edit.
  * ⚠ **On a red gate, snapshot with a TEMP INDEX — never `git stash` or
    `git checkout --`.** `core.autocrlf` rewrites LF → CRLF on the way back out, so the
    "restored" tree is not the tree you saved and the next diff is noise you then have to
    reason through (trap (ee), scope doc §11.13). Promoted here from `HANDOFF.md`'s banner
    on 2026-09-19d: it is durable and repo-wide, and the banner is volatile by design.
- **Shared doc conventions live in [`docs/README.md`](docs/README.md)** — the liveness
  states (LIVING / FROZEN / ACTIVE-PLAN) and the frozen banner, the session-ledger entry
  format, the citation-key rules (ids, `file::symbol`, archive-section form), the
  priority vocabulary (`NOW`/`NEXT`/`LATER`/`HOLD`/`SOMEDAY`) and its capacity budgets,
  and the one-home-per-statement routing table. Read it before restructuring any doc.
- **Two record-keeping rules, promoted from the board 2026-08-20b because they are
  repo-wide.**
  * ⚠ **`.scratch/` is gitignored — anything recorded ONLY there is already lost.** Board
    row `P7`'s entire cost analysis survived only in `.scratch/` and had to be transcribed
    into `PROOF_STATUS.md` (2026-08-16) to keep the item resumable. It recurred on
    2026-08-20b in a worse form: two sabotage runs (`sab_s4`/`sab_s5`), one of them a
    **green sabotage** proving a shipped property was unpinned, existed only as
    `.scratch/*.log` and appeared in no docstring, no `PERF_ANALYSIS.md` entry, and no
    report — a reviewer found them by listing the directory. **If a run is evidence, it
    goes in a tracked file the same hour.**
  * ⚠ **A trap must cite a symbol that EXISTS.** The board carried "do not extend
    `test_fixture_earns_its_place`" for weeks; no such test has ever existed, so the trap
    was unenforceable. Cite `file::symbol` and grep it before writing it down. The same
    applies to counts: on 2026-08-20b a `26 passed` summary line from a THREE-module run
    was written into four docstring sites as one module's test count (it collects **12**).
    Get a count from `pytest <target> -q --collect-only`, never from a run's tail.

## Delegation — the repo-specific half
**The rule itself lives in `~/.claude/CLAUDE.md` § Delegation and is NOT restated here**
(deduplicated 2026-09-20e, user instruction — the two copies were ~67% the same text and
had already drifted in wording). The underlying preference is the user's, **stated
2026-08-28**, and the `ultracode` / `Workflow` standing approval is **2026-09-20d** — both
dates are load-bearing and are kept here because the machine-wide file states the rule
without this repo's provenance. That section is auto-loaded every session and carries:
the purpose (context, never parallelism) and the test for when to delegate; verdicts plus
`file::symbol` instead of file dumps; standing permission for read-only agents; standing
approval for `ultracode` / the `Workflow` tool as of 2026-09-20d; the requirement that
every delegated unit persists its own output incrementally before returning, one file per
agent; the `.scratch/` audit-and-sweep procedure; and that delegation does not transfer
judgement. Read it there. What follows is only what is true HERE and nowhere else.

- **The sizing claims in this repo have come in LOW, repeatedly — that is why the
  `file::symbol` rule is not optional.** `P3`'s re-verified "~123 sites / 7 files" budget
  was live **~136 / 8** on 2026-08-28, and the gap was the pin module its own session had
  just created. An agent that returns prose has spent the tokens without buying the
  certainty.
- **`.scratch/` here is governed by § SCOUTING IS A DELIVERABLE above, which is stricter
  than the machine-wide rule**: a measurement lands in a TRACKED file the same hour, in the
  ACTIVE-PLAN shape, labelled first-hand READ / REASONED / UNVERIFIED. The machine note says
  "copy evidence out of the crash bag"; this repo additionally says where it goes and what
  it must be labelled.
- **The things that get verified FIRST-HAND before an agent's report is written down are
  named here**: anything headed for `formal/history/` (append-only), a gate pin, a golden,
  or an `audited_theorems.txt` entry. Contradicted reports get reconciled, not averaged.
- ⚠ **One file per agent is the 2026-09-10 gate trap one level up** — two writers on one
  filename is exactly how a passing run's exit code ended up beside a failing run's log.

## Running things
- Conda env named after the folder: `graph-reachability-zanzibar-index`; on this machine it
  lives under `C:/Users/user/anaconda3/envs/...`.
  **`ZANZIBAR_PY` is NOT required, and this bullet said it was until 2026-08-30.** It read
  "`formal/verify.sh` hardcodes the `avery` path too, so override it with `ZANZIBAR_PY`".
  `verify.sh` stopped hardcoding it under `ZT-P2-6`: `resolve_py` (`:297-320`) tries
  `$HOME`- and `$CONDA_PREFIX`-derived locations FIRST, keeps the `avery` path only as one
  later candidate, and accepts a candidate only if it can import the project's deps.
  `ZANZIBAR_PY` still wins outright when set — it is an override, not a prerequisite.
  Evidence: all ten gate phases were run green on 2026-08-30 with `ZANZIBAR_PY` unset.
  ⚠ **The Lean toolchain is the one that is not on `PATH`** — `lake`/`lean` live in
  `~/.elan/bin`, which `verify.sh:123` prepends for you. Building by hand needs
  `export PATH="$HOME/.elan/bin:$PATH"` first, or `lake` is simply not found.
- The full suite is the gate (`tests/` + `formal/conformance/`; more in `tests/` with a
  PostgreSQL DSN configured). These counts ARE enforced — `verify.sh` carries `-ge` floors
  on both (`MIN_TESTS_ALL` / `MIN_CONF_ALL`), so adding tests is always free and losing
  coverage is loud.
  **★ No figures here, deliberately (2026-08-14).** This bullet used to read "**1227
  tests** … `tests/` **762** + `formal/conformance/` **465**" as re-measured 2026-07-29.
  By 2026-08-14 the live floors were **879** and **494** — i.e. the durable contract
  understated the suite by hundreds of tests, and anyone sizing a coverage change off it would
  have mis-planned. That is `ZT-P3-5` recurring in the one file that is supposed to be
  stable. **Live figures live in ONE machine-checked place**, `formal/FINAL_REVIEW.md`'s
  generated counts block (gated by `verify.sh` step 4e; regenerate with
  `python -m formal.conformance.doc_counts --generate`). Read them there, and re-measure
  with `pytest <dir> -q --collect-only` before quoting one anywhere.
- **The gate = `bash formal/verify.sh`**, and it now covers `tests/` too. The one-shot
  blows the harness's ~10-min command cap, so it takes a **phase arg** and each phase
  fits: `lean` → `conf-tile:1/5`…`conf-tile:5/5` → `tests-tile:1/4`…`tests-tile:4/4`.
  The tiles are a structural partition (collected fresh at run time, index mod K), so
  a new test file lands in exactly one tile with no list to update. Every phase
  asserts a count floor, a nonzero pass count, the pytest exit code, and zero
  `skipped`/`xpassed`/`deselected`; `xfailed` is zero for conformance and carries a
  declared budget for `tests/` (`MAX_TESTS_XFAILED`). `lean` additionally pins the
  audited theorem NAMES, the headline theorem STATEMENTS, and every
  `CORRESPONDENCE.md` symbol anchor. **Push only after all ten phases are green**
  (+ a fuzz sweep for an algorithm change). Legacy `conf-heavy`/`conf-rest` still work.
  **Each run appends a row to the gitignored `.gate-runs/ledger.tsv`** (phase, verdict,
  counts, and the tree it ran against) plus that phase's full output;
  `python scripts/gate_status.py` reports which phases are green **on the current
  tree**, so "did I already run the tiles?" is no longer a memory question. Details
  and the sabotage evidence: [`docs/gate-runbook.md`](docs/gate-runbook.md) §4.
- **The PostgreSQL leg is opt-in and therefore easy to think you ran.**
  `bash scripts/pg_local.sh start` prints a DSN; export it as `ZANZIBAR_TEST_DSN` to
  re-run the HA/concurrency modules against a real server plus
  `tests/test_postgres_ha.py`. Without a DSN that module is dropped at COLLECTION (not
  skipped — a tolerated skip is how coverage leaks out of a gate). `ZANZIBAR_PG_REQUIRED=1`
  turns a missing DSN into a hard error. Worth running for anything touching locking,
  watermarks, isolation or multi-instance state: it found three real bugs the first day.
- Deps: `sqlmodel`, `pytest`, `pyroaring` (set-engine default bitmap backend),
  `hypothesis` (property/stateful fuzzing); `psycopg2-binary` for the server leg only.
  A missing `pyroaring` used to silently halve the validation matrix — collection now
  refuses to start (`tests/conftest.py`), and so does `verify.sh`'s preflight.

## Layout / mental model
- **`index_v4/`** — the graph index. `ReachabilityIndex` (core.py) materializes the full
  transitive closure as ref-counted edges, so `check` is O(1); `WildcardIndex`
  (wildcard.py) is the wildcard-aware façade adding materialized `*` bridges and the
  derived-relation read path (edge probe + residue). **Boolean operators are supported
  as derived predicates**: `processor.py` (the delta processor: reconcile + per-stratum
  cascade over the outbox), `outbox.py` (transactional `DeltaOutboxV1` stream +
  watermark/drain helpers — write paths return None, deltas are rows), `invariants.py`
  (I1–I12 checker, paranoia mode wiring, §8.3 delta-scoped verifier), `models.py`
  (adds `EdgeV4.derived`, `ResidueV1` symbolic `(stars, neg)` state). **Offline bulk
  bootstrap for `build_index`**: `bulk_build.py` (P13/N18 bulk closure builder —
  direct in-memory closure construction) with `bulk_backfill.py` (R4-BF in-memory
  boolean Phase-D backfill).
- **`setengine/`** — the set engine. Stores only raw tuples (`TupleV1`), builds no
  closure, computes memberships on the fly with bitmap algebra, and **supports `and` /
  `but not`**.
  - `setops.py` — the pluggable `SetOps` seam: `RoaringSets` (default) / `PySets`. Never
    `isinstance`-check the underlying set type.
  - `memberset.py` — the star-closed `MemberSet` (`pos` / `stars` / `neg`) algebra.
  - `engine.py` — `SetEngine`: a reference-counted `Interner` (recycled int32 ids),
    `NodeSets`, `member_of`, `check` / `expand` / `lookup`, and `rebuild()` (replay from
    `TupleV1`).
- **`zanzibar_utils_v1.py`** — shared schema layer. Recursive-descent parser →
  `SchemaAST` (`Direct` / `Computed` / `TTU` / `Union` / `Intersection` / `Exclusion`);
  `compile_ruleset` produces the graph index's Filters/Rules **plus, for boolean
  (tainted) relations, the AOT derived-predicate artifacts** (`RuleSet.compiled`:
  plans, namespace, strata, fan-out tables; leaf routing via `RewriteFilter`s;
  `unparse_schema_ast` round-trips the AST). `UnsupportedByGraphIndex` survives only
  for scope rejections (object wildcards on derived relations, wildcard usersets over
  derived relations) and via `enable_boolean=False`; derived-dependency cycles raise
  `ValueError`. `SchemaInfo`; `validate_write_identifiers`; `.` is reserved in declared
  relation names (leaf predicates are `<relation>.<index>`). `w4_fragment_report` is the
  opt-in, non-raising per-field report of whether a (schema, store) is inside `W4Fragment`,
  the scope of the headline theorems. It is a mirror of the Lean decider and is
  differential-pinned to it (`formal/conformance/test_conformance_fragment.py`), so fix the
  Python, not Lean, on a red.
- **`tests/oracle.py`** — independent reference oracle (pointwise, boolean-aware).
  **Independence contract:** it imports nothing from the backends and parses the DSL
  itself, so one parser bug can't corrupt both sides of the validation matrix.
- **`connectedstore/`** — the composed system (Zanzibar/Leopard split): `TupleV1` +
  permanent `TupleLogV1` = source of truth, graph index = materialized view.
  `TupleSource` (admission-validated writes returning log-id freshness tokens),
  `advance_index` (THE apply step — sync inlines it, async loops it via
  `ConnectedStore.catch_up`), `build_index` (offline bootstrap), `SchemaV4`
  (write-once schema source; compiled artifacts are cache). Composition layer only:
  it imports both backends, they never import it. Schemas are static — a new schema
  means a new store/index.
- **`legacy/`** — superseded predecessors v1–v3 (v1 in-memory; v3 the DB closure design,
  carrying a documented concurrency note that points at the v4 fix). Runnable
  documentation only — don't build on them; live code still imports `legacy.index_v1.
  MultiSet` and `legacy.index_v2.Node`.
- **Docs**: start at `docs/architecture/overview.md` (module map + pointers; the other
  architecture files cover the graph index, derived predicates, verification, and the
  decision log). Full design specs live in `docs/specs/` — code comments cite them by
  section: bare "spec §N" in `index_v4/*` → wildcard-materialization-spec.md, in
  `setengine/*` → set-engine-spec.md; "boolean spec §N" → graph-boolean-ivm-spec.md.
  Implementation divergences: `docs/spec-deviations.md`. Where a spec and the code
  disagree on a name, the code wins.

## Testing conventions
- The **validation matrix** (`tests/test_matrix.py`) is what pins "same semantics":
  handwritten expectations · oracle · set engine · graph index, compared over a full query
  grid, under **both** `SetOps`. Boolean schemas run **4-way** (graph included, processor-
  maintained, I9-audited per op).
- The **ParityEngine** (`tests/parity.py`) is the default engine for integration-style
  tests: every op fans out to all backends with unanimity, I12, and full-grid oracle
  parity asserted internally. **Paranoia mode** (default ON via `make_wildcard_index`)
  runs the invariant checker + delta-scoped verifier inside every commit; pass
  `paranoia=False` in benchmarks or when a test corrupts state on purpose.
- The **hypothesis campaign** (`tests/test_hypothesis.py`): metamorphic schema pairs,
  add/remove row-multiset restoration, permutation invariance, cascade replay-from-zero,
  generated-schema round-trips, and a stateful ParityEngine machine. Profiles: `ci`
  (default) / `HYPOTHESIS_PROFILE=deep` locally.
- Property tests reuse a shared candidate pool + grid (`tests/test_wildcard_property.py`).
- **`tests/test_lookup_oracle.py` is the lookup-surface oracle gate**: it composes
  `oracle.check` into brute-force reference lookups and pins `lookup` /
  `lookup_reverse` / `expand` on both backends. **Any strict xfail there pins a genuine
  divergence** — fix the surface and then flip the xfail; never relax the properties
  (how X1–X4 were closed; see `docs/spec-deviations.md` 2026-07-12/13).
- **Never edit a golden or oracle result just to make a refactor pass** — the oracle and
  goldens ARE the behavioral spec. A missing golden is now a hard FAIL, not a silent
  regeneration; regenerate deliberately with `ZANZIBAR_UPDATE_SNAPSHOTS=1`.
- **An assurance step that fails by PASSING is this project's house failure mode, and
  the response is a STANDARD PROCEDURE: [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md).**
  Read it before adding any test, floor, assertion, pin, or gate phase. It carries the
  protocol (break the narrowest *plausible* weakening, not an obvious catastrophe),
  the requirement to control your *instrument* as well as your subject, the durability
  ranking (make the sabotage a permanent test > derive the expectation > a floor with
  provenance > a docstring), and what counts as evidence (the literal observed output,
  in the test's docstring and the commit message). The rest of this bullet is the
  historical case for why it is mandatory. It
  has now recurred often enough to be a rule rather than an anecdote: a `HYPOTHESIS_SEED`
  sweep that ran the same seed six times; an axiom audit that counted reports without
  checking which theorems; a matrix that silently halved when `pyroaring` was missing; a
  property test that could `continue` past all twelve of its steps; a whole test suite
  outside the gate; a `SERIALIZABLE` isolation level accepted on the strength of a
  comment about a database this project does not support. **When you add a check,
  sabotage the thing it guards and watch it go red before you believe it.** When you
  find one of these, prefer a mechanical refusal over a doc warning — the next person
  will not read the doc. And prefer converting an `xfail` into a positive pin: an xfail
  is itself a failure that passes, which is why `verify.sh` budgets them explicitly
  (`MAX_TESTS_XFAILED`) instead of tolerating them silently.

## Gotchas / invariants
- **Schemas must be self-consistent (user decision 2026-09-26, `ASK-1`).** Both parsers
  refuse a dangling relation reference (computed ref, TTU tupleset, TTU target,
  `[T#P]`) and any cycle of computed / TTU-tupleset references
  (`zanzibar_utils_v1.py::_validate_ast_consistency`, oracle twin
  `tests/oracle.py::_validate_consistency`). Recursion through stored tuples (nested
  groups, `x from parent`) stays legal; bare restriction types are not checked. A test
  that needs "graph refuses, set engine accepts" uses a derived cycle through a TTU
  TARGET, the only form left for `_stratify`. The non-raising reports, the conformance
  encoder and grammar tests read `_parse_schema_ast_unchecked` /
  `oracle.parse_schema_ast_unchecked`, not the checked parse. Map:
  `docs/ask1-schema-self-consistency-2026-09-26.md`.
- **A `from`-tupleset must be DIRECT-ONLY (user decision 2026-09-26, `TK106`), as in
  OpenFGA.** The relation after `from` may only be Directs or a union of Directs (wildcards
  allowed); both parsers refuse the rest at parse time, tainted or not
  (`zanzibar_utils_v1.py::_validate_tuplesets_direct`, oracle twin
  `tests/oracle.py::_validate_tuplesets_direct`). `from` walks STORED tuples, so a boolean or
  computed arm there was silently ignored. The rewrite is `parent_link: [<types>]`, used by
  the `from`. Consequence: a tupleset is never tainted, so `PDerivedTuplesetTTU` /
  `derived-tupleset-ttu` and the processor's `derived_stored_*` helpers are unreachable from
  a checked parse. Map: `docs/tk106-boolean-tuplesets-2026-09-26.md`.
- **A tupleset may not restrict to a userset (user decision 2026-09-27, `TK108`).**
  `parent: [folder#member]` / `[folder:*#member]` under `x from parent` is a parse refusal in
  both parsers (same functions as `TK106`): `from` ignores a stored parent's predicate, so
  the `#member` was silently dropped. Rewrite: `parent: [folder]` plus
  `parent_member: member from parent`, pinned exact in
  `tests/test_tk108_userset_tupleset_rewrite.py`.
- **Every refused schema shape says WHY and what to write INSTEAD, at the refusal (user
  instruction 2026-09-27).** A `# REFUSED SHAPE (<id>): <what>.` / `# WHY: ...` /
  `# INSTEAD: <DSL that parses in both parsers>` (or `none -- <reason>`) block sits directly
  above the `raise`, in EVERY parser that refuses it (product and oracle twin). Adding a
  refusal without one is red: `tests/test_refused_shape_comments.py` (in-scope raises,
  WHY+INSTEAD per block, zero-headroom per-file floors `MIN_HEADERS`). Its limit is in its
  docstring: a plain `ValueError` outside a `_validate_*` / `_reject_*` function is only
  caught by review, so put a new refusal in such a function.
- **Identifiers** are validated on writes to `[A-Za-z0-9_./@+=-]` (1–256 chars). Reserved:
  a name may be `*` (wildcard sentinel), a subject predicate may be `...` (bare). Reads are
  lenient (an out-of-charset name just never matches).
- **Object wildcards** (`folder:*`) have no DSL syntax — pass `object_wildcard_shapes` to
  `parse_openfga_schema` / `SetEngine`.
- **Wildcard extensions beyond OpenFGA warn** (`ASK-2`, user decision 2026-09-26: kept, but
  unproven). Wildcard usersets `[T:*#p]`, star tuplesets and object wildcards are outside
  `W4Fragment`, so `zanzibar_utils_v1.py::derive_schema_info` emits
  `UnprovenExtensionWarning` on every construction path; a bare `[T:*]` stays silent.
  `pytest.ini` ignores it suite-wide; `tests/test_unproven_extension_warning.py` pins it.
  **Do not propose the OpenFGA registry idiom to close that gap** (user decision
  2026-09-29): it is a hand-maintained `*`, fail-open under `but not` when a registration
  is missed, and is not supported as a substitute. Why:
  `docs/architecture/decision-log.md` § "Wildcards beyond OpenFGA".
- **Set-engine ids** are recycled int32 (roaring is uint32); the `(type, name, predicate)`
  key is the stable surrogate. State is in-memory — `rebuild()` replays from `TupleV1`.
- **Operational knobs added 2026-07-27** (all default to today's behaviour):
  `ZANZIBAR_PARANOIA=residue` — recommended in production, the runtime detector for the
  `ZT-P0-1` escalation class, ~+5% on writes. `ZANZIBAR_MAX_CLOSURE_FANOUT` (default
  100,000, `0` disables) — per-write closure fan-out cap; **adds and node-adds only,
  removals are exempt** because a cap that can refuse a revocation is a fail-open, and
  an over-large region must stay shrinkable. ⚠ **That exemption does not hold in two
  admitted cases (`TK112`, reproduced 2026-09-27d):** under `but not` a revocation is an
  ADD on the subtrahend leaf and is capped, and on the async schedule a capped row stalls
  every later row, removals included. **Since 2026-10-02b (`TK111`) a stalled index is no
  longer SERVED**: `ConnectedStore.catch_up` records the stall on the cursor row
  (`IndexCursorV1.stalled_after`), and untokened reads then fall back to the set engine
  (`check`) or refuse with `IndexStalled` (lookups). So the async case is an availability
  loss, not a stale ALLOW. `ZANZIBAR_PARANOIA=residue` also does not catch an
  I14 regression; only `full`/`fixpoint` do (`TK118`). `index_v4.outbox.prune_outbox` — manual
  retention, never auto-called, and it keeps the head row so SQLite cannot recycle
  outbox ids under a held cursor. `SetEngine.log_governed` — set by `TupleSource`, makes
  a direct `add_tuple` on a logged store raise `UnloggedWriteRefused` instead of
  silently diverging the source from the index.
- **Supported backends: SQLite (dev/test) and PostgreSQL (the server). MySQL is NOT
  supported** — don't reason about it, and don't leave InnoDB facts in comments; one
  such fact was half the justification for a live authorization fail-open (see
  `docs/spec-deviations.md` 2026-07-27). PostgreSQL is the only server the gate
  exercises: `bash scripts/pg_local.sh start` then `ZANZIBAR_TEST_DSN=<dsn> pytest
  tests/test_postgres_ha.py` (skips without a DSN; `ZANZIBAR_PG_REQUIRED=1` makes a
  missing one a hard error instead of a silent green). **`READ COMMITTED` is the only
  accepted isolation level** — `TupleSource`/`ConnectedStore` raise
  `UnsafeIsolationLevel` at construction for anything else, SERIALIZABLE included.
  The dialect-specific surface is deliberately tiny and must stay that way:
  `index_v4/core.py::is_sqlite` + `take_row_write_lock`, and
  `connectedstore/source.py::assert_read_isolation`. New dialect branching goes
  *there*, not sprinkled through call sites or prose.
- **Concurrency**: `ReachabilityIndex._lock_store` (a `FOR UPDATE` store-row lock)
  serializes writers per store on PostgreSQL; it's a no-op on SQLite, which
  serializes writers itself (concurrent SQLite writers need retry on `SQLITE_BUSY` /
  node-creation `IntegrityError`). Use one `Session` per thread — never share one.
  **Multi-instance (HA):** writers take the source lock (`TupleSource._lock_source`,
  the `SchemaV4` row) BEFORE the graph store lock (lock ordering), and
  `TupleSource.add/remove` catch the evaluator up under the lock (validate against
  current committed state; log ids commit in id order per store); replica readers
  tail via `catch_up_evaluator` (O(delta)).
- **Derived-relation exclusivity (I5)**: only the delta processor writes incoming direct
  edges on derived-public families (`WildcardIndex.processor_writes` flag); users write
  public names, `RuleSet.apply` routes them onto leaf families. A graph write on a
  boolean schema must run `DeltaProcessor.run_cascade(watermark)` in the same
  transaction (synchronous v1) — see `GraphBackend.apply` in `tests/test_matrix.py`.
- **TTU parents are STORED tupleset tuples**, never computed membership (oracle-pinned
  Zanzibar semantics). That is why a tupleset must be direct-only since `TK106`
  (2026-09-26, the bullet above): a TTU over a derived tupleset used to be silently empty
  or silently ignore its boolean arm, and is now a parse refusal. Storage leaves are still
  split from rule-routed leaves on DERIVED relations, where a Direct arm's stored tuples
  must not mix with computed state.
- **Never edit a golden/oracle result to make a refactor pass** — and the compiled-
  RuleSet snapshots (`tests/snapshots/`) are the byte-identity gate for untainted
  compilation.
- **Status lines inside `docs/history/` and `formal/history/` are FROZEN as-of-then.**
  A "still open" / "N sorries" / "next lemma is X" in a dated history file was true on
  its date and nothing updates it. Read them for METHOD, never for state; state lives in
  the tree (`task.py show <id>`) and in `formal/HANDOFF.md`. (Promoted from `HANDOFF.md`
  "Standing traps" at the 2026-09-06 cutover — the note carries no trap list.)
- **Perf work & the Lean model.** The Lean proofs (`formal/`) verify *algorithm-twins*
  of the Python (`formal/CORRESPONDENCE.md` is the model↔code map). A behavior-preserving
  micro-optimization needs no Lean change (the differential matrix + hypothesis +
  conformance are the net). But an optimization that **changes the modeled algorithm**
  (candidate pruning, cascade order, closure/residue update, a new fast path) makes the
  corresponding Lean definition describe dead code — update that Lean model and re-run
  `formal/verify.sh` (phased, per gate-runbook §2), or log the gap in
  `CORRESPONDENCE.md` §7. Don't let code and model drift unrecorded
  (`CORRESPONDENCE.md` §8). Since 2026-07-27 `verify.sh lean` also resolves every
  `file::symbol` anchor in `CORRESPONDENCE.md`, so RENAMING a modelled function now
  fails the gate until the map is updated — the map can no longer rot silently, but
  it still only guarantees the pointers resolve, not that the claims are true.
