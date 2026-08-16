# Spec deviations log — graph-boolean-ivm-spec.md

Per spec §0: dated entries recording where implementation diverges from the spec's
*adaptable* prescriptions (concrete names, signatures, layouts, mechanisms marked
*(adapt)*), and P0 recon findings where the spec's repo-facts differ from repo reality.
Frozen items (§0 list) are never logged here — a frozen conflict stops the work and goes
to the user instead.

---

## 2026-08-14 — the `_any_residue_reference` / `_keys_referencing` scan is FIXED: `ResidueRefV1`, the index `ZT-P0-1` prescribed

Closes the board item opened by the 2026-07-29b **measurement** entry below, which
deliberately measured and did not fix. Both node-release lookups were complete
`ResidueV1` scans with a per-row JSON decode; they are now indexed seeks on a new
reverse-index table `index_v4/models.py::ResidueRefV1`
(`object_node_id`, `subject_node_id`, one row per id in `neg | upos`).

This is exactly the fix `ZT-P0-1`'s own note named — *"a subject-id → residue **index**
maintained in `_store_residue`, never a leaf-kind whitelist"* — and the N3-WITHDRAWN
block at the head of `processor.py` is updated to say it landed. The whitelist mechanism
stays retired: an index is keyed on the ids actually recorded, so widening
candidate-resolution maintains it automatically, which is precisely the coupling that
made a leaf-kind gate rot into an escalation.

**Measured** (SQLite in-memory, paranoia off, both implementations timed in the same
process on the same store; schema `viewer: [user:*] but not blocked`, R residue-bearing
objects). The old scan is linear in R; the new lookup does not move:

| R | scan (old) | index (new) | speedup |
|---|---|---|---|
| 25 | 0.30 ms | 0.114 ms | 3x |
| 100 | 1.05 ms | 0.222 ms | 5x |
| 400 | 3.40 ms | 0.140 ms | 24x |
| 800 | 6.17 ms | 0.126 ms | 49x |
| 1600 | 13.03 ms | 0.146 ms | 89x |

The headline is the **flatness**, not the 89x: the extrapolated ~1.4 s per node release
at 100k residue rows, and the quadratic churn past the crossover, are both gone by
construction rather than reduced. The 2026-07-29b instrument note is honoured — the
harness asserts its own residue-row and `neg`-id counts, because a run that built none
would have timed an empty table and printed a believable result.

**Maintenance and its checker.** `DeltaProcessor._sync_residue_refs` is called from
`_store_residue` (the only live-path `ResidueV1` writer) and diffs against the rows that
exist, so cost is O(rows for this object). `bulk_build.py` populates the index itself in
a new `(2c)` block — it bypasses `_store_residue` entirely, and that omission is the
single most plausible way to ship this broken. `ResidueV1.neg`/`upos` stay
**authoritative**; a new I6 clause asserts the index agrees with them exactly and in both
directions, plus an orphan clause for index rows outliving their residue. That clause
decodes the JSON directly and never consults `processor.py`, so it is an independent
check and not a mirror of its own subject.

**Not in the state gate, deliberately.** `formal/conformance/extractor.py` names the
tables it reads, so `ResidueRefV1` is not swept in. That loses nothing: its contents are
a pure function of `ResidueV1.neg`/`upos`, which the gate already compares, and the I6
clause pins the function. It is therefore not a new projection — there is no independent
state here to drop.

