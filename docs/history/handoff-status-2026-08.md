# HANDOFF archive — 2026-08

**FROZEN 2026-08-11 — provenance, not a living document.** Status lines below are
as-of-then and several may now be false; live state: `HANDOFF.md` + the session
ledger. Corrections are appended dated at the top, never edited into the body.

Retired from [`HANDOFF.md`](../../HANDOFF.md) on **2026-08-11**, when the 2026-08-10
TTU-tupleset fail-open family was closed and the gate went green end to end. This is
**provenance, not a living document** — nothing here is an open action. It is the direct
sequel to [`handoff-status-2026-07.md`](handoff-status-2026-07.md).

What is here, and why it was kept rather than deleted:

* **§1 / §1a / §1b** — the RC1+RC2 arc as it was briefed while open: the divergence
  filing, the fix list, and the generator-coverage leg that made RC2 visible. Kept for
  the *method* (three instruments sharing no derivation; the severity-sign rule; the
  measured-FALSE mechanisms a reader would otherwise have acted on), not the status.
  ⚠ **Status lines in here are frozen as-of-then and several are now wrong** — e.g. §1's
  "Still owes the 6-seed fuzz sweep" and "When you fix it", §1a's whole premise, and
  §1b's "Incidental finding, reported not fixed" (fixed 2026-08-11). Read
  §"What landed 2026-08-11" — which now lives **in this file**, under
  §"Retired 2026-08-16 (leg 7 4c-i session)" — for the true end state. (Repointed
  2026-08-16: it used to say "read `HANDOFF.md`'s", and that block has since been
  archived here.)
* ⚠⚠ **Every LINE NUMBER below is pre-fix, and one of them now inverts its own meaning.**
  `bulk_backfill.py:454` is cited repeatedly as the RC2 fix site. True then; **FALSE now** —
  the fix inserted `_stored_tupleset_subjects`, so post-fix `:454` lands inside
  `_stored_userset_subjects`, the one clause deliberately left ALONE. Resolve everything
  here by `file::function`, never by line.
* **Completed board items** — the 2026-08-08/09 legs, each carrying findings that
  corrected live documents at the time.
* **§"Retired 2026-08-16 (leg 7 4c-i session)"** and **§"Retired 2026-08-16b — the
  handoff-system migration (second batch)"** — two *different* batches retired on the same
  date. The `b` batch is the narrative half of `HANDOFF.md`, moved out when that file was
  rewritten into a priority board; it carries its own "Corrections applied on archiving"
  list, and ⚠ its deictic references ("this file", "the banner above", "item 3") point at
  the pre-rewrite `HANDOFF.md`. Cite these two by full title — a bare date is ambiguous.

---

## 1. The two TTU-tupleset divergences — BOTH FIXED (RC1 `ed46e54`, RC2 2026-08-11).

*Kept for the method, not the status.* The reusable parts are the severity-sign rule
below, the three-independent-instruments structure, and the record of which mechanisms
were measured FALSE — a reader who acted on the original filing would have rewritten
correct leaf-routing code.

**★★ These are AUTHORIZATION FAIL-OPENS, not under-reports.** Read through a negated TTU
(`define access: [user] but not viewer from parent`) the graph **GRANTS what the oracle and
both set engines DENY** — `oracle=False graph=True sets=[False, False]`, verified by hand
for both causes. The general rule worth carrying: **a dropped TTU parent is a false NEGATIVE
under a positive TTU and a false POSITIVE under a negated one**, so probing only the
positive direction mis-classifies severity by one sign. That is exactly what the original
filing did. *(No deployment exists — the store is a plain callable API — so this is a
library correctness defect, not an exposed system.)*

**There are TWO independent root causes**, both dropping a STORED tupleset tuple that
`CLAUDE.md`'s rule ("TTU parents are STORED tupleset tuples, never computed membership")
requires the TTU to walk. A bounded exhaustive sweep (2,302,854 queries over 346 compiled
schemas) found **26 distinct minimized divergences and exactly these 2 causes** — so the
family is mapped and closed at two.

* **RC1 — ✅ FIXED 2026-08-10.** `zanzibar_utils_v1.py::_member_types` returned
  `walk(e.base)` for an `Exclusion`, so on `define parent: [folder] but not [doc]` the type
  `doc` never entered the compiled `parent_types` and `processor.py::tupleset_parents`
  dropped the stored parent. Now `walk(e.base) | walk(e.subtract)`, with the docstring —
  which encoded the same mistake in prose — rewritten to say why both arms count.
  **All five callers pass a `tupleset_rel`**, so the function only ever answers "what types
  can a TTU parent have" and the widening is scoped exactly to that question.
  **`parent_types` is compiled once (`zanzibar_utils_v1.py:1761`) and frozen onto the plan
  node, which `processor.py` and `bulk_backfill.py` merely READ — so this one fix repaired
  the incremental AND bulk paths together**, no `bulk_backfill.py` edit needed.
  Verified: `formal/conformance/` **494 passed**, `tests/test_bulk_build.py` green,
  byte-identity snapshots survive, and both RC1 pins plus their controls now pass.
  ⚠ Still owes the 6-seed fuzz sweep — it is an algorithm change (item 5 below).
* **RC2 — NOT CHEAP. Budget a design decision, not a filter tweak.** The `n.wildcard == ''`
  clause of the same filter drops a stored `T:*` parent when the tupleset relation is
  derived (no exclusion, no object wildcard needed). Deleting the clause **breaks admission
  parity** (`accept/reject divergence on add ('...','doc','*','parent','doc','d1'):
  graph=False set:py=True`) and widening it naively **crashes** at `index_v4/core.py:914`
  (`name=='*' and a non-empty wildcard must go together`). The star parent has to be
  **represented** — the set engine's `MemberSet.stars` algebra is the analogue to port — not
  merely admitted. RC2 **does** need the duplicated fix at `bulk_backfill.py:454` alongside
  `processor.py:320`.

**⚠ The mechanism recorded before this session was FALSE** and would have sent you rewriting
correct code. It said the graph "respects the boolean evaluation of the tupleset relation"
and the storage-leaf split "is not being honoured". Measured otherwise: the split IS applied
(`plan(doc,parent).leaves` = `parent.0` + `parent.1`, both `storage=True`), the write DOES
land on a storage leaf (`doc:d2#... -> doc:d1#parent.1`), `derived_stored_parents` DOES reach
it, and the read path never evaluates `parent`'s plan. The loss is **compile-time metadata
only**. Corrected in `docs/spec-deviations.md` 2026-08-10 (which keeps the wrong version
struck-through, deliberately, so the bad reasoning is visible rather than deleted).

**Why nothing caught it, all three measured:**
* **No invariant I1–I14 catches either, and I9 structurally CANNOT** — it re-runs
  `reconcile`, which reads the same wrong `parent_types` and agrees with itself. *The
  instrument shares its subject's defect.* Paranoia was ON and stayed green. A new
  compile-time invariant (checking `parent_types` covers every type admission accepts onto
  the tupleset's storage leaves, read from the emitted `RewriteFilter`s rather than from
  `_member_types`) was prototyped and validated RED-before/GREEN-after — worth landing.
* **The hypothesis campaign cannot reach the shape at ANY budget** — see item 1b.
* **The bulk-vs-incremental identity gate is BLIND to the RC2 direction**, proven with an
  instrument control: one-sided edits S1 (RC2 direction) and S3 (RC1 direction) both leave
  `tests/test_bulk_build.py` **6 passed — GREEN**, while control S2 (`return []`) reddens it
  2/6. So the gate reaches the function and the blindness is a CORPUS gap. The RC2 schema is
  a ready-made minimal corpus — pin it as part of the fix.

**When you fix it:** full phased gate (all ten) + the 6-seed fuzz sweep
(`--hypothesis-seed=` 7 19 31 53 71 97 over `test_hypothesis.py` and
`test_lookup_hypothesis.py`) — it is an algorithm change. Then push.

## 1a. ~~THE FIX LIST~~ — ALL ITEMS DONE (2026-08-11). Kept for provenance.

Every numbered item below is now closed: (0) was already done in `d0dbefa`, (1) RC2,
(2) the bulk corpus, (3) the compile-time invariant, (4) the compiler rough edge, and
(5) the gate + fuzz sweep. See "What landed 2026-08-11" at the top for what each became.

RC1 is **FIXED and committed**. What follows is everything still owed, in the order to do it.

**(0) ⚠ READ THIS FIRST — a latent intermittent failure was found and fixed 2026-08-10, and
the lesson generalises.** When plan item 1b (c) made `schema_asts` DRAW the TTU tupleset, it
broke a documented assumption in a *different* file: `tests/test_lookup_oracle.py:126` imports
`schema_asts`, and its block comment asserted *"Object wildcards are not used (schema_asts
never emits them), so the graph always joins"*. Drawn star tuplesets made that false, and
`test_lookup_oracle_gate_generated_schemas` died on gate construction with
`UnsupportedByGraphIndex`. **No profile here sets `derandomize`, so this only fires on some
draws — the first full-suite run after (c) landed passed by luck and the commit shipped
red-capable.** Now fixed: the refusal is caught and asserted to be a RECORDED family
(`genswarm.match_rejection`), never swallowed, with `test_..._graph_join_rate` flooring how
often the gate actually runs. **Generalisation for anyone changing a generator: grep for its
importers.** A generator is a shared interface, and its consumers encode assumptions about
what it can emit — in prose that no test checks.

**(1) RC2 — the real work. A semantics decision, not a filter tweak. Budget accordingly.**
A stored `T:*` tupleset parent is dropped when the tupleset relation is derived.
* Sites: `index_v4/processor.py:320` (`n.wildcard == ''`) **and its verbatim duplicate**
  `index_v4/bulk_backfill.py:454`. Unlike RC1 — whose `parent_types` is compiled once and
  shared — **RC2 genuinely needs both**, or the offline `build_index` path stays wrong.
* ⚠ **Two dead ends already measured, do not repeat them.** Deleting the clause breaks
  admission parity before any query runs (`accept/reject divergence on add
  ('...','doc','*','parent','doc','d1'): graph=False set:py=True`). Widening it naively
  crashes at `index_v4/core.py:914` (`name=='*' and a non-empty wildcard must go together,
  got entity_name='*', wildcard=''`).
* **The decision you actually have to make:** what a wildcard TTU parent *means* — presumably
  a union over all objects of the parent type. The star parent must be **represented**, not
  merely admitted. **The set engine already has the analogue: port `MemberSet.stars`**
  (`setengine/memberset.py`), which is why the set engine gets this right today.
