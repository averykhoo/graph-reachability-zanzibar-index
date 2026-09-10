"""The gate run lock: `scripts/gate_lock.py`, and its wiring into `formal/verify.sh`.

PROPERTY GUARDED, in one sentence: two `formal/verify.sh` runs cannot be in flight at
once, and a run that collides with another CANNOT report success.

WHY THIS EXISTS. On 2026-09-10 a `conf-tile:1/5` phase reported ``EXIT=0`` to its caller
under a log whose last line was ``FAIL: conf (pytest rc=1)``. It was filed as a hole in
`verify.sh`'s own exit-code guard; it was not. Two runs overlapped by ~2.5 minutes and
both redirected into the runbook's then-fixed ``/tmp/p.log``, so the caller got the
PASSING run's honest ``rc`` next to the FAILING run's tail. The full reconstruction, the
ledger arithmetic that proves the overlap, and why staleness is age-based rather than
liveness-based are in the ``scripts/gate_lock.py`` module docstring.

THE END-TO-END SABOTAGE, run 2026-09-10 against the real `verify.sh` before this module
was written -- `lean` backgrounded, then a second `lean` started 8 s later::

    ===== SECOND (colliding) RUN: rc=1 =====
    REFUSED: another gate run holds the lock, so this run has done nothing.
             wanted phase: lean
             held by phase: lean (pid 16744, started 2026-09-10T19:16:28, 7 s ago)
             lock file:     .../.gate-runs/gate.lock
    FAIL: refusing to start 'lean' while another gate run holds the lock.
    ===== FIRST RUN: rc=0 =====
    === lean phase (steps 1-4) PASSED (holes=0, audits=587, pinned=587) ===

and the two ledger rows it produced, which is where a later session will look::

    ...T19:16:35  0    lean  FAILED  t2a:1be126f52276  rc=1 refused=lock-held
    ...T19:16:27  171  lean  PASSED  t2a:1be126f52276  rc=0 holes=0 audits=587 ...

The instrument was controlled: the lock file was confirmed GONE after the incumbent
finished (so the pass was not an artefact of a leaked lock), and the incumbent's own
verdict was unaffected.

THE MUTATION SWEEP over `scripts/gate_lock.py` (the 2026-09-08 rule: a sabotage certifies
ONE case, so weaken the check one plausible way at a time and require a NAMED test to
redden for each). Table in ``test_the_mutation_sweep_table_is_recorded`` below.

WHAT THIS MODULE CANNOT DO. The wiring test reads `verify.sh`'s source rather than running
it -- a mirror instrument in the sense of `docs/sabotage-procedure.md`, and it would stay
green if the lock were wired in a way that parses but does not work. That is exactly what
the end-to-end sabotage above covers, and why its literal output is recorded here rather
than in a throwaway log. Running two real gate phases concurrently inside pytest would
cost several minutes per run and is not in the tile budget.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE_LOCK = REPO / "scripts" / "gate_lock.py"
VERIFY_SH = REPO / "formal" / "verify.sh"

REFUSED = 3


def run(*args):
    """Invoke the tool exactly as `verify.sh` does: as a subprocess, on its exit code."""
    return subprocess.run(
        [sys.executable, str(GATE_LOCK), *args],
        capture_output=True, text=True, cwd=str(REPO),
    )


def acquire(lock, owner, phase="lean", stale_after=None):
    args = ["acquire", str(lock), "--phase", phase, "--owner", owner]
    if stale_after is not None:
        args += ["--stale-after", str(stale_after)]
    return run(*args)


def release(lock, owner):
    return run("release", str(lock), "--owner", owner)


def age_the_lock(lock: Path, seconds: float) -> None:
    """Backdate a held lock by rewriting its `started` field AND its mtime.

    Both, because `_read_holder` reads `started` and falls back to mtime -- ageing only
    one of them would leave a test that passes for the wrong reason.
    """
    body = lock.read_text(encoding="utf-8")
    out = []
    for line in body.splitlines():
        if line.startswith("started="):
            out.append("started=%.3f" % (time.time() - seconds))
        else:
            out.append(line)
    lock.write_text("\n".join(out) + "\n", encoding="utf-8")
    old = time.time() - seconds
    os.utime(lock, (old, old))


# --------------------------------------------------------------------------- #
# 1. The core exclusion
# --------------------------------------------------------------------------- #

def test_acquire_on_a_clean_dir_creates_the_lock_and_records_who_holds_it(tmp_path):
    lock = tmp_path / "sub" / "gate.lock"          # parent does not exist yet
    done = acquire(lock, "owner-A", phase="conf-tile:1/5")
    assert done.returncode == 0, done.stderr
    assert lock.exists()
    body = lock.read_text(encoding="utf-8")
    assert "owner=owner-A" in body
    assert "phase=conf-tile:1/5" in body
    assert "started=" in body


def test_a_second_acquire_while_held_is_refused_and_exits_nonzero(tmp_path):
    """THE headline property. If this test ever passes with returncode 0, the gate can
    run two phases at once and a shared caller-side log can again produce EXIT=0 over
    another run's failure."""
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A").returncode == 0
    second = acquire(lock, "owner-B", phase="tests-tile:2/4")
    assert second.returncode == REFUSED, second.stdout + second.stderr
    assert "REFUSED" in second.stderr


