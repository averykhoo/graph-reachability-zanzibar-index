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

## Current status — 2026-07-16

- **Everything is complete and green.** Both evaluation backends (set engine +
  graph index), the composition layer, and the Lean formal layer all pass their
  gates. Lean is sorry-free and axiom-clean (412/412). No known correctness bug.
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
_None in flight._ The repo is in a clean, fully-gated state awaiting the next
direction. **When you start a task, add it here** (with owner/date if useful) and
move it to the history/changelog trail when done.

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
- [ ] **Two OWC-on-self-referential-relation divergences (F1/F2, found 2026-07-16 by the
      new star-bridge fuzzer).** Both need an object wildcard on the relation that also
      carries a `T:*#A` wildcard-userset restriction (`(T,A) ∈ object_wildcard_shapes`).
      **F1** (graph *incomplete*): `check` returns graph `False` where set + oracle say
      `True`, routed through a double-wildcard `T:* parent T:*` parent. **F2** (graph
      *over-permissive*): `T:*#A A T:*` accepted by graph, rejected by set (the reg9
      same-shape self-reference with a wildcard object). Minimal repros + rationale in the
      dated `docs/spec-deviations.md` entry. Exotic (OpenFGA has no wildcard usersets);
      do NOT chase speculatively — but **F1 is a completeness gap**, so triage it first if
      either is ever prioritized.
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
