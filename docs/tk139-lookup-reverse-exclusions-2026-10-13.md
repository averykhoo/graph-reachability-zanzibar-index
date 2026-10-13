# TK139 -- `SetEngine.lookup_reverse` carries `but not` exclusions (2026-10-13)

**FROZEN 2026-10-13d, at `TK139`'s close -- provenance, not a living document.** Status lines
below are as-of-then. Corrections are appended dated at the top, never edited into the body.

> **Correction 2026-10-13d (TK139 review, fix lead; RUN first-hand).** Three things this
> doc missed:
> 1. **A red it caused.** The fix changed the body of `SetEngine.lookup_reverse`, which is
>    content-pinned in `formal/correspondence_anchor_pin.txt`, so
>    `tests/test_claim_rot_gate.py` went RED (`8 failed`: `BODY CHANGED (py:function
>    b2c221457f9d9b26 -> py:function bdf26f4f0f4427dd); re-read CORRESPONDENCE.md line(s)
>    1901`). Sec 6 did not record it. Line 1901 was re-read ("`lookup_reverse` is `expand`
>    rendered and rides on the `expand` model") and is still true; the pin was regenerated
>    (`python formal/conformance/claim_rot.py --generate`: 1 changed, 0 added, 0 removed),
>    after which the module is `42 passed`.
> 2. **The sec 5 gap is wider than stated.** Under M1, EVERY `test_lookup_oracle_gate_*`
>    stayed green, not just the generated-schema gate: `pytest tests/test_lookup_oracle.py
>    -k gate` gave `9 passed, 38 deselected` (the seeded `_gate_wildcards`, `_gate_boolean`,
>    `_gate_demorgans_reverse`, `_gate_owc_star_ttu` and both generated-schema gates). That
>    gap is now tracked as an open row, `TK142`, not only here.
> 3. **The service-boundary helper.** `SetEngine.result_keys` translated only `node_ids`,
>    while its docstring called its output "the portable form of a lookup result", so a
>    caller that shipped only keys and markers re-created the over-grant at the boundary.
>    `SetEngine.excluded_keys` was added and the docstrings were corrected, pinned by
>    `tests/test_tk139_lookup_reverse_exclusions.py::test_excluded_keys_is_the_portable_exclusion_channel`.
>    Also: the older `docs/spec-deviations.md` 2026-07-12 entry ("set `lookup_reverse` drops
>    `neg`") got a dated correction; the sec 2 census had missed it.

Row: `python scripts/task.py show TK139`. Filed from `docs/pypi-trial-0.0.4-2026-10-13.md`
BROKEN-1 (probe p05). Provenance labels: **READ** (first-hand read of the tree), **RUN**
(first-hand run, output quoted), **REASONED**. Session `2026-10-13d`. All scouting,
implementation and sabotage below were done first-hand by the TK139 lead (no subagent
report is relied on).

## 1. The defect and its cause (READ + RUN, 2026-10-13d)

* `src/zanzibar/setengine/engine.py::SetEngine.lookup_reverse` rendered `expand` as
  `node_ids = pos`, `markers = stars`, and dropped `neg`. Under
  `define viewer: [user:*] but not banned`, a `user:*` grant and `mallory` banned, the
  result was `markers={('user','...')}`, `excluded_node_ids=set()`: "every user".
* `src/zanzibar/graphindex/wildcard.py::WildcardIndex.lookup_reverse` (what
  `ConnectedStore.lookup_reverse` serves) fills `excluded_node_ids` from the derived
  relation's residue `neg`, in graph `Node`-row ids. The PyPI README tells callers to
  subtract it.
* `src/zanzibar/setengine/memberset.py::_normalize` builds `pos = E - starpop` and
  `neg = starpop - E`, so `pos` and `neg` are disjoint and `neg` lies inside starred
  shapes. `neg` therefore has exactly the graph field's meaning: "every subject of a
  marker's shape except these". (READ)
* `SetEngine.lookup` (forward) already filled `excluded_node_ids` since TK116, under object
  wildcards; only the reverse direction dropped it.

## 2. Census: what described or pinned the drop (READ, 2026-10-13d)

| site | what it said | action |
|---|---|---|
| `tests/test_lookup_oracle.py` module docstring, S3 | "the documented neg-dropping render of expand ... marker-covered-but-O-false is LEGAL" | rewritten: S3 exact two-sided |
| `tests/test_lookup_oracle.py::_check_set_reverse` | one-sided completeness; never read `excluded_node_ids` | now asserts `excluded == neg`, exclusion soundness, and two-sided exactness against the oracle (same shape as the graph's G3/G4) |
| `src/zanzibar/setengine/engine.py::LookupResult.__init__` comment | "Only a `but not` / `and` under an object wildcard fills it" | now names both fillers |
| `src/zanzibar/connectedstore/store.py::LookupNotFresh` docstring | `excluded_node_ids` "exists only on the graph side -- it cannot be reconstructed from a set-engine result at all" | corrected: both sides fill it, each in its own id domain |
| `docs/spec-deviations.md` 2026-07-27b, `docs/architecture/decision-log.md` "at_least" entry | "has no set-engine counterpart at all" | dated correction blockquotes appended (append-only logs, body not rewritten) |
| `tests/test_lookup_hypothesis.py::surfaces_match_oracle` comment | "exact/one-sided" | now "exact" |
| `PYPI_README.md` "Reading lookup results" | described `ConnectedStore` only | one paragraph added on the standalone `SetEngine`'s same three fields and its id space |
| `CHANGELOG.md` | -- | `## [Unreleased]` / `### Fixed` entry (the TK122 heading test reads only numeric version headings) |

Not changed, on purpose: `docs/pypi-trial-*` and closed rows (as-of-then records);
`docs/specs/graph-boolean-ivm-spec.md` (graph-side spec, still accurate).

## 3. The fix (LANDED, 2026-10-13d)

`SetEngine.lookup_reverse` adds `result.excluded_node_ids = set(m.neg)`, with the docstring
stating the contract. IDs stay instance-local interner ids (`se.interner.key(i)` resolves
them), as `node_ids` always were; unifying the two backends' id domains is NOT this row
(it is the "portable lookup key contract" prerequisite named in the decision log).

**Equivalence statement pinned** (REASONED from the tests below): after translating ids to
`(type, name, predicate)` keys, the two backends return the same concrete keys, the same
marker shapes (graph `'any'` variant projected), and the same excluded keys on the p05
repro and on a mixed-grant twin; and "listed = in node_ids, or marker-covered and not
excluded" equals the oracle's allowed set on both.

## 4. Tests (RUN, 2026-10-13d)

* NEW `tests/test_tk139_lookup_reverse_exclusions.py`: `test_p05_repro_both_backends_agree`
  and `test_mixed_grants_both_backends_agree`, each over `ALL_SETOPS` (4 tests). The mixed
  twin adds a concrete grant (bob), two bans on `doc:d`, and carol banned only on `doc:d2`
  (interned, star-covered, must NOT be excluded). Observed: bob is star-covered, so BOTH
  backends carry him by the marker, with `node_ids` empty on each side.
* NEW `tests/test_lookup_oracle.py::test_tamper_set_reverse_is_caught` (both SetOps):
  honest result passes; cleared exclusions fail; cleared exclusions compared against an
  `expand` that also lacks `neg` (the exact pre-TK139 render) fail by the ORACLE half;
  a wrong exclusion (bob) fails.
* S3 strengthened in `_check_set_reverse` (above).

## 5. Sabotage (RUN, 2026-10-13d, docs/sabotage-procedure.md)

**M1** -- fix line `result.excluded_node_ids = set(m.neg)` replaced by `pass`; ran the new
module + `tests/test_lookup_oracle.py`: `7 failed, 44 passed`.

```
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_p05_repro_both_backends_agree[py]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_p05_repro_both_backends_agree[roaring]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_mixed_grants_both_backends_agree[py]
FAILED tests/test_tk139_lookup_reverse_exclusions.py::test_mixed_grants_both_backends_agree[roaring]
FAILED tests/test_lookup_oracle.py::test_lookup_oracle_dense_boolean - Failed...
FAILED tests/test_lookup_oracle.py::test_tamper_set_reverse_is_caught[py] - A...
FAILED tests/test_lookup_oracle.py::test_tamper_set_reverse_is_caught[roaring]
E AssertionError: SetEngine[py] excluded set() != graph {('user', 'mallory', '...')}
E AssertionError: SetEngine[py] excluded set() != graph {('user', 'mallory', '...'), ('user', 'eve', '...')}
E AssertionError: set.lookup_reverse('viewer', 'doc', 'd1') [py]: excluded_node_ids set() != expand.neg {7}
```

**M2** (instrument control) -- M1 plus S3's structural `excluded_node_ids == set(m.neg)`
assertion disabled (`assert True or ...`), `-k "dense_boolean or tamper_set_reverse"`:
`3 failed`, the oracle half alone catching it:

```
E AssertionError: set.lookup_reverse('viewer', 'doc', 'd1') [py] vs oracle on subject (...,user,u1): set=True oracle=False (node_ids, or a marker minus excluded_node_ids)
```

Both files restored from byte copies; `grep -c "SABOTAGE\|assert True or"` = 0 on both and
`git diff src/zanzibar/setengine/engine.py` shows only the fix.

**Observed gap, not fixed here** (RUN): under M1 the generated-schema gate tests in
`tests/test_lookup_oracle.py` (ci profile, 6 examples) stayed GREEN; only the scripted
`test_lookup_oracle_dense_boolean` and the tamper test caught it. The random schema pool
rarely produces a `[T:*] but not` reverse lookup with an interned excluded subject. The two
deterministic pins cover TK139; widening the generator is a separate assurance item.

## 6. State

Closed 2026-10-13d. Targeted runs on the final tree (RUN, fresh mktemp logs, rc=0 each):
`tests/test_matrix.py` 17 passed; the new module, `test_lookup_oracle`,
`test_lookup_hypothesis`, `test_tk122_release_metadata`, `test_tk116_oracle_only_setengine`,
`test_reads`, `test_reg18_leaf_name_read_leak`, `test_setengine_eval`,
`test_blind_audit_regressions`, `test_zt_p1_8`, `test_tk111_stall_aware_freshness`,
`test_tk126_ttu_target_name_collision` together 239 passed. The full `verify.sh` gate was
NOT run by this lead (a dedicated gate agent runs it). Open follow-up: the generator gap in
section 5.
