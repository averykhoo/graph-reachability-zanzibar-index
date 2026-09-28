"""`P13`: the `CORRESPONDENCE.md` claim-rot gate, pinned WITHOUT a Lean build.

`formal/conformance/claim_rot.py` runs in `verify.sh`'s `lean` phase (steps 4d2 / 4d3),
which needs the Lean toolchain for its OTHER steps.  The checker itself is pure Python,
so its behaviour is pinned here, inside the `tests/` tiles, where every session runs it.

The two sabotage cases the design requires
(`formal/history/claim-rot-gate-design-2026-08-16.md`, "Sabotage plan") are PERMANENT
tests below, not a one-off run:

* (B) `test_B_lean_body_edit_moves_the_pin_while_step_4d_stays_green` -- a one-token
  edit to the BODY of `GraphIndex/Leaf.lean::persistedLeaves` (its `.excl` arm stops
  collecting the subtracted operand's leaves; the signature line is byte-identical).
  The real `anchor_check.main()` (step 4d) returns 0 on that tree and the content pin
  names the symbol.  That pair is the proof (B) sees what 4d structurally cannot.
* (C) `test_C_reinserted_82_of_82_claim_is_refused` -- "Validated: 82/82 derived keys
  agree." put back into the `PLeaf` row.  And the discriminating variant,
  `test_C_a_date_without_a_pastness_word_is_still_refused`.

The sabotage was ALSO run against the live checker on a mutated working tree, before
these tests existed; that literal output, and the mutation sweep over `claim_rot.py`
with its M0 control, are in `docs/p13-claim-rot-gate-2026-09-27.md` section 3.

Every tree edit here is made to a COPY under `tmp_path`, reached by monkeypatching
`anchor_check.resolve_path`; the working tree is never written (the tiles run in
parallel, and a test that edits a tracked file is a test that can leave it edited).
"""

from __future__ import annotations

import re
import sys

import pytest

from formal.conformance import anchor_check, claim_rot

DOC_TEXT = claim_rot.DOC.read_text(encoding="utf-8")

_SHARED: dict = {}


@pytest.fixture
def cache() -> dict:
    """A per-test copy of a module-wide parse cache (keyed by resolved path)."""
    return dict(_SHARED)


def _sub(text: str, old: str, new: str) -> str:
    """Replace EXACTLY one occurrence -- an anchor that matches 0 or 2 times makes a
    sabotage that silently did nothing, the failure docs/sabotage-procedure.md warns of."""
    n = text.count(old)
    assert n == 1, f"sabotage anchor matched {n} times: {old!r}"
    return text.replace(old, new)


def _patch_file(monkeypatch, tmp_path, anchor_file: str, edit):
    """Serve an edited copy of `anchor_file` to BOTH step 4d and the content pin."""
    orig = anchor_check.resolve_path
    real = orig(anchor_file)
    assert real is not None
    text = real.read_text(encoding="utf-8")
    new = edit(text)
    assert new != text
    # A FRESH directory per call.  The parse cache is keyed by path, so a second
    # patch of the same file written to the same tmp path was served the FIRST
    # patch's parse: on 2026-09-27 that made a theorem-STATEMENT edit read as
    # unchanged here (a false green) until this line existed.
    d = tmp_path / f"v{sum(1 for _ in tmp_path.iterdir())}"
    d.mkdir()
    dst = d / real.name
    dst.write_text(new, encoding="utf-8")
    monkeypatch.setattr(anchor_check, "resolve_path",
                        lambda f: dst if orig(f) == real else orig(f))
    return text, new


def _step_4d_rc(monkeypatch, capsys) -> tuple[int, str]:
    """Run the REAL step-4d instrument, not a re-implementation of it."""
    monkeypatch.setattr(sys, "argv", ["anchor_check.py"])
    rc = anchor_check.main()
    out = capsys.readouterr()
    return rc, out.out + out.err


