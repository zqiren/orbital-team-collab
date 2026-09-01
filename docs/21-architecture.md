# 21 — Orbital Team Workspace Architecture

> 状态：Protocol 1.0 冻结架构；SPEC-01～09 实现与最终 clean-copy 验证已收敛（2026-09-01）
> 规范性 schema：`schemas/v1/orbital-team.schema.json`  
> 命令、状态机与错误语义：`docs/22-protocol.md`

## 1. 架构目标

Team Workspace 必须在一个 clean clone 中可理解、可初始化和可演示，同时满足：

- 不安装或调用 Orbital 本体、daemon、本地 API。
- 多个 Git worktree 解析到同一份本地 runtime。
- agent/session/UI/daemon 随时退出后，下一次 run 只靠文件恢复。
- 高频协调数据不污染 Git；durable project learning 可被 Git 审查和传播。
- Manager 是可替换角色，不绑定 Codex、Claude 或其他厂牌。

## 2. 三层视图

```text
┌──────────────────────────────────────────────────────────────┐
│ Git-native durable layer                                     │
│ code · config · demo/seed · orbital/{STATE,DECISIONS,...}   │
└───────────────────────▲──────────────────────────────────────┘
                        │ validated Knowledge Proposal apply
┌───────────────────────┴──────────────────────────────────────┐
│ File-native local persistent runtime                         │
│ tasks · questions · reports · events · jobs · runs/logs      │
└──────────────▲───────────────────────▲───────────────────────┘
               │ domain/storage API    │ read projection
┌──────────────┴──────────────┐  ┌─────┴──────────────────────┐
│ teamctl · teamd · adapters  │  │ loopback Team Dashboard   │
│ ManagerRunner · IM fixture  │  │ no database/no state fork │
└─────────────────────────────┘  └────────────────────────────┘
```

文件 runtime 是业务事实来源。进程内对象、event cursor、Dashboard view model 和 agent prompt 都可丢弃重建。

## 3. Git 与 runtime 定位

任意 worktree 内执行：

```text
git rev-parse --path-format=absolute --git-common-dir
```

结果记为 `<git-common-dir>`；runtime 固定在：

```text
<git-common-dir>/orbital-team/
```

普通 clone 通常得到 `<repo>/.git/orbital-team/`；linked worktree 与主 worktree 指向同一个 common dir，因此天然共享 runtime 且不会出现在 `git status`。

初始化前必须同时验证：调用路径属于 Git worktree、common dir 可写、seed schema version 受支持。不得把未解析的 `$HOME`、`~`、宽泛 glob 或用户输入路径直接作为 reset/cleanup 目标。

## 4. Runtime layout

```text
<git-common-dir>/orbital-team/
├── registry.json                    # logical projects + schema/runtime version
├── events.jsonl                     # 全 workspace append-only domain events
├── locks/
│   ├── registry.lock
│   ├── events.lock
│   ├── project-<slug>.lock
│   └── git-<slug>.lock                # merge/knowledge commit 串行化
├── consumers/
│   └── teamd.json                   # 可重建 event cursor，不是业务真相
├── jobs/
│   └── <job-id>.json                # canonical Integration Job
└── projects/<project-slug>/
    ├── project.json
    ├── members.json
    ├── tasks.json
    ├── potential-tasks.json
    ├── open-questions.json
    ├── operations/                  # 可恢复的 command transaction journal
    ├── reports/<report-id>.json
    ├── integrations/<job-id>.json   # 结构化结果/验证证据
    ├── knowledge-packs/<pack-id>.json
    ├── knowledge-proposals/<proposal-id>.json
    ├── knowledge-summaries/<summary-id>.json
    └── runs/<run-id>/
        ├── run.json
        ├── stdout.log
        ├── stderr.log
        └── transcript.*             # adapter 可提供时才存在
```

`registry.json` 中 project slug 唯一，只保存 slug/display name/`project.json` 相对路径等 stable lookup，不复制 mutable config。每个 Project 的 `project.json` 是 canonical config，保存 canonical workspace、允许 worktree 根、active Manager、runner manifest 和 seed provenance；不保存凭证。

Manager handoff 只切换 Project 的 active role/config，不迁移 provider session。存在 Running/Retryable Job 时拒绝 handoff；新 Manager 的下一次 run 仍从文件冷启动。

## 5. 实现边界

### Runtime 与 CLI

- Python 3.11+。
- 一个共享 Python package 承载 schema model、domain transitions、storage、CLI、daemon 和 Dashboard adapter；调用方不得各自改 JSON。
- 规范验证使用 JSON Schema Draft 2020-12；实现依赖锁定 `jsonschema >=4,<5`。
- 跨平台 file lock 使用锁定版本的 `filelock >=3,<4`；atomic replace、fsync、hash 与 JSONL 使用 Python 标准库。
- CLI 使用 `argparse`；不引入第二套命令框架。