* Clears: `test_rc2_*` (2 pins) and whatever RC2 cells the generators light up.

**(2) Pin the corpus gap that hid RC2 from the bulk gate.** The bulk-vs-incremental identity
gate is **blind** to this direction — measured, with a control: one-sided edits S1 (RC2) and
S3 (RC1) both leave `tests/test_bulk_build.py` **6 passed GREEN**, while control S2
(`return []`) reddens it 2/6. So the gate reaches the function and the gap is the **corpus**:
nothing has a `T:*` subject holding a stored tupleset tuple on a derived tupleset relation.
**The RC2 schema is a ready-made minimal corpus** — add it, and confirm S1 turns red.

**(3) Land the new compile-time invariant.** Prototyped and validated RED-before/GREEN-after:
each TTU node's `parent_types` must cover every bare-entity type that **admission** accepts
onto that tupleset's storage leaves. ★ **Read it from the emitted `RewriteFilter`s, NOT from
`_member_types`** — that independence is the whole point. `_member_types` is what was wrong,
and an invariant reading it would be a *mirror* (`docs/sabotage-procedure.md`, "the mirror
instrument"), exactly like I9, which re-runs `reconcile`, reads the same wrong metadata,
agrees with itself, and stayed green through both fail-opens with paranoia ON.

**(4) The compiler rough edge found 2026-08-10, reported not fixed.** A TTU whose tupleset is
undeclared *and* whose target is derived (`define r7: [user] or r1 from nodecl`) escapes the
decision-15 scope checks and dies in `compile_boolean_schema` with a bare
`ValueError: Rule then-pattern carries a derived subject predicate` — the class
`tests/parity.py` says "must surface". With an untainted target it compiles cleanly. Already
captured as a rejection family in `tests/genswarm.py` so it cannot rot.

**(5) Then the gate, which is what this session deferred.** All ten phases + the 6-seed fuzz
sweep (`--hypothesis-seed=` 7 19 31 53 71 97 over `test_hypothesis.py` and
`test_lookup_hypothesis.py`) — RC1 and RC2 are algorithm changes. Then push.

**(6) Optional, open question — NOT a finding.** The 2026-08-09 sibling
(`spec-deviations.md`) carries the same "it fails closed, so it is not a security fail-open"
wording, and this session's rule (a dropped TTU parent inverts sign under a negated TTU)
predicts it inverts too. It was never re-tested, because it is fixed and testing means
reverting. If you want it settled, revert `c042056` in a scratch worktree and add a negated
TTU consumer. Do not propagate the prediction as measured fact.

## 1b. Close the generator gap that let this through.

*(Heading frozen as filed: "STARTED 2026-08-10, incomplete". It was COMPLETED 2026-08-10 —
(a), (b) and (c) all shipped and gated; see the ★★ STATUS block below.)*

`tests/test_hypothesis.py::schema_asts` hardcodes the TTU tupleset:
`ast = {('doc','parent'): Direct((Restriction('doc','...',False),))}`. **Every TTU in every
generated schema reads a plain single-type non-boolean `parent: [doc]`**, so the entire
"TTU over a structured tupleset" space is unreachable **by construction — not by seed luck,
and not fixable by raising `max_examples`.** `ci` runs `max_examples=12,
stateful_step_count=8`, and there is **no coverage assertion anywhere in the campaign**, so
"we fuzz broadly" is an unchecked claim. Yesterday's IIA instrument can't see it either —
its hypothesis leg samples tuples over four FIXED corpora, so a novel schema shape is
invisible to it too.

Scoped with the user 2026-08-10 as three pieces, all three approved:
* **(a) coverage cells, asserted** — enumerate the feature-cross cells, DERIVE the cell list
  from the compiler's own leaf kinds / AST node types rather than hand-writing it (a
  hand-written list is a future silent pass), record which cell each draw hits, assert every
  cell is hit, and distinguish "unreachable by design (compile-rejected)" from "unreachable
  by generator gap" — the second kind is what let these bugs through;
* **(b) swarm testing** — per run draw a random subset of features to ENABLE and generate
  deeply within it. Rationale: at a 12-example budget, uniform sampling over a rich grammar
  touches many features shallowly, the worst configuration for interaction bugs — and every
  bug this repo has found is an interaction bug;
* **(c) un-hardcode the TTU tupleset** so it is drawn from the same expression grammar.

⚠ **Constraint that will bite:** the candidate tuple pool must co-vary with the generated
schema. The existing generators guarantee schema-VALID candidates by construction, because
the graph admits a restriction-invalid tuple as a silent no-op while the set engine does
not. Widen the grammar without co-generating a valid pool and most draws are refused at
admission, so the sweep measures the REJECTION path **and reports green** — the house
failure mode. ★ **There is an unusually strong control available right now: the two bugs are
UNFIXED in the tree, so a correct new generator should go RED on them today and GREEN after
the fix. Use that as the sabotage evidence — it is a real defect, not a synthetic one.**

**★★ STATUS: (a), (b) AND (c) ARE ALL IMPLEMENTED AND GATED (2026-08-10).** Design + raw
evidence remain in [`docs/design/generator-coverage/`](../../docs/design/generator-coverage/); the
shipped code is `tests/genswarm.py` (library: derived alphabet, swarm, witness builder,
rejection witnesses, two-regime driving) + `tests/test_generator_coverage.py` (26 gated
tests) + the `test_hypothesis.py` changes. **Measured outcomes:**

| | cells | % |
|---|---|---|
| baseline at HEAD (the old generators) | 514 | 40.3 |
| union, `ci` | **967** | **75.8** |
| union, `deep` | 1034 | 81.1 |

`UNACCOUNTED == set()` **exactly**, with no hand-written exemption list — the design's "15
features unreachable at any budget" is now **0 unreachable + 3 carrying executable rejection
witnesses**. Runtime `ci` +130 s (design targeted +32 s; the entire overrun is the dense
driving regime, which is what closes the fail-open gap) and `test_hypothesis.py` +23.5 s. The
worst tile goes ~165 s → ~295 s of a 600 s cap.

**★ Three corrections the implementation made to the design — trust these over the design doc:**
* **The fail-open gap needed a GRAMMAR fix, not just a driving fix.** §6.7 blamed subset
  driving alone. In fact **no generator in the tree, including the design's own prototype,
  ever emitted a negated TTU**, so a fail-open was not *expressible* at any budget or
  discipline. It took `body_negttu` **plus** two-regime driving. Measured over one config
  space: sparse 62,691 comparisons → 0 fail-open / 10 fail-closed; dense (deterministic
  knockout) 61,659 → **1 fail-open** / 13 fail-closed; full pool 41,562 → 0 / 3. The design's
  suggested random co-subsets were seed-dependent and found 0 — replaced.
* **The design's own predicted sabotage #8 is REFUTED** (independently, by both implementing
  agents). It claims the acceptance-rate floor fires when the typed pool table is reverted.
  It does not — `folder:d1` is a legal `folder` name, so every backend admits it. The real
  damage is silent **inertness**, and the guard now asserts the pool's universe ⊆ the grid's
  universe instead.
* **Full-pool driving is not blind to everything** (it still catches 3 of 10 fail-closed
  families). The README's "0 divergences" is too strong; the direction it is genuinely blind
  to is **fail-open**.

**Two limitations recorded rather than smoothed over:** the swarm test does **not** in fact
guard the focus mechanism (min per-switch count 27/120 with focus, 27/120 without — the claim
was removed, not kept), and folding the wildcard bit out of the knockout shape key leaves the
negative control green (a known, stated limit).

**Incidental finding, reported not fixed:** a TTU whose tupleset is undeclared *and* whose
target is derived (`define r7: [user] or r1 from nodecl`) escapes the decision-15 scope checks
and dies in `compile_boolean_schema` with a bare `ValueError: Rule then-pattern carries a
derived subject predicate` — the class `tests/parity.py` says "must surface". With an
untainted target it compiles cleanly. Captured as a rejection family so it cannot rot.

