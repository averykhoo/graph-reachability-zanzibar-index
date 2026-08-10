# TTU-over-derived-tupleset under-report: root cause

Investigation date: 2026-08-10. Repo: `C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index`.
READ-ONLY: no repo file was modified. All experiments ran via monkeypatch from
`C:\Users\user\AppData\Local\Temp\ttu\`.

Repro confirmed verbatim as filed:

```
oracle True  graph False  sets [True, True]
```

---

## 0. TL;DR

The graph index stores the tuple correctly, on the correct storage leaf, and the
storage-leaf split works exactly as designed. The bug is **one line of compile-time
metadata**: `_member_types` drops the *subtract* arm of an `Exclusion`, so the TTU's
`parent_types` filter is too narrow and the read path discards a stored parent whose
entity type appears only in the negative arm.

**Fix: `zanzibar_utils_v1.py:1615-1616`**, `walk(e.base)` -> `walk(e.base) | walk(e.subtract)`.
Verified: flips the repro to 4-way agreement, flips the nested variant too, changes
nothing else in the boundary matrix.

**This corrects the diagnosis currently recorded in `docs/spec-deviations.md`** (top
entry), which says the graph "respects the boolean evaluation of the tupleset relation
instead of its stored tuples" and that "the storage-leaf split ... is evidently not being
applied when the tupleset relation is DERIVED". Both halves of that are **false** — see §5.

---

## 1. The exact mechanism, traced

### 1.1 Compile: what the schema becomes

`zanzibar_utils_v1.parse_openfga_schema` -> `compile_ruleset` (`:1130`).
Taint (`compute_taint`, `:1622`) marks both `('doc','parent')` (contains `Exclusion`) and
`('doc','inherited')` (mentions `parent`).

Measured compile output (script: `ttu/diag.py`):

```
tainted: [('doc', 'inherited'), ('doc', 'parent')]

PLAN ('doc','parent')
  PExclusion(base    = PClosureLeaf('parent.0', positive=True,  storage=True),
             subtract= PClosureLeaf('parent.1', positive=False, storage=True))
  leaf LeafSpec('parent.0', 'closure', True,  storage=True)
  leaf LeafSpec('parent.1', 'closure', False, storage=True)     <-- the [doc] arm

PLAN ('doc','inherited')
  PDerivedTuplesetTTU(target_rel='viewer', tupleset_rel='parent',
                      positive=True, parent_types=('folder',))  <-- 'doc' MISSING
namespace:
  ('doc','parent.0') LeafFamily(owner_relation='parent', index=0, positive=True,  storage=True)
  ('doc','parent.1') LeafFamily(owner_relation='parent', index=1, positive=False, storage=True)
```

Note `parent.1` is `storage=True`. `_build_plan_tree.build` (`:1716`) hits the
`Exclusion` branch (`:1735`) and recurses `build(e.subtract, not positive)`; the subtract
arm is a pure `Direct`, so `:1717-1730` gives it **its own storage leaf** via
`alloc(Direct(restrictions))` -> `_emit_leaf_expr` (`:1658`) -> one `RewriteFilter`
per restriction (`:1668`). So the negative arm is a first-class storage leaf. That part
is correct and load-bearing.

### 1.2 Write: where `(doc:d2, parent, doc:d1)` goes

`RuleSet.apply` (`:443`). `('doc','parent')` is in `compiled.derived_families`, so the
**fan-in expansion** branch (`:461-478`) fires: *every* matching `RewriteFilter` fires
(all-match, not first-match). The `[doc]` restriction in the subtract arm emitted a
`RewriteFilter` whose `if_pattern` matches `subject_type='doc'`, `predicate='...'`,
`relation='parent'`, `object_type='doc'` -> routes to `parent.1`.

Measured graph state after the two writes (script: `ttu/diag2.py`):

```
NODES:
  1 doc  d2    ...        wc=''
  2 doc  d1    parent.1   wc=''
  3 user alice ...        wc=''
  4 doc  d2    viewer     wc=''
EDGES:
  doc:d2#...      -> doc:d1#parent.1
  user:alice#...  -> doc:d2#viewer
