# TK73 — the boolean cascade failed to quiesce on a REMOVE

**ACTIVE-PLAN** (`docs/README.md` §3). Opened 2026-09-17. Corrections append **dated at
the top**. FREEZE when `TK73` closes.

Provenance labels are per claim: **READ** (verified first-hand against the live tree by
the session that wrote the line), **REASONED**, **UNVERIFIED** (reported by a subagent or
a prior session and *not* re-checked here). A subagent report is evidence, not a finding.

---

## 1. Verdict

**The CHECK was wrong, not the cascade.** The answers the cascade produced on the witness
were already correct — the terminal quiescence assertion over-fired on membership-neutral
garbage-collection traffic.

Fix (landed 2026-09-17): `index_v4/processor.py::DeltaProcessor._run_cascade`'s terminal
`if leftover: raise` is replaced by a **bounded settle-and-assert** pass — reconcile each
leftover key once and raise iff that reconcile was *not* a fixpoint. The round budget
`rounds = len(self.compiled.strata)` is **deliberately unchanged**; §5 records why.

## 2. The bug

Three writes on a legal boolean schema with no object wildcards raised on the REMOVE
(**READ**, reproduced first-hand 2026-09-17, `rc=1`):

```
InvariantViolation: cascade failed to quiesce after 1 strata rounds;
                    leftover keys: [('folder', 'owner', 'x')]
```

```
type user
type folder
  relations
    define parent: [folder, folder:*]
    define viewer: [user] or admin from parent
    define owner: viewer but not editor

add    ('...', 'folder', '*', 'parent', 'folder', 'x')     <- STAR parent
add    ('...', 'folder', 'x', 'parent', 'folder', 'y')
remove ('...', 'folder', 'x', 'parent', 'folder', 'y')     <- RAISED
```

All five ingredients are required; the witness probe carries one control each
(`formal/probes/cascade_quiesce_remove_2026-09-16.py`).

## 3. Mechanism (READ — every symbol below was read first-hand)

1. `DeltaProcessor._run_cascade` snapshots its frontier at the **top** of each round
   (`rows = outbox_rows(...)`, then `frontier_start = max(r.id ...)`) and only afterwards
   runs that round's reconciles.
2. A reconcile's **step (5)** may collect a recorded-subject node —
   `DeltaProcessor._gc_subject_node`, gated on `residue_changed`. `_reconcile_subject`
   has its own call to the same function, so **the emitter is not a single call site**.
3. `_gc_subject_node` demotes the node (`_demote_released_node` — the load-bearing BL-1
   demote-before-strip order, documented in its own comment), which lets
   `WildcardIndex._maybe_remove_bridges`' guard `fresh.implicit and
   fresh.reference_count == degree` pass for the first time.
4. `WildcardIndex._strip_bridges` then removes the star in-bridge; the ref-counted
   closure contraction **emits outbox rows**.
5. One of those rows carries object predicate `owner.0`, a
   `LeafFamily(kind='closure', owner_relation='owner')`, so `_map_deltas_to_keys` maps it
   back to `('folder','owner','x')` — the **same stratum, a different object**.
6. Those rows are written *after* the frontier snapshot and inside the **last** budgeted
   round (`rounds == 1` here), so the post-loop check sees them and raises.

**The rows are honest.** (**READ**, my own outbox dump 2026-09-17 confirming the
synthesis agent's, which is why I do not carry it as UNVERIFIED): they are an exact
*balanced retraction* — `#13 REMOVED 9->3`, `#14 REMOVED 9->4`, `#15 REMOVED 9->5` mirror
`#7 ADDED 9->3`, `#5 ADDED 9->4`, `#6 ADDED 9->5`. An external
`index_v4/outbox.py::drain_deltas` replica **must** see them. They are merely
membership-**neutral**, because the surviving wildcard node still carries the direct edges
that supply `owner@x`'s residue `stars=[["folder","admin"]]`. That is why the cascade's
answer is right while its invalidation traffic is real — and why suppressing the emission
was rejected (§5b).