* **The premise is confirmed and quantified: it is grammar, not budget.** Cell space is
  **51 features → 1275 pairwise cells**, with the alphabet DERIVED from six compiler sites
  (the `Expr` union, the `LeafSpec` kind literals, the `_plan_leaves` dispatch, the
  `DependentEdge` via-literals, `LeafFamily.kind`, `Restriction`'s fields) rather than
  hand-written. Current generators reach **514/1275 = 40.3 %** at their ceiling — and the
  `ci` budget already reaches **91–100 % of that ceiling**, so raising `max_examples` buys
  almost nothing. **15 features are unreachable at any budget, and 13 of them are the one
  hardcoded tupleset** (ten `ttu.ts:*` plus its three compiled consequences
  `leaf:derived-tupleset-ttu`, `plan:PDerivedTuplesetTTU`, `via:tupleset-ttu`).
  Pairs are used instead of a cartesian grid deliberately: the grid is 2^51, and a
  hand-picked sub-grid would be exactly the silent-pass list this work exists to kill.
* **★★ A SECOND instrument that fails by passing, found in passing — ✅ FIXED 2026-08-10
  (`d0dbefa`). Nothing to do; this bullet is the record.**
  `BoolStarBridgeParityMachine` — the generator the source itself calls the "headline blind
  spot" closer — **ran the graph index on only 12 % of its draws.** 59 % raised
  `UnsupportedByGraphIndex`, whereupon `ParityEngine` set `graph=None` and the machine
  fuzzed **3-way and reported green**; 29 % were skipped. Its sibling
  `StarBridgeParityMachine` has always asserted `graph is not None`; this one did not.
  ⚠ **The sharp form is worse than the 12 % suggests** and is recorded in
  `docs/sabotage-procedure.md:31`: all 768 `and`/`but not` configs were rejected for every
  OWC subset, so the draws that DID run 4-way were exactly the `or` ones — **it had tested
  booleans against the graph index zero times, ever.** Now asserted at
  `tests/test_hypothesis.py:1886` with the rate floored; 13 % → 76–82 % 4-way, 0 % → 49–55 %
  boolean-4-way. It was **not** the predicted one-line fix: the boolean arm's placement had
  to become a drawn choice.
* **★ Cell coverage is NECESSARY BUT NOT SUFFICIENT — the driving discipline is what makes
  a divergence observable.** The prototype's instrument control caught this in its own first
  draft: driving each config with the WHOLE candidate pool found **0 divergences** across
  the same 97 configs that small-subset driving detonates, because a fail-closed divergence
  is masked by any extra granting tuple (this repo's own IIA property). Without that control
  the design would have shipped a 35 s green phase over an unfixed live bug. **The full-pool
  variant must land as a permanent negative control.** Related trap: a neg-only arm whose
  subtrahend type also appears in the base compiles, reads correctly in review, and yields
  `parent ≡ ∅` — a "compiled but never driven" cell.
* **Reachability is decided by REJECTION WITNESSES, not an exemption list.** A cell counts
  as "unreachable by design" only if it carries an executable `(schema, owc)` the compiler
  is asserted to refuse, with the message recorded. Relax a scope check and the exemption is
  revoked automatically — so a scope relaxation cannot silently mint a new blind spot.
* **Costs, measured.** `ci` **+~32 s** (the tile goes 165 s → ~197 s against a 600 s cap):
  deterministic witness enumeration over switch singletons + pairs (119 configs), a
  compile-only cell assertion (`UNKNOWN == ∅`, 454 cells, exhaustive over its own closed
  config space), the rejection-witness checks, a driven pass of 2 small subsets per config,
  the existing swarm campaign at unchanged `max_examples=12`, plus the negative control.
  `deep`/nightly: triples (469 configs, 157 s measured), `max_examples=120`, committed
  histogram.
* **Honest limits, from the design's own §6.** Prototype swarm + (c) reaches 721–771 cells
  alone; unioned with the existing generators, **876–891/1275 (68.7–69.9 %)**. **~30 % stays
  unreached** and the doc says so. And the sweep found **only fail-closed divergences** — it
  could not independently reproduce a fail-open one; §6.7 attributes that to subset driving
  being tuned for under-grants and estimates a sparse+dense two-regime drive at ~+30 s.
  **So this design, as prototyped, would NOT have found the fail-open direction** that turned
  out to be the severity story of item 1. Treat that as an open gap, not a solved one.

---

## Completed board items (retired from "Active work")

- [x] ~~**★★ (2026-08-09) — A LIVE ANSWER-LEVEL DIVERGENCE.**~~ **FOUND, ADJUDICATED AND
      FIXED the same day** (`58b51a8` pin-red, `310fbcb` IIA-red, `c042056` fix). The graph
      index under-reported the **OWC × star-parent × TTU cross**. Three
      tuples on `tests/fga_schemas/owc_star_ttu.fga`:

      ```
      (user:u1, editor,  folder:f1)   # any tuple that makes folder:f1 exist
      (user:u1, viewer,  folder:*)    # OBJECT-wildcard grant
      (folder:*, parent, doc:d1)      # SUBJECT-wildcard tupleset
      check(user:u1, viewer, doc:d1): oracle=True set:py=True set:roaring=True GRAPH=False
      ```

      **A false negative** — it fails closed, so it is not a security fail-open, but it
      breaks the repo's central contract (two backends, identical semantics). **Pre-existing:**
      reproduces at `6d3c540` with byte-identical Python; the session that found it changed
      no `.py` file. **Found by** the hypothesis lookup campaign on a generated walk.

      **Root cause, measured:** `index_v4/wildcard.py::_ensure_bridges` bridges
      `w_all(T,p) → concrete → w_any(T,p)` only through an interned node of **shape `(T,p)`**,
      while `tests/oracle.py::instances` witnesses ∃ with any **entity of type `T`**. Vary
      only the witness relation and the graph flips: `folder:f1#editor` → False,
      `folder:f1#blocked` → False, `folder:f1#viewer` → True. The two sides read
      `wildcard-materialization-spec.md` §3.4 differently and **that asymmetry is written
      down nowhere** — adjudicate which reading is intended BEFORE assuming the graph is
      the side to change.

      **Pointer for the fix:** the set engine already has the analogue the graph lacks —
      `setengine/engine.py:1476-1480`, "the star-parent cross for the triple combo owc x
      star-parent x TTU where NO concrete `(T, X, r')` is interned".

      **Pinned deterministically** by `tests/test_owc_star_parent_cross.py` — 2 red pins +
      1 green positive control, a positive pin and NOT an xfail, per `CLAUDE.md`.
      ⚠ **Second finding, arguably the more important one:** before that file existed the
      shape was reachable but essentially never drawn (`max_examples=12`,
      `stateful_step_count=8`, ~50-tuple pool) — **the gate was green by seed luck**, the
      house failure mode by name. *The hypothesis campaign's green is a sample, not a
      proof, and nothing in the gate says so.* Consider whether that deserves its own fix.

      **The fix:** the crossing middle now tracks the **entity**, not the node —
      `WildcardIndex._ensure_entity_middles` / `::_sync_entity_middles`, with the property
      lifted into `index_v4/invariants.py` as **I14** so paranoia aborts the first innocent
      write if a path stops maintaining it. `_ALLOWED_DIRECT` was NOT relaxed; ∀⇒∃ stays
      strict *structurally* rather than by a counter. Sabotage: making
      `_ensure_entity_middles` a no-op leaves **I3 green and only I14 red**.

      **Two more findings that correct live documents:**
      * **The formal layer could not have caught this, by construction.** Lean's in-bridge
        test keys on a *literal* `T:*#p` restriction; Python's `bridged_in_shapes` also
        folds in star-tupleset through-shapes. So Lean's crossable set is exactly the
        compile-rejected set — empty among admissible schemas — and the arm where the bug
        lived has no Lean counterpart. Filed as a fragment boundary,
        `formal/CORRESPONDENCE.md` §7.3. **Do not read "the wildcard write path has a Lean
        twin" as "it is covered".**
      * **A live comment was refuted.** `zanzibar_utils_v1.py::wildcard_userset_restriction_shapes`
        claimed the `owc_star_ttu` class is "oracle-correct and unanimous on both
        backends". It was not. Corrected in situ; the narrowing it justifies still stands
        on its own argument.

      Full filing, including the five prior-art items checked and why none covers this:
      [`docs/spec-deviations.md`](../../docs/spec-deviations.md) 2026-08-09.

- [x] ~~**★★ (2026-08-08) — THE `rewriteClosure` DEDUP LEG.**~~ **LANDED
      2026-08-08 (`911c887` corpora-red, `c488a2f` fix). `CORRESPONDENCE.md` §7.2 item 6
      is CLOSED; leg 7's step 2b is DISCHARGED.** All ten gate phases green. Kept visible
      for one cycle because three of its outcomes correct documents that are still live:
      * **The sizing held exactly** — the count stack is list-generic, so `untOccCount`/R3/R4
        needed ZERO proof rework. **16 sites repaired, not the pre-measured 15**: the extra
        one consumed the definition through term-level defeq, so it was invisible to a grep
        for the TACTIC `unfold rewriteClosure`. *Grep the identifier, not the tactic.*
      * **★ The over-count cost RUNTIME, which nothing predicted.** Every prior write-up
        treated it as read-invisible bookkeeping; in fact `reconvergent_derived` blew
        zcli's 120 s remove-stream budget before the fix and passes after it (derived-arm
        multiplicity `185 → 52`). The masked value was also `lean=185`, not the scope doc's
        predicted `lean=10` — that figure was for a ONE-write probe.
      * **★ The sabotage found a real limitation, not a confirmation.** The two new corpora
        do **NOT** catch the WRONG fix (a global `admitEdge` presence dedup): every
        multiplicity in them is 1, so it leaves them green. `nary_union` catches that one,
        at `3 → 1`. They guard OPPOSITE errors and neither substitutes for the other —
        recorded in `corpus.py` so nobody deletes `nary_union` believing reconvergence is
        now covered. The `List.dedup` last-occurrence risk was probed and retired
        (topological on all three probe schemas, with a positive control).
      Detail: `formal/history/PROOF_STATUS.md` 2026-08-08b.

- [ ] **~~START HERE~~ (superseded — kept for the scope pointers below)** This is the
      original filing of the leg that landed above; everything else on this board is either
      deferred (leg 7 proper) or a design decision already made.

      **What it is.** `CORRESPONDENCE.md` §7.2 item 6: the Lean model's `rewriteClosure`
      does not dedupe where Python's `RuleSet.apply` does, so on a **reconvergent** schema
      the model over-counts edge multiplicity. Filed 2026-07-28 as "no corpus exercises it
      today"; **measured live 2026-08-08 and adjudicated MODEL-side.**

      ```
      a := b or c ; b := d ; c := d ; d := [user]   (one write: alice@d)
        alice -> doc:d1#a    lean=2  python=1   <== untainted arm, P3 compares EXACTLY
      ```

      **It is a UNIT divergence, not a retirement bug.** Both sides retire correctly
      (five-sequence add/remove battery agrees on presence; answer parity 0 mismatches over
      56 and 108 queries). Python counts **live raw tuples**; the model counts **derivation
      paths** — measured `1 → 2 → 4` for zero/one/two chained diamonds, fuel-stable, i.e.
      the model's ref count grows with SCHEMA SHAPE.

      **Why the model is the wrong side (house rule 5, and it is sharp):**
      `RemoveOccCount.lean`'s header *asserts Python's unit* — "`List.count (a,b)` IS the
      model's `direct_edge_count`" — which is FALSE on any reconvergent schema, while the
      same file's attack bullet already says so. **The file contradicts itself and R3/R4's
      faithfulness claim rests on the wrong half.** Fixing Python is not available: its
      `processed` worklist dedup is the TERMINATION mechanism (`a: [user] or b ; b: a`
      compiles — only *derived* cycles raise — and loops forever without it).

      **Why it is cheap — the key finding.** The count machinery is **list-generic**:
      `count_removeLoggedRules` opens with `generalize rewriteClosure S t = us`, and
      `count_foldl_writeDirect` is `∀ (us : List Tuple)`. So `untOccCount`, R3
      (`reachedByW3d2E_untOccCount`) and R4 (`RemoveConfluence`) need **zero proof rework** —
      values change, meaning improves. Only **15 `unfold rewriteClosure` sites** (mechanical,
      via one new `mem_rewriteClosure_iff`) and **2 list-equality sites**
      (`rewriteClosure_derived_eq_seed`, `…_nk`) need redoing.
      **Minimal-diff shape:** rename the current def `rewriteClosureRaw`, define
      `rewriteClosure S t := (rewriteClosureRaw S t).dedup`, add the one membership lemma.
      `DecidableEq Tuple` exists (`Core/Refs.lean`) and `List.dedup` is already used once
      (`Core/Store.lean`), so no new idiom.

      **⚠ ORDER WITHIN THE LEG: corpus FIRST (red, attributable, recorded), then the fix
      (green).** Corpus alone leaves a red gate; fix alone leaves the fix unexercised.
      Two corpora, both `SCHEMAS` + `GRAPH_FRAGMENT` + `_THEOREM_BACKED`,
      `_EXPECTED_SPLIT (23,0) → (25,0)`: `reconvergent_diamond` (taint set empty) and
      `reconvergent_derived` (`viewer := e but not banned` over a reconvergent base — this
      is the one that carries the leg-7 payload, since after the `writeDirect` fork its
      currently-masked `lean=10 python=1` moves onto a leaf node in the exactly-compared
      untainted arm).

      **⚠ The leg's one real risk, unverified:** Mathlib's `List.dedup` keeps the **LAST**
      occurrence, so write order shifts. Measured topological on both probe diamonds, but
      that is luck rather than a theorem. If a proof turns out order-sensitive, a
      first-occurrence dedup is the fallback.

      **Owed regenerations** (deliberate, each with the reason written): the definition pin
      (`rewriteClosure`'s row moves; the rows that merely NAME it stay byte-identical),
      `derived_arm_multiplicity.json`, `FINAL_REVIEW.md`'s counts block, and `zcli`.
      **Prose corrections owed:** `RulesWrite.lean`'s "duplicates are harmless (reachability,
      not counts)" — the sentence being retired — plus `RemoveOccCount.lean`'s header and
      attack bullet, `ReconcileDiff.lean`'s multiset claim, `Audit.lean`, and
      `CORRESPONDENCE.md` §7.2 item 6 (which now carries the adjudication).

      **Full adjudication, corpus design, and the exact predicted red:**
      [`formal/history/leaf-family-split-scope-2026-08-05.md`](../../formal/history/leaf-family-split-scope-2026-08-05.md)
      §10.5 (+ §10.3 for why it blocks leg 7), `formal/history/PROOF_STATUS.md` 2026-08-08.

---

## Retired from "Standing / latent"

- [x] ~~**`TupleSource.__init__` is not atomic on PostgreSQL**~~ — **CLOSED; this entry
      was STALE and said so in a way that mattered.** It claimed "the single remaining
      strict xfail in the tree … declared in `verify.sh`'s `MAX_TESTS_XFAILED=1`".
      Verified 2026-07-29 against the code: `verify.sh` carries
      **`MAX_TESTS_XFAILED=0`**, `tests/test_postgres_ha.py` records that
      `test_open_instance_races_a_concurrent_commit` **became a plain pin** when
      `TupleSource._consistent_rebuild` landed, and that helper
      (`connectedstore/source.py`) is used by BOTH `__init__` and `refresh_evaluator` —
      the two sites the finding named. Nothing in the tree is xfailed. Kept visible
      rather than deleted because for two days this was the one entry that would have
      made a reader believe a live authorization-adjacent bug was open.

---

## Retired 2026-08-16 (leg 7 4c-i session)

Five completed blocks moved out of [`HANDOFF.md`](../../HANDOFF.md) when board items 1
and 2 advanced and the file passed 1150 lines. **Provenance, not open actions.** The
METHOD from each was kept in the live docs rather than archived with the status:

* the **severity-sign rule** and the **mirror instrument** stay in `HANDOFF.md` §1;
* *"a teardown test is not a delete test"* (from the `_any_residue_reference` item) moved
  to [`docs/sabotage-procedure.md`](../sabotage-procedure.md), where it is now a named
  subsection rather than a bullet in a completed checkbox;
* the two `.fga`-corpus findings (single-type tuplesets never exercise `parent_types`
  breadth; every reachable uncovered feature sat on the TTU-tupleset axis) survive as the
  floored `test_fga_corpus_feature_coverage_does_not_regress` and the
  `tupleset_shapes.fga` fixture.

⚠ **Status lines below are frozen as-of-then.** In particular the `ttuStarFree` "(iv)
carries a possibly-blocking decidability question" framing that appears in the 2026-08-14
block is **DEAD** — answered NO-BLOCK on 2026-08-16 (`GraphIndex/TtuStarWide.lean`).

### CUT landed-0811
### What landed 2026-08-11

**(1) RC2 — the last root cause of the 2026-08-10 fail-open family.** A stored `T:*`
tupleset parent was dropped on the derived read path. The `n.wildcard == ''` clause was
**not** deleted — both recorded dead ends were re-confirmed first. Instead the two subject
shapes are split (`_stored_tupleset_subjects`) and the star one gets the semantics the
oracle and both set engines have always implemented: the shape `(T, target_rel)`
unconditionally (into the residue's `stars`), **plus** an ∃-expansion over tuple-mentioned
instances of `T`, folded into `tupleset_parents` so every downstream consumer
(`_from_chain_keys`, `_leaf_concretes`, `_derived_leaf_neg_ids`) became correct with no
edit. Fixed at BOTH sites — `processor.py` and `bulk_backfill.py` — which RC2 genuinely
needed, unlike RC1.

⚠ **Scope note — one clause was left alone DELIBERATELY, and it is a near neighbour of the
one that was fixed.** `index_v4/bulk_backfill.py::_stored_userset_subjects` still carries its
own `w2 == ''` test, for stored **usersets**. Different code path from the RC2 site, not part
of either root cause, and not widened because **no divergence justified it** — widening a
star-admitting filter without a failing case is precisely how RC2's two measured dead ends
happened. Recorded here because the board is what gets read: it otherwise lives only in
`tests/test_ttu_tupleset_parent_types.py`'s module docstring. **Bring a divergence before you
touch it** — the exhaustive sweep that mapped this family (2,302,854 queries, 346 schemas)
found exactly two root causes and neither was here.

★ **And a rot hazard this note exposed, worth more than the note.** The old board cited the
RC2 site as `bulk_backfill.py:454`. **That citation is now WRONG in the worst possible way:**
the fix inserted `_stored_tupleset_subjects`, and post-fix `:454` lands inside
`_stored_userset_subjects` — i.e. the line number that used to mean "fix this" now points at
the one clause that must be left alone. Current layout, as of this commit:
`_stored_userset_subjects` **447** (the untouched `w2 == ''` at 454) ·
`_stored_tupleset_subjects` **466** (the RC2 fix; its own `w2 == ''` at 479 is *fixed* code) ·
`_tupleset_parents` **485**. **Cite `file::function`, never `file:line`, for anything a
future session is meant to act on** — `verify.sh lean` already enforces exactly that for
`CORRESPONDENCE.md` anchors, and this file has no such gate.

★ **The part no design note predicted, and the transferable finding: the CASCADE FAN-OUT
had to change too.** A star tupleset tuple hangs off the `w_any(T,'...')` node, not off any
entity, so `_stored_parent_objects_of_entity` — which answers "what does a delta on this
entity invalidate?" by walking the entity's own edges — saw nothing, and a later write to
some `T:x` would have invalidated no dependent at all. **The read fix alone passes every
pin in the file**, because the pins write in one batch and reconcile once; it would have
failed only under incremental maintenance. *A correctness fix to a read path in an IVM
system is not done until the invalidation path has been asked the same question.*

**(2) The bulk corpus gap is CLOSED.** `rc2_star_tupleset` in `tests/test_bulk_build.py`,
carrying both TTU directions (positive fails closed, negated fails open — probing only one
mis-classifies severity by a sign). **Sabotage, literal output:** reverting the bulk half
alone — the S1 edit that used to leave the suite **6 passed GREEN** — now gives
`1 failed, 6 passed`, `AssertionError: [rc2_star_tupleset] snapshot_rows differ`, with the
other six corpora green so the red is attributable.

**(3) The compile-time invariant landed, and deliberately is NOT a mirror.**
`zanzibar_utils_v1.py::_assert_ttu_parent_types_cover_admission` — every TTU's frozen
`parent_types` must cover every bare-entity type ADMISSION accepts onto that tupleset
relation, read from the emitted `RewriteFilter`/`Filter` patterns and **never** from
`_member_types` (the function RC1 got wrong; an invariant reading it would reproduce I9's
mirror defect exactly). Validated RED-before/GREEN-after and made permanent as
`test_compile_refuses_parent_types_narrower_than_admission`. It catches the RC1 class **at
compile time, before any tuple is written**. Honest limit, stated in its docstring: it only
sees types some Filter accepts, so a tupleset fed only by rewrite Rules is vacuous there.

**(4) The compiler rough edge is FIXED** (was fix-list item 1a(4), "reported not fixed" —
now in the 2026-08 archive, where that stale wording is still visible). A TTU
whose tupleset is undeclared and whose target is derived died in `compile_boolean_schema`
with a bare `ValueError` — a class `tests/parity.py` says "must surface", so `ParityEngine`
was *unconstructible* (a hard crash) rather than degrading to 3-way. `_validate_ttu_tuplesets`
now refuses it up front as a scoped `UnsupportedByGraphIndex` and the `ValueError` is back
to being an unreachable backstop. The `genswarm` rejection witness was flipped to match,
and `test_undeclared_tupleset_with_untainted_target_still_compiles` is its **negative
control** — the witness alone is satisfied by an over-broad refusal, and "reject every
undeclared tupleset" is precisely the one-line over-fix a future reader would reach for.

**(5) Gate floors re-measured and raised** (`-ge`, so raising is free): `MIN_CONF_ALL`
465 → **494** (= 104 + 390), `MIN_TESTS_ALL` 763 → **823**. They had drifted ~90 tests below
live, i.e. that much coverage could have vanished silently.

**(6) No Lean change owed — and the reason is worth reading.** RC2's region is excluded
from the graph fragment by **two** standing hypotheses: `RulesBareStar.lean::TtuStarFree`
(star-subject tuples matching a TTU arm) and `RulesCorrect.lean::TtuTuplesetsDirect` (every
TTU tupleset must be `directsOnly`, so a *derived* tupleset is not expressible at all).
Nothing became dead code. Recorded in `CORRESPONDENCE.md` §7.3 — including the near-miss:
`TtuStarFree`'s own header records an attack-first `#eval` from 2026-07-11 on exactly this
shape, finding `sem=true` against a rule-routed graph `false`. ⚠ That was a property of the
LEAN write model and is **not** evidence anyone had observed the Python defect — Python's
UNTAINTED star-tupleset path was and is correct, and is pinned green by a control in the
same file. The general lesson still stands: **a shape fenced out of the model as "not
covered here" is a standing hint about where the implementation is least watched.**
Python moved TOWARD the models here: the new split is structurally
`SetEngine/Eval.lean::parentMS`.

⚠ **Correction to the previous board.** The item "`BoolStarBridgeParityMachine` runs the
graph on 12% of draws — cheap and independent, do it FIRST" was **already done** on
2026-08-10 in `d0dbefa` (the assertion is at `tests/test_hypothesis.py:1886`, 13% → 76–82%
4-way, floored with provenance). `docs/sabotage-procedure.md:31` was the accurate record;
this file and `docs/design/generator-coverage/README.md` were stale. Nothing to do.


@@@

### CUT landed-0814
### What landed 2026-08-14

**Both big Lean legs were taken up. NEITHER is finished, and that was called up front
rather than discovered at the end** — leg 7's step 4c alone is a 36-module recompile cone.
What this session actually bought is that the next one starts **unblocked**:

* **★★ Leg 7's §11.3 design fork is DECIDED — branch (α)**, the `Delta` row moves to the
  leaf node, measured on both the Python and Lean sides. The leg is no longer blocked on a
  decision, only on effort. **Four cells of the scope doc were refuted**, including a
  scheduling constraint it does not contain: **step 4c must co-land with step 7**, because
  P6 is a Python-side-only filter. Resume detail in board item 1 (B1) and scope-doc §11.5.
* **`ttuStarFree` part (i) LANDED** (`2cf76bb`) — but it is **INERT** and does **not**
  close the 2026-08-10 counterexample. Parts (ii)/(iii)/(iv) remain. ⚠ **The "(iv) carries
  a possibly-blocking decidability question" half of this line is DEAD as of 2026-08-16 —
  answered NO-BLOCK.** Board item 3.
* **`Leaf.lean`'s citations de-rotted and leg-7 addressing MAPPED** (`b47d9ed`) — it had
  landed entirely unmapped in `CORRESPONDENCE.md`, so those anchors are now gated.
* **Two method lessons were written up** rather than left in a commit message: the
  **INERT-change sabotage** (when nothing reddens, that *is* the finding, and it tells you
  you owe all the pinning) in [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md),
  and **the first fan-out that worked** (8/8 agents, and why) in
  [`docs/subagent-fanout-runbook.md`](docs/subagent-fanout-runbook.md).


@@@

### CUT item2
### 2. ~~Verify or discard two UNVERIFIED claims from the failed audit.~~ BOTH ADJUDICATED 2026-08-14.

Both were reproduced from scratch, with attribution controls and positive controls.
Neither was the known false positive. **Neither leaves a live correctness bug.**

* **`W4Fragment.computedOrDirect` — CONFIRMED as an empirical fact, MIS-FRAMED as a
  fail-open.** On `access: viewer from parent but not banned` with
  `viewer(alice, folder:f1)` + `parent(f1, doc:d1)`, `zcli mode=graph` really does answer
  `[false]` at **rc 0** while `mode=spec`, the oracle, both set engines and the real
  `WildcardIndex`+`DeltaProcessor` all answer `[true]`. Controls attribute it exactly to
  the `.ttu` leaf **inside a derived def** (`ComputedOrDirect` maps `.ttu` to `False`):
  hoisting the TTU out, or dropping the exclusion, restores agreement.
  * ★ **The direction is the opposite of the filing.** The Lean model *under*-reports —
    denies access that exists — so for authorization it is fail-**CLOSED**. The only
    "open" is that the driver emits an answer instead of refusing. Do not carry the
    original wording forward.
  * ★ **And it is less novel than it reads.** That mode=graph does not gate on
    `W4Fragment` was already documented in `formal/conformance/corpus.py`'s
    `GRAPH_FRAGMENT` header ("silently compares two models that no theorem relates").
    The new artifact is a *measured wrong answer*, not the non-gating property.
  * **Blast radius today: none.** A controls-validated scan of all 25 `GRAPH_FRAGMENT`
    corpora finds zero with a TTU inside a derived def, and mode=graph is driven only
    from that set. Recorded in `CORRESPONDENCE.md` §2 (the zcli exit-code block).
  * **What is actually left, and it is not small:** a driver-side fragment pre-check
    needs a DECIDABLE `W4Fragment`, and none exists (no `admissionB`-style boolean).
    Its own leg if anyone wants it; nothing is blocked meanwhile.

* **`GraphAdmission.ttuDirect` (`TtuTuplesetsDirect`) — TRUE WHEN FILED, ALREADY FIXED.
  It was RC2.** The audit's divergence (a `folder:*` stored tupleset parent on
  `parent: [folder, folder:*] but not detached`; oracle + both set engines True, graph
  False) is verbatim RC2, and it even nominated the fix that landed in `7e3294e`.
  Re-measured on the current tree: the audit's own exhaustive experiment (2^6 = 64
  stores × 9 queries = 576 comparisons) now gives **0 divergences** where it measured
  104, with a positive control confirming the instrument still fires; four further
  flavours of the excluded class (640 comparisons) are likewise clean.
  **Nothing actionable remains** — do not re-open it.
  * ⚠ **Its recommendation #3 stands: do NOT lift `ttuDirect` in Lean.** Consistent with
    item 3 below and `CORRESPONDENCE.md` §7.
  * **Two false docstrings it found were the only live residue, and are FIXED
    2026-08-14** (documentation, not defects): `State.lean::GraphAccepts` claimed
    "outside this scope the graph rejects the schema at compile", false for its clause
    (3) — a derived TTU tupleset compiles and gets a `derived-tupleset-ttu` leaf; and
    `FullScope.lean`'s `ttuDirect` field doc described Python's weaker check (which has
    a `ts_key not in tainted` guard) rather than the predicate it annotates (which has
    none). Both now state the gap the way `wsBare` / `directArmsConcrete` do. ★ This is
    precisely the rot class `verify.sh` step 4d **cannot** catch: the anchor check
    resolves pointers, not claims.

