"""P23 (+ TK109, TK105) -- the product parser and the oracle parser refuse the SAME schemas.

Property guarded
----------------
For every schema text, ``zanzibar.schema.parse_schema_ast`` accepts it iff
``tests.oracle.parse_schema_ast`` does, and when both accept they declare the same
``(type, relation)`` keys. The oracle is the independent referee. A schema only it accepts
is one where it answers questions the system refuses to serve. A schema only it refuses is
one it cannot referee at all. Map, census and contract:
``docs/p23-parser-refusal-parity-2026-10-03.md``.

The declared-name contract itself (both parsers, plus the JSON front end): a declared TYPE
name must match the write identifier charset ``[A-Za-z0-9_./@+=-]{1,256}``, and a declared
RELATION name must match it and contain no ``.``. Both implementations are
``_validate_declared_name``, NOT shared code (the oracle's independence contract), so each
parser is pinned by its own test and a red names the parser that regressed.

Pre-fix evidence, literal output (2026-10-03e, ``.scratch/p23/witness.py`` and
``consequence.py`` against the tree BEFORE this change; the ``.scratch/`` copies are
gitignored, this docstring is the tracked record)::

    '*'           prod=accept oracle=accept
    'a#b'         prod=accept oracle=accept
    'can view'    prod=accept oracle=accept
    'a.b'         prod=REFUSE oracle=accept
    ConnectedStore(schema=<define *: viewer but not blocked>): constructed OK
    add_tuple('...', 'user', 'alice', 'viewer', 'doc', 'd1') ->
        AdmissionRejected invalid relation '*': must match [A-Za-z0-9_./@+=-] (1-256 chars)

The pre-fix differential fuzz (seed 0, 20,000 trials; the census in the map, sec 1b)
found ten classes of split, the largest ``2169 prod-only-refuses | unrecognized schema
line``. The same sweep after the fix, at five seeds of 100,000 trials each, found none.

Sabotage (2026-10-03e, `.scratch/p23/sweep.py`). Sixteen mutations, each removing ONE new
check from one parser, file restored with its sha256 checked. All sixteen went RED, and an M0
control (production refuses every name) reddened exactly the accept controls. The literal
table, with the count of failing tests per row and whether the fuzz was among them, is in
the map, sec 4. A first sweep found four oracle twins INERT. Each was subsumed by another
check, and they were deleted (map, sec 4). The fuzz CANNOT see duplicates (a character edit
cannot copy a line) or `#...`. For those, the named cases below are the only pin.
"""

from __future__ import annotations

import pathlib
import random

import pytest
from sqlmodel import Session, SQLModel, create_engine

from zanzibar.connectedstore import ConnectedStore
from tests import oracle as oracle_mod
from zanzibar.schema import parse_openfga_json, parse_schema_ast

_HEAD = ("model\n  schema 1.1\ntype user\ntype group\n  relations\n"
         "    define member: [user]\ntype doc\n  relations\n"
         "    define blocked: [user]\n    define viewer: [user]\n")

