# 36 — Team Dashboard

SPEC-07 提供 repo 自带的 Python loopback server 与静态 HTML/CSS/ES modules。Dashboard 没有数据库、Node 构建链或前端业务状态机：每次请求都从 shared file runtime 重建 projection，所有 mutation 都委托给 `MemberWorkflow` 或 `IMContextWorkflow` 的 domain command。

## 启动

```bash
teamctl dashboard \
  --workspace /path/to/project \
  --actor human:default-manager \
  --host 127.0.0.1 \
  --port 8765
```

打开 `http://127.0.0.1:8765/`。Host 必须是 IPv4 loopback literal；`0.0.0.0`、LAN IP、hostname 和远程部署均被拒绝。`--port 0` 可让 OS 选择临时端口，启动 JSON 会打印实际地址。

`--actor` 是受信任的 server 启动配置，不来自浏览器：

- actor 必须是 `human:<id>`；格式无效或未知 identity 时整个 Dashboard 只读。
- actor 等于 Project `active_manager_id` 时，该 Project 开启 Human 写入口。
- 已登记但不是 active Manager 的 identity 可读、不可写；跨 Project active Manager 不一致时同样只读。
- request body 的 `actor` 字段或 `X-Orbital-Actor` header 一律以 `E_FORBIDDEN_ACTOR` 拒绝，不能覆盖 server binding。

v1 采用单 OS 用户信任边界，不宣称远程认证。runtime 继续使用 `0700` directory / `0600` sensitive files。

## Views 与刷新

- Overview：Project、active Manager、成员、runner availability、pending Integration Jobs、本地 Run。
- Tasks：Backlog、Ready、Claimed、In Progress、Submitted、Integrating、Blocked、Done；展示 assignee、Report、Integration 与 blocking Question。
- Potential Tasks：confidence、source evidence、triage、Promote、dismiss、duplicate、convert-to-question。
- Open Questions：blocking、owner、related Task，以及 answer/defer/reopen/close。
- Activity & Knowledge：最近 250 条 project event、schema-valid Knowledge Change Summary 与四个 canonical memory 文件的 bounded preview。

前端每 2 秒重新请求 Project projection，不刷新整个应用。projection revision 是当前规范数据的 SHA-256；server restart 不做 migration，直接从文件恢复。外部 CLI/domain mutation 会在下一次轮询出现。

若规范文件损坏，API 返回结构化 `E_CORRUPT_RUNTIME`，页面保留上一次成功 view 并显示错误，不以空数据覆盖文件。event log 只有 crash-truncated tail 时会保留源文件并在 projection 中显示 warning。

## 受控写入口

HTTP route 只允许以下 Human commands：

```text
task.create       task.edit       task.ready
potential.triage potential.promote potential.dismiss
potential.duplicate potential.question
question.add question.answer question.defer question.reopen question.close
```

Draft edit 由 `MemberWorkflow.edit_task` 验证，只允许未分配 Draft 的合法字段；Promote 委托 SPEC-06 并始终生成 Draft；blocking Question 继续由既有 ready/claim guard 判断。没有 claim/report/merge/knowledge-apply route，Dashboard 不冒充 Member 或 Manager 执行高权限动作。

写请求必须使用 `Content-Type: application/json`，body 上限 64 KiB，未知命令/字段拒绝。API 不提供 runtime JSON 文件路径或通用文件写接口。

## Run logs 与 knowledge preview

stdout/stderr/transcript 作为不可信文本使用 DOM `textContent` 展示；静态前端不使用 `innerHTML`。日志读取同时要求：

- RunRecord schema 有效；
- 相对路径严格位于 `runs/<run-id>/`；
- resolve 后仍在该 Project 私有 runtime 内；
- 单次最多读取 64 KiB。

绝对 transcript、任意 Project 文件、`..` 或 symlink escape 显示 unavailable。Knowledge preview 只接受 D13 的四个 canonical memory allowlist，单文件最多 8 KiB。页面明确标记这些日志只存在本机且不进入 Git。

## 验证边界

当前沙箱拒绝任何 loopback listen socket（`127.0.0.1:0` 返回 EPERM），因此 HTTP smoke 使用同一个 `BaseHTTPRequestHandler` 的内存 request/response transport，覆盖静态资源、projection、POST mutation、轮询 payload 与 actor header 拒绝；真实浏览器/socket bind 需在普通本机环境按上述启动命令复测。UI 未做营销截图，按计划留给 SPEC-09。
