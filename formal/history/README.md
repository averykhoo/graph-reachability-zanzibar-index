# formal/history/ — the historical record of the (now-complete) proof effort

These three documents are the **provenance archive** of the Lean formal-verification
effort. The effort is complete; for day-to-day orientation they are **superseded by
[`../ARCHITECTURE.md`](../ARCHITECTURE.md)** (the durable topical map) and
[`../FINAL_REVIEW.md`](../FINAL_REVIEW.md) (the exact, clause-checked claim). They are
kept for the record — especially the attack-first kills, the staged-widening designs,
and the decision rationale that only ever lived here.

| file | what it is |
|---|---|
| [`PROOF_STATUS.md`](./PROOF_STATUS.md) | the **append-only session ledger** (newest entry first): per-session resume points, the theorem ledger, decisions with rationale, and every attack-first refutation as it happened. The living detail behind each closed stage. |
| [`ROADMAP.md`](./ROADMAP.md) | the **staged-widening designs + post-mortems**: the per-stage plan (W1 → W2 → W3a…d → W4) and the "honest gaps" inventory, written as the work was scoped and re-scoped. |
| [`REVIEW.md`](./REVIEW.md) | the **early one-shot session digest** (2026-07-09 → 10): the first-overnight "what happened and what to check" summary, including the `fuelBound` spec-bug find. |

## About the stage names (W1–W4, T0–T6, the dated `12k`/`12m` tags)

The `W`-stages (`W1`, `W2`, `W3a`…`W3d-2`, `W4`) and the dated session tags are the
**timeline scaffold** of how the graph-index theorem was grown incrementally — from
the pure-direct fragment out to the operational two-round cascade. They are explained
here and are **not load-bearing for the current claim**: the final theorems live
unsuffixed in `../lean/ZanzibarProofs/FullScope.lean` over the operational closure
`ReachedBy := ReachedByW3d2E`, and the honest scope is stated topically (not by stage
name) in `../ARCHITECTURE.md` and `../FINAL_REVIEW.md`. The `T`-labels (`T0`–`T6`) are
the durable theorem IDs and do survive into the topical docs — see the theorem table
in `../ARCHITECTURE.md`.

Where a stage-era note here and the current code disagree on a name, **the code wins**
(and `../ARCHITECTURE.md` / `../CORRESPONDENCE.md` track the code).

**A note on links.** These documents were written while they lived in `formal/`, and are
kept verbatim (the ledger is append-only — editing it retroactively would violate the
honesty norm). Their internal cross-links to sibling docs (`HANDOFF.md`, `SEMANTICS.md`,
…) therefore read as if from `formal/`; resolve them against `../` from here.
