# Project Memory — vineeth_jobs

Durable, cross-session knowledge about this project that isn't already in `CLAUDE.md`. This is
the sibling repo to `manju_jobs` (Finnish job market, generalist roles) — this one targets global
semiconductor/VLSI roles. Most of the shared infrastructure (local LLM server, priority locking,
GitHub Pages data-serving, dashboard testing setup) is documented once, in
[manju_jobs/memory.md](../manju_jobs/memory.md) — read that first. This file only tracks what's
specific to vineeth_jobs or where it diverges from manju_jobs. Update it whenever something here
goes stale or a new vineeth-specific durable fact/gotcha is discovered; prune outdated entries
rather than letting them accumulate.

## Priority position

vineeth_jobs is the **lowest priority** consumer of the shared LM Studio server: it defers to both
OpenClaw (via `_wait_for_external_llm_idle()` polling `lms ps`) and to manju_jobs (via checking
`MANJU_PRIORITY_LOCK_FILE` before competing for the pipeline lock) before every LLM call. See
manju_jobs/memory.md for the full mechanism — it's identical code here, just on the deferring side
of both checks rather than the claiming side.

## Divergences from manju_jobs's `firebase_app/index.html`

- Default/`'total'` metric chart shows **both** Total+Yes lines; manju's shows Yes only.
- `filterTable()` uses index-based `vals[i]` column access (e.g. `vals[9]` for match status,
  `vals[12]` for applied); manju's uses `.col-*` CSS classes + `data-value` attributes on each
  cell. Same net behavior, different implementation — don't assume a fix ported to one file reads
  identically in the other; check the actual code.
- `applied-counter`'s hover-chart styling (`cursor:help`, dashed border) is baked into the static
  HTML markup here; manju_jobs sets it dynamically in JS with a `_chartHoverAttached` guard flag
  to avoid re-attaching listeners on every re-render. vineeth_jobs's `_attachChartHover` gets
  called unconditionally on every `filterTable()` invocation (pre-existing behavior, not
  introduced by recent chart fixes — worth revisiting if duplicate-listener buildup ever becomes
  a visible perf issue).
- vineeth_jobs's Firebase Hosting deploy uploads far fewer files than manju's (~2 vs ~118) since
  there's no `job_descriptions/` mirror or resume-generation pipeline here — this is expected, not
  a misconfiguration (see also `feedback_verify_large_json`/`project_publish_script` memories in
  the global Claude memory store).

## Groq cloud fallback (added 2026-08-20)

Same `_call_llm_with_fallback` mechanism as manju_jobs (see its memory.md for the full writeup) —
identical code here for the main review call and `analyze_scrape_run_log`. One divergence: the
original review-call payload here didn't set `temperature`/`max_tokens` at all (left as LM
Studio's own defaults), while manju's always used `0.1`/`500`. Harmonized to `0.1`/`500` here too
when wiring up the fallback helper, since the helper needs *some* values and manju's proven
defaults seemed like the safer choice for the same 6-key-JSON-extraction prompt shape — not
verified whether this changes output quality here, worth checking if review results look off after
2026-08-20. This repo has no `classify_requirements_change` function at all (manju-only), so there
was nothing to decide about migrating a third call site.

## Open/unresolved

- No `CLAUDE.md` existed for this repo until 2026-08-14 (just the memory.md pointer, above) —
  manju_jobs has a much fuller one covering `jobs.json` git hygiene, a per-job-id merge driver
  (`git_jobs_merge_driver.py`), and Firestore-based metadata storage (`job_status_store.py`) to
  avoid `jobs.json` write conflicts between machines. None of that tooling exists here
  (`git_jobs_merge_driver.py`, `job_status_store.py`, `setup_merge_driver.ps1`, `.gitattributes`
  are all absent from this repo as of this writing) — if vineeth_jobs's `jobs.json` conflict
  situation turns out to mirror manju's (multi-machine, frequent auto-commits), the same fix would
  apply here; not done yet since it wasn't the ask that surfaced this gap.

---
Last updated: 2026-08-20
