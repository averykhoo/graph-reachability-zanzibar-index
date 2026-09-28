# `P13`: the `CORRESPONDENCE.md` claim-rot gate — build record

**ACTIVE-PLAN (`docs/README.md` §3), opened 2026-09-27 (session `2026-09-27d`).** Corrections
are appended dated at the top. FROZEN when `P13` closes. Live state is
`python scripts/task.py show P13`, never this file. The design this executes is
[`formal/history/claim-rot-gate-design-2026-08-16.md`](../formal/history/claim-rot-gate-design-2026-08-16.md)
(ACTIVE-PLAN for the same row). Figures were measured on 2026-09-27 in a worktree at
master `d4ea804` plus this session's diff.

> **Correction 2026-09-28b (fixer, after the P13 verifier returned FIX_REQUIRED) — (C)
> had three live green sabotages and four unpinned behaviours; all are now refused or
> pinned.** Each verifier claim was re-run first-hand (MEASURED, probe
> `check_prose_numbers` on 76c471e) before anything was changed, and every one held:
> `around 80/82`, `baseline 82/82`, `pipeline 82/82` → 0 claims (`ORDINAL_RE` had no
> leading `\b`, so `around` ended in the ordinal `round`); `1,227/1,227` → 0 claims (read
> as `227/1`, N > M, dropped); `82 / 82` → not matched; "(see doc_counts for suite
> size)" → exempt (`GEN_RE` accepted the bare word); `tests/test_matrix.py::test_matrix`,
> the test fixture's "valid citation", does not exist (grep `^def test_` finds only
> `test_matrix_4way_*` and `test_demorgan_*`). Fixes, all in
> `formal/conformance/claim_rot.py`: `ORDINAL_RE` gets `\b` and is searched by
> `::_ordinal` over the WHOLE block with pos/endpos (a slice would make `\b` fire at the
> slice edge; the `window-starts-mid-word` case pins that); numbers are
> `::_NUM` (comma groups) and compared via `::_num`; `SLASH_RE` takes a spaced slash but
> not one link of a spaced chain (`24 / 23 / 33` stays a split); `GEN_RE` now requires
> "FINAL_REVIEW.md's generated counts block". The live map is unchanged by any of this:
> the census is still the same 8 claims, 0 uncited and unmarked (MEASURED). New honest
> limits in the module docstring: Lean whitespace normalisation hides an
> indentation-only re-nesting; `rows 82/82` is exempt as an ordinal; `all 82 of the 82`
> is not matched. §2's table now carries a provenance column. Tests: 26 → 42 in
> `tests/test_claim_rot_gate.py`. The live-CLI re-run of the sabotages and mutation
> sweep 4 (39 runs, M0 control) are in §3.4.

> **Correction 2026-09-28 (resumed implementer, same session key) — M19 was NOT
> equivalent; it is now KILLED.** §3.3 as first written called the one surviving mutant
> (M19, "a table row is no longer its own block") equivalent under the cell splitter.
> That was REASONED and wrong. MEASURED by a probe that ran `check_prose_numbers` under
> the shipped `_blocks` and under M19 (complaints shipped / M19):
> `row_then_paragraph 1/0`, `row_no_trailing_pipe 1/0`, `paragraph_then_row 1/0`,
> `neighbour_rows 1/1`. The `|` gap between two FULL rows is an empty "next sentence",
> which is why the one row-row test could not see it; but a row adjacent to a paragraph
> line (either side), or a row with no trailing pipe, borrows the neighbour's citation
> under M19. `tests/test_claim_rot_gate.py::test_C_a_table_row_cannot_borrow_its_neighbours_citation`
> is now parametrized over all four shapes, and sweep 3 (literal output in §3.3) kills
> all 22 mutants. The module now collects 26 tests, not 23.

Provenance labels: **READ** (first-hand, this session), **MEASURED** (a run whose output
is quoted), **REASONED**, **UNVERIFIED**. No subagent was used; every figure below is
first-hand.

## § 0 Scouting (written before any code, per `CLAUDE.md` "SCOUTING IS A DELIVERABLE")

### 0.1 What already exists

* READ — `formal/conformance/anchor_check.py` (step 4d) resolves every `file::symbol`
  anchor in `formal/CORRESPONDENCE.md`, Python by `ast` (`::python_symbols`) and Lean by a
  declaration scanner with namespace tracking (`::lean_symbols`), including structure
  fields and constructors (`Delta.leaf`). Anchors are extracted by `::extract_anchors`,
  which also handles the bare `::Sym` continuation form. It checks NAVIGABILITY only.
* READ — `formal/conformance/statement_pin.py` (steps 4b/4c) extracts Lean theorem
  STATEMENTS (`::extract`, up to the top-level `:=`, proof not pinned) and full
  definition TEXT (`::index_definitions`, `def`/`structure`/`class`/`inductive`/`abbrev`/
  `instance`), comment-stripped (`::strip_comments`) and whitespace-normalized
  (`::normalize`), into goldens that are regenerated only with `--generate`.
* READ — `formal/conformance/doc_counts.py::check_corpus_count_prose` (step 4e's prose
  half) is the analogue for (C): a number is accepted if it is LIVE, or if its line (plus
  the two before it) carries a date AND a pastness word (`::_PAST_WORDS`, `::_DATE_RE`).

### 0.2 Re-measured figures (the design's as-of-2026-08-16 numbers are stale)

* MEASURED 2026-09-27 — `anchor_check.py`:
  `CORRESPONDENCE.md anchors: 718 parsed (402 Python >= 250, 316 Lean >= 100), 718 resolved`.
  UNIQUE `(file, symbol)` pairs: **474** (248 Python, 226 Lean). (B) pins the unique set.
