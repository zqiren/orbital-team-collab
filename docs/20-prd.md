# 20 — Orbital Team Workspace PRD

> 状态：Protocol 1.0 冻结契约；SPEC-01～09 已按此实现并完成交付收敛（2026-09-01）
> 上游：`docs/02-competitive-landscape.md`、`docs/10-user-scenarios.md`、`docs/11-team-feature-directions.md`

## 1. 一句话

Orbital Team Workspace 把“某个人与某个 agent 的 session”升级为“团队与多个异构 agent 共同维护的 Project”：成员领取结构化任务并提交 Report，事件驱动的 Manager 自动集成代码、提炼可审查的项目学习，本地 Team Dashboard 展示任务、问题、运行记录和知识变化。

## 2. 要解决的问题

工程团队已经同时使用 Claude Code、Codex、Gemini CLI、Cursor 等 agent，但协作仍靠人搬运上下文：

- 任务与运行历史困在个人 session，换人、换 agent、换机器就断层。
- agent 做完代码后，决策、gotcha 和当前项目状态不会自动沉淀。
- 多个 agent 可以并行工作，却没有跨 session 的领取、上报、集成和恢复协议。
- 竞品的 Team 能力主要是 SSO、审计和用量控制，协作对象仍是用户账号或平台内黑盒资产。

Orbital 的差异不是“再做一个 coding agent”，而是把 Project 变成跨人、跨 agent、跨 session 的事实单位。

## 3. 产品判断：两层文件模型

“Git-native”不表示把每条运行事件都提交到 Git。产品明确分为两层：

| 层 | 内容 | 生命周期 | 传播方式 | 评审价值 |
|---|---|---|---|---|
| Git-native durable layer | 代码、配置、demo seed、PROJECT_STATE、DECISIONS、LESSONS、INDEX、instructions | 长期、低频、可审查 | clone / pull / PR | 看见 Orbital 学到了什么；clean clone 可运行 |
| File-native local runtime | Tasks、Potential Tasks、Open Questions、Reports、Events、Integration Jobs、Knowledge Proposals、run/session logs | 高频、本地持久、可恢复 | v1 同机共享；未来 Team Cloud | 看见团队和 agent 正在做什么 |

Git 是 durable knowledge 的同步与评审层，不是高频协调数据库。v1 诚实限定为单机多 worktree；跨机器 runtime 同步、团队访问控制与 retention 是 Team Cloud 路线。

## 4. 目标用户

### Primary：3–15 人、多 agent 混用的创业工程团队

- 每个成员有自己的 agent 与偏好。
- 需要共享任务、项目学习和交接状态，但不想先采购重型平台。
- Tech lead/CTO 是部署者与付费决策者。

### Secondary：20–100 人公司的工程负责人

- 需要团队预算、跨人审批、可观测性与审计。
- 本原型只验证共享状态与自动集成；Approval Routing、Team Budget 在产品路线中后续进入。

### Secondary：新成员与项目接手者

- 希望 clone 后立刻知道“做到哪、为什么这么做、踩过什么坑”。

## 5. 核心工作对象

| 对象 | 含义 | 谁主要写 | 是否进 Git |
|---|---|---|---|
| Project | logical project、workspace 与 Manager 配置 | Human/Manager | registry/runtime；配置 seed 可版本化 |
| Confirmed Task（简称 Task） | 已被团队确认、可进入执行承诺的工作 | Human/Manager；Member 推进自己领取的任务 | 否 |
| Potential Task | 从 IM/context 提取、尚未承诺的候选 | provider/system 创建，Human/Manager triage | 否 |
| Open Question | 缺失决策、冲突或风险；可阻塞 Task | Human/Manager/system | 否 |
| Report | Member 对 commit、验证、风险和 knowledge candidate 的不可变上报 | assignee Member | 否 |
| Integration Job | 一个 Report 的可恢复自动集成 pipeline | teamd/Manager | 否 |
| Knowledge Proposal | Manager 根据 merged diff 与 Report 生成的受验证 memory patch | Manager + deterministic validator | 否；apply 后结果进入 Git layer |
| Run Record | Manager/Member run 的状态、日志位置和可选 transcript | adapter/runner | 否，本地敏感数据 |

Potential Task 不能被直接领取；只有 Promote 后生成的 Draft Task 才可能经过 Ready 校验。Open Question 与 Task 分离，避免用含糊的“blocked task”掩盖真正缺失的决定。

## 6. 角色与身份

### Human Operator

- 创建/编辑 Task 与 Open Question，triage Potential Task。
- 回答需要人类判断的问题。
- Dashboard server 以显式 `human:<member-id>` 身份启动；浏览器 payload 不得伪造 actor。

### Member

- 通过 `/team claim <project> <task-id-or-query>` 原子领取唯一匹配的 Ready Task。
- 在独立 branch/worktree 工作，先 start，再 commit、验证和 report。
- 不直接修改 canonical project memory，不绕过 blocking Open Question。

### Manager

- 每个 Project 同时只有一个 active Manager role，但实现可以是 Codex、Claude、Gemini 或其他可配置 runner。
- 负责 Report review、验证、无冲突 merge、Potential Task triage、Open Question 管理和 canonical knowledge compilation。
- 默认每个事件启动新的短生命周期 run，从文件冷启动；provider session 不是事实来源。

### System (`teamd`)

- 监听/补偿文件事件，创建幂等 Integration Job，串行调度占用 integration slot 的 Job。
- 不做语义决策，不保存文件之外的隐藏业务状态。

## 7. v1 用户旅程

