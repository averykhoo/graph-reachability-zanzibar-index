---
id: TK146
title: hypothesis Phase.reuse / example DB can replay a stored failure and fake a sabotage catch
brief: ci profiles keep Phase.reuse and the .hypothesis DB; a sabotage run can pass on a replay
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

Residual of TK142 (challenge C3, `docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md`), not closed by the TK142 build (worktree-wf_9a094007-20b-11 @69080d4 changed no hypothesis profile).

Hypothesis REPLAYS stored failures, so a sabotage run can fake a catch. READ 2026-10-14: the `ci` profiles in `tests/test_lookup_hypothesis.py` and `tests/test_hypothesis.py` include `Phase.reuse`, and no profile sets `database=None`. The challenge's G1 run saved a failing machine example under `.hypothesis/` (gitignored); a later sabotage of the same machine replays it and reads as a deterministic catch. That is an assurance step that can pass for the wrong reason, the house failure mode, applied to the sabotage instrument rather than the subject.

Options (REASONED, not measured): (a) a mechanical refusal or switch for sabotage runs, e.g. an env-driven profile (`HYPOTHESIS_PROFILE=sabotage`) with `database=None` and no `Phase.reuse`, named in `docs/sabotage-procedure.md`; (b) drop `Phase.reuse` from `ci` (cost: a real local failure no longer replays first); (c) at minimum, a dated line in `docs/sabotage-procedure.md` saying to run hypothesis tests under a mutant with `database=None` or to record that a replay was possible.

Done when: a sabotage run of a hypothesis test cannot be satisfied by a replayed example without that being visible, demonstrated by a run that would have replayed (stored failure present) and did not.

## Traps

- HYPOTHESIS_SEED does nothing (tests/conftest.py refuses it); only --hypothesis-seed=N.
- CI (`.github/workflows/`) also runs these profiles; a profile change reaches CI too.

## Read first

- `docs/tk142-lookup-oracle-exclusion-gap-2026-10-14.md` (Corrections, C3).
- `docs/sabotage-procedure.md`.
- `tests/test_lookup_hypothesis.py` (register_profile).

## Log