```

**The stored tupleset tuple IS in the graph, on the storage leaf `parent.1`.** Nothing is
lost at write time.

### 1.3 Read: where it is thrown away

`index_v4/processor.py`:

- `EvalCtx.tupleset_ttu_check` (`:166`) -> `derived_stored_parents` (`:332`)
- `derived_stored_parents` -> `_ts_leaf_predicates` (`:325`) = `[spec.predicate for spec
  in plan.leaves if spec.storage]` = **`['parent.0', 'parent.1']`**. *Both* storage
  leaves, including the negative arm. Correct.
- for each leaf -> `tupleset_parents(object_type, obj_name, leaf, parent_types)` (`:307`)

`tupleset_parents`, `processor.py:317-323`:

```python
for e in edges:
    n = nodes.get(e.subject_id)
    if (n is not None and n.wildcard == '' and n.predicate == '...'
            and n.type in parent_types):          # <-- processor.py:321  THE FILTER
        out.append((n.type, n.name))
```

`parent_types = ('folder',)`. The stored parent node is `doc:d2#...`, `n.type == 'doc'`.
**Filtered out.** The parent set comes back empty, the TTU has nothing to walk, `inherited`
is empty, `check` -> `False`.

### 1.4 Where `parent_types` came from

`zanzibar_utils_v1.py:1761`:

```python
parent_types = tuple(sorted(_member_types(object_type, e.tupleset_rel, ast, frozenset())))
```

`_member_types`, `zanzibar_utils_v1.py:1592-1619`:

```python
if isinstance(e, (Union, Intersection)):
    return frozenset().union(*(walk(c) for c in e.children)) if e.children else frozenset()
if isinstance(e, Exclusion):
    return walk(e.base)          # <-- zanzibar_utils_v1.py:1615-1616   ROOT CAUSE
```

Docstring (`:1594-1597`) states the intent explicitly: *"Exclusion members come from its
base only."* That reading is right for *evaluated membership* and wrong for *stored
tuples*, and `parent_types` is used for the stored-tuple enumeration.

### 1.5 The second consumer: the fan-out tables

`_member_types` also builds the invalidation fan-out at `zanzibar_utils_v1.py:1893` and
`:1909`. For `PDerivedTuplesetTTU` (`:1909-1920`) it registers
`target_feeders[(t, target_rel)]` for `t` in `_member_types(...)` = `{'folder'}` only, so
`target_feeders[('folder','viewer')]` exists but **`target_feeders[('doc','viewer')]` does
not**. Consequence: writing `(user:alice, viewer, doc:d2)` fans out to nothing, so
`('doc','inherited')` on `d1` is never reconciled.

Measured (`ttu/fanout.py`):

```
UNFIXED:  parent_types: ('folder',)
          target_feeders keys: [('folder','viewer')]        # ('doc','viewer') MISSING
FIXED:    parent_types: ('doc', 'folder')
          target_feeders keys: [('doc','viewer'), ('folder','viewer')]
```

**Both consumers must be fixed, which is why the fix belongs at the shared source.**
Confirmed empirically: monkeypatching *only* `tupleset_parents` to drop the type filter
(`ttu/diag2.py patch`) does NOT fix the repro — the `doc:d1#inherited` node gets created
but stays edgeless, because the fan-out never fires. Fixing `_member_types` fixes both.

### 1.6 Why the reported boundary looks the way it does

- `[folder] but not [doc]`  -> `_member_types` = `{folder}`, `doc` dropped. DIVERGES.
- `[folder, doc] but not [doc]` -> `walk(base)` already yields `{folder, doc}`. Agrees.
- `[folder, doc] but not blocked` -> base carries `doc`. Agrees.
- `[folder, doc] and gate` -> `Intersection` at `:1613` **already unions all children**.
  Agrees.
- `[folder, doc]` -> plain `Direct`. Agrees.

The `Intersection` branch unioning its children while `Exclusion` returns base-only is an
internal inconsistency in the same function. `_mentions` (`:1576-1578`) *also* walks both
`e.base` and `e.subtract`. `_member_types` is the lone outlier — strong evidence this is a
plain bug, not a considered decision.

### 1.7 Scope: this is confined to derived tuplesets

