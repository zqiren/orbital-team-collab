# 22 — Orbital Team Workspace Protocol

> 状态：Protocol/schema 1.0 规范性契约；SPEC-01～09 实现与交付已收敛（2026-09-01）
> Schema bundle：`schemas/v1/orbital-team.schema.json`  
> 本文中的 MUST / MUST NOT / SHOULD 是实现、adapter 与最终验收的持续约束。

## 1. 版本与编码

- Protocol/schema version：`1.0`。
- JSON：UTF-8、object key 输出按字典序稳定化；持久文件末尾保留换行。
- 时间：UTC RFC 3339，例如 `2026-09-01T08:30:00Z`。
- hash：小写 SHA-256 hex；Git commit 接受仓库实际 object format 的完整 hex。
- mutable store 带从 `0` 开始单调递增的 `revision`。
- 未知 major version MUST 拒绝写入；未知字段默认拒绝，除非 schema 明确允许。

## 2. 标识符

### Actor

```text
human:<member-id>
member:<member-id>
manager:<manager-id>
system:teamd
system:fixture
```

Actor MUST 来自 trusted adapter/config，不能仅信任浏览器或 agent 自报。

### Object IDs

| 对象 | 规则 | 示例 |
|---|---|---|
| Project | lowercase slug：`[a-z][a-z0-9-]{1,31}` | `apollo` |
| Task | `<project>-T-<4+ digit sequence>` | `apollo-T-0001` |
| Potential Task | `<project>-P-<sequence>` | `apollo-P-0001` |
| Open Question | `<project>-Q-<sequence>` | `apollo-Q-0001` |
| Report | `<task-id>-R-<sequence>` | `apollo-T-0001-R-0001` |
| Integration Job | `<project>-J-<sha256(report-id)[0:12]>` | `apollo-J-9b1a60c0185f` |
| Knowledge Proposal | `<job-id>-KP-<sequence>` | `apollo-J-…-KP-0001` |
| Knowledge Summary | `<proposal-id>-KS-<sequence>` | `apollo-J-…-KP-0001-KS-0001` |
| Event / Run | UUID v4；Run 前缀 `<project>-RUN-` | `apollo-RUN-<uuid>` |

Project lock 内分配 sequence；删除对象不得复用。Task ID 因 project slug 唯一而在同一 runtime workspace 全局唯一。

## 3. 规范对象

本节给出最小可读示例；字段类型、required 与 enum 以 schema bundle 的 `$defs` 为准。

### 3.1 Registry 与 Project

```json
{
  "projects": {
    "apollo": {
      "created_at": "2026-09-01T08:00:00Z",
      "display_name": "Apollo",
      "project_file": "projects/apollo/project.json",
      "slug": "apollo"
    }
  },
  "revision": 1,
  "schema_version": "1.0"
}
```

`registry.json` 只保存 stable lookup，不复制 active Manager 等可变配置。`project.json` 使用 schema `$defs/project`，保存 canonical workspace、allowed worktree roots、active Manager、runner 与 seed provenance。绝对 workspace path 只存在本地 runtime，不得进入版本化 seed 或交付物。

Registry map key MUST 等于 registration/project slug；`members.json`、`tasks.json`、`potential-tasks.json`、`open-questions.json` 使用对应 Store schema，`items` map key MUST 等于对象自身 ID。JSON Schema 验证形状，domain validator 负责这些跨字段一致性。

### 3.2 Member

```json
{
  "agent_type": "claude-code",
  "branch": "team/alice/apollo-T-0001",
  "id": "alice",
  "joined_at": "2026-09-01T08:05:00Z",
  "role": "member",
  "worktree": "/tmp/orbital-team-demo/alice"
}
```

### 3.3 Confirmed Task

```json
{
  "acceptance_criteria": ["GET /health returns 200"],
  "assignee": null,
  "blocking_question_ids": [],
  "created_at": "2026-09-01T08:10:00Z",
  "created_by": "human:lead",
  "dependencies": [],
  "description": "Add a health endpoint.",
  "id": "apollo-T-0001",
  "labels": ["backend"],
  "paths": ["src/health.py"],
  "project_slug": "apollo",
  "revision": 1,
  "state": "ready",
  "title": "Add health endpoint",
  "updated_at": "2026-09-01T08:12:00Z"
}
```

