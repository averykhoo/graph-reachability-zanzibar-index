from dataclasses import dataclass
from pprint import pprint
from types import EllipsisType

from index_v2 import Node


@dataclass(frozen=True, slots=True, order=True, unsafe_hash=True)
class Entity:
    type: str
    name: str

    @property
    def wildcard(self):
        return self.name == '*'

    def __str__(self):
        return f'{self.type}:{self.name}'


@dataclass(frozen=True, unsafe_hash=True, order=True, slots=True)
class NodeV2(Node):
    type: str
    name: str
    predicate: str | EllipsisType


@dataclass(frozen=True, slots=True, order=True, unsafe_hash=True)
class RelationalTriple:
    subject: Entity
    relation: str
    object: Entity

    # needed for adding group:a#member is a writer of document:b
    subject_predicate: str | EllipsisType = Ellipsis

    def __str__(self):
        # follows zanzibar paper
        subject_predicate = '...' if self.subject_predicate is Ellipsis else self.subject_predicate
        return f'{self.object}#{self.relation}@{self.subject}#{subject_predicate}'

    @property
    def node_from(self):
        return NodeV2(type=self.subject.type,
                      name=self.subject.name,
                      predicate=self.subject_predicate)

    @property
    def node_to(self):
        return NodeV2(type=self.object.type,
                      name=self.object.name,
                      predicate=self.relation)


@dataclass(frozen=True, slots=True, order=True, kw_only=True)
class EntityPattern:
    type: str | None = None
    name: str | None = None

    @property
    def wildcard(self):
        return self.name == '*'

    def match(self, entity: Entity) -> bool:
        if not isinstance(entity, Entity):
            raise TypeError(f'expected an `Entity`, got {entity!r}')
        if self.type is not None and self.type != entity.type:
            return False
        if self.name is not None and self.name != entity.name:
            return False
        if self.wildcard != entity.wildcard:
            return False
        return True

    def replace(self, entity: Entity) -> Entity:
        if not isinstance(entity, Entity):
            raise TypeError(f'expected an `Entity`, got {entity!r}')
        return Entity(type=self.type or entity.type,
                      name=self.name or entity.name)


@dataclass(frozen=True, slots=True, order=True, kw_only=True)
class RelationalTriplePattern:
    subject_predicate: str | EllipsisType | None = None
    subject_type: str | None = None
    subject_name: str | None = None
    relation: str | None = None
    object_type: str | None = None
    object_name: str | None = None

    @property
    def subject(self):
        return EntityPattern(type=self.subject_type, name=self.subject_name)

    @property
    def object(self):
        return EntityPattern(type=self.object_type, name=self.object_name)

    def match(self, relational_triple: RelationalTriple) -> bool:
        if not isinstance(relational_triple, RelationalTriple):
            raise TypeError(f'expected a `RelationalTriple`, got {relational_triple!r}')
        if self.subject_predicate is not None and self.subject_predicate != relational_triple.subject_predicate:
            return False
        if self.subject is not None and not self.subject.match(relational_triple.subject):
            return False
        if self.relation is not None and self.relation != relational_triple.relation:
            return False
        if self.object is not None and not self.object.match(relational_triple.object):
            return False
        return True

    def replace(self, relational_triple: RelationalTriple) -> RelationalTriple:
        if not isinstance(relational_triple, RelationalTriple):
            raise TypeError(f'expected a `RelationalTriple`, got {relational_triple!r}')
        _pred = self.subject_predicate if self.subject_predicate else relational_triple.subject_predicate
        _subject = self.subject.replace(relational_triple.subject) if self.subject else relational_triple.subject
        _object = self.object.replace(relational_triple.object) if self.object else relational_triple.object
        return RelationalTriple(subject_predicate=_pred,
                                subject=_subject,
                                relation=self.relation or relational_triple.relation,
                                object=_object)


@dataclass(frozen=True, slots=True, order=True)
class Filter:
    if_pattern: RelationalTriplePattern

    def apply(self, relational_triple: RelationalTriple) -> bool:
        return self.if_pattern.match(relational_triple)


@dataclass(frozen=True, slots=True, order=True)
class Rule:
    if_pattern: RelationalTriplePattern
    then_pattern: RelationalTriplePattern | None

    def apply(self, relational_triple: RelationalTriple) -> RelationalTriple | None:
        if self.if_pattern.match(relational_triple):
            return self.then_pattern.replace(relational_triple)


