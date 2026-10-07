"""The schema layer shared by both backends: the OpenFGA-style DSL parser and AST, the
schema -> graph-index rule compiler (incl. boolean derived predicates), and the opt-in
scope reports.

Submodules, leaf first:

* `errors`        identifier validation and the shared error types
* `syntax`        the schema AST and walkers over it
* `rules`         the triple / pattern / rule data model, `SchemaInfo`, `RuleSet`
* `parser`        tokenizer + recursive-descent parser and the parse-time refusals
* `boolean`       boolean derived-predicate compilation
* `compiler`      `compile_ruleset`, wildcard scope refusals, `parse_openfga_schema`
* `unparse`       `unparse_schema_ast`
* `json_frontend` the OpenFGA JSON front end
* `reports`       `w4_fragment_report` / `graph_admission_report`

This module re-exports the public names, so `from zanzibar.schema import X` keeps
working. It was one 3,300-line file (`zanzibar_utils_v1.py`) until TK120 (2026-10-06).
"""
from .errors import (
    AdmissionRejected,
    ClosureFanoutExceeded,
    CyclicDerivedDependency,
    DoublyBridgedShapeError,
    IDENTIFIER_CHARSET,
    IndexResourceLimit,
    PathCountExceeded,
    UnsupportedByGraphIndex,
    is_valid_identifier,
    validate_node_identifiers,
    validate_store_id,
    validate_write_identifiers,
)
from .syntax import (
    Computed,
    Direct,
    Exclusion,
    Expr,
    Intersection,
    Restriction,
    SchemaAST,
    TTU,
    Union,
)
from .rules import (
    Entity,
    EntityPattern,
    Filter,
    RelationalTriple,
    RelationalTriplePattern,
    RewriteFilter,
    Rule,
    RuleSet,
    SchemaInfo,
    norm_pred,
    parse_relation_rule,
    replace_relation,
)
from .parser import (
    parse_schema_ast,
)
from .boolean import (
    CompiledBooleans,
    DependentEdge,
    DerivedFamily,
    LeafFamily,
    LeafSpec,
    PClosureLeaf,
    PDerivedComputed,
    PDerivedTTU,
    PDerivedUserset,
    PExclusion,
    PIntersection,
    PUnion,
    Plan,
    compile_boolean_schema,
    compute_taint,
)
from .compiler import (
    UnprovenExtensionWarning,
    compile_ruleset,
    derive_schema_info,
    parse_openfga_schema,
    schema_filters,
    unproven_extensions,
    wildcard_userset_restriction_shapes,
)
from .unparse import (
    unparse_schema_ast,
)
from .json_frontend import (
    openfga_json_to_dsl,
    parse_openfga_json,
)
from .reports import (
    GRAPH_ADMISSION_REPORTED_FIELDS,
    GraphAdmissionReport,
    W4FragmentReport,
    W4_FRAGMENT_FIELDS,
    graph_admission_report,
    w4_fragment_report,
)

# Private helpers that the test and conformance suites reach through this module;
# re-exported for them, NOT part of the API.
from .syntax import _iter_directs  # noqa: F401
from .parser import _parse_schema_ast_unchecked  # noqa: F401
from .boolean import _member_types, _plan_leaves  # noqa: F401

__all__ = [
    'AdmissionRejected',
    'ClosureFanoutExceeded',
    'CompiledBooleans',
    'Computed',
    'CyclicDerivedDependency',
    'DependentEdge',
    'DerivedFamily',
    'Direct',
    'DoublyBridgedShapeError',
    'Entity',
    'EntityPattern',
    'Exclusion',
    'Expr',
    'Filter',
    'GRAPH_ADMISSION_REPORTED_FIELDS',
    'GraphAdmissionReport',
    'IDENTIFIER_CHARSET',
    'IndexResourceLimit',
    'Intersection',
    'LeafFamily',
    'LeafSpec',
    'PClosureLeaf',
    'PDerivedComputed',
    'PDerivedTTU',
    'PDerivedUserset',
    'PExclusion',
    'PIntersection',
    'PUnion',
    'PathCountExceeded',
    'Plan',
    'RelationalTriple',
    'RelationalTriplePattern',
    'Restriction',
    'RewriteFilter',
    'Rule',
    'RuleSet',
    'SchemaAST',
    'SchemaInfo',
    'TTU',
    'Union',
    'UnprovenExtensionWarning',
    'UnsupportedByGraphIndex',
    'W4FragmentReport',
    'W4_FRAGMENT_FIELDS',
    'compile_boolean_schema',
    'compile_ruleset',
    'compute_taint',
    'derive_schema_info',
    'graph_admission_report',
    'is_valid_identifier',
    'norm_pred',
    'openfga_json_to_dsl',
    'parse_openfga_json',
    'parse_openfga_schema',
    'parse_relation_rule',
    'parse_schema_ast',
    'replace_relation',
    'schema_filters',
    'unparse_schema_ast',
    'unproven_extensions',
    'validate_node_identifiers',
    'validate_store_id',
    'validate_write_identifiers',
    'w4_fragment_report',
    'wildcard_userset_restriction_shapes',
]
