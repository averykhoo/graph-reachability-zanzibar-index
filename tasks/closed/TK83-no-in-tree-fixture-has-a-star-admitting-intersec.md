---
id: TK83
title: no in-tree fixture has a star-admitting intersection with a derived dep
brief: starred half-stale intersection diverges in the RESIDUE too, refuting 9.5; reachable only on a constructed fixture
pri: NOW
size: S
deps: []
related: [TK74, TK77]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-18c
moved: 2026-09-20g
updated: 2026-09-20g
closed: 2026-09-20g
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18c

Measured under the section 9.10 sweep; full write-up is docs/tk74-staleness-net-2026-09-18.md section 10.5 (verified first-hand by the session, not just agent-reported).

WHAT IS TRUE. Exactly 3 PIntersection nodes exist in the tree: boolean_wildcards (doc,restricted) stratum 0 deps=(); demorgans_law_2 (role,authorized_user) stratum 4 deps=((role,role_user_met),); tupleset_shapes (doc,approved_parent) stratum 0 deps=(). NONE has both a non-empty Plan.deps AND a star-admitting leaf child -- boolean_wildcards has the star but nothing to go stale, demorgans_law_2 has the dep but assigned: [user] is star-free. So the starred half-stale intersection is UNREACHABLE in-tree.

WHY IT MATTERS. Changing ONE token in demorgans_law_2.fga (assigned: [user] -> [user, user:*]) makes it reachable, and it is NOT clean. Section 9.5 recorded that a half-stale intersection writes NO residue and that the divergence is carried entirely in materialized closure edges. That is an artifact of the star-free leaf. With the star, the intersection DOES write a residue -- (role,authorized_user,r3) stars=[["user","..."]] -- and in 2 of 4 star-tight arms that row is present-and-starred when correct and ABSENT when stale, with the loss propagating to (doc,access,d2). One arm diverges FAIL-OPEN. Nothing catches it: settle 0/144, and off/residue/full all err=none (tier read back off the guard; a planted dead node id in that same row proves residue/full CAN go red there).

NOT A LIVE BUG. Needs a constructed fixture plus deliberate fault injection -- same class as TK74. The board 0 stays 0.

THE ITEM. Add a star-admitting intersection fixture to tests/fga_schemas/ so the case stops being unreachable, and let the matrix/hypothesis campaign cover it. Starting point: .scratch/tk74d-starisect/star_isect.fga (gitignored -- copy it into the tree, do not cite it as evidence).

TRAP: do NOT write "the residue always differs" -- 2 of 4 star-tight arms show the diff, the other 2 have no residue on either side at that op prefix. That a GENERAL starred intersection diverges is REASONED, not measured.

### 2026-09-20e

PROMOTED LATER -> NEXT on coverage-hole grounds, and the STARTING POINT IS NOW IN THIS ROW
so it stops depending on a gitignored file.

Ranked above `TK71` (the other `S` assurance-gap candidate) because this row is already
MEASURED and its action needs no further scoping: the divergence is real, one arm is
FAIL-OPEN, and the work is "put the fixture in the tree and let the matrix/hypothesis
campaign reach it". `TK71`'s own next action is still a measurement to settle its own scope
((a) vs (b), and the `== 132` pin), so it stays `LATER`.

(!) SALVAGE, 2026-09-20e. This row's only starting point was
`.scratch/tk74d-starisect/star_isect.fga` -- gitignored, i.e. already lost by the repo's own
rule. Verified present and transcribed here first-hand (28 lines, `wc -l`). It is a starting
point, NOT evidence: copy it into `tests/fga_schemas/`, do not cite this block as a result.

    model
      schema 1.1

    type user

    type attr
      relations
        define _all_users: [user:*]
        define has_attr: [user]
        define missing_user: _all_users but not has_attr

    type cond
      relations
        define _all_users: [user:*]
        define requires: [attr]
        define user_missing_requirement: missing_user from requires
        define user_met_requirement: _all_users but not user_missing_requirement

    type role
      relations
        define assigned: [user, user:*]
        define match_any: [cond]
        define role_user_met: user_met_requirement from match_any
        define authorized_user: assigned and role_user_met

    type doc
      relations
        define associated_role: [role]
        define access: authorized_user from associated_role

The one token that matters versus the in-tree `demorgans_law_2.fga` is `assigned: [user,
user:*]` -- that is what makes the intersection star-admitting and the half-stale case
reachable.

### 2026-09-20g

CLOSED. The fixture is in the tree, it is driven 4-way, and a mutation sweep shows it
catches something the whole pre-existing corpus does not.

Map: `docs/tk83-star-intersection-fixture-2026-09-20.md` (ACTIVE-PLAN, freeze it now).
Probe: `formal/probes/tk83_star_intersection_2026-09-20.py`, verbatim stdout in its
docstring.

