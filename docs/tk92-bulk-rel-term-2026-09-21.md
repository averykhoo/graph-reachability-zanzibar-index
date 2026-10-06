# TK92 — the bulk `_live_keys_of` mirror's `[rel]` term: REACHABLE, and INERT

**ACTIVE-PLAN** (`docs/README.md` §3). Opened 2026-09-21. Corrections append **dated at
the top**. FREEZE when `TK92` closes.

**2026-10-06 (`TK120`):** the code moved into the `src/zanzibar/` package and lost its version suffixes after this doc was written; its paths and class names are the OLD ones. Key: `docs/architecture/overview.md` § "Renamed in TK120".

Provenance labels are per claim: **READ** (verified first-hand against the live tree by
the session that wrote the line), **RAN** (the session executed it and quotes the literal
output), **REASONED**, **UNVERIFIED** (reported by a subagent and *not* re-checked here).
Every claim below is READ or RAN by this session; nothing here came from a subagent.

---

## 1. The verdict, first

`TK92` asked which of two honest outcomes holds for the leading `rel` in
`index_v4/bulk_backfill.py:811`'s `preds` list. **Neither does.** The measured answer is a
third one the row did not have on its menu:

> **The term is REACHABLE on the bulk path — the "unreachable by construction" defence is
> REFUTED — but every name it contributes exclusively reconciles to NOTHING, so deleting
> it is state-preserving. It is a harmless superset, not a repair affordance and not dead
> code.**

Consequences, and these are the decisions this session took
(`CLAUDE.md` § "Who decides"):

1. **The term STAYS.** Outcome 1 ("dead code — delete it") is factually wrong: it is
   reached. Outcome 2 ("an unpinned copy of a fail-open — give it `TK91`'s treatment") is
   also wrong: there is no fail-open on this path to pin, because `build_index` refuses a
   store that already has state, so the bulk backfill never faces derived state that
   outlived its leaf. Deleting it would also break the mirror's stated lockstep with
   `DeltaProcessor` (`bulk_backfill.py` module docstring) for zero gain.
2. **The hypothesis recorded in `tests/test_reg_tk91_live_keys_repair.py`'s docstring is
   REFUTED and must be corrected in place.** It currently reads "may be unreachable by
   construction. UNVERIFIED". Leaving a refuted hypothesis in a docstring is how the next
   session pays for this measurement twice.
3. **The real finding is bigger than the term.** No schema in the 26-entry conformance
   corpus uses a DERIVED relation as a userset subject, so the whole bulk-vs-incremental
   identity gate has never run on that input class. That — not the `[rel]` term — is what
   earns a test.

---

## 2. Why every previous sweep found it inert

**READ (2026-09-21).** `family_names` is the bulk mirror's entire data source. It is
seeded in `index_v4/bulk_backfill.py::_BulkBackfill.__init__` from the loader's `nodes`
set and grows only through `::_intern`, both keyed `(type, predicate) -> {name}` and both
skipping `wild != ''`.

So `family_names[(o_type, rel)]` — the set the `[rel]` term reads — is non-empty at
enumeration time only if some node with `predicate == rel` was interned. On the bulk path
there is exactly one pre-backfill source of such a node:

> **a stored USERSET SUBJECT** `group:eng#member` interns `(member, group, eng)` during
> the load.

Object-side writes on a derived relation cannot do it: `RuleSet.apply` routes them onto
leaf predicates (`viewer` → `viewer.0`), so the object node's predicate is the leaf, never
the public name.

**RAN (2026-09-21), the census that explains four green sweeps.** Over all 26 entries of
`formal/conformance/corpus.py::SCHEMAS`, crossing each schema's compiled `plans` keys
against the `[type#pred]` userset-subject predicates in its text:

```
group_userset          plans=[('doc','viewer')]                 userset_subj=[('group','member')]  DERIVED-AS-USERSET-> []
wildcard_group_member  plans=[...]                              userset_subj=[('group','member')]  DERIVED-AS-USERSET-> []
taint_union_userset_arm plans=[('doc','approver'),('doc','viewer')] userset_subj=[('group','member')] DERIVED-AS-USERSET-> []
residue_rich           plans=[('doc','approver'),('doc','viewer')] userset_subj=[('group','member')] DERIVED-AS-USERSET-> []
```

