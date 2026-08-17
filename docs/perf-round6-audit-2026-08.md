# Perf round 6 — the 2026-08-15 two-backend audit (CANDIDATE worklist)

> **Status: CANDIDATES. Nothing here is landed. ALL EIGHTEEN are now MEASURED
> (2026-08-17)** — ten recommended to land in a stated order, five declined on an upper
> bound, three unreachable by any benchmarked workload.
> This is the raw material for reopening the perf arc that closed at round 5.
> Per the reopening rule in [`perf-next-round.md`](perf-next-round.md), **every
> item still needs a motivating measurement** (`benchmarks/stmt_bench.py` /
> `scale_bench` / a fresh profile) before it is worth landing — the audit
> confirms the code *does* the inefficient thing, not that the inefficiency
> *dominates* any real workload. Round 5's lesson stands: two plausible
> candidates were declined on a fresh profile.
>
> When this round closes, retire this file verbatim to
> `docs/history/perf-round6-2026-08.md`, following rounds 3–5.

## Measured — the 2026-08-17 motivating-measurement pass (all 18)

Full numbers, method, box conditions and the two honest limits (in-memory SQLite;
cProfile depression) are in
[`benchmarks/results/R6_PROFILE_2026-08-17.md`](../benchmarks/results/R6_PROFILE_2026-08-17.md).
Instruments: `benchmarks/profile_r6.py` (read paths) and `benchmarks/profile_r6_write.py`
(write / cascade / bulk / space) — cProfile plus per-claim counters over the reviewed
`scale_bench` datasets. **Nothing was implemented.**

**Land in this order:** `R6-10` → `R6-6` → `R6-11` → `R6-5` → `R6-4` → `R6-9` → `R6-18` →
`R6-16` (co-design with `R6-7`/`R6-8`) → `R6-7`+`R6-8` → `R6-1` (prototype first).
**Declined on an upper bound:** `R6-15` (0.9%), `R6-12` (1.00×), `R6-14` (5.0%), `R6-2`
(24% of a non-bottleneck). **Unreachable by any benchmarked workload:** `R6-3` = `R6-17`,
and its bulk twin `R6-13` (0 calls each).

Read-path verdicts:

