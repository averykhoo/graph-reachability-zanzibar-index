# `TK70` — the detonation: the latent `w_any --> w_all` cycle, measured and closed

**ACTIVE-PLAN, opened 2026-09-17 — the body is provenance, not a living status.** Live
state is `python scripts/task.py show TK70` and `python scripts/gate_status.py`, never this
file. Corrections append **dated at the top**. Freeze it when `TK70` closes.

Companion to [`docs/tk69-admission-parity-2026-09-16.md`](tk69-admission-parity-2026-09-16.md),
which is the map for family F1 and states the F1/F2 split. This file is F2 only.

Provenance is labelled per claim. Everything below is FIRST-HAND (PROBED or READ) in the
2026-09-17 session unless it says otherwise; no subagent was used.

## 1. The mechanism, dumped

FIRST-HAND (PROBED). Schema is the reg11 / `owc_star_ttu` class; its one crossable shape is
`('folder','viewer')` — bridged **in** by the `[group#member]` userset restriction and
**out** by the declared object wildcard. Writes:

    A  ('...','user','u1','editor','folder','f1')      ordinary grant; mints folder:f1
    B  ('member','group','g','viewer','folder','*')    object-wildcard userset grant
    C  ('...','folder','*','parent','doc','d1')        bare-star tupleset parent
    D  ('viewer','doc','d1','member','group','g')      closes the userset cycle

After `B, C, D` the store holds exactly these three grant edges (node ids from the run):

    folder:*#viewer@any(i)  ->  doc:d1#viewer(i)      [C, via the TTU rewrite]
    doc:d1#viewer(i)        ->  group:g#member(i)     [D]
    group:g#member(i)       ->  folder:*#viewer@all(i) [B]

i.e. a **path `w_any(folder,viewer) --> w_all(folder,viewer)`** — the same shape's two
position-split rows joined by three hops. `WildcardIndex._reject_star_self_edge` refuses
exactly this configuration when it arrives as ONE routed edge; at length 3 nothing looks at
it.

Then `A` resolves `folder:f1#editor`, and `_ensure_bridges(obj)` →
`_ensure_entity_middles('folder','f1')` mints the I14 crossing middle `folder:f1#viewer`
with both bridges. The in-bridge lands first; the out-bridge detonates, literally:

    index_v4/wildcard.py:279  self.idx.add_edge_by_id(w_all.id, node.id)
    AdmissionRejected: subject_id=2 is reachable from object_id=9,
                       adding this edge would create a cycle

So the refusal is not about `A` at all. `A` is the write that happens to mint an entity of
type `folder`, and the cycle it closes was admitted three writes earlier.

## 2. The rule, and why it is the same rule the repo already states

REASONED, off a FIRST-HAND read of `index_v4/wildcard.py::WildcardIndex._reject_star_self_edge`
(`:185`, docstring `:186-222`, 2026-09-17).

That docstring's own argument is schematic, not data-dependent: the bridges of a crossable
shape are *"SCHEMATIC, not data: every present **and future** concrete `T:x#p` gets
`T:x#p -> w_any(T,p)` and `w_all(T,p) -> T:x#p`"*, so *"admitting the edge while the shape
happens to have no concretes yet therefore does not avoid the cycle — it defers it onto the
next innocent write"*. Nothing in that argument depends on the offending edge being a
single hop. The rule it justifies is:

> **L.** On a crossable shape `(T,p)`, a path `w_any(T,p) --> w_all(T,p)` is a cycle by
> construction. No write may create one.

`_reject_star_self_edge` is the length-1 case of L. F2 is the length-n case, and the hole is
exactly that generalisation. Fixing it is not a new design decision; it is finishing the one
already written down on 2026-07-26.

**The set engine already agrees in one place and disagrees in another** (FIRST-HAND, READ,
`setengine/engine.py::SetEngine._flow_reaches`, `:839`). Its `w_all` branch carries two
`w_all -> w_any` hops:

| hop | shape class | gate | added |
|---|---|---|---|
| ghost hop, `:906` | `doubly_bridged` | **none** — *"THROUGH any present-or-future concrete node of that shape"* | 2026-07-17 |
| I14 crossing hop, `:923` | `crossable` | `_any_entity_of_type(t)` | 2026-09-16 (`TK69`) |

The ghost hop is the schematic form of rule L and is ungated. The `TK69` hop is the same hop
for a different shape class, gated on present data. **The gate is what makes F2 possible on
the set side**, and it was added with a comment saying it "must not be dropped" — because at
the time the graph did detonate, so the ungated form would have over-rejected *relative to
the graph*. Fixing the graph removes that reason.

## 3. Baseline, measured before any edit

