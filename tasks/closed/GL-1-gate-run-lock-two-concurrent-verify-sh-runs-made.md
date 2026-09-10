---
id: GL-1
title: gate run lock -- two concurrent verify.sh runs made a PASSING phase report EXIT=0 over a failing log
brief: LANDED: verify.sh takes an exclusive run lock; a colliding run refuses nonzero instead of racing
pri: LATER
size: M
deps: []
related: []
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-10b
moved: 2026-09-10b
updated: 2026-09-10b
closed: 2026-09-10b
---

## What happened

A `conf-tile:1/5` phase reported `EXIT=0` to its caller under a log ending:

```
60 failed, 50 passed in 220.62s (0:03:40)
FAIL: conf (pytest rc=1)
```

filed (2026-09-10, commit `3ac7fd2`) as either a hole in `verify.sh:270-273` — the
`gate_on_exit` INCONSISTENT branch — or an EXIT trap that died under resource pressure.

## It was neither

* `verify.sh` **detected the failure and exited 1**. The log's last line is
  `FAIL: conf (pytest rc=1)` and the ledger row is
  `conf-tile:1/5 FAILED t2c:f40454f44b66 rc=1 collected=546 selected=110`.
* The **EXIT trap was alive** — it is what wrote that row.
* The guard at `:270-273` covers *exit 0 without the PASSED banner*, which never
  happened, so it was never in play.
* Bash **preserves an exit status across a returning EXIT trap**. Tested three ways on
  bash 5.2.26 (trap fn ending in a false `[ ]`, in a no-op, in an unexecuted `if`); all
  three gave `EXIT=1`.

## What it was: two runs, one filename

`.gate-runs/ledger.tsv` column 1 is the START time, column 2 the duration:

```
run A  started 14:35:01  ran 225 s -> ended 14:38:46   FAILED  60 failed, 50 passed
run B  started 14:36:14  ran 196 s -> ended 14:39:30   PASSED  110 passed
run C  started 14:40:21  ran 190 s -> ended 14:43:31   PASSED  110 passed  (the "re-run alone")
```

B started **73 s into A**. Both followed `docs/gate-runbook.md`, which prescribed the
FIXED path `bash formal/verify.sh <phase> > /tmp/p.log 2>&1; rc=$?`. Two processes
redirecting into one path each truncate it and then write at independent offsets: A wrote
6466 lines and finished first, B wrote ~30 and finished last, so B's banner landed at a
low offset and A's failure tail stayed at the end. `rc` was B's honest `0`; `tail` was A's
failure. Reproduced verbatim before the fix.

The concurrency is also the most plausible **cause** of A's 60 failures: every one was
`rc=3221225794` (`0xC0000142`, STATUS_DLL_INIT_FAILED) on `zcli` spawn, which is what two
tiles racing to spawn the same large Lean binary looks like. C, alone, passed 110/110 on
the same tree.

⚠ **The documented fix for footgun #1 created this one.** `/tmp/p.log` was prescribed
because piping through `tail` eats the exit code. A fixed log path is a shared resource.

## What landed

* `scripts/gate_lock.py` — an exclusive per-repo run lock. A second concurrent run
  REFUSES, nonzero, in under a second, naming the incumbent phase/pid and the lock file.
  Age-based staleness (3600 s, > 3x the longest legitimate run) so a SIGKILLed run cannot
  brick the gate; steals are announced, never silent; the steal claims the lock by
  `os.rename` so two stealers cannot both win. Liveness-by-pid was rejected deliberately:
  `os.kill(pid, 0)` on Windows calls `TerminateProcess`, and the recorded pid is an MSYS
  pid anyway.
* `formal/verify.sh` — acquires after `gate_tree_id` (before any phase work), releases
  from `gate_on_exit` after the ledger row and before the INCONSISTENT `exit`. A refused
  run lands as `FAILED ... rc=1 refused=lock-held`, duration 0 s.
* `tests/test_gate_lock.py` — 20 tests, plus the end-to-end sabotage and the 11-mutation
  sweep table in its docstrings.
* `docs/gate-runbook.md` + `CLAUDE.md` footgun #1 — the variant, and the recipe now uses
  `mktemp` instead of a fixed path.

**This also closes the 2026-09-08b orphan variant.** `verify.sh` re-execs itself (parent
tees, child works); the surviving process in that story is the child, which holds the lock
and releases it from its EXIT trap. An orphan keeps the lock and the next phase refuses.

## Sabotage (literal output, 2026-09-10)

`lean` backgrounded, second `lean` started 8 s later:

```
===== SECOND (colliding) RUN: rc=1 =====
REFUSED: another gate run holds the lock, so this run has done nothing.
         wanted phase: lean
         held by phase: lean (pid 16744, started 2026-09-10T19:16:28, 7 s ago)
         lock file:     .../.gate-runs/gate.lock
FAIL: refusing to start 'lean' while another gate run holds the lock.
===== FIRST RUN: rc=0 =====
=== lean phase (steps 1-4) PASSED (holes=0, audits=587, pinned=587) ===
```

Instrument controlled: the lock file was confirmed GONE after the incumbent finished, and
the incumbent's own verdict was unaffected.

## What is NOT claimed

The rename-atomicity of a steal is pinned only structurally (a source-reading mirror).
Mutation 10 of the sweep — steal by `unlink` instead of `rename` — was **INERT** against
every behavioural test, because the difference appears only when two runs steal at once. A
genuinely concurrent two-stealer test would be timing-dependent, i.e. a flaky test inside
the gate. See `tests/test_gate_lock.py::test_the_steal_claims_a_stale_lock_by_RENAME_rather_than_UNLINK`.

## Log

### 2026-09-10b

Landed: scripts/gate_lock.py, the verify.sh wiring (acquire before phase work, release from gate_on_exit), and tests/test_gate_lock.py -- 20 tests, an end-to-end sabotage against the real gate, and an 11-mutation sweep. Root cause was NOT the exit-code guard at verify.sh:270-273, which was correct and never in play: two concurrent runs shared the runbook fixed /tmp/p.log, so a PASSING run rc sat beside a FAILING run tail. Runbook recipe now uses mktemp; CLAUDE.md footgun 1 carries the variant. Mutation 10 (steal by unlink) was INERT and is pinned only structurally -- stated on the row and in the test.