### Dashboard

- Python local HTTP adapter + repo 内静态 HTML/CSS/ES modules。
- v1 不需要 Node 构建链或前端数据库；所有写 API 调用同一 domain command 层。
- 默认监听 `127.0.0.1`，server 启动参数绑定 actor；未知 actor 时只读。
- 事件更新可使用 bounded polling 或 SSE，但 cursor 只是投影，可从 `events.jsonl` 重建。

### Agent adapters

- `/team` 是产品行为协议；原生 slash adapter 只做参数转换。
- `teamctl` 是确定性状态变化入口；Skill 教 agent 工作规则，不复制状态机。
- ManagerRunner 使用 manifest/custom command 适配不同 agent CLI；provider session ID 只作为 observability metadata。

这一选择优先 clean clone、可审查与低依赖。复杂 UI framework、数据库、消息队列或云服务不在原型范围。

## 6. 身份与权限

Actor 使用不可省略的字符串：

```text
human:<member-id>
member:<member-id>
manager:<manager-id>
system:teamd
system:fixture
```

- Human Dashboard server 从启动参数取得 actor，写请求不能覆盖。
- Member command 从已登记 identity/worktree binding 取得 actor，不能仅信任 CLI 传入值。
- ManagerRunner 从 Project active Manager config 取得 actor。
- `teamd` 只执行调度/恢复转换，不冒充 Human/Member/Manager 做语义决定。

v1 是单 OS 用户信任边界，不宣称远程认证。runtime 根目录默认 `0700`，敏感文件默认 `0600`；非 POSIX 平台必须实现或记录等价边界。

## 7. Storage、并发与崩溃恢复

### Lock order

所有实现统一顺序，禁止逆序获取：

```text
registry.lock → project-<slug>.lock → git-<slug>.lock → events.lock
```

- registry 变更只需 registry lock。
- 一个 Project 的 resolve + precondition recheck + transition 在 project lock 内完成。
- 跨 Project 不共享 project lock，仅在 append 全局 event 时短暂竞争 events lock。
- integration slot 由 project lock 保护；`Queued`、`Running`、`Retryable` 算占用。
- Manager semantic review/compile 不长期持锁；实际 `git merge` 与 knowledge commit 必须通过 domain command 短暂取得 project + git lock。Awaiting Knowledge 虽释放 integration slot，仍不能与后续 Job 同时改 Git。

### Atomic JSON

1. 在目标文件同目录创建唯一 temp file。
2. 写入 canonical JSON、flush、`fsync`。
3. `os.replace` 到目标路径。
4. 尽可能 `fsync` 父目录。

禁止原地 truncate。每个 mutable store 带 `revision`，命令在锁内重新读取并校验预期 revision。

### Command transaction journal

涉及多个文件和 event 的 command 使用 `operations/<idempotency-key>.json`：

1. 在 project lock 内解析并重新检查 precondition。
2. 写入 `Prepared` operation，包含稳定 event ID、目标 revision/hash 和将写入的对象引用。
3. 原子写入业务文件。
4. 在 events lock 内 append 单行 event 并 fsync。
5. 将 operation 标记 `Committed`，返回稳定 result。

若进程在 2–5 之间退出，下一次同 key 调用或 startup reconciler 根据目标 revision/hash 重放缺失步骤；不得生成第二个 event。`report.submitted` 只有在 Report 与 Task=Submitted 已持久化后才 append。

### JSONL

- UTF-8、每行一个完整 JSON object、末尾换行。
- event ID 唯一；reader 忽略最后一条因崩溃产生的残缺行并报告 corruption，不覆盖源文件。
- event 是审计与调度入口，不是唯一恢复依据；`teamd` 还会扫描 Submitted Task/Report 与 Job idempotency key 修复漏消费。

## 8. Domain boundaries

```text
CLI / Dashboard route / Adapter / teamd
                 │
                 ▼
          Domain command layer
     resolve · authorize · transition
                 │
                 ▼
           Storage transaction
      lock · journal · atomic write · event
```

读取可通过 repository/query service；任何写入都必须经过 command layer。Dashboard 不能复制 promote/answer/ready 逻辑；Manager prompt 不能直接手改 runtime JSON。

## 9. Event-driven Manager pipeline

```text
Member report command
  └─ persist Report + Task Submitted + report.submitted
       └─ teamd reconciliation
            └─ deterministic Job ID; create Queued
                 └─ acquire project integration slot
                      └─ new Manager Run (file cold start)
                           ├─ validate binding/diff/tests
                           ├─ guarded clean merge → Awaiting Knowledge
                           ├─ changes → Changes Requested
                           └─ risk/conflict → Blocked + Open Question
```

