"""
Golden tests for the reference oracle (spec §8.1).

Every expected boolean below is computed BY HAND in the comments, not by any
implementation. These are the check on the shared DSL parser: if the oracle's
parse_schema diverges from the human reading of the schema, these fail.

Predicate convention: '...' is the bare subject predicate; a relation name means
a userset subject (T#relation).
"""

from tests.oracle import Oracle, OracleTuple, t, parse_schema


# ---------------------------------------------------------------------------
# 1. [user:*] public-doc scenario
# ---------------------------------------------------------------------------

PUBLIC_DOC_SCHEMA = '''
model
  schema 1.1

type user

type document
  relations
    define viewer: [user:*, user]
'''


def test_public_doc_ghost_user_true():
    # Single wildcard grant: user:* is a viewer of doc:d.
    tuples = [t('...', 'user', '*', 'viewer', 'document', 'd')]
    o = Oracle(PUBLIC_DOC_SCHEMA, tuples)

    # A never-mentioned user (ghost) is a viewer via the [user:*] marker.
    #   expand(document, d, viewer): direct tuple has subject user:* -> markers={(user,'...')}
    #   check(alice): s_pred='...' -> (user,'...') in markers -> TRUE
    assert o.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True
    assert o.check('...', 'user', 'ghost_who_never_existed', 'viewer', 'document', 'd') is True


def test_public_doc_other_doc_false():
    tuples = [t('...', 'user', '*', 'viewer', 'document', 'd')]
    o = Oracle(PUBLIC_DOC_SCHEMA, tuples)
    # doc:e has no grant at all. expand(document, e, viewer) sees no matching tuple
    # (matching_objects={'e','*'}; the grant targets 'd'). markers empty -> FALSE.
    assert o.check('...', 'user', 'alice', 'viewer', 'document', 'e') is False


def test_public_doc_intensional_wildcard_query():
    # Intensional (§4.2): user:* query asks "does a grant flow THROUGH the wildcard".
    tuples = [t('...', 'user', '*', 'viewer', 'document', 'd')]
    o = Oracle(PUBLIC_DOC_SCHEMA, tuples)
    # marker (user,'...') present -> TRUE
    assert o.check('...', 'user', '*', 'viewer', 'document', 'd') is True

    # Two users each granted individually, NO wildcard tuple: extensional-forall is
    # true but intensional is FALSE. markers stays empty.
    tuples2 = [
        t('...', 'user', 'alice', 'viewer', 'document', 'd'),
        t('...', 'user', 'bob', 'viewer', 'document', 'd'),
    ]
    o2 = Oracle(PUBLIC_DOC_SCHEMA, tuples2)
    assert o2.check('...', 'user', '*', 'viewer', 'document', 'd') is False
    # ...but each concrete user is still individually a viewer.
    assert o2.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True
    assert o2.check('...', 'user', 'bob', 'viewer', 'document', 'd') is True


def test_no_instance_leak_oracle():
    # bob granted directly; alice (a fellow user instance) must NOT inherit it.
    tuples = [t('...', 'user', 'bob', 'viewer', 'document', 'd')]
    o = Oracle(PUBLIC_DOC_SCHEMA, tuples)
    assert o.check('...', 'user', 'bob', 'viewer', 'document', 'd') is True
    assert o.check('...', 'user', 'alice', 'viewer', 'document', 'd') is False


# ---------------------------------------------------------------------------
# 2. [group:*#member] with strict forall=>exists (0 groups => False, 1 => True)
# ---------------------------------------------------------------------------

GROUP_STAR_SCHEMA = '''
model
  schema 1.1

type user

type group
  relations
    define member: [user]

type document
  relations
    define viewer: [group#member, group:*#member]
'''


def test_group_any_member_zero_groups_false():
    # "members of ANY group" are viewers -- but there are NO groups.
    # Strict forall=>exists: with zero concrete instances, the implication is False.
    tuples = [t('member', 'group', '*', 'viewer', 'document', 'd')]
    o = Oracle(GROUP_STAR_SCHEMA, tuples)
    #   expand(document,d,viewer): direct tuple subject group:*#member ->
    #     markers={(group,'member')}; s_pred='member'!='...' so union over
    #     universe(group). universe(group) has NO concrete group (only '*'), and the
    #     query mentions user:alice + document:d -> universe(group)=∅ -> no users.
    #   check(alice): (user,alice) in users? no. (user,'...') in markers? no. -> FALSE
    assert o.check('...', 'user', 'alice', 'viewer', 'document', 'd') is False