Four corpora use a userset subject at all, and in **none** of them is the referenced
relation derived — `group.member` is a plain direct relation in every one. **The
intersection is empty across all 26.** That is the mechanism behind
`tests/test_reg_tk91_live_keys_repair.py`'s "INERT across four whole modules" and the
`26 corpora × 5 seeds` byte-identical result (measured 2026-09-20, when there were 26
of them; `SCHEMAS` has grown since -- TK94) in
[`docs/tk91-tk80-removal-coverage-2026-09-20.md`](tk91-tk80-removal-coverage-2026-09-20.md)
§4.2: the corpora cannot reach the branch, so their green says nothing about it.

⚠ **This is the input class the identity gate has never seen**, and it is not exotic — a
derived relation used as a userset subject is ordinary Zanzibar. `parse_openfga_schema`
accepts it (RAN: the fixture in §3 compiles, `strata = [[('group','member')],
[('doc','viewer')]]`).

---

## 3. The probe, and what it measured

The probes were transient (`.scratch/tk92/`, **deleted this session** once the conclusions
landed here — `.scratch/` is gitignored, so anything recorded only there is already lost).
They are **not** promoted to `formal/probes/`: unlike the `TK77`/`TK89` census harnesses,
which exist to be re-run against a moving tree, this question is settled and its core claim
is re-verified mechanically on every gate run by
`tests/test_reg_tk92_bulk_rel_term.py::test_bulk_rel_term_is_reached_and_exclusive`. What a
re-run would need is below: the fixture is §3's schema, and the three arms are §3.3.

Fixture schema — `member` is derived **and** is a userset subject of `viewer`:

```
type user
type group
  relations
    define allowed: [user]
    define blocked: [user]
    define member: allowed but not blocked
type doc
  relations
    define viewer: [user, group#member]
```

`ops` carries `member` leaf state; `eng` is named only as a userset subject
(`group:eng#member` is the subject of `doc:d2#viewer`), so `eng` is the rel-exclusive
candidate.

### 3.1 Instrument control first

The wrapper models `preds`' two halves separately and then **asserts
`rel_names | other == what the shipped function returned`** on every call. A
rel-exclusive count of zero therefore means "the term added nothing", never "the
instrument mis-modelled the body" — the `P6` step-0 lesson (`M0`), applied to a
measurement whose interesting outcome is a zero.

A second control arm runs the same instrument over a schema with **no** derived-relation
userset (`viewer: editor but not banned`) and must report **zero** rel-exclusive names.

### 3.2 RAN — literal output

```
===== CONTROL: no derived-relation userset =====
  _live_keys_of calls: 1
    (doc,viewer): rel_term=[] other=['d1'] excl=[]
  TOTAL rel-exclusive names: 0
  MUTATED bulk == clean bulk: IDENTICAL (term is INERT here)

===== FIXTURE: member is derived AND a userset subject =====
  _live_keys_of calls: 2
    (group,member): rel_term=['eng', 'ops'] other=['ops'] excl=['eng']   <-- REL-EXCLUSIVE
    (doc,viewer): rel_term=[] other=['d1', 'd2'] excl=[]
  TOTAL rel-exclusive names: 1
  bulk == bulk=False (clean mirror): IDENTICAL
  MUTATED bulk == clean bulk: IDENTICAL (term is INERT here)
  membership moved under mutation: False

----- verdict -----
control rel-exclusive = 0 (expect 0), fixture rel-exclusive = 1
REACHABLE: the bulk [rel] term contributes names the other terms do not.
  ... and deleting it does NOT change the built state.
```

**The control reports 0 and the fixture reports 1 on the same instrument.** That pair is
what makes the fixture's `1` readable.

### 3.3 The harder arm — can a rel-exclusive name carry state?

`preds`' second term looks only at **positive** leaves, so an object whose only state sits
on a SUBTRAHEND (`but not blocked`) is invisible to it. If reconciling such an object wrote
a residue row, the `[rel]` term would be the only thing producing it — i.e. load-bearing.
**RAN**, three arms:

