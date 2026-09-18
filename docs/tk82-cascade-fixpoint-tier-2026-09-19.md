# TK82 — the opt-in I9 tier over the cascade's SCHEDULED-key union

**FROZEN 2026-09-19 — provenance, not a living document.** Status lines below are
as-of-then and several may now be false; live state: the task tree
(`python scripts/task.py show TK82`) + `HANDOFF.md` + the session ledger. Corrections are
appended dated at the top, never edited into the body. Opened as an ACTIVE-PLAN and frozen
in the same session, because `TK82` closed in it.

Provenance labels are per claim: **READ** (verified first-hand against the live tree by
the session that wrote the line), **MEASURED** (this session ran it and the literal output
is quoted), **REASONED**, **UNVERIFIED**. Line numbers are dated; cite `file::symbol`.

The prior scouting is `docs/tk74-staleness-net-2026-09-18.md` §10.3 (FROZEN) and §9.9 —
this file does not restate it. What is here is the *design decision* this session had to
make, the traps found while making it, and the measurement of the **shipped** tier (which
§10.3 explicitly could not stand in for: its instrument wrapped the public `run_cascade`
and therefore ran outside the two cache scopes).

---

## 1. The decision: where the tier sits in the level ladder

`docs/tk74-staleness-net-2026-09-18.md` §8.8 says "a new opt-in paranoia tier beside
`off`/`residue`/`full` … default OFF". That under-specifies the one thing that decides the
blast radius: **the ladder is a TOTAL ORDER** — `index_v4/invariants.py::_LEVEL_RANK` is
built by enumerating `PARANOIA_LEVELS`, and `ParanoiaGuard.raise_to` keeps the *higher*
rank when a store is wired twice (**READ**, 2026-09-19). So a new name is not free: where
it lands in the tuple decides which existing callers get it.

| candidate placement | consequence |
| --- | --- |
| `off < residue < TIER < full` | `full` **implies** the tier. `install_paranoia` defaults to `full` and `make_wildcard_index` defaults to `paranoia=True` = `full`, so the whole suite would start paying a doubled cascade — i.e. **not opt-in**, which is the one property the item is specified around. |
| a name outside the order | breaks `raise_to`'s total order and `normalize_paranoia_level`'s "one of `PARANOIA_LEVELS`" contract; every rank comparison becomes a special case. |
| `off < residue < full < TIER` | **TAKEN.** Nothing selects it implicitly (no default, no `_BOOLISH` word maps to it), the ladder stays monotone in both cost and coverage, and `raise_to` keeps working unchanged. |

**DECIDED: `PARANOIA_FIXPOINT = 'fixpoint'`, ranked above `full`.** Monotonicity is real,
not nominal: `fixpoint` runs everything `full` runs *and* the per-cascade check. The cost
ordering is the same direction — `full` is O(store) per commit, the tier is O(cascade
work) *on top of* it.

**The price of that choice, stated:** an operator cannot buy the cascade tier *without*
`full`'s O(store) per-commit checker. That is deliberate and it is not a production
regret — §8.8 measured the tier at roughly **double** cascade cost against `residue`'s
~+5%, so it was never going to be a production setting; it is a diagnosis/debug tier, and
so is `full`.

### 1.1 ⚠ TRAP the placement creates, found and fixed in the same edit

**READ** (2026-09-19): `ParanoiaGuard.before_commit` and `::after_commit` branch on
`self.level == PARANOIA_FULL` / `!= PARANOIA_FULL` — **equality, not rank**. Appending a
rank ABOVE `full` therefore silently routes `'fixpoint'` into the *residue* branch and
drops post-commit re-checking entirely: the strongest tier would have been **weaker than
`full`**, a tier knob that lies in the same direction §9.7 caught `make_wildcard_index`
lying. Both comparisons are now rank-based (`_LEVEL_RANK[...] >= _LEVEL_RANK[PARANOIA_FULL]`).

Pinned by `tests/test_cascade_fixpoint_tier.py::test_fixpoint_tier_is_at_least_full`.

## 2. The decision: the tier runs OUTSIDE the two cache scopes

`DeltaProcessor.run_cascade` is a wrapper that opens `idx._node_cache_scope()` and
`_stored_cache_scope()` around `_run_cascade` (**READ**, 2026-09-19). §10.3 carries an
explicit instrument caveat: its arm wrapped the *public* `run_cascade`, so the measured
re-reconciles ran **outside** both scopes, and "a tier shipped INSIDE those scopes is not
what was measured".

