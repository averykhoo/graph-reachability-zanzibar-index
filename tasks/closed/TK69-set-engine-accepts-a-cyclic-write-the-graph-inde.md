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
moved: 2026-09-16b
updated: 2026-09-16b
closed: 2026-09-16b
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

### 2026-09-16b

CLOSED on its audited case (family F1), FIXED, PINNED, LEDGERED. (!) READ THE NEXT PARAGRAPH BEFORE TREATING ADMISSION PARITY AS RESTORED -- IT IS NOT. A second family (`TK70`, NOW) is still open, and it was found by fixing this one.

**SEVERITY: MEASURED, AND WORSE THAN THIS ROW RECORDED.** The row said the wedge was AGENT-READ/REASONED and unverified. Both halves now verified first-hand. (a) The promotion EXISTS: `connectedstore/apply.py::_apply_row` wraps the fan-out in `except ValueError -> raise InvariantViolation(... corruption or a validity-parity bug ...)`, with only `ClosureFanoutExceeded` carved out. (b) The exception is NOT a bare `ValueError` -- it is `AdmissionRejected`, which SUBCLASSES `ValueError` deliberately ("load-bearing", and its docstring names this very promotion as a caller). So the promotion fires. (c) The refusal cannot be caught at admission because admission in the composed system is the SET ENGINE ALONE (`connectedstore/source.py::TupleSource.add` validates via `_engine._add_tuple_direct`), so the row reaches the permanent log and detonates inside apply. (d) THE WEDGE IS REAL AND DURABLE: reopening the store re-reads the same lag and `catch_up` fails identically. (e) (!) WORSE THAN REPORTED -- with the default `batch=None` the batch is atomic, so the cursor never advances past 0 AT ALL: rows 1-3 (valid, unrelated) are never materialised and an untokened read of a legitimate grant returns `False` forever. `batch=1` strands only row 4.

**THE FIX (F1).** `setengine/engine.py::SetEngine._flow_reaches` now steps `w_all(T,p) -> w_any(T,p)` on a CROSSABLE shape when an entity of type T exists -- the I14 crossing middle added VIRTUALLY, in the same style as the bridges around it. Existence is `::_any_entity_of_type`, the existential twin of `::_instances_of_type`, deliberately stated off the same set (any predicate, name not the star sentinel); `interner.ids_of_type` would NOT do, it holds only `pred == '...'` concretes and would miss an entity mentioned solely as a userset. (!) THE ENTITY GATE IS THE RULE, NOT AN OPTIMISATION: with no entity of type T the graph mints no middle and accepts the same write, so an ungated hop over-rejects -- see sabotage S2.

**THIS WAS NOT A DESIGN CALL.** `docs/specs/set-engine-spec.md` sec 1 item 5 already decided it, under a decisions-made heading: "Reject them here too, with equivalent errors, so the 4-way matrix compares identical stores ... A parity test asserts both backends accept/reject the same op sequences", with the mechanic prescribed in sec 6.2. TK69 was an UNIMPLEMENTED SPEC CLAUSE. Direction confirmed independently: the graph's acyclicity is structural (it stores the closure as ref-counted path multiplicities; a cycle has no fixpoint), so only the set-engine side was movable.

**ASSURANCE.** Instrument: [`formal/probes/tk69_admission_parity_2026-09-16.py`](../formal/probes/tk69_admission_parity_2026-09-16.py) (tracked, pre/post, cases F1 / F2 / CTRL). Pin: `tests/test_reg_tk69_entity_crossing.py`. Sabotages, literal: S1 remove the hop -> F1 red, CTRL green; S2 keep the hop but drop the entity gate -> CTRL red AND the F2 pin red (the latter fires on its third assertion, which exists to catch the detonation being propagated instead of removed). The narrower CTRL arm stays green under S2, so the reds attribute to the gate and not to a broken traversal. Full suite green; blast radius measured -- ZERO conformance schemas have a non-empty `crossable_shapes` (all censused, including `object_wildcard`, which declares an object wildcard but is not bridged in), so that leg is inert.

**(!) THIS ROW'S OWN COUPLING INSTRUCTION IS REFUTED, FIRST-HAND.** The row required the fix to land audit item 4d's non-vacuity floor on `formal/conformance/test_conformance_enum.py`, "so an admission OVER-REJECT stays green" otherwise. The gap is real (no surviving-store floor exists there) but the coupling is wrong: `::_tuple_space` emits `"*"` only as a SUBJECT name and draws every object name from `_POOL`, so it CANNOT enumerate an object-wildcard write and therefore cannot reach a TK69-class store however the fix goes. A floor there would have been advertised against a case it cannot see -- this repo's house failure mode. The over-reject guard that actually bites is the CTRL pin, a direct witness. Item 4d remains a genuine non-vacuity gap and deserves its own row; it is NOT this row's gate.

**WHAT IS STILL BROKEN -> `TK70`, NOW.** The same four writes in order B,C,D,A: the graph ACCEPTS the cycle-closing write (no folder entity yet) and then REFUSES the ordinary grant `user:u1 editor folder:f1` -- naming no wildcard, no userset, not the crossable relation -- and wedges the cursor identically. (!) ITS FIX IS THE OPPOSITE DIRECTION: `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge` was written to prevent exactly this and calls it "the detonation: the graph locks itself out of a grant the set engine and the oracle both allow". F2 is a hole in that early rejection, so it is fixed GRAPH-side by refusing the latent write -- never by teaching the set engine to detonate too, which would trade an admission divergence for an ORACLE divergence.

Map: [`docs/tk69-admission-parity-2026-09-16.md`](../docs/tk69-admission-parity-2026-09-16.md). Ledger: [`docs/spec-deviations.md`](../docs/spec-deviations.md) 2026-09-16.
