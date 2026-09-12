# session-log.md — the append-only root session ledger

**LIVING — append-only.** This file lives under `docs/history/` for filing reasons
only; it is *not* frozen provenance, and the frozen-banner rule does not apply to it
(`scripts/handoff_lint.py` excepts it by name). It is the root analogue of
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md), which keeps
the *formal* detail; a formal-heavy session writes the detail there and points at it
from here.

**The rules** (conventions are defined once in [`docs/README.md`](../README.md)):

* **Newest entry first.** One entry EVERY session, without exception — a task's
  `moved` field is only meaningful if every session leaves a dated trace.
* **Entry key: `## YYYY-MM-DD[letter] — <headline>`.** The letter disambiguates
  same-day sessions (`2026-08-16`, `2026-08-16b`, …). The key is a stable citation
  target: entries are **never retro-edited**. A later entry names what it refutes.
* **The headline is one line and feeds the banner** — the `## Banner` section of
  [`HANDOFF.md`](../../HANDOFF.md) — verbatim, so keep it under ~120 characters
  including the key.
* **`rows:`** names the task ids the session touched (`tasks/`; the `HANDOFF.md` board
  ids until the 2026-09-06 cutover).
* **Two literal receipt lines**, enforced by `handoff_lint.py::check_session_receipt` on
  the newest entry only: the output of `python scripts/task.py lint`, and
  `read: board only` / `read: board + note`.
* **`Still owed:`** closes every entry. If the session ran short of context and skipped
  a write-back step, list the skipped actions here *verbatim* — the next session
  executes them before its own work.
* Body length is up to the writer; no cap. Links are written relative to the repo
  root, so from this file they resolve against `../../`.

---

## 2026-09-12 — `P6` is BLOCKED, not expensive: `TtuStarFreeW` admits a through-shape no routing can bridge

rows: `P6` (two `2026-09-12` Log entries; **not** re-ranked — it stays `NOW`, still a
user-owned call). Nothing closed. New tracked file:
[`formal/probes/p6_inbridge_stability_2026-09-12.lean`](../../formal/probes/p6_inbridge_stability_2026-09-12.lean).

task lint: clean (13 checks, 181 task file(s) parsed), 24 warning(s)
read: board + note

User asked what was next, then whether `P6` fits one session, then to attempt it with
`ultracode` and to split it if completion failed. Answer to the sizing question was **no**;
the attempt then found something better than a size — **a scope defect that makes increment B
impossible as specified, rather than expensive.** Detail lives on the `P6` row
(`python scripts/task.py show P6`), which is the sole authority on open work; this entry is
the trace and the method note.

**The finding.** `TtuStarFreeW` (`GraphIndex/TtuStarWide.lean:72-76`) requires only
`S.isSubjectWildcardUserset t.subject.type tr = true` — **no `isDerived … = false`
conjunct** — so it admits stores whose TTU through-shape is a *derived* relation. At a derived
through-shape there is no node on the leaf-routed write list for `ensureInBridges` to fire on,
because `isStarTuplesetThrough` and disjunct (a) both scan `S.defs` and a minted leaf
`<R>.<i>` is not a declared shape. The probe measured it rather than arguing it:
`leafBridged := false`, `bridgesOnLeafRouted := 0`, `bridgesOnPublicKeyed := 1`, against
`legEdgesIntoLeaf := 1` / `legEdgesIntoPublic := 0`. The only bridgeable node is the **public**
one, which is exactly what `P6`'s standing constraint forbids. **So part (ii) cannot inhabit
the predicate part (iv) already landed and audit-pinned** — and (iv) was scheduled on
*decidability* alone, which is the only question anyone asked of it. The payoff criterion
failed too: bridging moves the graph-vs-`sem` grid from 14 mismatches to 9 of 546, i.e.
`bridgedAgree := false`. Restoring that agreement is the whole purpose of increment B.

**Second, independent blocker.** The write leg would mint an edge the remove leg *provably
cannot retract* (`objNode` yields only `Variant.wAll`/`plain`, `State.lean:126-128`, while
`wAnyNode` is `Variant.wAny`, `:122`, so no bridge pair is ever an `edgeOfTuple` image), there
is **zero** bridge-retraction machinery tree-wide (grepped six name variants: only an unrelated
sabotage pin), and the obvious guard repair is the shape `RemoveOccCount.lean:178-194` refuses
by name — "a theorem rescued by making its counterexample inadmissible". Both walls need a
**human decision**, so neither was taken.

**It does not split, and the boundary argument is where the naive answer fails.** Every
candidate boundary either leaves the bridge un-called — a fourth repeat of part (i)'s
inertness, with `W4Fragment.ttuStarFree` still uninhabited — or mints the edge and takes the
whole 42-module cone at once. "Cone 0 ⇒ gate green at the boundary" is **false here**:
`statement_pin.py::lean_files` is `LEAN_ROOT.rglob("*.lean")` and consults imports *never*, so
a new decl adds a pin row at import-cone 0; `doc_counts --check` runs inside the `lean` phase
(`formal/verify.sh:935`); and `TtuStarFree` sits in `formal/headline_statements.txt:44` inside
`W4WitnessDirect.fragment`, so widening it reds the headline pin as well.

**Method, and the part worth reusing.** Eleven agents: four read-only (spec / splittability /
census / probe design), **one serial** Lean runner, five adversarial skeptics on distinct
lenses, one synthesis. Two constraints made it safe on a shared laptop: no agent could run
`lake build` or `verify.sh` (one tree, serial builds), and **no worktrees** — a
`git worktree remove --force` once recursed through a `.lake/packages` junction and gutted the
main tree's mathlib. The probe is zero-cone *by construction* because `formal/probes/` sits
outside the lake package and `verify.sh` never reads it (grepped).
**All five skeptics refuted something.** They were reconciled, not averaged — and that is what
earned the session its result, twice over:

* ⚠ **A subagent report retired a VALID trap, and first-hand checking caught it.** The
  synthesis claimed "`RulesComplete.lean:91` / `ReachedByRulesAdmitted.step` does not exist …
  there is no `step` constructor", and elsewhere called the constructor `write`. **Both wrong.**
  The inductive is `RulesComplete.lean:111`, the constructor **is** `step` at `:113`, `hadm` is
  its field at `:115`, and it is used at 8+ sites. Only the line number `91` drifted. Had that
  been believed, the `FoldAdmits` three-stay-sites trap would have been deleted as
  unenforceable. This is the standing rule earning its keep: a subagent's report is evidence,
  not a finding.
* ⚠ **Two of my own figures from earlier the same day were wrong, and both were counting-unit
  failures** — the exact class this repo has burned four sessions on. (1) I wrote that the
  row's "38-module cone" was "an undercount, retired". It is **reconcilable**: union of the six
  reverse cones excluding the root aggregator = **42**, four of the six targets are themselves
  members, so union-minus-targets = **38** and union-∪-targets = **44**. One graph, three
  honest numbers. (2) I wrote "23 theorems / ~1,050 lines / 3 files" for the at-risk stability
  surface; the enumeration summed to **22**, and it had dropped the remove-leg duals in tiers 2
  and 3. First-hand recount under a stated unit: `CascadeStable` 10, `CascadeStrataSettle` 18,
  `CascadeSettle` 1 = **29 declarations**.

**A tier-2 instrument is owed, and the probe says so about itself.** `guardPre := false` and
`guardPost := false` in **all eight arms including BASE and NULL**, so no arm ever satisfied
the tier-2 premises and tier 2 is **undecided — zero information**, not green and not red.
Relatedly, do not read arm B-SUB-L's `verdict := "GREEN"` as "logging the bridge fixes it":
four of `verdictOf`'s six conjuncts quantify over unmapped keys only and the bridge mapped 3
of 4, so the green is bought by a ~75% collapse of the instrument's domain (`reachPairs`
1152 → 288, `guardPairs` 168 → 42) with `reachStableAll := false` — the probe's own documented
vacuity signature — ignored by the verdict. Tier 1, by contrast, is a solid negative:
`hunmapped` genuinely holds at a subject-endpoint bridge and the statements still go **FALSE**.

**Still owed:**

- **The Wall-1 decision is open and belongs to the user** — narrow `TtuStarFreeW` to untainted
  through-shapes (cheapest; re-opens four audited names, reds `[4b]`/`[4c]`/`[4e]`; the three
  `WideWitness` pins survive because `SwT`'s shape is `.direct`), model the entity-middle half
  (a larger project than `P6`; `CORRESPONDENCE.md:964-973` records it as deliberately
  unmodelled), or teach `isSubjectWildcardUserset` minted leaves (`UsStarWrite.lean:106-109`
  warns it breaks an audited lemma and a constructor field). Wall 2 needs a second decision:
  bridge-GC in the Lean model, or a ref-counted Python presence-guard.
- **A tier-2 stability instrument that actually engages its premises**, replacing the arms that
  returned zero information. Any replacement must gate its verdict on the unmapped-key count
  and must read `reachStableAll`, because a bridge both moves reachability and adds the key —
  one event, both effects — which is how this probe went vacuous at mapped keys.
- **The `two_stratum_cascade` multiplicity re-measure** (expect `1…5`) before any golden is
  regenerated, because a *logged* bridge adds frontier rows (`ckeys := 8`, 4 distinct).
  `affectedKeys` itself needs no code edit — verified: `Cascade.lean:542` guards the own-key
  branch on `d.node.name ≠ STAR`, `:548` skips `v.name = STAR` in fan-out.
- **No `PROOF_STATUS.md` entry was written** — deliberate, to avoid a third copy of one
  statement. The formal entry point instead carries a *pointer*: `formal/HANDOFF.md`'s
  "In flight — `ttuStarFree`" block now names the scope defect and points at the row and the
  probe. If a later session wants the formal ledger to carry the detail itself, that is an
  open choice, not an oversight.
- Unverified and flagged as such on the row: the def-pin closure simulation (242 → 243), live
  `doc_counts` values, `TtuStarWide`'s cone of 1, and the `statement_pin.py::_refs` suffix
  naming trap (mechanism read, not simulated).

---

## 2026-09-10b — `GL-1`: the gate takes a run lock; the "failed successfully" report was two runs, not a broken guard

rows: created and closed `GL-1`; created `GC-1` (open). Nothing re-ranked; `P6` stays
`NOW`, `R6` stays `NEXT`.

task lint: clean (13 checks, 181 task file(s) parsed), 24 warning(s)
read: board only

**The filed diagnosis was wrong, and that is the most reusable part of this entry.**
`3ac7fd2` recorded a `conf-tile:1/5` reporting `EXIT=0` under a log ending `60 failed,
50 passed` / `FAIL: conf (pytest rc=1)`, and reasoned that `verify.sh:270-273` — the
`gate_on_exit` INCONSISTENT branch — "has a hole or its EXIT trap died with everything
else". Neither. Three checks, in the order that settled it:

* The log's own last line is `FAIL: conf (pytest rc=1)` and the ledger row is
  `conf-tile:1/5 FAILED … rc=1`. `verify.sh` detected the failure and exited **1**.
* The EXIT trap was alive — it is what wrote that row.
* Bash preserves an exit status across a *returning* EXIT trap. Tested three ways on
  bash 5.2.26 (trap function ending in a false `[ ]`, in a no-op, in an unexecuted `if`);
  all three gave `EXIT=1`. The guard at `:270-273` covers exit 0 *without* the PASSED
  banner, which never happened, so it was never in play.

**What actually happened: two runs, one filename.** Reading `.gate-runs/ledger.tsv`
column 1 as the START time and column 2 as the duration:

```
run A  started 14:35:01  ran 225 s -> ended 14:38:46   FAILED  60 failed, 50 passed
run B  started 14:36:14  ran 196 s -> ended 14:39:30   PASSED  110 passed
run C  started 14:40:21  ran 190 s -> ended 14:43:31   PASSED  110 passed   ("re-run alone")
```

B started 73 s into A. Both followed this repo's own recipe, which named the FIXED path
`> /tmp/p.log 2>&1; rc=$?`. Two processes redirecting into one path each truncate it and
then write at independent offsets; A emitted 6466 lines and finished first, B emitted ~30
and finished last, so B's banner landed at a low offset and A's failure tail stayed at the
end of the file. `rc` was B's honest `0`. `tail` was A's failure. Reproduced verbatim with
two throwaway scripts before anything was changed.

Three things worth carrying:

1. **This is the third variant of footgun #1 and it needs neither of the first two's
   ingredients** — no pipe eats the status, no orphaned interpreter writes the log. Two
   writers and one filename are sufficient. The session that filed it checked for a stray
   interpreter (correctly, per the 2026-09-08b runbook entry), found none, and concluded
   the guard must be broken — because the runbook offered no third possibility.
2. **The documented fix for footgun #1 created it.** `/tmp/p.log` was prescribed *because*
   piping through `tail` eats the exit code. A fixed log path is a shared resource.
3. **The concurrency is also the most plausible cause of the 60 failures**, which were all
   `rc=3221225794` (`0xC0000142`, STATUS_DLL_INIT_FAILED) on `zcli` spawn — what two tiles
   racing to spawn the same large Lean binary looks like. They were filed as generic
   "fallout from this session's agent fan-out"; the sharper statement is that the gate was
   running twice.

**`GL-1` — the mechanical refusal.** `scripts/gate_lock.py` plus wiring in `verify.sh`
(acquire after `gate_tree_id`, before any phase work; release from `gate_on_exit` after the
ledger row and before the INCONSISTENT `exit`). A colliding run now refuses, nonzero, in
under a second, and lands as `FAILED … rc=1 refused=lock-held` with a 0 s duration — so it
**cannot report success whatever the log says**, which is the property that was missing.
Staleness is age-based (3600 s, > 3x the longest legitimate run) rather than
liveness-based, deliberately: `os.kill(pid, 0)` on Windows calls `TerminateProcess` rather
than probing, so the obvious liveness check would kill the incumbent run, and the recorded
pid is an MSYS pid anyway. Steals are announced; the steal claims the lock by `os.rename`
so two stealers cannot both win.

It also closes the **2026-09-08b orphan variant** as a side effect: `verify.sh` re-execs
itself (parent tees, child works), so the process that survives a harness kill is the
child — which holds the lock and releases it from its own EXIT trap. The next phase
refuses instead of overlapping. One mechanism, both variants.

Sabotage, end-to-end against the real gate (`lean` backgrounded, second `lean` 8 s later):

```
===== SECOND (colliding) RUN: rc=1 =====
REFUSED: another gate run holds the lock, so this run has done nothing.
         wanted phase: lean
         held by phase: lean (pid 16744, started 2026-09-10T19:16:28, 7 s ago)
FAIL: refusing to start 'lean' while another gate run holds the lock.
===== FIRST RUN: rc=0 =====
=== lean phase (steps 1-4) PASSED (holes=0, audits=587, pinned=587) ===
```

Instrument controlled: the lock file was confirmed gone afterwards, and the incumbent's
verdict was unaffected.

**The mutation sweep found the hole again, and then found one in itself.** Eleven
weakenings of `gate_lock.py`; ten reddened a named test. The eleventh — steal a stale lock
by `unlink` instead of `rename` — was **INERT**: no behavioural test in the module can see
the difference, because it only appears when two runs steal at once. Pinned structurally
(a source-reading mirror) with its limits stated, since a genuinely concurrent two-stealer
test would be timing-dependent, i.e. a flaky test inside the gate. ⚠ And the *first* draft
of that same mutation appeared to redden a named test — but only because it died of a
`TypeError` the code's `except OSError` does not catch. **A sweep row can be green for the
wrong reason exactly as easily as a test can**; the instrument needed sabotaging as much as
the subject did. That is now three consecutive additions where the module sweep earned its
keep.

**`GC-1` — the `ZT-P3-5` recurrence `TK44` found.** One measurement stated four ways with
four different values, two of them contradicting inside a single module. Live figure,
measured today via `test_report_cell_coverage`: `UNKNOWN 404 (31.7%)` of 1275 cells, `ci`,
K<=2. The cause is ordinary: the four sentences measured different things (HIT-only vs
HIT+REJ, `ci` vs `deep`, this tree vs the frozen prototype), so all four could be written
in good faith and no two agree. ⚠ **The commit that documented the drift introduced a fifth
wrong value** — `docs/sabotage-procedure.md` gained "roughly a quarter", obtained by
pairing one instrument's floor with another's framing. All four are now deleted and point
at the one home. The check that would have caught them is still owed and is on the row,
along with why widening `check_restated_counts` is not free.

That check did fire on this session, though, which is the confirmation it is live: a
"Still owed" bullet written for this entry said `17 tests` and `handoff_lint` refused
`HANDOFF.md:41` on the spot. The number was deleted rather than updated, per its own
instruction.

**`MIN_TESTS_ALL` 1094 → 1131**, with the instrument check the knob's provenance requires:
at 1132, `tests-tile:1/4` fails with `FAIL: tests/ collects only 1131 test(s); the gate
floor is 1132.` and `rc=1`; restored to 1131, which passes. Of the 37 raised, only 20 are
this session's new tests — **17 were already unratcheted** on `3ac7fd2`, the third
consecutive raise to find pre-existing headroom. Carried as a "Still owed" bullet.

GATE: all ten phases green on this tree — `lean` holes=0 audits=587 pinned=587;
conf 110/109/109/109/109 (546); tests 283/283/283/282 (1131). `FINAL_REVIEW.md`'s counts
block regenerated for the floor raise (`tests/` collected 1111 → 1131).

Still owed: nothing skipped.

---

## 2026-09-10 — `TT-8` landed (fence-aware banner) and `TK53` closed: 15 appends dispositioned, 4 verdicts overturned

rows: closed `TT-8`, closed `TK53`; dispositions logged on `TK3` `TK4` `TK6` `TK11` `TK15`
`TK28` `TK33` `TK34` `TK35` `TK36` `TK38` `TK39` `TK43` `TK44` `TK50`. Nothing re-ranked;
`P6` stays `NOW`, `R6` stays `NEXT`.

task lint: clean (13 checks, 179 task file(s) parsed), 23 warning(s)
read: board only

**`TT-8`.** `task.py::extract_banner` is now fence-aware and refuses two `## Banner`
headings instead of silently picking one. The sabotage was built BEFORE the fix, against
the `git show HEAD:` extractor on a temp copy of the live corpus, and reproduced the bug:
`check 12 failures: 0` for a banner that existed only inside a fence, and `0` again for two
real banners. Post-fix, both go red. Each of the three new clauses was certified standalone
against the pre-fix tool, because clause 5 fires first and would otherwise mask 6 and 7.

The mutation sweep is the part worth carrying. Twelve narrow weakenings; **seven left every
test green** — tracking ` ``` ` but not `~~~`, requiring a column-0 fence, a naive toggle,
an `==` close-marker length test, letting an info-string line close a fence, dropping the
filename from the refusal, and tracking only the first fence in the file. The gap was
uniform: the original clause wrote ONE fence shape, so what was unguarded was the fence
*grammar*, not the fence. Five clauses plus a filename assertion close all seven. This is
the second consecutive check where the module sweep found holes the single sabotage missed,
which is now evidence for the 2026-09-08b rule rather than an anecdote.

**`TK53`.** All 15 remaining appends are dispositioned: 11 landed, 3 were already carried
(`TK15`, `TK33`, `TK34`), 1 superseded (`TK6` — its destination, a `P4` board row in
`HANDOFF.md`, was abolished by the 2026-09-06 cutover; the file is 49 lines with zero table
rows). `tasks/` no longer sole-homes any of the fifteen statements, which is the condition
this row existed to reach. The individual `TK` rows stay OPEN on purpose: landing a
statement discharges the sole-home problem, not the underlying question.

Method, and it is the reusable part: each destination doc got a verify pass and then an
adversarial refute pass, grouped by destination so a doc was read twice rather than fifteen
times. **Every one of the eleven drafted appends carried at least one factual defect, and
four verdicts were overturned between the passes.** Caught before writing: a claim that
`install_paranoia` is not wired into `ConnectedStore` (it is, `store.py:193` — the true and
sharper statement is that `DEFAULT_PARANOIA` is `PARANOIA_OFF`), a severity error calling
the `BL-1` leak answer-level when it is recorded STATE-ONLY and explicitly not a fail-open,
a mis-description of what spec §10 conditions its non-goal on, and a link form already known
to resolve to the wrong file. A single-pass sweep would have written all of them — which is
exactly what the row's own re-verify trap predicted.

The refuters were wrong once too, so nothing was transcribed: one claimed perf lead `A10`
rewrites the `_bumped` fan-out, where the audit (`:857-862`) says it routes onto
`_reconcile_subject`, a different §7 gap. The weaker accurate claim is what landed.

`TK35`/`TK36` were **re-homed** from `docs/specs/wildcard-materialization-spec.md` to
`docs/spec-deviations.md`. `docs/README.md:122-124` holds `docs/specs/` frozen at landing
*by hand* — nothing walks it — so a dated append into a spec body looks legal and is not.

`TK44` surfaced a live `ZT-P3-5` recurrence in passing:
`tests/test_generator_coverage.py:68` (~19%) and `:428` (~28%) state one measurement with
identical wording and different values *inside a single module*, against `:1152` (~30%) and
`sabotage-procedure.md`'s "roughly a quarter". `check_restated_counts` cannot see it — wrong
file type and wrong pattern, out of scope twice over. Recorded in the landed text, with
`::test_report_cell_coverage` named as the single live source.

Still owed:
- **The ledger receipt vocabulary still has no token for "entered via `show`"** — carried
  unchanged from 2026-09-07b and 2026-09-08b. Still unfiled; file it or extend
  `handoff_lint.py::check_session_receipt`'s vocabulary.
- **`TT-8` left one behaviour unpinned by a clause, deliberately:** a fence *inside* the
  banner section now counts as banner content, so such a corpus fails the 14-line cap rather
  than truncating silently. Correct, but observed rather than designed-and-tested.
- **A percentage has no mechanical guard anywhere.** `TK44`'s four divergent figures are
  now described in `sabotage-procedure.md`, but nothing refuses the next one. Extending
  `check_restated_counts` to percentages, and past top-level markdown into `.py` docstrings,
  is unfiled work.

## 2026-09-08b — `TK58` landed: handoff_lint refuses a restated corpus count, the repo's oldest defect class

rows: closed `TK58`. Nothing re-ranked; `P6` stays `NOW`, `R6`/`TK53` stay `NEXT`. Batch 4
was the last of the `TK57`–`TK65` set that was going to be built; `TK62` stays declined.

task lint: clean (13 checks, 179 task file(s) parsed), 23 warning(s)
read: board + note

**The task.** Finish `TK58` — the scoped-down `count_guard` — which the previous session
censused but did not build. `scripts/handoff_lint.py::check_restated_counts` is the twelfth
check in `CHECKS`, so it rides `verify.sh` step 4f and was gated on arrival with no
`verify.sh` edit. It refuses `N checks` / `N open tasks` / `N tests` in `CLAUDE.md`,
`HANDOFF.md`, top-level `docs/*.md` and `tasks/*.md`. `docs/README.md` §1 has forbidden this
in prose since the doc system was written and nothing enforced it, which is why `ZT-P3-5`
kept recurring; the rule now has a mechanism.

**The census on the row was re-derived first-hand rather than trusted, and one of its
conclusions did not survive.** It reported 87 raw hits and 7 true live claims under a wider
pattern set. Re-measured with the three agreed patterns plus the escapes: **6** live claims,
all of them restated *test* counts, and every one fixed in this commit by DELETING the number
and pointing at its home — `docs/gate-runbook.md` ×4 (including a `MAX_TESTS_SKIPPED_ON_RDBMS`
value restated in prose, the exact footgun `CLAUDE.md` names for `MAX_TESTS_XFAILED`),
`docs/sabotage-procedure.md` ×1, `CLAUDE.md` ×1. The row's `TK62:19` and `CLAUDE.md:16` claims
are NOT caught by the landed patterns and the check does not pretend otherwise.

**The escapes, and the one the row got right.** AMENDMENT 1 on the row was correct and
load-bearing: a per-LINE date-stamp skip sees nothing in `docs/spec-deviations.md`, whose
3511 lines carry their date on the `## <date>` heading. Keying the exemption on the FILE's
liveness banner (`FROZEN` / `ACTIVE-PLAN` / the append-only form of `LIVING`) is what makes
the check survivable. Five escapes ship: fence, quoted span, dated line, banner, and a task
file's append-only `## Log`.

**Each escape was measured, not argued.** Disabled in turn against the live corpus, counting
what each suppresses: banner **+8**, dated-line **+4**, task `## Log` **+1**, quoted-span
**+0**, fence **+0**. ⚠ The last two suppress nothing today — the exact state the archived
`count_guard`'s FROZEN exemption was caught in — so they are kept only because each has a
test that is now their whole justification. An escape that suppresses nothing AND has no test
is decoration.

**The retrospective control is stronger than the sabotage, and it is why this was believed.**
Run against the parent commit `966f6aa`, the patterns report BOTH figures the 2026-09-08
session found by hand (`gate-runbook.md:285` "Three checks", `:365` a stale `handoff_lint.py`
count) plus four the same reader walked past. Real, independently-confirmed rot from before
the check existed. The invented sabotage — one true-today sentence appended to the banner —
reddens naming `HANDOFF.md:30` and the token; the same line re-prefixed `Measured 2026-09-08:`
goes silent, so the check judges the escape and not the line's shape. Baseline green in the
same session, both restored.

**⚠ The finding of the session is in the INSTRUMENT.** A sabotage certifies the case you
sabotaged; the seventeen tests written around the check were seventeen unverified claims. So
ten one-line weakenings were applied to `check_restated_counts` in turn — the edits a future
session would actually make, not deletions — and the module run against each. Nine reddened
by exactly the test that claimed to guard them. The tenth, widening the `checks` pattern to
allow an intervening word, **broke the check while the whole module passed**, because the test
owning that property asserted on one of the three patterns. No amount of re-reading the check
would have shown it. Fixed, sweep now 10/10, and the transferable rule is filed as
`docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations".

**Also measured, and rejected:** widening the corpus pattern to allow an intervening word
("the 65 still open tasks" is a census the immediate form misses). Against the live tree it
found zero new real claims and one false red — `docs/tasktool-spec.md:420`, a capacity RULE.
Uniform immediacy is a measured trade, not a symmetry argument.

**The check caught its own author within the hour**: the new `sabotage-procedure.md` section
said "all seventeen tests passed", and `handoff_lint` refused it. Fixed the prescribed way.

**Where the coverage lives, deliberately split.** `tests/test_handoff_lint_count_guard.py`
pins the MECHANISM on synthetic corpora only. There is no live-corpus assertion, and that is a
gate-hole argument rather than taste: the pytest tiles key off `t2c`, which excludes `*.md`
outside `tasks/`, so a corpus assertion would stay "green on this tree" after someone edited
`docs/gate-runbook.md`. Corpus coverage belongs to 4f/`lean`, which keys off `t2a`.

**A second trap, hit while gating this and now in the runbook.** The tiles were run as a
`for` loop; the harness killed the loop at the cap and the SHELL died while its `pytest`
child kept running. The next phase overlapped with that orphan, they shared a log file, and
a phase that reported `EXIT=0` had a log ending in `25 failed, 252 passed` — the failures
being the orphan's, with `rc=3221225794` (Windows DLL-init) from two runs fighting over
process handles. `25 + 252 = 277` is exactly the clean re-run's count, which is what
identified it. One phase per command; on a code/log disagreement, check for a stray
interpreter and re-run alone to a fresh log rather than debugging the red.

**One pre-existing test had to change**, and it was pinning the wrong property:
`test_handoff_lint_b_prime.py::test_the_two_checks_are_in_the_list_and_the_receipt_is_last`
asserted `check_session_receipt` is LAST in `CHECKS`. Its own docstring says the rule is
"appended, never inserted" — but last-ness makes the next legitimate APPEND fail while
still permitting an insertion anywhere after it. Now pins the INDEX, renamed
`..._and_nothing_was_inserted`. `formal/FINAL_REVIEW.md`'s counts block regenerated
(`tests/` 1094 → 1111).

Still owed: nothing. `docs/README.md` §1 now states what is enforced and what is not
(`docs/history/`, `docs/specs/`, `docs/architecture/`, `formal/`, and a task `## Log` are all
out of scope); `docs/sabotage-procedure.md` carries the mutation-sweep rule and
`docs/gate-runbook.md` the orphaned-child trap.

---

## 2026-09-08 — `TK59` landed: lint check 14 resolves every `## Read first` pointer; it found 25 dead ones

rows: closed `TK59`. Censuses appended to `TK58` and `TK59` before any code; follow-on note
on `TK66`. Nothing re-ranked; `P6` stays `NOW`, `R6`/`TK53` stay `NEXT`. `TK58` scoped and
censused but NOT built — see Still owed.

**The task.** The user asked what was left of the `TK57`–`TK65` sweep and what it would take
to finish batches 3 and 4 this session. Answer, given up front: not both. Each is a session
plus a ten-phase gate. Batch 3 (`TK59`) was taken; batch 4 (`TK58`) was censused so it starts
from measurement instead of from the plan's assumptions. `TK62` stays declined.

**Both batches were RED ON ARRIVAL as specified, and that is the finding that shaped the
session.** Two read-only subagent censuses ran before any code (the delegation rule: push the
bulky reading out, keep the table). Load-bearing claims from both were re-verified first-hand
before being written anywhere — a subagent report is evidence, not a finding.

**1. What check 14 found (`TK59`).** 25 dead pointers across 24 of the 66 open tasks. 22 were
one line: a citation of a checker deleted with `.scratch/tasktool/` on 2026-09-07. `R6-1`
recorded that deletion and `TK61` reworded ONE of the 22 copies; the other 21 kept sending
every formal session to a file that does not exist. Verified by hand:
`git ls-files | grep -c 'migrate.*\.py'` → `0`. The rest were bare basenames whose real homes
are under `formal/` (`test_conformance_enum.py`, `verify.sh`, `Cascade.lean`,
`UsStarWrite.lean`).

Two FALSE GREENS a path-only check cannot see: `TK39` and `TK43` link `[README.md](README.md)`
and cite `:399` / `:142` / `:150`. From `tasks/` that resolves to `tasks/README.md` — **86
lines**, against the root README's **660** (both measured 2026-09-08). Repointed by hand; the
check does not catch that class and its docstring says so rather than implying otherwise.

**The corpus was swept BEFORE the check landed**, so it shipped green rather than red — a
check that is red on arrival is a check someone deletes. 22 boilerplate lines retracted, and
the retraction DESCRIBES the deleted checker instead of naming it, because a retraction that
names a dead file leaves a dead pointer. That is the same conclusion 2026-09-07b reached about
a minted-shape id it could not quote; the 13 `R6-N` lines `TK61` reworded had the identical
defect and got the identical treatment. 17 `python task.py show <id>` entries were rewritten to
the spelling `HS-5` already used, `python scripts/task.py show <id>` — they then resolve as
paths, so **check 14 needed no special rule for CLI entries at all**. A rule not needed beats a
rule handled.

**2. The two false reds, which are the useful part.** The first version of check 14 reported 22
dead pointers on a clean tree: the token cleaner stripped `.` from both ends and ate the `../`
off every relative link — the checker eating its own input. The second version reported a fresh
batch: code spans were read before markdown links were removed, so the LABEL of
``[`FINAL_REVIEW.md`](formal/FINAL_REVIEW.md)`` was resolved as a path and called dead while
the target beside it resolved fine. **That is the identical false positive
`handoff_lint.py::check_doc_links` records 32 of and warns about in its own docstring** — read
during this work, and reproduced anyway. Both are recorded in `check_read_first`'s docstring,
because both are the obvious way to write this and both look right.

**3. Sabotage.** Four runs on the live tree, each restored, plus two permanent fixture cases
(`tests/test_tasktool.py::test_sabotage_rf_path`, `::test_sabotage_rf_symbol`, counted in their
own bucket so the 2026-08-21 transcript's 22/22 still means its own 22). Baseline green first,
so every red is attributable. Renaming a cited `.py` reddens — the class no other check here
can see, since `check_doc_links` matches `.md` only. A stale `file::symbol` reddens. The floor
fires when raised. And the one that matters:

```
FAIL: check 14 resolved only 0 read-first pointer(s) across the open tasks,
floor min_read_first_pointers=150.
```

an early `return []` in the tokeniser. The first three only prove the check notices broken
DATA; only the fourth asks whether it notices itself having stopped looking.

**4. Design decisions that departed from the agreed plan, each because the corpus said so.**
EITHER ROOT rather than renderer-strict: 130 of the corpus's links are root-relative and 11 are
`../`-relative, and zero were dead under both, so a strict rule would fail 130 live pointers.
Line RANGES (`:190-191`) strip too — the plan anticipated only `:190`. The instrument control
lives in `tasks/config.json` as `min_read_first_pointers`, not as a module constant, because a
constant sized for the live tree reddens every fixture and "make the fixture pass" is how a
floor gets deleted; 209 pointers resolved live (measured by raising the floor until it fired),
floor 150, headroom **on purpose** because the quantity is not monotonic — closing a task takes
its whole section with it.

**5. Two limits stated rather than left to be discovered.** The floor is skipped when the
corpus offers no read-first entries at all, so blinding the SECTION extractor evades it — not
silently (every task then trips a warning) but genuinely more weakly than the tokeniser half.
And `ZANZIBAR_TASK_POINTER_ROOT` is an escape hatch for one caller: a `tasks/` tree copied out
of the repo is severed from the files its pointers name. Deriving that root from `__file__` was
tried and is wrong — the sabotage harness runs patched COPIES of the tool out of a temp
directory, so `__file__` there names a repo that does not exist.

**6. Three live wrong figures, found by `TK58`'s census and fixed.** `docs/gate-runbook.md:285`
said three checks run inside `lean`; `verify.sh` echoes `[4a/7]`…`[4g/7]` — seven.
`docs/gate-runbook.md:365` named a stale `handoff_lint.py` check count; `CHECKS` at
`handoff_lint.py:890-904` has eleven entries, `check_session_receipt` having been appended
2026-09-06c without the prose being updated. Both verified by hand, both **rot introduced by
the very sessions that added the things they miscount**, both in the file a session reads to
run the gate. `docs/tasktool-spec.md`'s check-count sentence was the third and went wrong the
moment check 14 was appended — `ZT-P3-5` inside the spec for the tool built to cure it. All
three fixed by DELETING the restated number and pointing at the tool that prints it, the
`TK60`/`TK61` precedent, not by writing a fresh number that rots again. The runbook was also
missing a `4g` entry entirely; added.

**`TK58`'s census, on the row.** 87 raw hits in the agreed scan scope: 7 true live claims, ~65
evidence, 15 pattern false positives. 61 of the 80 non-claims collapse under ONE file-level
exemption, leaving ~26 lines to adjudicate. The agreed per-line date-stamp skip **provably does
not work**: `docs/spec-deviations.md` contributes 35 hits and dates its `##` headings, not its
body lines, so the exemption must key on the file's liveness banner. Pattern (b) needs a word
boundary — it matches "6 row" inside `R6-6` and "00 row" inside `1.00 row/edge`. And the row's
own sabotage instruction contains the literal it tells you to write, so the check fires on its
own design spec.

task lint: clean (13 checks, 179 task file(s) parsed), 23 warning(s)
read: board only

Still owed: `TK58` (batch 4) scoped and censused but not built — deliberate, two ten-phase
gates did not fit in one session, and everything needed is on the row. The ledger receipt
vocabulary still has no token for "entered via `show`" (carried from 2026-09-07b, unfiled).

---

## 2026-09-07b — six of `TK57`–`TK65` landed; `task.py lint` is INSIDE the gate as `[4g/7]`; `TK66`/`TK67` filed

rows: closed `TK57`, `TK60`, `TK61`, `TK63`, `TK64`, `TK65`. New `TK66`, `TK67` (both
`LATER`). Planning notes appended to `TK58`, `TK59`, `TK62` — agreed with the user, not
started. Nothing re-ranked; `P6` stays `NOW`, `R6`/`TK53` stay `NEXT`.

**The task.** The user asked for a fix plan across `TK57`–`TK65`, then for batches 1 and 2
of it to be executed and batches 3 and 4 to be written down as todos. Batches 1 and 2 are
below; 3 and 4 are recorded on `TK59`/`TK62` and `TK58` respectively, as decisions rather
than as sketches, so the next session does not re-litigate them.

**1. `task.py lint` now runs inside the gate (`TK57`).** New `verify.sh` step `[4g/7]`,
alongside 4f, with the same exit-code branch; `4a`–`4f` renumbered from `/6`. Until this
landed, exactly ONE of the tool's lint checks reached the gate, indirectly, via
`handoff_lint`'s tree fallback — everything else was covered only by the tool's own unit
tests against synthetic corpora, never against the live tree.

**The first sabotage was discarded as non-attributable, which is the part worth keeping.**
The obvious break — a second `NOW` row, the sabotage `TK57` itself proposed — is caught by
4f as well, so the phase would have gone red one step early and proved nothing about 4g. A
sabotage has to break something *only* the new step sees. Used instead a dangling dep
(`deps: []` → `deps: [NOSUCH1]`). Observed, both steps on one tree:

```
4f  handoff_lint: clean (11 checks)                                  rc=0
4g  --- [4g/7] task tree lint (scripts/task.py lint) ---
    task lint: 1 violation(s)
      FAIL: .../TK66-....md: dep 'NOSUCH1' resolves to no task (open or closed).
    FAIL: task tree lint (see above)                                 rc=1
```

The `=== lean phase … PASSED ===` line did not print — that is the wiring under test, not
the lint. Control: restored tree, `task lint: clean`, rc 0. **4f green with 4g red on one
tree is the entire justification for the step.**

**A zero-headroom pin caught the sabotage itself, and it was right.** The first run used a
dangling dep in the tool's OWN minted shape (the id prefix plus three digits). Writing that
id into this ledger turned `test_shipped_config_is_measured_not_an_example` red: it pins,
with zero headroom, that exactly ONE token of that shape repo-wide resolves to no task —
the hypothetical one in `task.py`'s retired-ids comment. The invented dep was a second. The
pin was NOT exempted; the sabotage was re-run with `NOSUCH1`, which is not minted-shape, and
all three records rewritten to the re-observed output.

Two things make it worth the ledger space. The failure came from a *record* of a test rather
than from code — prose in this file is inside that pin's blast radius. And the first fix
attempt failed the same way, because the write-up quoted the offending id verbatim while
explaining it: **you cannot name that token in tracked prose at all, only describe it.** The
next session writing up a dangling-dep sabotage will hit both walls.

**2. Two message defects, both halves of one 2026-08-21 pair (`TK64`, `TK65`).**
`handoff_lint`'s zero-`NOW` failure printed the `> 1` branch's sentence ("two of them is no
ranking at all") on a count of zero; it now prints one sentence true on both sides, ported
from `task.py::check_pri_budget` where it was fixed 17 days ago. The two checkers had
disagreed about one invariant that whole time. Sabotage: reverted the message only, watched
the new test go red on the literal old string, restored, 48 passed. `task.py::check_parses`
rendered an empty list as a bare `-`; now `(none)`, matching the four existing sites.
Pinned by extending the existing sabotage test rather than adding one.

**3. Two restated counts deleted rather than guarded (`TK60`, `TK61`).** `R6`'s parent
census ("10 `LATER`, 3 `HOLD`, 6 closed") is gone, replaced by the query that derives it —
no check 14 spent, and nothing left to drift. Two things surfaced doing it: the census
claimed to be generated by `migrate.py::r6_census`, which has not existed since 2026-09-07;
and `R6` now has **37** children, not 19 (`TK17`–`TK32`, `TK47`, `TK48` are parented there),
so the old census silently meant "`R6-N` only" and had a caveat bolted on to say so. The 13
open `R6-N` bodies citing `migrate.py` as refusing to build on a count change were reworded
to point at the section and say the section is the only home for the number — deliberately
*not* by deleting the parenthetical, which would leave an unattributed bare "five". One
instance is left on purpose in `tasks/closed/R6-6`: closed rows are as-of-then records.

**4. `P4`'s do-not-cancel warning, and a class that is bigger than `P4` (`TK63` → `TK66`,
`TK67`).** `tasks/P4` Traps went from "None recorded" to the warning as a POINTER, not a
copy — `formal/history/` is append-only, so a copy is a second home for a statement nothing
updates. **Both line citations on `TK63` were wrong** and were corrected by reading them:
`leaf-family-split-scope-2026-08-05.md:1082` → `:1099`, and `PROOF_STATUS.md:247` → `:5146`.
A row filed to say a trap must cite something that exists cited two things that did not,
which is why the resolver planned on `TK59` now checks the path only and never the line.

A read-only subagent sweep of `formal/history/` + `docs/history/` for forward-binding
directives found **17 that no live file surfaces**. Filed as `TK66` with the table marked
explicitly unverified — a subagent report is evidence, not a finding, and one line number in
it was already wrong. One row was verified first-hand and split out as `TK67` because it is
worse than unsurfaced: `PROOF_STATUS.md:4897` records "`FoldAdmits` lockstep: 21 sites MOVE,
3 MUST STAY", explicitly correcting "all 24 in lockstep" — and `formal/HANDOFF.md:227` and
`tasks/P6` both still said "in lockstep" unqualified. **A session following the file that
every formal item is told to read first would have moved three sites that must not move.**
Both live sites annotated; confirming the three sites against the current Lean tree is the
open work on `TK67`.

**5. Batches 3 and 4, recorded not done.** `TK59` (read-first pointer resolver, check 14 —
now cheaper, since 4g means it is gated on arrival). `TK62`: the figure-equality check is
**declined**, not deferred — the audit is prose carrying a known internal contradiction
(`TK48`), so a checker keyed on it is red-on-arrival or subtly wrong; the honest subset
rides `TK59`. `TK58`: port `count_guard` **scoped down** to three patterns over non-history
files as a `handoff_lint` check, keeping the two load-bearing rules (an exemption is an
assertion; no baseline regeneration).

**Not done / owed.** Nothing owed. Note for the next session: the receipt vocabulary has no
token for "entered via `show <id>`", which is what this session actually did — see the read
receipt below.

```
task lint: clean (12 checks, 179 task file(s) parsed)
```

read: board only — with a caveat the vocabulary cannot express: `task.py board` was never
run. Entry was straight to `show TK57`…`show TK65` on a user request naming the ids, so the
query surface replaced the note, but the *banner* was not read at start either. `board only`
is the closest of the two permitted tokens and is not exactly true. `formal/HANDOFF.md` was
opened later, to fix `TK67`, not to orient.


---

## 2026-09-07 — `.scratch/tasktool/` defused and transcribed; 9 never-fixed findings filed as `TK57`–`TK65`

rows: `TK57`–`TK65` (new, all `LATER`/`SOMEDAY` — the findings rescued out of the deleted
directory; nothing re-ranked, the `NOW`/`NEXT` set is untouched). All nine carry
`related: [TT-1]` on a user call, tagging them to the task-tool migration family; `related`
rather than `parent` because `TT-1` is closed and `check_parent_open` refuses a closed
parent.

**The task.** Defuse the `migrate.py` landmine the banner warned about, then rescue
whatever in `.scratch/tasktool/` was worth keeping so the directory can be deleted. Scope
confirmed with the user as `.scratch/tasktool/` only, **not** all of `.scratch/` — several
tracked files cite other scratch material by path, including from Lean sources
(`formal/lean/ZanzibarProofs/FullScope.lean:380`).

**1. The landmine was real, and worse than the warning said.** The warning was that
`--rebuild` destroys hand-filed tasks. Tested against throwaway copies of `tasks/`: aimed
correctly (`--out` = the tree's PARENT) the manifest guard holds exactly as designed,
rc 4, naming all 168 ids, corpus unchanged. Aimed one level deeper, at the corpus directory
itself — which is literally named `tasks/`, so it is the natural mistake — it printed
`manifest guard: ... matches migrate-manifest.json exactly; nothing hand-filed or
hand-edited is at risk` and deleted 68 of 171 files, **at rc 0, with no `--force`**. There
was no manifest at that path. The guard inventories `<out>/tasks/` while the wipe deletes
`<out>`: the scan path and the destruction path are different paths, and only one of them
was reasoned about. That is a guard that fails by passing, so the file was made inert
rather than left guarded — whole body commented out behind a two-statement refusal, rc 2 on
`--rebuild`, on `--rebuild --force` and on `--help`, verified against a fresh copy. The
comment-out is byte-reversible and that was verified too, round-tripping to the recorded
`sha256 68d95d94…`.

Correction to the retired warning: it said **51** hand-filed tasks. The refusal names
**all** ids in the tree.

**2. Nothing tracked depended on the directory.**
`git grep -E "(open|Path|import|sys\.path)[^#]*\.scratch"` over `*.py`/`*.sh` returns zero
hits; all ~30 tracked references were prose. Nine of them cited it **by section**, as
evidence, which is why the archive doc transcribes those referents rather than summarising
them.

**3. What was rescued**, into
[`docs/history/tasktool-scratch-archive-2026-09-07.md`](tasktool-scratch-archive-2026-09-07.md)
(FROZEN): the cited sections (`COVERAGE.md` §C5, `PROOF.md` §2d, `PROOF2.md` §1,
`PROOF3.md` §1a and the J-26 non-membership grep, `INTEGRATION.md` §5.2, `fix-tool.md`
BLOCKER 1, `inventory-formal.md` MISSes #2/#4/#5); the decisions that were never written
into the spec (the positive-claim retirement rule, the "a write op must never manufacture a
state lint calls red" rule, no-auto-repair, empty `pri`/`size` on closed records, the board
as a query, the Sonnet-safety principle); `SYNC-SPEC.md`'s two surviving design points; and
the `count_guard.py` design, since the tool itself is gone.

Two scripts were PORTED rather than described, because both are cited by live instructions
in tracked files: `scripts/measure_glyphs.py` (`scripts/task.py` says "re-run it after any
bulk import") and `scripts/measure_stale.py` (`tasks/config.json` says "re-derive with"
it). Both retargeted at the tracked tree; `measure_stale.py`'s hardcoded
`TODAY = date(2026, 8, 21)` became `--today`, since a hardcoded clock turns a measurement
into a fixed answer that looks plausible forever. **The first tracked run of
`measure_glyphs.py` reports 12 unmapped code points**, so `ASCII_FOLD` is not currently
complete for the corpus — recorded in its comment at `scripts/task.py`, not filed, because
the tracked pin (`test_banner_is_ascii`) deliberately covers the banner only.

**4. Three stale statements found in LIVING files, unrelated to the deletion.**
`docs/tasktool-spec.md:20` still told readers "Write ONLY inside `.scratch/tasktool/`. The
main repo is READ-ONLY" — a build-era constraint that survived graduation by nine days and
would have sent a reader to exactly the wrong place. Its `:235` and `scripts/task.py:511`
both justified never existence-checking a `source` path on the grounds that "this corpus
lives under `.scratch/`", untrue since the tree was tracked (the rule is right; the reason
was not). And `:480` pointed at `sandbox-migrated/tasks/config.json` for the live config
values. All three corrected in place.

**5. Nine findings that were never fixed**, each re-verified first-hand before filing —
a subagent's report is evidence, not a finding. `TK57` `formal/verify.sh` has no `task.py
lint` step (`grep -c 'task\.py' formal/verify.sh` → **0**), so eleven of twelve tree checks
reach the gate only through the pytest tiles; the 4g patch was graduation condition 21 and
never landed. `TK58` `count_guard.py` never graduated, so there is no mechanical guard
against a restated corpus count — this repo's most-recurring defect class. `TK59`
`LINKED_DOCS` excludes `tasks/`, so no task file's `## Read first` pointers are resolved by
anything. `TK64` `handoff_lint.py:439` still prints the `> 1` branch's sentence on a
zero-`NOW` failure, fixed in `task.py` and never ported back. `TK60` no parent-census
check, deferred through three renumberings. `TK61` thirteen `R6-N` bodies cite `migrate.py`
as the guarantor of their trap count — a citation to something that no longer exists.
`TK62` nothing checks the `R6-N` transcribed figures against the audit. `TK65` the
`missing keys -` cosmetic, the unfixed half of a fixed pair. `TK63` the "do not cancel
`P4`" warning is one hop away in `formal/history/` and `tasks/P4` records no traps — which
matters more since the cutover made the tree sole authority.

**A note on the read receipt.** The vocabulary is `board only` / `board + note`, and
neither is a true description of this session: it was handed a specific task, read the note
(and `CLAUDE.md`) but never ran `board` to choose work, and ran `board` only at the end to
check the banner edit. The check cannot express that, so the cheapest compliant answer is a
claim that did not happen — a small fail-by-passing shape in the receipt itself. Recorded
here rather than filed, since it is a one-line vocabulary question for whoever next touches
`READ_VOCAB`.

task lint: clean (12 checks, 177 task file(s) parsed)
read: board + note — with the qualification in the paragraph directly above: the note was
read to start, the board only at the end.

**The deletion.** Done at the end of the session, to the **Windows Recycle Bin** on a user
call rather than `rm -rf`: 14,916 items, 78.2 MB, restorable from
`C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index\.scratch` until the bin is
emptied. Confirmed present in the bin by enumerating `Shell.Application.Namespace(10)`
rather than by trusting the delete call's silence. (Sizes quoted as "~120 MB" earlier in
the session came from `du -sh`, which reports block-rounded disk usage and over-reports
badly across ~15k small files; 78.2 MB is the byte sum.)

**Still owed:** nothing.

---

## 2026-09-06d — Phase B′ cutover LANDED: tree sole authority, `HANDOFF.md` one-hop, `sync`/`ack`/check 13 retired

rows: `TT-1` (closed — this commit), `TT-2` (closed — retired with `sync`), `TT-8` (new, LATER:
the audit's deferred finding), `DW-1` (comment: the `ttuDirect` trap moved into its Traps),
`P6` (untouched, still `NOW` mechanically)

task lint: clean (12 checks, 168 task file(s) parsed)
read: board + note

**Task (user go, verbatim: "yes let's get the switch all done, you can use subagents or
ultracode to farm the validation out").** The cutover per
[`tree-sole-authority-spec-2026-08-29.md`](../tree-sole-authority-spec-2026-08-29.md)
(ii)/(iii)/(v), as ONE revertable commit — the commit message carries the `git revert`
line. To undo the whole thing: revert that one commit; nothing else moved.

**What changed, by surface:**

* `scripts/task.py` — lint check 12 reads the banner from the `## Banner` blockquote of
  `<root>/HANDOFF.md` (`note_path`, `BANNER_HEADING`, `extract_banner`) and fails on a
  reappearing `tasks/BANNER.md`; `board` reads the same; check 13 (`check_board_sync`)
  deleted, number never reused, `lint` prints `12 checks`; `sync` and `ack` stay in the
  parser with every old flag SUPPRESSed and dispatch to `retired_verb` → rc 2, `task <op>:
  REFUSED`, the cutover date, the replacement (`comment`), and `Nothing was read or
  written`; `source_hash` frozen (check 4 still validates its shape).
* `scripts/handoff_lint.py` — `MAX_LINES['HANDOFF.md']` 260 → 60; `READ_VOCAB` →
  `('board only', 'board + note')`; still 11 checks. `scripts/gate_status.py` —
  `CODE_SCOPE_MD_KEEP` names `tasks/` and `HANDOFF.md`, so the tiles' tree id covers the
  note too.
* `HANDOFF.md` 246 → ≤60 lines: `## Banner` (≤ `BANNER_MAX_LINES`, first line carries the
  session key, `ASCII_FOLD`-mappable glyphs only), `## Still owed`, `## Next session`. No
  table, no item blocks, no `Closed ids` lines (the three item blocks were reconciled into
  their task files on 2026-09-06b). `tasks/BANNER.md` DELETED.
* Docs — Rhythm → `docs/README.md` §7, "Where things live" → §8; `CLAUDE.md` start-here
  rewritten (query first, the note is one hop, the receipt rule with the new vocabulary,
  the backtick trap), trap 2 (frozen history status lines) promoted into its
  Gotchas; trap 1 (`ttuDirect`) → `DW-1` Traps; `tasks/README.md`, `docs/tasktool-spec.md`
  (§4 "The retired verbs", §5 twelve checks + check 13 RETIRED), `docs/latent-gaps.md`,
  `docs/architecture/overview.md`, `docs/spec-deviations.md`, `docs/gate-runbook.md`,
  `benchmarks/results/PERF_ANALYSIS.md` re-pointed from "the board" to the tree; the
  trial stub, the spec and the protocol flipped to FROZEN with dated landed notes
  (protocol §6 `2026-09-06d`, E1–E3).

**Tests** (re-measured with `--collect-only`, 2026-09-06d): `tests/test_tasktool.py`
92 → **94**, `tests/test_handoff_lint_b_prime.py` 30 (unchanged, edits only).
Ten `sync`/`ack` tests became `test_retired_verbs_refuse_every_old_argv_shape` (11
argv shapes); new `test_lint_check_12_refuses_a_reappearing_tasks_banner_file` and
`test_lint_reads_no_board_and_check_13_is_gone`; check-12 test gained the no-heading and
empty-section clauses. Three sabotage cases RE-POINTED and RE-RUN, observed lines in
their docstrings: `test_sabotage_bprime_check_13_can_go_blind` (`'sync'` dropped from
`OPS` → `sync --check` was not refused (rc=1)`), `test_sabotage_bprime_ack_adoption_can_skip_the_flip`
(citation reworded → `task ack: REFUSED` without the cutover line, red),
`test_sabotage_wp_ack_does_not_move_moved` (`comment --mechanical` hard-wired to progress
→ `moved` 2026-08-21b → 2026-08-21c: a review laundered a stale row into a fresh one).
The four `test_sabotage_live_*` cases went green only once the live `HANDOFF.md` and
`tasks/BANNER.md` were in the final shape — before that they reported the four check-12
violations of the pre-cutover tree, which is the instrument working.

**Validation farmed out** (user opt-in): a Workflow of read-only agents checked the
landed tree against the spec — every claim in this entry and in the FROZEN notes
re-verified against `file::symbol`, stale-reference sweep for `BANNER.md` / `sync` /
`ack` / `check 13` / "the board" across tracked `*.md`, and an adversarial pass on the
retirement. 21 agents, 13 findings confirmed, 2 refuted; what was done: seven "repo
board" pointers my sweep missed re-pointed (`formal/HANDOFF.md` ×4, line-neutral at its
520 cap; `formal/README.md`, `formal/ARCHITECTURE.md`, `docs/architecture/bulk-merge-design.md`,
`README.md`); `main()` now dispatches a retired verb BEFORE `Store.find`, because the
constructor reads `config.json` and the refusal says "Nothing was read"; the spec's
"the ledger names the sha" parenthetical dropped (it cannot); 247 → 246. Deferred to
the tree: `extract_banner` is not code-fence-aware (`TT-8`, LATER). Judgement stayed
here: nothing an agent reported was written into this entry unverified.

**Tree ops:** `close TT-1 -m`, `close TT-2 -m`, `comment DW-1 -m`, all
`--session 2026-09-06d`, messages passed single-quoted (the backtick trap from
`2026-09-06c`).

**Gate:** the commit is made only on a tree where `gate_status.py` says COVERED — all
ten phases, records written first, `lean` last; verdicts in the commit message. Not pushed.
The run finished 2026-09-07 (context was cleared mid-gate; handoff in `.scratch/`). Two
things the gate caught, both worth keeping: editing `formal/verify.sh` for the
`MIN_TESTS_ALL` ratchet STALED all nine already-green tiles, because `verify.sh` is inside
the tiles' `t2c` code scope — the ratchet has to come before the tiles, not after. And
step 4e (`FINAL_REVIEW.md` counts pin) went RED on a doc whose counts block a prior
session believed it had regenerated: the block still read `1089` in all three rows against
a tree of `1091`. Regenerated for real, `lean` re-run green. That pin is not decorative.

Still owed: nothing.

## 2026-09-06c — Phase B′ DECIDED (user); 5/7 prerequisites landed with sabotage evidence; cutover still needs a go

rows: `TT-1` (comment: decided, cutover pending an explicit go), `TT-2` (comment: retires with
`sync`), `TT-3` … `TT-7` (new, closed — tree-only, no board rows), `P6` (untouched, still `NOW`
mechanically)

**Task (user-assigned):** the trial feedback pass. Two decisions taken via one question each:
**C7 → Phase B′ as drafted** (tree authoritative; `HANDOFF.md` becomes a one-hop note; item
blocks move into task bodies behind a bounded `show`; Rhythm → `docs/README.md`; the
closed-ids lines go because `tasks/closed/` + `check_ledger_row_ids` cover them; `sync` /
`ack` / `source_hash` retire at the cutover; `TT-2` resolves as "retired with `sync`"), and
**scope → file every prerequisite as a row and land the cheap ones now**; the cutover commit
itself waits for the explicit go `TT-1`'s trap demands. A mid-pass user request — a session had
complained that a task's top was obsolete because comments append — became prerequisite 1:
`show` renders the Log **newest-first** (Jira-style); the file stays append-only.

**Landed** (status table atop
[`tree-sole-authority-spec-2026-08-29.md`](../tree-sole-authority-spec-2026-08-29.md);
decisions D1–D5 in [`tasktool-trial-protocol.md`](../tasktool-trial-protocol.md) §6):

* `TT-3` `task.py show`: Log newest-first above the body, `SHOW_LOG_HEAD` = 5 with the cut
  announced, `--section`, `--head`, `--json` uncut —
  `test_show_renders_the_log_newest_first_and_never_touches_the_file`.
* `TT-4` `handoff_lint.py::check_priority_capacities` falls back to the tree's open `pri:`
  fields when the board has no row table; None and empty trees are still red —
  `tests/test_handoff_lint_b_prime.py` (new, 30 tests).
* `TT-5` `task.py lint` **check 13**, `check_board_sync`: `sync --check` drift is now a lint
  violation, so a session that updates one arm goes red instead of leaving a hole for the
  next reader. It broke seven tests that asserted "lint clean" on deliberately drifted
  fixtures; they now assert `assert_intact_but_drifted` (every violation is check 13's).
* `TT-6` `task.py ack` fifth case: a `source: hand` task with a board row is ADOPTED
  (`source` → `board`, digest stamped, Log line) — the tool gap `2026-09-06b` hit three
  times. Path sources and row-less hand tasks are still refused.
* `TT-7` `handoff_lint.py::check_session_receipt` (11th check): the newest entry of THIS file
  must carry both trial receipts — the `task lint:` line and the `read:` line — in one of
  the shapes the ledger actually uses (all six lint × four read shapes pinned green).
* Prerequisite 4 decided (`TT-2` retires with `sync`); prerequisite 5 re-checked, no gap.

**Sabotage, first-hand** (observed lines in the test docstrings): check 13's drift branch
deleted → `task lint: clean (13 checks, 7 task file(s) parsed)` on a rewritten item block, red;
`ack` adoption flip → `pass` → `ack accepted T5 but did not adopt it (rc=2): task ack: REFUSED`;
`show` without `reversed()` → keys `['2026-08-21a', …]` oldest-first, red; receipt check made
to scan the whole ledger → `AssertionError: []`; tree fallback `if not tree:` → `if tree is
None:` stayed red for the WRONG reason (`found 0 NOW`), so that test asserts the message text.
`test_the_sabotage_record_is_complete` now requires three `bprime` sabotages.

**Board / tree:** mirror ops `new` ×5 (`TT-3` … `TT-7`, `min_tasks_parsed` 162 → 167 by
`new` itself), `close` ×5 with the test names as evidence, `comment` ×2 (`TT-1`, `TT-2`);
banner + `tasks/BANNER.md` rewritten; the `CLAUDE.md` trial bullet now records the decision.
⚠ One `close -m` message went through a double-quoted Bash string carrying backticks, which
ran as command substitutions and ate two fragments (`...: command not found`); fixed by hand
in `tasks/closed/TT-7-…md`. Quote close messages with single quotes or a heredoc.

`python scripts/task.py lint` → `task lint: clean (13 checks, 167 task file(s) parsed)`
read: board + HANDOFF (the board query first, then `HANDOFF.md` in full, then `show TT-1`)
`sync --check` → CLEAN (2 acked-no-row, 43 hand-filed, 62 closed, 30 unreadable-source — unchanged).

**Gate:** `MIN_TESTS_ALL` re-measured and ratcheted for the new tests; ten phases run after
every edit above; verdicts and `gate_status.py` in the commit message.

**Owed to the user:** the `TT-1` go — the cutover commit (banner consolidation,
`MAX_LINES['HANDOFF.md']` → 60, Rhythm rewrite, retirement of check 13 / `sync` / `ack` /
`source_hash`, `READ_VOCAB` update), one revertable commit.

Still owed: nothing.

## 2026-09-06b — `P17` + `TK55` closed by user decision; red branch inventoried, kept; trial window closed, no cutover

rows: `P17` (closed), `TK55` (closed), `P22` / `P23` / `P24` (new), `TT-1` (tree-only; prework, `moved`
bumped by a `comment`), `P6` (untouched, still `NOW` mechanically)

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session 2026-09-06b`
(§1 `P17` and why not a Lean constructor, §2 `TK55` — the divergence was real, §3 the branch
inventory and the evidence note, §4 `TT-1` prework, §5 the leaked floors, §6 mechanical checks,
§7 next, §8 gate pointer → here).

lint: `task lint: clean (12 checks, 162 task file(s) parsed)`
read: board + HANDOFF (the board query first, then `HANDOFF.md` in full, then `show TT-1`)

**Task (user-assigned):** four owed items from `2026-09-06` — "look into these things, explain
the context, recommend what should be done about each, and what should be done this session",
under an `ultracode` opt-in. Run as two scripted waves (land + adversarial review; fix + branch
note + independent re-check), every test result re-run first-hand afterwards. User decisions,
via one question each: **`P17` → option (c)** now (conformance differential + written scope;
the Lean `bulk = replay` shape filed `SOMEDAY` as `P24`); **`TK55` → fix both parsers AND
accept `keysNonempty` as scope**; **branch → keep as-is, inventory, tag/delete later**;
**`TT-1` → prework + grade only, decide at a feedback pass**.

**Landed.** `formal/conformance/test_conformance_bulk_state.py` (26 tests; bulk-built state
vs the write-by-write Python graph state, exact, over every `GRAPH_FRAGMENT` corpus, plus the
Lean-anchored `diff_states` leg and a coverage pin) with `backends.py::bulk_build_drive` and
`extractor.py::python_bulk_graph_state`; an empty-declared-name refusal in
`zanzibar_utils_v1.py::parse_schema_ast` and, independently, `tests/oracle.py::parse_schema_ast`,
pinned by `tests/test_reg_empty_relation_name.py` (15); the `keysNonempty` docstring in
`FullScope.lean` rewritten to a true justification (`lake build` rc 0); `FINAL_REVIEW.md` §3.1
items 3 and 6 + §4(h), `CORRESPONDENCE.md` §8.1, `ARCHITECTURE.md` and `spec-deviations.md`
(`2026-09-06` entry; its stale "first seven entries" ordering note also fixed);
`formal/history/p3-flip-red-snapshot-2026-09-05.md` (FROZEN; the branch's refuted declarations
verbatim, 55/55 re-verified); a DRAFT Phase B′ amendment atop
`docs/tree-sole-authority-spec-2026-08-29.md`; the trial grade,
[`tasktool-trial-protocol.md`](../tasktool-trial-protocol.md) §6 `2026-09-06` (C1–C7).

**Sabotage, first-hand:** main-parser refusal disabled → `8 failed, 7 passed in 0.24s`;
`bulk_build.py`'s Phase-W multiplicity clamped to 1 → `1 failed, 25 passed in 8.73s`
(`[nary_union] … incremental=3 bulk=1`); both restored byte-exact. **Two GREEN sabotages are
findings:** deleting the I14 crossable-middle loop (`bulk_build.py:206-221`) stays green in every
`build_index` caller → `P22`; collapsing Phase-P path counts is green in the new module because
`extract_sql_state` keeps direct rows only — `tests/test_bulk_build.py` remains the only closure
pin, and the docstring says so.

**Floors:** a `git stash -u` checkout of `HEAD 9f05fbf` collected **520 / 1038** against
`MIN_CONF_ALL=515` / `MIN_TESTS_ALL=1037` — `TK56` added six tests without ratcheting. Both
re-measured after this session's +26 / +15 → **546 / 1053**, provenance written beside them.
⚠ The first ratchet edited `MIN_CONF_ALL` alone; `verify.sh:512`'s identity check
(`MIN_CONF_HEAVY + MIN_CONF_REST == MIN_CONF_ALL`) would have failed every conformance phase —
surfaced by `doc_counts --check` before the gate ran. `MIN_CONF_REST` 411 → 442 (`HEAVY_CONF`
re-measured at 104, unchanged).

**Trial (`TT-1`) prework:** `sync --check` found the tree was the STALE arm — 9 drifts, all
reconciled and acked; three `source: hand` rows with a board row could not be acked without a
hand flip to `source: board` (tool gap, recorded as prerequisite 6 of the draft). Read tally
over the window, re-measured by script: 35 entries, `board + HANDOFF` 27, `board only` 6,
`HANDOFF only` 0, no line 2. User's leaning going into the feedback pass, recorded in C7: keep
the tree, make `HANDOFF.md` ephemeral/one-hop. Not decided.

**Board:** `P17`, `TK55` rows deleted and retired on the closed-ids line (with `TK56`, which
`2026-09-06` closed but never listed); `P22`, `P23` (`LATER` S), `P24` (`SOMEDAY` M) added;
banner rewritten; `tasks/BANNER.md` rewritten (14 lines); mirror ops `close` ×2, `new` ×3,
`ack` ×3 (first reconciliations), `sync CLEAN`. `handoff_lint` refused an 11th trap badge
(de-badged `P24`) and a 523-line `formal/HANDOFF.md` (two redundant blank lines removed).

**Gate:** ten phases run after every edit above; verdicts and `gate_status.py` in the
commit message. If this line still says that, the run had not finished when the entry was
written — check `python scripts/gate_status.py` on the committed tree.

**Owed to the user (not owed to the next session):** the trial feedback pass and the `TT-1` go.
*(Same-session addendum, after commit `ef5eb20`: the user chose DELETE, no tag — `git branch -D
p3-flip-red-2026-09-05` done; `d6d2dfc` unreachable; correction appended atop the snapshot note.)*

Still owed: nothing.

## 2026-09-06 — `TK56`: T3's undischargeable `hValid` (and its `opaque`) deleted; T3 instantiated; next is `P17`

rows: `TK56` (new, closed), `P17` (named as the next step — pointer only, not re-ranked), `P6` (untouched, still `NOW` mechanically)

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-06` (§1 the second opinion, §2 the 49-site deletion and the two witnesses, §3 the
cold build, §4 the three regenerated pins, §5 the `sorry_scan` sabotage evidence, §6 the
`task.py` floor ratchet, §7 next, §8 the gate).

lint: `task lint: clean (12 checks, 159 task file(s) parsed)`
read: board + HANDOFF (the banner and the `P17` row; the prior session's context was carried
in-conversation, so HANDOFF was not re-read in full)

**Task (user-assigned): a second opinion on "the optimal next step toward set-engine =
graph-index equivalence", then "if it's deleting `hValid`, do that, gate, commit, and tell
me what the next thing after is".** The opinion agreed with the prior session's pick, with
one qualification that is the whole point of the entry: deleting `hValid` is HYGIENE, not
reach. `backend_equivalence` (T3) carried `hValid : AllValid T` only to feed T1's unused
`_hValid` binder, and `AllValid` sat on `opaque ValidIdent : String → Prop` — a `Prop` with no
introduction rule, so `AllValid T` was undischargeable at every non-empty store and T3 had
NO instance anywhere in the tree while T2b (`graph_correct_public`) had two. Six weeks of a
headline that could not be applied.

**Landed:** `AllValid` and `opaque ValidIdent` deleted; `setEngine_correct` (T1) is now
`(S) (T) (q) : SetEngineModel.check S T q = sem S T q` with no hypotheses; 18 `Equiv.lean`
rungs and `FullScope.lean`'s T3/T6a lose the binder (49 sites / 5 files); T3 takes exactly
T2b's `hA hF h hq hqs hqo`. Two instantiations added, audited and pinned:
`FullScope.lean::W4WitnessDirect.equivalence_applies` and
`Exec.lean::graphRunOps_directArm_backend_equivalence` — the latter a closed form (∃σ at an
EXECUTED store, `ReachedBy`, `Drained`, both backends `= true`, proved equal). Cold build
`LAKE_RC=0` first try (one self-inflicted restart: a docstring edit to the root import
mid-build). Pins regenerated with the reasons in PROOF_STATUS §4: statements 49 → **51**,
definitions 250 → **251** (`AllValid` gone, `sdDirectArmOps`/`sdDirectArmQuery` in), audits
584 → **587** — the regeneration also caught `graphModeAnswers_eq_sem`, audited but never
pinned; the superset rule hides exactly that.

**Two mechanical refusals landed beside it, each with a control:**
* The tree now carries ZERO `opaque`s, so `formal/conformance/sorry_scan.py` refuses one at
  declaration position (`AXIOM_DECL_RE` = `axiom|opaque`). Control: `HEAD`'s `Ident.lean`
  scanned alone → 1 finding, rc 1; live 0 over 70 files. `test_sorry_scan.py` 39 → 44.
* `scripts/task.py new` ratchets `min_tasks_parsed` itself (`task.py::ratchet_min_parsed`,
  `max(floor, disk)`, never lowers) — the manual step `tasks/config.json`'s provenance recorded
  as forgotten in THREE consecutive sessions. First live use: filing `TK56` printed
  `floor min_tasks_parsed 158 -> 159`. `tests/test_tasktool.py` 85 → 86; the new test is RED
  against `HEAD`'s `task.py`. Spec row updated (`docs/tasktool-spec.md` `new`).

**Next (the answer to "what after"): `P17`.** `ReachedBy := ReachedByW3d2E` has
`emptyState` as its only base constructor (`CascadeStrataAssemble.lean:430`), so every
headline is a statement about indexes grown from empty by logged writes — and
`build_index(bulk=True)` is the DEFAULT constructor (`connectedstore/build.py:82-87`,
`bulk_build.py`/`bulk_backfill.py`). Model it as a second base constructor, or scope-exclude
it in writing in `FINAL_REVIEW.md`. Not re-ranked here (user-assigned task).

Docs touched: `formal/SEMANTICS.md` (§2.1, T1/T3 rows, the `hValid` bullet),
`formal/FINAL_REVIEW.md` (T1/T3 clauses + counts block), `formal/ARCHITECTURE.md`,
`formal/HANDOFF.md`, `docs/tasktool-spec.md`, `tasks/BANNER.md`, this board's banner.

Still owed: the three user calls carried from `2026-09-05b` — `TK55` (`keysNonempty` scope vs
discharge), branch `p3-flip-red-2026-09-05` (keep vs delete), and the `tasks/` trial decision
`TT-1` (window closes today; cutover-or-keep-both). `TK53`: 15 appends. `P6` at `NOW` was not
re-examined.

## 2026-09-05b — `P3` LANDED: the write-leg-only flip was kernel-refuted, so (α)+R5 co-landed; sorry-free, P6 retired

rows: `P3` (closed), `P6` (→ `NOW`), `P4`, `P5`, `P14`, `TK54` + `TK55` (new)

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-05b` (§1–§8 the refutation, §9 the landing, §10 the multiplicity fix); new traps
(bb)–(hh) in [the scope doc](../../formal/history/leaf-family-split-scope-2026-08-05.md)
§11.13.

lint: `task lint: clean (12 checks, 158 task file(s) parsed)`
read: board + HANDOFF (the `P3` block and the banner only — HANDOFF was not read in full)

**The re-point as adjudicated was FALSE, and the kernel said so.** Re-pointing ONLY
`GraphState.writeLoggedRules` onto `rewriteClosureL S (rawWriteTuples S t)` builds green
with four `sorry`s — and one of them is unfixable because the theorem is false: a
sorryAx-FREE `decide` refutes `graph_correct` on that tree (§2). Mechanism: the write lands
on the leaf node, the remove leg and the dirty-key branch still look at the public node, so
a write-then-remove leaves a ghost grant and the cascade never re-reconciles the public
key. Python has neither defect (§3). So branch (α) (`affectedKeys` dirties the public key
via `publicOfLeaf`) and R5 (leaf-routed `removeLoggedRules`) are CO-REQUISITES, not
follow-ups. **User decision: widen `P3` and land all three now.** The RED tree is kept as
evidence on branch `p3-flip-red-2026-09-05` (`d6d2dfc`, "do not merge").

**Landed (§9), one commit:** both logged legs fold the same leaf-routed list
(`Cascade.lean:190-191`, `:340-341`), the own-key branch reads back through `publicOfLeaf`
(`:542-546`), `untOccCount` restated over L. All four `sorry`s discharged — three with
byte-identical statements once both legs name the same list; the fourth needed a ROUTING
OBLIGATION (`CascadeStrataSettle.lean::rawWriteRels_ne_nil_of_exprDirectsAll`, bridging
`Leaf.lean`'s allocation walk to `exprDirectsAll`'s admission walk), and its new premise
`hroute` is discharged at its sole consumer, so no headline gained a binder (49/49). 53
refutation/bridge/`#check` declarations deleted, each after its `decide` went red first;
their content survives as kernel necessity controls (`::tvDer_own_key_not_dirty` etc.). The
verifier's decisive check: `hroute` HOLDS at the deleted refutation's own witness
(`rawWriteRels Sw tw = ["approver.0"]`) — the refutation died to (α), not to a guard (trap
(gg)). `GraphAdmission` gained `noLeafSubjects` (sanctioned) and `keysNonempty` (accepted as
scope: Python-enforced, not `WF`-derivable — **flagged to the user, not signed off**).
Pins: statements 49/49 unchanged; definitions regenerated **232 → 250** after a control run
showed exactly the predicted 35-row diff and nothing else (§9.3). Projection **P6 is
deleted** from the extractor; ledger `P6 = 0`, `compared 189 → 265`, conformance count 515
unchanged, and a positive pin (`test_conformance_state.py::test_leaf_rows_reach_the_compare_arm`,
floor 76) replaces the ledger key that would otherwise silently stop moving.

**The flip doubled an ALREADY-exponential derived-arm stacking, and ten conformance tests
timed out (§10, trap (hh)).** `two_stratum_cascade` alice→approver at n=1..5 was 2/13/46/204/
1013 on the control tree (16.4 s at n=5) and 4/26/92/408/2026 after the flip (176.8 s
against `runner.py`'s 120 s zcli timeout); `cross_stratum_resettle` went 12/160/900/timeout.
Root cause is two model lists that the Python keys as a `dict`/`set` and the model
`flatMap`'d: the dirty-key list `CascadeStrata.lean::cascadeKeysAbove`
(`processor.py::_map_deltas_to_keys`) and the enum candidates `CascadeStrataEnum.lean::
enumJob2(D).cands` (`processor.py::_reconcile` `candidates: dict`). Both got core
`List.eraseDups` (first occurrence — Mathlib `.dedup` keeps the last), `mem_cascadeKeys_iff_above`
replaced the zero-consumer `cascadeKeys_eq_above`, the consumer sites in
Resettle/Assemble/Settle/Inv/Enum were re-closed (§10.3), and the multiplicities are now
`1…5` (0.1 s), re-measured first-hand. Consequences, each with a control run first: golden
`derived_arm_multiplicity.json` regenerated (all 19 rows down; `direct_arm_exclusion` `[16, 1]`
→ `[4, 1]`), `_MIN_LEDGER_STACKED` **19 → 18** (`_MIN_LEDGER_ROWS` stays 19; literal
anti-vacuity output in the docstring), definition pin regenerated **250/250** after the
control showed exactly `def:Zanzibar.cascadeKeysAbove` + `def:Zanzibar.enumJob2D` and
nothing else. `CORRESPONDENCE.md` §7.2 item 6 (the residual `+1` per reconcile) is STILL
OPEN — no longer exponential, still not the Python's `1`. Two observations recorded, not
acted on: `Exec.lean:82` now gates on `foldAdmitsB` over the leaf-routed list (a stricter
refusal surface than Python's admission), and `State.lean:160-161`'s reach fuel is
`σ.nodes.length + 1`.

**The gate's `sorry` belt had been counting 0 on every build since `ZT-P2-4`** (§5, trap
(dd)): the grep pattern was wrong for Lean's backtick-quoted warning, so the 4-`sorry` RED
tree passed it. Fixed in `verify.sh` (`:644-650`, `:669`, `:673`); control 0 → 4 on the
RED log, live 0 on the landed tree.

**T2a did NOT widen, and its justification is retired.** `graph_reached_inv` still takes
`W4NarrowT2a`; `outside_narrow_t2a` still holds. The "P6 modelling limit" story is gone —
the model now routes exactly as Python does — so the carry is proof work owed, not a design
decision. The D.3 probe re-run on the landed model
(`formal/probes/d3_negedgefree_postflip_2026-09-05.lean`, rc 0, re-run first-hand with
identical output) reports `negFree := true` on the model's own write leg
(`{edges 5, rows 1, negTested 2, negFree true}`, `rawWriteRels S tW = ["approver.0"]`) while
the bridge-sabotage control reproduces D.3's kill (`negFree false`) — so `Inv.negEdgeFree`
(`GraphIndex/State.lean:706`) is plausibly provable on the `_d` fragment and is the only
clause implicated. ⚠ D.3's own witness (`Sd`/`Td`) is vacuous under routing; probe with
`LeafWitness.Sw`/`tw`. `P5` is that item.

**Board and tree bookkeeping:** `P3` closed. `P6` → `NOW` mechanically (the top `NEXT` row;
its "not parallel-safe with `P3`" blocker is gone) — **the user may re-rank**. `P4` deps
swept. `TK54` (`Scratch4cii.lean` is a tracked module inside the gated proof tree) and
`TK55` (`keysNonempty`: scope or discharge — user call) filed, both `LATER`/S. Mirrored in
`tasks/` under `--session 2026-09-05b` (`close P3`, `dep rm P4 P3`, `promote P6 NOW`,
comments on `P4`/`P5`/`P6`/`P14`, `new` ×2). ⚠ `tasks/config.json::min_tasks_parsed` was
ratcheted **156 → 158** for the two new files — the THIRD consecutive session in which
`task.py new` was run without the ratchet, found only by running `task.py counts` by hand
after `conf-tile:1/5` had already passed on the un-ratcheted tree (config.json is in the
tiles' code scope, so that tile was re-run); the mechanical fix (`new` raising the floor
itself) is still not done. `tests/test_tasktool.py::test_sabotage_live_blind_parser` was
relaxed from "exactly 2 FAILs" to "floor ×1 + recount ×1 + only `resolves to no task`
extras" because closing `P3` made `TK6`'s `related: [P3]` dangle under the blinded parser
(literal in the docstring). `CORRESPONDENCE.md` anchors **543 → 583** over the session (new §5 rows and §7.2
items 5c/6 for the flip and the dedups; `anchor_check.py` 583/583) and
`FINAL_REVIEW.md`'s counts block regenerated (515 / 1036 / 585 / 583; definition pin
232 → 250, `compared against Lean` 189 → 265). `formal/HANDOFF.md`
was over its 520-line ceiling after the sweep and was condensed back to pointers (narrative
lives in PROOF_STATUS); it is 519 lines.

**Gate, as observed on this tree:** all TEN phases PASSED — the nine pytest tiles
(`conf-tile:1/5`…`5/5` at `collected=515 selected=103 conf_passed=103`,
`tests-tile:1/4`…`4/4` at `collected=1036 selected=259 tests_passed=259`, zero `xfailed`,
zero `skipped`, every floor met, all on `t2c:ce27f3337040` with the tile rows read from
`.gate-runs/ledger.tsv` and each tile's own log — NOT from the wrapper's stdout, which an
orphaned earlier runner had polluted), then `lean` LAST after this entry was spliced
(`holes=0 audits=585 pinned=584 defs=250`, statements 49/49, anchors 583/583,
`doc_counts --check` green); `python scripts/gate_status.py` →
`VERDICT: the ten-phase gate is COVERED on this tree`. No Python algorithm changed
(`index_v4/` / `setengine/` untouched), so no fuzz sweep is owed. The earlier tile
runs at 20:20–21:37 were on intermediate trees (the timeouts, the un-ratcheted
`config.json`, and one runner that survived a `TaskStop` and kept appending stale
rows) and are superseded, not evidence. That was commit `2ccd321`.

🛑 **Two instrument incidents AFTER that commit, both fixed, one more commit.**
(1) One second after `2ccd321`, `gate_status.py` said NOT covered on a byte-identical
tree: `t2c:ce27f3337040` → `t2c:82a9ff014f3f`, `t2a:3c6cd121680f` → `t2a:44ac835f64e1`.
`GS-1` in a new costume — a PENDING deletion (the `tasks/P3-*.md` → `tasks/closed/`
rename) hashed as `path + "absent"`, a committed one as nothing. Fixed by skipping such
entries (`scripts/gate_status.py::_file_fingerprint` returns `None`); the new test
`tests/test_gate_status.py::test_tree_id_survives_a_commit_of_a_deletion_or_rename` was
run RED against the old code first (`assert 't2a:f75e122a9466' == 't2a:cef5c8a446fd'`,
`1 failed, 24 deselected`) and the existing deletion test is the control (it needed a
second committed file, since an id over zero files is refused — correct, but it made
the control pass for the wrong reason). `MIN_TESTS_ALL` **1036 → 1037**, re-measured
with `--collect-only`; `FINAL_REVIEW.md` counts regenerated again; runbook §4 has the
write-up. (2) Removing the control worktree `Temp/zz-control` gutted the main tree's
`formal/lean/.lake/packages/mathlib/` — its `.lake/packages` was an NTFS junction into
the main tree and `git worktree remove --force` recursed through it (`.git`, the
oleans, `lakefile`, manifest, toolchain, `Mathlib/Algebra`…`Mathlib/Lean*` gone before
the 2-minute timeout killed it); `lean` then failed at `lake build` ("`URL has changed`",
"`unable to read tree fabf563…`"). Nothing tracked was touched; recovered with
`rm -rf` + `lake exe cache get` (8498 files decompressed from `~/.cache/mathlib`, no
downloads) + `lake build` (1089 jobs, 0 sorry) in ~5 min. Runbook "Gotchas" carries the
rule: share packages by COPY, never by junction. The second commit's gate: all ten
phases re-run on the fixed tree — the nine tiles at `collected=1037`, `lean` last —
and `gate_status.py` COVERED, this time surviving the commit.

Still owed: a user call on `p3-flip-red-2026-09-05` (keep as evidence vs delete — it is the
only non-`.scratch` copy of the six refutation rounds); a user call on `keysNonempty`
(scope vs discharge, `TK55`); no `lake clean` full rebuild has ever been run on this tree
(§9.5); `task.py new` still does not ratchet `min_tasks_parsed` itself.

---

## 2026-09-05 — the write-path cone HAS a green additive prefix: (A)/(B)/(C) landed, (H) was never open

rows: `P3`

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-05`.

lint: `task lint: clean (12 checks, 156 task file(s) parsed)`
read: board + HANDOFF

**No re-point was made.** `Cascade.lean:175` still folds `rewriteClosure`; the tree is
unflipped, zero `sorry`, and every pin is byte-identical to the `7200484` anchor
(statements 49/49, definitions **232/232**, `audits=585 pinned=584`).

**The session's claim.** `2026-09-03c` §5 said landing the write path "is not
green-stoppable … 8 undischarged obligations". True of the RE-POINT, false of the
OBLIGATIONS: five of the eight are L-analogues of existing plain-closure lemmas, and an
L-analogue is provable against `rewriteClosureL` TODAY because that definition already
exists and is already what `LeafRules.lean::writeRulesRaw` folds. §11.13 **(w)** recurring
a third time, licensed by §11.12 **rule 6** — a green additive prefix contains no re-point
and no pin asserting anything untrue, and both halves were checked rather than assumed.

**(H) was never open.** `writeRulesRaw_schema` exists at `LeafRules.lean:292` and predates
the probe that declared it missing — so the record was wrong when written, not stale. Found
by grepping all eight cited symbols before reading anything else. **CLAUDE.md's "cite a
symbol that EXISTS" applies to claims of NON-existence too**, and nothing in the gate can
catch that direction. 8 substantive obligations is 7.

**Landed:** 21 declarations in `LeafRules.lean` — (B) `rewriteClosureL_object`, (C)
`::rewriteClosureL_produced`, (A) `::rewriteClosureL_subject_pred_ne` plus the `Q`-generic
chain (`TtuTargetsSatL`) it instantiates, with non-vacuity pins and two sabotages. Zero
existing declarations touched, no new import, green at every stage (1089 jobs), four build
cycles of a declared ten. Why it was cheap: `rewriteClosureAuxL` is `rewriteClosureAux` with
`rewriteStepL` swapped in, `rewriteStepL` is `rewriteStep` with `schemaRewritesL` swapped in,
`applyRRule` is shared, and the plain aux lemmas are already seed-LIST-generic. **The
obligations were sized as cone repairs because the probe met them as cone repairs; met
head-on as lemmas about an existing definition they are transcriptions.**

**★ (A)'s premise looks DISCHARGEABLE, which changes its sizing.** `Leaf.lean::isPure`'s TTU
arm requires `!derivedAnywhere S tgt` and `::atomLeaves` emits a `.closure` TTU leaf only
under `isPure`, so every leaf-rule TTU target is derived-nowhere; while
`FullScope.lean:238 W4Fragment.term` supplies `NoTtuTarget S R` only for a DERIVED `R` (as do
all fifteen `Equiv.lean` consumers). A name cannot be both. ⚠ **Source reading, not a kernel
check** — the missing lemma is "every `.closure` leaf of `persistedLeaves` is `isPure`", a
mutual induction for which no purity lemma exists today. Next session's first move; additive.

**Sabotages, both restored from a byte-exact `cp` backup (trap (aa)).** SAB-A narrowed
`TtuTargetsSatL` to `schemaRewrites` → `rc=1`, six errors, and the two that matter are
WITNESSES not plumbing (`stP_full_layer_does_target_viewer` at `:1348` fires because the
narrowed premise becomes vacuously true). SAB-B narrowed `rewriteStepL_outRel`'s existential
→ `rc=1`, two attributable errors. Both counts are lower bounds (traps (k)/(v)).

**Method note worth carrying:** a 23-agent read-only recon ran in parallel with the work and
independently converged on the same `TtuTargetsSatL` design — but its most useful output was
the `isPure` discharge route above, which I then verified first-hand before believing. It
also refuted my own pin's reach (the `SlStP` witness shows the gap at a NON-derived `R`, not
at the derived `R` consumers actually supply). Delegation as evidence, reconciled not
averaged — CLAUDE.md's rule landing the right way round this time.

Still owed: nothing.

## 2026-09-03c — trap (z) fixed, 66 decls wide not 2; SAB-5 closed end-to-end; write-path cone is 11-file scale

rows: `P3`

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-03c`.

lint: `task lint: clean (12 checks, 156 task file(s) parsed)`
read: board + HANDOFF

**Order taken was the user's, and the reason they gave for it held.** Trap (z) first, so
the write-path re-point would land against a gate that can observe it; then the re-point,
with the stale-doc retirement folded in; SAB-5's last piece at the tail.

**(z) was two defects, not one, and the unrecorded one was worse.** Beyond the receiver
dot-calls the trap named, `statement_pin.py::_resolve` never tried the ENCLOSING namespace
— so a bare name written inside `namespace Zanzibar.W4Witness` resolved to nothing, and
**the non-vacuity witnesses' own schemas and stores had no `def:` row at all**. Closure 158
→ 224; golden 165 → 232 rows, `+67 / -0`, statements byte-identical.

⚠ **The control is the finding, and it generalises.** The sabotage (delete `Sd`'s exclusion
arm, so the boolean witness stops witnessing a boolean schema) reds the fixed pin with one
attributable row — but the OLD pin is `165/165` GREEN on that same tree. An instrument that
reports a clean count while the thing it certifies has been hollowed out is this repo's
house failure mode aimed at the assurance layer itself, one level below where §11.13 was
looking.

⚠ **A trap's suggested remedy is not a sized plan.** (z) offered "hand-pin the two names".
That closes **2 of 66**. The entry was written by the session that found the symptom, which
is exactly when the blast radius is least known — so re-measure before taking one.

**The write-path re-point: the recorded first wave was accurate AND the cone is large.**
Both halves matter. `Cascade.lean:175` + one import gives exactly the 4 recorded errors, in
one file — but fixing them forces `writeLoggedRules_evalEq`'s twin to become
`writeRulesRaw`, and that statement change opens a 17-wave, 6-file descent that stopped
before reaching `Equiv`/`FullScope`/`Audit`. 8 substantive obligations, one needing a new
premise (`NoTtuTarget` does not transfer to `schemaRewritesL`, because `leafRewrites`
covers derived keys the taint filter skips), one changing a pinned inductive. Reverted; not
landed; the tree is unflipped with zero `sorry`. **What landed is the instrument.**

**Doc rot retired:** `docs/latent-gaps.md`'s `hql` section — the one that produced
`2026-09-03`'s false escalation a day after `2026-09-02d` closed it — is deleted per that
file's own replace semantics, with a bullet in its `Closed` list.

⚠ **Trap (aa) recurred, with a mundane new cause: an ordinary edit made WHILE the tiles
were running.** Removing one stray space from a *docstring* in `statement_pin.py` moved
`t2c` and stranded all five freshly-green conformance tiles plus the four `tests-` tiles in
flight. No `git checkout`, no CRLF — a one-character edit to a file in the code scope. The
rule is a sequencing one: **freeze the code tree, then run the tiles, never interleave.**
`*.md` edits are free, which is what makes the code-file exception easy to forget after an
hour of safe doc editing. `gate_status.py` caught it; cost was a re-run.

🛑 **A FAIL-OPEN IN THE GATE'S OWN CACHING, found by walking into it and FIXED.** `t2c`
(the pytest tiles' tree id) excludes `*.md`. That exclusion was justified in 2026-08-17 by
a survey concluding "NO collected test reads markdown" — true then, and **false since
2026-08-29d**, when `tests/test_tasktool.py` entered the gate: its `live_copy` helper
copies the LIVE `tasks/` corpus (entirely markdown) and lints it, and four collected tests
use it. So a `tasks/*.md` edit could turn the suite RED while `gate_status.py` went on
reporting COVERED from cached rows. Demonstrated rather than argued: this session's
`tasks/BANNER.md` rewrite broke its 14-line cap, `t2c` did not move, and all four `tests-`
tiles failed on `::test_sabotage_live_blind_parser`. Fixed by keeping `tasks/` in the code
scope (`scripts/gate_status.py::CODE_SCOPE_MD_KEEP`), with a three-way sabotage: it MOVES
on a `tasks/*.md` edit, REVERTS byte-exactly, and still IGNORES `docs/*.md` (so the
2026-08-17 docs-edit optimisation this id exists for is intact).

⚠ **The lesson is about the VERIFICATION, not the list.** A scope exclusion rests on a
survey of what exists *today*, and nothing re-runs that survey when a new test module
lands. Re-do it whenever one enters the gate — `verify.sh` cannot warn you, because the
excluded file is invisible to it too. Two of this session's three assurance findings
((z) and this) have the same shape: **a check whose justification was measured once and
then quietly outlived by the tree.**

⚠ **And a self-inflicted loss worth recording, because the trap that forbids it is on this
very item's list.** Reverting a one-newline probe with `git checkout -- docs/latent-gaps.md`
silently discarded that file's ENTIRE session rewrite — one of the four deliverables.
`git status` showed the file clean afterwards, so nothing flagged it; it was caught only by
grepping for content that should have been there, and redone. Scope doc §11.13 (aa) already
says *prefer a byte-exact `cp` backup over `git checkout --`*, and it was not followed
because the probe felt too small to warrant one. **`git checkout -- <path>` does not know
which of your changes were the probe.**

**All four of `2026-09-03b`'s owed items are discharged**: the cone measurement, the
`latent-gaps.md` retirement, SAB-5's build-surviving mutation, and trap (z)'s fix. The
proof repair itself is not landed — see below.

**Still owed:**
* **The write-path re-point's actual proof repair.** Now a sized job rather than an open
  question: 8 substantive obligations and 27 mechanical line edits, each with its symbol, in
  PROOF_STATUS `2026-09-03c` §4. Start with **(A)** — it needs a new premise and everything
  else is downstream of knowing its shape — and note **(E)** changes a pinned inductive.
* **Finish the cone measurement past `CascadeStrataSettle`.** The probe stopped at wave 17
  with `CascadeEnum`, `CascadeStrataEnum`, `CascadeStrataResettle`, `Equiv`, `FullScope`,
  `Audit` never reached, so every figure recorded is a LOWER bound. `Equiv` hosts six
  audited milestone declarations, so it is the one that decides whether the headline layer
  moves.
* **Re-run the 2026-08-17 `t2c` exclusion survey** if any further test module joins the
  gate. The fix keeps `tasks/` in scope, but the *class* of defect is unfixed: nothing
  mechanically re-checks which collected tests read `*.md`.
* **Nothing else.** The write-back ran in full: ledger, both banners, board row + item
  block, `task.py touch`/`comment`, the stale `gate-runbook.md` §4c count fixed in place,
  and the `t2c` scope fix documented in `gate-runbook.md` §"Per-phase scopes".

## 2026-09-03b — the `hql` blocker was already discharged, and the write-path re-point is one line plus an import

rows: `P3`

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-03b`.

lint: `task lint: clean (12 checks, 156 task file(s) parsed)`
read: board + HANDOFF

**This entry refutes the first `Still owed:` bullet of `2026-09-03`, immediately below.**
That entry — and the banner and board edits it made — said `P3` was blocked on a human call
about adding the `hql` guard to `graph_correct`. It is not. `headline_statements.txt:27`
already carries `(hql : publicOfLeaf S q.object.type q.relation = none)`; **4c-ii added it
on 2026-09-02d**, as that session's own banner records ("statements 49/49, `graph_correct`
gains `hql`"). The other two unfenced rows, `:66`/`:67`, pin `q.relation = "approver"` and
DERIVE the guard in their proofs (`FullScope.lean:1345-1347`, via `fence_not_identity` and
`checkPublic_of_not_leaf`) — structurally, since `publicOfLeaf` requires a dotted name and
`"approver"` has none. `:52 unfenced_grants` is a concrete `= true` witness and is meant to
stay unguarded. So `docs/latent-gaps.md:132-137` is stale: it describes the pre-4c-ii world.

⚠ **The mechanism is the lesson.** A subagent synthesizer asserted "I confirmed
`headline_statements.txt:27` carries no `hql` binder today"; it was taken at face value and
escalated to the user as a decision. `sed -n '27p'` refutes it in two seconds. This is
`CLAUDE.md`'s "delegation does not transfer judgement" hitting the exact case it names — a
claim headed for a user-facing decision, unverified first-hand. No rule needs changing.

**The re-point, measured on a scratch branch and reverted:** changing `Cascade.lean:175` to
fold `rewriteClosureL S (rawWriteTuples S t)` and adding
`import ZanzibarProofs.GraphIndex.LeafRules` builds to **4 errors, all in `Cascade.lean`
(:237, :240, :248, :250)** — one lemma family (`EvalEq` transfer + a watermark `rfl`/`simp`
pair). `writeLoggedOne` needs no edit at all: `Leaf.lean:762 rawWriteTuples` re-addresses
the tuple's relation to the leaf name, so the leaf node is already what gets materialized.
Both the session's starting plan and `LeafRules.lean:242-245`'s own banner over-specify this
step. ⚠ **4 is a FIRST WAVE, not a cone size** — nothing downstream of `Cascade` type-checked,
because it cannot until `Cascade` does. Quoting it as the cost would be the house sizing error.

**Still owed:**
* **The re-point's actual proof repair**, and a real measurement of the cone past
  `Cascade.lean`. No human call blocks it.
* **`docs/latent-gaps.md:132-137` is stale and still says otherwise** — it should be retired
  or re-scoped, and it is the document a future session would trust.
* Everything under `2026-09-03`'s `Still owed:` except its first bullet: SAB-5's
  build-surviving mutation (the ranked candidate is still unverified) and trap (z)'s fix.

## 2026-09-03 — SAB-5 was mis-instrumented, not unobservable; and the `P6` remainder is NOT a Python-side commit

rows: `P3`

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-03`. New trap: scope doc §11.13 **(z)**.

lint: `task lint: clean (12 checks, 156 task file(s) parsed)`
read: board + HANDOFF

**Two results, and each refutes something this repo's own records assert.**

**1. SAB-5 is discharged.** `2026-09-02d` filed it as unobservable: deleting
`GraphAdmission.computedRefsNotLeaf` breaks the build, so `verify.sh lean` never reaches
step 4c. But that is a property of the *harness*, not the instrument —
`statement_pin.py` is pure source-text extraction and never builds Lean. Run directly, it
reddens in 8.5 s with `REMOVED field(s)/constructor(s): computedRefsNotLeaf` and
`ComputedRefsNotLeaf` no longer reachable, **while the STATEMENT pin stays 49/49 green**.
That green is what makes it evidence rather than bookkeeping: it is a direct observation of
the hollowed-from-underneath attack 4b is blind to and 4c was built for, which
`statement_pin.py`'s docstring has claimed since 2026-07-27 with nothing checking it.
Reverted → rc=0, 165/165, tree clean; `--numstat` `0 1` identical with and without
`--ignore-cr-at-eol` (trap (y) control). **Still genuinely unobserved:** 4c firing
end-to-end through `verify.sh`, which needs a mutation the BUILD SURVIVES — filed below,
narrowly, instead of being papered over with substitutes.

**2. The `P6` projection cannot be retired, and the board said it could.** The `P3` item
block and board row both stated the remainder was "one thing", a Python-side number, on the
grounds that "4c-ii is what makes it retirable". Verified first-hand:
`LeafRules.lean:246 writeRulesRaw` still carries `⚠ No caller yet` and `:44` still reads
"Nothing here is wired into a caller"; `Cascade.lean:175 writeLoggedRules` still folds
`rewriteClosure`, not `rewriteClosureL`; `Cascade.lean:167 writeLoggedOne` still
materializes `objNode t.object t.relation`. **4c-ii re-pointed the proof-side
`UntaintedShadow`, not the executable driver.** The block also named the wrong projection —
it said P6 drops `w_any` rows, which is P2 (drops 0 of 498); P6 is the dotted leaf-family
branch at `extractor.py:236-237`.

The instrument control settles it. Deleting the branch hits the completion criterion
exactly — `{'P6': 0, 'compared': 265}` — and the state gate goes red:
`19 failed, 37 passed`, 99 × `edge only in PYTHON` at `viewer.0`/`viewer.1` targets. So the
criterion is reachable by a two-line deletion that proves nothing, exactly as
`2026-08-16c` §3 warned. The 19 decompose as 17 × `test_state_leangraph_vs_pythongraph` +
`test_residue_rich_corpus_is_really_rich` (it calls `diff_states` directly at :636 on a
tainted corpus) + `test_projection_ledger_is_not_vacuous`, reproducing `2026-08-16c` and
**refuting the recorded "18 failed / 38 passed" correction**, which missed `:593`.

**New trap §11.13 (z), found while sizing the re-point and live right now.** The definition
pin has **no row for `writeLoggedRules` or `writeLoggedOne`** — they appear only as the call
text `σ.writeLoggedRules S t` inside `graphRunAux`/`graphRunOpsAux`/the three `ReachedByW3d2*`
inductives, because the closure walk resolves bare names, not dot-notation. So the planned
re-point of `Cascade.lean:175`'s body leaves step 4c green while changing what the model
executes. The control for that work is the state gate, not the pin trio.

**Not taken unilaterally:** the re-point makes `graph_correct` **false as written** at minted
leaf-name queries unless it gains the `hql` guard (`docs/latent-gaps.md:132-137`,
machine-checked) — a change to a pinned headline statement. The `P3` item block has flagged
this as needing a human call since it was opened; it is now surfaced in the banner and the
board row rather than buried in the item.

Board: `P3` stays `NOW`, re-sized **M → L**, with the refuted sizing recorded in place.

**A third finding, and it cost this session a full tile re-run — new trap §11.13 (aa).**
Reverting the two probes with `git checkout --` **moved the content-addressed tree id**:
session start was `t2c:c18b40544b46`; afterwards a *fully clean tree at the same HEAD*
computed `t2c:f3d8f4a98aef`, dropping all nine cached tile verdicts to `this tree: NO`.
`git ls-files --eol` explains it — `i/lf w/crlf` on both files, so `checkout` writes CRLF
while the index holds LF. Git normalizes on read and reports clean; `gate_status.py`
hashes raw bytes and sees a different tree. This is (y)'s mechanism and is how this tree
came to mix line endings per file. The gate caught it, which is the safe direction; the
mirror — cached green rows surviving a rewrite back to LF — is the one to watch. Standing
check: after reverting a probe, ask `gate_status.py`, never `git status`.

**Still owed:**
* **The write-path re-point itself** (`Cascade.lean:167`/`:175`/`:301`,
  `RulesWrite.lean:135`, `publicOfLeaf` into `Cascade.lean:478 affectedKeys`) — blocked on
  the `hql` human call above, not on analysis.
* **SAB-5's end-to-end half:** find a mutation to a pinned definition that the Lean build
  SURVIVES, so step 4c can be watched firing through `verify.sh` rather than through the
  script alone. Candidate ranked this session but NOT run: swap the declaration order of
  `ttuNotLeaf` (`FullScope.lean:157`) and `directRestrNotLeaf` (`:158`) in `GraphAdmission`
  — all uses are by name, so the build should survive while the pinned `fields=(…)` list and
  body text both move. **Unverified — it is a prediction, not a result.**
* **Trap (z)'s fix is unwritten.** Recorded as a trap only; nobody has decided whether to
  teach the closure walk dot-notation receivers or to pin the two names by hand.

## 2026-09-02d — 4c-ii IS LANDED: the shadow is re-pointed, both premises threaded and discharged, one pin row moved

rows: `P3`

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-02d`.

lint: `task lint: clean (12 checks, 156 task file(s) parsed)`
read: board + HANDOFF

**The item the board has carried as `NOW` since 2026-08-21b is done.**
`CascadeStable.lean::UntaintedShadow` now abbreviates
`ShadowOver (fun k => DerNode S k ∨ LeafNode S k)`; `shadow_graphRec_agree` carries an
`hnl` premise; all 14 call sites supply it; `graph_correct` carries the query guard. Full
tree green at every stage (1089 jobs, rc=0, zero `sorry`).

* **The previous session's sizing was RIGHT, and is now kernel-confirmed rather than
  computed.** The `hcr` thread is exactly **62 declarations across eleven files**, with
  the per-file split it predicted (`CascadeStrataSettle` 14, `CascadeStrataResettle` 11,
  `CascadeStrataEnum` 8, `CascadeEnum` 6, `Equiv` 6, `CascadeSettle` 5, `CascadeStrataAssemble`
  4, `CascadeStable` 3, `CascadeStrataEdge` 3, `CascadeInv` 2, `FullScope` 0); `hql` is 13.
* **And the 14-SITE census was right all along — (q)/(v)/(t) were one cone under three
  COUNTING UNITS**, not three measurements of it: 14 argument-supply sites, 12 host
  declarations, 62 signature changes, all true simultaneously. The sites split **11
  membership-served + 3 query-served**, and `graph_correct_w3d2`/`_d` each host one of
  each — which is precisely why the two halves could not be landed separately.
* **Pin cost is one row, and the pin was run BEFORE regenerating as its own control.**
  `verify.sh lean` failed with exactly one discrepancy — `graph_correct` gaining `hql` —
  and step 4c (definitions) did not fire. After deliberate regeneration:
  statements **49/49, one row changed**; definitions **165, byte-identical**;
  `audited_theorems.txt` untouched.
* ⚠ **The flip itself is invisible to every pin.** Both headline files contain zero
  occurrences of `UntaintedShadow`/`ShadowOver`/`LeafNode`/`DerNode`, and the definition
  closure stops before that line. Re-pointing it changed what the development MEANS with
  every pin green — the `ZT-P2-5` class landing just outside the definition pin's reach.
  Its only control is the flip probe, which is why SAB-1 is not optional.
* **Three sabotages, each with a control that had to stay green** (literal output in
  PROOF_STATUS and in the touched docstrings): SAB-1 reverting the flip reds the `hsubjW`
  sites while the three self-adapting `first | … | …` sites stay GREEN; SAB-2 narrowing
  `hnl` to the already-derivable `¬ DerNode` reds at `:1653`, the predicted line; SAB-4
  mis-typing the query guard inside `graph_correct_w3d2_d` alone gives **exactly one
  error, at that declaration's query site, with its membership site green** — which is
  what makes the 11+3 split a fact rather than bookkeeping.
* **New method trap, and the build could not have caught it:** a `perl -i` pass that emits
  a wide character re-encodes the WHOLE file — inserting `→` via `"\x{2192}"`
  double-encoded every existing UTF-8 byte in `CascadeStrataResettle.lean`. It surfaced as
  `git diff --numstat` reporting 13/2 where 11/0 was expected; Lean would have compiled the
  mojibake comment happily. Also: this tree **mixes line endings per file** (four LF, six
  CRLF), so `numstat` vs `--ignore-cr-at-eol` numstat is now the standard check after any
  scripted edit.

**Still owed:** **SAB-5 was not run**, and its load-bearing half is the one that matters —
*"the DEFINITION pin must go red when a field is deleted from a pinned structure"*. It
cannot be observed as specified, because deleting `GraphAdmission.computedRefsNotLeaf`
breaks the build at `FullScope.lean` and `verify.sh lean` never reaches step 4c. Partial
evidence exists (step 4b was watched firing correctly this session; `2026-09-02c` watched
step 4c fire on this same field), but the specified control has not been run. Next session:
either construct a variant that keeps the tree building while the field is gone, or record
in `docs/sabotage-procedure.md` that this instrument is only observable in that narrow
window and say what the substitute is.

## 2026-09-02c — the "closed list" is a LOWER BOUND by construction, and "nothing smaller is green-stoppable" is refuted

rows: `P3`

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-02c`. New traps: scope doc §11.13 **(v)** and **(w)**.

lint: `task lint: clean (12 checks, 156 task file(s) parsed)`
read: board + HANDOFF

**The session's product is two landed prerequisites and a retired sizing.** Both of the
previous session's headline claims turned out to be wrong, and in opposite ways.

* **The census is a lower bound BY CONSTRUCTION (§11.13 (v)).** `2026-09-02b` staged `sorry`
  at all 14 `shadow_graphRec_agree` sites, got `rc=0` / 1089 jobs / zero errors, and
  concluded the list was CLOSED. The observation is right; it answers a different question.
  **A staged `sorry` discharges the new premise LOCALLY**, so the probe sizes *where the
  proof breaks*, never *which signatures must change to discharge it honestly* — and those
  differ by the entire transitive caller closure, which is what "thread the premise" means.
  Live: **62 declarations (`hcr`) + 13 (`hql`) across ELEVEN files**, five of them
  (`CascadeInv`, `CascadeStrataEdge`, `CascadeStrataAssemble`, `Equiv`, `FullScope`) in
  neither the census nor the board's 8-file list. ⚠ **(q) and (v) are the same cone
  mis-measured in opposite directions inside one week** — grep over-counted, the probe
  under-counted — which is the sharpest case yet for §11.13 item 2's rule that a site count
  is meaningless without its symbol list *and its counting unit*.
* **"Nothing smaller is green-stoppable" is refuted by kernel, twice (§11.13 (w)).** §11.12
  rule 5 forbids committing a *partial cone* — a tree whose own pins assert something untrue
  — and neither increment is one. Both additive, both green first attempt (1089 jobs, 0
  sorries). (a) **`GraphAdmission.computedRefsNotLeaf`**, the third syntactic reading of the
  one Python dot-lock the other two admission rows already model; it is the **terminator that
  cuts the `hcr` thread 79 → 62**, so landing it first makes the cone *smaller*. Non-vacuity
  is a new pair varying one axis (`FullScope::SxLeafRef`) plus a proof that every other
  decidable admission field still holds there — i.e. the field is independent, not implied.
  (b) **The widened six-field instrument** `Scratch4cii::{clsB,termB,shadowB}_correct_weak`,
  which **must** precede the flip: `shadowB_correct` is anchored at the strong shadow, so
  post-flip it would police nothing while every `decide` row stayed green. The file asserted
  this was impossible — *"has no such theorem and cannot have one"* — which was already false,
  since `ShadowOver` has been generic in its extras predicate since `2026-08-30c`.
* **Instruments controlled before use, both times.** Trap (u)'s sorry-grep was made to fire on
  purpose first (backtick-safe = 1, straight-quote = 0, same log). And `verify.sh lean` was run
  *before* regenerating the definition pin, as the control on the pin itself: it fired with
  exactly two discrepancies and no others. SAB-6's literal output is in `::termB_correct_weak`'s
  docstring — four error sites, all inside the new twin, **every `decide` row green**.
* ⚠ **Do not quote "six" or "38"** for the audited-but-unpinned residual; neither reproduces.
  Measured here: **578 audited names, 43 statement-pinned, 35 overlapping → 543 carry a NAME
  pin and no STATEMENT pin.** A name-pattern count is the wrong instrument for the question.

Pins: statements **49/49 byte-identical**, definitions **164 → 165** (deliberate),
`FINAL_REVIEW.md` counts regenerated twice (the second time for a `CORRESPONDENCE.md` anchor
this session added, 541 → 542). Gate: all ten phases re-run green.

---

## 2026-09-02b — the co-landing is a CLOSED LIST of 14 sites / 12 decls / 6 files, and `hql`'s eliminator landed

rows: `P3`

Formal detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-02b`. Traps: scope doc §11.13 **(t)** and **(u)**, plus an amendment to **(r)**.

**Entered on a stale next-task and caught it before editing anything.** The task file's
`2026-09-01d` entry records the `hag` widening as deferred, "hence its own increment". It is
in HEAD — `50535a6`, an ancestor of `dbf08a8`, landed the same day the entry called it
deferred, and the log was never updated. Acting on it would have produced an empty diff, a
green gate and a commit that looked like progress. **A board-first reader is only as good as
the board's freshness, and this is the second time in three sessions that a spent increment
sat at the top of an item.**

**The session's product is a MEASUREMENT and a missing eliminator** — the co-landing itself
was not attempted, and nothing smaller than it is green-stoppable.

* **Closed list, by probe (§11.13 (t)).** Run 1 gave one error and stopped at job 1070/1089
  — the (k) lower-bound trap, since `CascadeStable` is upstream of twenty modules. Run 2
  used (n)'s technique, staging `sorry` at every site: **`rc=0`, 1089 jobs, zero errors**, so
  nothing outside the census exists. **14 sites but 12 declarations**, because
  `graph_correct_w3d2` and `graph_correct_w3d2_d` each host two — one servable, one
  query-relation. That is why the two repairs are not separable at declaration granularity,
  and where a partial landing would be left half-done. Servability **7 of 8**.
* **The plan's one load-bearing unverified step is now a theorem.** Every scout flagged the
  same gap: nobody had checked that `hql`'s shape discharges a widened `hv1` at the three
  query sites. Verified by hand, then landed as
  `Leaf.lean::not_leafNode_of_publicOfLeaf_none` — row 27's guard's eliminator, additive,
  `lean` identical to the anchor (585/584/164), non-vacuity pinned by a RELATION-varying
  pair, two sabotages with literal output. The S2 negative control is a **permanent
  theorem** rather than a log line: a premise-free version would prove `¬ LeafNode` at a node
  the same file proves IS one.
* **A new instrument trap (§11.13 (u)), and it is the house failure mode inside the
  measuring tool.** `grep "declaration uses 'sorry'"` returns **0** — Lean uses BACKTICKS.
  Fourteen staged sorries plus `rc=0` first read back as "the premise was never needed". The
  general rule now filed: **an assurance grep must be made to fire once on purpose before
  its zero is believed**, exactly as this repo already demands of tests, floors and pins.
* **A correction appended, not merged** (ledger rule): PROOF_STATUS `2026-09-02` §7 and
  §11.13 (r) both say **six** audited-but-unpinned carriers of the step-9 premises; two
  independent measurements say **38**, omitting the whole `_w3d2` family. Both figures are
  UNVERIFIED first-hand — re-measure before quoting either.
* **Two stale docs fixed in place** (Rhythm step 5): the `P3` task file's `## Traps` bullet
  still called deleting `Scratch4cii.lean:51` "the NEXT SESSION'S FIRST EDIT" three sessions
  after it landed — and the trap's own prediction of a diagnostic red was wrong, the deletion
  built green; and this board's `P3` item block said "the flip is step 9 and is a two-line
  rollback" thirty lines above its own tail saying step 9 is done.

`python scripts/task.py lint` → `task lint: clean (12 checks, 156 task file(s) parsed)`
read: board + HANDOFF

Still owed: nothing.

## 2026-09-02 — the step-9 design call is MADE, and the step turns out to be cheaper than the record implied

rows: `P3`

**The user was asked the question `2026-09-01e` deliberately left open, weighed the
recommendation, and took it.** The adjudication: the seed-side `NotLeafName
t.subject.predicate` is to be threaded as a premise **and DISCHARGED from the
`GraphAdmission` bundle** — an undischarged premise is a landing state for an intermediate
commit only, never for the leg, because a conditional equivalence claim whose condition a
reader must go and verify is exactly this repo's house failure mode.

**The grounds were re-established FIRST-HAND rather than inherited**, which matters here
more than usual: `P20`'s adjudication is the standing warning that "Python already refuses
what the narrowing excludes" held for *zero of ten* fields, so the argument shape cannot be
cited, only re-run. Re-run, it holds. Write admission gates every tuple on a declared type
restriction (`setengine/engine.py:932`, check (2)), those restriction filters always pin
the subject predicate to bare `...` or a *referenced relation name*
(`zanzibar_utils_v1.py::_restriction_pattern` `:1012-1019`, plus
`RelationalTriplePattern.match` `:288`), and a referenced name can never carry a dot
(`_validate_ast_references`, `:916-919` — the same dot-lock step 7 already modelled as
`CascadeStable.lean::ComputedRefsNotLeaf`). So the premise describes an **enforced
invariant**, not a scope carve-out: it belongs in `GraphAdmission` (whose every field cites
its enforcing mechanism) and not in `W4Fragment` (the honest-gaps bundle).

**A second finding fell out of checking the premise, and it shrinks the step:** the
consumer already exists. `CascadeStable.lean:880::rewriteClosure_subject_not_leafNode` is
the post-flip `hsubj` shape stated over `rewriteClosure S t` verbatim, and of its two
premises the schema-side `hQ` is already owned
(`::ttuTargetsSat_notLeafName_of_noLeafSubjects`). Step 9 SUPPLIES `hbase`; it does not
prove a closure theorem, which is how this row had been reading.

**Then the seed side was given an owner, and it landed.** Six new declarations in
`CascadeStable.lean` — `NoLeafStoreSubjects`, the schema fact `DirectRestrictionsNotLeaf`,
two bridge steps and the discharge in both admission forms — all additive, green first
attempt at 1089 jobs, no existing declaration or signature touched. The discharge closes on
one line of the spec: `restrictionMatches`' middle conjunct is
`tup.subject.predicate == r.2.1`, so an admitted tuple's subject predicate is *equal to*
some declared restriction's, and the whole question reduces to a schema fact. Two sabotages
were run and both fired attributably (narrowing `exprDirectsAll` → `exprDirects` reddens
exactly the one discriminating witness; reading `r.1` instead of `r.2.1` reddens both).

⚠ **The trap that nearly ate this, worth carrying:** the clause had to be `NotLeafName`-shaped
("`= BARE` or dot-free"), never `relNameOK`-shaped ("dot-free"). `BARE = "..."` is itself
dot-carrying, and every `Direct` restriction in every `GraphAdmission` witness schema is
`("user", BARE, _)` — so the "obvious" dot-free clause is FALSE at all three witnesses and
would have **re-vacuated** the headline theorems instead of narrowing them. That is the
2026-08-05 vacuity failure mode arriving through a new door.

Decision, its rejected alternatives and the verification detail:
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-02`.

⚠ **The `lean` phase caught this entry's own absence**, along with both HANDOFF ceilings
and the trap-badge budget — all four at ZERO headroom, so the doc edits had to be made
net-neutral rather than merely correct. Worth recording because the first run *looked*
green: the background wrapper reported exit 0 while `verify.sh lean` returned `rc=1`, which
is CLAUDE.md's first standing footgun arriving in a new costume. Read the verdict line.

`task lint: clean (12 checks, 156 task file(s) parsed)`

`read: board + HANDOFF` — `python scripts/task.py board` ran first and correctly named `P3`
and the pending call, but the question was *which way to decide*, which needed the
adjudication history the board does not carry (`HANDOFF.md`'s `P3` block, PROOF_STATUS
`2026-09-01e`, and the `P20` warning). Same split as `2026-09-01`: the board replaced the
file read for orientation, not for adjudication.

**And one of the three sites is threaded end to end.** `reachedByW3d_shadow` now takes both
premises — it is TWO, not one: the seed premise alone cannot survive a `.ttu` hop, which
overwrites the subject predicate with the schema's rule target, so the schema-side
`TtuTargetsSat S NotLeafName` rides along. Measured cost, a closed list rather than a grep:
**18 declarations across 6 files**, and `CascadeStrata*` does not move at all — the census
lines there were docstrings the filter missed, which retires both `5+7+8=20` and this
session's own raw `46 lines / 9 files`.

**The control was the flip probe (trap (n): a pre-widen can only be vetted by the re-point)
and it came back positive.** Before this increment the flip red `CascadeStable` four times,
two of them the `hsubj` obligation; after it, those two are replaced by exactly the `Or.inl`
wrapper mismatch the pre-widen is designed to leave, and passing the wide form clears them —
leaving only `shadow_graphRec_agree`'s `hv1`/`hv3`, which are the other two obligations. Six
new `FullScope` pins machine-check that both premises hold at all three `GraphAdmission`
witness schemas, so nothing became vacuous.

**Then the other two sites landed, and the discharge with them — step 9 is done.**
`reachedByW3d2_shadow{,_d}` take the same pair (the `_d` variant routes the seed side
through the widened discharge lemma, which is why both were built), and `GraphAdmission`
gained `ttuNotLeaf` + `directRestrNotLeaf`. All four construction sites prove them
`by decide` — that IS the non-vacuity evidence, since the `relNameOK`-shaped clause would be
false there and leave the structure uninhabited. The headline theorems take both from the
bundle, so `graph_correct` and `graph_reached_inv` assume exactly what they assumed before.
The pin cost came in exactly as the adversarial pass predicted: `headline_statements.txt`
byte-identical, `headline_definitions.txt` regenerated deliberately 161→164 (the
`GraphAdmission` row plus three newly-reachable definitions — *the meaning of a claim grew
three dependencies*, which is what that pin exists to catch), and `FINAL_REVIEW.md`'s counts
block with it.

📏 **And the flip is now ONE obligation.** Re-running the flip probe on the finished tree,
the only reds are the eight `Or.inl` wrappers the pre-widens were designed to leave, plus
`shadow_graphRec_agree`'s `hv1`; with the wrappers swapped and `hv1` alone stubbed the whole
tree builds (1089 jobs, exactly one `sorry` warning). The probe was fully reverted.
`2026-09-01e`'s "four unowned obligations" is retired — `hv1` needs row 27's query-level
premise and is all that stands between this tree and 4c-ii.

⚠ **One residue, written down rather than left to be found.** The six audited TERMINAL
`_w3d`/`_w3d2` milestone theorems still spell their premises out one by one and now spell
out two more. The gate cannot flag that: `audited_theorems.txt` pins NAMES only and none of
the six has a `headline_statements.txt` row — the house failure mode exactly. It is bounded
(the facts are `GraphAdmission` fields, witness-checked, and the headline layer takes them
from the bundle), but retiring it means re-stating those six over the bundle, which is a
separate decision and not part of step 9. PROOF_STATUS `2026-09-02` §7.

---

## 2026-09-01e — step 8's free content landed; the flip's remaining cost is now a CLOSED list of four

rows: `P3`

**Step 8, taken by the cheaper route the previous entry flagged but could not check.**
`untaintedShadow_applyD` and both `untaintedShadow_applyLoggedR{,_d}` are PRE-WIDENED in
place with step 5's `first | <post-flip> | <today's>` idiom — no new declaration, no
signature change, no call-site churn, and no exposure for `Audit.lean:786`'s name pin. The
widened subject-side obligation costs **no new premise**: `W3cJobValid`'s `hcb` already
makes every candidate's predicate `BARE`. Green first attempt at every stage, 1089 jobs,
zero of a six-cycle abort budget.

**The bigger result is the measurement.** 2026-09-01d's "6 errors in 3 declarations" was a
LOWER bound because Lean does not build dependents of a failed module. Running the probe in
five stages — stubbing each *known-blocked* obligation with `sorry` so the build proceeds
past the red module — closed it: the second wave is **8 more errors in 4 declarations, all
in `CascadeStrataSettle.lean`**, and with the flip applied and only the four unowned
obligations stubbed **the whole tree builds green**. So the flip's complete remaining cost
is **5 repair sites in 4 declarations across 2 files** — 3 free and now landed, 1 free at
step 9 (delete two `Or.inl` wrappers), and 4 obligations blocked on premises nothing owns.
That replaces 2026-08-30c's scout figure of "~20 sites in 3 files".

**Trap (k) in its exact form, and it is recorded rather than papered over.** The post-flip
alternative of a `first | … | …` block is dead code today, so the sabotage (`hoffW` narrowed
to its `DerNode` half) is **GREEN unflipped and RED under the flip** — both halves run, both
literal outputs in the entry. The standing control for this kind of change is the flip
probe, not a weakening.

Formal detail, the five-probe table, the literal sabotage output and the gate-safety check:
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-09-01e`.

Still owed: nothing from this session. **Step 9 is blocked on a DESIGN DECISION, not proof
effort** — the seed-side `NotLeafName t.subject.predicate` wants a store-level
`NoLeafStoreSubjects T` threaded through `reachedByW3d_shadow` / `reachedByW3d2_shadow{,_d}`,
which changes their premises and hence potentially the headline theorems; the board already
records that as needing a human call. Do not thread it unasked. `hv1` still waits on row
27's query-level premise.

```text
task lint: clean (12 checks, 156 task file(s) parsed)
```
read: board + HANDOFF

## 2026-09-01d — trap (g) dissolved: `hag` now carries the membership it always threw away

rows: `P3`

**The increment the previous entry left owed, landed.** `ReconcileStars.lean::
checkFn_agree_of_graphRec` and `::checkFn_agree_of_graphRec_cd` now hand their `hag`
callback `r' ∈ computedRefs e` alongside the derivedness fact. That membership was never
missing — the callback has always bound it, as `evalE_computedOnly`'s own premise, and spent
it only on `hleafUnt`. All nine producer sites took one ignored binder; the new consumer
`CascadeStable.lean::checkFn_agree_of_graphRec_notLeafNode` turns it into `¬ LeafNode` via
`notLeafNode_of_computedRef`. Green first attempt at every stage, 1089 jobs.

Formal detail, the literal sabotage output and the call-site partition:
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-09-01d`. The short version:

* **The sabotage that mattered is not the obvious one.** Reverting the widening proves only
  that the edit exists; a widening nobody consumes is green by construction — the same
  hazard `ComputedRefsNotLeaf` shipped with last session, one level up. The weakening run
  was **"the binder was added and carries nothing"**: `hag`'s new premise became `r' = r'`
  and the forward became `rfl`. One error, at the consumer. **All nine call sites stayed
  green**, because each discards the membership with `_` — so the call sites cannot tell a
  real membership from `rfl`, and the consumer is the only instrument in the tree.
* **The recorded way-out citation was incomplete.** "`:618/:622/:633`" is binder / discard /
  binder and names only ONE of the two discards; **`:637` is the `_cd` twin's**. A session
  editing exactly the three cited lines would have shipped half the change. Cite
  `file::symbol`, per the standing trap.
* **The binder is still deferred — and no longer by trap (g).** The 14
  `shadow_graphRec_agree` sites partition **3 + 8 + 3**: three arrive via the `hag` callback
  (served now), eight already hold the membership locally, and three —
  `CascadeSettle.lean:1119`, `CascadeStrataResettle.lean:1539` and `:2683`, **opened
  first-hand because the deferral rests on them** — apply the lemma at the *query's own*
  relation inside the `untainted query` branch, where no `computedRefs` membership exists or
  can. Those need row 27's query-level premise, which is not landable before step 9's flip.
  **`11 = 3 + 8`** is where the ten-step plan's "11 call sites" came from; the plan simply
  never wrote down that the other three are a different repair.
* **An unbudgeted site surfaced.** `CascadeStrataEnum.lean::checkFnR_star_declared`
  (`:336-345`) has no `hlk` binder, so it will need a lookup premise as well as
  `ComputedRefsNotLeaf S` when the threading increment runs.
* **Gate safety, verified first-hand rather than delegated:** zero golden rows for the
  predicate and both eliminators, and none in `Audit.lean` either — so last session's lemmas
  were not audited and this one followed that precedent instead of inventing an audit row.
  The exposure runs the other way: `Zanzibar.computedRefs` **is** pinned in
  `headline_definitions.txt`, so threading it is free only while that declaration stays
  byte-identical. Do not tidy `computedRefs` while threading it.

`python scripts/task.py lint` → `task lint: clean (12 checks, 156 task file(s) parsed)`

read: board only  (`task.py board` was the first command of the session and named the right
next action; `show P3` supplied the item detail. The root `HANDOFF.md` was not opened for
orientation — it was opened at write-back, to edit it. ⚠ **`show P3` overflowed the context
again — 60KB this time, up from 35KB on 2026-09-01b** — so the item had to be piped to a
file and read from the tail. That is the same TT-1 blocking gap the earlier entry recorded,
recurring and growing: `show` still has no bounded mode, and a per-item read that cannot fit
in a context window is not a replacement for a file. Bulk reading was pushed into subagents
this session, per the user's standing preference, which is why the file-level census work
does not appear as reads here; every gate-safety and deferral claim above was nevertheless
re-verified first-hand before being written down.)

* **Step 8 was sized by measurement, not by the plan's prose.** The plan gives it six words
  and names none of the lemmas; the only document that does is under `.scratch/`, i.e.
  already lost. So the flip was run as a throwaway **probe** — point the abbrev at the
  disjunction, build, read the errors, revert — and it reds **6 errors in 3 declarations,
  all in `CascadeStable.lean`**: `untaintedShadow_applyD`, `reachedByW3d_shadow`,
  `shadow_graphRec_agree`. Tree byte-identical afterwards. ⚠ A **lower** bound —
  `CascadeStrataSettle.lean` never compiled, so its two `apply*` lemmas and two `hsubj`
  sites are unmeasured. Two corrections fell out of the sizing greps: **step 9 is a
  ONE-line edit** (the `Leaf` import is already `CascadeStable.lean:2`, so the plan's
  "rollback = revert two lines" is stale), and `untaintedShadow_applyD` is **name-pinned**
  via `Audit.lean:786` with exactly two call sites — step 8 may add binders but must not
  rename it.

**Still owed: nothing skipped.** Next green-stoppable move is **step 8**, untouched by this
session but now measured. The `hnl` binder depends on **step 9**, not on trap (g); that is a
real change in the dependency graph and the board row says so. Note what the probe implies
about ordering: `shadow_graphRec_agree` and the `hsubj` sites red in the *same first wave* as
`untaintedShadow_applyD`, so landing step 8 does not by itself make the flip green.

## 2026-09-01c — step 7's named premise was FALSE: Python enforces a dot-lock, not declaredness

rows: `P3`

**The step landed under a corrected name.** 4c-ii step 7 is enumerated
(`formal/history/PROOF_STATUS.md:933-943`) as "`ComputedRefsDeclared` + an unused `hnl`
binder on `shadow_graphRec_agree`". **`ComputedRefsDeclared` models nothing.** Measured,
not argued: `zanzibar_utils_v1.py::_validate_ast_references` refuses a referenced relation
name iff it contains `.` and is not `...`; an UNDECLARED operand is accepted and compiled,
both plain and inside a boolean relation. A declaredness clause would be strictly stronger
than Python — excluding schemas the implementation runs — and would contradict
`Core/Schema.lean:66-69`, which already records declaredness as deliberately *not* a `WF`
clause. Landed as **`ComputedRefsNotLeaf`**, over `Leaf.lean::NotLeafName`, which matches
the Python check byte for byte including the `'...'` escape.

Formal detail, the probe's literal output and both sabotages:
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-09-01c`. The short version:

* **The change is INERT, so the eight pins are the sole evidence** and the docstring says
  so (`docs/sabotage-procedure.md:100-141`). Best of them: the census hole is now
  *exhibited* — `slVBadRef_hunt_holds` shows `shadow_graphRec_agree`'s `hunt` HOLDS at a
  minted leaf name, which is the whole reason the step exists; and the discriminating
  control `computedRefsNotLeaf_ghost_true` makes the dot-lock-vs-declaredness call
  machine-checked rather than a docstring assertion.
* **Sabotage S1 was a verdict on the PINS, not the code.** Swapping in the plan's own
  `relNameOK` died at `failed to synthesize Decidable …` before reaching a pin, so it never
  tested the BARE escape it was aimed at. Three more pins were added afterwards to cover
  the gap it exposed. S2 (narrow the quantifier to the first def) fires attributably —
  one pin red, five green.
* **`hql` was never landable, and this was re-verified first-hand.** `graph_correct` is a
  *proved theorem of today's tree*, so the binder is a weakening of a byte-pinned headline
  that nothing in the gate can distinguish from not adding it.
  `docs/latent-gaps.md:164-167` already adjudicates it: "never before … never after".
* **Two corrections to the record.** The `shadow_graphRec_agree` call-site count is **14**,
  not 11 (the plan counts only the direct sites; 3 more are `hag` callbacks). And the
  previous entry's "`P3` continues at step 7 (row 27's `hql` guard)" mixed two numberings —
  under the live ten-step plan `hql` is **step 10**.

`python scripts/task.py lint` → `task lint: clean (12 checks, 156 task file(s) parsed)`

read: board only  (`task.py board` + `show P3` was the whole session-start view; the root
`HANDOFF.md` was never opened. `formal/HANDOFF.md` — a different file, the formal-frontier
pointer the `P3` item names under "Read first" — was read as item content, not as the board.)

**Still owed:** the binder threading, deferred deliberately with its design settled. It
needs `r' ∈ computedRefs e` at `shadow_graphRec_agree`, which
`ReconcileStars.lean:618/633` currently discards from the `hag` callback — scope-doc
§11.13 trap (g). **The way out is new this session**: `ReconcileStars.lean:622` already has
`hr'` in scope and throws it away, so widening `hag` to pass it through dissolves the trap.
That touches `checkFn_agree_of_graphRec{,_cd}` (9 sites) plus the 14, so it is its own
increment.

## 2026-09-01b — the Class-B repair LANDS: rows 46/56 on `checkPublic`, all four conditions discharged

rows: `P3`

**The execution session for what `2026-09-01` decided.** That entry adjudicated and built
nothing; this one built it. Rows 46 and 56 — `W4WitnessDirect.correct_applies` and
`::w3d2E_correct_applies` — are now stated over `GraphModel.checkPublic`. Neither took an
`hql` binder. Row 27 is untouched, so **the remaining `hql` surface is ONE row again** — by
migration, not by the 2026-08-28c argument that was refuted for claiming it.

Formal detail, both sabotages' literal output, and the gate record:
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-09-01b`. The short version:

* **The known unknown is REFUTED, and by the kernel rather than a source read.** There is
  no `reachedByW3d2C_schema`, none is needed, and the 2026-08-31c grep that failed to find
  one **was looking for the wrong name**: row 46's schema bridge composes as
  `reachedByW3d2_schema (reachedByW3d2C_toW3d2 h)`. It typechecks; `lake build
  ZanzibarProofs.FullScope` was green on the first attempt. The pessimistic "may need
  landing" branch never existed.
* **Condition 2 was the only real work.** `fence_changes_answer` proves the fence *fires*;
  nothing proved a migrated row still carries the audited core through the other branch,
  which is how these two could have degraded into certifying the fence alone. Three new
  statement-pinned instruments close it: `public_grant_survives_fence` (the fence is not
  total — new `σPub`/`qPub` differ from `σLeaf`/`qLeaf` only in the leaf-ness of the name)
  and `correct_applies_nonfence` / `w3d2E_correct_applies_nonfence` (each recovers the
  ORIGINAL unfenced statement at a query the fence provably does not touch). **Both
  sabotages were run**, and the observed output is in the docstrings.
* **Condition 3's two UNVERIFIED claims were re-verified first-hand, and both held.**
  `headline_definitions.txt` needed no regeneration — checked by inspection and then
  empirically, by regenerating it and finding it byte-identical. `audited_theorems.txt`
  pins names only, per its own header.
* ⚠ **A footgun found and disarmed: `statement_pin.py`'s list order IS the golden's line
  order.** Filing the three new pins thematically, next to the `fence_*` pins they belong
  with, moved `w3d2E_correct_applies` from row 56 to 59 and shifted the scope doc's
  `53, 59, 64` enumeration — **silently falsifying every living "rows 46/56" citation in
  the repo**, the same rot as the stale `:45`/`:55` numbering already on record. The pins
  were appended at the list tail instead (rows 65-67, nothing shifted; 46/53/56/59/64
  re-verified), with a ⚠ comment there so the next person files the same way. This also
  surfaced a pre-existing off-by-one: `formal/HANDOFF.md` cited `unfenced_grants` as
  `:51`, and it is `:52`.
* **Doc sweep:** `formal/HANDOFF.md`, `HANDOFF.md`'s banner + `P3` row, `tasks/BANNER.md`,
  `docs/latent-gaps.md` (the `hql`-guard section rewritten to the current one-row truth —
  that file has replace semantics, so the stacked corrections were folded in, not
  extended), `docs/gate-runbook.md` (a rotten hardcoded "26 statements" count dropped for
  a pointer at the golden — no count belongs in prose), and a dated **(m)** appended to
  scope doc §11.13 marking (e)/(l) spent and correcting what they assert.

**Gate:** all ten phases green on this tree; `lean` re-run last, after every `*.md` edit.
`lean` failed once mid-session and correctly — step 4e caught `FINAL_REVIEW.md`'s counts
block gone stale against the two new `#print axioms` lines; regenerated with
`doc_counts --generate`. One red was self-inflicted: a 21-line `tasks/BANNER.md` against a
14-line cap, which surfaced as two FAILING `tests-tile` phases via
`test_tasktool.py::test_sabotage_live_blind_parser`'s baseline-green precondition.
`task.py lint` reports that in one second — **run it right after touching `tasks/`**,
rather than paying for it in tile runs.

`python scripts/task.py lint` → `task lint: clean (12 checks, 156 task file(s) parsed)`

read: board only

**Still owed:** nothing from this session. `P3` continues at **step 7** (row 27's `hql`
guard, co-landing with 4c-ii). The seed-side `NoLeafStoreSubjects T` / ~20-call-site
figure remains **scout output, unverified** — re-check it before minting the predicate.

## 2026-09-01 — the Class-B repair is ADJUDICATED: rows 46/56 migrate onto `checkPublic`, the `hql` binder refused

rows: `P3`

**A decision session. No Lean file, proof, pin or golden was modified** — the product is the
adjudication and the doc re-pointing it required.

**The user asked for the pending call to be weighed, took the recommendation, and directed
that every record still deferring to them point at the decision instead.** So:

> **Rows 46 and 56 of `headline_statements.txt` — `W4WitnessDirect.correct_applies` and
> `::w3d2E_correct_applies` — are RE-STATED over `GraphModel.checkPublic`. They do NOT get an
> `hql` binder. Row 27 (`graph_correct`) keeps the binder accepted 2026-08-28; that call is
> not reopened.**

**Why.** Rows 46/56 are satisfiability witnesses with `q` universally quantified — their job
is to certify that the headline's hypothesis set is inhabited. An
`hql : publicOfLeaf S q.object.type q.relation = none` binder puts a schema-dependent
hypothesis on exactly the declarations that exist to detect unsatisfiable hypotheses, which
is the failure `FullScope.lean::graph_correct_public`'s docstring already refuses for
`final_applies`. The migration, by contrast, is a landed precedent (seven declarations on
2026-08-28c, **none gained a hypothesis**), and the pin that makes the fence contentful —
`fence_changes_answer` — is stated at `Sd`, the same schema rows 46/56 are instantiated at.
It is also the honest correspondence: `checkPublic` models the real public
`WildcardIndex.check`, while an `hql` binder models nothing in the Python. **Nothing true is
given up** — post-re-point the unguarded statement is machine-checked FALSE, so the choice
was only ever *which* weakening.

**Four conditions bind the repair session**, and the first one is what discharges `P3`'s
standing "do not smuggle this into step 7" — by sequencing rather than deferral: (1) its own
session and its own green commit, landing **before** step 7, on today's tree; (2) sabotage
the migrated witnesses' **non-fence** branch, since `fence_changes_answer` proves the fence
fires but not that the witness still exercises `graph_correct` through the other branch;
(3) re-verify the two paragraphs `2026-08-31c` labelled UNVERIFIED
(`headline_definitions.txt`, `audited_theorems.txt`) rather than trusting them from prose;
(4) doc sweep in the same commit, `verify.sh lean` re-run after the `*.md` edits.

⚠ **One known unknown, surfaced rather than discovered cold later.** Row 28's fence branch
takes `σ.schema = S` from `CascadeStrataAssemble.lean::reachedByW3d2E_schema`, which row 56
can reuse — but row 46 hypothesises `ReachedByW3d2C` and **no `reachedByW3d2C_schema` turned
up in a name grep**. It may be a structure field, exist under another name, or need landing.
**That is a grep, not a build**: sizing input for the repair session, in this repo's
"reported, not verified" sense.

**Records re-pointed so nothing still defers to the user:** `HANDOFF.md` (banner, `P3` row,
`P3` item block, read-first); `formal/HANDOFF.md` — the refuted "ONE pinned row" line struck
in place, plus a new warning that its dated-block series stops at 2026-08-28c while four
sessions have landed since; `docs/latent-gaps.md` — "what would close it" is now **two**
moves, because rows 46/56 close *early* and independently of the 4c-ii commit; scope doc
§11.13 (e) and (l); `tasks/P3` + `tasks/BANNER.md`. Full grounds:
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session 2026-09-01`.

**Trial close-the-loop.**

`task lint: clean (12 checks, 156 task file(s) parsed)`

**read: board + HANDOFF.** `python scripts/task.py board` ran first and named `P3` and the
pending call correctly — but the user's question was *which way to decide*, and that needed
adjudication history the board does not carry: `HANDOFF.md`'s `P3` block, PROOF_STATUS
`2026-08-31c`, and `graph_correct_public`'s own docstring. Honest reading: the board
**replaced** the file read for orientation and did **not** replace it for adjudication — a
narrower win than `2026-08-31c`'s "board only", and the gap is the item's *history* rather
than its *state*. Worth weighing against `TT-1`: a cutover has to put that history somewhere.
⚠ Also observed: `BANNER.md`'s 14-line cap was hit three times in a row because two of my
"fixes" swapped two lines for two lines instead of removing one. The lint refused every time
and its message was right each time — recorded because the failure was mine, not the tool's.

**Still owed:** nothing.

---

## 2026-08-31c — the Class-B spike is answered: it REACHES `graph_correct`, on THREE pinned rows not one

rows: `P3`

**The spike `P3` has carried as TOP OPEN RISK since 2026-08-30d is discharged.** The step-7
guard obligation **reaches** the byte-pinned `graph_correct` (`headline_statements.txt:27`) —
but by only **one** of the three Class-B sites; `graph_correct_w3d` and `graph_correct_w3d2`
die in `Equiv.lean` milestone theorems that are labelled superseded in-file. The consumer
sets were re-verified first-hand rather than taken from the subagent that traced them,
because it is a gate-safety claim.

**And the surface is wider than this repo's records said.** Rows **27 / 46 / 56** carry no
`checkPublic`, so `graph_correct`, `W4WitnessDirect.correct_applies` and
`::w3d2E_correct_applies` all sit below the fence — the latter two consuming the `_d`
theorems directly. That **refutes** the 2026-08-28c claim (repeated verbatim in
`HANDOFF.md`) that the remaining `hql` surface is one pinned row, and independently confirms
scope-doc §11.13 (e), which had reached the same conclusion by a different route.
⛔ **The repair is deliberately NOT started**: it weakens pinned statements on the two
*non-vacuity instruments*, where an `hql` binder risks a hypothesis nothing satisfies — the
exact failure `graph_correct_public`'s docstring warns about. That is a user-visible scope
change and `P3`'s own record forbids folding it into step 7. **It needs an explicit user
call.**

**Step 6's one free obligation landed.** `CascadeStable.lean::shadow_graphRec_agree`'s `hv3`
is pre-widened to `¬ (DerNode ∨ LeafNode)` at the `wAll` node with **zero** new premises, so
step 9's flip becomes "delete two `Or.inl` wrappers". Green first try, 1089 jobs, 3 of a
6-cycle budget. `hv1` was deliberately left alone — it needs a premise that cannot be phrased
locally and drags in a third file. **Four obligations remain, not five.**

**Method lesson, filed as scope-doc §11.13 (k) because it is about the sabotage procedure
itself:** the first sabotage of the new pin **failed to fire**, and not because the pin was
strong — `wAllNode` is guarded *redundantly* (`k.name != STAR` **and**
`k.variant == Variant.plain`), so weakening either alone cannot reach the assertion. Stopping
there would have recorded a passing sabotage that proved nothing. Dropping both fired it. It
was also **not** the only error (`leafNodeB_correct` broke too), which is reported rather
than tidied away, and the count is a lower bound because Lean skips dependents of a failed
module.

Detail: [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session 2026-08-31c`.
New durable pin: `Leaf.lean::wAllNode_not_leafNode`.

Trial close-the-loop, the two required literal lines:

    task lint: clean (12 checks, 156 task file(s) parsed)
    read: board only

`task.py board` was the first command of the session and named the next action correctly and
*sufficiently to start work* — `HANDOFF.md` was not opened to orient. **This is the first
session in the trial where the query genuinely REPLACED the file read** rather than being
added to it, and the reason is worth recording for the cutover decision: the 35KB `show P3`
never had to fit in context, because the harness persisted it to a file read in slices and
three delegated read-only scouts absorbed the Lean/doc bulk. So the "`show` has no bounded
mode" gap logged against `TT-1` on 2026-08-30d is **mitigable, not fatal** — but it was
mitigated by the *harness*, not by `task.py`, so that blocking-gap note stands as written.

Still owed: nothing.

## 2026-08-31b — `P20`: the narrowing is accepted because Python REFUSES what it excludes, and the refusal is now pinned

rows: `P3`, `P20`

Formal detail is [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-31b`. This entry is the root trace. **Gate:** ask
`python scripts/gate_status.py`, never a line here.

**This entry is opened BEFORE the first Lean edit** and is committed docs-only, per the
§11.12 rule-1 preamble. Green anchor `077bb50`, verified COVERED first-hand. It is
appended to as the session proceeds.

**Scope fixed up front:** `P20` (a)+(b) and the one unblocked `P3` edit (the bridge). Step 6
itself is **not** taken — adjudicating a change and landing it in the same session is the
shape the user declined on 2026-08-31.

**1. `P20` is adjudicated: ACCEPT.** The `NoLeafSubjects` narrowing of `W4Fragment` excludes
only schemas Python already refuses to compile (`zanzibar_utils_v1.py::_validate_ast_references`
raises on any referenced name containing `.`), so the narrowed `graph_correct` still covers
every schema the system can be made to accept. That argument was prose; it is now a test —
and the sabotage shows it is **load-bearing, not decorative**: with the validator neutered,
`define safe: viewer.0 from parent` compiles to exactly the rule the new field forbids, so the
narrowing would be *unsound*, not merely tight.

**2. ⚠ The guard immediately refuted the general shape of that argument, and this is the
session's most important finding.** Deliverable (b) forced a field-by-field classification of
`W4Fragment`'s ten EXISTING fields against Python enforcement, probe-derived. Result:
**LOUD 0 · MIXED 3 · SILENT 7.** Zero existing fields are loudly enforced. So "Python refuses
what the fragment excludes" is the **exception in this structure, not the rule** — seven
fields are silent scope holes where a violating schema is accepted, runs, and answers
queries, its correctness resting on the differential net rather than on `graph_correct`.
`ttuStarFree` is one of them (`folder:* parent doc:d1` on a TTU tupleset: **admitted**), which
is exactly what board row `P6` exists to fix. **The next narrowing does not inherit this
one's justification.**

**3. Three artifacts landed, each sabotage-controlled** — detail and literal outputs in
`PROOF_STATUS` §3:
* `formal/conformance/test_w4fragment_scope_pin.py` (15 tests) — the mechanical refusal. Parses
  `W4Fragment`'s fields out of Lean by NAME and matches them against a **hand-maintained**
  classification table. Not redundant with `headline_definitions.txt:102`, which pins the same
  field list but is **auto-regenerated** — accepting a narrowing destroys that signal in the
  same act. Sabotaged three ways, including blinding the *instrument*.
* `formal/conformance/test_leaf_namespace_correspondence.py` (5 tests) — the Python mirror of
  the Lean predicate, labelled in its own docstring as a **re-implementation, not a
  machine-check** (zcli has three modes and no channel for an arbitrary Prop; a fourth mode is
  what a real differential would need).
* `CascadeStable.lean::ttuTargetsSat_notLeafName_of_noLeafSubjects` — the `P3` bridge, green at
  1089 jobs in 5 of a 6-cycle budget, plus **removal of a FALSE sentence from the Lean source**
  claiming `NoLeafSubjects` "does not discharge these". Three sites remain undischarged; the
  correction does not overclaim.

**4. A pre-existing coverage hole, found on the way.** The `.`-lock had **zero** pins on the
DSL front-end, and the **TTU-target route had zero on either front-end** — the only pin
anywhere was `tests/test_openfga_json.py::test_rejects_reserved_dot_in_referenced_names` (JSON,
two other routes). That is not a gap created by this work; it was already there, on the exact
route the new Lean field depends on.

**5. Floors.** Conformance collects 515 (was 495). `MIN_CONF_ALL` 495 → 515 and
`MIN_CONF_REST` 391 → 411, re-measured first-hand. The floors are `-ge` so this was not needed
to stay green — it is the deliberate edit the zero-headroom convention asks for, since leaving
495 would have silently bought 20 tests of slack.

⚠ Per the standing rule, all three implementer reports are **evidence, not findings**:
the classification counts, the collection counts, the tree state and the floor arithmetic were
each re-derived first-hand before being written here. One scout figure was refuted that way
(“4 TTU targets corpus-wide”; live **28**, a 7× floor slack had it been inherited).

**6. Two small things worth their line.** (i) `tasks/BANNER.md` was **stale at `2026-08-30c`**
— the 2026-08-31 session rewrote `HANDOFF.md`'s banner but not this one, so the task tree's
session-start view still carried "repoint the abbrev at `DerNode` **OR** `LeafNode`" (the
misread disjunction that same session refuted) and "delete `Scratch4cii.lean:51` first"
(trap (h), closed 2026-08-30d). Both are now gone. ⚠ **This is the parallel-update contract
failing in the direction the trial exists to measure** — the board arm was updated, the tree
arm was not, and nothing caught it, because `task.py lint` checks the banner's SHAPE (line
cap, renderable glyphs) and not its freshness. Worth a lint check; not added this session.
(ii) `task.py::ASCII_FOLD` has no mapping for the disjunction glyph, so the banner cannot
spell the very symbol `P3`'s headline finding is about. One line to add, deliberately NOT
added here: editing `scripts/task.py` mid-session changes `t2c` and would have invalidated
the gate tiles already running.

**7. An adversarial audit of this session's own write-back found 8 defects, 3 of them
gate-red or claim-inflating.** Run as a read-only pass over the records BEFORE committing,
against the live tree. It is the single highest-value thing this session did, and everything
below would otherwise have been committed as true:
* ⚠ **`tasks/config.json`'s `min_tasks_parsed` was not ratcheted when `P21` was filed** —
  and **the entry immediately above records the identical miss from 2026-08-31, in the
  identical shape** (file a row, forget the floor, let `tests-tile:1/4` find it). Twice is a
  pattern, not an accident. `task.py new` has just written the file and could raise the floor
  itself, or refuse to exit 0 until it is raised; **a warning in a provenance string has now
  demonstrably failed to cause the behaviour twice.** Ratcheted 155 → 156.
* ⚠ **Closing `P20` swept its id from the board's `deps` cell but not from the task tree's**
  (`tasks/P3-….md` still read `deps: [P20]`), reddening
  `tests/test_tasktool.py::test_sabotage_live_blind_parser`. Note the direction: it is the
  same one-armed update §6(i) describes, **committed by the same session that wrote §6(i)**.
  The board arm is the one that gets remembered. Swept via `task.py dep rm`.
* ⚠ **`FINAL_REVIEW.md`'s "differential conformance tests" figure was inflated by 20** —
  both new modules were counted as Lean-vs-Python differentials when neither is one, which is
  what `doc_counts.py::TOOLING_FILES` exists to prevent. So the one number in the repo that
  quantifies differential coverage was inflated **by exactly the two files this session had
  just finished recording as not differentials.** Triaged; the figure is back to 449/13.
  ⚠ **And the gate could not have caught it**: step 4e's `--check` compares the block against
  a *regeneration of itself*, so a mis-triaged file is self-consistently wrong and stays
  green. Filed with the method lesson in `docs/sabotage-procedure.md`.
* Three more, all fixed: a `CascadeStable.lean:946`/`:956` citation carried forward stale
  (the census hole is `::shadow_graphRec_agree`) — **on a row whose own trap says "cite
  `file::symbol`", and in the same session that landed a pin asserting evidence must not
  contain a bare line number**; an overclaim that the three `rewriteClosure` sites "now need
  one premise, not two" when the Lean docstring says neither is available there; and the
  banner carrying `(nav)` (the ASCII fold's *output*) instead of the glyph.

The transferable part: **the records are an artifact, and they need the same adversarial
treatment as the code.** Every one of these was written by someone who had just verified the
underlying work first-hand — accuracy about the subject did not carry over into accuracy
about the write-up.

**8. The trial's two closing lines — and I omitted them until asked.**

    task lint: clean (12 checks, 156 task file(s) parsed)
    read: board + HANDOFF

⚠ **`read: board + HANDOFF`, and it was ADDITIVE, not substitutive** — `task.py board` and the
full `HANDOFF.md` read went out in the same first tool call, and I would have needed
`HANDOFF.md` regardless: the board view carries no item blocks, so the read-first lists, the
traps and the Rhythm protocol are only in the file.

⚠ **SAME-SESSION CORRECTION, and it is the NINTH record defect of this session** (the audit in §7 found eight; this is the one that got past the audit too). The
sentence here first read "the third session in a row to report the query as a supplement
(2026-08-30c, 2026-08-31, here)". **Both citations are wrong**: `2026-08-30c` carries no
`read:` line at all, and `2026-08-31` is the one session that reported **`board only`** — so
"in a row" is exactly backwards. Measured over every `read:` line in this file:

    board + HANDOFF   10        board only   1        HANDOFF only   0

**and the single `board only` is the session immediately before this one.** The corrected
figure is much stronger evidence than the false one it replaces, in the same direction: across
eleven sessions the query has substituted for the file **once**. Written down as a caution —
I asserted a trend from memory in the same entry that spends a paragraph on records needing
adversarial checking, and it took a `grep` of one file to refute.
⚠ **And these two lines were MISSING from this entry until the user asked for feedback on the
board** — written afterwards, which is exactly the failure mode they exist to expose. The
instrument is self-reported and unenforced: nothing in `task.py lint`, `handoff_lint.py` or
the gate checks that a session-log entry contains them, so a session that skips them looks
identical to one that had nothing to report. **A lint check for these two lines is the
cheapest possible fix and would have caught this.** Recorded plainly because the trial's whole
value is the honesty of this datum, and a self-report that only appears when someone asks is
worth less than one that is refused when absent.

Still owed: nothing.

## 2026-08-31 — the 4c-ii middle's blocking question was a misread `∨`; and step 3's cone is 30 modules, not 21

rows: `P3`

Formal detail is [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-31`. This entry is the root trace. **Gate:** ask
`python scripts/gate_status.py`, never a line here.

**This entry is opened BEFORE the first Lean edit** and is committed docs-only, per the
§11.12 rule-1 preamble as amended 2026-08-30b. Green anchor `c780597`, verified COVERED
first-hand. It is appended to as the session proceeds.

**1. The headline.** The board, `HANDOFF.md` and the task file all carried P3's next step
as "repoint the abbrev at `DerNode` **OR** `LeafNode`" — which reads as an unmade binary
decision, and is why the step kept being deferred as needing a call. **It is not a fork:
the target is the disjunction `DerNode ∨ LeafNode`**, said in those words in
`HANDOFF.md:113`, `PROOF_STATUS ## Session 2026-08-30d` §5, and the `ShadowOver` docstring
itself (`CascadeStable.lean:529-530`). And it *could not* be a fork — this tree already
proves the two predicates **incomparable** (`Scratch4cii.lean:256::
slSwD_classification_swap`, `by decide`), so neither alone can be the target. A settled
call was re-litigated for several sessions because prose spelled a `∨` as "or".

**2. Recon was delegated, and it paid for itself twice** — a four-agent read-only
`Workflow` fan-out (task file, scope doc §11.13, `PROOF_STATUS`, live Lean tree) writing
notes to `.scratch/p3-2026-08-31/`, then a synthesis pass that re-grepped every claim it
relied on. It found two things no session record carried: **(a)** step 3 edits
`ReconcileCorrect.lean`, whose reverse cone is **30 modules**, not the 21 the whole item is
sized on; **(b)** step 6 will make `Zanzibar.graph_correct` strictly weaker **without
turning its byte pin red**, because `headline_statements.txt:27` records the hypothesis by
name. (b) is the house failure mode and is a user call — see `PROOF_STATUS` §2(b).
⚠ Per the standing rule, the synthesis is *evidence, not a finding*: everything acted on
below was re-verified first-hand against the tree before it was written.

**3. Steps 3, 4 and 5 landed green.** `TtuTargetsSat` + an additive `_gen` chain (the three
audited names kept as one-line corollaries, so the `audited_theorems.txt:451` row and all 8
call sites never moved); `NoLeafSubjects` with a **two-layer** witness whose sabotage bit
**twice** (S12/S13 each `rc=1` naming a refutation witness while the positive pin stayed
green — which is exactly why two refutation witnesses were needed, not one); and the
pre-widen, with the abbrev **still unflipped**. Detail: `PROOF_STATUS ## Session 2026-08-31`
§3.

**4. 🚧 The pre-widen is PARTIAL, and that is the finding.** The plan said six of the eight
`¬ DerNode` obligations were free. **Three are.** The other three quantify over
`rewriteClosure S t`, whose subject predicate `rewriteStep` overwrites with a TTU target — so
it is not bare and `bare_subjNode_not_leafNode` does not apply. **5 obligations outstanding,
not 2**, three of them a pre-step-9 blocker the ten-step recipe never contained. No premise
was fabricated to close them; the bridge lemma was landed taking both as hypotheses.
✅ And half of what is missing already exists: `LeafRules.lean:106` defines
`schemaRewritesL = schemaRewrites ++ leafRewrites`, a **superset**, so
`NoLeafSubjects → TtuTargetsSat S NotLeafName` is a `List.mem_append_left`. (The implementer
concluded the opposite — "different rule lists" — and that was corrected here first-hand
against the definition, not averaged.) Only the *seed-side*
`NotLeafName t.subject.predicate` is genuinely unowned.

**5. Two board consequences.** New row **`P20`** — the `W4Fragment` narrowing that its own
byte pin cannot see — taken as a **user call: not accepted inside `P3`**, so it is adjudicated
on its own and blocks `P3` steps 6–10. `R6` demoted `NEXT → LATER` to seat it under the cap
of 3 (its item block was removed accordingly, and the ordering plus the "batch *through* the
N15 cache" rule were folded into its row so nothing was lost with the block). ⚠ I first
filed the new row as `P16`, **which already exists** ("widen the enumeration/state bounds") —
ids are never reused, and `task.py new` refused it. Renumbered to `P20`. `handoff_lint` then
caught that `P20` had no task file, which is the trial contract enforcing itself.

**6. Two new traps → scope doc §11.13.** **(i)** re-expressing a *pinned* definition in terms
of a new generic one moves a pin — `NoTtuTarget` **is** pinned at
`headline_definitions.txt:62`, and trap (f)'s "adding a hypothesis touches no pin" does not
cover it. **(j)** the three non-free sites above. Also: trap **(b)** was found to be *itself*
stale — every `Leaf.lean` line number above `:552` written before today is +58 out since
`50af00e`, so the trap that corrects a line number has a short half-life. **Cite
`file::symbol`.**

`task.py lint` → `task lint: clean (12 checks, 155 task file(s) parsed)`
read: board only

**Still owed:** the C1 spike (trace whether the `checkPublic` guard reaches `graph_correct`)
is **not** taken — user scoped this session to steps 3–5. Steps 6–10 stay blocked on `P20`
regardless. Next session's first edit is the bridge placement in §4.

---

## 2026-08-30d — the blind instrument is closed, and the red it predicted never came

rows: `P3`

Formal detail is [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-30d` §0–§5. This entry is the root trace. **Gate:** ask
`python scripts/gate_status.py`, never a line here.

**1. The headline.** The previous session declared one specific edit as "the NEXT
SESSION'S FIRST EDIT": delete `Scratch4cii.lean:51`, a local unguarded `leafNodeB` that
had been silently **shadowing** the guarded carrier step 1 added at `Leaf.lean:547`. The
child namespace wins every unqualified reference, so `clsB` and `termB` — and therefore
the whole P14 weakened battery stated over them — were measuring a *broader* proxy than
the carrier they exist to validate, in the unsafe direction. The recorded expectation was
"a diagnostic red confined to the file".

**It built green.** `rc=0`, `Build completed successfully (1089 jobs)`. Not one `by decide`
row and not one `#eval` row in the battery distinguishes the broad proxy from the narrow
carrier, so the shadowing corrupted no measurement and the P14 weak rows are valid as
taken. The prediction was wrong in the safe direction — which is the pleasant half of a
finding whose other half is that **the session could not tell that from a no-op edit.**

**2. A green is not a measurement, so the difference was made mechanical.** "The two
predicates agree everywhere I probe" and "my edit did not take effect" produce the same
`rc=0`; distinguishing them by reasoning is exactly the house failure mode. New positive
pin — not an `xfail`, not a docstring — `Scratch4cii.lean::leafNodeB_here_is_the_guarded_carrier`
asserts a conjunction whose two halves **disagree by construction** at
`LeafWitness.SwEmptyRel`, the pathological empty-relation-name schema: the second conjunct
is precisely the deleted proxy's sole test (`publicOfLeaf … = some ""`), the first is E3's
residual `leafPublic ≠ ""` guard that only the real carrier carries.

**Sabotaged before believed** ([`docs/sabotage-procedure.md`](../sabotage-procedure.md)):
re-add the proxy verbatim → `rc=1`, and that pin is the **only** error in the build. The
"only" is the load-bearing word. It establishes that this pin is the sole thing in the
file separating the two carriers, which is what upgrades §1's green from an absence of
evidence into a measurement. Proxy removed again: `rc=0`, 1089 jobs.

**3. Two docstrings had been falsified in silence** by step 1, by the same mechanism as
the shadow itself — nothing goes red when a comment stops being true. One claimed
`leafNodeB` "still has no `leafNodeB_correct` twin"; one claimed "no `LeafNode` definition
exists anywhere in this tree". Both were true when written; both are now false. Corrected
in place, each saying what it corrects and when, rather than overwritten.

**4. Citation hygiene, applied *before* the fact this time.** `bare_subject_not_leafNode`
exists in **both** `Leaf.lean:1180` and `Scratch4cii.lean`. Rather than record that in a
session note, the `⚠ cite `file::symbol`` warning was attached to the Scratch4cii twin's
own docstring — where the next reader of that name is actually standing.

**5. Two gate lint failures were earned and fixed, not worked around.** `verify.sh lean`
step 4f caught (a) `HANDOFF.md` at 266 lines against a 260 ceiling — the banner text this
very session added; trimmed rather than the ceiling raised, per the check's own advice,
and (b) this entry's absence. Both are the lint doing its job on the session that wrote
the offending lines.

**Still owed:** the re-point itself — instantiate the abbrev at `DerNode ∨ LeafNode` and
discharge the ~20 tier-1 sites. Trap **(h)** is closed, so **(g)** (`shadow_graphRec_agree`
needs operand declaredness, which `WF` does not model) is now the only one gating it.
**6. The re-point was scouted** (six read-only agents), and because `.scratch/` is
gitignored the durable half is **transcribed into** `PROOF_STATUS` `## Session 2026-08-30d`
§6 rather than left there — labelled as agent output, since none of it is kernel-confirmed
and no Lean edit was made from it. The useful idea is *make the flip a no-op before making
it* (anchor / generalise / pre-widen), which turns a ~19-goal simultaneous break into ten
green-stoppable steps. Two of my own briefing claims came back refuted, and I accept both:
the `fun _ => True` sabotage's "ten errors" is a **lower** bound on tree-wide work, not an
upper one (Lean never compiled the two files holding 14 of the 19 obligations, because
their dependency had errored); and the *lemma* names in this cone **are** identity-pinned
in `audited_theorems.txt` even though the predicate names are not — verified first-hand,
as a gate-safety claim should be.

**7. Steps 1 and 2 of that plan landed green**, each with its own control
(`PROOF_STATUS` §7). Step 1 anchors the four `Scratch4cii` declarations that genuinely
mean the *strong* shadow at `ShadowOver (DerNode …)`, so the flip cannot silently change
what they assert. That it was **mandatory** rather than tidy-up was verified first-hand:
`d_weak_holds` proves the weak mirror TRUE at byte-for-byte the fixture where
`strong_shadow_false_at_d_own_sigma0` asserts the strong shadow is FALSE — so under the
abbrev spelling that theorem would have flipped from true to *false* at step 9. A false
theorem, not a broken proof. Step 2 adds the schema-generic leaf-refutation toolkit to
`Leaf.lean`; the gap is real, since every pre-existing "bare subject is not a `LeafNode`"
fact is a `by decide` pin at a *fixed* schema. Its one falsifiable claim — that
`NotLeafName`'s two disjuncts are non-redundant — was sabotaged rather than asserted, and
came back rc=1 with `⊢ isLeafPred BARE = false` (BARE is dot-*carrying*, so dot-freeness
never covers it).

**Trial close-the-loop** (`CLAUDE.md`, the `tasks/` parallel-run contract):

```
task lint: clean (12 checks, 154 task file(s) parsed)
```
read: board + HANDOFF

Honest note on that second line, since the trial is measuring exactly this: the board
query genuinely replaced the *file* read for orientation — `task.py board` was the first
command of the session and it named the next action correctly. But it did not replace
`HANDOFF.md`, and could not have: the 35 KB `show P3` overflowed context, so the item
detail was read from `tasks/P3-*.md` directly, and the trap list, read-first list and exit
procedure were read from `HANDOFF.md` and the scope doc. So for this session the query was
**additive, not substitutive** — which is the outcome the trial exists to detect, and is
the failure mode the read-line was added to make visible rather than inferable.

**Still owed:** steps 3–10 of the re-point, and before step 7 a **spike** on
the top risk: three call sites pass `shadow_graphRec_agree` the arbitrary query's own
relation, and nobody has traced whether the guard that would fix them stops at
`graph_correct_w3d*` or reaches the byte-pinned `graph_correct`
(`headline_statements.txt:27`). If it reaches, the cost is a reviewed weakening of a
headline theorem — a user-visible scope change that must not be smuggled into this item.

---

## 2026-08-30c — the middle split too: the shadow is now generic, and "42 modules" was a mis-rooted census

rows: `P3`

Formal detail is [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-30c` §0–§6. This entry is the root trace. **Gate: all ten phases
re-run green on this tree** — `python scripts/gate_status.py` answers this, never a line
here.

**1. The headline: `P3`'s middle shrank, for the second day running.** The recorded plan
opened step 3 by widening `UntaintedShadow.classify` in place, going red until step 10 —
that is *why* the middle was un-splittable and why the §11.12 exit exists. The plan
conflates two separable things: making the shadow chain **able** to carry a wider extras
set, and **widening** it. Separating them costs one `abbrev`. `CascadeStable.lean` now has
`structure ShadowOver (P : NodeKey → Prop)` with `UntaintedShadow S σ σ0` an `abbrev` for
`ShadowOver (DerNode S) σ σ0`, and five shadow lemmas generalized over `{Extra}`. Because
`abbrev` is reducible, **every existing field access, anonymous constructor and signature
kept working untouched**: `lake build` green at 1089 jobs, in **three in-cone cycles
against a budget of ten**, with the 65 sites in `CascadeStrataSettle.lean` and the whole
`CascadeSettle`/`CascadeEnum`/`CascadeStrataEnum`/`CascadeStrataAssemble` chain never
going red. The widening is now a one-line re-instantiation instead of a re-proof.

**Why four sessions of costing missed it:** every census measured *how many sites mention
the symbol* (85–229, depending on the symbol list). None asked *how many depend on
`DerNode` specifically, rather than on "extras are terminal and off the probe target"* —
which is **17 `.classify` + 9 `.term`**. A sizing question asked in the wrong units cost
roughly two sessions.

**1b. And it was sabotaged before it was believed.** A refactor is not a check, but this
one makes a claim — that the widening is now a one-line re-instantiation — and that claim
is false if the chain stopped depending on the extras predicate at all. Instantiating the
abbrev at `fun _ => True` (run *after* committing the green prefix at `b42c52d`, per rule 6)
gives **`rc=1`, ten errors**, in both directions: `:800` is the `applyD` producer, whose
anonymous constructor collapses to `True.intro`; `:922`/`:923`/`:938` are
`shadow_graphRec_agree` and `:956` is `checkFn_eq_sem_w3d` — precisely the consumers that
will need `¬ LeafNode`. So the remaining work is real and sits where the plan says. Reverted,
green again at 1089 jobs. Two docstrings that were narrower than their now-generic theorems
were fixed in the same pass.

**2. The sizing dispute is SETTLED, and the recorded figure was a mis-rooted census.**
Reproduced first-hand, twice, independently: `CascadeStable`'s reverse import cone is
**20** (+root = 21), not 42. **41 is the reverse cone of `DirectCorrect` and of
`RulesWrite`**, and 41 is the *forward* cone of `CascadeStrataAssemble` — so the recorded
"42 modules" is a delegated census rooted at the wrong module, and the wall-clock half of
the 3-session estimate rested on a number 2× too large. The "~136 sites / 8 files" figure
was a raw two-symbol `grep -c` LINE count, correct at `d3c1226` and now stale (162/9 at
HEAD, a ~19% undercount — the same failure mode it was written to correct). Size this edit
with **three** numbers: 21 modules recompile, ~9 files / ~229 sites re-check, **~20 sites
in 3 files go genuinely red**.

⚠ **The durable lesson, and it should become a house rule: a site count is meaningless
without its symbol list and its counting unit.** The record and the census never disagreed
about the tree — they disagreed about what a "site" is, for four sessions, with neither
publishing its convention.

**3. A blind instrument, created by step 1's own session.** `Scratch4cii.lean:51` defines
a local unguarded `leafNodeB` that **shadows** the correctly-guarded carrier step 1 added
at `Leaf.lean:547`; the local one wins every unqualified reference in the file, including
`clsB` and `termB` — the definitions the whole P14 weakened battery is stated over. The
error runs in the unsafe direction (a broader proxy makes the weak disjunct easier, so
those rows can be green while the real widened `classify` fails). Reported by an agent,
then verified first-hand before being written down. **Not fixed here, deliberately** — its
expected outcome is a diagnostic red worth its own cycle, not a rider on a commit whose
headline is the genericization. It is the next session's first edit.

**4. `hql` lands on three pinned rows, not one** — measurement flag (3) settled, and the
answer moved. `docs/latent-gaps.md` excludes `headline_statements.txt:46`/`:56` as "staged
records over intermediate chains"; that reason is refuted by `FullScope.lean:78`
(`abbrev ReachedBy := ReachedByW3d2E`) and `:84` (`abbrev Drained`), both read first-hand,
which make `w3d2E_correct_applies` hypothesis-identical to `final_applies` — it is that
theorem with the fence deleted, not an intermediate chain. Consequence: their repair is
probably migration onto `checkPublic` (as `final_applies` was on 2026-08-28c), not the
`hql` binder. Structurally confirmed, not kernel-confirmed.

**5. Two corrections to earlier records.** (a) 2026-08-30b's "all four premises
discharged" for `rewriteClosureL_extras_leafNode_nonvacuous` is true but weaker than it
sounds: `hmd` is discharged **vacuously**, because `schemaRewrites SlV = []`
(`LeafRules.lean:609`), so no fixture exercises that branch of the induction. (b) The
worry about "a new hypothesis on an audited signature" is retired: none of
`shadow_graphRec_agree` / `checkFn_eq_sem_w3d` / `shadow_reach_agree` /
`reachedByW3d_shadow` is in `headline_statements.txt` or `headline_definitions.txt` — they
carry only **name** pins, so adding a hypothesis changes no pin file.

**6. What is still owed, and it is the real remaining cost.** The abbrev must be repointed
at `DerNode S k ∨ LeafNode S k` and ~20 tier-1 sites must discharge the new disjunct. One
of them has **no existing lemma**: `shadow_graphRec_agree` needs the probe relation to be
*declared*, and nothing in the model forces `computedRefs` names to be declared —
`Core/Schema.lean::WF` records only that declared names are dot-free. Python enforces it
(`_validate_ast_references`), so the repair is faithful new modelling, not a lookup.

**The §11.12 preamble, committed before the first Lean edit.** Green anchor **`5f48be2`**
(step 2's commit), verified COVERED first-hand by `python scripts/gate_status.py` at session
start — all ten phases green on `t2a:06de578e49ce` / `t2c:c4364193bede`, working tree clean.
Abort trigger fixed up front: 70% context consumed, or 10 red in-cone `lake build` cycles,
whichever comes first. Rule 3 is applied in its **amended** form (the 2026-08-30b correction
banner on the scope doc): this docs-only append is committed *first*, so the reset target
already contains the session's yield — which is exactly the failure that cost 105 lines on
2026-08-30b.

**Note the anchor moved, and that is rule 6 working.** The previous attempt anchored at
`d0310ed`; steps 1–2 landed and were committed in between, so this attempt risks only the
middle. Banking a green-stoppable prefix is not a partial cone under rule 5.

Still owed: the middle itself (steps 3→10) — this entry records only the preamble; the
session's findings are appended to it as the cone proceeds.

## 2026-08-30b — `P3`'s green prefix is COMPLETE: steps 1–2 landed, and the red middle is 3→10

rows: `P3`

Formal detail — the recon, the sabotage transcripts, the baseline measurements, the two
landed lemmas — is [`PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-30`, §0–§8, opened under scope-doc §11.12 rule 1 (green anchor
`d0310ed`, recorded before the first Lean edit). This entry is the root trace, the record
corrections, and the process failure. **Gate: all ten phases ran green after step 1; the
step-2 run was still going at write-back** — `python scripts/gate_status.py` answers this,
never a line here.

**1. The plan's shape changed, and that is the headline.** `P3` has been recorded as one
un-splittable block since `2026-08-28c`, and the board row said so. It is not. An 8-agent
read-only recon established that steps 1–2 — the `LeafNode` carrier and the unowned
superset-extras lemma — are purely ADDITIVE: they state new things about the pre-re-point
tree, take no hypothesis from the re-point, and change no existing declaration, so each can
be gated and committed on green. **Both then landed in this session, so the prefix is now
complete and everything left in `P3` is the middle.** That middle is **steps 3→10**: it
begins at the `UntaintedShadow.classify` weakening (`CascadeStable.lean:529`), which is
where the headline theorems start being kernel-`decide` FALSE, and ends when `hql` lands on
`graph_correct` (`FullScope.lean` / `headline_statements.txt:27`). This does not weaken
§11.12 — the middle is exactly as un-splittable as recorded. Its SHAPE changed: an item
that could previously only be attempted by a 3-session run had a prefix a bounded session
could bank, and a bounded session banked it.

**2. Step 1 landed, green, and it is committed-clean.** `Leaf.lean` gains `LeafNode` (Route
B's carrier for the `classify` disjunct), the Bool mirror `leafNodeB`, `leafNodeB_correct`
proving the mirror decides it, and the pins. The carrier is `publicOfLeaf`, never
`isLeafPred` — the E3 trap: `isLeafPred BARE = true`, so an `isLeafPred` carrier classifies
every bare-subject node as extra and kills `untaintedShadow_writeLeg`'s `hsubj` premise
everywhere. +107 lines in one file, zero deletions.

**3. A real hole, found by sabotage and closed with a fixture.** The E3 guard
`leafPublic p ≠ ""` was UNPINNED. Removing it from `leafNodeB` alone reddens
(`leafNodeB_correct` is live); removing it from **both** `LeafNode` and `leafNodeB`
consistently, with the destructuring arities adjusted so the weakening compiles for the
right reason, builds **fully green, `rc=0`** — both `by decide` pins and the correctness
theorem are blind, because the `LeafWitness.Sw` fixture declares no `""`-named relation and
no query over it can distinguish the two carriers. The residual was carried only by a
docstring. Closed per the procedure's durability ranking with a pathological fixture,
`LeafWitness.SwEmptyRel` (`""` declared derived on `"user"`), plus
`swEmptyRel_pol_bare` stating why it discriminates and
`swEmptyRel_bare_subject_not_leafNode` as the discriminator. Re-run under the sabotage
before being believed:

```
rc=1
error: ZanzibarProofs/GraphIndex/Leaf.lean:1228:74: Tactic `decide` proved that the proposition
  leafNodeB SwEmptyRel (subjNode { type := "user", name := "alice", predicate := BARE }) = false
is false
```

⚠ **The near-miss is the more useful half.** The first fixture declared `""` derived on
`"doc"`, and the sabotaged build stayed GREEN — `publicOfLeaf` keys on the SUBJECT's type
and the probe subject is `"user"`-typed, so the empty derived relation has to be declared
on `"user"` for the trap to fire at all. A discriminating pin that could not discriminate:
the exact failure the pin was written to prevent, reproduced one level up inside it. That
is three sessions running (`2026-08-28c`'s `graphModeAnswers`, `2026-08-28d`'s
`shadowB_correct`, now this) in which the INSTRUMENT was wrong in a way only an explicit
sabotage caught.

**4. Two corrections to the record, both from the step-2 design pass.**

* The §11.10 trap "the non-emptiness premise is `StoreValidRulesD`" **does not verify** for
  the superset-extras lemma. `StoreValidRulesD` constrains stored tuples; it says nothing
  about relation-name non-emptiness. The lemma needs an explicit
  `hne : ∀ dt R, isDerived S (dt, R) = true → R ≠ ""`, and the red-middle consumer must
  thread it.
* The same trap cites `rawWriteRels` at `:541`. It is `Leaf.lean:587` post-edit. Cite by
  `file::symbol` — this repo's own standing rule — and the line drift stops mattering.

**5. I destroyed the session's work with `git checkout --`, and it proves a live defect in
the §11.12 exit.** Restoring the tree after the verification sabotage, this session ran
`git checkout -- formal/lean/.../Leaf.lean` intending to undo the sabotage. Nothing was
committed, so it reverted to `HEAD` and discarded all 105 lines then written, not just the
sabotage; recovered from an out-of-tree file copy plus the authoring agent's context. The
durable lesson is not "be careful": §11.12 rule 3 promises `PROOF_STATUS.md` "survives the
reset", and **nothing uncommitted survives `git reset --hard`**. Knowing that in the
abstract — this session had written it down forty minutes earlier — did not prevent the
loss. The recommended amendment is in PROOF_STATUS §6: rule 3 should read "commit the
docs-only append first, then reset onto it", plus a new rule 6, *commit every
green-stoppable prefix before running a sabotage against it*. A dated correction banner
now sits at the top of the scope doc so a reader of §11.12 meets it there; the rules
themselves are §11's running record and are not retro-edited.

**6. `CLAUDE.md` said `ZANZIBAR_PY` was a prerequisite; it is an override.** `verify.sh`
stopped hardcoding the `avery` path under `ZT-P2-6` — `resolve_py` (`:297-320`) tries
`$HOME`- and `$CONDA_PREFIX`-derived candidates first and accepts one only if it imports
the project's deps. Evidence: all ten phases ran green today with the variable unset.
Fixed in place, and the genuine footgun put in its place: `lake`/`lean` are NOT on `PATH`,
they live in `~/.elan/bin` (`verify.sh:123` prepends it for you; a hand build does not).

**7. Step 2 landed too, and it is the lemma §11.11 recorded as owned by no slice.**
`LeafRules.lean::rewriteClosureL_extras_leafNode`, proved at the designed statement for a
general `t`, with no premise weakened:

```
∀ u ∈ rewriteClosureL S (rawWriteTuples S t),
  u ∈ rewriteClosure S t ∨ LeafNode S (objNode u.object u.relation)
```

— every tuple the leaf-routed closure produces is one the old rewrite closure already
produced, or its target is a `LeafNode`. +229 lines, purely additive, `lake build` green;
the workhorse is `::rewriteClosureAuxL_extras`, a lockstep equal-fuel induction over both
kernels. **Non-vacuity is PINNED with no hypotheses** —
`LeafRuleWitness::rewriteClosureL_extras_leafNode_nonvacuous` discharges all four premises
at `SlV`/`tlEditor` and derives the conclusion THROUGH the lemma, refuting the left
disjunct rather than deciding the conclusion directly. That was demanded, not optional: a
four-premise lemma whose premises never hold together is true and empty, the same shape as
`2026-08-28b`'s `graph_correct_public` vacuity warning. Two by-products worth their own
names: `LeafRuleWitness::slV_wf` had to be proved (**no `WF SlV` witness existed anywhere
importable**, which is why non-vacuity had never been cheap), and `::hne_of_keys_nonempty`
turns the undecidable `hne` of §4 into a `by decide` scan of `S.keys` — reusable by the
middle. Sabotage: drop the `LeafNode` disjunct → `rc=1`, type mismatch at
`LeafRules.lean:518`, red for the right reason. **No pre-existing `by decide` pin would
have caught it**; the non-vacuity theorem is now that reference.

**8. ⚠ Three measurement flags, logged and NOT adjudicated.** The prefix did not need the
cone's size, so none of these was chased; each is now a trap on the row, and the middle
must settle them before it is planned, not after.

* A live import-BFS census measured **24 modules / 125 code sites / 13 files**, second ring
  **36 raw / 27 code** — against the record's **42 / ~136 / 8** and **90 / 50**. No measured
  set reproduced the recorded figures. **The 3-session sizing rests on those figures, so it
  is now unverified in both directions**: do not re-cite either set as fact.
* `FoldAdmits`: 19 Prop + 2 exec gates move, 3 stay — but the second exec gate is
  `Exec.lean:443`, not the scope doc's `:376`.
* `hql` may land on more than one pinned row. `headline_statements.txt:46`
  (`W4WitnessDirect.correct_applies`) and `:56` (`::w3d2E_correct_applies`) carry the
  identical unfenced shape and are excluded from the "one row" count only as "staged records
  over intermediate chains". Step 7 discovers this the hard way if nobody checks first.

**Still owed:** nothing. Step 3 — `UntaintedShadow.classify` gains `∨ LeafNode S ab.2`, the
first red edit — is the next session's opening move, and it is on the row.

`python scripts/task.py lint` → `task lint: clean (12 checks, 154 task file(s) parsed)`
read: board + HANDOFF

⚠ **This line was wrong when first written, and the correction is the point.** The
write-back agent recorded `read: HANDOFF only`, inferring it from the session's records
rather than from what the session did; corrected here by the session itself. What actually
happened: `python scripts/task.py board` was the FIRST command run, `show P3` the second,
and `HANDOFF.md` was opened only afterwards and only for the §11.12 exit plan the board row
points at but does not carry. So the query did replace the file read as the entry point,
and the file read that followed was a pointer-chase, not a re-read.

The trial's whole measurement is this line, which makes it the one line in the entry a
subagent must never infer: the agent could see which files the session had *touched*, but
not the order or the purpose, and those are exactly what the line asks about. Delegating
the write-back is fine; delegating the self-report is not. Recorded so week two's reading
of the read-lines knows one of them was very nearly synthetic.

## 2026-08-30 — trial window extended to 2026-09-06, delete off the table; and the banner was printing `⏰`

rows: `TT-1`, `TT-2`

**User decision, recorded first because everything below follows from it:** the trial runs
in parallel for another week, to **2026-09-06**, and `tasks/` is **not** being deleted. The
open question narrows from keep-or-delete to **cutover-or-keep-both**. Phase B still needs
an explicit go; it was not started.

**1. Where the window was written down, and how each site was treated.** `2026-08-30`
appeared in five tracked places. `CLAUDE.md` and `docs/tasktool-spec.md` are LIVING and
were edited in place. `docs/tasktool-trial-protocol.md` and `docs/tasktool-trial-stub.md`
are ACTIVE-PLAN, so they got dated correction banners and their bodies were left alone —
including §6's "the 2026-08-30 verdict", which was true when written. `TK52`'s closed task
file was left entirely alone. The protocol's own `2026-08-24c` finding — that the deadline
governing both systems was tracked by neither — is now half-answered: the *extension* is on
the tree (`TT-1`, `TT-2`) as well as in prose.

**2. A defect in the session-start read, found by looking at it rather than by a test.**
Asked whether the board is yet as good as `HANDOFF.md` at first run, I rendered it and the
banner opened with a literal escape:

```
⏰ `TK53`: 15 appends remain. Until they land, deleting `tasks/` loses statements.
```

`ASCII_FOLD` was censused out of task **titles and bodies**; `tasks/BANNER.md` did not
exist when that census ran, and it is the one input to this view that is free-form prose
rewritten every session in the house banner style — which uses 🟢 and ⏰, neither mapped.
The escape fallback is right for a title (lossy but honest, written once by someone who
sees the result) and wrong at the very top of the session-start view, where a reader
cannot tell noise from content and nothing complains.

Both glyphs are now mapped, and the **gap** was made mechanical rather than the instance
fixed: lint check 12 gained a fourth clause refusing any banner character `ascii_safe`
would escape, scoped to the banner alone (making it fatal everywhere would redden 153 task
files nobody is editing, and the fold exists so those render). ⚠ Note this class is
invisible to `test_board_ascii_under_cp1252`, which proves the output **is** ASCII — and
`⏰` is ASCII. A check can be green and blind to the thing beside it.

**3. A sabotage that silently did nothing, caught only because its result was implausible.**
The first attempt to redden the new check reported `1 passed` with the check supposedly
disabled. The correct reading of that is "my test guards nothing"; the true cause was that
the patch never applied — the string replacement matched nothing and I had not asserted
otherwise. Re-run with the patch verified before the test (`found at`, `ORIGINAL LINE:`,
`SABOTAGE APPLIED` printed), it reddens properly:

```
E       AssertionError: task lint: clean (12 checks, 7 task file(s) parsed)
E       assert 0 == 1
FAILED tests/test_tasktool.py::test_the_banner_may_not_carry_a_glyph_the_board_cannot_render
```

**Assert that the sabotage APPLIED before believing what the test says about it** — a
no-op patch and a worthless test produce the identical green, and the green is the one
this repo is built to distrust. `docs/sabotage-procedure.md` already says to control your
instrument; this is that rule one level down, on the instrument's instrument.

**4. `TT-2` filed: `sync` is the one surface with no gated coverage.** Phase A skipped
`sync_sabotage.py` (14 cases) and `sync_accept.py` (57 assertions) on the explicit ground
that `sync` retires at cutover. **The extension expired that ground** — `sync` is in live
use for another week and the cutover may not come. Filing it was itself a small piece of
evidence for the trial: `new --pri NEXT` was **refused** at write time (`NEXT would have 4
rows, budget 3`), so it went in as LATER. Re-ranking the board is the user's call, not a
side effect of filing.

**5. My own banner tripped `BANNER_MAX_LINES`** on the first rewrite (16 lines, cap 14).
Recorded because the author of a cap being caught by it the same week is the cheapest
possible evidence that it is not decorative.

`min_tasks_parsed` 153 → 154; `MIN_TESTS_ALL` 1035 → 1036, instrument-checked at 1037:
`FAIL: tests/ collects only 1036 test(s); the gate floor is 1037.`

**Still owed:** nothing. `TT-1` (Phase B) and `TT-2` (the `sync` port) are filed, not owed.

`python scripts/task.py lint` → `task lint: clean (12 checks, 154 task file(s) parsed)`
read: board + HANDOFF

## 2026-08-29e — doc sweep after Phase A: five "465" floors, a fifth "~25 lines", and a second symbol that never existed

rows: `TT-1`, `ZT-P5`

Continuation of `2026-08-29d` (same working session; separate key because that entry was
written before this work and entries are never retro-edited). A census of tracked docs for
staleness introduced or exposed by `379dd60`. **Most of what it found was older than that
commit** — Phase A's real contribution here was making it visible.

**1. `docs/gate-runbook.md` carried `MIN_CONF_ALL` = 465 in five places; live is 495.**
Also `MIN_CONF_HEAVY` = 96 and `MIN_CONF_REST` = 369 against a live 104 / 391 — three
wrong numbers in one sentence, and a session copying it into a `conf-heavy` sanity check
would have set a floor 8 tests low. This is the exact sin `CLAUDE.md` names *this file*
for ("carried a wrong value for three weeks by doing so"), and the doc's own warning box
documents it. **Fixed by deleting the figures, not by updating them** — the identity
`MIN_CONF_HEAVY + MIN_CONF_REST == MIN_CONF_ALL` is asserted by `verify.sh` at startup, so
prose restating any of the three buys nothing it cannot lose.

**2. The fifth "~25 lines" claim.** `2026-08-29d` reported fixing four; there were five.
`docs/tasktool-trial-stub.md` — the draft of the very stub Phase B will land — still
described a board with no banner and no `brief`, and additionally listed **9 of the 12**
lint checks as if that were the contract, omitting the corpus floor, the depth warning and
`check_banner`. A partial contract is worse than none: a reader treats it as complete, and
this one would have left them not knowing `tasks/BANNER.md` is required.

⚠ **That file is GENERATED (`migrate.py::handoff_stub`) and the generator was not
updated**, because `migrate.py` must not be run at all. Recorded in the file's own
correction banner as a live divergence rather than left implicit. It also had **five**
broken relative links (`docs/CLAUDE.md`, `docs/docs/README.md`, …) that
`check_doc_links` has never seen, because the file is not in `handoff_lint.py::LINKED_DOCS`.

**3. A second cite of a symbol that never existed.** `tasks/ZT-P5-*.md` cited
`handoff_lint.py::check_ledger_ids` — the same non-existent symbol fixed at `HANDOFF.md:78`
in `2026-08-29d`, in the same session, in a different tree. Both are now
`check_ledger_row_ids`. Two independent copies of one wrong name is the argument for the
`file::symbol`-must-grep rule, not an anecdote about it.

**4. `docs/tasktool-spec.md` §7 said the schema "has not been widened to thirteen"** while
§3.1 of the same file said fifteen. Rewritten to stop stating a count at all and to point
at §3.1, with a note that the gap between `migrate.py`'s schema and the live one only ever
widens — which is one more reason not to run it.

**Deliberately NOT touched:** `docs/tasktool-trial-protocol.md`'s dated §6 observations
(append-only; its A7 items already carry the `2026-08-29d` resolution table), every
pre-`2026-08-29d` ledger entry, the literal sabotage transcripts quoted in
`scripts/task.py` docstrings, and `docs/spec-deviations.md`. Those are as-of-then
provenance and a "fix" would destroy the record.

`HANDOFF.md` gained a `tasks/README.md` + `docs/tasktool-spec.md` row in *Where things
live*; the line was paid for by reflowing the `B1`/`BL-2` paragraph, not by raising the
ceiling. The `Closed ids` lines at `:71-72` were not touched — reflowing those is the trap
three lines below them.

`docs/tree-sole-authority-spec-2026-08-29.md` now carries a dated **PHASE A IS LANDED**
banner naming where execution differed from the plan, so no session re-runs A1.

**Still owed:** nothing.

`python scripts/task.py lint` → `task lint: clean (12 checks, 153 task file(s) parsed)`
read: board + HANDOFF

## 2026-08-29d — Phase A landed: the task tool's suite is in the gate, and its six footguns are fixed

rows: `TK53`, `P3`, `P6`, `R6`, `TT-1`

Execution of Phase A of [`tree-sole-authority-spec-2026-08-29.md`](../tree-sole-authority-spec-2026-08-29.md).
Phase A is additive and safe under **every** trial outcome — even a DELETE verdict wants
the test rescue landed first. **Question (a) is still the user's call and is still not
made here**; Phase B (the cutover) is filed as `TT-1` and needs an explicit go.

**1. A1 — the suite is out of `.scratch/` and into the gate.** `tests/test_tasktool.py`,
**84 tests**, 72 s wall: 40 ported cases, 13 new, **30 sabotage cases converted from the
`--sabotage` self-runner into permanent tests** (22 fixture + 4 write-path + 4
live-corpus), and one record-completeness pin that counts the 22/4/4 so deleting a
sabotage case is red rather than free. No marks, no skips, no xfails. The live-corpus
pass was repointed from the gitignored `sandbox-migrated` onto the **tracked** `tasks/`,
copied into tmp; a missing corpus fails rather than skips, as it did before.

`MIN_TESTS_ALL` **943 → 1035**, re-measured with `--collect-only` and instrument-checked
at 1036, which failed literally as:

```
FAIL: tests/ collects only 1035 test(s); the gate floor is 1036.
```

The PROOF4/`sabotage-log.txt` record is transcribed into
[`tasktool-proof-2026-08.md`](tasktool-proof-2026-08.md) (FROZEN), carrying the `22/22`
and `4/4` results and the three instrument controls, with an explicit ⚠ against re-citing
its `40 test(s)` / `11 checks` figures as current.

**One thing did NOT get rescued, and it is a real gap.** `sync_sabotage.py` (14 cases) and
`sync_accept.py` (57 assertions) stayed in scratch, on the grounds that `sync` retires at
the Phase-B cutover. **If the cutover does not happen, that gap is live** — recorded in
the proof doc and in `TT-1`'s traps, not left as a silent omission. One ported case,
`test_migrate_schema14_refusal_is_a_message_not_a_traceback`, has no subject in this tree
(its script was never tracked); its literal red transcript is in the module docstring.

**2. A2 — the six A7 footguns, each fixed and sabotaged.** Resolution table appended to
[`tasktool-trial-protocol.md`](../tasktool-trial-protocol.md) §6; the friction list itself
is left **unedited**, because the friction as first found is the evidence.

* `ack` **refuses** any source but `board`. The old fall-through printed "acked", bumped
  `updated`, wrote a Log entry recording that the drift was reviewed — and stamped
  nothing, so the next `sync` reported the identical drift and the session that "handled"
  it had a log entry proving it did. The refusal branches: if the task **has** a board row
  it names the re-file remedy (`source` is immutable by design), otherwise it names
  `comment`, which is what the fall-through was actually doing minus the false word.
* `ack --since DIGEST` encodes *"`ack` must be a session's last step"*: pass what the
  drift report showed and a source that moved since is announced on stderr. It **warns**
  rather than refuses — the mover is usually the acking session's own edit — and the rule
  is stated in `tasks/README.md` and the spec.
* `new --id ID`, validated against live + retired ids. Proved on real work: `TT-1` was
  filed with it, instead of being minted into the `TK` **findings** series.
* `set --title x` now refuses with the working positional command line; `field`/`value`
  became `nargs='?'` so the refusal is reachable at all (argparse used to kill it first).
  `new --help` prints the 100-char cap.
* **Footgun 5 was already fixed.** `list` announces `showing 20 of 58 (--limit 0 for all,
  --limit N for N)` on every path including `--parent`, and `ready` / `--json` have no cap
  at all. It needed a pin, not a change — re-verified by measurement, not by reading.
  ⚠ Its **other** half is NOT fixed and is not scheduled: `list --parent R6` still
  includes children whose ids are not `R6-N`, because they genuinely are `R6`'s children
  and filtering by id prefix would make `list` lie about the parent graph to flatter a
  naming convention. Anyone re-counting `R6-N` sub-items must filter, and say they did.

**3. A3 — `brief`, the banner, and a board size that is asserted instead of described.**
`brief` is the 15th field, sitting under `title` because it is the second thing read.
One shared `brief_problem` backs `set`, `new`, lint check 4 and `validate_record`, so a
write op cannot refuse a record lint calls green. 152 files migrated; **round-trip
153/153 byte-identical** afterwards. The four current NOW/NEXT rows were hand-populated
from their board annotations, `--mechanical` — populating a field is not progress, and
bumping `moved` on `P3` would have laundered a stale NOW row.

`tasks/BANNER.md` is the single must-read thing: `board` **refuses** without it and
refuses one over 14 lines, and new **lint check 12** catches missing / over-long / a first
line with no session key. A default banner was rejected outright — it is a session-start
that looks complete and carries nothing.

The board now renders at **39 lines** against a new `BOARD_MAX_LINES = 50`, asserted by
`test_board_stays_under_its_size_ceiling` on a full-budget corpus. This replaces **four**
prose claims of "~25 lines" written before the view grew a banner and a `brief` per row.
Two more stale counts fell out of the same sweep: `render_file`'s docstring said
"Thirteen keys" while `FIELDS` held fourteen, and two live messages said "fourteen". All
three now interpolate `len(FIELDS)` or name `FIELDS` — the number is spelled out in
exactly one place, the spec's field table.

**4. A4 — rehoming, and a parity check that came back clean.** `tasks/README.md` carries
the preamble, the reading protocol, the rules the tool cannot enforce, and the mechanical
answer to the `ls tasks/` trap. `handoff_lint.py::check_ledger_row_ids` auto-detects the
task tree, unions its ids, and **fails when a board row has no task file** — the
dual-update contract from `CLAUDE.md` made mechanical rather than remembered. Auto-detect
rather than a flag, because the behaviour wanted is the same in all three states (board
only / both / tree only after a cutover). **It reports clean, so the week's dual-update
contract actually held.** `BANNER.md`/`README.md` are excluded from both scanners by name,
top level only — `closed/` is deliberately not exempt.

`HANDOFF.md:78`'s stale `check_ledger_ids` cite → `check_ledger_row_ids`, net-zero lines
(the file is at exactly its 260 ceiling).

**5. Two findings from sabotaging my own work, both of which changed something.**

* **The parity check's first version reported `'---'` and `'id'` as missing task files** —
  `_table_rows` yields the header row and the `|---|---|` separator, which was harmless
  while that set only fed a non-vacuity floor and stopped being harmless the moment it fed
  a comparison. Filtered through `_ROW_ID`; the literal pre-fix text is in the guarding
  test's docstring.
* **A guard was real and its stated reason was false.** The tree floor shipped carrying
  the standard `MIN_DOC_LINKS` justification, *"the harvester is broken, so this check
  would pass by comparing against nothing"*. Deleting it and probing **three** corpora
  showed that while both trees exist the parity comparison goes loud on its own; the floor
  buys a precise diagnosis and an early return, and the failure it is named for is real
  only **after** the cutover, when the board is a stub. The floor stayed — that state is
  what the work is trying to reach — but the comment and the message were rewritten to say
  which half is which. Filed as a method lesson in
  [`sabotage-procedure.md`](../sabotage-procedure.md): *a justification is an assurance
  claim and gets sabotaged like one*, and *probe more than one corpus, chosen to differ in
  what else is watching*.

**6. A process mistake, recorded because the next session will be tempted the same way.**
I probed the new `ack` refusal against the **live** corpus twice before switching to a
throwaway copy. `P3` is board-sourced, so it did not refuse — it wrote a real Log entry
saying `test` and then `probe`. Both are reverted and `P3`'s entry now says what actually
happened. A write op is not a read op; probe it against `--dir <copy>`.

`min_tasks_parsed` **150 → 153** (two files of growth had re-accumulated, plus `TT-1`),
with the provenance note extended in `tasks/config.json`.

**Still owed:** nothing. Phase B is not owed — it is gated on an explicit user go and is
filed as `TT-1`.

`python scripts/task.py lint` → `task lint: clean (12 checks, 153 task file(s) parsed)`
read: board + HANDOFF

## 2026-08-29c — `TK53`: 22 appends landed; re-verification overturned rows in BOTH directions

rows: `TK53`, `R6`, `HS-5`

Continuation of `2026-08-29b` (same working session; separate key because that entry was
written before this work and entries are never retro-edited). **Question (a) remains the
user's call and is still not made.**

**1. What landed, in five commits, each gated green.**
* `docs/latent-gaps.md` — four bullets in *"Latent, but owned by another doc"* (`TK8`,
  `TK9`, `TK10`, `TK13`), the section whose stated job is to be a complete index of what is
  open and which was missing them.
* `docs/architecture/decision-log.md` — `TK2`, `TK40`, `TK41`, `TK42`, including a new
  *"Reads are lenient"* section.
* `docs/architecture/correctness.md` — `TK5`, `TK37`.
* `docs/perf-round6-audit-2026-08.md` — one consolidated appendix subsection carrying ten
  cross-links and corrections (`TK19`–`TK32`), landed beside the verbatim leads rather than
  inside them.
* `docs/README.md` §3 (`TK45`), plus `TK7` into the Lean docstring that already carries the
  residual it corrects.

**2. ⚠ Verification overturned findings in BOTH directions, which is the session's real
result.** Every row was re-verified against the live tree before it was written, as the
adjudication's own trap requires. That was not ceremony:
* **Four rows marked `APPEND` were already carried** and were closed instead (`TK17`,
  `TK23`, `TK24`, `TK27`) — the increment sits verbatim in the appendix lead's own fix
  sketch.
* **`TK41`'s destination did not exist.** The adjudication said "append to the existing
  lenient-reads material" in `decision-log.md`; there is none. The file's only *lenient* is
  `lenient ∀⇒∃`, the wildcard vacuity mode — a different sense, and the anchor `TK4`
  targets. Landing there would have fused two unrelated concepts under one word.
* **`TK13` and `TK10` shrank**; their homes already carried more than the findings claimed.
* **`TK45` was half stale**, like `TK51` before it.
* ⚠ **And `TK27` shows the adversarial pass failing the other way**: it *refuted* a correct
  write-off by misreading a fix sketch. So `2026-08-29b`'s "6 of 11 overturned" measures
  **disagreement, not correctness** — the pass catches wrong write-offs and can also
  manufacture wrong appends. A dated correction is appended to the (FROZEN) adjudication
  file. **Neither pass substitutes for opening the file.**

**3. A near-miss worth recording, because it is the house failure mode in miniature.**
While checking `TK45` I read `handoff_lint.py:216`'s *"explicit list rather than a glob"* as
proof the frozen-banner check was list-based and therefore went stale. That comment belongs
to `check_doc_links`, a **different check**; `::check_frozen_banners` globs every `.md`
under the history dirs and its docstring explicitly refuses a filename list. Reading it the
first way would have written a false statement into a living doc *and* closed a finding on
a fabricated ground. The surviving residual is narrower and is what got recorded: design
docs outside a history dir are walked by nothing, and a stale *description* (as opposed to
a broken link) is not enforceable at all.

**4. Sharpest thing found.** Appendix lead `A15`'s fix sketch is **backwards about the
gate**: it reasons that CORRESPONDENCE anchors "still resolve since the public functions
keep their names", but the anchors are on the **nested closures** an AOT rewrite would
delete (`SetEngine.check.sat_expr`, `SetEngine.expand.do_expr`), and `anchor_check.py`
walks nested bodies with a dotted prefix. `R6-1`'s and `R6-2`'s Lean notes already
enumerate them; nothing connected that to `A15`. Runner-up: `A3` and `A14` both key
invalidation on `ResidueV1.version`, the token this same document already refutes for
`R6-4(a)`.

**5. What remains.** Fifteen appends, tracked on `TK53`, listed in the adjudication table.
`TK53` stays `NEXT`: until it closes, deleting `tasks/` still drops statements no living
doc carries.

`python scripts/task.py lint` → `task lint: clean (11 checks, 152 task file(s) parsed)`

`read: board + HANDOFF` — unchanged from `2026-08-29b`, and the same caveat applies:
orientation was `board` only, and `HANDOFF.md` was opened to write to it.

**Still owed:** nothing. The fifteen remaining appends are queued work on `TK53`, not a
skipped write-back step.

---

## 2026-08-29b — trial question (b) DECIDED: every `TK*` id bucketed, 3 discharged, appends carried by `TK53`

rows: `TK52` (closed), `TK53` (new), `HS-5`, `R6`

**No formal work.** `TK52`'s deliverable — the adjudication, not the snapshot — is
delivered: [`tk-findings-adjudication-2026-08-29.md`](tk-findings-adjudication-2026-08-29.md)
puts **every** open `TK*` id in exactly one bucket. ⚠ **Question (a) is deliberately NOT
decided.** Deleting `tasks/` and `scripts/task.py` is the user's call; the recommendation
is at the bottom of this entry.

**1. Method, and the number that justifies it.** A nine-way fan-out adjudicated each
finding against the live tree, distinguishing a carrier that holds the *subject* from one
that holds the *finding* (i.e. tells a reader work is outstanding). Every proposed
write-off then went to an independent agent told to **refute** it. **That pass overturned
6 of 11** (`TK5`, `TK7`, `TK15`, `TK23`, `TK24`, `TK27`). A single-pass adjudication would
have written off six findings with no living carrier — on the one verdict that is
unrecoverable once the tree is gone.

**2. Three discharged, all verified first-hand, and two were not what they were filed as.**
* `TK48` — the perf-audit banner is **fixed**. Counted from the body: **eleven**
  `MOTIVATED` rows and **four** `NOT MOTIVATED` (11+4+3 unreachable = its own "ALL
  EIGHTEEN"), against a banner claiming *"ten … five"*. Its second clause *"Nothing here is
  landed"* was false twice over (`R6-10`, `R6-6`). Per the finding's own trap the new
  banner **carries no count** and points at the tables. ⚠ **Instrument control:**
  `grep -c "NOT MOTIVATED"` returns **5** and is WRONG — `:90` is prose, not a verdict row.
  I ran that grep first and would have written the wrong figure from it.
* `TK51` — **stale, not written off.** The dense-regime pass it asks for **is implemented**:
  `tests/test_generator_coverage.py:881` runs `_sweep(G.DENSE, DENSE_SUBSETS)` beside the
  sparse sweep at `:805`, with the sabotage assertion at `:995-998`. "Stale" and "written
  off" are different dispositions and the record now says which.
* `TK49` — its scope correction **landed** into `docs/README.md` §2.

**3. ⚠ The board was pointing into the tree.** `HS-5` read *"count is method-sensitive, it
lives in `TK49`, not here"* — the **control arm delegating its own substance, by id, to the
arm that may be deleted tomorrow**. A dangling referent either way: DELETE breaks it, KEEP
leaves the board unable to state its own scope. The enumeration and the measuring method
now live in `docs/README.md` §2 and the row points there. This is `CLAUDE.md`'s *"a trap
must cite a symbol that EXISTS"* one level up — it applies to board rows citing task ids,
and nothing checks it.

**4. The count is method-sensitive, again, and neither doc carries one.** Re-measured
2026-08-29b by a stated method (a bolded `LIVING`/`FROZEN`/`ACTIVE-PLAN` inside the first 8
lines): the list in §2. It has read **six, then nine, then eleven, then this** across four
readings — not because docs changed but because each used a different candidate set and a
different test. §2 records the method beside the list and refuses a number; so does `HS-5`.

**5. The appends are DECIDED, not LANDED, and that is a tracked row.** The remainder each
have a named destination in a living doc. They are carried by **`TK53`**, filed before the
adjudication file was written — a decision recorded with no open carrier is precisely the
defect `TK11` exists to name (a residual declared at closure, never re-filed). `TK53` is
what makes DELETE lossless; until it closes, DELETE still drops statements.

**Recommendation on question (a), for the user to decide.** The directed 18-agent
experiment is a real but narrow win: TREE at **88.7%/88.8%** of BOARD tokens, Mann–Whitney
`U=0` as pre-registered — but on a total carrying a large fixed prompt floor, and at **3–5
tool calls against the board's 1**. Against that: §4 pre-registers **M3** as *"the metric
the whole trial turns on"* — *if the TREE arm keeps opening `HANDOFF.md` anyway, nothing
was saved* — and M3 was **never obtained** (pilot instrument failure). The only natural-use
substitute is the read tally, which is **self-reported**, the instrument §2 disqualifies by
name; it shows most sessions read both. The board also **won** the one cross-item question
(`S5`) structurally, by being one file. And the maintenance contract went RED with the tree
the stale side, skipped by four consecutive sessions — a cost §6 says no session ever
recorded. §7.4's pre-registered rule sinks the tree only on *quality loss at higher cost*,
which did not happen, so the rule does **not** compel deletion; it also does not compel
keeping. **My recommendation is DELETE the tool and KEEP two things it proved:** the
mechanical `lint`/`sync` refusals, which the board has no analogue for and which caught
real drift, and the `related` cross-links, which is the mechanism `F1` identified. Land
`TK53` first — that is what makes the deletion lossless.

`python scripts/task.py lint` → `task lint: clean (11 checks, 152 task file(s) parsed)`

`read: board + HANDOFF` — but the two reads were not equivalent and the tally should not
score them as one. **Orientation was `board` only**: `task.py board`, then `show TK52` and
`show P3`, and work started from those. `HANDOFF.md` was opened later and in full, to
**write** to it (three row edits, an item block, the banner). Declared the conservative way
rather than as `board only`, because the 260 lines were read either way and M3 asks what
was opened, not why.

**Still owed:** nothing. `TK53` is queued work, not a skipped write-back step.

---

## 2026-08-29 — trial verdict filed on both trees, 47 findings rescued; `sync` was RED and the TREE was the stale side

rows: `TK52` (new), `R6`, `P3`

**No formal work. This session made the 2026-08-30 verdict decidable and did not decide
it** — the call is the user's, and the irreversible half was deliberately left open.

**1. The findings are rescued, so DELETE is no longer destructive.** All 47 open `TK*`
findings are snapshotted in
[`docs/history/tasktool-findings-2026-08-29.md`](tasktool-findings-2026-08-29.md) (FROZEN,
47 entries, one per id, citations copied verbatim and explicitly *not* re-verified). The
trial's exit plan — *"delete `tasks/`, `scripts/task.py` and this bullet, which is one
revert"* — bundled two separable decisions; the snapshot unbundles them so question (a),
*does the query beat the file*, can be judged on its merits. ⚠ **This is safe-to-delete,
not decided-what-to-keep**; that adjudication is `TK52`'s deliverable.

**2. The verdict is now a tracked item on both trees** (`TK52`: board row + task file,
same session key), discharging the `Still owed` line carried since 2026-08-24c and closing
the protocol's own finding that *"the one deadline that governs both systems is tracked by
neither"*. It stood five days.

**3. ⚠ The parallel-update contract was RED, and the tree was the stale side.**
`task.py sync` reported **2 drift items** on arrival. `R6` was a real content divergence,
not a digest one: the task title and its `As built` census still read **"11 to land" / 11
`LATER` / 5 closed** — generated 2026-08-21 and never re-counted after `R6-6` closed
2026-08-24d — while `HANDOFF.md` had said **"10 to land"** since that day. Re-counted live
(`list --parent R6 --limit 0`, `R6-N` children only): **10 `LATER`, 3 `HOLD`, 6 closed**;
the board was right the whole time. `P3` was digest-only (four `2026-08-28*` sessions
rewrote the row without re-stamping; body content current). Both acked, `sync` now
**CLEAN**. This is the summary-row-contradicting-its-own-child defect (trial `P4`, then
`HS-5`/`TK49`) recurring a **third** time — inside the tree, on the row whose
self-recounting was cited as the tree's win.

**4. Two corrections to figures the verdict turns on.** The census is **`TK1`–`TK51`, 51
ids, no gaps — 47 open, 4 closed**, superseding 2026-08-24c's *"49 open, 2 closed"* by
exactly `TK46`/`TK47`, closed hours after it was written. And *"outside `tasks/`, exactly
one `TK` id is mentioned anywhere in this repo"* is **now false**: 34 of the 47 appear
nowhere outside `tasks/`, 12 appear only as narrative in the session log and the protocol,
and exactly 1 (`TK49`) is on the board. The board-only reading survives; the
no-other-file reading does not.

**Method note.** A subagent fan-out did the bulk reading (47 task files, the protocol, the
cross-reference sweep). Every load-bearing claim above was then re-verified first-hand
before it was written into a tracked file — the `sync` output, the `R6` child re-count,
the read tally, the census, and the `2026-08-30` grep. One agent-reported framing was
wrong and was corrected: an early `ls tasks/` of mine missed `tasks/closed/`, which made
the protocol's census look wrong in both directions; it was right when written.

⚠ **`TK52` was filed twice.** The first `new` took `--source hand`, which left `sync`
permanently unable to stamp its digest — a row that reports drift forever is a red
instrument people learn to ignore. The uncommitted file was removed and re-filed with
`--source board`, which takes the id from the row; it minted `TK52` again, so no id was
burned.

**5. Friction log, at the user's request.** §§1–7 measured *reading* cost and never
measured the cost of *operating* the tool — the recurring price if it graduates. Six
observed items are now protocol §6 `A7`, the sharpest being that **`ack` on a
`--source hand` task prints a success line and exits 0 while stamping nothing**, so `sync`
reports that task as drift forever: an assurance step that fails by passing, inside the
tool built to prevent drift. Also recorded: `ls tasks/` silently undercounts because
closed tasks live in `tasks/closed/` — the near-miss that nearly put a false finding in
this entry.

Full evidence, including what remains unmeasured: `docs/tasktool-trial-protocol.md` §6,
append `2026-08-29`, written **before** the `R6` repair so the divergence survives it.

`task lint: clean (11 checks, 151 task file(s) parsed)`
`read: board + HANDOFF`

**Still owed:** the verdict itself (`TK52`) — both questions, by 2026-08-30. Nothing else;
`P3`'s cone was deliberately not opened, since it is un-splittable and has no green
intermediate state.

---

## 2026-08-28d — `P14` settled: `classify` is the only failing field, and the old refutation used the wrong σ0

rows: `P3`

User asked to work the board with subagents for context economy, then gate and commit.
Formal detail (the authority for this entry):
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-28d`. The 4c-ii cone was **not** opened — un-splittable, sized at 3
sessions, and this was not a fresh window.

* **`P14`'s `UntaintedShadow` adjudication is settled, and it moved the answer.** A new
  six-field battery in `Scratch4cii.lean` (additive, zero-cone, still 1 importer / 0 audit
  / 0 pin rows) finds that **`classify` is the only field that ever fails**, and only
  unweakened — so Route B's weakening is one disjunct on one field, not "weaken
  `UntaintedShadow`". `term` holds in its leaf-extended form, so clause 3 costs nothing.
* **A risk was retired by measurement, not argument.** `nodesSub`, `closed` and `closed0`
  had never been probed here — the whole 2026-08-20 battery is edge-only. They hold on
  both chains, at both leaf indices, and on a mixed store, so **4c-ii owes no
  endpoint-closure edit to `LeafRules.lean::writeRulesRaw`**.
* ⚠ **The recorded refutation was an instrument artifact.** `slSwD_not_mono` pairs `sR`
  against `sP`, but `CascadeStrataSettle.lean::reachedByW3d2_shadow_d` builds σ0 over the
  untainted-**filtered** store, so at a one-derived-tuple store the σ0 is `emptyState` and
  `sub` holds vacuously. Against the σ0 that theorem actually constructs, the weak shadow
  holds on all six fields and the strong one is **uninhabited**
  (`strong_shadow_false_at_d_own_sigma0`). This corrects `2026-08-20b`; the pin stays,
  since it is true as stated, with `d_vs_sP_fails_on_sub` beside it saying what it measures.
* **The instrument is proved, and its sabotage found the blind spot.** `shadowB_correct`
  pins the six-field mirror to `UntaintedShadow` itself. Trimming `closedB`'s `ab.2`
  conjunct *and* its lemma statement together gave rc=1 with three errors, all inside
  `shadowB_correct`, while **every `decide` pin stayed green** — `2026-08-28c`'s
  "a guard-only pin cannot catch a fence removal", one layer down.
* **Gate floor drift repaired.** `MIN_TESTS_ALL` was 923 against a live 943, i.e. 20 tests
  could have been deleted with the gate green, against `CLAUDE.md`'s explicit zero-headroom
  contract. Raised, and the floor was checked rather than trusted (at 944:
  `FAIL: tests/ collects only 943 test(s); the gate floor is 944.`, rc=1). That edit then
  correctly reddened `verify.sh` step 4e; regenerated.
* **Both `2026-08-28c` found-not-fixed items discharged.** `formal/README.md`'s two
  figure-bearing paragraphs are deleted rather than updated (the Status one had rotted to
  `762` vs live `943`; the gate-size one restated numbers `FINAL_REVIEW.md`'s generated
  block explicitly says not to restate — it was the fourth such copy).
  `docs/tasktool-trial-protocol.md:403` deliberately untouched, unchanged reasoning.
* **The revert-to-green exit plan is written down** in `P3`'s item block. It was *required*
  in two places and existed in none: green anchor is a recorded commit sha, abort trigger
  declared up front in cycles (cone builds are 200–400s and serial), findings written to
  `PROOF_STATUS.md` **before** reverting, and no partial cone committed.

```
task lint: clean (11 checks, 150 task file(s) parsed)
```

read: board + HANDOFF

**Still owed:** nothing from this session's write-back. Carried forward, unchanged and
deliberate: `docs/tasktool-trial-protocol.md:403` stays as-is (pre-registered rubric).
Noted, not fixed: **there is still no machine-checked home for any cone/site figure** —
the 42-modules / ~136-sites / 3-sessions numbers are prose in `PROOF_STATUS.md` and can
rot exactly as `formal/README.md`'s did.

---

## 2026-08-28c — the public surface is migrated onto `checkPublic`, and the `hql` surface drops from 6 rows to 1

rows: `P3`

User asked what the next task was, whether the rest of `P3` fits one session, and directed
step A only after the scoping said no. Formal detail (the authority for this entry):
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-28c`.

* **Landed:** seven declarations re-stated over `GraphModel.checkPublic` via
  `graph_correct_public` — `backend_equivalence`, `exclusion_effective`, `no_ghost_grant`,
  `Exec.graphRun_check_eq_sem`, `::graphRunOps_check_eq_sem`,
  `W4WitnessDirect.final_applies`/`final_applies4` — plus `Cli.lean`'s graph-mode driver.
  **None gained a hypothesis**, every proof stayed a 1–2 line delegation, `lake build`
  clean first try. 7 of 45 pinned statement rows changed; **zero definition rows dropped**;
  `audited_theorems.txt` byte-identical.
* **The payoff, which is the point of the step.** `docs/latent-gaps.md` named six theorems
  as machine-checked FALSE after the 4c-ii re-point. Five of them plus both `final_applies`
  witnesses are now **out of that set entirely** — the fence discharges the leaf-name case
  — so **the remaining `hql` surface is ONE pinned row**, `graph_correct` (`:27`), kept
  deliberately as the internal-layer statement. The board's "8 declarations" figure is
  superseded.
* ⚠ **The session's sabotage found a real hole, not a confirmation.** The subject was the
  driver↔capstone coupling, not the theorems. Reverting `Cli.lean` to the unfenced read
  while migrating everything else left the entire conformance suite green —
  `495 passed in 590.51s` — and that is structural, not an oversight: pre-4c-ii nothing
  mints leaf nodes, so no corpus can distinguish the two reads. Fixed TEXTUALLY:
  `Exec.lean::graphModeAnswers` is a named definition whose body is pinned verbatim,
  dragged into the closure by `graphModeAnswers_eq_sem` in `statement_pin.py::HEADLINE`.
* ⚠ **Controlling the instrument mattered, and repeated 2026-08-28b's lesson one layer up.**
  The realistic sabotage reverts the body *and* repairs the proof, so `lake build`
  **succeeded (1089 jobs)** — the build is not the instrument. The definition pin fired;
  the **statement pin matched 46/46 and was blind**, because the theorem's text names only
  `graphModeAnswers`. A guard-level pin still cannot catch a read swap.
* **The `Equiv.lean` 27-rung ladder was NOT migrated, at zero cost.** It was flagged in
  advance as the load-bearing unbudgeted branch (6→8 module cone, +27 edits). The answer
  came from the file's own header — a per-stage historical record of the internal layer —
  not from taste.
* **Doc debt:** the `26 statements` rot was **8** live sites, not the 5 recorded; fixed by
  deleting the number rather than resetting it, since 26→46 re-arms the same trap. The
  `CORRESPONDENCE.md` anchor gate caught my own malformed anchor, which is step 4d working.
* **Sizing, delivered as asked:** the rest of `P3` is **3 sessions, not 1**. Nine-agent
  census plus two adversarial critics; every load-bearing figure corrected UPWARD for the
  first time in four attempts (cone 38/39→**42** modules, second ring ~45/4→**90 raw / 50
  code across 8 files**, sites ~123→**136**, in-cone verify cycle ~45 s→**200–400 s**). The
  binding constraint is trap 3: the cone is un-splittable, so there is no green state to
  stop at mid-way. Subagents do not change that — one tree compiles, `lake build` is serial.

Trial lines (`tasks/` parallel-maintenance protocol):

```
task lint: clean (11 checks, 150 task file(s) parsed)
```

read: board + HANDOFF

**Still owed:** nothing from this session's write-back. Two items found and deliberately
NOT fixed, recorded so the next session can pick them up: `formal/README.md:122-124` still
carries stale gate figures (`tests/` collection **762**, live floor 923 / collected 943) —
same rot class as the `26 statements` fix, different item; and
`docs/tasktool-trial-protocol.md:403` restates the superseded six-theorem falsity claim and
must stay as-is, because it is a **pre-registered** trial rubric and editing it would
corrupt the pre-registration rather than fix a doc.

---

## 2026-08-28b — the fence-modeling endgame landed green, and it never needed `hql` or the 4c-ii cone

rows: `P3`

User asked to "do the hql thing". Scouting said don't, and the re-scope was confirmed
before any Lean was written: `hql` is not the endgame but the INTERNAL layer, and the
thing that keeps the headline unguarded is a public fence. Formal detail (the authority
for this entry): [`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`## Session 2026-08-28b`.

* **The correction that made the session cheap.** 2026-08-28 recorded the fence layer as
  owed INSIDE the 4c-ii commit — which trap 3 forbids splitting, so it read as expensive
  and unscoutable. It is not: `graph_correct_public`'s fenced branch needs only `WF S`
  plus "undeclared ⇒ `sem` denies", and its unfenced branch is today's `graph_correct`
  verbatim. It landed BEFORE the cone, on green, as its own commit.
* **Landed:** `GraphIndex/Fence.lean` (`checkPublic` + the `relNameOK_of_mem_keys`
  bridge), `FullScope.lean::graph_correct_public` (unguarded public read = `sem`), and
  `CascadeStrataAssemble.lean::reachedByW3d2E_schema` — a prerequisite no document had
  costed. Purely additive: pins 38→45 statements / 155→160 definitions, **zero rows
  moved**, no existing statement or proof changed.
* ⚠ **The vacuity trap, and the sabotage that caught it.** `graph_correct_public` proves
  green even under a fence that NEVER FIRES, because pre-4c-ii nothing mints leaf nodes.
  The first sabotage (nulling `publicOfLeaf`) was the WRONG one — it breaks `Leaf.lean`'s
  own lemmas, so the build dies before reaching the new pins: it sabotaged the instrument.
  The narrow one (`checkPublic := check`) leaves the four polarity pins GREEN and fails
  exactly one declaration, `fence_changes_answer`. A guard-only pin cannot catch a fence
  removal; only one stated over a state can.
* **Preflight closed:** `parse_schema_ast` rejects dotted REFERENCES, not just dotted
  declarations (`_validate_ast_references`), so the WF clause is the faithful model — with
  a carve-out for the BARE `...` sentinel.
* **Deliberately not done:** migrating the public surface and `final_applies`(`4`) onto
  `checkPublic`. That is where the 4c-ii payoff is banked, but it changes pinned statements
  on the non-vacuity instruments and deserves its own session and sabotage.

**Method note.** The scouting fan-out's report was evidence, not findings: its
"three files import `GraphIndex.Leaf`" was two (the third is transitive) and its
"four docs say 26" was five. Both were caught by first-hand greps before anything was
written down. The load-bearing claim — that `graph_correct_public` is provable today with
no `hql` — was verified against the live tree before the plan was accepted.

task lint: clean (11 checks, 150 task file(s) parsed)
read: board + HANDOFF

Still owed: the nine pytest tiles. `verify.sh lean` is green on this tree; the tiles were
last green on `2026-08-24d`'s tree and this session changed Lean, so they are stale and
must be re-run before any push.

---

## 2026-08-28 — `P3`'s two human calls made (`hql` accepted, Route B retained); the census falsified B's cone argument

rows: `P3`

User-scoped de-risk session ("de-risk + additive only"), triggered by the question "can
4c-ii land in one session with subagents?" — answered NO, and the census is why that
answer was right. Six read-only census agents re-verified `P3`'s recorded sizing against
the live tree; the formal detail is in
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-08-28` (the authority for this entry) and scope doc §11.11 (which supersedes
§11.9/2026-08-20b's sizing). Headlines:

* **Both standing `P3` human calls are made** (user delegated in plain text, stating the
  goal: an unguarded "graph = semantics" claim with no sharp edges): `hql` accepted;
  Route B retained — but its "zero additional cone" selection argument is **falsified**
  (the `shadow_graphRec_agree` repair propagates ~45 second-ring sites through
  `ReconcileStars.lean::checkFn_agree_of_graphRec` into 4 files with zero
  `UntaintedShadow` presence; zero of the 14 sites are mechanical). Retention grounds:
  measured-bounded vs unmeasured-whole-tree, and three sessions of landed scouting.
* **The `hql` guard is cheap (8 declarations, depth 2, audit pin untouched) but lands on
  the leg-5 non-vacuity instrument** (`W4WitnessDirect.final_applies`), where it is
  FALSE at leaf queries — so the recommended repair shape adds a fence-modeling public
  layer (`checkPublic` mirroring `BL-2`'s public deny; unscouted) keeping the headline
  claim unguarded. Owed in the 4c-ii commit.
* Budget ~136 sites / 8 files, not ~123 / 7 — the third consecutive low count on this
  item, each time by the previous session's own new files.
* The 2026-08-21b stale-comment debt is discharged: four Lean doc-comment sites now name
  `_check_internal` + the fence (`CORRESPONDENCE.md` §7.1 marked RESOLVED). Comment-only.
* `CLAUDE.md` gained a "Delegation" section (user preference, stated this session:
  subagents exist to minimize context and tokens, never for parallelism; standing
  permission for read-only fan-outs of census shape).

**Method note.** Two census claims were load-bearing for the route re-adjudication
(`WF`'s single field; `checkFn_agree_of_graphRec`'s internal quantifier) — both were
re-verified first-hand before anything was written down. Per
[`docs/subagent-fanout-runbook.md`](../subagent-fanout-runbook.md), a fan-out discovers;
it does not adjudicate.

task lint: clean (11 checks, 150 task file(s) parsed)
read: board + HANDOFF

Still owed: the nine pytest-tile verdicts are green only on `2026-08-24d`'s tree —
re-run them before any push (today's edits are comment-only Lean + md; the `lean` phase
was re-run green on today's tree, twice). Landing-session preflight, before choosing
WF-clause vs threading: the `parse_schema_ast` dotted-reference probe (PROOF_STATUS
`2026-08-28` §3).

---

## 2026-08-24d — `R6-6` landed at its predicted 4.75 → 1.75 statements/`check`; its pin was green under sabotage

rows: `R6`

`task lint: clean (11 checks, 150 task file(s) parsed)`

`read: board only`

**On that read line, because it is the first one that means anything.** `python
scripts/task.py board` was the only thing read to pick and start the work: the user asked
"what are the next tasks, anything small?", and `board` + `ready` + three `show`s answered
it end to end — `NOW`/`NEXT` are all L/M and entangled, the `S` rows are listed, and each
`show` carried the traps and the read-first list. `HANDOFF.md` was opened only at
write-back, to edit it. The previous two entries both warned that the trial's read tally
was being sampled on comparison tasks that are guaranteed to need both trees; this is the
ordinary-work sample they said was missing, and on it the query did replace the file read.
⚠ One qualifier, against over-reading it: the traps that actually steered the work
(`R6-6`'s moved-symbol trap, `TK47`'s "check the siblings") live in the task files because
`migrate.py` put them there, and both were **incomplete** — see below. The tree replaced
the board read; it did not replace re-deriving from source.

**`R6-6` landed** (`index_v4/core.py::ReachabilityIndex.resolve_node_ids`, called once by
`::WildcardIndex._check_internal`). The edge probe in front of which it sits was already
one round trip; the up-to-four identity resolutions feeding it were a point SELECT each.
Measured `python -m benchmarks.profile_r6 --target graph-check`, run alone: `node_v4`
**4.00 → 1.00** per check, edge unchanged at 0.75, total **4.75 → 1.75** (`−63.2%`),
1,080/2,000 true answers unchanged. Exactly the audit's prediction. Full write-up with the
before/after table: `benchmarks/results/PERF_ANALYSIS.md` § Applied.

* **The one deviation from the audit's fix sketch is the transferable part.** The sketch
  said "a per-call fresh query, not a cache", and taken literally that is a WRITE-path
  regression: `_check_internal` is also reached from `processor.py::_EvalContext.leaf_check`
  inside a cascade, where the N15 `_node_cache` is installed and warm, so a fresh SELECT
  replaces cache hits with SQL. The landed helper batches *through* the cache. The
  verifier's "select bare columns, not entities" nit was declined for the same reason — a
  projected row cannot be cached, and the four statements it replaces already built
  entities. `R6-5`, `R6-4` and `R6-9` are the same shape and inherit the warning; it is now
  in the `R6` board block.
* ★ **The dropped-key pin was GREEN under the sabotage it exists for, and the fixture was
  rewritten rather than the sabotage** (`docs/sabotage-procedure.md`: a green pin under a
  sabotage that should break it is a verdict on the pin). It asked `check(alice, doc:d1)`
  in all four probe cases; because the closure is materialised, the bridge
  `alice → w_all → d1` is a real edge and probe 1 answers alone. Probes 3 and 4 are only
  reachable with a **ghost endpoint** — a node that does not exist contributes no id and
  drops every probe key naming it. After the rewrite, dropping key *k* reddens exactly the
  two cases whose surviving probe mentions it: a 2×2 that is verified, not asserted.
* ★ **Dropping the `w_all` key is `2 failed, 23 passed` in `tests/test_reads.py`** — the
  only two reds are the two new cases, while all **nine** of that module's oracle
  grid-parity tests stay green under a live under-grant. Widened it IS caught
  (`4 failed, 56 passed` over matrix + lookup-oracle + wildcard-property), so this is a
  module-local blind spot, not a project-wide one. `tests/test_lookup_oracle.py` (45
  collected) is fully green: the lookup surface never assembles a `w_all` probe key.
  Eight sabotages in total; the literal output is in the R6-6 block of `tests/test_reads.py`.
* **The refactor orphaned `WildcardIndex._w_id`, and its docstring was the load-bearing
  part.** Batching the w-variant ids into `_check_internal`'s own call left that wrapper
  with no callers anywhere in the repo — and it is not a `CORRESPONDENCE.md` anchor, so
  nothing in the gate would ever have said so. It was deleted, and the **W2** paragraph it
  carried (why w-node resolution is deliberately uncached across calls: stale misses, and
  false POSITIVES under SQLite rowid reuse) moved onto `::WildcardIndex._w_node`, the live
  symbol the rule now constrains. The rule outlived the function; that is the usual way one
  of these gets lost.
* **The instrument was corrected too, and it needed it more after the fix than before.**
  `benchmarks/profile_r6.py::target_graph_check`'s verdict predicate is `node_per >= 2.0`,
  so post-fix **0.00 reads NOT MOTIVATED exactly like 1.00** — a probe that stopped
  reaching the code would report as a *better* result than the real one. It now asserts
  non-vacuity first. Sabotage: blind the `node_v4` tally → `INSTRUMENT BROKEN: 0.00
  node_v4 statements per check`.

**`TK47` closed, and it under-counted its own scope by four.** It named five stale
`WildcardIndex.check` citations in `docs/perf-round6-audit-2026-08.md`; there are **nine**
— `### R6-18`'s four verbatim blocks name the same moved probe, and so do appendix leads
A4 and A14. Only the doc's own non-verbatim claims were repointed at
`::WildcardIndex._check_internal` (two table rows and the `### R6-6` header). **Every
`>`-quoted finder/verifier block was left verbatim on purpose** — those are the record of
what was said on 2026-08-15/17, and editing quoted evidence to match today's tree is how
provenance is destroyed; one dated symbol-correction note under the file's status banner
covers all of them. That note also states why this class is structurally uncatchable by an
anchor gate: `formal/conformance/anchor_check.py` reads only `CORRESPONDENCE.md`, and even
in scope it would pass, because **both** names exist.

**Two smaller corrections, made in place per Rhythm 5.** `benchmarks/profile_r6.py`'s Run
block told readers to size the two GRAPH targets with `--scale`, which those targets do
not take (they read `--graph-scale`) — so the audit's own `--target graph-check --scale
400` silently ran the default 200 and nobody noticed. No recorded R6 figure is affected
(statement counts are scale-invariant) and the landing measurement states the scale it
actually ran at. And `tests/test_reads.py`'s "warm the w-id cache" comment, untrue since
W2 made `_w_id` deliberately uncached.

**Gate: all ten phases green on the committed tree**, plus a fuzz sweep beyond it. R6-6 is
not an algorithm change — the probe-key set is identical, so `CLAUDE.md`'s sweep trigger
does not strictly fire — but it rewrites how the hottest authorization read resolves its
ids, so one ran anyway:
`HYPOTHESIS_PROFILE=deep pytest tests/test_hypothesis.py tests/test_lookup_hypothesis.py -q
--hypothesis-seed=17` → **`47 passed in 2357.03s (0:39:17)`**. (`--hypothesis-seed`, never
the `HYPOTHESIS_SEED` env var, which hypothesis does not read — `CLAUDE.md` footgun 2.)

**Filed, not fixed:** the audit's status banner says "Nothing here is landed", now false
twice over (`R6-10`, `R6-6`). `TK48` already owns that banner for a different stale clause
and its trap says to correct it from the body, so both clauses were routed there to be
fixed in one reviewed edit rather than two.

Still owed: nothing.

## 2026-08-24c — `TK46` closed: the board linter was blind to every `R6-N` id, and the one-line fix was two

rows: none. No board row changed. The item this session closed is tree-only, so it cannot
be named here — the fixed check below refused this very line when it tried, which is the
first thing the fix caught and a fair note on the two-tree split: `rows:` is a board
vocabulary and has no way to say "a tree item moved". Two board `moved` cells disagree
with the tree and were left alone deliberately — see the divergence note.

`task lint: clean (11 checks, 150 task file(s) parsed)`

`read: board + HANDOFF`

**On that read line.** `task.py board` came first and answered "what is next" on its own.
`HANDOFF.md` was then read in full because the user's second question was *do the two
trees agree* — the same task-specific reason as `2026-08-24b`, and the same caveat: this
is not evidence the query failed to replace the file read. Two of the last three sessions
have now been comparison tasks, which is a fair warning that the trial's read tally is
being sampled mostly on the one task shape guaranteed to need both. Ordinary work has
been under-sampled.

**`TK46` fixed and closed** (`scripts/handoff_lint.py`, `tests/test_handoff_lint_row_ids.py`).
`check_ledger_row_ids` could not see the ids it was comparing: `_ROW_ID` matched `R6` in
`R6-99` and stopped at the word boundary, so an invented sub-item citation resolved to its
real parent and reported clean. Nineteen live `R6-N` ids sat in that hole. Full outcome
evidence is in the closed task; the two things worth carrying up here:

* **The row's own estimate was wrong, and its own trap is what caught that.** `TK46` said
  "closed by porting one line". Porting the regex alone was run against the live tree and
  false-redded a *real* id — `FAIL: docs/history/session-log.md:388 cites board id 'R6-10'`
  — because the board names landed sub-items in the `### R6` block and never gives them a
  table row. So `known` now harvests the whole board, with the non-vacuity floor kept on
  the **table** harvest specifically; on the whole-file harvest a broken row parser would
  coast on prose. The row's third trap ("widening a regex can go the other way") predicted
  exactly this class.
* **The 2026-08-16 sabotage that certified this check was `P99`, and `P99` could never
  have found the bug.** It proves the comparison works; it cannot prove the regex read the
  id being compared, because `P99` is a shape the regex handles. The instrument was not
  controlled, only the subject. The replacement pins assert on the extracted **tokens**:
  `inherited -> ['R6', 'R6', 'P3', 'P6']` vs `ported -> ['R6-99', 'R6', 'P3', 'P6']` over
  the same sabotaged corpus. Method lesson filed to
  [`sabotage-procedure.md`](../sabotage-procedure.md).

Nine tests, durability rank 1 rather than a docstring. Suite-level sabotage run with each
half reinstalled separately and the red is attributable both times: inherited regex →
`3 failed, 6 passed` (the three extractor pins), whole-board harvest removed →
`1 failed, 8 passed` (the false-red control).

**`TK*` census, on the user's question "are they tracked anywhere".** They are, and
nothing is missing: **51 ids, `TK1`–`TK51`, no gaps**, 49 open (14 `LATER`, 25 `HOLD`,
10 `SOMEDAY`) and 2 closed (`TK1`/`TK14`, both `REFUTED` records). They carry no board row
**by design** — they are unranked, and the board's capacity budgets are the reason the
tree exists. ⚠ But they are tracked in exactly **one** place: outside `tasks/`, exactly one
`TK` id is mentioned anywhere in this repo (`TK49`, in `HANDOFF.md`'s `HS-5` row). The
trial's own exit plan in `CLAUDE.md` is "delete `tasks/`, `scripts/task.py` and this
bullet, which is one revert" — that revert deletes 49 open items that no source document
contains. **The 2026-08-30 verdict is not a row on either tree**, which is the one item
neither system tracks.

**Divergence found, and NOT reconciled — it needs a semantic call, not an edit.** Two
`moved` cells disagree, in opposite directions:

| row | `HANDOFF.md` | tree | what happened |
|---|---|---|---|
| `P3` | `2026-08-21b` | `2026-08-24` | the `related`-edge sweep bumped the file's `moved` |
| `R6` | `2026-08-24` | `2026-08-21` (`updated: 2026-08-24b`) | the child re-count went to `updated` |

Same week, same two sessions, opposite conventions: one treats a navigation-edge write as
progress on the item, the other treats a re-count as not-progress. `moved` is the neglect
signal on both trees, so guessing would just move the disagreement somewhere quieter.
Recorded here so it is not "reconciled next time" by silent overwrite.

**Gate.** `lean` re-run and `PASSED` on this tree (rc=0, 581 audits, step 4f green).
Step 4e caught the nine added tests and `FINAL_REVIEW.md`'s generated block was
regenerated deliberately (`923 → 932`, whole-repo `1418 → 1427`) — the counts pin doing
its job, not a hand edit. The four `tests-tile` phases were re-run; the five `conf-tile`
phases were **not**, and read `NO` for this tree. Ask `python scripts/gate_status.py`.

**Still owed:** re-run the five `conf-tile` phases before any push (unaffected by this
change in substance — no `formal/conformance/` file was touched — but tree-addressed, so
their verdicts do not apply here). Adjudicate the `moved` semantics above and reconcile
both trees in one session. File the 2026-08-30 trial verdict as a tracked item on both
trees before the deadline.

---

## 2026-08-24b — the `related`-edge sweep: F1 repaired with 10 edges, 2 refused as false links

rows: none. **No board row changed**, and that is a finding, not a skip — see below.

`task lint: clean (11 checks, 150 task file(s) parsed)`

`read: board + HANDOFF`

**On that read line.** `task.py board` came first and was enough to find the work. `HANDOFF.md`
was then read in full **because the task was to compare the two trees** — the board's
cross-item prose is the reference the sweep is measured against. That is a task-specific
reason, not evidence the query failed to replace the file read; a session doing ordinary
work would not have needed it. Recorded this way so the trial's read tally is not
silently inflated by the one task guaranteed to require both.

**Executed the item `2026-08-24` left owed: the `related`-edge sweep for collisions
other than `P3`/`P6`.** Ten edges added, each written on the **blind** end only (`show`
computes the incoming half, so one write serves both directions):
`R6-3`→`R6-13`,`R6-17` · `R6-16`→`R6-7`,`R6-8` · `TK20`→`R6-18` · `TK25`→`R6-5` ·
`TK6`→`P3`,`P4` · `TK51`→`TK44` · `TK8`→`P19` · `TK13`→`P18` · `TK38`→`P16` ·
`TK47`→`R6-6`. Full table, criterion and evidence:
[`tasktool-trial-protocol.md`](../tasktool-trial-protocol.md) §6 `2026-08-24b`.

**The criterion was fixed before the corpus was read**, because "add an edge wherever two
ids appear together" is how a navigation aid becomes noise: an edge is added only where
taking one item blind to the other is a *mistake*, **and** at least one end's `show` does
not already name the other. Verified by running `show` at the blind end rather than
trusting the write — `show P3` now reports incoming `TK6`, `show R6-18` incoming `TK20`.

⚠ **The A/B's subject has now changed.** The 2026-08-24 cost and quality figures are not
reproducible against this tree; a re-run is a different experiment, not more n.

**Two candidate edges were REFUSED, and one was a trap the corpus had set in advance.**
The generator was a mention scan (grep every body for other ids) and it proposed **51 of
91** tasks — ~5:1 noise, because the `R6-*` land-order paragraph and the "a cited symbol
may have MOVED" trap are boilerplate. `TK11`→`P7` was refused because `TK11`'s own trap
says *"Lean's projection `P7` is not board id `P7`. **Do not resolve `P7` by grep**"* — and
the scan had resolved it by grep. `TK19`→`P3` is the same id-namespace collision. **A
mention scan is a candidate generator and must not be the adjudicator**, which is the rule
[`subagent-fanout-runbook.md`](../subagent-fanout-runbook.md) already states for fan-outs.

**The sweep also found a false claim about the format itself.** `R6-16`'s trap explained
why the co-design constraint *cannot* be encoded and must live in prose across three
files, ending "the vocabulary has no mutual edge (lint rejects the cycle)". True of `deps`,
**false of `related`** — the spec defines it as untyped, symmetric-ish and deliberately not
cycle-checked. Corrected in place with a dated note; the constraint still lives in the
traps, because `related` navigates and cannot say "simultaneity". The tree grew a
mechanism and an item written before it went on asserting the mechanism did not exist.

**`task.py sync` reported 2 drift items, and one was a live wrong figure.** Run after the
sweep, as the trial's own reconcile instrument:

* **`HS-5` — content drift, not formatting.** The `2026-08-24` retitle fixed the title and
  left the BODY asserting *"six always-living docs"* — the exact figure that session
  retracted, still live one layer down. Rewritten to mirror the board cell (no count here;
  `TK49` owns it), a trap added against restating it, read-first repointed at `TK49`.
  **This is the A/B's finding `P4` recurring inside the tree**: a summary row carrying a
  figure its own child corrects. The board row was right and the task body was wrong —
  the second board-right/tree-wrong fact the trial has produced, after `F1`.
* **`R6` — digest only; content agrees and the tree is AHEAD.** The board was corrected on
  `2026-08-24` (`25.3%`→`25.4%`, and `11/4/3`) to match what the task body had carried
  since `2026-08-21`, so the stored `source_hash` still pointed at pre-correction board
  text. Re-stamped with `ack`, which holds `moved` — an ack must not claim progress.

Both acked; `sync` now reports **CLEAN**.

⚠ **One divergence is left standing ON PURPOSE: `R6`'s `moved` is `2026-08-24` on the
board and `2026-08-21` in the tree.** Both are defensible (the board row progressed on the
later date; the task did not), and harmonising it would erase exactly the kind of evidence
the week is being run to collect. Recorded here instead of silently fixed.

**Why no board row moved, stated rather than left to inference.** The board has no
`related` field — its equivalent is prose adjacency, which it already has for every pair
it carries (`P3`/`P6`, `R6-3`=`R6-17`, `R6-16`→`R6-7`+`R6-8` in the land order). Eight of
the ten edges touch `TK*` ids that have **never had board rows**, so there is nothing to
mirror. The `R6-16` correction is tree-only for the same reason: that trap exists only in
the tree. This is the parallel-maintenance rule being satisfied, not waived — but it is
also the first real asymmetry the trial has produced, and it points one way: **the tree
can express something the board cannot**, which is the mirror image of `F1`.

Still owed: unchanged from `2026-08-24` except the sweep, which is now done. `HS-5`'s real
deliverable — adjudicating which measured docs are *deliberately* exempt from
[`docs/README.md`](../README.md) §2 — is still untouched. `tasks/HS-5-six-always-living-docs-...md`'s
FILENAME still carries the retracted "six". **The full gate has still not run on this tree
— `verify.sh lean` re-run this session and PASSED on it (`holes=0, audits=581, pinned=581`;
`.gate-runs/20260824-081226-lean.log`), and that is all. Nine tiles before any push.**
No code changed this session, so nothing invalidates the 2026-08-21 tile run except the
tree hash. Branch `tasktool-trial` is
still unmerged, and until it is, the `CLAUDE.md` trial bullet is invisible to sessions on
other branches and the trial silently does not happen.

---

## 2026-08-24 — file-per-task tracker on trial beside the board; 18-agent A/B; three stale board figures fixed

rows: `HS-5` (retitled), `R6` (count corrected), `P3` / `P6` (a `related` edge, tree only).

**No code changed. No gate phase was re-run beyond `lean`.** Branch `tasktool-trial`,
five commits, additive: `tasks/` (150 files), `scripts/task.py`, `scripts/trial_metrics.py`,
`scripts/trial_stats.py`, `docs/tasktool-spec.md`, `docs/tasktool-trial-protocol.md`,
`docs/tasktool-trial-stub.md`, a narrow `.gitattributes`, and one `CLAUDE.md` bullet.

**The trial, and the obligation it puts on you.** `tasks/` is a file-per-task tree whose
`board` verb prints the session-start view as a QUERY (~19 lines) instead of a file. It
runs BESIDE `HANDOFF.md` until **2026-08-30**; the board stays authoritative and nothing
is gate-enforced. **Whoever edits either tree edits both, in the same session** — the two
are a control and a treatment arm and a divergence at the end of the week IS the result,
so a session that updates one destroys the evidence. Close with `python scripts/task.py
lint`'s literal output and a `read:` line in your entry here. Full contract:
[`docs/tasktool-spec.md`](../tasktool-spec.md); protocol and results:
[`docs/tasktool-trial-protocol.md`](../tasktool-trial-protocol.md).

**The instruction could not go on the board.** `HANDOFF.md` was at 260 lines against a
260-line ceiling — there was no room to write "also update the task tool" into the file
whose fullness is the thing being tested. It went in `CLAUDE.md`. The ceiling then caught
a one-line overrun during this session's own board edits, which is the check working.

**The A/B, pre-registered before any agent ran.** 18 agents, two arms (board vs tree),
one session-shaped task: pick up the `NOW` item and say how you would start. Tree median
tokens were **88.7%** of board on Haiku and **88.8%** on Sonnet — the same effect twice.
Haiku separated completely (Mann–Whitney U=0, critical U=5, p<0.05); tool calls separated
the other way, board answering in ONE call every time against the tree's 3–5. Sonnet was
descriptive only at n=3, as declared in advance. **Do not read 11% as "11% less
reading"** — a large fixed system-prompt floor sits inside both figures.

Quality was at parity: 17 of 18 agents found `P3`, the FALSE-AS-WRITTEN human call, the
scope-doc §11.10 traps and the census hole.

**The finding that goes AGAINST the tree, and it is the one to carry forward.** "`P6` is
not parallel-safe with `P3`" was reached by 5 of 9 board agents and 1 of 9 tree agents.
Structural, not luck: `P3`'s file had `deps: []` and `related: []`, so `show P3` never
mentioned `P6`, while on the board `P6`'s row sits four lines below `P3`'s and every
reader scrolls past it. **A single file buys cross-item awareness for free, and the tree
deletes that along with the ceiling.** Fixed for this pair (`related: [P6]` on `P3`;
`show` computes the incoming half, so one edge serves both ends) — but the *class* is
open, and every other collision in the corpus is still invisible.

**Three stale board figures, all found by the parallel tree and all fixed here.** `R6`
said `9 to land, 5 declined`; re-counted from the children it is **11 / 4 / 3**, and the
board heading said "nine remain". `R6-19` said `25.3% cumulative` where the audit doc says
**25.4%** — the old figure paired two different passes and no source states that pair.
`HS-5` said "six always-living docs". **It is NOT retitled to eleven**, because `TK49`
carries a trap saying exactly that: the count read six, then nine, then eleven across
three days, so a title carrying a count rots again. Both the row and the task title now
name the rule and point at `TK49` for the number.

⚠ **Nine board agents answered `9` in one tool call, several with corroborating detail** —
one listed the nine ids, another added "5 declined, 3 unreachable". A single authoritative
file manufactures uniform confidence whether or not it is right, and nine independent
readings of a wrong figure are not nine pieces of evidence.

Still owed: `HS-5`'s real deliverable — adjudicating which of the measured docs are
*deliberately* exempt from [`docs/README.md`](../README.md) §2 — is untouched; only the
title was fixed. The `related`-edge sweep for collisions other than `P3`/`P6` is not done.
`tasks/HS-5-six-always-living-docs-...md`'s FILENAME still carries the retracted "six"
(the id is the address, so lint is clean and nothing is broken, but it misreads). The full
gate has NOT been run on this tree — only `bash formal/verify.sh lean`, green; run the
nine tiles before any push. `tasktool-trial` is UNMERGED, so until it is merged the
`CLAUDE.md` trial bullet is invisible to sessions on other branches.

## 2026-08-21b — BL-2 leaf-name read leak found AND FIXED; machine-checked: post-4c-ii headlines FALSE at leaf queries

rows: `BL-2` (filed **and** closed this session; retired), `P3` (scouted/designed, NOT
landed, stays `NOW`).

Assigned `P3` (leg 7, step 4c-ii + step 7). `P3` did NOT land: scouting and design
produced plan-changing findings, and a probe built for one of them surfaced a live bug in
the shipped Python, which took priority. Branch: `bl-2-leaf-name-read-leak`, uncommitted.
The formal detail lives in `formal/history/PROOF_STATUS.md` `## Session 2026-08-21b`;
this entry summarises and points.

**`BL-2` — the graph index GRANTED queries at minted LEAF PREDICATE names, bypassing the
boolean guard — found, measured, fixed and pinned in one session.** The divergence, the
mechanism, the adjudicated DENY semantics (user call), the blast-radius numbers (201 of
1,728 target-position comparisons diverged, all with one signature; 0 of 4,833
subject-position), the fix and the three-leg sabotage record are all in
[`spec-deviations.md`](../spec-deviations.md) `## 2026-08-21b` — one home, not restated
here. Short form of the fix: `index_v4/wildcard.py::WildcardIndex.check` split into a
fenced public entry (leaf-family queries answer `False`/empty) and
`::WildcardIndex._check_internal` carrying the old body verbatim for the processor's two
legitimate internal readers; `lookup` / `lookup_reverse` / `_classify_ids` guarded. The
durable half is the GRID: `tests/parity.py::ParityEngine._grid` now unions leaf families
into the pre-cap pool (Layer A) plus a deterministic post-cap floor slice (Layer B) —
every differential grid in this repo was built from DECLARED `(object_type, relation)`
pairs, so no grid could ever express the failing query. Pins:
`tests/test_reg18_leaf_name_read_leak.py`, 6 positive pins, no xfails, every leaf name
derived from `compiled.leaf_families`. `formal/CORRESPONDENCE.md` rows re-anchored onto
`_check_internal` (anchor check 533/533 resolved) and a new §7.1 entry filed for three
stale Lean doc comments (see `Still owed:`).

**`P3` scouting — the resumable state (full formal detail in PROOF_STATUS
`## 2026-08-21b`, and the `P3` board block carries the working summary):**

* Route B's site budget re-verified live and CORRECT (~123: `UntaintedShadow` 84 lines in
  7 files, `DerNode` 39–40 in 3) — **but the adjudication's census has a HOLE**:
  `CascadeStable.lean::shadow_graphRec_agree` is one of the 11 audited shadow names, with
  14 call sites including one in `CascadeEnum.lean` — a file with ZERO `UntaintedShadow`
  mentions, hence outside the 7-file/84-site budget — and its
  `hunt : isDerived S (dt',r') = false` hypothesis does NOT imply `publicOfLeaf = none`.
  Route B forces a new hypothesis on an audited signature plus 14 call-site repairs.
  Unbudgeted work.
* The `FoldAdmits` lockstep is **21 sites that MOVE and 3 that MUST STAY** on the σ0 side
  — correcting the previously recorded "all 24 in lockstep".
* Dominant-cost decision taken: KEEP the names and change the BODIES of the live write
  leg; `rewriteClosure` KEEPS its meaning (the σ0 chain is rules-built by design, so a
  global redefinition is NOT available); `writeRules` keeps name AND body (changing it
  would BE the rejected Route C).
* An UNOWNED proof obligation surfaced: the shadow-existence write case
  (`CascadeStable.lean::reachedByW3d_shadow`, via `untaintedShadow_writeLeg`) pairs the
  SAME list on both folds, and post-re-point the leaf list is a STRICT SUPERSET on a
  mixed schema even for untainted tuples. Two design slices each assumed the other owned
  it. Not mechanical re-spelling; the Lean budget grows.
* MACHINE-CHECKED, by two independent kernel `by decide` constructions (standalone
  probes, deleted, tree left clean): AFTER 4c-ii the headline theorems are FALSE AS
  WRITTEN — not merely unproven — at queries whose relation is a minted leaf name. ~10
  pinned headline statements need a new query guard; the narrowest repairing one is
  `hql : publicOfLeaf S q.object.type q.relation = none`, and two guard shapes to REFUSE
  are recorded in PROOF_STATUS. ⚠ **This needs a HUMAN CALL before it lands** — it
  narrows the governing claims, and Route B itself was adjudicated as a human call for
  less. Latent today only (4c-ii has not landed): entered in
  [`latent-gaps.md`](../latent-gaps.md). This probe is also what surfaced `BL-2` — the
  shipped Python reproduced the model's grant.

**Gate, as observed on this tree:** all TEN phases PASSED — the nine pytest tiles
(`conf-tile:1/5`…`5/5`, `tests-tile:1/4`…`4/4`) with zero `xfailed`, zero `skipped` and
every floor met, then `lean` LAST (`holes=0 audits=581 pinned=581 defs=155`), after
`doc_counts --generate`, per the runbook ordering (ledger `2026-08-21`'s lesson).
Collected counts live in `formal/FINAL_REVIEW.md`'s generated block, not here, per
Rhythm 3b. `formal/verify.sh` `MIN_TESTS_ALL` raised 903 → 923, the count re-measured
with `pytest tests/ -q --collect-only`, NOT off a run tail; `MIN_CONF_ALL` (495) and
`MAX_TESTS_XFAILED` unmoved.

Still owed:
* The three Lean doc comments recorded in `formal/CORRESPONDENCE.md` §7.1 (NEW
  2026-08-21 entry) still assert the OLD `leaf_check` → `WildcardIndex.check` identity —
  `GraphIndex/CascadeStrata.lean:9` and `:89` (module header + the `graphRecR` doc
  comment), `GraphIndex/ReconcileWrite.lean:13-22` (module header), `Audit.lean:927`
  (the W3d-2 narration). Comments only, no proof touches them. Fold the fix into the
  next Lean-touching session.
* The HUMAN CALL on the `hql` headline guard: adjudicate
  `hql : publicOfLeaf S q.object.type q.relation = none` onto the ~10 pinned headline
  statements (`graph_correct`, `backend_equivalence`, `exclusion_effective`,
  `no_ghost_grant`, `graphRun_check_eq_sem`, `graphRunOps_check_eq_sem` —
  `formal/headline_statements.txt`) BEFORE 4c-ii lands; the accept/refuse analysis is in
  PROOF_STATUS `## 2026-08-21b`.

## 2026-08-21 — `BL-1` fixed by one reordering; the gate is GREEN on this tree for the first time since 2026-08-17

rows: `BL-1` (**closed**), `R6` (two filed figures corrected), `P3`/`P6` (untouched, still
`NEXT`).

An execute-the-owed-list session, not a design one. `2026-08-20b` closed with a `Still
owed:` naming three things — fix `BL-1`, run the ten phases, run a 3-seed fuzz sweep — and
this entry is those three plus the two smaller items that trailed them.

**`BL-1` is fixed, and the fix is one reordering.**
`index_v4/processor.py::DeltaProcessor._gc_subject_node` now calls
`::DeltaProcessor._demote_released_node` **before**
`index_v4/wildcard.py::WildcardIndex._maybe_remove_bridges` instead of after. The strip
guard is `fresh.implicit and fresh.reference_count == degree`, and a released userset
subject is still EXPLICIT there (the add-cascade's step-2d promotion), so the strip-first
order was a **guaranteed no-op on exactly the path that needed it** and nothing re-checked
once the demote landed. The board's warning was right and worth having: relaxing the
`implicit` guard is the fix the bug's shape suggests, and it would have broken
`index_v4/core.py::ReachabilityIndex.remove_node`'s "explicit nodes keep bridges" policy.

**The two orders are otherwise identical, which is the argument that this is the narrow
fix rather than a behaviour change** — when the node is already implicit the demote returns
immediately, and when a canonical explicit-reason still holds the node stays explicit and
the strip no-ops exactly as before. The `reference_count == 0` branch keeps its effect (it
now runs after the strip instead of in an `else`; `_maybe_remove_bridges` no-ops at
`rc == 0`). Only the leaking case diverges.

**Sabotage, and the reason it was not skipped as "already proven by the red pins".** The
pins were observed red before the edit and green after, which is a real before/after
control — but it controls the WHOLE edit, and the edit did two things (reorder + collapse
the `else`). The weakening that actually threatens this fix is narrower and entirely
plausible: a later reader tidying the two calls back into their original order. That exact
edit was applied — order swapped, every other part intact — and **both pins went red**
(`2 failed in 0.37s`), restoring gave `2 passed in 0.30s`. So the pins pin the ORDER. Filed
in the test module's docstring and in `spec-deviations.md ## 2026-08-21`.

**Gate: ten phases green ON THIS TREE**, `python scripts/gate_status.py` →
`VERDICT: the ten-phase gate is COVERED on this tree`. `tests/` now collects **915** (up
from 903 — this session's tree adds the `BL-1` and stored-cache-scope files), zero
`xfailed`, zero `skipped`, every floor met. Fuzz: 3 seeds × both hypothesis files —
`test_hypothesis.py` `30 passed` at 7/19/31 in 81.6 / 84.7 / 87.7 s and
`test_lookup_hypothesis.py` `17 passed` at the same three. **The differing durations are
the point**, per the runbook's `HYPOTHESIS_SEED` footgun: identical durations are the tell
that a "multi-seed sweep" ran one seed N times.

⚠ **A tests-tile pair blew the 10-min cap and the ledger is what saved the verdict.**
`tests-tile:1/4` + `4/4` in one command = 350 s + 260 s > 600 s, so the command was killed —
but `4/4` had already finished and written its `PASSED` row, and `gate_status.py` reported
it green on this tree. The 3-day-old per-tile durations in `gate-runbook.md` §1 (95–165 s)
are **well under** what these tiles now cost (187–350 s); that section already says not to
hard-code per-tile counts, and the same caution now applies to its durations. One phase per
command is the safe recipe.

⚠ **The gate was earned twice, and the second time was self-inflicted — filed as a method
lesson in [`gate-runbook.md`](../gate-runbook.md) §"Push gate".** The verdicts are
tree-addressed against **two scopes**: the nine pytest tiles hash CODE (`all` minus `*.md`
and `benchmarks/`), `lean` hashes EVERYTHING. So (a) tidying the `BL-1` pins' stale
present-tense docstrings *after* the tiles were green invalidated all nine — a docstring is
`.py` — and (b) every write-back edit invalidates `lean`. The correct order is: all `.py`
edits (docstrings included) → tiles → write-back → `doc_counts --generate` → `lean` last.
Both were caught by `gate_status.py` rather than by remembering, which is the argument for
that script existing. Two smaller gate facts fell out of the same loop: adding one real
anchor to `CORRESPONDENCE.md` fails step 4e until the counts block is regenerated
(**526 → 527**), and the first draft of that anchor was written
`` `test_hypothesis.py::…` `` — a bare filename, which **4d rejected** (`file does not
exist`). Note the contrast with 2026-08-20b, whose anchors were malformed in a way the
regex could not see at all and so passed: this one was a *real* anchor with a wrong path,
and the gate caught it immediately.

**No Lean change owed — checked, not assumed.** `_gc_subject_node` /
`_demote_released_node` have never had a Lean counterpart: `CORRESPONDENCE.md` §8.1 lists
them under *"Node GC + flag lifecycle AS AN ALGORITHM"* and `ReconcileDiff.lean` /
`Cascade.lean` both say node GC is a modeled-away optimization. A `grep` over
`formal/lean/` for the four function names returns nothing. That bullet already recorded
`ZT-P0-1` as a bug inside the unmodeled region; it now records `BL-1` as the second, with
the distinction that `ZT-P0-1` was found by review and `BL-1` by the differential net.
⚠ **A first draft of that edit claimed "two of two: every bug found here so far has been in
this region", which is simply false** (the three PostgreSQL bugs, X1–X4). It was caught and
narrowed before commit, but it is worth recording that the governing claim doc nearly
acquired a fresh overclaim *in the same edit that was tightening its accuracy* — the same
shape as 2026-08-20b's "the split committed its own new file's cardinal sin".

**The two smaller owed items, both done — and one became an instrument fix.** `R6-11`'s
inflated "8× per reconcile" is corrected in all four places (`perf-next-round.md`, the
audit's verdict table, and the two `R6_PROFILE_2026-08-17.md` sites via a dated header
correction — the body is left as run, because rewriting a measurement record destroys the
evidence trail that makes the artifact visible). **But a doc fix does not stop the next
probe re-deriving it**, so the halving moved into the instrument:
`benchmarks/profile_r6.py::_ctxmgr_entries`, which converts a `@contextmanager`'s cProfile
ncalls into scopes entered and **asserts the count is EVEN** — an odd count means a `with`
never completed, and then halving is the wrong correction, so the probe refuses rather than
reporting. It carries a second control in `profile_r6_write.py`: the halved
`_stored_cache_scope` figure must be `>=` the processor's own true `scopes` counter (a
bound, not a proof — the counter only increments on OUTER scopes). Re-ran the cascade
target to confirm: `184 scopes entered (cProfile ncalls 368, halved)` over 40 reconciles =
**4.6×**, the ~4 shape rather than 8. `R6-11`'s verdict is unchanged (`MOTIVATED`) — its
predicate is "at least one scope per reconcile", which both figures clear. What moved is
the size you would have sized the work off.

`R6-4(a)` now carries a dated `>` note **in its own entry**, not only in the Traps section.
The reason is specific: the fix sketch is a verbatim block containing the words *"a sound
invalidation token"*, and a reader taking `R6-4(a)` off the land-order list reads the
sketch. The verifier block below it already stated the correction, which is exactly why
this was easy to consider already-handled.

Nothing is committed — this tree still carries all of `2026-08-20b`'s uncommitted work as
well as this session's. `python scripts/handoff_lint.py` clean.

Still owed: nothing from this session. The next session inherits a green tree and a clean
`Still owed:` for the first time since 2026-08-16; `P3` (Route B adjudicated, unblocked) is
the recommended pick.

## 2026-08-20b — `R6-10` (2.54×), `HS-2`, `P3` Route B adjudicated — and a fake anchor gate

rows: `BL-1` (new, **NOW**), `R6-10`/`R6`, `P3` (unblocked, → `NEXT`), `P14` (split),
`P6` (corrected), `HS-2` (closed), `LT-1`, `HS-5`.

A three-track session run through subagent fan-outs: `R6-10` (perf), `HS-2` (docs), and the
`P3` proof-design adjudication. **Every track's headline finding came from its adversarial
verifier, not its implementer** — which is the transferable result and the reason the
`Verify` stage is not optional.

**⚠ THE GATE IS RED, DELIBERATELY, AND `BL-1` IS THE NEW `NOW`.** The hypothesis campaign
found a real correctness bug during this session's runs: from an empty store, add+remove of
`('r0','doc','d1','r1','doc','d1')` leaves a `w_any(doc,r0)` node and the bridge edge
`doc:d1#r0 → w_any(doc,r0)`. **It is PRE-EXISTING** — reproduced at `HEAD` in a clean
worktree with the same example DB, so it is not this session's work. Severity was **probed,
not inferred**: store A (add+remove) vs B (fresh) vs `tests/oracle.py`, both backends, all
read surfaces → `255 queries, 0 disagreements`. So it is a **state-only leak, not a
fail-open** — the damage is the row-multiset-restoration violation plus unbounded node/edge
growth under churn. Cause is an ORDER bug, not a missing teardown:
`processor.py::DeltaProcessor._gc_subject_node` calls `_maybe_remove_bridges` **before**
`_demote_released_node`, and the strip guard requires `implicit`, still `False` there.
⚠ Relaxing that guard would break the "explicit keeps bridges" policy — the strip belongs
*after* the demote. Pinned positively (never xfail) by
`tests/test_userset_bridge_release_leak.py`, currently RED; full record in the ledger's
`## 2026-08-20b` entry. **Note the shape: a fuzz campaign found this, and it was only
noticed because a reviewer ran the full suite rather than the touched modules.**

**`R6-10` landed, and its verifier caught a check that could not have worked.** Both steps
(call-site dedup + the reentrant stored-tupleset memo): SQL statements/cycle `1929 → 822`
(−57.4%), `node_v4`/cycle −86%, unprofiled wall `905.5 → 356.2 ms` (**2.54×**), memo hit
rate 98.9% with misses landing at exactly `3 distinct keys × 30 cascades`. The 59.8%
headline was **decomposed before landing** (`_direct_incoming` 28.4% + `_nodes_by_ids`
30.7%; the residual was already amortized by the N15 cache) rather than quoted as the
expected win — the `R6-19` trap in general form.
⚠ **The two new `CORRESPONDENCE.md` citations were NOT ANCHORS.** They were written
`` `::DeltaProcessor._stored_cache_scope()` `` — trailing parens defeat
`anchor_check.py::BARE_RE`, which requires the closing backtick to follow the symbol. The
"524 parsed, 524 resolved" quoted in `PERF_ANALYSIS.md` as proof they resolved is **HEAD's
own number**, i.e. the number you get when a change adds zero anchors. Renaming the symbol
would have rotted §5 with a green gate — the exact rot the anchor gate exists to foreclose.
Fixed → **526**, and sabotaged (rename → `FAIL: 2 anchor(s) no longer resolve`, rc=1).
⚠ **A green sabotage had been run and left out of the record.** `S4` (userset half returns
the shared cached list) came back `36 passed`; `S5`, the identical weakening on the tupleset
half, went red — so it was a coverage verdict, not a broken harness. Both lived only as
`.scratch/*.log`. The pin is now widened over both readers and `S4` reddens. This is why the
`.scratch/` trap was promoted to `CLAUDE.md` today.
⚠ **"The only net" was wrong twice over.** `tests/test_ttu_tupleset_parent_types.py` was
named as the only guard for star-expansion liveness; under the sabotage **all 12 of its
tests stayed green**, and so did `test_matrix.py` (`24 passed`) and `test_lookup_oracle.py`.
The module writes its pool in one batch, so it pins that a star parent *is* expanded and
nothing about the expansion staying *live*. **The repo already knew**: the `2026-07-26`
ledger entry says of a different fix that it "passes every pin in
`test_ttu_tupleset_parent_types.py`, because those write in one batch and reconcile once".
Known a month earlier, in the right file, never carried to where anyone would rely on it.
The limitation now lives in that module's own docstring. Method lesson filed in
[`sabotage-procedure.md`](../sabotage-procedure.md) §'"The only net" is a claim about a
test'. **Also corrected: the "26 tests" figure was a `26 passed` summary line from a
three-module run misread as a module count (it collects 12), after it had propagated into
four docstring sites.**

**`P3` is unblocked: Route B adjudicated (user call).** The `#eval` battery
(`GraphIndex/Scratch4cii.lean`, additive, zero-cone) returned no-kill at all five
`LeafRules.lean` witnesses on both chains. Two things made it trustworthy rather than
merely green: the instrument's draft Bool mirror of `DerNode` was **wrong** (missing
`variant == .plain`) and was caught by a deliberately-failing control, then *proved* correct
(`derNodeB_correct`); and probing the `_d` chain as well as the narrow one **refuted the
adjudication's own opening proposition** (`mono=false` at `SlSw/tApp`), yielding the
corrected per-chain form in scope doc §11.9. The weakening is invisible to
`backend_equivalence` because `UntaintedShadow` is **hypothesis-position at every lemma
whose conclusion leaves the shadow layer**; the pinned statement survives byte-identical and
all 581 audits keep every member. And "keep the strong form" was never an option —
`Scratch4cii.lean::strong_shadow_false_at_raw` machine-checks that the unweakened shadow is
already FALSE at a leaf-routed state. `P14` splits: the classification half is absorbed into
`P3`, the reach-collapse half stays `deps: P4`, and the `P3 → P14 → P4 → P3` cycle breaks.

**Board corrections earned this session.** `P6`'s row claimed for weeks that it "can run in
parallel with `P3`" — false: they are logically independent but textually collide on
`writeRules`, `writeLoggedOne` and `FoldAdmits`, and **pay the same 38-module cone**.
`R6-4(a)` is **unsound as filed** (its `(row.id, row.version)` memo breaks on SQLite —
deleted residues restart at `version=1`, rowids recycle). `R6-11`'s "8× per reconcile" is
**2× inflated**, a cProfile generator-resume artifact. The board hit both its line ceiling
and its trap budget, so seven `P3` traps went to scope doc §11.10 and five `R6` traps to the
perf audit doc — the defined overflow move, not a ceiling raise.

**The board's premise overstated the file.** `HS-2` said `docs/spec-deviations.md` "answers
two questions at once", which reads as *find the cut point*. There is no cut point: the
latent half was ~250 lines scattered across `2026-07-26 — ZT-P5` §Target 1–5, `2026-07-27b`
§"Residuals — the honest part", and three already-closed "filed not fixed" blocks. So this
was an **authoring** job, not a move, and the next reader of a "split X" row should budget
for that.

**The split that landed.** The dated LEDGER keeps the filename (user decision) —
[`spec-deviations.md`](../spec-deviations.md) — and the new
[`docs/latent-gaps.md`](../latent-gaps.md) owns "what is still latent today". Keeping the
name collapsed ~90 citer edits across 25 `.py` files to 10 doc edits and, more importantly,
keeps `docs/specs/graph-boolean-ivm-spec.md`'s charter (*"append a dated entry to
`docs/spec-deviations.md`"*) TRUE rather than falsifying a frozen spec.

**The boundary, decided against `docs/README.md` §1 before a line moved.** The two halves
have *opposite update rules*, and that — not size — is the whole reason to split: a ledger
entry is append-only and true as of its date; a latent inventory is rewritten in place. So
what moved is **status, not evidence**. The 2026-07-26 entry keeps every finding it
recorded; what left it is the "Disposition (board row `LT-1`, HOLD)" paragraph, i.e. the
one paragraph that had to be rewritten every time reality changed. `### Target 2` and
`### Target 3` are **section titles in both files now**, deliberately: they are cited by
name from `LT-1`, from `tests/test_owc_star_parent_cross.py` and from a frozen archive, and
the ledger's copies now redirect in their first line. Every `##` and `###` heading in the
ledger is byte-identical to HEAD — verified by diffing the heading lists, not by eye.

**⚠ RULING, recorded so it reads as decided rather than missed: frozen archives are NOT
repointed.** `docs/history/handoff-status-2026-07.md` cites "Target 2" and "Target 3" by
name (lines 68, 70). `docs/README.md` §2 says a frozen body is never edited and corrections
are appended dated at the top; that wins over "repoint every citer". **A frozen archive's
pointer is provenance** — it records what the citation looked like on the day, and the
names it cites still resolve because they were kept. The same ruling covers
`handoff-migration-map-2026-08.md`, `handoff-status-2026-08.md` and the append-only
ledgers. The one frozen doc that *did* get a correction is
`docs/design/generator-coverage/ttu-negarm-rootcause.md`, and it got one **appended at the
top**, never edited into the body, because its pointer is positional and does not resolve
at all.

**Three citations were ALREADY broken before this change** — fixed here so the split does
not get blamed for them, per the sabotage-procedure habit of controlling the instrument:

```
spec-deviations.md  "the 2026-08-09 sibling (below, `:83`)"   :83 was inside the 2026-08-14 entry
spec-deviations.md  F1 `:1320` / CLOSED `:1336` / `:1360-1367` / `:2292`  (2026-08-09 prior-art table)
                                                              :1320 was inside `## 2026-07-08`
ttu-negarm-rootcause.md  "top entry" x2                       positional into a newest-first log;
                                                              2026-08-14 is top, it meant 2026-08-10
```

All four re-keyed onto dated entry keys and section titles per §5. The `:1320` family is
mirrored verbatim in `tests/test_owc_star_parent_cross.py` and `:83` in
`tests/test_ttu_tupleset_parent_types.py`; both files were owned by other agents this
session and are listed under `Still owed:`.

**One correction the split forced out of hiding.** `ZT-P5`'s star-subject/star-object
divergence has said "**NOT FIXED here**" since 2026-07-26 — and
`WildcardIndex._reject_star_self_edge` fixed it *later the same day*. Nothing pointed that
out for three weeks, and `latent-gaps.md` would have inherited it as a live gap if the
inventory had been transcribed rather than re-verified against the code. It now carries a
dated `>` correction (the idiom this file already used twice) and appears in the new file's
**"Closed — do not re-file from the ledger's tense"** section, which exists specifically to
absorb that failure mode. Same for `Residuals` items 1 and 4, both long closed.

**Lint: a tenth check, `check_doc_links`.** `scripts/handoff_lint.py` validated *nothing*
about doc-to-doc links, and `verify.sh` step 4d resolves `file::symbol` anchors in
`CORRESPONDENCE.md` **only** — it never sees a markdown link, which is exactly why this
split was unguarded. The new check resolves every markdown `.md` link target and every inline
`` `docs/*.md` `` mention in the board files, `CLAUDE.md`, `docs/README.md` and the two
halves. Sabotaged per `docs/sabotage-procedure.md` with the **narrowest plausible**
weakening — the singular/plural typo a rename commit actually produces, not a deleted file
— and it carries an instrument control (a floor on links parsed), because a link checker
that finds zero links passes forever. Literal output is in the check's docstring.

`docs/spec-deviations.md` also finally declares **LIVING**, so `HS-5`'s count drops 7 → 6.
The row's wording is a decrement only — the 2026-08-20 filing says "always-living roots"
without scoping them to `docs/`, and the seven were never enumerated, so narrowing the row
to "`docs/` roots" would have silently changed what `HS-5` means.

**⚠ Adversarial review caught the split committing its own new file's cardinal sin, and
that is the lesson worth carrying.** `latent-gaps.md`'s "Latent, but owned by another doc"
listed the **untainted**-arm `rewriteClosure` dedupe divergence as still latent, quoting
"no corpus exercises it" — transcribed from the `## 2026-07-29` §"Left open, deliberately"
paragraph, whose present tense is 2026-07-29. It closed **2026-08-08**: the dedup landed
and two corpora now exercise the shape (`formal/CORRESPONDENCE.md` §7.2 item 6's "CLOSED
2026-08-08" note; `RemoveOccCount.lean`'s header says the sentence "was FALSE when it was
written"). The genuinely-open item in that same §7.2 item 6 is the **derived**-arm presence
diff on `reconcileKeyDR`'s fold guard — a different arm. So the entry-rule this file wrote
("still true today, verified — not inferred from the ledger's tense") was violated in the
same commit that wrote it, on a bullet that was **new prose rather than a moved citation**,
which is precisely why the citation census could not see it. The bullet now names the
derived arm, and the untainted one joined the "Closed" list. **A completeness census
validates what MOVED; it says nothing about what you WROTE while moving it.**

Three smaller review fixes, all applied: the re-key of F1 traded a wrong line number for
an **ambiguous** one (there are two `## 2026-07-16` entries) and now quotes enough of the
heading to resolve — this mattered because that exact string was queued to be pasted into
a test docstring; the ledger's forward pointer claimed the Target 2/3 section titles were
"unchanged" when only the *keys* were carried; and two newly-authored `>` blockquotes had
copied pin names and the `MAX_TESTS_XFAILED` VALUE into the append-only ledger — a copy
there can never be fixed in place when a test is renamed (`CLAUDE.md` footgun 3, and
`docs/README.md` §1). Both now point at `latent-gaps.md` instead of restating it.

Gate: not run by this session — the orchestrator runs it once. `python scripts/handoff_lint.py`
is clean (10 checks).

The 3 citations `HS-2` left owed in other agents' files were repointed before close:
`tests/test_owc_star_parent_cross.py` (``F1 (:1320, CLOSED :1336)`` and ``(:1360-1367)`` →
dated entry keys) and `tests/test_ttu_tupleset_parent_types.py` (``spec-deviations.md:83``
→ the `## 2026-08-09` entry). **A fourth candidate was reviewed and REJECTED:** that
docstring's ``ZT-P5 bullet 2 / "Target 3"`` citation stays on `docs/spec-deviations.md` —
it is a claim about what the 2026-07-26 probe covered ("never against oracle answers"),
i.e. evidence, which the ledger owns, not live status.

Still owed: **the ten-phase gate has NOT been run to completion on this tree.** `lean` is
green (`holes=0, audits=581, pinned=581`) and targeted suites pass, but `tests-tile:*` will
fail on `BL-1`'s two pins until the fix lands, so a full green run is not achievable and was
not attempted as a green run. The next session must (1) fix `BL-1`, (2) run all ten phases
and confirm with `python scripts/gate_status.py` that they are green **on this tree**, and
(3) run a 3-seed fuzz sweep — `R6-10` is a cascade cache, and a stale-cache defect is
exactly what the stateful ParityEngine machine catches and the unit suite does not.
**Nothing from this session has been committed.** Also owed, smaller: `R6-11`'s inflated
figure should be corrected in all four places it appears before that item is worked, and
`R6-4(a)`'s entry in the perf audit still describes the unsound memo in its body (the
correction is currently only in the new Traps section).

---

## 2026-08-20 — every living-doc citation re-keyed onto `file::symbol`; 8 pointed at unrelated code

rows: `HS-5` (new). **No item progressed** — see the `moved` note at the end.

The session started as a question — is the "cite symbols and headings, not line numbers"
convention actually applied in this repo's notes? The answer had two halves: it is
**written** here already ([`docs/README.md`](../README.md) §5, arrived at independently)
and **machine-checked for exactly one file**, and it had **slipped everywhere else** — 262
citations across nine living docs.

**Two things the local convention already had.** `verify.sh lean` step 4d resolves every
anchor in [`CORRESPONDENCE.md`](../../formal/CORRESPONDENCE.md) by `ast` parse, so a rename
fails the gate rather than rotting — the difference between a convention and a guarantee.
And this repo carries *evidence against* the "stamp it `:441 as of <date>`" escape hatch
that usually accompanies this rule: CORRESPONDENCE §0 records that the previous revision
**did** stamp its citations "as of 2026-07-12", and by 2026-07-26 the zero-trust review
measured **4 of ~45 accurate and ~35 pointing at unrelated code**, §5 100% wrong. A stamp
tells the reader an anchor is OLD, not that it is WRONG, and auditors followed it anyway
into `_write_derived` and `_gc_subject_node`. Ids and section titles are used instead of
markdown `#anchor`s, which is strictly better: a heading reword breaks an anchor, `ZT-P3-5`
survives.

**Eight citations were not stale, they were WRONG.** The measured drift:

```
install_paranoia       cited invariants.py:383       actually :773 (inside _check_derived_invariants)
"delta verifier"       cited invariants.py:322-368   actually ::verify_outbox_deltas (:649) — R6-8 had it right
outside_old_admission  cited FullScope.lean:564      actually :833 (:564 is ::accepts)
"explicit is sticky"   cited core.py:284-287         actually ::ReachabilityIndex.node (:936)
T4 acyclicity          cited core.py:319-342         actually ::_add_edge_locked
oracle ttu_leaf        cited tests/oracle.py:429      that is inside ::direct_leaf; ttu_leaf is :471
test_reg5_...          cited test_lookup_oracle.py:1181-1194   actually :1266
SEMANTICS §7.7         cites offsets 83-304          the I-series now lives at 160-393
```

The `core.py:319-342` one is the sharpest: **CORRESPONDENCE §4's rename ledger flagged that
exact range in July**, and the copy in `spec-deviations.md` was never repointed. A
correction filed in one doc does not propagate to its citers on its own.

Plus **13 pre-existing `::symbol` anchors that never resolved** — the convention followed in
form only: bare method names (`processor.py::_reconcile_subject` →
`::DeltaProcessor._reconcile_subject`), function locals (`::WildcardIndex.check.row`, which
`anchor_check` deliberately does not record), and `corpus.py::residue_rich`, which is a
`SCHEMAS` dict key and was never a symbol. **Writing `::` does not make an anchor resolve** —
that is the lesson worth carrying, and it is now in `docs/README.md` §5 with all three forms.

**One substantive correction, not a re-pointing.** [`formal/HANDOFF.md`](../../formal/HANDOFF.md)
claimed `Inv` is a hypothesis in "**exactly four places**", citing four line numbers — two of
which (`State.lean:813`, `:854`) had drifted onto `putResidue_residue` and `structInv_addEdge`,
neither of which mentions `Inv`. Re-measured with `grep -rn '(h : Inv S σ)\|Inv S σ →'`: it is
**five** `Inv → Inv` preservation steps plus the forgetful `Inv.toStruct`. The finding it
supports — nothing CONSUMES `Inv`, so weakening `negEdgeFree` could not turn anything red — is
unchanged; the count was never load-bearing, but it was wrong, and the rot is now recorded in
situ rather than silently repaired (CORRESPONDENCE §0's rule).

Method: inverted `formal/conformance/anchor_check.py`'s AST walk (line → enclosing
`__qualname__`), converted, then re-verified with **anchor_check's own resolver** — 262
anchors, 0 unresolved. Using the gate's resolver rather than a second hand-rolled one is the
point: the instrument that will judge these anchors later is the one that judged them now.

Left alone deliberately: frozen archives, the append-only ledgers (this file included — its
own entries cite line numbers and are never retro-edited), and CORRESPONDENCE's rename
ledger, which exists *to* record the old citations. Their line numbers are provenance, not
navigation.

**No new gate phase — the user's call, and the right one.** The resolver is cheap and already
exists, but extending it means every prose doc must stay parseable forever, and prose
legitimately wants to quote a snippet without minting an anchor. Recorded here because the
next session will be tempted: the reason is not cost, it is that `docs/` is not `CORRESPONDENCE.md`.
Note `P13` (CORRESPONDENCE claim-rot gate) is the adjacent LATER row and is *not* this.

Known and deliberately left: **12 bare parenthetical line numbers** in
[`perf-round6-audit`](../perf-round6-audit-2026-08.md)'s verifier blockquotes
(`ttu_expand (1328, 1331, ...)`). Those read as evidence-of-inspection on a stated date
rather than navigation, and the doc retires to `docs/history/` when the round closes. They
will still rot; `R6`'s owner may strip them when it lands.

Filed `HS-5`: seven living docs declare **no liveness state** though `docs/README.md` §2 says
every doc declares one in its first lines. Frozen archives all comply — the gap is
specifically the always-living roots.

`⚠` budget: this session added one trap to `formal/HANDOFF.md` (9 → 10).
`scripts/handoff_lint.py` is **clean (9 checks)** — it budgets the root board, which sits at
**10 with zero headroom**. The next trap on `HANDOFF.md` must take §4's demotion move, not
add an eleventh line.

Gate: ten phases COVERED on this tree. Only `lean` was re-run (rc=0, holes=0, audits=581,
pinned=581); step 4d `524 parsed, 524 resolved`; step 4e all four counts match. The nine
pytest tiles key on `t2c`, which excludes `*.md`, so they stayed green — **`GS-2` paying off
exactly as designed**: 152 s instead of ~25 min. Docs-only, so no fuzz sweep.

**On `moved`:** no row's `moved` was touched. This session changed citation formatting inside
`P3`'s block and `R6`'s audit doc but progressed neither item, and `moved` exists so that an
old date on a `NOW`/`NEXT` row reads as neglect. Touching it for an anchor edit would erase
that signal — `P3` has been `NOW` since 2026-08-16 without proof progress, and the board
should keep saying so. Flagged rather than done silently, per the Rhythm's own rule about
skips that leave no trace.

Still owed: nothing.

---

## 2026-08-18 — R6-19 filed, and filing it corrected the number: 25.4% cum, 2.0% self

rows: R6.

Executing the standing debt `2026-08-17e` left: the one measured number in round 6 that
belonged to no candidate, `bulk_backfill._reconcile_subject_edge` at **25.3%** of a bulk
build. It is now **`R6-19`** in
[`docs/perf-round6-audit-2026-08.md`](../perf-round6-audit-2026-08.md), marked in its own
header as **not a product of the 2026-08-15 audit** — no finder wrote it, no verifier
adversarially reviewed it — because that doc's entries are otherwise verbatim audit output
and a filing that borrows their authority would be the wrong kind of tidy.

**Filing it under yesterday's own rule changed what it says.** §"A MEASUREMENT is an
assurance step too" says ask what a number means before acting on it, so the share was
re-run rather than copied: `profile_r6_write --target bulk --bool-scale 300`, box idle,
nothing else running. It reproduces — and decomposes:

```
_reconcile_subject_edge : 145,560 calls   tottime 0.382 s ( 2.0%)   cum 4.80 s (25.4%)
_reconcile              :   1,050 calls                             cum 6.94 s (36.9%)
```

**The 25.3% was cumulative; the function's own time is 2.0%.** So the honest item is not
"a quarter of a bulk build sits here" — it is **this call site is the denominator**:
145,560 / 1,050 = **~138.6 bare-entity audit members per object reconcile**, each paying a
full `plan.check_fn` evaluation and a per-subject `_residue_state` read, with
`_member_check` / `_derived_check` / `_stored_tupleset_subjects` all *underneath* it. Any
in-function optimization has a **2.0% ceiling**. Had it been filed from the cum share alone
it would have read as the round's third-biggest target; it is not one.

Code-verified structure went in with it, each line labelled read-vs-measured: step (4)'s
audit loop (`:797-802`) re-walks a superset of what step (2) already evaluated; for a
star-covered bare entity `check_fn` provably runs twice on the same subject and `ctx`
(`:751` and `:689`) though **that rate is unmeasured on this workload**; and
`_residue_state` at `:691` is per-object state re-read per subject, plainly hoistable.

⚠ Recorded against the obvious fix: a `(subject) → bool` memo spanning steps (2) and (4)
is **not** obviously sound. `_BulkEvalContext` reads live `bf` state, and both `_reconcile`
(`:794`) and `_reconcile_subject_edge` (`:707`) write residues between the two evaluation
points — so the memo owes an argument that no interleaved write changes the answer, not
just matching arguments. The item's stated order is therefore: measure the duplicate rate
(may close it as declined), hoist the residue read (needs no soundness argument), then
design the memo. Overlap flagged both ways — `R6-14` already measured this neighbourhood
at a 5.0% ceiling and was **declined**, and `R6-10` is the incremental twin of the same
memo idea.

Citers updated in the same commit (`perf-next-round.md`, the board's `R6` block, the audit
doc's measured section); the profile doc keeps its original "(context)" line as the
provenance the correction is against. No code touched — the profile re-run is read-only.

Still owed: nothing.

---

## 2026-08-17e — the sabotage procedure now binds measurements, not just checks

rows: none (method lesson only; `R6`'s and `P3`'s state is unchanged).

A read-back session: check what the previous three sessions left unrecorded, then do
whatever small thing was owed. **The board was clean** — `R6`'s ten-to-land order, its five
declines with the number behind each, the three unreachable ids and the unfiled
`_reconcile_subject_edge` finding are all in the `R6` item block and
[`docs/perf-next-round.md`](../perf-next-round.md); `P3` is still `NOW` and still blocked on
the proof-design adjudication rather than on coding; `2026-08-17d` already carries the four
instrument corrections. Nothing was missing from the *state* record.

**What was missing was the rule.** `2026-08-17d` recorded the four corrections as session
narrative — the star-closed `R6-2` schema, the cascade probe on the bootstrap path, the
`R6-12` cross-cycle aggregation, and the `GS-2` harness that rewrote its own subject in text
mode — and [`docs/sabotage-procedure.md`](../sabotage-procedure.md), the living home for
exactly this class of lesson, scoped itself to *assurance steps*: tests, floors, pins, gate
phases. A benchmark was not on that list. Four verdicts in one session turned on instruments
that ran on nothing and reported cleanly, so per `docs/README.md` §"Archive the status, keep
the method" the lesson belongs in the living doc, not only in a dated entry that is read for
provenance.

**The edit.** The procedure's opening scope now names measurement instruments alongside
checks, and a new section — §"A MEASUREMENT is an assurance step too" — carries the
five-second test (*what would this number look like if the probe ran on nothing?*), the
four corrections as a table with what each reported versus what it was doing, and three
generalisations: wrong-workload dominates wrong-arithmetic (three of four ran correct code
over an input that never reached the studied function); **right answer by luck is still a
failed instrument** (`R6-2` reached NOT MOTIVATED both times — only the second run had
measured it); and an instrument can mutate its own subject, so anything that writes to the
tree it measures owes a baseline re-read after restore. The mechanical form is the one
`benchmarks/profile_r6.py` already uses and the reason two of the four were caught at all:
print the denominator next to every share, because 0/0 renders as a clean small percentage.

Pointers, not restatements, per the one-home rule: `docs/README.md`'s routing row widened to
"checks **and measurements**", and `perf-next-round.md`'s measurement-hygiene bullet links
the new section instead of copying it.

No code, no backend, no modeled algorithm touched — markdown only, so under `GS-2` the nine
pytest tiles keep their verdicts and this costs one `lean` run.

Still owed: nothing. (Standing, from `2026-08-17`: the unfiled
`bulk_backfill._reconcile_subject_edge` finding — 25.3% of a bulk build — still has no
`R6-*` id of its own. It is recorded in three places and is not lost; filing it is the next
`R6` session's first cheap act.)

---

## 2026-08-17d — GS-2: the gate's tree id is per-phase now, so a docs edit costs 50s not 25min

rows: GS-2 (new, closed and retired same session).

Third task of the session, and it came straight out of the second one's friction. Twice in
one session a **markdown-only edit** invalidated nine green pytest tiles: the tree id was a
content address over *every* tracked file, so appending one ledger paragraph moved it and
`gate_status --require-green` correctly said NOT COVERED. Correct, and ~50 minutes of gate
time re-earning verdicts that could not have changed. The user pushed back on the second
rerun — *"if you already ran the full 9 tiles and changed some docs I don't think that
warrants a full rerun?"* — and they were right: that is the letter of the rule beating its
intent, and **a rule whose cost is that visible is one sessions start overriding from
memory**, which is the exact habit `GS-1`'s ledger was built to retire.

**The fix is per-phase input scoping.** A phase's id now covers only the inputs that phase
can read: `t2a:` (everything) for `lean`, `t2c:` (everything minus `*.md` and
`benchmarks/`) for the nine pytest tiles. `verify.sh` passes `--phase`, so the recorder and
the reader still cannot drift. **`lean` keeps the full scope and must** — steps 4d/4e/4f
resolve `CORRESPONDENCE.md` anchors, scan prose globs, and lint both boards plus this
ledger — so a docs-only edit still costs one ~50 s `lean` run. That coupling was already
documented; what changed is that it no longer drags the tiles with it.

**The exclusion is a fail-open surface, so it was verified rather than argued.** Every
excluded input is one that can no longer invalidate a cached green — this repo's house
failure mode wearing a performance costume. Checked before writing any code: no collected
test reads markdown (every `.md` in `tests/` and `formal/conformance/test_*.py` is a
docstring mention; the only real reader is `doc_counts.py`, which runs from step 4e, and no
collected test imports it); **no `.md` file exists under `tests/` or `formal/conformance/`
at all**, so no golden, fixture or corpus can be markdown; and nothing there imports
`benchmarks` (the dependency runs the other way). Fixtures, goldens and corpora stay in
scope by construction — only two extensions are named — and an unrecognised phase falls
back to the **widest** scope, so a new or mistyped phase over-invalidates rather than
under-invalidating.

**Sabotage** (`docs/sabotage-procedure.md`), eight probes, each mutating one real file and
restoring it: backend `.py`, test `.py`, `.fga` fixture, `.txt` golden and a new untracked
`.py` all move BOTH ids; `.md` (edited and newly created) and `benchmarks/*.py` move the
all-scope id ONLY. Eight for eight, ids restored to baseline exactly. End-to-end on the
real ledger: append one line here → `lean` STALE, `conf-tile:2/5` still green; restore →
both green. Now permanent as 8 tests in `tests/test_gate_status.py`, each exclusion paired
with a control proving the scope still covers its neighbourhood — **an exclusion test alone
would pass just as happily if the code scope covered nothing**, which is why
`test_an_empty_scope_is_refused_rather_than_certifying_everything` exists too.

⚠ **Instrument correction #4 of the session, and the most embarrassing: the probe harness
mutated its own subject.** The first sweep reported two false FAILURES. Cause: it read and
rewrote files in **text mode**, so on Windows an LF-only file came back CRLF, the baseline
id drifted mid-sweep, and the markdown/benchmarks probes looked broken. It also left
`formal/audited_theorems.txt` stat-dirty (content identical after normalisation — verified
by `git diff --numstat`, then restored). Re-run with `read_bytes`/`write_bytes` — what
`tree_id`'s own `_file_fingerprint` uses — all eight behaved. **Four instrument corrections
in one session** (R6-2's star-closed schema, the cascade probe on the bootstrap path, the
R6-12 cross-cycle aggregation, and this one). Every one changed a verdict; not one was
caught by a test.

Versioning: `t1` → `t2`, and the scope tag is mixed into both the digest and the prefix, so
a code-scoped id cannot match an all-scoped row and no pre-existing row can match anything
— the same discipline that retired the pre-2026-08-17 `<sha>+<hash>` scheme. Floor raised
895 → 903; `FINAL_REVIEW.md`'s counts block regenerated (the documented tests → lean
coupling). Gate: all ten phases green on this tree.

Still owed: nothing.

---

## 2026-08-17b — HS-4 paid: two landed blocks retired verbatim, formal/HANDOFF 517 → 482

rows: HS-4 (closed and retired).

Asked for the cheap items, then a handoff cleanup, a green gate and a push. Perf work
(`R6`) was explicitly excluded — other agents were running test suites on other repos, and
a measurement pass under that load would produce numbers worth nothing. That exclusion is
the right call independent of scheduling: `R6`'s own entry condition is a motivating
measurement, and a noisy one is worse than none because it *looks* like evidence.

**`HS-4` was the only genuinely owed item, and it was owed twice.** `formal/HANDOFF.md`
stood at **517 lines against the 520-line ceiling** (`scripts/handoff_lint.py::MAX_LINES`,
enforced as `verify.sh lean` step 4f), so the next session to append a dated block — the
normal way that file is written — would have turned the gate red on a doc edit. The debt
was recorded under `Still owed:` in `2026-08-16g`, carried unexecuted through `2026-08-17`,
and this session is the third to see it.

**What moved, and why those two.** The two oldest dated blocks in the reverse-chronological
run, both fully landed, went verbatim to
[`formal/history/handoff-dated-blocks-2026-08-17.md`](../../formal/history/handoff-dated-blocks-2026-08-17.md)
(FROZEN banner, `HS-3` precedent — copy, never condense):

* **2026-08-09** — leg 7 steps 3 and 4a. Landed in `8291c3a` / `41b7029`. Its one open
  question, the §11.3 `pushDelta` fork, was *answered* by the 2026-08-14 block (branch
  (α)), which stays live in `formal/HANDOFF.md`. So the block carried no unanswered state.
* **2026-08-08** — the `rewriteClosure` dedup leg, closed as `CORRESPONDENCE.md` §7.2
  item 6.

Checked before cutting, because the citation-key rule (`docs/README.md` §5) is what makes a
move safe: **nothing outside `.scratch/` cites a dated block of `formal/HANDOFF.md`.** The
tree cites `formal/history/PROOF_STATUS.md` by date key instead, and both retired blocks
have fuller entries there under the same keys — this file was the fast path, not a unique
home. A one-line pointer replaces them in place and the routing table gains a row.

**A new archive rather than an append to the 2026-08-16 one.** That file is declared
`FROZEN 2026-08-16` and its header enumerates *three* retired zones; appending would have
falsified its own header and edited a frozen body, which `docs/README.md` §3 forbids
outright. Retirements get their own dated archive.

**Deliberately NOT done: raising the ceiling.** The lint's own comment says a ceiling is
raised as a deliberate reviewed act, and the whole point of 520 is that it fires on the
first appended layer. 517 → **482** buys ~38 lines, i.e. one more dated block, which is
the intended cadence: the next session to fill it retires the next landed block. The
2026-08-15 block is the obvious next candidate — it is already marked SUPERSEDED — but it
is deliberately kept for now because it carries the revised 4c-i/4c-ii step order that
`P3` is actively working from, and 4c-ii has not landed.

**The ratchet had to move with it, and that is the part worth carrying.**
`MAX_BOLDCAPS['formal/HANDOFF.md']` was **9**, set on 2026-08-16 at the exact measured
residue. Three of those nine offenders lived inside the 2026-08-09 block and left with it.
Leaving the budget at 9 would have handed the next session three free bold-caps lines — the
identical defect the original sabotage caught when the budget was first set to 18 and
lowering it by one left the check *silent*. Re-measured and lowered to **6**, with the
provenance in the source. Sabotage, per [`docs/sabotage-procedure.md`](../sabotage-procedure.md):
at budget **6 → 0 violations**, at **5 → 1 violation** — so the ratchet sits exactly on the
residue and has no slack. `python scripts/handoff_lint.py` → `handoff_lint: clean (9 checks)`.

**Method note.** The retirement is a pure move — the diff of the archive against the deleted
span is empty by construction, because the text was copied, not retyped. That is the whole
reason `HS-3` wrote "never condense" as a rule: a condensed retirement is unreviewable, since
a line diff cannot distinguish "shortened" from "lost".

Still owed: nothing.

---

## 2026-08-17c — R6 measured: R6-6 lands first, R6-2 declined, R6-3 unreached, nothing built

rows: R6 (measurement pass done, block rewritten).

Same session as `2026-08-17b`, second task. The user asked whether a perf scan was on the
board and authorised it **conditional on the box being quiet** — other agents had been
running suites on other repos. Checked before starting: 12 logical cores at 1.8–11%, and
per-process CPU-delta sampling showed the two stray `pytest -q` processes from
`audio-workspace` consuming **0 CPU-seconds over a 6-second window**. The user then stopped
them outright, so the wall-clock column is trustworthy and not just the counters. **No perf
work would have been legitimate under load** — `perf-next-round.md`'s hygiene rule is
explicit that contention has corrupted bench numbers before, and a noisy measurement is
worse than none because it looks like evidence.

**Nothing was implemented.** The round's declared next act was measurement, and the
deliverable is verdicts, not patches:
[`benchmarks/results/R6_PROFILE_2026-08-17.md`](../../benchmarks/results/R6_PROFILE_2026-08-17.md),
instrument [`benchmarks/profile_r6.py`](../../benchmarks/profile_r6.py) — cProfile plus
counters keyed to each candidate's own claim, over the reviewed `scale_bench` datasets.

**Six of eighteen settled.** `R6-6` **MOTIVATED and cheapest**: exactly **4.00 `node_v4`
point SELECTs per `check`** against 0.75 for the already-batched edge probe, so the fix
takes the hottest read surface **4.75 → 1.75 statements, −63% round trips**, with no Lean
change. `R6-5` **promoted from medium**: 22,410 ORM rows built (**32.7%** of profiled time)
to read three or four columns; `lookup_reachable` + `_classify_ids` are **52%** of boolean
lookup — the largest single measured block in the pass. `R6-4` **MOTIVATED**: **30.1%** of
every boolean lookup and **193 `json.loads` per lookup** over only **100** residue rows,
and being O(#derived objects) that share grows with the store. `R6-1` **MOTIVATED with a
caveat that is the point of the entry**: 74.1 `check` calls per `lookup` and **91.4%** of
lookup wall time, with `lookup` degrading 2.5× from scale 400→1600 while `check` stays
flat — but that proves `check` DOMINATES, *not* that sharing ELIMINATES, and the naive
shared memo is a correctness bug by the audit's own counterexample. Prototype before
landing. `R6-2` **recommended DECLINE**: 24.2% of a surface already 13–30× faster per call
than `lookup`, the feared quadratic star-population re-materialization absent (roaring
`_starpop` ~1 µs even at 20,000 population), against the price of a Lean model change plus
fuzz. `R6-3` **UNREACHED**: `_instances_of_type` called **0 times** across both set-engine
profiles, gdrive's object-wildcard shapes included — round-3's N7 deferral now measured
instead of assumed.

**The method lesson, filed in the results doc: a probe that exercises nothing reports a
verdict.** The first `R6-2` probe used `set_engine_bench`'s wide/star schema and printed a
clean `NOT MOTIVATED, 18.8%` — while returning **0 members** and running **2 unions per
expand**. On a star-CLOSED relation the answer lives in `stars`/`neg` and `direct_expand`
folds a bitmap leaf in ONE union, so the per-element fold the finding is *about* never
executed. The re-run on gdrive `lookup_reverse` (the surface the finding's own verifier
named) reaches the same verdict for a reason it actually measured. Both are kept in the
write-up: this is `docs/sabotage-procedure.md`'s "control your instrument as well as your
subject" landing one level down, on a benchmark rather than an assurance check — and it
would have been invisible had the wrong probe happened to say MOTIVATED.

**Scope, second half.** The first write-up stopped at the read paths and said so. The user
then asked whether `R6-7`…`R6-18` were measurable at all, whether the harness could be
written, or whether some upper bound already showed the effort was not worth it — and the
answer was that most of the plumbing existed (`build_graph(paranoia=, commit_every=)`,
`build_index(bulk=True)`, `stmt_bench`'s statement listener). `benchmarks/profile_r6_write.py`
followed, and **all eighteen are now measured**; `R6-17` needed no run, being a duplicate of
`R6-3`. Verdicts, added to the same results doc as Part 2:

* **`R6-10` is the round's headline — 59.8% of incremental boolean write+cascade time** in
  one function (16,690 calls to `_stored_tupleset_subjects`). Larger than anything on the
  read side.
* **`R6-7` is confirmed by a GROWTH CURVE, not a share**: per-commit cost rose **14.14×**
  from the first quartile to the last over 336 commits. A share could not have separated
  "expensive constant" from "grows without bound"; the quartile split does, and it settles
  the O(N²)-over-a-run claim. Gate-only (`PARANOIA_FULL` is the `tests/` default and never
  production), with `check_invariants` overall at **64.1%** of a paranoid build.
* **`R6-16` is the clearest waste in the round**: exactly **1.00 outbox row per closure
  edge** on a schema with no derived relations — 14,868 rows nothing consumes, retained
  permanently. Must be co-designed with `R6-7`/`R6-8`, which read those rows as paranoia's
  worklist.
* **`R6-18`: 53.1% smaller on disk** (57.7 → 27.0 bytes/row, VACUUMed file-backed A/B). The
  claim is about physical layout, so it was measurable exactly without touching production
  models.
* **Five declined on an upper bound** — `R6-15` (the entire topo sort is **0.9%** of a bulk
  build, so a perfect fix cannot beat that), `R6-12` (**1.00×** intra-run re-reconcile),
  `R6-14` (**5.0%**), `R6-2` (24% of a non-bottleneck) — and **three are unreachable**:
  `R6-3` = `R6-17` and its bulk twin `R6-13`, 0 calls each. **That is five items of
  implementation effort the round will not spend, which is the reopening rule paying for
  itself.**
* **Unfiled finding:** `bulk_backfill._reconcile_subject_edge` is **25.3%** of a bulk build
  and belongs to no candidate. Recorded as needing its own id rather than being folded into
  a neighbour.

**Three instrument corrections, all of which changed a verdict.** (1) The `R6-2` probe on a
star-CLOSED relation, described above. (2) The first cascade probe profiled `build_graph`,
which bootstraps through `backfill()` — the OFFLINE path — so `reconcile_subject` ran **0
times** and `R6-11`/`R6-12` returned INCONCLUSIVE against code that never executed; the
measured path had to be `GraphBackend.apply`'s write → `run_cascade(wm)` → commit. (3) The
`R6-12` counter then aggregated across cycles and printed **15.00× re-reconcile**, which was
the same key touched by successive *writes*, not the intra-run duplication `_bumped` is
about — per-cascade counting gives **1.00×**. Same failure in three costumes: **a probe that
exercises nothing, or counts the wrong scope, still reports a confident verdict.** None of
them was caught by a test; all three were caught by asking what the number could mean.

**Housekeeping — the carried "nine tile phases" debt is DISCHARGED, and this entry is where
that is said.** `2026-08-16d`, `2026-08-16e` and `2026-08-16g` each closed with
`Still owed: ... the nine tile phases before push`. Those entries are append-only and are
never retro-edited, so the debt is retired forward rather than by editing them: the
`2026-08-17` session ran all ten phases green, and this session ran all ten green twice more
(once after `HS-4`, once after this measurement pass), each time verified on the current
tree by `scripts/gate_status.py --require-green`. **Nothing about tile phases is
outstanding.** Anyone grepping `Still owed:` will still hit those three lines — that is the
cost of an append-only ledger, and the reason a later entry has to name what it discharges.

Still owed: nothing.

---

## 2026-08-17 — GS-1 closed: the tree id is a content address, and two fail-opens beside it

rows: GS-1 (closed and retired).

Asked whether `GS-1` is a correctness bug, and whether there are any correctness issues
to fix. The answer to the first is **no** — and the honest answer to the second turned
out to be *yes, in the same function, twice, in the dangerous direction*.

`GS-1` as filed is fail-**safe**. Committing changed the id although the content did
not, so a full green gate read stale one second later: it under-reports freshness, it
never certifies ungated code, and it is correctly not counted against the banner's
"live correctness bugs: 0" (which is about the two backends, not `scripts/`). But
`tree_id` hashed `git status --porcelain` + `git diff HEAD`, and that has two
fail-**open** consequences, both reproduced against the real repo at HEAD `0cddd4a`:

* **Untracked file contents were never read** — porcelain *names* them. Creating
  `tests/zz_probe.py` moved the id to `0cddd4a+0e72b085`; rewriting its contents left
  it at `0cddd4a+0e72b085`. Wider still: an untracked directory collapses to one
  `?? dir/` line, so `zz_probe_dir/two.py` left `0cddd4a+36649ed0` exactly where
  `zz_probe_dir/one.py` had put it. Write a new test file, run the ten phases green,
  edit it before `git add` — `--require-green` still said COVERED.
* **A failed `git status` was coalesced to `""`.** Untracked-only dirt leaves
  `git diff HEAD` empty as well, so *one* failed command sufficed: dirty tree, git
  healthy → `0cddd4a+1a7b0c67`; same tree, `git status` down → `0cddd4a+clean`,
  byte-identical to a genuinely clean tree's id and therefore a match against its
  green rows.

**And a third defect, in the reader, that the board had misattributed to `GS-1`.**
`report` kept the last row per PHASE, so re-running one phase on another tree
discarded the green row earned on yours. Against the real ledger: ten `PASSED` rows
existed for `b53bfc9+1eabb8af`, `lean` had since been re-run twice elsewhere, and the
report said `lean: missing` / `NOT covered` for a tree the ledger recorded as fully
green. Keyed by `(phase, tree)` the same rows give `lean: PASSED` / `COVERED: True`.
So yesterday's banner sentence — "committing changes the tree id even when content
does not (row `GS-1`)" — named a real defect that was not the one biting it.

**The fix.** `tree_id` is now `t1:<12 hex>`, a content address over
`git ls-files --cached --others --exclude-standard` (45 ms over 329 files / 8 MB), it
carries no commit id at all, and it **raises** rather than returning a plausible id
when git or the filesystem cannot be read. `verify.sh` still degrades such a run to
`tree=unknown` — the ledger never changes a verdict — but now WARNs, because `unknown`
matches nothing and a green phase that buys no coverage is exactly the outcome an
operator should not discover at push time. Verdicts are keyed by `(phase, tree)`. The
`t1:` prefix versions the algorithm, so every pre-existing row is structurally
incapable of matching a new id rather than accidentally capable of it.

**The root cause was the absence of tests, not any one of the four defects.**
`gate_status.py` is cited by `CLAUDE.md`, `verify.sh` and the runbook, and had no
tests at all — the one artifact whose job is answering "is the gate green" was itself
outside the gate. `tests/test_gate_status.py` (+16, floor raised 879 → 895) closes
that. Suite-level sabotage, per [`docs/sabotage-procedure.md`](../sabotage-procedure.md):
reinstalling the legacy `tree_id` and per-phase keying verbatim gives **`10 failed, 6
passed in 3.57s`**, and the six survivors are exactly the controls — tracked-file
edit, tracked-file deletion, the gitignored-scope assertion, the red-rerun negative
control, legacy-id non-collision, and `coverage`'s mixed-K refusal. Attributable red,
not blanket red; that distinction is what separates "these pin the four defects" from
"this file no longer imports".

**A consequence worth carrying: a tracked file can no longer quote its own tree id.**
Under content addressing, writing the id into the banner changes the id. That is not a
limitation to work around but rule 3b arriving mechanically — the ledger is the one
home for the figure, and prose points at it. The banner now says which phases ran and
tells you to ask `scripts/gate_status.py`, and it will be *right* after the commit
rather than stale, which is the whole point of the change.

**Method note.** Two read-only subagents ran the survey passes (which docs go false;
which conventions bind), and both earned their cost by catching things a from-memory
pass would not: `HANDOFF.md` sits at exactly its 10-`⚠` budget with a zero-tolerance
bold-ALL-CAPS ratchet, `tests/` forbids `skipif` outright so the git-dependent tests
had to be written as hard requirements, and `verify.sh` was silently swallowing the
new loud failure. No subagent edited anything.

Still owed: nothing from this session's own write-back. Carried forward from
`2026-08-16g`, still true and still unexecuted: ⚠ **`formal/HANDOFF.md` is at 517
lines against its 520 ceiling**, so the next session's dated block will trip
`verify.sh lean` step 4f. It owes a retirement pass (move one landed block verbatim to
`formal/history/`, per the `HS-3` precedent — never condense). This session did not
add a block there, so the ceiling was not tripped and the debt is unpaid, not resolved.

---

## 2026-08-16g — leg 7 4c-ii attacked before it was built: Route A refuted, and P3's criterion is weak

rows: P3 (blocked on an adjudication, block rewritten); P14 (entanglement recorded).

Asked to start leg 7 with subagents to hold context down, then run the full gate and push.
Method: a read-only fan-out — four maps of the tree, one synthesized 17-step edit plan, two
adversarial passes over that plan (formal house rule 2) — and then **every load-bearing
claim re-verified by hand**, because a subagent's confident citation is exactly the kind of
thing this repo has learned not to trust. Formal house rule 6 held: no subagent proved or
edited anything. Full detail: [`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md)
`2026-08-16c`; the scope doc's resolution is §11.8.

**No Lean file was modified, and that is the finding, not a shortfall.** Three cells of the
plan are refuted, two of them by running code:

* **Route A is refuted.** `ReconcileComplete.lean:164` needs a `ReachedByRules σ S T`
  witness for a `writeRulesRaw`-built σ, and `LeafRules.lean:461::lrV_writeRulesRaw_edges_ne`
  already machine-checks that those states' edges differ. The surviving branch weakens
  `UntaintedShadow`, a slice of `P14` — whose deps close a cycle `P3 → P14 → P4 → P3` that
  the board cannot express. That adjudication, not coding, is what 4c-ii is blocked on.
* **The own-key premise is backwards.** On the `ComputedOnly` fragment the leaf list is
  EMPTY rather than multi-element (`Leaf.lean:401`, `:551`), so `writeLeg_own_key_dirty`
  goes FALSE and wants a non-emptiness premise, not the `WF` the plan proposed.
* **`P3`'s completion criterion was weak, and the control is what saved it.** Commenting
  out the two-line P6 branch (`extractor.py:236-237`) — no Lean change whatsoever — makes
  `doc_counts.measure()` publish exactly the target block
  `{'P6': 0, 'compared': 265}`. The same probe leaves the state gate at **`19 failed, 37
  passed`** with `edge only in PYTHON : ('user','mallory','...','') -> ('doc','d1','viewer.1','')`.
  So the numbers alone certify nothing and **numbers ∧ `conf-tile` green** is the real
  criterion; both boards now say so. A board criterion that a two-line Python edit satisfies
  is the house failure mode wearing a board's clothes. (Bonus: §11.5 predicts the divergence
  arrives as `only in LEAN model`; Python-first gives the mirror.)

Four smaller corrections, each verified in the tree: the `FoldAdmits` lockstep is **24**
spelled-list sites, not the 7 `write` constructors; `Audit.lean:314` pins
`reachedByRules_of_admitted`, so `Audit.lean` is an edited file of this step and no pin
regeneration substitutes; `_MIN_LEDGER_ROWS`/`_MIN_LEDGER_STACKED = 19/19` are asserted
before the golden read, over exactly the multiplicity leg 4c-ii moves; and
`derived_arm_multiplicity.json` is owed a *derived* expectation rather than a re-recording
(sabotage-procedure rank 2 — a generated golden cannot witness a change to the tree that
generates it).

The 17-step plan is deliberately NOT filed: three of its cells are wrong in the places that
cost the most, and filing it would file the wrong plan.

**Method note worth carrying.** The fan-out was worth it, and the adversarial pass was worth
more than the maps: the maps' citations were accurate (I spot-checked ~10 and found none
wrong) but their synthesis was confidently wrong three times, and only the attack lenses
caught it. Also, one attacker over-claimed — it called the criterion "hollow, produced in
full by step 14 alone", and the gate control shows it is *weak*, not hollow. Both halves had
to be run to know which.

**A defect in yesterday's ledger, found by using it** (row `GS-1`): the tree id is
`<short HEAD>+<sha1 of porcelain+diff>`, so **committing changes it even though the content
does not**, and ten green rows earned on the pre-commit tree read as stale one second
later. The fix is to content-address the id (hash tracked + untracked-non-ignored file
contents, which is invariant under `git add`/`commit`); it is deliberately NOT done here,
because changing the algorithm invalidates every existing row and would need all ten phases
re-run to restore them — i.e. it must be its own commit, run its own gate, and not ride
along at the end of an unrelated session.

Still owed: the nine tile phases were run at the end of this session — see the banner.
⚠ **`formal/HANDOFF.md` is at 517 lines against its 520 ceiling**, so the next session's
dated block will trip `verify.sh lean` step 4f. It owes a retirement pass (move one landed
block verbatim to `formal/history/`, per the `HS-3` precedent — never condense).

---

## 2026-08-16f — verify.sh leaves a trace now: gitignored run ledger + gate_status.py; the tee footgun sabotaged

rows: none (user-assigned tooling task; no board item was open for it).

Asked whether the gate produces logs, because the board's `Still owed:` line — "the nine
tile phases before push" — is carried by human memory across sessions. It did not: every
phase printed to stdout and exited, and `BUILD_LOG` is a `mktemp` deleted by the EXIT trap.

**The archaeology that looks like it should work does not, and that is worth recording
separately from the fix.** `.pytest_cache` was the only surviving artifact:
`v/cache/nodeids` had today's mtime and 1449 ids (941 `tests/` + 508 `formal/`) — one
collection, with no phase, no verdict and no tree attached — and `v/cache/lastfailed`
carried six failing node ids, also written today. The second one reads like evidence of a
red tree and is not: pytest only rewrites `lastfailed` when the failing SET changes and it
**retains entries for tests that did not re-run**, so it is cumulative, not a verdict.
Probed all six directly: **every one is `ERROR: not found`** — they name parametrizations
and tests that no longer exist (`test_features_are_unique_to_this_fixture` is the one
`verify.sh`'s own floor comment records as deleted on the 867→879 review). So: no evidence
of red, and no evidence of green either. That is exactly the gap.

**What landed.** Two artifacts per run under a gitignored `.gate-runs/`: the phase's full
output verbatim, and one appended row in `ledger.tsv` (started · duration · phase ·
`PASSED`/`FAILED`/`INCONSISTENT` · tree id · observed counts · log name). Phases call
`gate_fact` as they observe a count, so a FAILED row still carries what the run got to.
`scripts/gate_status.py` reads it back and answers the actual session-opening question —
which phases are green **on the tree in front of me** — with `--require-green` as a
mechanical push check. Runbook §4 documents it; `CLAUDE.md`'s gate bullet points at it.

**The tree id is one function with two callers, deliberately.** `verify.sh` shells out to
`gate_status.py --tree-id` rather than computing `<short HEAD>+<sha1 of porcelain+diff>`
in shell. A recorder and a reader that derive "same tree" differently would report a
freshness that never existed, and it would look right. Its limits are written down where
they can be read: it does not see untracked file contents, anything gitignored (a matching
tree id does **not** mean the same Lean build), or the environment.

**The sabotage found a defect rather than confirming a good check** — the first one did,
which is the whole argument for the procedure. Property: *a row saying PASSED means the
phase really passed, and a phase that fails still exits nonzero even though its output now
goes through `tee`.*

| sabotage | observed |
|---|---|
| control, clean `conf-tile:6/100` | `EXIT=0`; row `PASSED … collected=495 selected=5 conf_passed=5 conf_xfailed=0 conf_skipped=0 conf_floor=5` |
| `MIN_CONF_ALL=495` → `99999` | `EXIT=1` — the tee did not eat it — but **no ledger row at all** (before the fix; after it, `FAILED … rc=1`) |
| genuinely red pytest in a tile (temp failing test, `conf-tile:96/100`) | `1 failed, 4 passed in 0.95s` → `FAIL: conf (pytest rc=1)`, `EXIT=1`, row `FAILED … rc=1 collected=496 selected=5` |
| delete `GATE_REACHED_END=1` | `EXIT=1`, row `INCONSISTENT`, `FAIL: verify.sh is exiting 0 WITHOUT its final PASSED banner` |

Row 2 is the finding. The trap was written beside `BUILD_LOG=$(mktemp)`, ~230 lines below
the floor-consistency check it needed to cover, so a real gate failure produced a log file
and no row — the reader could only call it "incomplete" while the script knew it had
FAILED. The trap now precedes the first `exit` in the script body, `GATE_TREE` is snapshot
as soon as `$PY` resolves, and the comment at the trap says what the sabotage cost.

**Two things the design refuses on purpose.** The ledger never changes a verdict — every
write is best-effort and non-fatal, because a full disk should lose the record, not the
gate. The single exception runs the other way: `rc=0` without the final banner is recorded
`INCONSISTENT` and **forced nonzero**, since a gate that exits 0 without finishing is the
house failure mode, not a logging concern. And coverage is judged per-K (some single K
with all K tiles green), not against a hard-coded ten — the throttled-box recipe
`conf-tile:1/8 … 8/8` is just as complete, while tiles at mixed K provably leave holes.

Also worth knowing: `.gate-runs/` **must** stay gitignored, because the tree id hashes
`git status --porcelain` — a tracked ledger would change the tree id on every run and
every row would be stale on arrival. `gate_status.py` warns loudly if it ever sees that.

Still owed: unchanged from `2026-08-16d`/`e` — the nine tile phases before push. `lean`
re-run green here (it lints the board edits in this session). No Python behaviour changed;
the 2026-08-14 3-seed fuzz sweep still stands.

---

## 2026-08-16e — B1 was already closed and nobody noticed: both halves proved 2026-07-28/08-04, now verified

rows: B1 (closed; id stays retired).

Asked to look into `B1` — the `w3cJobValid_enumJob2D` star-freeness hole — and close it if
it was not done. It was done. The proof landed three weeks ago and the record never caught
up, so this session is verification and bookkeeping, not proof work.

**What the old verdict said.** Written 2026-07-27: "STILL OPEN, but RECLASSIFIED … needs a
decision, not a proof session", the decision being between a star-filter inside
`storedDirectSubjects` and a new fragment clause banning wildcard restrictions on derived
Direct arms. Its clause (ii) was `grep -rn "w3cJobValid_enumJob2D" formal/lean/` returns
**nothing** — the lemma does not exist, so no landed theorem depends on it".

**What is actually in the tree.** The E-chain plan §B took *both* options the next day, and
both landed. `storedDirectSubjects` half: the faithfulness star-filter, giving
`storedDirectSubjects_name_ne_star` with no fragment premise (leg 1, 2026-07-28).
`edgeHolders` half: `reachedByW3d2_Rnode_source_name_ne_star_d` under the new `W4Fragment`
clause `directArmsConcrete`, discharged at the call sites (leg 2, 2026-08-04). Both feed
`w3cJobValid_enumJob2D`, which exists at `CascadeStrataAssemble.lean:290`, is audited and
axiom-clean, and reaches the final theorems through `enumJobs2At_valid` (four call sites)
and `FullScope.lean`'s `W4Fragment.directArmsConcrete`. So both parts of clause (ii) are
false today.

**Sabotage rather than trusting the docstrings.** The star-filter was defeated in place
(`fun s => s.name != STAR` → `fun _ => true`) and `lake build` of
`ZanzibarProofs.GraphIndex.CascadeStrataEnum` went red at `CascadeStrataEnum.lean:634`, the
`simpa` closing `storedDirectSubjects_name_ne_star`. That half is held by the type checker.
Restored and re-verified green. **The check was worth running because a comment forty lines
away says a nearby filter "still COMPILES with the filter defeated"** — that is the
`freshDirectCands` presence diff, which genuinely is measurement-pinned, and reading the two
as one filter would have produced the opposite conclusion.

**The carry is unchanged and stays declared:** `directArmsConcrete` excludes a shape Python
admits (`define approver: [user, user:*] but not banned`). It is a vacuity boundary, not an
unsoundness one — on such a schema `W3cJobValid` fails for every enumerated job at the key,
so the operational chain has no cascade constructor there — and the clause is
machine-confirmed load-bearing by the leg-1 sweep.

**The transferable lesson, and it is the same one twice in two days.** A finding is closed
where it is RECORDED, not where it is fixed. `Audit.lean` had said "the
`storedDirectSubjects` half of the Board-B1 star-freeness hole is closed" since 2026-08-04
while the board block said "STILL OPEN"; earlier today the same class of gap appeared as an
id retired on one board and a finding left open on the other. Both are now closed, and both
boards say the same thing. Recorded in `formal/HANDOFF.md`'s `B1` block and as a dated note
on the E-chain plan, whose §B predicted this upgrade and was right.

Still owed: unchanged from `2026-08-16d` — the nine tile phases before push. `lean` was
re-run after the sabotage restore and is green. No Python behaviour changed.

---

## 2026-08-16d — the redesign closes: formal/HANDOFF.md 1010 to 471 (HS-3), the board lint is gate step 4f (HS-1)

rows: HS-1, HS-3 (both closed and retired); HS-2 promoted to NEXT; P15–P19 added; P3, P6,
R6 pointers untouched.

Two sessions' worth of items in one. Started as an audit of whether the executed handoff
system matches [`handoff-redesign-2026-08.md`](handoff-redesign-2026-08.md) — it mostly did
— and the three deltas found are fixed, then both remaining design steps were executed.

**The audit's findings, all repaired.** (1) The board charter claims to rank *every* open
item and did not: `FINAL_REVIEW.md` §4 ranked five items with no row. Verified against the
pre-migration file — they were never on the board, so this was inherited, not lost in the
migration; but the new charter's completeness claim made it false. Now rows `P15`–`P19`,
and §4 opens with the reverse map so the two cannot drift apart silently. `P17` is the one
worth noticing: bulk build/backfill is the DEFAULT `build_index` path, has no Lean
counterpart at all, and its only net is a Python-vs-Python identity gate. (2) The leg-7
scope doc still opened "SCOPE, DEFERRED" above its own ACTIVE-PLAN banner, so a cold reader
following `P3`'s read-first list met a false status first. (3) §7's cheap half had run
three-quarters — the `★` retirement landed, the emphasis conversion never did — and nothing
recorded the gap.

**`HS-3`, the deep half.** `formal/HANDOFF.md` 1010 → 471. Retired zones went to
[`formal/history/handoff-status-2026-08-16.md`](../../formal/history/handoff-status-2026-08-16.md)
**verbatim, not condensed** — the previous session's own audit found that condensing is
where content dies and a line-diff cannot see it, so this copied rather than summarised even
where a duplicate was verified to exist. The staged theorem ladder (35 rows, ~15 filenames
that appear in no other table) moved to `ARCHITECTURE.md`, its declared home. The retired
"Status" section was the actively wrong one: it said "the formal-verification arc is
finished" and "what remains is optional" while leg 7 was mid-flight at the top of the same
file, and carried a conformance count in prose that the same file's house rule 3 forbids.

**Eight dead inbound pointers, found by sweep and repointed.** Five live files cited a
`HANDOFF "The next task"` section that has not existed for some time — including four Lean
sources — and `RestrictBase.lean` cited a "HANDOFF Step A" that never survived at all. The
file's own line 4 pointed at that same dead section. `formal/README.md` advertised a theorem
table that was about to stop being there, which is the one case where the rot was two-sided.

**`HS-1`, the lint in the gate.** `verify.sh` lean-phase step **4f**, not an eleventh phase:
it is pure Python with no toolchain, exactly like 4d/4e, and a new phase would have meant
propagating a phase count through `CLAUDE.md`, the runbook and both boards. Three checks
added: bold-caps ratchets, root-ledger-not-behind-`PROOF_STATUS`, and `rows:`-cited ids
resolving to real board ids. Consequence now documented in the runbook beside the
`tests/`-reddens-`lean` footgun: **a HANDOFF-only edit reddens `lean`.**

**The bold-caps sabotage failed, and that was the whole value of running it.** The budgets
were set to 1 and 18; lowering one by a step left the check SILENT, because the true counts
after a paragraph-scoped trap exemption were 1 and 9. A budget above the measured value
guards nothing — the same defect as a floor with headroom. Both are now exact, the root
board's single offender was cleaned to a hard zero, and `formal/HANDOFF.md` keeps 9 as
declared debt in the `MAX_TESTS_XFAILED` idiom. Two exemptions were separately controlled:
stripping every trap badge took offenders 9 → 28 (so the exemption exempts something real,
not everything), and a real id in the bogus id's position kept `check_ledger_row_ids` silent
(so it fires on the id, not the line shape).

**Full `moved`-vs-ledger cross-validation was attempted and rejected**, not deferred. The
`2026-08-16c` entry covers ~20 rows with the prose clause "every open item re-keyed onto the
new board" rather than an id list, so the reverse direction false-fails most of the board on
the very commit that created the ledger. The safe direction shipped instead; the reasoning
is in the check's docstring so nobody re-files it.

**Method note.** The survey ran as four read-only agent fan-outs. Two disagreed about
whether the theorem table was still in `formal/HANDOFF.md`; I opened the file rather than
believing either, and the confident negative was wrong — it had inferred from the routing
table instead of reading. That is the second time in three sessions a fan-out's confident
negative has been wrong, which is now the strongest argument for the runbook's rule that a
fan-out discovers candidates and does not adjudicate them.

**Left deliberately unresolved:** the two boards disagree about `B1`. The root board retired
the id; `formal/HANDOFF.md` still verdicts the finding open, and `CascadeStrataAssemble.lean`
says only the `storedDirectSubjects` half is closed. Recorded in both places as a question
rather than adjudicated, because I could not verify the `edgeHolders` half either way.

Still owed: the full ten-phase `verify.sh` run before push — `lean` was re-run because step
4f is new, but the nine tile phases were not, and the gate contract is all ten before a push.
No Python behaviour changed (docs, one shell step, one lint script), so no fuzz sweep.

---

## 2026-08-16c — the handoff-system migration executed: HANDOFF.md is a board, the ledger and the lint ship

rows: HS-1, HS-2, HS-3 (new); every open item re-keyed onto the new board.

Executed [`docs/handoff-redesign-2026-08.md`](../handoff-redesign-2026-08.md) §9 steps
2–11 against the survey evidence in
[`handoff-migration-map-2026-08.md`](handoff-migration-map-2026-08.md). Step 1 was
already done; **step 12 (the `formal/HANDOFF.md` deep half) is deliberately NOT in this
session** and is seeded as board row `HS-3`.

**What the migration found that the design did not know.** Each is recorded where it was
fixed, not here; this list exists so the *class* of defect is visible.

1. **A guard that would have been deleted along with its only true statement.** Step 4
   moves four footguns from the board into `CLAUDE.md`, each verified present in its
   durable home first. Three were. The fourth was not: `docs/gate-runbook.md` stated
   `MAX_TESTS_XFAILED` as "**1**, not 0, today", while `formal/verify.sh` sets it to `0`
   and `tests/test_postgres_ha.py` has carried `NO XFAILS REMAIN (2026-07-27)` ever since
   that date — there is not one xfail marker left in `tests/`. The runbook had described a
   state that ended three weeks earlier, and the board's copy was the only correct one.
   Fixed in the runbook *before* the board's copy died. **This is the entire reason step 4
   is phrased as verify-then-delete.**
2. **Ten of fourteen demoted rows had non-self-sufficient pointers.** The design gives
   `LATER`/`HOLD`/`SOMEDAY` rows no item block, on the invariant that the pointer target
   carries the traps and the completion criterion. Audited row by row, it mostly did not:
   `SD-1`'s target never mentioned either scope rejection; `P12` pointed at the bug being
   predicted *about* rather than the probe; `P8`'s target said the witness was "designed"
   without recording the design. All ten targets were repaired in place before the rows
   were demoted. Demoting them as written would have deleted the items.
3. **A trap that cited a symbol which has never existed.** The board carried "⚠ do not
   extend `test_fixture_earns_its_place` corpus-wide" — there is no such test, and never
   has been; it was a paraphrase of a docstring sentence. An unenforceable trap. Re-anchored
   to the two real gates (`test_corpus_pair_coverage_does_not_regress`,
   `test_fga_corpus_feature_coverage_does_not_regress`) and promoted to a standing trap so
   the next one gets grepped before it is written down.
4. **`P7`'s entire cost analysis existed only in gitignored `.scratch/`.** Not in any
   clone, not recoverable by another session. Transcribed into `PROOF_STATUS.md` as a dated
   correction; also now a standing trap.
5. **Stale figures inside the block that boasts of removing figures.** The archived
   "What landed 2026-08-16" recorded "audits 520 → **573**, anchors 471 → **497**". The
   machine-checked block generated in that same commit says **581** and **524**. `ZT-P3-5`,
   three lines below a banner congratulating itself for carrying no figures. Recorded as a
   correction on archiving; not carried forward.
6. **The severity-sign rule had no runbook home.** The single most transferable output of
   the RC1/RC2 arc ("probing only the positive direction mis-classifies severity by one
   sign") survived only in prose that was about to be archived. Lifted into
   [`sabotage-procedure.md`](../sabotage-procedure.md) *before* the archiving, along with
   six other method lessons — three of which were likewise homeless.
7. **My own new lint check failed by passing.** `check_frozen_banners` first tested
   `'LIVING' in head` as a plain substring, which every frozen archive satisfied via its
   prose "provenance, not a **living** document". It reported clean on exactly the files it
   was written to police, hiding six real violations; anchoring the match to the bold
   declaration form took the count from 8 to 15. Caught only because the house procedure
   says to sabotage a check before believing it. See `scripts/handoff_lint.py`'s docstring
   for the literal output of all six sabotages.
8. Two smaller ones: the migration map's line coordinates had drifted +7 (the board item
   that *ordered* this migration was added after the survey ran, so map §A carries no
   disposition for it — blocks were addressed by first line, never by the map's numbers);
   and `handoff-status-2026-08.md` already had a `## Retired 2026-08-16` section, so the
   design's "the existing section is the unlettered first batch" was false. The new section
   is keyed `2026-08-16b` rather than retro-editing an archive heading.

**Verification.** `python -m formal.conformance.doc_counts --check` green after every step
from 3 on. All ten `verify.sh` phases PASSED, exit codes captured directly rather than
through a pipe. `scripts/handoff_lint.py` green. `HANDOFF.md` went **986 → 202 lines**.

**The migration was then audited for loss, and the audit found real gaps.** A line-level
survival check over the pre-migration file confirmed the archived zones were faithful —
the only archived lines missing anywhere are exactly the ten that step 6 deleted as
verified duplicates. But line-identity says nothing about the *condensed* zones, where
content was rewritten rather than copied, so those were audited claim-by-claim against the
current tree. What that turned up, all now repaired:

* **Leg 7 step 5 was left unranked.** The scope doc calls it "the deepest single change";
  the new board's chain went `P3` → `P4` → `P5` and named step 5 nowhere. In a file whose
  charter is "the only file that ranks open items", that is the worst class of loss — the
  work is still described, but nothing points at it. Now board row **`P14`**.
* **Two facts existed nowhere afterwards**: the `RestrictBase` occurrence correction
  (19, not the 18 still recorded in a frozen 2026-08-10 block — and it is one of the two
  modules holding the CONSUMED sites `P7` must size), and the note that this machine's
  PostgreSQL cluster is stopped-but-RETAINED, so `start` is seconds rather than a cold
  `initdb`. Restored to `PROOF_STATUS.md` and `gate-runbook.md` respectively.
* **Two board pointers were simply wrong**: `DW-1` cited `CORRESPONDENCE.md` §2, which is
  the set-engine model and contains none of it; `HS-3` cited the design's §7 for a "step
  12" that is numbered in §9.
* **`docs/README.md`'s own citation rule cited a line number that had already drifted** —
  in the very paragraph explaining that a line-number citation is wrong the day the file is
  edited. It now cites by section, and says so.
* **Three items kept their warning but lost its reason**: the fixture-triple trap lost the
  exemption-list/failed-twice rationale and kept only a cost argument (so anyone who
  accepted the cost objection was no longer warned off the bad fix); `SD-1` lost the
  corpus measurement that made its deferral evidence-backed rather than assumed (48 schema
  files, 22 compile, 0 rejections — so a future session could re-file work already done and
  retired); and the declined store-level write quota had no entry in
  `perf-next-round.md`'s dead-end list, which is exactly where row `R6` sends a perf
  session.
* **Renaming "Working rhythm" to "Rhythm" dangled two code comments** that cite the section
  by name. The rule *number* `3b` was deliberately kept byte-stable for them; the section
  name was not. Both comments repointed.

The lesson worth carrying: **condensing is where content dies, and a line-diff cannot see
it.** Verbatim archiving verified itself trivially; every real loss was in a zone that had
been rewritten in good faith.

**Method note.** The recon ran as read-only agent fan-outs rather than being read into one
context. Two agents disagreed about whether `docs/design/` exists; both were checked by hand
before either was believed, and the one with the confident negative was wrong. Per
[`docs/subagent-fanout-runbook.md`](../subagent-fanout-runbook.md), a fan-out discovers
candidates and does not adjudicate them.

Still owed: nothing skipped. `HS-1` (wire the lint into `verify.sh`) and `HS-3` (the
`formal/HANDOFF.md` deep half, redesign step 12) are seeded board rows, not omissions.

---

## 2026-08-16b — perf round 6 opened (18 unmeasured candidates); the handoff-system redesign designed and approved

rows: R6 (opened).

Filed [`docs/perf-round6-audit-2026-08.md`](../perf-round6-audit-2026-08.md): a 24-agent
two-phase audit of both backends, 18 findings each adversarially verified against the
code, 0 refuted, plus 16 unverified lower-ranked leads. **Nothing landed and nothing is
measured** — per the reopening rule in
[`docs/perf-next-round.md`](../perf-next-round.md) every item still owes a motivating
measurement, and round 5 declined two plausible candidates on a fresh profile. One fix
sketch was refuted by counterexample while its finding stood (R6-1: the naive shared memo
is a correctness bug).

Designed [`docs/handoff-redesign-2026-08.md`](../handoff-redesign-2026-08.md) and had it
reviewed by three adversarial critics, then approved by the user (its §11 records the
decisions). The survey evidence was persisted first, as
[`handoff-migration-map-2026-08.md`](handoff-migration-map-2026-08.md) — migration step 1.

Still owed: execute §9 steps 2–11 (done in `2026-08-16c`); step 12 remains.

---

## 2026-08-16 — leg 7 step 4c-i landed: leaf-provenance rules, zero recompile cone; ttuStarFree (iv) unblocked

rows: P3, P6, P7.

Formal session — **the detail is in
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md) `## Session
2026-08-16`**, which is the authority for this entry. In short: the leaf-provenance rule
layer landed with a measured zero recompile cone; the 4c-pre allocation model was refuted
three more times before anything was built on it, once by an instrument that was itself
blind; and `ttuStarFree` part (iv)'s standing blocking decidability question is answered
NO-BLOCK, machine-checked.

Still owed: leg 7 steps 4c-ii + 7 (must co-land), 4b, 5, 6; `ttuStarFree` parts (ii) and
(iii), and part (iv)'s remaining effort now that it is unblocked.