**DECIDED: ship it outside**, in `run_cascade` after the `with` block closes. Three
reasons, in order of weight:

1. It is the **stronger question** — a memoised node resolution or stored-tuple
   enumeration cannot mask a divergence that the check exists to see.
2. It is **what was measured**, so §10.3's FP number transfers rather than needing a
   re-derivation with a different instrument. (It is re-measured on shipped code anyway,
   §4 — but the two are then comparable.)
3. One call site covers every normal exit of `_run_cascade`, which has three (`break` on
   an empty round, early `return` on empty leftover, fall-through) — a check placed
   *inside* would have to be repeated at each, and the next added exit would silently skip it.

⚠ **Known bound, not a defect:** under `connectedstore.advance_index` an OUTER
`_node_cache_scope` is installed around the whole apply loop, so there the tier's
re-reconciles still run inside *that* scope. The tier closes its own two scopes; it cannot
close a caller's.

## 3. The union comes from the SCHEDULING side, and that choice ships with a permanent test

This is the load-bearing constraint from §10.3, restated because the implementation is
shaped by it: on unmutated traffic the scheduled union and the dispatched set are
**byte-identical** (`union_minus_dispatched = 0` over 3,744 clean cascades, 2026-09-18c),
so **no benchmark and no clean-traffic test can tell the right design from the wrong one**.
The only instrument that distinguishes them is fault injection.

Implementation seam: `DeltaProcessor::_tier_schedule` is called at the two places a key is
*scheduled* — right after `_map_deltas_to_keys` + the bumped fan-out in each round, and
again on `leftover`. It is deliberately a named method rather than an inline `update()`
**so that the sabotage arm can re-source the union from the execution side by patching one
symbol**, which is exactly the refactor the design chooses against.

`tests/test_cascade_fixpoint_tier.py::test_sabotage_reconciled_union_ships_dead` is that
arm, permanent (`docs/sabotage-procedure.md` ranks a permanent test above a transcript).

---

## 4. Measurements of the SHIPPED tier (2026-09-19, MEASURED first-hand)

### 4.1 Detection, sabotage and the two controls — the whole result in one transcript

Fixture `tests/fga_schemas/demorgans_reverse.fga` (inlined into the test module, five
strata). One reconcile suppressed inside the cascade loop; the cascade driven directly
rather than through a commit, so the tier is the only detector in play.
`.scratch/tk82/probe3.py`:

```
== skip ('attr', 'does_not_label', 'a1')
    skipped=1 dispatched=[]
    union=[('attr','does_not_label','a1')]      changed=[('attr','does_not_label','a1')]
    RAISED
== skip ('cond', 'requirement_not_met', 'c1')
    skipped=1 dispatched=[('attr','does_not_label','a1')]
    union=[('attr','does_not_label','a1'), ('cond','requirement_not_met','c1')]
    changed=[('cond','requirement_not_met','c1')]
    RAISED
== skip ('cond', 'requirement_met', 'c1')                    changed=[that key]  RAISED
== skip ('role', 'access', 'r1')                             changed=[that key]  RAISED
== control: no skip
    skipped=0  union=5 keys (one per stratum)  changed=[]   NO RAISE
== SABOTAGE reconciled-union, skip requirement_not_met
    skipped=1  union=[('attr','does_not_label','a1')]  changed=[]   NO RAISE
== tier OFF (full), skip requirement_not_met
    union=None  changed=None   NO RAISE
```

Four of four skips caught; the reconciled-union variant blind on the same arm with a
**non-empty** union — it looks alive and is dead, exactly as TK74 §9.9 predicted. `'full'`
does not arm the tier.

⚠ **An instrument failure worth carrying, because it reads as a clean result.** The first
form of this probe (`.scratch/tk82/probe2.py`) left the suppression armed while the tier
ran, so the tier's OWN re-reconcile of the skipped key was suppressed and **all four skip
arms came back `NO RAISE`** — a detector that works, reported as a detector that does
nothing. The fix is one line (disarm on entry to `_check_cascade_fixpoint`) and it is now
in the shipped test harness. A second form wrapped only `reconcile` and not
`reconcile_subject`, which silently halves the injection: the in-loop dispatch takes the
subject-scoped path whenever the round scheduled subjects rather than a whole object.

