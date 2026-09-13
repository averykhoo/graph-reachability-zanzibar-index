# `TK68` — `GraphAdmission.usWild`, and the definition-pin regeneration it forced

**FROZEN 2026-09-13e — provenance, not a living document.** Status lines below are
as-of-then; live state is the task tree (`python scripts/task.py show TK68` /
`show P6`) and [`../HANDOFF.md`](../HANDOFF.md). Corrections are appended dated at the
top, never edited into the body.

This note exists because `formal/verify.sh` step 4c told it to. Adding a field to
`GraphAdmission` changed a definition that the headline theorems' statements depend on,
the definition pin went red, and the pin's own failure text prescribes the remedy:
*"If that is intended, regenerate the pin deliberately (`statement_pin.py --generate`),
say why in `formal/history/`, and re-check the `FINAL_REVIEW.md` claim wording."* This
is the "say why".

## 1. What changed, and why it is a fidelity fix rather than a convenience

`zanzibar_utils_v1.py` raises `UnsupportedByGraphIndex` for exactly TWO schema-scope
rejections (`CLAUDE.md` "Layout / mental model"): object wildcards on derived relations,
and **wildcard usersets over derived relations**. `FullScope.lean::GraphAdmission`
mirrored the first (`objWild`) and had **no field for the second**. The Lean admission
predicate was therefore strictly WEAKER than the shipped compiler: it admitted schemas
`compile_ruleset` refuses.

The new field closes that.

```
usWild : ∀ k ∈ taintedKeys S, S.isSubjectWildcardUserset k.1 k.2 = false
```

`GraphIndex/UsStarWrite.lean::Schema.isSubjectWildcardUserset` has two disjuncts and
Python refuses BOTH over a tainted key:

| disjunct | Python | line |
|---|---|---|
| (a) a literal `[T:*#p]` restriction, `(T,p)` derived | `zanzibar_utils_v1.py::_build_plan_tree` | `:1881-1886` |
| (b) a star-tupleset TTU through-shape landing on a derived target | `zanzibar_utils_v1.py::_reject_object_wildcard_scope` | `:1484-1492` |

Neither is dodgeable from an untainted container, which is what makes the field a total
mirror rather than a partial one:

* for (a), `zanzibar_utils_v1.py::_mentions` (`:1677-1678`) counts a userset restriction
  as a reference, so `::compute_taint` taints the container and the plan builder runs on
  it;
* for (b), the loop at `:1462` ranges over tainted keys only — but an UNTAINTED container
  whose TTU targets a derived predicate name is refused one check earlier, by
  `zanzibar_utils_v1.py::_validate_ttu_tuplesets` (`:1132-1145`).

**Direction of the change.** The headline theorems take `GraphAdmission` as a hypothesis,
so a new field makes them cover FEWER schemas. That is legitimate here for one reason and
it is worth stating plainly: the schemas removed from scope are exactly the ones the
shipped compiler REFUSES, so no shipped behaviour left the claim. This is not the
narrowing `CLAUDE.md` "Who decides" forbids (narrowing a fragment to dodge a divergence);
it is the fragment catching up to the code. Inhabitance is unaffected — all seven
`GraphAdmission` construction sites discharge the field `by decide`, so nothing became
vacuous.

## 2. Two forms, and why both

The FIELD quantifies over the computed list `taintedKeys S`, exactly as `objWild`
quantifies over `S.objectWildcards`. That keeps it `decide`-shaped at a concrete schema,
which is what lets all seven construction sites pay one line.

The CARRY is `GraphIndex/UsStarWrite.lean::NoBridgedDerived`:

```
def NoBridgedDerived (S : Schema) : Prop :=
  ∀ dt R, isDerived S (dt, R) = true → S.isSubjectWildcardUserset dt R = false
```

`FullScope.lean::GraphAdmission.noBridgedDerived` is the whole bridge between them. The
carry is deliberately SCHEMA-level and store-free — see §4 for why that is the load-bearing
property, not a stylistic one.

⚠ **The type-index trap.** `isDerived` and `isSubjectWildcardUserset` are both keyed on
`(type, relation)`, while the theorems that will consume this conclude about the predicate
STRING. A literal `[x:*#R]` restriction at an UNTAINTED key `(x, R)` is legal Python and
bridges a node whose `pred` is `R`, so `a.pred ≠ R` is false as a general claim **no
matter what premise is added**. The consumers must be RESTATED to carry the type; they
cannot be rescued by a premise. Full statement of the trap: the `2026-09-13d` Log entry on
`TK68`, and the docstring on `NoBridgedDerived`.

## 3. The evidence, and what the sweep changed

Machine-checked, all in `FullScope.lean` namespace `W4Witness`, all audited:

| pin | claims |
|---|---|
| `sx_usWild` | positive half — the live witness satisfies the field |
| `sxUsWild_usWild_false` | negative half — one `wildcard` flag refuses admission |
| `sxUsPlain_usWild` | the one-bit control: flip the flag back and it is re-admitted |
| `sxUsPlain_c_is_derived` | the control is not vacuous — `doc#c` is derived in both, and both `taintedKeys` lists agree |
| `sxUsWild_other_admission_fields_hold` | independence from every other decidable admission field |
| `sxThruDerived_wsBare_holds_but_usWild_fails` | ★ independence from `W4Fragment.wsBare` |
| `sxThruPlain_usWild` | its one-axis control — drop `but not banned` and it is re-admitted |
| `sxThru_shape_present_in_both` / `sxThru_literal_disjunct_is_false` | the axis is the TAINT, and it is disjunct (b) doing the work |
| `sxThruDerived_other_admission_fields_hold` | independence, again, at the through-shape witness |
| `sx_noBridgedDerived_applies` | behavioural arm on the CARRY, routed through the bundle |
| `sxUsWild_not_admitted` / `sxThruDerived_not_admitted` | the bundle REFUSES the two schemas Python refuses |
| `sxUsPlain_admitted` / `sxThruPlain_admitted` | the bundle ACCEPTS their one-bit-away controls |

★ **Why the `wsBare` row is the sharp one.** The `SxUsWild` pair shows independence from
the other *admission* fields, which is the precedent
(`sxLeafRef_other_admission_fields_hold`, 4c-ii step 10). It is not enough here. The
headlines take `GraphAdmission ∧ W4Fragment`, and `W4Fragment.wsBare` forces every shape
in `wildcardShapes S` BARE — which makes disjunct (a) **identically false on the whole W4
fragment**. `SxUsWild` carries a non-bare wildcard restriction, so `wsBare` is false at
it, and on the fragment alone the field could still have been dismissed as already
implied. `SxThruDerived` closes that: `wsBare` HOLDS there and `usWild` fails anyway, via
the purely schematic through-shape disjunct, which neither `wsBare` nor the
store-indexed `ttuStarFree` constrains. That is also the disjunct `P6` is about.

**(!) THE SWEEP CHANGED THE DELIVERABLE TWICE — the last four rows of that table are its
doing, and so is how they are PROVED.** `.scratch/tk68_mutation_sweep.py`, three runs;
table and analysis in §6. The two mutations that matter most are `M1` (re-range `usWild`
over `S.objectWildcards`, the plausible copy-paste slip from the field beside it) and `M2`
(re-range it over `[]`, vacuous on EVERY schema) — **the tautology attack, the one thing
the evidence block exists to refuse.**

* **Run 1** — `M1`/`M2` reddened `GraphAdmission.noBridgedDerived` and nothing else. A
  broken PROOF, not a broken claim: `P6` step 3a's lesson recurring one step later. Cause:
  **every pin re-spelled the predicate instead of reading the FIELD**, so no mutation of
  the field could move one, by construction.