| id | verdict | the measurement that decided it |
|---|---|---|
| `R6-6` | **MOTIVATED — land first** | exactly **4.00** `node_v4` point SELECTs per `check` + 0.75 edge; the fix takes the op **4.75 → 1.75 statements (−63% round trips)**, no Lean change |
| `R6-5` | **MOTIVATED — promoted** | **22,410 ORM rows built (32.7% of profiled time)** to read 3–4 columns; `lookup_reachable` + `_classify_ids` = **52%** of boolean lookup. Filed medium, measured as the largest single block |
| `R6-4` | **MOTIVATED** | **30.1%** of every boolean lookup, **193 `json.loads` per lookup** over only **100** residue rows — and the scan is O(#derived objects), so the share grows with the store |
| `R6-1` | **MOTIVATED — but prototype first** | **74.1 `check` calls per `lookup`, 91.4%** of lookup wall time; `lookup` degrades 2.5× from scale 400→1600 while `check` stays flat. ⚠ This proves `check` DOMINATES, not that sharing ELIMINATES — the redundant fraction is unmeasured, and the naive fix is a correctness bug (see the entry) |
| `R6-2` | **NOT MOTIVATED — recommend decline** | algebra is **24.2%** of a surface already **13–30× faster per call than `lookup`**; the feared quadratic star-population re-materialization **did not appear** (roaring `_starpop` ~1 µs even at 20,000 population), and the fix costs a Lean model change + fuzz |
| `R6-3` | **UNREACHED** | `_instances_of_type` called **0 times** across both set-engine profiles, gdrive's object-wildcard shapes included. Round-3 N7's "not exercised by profiled workloads" is now measured rather than assumed; it needs a `T:*#P` workload before it needs a patch |

Write / cascade / bulk / space verdicts:

| id | verdict | the measurement that decided it |
|---|---|---|
| `R6-10` | **MOTIVATED — the round's headline** | **59.8%** of incremental boolean write+cascade time in one function (16,690 calls). Largest measured cost anywhere in round 6 |
| `R6-11` | **MOTIVATED — cheapest** | **240** residue-cache scopes for **30** reconciles: built and torn down **8× per reconcile**; the digest's one-line scoping change |
| `R6-9` | **MOTIVATED** | **4.51** `_db_node` point SELECTs per raw write, **17.7%** of a non-boolean build (context: **34.62 SQL statements per raw write** overall) |
| `R6-16` | **MOTIVATED — but co-design** | exactly **1.00 outbox row per closure edge** on a schema with **no derived relations** (14,868 rows, nothing consumes them, manual prune only). ⚠ paranoia FULL uses the outbox as its worklist on ALL schemas — gate emission and its consumer together |
| `R6-18` | **MOTIVATED** | direct layout A/B on file-backed VACUUMed SQLite: **53.1% smaller** (57.7 → 27.0 bytes/row at 200k rows) — the closure table is 2.1× larger than it needs to be |
| `R6-7` | **MOTIVATED — gate-only** | **20.7%** of a paranoid build, and the decisive one: per-commit cost **14.14×** from first to last quartile over 336 commits. `check_invariants` overall is **64.1%**. `PARANOIA_FULL` never runs in production, but it IS the `tests/` default |
| `R6-8` | **MOTIVATED — gate-only** | **11.0%** of a paranoid build. Fix must test BFS *neighbours*, not the seen-set, or `(s,s)` reads reachable on corrupt state |
| `R6-14` | **NOT MOTIVATED** | **5.0%** ceiling across 221,460 individually-cheap calls |
| `R6-12` | **NOT MOTIVATED** | **1.00×** intra-run re-reconcile; worst single cascade = 1 call. Needs a fan-out write to exercise at all |
| `R6-15` | **NOT MOTIVATED — refuted by ceiling** | the entire topo sort is **0.9%** of a bulk build; a perfect heapq frontier cannot beat that |
| `R6-13` | **UNREACHED** | **0 calls** though the bulk path plainly ran — the bulk twin of `R6-3`, needs the same star/wildcard shapes |
| `R6-17` | duplicate of `R6-3` | settled by `R6-3`: unreached |

**Unfiled finding:** `bulk_backfill._reconcile_subject_edge` is **25.3%** of a bulk build
and belongs to no candidate. It deserves its own id, not absorption into one of these.

⚠ **THREE instrument corrections are recorded with this pass, and they matter more than the
verdicts they changed.** (1) The first `R6-2` probe used the wide/star schema and reported a
clean `NOT MOTIVATED` while returning **0 members** and running **2 unions per expand** — on
a star-CLOSED relation the per-element fold the finding is about never executes. (2) The
first cascade probe profiled `build_graph`, which bootstraps via `backfill()` — the OFFLINE
path — so `reconcile_subject` ran **0 times** and `R6-11`/`R6-12` came back INCONCLUSIVE
against code that never executed. (3) The `R6-12` counter then aggregated across cycles and
printed **15.00× re-reconcile**, which was the same key touched by successive *writes*, not
the intra-run duplication `_bumped` is about; per-cascade counting gives **1.00×**. A probe
that exercises nothing still reports a verdict — the house failure mode, one level down from
the assurance checks `docs/sabotage-procedure.md` covers.

## Provenance / method

Produced 2026-08-15 by a 24-agent, two-phase workflow audit (run `wf_162392d4-5d1`;
per-agent transcripts survive under
`~/.claude/projects/<this-project>/ee09a2de-413a-49e3-b662-746227cbda1c/subagents/workflows/wf_162392d4-5d1/`).

* **Phase 1 — six finder agents**, one per subsystem (set-engine lookup algebra;
  graph read path; graph write path; IVM cascade; bulk build; storage/compile +
  space), each required to QUOTE the inefficient code with line numbers and to
  skip anything already optimized.
* **Phase 2 — one adversarial verifier per finding**, instructed to REFUTE:
  re-read the cited lines; check the sketched fix preserves semantics (wildcard
  subjects/objects, star-closed `neg`/`stars`, boolean derived predicates,
  TTU-over-STORED-tuples, refcounts, the SetOps seam); check hot-path
  materiality; and grep `formal/CORRESPONDENCE.md` for Lean anchors on every
  touched symbol.
* Only each finder's **top 3 findings by filed impact** were verified (18 of 34).
  The 16 unverified leads are preserved in the appendix, clearly marked.

Result: **18 verified findings, 0 refuted** — but several impacts were
downgraded, several fix sketches were corrected, and one proposed fix was
outright REFUTED by counterexample while its finding stood (R6-1: the naive
shared-memo fix is a correctness bug; the two-tier design in its verdict is the
real fix). **Do not implement from titles alone — read each entry's verifier
corrections first.**

Everything under "The verified findings" and the appendix is the workflow's
structured output **verbatim** (evidence, fix sketches, verdicts, corrections,
Lean-impact notes). Only this header, the digest, and the R6-N ids are editorial.

## Rules that bind this list (from CLAUDE.md / perf-next-round.md)

* **Measurement first.** No item lands without a motivating measurement; never
  run two heavy jobs concurrently; results go in `benchmarks/results/PERF_ANALYSIS.md`.
* **The Lean column.** A behavior-preserving micro-opt needs no Lean change; an
  optimization that changes a MODELED algorithm updates the Lean def + full
  phased gate + fuzz, or logs the gap in `formal/CORRESPONDENCE.md` §7. Per the
  per-item verdicts: **R6-2, R6-4 and R6-16 change modeled algorithms**; R6-1
  owes a §7 log entry even though forward lookup is unmodeled. Many other items
  touch ANCHORED symbols — renaming anything fails `verify.sh lean`.
* **Sabotage procedure.** R6-7 and R6-8 rewrite assurance checkers: per
  [`sabotage-procedure.md`](sabotage-procedure.md) the rewritten check must be
  sabotaged red before it is trusted. R6-4's and R6-16's fixes add/gate derived
  state that a checker consumes — same requirement.
* **Never edit a golden/oracle/snapshot to make an opt pass.**

## Editorial digest — a suggested order (2026-08-16)

**Quick wins** — behavior-preserving, no Lean model change, small blast radius:
**R6-6** (batch `check()`'s node resolution: up to 5 round trips → 2 on the
hottest read surface), **R6-11** (cascade-wide residue cache scope — one-line
scoping change, invalidation already exists), **R6-12** (dedupe `_bumped`),
**R6-9** (reuse the already-loaded `node_map` in the write tail), **R6-7**
(watermark-scope the I10 outbox check — removes the only per-commit cost term
that grows without bound; mostly gate/test wall-clock since production runs the
`residue` tier).

**The big three** — algorithmic wins needing real care: **R6-1** (two-tier
shared memo across set-engine `lookup`'s checks — the naive version is refuted,
read the verdict), **R6-4** (stop full-scanning residues on boolean graph
`lookup`; `ResidueRefV1` already exists and reads never use it; needs a stars
twin + bulk_build population + I6 extension), **R6-10** (reconcile-scoped memo
for the cascade's stored tupleset/userset enumerations — memoize at the
`_stored_tupleset_subjects` level only, see verdict).

**Space:** **R6-18** (EdgeV4 composite PK / WITHOUT ROWID — one whole B-tree off
the biggest table; no alembic, persistent PG needs a hand migration), **R6-16**
(gate outbox emission + retention — the biggest combined space+write win and the
most dangerous fix: paranoia FULL uses the outbox as its worklist on ALL
schemas; read the corrections before designing anything).

**Build:** **R6-13** / **R6-14** (bulk-backfill enumeration index + per-context
memo), **R6-15** (heapq topo frontier in both bulk topo sorts).

**Set-engine star path:** **R6-3** (= **R6-17**, found independently twice): the
`names_of_type` interner index — this is round 3's N7 deferral ("only with
measurement"), now with two independent confirmations. The release side must
DELETE zero-count entries or a ghost name becomes a false exists-witness.

**Gate-only:** **R6-8** (per-source instead of per-pair BFS in the delta
verifier) — already recorded as a known cost in `perf-next-round.md`'s minor
notes; worth it for gate wall-clock, not a production win.

**Cross-references to existing records:** R6-3/R6-17 = round-3 N7 deferral
(`docs/history/perf-round3-2026-07.md`). R6-8 = the "paranoia delta verifier
O(pairs × edges)" minor note in `perf-next-round.md`. R6-2 is ADJACENT to but
distinct from the confirmed `_starpop`/`ops.new()` dead-end (that was about
removing the copy primitive; R6-2 batches the fold and normalizes once).
R6-16's auto-prune half must respect the `prune_outbox` MIN-cursor contract.
Impact ratings in the table below are the FINDER's filing; the verifier
downgraded or re-scoped several (R6-2, R6-3, R6-7, R6-8, R6-9, R6-10, R6-12,
R6-13) — the corrections in each entry are the honest rating.

## Index of verified findings

| id | where | dimension | category | filed impact | algo Δ | verifier | title |
|---|---|---|---|---|---|---|---|
| R6-1 | `setengine/engine.py:1567` | set-lookup | lookup-speed | high | yes | CONFIRMED (high) | lookup re-runs check with a fresh memo per candidate: O(candidates x ... |
| R6-2 | `setengine/engine.py:1328` | set-lookup | repeated-work | high | yes | CONFIRMED (high) | expand left-folds ms.union, paying a full renormalization (incl. star... |
| R6-3 | `setengine/engine.py:1039` | set-lookup | lookup-speed | medium | no | CONFIRMED (high) | _instances_of_type scans the entire interner per type; repeated acros... |
| R6-4 | `index_v4/wildcard.py:792` | graph-read | lookup-speed | high | yes | CONFIRMED (high) | lookup on boolean schemas full-scans every residue row in the store a... |
| R6-5 | `index_v4/core.py:1175` | graph-read | lookup-speed | medium | no | CONFIRMED (high) | lookup_reachable/lookup_reverse fetch full Edge ORM rows, filter in P... |
| R6-6 | `index_v4/wildcard.py:647` | graph-read | lookup-speed | medium | no | CONFIRMED (high) | check() issues up to 4 sequential point SELECTs for node resolution b... |
| R6-7 | `index_v4/invariants.py:625` | graph-write | repeated-work | high | no | CONFIRMED (high) | I10 outbox-sanity check rescans the ENTIRE outbox on every commit (tw... |
| R6-8 | `index_v4/invariants.py:686` | graph-write | repeated-work | high | no | CONFIRMED (high) | Delta-scoped verifier runs one BFS per flipped PAIR instead of per di... |
| R6-9 | `index_v4/core.py:887` | graph-write | repeated-work | medium | no | CONFIRMED (high) | Write-tail refcount update re-SELECTs the two nodes it just batch-loa... |
| R6-10 | `index_v4/processor.py:159` | cascade | repeated-work | high | no | CONFIRMED (high) | check_fn re-enumerates stored tupleset/userset tuples via SQL once pe... |
| R6-11 | `index_v4/processor.py:1350` | cascade | repeated-work | medium | no | CONFIRMED (high) | Residue cache is torn down between every reconcile_subject call of a ... |
| R6-12 | `index_v4/processor.py:1112` | cascade | repeated-work | medium | no | CONFIRMED (high) | _bumped is an unde-duplicated list, so one reconcile can trigger the ... |
| R6-13 | `index_v4/bulk_backfill.py:463` | build | repeated-work | high | no | CONFIRMED (high) | Full node-set scan per check_fn evaluation: _instances_of_type is O(|... |
| R6-14 | `index_v4/bulk_backfill.py:476` | build | repeated-work | medium | no | CONFIRMED (high) | Stored tupleset/userset parent enumerations re-sorted and re-built fo... |
| R6-15 | `index_v4/bulk_build.py:129` | build | build-speed | medium | no | CONFIRMED (high) | Kahn topo sort re-sorts the entire frontier list after every node tha... |
| R6-16 | `index_v4/core.py:550` | space-compile | write-speed | high | yes | CONFIRMED (high) | Every closure flip writes a denormalized outbox row even on schemas w... |
| R6-17 | `setengine/engine.py:1039` | space-compile | lookup-speed | high | no | CONFIRMED (high) | SetEngine._instances_of_type rescans the entire interner per evaluati... *(dup of R6-3)* |
| R6-18 | `index_v4/models.py:72` | space-compile | space | medium | no | CONFIRMED (high) | EdgeV4 closure rows carry a dead surrogate PK and the store_id string... |

---

## The verified findings (verbatim from the audit)

### R6-1 — lookup re-runs check with a fresh memo per candidate: O(candidates x chain-depth) instead of O(reachable)

**`setengine/engine.py:1567`** · dimension: set-lookup · category: lookup-speed · filed impact: high · algorithm change (finder): yes · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> The reverse walk confirms every dequeued candidate with a full independent check: `if not self.check(s_pred, s_type, s_name, p, t, n):` (line 1567), and the marker loop before it runs one more full check per declared (type, relation): `for (t, rel) in self.ast: if self.check(s_pred, s_type, s_name, rel, t, '*')` (lines 1511-1513). Each check call allocates fresh caches at lines 1051-1052: `memo: dict[tuple[str, str, str], bool] = {}` / `inst_memo: dict[str, set[str]] = {}`. The subject and the store state are fixed for the whole lookup (reads never intern, no writes interleave), so 'does the subject reach (ot,on,rel)' is recomputed from scratch for every candidate — e.g. a 100-doc walk over one deep group#member chain re-evaluates the same chain 100 times. Notably `expand` already takes an external `memo` parameter (line 1214, used by lookup_reverse's machinery); `check` has no such parameter, which is exactly the asymmetry.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Add an internal check variant that accepts shared `memo` and `inst_memo` dicts (mirroring expand's existing `memo` parameter), and have `lookup` pass one pair across the marker loop and the entire walk. This is exact, not approximate: the Tarjan-lowlink guard already withholds provisional (cycle-tainted) answers from `memo`, so every entry that lands there is a final state-and-subject-determined boolean, and `stack`/`low` stay call-local (the stack is empty between _drive runs). `inst_memo` is likewise safe to share because the interner cannot mutate during a read. Turns the walk's confirmation cost from O(candidates x chain) into amortized O(reachable subgraph).

**Verifier reasoning (verbatim):**

> Verified in setengine/engine.py: check() allocates fresh memo/inst_memo per call (lines 1051-1052, no memo parameter in the signature) and lookup() calls it once per declared (type,relation) in the marker loop (1511-1513) plus once per dequeued candidate (1567) with zero sharing, so shared sub-chains are re-derived per candidate — the O(candidates x chain-depth) claim is literally true on a hot query surface. HOWEVER, the fix sketch's safety argument is refuted by counterexample: the Tarjan-lowlink guard DOES memoize a frame that is the root of its own cycle (depth 0, back-edge sets low=0, my_low>=depth holds at 1085-1086), and that entry is the root-context cycle-broken answer, not a root-independent truth. With non-monotone Exclusion, sat is non-compositional across roots. Concrete: schema `x: [user] but not y` / `y: [user] but not x` (CyclicDerivedDependency -> engine runs ruleset-less per lines 356-372, and _would_cycle refuses nothing at 944-948, so the cyclic state is constructible), tuples `user:u x doc:d`, `user:u y doc:d`. Fresh check(u,x,d)=False (memoizes (doc,d,x)=False) and fresh check(u,y,d)=False; but with the shared memo, check(u,y,d) = True AND NOT memo[False] = True — so the patched lookup would emit a result the per-candidate oracle (tests/test_lookup_oracle.py) refutes. The inefficiency is real and a more careful fix works, so is_real=true with the fix corrected as below. Also, the evidence's claim that expand's memo parameter is 'used by lookup_reverse's machinery' is false — lookup_reverse (line 1350) and every other caller in the repo call expand without memo.

**Verifier corrections / refinements (verbatim):**

> Fix must NOT share the memo unconditionally. Use a two-tier memo: promote an entry to the lookup-shared dict only when its frame's evaluation was fully cycle-clean (low stayed _INF, i.e. no in-stack hit anywhere in the subtree, and every memo entry it consulted was itself shared/clean); keep cycle-tainted entries — including my_low==depth roots, which the current guard memoizes — call-local. On every schema that compiles a RuleSet (untainted schemas and, since the P7 flip, ordinary boolean schemas), _would_cycle rejects data cycles at admission, so no in-stack hit can occur and clean-sharing equals full sharing — the claimed O(reachable) amortization is achieved where it matters; only decision-15 / cyclic-derived-dependency oracle-only schemas pay the call-local fallback. inst_memo sharing is safe but must stay scoped to the single lookup invocation (interner stable only within one read; N7 docstring, lines 1028-1035). Evidence correction: expand's memo parameter (line 1214) is currently dormant — no caller passes it, lookup_reverse calls expand bare — and it carries the same root-memoization hazard if ever shared across roots.

**Lean impact (verifier, verbatim):**

> SetEngine.check — CORRESPONDENCE.md §2 pins it answer-for-answer against SetEngine/Eval.lean::SetEngineModel.check (explicitly NOT an algorithm twin) and anchors the closures SetEngine.check.sat / .sat_expr / .direct_leaf / .member_via_usersets / .ttu_leaf, which verify.sh lean resolves; those anchors must keep resolving. Forward lookup itself is explicitly unmodeled (§7 P1/N17: "no modeled definition describes lookup's candidate generation"). No Lean definition change needed if standalone check answers are preserved; a §7 log entry is due per CLAUDE.md.

### R6-2 — expand left-folds ms.union, paying a full renormalization (incl. star-population materialization) per element

**`setengine/engine.py:1328`** · dimension: set-lookup · category: repeated-work · filed impact: high · algorithm change (finder): yes · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> ttu_expand accumulates per stored parent: `acc = ms.union(acc, (yield do(pt, pn, target)), ops, pop)` (1328) and even adds a single id via a full algebra op: `acc = ms.union(acc, ms.singleton_entity(fid, ops), ops, pop)` (1331); direct_expand does the same per userset member and per star instance (1308, 1315), plus a final `ms.union(local, acc, ops, pop)` (1317). Each `ms.union` (memberset.py:130-133) computes `_ext(a)`, `_ext(b)` and then `_normalize(...)` — and `_ext`/`_normalize` EACH call `_starpop` (memberset.py:109, 119), which unions the entire concrete population of every covered star shape (`for shape in stars: ops.update(acc, pop(shape))`, memberset.py:84-95). So once `acc` carries a star, every subsequent single-element union costs O(|population|), and the k-element fold is O(k x (|acc| + starpop)) with ~4 fresh set allocations + 2 freezes per step — quadratic accumulation on the expand/lookup_reverse hot path.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Fold with one mutable extensional accumulator plus a plain stars set, normalizing once at the end: for each operand m, `ext_acc |= _ext(m); stars_acc |= m.stars`, then a single `_normalize(ext_acc, stars_acc)`. This is provably byte-identical: `_normalize(E, S)` restores ext = E exactly (pos = E - starpop, neg = starpop - E), so union chains satisfy union(...union(empty,m1)...,mk) = normalize(U ext(mi), U stars(mi)) by induction. Expose it as e.g. `ms.union_all(iterable, ops, pop)` in memberset.py (keeping the algebra engine-independent), and use it in do_expr's Union arm, direct_expand and ttu_expand; singleton adds become `ext_acc.add(fid)`. Also fixes the smaller intra-op duplication (union computes starpop of a.stars and b.stars in _ext, then recomputes the merged starpop in _normalize). Since the MemberSet algebra is a modeled/spec'd algorithm (spec §4), treat as an algorithm change: check CORRESPONDENCE.md and re-run the memberset property suite + gate.

**Verifier reasoning (verbatim):**

> Every cited line checks out: engine.py ttu_expand (1328, 1331, 1333, 1336), direct_expand (1308, 1315, 1317) and do_expr's Union arm (1262) all left-fold ms.union; memberset.py union (130-133) calls _ext(a) + _ext(b) + _normalize, and _starpop runs three times per union (109 x2 via _ext, 119 via _normalize), each unioning the full concrete population of every covered star shape (84-95), plus ops.new(ext_set) copies and 2 freezes in _normalize. Once acc carries a star shape, every subsequent single-element union re-materializes acc's whole star population twice, making the k-element fold O(k x (|acc_ext| + starpop)) — genuinely quadratic accumulation with no existing mitigation (the do memo caches completed sub-expansions, not fold intermediates). The fix's byte-identity argument is sound: _normalize(E,S) restores ext=E exactly (pos ∪ (starpop−neg) = E, per the module's own documented recipe) and union stars-merge is a plain ∪, so fold(union) = single _normalize(⋃ext(mi), ⋃stars(mi)) by induction, valid because pop is stable during an expand (reads never intern or mutate node_sets). The sketch stays on the SetOps seam (ops primitives only). Hot path: expand is a per-query public surface (§6.3) and lookup_reverse (engine.py:1350) is expand + rendering; explicitly in the allowed hot-path list. algorithm_change=true is correct — the touched functions are Lean-modeled and the verify.sh lean phase pins their CORRESPONDENCE anchors.

**Verifier corrections / refinements (verbatim):**

> Scope the impact honestly: only expand/lookup_reverse are affected. check() uses the separate pointwise sat coroutine path and lookup() uses a check-confirmed reverse BFS — neither builds MemberSets, so the hottest surface (check) gains nothing; 'high' is fair for expand-heavy workloads (quadratic in stored-parent/instance fan-out with full star-population re-materialization per element), 'medium' overall. Fix nuances: (1) the fold's intermediate normalizations are semantically invisible (memo only stores completed do-frame results, which the batched version reproduces value-identically), but keep the Intersection arm's raw-first-child behavior untouched; (2) byte-identity relies on pop stability within one eval — holds today (expand never interns on read); state that as a precondition on union_all; (3) in direct_expand, fold local's ext (pos + its stars' populations) into the accumulator rather than special-casing, so the final ms.union(local, acc) collapses into the same single normalize; (4) singleton adds (1331) can indeed become plain ext_acc.add(fid) — singleton_entity's ext is exactly {fid}.

**Lean impact (verifier, verbatim):**

> Touches Lean-modeled symbols: formal/CORRESPONDENCE.md:197 maps SetEngine/MemberSet.lean::MemberSet with ::union (and ::_normalize/::_starpop/::_ext) to setengine/memberset.py; lines 198-200 map SetEngine/Eval.lean::SetEngineModel.expandDirect/expandTtu/expandStep/expandAux to SetEngine.expand.direct_expand/ttu_expand/do/do_expr; line 906 (parentMS) models the ttu star-arm union. A union_all + batched-fold rewrite changes the modeled expand algorithm, so it needs the Lean model updated (or a CORRESPONDENCE.md §7 gap entry) and the full phased gate re-run; the lean phase pins these exact anchors.

### R6-3 — _instances_of_type scans the entire interner per type; repeated across lookup's many check calls

**`setengine/engine.py:1039`** · dimension: set-lookup · category: lookup-speed · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> `names = {n for (kt, n, _p) in self.interner.key_of.values() if kt == t and n != '*'}` — a full scan of every interned key (all types, all predicates) to list one type's tuple-mentioned names. It is memoized only per evaluation (`memo` is 'a CALL-LOCAL dict, never persisted across writes', line 1030), and it feeds the hot star-grant branches: member_via_usersets iterates it per T:*#P grant (line 1178), ttu_leaf per star parent (1202), direct_expand/ttu_expand likewise (1314, 1335). Because lookup runs a fresh check per candidate (finding 1), a star-heavy schema pays O(|interner|) per candidate per touched type, multiplied by the O(instances) sat() fan-out the strict forall=>exists semantics already require.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Maintain a persistent refcounted per-type name index in the Interner: `names_of_type: dict[str, dict[str, int]]`, incremented in `acquire` when a key's (type, name) is first mapped (name != '*') and decremented in `release` when the last id for that (type, name) is freed. `_instances_of_type` then returns (a copy or view of) `names_of_type[t].keys()` — the same set the comprehension builds, since key_of holds exactly the live interned keys. O(instances of t) per query instead of O(all interned keys), and cheap enough that the call-local memo can stay as-is. Pure index-maintenance; the enumerated set (and thus every answer) is unchanged — order-independence is already guaranteed by the lowlink memo guard.

**Verifier reasoning (verbatim):**

> Verified line-by-line: setengine/engine.py:1039 does the claimed full key_of scan; the memo is call-local (fresh inst_memo per check at :1052 and per expand at :1221); the four star-branch call sites (1178/1202/1314/1335) match; lookup (:1439) runs a fresh check per (t,rel) marker probe (:1512) and per reverse-walk candidate (:1567), so the O(|interner|) scan repeats per candidate per touched type on star schemas. The repo's own perf log (docs/history/perf-round3-2026-07.md N7, landed 2026-07-15) names this exact escalation — 'a names_of_type index maintained in the Interner would share across the many checks inside one lookup' — deferred 'only with measurement', confirming the inefficiency is real and the sketched fix is the known next step. Fix semantics check out: key_of is mutated only in Interner.acquire (new-key branch, :258) and Interner.release (zero-refcount branch, :280), rebuild replays through acquire, so a per-(type,name) live-key counter (excluding '*') exactly mirrors the comprehension's set, including bare, userset-pred, and dep-interned keys; no SetOps isinstance issue; enumerated set unchanged so lowlink/order-independence and strict forall=>exists semantics are untouched. Not an algorithm change under CLAUDE.md's rule (same enumerated set, pure index maintenance).

**Verifier corrections / refinements (verbatim):**

> Impact 'medium' is the optimistic edge: the branch fires only on T:*#P grants or star tupleset parents (docstring: 'Rare path (star parents)'), the per-instance sat() fan-out often dominates the scan when it does fire, and the project's N7 entry notes the path is 'not exercised by current profiled workloads; needs measurement'. The scan dominates specifically in large multi-type stores where |interner| >> instances-of-t, multiplied by lookup's per-candidate checks. So: medium for star-heavy multi-type schemas, none for star-free workloads; per project convention this escalation should land with a measurement (and note the fix should return a copy or a keys() view — both safe since the interner never mutates during a read and inst_memo is call-local). Minor sketch wording fix: the counter must count live KEYS per (type,name) — increment on each new (type,name,pred) key creation in acquire's i-is-None branch, decrement on each key deletion in release — not just 'first mapped'.

**Lean impact (verifier, verbatim):**

> Interner.acquire / Interner.release — anchored in formal/CORRESPONDENCE.md (~line 955) but inside §7's explicitly-UNMODELED 'Interner / int32 id-recycling layer' entry (Lean uses Id := SubjectRef; netted by the incremental-vs-rebuild differential). _instances_of_type itself is unanchored; SetEngineModel.check/expand need no change since the enumerated set is identical; no anchored symbol is renamed, so verify.sh lean's anchor resolution stays green.

### R6-4 — lookup on boolean schemas full-scans every residue row in the store and JSON-decodes per row

**`index_v4/wildcard.py:792`** · dimension: graph-read · category: lookup-speed · filed impact: high · algorithm change (finder): yes · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> In `_collect_residue_memberships` (called by every `lookup` whenever `self.schema_info.derived_families` is non-empty, line 783-784): `rows = self.idx.session.exec(select(ResidueV1).where(ResidueV1.store_id == self.idx.store_id)).all()` — no filter beyond store_id, so EVERY residue row (one per derived object in the store) is fetched as a full ORM row. Then per row, per lookup call: `covered = want in json.loads(row.stars)` (line 802) and, on the covered/concrete branches, `s_node.id in json.loads(row.neg) and s_node.id not in json.loads(row.upos)` (lines 803-804) / `json.loads(row.upos)` (line 807) — O(#derived objects) SQL rows plus O(total JSON bytes) decode work for a single subject's lookup, repeated on every call. The ResidueRefV1 reverse index (models.py:124, maintained by `_sync_residue_refs`, processor.py:1114) already answers "which residues record this subject in neg|upos" as an indexed seek, but the read path never uses it; no analogous stars-shape index exists.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Two-tier fix. (a) Small, no schema change: memoize the decoded (stars, neg, upos) triple per residue keyed by `(row.id, row.version)` — `ResidueV1.version` is bumped on every changing reconcile (I7, models.py:121), so the key is a sound invalidation token — eliminating repeated JSON decode across lookups/checks in one session. (b) Algorithmic: add a stars reverse-index table analogous to ResidueRefV1 (`(store_id, subject_type, subject_predicate, object_node_id)` rows written in `_store_residue` next to `_sync_residue_refs`), so lookup becomes: one indexed seek for residues whose stars cover `(s_type, s_pred)`, plus one ResidueRefV1 seek for residues recording `s_node.id` (decode neg/upos only for those rows to distinguish which). Keep the JSON authoritative and extend invariant I6's agreement check to the new table, per the existing "derived, not authoritative" pattern; run the sabotage procedure on the new index before trusting it.

**Verifier reasoning (verbatim):**

> Verified line-by-line: index_v4/wildcard.py:792-794 full-scans ResidueV1 by store_id inside _collect_residue_memberships, which lookup calls unconditionally when schema_info.derived_families is non-empty (783-784); per-row json.loads of stars (801) and branch-wise neg/upos (803-807) run on every lookup call. The existing _residue_cache (wildcard.py:90) is None outside processor reconcile scopes and is never consulted by this scan, so nothing already provides the optimization. Hot-path materiality is well-supported by the repo's own history: the identical scan shape on the GC path was measured ~15 us/residue row, went quadratic under churn, and was replaced by the ResidueRefV1 reverse index (docs/spec-deviations.md 2026-08-14); this read-path twin was flagged in perf-round-3 and only micro-optimized (~23% in-loop) in perf-round-4, leaving the O(#derived objects) structure. Evidence claims all check out: ResidueRefV1 (models.py:124) records exactly neg|upos (processor.py:1111 passes neg|upos to _sync_residue_refs) with an indexed (store_id, subject_node_id) seek, unused by reads; no stars index exists; ResidueV1.version (models.py:121) is set to 1 on insert and incremented on every content update in _store_residue. The two-seek fix preserves semantics for all cases I checked: covered-and-unrecorded rows include without decode; recorded rows decode neg/upos to distinguish (matches lines 803-808 exactly); wildcard subject (s_name='*') and ghost subjects have concrete=False so only the stars seek applies, matching the current guards; object wildcards on derived relations are compile-rejected so no residue can exist for them; TTU/refcount/SetOps are untouched (graph-side read path only, derived table stays non-authoritative like ResidueRefV1).

**Verifier corrections / refinements (verbatim):**

> Two corrections. (1) The part-(a) memo key (row.id, row.version) is not fully sound as stated: empty residues are DELETED (_store_residue processor.py:1099-1100) and a recreated row restarts at version=1; on SQLite a non-AUTOINCREMENT rowid can be recycled, so a stale memo entry keyed (recycled_id, matching_version) could serve wrong decodes. Fix by also invalidating the memo on the delete/upsert paths in _store_residue (alongside the existing _residue_cache.pop at processor.py:1088-1089) or by piggybacking on the _bumped channel; PostgreSQL sequences do not recycle so the edge is SQLite-only. Also note (a) only eliminates JSON decode, not the O(#residues) row fetch — (b) is the real win. (2) Part (b)'s maintenance list is incomplete: besides _store_residue (correctly identified as the only live-path ResidueV1 writer, per the comment at processor.py:1107-1110), the offline bulk bootstrap writes residues and ResidueRefV1 rows directly (index_v4/bulk_build.py:364), so the new stars table must be populated there too, and the I6 agreement clause extended, or bulk-built stores will read as having zero star coverage via the new seek path.

**Lean impact (verifier, verbatim):**

> Touches CORRESPONDENCE.md-anchored symbols but no proved Lean model. WildcardIndex.lookup / _collect_residue_memberships are anchored in §7.3 "Load-bearing Python surfaces with NO Lean model" (CORRESPONDENCE.md:931-933) — explicitly unmodeled, pinned only by tests/test_lookup_oracle.py + the matrix; anchors must keep resolving (no renames) or verify.sh lean fails. DeltaProcessor._store_residue appears in the §5 model map (line 333: the reconcileKeyC/reconcileStarsKey "residue-THEN-edges" order row) and §7.1/§7.2 (the _bumped channel, line 426; the version/I7 projection, line 487) — adding a derived side-table write there follows the exact ResidueRefV1 precedent (§8.1, CORRESPONDENCE.md:1155-1171: logged as no-Lean-change because the table is derived-not-authoritative and not in the Lean state model), so the fix needs a matching §8.1/§7 log entry and must preserve the residue-write-before-edge-audit order, but no Lean proof change.

### R6-5 — lookup_reachable/lookup_reverse fetch full Edge ORM rows, filter in Python, then re-fetch full Node rows just to classify

**`index_v4/core.py:1175`** · dimension: graph-read · category: lookup-speed · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> `lookup_reachable`: `triples = self.session.exec(select(EdgeV4).where(EdgeV4.store_id == self.store_id).where(EdgeV4.subject_id == subject_id)).all()` then `return {t.object_id for t in triples if t.indirect_edge_count > 0}` (lines 1176-1179; `lookup_reverse` mirrors it at 1181-1185). All columns of every incident edge are fetched and instantiated as ORM objects, and the `indirect_edge_count > 0` predicate is applied in Python instead of SQL — rows with only direct/zero counts are shipped and discarded. The façade then does a SECOND round of full-row fetches: `_classify_ids` (wildcard.py:862) calls `self.idx._load_nodes(node_ids)` which selects `NodeV4` full rows (core.py:441-443) only to read `wildcard`/`type`/`predicate` (wildcard.py:869-872). So one `lookup` with K results costs K Edge ORM instantiations + ceil(K/900) node queries + K Node ORM instantiations. `processor.py:285/1259/1277/1286` call the same helpers inside the cascade, so the churn hits the write path too.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Replace the two passes with one projected join: `SELECT n.id, n.type, n.predicate, n.wildcard FROM edge_v4 e JOIN node_v4 n ON n.id = e.object_id AND n.store_id = e.store_id WHERE e.store_id = :s AND e.subject_id = :id AND e.indirect_edge_count > 0` (and the object-keyed mirror) — the count filter moves into SQL, classification columns arrive directly, and no ORM Edge/Node objects are built. At minimum, project columns (`select(EdgeV4.object_id).where(EdgeV4.indirect_edge_count > 0)`) in the core helpers and add a projected variant of `_load_nodes` for `_classify_ids`. The computed set is identical (SetOps seam untouched; classification stays concrete-vs-wildcard by the same columns). The wildcard-shape double scan in `lookup` (wildcard.py:779-781: concrete node then w_any node) can share one query via `subject_id IN (:concrete, :w_any)`.

**Verifier reasoning (verbatim):**

> Verified against the code: index_v4/core.py:1175-1185 does fetch full EdgeV4 ORM rows and filter indirect_edge_count > 0 in Python, and wildcard.py:_classify_ids (853-872) does a second round of full NodeV4 fetches (_load_nodes, core.py:432-447) only to read wildcard/type/predicate. The helpers sit on both the lookup surface and the write-path cascade (processor.py:285/1259/1277/1286 — the latter three even add a per-id session.get N+1 the finding didn't mention). All consumers treat the core helpers' return as set[int], so the sketched projection/join fix is contract-preserving; the inner join's drop of a missing node matches _classify_ids' `continue` fallback (_node_by_id filters the same store_id as _load_nodes, so the fallback can never recover a join-dropped id), and default autoflush plus ORM-attribute count mutations mean an SQL-side filter sees exactly the state the Python filter reads mid-transaction. One mechanism claim is wrong (see corrected_notes) but the inefficiency and the fix's value (ORM instantiation + round-trip elimination) survive it.

**Verifier corrections / refinements (verbatim):**

> The claim that "rows with only direct/zero counts are shipped and discarded" is vacuous: invariant I1 forbids persisting any edge row with indirect_edge_count == 0 (core.py:539/586-587 raise on the add path; 673-677 delete zeroed rows on the remove path; indirect >= direct rules out direct-only rows), so in a healthy store the Python filter discards nothing and pushing it into SQL reduces zero shipped rows. The real win is (a) column projection avoiding K EdgeV4 + K NodeV4 ORM instantiations, (b) merging the edge fetch and the node classification fetch into one join (2+ceil(K/900) queries -> 1), and (c) sharing one query across the concrete/w_any pair. Keep the defensive > 0 predicate in SQL rather than dropping it (it guards a corrupted store; ZANZIBAR_PARANOIA-style defense in depth). The pure-core variant (project object_id/subject_id, filter in SQL) is the safest first step since processor.py callers only need the id set; the join variant belongs in WildcardIndex._classify_ids/_collect_* as a projected sibling of _load_nodes (the full-row _load_nodes must survive for its _emit region-snapshot use, which relies on identity-mapped instances). Note the processor call sites at 1259-1288 have their own per-id session.get N+1 that the sketch doesn't cover — a follow-up batch there would compound the win.

**Lean impact (verifier, verbatim):**

> Touched symbols are anchored in formal/CORRESPONDENCE.md (lines 931-943: index_v4/core.py::ReachabilityIndex.lookup_reachable / ::ReachabilityIndex.lookup_reverse; index_v4/wildcard.py::WildcardIndex.lookup / ::WildcardIndex.lookup_reverse / ::WildcardIndex._collect_reachable / ::WildcardIndex._collect_reverse / ::WildcardIndex._classify_ids) — but that bullet is the documented UNMODELED-gap list ("Pinned only by tests/test_lookup_oracle.py + the matrix"), so no Lean definition models these query shapes and no Lean update is required. The fix renames nothing, so verify.sh lean's file::symbol anchor resolution stays green. Caution from the same map entry: "A lookup_reachable bug is a write-path bug" — gate the change with the lookup-oracle suite, the matrix, and a fuzz sweep since Lean provides no net here.

### R6-6 — check() issues up to 4 sequential point SELECTs for node resolution before its single batched edge probe

**`index_v4/wildcard.py:647`** · dimension: graph-read · category: lookup-speed · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> The edge probe itself is already batched ("ONE SQL round trip for all probes", lines 677-684), but the id resolution feeding it is not: `subj = self._get_concrete(s_pred, s_type, s_name)` (line 649), `obj = self._get_concrete(relation, o_type, o_name)` (line 654), `w_any_id = self._w_id(s_type, s_pred, 'any') ...` (line 664), `w_all_id = self._w_id(o_type, relation, 'all') ...` (line 667) — each is a separate `_db_node` point SELECT (core.py:969-976; the N15 `_node_cache` is None outside a write batch, core.py:923-933, so reads always hit the DB). A hot `check` on a doubly-declared wildcard shape is therefore 5 sequential round trips, which dominates per-call latency on PostgreSQL. The line-645 comment "(w-ids cached)" is stale — `_w_id` is deliberately uncached (W2, lines 169-175).

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Batch the up-to-4 identity resolutions into ONE SELECT: `select(NodeV4.predicate, NodeV4.type, NodeV4.name, NodeV4.wildcard, NodeV4.id).where(store_id == ...).where(tuple_(predicate, type, name, wildcard).in_(keys))` — served as point seeks by `node_v4_unique_constraint` (models.py:34), then map rows back to subj/obj/w_any/w_all by their identity tuple. This is a per-call fresh query, not a cache, so it does not reintroduce the W2 staleness hazard; the probe-key set and semantics are byte-identical. check drops from up to 5 round trips to 2.

**Verifier reasoning (verbatim):**

> Verified line-by-line: wildcard.py:646-670 performs up to 4 separate node resolutions (_get_concrete x2, _w_id x2), each a point SELECT via core.py::_db_node because the N15 _node_cache is None outside _node_cache_scope (installed only by the processor cascade at processor.py:1318 and the apply-loop — write paths, never the read path), and _w_id is deliberately uncached (W2, wildcard.py:169-175). The edge probe itself is already one batched row-value IN (lines 677-684). So a hot check is 3-5 sequential round trips today. The sketched fix — one fresh per-call SELECT with tuple_(predicate,type,name,wildcard).in_(keys) served by node_v4_unique_constraint (models.py:33-35) — is semantically equivalent: same session/transaction snapshot, read-only (the implicit-promotion write branch in node() is unreachable with implicit=None), only .id is consumed, star endpoints map to their ('*', 'any'/'all') identity tuples unambiguously, and no cross-call cache lifetime means the W2 staleness/rowid-reuse hazard is not reintroduced. Row-value IN is already used on both supported dialects at line 680. check() is the hottest read surface and on PostgreSQL per-statement RTT dominates, so impact=medium is fair.

**Verifier corrections / refinements (verbatim):**

> Two minor corrections: (1) the line-643 "(w-ids cached)" comment most plausibly means the w-ids are resolved once and reused across probes 2-4 within the call (which the code does), not a cross-call cache — calling it "stale" slightly overstates; (2) the 5-round-trip figure requires a doubly-declared wildcard shape; the common cases are 4→2 (subject-wildcard only) and 3→2 (no wildcard shapes). Both immaterial to the finding. Implementation nit: select bare columns (not NodeV4 entities) or dedupe identity tuples when subject and object coincide; and preserve the WildcardIndex.check.key closure name for the CORRESPONDENCE.md anchor gate.

**Lean impact (verifier, verbatim):**

> WildcardIndex.check is a modeled symbol — CORRESPONDENCE.md maps GraphIndex/State.lean::GraphModel.probeNonDerived (≤4 probes) and ::GraphModel.check to index_v4/wildcard.py::WildcardIndex.check, with a nested anchor ::WildcardIndex.check.key. The fix batches id resolution only; the probe-key set the Lean model describes is unchanged, so no Lean model update is needed (algorithm_change=false stands), but the refactor must keep the nested `key` closure so the anchor check in `verify.sh lean` still resolves.

### R6-7 — I10 outbox-sanity check rescans the ENTIRE outbox on every commit (twice at full tier), despite a watermark sitting on the guard

**`index_v4/invariants.py:625`** · dimension: graph-write · category: repeated-work · filed impact: high · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> def _check_outbox_sanity(session, store_id): rows = session.exec(select(DeltaOutboxV1).where(DeltaOutboxV1.store_id == store_id)).all() — no id filter. It is called unconditionally from check_invariants (line 347), which ParanoiaGuard runs BOTH pre-commit (line 735) and post-commit in a fresh session (line 749). The guard already carries the committed watermark (self.wm = outbox_watermark(...), line 715) but only passes it to verify_outbox_deltas (line 737). The outbox is append-only and prune_outbox is 'manual retention, never auto-called' (CLAUDE.md), so the per-commit cost grows with TOTAL historical writes — O(N^2) over a test run or any long-lived full-tier store. Paranoia full is default ON in tests via make_wildcard_index.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Add an after_id parameter to _check_outbox_sanity and filter .where(DeltaOutboxV1.id > after_id); wire guard.wm from both listeners (same scoping verify_outbox_deltas already uses). Rows are immutable once inserted and were validated at their own commit, so detection power is unchanged. While there, switch to a column select of (id, action, subject_type, object_type, object_predicate) — the check reads only those five columns, and the residue tier's own comment (line 582) records ORM materialization as the bulk of per-commit checker cost.

**Verifier reasoning (verbatim):**

> Every factual claim checks out against the current code. invariants.py:625-626: _check_outbox_sanity selects all DeltaOutboxV1 entity rows for the store with no id filter; line 347 calls it unconditionally from check_invariants; ParanoiaGuard runs check_invariants pre-commit (line 735) and again post-commit in a fresh session (line 749) at FULL tier; the guard's watermark (self.wm, line 715) is passed only to verify_outbox_deltas (line 737). The outbox is insert-only (insert(DeltaOutboxV1) in core.py:430 and bulk_build.py:387; no UPDATE anywhere; only DELETE is the manual prune_outbox), so per-commit cost grows with total historical flips — O(N^2) over a run — and unlike the node/edge scans this term is unbounded relative to live state under add/remove churn. Full paranoia is the default in tests via make_wildcard_index (tests/wildcard_helpers.py:19-34, paranoia=True -> install_paranoia default level=PARANOIA_FULL), so this sits on the gate's write path, twice per commit. The fix is semantically safe: rows are immutable post-insert, wm advances only after the post-commit check (line 751) so each new row is still validated pre- and post-commit of its own transaction, the scoping mirrors verify_outbox_deltas exactly, and the check touches no evaluation semantics (no wildcard/MemberSet/derived/TTU/refcount/SetOps interaction). The column-select suggestion is also valid — the check reads exactly the five listed columns, and the same ORM-materialization rationale is already recorded at lines 578-585.

**Verifier corrections / refinements (verbatim):**

> Impact should be downgraded from 'high' to medium-high with two qualifications the finding omits: (1) _check_outbox_sanity runs only at PARANOIA_FULL — the production-recommended tier is ZANZIBAR_PARANOIA=residue, which calls check_residue_hygiene and never reaches this function, so the cost lands mainly on the test suite/gate and on full-tier deployments, not on default production; (2) full-tier check_invariants already performs full node/edge scans per commit, so the fix removes the only unbounded-growth term but the checker remains O(live store) per commit — total full-tier commit cost does not become O(delta). Two implementation notes: direct callers of check_invariants (tests, bulk_build one-shot verification) should keep a default after_id=0 full scan; and per docs/sabotage-procedure.md the scoped check should be sabotaged (insert a malformed row above wm) and observed red before trusting it, plus a CORRESPONDENCE.md §7 note since the symbol is anchored to GraphIndex/State.lean::Quiescent.

**Lean impact (verifier, verbatim):**

> Touches two CORRESPONDENCE.md-anchored symbols: index_v4/invariants.py::_check_outbox_sanity is mapped to GraphIndex/State.lean::Quiescent (line 257) and ::check_invariants to GraphIndex/State.lean::Inv (line 258). The sketched fix adds a parameter without renaming, so the file::symbol anchors still resolve and 'verify.sh lean' stays green; however, scoping a modeled whole-state predicate to id > wm is a model/code divergence that should be logged in CORRESPONDENCE.md §7 (it is a checker-scoping change, not an algorithm change — evaluation semantics are untouched).

### R6-8 — Delta-scoped verifier runs one BFS per flipped PAIR instead of per distinct source — O(pairs x edges) per commit where O(sources x edges) suffices

**`index_v4/invariants.py:686`** · dimension: graph-write · category: repeated-work · filed impact: high · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> for (s, o), action in final.items(): reachable = bfs_reaches(s, o) — a fresh BFS over the whole direct graph per pair. A single edge add emits |A|x|D| + |A| + |D| flips (core.py line 804's exact fanout arithmetic; the cap default admits up to 100,000 rows), and all |D| pairs sharing one ancestor s each re-walk the graph from s. The module docstring itself prices this at 'O(pairs x edges)' (line 45-46), and it runs inside every commit at the full tier (default in tests). verify_outbox_deltas also entity-loads every edge each commit: edges = session.exec(select(EdgeV4).where(...)).all() (line 663) when it reads only 4 columns.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Group final by source: for each distinct s, one BFS computing the full reachable-id set (drop the dst early-exit), then evaluate every (s, o) pair by set membership — identical comparisons against closure rows and claimed actions, identical failure messages, cost drops from O(pairs x edges) to O(distinct-sources x edges) (for an A x D region: |A|+1 walks instead of |A|x|D|). Load adjacency/closure via a column select of (subject_id, object_id, direct_edge_count, indirect_edge_count).

**Verifier reasoning (verbatim):**

> Verified against the code: invariants.py:686-687 runs one fresh BFS per flipped (s,o) pair, line 663 entity-loads every EdgeV4 while using only 4 columns, the module docstring (lines 45-46) itself prices the verifier at O(pairs x edges), and core.py:804 confirms the |A|x|D|+|A|+|D| fanout (cap default 100,000) that makes the pair set per commit potentially huge with few distinct sources. Grouping by distinct source with one full-reachable-set BFS per source preserves the comparisons exactly (same closure-row and claimed-action checks, same messages) — the verifier is read-only over integer node ids and materialized direct edges, so wildcard/MemberSet/SetOps/refcount/TTU semantics are untouched. The column-select sub-fix is likewise safe. The inefficiency is real and the fix works, so is_real=true, but the impact tier claimed ('high') is inflated: this code runs only at PARANOIA_FULL, which production never uses (ConnectedStore defaults 'off', recommended 'residue' skips verify_outbox_deltas) and benchmarks disable; the win accrues to test/gate wall-clock (full tier is the default in tests and runs pre-commit inside every graph-backend commit) — material to a gate the project actively tiles around a 10-min cap, but not a production hot path. The project already logs this cost as known/deprioritized in docs/perf-next-round.md:54-56.

**Verifier corrections / refinements (verbatim):**

> Three corrections. (1) Impact downgrade: high -> moderate. verify_outbox_deltas runs only at the 'full' paranoia tier — the default in tests via make_wildcard_index/install_paranoia — never in production ('off'/'residue') and never in benchmarks (paranoia=False). The payoff is test-suite/gate runtime, not the production write path. Also it runs pre-commit only: after_commit (invariants.py:741-751) re-runs check_invariants but NOT the delta verifier, despite the module docstring's 'pre-commit AND post-commit' wording. (2) Fix subtlety: membership must be tested against the set of nodes encountered as BFS *neighbors*, not the seen-set (which pre-seeds src). With the naive seen-set, a (s,s) pair would read as reachable=True unconditionally, whereas today's early-exit code returns True for (s,s) only via an actual cycle (corrupt state). Self-pairs cannot be emitted by the write path, but a corruption verifier must be exact on corrupt state. (3) Per the repo's sabotage procedure (docs/sabotage-procedure.md), rewriting an assurance step requires re-sabotaging it red (existing pins: tests/test_outbox.py:171,189). Note the cost is already documented as known and deliberately out of bench scope at docs/perf-next-round.md:54-56, so treat this as gate-speed hygiene, not an undiscovered production win.

**Lean impact (verifier, verbatim):**

> none — formal/CORRESPONDENCE.md anchors invariants.py::check_invariants, ::_check_derived_invariants, ::_check_residue_rows, and ::_check_outbox_sanity, but neither verify_outbox_deltas nor bfs_reaches is a mapped symbol; the fix touches no modeled algorithm (it is a checker, and the comparisons it performs are unchanged).

### R6-9 — Write-tail refcount update re-SELECTs the two nodes it just batch-loaded into node_map three lines earlier

**`index_v4/core.py:887`** · dimension: graph-write · category: repeated-work · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> In _add_direct_edge_unsafe_impl the else-branch runs: for node_id in (subject_id, object_id): _node = self.session.exec(select(NodeV4).where(NodeV4.store_id == self.store_id).where(NodeV4.id == node_id)).first() — but line 846-849 just built region_ids = {subject_id, object_id} | ancestors | descendants and node_map = self._load_nodes(region_ids). Between the map load and this tail only EdgeV4 rows are mutated/deleted (the batch writer and _add_db_edges_unsafe touch no nodes), and _load_nodes returns identity-mapped instances, so node_map.get(node_id) is the exact object the SELECT returns (None <=> absent). That is 2 redundant point SELECTs on EVERY direct-edge write — grants AND each bridge edge, so a bridged add_tuple pays 6. Round 4 deferred an id-keyed CACHE for this tail over rowid-reuse eviction hazards (perf-round4 N15 note); within-call reuse of the already-loaded map has no cross-transaction lifetime and hence no such hazard.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Replace the per-node SELECT with _node = node_map.get(node_id) (node_map is in scope; subject/object are seeded into region_ids unconditionally). Same instances, same None-for-missing behavior, byte-identical refcount/GC outcomes.

**Verifier reasoning (verbatim):**

> Verified against index_v4/core.py: lines 885-897 literally issue the two per-node point SELECTs in the else-branch tail, and lines 846-849 unconditionally seed subject_id/object_id into region_ids and load them via _load_nodes (same store_id+id predicate, identity-map instances per its docstring). Between the map load (849) and the tail (885), only _add_indirect_edges_batch_unsafe (851) and _add_db_edges_unsafe (855) run; both mutate/delete EdgeV4 rows and buffer outbox dicts only — _emit reads nodes but never mutates them, and its own docstring (lines 392-398) states the batch deletes no nodes so the snapshot stays valid. So node_map.get(node_id) returns the exact instance (or None) the SELECT would, and the sibling subject_id==object_id branch (866-868) already uses this exact _load_nodes hoist, confirming the pattern. The N15 rowid-reuse hazard cited by round 4 applied to the cross-batch node() resolution cache, not a call-local map. Hot path: every direct-edge write (grants, wildcard bridges, boolean-cascade leaf writes) pays 2 point round trips — material on PostgreSQL, minor on SQLite.

**Verifier corrections / refinements (verbatim):**

> Fix as sketched is correct; keep the existing `if _node:` guard (a miss is legitimately None on both paths). One negligible delta: the tail SELECT's implicit autoflush of pending edge mutations disappears; they flush at the same transaction's next flush point (_flush_outbox/commit) under SQLAlchemy's unit-of-work ordering, so outcomes are unchanged. Impact is honestly small-to-medium: 2 point SELECTs per direct-edge write against a write that already does several batch queries — meaningful on PostgreSQL round trips, minor on SQLite.

**Lean impact (verifier, verbatim):**

> _add_direct_edge_unsafe_impl (CORRESPONDENCE.md line 252: GraphIndex/Closure.lean::pathCount_addEdge / pathCount_removeEdge, T4). The fix edits a modeled symbol's body, but the model covers path-count closure arithmetic, not the node-refcount fetch strategy — behavior-preserving micro-optimization, no Lean change required per CLAUDE.md.

### R6-10 — check_fn re-enumerates stored tupleset/userset tuples via SQL once per subject per reconcile

**`index_v4/processor.py:159`** · dimension: cascade · category: repeated-work · filed impact: high · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> _EvalContext.ttu_check runs `for (pt, pn) in self.proc.tupleset_parents(self.object_type, self.obj_name, ts, parent_types):` (line 159) and `self.proc.tupleset_star_types(...)` (line 155) on every call; userset_check similarly calls `self.proc.stored_userset_subjects(...)` (line 129) per call. Each bottoms out in `_direct_incoming` (an EdgeV4 SELECT, line 309-313) plus `_nodes_by_ids` (an IN SELECT, line 302-305), with no memo. `_reconcile` invokes `plan.check_fn(ctx, ...)` once per neg candidate (line 756), once per audit member for upos (line 787), and once more per bare-entity subject via step 4's `_reconcile_subject` (line 822 -> line 609 `should = bool(plan.check_fn(ctx, s))`). The same enumerations are ALSO run outside check_fn by `_from_chain_keys` (line 475-479), `_derived_leaf_neg_ids` (line 944, 952), and `_leaf_concretes` (line 1005, 1020). Net: one full-object reconcile with N subjects and a TTU/userset leaf issues ~2*N+ duplicate SELECT pairs enumerating tuples that are constant for the whole reconcile (the cascade's `_write_derived` only writes the public derived family, never the storage leaves these read).

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Add a reconcile-scoped memo (mirroring the P3 residue cache pattern at `_residue_cache_scope`) for `_stored_tupleset_subjects(object_type, obj_name, ts, parent_types)` and `stored_userset_subjects(object_type, obj_name, leaf, t, p)`, keyed by their arguments. Stored tuples on storage-leaf families cannot change during a cascade (user writes happen before `run_cascade`; `_write_derived` targets only the public family, and GC never deletes edge-holding parent nodes), so a per-reconcile — or cascade-wide with invalidation hooks in the `add_tuple`/`remove_tuple` choke points — cache is exact. This turns O(subjects x leaves) SELECT pairs into O(leaves).

**Verifier reasoning (verbatim):**

> Every cited line checks out in index_v4/processor.py today: ttu_check/userset_check re-run tupleset_star_types (155) / tupleset_parents (159) / stored_userset_subjects (129) on every call, each issuing an uncached EdgeV4 SELECT (_direct_incoming, 308-313) plus a NodeV4 IN SELECT (_nodes_by_ids, 294-306). _reconcile calls check_fn per from-chain key (732), per neg candidate (756), per upos audit member (787), and per bare-entity subject via step 4 -> _reconcile_subject (822 -> 609), and the same enumerations also run in _from_chain_keys (475-479), _derived_leaf_neg_ids (944/952), and _leaf_concretes (1005/1020) — so O(subjects x leaves) duplicate SELECT pairs per reconcile is accurate. No existing cache covers this: the N15 node cache (run_cascade, 1318) caches only node lookups and the P3 residue cache (_residue_cache_scope, 573) only residue reads. The constancy premise for the memo holds: _write_derived writes only the public derived family (processor_writes, wildcard.py:473), user writes precede run_cascade, and _gc_subject_node deletes only reference_count==0 nodes so edge-holding stored-tuple endpoints survive a cascade. The sketch correctly memoizes at the _stored_tupleset_subjects level (pre-star-expansion), which is exact — memoizing tupleset_parents wholesale would freeze the _instances_of_type expansion, which legitimately changes mid-reconcile. Hot path: the cascade runs synchronously inside every boolean-schema write transaction, so the win is material for boolean schemas with TTU/userset leaves (especially over a PostgreSQL round trip), though zero for untainted schemas or the pure read path.

**Verifier corrections / refinements (verbatim):**

> Two refinements. (1) Impact is high only for boolean (tainted) schemas containing TTU or userset leaves and objects with many audit members; untainted schemas never run reconcile, and reads are untouched — so "high" is scoped to the boolean write/cascade path. (2) The sketch's per-reconcile memo scope must be reentrant like _residue_cache_scope (a cheap-path reconcile_subject can escalate into _reconcile at line 646, and step 4 nests _reconcile_subject inside _reconcile); a cascade-wide scope is also exact for the stored enumerations, but only because the sketch leaves _instances_of_type (star-parent expansion inside tupleset_parents) uncached — that one reads the global node table, which does change mid-reconcile (step-2a interns, step-4 implicit-GC), so it must stay live. Per the project's sabotage procedure, the memo should land with a test proving invalidation (or scope teardown) actually works — e.g. two back-to-back cascades where a storage-leaf tuple changes between them.

**Lean impact (verifier, verbatim):**

> Touches CORRESPONDENCE.md-anchored symbols: DeltaProcessor.tupleset_parents / _stored_tupleset_subjects (§7 RC2 entry — explicitly no graph-side Lean counterpart, fragment-excluded by TtuStarFree/TtuTuplesetsDirect) and the _EvalContext ttu_*/userset_* methods mapped under GraphIndex/CascadeStrata.lean::GraphState.checkFnR (§5 table). A result-identical memo is a behavior-preserving micro-optimization, so no Lean model change is owed — but do not rename the functions or verify.sh lean's anchor resolution goes red; a new cache-scope wrapper should mirror how reconcile/_reconcile kept both names in the §5 rename ledger.

### R6-11 — Residue cache is torn down between every reconcile_subject call of a cascade round

**`index_v4/processor.py:1350`** · dimension: cascade · category: repeated-work · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> `_run_cascade` reconciles subject-granular keys with `for s in sorted(subjects): self.reconcile_subject(object_type, rel, obj_name, s)` (lines 1350-1351), and `reconcile_subject` enters a fresh outermost `_residue_cache_scope()` per call (lines 589-592; `outer = self.widx._residue_cache is None`, line 580). So the object's own residue row plus every lower-stratum residue a leaf reads is re-SELECTed and re-`json.loads`-decoded (wildcard.py lines 707-718) once per subject and once per key, even though the node-resolution cache (N15) is deliberately installed for the WHOLE cascade at line 1318 (`with self.idx._node_cache_scope():`). `_store_residue` is the only writer/deleter of ResidueV1 (grep-verified: only processor.py:1095/1100 touch the table) and already invalidates exactly the key it writes (lines 1088-1089), which is the stated correctness basis of the cache.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Install the residue cache for the whole cascade: wrap `_run_cascade` in `self._residue_cache_scope()` alongside the existing `_node_cache_scope` (the scope is already reentrant, so the inner per-reconcile entries become no-ops, and standalone `reconcile()` callers keep today's behavior). Correctness rests on the invalidation `_store_residue` already performs; keep closing the scope before commit so paranoia reads true state, mirroring the N15 comment at lines 1315-1317.

**Verifier reasoning (verbatim):**

> Every load-bearing claim checks out. (1) index_v4/processor.py:_run_cascade (1344-1351) calls reconcile/reconcile_subject per key/subject; _residue_cache_scope is installed only inside reconcile (692) and reconcile_subject (591) — grep confirms no cascade-level or advance_index-level installation — so each call is the outermost scope and the residue cache is torn down between every reconcile of a round, while the N15 node cache (run_cascade:1318) deliberately spans the whole cascade. (2) Repeated work is real: wildcard.py:_residue_state (700-722) re-SELECTs ResidueV1 and re-json.loads stars/neg/upos on every miss, and all residue reads (processor _residue_state:248, derived_check→_check_derived:255-262, the leaf reads inside plan.check_fn) flow through it, so an object's own residue plus every lower-stratum residue is re-fetched once per subject per key. (3) The fix is semantics-preserving: the scope is reentrant (outer-flag, 580-587); _store_residue (1077-1112) is the only live-path writer/deleter of ResidueV1 (adds 1095, deletes 1100; bulk_build.py:345 is offline with no cache; direct test writes never run inside a cascade) and pops exactly the written key BEFORE the row-existence check (1088-1089), covering upsert, delete-when-empty, and creation-after-negative-cache; cached values are immutable snapshots with fresh mutable sets per call (695-699); the writer's own _residue_row read (242-246) and the invariants/paranoia checker (invariants.py 380/583) bypass the cache; the sketch keeps the scope closing before commit, mirroring N15. Escalation _reconcile_subject→_reconcile (646) calls the private method and is unaffected. Wildcards/stars, neg/upos, and TTU semantics all mutate residues solely via _store_residue, so invalidation is complete; no SetOps/isinstance concerns (plain frozenset/tuple snapshots). (4) Hot path: the cascade runs inside every write transaction on a boolean schema; on PostgreSQL each avoided SELECT is a network round trip. One honest downgrade: the node-resolution half of each residue read is already amortized by the cascade-wide N15 node cache (cached_concrete_node, 240), so the win is the ResidueV1 SELECT + JSON decode, not the node SELECT — medium impact stands, skewing larger on multi-subject fan-outs and PostgreSQL, smaller on SQLite.

**Verifier corrections / refinements (verbatim):**

> Impact is real but slightly overstated: the per-subject node SELECT (wildcard.py:707 via _get_concrete→cached_concrete_node) is already amortized by the cascade-wide N15 node cache, so the marginal saving is the ResidueV1 SELECT + 3x json.loads per repeated read, not the full node+residue pair. Fix as sketched is correct; per house rules it should ship with a sabotage check (e.g. temporarily disable the _store_residue pop at processor.py:1088-1089 under the cascade-wide scope and watch the matrix/I9 audit go red) to prove the invalidation is what carries correctness, and CORRESPONDENCE.md line 339's "thin _node_cache_scope() wrapper" description of run_cascade must be updated to mention the second scope.

**Lean impact (verifier, verbatim):**

> Touches DeltaProcessor.run_cascade, a CORRESPONDENCE.md-modeled symbol: §5 line 339 maps GraphIndex/CascadeStrata.lean::runCascade2 to "DeltaProcessor.run_cascade (a thin idx._node_cache_scope() wrapper) → ::DeltaProcessor._run_cascade" (also the §351-353 rename-note rows pinning reconcile/reconcile_subject/run_cascade as cache-scope wrappers). Caching (perf P3/N15) is not part of the modeled algorithm, so no Lean definition changes and the verify.sh lean symbol anchors still resolve; only the line-339 prose describing run_cascade as a thin node-cache-only wrapper needs a one-line doc update.

### R6-12 — _bumped is an unde-duplicated list, so one reconcile can trigger the same expensive fan-out many times

**`index_v4/processor.py:1112`** · dimension: cascade · category: repeated-work · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> `_store_residue` ends with `self._bumped.append((object_type, rel, obj_name))` (line 1112) on every residue write, and `_reconcile` step 4 calls `_reconcile_subject` per bare-entity audit member (lines 819-823), each of which may call `_store_residue` again for the same key — so a single full-object reconcile appends the same (type, rel, name) once per changed subject. `_run_cascade` then consumes it with no dedupe: `for (b_type, b_rel, b_name) in bumped: self._fan_out((b_type, b_rel), b_name, keys, lambda k: keys.__setitem__(k, None))` (lines 1332-1334). Each duplicate `_fan_out` re-runs the dependency walk, including `self.idx.lookup_reachable(ent.id)` over the closure plus a `session.get` per reached id (lines 1277-1279, 1286-1288) for 'ttu'/'userset' edges.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Dedupe before fanning out: `for key in dict.fromkeys(bumped): ...` (or make `_bumped` an insertion-ordered dict keyed by the triple). Behavior-preserving by construction — the consumer only does `keys[k] = None`, which is idempotent, and the quiescence-path loop at lines 1357-1359 gets the same treatment.

**Verifier reasoning (verbatim):**

> Verified line-by-line: _bumped is a plain list (processor.py:229) appended in _store_residue (line 1112) on every residue write, and _run_cascade consumes it with zero dedupe at lines 1331-1334 and 1357-1359, calling _fan_out per entry. Duplicate appends of the same (type, rel, name) per round genuinely occur — most robustly via the cheap path (lines 1350-1351: reconcile_subject per subject of one key; _reconcile_subject calls _store_residue at line 652 or 685 per changed subject, so K changed subjects = K identical appends), and also via the finder's full-reconcile path (step-3 store at 814 plus step-4 per-bare-subject stores at 685, reachable because step 2's neg loop only covers `candidates` while step 4 audits all bare audit members). Each duplicate _fan_out with a 'ttu'/'userset' dependent re-runs lookup_reachable, an unmemoized SELECT over the closure (core.py:1175-1179). Decisive corroboration: _map_deltas_to_keys already dedupes its own fan-out path (processed_objects, line 1188) and its P6 comment states the full/subject merges are idempotent and order-independent so per-object fan-out-once is equivalent — the same argument proves the sketched dedupe (dict.fromkeys on the swapped bumped list, plus the quiescence loop) is exactly behavior-preserving: _fan_out mutates nothing but the keys dict via `keys[k] = None`, and no reconciles interleave with the fan-out loop, so state is constant across it. The quiescence leftover set and abort behavior are also unchanged. No wildcard/MemberSet/SetOps/refcount/TTU-stored-tuple interactions — this is pure invalidation-key marking. Hot-path status confirmed: the cascade runs synchronously inside every write transaction on a boolean schema.

**Verifier corrections / refinements (verbatim):**

> Two refinements to the finder's account. (1) The dominant duplication path is not the cited full-reconcile step 4 (which usually no-ops because step 3 already stored the recomputed neg) but the cascade's cheap path (processor.py:1350-1351), where reconcile_subject per changed subject of one key appends the same triple once per subject via _store_residue lines 652/685; the step-4 path can still fire for star-covered expr-false positive-leaf concretes absent from step 2's candidate set, so the title's claim survives either way. (2) Impact is schema-dependent: _fan_out is only expensive when compiled.dependents has 'ttu'/'userset' entries for the source (stacked multi-stratum boolean schemas); on flat boolean schemas dependents.get returns [] and duplicates are near-free — so "medium" holds for stacked schemas, closer to low otherwise. Also note session.get per reached id is largely identity-map-cheap after the first fan-out; the repeated cost is chiefly the lookup_reachable closure SELECT per duplicate. The sketched fix (dict.fromkeys over the swapped list, same treatment in the quiescence loop) is correct as written; if _bumped instead becomes an insertion-ordered dict, keep the swap-then-iterate pattern at line 1331 so appends during later reconciles still land in the next round.

**Lean impact (verifier, verbatim):**

> DeltaProcessor._run_cascade is a CORRESPONDENCE.md-modeled symbol (GraphIndex/CascadeStrata.lean::runCascade2 / ::GraphState.frontierRows, CORRESPONDENCE.md lines 338-340), and _store_residue / _fan_out / the _bumped channel are all anchored too — the _bumped fan-out is an explicitly documented §7 modeling gap ("SECOND dirty-key source", line ~424; T5's abort caveat, line 340). The dedupe leaves the per-round dirty-key SET identical, so under CLAUDE.md's rule it is a behavior-preserving micro-optimization needing no Lean model change; keep function names unchanged so verify.sh lean's anchor resolution stays green.

### R6-13 — Full node-set scan per check_fn evaluation: _instances_of_type is O(|nodes|) and sits inside the per-candidate TTU check

**`index_v4/bulk_backfill.py:463`** · dimension: build · category: repeated-work · filed impact: high · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> _instances_of_type (lines 458-464) is `return sorted({name for (_p, typ, name, w) in self.nodes if typ == t and w == '' and name != '*'})` — a full scan of every interned NodeKey. It is called from `_tupleset_parents` (line 497-498: `for pt in star_types: out.extend((pt, inst) for inst in self._instances_of_type(pt))`), which is called from `ttu_check` (line 119) — and `ttu_check` is the compiled leaf closure `lambda ctx, s: ctx.ttu_check(tr, ts, pt, s)` (zanzibar_utils_v1.py:1938), i.e. it runs once per `plan.check_fn(ctx, s)` evaluation. `_reconcile` evaluates check_fn per neg candidate (line 751), per audit member in the upos loop (line 778), and again per bare-entity audit member in the edge audit (line 689 via line 801), for every live object of every relation (run(), lines 828-833). With a stored `T:*` tupleset parent the backfill therefore costs O(|nodes| × audit-size × live-objects) just re-deriving the same instance list.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Maintain a `names_by_type: dict[str, set[str]]` index exactly the way `family_names` is already maintained: seed it in `__init__` from `nodes`, add to it in `_intern` (the only place nodes are created). `_instances_of_type` becomes `sorted(self.names_by_type.get(t, ()))` — identical output (wild=='' keys never have name '*', and the set-comprehension dedupe is preserved), so the byte-identity gate in tests/test_bulk_build.py stays green. Turns an O(|nodes|) scan into O(|instances of t| log) per call.

**Verifier reasoning (verbatim):**

> Verified line-by-line: _instances_of_type (bulk_backfill.py:458-464) is an uncached full scan of self.nodes plus sorted(), called from _tupleset_parents (:498) on every ttu_check/tupleset_ttu_check evaluation, and zanzibar_utils_v1.py:1938 confirms ttu_check IS the compiled check_fn leaf. _reconcile evaluates check_fn per from-chain key (:737), per neg candidate (:751), per audit member (:778), and per bare-entity edge-audit member (:689 via :801), for every live object of every relation (run(), :828-833) — so with a stored T:* tupleset parent the backfill pays O(|nodes|) per evaluation, quadratic-ish in snapshot size. The fix sketch is sound: bulk_build.py seeds nodes (:224-227) before constructing _BulkBackfill (:244), and _intern (:280) is the only post-construction mutation site, so a names_by_type index seeded in __init__ and updated in _intern reproduces the live scan's immediate within-stratum visibility exactly (a naive memoization would NOT — nodes are interned mid-run — so the sketched maintained-index shape is the correct one). Output is byte-identical: set dedupe across predicates and sort order preserved; the name != '*' filter is provably vacuous today (bulk_build routes every '*' name to a w-node or raises; _ensure_entity_middles guards it). Materiality: this is the offline bulk build, not query-time check — but build is an enumerated hot path and this module exists solely for build performance; the scan only triggers when a stored T:* tupleset parent exists (legal, RC2-pinned config), and even after the fix the per-parent _member_check loop keeps ttu_check at O(|instances of T|) per evaluation (inherent to RC2), so the win is eliminating the |nodes| term — asymptotic when the star'd type is a small fraction of the interner, constant-factor otherwise. No SetOps/refcount/TTU-semantics involvement.

**Verifier corrections / refinements (verbatim):**

> Two refinements: (1) Impact is high only for bulk builds of boolean schemas that actually store a T:* tupleset parent — with no star parent, star_types is empty and _instances_of_type never runs; query-time check/lookup and the incremental DeltaProcessor (its _instances_of_type at processor.py:331 is a separate SQL-backed twin) are unaffected. Even with the fix, ttu_check stays O(|instances of T|) per evaluation because of the per-parent _member_check loop, so the improvement is removing the |nodes| scan term, not making TTU checks cheap. (2) Keep the name != '*' filter at read time (e.g. sorted(n for n in names_by_type.get(t, ()) if n != '*')) rather than trusting the "wild=='' keys never have name '*'" invariant — it is true today (verified in bulk_build's routing and all _intern call sites) but the filter costs O(k) and keeps the twin defensively identical to the processor's semantics. Also note the fix must NOT cache the sorted result across calls without invalidating on _intern — from-chain/public/middle nodes are interned mid-run and RC2's expansion must see them immediately (within-stratum visibility); the sketched maintained-set-plus-sort-per-call form handles this correctly.

**Lean impact (verifier, verbatim):**

> none — CORRESPONDENCE.md (lines 871-885) explicitly records the RC2 star-tupleset expansion, including the bulk twin, as having no graph-side Lean counterpart (fenced by TtuStarFree / TtuTuplesetsDirect hypotheses); the only anchored bulk symbol in that entry is _BulkBackfill._stored_tupleset_subjects, which the fix does not touch or rename, so all verify.sh lean anchors still resolve

### R6-14 — Stored tupleset/userset parent enumerations re-sorted and re-built for every check_fn call within one object's reconcile

**`index_v4/bulk_backfill.py:476`** · dimension: build · category: repeated-work · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> `_stored_tupleset_subjects` does `for (sp2, st2, sn2, w2) in sorted(self.in_adj.get(ts_key, ())):` (line 476) and `_stored_userset_subjects` does the same sort (line 453); `_tupleset_parents` then dedupes with `list(dict.fromkeys(out))` (line 499) and `_derived_stored_parents` repeats all of it per storage leaf (lines 510-516). All of these run inside the compiled leaf checks (`ttu_check` line 119, `tupleset_ttu_check` line 144, `userset_check` line 95), i.e. once per `plan.check_fn(ctx, s)` evaluation — so for one object with K audited subjects the same incoming-edge set is sorted and deduped K+ times (neg loop line 751, upos loop line 778, edge audit line 689), plus once each for stars_fn and _leaf_concretes/_from_chain_keys.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Memoize per `_BulkEvalContext` (one object's reconcile): cache `_tupleset_parents`/`_tupleset_star_types` keyed by (ts, parent_types) and `_stored_userset_subjects` keyed by (leaf, t, p) on the ctx. Within one _reconcile these enumerations are invariant: step-4 mutations only add derived edges into the current (tainted) public family and bridge edges whose subjects are w-nodes — both filtered out by the `sp2 != '...'` / `w2` conditions, and storage-leaf families (`<rel>.<idx>`) are never processor-written. The identity gate (tests/test_bulk_build.py) pins byte-identity if the invariance argument is ever wrong. Eliminates the repeated O(P log P) sort + dict churn per candidate.

**Verifier reasoning (verbatim):**

> Verified against C:/Users/user/PycharmProjects/graph-reachability-zanzibar-index/index_v4/bulk_backfill.py. Every cited line is accurate today: `_stored_userset_subjects` sorts `in_adj` per call (line 453), `_stored_tupleset_subjects` sorts per call (line 476), `_tupleset_parents` re-dedupes with `list(dict.fromkeys(out))` (line 499) and re-runs `_instances_of_type` — an O(|nodes|) full scan — per call when a stored `T:*` parent exists (lines 497-498), and `_derived_stored_parents`/`_derived_stored_star_types` repeat all of it per storage leaf (lines 510-525). These sit inside the compiled leaf callbacks (`userset_check` line 95, `ttu_check` lines 115/119, `tupleset_ttu_check` lines 140/144 — note ttu_check calls `_stored_tupleset_subjects` TWICE per evaluation, once via `_tupleset_star_types` and once via `_tupleset_parents`), and `plan.check_fn(ctx, s)` runs once per subject in four places per `_reconcile` (lines 689 edge-audit, 737 from-chain, 751 neg, 778 upos) plus `stars_fn` (line 715) and the direct enumeration users `_leaf_concretes`/`_derived_leaf_neg_ids`/`_from_chain_keys`. So for one object with K audited subjects the identical incoming-edge set is re-sorted/re-deduped ~2K+ times; with a star tupleset parent each of those also rescans all interned nodes. No memoization exists anywhere in the file. The invariance argument for the per-ctx cache holds on inspection: mid-reconcile mutations are (a) derived edges (wild='', subject concrete) targeting only the CURRENT relation's public family — never a storage leaf (`.` is reserved in declared names so leaf preds `<rel>.<idx>` can't collide) and never a tupleset of its own plan (stratification + cycle rejection), and (b) bridge edges whose in_adj contributions into concrete keys all carry w2='all' — filtered by `w2==''` in _stored_userset_subjects and `sp2!='...'` in _stored_tupleset_subjects (a w-node subject's sp2 is its predicate, never '...'). `_instances_of_type` is also invariant within a reconcile because every mid-reconcile `_intern` (from-chain keys, entity middles, defensive subject intern) adds nodes whose (type,name) pair already exists in `self.nodes`. Hot-path status: this is the offline bulk build, not per-query check/lookup — but bulk is the DEFAULT `build_index` path (CORRESPONDENCE.md §7 R4-BF/ZT-P3-6) and this module exists precisely because boolean backfill dominated build time, so 'medium' impact scoped to boolean bulk builds is fair; zero effect on online reads/writes. The differential identity gate (tests/test_bulk_build.py, 6 corpora, byte-identity vs the incremental processor path) is a real safety net for the change.

**Verifier corrections / refinements (verbatim):**

> Two additions to the sketch's invariance argument, both benign: (1) a `_concrete_key` that is None at first call can become non-None mid-reconcile (step-2a from-chain interning or `_ensure_entity_middles` can intern a node equal to a ts/leaf key), but the freshly-interned node's only in-edges are bridge edges (w2='all'), which the enumerations filter out — so the cached empty result still equals a recompute; (2) cache correctness also depends on `_instances_of_type` invariance (used for stored `T:*` expansion inside `_tupleset_parents`), which holds because every mid-reconcile intern reuses an already-present (type,name) pair — worth stating in the memo's docstring since it is not covered by the sketch's two filter conditions. Implementation detail: cache the computed lists per `_BulkEvalContext` lifetime (i.e., per `_reconcile`) and do not share cache entries across reconciles — across objects/strata the argument was not checked and need not be. Callers only iterate/membership-test the returned lists, so returning the cached list object is safe. Impact should be stated as build-time only (bulk boolean `build_index`), not query-path; within that scope the biggest win is eliminating the per-check `_instances_of_type` full-node scan under star tupleset parents (O(K·N) → O(N) per object), with the K-fold sort/dedupe churn as the secondary win.

**Lean impact (verifier, verbatim):**

> none — CORRESPONDENCE.md §7's R4-BF entry (~line 1345) explicitly records bulk_backfill.py as having NO Lean model (it is an "alternative constructor of the same modeled state", pinned only by the Python↔Python identity gate; the modeled algorithm is the incremental DeltaProcessor, which this fix does not touch). One mechanical caution: CORRESPONDENCE.md line 878 carries a resolvable anchor `index_v4/bulk_backfill.py::_BulkBackfill._stored_tupleset_subjects` and `verify.sh lean` resolves all anchors, so the fix must keep that method name (wrapping/memoizing it is fine; renaming it fails the gate until the map is updated).

### R6-15 — Kahn topo sort re-sorts the entire frontier list after every node that frees successors (both bulk topo sorts)

**`index_v4/bulk_build.py:129`** · dimension: build · category: build-speed · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> `_topo_order` keeps the frontier as a plain list and, whenever a processed node frees new nodes, does `queue.extend(newly); queue.sort()` (lines 128-129) — a full O(|queue| log |queue|) sort per processed node, worst case O(V² log V). The identical pattern exists in `_BulkBackfill._topo` (bulk_backfill.py lines 240-241: `queue.extend(newly); queue.sort()`). N18's own comments size the build at ~165k nodes, where a wide frontier makes this the dominant Phase-C cost.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Replace the list+sort with `heapq` (push newly-freed nodes, pop the min). Still fully deterministic run-to-run (the docstring's only requirement); the resulting topo order differs only in tie-break direction (current code pops the LARGEST of the sorted list), and nothing observable depends on it: the Phase-P DP is topo-order-invariant, node inserts iterate `sorted(nodes)`, and edge/outbox order comes from the independent `edge_pairs` sort. If exact pop-largest order is wanted anyway, heap a tiny reverse-compare wrapper. O(E log V) total.

**Verifier reasoning (verbatim):**

> Verified against the code: bulk_build.py _topo_order (lines 118-129) and bulk_backfill.py _BulkBackfill._topo (lines 231-241) both do `queue.extend(newly); queue.sort()` per processed node with a plain-list frontier, exactly as claimed. The fix sketch is sound: all consumers of the topo order are order-invariant across valid topo orders (Phase-P path-count DP; _seed_reachability set-union DP), node inserts iterate sorted(nodes), and edge/outbox order comes from an independent sorted(edge_pairs) at bulk_build.py line 302 — so a heapq frontier changes no written state at all, only the internal tie-break, and stays deterministic (docstring's only requirement). heapq compares NodeKey tuples with the same `<` the current sort uses. The differential identity gate (tests/test_bulk_build.py) compares id-independent canonical projections and would still pass. This is build-time (offline bootstrap), not per-query, but bulk is the DEFAULT build_index path and the file shows sustained N18 perf work at ~165k nodes / ~200k tuples, so build-speed/medium is honest.

**Verifier corrections / refinements (verbatim):**

> Minor overstatement in the evidence: Timsort exploits the already-sorted prefix, so each re-sort costs roughly O(|queue|) rather than O(|queue| log |queue|); the realistic worst case is O(V^2), not O(V^2 log V) — still quadratic vs. the heap's O(E log V), so the finding stands. "Dominant Phase-C cost" is speculative: it requires a wide frontier where many pops free successors, and Phase R/W DB I/O over ~200k rows may dominate wall-clock on many corpora. Also, no reverse-compare wrapper is needed — pop-smallest via plain heapq is fine since nothing observable depends on tie-break direction.

**Lean impact (verifier, verbatim):**

> none — CORRESPONDENCE.md's P13/R4-BF entries explicitly state the bulk build/backfill path has no Lean model (an "alternative constructor of the same state", pinned only by the Python↔Python differential identity gate); the modeled incremental algorithm is untouched

### R6-16 — Every closure flip writes a denormalized outbox row even on schemas with no boolean consumers, and rows are never reclaimed

**`index_v4/core.py:550`** · dimension: space-compile · category: write-speed · filed impact: high · algorithm change (finder): yes · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> core.py's `_emit` is called unconditionally on every closure edge flip (`self._emit(subject_id, object_id, "ADDED")` at lines 550/578/600 and in the batch loops at 664/676/696) and appends a row with SIX denormalized identity strings plus store_id: `self._outbox_buffer.append(dict(store_id=self.store_id, subject_node_id=..., object_node_id=..., action=action, subject_type=..., subject_name=..., subject_predicate=..., object_type=..., object_name=..., object_predicate=...))` (lines 408-414), bulk-inserted per write op by `_flush_outbox` (line 430). core.py:607 documents the volume: an "O(ancestors x descendants) closure region emitted by the expansion loops" — up to the 100,000 fan-out cap of rows per single add. `ReachabilityIndex` has no schema knowledge, so pure-union stores (no `RuleSet.compiled`, hence no DeltaProcessor cascade ever constructed to drain the stream) pay this on every write. Retention is manual only: CLAUDE.md pins "`index_v4.outbox.prune_outbox` — manual retention, never auto-called", so `delta_outbox_v1` plus its `(store_id, id)` index (models.py:183) grow without bound in both schema classes.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Gate emission on the store actually having a delta consumer: have WildcardIndex set a flag on ReachabilityIndex (exactly like the existing `processor_writes` flag) when `ruleset.compiled` is non-None OR when the paranoia §8.3 delta verifier is enabled; `_emit` becomes a no-op otherwise. For boolean stores, add an opt-in auto-prune below the processor's committed watermark (prune_outbox already keeps the head row safely). Sabotage-test per house procedure: assert the cascade and `verify_outbox_deltas` still go red when a delta is suppressed on a boolean/paranoia store.

**Verifier reasoning (verbatim):**

> Code today does exactly what the finding claims: _emit fires unconditionally on every closure flip (core.py 550/578/600 and 664/676/696), appends store_id plus six denormalized identity strings (408-414), and _flush_outbox bulk-inserts per write op (430). ReachabilityIndex has no schema knowledge and no emission gate. Pure-union stores have no in-tree outbox consumer: connectedstore/apply.py reads the watermark only when a DeltaProcessor exists (line 144), the cascade exists only for boolean-compiled schemas, and HA replicas tail TupleLogV1 (catch_up_evaluator), not the outbox. The only non-boolean reader is paranoia FULL's verify_outbox_deltas, and ConnectedStore.DEFAULT_PARANOIA is OFF with the recommended production tier 'residue' not touching the outbox. Retention is manual only: prune_outbox has zero non-test call sites, so delta_outbox_v1 plus its (store_id,id) index (models.py:183) grow without bound; bulk_build.py additionally writes one ADDED row per closure pair at build time (line 387). This is the hot write path (up to the 100k fan-out cap of rows per add, row volume matching the edge-write volume with wider string columns), and the prior N16/P7b optimizations show the cost was measurable. Nothing refutes the finding.

**Verifier corrections / refinements (verbatim):**

> Fix needs more care than sketched: (1) verify_outbox_deltas (paranoia FULL) uses the outbox as its worklist on ALL schemas — suppressed emission makes it silently vacuous (the house failure mode); paranoia is per-session and upgradeable in place (install_paranoia raise_to) and invisible cross-process in HA, so the emit gate must derive from durable store-level facts (schema boolean-ness) plus an explicit constructor opt-in, not the session guard, and must flip on when a FULL guard is installed. (2) Gating deviates from boolean spec §4 ("every flip inserts a row") and removes the documented async-worker seam (spec §13, drain_deltas back-compat) on pure-union stores — record in docs/spec-deviations.md; plain-union tests that drain deltas need the bare-ReachabilityIndex default to remain emit-on. (3) bulk_build.py (line 387) needs the same gate for build-time benefit. (4) Auto-prune must use the MIN cursor across all consumers (prune_outbox docstring) — the FULL guard holds its own cursor (guard.wm), so "below the processor watermark" alone is unsafe under FULL paranoia; also keep pruning off the hot write path (periodic/threshold, own transaction).

**Lean impact (verifier, verbatim):**

> GraphIndex/Cascade.lean::GraphState.writeLoggedOne / ::removeLoggedOne / ::writeLoggedRules (CORRESPONDENCE.md line 304 maps them to _emit/_flush_outbox: "delta row per accepted flip") and ::GraphState.pushDelta / ::nextDeltaId / ::maxOutboxId (line 314, the outbox append/cursor). Conditional emission changes the modeled write algorithm, so the Lean model needs updating or a CORRESPONDENCE.md §7 gap entry.

### R6-17 — SetEngine._instances_of_type rescans the entire interner per evaluation; lookup multiplies this per candidate

**`setengine/engine.py:1039`** · dimension: space-compile · category: lookup-speed · filed impact: high · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Duplicate corroboration of R6-3** — found independently by a second dimension; kept verbatim because the verdicts carry complementary detail.

**Evidence (finder, verbatim):**

> `names = {n for (kt, n, _p) in self.interner.key_of.values() if kt == t and n != '*'}` — a full scan of every interned key. The N7 memo (`inst_memo`) is CALL-local: `check()` creates `inst_memo = {}` at line 1052 and `expand()` at line 1221, so each check/expand call that touches a star branch (`member_via_usersets` line 1178, `ttu_leaf` line 1202, `direct_expand` line 1314, `ttu_expand` line 1335) rescans the whole interner once per type. `lookup` then calls `self.check(...)` once per declared (type, relation) for markers (line 1512) and once per dequeued candidate (line 1567), each with a fresh memo — so on schemas with wildcard-userset or star-tupleset restrictions, one lookup costs O(candidates × total-interned-keys) just to re-enumerate the same type populations.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Maintain a third population index in the Interner next to `ids_of_type`/`ids_of_shape`: `names_of_type: dict[str, dict[str, int]]` (name -> refcount over distinct interned keys), incremented in `acquire` when a new (type, name, pred) mapping is created and decremented in `release` when it is dropped (star names excluded, matching the existing `n != '*'` filter). `_instances_of_type` returns its keys — the identical set, now O(1). Semantics-preserving: same membership set, callers only iterate and short-circuit; reads never intern, so the view is stable within one evaluation. rebuild() reconstructs it via the same acquire replay.

**Verifier reasoning (verbatim):**

> Verified line-by-line: engine.py:1039 does a full key_of scan per memo-miss; inst_memo is created fresh at line 1052 (check) and 1221 (expand) so it never survives across the per-candidate check calls lookup makes at lines 1512 (markers, one per declared (type, relation)) and 1567 (one per dequeued candidate). All four star-branch call sites (1178, 1202, 1314, 1335) exist. No existing persistent cache: ids_of_type/ids_of_shape are deliberately unusable here (per-predicate, and the blind-audit comments forbid them because they miss Computed/TTU-only members' names). So on stores containing stored T:*#p userset subjects or stored T:* tupleset parents, one lookup really pays O((candidates + declared-relations) x total-interned-keys) purely for re-enumeration — a genuine hot-read-path inefficiency. The sketched names_of_type index is semantics-preserving: every interner mutation (including dep-/chain-interning at lines 633-660) goes through acquire/release, rebuild() replays through _apply_add onto a fresh Interner, the star-name exclusion matches n != '*', reads never intern so the view is stable within an evaluation, and the callers only iterate existentially/union over the set so iteration-order changes cannot alter answers (the lowlink memo guard and MemberSet union commutativity both ensure order-independence). Plain dicts, no SetOps isinstance issue.

**Verifier corrections / refinements (verbatim):**

> Two refinements. (1) The release-side decrement must DELETE the (type, name) entry when its distinct-key count reaches zero (not merely decrement): a stale zero-count name would act as a ghost exists-witness, violating the strict forall-implies-exists rule (blind-audit O3) and diverging check/expand from the oracle — this is exactly the failure class the surrounding comments guard, so the implementation should be pinned by a differential/hypothesis test over add-remove churn. Returning a copy of the keys (O(instances-of-type), still a strict win) is safer than a live keys() view if anyone ever holds the memo across a write. (2) Impact scoping: the fix removes only the enumeration cost (O(total-interned-keys) -> O(instances-of-type) per type per evaluation); the per-instance recursive sat/do evaluation over those instances remains and can dominate when the star-branch type's own population is large. The branch also fires only on stores with stored star tuples (the code calls it "Rare path (star parents)"), so schemas without them see zero change — impact is high specifically for large multi-type stores with wildcard-userset or star-tupleset data, not universally.

**Lean impact (verifier, verbatim):**

> none — `_instances_of_type` has no anchor anywhere in formal/ (grep: zero matches), and the symbols the fix edits (`Interner.acquire`, `Interner.release`) are anchored in CORRESPONDENCE.md §7.3 as an explicitly UNMODELED region (Lean uses Id := SubjectRef; id-recycling inexpressible, netted by differential tests) — the fix keeps those names so the `verify.sh lean` anchor resolution stays green. The enumerated population corresponds semantically to `Core/Store.lean::instances`, but that row is anchored to the oracle (`tests/oracle.py::Oracle.check.instances`), and its SetEngine consumers `SetEngine/Eval.lean::expandDirect`/`expandTtu` map to `expand.direct_expand`/`expand.ttu_expand`, which the fix does not modify and whose enumerated set is unchanged — CLAUDE.md's behavior-preserving micro-optimization case, no Lean model change owed.

### R6-18 — EdgeV4 closure rows carry a dead surrogate PK and the store_id string in the row plus two secondary indexes

**`index_v4/models.py:72`** · dimension: space-compile · category: space · filed impact: medium · algorithm change (finder): no · verifier: **CONFIRMED** (high confidence)

**Evidence (finder, verbatim):**

> `id: int | None = Field(default=None, primary_key=True)` plus `UniqueConstraint('store_id', 'subject_id', 'object_id', ...)` plus `Index('ix_edge_v4_store_object', 'store_id', 'object_id')` (lines 63-72). No query ever addresses or orders edges by `id` — the sole reference is wildcard.py:678's `select(EdgeV4.id)` used purely as an existence probe over `(subject_id, object_id)` pairs; every other access path filters `(store_id, subject_id/object_id)`. Since the materialized closure is the system's largest table (O(reachable-pairs) rows; the whole point of the O(1)-check design), each row pays an 8-byte id plus a full third B-tree (PK index on PostgreSQL, rowid tree on SQLite), and the arbitrary-length `store_id: str` is physically duplicated into the row and both composite indexes.

**Fix sketch (finder, verbatim — apply the verifier corrections below):**

> Make (store_id, subject_id, object_id) the primary key: drop the surrogate `id` and the now-redundant UniqueConstraint (the PK is the uniqueness), and declare the table WITHOUT ROWID on SQLite (sqlite_with_rowid=False in __table_args__) — removing one complete index and 8 bytes/row from the biggest table; rewrite wildcard.py:678's probe to select a literal/constant. Optionally intern stores behind an integer surrogate (StoreV4 already exists as the natural parent) to shrink the string out of every edge/node/residue/outbox row and index. Pure representation change — no traversal or count logic touched — but it is a schema migration, so goldens/conformance extractor (which reads EdgeV4 rows by key, not id) must be re-run.

**Verifier reasoning (verbatim):**

> Verified against the code: index_v4/models.py:61-90 has exactly the claimed triple structure (surrogate id PK at line 72, UniqueConstraint(store_id, subject_id, object_id) at line 64, composite Index(store_id, object_id) at line 68). Repo-wide grep confirms EdgeV4.id has exactly one reference — wildcard.py:678's existence probe (SELECT id ... LIMIT 1); nothing orders by it, no FK targets edge_v4.id, no ORM attribute access, and bulk_build.py's executemany insert (line 325) supplies all three key columns without id. The conformance extractor reads edges by content-projected keys, and the bulk-build identity gate compares content as a multiset (bulk_build.py:301), so ids are semantically inert. The fix is semantics-preserving: edge PK columns are never mutated (rows are created/deleted; only direct/indirect counts and the derived flag change), so a composite PK works with the identity map; wildcards, residues, refcounts, TTU-over-stored-tuples, and the SetOps seam are untouched; the outbox cursor is DeltaOutboxV1.id in a different table. Materiality is genuine: edge_v4 is the materialized closure (O(reachable-pairs), the biggest table by design), and the change drops one of three B-trees on both backends plus 8 bytes/row of PostgreSQL heap, and shaves one index maintenance off every closure-write/cascade insert — space plus a write-path constant factor, fairly rated medium.

**Verifier corrections / refinements (verbatim):**

> Minor corrections to the evidence/fix: (1) On SQLite the surrogate id is the rowid alias, so it costs a 1-9 byte varint (not 8 bytes) and there is no separate PK index — the "third B-tree" removed there is the collapse of the rowid table tree + unique index into one WITHOUT ROWID tree; net one-fewer-B-tree still holds on both backends, exactly 8 bytes/row saved only on PostgreSQL heap. (2) sqlite_with_rowid=False must go in the dict portion of __table_args__ alongside extend_existing. (3) The comment at bulk_build.py:305-312 promising auto-increment edge ids "in the exact same order as the old single INSERT" becomes stale and should be removed (nothing enforces it — the identity gate is a content multiset). (4) There is no migration framework in the repo (no alembic); dev/test DBs are created fresh via metadata, but any persistent PostgreSQL deployment needs a hand-written migration. (5) The optional store-id interning is a much larger blast radius (NodeV4/ResidueV1/ResidueRefV1/DeltaOutboxV1 all carry store_id: str, and StoreV4.id is a str PK) — real additional space but should be scoped separately from the edge-PK change. (6) Per CLAUDE.md, the gate (all verify.sh phases) plus a fuzz sweep should follow since this rewrites the probe query and the schema of the modeled state.

**Lean impact (verifier, verbatim):**

> Touches two CORRESPONDENCE.md-anchored symbols: index_v4/models.py::EdgeV4 (modeled by GraphIndex/State.lean::GraphState, CORRESPONDENCE.md line 250) and the probe inside index_v4/wildcard.py::WildcardIndex.check (modeled by GraphIndex/State.lean::GraphModel.probeNonDerived, lines 253/255, incl. the ::WildcardIndex.check.key anchor). Names survive so anchors still resolve, and the Lean model keys edges abstractly without a SQL surrogate id — a pure representation change, no Lean edit required, but run verify.sh lean since anchored symbols are edited.

---

## Appendix — the 16 UNVERIFIED lower-ranked leads

Each finder returned 5–6 findings; only the top 3 by filed impact went to
verification. The rest are preserved here **verbatim and UNVERIFIED**: no
adversarial pass confirmed the code does what is claimed, that the fix is
semantics-preserving, or that the Lean notes are right. History says treat
these as leads only — the verified set above had fix sketches corrected and one
refuted outright. Re-verify against the code before acting on any of them.

### [unverified · set-lookup] rebuild() replays full ORM rows one tuple at a time; no column projection or bulk bitmap insertion

**`setengine/engine.py:455`** · category: build-speed · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> `rows = self.session.exec(select(TupleV1).where(...).order_by(TupleV1.id)).all()` materializes a full SQLModel ORM object (identity map, attribute instrumentation) per stored tuple, then `for row in rows: self._apply_add(row.subject_predicate, ...)` (459-460) does per-tuple work: 2+ dict-probing `interner.acquire` calls, a `node_sets.get`, and a per-id `.add` into a roaring BitMap — the access pattern roaring is worst at (per-element inserts vs. bulk construction), repeated for the reverse-dependency acquires (656-660). The N10 lazy flow graph already removed the biggest replay cost, but every open/reopen (`rebuild()` is called from __init__, line 421, and by refresh/rollback paths) still pays ORM hydration + element-at-a-time set building over the whole store.

**Fix sketch (finder, verbatim, unreviewed):**

> (a) Select bare column tuples instead of TupleV1 entities (`select(TupleV1.subject_predicate, TupleV1.subject_type, ...)`) — rebuild only reads the six fields, so ORM hydration is pure overhead. (b) Two-pass batch apply: first pass in row order performs the interner acquires exactly as today (preserving id-assignment order, so instance-local ids stay byte-identical to the current replay); second pass groups subject ids per (object_id, entities|usersets) bucket in plain lists and lands each bucket with one `ops.update(bitmap, ids)` C call instead of len(bucket) `.add`s, ditto member_of. Resulting state is identical to sequential _apply_add (adds commute within a bucket). Keep `apply_logged` on the incremental path untouched.

### [unverified · set-lookup] population() constructs a throwaway empty set on every call, hit or miss

**`setengine/engine.py:486`** · category: repeated-work · filed impact: low · algorithm change (finder): no

**Evidence (finder, verbatim):**

> `return self.interner.ids_of_type.get(entity_type, self.ops.new())` and line 487 `return self.interner.ids_of_shape.get(shape, self.ops.new())` — Python evaluates `dict.get`'s default eagerly, so every population() call allocates a fresh mutable set (for RoaringSets a C-level `BitMap()` construction) even when the mask exists. population is the `pop` callback threaded through the whole MemberSet algebra: `_starpop` calls it once per star shape inside every `_ext` and `_normalize` (memberset.py:94), i.e. several times per ms.union/intersect/subtract step in expand's accumulation loops, and direct_expand calls it per '...'-restriction per node (engine.py:1302).

**Fix sketch (finder, verbatim, unreviewed):**

> Avoid the eager default: `m = self.interner.ids_of_type.get(entity_type); return m if m is not None else self.ops.new()` (same for the shape branch). All current callers only read the result (`ops.update(acc, pop(shape))`, `ns.entities & pop(...)`), but returning a fresh mutable on miss preserves today's contract exactly, so no caller audit is needed. Constant-factor allocation-churn fix on the algebra hot path; no semantic surface.

### [unverified · graph-read] _check_derived resolves the object node twice and _residue_state always decodes all three JSON blobs

**`index_v4/wildcard.py:748`** · category: repeated-work · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> In the `...`-subject branch of `_check_derived`: `obj = self._get_concrete(relation, o_type, o_name)` (line 748) for the edge probe, then on a probe miss `stars, neg, _ = self._residue_state(relation, o_type, o_name)` (line 755) whose body re-runs the identical point SELECT: `node = self._get_concrete(relation, o_type, o_name)` (line 707) — outside a reconcile the P3 `_residue_cache` is None (line 700-705), so every failed-edge-probe derived check pays a duplicated node resolution. Additionally `_residue_state` eagerly decodes all three blobs — `stars = frozenset(tuple(s) for s in json.loads(row.stars)); neg_ids = tuple(json.loads(row.neg)); upos_ids = tuple(json.loads(row.upos))` (lines 716-718) and builds fresh `set(neg_ids), set(upos_ids)` (line 722) — even when the caller discards `upos` (line 755) or only needs a single O(1)-membership answer; a large `neg` (many excluded subjects) makes every point check O(|neg|) decode + set-build.

**Fix sketch (finder, verbatim, unreviewed):**

> Let `_residue_state` accept an optional pre-resolved object node (the `...` branch already holds `obj`; pass it through, keeping the None-handling identical). For the decode churn, memoize the immutable decoded snapshot keyed by `(row.id, row.version)` (I7's version bump is the invalidation token — same shape as the existing P3 cache entries, which already store immutable tuples and rebuild fresh mutable sets per call), or decode lazily per field so a stars-only answer never touches neg/upos. Return values stay value-identical, so no behavior change and no Lean-model impact.

### [unverified · graph-read] Edge read indexes are not covering: check probe and object-keyed lookups need a heap fetch per row for indirect_edge_count/subject_id

**`index_v4/models.py:68`** · category: lookup-speed · filed impact: low · algorithm change (finder): no

**Evidence (finder, verbatim):**

> The read queries filter or project columns the indexes do not carry: the check probe adds `.where(EdgeV4.indirect_edge_count > 0)` on top of the `(store_id, subject_id, object_id)` unique-constraint seek (wildcard.py:681; models.py:64 `UniqueConstraint('store_id', 'subject_id', 'object_id', ...)`), and `lookup_reverse` needs `subject_id` + `indirect_edge_count` while `Index('ix_edge_v4_store_object', 'store_id', 'object_id')` (line 68) carries neither — so on PostgreSQL every matching edge of a popular object costs a heap fetch (no index-only scan), and on SQLite a rowid lookup per row. High-fan-in objects (a document every group can see) make `lookup_reverse`/expand pay this per edge.

**Fix sketch (finder, verbatim, unreviewed):**

> Widen the object-keyed index to `Index('ix_edge_v4_store_object', 'store_id', 'object_id', 'subject_id', 'indirect_edge_count')` and optionally add a covering companion for the subject-keyed direction (`store_id, subject_id, object_id, indirect_edge_count`) so check/lookup/lookup_reverse become index-only scans on PostgreSQL. Pure DDL, no query or algorithm change; costs index space and slightly larger write amplification — worth measuring with benchmarks/stmt_bench.py before adopting, per the N5 audit's one-index-per-question house style.

### [unverified · graph-write] Bridge maintenance issues up to ~8 separate point existence-probes per tuple write; the read path already shows the batched row-value-IN pattern

**`index_v4/wildcard.py:271`** · category: write-speed · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> _ensure_own_bridges: 'if not self.idx.direct_edge_exists_by_id(node.id, w_any.id): self.idx.add_edge_by_id(...)' and the same for w_all (lines 271/276) — direct_edge_exists_by_id is one point SELECT each (core.py 1103-1112). _add_tuple_trusted runs _ensure_bridges on BOTH endpoints (lines 519-520), and _ensure_entity_middles (lines 294-298) repeats a node resolve + both probes per crossable shape of the entity's type, on every write. Steady state (bridges already exist — the overwhelmingly common case) this is 4-8 sequential probe round trips per add_tuple that all return 'exists'. Contrast the check() read path, which puts all candidate probe keys into ONE tuple_(EdgeV4.subject_id, EdgeV4.object_id).in_(keys) SELECT (lines 677-684). Remove side repeats the pattern in _strip_bridges (lines 351, 358).

**Fix sketch (finder, verbatim, unreviewed):**

> Per write, collect the candidate bridge (subject_id, object_id) pairs for both endpoints plus their crossing middles, run one row-value IN SELECT with direct_edge_count > 0 to learn which exist, then add_edge_by_id only the missing pairs in the original loop order. Valid because adding bridge pair i never changes another pair's direct count (a direct-edge add only touches its own row's direct count), so the probe snapshot cannot go stale within the write; identical edges created in identical order.

### [unverified · graph-write] Full-tier invariant checker entity-loads every node and edge twice per commit; the residue tier's own comment records ORM materialization as the dominant cost

**`index_v4/invariants.py:151`** · category: write-speed · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> _load: 'nodes = list(session.exec(select(NodeV4).where(...)).all()); edges = list(session.exec(select(EdgeV4).where(...)).all())' — full ORM entity scans at the top of check_invariants, which runs per commit pre-commit AND again post-commit in a fresh session at the full tier (lines 735, 749; default ON in tests via make_wildcard_index). The same file already learned this lesson for the cheap tier: 'COLUMN selects, not entity selects ... materializing ORM instances (identity-map bookkeeping, instance state) measured as the bulk of the tier's cost' (lines 582-584), with the _NodeFacts/_ResidueFacts NamedTuple pattern already in place (lines 535-558). The checker only ever READS attributes off nodes/edges.

**Fix sketch (finder, verbatim, unreviewed):**

> Extend the existing _NodeFacts pattern: column-select the node/edge columns the checks read (add reference_count to _NodeFacts; an _EdgeFacts of subject_id/object_id/direct/indirect/derived) and pass those through check_invariants/_check_derived_invariants/snapshot_rows, which are attribute-read-only. Pre-commit correctness is unaffected: before_commit flushes first (line 732), so column selects see the identical pending state the entity selects do.

### [unverified · graph-write] Facade edge ops re-pay the _require_live_nodes liveness SELECT that core.add_edge documents as unnecessary after in-lock resolution

**`index_v4/wildcard.py:524`** · category: repeated-work · filed impact: low · algorithm change (finder): no

**Evidence (finder, verbatim):**

> _add_tuple_trusted: self.idx._lock_store() (line 509) -> _resolve(..., create=True) under the lock -> self.idx.add_edge_by_id(subject.id, obj.id) (line 524), and add_edge_by_id runs '_lock_store(); self._require_live_nodes(subject_id, object_id)' (core.py 1054-1055) — one extra IN-SELECT. Core's own name-based add_edge skips exactly this: 'resolved under the lock: live by construction, no re-verification round trip' and calls _add_edge_locked directly (core.py 1122-1123). Every facade edge op repeats it: the grant (524), each bridge add (272, 277), each bridge strip (352, 359), and remove_tuple's grant removal (564) — so one bridged add_tuple pays up to 3 redundant liveness queries, all guaranteed to pass because resolution happened under the same held store lock.

**Fix sketch (finder, verbatim, unreviewed):**

> Route facade calls whose endpoints were resolved (or whose edge row was just existence-probed) under the held lock through _add_edge_locked/_remove_edge_locked, mirroring core.add_edge's documented pattern — e.g. a narrow trusted by-id entry with the same trust-contract docstring style as _add_tuple_trusted/N9. Keep _require_live_nodes on the public add_edge_by_id/remove_edge_by_id for external/processor callers. For _strip_bridges the liveness argument is the just-probed direct edge row (direct>0 implies both endpoints refcounted, hence live under I13, and no concurrent writer can intervene under the lock). This removes a defense-in-depth check on those paths, so sabotage-test the trusted entry per docs/sabotage-procedure.md before trusting it.

### [unverified · cascade] Per-id session.get N+1 loops in fan-out and delta mapping, next to the batch helper built to replace them

**`index_v4/processor.py:1278`** · category: write-speed · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> `_fan_out` ttu branch: `for oid in self.idx.lookup_reachable(ent.id): o = self.session.get(NodeV4, oid)` (lines 1277-1279), and the userset branch repeats the pattern (1286-1288); `_map_deltas_to_keys`' target-feeders 'ttu' arm does the same per reachable id (1259-1261); `_keys_referencing` does `obj = self.session.get(NodeV4, row.object_node_id)` per ResidueRef row (458-461); and the subject-GC pre-pass issues one memoized `session.get` per distinct GC'd subject id (1183-1185). `lookup_reachable` returns the FULL transitive-closure descendant set, so a well-connected entity turns each fan-out into hundreds of point SELECTs (cold ids miss the identity map). `_nodes_by_ids` (lines 294-306) exists precisely for this — its docstring says 'replacing per-id session.get N+1 loops' — but these five sites don't use it.

**Fix sketch (finder, verbatim, unreviewed):**

> Batch each loop through `self._nodes_by_ids(ids)` and iterate the dict, or better, push the (type, predicate) filter into SQL: `select(NodeV4).where(NodeV4.store_id==...).where(NodeV4.id.in_(ids)).where(NodeV4.type==dep_t).where(NodeV4.predicate==edge.tupleset_rel)` — the loops only keep nodes matching one (type, predicate) pair, so most fetched rows are currently discarded. Identity-map semantics are preserved (same instances returned), as the `_nodes_by_ids` docstring already argues.

### [unverified · cascade] lookup_reachable/lookup_reverse hydrate full EdgeV4 ORM rows to project one id and filter in Python

**`index_v4/core.py:1175`** · category: write-speed · filed impact: medium · algorithm change (finder): no · overlaps verified R6-5

**Evidence (finder, verbatim):**

> `lookup_reachable` runs `select(EdgeV4).where(...).where(EdgeV4.subject_id == subject_id)).all()` then `return {t.object_id for t in triples if t.indirect_edge_count > 0}` (lines 1175-1179); `lookup_reverse` mirrors it (1181-1185). Every edge row incident to the node is transferred with all columns, ORM-hydrated and registered in the identity map, only to keep one int column — and rows with `indirect_edge_count == 0` (direct-only edges) are transferred just to be discarded in Python. These are the cascade's hottest primitives: `_incoming_concretes` (processor.py:285) calls `lookup_reverse` for every closure leaf of every full-object reconcile, and `_fan_out`/`_map_deltas_to_keys` call `lookup_reachable` per dependency edge per changed object.

**Fix sketch (finder, verbatim, unreviewed):**

> Project and filter in SQL: `select(EdgeV4.object_id).where(EdgeV4.store_id == ...).where(EdgeV4.subject_id == subject_id).where(EdgeV4.indirect_edge_count > 0)` (symmetric for reverse), returning `set(result)`. Same result set, no ORM hydration, no discarded rows. Behavior-preserving column projection, no Lean-modeled algorithm touched; check other callers of these two helpers don't rely on the identity-map side effect (they consume only the id set).

### [unverified · cascade] Residue version bumps always escalate every dependent to a full-object reconcile, even for single-subject changes

**`index_v4/processor.py:1334`** · category: write-speed · filed impact: medium · algorithm change (finder): yes

**Evidence (finder, verbatim):**

> Every `_store_residue` bump fans out with `self._fan_out((b_type, b_rel), b_name, keys, lambda k: keys.__setitem__(k, None))` (lines 1332-1334) — the `None` value means full-object reconcile — and `_fan_out`'s 'computed' branch likewise does `full((dep_t, dep_r, obj_name))` (1270-1271). So a cheap-path flip of ONE subject on a source relation (e.g. `reconcile_subject` toggling one edge, line 674-677) forces each dependent object through `_reconcile`'s complete pipeline: stars_fn, full candidate/audit enumeration, and check_fn over EVERY member (lines 695-835), re-evaluating subjects whose inputs did not change.

**Fix sketch (finder, verbatim, unreviewed):**

> Propagate granularity: record bumps as (key, changed_subjects | None) — `_store_residue` knows whether the write was a stars/topology change (escalate to full, as today) or a pointwise neg/upos/edge delta for known subjects. For 'computed' dependents (same object, same subject space) the changed subjects can take the existing cheap `reconcile_subject` path; 'ttu'/'userset'/'tupleset-ttu' dependents keep full reconciles. This changes the modeled cascade invalidation rule (spec §5.2), so the corresponding Lean model must be updated and the gate re-run per the CORRESPONDENCE.md workflow; it also needs the §5.4 symbolic-delta full-object rule preserved (star-covered members hold no edges to invalidate them individually).

### [unverified · build] Phase-W node write still goes through the ORM: ~165k SQLModel objects + add_all + flush + expunge loop, while every other Phase-W table uses core insert dicts

**`index_v4/bulk_build.py:287`** · category: build-speed · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> Lines 282-297 build a full dict of ORM objects — `node_objs[key] = NodeV4(store_id=..., predicate=pred, ...)` for every node, then `session.add_all(node_objs.values()); session.flush()`, then read ids back from the live instances and manually `session.expunge(n)` each one. The N18 comment on lines 292-296 ("so ~165k NodeV4 objects do not sit in the identity map") shows the scale. Edges, residues, residue-refs and outbox rows (lines 313-387) already use `session.execute(insert(Model), chunk)` with plain dicts. On SQLAlchemy 2.0.51 the flush SQL is batched (insertmanyvalues+RETURNING), so the remaining cost is pure Python churn: 165k SQLModel instantiations, unit-of-work state tracking on each, and the expunge loop.

**Fix sketch (finder, verbatim, unreviewed):**

> Insert nodes the way edges are inserted: chunked `session.execute(insert(NodeV4), [dict(...)])` over `sorted(nodes)` (same insertion order, so ids are assigned identically), then build `node_id` with ONE core SELECT of `(id, predicate, type, name, wildcard)` for the store (or use `insert(...).returning(...)` per chunk on SQLite/PostgreSQL). Removes ~165k ORM object constructions, identity-map insertions and expunges for the price of one read-back query; state is byte-identical, pinned by the identity gate.

### [unverified · build] Boolean bulk build holds three full-closure copies simultaneously: bf's reach_out/reach_in survive into Phases C/P/W under pvec and the materialized edge_pairs list

**`index_v4/bulk_build.py:302`** · category: space · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> On a boolean schema `bf = _BulkBackfill(...); bf.run()` (lines 244-245) builds `reach_out`/`reach_in` — the FULL transitive reachability in both directions as Python sets (bulk_backfill.py lines 204-206) — plus out_adj/in_adj. After `bf.run()` only `derived_pairs`/`explicit`/`residues` are read (lines 246-248), but `bf` stays referenced for the rest of the function, so ~2× closure of set entries sits in RAM while Phase P builds `pvec` (the full closure again as dict-of-dicts, lines 267-274) and line 302-303 materializes yet another full-closure list: `edge_pairs = sorted((a, b) for a in order for b in pvec[a] if pvec[a][b] > 0)`. N18 already had to bound Phase-W row dicts because peaks hit ~3× the DP at 200k tuples — these two allocations are the same RSS class and are untouched.

**Fix sketch (finder, verbatim, unreviewed):**

> Two independent, order-preserving trims: (1) after copying `bf.derived_pairs`/`bf.explicit`/`bf.residues`, `del bf` (or clear its reach_out/reach_in/out_adj/in_adj) before computing ref_count/succ/topo/DP — frees ~2x closure before pvec exists. (2) drop the `edge_pairs` list: iterating `for a in sorted(nodes): for b in sorted(pvec[a])` yields exactly the same lexicographic (a,b) order for both the edge and outbox chunk loops (lexicographic pair sort == sort by a then b), avoiding the O(C) list and replacing one global O(C log C) sort with cheaper per-node sorts; chunk boundaries and insertion order are unchanged.

### [unverified · build] catch_up defaults to a single unbounded batch: the whole backlog is materialized as ORM rows and applied under one transaction/store lock

**`connectedstore/store.py:277`** · category: space · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> `def catch_up(self, batch: int | None = None)` loops `advance_index(..., batch=batch)` — with the default None, `advance_index` calls `log_rows(session, ..., limit=batch)` (apply.py line 137) and `log_rows` does `return list(session.exec(stmt).all())` (source.py line 224): every `TupleLogV1` row past the cursor is materialized as ORM objects in one list, the contiguity check builds `[r.id for r in rows]` over all of them, and the entire drain runs under one `_lock_store()` FOR UPDATE (apply.py line 130) and one commit. advance_index's own docstring (apply.py lines 96-105) proves batch size "affects only latency/granularity, not the final materialized state or any semantic guarantee", and the catch_up loop + per-batch commit already exist — the batching is simply never engaged by default.

**Fix sketch (finder, verbatim, unreviewed):**

> Give catch_up a bounded default (e.g. batch=10_000) instead of None, or have the worker pass one: the existing loop then commits per batch, bounding both the ORM row list and the writer-blocking FOR UPDATE hold to one batch instead of the whole backlog. Semantics are already argued identical in advance_index's docstring (contiguous prefixes, monotone cursor); a large-backlog catch_up test at two batch sizes pins it.

### [unverified · space-compile] Derived check path re-SELECTs and re-decodes the full residue JSON (stars+neg+upos) on every check outside reconcile scopes

**`index_v4/wildcard.py:700`** · category: lookup-speed · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> `_residue_state` memoizes only "when a per-reconcile cache is installed (perf P3)" — `self._residue_cache` is set exclusively inside `DeltaProcessor._residue_cache_scope` (processor.py:580-587) and is None on the ordinary read path. So every `WildcardIndex.check` on a derived relation (`_check_derived` lines 732/740/755 all call `_residue_state`) performs a node SELECT, a ResidueV1 SELECT, and three full decodes — `stars = frozenset(tuple(s) for s in json.loads(row.stars)); neg_ids = tuple(json.loads(row.neg)); upos_ids = tuple(json.loads(row.upos))` (lines 716-718) — then materializes fresh `set(neg_ids)`/`set(upos_ids)` (line 722), all to answer a single `subj.id in neg` membership probe. `neg` holds every excluded concrete subject id on the object (models.py:115), so hot derived checks on exclusion-heavy objects are O(|residue|) each instead of O(1).

**Fix sketch (finder, verbatim, unreviewed):**

> Add a persistent decoded-snapshot cache on WildcardIndex keyed by (o_type, relation, o_name) and validated by `ResidueV1.version` — the column exists precisely for this (models.py:121, "bumped on every changing reconcile (I7)"): SELECT only (id, version) first, reuse the cached (stars, frozenset(neg), frozenset(upos)) on version match, decode on mismatch. Invalidate on `_store_residue` like the P3 cache already does. Same immutable-snapshot discipline (hand mutable copies to reconcile callers) so the existing in-place mutation contract is untouched.

### [unverified · space-compile] Set-engine check/expand re-walk the SchemaAST with per-node isinstance dispatch on every query

**`setengine/engine.py:1092`** · category: repeated-work · filed impact: medium · algorithm change (finder): no

**Evidence (finder, verbatim):**

> `sat_expr` (lines 1092-1115) and `do_expr` (lines 1258-1280) re-interpret the same lifetime-stable AST on every check/expand call: each node visit runs a chain of up to six isinstance tests (`if isinstance(expr, Union): ... if isinstance(expr, Intersection): ... if isinstance(expr, Exclusion): ... Direct ... Computed ... TTU`) and re-enters via the generator driver. The AST is pinned for the engine's life (__init__ comment: "self.ast pins every node for the engine's life (rebuild() only resets tuple state, never reparses the AST)"), and the codebase already has the compile-once pattern for exactly this: `_compile_check_fn` in zanzibar_utils_v1.py:1926 builds closure-composed plans with "no AST walk, no per-node dispatch, short-circuit" (boolean spec §1.11) — but only for the graph side's derived plans, not the set engine's evaluator, whose check is the inner loop of lookup (called once per candidate plus once per declared relation).

**Fix sketch (finder, verbatim, unreviewed):**

> AOT-compile each (type, relation) Expr once at __init__ into generator-closures mirroring sat_expr's exact statement order (Union: in-order any with short-circuit; Intersection: in-order all; Exclusion: base then subtract; leaves bind their Direct/TTU fields into the closure), keeping the _drive heap-stack protocol and the lowlink memo guard verbatim in the sat/do drivers. Mechanical dispatch-hoisting in the ZT-P1-6 style — control flow, evaluation order and short-circuiting byte-identical — netted by the matrix/hypothesis/conformance suites; check CORRESPONDENCE.md anchors on `check`/`expand` still resolve since the public functions keep their names.

### [unverified · space-compile] Interner keeps refcount and key_of as int-keyed dicts although ids are dense and recycled

**`setengine/engine.py:238`** · category: space · filed impact: low · algorithm change (finder): no

**Evidence (finder, verbatim):**

> `self.id_of: dict[tuple[str, str, str], int] = {}`, `self.key_of: dict[int, tuple[str, str, str]] = {}`, `self.refcount: dict[int, int] = {}` (lines 238-240). Ids are allocated densely from `self._next` with a free-list (`self._free.pop()` / `self._next += 1`, lines 252-256) precisely so they stay compact for roaring — yet two of the three tables are hash maps keyed by those dense ints, costing ~80-100 bytes/entry of dict overhead plus boxed keys, versus 8 bytes/slot for a list indexed by id. For the in-memory backend that is meant to hold whole stores (every subject, object, and §6.4 candidate key is interned), that is an O(live-entities) constant-factor memory multiplier on two of the three interner tables.

**Fix sketch (finder, verbatim, unreviewed):**

> Replace `key_of` and `refcount` with plain lists indexed by id (append on fresh `_next` allocation, overwrite slot on free-list reuse, sentinel None/0 on release). `key(uid)` becomes a list index; `release` writes the sentinel instead of `del`. `_instances_of_type`'s scan iterates the list skipping sentinels (or, better, the maintained names_of_type index from the companion finding). No SetOps-seam interaction, no semantic surface change; `rebuild()` reconstructs identically.
