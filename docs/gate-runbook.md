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
  + `tests/` + conformance ≈ 20+ min — blows the cap. Run it **phased**
  instead (§2): `verify.sh lean | conf-tile:1/5 … conf-tile:5/5 | tests-tile:1/4 …
  tests-tile:4/4`, each of which fits the cap with room to spare (worst conf tile
  ≈ 235 s, worst tests tile ≈ 120 s, of the 600 s cap).
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

### 1. Backend + differential suite — `verify.sh tests-tile:I/K` (4 × ~2 min)
`pytest tests/ -q` in one shot is **over the cap** (~10:30 on 2026-07-14/15 at 531
tests; it is several hundred more now — re-measure, never quote). Since 2026-07-27
`tests/` is a **phase of `verify.sh`** rather than a hand-typed `pytest` command:

```bash
bash formal/verify.sh tests-tile:1/4; echo "EXIT=$?"
bash formal/verify.sh tests-tile:2/4; echo "EXIT=$?"
bash formal/verify.sh tests-tile:3/4; echo "EXIT=$?"
bash formal/verify.sh tests-tile:4/4; echo "EXIT=$?"
```

**95–165 s per tile at K=4**, measured warm on the dev box 2026-07-27 (190–191 of
762 node ids each, including a fresh `--collect-only` of the whole directory; the
full four-tile pass was 96 + 145 + 100 + 164 s) — well under a third of the cap, so
K=4 has real headroom; raise K on a throttled box. With a PostgreSQL DSN exported the
collection grows and the tiles resize themselves — the tiling is derived from the
live collection, so nothing here needs editing when the count moves.

Why this and not the old two-way `--ignore` split: the `--ignore` recipe had **no
count floor, no skipped/xfailed parse, and no proof that a tile collected
anything** — it was an agent reading a summary line. `tests-tile:I/K` reuses the
conformance machinery verbatim, so `tests/` now gets: a fresh collection asserted
`>= MIN_TESTS_ALL`, the partition-arithmetic tile-size check, `passed >= the tile's
exact size`, a hard zero on `skipped`/`xpassed`/`deselected`, a **declared** xfail
budget (`MAX_TESTS_XFAILED`, see the floors table), and a real exit-code assertion.
Deliberately **do not** hard-code per-tile counts here: the tiling is structural, so
the numbers move with every added test and a stale number in this file is worse than
no number.

**If a tests tile fails on `N skipped`, find the skip and remove its CAUSE** — do
not reach for a budget. The intended pattern for an environment-gated leg (the
Postgres HA suite) is to **drop it at COLLECTION** when `ZANZIBAR_TEST_DSN` is
unset, not to collect it and skip at run time; a tolerated skip is how coverage
leaks, and it is the reason the parse is zero-tolerance.

**The one exception, and it only exists WITH a DSN.** Three tests in the shared HA
modules are SQLite-only *by nature* — two pin the `StaleRead` pinned-snapshot path,
one pins "a replica never sees torn state" — and PostgreSQL at READ COMMITTED gives
a reader no stable snapshot at all, so those properties do not exist there to test.
They `skipif` on `ZANZIBAR_TEST_DSN`, so `MAX_TESTS_SKIPPED_ON_RDBMS=3` applies only
when a DSN is exported; the default SQLite gate keeps its hard zero. A budgeted
outcome also counts toward the tile's floor, so budgeting something never quietly
shrinks what had to pass.

### 1b. The PostgreSQL leg (opt-in, and worth running)

```bash
bash scripts/pg_local.sh start                 # prints ZANZIBAR_PG_DSN=...
export ZANZIBAR_TEST_DSN=postgresql+psycopg2://postgres@127.0.0.1:55432/zanzibar_test
"$PY" -m pytest tests/test_postgres_ha.py -q; echo "EXIT=$?"
bash scripts/pg_local.sh stop                  # or `destroy` to remove the cluster
```