#: One schema per refused shape. `P23` = declared-name charset (new in BOTH parsers);
#: the rest were already refused by production and are new in the oracle (`TK109`; the
#: duplicate define is `TK105`). The census class each came from is in the map, sec 1b.
_REFUSED = {
    # P23 -- declared names outside the write charset
    'P23/rel-star': _HEAD + "    define *: viewer but not blocked\n",
    'P23/rel-hash': _HEAD + "    define a#b: viewer\n",
    'P23/rel-space': _HEAD + "    define can view: viewer\n",
    'P23/rel-tab': _HEAD + "    define can\tview: viewer\n",
    'P23/rel-non-ascii': _HEAD + "    define caf\u00e9: viewer\n",
    'P23/rel-257-chars': _HEAD + "    define " + "r" * 257 + ": viewer\n",
    'P23/type-hash': _HEAD + "type d#oc\n",
    'P23/type-bracket': _HEAD + "type re[o\n",
    'P23/type-257-chars': _HEAD + "type " + "t" * 257 + "\n",
    # TK109 -- shapes production already refused and the oracle accepted
    'TK109/dot-in-declared-name': _HEAD + "    define a.b: viewer\n",
    'TK109/duplicate-type': _HEAD + "type doc\n",
    'TK109/duplicate-relation (TK105)': _HEAD + "    define viewer: [user] or blocked\n",
    'TK109/malformed-type-line': _HEAD + "type use r\n",
    'TK109/unrecognised-line': _HEAD + "    defne owner: [user]\n",
    'TK109/bare-define-line': _HEAD + "    define\n",
    'TK109/empty-restriction-list': _HEAD + "    define owner: []\n",
    'TK109/empty-restriction-entry': _HEAD + "    define owner: [user,, group#member]\n",
    'TK109/leading-empty-entry': _HEAD + "    define owner: [,user]\n",
    'TK109/restriction-type-space': _HEAD + "    define owner: [us er]\n",
    'TK109/restriction-wild-space': _HEAD + "    define owner: [user: *]\n",
    'TK109/restriction-type-garbage': _HEAD + "    define owner: [group:)]\n",
    'TK109/restriction-userset-garbage': _HEAD + "    define owner: [group#mem*er]\n",
}

#: Accept controls: near-misses of the shapes above that BOTH parsers must accept with
#: the same keys. Without them a parser that refused everything would pass every test above.
#: `tab-heads` is the case where the oracle used to be STRICTER by accident: it tested
#: `startswith('define ')` and skipped the line, then refused the dangling reference to it.
_ACCEPTED = {
    'baseline': _HEAD,
    'rel-256-chars': _HEAD + "    define " + "r" * 256 + ": viewer\n",
    'rel-full-charset': _HEAD + "    define a_/@+=-9: viewer\n",
    'type-with-dot': _HEAD + "type a.b\n",
    'tab-heads': _HEAD + "type\tfolder\n  relations\n    define\towner: [user]\n",
    'userset-ellipsis-is-bare': _HEAD + "    define owner: [group#...]\n",
    'space-before-colon': _HEAD + "    define owner : [user]\n",
    'header-lines-with-junk': "model x y\nrelations z\n" + _HEAD,
}


@pytest.mark.parametrize('label', sorted(_REFUSED))
def test_production_parser_refuses(label):
    """Sabotage P (2026-10-03e): `src/zanzibar/schema/parser.py::_validate_declared_name` made a
    no-op -> `17 failed`: the nine `P23/*` cases here, the six JSON cases, the end-to-end
    test and the fuzz. Every oracle case stayed green."""
    with pytest.raises(ValueError):
        parse_schema_ast(_REFUSED[label])


@pytest.mark.parametrize('label', sorted(_REFUSED))
def test_oracle_parser_refuses_independently(label):
    """Sabotage O1-O8 (2026-10-03e): each new oracle check in `tests/oracle.py` disabled
    on its own -> its named case(s) here went red (map, sec 4)."""
    with pytest.raises(ValueError):
        oracle_mod.parse_schema_ast(_REFUSED[label])


@pytest.mark.parametrize('label', sorted(_ACCEPTED))
def test_both_parsers_accept_the_controls_with_the_same_keys(label):
    prod = parse_schema_ast(_ACCEPTED[label])
    orac = oracle_mod.parse_schema_ast(_ACCEPTED[label])
    assert set(prod) == set(orac)


# --------------------------------------------------------------------------- #
# The differential fuzz (the census in the map, sec 1b, made permanent)
# --------------------------------------------------------------------------- #

_SEED_DIR = pathlib.Path(__file__).resolve().parent / 'fga_schemas'
_ALPHABET = (list('[]#:*,.() \t\n-_/@+=x\u00e9')
             + ['or ', 'and ', 'but not ', ' from ', 'define ', 'type ', 'relations\n',
                'model\n'])
_FUZZ_SEEDS = (0, 1, 2)
_FUZZ_TRIALS = 6000

#: Non-vacuity floors for the 18,000 trials, set 2026-10-03e at about half the count
#: measured on this tree that day: `refused 17089 accepted 911 splits 0`. Most mutations
#: break the text, so the accept side is the thin one. Too few refusals means the mutator
#: stopped reaching the parsers' checks; too few accepts means it only produces garbage
#: and the key comparison never runs.
MIN_FUZZ_REFUSED = 8000
MIN_FUZZ_ACCEPTED = 450


