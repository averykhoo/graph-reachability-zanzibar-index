# HANDOFF — start here

The single entry point for a Claude Code (or human) session on this repo. Read
this **first**, then [`CLAUDE.md`](CLAUDE.md), then whatever the task points into.

- **`CLAUDE.md`** = the durable contract (how to run things, conventions, the
  gate, invariants). It rarely changes.
- **`HANDOFF.md`** (this file) = the mutable state: current status + the open-TODO
  board. **Keep it current** — when you pick up or finish work, edit the board
  below. This is the "one thing to point at" so instructions don't have to be
  relayed each session.

> The formal subtree has its own compact entry point,
> [`formal/HANDOFF.md`](formal/HANDOFF.md) — read that before touching anything
> under `formal/`. This file is the whole-project analog.

---

## Current status — 2026-07-17

- **2026-07-17 — the three OPEN 2026-07-17 divergences CLOSED (+ a 4th found en route)
  + reg13 admission wart fixed + fuzzer exclusions reverted; full gate GREEN; UNCOMMITTED
  (awaiting Avery's go-ahead).**
  The three OPEN/latent divergences filed earlier today (below) were root-caused and fixed,
  their strict xfails flipped to plain pins: **Fix A** — the reconcile audit-set builder
  (`processor._leaf_concretes`, + `bulk_backfill` mirror) now lifts a referenced tainted
  relation's residue `upos` for `derived-computed`/`derived-userset` leaves (the X4b lift
  extended), closing the two answer-level completeness gaps **and a NEW 4th** (userset member
  of a granted userset over a derived relation). **Fix B** — a state-functional `implicit` flag
  (promote-on-record step 2d + a demote-on-release exception to core's explicit-is-sticky rule,
  I6 extended) closes the answer-benign canonical drift. **reg13** — `RuleSet.apply` now raises
  (not silent-drops) a raw write matching no declared restriction (a unanimity wart; production
  unexposed). Fuzzer exclusions reverted: `allow_usersets` default ON, `ttu_in_boolean` knob
  removed — zero active 2026-07-17 generator exclusions remain. `HYPOTHESIS_PROFILE=deep` hunt
  green (state trio 3/87 s, machines 3/310 s, rest 14/629 s, deep G4 1/45 s; no falsifying
  examples). Two read-only scout sweeps (read/enumeration symmetry; ~3,800 remove-heavy
  delta/lifecycle sequences) found ZERO further gaps. **Gate GREEN (2026-07-17): `pytest tests/`
  561 + 32 = 593 passed, 0 xfailed (cap-safe split); `verify.sh` lean PASSED (sorry-free,
  412/412) / conf-heavy 68 PASSED / conf-rest 195 PASSED; 6-seed fuzz sweep on
  `tests/test_hypothesis.py` (seeds 7/19/31/53/71/97) all 20 passed.**
  Details: `docs/spec-deviations.md` 2026-07-17 ("the three OPEN 2026-07-17 divergences CLOSED");
  formal note in `formal/CORRESPONDENCE.md` §7.
- **2026-07-17 — F1/F2 CLOSED + fuzzer blind-spot hardening landed; full gate green;
  UNCOMMITTED (awaiting Avery's go-ahead).** The F1/F2 divergences (and their
  newly-found "detonation" — innocent-write lockout, a 3rd divergence) are closed by a
  compile-time scope rejection (`DoublyBridgedShapeError`, both backends, literal
  `T:*#p` ∩ object-wildcard criterion) + a set-engine ghost-hop safeguard (never
  fires, test-pinned). The generator blind-spot audit + hardening (G1/G2/G4/G5/D4
  + pins) landed; the deep hunt filed **three NEW latent divergences** (1 answer-benign
  drift, 2 graph completeness gaps — X4 family) as strict xfails — see Standing/latent.
  Gate: `pytest tests/` 582 passed + 3 xfailed; `verify.sh` lean (sorry-free, 412/412) /
  conf-heavy (68) / conf-rest (195) all PASSED; 6-seed fuzz sweep on
  `tests/test_hypothesis.py` green. Details: `docs/spec-deviations.md` 2026-07-17.
- **Everything green.** Both evaluation backends (set engine + graph index), the
  composition layer, and the Lean formal layer all pass their gates. Lean is
  sorry-free and axiom-clean (412/412). Known correctness bugs: only the two
  strict-xfail graph completeness gaps filed 2026-07-17 (Standing/latent).
