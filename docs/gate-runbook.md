# Gate runbook — running the full suite, fuzzing, and Lean without partial/killed runs

The full validation gate is three heavy jobs — the pytest suite, the hypothesis
campaign, and the Lean `verify.sh`. Run naively they exceed the harness's **~10-min
per-command execution cap** and get killed mid-run, leaving no verdict. This runbook
is the cap-safe recipe. **`verify.sh` now takes a phase argument so the whole formal
gate runs as three cap-fitting commands an agent can execute unattended (§2)** — the
old "the user must run it uncapped" requirement survives only for a cold Lean build.

## The constraint

- One shell command is killed at ~10 min (600 s), foreground **or** background.
- `pytest -q` (whole repo) ≈ 655 s — right at the edge; it *has* been killed at
  ~64%.
- `verify.sh all` (one shot) = Lean build (warm ≈ 90 s / 1082 jobs, cold ≈ 20-40 min)
  + conformance (≈ 15-16 min today) ≈ 16-18 min — blows the cap. Run it **phased**
  instead (§2): `verify.sh lean | conf-heavy | conf-rest`, each of which fits the
  cap (worst phase is now `conf-rest` ≈ 9 min / ~544 s — close to the 600 s cap; then
  `conf-heavy` ≈ 6.5 min).
- `HYPOTHESIS_PROFILE=deep` (max_examples=120, stateful_step_count=25) is ~30× the
  `ci` profile — a single deep test file blows the cap.

## The recipe (run sequentially — never two heavy jobs at once)

CPU-contention between concurrent heavy jobs has corrupted measurements before
(benchmarks) and just wastes wall-clock (tests). Do these **one at a time**.

Interpreter: `C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`

### 1. Backend + differential suite — run it SPLIT (~7 + 4 min)
`pytest tests/ -q` in one shot is **right at the cap** (~10:30 on 2026-07-14/15;
it has finished at 628 s once and been killed with no verdict twice). Run the
tiled split instead — together the two halves are exactly the 531-test suite:

```bash
"$PY" -m pytest tests/ -q --ignore=tests/test_hypothesis.py --ignore=tests/test_matrix.py; echo "EXIT=$?"   # ~407 s, 507 passed
"$PY" -m pytest tests/test_hypothesis.py tests/test_matrix.py -q; echo "EXIT=$?"                            # ~230 s, 24 passed
```

Tiling check: 507 + 24 = 531. A newly added test file automatically lands in the
first half (the split only ever names the two heavy files). **Capture `$?`
directly** — piping through `tee` returns tee's exit code (0) and masks a failure.

### 2. Lean + conformance — the split `verify.sh` gate
`verify.sh` takes a **phase argument** so the whole formal gate (its 5 steps) runs
as three cap-fitting commands an agent can execute unattended. Warm timings on the
dev box:

```bash
bash formal/verify.sh lean        # steps 1-4: lake build + sorry=0 + zcli + axiom audit   (~0.5-3 min warm)
bash formal/verify.sh conf-heavy  # step 5, the slow file only (test_conformance_remove)   (~6.5 min)
bash formal/verify.sh conf-rest   # step 5, every OTHER conformance file          (~9 min / ~544 s — near the 600 s cap)
```

Run them **in that order** — the `lean` phase builds the `zcli` binary the conf
phases preflight on (a conf phase run without it FAILs loudly rather than skipping
vacuously). All three must print `PASSED`. Together they == `pytest tests/` (step 1)
+ a full `verify.sh all`.

- **Coverage is complete, by construction.** `conf-rest` is the conformance dir
  MINUS the heavy file (`--ignore=…/test_conformance_remove.py`), so the two conf
  phases *tile* `formal/conformance/` with no gap and any newly-added conformance
  file automatically lands in `conf-rest`. Tiling check: `conf-heavy` + `conf-rest`
  pass counts sum to the full total (76 + 239 = 315 today; the new
  `test_conformance_remove_graph.py` lands in `conf-rest` and, because it drives zcli
  `graphRunOps` per op, is what pushed `conf-rest` to ~544 s — near the cap).
- **A split pass is not a weakened pass.** Every phase carries the same anti-vacuous
  guards as the one-shot — olean layout-drift guard + `#print axioms` observed==expected
  (Lean), zcli-binary preflight + no-skip + passed>0 (conformance). So three green
  phases ≡ a green `verify.sh all`; there is no reconstructed-pass hole to manage.
- **`bash formal/verify.sh` with no arg** still runs all 5 steps in one shot
  (~13-16 min) — for an uncapped shell or CI only; it does NOT fit the cap.

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
`verify.sh lean` warm costs ~1 min, so just run it. Then `conf-heavy` + `conf-rest`.

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

### Push gate
Push only after ALL of: step 1 (`pytest tests/`) green; the three `verify.sh`
phases (`lean` → `conf-heavy` → `conf-rest`) each green; and — for an algorithm
change — a fuzz sweep (step 3) green. The phased gate is fully **agent-runnable
within the cap** (worst phase is now `conf-rest` ≈ 9 min / ~544 s, near the 600 s cap), and each phase carries the one-shot's
anti-vacuous guards, so three green phases satisfy the gate on their own — no
uncapped `verify.sh all` and no user hand-off is required (except to pre-warm a
cold Lean build; see §2).

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
- the conformance corpora (`formal/conformance/`, 315 deterministic tests),
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