def _verdict(parse, text):
    try:
        return frozenset(parse(text))
    except ValueError:
        return None


def _mutate(text: str, rng: random.Random) -> str:
    for _ in range(rng.randint(1, 3)):
        i = rng.randrange(len(text) + 1)
        k = rng.random()
        if k < 0.4:
            text = text[:i] + rng.choice(_ALPHABET) + text[i:]
        elif k < 0.7:
            text = text[:i] + text[i + rng.randint(1, 4):]
        else:
            text = text[:i] + rng.choice(_ALPHABET) + text[i + 1:]
    return text


def test_differential_fuzz_parsers_agree_on_accept_and_keys():
    """Both parsers give the same verdict on every mutated fixture, and the same keys when
    both accept.

    Instrument control: the seeds must all be accepted by both parsers, otherwise every
    mutation of a seed is compared refuse-with-refuse. The refused/accepted floors check
    the mix. Sabotage F (2026-10-03e): the oracle's unrecognised-line refusal removed ->
    this test goes red (sweep row O7, map sec 4)."""
    seeds = [p.read_text(encoding='utf-8') for p in sorted(_SEED_DIR.glob('*.fga'))]
    assert len(seeds) >= 15
    for s in seeds:
        assert _verdict(parse_schema_ast, s) is not None
        assert _verdict(oracle_mod.parse_schema_ast, s) is not None
    splits, refused, accepted = [], 0, 0
    for seed in _FUZZ_SEEDS:
        rng = random.Random(seed)
        for _ in range(_FUZZ_TRIALS):
            text = _mutate(rng.choice(seeds), rng)
            a = _verdict(parse_schema_ast, text)
            b = _verdict(oracle_mod.parse_schema_ast, text)
            if a != b:
                splits.append((a is None, b is None, text))
            elif a is None:
                refused += 1
            else:
                accepted += 1
    assert not splits, (
        f'{len(splits)} split(s); first (prod_refused, oracle_refused, text): {splits[0]!r}')
    assert refused >= MIN_FUZZ_REFUSED, refused
    assert accepted >= MIN_FUZZ_ACCEPTED, accepted


# --------------------------------------------------------------------------- #
# The shipped consequence, and the JSON front end
# --------------------------------------------------------------------------- #

def test_connected_store_refuses_the_schema_instead_of_the_write():
    """Pre-fix (docstring): the store was built, then refused a VALID write on `viewer`
    with `AdmissionRejected invalid relation '*'`. Now the schema itself is refused,
    before any write, naming the charset."""
    engine = create_engine('sqlite:///:memory:')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        with pytest.raises(ValueError, match=r"declared relation name '\*'"):
            ConnectedStore(session, 'cs', schema=_REFUSED['P23/rel-star'])


def _json_model(type_name='doc', rel_name='viewer'):
    return {
        'schema_version': '1.1',
        'type_definitions': [
            {'type': 'user'},
            {'type': type_name,
             'relations': {rel_name: {'this': {}}},
             'metadata': {'relations': {
                 rel_name: {'directly_related_user_types': [{'type': 'user'}]}}}},
        ],
    }


@pytest.mark.parametrize('type_name,rel_name', [
    ('doc', '*'), ('doc', ''), ('doc', 'can view'), ('doc', 'r' * 257), ('d#oc', 'viewer'),
    ('', 'viewer'),
])
def test_json_front_end_refuses_the_same_declared_names(type_name, rel_name):
    """`TK115` V6 (`can view`) and V8 (an empty name) were accepted by `parse_openfga_json`.
    Its other holes (duplicate keys, `"wildcard": false`) stay on `TK115`."""
    with pytest.raises(ValueError, match=r'declared (type|relation) name'):
        parse_openfga_json(_json_model(type_name, rel_name))


def test_json_front_end_control_accepts():
    assert set(parse_openfga_json(_json_model())) == {('doc', 'viewer')}
