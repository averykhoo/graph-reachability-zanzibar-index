"""Sphinx extension: render the product's ``REFUSED SHAPE`` comment blocks as a reference page.

The product package (``src/zanzibar/``) puts a comment block directly above every refusal::

    # REFUSED SHAPE (<origin id>): <what is refused>.
    # WHY: <why>.
    # INSTEAD: <a rewrite that parses>   -- or --   # INSTEAD: none -- <reason>.

The ``refused-shapes`` directive reads those blocks from EVERY ``*.py`` file under
``src/zanzibar/`` at build time (``SRC_ROOT``, ``source_files``) and renders one section per
block (what / why / instead / raises), grouped by where the refusal happens (``STAGES``:
schema text, JSON models, ``object_wildcard_shapes``, graph-index compilation, set engine,
store, graph-index maintenance), so the user page cannot drift from the code. In a MyST
page::

    ```{refused-shapes}
    ```

The directive takes no argument. The test suite's reference oracle (``tests/oracle.py``)
is outside ``src/zanzibar/`` and is never scanned. Each rendered entry is a section with the
class ``refused-shape``; ``tests/test_userdocs_refused_shapes.py`` counts them against an
independent grep of the source tree.

The comments are written for maintainers, so the rendered text is cleaned mechanically:

* the origin id in the header line is dropped;
* a parenthetical that cites an internal id, a source path or a ``file::symbol`` is dropped;
* ``PHRASES`` reword the few maintainer phrases that remain;
* a back-reference (``WHY: see above``, ``WHY: the comment above``) is resolved to the text
  it points at: the previous block's field in the same function, or the comment lines
  directly above the header;
* a block whose text cannot be cleaned that way gets an ``OVERRIDES`` entry, pinned to a
  fingerprint of its source block.

Then a leak check runs over everything rendered. The build FAILS (``ExtensionError``) when:

* no block is found in the whole package (the scan broke, or the convention was renamed);
* a source file cannot be read or decoded, or does not parse as Python;
* a file has a line naming ``REFUSED SHAPE`` that the scan did not turn into a block (for
  example the header moved into a docstring), so the per-file count disagrees;
* a block's file / function has no place in ``STAGES`` (a new refusal site must be given
  a section deliberately);
* a block's exception is not exported by ``zanzibar`` (``_EXCEPTION_HOMES``), so the
  "Raises:" link could not resolve;
* a block has no WHY or no INSTEAD after resolution;
* rendered text still contains an internal id, a source path, a private name or a
  proof/test-suite term (``LEAKS``);
* an ``OVERRIDES`` entry's fingerprint no longer matches its source block (the comment was
  edited, so the hand-written text must be reviewed), or the entry names no block;
* a ``PHRASES`` rule matches nothing (it is stale);
* rendered prose still holds an all-capitals word not in ``CAPS_ALLOWED`` (maintainer
  emphasis such as STORED is lowercased through ``EMPHASIS``), or an ``EMPHASIS`` word
  occurs nowhere (stale);
* a block has no ``raise`` within ``RAISE_WINDOW`` lines below it. The first ``raise``
  names the exception (a bare ``raise`` names the nearest ``except`` above the block), and
  every entry gets a "Raises:" line linking it; for ``ShapeNoLongerAccepted`` the line also
  quotes the raise site's ``accepted_through`` (default ``'0.0.4'``, as in the class).

So editing a refusal comment anywhere in the package can turn the docs build red. The error
names the block and what to do; the fix goes in this file or in the comment, never in the
page. OVERRIDES / STAGES keys name the file relative to ``src/zanzibar/``
(``schema/parser.py``).

Multi-file sabotage (2026-10-20, round 2): see the docstring of
``tests/test_userdocs_refused_shapes.py`` for the literal red output.

The single-file sabotage below predates the multi-file scan (round 1, parser.py only).

Sabotage (2026-10-20, a scratch Sphinx project holding this file and a COPY of parser.py,
each mutation applied alone to the copy, anchor asserted to occur once; the real parser
was never edited). Baseline rc=0; each line below is the literal observed result:

* S1, every ``REFUSED SHAPE`` renamed (23 replaced): rc=2, "refused-shapes: found no
  '# REFUSED SHAPE' comment block in src/zanzibar/schema/parser.py".
* S2, an INSTEAD reworded to cite ``TK<999>`` (angle brackets added in this note only: tests/test_tasktool.py refuses an unfiled task id outside tasks/) and ``_private_helper``: rc=2, "rendered text
  contains an internal task id 'TK<999>'" and "... a private name '_private_helper'".
* S3, the header of an overridden block edited: rc=2, "this comment changed after its
  OVERRIDES entry was written (source fingerprint f3855e35a495, entry 9ef15783ed57)".
* S4, an ``INSTEAD:`` label renamed: rc=2, "(_parse_chain, block 0): no INSTEAD after
  resolving back-references".
* S5, the text a PHRASES rule rewrites reworded: rc=2, "PHRASES rule 'the assignment below
  would silently replace the first definition' matched nothing ... it is stale".
* Restored: rc=0, copy byte-identical to the real parser (``cmp``).

Sabotage of the emphasis / raises checks (2026-10-20, fix pass; the module's lists
patched in memory and ``resolve(extract(parser.py))`` run, each alone; literal output):

* baseline: no error, 4 entries carry "Raises: ShapeNoLongerAccepted".
* X1, ``STORED`` removed from EMPHASIS: "parser.py:665 (_validate_ast_consistency, block
  4): rendered prose shouts 'STORED' in 'None for a pure alias loop ..."
* X2, ``FROBNICATED`` added to EMPHASIS: "EMPHASIS word 'FROBNICATED' occurs nowhere in
  parser.py; it is stale, so delete it."
* X3, RAISE_WINDOW = 1: 21 errors, first "parser.py:204 (_reject_conditional_restriction,
  block 0): no ``raise`` within 1 lines below the block ...".
* X4, ``JSON`` removed from CAPS_ALLOWED: "parser.py:226 (_validate_header_line, block 0):
  rendered prose shouts 'JSON' in ...".
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from docutils import nodes
from sphinx import addnodes
from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective

REPO = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO / "src" / "zanzibar"
HEADER = "REFUSED SHAPE"
_PARSER = "schema/parser.py"


def source_files(root: Path = SRC_ROOT) -> list[Path]:
    """Every product module scanned for refusals, in a stable order."""
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)

# --------------------------------------------------------------------------------------
# Cleaning rules
# --------------------------------------------------------------------------------------

#: Text that must never reach a user page.
LEAKS = [
    (re.compile(r"\b(?:TK|ZT-P|ASK-|P)\d+"), "an internal task id"),
    (re.compile(r"blind-audit|decision-15|install trial|review challenge|[Rr]eviewer probe"),
     "an internal audit reference"),
    (re.compile(r"spec §|§\s*\d"), "an internal spec section"),
    (re.compile(r"\.py\b|\.g4\b|\.go\b|::|\b(?:docs|tests|formal|src)/"),
     "a source path or file::symbol"),
    (re.compile(r"(?<![\w.])_[a-z]\w*"), "a private name"),
    (re.compile(r"\b(?:Lean|theorem|oracle|genswarm|W4Fragment|GraphAdmission|TTU|AST)\b"),
     "a proof, test-suite or compiler-internal term"),
]

#: A parenthetical containing one of these is dropped whole.
_INTERNAL_PAREN = re.compile(
    r"\b(?:TK|ZT-P|ASK-|P)\d+|blind-audit|decision-15|\.py\b|\.g4\b|\.go\b|::"
    r"|\b(?:docs|tests|formal)/|`_[a-z]|spec §|install trial")

#: Ordered (old, new) rewordings applied to every rendered text segment. Each must match at
#: least once in the scanned file, or the build fails as stale.
PHRASES: list[tuple[str, str]] = [
    ("until TK137 ``but not`` bound loosest",
     "before version 0.0.5, ``but not`` bound loosest"),
    ("TTU-tupleset references", "``from``-tupleset references"),
    ("a TTU target declared on none of the tupleset's types",
     "a ``from`` target declared on none of the tupleset's types"),
    ("spell the userset reading as its own TTU", "spell the userset reading as its own ``from``"),
    ("Lexical collision lock", ""),
    ("'.' is reserved for synthetic leaf predicates ('<relation>.<index>')",
     "``.`` is reserved for the names the compiler gives its internal relations "
     "(``<relation>.<index>``)"),
    ("``.``-names are the compiler's leaf predicates",
     "names containing ``.`` belong to the compiler's internal relations"),
    ("the assignment below would silently replace the first definition",
     "the second definition would silently replace the first"),
    ("a dangling reference silently meant \"empty\" and a computed cycle was answered by a "
     "fixpoint; no headline theorem covers either, and OpenFGA refuses both",
     "a reference to an undeclared relation used to mean \"nobody\" without a word, so a "
     "typo silently denied access, and a cycle of references was answered with whatever "
     "the evaluation happened to settle on. OpenFGA refuses both"),
    ("The set engine and the oracle answered that way while the graph refused the schema "
     "at compile time", "The set engine answered that way while the graph index refused "
     "the schema"),
    ("The set engine and the oracle used to answer anyway, identically, because both seed "
     "in-progress recursion with False; their answers were not models of the schema.",
     "The set engine used to answer anyway, and its answers did not satisfy the schema."),
    ("The graph refused it at compile", "The graph index refused it at compile time"),
    ("a ``but not`` subtrahend", "the right-hand side of a ``but not``"),
]

#: Hand-written text for blocks whose source wording is maintainer-only (internal history,
#: or a pointer to a docstring). Keyed by (function, ordinal of the block in that function,
#: 0-based), within one file; ``OVERRIDES`` below prefixes the file. Each value maps a field
#: ("what", "why", "instead") to a list of segments: a ``str`` is prose, a ``list`` of
#: ``str`` is a code block. ``fingerprint`` is ``fingerprint(block)`` of the source block the
#: text was written against.
_PARSER_OVERRIDES: dict[tuple[str, int], dict] = {
    ("_reject_unsupported_openfga_line", 0): {
        "fingerprint": "a5799d341a31",
        "what": ["OpenFGA modules, ``extend type`` and ``condition`` blocks -- "
                 "``module core``, ``extend type doc``, "
                 "``condition in_office(ip: ipaddress) {``."],
    },
    ("_validate_declared_name", 0): {
        "fingerprint": "0107d07bf56f",
        "why": ["Every write is held to the identifier charset, so no tuple can ever be "
                "written on such a name, yet a computed reference or a ``from`` can still "
                "reach it. With ``define *: viewer but not blocked``, a valid write on "
                "``viewer`` would be refused, and an index maintained asynchronously would "
                "stall."],
    },
    ("_parse_schema_ast_declared", 1): {
        "fingerprint": "cd15e7799483",
        "why": ["No tuple can be written on an empty name, yet a computed reference to it "
                "(``define : viewer``) would still be reached through a valid write on "
                "``viewer``, and there the two evaluation backends would give different "
                "answers."],
    },
    ("_validate_declares_a_type", 0): {
        "fingerprint": "9ef15783ed57",
        "why": ["``Store(session, \"x\", schema=\"\")`` would save the empty schema as "
                "the store's permanent schema. Every later write would be refused, reopening "
                "the store with the intended schema would raise ``SchemaMismatch``, and a "
                "store cannot be dropped, so the store id would be lost. An empty schema "
                "file read from disk is the usual way to get here."],
        "instead": ["Declare the types and their relations, for example:",
                    ["model", "  schema 1.1", "type user", "type doc", "  relations",
                     "    define viewer: [user]"]],
    },
    ("_validate_declares_a_type", 1): {
        "fingerprint": "df2614072f9f",
        "why": ["It is the same empty schema as ``\"\"`` and would lose a store id the same "
                "way: saved permanently, every write refused, and reopening with the "
                "intended schema raising ``SchemaMismatch``."],
        "instead": ["Declare the relations, for example:",
                    ["type user", "type doc", "  relations", "    define viewer: [user]"]],
    },
    # The source example omits that ``parent`` links a doc to a doc; with
    # ``parent: [folder]`` the same define parses, so the page spells the link out.
    ("_validate_stratified_negation", 0): {
        "fingerprint": "1403c92dd213",
        "what": ["A relation that depends on itself through the right-hand side of a "
                 "``but not`` -- ``define viewer: [user] but not viewer from parent`` where "
                 "``define parent: [doc]`` links a doc to another doc, or "
                 "``member: [user] but not blocked`` with ``blocked: [group#member]`` on "
                 "type ``group``."],
        "why": ["Such a schema has no consistent answer on some data (``doc:a parent doc:a`` "
                "makes ``viewer = not viewer``) and several on other data, so there is no "
                "single answer for the two evaluation backends to agree on."],
    },
    ("_validate_tuplesets_direct", 0): {
        "fingerprint": "71e21d9a7187",
        "what": ["A tupleset with computed, ``from``, ``and`` or ``but not`` arms -- "
                 "``parent: [folder] or other``, ``parent: [folder] but not blocked`` under "
                 "``viewer from parent``."],
        "why": ["``from`` follows the tuples stored on the tupleset relation, never its "
                "computed members, so any other arm on that relation would be ignored "
                "without a word by every ``from`` that uses it. OpenFGA refuses the shape "
                "too: a relation "
                "used as a tupleset must be a direct relation. Allowed are ``[folder]``, "
                "``[folder, doc]`` and ``[folder] or [doc]``."],
        "instead": ["Store the links on a relation made only of type restrictions, listing "
                    "every type the old relation named, and use that one in the ``from``:",
                    ["define parent_link: [folder]",
                     "define viewer: viewer from parent_link"]],
    },
    # ---- Present-tense reasons (the source comments carry change history, which belongs
    # on the changelog page, not in reference).
    ("_reject_unparenthesised_but_not", 0): {
        "fingerprint": "2a4bd42d1ba2",
        "why": ["Without parentheses the shape has two readings that grant different "
                "subjects: ``a but not b or c`` reads as ``(a but not b) or c``, but can "
                "also mean ``a but not (b or c)``, and only the first admits the members of "
                "``c``. OpenFGA's grammar refuses the shape too. A store whose saved schema "
                "uses it was served the second reading by version 0.0.4 and earlier; the "
                "exception's ``instead`` attribute is the rewrite that keeps that meaning."],
    },
    ("_validate_header_line", 0): {
        "fingerprint": "700fd66f05b4",
        "why": ["Only schema 1.1 is implemented, so a ``schema 1.2`` model (OpenFGA's "
                "modular models) would otherwise run with whatever meaning 1.1 gives it. "
                "The JSON front end refuses every ``schema_version`` but ``'1.1'`` the same "
                "way. This is stricter than OpenFGA, which also accepts ``1.2``."],
    },
    ("_validate_header_line", 1): {
        "fingerprint": "b174a0c85e45",
        "why": ["These lines are read by their first word, so the rest of the line would be "
                "dropped without a word: ``relations define viewer: [user]`` would leave "
                "``viewer`` undeclared. OpenFGA's grammar refuses extra words on these "
                "lines too."],
    },
    ("_parse_schema_ast_declared", 0): {
        "fingerprint": "655809f28387",
        "what": ["A second ``type`` block for the same type -- ``type doc`` declared twice "
                 "in one schema."],
        "why": ["Merging the two blocks would let a duplicate pasted into a schema change "
                "its relations without any warning."],
    },
    ("_parse_schema_ast_declared", 2): {
        "fingerprint": "f37fcd212872",
        "what": ["``.`` in a declared relation name -- ``define can.view: [user]``."],
    },
    ("_parse_schema_ast_declared", 3): {
        "fingerprint": "cae67fa06d28",
        "what": ["A second ``define`` of the same relation in one type -- "
                 "``define viewer: [user]`` and then ``define viewer: editor`` under one "
                 "``type doc``."],
    },
    ("_validate_restriction_types_declared", 0): {
        "fingerprint": "139f8f39b2bd",
        "why": ["A typo here would grant access. Write admission checks a write against the "
                "schema, not the schema against itself, so a ``usr:x`` write would be "
                "admitted and ``check`` would answer True. OpenFGA refuses it."],
    },
    # One reason per entry: the source states one reason for all five refusals.
    ("_validate_ast_consistency", 0): {
        "fingerprint": "f6d2410ff85e",
        "why": ["The members of an undeclared relation would be nobody, without a word, so "
                "a typo would silently deny access. OpenFGA refuses it."],
    },
    ("_validate_ast_consistency", 1): {
        "fingerprint": "8d24e59fc30b",
        "why": ["An undeclared relation would mean \"nobody\" without a word, so a "
                "misspelled relation name would silently deny access. OpenFGA refuses it."],
    },
    ("_validate_ast_consistency", 2): {
        "fingerprint": "c36935cccd1c",
        "why": ["No tuple can be stored on an undeclared relation, so the ``from`` would "
                "find no parent and mean \"nobody\" without a word; a typo would silently "
                "deny access. OpenFGA refuses it."],
    },
    ("_validate_ast_consistency", 3): {
        "fingerprint": "dd0dfb26bed3",
        "why": ["No parent object can have the target relation, so the ``from`` would mean "
                "\"nobody\" without a word; a typo would silently deny access. OpenFGA "
                "refuses it."],
    },
    ("_validate_ast_consistency", 4): {
        "fingerprint": "f203166ca9a6",
        "why": ["A loop of computed references has no single answer: with "
                "``define a: [user] or b`` and ``define b: a``, any set that contains the "
                "users stored on ``a`` satisfies both definitions, so the result would "
                "depend on how an evaluator settles the loop. OpenFGA refuses it."],
    },
    ("_validate_tuplesets_direct", 1): {
        "fingerprint": "e509925201da",
        "why": ["``from`` takes the stored subject's object as the parent and never looks "
                "at its predicate, so a stored ``folder:f#member`` would mean just "
                "``folder:f``, and the ``#member`` would be dropped without a word. OpenFGA "
                "refuses it: tupleset relations must be directly assignable types."],
    },
}

#: Hand-written text for blocks outside the parser, keyed (function, ordinal) per file.
#: Written 2026-10-20 (round 2) against the comment and the code beside it; the examples
#: were run against this checkout's code the same day (TK151 round-2 probes).
_OTHER_OVERRIDES: dict[str, dict[tuple[str, int], dict]] = {
    "schema/json_frontend.py": {
        ("parse_openfga_json", 0): {
            "fingerprint": "3e5c9a16cc49",
            "what": ["A ``schema_version`` other than ``\"1.1\"`` -- ``\"1.2\"``, or the "
                     "field left out."],
            "why": ["Only the 1.1 format is implemented: its "
                    "``directly_related_user_types`` metadata is where ``this`` gets its "
                    "type restrictions. An unsupported feature is refused, never skipped."],
            "instead": ["Supply the model as ``\"schema_version\": \"1.1\"``, or write it in "
                        "the DSL."],
        },
        ("parse_openfga_json", 1): {
            "fingerprint": "b49ffd76b956",
            "what": ["Model-level ``conditions`` -- a ``\"conditions\"`` object beside "
                     "``\"type_definitions\"``."],
            "why": ["Neither backend evaluates a condition, and skipping one would let its "
                    "tuples grant access unconditionally, which is wider access than the "
                    "model says."],
            "instead": ["None: conditions are not supported. Where the condition is a "
                        "stored fact, model it as a relation, for example "
                        "``define viewer: [user] but not suspended``."],
        },
        ("parse_openfga_json", 2): {
            "fingerprint": "9ea994b69166",
            "what": ["Two ``type_definitions`` entries for the same type -- two "
                     "``{\"type\": \"doc\", ...}`` entries."],
            "why": ["The second entry would replace the first one's relations without a "
                    "word, so the store would run a different schema from the one written. "
                    "The DSL refuses a second ``type`` block the same way."],
            "instead": ["Merge both entries' ``relations`` and ``metadata`` into one type "
                        "definition."],
        },
        ("parse_openfga_json", 3): {
            "fingerprint": "03a04f2ac031",
            "what": ["``.`` in a declared relation name -- a ``\"can.view\"`` key under "
                     "``\"relations\"``."],
            "why": ["Names containing ``.`` belong to the compiler's internal relations "
                    "(``<relation>.<index>``). The DSL refuses them too."],
            "instead": ["Use ``_``: ``can_view``, not ``can.view``."],
        },
        ("_validate_json_declares_a_relation", 0): {
            "fingerprint": "6b357cc974cd",
            "what": ["Type definitions none of which has a relation -- "
                     "``[{\"type\": \"user\"}]``, or ``\"relations\": {}`` on every type."],
            "why": ["It is the same empty schema as a model with no ``type_definitions``: "
                    "a store would save it as its permanent schema, refuse every write, and "
                    "the store id would be lost."],
            "instead": ["Give some type a relation, for example:",
                        ['{"type": "doc",',
                         ' "relations": {"viewer": {"this": {}}},',
                         ' "metadata": {"relations": {"viewer":',
                         '   {"directly_related_user_types": [{"type": "user"}]}}}}']],
        },
        ("_validate_json_declares_a_type", 0): {
            "fingerprint": "c288c432cea7",
            "what": ["A model with no ``type_definitions`` -- the field absent, ``null`` or "
                     "``[]``."],
            "why": ["It is an empty schema. A store would save it as its permanent schema "
                    "and then refuse every write, and since a store cannot be dropped, the "
                    "store id would be lost."],
            "instead": ["List the types, for example:",
                        ['"type_definitions": [',
                         '  {"type": "user"},',
                         '  {"type": "doc",',
                         '   "relations": {"viewer": {"this": {}}},',
                         '   "metadata": {"relations": {"viewer":',
                         '     {"directly_related_user_types": [{"type": "user"}]}}}}]']],
        },
        ("_validate_json_object", 0): {
            "fingerprint": "f9f403a7b517",
            "what": ["A field the OpenFGA model format defines as an object, given as some "
                     "other JSON kind -- the model itself as ``null`` or a list, a type "
                     "definition as a string, ``\"relations\": [\"viewer\"]``, a "
                     "``computedUserset`` body as a bare string."],
            "why": ["The model cannot be read as written. The error names the field, so the "
                    "mistake can be found."],
            "instead": ["The object form, for example "
                        "``{\"type\": \"doc\", \"relations\": {\"viewer\": "
                        "{\"computedUserset\": {\"relation\": \"owner\"}}}}``."],
        },
        ("_validate_json_array", 0): {
            "fingerprint": "1e4c032a68d2",
            "what": ["A field the OpenFGA model format defines as an array, given as some "
                     "other JSON kind -- ``\"type_definitions\": \"user\"``, "
                     "``\"child\": null``, ``\"directly_related_user_types\": \"user\"``."],
            "why": ["The model cannot be read as written, and a string in place of an array "
                    "would be read as a list of its characters."],
            "instead": ["The array form, for example "
                        "``\"directly_related_user_types\": [{\"type\": \"user\"}]``."],
        },
        ("_validate_json_field", 0): {
            "fingerprint": "c08a9240e928",
            "what": ["A required string field that is missing or not a string -- a type "
                     "definition with no ``\"type\"``, a ``computedUserset`` with no "
                     "``\"relation\"``, a ``tupleToUserset`` with no ``\"tupleset\"`` "
                     "relation."],
            "why": ["The model cannot be read without it. The error names the field."],
            "instead": ["Give the field, for example ``{\"type\": \"doc\"}`` or "
                        "``{\"computedUserset\": {\"relation\": \"owner\"}}``."],
        },
        ("_reject_duplicate_json_keys", 0): {
            "fingerprint": "5ba6c7ed929d",
            "what": ["A JSON object naming the same key twice -- two ``\"viewer\"`` "
                     "relations, two ``\"schema_version\"`` fields."],
            "why": ["A JSON reader keeps the last value without a word, so the store would "
                    "run a schema nobody wrote as such. The DSL refuses a second "
                    "``define viewer`` the same way."],
            "instead": ["One entry per key. Merge two definitions of a relation into one, "
                        "for example:",
                        ['"viewer": {"union": {"child": [',
                         '  {"this": {}},',
                         '  {"computedUserset": {"relation": "owner"}}]}}']],
        },
        ("_validate_json_wildcard", 0): {
            "fingerprint": "847594c30cf3",
            "what": ["``\"wildcard\"`` set to anything but ``{}`` or ``null`` -- ``false``, "
                     "``0``, ``\"\"``, ``{\"enabled\": false}``."],
            "why": ["A wildcard restriction grants access to every subject of the type, and "
                    "these values read as \"not a wildcard\". OpenFGA never writes them, so "
                    "any reading would be a guess, and the wrong guess grants public "
                    "access."],
            "instead": ["``{\"type\": \"user\", \"wildcard\": {}}`` for ``[user:*]``; leave "
                        "the key out for ``[user]``."],
        },
        ("_validate_json_round_trip", 0): {
            "fingerprint": "ab4ca1345a3f",
            "what": ["A JSON model whose DSL rendering is a different schema -- a name "
                     "holding ``]``, ``,``, a line break or a space, such as a restriction "
                     "``{\"type\": \"user,group\"}``."],
            "why": ["A JSON model is stored as its DSL rendering, so the store would run a "
                    "schema the JSON never declared, and could admit writes on a relation "
                    "it never had. The name checks usually refuse such a model first, with "
                    "a more specific message; this check is the last guard."],
            "instead": ["Keep every name inside the identifier charset, for example "
                        "``{\"type\": \"user\"}``."],
        },
        ("_json_restrictions", 0): {
            "fingerprint": "e2d906c29005",
            "what": ["A conditional type restriction -- "
                     "``{\"type\": \"user\", \"condition\": \"in_office\"}``."],
            "why": ["Conditions are not supported, and dropping one would make the "
                    "restriction unconditional, which is wider access than the model says."],
            "instead": ["None. Remove ``condition`` only if the unconditional grant is what "
                        "you mean, or model the condition as a relation "
                        "(``[user] but not suspended``)."],
        },
        ("_json_rewrite", 0): {
            "fingerprint": "d2881861a1b9",
            "what": ["``this`` with no ``directly_related_user_types`` metadata."],
            "why": ["With no type restrictions ``this`` admits no subject type, so the arm "
                    "could never hold a tuple."],
            "instead": ["Add the metadata on the type definition, for example "
                        "``\"metadata\": {\"relations\": {\"viewer\": "
                        "{\"directly_related_user_types\": [{\"type\": \"user\"}]}}}``."],
        },
        ("_json_rewrite", 1): {
            "fingerprint": "a2964c9db78a",
            "what": ["An unknown rewrite operator -- a misspelt key such as "
                     "``computedUserSet``."],
            "why": ["Skipping an unknown node would drop an arm of the relation without a "
                    "word. An unsupported feature is refused, never skipped."],
            "instead": ["None. Use ``this``, ``computedUserset``, ``tupleToUserset``, "
                        "``union``, ``intersection`` or ``difference``."],
        },
    },
    "schema/compiler.py": {
        ("_validate_object_wildcard_shapes", 0): {
            "fingerprint": "b6aab2d264cb",
            "what": ["An ``object_wildcard_shapes`` entry that is not a pair of strings -- "
                     "``\"doc:viewer\"``, ``(\"doc\",)``, ``(\"doc\", \"viewer\", \"x\")``."],
            "why": ["Read as a pair, a two-character string would split into a one-letter "
                    "type and relation, and other values would fail later with an error "
                    "that does not name the entry. Neither is what the caller meant."],
            "instead": ["A set of ``(object_type, relation)`` tuples, for example "
                        "``object_wildcard_shapes={(\"doc\", \"viewer\")}``."],
        },
        ("_validate_object_wildcard_shapes", 1): {
            "fingerprint": "e7cccf659b6c",
            "what": ["An ``object_wildcard_shapes`` entry naming an undeclared type -- "
                     "``(\"nosuch\", \"viewer\")``."],
            "why": ["No ``nosuch:*`` object can ever be written, so the entry would do "
                    "nothing while the caller believes an object wildcard is enabled: a "
                    "typo that silently denies."],
            "instead": ["Name a type the schema declares, ``(\"doc\", \"viewer\")`` for "
                        "``type doc``, or drop the entry; dropping it changes no answer."],
        },
        ("_validate_object_wildcard_shapes", 2): {
            "fingerprint": "e916daec5b30",
            "what": ["An ``object_wildcard_shapes`` entry naming a relation the type does "
                     "not declare -- ``(\"doc\", \"nosuchrel\")``, or a name containing "
                     "``.`` such as ``(\"doc\", \"viewer.0\")``."],
            "why": ["No grant on ``doc:*`` can ever be written to that relation, so the "
                    "entry would do nothing. A name containing ``.`` is never a declared "
                    "relation."],
            "instead": ["Name a relation the type declares (``define viewer: ...`` gives "
                        "``(\"doc\", \"viewer\")``), or drop the entry."],
        },
        ("_emit_expr", 0): {
            "fingerprint": "bf2f3d229f9a",
            "what": ["``and`` or ``but not`` compiled with ``enable_boolean=False`` -- "
                     "``parse_openfga_schema(schema, enable_boolean=False)`` or "
                     "``compile_ruleset(ast, schema_info, enable_boolean=False)``."],
            "why": ["That flag asks for the plain rule set only, which cannot express "
                    "``and`` or ``but not``."],
            "instead": ["Compile with the default, ``enable_boolean=True``."],
        },
        ("_validate_ttu_tuplesets", 0): {
            "fingerprint": "7d3ab64ce980",
            "what": ["A ``from`` in a plain relation that reaches a relation using ``and`` "
                     "or ``but not``, in a schema tree built by hand -- the parsed tree of "
                     "``define parent: [folder]`` and ``define reader: viewer from parent`` "
                     "on ``doc``, with ``define viewer: [user] but not banned`` on "
                     "``folder``, after deleting its ``(\"doc\", \"parent\")`` entry and "
                     "passing it to ``compile_ruleset``."],
            "why": ["Compiled as a plain rule, the ``from`` would give the graph index "
                    "different answers from the set engine. A schema text never gets "
                    "here: the parser refuses the undeclared tupleset, and an accepted "
                    "schema of this shape compiles correctly."],
            "instead": ["Write the schema as text and parse it, with the tupleset declared "
                        "as a direct relation:",
                        ["define parent: [folder]", "define reader: viewer from parent"]],
        },
        ("_validate_ttu_tuplesets", 1): {
            "fingerprint": "4d6e6a9d2101",
            "what": ["A tupleset with computed, ``from``, ``and`` or ``but not`` arms, in a "
                     "schema tree built by hand."],
            "why": ["``from`` follows the tuples stored on the tupleset relation, never its "
                    "computed members, so any other arm would be ignored without a word. "
                    "In a schema text the parser refuses this shape first; see "
                    ":ref:`Tuplesets <refused-tuplesets-the-relation-after-from>`."],
            "instead": ["Store the links on a direct relation and use that one in the "
                        "``from``:",
                        ["define parent_link: [folder]",
                         "define viewer: viewer from parent_link"]],
        },
        ("_reject_doubly_bridged_shapes", 0): {
            "fingerprint": "f378c8cfb54f",
            "what": ["A shape wildcarded on both sides -- ``[group:*#member]`` in a "
                     "restriction while ``(\"group\", \"member\")`` is also an "
                     "object-wildcard shape."],
            "why": ["A wildcard write on such a shape would make the graph index refuse "
                    "every later ordinary write of that shape, so neither backend runs the "
                    "schema. Neither form exists in OpenFGA."],
            "instead": ["Drop one of the two. Either write ``[group#member]`` instead of "
                        "``[group:*#member]`` (closest legal form: it covers only the groups "
                        "written, not every group), or remove the shape from "
                        "``object_wildcard_shapes``. The shape can also arrive through a "
                        "``from``, so the declared shape to remove may be the one the "
                        "``from`` reads."],
        },
        ("_reject_object_wildcard_scope", 0): {
            "fingerprint": "9c851d2c15f1",
            "what": ["An object-wildcard shape on a relation that uses ``and`` or "
                     "``but not`` -- ``(\"doc\", \"viewer\")`` with "
                     "``define viewer: [user] but not banned``."],
            "why": ["The graph index cannot keep a grant on every object of a type for a "
                    "relation that uses ``and`` or ``but not``."],
            "instead": ["None in the graph index. Drop the shape from "
                        "``object_wildcard_shapes`` and grant on concrete objects (this "
                        "covers only the objects written, not every object)."],
        },
        ("_reject_object_wildcard_scope", 1): {
            "fingerprint": "f7dd58bc6297",
            "what": ["An object-wildcard shape naming one of the compiler's internal "
                     "relations -- ``(\"doc\", \"viewer.0\")``."],
            "why": ["Names containing ``.`` belong to the compiler's internal relations and "
                    "are never declared by a schema. In practice the check described under "
                    ":ref:`Object-wildcard shapes <refused-object-wildcard-shapes>` refuses "
                    "such a name first."],
            "instead": ["Name the declared relation, ``(\"doc\", \"viewer\")``, subject to "
                        "the refusal above."],
        },
        ("_reject_object_wildcard_scope", 2): {
            "fingerprint": "81e7519f5f41",
            "what": ["An object-wildcard shape that the rewrite rules carry into a relation "
                     "that uses ``and`` or ``but not`` -- ``(\"doc\", \"editor\")`` with "
                     "``define viewer: editor but not banned``."],
            "why": ["The graph index cannot carry a grant on every object into a relation "
                    "that uses ``and`` or ``but not``."],
            "instead": ["None. Drop the shape, or drop the arm of the ``and`` / ``but not`` "
                        "relation that reads the wildcarded relation (that changes its "
                        "answers)."],
        },
        ("_reject_object_wildcard_scope", 3): {
            "fingerprint": "d077ae54a140",
            "what": ["An object-wildcard shape on the tupleset of a ``from`` inside a "
                     "relation that uses ``and`` or ``but not`` -- ``(\"doc\", \"parent\")`` "
                     "with ``define viewer: (viewer from parent) but not banned``."],
            "why": ["That relation reads the stored parent tuples directly, so a "
                    "``doc:*`` parent tuple would be invisible to it: wrong denials, with "
                    "nothing to report them."],
            "instead": ["Drop the shape and write one concrete parent tuple per object, "
                        "``folder:f parent doc:d``; this covers only the objects written."],
        },
        ("_reject_object_wildcard_scope", 4): {
            "fingerprint": "bede5bb87954",
            "what": ["An object-wildcard shape on the target of a ``from`` inside a "
                     "relation that uses ``and`` or ``but not`` -- ``(\"folder\", "
                     "\"viewer\")`` with ``define viewer: (viewer from parent) but not "
                     "banned`` on ``doc``."],
            "why": ["That relation reads the parents' concrete grants and never sees a grant "
                    "on every folder, so it would deny wrongly."],
            "instead": ["Drop the shape and grant on concrete folders, "
                        "``user:alice viewer folder:f``; this covers only the folders "
                        "written."],
        },
        ("_reject_object_wildcard_scope", 5): {
            "fingerprint": "ecc544120eb6",
            "what": ["A star tupleset ``[folder:*]`` whose ``from`` target uses ``and`` or "
                     "``but not`` -- ``define parent: [folder, folder:*]`` and "
                     "``define viewer: viewer from parent`` on ``doc``, with "
                     "``define viewer: [user] but not banned`` on ``folder``."],
            "why": ["It amounts to a wildcard userset over a relation that uses ``and`` or "
                    "``but not``, which the graph index cannot evaluate."],
            "instead": ["``define parent: [folder]`` and one parent tuple per folder "
                        "(closest legal form: it covers only the folders written)."],
        },
    },
    "schema/boolean.py": {
        ("build", 0): {
            "fingerprint": "8b1bc7bc45b5",
            "what": ["A wildcard userset over a relation that uses ``and`` or ``but not`` "
                     "-- ``[group:*#member]`` with ``define member: [user] but not banned`` "
                     "on ``group``."],
            "why": ["\"The members of every group\" over such a relation is a set the graph "
                    "index cannot evaluate."],
            "instead": ["``[group#member]`` with one tuple per group (closest legal form: "
                        "it covers only the groups written), or make ``group#member`` a "
                        "plain relation."],
        },
        ("_stratify", 0): {
            "fingerprint": "abc3565d7c4f",
            "what": ["Relations that use ``and`` or ``but not`` and depend on themselves -- "
                     "``define member: [user, group#member] but not banned``, where the "
                     "recursion runs through the type restriction ``group#member``."],
            "why": ["The graph index evaluates relations that use ``and`` or ``but not`` in "
                    "dependency order, and a relation that depends on itself has no place in "
                    "that order. A standalone set engine evaluates the schema. A loop "
                    "through the right-hand side of a ``but not`` is refused earlier, when "
                    "the schema is parsed (see \"Operators\" above)."],
            "instead": ["Recurse on a plain relation and apply the operator on top:",
                        ["define member_base: [user, group#member_base]",
                         "define member: member_base but not banned"],
                        "This is not equivalent: ``banned`` is subtracted once, at the "
                        "group queried, not at every level of nesting. Excluding at every "
                        "level has no form the graph index accepts."],
        },
    },
    "setengine/engine.py": {
        ("_reject_unlogged_write", 0): {
            "fingerprint": "8cd07b554e99",
            "what": ["A direct set-engine write on a store id that a ``Store`` owns -- "
                     "``SetEngine.add_tuple`` or ``remove_tuple`` on an id with a saved "
                     "schema."],
            "why": ["The write would change the stored tuples with no tuple-log row, so the "
                    "graph index, replicas and ``at_least`` tokens would never see it while "
                    "``lag()`` reports 0. An unlogged removal would leave the grant allowed "
                    "by ``Store.check``, and the store could then no longer revoke it."],
            "instead": ["Write through ``Store.add_tuple`` / ``Store.remove_tuple``. For a "
                        "standalone set engine, use a store id no ``Store`` owns."],
        },
        ("__init__", 0): {
            "fingerprint": "0c185c85181c",
            "what": ["A shape wildcarded on both sides, in a standalone set engine -- "
                     "``[group:*#member]`` while ``(\"group\", \"member\")`` is also an "
                     "object-wildcard shape."],
            "why": ["The same refusal as under \"Shapes the graph index cannot compile\" "
                    "above. The set engine runs the other shapes listed there, but refuses "
                    "this one too, so that both backends refuse it alike."],
            "instead": ["Drop one of the two, as described there."],
        },
    },
    "store/_store.py": {
        ("_reject_unlogged_adoption", 0): {
            "fingerprint": "ab2aea69683a",
            "what": ["Opening a ``Store`` on a store id whose tuples were written without "
                     "the tuple log -- tuples written with ``SetEngine.add_tuple`` on store "
                     "id ``\"s1\"``, then ``Store(session, \"s1\", schema=schema)``."],
            "why": ["A standalone set engine writes tuples without the tuple log. A new "
                    "store's graph index is built from the tuple log, so those tuples "
                    "would be invisible to it: ``check`` would answer False where the set "
                    "engine answers True, and removing one would be reported as corruption."],
            "instead": ["Open it with ``Store.adopt(session, store_id, schema=schema)``, "
                        "which builds the index from the stored tuples; leave ``schema=`` "
                        "out if the store already has a saved schema."],
        },
    },
    "graphindex/wildcard.py": {
        ("remove_node", 0): {
            "fingerprint": "e71fe02920e2",
            "what": ["Removing a node whose type and relation the schema's rewrites copy "
                     "tuples to or from -- on ``define viewer: editor``, removing "
                     "``doc:x#editor``."],
            "why": ["The write path stores a copy of each such tuple on another node, and "
                    "``remove_node`` deletes one node's edges without running the rewrites, "
                    "so the copies would outlive their originals. In the example, the "
                    "editors of ``doc:x`` would stay viewers."],
            "instead": ["Remove the node's tuples through the write path: route each one "
                        "through :meth:`zanzibar.schema.RuleSet.apply` and remove every edge "
                        "it yields with "
                        ":meth:`zanzibar.graphindex.WildcardIndex.remove_tuple`; on a schema "
                        "that uses ``and`` or ``but not``, then call "
                        ":meth:`zanzibar.graphindex.DeltaProcessor.run_cascade` in the same "
                        "transaction."],
        },
    },
}

#: Every override, keyed (file relative to src/zanzibar/, function, ordinal).
OVERRIDES: dict[tuple[str, str, int], dict] = {
    (_PARSER, fn, n): v for (fn, n), v in _PARSER_OVERRIDES.items()}
OVERRIDES.update({(f, fn, n): v for f, d in _OTHER_OVERRIDES.items() for (fn, n), v in d.items()})

#: Maintainer emphasis in the source comments, lowercased in rendered prose (never inside
#: a literal). Each must occur at least once in the scanned file, or the build fails as
#: stale. Any other all-capitals word left in rendered prose, outside ``CAPS_ALLOWED``,
#: fails the build.
EMPHASIS = ["IGNORED", "DROPPED", "STORED", "ONE", "SAME", "OBJECT", "BOTH", "ADMITTED",
            "REFERENCED", "TYPE"]
CAPS_ALLOWED = {"JSON", "ASCII", "DSL"}

#: Where a "Raises:" link may point: the exception's name must be exported by one of these
#: modules (first match wins); the link targets ``<module>.<name>``. Every exception the
#: product raises at a refusal is re-exported at the top level.
_EXCEPTION_HOMES = ["zanzibar"]
RAISE_WINDOW = 30   # lines below the block in which its ``raise`` must appear

#: Topic of each parser block, by the function it sits in; (function, ordinal) wins over
#: function. A parser block in an unlisted function lands under "Other refused shapes".
GROUPS: list[tuple[str, list]] = [
    ("Schema file and header lines", [
        "_validate_declares_a_type", "_validate_header_line",
        "_reject_unsupported_openfga_line", ("_parse_schema_ast_declared", 0),
        ("_parse_schema_ast_declared", 3)]),
    ("Names", [
        "_validate_declared_name", ("_parse_schema_ast_declared", 1),
        ("_parse_schema_ast_declared", 2), "check_name"]),
    ("Operators", [
        "_parse_chain", "_reject_unparenthesised_but_not", "_validate_stratified_negation"]),
    ("Type restrictions", [
        "_reject_conditional_restriction", "_validate_restriction_types_declared"]),
    ("References between relations", ["_validate_ast_consistency"]),
    ("Tuplesets (the relation after `from`)", ["_validate_tuplesets_direct"]),
]
OTHER_GROUP = "Other refused shapes"

#: Where each refusal happens: (title, intro, members, topic groups). A member is a file
#: (relative to ``src/zanzibar/``), a (file, function) or a (file, function, ordinal); the
#: most specific match wins. ``topic groups`` is ``GROUPS`` for the parser and ``None``
#: (one flat list) elsewhere. A block that matches no stage FAILS the build: each new
#: refusal site needs a deliberate place. In an intro, ``:func:`x``` / ``:class:`x``` /
#: ``:exc:`x``` / ``:meth:`x``` become links.
STAGES: list[tuple[str, str, list, list | None]] = [
    ("Schema text",
     "Refused while a DSL schema is parsed, by :func:`zanzibar.parse_openfga_schema`, by "
     ":class:`zanzibar.Store` and by :class:`zanzibar.setengine.SetEngine` alike.",
     [_PARSER], GROUPS),
    ("JSON models",
     "Refused by :func:`zanzibar.schema.parse_openfga_json`, and by :class:`zanzibar.Store` "
     "when ``schema=`` is a ``dict``, while it reads an OpenFGA JSON model. A refused model raises :exc:`zanzibar.SchemaError`, like a refused DSL text.",
     ["schema/json_frontend.py"], None),
    ("Object-wildcard shapes",
     "The ``object_wildcard_shapes`` argument is checked against the schema it comes with, "
     "by :func:`zanzibar.parse_openfga_schema`, :class:`zanzibar.Store` and "
     ":class:`zanzibar.setengine.SetEngine` alike.",
     [("schema/compiler.py", "_validate_object_wildcard_shapes")], None),
    ("Shapes the graph index cannot compile",
     "The schema is valid, but the graph index cannot serve it. "
     ":func:`zanzibar.parse_openfga_schema` and :class:`zanzibar.Store` raise these, because "
     "both build the graph index's rules; a standalone "
     ":class:`zanzibar.setengine.SetEngine` runs every one of these schemas except a shape "
     "that is wildcarded on both sides, which both backends refuse. Three entries are "
     "reached only through lower-level calls: ``enable_boolean=False`` passed to "
     ":func:`zanzibar.parse_openfga_schema` or :func:`zanzibar.schema.compile_ruleset`, "
     "and a schema tree built by hand and passed to "
     ":func:`zanzibar.schema.compile_ruleset`.",
     ["schema/compiler.py", "schema/boolean.py"], None),
    ("Set engine",
     "Refused by a standalone :class:`zanzibar.setengine.SetEngine`.",
     ["setengine/engine.py"], None),
    ("Opening a store",
     "Refused by :class:`zanzibar.Store` when it opens.",
     ["store/_store.py"], None),
    ("Graph index maintenance",
     "Refused by :meth:`zanzibar.graphindex.WildcardIndex.remove_node`, part of the "
     "low-level graph index API. A :class:`zanzibar.Store` has no call that removes a node.",
     ["graphindex/wildcard.py"], None),
]


# --------------------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------------------

Segments = list  # of str (prose) and list[str] (a code block)


@dataclass
class Block:
    file: str                          # relative to src/zanzibar/, posix
    function: str
    ordinal: int
    line: int
    raw: list[str]                     # the comment lines, '#' and one space stripped
    above: list[str]                   # contiguous comment lines directly above the header
    raises: str | None = None          # exception class of the first ``raise`` below the block
    accepted_through: str | None = None   # ``accepted_through=`` at that raise, if any
    fields: dict[str, Segments] = field(default_factory=dict)   # what / why / instead

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.file, self.function, self.ordinal)

    @property
    def where(self) -> str:
        return f"src/zanzibar/{self.file}:{self.line} ({self.function}, block {self.ordinal})"


def fingerprint(block: Block) -> str:
    text = "\n".join(" ".join(l.split()) for l in block.raw)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _comment_text(line: str) -> str | None:
    s = line.strip()
    if not s.startswith("#"):
        return None
    s = s[1:]
    return s[1:] if s.startswith(" ") else s


def _function_spans(source: str) -> list[tuple[int, int, str]]:
    return [(n.lineno, n.end_lineno or n.lineno, n.name) for n in ast.walk(ast.parse(source))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _innermost(spans, lineno: int) -> str:
    best = None
    for start, end, name in spans:
        if start <= lineno <= end and (best is None or start >= best[0]):
            best = (start, end, name)
    return best[2] if best else "<module>"


# ``Provenance:`` (maintainer history) and ``PROBED:`` (evidence notes) are read and dropped.
_FIELD_RE = re.compile(
    r"\b(WHY and INSTEAD|WHY/INSTEAD|WHY|INSTEAD|Provenance)(?: \([^)]*\))?:\s*")
_BOTH = "<<see why>>"


def _split_fields(lines: list[str]) -> dict[str, Segments]:
    """A block's lines as what / why / instead segment lists; a line indented four or
    more spaces past the ``#`` is code."""
    fields: dict[str, Segments] = {"what": [], "why": [], "instead": [], "dropped": []}
    current = "what"

    def add_text(key: str, text: str) -> None:
        segs = fields[key]
        if segs and isinstance(segs[-1], str):
            segs[-1] += " " + text
        else:
            segs.append(text)

    first = lines[0]
    head = first[first.index(HEADER) + len(HEADER):]
    head = re.sub(r"^\s*\([^)]*\)", "", head)      # the origin id
    head = re.sub(r"^\s*:\s*", "", head)
    for i, text in enumerate([head] + lines[1:]):
        if i > 0 and text.startswith("    ") and text.strip():
            segs = fields[current]
            if segs and isinstance(segs[-1], list):
                segs[-1].append(text[4:].rstrip())
            else:
                segs.append([text[4:].rstrip()])
            continue
        pos = 0
        for m in _FIELD_RE.finditer(text):
            add_text(current, text[pos:m.start()])
            if m.group(1) in ("WHY and INSTEAD", "WHY/INSTEAD"):
                add_text("why", _BOTH)
                current = "instead"
            elif m.group(1) == "Provenance":
                current = "dropped"
            else:
                current = m.group(1).lower()
            pos = m.end()
        add_text(current, text[pos:])
    del fields["dropped"]
    for key, segs in fields.items():
        fields[key] = [" ".join(s.split()) if isinstance(s, str) else s for s in segs]
        fields[key] = [s for s in fields[key] if s]
    return fields


