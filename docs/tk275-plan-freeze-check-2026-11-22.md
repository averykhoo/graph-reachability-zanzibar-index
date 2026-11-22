# `TK-275` -- freezing closed-row ACTIVE-PLAN docs, and a lint check that holds the rule

FROZEN 2026-11-23 (session 2026-11-22a): TK-275 closed; below, the plan as it stood

**ACTIVE-PLAN, opened 2026-11-22 (session `2026-11-22a`) -- the body is provenance, not a living
status.** The census and design calls for `TK-275`'s NOW scope (row Log 2026-11-20a: freeze the
list-(c) docs, add a `handoff_lint` RED check keyed on the engine's closed state, sabotage it).
Parts (a) and (d) are `TK-307`'s. Live state is the row (`context-engine task show TK-275`),
never this file. Corrections append **dated at the top**. Freeze it when `TK-275` closes.

Provenance labels: **READ** = read first-hand by the task-owner agent this session; **RAN** = a
command it ran, output quoted; **REASONED**. Line numbers are not used (cite `file::symbol`).

## 1. The engine already has this rule, and cannot hold it here (READ)

- `context_engine.guards.liveness` (G-D4, engine pinned at `989982a`) reds an ACTIVE-PLAN doc
  whose window names only closed items, and `task close` refuses to close the last open item a
  plan names (`context_engine.guards.active_plans`). It reads only docs under `[guards] liveness`
  / `history` in `context.toml`, which list no plan doc in `docs/`.
- Pointing it at `docs/` fails twice: `context_engine.guards._named` matches canonical ids only
  (`TK-106`), and every pre-engine plan names the task.py alias (`TK106`), so each would be red
  as "names no board item"; and a listed directory makes every doc in it declare a state,
  which reds the undeclared docs that are `TK-307`'s open adjudication.
- **PROVISIONAL (agent, this session):** hold the rule in `scripts/handoff_lint.py` as the row
  planned, keyed on the FILE NAME (the `docs/<id>-<topic>-<date>.md` convention), aliases
  resolved, red only when every resolved row is closed; and read the declaration the way G-D4
  reads it (`context_engine.guards.declared`, mirrored as `handoff_lint._declared_liveness`),
  because `context-engine doc freeze` writes an UNBOLDED `FROZEN <date>` line, which the bold
  `handoff_lint._DECLARATION` would not see. Why not the window's ids: the TK120 rename note
  sits in the window of most of these docs, so window ids would be noise. Undo: delete the
  check; nothing else depends on it.

## 2. The census and the freeze (RAN, 2026-11-22 / 2026-11-23)

Method: every `.md` in `handoff_lint.PLAN_DOC_DIRS` whose file name's leading
`<letters><digits>-` tokens resolve to a task row (id or alias, `tasks/` frontmatter `state`),
declaration read as above. The 2026-10-13 list (c) held twelve docs; the re-measure found more
of the same class, and one (`tk185-...`) already frozen by `doc freeze` in an earlier session
(a bold-only census, the first one run here, misread it as still ACTIVE-PLAN).

Frozen this session with `context-engine doc freeze <doc> --note "<ids> closed; below, the plan
as it stood (banner applied late, under TK-275)"`, which logs an op line per doc:

- the row's list (c): `tk106-boolean-tuplesets`, `tk108-userset-tuplesets`,
  `tk126-ttu-target-boolean-name`, `tk70-detonation`, `tk73-cascade-quiesce-gc`,
  `tk78-offline-bootstrap-audit`, `tk83-star-intersection-fixture`, `tk87-swarm-churn`,
  `tk89-census-reproducibility`, `tk91-tk80-removal-coverage` (both rows closed),
  `tk92-bulk-rel-term`, `tk93-ensure-raw-seed-dependence`;
- found by the re-measure: `tk138-userset-self-relation`, `tk158-cheap-fanout-refusal`,
  `tk164-public-surface`, `tk166-foreign-token`, `tk179-strict-public-args-plan`,
  `tk182-lint-typecheck-plan`, `tk3-cascade-ran-mark`;
- found by the check itself on its first run (an UNBOLDED `ACTIVE-PLAN` the bold census could
  not see): `tk151-diataxis-plan`;
- found by the review agent (2026-11-23): `tk151-site-review`, which declares nothing in the
  window (its "ACTIVE-PLAN until the listed MUST items land" sits further down), so the check
  cannot see it; its row is closed, so it was frozen by hand the same way.

Not frozen: `r6-sizing-census` (its `R6` row is open), the three `p6-*` plans (`P6` open).

## 3. Out of scope, handed to `TK-307` (RAN, same census)

ACTIVE-PLAN docs whose file name names no row, so neither this check nor G-D4 sees them:
`adversarial-audit-2026-09-15`, `goal-census-2026-09-22`, `promote-next-triage-2026-10-03`,
`pypi-readiness-2026-10-07` and the `pypi-trial-*` docs. Their windows name only closed rows or
none (REASONED: most are stale, but which item each serves is a judgement, as in part (a)).
Also, under `formal/history/`, `echain-widening-plan-2026-07-28` and
`leaf-family-split-scope-2026-08-05` (ACTIVE-PLAN, named after no row; the review agent's
census). `tk151-fable-review` declares an unbolded FROZEN, which is fine. Recorded on
`TK-307` as a widening of its scope (task comment, 2026-11-23).

## 4. The check and its sabotage

`scripts/handoff_lint.py::check_active_plans_closed_rows`, appended to `CHECKS`; pinned by
`tests/test_handoff_lint_active_plans.py`, whose docstring carries the sabotage record verbatim
(seventeen mutants of the check, each killed, the last seven added after the review found
those reader branches unpinned; plus the subject: `tk70-detonation` read as before its
freeze gives exactly one failure). `tests/test_handoff_lint_b_prime.py`'s positional pin grew
by the one appended name. No test in that module reads the live docs/ tree: docs/*.md is out of
the code scope the pytest tiles are keyed on (`scripts/gate_status.py::_in_scope`), so such a
test would stay cached green after a doc edit; the live property is held by `verify.sh lean`,
which runs `scripts/handoff_lint.py` (REASONED from `_in_scope`, READ). `docs/README.md` sec 3 now says what is and is not enforced.
