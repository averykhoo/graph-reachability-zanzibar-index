"""zanzibar: Zanzibar-style relationship/permission evaluation.

Two backends with identical semantics and opposite cost models:

* `zanzibar.setengine` -- stores raw tuples, evaluates on the fly with bitmap algebra;
* `zanzibar.graphindex` -- materializes the transitive closure, O(1) `check`;

sharing the schema layer `zanzibar.schema`, and composed with a tuple log in
`zanzibar.connectedstore`. Deliberately imports nothing: import the subpackage
you need.
"""

__version__ = "0.0.1"
