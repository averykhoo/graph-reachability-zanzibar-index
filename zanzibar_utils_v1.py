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


def parse_relation_rule(rule: str) -> tuple[list[tuple[str, str | None]], list[tuple[str, str]]]:
    """
    NOTE: WINDSURF WROTE THIS CODE
    Parse a single relation rule into direct assignments and from relations.
    Returns (direct_assignments, from_relations) where:
        - direct_assignments is list of (type, predicate) for direct type assignments
        - from_relations is list of (relation, from_relation) for 'X from Y' rules
    
    Examples:
        "[user]" -> ([(user, None)], [])
        "[user, domain#member]" -> ([(user, None), (domain, member)], [])
        "writer" -> ([(None, writer)], [])
        "owner from parent_folder" -> ([], [(owner, parent_folder)])
    """
    direct_assignments = []
    from_relations = []

    # Handle 'X from Y' format
    if ' from ' in rule:
        relation, from_relation = rule.strip().split(' from ')
        from_relations.append((relation.strip(), from_relation.strip()))
        return direct_assignments, from_relations

    # Handle direct type assignments [type1, type2#relation]
    if rule.startswith('['):
        subjects = rule[1:].split(']')[0].split(',')
        for subject in subjects:
            subject = subject.strip()
            if '#' in subject:
                # Handle type#relation format
                subject_type, subject_predicate = subject.split('#')
                direct_assignments.append((subject_type.strip(), subject_predicate.strip()))
            else:
                # Handle direct type assignment
                direct_assignments.append((subject.strip(), None))
    else:
        # Handle single relation reference (e.g., "writer")
        direct_assignments.append((None, rule.strip()))

    return direct_assignments, from_relations


def parse_openfga_schema(schema: str) -> RuleSet:
    """
    NOTE: WINDSURF WROTE THIS CODE
    Parse an OpenFGA schema string and generate a RuleSet.
    
    Example schema:
    model
      schema 1.1
    
    type folder
      relations
        define owner: [user, domain#member] or owner from parent_folder
        define viewer: [user] or writer or viewer from parent_folder
    """
    rules_and_filters = []
    current_type = None

    for line in schema.strip().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Handle indentation by counting leading spaces
        indent = len(line) - len(line.lstrip())
        line = line.lstrip()

        if line.startswith('model'):
            continue
        elif line.startswith('schema'):
            continue
        elif line.startswith('type '):
            current_type = line.split(' ', 1)[1].strip()
        elif line.startswith('relations'):
            continue
        elif line.startswith('define '):
            if not current_type:
                raise ValueError("Relation definition without type context")

            # Parse relation definition
            # Format: define relation_name: [...] or other_relation or relation from other_relation
            relation_def = line[7:].strip()  # Remove 'define '
            relation_name, relation_rules = relation_def.split(':', 1)
            relation_name = relation_name.strip()

            # Split on 'or' and process each rule
            for rule in relation_rules.strip().split(' or '):
                rule = rule.strip()
                direct_assignments, from_relations = parse_relation_rule(rule)

                # Add filters for direct type assignments
                for subject_type, subject_predicate in direct_assignments:
                    if subject_type is None:
                        # This is a relation reference (e.g., "writer")
                        rules_and_filters.append(
                            Rule(
                                RelationalTriplePattern(
                                    relation=subject_predicate,
                                    object_type=current_type
                                ),
                                RelationalTriplePattern(
                                    relation=relation_name,
                                    object_type=current_type
                                )
                            )
                        )
                    else:
                        # This is a type assignment (e.g., "[user]" or "domain#member")
                        rules_and_filters.append(
                            Filter(RelationalTriplePattern(
                                subject_predicate=subject_predicate or Ellipsis,
                                subject_type=subject_type,
                                relation=relation_name,
                                object_type=current_type
                            ))
                        )

                # Add rules for 'from' relations
                for relation, from_relation in from_relations:
                    # Create a rule that says: if X has relation R with Y's from_relation,
                    # then X has relation with Y
                    rules_and_filters.append(
                        Rule(
                            RelationalTriplePattern(
                                relation=relation,
                                object_type=current_type,
                                object_predicate=from_relation
                            ),
                            RelationalTriplePattern(
                                relation=relation_name,
                                object_type=current_type
                            )
                        )
                    )

    return RuleSet(rules_and_filters)


def generate_example_ruleset() -> RuleSet:
    """
    NOTE: WINDSURF WROTE THIS CODE
    Generate a RuleSet from the Google Drive example OpenFGA schema.
    """
    schema = '''
    model
      schema 1.1

    type user

    type domain
      relations
        define member: [user]

    type folder
      relations
        define can_share: writer
        define owner: [user, domain#member] or owner from parent_folder
        define parent_folder: [folder]
        define viewer: [user, domain#member] or writer or viewer from parent_folder
        define writer: [user, domain#member] or owner or writer from parent_folder

    type document
      relations
        define can_share: writer
        define owner: [user, domain#member] or owner from parent_folder
        define parent_folder: [folder]
        define viewer: [user, domain#member] or writer or viewer from parent_folder
        define writer: [user, domain#member] or owner or writer from parent_folder
    '''
    return parse_openfga_schema(schema)


# NOTE: WINDSURF WROTE THIS CODE
if __name__ == '__main__':
    # Test the parser with the Google Drive example
    ruleset = generate_example_ruleset()

    # Test some example triples
    test_triples = [
        # Direct user ownership
        RelationalTriple(Entity('user', 'alice'), 'owner', Entity('folder', 'root')),
        # Domain member ownership
        RelationalTriple(Entity('domain', 'example.com'), 'member', Entity('user', 'bob')),
        # Parent folder inheritance
        RelationalTriple(Entity('folder', 'subfolder'), 'parent_folder', Entity('folder', 'root')),
        # Writer implies viewer
        RelationalTriple(Entity('user', 'charlie'), 'writer', Entity('document', 'doc1')),
    ]

    for triple in test_triples:
        print(f"\nProcessing: {triple}")
        for result in ruleset.apply(triple):
            print(f"Generated: {result}")

if __name__ == '__main__':
    # https://github.com/openfga/sample-stores/blob/main/stores/github/model.fga
    # (the openfga dsl is slightly nicer than the spicedb dsl)
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
