"""TK151 (2026-10-20): every ```python block on the user-docs site is EXECUTED.

The user docs live in ``userdocs/`` (Sphinx + MyST). A code example nobody runs is the
doc-shaped version of a test that fails by passing, so:

* One test per page that has at least one ```python block, id = the page's path under
  ``userdocs/`` (``pytest tests/test_userdocs_examples.py -k first-check``).
* All of a page's python blocks run IN ORDER, in ONE fresh interpreter, with a temp cwd,
  as if they were one script. Blocks share names, so a page can build up an example.
* A line ``print(EXPR)  # -> LITERAL`` is CHECKED: it still prints EXPR, and the run fails
  unless EXPR == LITERAL (and, when either side is a bool, ``EXPR is LITERAL``, so
  ``print(1)  # -> True`` is red). Any other line carrying ``# ->`` is refused, so an
  expectation cannot silently go unchecked by being written in a shape the rewrite misses.
* A block whose FIRST line starts with ``# not run:`` is skipped, and must give a reason.
* Only an exact, column-0 ```python fence runs. Any other python-ish fence (```py,
  ```python3, ```pycon, ```{code-block} python, ~~~python, an indented ```python, a
  four-backtick ````python) is refused, because it would render as code and never run.
* Collection refuses zero executed pages, and ``REQUIRED_PAGES`` must all be executed.

Sabotage evidence (2026-10-20, TK151 scaffold), each applied alone and reverted:

    S1 the rewrite emits the expectation as a bare print (``line = f"{indent}print({expr})"``,
       i.e. the check silently dropped; every page would still print and pass):
         FAILED tests/test_userdocs_examples.py::test_the_expectation_check_really_fires
         E  AssertionError: a wrong '# -> False' ran GREEN -- the expectation rewrite is
            not checking anything
         -> 1 failed, 5 passed
    S2 the expectation regex stops matching the ``->`` form (``#\\s*=>`` for ``#\\s*->``):
         FAILED ...::test_page_examples_run[tutorials/first-check.md]
         FAILED ...::test_every_page_parses_and_its_expectations_are_well_formed
         FAILED ...::test_the_expectation_check_really_fires
         E  ValueError: tutorials/first-check.md:26: a '# ->' expectation the checker does
            not understand (only `print(EXPR)  # -> LITERAL` on one line is checked): ...
         -> 3 failed, 3 passed
    S3 flip the placeholder tutorial's ``# -> False`` to ``# -> True`` (a wrong page):
         FAILED ...::test_page_examples_run[tutorials/first-check.md]
         E  AssertionError: tutorials/first-check.md:27: printed False, but the page says
            # -> True
    S4 the fence parser stops recognising ```python (``info == "Python"``), so every page
       would silently drop out of the parametrization:
         E  RuntimeError: userdocs/ has pages but none has a runnable ```python block --
            the example runner collected nothing (did the fence parser break?)
         -> 1 error during collection
    Restored: 6 passed.

TK181 (2026-10-30): a page that leaves a file in its directory runs TWICE there, and the
second run must pass and print what the first printed; the pages that touch files also
run one after another in ONE shared directory. Cost on a loaded machine: 32.6s -> 60.6s
for this module (every page twice + every page shared measured 110s, hence the filters;
``_TOUCHES_FILES`` is held to the observed leftovers by ``test_page_examples_run``).
Sabotage evidence, each applied alone, page restored byte-for-byte (``cmp``):

    T1 ``how-to/stall-recovery.md``: its ``Path("stall.db").unlink(missing_ok=True)`` deleted:
         AssertionError: how-to/stall-recovery.md examples failed (SECOND run in the same
         directory): ... how-to/stall-recovery.md:78: printed 1, but the page says # -> 27
    T2 the same page, unlink deleted AND ``sqlite:///stall.db`` -> ``sqlite:///fanout.db``
       (an earlier page's file):
         AssertionError: 1 page(s) failed in a shared directory:
           how-to/stall-recovery.md examples failed (shared directory): ... SchemaMismatch
         -> test_all_pages_in_one_shared_directory: 1 failed
    T3 ``explanation/consistency.md`` unlink deleted: GREEN, correctly -- the page reopens
       the same store and re-adds a present tuple (writes nothing), so it prints the same.
    Instrument mutants on test_the_run_twice_check_really_fires, each RED (1 failed):
       the stdout comparison off; the ``_TOUCHES_FILES`` guard off; never re-running.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
USERDOCS = ROOT / "userdocs"

# Pages that MUST carry executed examples. The tutorials are "run start to finish by a
# test" (docs/tk151-diataxis-plan-2026-10-20.md); a tutorial whose blocks all vanished, or
# became ``# not run:``, would otherwise just drop out of the parametrization.
REQUIRED_PAGES = frozenset({"tutorials/first-check.md"})

SENTINEL = "USERDOCS-PAGE-OK"
NOT_RUN = re.compile(r"^#\s*not run:(.*)$")
_EXPECT = re.compile(r"^(\s*)print\((.*)\)\s*#\s*->\s*(.*?)\s*$")
_ANY_EXPECT = re.compile(r"#\s*->")
_FENCE = re.compile(r"^([ \t]*)(`{3,}|~{3,}|:{3,})(.*)$")
_RST_PY = re.compile(r"^\s*\.\.\s+((code-block|code|sourcecode)::\s*(python3?|py)\b|(doctest|testcode)::)", re.I)
_PYISH = re.compile(r"\b(python|python3|py|pycon|ipython|ipython3)\b", re.I)

_HELPER = '''\
def _userdocs_expect(got, want, where):
    print(got)
    if isinstance(got, bool) or isinstance(want, bool):
        ok = got is want
    else:
        ok = got == want
    if not ok:
        raise AssertionError(f"{where}: printed {got!r}, but the page says # -> {want!r}")
'''


class Block:
    def __init__(self, page: str, start: int, lines: list[str]):
        self.page, self.start, self.lines = page, start, lines  # start = 1-based line of first code line

    @property
    def not_run_reason(self) -> str | None:
        if not self.lines:
            return None
        m = NOT_RUN.match(self.lines[0].strip())
        return None if m is None else m.group(1).strip()


def parse_blocks(text: str, page: str) -> list[Block]:
    """Return the page's ```python blocks; raise on a python-ish fence that would not run.

    A directive fence (``{note}``, ``{admonition}``, any ``:::``) is MARKUP: its body is
    scanned, so a ```python inside a ````{note} still runs. Any other fence is a code
    block whose body is opaque.
    """
    blocks: list[Block] = []
    lines = text.splitlines()
    stack: list[tuple[str, int]] = []  # open directive fences: (char, length)
    i = 0
    while i < len(lines):
        if _RST_PY.match(lines[i]):
            raise ValueError(f"{page}:{i + 1}: an reST python code directive is never run; "
                             f"use a ```python fence")
        m = _FENCE.match(lines[i])
        if m is None:
            i += 1
            continue
        indent, fence, info = m.groups()
        info = info.strip()
        if stack and not info and fence[0] == stack[-1][0] and len(fence) >= stack[-1][1]:
            stack.pop()
            i += 1
            continue
        if _PYISH.search(info) and not (indent == "" and fence == "```" and info == "python"):
            raise ValueError(f"{page}:{i + 1}: python code fence {lines[i].strip()!r} would render but "
                             f"never run; use a column-0 ```python fence (or start it with '# not run: <why>')")
        if fence[0] == ":" or info.startswith("{"):
            stack.append((fence[0], len(fence)))
            i += 1
            continue
        close = re.compile(r"^[ \t]*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$")
        j = i + 1
        while j < len(lines) and not close.match(lines[j]):
            j += 1
        if j == len(lines):
            raise ValueError(f"{page}:{i + 1}: unclosed code fence")
        if info == "python":
            blocks.append(Block(page, i + 2, lines[i + 1:j]))
        i = j + 1
    if stack:
        raise ValueError(f"{page}: unclosed directive fence {stack[-1][0] * stack[-1][1]!r}")
    return blocks