* MEASURED 2026-09-27 — (A)'s backlog. Method: every declaration under
  `formal/lean/ZanzibarProofs/`, excluding any whose enclosing namespace has a component
  ending in `Witness`, counted as anchored if some anchor in the same file resolves to it
  by dotted suffix. First measured by a throwaway probe (column-0 declarations only),
  then REPRODUCED EXACTLY by the tracked `python formal/conformance/claim_rot.py
  --coverage` (which also admits indented declarations), so the figure regenerates:
  `2336 non-witness Lean declarations, 200 anchored; non-theorem 523, anchored 154;
  28 of 70 files have none`. Of those, non-theorem
  declarations **523, anchored 154 (29%)**; **28 of 70** files have zero anchored
  declarations. The design's 2026-08-16 figure was 143 of 396 (36%); the backlog it
  called 253 is now **369** non-theorem declarations.
* READ 2026-09-27 — (C)'s current candidates in `formal/CORRESPONDENCE.md` (line numbers
  as of `d4ea804`): `82/82` (l.1002) and `744/744` (l.1005), both inside the 2026-08-16b
  retraction bullet; `5 of 21` (l.649) and `11 of 13` (l.661) in the superseded §5
  projection paragraph; `18 of 171` (l.957) in the 2026-07-28 filing's end-note;
  `132/299` (l.1140), which already cites a test; `Phase 0/2` (l.198), a heading.
* READ — the original live "82/82" was replaced in commit `c01ad33`. The row that now
  carries the allocation claim (`GraphIndex/Leaf.lean::PLeaf`, l.366) contains both
  dates and the word "was". **So a pastness exemption scoped to the ROW (or to 4e's
  three-line window) would have let the sabotage through**: re-inserting "82/82 derived
  keys agree" into that row would inherit the row's unrelated "2026-08-16 ... was
  measured WRONG". REASONED consequence: (C)'s exemption is scoped to the SENTENCE.

### 0.3 Decision on (A), the reverse-anchor ratchet: NOT BUILT (the model's, under "Who decides")

REASONED from the figures above:

1. Of the four defects that motivated the design (82/82 live; two rows describing a
   changed model; `unionSpineLeaves` unanchored; the binary-`Expr` divergence missing from
   §7), (A) catches **none**: (C) catches the first, (B) the second, the design itself
   says (A) would NOT have caught the third, and the fourth is not mechanizable.
2. The backlog it would ratchet against grew from 253 to 369 in six weeks, and 28 of 70
   files are unmapped. A "new file must be fully anchored" rule would fire on almost
   every proof session (the tree gained lemma files at that rate), and a proof session
   under pressure satisfies it by adding a row, not by thinking about the row, which
   converts a coverage gate into boilerplate.
3. A floor on the anchored count "so it can only rise" is already what
   `anchor_check.py::MIN_PY_ANCHORS` / `::MIN_LEAN_ANCHORS` do for anchors.

So (A) adds cost with no recorded defect behind it. If it is ever built, the witness
exclusion must be structural (a namespace component ending in `Witness`, as the probe
above measures it), never a list.

## § 1 What was built (READ: the files named)

* `formal/conformance/claim_rot.py` (NEW) — `--check` runs both checks, `--generate`
  rewrites the (B) golden and lists what changed, `--coverage` prints the (A) census
  (report only, never a gate). Its module docstring carries the per-kind definition of
  "body" and the honest limits of each check.
* `formal/correspondence_anchor_pin.txt` (NEW golden) — one row per unique anchor:
  `<file>::<symbol> TAB <kind> TAB <sha256 prefix>`. MEASURED 2026-09-27 at generation:
  474 rows; Lean 140 `def`, 66 theorem statements, 13 `structure`, 4 `inductive`,
  2 `abbrev`, 1 structure member (`GraphIndex/State.lean::Delta.leaf`); Python 211
  functions, 33 class shells, 4 assignments. MEASURED by a throwaway probe: no Lean
  anchor's body spans more than one declaration, and no Python anchor has more than one
  binding statement, so the multi-match paths in `claim_rot.py::anchor_body` are
  currently unexercised by the live map.
* `formal/conformance/anchor_check.py` — `::python_symbols` now reads from a new
  `::python_nodes`, the ONE walker both 4d and 4d2 use, so the two checks cannot
  disagree about what a Python anchor names. Behaviour unchanged: 4d still prints
  `718 parsed (402 Python >= 250, 316 Lean >= 100), 718 resolved` (MEASURED).