| arm | `eng`'s state | enumerated? | clean == MUTATED |
|---|---|---|---|
| A | `blocked` only, **and** a userset subject | yes, rel-exclusive | IDENTICAL → INERT |
| B | `blocked` only, not a userset subject | no — not enumerated at all | IDENTICAL → INERT |
| C | no state, a userset subject | yes, rel-exclusive | IDENTICAL → INERT |

Every arm also ran `clean == bulk=False`: **IDENTICAL** in all three.

### 3.4 REASONED — why arm A generalises

**READ:** `zanzibar_utils_v1.py::LeafSpec.kind` is exactly one of five values —
`closure | derived-computed | derived-userset | derived-ttu | derived-tupleset-ttu`
(`:1603` is a *different* type, `LeafFamily.kind`, whose `'userset-storage'` value is not
a `LeafSpec` kind and does not reach this code). `_live_keys_of` handles all five: two in
`preds`, three in the branch loop. The enumeration is exhaustive over leaf kinds, which is
what the §3.1 ceiling assertion confirms call by call.

Therefore a **rel-exclusive** name is precisely one with *no positive-leaf state of any
kind*. Positive leaves are the only candidate generators in `_reconcile` (subtrahends
filter, they never generate), and stars fold out of leaf state — so such a name reconciles
to the empty membership, writes no derived edge and stores no residue. Arm A is the sharp
case (subtrahend state present, still nothing written) and it came out inert.

⚠ **Labelled REASONED, not proved.** It is a claim about `_reconcile` over all schemas,
backed by a first-hand read of the leaf-kind space plus three measured arms. What is
mechanically held going forward is §5's pin, not this paragraph.

---

## 4. What this does NOT say

* **It does not touch the processor's copy.** `index_v4/processor.py::_live_keys_of`'s
  `[rel]` term is still the repair affordance `TK91` proved it to be, still a fail-open
  when deleted, and still pinned by `tests/test_reg_tk91_live_keys_repair.py`. Nothing
  here weakens that.
* **It does not claim the bulk path can never face an inconsistent store.** It claims the
  narrower, checked thing: on the only route that reaches `_BulkBackfill`
  (`connectedstore/build.py:128`, the sole caller of `bulk_build`, itself guarded by
  `build_index`'s fresh-store refusal — **READ**), the store is freshly constructed, so a
  rel-exclusive name has no derived state to repair.
* **"Live correctness bugs: 0" is undisturbed.** This item was an assurance question from
  the start and the answer is that the assurance was adequate for the wrong reason.

---

## 5. What landed

`tests/test_reg_tk92_bulk_rel_term.py` — three pins on the fixture above:

1. `test_bulk_rel_term_is_reached_and_exclusive` — `eng` is in
   `_live_keys_of('group','member')` and is **not** in the non-`rel` half. This is the
   mechanical refutation of "unreachable by construction", and it is asserted off the
   primitive the mutation would touch (the 2026-09-13e lesson: not routed through a
   helper). Deleting `[rel]` from the mirror reddens it.
2. `test_bulk_matches_incremental_on_a_derived_userset_schema` — full state identity
   between `build_index(bulk=True)` and `bulk=False` on the input class §2 showed the
   corpus has never covered. This is the coverage the item actually bought.
3. `test_fixture_keeps_eng_rel_exclusive` — the fixture guard: `eng` must stay out of every
   positive-leaf family, or pin 1 is vacuous. On a failure here the repair is to restore
   the fixture, never to relax the test (the `TK91` precedent,
   `::test_fixture_keeps_the_public_family_the_only_route`).

Sabotage evidence and the module mutation sweep are in §6.

---

## 6. Sabotage and the module sweep

The durable home is the test module's docstring (`docs/sabotage-procedure.md` ranks a
permanent test above a doc note); this section carries the full table.

**RAN 2026-09-21.** Every row is
`pytest tests/test_reg_tk92_bulk_rel_term.py -q` against the fixture as landed.
`S1`/`S2` were byte-level edits (restored from a byte copy, `git diff --stat` empty
afterwards — **not** `git checkout --`, trap (ee)); the `M*` sweep used runtime
monkeypatches loaded with `-p`, each a copy of the shipped body with one named line
changed.