`blocking_question_ids` 是索引/缓存，claim 时 MUST 重新读取 Open Question store；Open/Deferred 且 `blocking=true` 的关联问题是最终阻塞条件。

### 3.4 Potential Task

```json
{
  "confidence": 0.84,
  "created_at": "2026-09-01T08:15:00Z",
  "created_by": "system:fixture",
  "dedupe_key": "fixture:fixture-1:m-42:v1",
  "evidence": [{
    "conversation_id": "fixture-1",
    "message_id": "m-42",
    "permalink": null,
    "provider": "fixture",
    "quote": "We should add retry metrics."
  }],
  "id": "apollo-P-0001",
  "project_slug": "apollo",
  "promoted_task_id": null,
  "revision": 0,
  "state": "new",
  "summary": "Track retries by a stable dimension.",
  "suggested_title": "Add retry metrics"
}
```

### 3.5 Open Question

```json
{
  "answer": null,
  "blocking": true,
  "created_at": "2026-09-01T08:20:00Z",
  "created_by": "manager:lead",
  "evidence": [],
  "id": "apollo-Q-0001",
  "owner": "human:lead",
  "project_slug": "apollo",
  "question": "Should retries be counted per provider or per task?",
  "related": {
    "job_ids": [],
    "potential_task_ids": [],
    "proposal_ids": [],
    "task_ids": ["apollo-T-0001"]
  },
  "revision": 0,
  "state": "open"
}
```

### 3.6 Report

Report 创建后不可变；更改代码必须提交新 commit 与新 Report。

```json
{
  "base_commit": "1111111111111111111111111111111111111111",
  "branch": "team/alice/apollo-T-0001",
  "changed_files": ["src/health.py", "tests/test_health.py"],
  "commit": "2222222222222222222222222222222222222222",
  "diff_summary": "Add health endpoint and tests.",
  "id": "apollo-T-0001-R-0001",
  "knowledge_candidates": ["Health checks must not call external services."],
  "project_slug": "apollo",
  "risks": [],
  "submitted_at": "2026-09-01T09:00:00Z",
  "submitted_by": "member:alice",
  "summary": "Implemented GET /health.",
  "task_id": "apollo-T-0001",
  "validation": [{
    "command": "pytest -q",
    "outcome": "passed",
    "summary": "12 passed"
  }]
}
```

### 3.7 Event

```json
{
  "actor": "member:alice",
  "data": {
    "report_id": "apollo-T-0001-R-0001",
    "task_id": "apollo-T-0001"
  },
  "id": "812c72e2-72c7-4b68-b2d9-d52660f89e85",
  "idempotency_key": "report:apollo-T-0001:2222222222222222222222222222222222222222",
  "project_slug": "apollo",
  "schema_version": "1.0",
  "timestamp": "2026-09-01T09:00:00Z",
  "type": "report.submitted"
}
```

### 3.8 Integration Job

```json
{
  "attempt": 0,
  "block_kind": null,
  "created_at": "2026-09-01T09:00:01Z",
  "id": "apollo-J-9b1a60c0185f",
  "idempotency_key": "integration:apollo-T-0001-R-0001",
  "merge_commit": null,
  "project_slug": "apollo",
  "report_id": "apollo-T-0001-R-0001",
  "revision": 0,
  "run_id": null,
  "state": "queued",
  "task_id": "apollo-T-0001",
  "updated_at": "2026-09-01T09:00:01Z"
}
```

### 3.9 Knowledge Proposal

```json
{
  "created_at": "2026-09-01T09:05:00Z",
  "created_by": "manager:lead",
  "id": "apollo-J-9b1a60c0185f-KP-0001",
  "job_id": "apollo-J-9b1a60c0185f",
  "patches": [{
    "base_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "content": "# PROJECT_STATE\n\n- Health endpoint is implemented.\n",
    "operation": "updated",
    "path": "orbital/PROJECT_STATE.md"
  }],
  "project_slug": "apollo",
  "report_id": "apollo-T-0001-R-0001",
  "revision": 0,
  "state": "proposed",
  "summary": "Record the completed health endpoint.",
  "task_id": "apollo-T-0001"
}
```