An *untainted* relation cannot reach an `Exclusion` through `_member_types`, because
`_mentions` (`:1567-1572`) propagates taint through a TTU's `tupleset_rel` **and** its
`(t, target_rel)` keys, and `compute_taint` closes over that. So any relation whose
`_member_types` walk touches an `Exclusion` is itself tainted. Therefore:

- untainted compilation is byte-identical -> the `tests/snapshots/` byte-identity gate is
  not at risk (confirmed empirically: `tests/test_compile_snapshot.py` passes under the
  fix);
- in practice only **`PDerivedTuplesetTTU`** can carry a wrong `parent_types`. I probed
  the sibling `PDerivedTTU` path (`ttu/sibling.py`) by trying to reach an `Exclusion`
  through a Computed hop with an untainted tupleset. It cannot be reached: for the
  tupleset to hold *stored* tuples it must have `Direct` restrictions, and `Direct`
  restrictions inside an `Exclusion` taint the relation, which routes it back to
  `PDerivedTuplesetTTU`. With a `Computed` tupleset instead (`parent: src`), all three
  backends **reject** the write (no direct restriction admits it), so no stored parent
  exists to lose. Measured: `admit ... -> False`, all backends AGREE.

---

## 2. How the set engine gets it right

`setengine/engine.py::ttu_leaf`, `:1183-1205`:

```python
def ttu_leaf(target_rel, tupleset_rel, ot, on):
    nodes = [self.node_sets[i] for i in self._object_ids(ot, on, tupleset_rel)
             if i in self.node_sets]
    for ns in nodes:
        for pid in chain(ns.entities, ns.usersets):
            pt, pn, _pp = self.interner.key(pid)
            ...
```

`_object_ids` (`:1006-1022`) resolves the interned id for `(ot, on, tupleset_rel)` — the
**raw stored tuple set** for the *public* relation name; the set engine stores only
`TupleV1`s and builds no closure and no leaf families at all. It then iterates
`ns.entities` / `ns.usersets` — every stored parent — with **no schema-derived type
filter anywhere on the path**. There is nothing analogous to `parent_types` to get wrong.

The set engine's boolean evaluation of `parent` happens elsewhere (`sat`/`member_of`), and
never gates the TTU parent enumeration. That is precisely the pinned separation.

**The analogue to port** is therefore not a new mechanism — it is to make
`parent_types` a *sound over-approximation* of "types admitted onto this relation's
storage", rather than "types of evaluated members". The graph needs *some* filter (it
enumerates edges into a node, which can include non-parent shapes), so the right move is
widening `_member_types`, not deleting `processor.py:321`.

## 3. How the oracle gets it right

`tests/oracle.py::ttu_leaf`, `:471-492`:

```python
for tup in self.tuples:
    if not (tup.relation == tupleset_rel and tup.object_type == o_type
            and tup.object_name in objs):
        continue
    p_type, p_name = tup.subject_type, tup.subject_name
    ...
```

It scans `self.tuples` — the raw admitted tuple list — matching on `relation`,
`object_type`, `object_name` only. **No type filter, no schema consultation, no call to
`sat` on the tupleset relation.** This is a genuine stored-tuple walk, not something
incidental: the tupleset relation's own boolean evaluation is never consulted at this
point, exactly as CLAUDE.md pins. Confirmed independent (the oracle imports nothing from
the backends and parses the DSL itself).

## 4. The proposed fix

### 4.1 The change

**`zanzibar_utils_v1.py:1615-1616`**, inside `_member_types`:

```python
if isinstance(e, Exclusion):
    return walk(e.base) | walk(e.subtract)
```

plus the docstring at `:1594-1597`, which currently asserts the wrong rule and must be
rewritten to say: *these are the entity types that can be STORED as a direct subject of
the relation (the TTU parent-enumeration domain), which includes an Exclusion's subtract
arm because admission routes those tuples onto a storage leaf.*

**Compile-time, not read-time.** `processor.py:321` is correct as written given a correct
`parent_types`; do not delete the filter there.

### 4.2 Verified

- repro: `oracle True graph True sets [True, True]` (`ttu/repro_fixed.py`)
- boundary matrix, before -> after (`ttu/boundary.py`):