**The defect, stated once:** the check tested a *syntactic proxy* — "no outbox row above
the final frontier maps to a derived key" — for the *semantic* property it wants, "no
derived key is stale". Reconcile-time node GC makes the two come apart.

## 4. The fix

`_run_cascade`'s terminal assertion now:

1. computes `leftover` exactly as before;
2. reconciles each leftover key **once**, full-object (strictly stronger than
   subject-scoped: it recomputes `neg`/`upos` wholesale);
3. raises iff any of those reconciles reported **changed** — the I9 property (§8.2), i.e.
   *genuine staleness*;
4. records the pass on `DeltaProcessor._settle` (a new `SettlePass` NamedTuple) so a test
   can observe the verdict;
5. raises (rather than looping) if the fixpoint pass itself emits mapping deltas —
   unobserved in practice; an unbounded drain has no termination argument here, because
   the extra pass runs a full reconcile that can itself write and emit.

## 5. Rejected alternatives, and why (this is the decision-relevant section)

**(a) `rounds = len(strata) + 1`, or an unbounded drain loop — REJECTED.**
This is the cheapest fix and it makes the witness green, so the witness *cannot choose
between it and the shipped fix*. The sabotage can, and it is the whole argument
(**READ**, `.scratch/tk73-lead/sabotage_settle_vs_budget.py`, rc=0, 2026-09-17):

```
== unsabotaged: both arms must be GREEN (the witness cannot choose) ==
  A settle-and-assert   : green   settle=([('folder', 'owner', 'x')], [])
  B rounds+1            : green
== SABOTAGED (owner@x residue dropped immediately before the pass examines it) ==
  A settle-and-assert   : RAISED: cascade failed to quiesce after 1 strata rounds; the
                          settle pass CHANGED derived state at [('folder','owner','x')]
                          -- those keys were genuinely stale
  B rounds+1            : green
```

`rounds+1` **silently repairs** genuine staleness and reports success: an assurance step
that fails by passing, this repo's house failure mode. That is why the budget was left
alone. Note the shipped fix is *strictly stronger*, not merely different — it raises on a
case the budget bump absorbs.

**(b) Suppress the GC emission (a "no-emit window" around the strip) — REJECTED.**
The rows are a balanced retraction (§3). Suppressing them leaves an external
`drain_deltas` replica holding three unretracted ADDs for a node that no longer exists.
Worse, `index_v4/invariants.py::verify_outbox_deltas` is structurally blind to a *missing*
row (**UNVERIFIED** — reported by a verifier agent, not re-read by me; it strengthens an
argument I am not relying on, so I did not chase it).

**(c) Relax `_maybe_remove_bridges`' `implicit` conjunct — REJECTED**, for the reason
`_gc_subject_node`'s own comment gives (**READ**): "the strip guard is NOT the thing to
relax — `remove_node`'s 'explicit nodes keep bridges for as long as they exist' policy
depends on it". ⚠ A diagnosis agent excluded this citing
`tests/test_userset_bridge_release_leak.py`; its verifier showed that module stays **2/2
green** under the relax. Exclude (c) for the policy reason, **not** that test.

**(d) Revert BL-1's demote-before-strip — REJECTED**: turns
`tests/test_userset_bridge_release_leak.py` RED (**UNVERIFIED** — reported, not re-run; it
is a revert of a deliberate prior fix and was never a live candidate).

## 6. The pin, and why the obvious pins fail

`tests/test_cascade_quiesce_gc.py` (new, 3 tests, **READ** — `3 passed in 0.47s`,
2026-09-17). Two weaker pins were tried and rejected first:

- **The witness probe cannot be the acceptance signal.** All six of its controls assert
  "no failure", so simply *deleting* the quiescence check makes it `rc=0` exactly as a
  real fix does (**READ**).