def rewrite(blocks: list[Block]) -> tuple[str, int]:
    """Concatenate the runnable blocks into one script; return (script, n_expectations)."""
    out = [_HELPER]
    n = 0
    for b in blocks:
        if b.not_run_reason is not None:
            continue
        out.append(f"# ---- {b.page}:{b.start}")
        for k, line in enumerate(b.lines):
            where = f"{b.page}:{b.start + k}"
            m = _EXPECT.match(line)
            if m:
                indent, expr, want = m.groups()
                if not want:
                    raise ValueError(f"{where}: '# ->' with no expected value")
                line = f"{indent}_userdocs_expect(({expr}), ({want}), {where!r})"
                n += 1
            elif _ANY_EXPECT.search(line):
                raise ValueError(f"{where}: a '# ->' expectation the checker does not understand "
                                 f"(only `print(EXPR)  # -> LITERAL` on one line is checked): {line.strip()!r}")
            out.append(line)
    out.append(f"print({SENTINEL!r})")
    return "\n".join(out) + "\n", n


def run_script(script: str, cwd: Path) -> subprocess.CompletedProcess:
    # Its own process and cwd: examples create database files and touch the global SQLModel
    # metadata, neither of which may leak into the test tile. Run from a FILE (not -c) so a
    # traceback shows the failing source line.
    path = cwd / "userdocs_page.py"
    path.write_text(script, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable, str(path)], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", env=env, timeout=300)