# --------------------------------------------------------------------------- #
# The live tree
# --------------------------------------------------------------------------- #
def test_live_map_is_clean_under_both_checks():
    """The shipped golden matches the shipped tree, and the shipped map has no
    uncited, unmarked ratio.  Also the M0 control for every sabotage below: each
    of them starts from THIS state, so a red here would make them meaningless."""
    assert claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), _SHARED) == []
    assert claim_rot.check_prose_numbers(DOC_TEXT) == []


def test_every_anchor_step_4d_resolves_is_pinned():
    """Coverage, not just agreement: the golden holds exactly the unique anchors
    step 4d extracts, and none of them was dropped as unpinnable."""
    live, _, unpinnable = claim_rot.live_anchor_rows(DOC_TEXT, _SHARED)
    uniq = {f"{f}::{s}" for _, f, s in anchor_check.extract_anchors(DOC_TEXT)}
    assert unpinnable == []
    assert set(live) == uniq == set(claim_rot.read_pin())
    assert len(live) >= claim_rot.MIN_PINNED_ANCHORS


# --------------------------------------------------------------------------- #
# (B) the content pin
# --------------------------------------------------------------------------- #
LEAF = "GraphIndex/Leaf.lean"
PERSISTED_EXCL = (
    "  | .excl a b => persistedLeaves S ty a ++ persistedLeaves S ty b\n"
    "  | e => atomLeaves S ty e\n\n/-- **The union SPINE"
)


def test_B_lean_body_edit_moves_the_pin_while_step_4d_stays_green(
        monkeypatch, tmp_path, capsys, cache):
    before, after = _patch_file(
        monkeypatch, tmp_path, LEAF,
        lambda t: _sub(t, PERSISTED_EXCL, PERSISTED_EXCL.replace(
            " ++ persistedLeaves S ty b\n", "\n", 1)))
    sig = "def persistedLeaves (S : Schema) (ty : String) : Expr → List PLeaf\n"
    assert before.count(sig) == after.count(sig) == 1, "the SIGNATURE must be untouched"

    rc, out = _step_4d_rc(monkeypatch, capsys)
    assert rc == 0, out
    m = re.search(r"anchors: (\d+) parsed .*?, (\d+) resolved", out)
    assert m and m.group(1) == m.group(2), out

    bad = claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache)
    assert len(bad) == 1, bad
    assert bad[0].startswith(f"{LEAF}::persistedLeaves: BODY CHANGED"), bad
    assert "re-read CORRESPONDENCE.md line(s)" in bad[0]


WCHECK = "        if (o_type, relation) in self.schema_info.leaf_families:\n            return False\n"


def test_B_python_body_edit_moves_the_pin(monkeypatch, tmp_path, cache):
    """The BL-2 fence tests the wrong family set -- one token, same signature."""
    _patch_file(monkeypatch, tmp_path, "index_v4/wildcard.py",
                lambda t: _sub(t, WCHECK, WCHECK.replace("leaf_families",
                                                         "derived_families")))
    bad = claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache)
    assert len(bad) == 1 and bad[0].startswith(
        "index_v4/wildcard.py::WildcardIndex.check: BODY CHANGED"), bad


def test_B_comment_and_docstring_edits_do_not_move_the_pin(monkeypatch, tmp_path, cache):
    """The noise control.  A pin that fires on a comment gets regenerated unread."""
    _patch_file(monkeypatch, tmp_path, LEAF,
                lambda t: _sub(t, PERSISTED_EXCL, PERSISTED_EXCL.replace(
                    "  | e => atomLeaves S ty e\n",
                    "  -- a new comment, and /- a block one -/\n  | e => atomLeaves S ty e\n",
                    1)))
    assert claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache) == []

    monkeypatch.undo()
    _patch_file(monkeypatch, tmp_path, "index_v4/wildcard.py",
                lambda t: _sub(t, '"""Public read entry: the BL-2 leaf-name fence',
                               '"""Public read entry (reworded): the BL-2 leaf-name fence')
                .replace(WCHECK, "        # a comment\n" + WCHECK, 1))
    assert claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache) == []


