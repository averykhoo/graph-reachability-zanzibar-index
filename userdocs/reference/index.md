# Reference

Exact descriptions of what the library accepts and does: the Python API, the schema
language, the tuple-string format, the exceptions, the configuration knobs, the database
tables and the supported environments. These pages state facts and do not teach; for a
guided start read the [first tutorial](../tutorials/first-check.md), and for the reasons
behind a behaviour see the [explanation pages](../explanation/index.md).

| Page | What it covers |
|---|---|
| [Python API](api/index.md) | Every public class, function and constant, mostly generated from the docstrings. |
| [Schema language](schema-language.md) | The accepted subset of the OpenFGA modelling language. |
| [Refused schema shapes](refused-shapes.md) | Every shape the parser refuses, why, and what to write instead. |
| [Tuple strings and identifiers](tuple-strings.md) | The `"type:name#relation"` format and the identifier character set. |
| [Exceptions](exceptions.md) | The exception hierarchy (rooted at `ZanzibarError`, plus `InvariantViolation`) and the one warning. |
| [Configuration](configuration.md) | Environment variables and `Store` keyword arguments. |
| [Database tables](tables.md) | The `zanzibar_*` tables the library creates and owns. |
| [Supported environments](environments.md) | Python versions, databases, isolation levels. |
| [Changelog](changelog.md) | What changed in each release. |

```{toctree}
:maxdepth: 1
:hidden:

api/index
schema-language
refused-shapes
tuple-strings
exceptions
configuration
tables
environments
changelog
```