★ **Where the primary record was, since the board said it was lost.** Nothing was
persisted to the repo — `docs/subagent-fanout-runbook.md`'s "every agent writes its own
file" rule was written *from* this failure and so was not yet in force. But the audit
survives in full in the session journal under
`~/.claude/projects/<this-project>/…/subagents/workflows/wf_f8c85180-b74/`, which holds
279 agent transcripts including ~9 KB of structured output for `ttuDirect` (verbatim
command transcripts, a positive control, and a self-caught instrument bug). **The three
adversarial verifiers dispatched for that claim are each 4 lines: prompt in, nothing
out** — the death of the fan-out, visible on disk. Worth knowing before re-running
anything: a dead fan-out is recoverable from the journal, so item 4 below need not start
from zero.

⚠ Of the 26 audits that completed, one reported `divergenceFound: YES` on a schema **both
backends refuse** — the false positive the verify phase existed to kill. Neither claim
above was that one, but the rule stands: reproduce before promoting.


@@@

### CUT residue
- [x] ~~**`_any_residue_reference` / `_keys_referencing` — MEASURED 2026-07-29; the fix
      is not done.**~~ **DONE 2026-08-14.** The scan is now an indexed seek on a new
      `ResidueRefV1` reverse-index table — the fix `ZT-P0-1`'s own note named, maintained
      in `_store_residue` (via `_sync_residue_refs`) and in `bulk_build`'s offline path.
      Re-measured: the lookup is **FLAT in R** where it was linear (0.30 → 13.03 ms
      across R=25→1600 before; 0.11–0.22 ms throughout after). The extrapolated ~1.4 s
      per node release at 100k residue rows and the quadratic churn are gone by
      construction, not reduced. Nothing owed to Lean (the node-GC region has no model
      at all, §7.3) — verified, and the three function NAMES were kept deliberately
      because `verify.sh` step 4d resolves them as `CORRESPONDENCE.md` anchors.
      Design, measurement, migration note: `docs/spec-deviations.md` 2026-08-14.
      * ★ **The transferable finding, from the sabotage that did NOT fire.** Skipping
        index maintenance on the residue-DELETE branch alone left the whole new test
        file **green** (`11 passed`); only the paranoia-driven matrix caught it. An
        orphan is observable only when the indexed row goes from ref-bearing straight
        to deleted in ONE step, and every natural teardown ordering empties
        `neg`/`upos` while `stars` is still present — clearing the index through the
        *update* branch, so there is nothing left to orphan. **A teardown test is not
        a delete test.** Generalises to any index maintained beside a deletable row;
        `test_residue_emptied_in_one_step_takes_its_index_rows_with_it` is the pin.
      * ⚠ **No migration path exists and none is offered.** An index built before this
        change gets an empty `residue_ref_v1` from `create_all`, and its node-release
        guards would then believe nothing is referenced (the ZT-P0-1 direction). The
        cheap `ZANZIBAR_PARANOIA=residue` tier fires on the first commit against such
        a store; rebuild with `build_index`.

