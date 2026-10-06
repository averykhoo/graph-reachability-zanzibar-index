# `TK83` — putting the star-admitting intersection in the tree

**ACTIVE-PLAN, opened 2026-09-20g — the body is provenance, not a living status.** Live
state is the task row (`python scripts/task.py show TK83`) and
`python scripts/gate_status.py`, never this file. Corrections append **dated at the top**,
never edited into the body. Freeze it when `TK83` closes.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

Provenance labels: **MEASURED** (this session ran it and read the literal output), **READ**
(first-hand from the named `file::symbol`), **REASONED** (derived from a READ, not
separately observed), **UNVERIFIED**. No subagent was used; nothing here is agent-reported.

Reproduce the two headline measurements with
`formal/probes/tk83_star_intersection_2026-09-20.py` (its docstring carries the verbatim
stdout).

---

## 1. Why the item existed

`docs/tk74-staleness-net-2026-09-18.md` §9.5 recorded that a half-stale intersection writes
**no residue at all**, and generalised: *"The divergence is carried entirely in materialized
closure edges."* §9.5's own caveat flagged the **starred** case as *untested, not
tested-and-clean*. §10.5 then refuted the generalisation — and did it on
`.scratch/tk74d-starisect/star_isect.fga`, a **gitignored** file, i.e. per this repo's own
rule already lost. `TK83`'s whole content is that the shape which breaks §9.5 was reachable
from nothing tracked.

**MEASURED 2026-09-20g** (probe section (A)), and this reproduces §10.5's 2026-09-18c
census on the live tree rather than trusting it:

| fixture | intersection key | stratum | `Plan.deps` | star-admitting leaf child? |
|---|---|---|---|---|
| `boolean_wildcards` | `('doc','restricted')` | 0 | `()` | **yes** — nothing to go stale |
| `demorgans_law_2` | `('role','authorized_user')` | 4 | `(('role','role_user_met'),)` | no |
| `tupleset_shapes` | `('doc','approved_parent')` | 0 | `()` | no |
| **`star_admitting_intersection`** (new) | `('role','authorized_user')` | 4 | `(('role','role_user_met'),)` | **yes** |

The three pre-existing rows are asserted as an instrument control before the fourth is
read: a walker that mis-classified `boolean_wildcards` would also mis-classify the new
fixture, and "the new fixture is the only one" is exactly the shape of claim a broken
walker produces.

⚠ **The star column is subtler than it looks, and getting it wrong inverts the table.**
Stars **do** reach `demorgans_law_2`'s intersection — through its derived dep
`('role','role_user_met')`, whose residue carries `stars=[['user','...']]` (MEASURED,
probe section (B)). The intersection still writes nothing, because `stars ∩ no-stars = ∅`.
So the column is about the intersection's own **leaf** child, and a walker that followed
the dep would report `True` for every row. `_star_admitting` stops at a `Computed` into a
tainted relation for exactly this reason
(`tests/test_star_admitting_intersection.py::_star_admitting`).

## 2. The fixture

`tests/fga_schemas/star_admitting_intersection.fga` — `demorgans_law_2.fga` with **one
token changed**, line 21:

```
-    define assigned: [user]
+    define assigned: [user, user:*]
```

**MEASURED**: byte-for-byte that is the only difference (727 → 735 bytes), asserted in the
tree by `test_the_two_fixtures_differ_by_exactly_the_star`. The pair is only evidence while
it stays one token apart — every residue claim below is a *difference* against the twin,
and an edit to either schema would leave those assertions still finding a difference and
no longer measuring the star.

The compiled golden differs from the twin by exactly one `Filter`
(`tests/snapshots/compiled_ruleset/star_admitting_intersection.fga.txt`, 16 lines,
generated deliberately with `ZANZIBAR_UPDATE_SNAPSHOTS=1`):

```
> Filter(if_pattern=RelationalTriplePattern(subject_predicate=Ellipsis, subject_type='user',
  subject_name='*', relation='assigned', object_type='role', object_name=None,
  match_wildcards=False, object_match_wildcards=True))
```

## 3. §9.5 is refuted from the tree — MEASURED

