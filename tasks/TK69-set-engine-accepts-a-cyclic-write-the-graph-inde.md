---
id: TK69
title: set engine ACCEPTS a cyclic write the graph index REFUSES -- backends fork on which stores may exist
brief: CONFIRMED 2026-09-15d: admission-contract divergence, NOT a ghost grant; each backend matches the oracle on its store
pri: NOW
size: M
deps: []
related: [P22, P23]
parent:
labels: [infra]
source: hand
source_hash:
created: 2026-09-15d
moved: 2026-09-15d
updated: 2026-09-15d
closed:
---

The two backends disagree about **which stores may exist**. A write that closes a userset
cycle is REFUSED by the graph index and ACCEPTED by both `SetOps` set-engine backends, so
from the same write sequence the two hold different data and answer differently. It is not
a ghost grant -- each backend matches the independent oracle on the store it holds -- but it
is the project's primary goal (`CLAUDE.md` sec "Who decides": the graph index must give the
same answers as the set engine) breaking at the ADMISSION layer instead of the evaluation
layer. Confirmed first-hand 2026-09-15d; nothing in the suite catches it.

## Traps

- (!) **Do not size or prioritise this off the audit's severity claim.** The "corruption-class
  error / permanently wedged multi-instance cursor" framing is AGENT-READ for the `ValueError`
  -> `InvariantViolation` promotion in `connectedstore/apply.py::_apply_row` and REASONED for
  the wedge. NEITHER is verified. Measuring it is step one, and the answer changes whether this
  is urgent or a contract wart.
- (!) **Do not "fix" it by making the graph accept the cycle.** `index_v4` materialises a
  transitive closure; `Inv.acyclic` / I2 is load-bearing, and an admitted cycle breaks it. Only
  the set-engine side is movable.
- (!) **A fix here is an admission OVER-REJECT risk, and the gate cannot see one.** Audit item
  4d: `formal/conformance/test_conformance_enum.py` carries no non-vacuity floor on
  surviving-store counts, so narrowing `_would_cycle` too far silently shrinks the enumerated
  store space with the whole suite staying green. **Add the floor as part of the fix, not
  after** -- and sabotage it (`docs/sabotage-procedure.md`) before believing it.
- (!) The probe drives `tests/test_matrix.py::GraphBackend` / `::SetBackend` deliberately, so
  accept/reject semantics are the GATE's and not the probe's. Keep it that way if it becomes a
  permanent test; a hand-rolled admission wrapper would prove something weaker.

## Read first

- **READ [`docs/adversarial-audit-2026-09-15.md`](../docs/adversarial-audit-2026-09-15.md)
  sec 1 FIRST** -- the finding, the mechanism, and the reconciliation that corrected the
  audit's characterisation of it. Sec "What the reconciliation changed" is why the other
  items on that page carry provenance labels.
- **The evidence:**
  [`formal/probes/i14_admission_divergence_2026-09-15.py`](../formal/probes/i14_admission_divergence_2026-09-15.py)
  -- rc=0, literal transcript in its header, re-runnable with
  `PYTHONPATH=. <env-python> formal/probes/i14_admission_divergence_2026-09-15.py`.
  Its part (C) is the oracle adjudication; that is the part the audit did not do.
- **The mechanism, both sides:** `setengine/engine.py::SetEngine._would_cycle` ->
  `::_flow_reaches` -> `::_shape_node_ref` (flow nodes per incident EDGE) against
  `index_v4/wildcard.py::WildcardIndex._ensure_entity_middles` (middles per ENTITY).
- **Related, and read before deciding the contract:** `P23` (the other admission-layer
  asymmetry between the two parsers -- same shape, already filed with a decided fix) and
  `docs/spec-deviations.md`, which is where an admission-contract decision is ledgered.

## Log

### 2026-09-15d

FILED FROM THE 2026-09-15 ADVERSARIAL AUDIT, AND CONFIRMED FIRST-HAND THE SAME SESSION. Read `docs/adversarial-audit-2026-09-15.md` sec 1 FIRST. Tracked probe with the literal transcript in its header: `formal/probes/i14_admission_divergence_2026-09-15.py` (rc=0).

**THE DIVERGENCE.** Four adds; the graph index REFUSES the fourth, both `SetOps` backends ACCEPT it:

    DIVERGES: add ('viewer','doc','d1','member','group','g')
              -> graph=False set:py=True set:roaring=True

Write 4 closes a userset cycle -- `doc:d1#viewer` -> `group:g#member` -> `folder:*#viewer` -> (wildcard parent + `viewer from parent`) -> `doc:d1#viewer`.

**THE MECHANISM** (AGENT-READ, symbols grepped, behaviour reproduced): the set engine's cycle check walks a flow graph whose nodes are created per incident EDGE (`setengine/engine.py::SetEngine._shape_node_ref`, from `::_flow_reaches` / `::_would_cycle`), while the graph's entity middles exist per ENTITY (`index_v4/wildcard.py::WildcardIndex._ensure_entity_middles`). Entity existence strictly contains flow-node existence, so the crossing is invisible to the set engine.

**(!) WHAT IT IS, AND WHAT THE AUDIT GOT WRONG.** The audit reported a corruption-class error. The probe's part (C) brings in the INDEPENDENT ORACLE and reframes it: the oracle evaluates the 4-tuple store fine, and EVERY backend matches the oracle ON THE STORE IT HOLDS -- 0 of 12 grid queries has a backend disagreeing with its own spec reading. So this is NOT a ghost grant and NOT a wrong answer. It is an ADMISSION-CONTRACT divergence: the two backends disagree about which stores may EXIST, then hold different data (3 tuples vs 4) and fork on 4 of 12 queries. Given identical write sequences two deployments diverge permanently -- equivalence breaking at the ADMISSION layer, not the evaluation layer.

**(!) THE SEVERITY IS UNMEASURED AND IS THE FIRST ACTION.** The audit's "wedged multi-instance cursor" clause runs through a `ValueError` -> `InvariantViolation` promotion in `connectedstore/apply.py::_apply_row`; that is AGENT-READ for the promotion and REASONED for the wedge, and NEITHER is verified. Nothing else on this row depends on it. Measure what the composed `ConnectedStore` does with the refusal BEFORE sizing the fix: if the log row commits and apply then fails repeatedly, this is serious; if the write is cleanly rejected end to end, it is a contract wart with an answer fork behind it.

**THE CONTRACT DECISION** (mine to make per `CLAUDE.md` sec "Who decides", NOT yet made): the spec defines a meaning for the cyclic store (least fixpoint -- the cycle is unfed, so it grants nothing), so the graph is the more restrictive side. But the graph's restriction is structural: it materialises a transitive closure and `Inv.acyclic`/I2 is load-bearing, so widening the graph is not on the table. LEANING (REASONED, not decided): narrow `setengine/engine.py::SetEngine._would_cycle` to see entity middles, which preserves both backends' existing guarantees. Decide it after the severity measurement, and record the reasoning here.

**NOTHING IN THE SUITE CATCHES THIS.** The reproduction is ready-made as a permanent test -- `tests/test_matrix.py`'s own `GraphBackend`/`SetBackend` adapters are what the probe drives, so accept/reject semantics are the gate's. (!) Note the coupling to audit item 4d: `formal/conformance/test_conformance_enum.py` carries no non-vacuity floor on surviving-store counts, so an admission OVER-REJECT -- i.e. a bad fix to THIS row -- would silently shrink the enumerated space with the suite staying green. Add the floor as part of the fix, not after.

-> NEXT, single action: measure the severity through `ConnectedStore` (sync and multi-instance async), then decide the contract.