@@@

### CUT openfga
- [x] ~~**Vendor a corpus of REAL OpenFGA schemas, crawled from the wild**~~ —
      **DONE DIFFERENTLY, 2026-08-11: reviewed, measured, and ADAPTED rather than
      vendored.** The user supplied a corpus (canonical `openfga/sample-stores` +
      internal models). Outcome, all measured:
      * **48 schema files, 22 compile, and `UnsupportedByGraphIndex` rejections = 0.**
        That is the evidence this item was built to produce → see the scope-rejection
        item directly below, whose deferral is now **evidence-backed rather than
        assumed**. (The 26 non-compiling are out of scope by construction, not
        rejections: 11 use CEL conditions, 4 use modular `module` models, 11 are
        `model_file:` indirections or test-only files.)
      * ⚠ **This item's own premise was WRONG, and the correction is the useful part.**
        It said real schemas "essentially never touch the wildcard × boolean × TTU
        crosses". One internal schema hits that cross dead-on — a De Morgan
        "holds ALL required roles" model with `[user:*]`, an exclusion over it, a TTU
        whose TARGET is derived, and that TTU under a negation. **The prediction still
        held** (0 divergences; an RC1 sabotage leaves it green, instrument controlled
        against the known RC1 repro) — but "they never touch the crosses" is false, and
        the *reason* to expect passing is not the reason recorded here.
      * **Nothing was vendored, and copying would have been near-worthless anyway:**
        `demorgans_law_2.fga` is structurally the same schema as the interesting
        internal one, plus an `and` and an extra TTU hop. **Three** shapes measured at
        **zero occurrences across all 11 pre-existing fixtures** were adapted instead —
        `userset_over_derived.fga`, `heterogeneous_tupleset.fga` and
        `tupleset_shapes.fga`, driven by `tests/test_schema_shapes.py`.
        ★ Two findings worth carrying:
        **(i)** every TTU tupleset in the old corpus was **single-type**, so
        `parent_types` was never exercised with breadth > 1 — and `parent_types`
        breadth is exactly what RC1 got wrong; a single-type corpus cannot distinguish
        "computes the set correctly" from "returns the only candidate".
        **(ii)** scoring every fixture against `genswarm`'s DERIVED alphabet showed
        **every reachable uncovered feature sat on the TTU-tupleset axis** — the axis
        RC1/RC2 lived on. `tupleset_shapes.fga` closes it and is the only one of the
        three that **catches RC1**: under the sabotage it does not answer wrong, it
        refuses to COMPILE (the 2026-08-11 invariant). It is the tree's first RC1
        regression pin in `.fga` form.
        Corpus coverage went **43 → 46 of 51 features / 903 → 1035 of 1275 pairwise
        cells**, floored by `test_fga_corpus_feature_coverage_does_not_regress` with the
        residual gaps pinned as an EXACT set (all five are measurement artifacts or
        carry executable rejection witnesses).
      * **8 of the 14 fixtures contribute no unique feature at all** —
        `boolean_wildcards`, `confluence`, `custom_roles`, `demorgans_law_2`,
        `demorgans_reverse`, `gdrive`, `github`, `master_store`. Not a reason to delete
        them (they are cheap realism anchors and feed the snapshot/bulk gates), but it
        is where the corpus was spending coverage without buying any.
      * **Licensing sidestepped, not solved.** Adapting rather than copying means no
        internal schema text entered the tree and no per-schema manifest was needed.
        If anyone later wants the literal schemas, that decision is still open and is
        the user's. `.scratch/` is now gitignored (`0e6ef33`) — it was untracked but
        NOT ignored, in a repo that mirrors.
      * **The "plausibility anchor" use is RETIRED, not deferred** (user, 2026-08-11).
        The original filing wanted real schemas as a realism weighting for the
        generated-schema campaign. **That only pays off if you are prioritising WHICH
        divergences to fix first — and this project's goal is that everything is
        correct**, so a realism prior buys nothing and would actively mislead: every
        bug this repo has found lived in a cross that real schemas rarely reach.
        Feature coverage against the derived alphabet is the right instrument, and it
        is the one now floored. Also, practically, there is no downloadable corpus of
        real models — production authorization schemas are mostly not public, and
        arguably should not be. Do not re-open this on "we should ground the fuzzer in
        reality"; ground it in the compiler's own feature space instead.

      *Original filing kept below for the reasoning it recorded.*
      **What it is for, and it is NOT bug-finding.** Real-world schemas are union/TTU
      heavy and essentially never touch the wildcard x boolean x TTU crosses where every
      divergence this repo has found actually lived, so expect them to pass. The value is
      that they are the **empirical instrument for the scope-rejection item directly
      below**: that item defers on "revisit on a concrete need", and its *previous*
      priority argument was already found INVALID once (see its own note). A corpus of
      schemas people actually wrote is how you decide whether a concrete need exists —
      if 3 of 40 hit `UnsupportedByGraphIndex` the item's priority changes overnight; if
      0 of 40 do, the deferral becomes evidence-backed instead of assumed. Second use:
      a plausibility anchor for the generated-schema campaign, which is otherwise tied
      to nothing real.
      **Precedent already exists** — `tests/fga_schemas/gdrive.fga` and `github.fga` are
      OpenFGA's canonical sample stores, already vendored. This extends an accepted
      pattern.
      **Sources:** `openfga/sample-stores`, the OpenFGA docs modeling guides, the
      playground examples, GitHub code search for `.fga` / `model\n  schema 1.1`.
      **Two constraints:** record provenance + license per schema in a manifest (OpenFGA
      is Apache-2.0), and remember a crawl supplies **inputs only** — `tests/oracle.py`
      stays the spec, so a real schema is a query-grid subject, never an expected answer.

