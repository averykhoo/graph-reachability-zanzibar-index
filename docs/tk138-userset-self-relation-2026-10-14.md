# `TK138` — a userset related to itself (`doc:1#viewer` @ `viewer` @ `doc:1`): measured plan

**ACTIVE-PLAN, opened 2026-10-14 — the body is provenance, not a living status.** Scouting
for `TK138`, produced by the `scout-TK138` workflow agent on 2026-10-14 against HEAD
`0b09687` (+ an unrelated uncommitted `tasks/TK119-*.md` edit). Live state is the task row
(`python scripts/task.py show TK138`) and `python scripts/gate_status.py`, never this file.
Corrections append **dated at the top**, never edited into the body. Freeze it when `TK138`
closes. This doc DOES NOT DECIDE: a decision stage follows (the user's 2026-10-13d word on
the row is "verify against a real OpenFGA server, then ADOPT"; § 1 is that verification).

**Provenance labels.** first-hand PROBE = a script this agent ran (paths under
`.scratch/now-next/probes/scout-TK138/`, gitignored, so every load-bearing output is
transcribed literally below). first-hand READ = this agent read the source line.
REASONED = inference, not run. UNVERIFIED = from memory / not checked. Line numbers are
dated 2026-10-14 and rot; the `file::symbol` is the durable pointer.

## Decision recommendation 2026-10-14

By the `decide-TK138` workflow agent (the executive-decision subagent CLAUDE.md "Who
decides" allows), 2026-10-14, against HEAD `0b09687`. Inputs: this doc in full (scout and
challenge sections) and `task.py show TK138`. No new probes; everything below is REASONED
from the first-hand PROBE / READ transcripts above. It is a recommendation: the coordinator
records the decision on the row (`task.py comment TK138 --session <key>`).

**Decision: option A, staged as two landings — landing 1 now (S: pin the gap, document
it), landing 2 later as ONE atomic change set (L Python + XL Lean) sequenced behind
`TK123`, `TK119` and `TK132`. Not B-and-stop, not C.**

Reasoning:
1. The user's 2026-10-13d word was "verify, then ADOPT"; § 1 verified it, so the goal
   stands. What verification changed is the COST: the rule propagates (§ 1.3 item 2),
   crosses objects (C1), flips ALLOW to DENY (`vx`, § 2.1) and reaches lookups (D3a is
   forced by the lookup gate, § 7.1 item 3). The row's `M` assumed a root identity
   short-circuit; the measured shape is L+XL and NOT deferrable (§ 7.1 item 2: the
   conformance suites compare executable Lean, so a `CORRESPONDENCE.md` § 7 gap entry is
   not an interim).
2. Equivalence beats parity. A landing that moves one corner, or the Python without the
   Lean spec / set-engine / graph models, is a divergence the gate refuses (§ 8: red from
   step 3 to step 6). The only honest interim moves NO corner.
3. Today's semantics is an undocumented, security-relevant gap on the PyPI page (`vx` is
   ALLOWED here and DENIED by OpenFGA). The cheap, legible half has no reason to wait on
   the expensive half, and pinning the gap mechanically is exactly the 2026-09-22c goal
   (honest, legible assurance; not wider).
4. Three concurrent Lean edits to one model (`TK119`, `TK132`, this) is the merge risk § 8
   names, and D3a's `LookupResult` channel must be decided once, inside `TK123`'s API pass,
   which is this session.

**Landing 1 (this session, S; no semantic change, no Lean, no golden):**
- `tests/test_tk138_userset_self_relation.py`: a `ParityEngine` over models A-as-accepted,
  B and C, carrying a LITERAL table of OpenFGA v1.22.0 answers transcribed from § 1 and C1
  (never derived from the oracle). It asserts today's unanimous repo answer for every row
  AND the exact set of rows where repo ≠ OpenFGA (§ 2.1 plus C1's four `group:*#admin`
  rows). A positive divergence pin, never an xfail: the moment any corner moves it goes
  red and is edited deliberately. It also pins what must NOT move: the TTU from-chain rows
  (True), concrete-user and `user:*` answers, the self-tuple refusal. Sabotage: run it
  under the § 7.1 oracle instrument (the `sat` disjunct in the oracle only); must go red.
- `docs/spec-deviations.md`: a dated entry stating the rule (§ 3.1), the `vx` direction,
  that the TTU from-chain row agrees by accident of representation (§ 2.1), the C3
  undeclared-relation asymmetry, and — amending the 2026-07-13 entry per C6 — "both refuse
  the exact self tuple", not "agrees". One `PYPI_README.md` "differences from OpenFGA" line
  naming the `vx` direction, written once together with `TK137`'s text (§ 8).
- Sub-decisions recorded on the row: **D1** star subjects excluded (answers unchanged);
  **D2** the spec IS the disjunct form, the § 3.1 reduction is a proof device only;
  **D3 = D3a** (lookups list implicit usersets); **D4** keep the `ttu_leaf` from-chain
  disjunct unchanged (no answer change, no `ttuLeaf` churn; C3).
- Resize the row to L (Python) + XL (Lean). Open a child row for landing 2 at `NEXT` with
  `deps: [TK123, TK119, TK132]`. In `TK123`, settle the lookup channel now: `LookupResult`
  carries `(type, name, predicate)` keys, not interned ids — an internal surrogate id is a
  first-time-user surprise regardless of TK138, and D3a needs the channel.

