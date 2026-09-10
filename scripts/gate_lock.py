#!/usr/bin/env python3
"""One gate run at a time: an exclusive lock `formal/verify.sh` takes for its phase.

    python scripts/gate_lock.py acquire <lockfile> --phase <p> --owner <tok>
    python scripts/gate_lock.py release <lockfile> --owner <tok>

THE DEFECT THIS CLOSES (2026-09-10, task ``GL-1``). On 2026-09-10 a `conf-tile:1/5`
phase reported ``EXIT=0`` to its caller under a log whose last three lines were::

    FAILED formal/conformance/test_sorry_scan.py::test_main_reports_scanned_and_skipped_counts
    60 failed, 50 passed in 220.62s (0:03:40)
    FAIL: conf (pytest rc=1)

The session filed it as a hole in ``verify.sh``'s own exit-code guard
(``gate_on_exit``, the INCONSISTENT branch). It was not. `verify.sh` behaved
perfectly: it detected the failure, exited 1, and recorded ``FAILED ... rc=1`` in
the ledger. Bash preserves an exit status across a returning EXIT trap (tested
three ways on bash 5.2.26), so nothing was lost.

TWO RUNS WERE IN FLIGHT AT ONCE, and the caller read the wrong one's log. From
`.gate-runs/ledger.tsv`, whose first column is the START time and second the
duration in seconds::

    run A  started 14:35:01  ran 225 s -> ended 14:38:46   FAILED  60 failed, 50 passed
    run B  started 14:36:14  ran 196 s -> ended 14:39:30   PASSED  110 passed

B started 73 s into A. Both followed the recipe in `docs/gate-runbook.md`, which
until today named a FIXED path -- ``bash formal/verify.sh <phase> > /tmp/p.log
2>&1; rc=$?``. Two processes redirecting to one path each truncate it and then
write at their own independent offsets; A emitted 6466 lines and finished first,
B emitted ~30 and finished last, so B's PASSED banner landed at a low offset and
A's failure tail stayed at the end of the file. ``rc`` was B's honest 0. ``tail``
was A's failure. Reproduced verbatim before this lock was written.

Note the shape, because it is the third variant of CLAUDE.md footgun #1 and it
needs neither of the first two's ingredients: no pipe eats the status, and no
orphaned interpreter writes the log. It is simply two runs and one filename. The
concurrency is also the most plausible CAUSE of A's 60 failures -- they were all
``rc=3221225794`` (``0xC0000142``, STATUS_DLL_INIT_FAILED) on ``zcli`` spawn,
which is what two tiles racing to spawn the same large Lean binary looks like;
run C, alone, passed 110/110 on the same tree.

WHY A LOCK IS THE RIGHT MECHANISM, rather than a longer warning in the runbook.
`docs/sabotage-procedure.md` "Prefer a mechanical refusal to a doc warning" ranks
a docstring last, and this defect has an unusually sharp illustration of why: the
fixed ``/tmp/p.log`` recipe WAS the documented remedy for footgun #1 (piping
through ``tail`` eats the exit code), and it created footgun #3. A third warning
would have been the third thing nobody reads at the moment it matters.

With the lock, a colliding run cannot report success. It refuses, nonzero, before
doing any work -- so the worst a shared log can now produce is a confusing tail
next to an HONEST nonzero status, never ``EXIT=0`` over someone else's failure.

IT ALSO CLOSES THE 2026-09-08b ORPHAN VARIANT, which was a separate finding with
a separate write-up. There, the harness killed the shell at its command cap while
the ``pytest`` child survived, and the NEXT phase overlapped with the orphan and
shared its log file. `verify.sh` re-execs itself (parent tees, child works), so
the surviving process in that story is the child -- the one that holds this lock
and releases it from its EXIT trap. An orphan therefore keeps the lock, and the
next phase refuses instead of overlapping. One mechanism, both variants.

STALENESS, and why it is age-based rather than liveness-based. A run killed by
SIGKILL leaves the file behind, and a lock that can permanently brick the gate is
worse than the race it prevents. The obvious check -- is the recorded pid alive?
-- is not available portably here and is actively dangerous on this platform:
``os.kill(pid, 0)`` on Windows does not probe, it calls ``TerminateProcess``, so
the "liveness check" would kill the incumbent run. The pid recorded below is also
an MSYS pid (`verify.sh` runs under Git Bash) and means nothing to a Windows
Python. So the file records ``started`` and a lock older than ``--stale-after``
(default ``DEFAULT_STALE_AFTER_S``) is stolen, LOUDLY.

The default has provenance: the longest legitimate run is the one-shot ``all``
phase at ~18-20 min (`formal/verify.sh` header, measured 2026-07-26), and the
harness command cap is 600 s, so 3600 s is more than 3x the longest run anything
here can legitimately hold it for. A stolen lock always prints; a silent steal
would be this repo's house failure mode wearing a different hat.

STEALING IS ATOMIC-ISH, VIA RENAME, not unlink-then-create. Two processes that
both judge a lock stale would otherwise both unlink, and the loser's unlink could
delete the WINNER's fresh lock -- handing the gate to two runs by way of the
mechanism that exists to prevent exactly that. Only the process whose ``os.rename``
of the stale file succeeds proceeds to create; the other refuses.

OUTPUT IS ASCII-ONLY, deliberately. `verify.sh` runs under a cp1252 console on
this box (`formal/conformance/doc_counts.py::_ascii` carries the same note, and
the 2026-09-10 run log shows a mangled character where one leaked through).

Pinned by ``tests/test_gate_lock.py``, which carries the end-to-end sabotage
against the real `verify.sh` and the mutation sweep over this module.
"""

