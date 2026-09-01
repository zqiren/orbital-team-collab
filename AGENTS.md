# AGENTS.md — read this first

Onboarding for any agentic tool landing in this project — Claude Code, Codex,
Cursor, Copilot, or otherwise. Read this before touching anything.

Orbital generated this file when the project was created, and never rewrites
it. Edit it freely; your changes will not be overwritten. Where it disagrees
with a hand-authored `CLAUDE.md` or anything under `orbital/instructions/`,
those win.

## This project

- **Project:** Agent-collaboration
- **Orbital agent:** Agent-collaboration
- **Workspace:** the directory this file sits in.

## The memory system

Orbital is an agent orchestration platform: a management agent works on this
project across many sessions and keeps what it learns on disk instead of
starting cold each time. That memory lives in `orbital/`, beside this file. It
is as much yours as Orbital's — read it to recover context, and update it when
you learn something worth keeping.

These files accumulate as the project runs. One that does not exist yet simply
means nothing has been recorded there; it is not a broken install. In a
brand-new project this file may be the only one present.

- **`orbital/PROJECT_STATE.md`** — what is true *right now*: current focus,
  work in progress, blockers, next steps. Read it first, every session.
  Overwrite stale lines in place rather than appending a dated entry.
- **`orbital/DECISIONS.md`** — settled decisions and the reasoning behind
  them. Read before re-litigating anything that sounds already decided. Append
  when a decision lands; supersede the old entry outright if they conflict —
  never leave two contradictory ones standing.
- **`orbital/LESSONS.md`** — hard-won gotchas and playbooks from past
  failures. Append whenever you recover from a non-obvious mistake or find a
  workaround worth remembering next time.
- **`orbital/INDEX.md`** — the navigation map: one line per path. Start here
  when you do not know where something lives, and update it when files move or
  a new area appears.
- **`orbital/instructions/`** — standing goals, scope, and the user's own
  directives for whoever operates this workspace. Read these to understand
  *why* the conventions here exist.
- **`orbital/skills/`** — reusable multi-step procedures, captured once a
  workflow has repeated. Check here before inventing an approach from scratch.
- **`orbital/sub_agents/<slug>/MEMORY.md`** — private memory for one
  sub-agent. If you are that agent, this file is yours to read and append to
  across dispatches.

`orbital/INDEX.md` describes the layout as it actually is today. Where this
file's map has drifted from it, believe INDEX.md.

## Write posture

Full read/write on everything listed above — no append-only games, no asking
permission first. Update what needs updating. The guidance on *how* each file
wants to be edited (overwrite vs. append vs. supersede) is a courtesy to the
next reader, not a gate.

The one hands-off zone is machine-managed runtime state, which nobody
hand-edits — agent or human:

- `orbital/sessions/` — session transcripts
- `orbital/ledger/` — cost and usage records
- `orbital/tool-results/` — captured tool output
- `orbital/sub_agents/*/*.jsonl` — sub-agent dispatch transcripts

Reading those while debugging is fine; editing them corrupts state Orbital
depends on.

## Recovering context

1. `orbital/PROJECT_STATE.md` — where things stand.
2. `orbital/DECISIONS.md` — what is already settled.
3. `orbital/LESSONS.md` — recent entries especially.
4. `orbital/INDEX.md` — where everything lives.
