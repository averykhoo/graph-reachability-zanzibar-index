# `TK161` — the residue userset arm's phantom branch: pinned, not deleted

> **FROZEN 2026-10-26 — provenance, not a living document.** Status lines below are
> as-of-then and several may now be false; live state: `HANDOFF.md` + the session
> ledger. Corrections are appended dated at the top, never edited into the body.

> **Correction 2026-10-26 (repair round 1, same session).** First-hand READ + RUN. The row
> body says "the `subj is None` returns" (plural), but the close pinned only the USERSET
> arm; the BARE-subject arm's identical disjunct had no recorded pin (S2 was inert here,
> and a reviewer measured it inert in `tests/test_p6_phantom_subject.py` +
> `tests/test_lookup_oracle.py`: 59 passed). Added `BARE_SCHEMA` / `test_bare_ghost_*` to
> `tests/test_tk161_seedless_phantom_arm.py` (ghost `user:zed` under `user:*` on a
> `but not` relation, via the compiled facade's public read and the seedless facade).
> Observed with `formal/probes/tk161_sabotage_2026_10_26.py`: no mode `8 passed`; S1
> `2 failed, 6 passed`; S2 `4 passed, 4 errors`
> (`check parity broken after add ('...', 'user', '*', 'viewer', 'doc', 'd1'):
> q=('...', 'user', 'zz-ghost', 'can', 'doc', 'd1') graph=False oracle=True`, raised by
> `ParityEngine`'s per-op ghost grid in the fixture). The literal output is in the test
> module's docstring. The P6 docstring's "no longer inert anywhere it matters" was reworded:
> S1 is still inert inside the P6 module and is red only in the TK161 module.

Frozen at `TK161`'s close (session `2026-10-26e`, release-0.1.0 workflow). Follow-up from
`TK144` (`docs/tk138-userset-self-relation-2026-10-14.md`, Corrections 2026-10-17, S13/S14).

## 1. The branch and who reaches it

- **First-hand READ (2026-10-26):** `src/zanzibar/graphindex/wildcard.py::WildcardIndex._check_derived`,
  userset arm, last line `return subj is None or subj.id not in neg`. A phantom subject
  (no node) cannot be in `neg`, so star coverage alone answers. The arm runs when the TK144
  read-time branch does not: `reflexive=False` (reconcile, invariants, I9), or
  `WildcardIndex._reflexive_reads` False (no seed table).
- **First-hand PROBE (2026-10-26, inline `python -c`, P6 schema):** `parse_openfga_schema`
  gives `self_seeds` of size 9 and `derived_families` `[('doc','admin'), ('doc','gate')]`;
  `compiler.py::derive_schema_info` on the same AST gives 0 seeds and NO derived families.
- **REASONED:** `compiler.py::_self_seed_table` adds `(T, p, p)` for every declared `(T, p)`,
  so any compiled schema with a derived relation has a non-empty seed table. No public
  construction path builds a seedless facade with derived families; only a hand-built
  `SchemaInfo` passed to `WildcardIndex(idx, schema_info)` does, which the
  `WildcardIndex.__init__` comment documents ("reads non-reflexively throughout").

## 2. Decision: pin

Deleting the `subj is None` disjunct would make a seedless facade's phantom read raise
`AttributeError` (`None.id`) instead of answering; the bare-subject arm keeps the same idiom
for ghosts on the public read, so the two arms would also stop reading alike. Pinning costs
one test module and changes no code, so no modelled algorithm moves (`formal/CORRESPONDENCE.md`
§7 TK144 note gained a TK161 line; `formal/FINAL_REVIEW.md` §3.1 item 9 likewise).

## 3. Pin and sabotage (first-hand, 2026-10-26)

`tests/test_tk161_seedless_phantom_arm.py`: the P6 schema and store through `ParityEngine`,
then a second `WildcardIndex` over the same `ReachabilityIndex` with
`replace(schema_info, self_seeds=frozenset())`. Asserts non-vacuity (seedless facade reads
non-reflexively, compiled one reflexively, f9 has no node, `admin`/`gate` derived) and that
the seedless answer equals the live unanimous `ParityEngine.check` answer (True) for
`folder:f9#viewer` at `admin`/`gate` on `doc:d1`, plus the f1 control.

Sabotage plugin `formal/probes/tk161_sabotage_2026_10_26.py` (in-memory patch, source never
edited). Literal verdicts:

    (no mode)  4 passed
    S1  userset arm -> `subj is not None and subj.id not in neg`
          RED: 2 failed, 2 passed  [phantom f9 derived], [phantom f9 strat2]
          E   AssertionError: phantom f9 derived / assert False is True
    S2  same edit on the bare-subject arm (wrong-arm control)
          GREEN -- INERT (4 passed)

`tests/test_p6_phantom_subject.py` + the new module: 13 passed (before the docstring edits;
both still green after).
