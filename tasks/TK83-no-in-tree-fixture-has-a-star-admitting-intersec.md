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
moved: 2026-09-20f
updated: 2026-09-20f
closed:
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
