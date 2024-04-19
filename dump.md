

* causality
* correctness / consistency
* generality / expressiveness
* perforamnce
* (real) availability
* multi-tenancy
* cross-namespace relations?
* shared tuples / state?

* conditional transition
* default condition exists?
* acyclic check?

```mermaid
flowchart LR
    ns["`namespace
         - schema
         - types`"]

    g["`graph
        - models`"]
    ns-->|model rewrite
          - ns
          - relations
          - dag|g
    g-->|self-update tuples?|g
    i["`indexes
        - from_node
        - to_node
        - entites, entity relatinos
        - only really need to index entity -> er, the rest can be slower?
        - mafsa something`"]
    g-->|zookie?, reachability|i
    ai[acl index + lookup-reverse index]
    i-->ai
```

* `*` as special entity?
* check twice, lookup twice, reverse lookup
* 

