---
id: ASK-3
title: GitHub settings for the docs site: Pages source = Actions, github-pages env allows v* tags
brief: user action: two repo settings before the first docs deploy; user asked to be nagged
pri: LATER
size: S
deps: []
related: [TK151]
parent:
labels: []
source: hand
source_hash:
created: 2026-10-20b
moved: 2026-10-21a
updated: 2026-10-21a
closed: 2026-10-21a
---

Only the repo owner can do this: two GitHub settings the docs site needs before its first deploy (`.github/workflows/docs.yml`, TK151). User asked on 2026-10-20b to be reminded ("nag me to change the GitHub settings tomorrow or whenever").

1. Settings -> Pages -> Build and deployment -> Source: **GitHub Actions**.
2. Settings -> Environments -> `github-pages` -> Deployment branches and tags: add a **tag rule `v*`** (by default only the default branch may deploy, so the tag-triggered deploy would be refused). Keep `master` allowed too, for a manual workflow_dispatch deploy.

Close this row once the user confirms both are done. A manual `workflow_dispatch` of the docs workflow on master is a safe first deploy check (it builds and deploys the current docs; the page banner says they describe unreleased code).

## Log

### 2026-10-21a

Both settings confirmed via API 2026-10-21 (Pages build_type=workflow; github-pages env policies: master branch + v* tag). First deploy: workflow_dispatch docs run 39523943275 on master @ 7a6abf7, build+deploy success; gate run 39523926056 green. Site returns 200: / , tutorials/first-check.html, how-to/postgresql.html (curl, first-hand).
