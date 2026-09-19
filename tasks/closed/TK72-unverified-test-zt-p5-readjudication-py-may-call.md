---
id: TK72
title: UNVERIFIED: test_zt_p5_readjudication.py may call check_invariants without schema_info (I14 off)
brief: CLOSED 2026-09-19f: 3 call sites fixed, false docstring corrected, AST census now refuses a silent revert
pri: NOW
size: S
deps: []
related: []
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-16b
moved: 2026-09-19f
updated: 2026-09-19f
closed: 2026-09-19f
---

## What it is

An UNVERIFIED claim, made in passing by the 2026-09-15 adversarial audit agent while
probing `P22`, and never checked by anyone since. Recorded here so it stops travelling as a
footnote on someone else's row.

THE CLAIM (AGENT-READ, NOT reproduced): `tests/test_zt_p5_readjudication.py` calls
`check_invariants` WITHOUT `schema_info`, which disables the I14 clause outright. If that
reproduces, an invariant clause is silently switched off inside a state gate -- the same
shape as `P22`'s green sabotage, where a clause existed and nothing could reach it.

## (!) Traps

- **(!) THE CLAIM IS A SUBAGENT'S AND IS EVIDENCE, NOT A FINDING** (`CLAUDE.md`
  sec Delegation). Step one is to reproduce it: read the call sites, and if `schema_info` is
  genuinely absent, confirm FIRST-HAND that the I14 clause is thereby skipped rather than
  defaulted. Do not act on the claim as stated.
- **(!) If it reproduces, the fix is not just "pass `schema_info`".** Ask what ELSE the
  clause would have caught in that module while it was off, and whether passing it turns
  the module red today. A clause that has been disabled for a while may be guarding
  something that has since drifted.
- **(!) The generalisable question is the valuable one:** is there any OTHER
  `check_invariants` call site in the tree that omits `schema_info`? A census is cheap and
  is the difference between fixing one module and closing the class. `P22` proved the class
  exists; this row is the second instance found.

## Read first

- `tests/test_zt_p5_readjudication.py` -- the call sites in question.
- `index_v4/invariants.py::check_invariants` -- what `schema_info` gates, and what the I14
  clause asserts when it is present.
- [`docs/p22-i14-corpus-masking-2026-09-16.md`](../docs/p22-i14-corpus-masking-2026-09-16.md)
  -- the sibling case, for the shape of "the clause was there and nothing reached it".
- `docs/adversarial-audit-2026-09-15.md` sec 2 -- where the claim was made, for provenance.

## Log

### 2026-09-17c

CONFIRMED FIRST-HAND. The row was filed UNVERIFIED (an agent claim inherited from `P22`); this session reproduced it by reading, not by trusting the report.

* The three call sites are `tests/test_zt_p5_readjudication.py:673` (`'live'`), `:677` (`'inc'`), `:678` (`'blk'`) -- all `check_invariants(session, <store>)` with no third argument. `index_v4/invariants.py:161` defaults `schema_info` to `None`.
* What that actually switches OFF is WIDER than the row's claim of "the I14 clause". With `schema_info is None` the gates at `invariants.py:256`, `:296` and `:343` skip: the rest of I3 (bridge completeness/exclusivity), **I14 crossing-middle completeness**, I4 namespace, AND all derived invariants (`_check_derived_invariants`). Roughly half the checker.
* The module's own docstring at `:657` claims "I1-I13 are green on all three". It is not.
* CENSUS of every `check_invariants` call site lacking `schema_info`, whole tree: 9 sites in 4 modules -- the three above, plus `tests/test_blind_audit_regressions.py:242`, `tests/test_invariants_docstring_matches_body.py:76` and `:84`, `tests/test_reg17_closure_fanout_cap.py:119`, `:147`, `:165`. Every OTHER call site in the tree passes `rs.schema_info` or `widx.schema_info`, so these are the outliers, not the idiom.
* (!) WHY THIS MAY BE MORE THAN A TIDY-UP: the corpus is `_OWC_TTU_CORPUS` (`:592`), whose object-wildcard shapes are `{('folder','viewer')}` -- the same shape family where `P22` found the I14 crossable-middle loop and `TK70` found the latent star cycle. The test compares live vs incremental-rebuild vs BULK state over that corpus with the bridge invariants disabled. Turning them on is a plausible route to a real red, not just a green-to-green docstring fix.
* NOT YET DONE: nothing has been changed. `ConnectedStore` exposes the handle as `self.widx.schema_info` (`connectedstore/store.py:194`), so the fix is mechanical; whether it goes RED is the open question.

