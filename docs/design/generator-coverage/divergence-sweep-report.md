# Bounded exhaustive divergence sweep — oracle vs graph index vs both set engines

**Status: COMPLETE** (written incrementally as the sweep ran). 2026-08-10.

Script: `C:\Users\user\AppData\Local\Temp\divsweep\sweep.py`
Raw findings (JSONL, one per divergent query-state): `C:\Users\user\AppData\Local\Temp\divsweep\findings-<shard>.jsonl`
Per-shard progress/stats: `C:\Users\user\AppData\Local\Temp\divsweep\stats-<shard>.json`

## 0. Confirmation of the hand-found bug

Re-confirmed verbatim before the sweep was designed:

```
oracle=True  graph=False  sets=[True, True]
```

on `check(user:alice, inherited, doc:d1)` for
`parent: [folder] but not [doc]` with `(doc:d2,parent,doc:d1)` + `(user:alice,viewer,doc:d2)`.

## 1. What the sweep enumerates (stated plainly, including its caps)

443 schemas over exactly 3 types (`user`, `folder`, `doc`), in 5 families:

| family | n | what varies |
|---|---|---|
| `T` | 95 | the body of the **TTU tupleset relation** (`parent`), then `inherited: viewer from parent` |
| `V` | 145 | the body of the **TTU target relation** (`folder#viewer`), crossed with 2 tupleset bodies |
| `A` | 110 | the body of a **plain, directly-queried relation** (`doc#c`), no TTU |
| `X` | 35 | a **TTU inside a boolean arm** (`access: viewer from parent {but not,and,or} …`), crossed with 5 tupleset bodies |
| `O` | 58 | **object wildcards** (`object_wildcard_shapes`) over T-shaped and A-shaped schemas |

Arm alphabets crossed exhaustively (every ordered pair, so "which subject type is in
which arm" is a full cross, not a sample):

* entity-subject arms (tupleset slots): `[folder]`, `[doc]`, `[folder, doc]`, `[folder:*]`, `[doc:*]`
* user-ish arms (grant slots): `[user]`, `[user:*]`, `[folder#viewer]`, `[user, folder#viewer]`, `[user:*, folder#viewer]`
* operators: `or`, `and`, `but not` — each with **both** a direct-type right arm (full
  5x5 cross) and a **computed** right arm (`but not gate`, `and editor`, `or a`, …)
* plus each arm alone (unary) and a bare computed body

Per schema: every candidate tuple is probed alone, then **every subset of size 2 and 3**
of the unanimously-admitted pool (capped at 6 tuples => 6 + 15 + 20 = 41 states max).
Each state is compared over the full query grid
(subjects = every Direct-restriction shape + every TTU from-chain shape, over
{`alice`|`f1`|`d1`,`d2`} + ghost + `*`; objects = every declared relation over
{names} + `*`).

## 2. Declared caps — what a silent version of this sweep would have hidden

* **Entity pool is 1 user / 1 folder / 2 docs** (+ a ghost name + `*`). Two distinct
  users or two distinct folders are NOT crossed.
* **Ghost OBJECTS are omitted from the query grid** (ghost SUBJECTS are present). An
  object that appears in no tuple is covered de facto by `d2`/`f1` in states that do not
  mention them.
* **Tuple subsets are capped at size 3**, from a pool capped at 6 unanimously-admitted
  tuples per schema (the pool is hand-picked per family, ordered structurally-first).
  Any divergence needing 4+ simultaneous tuples is out of reach.
* **Tuple pools are hand-picked per family**, not generated — they are chosen to hit the
  structural shapes (`d2 parent d1`, `f1 parent d1`, star-subject parents, userset
  subjects, object-wildcard objects). A tuple shape I did not think of is not swept.
* **Only `check` is compared**, not `lookup` / `lookup_reverse` / `expand`.
  (`tests/test_lookup_oracle.py` is the gate for those.)
* Only **2 strata** deep in most families; no schema has a 3-level derived chain except
  where `V`'s target body is itself boolean under a boolean tupleset.
* No **removals** are exercised beyond the reset-between-states path (each state is
  reached by add-only from empty, then fully removed). Divergences that only appear
  after a remove are not directly targeted, though every state's `reset()` does exercise
  the remove path and paranoia runs on it.


---

## 3. MECHANISM ANALYSIS (written live while the sweep ran; all claims re-verified)

### 3.1 Confirmed mechanism of the hand-found bug (read out of the compiler, not guessed)

`parse_openfga_schema` on `parent: [folder] but not [doc]` produces

```
plan ('doc','inherited') tree=PDerivedTuplesetTTU(target_rel='viewer', tupleset_rel='parent',
                                                  positive=True, parent_types=('folder',))
plan ('doc','parent')    tree=PExclusion(PClosureLeaf('parent.0', storage=True),
                                         PClosureLeaf('parent.1', storage=True))
route (doc:d2 parent doc:d1)    -> [(doc:d2, parent.1, doc:d1)]      # NEGATIVE leaf only
route (folder:f1 parent doc:d1) -> [(folder:f1, parent.0, doc:d1)]
```

with `[folder, doc] but not [doc]` giving `parent_types=('doc','folder')` and routing the
same write onto **both** `parent.0` and `parent.1`.

`index_v4/processor.py::derived_stored_parents` already unions over **all** storage leaves
(so `parent.1` is walked), but `tupleset_parents` filters `n.type in parent_types`, and
`parent_types` comes from `zanzibar_utils_v1.py::_member_types`, whose `Exclusion` case is

```python
if isinstance(e, Exclusion):
    return walk(e.base)          # zanzibar_utils_v1.py:1615-1616
```

i.e. the negative arm's entity types are dropped. `_member_types` answers "who can be a
*member*" (where base-only is right) and is being used for "which entity types can appear
as a *stored* tupleset parent" (where base-only is wrong, because CLAUDE.md pins TTU
parents as stored tuples regardless of boolean evaluation). `Intersection` in the same
function unions its children — an over-approximation, which is why the `and` cells agree.

