"""TK144 sabotage plugin (2026-10-17). Patches ONE method's source at pytest configure time
(anchor asserted to occur exactly once; the method is recompiled in its own module's
globals and rebound on the SAME class, so class identity -- and every
``from ... import`` of it -- is untouched). The shared source tree is never edited.

Modes S1-S12 each remove one corner or one guard of OpenFGA's implicit userset
self-relation; the expected reds are recorded in
``tests/test_tk138_userset_self_relation.py``'s docstring ("SABOTAGE") and in the plan doc's
2026-10-17 corrections. S13/S14 re-run ``tests/test_p6_phantom_subject.py``'s S1 at its old
site (the residue userset arm) and on the read-time branch; the verdicts are recorded in
that module's docstring. S15-S19 (added by the 2026-10-17 review fix) remove the
seed-shape ``w_any`` probe, its witness gate, the seed -> object-star probe, and the two
lookup twins; their reds are recorded in the docstrings of the three seed-shape tests at
the bottom of ``tests/test_tk138_userset_self_relation.py``. S20 (the set engine applies the
self hit only on types some ``[T#r]`` restriction names) is the sabotage for the grid
widening of the same review, and G0 is its INSTRUMENT control (the widening reverted);
their verdicts are in ``tests/parity.py::ParityEngine._self_floor``'s docstring.

Run (Bash, repo root; modes may be comma-joined):

    SAB144=S4 PYTHONPATH=formal/probes python -m pytest -p tk144_sabotage_plugin_2026_10_17 \\
        tests/test_tk138_userset_self_relation.py -q

The name uses underscores (not this directory's hyphenated dates) because ``-p`` imports it.
"""
import __future__
import inspect
import os
import sys
import textwrap

MODES = [m for m in os.environ.get('SAB144', '').split(',') if m]


def _patch(cls, name, old, new):
    fn = getattr(cls, name)
    src = textwrap.dedent(inspect.getsource(fn))
    n = src.count(old)
    if n != 1:
        raise RuntimeError(f'SAB144 anchor for {cls.__name__}.{name} occurs {n} times')
    src = src.replace(old, new)
    module = sys.modules[fn.__module__]
    ns = dict(module.__dict__)
    flags = __future__.annotations.compiler_flag      # the modules defer annotations
    exec(compile(src, f'<sab144 {cls.__name__}.{name}>', 'exec', flags=flags,
                 dont_inherit=True), ns)
    setattr(cls, name, ns[name])


def pytest_configure(config):
    for mode in MODES:
        _apply(mode)


def pytest_collection_finish(session):
    if 'G0' not in MODES:
        return
    done = set()
    for name in ('test_lookup_oracle', 'tests.test_lookup_oracle'):
        mod = sys.modules.get(name)
        if mod is None or id(mod) in done:
            continue
        done.add(id(mod))
        _patch(mod, '_subject_candidates',
               "shapes.update(ast)",
               "for (t, p) in sorted(shapes):\n"
               "        if p != '...':\n"
               "            shapes.update((t, r) for (ot, r) in ast if ot == t)")
        print(f'[sab144] G0 patched {name}._subject_candidates')