_RAISE = re.compile(r"\s*raise\b\s*([A-Za-z_][\w.]*)?")
_EXCEPT = re.compile(r"\s*except\s*\(?\s*([A-Za-z_][\w.]*)")
_ACCEPTED = re.compile(r"accepted_through\s*=\s*['\"]([^'\"]+)['\"]")


def extract(path: Path, rel: str | None = None) -> list[Block]:
    """Every ``REFUSED SHAPE`` block in one file. Raises ``ExtensionError`` if the file
    cannot be read or parsed, or if a line names ``REFUSED SHAPE`` outside a block header."""
    rel = rel or path.relative_to(SRC_ROOT).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
        spans = _function_spans(source)
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
        raise ExtensionError(
            f"refused-shapes: cannot read src/zanzibar/{rel} ({type(exc).__name__}: {exc}); "
            f"its refusals would be missing from the page.") from exc
    lines = source.splitlines()
    blocks: list[Block] = []
    counts: dict[str, int] = {}
    for i, line in enumerate(lines):
        text = _comment_text(line)
        if text is None or HEADER not in text:
            continue
        raw = [text]
        for nxt in lines[i + 1:]:
            t = _comment_text(nxt)
            if t is None or HEADER in t:
                break
            raw.append(t)
        above: list[str] = []
        j = i - 1
        while j >= 0:
            t = _comment_text(lines[j])
            if t is None or HEADER in t:
                break
            above.insert(0, t)
            j -= 1
        fn = _innermost(spans, i + 1)
        ordinal = counts.get(fn, 0)
        counts[fn] = ordinal + 1
        b = Block(file=rel, function=fn, ordinal=ordinal, line=i + 1, raw=raw, above=above)
        window = lines[i + len(raw):i + len(raw) + RAISE_WINDOW]
        for k, nxt in enumerate(window):
            m = _RAISE.match(nxt)
            if not m:
                continue
            if m.group(1):
                b.raises = m.group(1).rsplit(".", 1)[-1]
            else:                       # a bare ``raise``: the handler's exception
                for back in reversed(lines[:i]):
                    e = _EXCEPT.match(back)
                    if e:
                        b.raises = e.group(1).rsplit(".", 1)[-1]
                        break
            call = "\n".join(window[k:k + 12])
            a = _ACCEPTED.search(call)
            b.accepted_through = a.group(1) if a else None
            break
        b.fields = _split_fields(raw)
        blocks.append(b)
    named = sum(1 for line in lines if HEADER in line)
    if named != len(blocks):
        raise ExtensionError(
            f"refused-shapes: src/zanzibar/{rel} names '{HEADER}' on {named} line(s) but "
            f"{len(blocks)} comment block(s) were found. A header outside a '#' comment "
            f"(a docstring, a string) would be missing from the page; make it a comment "
            f"block or reword the line.")
    return blocks