**So the hand-found bug is one instance of a general cell, not a one-off:** *any* TTU whose
tupleset relation is an exclusion introducing an entity type only in the negative arm.

### 3.2 A SECOND, independent family found in the first 50 schemas

Star-subject parents stored on a **derived** tupleset relation are dropped. One tuple, no
exclusion needed:

```
parent: [doc] and [doc:*]        (or [folder] and [folder:*], [doc:*] and [folder], ...)
tuple:  (doc:*, parent, doc:d1)
check(doc:d1#viewer, inherited, doc:d1):  oracle=True  graph=False  sets=[True, True]
```

`index_v4/processor.py::tupleset_parents` (line ~320) requires `n.wildcard == ''`, so a
stored `T:*` tupleset parent is never enumerated on a derived tupleset relation. This is
the same *shape* as the I14 / `owc x star-parent x TTU` bug fixed 2026-08-09 but on a
different code path (the delta processor's derived-tupleset walk, not
`WildcardIndex._ensure_bridges`), and it needs no object wildcard.

Interim tally, recorded live at 49/443 schemas (final numbers in section 4): 732 divergent (state, query) rows, all
`oracle=True graph=False sets=[True,True]` — every divergence so far is a graph-side
**under-report** (fail-closed), and both set engines always agree with the oracle.

### 3.3 ★★ BOTH causes become FAIL-OPEN when the TTU sits in a negative arm

The under-report is only fail-closed while the TTU is read positively. Put the same TTU
under a `but not` and the graph **grants access the oracle and both set engines deny**:

```python
import sys
sys.path.insert(0, r'C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index')
from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_oracle import _Gate

SCHEMA = """model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define viewer: [user]
    define parent: [folder] but not [doc]
    define access: [user] but not viewer from parent
"""
POOL = [('...','doc','d2','parent','doc','d1'),
        ('...','user','alice','viewer','doc','d2'),
        ('...','user','alice','access','doc','d1')]
gate = _Gate(SCHEMA, set(), POOL)
for t in POOL:
    assert gate.apply('add', t)
oracle = Oracle(SCHEMA, [OracleTuple(*r) for r in gate.present])
Q = ('...','user','alice','access','doc','d1')
print(oracle.check(*Q), gate.graph.widx.check(*Q), [s.se.check(*Q) for s in gate.sets])
# -> False True [False, False]      <== graph GRANTS; oracle + both set engines DENY
gate.close()
```

Measured, with controls (`(oracle, graph, [set:py, set:roaring])`):

