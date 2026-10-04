# TK117 (c) -- the ParityEngine grid gets a write-local floor: decision, pins, sweep (2026-10-04)

**FROZEN 2026-10-04c, at `TK117`'s close -- provenance, not a living document.** Status lines
below are as-of-then. In particular, sec 5's "still open" items were NOT done: the row closed
with the user's agreement, because (a) and (b) are covered elsewhere (see the close message,
`python scripts/task.py show TK117`). Corrections are appended dated at the top, never edited
into the body.

Row: `python scripts/task.py show TK117`. Filed from `docs/p10-scope-audit-2026-09-27.md`
sec 5 H7. The 2026-10-03c triage scoped the first step to part (c) alone
(`docs/promote-next-triage-2026-10-03.md` sec 4).

## 1. The gap (evidence AGENT-PROBED 2026-09-28, RE-WITNESSED first-hand 2026-10-04)

`tests/parity.py::ParityEngine._grid` built Layer A (every grid subject x every declared or
leaf target x every known object name plus a ghost), then, above `grid_cap` (default 600),
replaced it with `self._rng.sample(queries, self.grid_cap)`. It had no floor. A backend lie
confined to the last write's own queries therefore escaped with probability about
`(N - cap) / N`.

The P10 verifier's probe (`.scratch/wf-0927/probes/parity-grid-cap-sampling/verify2/v2_probe.py`,
gitignored) used `tests/fga_schemas/github.fga` with 14 writes, the last being
`user:hank maintainer repo:docs`. It planted a graph lie on that write's own check, and the
lie escaped at cap 600 on 8 of 20 seeds (15 of 20 on an independent store). The literal
output is quoted in `tests/test_tk117_write_local_floor.py`'s module docstring.

Re-witnessed first-hand this session: the module's `no_floor` controls run the same lies
with the floor stubbed out, and each control finds at least one escaping seed (sec 3).

## 2. The decision (taken by the session under `CLAUDE.md` "Who decides", 2026-10-04c)

`ParityEngine._grid(last)` appends `ParityEngine._write_local_floor(last, subjects, targets,
have)` after the cap. The floor is:

- the op's own tuple, plus
- every grid subject x every target relation (declared UNION leaf families) whose object type
  is the written object's type, at the written object's name,
- minus whatever the sample already holds (no duplicates).

It is rng-free and applied to adds and removes alike. `_apply` passes `last=raw` through
`_assert_grid_parity`.

**Why the written OBJECT, not only the op's own tuple** (REASONED, then pinned): a userset
write (`team:t2#member admin repo:r6`) changes the answer for subjects that never appear in
the tuple (`user:u3`, a member through nested teams). A floor of the own tuple alone misses
that; sweep mutation M1 is exactly that weakening, and it goes RED.

**Why it is applied BELOW the cap too.** Below the cap the pool already holds every floor
query, because the written object's name is noted before the grid is built. So the floor adds
nothing, which `test_below_the_cap_the_floor_adds_nothing` pins as byte-identity. The one
exception is an object-wildcard write: its object is `*`, which `_note_names` never lists. So
the floor is the only place an object-`*` query is ever asked. A capped-only floor would ask
it on large stores and not on small ones, an asymmetry with no reason behind it. M5 is that
weakening, and it goes RED.

