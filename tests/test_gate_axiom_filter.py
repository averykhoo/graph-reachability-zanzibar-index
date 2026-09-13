"""`formal/audit_axiom_filter.sh` — the gate's axiom allowlist, pinned.

WHAT THIS GUARDS. `formal/verify.sh` step 4 reads every `#print axioms` report from the
Lean build and fails if any theorem depends on an axiom outside {propext,
Classical.choice, Quot.sound}. That check is the only thing standing between the gate and
a `sorryAx`-backed headline, and `Audit.lean`'s own header records the attack it exists to
stop.

WHY THIS MODULE EXISTS (2026-09-13e, `TK68`). The allowlist was two inline `grep`s and the
second was anchored `\\]$`. **Lean wraps a `#print axioms` message at ~100 columns**, so a
long enough declaration name puts the axiom list on continuation lines and the head line
ends `[propext,` with no closing bracket. The anchored allowlist did not match, and the
gate reported "non-standard axioms in the audit" for a theorem whose axioms are the
standard three — observed on `W4Witness.sxThruDerived_other_admission_fields_hold` while
closing `TK68`:

    info: ...'...sxThruDerived_other_admission_fields_hold' depends on axioms: [propext,
     Classical.choice,
     Quot.sound]

A guard that reddens on a benign input is how a guard gets RELAXED: the obvious repair is
to drop the `$` anchor or prefix-match `[propext`, and either would make the check blind to
a wrapped list whose tail carries `sorryAx`. So the filter rejoins the wrapped line and
keeps the allowlist anchored and exact — and `test_wrapped_bad_axiom_is_still_caught` is
the arm that refuses the tempting repair.

⚠ THIS MODULE RUNS THE REAL SCRIPT, never a copy of its pipeline. A hand-written mirror of
a checker is its own failure mode (`docs/sabotage-procedure.md` §"The mirror instrument"
and §"Never hand-write a Bool mirror of a `Prop` without PROVING it"); a reimplementation
here could pass while the shipped filter was broken.

SABOTAGE TABLE — literal observed behaviour, 2026-09-13e. Each row is a plausible
weakening of `audit_axiom_filter.sh`; the right-hand column is which test reddens. The
instrument control is S0.

    S0  flip `test_clean_unwrapped_is_silent`'s own expectation      test_clean_unwrapped_is_silent
                                                                     (control: attributed)
    S1  drop the `$` anchor from the allowlist                       INERT -- see below
    S2  prefix-match `\\[propext` instead of the full list           test_unwrapped_bad_axiom_is_caught,
                                                                     test_wrapped_bad_axiom_is_still_caught,
                                                                     test_extra_axiom_in_wrapped_list_is_caught,
                                                                     test_chatter_between_wrap_lines_...
    S3  delete the awk join (i.e. restore the pre-fix pipeline)      test_wrapped_clean_is_silent,
                                                                     test_wrapped_bad_axiom_is_still_caught,
                                                                     test_extra_axiom_in_wrapped_list_is_caught,
                                                                     test_chatter_between_wrap_lines_...
    S4  join ANY line onto the previous one, not only unterminated
        `depends on axioms` lines                                    test_build_chatter_is_not_glued_on
    S5  make the filter print nothing at all (the blind guard)       test_unwrapped_bad_axiom_is_caught,
                                                                     test_wrapped_bad_axiom_is_still_caught,
                                                                     test_extra_axiom_in_wrapped_list_is_caught,
                                                                     test_chatter_between_wrap_lines_...

S5 is the one worth reading: a filter that outputs nothing is INDISTINGUISHABLE from a
clean audit to `verify.sh`, because the step's contract is "empty output means clean". The
three positive-catch tests are what make that observable, and they are the reason this
module asserts on dirty input rather than only on clean input.

⚠ TWO ROWS OF THIS TABLE WERE WRONG WHEN FIRST WRITTEN, AND THE SWEEP IS WHAT FOUND IT --
not review. A sabotage table asserting a red that does not happen is the same defect as a
trap citing a symbol that does not exist, and it is just as invisible.
* **S1 is INERT, and the `$` anchor is therefore DEFENSIVE, not load-bearing.** Dropping
  it changes nothing on any input here: the unanchored pattern still needs a literal
  `[<allowed>…]` substring, and `[propext, Classical.choice, sorryAx]` contains no such
  substring because the bracket closes after the offending name. Do not delete the anchor
  on the strength of this row -- Lean's formatting is not a contract -- but do not cite it
  as guarded either.
* **S4 was inert until the test was fixed.** `test_build_chatter_is_not_glued_on`
  originally fed chatter that begins with its own `info:`/`warning:` lines, which flush
  the S4 buffer before the unprefixed line arrives; the mutation was therefore invisible
  and the table's claim was false. The arm now puts a bare `Build completed…` line
  IMMEDIATELY after a terminated report, which is the ordering that actually glues. This
  is `P6` step 2's rule applied to a mutation's TARGET rather than its subject: state what
  the edit was supposed to move, then check that the arm can see it move.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FILTER = REPO / "formal" / "audit_axiom_filter.sh"

STD = "[propext, Classical.choice, Quot.sound]"

pytestmark = pytest.mark.skipif(
    shutil.which("sh") is None,
    reason="POSIX sh not on PATH; the gate itself needs bash, so this cannot be a "
           "tolerated skip in CI -- see formal/verify.sh's preflight",
)


def run_filter(text: str) -> list[str]:
    """Run the SHIPPED filter over `text`; return the offending lines it prints."""
    assert FILTER.is_file(), f"{FILTER} is missing -- verify.sh calls it by path"
    proc = subprocess.run(
        ["sh", str(FILTER)],
        input=text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO),
    )
    assert proc.returncode == 0, (
        "the filter must exit 0 whether or not it finds offenders -- verify.sh reads its "
        f"STDOUT, not its status. stderr={proc.stderr!r}"
    )
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def report(name: str, axioms: str) -> str:
    return f"info: ZanzibarProofs/Audit.lean:1:0: 'Zanzibar.{name}' depends on axioms: {axioms}"


def wrapped(name: str, head: str, *tail: str) -> str:
    """Lean's ~100-column wrap: head line unterminated, continuations indented."""
    lines = [f"info: ZanzibarProofs/Audit.lean:1:0: 'Zanzibar.{name}' depends on axioms: {head}"]
    lines.extend(f" {t}" for t in tail)
    return "\n".join(lines)


