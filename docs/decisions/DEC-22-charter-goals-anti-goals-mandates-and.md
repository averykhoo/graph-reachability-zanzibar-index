---
type: Decision
id: DEC-22
title: Charter goals, anti-goals, mandates and acceptance criteria (owner, 2026-11-24)
actor: owner
decided: 2026-11-24
session: 2026-11-24a
decision_status: ACCEPTED
body_sha: sha256:7e98ed608197f51a64549c0134f536175b5b135e670e10a1654317504b4c14e0
---

G1 yes, we're building independent implementations, attempting to prove their equivalence through lean and fuzzing, and reasoning from there that the spec is followed precisely

G2 yes, the goal is correctness, and now that Claude can prove the Riemann hypothesis we'll probably resume work on the lean proofs when the new fable and opus models are out

G3 yes as well, as much as this is an exploration of algorithms it should also be usable 

Perf is not a direct goal, but implicitly since this is about indexing perf does have to be a small consideration since if the index runs significantly slower than brute force then it's not a very good index

It's not an openfga clone yes, but that's somewhat due to my personal taste in what I think is pretty in a dsl or api, but compat is nice to have since we can just point to their docs and list a few deviations and how to work around them (or provide a polyfill or compat mode)

No MySQL isn't a rule but yes the backend engine should not be reliant on it, it's more like I'm okay with building SQLite and postgres specific features, but ideally it's fully backend agnostic. But since we're using postgres notifications I guess we're past that

And yes we don't want too many shims in here, things should be mostly either supported or not, without much legacy stuff in it

I don't read lean, I'll leave it to Claude yes, but I feel like fable might be a worthwhile opinion on top of opus

Fuzz on demand is a side effect of me not watching cicd pipelines and never acting on them, and Claude will usually only see the repo and won't check all historical runs, so there's no point running fuzz on a schedule, it's easier to just run on push with a haiku or scripted babysitter 

we do want to prove the wildcards eventually, they're just not the highest priority yet given that proofs take a long time with current opus and fable, if future models are optimized for lean then we'll reprioritize accordingly

Yes to all acceptance criteria, the tldr would be there should be no way to get the different engines into a state where they disagree with each other or fall out of spec with respect to the proof (idk maybe breaking some invariant)
