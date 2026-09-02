2026-09-03 — SAB-5 discharged; the `P6` remainder was MIS-SIZED and is blocked on a human call.

(nav) **`P3` IS LEAN WORK AFTER ALL — this banner said the opposite until today.** The write
path was never re-pointed: `LeafRules.lean:246 writeRulesRaw` still says `No caller yet` and
`Cascade.lean:175` still folds `rewriteClosure`, not `rewriteClosureL`. 4c-ii re-pointed the
PROOF-side shadow, not the driver, so Lean and Python edge targets do NOT agree.
(!) **THE `0`/`265` CRITERION IS MET BY A TWO-LINE DELETION THAT PROVES NOTHING.** Observed
2026-09-03: deleting `extractor.py:236-237` gives `P6 0 / compared 265` **and** reds the state
gate — `19 failed, 37 passed`. Control is `test_conformance_state.py`; ledger **76 / 189** of 498.
(!) **BLOCKING HUMAN CALL:** post-re-point `graph_correct` is FALSE AS WRITTEN without `hql`.
(!) **§11.13 (z): THE DEFINITION PIN MISSES DOT-NOTATION CALLS** — no `def:` row exists for
`writeLoggedRules`, so re-pointing its body leaves step 4c GREEN. Control is the state gate.
(!) **SAB-5 WAS MIS-INSTRUMENTED:** `statement_pin.py` never builds Lean — run it DIRECTLY and
a deleted field reds 4c **while 4b stays 49/49**. Owed: a BUILD-SURVIVING mutation for 4c.