---

## Retired 2026-08-16b — the handoff-system migration (second batch)

The narrative half of `HANDOFF.md` was retired here on **2026-08-16** when that file was
rewritten into a compact priority board (the design is
[`docs/handoff-redesign-2026-08.md`](../handoff-redesign-2026-08.md); the survey evidence
is [`handoff-migration-map-2026-08.md`](handoff-migration-map-2026-08.md)). **Provenance,
not open actions.** Five blocks moved: the two "What landed" session blocks, the
"Still open" recap, the closed §1/§2 sections, and the whole 2026-08-11 status run.

⚠ **Status lines below are frozen as-of-then and several were already false when moved —
see "Corrections applied on archiving" immediately below.** Live state is the board in
[`HANDOFF.md`](../../HANDOFF.md) plus
[`docs/history/session-log.md`](session-log.md).

**This section is keyed `2026-08-16b`** because an earlier section in this same file is
already `## Retired 2026-08-16 (leg 7 4c-i session)`. Cite them by their full titles; a
bare date is ambiguous between the two.

⚠ **Deictic references in the moved text point at the OLD `HANDOFF.md`.** The text is
reproduced verbatim, so "this file", "the banner at the top", "§1 above", "the board item
below" and "item 3" all refer to `HANDOFF.md` **as it stood on 2026-08-16, before the
rewrite** — a file that no longer exists in that shape. The numbered sections §1–§6 it
cites are gone; resolve them against the board ids instead (`P3`–`P13`), or against
`git show ac3847b:HANDOFF.md`. Headings in the moved blocks were demoted one level so they
nest under this section; nothing else in them was altered.

### Corrections applied on archiving (2026-08-16b)

Nine statements in the moved text were not merely dated — they were **actively false** by
the time of archiving, or became false the moment the text left `HANDOFF.md`. They are
retained for provenance with the correction recorded here rather than silently deleted.

1. **"The leg is NOT finished; steps 4c-i, 4c-ii, 4b, 5, 6, 7 remain."** (2026-08-11 status
   run, "LEG 7 STARTED HERE"). — **4c-i landed 2026-08-16** (`GraphIndex/LeafRules.lean`,
   commit `ac3847b`). The remaining steps are **4c-ii, 4b, 5, 6, 7**, and 4c-ii must
   co-land with 7.
2. **"Step 4c is blocked on a design fork the scope doc does not contain (§11.3) … attack-first
   that before coding either branch."** (same block). — False in both halves. The fork was
   **decided as branch (α) on 2026-08-14**, and the scope doc does now contain it:
   `formal/history/leaf-family-split-scope-2026-08-05.md` §11.5, which also records that
   **§11.3 is wrong in two places, both measured**.
3. **"Audits 520 → 573, anchors 471 → 497"** (in "What landed 2026-08-16", restated in the
   "Still open" recap). — **Both end figures are wrong** against the machine-checked block
   generated in the same commit: `formal/FINAL_REVIEW.md`'s generated counts block gives
   **581** audited theorems and **524** anchors (re-verified 2026-08-16). This is `ZT-P3-5`
   recurring *inside the session block that boasts of removing figures from the banner*.
   **Do not carry 573/497 forward.**
4. **"See the banner at the top of this file for the measured figures."** (2026-08-11 status
   run). — The banner has deliberately carried **no** figures since 2026-08-14. Live
   figures are `formal/FINAL_REVIEW.md`'s generated counts block, and nowhere else.
5. **"Three things are kept HERE because they are live, not historical"** (§1) and **"Three
   things survive as live constraints rather than history"** (§2). — False by construction:
   "HERE" is now this archive. Their real homes as of 2026-08-16: the **mirror instrument**
   and the **severity-sign rule** are both in
   [`docs/sabotage-procedure.md`](../sabotage-procedure.md) (the severity-sign rule was
   lifted there *by this migration* — it had no runbook home before); the
   generator-coverage figures are in `docs/design/generator-coverage/`; the
   **do-NOT-lift-`ttuDirect`** constraint is a standing trap on the board; and the
   decidable-`W4Fragment` descendant is board row `DW-1`, recorded in
   `formal/CORRESPONDENCE.md` §2.
6. **"`tests/test_generator_coverage.py` (26 gated tests)"** — that is **this file's own**
   §1b text at the "STATUS: (a), (b) AND (c) ARE ALL IMPLEMENTED AND GATED" paragraph, and
   it is stale. Re-measured 2026-08-16 with `--collect-only`: **27 tests collected**. The
   body is left unedited; this entry is the correction.
7. **"(iv) carries a possibly-blocking decidability question"** (wherever it appears in the
   2026-08-14 and earlier text). — **Answered NO-BLOCK on 2026-08-16**, machine-checked
   (`GraphIndex/TtuStarWide.lean`). Already flagged dead in this file's `## Retired
   2026-08-16 (leg 7 4c-i session)` header; repeated here because the claim also appears in
   the newly moved blocks.
8. **"### What landed 2026-08-16 (most recent session)"** — "most recent session" is a claim
   about the present that an archive cannot make; it was false for the very next session.
   Read it as "the session of 2026-08-16".
9. **"the severity-sign rule and the mirror instrument stay in `HANDOFF.md` §1"** — that is
   this file's own `## Retired 2026-08-16 (leg 7 4c-i session)` intro, and it went false the
   moment §1 was archived by this batch. Both now live in
   [`docs/sabotage-procedure.md`](../sabotage-procedure.md).

**Verified as needing NO correction** (checked because they read like corrections to other
documents): **"§4's prescription is REFUTED — do not fork `writeDirect`, fork the TUPLE"**
is already carried by the document it corrects, at
`formal/history/leaf-family-split-scope-2026-08-05.md` §11.1; and the index-2 breadth
overstatement is carried at that same doc's §11 tail and in `PROOF_STATUS.md` 2026-08-16.
Both are archived below without loss.

#### CUT HANDOFF.md:44-95 (2026-08-16, pre-migration numbering)

#### What landed 2026-08-16 (most recent session)

**Leg 7 step 4c-i is IN with a ZERO recompile cone; the allocation it rests on was refuted
THREE more times first — once by an instrument that was itself blind; and `ttuStarFree`
part (iv)'s standing blocking question is ANSWERED.**

* **★★ Step 4c-i — the leaf-provenance rule layer** (`GraphIndex/LeafRules.lean`, NEW).
  `leafRewrites` supplies the half `schemaRewrites`' taint filter omits: each derived key's
  CLOSURE leaves compile to rewrite rules targeting the **minted leaf name**, exactly as
  Python's `_emit_leaf_expr` → `_rewrite_rule(expr, object_type, leaf)`. Additivity is
  **proved**, not observed (`schemaRewrites_leafRewrites_disjoint`: untainted rules target
  declared dot-free names, leaf rules target minted dot-carrying ones), and
  `writeRulesRaw_untaintedSchema` says the same at the write level. Measured before it was
  written: **50/50 schemas, 0 mismatches, 32 with a non-empty leaf rule set.**