- **2026-07-16 — found + fixed a real set-engine/graph admission divergence.** The
  previously-latent "bridge-edge residual" turned out to be constructible (a
  multi-hop cycle through a star bridge: set-accepted / graph-rejected). Fixed by
  making the set engine's flow-graph cycle check bridge-aware, mirroring the graph's
  `_ensure_bridges` (in-bridges concrete→`w_any`, out-bridges `w_all`→concrete, kept
  distinct). Parity restored; pinned by `test_reg10...`; no Lean change (set-engine
  admission is unmodeled). See `docs/spec-deviations.md`.
- **2026-07-16 — hardened the fuzzer against the whole star-bridge class.** Added a
  dedicated star-bridge schema generator + `StarBridgeParityMachine` to
  `tests/test_hypothesis.py`, a deterministic class pin, and `test_reg11...` (the
  object-wildcard / OUT-bridge analog of reg10). Closed the blind spot that let the
  reg10 bug hide. The new generator also surfaced **two exotic OWC-on-self-referential-
  relation divergences (F1 graph-incomplete, F2 graph-over-permissive)** — filed as
  latent/out-of-scope (backlog + `docs/spec-deviations.md`), NOT chased. Test-only
  change; no backend/Lean change.
- **Perf optimization arc is CLOSED at round 5** — the measured worklist is
  exhausted (the last candidates N13/N14 were assessed and declined on a fresh
  profile). Record: [`docs/history/perf-round5-2026-07.md`](docs/history/perf-round5-2026-07.md).
  Standing perf guardrails (fence, dead-ends, hygiene) live in
  [`docs/perf-next-round.md`](docs/perf-next-round.md).
- **Clean on `master`.** Last change: docs cleanup (commit `972993d`, retire
  completed design/planning docs + align docs to code).

---

## Open-TODO board

### Active work
- [x] **DONE 2026-07-17 (full gate GREEN; uncommitted — commit pending Avery's go-ahead).** **Closed the three OPEN 2026-07-17 divergences (+ a 4th
      found en route) + the reg13 admission wart; reverted the fuzzer exclusions.** Fix A (the
      `processor._leaf_concretes` `upos` lift for `derived-computed`/`derived-userset` leaves,
      mirrored in `bulk_backfill`) closed the two graph completeness gaps + the new 4th; Fix B
      (state-functional `implicit` flag — promote-on-record step 2d + demote-on-release, I6
      extended) closed the answer-benign canonical drift; reg13 made `RuleSet.apply` raise on a
      no-restriction-match raw write. `allow_usersets` default flipped ON, `ttu_in_boolean` knob
      removed — no active 2026-07-17 generator exclusions remain. `HYPOTHESIS_PROFILE=deep` hunt
      green; two read-only scout sweeps found zero further gaps. New pins: reg13 block +
      `test_graph_userset_member_through_granted_userset_over_derived` +
      `test_pderived_recording_promote_demote_hysteresis` + `test_i6_upos_userset_implicit_bites`;
      three prior strict xfails flipped to plain pins. Details: `docs/spec-deviations.md`
      2026-07-17; formal note in `formal/CORRESPONDENCE.md` §7.