v1 patch path allowlist 精确为 `orbital/PROJECT_STATE.md`、`orbital/DECISIONS.md`、`orbital/LESSONS.md`、`orbital/INDEX.md`。`orbital/instructions/` 进入 Git durable layer 但由 Human 管理，Manager 只读；schema 的 `instruction` category 为后续显式授权保留。`content` 是期望的完整 UTF-8 文件结果；apply 前 MUST 验证 base hash，禁止让模型直接执行任意 patch command。

### 3.10 Knowledge Change Summary

```json
{
  "actor": "manager:lead",
  "applied_at": "2026-09-01T09:06:00Z",
  "changes": [{
    "category": "state",
    "operation": "updated",
    "path": "orbital/PROJECT_STATE.md",
    "summary": "Recorded the completed health endpoint."
  }],
  "job_id": "apollo-J-9b1a60c0185f",
  "knowledge_commit": "4444444444444444444444444444444444444444",
  "project_slug": "apollo",
  "proposal_id": "apollo-J-9b1a60c0185f-KP-0001",
  "report_id": "apollo-T-0001-R-0001",
  "schema_version": "1.0",
  "source_commit": "3333333333333333333333333333333333333333",
  "summary_id": "apollo-J-9b1a60c0185f-KP-0001-KS-0001"
}
```

### 3.11 Run Record

```json
{
  "actor": "manager:lead",
  "agent_type": "custom",
  "ended_at": null,
  "id": "apollo-RUN-5fb65a21-9d48-410d-a1b0-f8b2d77a9302",
  "job_id": "apollo-J-9b1a60c0185f",
  "log_paths": {
    "stderr": "runs/apollo-RUN-5fb65a21-9d48-410d-a1b0-f8b2d77a9302/stderr.log",
    "stdout": "runs/apollo-RUN-5fb65a21-9d48-410d-a1b0-f8b2d77a9302/stdout.log",
    "transcript": null
  },
  "project_slug": "apollo",
  "provider_session_id": null,
  "revision": 0,
  "started_at": "2026-09-01T09:00:02Z",
  "state": "running",
  "task_id": "apollo-T-0001"
}
```

### 3.12 ManagerRunner I/O

每次 runner invocation MUST 从 JSON request 文件读取并只向指定 result path 写一个 JSON result：

- request 使用 `#/$defs/managerRunRequest`：`phase`（integration/knowledge）、workspace/allowed roots、project/task/job/run IDs、Skill/brief/input paths、结构化 command policies、timeout、result path。每条 policy 固定 argv prefix、cwd scope 和是否允许追加参数；执行 MUST 使用 argv + `shell=false`，不得把模型文本拼接进 shell command。
- result 使用 `#/$defs/managerRunResult`：outcome、merge/proposal ID、validation、changes requested、risk、Open Question IDs、completed time。
- phase=integration 只接受 `merged|changes_requested|blocked|retryable`；phase=knowledge 只接受 `proposed|blocked|stale|no_change`。`no_change` 仍须生成一个 `patches=[]` 的可追溯 Proposal ID。domain guard MUST 拒绝 phase/outcome 不匹配或 schema-invalid 的结果。
- runner 的 exit code/stdout/session state 不等于业务 outcome；result file 缺失或无效视为 retryable/blocked policy 输入。

## 4. Confirmed Task 状态机

状态值：`draft`、`ready`、`claimed`、`in_progress`、`submitted`、`integrating`、`changes_requested`、`blocked`、`done`、`cancelled`。