def _all_pages() -> list[Path]:
    return sorted(p for p in USERDOCS.rglob("*.md") if "_build" not in p.relative_to(USERDOCS).parts)


def _rel(p: Path) -> str:
    return p.relative_to(USERDOCS).as_posix()


def _runnable_pages() -> list[str]:
    pages = []
    for p in _all_pages():
        blocks = parse_blocks(p.read_text(encoding="utf-8"), _rel(p))
        if any(b.not_run_reason is None for b in blocks):
            pages.append(_rel(p))
    return pages


PAGES = _runnable_pages()
if _all_pages() and not PAGES:
    # An empty parametrization is a SKIP, and a skip is how coverage leaks out of the gate.
    raise RuntimeError("userdocs/ has pages but none has a runnable ```python block -- the "
                       "example runner collected nothing (did the fence parser break?)")


def _page_script(page: str) -> str:
    return rewrite(parse_blocks((USERDOCS / page).read_text(encoding="utf-8"), page))[0]


def _page_failure(page: str, r: subprocess.CompletedProcess, run: str) -> str | None:
    """None if the page ran green, else a message naming the page and the run."""
    lines = r.stdout.strip().splitlines()
    if r.returncode != 0 or not lines or lines[-1] != SENTINEL:
        return f"{page} examples failed ({run}):\n{r.stdout}\n{r.stderr}"
    return None


def _leftovers(cwd: Path) -> list[str]:
    return sorted(p.name for p in cwd.iterdir() if p.name != "userdocs_page.py")


# A page whose text matches this may touch files in its working directory; only those
# pages run in test_all_pages_in_one_shared_directory. test_page_examples_run keeps it
# honest: a page that LEAVES a file behind but does not match is red there.
_TOUCHES_FILES = re.compile(r"sqlite:///|open\(|write_text|write_bytes|\.db\b")


@pytest.mark.parametrize("page", PAGES, ids=PAGES)
def test_page_examples_run(page, tmp_path):
    """TK181: a page that leaves a file behind runs TWICE in the same directory; the second
    run must pass and print exactly what the first printed (every ``# ->`` value included).
    A stranger re-runs a page in the folder they ran it in, and a page that does not delete
    the database file it left behind then prints something else or crashes (0.1.0 trial
    F22, 0.1.1 trial F5). A page that leaves the directory as it found it would re-run the
    same script on the same inputs, so it runs once (that halves the added cost)."""
    text = (USERDOCS / page).read_text(encoding="utf-8")
    assert (msg := _twice_failure(page, text, _page_script(page), tmp_path)) is None, msg


def _twice_failure(page: str, text: str, script: str, cwd: Path) -> str | None:
    """Run ``script`` in ``cwd``; if it left a file there, run it again and compare."""
    first = run_script(script, cwd)
    if (msg := _page_failure(page, first, "first run")) is not None:
        return msg
    left = _leftovers(cwd)
    if not left:
        return None
    if not _TOUCHES_FILES.search(text):
        return (f"{page} leaves {left} in its directory but does not match _TOUCHES_FILES, "
                f"so test_all_pages_in_one_shared_directory skips it; widen the pattern")
    again = run_script(script, cwd)
    if (msg := _page_failure(page, again, "SECOND run in the same directory")) is not None:
        return msg
    if again.stdout != first.stdout:
        return (f"{page}: a second run in the same directory printed something else\n"
                f"--- first run:\n{first.stdout}\n--- second run:\n{again.stdout}")
    return None


def test_all_pages_in_one_shared_directory(tmp_path):
    """TK181: every page that touches files, one after another, in ONE directory (a reader
    working through the docs in one folder). Pages share database file names, so a page that
    assumes a fresh folder breaks on a file an EARLIER page left behind. A page that touches
    no file can neither leave one nor trip over one, so it is not run here."""
    pages = [p for p in PAGES if _TOUCHES_FILES.search((USERDOCS / p).read_text(encoding="utf-8"))]
    assert len(pages) >= 2, f"the shared-directory run selected {pages}; the filter broke"
    failures = []
    for page in pages:
        msg = _page_failure(page, run_script(_page_script(page), tmp_path), "shared directory")
        if msg is not None:
            failures.append(msg)
    assert not failures, (f"{len(failures)} page(s) failed in a shared directory:\n"
                          + "\n".join(failures))


def test_required_pages_are_executed():
    missing = sorted(REQUIRED_PAGES - set(PAGES))
    assert not missing, f"pages that must carry executed examples but do not: {missing}"


def test_every_not_run_block_gives_a_reason():
    bad = []
    for p in _all_pages():
        for b in parse_blocks(p.read_text(encoding="utf-8"), _rel(p)):
            reason = b.not_run_reason
            if reason is not None and len(reason) < 3:
                bad.append(f"{b.page}:{b.start}")
    assert not bad, f"'# not run:' blocks without a reason: {bad}"