- **"assert `reconcile(...) is False` and `audit_fixpoint()` passes" fails by passing.**
  `reconcile` is a *repairing mutator*: on genuinely stale state the first call repairs
  and every later call returns False. The assertion passes on corrupted state.

So the pin reads `DeltaProcessor._settle` — the pass's own verdict, recorded before any
repairing reconcile can launder it. `test_settle_pass_detects_genuine_staleness` makes
the choosing sabotage of §5a **permanent** (the durability ranking of
`docs/sabotage-procedure.md`).

**Mutation sweep over the module** (**READ**, `.scratch/tk73-lead/sweep_pin_module.py`,
rc=0, 2026-09-17) — a single sabotage certifies one test, so the module was swept:

| mutation | result |
| --- | --- |
| `M0` (control: flip a pin's own claim) | RED `test_settle_pass_runs_and_is_a_fixpoint` — **attribution works** |
| `M1` revert the fix | RED all three |
| `M2` settle assert has no teeth (`if False`) | RED `test_settle_pass_detects_genuine_staleness` |
| `M3` do not record `_settle` | RED `test_settle_pass_runs_and_is_a_fixpoint` |
| `M4` settle examines no keys | RED two |
| `M5` settle never reports changed | RED `test_settle_pass_detects_genuine_staleness` |
| `M6` reword the tail-raise message | INERT (expected — no pin asserts that text) |

⚠ **Two instrument failures happened during this work and are the reason the sweep
carries `M0` and the "settle pass RAN" assertion.** Both are the quiet kind:

1. The first sabotage fired one reconcile too early. **Both arms stayed green while every
   `fired` / `row_existed` control passed** — because `owner@x`'s residue is the reference
   that *defers* the GC, so dropping it early removed the sabotage's own precondition and
   no settle pass ever ran. A sabotage that disarms itself reads exactly like a clean pin.
   The fix was to assert the pass **ran**, not just that the sabotage fired.
2. The second attempt keyed on the *second* `reconcile` of the target and never fired:
   round 1 settles the raw delta through `reconcile_subject` (a different method), so the
   settle pass is the target's **first** full `reconcile`. The `seen` counter caught this
   only because it was asserted.

## 7. Still owed / open questions

- **Can a late GC delta ever leave a key GENUINELY stale on some other shape?**
  ~15,000 instrumented cascades across the diagnosis found no over-budget round that
  changed state (**UNVERIFIED** — I re-ran none of those sweeps; do not record it as
  established). The fix does **not** depend on the answer: settle-and-assert *raises* on
  such a case instead of absorbing it, which is precisely the argument for it over (5a).
- `_gc_subject_node`'s final act is `widx._sync_entity_middles(*entity)` (**READ**), and
  `_gc_public_node` carries the same call. `_sync_entity_middles` both strips **and
  re-adds** bridges, so on a schema with non-empty `crossable_shapes` it is a second late-
  emission site. No witness in hand; settle-and-assert covers it by construction, but it
  deserves a targeted hunt.
- **The quiescence check is narrower than it looks.** A verifier skipped a reconcile in a
  *productive* round and got 2 wrong answers against the oracle with **no raise from
  either candidate fix** (paranoia off) (**UNVERIFIED** — not reproduced by me). So this
  is a *drainage* check only; I9 `audit_fixpoint` is the correctness net, and it is not
  run per-write outside `tests/test_matrix.py::GraphBackend.post_op`. Worth its own row:
  should a cheap per-write staleness check exist at all?
- A **second independent witness** was reported (leftover `('folder','owner','z')` on a
  schema adding `editor: [user, user:*]`) (**UNVERIFIED** — not reproduced). If real, the
  pin should grow a second shape.
- `.scratch/` is shared across concurrent agents; one diagnosis agent reported a filename
  collision where another overwrote its probe between write and run. The lead's probes are
  isolated under `.scratch/tk73-lead/`. **Everything in `.scratch/` is gitignored** — the
  transcripts that matter are quoted in this file and in the pin module's docstring.
