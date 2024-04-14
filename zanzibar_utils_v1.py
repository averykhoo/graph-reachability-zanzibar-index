from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Entity:
    type: str
    name: str


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class RelationalTriple:
    subject: Entity
    relation: str
    object: Entity


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
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


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class RelationalTriplePattern:
    subject: EntityPattern | None = None
    relation: str | None = None
    object: EntityPattern | None = None

    def match(self, relational_triple: RelationalTriple) -> bool:
        if not isinstance(relational_triple, RelationalTriple):
            raise TypeError(f'expected a `RelationalTriple`, got {relational_triple!r}')
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
        _subject = None if self.subject is None else self.subject.replace(relational_triple.subject)
        _object = None if self.object is None else self.object.replace(relational_triple.object)
        return RelationalTriple(subject=_subject,
                                relation=self.relation or relational_triple.relation,
                                object=_object)