One workload, shape-identical on both fixtures. The control cannot store
`role:r3 assigned user:*` at all (`assigned: [user]`), and that refusal is itself pinned —
otherwise the comparison is measuring two workloads rather than two schemas.

| residue key | `star_admitting_intersection` | `demorgans_law_2` |
|---|---|---|
| `('role','authorized_user','r3')` — **the intersection** | `stars=[['user','...']]` | **no row at all** |
| `('doc','access','d2')` — one relation further | `stars=[['user','...']]` | `stars=[]` |
| `('role','role_user_met','r3')` — the derived dep | `stars=[['user','...']]` | `stars=[['user','...']]` |
| total rows | 5 | 4 |

and the answer differs end to end: `check(user:bob, access, doc:d2)` is **True** on the new
fixture and **False** on the twin (`bob` is granted nothing anywhere; he arrives only
through `assigned: [user:*]`). Every `check` is a `ParityEngine` check, so that is unanimous
across the graph index, both `SetOps` set engines, and the oracle.

**So the residue channel carries the divergence too**, exactly as §10.5 found — and now
visible as a standing difference between two tracked fixtures rather than only under fault
injection.

⚠ **SCOPE, stated because the row's headline invites over-reading.** This closes a
*reachability* gap. It does **not** re-run §10.5's 144 fault-injection arms, and it says
nothing about what the settle pass or the paranoia tiers catch under a skipped reconcile —
that is `TK74`'s assurance gap and is **untouched**. §10.5's one FAIL-OPEN arm
(`graph=True, oracle=False` on three `user_missing_requirement c4` queries) is **not**
reproduced here and remains UNVERIFIED by this session; it required deliberate fault
injection. The board's "live correctness bugs: 0" is undisturbed.

## 4. The corpus scorer cannot see this fixture — and that changes where the guard goes

**MEASURED 2026-09-20g.** The symmetric difference between the two fixtures' `genswarm`
feature sets is the **empty set**. Adding a wildcard to one restriction list moves no
genswarm feature. Consequences, both load-bearing:

* **A coverage floor is the wrong guard.** `test_schema_shapes.py`'s two `>=` floors would
  stay green with this fixture deleted. The guard therefore had to be *structural*:
  `tests/test_star_admitting_intersection.py::test_corpus_has_a_star_admitting_intersection_with_a_derived_dep`
  asserts the corpus still contains ≥1 intersection with both a non-empty dep and a
  star-admitting leaf child. That assertion is the only thing that reds on deletion.
* **The retirement register mis-fires on the pair.** Scored leave-one-out, adding the new
  fixture made **both** it and `demorgans_law_2` come back "fully covered by other
  fixtures" — each is the other's cover. That is the self-masking artifact
  `test_subsumption_register_is_current`'s own docstring names, and listing them in
  `KNOWN_SUBSUMED` (which means *retirement candidate*) would have been an invitation to
  delete the thing `TK83` just landed.

**MEASURED, the three numbers the new `MASKED_PAIRS` exemption rests on:**

| question | answer |
|---|---|
| each member subsumed against the whole corpus? | yes / yes |
| each member subsumed with the *other* dropped? | **no / no** — so it is masking, not redundancy |
| dropping **both** at once loses | 0 features, **6** co-occurring pairs |

The third is the one that matters: the pair is jointly load-bearing even in `genswarm`'s own
vocabulary, so the exemption is not a way of parking a genuinely-dead fixture.
`test_masked_groups_are_really_masked` asserts all three per group, and
`test_masked_groups_cite_a_live_guard` resolves the `file::symbol` the group cites —
`CLAUDE.md`'s standing trap is a guard named by a symbol that never existed.

## 5. What landed

