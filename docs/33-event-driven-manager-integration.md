# 33 — Event-driven Manager Integration

SPEC-04 adds the file-driven Manager pipeline. A persisted
`report.submitted` event is enough for `teamd` to create and drain an
Integration Job; no long-lived agent session is required.

## Run the daemon

```bash
teamd --workspace /path/to/canonical/workspace --once
teamd --workspace /path/to/canonical/workspace --watch --interval 2
```

`--once` drains all currently runnable work. `--watch` polls the file event
log, while startup reconciliation also scans immutable Reports, Tasks and
Jobs so a deleted cursor or a crash between file writes does not lose work.

The Project `runner` value selects an injected runner or a manifest named
`demo/runners/<runner>.json`. Versioned seed can set this value before
`teamctl init`; `manual` leaves Jobs queued for explicit Manager commands.
The shipped `builtin` manifest runs the deterministic subprocess adapter.
The Codex and Claude Code files are provider manifests and require their
respective local CLI and execution environment.

## Manager commands

```bash
teamctl manager inbox [--project apollo]
teamctl manager review <job-id>
teamctl manager merge <job-id> --expected-head <sha> --validation '<json>'
teamctl manager request-changes <job-id> --change <text>
teamctl manager block <job-id> --reason <text> --question <text>
teamctl manager resume <job-id>
```

`manager merge` is the controlled implementation of the integration action.
It rechecks the Report branch/commit, canonical HEAD, clean workspace and
validation evidence inside project and Git mutation locks. Runner policy does
not expose raw `git merge`, `git commit` or `git push`.

## State and recovery

- `queued`, `running` and `retryable` occupy the per-project integration slot.
- `merged` records the local merge commit and emits `integration.merged`.
- `awaiting_knowledge` releases the slot while the Task stays `integrating`.
- validation failure becomes `changes_requested`; conflict or missing human
  judgment becomes `blocked` with an Open Question.
- a project Manager execution lock distinguishes a live runner from a
  crash-released `running` Job. Retry always reloads the file runtime.
- if the controlled merge persisted before the runner could write result JSON,
  restart trusts the guarded merge record/event and never merges twice.

SPEC-04 only prepares the mechanical Knowledge Pack. It never emits
`integration.completed`; SPEC-05 may do that only after knowledge apply and
Task/Job completion.

## Runner boundary and logs

Each run receives a schema-valid request, a private Task snapshot, Report,
Job, context and a brief containing Task acceptance criteria. It must write a
schema-valid result to the declared path; stdout is not a business result.
Run metadata, brief, inputs, stdout and stderr live under the private runtime
`projects/<slug>/runs/<run-id>/` and are not committed.

Manifest environment cannot override `GIT_CONFIG_GLOBAL`,
`GIT_CONFIG_SYSTEM`, `HOME`, `PATH` or `PYTHONPATH`. On POSIX, runner timeout
kills the whole spawned process group; other platforms terminate the direct
process as the standard-library fallback.

## Verification note

The deterministic subprocess adapter completed real clean merges, validation
failure, conflict, serialization, replay and crash recovery in temporary Git
repositories. A real Codex CLI smoke was attempted in the delivery sandbox;
the CLI started but its nested in-process app-server initialization was denied
with `Operation not permitted`, so no external-provider success is claimed.