EQUIV_PROOF = "  rw [setEngine_correct S T q,\n      graph_correct_direct S T σ q hWF hPD hSV hSF hqs hqo hReach]\n"


def test_B_theorem_pins_the_statement_not_the_proof(monkeypatch, tmp_path, cache):
    _patch_file(monkeypatch, tmp_path, "Equiv.lean",
                lambda t: _sub(t, EQUIV_PROOF, EQUIV_PROOF.replace("  rw [", "  rw  [")
                               + "  -- proof refactored\n"))
    assert claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache) == []

    monkeypatch.undo()
    _patch_file(monkeypatch, tmp_path, "Equiv.lean",
                lambda t: _sub(t, "    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)\n"
                               "    (hReach : ReachedByAdmitted σ S T) :\n"
                               "    SetEngineModel.check S T q = GraphModel.check σ q := by\n",
                               "    (hqs : q.subject.name ≠ STAR) (hqo : q.object.name ≠ STAR)\n"
                               "    (hReach : ReachedByAdmitted σ S T) (hX : False) :\n"
                               "    SetEngineModel.check S T q = GraphModel.check σ q := by\n"))
    bad = claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache)
    assert len(bad) == 1 and bad[0].startswith(
        "Equiv.lean::backend_equivalence_direct: BODY CHANGED"), bad


EDGE_DERIVED = "    derived: bool = Field(default=False)\n"


def test_B_class_is_pinned_at_its_shell(monkeypatch, tmp_path, cache):
    """A class-level FIELD change moves the class pin; a new method does not."""
    _patch_file(monkeypatch, tmp_path, "index_v4/models.py",
                lambda t: _sub(t, EDGE_DERIVED, EDGE_DERIVED.replace("False", "True")))
    bad = claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache)
    assert len(bad) == 1 and bad[0].startswith("index_v4/models.py::EdgeV4: BODY CHANGED"), bad

    monkeypatch.undo()
    _patch_file(monkeypatch, tmp_path, "index_v4/models.py",
                lambda t: _sub(t, EDGE_DERIVED, EDGE_DERIVED
                               + "\n    def a_new_helper(self) -> int:\n        return 1\n"))
    assert claim_rot.check_content_pin(DOC_TEXT, claim_rot.read_pin(), cache) == []


def test_B_structure_field_anchor_pins_its_parent(cache):
    live, _, _ = claim_rot.live_anchor_rows(DOC_TEXT, cache)
    assert live["GraphIndex/State.lean::Delta.leaf"].startswith("lean:structure:member\t")


def test_B_a_gutted_golden_is_refused(cache):
    pinned = claim_rot.read_pin()
    victim = "GraphIndex/Leaf.lean::persistedLeaves"
    del pinned[victim]
    bad = claim_rot.check_content_pin(DOC_TEXT, pinned, cache)
    assert len(bad) == 1 and bad[0].startswith(f"{victim}: anchored") and "NOT pinned" in bad[0]
    assert any("floor" in b for b in
               claim_rot.check_content_pin(DOC_TEXT, {}, cache))


def test_B_the_floor_binds_when_map_and_golden_shrink_together(cache):
    """Delete almost every row AND regenerate: every live anchor is pinned, and only
    the floor notices."""
    tiny = "| `GraphIndex/Leaf.lean::persistedLeaves` | x | y |\n"
    live, _, _ = claim_rot.live_anchor_rows(tiny, cache)
    assert claim_rot.check_content_pin(tiny, live, cache) == [
        f"the golden lists only 1 anchor(s); floor is {claim_rot.MIN_PINNED_ANCHORS} "
        "-- a gutted golden compares nothing"]