def test_every_page_parses_and_its_expectations_are_well_formed():
    # parse_blocks refuses python fences that would never run; rewrite refuses an
    # expectation shape it does not check. Both raise, so this fails on the first offender.
    for p in _all_pages():
        rewrite(parse_blocks(p.read_text(encoding="utf-8"), _rel(p)))


# ---- self-tests of the instrument itself (page-independent) -------------------------------

_SYNTH_OK = "```python\nx = 1 + 1\nprint(x == 2)  # -> True\nprint(x)  # -> 2\n```\n"
_SYNTH_WRONG = "```python\nx = 1 + 1\nprint(x == 2)  # -> False\n```\n"
_SYNTH_BOOL_INT = "```python\nprint(1)  # -> True\n```\n"


def test_the_expectation_check_really_fires(tmp_path):
    ok_script, n_ok = rewrite(parse_blocks(_SYNTH_OK, "synthetic.md"))
    assert n_ok == 2
    ok = run_script(ok_script, tmp_path)
    assert ok.returncode == 0 and ok.stdout.split() == ["True", "2", SENTINEL], ok.stdout + ok.stderr

    for synth in (_SYNTH_WRONG, _SYNTH_BOOL_INT):
        script, n = rewrite(parse_blocks(synth, "synthetic.md"))
        assert n == 1
        r = run_script(script, tmp_path)
        assert r.returncode != 0 and SENTINEL not in r.stdout, (
            "a wrong '# -> False' ran GREEN -- the expectation rewrite is not checking anything\n"
            + r.stdout + r.stderr)
        assert "but the page says # ->" in r.stderr, r.stderr


def test_the_parser_refuses_fences_that_would_not_run():
    for bad in ("```py\nx = 1\n```\n", "```python3\nx = 1\n```\n", "```pycon\n>>> 1\n```\n",
                "```{code-block} python\nx = 1\n```\n", "~~~python\nx = 1\n~~~\n",
                "  ```python\n  x = 1\n  ```\n", "````python\nx = 1\n````\n",
                ":::{code-block} python\nx = 1\n:::\n"):
        with pytest.raises(ValueError):
            parse_blocks(bad, "synthetic.md")
    for bad in ("```{eval-rst}\n.. code-block:: python\n\n   x = 1\n```\n",
                "````{note}\n```python3\nx = 1\n```\n````\n",
                "````{note}\ntext\n"):
        with pytest.raises(ValueError):
            parse_blocks(bad, "synthetic.md")
    # a ```python inside a directive still RUNS, and the directive's close does not swallow the page
    nested = parse_blocks("````{note}\n```python\nx = 1\n```\n````\n\n```python\ny = 2\n```\n", "s.md")
    assert [b.lines for b in nested] == [["x = 1"], ["y = 2"]]
    assert parse_blocks("```sql\n```python\n```\n", "s.md") == []   # opaque code body
    with pytest.raises(ValueError, match="does not understand"):
        rewrite(parse_blocks("```python\nx = 1  # -> 1\n```\n", "synthetic.md"))
    blocks = parse_blocks("```python\n# not run: needs PostgreSQL\nraise SystemExit(1)\n```\n", "s.md")
    assert blocks[0].not_run_reason == "needs PostgreSQL"
    assert "SystemExit" not in rewrite(blocks)[0]


_SYNTH_DRIFTS = ('```python\nfrom pathlib import Path\np = Path("n.db")\n'
                 'p.write_text((p.read_text() if p.exists() else "") + "x")\nprint(len(p.read_text()))\n```\n')
_SYNTH_RESETS = _SYNTH_DRIFTS.replace('p = Path("n.db")\n',
                                      'p = Path("n.db")\np.unlink(missing_ok=True)\n')
assert _SYNTH_RESETS != _SYNTH_DRIFTS
_SYNTH_HIDDEN = '```python\nimport os\nos.mkdir("d")\nprint(1)\n```\n'


def test_the_run_twice_check_really_fires(tmp_path):
    """TK181: the instrument behind test_page_examples_run, on synthetic pages: a page whose
    output drifts with the file it leaves is red, the same page deleting its file first is
    green, and a page that leaves a file without matching _TOUCHES_FILES is red."""
    def twice(name, text):
        cwd = tmp_path / name
        cwd.mkdir()
        return _twice_failure(f"{name}.md", text, rewrite(parse_blocks(text, f"{name}.md"))[0], cwd)

    drift = twice("drifts", _SYNTH_DRIFTS)
    assert drift is not None and "printed something else" in drift, drift
    assert twice("resets", _SYNTH_RESETS) is None
    hidden = twice("hidden", _SYNTH_HIDDEN)
    assert hidden is not None and "widen the pattern" in hidden, hidden