* **⚠ THE ALLOCATION WAS WRONG THREE MORE TIMES**, all caught before 4c-i was built on it:
  Python **merges** a maximal pure subtree (`(a or b) but not banned` → `r.0={a,b}` /
  `r.1=banned`, not three leaves, storage always allocated first); a tainted **userset**
  restriction gets its own storage leaf (reachable from the LIVE fixture
  `tests/fga_schemas/userset_over_derived.fga`); and the n-ary union **spine**.
* **★★ THE TRANSFERABLE FINDING — a new member of the mirror-instrument family**, written
  up in [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md). The first two fixes
  were validated by transcribing the Lean model into Python and diffing: *"82/82 derived
  keys, 0 disagreements"*. That transcription consumed Python's **n-ary** AST — but Lean
  never sees it, because `formal/conformance/encode.py::_fold_binary` **LEFT-FOLDS**.
  Re-run over the binarized tree: **1 disagreement, on `nary_union_derived4`, which is IN
  `GRAPH_FRAGMENT`.** *A transcription of the right rule over the wrong input
  REPRESENTATION is the mirror instrument with extra steps.* And the second, genuinely
  independent instrument (744/744, three positive controls) was **structurally incapable**
  of catching it — it maps closure leaves to `none`. Two green instruments, one shared
  blind spot.
* **★★ A LIMIT OF THE MODEL'S AST that leg 7 must now carry.** `Core/Schema.lean` justifies
  left-folding n-ary unions by associativity+commutativity — true of `sem`, **false of the
  leaf ALLOCATION**. Measured: `a or b or safe` → 2 leaves, `(a or b) or safe` → **1**, and
  the encoder maps both to the same `Expr`. The model is faithful to the FLAT form (the only
  one any corpus writes); the other shape is now **refused mechanically**, not by a doc
  warning, at
  `formal/conformance/test_conformance_state.py::test_no_corpus_nests_a_pure_union_inside_an_impure_one`
  (sabotage-verified). Faithful-to-both needs an n-ary `Expr` — a trust-root change.
* **★★ `ttuStarFree` part (iv) is UNBLOCKED** (`GraphIndex/TtuStarWide.lean`, NEW,
  additive, no caller). The board has carried "(iv) has an unanswered question that could
  block it outright — is the widened predicate still decidable by a boolean function?"
  since 2026-08-14. **Answer: NO-BLOCK, machine-checked.** `TtuStarFree` is a bounded
  quantification over finite lists; the widening only weakens the body; the new conjunct
  `Schema.isSubjectWildcardUserset` is **already `Bool`-valued**. So `ttuStarFreeWB` decides
  `TtuStarFreeW` and `removeGateB` widens by the same textual edit. Proved a genuine
  weakening *and* strictly wider at a store, with two sabotages reddening **disjoint** pins
  (strictness vs soundness). ⚠ `W4Fragment.ttuStarFree` is UNCHANGED — the 2026-08-10
  refutation stands until part (ii) materializes the bridge.
* Audits 520 → **573**, anchors 471 → **497**; headline statements 38/38 and definitions
  155/155 **UNMOVED**. Also re-measured: *"17 of 25 corpora mint indices 1 AND 2"*
  overstated the index-2 breadth 3.4× — index ≥1 in 17 of 25, index 2 in **5**.


#### CUT HANDOFF.md:96-121 (2026-08-16, pre-migration numbering)

#### What landed 2026-08-15

**Leg 7 4c-pre: the briefed step 4c was REFUTED by measurement before its 36-module cone
was paid, and the addressing layer under it landed measured-correct instead.**

* **★★ The kill (attack-first, before coding):** enumerating the 76 P6-dropped edge rows
  per corpus shows **leaf indices 1 and 2 in 17 of 25 `GRAPH_FRAGMENT` corpora** — every
  non-first boolean arm gets its own leaf — and a raw write **fans out to every matching
  storage leaf**. So the landed `rawWriteRel` (single target, hardcoded index 0) could
  never meet the landing criterion, in index OR arity. Worse structurally: the dropped
  rows are mostly RULE-copied closure leaves whose index depends on **which arm produced
  the copy** — provenance `rewriteClosure` does not carry — so **4c is not a caller
  re-point at all**; the rule layer must mint leaf-indexed targets first. Revised plan:
  scope-doc **§11.6** (4c-i rules-with-provenance → 4c-ii caller re-point + (α) row move,
  4c-ii + 7 still co-landing).
* **What landed in Lean (`GraphIndex/Leaf.lean`, reworked while still unwired — the cheap
  moment):** `persistedLeaves` (the measured pre-order allocation; derived refs and
  non-pure TTU arms consume no index), `leafPublic`/`publicOfLeaf` (the (α) leaf→public
  map, **index-agnostic by construction**; `publicOfLeaf_rawWriteRels` is the feeder
  `affectedKeys` will consume), `rawWriteRels`/`rawWriteTuples`/`writeDirectRaw` (the
  filtered fan-out). Every measured Python fact is a `decide` pin (`swU_routes` =
  §11.5's `approver.2`; `swF_fanout`; `stP_leaves`/`stD_leaves`; `swX_skip`), **five
  sabotages run with attributable reds and green controls** — including the `".0"`-
  stripper run where the index-0 pin stayed green, proving an index-0-only pin would
  have been vacuous. Audits 501 → **520**; headline statements/definitions UNMOVED.


#### CUT HANDOFF.md:161-181 (2026-08-16, pre-migration numbering)

#### Still open — updated 2026-08-16

**What moved 2026-08-16:**
* **Leg 7 step 4c-i LANDED** (`GraphIndex/LeafRules.lean`) — and the cost went DOWN, not up:
  §11.6 sized it as ~double the Cascade cone, but as an extension downstream of
  `RulesWrite` the recompile cone is **one file**. The remaining expense is concentrated in
  **4c-ii + 7**, which must co-land. See item 5 and scope-doc **§11.7**.
* **The allocation 4c-i rests on was refuted three more times first**, once by an instrument
  that was itself blind — including a wrong model of the in-fragment corpus
  `nary_union_derived4`. Audits 520 → **573**.
* **`ttuStarFree` part (iv) is UNBLOCKED** — the decidability question is answered NO-BLOCK
  and machine-checked. Item 3.

Item 4 (the scope-audit re-run) is untouched and not blocking. **Item 3 moved on
2026-08-16: part (iv)'s decidability question is ANSWERED (NO-BLOCK) and the predicate +
its decider are machine-checked in `GraphIndex/TtuStarWide.lean`; parts (ii) and (iii)
remain.**
Item 6 is a one-question optional loose end from the closed arc. **Item 2 (the two
UNVERIFIED audit leads) was CLOSED 2026-08-14** — both reproduced, neither leaves a live
bug; read its residue before touching the zcli driver or `ttuDirect`.


#### CUT HANDOFF.md:182-239 (2026-08-16, pre-migration numbering)

#### 1. The RC1/RC2 arc — CLOSED. Archived 2026-08-11; three things kept here.

Both root causes are fixed (RC1 `ed46e54`, RC2 2026-08-11), the fix list is fully
discharged, and the generator gap that hid them is closed. The full text as it was briefed
while open — the divergence filing, the fix list, the generator-coverage leg, and the
measured-FALSE mechanisms — moved to
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md) §§1–1b.
**Read it before re-opening anything in this area**: it records which mechanisms were
measured FALSE, and a reader who acted on the original filing would have rewritten correct
leaf-routing code.

Three things are kept HERE because they are live, not historical:

* **★ The severity-sign rule — the single most transferable output of the arc.** A dropped
  TTU parent is a false NEGATIVE under a positive TTU and a false POSITIVE (an authorization
  **fail-open**) under a negated one (`define access: [user] but not viewer from parent`).
  **Probing only the positive direction mis-classifies severity by one sign** — which is
  exactly what the original filing did. Any new TTU corpus must carry both directions.
* **★ An instrument that shares its subject's defect cannot see it.** Neither RC was caught
  by I1–I14 with paranoia ON, and **I9 structurally CANNOT** catch this class: it re-runs
  `reconcile`, reads the same wrong `parent_types`, and agrees with itself. That is why the
  new compile-time invariant reads the emitted `RewriteFilter`s and **never** `_member_types`.
  Generalised in [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) ("the mirror
  instrument").
* **Generator coverage — the current baseline, and its honest limit.** `tests/genswarm.py`
  + `tests/test_generator_coverage.py` (**27** gated tests — re-measured 2026-08-11 with
  `--collect-only`; the archived prose says 26 and was already stale) reach, against a 1275-cell pairwise
  space **derived from six compiler sites** rather than hand-written:

  | | cells | % |
  |---|---|---|
  | baseline before the leg (the old generators) | 514 | 40.3 |
  | union, `ci` | **967** | **75.8** |
  | union, `deep` | 1034 | 81.1 |

  `UNACCOUNTED == set()` exactly, with no hand-written exemption list; 3 cells carry
  executable rejection witnesses instead. **~24–28 % of the pair space is still unreached
  even at `deep`** — so read a green gate as "the instruments we have found nothing", not as
  a proof. Design + raw evidence: [`docs/design/generator-coverage/`](docs/design/generator-coverage/).

#### 2. ~~Verify or discard two UNVERIFIED claims from the failed audit.~~ CLOSED — archived 2026-08-16.

Both were reproduced from scratch on 2026-08-14 with attribution and positive controls.
**Neither leaves a live correctness bug; do not re-open either.** Full text, including the
`zcli` mode=graph fail-CLOSED finding and the `ttuDirect`-was-RC2 re-measurement, is in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md).

