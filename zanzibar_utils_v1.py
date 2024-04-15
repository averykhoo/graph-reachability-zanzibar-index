from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class Entity:
    type: str
    name: str


@dataclass(frozen=True, slots=True, order=True)
class RelationalTriple:
    subject: Entity
    relation: str
    object: Entity

    # needed for adding group:a#member is a writer of document:b
    subject_predicate: str | None = None


@dataclass(frozen=True, slots=True, order=True)
class EntityPattern:
    type: str | None = None
    name: str | None = None

    def match(self, entity: Entity) -> bool:
        if not isinstance(entity, Entity):
            raise TypeError(f'expected an `Entity`, got {entity!r}')
        if self.type is not None and self.type != entity.type:
            return False
        if self.name is not None and self.name != entity.name:
            return False
        return True

    def replace(self, entity: Entity) -> Entity:
        if not isinstance(entity, Entity):
            raise TypeError(f'expected an `Entity`, got {entity!r}')
        return Entity(type=self.type or entity.type,
                      name=self.name or entity.name)


@dataclass(frozen=True, slots=True, order=True)
class RelationalTriplePattern:
    subject: EntityPattern | None = None
    relation: str | None = None
    object: EntityPattern | None = None
    subject_predicate: str | None = None

    def match(self, relational_triple: RelationalTriple) -> bool:
        if not isinstance(relational_triple, RelationalTriple):
            raise TypeError(f'expected a `RelationalTriple`, got {relational_triple!r}')
        if self.subject is not None and not self.subject.match(relational_triple.subject):
            return False
        if self.relation is not None and self.relation != relational_triple.relation:
            return False
        if self.object is not None and not self.object.match(relational_triple.object):
            return False
        if self.subject_predicate is not None and self.subject_predicate != relational_triple.subject_predicate:
            return False
        if self.subject_predicate is None and relational_triple.subject_predicate is not None:
            raise NotImplemented  # need another way to match any
        return True

    def replace(self, relational_triple: RelationalTriple) -> RelationalTriple:
        if not isinstance(relational_triple, RelationalTriple):
            raise TypeError(f'expected a `RelationalTriple`, got {relational_triple!r}')
        _subject = self.subject.replace(relational_triple.subject) if self.subject else relational_triple.subject
        _object = self.object.replace(relational_triple.object) if self.object else relational_triple.object
        return RelationalTriple(subject=_subject,
                                relation=self.relation or relational_triple.relation,
                                object=_object)


@dataclass(frozen=True, slots=True, order=True)
class Rule:
    if_pattern: RelationalTriplePattern
    then_pattern: RelationalTriplePattern

    def apply(self, relational_triple: RelationalTriple) -> RelationalTriple | None:
        if self.if_pattern.match(relational_triple):
            return self.then_pattern.replace(relational_triple)


@dataclass
class RuleSet:
    rules: list[Rule]

    def apply(self, relational_triple: RelationalTriple):
        yield relational_triple
        for rule in self.rules:
            if (_result := rule.apply(relational_triple)) is not None:
                yield _result


if __name__ == '__main__':
    rt1 = RelationalTriple(Entity('user', 'A'), 'admin', Entity('group', 'X'))
    rt2 = RelationalTriple(Entity('user', '*'), 'member', Entity('group', 'X'))

    rules = RuleSet([
        Rule(RelationalTriplePattern(EntityPattern('user'), 'admin', EntityPattern('group')),
             RelationalTriplePattern(relation='writer', object=EntityPattern('asdf')))
    ])

    print(list(rules.apply(rt1)))
    print(list(rules.apply(rt2)))