def test_the_refusal_names_the_incumbent_and_the_lock_path(tmp_path):
    """A refusal that does not say WHO holds it or WHERE the file is turns into a
    deleted lock file or a re-run loop. Actionability is part of the mechanism."""
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A", phase="lean").returncode == 0
    err = acquire(lock, "owner-B", phase="conf-tile:3/5").stderr
    assert "lean" in err                      # the incumbent phase
    assert "conf-tile:3/5" in err             # the phase that was refused
    assert str(lock) in err or lock.name in err
    assert "delete the lock file" in err      # the escape hatch, stated


def test_a_refusal_is_a_refusal_and_not_a_crash(tmp_path):
    """Nonzero is not enough: a traceback is also nonzero, and would mean the operator
    is reading a bug report instead of an instruction."""
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A").returncode == 0
    second = acquire(lock, "owner-B")
    assert second.returncode == REFUSED
    assert "Traceback" not in second.stderr


# --------------------------------------------------------------------------- #
# 2. Release, and the one way release could hand the gate to two runs
# --------------------------------------------------------------------------- #

def test_release_by_the_owner_frees_the_lock_for_the_next_run(tmp_path):
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A").returncode == 0
    assert release(lock, "owner-A").returncode == 0
    assert not lock.exists()
    assert acquire(lock, "owner-B").returncode == 0


def test_release_by_a_different_owner_refuses_and_leaves_the_lock_in_place(tmp_path):
    """The steal-safety property. A run whose lock was stolen while it was merely slow
    (not dead) must not, on its way out, unlink the lock now held by a LIVE run --
    that would start a second run alongside it via the mechanism meant to prevent
    exactly that."""
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A").returncode == 0
    done = release(lock, "owner-B")
    assert done.returncode == REFUSED, done.stdout
    assert lock.exists(), "a foreign release removed the incumbent's lock"
    assert "owner-A" in done.stderr


def test_releasing_a_lock_that_is_already_gone_succeeds_quietly(tmp_path):
    """`verify.sh` releases from its EXIT trap, which runs on every path including ones
    where the lock was never taken or was stolen. The ledger rule applies: bookkeeping
    must never change a verdict, so this is a success, not an error."""
    lock = tmp_path / "gate.lock"
    assert release(lock, "owner-A").returncode == 0


# --------------------------------------------------------------------------- #
# 3. Staleness -- recovery from a SIGKILLed run, and its boundary
# --------------------------------------------------------------------------- #

def test_a_stale_lock_is_stolen_so_a_killed_run_cannot_brick_the_gate(tmp_path):
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A", phase="lean").returncode == 0
    age_the_lock(lock, 7200)                   # older than the 3600 s default
    done = acquire(lock, "owner-B", phase="conf-tile:1/5")
    assert done.returncode == 0, done.stderr
    assert "owner=owner-B" in lock.read_text(encoding="utf-8")


def test_a_steal_is_announced_and_never_silent(tmp_path):
    """A silent steal is this repo's house failure mode wearing a different hat: the one
    case where the lock hands the gate to two live runs is a wrong staleness call, and
    the operator can only catch it if it is printed."""
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A", phase="lean").returncode == 0
    age_the_lock(lock, 7200)
    out = acquire(lock, "owner-B").stdout
    assert "STALE LOCK STOLEN" in out
    assert "lean" in out                       # who it was taken from
    assert "STOP" in out                       # what to do if that run is alive