A throwaway user-space cluster (conda-forge binaries; no system install, no service,
loopback-only, non-default port). **On this machine the cluster is STOPPED but
RETAINED** (as of 2026-08-16): `start` brings it back in seconds rather than doing a
cold `initdb`, `destroy` removes it entirely, and nothing in the default gate needs it. `ZANZIBAR_PG_REQUIRED=1` turns a missing or
unreachable DSN into a hard ERROR rather than a skip — use it whenever you intend the
server leg to have actually run. Worth running for anything touching locking,
watermarks, isolation, or multi-instance state: it found three real bugs the first
day it existed, one of them a live authorization fail-open, on code that had been
reviewed and gated for months.

**Capture `$?` directly** — piping through `tee` returns tee's exit code (0) and
masks a failure. ⚠ **`tail` does this too, and it is the one that keeps biting.**
`bash formal/verify.sh lean 2>&1 | tail -12` reports `tail`'s status, so a FAILED
phase looks like exit 0 — and if it is followed by `&& <next phase>`, the chain
happily continues past the failure. This bit the 2026-08-10 session (a genuinely
`4 failed` run reported exit 0) and bit again on 2026-08-11 (a FAILED `lean` phase
reported exit 0, caught only by reading the output rather than the status). Use
`bash formal/verify.sh <phase> > /tmp/p.log 2>&1; rc=$?` and branch on `$rc`.
**This is already written down twice below and was hit anyway — if you are reading
it now, that is the whole warning.**

★ **A tests-ONLY change still requires re-running `lean`.** This is not obvious and
was reasoned wrong on 2026-08-11: "I touched no Lean, no production code, and
nothing under `formal/conformance/`, so `lean` cannot be affected." It can. Step
**4e** compares `FINAL_REVIEW.md`'s generated counts block against the tree, and
that block contains the live `tests/` collection count and `MIN_TESTS_ALL`. So
adding or removing a single test in `tests/` makes the `lean` phase FAIL until you
run `python -m formal.conformance.doc_counts --generate`. The coupling runs
tests → lean, which is the opposite direction from the one you would guess.
Conformance genuinely is independent of `tests/`; `lean` is not.

★ **A HANDOFF-ONLY change also requires re-running `lean`** (new 2026-08-16). Step
**4f** runs `scripts/handoff_lint.py`, so editing `HANDOFF.md` or
`formal/HANDOFF.md` — adding a board row, flipping a `pri`, appending a ledger
entry — can turn the `lean` phase red without a line of code changing. Same
surprising direction as the `tests/` coupling above: a docs-only edit reddens the
Lean phase. Run `python scripts/handoff_lint.py` yourself first (it is Rhythm step
0 and takes under a second) rather than discovering it after a Lean build.

### 2. Lean + conformance — the split `verify.sh` gate
`verify.sh` takes a **phase argument** so the whole formal gate (its 5 steps) runs
as cap-fitting commands an agent can execute unattended. Warm timings on the
dev box (`lean` re-measured 2026-07-27):

```bash
bash formal/verify.sh lean           # steps 1-4: lake build + hole scan + zcli + axiom audit
                                     #            + audit identity + statement + DEFINITION pins
                                     #            + CORRESPONDENCE.md anchor pin      (29 s warm)
                                     #            + FINAL_REVIEW.md counts pin     (+30 s)
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
conf phase run without it FAILs loudly rather than skipping vacuously). The tiles
are order-independent. Every phase must print `PASSED`. Together, `lean` + the five
`conf-tile` phases + the four `tests-tile` phases (§1) == a full `verify.sh all`.

- **Coverage is complete, by construction — and now also asserted.** A
  `conf-tile:I/K` phase collects `formal/conformance/` fresh, asserts the collected
  total is `>= MIN_CONF_ALL` (465 today), then runs the node ids whose 0-based
  collection index is `≡ I-1 (mod K)`. Every collected node lands in **exactly one**
  tile, so the K tiles partition the directory: a newly added file, corpus or
  parametrization is automatically in exactly one tile, nothing is named by hand, and
  the tile's size is cross-checked against the partition arithmetic
  (`floor((total-I)/K)+1`) so a tiling that is not a partition FAILs. Each tile's own
  pass floor is its exact size — every selected test must pass.
- **The global floor is per-phase.** Because *every* tile re-asserts the 465-test
  collection floor, you cannot lose conformance coverage and still get a green tile —
  even if you only ever run one.
- **A split pass is not a weakened pass.** Every phase carries the same anti-vacuous
  guards as the one-shot — olean layout-drift guard, `#print axioms`
  observed==expected **plus a hard-coded 460 floor, an IDENTITY pin and a headline
  STATEMENT pin** (Lean), zcli-binary preflight,
  the collection floor, zero `skipped`/`xfailed`/`xpassed`/`deselected`, and
  `passed >= floor` (conformance). So the green phases ≡ a green `verify.sh all`;
  there is no reconstructed-pass hole to manage.