- [x] **DONE 2026-07-17 (gate green; uncommitted — commit pending Avery's go-ahead).**
      **F1/F2 fix (started 2026-07-17, Claude+Avery):** compile-time scope rejection of
      shapes in `bridged_in ∩ bridged_out` (a shape that is both a wildcard-userset
      shape and an object-wildcard shape — the F1/F2 precondition). Decision: reject at
      compile (`UnsupportedByGraphIndex`, third entry in the scope-rejection family;
      OpenFGA supports neither construct) rather than a write-time ghost-hop gate.
      Plus: always-on set-engine flow-graph ghost-hop safeguard (w_all→w_any for
      doubly-bridged shapes; unreachable post-rejection, hypothesis asserts it never
      fires), regression pins, fuzzer blind-spot audit + generator hardening.
      New findings recorded en route: both F1/F2 states detonate on innocent later
      writes (graph rejects plain grants set+oracle accept — a 3rd divergence), and
      all→any is NOT read semantics (oracle-pinned via acyclic cross-type probe).
      **Generator-hardening sub-item LANDED 2026-07-17** (fuzzer blind-spot audit closed):
      `schema_asts` now emits concrete usersets (G2), a new `bool_star_bridge_configs` +
      `BoolStarBridgeParityMachine` cross booleans × star-bridge (G1), the machines gained
      `check`/`rebuild` rules + ghost-hop never-fires teardown asserts (D4/G5), and the
      lookup gate runs over generated schemas (G4). THREE OPEN/latent divergences filed as
      strict xfails (a deep `HYPOTHESIS_PROFILE=deep` hunt drove the exclusion calibration) —
      see the Standing/latent section below and `docs/spec-deviations.md` 2026-07-17 (fuzzer
      blind-spot hardening).

### Deferred / backlog (documented, none urgent; none block)

Migrated from the `README.md` "TODO" list (its struck-through items already shipped).

- [ ] **Track user-triples vs rule-triples in the index** — partial today:
      boolean relations already distinguish storage leaves from routed leaves, but
      pure-union relations still mix user-added and rule-derived triples. (The dead
      `legacy/index_v3.py` `user_edge_count` musing was the v3 gesture at this.)
- [x] ~~**Extend the hypothesis schema generator to emit star-bridge cycle shapes.**~~
      DONE 2026-07-16. Added a dedicated star-bridge generator + `StarBridgeParityMachine`
      to `tests/test_hypothesis.py` (emits `parent:[T,T:*]` / `A:[user,T:*#A,T#B]` /
      `B:[user] or A from parent`), a deterministic class pin, and the OUT-bridge analog
      of reg10 (`test_reg11...` in `tests/test_lookup_oracle.py`) — the object-wildcard
      mirror; verified only the single-hop out-bridge self-cycle is realizable (the
      multi-hop generalization is unreachable). See the dated `docs/spec-deviations.md`
      entry. The generator ALSO surfaced two new latent OWC divergences — see the
      Standing/latent section below.

### Someday / out of scope (low priority — revisit only on a concrete need)

- [ ] **Lift the two scope rejections** — object wildcards on derived relations,
      and wildcard usersets over derived relations, currently raise
      `UnsupportedByGraphIndex` (loud compile-error hooks); the documented fix is a
      symmetric subject-keyed residue (symbolic composition through residues), and
      it is the sole item not yet modeled in Lean (`formal/FINAL_REVIEW.md` §4 last
      item). **Low priority — the OpenFGA DSL does not support these either**
      (verified against the OpenFGA Configuration Language docs, 2026-07-16):
      OpenFGA rejects `<type>:*` in a tuple's object field and rejects wildcard
      usersets (`[group:*#member]`) with a validation error. The one plausible
      pattern (broad grant + per-object boolean exception) is already expressible
      via a supported TTU/hierarchy. So this is a deliberate boundary, not a gap —
      revisit only if a concrete, OpenFGA-shaped need appears.
- [ ] **A real service wrapper** — deliberately skipped; the store is a plain
      callable API.
- [ ] **Tuple-log compaction** — only if the log ever outgrows "humans wrote this" scale.

### Standing / latent (non-blocking — no action needed unless a motivating case appears)

- [x] ~~**Set-engine flow graph omits bridge edges**~~ — RESOLVED 2026-07-16 (was a
      real, constructible divergence, not merely latent). Fixed; see the Current
      status note above and `docs/spec-deviations.md`.
- [x] ~~**Two OWC-on-self-referential-relation divergences (F1/F2, found 2026-07-16 by the
      new star-bridge fuzzer).**~~ — RESOLVED 2026-07-17 by a **compile-time scope
      rejection** (the third decision-15 entry): a *doubly-bridged* shape — a literal
      `T:*#p` wildcard-userset restriction that is also an object-wildcard shape — now
      raises `DoublyBridgedShapeError` on **both** backends at construction (the set engine
      re-raises it rather than degrading). Also surfaced en route: both states **detonate**
      (after the wildcard write, innocent later concrete writes of the shape are permanently
      graph-rejected — a 3rd divergence), and *all→any is NOT read semantics* (oracle-pinned
      via an acyclic cross-type probe, so no read-path fix was warranted). Belt-and-braces
      set-engine ghost-hop safeguard added (never fires post-rejection). Pinned by the
      `reg12` block in `tests/test_lookup_oracle.py`; see the dated `docs/spec-deviations.md`
      entry. (Note: the criterion is the *literal-restriction* ∩ object-wildcard set, not
      the coarse `bridged_in ∩ bridged_out`, which over-rejects the legal reg11 class.)
- [x] ~~**THREE OPEN/latent divergences filed 2026-07-17 by the hardened generators**~~ —
      **RESOLVED 2026-07-17 (+ a 4th found en route).** All three were root-caused and fixed,
      their strict xfails flipped to plain regression pins, and the generator exclusions
      reverted (`allow_usersets` default ON, `ttu_in_boolean` removed). See the Current-status
      top bullet and `docs/spec-deviations.md` 2026-07-17 ("the three OPEN 2026-07-17
      divergences CLOSED"). Summary: #2/#3 (the graph *completeness* gaps —
      `test_graph_from_chain_userset_through_boolean_ttu_arm`,
      `test_graph_userset_subject_through_derived_wildcard_gap`) + a new 4th
      (`test_graph_userset_member_through_granted_userset_over_derived`) fixed by **Fix A**
      (the `processor._leaf_concretes` `upos` lift for `derived-computed`/`derived-userset`
      leaves + `bulk_backfill` mirror); #1 (the answer-benign implicit-flag canonical drift,
      `test_pderived_userset_self_ref_cascade_replay_drift`) fixed by **Fix B** (the
      state-functional `implicit` flag — promote step 2d + demote-on-release, I6 extended;
      hysteresis pin `test_pderived_recording_promote_demote_hysteresis`).
