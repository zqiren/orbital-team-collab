---
id: SPEC-07
title: Tasks / Potential Tasks / Open Questions Dashboard
status: Done
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

- Final status: Done
- Outcome achieved: 实现 Python IPv4 loopback Team Dashboard、可重建 file projection、active-Human actor-bound command adapter、静态 HTML/CSS/ES module UI 与 `teamctl dashboard` 入口；覆盖三类工作对象、Integration/Report/Run、Activity、Knowledge Summary/preview、bounded local logs、轮询刷新和结构化错误。
- Files changed: 新增 `src/orbital_team/dashboard.py`、`src/orbital_team/dashboard_static/{index.html,styles.css,app.js}`、`tests/test_dashboard.py`、`docs/36-team-dashboard.md`；扩展 `MemberWorkflow.edit_task`、CLI/package exports 与 wheel static package data；更新本 spec、Spec Index 及 Orbital state/index/lessons。
- Verification run: `python3 -m compileall -q src tests`；`python3 -m pytest -q tests/test_dashboard.py`；`python3 -m pytest -q`；`PYTHONPATH=src python3 -m orbital_team.cli dashboard --help`；`python3 -m pip wheel --no-deps --no-build-isolation ...` 并检查 wheel 静态资源；`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git diff --check`；静态资源 direct-JSON-write/innerHTML/credential/绝对路径扫描与只读 `git status --short`。
- Verification result: SPEC-07 专项 9/9、全量 100/100 通过；真实临时 runtime 覆盖 projection→domain mutation、Draft edit、blocking ready gate、Potential Promote、actor override/unknown/cross-Project 拒绝、Integration/Knowledge/Run/log、损坏零覆盖、外部更新/重启恢复；内存 HTTP transport 覆盖 GET/static/POST/poll payload/403。
- Deviations from spec: 无产品契约、依赖或架构偏离；因当前 sandbox 对 `127.0.0.1:0` listen 返回 EPERM，spec 的真实 browser/socket smoke 改为同一 `BaseHTTPRequestHandler` 的内存 HTTP smoke，未伪造真实浏览器成功，普通本机复测列为限制。
- Decisions recorded: 无；直接遵循 D11/D12/D14 的 actor、loopback、单 package/storage 与无 Node/DB 边界。
- Lessons recorded: 当前执行沙箱禁止 loopback listen socket；Dashboard HTTP 测试用可注入 handler transport，真实 bind 留普通本机验证。
- Known limitations: 未在本 sandbox 运行真实浏览器或 live socket；v1 polling 固定 2 秒且 activity 上限 250 event；仅 active Manager 对应 Human actor 可写，其他已登记 Human identity 暂为只读；runner availability 只投影 manual/manifest 配置，不探测 provider 进程健康。
- Working tree / commit: 实现与 handoff 文件保留在未提交工作树，未 commit/push、未写 `.git`；交由主 session 复测与 checkpoint。
- Next spec readiness: SPEC-03/05/06/07 均 Done，SPEC-08 已标 Ready。