**Rejected alternative: a true delta-affected set** (the spec's *"delta-affected pairs UNION
a sampled grid"*, boolean spec sec 8.4). It is computed by evaluating the oracle over the
whole pool before and after every op. The oracle is the expensive side, so this costs what
the cap exists to avoid. The written-object floor is the cheap approximation, and its limit
is stated in sec 4.

**Cost** (date-keyed measurement, 2026-10-04): with the P10 settings (cap 600, 20 seeds),
the new module took `371 s`. It now runs at cap 100 with 5 seeds, in about `60 s`. Neither
setting affects the floor, which is rng-free; the controls need only one escaping seed.

## 3. Pins and the mutation sweep (RUN first-hand 2026-10-04c)

Pins: `tests/test_tk117_write_local_floor.py`, ten tests:

- precondition: `test_the_store_is_capped_and_the_lie_is_a_real_divergence`;
- four claims, each with a `no_floor` control that must ESCAPE:
  - `test_a_lie_on_the_last_writes_own_check_is_caught_on_every_seed`
  - `test_a_userset_write_floors_its_expanded_members_at_the_written_object`
  - `test_a_remove_is_floored_too`
  - `test_an_object_wildcard_write_is_asked_at_its_star_object`
- byte-identity: `test_below_the_cap_the_floor_adds_nothing`.

Sweep: `.scratch/tk117/mutsweep.py` (gitignored; this table is the tracked record). It ran
the module per mutation, asserted each anchor at count 1, and restored the file in a
`finally`. It ran with no outer timeout. The baseline was `10 passed`.

| mutation | verdict | failed tests |
|---|---|---|
| M0 control: the own-check pin claims `after remove` | RED 1 | exactly that test -- attribution works |
| M1 floor = own tuple only | RED 2 | userset, object-wildcard |
| M2 removes not floored | RED 1 | remove |
| M3 floor appended BEFORE the cap (sampled away) | RED 3 | own-check, remove, userset |
| M4 first subject only | RED 2 | userset, object-wildcard |
| M5 floor only above the cap | RED 1 | object-wildcard |
| M6 dedup forgets what it added | INERT | -- (below) |
| M7 object-type filter dropped | RED 1 | below-the-cap identity |
| M8 floor at a ghost object, not the written one | RED 2 | userset, object-wildcard |
| M9 floor never applied (`if last is None`) | RED 6 | all four claims + identity + precondition |
| M10 own tuple dropped from the floor | INERT | -- (below) |

M9's red on the precondition test is a `TypeError` (the mutant calls the floor with
`last=None`), not that test's property. Its other five reds are property failures.

**M6 is INERT by construction (REASONED).** `have.add` only stops one query from being asked
twice. A duplicate query is redundant work and changes no verdict.

**M10 is INERT by construction (REASONED).** Admission accepts a tuple only if its subject
shape is a Direct restriction of the relation. `subjects` lists every such shape with every
noted name plus `*`. The relation is a declared target of the object's type. So the own tuple
is always inside the subject x relation product. The explicit `[last]` is kept: it states
the intent, and it survives a future change to how `subjects` is built (part (b) changes
exactly that).

## 4. The stated limit

Effects that land on OTHER objects stay sampled. Examples: a TTU child of the written object
(`doc` under a written `folder`), and an object whose restriction names the written userset.
A lie confined to those can still escape above the cap. The spec's delta-affected set would
cover them, at the cost given in sec 2.

## 5. What is still open on `TK117` (first-hand READ 2026-10-04c)

- **(a) object-`*` targets for every object-wildcard SHAPE.** The floor now asks `T:*` only
  at a write that named `T:*`. The 2026-10-03c skeptic (AGENT-REPORTED) said this is covered
  elsewhere: `tests/test_matrix.py` `union_wildcard`.
- **(b) star from-chain userset subjects** (`doc:*#r0`). Not touched. The skeptic says it is
  covered by `tests/test_lookup_oracle.py::_subject_candidates` and the star-bridge hypothesis
  machines.
- **`tests/genswarm.py::grid_for` (cap 400).** Same bare `rng.sample`. But `Diff.sweep` runs
  once per driven SUBSET, not per op, so the analogue is a floor over the objects the subset
  wrote. That is a different design; not done.
- **`tests/test_hypothesis.py::_grid` has NO cap** (first-hand READ). The row's fix list named
  it, but it has no sampling gap. Nothing to do there.
- `docs/spec-deviations.md` 2026-07-07 item 2 says *"full-grid"* and *"sampled above a cap"*
  in one entry. That is reconciled by the `## 2026-10-04c` entry there, which states what the
  per-op grid now guarantees.