| id | mutation | result | status |
|---|---|---|---|
| — | CLEAN | `4 passed in 0.38s` | — |
| `M_ID` | reconstruction, **nothing changed** | `4 passed` | ✅ FIDELITY CONTROL |
| `S1`=`M1` | drop the leading `[rel]` | `2 failed, 2 passed in 0.44s` | ✅ caught |
| `S2` | flip the pin's own claim to `not in` | `1 failed, 3 passed in 0.42s` | ✅ instrument control |
| `M2` | keep **only** `[rel]` | `2 failed, 2 passed` | ✅ caught |
| `M3` | drop the `spec.positive` filter | `1 failed, 3 passed` | ✅ caught **after** the fixture gained `qa` |
| `M4` | narrow kinds to `('closure',)` | `2 failed, 2 passed` | ✅ caught |
| `M5` | drop the `derived-computed` recursion | `4 passed` | ⚪ UNREACHABLE on this fixture |
| `M6` | drop the `derived-ttu` branch | `4 passed` | ⚪ UNREACHABLE on this fixture |
| `M7` | drop the `derived-tupleset-ttu` branch | `4 passed` | ⚪ UNREACHABLE on this fixture |
| `M8` | look the family up by `rel`, not `pred` | `2 failed, 2 passed` | ✅ caught |
| `M9` | seed `family_names` including wildcards | `4 passed` | ⚪ UNREACHABLE on this fixture |
| `M10` | `_intern` stops updating `family_names` | `4 passed` | ⚠ REACHED and MASKED — not pinned |

**5 of 10 caught.** The five greens are classified by REACHED, never by colour — the
`P6` step-2 lesson, that a mutation which does not move the property under test reports
INERT and reads exactly like a clean pin.

* `M5`/`M6`/`M7`/`M9` are **unreachable**: RAN — `member`'s leaves are
  `[('member.0','closure',True), ('member.1','closure',False)]`, `viewer`'s are
  `[('viewer.0','closure',True), ('viewer.1','derived-userset',True)]`, and the seed node
  set holds zero `wild != ''` entries (measured `[]`). There is no branch for these
  mutations to delete. That is a fact about the fixture, not evidence about the module.
* `M10` is **reached** — instrumented, `_intern` added `2` nodes — and masked: a family
  populated DURING the run is only observable if a later enumeration reads it, and across
  two strata nothing does. **MEASURED AND DELIBERATELY NOT PINNED.** Unmasking it needs a
  schema where one relation's from-chain interning lands in a family a later stratum
  enumerates; that is a larger fixture than this `S`-sized row bought.

⚠ **`M3` is the row this sweep exists for.** It was GREEN on the first pass and it was
reached the whole time: the `blocked` family was a SUBSET of the `allowed` family, so
dropping the `positive` filter enumerated exactly the same names. One tuple —
`u9 blocked group:qa`, a group with subtrahend-only state that nothing enumerates — makes
the filter load-bearing and the mutation caught. **The single sabotage (`S1`) would never
have found it**, which is the standing rule's whole claim.

---

## 7. Follow-on, filed rather than done

* **`M10` (above)** — reached, masked, unpinned. The honest next fixture is a three-stratum
  schema; not bought here.
* **The corpus gap is wider than this test.** `tests/test_reg_tk92_bulk_rel_term.py` covers
  ONE derived-userset schema. §2's census says the conformance corpus has **zero**, so
  every generated/enumerated conformance arm — not just the bulk identity gate — is blind
  to the class. Adding one `SCHEMAS` entry whose userset subject names a derived relation
  would widen `test_conformance_bulk_state.py`, `test_conformance_remove.py` and the
  generated arms at once. **Filed as `TK94`** (`NEXT`, `M`) — not part of `TK92`. ⚠ It is
  not free: `test_conformance_enum.py` enumerates every store up to a bound, so a corpus
  entry costs combinatorially there, which is why it was sized `M` and left unstarted.
