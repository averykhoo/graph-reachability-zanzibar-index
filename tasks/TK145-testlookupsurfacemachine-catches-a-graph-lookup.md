---
id: TK145
title: TestLookupSurfaceMachine catches a graph lookup_reverse exclusion drop in only ~half of ci runs
brief: G1 caught 4/8 machine runs (database=None); measure M1 too; make deterministic or document the rate
pri: LATER
size: S
deps: []
related: [TK142]
parent:
labels: []
source: docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md
source_hash:
created: 2026-10-14
moved: 2026-10-14
updated: 2026-10-14
closed:
---

Residual of TK142 (challenge C2, `docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md`), not closed by the TK142 build (worktree-wf_9a094007-20b-11 @69080d4 did not touch `tests/test_lookup_hypothesis.py`).

`tests/test_lookup_hypothesis.py::TestLookupSurfaceMachine` catches G1 (`WildcardIndex.lookup_reverse` clears `excluded_node_ids`) only PROBABILISTICALLY. Challenge PROBE 2026-10-14 (`c4_machine_catch_rate.py`, ci settings, `database=None`, generate phase only): **G1 caught 4/8 runs**; every catch was `graph.lookup_reverse('does_not_label', 'attr', 'at1') vs oracle on subject (...,doc,dc1): graph=True oracle=False` on the `demorgans_reverse` corpus. REASONED: M1 (set side) should have a similar rate; UNVERIFIED as a rate. The scout's "blind" was one draw.

The deterministic catch now lives in the seeded gates TK142 added (demorgans walk_steps=12, boolean seed 4, the generated-schema exclusion witness), so this row is about the machine's own honesty, not about an uncaught regression.

Options (REASONED, none measured): (a) record the machine as a probabilistic second instrument and say so in its docstring; (b) bias the machine's rules toward the exclusion shape (a subject wildcard under `but not` / `and` with an interned refused subject) and re-measure the catch rate under G1 and M1 with `database=None`; (c) add an `@example` / explicit-phase seed that reaches the shape so every ci run sees it at least once.

Done when: the machine's catch rate under G1 and M1 is measured over >= 8 runs with `database=None` and either brought to deterministic or recorded as probabilistic in its docstring with the measured number and date.

## Traps

- Never use HYPOTHESIS_SEED (refused by tests/conftest.py); use --hypothesis-seed=N.
- Under a sabotage run with `database=None`, or the `.hypothesis/` example DB replays a stored failure and looks deterministic.

## Read first

- `docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md` (Corrections, C2 and C3).
- `tests/test_lookup_hypothesis.py` (LookupSurfaceMachine, the ci profile).

## Log