Three things survive as live constraints rather than history:
* ⚠ **Do NOT lift `ttuDirect` in Lean** (the audit's recommendation #3), consistent with
  item 3 below and `CORRESPONDENCE.md` §7.
* **The one genuinely open descendant, and it is its own leg:** a driver-side fragment
  pre-check needs a **DECIDABLE `W4Fragment`**, and none exists (no `admissionB`-style
  boolean). Nothing is blocked meanwhile. ★ Note the contrast with `ttuStarFree` part
  (iv), whose analogous decidability question turned out to be answerable (2026-08-16) —
  so this one is worth actually attempting rather than assuming.
* **The audit's primary record survives in the session journal**, not the repo:
  `~/.claude/projects/<this-project>/…/subagents/workflows/wf_f8c85180-b74/` (279 agent
  transcripts). That is also item 4's head start.

#### CUT HANDOFF.md:358-488 (2026-08-16, pre-migration numbering)

### Status run — 2026-08-11 (historical; the live status is the banner at the top)

**🟢 The gate is GREEN end to end, and the 2026-08-10 fail-open family is CLOSED.** All
ten phases plus the 6-seed fuzz sweep; no `sorry`, no `xfail`, no skip. See the banner at
the top of this file for the measured figures.

* **Known live correctness bugs: 0.** RC1 (`ed46e54`, 2026-08-10) and RC2 (2026-08-11) are
  both fixed, both at every site, and both pinned by positive assertions rather than
  xfails. The bounded exhaustive sweep that mapped the family found exactly two root
  causes, so it is closed at two.
* **Nothing regressed to get here.** Both bugs were PRE-EXISTING — RC1 reproduces on a
  hand-written schema at `e136c8c` with no `.py` file touched. The 2026-08-10 session made
  them *known and pinned*; this one fixed them.
* **★ The 2026-08-09 "everything is green" was true of the gate and false of the code**,
  and that caveat is now DISCHARGED rather than merely repeated: the generator-coverage leg
  landed (cell coverage, swarm, a drawn TTU tupleset, two driving regimes), and it is what
  made RC2 visible to a generator at all. A green gate here now means meaningfully more than
  it did — but its honest limit still stands, ~24–28% of the pair space is unreached even at
  `deep`, so read green as "the instruments we have found nothing", not as a proof.
  Numbers in §1 above; full leg in the 2026-08 archive §1b.

- **LEG 7 STARTED HERE — steps 3 and 4a went IN** (2026-08-09, `8291c3a` + `41b7029`).
  `formal/lean/ZanzibarProofs/GraphIndex/Leaf.lean` is new: leaf addressing,
  the raw-write routing, the forked write `writeDirectRaw`, and the distinctness linchpin.
  Additive — headline statements 38/38 and the definition pin 155/155 **unmoved**.
  ⚠ **The raw-write half of this bullet was SUPERSEDED 2026-08-15** — `rawWriteRel`'s
  single index-0 target was measured wrong and is now `rawWriteRels` (a fan-out); see the
  banner. The addressing and linchpin halves stand.
  **The leg is NOT finished**; steps 4c-i, 4c-ii, 4b, 5, 6, 7 remain. Three things a next session
  must read before touching it (all in `formal/history/leaf-family-split-scope-2026-08-05.md`
  §11 and `formal/history/PROOF_STATUS.md` 2026-08-09):
  * **The scope doc's §3 bet HELD** — the leaf-vs-bare distinctness linchpin needs no new
    axiom, `relNameOK` already gives it.
  * **★ Its §4 prescription is REFUTED.** Do not fork `writeDirect`; fork the TUPLE, as
    `RuleSet.apply` does. `writeDirect` then stays byte-identical and the duplication §4
    predicted for every projection and fold lemma is not owed.
  * **★★ Step 4c is blocked on a design fork the scope doc does not contain** (§11.3):
    once the edge moves to the leaf node, where is the `Delta` row addressed? The
    `Delta.leaf` tag does not answer it. Attack-first that before coding either branch.
- **Previously landed: THE `rewriteClosure` DEDUP LEG — `CORRESPONDENCE.md` §7.2 item 6 is
  CLOSED** (2026-08-08, `911c887` + `c488a2f`). The Lean model counted DERIVATION PATHS
  where Python counts LIVE RAW TUPLES, so on a *reconvergent* schema it over-counted edge
  multiplicity; `rewriteClosure` now mirrors `RuleSet.apply`'s worklist dedup, per stored
  tuple. Two corpora (`reconvergent_diamond`, `reconvergent_derived`) were added FIRST, in
  their own deliberately-red commit, so the divergence was attributable rather than
  arriving mixed into the fix. The count stack needed zero proof rework; the definition
  pin moved (154 → 155) while all 38 headline statements stayed byte-identical. **Leg 7's
  step 2b is discharged.** Three findings that correct live documents are in the board item
  below; full detail in `formal/history/PROOF_STATUS.md` 2026-08-08b.
- **Previously landed: E-chain Direct-arm widening, LEGS 5 AND 6 — `ZT-P3-1` IS CLOSED for
  T2b** (2026-08-05). The headline `graph_correct` / `backend_equivalence` /
  `exclusion_effective` / `no_ghost_grant` / `Exec.graphRun{,Ops}_check_eq_sem` are **no
  longer VACUOUS on `can_view: [user] but not blocked`**, the canonical Zanzibar boolean
  shape they had said nothing about since the claim was first written.
  `W4WitnessDirect.final_applies` instantiates the unsuffixed T2b at that store, and
  `final_applies4` does it at the four-tuple `direct_arm_exclusion` corpus store verbatim.
  * **Leg 5** rebased the bundles: `GraphAdmission.storeValid` → `StoreValidRulesD`;
    `W4Fragment`'s single `computedOnly` field → **five** derived-def clauses (so **ten**
    fields, not the plan's nine — `DirectArmsConcrete` again, exactly as §C.4 warned).
    `graph_correct` routes through `graph_correct_w3d2E_d`; the T3/T6 finals and both Exec
    drivers inherited it with **zero edits**. `w4Fragment_of_computedOnly` machine-checks
    that the old six fields imply all ten, so nothing that held before stopped holding.
  * **Leg 6** moved `direct_arm_exclusion` from `_DIFFERENTIAL_ONLY` into
    `_THEOREM_BACKED` (`_EXPECTED_SPLIT` `(22,1)` → `(23,0)`) and retired the vacuity
    caveat from ~25 prose sites across `formal/` and `docs/`.
  * **⚠ T2a did NOT widen, and now says so in its own type.** `graph_reached_inv` takes a
    third bundle `W4NarrowT2a` (schema-wide `ComputedOnly` + narrow `StoreValidRules`), and
    `outside_narrow_t2a` machine-checks that the Direct-arm store fails it. **T2a is still
    vacuous exactly where T2b no longer is.** Not a proof gap — probe D.3 machine-checked
    `Inv.negEdgeFree` FALSE on the `_d` fragment; Python is fine (P6 leaf-family modelling
    limit). A **design decision** is owed, not effort. This is the arc's predicted honest
    end state (plan §F) and the board item below is now about that decision.
  * Audits 471 → **481**; statements **26 → 38**; definitions **142 → 154**. No Python
    behavior changed (only conformance CLASSIFICATION + prose), so no fuzz sweep was owed.
  * **★ The leg-5 sabotage is the transferable finding, and it is worse than legs 3/4's.**
    A bundle REBASE needs a different control than a packaging clone. The plausible failure
    is the **half-done leg**: widen `W4Fragment` but leave `GraphAdmission.storeValid`
    narrow and convert with `storeValidRulesD_of_storeValidRules_directArmsBare` — which
    **typechecks**. Every gate signal then reads as success (statement byte-identical,
    definition pin MOVES so the gate even reports "meaning changed", audits clean), and the
    theorem is still worth nothing. Measured: with the witnesses present, ONE error in the
    whole tree; delete the four witness declarations and it is **"Build completed
    successfully (1084 jobs)"** — and since both goldens are GENERATED from the tree, the
    leg would have regenerated them to a self-consistent pair and passed the entire gate.
    Legs 3/4's sabotages at least reddened `FullScope`; this one reddens nothing.
  * Detail: `formal/history/PROOF_STATUS.md` 2026-08-05c/d, plan §C.5/§C.6.
- **Previously landed: legs 2/3/4** (2026-08-04 / 2026-08-05 / 2026-08-05) — the
  enumeration model change, the coverage packaging, the chain projection + E-chain final.
  Each carries a plan correction worth reading before trusting any cell of that document:
  two of its instructions were refuted by measurement, its gate specification was found
  insufficient **three legs running**, and its obligation inventory missed a hypothesis.
- **Previously landed: the P3 edge-multiplicity blind spot, ADJUDICATED and closed** — the
  last open item where the gate was blind to a whole class of divergence. Verdict:
  real, model-side, confined exactly to the DERIVED arm (Python's presence diff caps
  `direct_edge_count` at 1 there; the model compounds to 1013), removal-inert. P3 is
  narrowed so untainted-arm multiplicity is now compared EXACTLY — 153 edges that
  nothing had ever compared — and the derived arm is golden-pinned. Detail:
  `formal/CORRESPONDENCE.md` §7.2, `docs/spec-deviations.md` 2026-07-29.
- **Also landed 2026-07-29: the counts pin.** `ZT-P3-5` ("every doc number is stale and
  nothing enforces any of them") had been hand-fixed twice and rotted a third time, so
  `formal/FINAL_REVIEW.md`'s headline counts are now GENERATED
  (`formal/conformance/doc_counts.py`) and checked by `verify.sh` step 4e. It **fired on
  this session's leg-6 doc edits** (a new `CORRESPONDENCE.md` anchor), which is the first
  time it has caught a live drift rather than a historical one.
- **Live gate figures live in ONE place** — the generated counts block in
  `formal/FINAL_REVIEW.md`. Do not restate them here; this file went stale three times
  doing exactly that.

**History moved out 2026-07-29:** the dated status run, the full zero-trust review, and
every completed board item are now in
[`docs/history/handoff-status-2026-07.md`](docs/history/handoff-status-2026-07.md),
together with the reconciled **`ZT-*` disposition ledger** (which fixes three ids that
had no disposition anywhere and one that was listed CLOSED while its substance was
open). This file is now only what a future session must ACT on.

**History moved out again 2026-08-16:** the "What landed" blocks for 2026-08-11 and
2026-08-14, board item 2 (both audit claims adjudicated), the completed
`_any_residue_reference` item, and the completed OpenFGA-corpus item — 288 lines — are in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md)
§"Retired 2026-08-16". **The METHOD from each was kept in the live docs, not archived with
the status** — notably *"a teardown test is not a delete test"*, which is now a named
subsection of [`docs/sabotage-procedure.md`](docs/sabotage-procedure.md) rather than a
bullet inside a ticked checkbox.

**History moved out again 2026-08-11:** the whole RC1/RC2 arc as briefed while open (the
divergence filing, the discharged fix list, the generator-coverage leg) plus four completed
board items are now in
[`docs/history/handoff-status-2026-08.md`](docs/history/handoff-status-2026-08.md).

---