Promoted to NEXT this session (user instruction: prioritize Python coverage / edge-case bug hunting).

CORRECTION to this session's own entry above, MEASURED not reasoned. The entry claimed passing `schema_info` here was "a plausible route to a real red, not just a green-to-green docstring fix", on the grounds that `_OWC_TTU_CORPUS` is the shape family of `P22`/`TK70`. **That is REFUTED.** The route does not exist, and the reason is exactly what the house rule says to check first.

PROBE: replicated both ZT-P5 corpora and both rebuild legs, calling `check_invariants(session, <store>, schema_info)` on all three stores (`live` / `inc` / `blk`), 147 checked calls. Literal output:

    === object_wildcard: 22 store subsets
        INSTRUMENT CONTROL, live SchemaInfo: {'crossable_shapes': [], 'bridged_in_shapes': [], 'bridged_out_shapes': [('folder', 'viewer')], 'derived_families': []}
        63 check_invariants(with schema_info) calls, 0 RED
    === object_wildcard_ttu: 29 store subsets
        INSTRUMENT CONTROL, live SchemaInfo: {'crossable_shapes': [], 'bridged_in_shapes': [], 'bridged_out_shapes': [('folder', 'viewer')], 'derived_families': []}
        84 check_invariants(with schema_info) calls, 0 RED

**READ THE CONTROL, NOT THE COUNT.** `crossable_shapes` is EMPTY on both corpora, so the I14 loop at `index_v4/invariants.py:296` iterates nothing; `bridged_in_shapes` is empty, so only the OUT half of the I3 bridge clause at `:266` has work; `derived_families` is empty, so `::_check_derived_invariants` at `:343` checks nothing. A green here is therefore **not** evidence that these corpora satisfy I14 -- it is evidence that **I14 was never applicable to them**. Without the control line this run would have read as "147 calls, all green", which is the failure-by-passing shape.

(!) The `[user, user:*]` subject wildcard in `_OWC_TTU_CORPUS` does NOT produce an in-bridge, so the corpus is not crossable despite looking like the `P22` shape. Crossability needs bridged IN and OUT; this has OUT only. **Anyone reaching for these corpora as a crossable fixture should stop here** -- that is a direct input to `TK75`, whose whole difficulty is finding a fixture with non-empty `crossable_shapes`.

REVISED DISPOSITION: `TK72` is a genuine but SMALL item -- the docstring at `tests/test_zt_p5_readjudication.py:657` claims "I1-I13 are green on all three" and that is false, and the three call sites should pass `cs.widx.schema_info` so the clauses that DO apply (I3-out, I4) actually run. It is NOT a bug route. It should not outrank `TK74` or `TK75`; consider demoting it back if a better candidate needs the NEXT slot.

Probe was `.scratch/tk72/probe.py` (gitignored, therefore already lost -- the transcript above is the tracked copy, per the `.scratch/` rule).

### 2026-09-19f

PROMOTED to NOW 2026-09-19f by the session that closed TK77/TK87, with the reasoning here
rather than on the banner. Three reasons, no new work done on this row:

1. It is the loose thread P22's close explicitly refused to pull ("NOT CLOSED HERE ... still
   UNVERIFIED and still deserves its own row"), and it is still labelled UNVERIFIED after
   three sessions in the I14 area.
2. If it is true, it is an assurance hole of the exact shape this repo calls the house
   failure mode: a module that runs the invariant checker with the I14 clause silently
   DISABLED passes for a reason unrelated to what it claims. TK77's census measured
   test_zt_p5_readjudication.py as the single largest crossable reacher in the suite, so
   this is the module where an I14 clause would matter most.
3. It is `S` and mechanically checkable: grep the `check_invariants` call sites in that
   module, look at whether `schema_info` is passed, and if it is not, decide whether the
   clause can be turned on without a corpus change. First-hand, not by agent report.