- **Legacy phases still work.** `conf-heavy` (`test_conformance_remove.py`, **175 s**
  measured 2026-07-26, floor `MIN_CONF_HEAVY` = 96) and `conf-rest` (the dir MINUS that
  file via `--ignore`, floor `MIN_CONF_REST` = 369) also tile the directory — 96 + 369
  = 465 = `MIN_CONF_ALL`, and `verify.sh` checks that identity on its own floors at
  startup. `conf-heavy` is a handy quick
  single-file rerun. **`conf-rest` is AT OR OVER the cap** (579 s measured
  2026-07-19g/07-26 at 250-276 tests, and the whole dir is ~800 s of work) — that is
  why the `conf-tile` phases exist. Do not use `conf-rest` unattended; use the tiles.
- **Where `conf-rest`'s time actually goes.** `test_conformance_enum.py` — 6 tests,
  **~380-475 s** (exhaustive small-scope enumeration) — is the hog, not
  `test_conformance_remove_graph.py` (21 tests, ~27 s) as the 2026-07-19g note
  guessed. Everything else in `conf-rest` is ~165 s combined. The `conf-tile` split
  interleaves those 6 tests across the **five** tiles (K=5 is the recommended default
  above; the "four" this sentence used to say was left over from an earlier K and
  contradicted the recommendation 40 lines up), which is what balances them.
- **`bash formal/verify.sh` with no arg** still runs all 5 steps in one shot
  (~18-20 min) — for an uncapped shell or CI only; it does NOT fit the cap.

#### The hard-coded floors in `verify.sh` (gate self-defence, 2026-07-26/27)
Before these, the gate could stay green while the assurance surface eroded: deleting
`#print axioms graph_correct` from `Audit.lean` was invisible (the "expected" count
was grepped out of the very file being audited), and deleting `test_conformance_graph.py`
outright was invisible (the only conformance assertions were `skipped == 0` and
`passed > 0`). These numbers now live in `formal/verify.sh`, all asserted with `-ge`
so **adding** theorems/tests never fails the gate (the one `-le` is called out):