| parent | access | result |
|---|---|---|
| `[folder] but not [doc]` | `[user] but not viewer from parent` | `(False, **True**, [False, False])` **fail-open** |
| `[folder, doc] but not [doc]` | same | `(False, False, [False, False])` control, agrees |
| `[doc:*] and [doc]` | same | `(False, **True**, [False, False])` **fail-open** |
| `[doc:*]` (untainted) | same | `(False, False, [False, False])` control, agrees |

So RC1 and RC2 are each a **two-signed** defect: fail-closed in a positive TTU position,
fail-open in a negated one. The previously-filed 2026-08-09 sibling was described as
"a false negative — it fails closed, so it is not a security fail-open". That framing does
not survive this cross: the same missing-parent-set defect is a live over-grant one
`but not` away.

### 3.4 Both causes are duplicated in the OFFLINE BULK path

`index_v4/bulk_backfill.py::_tupleset_parents` (line 453-455) carries byte-equivalent
filters to `index_v4/processor.py::tupleset_parents` (line 318-322):

```python
if w2 == '' and sp2 == '...' and st2 in parent_types:     # bulk_backfill.py:454
if (n is not None and n.wildcard == '' and n.predicate == '...'
        and n.type in parent_types):                       # processor.py:320-321
```

so a `build_index` bootstrap reproduces both RC1 and RC2 identically. The sweep does not
exercise `bulk_build`/`bulk_backfill` (it writes incrementally), so this is a *read of the
code*, not a measurement — but any fix must touch both sites or the differential
bulk-vs-incremental identity gate (`tests/test_bulk_build.py`) will stay green while only
half the bug is fixed.

### 3.5 Scope control for RC2: the UNTAINTED-tupleset branch is clean

RC2 is specific to the **derived (tainted) tupleset** branch
(`PDerivedTuplesetTTU` -> `DeltaProcessor.derived_stored_parents`). Where the tupleset
relation is untainted, star parents are handled correctly even when the *consumer* is
derived — measured `(oracle, graph, [set:py, set:roaring])`:

| parent (tupleset) | access | result |
|---|---|---|
| `[doc:*]` untainted | `viewer from parent but not banned` | `(True, True, [True, True])` clean |
| `[folder:*]` untainted | `viewer from parent but not banned` | `(True, True, [True, True])` clean |
| `[doc:*]` untainted | `[user] but not viewer from parent` | `(False, False, [False, False])` clean |
| `[doc:*] and [doc]` **tainted** | `viewer from parent` | `(True, **False**, [True, True])` RC2 |

So the defect is not "star parents in TTUs"; it is "star parents in TTUs **over a boolean
tupleset relation**". Same for RC1: it needs the tupleset relation itself to be an
exclusion.

---

## 4. FINAL RESULTS — the sweep completed

**Status: COMPLETE.** All 443 schemas ran (10 parallel shards, ~23 min wall).

### 4.1 Exact counts

| quantity | value |
|---|---|
| schemas **generated** | **443** |
| schemas **compiled** (accepted by parser + graph compiler) | **346** |
| schemas **compile-rejected** | **97** |
| schemas that **admitted at least one write** on all 3 backends | **346** (every compiled one) |
| tuple states **enumerated** | **13,042** |
| tuple states **admitted** (all backends unanimously accepted every tuple) | **13,042** |
| candidate tuples **unanimously rejected** at write time (not divergences) | **962** |
| schemas whose candidate pool hit the 6-tuple cap | **156** |
| **queries** compared | **2,302,854** (x4 backends = ~9.2M backend `check` calls) |
| **divergent (state, query) rows** | **3,161** |
| distinct (schema, query, direction) after dedup | **239** |
| **distinct MINIMIZED repros** | **26** |
| **distinct ROOT CAUSES** | **2** |
| admission (accept/reject) divergences between backends | **0** |
| oracle exceptions / harness crashes | **0 / 0** |
| divergences where a **set engine** disagreed with the oracle | **0** — the two set engines matched the oracle on every one of the 2.3M queries |

Every one of the 3,161 sweep-found rows is `oracle=True, graph=False, sets=[True, True]`.

### 4.2 Compile rejections, in aggregate (what the sweep could not reach)

97 of 443 schemas never ran. Breakdown by error:

