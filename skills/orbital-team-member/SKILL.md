---
name: orbital-team-member
description: Work as a Member in an Orbital Git-native Team Workspace. Use when an agent needs to discover, claim, start, execute, block, inspect, or report a confirmed team task through `/team` or the agent-neutral `teamctl` fallback while preserving current-worktree identity, branch, validation, Report, and canonical-memory guardrails.
---

# Orbital Team Member

Treat the file runtime and current Git worktree binding as the only sources of
identity and task state. Use the deterministic adapter or `teamctl` for every
state change. Never edit runtime JSON directly.

## Establish identity

Require the project owner to join this named-branch worktree once:

```bash
teamctl member join --project <project> --member <id> --agent <agent-type>
```

Treat `--member` as identity selection only for this explicit join. For every
later command, derive `member:<id>` from the unique current-worktree binding.
Never accept or invent a member/actor override. If the worktree is unjoined,
multiply bound, or on a different branch, stop and surface the stable error.

## Execute the member workflow

1. Inspect `/team status` and `/team questions <project>` before choosing work.
2. Claim exactly one confirmed Ready Task with
   `/team claim <project> <task-id-or-query>`. Treat ambiguity and blocking
   questions as hard stops; never select a candidate silently.
3. Read the returned bounded Context Pack. Work only in the bound branch and
   worktree. Do not edit canonical `orbital/PROJECT_STATE.md`, `DECISIONS.md`,
   `LESSONS.md`, or `INDEX.md` as a Member.
4. Enter execution with `/team start <task-id>` before changing task state.
5. Implement the scoped work, run relevant validation, and create a local Git
   commit on the bound branch. Do not merge or push as part of Member report.
6. Submit `/team report <task-id>` with a concise summary, structured validation
   evidence, durable knowledge candidates, risks, and the bound commit when
   useful. Never claim validation passed when it did not.
7. Use `/team block <task-id> <reason>` for a genuine blocker. Report invalid,
   ambiguous, forbidden, or stale states to the user; never repair runtime JSON.

## Command equivalence

Use the same grammar across agent surfaces:

```text
/team claim <project> <query>          → teamctl claim --project <project> --query <query>
/team start <task-id>                  → teamctl task start <task-id>
/team report <task-id> [...]           → teamctl report submit <task-id> [...]
/team block <task-id> <reason>         → teamctl task block <task-id> --reason <reason>
/team status [task-id]                 → teamctl task status [task-id]
/team questions <project>              → teamctl question list --project <project>
/team manager inbox [project]          → teamctl manager inbox [--project <project>]
```

When native slash commands are unavailable, invoke the CLI equivalents
directly or dispatch natural-language arguments with:

```bash
python3 -m orbital_team.member_adapter dispatch \
  --workspace "$PWD" --command '/team status'
```

The dispatcher parses arguments without a shell and rejects `--member`,
`--actor`, and caller-selected `--workspace` overrides.

## Install or remove an adapter

Use the bundled installer only after an explicit installation request:

```bash
python3 skills/orbital-team-member/scripts/install_adapter.py \
  --agent claude-code --target <project> --mode copy
python3 skills/orbital-team-member/scripts/install_adapter.py \
  --agent generic --target <project> --mode link
```

Claude installation adds a project-level `/team` command, this Skill, and a
bounded SessionStart hook. The hook records or refreshes a private local member
Run and prints identity/tasks/questions; it never claims a Task. Generic
installation links or copies only the canonical Skill under `.agents/skills`.
Reverse either operation with the same arguments plus `--uninstall`.

## Guardrails

- Do not bypass blocking questions, Task transitions, Report bindings, or Git
  validation.
- Do not work on the canonical integration branch as a Member.
- Do not write canonical memory, machine-managed runtime, session, ledger,
  tool-result, or sub-agent transcript files.
- Do not bind Manager to Codex, Claude, or another provider. Manager and Member
  are roles independent of agent type.
- Keep provider transcripts optional. Record only a transcript path the
  provider actually supplied; otherwise leave it unavailable.
