---
id: SPEC-07
title: Tasks / Potential Tasks / Open Questions Dashboard
status: Planned
depends_on: [SPEC-04, SPEC-06]
unlocks: [SPEC-08]
---

# Outcome

提供 repo 自带的本地 Team Dashboard，在不引入外部服务或第二事实源的前提下展示并操作 Confirmed Tasks、Potential Tasks、Open Questions、Manager integrations 和 project knowledge changes。

# Required Reading

- `specs/EXECUTION_PROTOCOL.md`
- SPEC-04、SPEC-06 Completion Records
- `docs/21-architecture.md`
- `docs/22-protocol.md`

# Starting State

- 三类对象 storage operations 可用。
- Integration Jobs/Events 可读。
- runtime path resolver 可从 canonical repo 定位 shared data。

# Frozen Decisions

- 文件仍是唯一事实来源。
- Dashboard 的本地 server 是 storage adapter/UI host，不维护独立数据库。
- 所有写操作复用和 `teamctl` 相同的 domain/storage 层。
- Dashboard 可以添加 Tasks/Open Questions，并 triage Potential Tasks。
- server 启动时绑定已登记的 `human:<member-id>` actor；未知 actor 时只读，浏览器请求不能覆盖 actor。
- server 默认只监听 loopback；runtime 根目录使用当前用户私有权限。完整 transcript 仅在 runner/adapter 能提供时展示，并明确其本地敏感数据属性。

# In Scope

- 本地 dashboard 启动入口。
- Project selector。
- Confirmed Tasks Kanban/list：新增、编辑合法字段、状态/assignee/report/integration 可见。
- Potential Tasks：来源证据、promote、dismiss、duplicate、转 Open Question。
- Open Questions：新增、回答、defer、close、blocking、关联对象。
- Activity Feed：claim/report/integration/knowledge events。
- Pending Integrations 与 Manager status。
- 本地 Manager/member run 记录、stdout/stderr 和可选 session transcript；明确标注仅本机持久化且不进入 Git。
- Project Knowledge 最近变更摘要及文件链接/预览。
- 文件变化刷新、空状态、损坏/锁/runner offline 错误状态。
- UI/domain tests 和最小可访问性。

# Out of Scope

- 云部署、账号、多人远程浏览。
- 在 UI 重写业务状态机。
- 代码 diff 全功能 review IDE。
- 完整 IM 客户端。

# Required Views

1. Overview：项目、Manager、成员、运行状态。
2. Tasks：Backlog/Ready/Claimed/In Progress/Submitted/Integrating/Done/Blocked。
3. Potential Tasks：evidence + triage actions。
4. Open Questions：blocking、owner、answer、related work。
5. Activity/Knowledge：事件与 canonical memory changes。

# Write Semantics

- Add Task 默认进入 Draft，只有满足必填项且无 blocking question 才可设 Ready。
- Promote Potential Task 走 domain command 并一律生成 Draft，不能前端复制对象或自动 Ready。
- Answer blocking question 后，只解除阻塞条件；是否 Ready 仍按 Task 规则判断。
- UI 对 claim/report/merge 主要展示，不冒充成员/Manager 身份执行高权限动作。
- Knowledge view 只消费 SPEC-00 冻结的 knowledge change summary schema，不从 markdown diff 猜测第二套结构。

# Acceptance Criteria

- 页面同时清晰区分两类 Task storage 和 Open Questions。
- UI 添加 Task/Open Question 后文件立即更新且 schema 有效。
- Potential Task 可从证据页 Promote，并生成可追溯 Confirmed Task。
- blocking question 在 Task 上可见并阻止其 Ready/claim 行为。
- 成员 claim/report 与 Manager integration/knowledge 事件无需刷新整个应用即可看见，或在明确轮询间隔内出现。
- server 重启后完全从文件恢复，无数据库迁移。
- runtime 文件损坏时页面显示错误而不是覆盖数据。

# Verification

- domain route/API tests（仅作为本地 UI adapter）。
- React/component tests 或所选 UI 栈等价测试。
- 真实临时 runtime 的浏览器 smoke：add task、promote、answer、观察事件。
- server restart/file external update 测试。
- build/lint/test 全部执行并记录。

# Deliverables

- dashboard backend/adapter 与 frontend。
- start script。
- UI tests/fixtures。
- 必要的截图只在 SPEC-09 统一交付，本 spec 不做营销包装。

# Handoff Checklist

- Completion Record 记录启动命令、端口行为、刷新机制和已知浏览器限制。
- SPEC-07 Done；若 SPEC-03/05/06 均 Done 则 SPEC-08 Ready。
- 更新 PROJECT_STATE、INDEX、必要的 LESSONS。

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