def test_a_lock_just_under_the_threshold_is_NOT_stolen(tmp_path):
    """The negative control for the test above. Without it, a mutation that steals
    unconditionally passes the steal tests and disables the whole lock."""
    lock = tmp_path / "gate.lock"
    assert acquire(lock, "owner-A").returncode == 0
    age_the_lock(lock, 60)
    done = acquire(lock, "owner-B", stale_after=3600)
    assert done.returncode == REFUSED, done.stdout
    assert "STALE LOCK STOLEN" not in done.stdout


def test_the_staleness_threshold_is_longer_than_the_longest_legitimate_run(tmp_path):
    """Provenance floor (durability rank 3). The one-shot `all` phase measures ~18-20 min
    and the harness command cap is 600 s, so a threshold at or below ~20 min would steal
    the lock out from under a live run."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import gate_lock
    finally:
        sys.path.pop(0)
    assert gate_lock.DEFAULT_STALE_AFTER_S >= 3600


# --------------------------------------------------------------------------- #
# 4. A damaged lock file -- fail closed while fresh, recoverable when old
# --------------------------------------------------------------------------- #

def test_a_corrupt_but_fresh_lock_is_refused_rather_than_overwritten(tmp_path):
    """Fail-closed. A lock whose body is garbage may still belong to a live run, so
    "I cannot read it" must not become "therefore it is mine"."""
    lock = tmp_path / "gate.lock"
    lock.write_text("this is not a lock body\n", encoding="utf-8")
    done = acquire(lock, "owner-B")
    assert done.returncode == REFUSED, done.stdout
    assert lock.read_text(encoding="utf-8").startswith("this is not")


def test_a_corrupt_and_old_lock_is_recoverable_by_age(tmp_path):
    """The other side of the same coin: a garbled lock must not jam the gate forever."""
    lock = tmp_path / "gate.lock"
    lock.write_text("this is not a lock body\n", encoding="utf-8")
    old = time.time() - 7200
    os.utime(lock, (old, old))
    done = acquire(lock, "owner-B")
    assert done.returncode == 0, done.stderr
    assert "owner=owner-B" in lock.read_text(encoding="utf-8")


def test_an_empty_owner_token_is_refused(tmp_path):
    """Every lock would otherwise share the owner ``''`` and any run could release any
    other run's lock."""
    lock = tmp_path / "gate.lock"
    done = run("acquire", str(lock), "--phase", "lean", "--owner", "   ")
    assert done.returncode != 0


# --------------------------------------------------------------------------- #
# 5. The wiring -- a lock nothing calls guards nothing
# --------------------------------------------------------------------------- #

def test_verify_sh_acquires_the_lock_before_doing_any_phase_work():
    """Scope assertion, per `docs/sabotage-procedure.md` "assert the SCOPE it claims".
    The tool can be perfect and unwired; that is a silently-passing gate, which is the
    class of defect this whole file belongs to."""
    src = VERIFY_SH.read_text(encoding="utf-8")
    assert "scripts/gate_lock.py" in src, "verify.sh no longer calls the lock at all"
    assert "gate_lock.py\" acquire" in src or "gate_lock.py' acquire" in src
    acq = src.index("acquire \"$GATE_LOCK_FILE\"")
    # It must be taken BEFORE the phase dispatch, or a colliding run does its work and
    # only then discovers it was not allowed to.
    dispatch = src.index('case "$PHASE" in\n  lean)')
    assert acq < dispatch, "the lock is taken after the phase dispatch"


def test_verify_sh_releases_the_lock_from_its_exit_trap():
    """Released anywhere else and the lock leaks on the ~30 `exit 1` paths -- which are
    precisely the runs after which someone immediately re-runs the phase."""
    src = VERIFY_SH.read_text(encoding="utf-8")
    trap_at = src.index("gate_on_exit() {")
    trap_end = src.index("trap 'gate_on_exit $?' EXIT")
    body = src[trap_at:trap_end]
    assert "gate_lock.py" in body and "release" in body


def test_verify_sh_only_releases_a_lock_it_actually_holds():
    """`GATE_LOCK_HELD` is what stops a REFUSED run from releasing the incumbent's lock
    on its way out -- the same defect as the foreign-release test above, one layer up."""
    src = VERIFY_SH.read_text(encoding="utf-8")
    assert 'GATE_LOCK_HELD=0' in src
    assert '[ "$GATE_LOCK_HELD" = "1" ]' in src
    trap_at = src.index("gate_on_exit() {")
    guard = src.index('[ "$GATE_LOCK_HELD" = "1" ]')
    rel = src.index("release \"$GATE_LOCK_FILE\"")
    assert trap_at < guard < rel