```
                                                       BEFORE          AFTER
A  [folder] but not [doc]                              DIVERGE         AGREE
B  [folder, doc] but not [doc]                         AGREE           AGREE
C  [folder, doc] but not blocked                       AGREE           AGREE
D  [folder, doc] and gate                              AGREE           AGREE
E  [folder, doc]                                       AGREE           AGREE
F  [folder] and gate  (write correctly REJECTED)       AGREE           AGREE
G  [folder] but not ([doc] but not [folder])           DIVERGE         AGREE
```

Variant G (nested exclusion) is a **second, previously unreported instance** of the same
bug, found by this investigation.

- **The project's own lookup-surface oracle gate agrees** (`ttu/regress.py`). Running
  `_Gate.assert_surfaces` — `tests/test_lookup_oracle.py:388`, the full
  `lookup`/`lookup_reverse`/`expand` brute-force-vs-oracle battery over the whole
  candidate grid, on both backends — across an add / remove / re-add walk:

```
UNFIXED: Failed: lookup/oracle divergence (full lookup surface):
         graph.lookup('viewer','doc','d2') vs oracle on inherited doc:d1:
         graph=False oracle=True
FIXED:   full lookup/expand/reverse oracle surface: PASSED
```

- **The exclusion itself is not weakened by the fix.** Under the fix, across the same
  walk, `check(doc:d2, parent, doc:d1)` stays `False` on all four backends while
  `check(folder:f1, parent, doc:d1)` stays `True`. The negative arm still subtracts; it
  just no longer also erases the tuple from the TTU's parent enumeration. Add/remove/
  re-add is symmetric.

### 4.3 Blast radius

Functions whose behaviour changes: `_member_types` only, and only on schemas where a
tainted relation reachable from a TTU carries a `Direct` restriction inside an
`Exclusion` subtract arm. Downstream consumers, all widened monotonically (a
strictly larger type set):

| consumer | line | effect of widening |
|---|---|---|
| `_mentions` (taint) | `:1570` | possibly more taint. Conservative and correct: if the TTU can read `(doc, viewer)`, taint must follow it. |
| `_is_pure` | `:1652` | possibly "not pure" -> derived path instead of closure leaf. Conservative. |
| `parent_types` on `PDerivedTTU`/`PDerivedTuplesetTTU` | `:1761` | the fix |
| `target_feeders`/`dependents` fan-out | `:1893`, `:1909` | more invalidation edges -> more reconciles. Fail-safe direction. |

**Corpus exposure measured** (`ttu/corpus.py`, running the §4.5 detector over every
`.fga` in the repo):

```
scanned 11 .fga schemas, 0 carry the shape
```

The corpus does contain bracketed subtrahends — `tests/scenarios/__init__.py:114`
(`[user] but not [user:*]`), `tests/test_boolean_compile.py:405` (`[user] but not
[user]`), `tests/test_processor.py:146` — but in **every** one the subtrahend's types
already appear in the base arm, so `walk(e.base)` happens to return the right set and the
bug is invisible. And none of them is the tupleset of a TTU. That conjunction
(type present *only* in the subtrahend **and** the relation used as a TTU tupleset) is
what no fixture has. This both explains the survival and predicts a near-zero blast
radius on the existing corpora.

**Full sweeps under the fix** (monkeypatched via a pytest plugin; repo untouched, `git
status` clean throughout):

```
tests/                773 passed in  868.31s (0:14:28)
formal/conformance/   494 passed in 1472.52s (0:24:32)
                     ---
                     1267 passed, 0 failed, 0 skipped, 0 xfailed
```

Zero failures on either leg. `tests/` includes `test_compile_snapshot.py` (the
byte-identity gate on untainted compilation — empirically confirming the §1.7 argument),
`test_matrix.py` (the 4-way validation matrix under both `SetOps`), `test_lookup_oracle.py`
(the lookup-surface oracle gate), `test_hypothesis.py`, and the I1-I14 invariant modules
with paranoia on.

A targeted re-run of the derived/boolean-heavy modules alone
(`test_boolean_compile` + `test_processor` + `test_matrix` + `test_invariants_derived` +
`test_compile_snapshot` + `test_lookup_oracle`) also came back `136 passed`.