def collect(root: Path = SRC_ROOT, files: list[Path] | None = None) -> list[Block]:
    """Every block in the product package. Raises ``ExtensionError`` if none is found."""
    files = source_files(root) if files is None else files
    if not files:
        raise ExtensionError(f"refused-shapes: no Python file under {root}.")
    blocks = [b for path in files for b in extract(path, path.relative_to(root).as_posix())]
    if not blocks:
        raise ExtensionError(
            f"refused-shapes: found no '# {HEADER}' comment block under src/zanzibar/. The "
            f"scan broke or the convention was renamed, and the page would be empty.")
    return blocks


# --------------------------------------------------------------------------------------
# Cleaning and resolution
# --------------------------------------------------------------------------------------

def _drop_internal_parens(text: str) -> str:
    out, i = "", 0
    while i < len(text):
        if text[i] == "(":
            depth, j = 0, i
            while j < len(text):
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                if depth == 0:
                    break
                j += 1
            if j < len(text) and _INTERNAL_PAREN.search(text[i:j + 1]):
                # drop the parenthetical and the space before it, so "x (y)." -> "x."
                out = out.rstrip()
                i = j + 1
                if i < len(text) and text[i] not in ",.;:)":
                    out += " "
                continue
        out += text[i]
        i += 1
    return " ".join(out.split())