def test_B_a_removed_row_and_an_unpinnable_anchor_are_reported(cache):
    pinned = claim_rot.read_pin()
    doc = DOC_TEXT.replace("`GraphIndex/State.lean::Delta.leaf`", "`Delta.leaf`")
    assert doc != DOC_TEXT
    bad = claim_rot.check_content_pin(doc, pinned, cache)
    assert any(b.startswith("GraphIndex/State.lean::Delta.leaf: pinned but no longer")
               for b in bad), bad
    doc2 = DOC_TEXT + "\n| `GraphIndex/Leaf.lean::noSuchDeclaration` | x |\n"
    bad2 = claim_rot.check_content_pin(doc2, pinned, cache)
    assert len(bad2) == 1 and "no pinnable body" in bad2[0], bad2


# --------------------------------------------------------------------------- #
# (C) the prose-number lint
# --------------------------------------------------------------------------- #
PLEAF_ROW_RE = re.compile(r"^\| \*\*`GraphIndex/Leaf\.lean::PLeaf`.*\|$", re.M)


def _pleaf_row() -> tuple[str, int]:
    m = PLEAF_ROW_RE.search(DOC_TEXT)
    assert m, "the PLeaf row moved; re-anchor this test"
    return m.group(0), DOC_TEXT.count("\n", 0, m.start()) + 1


def _into_pleaf_row(sentence: str) -> tuple[str, int]:
    row, line_no = _pleaf_row()
    assert row.endswith(" |")
    return _sub(DOC_TEXT, row, row[:-2] + ". " + sentence + " |"), line_no


def test_C_the_row_itself_would_have_exempted_the_claim():
    """Why the window is the SENTENCE.  The row already carries a date and a
    pastness word, so 4e's rule applied per row would wave any claim in it through."""
    row, _ = _pleaf_row()
    assert claim_rot.DATE_RE.search(row) and claim_rot.PAST_RE.search(row)


def test_C_reinserted_82_of_82_claim_is_refused():
    doc, line_no = _into_pleaf_row("Validated: 82/82 derived keys agree.")
    bad = claim_rot.check_prose_numbers(doc)
    assert bad == [f"CORRESPONDENCE.md:{line_no}: '82/82' | "
                   "Validated: 82/82 derived keys agree."], bad


def test_C_a_date_without_a_pastness_word_is_still_refused():
    """4e's discriminating case, here: provenance attached to a current-tense claim
    is exactly the shape that rotted."""
    doc, line_no = _into_pleaf_row("Validated 2026-08-16: 82/82 derived keys agree.")
    assert [b.split(" | ")[0] for b in claim_rot.check_prose_numbers(doc)] == [
        f"CORRESPONDENCE.md:{line_no}: '82/82'"]


def test_C_a_pastness_word_without_a_date_is_still_refused():
    """The other half of the contract: "was" alone dates nothing."""
    doc, line_no = _into_pleaf_row("It was 82/82 derived keys agree.")
    assert [b.split(" | ")[0] for b in claim_rot.check_prose_numbers(doc)] == [
        f"CORRESPONDENCE.md:{line_no}: '82/82'"]


@pytest.mark.parametrize("sentence", [
    "Validated: 82/82 derived keys agree (`tests/test_matrix.py::test_matrix_4way_boolean`).",
    "82/82 derived keys agree. Pinned by `formal/conformance/test_conformance_state.py`.",
    "The 82/82 figure lives in FINAL_REVIEW.md's generated counts block.",
    "It was 82/82 when it was measured 2026-08-16, and was retracted.",
])
def test_C_a_cited_or_past_marked_claim_passes(sentence):
    doc, _ = _into_pleaf_row(sentence)
    assert claim_rot.check_prose_numbers(doc) == []


def test_C_a_citation_of_a_test_file_that_does_not_exist_is_refused():
    doc, _ = _into_pleaf_row(
        "Validated: 82/82 derived keys agree (`tests/test_no_such_module.py`).")
    assert len(claim_rot.check_prose_numbers(doc)) == 1