| file | change |
|---|---|
| `tests/fga_schemas/star_admitting_intersection.fga` | NEW — the fixture |
| `tests/snapshots/compiled_ruleset/star_admitting_intersection.fga.txt` | NEW — golden |
| `tests/test_star_admitting_intersection.py` | NEW — 11 pins: census control, retirement guard, the §9.5 refutation, propagation, end-to-end answer, pair integrity, and the star fold itself (§8) |
| `tests/test_schema_shapes.py` | `MASKED_PAIRS` + 2 tests; register exempts masked members |
| `tests/test_matrix.py` | fixture joins `test_demorgan_oracle_equals_setengine_equals_graph` (static 4-way leg) |
| `tests/test_reads.py` | fixture joins `test_grid_parity_demorgans` (walking add/remove leg) |
| `tests/test_schema_ast.py` | fixture joins `test_compile_accepts_booleans` |
| `tests/test_boolean_compile.py` | boolean/pure split **derived**, was two index slices |
| `formal/probes/tk83_star_intersection_2026-09-20.py` | NEW — the acceptance instrument |

⚠ **§6 below records a bug this item tripped over on the way**, in a place `TK83` had no
reason to look.

## 6. `test_boolean_compile.py`'s split was two hardcoded index slices — found by walking into it

**READ 2026-09-20g.** The module carried `BOOLEAN_FIXTURES = ALL_FIXTURES[:4]` and
`@pytest.mark.parametrize('fixture', ALL_FIXTURES[4:])`. Inserting the new boolean fixture
at index 4 put it in *neither* the boolean leg *nor*, correctly, the pure leg — it landed in
`test_pure_fixtures_identical_under_enable_boolean`, which asserts a schema has **no**
tainted relations, and reddened:

```
FAILED tests/test_boolean_compile.py::test_pure_fixtures_identical_under_enable_boolean[star_admitting_intersection.fga]
1 failed, 197 passed in 159.45s
```

**That red was luck.** The complement slice happens to assert something a boolean schema
violates. The other direction is silent: append a boolean fixture at the **end** of
`ALL_FIXTURES` and it simply never receives its boolean-specific assertions, with the module
green throughout — which is precisely how `owc_star_ttu.fga` spent its whole life in the
weak leg (`tests/test_zanzibar_utils.py::test_boolean_fga_files_is_derived_not_hardcoded`).
This is the hand-maintained-list-beside-a-derivation pattern for the **third** time in this
tree.

Fixed by deriving the split from the schema (an AST scan for `Intersection`/`Exclusion`,
deliberately **not** `rs.compiled.tainted` — routing the split through the thing under test
means a taint bug reclassifies the fixtures that would have caught it), with a module-level
anti-vacuity assert so a derivation returning `[]` cannot make a whole leg vanish into
`0 collected`.

⚠ **The harness reported that 159 s run as "exit code 0".** The log's last line said
`1 failed, 197 passed`. This is `CLAUDE.md`'s standing footgun again, in its background-job
form: the captured status was not pytest's. The failure was found by reading the log's last
line, which is the only reliable move.

## 7. Mutation sweep — does the fixture earn its place?

See §8. The sweep runs each production mutation twice over the same target set: **WITH** the
new fixture, and **WITHOUT** (`-k "not star_admitting"`, i.e. the corpus as it stood before
2026-09-20g). A mutation caught only in the WITH arm is coverage the fixture added; one
caught in both was already covered and is recorded as such, because *"the new module
reddens"* is a weaker claim than *"only the new module reddens"*.

Guard-arm sweep over `tests/test_schema_shapes.py`, **MEASURED 2026-09-20g**, `M0` control
first and attributed correctly:

| id | mutation | verdict | attributed to |
|---|---|---|---|
| `M0` | cited symbol stops resolving (**the control**) | RED | `test_masked_groups_cite_a_live_guard` |
| `M1` | cited **file** stops existing | RED | `test_masked_groups_cite_a_live_guard` |
| `M2` | cited symbol renamed (the realistic editor slip) | RED | `test_masked_groups_cite_a_live_guard` |
| `M3` | a **non**-subsumed fixture parked on the exemption list | RED | `test_masked_groups_are_really_masked` |
| `M4` | a genuinely-subsumed fixture moved onto the exemption list | RED | `test_masked_groups_are_really_masked` |
| `M5` | the register's exemption widened to swallow everything | **INERT** | — (`37 passed`) |