_BACKREF_ONLY = re.compile(
    r"^(?:see above|as above|the comment above|the docstring(?: above)?)"
    r"\s*(?:\([^)]*\))?\s*[.:]?\s*$", re.I)
_BACKREF_PREFIX = re.compile(
    r"^(?:the comment above|the docstring(?: above)?|as above)\s*(?::|--|-)\s*", re.I)


def _text_of(segs: Segments) -> str:
    return " ".join(s for s in segs if isinstance(s, str))


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


_LITERAL_SPLIT = re.compile(r"(``.+?``|`[^`]+`)")
_CAPS = re.compile(r"\b[A-Z]{2,}\b")


def _outside_literals(s: str, fn) -> str:
    return "".join(part if i % 2 else fn(part) for i, part in enumerate(_LITERAL_SPLIT.split(s)))


class _Cleaner:
    def __init__(self) -> None:
        self.used = [0] * len(PHRASES)
        self.emphasis_used = {w: 0 for w in EMPHASIS}

    def lower_emphasis(self, s: str) -> str:
        def fix(part: str) -> str:
            for w in EMPHASIS:
                part, n = re.subn(rf"\b{w}\b", w.lower(), part)
                self.emphasis_used[w] += n
            return part
        return _outside_literals(s, fix)

    def text(self, s: str) -> str:
        for k, (old, new) in enumerate(PHRASES):
            if old in s:
                self.used[k] += 1
                s = s.replace(old, new)
        s = _drop_internal_parens(s)
        s = re.sub(r"^\s*:\s*", "", s)
        s = self.lower_emphasis(s)
        return " ".join(s.split())

    def segs(self, segs: Segments) -> Segments:
        out = [self.text(s) if isinstance(s, str) else list(s) for s in segs]
        return [s for s in out if s]