Counts exceed the CLAUDE.md floors (`tests/` 762, conformance 465), so no coverage was
lost. **Caveat:** this is `pytest` directly, not `bash formal/verify.sh` — the phased gate
additionally pins Lean theorem names/statements and the `CORRESPONDENCE.md` anchors. The
real fix still needs the ten phased gate runs plus the fuzz sweep.

Risk notes:
- **Monotone widening only, and over-inclusion is structurally safe.** `parent_types` is
  a coarse *type gate*, not the correctness mechanism: `tupleset_parents`
  (`processor.py:317-323`) independently requires a real direct incoming edge on a
  **storage** leaf and `n.predicate == '...'` and `n.wildcard == ''`. Widening the type
  set therefore cannot invent a parent that has no stored tuple — it can only stop
  discarding one that does. No previously-True answer can become False. The direction is
  toward more grants, which warrants a security read, but it is convergence *to the
  oracle*, which is the spec.
- **Adjacent question this fix deliberately does NOT touch.** `_member_types` also
  recurses through `Computed` (`:1607`) and `TTU` (`:1608-1612`). Whether a `Computed`
  reference should contribute to a *stored-parent* domain at all is a separate modelling
  question (rule-routed edges are not stored tuples). That behaviour is unchanged here;
  flagging it only so it is not conflated with this fix.
- **Snapshot gate safe** by the §1.7 argument (untainted compile cannot reach an
  `Exclusion`); confirmed by the full `tests/` sweep.
- **Perf**: more `target_feeders` entries means more reconciles on writes to the newly
  covered `(type, target_rel)` keys. Bounded by schema size.
- **It is an algorithm change** (changes the modelled parent-enumeration domain), so per
  CLAUDE.md it needs the full phased gate **plus a multi-seed fuzz sweep**.
- **Lean impact: none expected.** Neither `_member_types` nor `parent_types` nor
  `tupleset_parents` / `derived_stored_parents` appears anywhere in
  `formal/CORRESPONDENCE.md`, so `verify.sh lean`'s `file::symbol` anchor resolution is
  unaffected and no anchor needs updating. `CORRESPONDENCE.md:421` further records that
  the Lean fragment admits **no TTU/userset/tupleset dependency edges** — the shape is
  outside the modelled fragment entirely. So no Lean definition becomes dead code. This
  is worth a `CORRESPONDENCE.md` §7 gap note rather than a model change, and it is
  another datapoint for the "Lean-excluded shapes are where the corpora are thin"
  observation already recorded in `docs/spec-deviations.md`.
- House order per `docs/spec-deviations.md`: **pin RED first in its own commit**, then fix.
  The pin should cover variant A *and* variant G.

### 4.4 Which invariant would have caught it — none

I checked `index_v4/invariants.py` I1-I14 and `processor.audit_fixpoint`:

- **I1/I2/I13** count/DAG/refcount algebra — blind to plan metadata.
- **I3/I14** bridge and crossing-middle hygiene — wildcard topology only.
- **I4** namespace: `parent.0`/`parent.1` are properly registered `LeafFamily`s. Passes.
- **I5** derived exclusivity: the write went through `RuleSet.apply` routing. Passes.
- **I6/I7** residue hygiene/versioning: the residue is *consistently* empty. Passes.
- **I9** (`processor.py:1281-1291`) re-runs `reconcile` and demands a fixpoint. **This is
  the one that should have caught it and structurally cannot**: `reconcile` reads the same
  `plan.leaf_nodes[i].parent_types`, so it reproduces the same wrong answer and agrees
  with itself. Classic house failure mode — *the instrument shares the subject's bug*
  (`docs/sabotage-procedure.md`). Paranoia was ON (`_Gate(paranoia=True)`) throughout the
  repro and stayed green.
- **I11/I12** are differential snapshot invariants across *graph* stores; both graph
  stores are wrong identically.

Nothing in the suite compares the compiled plan metadata against the compiled *admission*
metadata, which is exactly the seam that broke.

### 4.5 A new invariant IS warranted — and I built and validated one

**Proposed: TTU parent-type coverage.** For every plan leaf node of kind `derived-ttu` /
`derived-tupleset-ttu`, `parent_types` must be a superset of the bare-entity subject types
that the *admission* path will accept onto that tupleset relation's storage leaves.

