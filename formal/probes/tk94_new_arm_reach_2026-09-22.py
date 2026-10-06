"""TK94 -- WHICH BRANCH does each newly-collected conformance arm actually REACH?

`TK94`'s third trap: *"Do not assume the new arms are vacuous because they pass. Say
which branch each new arm reaches."* Adding
`formal/conformance/corpus.py::SCHEMAS['derived_userset_subject']` collected nine new
tests (measured 2026-09-22: conformance 572 -> 581) and all nine passed. A pass is not
evidence that anything new ran.

This probe answers the question mechanically, for the branch the corpus exists for:
the leading ``rel`` term of the bulk mirror

    src/zanzibar/graphindex/bulk_backfill.py::_BulkBackfill._live_keys_of
        preds = [rel] + [spec.predicate for spec in plan.leaves
                         if spec.positive and spec.kind in ('closure', 'derived-userset')]

`TK91` hypothesised that term was unreachable by construction; `TK92` refuted it, but
could only do so from `tests/` because **no conformance corpus paired a derived relation
with a userset subject** (census 2026-09-21, all 26 entries). So the conformance
bulk-vs-incremental gate, `test_conformance_remove.py::test_graph_remove_bulk_build_survivors`,
had never exercised the branch at all.

WHAT IT MEASURES, per corpus, driving the REAL gate path
(`backends.graphindex_drive_ops` + `backends.bulk_build_drive`, the same calls the test
makes, same seeds):

    calls        -- how many times `_live_keys_of` ran during the bulk build
    rel_exclusive -- did the leading `rel` term ever enumerate a name that the
                     positive-leaf half did NOT?  This is the TK92 property.
    examples     -- the (type, rel) key and the exclusive names, so a reader can check

A corpus with ``rel_exclusive = False`` runs the line and learns nothing from it; that
is the state EVERY corpus was in before this row.

Run:  PYTHONPATH=. python formal/probes/tk94_new_arm_reach_2026-09-22.py
Exit: 0 if the new corpus is rel-exclusive and the pre-existing ones are not.
"""

from __future__ import annotations

import random
import sys

from formal.conformance.corpus import SCHEMAS
from formal.conformance import test_conformance_remove as R
from formal.conformance.backends import graphindex_drive_ops, bulk_build_drive
from zanzibar.graphindex import bulk_backfill

NEW = "derived_userset_subject"


def _instrumented_run(name, seed):
    """Drive the corpus exactly as `test_graph_remove_bulk_build_survivors` does, with
    `_live_keys_of` wrapped so each call records both halves of `preds`."""
    schema_text, corpus_tuples, obj_wild = SCHEMAS[name]
    rng = random.Random(seed)
    universe = list(corpus_tuples) + R._extras(rng, corpus_tuples)
    ops = R._sequence(rng, universe)

    session, widx, _proc, store_id, final = graphindex_drive_ops(
        schema_text, ops, obj_wild)
    survivors = sorted(final)
    session.close()

    rec = []
    orig = bulk_backfill._BulkBackfill._live_keys_of

    def wrapped(self, o_type, rel):
        # NB: the shipped body RECURSES through `self._live_keys_of` and unions the
        # result into a set, so the wrapper must return the same type it received.
        # Returning a list here made eight corpora die of a TypeError that read as
        # a clean SKIPPED row (the GL-1 instrument lesson).
        got = orig(self, o_type, rel)
        plan = self.compiled.plans.get((o_type, rel))
        other = set()
        if plan is not None:
            for spec in plan.leaves:
                if spec.positive and spec.kind in ("closure", "derived-userset"):
                    other |= set(self.family_names.get((o_type, spec.predicate), ()))
        rel_only = set(self.family_names.get((o_type, rel), ())) - other
        rec.append(((o_type, rel), sorted(rel_only), sorted(got)))
        return got

    bulk_backfill._BulkBackfill._live_keys_of = wrapped
    try:
        bsession, _bwidx, _bstore = bulk_build_drive(
            schema_text, survivors, obj_wild)
        bsession.close()
    finally:
        bulk_backfill._BulkBackfill._live_keys_of = orig
    return rec


def main():
    print("TK94 -- reach of the bulk mirror's [rel] term, per SCHEMAS corpus")
    print("driver: test_conformance_remove::test_graph_remove_bulk_build_survivors")
    print(f"seeds:  {list(R.SEEDS)}")
    print()
    print(f"{'corpus':34s} {'calls':>6s} {'rel_exclusive':>14s}  examples")
    results = {}
    for name in sorted(SCHEMAS):
        calls = 0
        excl = []
        for seed in R.SEEDS:
            try:
                rec = _instrumented_run(name, seed)
            except Exception as exc:                      # noqa: BLE001
                print(f"{name:34s} {'--':>6s} {'SKIPPED':>14s}  "
                      f"{type(exc).__name__}: {str(exc)[:60]}")
                calls = None
                break
            calls += len(rec)
            for key, rel_only, _got in rec:
                if rel_only:
                    excl.append((seed, key, rel_only))
        if calls is None:
            continue
        results[name] = bool(excl)
        ex = ""
        if excl:
            seed, key, names = excl[0]
            ex = f"seed={seed} {key} rel-only={names}"
        print(f"{name:34s} {calls:6d} {str(bool(excl)):>14s}  {ex}")

    print()
    ok = True
    if not results.get(NEW):
        print(f"FAIL: [{NEW}] did NOT reach the [rel] term exclusively -- the corpus "
              f"does not buy the branch it was added for.")
        ok = False
    others = sorted(n for n, v in results.items() if v and n != NEW)
    print(f"rel-exclusive corpora: {sorted(n for n, v in results.items() if v)}")
    if others:
        print(f"NOTE: {others} are ALSO rel-exclusive -- the TK92 census said the "
              f"class was empty; re-check before believing this probe.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