def _stage_of(b: Block) -> tuple[int, int] | None:
    """(stage index, member index) of the most specific STAGES member matching ``b``."""
    best, rank = None, -1
    for idx, (_title, _intro, members, _groups) in enumerate(STAGES):
        for mi, m in enumerate(members):
            r = -1
            if m == b.file:
                r = 0
            elif isinstance(m, tuple) and len(m) == 2 and m == (b.file, b.function):
                r = 1
            elif isinstance(m, tuple) and len(m) == 3 and m == b.key:
                r = 2
            if r > rank:
                best, rank = (idx, mi), r
    return best


def _group_of(b: Block, groups: list | None) -> str | None:
    if groups is None:
        return None
    for title, members in groups:
        if (b.function, b.ordinal) in members:
            return title
    for title, members in groups:
        if b.function in members:
            return title
    return OTHER_GROUP


def _split_heading(what: str) -> tuple[str, str]:
    what = what.strip().rstrip(".")
    heading, sep, examples = what.partition(" -- ")
    if not sep:
        m = re.match(r"^(.*?)[ ,]*\(([^()]*``[^()]*)\)$", what)
        if m:
            heading, examples = m.group(1), m.group(2)
        else:
            m = re.match(r"^(.*?), (``.*``)$", what)
            if m:
                heading, examples = m.group(1), m.group(2)
    return _cap(heading.strip().rstrip(",:")), examples.strip()