| From → To | Actor | Preconditions | Event | 幂等行为 |
|---|---|---|---|---|
| none → draft | Human/Manager | project 存在；ID/title 合法 | `task.created` | request key 相同返回原 Task |
| draft → ready | Human/Manager | 必填字段齐；依赖 Done；无 Open/Deferred blocking question | `task.ready` | 已 Ready 返回当前对象 |
| ready → claimed | Member | 已 join；唯一 resolve；未分配；无 blocking question | `task.claimed` | 同 assignee+request 返回 Context Pack；其他 actor 冲突 |
| claimed → in_progress | assignee Member | worktree/branch binding 有效 | `task.started` | 已 In Progress 返回当前对象 |
| in_progress → submitted | assignee Member | commit 属于绑定 branch/repo；Report schema/验证证据有效 | `report.submitted` | `(task, commit)` 返回原 Report |
| submitted → integrating | system:teamd | Report 存在；deterministic Job 已创建 | `integration.queued` | 同 Report 只存在一个 Job |
| submitted/integrating → changes_requested | Manager | 结构化 review result；未标 Done | `integration.changes_requested` | 同 Job result 重放无变化 |
| changes_requested → in_progress | assignee Member | 原 assignee 存在；新修改将使用新 commit/report | `task.resumed` | 已 In Progress 返回当前对象 |
| in_progress → blocked | assignee Member/Manager | reason 非空；记录 `blocked_from` | `task.blocked` | 相同 reason/request 返回当前对象 |
| submitted → blocked | Manager | integration 风险/缺失决定；关联 Open Question | `integration.blocked` | 同 Job block result 重放无变化 |
| blocked → blocked_from | Human/Manager/assignee Member | blocking question 均已 Answered/Closed；reason resolved | `task.unblocked` | 已恢复返回当前对象 |
| integrating → done | system:teamd | merge commit 已记录；Knowledge Proposal 已 Applied 并 commit，或产生 validated no-change summary | `task.completed` | proposal/summary apply key 保证只完成一次 |
| 任意非终态 → cancelled | Human/Manager | reason 非空；若已 merge 必须记录“不回滚代码” | `task.cancelled` | 已 Cancelled 返回当前对象 |

补充规则：

- `Claimed → Submitted` 非法，MUST 先 start。
- Ready Task 后续出现 blocking question 时可保持 Ready，但 derived `claimable=false`；已执行中的 Task 是否转 Blocked由创建问题的同一 command 显式决定。
- Knowledge 冲突不把 Task 从 Integrating 改为 Blocked；它关联 Open Question 并等待 resume。
- Done/Cancelled 是终态。Cancelled 不自动 revert 已合并 Git commit。

## 5. Potential Task 状态机

| From → To | Actor | Preconditions | Event | 幂等行为 |
|---|---|---|---|---|
| none → new | system:fixture/Provider extractor | evidence key 唯一 | `potential_task.created` | 同 evidence+extractor 返回原对象 |
| new → triaged | Human/Manager | triage note/owner 已记录 | `potential_task.triaged` | 已 Triaged 返回当前对象 |
| triaged → promoted | Human/Manager | 未 duplicate/dismiss；source evidence 完整 | `potential_task.promoted` + `task.created` | 原子生成一个 Draft Task 并回写 ID |
| new/triaged → dismissed | Human/Manager | reason 非空 | `potential_task.dismissed` | 已 Dismissed 返回当前对象 |
| new/triaged → duplicate | Human/Manager | target object 存在 | `potential_task.duplicated` | 相同 target 返回当前对象 |
| new/triaged → dismissed + Question Open | Human/Manager | question/owner 合法 | `potential_task.converted_to_question` + `question.created` | 原子创建一个 Question 并回写 `converted_question_id` |

Promote 永远生成 `draft`，不会自动 Ready。`promoted`、`dismissed`、`duplicate` 是终态。

## 6. Open Question 状态机

| From → To | Actor | Preconditions | Event | 幂等行为 |
|---|---|---|---|---|
| none → open | Human/Manager/System | question、owner、related refs 合法 | `question.created` | request key 相同返回原对象 |
| open/deferred → answered | owner Human/Manager | answer 非空 | `question.answered` | 相同 answer 返回当前对象；不同 answer 冲突 |
| open → deferred | owner Human/Manager | reason；可选 revisit time | `question.deferred` | 相同字段返回当前对象 |
| deferred → open | owner Human/Manager | reopen reason | `question.reopened` | 已 Open 返回当前对象 |
| answered/deferred → closed | owner Human/Manager | close reason | `question.closed` | 已 Closed 返回当前对象 |

Open/Deferred 且 `blocking=true` 会阻止关联 Task claim/ready。`question.answered` 若关联 blocked knowledge proposal，MUST 在同一 transaction 后发出 `knowledge.resume_requested`；Answer 只解除问题条件，不自动把 Draft Task 置 Ready。

## 7. Integration Job 状态机

状态值：`queued`、`running`、`retryable`、`merged`、`awaiting_knowledge`、`changes_requested`、`blocked`、`done`。