> ⚠ **This table deliberately carries NO values.** It used to, and they rotted: on
> 2026-08-11 it still said `MIN_CONF_ALL` 465 and `MIN_TESTS_ALL` 762 while the tree
> was at 494 and 857. That is `ZT-P3-5` ("every doc number is stale and nothing
> enforces any of them") recurring in a doc that, unlike `FINAL_REVIEW.md`'s counts
> block, has no generator and no step-4e check behind it — and it is this project's
> own rule being broken (`CLAUDE.md`: *do not restate gate counts in prose*).
> **Read the live values out of `formal/verify.sh`**, which is the only place they
> are asserted. What each one MEANS does not rot, so that is all this table keeps.

| constant | what it guards |
|---|---|
| `EXPECTED_MIN_AUDITS` | `#print axioms` reports observed from `Audit.lean` |
| `MIN_PINNED_AUDITS` | names in `formal/audited_theorems.txt` — the identity pin can't be gutted |
| `MIN_PINNED_DEFS` | rows in `formal/headline_definitions.txt` — likewise, so emptying the golden can't make the definition pin compare nothing |
| `MIN_CONF_ALL` | tests collected from `formal/conformance/` |
| `MIN_CONF_HEAVY` / `MIN_CONF_REST` | the legacy split's floors (checked to sum to `MIN_CONF_ALL`) |
| `MIN_TESTS_ALL` | tests collected from `tests/` |
| `MAX_TESTS_XFAILED` | (**`-le`**) declared xfail budget for `tests/` only — see below |
| `MAX_TESTS_SKIPPED_ON_RDBMS` | (**`-le`**) dialect-only skips, and ONLY when `ZANZIBAR_TEST_DSN` is set; the default SQLite gate keeps a hard zero |
| `MIN_SCANNED_LEAN_FILES` | project `.lean` files the hole scan must cover |
| `MIN_FIXTURES` (`tests/test_compile_snapshot.py`) | `.fga` fixtures the byte-identity snapshot gate runs on |
| `MIN_PY_ANCHORS` / `MIN_LEAN_ANCHORS` | `CORRESPONDENCE.md` anchors found (in `anchor_check.py`) |
| *(no constant)* | step **4e** compares `FINAL_REVIEW.md`'s generated counts block against the tree exactly; there is no floor to lower, only a regeneration to perform |
| `MAX_LINES` / `NEXT_MAX` / `WARN_BUDGET` / `HEADLINE_MAX` / `MAX_BOLDCAPS` (in `scripts/handoff_lint.py`, step **4f**) | the board files' capacities: line ceilings, at most three `NEXT` rows, the trap budget, the ledger-headline cap, and the bold-caps ratchets. All are set at measured values with in-file provenance; `MAX_BOLDCAPS` is a ratchet — lower it when you clean a line, never raise it |

**Lowering any of them must be a deliberate, reviewed edit to `verify.sh`** — and
should be justified in `formal/history/`. Raising them is free and encouraged when
counts grow. The conformance floors are cross-checked arithmetically against each
other, so you cannot bump one and leave a hole in another.

**The budgets, and why they are not hard zeros.** `MAX_TESTS_XFAILED` applies to
`tests/` and nothing else; `formal/conformance/` keeps a hard zero because a
divergence there is a bug to fix, not a marker to add. `CLAUDE.md` *does* endorse a
strict xfail as the legitimate way to PIN a genuine divergence in `tests/` while it
is being fixed (that is how X1–X4 were tracked). A blanket zero would hand the first
person who follows that convention a red gate and tempt them to delete the pin — a
self-inflicted version of the erosion this whole mechanism exists to stop. Raising
the budget is a deliberate act: point the commit at the filed divergence
(`docs/spec-deviations.md`) and **lower it again when the pin is flipped**. A
budgeted xfail counts toward the tile's pass floor (it ran and it asserted);
`xpassed` stays a hard zero for both suites, because an xpass means the pin is
stale — and the repo-root `pytest.ini` sets `xfail_strict = true`, so a stale pin
also fails locally.

⚠ **Corrected 2026-08-16 — this paragraph used to open "It is `1`, not 0, today."**
That was false from 2026-07-27, when the one pin it named
(`tests/test_postgres_ha.py::test_open_instance_races_a_concurrent_commit`) became a
plain test; that module has carried `NO XFAILS REMAIN (2026-07-27)` ever since and
there is not one xfail marker left in `tests/`. **The value is deliberately not
restated here** — it lives in `formal/verify.sh` and nowhere else, for exactly the
reason the floors table above carries no values. The hazard that retired pin described
is still real and still covered: `TupleSource.__init__` reads the watermark and *then*
rebuilds — atomic under a pinned SQLite-WAL snapshot, not at READ COMMITTED. It fails
loud rather than answering wrongly, and there is no one-line fix: reading the watermark
*after* the rebuild turns the loud failure into a silent skip. `MAX_TESTS_SKIPPED_ON_RDBMS`
works the same way and is documented in §1 above. Both budgeted outcomes count
toward the tile's pass floor, so budgeting one never quietly shrinks what had to
pass — otherwise the budget would just move the red one line down.

#### Step 4 is no longer a COUNT: the identity, statement + definition pins (2026-07-27, ZT-P2-5)
An audit count proves nothing about *which* theorems are audited or *what they say*.
Two erosions used to keep the gate fully green:

1. delete `#print axioms graph_correct`, add `#print axioms Nat.add_comm` — count
   unchanged, so nothing noticed;
2. restate `theorem graph_correct : True := trivial` — it **builds**, the hole scan
   scans TOKENS not statements so it finds nothing, and the audit prints a clean
   report.

Three checks now run inside the `lean` phase (all cheap; total ~2 s):

- **4a IDENTITY** — the live `#print axioms <name>` extraction must be a **superset**
  of `formal/audited_theorems.txt`. Adding audits is free; swapping a headline
  theorem out for a filler one FAILs with the missing name. Regenerate deliberately:
  `bash formal/regen_audit_pin.sh`.
  Additionally, a **headline** theorem reporting *"does not depend on any axioms"* is
  treated as suspicious and FAILs — a real theorem over this development is routed
  through `propext` / `Classical.choice` / `Quot.sound`, so axiom-freedom is the
  signature of a vacuous restatement. (12 non-headline lemmas legitimately report no
  axioms, which is why the rule is scoped to the headline set.)
- **4b STATEMENT** — `formal/conformance/statement_pin.py` extracts each headline
  theorem's statement text (binders + `:` + conclusion, up to the top-level `:=`)
  from the Lean source and diffs it against `formal/headline_statements.txt` (26
  statements: T0a/T0b, T1, T4, T5, T2a/T2b/T3/T6, the Phase-6 driver theorems and the
  `W4Witness*` non-vacuity witnesses). The **proof** is not pinned — refactoring a
  proof is normal work; changing what is CLAIMED is not. Regenerate deliberately:
  `"$PY" formal/conformance/statement_pin.py --generate`.
  *Honest scope:* this pins surface syntax **of the statement only**. On its own it
  could not see a statement hollowed out from underneath — which is what 4c exists
  for.
- **4c DEFINITIONS** — the hole 4b could not see, closed 2026-07-27. 4b records
  `graph_correct`'s hypothesis as `(hF : W4Fragment S T)` **by name**, so weakening
  that structure changes what the theorem claims while its pinned line stays
  byte-identical *and* no declaration name changes, so 4a is blind too. `statement_pin.py`
  now also diffs `formal/headline_definitions.txt`: the full text of every project
  declaration the 26 statements depend on, **transitively**, plus the ambient
  `variable` / `open` context of the files hosting them (a dropped `[Fintype V]` is
  the same attack). 139 rows / 132 declarations, floor `MIN_PINNED_DEFS`.
  *Why unbounded depth:* resolution stops at the project boundary by construction, so
  the closure converges on its own — measured 58/36/17/5/7/3/3/2/1, settling at depth
  9. Replayed over the tree's busiest fortnight (34 commits), levels 3–9 contributed
  **zero** firings beyond levels 1–2, so unbounded costs the same maintenance as
  depth-2 and covers 38 more definitions. Every would-be firing was a real meaning
  change. Regenerate both goldens together:
  `"$PY" formal/conformance/statement_pin.py --generate`.
  *Still invisible:* the project boundary (a Mathlib/toolchain change to what
  `List.erase` means — that is `lean-toolchain`'s job); definitional-vs-textual
  equality in both directions; and anything requiring ELABORATION, so a definition
  vacuous on its own terms passes with its text intact. That last one stays the job
  of the `W4Witness*` non-vacuity theorems and the conformance suite.
- **4d ANCHORS** — `formal/conformance/anchor_check.py` resolves every
  `` `file::symbol` `` anchor in `formal/CORRESPONDENCE.md` (397 today: 272 Python by
  `ast` parse, 125 Lean by declaration scan; no imports, no Lean toolchain, ~1 s) and
  asserts the anchor COUNT against floors, so deleting rows fails too. This is the
  §9 design in that file, landed. It keeps the map **navigable, not true** — it
  cannot tell you a row's correspondence claim is wrong.
- **4e COUNTS** — `python -m formal.conformance.doc_counts --check` regenerates
  `formal/FINAL_REVIEW.md`'s delimited counts block from the tree (two
  `--collect-only` runs, per-file collection, `Audit.lean`, the pin files,
  `anchor_check`, `corpus.py`, `verify.sh`'s own floors, and — since 2026-08-05 —
  the **state-gate projection ledger**, every in-fragment corpus driven through the
  real graph index to count what each projection drops) and fails if the
  document disagrees. **~30 s** measured warm (this line said "~4 s" until
  2026-08-05 and had never been re-measured after the per-file table landed; ~24-28 s
  of it is 17 pytest `--collect-only` subprocesses, ~5 s the ledger).
  **Why it exists:** `ZT-P3-5` — "every doc number is
  stale and NOTHING gate-enforces any of them" — was hand-fixed on 2026-07-26,
  hand-fixed again on 2026-07-28, and was stale AGAIN on 2026-07-29, including
  `FINAL_REVIEW.md`'s own header stating two different values for the same
  quantity. Three hand-fixes of one defect is the signal to build a refusal.
  Regenerate deliberately with `--generate`.
  **Scope, honestly:** it pins ONE block in ONE file. Prose counts elsewhere are
  still hand-maintained — what changed is that there is now an authoritative
  machine-checked place to check them against, and widening the block is one row
  in `doc_counts.py::measure`.
- **4f BOARD LINT** (added 2026-08-16, board row `HS-1`) — `python
  scripts/handoff_lint.py`. Nine checks over the two board files and the two
  ledgers: line ceilings, exactly one `NOW` row and at most three `NEXT`, zero
  retired `★` glyphs, the trap budget, a liveness declaration in the first ten
  lines of every `docs/history/` and `formal/history/` file, the ledger-headline
  cap, the bold-caps ratchets, root-ledger-not-behind-`PROOF_STATUS`, and
  `rows:`-cited ids resolving to real board ids. **Sub-second**; it rides `lean`
  for the same reason 4d/4e do rather than becoming an eleventh phase.
  **Why it exists:** every capacity in the 2026-08-16 handoff redesign was prose,
  and this repo's record is that a prose capacity rots — `HANDOFF.md` restated
  gate counts three times after a rule forbade it, and `formal/HANDOFF.md`
  claimed "~250 lines" at over a thousand.
  **Scope, honestly:** it proves the board is well-FORMED, never that it is true,
  current, or useful. It cannot tell you a `NOW` row is the right `NOW`, that a
  pointer resolves to something actionable, or that a `moved` date is not a lie.
  Full `moved`-vs-ledger cross-validation was attempted and rejected as
  unsatisfiable — see `check_ledger_row_ids`' docstring.

#### What step 2 scans now (`formal/conformance/sorry_scan.py`)
The hole scan is no longer just `\b(?:sorry|admit)\b` over `formal/lean/ZanzibarProofs`:

- **Tokens:** `sorry`, `admit`, **`sorryAx`** (the constant a `sorry` elaborates to —
  `\bsorry\b` *cannot* match it, `A` is a word character) and **`native_decide`**
  (closes goals by running compiled code, pulling the `Lean.ofReduceBool` axiom).
- **Custom `axiom` declarations** (`^\s*axiom\s`, modulo modifiers/attributes) —
  `axiom cheat : ∀ p, p` typechecks and produces no `sorry`. Anchored so the 460
  `#print axioms` commands and every prose mention of the word do not trip it.
- **Unterminated string literals** are themselves a violation: one stray `"` used to
  make the rest of that file invisible to the scanner *in silence*.
- **Root is `formal/lean`**, not `formal/lean/ZanzibarProofs` — the latter missed the
  sibling library root `ZanzibarProofs.lean`. The scanner skips every dot-directory,
  which is what keeps the ~9.3k vendored `.lean` files under `formal/lean/.lake/**`
  (mathlib/aesop/batteries) out of the scan: **65 project files scanned, ~9.3k
  vendored files skipped** (was 64 / 0); the floor `MIN_SCANNED_LEAN_FILES` is 64.
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

### 4. The run ledger — what ran, when, and against which tree (2026-08-16)

Every `verify.sh` phase now leaves two artifacts behind, both under a **gitignored**
`.gate-runs/`:

| artifact | what it is |
|---|---|
| `.gate-runs/<stamp>-<phase>.log` | that phase's full output, verbatim |
| `.gate-runs/ledger.tsv` | one appended row: started · duration · phase · `PASSED`/`FAILED`/`INCONSISTENT` · tree id · the counts it observed · the log filename |

```bash
python scripts/gate_status.py                  # the report (see below)
python scripts/gate_status.py --require-green  # exit 1 unless THIS tree is covered
ZANZIBAR_GATE_LOG=0 bash formal/verify.sh lean # opt out for one run
ZANZIBAR_GATE_RUNS_DIR=/somewhere bash formal/verify.sh lean   # relocate
```

**Why it exists.** Before this, `verify.sh` printed to stdout and exited, leaving no
trace at all — so "were the nine tile phases run, and do they apply to the code in
front of me?" was answerable only across a session boundary by *memory*, which is
why the board carried it as a hand-written `Still owed:` line. The archaeology that
looks like it should work does not: `.pytest_cache/v/cache/lastfailed` is
**cumulative** (it retains entries for tests that did not re-run), so its contents
are not the last run's verdict — on 2026-08-16 all six of its entries named node ids
that **no longer exist**, and its mtime was that same day. `nodeids` is one
collection with no phase, no verdict and no tree attached.

**A row is about a tree, not about the repo.** The `tree` column is a **content
address** — `t1:<12 hex>` over the contents of every tracked and
untracked-non-ignored file (`scripts/gate_status.py::tree_id`; `verify.sh` shells out
to that same function so the recorder and the reader cannot drift). It carries no
commit id at all, and that is the point: it is invariant under `git add` and
`git commit`, so ten phases earned just before a commit still read green just after
it. It does **not** see anything gitignored (notably `formal/lean/.lake/**` — a
matching tree id does **not** mean the same Lean build) or the environment
(`ZANZIBAR_TEST_DSN`, installed deps). Read a green row as "this phase passed against
this source", never as full provenance.

⚠ **The scheme it replaced (2026-08-17, row `GS-1`) failed three ways — once safely,
twice not.** That asymmetry is why this is written out rather than summarised. The id
was `<short HEAD>+clean`, else `<short HEAD>+<sha1 of porcelain+diff>`:

| failure | direction | effect |
|---|---|---|
| committing changed the id although the content did not | fail-**safe** | a full green gate went stale one second after `git commit` — this was the filed defect, and the only harmless one |
| `--porcelain` *names* untracked files but never reads them, and collapses an untracked directory to a single `?? dir/` line | fail-**open** | editing an untracked file, or adding files inside an untracked directory, left the id — and its green rows — unchanged |
| a failed `git status` was coalesced to `""`, and untracked-only dirt leaves `git diff HEAD` empty as well | fail-**open** | one failed command was enough to make a dirty tree report the **clean** id and match a clean tree's green rows |

So `--tree-id` now **exits nonzero** rather than returning a plausible id when it
cannot read the tree. `verify.sh` still records `tree=unknown` for such a run — the
ledger never changes a verdict — but warns loudly, because `unknown` matches nothing
and the run therefore buys no coverage however green it was.

**A green verdict is keyed by (phase, tree), not by phase.** Re-running a single phase
against a different tree — a doc edit, a stash, a scratch file — used to overwrite the
reader's only entry for that phase and silently discard the green row earned on
*your* tree. A phase re-run **red on the same tree** still reads red: that is the
property the keying preserves.

⚠ **Do not un-ignore `.gate-runs/`.** The id hashes every tracked *and*
untracked-non-ignored file, so an un-ignored ledger sits inside its own hash: writing
a row changes the tree id that the next row records, and every row is stale on
arrival. Un-ignoring it does not start tracking the ledger, it breaks the ledger.
`gate_status.py` prints a loud warning if it sees `.gate-runs/` in `git status`.

**Coverage is judged per-K, not against a hard-coded ten.** `--require-green` wants
`lean` plus, for each suite, *some single K* with all K tiles green on the current
tree — so the throttled-box recipe (`conf-tile:1/8 … 8/8`, §"secondary machine") is
just as complete as `1/5 … 5/5`. Tiles at **mixed** K provably leave holes, so a mix
is refused rather than summed.

**A killed run leaves a log and no row** (the ~10-min cap kills the child before its
EXIT trap). `gate_status.py` reports that as an *incomplete run* — never as a pass.
The row is written by the trap precisely so that all ~30 `exit 1` paths are covered
without touching any of them.

**Sabotage evidence** (procedure: [`sabotage-procedure.md`](sabotage-procedure.md)).
The property: *a row saying `PASSED` means the phase really passed, and a phase that
fails still exits nonzero even though its output now goes through `tee`.*

| sabotage | observed |
|---|---|
| control — clean `conf-tile:6/100` | `EXIT=0`, row `PASSED … rc=0 collected=495 selected=5 conf_passed=5 conf_xfailed=0 conf_skipped=0 conf_floor=5` |
| `MIN_CONF_ALL=495` → `99999` (a real gate failure) | `EXIT=1` — **the tee did not eat it** — row `FAILED … rc=1` |
| a genuinely red pytest inside a tile (temp failing test, `conf-tile:96/100`) | `1 failed, 4 passed in 0.95s` → `FAIL: conf (pytest rc=1)`, `EXIT=1`, row `FAILED … rc=1 collected=496 selected=5` |
| delete `GATE_REACHED_END=1` (models a future exit path that skips the banner) | `EXIT=1`, row `INCONSISTENT`, and `FAIL: verify.sh is exiting 0 WITHOUT its final PASSED banner` |

The **first** sabotage found a real defect rather than confirming a good check: the
trap was originally installed beside `BUILD_LOG=$(mktemp)`, ~230 lines *below* the
floor-consistency check, so that `EXIT=1` produced a log file and **no row** — a
failure the reader could only call "incomplete". The trap now precedes the first
`exit` in the script body, and the comment there says why.

**Sabotage evidence, the tree id (2026-08-17).** Property: *a row's tree id names the
content the phase ran against — it survives a commit that changes nothing, it moves
when any covered file's content moves, it is never invented when the tree cannot be
read, and a green verdict is not erased by a later run of the same phase elsewhere.*
Pinned by `tests/test_gate_status.py`; the per-defect observations are in that file's
module docstring. The suite-level sabotage — reinstall the pre-2026-08-17 `tree_id`
and per-phase keying verbatim, then run the suite against them:

| sabotage | observed |
|---|---|
| control — the fixed implementation | `16 passed in 2.59s` |
| the legacy `tree_id` + legacy per-phase keying restored | `10 failed, 6 passed in 3.57s` |

The six survivors are exactly the controls (tracked-file edit, tracked-file deletion,
the gitignored-scope assertion, the red-rerun negative control, the legacy-id
non-collision, and `coverage`'s unchanged mixed-K refusal). That the red is
**attributable** rather than blanket is the point: it distinguishes "these tests pin
the four defects" from "this file no longer imports".

### Push gate
Push only after ALL of: the ten `verify.sh` phases — `lean` → `conf-tile:1/5` →
`2/5` → `3/5` → `4/5` → `5/5` → `tests-tile:1/4` → `2/4` → `3/4` → `4/4` — each
green; and — for an algorithm change — a fuzz sweep (step 3) green.
`python scripts/gate_status.py --require-green` answers "are they all green **on
this tree**" mechanically (§4) — it is a convenience over the ledger, not a
substitute for running the phases, and it knows nothing about the fuzz sweep. (`tests-tile`
replaced the hand-typed `pytest tests/` split on 2026-07-27; see §1.) The phased
gate is fully **agent-runnable
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
- **`tests/` on a throttled box: just raise K.** The hand-rolled tiling this bullet
  used to describe (group files alphabetically into ≤130-test tiles and assert
  Σ(tile passed) == the collect-only total) is obsolete since 2026-07-27:
  `verify.sh tests-tile:I/K` takes any `K`, partitions by collection index, and does
  the Σ-check for you as partition arithmetic. On a 2-3× slower box run
  `tests-tile:1/8 … 8/8`. (Historical calibration: 2026-07-23 ran 10 hand-made tiles,
  606/606, worst tile 546 s throttled.)
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
  re-collects the directory, re-asserts the 465-test global floor, checks its own size
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

- `tee` masks pytest's exit code → capture `$?`. (Since 2026-08-16 `verify.sh`
  itself pipes its whole run through `tee` for the run log — it takes
  `${PIPESTATUS[0]}`, so **callers still get the phase's real exit code**. That is
  the one place in this repo where the footgun would be systemic, so it carries a
  positive control: see §4's sabotage table.)
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
- the conformance corpora (`formal/conformance/`, ~465 deterministic tests),
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