def _exception_target(name: str | None) -> str | None:
    import importlib
    if not name:
        return None
    for home in _EXCEPTION_HOMES:
        mod = importlib.import_module(home)
        if name in getattr(mod, "__all__", ()) and isinstance(getattr(mod, name, None), type):
            return f"{home}.{name}"
    return None


def resolve(blocks: list[Block]) -> list[dict]:
    """Every block as {stage, group, heading, examples, why, instead, raises, ...}."""
    cleaner = _Cleaner()
    rendered: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    previous: dict[tuple[str, str], dict] = {}
    errors: list[str] = []
    for b in blocks:
        where = b.where
        f = {k: cleaner.segs(v) for k, v in b.fields.items()}
        override = OVERRIDES.get(b.key)
        if override is not None:
            seen.add(b.key)
            if override.get("fingerprint") != fingerprint(b):
                errors.append(
                    f"{where}: this comment changed after its OVERRIDES entry was written "
                    f"(source fingerprint {fingerprint(b)}, entry "
                    f"{override.get('fingerprint')}). Review the hand-written text in "
                    f"userdocs/_ext/refused_shapes.py::OVERRIDES against the new comment, "
                    f"then update the fingerprint.")
            for k in ("what", "why", "instead"):
                if k in override:
                    f[k] = [s if isinstance(s, str) else list(s) for s in override[k]]
        for k in ("why", "instead"):
            text = _text_of(f[k])
            if not f[k] or text == _BOTH or _BACKREF_ONLY.match(text) or _BOTH in text:
                if "comment above" in text.lower() and b.above:
                    f[k] = [_cap(cleaner.text(" ".join(b.above)))]
                elif (b.file, b.function) in previous and previous[(b.file, b.function)][k]:
                    f[k] = previous[(b.file, b.function)][k]
                else:
                    f[k] = []
            elif f[k] and isinstance(f[k][0], str):
                f[k][0] = _cap(_BACKREF_PREFIX.sub("", f[k][0]))
            if not f[k]:
                errors.append(f"{where}: no {k.upper()} after resolving back-references; "
                              f"add an OVERRIDES entry or fix the comment.")
            elif isinstance(f[k][-1], str) and not f[k][-1].endswith((".", ":", "?", "!")):
                f[k][-1] += "."
        previous[(b.file, b.function)] = f
        heading, examples = _split_heading(_text_of(f["what"]))
        placed = _stage_of(b)
        if placed is None:
            errors.append(f"{where}: no entry in STAGES places this file or function, so "
                          f"the page would not say where the refusal happens. Add one.")
            placed = (len(STAGES), 0)
        stage = placed[0]
        if b.raises is None:
            errors.append(f"{where}: no ``raise`` within {RAISE_WINDOW} lines below the "
                          f"block, so the entry cannot say what it raises.")
        target = _exception_target(b.raises)
        if b.raises is not None and target is None:
            errors.append(f"{where}: raises {b.raises!r}, which no module in "
                          f"_EXCEPTION_HOMES exports, so the 'Raises:' link cannot resolve.")
        note = None
        if b.raises == "ShapeNoLongerAccepted":
            note = (f"the shape was accepted by version {b.accepted_through or '0.0.4'} "
                    f"and earlier")
        groups = STAGES[stage][3] if stage < len(STAGES) else None
        item = {"stage": stage, "group": _group_of(b, groups), "heading": heading,
                "examples": examples, "why": f["why"], "instead": f["instead"],
                "raises": target, "raises_note": note, "where": where,
                "order": (placed[1], b.file, b.line)}
        lines = [heading, examples]
        for k in ("why", "instead"):
            for s in item[k]:
                lines.extend([s] if isinstance(s, str) else s)
        for line in lines:
            for m in _CAPS.finditer(_LITERAL_SPLIT.sub("", line)):
                if m.group(0) not in CAPS_ALLOWED:
                    errors.append(f"{where}: rendered prose shouts {m.group(0)!r} in "
                                  f"{line[:110]!r}. Add it to EMPHASIS (lowercased) or "
                                  f"CAPS_ALLOWED, or override the text.")
            for rx, kind in LEAKS:
                m = rx.search(line)
                if m:
                    errors.append(f"{where}: rendered text contains {kind} {m.group(0)!r} "
                                  f"in {line[:110]!r}. Add a PHRASES rule or an OVERRIDES "
                                  f"entry, or reword the comment.")
        rendered.append(item)
    for k, n in enumerate(cleaner.used):
        if n == 0:
            errors.append(f"PHRASES rule {PHRASES[k][0]!r} matched nothing under "
                          f"src/zanzibar/; it is stale, so delete or update it.")
    for w, n in cleaner.emphasis_used.items():
        if n == 0:
            errors.append(f"EMPHASIS word {w!r} occurs nowhere under src/zanzibar/; it is "
                          f"stale, so delete it.")
    for key in OVERRIDES:
        if key not in seen:
            errors.append(f"OVERRIDES entry {key} names no REFUSED SHAPE block under "
                          f"src/zanzibar/; it is stale.")
    if errors:
        raise ExtensionError("refused-shapes:" + "".join("\n  " + e for e in errors))
    return rendered


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------