| From → To | Actor | Preconditions | Event | Slot |
|---|---|---|---|---|
| none → queued | system:teamd | Report Submitted；无同 report Job | `integration.queued` | 占用 |
| queued → running | system:teamd | project 无其他占 slot Job；runner 可用 | `integration.started` | 占用 |
| running → retryable | system:teamd | crash/timeout；未确认 merge | `integration.retryable` | 占用 |
| retryable → queued | system:teamd | retry policy 允许 | `integration.requeued` | 占用 |
| running → changes_requested | Manager | review/tests 不通过；建议结构化 | `integration.changes_requested` | 释放、该 Job 终止 |
| running → blocked | Manager | 高风险/冲突/缺决定；Open Question 已创建 | `integration.blocked` | 释放 |
| running → merged | Manager | report/commit binding 有效；验证通过；clean merge commit 已持久化 | `integration.merged` | 释放 |
| merged → awaiting_knowledge | system:teamd | Knowledge Pack 已准备 | `knowledge.prepared` | 不占用 |
| awaiting_knowledge → blocked | Manager | proposal 冲突/缺决定；关联 Open Question | `knowledge.blocked` | 不占用 |
| blocked → awaiting_knowledge | system:teamd | `knowledge.resume_requested` 且 block_kind=knowledge | `knowledge.resumed` | 不占用 |
| blocked → queued | Human/Manager + system | integration block 已解决且尚未 merge | `integration.requeued` | 占用 |
| awaiting_knowledge → done | system:teamd | proposal Applied + knowledge commit，或 validated no-change summary；Task Done | `integration.completed` | 不占用、终态 |

`retryable` 仍占 slot，防止 crash job 被后续 merge 越过；超过 retry policy 后必须转 Blocked 并释放。`awaiting_knowledge` 不阻塞后续代码集成。

## 8. Knowledge Proposal 状态机

| From → To | Actor | Preconditions | Event | 幂等行为 |
|---|---|---|---|---|
| none → proposed | Manager | merge 已完成；Pack/hash 完整；patch path allowlisted；no-change 可用空 patches | `knowledge.proposed` | 同 job+inputs hash 返回原 Proposal |
| proposed → validated | system:teamd | schema、memory rules、base hash 全通过 | `knowledge.validated` | 已 Validated 返回当前对象 |
| proposed/validated → stale | system:teamd | 任一 target base hash 变化 | `knowledge.stale` | 同 observation 无重复 event |
| proposed/validated → blocked | Manager/System | 事实冲突、缺决定或非法语义 | `knowledge.blocked` | 关联一个 Open Question |
| stale/blocked → 保持终态；另建 proposed | Manager | resume run 重编，新 inputs hash | `knowledge.recompiled` | 新 proposal sequence；旧对象不可回写 |
| validated → applied | system:teamd | project lock；base hash recheck；一次性 apply key | `knowledge.applied` | 重放返回同 Summary，不重复写 |

apply 顺序固定：确认 canonical workspace 除本 pipeline 变更外干净 → 再次 hash 校验 → atomic replace 各 memory 文件 → 只 stage allowlisted memory path → 创建独立本地 knowledge commit → 写 Knowledge Summary（记录 source/knowledge commit）→ Task/Job Done events。崩溃由 operation journal 恢复。不得 amend code merge，不得 remote push；无 knowledge change 时不创建空 commit，而是写 `changes=[]`、`knowledge_commit=null` 的 no-change summary。

## 9. Run Record 状态机

`starting → running → succeeded|failed|timed_out|cancelled`。Run 状态不直接决定业务成功；只有 schema-valid Manager result 经 domain guard 处理后才能改变 Task/Job。

## 10. `/team` 与 `teamctl`

### Member-facing protocol

| Product command | Deterministic CLI equivalent |
|---|---|
| `/team claim <project> <query>` | `teamctl claim --project <project> --query <query>` |
| `/team start <task-id>` | `teamctl task start <task-id>` |
| `/team report <task-id>` | `teamctl report submit <task-id> ...` |
| `/team block <task-id> <reason>` | `teamctl task block <task-id> --reason <reason>` |
| `/team status [task-id]` | `teamctl task status [task-id]` |
| `/team questions <project>` | `teamctl question list --project <project>` |
| `/team manager inbox` | `teamctl manager inbox` |

