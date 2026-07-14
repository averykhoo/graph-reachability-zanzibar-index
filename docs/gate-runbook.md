# Gate runbook — running the full suite, fuzzing, and Lean without partial/killed runs

The full validation gate is three heavy jobs — the pytest suite, the hypothesis
campaign, and the Lean `verify.sh`. Run naively they exceed the harness's **~10-min
per-command execution cap**, get killed mid-run, and leave no verdict (or, for
`verify.sh`, a *corrupted* Lean cache). This runbook is the cap-safe recipe.

## The constraint

- One shell command is killed at ~10 min (600 s), foreground **or** background.
- `pytest -q` (whole repo) ≈ 655 s — right at the edge; it *has* been killed at
  ~64%.
- `verify.sh` = Lean build (cache-hit ≈ fast, cold ≈ 20-40 min) + conformance
  (≈ 5.5 min). Cold, or after a prior kill, it blows the cap.
- `HYPOTHESIS_PROFILE=deep` (max_examples=120, stateful_step_count=25) is ~30× the
  `ci` profile — a single deep test file blows the cap.

## The recipe (run sequentially — never two heavy jobs at once)

CPU-contention between concurrent heavy jobs has corrupted measurements before
(benchmarks) and just wastes wall-clock (tests). Do these **one at a time**.

Interpreter: `C:/Users/avery/anaconda3/envs/graph-reachability-zanzibar-index/python.exe`

### 1. Backend + differential suite (~5 min)
```bash
"$PY" -m pytest tests/ -q; echo "EXIT=$?"
```
`tests/` alone (without `formal/conformance/`) fits under the cap. **Capture `$?`
directly** — piping through `tee` returns tee's exit code (0) and masks a failure.

### 2. Lean + conformance
`verify.sh`'s step 5 (`pytest formal/conformance/`, ≈ 5.5–7 min) is the *other* half
of `pytest -q`, so step 1 + conformance together == the whole suite + the
conformance gate.

**Reality check: `verify.sh` does NOT reliably fit the 10-min cap, even warm.**
Step 1 (`lake build`) *replays* all ~2144 modules every run (~4–5 min inherent for
a Mathlib-scale project — a warm rebuild is not instant), and conformance is another
5.5–7 min, so the total is ~10–12 min. It sometimes squeaks under, often doesn't.
So:

- **For a change that touches NO `.lean` file** (Python-only perf work is the
  usual case): the Lean *proofs* (steps 1–4: build, `sorry`=0, `zcli`, axiom audit)
  are unaffected — verify they were green earlier and confirm `git diff` shows no
  `formal/lean/**/*.lean` change. Then run only the part that exercises your code:
  ```bash
  "$PY" -m pytest formal/conformance/ -q; echo "EXIT=$?"
  ```
  That + step 1 == the full `pytest -q` coverage; the proofs ride on "unchanged".
- **For a change that DOES touch `.lean`**, or when you need the classifier's
  end-to-end `verify.sh` green (it rejects a reconstructed pass): run
  `bash formal/verify.sh` **uncapped** — from an interactive shell, or in this
  harness via the user typing `! bash formal/verify.sh` (the user's shell has no
  10-min cap). Pre-warm first (`cd formal/lean && lake build && lake build zcli &&
  lake build ZanzibarProofs.Audit`) to minimise its runtime.

**Never kill `verify.sh` mid-run.** Its step 4 does `rm -f Audit.olean` then rebuilds
it; a kill in between leaves `Audit.olean` missing (and the default `lake build`
does *not* rebuild the `Audit` target), so the next run fails the layout-drift
guard (`FAIL: audit olean not at expected path`). Recovery:
`cd formal/lean && lake build ZanzibarProofs.Audit`, then re-run. This corruption
cost several retries this session — treat `verify.sh` as uninterruptible.

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
Push only after: step 1 green, step 2 green **end-to-end in one `verify.sh`
invocation** (the push-gate classifier rejects a reconstructed pass — a
killed-at-step-5 run + a separate conformance run does not count), and — for an
algorithm change — a fuzz sweep (step 3) green.

## Gotchas (all hit this session, 2026-07-14)

- `tee` masks pytest's exit code → capture `$?`.
- Background commands are capped the same ~10 min as foreground.
- A killed `verify.sh` corrupts the Lean cache (`Audit.olean`); rebuild before retry.
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
- the conformance corpora (`formal/conformance/`, 263 deterministic tests),
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
