# `TK69` / `TK70` — admission parity on the I14 crossing middle, measured

**FROZEN 2026-09-17 — read for METHOD, not for state.** `TK70` closed that day, which was
this file's stated freeze condition. Live state is the task rows
(`python scripts/task.py show TK70`) and `python scripts/gate_status.py`.

> **CORRECTION 2026-09-17 — two claims below were true on 2026-09-16 and are now WRONG.**
> Both concern the entity gate on `SetEngine::_flow_reaches`'s I14 crossing hop.
>
> 1. § The F1 fix says *"⚠ The entity gate is the rule, not an optimisation … With no
>    entity of type `T` the graph mints no middle and accepts the same write, so an
>    ungated hop over-rejects."* The premise was `TK70`: the graph was admitting a cycle
>    that was merely LATENT and detonating on a later innocent write. The graph now refuses
>    the latent write itself (`WildcardIndex::_reject_latent_star_cycle`), and the hop is
>    **schematic and ungated**, matching the doubly-bridged ghost hop beside it.
>    `_any_entity_of_type` was deleted with its last caller.
> 2. The sabotage table's **S2** (*"keep the hop, drop the entity gate → 2 failed"*) is no
>    longer a sabotage — it is the shipped behaviour. Its two reds were red against the
>    unfixed graph. The `TK69` pins were rewritten accordingly; the 2026-09-17 mutation
>    sweep in `tests/test_reg_tk69_entity_crossing.py`'s docstring is the current evidence.
>
> Everything else here stands, including the F1/F2 split and the reasoning for why the two
> families take opposite fixes — that call survived first contact. The `TK70` half of the
> story, measured, is [`docs/tk70-detonation-2026-09-17.md`](tk70-detonation-2026-09-17.md).

This is the measured map for the two admission-divergence families between the graph index
and the set engine, as of 2026-09-16.

**Provenance is labelled per claim and it is not uniform.** This session reproduced a
subset first-hand and inherited the rest from a six-strand subagent sweep run the same day.
A subagent report is evidence, not a finding (`CLAUDE.md` § Delegation), so anything
un-reproduced is marked AGENT and must be re-verified before it is acted on. Two of the
sweep's conclusions were **wrong or mis-framed** and are corrected in § What the
reconciliation changed — read that before trusting any AGENT row.

## The two families, in one instrument

`formal/probes/tk69_admission_parity_2026-09-16.py` (tracked, rc=1 pre-fix and post-fix)
drives `tests/test_matrix.py::GraphBackend` / `::SetBackend` so the accept/reject semantics
are the gate's. Four writes:

    A  ('...','user','u1','editor','folder','f1')      an ORDINARY grant; mints folder:f1
    B  ('member','group','g','viewer','folder','*')    object-wildcard userset grant
    C  ('...','folder','*','parent','doc','d1')        bare-star tupleset parent
    D  ('viewer','doc','d1','member','group','g')      closes the userset cycle

| case | order | pre-fix | post-fix |
|---|---|---|---|
| **F1** | A,B,C,D | graph refuses D, both set backends accept → **DIVERGES** | all three refuse D → ok |
| **F2** | B,C,D,A | graph accepts D, then refuses A → **DIVERGES** | unchanged → **still DIVERGES** (`TK70`) |
| **CTRL** | B,C,D (no A) | all three accept everything | unchanged — **no over-reject** |

All three rows: FIRST-HAND (PROBED). The literal transcripts are in the probe header and in
`tests/test_reg_tk69_entity_crossing.py`'s module docstring.

## F1 — the cause, and why only the set engine was movable

FIRST-HAND (READ). On a CROSSABLE shape `(T, p)` — bridged in **and** out — the graph mints
the crossing middle `(T, x, p)` with both bridges for every live ENTITY of type `T`
(`index_v4/wildcard.py::WildcardIndex._ensure_entity_middles`, invariant I14). That is not
incidental: `zanzibar_utils_v1.py::SchemaInfo.crossable_shapes`' own docstring fixes the
wildcard-materialization spec §3.4 existential as ENTITY-wise — *"so the concrete middle
must track ENTITY existence rather than node existence"*. The set engine's flow graph holds
a node only once an edge is incident on it (`setengine/engine.py::SetEngine._shape_node_ref`
— *"Added on the first incident edge"*), so `::_flow_reaches`'s w_all OUT-bridge branch
could step only to concretes some edge already touched. An entity mentioned by an unrelated
relation was invisible, and with it the whole crossing.

