---
id: SPEC-00
title: Product Contract & Architecture
status: Done
depends_on: []
unlocks: [SPEC-01]
---

# Outcome

将 Team Workspace 的角色、数据对象、状态机、目录、事件链路、权限和公开命令冻结成一份可实现契约。完成后，后续 session 不需要依赖聊天历史重新解释产品。

# Required Reading

- `AGENTS.md`
- `orbital/PROJECT_STATE.md`
- `orbital/DECISIONS.md`
- `docs/10-user-scenarios.md`
- `docs/11-team-feature-directions.md`
- `specs/EXECUTION_PROTOCOL.md`

# Starting State

- 当前目录包含 Orbital 风格的 `orbital/PROJECT_STATE.md`、`DECISIONS.md`、`LESSONS.md`、`INDEX.md`。
- 当前目录已是 Git repo（2026-09-01 应用户要求提前初始化，main 分支，remote `origin` = github.com/zqiren/orbital-team-collab；push 仍需用户单独授权，见 DECISIONS D10）。
- 不存在已冻结的 Team Workspace schema 或 CLI contract。

Gate checks：

```text
确认上述 memory 文件存在。
确认 specs/README.md 将 SPEC-00 标记为 Ready。
```

# Frozen Decisions

本 spec 必须把以下已对齐内容写入持久架构文档，不能重新设计：

1. 交付 repo 不依赖 Orbital 安装、daemon 或 API。
2. Manager/Member 是角色，与 agent 类型正交。
3. repo 架构支持多个 logical projects，demo 只使用一个。
4. 最终 Git runtime 位于 shared git common dir 的 `orbital-team/` 子目录；seed 位于版本化的 `demo/seed/`。
5. `/team` 是产品级命令协议；支持原生 slash 的 adapter 提供 slash command，其他 agent 使用 Skill 或 `teamctl` 等价入口。
6. `/team claim <project-name> <task-id-or-query>` 唯一匹配时原子认领并返回 context；歧义时不认领。
7. Confirmed Tasks、Potential Tasks、Open Questions 是独立存储。
8. Potential Task 只有 Promote 后才能进入 Confirmed Tasks。
9. Blocking Open Question 阻止 Confirmed Task 被领取。
10. IM v1 只提供 provider stub 与 fixture。
11. 成员 report 写入事件后，由本地 `teamd` 自动启动新的 Manager Agent Run。
12. Manager Run 默认短生命周期、文件冷启动；不向长期窗口注入事件。
13. Manager 在授权范围内自动 merge 与 apply knowledge；高风险、冲突或缺失决策转为 Open Question/Blocked。

# In Scope

- 创建架构与协议文档，至少覆盖：
  - 角色与身份；
  - logical project registry；
  - Git common runtime 定位；
  - 三类工作对象 schema；
  - Report、Event、Integration Job、Knowledge Proposal schema；
  - 状态机和合法转换；
  - `/team` 命令语法与解析规则；
  - file locking、atomic write、idempotency 基线；
  - `teamd` 与 `ManagerRunner` contract；
  - Manager 自动权限与禁止动作；
  - dashboard 与 storage 的边界；
  - IM provider contract；
  - demo 的单 repo 闭环。
- 选择并记录 Python/Node 等实现边界，但不搭建业务代码。
- 为后续 spec 提供直接链接的 schema 示例或正式 schema 文件位置。

# Out of Scope

- 实现 `teamctl`、`teamd`、Skill、dashboard 或 demo。
- 接入真实 IM、账号、云服务或远程 Git。
- 修改 `orbital-src/`。
- 创建生产级权限、SSO、预算或审批系统。

# Required Architecture

## Role Model

- `Manager`：项目级唯一 active role；agent implementation 可切换。负责 integration、任务裁决、Potential Task triage、Open Question 管理和 canonical knowledge。
- `Member`：项目成员；认领 Confirmed Task，在独立 worktree/branch 工作并上报。
- v1 每个 project 同时只有一个 active Manager，但允许通过配置完成 role handoff。

## Storage Model

版本化项目知识：

```text
orbital/PROJECT_STATE.md
orbital/DECISIONS.md
orbital/LESSONS.md
orbital/INDEX.md
orbital/instructions/
```

这里还包括 repo 内的产品代码、配置和 `demo/seed/`。它们构成 git-native durable layer：评审者可以看到 Orbital 编译出的项目学习，并在 clean clone 后从 seed 初始化一个可运行 workspace。

运行时根目录（Git 初始化后）：

```text
<git-common-dir>/orbital-team/
├── registry.json
├── events.jsonl
├── jobs/
├── locks/
└── projects/<project-slug>/
    ├── project.json
    ├── members.json
    ├── tasks.json
    ├── potential-tasks.json
    ├── open-questions.json
    ├── reports/
    ├── integrations/
    ├── knowledge-packs/
    ├── knowledge-proposals/
    └── runs/                 # 本地 Manager/member run metadata、stdout/stderr 与可选 transcript
```

