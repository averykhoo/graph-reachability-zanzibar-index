# Gate runbook — running the full suite, fuzzing, and Lean without partial/killed runs

The full validation gate is three heavy jobs — the pytest suite, the hypothesis
campaign, and the Lean `verify.sh`. Run naively they exceed the harness's **~10-min
per-command execution cap** and get killed mid-run, leaving no verdict. This runbook
is the cap-safe recipe. **`verify.sh` takes a phase argument so the whole formal
gate runs as a handful of cap-fitting commands an agent can execute unattended
(§2)** — the old "the user must run it uncapped" requirement survives only for a
cold Lean build.

## The constraint

- One shell command is killed at ~10 min (600 s), foreground **or** background.
- `pytest -q` (whole repo) ≈ 700 s+ — over the edge; it *has* been killed at ~64%.
- `verify.sh all` (one shot) = Lean build (warm ≈ 90 s / 1082 jobs, cold ≈ 20-40 min)
  + conformance (≈ 17-18 min today) ≈ 18-20 min — blows the cap. Run it **phased**
  instead (§2): `verify.sh lean | conf-tile:1/5 … conf-tile:5/5`, each of which fits
  the cap with room to spare (worst tile ≈ 235 s of the 600 s cap).
- `HYPOTHESIS_PROFILE=deep` (max_examples=120, stateful_step_count=25) is ~30× the
  `ci` profile — a single deep test file blows the cap.

## The recipe (run sequentially — never two heavy jobs at once)

CPU-contention between concurrent heavy jobs has corrupted measurements before
(benchmarks) and just wastes wall-clock (tests). Do these **one at a time**.

**Interpreter.** `verify.sh` resolves it itself (since 2026-07-26): `ZANZIBAR_PY`
wins if set, otherwise it tries `$HOME/anaconda3|miniconda3|mambaforge/envs/graph-
reachability-zanzibar-index/python.exe`, two literal `C:/Users/...` fallbacks,
`$CONDA_PREFIX`, and finally `python` on PATH — accepting only a candidate that can
actually `import pytest, sqlmodel`, and printing the one it picked. For your own
`pytest` invocations use the conda env named after the folder; on this machine that
is `C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`
(**not** the `C:/Users/avery/...` path older revisions of this file and CLAUDE.md
still name — that path does not exist here).

**Before anything long, check the declared deps.** A missing `hypothesis` fails
collection outright; a missing `pyroaring` used to *silently* drop the set engine to
the `PySets` fallback so every "both SetOps" leg quietly halved. `verify.sh`'s
preflight now **FAILS** on that (it asserts `RoaringSets is not None`, `len(ALL_SETOPS)
>= 2` and `DEFAULT_SETOPS.name == 'roaring'`) — but `pytest` on its own still will
not, so `pip install pyroaring hypothesis` into the env first.

### 1. Backend + differential suite — run it SPLIT (~7 + 4 min)
`pytest tests/ -q` in one shot is **over the cap** (~10:30 on 2026-07-14/15 at 531
tests; it is 610 tests now). Run the tiled split instead — together the two halves
are exactly the whole `tests/` suite:

```bash
"$PY" -m pytest tests/ -q --ignore=tests/test_hypothesis.py --ignore=tests/test_matrix.py; echo "EXIT=$?"   # 578 tests
"$PY" -m pytest tests/test_hypothesis.py tests/test_matrix.py -q; echo "EXIT=$?"                            # 32 tests
```

Tiling check: 578 + 32 = 610 collected (measured 2026-07-26 — re-measure with
`pytest tests/ -q --collect-only`; `tests/` is under active development and the
number moves). A newly added test file automatically lands in the first half (the
split only ever names the two heavy files). **Capture `$?` directly** — piping
through `tee` returns tee's exit code (0) and masks a failure. If the first half
blows the cap, tile it finer per the slow-machine section below.

### 2. Lean + conformance — the split `verify.sh` gate
`verify.sh` takes a **phase argument** so the whole formal gate (its 5 steps) runs
as five cap-fitting commands an agent can execute unattended. Warm timings on the
dev box (measured 2026-07-26):