**No Lean obligation, verified rather than assumed.** The whole region is already
declared unmodeled in `CORRESPONDENCE.md` §7.3 ("Node GC + flag lifecycle AS AN
ALGORITHM"), and `ReconcileDiff.lean` / `Cascade.lean` both state that node GC is a
modeled-away optimization. Nothing became dead code. The three function names in §7.3's
anchor list (`_any_residue_reference`, `_keys_referencing`, `_residue_references`) were
kept **for that reason** — renaming any of them would fail `verify.sh` step 4d.

### ★ The sabotage findings, which are the transferable part

Three source-level sabotages, all restored; full literal output in
`tests/test_residue_ref_index.py`'s module docstring. **Two of the three predictions
were wrong**, and the second correction is the one worth carrying:

* **(S1) the offline path forgets the index.** Predicted: the bulk differential gate
  stays green (it compares `snapshot_rows`, i.e. nodes and edges only) and the new file
  is the only witness. Observed: it goes `5 failed, 2 passed` — `test_bulk_build.py`
  calls `check_invariants`, so the new I6 clause fires inside the existing gate. Better
  coverage than designed for.
* **(S3) skip the sync on the residue-DELETE branch only** — the narrowest of the three.
  Predicted: caught by the teardown test. **Observed: the entire new test file was GREEN
  (`11 passed`)**; only `tests/test_matrix.py` caught it, via paranoia. **The reason
  generalises to any index maintained beside a deletable row:** an orphan is observable
  only when the indexed row goes from ref-bearing straight to deleted in ONE step, and
  every natural teardown ordering empties `neg`/`upos` while `stars` is still present —
  which clears the index through the *update* branch and leaves nothing to orphan. A
  teardown test is not a delete test.
  `test_residue_emptied_in_one_step_takes_its_index_rows_with_it` constructs that
  ordering explicitly (drop the wildcard grant first, then the userset grant) and is the
  file's only pin on the delete branch.

**Migration note, stated because there is no migration framework.** Tables are created by
`SQLModel.metadata.create_all`, so an index built before this change gets an empty
`residue_ref_v1` and its node-release guards would believe nothing is referenced — the
ZT-P0-1 direction. There is no in-tree upgrade path and none is offered (schemas are
static; a new schema means a new store/index). What exists is detection: the cheap
`ZANZIBAR_PARANOIA=residue` tier fires on the first commit against such a store, with
`I6: residue_ref index disagrees with neg|upos on ...`. Rebuild with `build_index` to
recover.

---

## 2026-08-11 — ★★ RC2 FIXED: a stored `T:*` tupleset parent is represented, not dropped. The 2026-08-10 fail-open family is CLOSED.

RC1 was fixed 2026-08-10 (`ed46e54`); this closes **RC2**, the second and last root cause of
the entry below. Both had an authorization fail-open direction. The bounded exhaustive
sweep that mapped the family (2,302,854 queries over 346 compiled schemas, 26 minimized
divergences) found **exactly these two causes**, so the family is closed at two.

### What the fix is, and why it is not the one-liner

The `n.wildcard == ''` clause was **not** deleted — the entry below records both dead ends,
and both were re-confirmed before starting. The star parent is now *represented*, mirroring
the semantics the oracle (`tests/oracle.py::ttu_leaf`, the `pn == '*'` arm) and the set
engine (`setengine/engine.py::ttu_leaf` / `ttu_expand`) already implement and have always
agreed on. A stored `T:*` tupleset tuple contributes **two things, not one**:

1. **the SHAPE `(T, target_rel)`, unconditionally** — every userset of that shape is a
   member whatever its name. New `DeltaProcessor.tupleset_star_types` /
   `derived_stored_star_types`, consumed by all four `_EvalContext` TTU methods and folded
   into the residue's `stars`. This is the direct analogue of `ms.star((pt, target))` at
   `setengine/engine.py::ttu_expand`.
2. **an ∃-expansion over the tuple-mentioned instances of `T`** — folded into
   `tupleset_parents` itself, so every downstream consumer (`_from_chain_keys`,
   `_leaf_concretes`, `_derived_leaf_neg_ids`) became correct with **no edit**. The
   instance source is the interned concrete nodes, which are exactly the tuple-mentioned
   names because the graph interns only on write paths — query endpoints must never
   witness existence (strict ∀⇒∃, blind-audit O3), the same rule both other backends keep.

The split (`_stored_tupleset_subjects`) is what makes this expressible: returning
`('T', '*')` as if it were a parent name is precisely the naive fix that detonates, because
`('T','*')` is **not representable as a concrete node** (`core.py:913`).

### ★ The part no design document predicted: the CASCADE FAN-OUT

Getting the read path right is not enough, and this is the transferable finding. A star
tupleset tuple hangs off the `w_any(T,'...')` node, **not** off any entity. So
`_stored_parent_objects_of_entity` — which finds "objects invalidated by a delta on this
entity" by walking the entity's own outgoing edges — saw nothing, and a later write to some
`T:x` would have invalidated no dependent at all. The read fix alone therefore **passes
every pin in `tests/test_ttu_tupleset_parent_types.py`**, because those write in one batch
and reconcile once; it would have failed only under incremental maintenance. Both that
helper and the `'ttu'` arm of the delta fan-out now read the `w_any` node as a second
source. *A correctness fix to a read path in an IVM system is not done until the
invalidation path has been asked the same question.*

### Assurance added with the fix — and what each one is worth

* **The bulk corpus gap is CLOSED.** `tests/test_bulk_build.py` was *measured* blind to this
  direction (see the 2026-08-10 entry: one-sided edit S1 left it 6-passed-GREEN while
  control S2 reddened it 2/6, so the gate reached the function and the gap was the corpus).
  New corpus `rc2_star_tupleset` — a `T:*` subject holding a stored tupleset tuple on a
  derived tupleset relation, carrying BOTH TTU directions. **Sabotage, literal output:**
  reverting the bulk half alone (S1, leaving `processor.py` fixed) now gives
  `1 failed, 6 passed` with `AssertionError: [rc2_star_tupleset] snapshot_rows differ`,
  and the other six corpora stay green so the red is attributable. Its anti-vacuity branch
  asserts three separate things, because each is a way the corpus could quietly stop
  testing what it exists for: the leaf kind is reached, a `doc:*` subject really lands on a
  **storage** leaf of `parent`, and some residue really carries the star shape.
* **A compile-time invariant, and deliberately NOT a mirror.**
  `zanzibar_utils_v1.py::_assert_ttu_parent_types_cover_admission`: every TTU's frozen
  `parent_types` must cover every bare-entity type **admission** accepts onto that tupleset
  relation. ★ It reads the emitted `RewriteFilter`/`Filter` patterns, **never
  `_member_types`** — the function RC1 got wrong. An invariant reading `_member_types`
  would be a mirror (`docs/sabotage-procedure.md`), exactly like **I9**, which re-runs
  `reconcile`, reads the same wrong `parent_types`, agrees with itself, and stayed green
  through both fail-opens with paranoia ON. **Validated RED-before/GREEN-after:** reverting
  `_member_types`' `Exclusion` arm to `walk(e.base)` and compiling
  `parent: [folder] but not [doc]` gives

  ```
  ValueError: TTU 'viewer' from 'parent' in doc#inherited: compiled parent_types
  ('folder',) omits type(s) ['doc'] that ADMISSION accepts onto doc#parent. A stored
  tupleset tuple of that type would be silently dropped as a TTU parent (fail-open under
  a negated TTU). This is the RC1 class -- suspect _member_types, not this check.
  ```

  It catches RC1 **at compile time, before any tuple is written**. Made permanent as
  `test_compile_refuses_parent_types_narrower_than_admission`.
  *Honest limit:* it only sees types some Filter accepts, so a tupleset fed only by rewrite
  Rules is vacuous here rather than wrong — stated in the docstring.

### The gate

All five previously-red tests went green **with no test edit**, which was the stated
completeness criterion (`HANDOFF.md`): the two hand-minimised pins, the generated tupleset
grammar (`test_every_tupleset_kind_is_driven_against_the_oracle`), and both driving regimes
— three instruments sharing no derivation. `tests/` 823/823 across the four tiles; 6-seed
fuzz sweep (`--hypothesis-seed=` 7 19 31 53 71 97, the flag form) clean on
`test_hypothesis.py` and `test_lookup_hypothesis.py`, including seeds 53 and 97 where
`TestParityMachine` detonated pre-fix.

---

## 2026-08-10 — ★★ LIVE AUTHORIZATION FAIL-OPEN: two root causes drop STORED TTU tupleset parents. RC1 FIXED `ed46e54`; RC2 FIXED 2026-08-11 (see entry above).

> ⚠ **This entry was substantially REWRITTEN on 2026-08-10 (later the same day).** The
> original filing — preserved verbatim in the "superseded original" block at the end of this
> entry — was wrong in three ways that each mattered: it described **one** bug where there
> are **two independent** ones, it classified the severity as **fail-closed** when both
> causes have a **fail-open** direction, and its **mechanism was false** in a way that would
> have sent the next reader rewriting correct leaf-routing code. All three corrections are
> measured, not argued. The original is kept because a reader who acted on it would have
> done damage, and that is worth being able to see.

**Second and third bugs of the same family as 2026-08-09** — the graph index alone diverges
while the oracle and BOTH set engines agree against it. Reproduced by hand before filing.

### Severity: FAIL-OPEN, correcting the original filing

Read through a **negated** TTU (`define access: [user] but not viewer from parent`) the
graph **GRANTS what the oracle and both set engines DENY**:

```
RC1  check(alice, access, doc:d1):  oracle=False  graph=True   sets=[False, False]
RC2  check(alice, access, doc:d1):  oracle=False  graph=True   sets=[False, False]
```

**The general rule, which is the transferable part:** a dropped TTU parent is a false
NEGATIVE under a positive TTU and a false POSITIVE under a negated one. Probing only the
positive direction mis-classifies severity by exactly one sign — which is what happened
here, and what the original entry below recorded.

⚠ **NOT claimed:** the 2026-08-09 sibling (below, `:83`) carries identical "it fails closed,
so it is not a security fail-open" wording and the rule predicts it inverts too. It was
**not re-tested** — that bug is fixed (`c042056`) and testing would mean reverting. Open
question, not a finding. Do not propagate the prediction into that entry as measured fact.

**The probe, if anyone runs it (board row `P12`, ~½ session).** Revert `c042056` in a
**scratch worktree** — never the working tree — add a **negated**-TTU consumer over the
`owc_star_ttu.fga` shape, and re-measure the answer direction. **Completion criterion:**
either this entry gains a measured severity for the 2026-08-09 sibling, or that sibling's
"fails closed" wording is corrected in place. ⚠ Until then this remains a **prediction, not
an observation** — do not propagate it as measured fact anywhere, including into the
2026-08-09 entry itself.

*(Context for triage: this repo ships no service wrapper — the store is a plain callable
API with no deployment — so this is a library correctness defect, not an exposed system.)*

### The two root causes

Both drop a stored tupleset tuple that `CLAUDE.md`'s pinned rule requires the TTU to walk.

**RC1 — a type reaching the tupleset relation only through the exclusion's subtrahend.**
`zanzibar_utils_v1.py::_member_types` returns `walk(e.base)` for an `Exclusion`, so on
`define parent: [folder] but not [doc]` the type `doc` never enters the compiled
`parent_types`, and `index_v4/processor.py::tupleset_parents` filters the stored parent out
with `n.type in parent_types`. Fix: union `walk(e.subtract)`. Its docstring encodes the same
mistake and must change with it.

**RC2 — a stored `T:*` parent when the tupleset relation is DERIVED.** The `n.wildcard == ''`
clause of the same filter drops it. Needs no exclusion and no object wildcard; the tupleset
relation only has to be tainted. ⚠ **Not a one-liner** — deleting the clause breaks admission
parity first (`accept/reject divergence on add ('...','doc','*','parent','doc','d1'):
graph=False set:py=True`) and a naive widening crashes at `index_v4/core.py:914`
(`name=='*' and a non-empty wildcard must go together`). The star parent must be
**represented** (the set engine's `MemberSet.stars` algebra is the analogue), not merely
admitted. This is a semantics decision, not a filter tweak.

### The mechanism the original entry got wrong

The original said the graph "respects the boolean evaluation of the tupleset relation
instead of its stored tuples" and that the storage-leaf split "is evidently not being
applied". **Both clauses are false**, measured on the RC1 fixture at `e136c8c`:

* the split **is** applied — `plan(doc,parent).leaves` carries `parent.0` *and* `parent.1`,
  both `storage=True`;
* the write **does** land on a storage leaf — `doc:d2#... -> doc:d1#parent.1`;
* `derived_stored_parents` **does** scan every storage leaf and reach that edge;
* the read path **never evaluates** `parent`'s boolean plan — it consults the plan only for
  its storage-leaf name list (`_ts_leaf_predicates`).

The parent is lost one step later, purely to compile-time metadata. Anyone fixing the bug as
originally described would have gone rewriting correct code.

### Scope, measured

A bounded exhaustive sweep (443 schemas generated → 346 compiled → 13,042 tuple states →
**2,302,854 queries** compared 4-way) found **26 distinct minimized divergences from exactly
these 2 root causes**, direction-symmetric, under every TTU consumer shape tried. Zero
admission divergences; both set engines matched the oracle on all 2.3M queries; 110
plain-relation schemas over the full `or`/`and`/`but not` arm cross were clean. So the
hand-found bug is one cell of a family, not a one-off — and the family is closed at two.

### Why nothing caught it

* **No invariant I1–I14 catches either**, and **I9 structurally cannot**: it re-runs
  `reconcile`, which reads the same wrong `parent_types` and agrees with itself. The
  instrument shares its subject's defect. Paranoia was ON throughout and stayed green.
* **The hypothesis campaign could not reach the shape at any budget.** `schema_asts`
  hardcodes `ast = {('doc','parent'): Direct((Restriction('doc','...',False),))}` — every
  TTU in every generated schema reads a plain single-type non-boolean tupleset. This is a
  grammar gap, not seed luck, and it is what the 2026-08-10 generator work addresses.
* **The bulk-vs-incremental identity gate is BLIND to the RC2 direction**, with an
  instrument control proving the blindness is real rather than an unreachable path.
  One-sided edits to `processor.py::tupleset_parents`, `pytest tests/test_bulk_build.py -q`:

  | edit | result |
  |---|---|
  | S1 `n.wildcard == ''` → `in ('', 'any')` (RC2 direction) | **6 passed — GREEN** |
  | S3 drop the `n.type in parent_types` clause (RC1 direction) | **6 passed — GREEN** |
  | S2 control — body → `return []` | 2 failed (`snapshot_rows differ`) |

  S2 proves the gate reaches the function and can see a one-sided change. The gap is the
  **corpus**, not the comparison: no corpus has a `T:*` subject holding a stored tupleset
  tuple on a derived tupleset relation. The RC2 schema is a ready-made minimal corpus.

### Fix-site note that saves a wasted step

`parent_types` is **not** computed in `processor.py` or `bulk_backfill.py` — it is compiled
once at `zanzibar_utils_v1.py:1761` from `_member_types` and frozen onto the plan node, which
both files merely read. So **RC1's single fix repairs the incremental AND bulk paths
together** (measured: `tests/test_bulk_build.py` 6 passed, byte-identity snapshots survive).
**RC2 does need the duplicated fix** at `bulk_backfill.py:454` alongside `processor.py:320`.

### Superseded original (2026-08-10, earlier the same day) — kept as a record of the error

```
type user
type folder
type doc
  relations
    define parent:    [folder] but not [doc]
    define viewer:    [user]
    define inherited: viewer from parent

admit (doc:d2,     parent, doc:d1) -> True        # accepted by graph AND both set engines
admit (user:alice, viewer, doc:d2) -> True

check(alice, inherited, doc:d1):  oracle=True   graph=False  sets=[True, True]   <== DIVERGES
check(doc:d2, parent,   doc:d1):  oracle=False  graph=False  sets=[False, False] (all agree)
```

**The second line is the diagnosis.** `d2` genuinely is excluded from `parent` by the
`but not` — all four backends agree on that. But `CLAUDE.md` pins the Zanzibar semantics:

> **TTU parents are STORED tupleset tuples**, never computed membership (oracle-pinned
> Zanzibar semantics) … Storage leaves are split from rule-routed leaves for exactly this.

So the TTU must still walk the stored `(d2, parent, d1)` tuple regardless of how `parent`
*evaluates* for `d2`. The oracle and both set engines do. The graph index does not — ~~it
respects the boolean evaluation of the tupleset relation instead of its stored tuples.
Fail-closed (under-grant), so not a security fail-open, but it is a divergence on a rule
this repo states as an explicit invariant, and the storage-leaf split that exists precisely
to honour it is evidently not being applied when the tupleset relation is DERIVED.~~

> ⚠ **EVERY CLAUSE STRUCK ABOVE IS FALSE — see the corrected entry at the top of this
> section.** The graph does NOT evaluate the tupleset's boolean; the storage-leaf split IS
> applied and the write DOES land on a storage leaf; and it is NOT fail-closed — both root
> causes have a fail-open direction. Left in place, struck, because this is the reasoning a
> reader would otherwise have repeated.

~~**Not yet pinned or fixed**~~ — **PINNED 2026-08-10 as `d0010e2`**
(`tests/test_ttu_tupleset_parent_types.py`, 4 red pins + 7 controls); still **not fixed**,
deliberately, so the gate is knowingly RED. The house order was followed: pin RED in its own
commit first so the fix's green is attributable, then fix, then the full phased gate plus a
multi-seed fuzz sweep (it is an algorithm change).

**Relation to 2026-08-09:** different mechanism (that one was a missing crossing middle in
the wildcard bridge; this one is TTU tupleset routing on a derived relation), same shape of
failure — the graph index alone, under-reporting, on a shape no differential corpus
exercised. Two in two days from the same blind spot class is the signal worth acting on:
**shapes that the Lean fragment excludes are exactly where the differential corpora are
thin**, because the corpora were built to feed the model.

---

## 2026-08-09 — ★ the graph index under-reported the OWC x star-parent x TTU cross (answer level). FOUND, ADJUDICATED, FIXED same day.

**Found by** `tests/test_lookup_hypothesis.py::TestLookupSurfaceMachine` on a generated
walk. **Pre-existing** — it reproduces at `6d3c540` with byte-identical Python; the
session that found it changed no `.py` file. **Not previously documented anywhere** (see
"prior art" below). **The gate is RED on `tests-tile:2/4` until it is fixed**; the other
nine phases pass.

**The divergence.** Schema `tests/fga_schemas/owc_star_ttu.fga`, object-wildcard shapes
`{('folder','viewer'), ('doc','viewer')}`, three tuples:

```
(user:u1, editor, folder:f1)    # any tuple that makes folder:f1 exist
(user:u1, viewer, folder:*)     # OBJECT-wildcard grant     -> w_all(folder, viewer)
(folder:*, parent, doc:d1)      # SUBJECT-wildcard tupleset -> w_any(folder, '...')

check(user:u1, viewer, doc:d1):
    oracle = True   set:py = True   set:roaring = True   GRAPH = False
```

Three backends to one, and the oracle is the spec — so the **graph** is wrong. It is a
**false negative** (under-grant): it fails closed, so it is not a security fail-open, but
it breaks the repo's central contract that the two backends have identical semantics.

**Root cause — measured, not inferred.** `index_v4/wildcard.py::_ensure_bridges` only ever
links `w_all(T,p) -> concrete -> w_any(T,p)` through an **interned node of shape `(T,p)`**;
`backfill`'s own docstring says so ("Does not create a w node for a shape that has no
concrete instances"). `tests/oracle.py::instances` witnesses the existential with any
**tuple-mentioned entity of type `T`**, whatever relation mentioned it. Holding everything
else fixed and varying only which relation mentions `folder:f1`:

| witness tuple | interns | oracle | graph |
|---|---|---|---|
| `u9 editor folder:f1` | `folder:f1#editor` | True | **False** |
| `u9 blocked folder:f1` | `folder:f1#blocked` | True | **False** |
| `u9 viewer folder:f1` | `folder:f1#viewer` | True | True |

So the two sides disagree about what satisfies
`wildcard-materialization-spec.md` §3.4's pinned rule — *"'granted on all S' implies
'reaches some S' only if at least one concrete instance of S exists ... which requires a
real concrete in the middle"*. The spec says "instance of S"; **the graph reads that as
"node of shape `(T,p)`", the oracle and the set engine read it as "entity of type `T`",
and that asymmetry is written down nowhere.** Adjudicating which reading is intended is
the first step of any fix — this entry does not presume the graph is the side to change,
only that three of four backends currently disagree with it.

**The pointer for the fix.** The set engine has an explicit, named mechanism for exactly
this composition and the graph has no analogue — `setengine/engine.py:1476-1480`, *"the
star-parent cross for the triple combo owc x star-parent x TTU where NO concrete
`(T, X, r')` is interned"*. `index_v4/core.py` contains zero occurrences of `ttu`.

### ✅ FIXED the same day — the middle tracks the ENTITY (invariant I14)

**Adjudication: the graph is the side to fix**, on three independent readings, none of
which needed a judgement call. (1) §4.1 defines `universe(T)` — the domain of §3.4's
existential — as *entity names appearing in any input tuple*, not "nodes of shape (T,p)".
(2) §3.6 pins "a wildcard grant … is the same row count as granting each instance
explicitly", and granting explicitly answered True while the wildcard answered False, so
the graph violated the spec's own stated equivalence. (3) The graph was
**self-inconsistent under irrelevant data** — an unrelated grant to another principal
flipped the answer. The oracle and both set engines stay untouched.

**The fix**, `index_v4/wildcard.py::WildcardIndex._ensure_entity_middles` /
`::WildcardIndex._sync_entity_middles`, with the property lifted into
`index_v4/invariants.py` as **I14**:

> for every crossable shape `(T, p)` (`SchemaInfo.crossable_shapes` — bridged in AND out)
> and every entity name `x` such that the store holds at least one node `(T, x, *)` that
> is not itself a bridge-only middle, the store holds the node `(T, x, p)` with BOTH
> bridges.

I3 says a concrete of a bridged shape must HAVE its bridges; I14 says the middle must
EXIST while the entity does. Paranoia runs `check_invariants` inside every commit, so a
write path that stops maintaining middles now aborts the first innocent write instead of
silently under-reporting again. **∀⇒∃ stays strict structurally** — a middle can only
exist while its entity does, so there is no counter to drift.

**`_ALLOWED_DIRECT` was NOT relaxed.** The cheap alternative — permit the forbidden
`('all','any')` edge and gate it on an entity count — was considered and rejected: it
converts a structural guarantee into maintained state. (For the record, that direction is
*not* the instance leak; the leak is `w_any → w_all`, and the same-shape cycle it enables
is already compile-rejected. The `('all','any')` prohibition is the ∀⇒∃ collapse plus a
"cannot arise from any tuple" guard, since the position rule makes subject wildcards
`w_any` and object wildcards `w_all`.)

Two subtleties that would have bitten a naive implementation: a middle must **not**
witness its own entity, or the middles keep each other alive as self-sustaining garbage;
and `remove_node` can orphan a **neighbour** entity, so concrete neighbours are captured
before the core removal and re-synced after. Mirrored into `bulk_backfill.py`/`bulk_build.py`
because `tests/test_bulk_build.py` is a byte-identity differential gate.

Cost is confined: `bridged_in_shapes` excludes bare `(T,'...')` shapes, so plain OpenFGA
`[user:*]` usage is never crossable and pays zero middles.

**Sabotage (`docs/sabotage-procedure.md`), the narrowest plausible weakening** —
`_ensure_entity_middles` made a no-op, exactly what a refactor that "simplifies the bridge
code" would do. The degraded store keeps every old bridge so **I3 stays green and only I14
fires**:

```
InvariantViolation: I14: entity folder:f1 exists but its crossing middle
folder:f1#viewer for crossable shape ('folder', 'viewer') is missing
```

Re-run independently on the committed tree: 7 of 10 pinned tests fail under the sabotage,
10/10 pass restored. Gates: `tests/` 773 passed, `formal/conformance` 494 passed.

**★ A third finding: the formal layer could not have caught this, by construction.**
Lean's in-bridge test (`UsStarWrite.lean::Schema.isSubjectWildcardUserset`) keys on a
*literal* `T:*#p` restriction, while Python's `bridged_in_shapes` also folds in
star-tupleset through-shapes. So Lean's crossable set is exactly the set
`_reject_doubly_bridged_shapes` refuses — empty among admissible schemas — and the arm
where the bug lived has no Lean counterpart at all. Filed as a fragment boundary in
`formal/CORRESPONDENCE.md` §7.3.

> **UPDATE 2026-08-14 — the "no Lean counterpart at all" half is no longer true.**
> Part (i) of the `ttuStarFree` lift added `UsStarWrite.lean::Schema.isStarTuplesetThrough`
> (the twin of `derive_schema_info`'s SECOND loop) and made
> `Schema.isSubjectWildcardUserset` the disjunction of both loops, as Python has always
> been. The arm now HAS a Lean counterpart.
> **What has NOT changed, and is the honest reading:** the finding's headline — *the formal
> layer could not have caught this* — still stands for the 2026-08-09 bug, and part (i)
> does not retroactively make it catchable. The new predicate is still **inert on every
> live chain**: `writeRules`/`writeLoggedRules` never call `ensureInBridges`, so nothing
> materializes the edge until part (ii) lands. Read this as "the definition-level gap is
> closed, the machinery-level gap is not".

**★ A fourth: a live comment was refuted.** `zanzibar_utils_v1.py::wildcard_userset_restriction_shapes`
justified its narrowing partly with "…the legal reg11 / `owc_star_ttu` class … whose whole
write space is oracle-correct and unanimous on both backends". That clause was false —
`owc_star_ttu` is exactly where the graph disagreed. The narrowing itself still stands on
its own argument (the F1/F2 danger is a writable userset *subject*, which a through-shape
does not enable); the comment is corrected in situ.

**Pinned deterministically** by `tests/test_owc_star_parent_cross.py` (2 red + 1 green
positive control). It is a positive pin, NOT an xfail, per `CLAUDE.md`. Before that file
existed the shape was reachable by the hypothesis campaign but essentially never drawn
(`max_examples=12`, `stateful_step_count=8`, ~50-tuple pool) — **the gate was green by
seed luck**, which is this repo's named house failure mode (an assurance step that fails
by PASSING). That is a second finding in its own right: *the hypothesis campaign's green
is a sample, not a proof, and nothing in the gate says so.*

**Prior art checked, and none of it covers this** (2026-08-09 sweep):

| item | where | why it does not cover this |
|---|---|---|
| **F1** (graph-incomplete OWC check divergence) | `:1320`, CLOSED `:1336` | a *doubly-bridged* topology, rejected at compile time by `DoublyBridgedShapeError`; this schema compiles fine |
| "all -> any is NOT read semantics, no completeness fix warranted" | `:1360-1367` | decided on an **oracle-False** probe (no concrete in the universe). Here the oracle is **True** because `folder:f1` is in the universe, so it adjudicates the vacuous variant only |
| `ZT-P5` bullet 2 / "Target 3", object wildcards at state level | `:2292`, `HANDOFF.md` | ran this exact fixture, but only for live-vs-rebuild / order / restoration — **never against oracle answers**, so a check-level under-report was invisible to it |
| "zero check-level divergence observed on the object-wildcard corpus" | `formal/FINAL_REVIEW.md:396-403`, `formal/CORRESPONDENCE.md:848-854` | that corpus (`formal/conformance/corpus.py:90-98`) is one type, `define viewer: [user]`, one tuple — no TTU, no star tupleset. The sentence is flagged in situ as a hypothesis; this is the first evidence against it |
| `test_reg5_triple_combo_star_parent_cross_no_concrete` | `tests/test_lookup_oracle.py:1181-1194` | pins the **set engine** on the structural case; the graph is never constructed there |

---

## 2026-07-29c — the hub-topology DoS: store-level quota DECLINED by the user; "bulk rebuild instead" MEASURED and rejected; the async schedule is the answer

**Decision (user, 2026-07-29): no store-level write quota.** *"I don't want to limit
what can be added to a permission store — it might be slow but it should not be
limited by perf."* Board item (A) is closed as DECLINED, not deferred. The decision is
coherent with the codebase's own reasoning: `index_v4/core.py` already exempts removals
from the fan-out cap because "a cap that can refuse a REVOCATION is a fail-open".

**Proposal evaluated instead:** *"if we detect a DoS-causing fan-out, do a bulk rebuild
instead of adding the thing the usual way."*

**Measured** (hub topology, `N/2` users into `group:hub#member` + `N/2` inheriting
groups, SQLite in-memory):

| N tuples | closure rows | sync per-write | async write phase | bulk `build_index` | `SetEngine.rebuild` |
|---:|---:|---:|---:|---:|---:|
| 60 | 960 | 0.53 s | 0.08 s | 0.036 s | 0.0015 s |
| 240 | 14,640 | 7.35 s | 0.65 s | 0.824 s | 0.0084 s |
| 480 | 58,080 | 22.1 s | 1.43 s | 2.65 s | 0.0104 s |
| 960 | 231,360 | 74.0 s | 2.90 s | 10.1 s | 0.0298 s |

Rows are exactly `(N/2)² + N` at every size — **N² confirmed**, and the original
240 → 14,640 finding reproduces verbatim. Peak per-write fan-out at N=240 is **exactly
120**, so `ZANZIBAR_MAX_CLOSURE_FANOUT` is confirmed useless here.

**Verdict: the proposal does not work as stated.** Separating three costs it conflates:

| cost | does a bulk rebuild help? |
|---|---|
| TIME to build | **Yes, 7–15×** — and bulk wins at every size; there is no crossover. |
| closure SIZE | **No.** Row counts are byte-identical in every arm. It is a property of the topology. |
| LOCK HOLD / tail latency | **Worse, decisively.** Total lock-seconds fall 18.0 → 2.7 s, but the worst single stall goes 105 ms → 2,685 ms at N=480 and 237 ms → 10.1 s at N=960. It trades a bounded per-write hold for an O(store) one that grows forever. |

Four independent blockers on top:
1. **The trigger cannot fire.** The only fan-out signal that exists is the per-write
   region size, measured at 120 — the same signal already known not to fire. Detecting
   this needs a *store-level* signal, i.e. the quota that was declined.
2. **`build_index` structurally refuses mid-stream** (verified live: `ValueError:
   index 'inc' already exists (cursor at 14); build_index is for fresh builds`), and
   there is no teardown API anywhere.
3. **It requires quiescence** (`RuntimeError: concurrent writes ... retry when the
   store is quiescent`) — precisely the condition a write burst violates. It also takes
   no store lock at all, so making it safe mid-stream reintroduces the lock problem.
4. **★ The delta outbox loses every REMOVED.** Measured: incremental produced 185
   outbox rows (143 ADDED / 42 REMOVED) on a boolean schema; the rebuild produced 101,
   **100% ADDED, zero REMOVED**. Downstream consumers would never learn a revocation
   happened. **And §8.3 `verify_outbox_deltas` is blind to it** — it checks each pair's
   final action against BFS reachability, so a missing `REMOVED` is never examined.
   In an authorization system this is the fail-open direction.

**The answer that already exists: `ConnectedStore(sync=False)`.** `advance_index` is
NOT unconditionally inline — `store.py::_write` calls it only when `self.sync`.
Measured at N=480: the async write phase is **1.31 s for 480 writes (2.7 ms/write, max
6.6 ms)** against 19.1 s / 105 ms max in sync — a **14.5× drop in write-path latency**,
with the closure work off the write path entirely. Lock-wise strictly better: writers
hold the source lock (`SchemaV4` row), catch-up holds the graph store lock (`StoreV4`
row) — different rows, so on PostgreSQL a catching-up worker does not block writers.
`catch_up(batch=k)` is a direct lock-hold knob (batch=8 → max 733 ms). The consistency
contract already exists and is pinned (`check(at_least=)` falls back to the always-fresh
set engine; `lookup` raises `LookupNotFresh` rather than serve stale enumerations;
`test_connectedstore_async.py::test_async_equals_sync_after_catch_up`). **This bounds
whose latency pays, not total work — which is exactly what "don't limit what can be
stored" asks for.**

Two further options, recorded not adopted: **rebuild-instead-of-applying-K-pending-
deltas** is a sound IVM amortisation with a measured crossover at **K\* ≈ 30–40** for
this store — a better idea than the per-write version and composable with async — but
it inherits blockers 2–4. And **routing hub-like workloads to the set engine** is the
strongest number of all (`rebuild` at N=960: **0.03 s vs 74 s**, zero closure rows),
consistent with `benchmarks/results/M2_FOLLOWUP_2026-07-15.md`. The honest framing:
*the hub topology is not expensive to STORE, it is expensive to materialise the CLOSURE
of — so don't materialise it.*

### Fixed here: the cap misreported itself as corruption through `ConnectedStore`

Found while measuring the above. `AdmissionRejected` subclasses `ValueError`, and
`connectedstore/apply.py::_apply_row` promotes every `ValueError` to
`InvariantViolation('... the log is admission-validated, so this is corruption or a
validity-parity bug ...')`. So a tuned-down cap surfaced as a corruption report — **the
exact opposite of what `index_v4/core.py`'s own raise-site comment says** ("not an
InvariantViolation, because nothing is corrupt"). The two comments contradicted each
other and neither was tested through the composed system (`tests/test_reg17_*` drove
only the raw `ReachabilityIndex`).

Fix: new `ClosureFanoutExceeded(AdmissionRejected)`, raised at the cap site and allowed
to escape `_apply_row`'s promotion. It is the one refusal family admission provably
cannot predict — every other family is a property of the tuple and schema, decided
before the row reaches the log, so promoting *those* is right. The real consequence is
now stated rather than disguised: **the cursor cannot advance past such a row until the
cap is raised.** Does not bite at the 100,000 default; bites the moment anyone follows
the cap's own error message and tunes it down.

Sabotage (remove the escape, re-run `test_cap_through_connectedstore_is_a_refusal_not_a_corruption_report`):
```
E  index_v4.invariants.InvariantViolation: log row 13 (ADD) was rejected by the index --
   the log is admission-validated, so this is corruption or a validity-parity bug:
   closure fan-out cap exceeded: this edge would materialise 12 closure rows ...
```

---

## 2026-07-29b — `_any_residue_reference` / `_keys_referencing` MEASURED (`ZT-P5` bullet 6)

Both are complete `ResidueV1` scans (select every residue row for the store, then
JSON-decode `neg` and `upos` per row) on every node-release path.
`_keys_referencing` became **unconditional** when the N3 leaf-kind elision was
withdrawn as unsound (`ZT-P0-1`, 2026-07-26). It had never been measured; the board
carried it as "unbenchmarked" and it was reachable only from inside a closed item's
residual list.

**Measured** (SQLite in-memory, paranoia off, `base: [user:*] / viewer: base but not
blocked`; residue rows scale with objects):

| residue rows | one scan | µs/row | per-remove (2 blocks/obj) | scan share |
|---|---|---|---|---|
| 25 | 0.35 ms | 14 | 13.1 ms | ~3% |
| 100 | 1.6 ms | 16 | 25.5 ms | ~6% |
| 400 | 6.8 ms | 17 | 26.7 ms | ~25% |
| 800 | 10.1 ms | 13 | — | — |
| 1600 | 22.2 ms | 14 | — | — |

**Verdict: the scan is cleanly O(R) at ~15 µs per residue row** (x1.98 per doubling
at the top end — linear, not worse). It is a *minority* term below ~1–2k residue
rows and becomes the *dominant* term above that; a full churn over R objects turns
quadratic past the crossover. Extrapolating the measured slope, a store with 100k
residue-bearing keys costs **~1.4 s per node release**.

**Scoping, so this is not over-read:** a `ResidueV1` row exists only for a DERIVED
key carrying symbolic star coverage. R is the number of `(object, derived relation)`
pairs with a wildcard grant, not the number of tuples. Stores with no boolean
relations, or with only concrete grants, have R = 0 and pay nothing.

**Not fixed here.** The fix is the one `ZT-P0-1`'s own note named — *"replace the
full `ResidueV1` scan with a real index rather than eliding it"* — i.e. a
node-id-keyed reference table maintained alongside `neg`/`upos`. That is an
algorithm change (gate + multi-seed fuzz + a Lean/CORRESPONDENCE look), not a
measurement, so it is recorded rather than smuggled in.

> **FIXED 2026-08-14** — `ResidueRefV1` landed; see the entry at the top of this file
> for the design, the re-measurement (the new lookup is FLAT in R), and the sabotage
> findings. The numbers in this entry are the *pre-fix* baseline and are kept as such.

**Instrument note, recorded because it is the house failure mode.** The first
*two* versions of this benchmark measured **nothing** and printed a perfectly
plausible table — 0 residue rows, timing only SQLite `SELECT` overhead on an empty
table, with a churn column that looked superlinear and meant nothing. The cause is
a real fact about the system worth writing down: **`neg` records subjects excluded
from a WILDCARD-covered population**, so a schema whose grants are all concrete
produces no residue rows at all (an excluded concrete subject is handled by simply
not writing the edge). It was caught only by adding a non-vacuity assert on the row
count — which is exactly what `docs/sabotage-procedure.md` demands of an
instrument, and which I added only after the first table looked believable.

---

## 2026-07-29 — the P3 edge-multiplicity blind spot, ADJUDICATED and closed

`CORRESPONDENCE.md` §7.2's finding of 2026-07-28 (filed UNADJUDICATED) is resolved.
No backend behaviour changed; the change is to the conformance seam and to two
docstrings that stated a correspondence which does not hold.

**The finding.** The Lean graph model's cascade re-enumerates edges it already holds
(`edgeHolders` reads the edge LIST; `admitEdge` has no presence test; `addEdge` conses),
so a derived edge's multiplicity compounds per cascade leg. Python does not. State-gate
projection **P3 compared edges as a SET**, so the difference was structurally invisible.

**What the investigation actually established** (each measured, not argued):

1. **Python's derived arm is capped at 1 by construction, not by luck.**
   `DeltaProcessor._reconcile_subject` writes a derived edge by a presence DIFF
   (`want_edge and not has_edge`), so re-deriving is a total no-op. Measured: all 18
   processor-written derived rows across `GRAPH_FRAGMENT` are `direct_edge_count == 1`.
   The filed text's "Python dedupes by node id" is true but is not the operative
   mechanism.
2. **The divergence is exactly co-extensive with the derived arm.** Of 171 compared
   edges: 153 untainted-arm agreeing EXACTLY (including `nary_union`'s genuinely
   non-unit 3-arm fan-in, 3 == 3), 18 derived-arm all diverging (Python 1, Lean 4 …
   **1013**). Zero set-level asymmetry — the pre-existing gate was honestly green.
   **The filed `1 → 2 → 4 → 8` understates it**: that is the single-candidate shape.
   > ⚠ **QUALIFIED 2026-08-08 by the `rewriteClosure` dedup leg.** "153 untainted-arm
   > agreeing EXACTLY" was true, and it was true *conditionally on no corpus being
   > reconvergent* — a condition nobody stated, because nothing measured it. The
   > untainted arm ALSO diverged on any schema with two rewrite paths from one tuple
   > to the same key (`lean=2 python=1`); the fragment simply contained no such
   > schema, so "the pre-existing gate was honestly green" meant green-on-the-shapes-
   > it-had rather than green-on-the-property. Two corpora now cover the shape and
   > the model dedupes. Counts in this item are the 2026-07-29 measurement over the
   > then-23-corpus fragment; the live figures are in `FINAL_REVIEW.md`'s generated
   > block. Detail: `formal/CORRESPONDENCE.md` §7.2 item 6,
   > `formal/history/PROOF_STATUS.md` 2026-08-08b.
3. **It is removal-inert**, so there is no modelled fail-open — but by ASSEMBLY, not
   by a theorem: derived edges are retracted only by filter-ALL (`removeEdgePair`),
   and the erase-ONE primitive's targets are untainted under a hypothesis
   `removeGateB` decides at runtime. Recorded as a caveat rather than glossed.
4. **A whole-set multiset compare was assessed and REJECTED.** It fails on 18 of 171
   edges for a declared model artifact and nothing honest makes it green short of a
   multi-session model change. Worse, **it would have reported green if done naively**:
   multiplicity died TWICE, first inside the Lean binary (`Cli.lean::canonJsonArr`
   de-duplicates) and again in the extractor's `set`, so a Python-side `Counter` alone
   would have read all-ones from Lean and compared nothing. That is the sabotage
   procedure's "instrument as broken as the subject" case, found before it bit.

**What landed.** P3 is NARROWED, not dropped:

* `Cli.lean` emits a new `edgeCounts` field (`edgeCountsJson`); `edges` is unchanged.
* `extractor.py::diff_states` compares `direct_edge_count`-weighted multiplicity
  EXACTLY on the untainted arm — in the 23-corpus state gate AND the ~257-store
  enumerated state gate. **This is net-new assurance**: 153 edges' multiplicity had
  never been compared by anything.
* the derived arm is golden-pinned per corpus
  (`formal/conformance/derived_arm_multiplicity.json`,
  `test_derived_arm_multiplicity_ledger`), so the artifact's shape is a checked
  quantity. This **supersedes the E-chain plan's §D.6 hand-probe**.
* the exemption boundary comes from the SCHEMA (`compute_taint`) and is cross-checked
  against `EdgeV4.derived` (`_classify_edges`), so a corrupted flag cannot move it.
* two docstrings corrected: `ReconcileDiff.lean`'s "list multiplicity ==
  `direct_edge_count`" and `Cli.lean`'s dedup justification both asserted a
  correspondence that fails on the derived arm.

**Sabotage evidence** (procedure per `docs/sabotage-procedure.md`; literal output):

| # | sabotaged | observed |
|---|---|---|
| 1a | `Cli.lean` `edgeCountsJson` emits count `1` (i.e. someone reuses the de-duplicating `canonJsonArr`) | `edge MULTIPLICITY (untainted arm, P3) ('user','alice','...','') -> ('doc','d1','any_of',''): lean=1 python=3` + `ANTI-VACUITY: … 18 row(s) (0 with lean multiplicity > 1)` |
| 1b | `extract_sql_state` weights by `1` instead of `direct_edge_count` | same untainted-arm line, `lean=3 python=1`; **exactly one** test fails, `nary_union` |
| 2 | `derived_relations` returns `frozenset()` | `AssertionError: P3 edge classification disagreement (schema taint vs EdgeV4.derived)` |
| 3 | one golden value `13 → 12` | `[boolean_exclusion] user:alice#.../ -> doc:d1#viewer/: golden=[12, 1] observed=[13, 1]` |
| 4 | **subject-side:** drop `_reconcile_subject`'s presence guard (`if want_edge:`) | `PYTHON derived-arm direct_edge_count is no longer uniformly 1: {'nary_union_derived4:…': 4, …, 'two_stratum_cascade:…': 4}` |
| 5 | ledger floor `18 → 19` | `ANTI-VACUITY: … observed 18 row(s) (18 with lean multiplicity > 1); floors are 19/18` |
| 6 | remove `edgeCounts` from `stateJson` | `graph-state output shape unexpected: keys=['edges', 'residues']` |
| 7 | `MIN_CONF_ALL/REST` `465/369 → 466/370` | `FAIL: formal/conformance/ collects only 465 test(s); the gate floor is 466` |

Note sabotage 1b's shape: it fails on **exactly one** corpus, the only one with a
non-unit untainted multiplicity. That is the check having precise content rather than
being a blanket assertion — and it is why `nary_union` must not lose its three-arm
fan-in.

**A near-miss worth recording, because it is the house failure mode pointed at me.**
`diff_states` gained a `tainted` parameter. I first gave it a `None` default with a
docstring saying "used by nothing in the gate" — i.e. a doc warning where the repo's own
procedure demands a mechanical refusal — then made it REQUIRED. That change immediately
exposed a SECOND call site I had missed,
`test_conformance_state.py::test_residue_rich_corpus_is_really_rich`, which had been
silently getting the pre-2026-07-29 set-only comparison. Two lessons, both already in the
house rules and both re-learned the hard way: (1) **the mechanical refusal earned its
keep within minutes** — with the default left in place that call site would have kept
comparing blind, at full green, which is precisely the blind spot this entry closes;
(2) **I did not re-run the suite after the signature change**, so my earlier "all ten
phases green" was true of the tree as it stood when measured and NOT of the tree after
the next edit. Re-run after the last edit, not after the last interesting edit.

**Left open, deliberately.** The faithful model fix is to mirror the presence diff in
`reconcileKeyDR`'s fold guard; it ripples through the edge-characterisation and
settledness stacks and was not attempted. **Do not instead make `admitEdge` reject a
present edge** — that global version breaks the untainted arm, which is load-bearing for
`untOccCount`/erase-one removal and is now checked. A second, opposite untainted-arm
divergence (model `rewriteClosure` does not dedupe where `RuleSet.apply` does) is
recorded in `RemoveOccCount.lean`'s header; **no corpus exercises it today** — all 153
untainted comparisons agree — and the new compare is what would catch it if one did.

---

## 2026-07-07 — P0 recon findings (spec-fact vs repo-fact)

Baseline: **309 passed in 42.12s** (full suite, green, commit `32ebcf4`).
Compile snapshots for all 6 pure-union fixtures captured in
`tests/snapshots/compiled_ruleset/` (boolean fixtures skip until the P7 flip).

Facts verified against the repo, with deviations from the spec text noted:

1. **Count invariant exact form** (spec §2 "match the core's actual count asserts"):
   `indirect_edge_count >= direct_edge_count` and `indirect_edge_count > 0` per
   persisted row (`index_v4/core.py:120-121`); zero-reachability rows are deleted,
   not persisted. I1 uses this form.

2. **`LookupResult` field names** (spec §6 says "concretes"/"markers"): actual fields
   are `node_ids: set[int]` and `markers: set[tuple[str, str, str]]` — markers are
   **3-tuples** `(type, predicate, variant)` with variant ∈ {'any','all'}
   (`index_v4/wildcard.py:26-29`), not 2-tuple shapes. Residue `stars` rendered as
   markers will use variant `'any'` (subject-side coverage). `excluded_node_ids` is
   added in P5 as specced (additive, default empty).

3. **Oracle surface** (spec §8.4 implies parity over lookups): the oracle is
   **check-only** (`tests/oracle.py:318`) — no lookup/lookup_reverse/add/remove; it is
   stateless and rebuilt from the raw-tuple multiset per comparison. ParityEngine
   therefore asserts *check*-parity 3-ways (oracle + set engine + graph) and
   lookup-parity only between the two live engines. This matches the existing matrix
   harness, which also compares checks only.

4. **No backend has `load_schema`** (spec §8.4 lists it in the common op API): every
   backend takes its schema at construction (`SetEngine.__init__`,
   `make_wildcard_index(schema_info)`, `Oracle(schema, tuples)`). ParityEngine keeps
   construction-time schema loading; `load_schema` exists on ParityEngine itself as
   the constructor argument, not as a retrofit onto the backends.

5. **`check` today is ≤4 *separate* SQL point reads**, not one round trip
   (`index_v4/wildcard.py:235-286` → `core.check_reachable_by_id` per probe). The
   single-round-trip consolidation is P5 work as planned, not a present fact.

6. **`backfill()` precedent is idempotent but NOT chunked** (spec §5.5 says "chunked,
   idempotent, mirroring the wildcard backfill precedent"): `wildcard.py:164-189`
   loads each shape's concrete list in one query. The new derived-relation backfill
   will chunk by object node; the *idempotency* pattern (presence-guarded writes) is
   the part actually mirrored.

7. **Filters do not rewrite and are first-match today**
   (`zanzibar_utils_v1.py:259-283`): Filters are pure admission gates (first match
   admits the raw triple, then `break`); all rewriting is Rule-driven and all-match.
   `Filter.rewrite_relation` (spec §3.3) is a new field with default `None`;
   `RuleSet.apply` keeps the existing first-match admission path for pure-union
   relations **unchanged** (byte-identity gate) and adds the all-match fan-in
   expansion only for triples admitted by rewriting Filters.

8. **`.` is currently a legal identifier char everywhere** (`IDENTIFIER_CHARSET`,
   `zanzibar_utils_v1.py:21`), and the DSL parser never runs the write-validators, so
   relation *declarations* are entirely unvalidated today. The §3.2 lexical lock
   ("schema declarations reject `.` in relation names") is enforced at parse time in
   P2 — a new check in the schema parser, not a change to tuple-side validation
   (entity names keep `.`; fixture data like `domain:example.com` stays legal).

9. **Spec-citation numbering in code comments**: existing code cites "spec §N" against
   `wildcard-materialization-spec.md` / `set-engine-spec.md` (per CLAUDE.md, the
   set-engine spec). New code citing the boolean spec says "boolean spec §N" to avoid
   aliasing.

10. **MemberSet fold is module functions, not operators** (spec §5.3 "lift the fold
    rules/table, not the type"): the star fold to lift is exactly
    `a.stars | b.stars` (union), `a.stars & b.stars` (intersection),
    `a.stars - b.stars` (exclusion) — `setengine/memberset.py:115,121,127` — over
    plain `frozenset[tuple[str, str]]`. `neg` is never folded there (it is
    renormalized against interner-backed populations); the processor computes `neg`
    per spec §5.3 step 2 instead. Nothing bitmap/interner-coupled is imported.

11. **`parse_openfga_schema(schema, object_wildcard_shapes=...)` is the compile
    entrypoint** (spec §3.4 calls it `compile_schema(ast, schema_info) ->
    CompiledSchema`). Kept: the existing entrypoint name and pipeline
    (`parse_schema_ast` → `derive_schema_info` → `compile_ruleset`), extended to
    return a `RuleSet` that additionally carries the compiled boolean artifacts
    (namespace map, plans, leaf_owner, dependents, strata). Names adapted to repo
    convention; contents as specced.

---

## 2026-07-07 — P1 (verification foundation)

1. **Paranoia wiring mechanism** (spec §8.1 *(adapt)*): SQLAlchemy session events.
   `index_v4.invariants.install_paranoia(session, store_id, schema_info)` listens on
   `before_commit` (flush + check inside the transaction; `InvariantViolation` aborts
   the commit) and `after_commit` (re-check in a fresh `Session` on the same bind).
   Wired on by default in `tests.wildcard_helpers.make_wildcard_index` — i.e. every
   test that builds a graph store now runs under paranoia (`paranoia=False` opt-out
   for benchmarks and for tests that corrupt state on purpose).

2. **ParityEngine parity scope** (spec §8.4): per-op parity is *check*-parity
   (unanimous accept/reject + full-grid check vs the oracle). `lookup` /
   `lookup_reverse` are served by the richest live backend without per-op
   cross-assertion, because the oracle is check-only (P0 finding #3) and the two live
   engines use different id spaces; lookup correctness stays pinned by its dedicated
   tests and P5 adds the derived-lookup ones. Grid: universe (names seen in applied
   ops) ∪ ghosts ∪ `'*'`, subjects from Direct restrictions, deterministically
   sampled above a cap.

3. **ParityEngine is additive, not a retrofit**: existing matrix/property tests keep
   their own harnesses (they are the pinned artifact P7 flips); ParityEngine drives
   the handwritten scenarios + new random walks, and is the default engine for all
   *new* phase tests going forward. Suite-wide paranoia comes via
   `make_wildcard_index` (see #1).

4. **Façade rejection-family fix** (validity parity, frozen): `WildcardIndex.
   remove_tuple` leaked `KeyError` when an endpoint node never existed, while the set
   engine and `ReachabilityIndex.remove_edge` reject the same op with `ValueError`.
   Surfaced by ParityEngine's unanimity assert; fixed by translating `KeyError` →
   `ValueError('Non-existent edge cannot be removed')` in the façade, matching
   core.remove_edge.

---

## 2026-07-07 — P2 (compile)

1. **⚠ Decision-15 override: derived-tupleset TTUs are SUPPORTED, not rejected.**
   Decision 15 rejects "a `TTU` whose *tupleset* relation is derived", but the §0
   **frozen** acceptance event requires `demorgans_law_1.fga` to flip 4-way — and that
   fixture is built on three such TTUs (`required_by from non_labels`,
   `assigned from matchable_conds`, `granted from matched_roles`). Frozen list beats
   the decision list, so the shape is implemented as a fourth plan-leaf kind,
   `PDerivedTuplesetTTU`: evaluation enumerates candidate parents from the *subject's
   own target edges* plus a residue scan keyed by the tupleset relation — data-bounded,
   never universe-bounded, so the cost-model row ("symbolic write: data-bounded") is
   preserved. New compile artifact `target_feeders` routes deltas on the (possibly
   untainted) target relations into the processor. The decision's underlying fear
   (object-star-shaped parent sets) is real but answerable: ghosts/star-covered parents
   contribute no members under strict ∀⇒∃ because they hold no target tuples.
   **If the rejection was intentional and demorgans_law_1 was meant to stay 3-way,
   say so — the plan-node + feeder wiring is cleanly removable.**

   **Resolved 2026-07-13 — KEEP (owner decision).** Avery confirms the decision-15
   override stands: derived-tupleset-TTU support is retained and `demorgans_law_1`
   stays 4-way (not reverted to 3-way). Consistent with P5 #1 below, which corrected
   this path's semantics (TTU parents are STORED tupleset tuples) rather than removing
   it — the plan-node + feeder wiring stays.

2. **`Filter.rewrite_relation` is a subclass** (`RewriteFilter(Filter)`), not a new
   field on `Filter`: keeps pure-union compile output (and its P0 snapshot reprs)
   byte-identical. Mechanism-only change; behavior as specced (§3.3).

3. **Namespace keys are `(object_type, predicate)`**, not bare predicate strings
   (§3.4 says `dict[predicate_str → Family]`): the same relation name may be tainted
   on one type and plain on another (`demorgans_law_2.fga` declares `_all_users` on
   two types), and node identity in the store is `(type, name, predicate)`. One dict
   hit either way.

4. **Boolean compilation is opt-in until P7** (`parse_openfga_schema(...,
   enable_boolean=False)` default): compile capability lands green in P2 while the
   default path still raises `UnsupportedByGraphIndex`, because a graph backend that
   compiles boolean schemas but has no delta processor yet would answer derived checks
   wrongly (ParityEngine auto-joins the graph on compile success — the P7 seam).
   P7 flips the default and replaces the refusal tests; until then they stay green.

5. **Added scope restriction (beyond decision 15): wildcard userset restrictions over
   derived relations (`[T:*#P]` with P tainted) are rejected** with a loud
   `UnsupportedByGraphIndex`. Star coverage of `T:*#P` composes through *residue*
   stars of every instance, which the leaf-probe star fold cannot see (needs
   symbolic composition through residues — same hook family as object wildcards on
   derived). No fixture or OpenFGA-standard schema uses this shape; the set engine
   still handles such schemas 3-way.

6. **Indexed dispatch preserves list order across buckets** (position-tagged merge),
   so pure-union first-match admission is provably byte-identical; verified by the P0
   snapshot suite plus the unchanged 330 green tests.

7. **Leaf indexes count both closure-leaves and userset storage leaves** in one
   pre-order sequence (§3.2 says "closure-leaf positions"; tainted userset
   restrictions also need a persisted family for their raw tuples, so they draw from
   the same counter — deterministic and collision-free either way).

8. **Derived-dependency cycles raise `ValueError`** (naming the cyclic keys), not
   `UnsupportedByGraphIndex` — §3.4 reserves the latter for decision-15 scope
   rejections. Cyclic boolean schemas stay set-engine-only permanently.

---

## 2026-07-07 — P3 (models + outbox)

1. **Residue `stars`/`neg` are JSON text columns**, not a JSON list + roaring-bitmap
   bytes (§4's sketch): graph node ids are plain autoincrement ints and residues are
   per-object small, so JSON keeps the column debuggable and avoids coupling the graph
   backend to pyroaring. Layout was explicitly *(adapt)*; uniqueness
   (`store_id, object_node_id`), the relation index, and `version` are as specced.

2. **Write-path return type is now `None`** (`add_edge`/`remove_edge`/`remove_node`/
   `add_tuple`/`remove_tuple`): flips go to `DeltaOutboxV1` inside the transaction.
   Back-compat drain: `index_v4.outbox.drain_deltas(session, store, after_id)` +
   `outbox_watermark`. `PermissionDelta` survives as the drained value type.
   Delta-consuming tests migrated to watermark+drain; stream equivalence pinned by
   `tests/test_outbox.py::test_outbox_stream_matches_legacy_flips` (order included).

3. **`EdgeV4.derived` is written by the façade's processor context** (`processor_writes`
   flag → `ReachabilityIndex._writing_derived` around the direct-edge update), set on
   direct-count increase, cleared when the direct count retires. Equivalent to I5's
   "incoming direct edge on a derived-public family" because exclusivity (P2) already
   guarantees only the processor writes those.

4. **Delta-scoped verification cost**: wired into paranoia's `before_commit` (per-
   transaction range from the last committed watermark; BFS over direct edges per
   affected pair). Full suite 60s → 110s with it on everywhere — accepted while
   prerelease per §8.1; `paranoia=False` opts out (benchmarks).

---

## 2026-07-07 — P4 (delta processor)

1. **Outbox rows denormalize their endpoints** (type/name/predicate captured at
   emission): implicit-node GC can delete an endpoint's node row *inside the same
   transaction* (e.g. removing a subject's last tuple), and the §5.2 delta→key mapping
   must still resolve the flip. Ids alone would leave unmappable rows and stale
   residue-neg ids (an id-reuse hazard under SQLite rowid recycling). A delta whose
   subject node is already gone maps to a *full-object* reconcile so the neg recompute
   prunes the dead id.

2. **Derived-public nodes are pinned non-implicit**: they anchor `ResidueV1` rows
   (star-only objects legitimately have residues with zero edges), and implicit GC on
   the last derived edge's removal would orphan the residue.

3. **§5.2 gap fixed — tupleset-tuple deltas**: a new/removed *tupleset* tuple of a
   `PDerivedTTU` (e.g. `doc:d1 parent doc:d2` under `inherited: viewer from parent`)
   changes the parent set but maps to no key under §5.2's enumeration. New compile
   artifact `tupleset_feeders` routes those deltas to the dependent on the same
   object; `target_feeders` also covers mixed-type untainted TTU targets.

4. **Canonical edge representation (order-independence)**: a derived edge exists iff
   eval-true AND NOT star-covered; star-covered subjects are answered exclusively by
   the residue (`neg` iff expr-false). Without the covered-⇒-no-edge half, a subject
   holding transient concrete support kept its edge across op orders that never
   re-audited it, breaking permutation invariance and the "star-only members: zero
   edges" space rule. Same read semantics, deterministic rows.

5. **§5.3 step-2 neg candidates pull the neg sets of ALL derived-leaf kinds**
   (computed, userset, ttu, tupleset-ttu) — exclusions propagate up strata through
   residues; the ttu case is what makes `inherited`'s neg inherit `viewer`'s
   exclusions on the tupleset parent.

6. **No revisit guard needed in the evaluator**: the compiled plans evaluate against
   persisted lower-stratum state only (edge probes + residues) — there is no recursive
   eval path to guard. The §5.3 guard's intent (a corrupted store must fail loudly,
   never spin) is carried by the cascade's quiescence check and the hard-fail cycle
   guard on derived writes (`InvariantViolation`, not a rejection).

7. **Cascade rounds process every mapped key per round** (spec §5.1's own structure),
   ordered by stratum inside a round; residue-version bumps are carried in-memory to
   the next round's key set (they emit no outbox rows). Quiescence is asserted after
   `len(strata)` rounds.

---

## 2026-07-07 — P5 (reads)

1. **⚠ TTU semantics correction (oracle-pinned): parents are STORED tupleset tuples,
   never computed membership.** The oracle's `ttu_leaf` (tests/oracle.py:429) iterates
   raw tuples with `tup.relation == tupleset_rel` — authentic Zanzibar semantics. My
   P4 derived-tupleset-TTU enumerated *computed* members of the derived tupleset,
   which disagreed with the oracle on demorgans_law_1 (caught by the P5 grid-parity
   walk). Consequence: a derived tupleset with no Direct restrictions can hold no
   stored tuples, so its dependent TTUs are constantly empty — exactly the oracle's
   answer (demorgans_law_1's `unmatchable_conds`/`matched_roles`/`matched_users` are
   ∅ by construction; the fixture's live semantics are in `non_labels` and
   `matchable_conds`). This also retro-simplifies the decision-15 override: no
   residue-scan parent enumeration exists; `target_feeders` fan-out uses the entity's
   stored tuples on the tupleset's storage leaves.

2. **Storage leaves are split from routed leaves**: Direct restrictions of a derived
   relation always compile into their OWN leaf (marked `storage=True` on
   PClosureLeaf/LeafSpec/LeafFamily), never merged with Computed/TTU references in
   the same pure subtree. Rule-routed edges on a shared leaf would otherwise be
   indistinguishable from raw stored tuples, corrupting TTU parent sets (the bug the
   grid walk exposed). Affects derived compile only; pure-union output remains
   byte-identical.

3. **`tupleset_parents` uses DIRECT incoming entity edges** on the tupleset node (not
   closure reachability): a member of a granted userset is not a tupleset parent.
   Note: rule-routed members of an *untainted* tupleset relation still count as
   parents (the pre-existing pure-union TTU-rule behavior); the oracle counts raw
   tuples only. No fixture exercises the difference; noted as a latent gap in the
   pure-union path, not introduced here.

   **Resolution (2026-07-13, fixture added — `tests/test_pure_union_ttu.py`).** The
   gap is **unreachable on the graph; closed as benign.** For rule-routed members to
   land on a tupleset node the tupleset relation would need a Computed/TTU arm (a
   rewrite rule only ever lands edges on the relation it *defines*, `_rewrite_rule` /
   `_emit_expr`), but `_validate_ttu_tuplesets` (zanzibar_utils_v1.py) **rejects** any
   untainted tupleset that is not directs-only with `UnsupportedByGraphIndex`. So the
   only untainted tuplesets that compile receive raw stored edges exclusively, and
   `tupleset_parents` cannot see a rule-routed member — the over-granting shape never
   materializes. The fixture pins this three ways: the graph *rejects* the rule-routed
   schema at compile time (both `enable_boolean` paths); the set engine and oracle
   (stored-only) *accept* it and agree it does **not** grant `can_read` through the
   rule-routed `backlink` arm (no over-grant), while a genuinely stored `linked` tuple
   does grant; and on the compilable directs-only sibling all three backends agree
   pointwise. No backend fix was needed — the guard already adjudicates to the
   oracle/Zanzibar stored-parent semantics.

4. **Untainted `check` consolidation counts**: node-id resolution (≤2 concrete
   lookups; w-ids cached) stays separate from the single edge-probe statement
   (`tuple_(subject_id, object_id).in_(keys) ... LIMIT 1`), per the spec's own
   description. The statement-counter test asserts exactly one edge_v4 statement per
   check (zero allowed on a no-key miss).

5. **`lookup_reverse` on derived relations returns the canonical representation**:
   star-covered members appear via markers + `excluded_node_ids` (never enumerated,
   and they hold no edges by the P4 canonical rule); `node_ids` carries only
   uncovered concrete members.

---

## 2026-07-07 — P6 (new-state invariants + backfill)

1. **I7 lineage is per residue ROW**, keyed `(row id, object_node_id)` with absent
   keys pruned each check: empty residues are deleted (spec §4), so a legitimate
   delete-then-recreate restarts at version 1 — the §8.2 wording ("checker keeps
   last-seen versions in memory") tripped on cascades whose intermediate rounds
   emptied a residue that a later round refilled (caught by the demorgans_reverse
   parity walk under paranoia). In-place regressions on a live row still fail.
   Residual corner: SQLite rowid reuse of a just-deleted max-id row for the same
   object could mask one regression — accepted for a prerelease checker.
   *(Correction, review round: this claim was wrong — the corner produced a FALSE
   POSITIVE (a legitimate same-transaction recreate reusing the max rowid would trip
   I7 and abort the commit), not a mask. Fixed: version-1 rows always restart their
   lineage; the residual blind spot is now an in-place regression to exactly 1.)*

2. **I9 wiring**: `audit_fixpoint` (all live keys — the paranoia dose) runs per-op in
   the P5/P7 parity walks and per scenario in the processor tests, not inside every
   `session.commit()` — it needs a processor instance, which the commit hook doesn't
   have; the per-commit paranoia layer covers I1–I7/I10–I12 plus §8.3.

3. **I8**: stratification acyclicity is compile-time (`_stratify` raises); the
   runtime re-assert is the cascade's quiescence check, which fails loudly if the
   strata bound is ever wrong.

4. **Backfill enumerates positive leaf families + the public family** per key
   (subtrahends never generate candidates), chunked and idempotent; residue-only
   objects are covered because derived-public nodes are pinned non-implicit (P4).

---

## 2026-07-07 — P7 (matrix flip — THE ACCEPTANCE EVENT)

**Boolean fixture stores run 4-way** (`boolean_wildcards.fga` in the randomized
matrix; the `demorgans_*` trio pointwise across every relation): graph (delta-
processor-maintained, I9-audited per op) · oracle · set engine under both `SetOps`,
unanimous accept/reject, identical checks over the same grids as before. Suite:
411 passed, 0 skipped.

1. **`enable_boolean` defaults flipped to True** in `compile_ruleset` and
   `parse_openfga_schema`; `enable_boolean=False` keeps the historical refusal
   reachable (one test pins it). Refusal tests replaced with compile-success +
   plan-shape assertions (test_schema_ast, test_zanzibar_utils, test_integration).

2. **Set-engine cycle parity now covers boolean schemas**: `compile_ruleset`
   succeeding means `SetEngine._ruleset` exists, so its flow-graph reproduces the
   graph's raw-write edge set (leaf-routed) and both backends reject the same data
   cycles — required for 4-way unanimity. Schemas the graph still refuses
   (decision-15 scope, cyclic derived deps → the new `except (UnsupportedByGraph
   Index, ValueError)`) degrade to no-cycle-rejection as before.

3. **Derived check with a `'*'` object answers False** without node resolution
   (decision 15: no object-star state can exist on a derived relation) — the grid's
   star-object queries surfaced that `_get_concrete` would otherwise reject the
   reserved name.

4. **Compile snapshots now cover boolean fixtures too** (they compile, so the P0
   golden gate extends to them automatically).

5. **Latent graph-vs-oracle divergence NOT introduced here (pre-existing)**: rule-
   routed members of an *untainted* TTU tupleset count as parents in the graph's
   rewrite semantics but not in the oracle's raw-tuple semantics (P5 entry #3). No
   fixture exercises it; the 4-way matrix pins all shapes that are exercised.

---

## 2026-07-07 — P8 (hypothesis campaign)

1. **The ParityEngine is the machine's oracle**: rather than re-implementing per-op
   assertions, both the property layer and the `RuleBasedStateMachine` drive
   ParityEngines, which already assert unanimity, I12, full-grid oracle parity,
   paranoia (I1–I7/I10/§8.3), and the graph's I9 audit on every accepted op.

2. **Schema strategy**: relations generated in topo order over a fixed `user`/`doc`
   universe with a `parent` tupleset — stratifiable by construction, exactly as §9
   prescribes; cyclic boolean schemas asserted separately as compile rejections.

3. **CI profile**: `max_examples=12`, `stateful_step_count=8`, `deadline=None`
   (each example spins up 3–4 full backends); `HYPOTHESIS_PROFILE=deep` gives
   120/25 for local/nightly runs.

4. **The deep profile found two real bugs** (CI profile was green; §11-P8's "fixes may
   reopen earlier phases" happened exactly as predicted). Both shrunk, triaged, fixed,
   frozen as named regressions:

   * **Pinned public-node leak** (`test_add_then_remove_restores_row_multiset` +
     `test_cascade_replay_from_zero`): derived-public nodes are pinned non-implicit
     (P4, residue anchoring), so add-then-remove left an empty pinned node behind,
     breaking exact row-multiset restoration. Fix: the processor GCs its own public
     node once neither residue nor edges remain (`_gc_public_node`; refcount 0 ⇒ no
     closure rows can reference it). Frozen:
     `test_processor.py::test_regression_public_node_gc_on_add_remove`.
   * **Duplicate-raw-add divergence** (stateful machine): adding the SAME raw tuple
     twice then removing once left the graph's ref-counted edge at count 1 while the
     set engine/oracle (raw tuples are a SET; TupleV1 unique) dropped it — a
     pre-existing pure-union divergence no pool ever exercised (matrix pools filter
     `raw not in present`). The graph core stays ref-counted (two *different* raw
     tuples may rewrite to the same derived edge — counts are load-bearing there);
     idempotence belongs at the raw-tuple API boundary, implemented in
     `ParityEngine._apply`. Frozen:
     `test_parity_engine.py::test_regression_duplicate_raw_add_is_idempotent`.

   Deep-profile status after fixes: all property tests + the stateful machine green
   at `max_examples=120` / `stateful_step_count=25`. Final suite: 425 passed.

## 2026-07-07 — P9 (docs)

README: boolean-operators section rewritten (both backends), rewrite-table rows
updated, memoization-spectrum + cost-model tables reflect derived predicates and the
outbox, new "Booleans in the graph index" section with the honesty notes (write
amplification multiplicative in strata depth; symbolic-write full-object reconcile
cost; TTU stored-tuple semantics; paranoia ~2× suite time), non-goals updated
(boolean-in-graph delivered; async workers/pruning/residue-GC hooks listed).
CLAUDE.md: layout notes for processor/outbox/invariants, compile-layer description,
4-way matrix + ParityEngine + paranoia + hypothesis testing conventions, derived
gotchas, spec pointer now names `graph-boolean-ivm-spec.md` (the earlier two spec
files were removed from the working tree by the author; noted as living in git
history).

---

## 2026-07-07 — connected-store round, S4 (build_index)

**P6 backfill enumeration gap found and fixed** by the built-vs-live equivalence
test: `_live_keys_of` discovered objects via leaf *families* only, so derived
relations with no storage family of their own — TTU-only (`inherited: viewer from
parent`) and computed-only (`approver: viewer`) shapes — were never reconciled by
`backfill()`/`audit_fixpoint` (live maintenance reaches those objects via
dependents-invalidation, so the gap was invisible until an offline build). Fix:
enumeration now follows what non-storage derived leaves *read* — the tupleset-tuple
family for `derived-ttu`, the referenced relation's live keys for
`derived-computed`/`derived-tupleset-ttu` (strictly lower stratum ⇒ recursion
terminates). P6's own backfill test had only closure-leaf relations, which is why it
passed.

---

## 2026-07-07 — connected-store round, S7 (concurrency & stale reads)

Three findings, all product-relevant:

1. **Cursor lost-update**: two concurrent appliers could read the same cursor value
   before either committed and double-apply log rows onto ref-counted state.
   `advance_index` now takes the index store's write lock (`_lock_store`) **before**
   reading the cursor and re-reads it fresh — FOR UPDATE on PostgreSQL/MySQL; on
   SQLite the database write lock + caller retry-on-busy give the same serialization.

2. **W-id cache cached misses**: the wildcard façade cached `None` for absent w
   nodes, invalidated only by the session's own writes — sound single-session, wrong
   for a replica reader (another session creates the w node; the reader's probes
   stay off forever). Misses are no longer cached; positive ids remain safe (a GC'd
   w node had no wildcard state left, so a dead-id probe is correctly False).
   `ConnectedStore.refresh()` is the replica poll API: fresh snapshot + rebuilt
   evaluator + cleared w-id cache.

3. **pysqlite defaults tear snapshots** (the spec §1.8 caveat, met in practice):
   SELECTs run in autocommit, so multi-statement reads straddle commits. The
   concurrency tests install the SQLAlchemy-documented workaround
   (`isolation_level=None` + BEGIN on the `begin` event) and `journal_mode=WAL` —
   snapshot-isolated readers that never block the writer, the honest local
   simulation of primary-write/replica-read.

---

## 2026-07-07 — external review round (triage + fixes)

An external code review raised seven issues; verified against the code, five were
real (two with wrong details), two were by-design/documentation items. All
addressed:

1. **Cross-session freshness-token gap (real, the important one).** The
   `at_least` fallback consulted the set engine's in-memory state, which is only as
   fresh as its last rebuild — a write committed after a reader opened was not
   honored by that reader's tokened reads. (Our own S7 test masked it: the reader
   opened *after* the write.) Fix: `TupleSource.evaluator_watermark` tracks exactly
   what the in-memory evaluator reflects; a tokened read whose token exceeds it
   rebuilds on demand (the honest cost: one rebuild per stale tokened read), and if
   the token is *still* not visible — the session's read snapshot predates the
   write — raises `StaleRead` rather than silently serving stale under an explicit
   freshness demand. Rollback paths reset (not max) the watermark so a discarded
   token can never overstate freshness.

2. **`lag()` materialized every pending row (real).** Now a `SELECT COUNT(*)`.

3. **Pure-union TTU divergence (real, previously logged as latent; now closed).**
   An *untainted* TTU tupleset with computed/rewritten arms would let the graph's
   TTU rule propagate rewrite-derived members that the oracle and set engine
   (stored-tuple semantics) never see. Fix: compile-time rejection
   (`UnsupportedByGraphIndex`, "stored tuples only") — exactly how OpenFGA
   validates its models. Derived (tainted) tuplesets are exempt: their storage
   leaves already isolate raw tuples. Fixture scan confirmed every untainted
   tupleset in the repo is Direct-only, so nothing existing was rejected.

4. **`remove_node` dangling-edge worry (speculative — the counting theorem +
   `_lock_store` + I1's missing-node check cover it).** Hardened anyway with a
   cheap in-transaction post-condition: any edge row still referencing the deleted
   node fails loudly instead of persisting a ghost.

5. **I7 rowid corner (reviewer right, our log wrong).** The corner was a false
   positive, not a mask — corrected above and fixed in code (version-1 lineage
   restart).

6. **Façade multigraph semantics (by design).** `WildcardIndex.add_tuple` is
   deliberately ref-counted (rewrite fan-in requires it: two different raw tuples
   may derive the same edge and must retire independently); set-semantics
   idempotence lives at the raw-tuple boundary (`TupleSource`, harness adapters).
   Now documented loudly on the method itself.

7. **`is_valid_identifier` naming (fair nit).** Docstring now states the sentinels
   (`'*'`, `'...'`) are admitted positionally by `_require`, never by the charset
   predicate.

---

## 2026-07-08 — external review round 2 (triage + fixes)

Two claims; one confirmed, one half-right:

1. **`_find_leaf_node` crash on derived-userset leaves (CONFIRMED).** The helper
   only knew TTU node kinds, so a FULL reconcile of any plan holding a tainted
   userset restriction (`[T#P]` with P derived) died with "plan node not found".
   The reviewer's diagnosis of the blind spot was exact: no fixture places a
   tainted userset inside a plan, and the cheap per-subject path masked the naive
   repro — the trigger is any full reconcile (symbolic delta, dependency
   invalidation, `audit_fixpoint`, `backfill`). Fixed (userset leaves match on
   their storage predicate); the previously-unexercised PDerivedUserset path is
   now covered end-to-end against the oracle, including the three-relation
   invalidation chain (`gblocked` → `member` → `banned` → `viewer`) both ways.

2. **`WildcardIndex.remove_node` missing (half-right).** The quoted "docstring" is
   actually `wildcard-materialization-spec.md` §remove_tuple — a spec-mandated
   façade API that was never implemented; that part stands, and it now exists
   (bridge-strip first, derived-exclusivity guard, KeyError→ValueError parity).
   The claimed SYMPTOM was empirically refuted: core `remove_node` retires bridge
   edge rows fine via the count math (no dangling rows, no post-condition trip).
   The *actual* value of strip-bridges-first, which the review missed: the core's
   node-removal shortcut doesn't decrement neighbour reference counts, so façade-
   level bridge removal keeps w-node refcounts honest and lets an orphaned w node
   be implicit-GC'd instead of lingering with a stale count. (The general
   neighbour-refcount staleness of core `remove_node` is pre-existing and remains
   — noted as a core wart; it affects only GC eagerness, never reachability.)

---

## 2026-07-08 — blind self-audit (7 fresh-context agents; consolidated fixes)

Seven agents audited the code blind (oracle, set engine, graph core, wildcard
façade, processor, schema layer, connected store). Findings triaged to 7 CRITICAL
+ 12 HIGH confirmed; everything below is fixed and pinned in
`tests/test_blind_audit_regressions.py` (plus suite-local additions). Four were
**semantic decisions**, flagged for veto:

**D1 — `'*'`-subject queries are flow-through (SEMANTIC CHANGE).** Live 3-way
divergence: for a star that reaches a relation only *through a granted userset*
(`user:*` member of `group:g`, `g#member` granted viewer), the graph answered True
while oracle + set engine answered False ("per-branch only"). Per-branch was
structurally unimplementable in the graph (the closure cannot distinguish how the
star arrived), and the flow-through reading matches OpenFGA's literal-subject
treatment (`user:*` is a subject like any other; membership composes). Oracle and
set engine now flow through; the graph was already correct. The wildcard spec's
"intensional, per branch" wording (§7) now applies to **object**-side stars only.

**D2/P4 — userset subjects on derived relations are edge-free (`ResidueV1.upos`).**
CRITICAL: a derived EDGE from a userset node (`group:g#member` satisfying the
expression) is transitive — the closure grants every member, silently defeating
each member's own pointwise exclusion (`a but not b` leaked to excluded members).
Boolean membership does not distribute over a userset's members, so it must not be
an edge. New residue column `upos` records true userset memberships
(pos-without-transitivity); check/lookup/lookup_reverse answer userset-shaped
subjects from `upos` ∪ (stars ∖ neg) with no closure probe; reconcile settles
usersets wholesale (step 2c) and audits edges over bare-entity subjects only. I6
extended (upos: live + userset-shaped + uncovered + edge-free + disjoint from neg).

**D3 — userset restrictions in tuplesets rejected (OpenFGA model rule).** A
userset restriction on a tupleset relation bypassed taint analysis entirely and
had drop-the-predicate parent semantics no spec defines. Wildcard restrictions in
tuplesets stay ALLOWED — star tuplesets are this repo's deliberate object-wildcard
extension (w_all machinery, pinned by `test_wildcard_through_from_chain`);
`derive_schema_info` now derives their TTU through-shapes
(`(parent_type, target_rel)`) so the rewritten write resolves on the graph (this
was the oracle-agent's wildcard-tupleset divergence).

**D4 — object-wildcard shapes on TTU targets of tainted plans rejected**
(decision-15 family). Derived evaluation probes the closure directly and cannot
see w_all state, so such a grant would be silently invisible to the plan.

**D4 widened (review 3) — the decision-15-family guards run on the EXPANDED
shape set and cover every TTU position.** `_reject_object_wildcard_scope` runs
twice in `compile_ruleset`: on the declared shapes before plan construction and
again after `_expand_object_wildcard_shapes` closes them over the rewrite rules
(a shape one Computed/TTU hop upstream of a rejected position is the same shape
post-expansion — guarding declared shapes only re-admitted the rejected class,
and the first legal star-object write crashed the delta processor). Newly
rejected alongside the original two: shapes expanding onto compiled leaf
predicates, shapes on the TUPLESET relation of a tainted plan's TTU
(`tupleset_parents` reads direct stored tuples and never consults w_all —
silent wrong denials with no invariant tripping), and star-tupleset
through-shapes landing on a derived TTU target (an underived wildcard userset
over a derived relation; it structurally violated I3). The set engine now
adopts the compiled RuleSet's expanded `SchemaInfo`, so star-object write
admission agrees across backends.

The rest, by area:

* **Memo poisoning under the recursion guard (CRITICAL, oracle + set engine +
  expand).** The revisit guard returns a provisional False, but frames computed
  *while the guard was active* were memoized as final — `reader=True`,
  `editor=True`, `reader and editor=False`, internally inconsistent; and since the
  oracle shared the scheme, the validation matrix was structurally blind to it.
  Fixed with a Tarjan-lowlink-style guard in all three evaluators (memoize a frame
  only if its subtree consulted no in-stack key above it). Both auditor repros
  pinned.
* **Processor:** `_fan_out` called a method deleted in the P5 rework
  (AttributeError on any tainted-target fan-out); `_find_leaf_node` resolved leaves
  by first-match instead of the compile-time binding (wrong-node reconciles) — plans
  now carry `leaf_nodes` zipped to `leaves`; userset-storage deltas with a userset
  subject now force a full reconcile; `userset_check` answers the exact-granted
  userset directly from stored tuples.
* **Graph core:** the node-removal shortcut never decremented neighbour
  reference_counts (the review-2 "wart", upgraded to CRITICAL: it defeats bridge GC
  and `_gc_public_node` under churn) — debits are computed from incident direct
  edges and applied at the tail with the same implicit-GC rule, *after* the
  expansion loops so every REMOVED delta still denormalizes live endpoints (I10).
  New **I13**: `reference_count` == direct-edge degree, checked after I3 (bridges
  are the more specific diagnosis for bridge corruption). `add/remove_edge_by_id`
  re-verify endpoint liveness inside the store lock (TOCTOU); self-edges rejected
  as 1-cycles; `add_edge`/`remove_edge` lock before resolution.
* **Wildcard façade:** the `_w_id` cache returned stale ids across
  rollback/session boundaries — removed (resolve fresh; `_invalidate_w_cache` kept
  as a documented no-op); `remove_node` rejects `name='*'` cleanly.
* **Schema layer:** tokenizer hung on a stray `]` (zero-progress loop) — now a
  ValueError; multi-`#` and empty-predicate restrictions rejected; unrecognized
  schema lines and duplicate type/define blocks rejected; `'.'`-reservation
  enforced on restriction/Computed/TTU references; exclusivity asserts promoted to
  ValueError; single-child union/intersection collapsed (and empty children
  rejected) in `_json_rewrite`.
* **Oracle (O4):** its independent parser had the same stray-`]` hang and silent
  multi-`#` misparse — mirrored fixes (independence contract kept: no production
  imports).
* **Connected store:** `build_index` re-reads the watermark after snapshotting and
  raises on movement (lost-write race); idle `catch_up` rolls back instead of
  pinning its read snapshot (and, on PostgreSQL, holding the store lock) forever;
  the constructor commits its bootstrap so a second session can reopen
  self-describing; ParityEngine catches ValueError too, so cyclic boolean schemas
  degrade to 3-way instead of being unconstructible (X7 — exactly the schema class
  where the memo bug lived); tokens documented as store-local (X6).

Full suite after: 497 passed (18 of them the new regression pins).

---

## 2026-07-12 — lookup-surface oracle gate (`tests/test_lookup_oracle.py`)

Closes the gap logged as P0 recon finding #3 / P1 finding #2: the oracle is
check-only, so `lookup` / `lookup_reverse` / `expand` had **no independent
reference** — ParityEngine serves them from a single "richest live backend"
with no cross-assertion. The new gate composes `oracle.check` over a
schema-derived candidate universe into brute-force reference lookups
(`oracle_lookup(subject, rel, T) = {n | check(subject, rel, T:n)}` and its
reverse) and asserts BOTH backends' lookup surfaces against it after every
accepted op of seeded add/remove walks (drained to the empty store) plus
dense scripted states — **exact (two-sided) where the API is exact, one-sided
where the API drops information by design** (set `lookup_reverse` drops `neg`,
`setengine/engine.py:738-740`). Coverage: `wildcards.fga` (+object wildcards),
`boolean_wildcards.fga`, `demorgans_reverse.fga`. Permanent tamper tests
(leaked id, dropped id, cleared exclusions, dropped neg) prove the checkers
bite. 15 tests: 10 pass + 5 **strict xfails** — the xfails pin GENUINE
divergences (the properties were NOT weakened around them; fix the surface,
then flip the xfail):

1. **X4 — CHECK-level graph divergence on derived-TTU userset subjects (the
   significant one; wider than lookups).** On a derived TTU, userset-shaped
   subjects whose truth flows through a stored tupleset parent answer False
   on the graph index where the oracle AND both set engines answer True. Two
   shapes: (a) the from-chain userset itself — after `doc:d1 parent doc:d2`,
   `check('viewer','doc','d1','inherited','doc','d2')` = graph False / others
   True (the graph's own *untainted* TTU path answers the analogous
   `wildcards.fga` query True via the rewrite edge); (b) cross-object userset
   membership lift — after `group:g1#member editor doc:d2` +
   `doc:d2 parent doc:d1`, `check('member','group','g1','inherited','doc','d1')`
   = graph False / others True, even though the graph answers the `viewer`
   query on `doc:d2` True: the dependent's residue `upos` never receives
   cross-object userset memberships (reconcile settles usersets from the
   object's OWN stored tuples only). Also reproduces on
   `demorgans_reverse.fga`. The matrix/property grids never query userset
   subjects on derived-TTU families, which is why it survived P7. Formal
   scope note: the shape is outside `W4Fragment` (`computedOnly` bans `ttu`
   leaves in derived defs; `PDerivedTTU` was already a documented proof gap),
   so the Lean theorems are untouched — but the repo-wide "identical
   semantics" claim now carries this known, pinned exception
   (`formal/FINAL_REVIEW.md` §3 note) awaiting a fix.
2. **X1 — set forward `lookup` drops TTU-only objects.** Objects reachable
   ONLY via TTU whose `(type, name, relation)` key was never interned are
   silently missing (`engine.py:753`: the candidate universe is interned keys
   only) where set-engine spec §6.4 prescribes reverse propagation including
   TTU. The graph returns them.
3. **X2 — graph `lookup_reverse` on a derived relation with `o_name='*'`
   raises `ValueError`** (the `_get_concrete` → `core.node` reserved-name
   guard) where `check` answers False (P7 #3) and the set engine returns
   empty — an inconsistent refusal, not a wrong grant.
4. **X3 — set `expand`/`lookup_reverse` cannot represent an oracle-true
   uninterned from-chain userset subject** (no interned id exists; `check`
   answers it True via the from-chain rule, and the graph returns its node).
   Representational, not evaluative.

---

## 2026-07-13 — set-engine lookup completeness (X1 + X3 fixed)

Both set-engine entries from the 2026-07-12 gate are fixed and their strict
xfails flipped to plain regression pins (`tests/test_lookup_oracle.py`); the
gate's S1/S3/S4 properties are now **exact two-sided over the whole candidate
grid** (the one-sided uninterned escapes were removed, not relaxed).

1. **X1 root cause**: `SetEngine.lookup`'s candidate universe was the interned
   keys, and an object reachable only through TTU (or a Computed hop over
   another relation's stored tuples) never interns its own
   `(type, name, relation)` key — no id existed to return. **Fix (spec
   set-engine §6.4 reverse propagation, mechanism adapted)**: reverse
   propagation is realized at WRITE time instead of per-lookup. Compile-time
   tables (`_candidate_reverse_deps`) invert the schema: for each stored tuple
   of relation `r` on `(T, n)`, `_apply_add` also interns `(T, n, R)` for every
   relation `R` on `T` that reaches `r` through Computed chains or holds a TTU
   over tupleset `r` (any TTU-derived membership implies exactly such a stored
   tuple on the object — TTU parents are stored tuples, P5 #1). All expression
   positions count (subtrahends included): over-approximate candidates are
   pruned by lookup's check-verification. `_apply_remove` releases
   symmetrically, so interner refcounts stay balanced, `rebuild()` replays
   identically (conformance `driven == rebuilt` fingerprints re-verified, incl.
   full-churn drain-to-empty), and reads remain side-effect-free. Forward
   `lookup` markers are now intensional and exact by construction: one
   star-object `check` per **declared** relation (instead of per interned star
   key), so star coverage arriving through Computed/TTU hops surfaces as a
   marker. Cost: lookup stays a check semi-join, `O(declared relations +
   interned relation keys)` checks; interner growth is linear in stored tuples
   (× schema-bounded fan-out), never universe-bounded.

2. **X3 adjudication: fixable, not representational.** The missing piece was
   only the id: `ttu_expand` already emitted the from-chain userset when its id
   existed (`singleton_entity(fid)`). The same write-time pass interns the
   from-chain userset key `(subject_type, subject_name, target_rel)` for every
   stored tupleset tuple with a bare concrete subject (star parents stay
   symbolic via `stars`; userset-shaped parents are D3-rejected), so
   `expand`/`lookup_reverse` now carry it in `pos`. No read-time interning, ids
   stay recycled-int32, the `(type, name, predicate)` key remains the
   surrogate.

   Population note: pre-interned keys join `ids_of_shape[(T, rel)]`, so a
   `[T:*#rel]` star's extensional population can now include from-chain-only
   usersets — strictly more faithful (their exclusions become representable in
   `neg`); no fixture stars a shape that pre-interning feeds.

---

## 2026-07-13 — graph derived-TTU userset subjects (X4 + X2 fixed)

Both graph entries from the 2026-07-12 gate are fixed and their strict xfails
flipped to plain regression pins (`tests/test_lookup_oracle.py`); the walks no
longer skip any (subject, object) pair (`_make_derived_ttu_userset_gap`
removed) and derived `'*'`-object reverse lookups are asserted like every
other object. The repo-wide "identical semantics" claim no longer carries the
X4 exception.

1. **X4 root cause (both shapes).** The boolean spec is **silent** on
   userset-shaped subjects flowing through a derived TTU's stored parents —
   §5.3/§6 define residues over closure-leaf state and same-object usersets
   only; the oracle (`ttu_leaf`) is the pin. (a) *From-chain*: the plan
   evaluator's `ttu_check`/`tupleset_ttu_check` never implemented the
   from-chain identity rule (a stored tupleset parent `p` makes `p#target_rel`
   itself a member — exactly what the untainted path materializes as the
   rewrite edge), and no reconcile step enumerated the from-chain keys.
   (b) *Cross-object lift*: userset memberships of a tainted TTU target are
   edge-free (`upos`, P4), so the dependent's audit set — built from closure
   reverse lookups on the parents' public nodes — could never see them.
   **Fix (processor only)**: `ttu_check`/`tupleset_ttu_check` gain the
   identity rule; `reconcile` gains a from-chain pass (step 2a: keys per
   stored parent, both polarities, interning a subject node ONLY when the
   outcome must be recorded — upos: true∧uncovered, neg: false∧covered; the
   other two outcomes are already exact via stars) and `_leaf_concretes`
   lifts the tainted targets' residue `upos` members into the audit.
   Cross-object recordings are not edge-justified on the recording object, so
   two lifecycle pieces close the id-liveness loop: `_gc_public_node` keeps a
   node that another residue's `neg`/`upos` still references (and the new
   `_gc_subject_node` collects dropped anchor nodes symmetrically, keeping
   add-then-remove a row-multiset round trip), and `_map_deltas_to_keys`
   full-reconciles every residue referencing a subject node GC'd in the
   transaction. Read paths unchanged — `check`/`lookup`/`lookup_reverse`
   answer userset subjects from the (now complete) residue exactly as before.
   Formal scope: derived-TTU shapes are outside `W4Fragment` (`computedOnly`),
   and every new processor path is gated on `derived-ttu`/`derived-tupleset-ttu`
   leaf kinds or on states (cross-residue references of dead/ref-0 nodes) that
   in-fragment runs never reach; the state-level conformance gate (exact
   edge+residue equality vs Lean) stayed green unchanged.

   Residual THEORETICAL note (recorded, not observed): if a from-chain TARGET
   were an untainted subject-wildcard-bridged shape with grants already sitting
   in its `w_any`, interning a from-chain subject node mid-cascade could create
   new bridge-fed truth and so require extra cascade rounds. No
   currently-compilable schema class reaches this shape, and if one ever did it
   fails LOUD — the cascade-quiescence check raises `InvariantViolation` —
   never silently wrong.

   > **SUPERSEDED 2026-07-26 — the *reachability* half is DISPROVED by a structural
   > route; the *loud-failure* half is NOT contradicted.** A `derived-ttu` leaf
   > needs only SOME parent type tainted (`_is_pure` false), but `_from_chain_keys`
   > enumerates **all** stored parents — so a parent of a DIFFERENT type whose
   > `target_rel` is UNTAINTED and wildcard-bridged reaches exactly the excluded
   > shape; "no currently-compilable schema class reaches this shape" is false.
   > (A second route: `derived-tupleset-ttu`, where the TUPLESET itself is tainted,
   > leaves the target unconstrained outright.) The "fails LOUD" half stands as the
   > actual safety property: 400 randomized trials (88 reaching a fresh
   > untainted+bridged from-chain intern) produced 0 admission/answer/invariant
   > problems across 3 seeds — a hypothesis, not a proof (not established for
   > intersection-rooted grant relations, no bounded search over >2 strata). See
   > `## 2026-07-26 — ZT-P5 …` (Target 2) at the end of this file and
   > `tests/test_zt_p5_readjudication.py::test_zt_p5_from_chain_target_shape_IS_reachable`.

2. **X2**: `lookup_reverse` on a derived relation with `o_name='*'` now
   short-circuits to the empty result before node resolution (decision 15: no
   object-star state can exist), matching `check`'s False (P7 #3) and the set
   engine's empty result instead of raising through the reserved-name guard.

Grid widening (regression cover beyond the lookup gate): `_boolean_grid` adds
the `doc#viewer` from-chain subjects, and the De Morgan grid derives every TTU
from-chain userset shape from the AST (`_from_chain_userset_subjects`), so the
matrix now queries userset subjects on derived-TTU families after every op.

---

## 2026-07-13 — FIXED: self-referential TTU-parent add/remove state non-restoration (answer-benign)

**Status: FIXED 2026-07-13** (`index_v4/processor.py` reconcile step 2a; regression
`tests/test_self_referential_tuples.py`). Found by the hypothesis campaign
(`tests/test_hypothesis.py::test_add_then_remove_restores_row_multiset`); a
falsifying example was discovered and persisted to the (gitignored) `.hypothesis/`
DB. Pre-existing — reproduced on a clean tree; not introduced by the surrounding
session's work.

**Self-referential tuples ARE supported** (OpenFGA `IsSelfDefining`; the
self-defining / attribute-marker idiom — `document:1#viewer@document:1#viewer`, or
a `resource:r1 activated resource:r1` flag). The bug was a canonicalization drift,
not an evaluation error, so the fix keeps accepting them (does NOT reject).

**Shape.** A self-referential tupleset tuple `doc:d1 parent doc:d1` (d1 is its own
`parent`) present in the store, a derived intersection `r0: [user] and [user]`, and
a TTU that reads it back on the same object `r4: r0 from parent or [user, user:*]`.
Adding then removing `u1 r0 d1` does **not** restore the materialized state.

**Symptom (answer-benign).** After the add/remove: `check` is CORRECT on every
query (`check(u1,r0,d1)` and `check(u1,r4,d1)` both False, matching the oracle),
and `DeltaProcessor.audit_fixpoint()` PASSES — the ending state is a valid
fixpoint. What drifts is a single NODE row (`snapshot_rows`): the node
`(r0, doc, d1)` ends with `implicit=False` where the before-state and a fresh
add-only build have `implicit=True`, both at `reference_count=0`. So it is a
refcount-0 node left un-GC'd with a stale `implicit` flag on the remove path — the
"node GC" representation class the formal state gate deliberately projects out
(`extractor.py` P5). It violates the repo's canonical-representation *uniqueness*
guarantee (add/remove exact-state restoration), which `test_add_then_remove_...`
pins, but does NOT affect answers, the fixpoint, or any check-level parity.

**Root cause.** By node keying `(predicate, type, name)`, the object's own derived
node `(r0, doc, d1)` is the SAME node as the from-chain userset subject `doc:d1#r0`
that the self-referential TTU records in `r4@d1`'s residue `upos` (X4a from-chain
rule). That node therefore plays two roles: a derived-public node (pinned
`implicit=False` while it holds an edge) AND a recorded from-chain subject (kept
alive by the `upos` reference). Reconcile step 2a interned the from-chain subject
node with the DEFAULT `implicit=True`, so a fresh build created it implicit; but on
the add path it had first held r0's derived edge, which promoted it to explicit
(`implicit=False`, and "explicit is sticky", `core.py:284-287`). Add-then-remove
thus ended explicit where a fresh build was implicit — a one-node canonical-form
divergence. Answers were never affected (the read path resolves the from-chain
identity directly; `audit_fixpoint` passed). Note the graph's closure-cycle
rejection (`core.py:319-342`, T4 acyclicity) does not catch this: `parent` tuples
are tupleset/entity edges consumed by the TTU rule, not closure self-loops.

**Fix (allow, don't reject).** From-chain subject nodes are now interned
**NON-implicit** in reconcile step 2a (`processor.py`): a recorded subject must
survive on its `upos`/`neg` reference alone and be collected only by
`_gc_subject_node` (step 5) — an implicit one would be premature-GC'd and dangle
the reference. Both the incremental and fresh-build paths now intern it explicit,
so add/remove is again an exact row-multiset round trip. Rejecting self-referential
tuples was NOT chosen: OpenFGA supports them and they have real use (the flag
pattern above).

**Formal scope:** unaffected. Derived-TTU shapes are outside `W4Fragment`; the
Lean chain is add-only (no remove legs); and the state-level conformance gate
projects the node-GC class out (P5). No theorem, gate, or bound is touched.

---

## 2026-07-15 — set-engine lookup completeness ×2 + accept/reject parity (star tuplesets)

Three pre-existing set-engine divergences, all on states combining star tupleset
parents (`[T, T:*]`) with TTU chains — a constellation NO prior corpus built. The
first was found by the N17 design review (a `check`-recursion vs walk-hop audit),
the other two by N17's new fuzz artifacts on their first runs. All fixed
2026-07-15 (`setengine/engine.py`), landed with N17; the graph index and oracle
were never wrong — these are set-engine-only surface/admission bugs.

1. **Walk drops downstream objects behind a STAR bare parent (H3 gap).** A stored
   star parent tuple `Q:q ts T:*` makes every tuple-mentioned instance of `T` a
   parent of `Q:q` (`ttu_leaf`'s ∀⇒∃ star branch), but `_reverse_neighbors`' H3
   hop folded only the CONCRETE bare sibling — so a subject confirmed on
   `(T, X, rel)` never hopped to `(Q, q, R)`. `check` said True (engine AND
   oracle), `lookup` dropped the object, no marker covered it — an S4 violation
   live on any walked schema with a star-able tupleset. **Fix:** H3 also folds the
   star bare sibling `(t, '*', '...')` through the same `member_of × _ttu_map`
   cross. Pinned: `test_reg1_star_bare_parent_from_chain` + the `owc_star_ttu`
   corpus gates.

2. **Walk seed empty for uninterned from-chain star-identity subjects.** A userset
   subject `T:X#r` (ghost, or the `*` shape itself) is a member of every object
   with a stored `T`/`T:*` tupleset parent whose TTU targets `r` (`ttu_leaf`'s
   identity branches) — with NO stored tuple at the subject key, so the old
   interned-id seed (and its star-sentinel fallback) produced nothing. Found by
   the walk≡sweep differential on its first run, oracle-confirmed. **Fix:** the
   seed is addressed by SHAPE (`_reverse_neighbors_key`); H2/H3 need only the
   bare siblings interned, not the subject node.

3. **Accept/reject divergence: routed same-shape wildcard self-reference.** A
   same-type star parent `folder:* parent folder:f2` routes (TTU-rewrite
   through-shape) to `folder:*#viewer viewer folder:f2`, which the graph rejects
   by construction (bridge-before-grant: the object's in-bridge to the star
   userset node + the grant edge = two-cycle; `index_v4/wildcard.py`'s reworded
   cycle error). The set engine's §1.5 same-shape check only saw the RAW tuple
   (bare subject) and its flow graph carries only RuleSet-derived edges, never
   the materialized bridges — so it ACCEPTED. Found by the seed-7 hypothesis
   sweep over the new corpus (`_Gate` unanimity assert). **Fix:** the same-shape
   wildcard self-reference test now also runs over every DERIVED pair
   (`_would_cycle`), guarded by the through-shape's presence in
   `subject_wildcard_shapes` (always true for routed stars — the D3 derivation —
   so it never blocks a pair the graph accepts). Pinned:
   `test_reg9_same_type_star_parent_accept_reject_parity` (both backends reject
   same-type, both accept cross-type).

   **Known residual — NOW FIXED (2026-07-16, see the dated entry at the end of this
   file).** The multi-hop version turned out to be *constructible* after all (the
   "no current corpus" claim was true only of the existing fuzz pool, not of
   reachability): a 3-relation schema + 2 writes builds it. The flow graph is now
   bridge-aware and rejects it, restoring accept/reject parity.

**Formal scope:** unaffected. Forward `lookup` is unmodeled (CORRESPONDENCE §8.1
N17 entry); set-engine write admission is unmodeled (`GraphAdmission` mirrors the
GRAPH's admission, unchanged); conformance corpora contain no star tupleset
parents, and all three verify.sh phases re-ran green.

---

## 2026-07-16 — bridge-aware set-engine admission (the "Known residual" §3 above, FIXED)

**What.** The multi-hop star-bridge accept/reject divergence documented as the
"Known residual" in §3 (set engine accepts a bridge-mediated cycle the graph
rejects) was believed unbuildable ("no current corpus/pool can build it"). It is
**buildable** — a minimal red repro (pinned as
`tests/test_lookup_oracle.py::test_reg10_multihop_star_bridge_cycle_accept_reject_parity`):

```
type folder
  relations
    define parent: [folder, folder:*]
    define admin:  [user, folder:*#admin, folder#viewer]
    define viewer: [user] or admin from parent
```
writes `folder:* parent folder:c` then `folder:c#viewer admin folder:y`. The graph
rejects the 2nd (cycle `(folder,c,viewer) → (folder,y,admin) →[in-bridge] w_any(folder,admin)
→[rule] (folder,c,viewer)`); the set engine's flow graph carried the two rule edges
but not the materialized in-bridge, so it accepted. `ParityEngine` fires.

**Fix (set engine only — `setengine/engine.py`).** The write-time cycle check
(`_flow_reaches` / `_would_cycle`) is now **bridge-aware**, mirroring
`index_v4/wildcard.py` `_ensure_bridges`: concrete `(T,x,p)` → `w_any(T,p)` for
`bridged_in_shapes`, and `w_all(T,p)` → concrete for `bridged_out_shapes`, with
`w_any`/`w_all` kept **distinct** (flow-graph star nodes are position-tagged 4-tuples
`(T,'*',p,'any'|'all')`) so an in-bridge and an out-bridge on the same shape can't fuse
into a spurious path. Bridges are computed virtually during traversal (no new state, no
DB reads); an OUT-bridge shape→concrete index is maintained only when the schema
declares object wildcards. Both `SetOps` now reject the repro, matching the graph.

**Fix direction rationale.** The graph's exact path-counting closure fundamentally
requires an acyclic routed graph; its admission is the authoritative acyclicity gate,
and Lean's `GraphAdmission` models *it*. The set engine must mirror that gate (reject),
not the other way round — so **no Lean change** (set-engine write admission is unmodeled;
the graph/Lean side already rejected). Verified: full `pytest tests/` (544+24), all three
`verify.sh` phases (lean + conf 68+195), and a 6-seed hypothesis fuzz sweep — all green.

**Residual (hardening follow-up, not a divergence).** The fuzzer's schema generator
still can't *build* this shape class (that's why the bug hid); `test_reg10` pins the
instance. Teaching the generator to emit star-tupleset-parent + self-referential-userset
shapes would fuzz the class — filed in `HANDOFF.md` backlog.

*(subsequent phases append below)*

## 2026-07-16 — star-bridge fuzzer generator + out-bridge regression (reg11); two new latent OWC divergences filed

**What (hardening, the follow-up above, DONE).** Closed the fuzzer blind spot that let the
reg10 bug hide. Two additions:
- `tests/test_lookup_oracle.py::test_reg11_out_bridge_object_wildcard_self_cycle_accept_reject_parity`
  — the **object-wildcard / OUT-bridge analog of reg10**. Where reg10 closes a cycle through
  a subject-wildcard IN-bridge (concrete→`w_any`), reg11 closes one through an object-wildcard
  OUT-bridge (`w_all`→concrete): `folder:a parent folder:*` (with `(folder,parent)` and
  `(folder,viewer)` object-wildcard shapes) routes via the `viewer from parent` TTU to
  `folder:a#viewer → folder:*#viewer`, and the `w_all(folder,viewer) → folder:a#viewer`
  out-bridge closes the two-cycle. Both backends reject; blinding `bridged_out_shapes` to
  empty flips the set engine to *accept* (the pre-fix divergence), so reg11 gives real
  coverage to the OUT-bridge branch of the fix (reg10 exercises only the IN-bridge branch).
  **Only this single-hop out-bridge self-cycle is realizable**: any derived edge into
  `w_all(T,p)` is minted by a `T:x <tupleset> T:*` write whose own subject is a same-shape
  concrete `T:x#p`, which the out-bridge immediately reaches back — so such a write always
  self-cycles at admission and can never persist for a later write to build a longer loop on.
  The multi-hop generalization of reg10 is therefore **unreachable** in the out-bridge
  direction (verified: `folder:b parent folder:a` then `folder:a parent folder:*` is still
  rejected on the second write, both backends).

  > **SUPERSEDED 2026-07-26 — DISPROVED by repro; the "unreachable" argument was an
  > artefact of this test's own self-referential TTU.** With a TTU whose TARGET
  > differs from its HEAD (`viewer: [user] or admin from parent`, the reg10 shape —
  > not reg11's own `viewer: … or viewer from parent`), `folder:a parent folder:*`
  > is **ACCEPTED and PERSISTS** on both backends, and a later
  > `folder:a#viewer admin folder:a` closes the genuine multi-hop out-bridge loop,
  > rejected by both — parity holds, but the reachability claim above does not: it
  > was true only of reg11's own self-referential schema, not of the out-bridge
  > direction in general. See `## 2026-07-26 — ZT-P5 …` (Target 1) at the end of
  > this file and
  > `tests/test_zt_p5_readjudication.py::test_zt_p5_reg11_multihop_out_bridge_IS_reachable`.
  > The same re-adjudication also found a NEW accept/reject divergence on this
  > schema family (a `folder:* parent folder:*` write: graph-accepted / set-rejected,
  > then detonating on a later innocent write) — filed strict-xfail there, not fixed;
  > see the ZT-P5 entry's "★ NEW DIVERGENCE" section rather than duplicating it here.
- `tests/test_hypothesis.py` — a dedicated **star-bridge schema generator** (`star_bridge_configs`
  + `_star_bridge_pool`) emitting the `parent:[T,T:*]` / `A:[user,T:*#A,T#B]` /
  `B:[user] or A from parent` class the stock `schema_asts` cannot build, plus a deterministic
  pin and a `StarBridgeParityMachine` (order-dependent admission fuzzing through a 4-way
  ParityEngine). Authoring check: blinding the set engine's bridge awareness makes both fire
  the reg10 accept/reject disagreement, confirming the class is now actually fuzzed.

**Two NEW latent divergences surfaced by the generator (NOT chased — out of scope; filed).**
Both require an **object wildcard on the relation that also carries the `T:*#A`
wildcard-userset restriction** (i.e. `(T, A) ∈ object_wildcard_shapes`) — a pathological
config where the `T:*` star node plays both the object-wildcard and the subject-userset role.
This is an orthogonal axis to the star-bridge *cycle* class, so the generator draws OWC only
over `{(T,'parent'), (T, B)}` and these stay unexercised by the committed fuzzer. Minimal repros:
- **F1 (graph incomplete — check divergence).** Schema `viewer:[user,folder:*#viewer,folder#admin]`,
  `admin:[user] or viewer from parent`; OWC `{(folder,parent),(folder,viewer)}`; writes
  `folder:* parent folder:*` then `folder:x#admin viewer folder:*`. Then
  `check(folder:x#admin, admin, folder:x)` = **graph `False`, set + oracle `True`** — the graph
  misses a membership routed through the double-wildcard (`folder:* parent folder:*`) parent.
- **F2 (graph over-permissive — accept/reject divergence).** Schema
  `admin:[user,folder:*#admin,folder#viewer]`; OWC `{(folder,admin)}`; write
  `folder:*#admin admin folder:*` = **graph accepts, set rejects** (the reg9 same-shape
  wildcard self-reference, but with the wildcard *object* — the graph's cycle check doesn't
  catch it when the object is itself `T:*`). Set (rejecting) matches the reg9 semantics.

These are genuinely exotic OWC-on-self-referential-userset-relation corners (OpenFGA does not
support wildcard usersets at all), consistent with the "latent/theoretical, no corpus forces
it" class — **do not chase speculatively**; filed in the HANDOFF backlog for triage. F1 is a
graph *completeness* gap (graph vs oracle), so if either is ever prioritized, F1 first.

## 2026-07-17 — F1/F2 CLOSED by compile-time scope rejection (doubly-bridged shapes)

**What.** The two latent OWC divergences filed 2026-07-16 (F1 graph-incomplete, F2
graph-over-permissive) are **closed** by a new compile-time scope rejection — the THIRD
entry in the decision-15 scope-rejection family (alongside object wildcards on derived
relations and wildcard usersets over derived relations). Both F1 and F2 need a
**doubly-bridged shape**: a shape `(T,p)` that is simultaneously a **literal
wildcard-userset restriction** `T:*#p` in the schema AND an **object-wildcard shape**
(declared or compiler-propagated through a TTU head). When such a shape exists, a wildcard
write materializes a `w_any(T,p) → w_all(T,p)` path in the graph closure; every
present-or-future concrete node of that shape carries both bridges (concrete→`w_any`
in-bridge, `w_all`→concrete out-bridge), so the path is a **latent cycle**.

**New findings recorded en route (not in the original F1/F2 filing).**

- **(a) Detonation — a THIRD divergence.** Both F1 and F2 states lock out *innocent*
  concrete writes. After the wildcard write is graph-accepted, the graph's
  `_ensure_bridges` closes the `w_any → … → w_all` cycle; every later plain concrete
  write of the doubly-bridged shape is then permanently graph-**REJECTED** while the set
  engine and oracle accept it (verified: F1's `folder:* parent folder:*` + `folder:x#admin
  viewer folder:*`, then an innocent `user:v viewer folder:q` is graph-rejected; F2's
  `folder:*#admin admin folder:*`, then `user:v admin folder:y` graph-rejected). This is
  the decisive reason the state must be made **unconstructible**, not papered over at read
  time: the ref-counted closure cannot host the data cycle at all.

- **(b) "all → any" is NOT read semantics (no completeness fix warranted).** We checked
  whether F1's missing membership was a genuine read-path gap ("`p` of ALL `T` ⊆ the
  wildcard userset `T:*#p`", i.e. all→any). It is not: an **acyclic cross-type probe**
  (`user:u member group:*` + `group:*#member viewer folder:z`) answers **False on all four
  backends** (graph, both set ops, oracle) — the oracle does not read all→any either. So
  the F1 "graph False vs set/oracle True" was an artifact of the *cyclic* doubly-bridged
  topology, not a real completeness rule the graph was missing. No read-path change made.

- **(c) Decision rationale — compile rejection over a write-time ghost-hop gate.** Zero
  spec pressure: OpenFGA supports **neither** wildcard usersets (`[group:*#member]`) **nor**
  object-wildcard tuple objects (`folder:*` in a tuple's object field), so this corner is
  doubly out of spec. OpenFGA/Zanzibar tolerate *data* cycles at read time, but that is
  fundamentally incompatible with our ref-counted transitive-closure materialization — our
  write/compile-time acyclicity strictness is the standing documented deviation, and this
  is one more instance of it. A write-time gate (reg9/reg10/reg11-style admission check)
  was considered and rejected as unnecessarily complex given the above.

**Precision of the criterion (empirical correction to the original framing).** The
precondition was first framed as `bridged_in_shapes ∩ bridged_out_shapes ≠ ∅`. That is
**too coarse** and over-rejects the legal reg11 class: `bridged_in_shapes` also carries
**star-tupleset through-shapes** (reg11's `(folder,viewer)`, derived from `[folder:*]` on
the TTU tupleset `parent`), which are NOT writable usersets and cannot mint a persistent
`w_any` node — reg11's dangerous writes self-cycle and are rejected on both backends, so
nothing detonates.

> ⚠ **PARTLY FALSE — corrected 2026-07-26 (ZT-P5-NEW).** The clause "cannot mint a
> persistent `w_any` node … so nothing detonates" is **wrong**. On reg11's OWN schema a
> single `folder:* parent folder:*` write mints exactly such a node: the routed edge is
> `w_any(folder,viewer) → w_all(folder,viewer)`, two DISTINCT `node_v4` rows under the
> position-split encoding, so it is not a self-loop and the cycle check never fires. It
> was graph-ACCEPTED / set-REJECTED, and it **did** detonate — every later innocent
> concrete `viewer` grant was permanently graph-rejected while the oracle said it should
> hold, with I1–I13 green throughout.
>
> What survives is the NARROWER reading, which is the part that actually justifies the
> narrowing: a through-shape cannot make the danger a property of the **schema**, so it
> does not belong in a **compile-time** criterion — nothing more. That distinction is
> load-bearing: the dangerous schema IS reg11's schema (character-identical to
> `REG11_SCHEMA`, same OWC set after expansion), so any compile-time rejection would
> reject the legal reg11 / `owc_star_ttu` class wholesale.
>
> The fix is therefore a **write-time** rejection, not a schema rejection:
> `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge` refuses a routed
> `w_any(T,p) → w_all(T,p)` edge when the shape is in `bridged_in ∩ bridged_out` — a
> cycle by construction, since bridges are schematic, so every present and future
> concrete `T:x#p` closes `w_any → w_all → concrete → w_any`. This is the position-split
> restatement of a rule the set engine already had (`_would_cycle`'s raw-level
> `u == v` on the UNSPLIT node key), so the two backends now implement one rule in two
> representations rather than two rules that happened to agree. See the 2026-07-26 ZT-P5
> entry. The implemented left factor is therefore the set of **literal `T:*#p`
restriction shapes** (`wildcard_userset_restriction_shapes(ast)`), a strict subset of
`bridged_in_shapes`. Verified empirically: reg11's coarse intersection is non-empty but its
literal-restriction intersection is empty (legal); the shared `CANON_SCHEMA` used by
`test_wildcard`/`test_integration` (`viewer:[user:*,user,folder:*#viewer] …` **with** an
object-wildcard on `viewer`) IS genuinely doubly-bridged and **did** exhibit the F2
accept/reject divergence (`folder:x#viewer viewer folder:*` graph-accepted, set-rejected) —
those three tests were migrated to drop the superfluous, never-exercised OWC.

**Fix (both backends, symmetric).** `zanzibar_utils_v1.py`:
- New `DoublyBridgedShapeError(UnsupportedByGraphIndex)` — its OWN type so the set engine
  can single it out (the other scope rejections the set engine *swallows* into an
  oracle-only/ruleset-less mode; this one it must **re-raise**, so both backends reject
  identically — the state is unconstructible everywhere, not merely graph-incomplete).
- `_reject_doubly_bridged_shapes(ast, schema_info)` raises it when
  `wildcard_userset_restriction_shapes(ast) ∩ bridged_out_shapes ≠ ∅`, run in
  `compile_ruleset` **after** `_expand_object_wildcard_shapes` (so it catches the
  propagation-derived intersection — the P3 case, where `viewer` is never *declared* an
  object wildcard but the compiler propagates it onto the OWC set through the `viewer from
  parent` TTU head).
- `setengine/engine.py` re-raises `DoublyBridgedShapeError` (instead of swallowing it with
  the other `UnsupportedByGraphIndex` scope rejections). Because the compiler runs
  expansion internally, this also covers the P3 propagation case the set engine's own
  *unexpanded* `schema_info` would miss.

**(d) Safeguard (defense-in-depth, always-on, never fires).** `setengine/engine.py`
`_flow_reaches` gains a **ghost hop**: at a `w_all(T,p)` node whose shape is doubly-bridged
(`self.doubly_bridged`, computed once from the literal-restriction ∩ object-wildcard set),
it ALSO steps `w_all(T,p) → w_any(T,p)` — the virtual composition of the out-bridge and the
in-bridge through any present-or-future concrete of the shape — closing the F1/F2 latent
cycle at write time so set/graph admission stay in parity. **Post-rejection this hop is
unreachable** (`self.doubly_bridged` is always empty for any constructible engine); a
`self._ghost_hop_fired` flag (init `False`) flips only if the compile gate is
bypassed/regressed, and `test_reg12_ghost_hop_never_fires_on_legal_star_bridges` asserts it
never fires on the legal reg10/reg11 star-bridge sequences. A mirror-side note (no assert,
since the precise check needs the AST) documents the same in `index_v4/wildcard.py`
`WildcardIndex.__init__`.

**Regression pins** (`tests/test_lookup_oracle.py`, the reg12 block): F1 + F2 rejected on
**both** backends at construction; the **propagation-derived** case (constructible —
verified: expansion adds `(folder,viewer)` to the OWC set the user never declared, both
backends reject); negative controls (reg10 no-OWC + reg11 with-OWC still compile, their
literal-restriction ∩ object-wildcard set empty, existing reg10/reg11 parity tests still
green); and the ghost-hop never-fires flag.

**Formal scope:** unaffected. This change only NARROWS the admissible schema space (a new
compile rejection); no modeled algorithm changes (`GraphState.admitEdge` untouched). Logged
under the `GraphAccepts` row in `CORRESPONDENCE.md §3` alongside the other two scope
rejections. `pytest tests/` green (576, +6 reg12) and the hypothesis smoke (14) re-ran
green; the phased `verify.sh` gate is the orchestrator's to run after integration.

## 2026-07-17 — fuzzer blind-spot hardening (generator coverage: booleans × wildcards/
usersets/bridges) + two OPEN divergences filed

**What.** A blind-spot audit found the two schema generators disjoint on the axis where
every historical bug lived: `tests/test_hypothesis.py::schema_asts` fuzzed booleans but only
bare `user`/`user:*` subjects, while `star_bridge_configs` fuzzed wildcards/usersets/bridges
but was provably pure-union — so the PRODUCT (booleans × wildcards/usersets/bridges) was
covered only by handwritten pins. Test-only change (NO backend/Lean change); generators
hardened across six items:

- **G2 — concrete usersets in `schema_asts`** (`schema_asts` `expr`): the leaf strategy now
  optionally emits a CONCRETE userset `[doc#r_k]` over an earlier (possibly derived)
  relation. When `r_k` is tainted this compiles to a `PDerivedUserset` and drives the
  `ResidueV1.upos` / `_find_leaf_node` reconcile paths (2× historical CRITICALs found by
  review, not fuzzing — 2026-07-08 D2, review-2 #1). `_op_pool` already routes the userset
  subject-predicate writes. Deterministic pin: `test_pderived_userset_add_remove_
  deterministic_pin`.
- **D4 — explicit `check` rule** added to `StarBridgeParityMachine` (and the new boolean
  machine): the machines relied on ParityEngine's post-write grid parity, which SAMPLES the
  grid (cap 150); a drawn check asserts cross-backend equality on a query of the harness's
  choosing.
- **G1 — booleans × star-bridge** (`bool_star_bridge_configs` + `BoolStarBridgeParityMachine`
  + `test_bool_star_bridge_deterministic_pin`): crosses the star-bridge template with a
  boolean arm on `B` (`([user] or A from parent) but not blk`). A draw that compiles runs a
  ParityEngine (3-way when a boolean `B` drops the graph via owc-on-derived, else 4-way); a
  draw that rejects is asserted consistent per each backend's contract (reusing ParityEngine's
  own behavior). Also WIDENED `star_bridge_configs`' OWC domain to include `(T, A)` — the
  previously-excluded F1/F2 axis — now asserting configs whose OWC hits the literal-userset
  intersection raise `DoublyBridgedShapeError` on both backends and are skipped, all others
  proceed as before. Ghost-hop never-fires asserted in every machine teardown that reaches a
  SetEngine.
- **G5 — `rebuild` + `remove_node`**: a low-frequency `rebuild_sets` rule (set-engine replay
  from `TupleV1`, spec §6.5, asserting post-rebuild grid equality) added to both machines. A
  `remove_node` PARITY rule was NOT added — the set engine has no node-level removal, so it
  cannot fan out through ParityEngine without a set-engine API change (declined per the
  no-forced-API-change instruction); remove_node + I13 (the 2026-07-08 refcount CRITICAL) is
  instead pinned on the graph surface that exists by `test_graph_remove_node_invariants_and_
  answers` (invariants I1–I13 + answers vs an oracle over the remaining tuples).
- **Item 4a — OWC propagation through a Computed hop** (`test_owc_propagates_through_computed_
  hop`): an object-wildcard shape on `w` propagates through `v: w` onto `(doc, v)` (the
  type-agnostic wildcard-relation branch of `_expand_object_wildcard_shapes`); an object-star
  write on `w` is accepted unanimously and the grant flows through `v`. Not a doubly-bridged
  landing (`v` is Computed — no writable `doc:*#v`), so it compiles.
- **G4 — lookup-surface gate over GENERATED schemas** (`test_lookup_oracle_gate_generated_
  schemas`): the `_Gate` two-sided lookup/lookup_reverse/expand battery, previously only 5
  handwritten fixtures, now runs over drawn `schema_asts` schemas (low example count — the
  brute-force oracle reference is expensive; deep-aware cap).

**Exclusion scope for the G2 userset leaf (empirically calibrated by the deep hunt).** When
`r_k` is tainted, the userset `[doc#r_k]` makes a schema carry userset-shaped subjects
(`doc:X#r_k`) over a derived relation — which trips TWO pre-existing graph behaviours the deep
hunt surfaced: (i) the answer-benign implicit-flag CANONICAL DRIFT (a derived object node
doubling as a self-referential userset subject) breaks the exact-state-equality property of
`test_cascade_replay_from_zero` / `test_permutation_invariance` / `test_add_then_remove_
restores_row_multiset`; (ii) the userset-subject-through-derived COMPLETENESS GAP breaks the
check/lookup parity of `ParityMachine` / the G4 gate. Because the *valuable* case (userset over
a TAINTED relation) is exactly what trips both, `allow_usersets` is made OPT-IN (default OFF):
- OFF (the default) in every BACKEND-driven consumer: the three state-restoration tests,
  `ParityMachine`, and the G4 gate (which also uses `ttu_in_boolean=False`).
- ON only in `test_parser_round_trip_generated` (pure parse/unparse of userset restrictions —
  no backend, so neither gap can bite).
- The PDerivedUserset reconcile WRITE path (`upos` / `_find_leaf_node`) — G2's real value — is
  covered DETERMINISTICALLY by `test_pderived_userset_add_remove_deterministic_pin` instead.
  Userset LOOKUP surfaces remain pinned by the handwritten fixture gates (wildcards/boolean/
  demorgans, which carry usersets and pass) + the X4 regression pins. Net: G2's achievement is
  finding the three gaps below; live random userset fuzzing over derived schemas is blocked by
  them (can't leave a strict-xfail-per-example on a random generator), so it is excluded and
  the gaps are filed.

**THREE OPEN/latent divergences surfaced by the new generators — FILED not fixed** (per the
fuzzer-hardening failure protocol: file a minimal repro as a strict xfail, exclude the
offending class from the generator with a dated comment, keep the suite GREEN; do NOT change
backend code). All pinned by strict `xfail(strict=True)` tests that xpass-alert when the
underlying gap is closed:

1. **Answer-benign implicit-flag canonical drift (PDerivedUserset path)** —
   `test_hypothesis.py::test_pderived_userset_self_ref_cascade_replay_drift`. Surfaced by G2
   in `test_cascade_replay_from_zero`. Schema: derived `r0` (intersection), `r1` with a
   concrete userset over r0 (`[doc#r0]`), TTU `r4: r0 from parent`; writes `doc:d1 parent
   doc:d1` (self-ref) + `doc:d1#r0 r1 doc:d1`. Node `(r0, doc, d1)` is BOTH r0's derived-public
   node AND the userset subject `doc:d1#r0`; the live cascade gives it a transient r0 edge
   (promoted `implicit=False`, "explicit is sticky"), where bulk replay-from-zero interns it
   fresh at `implicit=True`. States differ by that ONE flag only — **answer-benign** (both
   builds answer every check identically and match the oracle, both pass `audit_fixpoint`).
   Exactly the class the 2026-07-13 self-referential-TTU entry FIXED for the from-chain path,
   here in the PDerivedUserset path (unfixed). Excluded from `test_cascade_replay_from_zero`
   only (via `schema_asts(allow_usersets=False)` — the one test comparing incremental vs bulk
   CANONICAL state); usersets stay ON in every other consumer (they fuzz ANSWER correctness,
   which this drift never touches).

2. **Graph from-chain-identity completeness gap through a Computed alias of a boolean TTU
   arm (X4 family, OPEN)** — `test_lookup_oracle.py::test_graph_from_chain_userset_through_
   boolean_ttu_arm`. Surfaced by G4. After `doc:d1 parent doc:d1`, with `r1: (r0 from parent)
   and (r0 from parent)` and `r2: r1`, `check('r0','doc','d1','r2','doc','d1')` = **graph
   False / set engines + oracle True** — an answer-level completeness gap (the graph denies a
   real grant). The X4a from-chain identity rule (2026-07-13) IS applied for a bare
   derived-TTU, through a Computed alias over a whole-definition TTU, and for the boolean `r1`
   queried directly (all verified graph-True); it fails ONLY on the combination of a Computed
   alias reading a boolean relation whose arm is a DIRECT TTU. A graph *completeness* gap
   (graph vs oracle), same family as X4.

3. **Graph userset-subject-through-derived completeness gap (wildcard variant; X4/D2/upos
   family, OPEN)** — `test_lookup_oracle.py::test_graph_userset_subject_through_derived_
   wildcard_gap`. Surfaced by the deep `ParityMachine` hunt (the G2 userset leaf expanded
   ParityEngine's grid to CHECK userset subjects on derived relations). With `r0` a
   wildcard/exclusion relation, `r1: r0 or ([user] or [doc#r0])` (so `doc:d1#r0` can be STORED
   on r1), and `r3: r1 but not [doc#r1] or [doc#r1]`, after the shown writes
   `check('r0','doc','d1','r3','doc','d2')` = **graph False / set engines + oracle True** — the
   graph does not lift `r1`'s userset-subject membership into the dependent `r3`. The complex
   `r0` (a `user:*` / nested-exclusion arm) is LOAD-BEARING (`r0: [user]` is graph-correct), so
   this is the userset-subject × wildcard × derived interaction — the edge-free `upos` (D2) /
   X4 family (userset memberships on derived relations). State-dependent (the write ORDER
   matters; hypothesis could not shrink it), so pinned as-is with the deterministic
   3-relation / 3-write repro. This is the divergence the usersets-off exclusion above avoids.

**Formal scope:** unaffected — test-only; no modeled algorithm or schema-admission change.
All three OPEN/latent gaps are outside `W4Fragment` (from-chain-through-boolean, userset-
subject-through-derived `upos`, and PDerivedUserset node-GC canonical form are already-
documented proof gaps). `pytest tests/test_hypothesis.py tests/test_lookup_oracle.py` green;
full `pytest tests/` green; a `HYPOTHESIS_PROFILE=deep` hunt on the new generators drove the
exclusion calibration above (the star-bridge/boolean machines + the state-restoration
consumers ran clean at 120 examples; the userset-subject CHECK gap on generated derived
schemas is the excluded-and-filed class).

---

## 2026-07-17 — FIXED: graph silently dropped no-restriction-match writes (accept/reject parity)

**Status: FIXED** (`zanzibar_utils_v1.py` `RuleSet.apply`; regression `tests/test_lookup_oracle.py`
reg13 block; test update `tests/test_wildcard_schema.py::test_concrete_filter_rejects_wildcard_tuple`).

**Scout report.** On `boolean_wildcards`-shaped schemas the write `group:*#member editor doc:d1`
— tuple subject `group:*#member` (a WILDCARD-userset subject) against a CONCRETE `[group#member]`
restriction — was **accepted by the graph backend and rejected by the set engine** (a reg9-family
accept/reject / unanimity break).

**Reproduced, and found BROADER than reported.** The divergence is a **general** graph-admission
wart, not specific to wildcard usersets. The graph's raw-write routing `RuleSet.apply` had a
pure-union `else: return` branch that **silently dropped** any raw tuple matching no declared type
restriction, so the direct-drive graph harnesses (`GraphBackend`/`_GraphSide`) reported `True`
having written nothing — a **vacuous accept**. The set engine's `_validate` step 2 (`if not
any(f.apply(triple) for f in self.filters): raise ValueError`) rejects the same tuple. Confirmed
divergent for the whole class: wrong subject type (`doc:x#foo editor`), wrong userset predicate
(`group:g#admin editor`), a bare write to a userset-only shape, a nonexistent relation
(`user:alice bogus doc:d1`), and the reported `group:*#member` case. Note the **derived-family**
branch of `RuleSet.apply` already RAISED on no-match; only the pure-union branch dropped silently.

**Which layer.** Graph: `RuleSet.apply` (pure-union no-match → silent `return`). Set engine:
`SetEngine._validate` step 2 → `ValueError`. `validate_write_identifiers` (charset only) is not
involved. In the PRODUCTION composed path the divergence never manifests: `connectedstore.TupleSource`
uses the SET ENGINE as the admission validator, so a no-match tuple is rejected before it ever
reaches `RuleSet.apply` / `advance_index` — the wart lived only in the standalone graph test
harnesses (`GraphBackend`, `_GraphSide`) that drive the graph without that gate.

**Adjudication (evidence, not assumption): set engine's rejection is right; graph should reject.**
(1) OpenFGA rejects a tuple matching no type restriction. (2) The admitted state materializes
NOTHING on the graph — `RuleSet.apply` yields 0 routed triples, 0 stored rows, and every
downstream `check` is False on ALL backends (graph, both set ops, oracle). So this is a pure
accept/reject wart, NOT a completeness gap, and NOT "the graph legitimately materializes state"
(removal/GC unaffected) — squarely the "clean admission-gate change" case, not the file-and-pin case.

**Fix (`RuleSet.apply`, one branch).** The pure-union no-match branch now RAISES `ValueError`
("matches no declared type restriction") instead of silently returning — mirroring the
derived-family branch directly above it and the set engine. **Scoped to schema-derived rulesets**
(`self.schema_info is not None`, always set by `parse_openfga_schema`): a hand-built `RuleSet([...])`
used as a pure filter/rewrite engine (schema_info None — tests only; no production construction, no
set-engine counterpart) keeps the historical silent-drop filtering semantics. The production
`advance_index` already treats any `ruleset.apply` ValueError as a hard corruption signal
(`InvariantViolation`), and production tuples are set-engine-admitted, so the new raise can only
fire there on genuine corruption — exactly the intended behavior.

**Regression pins** (`tests/test_lookup_oracle.py` reg13 block): the reported wildcard-userset case
+ the general no-match variants rejected on both backends; valid writes still accepted; the declared
`[group:*#member]` shape still accepted on both (reg10/reg11 bridged-in family UNCHANGED); plain
`user:*` sentinel behavior unchanged (accepted under `[user:*]`, rejected without). Updated
`test_concrete_filter_rejects_wildcard_tuple` to assert the loud reject (was pinning the silent
drop) — the test's stated intent ("[user] must keep rejecting a user:* tuple") is preserved and
strengthened.

**Formal scope:** unaffected. This only NARROWS admissible raw writes (a stricter admission gate);
no modeled algorithm changes. The graph's acyclicity/admission model (`GraphAccepts` /
`GraphAdmission`) is untouched — matching-no-restriction was never a modeled accept.

---

## 2026-07-17 — FIXED: the three OPEN 2026-07-17 divergences CLOSED (+ a 4th found en route)

**Status: FIXED** (`index_v4/processor.py`, `index_v4/bulk_backfill.py`, `index_v4/invariants.py`).
The three OPEN/latent divergences filed earlier today (the "fuzzer blind-spot hardening" entry
above) were root-caused and fixed — no longer file-and-pin, now closed with the strict xfails
flipped to plain regression pins. A **4th** divergence in the same family surfaced during
root-causing (previously unfiled) and is pinned too. The fixes are two independent processor
changes (Fix A — answer-level; Fix B — answer-benign canonical form), each mirrored into the
bulk backfill so built-vs-live equivalence holds. (The reg13 admission wart found by a scout in
the same session is its own entry directly above — cross-referenced here, not duplicated.)

### Fix A — audit-set `upos` lift for `derived-computed` / `derived-userset` leaves (both answer-level gaps)

**Root cause.** `DeltaProcessor._leaf_concretes` (the reconcile audit-set builder) lifted a
referenced tainted relation's residue `upos` (edge-free userset-shaped memberships, P4/D2) into
the audit set **only** for the `derived-ttu` / `derived-tupleset-ttu` leaf kinds — the X4b lift
landed 2026-07-13. The `derived-computed` and `derived-userset` branches pulled only
edge-justified incoming concretes off the closure, never the referenced relation's `upos`. (The
`neg` side was already lifted for **all** derived kinds via `_derived_leaf_neg_ids`; only the
positive `upos` side was asymmetric.) So a userset-shaped member recorded *only* in a referenced
relation's `upos` was invisible to any dependent whose leaf is a Computed alias or a concrete
userset over that relation; the dependent's residue stayed incomplete and `_check_derived`
answered **False** where the oracle + both set engines answer **True** — a graph *completeness*
gap (denies a real grant), same family as X4.

**Fix (`_leaf_concretes`, `derived-computed` + `derived-userset` branches; `_ttu_target_upos_nodes`
helper).** Both branches now lift the referenced relation's residue `upos` members into the audit
set — the direct analog of the X4b TTU lift. **Safety:** the lift only *widens* the candidate set;
membership is still decided by `plan.check_fn` (evaluation), so it cannot over-grant, and it reads
strictly-lower-stratum residues (no new cascade rounds, no quiescence risk). Mirrored into
`index_v4/bulk_backfill.py` (same two branches) so bulk build sees the same members. Closes:
- **xfail #2** `test_lookup_oracle.py::test_graph_from_chain_userset_through_boolean_ttu_arm` —
  flipped to a plain regression pin.
- **xfail #3** `test_lookup_oracle.py::test_graph_userset_subject_through_derived_wildcard_gap` —
  flipped to a plain pin.
- **NEW 4th divergence** (found by a planning probe, previously unfiled): a userset member of a
  granted userset **over a derived relation**. With `r0: [user] and [user]`, `r1: [user] or
  [doc#r0]`, `r3: [user] or [doc#r1]` and the writes `doc:d1#r0 → r1 @ dx`, `doc:dx#r1 → r3 @ dy`,
  `check(doc:d1#r0, r3, dy)` was graph **False** / oracle + both set engines **True** in **both**
  write orders. Pinned: `test_lookup_oracle.py::test_graph_userset_member_through_granted_userset_over_derived`.

### Fix B — state-functional `implicit` flag (the answer-benign canonical drift, divergence #1)

**Root cause (canonical drift, answer-benign).** Reconcile step 2a interned a recorded from-chain /
userset subject node with `implicit=False` **only when the node did not already exist**. A
pre-existing raw-endpoint node (default `implicit=True`) that then got recorded into a residue
`neg`/`upos` stayed `implicit=True` on the live path, while a bulk replay-from-zero interned it
fresh — order-dependent flag → live-vs-bulk canonical-form drift by exactly one node's `implicit`
bit. Answers, `audit_fixpoint`, and every check-parity were unaffected (this is the
2026-07-13 self-referential-TTU drift's analog in the PDerivedUserset path). Convergence direction
is forced *explicit* (core's "explicit is sticky" forbids demotion in the write path;
`_write_derived` / `_store_residue` pin explicit as edges transit).

**Fix — make the flag state-functional** (invariant target: a node is `implicit=False` ⟺ it owns a
residue row **∨** is referenced by any residue's `neg`/`upos` **∨** is an active derived-public node
with an incoming direct edge). Two symmetric halves:
- **promote-on-record** — new reconcile **step 2d** in `_reconcile` (plus the cheap
  `_reconcile_subject` path): every userset-shaped node still `implicit` in `neg | upos` is
  sticky-promoted to explicit. **Bare-entity ids are deliberately excluded** — their canonical
  convergence still relies on the existing implicit-GC + full-reconcile-prune dance (P4 #1), so
  the promote guard is `predicate != '...'` and `wildcard == ''`.
- **demote-on-release** — new `_demote_released_node` (+ helpers `_has_incoming_direct_edge`,
  `_any_residue_reference`) wired into the *survive* paths of `_gc_subject_node` /
  `_gc_public_node`. This is a **DELIBERATE, documented exception to core's "explicit is sticky"
  rule**, and it is *necessary*: promote-only reintroduces the drift one op later (hysteresis — a
  node recorded then un-recorded that survives on an unrelated reference would stay stuck explicit
  where a fresh build interns it implicit). On release, a node is demoted back to `implicit=True`
  unless a canonical explicit-reason still holds (owns a residue row, is referenced by any residue,
  or is a derived-public node holding an incoming direct edge).
- **N3 subtlety (worth recording).** The `_cross_object_recordings_possible` (N3) elision makes
  the fast `_residue_references` scan see only *cross-object* recordings — that is safe for the
  DELETE decision (refcount keeps the node alive regardless) but **wrong for the DEMOTE decision**,
  which must not miss a same-object reference. Hence the separate complete-scan `_any_residue_reference`
  used only on the demote path.
  > **SUPERSEDED 2026-07-26 — and the parenthetical above is exactly the false premise.**
  > "Safe for the DELETE decision (refcount keeps the node alive regardless)" is **wrong**:
  > `closure` leaves resolve candidates through the transitive closure, so they record
  > subjects that hold NO edge on the recording object, and refcount does *not* keep those
  > alive. That is a reproduced authorization escalation (ZT-P0-1) — see the 2026-07-26 entry
  > at the end of this file. `_cross_object_recordings_possible` and
  > `_RESIDUE_LOCAL_LEAF_KINDS` no longer exist; `_keys_referencing` always scans, so it and
  > `_any_residue_reference` are now identical in extension and survive as separate names only
  > because one gates deletion and the other demotion.
- **I6 extended** (`invariants.py`): userset-shaped `neg` subjects (`predicate != '...'`) and **all**
  `upos` subjects must be `implicit == False`. Tamper pin: `tests/test_invariants_derived.py::test_i6_upos_userset_implicit_bites`.
- **Bulk mirror**: `bulk_backfill.py` mirrors promote-on-record (no demote leg — a from-scratch
  build is state-functional by construction; an un-recorded node is simply never promoted). The
  built-vs-live equivalence suites stay green.
- Flipped **xfail #1** `test_hypothesis.py::test_pderived_userset_self_ref_cascade_replay_drift` to
  a plain regression pin. Both halves are covered end-to-end by the new
  `tests/test_self_referential_tuples.py::test_pderived_recording_promote_demote_hysteresis`.
- **Code-health note (scout observation, not a bug).** The `sp != '...'` userset branch of
  `_reconcile_subject` appears effectively unreachable in practice (userset-storage deltas force a
  full `_reconcile` rather than the cheap subject path), so its promote logic is belt-and-braces —
  correct if ever reached, but not exercised by the current write routing.

  *Resolution (2026-07-17, verified — the hedge made precise).* The branch is genuinely
  unreachable from the cascade, its sole caller. `_map_deltas_to_keys` routes every
  userset-subject delta on a `'userset-storage'` leaf to a full reconcile (blind-audit P3),
  and the only other `LeafFamily` kind, `'closure'`, cannot receive a userset-subject flip:
  its stored subjects are bare, and bare (`'...'`) nodes have no incoming edges (objects
  always carry a relation predicate; bridges target relation-predicated nodes), so no
  transitive userset path into a closure leaf exists. Kept correct-if-reached (not converted
  to an assert) as belt-and-braces against future routing changes; the argument is now also
  a comment at the branch itself (`processor.py::_reconcile_subject`).

### reg13 — cross-reference (not duplicated)

The graph vacuous-accept admission wart in `zanzibar_utils_v1.py::RuleSet.apply` (pure-union no-match
branch silently dropped a raw tuple where the set engine raises) was found by a scout in this same
session and is written up in its own dated entry directly above ("graph silently dropped
no-restriction-match writes"). It is a unanimity wart, not a completeness gap (0 rows materialized),
production-unexposed (`TupleSource` admits via the set engine first), and the fix narrows accepted
writes (raise, scoped to schema-derived rulesets).

### Scout campaign (recorded as evidence — no further findings)

Two read-only scouts swept for MORE gaps after the fixes: **(1) read/enumeration symmetry** —
`lookup` / `lookup_reverse` / `expand` / `_check_derived` / stars-folds / backfill enumeration
audited against oracle-composed references: **no further silent graph≠oracle omission** (it also
confirmed the X4-family fixes live). **(2) delta/fan-out/lifecycle** — ~3,800 randomized
remove-heavy sequences over 9 targeted schemas (cross-object userset fan-out, computed-chain
quiescence, from-chain removal, wildcard-mediated `target_feeders`, GC races, removal-order
permutations on the new lift sources): live ≡ replay-from-zero ≡ oracle throughout, `audit_fixpoint`
+ paranoia green; **zero confirmed findings**. The only code-health observation is the effectively
unreachable `_reconcile_subject` userset branch noted under Fix B.

### Fuzzer exclusions reverted (test-only; no active 2026-07-17 generator exclusions remain)

With the gaps closed, the earlier calibration was undone: `schema_asts`' `allow_usersets` default
was flipped **ON** (the G2 concrete-userset leaf is now fully fuzzed everywhere, not opt-in), and
the `ttu_in_boolean` knob was **removed entirely** (the G4 lookup-oracle gate now fuzzes the full
space — booleans × Computed × whole-definition + boolean-arm TTU × userset leaves over generated
derived schemas). No active 2026-07-17 generator exclusion remains. **Validation — full deep hunt
green** (`HYPOTHESIS_PROFILE=deep`, run in this session): the state-equality trio (3 passed, 87 s),
the stateful machines (3 passed, 310 s), the remaining hypothesis tests (14 passed, 629 s), and the
deep G4 gate (1 passed, 45 s). No falsifying examples.

**Formal scope:** unaffected. Every touched path is **outside `W4Fragment`**: the `upos`
userset-membership machinery and the derived-TTU/derived-userset/derived-computed lift shapes are
already-documented proof gaps (userset subjects on derived relations are edge-free, `computedOnly`),
and node `implicit` flags are **projected out** of the state-level gate by the extractor (P5, the
node-GC representation class). So the promote/demote lifecycle and the audit-set lift add processor
paths gated on tainted userset/`upos` state that in-fragment runs never produce, decided entirely
by projected-out flags or by strictly-lower-stratum residue reads — the state-level conformance gate
(`test_conformance_state.py`) is unaffected. The reg13 admission change only narrows accepted raw
writes (never loosens), toward a `matchDecl` guarantee the model already assumed. See
`formal/CORRESPONDENCE.md` §7 for the model↔code note. **NOTE: the phased `verify.sh` is being run
separately by the orchestrator and is NOT claimed green here** — only the `pytest`/hypothesis runs
above were executed in this session. *(Follow-up: the orchestrator subsequently ran the full gate
green — `verify.sh` lean sorry-free 412/412 / conf-heavy 68 / conf-rest 195 all PASSED plus the
6-seed fuzz sweep — recorded in `HANDOFF.md` 2026-07-17 and landed as commit `d517fb5`.)*

---

## 2026-07-23 — multi-instance set-engine support (HA); connected-store spec §2.4/§2.5

The connected-store spec (§2.4 admission, §2.5 freshness tokens) was written
**single-instance**: one `TupleSource` per store, one online evaluator, tokens
consumed only on `ConnectedStore.check`. The code now adds the multi-instance
discipline — several `TupleSource`/`ConnectedStore` instances (one `Session` each)
sharing a store, each set engine instance-local in-memory and synced from
`TupleLogV1`. Additive; no single-instance behavior changes.

The new / relocated mechanisms:

1. **`SetEngine.apply_logged`** (`setengine/engine.py`) — trusted replay of one
   *committed* log row into in-memory state only (no validation, no DB writes). It
   performs exactly the `_apply_add`/`_apply_remove` sequence `rebuild()` would, so
   the state after tailing a log prefix equals a rebuild at that prefix
   (rebuild-prefix equivalence). Presence mismatches (ADD of a present tuple, REMOVE
   of an absent one) are HARD `RuntimeError`s, never op rejections — the log is
   admission-validated and applied exactly-once, so a mismatch means the caller's
   watermark is corrupt (mirrors the apply step's corruption guard).

2. **`TupleSource.catch_up_evaluator`** — tails committed log rows past
   `evaluator_watermark` (`apply_logged` per row, watermark advanced to each applied
   id) until the read comes back empty. **O(delta)** where `refresh_evaluator` is
   O(store). Two caveats carried in the docstring: (X2) the rows tailed are *this
   session's* read snapshot — a long-lived read session must `rollback()` first to
   advance its snapshot; and after a rollback of the instance's OWN uncommitted write
   the watermark may claim an id that never committed, so callers must
   `refresh_evaluator()` after rolling back their own writes (the pre-existing
   contract, unchanged). **Gap-freedom** rests on the writer lock discipline below.

3. **`_lock_source` + the write critical section** — `add`/`remove` now run
   `_lock_source()` → `catch_up_evaluator()` → validate → `_append`, one transaction.
   `_lock_source` takes a `FOR UPDATE` lock on the store's `SchemaV4` row
   (transaction-memoed on `Session.get_transaction()` identity, mirroring
   `ReachabilityIndex._lock_store`). Under the lock no new commit can appear, so
   duplicate detection / remove-existence / cycle parity validate against **current
   committed state**, not a stale local cache. **LOCK ORDERING**: source lock
   (`SchemaV4`) is taken before the graph store lock (`StoreV4`, inside
   `advance_index`) — one global order, deadlock-free.

   **This closes a latent, pre-existing real bug — not merely a new-feature
   invariant.** `_append` flushes the log row's autoincrement id, and that flush used
   to happen *before any lock*, so two concurrent writers on PostgreSQL could
   interleave such that log ids **committed out of id order**. A tailer (or
   `advance_index`'s cursor) advancing on `id > watermark` could then step past the
   lower id before it committed and **permanently skip that row**. With the append
   inside the critical section, ids commit in id order per store and `id > watermark`
   tailing can never skip a row. This hazard existed in the single-instance code path
   too whenever two sessions wrote concurrently on a real ordering-sensitive engine.

4. **`TupleSource.check(at_least=…)`** — the freshness token (§2.5) is now honored on
   the source's own check, not only `ConnectedStore.check`: if
   `evaluator_watermark < at_least` it catches up O(delta), then raises `StaleRead`
   if the token is still not visible in this session's snapshot.

5. **`StaleRead` relocated** from `store.py` to `source.py` (it is raised first by
   `TupleSource.check`); **still re-exported** from `connectedstore.store` for
   backward compatibility.

6. **`ConnectedStore.check` fallback tails instead of rebuilding** — when the index
   lags the token and the fallback set engine also predates it, the fallback now
   `catch_up_evaluator()`s (O(delta)) rather than a full O(store) rebuild.

7. **`SetEngine.result_keys` + `LookupResult` instance-locality warning**
   (`setengine/engine.py`) — `LookupResult.node_ids` are recycled instance-local
   interner ids, meaningless to another instance/process over the same store;
   `result_keys` translates them to the stable `(type, name, predicate)` surrogate
   keys — the portable form for any service boundary (`markers` are already
   portable). Made explicit now that multiple instances share a store.

**Consistency model.** Every instance's state is the fold of an exact *prefix* of the
store's log (prefix consistency — instances differ only in recency, never sideways);
un-tokened replica reads are bounded-stale by tail cadence; read-your-writes / causal
via the log-id `at_least` token. **Cost trade (single-writer):** the lock never
contends and catch-up is one empty indexed SELECT, so a degenerate single-writer
deployment pays one `FOR UPDATE` SELECT (no-op-rendered on SQLite) + one empty log
SELECT per write — correctness-over-perf, deliberate.

**Out of scope** (unchanged): snapshot / "at exactly" reads; cross-store tokens (X6);
`at_least` on `lookup`/`expand`; instance gossip (the DB log is the only channel);
schema-version skew (write-once schemas).

**Formal scope:** unaffected — see `formal/CORRESPONDENCE.md` §7 (multi-instance
scheduling is out-of-model; a lagging replica's state is the fold of an
admission-validated log prefix, and every prefix is a valid store, so T1 applies
pointwise per prefix; `apply_logged` replays the exact `rebuild()` sequence, so no
modeled algorithm changed).

---

## 2026-07-26 — ZT-P0-1: the N3 `_keys_referencing` elision WITHDRAWN (it was unsound)

Found by the zero-trust review (`docs/history/handoff-status-2026-07.md` "Zero-trust review 2026-07-26" (archived from `HANDOFF.md` 2026-07-29), item
ZT-P0-1). **This was a real authorization escalation, not a canonicalization wart:**
`check` returned ALLOW where the oracle returned DENY. Reproduced, then fixed, then
pinned by `tests/test_reg14_residue_gc_elision.py`.

**What was wrong.** `DeltaProcessor` used to skip the `ResidueV1` scan in
`_keys_referencing` on any schema whose every leaf kind fell in a whitelist
`_RESIDUE_LOCAL_LEAF_KINDS = {'closure', 'derived-computed'}` (the N3 perf item,
2026-07-14). With the scan elided, `_residue_references` returned False
unconditionally, so `_gc_subject_node`'s guard stopped protecting nodes.

The whitelist's stated justification was that these kinds' recordings are "always
LOCAL … not cross-object". **That is the wrong property.** What GC actually needs is:

> (P) the recorded subject id's node holds a DIRECT-EDGE-justified position on the
> recording object, so that object's `reference_count` accounting keeps the node alive
> independently of the recording.

`closure` violates (P): `_leaf_concretes(kind='closure')` resolves candidates through
`_incoming_concretes` → `idx.lookup_reverse` — the **full transitive closure**, not the
raw stored tuples the old comment claimed. So a userset node reachable only
transitively (`group:g1#member → group:g2#member → doc:y#a.0`) is recorded on `doc:y`
while holding no edge there. `derived-computed` violates (P) too, since the 2026-07-17
Fix A lift added `_ttu_target_upos_nodes` to its branch (edge-free lifted memberships);
`reference_count` happens to still protect those nodes, but only by accident of the
current leaf set, so it cannot carry the safety argument.

**The failure sequence.** Removing the chain edge drops the userset node to
`reference_count == 0`. Both affected keys take the cheap path; the first un-records and
DELETES the node (the elision reports nothing referencing it); the second then finds
`s_node is None` and skipped its whole update block, so the stale id was never pruned.
SQLite then recycles the freed rowid onto an unrelated principal and the surviving
`upos` entry vouches for it at an object it was never granted on.

**Fix: the elision is removed entirely** — `_keys_referencing` now always scans. Option
(b), narrowing the whitelist, was rejected because the safe residual set is **empty**
(every remaining kind records from-chain (X4a) or lifted (X4b) usersets that are
edge-free by construction), and because (P) is a property of *candidate-resolution*
code, which widened twice without the whitelist noticing. The rationale comment is
replaced by an `N3 WITHDRAWN … DO NOT RE-INTRODUCE` block stating (P) formally. If this
scan must ever get cheaper, the answer is a subject-id → residue **index** maintained in
`_store_residue`, never a leaf-kind whitelist.

**Cost.** Negligible, and much less than it looks: `_any_residue_reference` already ran
the identical full scan with per-row JSON decode on every node-release path on every
schema. Measured (interleaved A/B, min-of-3): **+4.3%** on a synthetic all-`closure`
worst case, **below noise** on the real suite.

**Second barrier (ZT-P0-2).** The comment claiming `_reconcile_subject`'s `sp != '...'`
branch is "UNREACHABLE from the cascade today" was **wrong** — closure leaves do store
untainted-userset subjects, so that branch is reached in exactly this sequence. It is
corrected, and the `s_node is None` early-skip now **escalates to the full-object
reconcile** instead of no-opping: the fix above prevents the processor from deleting a
recorded node, but `ReachabilityIndex.remove_node` deletes its subject node
unconditionally and is not owned by the processor, so a missing node remains reachable
from outside. Escalation drops dead ids by construction (the same policy
`_map_deltas_to_keys` already applies when the node is missing at map time).

**`bulk_backfill.py`: no mirror needed.** It has no GC, is add-only from empty, and its
`_Residue.neg/upos` hold `NodeKey` tuples rather than int ids — so the dangling-id /
rowid-recycle class cannot arise there at all. `tests/test_bulk_build.py` (the
byte-identity differential gate) passes unchanged.

**Why no corpus caught it.** The trigger needs all three at once: an all-whitelist
schema, a *transitive* userset chain into a tainted relation's closure leaf on **≥2
objects**, and the chain edge removed in one op so both objects flip in one cascade
round. No corpus or generator built that conjunction; two earlier fuzz sweeps missed it
for specific structural reasons (no userset chain in one, a wildcard bridge keeping
`reference_count > 0` in the other).

**Formal scope: no Lean change owed, and the divergence NARROWED.** There is no Lean
counterpart to `_keys_referencing`, node GC, or residue-reference scanning (grep: zero
hits), so no modeled definition described the elided code. The Lean model never had an
elision, so removing it moves Python *toward* the model. See `formal/CORRESPONDENCE.md`
§8.1. The escalation branch lands inside the already-recorded unmodeled
`_reconcile_subject` cheap-path gap (`formal/ARCHITECTURE.md`), not a new one.

**Gate.** `pytest tests/` 610 passed; `HYPOTHESIS_PROFILE=deep tests/test_hypothesis.py`
20 passed; a 75-seed post-fix sweep (3 boolean schemas × 25 seeds × 45 random
add/remove ops, checking dangling ids + I1–I6/I10 + full-grid `check` == oracle after
every op) clean — and confirmed to be a real net: restoring the elision makes the same
sweep fail at `ttu-mix seed=0 step=14`.

---

## 2026-07-26 — ZT-P1: security + operational-envelope hardening (zero-trust review)

Companion to the ZT-P0-1 entry above. All items found by the zero-trust review recorded
in `docs/history/handoff-status-2026-07.md` "Zero-trust review 2026-07-26" (archived from `HANDOFF.md` 2026-07-29); every one was confirmed by execution
before being fixed. **Scope decisions on the last three were made by the repo owner**
(caps vs no caps, auto-configure vs warn, raise vs log) and are recorded as chosen.

**ZT-P1-1 — identifier validation accepted a trailing newline (and 257 chars).**
`_IDENTIFIER_RE` was anchored `^...$`; Python's `$` also matches immediately BEFORE a
trailing newline, so `alice\n` validated end-to-end through `SetEngine.add_tuple`, and
because the newline is not consumed by the `{1,256}` repeat, so did 257-character names
ending in one — a control character reaching persisted identity strings, and an
off-by-one against the bound documented in the module header. Now `\Z` + `re.fullmatch`.
Pin: `tests/test_reg15_security_hardening.py`.
*En route:* the review's claim that `*` and `...` are "outside the charset" is **wrong** —
`.` IS in the charset, so `...` is charset-valid. Re-probed: relations named `...` or
containing `.` are separately rejected (the `.` reservation for compiled leaf
predicates), and a mere object/subject NAME of `...` cannot collide with a
predicate-position sentinel. No principal confusion — but for a stronger reason than the
one originally given.

**ZT-P1-2 — 16 load-bearing safety checks vanished under `python -O`.**
`index_v4/core.py` (plus one in `processor.py`) expressed store invariants as bare
`assert`s. Three were the only guard on their path: the batch/bridge expansion **cycle
detector** (bypassed ⇒ unbounded path counts ⇒ permanent phantom reachability ⇒ **stale
ALLOW**), the two **refcount-underflow** guards (⇒ GC stops, silent divergence from the
set engine), and the `remove_node` **dangling-edge post-condition** (on a table with no
enforced FKs, where SQLite rowid reuse can later repoint the row at an unrelated
principal). All converted to `raise InvariantViolation(...)`, following the existing
`blind-audit C3` precedent that had already converted exactly one such assert and not
generalized it. `InvariantViolation` subclasses `AssertionError`, so this is
backward-compatible with callers/tests catching `AssertionError` — no test was weakened.
**The durable pin is structural**: an AST test asserts these two modules contain NO
`assert` statement at all, so a future invariant written as an assert fails immediately;
plus `-O` subprocess tests, and a control proving `-O` really strips asserts (otherwise a
green result could be a false negative).

**ZT-P1-3 — the I1–I13 invariant layer was never reachable from production.**
`install_paranoia` had exactly two callers, both tests; `ConnectedStore` never called it
and exposed no flag, so every runtime detector for the corruption classes in this review
was dark in production — **including the I6 dead-node-id check that catches ZT-P0-1**.
Now `ConnectedStore(paranoia=...)` + `ZANZIBAR_PARANOIA`, with three tiers: `off`,
`residue` (the I6 residue-hygiene family; O(residue rows), pre-commit only) and `full`
(`check_invariants` + the delta-scoped BFS verifier, what tests get). Clause code is
SHARED with the full checker, not duplicated, so the tiers cannot drift.
**Default is `off`, on measured evidence** — interleaved A/B, min-of-3: `residue` costs
**+4.3%** at 162 writes and **+5.7%** at 478, i.e. it grows with store size (the scan is
O(objects carrying derived state)); `full` is +124%/+303%. Shipping a silent ~5%-and-
rising write regression was judged worse than an accurate docstring, which now carries
these numbers and recommends operators set `ZANZIBAR_PARANOIA=residue`. **I5 was
deliberately kept OUT of the cheap tier** — as written it is a full `EdgeV4` scan, which
would have quietly made "cheap" O(store); that boundary is itself pinned by a test.

**ZT-P1-7 — a caller `begin_nested()` silently disabled BOTH locks.** `_lock_store` /
`_lock_source` memoized on `session.get_transaction()`, which returns the ROOT
transaction even inside a savepoint. Take the lock in a savepoint, roll it back
(PostgreSQL RELEASES locks acquired inside it), and the next call matched the memo and
took no lock. The `Session` is caller-supplied and speculative-write-in-a-savepoint is an
ordinary pattern. Memo keys are now the `(root, nested)` pair. The P12a short-circuit
within one transaction is preserved (pinned).

**ZT-P1-4 — both documented locks were silent no-ops on SQLite. DECISION: auto-configure
+ fail loud.** `with_for_update()` compiles to a plain SELECT on pysqlite (no dialect
branch existed anywhere), and pysqlite's default empty-string `isolation_level` runs
SELECTs in autocommit — so a write's check-then-act admission was not atomic, and two
default-configured writers could both pass admission (duplicate / remove-existence /
cycle parity) against a state their combined result invalidates. The working recipe
existed ONLY in the test harness. Now: off SQLite, `SELECT ... FOR UPDATE` unchanged; on
SQLite, a **no-op UPDATE of the same lock row**, which takes the RESERVED write lock for
the rest of the transaction and promotes the connection into a real transaction
(verified: a second connection's write blocks, and it locks even when it matches zero
rows). `SQLITE_BUSY` is now handled at all (there was no retry anywhere): the
connection's `busy_timeout` is floored to 10 s — SQLite's busy handler IS the correct
backoff — plus a bounded statement-level retry for the residual WAL write-after-read
case.
**Now raises `WriteLockUnsafe` at construction** (SQLite binds only, by empirical probe
rather than config guesswork) for: SQLAlchemy `AUTOCOMMIT`; pysqlite `isolation_level=None`
with no `BEGIN` listener (half the recipe); sqlite3 `autocommit=True`. Explicitly NOT
raising: pysqlite's default (the whole existing suite) and the full recipe.
**Caller-visible:** opening a ConnectedStore on SQLite now performs one write, so a
read-only SQLite file can no longer be opened.

**ZT-P1-5 — watermark advances could skip log rows permanently, and `at_least` then
certified the stale answer. DECISION: contiguity-check and raise.** `advance_index` did
`cursor.applied_log_id = rows[-1].id` and `TupleSource.add/remove` did
`max(watermark, token)`, both assuming the preceding catch-up was complete. Under a
pinned read snapshot it is not — **MySQL/InnoDB defaults to REPEATABLE READ** — so a
concurrent commit stays invisible, the catch-up tails nothing, the watermark jumps past
those rows, and they are never applied again. `check` then returns ALLOW forever
*including under `at_least`*, because `_fresh_enough` compares against the bogus
watermark. (`source.py` already used the correct pattern elsewhere: "Assignment, not
max".) Both advances are now contiguity-checked, raising the new retryable
`WatermarkGap` (distinct from `StaleRead` — nothing is corrupt; a fresh snapshot fixes
it). `log_gap` is free in the contiguous case (an interval of N ids with N applied has no
room for a skipped one) and otherwise uses a LOCKING read, because the row it hunts is
exactly the one a pinned snapshot hides. `assert_read_isolation` at construction rejects
`REPEATABLE READ` / `READ UNCOMMITTED`; skipped on SQLite (pysqlite reports
`SERIALIZABLE` regardless, and SQLite fails a stale-snapshot write loudly rather than
hiding rows). **Caller-visible: MySQL/InnoDB at its default isolation level now refuses
to open** — pass `isolation_level="READ COMMITTED"`.

> ⚠ **EVIDENCE CAVEAT (2026-07-26) — none of this was exercised against a real MySQL or
> PostgreSQL server.** `requirements.txt` is `pytest / sqlmodel / pyroaring /
> hypothesis`; there is no MySQL or PostgreSQL driver in the tree and every test runs on
> in-memory SQLite. Concretely:
> * the **hazard** (an InnoDB REPEATABLE READ read view pinned at the first read, so a
>   concurrently-committed log row stays invisible for the rest of the transaction) is
>   **reasoned from documented InnoDB semantics**, not observed here;
> * `assert_read_isolation` is unit-tested against a **fake session** that merely reports
>   a dialect name and level (`tests/test_zt_p1_hardening.py`'s `_FakeSession('mysql',
>   …)`) — it has never rejected a real server;
> * the **gap detection itself IS genuinely tested**, but by SYNTHESIZING an invisible
>   commit (hiding a row from `log_rows`) on SQLite to imitate what InnoDB would do. That
>   proves `log_gap`/`WatermarkGap` fire on the state; it does not prove real InnoDB
>   produces that state.
>
> This is the SAME class as the standing CS-1 caveat the zero-trust review itself filed
> ("the `FOR UPDATE` semantics that make this hold on PostgreSQL/MySQL are *reasoned
> about, not CI-tested*") — the fix adds a second layer of reasoned-but-untested
> behaviour on top of the first, and the same is true of ZT-P1-4's `FOR UPDATE` arm
> (only the SQLite arm was empirically verified: a second connection's write blocking,
> and the lock being taken on a zero-row UPDATE). **Do not read "now refuses to open" as
> "verified to refuse to open."** Settling it needs a real MySQL and PostgreSQL in CI —
> which would also finally close CS-1 and the Phase-7 concurrency gap, and is the single
> highest-value untested surface in the system.

**ZT-P1-6 — no resource bounds. DECISION: fix the crash only, no admission caps.**
Nothing that is accepted today became rejected. The fixed half: `SetEngine.check`'s
`sat`/`member_via_usersets` recursion was depth-linear, so a ~1,500-long `group#member`
chain — accepted without complaint, because the write path is iterative — made every
subsequent read raise `RecursionError` permanently, `lookup` worst of all (it sweeps
every declared `(type, relation)`). `check`/`expand` are now generator/trampoline-driven
on an explicit heap stack, so evaluation is depth-independent. **The Tarjan-lowlink
memoization and provisional-False cycle guard are preserved exactly** — verified by
differential, not by inspection: 68,400 `check` comparisons against the old code lifted
verbatim (4 schemas × both `SetOps` × 25 mutation states), plus a cycle-focused pass over
object-level `parent` rings where the guard genuinely fires (10/24 states) — **0
divergences vs the old code and 0 vs the oracle**. Not slower on real workloads
(explicit short-circuit loops offset the driver); a synthetic chain-heavy microbenchmark
shows `check` +~55%. Pins in `tests/test_zt_p1_hardening.py`, including a test that
crushes `sys.setrecursionlimit(60)` and shows a control recursion dying while a 300-link
chain still evaluates.
**Left unbounded by decision:** the N² closure amplification (240 tuples → 14,640 closure
rows in 5.1 s), which runs inside `advance_index` holding both locks, and outbox
retention (the outbox is still append-only with no DELETE anywhere).

**Formal scope: no Lean change owed for any ZT-P1 item.** ZT-P1-1/-2/-7 are
admission/guard hardening below the model's abstraction. ZT-P1-6 is below it too:
`formal/CORRESPONDENCE.md` §2 already records that `SetEngineModel.check` is NOT an
algorithm twin of `SetEngine.check` (the model is a pure fuel recursion; the shipped
evaluator is a memoized DFS), and the row that IS a twin claim — the `expand` family —
keeps the same modeled algorithm, only relocating its frames from the C stack to the
heap. ZT-P1-4/-5 are the concurrency/persistence layer, explicitly out-of-model
(`CORRESPONDENCE.md` §7, multi-instance scheduling).

**Gate at time of writing:** `pytest tests/` **685 passed**; `verify.sh lean` PASSED
(455/455 audits, floor 455, 0 holes); conformance 4×89 = 356 across `conf-tile:I/4`.

---

## 2026-07-26 — ZT-P5: stale dismissals re-adjudicated by PROOF or REPRO (+ one NEW divergence)

Re-adjudication of `docs/history/handoff-status-2026-07.md` "Zero-trust review 2026-07-26" (archived from `HANDOFF.md` 2026-07-29) §P5 under the
owner's "ignore the ignore" standing instruction: every past dismissal is an
unproven assumption until re-tested, and a constructed counterexample or a
structural derivation beats prose. INVESTIGATION ONLY — no product code was
changed here; the new pins live in `tests/test_zt_p5_readjudication.py`.

### ★ NEW DIVERGENCE (accept/reject parity) — `folder:* parent folder:*`

**Found while disproving reg11.** On **reg11's own schema**, with **one write**:

```
model
  schema 1.1
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user] or viewer from parent
```
`object_wildcard_shapes = {('folder','parent')}`; write
`folder:*  parent  folder:*` (star SUBJECT **and** star OBJECT).

* **graph index: ACCEPTED.** `RuleSet.apply` routes it to
  `folder:*#viewer @ folder:*#viewer`, which is NOT a self-loop in the graph
  because the wildcard node is position-split (spec §1.2/§1.3): the edge is
  `w_any(folder,viewer) -> w_all(folder,viewer)` between two distinct `node_v4`
  rows (`wildcard='any'` / `'all'`). The cycle check does not fire.
* **set engine: REJECTED** on both `SetOps` ("would create a cycle in the userset
  membership topology"). `ConnectedStore` is therefore NOT exposed — `TupleSource`
  delegates admission to the `SetEngine`. The exposure is `WildcardIndex` used
  directly (a public API, and the validation matrix's `GraphBackend`).
* **DETONATION, verified.** After the graph accepts it, `(folder,viewer)` is in
  BOTH `bridged_in_shapes` and `bridged_out_shapes`, so every present-or-future
  concrete `folder:x#viewer` carries the in-bridge **and** the out-bridge and the
  `w_any -> w_all` edge closes a data cycle. An innocent later
  `user:v viewer folder:q` is then **permanently graph-REJECTED** while set engine
  and oracle accept it. I1–I13 stay **GREEN** on the state, so no invariant
  catches it.
* **Why the 2026-07-17 gate misses it.** `_reject_doubly_bridged_shapes` uses the
  NARROW left factor `wildcard_userset_restriction_shapes(ast)` (literal `T:*#p`
  restrictions) rather than `bridged_in_shapes`. That narrowing (the "Precision of
  the criterion" paragraph of the 2026-07-17 F1/F2 entry) was justified by:
  *"star-tupleset through-shapes … are NOT writable usersets and cannot mint a
  persistent `w_any` node — reg11's dangerous writes self-cycle and are rejected on
  both backends, so nothing detonates."* **That sentence is false.** Here the
  through-shape `(folder,viewer)` (derived from `[folder:*]` on the tupleset
  `parent`) is exactly what mints the persistent `w_any -> w_all` path, and it does
  detonate. Under the COARSE criterion (`bridged_in ∩ bridged_out ≠ ∅`) this schema
  IS doubly bridged and would have been rejected.
* **Pins:** `tests/test_zt_p5_readjudication.py::test_zt_p5_star_subject_star_object_tupleset_write_parity`
  (**strict xfail** — it pins a genuine divergence; flip it when fixed, never relax
  it), `…_current_behaviour_documented` (pins today's asymmetry so a silent change
  in either direction is caught) and `…_connectedstore_is_not_exposed_…`.
* **Preconditions, delimited empirically** (3 schemas × 2 OWC sets × 3 write
  shapes): the divergence needs (i) the star-SUBJECT **and** star-OBJECT tupleset
  write — `folder:x parent folder:*` (reg11's own case) and `folder:* parent
  folder:x` (reg9's) are both rejected by BOTH backends; (ii) a TTU whose head and
  target are the SAME relation (with `admin from parent` the routed edge is
  `w_any(folder,admin) -> w_all(folder,viewer)`, different shapes, no latent cycle
  — all backends accept); (iii) any TTU at all (with no TTU all backends accept).
* **Why the gate missed it — the exact blind spot.** The star-bridge fuzzer DOES
  draw this tuple: `_star_bridge_pool` emits `('...', T, '*', 'parent', T, '*')`
  whenever `(T,'parent')` is in the drawn object-wildcard set. What it cannot draw
  is a **self-referential TTU**: `_star_bridge_schema` is always
  `B: [user] or A from parent` with `A != B` drawn distinct, so precondition (ii)
  never holds and the write is unanimously ACCEPTED there (verified: on the
  fuzzer's own schema with `(T,'parent')` object-wildcarded, all three backends
  accept). Conversely the self-referential TTU DOES appear — it is reg11's schema
  and `owc_star_ttu.fga` — but reg11 is a hand-written pin that only writes
  `folder:a parent folder:*` (concrete subject), and `OWC_STAR_TTU_SHAPES` omits
  `(folder,parent)` so `_owc_star_ttu_pool` never emits a star-OBJECT `parent`
  tuple at all. The two halves of the precondition are each covered; their
  CONJUNCTION is generated by nothing in `tests/` or `formal/conformance/`.
  **Cheapest generator fix:** let `star_bridge_configs` sometimes draw `A == B`
  (a self-referential TTU).
* **NOT FIXED here** (investigation scope). A fix is a compile-gate or cycle-check
  change and needs the full gate + its own review. Candidate directions: restore
  the coarse `bridged_in ∩ bridged_out` criterion (it over-rejects the legal reg11
  class, so it needs a carve-out that is not the current one), or make the graph's
  cycle check see the `w_any -> w_all` edge as the latent cycle it is.

### Target 1 — reg11's "the multi-hop out-bridge generalization is unreachable": **DISPROVED**

reg11 argued: *"Any derived edge INTO `w_all(T,p)` is minted by a
`T:x <tupleset> T:*` write whose own subject is a same-shape concrete `T:x#p`,
which the out-bridge immediately reaches back — so such a write always self-cycles
at admission and can never persist for a later write to build a longer loop on."*

That is true only of reg11's own schema, where the TTU reads the SAME relation it
defines (`viewer: … or viewer from parent`). With a TTU whose TARGET differs from
its HEAD (`viewer: [user] or admin from parent` — the reg10 shape), the edge into
`w_all(folder,viewer)` is minted from `folder:a#admin`, a **different** shape that
the out-bridge does not reach back. Verified: `folder:a parent folder:*` is
**ACCEPTED and PERSISTS** on both backends; a later `folder:a#viewer admin
folder:a` closes the genuine **multi-hop** loop
`folder:a#admin -> w_all(folder,viewer) ->[out-bridge] folder:a#viewer ->
folder:a#admin` and is rejected by both. Parity holds in this instance — what is
disproved is the reachability argument, which is what licensed leaving the class
unfuzzed. Pinned: `…::test_zt_p5_reg11_multihop_out_bridge_IS_reachable`.

**Bounded negative result** (evidence, NOT a proof — stated bounds):
* Family A — one object type `folder`; relations `{parent:[folder,folder:*], a, b}`;
  restriction subsets of `{user, folder#a, folder#b, folder:*#a, folder:*#b}` of
  size 1–2; optional `{a|b} from parent` arm; `object_wildcard_shapes` any
  non-empty subset of `{(folder,parent),(folder,a),(folder,b)}`; write sequences of
  2–4 tuples from a 33-tuple pool always containing a `folder:*`-OBJECT write.
* Family B — two object types (`folder`, `doc`) with cross-type tuplesets and
  `remove` ops; write sequences of 2–4.
* ≈1,720 admissible randomized trials in total: family A ≈265 (seeds 1, 7) plus a
  344-trial family-A sweep with the star-subject/star-object class excluded from
  the pool; family B ≈1,112 (seeds 3–6, 8). **Every** admission divergence found
  was the single class filed above (7 hits); **zero** answer-level divergences were
  found anywhere, and the 344-trial exclusion sweep found **zero** divergences of
  any kind.
* A deterministic ≈72-state slice is pinned as
  `…::test_zt_p5_bounded_search_object_wildcard_out_bridge_no_further_divergence`
  so the negative result is executable rather than asserted.

### Target 2 — the from-chain TARGET note's *reachability* half (2026-07-13 X4 §1): **DISPROVED**

The note said: *"if a from-chain TARGET were an untainted subject-wildcard-bridged
shape with grants already sitting in its `w_any` … No currently-compilable schema
class reaches this shape."* It is reachable. **Structural route:**
`_from_chain_keys` fires for leaf kind `derived-ttu`, which `_build_plan_tree`
produces when `_is_pure` is false — i.e. when **some** parent type of the tupleset
has a TAINTED `target_rel`. But `_from_chain_keys` enumerates **all** stored
parents, so a parent of a DIFFERENT type whose `target_rel` is UNTAINTED yields
exactly the excluded shape. (A second route: `derived-tupleset-ttu`, where the
TUPLESET is tainted, leaves the target unconstrained outright.)

Minimal repro (`tests/…::test_zt_p5_from_chain_target_shape_IS_reachable`):
`doc.fparent: [folder, team]`, `doc.viewer: member from fparent`, with
`team.member` tainted (`[user] but not tblk`) and `folder.member` UNTAINTED and
bridged-in via `folder.shared: [user, folder:*#member]`. Writing the grant
`folder:*#member shared folder:g` FIRST puts it in the `w_any` before the
from-chain intern; then `folder:f1 fparent doc:d1` makes reconcile step 2a intern
`folder:f1#member` FRESH mid-cascade and `_ensure_bridges` mints
`folder:f1#member -> w_any(folder,member)`, whose closure reaches the pre-existing
grant `folder:g#shared` — the note's "new bridge-fed truth".

**The note's OTHER half is not contradicted.** No misbehaviour was observed: 400
randomized trials over a family varying the grant relation's operators
(`but not` / `and` / `or` / nested), the TTU's operators and the write order —
88 of which reached a FRESH untainted+bridged from-chain intern — produced 0
admission divergences, 0 answer divergences vs the oracle, 0 invariant violations
and 0 `audit_fixpoint` failures (re-run clean on 3 seeds). A plausible structural
reason: the grant that puts edges in the `w_any` is itself a wildcard-userset
grant, which puts the shape in the granting relation's residue `stars`, so a later
concrete of that shape is already covered and needs no new recording. **That is a
hypothesis, not a proof** — it is not established for intersection-rooted grant
relations, and no bounded search was run over `>2` strata.

### Target 3 — the object-wildcard corpus at STATE level: Python side CLEAN, **Lean side STILL UNVERIFIED**

`FINAL_REVIEW.md` §3 / `ARCHITECTURE.md` §6 infer "the fragment exclusions are
proof-scope, not observed divergence" from a 2026-07-12 CHECK-level probe — the
same inference that failed at STATE level on 2026-07-17. The Lean half cannot be
settled from here (`formal/` was out of scope for this session). What was
established Python-side:

* **Live == rebuild.** Exhaustively to K=2 over the formal `object_wildcard`
  corpus's 6-tuple space and an object-wildcard TTU corpus's 7-tuple space, the
  LIVE `ConnectedStore` state equals `build_index(bulk=False)` and
  `build_index(bulk=True)` on all four canonical projections (nodes / edges /
  residues / outbox, natural keys), with I1–I13 green on all three states.
  Exhaustive K=3 was also run clean in-session (42 + 64 stores).
* **Order independence.** The live state is a function of the tuple SET, not the
  write order (the property the 2026-07-17 stale-fanout bug broke) — pinned over
  the K=3 stores of the TTU corpus.
* **The RICH corpus.** 160 randomized trials (4 seeds) over
  `tests/fga_schemas/owc_star_ttu.fga` (object wildcards + star tupleset parents +
  group usersets + a boolean `restricted`), stores of 3–10 tuples, each checked
  for live-vs-rebuild, live-vs-bulk, order independence over 3 shuffles, and
  add-then-remove state restoration: **0 problems**.

**What would settle the remaining half:** a `formal/` state-level conformance run
(the exact edge+residue equality extractor used by `test_conformance_state.py`)
over the `object_wildcard` corpus. It is currently EXCLUDED from `GRAPH_FRAGMENT`
for a stated proof-scope reason (`BareStarStore` requires concrete stored
objects), so the state extractor has never been pointed at it. Until that runs,
the §3/§6 sentence should be read as *"no Python-side state divergence observed
(bounded)"*, not as *"no state divergence"*.

**Disposition (board row `LT-1`, HOLD).** Target 2 and Target 3 above are the only
genuinely-live latent residues left in this inventory. **Do not chase them speculatively —
act if a real schema or corpus surfaces one.** Completion criterion if reopened: Target 2
needs a bounded search over more than two strata **and** intersection-rooted grant
relations (the 400-trial sweep covered neither); Target 3 needs the LEAN half, which
cannot be settled from the Python side at all. ⚠ Target 3's inference class — "fragment
exclusions are proof-scope, not observed divergence", argued from check-level evidence — is
**the exact inference that failed at state level on 2026-07-17**; do not re-derive comfort
from it.

### Target 4 — the `group_userset` enum exclusion: **CONFIRMED CORRECT** (the backends agree)

The review flagged the exclusion as an unadjudicated ADMISSION-DOMAIN difference —
the reg9/reg10/reg13 bug class. It is not one. Enumerating **all 299 stores** of
the shape's 12-tuple declared space at the enum module's own K=3 and feeding each
store to both backends:

* set engine rejects at least one write on **132** stores; graph rejects on
  **132**; **per-write admission disagreements: 0**;
* over **all permutations** of every store: **0** mismatches and **0**
  order-dependent stores (a store admissible in some order but not another);
* on the 167 fully-admitted stores, graph == both `SetOps` == oracle over a
  16-query grid: **0** answer divergences.

So the rejections are a property of the SHAPE (self-referential nested groups are
cyclic, and this repo's write/compile-time acyclicity strictness is the standing
documented deviation), not a backend disagreement. Pinned exhaustively as
`…::test_zt_p5_group_userset_admission_domains_are_identical` (the 132/299 figure
is asserted, so it cannot drift silently).

### Target 5 — orphaned `formal/history/` findings: current Python-side truth

* **`w3cJobValid_enumJob2D` star-freeness hole** ("a WILDCARD restriction on a
  derived Direct arm puts `user:*` in `storedDirectSubjects`"). Python **admits**
  the shape (`viewer: [user, user:*] but not blocked`); it compiles to two closure
  leaves and is exhaustively correct at K=2 over its 10-tuple space (graph == both
  `SetOps` == oracle; 176 stores to K=3 in-session). **Proof-side only** — no
  Python behaviour change implied. Pinned.
* **`PDerivedUserset` never modelled in Lean.** Python: a Direct restriction over a
  DERIVED relation compiles to a `derived-userset` leaf and is exhaustively correct
  at K=2 (also inside an exclusion — the 2026-07-17 extension); its WILDCARD form
  `[group:*#member]` remains a compile-time scope rejection on both backends. The
  gap is Lean-side modelling only. Pinned.
* **Phase-ledger row 0.5 — "verify compiler undefined-reference behavior (A3)"
  (`todo` since Phase 0): ANSWERED.** `compile_ruleset` performs **no**
  undefined-reference validation whatsoever. All seven forms tested compile
  **silently**: undefined computed target, undefined TTU target, undefined tupleset
  relation, undefined restriction type, undefined userset relation, undefined
  boolean arm, and a self-referential `define viewer: viewer`. All three backends
  then build, and every undefined reference reads as the **empty** relation —
  **fail-CLOSED and unanimous** (graph == both `SetOps` == oracle). So this is a
  well-formedness/diagnostics gap, not a soundness one. Pinned (7 parametrised
  cases) so a future "reject undefined references" change is a deliberate, visible
  decision rather than a silent behaviour flip.

### Also re-derived while working (not separately filed)

* The compiler PROPAGATES object-wildcard shapes through TTU heads: declaring only
  `(folder,parent)` puts `(folder,viewer)` in `bridged_out_shapes`. Both the new
  divergence and the reg11 multi-hop repro depend on this, and neither declares
  `(folder,viewer)`.
* `ConnectedStore`'s admission is the **set engine's**, not the graph's
  (`TupleSource.add` -> `SetEngine.add_tuple`). Any accept/reject divergence in the
  graph-accepts direction is therefore invisible to the composed system and visible
  only to direct `WildcardIndex` users and to the validation matrix.

### META-lesson (recurring; state it plainly)

Both Target 1 and Target 2 above were dismissed on the same flawed reasoning:
**absence of a corpus** — reg11's "no currently-compilable schema class reaches
this shape" and the from-chain note's identical phrasing — read as a reachability
claim when each was actually only a claim about what the *existing fuzz pool or
hand-written pins* happened to build. This is the third time this exact reasoning
has failed: reg10's own "Known residual" (2026-07-13, closed 2026-07-16) already
recorded that its "no current corpus" claim was "true only of the existing fuzz
pool, not of reachability." Three strikes is a pattern, not a coincidence. The
norm going forward: **absence of a corpus is evidence about the corpus, not about
reachability.** A dismissal on those grounds needs either a structural argument
(why no schema/write-sequence CAN reach the shape — not why none currently does)
or a bounded search with STATED bounds (corpus, K, trial count — as Target 1's
"Bounded negative result" and Target 2's 400-trial sweep do above), never a bare
"nothing exercises it."

### Gate at time of writing

`pytest tests/` **703 passed, 1 xfailed** in 8m16s -- the 685 baseline plus this
session's 18 new passes and 1 strict xfail. One further pin
(`test_zt_p5_starstar_divergence_generator_blind_spot`) landed after that run;
the module alone is **19 passed, 1 xfailed**, so the expected full-suite figure is
**704 passed, 1 xfailed**. `formal/` was NOT touched and `verify.sh` was NOT run by
this session (other agents held it) -- the new module lives entirely under
`tests/` and imports nothing from `formal/`.

---

## 2026-07-27 — the RDBMS evidence gap CLOSED against a real PostgreSQL (and what it falsified)

Scope note: this entry does **not** revise the 2026-07-26 ZT-P1-5 EVIDENCE CAVEAT above.
That caveat was an accurate statement of what was known on the day it was written, and it
did exactly its job — it named the untested surface precisely enough that testing it was a
one-session task. It stands as written; this entry supersedes it in fact.

**What now exists.** A real server leg: `scripts/pg_local.sh` stands up a throwaway
user-space **PostgreSQL 17.10** cluster (conda-forge binaries, scratch data directory,
127.0.0.1 on a non-default port, `destroy` removes it without a trace), and
`tests/test_postgres_ha.py` runs the HA/concurrency scenarios SQLite provably cannot
express. `tests/dbengine.py` routes `ZANZIBAR_TEST_DSN` to the same server for
`tests/test_concurrency.py` and the connected-store concurrency/multi-instance modules.
`psycopg2-binary` is now in `requirements.txt`, marked as needed only for this leg —
without a DSN everything skips, and `ZANZIBAR_PG_REQUIRED=1` turns a missing DSN into a
hard error rather than a silent green. Also settled by the same decision: **MySQL is not
a supported backend.** Supported = SQLite (dev/test) + PostgreSQL (server). Every
load-bearing InnoDB claim in live code and living docs has been rewritten or deleted;
`docs/history/**`, `benchmarks/results/**`, `formal/history/**`, `legacy/**` and the dated
entries above keep theirs, because they record what was believed at the time.

### VERIFIED (previously reasoned-only)

* **`FOR UPDATE` is real, blocking, and row-granular.** `TupleSource._lock_source` on the
  store's `SchemaV4` row makes a second writer sit in the lock queue until the server
  cancels it (`QueryCanceled` after the statement timeout, not an instant pass-through),
  while a *different* store's row stays free — so it is a row lock, not a table lock — and
  it releases on commit. This arm had never executed in the repo's history.
* **The documented LOCK ORDERING invariant holds**, observed rather than argued: with the
  graph `StoreV4` row held by a third party, a writer queues on *that* lock while already
  holding the `SchemaV4` one — source lock before store lock, exactly as the docstring
  claims.
* **Multi-writer admission is sound under real contention.** 4 concurrent `TupleSource`
  instances on one store produce log rows that are contiguous and exactly-once, and the
  resulting index is identical to a single-writer replay of the same tuples. A racing
  observer thread never sees a hole (and the test fails if it never actually raced).
* **`log_gap` / `WatermarkGap` fire on a genuinely out-of-order commit.** PostgreSQL
  assigns a log id at INSERT and publishes visibility at COMMIT, so a lower id really can
  land after a higher one; `advance_index` refuses the advance, commits nothing, and a
  fresh pass applies both rows. Until now this was only ever demonstrated by *synthesizing*
  the invisible commit on SQLite.

### FALSIFIED (the valuable half)

1. **`SERIALIZABLE` was NOT safe, and accepting it reproduced a live authorization
   fail-open.** `SAFE_ISOLATION_LEVELS` admitted it on the stated grounds that
   "PostgreSQL aborts the transaction with a serialization failure rather than letting it
   act on a stale view." Measured: it does not. A plain log read is not a dangerous SSI
   structure on its own, and `SELECT ... FOR UPDATE` against a row another transaction only
   LOCK-modified raises no conflict. So a SERIALIZABLE `TupleSource` pinned its snapshot at
   open, missed a concurrently committed **revocation**, jumped its watermark past it, and
   then answered `check(..., at_least=<revocation token>)` with **True** — the freshness
   mechanism certifying a state that never existed. Fixed: `SAFE_ISOLATION_LEVELS` is now
   `frozenset({'READ COMMITTED'})`. Repro: `test_serializable_bind_is_refused`.
2. **`log_gap`'s `FOR SHARE` was not what made it sound.** The docstring argued "InnoDB
   serves locking reads from the LATEST committed version, so `FOR SHARE` surfaces the
   hidden row." That is an InnoDB property — about a database this project does not
   support — and it is false of PostgreSQL, where a locking read under a pinned snapshot is
   served from the transaction snapshot like any other read. Measured: `FOR SHARE` returned
   `[]` for a row committed after the snapshot and `log_gap` returned `None`, blind to
   exactly the row it exists to find. The real guarantee is upstream — the isolation gate
   admits only READ COMMITTED, under which every statement sees the newest commit. Pinned
   in the direction that matters by `test_log_gap_is_snapshot_served_under_a_pinned_snapshot`,
   which asserts the *blindness*: weaken `SAFE_ISOLATION_LEVELS` and the gap check is
   silently disarmed. **This is the entry's headline lesson: an unsupported-database fact,
   sitting in a comment, was half the justification for a real bug.**
3. **`assert_read_isolation` was not on the public write path.** It ran only in
   `ConnectedStore.__init__`, while `TupleSource` — exported from `connectedstore/__init__`
   and a complete write path in its own right — got no check at all. The reproduced
   SERIALIZABLE escalation ran entirely through `TupleSource`, never touching
   `ConnectedStore`. It is now called from `TupleSource.__init__` too (cheap, idempotent, a
   no-op on SQLite).
4. **"A replica reader never sees torn state" is a SQLite-WAL inheritance, not a property
   of the target dialect.** PostgreSQL READ COMMITTED — the level this design *requires* —
   re-snapshots per **statement**, so a multi-statement read straddles concurrent commits
   and two identical `SELECT`s in one transaction return different answers. Demonstrated
   deterministically (`test_read_committed_gives_a_reader_no_stable_snapshot`) rather than
   left to surface as a flake. Nothing here is a wrong *answer* today, but any reasoning
   that assumed a stable read snapshot on the server is void.

Three strict xfails carry live PostgreSQL-only findings forward, each with an explicit
`raises=` (a bare strict xfail also "passes" when the database is unreachable — the exact
silent-green this module exists to eliminate). The sharpest: `TupleSource.__init__` reads
`log_watermark` and *then* rebuilds the set engine — two statements, atomic under a pinned
SQLite-WAL snapshot, not atomic at READ COMMITTED — so a write committed between them lands
in the rebuild but not the watermark, and the next `catch_up_evaluator()` raises
`RuntimeError("log ADD of an already-present tuple")` permanently. Fails loud, so no wrong
answer, but a routine concurrent open bricks the instance. There is no one-line fix:
reading the watermark *after* the rebuild converts the loud failure into a silent skip, so
the pair has to become genuinely atomic.

**META-lesson, matching the 2026-07-26 one in kind:** "reasoned from documented semantics"
is evidence about the documentation, not about the system — and it is worth *less* than
"no corpus", because it carries the confident shape of a proof. Two of the four
falsifications above were confidently-worded comments citing a database the project does
not run. Prose about a dialect is executable-adjacent: it decides what future changes are
considered safe. If a claim about server behaviour is load-bearing, either a test asserts
it against that server or the comment says out loud that it is unverified.

---

## 2026-07-27b — the remaining zero-trust backlog cleared, and what was deliberately NOT closed

Same day, after the PostgreSQL entry above. `ZT-P1-8` (a–e), `ZT-P1-6a`, outbox
retention, `ZT-P4-4/4-5/4-6`, the `check_invariants` docstring, and both orphaned
`formal/history/` findings. The per-fix record is on the HANDOFF board; this entry
exists for the parts a future reader would otherwise have to re-derive — the places
where the fix is deliberately NARROWER than the finding, and the residuals.

### Two fixes are narrower than their findings, on purpose

**`lookup(at_least=)` REFUSES; it does not fall back.** `check`'s third rung answers
from the set engine when the index lags. The enumeration surfaces cannot: graph
`node_ids` are `NodeV4` row ids, set-engine ones are recycled instance-local interner
ids; markers are `(type, predicate, variant)` triples vs `(type, predicate)` pairs; and
`excluded_node_ids` — the derived `neg` channel — has no set-engine counterpart at all.
A fallback would silently change *what the return value means* as a function of worker
lag. And in the case that actually matters, a stale index, the graph node rows for the
un-applied tuples **do not exist**, so even a translation bridge is impossible in
principle rather than merely expensive. So the surfaces now ACCEPT a token and raise
`LookupNotFresh` when they cannot honour it. The distinction being asserted:
*refusing a demand you cannot meet is not the same as not offering one.* Before this,
a revoked principal stayed enumerable with no API to object — and list-objects /
list-users is exactly what a revocation UI reads. `docs/architecture/decision-log.md`'s
"at_least is check-only" entry is revised in place rather than deleted; the
prerequisite it names (a portable lookup key contract for both backends) is unchanged
and still unbuilt.

**The closure fan-out cap EXEMPTS removals.** `ZANZIBAR_MAX_CLOSURE_FANOUT` bounds what
a single ADD may materialise while holding both per-store locks. Applying it to removes
would be actively harmful twice over: an over-capped region would become permanently
unshrinkable (a worse denial of service than the one being fixed), and in an
authorization system a cap that can refuse a REVOCATION is a fail-open. The cap is
counted before anything is materialised, so a rejection leaves no partial state.

### Residuals — the honest part

1. **The cap does not stop the DoS that motivated it.** The review's scenario was
   re-reproduced (240 tuples → 14,640 closure rows, 2.2 s here) and its peak
   *per-write* fan-out is **120**. It is 240 cheap writes, not one expensive one. The
   cap bounds a single write's lock-hold; the N² accumulation needs a **store-level
   quota**, which was not built. Do not read "resource bounds added" as "the measured
   DoS is closed".
2. **≥3-strata coverage of the LEAN model cannot be closed without widening the
   fragment.** `runCascade2` is two literal nested applications — the round count is
   structural, not a parameter — and `W4Fragment.twoStrata` is a hypothesis of
   `graph_correct`. Widening needs a `runCascadeN` and a re-proof of the whole W3d-2
   layer. What is NOT ungated is Python: `test_multi_stratum_three_way` already drives
   the real cascade at 3 strata. The review's framing ("the ≥3-stratum cascade path is
   tested by NOTHING") was outdated; the correct statement is narrower and about Lean.
3. ~~**Still at zero coverage anywhere:** wildcard usersets `[T:*#p]`, and the
   `derived-tupleset-ttu` plan leaf. Both were left OUT of the new plan-leaf coverage
   floor rather than papered over. The floor exists to make the next gap nameable.~~
   **CLOSED 2026-07-28 — see the 2026-07-28 entry below.** The floor did its job: both
   holes were named, and both turned out to be reachable (the wildcard-userset one only
   over UNTAINTED relations — over derived relations it is a compile-time scope
   rejection, so the surface is narrower than the finding read).
4. **`_any_residue_reference`'s complete `ResidueV1` scan is still unbenchmarked**, and
   it is now unconditional on every node-release path after the `ZT-P0-1` fix.

### Two findings that only appeared because a fix forced an audit

* `processor_writes` had a **downstream mirror** — `ReachabilityIndex._writing_derived`,
  the bool the row writer actually consults to stamp `EdgeV4.derived`, with the same
  shared-object defect. Fixing one flag without auditing every site would have left the
  half that touches the stored row.
* `prune_outbox` must **keep the head row**. `id` is the SQLite rowid, so emptying the
  table restarts ids at 1 and a consumer holding cursor 500 never sees the next 500
  deltas — silent, permanent delta loss, on the one dialect CI runs. A retention helper
  written without that guard would have been a data-loss bug shipped as housekeeping.
* No corpus anywhere compiled a **`derived-userset` plan leaf** (histogram over all 69
  schemas the harness reads: `closure 211 · derived-computed 42 · derived-ttu 50 ·
  derived-userset 0`) — in the exact area where five real divergences were found. The
  `PDerivedUserset` orphan turned out to name a real hole, not a stale worry.

**META-lesson, matching the one above.** Every item here was filed by a review that
read the code carefully. Three of them were *wrong in detail* — the strata claim was
outdated, the DoS was misattributed to a single write, and the "no node identity in
Lean" premise was false (`GraphState` does have `nodes`). A finding is a hypothesis
with a citation, not a verdict; re-measure before fixing, and report the correction as
loudly as the fix.

---

## 2026-07-28 — the last two ZERO-coverage conformance holes closed (board item C)

Both holes were named by the 2026-07-27 plan-leaf floor rather than papered over,
and both had to be **measured before being believed** — the finding text read
wider than the reachable surface in one case, and narrower in the other.

1. **Wildcard usersets `[T:*#p]` are reachable ONLY over UNTAINTED relations.**
   Over a **derived** relation the shape is a deliberate compile-time scope
   rejection — `zanzibar_utils_v1.py::_build_plan_tree`'s `Direct` arm raises
   `UnsupportedByGraphIndex` ("needs symbolic composition through residues"), and
   it raises out of `parse_openfga_schema` itself, so such a schema cannot be a
   conformance corpus at all (the plan-leaf coverage floor and
   `test_grid_independence` both call `parse_openfga_schema` on every entry of
   every corpus dict). The **set engine** does answer it — verified, oracle ==
   set engine on all 102 grid queries of `[group:*#member]` over
   `member: base but not kicked` — but a corpus entry would crash the harness
   rather than extend it, so this is recorded, not corpus'd.
   Over an **untainted** relation the shape is fully live: new corpus
   `formal/conformance/corpus.py::TTU_USERSET_SCHEMAS['wildcard_userset']`
   (`viewer: [user, group:*#member]`, `can_view: viewer but not banned`), and
   Lean `sem` == oracle == set engine == real graph index over the full 210-query
   grid. Load-bearing witnesses: a user in NO group is not a viewer (the star is
   not "everyone"); a ghost group's `#member` userset IS covered (probe-2
   parity); the `banned` exclusion bites STAR-derived membership.

2. **`derived-tupleset-ttu` is reachable, and the reason it was never covered is
   worth keeping.** The leaf is emitted whenever a TTU's tupleset relation is
   tainted, and `tests/test_boolean_compile.py` has pinned three of them on
   `demorgans_law_1.fga` since P2 — so it is **not** unreachable-by-construction.
   What is hard is *driving* it: per the 2026-07-07 P5 #1 correction, TTU parents
   are the **STORED** tupleset tuples, never computed membership, so a derived
   tupleset with no `Direct` restriction holds no stored tuples and its dependent
   TTU is constantly EMPTY. That is exactly `demorgans_law_1.fga`'s shape
   (`unmatchable_conds`/`matched_roles`/`matched_users` are ∅ by construction), so
   a corpus copied from it would have raised the histogram and tested nothing.
   New corpus `TTU_USERSET_SCHEMAS['derived_tupleset_ttu']` gives the tupleset a
   storage leaf (`parent: [folder] but not detached`), and its load-bearing
   witness is the asymmetry the kind exists for: `parent(f2,d1)` is **False** (the
   exclusion bites on the tupleset relation) while `inherited(bob,d1)` is **True**
   (f2 is still a STORED `parent` tuple). Lean `sem` == oracle == set engine ==
   real graph index over the full 200-query grid.

**Scope discipline (the ZT-P3-3 forcing function).** Neither corpus may enter
`SCHEMAS` or `GRAPH_FRAGMENT`, and both scope assertions are tested:
`wildcard_userset` makes `FullScope.lean::W4Fragment.wsBare`
(`∀ sh ∈ wildcardShapes S, sh.2 = BARE`) FALSE; `derived_tupleset_ttu` is outside
`W4Fragment.computedOnly` **and** outside the ADMISSION bundle's
`GraphAdmission.ttuDirect` (`TtuTuplesetsDirect` forces a declared tupleset def to
be directs-only). Both DO run a **python-only** three-backend differential
(oracle == set engine == real `WildcardIndex`+`DeltaProcessor`, both `SetOps`),
which makes no Lean claim — the same footing as `test_multi_stratum_three_way`.

**Two checks that were designed against a fail-by-passing shape**, per the house
rule, and both were sabotaged red before being believed:
* the harness-wide wildcard floor counts **non-bare** shapes specifically.
  Swapping `[group:*#member]` for the bare `[user:*]` leaves "a wildcard" in the
  corpus and would have kept a naive floor green; the real floor goes to 0.
* `test_derived_tupleset_ttu_corpus_features` asserts the derived tupleset keeps
  a **storage leaf**. Removing it still COMPILES the `derived-tupleset-ttu` leaf,
  so `test_every_plan_leaf_kind_is_reached_by_some_corpus` stays green while the
  TTU is empty and the differential compares nothing.
Also added: `test_required_leaf_kinds_are_exactly_the_compilers_kinds`, which
reads the kind literals out of `zanzibar_utils_v1._plan_leaves`' own source — a
hand-maintained "required kinds" list is itself a check that fails by passing
once the compiler grows a branch.

Conformance count 450 → 464. Full write-up incl. every sabotage and its observed
output: `formal/history/nary-strata-coverage-2026-07-27.md` (2026-07-28 addendum).
