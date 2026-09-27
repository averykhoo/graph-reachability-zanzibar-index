# `P12`: severity-sign revert probe — the 2026-08-09 sibling's sign, OBSERVED

**ACTIVE-PLAN 2026-09-27 (session `2026-09-27d`).** Living while `P12` is open; FROZEN at its
close. Corrections are appended dated at the top, never edited into the body. Every figure
below was measured on 2026-09-27; the base is master `d4ea804`.

Provenance labels: **READ** (first-hand, this session), **MEASURED** (a run whose literal
output is quoted), **REASONED**, **UNVERIFIED**. No subagents were used.

## § 0 The question, and why it was open (READ)

`docs/spec-deviations.md` 2026-08-10 ("LIVE AUTHORIZATION FAIL-OPEN", §"Severity: FAIL-OPEN,
correcting the original filing") states the severity-sign rule — *a dropped TTU parent is a
false NEGATIVE under a positive TTU and a false POSITIVE under a negated one* — and then
fences off one thing it did **not** observe: the 2026-08-09 sibling (the OWC x star-parent x
TTU under-report, fixed by the I14 crossing middles) carries "it fails closed, so it is not a
security fail-open" wording, and the rule *predicts* it inverts. Completion criterion, quoted:
*"either this entry gains a measured severity for the 2026-08-09 sibling, or that sibling's
'fails closed' wording is corrected in place."* Corrections here are appended dated, so the
first branch is the one taken.

RC1 and RC2 themselves are NOT open: both signs were already measured on 2026-08-10
(`tests/test_ttu_tupleset_parent_types.py` docstring at the pre-fix trees, rows (1a)/(1b),
(2a)/(2b): positive TTU `oracle=True graph=False`, negated TTU `oracle=False graph=True`).

## § 1 Scouting (READ, 2026-09-27)

* **The commit hashes the docs cite are not in master's history.** `c042056` (the I14 fix)
  and `ed46e54` (RC1) are named in `docs/spec-deviations.md`, but
  `git branch -a --contains c042056` prints nothing. Their in-history twins, with
  byte-identical trees (`git diff --stat c042056 33242de` and `git diff --stat 7cd12b5 ed46e54`
  both print nothing):
  * `33242de` = `c042056` — "index_v4: fix the OWC x star-parent x TTU under-report — the
    middle tracks the ENTITY" (the sibling's fix);
  * `7cd12b5` = `ed46e54` — RC1's fix;
  * `0838bcf` — RC2's fix ("RC2: represent the star TTU tupleset parent").
  Anyone reverting by the cited hash will hit an unknown-to-this-branch object; use the twins.
* **The sibling's fix is structural, not a filter.** `index_v4/wildcard.py::WildcardIndex._ensure_entity_middles`
  interns the crossing middle `(T, x, p)` with both bridges for every crossable shape of an
  existing entity; `::WildcardIndex._sync_entity_middles` is its removal-side dual; the
  property is invariant I14 (`index_v4/invariants.py`). The fixture is
  `tests/fga_schemas/owc_star_ttu.fga` with `OWC_STAR_TTU_SHAPES`
  (`tests/test_lookup_oracle.py::OWC_STAR_TTU_SHAPES`), pinned by
  `tests/test_owc_star_parent_cross.py`.
* **RC1 and RC2 are now unreachable from a checked parse (REASONED from READ).** `TK106`
  (2026-09-26) made a `from`-tupleset direct-only (`zanzibar_utils_v1.py::_validate_tuplesets_direct`),
  so `parent: [folder] but not [doc]` (RC1) and any tainted tupleset (RC2) are parse
  refusals today. Their signs can only be re-observed on the historical trees.
* **The consumer polarities that exist for the sibling (REASONED).** In `owc_star_ttu.fga`,
  `doc#viewer = [...] or viewer from parent` is a union — NOT tainted — so the positive TTU is
  read on the plain closure path. A negated consumer (`define access: [user] but not viewer
  from parent`) is tainted and read through the delta processor's derived predicate. The two
  polarities therefore exercise **different machinery**, which is why the sign has to be
  measured rather than transferred from RC1/RC2.

## § 2 Method (planned)

1. **Literal revert, no product file touched.** `git archive` the pre-fix tree `33242de^` and
   the post-fix tree `33242de` into the worktree's gitignored `.scratch/p12/`, and run one
   probe script against each: `owc_star_ttu.fga` plus a negated consumer, every subset of a
   small tuple pool, the full check grid, graph vs oracle, divergences counted by SIGN.
2. **The same probe on today's code, with the fix's core simulated away** (no-op
   `_ensure_entity_middles`, paranoia OFF because I14 would otherwise abort the write). If the
   counts match the literal revert's, the simulation is faithful and can be a permanent test.
3. **Optional, cheap:** re-run the harness on `7cd12b5^` / `0838bcf^` for RC1/RC2 grid counts.
4. **Keep it durably:** a permanent test pinning the SIGN of the simulated revert (both
   polarities, with an unsabotaged control), sabotage + mutation sweep with an M0 control, and
   a dated entry in `docs/spec-deviations.md`.

## § 3 Results (MEASURED 2026-09-27)

### § 3.1 The negated consumer the 2026-08-10 entry proposed does not compile

`.scratch/p12/compile_probe.py` (throwaway; its verdicts are transcribed here and pinned by
`tests/test_p12_severity_sign.py::test_the_proposed_negated_consumer_is_refused`), run on
the pre-fix tree `33242de^` AND on `d4ea804`, identical output both times:

```
REFUSED   owc=both         A doc.access = [user] but not viewer from parent: UnsupportedByGraphIndex: object-wildcard shape (folder, viewer) is the TTU target of derived relation doc#access; ...
REFUSED   owc=folder-only  A doc.access = [user] but not viewer from parent: UnsupportedByGraphIndex: ... (same)
REFUSED   owc=both         B doc.access = [user] but not viewer: UnsupportedByGraphIndex: object-wildcard shape (doc, access) expands onto the compiled leaf predicate (doc, access.1) ...
COMPILES  owc=folder-only  B doc.access = [user] but not viewer
REFUSED   owc=both         D report.access = [user] but not viewer from parent (report.parent:[doc]): UnsupportedByGraphIndex: object-wildcard shape (doc, viewer) is the TTU target of derived relation report#access; ...
COMPILES  owc=folder-only  D report.access = [user] but not viewer from parent (report.parent:[doc])
COMPILES  owc=both         E report.access = [user] but not blocked (blocked:[user, doc#viewer])
COMPILES  owc=folder-only  E report.access = [user] but not blocked (blocked:[user, doc#viewer])
```

So the probe as written in the 2026-08-10 entry ("add a negated-TTU consumer over the
`owc_star_ttu.fga` shape") cannot be run against the graph index: blind-audit D4
(`zanzibar_utils_v1.py::_reject_object_wildcard_scope`) refuses an object-wildcard shape
as the TTU target of a derived relation. The three negated consumers that DO compile
consume the defective positive TTU (`doc#viewer = ... or viewer from parent`) one hop
downstream, through three different mechanisms:

| id | consumer | object-wildcard shapes | how it reads `doc#viewer` |
|---|---|---|---|
| B | `doc#access: [user] but not viewer` | `{(folder, viewer)}` | Computed arm |
| D | `report#access: [user] but not viewer from parent`, `report#parent: [doc]` | `{(folder, viewer)}` | TTU arm |
| E | `report#access: [user] but not blocked`, `report#blocked: [user, doc#viewer]` | both (the 2026-08-09 fixture's) | userset subject |

### § 3.2 The literal revert — the sign is OBSERVED

Instrument: `.scratch/p12/probe.py <tree> <case>` — every subset of an 8-tuple pool (adds
in pool order, admission checked), the full check grid, graph vs the SAME tree's oracle,
each divergence classified OPEN (graph grants, oracle denies) or CLOSED (graph denies,
oracle grants). Paranoia at the tree's test default (`True`). The pool is the 2026-08-09
three tuples (`u9 editor folder:f1`, `u1 viewer folder:*`, `folder:* parent doc:d1`) plus
a healing tuple (`u2 viewer folder:f1`), a second witness (`u1 blocked folder:f2`) and the
consumer's own tuples. Literal output:

```
tree=pre_i14 case=B        (33242de^, the pre-fix tree)
states=256 rejected_adds=0 queries=3072 divergences=36
  access     fail-OPEN   12
  viewer     fail-CLOSED 24
  minimal witness [access fail-OPEN]: check('user', 'u1', 'access', 'doc', 'd1') oracle=False graph=True
      ('...', 'user', 'u9', 'editor', 'folder', 'f1')
      ('...', 'user', 'u1', 'viewer', 'folder', '*')
      ('...', 'folder', '*', 'parent', 'doc', 'd1')
      ('...', 'user', 'u1', 'access', 'doc', 'd1')
  minimal witness [viewer fail-CLOSED]: check('user', 'u1', 'viewer', 'doc', 'd1') oracle=True graph=False
      (the first three tuples above)

tree=pre_i14 case=D
states=256 rejected_adds=0 queries=3072 divergences=30
  access     fail-OPEN   6
  viewer     fail-CLOSED 24

tree=pre_i14 case=E
states=256 rejected_adds=0 queries=3840 divergences=42
  access     fail-OPEN   6
  blocked    fail-CLOSED 12
  viewer     fail-CLOSED 24
```

**Verdict (MEASURED): the prediction holds.** The 2026-08-09 defect is fail-CLOSED under
every positive consumer (`viewer`, and `blocked` in E, which is itself a positive read of
`doc#viewer`) and **fail-OPEN — an authorization over-grant — under every negated consumer
the graph index compiles**. Every OPEN cell is on a negated relation and every CLOSED cell
on a positive one; zero admission refusals, so no cell is explained by a refused write.

### § 3.3 The simulated revert on today's code reproduces the literal one exactly

`probe.py ../.. B --sabotage-middles --paranoia off` — `d4ea804` with
`WildcardIndex._ensure_entity_middles` replaced by a no-op in-process:

```
tree=wf_5557c336-8fc-2 case=B sabotage_middles=True paranoia=False
states=256 rejected_adds=0 queries=3072 divergences=36
  access     fail-OPEN   12
  viewer     fail-CLOSED 24
```

Identical counts, identical minimal witnesses to `pre_i14 B`. The literal post-fix tree
`33242de` gives `tree=post_i14 case=B states=256 rejected_adds=0 queries=3072 divergences=0`,
so the 36 divergences are attributable to that one commit. The same simulation for D and E:

```
tree=wf_5557c336-8fc-2 case=D sabotage_middles=True paranoia=False
states=256 rejected_adds=0 queries=3072 divergences=30
  access     fail-OPEN   6
  viewer     fail-CLOSED 24
tree=wf_5557c336-8fc-2 case=E sabotage_middles=True paranoia=False
states=256 rejected_adds=0 queries=3840 divergences=42
  access     fail-OPEN   6
  blocked    fail-CLOSED 12
  viewer     fail-CLOSED 24
```

— identical to `pre_i14 D` / `pre_i14 E` for all three consumers. Unsabotaged control on the same
tree (`paranoia=True`): `states=256 rejected_adds=0 queries=3072 divergences=0`. That is what
licenses the permanent test (§ 4) to simulate the revert instead of shipping it.

### § 3.4 Which paranoia level catches the regression today

`.scratch/p12/paranoia_levels.py`, simulated revert, minimal witness, each consumer:

```
B-computed off      admitted=[True, True, True, True] positive: oracle=True graph=False  negated: oracle=False graph=True
B-computed residue  admitted=[True, True, True, True] positive: oracle=True graph=False  negated: oracle=False graph=True
B-computed full     RAISED InvariantViolation: store='g' [pre-commit] I14: entity folder:f1 exists but its crossing middle folder:f1#viewer for crossable shape ('folder', 'viewer') is missing
B-computed fixpoint RAISED InvariantViolation: (same)
(D-ttu and E-userset: the same four lines)
```

**Finding (MEASURED, not previously written down):** `ZANZIBAR_PARANOIA=residue` — the level
`CLAUDE.md` recommends in production — does NOT detect an I14 regression; only `full` and up
run `check_invariants`, where I14 lives. So a future refactor that dropped the crossing
middles would be a silent fail-open in a production configured as recommended, and a loud
abort only in the test suite. This is a detector gap for a hypothetical regression, not a
live bug (the shipped code maintains the middles and the gate runs at `full`); it is pinned
by `test_which_paranoia_level_catches_the_simulated_revert` so the gap cannot close or widen
unnoticed. Whether `residue` should gain an I14 check is a cost question left open (§ 6).

### § 3.5 RC1 and RC2, re-observed with grid counts on their own pre-fix trees

Both signs were already measured on 2026-08-10; these are the grid counts, with the exact
fixtures of `tests/test_ttu_tupleset_parent_types.py` as it stood at `0838bcf^` plus one
extra `bob access doc:d1` tuple:

```
tree=pre_rc1 case=rc1      (7cd12b5^ = ed46e54^)
states=64 rejected_adds=0 queries=512 divergences=18
  access     fail-OPEN   6
  inherited  fail-CLOSED 12

tree=pre_rc2 case=rc2      (0838bcf^: RC1 fixed, RC2 open)
states=128 rejected_adds=0 queries=1024 divergences=24
  access     fail-OPEN   8
  inherited  fail-CLOSED 16
```

Same split: every negated cell OPEN, every positive cell CLOSED. Both shapes are parse
refusals since `TK106`, so they stay history. Post-fix controls on `0838bcf`: `case=rc1`
`states=64 queries=512 divergences=0`; `case=rc2` `states=128 queries=1024 divergences=0`.

## § 4 What landed, and the decision behind its shape (REASONED)

**Decision: a permanent test that SIMULATES the revert, not a doc-only record.** The
durability ranking in `docs/sabotage-procedure.md` puts a permanent test first. Shipping
reverted code is out; simulating the pre-fix behaviour in-test is honest *only if the
simulation is faithful*, and § 3.3 measured that it is (identical counts to the literal
revert on the 256-state grid). The simulation is the one-line no-op of
`WildcardIndex._ensure_entity_middles` that `tests/test_i14_crossing_middles.py` already
uses, so the test reuses a sabotage the repo already trusts.

`tests/test_p12_severity_sign.py` (14 tests, `pytest --collect-only` 2026-09-27):

| test | pins |
|---|---|
| `test_simulated_revert_is_fail_open_under_a_negated_consumer[B/D/E]` | the SIGN: positive consumer fail-CLOSED, negated consumer fail-OPEN; oracle and both set engines asserted first |
| `test_live_graph_agrees_with_the_oracle[B/D/E]` | control: shipped code, paranoia full, agrees everywhere |
| `test_simulated_revert_heals_when_the_middle_is_interned_by_data[B/D/E]` | control: interning `folder:f1#viewer` by data restores agreement, so the divergence is the middle |
| `test_which_paranoia_level_catches_the_simulated_revert[off/residue/full/fixpoint]` | § 3.4's per-level severity |
| `test_the_proposed_negated_consumer_is_refused` | § 3.1: the entry's proposed consumer is a D4 refusal |

Doc edits: `docs/spec-deviations.md` `## 2026-09-27b` (new, top) plus a dated blockquote in
each of `## 2026-08-10` and `## 2026-08-09` (bodies untouched); the P12 bullet deleted from
`docs/latent-gaps.md` (replace semantics — the gap was "never re-tested", and it now is);
dated notes in the docstrings of `tests/test_owc_star_parent_cross.py` and
`tests/test_ttu_tupleset_parent_types.py`, which carried the same "fails closed" /
"NOT claimed" wording.

## § 5 Sabotage + mutation sweep (MEASURED 2026-09-27)

`.scratch/p12/mut.py`: anchor asserted to occur exactly once, file restored in `finally` and
sha256-checked, no outer timeout; `git status` clean afterwards. Literal:

```
M0 [control: no change] rc=0 :: 14 passed in 10.67s
M1 [product: _ensure_entity_middles creates no middle (the literal regression)] rc=1 :: 3 failed, 11 passed in 14.71s
      FAILED tests/test_p12_severity_sign.py::test_live_graph_agrees_with_the_oracle[B-computed]
      FAILED tests/test_p12_severity_sign.py::test_live_graph_agrees_with_the_oracle[D-ttu]
      FAILED tests/test_p12_severity_sign.py::test_live_graph_agrees_with_the_oracle[E-userset]
M2 [product: _ensure_own_bridges never adds the w_all -> concrete out-bridge] rc=1 :: 6 failed, 8 passed in 10.16s
      FAILED ...test_live_graph_agrees_with_the_oracle[B-computed] / [D-ttu] / [E-userset]
      FAILED ...test_simulated_revert_heals_when_the_middle_is_interned_by_data[B-computed] / [D-ttu] / [E-userset]
M3 [product: the I14 checker checks nothing] rc=1 :: 2 failed, 12 passed in 10.68s
      FAILED ...test_which_paranoia_level_catches_the_simulated_revert[full-abort]
      FAILED ...test_which_paranoia_level_catches_the_simulated_revert[fixpoint-abort]
M4 [instrument: the simulation patches the removal-side dual instead] rc=1 :: 7 failed, 7 passed in 11.90s
      FAILED ...test_simulated_revert_is_fail_open_under_a_negated_consumer[B-computed] / [D-ttu] / [E-userset]
      FAILED ...test_which_paranoia_level_catches_the_simulated_revert[off-fail-OPEN] / [residue-fail-OPEN] / [full-abort] / [fixpoint-abort]
M5 [instrument: sign classifier inverted] rc=1 :: 5 failed, 9 passed in 11.77s
      FAILED ...test_simulated_revert_is_fail_open_under_a_negated_consumer[B-computed] / [D-ttu] / [E-userset]
      FAILED ...test_which_paranoia_level_catches_the_simulated_revert[off-fail-OPEN] / [residue-fail-OPEN]
M6 [instrument: the heal control loses its healing tuple] rc=1 :: 3 failed, 11 passed in 13.06s
      FAILED ...test_simulated_revert_heals_when_the_middle_is_interned_by_data[B-computed] / [D-ttu] / [E-userset]
ALL RESTORED (hash-checked)
```

Every mutant reddened exactly the tests that guard its target, and nothing else. **INERT by
design:** M4 leaves the heal controls green (they pass with or without the simulation; M6
shows they have teeth). **Not reached:** no single-line mutant flips the SIGN while keeping
the live graph correct — the sign pin guards against a future change in how negated
consumers read `doc#viewer`, which is a multi-site change.

## § 5b Gate, in the worktree (MEASURED 2026-09-27/28)

Targeted: `pytest tests/test_p12_severity_sign.py tests/test_owc_star_parent_cross.py
tests/test_ttu_tupleset_parent_types.py tests/test_i14_crossing_middles.py` → `35 passed`.
`bash formal/verify.sh tests-tile:K/4`, one phase per command (collected 1440 node ids,
global floor 1421):

```
=== verify.sh: phase 'tests-tile:1/4' PASSED ===   360 passed in 1174.11s
=== verify.sh: phase 'tests-tile:2/4' PASSED ===   360 passed in 759.68s
=== verify.sh: phase 'tests-tile:3/4' PASSED ===   360 passed in 744.36s
=== verify.sh: phase 'tests-tile:4/4' PASSED ===   360 passed in 501.55s
```

NOT run here: `lean` and `conf-tile:1/5`…`5/5` (no `.lake` in a fresh worktree; the
orchestrator runs them on the main tree after merge). `MIN_TESTS_ALL` was not ratcheted
(1421 vs 1440 collected). `python scripts/task.py lint` clean (13 checks, 227 files);
`scripts/handoff_lint.py` clean (12 checks).

## § 6 Open, and the single next action

* **Decision for the orchestrator/next session, not taken here:** should `residue` paranoia
  gain the I14 check (§ 3.4)? It is `check_invariants`-shaped (a full node scan), so it would
  cost more than the ~+5% `residue` is sold at. REASONED only; no measurement made. If
  filed, it is a new row, not part of `P12`.
* `P12`'s completion criterion (the 2026-08-10 entry's) is met. Next action: close `P12`
  citing `## 2026-09-27b`, and FREEZE this doc.
* The throwaway instruments (`.scratch/p12/probe.py`, `compile_probe.py`,
  `paranoia_levels.py`, `mut.py`) live only in the worktree's gitignored `.scratch/`; every
  output they produced that this doc relies on is transcribed above.