The instrument reads the emitted `RewriteFilter`/`Filter` `if_pattern`s directly — it never
calls `_member_types`, so it is genuinely independent of the thing it guards.

Validated (`ttu/detector.py`), literal observed output:

```
-- unfixed --
DETECTOR: RED  violations=[(('doc','inherited'), 'parent', 'viewer', ('folder',), ('doc',))]
-- fixed --
DETECTOR: GREEN (no violations)
```

This is a compile-time check, so it is O(schema) and free at runtime — it can go in
`compile_ruleset`'s existing post-compile validation block (near the
`RewriteFilter routes outside a leaf family` assertion at `zanzibar_utils_v1.py:2016-2019`),
which already does exactly this style of self-audit. Making it a hard compile failure is
the "mechanical refusal over a doc warning" that CLAUDE.md prefers.

A runtime state variant is also possible (for every direct edge from a bare entity of type
T into a tupleset storage-leaf family, assert T is in the parent_types of every TTU node
reading that tupleset) — but it is strictly weaker (only fires once a tuple exists) and
costs an edge scan. **Recommend the compile-time form.**

---

## 5. Is it an ADMISSION question? — No. Recommendation: keep admitting; fix the read domain.

All three backends currently admit `(doc:d2, parent, doc:d1)`.

**The steelman for rejecting, stated fairly.** In variant A specifically
(`parent: [folder] but not [doc]`), `doc` appears *only* in the subtrahend, and since the
base arm admits only `folder`, the subtraction is a **membership no-op**: `check(doc:d2,
parent, doc:d1)` is `False` whether or not the tuple is stored. So in variant A the *only*
observable consequence of admitting the tuple is the TTU parent walk. One could therefore
define the admission domain as "types named in **positive** arms", under which variant A
rejects the write and the graph's narrow `parent_types` becomes retroactively correct with
no read-path change. That is a genuinely self-consistent design — I do not want to
strawman it. Note it would *not* break variant B (`[folder, doc] but not [doc]`), where
`doc` is in a positive arm, and where the stored `doc` tuple demonstrably does real work:

```
admit (doc:d2,    parent, doc:d1) -> True
admit (folder:f1, parent, doc:d1) -> True
  check doc:d2    -> oracle=False graph=False sets=[False, False]   # subtracted
  check folder:f1 -> oracle=True  graph=True  sets=[True,  True ]
```

**Why I nonetheless recommend admitting.** Four reasons, in increasing weight:

1. **Admission is already coherent and already refuses the genuinely undeclared case.**
   Boundary variant F (`parent: [folder] and gate`, no `doc` restriction anywhere)
   measured `admit=False` for the same tuple. Admission is applying a defensible rule —
   "some declared restriction in this relation's expression names this type" — not being
   sloppy. The compile-time *plan* table simply fails to agree with the compile-time
   *admission* table. Two tables disagree, and this is a question of which one to move.
2. **Rejecting is a narrowing, and narrowings are not backward compatible.** Widening
   `parent_types` is purely additive. Tightening admission invalidates tuples that three
   backends have been accepting, i.e. potentially data already at rest.
3. **It is a 3-backend change, not a 1-backend fix.** Rejecting means changing
   `RuleSet.apply`'s admission **and** `SetEngine._validate` **and** the oracle. The
   measured divergence is graph-vs-(oracle + both set engines); rejecting means making
   the three conform to the one.
4. **The oracle is the spec, and it admits.** CLAUDE.md: *"Never edit a golden or oracle
   result just to make a refactor pass — the oracle and goldens ARE the behavioral
   spec."* Rewriting the oracle's admission so the graph's existing answer becomes right
   is exactly that move wearing a different hat. The house rule for this precise
   situation is already written down for the 2026-08-09 bug: *"Three backends to one, and
   the oracle is the spec — so the **graph** is wrong."*

Also relevant: `parent: [folder] but not [doc]` is not valid upstream OpenFGA DSL (`but
not` there takes a relation reference, not a type-restriction list), so this repo's parser
is a deliberate superset and there is no upstream authority to defer to. The oracle is the
authority, and it admits.

