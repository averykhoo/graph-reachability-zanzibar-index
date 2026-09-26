---
id: TK106
title: refuse boolean tuplesets: a from-tupleset must be direct-only, as in OpenFGA
brief: user go 2026-09-26: drop the tainted-tupleset exemption; from walks STORED tuples so the boolean part was ignored
pri: NOW
size: L
deps: []
related: [ASK-1, TK104]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-26
moved: 2026-09-26b
updated: 2026-09-26b
closed: 2026-09-26b
---

**User decision, 2026-09-26: refuse boolean tuplesets** ("Okay yes let's close block this shape then"), as OpenFGA does ("the relation is referenced in at least one tupleset and thus must be a direct relation", `pkg/typesystem/typesystem.go::isUsersetRewriteValid`, READ 2026-09-26).

Why: `x from parent` walks the STORED `parent` tuples, never the computed relation. A boolean tupleset (`parent: [folder] but not blockedp`) therefore has its boolean part silently ignored by every `from`. PROBED 2026-09-26 on ParityEngine (all three backends agree): `check(f1 parent d1)` is False, but `alice view d1` via f1 is True. The extreme form is `tupleset_shapes.fga`'s `mixed_parent: [folder] but not [doc]`: a doc link is writable only because it is excluded, and `from` walks it.

Change: drop the `ts_key not in tainted` exemption in `zanzibar_utils_v1.py::_validate_ttu_tuplesets`, so every tupleset is `_directs_only` (a Direct, or a union of Directs). Effect: `GraphAdmission.ttuDirect` goes MIXED -> LOUD. No schema enters the headline premise, because its silent half was already shadowed by `W4Fragment.computedOrDirect`. Every refused schema has a behaviour-preserving rewrite: split into `parent_link: [<every type named in parent>]` and use it in the `from`.

## Read first

- `zanzibar_utils_v1.py::_validate_ttu_tuplesets` -- the exemption
- `formal/conformance/test_graphadmission_scope_pin.py` -- the `ttuDirect` row
- `docs/ask1-schema-self-consistency-2026-09-26.md` -- the method this follows

## Log

### 2026-09-26

**HANDOFF 2026-09-26: NOT STARTED -- nothing in code has changed.** The user decided and asked for it to be the next item.

**Rule after the change:** the relation after `from` must be `_directs_only` (`[folder]`, `[folder, doc]`, `[folder] or [doc]`), whatever its taint.

**Blocked patterns (REASONED from the stored-tuple rule, shown to the user 2026-09-26):**

1. `parent: [folder] but not blockedp`: `from` inherits from every stored parent, blocked or not.
2. `parent: [folder] and vetted`: `from` ignores the vetting.
3. `parent: [folder] but not [doc]`: a doc link is writable only because it is excluded, and `from` walks it. This is the RC1 pin, `tupleset_shapes.fga::mixed_parent`.
4. `parent: approved_parent` (a reference to a boolean relation): `from` sees no parents at all, because `parent` stores nothing.
5. Any boolean tupleset containing a reference or another `from`: only `parent`'s own stored tuples are walked.

**Behaviour-preserving rewrite for every one:** `parent_link: [<every type named in parent's restrictions>]`, used by the `from`, plus an optional `parent: parent_link but not ...` if something queries `parent` directly. Stored `parent` tuples migrate to `parent_link`.

**Intended-meaning rewrites:**
- user blocklist: `view: (viewer from parent) but not blocked`, exact;
- link-level block or allow: store only the effective links, since the app maintains them, exact;
- `(viewer from parent) but not (viewer from blockedp)` and `(viewer from parent) and (viewer from vetted)` are NOT exact: they over-block and over-grant respectively.

**Implementation map.** REASONED by analogy with ASK-1, NOT MEASURED -- run the census first:

- `zanzibar_utils_v1.py::_validate_ttu_tuplesets`: drop `ts_key not in tainted` from the `_directs_only` check, reword the error, and fix the docstring's "Tainted (derived) tuplesets are exempt". Decide whether the oracle needs a twin. It has no `_validate_ttu_tuplesets` today, so the refusal is compile-time (`UnsupportedByGraphIndex`), not parse-time. Check what `SetEngine` construction calls.
- `formal/conformance/test_graphadmission_scope_pin.py`: `ttuDirect` MIXED -> LOUD (LOUD 13 / MIXED 1 / SILENT 0), with a dated docstring update. In `graphadmission_scope_probes.py`, the `ttuDirect.derived/derived-tupleset` probe expected outcome becomes a raise, and its `SHADOWED` entry goes. `test_every_mixed_row_has_a_shadowed_probe` still needs `storeValid`'s.
- `formal/conformance/w4_scope_probes.py`: any probe with a boolean tupleset (`PYTHON_OUTCOME`) may flip ADMITTED -> RAISED. Test (F) in `test_conformance_fragment.py` is what catches it.
- `tests/fga_schemas/tupleset_shapes.fga`: `approved_parent` and `mixed_parent` (and their `via_*` consumers) become refused. That removes the RC1 regression pin's only home (`tests/test_schema_shapes.py` module docstring). Record the retirement: RC1's shape is now unreachable. The snapshot golden gets regenerated deliberately, with an entry in `docs/spec-deviations.md`. `REQUIRED['tupleset_shapes']`, `EXPECTED_UNREACHED` (`ttu.ts:Intersection`, `ttu.ts:neg-only-type`, maybe `ttu.ts:Exclusion`) and `MIN_COOCCURRING_PAIRS` move. Measure the pair loss the same way as ASK-1 (old fixture with the refusal off vs new). If the fixture keeps no arm, decide whether it survives at all.
- `tests/genswarm.py`: the `ts_boolean` and `ts_negonly` switches (maybe `ts_computed`) now produce refused configs. Add a Rejection witness, and check `test_every_rejection_witness_family_is_actually_exercised_by_the_enumerator` and `test_no_enumerated_config_is_silently_dropped`.
- `formal/lean`: `GraphAdmission.ttuDirect`'s field comment ("stronger than the mechanism it cites") and `FullScope.lean`'s classification note. Docs only; no statement changes.
- `CLAUDE.md` Gotchas bullet on self-consistency: add the tupleset rule. `formal/ARCHITECTURE.md` and `formal/CORRESPONDENCE.md` classification lines.
- Floors: re-measure `MIN_TESTS_ALL` / `MIN_CONF_ALL` / `MIN_CONF_REST`, then `python -m formal.conformance.doc_counts --generate`.

**Assurance:**
- a positive pin that every blocked pattern (1-5) is refused on every construction path (`parse_openfga_schema`, `SetEngine`, `ConnectedStore`, ParityEngine);
- a pin that each behaviour-preserving rewrite gives the SAME answers as the old schema on the old data;
- a mutation sweep with an M0 control (`docs/sabotage-procedure.md`).

### 2026-09-26b

**STARTED 2026-09-26b. Plan doc: `docs/tk106-boolean-tuplesets-2026-09-26.md` (ACTIVE-PLAN).**

Design decisions (the model's, recorded in the doc's § 1):

- D1: refuse at PARSE time in both parsers, not at graph compile time. `SetEngine.__init__` degrades past `UnsupportedByGraphIndex`, so the row's original map, which drops the exemption in `_validate_ttu_tuplesets`, would have left the set engine and the oracle accepting the schema. Landed in the working tree: `zanzibar_utils_v1.py::_validate_tuplesets_direct`, called from `parse_schema_ast` and `parse_openfga_json`, plus the oracle twin `tests/oracle.py::_validate_tuplesets_direct`.
- D2: the rule also covers UNTAINTED computed tuplesets. That is OpenFGA's rule and the same silent-ignore bug; before, the graph refused them and the set engine degraded past them.
- D3: userset restrictions in tuplesets are NOT folded in. They have the same gap, but the user did not approve them for this item, so they are a follow-up.

PROBED: both parsers refuse patterns 1-5a and accept direct, union-of-directs and star tuplesets.

NEXT: the breakage census (full `tests/` and conformance with `--continue-on-collection-errors`), recorded in the doc's § 3.

**CHECKPOINT 2026-09-26b. Resize M -> L: the census is done, and the fix list is long.**

Docs (tracked): `docs/tk106-boolean-tuplesets-2026-09-26.md` has the decisions (§ 1), the censuses (§ 3a-c) and the generator attribution (§ 4). `docs/tk106-triage-2026-09-26.md` has per-test fix classes (a subagent report, UNVERIFIED).

LANDED in the working tree, not yet gated:
- the parse refusal in both parsers;
- `tests/genswarm.py` reworked. MEASURED: 685 enumerator cells, 0 generator-gap cells, 229 lost cells all by design.

Census: `tests/` gave `68 failed, 28 errors`, plus two modules that fail to collect. Conformance gave `14 failed`.

Fixture impact: 2 of 18 refused, `tupleset_shapes.fga` (RC1's only pin) and `demorgans_law_1.fga` (whose `from` chain was always constantly empty).

REMAINING, in order:
1. The `test_generator_coverage.py` floors and the two driving controls: `_CONTROL_SWITCHES` has `ts_negonly`, which is now refused.
2. Retire `tupleset_shapes.fga`. Cut `demorgans_law_1.fga`'s three `from` relations.
3. The per-module fixes from the triage doc.
4. Conformance: the `derived_tupleset_ttu` corpus entry and the two `ttuDirect` probes (MIXED -> LOUD).
5. `tests/test_hypothesis.py::_TUPLESET_BODIES`.
6. Floors (`MIN_TESTS_ALL`, `MIN_CONF_ALL`, `MIN_COOCCURRING_PAIRS` measured 813 -> 591 by the agent, `MIN_FIXTURES` 15 -> 14) and `doc_counts`.
7. File the dead-code follow-up row (the triage doc's section 18: `PDerivedTuplesetTTU`, the processor's `derived_stored_*`, the `bulk_backfill` twins; `formal/CORRESPONDENCE.md` cites `PDerivedTuplesetTTU`).
8. Investigate the userset-bridge-release-leak pin, which is at risk (triage § 4).
9. The gate, then commit.

DONE 2026-09-26b. A `from`-tupleset must be direct-only. Both parsers refuse the rest at PARSE time, tainted or not: `zanzibar_utils_v1.py::_validate_tuplesets_direct` (called from `parse_schema_ast` and `parse_openfga_json`), with the oracle twin `tests/oracle.py::_validate_tuplesets_direct`. `GraphAdmission.ttuDirect` moves MIXED -> LOUD, giving LOUD 13 / MIXED 1 / SILENT 0.

Map and all measurements are in `docs/tk106-boolean-tuplesets-2026-09-26.md` (decisions D1-D6, censuses, generator attribution, RC / memo / bulk / leak re-sabotage, mutation sweep). Companions: `docs/tk106-triage-2026-09-26.md` and `docs/tk106-agent-reports-2026-09-26.md`.

Pins:
- `tests/test_tupleset_must_be_direct.py` (75 tests; mutation sweep M0-M5, all caught).
- RC2 / memo / bulk / userset-leak moved to legal schemas and re-sabotaged first-hand.
- RC1 is now a refusal pin.

Fixtures: `tupleset_shapes.fga` retired; `demorgans_law_1.fga` trimmed.

Follow-ups: `TK107` (dead tainted-tupleset code), `TK108` (userset restrictions in tuplesets; needs a user go).

Gate: all ten phases, recorded in the commit.
