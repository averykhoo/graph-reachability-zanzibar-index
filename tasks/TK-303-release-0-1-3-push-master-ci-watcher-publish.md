---
type: Task
id: TK-303
title: "Release 0.1.3: push master, CI watcher, publish dry run, then the v0.1.3 tag on the owner's word, install trial + installed_smoke.py"
brief: TK-185 step 9 remainder; the tag only on the owner's explicit word; release.md is the recipe
pri: NEXT
state: open
deps: []
source: session 2026-11-20a
created: 2026-11-20
moved: 2026-11-20a
updated: 2026-11-25a
---

Release 0.1.3: push master, CI watcher, publish dry run, then the v0.1.3 tag on the owner's word, install trial + installed_smoke.py.

The remainder of TK-185's step 9 (TK-185 closed 2026-11-20a; its local half landed in 3b5ea66, 0d5bf34 and d2effc4).

- The push of efc8de3..d2effc4, plus this session's record commits, was blocked in session 2026-11-20a by the harness permission classifier. The owner pushes, or grants the push.
- The ten-phase gate was COVERED at d2effc4 (2026-11-20, `scripts/gate_status.py`), lint clean, fuzz 5 modules x 6 seeds green. Re-check `gate_status.py` on the tree being pushed: record commits since d2effc4 stale the tiles that read `tasks/` and `HANDOFF.md`.
- Order: push master; a background CI watcher on the pushed SHA; the `publish.yml` dry run (`workflow_dispatch`); then ASK the owner for the `v0.1.3` tag (a tag is a release: only on the owner's explicit word); watch the publish run; confirm 0.1.3 is live on PyPI; the fresh-user install trial plus `scripts/installed_smoke.py` against the wheel.
- HANDOFF's "0.1.2 is the newest release" line changes only at the tag, not before.

## Traps

- A tag is a RELEASE: push one only on the owner's explicit word (CLAUDE.md, Running things).
- `publish.yml` and the `pypi` environment are the PyPI trusted publisher: never rename either.

## Read first

- docs/runbooks/release.md
- docs/tk185-0.1.3-batch-2026-11-20.md

## Log

- 2026-11-25a (claude-code/claude-opus-5-5): SALVAGE (2026-11-25a, from gitignored .scratch/s24a/release-prep.md, the release-prep agent's log for session 2026-11-24a, file dated 2026-11-24 13:29; READ by the 2026-11-25a salvage agent, not re-run; no run ids were recorded). The publish dry-run step has a result: lines F/G read "gate/docs/publish-dryrun all success; upload step skipped; artifacts zanzibar_index-0.1.3-py3-none-any.whl, zanzibar_index-0.1.3.tar.gz", after push range 0602841..4937211 (line E: commit 4937211). Precheck (line G-precheck): publish.yml has no dispatch inputs and its upload step is gated `if: github.ref_type == 'tag'`, so a workflow_dispatch on master has ref_type branch and skips the upload (attestation still runs; the deploy job uses environment pypi). So the dry run is DONE on 4937211; still owed here: the v0.1.3 tag on the owner's word, then the install trial + installed_smoke.py.
- 2026-11-25a (claude-code/claude-opus-5-5): Correction to the SALVAGE line above (2026-11-25a): release-prep.md does not name the SHA the publish dry run was dispatched on; "on 4937211" is REASONED from line order (E: commit 4937211 and push range, then F/G), not READ. A dry run on the current master head before tagging is the safe reading.
