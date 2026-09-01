---
id: SPEC-06
title: IM Context & Potential Task Stub
status: Done
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

- Final status: Done
- Outcome achieved: 实现 agent-neutral `IMContextProvider`/registry、离线 Fixture Provider、标准 ContextItem 校验、bounded deterministic extraction，以及 Potential Task/Open Question 的 ingest、去重、triage/promote/dismiss/duplicate/convert 与 Question lifecycle；Promote 原子生成带来源的 Draft Task，blocking Question 继续复用 MemberWorkflow ready/claim gate。
- Files changed: 新增 `src/orbital_team/im_context.py`、`demo/im-fixtures/messages.json`、`tests/test_im_context.py`、`docs/35-im-context-and-potential-task-stub.md`；扩展 package exports 与 `teamctl` context/potential/question 命令；更新本 spec、Spec Index 与 Orbital state/index。
- Verification run: `python3 -m compileall -q src tests`；`python3 -m pytest -q tests/test_im_context.py`；`python3 -m pytest -q`；`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git diff --check`；fixture credential/真实 provider/network import 扫描与只读 `git status --short`。
- Verification result: SPEC-06 专项 10/10、全量 91/91 通过；provider/schema、evidence、重复 ingest、Draft-only Promote、blocking ready gate、权限/空消息/缺 evidence、不可 claim/未 triage、dismiss/duplicate/convert 幂等、Question owner/lifecycle、CLI 及 Promote 中断恢复均覆盖。
- Deviations from spec: 无 schema、依赖、网络、安全边界或产品契约偏离；v1 extraction 选择 spec 允许的 deterministic fixture runner，并以文档化字段 grammar 替代真实 Extraction Agent。CLI 额外允许 `--fixture <local-json>`，只选择本地输入，不扩大 provider 权限。
- Decisions recorded: 无；实现直接遵循 D8、D11、D12、D14 的冻结契约。
- Lessons recorded: 无新增跨 session gotcha；崩溃恢复沿用既有 operation journal + canonical reconciliation 模式。
- Known limitations: 未接入或 smoke 任何真实 IM/账号/OAuth/webhook；fixture runner 只识别文档化 bounded grammar，不做自然语言模型抽取；默认 fixture path 面向 repo workspace，其他 workspace 需显式 `--fixture`。
- Working tree / commit: 实现与 handoff 文件保留在未提交工作树，未 commit/push、未写 `.git`；交由主 session 复测与 checkpoint。
- Next spec readiness: SPEC-07 的 SPEC-04/SPEC-06 依赖均 Done，已标 Ready；SPEC-08 仍等待 SPEC-07。