```bash
bash formal/verify.sh lean           # steps 1-4: lake build + hole scan + zcli + axiom audit  (32 s warm)
bash formal/verify.sh conf-tile:1/5  # step 5, tile 1 of 5 of formal/conformance/
bash formal/verify.sh conf-tile:2/5  # step 5, tile 2 of 5
bash formal/verify.sh conf-tile:3/5  # step 5, tile 3 of 5
bash formal/verify.sh conf-tile:4/5  # step 5, tile 4 of 5
bash formal/verify.sh conf-tile:5/5  # step 5, tile 5 of 5
# K is a free parameter -- the tiles partition formal/conformance/ by collection index,
# so union coverage is STRUCTURAL at any K. Raise K when a tile nears the ~600 s cap.
# 2026-07-26: at K=4 the conformance suite grew to 391 tests and tile 2/4 hit 462 s,
# so the recommended default moved to K=5.
```

Run `lean` **first** — it builds the `zcli` binary the conf phases preflight on (a
conf phase run without it FAILs loudly rather than skipping vacuously). The four
tiles are order-independent. All five must print `PASSED`. Together they ==
`pytest tests/` (step 1) + a full `verify.sh all`.

- **Coverage is complete, by construction — and now also asserted.** A
  `conf-tile:I/K` phase collects `formal/conformance/` fresh, asserts the collected
  total is `>= MIN_CONF_ALL` (356 today), then runs the node ids whose 0-based
  collection index is `≡ I-1 (mod K)`. Every collected node lands in **exactly one**
  tile, so the K tiles partition the directory: a newly added file, corpus or
  parametrization is automatically in exactly one tile, nothing is named by hand, and
  the tile's size is cross-checked against the partition arithmetic
  (`floor((total-I)/K)+1`) so a tiling that is not a partition FAILs. Each tile's own
  pass floor is its exact size — every selected test must pass.
- **The global floor is per-phase.** Because *every* tile re-asserts the 356-test
  collection floor, you cannot lose conformance coverage and still get a green tile —
  even if you only ever run one.
- **A split pass is not a weakened pass.** Every phase carries the same anti-vacuous
  guards as the one-shot — olean layout-drift guard, `#print axioms`
  observed==expected **plus a hard-coded 455 floor** (Lean), zcli-binary preflight,
  the collection floor, zero `skipped`/`xfailed`/`xpassed`/`deselected`, and
  `passed >= floor` (conformance). So the green phases ≡ a green `verify.sh all`;
  there is no reconstructed-pass hole to manage.
- **Legacy phases still work.** `conf-heavy` (`test_conformance_remove.py`, 80 tests,
  **175 s** measured 2026-07-26) and `conf-rest` (the dir MINUS that file via
  `--ignore`, 276 tests) also tile the directory — 80 + 276 = 356, and `verify.sh`
  checks that identity on its own floors at startup. `conf-heavy` is a handy quick
  single-file rerun. **`conf-rest` is AT OR OVER the cap** (579 s measured
  2026-07-19g/07-26 at 250-276 tests, and the whole dir is ~800 s of work) — that is
  why the `conf-tile` phases exist. Do not use `conf-rest` unattended; use the tiles.
- **Where `conf-rest`'s time actually goes.** `test_conformance_enum.py` — 6 tests,
  **~380-475 s** (exhaustive small-scope enumeration) — is the hog, not
  `test_conformance_remove_graph.py` (17 tests, ~27 s) as the 2026-07-19g note
  guessed. Everything else in `conf-rest` is ~165 s combined. The `conf-tile` split
  interleaves those 6 tests across the four tiles, which is what balances them.
- **`bash formal/verify.sh` with no arg** still runs all 5 steps in one shot
  (~18-20 min) — for an uncapped shell or CI only; it does NOT fit the cap.

#### The hard-coded floors in `verify.sh` (gate self-defence, 2026-07-26)
Before this, the gate could stay green while the assurance surface eroded: deleting
`#print axioms graph_correct` from `Audit.lean` was invisible (the "expected" count
was grepped out of the very file being audited), and deleting `test_conformance_graph.py`
outright was invisible (the only conformance assertions were `skipped == 0` and
`passed > 0`). Four numbers now live in `formal/verify.sh`, all asserted with `-ge`
so **adding** theorems/tests never fails the gate:

| constant | value | what it guards |
|---|---|---|
| `EXPECTED_MIN_AUDITS` | 455 | `#print axioms` reports observed from `Audit.lean` |
| `MIN_CONF_ALL` | 356 | tests collected from `formal/conformance/` |
| `MIN_CONF_HEAVY` / `MIN_CONF_REST` | 80 / 276 | the legacy split's floors (checked to sum to `MIN_CONF_ALL`) |
| `MIN_SCANNED_LEAN_FILES` | 60 | project `.lean` files the hole scan must cover (65 today) |

