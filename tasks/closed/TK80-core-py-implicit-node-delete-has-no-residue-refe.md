---
id: TK80
title: core.py implicit-node delete has no residue-reference check, unlike both processor GC paths
brief: THREE branches not two; :884 is the unguarded one; 10 of 5132 evictions ran under a live residue ref, all at core.py:893
pri: NEXT
size: S
deps: []
related: [TK74]
parent:
labels: [formal]
source: hand
source_hash:
created: 2026-09-18b
moved: 2026-09-20f
updated: 2026-09-20f
closed: 2026-09-20f
---

TODO: one paragraph -- what this item is and why it matters.

## Traps

## Read first

## Log

### 2026-09-18c

DRIVEN. Section 9.10 item 2 said "never deliberately driven"; it has been. Map: docs/tk74-staleness-net-2026-09-18.md sections 10.1 and 10.8 (FROZEN doc).

VERDICT: OBSERVED-AND-POSSIBLE. Not unreachable, and no longer unobserved -- section 9.3 "unobserved in 208 arm executions" is REFUTED. It occurs about once per 240 node deletes in the ordinary suite, and a separate census found 10 of 5132 _evict_node calls deleted a node under a LIVE residue reference -- all 10 at core.py:893, and 0 at each processor GC path (0 of 458 at _gc_subject_node, 0 of 992 at _gc_public_node), exactly as their guards predict.

(!) THE ROW BRIEF WAS WRONG IN THREE WAYS, now fixed. (i) There are THREE delete branches, not two: :877 and :894 check implicit only, and :884 (_node = nodes.get(subject_id); if _node: evict; delete) has NO guard at all -- no implicit check, no residue check. Section 9.3 omitted the only unguarded one. (ii) The claimed route _gc_subject_node -> _maybe_remove_bridges is TRANSITIVELY GUARDED: _gc_subject_node returns at :1075-1076 when a residue references the node, before the _maybe_remove_bridges call at :1096. The live route is remove_tuple -> _remove_tuple_trusted:645 -> remove_edge_by_id:1149 -> _remove_edge_locked:1143 -> :894. (iii) "unobserved" is refuted, see above.

VERIFIED FIRST-HAND, with the reason, because the claim as reported did not survive the obvious objection: :877/:884 sit on the self-edge path (subject_id == object_id), and that path is remove_node-only BY CONSTRUCTION -- a self direct edge is never created (:854 guards subject_id != object_id and count > 0), so _remove_edge_locked finds direct_edge_count == 0 and raises AdmissionRejected at :1135-1141. A cycle self Edge row carries only indirect_edge_count and is rejected by the same test. _add_direct_edge_unsafe has exactly three call sites: :1099 add, :1143 remove, :1204 in remove_node.

SEVERITY, and why this stays LATER. On every shipped path the dangling state is TRANSIENT and repaired inside the same transaction: remove_tuple + cascade gave 0 corruptions over 31 removals / 87 node deletes / 2 live-ref hits. It commits as real corruption only via WildcardIndex.remove_node with NO cascade in the same transaction -- I6: residue neg holds a dead node id. remove_node has no caller in connectedstore/ (only wildcard.py:697 -> core.py:1199), and both non-off paranoia tiers REFUSE it pre-commit; it commits silently only at the production default (off). The hazard is already named in-tree by tests/test_reg14_residue_gc_elision.py::test_reg14_cheap_path_self_heals_a_missing_userset_node.

(!) A CONTROL THAT FAILED TO GO RED, and it is the most useful datum here. Stubbing _keys_referencing to [] (neutralising _map_deltas_to_keys branch (A)) on the reproducing workload left the state CLEAN. So branch (A) is NOT the only repair -- the ordinary leaf/dependent fan-out also reconciles the key. The delete safety rests on at least TWO independent downstream repairs, neither of which is a guard on the delete itself. That is the argument for putting the fix ON THE DELETE.

THE FIX WHEN IT IS TAKEN (S, no design decision needed): add the two-clause check the processor already uses -- _residue_row(node.id) is None and not _residue_references(node.id) -- at core.py:882-884 (and optionally :875-877); or make WildcardIndex.remove_node refuse a residue-referenced node, mirroring its existing T:* refusal at wildcard.py:668. Per docs/sabotage-procedure.md it needs a PERMANENT positive test built from the reproducing arm (remove_node, paranoia off, no cascade, assert the refusal).

### 2026-09-20e

PROMOTED LATER -> NEXT, on the same axis as the current `NOW`: removals are where this
tree's coverage actually thins.

The ranking argument, so it is not re-derived. `TK91` (NOW) says the bulk-vs-live
differential never sees a removal; this row says the REMOVE path's own node-delete has no
residue-reference guard on the one branch that is unguarded (`core.py:884`), with 10 of
5132 evictions measured running under a live residue reference. They are the same theme at
two altitudes, and this one is `S` with the fix already written out on the row -- no design
decision is left in it. Taking it alongside `TK91` is cheap and the two share a workload.

What keeps it honest and un-inflated: the row's own SEVERITY paragraph stands unchanged --
on every shipped path the dangling state is transient and repaired in-transaction, and it
commits as real corruption only via `WildcardIndex.remove_node` with no cascade at the
production paranoia default. **The board's "live correctness bugs: 0" is NOT disturbed by
this promotion.** This is hardening plus the permanent positive test
`docs/sabotage-procedure.md` requires, not a defect fix.

