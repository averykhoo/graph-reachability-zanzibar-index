---
type: Decision
id: DEC-23
title: 'Charter follow-up: ORM backend abstraction, fuzz local and CI, why G-1 is an attempt'
actor: owner
decided: 2026-11-24
session: 2026-11-24b
decision_status: ACCEPTED
body_sha: sha256:288d555528d11ea5b87d77cef85637ca944147f1fd76add74680e13a8ea06f50
---

Oh for the backend, sqlalchemy or sqlmodel are probably a good orm layer to use as an abstraction that we can just select SQLite as the backend for, and should probably work with any db, and I'm okay to maintain the psycopg thing for the locks or pubsub for faster replication, mostly as an example, but it should still work without it. Also it might work with redis but we don't really need that in here, although I'm guessing it won't be hard to swap it over

Fuzz and hypothesis can be local before push, although I guess since GitHub minutes are free for public projects it doesn't really matter, or we could do both

G1 is an attempt mostly because we haven't been able to write a comprehensive proof yet, if it was easy enough I think we would strengthen the goal to say we want it proven equivalent with code pins to lean from python comments or decorators or something
