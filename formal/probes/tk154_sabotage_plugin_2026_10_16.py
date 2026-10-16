"""TK154 sabotage plugin (2026-10-16). Monkeypatches at pytest configure time, so the shared
source tree is never edited. Each mode removes one guard; the expected reds are the table in
docs/tk154-stale-lookup-ids-2026-10-16.md ("Sabotage") and the test docstrings. Re-run 2026-10-16 after the move: failed counts
unchanged, module 14 tests (it had 11 when the table was written).

    S1  both raises in SetEngine._check_id_stamp     -> 4 failed
    S2  `self.frees += 1` in Interner.release         -> 2 failed
    S3  sqlite_autoincrement on Node                  -> 4 failed
    S4  refuse_reusable_node_ids returns at once      -> 1 failed

Run (Bash, repo root; modes may be comma-joined):

    SAB154=S4 PYTHONPATH=formal/probes python -m pytest -p tk154_sabotage_plugin_2026_10_16         tests/test_tk154_stale_lookup_ids.py -q

The name uses underscores (not this directory's hyphenated dates) because `-p` imports it.
"""
import os

MODES = [m for m in os.environ.get('SAB154', '').split(',') if m]


def pytest_configure(config):
    if not MODES:
        return
    for MODE in MODES:
        _apply(MODE)


def _apply(MODE):
    import zanzibar.setengine.engine as eng
    import zanzibar.store._store as st
    from zanzibar.graphindex.models import Node
    if MODE == 'S1':
        # comment out the two raises in _check_id_stamp (missing-id path untouched)
        def _check_id_stamp(self, res, field):
            stamp = res.id_stamp
            if stamp is None:
                return
            return
        eng.SetEngine._check_id_stamp = _check_id_stamp
    elif MODE == 'S2':
        orig = eng.Interner.release

        def release(self, entity_type, name, pred):
            before = self.frees
            out = orig(self, entity_type, name, pred)
            self.frees = before          # as if `self.frees += 1` were deleted
            return out
        eng.Interner.release = release
    elif MODE == 'S3':
        Node.__table__.dialect_options['sqlite']['autoincrement'] = False
    elif MODE == 'S4':
        st.refuse_reusable_node_ids = lambda session: None
    else:
        raise RuntimeError(f'unknown SAB154={MODE!r}')
    print(f'[sab154] applied {MODE}')
