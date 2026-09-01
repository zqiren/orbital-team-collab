---
id: SPEC-04
title: Event-driven Manager Integration
status: Planned
depends_on: [SPEC-02]
unlocks: [SPEC-05, SPEC-07]
---

# Outcome

成员 Report Submitted 后，无需用户提醒，由 repo 自带的 `teamd` 将文件事件转换为 Integration Job，并通过可替换 `ManagerRunner` 启动新的 Manager Agent Run，完成审查、验证、merge 和 Task 状态闭环。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-02 Completion Record
- `docs/21-architecture.md`
- `docs/22-protocol.md`

# Starting State

- Report、Task、Event 和 storage primitives 可用。
- 成员 report 会原子产生 `report.submitted`。

# Frozen Decisions

- Manager 是 project role，不绑定 agent 类型。
- v1 每个 Report 触发新的短生命周期 Manager Run，不向长期窗口注入。
- `teamd` 不保存隐藏业务状态；Job/Event/结果均在文件中。
- 每 project 同时最多一个 active integration job。
- merge 成功后才允许进入知识编译。

# In Scope

- `teamd` event tail/watch 与 crash resume。
- Integration Job store/state machine。
- project-level manager lock。
- `ManagerRunner` protocol 与 custom command runner。
- 至少一个实际可验证的 agent runner adapter；其他 runner 可为 manifest/stub。
- Manager integration prompt/brief 生成。
- inbox/review/integrate/request-changes/block 命令。
- branch/commit/report 绑定校验。
- merge、测试、结果事件、retry/idempotency。
- 自动权限 guardrails。

# Out of Scope

- Knowledge Proposal 的语义生成和 apply（SPEC-05）。
- 真实云 queue、长期 manager session、remote push。
- 自动解决复杂冲突。
- 任意仓库外命令或写入。

# Integration Job States

```text
Queued → Running → Merged → Awaiting Knowledge
Queued/Running → Changes Requested
Queued/Running → Blocked
Running → Retryable → Queued
Any terminal result remains idempotent
```

必须明确 Job 与 Task 的同步转换；失败不得让 Task 停留在无法解释的 Integrating。

# Event Contract

- 输入：`report.submitted`。
- teamd 以 report ID 生成稳定 job idempotency key。
- runner 结果写入 integration record，再发结果事件。
- 成功：`integration.completed`，Task/Job 进入 awaiting knowledge 状态。
- 需修改：`integration.changes_requested`。
- 风险/冲突：`integration.blocked`，必要时创建 Open Question。

# ManagerRunner Contract

输入至少包括：workspace、project slug、job/report IDs、Manager Skill/brief 路径、允许工具/命令、timeout。输出必须结构化说明 outcome、merge commit、validation、risk/open question 和日志位置。

Runner 实现不得把 provider session 作为事实来源；重试必须重新从文件恢复。

# Guardrails

允许：读取、审查绑定 diff、项目内验证、无冲突 merge、Task/Job 状态更新、创建 Open Question。

禁止：force push、remote push、repo 外写入、删除 repo/worktree、合并未绑定 commit、测试失败标 Done、绕过项目锁。

# Acceptance Criteria

- report.submitted 在无用户提示下生成 Integration Job 并启动配置的 runner。
- 两个同时 report 的任务被串行集成。
- 同一 report 重放不会重复 merge。
- runner crash 后 Job 可重试且状态一致。
- 测试失败进入 Changes Requested/Blocked，不进入 Done。
- merge 成功记录 merge commit，并发出 `integration.completed`。
- 替换 runner 配置不改变 Task/Report schema。

# Verification

- 使用 fake/deterministic runner 完整测试事件、锁、retry 和幂等。
- 使用临时 Git repo 进行真实 clean merge、冲突、失败验证测试。
- 至少一次受控的实际 agent runner smoke；若环境不具备 agent CLI，明确记录为 blocker 而非伪造。
- 模拟 teamd 重启后从 event offset/job state 恢复。

# Deliverables

- `teamd` 与运行入口。
- Integration Job/record 实现。
- ManagerRunner protocol、adapter/manifest。
- manager integration commands/brief。
- 自动化测试和 fixture。

# Handoff Checklist

- Completion Record 记录真实 runner smoke、失败恢复和权限限制。
- SPEC-04 Done；SPEC-05 Ready，若 SPEC-06 Done 则 SPEC-07 Ready。
- 更新 PROJECT_STATE、INDEX、DECISIONS/LESSONS。

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