* **Run 2** — added the four `_admitted` / `_not_admitted` pins, which name
  `GraphAdmission` in their statements. `M1`/`M2` **still reddened the helper alone.**
  Adding the pins was not enough, and this is the finding worth carrying out of this row:
  **Lean ERROR-RECOVERS a failed declaration.** When `noBridgedDerived`'s proof fails, Lean
  admits it anyway at its stated type, so every downstream use elaborates cleanly and a pin
  routed through it is unable — by construction — to observe anything upstream of it. The
  table read like a clean single-cause result; nothing in the output said otherwise. Filed
  in `docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations" as a general
  rule, because it applies to every sweep in this repo, and it is nastier than the
  already-recorded cross-module truncation limit (there the build visibly stops; here it
  does not).
* **Run 3** — the two refusals rerouted off `hA.usWild` directly. `M1`/`M2` now redden
  both refusal CLAIMS. `M3`/`M4` turn out **complementary** — narrow the field to disjunct
  (a) and only `sxThruDerived_not_admitted` reddens, narrow it to (b) and only
  `sxUsWild_not_admitted` does — so each disjunct is guarded by exactly one refusal, and a
  single pin would have left half the predicate free to be "simplified" away.

## 4. What this cost, what it did not, and the measurement `TK68` was missing

`TK68` was filed with the scope *"add the field next to `objWild`, discharge it where the
other admission fields are discharged, and use it at `reachedByW3d_Rnode_not_source`"*,
sized `S`. The field half is done and was indeed `S`. **The third clause is not `S`, and
the row named only half of the work**, measured here first-hand (`.scratch/tk68_declcone.py`,
2026-09-13e; counting unit: APPLICATIONS = occurrences in comment-stripped bodies, CONSUMERS
= distinct declarations containing one, CONE = transitive closure excluding the seeds):

| theorem | audited | applications | cone |
|---|---|---|---|
| `Cascade.lean::reachedByW3d_edge_source_ne_R` | yes | 1 | 14 decls / 5 files |
| `Cascade.lean::reachedByW3d_Rnode_not_source` | yes | 2 | 13 decls / 5 files |
| `CascadeStrata.lean::reachedByW3d2_edge_source_ne_R` | **no** | 1 | 35 decls / 8 files |
| `CascadeStrata.lean::reachedByW3d2_Rnode_not_source` | yes | 8 | 34 decls / 8 files |
| **union of the four** | | **12** | **47 decls / 12 files (51 with the seeds)** |

**`TK68` and the `P6` `2026-09-13d` entry both name only the W3d pair.** The two-round
twins at `CascadeStrata.lean:1595` / `:1667` are verbatim analogues — same statement modulo
`ReachedByW3d2`, and the `write` case takes the SAME
`writeLoggedRules_evalEq → writeRulesRaw → foldl_writeDirect_edges_sound` step, so it goes
false for exactly the same reason once the leg bridges. It is the W3d2 pair, not the W3d
pair, that is **on the headline path**: the W3d cone terminates below the headlines, while
the W3d2 cone reaches `FullScope.lean` and contains `graph_correct`, `graph_correct_public`,
`backend_equivalence`, `exclusion_effective`, `no_ghost_grant` and `graph_reached_inv`.

Two facts make that affordable rather than alarming, and they are why the carry is shaped
the way it is:

1. **It terminates in `GraphAdmission`, so no headline gains a hypothesis.** `graph_correct`
   (`FullScope.lean:616`) already binds `hA : GraphAdmission S T` and passes explicit field
   projections down to `graph_correct_w3d2E_d`; `hA.noBridgedDerived` is one more
   projection in that list. Same route `noLeafSubjects` / `keysNonempty` took through
   `GraphAdmission.leafScope`.
2. **The carry is store-free, so it needs no weakening lambdas.** Contrast the neighbouring
   `W4Fragment.term` (`∀ dt R, isDerived S (dt,R) = true → NoTtuTarget S R ∧
   NoStoreSubjectR T R`): it is store-indexed, spelled out at 134 declarations, and needs a
   two-line weakening lambda at 22 of them (`t :: T → T` via `List.mem_cons_of_mem`,
   `T → T.erase t` via `List.mem_of_mem_erase`). Extending *that* conclusion by a conjunct
   — the obvious-looking route — is a 134-site edit. `NoBridgedDerived` passes through a
   `write` or `remove` step verbatim.

**Not done here, and deliberately:** the restatements themselves. Both `edge_source_ne_R`
theorems must be restated (not re-premised — §2's trap) and the carry threaded through the
47. That is `P6` step 3b work, it only becomes *provable* once the write leg actually
bridges, and doing it now would mean restating a theorem to a form nothing yet needs. What
this note buys 3b is that the field, the carry and the bridge are already in the tree,
audited and swept, and the cone is measured rather than forecast.

**One pin-layout fact that makes the restatement legal:** neither theorem's STATEMENT is
pinned. `formal/headline_statements.txt` and `formal/headline_definitions.txt` contain
neither name (they pin `def:`s reachable from headline STATEMENTS, and these are theorems
that appear only in proofs). Only their NAMES are pinned, in
`formal/audited_theorems.txt`. So 3b may restate them freely provided the names stay
audited — which is exactly the "restate, don't rescue" move `TK68` prescribes.

## 5. The pins that were regenerated, and the diff

* `formal/headline_definitions.txt` — **3 changes, all intended and all shown by the gate
  before it was regenerated**: the `GraphAdmission` structure line gained `usWild` (field
  list and body), and `def:Zanzibar.Schema.isSubjectWildcardUserset` +
  `def:Zanzibar.Schema.isStarTuplesetThrough` became newly reachable from a headline
  statement, because the field names the first and the first names the second. Row count
  251 → 253. No row was removed. Regenerated with
  `python formal/conformance/statement_pin.py --generate`.
* `formal/headline_statements.txt` — **unchanged** (51/51 matched throughout). Correct:
  no headline theorem's statement text moved.
* `formal/audited_theorems.txt` — additions only, no removals; regenerated with
  `bash formal/regen_audit_pin.sh`. Adding audits was already free (the gate requires the
  live extraction to be a SUPERSET), but pinning them makes the new evidence
  un-droppable.
* `formal/FINAL_REVIEW.md` — the generated counts block regenerated
  (`python -m formal.conformance.doc_counts --generate`); the hand-maintained
  "13 fields" parenthetical was replaced by a pointer at
  `formal/headline_definitions.txt`, which is the machine-checked home for that list, and
  a `usWild` row was added to the LOUD/SILENT/MIXED classification table (class: **LOUD** —
  Python raises at compile time on both disjuncts).
* `formal/CORRESPONDENCE.md` — the `GraphAdmission` §6 row gained `usWild` in the field
  list and its Python mapping in the evidence cell.

## 6. The mutation sweep

Instrument controls carried forward, each earned by a prior failure: `M0` flips a pin's own
claim and the sweep must attribute the red to exactly that pin (`P6` step 0's inverted
error-location regex reported everything as `<unattributed>`, which read like a discovery);
anchors are read with no newline translation and asserted to occur exactly once (`P6` step
2 lost ten of fourteen anchors to a CRLF/LF mismatch); an `INERT` row is believed only
after saying what the edit was supposed to move (`P6` step 2's `M12`).

Run 3 (the landed tree). Baseline and restore green on all three runs. The live copy of
this table, with the per-row analysis, is the `FullScope.lean` docstring §"CONTROLLED —
MUTATION SWEEP over everything `TK68` added"; it is reproduced here because this note is
the one place the three runs are compared.

```text
M0   INSTRUMENT CONTROL: flip sx_usWild's own claim false -> true
     RED: sx_usWild