**The direction was already decided, in writing, and this is the single most
decision-relevant fact in the file** (FIRST-HAND, READ). `docs/specs/set-engine-spec.md` §1
item 5 — under a decisions-made heading — says: *"Write-validity parity with the graph
backend … Reject them here too, with equivalent errors, so the 4-way matrix compares
identical stores. Cycles among usersets: rejected at write via a DFS over the stored
membership topology (§6.2). A parity test asserts both backends accept/reject the same op
sequences."* `TK69` was an **unimplemented spec clause**, not an open design question.

AGENT, not reproduced: that the graph's refusal is structural because the closure is stored
as ref-counted path multiplicities and a cycle yields *"unbounded path counts, hence
permanent phantom reachability, hence a stale ALLOW"* (`index_v4/core.py`), so widening the
graph was never available. The conclusion is corroborated first-hand by I2's unconditional
assertion in the invariant checker, and nothing in this session contradicts it.

## Severity — the half the row had never verified

The `TK69` row carried its severity as AGENT-READ for the exception promotion and REASONED
for the wedge, and required measuring it as the first action. Measured:

| claim | verdict | provenance |
|---|---|---|
| `connectedstore/apply.py::_apply_row` promotes `ValueError` → `InvariantViolation` | EXISTS, only `ClosureFanoutExceeded` carved out | AGENT (READ) |
| the exception is not a bare `ValueError` but `AdmissionRejected`, which subclasses it deliberately | CONFIRMED — the promotion fires | AGENT (PROBED) |
| composed-system admission is the SET ENGINE alone, so the row reaches the permanent log | CONFIRMED | AGENT (READ+PROBED) |
| the async cursor wedges, and the wedge is DURABLE across reopening the store | **CONFIRMED FIRST-HAND** (for family F2's write; see below) | PROBED |
| with the default `batch=None` the cursor never advances past 0 at all | AGENT (PROBED) — the whole index stays empty, unrelated valid grants read `False` | AGENT |

The first-hand reproduction used family F2's ordering and is literal:

    add ('...','user','u1','editor','folder','f1') -> token 4
    catch_up #1 RAISED InvariantViolation: log row 4 (ADD) was rejected by the index --
      the log is admission-validated, so this is corruption or a validity-parity bug ...
       cursor=0 lag=4
    catch_up #2 RAISED ... cursor=0 lag=4
    check(u1 editor f1) untokened -> False

So the severity framing the row doubted is **real**, and on the default batch it is worse
than the row recorded: not a stranded row but a frozen index.

## The F1 fix, and what makes its green mean anything

`SetEngine._flow_reaches` now steps `w_all(T,p) -> w_any(T,p)` on a crossable shape when an
entity of type `T` exists — the middle added VIRTUALLY, in the same style as the bridges
around it, with no new stored state. Existence is `::_any_entity_of_type`, the existential
twin of `::_instances_of_type` and deliberately stated off the same set (any predicate, name
not the star sentinel). `interner.ids_of_type` would **not** do: it holds only
`pred == '...'` concretes, so an entity mentioned solely as a userset would be missed — on
exactly the shapes this is about.

⚠ **The entity gate is the rule, not an optimisation.** With no entity of type `T` the graph
mints no middle and accepts the same write, so an ungated hop over-rejects. That is what the
CTRL case exists to catch, and it is why F1's green is informative at all: a fix that bought
parity by refusing everything would pass F1 and fail CTRL.

**Sabotages** (FIRST-HAND, literal, `pytest tests/test_reg_tk69_entity_crossing.py -q`):

| # | sabotage | result |
|---|---|---|
| S1 | remove the crossing hop entirely | 1 failed, 3 passed — only `test_family1_*` |
| S2 | keep the hop, drop the entity gate | 2 failed, 2 passed — `test_ctrl_*[ops0]` **and** `test_family2_*` |

S2's second red is not noise and is worth carrying: an ungated hop makes the SET ENGINE
refuse the ordinary grant too, so the F2 pin fires on its third assertion — the one that
exists to catch the detonation being *propagated* rather than removed. The narrower CTRL arm
(`[B, C]`, no closing write) stays green under S2, which is what attributes both reds to the
gate rather than to a broken traversal.

**Blast radius** (FIRST-HAND, PROBED): **no** `formal/conformance/` schema has a non-empty
`crossable_shapes` — every shape censused, including `object_wildcard`, which declares an
object wildcard but is not bridged in — so that entire leg is inert to this change. The
whole `tests/` suite passes unchanged.

## F2 — `TK70`, and why it takes the OPPOSITE fix

The same four writes in order B,C,D,A leave the graph ACCEPTING the cycle-closing write (no
`folder` entity exists yet, so the cycle is latent) and then REFUSING the ordinary grant
`user:u1 editor folder:f1` — a write naming no wildcard, no userset, and not the crossable
relation. Minting that entity's I14 middle emits the bridge edge that closes the cycle.

⚠ **Do not fix this by narrowing the set engine**, which is the obvious move and the one the
F1 result invites. FIRST-HAND (READ):
`index_v4/wildcard.py::WildcardIndex._reject_star_self_edge` was written to prevent exactly
this outcome, and its docstring states the verdict already — admitting the edge while the
shape has no concretes yet *"does not avoid the cycle — it defers it onto the next innocent
write, which is then permanently rejected (the 'detonation': the graph locks itself out of a
grant the set engine and the oracle both allow)"*. Teaching the set engine to detonate too
would make **both** backends refuse a grant the ORACLE allows: that trades an admission
divergence for an oracle divergence, which under `CLAUDE.md` § "Who decides" is a strictly
worse trade. F2 is a **hole in that early rejection** — the same by-construction latent cycle
arriving through the entity middles instead of through a directly routed same-shape edge — so
it is fixed graph-side, by refusing the latent write. `TK70` carries the traps, including the
over-reject risk on a legal, oracle-pinned schema class.

## What the reconciliation changed — read before trusting an AGENT row

1. **The sweep recommended "one rule, two triggers": narrow the set engine for BOTH
   families.** All three of its independent decision lenses said so. That is **rejected**
   here, on a first-hand read of `_reject_star_self_edge`'s docstring, which the lenses had
   seen only as a quoted fragment. One lens did raise it as its own strongest objection —
   *"my recommendation propagates a behaviour the repo has already written down as a
   defect"* — and that objection is correct and decisive. Family 2's correct direction is
   the opposite of family 1's, which is why they are two rows and not one.
2. **The `TK69` row's coupling to audit item 4d is REFUTED** (FIRST-HAND). The row required
   the fix to land a non-vacuity floor on `formal/conformance/test_conformance_enum.py`,
   "so an admission OVER-REJECT stays green" otherwise. The gap is real — no surviving-store
   floor exists there — but `::_tuple_space` emits `"*"` only as a SUBJECT name and draws
   every object name from `_POOL`, so it cannot enumerate an object-wildcard write and
   therefore cannot reach a `TK69`-class store however the fix goes. A floor there would
   have been an assurance step advertised against a case it cannot see, which is this
   repo's house failure mode. It deserves its own row on its own merits; it was never this
   fix's gate. The guard that does bite is CTRL.
3. **The reported cause named the wrong exception type** — `ValueError` rather than
   `AdmissionRejected`. Harmless (it subclasses `ValueError`, deliberately), but it is the
   third time in two sessions that a confident-sounding type name in a hand-off did not
   survive a probe.

## Measurements NOT reproduced first-hand

Recorded here so they are not lost with the gitignored `.scratch/`, and flagged so nobody
cites them as settled. All AGENT, all from the 2026-09-16 sweep:

* an exhaustive **720-ordering** sweep of six writes straddling the crossing (4320 steps):
  44 steps fixed by the F1 patch, **0** over-rejecting, **80** still under-rejecting — the
  residual being family 2, attributed to writes `A` (×40) and `('...','user','u1','viewer',
  'folder','f1')` (×40);
* a 400-sequence × 10-step randomised add/remove differential fuzz: **0** steps where
  patched and unpatched set engines differed;
* 225 tests across 17 admission/wildcard/parity modules identical patched and unpatched.

The first of these is the only evidence for the *completeness* of the family split — i.e.
that F1 and F2 are the only two families. It has not been reproduced. Treat "there are
exactly two families" as UNVERIFIED; everything else in this file about F1 and F2
individually is first-hand.
