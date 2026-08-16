# bulk_backfill duplication of RC1/RC2 — measurement log

> **FROZEN 2026-08-16 — provenance, not a living document.** Status lines below are
> as-of-then and several are now false; live state: `HANDOFF.md` + the session ledger.
> Corrections are appended dated at the top, never edited into the body.
>
> ⚠ **This leg LANDED on 2026-08-11, and where this document and the archive disagree,
> trust the archive.** `docs/history/handoff-status-2026-08.md` §1 records BOTH root
> causes measured here as FIXED (RC1 `ed46e54`, RC2 2026-08-11), and §1b records the
> implementation corrections found while building the generator-coverage work this fed.
> The “READ-ONLY; tree restored” line below describes the investigation, not the repo
> today; every excerpt and line number is against `e136c8c` and has since moved.

Repo: C:\Users\user\PycharmProjects\graph-reachability-zanzibar-index (READ-ONLY; tree restored)
Date: 2026-08-10
Interpreter: C:/Users/user/anaconda3/envs/graph-reachability-zanzibar-index/python.exe
Scratch: C:\Users\user\AppData\Local\Temp\zbmeas\measure.py
HEAD: e136c8c664b53339ab6fb48f432818b194938d57

## 1. Code sites — duplication CONFIRMED (partially)

`index_v4/processor.py::DeltaProcessor.tupleset_parents` (307-323):

```python
    for e in edges:
        n = nodes.get(e.subject_id)
        if (n is not None and n.wildcard == '' and n.predicate == '...'
                and n.type in parent_types):
            out.append((n.type, n.name))
```

`index_v4/bulk_backfill.py::_BulkBackfill._tupleset_parents` (445-456):

```python
    for (sp2, st2, sn2, w2) in sorted(self.in_adj.get(ts_key, ())):
        if w2 == '' and sp2 == '...' and st2 in parent_types:
            out.append((st2, sn2))
```

The three-part filter (`wildcard == ''`, `predicate == '...'`, `type in parent_types`)
is duplicated verbatim in semantics. Same duplication in
`processor.py::stored_userset_subjects` (291-305, `n.wildcard == ''`) vs
`bulk_backfill.py::_stored_userset_subjects` (434-443, `w2 == ''`).

**CRITICAL ASYMMETRY the code-reading agent missed:** `parent_types` is NOT computed in
either file. It is compiled ONCE at `zanzibar_utils_v1.py:1761` (`plan_expr` ->
`PDerivedTTU` / `PDerivedTuplesetTTU`) from `_member_types`, frozen onto the plan node,
and BOTH files merely read `node.parent_types`. So:

- **RC1's fix site (`_member_types`) is SHARED** — one edit fixes both paths.
- **RC2's fix site (`wildcard == ''`) is genuinely DUPLICATED** — needs two edits.

## 2. Baseline (unmodified tree) — both bugs live on BOTH paths

Same TupleSource snapshot built two ways via `connectedstore.build_index`:
`bulk=False` (incremental per-tuple loop -> processor.py) and `bulk=True`
(bulk_build.py + bulk_backfill.py). Oracle = `tests/oracle.py`.

```
===== rc1 =====
   tuples landed: 3
   query          : ('...', 'user', 'alice', 'access', 'doc', 'd1')
   oracle         : False
   incremental    : True   *** DIVERGES ***
   bulk build     : True   *** DIVERGES ***
   inc == bulk    : True

===== rc2 =====
   tuples landed: 3
   query          : ('...', 'user', 'alice', 'inherited', 'doc', 'd1')
   oracle         : True
   incremental    : False   *** DIVERGES ***
   bulk build     : False   *** DIVERGES ***
   inc == bulk    : True
```

RC1 = FAIL-OPEN on both paths. RC2 = FAIL-CLOSED on both paths.
`inc == bulk` on both: pre-fix the identity gate is blind by construction (shared defect).

## 3. THE KEY QUESTION — measured by applying the fix

### Experiment A: RC1 candidate fix (`zanzibar_utils_v1.py` ~1616,
`return walk(e.base)` -> `return walk(e.base) | walk(e.subtract)`), bulk_backfill.py UNTOUCHED