1. 评审者 clean clone repo，运行 setup；版本化 seed 初始化本地 runtime。
2. Dashboard 展示一个 Project、Manager、两个 Ready Tasks、Potential Tasks 和 Open Questions。
3. Alice 执行 `/team claim Apollo apollo-T-0001`，唯一匹配时在 project lock 内完成认领并拿到 Context Pack。
4. Bob 无法领取 Alice 的任务，选择第二个 Task。
5. 两人显式 start，在各自 worktree 修改、验证、commit，再提交结构化 Report。
6. `report.submitted` 触发 `teamd` 创建 Integration Job；短生命周期 Manager Run 审查、验证并无冲突 merge。
7. merge 成功后 Manager 生成 Knowledge Proposal；validator 检查路径、基线 hash 和 memory 规则后 apply，并把 allowlisted memory changes 做成独立的本地 knowledge commit（不 push）。
8. Task/Job 进入 Done；Dashboard 展示代码 merge、运行日志、活动流与 PROJECT_STATE/LESSONS 变化。
9. 新成员冷启动时读取最新 durable knowledge，不需要继承旧 agent session。

## 8. v1 功能范围

### P0：必须成立

- 多 logical project registry；demo 使用一个 Project。
- Confirmed Tasks、Potential Tasks、Open Questions 三种独立生命周期。
- `/team` + `teamctl` 等价协议；唯一匹配原子 claim，歧义零副作用。
- Member Context Pack、worktree/commit 绑定、不可变 Report。
- `report.submitted → teamd → Integration Job → ManagerRunner` 自动闭环。
- 无冲突 merge、验证、retry/idempotency 与 Changes Requested/Blocked 恢复。
- Knowledge Pack、Proposal、validate/apply 与 canonical memory 更新。
- 本地 Team Dashboard：任务、候选、问题、活动、integration、knowledge、run/session logs。
- IM provider contract + fixture，只生成 Potential Task/Open Question。
- clean-clone demo、live flow 和明确标注的 deterministic replay。

### P1：产品路线，但不进入本原型

- Team Cloud：跨机器 runtime 同步、身份、权限、retention 和冲突协议。
- Approval Routing：按风险/项目/预算路由到其他人审批。
- Team Budget：per-project/member/worker 跨 provider 计量与闸门。
- 异构 worker pool 的远程调度。

### 非目标

- 不依赖 Orbital 安装、daemon 或本地 API。
- 不接真实 IM、真实用户账号、远程 Git push 或云服务。
- 不做 SSO/SCIM、生产级 RBAC、预算或审批系统。
- 不做云托管 IDE、团队聊天室、向量记忆库或完整 code-review IDE。
- 不自动解决复杂 merge conflict，不 force push，不删除 repo/worktree。

## 9. 产品原则与安全边界

1. 文件是唯一事实来源；UI、daemon、cache、agent 输出和 provider session 都只是执行器或投影。
2. 状态变化只能复用同一 domain/storage 层，必须留下 actor、event 和 idempotency key。
3. Manager 可自动读取、审查绑定 diff、运行项目内验证、无冲突 merge、对 PROJECT_STATE/DECISIONS/LESSONS/INDEX 做合法 knowledge apply；instructions v1 只读。
4. Manager 不得 remote push、force push、写仓库外、删除 repo/worktree、合并未绑定 Report 的 commit、测试失败标 Done或静默覆盖事实冲突。
5. runtime 默认当前 OS 用户私有；Dashboard 默认 loopback。完整 transcript 只在 runner/adapter 能提供时展示。
6. replay 必须标注模拟，不能替代 live acceptance。

## 10. 成功指标

### 原型验收指标

- 两个成员并发 claim 同一 Task，恰好一个成功。
- Report 后无需人提醒，Manager pipeline 自动运行到 Done 或可解释的 Changes Requested/Blocked。
- 同一 Report/event 重放不重复 merge 或 apply knowledge。
- durable knowledge 更新有独立 Git commit；无变化时明确记录 no-change，不制造空 commit。
- clean clone 不安装 Orbital 即可 setup 和启动 Dashboard。
- demo 前后交付 repo 不被本地 runtime 污染。

### 产品北极星

**周跨成员项目闭环数**：一周内由成员 A/其 agent 发起，经过其他成员或 Manager role 继承、审查、合并或决策，并落入 durable project knowledge 的闭环数量。

辅助指标：新成员首次有效 Task 的时间、重复踩坑率、Report→integration 中位时长、需要人工恢复的 pipeline 比例、knowledge proposal 接受/阻塞率。

## 11. 已知限制

- v1 runtime 不随 clone/push 传播，因此不是跨机器 live collaboration；clone 继承的是 durable knowledge 和可初始化 seed。
- 同一 Project 只有一个 active Manager role；handoff 是配置操作，不做多 Manager 共识。
- v1 的 OS identity 等于本机信任边界，`human:<member-id>` 不是远程认证。
- provider 不暴露 transcript 时，只能展示 run metadata、stdout/stderr 或日志指针。
- POSIX 文件权限是 v1 默认目标；其他平台需在实现验证中记录等价边界。
- 默认验收 runner 是完全离线的 builtin scripted Manager；外部 Codex/Claude Code 的实际可用性取决于本机 CLI、登录与 provider sandbox，不能由 replay 或 CLI 文件存在替代。
- 受限 sandbox 可验证 Dashboard handler/projection 但可能禁止 loopback bind；真实 browser/socket 必须在普通本机单独记录。

## 12. 实现与证据

- 根 `README.md` 提供 30 秒立论、架构图与 5 分钟 quickstart。
- `specs/README.md` 的 SPEC-00～09 均为 Done，每份 Completion Record 保存实际验证与偏离。
- `scripts/verify_clean_copy.py` 从 disposable copy 验证 install、tests、CLI、demo、reset、repo isolation 与可选 live bind。
- `docs/38-final-verification.md` 给出最终测试矩阵、external runner 判定标准与无隐私泄漏的录制清单。