**Lowering any of them must be a deliberate, reviewed edit to `verify.sh`** — and
should be justified in `formal/history/`. Raising them is free and encouraged when
counts grow. The conformance floors are cross-checked arithmetically against each
other, so you cannot bump one and leave a hole in another.

#### What step 2 scans now (`formal/conformance/sorry_scan.py`)
The hole scan is no longer just `\b(?:sorry|admit)\b` over `formal/lean/ZanzibarProofs`:

- **Tokens:** `sorry`, `admit`, **`sorryAx`** (the constant a `sorry` elaborates to —
  `\bsorry\b` *cannot* match it, `A` is a word character) and **`native_decide`**
  (closes goals by running compiled code, pulling the `Lean.ofReduceBool` axiom).
- **Custom `axiom` declarations** (`^\s*axiom\s`, modulo modifiers/attributes) —
  `axiom cheat : ∀ p, p` typechecks and produces no `sorry`. Anchored so the 455
  `#print axioms` commands and every prose mention of the word do not trip it.
- **Unterminated string literals** are themselves a violation: one stray `"` used to
  make the rest of that file invisible to the scanner *in silence*.
- **Root is `formal/lean`**, not `formal/lean/ZanzibarProofs` — the latter missed the
  sibling library root `ZanzibarProofs.lean`. The scanner skips every dot-directory,
  which is what keeps the ~9.3k vendored `.lean` files under `formal/lean/.lake/**`
  (mathlib/aesop/batteries) out of the scan: **65 project files scanned, 9341
  vendored files skipped** (was 64 / 0).
- `--min-files N` is a coverage floor: a clean `0` from a scan that stopped finding
  files is not evidence.
- Step 3's `lake build zcli` output is now `tee`'d into the same
  `declaration uses 'sorry'` grep as step 1. `Cli.lean` is not reachable from the
  default lake target, so the zcli that IS the conformance ground truth was building
  with its warnings going nowhere.
- All of the above is unit-tested in `formal/conformance/test_sorry_scan.py` (39
  cases) — extend it there, not by hand-testing the gate.

**When can `lean` blow the cap?** Only a genuinely **cold** Lean build (fresh
checkout, cleaned `.lake`, or a toolchain bump) is 20-40 min. A **warm** tree — the
case for any Python-only change, since nothing invalidates the Lean cache — is
~0.5-3 min (`lake build` ≈ 90 s cold-of-session, then near-instant; the audit
rebuild ≈ 85 s). If `lean` is killed on a cold build, pre-warm once from an uncapped
shell (`cd formal/lean && lake build && lake build zcli`) or have the user run
`! bash formal/verify.sh lean`; after that the capped phases work.

**For a change that touches NO `.lean` file** (Python-only perf work is the usual
case): the Lean *proofs* are unaffected — you may confirm `git diff` shows no
`formal/lean/**/*.lean` change and lean on the last green `lean` phase — but running
`verify.sh lean` warm costs ~1 min, so just run it. Then the four `conf-tile` phases.

**A killed `lean` phase no longer wedges the cache.** Step 4 (`rm -f Audit.olean`
then rebuild) is now **self-healing**: it rebuilds a missing `Audit.olean` before
asserting the expected path, so a prior kill can't leave the layout-drift guard
tripped. (The guard still catches genuine path drift: a rebuild at a drifted path
leaves the expected path empty and FAILs.) Recovery from an *older* kill (pre-self-heal
state) if ever needed: `cd formal/lean && lake build ZanzibarProofs.Audit`.

### 3. Fuzzing before an algorithm change (do NOT skip — see the P1 lesson)
The `ci` profile (max_examples=12, stateful_step_count=8) is the per-commit floor
and runs inside step 1. Before shipping an **algorithm change** to a read/write
surface, run a deeper campaign. Two cap-safe options:
- **Multi-seed sweep** (preferred, simple): loop the relevant hypothesis file over
  several explicit seeds — each run is fast, the union is broad.
  ```bash
  for s in 7 19 31 53 71 97; do
    "$PY" -m pytest tests/test_lookup_hypothesis.py --hypothesis-seed=$s -q; done
  ```
- **Deep, chunked**: `HYPOTHESIS_PROFILE=deep` on a *single* targeted test node,
  and only if it fits the cap; otherwise split by test node. Full-repo deep is a
  nightly/offline job, not a single command.

