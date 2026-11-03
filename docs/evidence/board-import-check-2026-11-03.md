# Board import: the conservation check (2026-11-03)

FROZEN 2026-11-03 (session 2026-11-03a): the check the context-engine CE-167 import script ran on the
converted tree; never edited. `check_board.py` (kept with the script, sha256 below) shares no code with
the converter: it reads the task.py corpus from git with task.py's own grammar and each record with the
engine's parser, and needs every body byte-equal, every frontmatter value equal and nothing lost or invented.

```text
legacy records at 4826a01: 303; new records in tasks/: 303
legacy records with no single new record: 0
new records with no legacy source: 0
bodies byte-equal: 303 of 303; body lines 15638 legacy, 15638 new
frontmatter values differing: 0; states wrong: 0; kinds wrong: 0
PASS
```

Sabotaged before it was believed, each on a copy of the converted tasks/, each FAIL: body byte, record dropped, field changed, record invented, alias dropped.

check_board.py sha256 6cbe45a6964b5c73ada1dfda4a7459f5931c14faf56bd77813d9b9e83559af64; ce167_import.py sha256 a11f78beeb9a098ab889e18c59544e03a4d88f7af1717ded5cadaeede526ddfc.