| n | error | meaning |
|---|---|---|
| 81 | `CyclicDerivedDependency` | mostly family `V`: a userset arm `[folder#viewer]` inside `folder#viewer`'s own (now derived) body — a self-referential derived relation |
| 8 | `UnsupportedByGraphIndex` "derived evaluation probes the closure directly and cannot see object-wildcard …" | object wildcard declared on a **derived** relation (documented decision-15 scope rejection) |
| 5 | `UnsupportedByGraphIndex` "Zanzibar tupleset semantics read stored tuples only …" | a TTU tupleset relation with a **computed/rewritten positive arm** (e.g. `parent: [folder] or gate`) |
| 3 | `UnsupportedByGraphIndex` "symbolic object state on derived relations needs a subject-keyed residue" | object wildcard x derived, the second scope hook |

Note the asymmetry the sweep bumped into, worth flagging on its own:
`parent: [folder] or gate` is **rejected** as a tupleset ("positive arms must be direct"),
while `parent: [folder] and gate` and `parent: [folder] but not gate` are **accepted** —
the tupleset purity check only inspects the positive/base side. That accepted class is
exactly where root cause 2 lives.

### 4.3 The 26 distinct minimized repros group into exactly 2 root causes

13 repros per cause; the split is decided by whether the minimized tuple's subject is `*`.

**RC1 — `_member_types` under-approximates through `Exclusion`** (13 repros).
Distinct minimized tupleset bodies: `[folder] but not [doc]`, `[doc] but not [folder]`,
`[folder:*] but not [doc]`. All share: an entity type that appears **only in the negative
arm** of the tupleset relation's exclusion.

**RC2 — a `T:*` stored tupleset parent is invisible on a DERIVED tupleset relation**
(13 repros). Distinct minimized tupleset bodies:
`[doc:*] and [doc:*]`, `[doc:*] and [doc]`, `[doc:*] and [folder:*]`, `[doc:*] and [folder]`,
`[doc:*] and gate`, `[doc:*] but not [doc]`, `[doc:*] but not gate`, `[doc] and [doc:*]`,
`[doc] and [folder:*]`, `[doc] but not [doc:*]`, `[folder:*] and [doc]`,
`[folder:*] and gate`, `[folder] and [doc:*]`. All share: a subject-wildcard arm anywhere
in a **boolean** tupleset relation, plus a stored `(T:*, parent, obj)` tuple.

Both live in the same two-line filter, and both make the graph's set of TTU parents a
*strict subset* of the raw stored tuples that CLAUDE.md pins as the TTU semantics:

```python
# index_v4/processor.py:318-322   (and index_v4/bulk_backfill.py:453-455)
for e in edges:
    n = nodes.get(e.subject_id)
    if (n is not None and n.wildcard == ''          # <-- RC2: drops stored T:* parents
            and n.predicate == '...'
            and n.type in parent_types):            # <-- RC1: parent_types is base-arm-only
        out.append((n.type, n.name))
```

They are genuinely independent (each reproduces with the other's precondition absent, with
controls) but they share one fix site.

### 4.4 Runnable repros (all eight verified together in one process)

