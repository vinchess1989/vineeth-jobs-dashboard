# CLAUDE.md

Instructions for any Claude Code session (interactive or via a skill/slash-command) working in this repo.

## Read and maintain `memory.md`

`memory.md` (this directory) holds durable, cross-session project knowledge — infrastructure
gotchas, architecture notes, things that were nearly broken by mistake, non-obvious root causes
of bugs that got fixed. **Read it at the start of any nontrivial work in this repo** — it'll save
you from re-diagnosing something already solved (e.g. the local LLM's priority-locking setup, or
why GitHub Pages must stay enabled).

**Update it whenever you learn something a future session would need** — a new gotcha, a fixed
bug with a non-obvious cause, a changed architecture/config, a mistake narrowly avoided. Don't
log routine work (a normal scraper commit, a one-off answered question) — only what's durable
and non-derivable from just reading the current code. Keep entries current: correct or remove
ones that turn out to be wrong or stale rather than letting them accumulate. The sibling repo
(`manju_jobs`) has its own `memory.md` and a fuller `CLAUDE.md` (git hygiene, `jobs.json`
read-only rules, merge driver) — shared infrastructure is documented once, in whichever repo it
more naturally belongs to, with the other cross-referencing it; check there too since this repo's
own git-hygiene tooling is thinner (see `memory.md`'s Open/unresolved section).