一个 Project 同时最多一个占用 slot 的 Job。`Awaiting Knowledge` 已完成代码 merge，不继续占 slot，后续 Report 可集成。

### ManagerRunner input

- workspace 与 allowed worktree roots
- project slug、job/report/task IDs
- bound branch/commit 与 base/target ref
- Manager Skill/brief 路径
- 结构化 command policies（argv prefix/cwd scope/additional-args policy）、timeout、environment policy；执行使用 argv 且禁止 shell interpolation
- output/result 路径

### ManagerRunner output

- outcome、merge commit、validation records
- changes requested 或 blocking risk
- created Open Question IDs
- run ID 与 stdout/stderr/transcript location

输出必须先通过 schema 和 deterministic guard，再驱动状态变化。自然语言 stdout 不能直接被当成成功。Runner 不得直接执行裸 `git merge/commit`；它只能调用受控 domain command，后者在 git lock 内重新校验 target HEAD、Report binding、allowlist 和 workspace cleanliness。

## 10. Knowledge compilation

```text
integration.merged
→ Knowledge Pack(report + merged diff + current memory hashes)
→ Manager semantic compile
→ Knowledge Proposal(structured patches + summary)
→ path/rule/hash validation
→ atomic apply to canonical memory + local knowledge commit
→ knowledge.applied
→ Task Done + Job Done
```

- merge 未成功时不得生成可 apply proposal。
- apply 前 canonical workspace 必须没有 pipeline 外未提交改动；否则进入 Blocked，不得覆盖用户工作。
- proposal 记录每个目标文件的 base hash；变化则进入 Stale 并重新编译。v1 自动 apply allowlist 仅含 PROJECT_STATE、DECISIONS、LESSONS、INDEX；`orbital/instructions/` 只读、由 Human 管理。
- 事实冲突或缺失判断创建关联 Open Question，Task 保持 Integrating，Job/Proposal 保持 Awaiting/Blocked，但不占 integration slot。
- `question.answered` 产生 `knowledge.resume_requested`；新的短生命周期 Manager Run 从文件恢复、重新校验并继续。
- 成功 apply 只 stage allowlisted memory path，创建独立本地 knowledge commit 并生成规范的 Knowledge Change Summary；不得 amend code merge 或 remote push。无变化时生成 `knowledge_commit=null` 的 no-change summary，不创建空 commit。SPEC-07 只消费该 schema。

## 11. Dashboard boundary

Dashboard 是本地 projection 和 command adapter：

- 读取 registry、三类工作对象、events、jobs、knowledge summaries、run records/logs。
- 写入仅允许 Add/Edit Task、Add/Answer/Defer/Close Question、Potential Task triage 等 Human 权限命令。
- claim/report/merge 主要展示，不冒充 Member/Manager。
- server 重启后不迁移数据库，完全从文件重建。
- 文件损坏、锁超时、runner offline、transcript unavailable 必须显示错误，不得以空状态覆盖数据。

## 12. IM provider contract

v1 provider 只负责把 fixture/context 规范化为 message envelope：provider、conversation、message ID、sender、timestamp、text、permalink/evidence metadata。

Extractor 只能产生 Potential Task 或 Open Question：

- 不创建 Ready Task。
- 不 claim、不 assign、不启动 agent。
- 使用 `(provider, conversation_id, message_id, extractor_version)` 幂等。
- 保存最小 evidence；不得提交真实 IM 或凭证。

真实 Slack/飞书/企业微信连接、账号授权和 retention 不在 v1。

## 13. Demo isolation

- `demo/seed/` 版本化；setup 将其复制到安全创建的临时 Git repo。
- manager/member worktrees 与 runtime 都位于打印出的精确临时路径。
- reset/cleanup 只接受带 demo marker 且解析通过的精确目录。
- live run 和 replay 均不得修改交付 repo；replay 在 UI 中持续标注 simulated。
- 缺少 agent CLI 时 doctor 提示 runner 替代，不伪造 live success。

## 14. Team Cloud 演进边界

Team Cloud 不是把 `.git/orbital-team/` 粗暴上传：它需要独立设计 tenant identity、authorization、event replication、offline conflict、encryption、retention、regional storage 和 audit export。

v1 schema 为未来同步保留稳定 object/event ID、actor、timestamp、revision 与 schema version，但不承诺远程一致性。Durable knowledge 仍通过 Git/PR 传播；Team Cloud 主要同步 runtime 与 observability，并承载 Approval Routing 和 Team Budget 的团队控制面。