M1   usWild: range over S.objectWildcards (copy-paste slip from objWild)   [TAUTOLOGY]
     RED: GraphAdmission.noBridgedDerived, sxUsWild_not_admitted, sxThruDerived_not_admitted
M2   usWild: range over the empty list (vacuous on EVERY schema)           [TAUTOLOGY]
     RED: GraphAdmission.noBridgedDerived, sxUsWild_not_admitted, sxThruDerived_not_admitted
M3   usWild: forbid only the LITERAL disjunct (a)
     RED: GraphAdmission.noBridgedDerived, sxThruDerived_not_admitted
M4   usWild: forbid only the THROUGH-shape disjunct (b)
     RED: GraphAdmission.noBridgedDerived, sxUsWild_not_admitted
M5   NoBridgedDerived: weaken to the through-shape half only
     RED: GraphAdmission.noBridgedDerived
M6   NoBridgedDerived: drop the isDerived premise's direction (= false)
     RED: GraphAdmission.noBridgedDerived, sx_noBridgedDerived_applies
M7   witness: SxUsWild's wildcard flag true -> false (it becomes the control)
     RED: sxUsWild_usWild_false, sxUsWild_r_is_derived_and_bridged, sxUsWild_not_admitted
M8   witness: the SxUsPlain CONTROL's flag false -> true (it stops being one)
     RED: sxUsPlain_usWild, sxUsWild_r_is_derived_and_bridged, sxUsPlain_admitted
M9   witness: SxThruDerived's star tupleset [folder:*] -> [folder]
     RED: sxThruDerived_wsBare_holds_but_usWild_fails, sxThru_shape_present_in_both,
          sxThru_literal_disjunct_is_false, sxThruDerived_not_admitted
M10  witness: SxThruDerived's folder#viewer loses `but not banned` (= the control)
     RED: sxThruDerived_wsBare_holds_but_usWild_fails, sxThru_shape_present_in_both,
          sxThruDerived_not_admitted
M11  sx_noBridgedDerived_applies: prove it by `decide`, bypassing the bundle
     INERT (nothing reddened) — EXPECTED
```

Two rows that are NOT clean reds and are recorded as such rather than smoothed over:

* **`M11` is INERT by design, and the row is the point.** Proving the behavioural arm by
  `decide` instead of through the bundle changes nothing — which is precisely the claim in
  that theorem's own docstring: the same fact proved directly would stay green under a
  broken bridge, so it would be no pin. Read beside `M6`, which does redden the arm,
  because today the arm is routed through the bridge. (`P6` step 2's `M12` rule: before
  believing an `INERT`, say what the edit was supposed to move.)
* **`M5` reddens only a proof, and the mechanism is worth knowing.**
  `sx_noBridgedDerived_applies` cannot observe it even though it routes through the carry:
  at a CONCRETE schema, `Sx.isStarTuplesetThrough "doc" "r" = false` and
  `Sx.isSubjectWildcardUserset "doc" "r" = false` are **definitionally equal** — both
  evaluate to `false = false` — so the weakened carry still typechecks there. **An arm
  instantiated at a concrete witness is defeq-blind to a mutation that preserves the
  witness's value.** `M5` remains guarded (it reddens `noBridgedDerived`, and step 3b's
  restatement would not go through), but it is guarded by a proof, and saying so is better
  than implying a claim covers it.