> ### ⚠ FOOTGUN — `HYPOTHESIS_SEED` does NOTHING (recorded 2026-07-26)
>
> The multi-seed sweep above works **only** via the `--hypothesis-seed=$s` **command-line
> flag**. There is no `conftest.py` in this repo that reads a `HYPOTHESIS_SEED`
> environment variable — `grep -rn HYPOTHESIS_SEED` over the whole tree returns **zero
> hits**. So this, which looks right and is easy to reach for by analogy with
> `HYPOTHESIS_PROFILE` (which *is* read, by hypothesis itself):
>
> ```bash
> for s in 7 19 31 53 71 97; do HYPOTHESIS_SEED=$s "$PY" -m pytest tests/test_hypothesis.py -q; done   # ← WRONG
> ```
>
> silently runs **six identical default-seeded runs** and reports six greens. It fails by
> PASSING, which is the worst failure mode a gate step can have: you get the reassurance
> without the coverage. Use the flag form in the recipe above.
>
> This bit a real session on 2026-07-26 (the zero-trust review): a "6-seed fuzz sweep
> clean" claim was made — and written into a pushed commit message — on the strength of
> six identical runs. Re-running with the flag produced genuinely varied seeds and was
> also clean, so nothing was missed that time. If you assert a multi-seed sweep, paste
> the per-seed output; identical durations across seeds are the tell.
>
> (If you would rather make the env-var form work than remember this, adding a
> `conftest.py` that reads `HYPOTHESIS_SEED` and calls `hypothesis.seed()` would close
> it permanently — not done, deliberately, to avoid a second way to do the same thing.)

### Push gate
Push only after ALL of: step 1 (`pytest tests/`) green; the five `verify.sh` phases
(`lean` → `conf-tile:1/5` → `2/5` → `3/5` → `4/5` → `5/5`) each green; and — for an algorithm
change — a fuzz sweep (step 3) green. The phased gate is fully **agent-runnable
within the cap** (worst phase ≈ 235 s of the 600 s cap since the 2026-07-26 retiling),
and each phase carries the one-shot's anti-vacuous guards *plus* the count floors, so
the green phases satisfy the gate on their own — no uncapped `verify.sh all` and no
user hand-off is required (except to pre-warm a cold Lean build; see §2).

## Running the gate on a secondary / slow machine (lessons 2026-07-23)

All timings above are the primary dev box's. The gate was first run end-to-end on a
second machine (laptop, intermittently in power-saver on battery — **2-3×+ slower**,
and the throttle comes and goes mid-gate). What breaks and what to do:

- **Environment first.** `verify.sh` no longer pins one box's interpreter — it
  resolves a candidate list and validates it (see §"The recipe" above); `ZANZIBAR_PY`
  still overrides. `CLAUDE.md` still names the old `C:/Users/avery/...` path, so use
  the local conda env directly for your own pytest invocations. Check the declared
  deps before anything long: a missing `hypothesis` fails collection outright, and a
  missing `pyroaring` silently drops the set engine to the `PySets` fallback — the
  "both SetOps" legs of the matrix then under-test. `verify.sh`'s preflight FAILs on
  that since 2026-07-26, but plain `pytest` does not: `pip install pyroaring
  hypothesis` into the env and only then start the gate.
- **The §1 two-way pytest split can blow the cap.** Tile finer: get per-file counts
  with `pytest tests/ -q --collect-only`, group files into tiles of roughly ≤130
  tests (alphabetical ranges work; keep the known-slow files —
  `test_connectedstore_concurrency`, `test_processor`+`test_reads`,
  `test_parity_engine` — in small tiles), and **assert Σ(tile passed) == the
  collect-only total** so the tiling provably has no gap. 2026-07-23 ran 10 tiles,
  606/606, worst tile 546 s (throttled).
- **Capture exit codes without pipes.** `out=$(pytest ... 2>&1); code=$?` — both
  `tee` and `tail` mask the pytest exit code (same trap as the tee gotcha below).
- **Cold Lean on a fresh machine.** Install elan from the GitHub release zip
  (`elan-x86_64-pc-windows-msvc.zip` → `elan-init.exe -y --default-toolchain
  leanprover/lean4:v4.31.0`; the winget id doesn't exist and `elan-init.ps1` fights
  PowerShell parameter quoting). Then **`lake exe cache get` BEFORE `lake build`** —
  mathlib is a dependency and building it from source wastes ~2 chunks before you
  notice (the lakefile says this; read it). With the cache (~8.5 k files, fits one
  chunk on a normal connection) the library build is ~1084 jobs and **`lake build`
  is resumable**: repeated capped runs make monotone progress to completion. After
  that `verify.sh lean` fits the cap.