from __future__ import annotations

import argparse
import errno
import os
import sys
import time

# See the module docstring: 3x the longest legitimate run (`all`, ~18-20 min).
DEFAULT_STALE_AFTER_S = 3600

# Exit codes. Nonzero is the whole contract -- `verify.sh` branches on "did this
# succeed", not on which nonzero -- but a distinct code lets a test assert that a
# refusal is a REFUSAL and not, say, a traceback that also happens to be nonzero.
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_REFUSED = 3


def _fields(text):
    """Parse the `key=value` lock body. Unknown/garbled lines are ignored."""
    out = {}
    for line in text.splitlines():
        if '=' in line:
            k, _, v = line.partition('=')
            out[k.strip()] = v.strip()
    return out


def _read_holder(path):
    """(fields, age_seconds) for the lock at `path`, or None if it is gone.

    The age falls back to the file's mtime when `started` is missing or garbled,
    so a CORRUPT lock is still recoverable by age instead of jamming the gate
    forever -- and a corrupt lock that is FRESH is still refused, which is the
    fail-closed direction.
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except FileNotFoundError:
        return None
    except OSError:
        text = ''
    fields = _fields(text)
    now = time.time()
    try:
        age = now - float(fields['started'])
    except (KeyError, ValueError):
        try:
            age = now - os.path.getmtime(path)
        except OSError:
            return None
    return fields, max(age, 0.0)


def _body(owner, phase):
    return (
        'owner=%s\n'
        'phase=%s\n'
        'pid=%d\n'
        'started=%.3f\n'
        'stamp=%s\n'
    ) % (owner, phase, os.getpid(), time.time(),
         time.strftime('%Y-%m-%dT%H:%M:%S'))


def _create(path, owner, phase):
    """Atomically create the lock. True on success, False if one already exists."""
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            return False
        raise
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(_body(owner, phase))
    return True


def _refuse(path, fields, age, phase):
    sys.stderr.write(
        "REFUSED: another gate run holds the lock, so this run has done nothing.\n"
        "         This is not a gate failure -- it is the gate refusing to run two\n"
        "         phases at once. Two concurrent runs sharing one caller-side log\n"
        "         file is how a PASSING phase came to report EXIT=0 under a log\n"
        "         ending '60 failed' on 2026-09-10 (see scripts/gate_lock.py).\n"
        "\n"
        "         wanted phase: %s\n"
        "         held by phase: %s (pid %s, started %s, %d s ago)\n"
        "         lock file:     %s\n"
        "\n"
        "         Wait for that run to finish, then re-run this phase. If you are\n"
        "         certain no gate run is alive, delete the lock file above; a lock\n"
        "         older than %d s is stolen automatically.\n"
        % (phase, fields.get('phase', '?'), fields.get('pid', '?'),
           fields.get('stamp', '?'), int(age), path, DEFAULT_STALE_AFTER_S))


def acquire(path, phase, owner, stale_after):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as exc:
            sys.stderr.write('gate_lock: cannot create %s (%s)\n' % (parent, exc))
            return EXIT_REFUSED

    if _create(path, owner, phase):
        print('gate lock acquired: %s (phase %s)' % (path, phase))
        return EXIT_OK

    held = _read_holder(path)
    if held is None:                       # released between our create and our read
        if _create(path, owner, phase):
            print('gate lock acquired: %s (phase %s)' % (path, phase))
            return EXIT_OK
        held = _read_holder(path)
        if held is None:
            sys.stderr.write('gate_lock: %s keeps appearing and vanishing; refusing.\n' % path)
            return EXIT_REFUSED
    fields, age = held

    if age <= stale_after:
        _refuse(path, fields, age, phase)
        return EXIT_REFUSED

    # Stale. Claim it by RENAME so two would-be stealers cannot both win (see the
    # module docstring), and say so out loud -- a silent steal is a fail-open.
    grave = '%s.stale-%s' % (path, owner)
    try:
        os.rename(path, grave)
    except OSError:
        held = _read_holder(path)
        if held is None:
            sys.stderr.write('gate_lock: lost the steal race on %s; refusing.\n' % path)
            return EXIT_REFUSED
        _refuse(path, held[0], held[1], phase)
        return EXIT_REFUSED
    try:
        os.unlink(grave)
    except OSError:
        pass
    print('STALE LOCK STOLEN: %s was held by phase %s (pid %s) since %s, %d s ago,\n'
          '    which is older than the %d s staleness threshold -- assuming that run\n'
          '    died without releasing it. If it is in fact alive, STOP: you now have\n'
          '    two gate runs and neither log can be trusted.'
          % (path, fields.get('phase', '?'), fields.get('pid', '?'),
             fields.get('stamp', '?'), int(age), int(stale_after)))
    if not _create(path, owner, phase):
        held = _read_holder(path)
        if held is not None:
            _refuse(path, held[0], held[1], phase)
        return EXIT_REFUSED
    print('gate lock acquired: %s (phase %s)' % (path, phase))
    return EXIT_OK


def release(path, owner):
    """Drop the lock, but ONLY if we still hold it.

    Releasing someone else's lock is the one way this tool could hand the gate to
    two runs, and it is reachable: our own lock may have been stolen while we ran
    (we were slow, not dead), in which case the file now belongs to a live run and
    unlinking it would be worse than leaking. Refuse, loudly, and leave it.
    """
    held = _read_holder(path)
    if held is None:
        print('gate lock already gone: %s' % path)
        return EXIT_OK
    fields, _age = held
    if fields.get('owner') != owner:
        sys.stderr.write(
            'REFUSED: %s is held by another run (owner %s, phase %s), not by this one\n'
            '         (owner %s). Leaving it alone -- releasing it would let a second\n'
            '         run start alongside the one that owns it.\n'
            % (path, fields.get('owner', '?'), fields.get('phase', '?'), owner))
        return EXIT_REFUSED
    try:
        os.unlink(path)
    except OSError as exc:
        sys.stderr.write('gate_lock: cannot remove %s (%s)\n' % (path, exc))
        return EXIT_REFUSED
    print('gate lock released: %s' % path)
    return EXIT_OK


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='gate_lock.py',
        description='Exclusive lock so only one formal/verify.sh phase runs at a time.')
    ap.add_argument('action', choices=('acquire', 'release'))
    ap.add_argument('lockfile')
    ap.add_argument('--phase', default='?', help='the phase name, for the refusal message')
    ap.add_argument('--owner', required=True, help='token identifying this run')
    ap.add_argument('--stale-after', type=float, default=DEFAULT_STALE_AFTER_S,
                    help='seconds after which a held lock is presumed abandoned')
    args = ap.parse_args(argv)
    if not args.owner.strip():
        ap.error('--owner must be a non-empty token')
    if args.action == 'acquire':
        return acquire(args.lockfile, args.phase, args.owner, args.stale_after)
    return release(args.lockfile, args.owner)


if __name__ == '__main__':
    sys.exit(main())