### 4.2 The skip is a REAL defect, not an artifact of the monkeypatch

Same skip, tier OFF, committed, then compared against the independent oracle over a
49-query grid (`.scratch/tk82/probe4.py`, 2026-09-19):

```
skipped = 1
grid = 49 divergences = 4
    ('...','doc','d1','requirement_not_met','cond','c1')  graph=True  oracle=False
    ('...','doc','d1','requirement_met','cond','c1')      graph=False oracle=True
    ('...','doc','d1','access','role','r1')               graph=False oracle=True
    ('...','doc','d1','access','user','u1')               graph=False oracle=True
```

The divergence reaches the TOP stratum, and one of the four is permissive in the wrong
direction (`requirement_not_met` answers `True` where the oracle says `False`). Pinned by
`::test_the_suppressed_reconcile_makes_the_store_oracle_wrong`.

### 4.3 False positives on real traffic, with the tier as SHIPPED

`.scratch/tk82/fp_plugin.py` upgrades every store the suite wires at `'full'` to
`'fixpoint'`, so the existing suite becomes the FP sweep — broader and less synthetic than
§10.3's generated workload, and it runs the tier from inside its real call site rather
than from a wrapper. It counts cascades and re-reconciled keys so a plugin that silently
stopped upgrading cannot read as a clean result.

Boolean-heavy modules (`test_matrix`, `test_processor`, `test_invariants_derived`,
`test_parity_engine`, `test_cascade_quiesce_gc`), 2026-09-19:

```
TK82 FP SWEEP: upgraded=76 tier_cascades=326 keys_rereconciled=490 tier_raises=0
61 passed in 59.70s
```

The whole-suite figure is in §4.5.

### 4.4 The mutation sweep of the new test module

Mandatory per `docs/sabotage-procedure.md` §"Sweep the TEST MODULE with mutations": a
sabotage certifies one test, not a module. `.scratch/tk82/sweep.py`, 2026-09-19, **13
mutations, 12 RED, 1 INERT**, with the `M0` control attributing correctly:

| mutation | verdict | what it weakens |
| --- | --- | --- |
| `M0-control` | **RED(3)** | harness control: flip the clean-traffic pin's own expected cascade |
| `M1-no-loop-schedule` | **RED(5)** | union loses the per-round scheduled keys |
| `M2-no-leftover-schedule` | **RED(1)** | union loses the terminal leftover keys |
| `M3-full-implies-tier` | **RED(2)** | the tier stops being opt-in: `full` arms it too |
| `M4-equality-branch` | **RED(1)** | the old `== PARANOIA_FULL` branch: fixpoint falls through to residue |
| `M5-no-raise` | **RED(4)** | the tier measures and never raises |
| `M6-inside-cache-scopes` | **RED(1)** | the tier runs INSIDE the two cache scopes (§2) |
| `M7-skip-on-empty-union` | **RED(1)** | short-circuit the check when the union is empty |
| `M8-no-verdict-recorded` | **RED(12)** | the verdict is not recorded, so no test can see the tier ran |
| `M9-changed-ignored` | **RED(4)** | reconcile still runs (repairing!) but its verdict is dropped |
| `M10-rank-below-full` | **RED(3)** | `fixpoint` ranked BELOW `full` |
| `M11-first-key-only` | **RED(3)** | the tier checks only the first key of the union |
| `M12-no-bumped-clear` | **INERT** | the tier stops clearing `_bumped` after its re-reconciles |

**Two rows earned changes to the shipped work, and both were INERT before they were RED.**
Per the standing trap, an `INERT` was not believed until the edit was shown to move
something:

* `M2` was INERT on the first run. **Cause measured, not guessed**
  (`.scratch/tk82/probe5.py`): the module's own fixture never produces a non-empty
  `leftover` at all — `_settle` is `None` on every one of its cascades — so the leftover
  half of the union was *untested*, not redundant. On TK73's GC witness it is not redundant
  either: that cascade's rounds schedule `('folder','owner','y')` while `leftover` is
  `('folder','owner','x')`, so the leftover call site is the only reason the union has two
  keys instead of one. `::test_the_union_includes_the_terminal_leftover_keys` was added and
  `M2` now reddens. ⚠ Stated bound, in that test's own docstring: on that path the settle
  pass has already proved the leftover key a fixpoint, so the leftover half cannot
  *currently* produce a raise. It is pinned so the tier's completeness does not rest on the
  settle pass — the mechanism TK74 found structurally blind.