def test_C_a_citation_two_sentences_away_does_not_count():
    doc, _ = _into_pleaf_row(
        "82/82 derived keys agree. Unrelated. Pinned by `tests/test_matrix.py`.")
    assert len(claim_rot.check_prose_numbers(doc)) == 1


def test_C_n_of_m_form_and_the_non_claims():
    bad = claim_rot.check_prose_numbers(
        "A paragraph: only 5 of 21 corpora produced a residue row.\n\n"
        "## Phase 0/2 heading\n\nThe rows 46/56 discharge it; a 194/41 split; tile:1/5.\n")
    assert [b.split(" | ")[0] for b in bad] == ["CORRESPONDENCE.md:1: '5 of 21'"]


@pytest.mark.parametrize("doc", [
    "| a | 3/3 agree |\n| b | pinned by `tests/test_matrix.py::test_matrix_4way_boolean` |\n",
    "| a | 3/3 agree |\nSee `tests/test_matrix.py::test_matrix_4way_boolean`.\n",
    "| a | 3/3 agree\n| `tests/test_matrix.py::test_matrix_4way_boolean` | b |\n",
    "Keys: 3/3 agree\n| `tests/test_matrix.py::test_matrix_4way_boolean` | b |\n",
], ids=["row-row", "row-then-paragraph", "row-without-trailing-pipe",
        "paragraph-then-row"])
def test_C_a_table_row_cannot_borrow_its_neighbours_citation(doc):
    """A table row is its own block (`claim_rot.py::_blocks`).  Only the first shape
    is caught by the cell splitter alone -- the `|` gap between two full rows is an
    empty "next sentence".  The other three are what the row-is-its-own-block rule
    buys: with it disabled (`is_row = False`, mutant M19) each borrowed the adjacent
    citation and went GREEN (probe, 2026-09-28: shipped 1 complaint each, M19 0)."""
    assert [b.split(" | ")[0] for b in claim_rot.check_prose_numbers(doc)] == [
        "CORRESPONDENCE.md:1: '3/3'"]


# --------------------------------------------------------------------------- #
# (C) holes found by the P13 verifier, 2026-09-28 -- each was a live-CLI green
# sabotage or a surviving mutant against 76c471e; each is now refused.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sentence, ratio", [
    ("Validated: around 80/82 derived keys agree.", "80/82"),
    ("Validated against the baseline 82/82 derived keys.", "82/82"),
    ("The pipeline 82/82 derived keys agree.", "82/82"),
    ("Validated: 1,227/1,227 derived keys agree.", "1,227/1,227"),
    ("Validated: 1,227 of 1,227 derived keys agree.", "1,227 of 1,227"),
    ("Validated: 999/1,000 derived keys agree.", "999/1,000"),
    ("Validated: 82 / 82 derived keys agree.", "82 / 82"),
    ("Validated: 82/82 derived keys agree (see doc_counts for suite size).", "82/82"),
    ("Validated: the discipline" + " " * 20 + "82/82 derived keys agree.", "82/82"),
], ids=["around-contains-round", "baseline-contains-line", "pipeline-contains-line",
        "thousands-slash", "thousands-of", "thousands-denominator", "spaced-slash", "bare-doc_counts-word",
        "window-starts-mid-word"])
def test_C_verifier_green_sabotages_are_refused(sentence, ratio):
    """On 76c471e every one of these, in the PLeaf row, left `claim_rot.py --check`
    at rc=0 with '8 N/M claim(s), 0 uncited and unmarked'.  Causes: `ORDINAL_RE` had
    no leading `\\b` (so `around` ended in the ordinal `round`); `\\d+` read
    `1,227/1,227` as `227/1` (N > M, dropped) and never matched a spaced slash; and
    `GEN_RE` accepted the bare word `doc_counts` as a citation.  The last case is the
    fix's own trap: search the ordinal window in a SLICE of the block and `\\b` fires
    at the slice edge, so `discipline` + 20 spaces is skipped as the ordinal `line`
    (`claim_rot.py::_ordinal` searches the whole block with pos/endpos instead)."""
    doc, line_no = _into_pleaf_row(sentence)
    assert [b.split(" | ")[0] for b in claim_rot.check_prose_numbers(doc)] == [
        f"CORRESPONDENCE.md:{line_no}: '{ratio}'"]


