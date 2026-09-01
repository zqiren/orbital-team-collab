---
name: orbital-team-manager
description: Compile a merged Orbital Team Workspace Integration Job into durable canonical project knowledge. Use during the knowledge phase after a Job reaches Awaiting Knowledge to classify a Knowledge Pack, Report, Task, merged diff, and current PROJECT_STATE/DECISIONS/LESSONS/INDEX; produce a controlled full-file Knowledge Proposal or no-change result; and surface stale baselines or decisions needing human judgment.
---

# Orbital Team Manager — Knowledge Compilation

Treat the file runtime and canonical workspace as the only sources of truth.
Provider-session memory is disposable. On every run, read the request, brief,
Knowledge Pack, Report, Task, and all declared canonical memory files again.

## Classify durable knowledge

- `orbital/PROJECT_STATE.md`: keep only facts true now, active work, blockers,
  and next steps. Replace stale facts; never append a session changelog.
- `orbital/DECISIONS.md`: record settled, cross-session decisions and reasons.
  Supersede an old entry only when the evidence clearly establishes the new
  decision. If authority or intent is unclear, block for human judgment.
- `orbital/LESSONS.md`: add reusable, non-obvious failure recovery or
  playbooks. Deduplicate without weakening an existing complete lesson.
- `orbital/INDEX.md`: maintain one concise navigation bullet per durable path.
  Reflect created, removed, or moved assets; never put status, dates,
  decisions, or long summaries here.

Exclude ordinary implementation detail, transient debugging, raw transcripts,
repeated Report text, and speculation. Read `orbital/instructions/` when useful,
but never propose changes to it.

## Compile the proposal

1. Confirm `phase` is `knowledge`, the Job is `awaiting_knowledge`, and the
   Knowledge Pack identifies the source merge commit and current memory hashes.
2. Compare the Report and merged diff with current canonical memory. Preserve
   each file's leading format-contract comment, every daemon-managed
   `<!--mem ...-->` comment byte-for-byte in place, its single required H1,
   and final newline.
3. Create at most one full-file patch per changed memory file. Use only the four
   allowlisted paths above. Use `updated` with the Pack's exact SHA-256 for an
   existing file, or `created` with `base_sha256: null` for a missing file. Do
   not delete or move canonical memory files in v1.
4. Submit patches only through the request's `knowledge-propose` controlled
   command. Never edit canonical memory or runtime JSON directly.
5. Write exactly one schema-valid `managerRunResult` to `result_path`:
   - `proposed`: the controlled command created a non-empty Proposal;
   - `no_change`: it created a traceable Proposal with `patches=[]`;
   - `blocked`: facts conflict or a human-owned decision is missing;
   - `stale`: the Pack or memory baseline changed before proposal creation.

A patch has this shape:

```json
{
  "base_sha256": "<pack hash or null>",
  "content": "<complete UTF-8 file ending with newline>",
  "operation": "updated",
  "path": "orbital/PROJECT_STATE.md"
}
```

Set `proposal_id` for `proposed`, `no_change`, and proposal-specific `stale`
results. Give `blocked` and `stale` a precise `risk_summary`. Stdout is not a
business result.

## Guardrails and recovery

- Never run raw `git merge`, `git commit`, `git push`, force push, amend, or
  stage files. Validation and apply own all Git mutation and locking.
- Never touch `orbital/sessions/`, `orbital/ledger/`, `orbital/tool-results/`,
  sub-agent JSONL transcripts, paths outside the workspace, or any path not in
  the four-file allowlist.
- Never overwrite a hash mismatch. Return `stale`; a later short-lived run must
  reload files and compile a new Proposal.
- Never silently resolve contradictory decisions. Return `blocked` so the
  domain layer creates a linked Open Question. After
  `knowledge.resume_requested`, reload the answered question and recompile.
- Do not claim completion or create commits. Only validated apply may create a
  separate local knowledge commit and then mark the Task and Job Done.
- A no-change Proposal must remain empty; apply records
  `knowledge_commit=null` and must not create an empty commit.