CHATTER = [
    "info: ZanzibarProofs/Audit.lean:2:0: 'Zanzibar.axiom_free' does not depend on any axioms",
    "warning: ZanzibarProofs/Foo.lean:9:0: unused variable `x`",
    "Build completed successfully (1089 jobs).",
]


def test_clean_unwrapped_is_silent():
    """The ordinary case: a one-line standard report is not an offender."""
    assert run_filter(report("ordinary", STD)) == []


def test_wrapped_clean_is_silent():
    """★ THE BUG THIS FILE EXISTS FOR. A wrapped standard triple is clean."""
    text = wrapped("a_very_long_witness_name_that_makes_lean_wrap_the_axiom_list",
                   "[propext,", "Classical.choice,", "Quot.sound]")
    assert run_filter(text) == []


def test_unwrapped_bad_axiom_is_caught():
    """The audit's whole purpose: `sorryAx` on one line is reported."""
    out = run_filter(report("hollow", "[propext, sorryAx]"))
    assert len(out) == 1 and "sorryAx" in out[0]


def test_wrapped_bad_axiom_is_still_caught():
    """★ THE ARM THAT REFUSES THE TEMPTING REPAIR (S1/S2).

    A wrapped list whose HEAD is the innocent `[propext,` and whose TAIL carries
    `sorryAx`. Loosening the anchor, or prefix-matching `[propext`, makes this pass as
    clean -- which is the exact shape of report the fix had to keep catching.
    """
    text = wrapped("a_very_long_witness_name_that_makes_lean_wrap_the_axiom_list",
                   "[propext,", "Classical.choice,", "sorryAx]")
    out = run_filter(text)
    assert len(out) == 1, out
    assert "sorryAx" in out[0], out