* `M6` was INERT, and that is the honest status of §2's placement decision: no behavioural
  assertion in the module can see whether the tier runs inside or outside the cache scopes.
  Rather than leave the decision as a doc warning,
  `::test_the_tier_runs_outside_the_cache_scopes` pins it mechanically off
  `ReachabilityIndex._node_cache`, and `M6` now reddens.

**`M12` remains INERT and is kept deliberately.** Mechanism: a fixpoint re-reconcile writes
nothing and therefore bumps nothing, and on the `changed` path the tier raises, so no
current arm can observe the clear. It guards a caller that swallows the violation and
reuses the processor — a hazard no test drives today.

### 4.5 Whole-suite FP sweep — 0 false positives, every raise attributed

Same plugin, whole `tests/` tree, 2026-09-19. The first run reported `tier_raises=5` and
that number is **useless without attribution** — five raises could be five false positives
or five true ones, and "5 failed" in the summary is a different set of five. So the plugin
was re-run recording the current test nodeid at each raise:

```
TK82 TIER RAISE @ test_cascade_fixpoint_tier.py::test_full_does_not_imply_the_tier
TK82 TIER RAISE @ test_cascade_fixpoint_tier.py::test_tier_detects_a_skipped_reconcile[skip_key0]
TK82 TIER RAISE @ test_cascade_fixpoint_tier.py::test_tier_detects_a_skipped_reconcile[skip_key1]
TK82 TIER RAISE @ test_cascade_fixpoint_tier.py::test_tier_detects_a_skipped_reconcile[skip_key2]
TK82 TIER RAISE @ test_cascade_fixpoint_tier.py::test_tier_detects_a_skipped_reconcile[skip_key3]
TK82 FP SWEEP: upgraded=1250 tier_cascades=1612 keys_rereconciled=1912 tier_raises=5
5 failed, 1204 passed in 751.93s (0:12:31)
```

**All five are this module's own deliberate fault injection** — four are the detection arms
doing their job, and the fifth is `test_full_does_not_imply_the_tier`, whose arm also
suppresses a reconcile and which the plugin (by design) forces the tier ON for. So on the
**1,607 unmutated cascades** the tier examined, it raised **zero** times. That reproduces
TK74 §10.3's `0 / 2853` on the shipped code, inside its real call site, against traffic the
repo already trusts.

⚠ **The five test FAILURES are plugin artifacts and are not the five raises.** Three are
in `tests/test_paranoia_wiring.py` (`test_reinstall_upgrades_in_place_instead_of_stacking`,
`test_helper_forwards_the_tier[True-full]`, `[full-full]`) and assert an exact installed
level, which a plugin that rewrites `'full'` to `'fixpoint'` necessarily breaks. The other
two are this module's own `'full'`-level arms, for the same reason. **The sweep plugin is
deliberately incompatible with any test that asserts a tier**, and a run of `tests/`
WITHOUT it is green (that is the gate).

⚠ **One artifact is worth keeping, because it independently re-derives §4.1's instrument
finding.** `::test_the_suppressed_reconcile_makes_the_store_oracle_wrong` fails under the
plugin but appears in **no** raise line: that test keeps its suppression armed through the
whole cascade, so the tier's own re-reconcile of the skipped key was suppressed too — no
raise — while its re-reconciles of the *other* keys silently REPAIRED downstream state and
moved the divergence count off 4. An armed instrument does not merely hide the detector; at
this tier it also edits the thing being measured.

---

## 5. Found in passing, and fixed

`docs/architecture/verification.md` §"Paranoia mode" and `docs/architecture/correctness.md`
§3 both asserted that **`ConnectedStore.__init__` never calls `install_paranoia` and
exposes no flag, so production runs with this entire layer dark.** That was true before
ZT-P1-3 and has been false since: `connectedstore/store.py::ConnectedStore.__init__` takes
`paranoia=`, resolves `ZANZIBAR_PARANOIA`, and installs the guard. The claim errs in the
security-relevant direction — it describes a layer that cannot be turned on, when the real
situation is a layer that defaults off and *can* be. Both sentences were corrected
2026-09-19 and both now name the live caller census command instead of a count.
