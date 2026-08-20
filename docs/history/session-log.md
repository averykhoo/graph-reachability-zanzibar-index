# session-log.md — the append-only root session ledger

**LIVING — append-only.** This file lives under `docs/history/` for filing reasons
only; it is *not* frozen provenance, and the frozen-banner rule does not apply to it
(`scripts/handoff_lint.py` excepts it by name). It is the root analogue of
[`formal/history/PROOF_STATUS.md`](../../formal/history/PROOF_STATUS.md), which keeps
the *formal* detail; a formal-heavy session writes the detail there and points at it
from here.

**The rules** (conventions are defined once in [`docs/README.md`](../README.md)):

* **Newest entry first.** One entry EVERY session, without exception — the board's
  `moved` column is only meaningful if every session leaves a dated trace.
* **Entry key: `## YYYY-MM-DD[letter] — <headline>`.** The letter disambiguates
  same-day sessions (`2026-08-16`, `2026-08-16b`, …). The key is a stable citation
  target: entries are **never retro-edited**. A later entry names what it refutes.
* **The headline is one line and feeds the banner** in [`HANDOFF.md`](../../HANDOFF.md)
  verbatim, so keep it under ~120 characters including the key.
* **`rows:`** names the [`HANDOFF.md`](../../HANDOFF.md) board ids the session touched.
* **`Still owed:`** closes every entry. If the session ran short of context and skipped
  a write-back step, list the skipped actions here *verbatim* — the next session
  executes them before its own work.
* Body length is up to the writer; no cap. Links are written relative to the repo
  root, so from this file they resolve against `../../`.

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