* `formal/verify.sh` — steps 4d2/4d3 run `claim_rot.py --check` directly after 4d in
  the `lean` phase (the header's check list names them too). NOT run by this session:
  the `lean` phase needs `.lake`, which a worktree does not have. The exact command it
  runs was run by hand (MEASURED, rc=0, ~5.5 s wall).
* `tests/test_claim_rot_gate.py` (NEW) — pins the checker without a Lean build, in the
  `tests/` tiles. Both design sabotages are permanent tests there.
* `formal/CORRESPONDENCE.md` — seven ratio claims marked as past measurements (§2) and
  a new §9.5 telling authors what the two checks want.

### 1.1 Design decisions taken in-session (the model's, under `CLAUDE.md` "Who decides")

* **D1: (B) pins a hash, not the text.** `headline_definitions.txt` stores full text for
  a small closure; 474 rows of full Python class and function text would make the golden
  a second copy of the source. The failure names the anchor and the rows that cite it,
  which is what the reader needs; `git diff` of the source shows what changed.
* **D2: what "body" means per kind** (the list is in the module docstring). The two
  choices that are not obvious: a Lean THEOREM pins its statement only (the rule
  `statement_pin.py` already follows, because proof refactors are normal work), and a
  Python CLASS pins only its shell — decorators, bases, fields, class constants — not its
  methods. A whole-class hash would fire on every edit to `WildcardIndex` or
  `SetEngine`; a gate that fires on everything gets regenerated without being read,
  which is the one failure (B) cannot detect. A method is pinned if a row anchors it,
  and 211 rows do.
* **D3: comments and docstrings never move a hash.** Lean text goes through
  `statement_pin.strip_comments` / `::normalize`; Python goes through `ast.unparse`
  after the docstring is dropped. Pinned by
  `tests/test_claim_rot_gate.py::test_B_comment_and_docstring_edits_do_not_move_the_pin`.
  Consequence stated in the docstring: a Python upgrade that changes `unparse` output
  moves every Python hash at once. That is loud, not silent.
* **D4: an anchor 4d resolves but 4d2 cannot pin is a FAILURE**, never a skip — a
  silent drop is exactly the coverage leak this row exists to close. None exist today
  (`test_every_anchor_step_4d_resolves_is_pinned`).
* **D5: (C) is scoped to the SENTENCE** (§0.2 for why the row is too wide). A citation
  in the NEXT sentence also counts ("X is 132/299. It is pinned by ..."); two sentences
  away does not. The exemption vocabulary is 4e's (`doc_counts.py::_PAST_WORDS`,
  `::_DATE_RE`, imported so it has one home) plus "retracted" and "refuted", matched on
  word boundaries (READ: 4e's `any(w in low for w in _PAST_WORDS)` matches substrings,
  so "then" matches "strengthened" there). A cited test FILE must exist
  (`claim_rot.py::_cites`); the `::symbol` of an anchored cite is resolved by 4d.
* **D6: what counts as a ratio claim.** `N/M` and `N of M` with N ≤ M. Skipped: N > M
  (`194/41` is a split), ordinal positions (`Phase 0/2`, `rows 46/56`, `tile:1/5`).
  The first run flagged `rows 46/56` (l.315, "rows 46/56, which discharge the guard"),
  which is two row numbers; `ORDINAL_RE` gained `rows?|lines?` for it. That is the only
  false positive the first run produced.
* **D7: (A) not built** — §0.3.
* **D8: tests live in `tests/`, not `formal/conformance/`.** `doc_counts.py` classifies
  every `formal/conformance/` file not in `TOOLING_FILES` as differential, so a tooling
  test there would have been miscounted in FINAL_REVIEW's generated block.

## § 2 What the first run of (C) found (MEASURED 2026-09-27, before any doc edit)

`claim_rot.py --check` on the unedited map flagged eight ratios. One was the
`rows 46/56` false positive (D6). The other seven were genuine uncited, unmarked
validation ratios, and each was fixed by marking it past IN ITS SENTENCE (the edit
script asserted every anchor matched exactly once):

| line (2026-09-27) | ratio | where | fix | provenance of the date written in |
|---|---|---|---|---|
| 366 | `82/82` | `PLeaf` row, the retraction sentence | `RETRACTED (2026-08-16b)` | REASONED from the row's own header, "CORRECTED TWICE — 2026-08-16 and 2026-08-16b" |
| 370 | `50/50` | `keyLeafRewrites` row: "Measured 2026-08-16 … 50/50 schemas, 0 mismatches" | see below | READ: the date was already in the row; only the tense changed |
| 649 | `5 of 21` | §5 state-gate paragraph | `then (2026-07-27)` | REASONED from the paragraph's header, "RE-MEASURED 2026-07-27" |
| 661 | `11 of 13` | the SUPERSEDED 2026-08-05 note | `were then (2026-08-05)` | REASONED from the note's header, "SUPERSEDED 2026-08-05" |
| 957 | `18 of 171` | end of the 2026-07-28 filing | `was assessed (2026-07-29) … went red` | REASONED (below) |
| 1002 | `82/82` | §7 binary-`Expr` bullet | `retracted 2026-08-16b` | REASONED (below) |
| 1005 | `744/744` | same bullet | `when it was run 2026-08-16b` | REASONED (below) |

(Provenance column added 2026-09-28 at the P13 verifier's request: every date inserted
to satisfy 4d3 is inferred from the text around it, none from a log of the run itself.)