⚠ **`M5` is INERT and it is a finding, not a gap to paper over.** Rewriting
`newly = subsumed - KNOWN_SUBSUMED - _MASKED_MEMBERS` as `subsumed - subsumed` makes
`test_subsumption_register_is_current` pass vacuously and **nothing catches it** — a test
cannot observe its own neutering. What `M5` actually establishes is a property worth stating
plainly: **the subsumption register is a REPORT, not a guard.** It is why `TK83`'s protection
for the fixture lives in
`test_corpus_has_a_star_admitting_intersection_with_a_derived_dep` and not in the register,
and why `MASKED_PAIRS` is required to name a guard elsewhere.

## 8. Sweep results — MEASURED 2026-09-20g

Target set: `tests/test_star_admitting_intersection.py`, `test_matrix.py`, `test_reads.py`,
`test_oracle_boolean.py`, `test_schema_shapes.py`. The WITHOUT arm is `-k "not
star_admitting"`, which deselects exactly **14** items (10 module tests + 2 `test_matrix`
params + 2 `test_reads` params) — i.e. the corpus as it stood before this item.

| id | mutation | WITH | WITHOUT | verdict |
|---|---|---|---|---|
| `M0` | the fixture stops being star-admitting (**the control**) | `6 failed, 92 passed` | `84 passed, 14 deselected` | control OK — attributed to 6 named pins |
| `P1` | `_compile_stars_fn` `PIntersection` `&` → `|` | `4 failed, 90 passed, 4 errors` | `2 failed, 82 passed` | **already covered** |
| `P2` | `_compile_stars_fn` `PIntersection` → `fns[0](ctx)` | `2 failed, 96 passed` | **`84 passed`** | **EARNS ITS PLACE** |

**`P2` is the result.** The "short-circuit the fold to its first child" edit to the
intersection star fold is **invisible to the entire pre-existing corpus** — 84 passed,
nothing red — and reddens the moment the starred intersection is reachable. That is the
coverage `TK83` bought, stated as a mutation rather than as a shape.

`P1` is recorded as **already covered**, not claimed: `tests/test_matrix.py::test_matrix_4way_boolean`
catches `&` → `|` on `boolean_wildcards.fga` without this fixture. Saying otherwise would be
taking credit for an existing pin — and *"the new module reddens"* is a strictly weaker
claim than *"only the new module reddens"*.

### ⚠ The sweep found a hole in the new module, and closing it is the better finding

On the run above, the WITH arm for `P1` and `P2` named only
`tests/test_matrix.py::test_demorgan_oracle_equals_setengine_equals_graph` — **not one
assertion in `tests/test_star_admitting_intersection.py`**. The reason is `P6` step 2's
quiet failure verbatim (*"a mutation that does not move the property under test reports
`INERT` and reads exactly like a clean pin"*): the module's main workload leaves **both**
children of the intersection starred, so `&`, `|` and `fns[0]` all return the same set. The
mutation changed the fold and changed nothing the module looks at.

**Workload B** — the same store minus the `_all_users` star on `cond:c1`, which is the sole
source of `('role','role_user_met')`'s stars — leaves exactly one child starred and
separates the three candidate folds:

```
&            -> {}                  (shipped; MEASURED: no residue row at ('role','authorized_user','r3'))
|            -> {('user','...')}
fns[0](ctx)  -> {('user','...')}
```

`test_the_intersection_intersects_its_childrens_stars` pins it, and a re-sweep of the module
**alone** attributed all three mutations to that pin (`M0` control first, OK).

⚠ **Its first draft aimed the ceiling at a leaf family's residue row and reddened
immediately** — a `PClosureLeaf`'s stars live in the materialised closure, not in
`ResidueV1`, which carries derived relations only. Recorded because that is the ceiling
control working: a mis-aimed control that *passes* is the failure mode, and this one said so.

⚠ **INSTRUMENT LIMIT, and it bounds what the module-only table proves.** Under `P1`/`P2`
the red arrives as an **ERROR raised inside the fixtures**: `ParityEngine` asserts backend
unanimity and full-grid oracle parity inside every `add_tuple`, so it detects the divergence
while the store is still being built and the module's own assertions never execute. The pin
is *reached* and correctly attributed, but what fires is the engine, not the `assert`. That
is the shipped detector and is exactly the item's point — the shape is now reachable by
something that already checks equivalence — but it is **not** evidence that these particular
assertions are load-bearing.