_INLINE = re.compile(r":(func|class|exc|meth):`([^`]+)`|``(.+?)``|`([^`]+)`"
                     r"|:ref:`([^`<]+?) <([^`>]+)>`")


def _prose(text: str) -> str:
    return text.replace(" -- ", " — ")


def _xref(reftype: str, target: str, docname: str) -> nodes.Node:
    shown = target.rsplit(".", 1)[-1] if reftype != "meth" else ".".join(target.split(".")[-2:])
    ref = addnodes.pending_xref("", refdomain="py", reftype=reftype, reftarget=target,
                                refexplicit=False, refwarn=True, refdoc=docname)
    if reftype in ("func", "meth"):
        shown += "()"
    ref += nodes.literal(shown, shown, classes=["xref", "py", f"py-{reftype}"])
    return ref


def _inline(text: str, docname: str = "") -> list[nodes.Node]:
    out: list[nodes.Node] = []
    pos = 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            out.append(nodes.Text(_prose(text[pos:m.start()])))
        if m.group(1):
            out.append(_xref(m.group(1), m.group(2), docname))
        elif m.group(5):
            # A link to another entry's or section's anchor on this page (see ``anchor``).
            ref = addnodes.pending_xref("", refdomain="std", reftype="ref",
                                        reftarget=m.group(6), refexplicit=True,
                                        refwarn=True, refdoc=docname)
            ref += nodes.inline(m.group(5), m.group(5))
            out.append(ref)
        else:
            lit = m.group(3) if m.group(3) is not None else m.group(4)
            out.append(nodes.literal(lit, lit))
        pos = m.end()
    if pos < len(text):
        out.append(nodes.Text(_prose(text[pos:])))
    return out