- **Conformance can blow the cap throttled — just use more tiles.** This no longer
  needs a hand-rolled wrapper: `verify.sh conf-tile:I/K` takes any `K`, so on a
  throttled box run `conf-tile:1/8 … conf-tile:8/8` (or `1/12 … 12/12`). Every tile
  re-collects the directory, re-asserts the 356-test global floor, checks its own size
  against the partition arithmetic and carries all of `run_conf`'s anti-vacuous guards
  — so the union is provably the whole dir for any `K` and there is nothing to
  replicate by hand. (The 2026-07-23 advice here — tile A = dir minus
  `test_conformance_remove.py` minus `test_conformance_remove_graph.py`, tile B =
  `remove_graph` alone — was aimed at the wrong file: `remove_graph` is ~27 s;
  `test_conformance_enum.py` is the ~380-475 s one.)
- **A timed-out foreground command may be moved to the background** by the current
  harness instead of killed — check the task's output file for a late verdict
  before assuming "no verdict" and rerunning.

## Gotchas (hit 2026-07-14/15)

- `tee` masks pytest's exit code → capture `$?`.
- Background commands are capped the same ~10 min as foreground — and an
  explicit per-command timeout kills a background run at that timeout **with no
  verdict** (hit 2026-07-15: full suite killed at ~67%). A killed run tells you
  nothing; use the §1 split instead of gambling on the monolith.
- A killed `lean` phase no longer wedges the Lean cache — step 4 self-heals a missing
  `Audit.olean` (was: manual `lake build ZanzibarProofs.Audit` before retry).
- **Algorithm changes need the fuzz gate BEFORE pushing.** P1 (lookup reverse
  walk) shipped an object-wildcard×TTU completeness bug because only the `ci`
  profile ran pre-push; a multi-seed / deep sweep caught it the next run. The
  differential oracle gate with *fixed seeds* is necessary but not sufficient for
  an algorithm change — randomized/stateful fuzzing is what finds the long tail.

---

## Can test runtime be a perf signal?

Short answer: **weakly, and only a stable subset — but the dedicated benchmark
harness is the real signal; don't overload the tests with perf duties.**

**Why raw test runtime is weak.** Test wall-time is dominated by fixture setup,
ORM/session overhead, assertion cost, and per-process import (~10-15 s), not by the
optimized inner loops. Most tests aren't *sized* to stress hot paths, and CI/machine
variance is ±10-15%. A real regression can hide inside that noise; a GC hiccup can
masquerade as one.

**The strong signal already exists:** `benchmarks/scale_bench.py` (controlled sizes,
deterministic data, results appended to `scale_bench.jsonl`, fitted in
`benchmarks/analyze.py`). That is where perf tracking belongs — it isolates
write/check/lookup/reverse per backend at growing N and reports the scaling
*exponent*, which is what actually caught (and confirmed the fix of) every
optimization this session.

**If you still want an always-on tripwire** (cheaper than the full sweep, more
controlled than test runtime): time a **deterministic, rarely-changing,
hot-path-heavy subset**. Best candidates, because they change by design only when
behavior changes:
- the conformance corpora (`formal/conformance/`, 356 deterministic tests),
- the validation matrix (`tests/test_matrix.py`),
- the compiled-RuleSet snapshots (`tests/snapshots/`).
Track these via `pytest --durations=20` across commits and eyeball for a step
change. **Do not gate on it** — machine variance makes a hard threshold flaky.

**A concrete lightweight proposal** (`benchmarks/canary.py`, if we want it): build
one fixed store (e.g. `simple` N=8000) and time a fixed op mix (K writes, K
lookups, K checks), print rates, compare to a recorded baseline with a *generous*
threshold (e.g. flag only a >2× regression). Runs in seconds; it's a coarse
"did something get 2× slower" alarm, not a measurement. It sits between "grep the
test durations" (free, noisy) and "run the full `scale_bench` sweep" (accurate,
minutes).

**Recommendation.** Keep perf out of the pass/fail test gate (flaky). Use
`scale_bench` for real perf work, `--durations` as an opportunistic spot-check, and
add `canary.py` only if we want a nightly tripwire. The "rarely-changing subset"
idea is sound *as a tripwire*, but even the most stable subset is still a proxy for
correctness-checking time, not for the optimized paths — so treat any signal from
it as "look closer with `scale_bench`," never as a verdict.
