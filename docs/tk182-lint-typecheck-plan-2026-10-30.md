# TK182 -- ruff + a type checker in the gate (2026-10-30)

> **ACTIVE-PLAN** (`docs/README.md` sec 3). User, 2026-10-30b: "including lint (ruff?) and mypy
> (why not pyrefly) would be great, let's get that all done before 0.1.2". Release row `TK178`
> depends on this. Corrections go at the top, dated. FROZEN when `TK182` closes.

## 2026-10-30b -- outcome

- ruff + mypy clean over the repo (`scripts/lint_gate.py`, `verify.sh lean` step 4h; pins in
  pyproject `lint` extra + requirements.txt; `rc=0 | lint + type check: clean`). Sabotage L1-L3
  red (type error, unused import, pin/installed mismatch): tails in `scripts/lint_gate.py`.
- Correction to the measurement below: "174 errors in invariants.py" counted mypy OUTPUT LINES
  (notes included); the true error count there was 19 (agent mypy-A). The per-file split is
  likewise lines, not errors.
- Fixes by agents mypy-A/B/C and ruff-rest (reports were in `.scratch/agents/`): annotations,
  `sqlmodel.col()`, documented casts, `core.py::persisted_id` (a typed `row.id`), cache
  sentinels as a private enum compared with `is`, renames, default-arg loop binding,
  `zip(..., strict=True)` where pairs are equal by construction. 7 `# type: ignore` with codes
  (5x sqlmodel `select()` with >4 columns, 1 bulk_build same, 1 dynamic attribute).
  No real bug found. Possible latent one noted (UNVERIFIED, agent mypy-C):
  `schema/compiler.py::_node_removal_fence` reads `rf.then_pattern.object_type` without a
  None check; the compiler never emits a Rule with `then_pattern=None` (typed with a cast).
- Anchor content pin: 69 anchored bodies changed. Reviewed by agent anchor-review (each HEAD
  vs working-tree body via claim_rot's own `_py_body`, cited rows read): 0 behaviour changes,
  0 rows false; one stale quote (row 427, `r.id` -> `persisted_id(r)`) updated. Session
  first-hand spot checks: no `==` on `_MISSING`/`_UNCACHED` in core.py; `settle_keys` rename
  consistent in `DeltaProcessor._run_cascade`. Pin regenerated (`claim_rot.py --generate`).

## Measurements (first-hand RUN, 2026-10-30b)

Tools installed with `pip install --target .scratch/tools` (NOT into the env, which a gate run
was using): ruff 0.17.3, mypy 2.4.1, pyrefly 1.4.0, pyright 1.1.414. Target `src/zanzibar`
(35 source files), env interpreter for third-party resolution, no project config.

| tool | findings on `src/zanzibar` | wall time |
|---|---|---|
| ruff, its 0.17 default rule set (broad: UP, I, SIM, RUF, B, ...) | 241 | ~instant |
| mypy, defaults | 275 errors in 22 files | 3.7 s cold, 0.3 s cached |
| pyrefly, defaults | 274 errors (+20 warnings hidden) | 0.4 s |
| pyright, defaults | 329 errors, 1 warning | 3.1 s |

mypy by code: arg-type 130, attr-defined 36, assignment 29, union-attr 22, index 13, misc 12,
operator 11, call-overload 9, others < 5. By file: `graphindex/invariants.py` 174 (the bulk),
`setengine/engine.py` 59, `graphindex/processor.py` 57, `graphindex/wildcard.py` 53,
`graphindex/bulk_build.py` 41, `graphindex/core.py` 31, `store/source.py` 14, `store/apply.py` 8.
UNVERIFIED (not yet read): most arg-type hits are expected to be SQLModel column expressions
(`Model.col == x` typed as `bool`), fixed by `sqlmodel.col(...)`.

ruff with a CORRECTNESS-only selection (`F`, `E9`, `B`, `PLE`, `--isolated`) over `src tests
scripts formal/conformance benchmarks`: F401 160 (of which `src` 127 are package `__init__`
re-exports: `schema/__init__` 48, `zanzibar/__init__` 35, `store/__init__` 33, `setengine` 7,
`graphindex` 4), B023 41, B905 24, B007 11, F541 4, F402 4, F821 3, PLE0604 1, B904 1, F841 1.

Candidate real defects to READ before calling them noise: F821 / mypy name-defined
(`schema/reports.py:136,256` `SchemaAST`, `schema/rules.py:552` `TTU` -- REASONED: string
annotations under `from __future__ import annotations`, so no runtime effect); pyright
possibly-unbound `graphindex/core.py:1044-1045` `neighbour_debits`; B023 loop-variable closures in
`schema/parser.py` (534-539, 788-797) and `graphindex/processor.py:1514`; PLE0604 (a non-str
in some `__all__`); mypy return-value `setengine/engine.py:1133,1138` (a 4-tuple where a
3-tuple is declared), `graphindex/core.py:1179`. Line numbers dated 2026-10-30.

## Decision (session, 2026-10-30b)

- **ruff, with an explicit correctness rule set** (`F`, `E9`, `B`, `PLE` to start), over
  `src/`, `tests/`, `scripts/`, `formal/conformance/`, `benchmarks/`; `__init__.py` re-exports
  exempt from F401. No `ruff format` and no style families (UP / I / SIM): hundreds of lines of
  churn in tests for no correctness gain, against the project goal (assurance honest, not
  wider). An explicit `select` also stops a ruff upgrade from changing what the gate means.
- **mypy as the gate's type checker, over `src/zanzibar` only.** Not pyrefly, although it
  finds the same order of problems: its advantage is speed, which does not matter at 35 files
  (0.4 s vs 3.7 s cold); mypy is the reference implementation of the typing spec, so a
  `py.typed` package that is mypy-clean is what most downstream users' checkers will agree
  with; it is pure Python and pins like every other dev dependency. pyrefly (and pyright, which
  backs VS Code / Pylance) stay useful as a second opinion; an occasional cross-check is
  cheap. Revisit if the codebase grows past the point where 4 s matters.
- **Both pinned to exact versions** in a new `lint` extra and installed by the gate's `lean`
  job in CI; the check runs inside `verify.sh lean` (fast), so it is in the local gate and CI
  with no new phase.
- Fixes are behaviour-preserving. An edit inside a `formal/CORRESPONDENCE.md` anchored body
  re-pins that anchor deliberately (content pin), never silently.