Left at `LATER` deliberately in the same pass: `TK71` (its next action is a measurement to
settle its own scope), `TK79`, `TK44`, `TK3`, `TK85`, `TK88`. `NEXT` is capacity 3
(`docs/README.md` sec 4) and is now full: `TK80`, `TK83`, `TK89`.

### 2026-09-20f

CLOSED. Map: docs/tk91-tk80-removal-coverage-2026-09-20.md (ACTIVE-PLAN -> freeze with TK91).

DECISION (delegated per CLAUDE.md "Who decides", design panel + first-hand verification):
FACADE REFUSAL in index_v4/wildcard.py ONLY. core.py is UNTOUCHED, so no modelled algorithm
changed and all 696 CORRESPONDENCE.md anchors still resolve (anchor_check rc=0).

WHY NOT THE CORE GUARD, so it is not re-derived. WildcardIndex.remove_node calls _strip_bridges
BEFORE idx.remove_node and handles "the strip may already have implicit-GC'd the node" with an
early return and no cascade -- so a guard below the facade can be reached too late, while the
facade sits above every branch. Beyond that, a `return` guard at branch C would keep an implicit
rc-0 node alive that a bulk build never creates -- MANUFACTURING EXACTLY THE LIVE-VS-BULK
DIVERGENCE TK91 EXISTS TO DETECT -- and would disable the downstream repair that keys on the node
being gone. A `raise` at C would turn routine remove_tuple traffic into write failures. All of
that buys zero equivalence: the 10 observed hits gave 0 corruptions.

HAZARD RE-OBSERVED FIRST-HAND on the pre-fix tree. It was NOT recoverable by copy -- the frozen
doc tk74-staleness-net-2026-09-18.md 10.1/10.8 carries the RESULT and the I6 string but no schema,
no tuple list, no call sequence, and the .scratch fixture it used is gone. Re-constructed from its
invariants; observed on committed state at paranoia off:
  InvariantViolation: I6: residue neg holds a dead node id 8 on node id=3 doc:x#viewer

THREE WITNESS FINDINGS THAT CORRECT OR EXTEND THIS ROW:
(i) The branch that COMMITS is B (core.py:883), instrumented -- not C. Not a contradiction of the
    census, which counted branch-C hits under ordinary add/remove_edge traffic (0 corruptions).
    Line map re-read 2026-09-20: 876=A, 883=B, 893=C, unmoved.
(ii) THE HAZARD IS neg | upos, NOT JUST neg. Second victim (id 6, a upos subject) was
    implicit=False with reference_count=3 and branch B deleted it anyway -- branch B has neither
    an implicit check nor a refcount check. The guard keys on residue REFERENCE.
(iii) CONTROL C3 IS LOAD-BEARING: the same unguarded branch deletes an UNREFERENCED node and
    commits CLEAN, so the refusal had to be CONDITIONAL. Shipped as a real test.

LANDED: WildcardIndex._residue_records_node (owner clause + ResidueRefV1 reverse index under the
processor's liveness rule; duplicated not imported, because core->processor->wildcard->core is a
real cycle) and the refusal in remove_node, raising AdmissionRejected (ValueError subclass -- a
refusal, not an InvariantViolation which asserts proven corruption), placed BEFORE _strip_bridges
and before any write so I12 rejection cleanliness holds.
PIN: tests/test_reg_tk80_remove_node_residue.py, 11 tests.

SWEEP: M0 attributed correctly. 13 mutations; GAPS_FOUND, both gaps proven-to-move and both closed:
 - M2 dropping the liveness filter was GREEN -- the "agrees with the processor on every node" test
   never reached the one case where they can differ. Closed by
   ::test_a_dangling_residue_ref_does_not_count_as_a_recording.
 - M10 dropping both store_id filters was GREEN. Closed by ::test_the_guard_is_scoped_to_its_own_store,
   which needed a CO-TENANT fixture (two stores on one session/engine sharing one NodeV4 table);
   make_wildcard_index cannot express it, and two isolated DBs would have proved nothing.
(!) A GREEN SABOTAGE was found and fixed before the sweep: moving the refusal below _strip_bridges
left the module `8 passed`, because _strip_bridges writes nothing for any node of the original
fixture. A bridged fixture and ::test_the_refusal_runs_before_the_bridge_strip were added.

ADJUDICATED A BOUNDARY, NOT A GAP: the guard reads the derived ResidueRefV1 index, not the
ResidueV1 neg/upos JSON. DeltaProcessor._keys_referencing reads the same index under the same rule,
so a JSON-reading guard would be a second divergent definition of "referenced"; an index out of
sync with its JSON is already owned by invariants.py::_check_residue_rows -- VERIFIED BY RUNNING IT,
not cited from memory: "I6: residue_ref index disagrees with neg|upos on node id=3 doc:x#viewer".
(!) HONEST CAVEAT FOR THE NEXT SESSION: that check only runs when a paranoia tier is INSTALLED. At
the production default (off) nothing compares the index to the JSON at write time. That is an
argument for ZANZIBAR_PARANOIA=residue in production, not for widening this guard.

(!) BEHAVIOUR CHANGE: remove_node followed by run_cascade in ONE transaction is now refused
(pre-fix control C4, which used to self-repair). No in-tree caller does this; the sanctioned order
is the reverse, and the refusal message names it.

The board's "live correctness bugs: 0" is NOT disturbed. The severity paragraph stands: transient
and repaired in-transaction on every shipped path. This is hardening plus the permanent positive
test docs/sabotage-procedure.md requires.
