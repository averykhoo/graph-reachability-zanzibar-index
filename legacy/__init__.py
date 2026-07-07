"""Superseded index generations, kept as runnable documentation.

v1 (in-memory closure) -> v2 (typed nodes) -> v3 (DB closure, with the documented
concurrency gap that index_v4 fixes). Don't build on these; index_v4 is the live
graph backend. Two small pieces are still imported by live code (v1's MultiSet,
v2's Node) -- that is the only reason this package is on the import path.
"""