def test_group_any_member_one_group_true():
    # Same grant, but now group g1 exists and alice is a member.
    tuples = [
        t('member', 'group', '*', 'viewer', 'document', 'd'),
        t('...', 'user', 'alice', 'member', 'group', 'g1'),
    ]
    o = Oracle(GROUP_STAR_SCHEMA, tuples)
    #   universe(group)={g1} now (g1 is an object in the membership tuple).
    #   expand(group,g1,member): tuple alice member g1 -> users={(user,alice)}.
    #   check(alice): (user,alice) in users -> TRUE
    assert o.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True
    # bob is NOT a member of g1, so bob is NOT a viewer.
    assert o.check('...', 'user', 'bob', 'viewer', 'document', 'd') is False


def test_group_any_member_ghost_group_probe_parity():
    # A ghost group's #member userset queried against the group:* grant: the marker
    # matches by shape alone, so ANY group's members (as a userset subject) match.
    tuples = [t('member', 'group', '*', 'viewer', 'document', 'd')]
    o = Oracle(GROUP_STAR_SCHEMA, tuples)
    #   check(subject=group:ghost#member): s_pred='member', s_name='ghost'
    #   -> (group,ghost,member) in usersets? no. (group,'member') in markers? YES -> TRUE
    assert o.check('member', 'group', 'ghost', 'viewer', 'document', 'd') is True


# ---------------------------------------------------------------------------
# 3. Object-wildcard hierarchy scenario
# ---------------------------------------------------------------------------

OBJECT_WILDCARD_SCHEMA = '''
model
  schema 1.1

type user

type folder
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent

type document
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
'''


def test_all_folders_grant_reaches_child_doc():
    # alice is a viewer of ALL folders (object wildcard folder:*), and f1 is the
    # parent of document d. So alice views d via "viewer from parent".
    tuples = [
        t('...', 'user', 'alice', 'viewer', 'folder', '*'),
        t('...', 'folder', 'f1', 'parent', 'document', 'd'),
    ]
    o = Oracle(OBJECT_WILDCARD_SCHEMA, tuples)
    #   expand(document,d,viewer): ttu(viewer,parent) -> tuple f1 parent d -> subject
    #     folder:f1 -> expand(folder,f1,viewer). matching_objects there = {f1,'*'};
    #     direct tuple "alice viewer folder:*" has object '*' in matching -> users={(user,alice)}.
    #   check(alice): TRUE
    assert o.check('...', 'user', 'alice', 'viewer', 'document', 'd') is True
    # bob was never granted anything -> FALSE
    assert o.check('...', 'user', 'bob', 'viewer', 'document', 'd') is False


def test_all_folders_grant_ghost_folder_probe3():
    # Ghost object under an all-grant: alice views a folder never mentioned anywhere.
    tuples = [t('...', 'user', 'alice', 'viewer', 'folder', '*')]
    o = Oracle(OBJECT_WILDCARD_SCHEMA, tuples)
    #   expand(folder,ghost,viewer): matching_objects={'ghost','*'}; folder:* grant
    #   object '*' matches -> users={(user,alice)} -> TRUE
    assert o.check('...', 'user', 'alice', 'viewer', 'folder', 'never_created') is True
    # And the intensional object-wildcard query itself is True.
    assert o.check('...', 'user', 'alice', 'viewer', 'folder', '*') is True


# ---------------------------------------------------------------------------
# Parser sanity (hedges the shared DSL reading directly)
# ---------------------------------------------------------------------------

def test_parse_schema_classification():
    rels = parse_schema('''
    type document
      relations
        define owner: [user]
        define viewer: [user, group#member] or owner or viewer from parent
    ''')
    owner = rels[('document', 'owner')]
    assert owner.has_direct is True
    assert owner.computed == []
    assert owner.ttu == []

    viewer = rels[('document', 'viewer')]
    assert viewer.has_direct is True                # [user, group#member]
    assert viewer.computed == ['owner']             # computed userset
    assert viewer.ttu == [('viewer', 'parent')]     # P from R2