Slash adapter MUST 把参数传入 domain CLI/library，不得自己读写 JSON。

### Human/Manager CLI

```text
teamctl init --project <name> --workspace <path> [--seed <path>]
teamctl member join --project <slug> --member <id> --agent <type> --worktree <path>
teamctl task create --project <slug> --title <text> [...]
teamctl task ready <task-id>
teamctl task cancel <task-id> --reason <text>
teamctl potential triage|promote|dismiss|duplicate|question <potential-id> [...]
teamctl question add|answer|defer|reopen|close ...
teamctl manager inbox
teamctl manager handoff --project <slug> --to <manager-id>
teamctl manager request-changes|block|resume <job-id> [...]
teamctl status [--project <slug>]
```

所有 mutation SHOULD 接受 `--request-id`；adapter 重试 MUST 复用该 ID。

### Manager role handoff

`human:<active-manager-id>` 可把 role handoff 给同 Project 已登记且 `role=manager` 的目标 identity。Project 存在 `running` 或 `retryable` Job 时拒绝；Queued Job 可由新 Manager 接手。命令按 `project → events` 锁顺序原子更新 `project.json.active_manager_id` 并发出 `manager.handed_off`。它不迁移 provider session；新 Manager 下一次 run 仍从文件冷启动。

## 11. Project/Task resolve

### Project

1. exact slug match；
2. display name Unicode casefold exact match；
3. 否则 not found 或 ambiguous，不做 fuzzy 自动选择。

### Task query（在已解析 Project 内）

1. exact Task ID；
2. normalized title exact match（Unicode casefold、连续空白折叠）；
3. ID/title/label 的 normalized token substring match；
4. 返回按 Task ID 排序的候选。

claim resolve 包含所有非终态 Task，不能为了“只剩一个 Ready”而隐藏已 Claim 的同名 Task。只有恰好一个候选才继续；随后在 project lock 内重新 resolve、检查 Ready/assignee/blocking/dependency 并写入。零个或多个候选都 MUST 零副作用。

## 12. Context Pack

claim 成功返回：Task、acceptance criteria、paths、dependencies、related Open Questions、member/worktree/branch、Report 要求，以及 PROJECT_STATE/DECISIONS/LESSONS/INDEX 的摘要与路径。

- 默认序列化预算 32 KiB，硬上限 64 KiB。
- 优先摘要和路径，不无界内联 memory、IM、transcript 或 Git diff。
- 截断时必须返回 `truncated=true` 和 omitted paths/count。

## 13. Manager permissions

### 自动允许

- 读取 repo/runtime；审查 Report 绑定 diff。
- 在 repo/worktree 内运行 allowlisted 验证命令。
- 对目标 integration branch 做无冲突 merge。
- 写结构化 result、状态、event、Open Question。
- 对 allowlisted canonical memory 做 hash-guarded Knowledge Proposal apply。
- 只 stage allowlisted memory path 并创建本地 knowledge commit；不 push。

### 自动禁止

- remote push、force push、删除 repo/worktree、写仓库外。
- 合并未绑定 Report 的 commit；跨 Project 读取敏感 runtime。
- 测试失败标 Done；用自然语言 stdout 代替结构化 result。
- proposal path traversal、symlink escape、静默覆盖事实冲突。
- 自动回答需要 Human owner 的 Open Question。

违反 guardrail 返回 stable error，并进入 Blocked/Changes Requested；不得“尽力继续”。

所有 Git 写操作必须经过受控 domain command：`teamctl manager merge <job-id>` 或 knowledge apply。命令取得 project + git mutation lock 后重新校验 target HEAD、Report/commit binding 与工作树；ManagerRunner policy MUST NOT 暴露裸 `git merge`、`git commit`、`git push`。若 HEAD 与 review 基线不同，返回 retryable/stale，不使用过期审查结果继续。

## 14. IM provider contract

Provider 输出 message envelope；`access_scope` 由 adapter 给出且下游必须保留：

```json
{
  "access_scope": "fixture",
  "conversation_id": "fixture-1",
  "message_id": "m-42",
  "permalink": null,
  "provider": "fixture",
  "sender": "user-1",
  "text": "We should add retry metrics.",
  "timestamp": "2026-09-01T08:15:00Z"
}
```

