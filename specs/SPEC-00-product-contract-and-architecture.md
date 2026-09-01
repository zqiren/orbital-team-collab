---
id: SPEC-00
title: Product Contract & Architecture
status: Ready
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
5. `/project` 是产品级命令协议；支持原生 slash 的 adapter 提供 slash command，其他 agent 使用 Skill 或 `teamctl` 等价入口。
6. `/project <project-name> <task-id-or-query>` 唯一匹配时原子认领并返回 context；歧义时不认领。
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
  - `/project` 命令语法与解析规则；
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
    └── knowledge-proposals/
```

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
- 每个 project 同时最多一个 active integration job。
- Runner contract 至少包含 `workspace`、`project`、`job_id`、`report_id`、Manager Skill 路径和允许命令。
- merge 成功后才进入 Knowledge Compilation；失败不得修改 canonical knowledge。
- Run 崩溃后可重试，已完成 report 不得重复 merge/apply。

## Manager Guardrails

自动允许：读取项目、审查绑定 commit、运行项目内验证、无冲突 merge、任务状态写入、合法 knowledge apply、创建 Potential Task/Open Question。

自动禁止：force push、remote push、仓库外写入、删除 repo/worktree、合并未绑定 report 的 commit、测试失败标 Done、事实冲突时静默覆盖。

## Command Contract

至少冻结：

```text
/project <project-name> <task-id-or-query>
/project report <task-id>
/project block <task-id> [reason]
/project status [task-id]
/project questions <project-name>
/project manager inbox
```

同时定义等价 `teamctl` 调用、唯一匹配/歧义/已被领取/被问题阻塞时的响应。

# Design Review Notes (2026-09-01)

执行本 spec 时，以下审查发现的 open questions 必须在交付文档中给出明确答案（除第 1 条外均为契约级细节，执行 session 可自行裁决并记录）：

1. **「git-native」叙事 vs runtime 不进 git**：任务/事件 runtime 位于 `<git-common-dir>/orbital-team/`，不版本化、不随 clone/push 传播。单机多 worktree 成立，但产品主线是「git 化项目状态」。`docs/21-architecture.md` 必须正面回答分层：版本化知识（`orbital/*.md`）是 git-native 层；协调 runtime 是本地 ephemeral 层；跨机器同步是 roadmap 项（写入 `docs/30-roadmap.md`），否则评审第一问就会命中此处。
2. **"active integration job" 的定义**：`Awaiting Knowledge` 是否算 active？决定知识编译挂起/失败时后续 report 是否被阻塞。同时补全恢复路径：knowledge 因事实冲突转 Open Question 后 Task 停在什么状态、question answered 后由什么事件恢复 pipeline（当前事件链没有 `question.answered → resume` 路径）。
3. **Task ID 唯一性范围**：`teamctl task start <task-id>`、`/project status [task-id]` 不带 project 参数，隐含 task ID 跨 project 全局唯一。冻结 ID 生成规则（建议 project-prefixed）。
4. **`/project` 保留字**：`<project-name>` 参数位与 `report|block|status|questions|manager` 子命令冲突。冻结保留字清单与解析优先级。
5. **Knowledge change summary schema**：SPEC-07（dashboard 消费方）不依赖 SPEC-05（生产方），可能先行实现。该 schema 必须在本 spec 冻结，否则两个 session 会各自发明格式。
6. **Dashboard 写操作的 actor 身份**：events 要求 actor 字段；UI 添加 Task/回答 question 时的 actor 标识规则需冻结。
7. **Promote 后的初始状态**：统一规则建议 promote → Draft，满足必填项且无 blocking question 才可置 Ready（与 SPEC-07 Write Semantics 对齐）。
8. **Claimed 直接 report 是否合法**：状态机允许 `Claimed → Submitted` 跳过 `In Progress`，还是必须先 `task start`？逐条转换表中明确。

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
- `/project` 在唯一匹配时的 claim 是原子操作，歧义时不改变状态。
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
