---
id: SPEC-02
title: /project Command & Member Workflow
status: Planned
depends_on: [SPEC-01]
unlocks: [SPEC-03, SPEC-04]
---

# Outcome

实现 agent-neutral 的成员工作协议：从项目和任务查询开始，原子认领、加载上下文、推进状态，并从 Git 工作成果生成结构化 Report。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-01 Completion Record
- `docs/22-protocol.md`

# Starting State

- runtime kernel、registry、locks、events 可用。
- 目标临时 repo 可创建至少两个 worktree。

# Frozen Decisions

- 唯一匹配时 `/project <project> <query>` 同时 claim 和返回 context。
- 多个匹配、无匹配、已被领取或存在 blocking question 时不得改变任务状态。
- 只有 Confirmed Task 的 Ready 状态可被领取。
- Report Submitted 后其他成员仍不可领取该任务。

# In Scope

- member identity/join。
- project/task resolve：ID 精确匹配优先，之后使用确定性标题/标签匹配；v1 不要求 embedding。
- claim/start/status/block/report。
- Task Context Pack 组装。
- Git branch、commit、changed files、diff summary、验证结果收集。
- Report schema 校验。
- 状态转换、事件和幂等测试。

# Out of Scope

- Slash command adapter/Hook。
- Manager integration 与自动 runner。
- IM extraction、dashboard。
- 自动替成员修改或提交代码。

# Public Commands

```text
teamctl member join --project <name> --member <id> --agent <type>
teamctl project <project-name> <task-id-or-query>
teamctl task start <task-id>
teamctl task status [task-id]
teamctl task block <task-id> --reason <text>
teamctl report <task-id> [--summary ...] [--validation ...]
teamctl questions <project-name>
```

# Context Pack

返回内容至少包括：Task、acceptance criteria、关联路径、dependencies、相关项目状态/决定/lesson 指针、Open Questions、成员/branch 信息、Report 要求。设置明确大小预算；优先返回摘要与路径，不无界内联全部 memory。

# State and Concurrency Requirements

- claim 在 project lock 内完成 resolve recheck + state write + event append。
- member 必须是 project 成员。
- branch/commit 必须属于当前 Git repo。
- report actor 必须是当前 assignee。
- 同一 commit/task 重复 report 返回原 report，不生成重复提交事件。
- block/report 的非法转换给出稳定错误码。

# Acceptance Criteria

- Alice/Bob 并发认领同一 Ready Task 只有一个成功。
- 唯一标题匹配能 claim；歧义查询返回候选且不 claim。
- blocking Open Question 阻止 claim，并返回关联问题。
- 成员能获得受大小限制的 Context Pack。
- report 自动包含可验证 Git metadata，并让 Task 进入 Submitted。
- 所有动作可在 events 中追溯。

# Verification

- 状态机单元测试。
- 两进程并发 claim 测试。
- 临时 Git repo/worktree report 集成测试。
- 重复命令幂等测试。
- 非 assignee、错误 commit、blocking question、歧义查询负向测试。

# Deliverables

- member/task/report command implementation。
- Context Pack builder。
- 状态机与测试 fixtures。
- CLI usage help。

# Handoff Checklist

- Completion Record 完整记录命令与错误语义。
- SPEC-02 Done；SPEC-03 和 SPEC-04 Ready。
- 更新 PROJECT_STATE、INDEX、必要的 DECISIONS/LESSONS。

## Completion Record

- Final status: —
- Outcome achieved:
- Files changed:
- Verification run:
- Verification result:
- Deviations from spec:
- Decisions recorded:
- Lessons recorded:
- Known limitations:
- Working tree / commit:
- Next spec readiness:
