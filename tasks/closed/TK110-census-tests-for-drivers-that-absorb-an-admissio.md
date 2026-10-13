---
id: TK110
title: census tests/ for drivers that absorb an admission refusal into a smaller compared store
brief: TK71 follow-up: formal/conformance absorbers pinned; tests/ has 17 files of refusal catches, unclassified
pri: LATER
size: M
deps: []
related: [TK71]
parent:
labels: []
source: hand
source_hash:
created: 2026-09-27b
moved: 2026-10-13
updated: 2026-10-13
closed: 2026-10-13
---

## What it is

`TK71` (2026-09-27) found that three drivers in `formal/conformance/` ABSORBED an admission
refusal into a smaller compared store, and nothing counted how many. An over-reject there
made the gate test less and stay green: pre-fix, S1/S2/S4 left the remove gate green, and a
broad over-reject left the generated gate green on 38 of 40 seeds. All three now carry exact
pins. **`tests/` was not censused.** Do the same census there: classify every refusal catch
as (i) an expected-refusal test, (ii) a parity driver that asserts both backends refuse the
same write (safe), or (iii) an absorber that shrinks what is compared without counting. Pin
every (iii) exactly, the way `formal/conformance/test_conformance_remove.py::_assert_poisoned`
does.

## Read first

- [`docs/tk71-admission-survival-2026-09-27.md`](../docs/tk71-admission-survival-2026-09-27.md)
  sections 2-4: the census shape, the measurement and the sabotage table to copy.
- `tests/test_hypothesis.py` and 16 more files: the starting surface (MEASURED 2026-09-27, `grep -rc "except AdmissionRejected\|except
  ValueError\|except (ValueError" --include=*.py tests`): 17 files. Largest:
  `tests/test_hypothesis.py` 6, `tests/test_admission_rejected.py` 5, `tests/test_matrix.py` 4,
  `tests/test_wildcard_property.py` 3, `tests/test_setengine_storage.py` 3, `tests/parity.py` 2.

## Traps

- (!) A bare `except ValueError` also swallows a non-refusal engine bug (S4 in the map doc).
  Narrow it to `AdmissionRejected` before pinning the count, or the count includes bugs.
- (!) The measure must re-use each module's OWN generators (seeded), or it measures a
  different op stream from the one the gate drives.
- (!) Sabotage each pin with a PRE-FIX contrast (the `HEAD` copy of the module as a temporary
  probe): a pin whose pre-fix module also goes red was not the gap.

## Log

### 2026-10-03c

Triage 2026-10-03c: skeptic verdict WEAKENED, near-refuted (AGENT-REPORTED). The `TK71` premise does not carry over: the `tests/` parity drivers require all backends to accept or reject alike, and three sabotages (`TK71`'s S1, a shared wildcard-userset over-reject, a shared same-type-userset over-reject) all went RED. Keep at LATER as hygiene: narrowing bare `except ValueError` to `AdmissionRejected` in the absorbers still stops them swallowing non-refusal engine bugs. Site list and reasoning: `docs/promote-next-triage-2026-10-03.md` sec 4.

### 2026-10-13

Closed 2026-10-13 (lane L6). RE-SCOPED and DONE. Scope delivered: the hygiene half, plus the one genuinely lopsided absorber. The full exact-pin census was not built. It was near-refuted on 2026-10-03c: the parity drivers already require backends to accept and reject alike, and exact pins are not buyable at @given sites because the draws are unstable. That is the model's call under CLAUDE.md 'Who decides'.

(1) NARROWED `except ValueError` to `except AdmissionRejected`: 28 sites in 15 files. Census READ 2026-10-13 with `grep -rn 'except AdmissionRejected|except ValueError|except (ValueError' tests`; line numbers are pre-edit, dated 2026-10-13. Sites: tests/parity.py::_GraphSide.apply and ::_SetSide.apply (:85, :117); tests/test_matrix.py GraphBackend/SetBackend/ConnectedBackend.apply (:85, :113, :160) and the set-engine-first loop (:544); test_bulk_build.py::_seed_source (:525); test_connectedstore.py (:72); test_connectedstore_concurrency.py::_write_retry (:83); test_connectedstore_multi_instance.py::_write_retry (:444); test_hypothesis.py (:485, :977, :985, :1009, :1041, :1099); test_lookup_hypothesis.py (:193); test_reads.py::_walk_and_compare (:499); test_setengine_check.py (:48); test_setengine_eval.py (:61, :102); test_setengine_storage.py (:69, :100, :110); test_tk126_ttu_target_name_collision.py (:409); test_wildcard_property.py (:146, :528); test_zt_p5_readjudication.py (:654). The docstrings in parity.py and the two _write_retry helpers were updated, as was the anti-vacuity comment in test_wildcard_property.py. Narrowing loses nothing: READ src/zanzibar/schema/errors.py, where AdmissionRejected subclasses ValueError and PathCountExceeded/ClosureFanoutExceeded subclass it via IndexResourceLimit. Every admission raise in setengine/engine.py::_validate, schema/rules.py::RuleSet.apply and graphindex/{core,wildcard}.py is already typed.

(2) LEFT bare, by decision: 10 sites in 6 files. test_admission_rejected.py :90, :106, :141 test the subclass contract itself. test_p23_parser_refusal_parity.py:166 catches a schema PARSE refusal, not an admission refusal. test_reg15_security_hardening.py:193 is an expected-refusal subprocess probe (class i). test_reg16_processor_writes_thread_scope.py :65, :159 catch I5 exclusivity, which is deliberately plain ValueError (wildcard.py::_assert_derived_exclusivity). test_tk113_remove_node_fence.py:182 deliberately handles AdmissionRejected OR the I5 ValueError. test_tk95_truncated_fanout_rollback.py:186 records the raise point and RE-RAISES, so it is not an absorber.

(3) tests/test_reads.py::_walk_and_compare was class (iii): the graph alone decided admission and refused ops were never offered to the set engines. It is now class (ii): on a graph refusal both set engines must raise AdmissionRejected (pytest.raises), and the op is recorded. It also has an ANTI-VACUITY floor `len(history) >= steps - 1`. MEASURED 2026-10-13, first-hand (Random(seed) is deterministic): boolean_wildcards seeds 0/1/2 accepted 13/14, 14/14, 14/14; every demorgans fixture x seeds 0/1 accepted 10/10. The worst case sits on the floor.

SABOTAGE, first-hand 2026-10-13, using a monkeypatch plugin with no src edit and `-k boolean_wildcards`. POST-FIX: graph-only over-reject of `editor` gave 3 failed (DID NOT RAISE AdmissionRejected); shared Filter.apply returning False gave 3 failed (only 0/14 ops accepted); shared over-reject of `editor` gave 2 failed, 1 passed (10/14, 9/14). PRE-FIX HEAD copy: 3 passed under every sabotage, so the gap was real. S4 (a plain non-refusal ValueError from SetEngine.add_tuple on `viewer`), run on test_setengine_check.py: post 10 failed, HEAD copy 10 passed. The literal results are recorded in the _walk_and_compare docstring.

Runs: all 15 touched files green on 2026-10-13 (test_hypothesis 32 passed, test_matrix 17, test_reads 27, test_wildcard_property 9, the rest as listed in the lane return). No test added or removed. Nothing RED. Next action: none, beyond the serial gate run.
