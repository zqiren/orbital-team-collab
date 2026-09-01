# Versioned demo seed

This directory is deterministic initialization input for the synthetic `Apollo`
project. It contains no credentials, transcripts, real messaging data, or absolute
user paths. It seeds two independent Ready Tasks and selects the fully offline
`builtin` Manager runner. Initialize it with:

```bash
teamctl init --project Apollo --workspace . --seed demo/seed
```

The `demo: true` manifest flag is the explicit demo marker accepted by
`teamctl reset --runtime-only --project apollo`. Non-demo runtimes additionally
require `--yes`.

For the complete disposable multi-worktree story, run
`python3 demo/scripts/team_demo.py doctor` followed by `setup`, `start`, and
`reset`; see `docs/37-demo-fixture-and-orchestration.md`.