⚠ Do not assume the claim is true because it is old. It entered the tree as a subagent's
passing remark; CLAUDE.md sec  Delegation makes verifying it the first step, and TK67 is the
standing example of a trap that was nearly deleted because the subagent report about it was
wrong.

CLOSED 2026-09-19f. Outcome: the row's 2026-09-17c disposition ("a genuine but SMALL item
-- fix the three call sites and the false docstring, it is NOT a bug route") is CONFIRMED
and executed, and it gained the one thing that disposition did not name: a mechanical
refusal, because the fix was otherwise silently revertible.

(!) FIRST, A CORRECTION TO THIS ROW'S OWN BRIEF. The brief still read "UNVERIFIED: ...
verify FIRST", and the 2026-09-19f promote comment repeated that instruction -- but the
2026-09-17c log entry had already CONFIRMED it first-hand and censused every call site. The
brief is what the board prints, so a stale brief re-orders a session's work; it was the
promoting session (this one) that read the brief and not the log. Brief corrected at close.

LANDED (tests/test_zt_p5_readjudication.py): `_live_state` now returns
`(session, landed, cs.widx.schema_info)` and all three `check_invariants` calls in
`::test_zt_p5_object_wildcard_state_level_live_equals_rebuild` pass it, with an INSTRUMENT
CONTROL asserting `si.bridged_out_shapes` is non-empty so the enabled clause cannot iterate
nothing unnoticed. The docstring's false "I1-I13 are green on all three" is replaced by what
is actually run, plus the narrowing the 2026-09-17c probe measured and this session
re-measured: `crossable_shapes` is EMPTY on both corpora, so **I14 still checks nothing
here** -- the clause the handle really turns on is I3 bridge completeness/exclusivity.
Module green, 21 passed.

EVIDENCE THE ARGUMENT BUYS COVERAGE (formal/probes/tk72_schema_info_gate_2026-09-19.py,
MEASURED 2026-09-19f). Delete one `w_all -> concrete` bridge edge and decrement the two
endpoint refcounts, so every schema-INDEPENDENT clause stays satisfied:

    sabotage: deleting the bridge folder:*#viewer[all] -> folder:f1#viewer,
    and decrementing both refcounts by 1
      WITHOUT schema_info  GREEN
      WITH schema_info     RED   I3: concrete id=2 ... name='f1' predicate='viewer'
        type='folder' ... of bridged-out shape missing its w_all->concrete bridge

(!) THE PART THE ROW DID NOT ASK FOR, AND THE REASON IT WAS NEEDED. Nothing went red when
the three sites were fixed, and nothing would go red if they were un-fixed -- `schema_info`
defaults to None and the reduced checker returns cleanly. So the fix was invisible in both
directions. NEW:
`tests/test_invariants_docstring_matches_body.py::test_every_schema_backed_check_invariants_call_passes_schema_info`
-- an AST census of every `check_invariants` call site in the repo, with an EXACT allowlist
(both directions: a new bare site FAILS, and an allowlisted site that gains a handle FAILS as
rot) and a ceiling control floor of 40 sites so a broken walk cannot pass by scanning nothing.

CENSUS RE-VERIFIED FIRST-HAND, and the row's remaining six sites are NOT defects: all six
(`test_blind_audit_regressions.py`, `test_invariants_docstring_matches_body.py` x2,
`test_reg17_closure_fanout_cap.py` x3) build a raw `index_v4.ReachabilityIndex`, which has no
`schema_info` attribute at all -- there is no handle in scope to pass. They are the
allowlist, each with its reason at the entry.

SWEEP (formal/probes/tk72_callsite_sweep_2026-09-19.py): 6 mutations, 4 CAUGHT -- `S0`
harness control, `S1` revert one ZT-P5 call site, `S2` drop an allowlist entry, `S4` blind
the AST walk (the floor fires: "only 0 check_invariants call site(s) found, floor 40"). Two
INERT, both predicted and stated: `S3` a no-op edit, and `S5` weakening the ZT-P5 instrument
control to `or True` -- a control claims nothing while its subject is unchanged.
