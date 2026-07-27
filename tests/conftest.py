import os
from pathlib import Path

import pytest


# --------------------------------------------------------------------------- #
# Preflight: refuse to run a suite that would silently test LESS than it claims
#
# Both guards below exist because of the same failure mode this repo keeps
# re-discovering -- an assurance step that fails by PASSING.  Neither can be
# satisfied by an author "remembering"; they abort collection.
# --------------------------------------------------------------------------- #

def _require_both_setops() -> None:
    """`pyroaring` missing degrades the whole validation matrix, silently.

    `setengine/setops.py` sets ``RoaringSets = None`` on ImportError and
    ``ALL_SETOPS`` shrinks to ``[PySets]``; ``tests/test_matrix.py`` then builds
    its backend list as ``... + ([roaring] if RoaringSets else [])``.  The
    matrix's headline contract -- "compared over a full query grid, under BOTH
    ``SetOps``" (CLAUDE.md) -- collapses to one backend, the test COUNT barely
    moves, and nothing anywhere says so.  `formal/verify.sh` already preflights
    this for the conformance run; `tests/` had no equivalent.

    pyroaring is a declared dependency (`requirements.txt`), so this is never a
    legitimate configuration -- it is a broken environment, and a broken
    environment must fail loudly rather than quietly test half as much."""
    from setengine.setops import ALL_SETOPS, RoaringSets
    if RoaringSets is None or len(ALL_SETOPS) < 2:
        raise pytest.UsageError(
            'pyroaring is not importable, so the set engine silently falls back '
            'to PySets and every "under both SetOps" leg of the validation '
            'matrix collapses to one backend. This is a broken environment, not '
            'a supported mode: pip install pyroaring (it is in requirements.txt).')


def _reject_hypothesis_seed_env() -> None:
    """``HYPOTHESIS_SEED`` is not a thing, and believing it is cost a whole sweep.

    A multi-seed fuzz sweep was run as ``HYPOTHESIS_SEED=7 pytest ... ;
    HYPOTHESIS_SEED=19 pytest ...`` and reported six independent greens.
    hypothesis reads no such variable: all six runs were the SAME default-seeded
    pass, and the tell (identical durations across "different" seeds) was there
    to be seen.  ``docs/gate-runbook.md`` carries a boxed warning about it --
    but a doc cannot stop the next person, and the failure is invisible by
    construction, so it gets a mechanical refusal too.

    The working form is the pytest flag ``--hypothesis-seed=N`` (verified: no
    profile in this repo sets ``derandomize``, which would override it)."""
    if os.environ.get('HYPOTHESIS_SEED'):
        raise pytest.UsageError(
            'HYPOTHESIS_SEED is not read by hypothesis -- setting it runs the '
            'DEFAULT seed while looking like a seeded run, so an N-seed sweep '
            'is really N identical passes (docs/gate-runbook.md). Use '
            '--hypothesis-seed=N instead.')


def pytest_configure(config: pytest.Config) -> None:
    _require_both_setops()
    _reject_hypothesis_seed_env()


# The real-server (PostgreSQL) leg is dropped at COLLECTION time when no DSN is
# configured -- not skipped at run time.
#
# `formal/verify.sh`'s `tests-tile:I/K` phase has ZERO TOLERANCE for a `skipped`
# in the pytest summary, because a tolerated skip is precisely how coverage leaks
# out of a gate while it keeps printing green. A run-time skip here would have
# forced that rule to be relaxed for the whole suite to accommodate one file --
# trading a durable guarantee for a local convenience. Not collecting the module
# keeps `skipped == 0` absolute: the tile floor then adjusts by itself (it is
# derived from the live collection), and setting ZANZIBAR_TEST_DSN only ever adds
# tests, which `-ge` floors welcome.
#
# `ZANZIBAR_PG_REQUIRED=1` deliberately KEEPS the module collected even with no
# DSN, so `tests/dbengine.py::_require_dsn` can fail loudly. That flag exists to
# assert "the server leg really ran"; silently collecting nothing would be the
# same lie in a different costume.
if not (os.environ.get('ZANZIBAR_TEST_DSN')
        or os.environ.get('ZANZIBAR_PG_REQUIRED', '') not in ('', '0', 'false', 'False')):
    collect_ignore = ['test_postgres_ha.py']


@pytest.fixture(scope="session")
def tests_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture
def load_fga_schema(tests_dir: Path):
    def _load(filename: str) -> str:
        with open(tests_dir / "fga_schemas" / filename, 'r') as f:
            return f.read()
    return _load
