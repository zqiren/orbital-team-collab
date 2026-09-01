# 35 — IM Context 与 Potential Task Stub

SPEC-06 提供一个只读、agent-neutral 的 `IMContextProvider` seam。v1 唯一内置 provider 是 `FixtureIMProvider`：它只读取本地 synthetic JSON，不导入网络库、不连接真实 IM 账号，也不保存 token。

## ContextItem 与 provider seam

Provider 实现三个操作：列出 conversation、按 conversation 获取标准 ContextItem、生成 message reference。ContextItem 使用冻结 schema `#/$defs/imMessage`，包含 provider/conversation/message identity、sender、UTC timestamp、bounded text、permalink/reference 与 `access_scope`。下游只依赖这个 protocol；未来 connector 只需新增 adapter，不修改提取或 triage store。

默认安全 fixture 位于 `demo/im-fixtures/messages.json`。它只含明确标记的 synthetic identity。fixture extractor 使用固定的 bounded grammar：

```text
TASK: <suggested title>
SUMMARY: <bounded summary>
QUESTION: <open question>
BLOCKING: true|false
OWNER: human:<id>|manager:<id>
```

没有 `TASK`/`QUESTION` 标记的消息只作为 ContextItem 返回，不生成候选。`TASK` 与 `SUMMARY` 必须同时出现。所有候选保留 provider、conversation ID、message ID、permalink 与 quote evidence；空消息、schema-invalid evidence、跨 project access scope 均在写 store 前拒绝。

## 命令

```bash
teamctl context ingest --provider fixture --project apollo
teamctl potential list --project apollo
teamctl potential triage apollo-P-0001 --note "scope reviewed"
teamctl potential promote apollo-P-0001
teamctl task ready apollo-T-0001

teamctl potential dismiss apollo-P-0002 --reason "not planned"
teamctl potential duplicate apollo-P-0003 --of apollo-P-0001
teamctl potential question apollo-P-0004 \
  --owner human:default-manager --question "Which behavior is intended?"

teamctl question add --project apollo --question "Which rollout window?" \
  --owner human:default-manager --blocking --task apollo-T-0001
teamctl question answer apollo-Q-0001 --answer "Use the staged rollout."
teamctl question defer apollo-Q-0002 --reason "Waiting for plan" --until 2026-09-08T00:00:00Z
teamctl question reopen apollo-Q-0002 --reason "Plan received"
teamctl question close apollo-Q-0002 --reason "Decision recorded"
```

在 repo 以外运行时，可用 `context ingest --fixture <local-json>` 显式指定本地 fixture。省略 `--project` 只在 runtime 恰有一个 Project 时允许。

## 状态与恢复

- ingest 只能创建 `new` Potential Task 或 `open` Open Question，绝不创建 Confirmed Task。
- dedupe identity 包含 provider/conversation/message/extractor version；相同 identity 内容改变会报 `E_IDEMPOTENCY_CONFLICT`，不会静默覆盖证据。
- Promote 只接受 `triaged`，在 project lock 内创建一个 `draft` Task、写入 `source_potential_task_id`、回写 `promoted_task_id`，并把相关 blocking Question 关联到新 Task。
- Draft 必须另行执行 `teamctl task ready`；Open/Deferred blocking Question 会继续通过既有 MemberWorkflow 阻止 ready/claim。
- dismiss、duplicate、convert-to-question 是终态。Question mutation 由当前 Project active Manager 对应的 trusted human actor 执行，不能传入任意 actor 冒充 owner。
- 所有 mutation 复用 ProjectStore、RuntimeLock、IdempotencyGuard 与 EventLog。Promote 若在 Task 已写入但 Potential 回写前中断，重放会按 `source_potential_task_id` 恢复，不重复创建 Task/event。

## 已知边界

v1 不包含 Slack/飞书/企业微信 adapter、OAuth、webhook、后台轮询或真实账号 smoke；也不把无界 IM transcript 注入 member Context Pack。真实 provider 接入留给后续范围，必须继续提供标准 ContextItem 与可信 `access_scope`。
