2026-09-01c — gate re-run after the doc edits; verdict line in the session-log entry.

(nav) **STEP 7's PREDICATE IS LANDED (2026-09-01c) as `ComputedRefsNotLeaf` — the step's
named premise was FALSE.** Python **dot-locks** referenced relation names rather than
requiring declaredness: an UNDECLARED operand is accepted and compiled, only a dotted one
raises, so `ComputedRefsDeclared` would be stricter than Python. **Binder DEFERRED, design
settled** — trap (g)'s way out is `ReconcileStars.lean:622`, which discards an in-scope `hr'`.

(!) **"STEP 7" IS AMBIGUOUS — three numberings are live and the board mixed them.** `hql`
is **step 10**, not 7; step 9 (the flip) is what it co-lands with, and it is NOT landable
before then — `graph_correct` is a proved theorem of today's tree.

(!) **INERT, so its 8 pins are the SOLE evidence.** S1 was a verdict on the PINS, not the
code. Sizing: 14 call sites, not 11.