def test_C_ordinal_words_and_chains_are_still_not_claims():
    """The other side of the `\\b` and spaced-slash fixes: whole ordinal words and
    one link of a spaced split chain (the map's line-71 shape) stay exempt, and a
    comma-grouped number that is not a ratio is not matched."""
    assert claim_rot.check_prose_numbers(
        "Phase 0/2; the rows 46/56 discharge it; tile 1/5; line 3/9.\n\n"
        "Then 24 / 23 / 33 / 15 files, 13 / 20 / 33 tests; ~3,000 lines; 4,000-op runs.\n"
    ) == []


def test_C_a_semicolon_ends_the_sentence():
    """Mutant K1 (`;` dropped from `SENT_END_RE`) survived: the date and `was` of the
    next clause then exempt a current-tense claim."""
    doc, line_no = _into_pleaf_row(
        "Validated: 82/82 derived keys agree; the 2026-08-16 figure was wrong.")
    assert [b.split(" | ")[0] for b in claim_rot.check_prose_numbers(doc)] == [
        f"CORRESPONDENCE.md:{line_no}: '82/82'"]


def test_C_a_table_cell_ends_the_sentence():
    """Mutant K7 (`|` dropped from `SENT_END_RE`) survived: the cells merge and the
    neighbouring cell's date and pastness word exempt the claim."""
    assert [b.split(" | ")[0] for b in claim_rot.check_prose_numbers(
        "| x | Validated: 82/82 agree | 2026-08-16 was wrong |\n")] == [
        "CORRESPONDENCE.md:1: '82/82'"]


def test_C_out_of_form_is_a_claim():
    """Mutant K2 (`(?:out )?` dropped from `OF_RE`) survived, though the module
    docstring advertises `18 out of 171`."""
    assert [b.split(" | ")[0] for b in claim_rot.check_prose_numbers(
        "Only 18 out of 171 corpora agree.\n")] == ["CORRESPONDENCE.md:1: '18 out of 171'"]


@pytest.mark.parametrize("word", ["retracted", "refuted"])
def test_C_retracted_and_refuted_are_pastness_words(word):
    """Mutant K3 (the two words `claim_rot.py::PAST_WORDS` adds to 4e's list dropped)
    survived, though the CLI's own fix advice gives '82/82, retracted 2026-08-16b' as
    the model form.  No other pastness word is in these sentences (`is`, not `was`)."""
    doc, _ = _into_pleaf_row(f"It is 82/82, {word} 2026-08-16b.")
    assert claim_rot.check_prose_numbers(doc) == []


def test_B_every_binding_of_a_python_name_is_hashed(monkeypatch, tmp_path):
    """Mutant K4 (hash only the FIRST binding) survived, inert on today's map (no
    anchored Python name is multiply bound, verifier probe 2026-09-28).  The
    docstring promises a property AND its setter are hashed; pin it synthetically."""
    src = ("class C:\n"
           "    @property\n    def p(self):\n        return self._p\n\n"
           "    @p.setter\n    def p(self, v):\n        self._p = v\n")
    bodies = []
    for i, text in enumerate([src, src.replace("self._p = v", "self._p = -v")]):
        f = tmp_path / f"v{i}" / "fake_mod.py"
        f.parent.mkdir()
        f.write_text(text, encoding="utf-8")
        monkeypatch.setattr(anchor_check, "resolve_path", lambda _f, f=f: f)
        bodies.append(claim_rot.anchor_body("x/fake_mod.py", "C.p", {}))
    assert bodies[0] is not None and bodies[0][1].count("def p(") == 2
    assert bodies[0][1] != bodies[1][1]