**The `50/50` row is a real finding, not a formality.** It is a current-tense validation
claim ("Measured 2026-08-16 … 50/50 schemas, 0 mismatches, 32 with a non-empty leaf rule
set") with no test behind it: READ — no file under `formal/conformance/` or `tests/`
compares `GraphIndex/LeafRules.lean`'s rules against `compile_ruleset`'s (grep for
`leafRewrites|schemaRewritesL|leaf_rules` finds only
`formal/conformance/graphadmission_scope_probes.py`,
`formal/conformance/test_graphadmission_scope_pin.py` and
`formal/conformance/test_leaf_namespace_correspondence.py`,
none of which runs that comparison). It now reads "Reported 2026-08-16 from a one-off
probe that was never made a test, so nothing has re-checked it since". Turning it into a
test is follow-up work, not this row's (UNVERIFIED whether it still holds).

The dates in the `957`, `1002` and `1005` fixes are REASONED from the surrounding text
(the filing says its questions were "answered in the 2026-07-29 verdict"; the §7 bullet
is headed "NEW 2026-08-16b"), not from a log of the runs themselves.

## § 3 Sabotage and mutation evidence (MEASURED 2026-09-27/28, literal output)

### 3.1 The two design sabotages, on the WORKING TREE with the real CLIs

Run by a throwaway script that edited the tracked file in place (anchor asserted to
match exactly once), ran `anchor_check.py` (step 4d) and `claim_rot.py --check`
(4d2/4d3) as subprocesses, restored the original bytes in `finally` and verified the
restore byte-for-byte. `git status` afterwards showed `Leaf.lean` unmodified. S-B is the
design's "(B) edit an anchored symbol's body and confirm the pin moves WHILE the anchor
check stays green"; S-C is "(C) re-insert the 82/82 claim and confirm it fails"; S-C2 is
the discriminating variant (a date, no pastness word). The last block is the control.

```
=== S-B  body of GraphIndex/Leaf.lean::persistedLeaves (.excl arm drops b)
--- formal/conformance/anchor_check.py  rc=0
  CORRESPONDENCE.md anchors: 718 parsed (402 Python >= 250, 316 Lean >= 100), 718 resolved
--- formal/conformance/claim_rot.py --check  rc=1
FAIL: 1 CORRESPONDENCE.md anchor CONTENT-pin discrepancy(ies) against correspondence_anchor_pin.txt:
      GraphIndex/Leaf.lean::persistedLeaves: BODY CHANGED (lean:def	1599149a3ed22dcf -> lean:def	129765dd75206f90); re-read CORRESPONDENCE.md line(s) 366,979
      A symbol a row DESCRIBES changed under an unchanged name. Re-read
      the cited rows; fix any that are now false (or log the drift in
      CORRESPONDENCE.md section 7); THEN regenerate deliberately:
        python formal/conformance/claim_rot.py --generate
  CORRESPONDENCE.md prose numbers: 8 N/M claim(s), 0 uncited and unmarked
=== S-C  re-insert '82/82 derived keys agree' into the PLeaf row
--- formal/conformance/anchor_check.py  rc=0
  CORRESPONDENCE.md anchors: 718 parsed (402 Python >= 250, 316 Lean >= 100), 718 resolved
--- formal/conformance/claim_rot.py --check  rc=1
  CORRESPONDENCE.md anchor content pin: 474/474 bodies match (floor 470)
FAIL: 1 N/M or 'N of M' claim(s) in CORRESPONDENCE.md that neither cite a test / the generated counts block nor are marked as past measurements:
      CORRESPONDENCE.md:366: '82/82' | Validated: 82/82 derived keys agree.
      Fix EITHER way, in the SAME sentence: (a) cite the test that pins
      it (`tests/x.py::test_y`) or point at FINAL_REVIEW.md's generated
      counts block; (b) if it is a past measurement, say so -- a date AND
      a pastness word ('82/82, retracted 2026-08-16b'). Deleting the
      number is always available and is the durable fix.
=== S-C2 same, with a date but no pastness word
--- formal/conformance/anchor_check.py  rc=0
  CORRESPONDENCE.md anchors: 718 parsed (402 Python >= 250, 316 Lean >= 100), 718 resolved
--- formal/conformance/claim_rot.py --check  rc=1
  CORRESPONDENCE.md anchor content pin: 474/474 bodies match (floor 470)
FAIL: 1 N/M or 'N of M' claim(s) in CORRESPONDENCE.md that neither cite a test / the generated counts block nor are marked as past measurements:
      CORRESPONDENCE.md:366: '82/82' | Validated 2026-08-16: 82/82 derived keys agree.
      Fix EITHER way, in the SAME sentence: (a) cite the test that pins
      it (`tests/x.py::test_y`) or point at FINAL_REVIEW.md's generated
      counts block; (b) if it is a past measurement, say so -- a date AND
      a pastness word ('82/82, retracted 2026-08-16b'). Deleting the
      number is always available and is the durable fix.
=== restored; control run on the untouched tree:
--- claim_rot.py --check  rc=0
  CORRESPONDENCE.md anchor content pin: 474/474 bodies match (floor 470)
  CORRESPONDENCE.md prose numbers: 8 N/M claim(s), 0 uncited and unmarked
```

Both sabotages are ALSO permanent tests (they edit a copy under `tmp_path`, never the
tree): `tests/test_claim_rot_gate.py::test_B_lean_body_edit_moves_the_pin_while_step_4d_stays_green`,
`::test_C_reinserted_82_of_82_claim_is_refused`,
`::test_C_a_date_without_a_pastness_word_is_still_refused`.

### 3.2 An instrument defect the tests caught in themselves

The first version of the test harness wrote every patched copy of a file to the same
`tmp_path/<name>`, and the parse cache is keyed by path. So in a test that patched
`Equiv.lean` twice (proof edit, then statement edit) the second patch was served the
FIRST patch's parse, and the theorem-STATEMENT edit read as unchanged: a false green
(`assert (0 == 1)` in `test_B_theorem_pins_the_statement_not_the_proof`). The class test
failed the mirror way. Fixed by a fresh directory per patch
(`tests/test_claim_rot_gate.py::_patch_file`, comment dated 2026-09-27).

### 3.3 Mutation sweep over `formal/conformance/claim_rot.py`, with an M0 control

A throwaway runner applied one anchored replacement per mutant (asserted to match
exactly once, so a no-op mutant cannot read as killed), ran BOTH
`pytest tests/test_claim_rot_gate.py` and the live `claim_rot.py --check`, and restored
the file in `finally`, byte-verified after each. No outer timeout.

**Sweep 3 (2026-09-28, the FINAL module and the FINAL test module)** — `claim_rot.py`
unchanged since sweep 2; the test module gained the three M19-killing shapes. The
`red:` lines are shown for M19 only (the full log had them for every kill):

```
# mutation sweep over formal\conformance\claim_rot.py (23 runs incl. M0)
M0   control  pytest rc=0 [26 passed in 7.31s]  cli rc=0  | control: no mutation
M1   KILLED   pytest rc=1 [9 failed, 17 passed in 11.88s]  cli rc=0  | N/N ratios ignored (n > d -> n >= d)
M2   KILLED   pytest rc=1 [5 failed, 21 passed in 16.43s]  cli rc=0  | sentence scope -> block scope (never split)
M3   KILLED   pytest rc=1 [1 failed, 25 passed in 12.68s]  cli rc=0  | citation in the NEXT sentence no longer counts
M4   KILLED   pytest rc=1 [1 failed, 25 passed in 11.46s]  cli rc=0  | a date alone exempts (pastness word dropped)
M5   KILLED   pytest rc=1 [1 failed, 25 passed in 14.73s]  cli rc=0  | a pastness word alone exempts (date dropped)
M6   KILLED   pytest rc=1 [8 failed, 18 passed in 13.30s]  cli rc=1  | function docstring kept in the hash
M7a  KILLED   pytest rc=1 [8 failed, 18 passed in 16.23s]  cli rc=1  | class shell includes method bodies
M7b  KILLED   pytest rc=1 [8 failed, 18 passed in 12.31s]  cli rc=1  | class shell drops fields too (always Pass)
M8   KILLED   pytest rc=1 [8 failed, 18 passed in 14.08s]  cli rc=1  | Lean def pinned at its SIGNATURE line only
M9   KILLED   pytest rc=1 [8 failed, 18 passed in 14.90s]  cli rc=1  | Lean theorem pinned with its PROOF
M10  KILLED   pytest rc=1 [8 failed, 18 passed in 13.07s]  cli rc=1  | Lean comments not stripped
M11  KILLED   pytest rc=1 [4 failed, 22 passed in 17.21s]  cli rc=0  | BODY CHANGED comparison disabled
M12  KILLED   pytest rc=1 [1 failed, 25 passed in 14.19s]  cli rc=0  | unpinned-anchor report disabled
M13  KILLED   pytest rc=1 [2 failed, 24 passed in 15.99s]  cli rc=0  | golden floor disabled
M14  KILLED   pytest rc=1 [10 failed, 16 passed in 12.41s]  cli rc=1  | field/constructor -> parent fallback removed
M15  KILLED   pytest rc=1 [11 failed, 15 passed in 13.68s]  cli rc=1  | ordinal enumerations no longer skipped
M16  KILLED   pytest rc=1 [8 failed, 18 passed in 12.54s]  cli rc=1  | hash truncated to nothing
M17  KILLED   pytest rc=1 [1 failed, 25 passed in 14.33s]  cli rc=0  | unpinnable anchors silently dropped
M18  KILLED   pytest rc=1 [1 failed, 25 passed in 13.66s]  cli rc=0  | removed-row report disabled
M19  KILLED   pytest rc=1 [3 failed, 23 passed in 16.25s]  cli rc=0  | table rows no longer their own block
       red: test_C_a_table_row_cannot_borrow_its_neighbours_citation[paragraph-then-row]
       red: test_C_a_table_row_cannot_borrow_its_neighbours_citation[row-then-paragraph]
       red: test_C_a_table_row_cannot_borrow_its_neighbours_citation[row-without-trailing-pipe]
M20  KILLED   pytest rc=1 [1 failed, 25 passed in 14.02s]  cli rc=0  | ':' no longer excluded before N/M (tile:1/5 counts)
M21  KILLED   pytest rc=1 [1 failed, 25 passed in 16.71s]  cli rc=0  | a cited test file need not exist
# restored; claim_rot.py byte-identical to the pre-sweep file
```

**M0 green; all 22 mutants KILLED.** M19's kill is exactly the three shapes the probe
predicted, and NOT the `row-row` case — the discriminating half of the prediction.

Sweep 2 (2026-09-27, same `claim_rot.py`, the 23-test module) is kept below because it
is the record of the survivor. Sweep 1 ran over the module before `_cites` existed and
gave the same verdicts for M0 to M20, M19 included.

```
# mutation sweep over formal\conformance\claim_rot.py (23 runs incl. M0)
M0   control  pytest rc=0 [23 passed in 23.04s]  cli rc=0  | control: no mutation
M1   KILLED   pytest rc=1 [6 failed, 17 passed in 31.22s]  cli rc=0  | N/N ratios ignored (n > d -> n >= d)
M2   KILLED   pytest rc=1 [5 failed, 18 passed in 23.60s]  cli rc=0  | sentence scope -> block scope (never split)
M3   KILLED   pytest rc=1 [1 failed, 22 passed in 27.94s]  cli rc=0  | citation in the NEXT sentence no longer counts
M4   KILLED   pytest rc=1 [1 failed, 22 passed in 21.70s]  cli rc=0  | a date alone exempts (pastness word dropped)
M5   KILLED   pytest rc=1 [1 failed, 22 passed in 26.40s]  cli rc=0  | a pastness word alone exempts (date dropped)
M6   KILLED   pytest rc=1 [8 failed, 15 passed in 20.26s]  cli rc=1  | function docstring kept in the hash
M7a  KILLED   pytest rc=1 [8 failed, 15 passed in 20.90s]  cli rc=1  | class shell includes method bodies
M7b  KILLED   pytest rc=1 [8 failed, 15 passed in 19.11s]  cli rc=1  | class shell drops fields too (always Pass)
M8   KILLED   pytest rc=1 [8 failed, 15 passed in 22.03s]  cli rc=1  | Lean def pinned at its SIGNATURE line only
M9   KILLED   pytest rc=1 [8 failed, 15 passed in 20.77s]  cli rc=1  | Lean theorem pinned with its PROOF
M10  KILLED   pytest rc=1 [8 failed, 15 passed in 20.64s]  cli rc=1  | Lean comments not stripped
M11  KILLED   pytest rc=1 [4 failed, 19 passed in 22.29s]  cli rc=0  | BODY CHANGED comparison disabled
M12  KILLED   pytest rc=1 [1 failed, 22 passed in 24.26s]  cli rc=0  | unpinned-anchor report disabled
M13  KILLED   pytest rc=1 [2 failed, 21 passed in 23.61s]  cli rc=0  | golden floor disabled
M14  KILLED   pytest rc=1 [10 failed, 13 passed in 19.37s]  cli rc=1  | field/constructor -> parent fallback removed
M15  KILLED   pytest rc=1 [11 failed, 12 passed in 23.06s]  cli rc=1  | ordinal enumerations no longer skipped
M16  KILLED   pytest rc=1 [8 failed, 15 passed in 21.54s]  cli rc=1  | hash truncated to nothing
M17  KILLED   pytest rc=1 [1 failed, 22 passed in 27.33s]  cli rc=0  | unpinnable anchors silently dropped
M18  KILLED   pytest rc=1 [1 failed, 22 passed in 17.80s]  cli rc=0  | removed-row report disabled
M19  SURVIVED pytest rc=0 [23 passed in 17.60s]  cli rc=0  | table rows no longer their own block
M20  KILLED   pytest rc=1 [1 failed, 22 passed in 17.91s]  cli rc=0  | ':' no longer excluded before N/M (tile:1/5 counts)
M21  KILLED   pytest rc=1 [1 failed, 22 passed in 16.03s]  cli rc=0  | a cited test file need not exist
# restored; claim_rot.py byte-identical to the pre-sweep file
```

Sweep 2: M0 green; of the 22 mutants, 21 KILLED and 1 SURVIVED (M19). As first
written, this section called M19 EQUIVALENT because `SENT_END_RE` also splits at every
`|`. **That was wrong** (correction at the top): the `|` split only separates two FULL
rows, and M19 is killed by sweep 3 above.

What the kills are made of, so they are not over-read: the mutants that change EVERY
hash (M6, M7a, M7b, M8, M9, M10, M14, M16) are killed first by the live golden
mismatch (`cli rc=1`), not only by the targeted test. REASONED for the design's key
case M8 (pin the signature line only): the targeted test would catch it even against a
golden regenerated under the mutant, because the edited `.excl` line is not the
signature line.

### 3.4 The verifier's findings, re-run after the 2026-09-28b fix (MEASURED, literal)

**Live-CLI sabotage** on the real `CORRESPONDENCE.md` (CRLF), each sentence appended to
the `PLeaf` row, `claim_rot.py --check` run as a subprocess, file restored and
sha256-checked after (script: the verifier's `sab_cli.py`, extended). Before the fix,
the verifier measured `around 80/82`, `baseline 82/82` and `1,227/1,227` at rc=0:

```
CRLF in file: True
rc=0 <- M0 control (untouched) :: ['CORRESPONDENCE.md prose numbers: 8 N/M claim(s), 0 uncited and unmarked']
rc=1 <- Validated: 82/82 derived keys agree. :: ["CORRESPONDENCE.md:366: '82/82' | Validated: 82/82 derived keys agree."]
rc=1 <- Validated: around 80/82 derived keys agree. :: ["CORRESPONDENCE.md:366: '80/82' | Validated: around 80/82 derived keys agree."]
rc=1 <- Validated against the baseline 82/82 derived keys. :: ["CORRESPONDENCE.md:366: '82/82' | Validated against the baseline 82/82 derived keys."]
rc=1 <- Validated: 1,227/1,227 derived keys agree. :: ["CORRESPONDENCE.md:366: '1,227/1,227' | Validated: 1,227/1,227 derived keys agree."]
rc=1 <- The pipeline 82/82 derived keys agree. :: ["CORRESPONDENCE.md:366: '82/82' | The pipeline 82/82 derived keys agree."]
rc=1 <- Validated: 82 / 82 derived keys agree. :: ["CORRESPONDENCE.md:366: '82 / 82' | Validated: 82 / 82 derived keys agree."]
rc=1 <- Validated: 82/82 derived keys agree (see doc_counts for suite size). :: ["CORRESPONDENCE.md:366: '82/82' | Validated: 82/82 derived keys agree (see doc_counts for suite size)."]
rc=0 <- It is 82/82, retracted 2026-08-16b. :: ['CORRESPONDENCE.md prose numbers: 9 N/M claim(s), 0 uncited and unmarked']
restored byte-identical
```

The last line is the model form the CLI's own fix advice prints, and it passes.

**Mutation sweep 4** (2026-09-28, final module and final tests; 42 tests collected).
M1..M21 are sweep 3's mutants (M15 re-anchored to `claim_rot.py::_ordinal`), K1..K7
are the verifier's (`K1`/`K2`/`K3`/`K4`/`K7` SURVIVED its sweep with 26 tests), N1..N8
target this fix, and OLD swaps in the whole 76c471e module, which is the direct
proof that the new tests are red on the code the verifier reviewed. Every anchor was
asserted to match exactly once; `claim_rot.py` sha256 was
`7ff03dae…3152` before and after. Red test names are shown for K/N/OLD only (M1..M21's
lists are as in sweep 3, plus the new tests):

```
# mutation sweep 4 over formal/conformance/claim_rot.py (39 runs incl. M0)
M0   control  pytest rc=0 [42 passed in 13.68s]  cli rc=0  | control: no mutation
M1   KILLED   pytest rc=1 [18 failed, 24 passed in 15.41s]  cli rc=0  | N/N ratios ignored (n > d -> n >= d)
M2   KILLED   pytest rc=1 [16 failed, 26 passed in 15.57s]  cli rc=0  | sentence scope -> block scope (never split)
M3   KILLED   pytest rc=1 [1 failed, 41 passed in 14.33s]  cli rc=0  | citation in the NEXT sentence no longer counts
M4   KILLED   pytest rc=1 [1 failed, 41 passed in 13.83s]  cli rc=0  | a date alone exempts (pastness word dropped)
M5   KILLED   pytest rc=1 [1 failed, 41 passed in 15.42s]  cli rc=0  | a pastness word alone exempts (date dropped)
M6   KILLED   pytest rc=1 [8 failed, 34 passed in 13.95s]  cli rc=1  | function docstring kept in the hash
M7a  KILLED   pytest rc=1 [8 failed, 34 passed in 16.57s]  cli rc=1  | class shell includes method bodies
M7b  KILLED   pytest rc=1 [8 failed, 34 passed in 14.61s]  cli rc=1  | class shell drops fields too (always Pass)
M8   KILLED   pytest rc=1 [8 failed, 34 passed in 13.78s]  cli rc=1  | Lean def pinned at its SIGNATURE line only
M9   KILLED   pytest rc=1 [8 failed, 34 passed in 13.02s]  cli rc=1  | Lean theorem pinned with its PROOF
M10  KILLED   pytest rc=1 [8 failed, 34 passed in 11.54s]  cli rc=1  | Lean comments not stripped
M11  KILLED   pytest rc=1 [4 failed, 38 passed in 15.75s]  cli rc=0  | BODY CHANGED comparison disabled
M12  KILLED   pytest rc=1 [1 failed, 41 passed in 14.45s]  cli rc=0  | unpinned-anchor report disabled
M13  KILLED   pytest rc=1 [2 failed, 40 passed in 15.46s]  cli rc=0  | golden floor disabled
M14  KILLED   pytest rc=1 [10 failed, 32 passed in 13.66s]  cli rc=1  | field/constructor -> parent fallback removed
M15  KILLED   pytest rc=1 [24 failed, 18 passed in 16.42s]  cli rc=1  | ordinal enumerations no longer skipped
M16  KILLED   pytest rc=1 [8 failed, 34 passed in 12.68s]  cli rc=1  | hash truncated to nothing
M17  KILLED   pytest rc=1 [1 failed, 41 passed in 13.42s]  cli rc=0  | unpinnable anchors silently dropped
M18  KILLED   pytest rc=1 [1 failed, 41 passed in 12.84s]  cli rc=0  | removed-row report disabled
M19  KILLED   pytest rc=1 [3 failed, 39 passed in 12.75s]  cli rc=0  | table rows no longer their own block
M20  KILLED   pytest rc=1 [1 failed, 41 passed in 13.60s]  cli rc=0  | ':' no longer excluded before N/M (tile:1/5 counts)
M21  KILLED   pytest rc=1 [1 failed, 41 passed in 12.99s]  cli rc=0  | a cited test file need not exist
K1   KILLED   pytest rc=1 [1 failed, 41 passed in 16.84s]  cli rc=0  | ';' no longer ends a sentence
       red: test_C_a_semicolon_ends_the_sentence
K2   KILLED   pytest rc=1 [1 failed, 41 passed in 15.82s]  cli rc=0  | 'N out of M' form dropped
       red: test_C_out_of_form_is_a_claim
K3   KILLED   pytest rc=1 [2 failed, 40 passed in 14.26s]  cli rc=0  | 'retracted'/'refuted' past words dropped
       red: test_C_retracted_and_refuted_are_pastness_words[refuted]
       red: test_C_retracted_and_refuted_are_pastness_words[retracted]
K4   KILLED   pytest rc=1 [1 failed, 41 passed in 13.55s]  cli rc=0  | only the FIRST binding of a multiply-bound Python name is hashed
       red: test_B_every_binding_of_a_python_name_is_hashed
K5   KILLED   pytest rc=1 [8 failed, 34 passed in 10.72s]  cli rc=1  | Lean def body stops at the first blank line
       red: test_B_a_gutted_golden_is_refused
       red: test_B_a_removed_row_and_an_unpinnable_anchor_are_reported
       red: test_B_class_is_pinned_at_its_shell
       red: test_B_comment_and_docstring_edits_do_not_move_the_pin
       red: test_B_lean_body_edit_moves_the_pin_while_step_4d_stays_green
       red: test_B_python_body_edit_moves_the_pin
       red: test_B_theorem_pins_the_statement_not_the_proof
       red: test_live_map_is_clean_under_both_checks
K6   KILLED   pytest rc=1 [8 failed, 34 passed in 12.15s]  cli rc=1  | Lean def body stops after the signature's next line
       red: test_B_a_gutted_golden_is_refused
       red: test_B_a_removed_row_and_an_unpinnable_anchor_are_reported
       red: test_B_class_is_pinned_at_its_shell
       red: test_B_comment_and_docstring_edits_do_not_move_the_pin
       red: test_B_lean_body_edit_moves_the_pin_while_step_4d_stays_green
       red: test_B_python_body_edit_moves_the_pin
       red: test_B_theorem_pins_the_statement_not_the_proof
       red: test_live_map_is_clean_under_both_checks
K7   KILLED   pytest rc=1 [1 failed, 41 passed in 13.37s]  cli rc=0  | cell bar no longer ends a sentence
       red: test_C_a_table_cell_ends_the_sentence
N1   KILLED   pytest rc=1 [4 failed, 38 passed in 13.55s]  cli rc=0  | ORDINAL_RE loses its leading \b (around/baseline skipped)
       red: test_C_verifier_green_sabotages_are_refused[around-contains-round]
       red: test_C_verifier_green_sabotages_are_refused[baseline-contains-line]
       red: test_C_verifier_green_sabotages_are_refused[pipeline-contains-line]
       red: test_C_verifier_green_sabotages_are_refused[window-starts-mid-word]
N2   KILLED   pytest rc=1 [3 failed, 39 passed in 14.69s]  cli rc=0  | numbers back to \d+ (1,227/1,227 read as 227/1)
       red: test_C_verifier_green_sabotages_are_refused[thousands-denominator]
       red: test_C_verifier_green_sabotages_are_refused[thousands-of]
       red: test_C_verifier_green_sabotages_are_refused[thousands-slash]
N3   KILLED   pytest rc=1 [1 failed, 41 passed in 15.65s]  cli rc=0  | spaced slash no longer matched
       red: test_C_verifier_green_sabotages_are_refused[spaced-slash]
N4   KILLED   pytest rc=1 [1 failed, 41 passed in 14.83s]  cli rc=0  | spaced chain: left-link exclusion dropped
       red: test_C_ordinal_words_and_chains_are_still_not_claims
N5   KILLED   pytest rc=1 [1 failed, 41 passed in 12.63s]  cli rc=0  | spaced chain: right-link exclusion dropped
       red: test_C_ordinal_words_and_chains_are_still_not_claims
N6   KILLED   pytest rc=1 [1 failed, 41 passed in 14.29s]  cli rc=0  | GEN_RE back to the bare words
       red: test_C_verifier_green_sabotages_are_refused[bare-doc_counts-word]
N7   KILLED   pytest rc=1 [1 failed, 41 passed in 13.05s]  cli rc=0  | ordinal window searched in a SLICE (\b fires at the slice edge)
       red: test_C_verifier_green_sabotages_are_refused[window-starts-mid-word]
N8   KILLED   pytest rc=1 [1 failed, 41 passed in 11.57s]  cli rc=0  | comma-grouped number read as its first group
       red: test_C_verifier_green_sabotages_are_refused[thousands-denominator]
OLD  KILLED   pytest rc=1 [8 failed, 34 passed in 12.22s]  cli rc=0  | the whole 76c471e module (pre-fix)
       red: test_C_verifier_green_sabotages_are_refused[around-contains-round]
       red: test_C_verifier_green_sabotages_are_refused[bare-doc_counts-word]
       red: test_C_verifier_green_sabotages_are_refused[baseline-contains-line]
       red: test_C_verifier_green_sabotages_are_refused[pipeline-contains-line]
       red: test_C_verifier_green_sabotages_are_refused[spaced-slash]
       red: test_C_verifier_green_sabotages_are_refused[thousands-denominator]
       red: test_C_verifier_green_sabotages_are_refused[thousands-of]
       red: test_C_verifier_green_sabotages_are_refused[thousands-slash]
# restored; claim_rot.py byte-identical to the pre-sweep file
```

38 of 38 mutants KILLED against a green M0. Not mutated, and so unproven by this sweep:
`ORDINAL_WINDOW`'s value (24; shrinking it only flags more), and `OF_RE`'s lookbehind.

**Verifier nits, adjudicated.** Fixed: the nonexistent `tests/test_matrix.py::test_matrix`
fixture cite (now `::test_matrix_4way_boolean`, which grep finds); `GEN_RE`'s looseness
(now refused, not merely documented); the `::file.py` cites in §2; the unlabelled
inserted dates (§2's provenance column); the Lean whitespace-normalisation hole and the
`rows 82/82` / `all 82 of the 82` forms (now honest limits in the module docstring).
K4's docstring promise is pinned by a synthetic property-plus-setter test rather than
softened.

## § 4 State at hand-off (2026-09-28)

* LANDED in the worktree commit (see `task.py show P13`): §1's files.
* GREEN, MEASURED here: `claim_rot.py --check` rc=0 (474/474, 8 ratios, 0 uncited and
  unmarked); `anchor_check.py` 718/718; `tests/test_claim_rot_gate.py` 26 passed
  (2026-09-28; 42 passed after the 2026-09-28b fix, §3.4);
  `handoff_lint.py` clean; `task.py lint` clean; 4e's corpus-count prose scan
  (`doc_counts.py::check_corpus_count_prose`) returns no complaints. The `tests-tile`
  results are in the commit message.
* NOT RUN here, by construction: the `lean` phase and the `conf-tile` phases (a worktree
  has no `.lake`). The orchestrator runs them on the main tree after merge.
  FINAL_REVIEW.md's generated counts block will be STALE after merge (the `tests/`
  collected count grew by this module's tests) and must be regenerated there
  (`python -m formal.conformance.doc_counts --generate`); until then step 4e is red.
* OPEN follow-ups, not this row's: turn the `50/50` leaf-rule probe (§2) into a test,
  or delete the number; (A) stays unbuilt unless a defect it would catch is recorded.
