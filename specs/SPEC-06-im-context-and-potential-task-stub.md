---
id: SPEC-06
title: IM Context & Potential Task Stub
status: Planned
depends_on: [SPEC-01]
unlocks: [SPEC-07, SPEC-08]
---

# Outcome

定义并实现 agent 可接入不同 IM 上下文的稳定 provider seam；v1 使用本地 fixture，将消息转换为带证据的 Potential Tasks 和 Open Questions，不接真实用户账号。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-01 Completion Record
- `docs/22-protocol.md`

# Starting State

- runtime/storage/event primitives 可用。
- Potential Task/Open Question schema 已在 SPEC-00 冻结。

# Frozen Decisions

- v1 只实现 provider interface + fixture provider。
- extraction 只能创建 Potential Task/Open Question，不能直接创建 Ready Task。
- 每个候选必须保留可追溯 source evidence。
- 不把真实 IM 消息、token 或账号数据提交到 repo。

# In Scope

- `IMContextProvider` protocol：list conversations、fetch messages、message link/reference。
- 标准化 `ContextItem` schema。
- fixture messages 与 Fixture Provider。
- extraction input/output contract。
- 使用 Manager/Extraction Agent 或 deterministic fixture runner 生成 candidates。
- Potential Task/Open Question 去重、置信度、证据引用。
- triage/promote/dismiss/duplicate/convert-to-question 命令的 storage 支持。
- provider registry/stub 文档。

# Out of Scope

- Slack、飞书、企业微信或其他真实 connector。
- OAuth、webhook、后台持续同步。
- 自动执行或 claim Potential Task。
- 将整段私聊无界注入 Agent。

# Data Contract

`ContextItem` 至少包含 provider、conversation ID、message ID、author、timestamp、text、permalink/reference 和 access scope。

Potential Task 至少包含 title、summary、source refs、confidence、status、dedupe key、created_by。

Open Question 至少包含 question、source refs、blocking、related potential/task IDs、status 和 answer fields。

# Commands

```text
teamctl context ingest --provider fixture [--project <name>]
teamctl potential list [--project <name>]
teamctl potential promote <id>
teamctl potential dismiss <id> --reason <text>
teamctl potential duplicate <id> --of <id>
teamctl potential question <id> --owner <actor> --question <text>
teamctl question add/answer/defer/reopen/close ...
```

Promote 必须原子创建 Confirmed Task 并回写 `promoted_task_id`。

# Acceptance Criteria

- fixture provider 产生标准 Context Items。
- extraction 产生至少一个 Potential Task 和一个 Open Question，均带 message evidence。
- 重复 ingest 不生成重复 candidate。
- Potential Task 不能被 member claim。
- Promote 后一律生成 Draft Confirmed Task 并可追溯来源；另一次显式 ready 校验必填项与 blocking question。
- 未回答的 blocking question 会阻止关联 Task claim。
- provider contract 足够让后续真实 IM 只新增 adapter，不改下游 schema。

# Verification

- provider contract/unit tests。
- fixture ingest snapshot/schema tests。
- 重复 ingest、promote、dismiss、duplicate 幂等测试。
- source evidence 丢失/无权限/空消息负向测试。
- 检查 fixture 不含真实个人信息或凭证。

# Deliverables

- IM provider protocol/registry。
- Fixture Provider 和安全样例数据。
- extraction/triage commands 与 tests。
- Potential Task/Open Question storage operations。

# Handoff Checklist

- Completion Record 记录 fixture 行为和未来 adapter seam。
- SPEC-06 Done；若 SPEC-04 Done 则 SPEC-07 Ready。
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