**Recommendation: keep admitting; fix `_member_types`.** But because the steelman is
real, this is worth recording as an explicit adjudication in `docs/spec-deviations.md`
rather than as a silent bug fix — *"the admission domain of a relation is every type named
by any Direct restriction anywhere in its expression, including inside an Exclusion
subtrahend; the plan's TTU parent domain must equal it"* — so the next person does not
relitigate it. The compile-time invariant in §4.5 then mechanically enforces that the two
tables agree, in either direction, forever.

Also worth noting: `parent: [folder] but not [doc]` is not valid upstream OpenFGA DSL
(`but not` there takes a relation reference, not a type-restriction list); this repo's
parser is a deliberate superset. So there is no upstream authority to defer to — the
oracle is the authority, and it admits.

**Recommendation: keep admitting. Fix `_member_types`.** The proposed compile-time
invariant (§4.5) then *permanently enforces* the agreement between the admission table and
the plan table, so the two can never drift apart again in either direction.

---

## 6. Shared mechanism with the 2026-08-09 I14 fix? — No, confirmed.

Your suspicion is right, and the repo already says so. Verified two ways.

**Code reading.** The I14 fix is `WildcardIndex._ensure_entity_middles`
(`index_v4/wildcard.py:279-298`) plus `_is_bridge_middle` (`:300`), `_sync_entity_middles`
(`:336`), `_maybe_remove_bridges` (`:361`). Every line of it is about **wildcard bridge
topology**: `schema_info.crossable_shapes`, `bridged_in_shapes`/`bridged_out_shapes`,
`w_all -> concrete -> w_any` crossing middles, implicit-node GC. It touches no plan, no
`parent_types`, no leaf family, no `Exclusion`, and nothing in `zanzibar_utils_v1`'s taint
or member-type analysis. Conversely the bug here needs no wildcard at all — the repro has
zero `*` nodes (see the node dump in §1.2), so the I14 machinery is not even reachable.

**Repo record.** `docs/spec-deviations.md` (top entry, filed by the session that found
this) already states: *"different mechanism (that one was a missing crossing middle in the
wildcard bridge; this one is TTU tupleset routing on a derived relation)"*.

What they **do** share is a *class*, and the existing entry names it correctly: graph-only
under-report, three backends to one, on a shape no differential corpus exercised —
"shapes that the Lean fragment excludes are exactly where the differential corpora are
thin".

**One correction to the filed entry**, though. Its mechanism sentence reads:

> it respects the boolean evaluation of the tupleset relation instead of its stored
> tuples ... the storage-leaf split that exists precisely to honour it is evidently not
> being applied when the tupleset relation is DERIVED.

Both clauses are wrong, and the second is actively misleading for whoever picks this up:

- The storage-leaf split **is** applied. `_ts_leaf_predicates` (`processor.py:325`)
  correctly returns both `parent.0` and `parent.1`, including the negative arm's leaf,
  and `derived_stored_parents` reads both. Measured.
- The read path does **not** consult the boolean evaluation of `parent`. It never calls
  `parent`'s plan. It reads raw direct edges into the storage-leaf nodes — a genuine
  stored-tuple walk.

The single failure is the `parent_types` *type filter* on that walk, sourced from a
compile-time set that omits the subtract arm. Anyone who fixes the entry as written would
go rewriting the leaf-routing/storage-split machinery, which is correct code.

---

## 7. Artifacts

All under `C:\Users\user\AppData\Local\Temp\ttu\`, all read-only w.r.t. the repo:

- `repro.py`        — the filed repro, confirmed
- `diag.py`         — compile dump (plans, leaves, namespace)
- `diag2.py`        — graph node/edge dump; `patch` arg = read-path-only monkeypatch (insufficient)
- `patchfix.py`     — the `_member_types` fix as an importable monkeypatch
- `repro_fixed.py`  — repro under the fix (4-way agreement)
- `boundary.py`     — the 7-variant boundary matrix, before/after
- `detector.py`     — the proposed compile-time invariant, RED before / GREEN after
- `zzfix_plugin.py` — pytest plugin form of the fix, for the blast-radius sweep
- `regress.py`      — add/remove/re-add walk + the full `assert_surfaces` oracle battery
- `fanout.py`       — `parent_types` / `target_feeders` dump, before and after
- `corpus.py`       — detector swept over every `.fga` in the repo
- `admission.py`    — Q5 evidence that a stored negative-arm tuple does real work