该 runtime 是 file-native local persistent layer：跨进程/重启保留并由 Team Dashboard 读取，但不进入 Git。runtime 使用当前用户私有权限，Dashboard 默认仅监听 loopback；涉及 session/transcript 的内容默认本地私有。Team Cloud 同步、团队访问控制和保留策略属于 roadmap，不伪装成 v1 已具备的跨机器协作。

## Core Flow

```text
IM fixture/context → Potential Task/Open Question → Manager/Human triage
→ Confirmed Task → Member atomic claim → Work/Commit → Report submitted
→ Event → teamd → Integration Job → ManagerRunner → merge/validate
→ Knowledge Proposal → validate/apply → canonical project memory
```

## Confirmed Task States

```text
Draft → Ready → Claimed → In Progress → Submitted → Integrating → Done
                                  ↘ Blocked
Submitted/Integrating → Changes Requested → Claimed/In Progress
Any non-terminal state → Cancelled
```

必须定义每条转换的 actor、precondition、event 和幂等行为。

## Potential Task States

```text
New → Triaged → Promoted
New/Triaged → Dismissed
New/Triaged → Duplicate
```

`Promoted` 必须记录生成的 Confirmed Task ID。

## Open Question States

```text
Open → Answered → Closed
Open → Deferred → Open/Closed
```

`blocking=true` 且状态为 Open/Deferred 的问题会让关联 Task 不可 claim。

## Event-driven Manager

- `report.submitted` 只在 report 和 Task Submitted 状态均持久化成功后写入。
- `teamd` 将事件转成有 idempotency key 的 Integration Job。
- 每个 project 同时最多一个占用 integration slot 的 Job；`Queued`、`Running`、`Retryable` 占用，`Merged`、`Awaiting Knowledge`、`Changes Requested`、`Blocked`、`Done` 不占用。
- Runner contract 至少包含 `workspace`、`project`、`job_id`、`report_id`、Manager Skill 路径和允许命令。
- merge 成功后才进入 Knowledge Compilation；失败不得修改 canonical knowledge。
- Run 崩溃后可重试，已完成 report 不得重复 merge/apply。

## Manager Guardrails

自动允许：读取项目、审查绑定 commit、运行项目内验证、无冲突 merge、任务状态写入、合法 knowledge apply、创建 Potential Task/Open Question。

自动禁止：force push、remote push、仓库外写入、删除 repo/worktree、合并未绑定 report 的 commit、测试失败标 Done、事实冲突时静默覆盖。

## Command Contract

至少冻结：

```text
/team claim <project-name> <task-id-or-query>
/team start <task-id>
/team report <task-id>
/team block <task-id> [reason]
/team status [task-id]
/team questions <project-name>
/team manager inbox
```

同时定义等价 `teamctl` 调用、唯一匹配/歧义/已被领取/被问题阻塞时的响应。

# Resolved Design Review Decisions (2026-09-01)

用户已确认第 1、4 项，其余采用建议默认值。执行本 spec 时须把以下答案写入交付文档，不再作为 open questions 重做设计：

1. **Git-native 与 local runtime 分层**：版本化层包含 durable knowledge、配置、代码和 demo seed，用于审查学习成果与 clean clone；tasks/events/reports/jobs/run/session logs 是持久化的本地 runtime，由 Dashboard 读取但不提交。Team Cloud 的同步、权限和 retention 进入 `docs/30-roadmap.md`。
2. **Integration slot 与恢复**：仅 `Queued`、`Running`、`Retryable` 占用 slot；`Awaiting Knowledge` 不阻塞后续 report。知识冲突时 Task 保持 `Integrating`，Open Question 记录 job/proposal 关联；`question.answered` 发出 `knowledge.resume_requested`，新的短生命周期 Manager Run 重新校验文件哈希，必要时重编 proposal 后继续。
3. **Task ID 唯一性**：使用 `<project-slug>-T-<zero-padded-sequence>`，project slug 保证 registry 内唯一，因此 Task ID 跨 workspace 全局唯一；命令仍可用 project 做额外一致性校验。
4. **命令语法**：入口改为 `/team`，所有操作使用显式动词；claim 固定为 `/team claim <project-name> <task-id-or-query>`，不存在 project-name/subcommand 参数位冲突。
5. **Knowledge change summary schema**：冻结字段 `schema_version`、`summary_id`、`project_slug`、`job_id`、`report_id`、`proposal_id`、`actor`、`applied_at`、`source_commit`、`changes[]`；每个 change 含 `path`、`operation`（created/updated/deleted/moved）、`category`（state/decision/lesson/index/instruction/other）、`summary`，move 另含 `from_path`。SPEC-05 生产、SPEC-07 只读消费同一 schema。
6. **Dashboard actor**：server 启动时必须显式绑定已登记的 `human:<member-id>`，写请求继承 server actor 且不能由浏览器 payload 覆盖；自动事件分别使用 `member:<id>`、`manager:<id>` 或 `system:teamd`。UI 显示当前 actor，缺失或未知 actor 时只读启动。
7. **Promote 初始状态**：promote 一律原子生成 Draft 并保留 evidence/source；另一次显式 validate/ready 转换检查必填项和 blocking question，不自动 Ready。
8. **Report 前置状态**：`Claimed → Submitted` 非法；成员必须先用 `/team start <task-id>`（等价 `teamctl task start`）进入 `In Progress`，只有 assignee 可从 `In Progress` report 到 `Submitted`。

