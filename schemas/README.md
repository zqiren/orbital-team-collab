# Schemas

`v1/orbital-team.schema.json` is the normative JSON Schema Draft 2020-12 bundle for Team Workspace protocol version `1.0`.

Consumers validate a runtime file or domain object against the matching `$defs` fragment, for example:

- `registry.json` → `#/$defs/registry`
- `project.json` → `#/$defs/project`
- `members.json` / a member entry → `#/$defs/memberStore`, `member`
- `tasks.json` / a Confirmed Task → `#/$defs/taskStore`, `task`
- `potential-tasks.json` / a Potential Task → `#/$defs/potentialTaskStore`, `potentialTask`
- `open-questions.json` / an Open Question → `#/$defs/openQuestionStore`, `openQuestion`
- a Report → `#/$defs/report`
- one `events.jsonl` line → `#/$defs/event`
- an Integration Job → `#/$defs/integrationJob`
- a Knowledge Pack/Proposal/Summary → `#/$defs/knowledgePack`, `knowledgeProposal`, `knowledgeChangeSummary`
- a local run/session record → `#/$defs/runRecord`
- ManagerRunner JSON I/O → `#/$defs/managerRunRequest`, `managerRunResult`
- an IM fixture message → `#/$defs/imMessage`
- a CLI/API error → `#/$defs/errorResponse`

The bundle freezes domain object shape and mutable collection envelopes. The recoverable operation journal is a deterministic storage concern implemented in SPEC-01; it must retain stable idempotency/event IDs and target revisions without changing these object definitions.