def _para(label: str | None, text: str, docname: str = "") -> nodes.paragraph:
    p = nodes.paragraph()
    if label:
        p += nodes.strong(label, label)
        if text:
            p += nodes.Text(" ")
    p.extend(_inline(text, docname))
    return p


def _code(lines: list[str]) -> nodes.literal_block:
    body = "\n".join(lines)
    block = nodes.literal_block(body, body)
    block["language"] = "text"
    return block


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60].rstrip("-") or "shape"


class RefusedShapesDirective(SphinxDirective):
    """``{refused-shapes}``: one section per refused shape, grouped by where it happens."""

    has_content = False
    optional_arguments = 0

    def run(self) -> list[nodes.Node]:
        files = source_files()
        for path in files:
            self.env.note_dependency(str(path))
        items = resolve(collect(files=files))
        doc = self.env.docname
        result: list[nodes.Node] = []
        used: set[str] = set()

        std = self.env.get_domain("std")

        def anchor(text: str) -> str:
            # Each anchor is also a std label, so another page can link it with
            # {ref}`text <refused-...>` (a MyST "page.md#id" link only sees headings).
            base = "refused-" + _slug(text)
            ident, n = base, 1
            while ident in used:
                n += 1
                ident = f"{base}-{n}"
            used.add(ident)
            std.note_hyperlink_target(ident, doc, ident, text.replace("``", ""))
            return ident

        def entry(it: dict) -> nodes.section:
            sec = nodes.section(ids=[anchor(it["heading"])], classes=["refused-shape"])
            sec += nodes.title("", "", *_inline(it["heading"], doc))
            if it["examples"]:
                sec += _para("Refused, for example:", it["examples"], doc)
            for key, label in (("why", "Why:"), ("instead", "Instead:")):
                first = True
                for s in it[key]:
                    if isinstance(s, str):
                        sec += _para(label if first else None, _cap(s) if first else s, doc)
                    else:
                        if first:
                            sec += _para(label, "", doc)
                        sec += _code(s)
                    first = False
            p = _para("Raises:", "", doc)
            p += nodes.Text(" ")
            p += _xref("exc", it["raises"], doc)
            if it["raises_note"]:
                p += nodes.Text(f" ({it['raises_note']}).")
            sec += p
            return sec

        for idx, (title, intro, _members, groups) in enumerate(STAGES):
            # Within a stage, entries follow the order of its members, then the source.
            members = sorted((it for it in items if it["stage"] == idx),
                             key=lambda it: it["order"])
            if not members:
                continue
            ssec = nodes.section(ids=[anchor(title)])
            ssec += nodes.title("", "", *_inline(title, doc))
            ssec += _para(None, intro, doc)
            if groups is None:
                for it in members:
                    ssec += entry(it)
            else:
                for gtitle in [t for t, _ in groups] + [OTHER_GROUP]:
                    gm = [it for it in members if it["group"] == gtitle]
                    if not gm:
                        continue
                    gsec = nodes.section(ids=[anchor(gtitle)])
                    gsec += nodes.title("", "", *_inline(gtitle, doc))
                    for it in gm:
                        gsec += entry(it)
                    ssec += gsec
            result.append(ssec)
        return result


def setup(app):
    app.add_directive("refused-shapes", RefusedShapesDirective)
    return {"version": "2", "parallel_read_safe": True, "parallel_write_safe": True}