def test_extra_axiom_in_wrapped_list_is_caught():
    """A wrapped list that is otherwise standard but carries one extra axiom."""
    text = wrapped("another_long_name_forcing_the_wrap_in_lean_output",
                   "[propext,", "Classical.choice,", "Quot.sound,", "Foo.bar]")
    out = run_filter(text)
    assert len(out) == 1 and "Foo.bar" in out[0], out


def test_build_chatter_is_not_glued_on():
    """S4's arm: the join must not swallow unrelated build output.

    A general "join any line that is not a new `info:`/`warning:`" rule would append
    `Build completed successfully (...)` to a report line, leaving it no longer ending
    `]` — so a perfectly standard triple would be reported as a non-standard axiom. That
    is the same false-positive class as the wrap bug this module exists for, arriving
    from the opposite direction.

    ⚠ THE ORDERING IS LOAD-BEARING AND WAS WRONG AT FIRST. This test originally put the
    bare chatter after `CHATTER`'s own `info:`/`warning:` lines, which FLUSH the buffer
    under S4 — so the mutation came back INERT and the docstring's claim that this arm
    caught it was false. The sweep found that, not review. The bare line must come
    IMMEDIATELY after a terminated report, with nothing prefixed in between.
    """
    adversarial = "\n".join([
        report("ordinary", STD),
        "Build completed successfully (1089 jobs).",
    ])
    assert run_filter(adversarial) == [], (
        "a clean report followed immediately by unprefixed build chatter must stay "
        "silent -- if the chatter is glued on, the report stops ending in `]` and the "
        "allowlist reports a standard triple as an offender"
    )
    # …and the same holds with the fuller, more realistic tail.
    assert run_filter("\n".join([report("ordinary", STD), *CHATTER])) == []


def test_chatter_between_wrap_lines_does_not_hide_a_bad_axiom():
    """The adversarial ordering: chatter interleaved into a wrapped BAD report.

    Whatever the join does with the intervening line, the `sorryAx` tail must not be
    silently dropped. This pins that the filter errs toward REPORTING rather than
    toward silence -- the correct direction for a guard whose empty output means clean.
    """
    text = "\n".join([
        "info: ZanzibarProofs/Audit.lean:1:0: 'Zanzibar.longname' depends on axioms: [propext,",
        "Build completed successfully (1089 jobs).",
        " sorryAx]",
    ])
    out = run_filter(text)
    assert any("sorryAx" in ln for ln in out), out


def test_does_not_depend_on_any_axioms_is_never_an_offender():
    """An axiom-FREE theorem is not an axiom violation.

    (`verify.sh` has a separate check for a headline that reports axiom-free, which is
    its own erosion -- a `: True := trivial` restatement. That is step 4's business, not
    this filter's, and conflating them here would double-report.)
    """
    assert run_filter("\n".join(CHATTER)) == []


def test_filter_is_wired_into_verify_sh():
    """The filter is worthless if the gate stopped calling it.

    Reads `verify.sh`'s source rather than running it (the same compromise
    `test_gate_lock.py` documents): running the gate from a test would take minutes and
    recurse into this suite.
    """
    src = (REPO / "formal" / "verify.sh").read_text(encoding="utf-8")
    assert "formal/audit_axiom_filter.sh" in src, (
        "verify.sh no longer invokes the axiom filter -- step 4's allowlist is not running"
    )
    assert 'BAD=$(echo "$AUDIT_OUT" | sh' in src, (
        "verify.sh still computes BAD, but no longer by piping the audit output through "
        "the filter script"
    )
    # The pre-fix inline pipeline must not have come back alongside it: two allowlists
    # would let one rot while the other stayed green.
    assert src.count("Quot\\.sound)*\\]$") == 0, (
        "the inline allowlist regex is back in verify.sh -- there must be exactly one "
        "allowlist, in formal/audit_axiom_filter.sh"
    )