**Landing 2 (one uncommitted change set; commit only on green):** § 5 steps 2–9 with
these refinements. Derived graph side: build **C5** first (read-time seed-aware
`plan.check_fn`), falling back to C1 (a)–(d) only if `WildcardIndex` cannot reach
`check_fn` without importing the processor — C5 leaves canonical state,
`test_conformance_state` and the Lean reconcile model untouched (perf is deprioritized).
Tests per C2: model C, the variant without `[group#admin]`, a model-C-shaped corpus schema,
the widened `ParityEngine._grid` / `_subject_candidates`, the own-object-only sabotage.
`CHANGELOG` entry plus a MINOR version bump (an ALLOW-to-DENY flip is not a patch).
Hypothesis sweep with `--hypothesis-seed=N`. `headline_definitions.txt`,
`headline_statements.txt` and `claim_rot --generate` regenerated deliberately, after
re-reading the cited rows. Re-check C7 (`sem_fuel_stable`, model C's `group:3`) in Lean.

**Do NOT:** move one corner alone, or the Python without all three Lean models; xfail
anything; delete the TTU from-chain disjunct (B3) or refuse the query shape (B2);
materialize self edges in the closure (§ 3.4); intern on read; narrow the Lean fragment to
exclude the shape; edit a golden, snapshot or oracle result to pass; start the Lean graph
edits while `TK119` / `TK132` are open; close `TK138` on landing 1 — the user's ADOPT stands
until landing 2 ships, and landing 1's pin exists to make that debt visible, not to settle it.

## Corrections (dated, newest first)

### Corrections 2026-10-14 (challenge)

By the `challenge-TK138` workflow agent (skeptic pass), 2026-10-14. Probes live under
`.scratch/now-next/probes/challenge-TK138/` (gitignored); every load-bearing output is
transcribed literally here. **Verdict: NEEDS-CHANGES.** The root cause, the OpenFGA rule
and the oracle/set-engine disjunct stand, including propagation across objects. The
derived-graph step is under-specified (C1), its tests can pass without the missing part
(C2), and one claim is false (C3).

**Re-verified (no change).**
- first-hand READ: the § 1.1, § 1.2 and § 2 transcripts are byte-identical to
  `scout-TK138/openfga_probe.out`, `openfga_probe2.out` and `repo_probe.out` (checked with
  `diff`; only the trailing `probe rc=0` line differs). The § 7.1 tally
  `194 failed, 202 passed in 691.87s` is the last line of `oracle_self_tests2.log`, which
  contains 0 `TypeError` lines.
- first-hand READ: `formal/headline_definitions.txt` pins `step`, `semAux`, `sem`, `evalE`,
  `directLeaf` and `ttuLeaf`. `formal/lean/ZanzibarProofs/GraphIndex/Correct.lean::graph_correct_empty`
  states `GraphModel.check (emptyState S) q = sem S [] q`, so it breaks once `sem` is
  reflexive, as § 3.5 says. `formal/conformance/test_conformance_graph.py` compares the Lean
  graph model with `sem`, and the Python graph with the Lean graph model, so the Lean graph
  model is on the critical path (§ 7.1 item 2 holds). The `TK123` row lists "lookup
  results" and "lookup ids", so the D3a collision is real.

**C1 (MATERIAL; first-hand PROBE plus READ). The derived-graph plan misses propagation
ACROSS objects.** This affects § 3.4 bullet 2, § 4 "A3 graph, derived" and § 5 step 6.
- **Model C** (`openfga_probe3.py`, JSON form sent):
  `group: admin: [user]; member: [user] or admin` and
  `doc: viewer: [user, group#member]; banned: [user, group#admin]; nb: viewer but not banned`.
  Tuples: `group:1#member viewer doc:1`, `group:1#member viewer doc:2`,
  `group:1#admin banned doc:2`, `user:alice admin group:1`, `group:3#member viewer doc:1`.
- **OpenFGA v1.22.0** (same build `a38d5d0`, throwaway container, `wsl docker ps` empty
  afterwards), literal `openfga_probe3.out`:

  ```
  CHECK  group:1#admin    viewer  doc:1  -> True
  CHECK  group:1#admin    nb      doc:1  -> True
  CHECK  group:3#admin    viewer  doc:1  -> True
  CHECK  group:3#admin    nb      doc:1  -> True
  CHECK  group:1#member   nb      doc:1  -> True
  CHECK  group:1#admin    nb      doc:2  -> False
  CHECK  group:1#member   nb      doc:2  -> True
  CHECK  user:alice       nb      doc:2  -> False
  CHECK  user:alice       nb      doc:1  -> True
  LISTOBJ user=group:1#admin doc#viewer -> ['doc:1', 'doc:2']
  LISTOBJ user=group:1#admin doc#nb -> ['doc:1']
  LISTOBJ user=group:3#admin doc#nb -> ['doc:1']
  LISTUSR doc:1#nb filter=group#admin -> ['group:1#admin', 'group:3#admin']
  LISTUSR doc:2#nb filter=group#member -> ['group:1#member']
  ```
- **This repo** (`repo_probe3.py`, same store, each corner asked separately). Literal
  `repo_probe3.out`, columns: openfga, patched oracle (the § 3.2 disjunct), today's oracle,
  graph, set:py, set:roaring:

  ```
  ('admin', 'group', '1', 'viewer', 'doc', '1') True    True           False  False  False  False
  ('admin', 'group', '1', 'nb', 'doc', '1')     True    True           False  False  False  False
  ('admin', 'group', '3', 'viewer', 'doc', '1') True    True           False  False  False  False
  ('admin', 'group', '3', 'nb', 'doc', '1')     True    True           False  False  False  False
  ('member', 'group', '1', 'nb', 'doc', '1')    True    True           True   True   True   True
  ('admin', 'group', '1', 'nb', 'doc', '2')     False   False          False  False  False  False
  ('member', 'group', '1', 'nb', 'doc', '2')    True    True           True   True   True   True
  ('...', 'user', 'alice', 'nb', 'doc', '2')    False   False          False  False  False  False
  ('...', 'user', 'alice', 'nb', 'doc', '1')    True    True           True   True   True   True
  ```

  The patched oracle matches OpenFGA on all 9 rows, so the § 3.2 disjunct is right.
- **Why the plan misses it.** The planned reconcile step enumerates "the object's own
  userset keys `(r', T, o)`". For `doc:1#nb` those are `doc:1#*` only; `group:1#admin` and
  `group:3#admin` are never among them, and `group:3#admin` has no node anywhere.
  - first-hand READ: `src/zanzibar/graphindex/processor.py::DeltaProcessor._reconcile`
    builds `upos` (step 2c) only from the audit set (2b): incoming concretes, leaf
    concretes, step-2 candidates and old `upos`.
  - first-hand READ: `src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_derived`
    answers a userset subject from `upos`, `stars` and `neg` only.
  - REASONED from those two reads: `check(group:1#admin, nb, doc:1)` would stay False, and
    parity goes red.
- **The seed node's answer cannot be reused.** `group:1#member` ∈ `doc:2#nb` is True but
  `group:1#admin` ∈ `doc:2#nb` is False (rows 7 and 6). The propagated subject has to be
  evaluated in its own right.
- **Fix (REASONED):**
  - (a) **Enumerate keys by INVERSE seed expansion.** For every userset-shaped concrete
    `(T, o, r')` that reaches any leaf (both polarities), and every one in a referenced
    derived leaf's `upos`/`neg`, add the key `(r_s, T, o)` for each `r_s` with
    `r' ∈ seeds(T, r_s)`. That set is the computed-SUBSET table, the transpose of § 3.4's
    seed table. Add the object's own keys as well. Intern only when the outcome must be
    recorded, as the 2a recipe does.
  - (b) **Use the seed probes inside `_EvalContext` too.** Its untainted leaf reads and
    `ttu_check` must probe from the seed nodes, exactly as `_check_internal` will. A root
    identity alone is not enough: without the probes, `check_fn` answers False for
    `group:1#admin` at the `viewer` leaf.
  - (c) **Same key set in the invariants.** `src/zanzibar/graphindex/invariants.py` (I9 and
    the delta-scoped verifier) must recompute the same expanded key set.
  - (d) **Narrow the trigger claim.** § 3.4's "self keys depend only on the object node, so
    the reconcile trigger set is unchanged" holds as written only for own-object keys. For
    cross-object keys the trigger is still a leaf change at the object: a new
    `group:1#member viewer doc:1` already reconciles `doc:1#nb`, and the subset table is
    static because schemas are. So the trigger set plausibly stays unchanged — REASONED,
    re-check when building.
- **Sizing.** A3-derived stays L, but it is not an X4a clone. Interned subject nodes grow
  with |userset concretes| × |subsets|, which moves canonical state
  (`formal/conformance/test_conformance_state.py`, the Lean reconcile model in
  `GraphIndex/ReconcileStars.lean`) — REASONED.

**C2 (a test that would fail by passing; first-hand READ plus REASONED).**
- **The dedicated test does not cover the cross-object shape.** Models A and B (§ 5 step 2)
  contain no cross-object computed-subset subject, so a graph build that enumerates only
  own-object keys passes it.
- **Two broad grids do not cover it either.**
  - first-hand READ: `tests/parity.py::ParityEngine._grid` and
    `tests/test_lookup_oracle.py::_subject_candidates` build userset subjects only from
    Direct-restriction shapes (plus TTU from-chain shapes, in the lookup gate).
  - So `group:1#admin` is queried only when some relation says `[group#admin]`. Model C
    has one (`banned`); drop it and the subject leaves both grids, although OpenFGA still
    answers `check(group:1#admin, viewer, doc:1)` True (REASONED from row 1; the dropped
    variant was not probed).
- **The conformance grid is broader, but helps only if a corpus has the shape.**
  first-hand READ: `formal/conformance/grid.py::grid` emits every declared relation on its
  own type as a userset subject, so the conformance phases catch the gap only when some
  corpus schema has the cross-object shape.
- **Fix:**
  - Put model C, with `openfga_probe3.out`'s literal answers, into
    `tests/test_tk138_userset_self_relation.py`.
  - Add a variant WITHOUT `[group#admin]` anywhere, plus a model-C-shaped schema in
    `formal/conformance/corpus.py`.
  - Widen the userset shapes in `ParityEngine._grid` and `_subject_candidates`: for each
    userset shape `(T, p)`, also add `(T, r)` for every declared relation `r` of `T`. This
    adds candidates and relaxes no property.
  - New sabotage row: restrict the processor's enumeration to own-object keys. The model C
    test must go red.

**C3 (first-hand PROBE). § 3.2 / § 3.3's claim that the `ttu_leaf` from-chain disjunct
"becomes redundant" is false.**
- **Where it fails.** A TTU target may be undeclared on one of the tupleset's types. That
  is legal, because ASK-1 requires the target only on at least one of them
  (`src/zanzibar/schema/parser.py::_validate_ast_consistency` docstring, first-hand READ).
- **Probe** (`repo_probe4.py`). Schema: `parent: [folder, team]`, `x: viewer from parent`,
  `folder: viewer: [user]`, and `team` declares no relations. Tuples: `team:1 parent doc:1`,
  `folder:1 parent doc:1`. Literal `repo_probe4.out`:

  ```
  ('viewer', 'team', '1', 'x', 'doc', '1') oracle True patched True patched-minus-ttu-disjunct False {'graph': True, 'set:py': True, 'set:roaring': True}
  ('viewer', 'folder', '1', 'x', 'doc', '1') oracle True patched True patched-minus-ttu-disjunct True {'graph': True, 'set:py': True, 'set:roaring': True}
  ```

  The `folder` row is the instrument control: the method with the disjunct removed still
  answers True where the target is declared.
- **OpenFGA** (`openfga_probe5.out`): `CHECK team:1#viewer x doc:1 -> ERR 400
  validation_error: invalid relation: relation 'team#viewer' not found`.
- **Why it matters.** All four corners answer True today, under the lenient-read contract.
  The new `sat` disjunct is declared-only, so it answers False here. Deleting the from-chain
  disjunct in the oracle, the set engine, the Lean `ttuLeaf` and processor step 2a would
  therefore flip a live answer.
- **Decision needed.** Add sub-decision **D4: userset subjects whose relation is
  undeclared**. Recommendation (REASONED): keep the `ttu_leaf` disjunct unchanged, so there
  is no answer change and no `ttuLeaf` churn, and record the asymmetry in the
  spec-deviations entry.

**C4 (first-hand READ). Risk 9 / § 7.2's snapshot question is resolved.**
`tests/test_compile_snapshot.py::_canonical_ruleset` serializes `rules_and_filters` and only
two `SchemaInfo` fields (`subject_wildcard_shapes`, `object_wildcard_shapes`). A new
`SchemaInfo` seed table does NOT move `tests/snapshots/`. A new Rule or Filter emitted into
`rules_and_filters` would.

**C5 (alternative for the decision stage; REASONED, not built). Answer userset subjects on
DERIVED relations at read time.**
- **The idea.** Evaluate `plan.check_fn` with the seed-aware context at read time, instead
  of extending the residue `upos`/`neg` enumeration (C1 a–c).
- **Gains.** The persisted residue state and its canonical form stay as they are, and so do
  `test_conformance_state` and the Lean reconcile model. No nodes are interned for keys
  such as `group:3#admin`.
- **Costs.** Read latency (perf is deprioritized under the 2026-09-22c goal). Lookups still
  need the enumeration (D3a), now done at lookup time.
- **Unchanged either way.** The Lean `graphModeAnswers` still changes.
- UNVERIFIED: whether `WildcardIndex` can reach `plan.check_fn` at read time without
  importing the processor.

**C6 (REASONED, minor). The § 2.1 write row "agrees (refused)" agrees in outcome only.**
- **The two rules differ.** OpenFGA refuses only the exact self tuple, as "implicit"
  (`IsSelfDefining`). This repo refuses it as a cycle.
- **Where they part.** A different same-object cycle is refused here, for example
  `doc:1#can_view viewer doc:1` with `can_view: viewer` and `viewer: [user, doc#can_view]`.
  It is UNVERIFIED (not probed) whether OpenFGA accepts it.
- **Consequence.** This is outside TK138's scope, but the spec-deviations entry should say
  "both refuse the exact self tuple", not "agrees".

**C7 (UNVERIFIED). Lean fuel.** The disjunct sits in `step` and needs no extra depth, so
`fuelBound` plausibly still suffices (REASONED). The case to check inside
`Spec/WellDef.lean::sem_fuel_stable` is a subject whose object is reached only through a
stored tuple (model C's `group:3`).

## 0. Summary

- **OpenFGA's rule, measured on a live server (v1.22.0):** a userset subject `o#r` is a
  member of node `(o, r)` **unconditionally, at every resolve node** — regardless of the
  relation's type restrictions, and OUTSIDE its rewrite (a `but not` cannot remove it, an
  `and` cannot block it). Because it fires at inner nodes too, it **propagates** through
  computed usersets, TTU and boolean arms — and so it can FLIP an existing answer here
  from ALLOW to DENY (§ 1.3, `vx`). Formally:
  `Members(o, r) = {o#r} ∪ Eval(rewrite(r), Members)`. Expand does NOT show it; Check,
  ListObjects and ListUsers all do.
- **This repo today:** all four corners (oracle, set engine ×2 SetOps, graph index) agree
  and are NON-reflexive, **except** that the TTU leaf already has the self disjunct for the
  from-chain userset (`folder:1#viewer` ∈ `doc:1#fview` when `doc:1 parent folder:1`), in
  the oracle, the Lean `sem`, the set engine and the graph (as a materialized node). So
  today's semantics is partially reflexive by accident of representation, not by design.
- **Only userset-subject queries can change.** Concrete-user and `user:*` answers are
  unaffected (the rule adds only the subject `o#r` itself, never its members) — REASONED,
  and consistent with every probe below.
- **Cost shape (§ 4, § 7.1).** Oracle and set-engine `check` take one disjunct each (S).
  The graph index is L (static seed probes on the untainted side, plus an X4a-style
  reconcile step for derived relations). Two measured facts make option A bigger than
  "one disjunct per backend". First, the Lean corner cannot be deferred: the conformance
  suites compare the EXECUTABLE Lean `sem` and graph model against the Python, so the
  Lean definitions and their proofs change in the same landing, and the graph proofs
  are XL. Second, the lookup gate pins lookups exactly over self-shaped candidates, so
  lookups must list implicit usersets (D3a). That needs an API channel for keys that
  are not interned, which collides with `TK123`.
  Option B (document) is S. Option C (leave) leaves a security-relevant gap
  undocumented: the `vx` shape is ALLOWED here and DENIED by OpenFGA.

## 1. OpenFGA's exact rule — first-hand PROBE against a live server

Setup (first-hand PROBE, 2026-10-14): `openfga/openfga:latest` pulled into WSL2 docker,
`OpenFGA version v1.22.0 build from a38d5d0f65a964b6030e0b1afd2a831f62309159 on
2026-10-06T19:14:15Z`, memory storage, run by
`.scratch/now-next/probes/scout-TK138/run_openfga.sh` (container started and removed in one
`wsl` session; `wsl docker ps` empty afterwards). Probes: `openfga_probe.py` (model A) and
`openfga_probe2.py` (model B), JSON models over the HTTP API. Source claims it rests on:
`docs/openfga-claims-audit-2026-10-13.md` § 2 fact 5 (`pkg/tuple/tuple.go::IsSelfDefining`;
the API docs' "because they are implicit") — now confirmed behaviourally.

### 1.1 Model A (DSL-equivalent; the probe sends the JSON form)

```
type user
type folder
  relations
    define viewer: [user, folder#viewer]
    define plain: [user]
type doc
  relations
    define viewer: [user, doc#viewer]
    define banned: [user]
    define editor: [user]
    define plain: [user]
    define parent: [folder]
    define viewer_bn: [user, doc#viewer_bn] but not banned
    define banned2: [user, doc#viewer_bn3]
    define viewer_bn3: [user, doc#viewer_bn3] but not banned2
    define can_view: viewer
    define fview: viewer from parent
    define fplain: plain from parent
    define vi: [user, doc#vi] and editor
    define vu: [user] or editor
    define nb: viewer but not banned
```

Literal output (`openfga_probe.out`):

```
== empty store ==
CHECK  doc:1#viewer           viewer     doc:1     -> True
CHECK  doc:1#viewer           viewer     doc:2     -> False
CHECK  doc:1#editor           viewer     doc:1     -> False
CHECK  doc:1#plain            plain      doc:1     -> True
CHECK  doc:1#banned           banned     doc:1     -> True
CHECK  doc:1#viewer_bn        viewer_bn  doc:1     -> True
CHECK  doc:1#can_view         can_view   doc:1     -> True
CHECK  doc:1#viewer           can_view   doc:1     -> True
CHECK  doc:1#fview            fview      doc:1     -> True
CHECK  doc:1#vi               vi         doc:1     -> True
CHECK  doc:1#vu               vu         doc:1     -> True
CHECK  doc:1#nb               nb         doc:1     -> True
CHECK  doc:1#viewer           nb         doc:1     -> True
CHECK  folder:1#viewer        viewer     folder:1  -> True
CHECK  folder:1#viewer        fview      doc:1     -> False
CHECK  doc:1#nosuchrel        nosuchrel  doc:1     -> ERR validation_error: invalid relation: relation 'doc#nosuchrel' not found
LISTOBJ user=doc:1#viewer doc#viewer -> ['doc:1']
LISTOBJ user=doc:1#viewer doc#can_view -> ['doc:1']
LISTUSR doc:1#viewer filter=doc#viewer -> [{"userset": {"type": "doc", "id": "1", "relation": "viewer"}}]
LISTUSR doc:1#can_view filter=doc#viewer -> [{"userset": {"type": "doc", "id": "1", "relation": "viewer"}}]
LISTUSR doc:1#viewer_bn filter=doc#viewer_bn -> [{"userset": {"type": "doc", "id": "1", "relation": "viewer_bn"}}]
LISTUSR doc:1#vi filter=doc#vi -> [{"userset": {"type": "doc", "id": "1", "relation": "vi"}}]
LISTUSR doc:1#viewer filter=user -> []
EXPAND doc:1#viewer -> 200 {"root": {"name": "doc:1#viewer", "leaf": {"users": {"users": []}}}}
== writes ==
WRITE  doc:1#viewer viewer doc:1 -> 400 Invalid tuple 'doc:1#viewer@doc:1#viewer'. Reason: cannot write a tuple that is implicit
WRITE  doc:1#viewer_bn3 banned2 doc:1 -> 200 ok
WRITE  doc:1#viewer viewer doc:2 -> 200 ok
WRITE  user:alice viewer doc:1 -> 200 ok
WRITE  user:bob banned doc:1 -> 200 ok
WRITE  user:bob viewer doc:1 -> 200 ok
WRITE  folder:1 parent doc:1 -> 200 ok
WRITE  user:carol viewer folder:1 -> 200 ok
== after writes ==
CHECK  doc:1#viewer           viewer     doc:1     -> True
CHECK  doc:1#viewer           viewer     doc:2     -> True
CHECK  doc:1#viewer_bn3       viewer_bn3 doc:1     -> True
CHECK  doc:1#viewer_bn        viewer_bn  doc:1     -> True
CHECK  folder:1#viewer        fview      doc:1     -> True
CHECK  folder:1#plain         fplain     doc:1     -> True
CHECK  folder:2#viewer        fview      doc:1     -> False
CHECK  user:alice             viewer     doc:2     -> True
CHECK  user:bob               viewer_bn  doc:1     -> False
CHECK  user:bob               nb         doc:1     -> False
LISTOBJ user=doc:1#viewer doc#viewer -> ['doc:1', 'doc:2']
LISTOBJ user=doc:1#viewer doc#can_view -> ['doc:1', 'doc:2']
LISTOBJ user=doc:1#viewer_bn3 doc#viewer_bn3 -> ['doc:1']
LISTOBJ user=folder:1#viewer doc#fview -> ['doc:1']
LISTOBJ user=folder:1#viewer folder#viewer -> ['folder:1']
LISTUSR doc:1#viewer filter=doc#viewer -> [{"userset": {"type": "doc", "id": "1", "relation": "viewer"}}]
LISTUSR doc:2#viewer filter=doc#viewer -> [{"userset": {"type": "doc", "id": "2", "relation": "viewer"}}, {"userset": {"type": "doc", "id": "1", "relation": "viewer"}}]
LISTUSR doc:1#viewer_bn3 filter=doc#viewer_bn3 -> [{"userset": {"type": "doc", "id": "1", "relation": "viewer_bn3"}}]
LISTUSR doc:1#fview filter=folder#viewer -> [{"userset": {"type": "folder", "id": "1", "relation": "viewer"}}]
LISTUSR doc:2#viewer filter=user -> [{"object": {"type": "user", "id": "alice"}}, {"object": {"type": "user", "id": "bob"}}]
EXPAND doc:1#viewer -> 200 {"root": {"name": "doc:1#viewer", "leaf": {"users": {"users": ["user:alice", "user:bob"]}}}}
EXPAND doc:2#viewer -> 200 {"root": {"name": "doc:2#viewer", "leaf": {"users": {"users": ["doc:1#viewer"]}}}}
```

### 1.2 Model B — where the self rule flips a boolean answer

```
type user
type doc
  relations
    define banned: [user]
    define editor: [user]
    define plain: [user]
    define viewer: [user, doc#viewer]
    define vx: [user, doc#banned] but not banned
    define vy: [user, doc#editor] and editor
    define nb: viewer but not banned
    define chain: [user, doc#viewer]
    define cv: plain
```

Literal output (`openfga_probe2.out`):

```
== empty store: lookup on relations lacking the self type ==
CHECK  doc:1#plain            plain      doc:1     -> True
LISTOBJ user=doc:1#plain doc#plain -> ['doc:1']
LISTUSR doc:1#plain filter=doc#plain -> [{'userset': {'type': 'doc', 'id': '1', 'relation': 'plain'}}]
CHECK  doc:1#plain            cv         doc:1     -> True
LISTOBJ user=doc:1#plain doc#cv -> ['doc:1']
LISTUSR doc:1#cv filter=doc#plain -> [{'userset': {'type': 'doc', 'id': '1', 'relation': 'plain'}}]
CHECK  doc:1#viewer           nb         doc:1     -> True
LISTOBJ user=doc:1#viewer doc#nb -> ['doc:1']
LISTUSR doc:1#nb filter=doc#viewer -> [{'userset': {'type': 'doc', 'id': '1', 'relation': 'viewer'}}]
== writes ==
WRITE  doc:1#banned vx doc:1 -> 200 ok
WRITE  doc:1#editor vy doc:1 -> 200 ok
WRITE  doc:1#viewer chain doc:2 -> 200 ok
WRITE  doc:2#chain viewer doc:3 -> 400 Invalid tuple 'doc:3#viewer@doc:2#chain'. Reason: 'doc#chain' is not an allowed type restriction for 'doc#viewer'
== self flips a boolean answer ==
CHECK  doc:1#banned           vx         doc:1     -> False
CHECK  doc:1#banned           vx         doc:2     -> False
CHECK  doc:1#editor           vy         doc:1     -> True
LISTOBJ user=doc:1#banned doc#vx -> []
LISTUSR doc:1#vx filter=doc#banned -> []
LISTOBJ user=doc:1#editor doc#vy -> ['doc:1']
LISTUSR doc:1#vy filter=doc#editor -> [{'userset': {'type': 'doc', 'id': '1', 'relation': 'editor'}}]
== chain ==
CHECK  doc:1#viewer           chain      doc:2     -> True
CHECK  doc:2#chain            chain      doc:2     -> True
```

### 1.3 What the server output establishes (first-hand PROBE unless labelled)

1. **Unconditional at the node.** `check(o#r, r, o)` is True for every declared `r`, even
   when `r`'s type restrictions do not admit `o#r` (`plain`, `banned`), and even when the
   rewrite would deny it: `viewer_bn3` is True although `doc:1#viewer_bn3` is STORED in the
   subtrahend `banned2`; `vi` is True although its `editor` arm is False.
2. **It recurses.** It fires at every inner resolve node, so it propagates through a
   computed userset (`doc:1#viewer` ∈ `doc:1#can_view`), a boolean base (`doc:1#viewer` ∈
   `doc:1#nb`), and a TTU target (`folder:1#viewer` ∈ `doc:1#fview`, `folder:1#plain` ∈
   `doc:1#fplain` — the latter although `folder#plain` admits no userset).
3. **It flips answers under `but not` / `and`.** `vx`: a stored `doc:1#banned vx doc:1` is
   DENIED because the subtrahend `banned` on `doc:1` contains `doc:1#banned` by the self
   rule. `vy`: a stored `doc:1#editor vy doc:1` is ALLOWED because the `editor` arm is
   satisfied by self.
4. **Lookups follow Check; Expand does not.** ListObjects and ListUsers include the self
   answer (on an empty store too, and on relations whose types do not admit the userset);
   Expand shows only stored members.
5. **Writes.** The self tuple is refused (`400 ... cannot write a tuple that is implicit`).
   A cross-relation same-object tuple (`doc:1#banned vx doc:1`) is accepted.
6. **Undeclared relation** is a `validation_error`, not False (this repo answers False:
   reads are lenient by contract — unchanged by `TK138`).
7. REASONED, consistent with 1–4: OpenFGA evaluates `Members(o, r) = {o#r} ∪
   Eval(rewrite(r), Members)` — the self term sits OUTSIDE the rewrite, at every node.
8. UNVERIFIED (not probed): ListObjects/ListUsers behaviour with the experimental
   `pipeline_list_objects` flag OFF (the image logs it as enabled by default), and
   conditions/contextual tuples.

## 2. This repo today — first-hand PROBE (all four corners)

Probe: `.scratch/now-next/probes/scout-TK138/repo_probe.py` builds `tests/parity.py::_GraphSide`
(paranoia ON), both `tests/parity.py::_SetSide` (`set:py`, `set:roaring`) and
`tests/oracle.py::Oracle`, and asks each corner separately (no unanimity assert; a split
would print `SPLIT {...}`). Schema = model A with three edits forced by THIS repo's
refusals (each is itself a parity gap with OpenFGA, recorded in § 3.6):
`viewer_bn: [user, doc#viewer] but not banned` and `vi: [user, doc#viewer] and editor`
(a derived relation that restricts ITSELF as a userset is a `CyclicDerivedDependency` on
the graph), `banned2`/`viewer_bn3` dropped (`_validate_stratified_negation` refuses the
`viewer_bn3 -> banned2 -> viewer_bn3` negative cycle that OpenFGA accepts), plus model B's
`vx`, `vy`, `chain`, `cv`. Literal output (`repo_probe.out`, every line unanimous):

```
== empty store ==
CHECK  doc:1#viewer           viewer     doc:1     -> False
CHECK  doc:1#viewer           viewer     doc:2     -> False
CHECK  doc:1#editor           viewer     doc:1     -> False
CHECK  doc:1#plain            plain      doc:1     -> False
CHECK  doc:1#banned           banned     doc:1     -> False
CHECK  doc:1#viewer_bn        viewer_bn  doc:1     -> False
CHECK  doc:1#can_view         can_view   doc:1     -> False
CHECK  doc:1#viewer           can_view   doc:1     -> False
CHECK  doc:1#fview            fview      doc:1     -> False
CHECK  doc:1#vi               vi         doc:1     -> False
CHECK  doc:1#vu               vu         doc:1     -> False
CHECK  doc:1#nb               nb         doc:1     -> False
CHECK  doc:1#viewer           nb         doc:1     -> False
CHECK  folder:1#viewer        viewer     folder:1  -> False
CHECK  folder:1#viewer        fview      doc:1     -> False
CHECK  doc:1#editor           vu         doc:1     -> False
CHECK  doc:1#plain            cv         doc:1     -> False
LOOKUP doc:1#viewer (filter #None) graph=[] set=[]
LREV   doc:1#viewer graph=[] set=[]
EXPAND doc:1#viewer set=MemberSet(pos=frozenset(), stars=frozenset(), neg=frozenset())
== writes ==
WRITE  doc:1#viewer viewer doc:1 -> {'graph': False, 'set:py': False, 'set:roaring': False}
WRITE  doc:1#viewer viewer doc:2 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  user:alice viewer doc:1 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  user:bob banned doc:1 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  user:bob viewer doc:1 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  folder:1 parent doc:1 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  user:carol viewer folder:1 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  doc:1#banned vx doc:1 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  doc:1#editor vy doc:1 -> {'graph': True, 'set:py': True, 'set:roaring': True}
WRITE  doc:1#viewer chain doc:2 -> {'graph': True, 'set:py': True, 'set:roaring': True}
== after writes ==
CHECK  doc:1#viewer           viewer     doc:1     -> False
CHECK  doc:1#viewer           viewer     doc:2     -> True
CHECK  doc:1#viewer_bn        viewer_bn  doc:1     -> False
CHECK  folder:1#viewer        fview      doc:1     -> True
CHECK  folder:1#plain         fplain     doc:1     -> True
CHECK  folder:2#viewer        fview      doc:1     -> False
CHECK  user:alice             viewer     doc:2     -> True
CHECK  user:bob               viewer_bn  doc:1     -> False
CHECK  user:bob               nb         doc:1     -> False
CHECK  doc:1#banned           vx         doc:1     -> True
CHECK  doc:1#banned           vx         doc:2     -> False
CHECK  doc:1#editor           vy         doc:1     -> False
CHECK  doc:1#viewer           chain      doc:2     -> True
CHECK  doc:2#chain            chain      doc:2     -> False
CHECK  user:carol             fview      doc:1     -> True
LOOKUP doc:1#viewer (filter #None) graph=['doc:2#can_view', 'doc:2#chain', 'doc:2#nb', 'doc:2#viewer'] set=['doc:2#can_view', 'doc:2#chain', 'doc:2#nb', 'doc:2#viewer']
LOOKUP folder:1#viewer (filter #None) graph=['doc:1#fview'] set=['doc:1#fview']
LOOKUP doc:1#banned (filter #None) graph=['doc:1#vx'] set=['doc:1#vx']
LOOKUP doc:1#editor (filter #None) graph=[] set=[]
LREV   doc:1#viewer graph=['user:alice#...', 'user:bob#...'] set=['user:alice#...', 'user:bob#...']
LREV   doc:2#viewer graph=['doc:1#viewer', 'user:alice#...', 'user:bob#...'] set=['doc:1#viewer', 'user:alice#...', 'user:bob#...']
LREV   doc:1#fview graph=['folder:1#viewer', 'user:carol#...'] set=['folder:1#viewer', 'user:carol#...']
LREV   doc:1#vx graph=['doc:1#banned'] set=['doc:1#banned']
LREV   doc:1#vy graph=[] set=[]
EXPAND doc:1#viewer set=MemberSet(pos=frozenset({4, 7}), stars=frozenset(), neg=frozenset())
EXPAND doc:2#viewer set=MemberSet(pos=frozenset({0, 4, 7}), stars=frozenset(), neg=frozenset())
```

### 2.1 Divergence table, repo vs OpenFGA v1.22.0 (first-hand PROBE, both sides)

| query | repo (all corners) | OpenFGA | class |
|---|---|---|---|
| `check(doc:1#R, R, doc:1)`, any declared `R`, empty store | False | True | direct self |
| `check(doc:1#viewer, can_view, doc:1)` (`can_view: viewer`) | False | True | self through computed |
| `check(doc:1#viewer, nb, doc:1)` (`nb: viewer but not banned`) | False | True | self through a boolean base |
| `check(doc:2#chain, chain, doc:2)` with tuples present | False | True | direct self |
| `check(folder:1#viewer, fview, doc:1)` after `doc:1 parent folder:1` | **True** | True | self through TTU, **already agrees** |
| `check(folder:1#plain, fplain, doc:1)` (target admits no userset) | **True** | True | already agrees |
| `check(doc:1#banned, vx, doc:1)`, stored `doc:1#banned vx doc:1` | **True** | **False** | **ALLOW to DENY flip** (self in the subtrahend) |
| `check(doc:1#editor, vy, doc:1)`, stored `doc:1#editor vy doc:1` | False | True | DENY to ALLOW (self satisfies the `and` arm) |
| `lookup(doc:1#viewer)` | omits `doc:1#viewer`, `doc:1#can_view`, `doc:1#nb` | ListObjects includes `doc:1` for each | lookup |
| `lookup_reverse(viewer, doc, 2)` | `doc:1#viewer` + users | ListUsers also returns `doc:2#viewer` itself | lookup |
| `expand(viewer, doc, 1)` | stored members only | Expand: stored members only | **agrees** |
| write `doc:1#viewer viewer doc:1` | `AdmissionRejected` (cycle) | 400 "implicit" | agrees (refused) |

**Why the TTU row already agrees (first-hand READ).** The TTU leaf has carried a from-chain
identity disjunct since the 2026-07-13 lookup-gate fix X4a ("the Zanzibar from-chain
rule"): `tests/oracle.py::Oracle.check.ttu_leaf` (`if (s_type, s_name, s_pred) ==
(p_type, p_name, target_rel): return True`), its Lean twin
`formal/lean/ZanzibarProofs/Spec/Semantics.lean::ttuLeaf` (`(s.type == pt && s.name == pn
&& s.predicate == targetRel) || rec pt pn targetRel`), the set engine's `ttu_leaf`, the
graph's materialized rewrite edge (untainted), and for derived TTUs
`src/zanzibar/graphindex/processor.py::_EvalContext.ttu_check` plus reconcile step (2a)
(`::DeltaProcessor._from_chain_keys`). History: `tests/test_lookup_oracle.py` module
docstring (X4) and `::test_graph_check_from_chain_userset_on_derived_ttu`. So the repo
ALREADY applies OpenFGA's self rule at exactly one kind of node (a TTU target reached
through a stored parent) and nowhere else. REASONED: the current semantics is an accident
of representation (the untainted graph materializes a rewrite EDGE for a TTU but only a
write-time RULE for a computed userset), not a design. No spec section, deviation entry
or oracle comment weighs the general rule (the row's 2026-10-13d finding; re-checked by
this agent with a grep of `docs/spec-deviations.md`, `README.md`, `PYPI_README.md`,
`docs/specs/*.md`, `formal/*.md` for `implicit.*userset|related to itself|self-defining|
IsSelfDefining` on 2026-10-14: only the 2026-07-13 attribute-marker correction hits).

## 3. Every surface the rule touches

### 3.1 The rule, stated for this codebase (REASONED from § 1.3, checked against § 1 output)

For a **concrete userset** query subject `s = (T, o, r_s)` (`s_pred != '...'`,
`s_name != '*'`), at every evaluation node `(T', o', r)` of a DECLARED relation:
`member(s, T', o', r) = (s == (T', o', r)) or eval(rewrite(T', r), s)`. The disjunct sits
outside the rewrite, so it beats `but not` and short-circuits `and`. Undeclared relations
stay `False` (this repo's lenient-read contract; OpenFGA errors, § 1.3 item 6). Bare and
star subjects are untouched. **Open sub-decision D1 (no OpenFGA counterpart):** a userset
STAR subject `doc:*#viewer` at the intensional node `(doc, *, viewer)`. OpenFGA forbids
userset wildcards (audit § 2 fact 3), so parity says nothing; the probe patch below
excludes star subjects, which keeps every star answer unchanged.

**An equivalent store/schema reduction (REASONED, not proven; useful for the Lean spec,
§ 4 A4).** For userset subject `s = (T, o, r_s)`: `semR(S, T, q) = sem(S', T ∪ {o#r_s
r_s o}, q)` where `S'` adds a top-level `[T#r_s]` union arm to `r_s` only. At node
`(o, r_s)` the virtual grant's subject equals `s`, so the direct leaf answers True with no
recursion; every other node reaches it only by recursing into `(o, r_s)`, which is exactly
the propagation § 1.3 item 2 shows. Hand-checked against `vx`, `vy`, `nb`, `can_view`,
`vi`. ONE known difference from the disjunct form: the virtual tuple makes `o` a
tuple-mentioned name, so `instances(T)` (the ∃-witness population, which deliberately
EXCLUDES query endpoints — `tests/oracle.py::Oracle.check.instances`) gains `o`, which
changes userset-STAR grants (`[doc:*#can_view]`) for a ghost `o`. That is repo-extension
territory (OpenFGA has no userset wildcards) and is sub-decision D2.

### 3.2 Oracle — `tests/oracle.py`

- `::Oracle.check.sat` — the one place to add the disjunct (after the `expr is None`
  early return, around the `result = sat_expr(expr, o_type, o_name, rel)` line, line 655
  on 2026-10-14). The probe patch used exactly:
  `result = ((subject[2] != '...' and subject[1] != '*' and subject == (o_type, o_name, rel)) or sat_expr(...))`.
- `::Oracle.check.ttu_leaf`'s from-chain disjunct becomes redundant once `sat` has the
  rule (it is the rule applied one node early). Keep it or delete it, but decide with the
  Lean `ttuLeaf` twin in mind: under the fuel bound the inline disjunct costs no fuel and
  the recursive one does (REASONED, see § 4 A4).
- The independence contract holds: no package import is needed.

### 3.3 Set engine — `src/zanzibar/setengine/engine.py`

- `::SetEngine.check.sat` — same disjunct (generator form; `subject` is in scope).
  first-hand READ: the evaluator is the oracle's twin statement-for-statement.
- `::SetEngine.check.ttu_leaf` — the existing from-chain identity (redundant after).
- `::SetEngine.lookup` — reverse BFS seeded by the subject's direct memberships and
  confirmed by `check`. With the rule, the subject's OWN key `(T, o, r_s)` must seed the
  walk (it is a member of itself) so the existing H2 (computed) / H3 (TTU) hops surface
  `doc:1#can_view`, `doc:1#nb`, ... and `check` (now self-aware) confirms them. REASONED.
- `::SetEngine.expand` / `::SetEngine.lookup_reverse` — expand is "the full member set"
  rendered as interned ids (`MemberSet.pos`). OpenFGA's Expand does NOT list the self
  userset; its ListUsers DOES. Sub-decision D3 (below) decides whether `lookup_reverse`
  must list implicit self usersets; if yes, they are frequently NOT INTERNED (expand
  "never interns on read"), so `LookupResult` cannot carry them as ids.
- `::SetEngine._would_cycle` / `::SetEngine._validate` — unchanged: the self tuple stays
  refused (matches OpenFGA's 400), and other cycles stay refused.

### 3.4 Graph index — `src/zanzibar/graphindex/`

- `wildcard.py::WildcardIndex._check_internal` (untainted branch): for `s = (T, o, r_s)`
  the probe-1 key `(subj_id, obj_id)` collapses to `(id, id)` and no self-edge exists
  (cycles are refused), so the answer is False. Untainted relations only depend on
  untainted relations (a container that references a derived relation, including through
  a userset restriction, is tainted: `src/zanzibar/schema/boolean.py::_mentions` /
  `::compute_taint`, as quoted in `formal/CORRESPONDENCE.md` § the `GraphAdmission`
  row) — so on the untainted side the rule reduces to a STATIC same-object seed set:
  `seeds(T, r_s) = {r_s} ∪ {r' : r' reaches r_s through computed-userset arms}`
  (computed at compile time into `SchemaInfo`), and the answer is
  `(relation, o_type, o_name) ∈ {(r', T, o) : r' ∈ seeds}` OR an edge probe from any seed
  node. Mid-path computed hops are already materialized by `RuleSet.apply`'s rule fan-out;
  TTU hops are materialized rewrite edges. REASONED, not built.
- `wildcard.py::WildcardIndex._check_derived` + `processor.py`: derived reads for userset
  subjects come from the residue `upos`/`neg` ("edge-free membership", blind-audit P4), and
  the processor fills them from candidates. A self-propagated subject (`doc:1#viewer` at
  `doc:1#nb`) is never a candidate today, so it must be enumerated the way X4a enumerates
  from-chain keys: a new reconcile step beside
  `processor.py::DeltaProcessor._reconcile` step (2a) (`::DeltaProcessor._from_chain_keys`)
  that enumerates the object's own userset keys `(r', T, o)` for the relations `r'` the
  derived relation can see (a static per-`(T, R)` set from compile), evaluates
  `plan.check_fn` with self-aware leaf reads, and records only when the outcome differs
  from the star default (interning NON-implicit, exactly the 2a recipe). Self keys depend
  only on the object node, so the reconcile trigger set is unchanged (REASONED). Plus the
  identity short-circuit at the root (`(s_pred, s_type, s_name) == (relation, o_type,
  o_name)`) in `_check_derived`, and in `_EvalContext`'s computed/leaf reads.
- `wildcard.py::WildcardIndex.lookup` / `::lookup_reverse` — same id-channel problem as
  the set engine (D3).
- `core.py::ReachabilityIndex` closure — **no change** in the recommended shape (no
  self-edges; cycles stay refused). A materialized alternative (self edges `o#r -> o#r'`
  interned with nodes) would touch refcounts, I1–I12, exact-state restoration and the Lean
  `Closure`/`Write` model; rejected here as strictly more expensive (REASONED).

### 3.5 Lean — `formal/lean/ZanzibarProofs/`

- `Spec/Semantics.lean::step` (adoption point; inside `some e`), or the reduction of
  § 3.1. `step`, `semAux`, `sem`, `evalE`, `directLeaf` are all in
  `formal/headline_definitions.txt` (first-hand READ), so any edit is a deliberate
  definition-pin regeneration.
- `Spec/WellDef.lean::sem_fuel_stable` (T0a) — re-proof if `step` changes.
- `SetEngine/Eval.lean` / `SetEngine/Correct.lean` (`SetEngineModel.check`, answer-for-answer
  twin of `SetEngine.check`).
- Graph: every `graph_correct*` headline (`FullScope.lean::graph_correct`,
  `::graph_correct_public`, `GraphIndex/Correct.lean::graph_correct_empty` — which states
  the EMPTY graph agrees with `sem`, false for a self query once `sem` is reflexive —
  `GraphIndex/DirectCorrect.lean::graph_correct_direct`, the `CascadeStrata*` family) and
  the conformance capstones `GraphIndex/Exec.lean::graphRun_check_eq_sem` /
  `::graphModeAnswers_eq_sem`. Reference counts (grep -w, 2026-10-14, under
  `formal/lean/ZanzibarProofs`): `evalE` 26 files / 176 lines, `semAux` 23 / 295,
  `directLeaf` 23 / 122, `ttuLeaf` 15 / 61.

### 3.6 Schema shapes OpenFGA accepts that this repo refuses (found on the way; not TK138)

first-hand PROBE (§ 1 accepted them; `repo_probe.py`'s first two runs refused them):
`define viewer_bn3: [user, doc#viewer_bn3] but not banned2` with
`define banned2: [user, doc#viewer_bn3]` — `ValueError: recursion through negation ...
doc#viewer_bn3 -> doc#banned2 -> doc#viewer_bn3` (`_validate_stratified_negation`, both
parsers, `TK114`); and `define vi: [user, doc#vi] and editor` —
`CyclicDerivedDependency` (graph compile only; the set engine accepts it). Both are known,
deliberate refusals; listed so the decision stage does not mistake them for TK138 scope.

## 4. Options and their cost (REASONED estimates unless a measurement is cited)

Sub-decisions any option A must settle first (none has an OpenFGA answer to copy):

- **D1** userset STAR subjects (`doc:*#viewer`) — recommended: rule does not apply
  (unchanged answers; OpenFGA has no such subject).
- **D2** if the Lean spec uses the § 3.1 reduction, the ghost-object `instances` difference
  — recommended: define the spec by the disjunct (so `instances` is untouched) and use the
  reduction only as a proof device, or prove the two agree outside userset-star grants.
- **D3** lookups. OpenFGA's ListObjects/ListUsers include implicit self answers. Here
  `LookupResult.node_ids` are interned ids (set engine: recycled interner handles; graph:
  `Node` rows), and the implicit usersets (`doc:1#can_view` for subject `doc:1#viewer`,
  `doc:2#viewer` in `lookup_reverse(viewer, doc, 2)`, and every same-object sub-relation of
  every userset reached) are often NOT interned. Either (D3a) lookups list them — needs a
  key channel in `LookupResult` (an API change; **collides with `TK123`, which is reviewing
  "lookup results" this session**), or intern-on-read (forbidden today on both backends);
  or (D3b) lookups list only materialized/stored usersets and the deviation is documented
  (OpenFGA's Expand also omits them, § 1.3 item 4). Whether D3b is even available depends
  on the lookup oracle gate's candidate universe (§ 7.1 measurement).

### Option A — adopt OpenFGA semantics everywhere (the user's 2026-10-13d direction)

| part | files / symbols | size |
|---|---|---|
| A1 oracle | `tests/oracle.py::Oracle.check.sat` (one disjunct) | S |
| A2 set engine | `src/zanzibar/setengine/engine.py::SetEngine.check.sat` (one disjunct); `::SetEngine.lookup` (seed the walk with the subject's own key); `::SetEngine.lookup_reverse` per D3 | S (check) + M (lookups, D3a) |
| A3 graph, untainted | `src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_internal` (identity + static seed-set probes); compile a per-`(T, r)` computed-superset table into `SchemaInfo` (`src/zanzibar/schema/compiler.py::derive_schema_info` or beside it) | M |
| A3 graph, derived | `src/zanzibar/graphindex/processor.py` — a reconcile step beside (2a) enumerating self keys, identity in `_EvalContext` reads; `wildcard.py::WildcardIndex._check_derived` root identity; `src/zanzibar/graphindex/invariants.py` (I9 / delta-scoped verifier must recompute the same self keys or paranoia goes red) | L |
| A3 graph, lookups | `wildcard.py::WildcardIndex.lookup` / `::lookup_reverse` per D3 | M (D3a) |
| A4 Lean spec | `Spec/Semantics.lean::step` (+ `formal/headline_definitions.txt` regen) and `Spec/WellDef.lean::sem_fuel_stable`; OR a new `semR` defined by the § 3.1 reduction, leaving every existing `sem` theorem untouched | M |
| A4 Lean set engine | `SetEngine/Eval.lean`, `SetEngine/Correct.lean` | M |
| A4 Lean graph | every `graph_correct*` headline + `graphRun_check_eq_sem` / `graphModeAnswers_eq_sem` + the reconcile model (`GraphIndex/Reconcile*.lean`, where the X4a from-chain keys are already modelled in `ReconcileStars.lean`) + `formal/headline_statements.txt` | XL |
| A5 docs | `docs/spec-deviations.md` (new dated entry; amend the 2026-07-13 one), `PYPI_README.md` (+ its executed quickstart is unaffected), `formal/SEMANTICS.md` § 5, `formal/CORRESPONDENCE.md` rows for `sem`/`evalE`/`ttuLeaf`/`_check_internal`/`_check_derived`/`probeNonDerived`/`probeDerived`, `tests/test_self_referential_tuples.py` docstring | S |

Goldens: the compiled-RuleSet snapshots (`tests/snapshots/`) do not change unless the
seed table is added to `RuleSet`/`SchemaInfo` in a way the snapshot serializes — check
before building (REASONED; a new `SchemaInfo` field may or may not be snapshotted).
Total: **L for the Python, XL with the Lean graph model.** The honest staging is Python
(all three corners together, never one alone) + Lean spec + Lean set engine first, with
the Lean graph gap logged in `formal/CORRESPONDENCE.md` § 7 until it lands (the sanctioned
interim, CLAUDE.md "Perf work & the Lean model"); a staged plan that changes one Python
corner before the others creates a divergence and is out.

Behaviour change to announce: `vx`-shaped answers flip ALLOW to DENY (§ 2.1). That is the
security-relevant direction for anyone who relies on today's answer, and the reason the
change needs a CHANGELOG entry and a version bump, not a silent patch.

### Option B — keep the semantics, document (and optionally make it uniform)

- B1 document only: `docs/spec-deviations.md` entry + `PYPI_README.md` "differences from
  OpenFGA" line, both naming § 2.1's table (especially the `vx` direction: this library
  ALLOWS a userset-subject check that OpenFGA DENIES). Size S. No code, Lean or golden.
- B2 refuse the query shape: rejected. Reads are lenient by contract, and the divergence
  is not confined to `check(o#r, r, o)` — it propagates to other relations and other
  objects (§ 1.3 item 2), so no syntactic refusal captures it.
- B3 make the semantics uniformly NON-reflexive by deleting the TTU from-chain identity:
  rejected. It reverses a deliberate 2026-07-13 fix (X4a), moves AWAY from OpenFGA, and
  costs about as much Lean as A4's spec half.

### Option C — leave

Zero cost. Leaves a security-relevant parity gap undocumented on the PyPI page, against
the user's recorded decision. Listed for completeness only.

## 5. Plan for option A as numbered steps (for the builder, if A is chosen)

1. Record D1–D3 decisions on the row (`task.py comment TK138`).
2. Add the dedicated pin test FIRST, red against today's tree:
   `tests/test_tk138_userset_self_relation.py` — a `ParityEngine` (all corners + oracle,
   `tests/parity.py::ParityEngine`) over model A-as-accepted + model B, asserting every
   § 2.1 row at its OpenFGA value (literal expectations transcribed from § 1, NOT derived
   from the oracle, so the oracle cannot drift with them). Include an empty-store block, a
   `vx` flip, a `vy` flip, the TTU rows (must stay True), the write refusal, concrete-user
   and `user:*` queries on the same store (must be unchanged), and D1's star subject.
3. Oracle: `tests/oracle.py::Oracle.check.sat` disjunct. Expect the parity suites to go red
   (§ 7.1 measures where).
4. Set engine: `SetEngine.check.sat` disjunct; `SetEngine.lookup` seeding. Re-run step 2.
5. Graph untainted: seed table at compile + `_check_internal` identity/seed probes.
6. Graph derived: processor reconcile self keys + `_check_derived` identity + invariants.
7. Lookups per D3 (if D3a: coordinate the `LookupResult` shape with `TK123` first).
8. Lean spec + set engine model; graph model or § 7 gap entry. Regenerate definition /
   statement pins deliberately; update `CORRESPONDENCE.md` rows, then
   `claim_rot.py --generate` (anchor content pins move for every edited symbol).
9. Docs (A5), CHANGELOG, version bump; full phased gate; hypothesis fuzz sweep with
   `--hypothesis-seed=N` (algorithm change).

## 6. Tests to add, and the sabotage for each

| test | guards | sabotage (must go red) |
|---|---|---|
| `tests/test_tk138_userset_self_relation.py::test_openfga_transcript_*` (literal § 1 expectations, all corners) | the rule on every corner | delete the disjunct in ONE corner at a time (oracle; `SetEngine.check.sat`; `_check_internal`; the processor self-key step) — each alone must fail, proving no corner is carried by another |
| `...::test_vx_flip_denies` | self in a subtrahend | invert the disjunct's polarity in the processor's self-key step only (records upos instead of neg) |
| `...::test_concrete_and_bare_star_subjects_unchanged` | blast radius stays userset-only | widen the guard to bare subjects (`s_pred == '...'`) — must go red |
| `...::test_userset_star_subject_unchanged` (D1) | star exclusion | drop `subject[1] != '*'` |
| `...::test_self_tuple_still_refused` | admission unchanged | bypass `SetEngine._would_cycle` for `s == o` |
| lookup pins (per D3) | lookups follow check | remove the subject-own-key seed in `SetEngine.lookup` |
| a conformance corpus schema with self-shaped queries (`formal/conformance/corpus.py`) | Lean `sem` ≡ oracle on the shape | revert the Lean `step` disjunct; `test_conformance_spec.py` must go red |

Record each literal red output in the test docstring and the commit message
(`docs/sabotage-procedure.md`).

## 7. Gate impact

### 7.1 Measured: where the tree already observes the shape (first-hand PROBE, 2026-10-14)

Instrument: a pytest plugin (`.scratch/now-next/probes/scout-TK138/tk138_oracle_plugin.py`)
that replaces `tests.oracle.Oracle.check` with a copy carrying ONLY the § 3.2 disjunct
(`make_oracle_self.py` builds it; anchor replaced exactly once). Nothing else changed: no
backend, no Lean. So every failure is a place where an existing test or conformance suite
already queries a self-shaped userset and compares the oracle against another corner.

**Instrument control.** The first run (129 failed / 95 passed) was an INSTRUMENT failure,
not a measurement: the copied module's AST classes were distinct from `tests.oracle`'s, so
`sat_expr` raised `TypeError: unknown AST node OUnion(...)`. Fixed by rebinding the copy's
module globals to `tests.oracle`'s objects; `sanity2.py` then shows the patched METHOD on a
`tests.oracle.Oracle` instance answering `orig [False, False, True, False]` /
`patch [True, True, False, False]` for (self, self-through-computed, `vx`, a concrete
user) — the OpenFGA values. The rerun log has zero `TypeError`.

Run (modules: `tests/test_matrix.py`, `test_lookup_oracle.py`, `test_oracle.py`,
`test_oracle_boolean.py`, `test_scenarios.py`, `test_parity_engine.py`,
`test_self_referential_tuples.py`, `test_pure_union_ttu.py`, `test_reads.py`,
`test_setengine_check.py`, `test_blind_audit_regressions.py`, `test_lookup_hypothesis.py`,
`test_hypothesis.py`, `formal/conformance/test_conformance_spec.py`,
`test_conformance_random.py`, `test_conformance_generated.py`):
`194 failed, 202 passed in 691.87s`. Failures per module:

```
     40 formal/conformance/test_conformance_generated.py
     26 formal/conformance/test_conformance_random.py
     68 formal/conformance/test_conformance_spec.py
      2 tests/test_blind_audit_regressions.py
      9 tests/test_hypothesis.py
      1 tests/test_lookup_hypothesis.py
     17 tests/test_lookup_oracle.py
     15 tests/test_matrix.py
      3 tests/test_parity_engine.py
      3 tests/test_reads.py
     10 tests/test_setengine_check.py
```

Most frequent assertion lines (`^E ` in the log): `query=('parent', 'doc', 'd1', 'parent',
'doc', 'd1') oracle=True setengine=False` (45), `query=('r0', 'doc', 'd1', 'r0', 'doc',
'd1') oracle=True setengine=False` (41). The lookup gate fails G1, e.g.
`AssertionError: graph.lookup('viewer', 'folder', 'f1') vs oracle on viewer folder:f1:
graph=False oracle=True` (`tests/test_lookup_oracle.py:248`).

What this establishes:

1. **The existing grids already cover the shape** — the validation matrix, the
   ParityEngine suites, the hypothesis campaign, the lookup gate and all three Lean
   conformance suites query self-shaped usersets. So once every corner moves, these
   suites pin the new semantics with no new grid work; the new dedicated test (§ 6) is
   still needed because none of them carries OpenFGA's literal answers.
2. **The Lean corner is NOT deferrable.** `test_conformance_spec.py` / `_random` /
   `_generated` compare the oracle with the executable Lean `sem` (zcli), and
   `test_conformance_graph.py` compares `WildcardIndex` with the executable Lean graph
   model `GraphIndex/Exec.lean::graphModeAnswers` (`formal/CORRESPONDENCE.md` row for
   `graphRun`, first-hand READ). Changing the Python without changing those Lean
   DEFINITIONS turns the conformance phases red; changing the definitions breaks the
   theorems about them, and `formal/conformance/sorry_scan.py` forbids a `sorry`. So a
   `CORRESPONDENCE.md` § 7 gap entry is NOT a sufficient interim for this change (REASONED
   from the above). The Lean graph re-proof is on the critical path of a green gate.
3. **D3b (lookups omit implicit usersets) is not available without weakening a gate.** The
   lookup gate asserts G1/G3/S1 two-sided exactness over a candidate grid that includes
   self-shaped userset subjects and ghosts (`tests/test_lookup_oracle.py::_subject_candidates`,
   `::_object_candidates`), and CLAUDE.md forbids relaxing those properties. So option A
   means D3a: lookups must list implicit usersets, which needs a non-id channel or
   intern-on-read (§ 4 D3).

Not run (time): `test_conformance_graph.py`, `test_conformance_state.py`, the rest of
`tests/`. UNVERIFIED whether they also observe the shape; expected yes for the graph suite
(it shares `formal/conformance/grid.py`, whose docstring says it emits userset subjects).

### 7.2 Floors, pins, snapshots

- `MIN_TESTS_ALL` / `MIN_CONF_ALL`: only go up (new tests and corpus rows); nothing in
  option A deletes a test. Re-measure with `pytest <dir> -q --collect-only`.
- `MAX_TESTS_XFAILED`: unchanged — any interim divergence gets a positive pin, never an
  xfail.
- `formal/headline_definitions.txt`: `step` / `semAux` / `sem` / `evalE` / `directLeaf` /
  `ttuLeaf` entries move if touched (deliberate regen); `formal/headline_statements.txt`
  moves for any graph headline whose statement changes.
- `formal/correspondence_anchor_pin.txt` (`formal/conformance/claim_rot.py`): every edited
  anchored symbol (`tests/oracle.py::Oracle.check.sat`, `SetEngine.check`,
  `WildcardIndex._check_internal`, `::_check_derived`, the processor reconcile, the Lean
  defs) moves its body hash — regenerate with `--generate` only after re-reading the cited
  rows.
- `tests/snapshots/` (compiled RuleSet byte identity): unchanged unless the seed table is
  serialized there (check before building).
- `formal/FINAL_REVIEW.md` generated counts block: regenerate
  (`python -m formal.conformance.doc_counts --generate`) after tests are added.

## 8. Risks and collisions with other open items

- **`TK123` (public API review, renames `connectedstore` and reviews "lookup results")** —
  D3a needs a `LookupResult` channel for uninterned keys; decide that inside `TK123`'s
  API pass, not twice. TK123's rename touches import paths only; nothing in
  `connectedstore/` changes for TK138 (REASONED: the composition layer calls the backends).
- **`TK119` and `TK132` (both Lean, both NEXT)** — `TK132` changes `isPure` in the graph
  leaf model, `TK119` adds a `leaf-rules` zcli mode; option A's Lean graph work edits the
  same graph-model files and the same `Cli.lean`. Land TK119/TK132 first, or serialize:
  three concurrent Lean edits to one model is the merge risk.
- **`TK137` (DSL parsers accept shapes OpenFGA refuses)** — independent, but both edit the
  PyPI "differences from OpenFGA" text; one doc edit, not two.
- **`TK4` (strict ∀⇒∃ for wildcards)** — D1/D2 sit on the same `instances` population;
  keep the userset-star answers unchanged so TK4's pins do not move.
- **`TK143` (docs site)** — consumes whatever § 2.1 table ships.
- Perf: the graph's untainted userset-subject check grows from ≤4 probe keys to
  ≤4×|seeds| in the same single `IN` query; derived reconcile evaluates up to
  |self keys of (T, R)| extra candidates per reconciled node. Unmeasured.
- The `ParityEngine`/`test_matrix` failures in § 7.1 will ALL go red the moment any one
  corner changes alone — the builder should expect a red-everywhere tree from step 3 until
  step 6, and keep that window inside one uncommitted change set (commit only on green).