```
===== rc1 =====
   oracle         : False
   incremental    : False   OK
   bulk build     : False   OK
   inc == bulk    : True
===== rc2 =====
   oracle         : True
   incremental    : False   *** DIVERGES ***
   bulk build     : False   *** DIVERGES ***
```

`pytest tests/test_bulk_build.py -q`  ->  `6 passed in 5.70s`

**=> The claim is REFUTED for RC1.** The bulk path is fixed automatically, because
`parent_types` is a compile-time artifact shared by both readers. There is nothing to
fix in `bulk_backfill.py` for RC1, and the identity gate staying green is CORRECT
(both sides genuinely moved together), not blindness.

Fallout check with the RC1 fix applied:
`pytest tests/test_bulk_build.py tests/test_compile_snapshot.py tests/test_boolean_compile.py
 tests/test_zanzibar_utils.py tests/test_processor.py -q` -> `90 passed in 8.76s`
`pytest tests/test_matrix.py tests/test_lookup_oracle.py -q` -> `56 passed in 92.34s`
(the compiled-RuleSet byte-identity snapshots survive it.)

### Experiment B (sabotage protocol): is the gate blind to a ONE-SIDED change
to the genuinely duplicated filter?

Node shape observed for a subject wildcard (RC2 store, dumped from NodeV4):
`node id=1 pred='...' type='doc' name='*' wc='any'`  (wildcard column is `'any'`, not `'*'`)

| # | one-sided edit to `processor.py::tupleset_parents` (bulk_backfill.py untouched) | `pytest tests/test_bulk_build.py -q` |
|---|---|---|
| S1 | `n.wildcard == ''` -> `n.wildcard in ('', 'any')`  (the RC2 fix direction) | **6 passed in 6.01s — GREEN** |
| S2 | function body replaced by `return []` (instrument control) | **2 failed, 4 passed in 6.22s — RED** (`[boolean]`, `[demorgan]`: `snapshot_rows differ`) |
| S3 | dropped `and n.type in parent_types` (the RC1 fix direction, done wrong) | **6 passed in 6.60s — GREEN** |

S2 is the instrument control: the gate DOES reach `tupleset_parents` and CAN detect a
one-sided divergence there. So S1/S3 going green is real blindness, not a dead code path.

**=> The identity gate is BLIND to exactly the two asymmetries that matter.** None of the
six corpora (`wildcards`, `boolean`, `demorgan`, `fanin`, `derived_member`, `demorgan1`)
contains (a) a `T:*` wildcard subject holding a stored tupleset tuple on a derived
tupleset relation, or (b) a stored tupleset parent whose entity type is outside
`parent_types`. The gate's corpus, not its comparison logic, is the gap.

## 4. Conclusions

1. Duplication of the FILTER: real (processor.py 320-322 == bulk_backfill.py 454; and
   processor.py 303 == bulk_backfill.py 441).
2. RC1 needs NO bulk_backfill.py change — its fix lives in shared compile-time code
   (`zanzibar_utils_v1.py:1616`). Claim refuted.
3. RC2 DOES need the same fix in `bulk_backfill.py:454` (`w2 == ''`) alongside
   `processor.py:320` (`n.wildcard == ''`), and likely `bulk_backfill.py:441` /
   `processor.py:303` for the userset-subject analog. Claim upheld for RC2.
4. The identity gate would NOT catch an RC2 fix applied to only one side. Worth pinning:
   add a corpus with a wildcard tupleset parent over a derived tupleset relation (the
   RC2 schema is a ready-made minimal one) — that single corpus turns S1 red.
5. Note the naive S1 edit alone is not a working RC2 fix: it crashes downstream with
   `ValueError: name=='*' and a non-empty wildcard must go together, got
   entity_name='*', wildcard=''` at `index_v4/core.py:914` via
   `processor.py::_reconcile:634`. The real RC2 fix must decide TTU semantics for a
   wildcard parent (union over all objects of the parent type), not just pass `('doc','*')`
   through as an entity name.

## 5. Tree state

All source edits reverted via `git checkout --`. Final `git status --porcelain`:
`  M HANDOFF.md` — PRE-EXISTING, not mine: hash `63a014ff7132c66839e8f2d9c0dd6565dd3a3cc9`
recorded before any edit and identical after. `git stash list` empty.
Baseline re-measured on the restored tree: `RC1: (False, True, True)  RC2: (True, False, False)`.