```python
import sys
sys.path.insert(0, r'C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index')
from tests.oracle import Oracle, OracleTuple
from tests.test_lookup_oracle import _Gate

def run(label, SCHEMA, POOL, ADD, Q):
    gate = _Gate(SCHEMA, set(), POOL)
    for t in ADD:
        assert gate.apply('add', t), f'rejected {t}'
    oracle = Oracle(SCHEMA, [OracleTuple(*r) for r in gate.present])
    print(label, '->', oracle.check(*Q), gate.graph.widx.check(*Q),
          [s.se.check(*Q) for s in gate.sets])
    gate.close()

S = lambda p, extra: """model
  schema 1.1
type user
type folder
  relations
    define viewer: [user]
type doc
  relations
    define gate: [user]
    define viewer: [user]
    define parent: %s
%s""" % (p, extra)

TTU = "    define inherited: viewer from parent\n"
NEG = "    define access: [user] but not viewer from parent\n"

POOL = [('...','doc','d2','parent','doc','d1'), ('...','user','alice','viewer','doc','d2'),
        ('...','user','alice','viewer','folder','f1'), ('...','user','alice','gate','doc','d1'),
        ('...','user','alice','access','doc','d1'), ('...','doc','*','parent','doc','d1'),
        ('...','folder','*','parent','doc','d1')]

# ---- RC1: entity type present ONLY in the exclusion's negative arm ----------
run('RC1 min (1 tuple, from-chain userset)', S('[folder] but not [doc]', TTU), POOL,
    [('...','doc','d2','parent','doc','d1')],
    ('viewer','doc','d2','inherited','doc','d1'))
run('RC1 concrete user (2 tuples)         ', S('[folder] but not [doc]', TTU), POOL,
    [('...','doc','d2','parent','doc','d1'), ('...','user','alice','viewer','doc','d2')],
    ('...','user','alice','inherited','doc','d1'))
run('RC1 FAIL-OPEN (3 tuples)             ', S('[folder] but not [doc]', NEG), POOL,
    [('...','doc','d2','parent','doc','d1'), ('...','user','alice','viewer','doc','d2'),
     ('...','user','alice','access','doc','d1')],
    ('...','user','alice','access','doc','d1'))
run('RC1 control [folder,doc] but not[doc]', S('[folder, doc] but not [doc]', NEG), POOL,
    [('...','doc','d2','parent','doc','d1'), ('...','user','alice','viewer','doc','d2'),
     ('...','user','alice','access','doc','d1')],
    ('...','user','alice','access','doc','d1'))

# ---- RC2: a stored T:* tupleset parent on a DERIVED tupleset relation ------
run('RC2 min (1 tuple, star parent)       ', S('[doc:*] and [doc]', TTU), POOL,
    [('...','doc','*','parent','doc','d1')],
    ('viewer','doc','d1','inherited','doc','d1'))
run('RC2 concrete user (2 tuples)         ', S('[doc:*] and [doc]', TTU), POOL,
    [('...','doc','*','parent','doc','d1'), ('...','user','alice','viewer','doc','d2')],
    ('...','user','alice','inherited','doc','d1'))
run('RC2 FAIL-OPEN (3 tuples)             ', S('[doc:*] and [doc]', NEG), POOL,
    [('...','doc','*','parent','doc','d1'), ('...','user','alice','viewer','doc','d2'),
     ('...','user','alice','access','doc','d1')],
    ('...','user','alice','access','doc','d1'))
run('RC2 control untainted [doc:*]        ', S('[doc:*]', NEG), POOL,
    [('...','doc','*','parent','doc','d1'), ('...','user','alice','viewer','doc','d2'),
     ('...','user','alice','access','doc','d1')],
    ('...','user','alice','access','doc','d1'))
```

Observed output (literal, 2026-08-10), printed as `oracle graph [set:py, set:roaring]`:

```
RC1 min (1 tuple, from-chain userset) -> True False [True, True]
RC1 concrete user (2 tuples)          -> True False [True, True]
RC1 FAIL-OPEN (3 tuples)              -> False True [False, False]
RC1 control [folder,doc] but not[doc] -> False False [False, False]
RC2 min (1 tuple, star parent)        -> True False [True, True]
RC2 concrete user (2 tuples)          -> True False [True, True]
RC2 FAIL-OPEN (3 tuples)              -> False True [False, False]
RC2 control untainted [doc:*]         -> False False [False, False]
```

### 4.5 Where NOTHING was found

* **Family `A` — 110 schemas, plain directly-queried relations, no TTU: zero divergences.**
  That includes the full 5x5 cross of `[user]` / `[user:*]` / `[folder#viewer]` /
  `[user, folder#viewer]` / `[user:*, folder#viewer]` under `or` / `and` / `but not`, plus
  computed right arms. The boolean machinery itself, over subject wildcards and usersets,
  is clean at check level within this bound.
* **Family `V` (TTU target body varies): every divergence traced back to the `parent`
  variant `[folder] but not [doc]`, none to the target body.** Varying the target relation
  across all 55 body shapes produced no cause of its own.
* **Object wildcards (family `O`): no cause of their own.** The 95 `O` findings are
  RC1/RC2 reached through the same tupleset bodies; the object-wildcard declaration was
  incidental.
* **Zero admission divergences** across 13,042 states.
* **Both set engines (`PySets`, `RoaringSets`) matched the oracle on all 2,302,854
  queries.** Every divergence found is graph-side.

## 5. Judgment: how many root causes, and is the hand-found bug a family?

**Two root causes. Twenty-six distinct minimized repros. The hand-found bug is one cell of
a family — RC1 — and there is a second, previously unreported family (RC2) beside it.**