def test_the_lock_lives_beside_the_run_ledger_and_is_therefore_gitignored():
    """`.gate-runs/` is gitignored for reasons that are load-bearing for the tree id (a
    tracked lock file would sit inside its own hash). A lock written anywhere tracked
    would move `t2c` on every run and stale every tile."""
    src = VERIFY_SH.read_text(encoding="utf-8")
    assert 'GATE_LOCK_FILE="$GATE_RUNS_DIR/gate.lock"' in src
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".gate-runs/" in ignored


def test_the_steal_claims_a_stale_lock_by_RENAME_rather_than_UNLINK():
    """The one property the sweep below found UNPINNED, now pinned as well as it can be.

    Two processes that both judge a lock stale must not both proceed. Stealing by
    ``unlink`` then ``create`` allows exactly that -- and worse, the loser's unlink can
    remove the WINNER's fresh lock, handing the gate to two runs via the mechanism that
    exists to prevent it. Claiming by ``os.rename`` means only the process whose rename
    succeeds continues.

    ⚠ THIS IS A MIRROR INSTRUMENT (`docs/sabotage-procedure.md`): it reads the subject's
    own source, so it pins the SHAPE of the steal and not its behaviour under a real
    race. It exists because the sweep showed the behavioural tests do not notice --
    mutation 10 below is INERT -- and because a genuinely concurrent two-stealer test
    would be timing-dependent, i.e. a flaky test inside the gate, which is a worse
    trade. What is NOT claimed: that the rename path was observed to win a real race.
    """
    src = GATE_LOCK.read_text(encoding="utf-8")
    steal = src[src.index("    grave = "):src.index("def release")]
    assert "os.rename(path, grave)" in steal
    assert "os.unlink(path)" not in steal, "the steal no longer claims the lock atomically"


def test_the_mutation_sweep_table_is_recorded():
    """The sweep is evidence, so it is tracked, not left in a gitignored log (CLAUDE.md:
    "if a run is evidence, it goes in a tracked file the same hour").

    Eleven plausible weakenings of `scripts/gate_lock.py`, applied one at a time, the
    whole module run against each (2026-09-10, ``pytest -x``, so the name is the FIRST
    test to redden, not the only one). Control: unmutated, ``19 passed``::

      1  acquire: steal regardless of age           -> a_second_acquire_while_held...
      2  acquire: never steal (drop the stale path) -> a_stale_lock_is_stolen...
      3  _create: O_CREAT without O_EXCL            -> a_second_acquire_while_held...
      4  acquire: steal silently (drop the notice)  -> a_steal_is_announced...
      5  release: unlink without the owner check    -> release_by_a_different_owner...
      6  release: report an absent lock as an error -> releasing_a_lock_that_is_already_gone...
      7  DEFAULT_STALE_AFTER_S = 60                 -> the_staleness_threshold_is_longer...
      8  _read_holder: unparsable body -> absent    -> a_corrupt_and_old_lock_is_recoverable...
      9  refusal message drops the incumbent phase  -> the_refusal_names_the_incumbent...
     10  steal by unlink instead of atomic rename   -> INERT at sweep time; now
                                                       the_steal_claims_a_stale_lock_by_RENAME...
     11  drop the empty-owner check                 -> an_empty_owner_token_is_refused

    TEN of eleven reddened a named test. **Mutation 10 reddened nothing**, and that is
    the finding rather than a gap to round off (`docs/sabotage-procedure.md`, "The INERT
    change"): no behavioural test in this module can see the difference between an atomic
    and a non-atomic steal, because the difference only appears when two runs steal at
    once. ``test_the_steal_claims_a_stale_lock_by_RENAME_rather_than_UNLINK`` above is
    the structural pin added in response, with its limits stated.

    ⚠ Mutation 10 also caught the INSTRUMENT first. Written as
    ``os.unlink(path); grave = None`` it appeared to redden a named test -- but only
    because the later ``os.unlink(grave)`` then raised ``TypeError``, which is not the
    ``OSError`` that path catches. A crash is not a property. Rewritten as the weakening a
    contributor would actually make (plain ``os.unlink(path)``), it went inert. A sweep
    row can be green for the wrong reason exactly as easily as a test can.

    Mutation 3 is the one to keep in mind: dropping ``O_EXCL`` leaves a tool that behaves
    normally in every single-run test and fails only under the race it exists to prevent.
    """