FIRST-HAND (PROBED), `formal/probes/tk70_latent_cycle_sweep_2026-09-17.py`, 2026-09-17,
rc=1. All 720 orderings of six writes (the four above plus
`E = ('...','user','u2','viewer','folder','f1')` and
`F = ('...','folder','f1','parent','doc','d1')`), on the graph index and both `SetOps`
backends:

    SWEEP: 720 orderings, 4320 write decisions, 80 divergence(s),
           824 unanimous refusal(s), 156 latent-cycle state(s)
      divergence on A  in 40 ordering(s)
      divergence on E  in 40 ordering(s)
      latent state after on A(40) B(12) C(16) D(12) E(40) F(36)
      unanimous refusals: B(288) C(104) D(288) F(144)
    OVERREJECT: 120 orderings, 600 write decisions, 0 / 0 / 0
    NARROW:       2 orderings,   4 write decisions, 0 / 0 / 0

Readings:

* the detonation is **not** confined to the one ordering `TK69`'s probe names. 80 of 4320
  write decisions diverge, spread over 80 distinct orderings, and it detonates on **`E` as
  well as `A`** — `E` is an ordinary `user:u2 viewer folder:f1` grant.
* **OVERREJECT and NARROW are clean pre-fix**, which is what makes them usable as controls.
  A fix that reddens either has over-rejected on a legal, oracle-pinned class.
* 156 store states hold the latent path. That is the population the fix must drive to 0.

## 4. (!) The acceptance property is a store invariant — the first draft got this wrong

FIRST-HAND, and worth carrying: the probe's first draft stated the property per-write —
*"an INNOCENT write (no `*` endpoint, bare `'...'` subject predicate, non-crossable object
relation) is never refused"*. Its pre-fix run reported **144 orderings refusing `F`
unanimously**, which reads exactly like a second, larger detonation family.

It is not one. `F = folder:f1 parent doc:d1` is innocent only in its RAW form; the TTU
rewrite routes it to `folder:f1#viewer -> doc:d1#viewer`, whose **subject is a concrete of
the crossable shape**. With `D` present it genuinely closes the loop, and both backends
correctly refuse it. **A syntactic innocence test cannot see a routed edge**, so it
manufactures a finding out of a correct refusal.

What actually separates the defect from a correct refusal is *when* the refusal happens, and
that is invariant L restated over the store: **after every accepted write, no crossable
shape has a `w_any --> w_all` path.** The probe measures it with an **independent
instrument** — `::latent_paths` walks the stored DIRECT edge rows breadth-first, and
deliberately does *not* call `ReachabilityIndex.check_reachable_by_id`, which is what the
fix itself queries. Sharing that query would have made probe and fix agree by construction.

The instrument's own discrimination control is built in and passes: SWEEP reports 156 latent
states, OVERREJECT (the same corpus minus the cycle-closing write) reports 0. An instrument
that reported latency everywhere, or nowhere, could not do that.

## 5. The fix

**Graph side**, `index_v4/wildcard.py`: `_reject_latent_star_cycle(subject, obj)`, called
from `_add_tuple_trusted` immediately after `_reject_star_self_edge` and **before**
`_ensure_bridges`, so a refused write never mutates closure state. For each crossable shape
whose `w_any` and `w_all` rows both exist, refuse when `w_any` reaches (or is) `subject`
**and** `obj` reaches (or is) `w_all`.

Checking only the grant edge is sufficient, and the reason is inductive: the only other
edges a write adds are bridges, and neither bridge direction can create a `w_any --> w_all`
path without one already existing. A new in-bridge `c -> w_any` can only extend a path that
already passes through `w_any`; a new out-bridge `w_all -> c` leaves `w_all`, so any
`w_any --> w_all` path through it must already have reached `w_all`. Both cases presuppose
the invariant already broken.

**Set engine side**, `setengine/engine.py::_flow_reaches`: drop the `_any_entity_of_type`
gate on the I14 crossing hop, making it schematic like the ghost hop three lines above it.
Without this the two backends diverge on the *cycle-closing* write instead of on the
innocent one — the divergence would move, not close.

The set-engine half deletes `::_any_entity_of_type` with its last caller. It was added
2026-09-16 for this gate alone, and leaving a dead existential in place would read as a
live rule.

## 6. Post-fix measurement

FIRST-HAND (PROBED), 2026-09-17, same instruments, same session:

| instrument | pre-fix | post-fix |
|---|---|---|
| `formal/probes/tk69_admission_parity_2026-09-16.py` | rc=1, F2 diverges | **rc=0**, all three cases parity-clean |
| `formal/probes/tk70_latent_cycle_sweep_2026-09-17.py` SWEEP | 80 divergences, 156 latent states | **0 and 0** |
| …  OVERREJECT (the control) | 0 refusals | **0 refusals** |
| …  NARROW | clean | clean |
| `tests/test_reg_tk69_entity_crossing.py` | 4 tests, 2 red by design | **32 passed** |

The two numbers to read together are the refusal census and the OVERREJECT arm. Unanimous
refusals rise 824 → 840, which looks like a widened gate and is not: pre-fix, `A` and `E`
were refused by the graph in 40 orderings each *while both set backends accepted them*
(counted as divergences, not refusals), and post-fix they are refused in **zero**. The
growth is entirely in `B`/`C`/`D` — the three writes that form the path — because the
refusal now lands on whichever arrives last rather than being deferred. `F` *falls*
(144 → 120) for the same reason. OVERREJECT is 0 before and after, which is what says none
of this movement reached a write outside the cycle.