@dataclass
class RuleSet:
    rules_and_filters: list[Rule | Filter]

    def apply(self, relational_triple: RelationalTriple):
        unprocessed = set()
        for rule in self.rules_and_filters:
            if not isinstance(rule, Filter):
                continue
            if rule.apply(relational_triple):
                unprocessed.add(relational_triple)
                break
        else:
            return

        processed = set()
        while unprocessed:
            relational_triple = unprocessed.pop()
            if relational_triple in processed:
                continue
            yield relational_triple

            processed.add(relational_triple)
            for rule in self.rules_and_filters:
                if not isinstance(rule, Rule):
                    continue
                if (_result := rule.apply(relational_triple)) is not None:
                    unprocessed.add(_result)


if __name__ == '__main__':
    # https://github.com/openfga/sample-stores/blob/main/stores/github/model.fga
    rules_and_filters = RuleSet([
        # model
        #   schema 1.1

        # type user

        # type team
        #   relations
        #     define member: [user, team#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='member', object_type='team')),

        # type organization
        #   relations
        #     define owner: [user]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='owner', object_type='organization')),
        #     define member: [user] or owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='member', object_type='organization')),
        Rule(RelationalTriplePattern(relation='owner', object_type='organization'),
             RelationalTriplePattern(relation='member', object_type='organization')),
        #     define repo_admin: [user, organization#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='repo_admin', object_type='organization')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='organization',
                                       relation='repo_admin', object_type='organization')),
        #     define repo_writer: [user, organization#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='repo_writer', object_type='organization')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='organization',
                                       relation='repo_writer', object_type='organization')),
        #     define repo_reader: [user, organization#member]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='repo_reader', object_type='organization')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='organization',
                                       relation='repo_reader', object_type='organization')),

        # type repo
        #   relations
        #     define owner: [organization]
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                       relation='owner', object_type='repo')),
        #     define admin: [user, team#member] or repo_admin from owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='admin', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='admin', object_type='repo')),
        Rule(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                     relation='owner', object_type='repo'),
             RelationalTriplePattern(subject_predicate='repo_admin', relation='admin')),
        #     define maintainer: [user, team#member] or admin
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='maintainer', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='maintainer', object_type='repo')),
        Rule(RelationalTriplePattern(relation='admin', object_type='repo'),
             RelationalTriplePattern(relation='maintainer', object_type='repo')),
        #     define writer: [user, team#member] or maintainer or repo_writer from owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='writer', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='writer', object_type='repo')),
        Rule(RelationalTriplePattern(relation='maintainer', object_type='repo'),
             RelationalTriplePattern(relation='writer', object_type='repo')),
        Rule(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                     relation='owner', object_type='repo'),
             RelationalTriplePattern(subject_predicate='repo_writer', relation='writer')),
        #     define triager: [user, team#member] or writer
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='triager', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='triager', object_type='repo')),
        Rule(RelationalTriplePattern(relation='writer', object_type='repo'),
             RelationalTriplePattern(relation='triager', object_type='repo')),
        #     define reader: [user, team#member] or triager or repo_reader from owner
        Filter(RelationalTriplePattern(subject_predicate=..., subject_type='user',
                                       relation='reader', object_type='repo')),
        Filter(RelationalTriplePattern(subject_predicate='member', subject_type='team',
                                       relation='reader', object_type='repo')),
        Rule(RelationalTriplePattern(relation='triager', object_type='repo'),
             RelationalTriplePattern(relation='reader', object_type='repo')),
        Rule(RelationalTriplePattern(subject_predicate=..., subject_type='organization',
                                     relation='owner', object_type='repo'),
             RelationalTriplePattern(subject_predicate='repo_reader', relation='reader')),
    ])

    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('user', 'A'), 'admin', Entity('repo', 'X')))))
    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('user', 'A'), 'owner', Entity('team', 'X')))))
    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('organization', 'O'), 'owner', Entity('team', 'X')))))
    pprint(list(rules_and_filters.apply(RelationalTriple(Entity('organization', 'O'), 'owner', Entity('repo', 'X')))))

    print(RelationalTriple(subject=Entity(type='organization', name='O'),
                           relation='admin',
                           object=Entity(type='repo', name='X'),
                           subject_predicate='repo_admin',
                           ).node_from)
    print(RelationalTriple(subject=Entity(type='organization', name='O'),
                           relation='admin',
                           object=Entity(type='repo', name='X'),
                           subject_predicate='repo_admin',
                           ).node_to)