- [ ] **Other documented latent/theoretical notes** — a handful of
      "documented, no corpus exercises it, not urgent" corners (e.g. a from-chain
      TARGET theoretical note; tupleset-of-derived latent gap). The full inventory
      is the divergence log: [`docs/spec-deviations.md`](docs/spec-deviations.md).
      Do not chase these speculatively; act only if a real schema/corpus surfaces one.

_(Declined / dead-end items — do NOT re-chase — are listed in
[`docs/perf-next-round.md`](docs/perf-next-round.md) "Minor notes" and the fenced
P12c list.)_

---

## Where things live

| doc | what it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | durable rules: env, the gate, layout/mental model, testing conventions, invariants |
| [`docs/architecture/overview.md`](docs/architecture/overview.md) | **architecture index** — module map + pointers to every deeper doc |
| [`docs/gate-runbook.md`](docs/gate-runbook.md) | how to run the full gate cap-safe (pytest split + phased `verify.sh` + fuzz) |
| [`docs/perf-next-round.md`](docs/perf-next-round.md) | perf standing guardrails (arc closed; fence + dead-ends + hygiene) |
| [`docs/spec-deviations.md`](docs/spec-deviations.md) | dated log of where the code diverges from the specs, and the latent-gap inventory |
| [`docs/specs/`](docs/specs/) | the full original design specs (cited by code comments as "spec §N") |
| [`formal/HANDOFF.md`](formal/HANDOFF.md) | entry point for the Lean formal layer (read before touching `formal/`) |
| [`formal/CORRESPONDENCE.md`](formal/CORRESPONDENCE.md) | the model↔Python code map (§7/§8 record any algorithm drift) |
| [`benchmarks/results/PERF_ANALYSIS.md`](benchmarks/results/PERF_ANALYSIS.md) | measured perf numbers per landed item ("Applied") |
| [`docs/history/`](docs/history/) | retired round records (perf rounds 3–5) — provenance, not living docs |

---

## Working rhythm

1. **Read this file + `CLAUDE.md` first.** Pull deeper docs on demand from the map above.
2. **Run the gate before pushing** — never push red or unverified. Cap-safe recipe
   in [`docs/gate-runbook.md`](docs/gate-runbook.md): `pytest tests/` (split) green,
   then `verify.sh lean` → `conf-heavy` → `conf-rest` all `PASSED`; an algorithm
   change also runs the multi-seed fuzz sweep. Commit and push **only when asked**.
3. **Keep the honesty norms** — report gate output as-is; if something is skipped
   or fails, say so. Never edit a golden/oracle/snapshot just to make a change pass.
4. **Keep this board current** — add active tasks when you start them, clear them
   when the work lands (the git log + `docs/history/` are the durable trail).
5. **Perf or algorithm work?** A behavior-preserving micro-opt needs no Lean change;
   an optimization that changes a *modeled* algorithm must update the matching Lean
   def and re-run `verify.sh`, or log the gap in `formal/CORRESPONDENCE.md §7`
   (see `CLAUDE.md` "Perf work & the Lean model").