**Fuzz sweep** (FIRST-HAND, 2026-09-17, an algorithm change so the gate's ten phases are not
sufficient on their own). `tests/test_hypothesis.py` under `HYPOTHESIS_PROFILE=deep`, three
DISTINCT seeds passed with `--hypothesis-seed=N` — the env var `HYPOTHESIS_SEED` is a no-op
and a "sweep" written with it runs one seed three times:

| seed | result |
|---|---|
| `--hypothesis-seed=20260917` | `30 passed in 724.35s` |
| `--hypothesis-seed=4242` | `30 passed in 709.12s` |
| `--hypothesis-seed=991177` | `30 passed in 657.06s` |

Each verdict was read off the run's own log, not off a wrapper's exit status. (The command
that printed the table exited 1 — its trailing `grep -c` matched zero `FAILED` lines — which
is the standing footgun in miniature and is exactly why the logs are the authority.)

### 6a. The composed-system wedge, end to end

FIRST-HAND (PROBED), 2026-09-17, `ConnectedStore(sync=False)` on the same schema, writes in
the F2 order:

    B ACCEPTED -> token 1
    C ACCEPTED -> token 2
    D REFUSED  AdmissionRejected: tuple doc:d1#viewer member group:g would create a
               cycle in the userset membership topology
    A ACCEPTED -> token 3
    catch_up OK
    check(u1 editor f1) = True

Compare the pre-fix transcript in the `TK69` map: `A` was admitted into the permanent log,
`catch_up` then raised `InvariantViolation` on every call, `cursor=0 lag=4`, and an
untokened `check(u1 editor f1)` read `False` — the whole index frozen by an ordinary grant.
The refusal now happens at admission, on the write that actually forms the cycle, and
nothing reaches the log that the evaluator cannot apply.

**This also disposes of the `bulk_build` question the change raises.** `build_index`
bootstraps from the source store's `TupleLogV1`, and admission on that path is the set
engine alone. Since the set engine now refuses the latent write, no log can carry a
latent-cycle corpus, so the offline builder cannot construct a store the incremental path
would refuse. That is the second thing the set-engine half buys, beyond parity.

## 7. The pins, and the mutation sweep that certifies them

`tests/test_reg_tk69_entity_crossing.py` (32 tests, was 4). Two pins were flipped
deliberately, as the `TK69` module's own docstring instructed:

* `test_family2_detonation_is_still_open` → `test_family2_detonation_closed`. It asserted
  today's divergence positively (never an xfail) so that closing F2 would force this edit.
* `test_ctrl_no_entity_means_no_refusal` → `test_ctrl_cycle_free_corpus_fully_accepted`.
  Its `[B, C, D]` arm asserted that D is accepted when no `folder` entity exists — which
  is exactly the latent admission `TK70` removes. **That arm could not survive the fix,
  and replacing it with a weaker one would have retired the over-reject control.** It is
  instead restated over corpora that contain no cycle-forming write at all, which is what
  the arm was always *for*: five corpora, including `E` (an ordinary grant on the
  crossable relation itself) and two reorderings.

New: `test_no_latent_star_cycle_is_ever_admitted` (invariant L over all 24 orderings, with
the independent BFS instrument) and `test_ordinary_grant_accepted_in_every_ordering` (the
user-visible form: `A` is never the victim, in any of the 24).

The mutation sweep table is in the module docstring, where the next reader is already
looking. Its three non-obvious rows:

* **M4** — restore the set engine's entity gate — reddens the two *parity* arms and leaves
  `test_no_latent_star_cycle_is_ever_admitted` green, because the graph still refuses
  correctly. That is the signature of a divergence rather than a bug, and it is why this
  module asserts unanimity separately from the store invariant.
* **M5** — drop the `obj reaches w_all` half — is the only mutation that reddens the
  over-reject control. It still refuses `D`, so the F1/F2 arms alone cannot tell it from
  the correct rule.
* **M6** — widen `crossable` to `bridged_in_shapes` — is **INERT, for a stated reason**:
  on this schema the three shape sets are all `{('folder','viewer')}` (dumped first-hand),
  so the edit could not move anything the module observes. Per the 2026-09-13c rule, an
  `INERT` row is only readable with the argument for why the edit did not move the
  property; without one it is indistinguishable from an uncovered pin.

## 8. What this does NOT establish

* **That F1 and F2 are the only two families.** The `TK69` map records that claim as
  resting on a 720-ordering agent sweep that was never reproduced. This session's sweep is
  first-hand but over the same six writes and the one schema, so it does not widen that
  claim. Still UNVERIFIED.
* **Evaluation parity on the newly-refused stores.** This work touches admission only
  (`SetEngine._flow_reaches` is reached solely from `::_would_cycle`, grep-verified
  2026-09-17); the validation matrix and the hypothesis campaign are what pin evaluation,
  and they run in the gate.
* **Anything about non-crossable schemas.** `crossable_shapes` is empty for every
  `formal/conformance/` schema (measured 2026-09-16, `TK69` map § Blast radius), so both
  halves of this change are inert there by construction.
