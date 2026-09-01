---
description: Execute the Orbital Team Member protocol through the current worktree binding
argument-hint: claim|start|report|block|status|questions|manager ...
allowed-tools: Bash(python3 -m orbital_team.member_adapter:*)
disable-model-invocation: true
---

Use the `orbital-team-member` Skill installed in this project. Treat the text
below as `/team` arguments, never as shell syntax:

```text
$ARGUMENTS
```

Pass the complete text as the value of `--command` to this deterministic
adapter from the project worktree:

```text
python3 -m orbital_team.member_adapter dispatch --workspace . --command "/team $ARGUMENTS"
```

Run that command once. Return its structured stdout or stable error without
rewriting runtime JSON, selecting another member/actor, or silently resolving
ambiguous tasks or blocking questions.