Extractor output 只能为 `potential_task` 或 `open_question`，并携带 evidence。幂等键：`im:<provider>:<conversation-id>:<message-id>:<extractor-version>`。

## 15. 稳定错误语义

所有失败输出统一：

```json
{
  "error": {
    "code": "E_TASK_AMBIGUOUS",
    "details": {"candidates": ["apollo-T-0001", "apollo-T-0002"]},
    "message": "Task query matched multiple tasks.",
    "retryable": false
  },
  "ok": false,
  "schema_version": "1.0"
}
```

| Code | 语义 | Exit |
|---|---|---:|
| `E_USAGE` | 参数/命令错误 | 2 |
| `E_NOT_GIT_REPO` | 不在 Git worktree | 3 |
| `E_PROJECT_NOT_FOUND` / `E_MEMBER_NOT_FOUND` / `E_TASK_NOT_FOUND` | 对象不存在 | 3 |
| `E_PROJECT_AMBIGUOUS` / `E_TASK_AMBIGUOUS` | resolve 不唯一 | 3 |
| `E_TASK_NOT_READY` / `E_TASK_ALREADY_CLAIMED` | claim precondition 失败 | 4 |
| `E_BLOCKING_QUESTION` | Open/Deferred blocking question | 4 |
| `E_INVALID_TRANSITION` | 状态转换非法 | 4 |
| `E_DEPENDENCY_INCOMPLETE` | Task 依赖未 Done | 4 |
| `E_IDEMPOTENCY_CONFLICT` | 同 key 不同 payload | 4 |
| `E_FORBIDDEN_ACTOR` / `E_READ_ONLY` | actor 无权限 | 5 |
| `E_WORKTREE_MISMATCH` / `E_COMMIT_MISMATCH` | Git binding 非法 | 5 |
| `E_GUARDRAIL_VIOLATION` | Manager 动作越界 | 5 |
| `E_SCHEMA_VERSION` / `E_CORRUPT_RUNTIME` | schema/文件损坏 | 6 |
| `E_LOCK_TIMEOUT` / `E_INTEGRATION_SLOT_BUSY` | 可重试并发冲突 | 4 |
| `E_VALIDATION_FAILED` / `E_MERGE_CONFLICT` / `E_STALE_PROPOSAL` | integration/knowledge 未通过 | 4 |
| `E_DIRTY_WORKSPACE` | canonical workspace 有 pipeline 外未提交改动 | 4 |
| `E_RUNNER_UNAVAILABLE` / `E_RUNNER_TIMEOUT` | 外部 runner 问题 | 7 |
| `E_INTERNAL` | 未分类内部错误；不得带 secret | 8 |

错误时默认不改变状态。若失败发生在已持久化 transaction 中，response 必须包含 operation ID，recovery 按 journal 完成或返回已完成 result。

## 16. Event types

v1 至少支持：

```text
project.created              member.joined
task.created                 task.ready
task.claimed                 task.started
task.blocked                 task.unblocked
task.resumed                 task.cancelled
report.submitted             integration.queued
integration.started          integration.retryable
integration.requeued         integration.merged
integration.changes_requested integration.blocked
potential_task.created       potential_task.triaged
potential_task.promoted      potential_task.dismissed
potential_task.duplicated    potential_task.converted_to_question
question.created
question.answered            question.deferred
question.reopened            question.closed
knowledge.prepared           knowledge.proposed
knowledge.validated          knowledge.stale
knowledge.blocked            knowledge.resume_requested
knowledge.resumed            knowledge.recompiled
knowledge.applied            task.completed
integration.completed        manager.handed_off
run.started                  run.finished
```

Consumer MUST ignore and preserve unknown minor-version event types；unknown major schema version MUST stop with `E_SCHEMA_VERSION`。

## 17. 安全与隐私

- runtime/log 默认当前用户私有；Dashboard loopback-only。
- versioned seed 必须使用 synthetic identities/evidence，不含真实 IM、transcript、token 或绝对用户路径。
- log view 做路径 allowlist，不允许 `../`、绝对任意路径或 symlink escape。
- stdout/stderr/transcript 是不可信敏感内容；不得作为 shell/HTML 直接执行，UI 必须 text-escape。
- reset 只允许已解析 common dir 下、带 schema/marker 的精确 runtime target，并要求显式 `--yes` 或 demo marker。