def _apply(mode):
    from tests.oracle import Oracle
    from zanzibar.setengine.engine import SetEngine
    from zanzibar.graphindex.wildcard import WildcardIndex
    if mode == 'S1':        # oracle corner: no self disjunct
        _patch(Oracle, 'check',
               "result = ((subject[2] != '...' and subject[1] != '*' and subject == key)",
               "result = (False")
    elif mode == 'S2':      # set-engine corner: no self hit in sat
        _patch(SetEngine, 'check',
               "if s_pred != '...' and s_name != '*' and subject == key:",
               "if False:")
    elif mode == 'S3':      # graph untainted: no self-relation at all
        _patch(WildcardIndex, '_check_internal',
               "if reflexive and s_pred != '...' and not subj_is_star:",
               "if False:")
    elif mode == 'S4':      # graph untainted: OWN-OBJECT ONLY (self hit kept, no seed probes)
        _patch(WildcardIndex, '_check_internal',
               "seed_keys.append((r1, s_type, s_name, ''))",
               "pass")
    elif mode == 'S5':      # graph derived: no C5 (the residue answers userset subjects)
        _patch(WildcardIndex, '_check_derived',
               "if reflexive and self._reflexive_reads and s_pred != '...':",
               "if False:")
    elif mode == 'S6':      # graph derived: self hit only, no read-time plan evaluation
        _patch(WildcardIndex, '_check_derived',
               "return self._derived_read_eval(s_pred, s_type, s_name, relation, o_type, o_name)",
               "pass")
    elif mode == 'S7':      # set lookup: no own-object relation-by-relation pass
        _patch(SetEngine, 'lookup',
               "if s_pred != '...' and s_name != '*' and (s_type, s_pred) in self.ast:",
               "if False:")
    elif mode == 'S8':      # set expand / lookup_reverse: no self-relation correction
        _patch(SetEngine, '_self_relation_corrected',
               "pos, neg = set(m.pos), set(m.neg)",
               "return m")
    elif mode == 'S9':      # graph lookup: no self lookup (residue memberships instead)
        _patch(WildcardIndex, 'lookup',
               "and (s_type, s_pred) in self._seed_index):",
               "and False):")
    elif mode == 'S10':     # graph lookup_reverse, untainted: no self expansion
        _patch(WildcardIndex, '_self_reverse_extra',
               "out: set[tuple[str, str, str]] = set()",
               "return set()")
    elif mode == 'S11':     # graph lookup_reverse, derived: no candidate correction
        _patch(WildcardIndex, '_self_reverse_derived',
               "cands = self._derived_reverse_candidates(relation, o_type, o_name)",
               "return")
    elif mode == 'S12':     # D1 widened in the oracle: userset STAR subjects take the rule
        _patch(Oracle, 'check',
               "(subject[2] != '...' and subject[1] != '*' and subject == key)",
               "(subject[2] != '...' and subject == key)")
    elif mode == 'S13':     # tests/test_p6_phantom_subject.py's S1, on the RESIDUE userset
        # arm only (the reflexive=False read): require a materialised node there.
        _patch(WildcardIndex, '_check_derived',
               "\n        return subj is None or subj.id not in neg",
               "\n        return subj is not None and subj.id not in neg")
    elif mode == 'S14':     # the same edges-alone reading on the LIVE (C5) userset read
        _patch(WildcardIndex, '_check_derived',
               "return self._derived_read_eval(s_pred, s_type, s_name, relation, o_type, o_name)",
               "return (self._get_concrete(s_pred, s_type, s_name) is not None\n"
               "                    and self._derived_read_eval(s_pred, s_type, s_name,"
               " relation, o_type, o_name))")
    # S15-S19 (TK144 review, 2026-10-17): the seed-shape / object-star branches the review
    # found gate-inert (its W1, W2, W3, L1; S19 is this session's twin on lookup_reverse).
    elif mode == 'S15':     # graph untainted: no seed-SHAPE w_any probes
        _patch(WildcardIndex, '_check_internal',
               "w_seed_keys.append((r1, s_type, '*', 'any'))",
               "pass")
    elif mode == 'S16':     # graph untainted: seed-shape w_any probed without the witness gate
        _patch(WildcardIndex, '_check_internal',
               "if w_seed_keys and not self._entity_has_witness(s_type, s_name):",
               "if False:")
    elif mode == 'S17':     # graph untainted: no seed -> object-star (w_all) probe
        _patch(WildcardIndex, '_check_internal',
               "key(seed_id, obj_id)\n        key(seed_id, w_all_id)",
               "key(seed_id, obj_id)")
    elif mode == 'S18':     # graph lookup: no witnessed seed-shape w_any collection
        _patch(WildcardIndex, '_self_lookup', "if witnessed:", "if False:")
    elif mode == 'S19':     # graph lookup_reverse: no any-marker expansion to instances
        _patch(WildcardIndex, '_self_reverse_extra',
               "for n in self._witnessed_names(t):", "for n in ():")
    elif mode == 'S20':     # set engine: self hit only on types some [T#r] restriction names
        # (the grid-widening sabotage: invisible to a grid that offers (T, r) userset
        # subjects only for types that already have a userset shape)
        _patch(SetEngine, 'check',
               "if s_pred != '...' and s_name != '*' and subject == key:",
               "if (s_pred != '...' and s_name != '*' and subject == key and s_type in {\n"
               "                    r.type for e in self.ast.values() for d in __import__(\n"
               "                        'zanzibar.schema.syntax', fromlist=['_iter_directs']\n"
               "                    )._iter_directs(e) for r in d.restrictions\n"
               "                    if r.predicate != '...'}):")
    elif mode == 'G0':      # INSTRUMENT control: revert the 2026-10-17 grid widening (the
        # ParityEngine self floor; _subject_candidates back to "every relation of a type
        # that already has a userset shape")
        # (tests/test_lookup_oracle.py's half is patched after collection, below: pytest
        # imports a test module of a package-less directory under its basename)
        from tests import parity
        _patch(parity.ParityEngine, '_grid',
               "queries += self._self_floor(subject_shapes, targets, set(queries))",
               "pass")
    else:
        raise RuntimeError(f'unknown SAB144={mode!r}')
    print(f'[sab144] applied {mode}')