# Deliverables

- `docs/20-prd.md`：核心产品范围、角色、场景和非目标。
- `docs/21-architecture.md`：文件架构、事件链路、权限与 runtime。
- `docs/22-protocol.md`：schema、状态机、命令和错误语义。
- `docs/30-roadmap.md`：按 SPEC-01～SPEC-09 的依赖、风险与演示里程碑组织的路线图。
- 必要时新增 `schemas/`，但只包含后续实现直接消费的 schema，不创建装饰性文件。
- 更新 `orbital/DECISIONS.md`、`orbital/INDEX.md`、`orbital/PROJECT_STATE.md`。

# Acceptance Criteria

- 新 session 只读交付文档即可准确回答：谁能写什么、三类工作对象如何转换、report 如何触发 Manager、失败如何恢复。
- 每个状态转换都有 actor、precondition 和 event。
- `/team claim` 在唯一匹配时的 claim 是原子操作，歧义时不改变状态。
- 文档明确 Manager agent-agnostic，且 v1 runner 为事件触发的新 run。
- 文档明确文件是唯一事实来源，UI/daemon/agent session 都不是隐藏事实源。
- 后续 SPEC-01 不需要新增产品决策即可实现 runtime kernel。

# Verification

- 人工逐条核对 `Frozen Decisions` 均在交付文档出现且无冲突。
- 检查三份文档之间术语一致：Project、Manager、Member、Task、Potential Task、Open Question、Report、Integration Job、Knowledge Proposal。
- 检查所有 schema 示例可被 JSON parser 接受（若创建 JSON 文件）。
- 使用 `rg` 检查旧的 “Codex Manager” 绑定表述未进入新协议。

# Handoff Checklist

- 填写 Completion Record。
- 将 SPEC-00 标记 Done、SPEC-01 标记 Ready。
- 把架构决定写入 `orbital/DECISIONS.md`。
- 在 `orbital/INDEX.md` 登记 `specs/` 与新增 docs/schema。
- `orbital/PROJECT_STATE.md` 指向 SPEC-01。

## Completion Record

- Final status: Done
- Outcome achieved: 冻结 Team Workspace 的产品范围、两层文件模型、角色/权限、Git common-dir runtime、schema、状态机、`/team`/`teamctl`、event-driven Manager、knowledge Git 闭环、Dashboard/IM boundary 与 SPEC-01～09 路线。
- Files changed: 新增 `docs/20-prd.md`、`docs/21-architecture.md`、`docs/22-protocol.md`、`docs/30-roadmap.md`、`schemas/README.md`、`schemas/v1/orbital-team.schema.json`；同步校准上游 docs、SPEC-01～09、Spec Index 与 Orbital memory。
- Verification run: Python `json` + `jsonschema.Draft202012Validator` 校验 schema、13 个命名 JSON 示例、Project/四类 Store/ManagerRunner I/O 与非法 actor；`rg` 扫描凭证/用户路径、旧 `/project`/“Codex Manager”绑定及 integration event 语义；`git diff --check`；Git gate。
- Verification result: 全部通过；48 个 `$defs`、13 个 JSON 示例有效，三份核心文档术语与 Markdown fence 一致，未发现交付隐私数据、旧接口或空白字符错误。
- Deviations from spec: 无范围偏离；按 spec 允许新增直接消费的 schema bundle。为落实禁止 `Claimed → Submitted` 补齐 `/team start`；契约审计补齐受控 git mutation lock、独立 local knowledge commit/no-change summary 与 `integration.merged`/`integration.completed` 分义。
- Decisions recorded: D12（Python 3.11 + JSON Schema/filelock + 无 Node/DB Dashboard 边界）；D13（durable knowledge commit、clean workspace 与受控 Git mutation）。
- Lessons recorded: zsh 的 `path` 是特殊参数，验证脚本不得用作循环变量。
- Known limitations: v1 是单机/单 OS 用户信任边界；跨机器 runtime/权限/retention 属于 Team Cloud；完整 transcript 取决于 runner/adapter；非 POSIX 权限边界需在实现期验证。
- Working tree / commit: 内容与验证均完成，但当前 sandbox 禁止创建 `.git/index.lock`，且执行环境无法解析 `github.com`，因此 checkpoint 尚未 commit/push；本机终端执行 `git add -A && git commit -m "docs: freeze Team Workspace product contract" && git push -u origin main` 即可完成。standing authorization 见 DECISIONS D10。
- Next spec readiness: SPEC-01 已 Ready；可仅依赖本 Completion Record、四份交付文档与 schema bundle 实现 File Runtime Kernel。
