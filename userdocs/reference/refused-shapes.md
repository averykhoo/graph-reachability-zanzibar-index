# Refused schema shapes

zanzibar-index refuses some schemas and calls that look reasonable, because each one would
otherwise be run with a meaning other than the one written, would give the two evaluation
backends different answers, or would break a store. This page lists every documented
refusal, grouped by where it happens: while a schema text or a JSON model is parsed, while
the `object_wildcard_shapes` argument is checked, while the graph index's rules are built,
and in the set engine, the store and the graph index API.

Each entry says what is refused, why, what to write instead, and the exception raised. The
page is generated from the comments the code keeps beside each refusal, so it cannot drift
from the installed version.

Most schema refusals raise {py:exc}`zanzibar.SchemaError` (a `ValueError`) with a message
that says what is wrong. The entries that raise {py:exc}`zanzibar.ShapeNoLongerAccepted` are
shapes an earlier version accepted; that exception is a `SchemaError` subclass whose
`instead` attribute is the rewrite that keeps the meaning an older store was serving, and a
store whose saved schema uses such a shape raises {py:exc}`zanzibar.PersistedSchemaRefused`
when it is opened.

Plain syntax errors, such as an unclosed `[`, a missing `:` after a relation name, an empty
restriction list or a stray token, also raise `SchemaError`; the syntax they break is the
[grammar](schema-language.md#grammar). For the accepted language as a whole, see
[Schema language](schema-language.md) and its [JSON models](schema-language.md#json-models)
section; for a worked rewrite, see
[Rewrite a refused schema shape](../how-to/rewrite-refused-shape.md); for the wildcard forms
that have no OpenFGA counterpart, see
[Wildcard extensions beyond OpenFGA](../explanation/wildcard-extensions.md).

```{refused-shapes}
```