WHAT LANDED. `tests/fga_schemas/star_admitting_intersection.fga` -- `demorgans_law_2.fga`
with one token changed (line 21, `assigned: [user]` -> `[user, user:*]`), transcribed from
the row's own salvaged block. It is the ONLY plan in the corpus with both a non-empty
`Plan.deps` and a star-admitting leaf child (MEASURED; the three intersections sec 10.5
censused are re-measured as an instrument control, star column included). Wired into
`test_matrix.py::test_demorgan_...` (static 4-way), `test_reads.py::test_grid_parity_demorgans`
(walking), `test_schema_ast.py::test_compile_accepts_booleans`, `test_boolean_compile.py`,
plus a golden. New module `tests/test_star_admitting_intersection.py`, 11 pins.

sec 9.5 IS REFUTED FROM THE TREE. `('role','authorized_user','r3')` carries
`stars=[["user","..."]]`; the one-token twin has NO residue row at that key at all (5 rows vs
4) and `stars=[]` one relation further at `('doc','access','d2')`. `check(bob, access, doc:d2)`
is True on the new fixture and False on the twin -- unanimous across graph, both set engines
and the oracle, since every check is a ParityEngine check.

(!) SCOPE, because the row's headline invites over-reading. This closes a REACHABILITY gap.
It does not re-run sec 10.5's 144 fault-injection arms and says nothing about the settle pass
or the paranoia tiers under a skipped reconcile -- that is `TK74`, untouched. The FAIL-OPEN
arm is NOT reproduced here and stays UNVERIFIED by this session. "Live correctness bugs: 0"
is undisturbed.

(!) THE SWEEP IS THE EVIDENCE, AND ONE ROW IS A REFUSAL TO TAKE CREDIT. Each production
mutation ran twice over the same targets, WITH the fixture and WITHOUT (`-k "not
star_admitting"`, 14 deselected = the pre-2026-09-20g corpus). `M0` control attributed
correctly to 6 named pins.
  P1  intersection star fold `&` -> `|`        WITH 4 failed / WITHOUT 2 failed -> ALREADY COVERED
  P2  intersection star fold -> `fns[0](ctx)`  WITH 2 failed / WITHOUT **84 passed** -> EARNS IT
P2 is the result: that edit is invisible to the entire pre-existing corpus. P1 is recorded as
already covered because `test_matrix_4way_boolean` catches it on `boolean_wildcards.fga`.

(!) THE SWEEP FOUND A HOLE IN THE NEW MODULE and that is the better finding. On the main
workload BOTH children of the intersection are starred, so `&`, `|` and `fns[0]` coincide --
`P6` step 2's quiet failure, an edit that moves nothing the pins look at. Workload B (one
child starred) separates them; `test_the_intersection_intersects_its_childrens_stars` pins it
and a module-only re-sweep attributed all three mutations to it. Its first draft aimed the
ceiling at a leaf family's residue row and reddened -- a `PClosureLeaf`'s stars live in the
closure, not in `ResidueV1`.

(!) INSTRUMENT LIMIT: under P1/P2 the red arrives as an ERROR inside the fixtures, because
ParityEngine asserts unanimity and grid parity inside every `add_tuple` and catches the
divergence while the store is still being built. The pins are REACHED and attributed, but
what fires is the engine, not the assert.

(!) TWO THINGS FOUND EN ROUTE, both in places this row had no reason to look.
1. `test_boolean_compile.py` split its fixtures with TWO hardcoded index slices
   (`ALL_FIXTURES[:4]` / `[4:]`). Inserting a boolean fixture at index 4 reddened -- by LUCK,
   because the complement slice asserts a schema has no tainted relations. Appending at the
   END would have been SILENT, exactly how `owc_star_ttu.fga` spent its life in the weak leg.
   The split is now derived from the schema (an AST scan, deliberately not `compiled.tainted`)
   with a module-level anti-vacuity assert. Third time this tree has been bitten by a
   hand-maintained list beside a derivation.
2. The fixture makes `demorgans_law_2` score "subsumed" too -- each masks the other. Listing
   them in `KNOWN_SUBSUMED` (= retirement candidate) would have invited deleting what this
   row just landed. New `test_schema_shapes.py::MASKED_PAIRS` holds them out, and the
   exemption is EARNED mechanically: `test_masked_groups_are_really_masked` asserts each
   member is subsumed, is NOT subsumed once its partner is dropped, and that dropping the
   group loses something (MEASURED: 0 features, 6 pairs); `test_masked_groups_cite_a_live_guard`
   resolves the `file::symbol` each group names. Sweep: M0-M4 all RED and attributed.
   (!) M5 is INERT: widening the register's own exemption is caught by nothing, because a
   test cannot observe its own neutering. That is worth carrying as a property -- THE
   SUBSUMPTION REGISTER IS A REPORT, NOT A GUARD. The fixture's actual protection is
   `test_corpus_has_a_star_admitting_intersection_with_a_derived_dep`, and it has to be
   structural: MEASURED, the symmetric difference of the two fixtures' genswarm features is
   EMPTY, so both corpus floors stay green with the fixture deleted.