* The hand-found bug (`parent: [folder] but not [doc]`) is **not special about `[folder]`
  or about `doc`**: the sweep found the mirror (`[doc] but not [folder]`) and the
  wildcard-base variant (`[folder:*] but not [doc]`), and it fires for *every* consumer
  shape tried — a bare TTU, a TTU inside `or`, inside `and`, inside `but not`.
  The predicate is exactly: **an entity type that appears only in the negative arm of a
  TTU tupleset relation's exclusion**.
* RC2 is a **different mechanism in the same function**, needs no exclusion at all
  (`[doc:*] and [doc]` suffices), and needs no object wildcard. It is the same *shape*
  as the `owc x star-parent x TTU` bug fixed on 2026-08-09 (I14) but on the delta
  processor's derived-tupleset walk rather than `WildcardIndex._ensure_bridges`, so the
  I14 fix does not cover it.
* Both are **two-signed**: fail-closed under a positive TTU, **fail-open under a negated
  one**. That upgrades the severity classification used for the 2026-08-09 sibling
  ("a false negative … not a security fail-open") — with one `but not` in front of the
  TTU, the same defect grants access the oracle and both set engines deny.
* Both are duplicated verbatim in `index_v4/bulk_backfill.py`, so a fix that touches only
  `processor.py` will leave the offline `build_index` path wrong while the
  bulk-vs-incremental differential identity test stays green.

## 6. What this sweep did NOT cover (stated plainly)

1. **Only `check`.** `lookup`, `lookup_reverse` and `expand` were not compared. RC1/RC2
   almost certainly affect them too, but that is inference, not measurement.
2. **Add-only states, size <= 3, from a pool capped at 6.** Any divergence requiring 4+
   simultaneous tuples, or a specific add/remove *interleaving*, is out of reach. The
   reset-between-states path does exercise removes with paranoia on, but no remove-order
   sweep was run.
3. **Hand-picked tuple pools.** ★ This bit: the sweep's `X` family contained the cell
   `access: [user] but not viewer from parent`, but its pool had **no `access` grant
   tuple**, so the base arm was never true and the **fail-open direction was unreachable
   by the sweep grid**. Every one of the 3,161 sweep rows is fail-closed; the fail-open
   was found only by a follow-up hand probe. A reader who took "3,161 rows, all
   fail-closed" at face value would have concluded the family is not security-relevant.
   That is the house failure mode in miniature, inside this instrument.
4. **3 types, 1 user / 1 folder / 2 docs (+ ghost + `*`).** No two-user or two-folder
   discrimination; no 4th type; no deep type chains.
5. **Ghost OBJECTS omitted** from the query grid (ghost subjects present).
6. **Depth <= 2 derived strata.** No 3-level derived chain was constructed deliberately.
7. **97 of 443 schemas never compiled** (see 4.2) — notably every self-referential
   userset-over-derived shape, and every object-wildcard-on-derived shape.
8. **No `bulk_build` / `bulk_backfill` path, no `ConnectedStore`, no PostgreSQL, no
   concurrency.** Section 3.4's claim about `bulk_backfill.py` is a code read.
9. **No nested TTU** (a TTU whose tupleset relation is itself a TTU) — the compiler
   rejects it as a tupleset ("computed/rewritten arms").
10. **Deterministic, not random.** Nothing here is a probabilistic sample: within the
    declared bounds it is exhaustive. Outside them it says nothing.

## 7. Artifacts

| file | what |
|---|---|
| `C:\Users\user\AppData\Local\Temp\divsweep\sweep.py` | **the sweep** (schema generator, grid, multi-backend trial, state enumeration) |
| `C:\Users\user\AppData\Local\Temp\divsweep\minimize.py` | merge + dedupe + tuple/schema minimizer |
| `C:\Users\user\AppData\Local\Temp\divsweep\final_repros.py` | the 8 verified repros of section 4.4 |
| `C:\Users\user\AppData\Local\Temp\divsweep\rc1.py`, `rc2.py`, `rc2b.py`, `failopen.py` | the control probes (sections 3.3, 3.5) |
| `C:\Users\user\AppData\Local\Temp\divsweep\findings-0..9.jsonl` | 3,161 raw divergence rows |
| `C:\Users\user\AppData\Local\Temp\divsweep\stats-0..9.json` | per-shard counts + the 97 compile rejections |
| `C:\Users\user\AppData\Local\Temp\divsweep\minimized.json` | the 34 minimized representatives (26 distinct) |

Nothing under the repo was modified.
